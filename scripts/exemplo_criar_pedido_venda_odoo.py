#!/usr/bin/env python3
"""
Exemplo: Criar Pedido de Venda no Odoo 17 via XML-RPC
=====================================================

Este script demonstra como criar um pedido de vendas completo
no Odoo 17 com localização brasileira (CIEL IT), incluindo
o cálculo de impostos.

Uso:
    python scripts/exemplo_criar_pedido_venda_odoo.py

Autor: Sistema de Fretes
Data: 04/12/2025
"""

import xmlrpc.client
import ssl
import sys
import os
from datetime import datetime
from typing import Dict, List, Optional, Any

# Adicionar path do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class OdooSaleOrderCreator:
    """
    Classe para criar pedidos de venda no Odoo 17 via XML-RPC
    """

    def __init__(self, url: str, database: str, username: str, api_key: str):
        """
        Inicializa conexão com Odoo

        Args:
            url: URL do Odoo (ex: https://odoo.empresa.com.br)
            database: Nome do banco de dados
            username: Email do usuário
            api_key: Chave de API do usuário
        """
        self.url = url
        self.database = database
        self.username = username
        self.api_key = api_key
        self.uid = None
        self.models = None

        self._connect()

    def _connect(self):
        """Estabelece conexão com Odoo"""
        # Configurar SSL (desabilitar verificação para ambientes de teste)
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        # Conectar ao endpoint comum para autenticação
        common = xmlrpc.client.ServerProxy(
            f'{self.url}/xmlrpc/2/common',
            context=ssl_context
        )

        # Autenticar
        self.uid = common.authenticate(
            self.database,
            self.username,
            self.api_key,
            {}
        )

        if not self.uid:
            raise Exception("Falha na autenticação com Odoo")

        # Conectar ao endpoint de modelos
        self.models = xmlrpc.client.ServerProxy(
            f'{self.url}/xmlrpc/2/object',
            context=ssl_context
        )

        print(f"✅ Conectado ao Odoo - UID: {self.uid}")

    def execute(self, model: str, method: str, *args, **kwargs) -> Any:
        """
        Executa método no Odoo

        Args:
            model: Nome do modelo (ex: 'sale.order')
            method: Nome do método (ex: 'create', 'read', 'write')
            *args: Argumentos posicionais
            **kwargs: Argumentos nomeados
        """
        return self.models.execute_kw(
            self.database,
            self.uid,
            self.api_key,
            model,
            method,
            list(args) if args else [],
            kwargs if kwargs else {}
        )

    def buscar_cliente_por_cnpj(self, cnpj: str) -> Optional[Dict]:
        """
        Busca cliente pelo CNPJ

        Args:
            cnpj: CNPJ formatado ou não
        """
        # Limpar CNPJ
        cnpj_limpo = ''.join(filter(str.isdigit, cnpj))

        # Buscar por vat (pode estar formatado de várias formas)
        clientes = self.execute(
            'res.partner', 'search_read',
            [['vat', 'ilike', cnpj_limpo]],
            fields=['id', 'name', 'vat', 'property_product_pricelist']
        )

        return clientes[0] if clientes else None

    def buscar_produto_por_codigo(self, codigo: str) -> Optional[Dict]:
        """
        Busca produto pelo código interno

        Args:
            codigo: Código do produto (default_code)
        """
        produtos = self.execute(
            'product.product', 'search_read',
            [['default_code', '=', codigo]],
            fields=['id', 'name', 'default_code', 'list_price', 'uom_id']
        )

        return produtos[0] if produtos else None

    def listar_operacoes_fiscais_venda(self) -> List[Dict]:
        """Lista operações fiscais de venda disponíveis"""
        return self.execute(
            'l10n_br_ciel_it_account.fiscal.operation', 'search_read',
            [['type', '=', 'sale']],
            fields=['id', 'name', 'code'],
            limit=50
        )

    def criar_pedido_venda(
        self,
        partner_id: int,
        company_id: int,
        operacao_fiscal_id: int,
        linhas: List[Dict],
        pricelist_id: Optional[int] = None,
        team_id: Optional[int] = None,
        user_id: Optional[int] = None,
        payment_term_id: Optional[int] = None,
        client_order_ref: Optional[str] = None,
        pedido_compra: Optional[str] = None,
        imposto_auto: bool = True
    ) -> int:
        """
        Cria um pedido de venda no Odoo

        Args:
            partner_id: ID do cliente (res.partner)
            company_id: ID da empresa
            operacao_fiscal_id: ID da operação fiscal (l10n_br_ciel_it_account.fiscal.operation)
            linhas: Lista de dicts com dados das linhas:
                [{'product_id': 123, 'product_uom_qty': 10.0, 'price_unit': 100.00}, ...]
            pricelist_id: ID da lista de preços (opcional)
            team_id: ID da equipe de vendas (opcional)
            user_id: ID do vendedor (opcional)
            payment_term_id: ID do prazo de pagamento (opcional)
            client_order_ref: Referência do cliente (opcional)
            pedido_compra: Pedido de compra do cliente (opcional)
            imposto_auto: Se True, calcula impostos automaticamente

        Returns:
            ID do pedido criado
        """
        # Preparar linhas do pedido
        order_lines = []
        for linha in linhas:
            order_lines.append((0, 0, {
                'product_id': linha['product_id'],
                'product_uom_qty': linha.get('product_uom_qty', 1.0),
                'price_unit': linha.get('price_unit', 0.0),
                # Campos opcionais
                'name': linha.get('name'),
                'discount': linha.get('discount', 0.0),
            }))

        # Preparar dados do pedido
        order_data = {
            'partner_id': partner_id,
            'company_id': company_id,
            'l10n_br_operacao_id': operacao_fiscal_id,
            'l10n_br_imposto_auto': imposto_auto,
            'order_line': order_lines,
        }

        # Campos opcionais
        if pricelist_id:
            order_data['pricelist_id'] = pricelist_id
        if team_id:
            order_data['team_id'] = team_id
        if user_id:
            order_data['user_id'] = user_id
        if payment_term_id:
            order_data['payment_term_id'] = payment_term_id
        if client_order_ref:
            order_data['client_order_ref'] = client_order_ref
        if pedido_compra:
            order_data['l10n_br_pedido_compra'] = pedido_compra

        # Criar pedido
        order_id = self.execute('sale.order', 'create', order_data)

        print(f"✅ Pedido criado - ID: {order_id}")

        return order_id

    def calcular_impostos(self, order_id: int) -> bool:
        """
        Dispara cálculo de impostos brasileiros

        Args:
            order_id: ID do pedido

        Returns:
            True se executado com sucesso
        """
        try:
            self.execute(
                'sale.order',
                'onchange_l10n_br_calcular_imposto',
                [order_id]
            )
            print(f"✅ Impostos calculados para pedido {order_id}")
            return True
        except Exception as e:
            # O método retorna None, causando erro de serialização
            # mas o cálculo é executado mesmo assim
            if "cannot marshal None" in str(e):
                print(f"✅ Impostos calculados para pedido {order_id} (retorno None esperado)")
                return True
            else:
                print(f"❌ Erro ao calcular impostos: {e}")
                return False

    def confirmar_pedido(self, order_id: int) -> bool:
        """
        Confirma o pedido (draft -> sale)

        Args:
            order_id: ID do pedido

        Returns:
            True se confirmado com sucesso
        """
        try:
            self.execute('sale.order', 'action_confirm', [order_id])
            print(f"✅ Pedido {order_id} confirmado")
            return True
        except Exception as e:
            print(f"❌ Erro ao confirmar pedido: {e}")
            return False

    def destravar_pedido(self, order_id: int) -> bool:
        """
        Destrava pedido para edição

        Args:
            order_id: ID do pedido

        Returns:
            True se destravado com sucesso
        """
        try:
            self.execute('sale.order', 'action_unlock', [order_id])
            print(f"✅ Pedido {order_id} destravado")
            return True
        except Exception as e:
            print(f"❌ Erro ao destravar pedido: {e}")
            return False

    def travar_pedido(self, order_id: int) -> bool:
        """
        Trava pedido após edição

        Args:
            order_id: ID do pedido

        Returns:
            True se travado com sucesso
        """
        try:
            self.execute('sale.order', 'action_lock', [order_id])
            print(f"✅ Pedido {order_id} travado")
            return True
        except Exception as e:
            print(f"❌ Erro ao travar pedido: {e}")
            return False

    def ler_pedido(self, order_id: int) -> Dict:
        """
        Lê dados completos do pedido

        Args:
            order_id: ID do pedido

        Returns:
            Dados do pedido
        """
        fields = [
            'name', 'state', 'locked',
            'partner_id', 'date_order',
            'amount_untaxed', 'amount_tax', 'amount_total',
            'l10n_br_operacao_id', 'l10n_br_cfop_id',
            'l10n_br_icms_valor', 'l10n_br_icms_base',
            'l10n_br_ipi_valor', 'l10n_br_pis_valor', 'l10n_br_cofins_valor',
            'l10n_br_total_tributos', 'l10n_br_total_nfe',
            'order_line'
        ]

        pedidos = self.execute('sale.order', 'read', [order_id], fields=fields)
        return pedidos[0] if pedidos else {}

    def ler_linhas_pedido(self, order_id: int) -> List[Dict]:
        """
        Lê linhas do pedido

        Args:
            order_id: ID do pedido

        Returns:
            Lista de linhas do pedido
        """
        fields = [
            'product_id', 'name', 'product_uom_qty', 'price_unit',
            'price_subtotal', 'price_total',
            'l10n_br_cfop_id', 'l10n_br_ncm_id',
            'l10n_br_icms_valor', 'l10n_br_icms_aliquota',
            'l10n_br_ipi_valor', 'l10n_br_pis_valor', 'l10n_br_cofins_valor',
            'l10n_br_total_nfe'
        ]

        return self.execute(
            'sale.order.line', 'search_read',
            [['order_id', '=', order_id]],
            fields=fields
        )


