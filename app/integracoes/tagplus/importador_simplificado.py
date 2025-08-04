"""
Importador simplificado TagPlus - Clientes e Notas Fiscais
"""
import logging
from datetime import datetime
from app import db
from app.carteira.models import CadastroCliente
from app.faturamento.models import FaturamentoProduto
from app.integracoes.tagplus.processador_faturamento_tagplus import ProcessadorFaturamentoTagPlus
import re
import requests
import os

logger = logging.getLogger(__name__)

class ImportadorTagPlus:
    """Importador simplificado para TagPlus"""
    
    def __init__(self, usuario='rayssa', senha='A12345', api_key=None, client_id=None, client_secret=None, access_token=None, refresh_token=None):
        # Permite teste local com URL diferente
        if os.getenv('TAGPLUS_TEST_MODE') == 'local':
            self.base_url = os.getenv('TAGPLUS_TEST_URL', 'http://localhost:8080/api/v1')
        else:
            self.base_url = "https://api.tagplus.com.br/v1"
        
        # Tenta diferentes métodos de autenticação
        self.auth = None
        self.api_key = api_key
        self.usuario = usuario
        self.senha = senha
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = access_token
        self.refresh_token = refresh_token
        self._configurar_autenticacao()
        self.processador_faturamento = ProcessadorFaturamentoTagPlus()
        self.resultados = {
            'clientes': {'importados': 0, 'atualizados': 0, 'erros': []},
            'nfs': {'importadas': 0, 'erros': []},
            'produtos': {'importados': 0, 'erros': []}
        }
    
    def _configurar_autenticacao(self):
        """Configura o método de autenticação apropriado"""
        # Primeiro tenta Bearer Token com Access Token existente
        if (self.access_token or os.environ.get('TAGPLUS_ACCESS_TOKEN')):
            try:
                from app.integracoes.tagplus.auth_bearer import TagPlusAuthBearer
                self.auth = TagPlusAuthBearer(
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                    access_token=self.access_token or os.environ.get('TAGPLUS_ACCESS_TOKEN'),
                    refresh_token=self.refresh_token or os.environ.get('TAGPLUS_REFRESH_TOKEN')
                )
                sucesso, _ = self.auth.testar_conexao()
                if sucesso:
                    logger.info("Usando autenticação Bearer Token (OAuth2 com tokens)")
                    return
            except Exception as e:
                logger.warning(f"Bearer Token falhou: {e}")
        
        # Depois tenta API Key
        if self.api_key or os.environ.get('TAGPLUS_API_KEY'):
            try:
                from app.integracoes.tagplus.auth_api_key import TagPlusAuthAPIKey
                self.auth = TagPlusAuthAPIKey(self.api_key)
                sucesso, _ = self.auth.testar_conexao()
                if sucesso:
                    logger.info("Usando autenticação por API Key")
                    return
            except Exception as e:
                logger.warning(f"API Key falhou: {e}")
        
        # Por último, tenta OAuth2/usuário+senha
        try:
            from app.integracoes.tagplus.auth_simplificado import TagPlusAuthSimplificado
            self.auth = TagPlusAuthSimplificado(self.usuario, self.senha)
            logger.info("Usando autenticação OAuth2/usuário+senha")
        except Exception as e:
            logger.error(f"Nenhum método de autenticação funcionou: {e}")
            # Usa API Key como fallback
            from app.integracoes.tagplus.auth_api_key import TagPlusAuthAPIKey
            self.auth = TagPlusAuthAPIKey()
    
    def testar_conexao(self):
        """Testa se consegue conectar no TagPlus"""
        if not self.auth:
            return False, "Sistema de autenticação não configurado"
        return self.auth.testar_conexao()
    
    # ===== IMPORTAÇÃO DE CLIENTES =====
    
    def importar_clientes(self, limite=None):
        """Importa clientes do TagPlus para CadastroCliente"""
        try:
            logger.info("Iniciando importação de clientes TagPlus...")
            
            headers = self.auth.get_headers()
            params = {'page': 1, 'per_page': 100}
            
            total_processados = 0
            
            while True:
                # Busca página de clientes
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
                
                if not clientes:
                    break
                
                # Processa cada cliente
                for cliente_tagplus in clientes:
                    try:
                        self._processar_cliente(cliente_tagplus)
                        total_processados += 1
                        
                        if limite and total_processados >= limite:
                            break
                    except Exception as e:
                        logger.error(f"Erro ao processar cliente: {e}")
                        self.resultados['clientes']['erros'].append(str(e))
                
                # Verifica se deve parar
                if limite and total_processados >= limite:
                    break
                
                # Próxima página
                if not data.get('has_more', False):
                    break
                    
                params['page'] += 1
            
            # Commit final
            db.session.commit()
            
            logger.info(f"Importação de clientes concluída: {self.resultados['clientes']}")
            return self.resultados['clientes']
            
        except Exception as e:
            logger.error(f"Erro geral na importação de clientes: {e}")
            db.session.rollback()
            self.resultados['clientes']['erros'].append(str(e))
            return self.resultados['clientes']
    
    def _processar_cliente(self, dados):
        """Processa um cliente do TagPlus"""
        # Extrai e limpa CNPJ
        cnpj = re.sub(r'\D', '', str(dados.get('cnpj', dados.get('cpf', ''))))
        
        if not cnpj:
            raise ValueError("Cliente sem CNPJ/CPF")
        
        # Verifica se já existe
        cliente = CadastroCliente.query.filter_by(cnpj_cpf=cnpj).first()
        
        if cliente:
            # Atualiza campos vazios
            self._atualizar_cliente(cliente, dados)
            self.resultados['clientes']['atualizados'] += 1
        else:
            # Cria novo
            self._criar_cliente(dados, cnpj)
            self.resultados['clientes']['importados'] += 1
    
    def _criar_cliente(self, dados, cnpj):
        """Cria novo cliente"""
        cliente = CadastroCliente(
            # Identificação
            cnpj_cpf=cnpj,
            raz_social=dados.get('razao_social', dados.get('nome', '')),
            raz_social_red=(dados.get('nome_fantasia', '') or dados.get('nome', ''))[:50],
            
            # Endereço
            cep_endereco_ent=dados.get('cep', ''),
            rua_endereco_ent=dados.get('logradouro', ''),
            endereco_ent=f"{dados.get('logradouro', '')}, {dados.get('numero', '')}",
            bairro_endereco_ent=dados.get('bairro', ''),
            nome_cidade=dados.get('cidade', ''),
            municipio=dados.get('cidade', ''),
            estado=dados.get('uf', ''),
            cod_uf=dados.get('uf', ''),
            
            # Contato
            telefone_endereco_ent=self._formatar_telefone(dados.get('telefone', '')),
            email=dados.get('email', ''),
            
            # Endereço de entrega (copia do principal)
            cnpj_endereco_ent=cnpj,
            empresa_endereco_ent=dados.get('razao_social', dados.get('nome', '')),
            
            # Defaults obrigatórios
            vendedor='A DEFINIR',
            equipe_vendas='GERAL',
            cliente_ativo=dados.get('ativo', True),
            
            # Controle
            created_by='ImportTagPlus',
            updated_by='ImportTagPlus',
            observacoes=f"Importado do TagPlus - ID: {dados.get('id', '')}"
        )
        
        db.session.add(cliente)
        logger.info(f"Cliente {cliente.raz_social} criado")
    
    def _atualizar_cliente(self, cliente, dados):
        """Atualiza apenas campos vazios do cliente"""
        # Atualiza apenas se estiver vazio
        if not cliente.email and dados.get('email'):
            cliente.email = dados.get('email', '')
        
        if not cliente.telefone_endereco_ent and dados.get('telefone'):
            cliente.telefone_endereco_ent = self._formatar_telefone(dados.get('telefone', ''))
        
        if not cliente.cep_endereco_ent and dados.get('cep'):
            cliente.cep_endereco_ent = dados.get('cep', '')
            cliente.rua_endereco_ent = dados.get('logradouro', '')
            cliente.endereco_ent = f"{dados.get('logradouro', '')}, {dados.get('numero', '')}"
            cliente.bairro_endereco_ent = dados.get('bairro', '')
            cliente.nome_cidade = dados.get('cidade', '')
            cliente.municipio = dados.get('cidade', '')
            cliente.estado = dados.get('uf', '')
            cliente.cod_uf = dados.get('uf', '')
        
        # Adiciona ID TagPlus se não tiver
        if cliente.observacoes and 'TagPlus' not in cliente.observacoes:
            cliente.observacoes += f"\nImportado do TagPlus - ID: {dados.get('id', '')}"
        elif not cliente.observacoes:
            cliente.observacoes = f"Importado do TagPlus - ID: {dados.get('id', '')}"
        
        cliente.updated_by = 'ImportTagPlus'
        cliente.updated_at = datetime.utcnow()
        
        logger.info(f"Cliente {cliente.raz_social} atualizado")
    
    def _formatar_telefone(self, telefone):
        """Formata telefone removendo caracteres especiais"""
        if not telefone:
            return ''
        # Remove tudo exceto números, espaços e parênteses
        return re.sub(r'[^\d\s\(\)]', '', str(telefone))
    
    # ===== IMPORTAÇÃO DE NOTAS FISCAIS =====
    
    def importar_nfs(self, data_inicio, data_fim, limite_nfs=500):
        """Importa NFs de um período para FaturamentoProduto (limitado a 500 por padrão)"""
        try:
            logger.info(f"Importando NFs de {data_inicio} até {data_fim} (limite: {limite_nfs})...")
            
            headers = self.auth.get_headers()
            params = {
                'page': 1,
                'per_page': 50,
                'data_emissao_inicio': data_inicio.strftime('%Y-%m-%d'),
                'data_emissao_fim': data_fim.strftime('%Y-%m-%d'),
                'status': 'autorizada',  # Apenas NFs autorizadas
                'order': 'desc'  # Mais recentes primeiro
            }
            
            nfs_processadas = 0
            
            while True:
                # Busca página de NFs
                response = requests.get(
                    f"{self.base_url}/nfes",
                    headers=headers,
                    params=params
                )
                
                if response.status_code != 200:
                    logger.error(f"Erro ao buscar NFs: {response.text}")
                    break
                
                data = response.json()
                nfes = data.get('data', [])
                
                if not nfes:
                    break
                
                # Processa cada NF
                for nfe in nfes:
                    try:
                        # Verifica limite
                        if nfs_processadas >= limite_nfs:
                            logger.info(f"Limite de {limite_nfs} NFs atingido")
                            break
                            
                        # Busca detalhes completos da NF
                        nfe_detalhada = self._buscar_nfe_detalhada(nfe['id'])
                        if nfe_detalhada:
                            self._processar_nfe(nfe_detalhada)
                            nfs_processadas += 1
                    except Exception as e:
                        logger.error(f"Erro ao processar NF {nfe.get('numero')}: {e}")
                        self.resultados['nfs']['erros'].append(str(e))
                
                # Verifica se deve parar
                if nfs_processadas >= limite_nfs:
                    break
                
                # Próxima página
                if not data.get('has_more', False):
                    break
                    
                params['page'] += 1
            
            # Commit final
            db.session.commit()
            
            # Processa faturamento (movimentações, consolidação, etc)
            logger.info("Processando faturamento das NFs importadas...")
            resultado_processamento = self.processador_faturamento.processar_lote_nfs()
            
            logger.info(f"Importação de NFs concluída: {self.resultados}")
            
            # Adiciona resultado do processamento
            self.resultados['processamento'] = resultado_processamento
            
            return self.resultados
            
        except Exception as e:
            logger.error(f"Erro geral na importação de NFs: {e}")
            db.session.rollback()
            self.resultados['nfs']['erros'].append(str(e))
            return self.resultados
    
    def _buscar_nfe_detalhada(self, nfe_id):
        """Busca detalhes completos de uma NF"""
        try:
            headers = self.auth.get_headers()
            response = requests.get(
                f"{self.base_url}/nfes/{nfe_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Erro ao buscar detalhes da NF {nfe_id}")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao buscar NF {nfe_id}: {e}")
            return None
    
    def _processar_nfe(self, nfe):
        """Processa uma NF e seus itens"""
        # Extrai dados básicos
        numero_nf = str(nfe.get('numero', ''))
        
        # Verifica se já existe
        existe = FaturamentoProduto.query.filter_by(numero_nf=numero_nf).first()
        if existe:
            logger.info(f"NF {numero_nf} já existe, pulando...")
            return
        
        # Busca ou cria cliente
        cliente_data = nfe.get('cliente', {})
        cnpj_cliente = re.sub(r'\D', '', str(cliente_data.get('cnpj', cliente_data.get('cpf', ''))))
        
        if not cnpj_cliente:
            raise ValueError(f"NF {numero_nf} sem CNPJ do cliente")
        
        # Verifica se cliente existe
        cliente = CadastroCliente.query.filter_by(cnpj_cpf=cnpj_cliente).first()
        if not cliente:
            # Cria cliente básico
            self._criar_cliente(cliente_data, cnpj_cliente)
            db.session.flush()
            cliente = CadastroCliente.query.filter_by(cnpj_cpf=cnpj_cliente).first()
        
        # Processa cada item da NF
        for item in nfe.get('itens', []):
            try:
                self._criar_item_faturamento(nfe, item, cliente)
                self.resultados['produtos']['importados'] += 1
            except Exception as e:
                logger.error(f"Erro ao processar item da NF {numero_nf}: {e}")
                self.resultados['produtos']['erros'].append(str(e))
        
        self.resultados['nfs']['importadas'] += 1
        logger.info(f"NF {numero_nf} importada com {len(nfe.get('itens', []))} itens")
    
    def _criar_item_faturamento(self, nfe, item, cliente):
        """Cria registro em FaturamentoProduto para cada item da NF"""
        # Extrai dados do item
        faturamento = FaturamentoProduto(
            # Dados da NF
            numero_nf=str(nfe.get('numero', '')),
            data_fatura=self._parse_data(nfe.get('data_emissao')),
            
            # Dados do cliente
            cnpj_cliente=cliente.cnpj_cpf,
            nome_cliente=cliente.raz_social,
            municipio=cliente.municipio,
            estado=cliente.estado,
            vendedor=cliente.vendedor,
            equipe_vendas=cliente.equipe_vendas,
            
            # Dados do produto
            cod_produto=str(item.get('codigo', '')),
            nome_produto=item.get('descricao', ''),
            qtd_produto_faturado=float(item.get('quantidade', 0)),
            preco_produto_faturado=float(item.get('valor_unitario', 0)),
            valor_produto_faturado=float(item.get('valor_total', 0)),
            
            # Peso (se disponível)
            peso_unitario_produto=float(item.get('peso_unitario', 0)),
            peso_total=float(item.get('peso_total', 0)) or (
                float(item.get('peso_unitario', 0)) * float(item.get('quantidade', 0))
            ),
            
            # Origem - número do pedido se disponível
            origem=nfe.get('pedido', ''),
            
            # Status
            status_nf='Lançado',  # NF autorizada no TagPlus
            
            # Controle
            created_by='ImportTagPlus',
            updated_by='ImportTagPlus'
        )
        
        db.session.add(faturamento)
    
    def _parse_data(self, data_str):
        """Converte string de data para objeto date"""
        if not data_str:
            return datetime.now().date()
        
        # Remove hora se existir
        data_str = str(data_str).split('T')[0].split(' ')[0]
        
        # Tenta diferentes formatos
        for formato in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']:
            try:
                return datetime.strptime(data_str, formato).date()
            except:
                continue
        
        logger.warning(f"Não foi possível converter data: {data_str}")
        return datetime.now().date()
    
    def gerar_relatorio(self):
        """Gera relatório resumido da importação"""
        return {
            'sucesso': True,
            'clientes': {
                'novos': self.resultados['clientes']['importados'],
                'atualizados': self.resultados['clientes']['atualizados'],
                'erros': len(self.resultados['clientes']['erros'])
            },
            'notas_fiscais': {
                'importadas': self.resultados['nfs']['importadas'],
                'itens_importados': self.resultados['produtos']['importados'],
                'erros': len(self.resultados['nfs']['erros'])
            },
            'detalhes_erros': {
                'clientes': self.resultados['clientes']['erros'][:10],  # Primeiros 10 erros
                'nfs': self.resultados['nfs']['erros'][:10]
            }
        }