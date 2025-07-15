"""
Serviço de Carteira Odoo
========================

Serviço responsável por gerenciar a importação de dados de carteira de pedidos
do Odoo ERP. Foca apenas na consulta e filtro 'Carteira Pendente'.

Funcionalidades:
- Importação de carteira pendente
- Filtro por período e pedidos específicos
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

class CarteiraService:
    """Serviço para gerenciar carteira de pedidos do Odoo"""
    
    def __init__(self):
        self.connection = get_odoo_connection()
    
    def obter_carteira_pendente(self, data_inicio=None, data_fim=None, pedidos_especificos=None):
        """
        Obter carteira pendente do Odoo com campos corretos
        """
        logger.info("Buscando carteira pendente do Odoo...")
        
        try:
            # Domínio para carteira pendente
            domain = [['qty_saldo', '>', 0]]  # Apenas pedidos com saldo pendente
            
            # CAMPOS CORRETOS baseados nos testes
            fields = [
                'order_id/l10n_br_pedido_compra',  # Pedido de Compra do Cliente
                'order_id/name',  # Referência do pedido
                'order_id/create_date',  # Data de criação
                'order_id/date_order',  # Data do pedido
                'order_id/partner_id/l10n_br_cnpj',  # CNPJ Cliente
                'order_id/partner_id/l10n_br_razao_social',  # Razão Social
                'order_id/partner_id/name',  # Nome Cliente
                'order_id/partner_id/l10n_br_municipio_id/name',  # Município
                'order_id/partner_id/state_id/code',  # Estado
                'order_id/user_id',  # Vendedor
                'order_id/team_id',  # Equipe de vendas
                'product_id/default_code',  # Referência interna produto
                'product_id/name',  # Nome produto
                'product_id/uom_id',  # Unidade de medida
                'product_uom_qty',  # Quantidade
                'qty_to_invoice',  # Quantidade a faturar
                'qty_saldo',  # Saldo
                'qty_cancelado',  # Cancelado
                'qty_invoiced',  # Quantidade faturada
                'price_unit',  # Preço unitário
                'l10n_br_prod_valor',  # Valor do Produto
                'l10n_br_total_nfe',  # Valor do Item do Pedido
                'order_id/state',  # Status
                'product_id/categ_id/name',  # Categoria produto
                'product_id/categ_id/parent_id/name',  # Categoria primária
                'product_id/categ_id/parent_id/parent_id/name',  # Categoria primária/primária
                'order_id/payment_term_id',  # Condições de pagamento
                'order_id/payment_provider_id',  # Forma de Pagamento
                'order_id/picking_note',  # Notas para Expedição
                'order_id/incoterm',  # Incoterm
                'order_id/carrier_id',  # Método de entrega
                'order_id/commitment_date',  # Data de entrega
                'order_id/partner_id/agendamento',  # Agendamento
                'qty_delivered',  # Quantidade entregue
                'order_id/partner_shipping_id/l10n_br_cnpj',  # CNPJ Endereço entrega
                'order_id/partner_shipping_id/self',  # O próprio
                'order_id/partner_shipping_id/zip',  # CEP
                'order_id/partner_shipping_id/state_id',  # Estado entrega
                'order_id/partner_shipping_id/l10n_br_municipio_id',  # Município entrega
                'order_id/partner_shipping_id/l10n_br_endereco_bairro',  # Bairro
                'order_id/partner_shipping_id/street',  # Endereço
                'order_id/partner_shipping_id/l10n_br_endereco_numero',  # Número
                'order_id/partner_shipping_id/phone'  # Telefone
            ]
            
            logger.info(f"🔍 Buscando campos: {fields}")
            
            # Buscar dados do Odoo
            odoo_data = self.connection.search_read(
                model='sale.order.line',
                domain=domain,
                fields=fields,
                limit=5000
            )
            
            logger.info(f"✅ SUCESSO: {len(odoo_data)} registros encontrados")
            
            # Mostrar estrutura dos dados
            for i, record in enumerate(odoo_data):
                logger.info(f"📋 REGISTRO {i+1}: {record}")
                
                # Analisar campos relacionados
                if 'order_id' in record:
                    logger.info(f"🎯 ORDER_ID: {record['order_id']}")
                if 'product_id' in record:
                    logger.info(f"🎯 PRODUCT_ID: {record['product_id']}")
                if 'order_partner_id' in record:
                    logger.info(f"🎯 ORDER_PARTNER_ID: {record['order_partner_id']}")
            
            return {
                'sucesso': True,
                'dados': odoo_data,
                'total_registros': len(odoo_data),
                'mensagem': f'✅ {len(odoo_data)} registros encontrados com campos corretos'
            }
            
        except Exception as e:
            logger.error(f"❌ ERRO: {e}")
            return {
                'sucesso': False,
                'erro': str(e),
                'mensagem': 'Erro ao buscar carteira pendente'
            }
    
    def _build_carteira_domain(self, data_inicio: Optional[date] = None, data_fim: Optional[date] = None, 
                              pedidos_especificos: Optional[List[str]] = None) -> List:
        """Constrói domínio de busca para carteira pendente"""
        # Filtro principal: Carteira Pendente (saldo > 0 e não cancelado)
        domain = [
            '&',
            ('qty_saldo', '>', 0),  # Saldo > 0
            ('order_id.state', '!=', 'cancel')  # Pedido não cancelado
        ]
        
        if data_inicio:
            domain.append(('order_id.date_order', '>=', data_inicio.strftime('%Y-%m-%d')))
        
        if data_fim:
            domain.append(('order_id.date_order', '<=', data_fim.strftime('%Y-%m-%d')))
        
        if pedidos_especificos:
            domain.append(('order_id.name', 'in', pedidos_especificos))
        
        return domain
    
    def _processar_dados_carteira(self, odoo_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Processa dados de carteira do Odoo"""
        dados_processados = []
        
        for item in odoo_data:
            try:
                # Processar cada item da carteira
                item_processado = {
                    'pedido_compra_cliente': self._extract_value(item, 'order_id/l10n_br_pedido_compra'),
                    'referencia_pedido': self._extract_value(item, 'order_id/name'),
                    'data_criacao': self._format_date(item.get('order_id/create_date')),
                    'data_pedido': self._format_date(item.get('order_id/date_order')),
                    'cnpj_cliente': self._extract_value(item, 'order_id/partner_id/l10n_br_cnpj'),
                    'razao_social': self._extract_value(item, 'order_id/partner_id/l10n_br_razao_social'),
                    'nome_cliente': self._extract_value(item, 'order_id/partner_id/name'),
                    'municipio_cliente': self._extract_value(item, 'order_id/partner_id/l10n_br_municipio_id/name'),
                    'estado_cliente': self._extract_value(item, 'order_id/partner_id/state_id/code'),
                    'vendedor': self._extract_relational_field(item, 'order_id/user_id'),
                    'equipe_vendas': self._extract_relational_field(item, 'order_id/team_id'),
                    'codigo_produto': self._extract_value(item, 'product_id/default_code'),
                    'nome_produto': self._extract_value(item, 'product_id/name'),
                    'unidade_medida': self._extract_relational_field(item, 'product_id/uom_id'),
                    'quantidade': self._format_decimal(item.get('product_uom_qty')),
                    'quantidade_a_faturar': self._format_decimal(item.get('qty_to_invoice')),
                    'saldo': self._format_decimal(item.get('qty_saldo')),
                    'cancelado': self._format_decimal(item.get('qty_cancelado')),
                    'quantidade_faturada': self._format_decimal(item.get('qty_invoiced')),
                    'preco_unitario': self._format_decimal(item.get('price_unit')),
                    'valor_produto': self._format_decimal(item.get('l10n_br_prod_valor')),
                    'valor_item_pedido': self._format_decimal(item.get('l10n_br_total_nfe')),
                    'status': self._extract_value(item, 'order_id/state'),
                    'categoria_produto': self._extract_value(item, 'product_id/categ_id/name'),
                    'categoria_primaria': self._extract_value(item, 'product_id/categ_id/parent_id/name'),
                    'categoria_primaria_pai': self._extract_value(item, 'product_id/categ_id/parent_id/parent_id/name'),
                    'condicoes_pagamento': self._extract_relational_field(item, 'order_id/payment_term_id'),
                    'forma_pagamento': self._extract_relational_field(item, 'order_id/payment_provider_id'),
                    'notas_expedicao': self._extract_value(item, 'order_id/picking_note'),
                    'incoterm': self._extract_relational_field(item, 'order_id/incoterm'),
                    'metodo_entrega': self._extract_relational_field(item, 'order_id/carrier_id'),
                    'data_entrega': self._format_date(item.get('order_id/commitment_date')),
                    'agendamento_cliente': self._extract_value(item, 'order_id/partner_id/agendamento'),
                    'quantidade_entregue': self._format_decimal(item.get('qty_delivered')),
                    'cnpj_endereco_entrega': self._extract_value(item, 'order_id/partner_shipping_id/l10n_br_cnpj'),
                    'proprio_endereco': self._extract_value(item, 'order_id/partner_shipping_id/self'),
                    'cep_entrega': self._extract_value(item, 'order_id/partner_shipping_id/zip'),
                    'estado_entrega': self._extract_relational_field(item, 'order_id/partner_shipping_id/state_id'),
                    'municipio_entrega': self._extract_relational_field(item, 'order_id/partner_shipping_id/l10n_br_municipio_id'),
                    'bairro_entrega': self._extract_value(item, 'order_id/partner_shipping_id/l10n_br_endereco_bairro'),
                    'endereco_entrega': self._extract_value(item, 'order_id/partner_shipping_id/street'),
                    'numero_entrega': self._extract_value(item, 'order_id/partner_shipping_id/l10n_br_endereco_numero'),
                    'telefone_entrega': self._extract_value(item, 'order_id/partner_shipping_id/phone')
                }
                
                # Adicionar apenas se tem dados válidos
                if item_processado['referencia_pedido'] and item_processado['saldo'] > 0:
                    dados_processados.append(item_processado)
                    
            except Exception as e:
                logger.error(f"Erro ao processar item da carteira: {e}")
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
        """Calcula estatísticas básicas da carteira"""
        if not dados:
            return {
                'total_itens': 0,
                'total_pedidos': 0,
                'valor_total': 0.0,
                'quantidade_total': 0.0,
                'saldo_total': 0.0
            }
        
        # Calcular estatísticas
        total_itens = len(dados)
        pedidos_unicos = len(set(item['referencia_pedido'] for item in dados))
        valor_total = sum(item['valor_item_pedido'] for item in dados)
        quantidade_total = sum(item['quantidade'] for item in dados)
        saldo_total = sum(item['saldo'] for item in dados)
        
        return {
            'total_itens': total_itens,
            'total_pedidos': pedidos_unicos,
            'valor_total': valor_total,
            'quantidade_total': quantidade_total,
            'saldo_total': saldo_total
        } 

