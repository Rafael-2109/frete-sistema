"""
Serviço de Faturamento Odoo
===========================

Serviço responsável por gerenciar a consulta de dados de faturamento
do Odoo ERP. Foca apenas na consulta de faturamento por produto.

Funcionalidades:
- Importação de faturamento por produto
- Filtro por período e NFs específicas
- Estatísticas básicas

Autor: Sistema de Fretes
Data: 2025-07-14
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, date
from decimal import Decimal

from app.odoo.utils.connection import get_odoo_connection

logger = logging.getLogger(__name__)

class FaturamentoService:
    """Serviço para gerenciar faturamento do Odoo"""
    
    def __init__(self):
        self.connection = get_odoo_connection()
    
    def obter_faturamento_produtos(self, data_inicio: Optional[date] = None, data_fim: Optional[date] = None, 
                                  nfs_especificas: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Obtém faturamento por produto do Odoo baseado nos campos definidos em campos_faturamento.md
        
        Args:
            data_inicio: Data início do período
            data_fim: Data fim do período
            nfs_especificas: Lista de NFs específicas
            
        Returns:
            Dict com dados do faturamento por produto
        """
        try:
            # Construir domínio de busca
            domain = self._build_faturamento_domain(data_inicio, data_fim, nfs_especificas)
            
            # Campos baseados em campos_faturamento.md
            fields = [
                'invoice_line_ids/x_studio_nf_e',  # NF-e
                'invoice_line_ids/partner_id/l10n_br_cnpj',  # CNPJ Parceiro
                'invoice_line_ids/partner_id',  # Parceiro
                'invoice_line_ids/partner_id/l10n_br_municipio_id',  # Município
                'invoice_line_ids/invoice_origin',  # Origem
                'state',  # Status
                'invoice_line_ids/product_id/code',  # Referência Produto
                'invoice_line_ids/product_id/name',  # Nome Produto
                'invoice_line_ids/quantity',  # Quantidade
                'invoice_line_ids/l10n_br_total_nfe',  # Valor Total do Item da NF
                'invoice_line_ids/date',  # Data
                'invoice_incoterm_id',  # Incoterm
                'invoice_user_id',  # Vendedor
                'invoice_line_ids/product_id/gross_weight'  # Peso bruto (peso unitário)
            ]
            
            # Buscar dados do Odoo
            logger.info(f"Buscando faturamento por produto do Odoo...")
            odoo_data = self.connection.search_read(
                'account.move.line',
                domain=domain,
                fields=fields,
                limit=5000
            )
            
            logger.info(f"Encontrados {len(odoo_data)} registros no Odoo")
            
            if not odoo_data:
                return {
                    'sucesso': True,
                    'mensagem': 'Nenhum faturamento encontrado no período especificado',
                    'dados': [],
                    'total_registros': 0,
                    'estatisticas': self._calcular_estatisticas([])
                }
            
            # Processar dados
            dados_processados = self._processar_dados_faturamento(odoo_data)
            
            return {
                'sucesso': True,
                'mensagem': f'Faturamento por produto obtido com sucesso',
                'dados': dados_processados,
                'total_registros': len(dados_processados),
                'estatisticas': self._calcular_estatisticas(dados_processados)
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter faturamento por produto: {e}")
            raise
    
    def _build_faturamento_domain(self, data_inicio: Optional[date] = None, data_fim: Optional[date] = None, 
                                 nfs_especificas: Optional[List[str]] = None) -> List:
        """Constrói domínio de busca para faturamento com filtro específico"""
        # Filtro principal: venda OU bonificação
        domain = [
            '|',
            ('l10n_br_tipo_pedido', '=', 'venda'),
            ('l10n_br_tipo_pedido', '=', 'bonificacao')
        ]
        
        if data_inicio:
            domain.append(('invoice_line_ids/date', '>=', data_inicio.strftime('%Y-%m-%d')))
        
        if data_fim:
            domain.append(('invoice_line_ids/date', '<=', data_fim.strftime('%Y-%m-%d')))
        
        if nfs_especificas:
            domain.append(('invoice_line_ids/x_studio_nf_e', 'in', nfs_especificas))
        
        return domain
    
    def _processar_dados_faturamento(self, odoo_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Processa dados de faturamento do Odoo"""
        dados_processados = []
        
        for item in odoo_data:
            try:
                # Processar cada item do faturamento
                item_processado = {
                    'numero_nf': self._extract_value(item, 'invoice_line_ids/x_studio_nf_e'),
                    'cnpj_cliente': self._extract_value(item, 'invoice_line_ids/partner_id/l10n_br_cnpj'),
                    'nome_cliente': self._extract_relational_field(item, 'invoice_line_ids/partner_id'),
                    'municipio': self._extract_relational_field(item, 'invoice_line_ids/partner_id/l10n_br_municipio_id'),
                    'origem': self._extract_value(item, 'invoice_line_ids/invoice_origin'),
                    'status': self._extract_value(item, 'state'),
                    'codigo_produto': self._extract_value(item, 'invoice_line_ids/product_id/code'),
                    'nome_produto': self._extract_value(item, 'invoice_line_ids/product_id/name'),
                    'quantidade': self._format_decimal(item.get('invoice_line_ids/quantity')),
                    'valor_total_item': self._format_decimal(item.get('invoice_line_ids/l10n_br_total_nfe')),
                    'data_fatura': self._format_date(item.get('invoice_line_ids/date')),
                    'incoterm': self._extract_relational_field(item, 'invoice_incoterm_id'),
                    'vendedor': self._extract_relational_field(item, 'invoice_user_id'),
                    'peso_unitario_produto': self._format_decimal(item.get('invoice_line_ids/product_id/gross_weight'))
                }
                
                # Calcular campos adicionais
                if item_processado['quantidade'] > 0 and item_processado['valor_total_item'] > 0:
                    item_processado['preco_unitario'] = item_processado['valor_total_item'] / item_processado['quantidade']
                else:
                    item_processado['preco_unitario'] = 0.0
                
                # Calcular peso total
                if item_processado['peso_unitario_produto'] > 0 and item_processado['quantidade'] > 0:
                    item_processado['peso_total'] = item_processado['peso_unitario_produto'] * item_processado['quantidade']
                else:
                    item_processado['peso_total'] = 0.0
                
                # Adicionar apenas se tem dados válidos
                if item_processado['numero_nf'] and item_processado['codigo_produto']:
                    dados_processados.append(item_processado)
                    
            except Exception as e:
                logger.error(f"Erro ao processar item do faturamento: {e}")
                continue
        
        return dados_processados
    
    def _extract_value(self, data: Dict[str, Any], field: str) -> str:
        """Extrai valor simples de um campo"""
        value = data.get(field)
        if value is None:
            return ''
        return str(value)
    
    def _extract_relational_field(self, data: Dict[str, Any], field: str) -> str:
        """Extrai valor de campo relacional [id, name]"""
        value = data.get(field)
        if isinstance(value, list) and len(value) >= 2:
            return str(value[1])  # Retorna o nome
        return str(value) if value else ''
    
    def _format_date(self, date_value) -> str:
        """Formata data para string"""
        if not date_value:
            return ''
        
        if isinstance(date_value, str):
            try:
                dt = datetime.strptime(date_value, '%Y-%m-%d %H:%M:%S')
                return dt.strftime('%d/%m/%Y')
            except ValueError:
                try:
                    dt = datetime.strptime(date_value, '%Y-%m-%d')
                    return dt.strftime('%d/%m/%Y')
                except ValueError:
                    return str(date_value)
        return str(date_value)
    
    def _format_decimal(self, value) -> float:
        """Formata valor decimal"""
        if value is None:
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0
    
    def _calcular_estatisticas(self, dados: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calcula estatísticas básicas do faturamento"""
        if not dados:
            return {
                'total_itens': 0,
                'total_nfs': 0,
                'total_produtos': 0,
                'valor_total': 0.0,
                'quantidade_total': 0.0,
                'peso_total': 0.0
            }
        
        # Calcular estatísticas
        total_itens = len(dados)
        nfs_unicas = len(set(item['numero_nf'] for item in dados))
        produtos_unicos = len(set(item['codigo_produto'] for item in dados))
        valor_total = sum(item['valor_total_item'] for item in dados)
        quantidade_total = sum(item['quantidade'] for item in dados)
        peso_total = sum(item['peso_total'] for item in dados)
        
        return {
            'total_itens': total_itens,
            'total_nfs': nfs_unicas,
            'total_produtos': produtos_unicos,
            'valor_total': valor_total,
            'quantidade_total': quantidade_total,
            'peso_total': peso_total
        }
    
    def consolidar_para_relatorio(self, dados: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Consolida dados de faturamento por produto para formato de relatório
        
        Args:
            dados: Lista de dados de faturamento por produto
            
        Returns:
            Lista de dados consolidados por NF
        """
        if not dados:
            return []
        
        # Agrupar por NF
        nfs_agrupadas = {}
        for item in dados:
            nf = item['numero_nf']
            if nf not in nfs_agrupadas:
                nfs_agrupadas[nf] = []
            nfs_agrupadas[nf].append(item)
        
        # Consolidar cada NF
        dados_consolidados = []
        for nf, itens in nfs_agrupadas.items():
            if not itens:
                continue
                
            # Usar dados do primeiro item como base
            primeiro_item = itens[0]
            
            # Consolidar valores
            consolidado = {
                'numero_nf': nf,
                'data_fatura': primeiro_item['data_fatura'],
                'cnpj_cliente': primeiro_item['cnpj_cliente'],
                'nome_cliente': primeiro_item['nome_cliente'],
                'municipio': primeiro_item['municipio'],
                'origem': primeiro_item['origem'],
                'status': primeiro_item['status'],
                'incoterm': primeiro_item['incoterm'],
                'vendedor': primeiro_item['vendedor'],
                'valor_total': sum(item['valor_total_item'] for item in itens),
                'peso_bruto': sum(item['peso_total'] for item in itens),
                'quantidade_itens': len(itens),
                'produtos': [{'codigo': item['codigo_produto'], 'nome': item['nome_produto']} for item in itens]
            }
            
            dados_consolidados.append(consolidado)
        
        return dados_consolidados 

def sincronizar_faturamento_odoo(usar_filtro_venda_bonificacao=True):
    """
    Sincroniza faturamento do Odoo para FaturamentoProduto e RelatorioFaturamentoImportado
    
    Args:
        usar_filtro_venda_bonificacao (bool): Se deve usar filtro para venda/bonificação
    
    Returns:
        dict: Estatísticas da sincronização
    """
    try:
        from app.faturamento.models import FaturamentoProduto, RelatorioFaturamentoImportado
        from app.localidades.models import Cidade
        from app import db
        from flask_login import current_user
        from datetime import datetime
        import logging
        
        logger = logging.getLogger(__name__)
        
        # Criar instância do serviço para chamar método
        service = FaturamentoService()
        
        # Buscar dados do Odoo
        dados_odoo = service.obter_faturamento_produtos()
        
        if not dados_odoo:
            return {
                'sucesso': False,
                'erro': 'Nenhum dado encontrado no Odoo',
                'produtos_importados': 0,
                'produtos_atualizados': 0,
                'nfs_consolidadas': 0
            }
        
        # Filtrar apenas registros com numero_nf preenchido
        dados_filtrados = [
            item for item in dados_odoo 
            if item.get('numero_nf') and str(item.get('numero_nf')).strip() != ''
        ]
        
        if not dados_filtrados:
            return {
                'sucesso': False,
                'erro': 'Nenhum registro com número de NF encontrado',
                'produtos_importados': 0,
                'produtos_atualizados': 0,
                'nfs_consolidadas': 0
            }
        
        # Aplicar filtro de venda/bonificação se solicitado
        if usar_filtro_venda_bonificacao:
            dados_filtrados = [
                item for item in dados_filtrados
                if item.get('tipo_pedido') in ['venda', 'bonificacao']
            ]
        
        produtos_importados = 0
        produtos_atualizados = 0
        nfs_consolidadas = 0
        erros = []
        
        # Processar cada produto
        for item in dados_filtrados:
            try:
                # Validar campos obrigatórios
                numero_nf = str(item.get('numero_nf', '')).strip()
                cod_produto = str(item.get('cod_produto', '')).strip()
                
                if not numero_nf or not cod_produto:
                    continue
                
                # Verificar se produto já existe
                produto_existente = FaturamentoProduto.query.filter_by(
                    numero_nf=numero_nf,
                    cod_produto=cod_produto
                ).first()
                
                # Processar data
                data_fatura = None
                if item.get('data_fatura'):
                    try:
                        if isinstance(item['data_fatura'], str):
                            data_fatura = datetime.strptime(item['data_fatura'], '%Y-%m-%d').date()
                        else:
                            data_fatura = item['data_fatura']
                    except:
                        pass
                
                # Processar valores
                qtd_produto = float(item.get('qtd_produto_faturado', 0)) or 0
                valor_produto = float(item.get('valor_produto_faturado', 0)) or 0
                peso_unitario = float(item.get('peso_unitario_produto', 0)) or 0
                
                # Calcular preço unitário
                preco_unitario = valor_produto / qtd_produto if qtd_produto > 0 else 0
                
                # Calcular peso total
                peso_total = peso_unitario * qtd_produto
                
                # Mapear status
                status_map = {
                    'posted': 'ATIVO',
                    'draft': 'RASCUNHO',
                    'cancel': 'CANCELADO'
                }
                status_nf = status_map.get(item.get('status_nf', '').lower(), 'ATIVO')
                
                if produto_existente:
                    # Atualizar apenas status se registro já existe
                    produto_existente.status_nf = status_nf
                    produto_existente.updated_by = current_user.nome if current_user else 'Sistema'
                    produtos_atualizados += 1
                else:
                    # Criar novo produto
                    novo_produto = FaturamentoProduto()
                    novo_produto.numero_nf = numero_nf
                    novo_produto.data_fatura = data_fatura
                    novo_produto.cnpj_cliente = str(item.get('cnpj_cliente', '')).strip()
                    novo_produto.nome_cliente = str(item.get('nome_cliente', '')).strip()
                    novo_produto.municipio = str(item.get('municipio', '')).strip()
                    novo_produto.estado = str(item.get('estado', '')).strip()
                    novo_produto.vendedor = str(item.get('vendedor', '')).strip()
                    novo_produto.incoterm = str(item.get('incoterm', '')).strip()
                    novo_produto.cod_produto = cod_produto
                    novo_produto.nome_produto = str(item.get('nome_produto', '')).strip()
                    novo_produto.qtd_produto_faturado = qtd_produto
                    novo_produto.preco_produto_faturado = preco_unitario
                    novo_produto.valor_produto_faturado = valor_produto
                    novo_produto.peso_unitario_produto = peso_unitario
                    novo_produto.peso_total = peso_total
                    novo_produto.origem = str(item.get('origem', '')).strip()
                    novo_produto.status_nf = status_nf
                    novo_produto.created_by = current_user.nome if current_user else 'Sistema'
                    
                    db.session.add(novo_produto)
                    produtos_importados += 1
                
            except Exception as e:
                erros.append(f"Erro ao processar produto {cod_produto} da NF {numero_nf}: {str(e)}")
                logger.error(f"Erro sincronização produto: {e}")
                continue
        
        # Commit dos produtos
        db.session.commit()
        
        # Consolidar para RelatorioFaturamentoImportado
        nfs_consolidadas = _consolidar_relatorio_faturamento()
        
        resultado = {
            'sucesso': True,
            'produtos_importados': produtos_importados,
            'produtos_atualizados': produtos_atualizados,
            'nfs_consolidadas': nfs_consolidadas,
            'erros': erros[:5]  # Primeiros 5 erros
        }
        
        logger.info(f"Sincronização concluída: {resultado}")
        return resultado
        
    except Exception as e:
        logger.error(f"Erro na sincronização: {e}")
        db.session.rollback()
        return {
            'sucesso': False,
            'erro': str(e),
            'produtos_importados': 0,
            'produtos_atualizados': 0,
            'nfs_consolidadas': 0
        }

def _consolidar_relatorio_faturamento():
    """
    Consolida dados do FaturamentoProduto para RelatorioFaturamentoImportado
    
    Returns:
        int: Número de NFs consolidadas
    """
    try:
        from app.faturamento.models import FaturamentoProduto, RelatorioFaturamentoImportado
        from app.localidades.models import Cidade
        from app import db
        from sqlalchemy import func
        
        # Buscar NFs distintas do FaturamentoProduto
        nfs_para_consolidar = db.session.query(
            FaturamentoProduto.numero_nf
        ).distinct().all()
        
        nfs_consolidadas = 0
        
        for (numero_nf,) in nfs_para_consolidar:
            # Buscar dados consolidados da NF
            dados_nf = db.session.query(
                FaturamentoProduto.numero_nf,
                FaturamentoProduto.data_fatura,
                FaturamentoProduto.cnpj_cliente,
                FaturamentoProduto.nome_cliente,
                FaturamentoProduto.municipio,
                FaturamentoProduto.estado,
                FaturamentoProduto.origem,
                FaturamentoProduto.incoterm,
                FaturamentoProduto.vendedor,
                func.sum(FaturamentoProduto.valor_produto_faturado).label('valor_total'),
                func.sum(FaturamentoProduto.peso_total).label('peso_bruto')
            ).filter(
                FaturamentoProduto.numero_nf == numero_nf
            ).group_by(
                FaturamentoProduto.numero_nf,
                FaturamentoProduto.data_fatura,
                FaturamentoProduto.cnpj_cliente,
                FaturamentoProduto.nome_cliente,
                FaturamentoProduto.municipio,
                FaturamentoProduto.estado,
                FaturamentoProduto.origem,
                FaturamentoProduto.incoterm,
                FaturamentoProduto.vendedor
            ).first()
            
            if not dados_nf:
                continue
            
            # Buscar código IBGE
            codigo_ibge = None
            if dados_nf.municipio and dados_nf.estado:
                cidade = Cidade.query.filter(
                    Cidade.nome.ilike(f'%{dados_nf.municipio}%'),
                    Cidade.uf == dados_nf.estado
                ).first()
                if cidade:
                    codigo_ibge = cidade.codigo_ibge
            
            # Verificar se já existe no relatório
            relatorio_existente = RelatorioFaturamentoImportado.query.filter_by(
                numero_nf=numero_nf
            ).first()
            
            if relatorio_existente:
                # Atualizar dados consolidados
                relatorio_existente.data_fatura = dados_nf.data_fatura
                relatorio_existente.cnpj_cliente = dados_nf.cnpj_cliente
                relatorio_existente.nome_cliente = dados_nf.nome_cliente
                relatorio_existente.valor_total = float(dados_nf.valor_total) if dados_nf.valor_total else 0
                relatorio_existente.peso_bruto = float(dados_nf.peso_bruto) if dados_nf.peso_bruto else 0
                relatorio_existente.municipio = dados_nf.municipio
                relatorio_existente.estado = dados_nf.estado
                relatorio_existente.codigo_ibge = codigo_ibge
                relatorio_existente.origem = dados_nf.origem
                relatorio_existente.incoterm = dados_nf.incoterm
                relatorio_existente.vendedor = dados_nf.vendedor
                # Manter campos de transportadora vazios conforme especificado
                relatorio_existente.cnpj_transportadora = None
                relatorio_existente.nome_transportadora = None
            else:
                # Criar novo registro
                novo_relatorio = RelatorioFaturamentoImportado(
                    numero_nf=numero_nf,
                    data_fatura=dados_nf.data_fatura,
                    cnpj_cliente=dados_nf.cnpj_cliente,
                    nome_cliente=dados_nf.nome_cliente,
                    valor_total=float(dados_nf.valor_total) if dados_nf.valor_total else 0,
                    peso_bruto=float(dados_nf.peso_bruto) if dados_nf.peso_bruto else 0,
                    municipio=dados_nf.municipio,
                    estado=dados_nf.estado,
                    codigo_ibge=codigo_ibge,
                    origem=dados_nf.origem,
                    incoterm=dados_nf.incoterm,
                    vendedor=dados_nf.vendedor,
                    # Campos de transportadora vazios conforme especificado
                    cnpj_transportadora=None,
                    nome_transportadora=None
                )
                
                db.session.add(novo_relatorio)
                nfs_consolidadas += 1
        
        db.session.commit()
        return nfs_consolidadas
        
    except Exception as e:
        db.session.rollback()
        raise e 