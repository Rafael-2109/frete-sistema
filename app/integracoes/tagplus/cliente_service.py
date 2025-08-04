"""
Serviço para importar clientes do TagPlus
"""
import requests
import logging
from datetime import datetime
from app import db
from app.carteira.models import CadastroCliente
from app.integracoes.tagplus.auth import TagPlusAuth
import re

logger = logging.getLogger(__name__)

class TagPlusClienteService:
    """Serviço para importar e sincronizar clientes do TagPlus"""
    
    def __init__(self, auth_manager=None):
        self.auth = auth_manager or TagPlusAuth()
        self.base_url = "https://api.tagplus.com.br/v1"
        self.clientes_importados = []
        self.erros = []
    
    def listar_clientes(self, filtros=None):
        """Lista clientes do TagPlus com filtros opcionais"""
        try:
            headers = self.auth.get_headers()
            
            # Parâmetros de busca
            params = {
                'page': 1,
                'per_page': 100
            }
            
            if filtros:
                params.update(filtros)
            
            todos_clientes = []
            
            while True:
                response = requests.get(
                    f"{self.base_url}/clientes",
                    headers=headers,
                    params=params
                )
                
                if response.status_code != 200:
                    logger.error(f"Erro ao buscar clientes: {response.text}")
                    break
                
                data = response.json()
                clientes = data.get('data', [])
                todos_clientes.extend(clientes)
                
                # Verifica se há mais páginas
                if not data.get('has_more', False):
                    break
                
                params['page'] += 1
            
            logger.info(f"Total de clientes encontrados: {len(todos_clientes)}")
            return todos_clientes
            
        except Exception as e:
            logger.error(f"Erro ao listar clientes TagPlus: {e}")
            self.erros.append(str(e))
            return []
    
    def buscar_cliente_por_cnpj(self, cnpj):
        """Busca cliente específico por CNPJ"""
        try:
            cnpj_limpo = re.sub(r'\D', '', str(cnpj))
            
            clientes = self.listar_clientes({
                'cnpj': cnpj_limpo
            })
            
            if clientes:
                return clientes[0]
            return None
            
        except Exception as e:
            logger.error(f"Erro ao buscar cliente por CNPJ: {e}")
            return None
    
    def importar_cliente(self, cliente_tagplus):
        """Importa um cliente do TagPlus para o sistema"""
        try:
            # Extrai dados do cliente
            cnpj = re.sub(r'\D', '', str(cliente_tagplus.get('cnpj', '')))
            
            # Verifica se já existe
            cliente_existente = CadastroCliente.query.filter_by(
                cnpj_cpf=cnpj
            ).first()
            
            if cliente_existente:
                # Atualiza dados
                return self._atualizar_cliente(cliente_existente, cliente_tagplus)
            else:
                # Cria novo
                return self._criar_cliente(cliente_tagplus)
                
        except Exception as e:
            logger.error(f"Erro ao importar cliente: {e}")
            self.erros.append(f"Erro ao importar cliente {cliente_tagplus.get('nome')}: {str(e)}")
            return None
    
    def _criar_cliente(self, dados_tagplus):
        """Cria novo cliente no sistema"""
        try:
            # Mapeia dados do TagPlus para o sistema
            cliente = CadastroCliente(
                # Identificação
                cnpj_cpf=re.sub(r'\D', '', str(dados_tagplus.get('cnpj', ''))),
                raz_social=dados_tagplus.get('razao_social', dados_tagplus.get('nome', '')),
                raz_social_red=dados_tagplus.get('nome_fantasia', '')[:50] if dados_tagplus.get('nome_fantasia') else '',
                
                # Endereço principal
                cep_endereco_ent=dados_tagplus.get('cep', ''),
                rua_endereco_ent=dados_tagplus.get('logradouro', ''),
                endereco_ent=f"{dados_tagplus.get('logradouro', '')}, {dados_tagplus.get('numero', '')}",
                bairro_endereco_ent=dados_tagplus.get('bairro', ''),
                nome_cidade=dados_tagplus.get('cidade', ''),
                municipio=dados_tagplus.get('cidade', ''),
                estado=dados_tagplus.get('uf', ''),
                cod_uf=dados_tagplus.get('uf', ''),
                
                # Contato
                telefone_endereco_ent=dados_tagplus.get('telefone', ''),
                email=dados_tagplus.get('email', ''),
                
                # Dados de entrega (copia do principal se não tiver)
                cnpj_endereco_ent=re.sub(r'\D', '', str(dados_tagplus.get('cnpj', ''))),
                empresa_endereco_ent=dados_tagplus.get('razao_social', dados_tagplus.get('nome', '')),
                
                # Status
                cliente_ativo=dados_tagplus.get('ativo', True),
                
                # Controle
                created_by='ImportTagPlus',
                updated_by='ImportTagPlus',
                
                # ID TagPlus para referência
                observacoes=f"ID TagPlus: {dados_tagplus.get('id', '')}"
            )
            
            # Define vendedor padrão se não tiver
            if not cliente.vendedor:
                cliente.vendedor = 'A DEFINIR'
            
            # Define equipe de vendas padrão
            if not cliente.equipe_vendas:
                cliente.equipe_vendas = 'GERAL'
            
            db.session.add(cliente)
            db.session.commit()
            
            self.clientes_importados.append({
                'cnpj': cliente.cnpj_cpf,
                'nome': cliente.raz_social,
                'acao': 'criado'
            })
            
            logger.info(f"Cliente {cliente.raz_social} criado com sucesso")
            return cliente
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao criar cliente: {e}")
            raise
    
    def _atualizar_cliente(self, cliente_existente, dados_tagplus):
        """Atualiza cliente existente com dados do TagPlus"""
        try:
            # Atualiza apenas campos vazios ou com flag de atualização
            if not cliente_existente.raz_social:
                cliente_existente.raz_social = dados_tagplus.get('razao_social', dados_tagplus.get('nome', ''))
            
            if not cliente_existente.raz_social_red:
                cliente_existente.raz_social_red = dados_tagplus.get('nome_fantasia', '')[:50] if dados_tagplus.get('nome_fantasia') else ''
            
            # Atualiza endereço se estiver vazio
            if not cliente_existente.cep_endereco_ent:
                cliente_existente.cep_endereco_ent = dados_tagplus.get('cep', '')
                cliente_existente.rua_endereco_ent = dados_tagplus.get('logradouro', '')
                cliente_existente.endereco_ent = f"{dados_tagplus.get('logradouro', '')}, {dados_tagplus.get('numero', '')}"
                cliente_existente.bairro_endereco_ent = dados_tagplus.get('bairro', '')
                cliente_existente.nome_cidade = dados_tagplus.get('cidade', '')
                cliente_existente.municipio = dados_tagplus.get('cidade', '')
                cliente_existente.estado = dados_tagplus.get('uf', '')
                cliente_existente.cod_uf = dados_tagplus.get('uf', '')
            
            # Atualiza contato se vazio
            if not cliente_existente.telefone_endereco_ent:
                cliente_existente.telefone_endereco_ent = dados_tagplus.get('telefone', '')
            
            if not cliente_existente.email:
                cliente_existente.email = dados_tagplus.get('email', '')
            
            # Adiciona ID TagPlus nas observações
            if cliente_existente.observacoes:
                if 'ID TagPlus:' not in cliente_existente.observacoes:
                    cliente_existente.observacoes += f"\nID TagPlus: {dados_tagplus.get('id', '')}"
            else:
                cliente_existente.observacoes = f"ID TagPlus: {dados_tagplus.get('id', '')}"
            
            cliente_existente.updated_by = 'ImportTagPlus'
            cliente_existente.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            self.clientes_importados.append({
                'cnpj': cliente_existente.cnpj_cpf,
                'nome': cliente_existente.raz_social,
                'acao': 'atualizado'
            })
            
            logger.info(f"Cliente {cliente_existente.raz_social} atualizado")
            return cliente_existente
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao atualizar cliente: {e}")
            raise
    
    def importar_todos_clientes(self, apenas_ativos=True):
        """Importa todos os clientes do TagPlus"""
        try:
            filtros = {}
            if apenas_ativos:
                filtros['ativo'] = True
            
            clientes = self.listar_clientes(filtros)
            
            for cliente_tagplus in clientes:
                try:
                    self.importar_cliente(cliente_tagplus)
                except Exception as e:
                    logger.error(f"Erro ao importar cliente {cliente_tagplus.get('nome')}: {e}")
                    continue
            
            return {
                'success': True,
                'total_processados': len(clientes),
                'importados': len(self.clientes_importados),
                'detalhes': self.clientes_importados,
                'erros': self.erros
            }
            
        except Exception as e:
            logger.error(f"Erro na importação em massa: {e}")
            return {
                'success': False,
                'erro': str(e),
                'erros': self.erros
            }