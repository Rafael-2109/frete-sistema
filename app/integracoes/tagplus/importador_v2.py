"""
Importador TagPlus usando API v2 com OAuth2
"""

import logging
import re
from datetime import datetime
from app import db
from app.carteira.models import CadastroCliente
from app.faturamento.models import FaturamentoProduto
from app.integracoes.tagplus.oauth2_v2 import TagPlusOAuth2V2
from app.integracoes.tagplus.processador_faturamento_tagplus import ProcessadorFaturamentoTagPlus

logger = logging.getLogger(__name__)

class ImportadorTagPlusV2:
    """Importador que usa API v2 com OAuth2"""
    
    def __init__(self):
        # Cria gerenciadores OAuth2 para cada API
        self.oauth_clientes = TagPlusOAuth2V2(api_type='clientes')
        self.oauth_notas = TagPlusOAuth2V2(api_type='notas')
        
        # Processador de faturamento
        self.processador_faturamento = ProcessadorFaturamentoTagPlus()
        
        # Estatísticas
        self.stats = {
            'clientes': {'importados': 0, 'atualizados': 0, 'erros': []},
            'nfs': {'importadas': 0, 'itens': 0, 'erros': []},
            'processamento': None
        }
    
    def testar_conexoes(self):
        """Testa conexão com ambas as APIs"""
        resultado = {}
        
        # Testa API de Clientes
        try:
            sucesso, info = self.oauth_clientes.test_connection()
            resultado['clientes'] = {'sucesso': sucesso, 'info': info}
        except Exception as e:
            resultado['clientes'] = {'sucesso': False, 'info': str(e)}
        
        # Testa API de Notas
        try:
            sucesso, info = self.oauth_notas.test_connection()
            resultado['notas'] = {'sucesso': sucesso, 'info': info}
        except Exception as e:
            resultado['notas'] = {'sucesso': False, 'info': str(e)}
        
        return resultado
    
    def importar_clientes(self, limite=None):
        """Importa clientes usando API v2"""
        try:
            logger.info(f"📥 Importando clientes (limite: {limite or 'sem limite'})...")
            
            pagina = 1
            limite_por_pagina = 50
            total_importados = 0
            
            while True:
                # Faz requisição
                response = self.oauth_clientes.make_request(
                    'GET',
                    '/clientes',
                    params={
                        'pagina': pagina,
                        'limite': limite_por_pagina
                    }
                )
                
                if not response:
                    logger.error("Erro ao buscar clientes: sem resposta")
                    break
                
                if response.status_code == 401:
                    logger.error("Token expirado ou inválido. É necessário autorizar novamente.")
                    self.stats['clientes']['erros'].append("Não autorizado - faça login em /tagplus/oauth/")
                    break
                
                if response.status_code != 200:
                    logger.error(f"Erro ao buscar clientes: {response.status_code} - {response.text}")
                    break
                
                data = response.json()
                
                # API v2 retorna dados em formato diferente
                if isinstance(data, dict):
                    clientes = data.get('data', data.get('clientes', []))
                    tem_mais = data.get('has_more', False) or data.get('proxima_pagina')
                else:
                    clientes = data if isinstance(data, list) else []
                    tem_mais = len(clientes) == limite_por_pagina
                
                if not clientes:
                    logger.info("Não há mais clientes para importar")
                    break
                
                # Processa cada cliente
                for cliente_data in clientes:
                    try:
                        self._processar_cliente(cliente_data)
                        total_importados += 1
                        
                        if limite and total_importados >= limite:
                            break
                            
                    except Exception as e:
                        logger.error(f"Erro ao processar cliente: {e}")
                        self.stats['clientes']['erros'].append(str(e))
                
                # Verifica se deve continuar
                if limite and total_importados >= limite:
                    break
                
                if not tem_mais:
                    break
                
                pagina += 1
            
            # Commit
            db.session.commit()
            
            logger.info(f"✅ Importação concluída: {self.stats['clientes']}")
            return self.stats['clientes']
            
        except Exception as e:
            logger.error(f"❌ Erro na importação: {e}")
            db.session.rollback()
            self.stats['clientes']['erros'].append(str(e))
            return self.stats['clientes']
    
    def importar_nfs(self, data_inicio, data_fim, limite=None):
        """Importa NFs usando API v2"""
        try:
            logger.info(f"📥 Importando NFs de {data_inicio} até {data_fim}...")
            
            pagina = 1
            limite_por_pagina = 50
            total_nfs = 0
            nfs_para_processar = []
            
            while True:
                # Faz requisição
                response = self.oauth_notas.make_request(
                    'GET',
                    '/nfes',
                    params={
                        'pagina': pagina,
                        'limite': limite_por_pagina,
                        'data_emissao_inicio': data_inicio.strftime('%Y-%m-%d'),
                        'data_emissao_fim': data_fim.strftime('%Y-%m-%d'),
                        'status': 'autorizada'
                    }
                )
                
                if not response:
                    logger.error("Erro ao buscar NFs: sem resposta")
                    break
                
                if response.status_code == 401:
                    logger.error("Token expirado ou inválido. É necessário autorizar novamente.")
                    self.stats['nfs']['erros'].append("Não autorizado - faça login em /tagplus/oauth/")
                    break
                
                if response.status_code != 200:
                    logger.error(f"Erro ao buscar NFs: {response.status_code} - {response.text}")
                    break
                
                data = response.json()
                
                # API v2 retorna dados em formato diferente
                if isinstance(data, dict):
                    nfes = data.get('data', data.get('nfes', []))
                    tem_mais = data.get('has_more', False) or data.get('proxima_pagina')
                else:
                    nfes = data if isinstance(data, list) else []
                    tem_mais = len(nfes) == limite_por_pagina
                
                if not nfes:
                    logger.info("Não há mais NFs para importar")
                    break
                
                # Processa cada NF
                for nfe_resumo in nfes:
                    try:
                        # Busca detalhes se necessário
                        nfe_id = nfe_resumo.get('id') or nfe_resumo.get('numero')
                        nfe_detalhada = self._buscar_nfe_detalhada(nfe_id) if nfe_id else nfe_resumo
                        
                        if nfe_detalhada:
                            itens_criados = self._processar_nfe(nfe_detalhada)
                            if itens_criados:
                                nfs_para_processar.extend(itens_criados)
                                total_nfs += 1
                            
                            if limite and total_nfs >= limite:
                                break
                                
                    except Exception as e:
                        logger.error(f"Erro ao processar NF: {e}")
                        self.stats['nfs']['erros'].append(str(e))
                
                # Verifica se deve continuar
                if limite and total_nfs >= limite:
                    break
                
                if not tem_mais:
                    break
                
                pagina += 1
            
            # Commit das NFs
            db.session.commit()
            
            # Processa faturamento
            if nfs_para_processar:
                logger.info(f"📊 Processando {len(nfs_para_processar)} itens...")
                self.stats['processamento'] = self._processar_faturamento(nfs_para_processar)
            
            logger.info(f"✅ Importação concluída: {self.stats['nfs']}")
            return self.stats
            
        except Exception as e:
            logger.error(f"❌ Erro na importação: {e}")
            db.session.rollback()
            self.stats['nfs']['erros'].append(str(e))
            return self.stats
    
    def _processar_cliente(self, dados):
        """Processa um cliente"""
        # Extrai CNPJ/CPF
        cnpj = re.sub(r'\D', '', str(dados.get('cnpj', dados.get('cpf', ''))))
        
        if not cnpj:
            raise ValueError("Cliente sem CNPJ/CPF")
        
        # Verifica se já existe
        cliente = CadastroCliente.query.filter_by(cnpj_cpf=cnpj).first()
        
        if cliente:
            # Atualiza campos vazios
            campos_atualizados = 0
            
            if not cliente.email and dados.get('email'):
                cliente.email = dados.get('email')
                campos_atualizados += 1
            
            if not cliente.telefone_endereco_ent and dados.get('telefone'):
                cliente.telefone_endereco_ent = self._formatar_telefone(dados.get('telefone'))
                campos_atualizados += 1
            
            if campos_atualizados > 0:
                self.stats['clientes']['atualizados'] += 1
                logger.debug(f"Cliente {cnpj} atualizado")
        else:
            # Cria novo cliente
            cliente = CadastroCliente(
                cnpj_cpf=cnpj,
                raz_social=dados.get('razao_social', dados.get('nome', '')),
                raz_social_red=(dados.get('nome_fantasia', '') or dados.get('nome', ''))[:50],
                
                # Endereço
                cep_endereco_ent=dados.get('cep', ''),
                rua_endereco_ent=dados.get('logradouro', ''),
                endereco_ent=dados.get('numero', ''),
                bairro_endereco_ent=dados.get('bairro', ''),
                nome_cidade=dados.get('cidade', ''),
                municipio=dados.get('cidade', ''),
                estado=dados.get('uf', ''),
                cod_uf=dados.get('uf', ''),
                
                # Contato
                telefone_endereco_ent=self._formatar_telefone(dados.get('telefone', '')),
                email=dados.get('email', ''),
                
                # Endereço de entrega
                cnpj_endereco_ent=cnpj,
                empresa_endereco_ent=dados.get('razao_social', dados.get('nome', '')),
                
                # Controle
                origem='TagPlus',
                criado_em=datetime.utcnow()
            )
            
            db.session.add(cliente)
            self.stats['clientes']['importados'] += 1
            logger.debug(f"Cliente {cnpj} criado")
    
    def _buscar_nfe_detalhada(self, nfe_id):
        """Busca detalhes de uma NF"""
        try:
            response = self.oauth_notas.make_request('GET', f'/nfes/{nfe_id}')
            
            if response and response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Erro ao buscar NF {nfe_id}")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao buscar NF {nfe_id}: {e}")
            return None
    
    def _processar_nfe(self, nfe_data):
        """Processa uma NF e seus itens"""
        numero_nf = str(nfe_data.get('numero', ''))
        
        # Verifica se já existe
        existe = FaturamentoProduto.query.filter_by(numero_nf=numero_nf).first()
        if existe:
            logger.debug(f"NF {numero_nf} já existe")
            return []
        
        # Extrai cliente
        cliente_data = nfe_data.get('cliente', {})
        cnpj_cliente = re.sub(r'\D', '', str(cliente_data.get('cnpj', cliente_data.get('cpf', ''))))
        
        if not cnpj_cliente:
            raise ValueError(f"NF {numero_nf} sem CNPJ")
        
        # Busca ou cria cliente
        cliente = CadastroCliente.query.filter_by(cnpj_cpf=cnpj_cliente).first()
        if not cliente:
            self._processar_cliente(cliente_data)
            db.session.flush()
            cliente = CadastroCliente.query.filter_by(cnpj_cpf=cnpj_cliente).first()
        
        # Processa itens
        itens_criados = []
        for item in nfe_data.get('itens', []):
            try:
                faturamento = FaturamentoProduto(
                    numero_nf=numero_nf,
                    data_fatura=self._parse_data(nfe_data.get('data_emissao')),
                    
                    cnpj_cliente=cnpj_cliente,
                    nome_cliente=cliente.raz_social if cliente else '',
                    municipio=cliente.municipio if cliente else '',
                    estado=cliente.estado if cliente else '',
                    vendedor=cliente.vendedor if cliente else '',
                    equipe_vendas=cliente.equipe_vendas if cliente else '',
                    
                    cod_produto=str(item.get('codigo', '')),
                    nome_produto=item.get('descricao', ''),
                    qtd_produto_faturado=float(item.get('quantidade', 0)),
                    preco_produto_faturado=float(item.get('valor_unitario', 0)),
                    valor_produto_faturado=float(item.get('valor_total', 0)),
                    
                    peso_unitario_produto=float(item.get('peso_unitario', 0)),
                    peso_total=float(item.get('peso_total', 0)) or (
                        float(item.get('peso_unitario', 0)) * float(item.get('quantidade', 0))
                    ),
                    
                    origem=nfe_data.get('pedido', ''),
                    status_nf='Lançado',
                    
                    created_by='ImportTagPlus',
                    updated_by='ImportTagPlus'
                )
                
                db.session.add(faturamento)
                itens_criados.append(faturamento)
                self.stats['nfs']['itens'] += 1
                
            except Exception as e:
                logger.error(f"Erro no item da NF {numero_nf}: {e}")
                self.stats['nfs']['erros'].append(f"Item NF {numero_nf}: {str(e)}")
        
        if itens_criados:
            self.stats['nfs']['importadas'] += 1
            logger.debug(f"NF {numero_nf} importada com {len(itens_criados)} itens")
        
        return itens_criados
    
    def _processar_faturamento(self, itens_faturamento):
        """Processa faturamento dos itens"""
        try:
            for item in itens_faturamento:
                self.processador_faturamento.processar_nf_completo(item)
            
            db.session.commit()
            
            return {
                'success': True,
                'nfs_processadas': len(set(item.numero_nf for item in itens_faturamento)),
                'itens_processados': len(itens_faturamento),
                'movimentacoes_criadas': len(self.processador_faturamento.movimentacoes_criadas)
            }
            
        except Exception as e:
            logger.error(f"Erro no processamento: {e}")
            db.session.rollback()
            return {'success': False, 'erro': str(e)}
    
    def _formatar_telefone(self, telefone):
        """Formata telefone"""
        if not telefone:
            return ''
        return re.sub(r'[^\d\s\(\)]', '', str(telefone))[:20]
    
    def _parse_data(self, data_str):
        """Converte string para date"""
        if not data_str:
            return datetime.now().date()
        
        data_str = str(data_str).split('T')[0].split(' ')[0]
        
        for formato in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']:
            try:
                return datetime.strptime(data_str, formato).date()
            except:
                continue
        
        return datetime.now().date()