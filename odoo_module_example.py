# -*- coding: utf-8 -*-
"""
Módulo Odoo para Integração com Sistema de Fretes
Sincronização de Carteira de Pedidos e Faturamento
"""

import json
import requests
import logging
from datetime import datetime, date
from app.api.odoo import models, fields, api, _
from app.api.odoo.validators import UserError, ValidationError

_logger = logging.getLogger(__name__)

class FretesSyncWizard(models.TransientModel):
    """
    Wizard para sincronização com Sistema de Fretes
    """
    _name = 'fretes.sync.wizard'
    _description = 'Sincronização Sistema de Fretes'

    # Configurações da API
    api_base_url = fields.Char(
        string='URL Base da API',
        default='https://sistema-fretes.onrender.com',
        required=True
    )
    api_token = fields.Char(
        string='Token JWT',
        required=True
    )
    api_key = fields.Char(
        string='API Key',
        required=True
    )
    
    # Opções de sincronização
    sync_type = fields.Selection([
        ('carteira', 'Carteira de Pedidos'),
        ('faturamento_consolidado', 'Faturamento Consolidado'),
        ('faturamento_produto', 'Faturamento por Produto')
    ], string='Tipo de Sincronização', required=True)
    
    # Filtros
    date_from = fields.Date(string='Data De', required=True)
    date_to = fields.Date(string='Data Até', required=True)
    customer_ids = fields.Many2many('res.partner', string='Clientes Específicos')
    
    # Resultados
    result_message = fields.Text(string='Resultado', readonly=True)
    
    def _get_api_headers(self):
        """Retorna headers para requisições API"""
        return {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_token}',
            'X-API-Key': self.api_key
        }
    
    def _make_api_request(self, endpoint, data):
        """Faz requisição para API do sistema de fretes"""
        url = f"{self.api_base_url.rstrip('/')}/{endpoint}"
        headers = self._get_api_headers()
        
        try:
            response = requests.post(url, json=data, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            _logger.error(f"Erro na requisição API: {e}")
            raise UserError(f"Erro na comunicação com API: {e}")
    
    def _prepare_carteira_data(self):
        """Prepara dados da carteira de pedidos para sincronização"""
        # Buscar pedidos de venda no período
        domain = [
            ('date_order', '>=', self.date_from),
            ('date_order', '<=', self.date_to),
            ('state', 'in', ['sale', 'done'])
        ]
        
        if self.customer_ids:
            domain.append(('partner_id', 'in', self.customer_ids.ids))
        
        orders = self.env['sale.order'].search(domain)
        
        items = []
        for order in orders:
            for line in order.order_line:
                # Mapear campos do Odoo para formato do Sistema de Fretes
                item_data = {
                    # Campos obrigatórios
                    'num_pedido': order.name,
                    'cod_produto': line.product_id.default_code or str(line.product_id.id),
                    'nome_produto': line.product_id.name,
                    'qtd_produto_pedido': line.product_uom_qty,
                    'qtd_saldo_produto_pedido': line.product_uom_qty - line.qty_delivered,
                    'cnpj_cpf': order.partner_id.vat or '',
                    'preco_produto_pedido': line.price_unit,
                    
                    # Dados do pedido
                    'pedido_cliente': order.client_order_ref or '',
                    'data_pedido': order.date_order.strftime('%Y-%m-%d'),
                    'status_pedido': 'Pedido de venda' if order.state == 'sale' else 'Cancelado',
                    
                    # Dados do cliente
                    'raz_social': order.partner_id.name,
                    'raz_social_red': order.partner_id.display_name,
                    'municipio': order.partner_id.city or '',
                    'estado': order.partner_id.state_id.code or '',
                    'vendedor': order.user_id.name or '',
                    'equipe_vendas': order.team_id.name or '',
                    
                    # Dados do produto
                    'unid_medida_produto': line.product_uom.name,
                    'embalagem_produto': line.product_id.categ_id.name or '',
                    
                    # Condições comerciais
                    'cond_pgto_pedido': order.payment_term_id.name or '',
                    'incoterm': order.incoterm.code if order.incoterm else '',
                    'data_entrega_pedido': order.commitment_date.strftime('%Y-%m-%d') if order.commitment_date else None,
                    
                    # Endereço de entrega
                    'cnpj_endereco_ent': order.partner_shipping_id.vat or '',
                    'empresa_endereco_ent': order.partner_shipping_id.name or '',
                    'cep_endereco_ent': order.partner_shipping_id.zip or '',
                    'nome_cidade': order.partner_shipping_id.city or '',
                    'cod_uf': order.partner_shipping_id.state_id.code or '',
                    'bairro_endereco_ent': order.partner_shipping_id.street2 or '',
                    'rua_endereco_ent': order.partner_shipping_id.street or '',
                    'telefone_endereco_ent': order.partner_shipping_id.phone or '',
                    
                    # Estoque (se disponível)
                    'estoque': line.product_id.qty_available
                }
                
                items.append(item_data)
        
        return {'items': items}
    
    def _prepare_faturamento_consolidado_data(self):
        """Prepara dados do faturamento consolidado"""
        # Buscar faturas no período
        domain = [
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
            ('move_type', '=', 'out_invoice'),
            ('state', 'in', ['posted'])
        ]
        
        if self.customer_ids:
            domain.append(('partner_id', 'in', self.customer_ids.ids))
        
        invoices = self.env['account.move'].search(domain)
        
        items = []
        for invoice in invoices:
            # Buscar pedido de origem
            origin_order = self.env['sale.order'].search([
                ('name', '=', invoice.invoice_origin)
            ], limit=1)
            
            item_data = {
                # Campos obrigatórios
                'numero_nf': invoice.name,
                'data_fatura': invoice.invoice_date.strftime('%Y-%m-%d'),
                'cnpj_cliente': invoice.partner_id.vat or '',
                'nome_cliente': invoice.partner_id.name,
                'valor_total': invoice.amount_total,
                'origem': invoice.invoice_origin or '',
                
                # Campos opcionais
                'municipio': invoice.partner_id.city or '',
                'estado': invoice.partner_id.state_id.code or '',
                'codigo_ibge': invoice.partner_id.l10n_br_city_id.ibge_code if hasattr(invoice.partner_id, 'l10n_br_city_id') else '',
                'incoterm': origin_order.incoterm.code if origin_order and origin_order.incoterm else '',
                'vendedor': origin_order.user_id.name if origin_order else ''
            }
            
            items.append(item_data)
        
        return {
            'tipo': 'consolidado',
            'items': items
        }
    
    def _prepare_faturamento_produto_data(self):
        """Prepara dados do faturamento por produto"""
        # Buscar faturas no período
        domain = [
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
            ('move_type', '=', 'out_invoice'),
            ('state', 'in', ['posted'])
        ]
        
        if self.customer_ids:
            domain.append(('partner_id', 'in', self.customer_ids.ids))
        
        invoices = self.env['account.move'].search(domain)
        
        items = []
        for invoice in invoices:
            # Buscar pedido de origem
            origin_order = self.env['sale.order'].search([
                ('name', '=', invoice.invoice_origin)
            ], limit=1)
            
            for line in invoice.invoice_line_ids:
                if line.product_id:
                    item_data = {
                        # Campos obrigatórios
                        'numero_nf': invoice.name,
                        'data_fatura': invoice.invoice_date.strftime('%Y-%m-%d'),
                        'cnpj_cliente': invoice.partner_id.vat or '',
                        'nome_cliente': invoice.partner_id.name,
                        'cod_produto': line.product_id.default_code or str(line.product_id.id),
                        'nome_produto': line.product_id.name,
                        'qtd_produto_faturado': line.quantity,
                        'preco_produto_faturado': line.price_unit,
                        'valor_produto_faturado': line.price_subtotal,
                        
                        # Campos opcionais
                        'municipio': invoice.partner_id.city or '',
                        'estado': invoice.partner_id.state_id.code or '',
                        'vendedor': origin_order.user_id.name if origin_order else '',
                        'incoterm': origin_order.incoterm.code if origin_order and origin_order.incoterm else '',
                        'origem': invoice.invoice_origin or '',
                        'status_nf': 'Lançado'
                    }
                    
                    items.append(item_data)
        
        return {
            'tipo': 'produto',
            'items': items
        }
    
    def action_sync_carteira(self):
        """Sincroniza carteira de pedidos"""
        try:
            data = self._prepare_carteira_data()
            
            if not data['items']:
                raise UserError("Nenhum pedido encontrado no período especificado.")
            
            result = self._make_api_request('api/v1/carteira/bulk-update', data)
            
            message = f"""
            ✅ SINCRONIZAÇÃO DA CARTEIRA CONCLUÍDA
            
            📊 Processados: {result.get('processed', 0)}
            ➕ Criados: {result.get('created', 0)}
            ✏️ Atualizados: {result.get('updated', 0)}
            ❌ Erros: {len(result.get('errors', []))}
            
            {result.get('message', '')}
            """
            
            if result.get('errors'):
                message += f"\n\n❌ ERROS ENCONTRADOS:\n"
                for error in result.get('errors', []):
                    message += f"- {error}\n"
            
            self.result_message = message
            return self._show_result()
            
        except Exception as e:
            self.result_message = f"❌ ERRO: {str(e)}"
            return self._show_result()
    
    def action_sync_faturamento(self):
        """Sincroniza faturamento"""
        try:
            if self.sync_type == 'faturamento_consolidado':
                data = self._prepare_faturamento_consolidado_data()
            else:
                data = self._prepare_faturamento_produto_data()
            
            if not data['items']:
                raise UserError("Nenhuma fatura encontrada no período especificado.")
            
            result = self._make_api_request('api/v1/faturamento/bulk-update', data)
            
            message = f"""
            ✅ SINCRONIZAÇÃO DO FATURAMENTO CONCLUÍDA
            
            📊 Processados: {result.get('processed', 0)}
            ➕ Criados: {result.get('created', 0)}
            ✏️ Atualizados: {result.get('updated', 0)}
            ❌ Erros: {len(result.get('errors', []))}
            
            {result.get('message', '')}
            """
            
            if result.get('errors'):
                message += f"\n\n❌ ERROS ENCONTRADOS:\n"
                for error in result.get('errors', []):
                    message += f"- {error}\n"
            
            self.result_message = message
            return self._show_result()
            
        except Exception as e:
            self.result_message = f"❌ ERRO: {str(e)}"
            return self._show_result()
    
    def action_sync(self):
        """Ação principal de sincronização"""
        if self.sync_type == 'carteira':
            return self.action_sync_carteira()
        else:
            return self.action_sync_faturamento()
    
    def _show_result(self):
        """Mostra resultado da sincronização"""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'fretes.sync.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {'show_result': True}
        }

    def action_test_connection(self):
        """Testa conexão com a API"""
        try:
            # Fazer uma requisição de teste
            url = f"{self.api_base_url.rstrip('/')}/api/v1/test"
            headers = self._get_api_headers()
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                self.result_message = "✅ CONEXÃO ESTABELECIDA COM SUCESSO!"
            else:
                self.result_message = f"❌ ERRO DE CONEXÃO: Status {response.status_code}"
                
        except Exception as e:
            self.result_message = f"❌ ERRO DE CONEXÃO: {str(e)}"
        
        return self._show_result()

