"""
Mapeadores de Campos Odoo
=========================

Sistema centralizado de mapeamento de campos entre Odoo e Sistema de Fretes.
Inclui transformações, validações e formatações específicas.

Autor: Sistema de Fretes
Data: 2025-07-14
"""

import re
from datetime import datetime
from typing import Dict, Any, Optional, List
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

class BaseMapper:
    """Classe base para mapeadores de campos"""
    
    def __init__(self):
        self.field_mapping = {}
        self.transformations = {}
    
    def map_data(self, odoo_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mapeia dados do Odoo para o formato do sistema"""
        mapped_data = {}
        
        for odoo_field, system_field in self.field_mapping.items():
            if odoo_field in odoo_data:
                raw_value = odoo_data[odoo_field]
                
                # Aplicar transformação se definida
                if system_field in self.transformations:
                    try:
                        transformed_value = self.transformations[system_field](raw_value)
                        mapped_data[system_field] = transformed_value
                    except Exception as e:
                        logger.warning(f"Erro na transformação de {system_field}: {e}")
                        mapped_data[system_field] = raw_value
                else:
                    mapped_data[system_field] = raw_value
        
        return mapped_data
    
    def validate_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Valida dados mapeados"""
        # Implementar validações específicas nas subclasses
        return data

class CarteiraMapper(BaseMapper):
    """Mapeador para dados de carteira de pedidos"""
    
    def __init__(self):
        super().__init__()
        
        # Mapeamento de campos: odoo_field -> system_field
        self.field_mapping = {
            'name': 'num_pedido',
            'partner_id': 'cnpj_cpf',
            'partner_id/l10n_br_cnpj': 'cnpj_cpf',
            'product_id': 'cod_produto',
            'product_id/default_code': 'cod_produto',
            'product_id/name': 'nome_produto',
            'product_uom_qty': 'qtd_produto_pedido',
            'qty_saldo': 'qtd_saldo_produto',
            'price_unit': 'preco_produto_pedido',
            'price_subtotal': 'valor_produto_pedido',
            'order_id/date_order': 'data_pedido',
            'order_id/commitment_date': 'data_prevista_entrega',
            'order_id/state': 'status_pedido',
            'order_id/user_id': 'vendedor',
            'order_id/client_order_ref': 'referencia_cliente',
            'order_id/partner_shipping_id': 'endereco_entrega',
            'order_id/amount_total': 'valor_total_pedido',
            'order_id/incoterm': 'incoterm',
            'order_id/pricelist_id': 'lista_preco',
            'order_id/payment_term_id': 'condicao_pagamento'
        }
        
        # Transformações específicas
        self.transformations = {
            'cnpj_cpf': self._extract_partner_cnpj,
            'cod_produto': self._extract_product_code,
            'nome_produto': self._extract_product_name,
            'data_pedido': self._format_date,
            'data_prevista_entrega': self._format_date,
            'status_pedido': self._map_order_state,
            'vendedor': self._extract_user_name,
            'preco_produto_pedido': self._format_decimal,
            'valor_produto_pedido': self._format_decimal,
            'valor_total_pedido': self._format_decimal,
            'qtd_produto_pedido': self._format_decimal,
            'qtd_saldo_produto': self._format_decimal,
            'endereco_entrega': self._extract_address,
            'lista_preco': self._extract_pricelist,
            'condicao_pagamento': self._extract_payment_term
        }
    
    def _extract_partner_cnpj(self, partner_data):
        """Extrai CNPJ do parceiro"""
        if isinstance(partner_data, list) and len(partner_data) > 0:
            return partner_data[0] if isinstance(partner_data[0], str) else str(partner_data[0])
        return str(partner_data) if partner_data else ''
    
    def _extract_product_code(self, product_data):
        """Extrai código do produto"""
        if isinstance(product_data, list) and len(product_data) > 0:
            return product_data[0] if isinstance(product_data[0], str) else str(product_data[0])
        return str(product_data) if product_data else ''
    
    def _extract_product_name(self, product_data):
        """Extrai nome do produto"""
        if isinstance(product_data, list) and len(product_data) > 1:
            return product_data[1]  # [id, name]
        return str(product_data) if product_data else ''
    
    def _format_date(self, date_value):
        """Formata data para o sistema"""
        if not date_value:
            return None
        
        if isinstance(date_value, str):
            try:
                return datetime.strptime(date_value, '%Y-%m-%d').date()
            except ValueError:
                try:
                    return datetime.strptime(date_value, '%Y-%m-%d %H:%M:%S').date()
                except ValueError:
                    return None
        return date_value
    
    def _map_order_state(self, state):
        """Mapeia estado do pedido"""
        state_mapping = {
            'draft': 'RASCUNHO',
            'sent': 'ENVIADO',
            'sale': 'CONFIRMADO',
            'done': 'CONCLUIDO',
            'cancel': 'CANCELADO'
        }
        return state_mapping.get(state, state or 'PENDENTE')
    
    def _extract_user_name(self, user_data):
        """Extrai nome do usuário"""
        if isinstance(user_data, list) and len(user_data) > 1:
            return user_data[1]  # [id, name]
        return str(user_data) if user_data else ''
    
    def _extract_address(self, address_data):
        """Extrai endereço de entrega"""
        if isinstance(address_data, list) and len(address_data) > 1:
            return address_data[1]  # [id, name]
        return str(address_data) if address_data else ''
    
    def _extract_pricelist(self, pricelist_data):
        """Extrai lista de preços"""
        if isinstance(pricelist_data, list) and len(pricelist_data) > 1:
            return pricelist_data[1]  # [id, name]
        return str(pricelist_data) if pricelist_data else ''
    
    def _extract_payment_term(self, payment_data):
        """Extrai condição de pagamento"""
        if isinstance(payment_data, list) and len(payment_data) > 1:
            return payment_data[1]  # [id, name]
        return str(payment_data) if payment_data else ''
    
    def _format_decimal(self, value):
        """Formata valor decimal"""
        if value is None:
            return 0
        try:
            return Decimal(str(value))
        except:
            return Decimal('0')
    
    def map_data(self, odoo_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mapeia dados com cálculos específicos da carteira"""
        mapped_data = super().map_data(odoo_data)
        
        # Calcular status baseado no saldo
        qtd_saldo = mapped_data.get('qtd_saldo_produto', 0)
        if qtd_saldo > 0:
            mapped_data['status_calculado'] = 'PENDENTE'
        else:
            mapped_data['status_calculado'] = 'ATENDIDO'
        
        # Garantir que campos obrigatórios não sejam None
        if not mapped_data.get('num_pedido'):
            mapped_data['num_pedido'] = odoo_data.get('order_id', ['', ''])[1] if isinstance(odoo_data.get('order_id'), list) else str(odoo_data.get('order_id', ''))
        
        if not mapped_data.get('cnpj_cpf'):
            # Tentar extrair CNPJ do partner_id
            partner_data = odoo_data.get('partner_id')
            if isinstance(partner_data, list) and len(partner_data) > 0:
                mapped_data['cnpj_cpf'] = str(partner_data[0])
        
        # Garantir que datas sejam válidas
        if not mapped_data.get('data_pedido'):
            mapped_data['data_pedido'] = datetime.now().date()
        
        return mapped_data

class FaturamentoMapper(BaseMapper):
    """Mapeador para dados de faturamento consolidado"""
    
    def __init__(self):
        super().__init__()
        
        # Mapeamento de campos: odoo_field -> system_field
        self.field_mapping = {
            'number': 'numero_nf',
            'date': 'data_fatura',
            'partner_id': 'cnpj_cliente',
            'amount_total': 'valor_total',
            'weight': 'peso_bruto',
            'delivery_carrier_id': 'cnpj_transportadora',
            'city': 'municipio',
            'state_id': 'estado',
            'l10n_br_city_id': 'codigo_ibge',
            'invoice_origin': 'origem',
            'invoice_incoterm_id': 'incoterm',
            'invoice_user_id': 'vendedor'
        }
        
        # Transformações específicas
        self.transformations = {
            'cnpj_cliente': self._extract_partner_cnpj,
            'data_fatura': self._format_date,
            'valor_total': self._format_decimal,
            'peso_bruto': self._format_decimal,
            'cnpj_transportadora': self._extract_carrier_cnpj,
            'estado': self._extract_state_code,
            'vendedor': self._extract_user_name,
            'incoterm': self._extract_incoterm_name
        }
    
    def _extract_partner_cnpj(self, partner_data):
        """Extrai CNPJ do parceiro"""
        if isinstance(partner_data, list) and len(partner_data) > 1:
            return partner_data[1]  # [id, name]
        return partner_data
    
    def _extract_carrier_cnpj(self, carrier_data):
        """Extrai CNPJ da transportadora"""
        if isinstance(carrier_data, list) and len(carrier_data) > 1:
            return carrier_data[1]  # [id, name]
        return carrier_data
    
    def _extract_state_code(self, state_data):
        """Extrai código do estado"""
        if isinstance(state_data, list) and len(state_data) > 1:
            name = state_data[1]  # [id, name]
            # Extrair código do estado do nome (ex: "São Paulo" -> "SP")
            return self._get_state_code(name)
        return state_data
    
    def _extract_incoterm_name(self, incoterm_data):
        """Extrai nome do incoterm"""
        if isinstance(incoterm_data, list) and len(incoterm_data) > 1:
            return incoterm_data[1]  # [id, name]
        return incoterm_data
    
    def _extract_user_name(self, user_data):
        """Extrai nome do usuário"""
        if isinstance(user_data, list) and len(user_data) > 1:
            return user_data[1]  # [id, name]
        return user_data
    
    def _format_date(self, date_value):
        """Formata data para o sistema"""
        if not date_value:
            return None
        
        if isinstance(date_value, str):
            try:
                return datetime.strptime(date_value, '%Y-%m-%d').date()
            except ValueError:
                try:
                    return datetime.strptime(date_value, '%Y-%m-%d %H:%M:%S').date()
                except ValueError:
                    return None
        return date_value
    
    def _format_decimal(self, value):
        """Formata valor decimal"""
        if value is None:
            return 0
        try:
            return Decimal(str(value))
        except:
            return Decimal('0')
    
    def _get_state_code(self, state_name):
        """Obtém código do estado pelo nome"""
        state_codes = {
            'Acre': 'AC',
            'Alagoas': 'AL',
            'Amapá': 'AP',
            'Amazonas': 'AM',
            'Bahia': 'BA',
            'Ceará': 'CE',
            'Distrito Federal': 'DF',
            'Espírito Santo': 'ES',
            'Goiás': 'GO',
            'Maranhão': 'MA',
            'Mato Grosso': 'MT',
            'Mato Grosso do Sul': 'MS',
            'Minas Gerais': 'MG',
            'Pará': 'PA',
            'Paraíba': 'PB',
            'Paraná': 'PR',
            'Pernambuco': 'PE',
            'Piauí': 'PI',
            'Rio de Janeiro': 'RJ',
            'Rio Grande do Norte': 'RN',
            'Rio Grande do Sul': 'RS',
            'Rondônia': 'RO',
            'Roraima': 'RR',
            'Santa Catarina': 'SC',
            'São Paulo': 'SP',
            'Sergipe': 'SE',
            'Tocantins': 'TO'
        }
        return state_codes.get(state_name, state_name)

class FaturamentoProdutoMapper(BaseMapper):
    """Mapeador para dados de faturamento por produto"""
    
    def __init__(self):
        super().__init__()
        
        # Mapeamento de campos: odoo_field -> system_field
        self.field_mapping = {
            'x_studio_nf_e': 'numero_nf',
            'partner_id': 'cnpj_cliente',
            'l10n_br_municipio_id': 'municipio',
            'invoice_origin': 'origem',
            'state': 'status_nf',
            'product_id': 'cod_produto',
            'quantity': 'qtd_produto_faturado',
            'l10n_br_total_nfe': 'valor_produto_faturado',
            'date': 'data_fatura',
            'gross_weight': 'peso_unitario_produto'
        }
        
        # Transformações específicas
        self.transformations = {
            'cnpj_cliente': self._extract_partner_cnpj,
            'municipio': self._extract_city_state,
            'cod_produto': self._extract_product_code,
            'data_fatura': self._format_date,
            'status_nf': self._map_invoice_state,
            'qtd_produto_faturado': self._format_decimal,
            'valor_produto_faturado': self._format_decimal,
            'peso_unitario_produto': self._format_decimal
        }
    
    def _extract_partner_cnpj(self, partner_data):
        """Extrai CNPJ do parceiro"""
        if isinstance(partner_data, list) and len(partner_data) > 1:
            return partner_data[1]  # [id, name]
        return partner_data
    
    def _extract_city_state(self, city_data):
        """Extrai cidade e estado"""
        if isinstance(city_data, list) and len(city_data) > 1:
            return city_data[1]  # [id, name]
        return city_data
    
    def _extract_product_code(self, product_data):
        """Extrai código do produto"""
        if isinstance(product_data, list) and len(product_data) > 1:
            return product_data[1]  # [id, name]
        return product_data
    
    def _format_date(self, date_value):
        """Formata data para o sistema"""
        if not date_value:
            return None
        
        if isinstance(date_value, str):
            try:
                return datetime.strptime(date_value, '%Y-%m-%d').date()
            except ValueError:
                try:
                    return datetime.strptime(date_value, '%Y-%m-%d %H:%M:%S').date()
                except ValueError:
                    return None
        return date_value
    
    def _map_invoice_state(self, state):
        """Mapeia estado da fatura"""
        state_mapping = {
            'draft': 'RASCUNHO',
            'posted': 'LANCADO',
            'cancel': 'CANCELADO'
        }
        return state_mapping.get(state, state)
    
    def _format_decimal(self, value):
        """Formata valor decimal"""
        if value is None:
            return 0
        try:
            return Decimal(str(value))
        except:
            return Decimal('0')
    
    def map_data(self, odoo_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mapeia dados com cálculo de peso total"""
        mapped_data = super().map_data(odoo_data)
        
        # Calcular peso_total = peso_unitario * quantidade
        peso_unitario = mapped_data.get('peso_unitario_produto', 0)
        quantidade = mapped_data.get('qtd_produto_faturado', 0)
        
        if peso_unitario and quantidade:
            mapped_data['peso_total'] = peso_unitario * quantidade
        else:
            mapped_data['peso_total'] = 0
        
        return mapped_data

# Instâncias globais dos mapeadores
_carteira_mapper = None
_faturamento_mapper = None
_faturamento_produto_mapper = None

def get_carteira_mapper() -> CarteiraMapper:
    """Obtém instância do mapeador de carteira"""
    global _carteira_mapper
    if _carteira_mapper is None:
        _carteira_mapper = CarteiraMapper()
    return _carteira_mapper

def get_faturamento_mapper() -> FaturamentoMapper:
    """Obtém instância do mapeador de faturamento"""
    global _faturamento_mapper
    if _faturamento_mapper is None:
        _faturamento_mapper = FaturamentoMapper()
    return _faturamento_mapper

def get_faturamento_produto_mapper() -> FaturamentoProdutoMapper:
    """Obtém instância do mapeador de faturamento por produto"""
    global _faturamento_produto_mapper
    if _faturamento_produto_mapper is None:
        _faturamento_produto_mapper = FaturamentoProdutoMapper()
    return _faturamento_produto_mapper 