def exemplo_criar_pedido():
    """Exemplo de uso completo"""

    # Configuração de conexão
    # ⚠️ Em produção, use variáveis de ambiente!
    config = {
        'url': 'https://odoo.nacomgoya.com.br',
        'database': 'odoo-17-ee-nacomgoya-prd',
        'username': 'rafael@conservascampobelo.com.br',
        'api_key': '67705b0986ff5c052e657f1c0ffd96ceb191af69'
    }

    # Criar cliente
    odoo = OdooSaleOrderCreator(**config)

    # =====================================================
    # EXEMPLO 1: Listar operações fiscais disponíveis
    # =====================================================
    print("\n" + "="*60)
    print("OPERAÇÕES FISCAIS DE VENDA DISPONÍVEIS")
    print("="*60)

    operacoes = odoo.listar_operacoes_fiscais_venda()
    for op in operacoes[:10]:  # Mostrar apenas 10
        print(f"  ID: {op['id']:5} | {op['name']}")

    # =====================================================
    # EXEMPLO 2: Criar pedido (SEM EXECUTAR - apenas demonstração)
    # =====================================================
    print("\n" + "="*60)
    print("ESTRUTURA DE CRIAÇÃO DE PEDIDO (demonstração)")
    print("="*60)

    # IDs de exemplo (substituir pelos IDs reais)
    CLIENTE_ID = 87810  # NUTRICIONALE
    EMPRESA_ID = 4  # NACOM GOYA - CD
    OPERACAO_FISCAL_ID = 2768  # Venda de produção do estabelecimento
    PRICELIST_ID = 11  # TABELA PADRÃO (BRL)

    # Linhas de exemplo
    linhas_exemplo = [
        {
            'product_id': 12345,  # Substituir por ID real
            'product_uom_qty': 10.0,
            'price_unit': 100.00
        },
        {
            'product_id': 12346,  # Substituir por ID real
            'product_uom_qty': 5.0,
            'price_unit': 200.00
        }
    ]

    print(f"""
    Para criar um pedido, use:

    order_id = odoo.criar_pedido_venda(
        partner_id={CLIENTE_ID},
        company_id={EMPRESA_ID},
        operacao_fiscal_id={OPERACAO_FISCAL_ID},
        pricelist_id={PRICELIST_ID},
        linhas={linhas_exemplo},
        pedido_compra='PC-12345',  # Opcional
        imposto_auto=True  # Calcular impostos automaticamente
    )

    # Calcular impostos manualmente (se necessário)
    odoo.calcular_impostos(order_id)

    # Confirmar pedido
    odoo.confirmar_pedido(order_id)
    """)

    # =====================================================
    # EXEMPLO 3: Ler um pedido existente
    # =====================================================
    print("\n" + "="*60)
    print("EXEMPLO DE PEDIDO EXISTENTE")
    print("="*60)

    pedido = odoo.ler_pedido(68539)  # VCD2565408

    print(f"""
    Pedido: {pedido.get('name')}
    Estado: {pedido.get('state')}
    Travado: {pedido.get('locked')}
    Cliente: {pedido.get('partner_id')}

    Valores:
    - Subtotal: R$ {pedido.get('amount_untaxed', 0):.2f}
    - Impostos: R$ {pedido.get('amount_tax', 0):.2f}
    - Total:    R$ {pedido.get('amount_total', 0):.2f}

    Impostos Brasileiros:
    - ICMS:    R$ {pedido.get('l10n_br_icms_valor', 0):.2f}
    - IPI:     R$ {pedido.get('l10n_br_ipi_valor', 0):.2f}
    - PIS:     R$ {pedido.get('l10n_br_pis_valor', 0):.2f}
    - COFINS:  R$ {pedido.get('l10n_br_cofins_valor', 0):.2f}
    - Total:   R$ {pedido.get('l10n_br_total_tributos', 0):.2f}

    Operação Fiscal: {pedido.get('l10n_br_operacao_id')}
    CFOP: {pedido.get('l10n_br_cfop_id')}
    """)


if __name__ == "__main__":
    exemplo_criar_pedido()
