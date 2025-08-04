"""
Serviço para importar Notas Fiscais do TagPlus
"""
import requests
import logging
from datetime import datetime
from app import db
from app.faturamento.models import NotaFiscal, ItemNotaFiscal
from app.carteira.models import CadastroCliente, CarteiraPrincipal
from app.integracoes.tagplus.auth import TagPlusAuth
import re

logger = logging.getLogger(__name__)

class TagPlusNFService:
    """Serviço para importar e sincronizar Notas Fiscais do TagPlus"""
    
    def __init__(self, auth_manager=None):
        self.auth = auth_manager or TagPlusAuth()
        self.base_url = "https://api.tagplus.com.br/v1"
        self.nfs_importadas = []
        self.erros = []
    
    def listar_nfes(self, filtros=None):
        """Lista NFEs do TagPlus com filtros opcionais"""
        try:
            headers = self.auth.get_headers()
            
            # Parâmetros de busca
            params = {
                'page': 1,
                'per_page': 100
            }
            
            if filtros:
                params.update(filtros)
            
            todas_nfes = []
            
            while True:
                response = requests.get(
                    f"{self.base_url}/nfes",
                    headers=headers,
                    params=params
                )
                
                if response.status_code != 200:
                    logger.error(f"Erro ao buscar NFEs: {response.text}")
                    break
                
                data = response.json()
                nfes = data.get('data', [])
                todas_nfes.extend(nfes)
                
                # Verifica se há mais páginas
                if not data.get('has_more', False):
                    break
                
                params['page'] += 1
            
            logger.info(f"Total de NFEs encontradas: {len(todas_nfes)}")
            return todas_nfes
            
        except Exception as e:
            logger.error(f"Erro ao listar NFEs TagPlus: {e}")
            self.erros.append(str(e))
            return []
    
    def buscar_nfe_detalhada(self, nfe_id):
        """Busca detalhes completos de uma NFE"""
        try:
            headers = self.auth.get_headers()
            
            response = requests.get(
                f"{self.base_url}/nfes/{nfe_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Erro ao buscar NFE {nfe_id}: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao buscar detalhes da NFE: {e}")
            return None
    
    def importar_nfe(self, nfe_tagplus):
        """Importa uma NFE do TagPlus para o sistema"""
        try:
            # Busca detalhes completos se necessário
            if not nfe_tagplus.get('itens'):
                nfe_detalhada = self.buscar_nfe_detalhada(nfe_tagplus['id'])
                if nfe_detalhada:
                    nfe_tagplus = nfe_detalhada
            
            # Extrai dados básicos
            numero_nf = nfe_tagplus.get('numero')
            serie = nfe_tagplus.get('serie', '1')
            chave_acesso = nfe_tagplus.get('chave_acesso', '')
            
            # Verifica se já existe
            nf_existente = NotaFiscal.query.filter_by(
                numero=numero_nf,
                serie=serie
            ).first()
            
            if nf_existente:
                logger.info(f"NF {numero_nf} já existe no sistema")
                return nf_existente
            
            # Busca ou cria cliente
            cliente = self._buscar_criar_cliente(nfe_tagplus.get('cliente', {}))
            if not cliente:
                self.erros.append(f"Cliente não encontrado para NF {numero_nf}")
                return None
            
            # Cria a nota fiscal
            return self._criar_nota_fiscal(nfe_tagplus, cliente)
            
        except Exception as e:
            logger.error(f"Erro ao importar NFE: {e}")
            self.erros.append(f"Erro ao importar NF {nfe_tagplus.get('numero')}: {str(e)}")
            return None
    
    def _buscar_criar_cliente(self, dados_cliente):
        """Busca cliente ou cria se não existir"""
        try:
            cnpj = re.sub(r'\D', '', str(dados_cliente.get('cnpj', '')))
            
            if not cnpj:
                return None
            
            # Busca cliente existente
            cliente = CadastroCliente.query.filter_by(
                cnpj_cpf=cnpj
            ).first()
            
            if not cliente:
                # Cria cliente básico
                cliente = CadastroCliente(
                    cnpj_cpf=cnpj,
                    raz_social=dados_cliente.get('razao_social', dados_cliente.get('nome', '')),
                    raz_social_red=dados_cliente.get('nome_fantasia', '')[:50] if dados_cliente.get('nome_fantasia') else '',
                    municipio=dados_cliente.get('cidade', ''),
                    estado=dados_cliente.get('uf', ''),
                    cod_uf=dados_cliente.get('uf', ''),
                    vendedor='A DEFINIR',
                    equipe_vendas='GERAL',
                    cliente_ativo=True,
                    created_by='ImportNFTagPlus',
                    updated_by='ImportNFTagPlus'
                )
                
                db.session.add(cliente)
                db.session.commit()
                
                logger.info(f"Cliente {cliente.raz_social} criado automaticamente")
            
            return cliente
            
        except Exception as e:
            logger.error(f"Erro ao buscar/criar cliente: {e}")
            return None
    
    def _criar_nota_fiscal(self, dados_nf, cliente):
        """Cria nota fiscal no sistema"""
        try:
            # Mapeia dados da NF
            nota_fiscal = NotaFiscal(
                # Identificação
                numero=dados_nf.get('numero'),
                serie=dados_nf.get('serie', '1'),
                chave_acesso=dados_nf.get('chave_acesso', ''),
                
                # Datas
                data_emissao=self._parse_data(dados_nf.get('data_emissao')),
                data_saida=self._parse_data(dados_nf.get('data_saida')),
                
                # Cliente
                cliente_id=cliente.id,
                cnpj_cliente=cliente.cnpj_cpf,
                
                # Valores
                valor_total=float(dados_nf.get('valor_total', 0)),
                valor_produtos=float(dados_nf.get('valor_produtos', 0)),
                valor_frete=float(dados_nf.get('valor_frete', 0)),
                valor_desconto=float(dados_nf.get('valor_desconto', 0)),
                
                # Status
                status='AUTORIZADA' if dados_nf.get('autorizada') else 'PENDENTE',
                
                # Transporte
                transportadora=dados_nf.get('transportadora', {}).get('nome', ''),
                
                # Controle
                origem='TagPlus',
                id_origem=str(dados_nf.get('id', '')),
                created_by='ImportTagPlus',
                updated_by='ImportTagPlus'
            )
            
            db.session.add(nota_fiscal)
            db.session.flush()  # Para obter o ID
            
            # Importa itens da NF
            for item_data in dados_nf.get('itens', []):
                self._criar_item_nf(nota_fiscal.id, item_data)
            
            db.session.commit()
            
            self.nfs_importadas.append({
                'numero': nota_fiscal.numero,
                'serie': nota_fiscal.serie,
                'cliente': cliente.raz_social,
                'valor': nota_fiscal.valor_total
            })
            
            logger.info(f"NF {nota_fiscal.numero} importada com sucesso")
            return nota_fiscal
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao criar nota fiscal: {e}")
            raise
    
    def _criar_item_nf(self, nf_id, item_data):
        """Cria item da nota fiscal"""
        try:
            item = ItemNotaFiscal(
                nota_fiscal_id=nf_id,
                
                # Produto
                codigo_produto=item_data.get('codigo', ''),
                descricao_produto=item_data.get('descricao', ''),
                ncm=item_data.get('ncm', ''),
                cfop=item_data.get('cfop', ''),
                unidade=item_data.get('unidade', 'UN'),
                
                # Quantidades e valores
                quantidade=float(item_data.get('quantidade', 0)),
                valor_unitario=float(item_data.get('valor_unitario', 0)),
                valor_total=float(item_data.get('valor_total', 0)),
                
                # Impostos (simplificado)
                valor_icms=float(item_data.get('icms', {}).get('valor', 0)),
                valor_ipi=float(item_data.get('ipi', {}).get('valor', 0)),
                valor_pis=float(item_data.get('pis', {}).get('valor', 0)),
                valor_cofins=float(item_data.get('cofins', {}).get('valor', 0))
            )
            
            db.session.add(item)
            
        except Exception as e:
            logger.error(f"Erro ao criar item NF: {e}")
            raise
    
    def _parse_data(self, data_str):
        """Converte string de data para objeto datetime"""
        if not data_str:
            return None
        
        try:
            # Tenta diferentes formatos
            for formato in ['%Y-%m-%d', '%d/%m/%Y', '%Y-%m-%dT%H:%M:%S']:
                try:
                    return datetime.strptime(data_str[:10], formato).date()
                except:
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao converter data {data_str}: {e}")
            return None
    
    def importar_nfes_periodo(self, data_inicio, data_fim):
        """Importa NFEs de um período específico"""
        try:
            filtros = {
                'data_emissao_inicio': data_inicio.strftime('%Y-%m-%d'),
                'data_emissao_fim': data_fim.strftime('%Y-%m-%d'),
                'autorizada': True  # Apenas notas autorizadas
            }
            
            nfes = self.listar_nfes(filtros)
            
            for nfe_tagplus in nfes:
                try:
                    self.importar_nfe(nfe_tagplus)
                except Exception as e:
                    logger.error(f"Erro ao importar NF {nfe_tagplus.get('numero')}: {e}")
                    continue
            
            return {
                'success': True,
                'total_processadas': len(nfes),
                'importadas': len(self.nfs_importadas),
                'detalhes': self.nfs_importadas,
                'erros': self.erros
            }
            
        except Exception as e:
            logger.error(f"Erro na importação de NFEs: {e}")
            return {
                'success': False,
                'erro': str(e),
                'erros': self.erros
            }
    
    def vincular_nf_pedidos(self, nota_fiscal):
        """Tenta vincular NF com pedidos da carteira"""
        try:
            # Busca pedidos do cliente na carteira
            pedidos = CarteiraPrincipal.query.filter_by(
                cnpj_cpf=nota_fiscal.cnpj_cliente,
                status_pedido='Pedido de venda'
            ).all()
            
            if not pedidos:
                logger.info(f"Nenhum pedido encontrado para vincular à NF {nota_fiscal.numero}")
                return
            
            # Aqui você pode implementar a lógica de vinculação
            # Por exemplo, comparar produtos, quantidades, etc.
            
            logger.info(f"Encontrados {len(pedidos)} pedidos para possível vinculação")
            
        except Exception as e:
            logger.error(f"Erro ao vincular NF com pedidos: {e}")