def sincronizar_carteira_odoo(usar_filtro_pendente=True):
    """
    Sincroniza carteira do Odoo por substituição completa da CarteiraPrincipal
    
    Args:
        usar_filtro_pendente (bool): Se deve usar filtro 'Carteira Pendente' (qty_saldo > 0)
    
    Returns:
        dict: Estatísticas da sincronização
    """
    try:
        from app.carteira.models import CarteiraPrincipal
        from app import db
        from flask_login import current_user
        from datetime import datetime
        import logging
        
        logger = logging.getLogger(__name__)
        
        # Criar instância do serviço para chamar método
        service = CarteiraService()
        
        # Buscar dados do Odoo
        dados_odoo = service.obter_carteira_pendente()
        
        if not dados_odoo:
            return {
                'sucesso': False,
                'erro': 'Nenhum dado encontrado no Odoo',
                'registros_importados': 0,
                'registros_removidos': 0
            }
        
        # Aplicar filtro pendente se solicitado
        if usar_filtro_pendente:
            dados_filtrados = [
                item for item in dados_odoo
                if item.get('qty_saldo', 0) > 0
            ]
        else:
            dados_filtrados = dados_odoo
        
        # SUBSTITUIÇÃO COMPLETA: Remover todos os registros existentes
        registros_removidos = CarteiraPrincipal.query.count()
        CarteiraPrincipal.query.delete()
        
        registros_importados = 0
        erros = []
        
        # Processar cada item da carteira
        for item in dados_filtrados:
            try:
                # Validar campos obrigatórios
                pedido_id = item.get('pedido_id')
                cod_produto = item.get('cod_produto')
                
                if not pedido_id or not cod_produto:
                    continue
                
                # Processar data
                data_pedido = None
                if item.get('data_pedido'):
                    try:
                        data_pedido_value = item.get('data_pedido')
                        if isinstance(data_pedido_value, str):
                            data_pedido = datetime.strptime(data_pedido_value, '%Y-%m-%d').date()
                        else:
                            data_pedido = data_pedido_value
                    except:
                        pass
                
                # Processar data prevista
                data_prevista = None
                if item.get('data_prevista'):
                    try:
                        data_prevista_value = item.get('data_prevista')
                        if isinstance(data_prevista_value, str):
                            data_prevista = datetime.strptime(data_prevista_value, '%Y-%m-%d').date()
                        else:
                            data_prevista = data_prevista_value
                    except:
                        pass
                
                # Processar valores
                qtd_pedido = float(item.get('qtd_pedido', 0)) or 0
                qtd_faturado = float(item.get('qtd_faturado', 0)) or 0
                qtd_saldo = float(item.get('qty_saldo', 0)) or 0
                valor_unitario = float(item.get('valor_unitario', 0)) or 0
                valor_total = float(item.get('valor_total', 0)) or 0
                
                # Criar novo registro na CarteiraPrincipal
                novo_registro = CarteiraPrincipal()
                novo_registro.pedido_id = str(pedido_id)
                novo_registro.data_pedido = data_pedido
                novo_registro.data_prevista = data_prevista
                novo_registro.cnpj_cliente = str(item.get('cnpj_cliente', '')).strip()
                novo_registro.nome_cliente = str(item.get('nome_cliente', '')).strip()
                novo_registro.cod_produto = str(cod_produto).strip()
                novo_registro.nome_produto = str(item.get('nome_produto', '')).strip()
                novo_registro.qtd_pedido = qtd_pedido
                novo_registro.qtd_faturado = qtd_faturado
                novo_registro.qtd_saldo = qtd_saldo
                novo_registro.valor_unitario = valor_unitario
                novo_registro.valor_total = valor_total
                novo_registro.vendedor = str(item.get('vendedor', '')).strip()
                novo_registro.incoterm = str(item.get('incoterm', '')).strip()
                novo_registro.municipio = str(item.get('municipio', '')).strip()
                novo_registro.estado = str(item.get('estado', '')).strip()
                novo_registro.endereco_entrega = str(item.get('endereco_entrega', '')).strip()
                novo_registro.bairro_entrega = str(item.get('bairro_entrega', '')).strip()
                novo_registro.cep_entrega = str(item.get('cep_entrega', '')).strip()
                novo_registro.municipio_entrega = str(item.get('municipio_entrega', '')).strip()
                novo_registro.estado_entrega = str(item.get('estado_entrega', '')).strip()
                novo_registro.observacoes = str(item.get('observacoes', '')).strip()
                novo_registro.peso_bruto = float(item.get('peso_bruto', 0)) or 0
                novo_registro.peso_liquido = float(item.get('peso_liquido', 0)) or 0
                novo_registro.volume = float(item.get('volume', 0)) or 0
                novo_registro.created_by = current_user.nome if current_user else 'Sistema'
                
                db.session.add(novo_registro)
                registros_importados += 1
                
            except Exception as e:
                erros.append(f"Erro ao processar pedido {pedido_id}: {str(e)}")
                logger.error(f"Erro sincronização carteira: {e}")
                continue
        
        # Commit das alterações
        db.session.commit()
        
        resultado = {
            'sucesso': True,
            'registros_importados': registros_importados,
            'registros_removidos': registros_removidos,
            'erros': erros[:5]  # Primeiros 5 erros
        }
        
        logger.info(f"Sincronização carteira concluída: {resultado}")
        return resultado
        
    except Exception as e:
        logger.error(f"Erro na sincronização da carteira: {e}")
        db.session.rollback()
        return {
            'sucesso': False,
            'erro': str(e),
            'registros_importados': 0,
            'registros_removidos': 0
        } 