# Modelo para histórico de sincronizações
class FretesSyncHistory(models.Model):
    """
    Histórico de sincronizações com o Sistema de Fretes
    """
    _name = 'fretes.sync.history'
    _description = 'Histórico de Sincronização'
    _order = 'create_date desc'

    name = fields.Char(string='Nome', required=True)
    sync_type = fields.Selection([
        ('carteira', 'Carteira de Pedidos'),
        ('faturamento_consolidado', 'Faturamento Consolidado'),
        ('faturamento_produto', 'Faturamento por Produto')
    ], string='Tipo', required=True)
    
    date_from = fields.Date(string='Data De', required=True)
    date_to = fields.Date(string='Data Até', required=True)
    
    processed = fields.Integer(string='Processados', default=0)
    created = fields.Integer(string='Criados', default=0)
    updated = fields.Integer(string='Atualizados', default=0)
    errors = fields.Integer(string='Erros', default=0)
    
    result_message = fields.Text(string='Mensagem')
    state = fields.Selection([
        ('success', 'Sucesso'),
        ('error', 'Erro'),
        ('warning', 'Aviso')
    ], string='Status', default='success')
    
    user_id = fields.Many2one('res.users', string='Usuário', default=lambda self: self.env.user)
    
    @api.model
    def create_history(self, sync_type, date_from, date_to, result):
        """Cria registro no histórico"""
        vals = {
            'name': f"{sync_type.replace('_', ' ').title()} - {date_from} a {date_to}",
            'sync_type': sync_type,
            'date_from': date_from,
            'date_to': date_to,
            'processed': result.get('processed', 0),
            'created': result.get('created', 0),
            'updated': result.get('updated', 0),
            'errors': len(result.get('errors', [])),
            'result_message': result.get('message', ''),
            'state': 'success' if result.get('success') else 'error'
        }
        
        return self.create(vals)

# Configurações da integração
class FretesSyncConfig(models.Model):
    """
    Configurações da integração com Sistema de Fretes
    """
    _name = 'fretes.sync.config'
    _description = 'Configurações Sistema de Fretes'
    
    name = fields.Char(string='Nome', required=True)
    api_base_url = fields.Char(string='URL Base da API', required=True)
    api_token = fields.Char(string='Token JWT', required=True)
    api_key = fields.Char(string='API Key', required=True)
    
    active = fields.Boolean(string='Ativo', default=True)
    
    # Configurações de sincronização automática
    auto_sync_carteira = fields.Boolean(string='Sincronização Automática - Carteira')
    auto_sync_faturamento = fields.Boolean(string='Sincronização Automática - Faturamento')
    
    sync_interval = fields.Integer(string='Intervalo (minutos)', default=60)
    
    def action_test_connection(self):
        """Testa conexão com a API"""
        wizard = self.env['fretes.sync.wizard'].create({
            'api_base_url': self.api_base_url,
            'api_token': self.api_token,
            'api_key': self.api_key
        })
        
        return wizard.action_test_connection() 