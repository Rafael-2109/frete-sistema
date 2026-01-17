"""
Serviço de Emissão de NF de Pallet no Odoo
==========================================

Cria picking de expedição de vasilhame e emite a NF-e correspondente.

Fluxo:
    1. Criar stock.picking (tipo: Expedição Pallet/Vasilhame)
    2. Confirmar picking (action_confirm)
    3. Atribuir estoque (action_assign)
    4. Preencher quantidade feita (qty_done)
    5. Validar picking (button_validate)
    6. Criar account.move (fatura de remessa)
    7. Postar fatura (action_post) - emite NF-e

Autor: Sistema de Fretes
Data: 02/01/2026
"""

import sys
import os
from datetime import datetime
from typing import Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from app.odoo.utils.connection import get_odoo_connection # noqa: E402


# ==============================================================================
# CONFIGURAÇÃO POR EMPRESA
# ==============================================================================

EMPRESA_CONFIG = {
    'CD': {
        'company_id': 4,
        'company_name': 'NACOM GOYA - CD',
        'picking_type_id': 84,           # Expedição Pallet (CD)
        'picking_type_name': 'Expedição Pallet (CD)',
        'sequence_code': 'CD/PALLET',
        'location_id': 32,               # CD/Estoque
        'location_dest_id': 5,           # Parceiros/Clientes
        'journal_id': 831,               # REMESSA DE VASILHAME
        'fiscal_position_id': 46,        # REMESSA DE VASILHAME
    },
    'FB': {
        'company_id': 1,
        'company_name': 'NACOM GOYA - FB',
        'picking_type_id': 93,           # Expedição Vasilhame (FB)
        'picking_type_name': 'Expedição Vasilhame (FB)',
        'sequence_code': 'FB/SAI/VAS',
        'location_id': 8,                # FB/Estoque
        'location_dest_id': 5,           # Parceiros/Clientes
        'journal_id': 390,               # REMESSA DE VASILHAME
        'fiscal_position_id': 17,        # REMESSA DE VASILHAME
    },
    'SC': {
        'company_id': 3,
        'company_name': 'NACOM GOYA - SC',
        'picking_type_id': 90,           # Expedição Vasilhame (SC)
        'picking_type_name': 'Expedição Vasilhame (SC)',
        'sequence_code': 'SC/SAI/VAS',
        'location_id': 22,               # SC/Estoque
        'location_dest_id': 5,           # Parceiros/Clientes
        'journal_id': 810,               # REMESSA DE VASILHAME
        'fiscal_position_id': 37,        # REMESSA DE VASILHAME
    },
}

# Produto PALLET (fixo para todas as empresas)
PRODUTO_PALLET = {
    'product_id': 28108,
    'product_code': '208000012',
    'product_name': '[208000012] PALLET',
    'price_unit': 35.00,
    'account_id': 26846,                 # 1150100012 FATURAMENTO FISICO FISCAL
    'product_uom': 1,                    # Units
}

# Condição de pagamento (fixo)
PAYMENT_TERM_ID = 2800  # A VISTA


# ==============================================================================
# FUNÇÕES AUXILIARES
# ==============================================================================

def validar_cliente(odoo, cliente_id: int) -> Dict[str, Any]:
    """Valida se o cliente existe e retorna seus dados"""
    clientes = odoo.search_read(
        'res.partner',
        [['id', '=', cliente_id]],
        ['id', 'name', 'l10n_br_cnpj', 'l10n_br_municipio_id', 'state_id'],
        limit=1
    )
    if not clientes:
        raise ValueError(f"Cliente ID {cliente_id} não encontrado no Odoo")
    return clientes[0]


def validar_transportadora(odoo, transportadora_id: int) -> Dict[str, Any]:
    """Valida se a transportadora existe e retorna seus dados"""
    transportadoras = odoo.search_read(
        'delivery.carrier',
        [['id', '=', transportadora_id]],
        ['id', 'name'],
        limit=1
    )
    if not transportadoras:
        raise ValueError(f"Transportadora ID {transportadora_id} não encontrada no Odoo")
    return transportadoras[0]


def criar_picking(odoo, config: Dict, cliente_id: int, transportadora_id: int,
                  quantidade: int) -> int:
    """
    Cria o picking de expedição de pallet

    Args:
        odoo: Conexão com Odoo
        config: Configuração da empresa
        cliente_id: ID do cliente (res.partner)
        transportadora_id: ID da transportadora (delivery.carrier)
        quantidade: Quantidade de pallets

    Returns:
        int: ID do picking criado
    """
    picking_vals = {
        'picking_type_id': config['picking_type_id'],
        'location_id': config['location_id'],
        'location_dest_id': config['location_dest_id'],
        'partner_id': cliente_id,
        'carrier_id': transportadora_id,
        'company_id': config['company_id'],
        'scheduled_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'move_ids': [(0, 0, {
            'name': PRODUTO_PALLET['product_name'],
            'product_id': PRODUTO_PALLET['product_id'],
            'product_uom_qty': quantidade,
            'product_uom': PRODUTO_PALLET['product_uom'],
            'location_id': config['location_id'],
            'location_dest_id': config['location_dest_id'],
        })]
    }

    picking_id = odoo.create('stock.picking', picking_vals)
    return picking_id


def confirmar_picking(odoo, picking_id: int) -> None:
    """Confirma o picking (reserva estoque)"""
    odoo.execute('stock.picking', 'action_confirm', [picking_id])


def atribuir_picking(odoo, picking_id: int) -> None:
    """Verifica disponibilidade e atribui estoque"""
    odoo.execute('stock.picking', 'action_assign', [picking_id])


def preencher_quantidade_feita(odoo, picking_id: int, quantidade: int) -> None:
    """Preenche a quantidade feita (qty_done) nas linhas do movimento"""
    move_lines = odoo.search_read(
        'stock.move.line',
        [['picking_id', '=', picking_id]],
        ['id']
    )

    for ml in move_lines:
        odoo.write('stock.move.line', ml['id'], {'quantity': quantidade})


def validar_picking(odoo, picking_id: int) -> None:
    """Valida o picking (conclui a transferência)"""
    odoo.execute('stock.picking', 'button_validate', [picking_id])


def criar_fatura(odoo, config: Dict, cliente_id: int, transportadora_id: int,
                 picking_id: int, quantidade: int) -> int:
    """
    Cria a fatura (account.move) de remessa de vasilhame

    Args:
        odoo: Conexão com Odoo
        config: Configuração da empresa
        cliente_id: ID do cliente
        transportadora_id: ID da transportadora
        picking_id: ID do picking vinculado
        quantidade: Quantidade de pallets

    Returns:
        int: ID da fatura criada
    """
    invoice_vals = {
        'move_type': 'out_invoice',
        'journal_id': config['journal_id'],
        'partner_id': cliente_id,
        'fiscal_position_id': config['fiscal_position_id'],
        'invoice_payment_term_id': PAYMENT_TERM_ID,
        'company_id': config['company_id'],
        'picking_ids': [(6, 0, [picking_id])],
        'l10n_br_carrier_id': transportadora_id,
        'invoice_line_ids': [(0, 0, {
            'product_id': PRODUTO_PALLET['product_id'],
            'quantity': quantidade,
            'price_unit': PRODUTO_PALLET['price_unit'],
            'name': PRODUTO_PALLET['product_name'],
        })]
    }

    invoice_id = odoo.create('account.move', invoice_vals)
    return invoice_id


def postar_fatura(odoo, invoice_id: int) -> None:
    """Posta a fatura (emite a NF-e)"""
    odoo.execute('account.move', 'action_post', [invoice_id])


def buscar_dados_fatura(odoo, invoice_id: int) -> Dict[str, Any]:
    """Busca os dados da fatura emitida"""
    faturas = odoo.search_read(
        'account.move',
        [['id', '=', invoice_id]],
        ['id', 'name', 'ref', 'state', 'l10n_br_numero_nota_fiscal',
         'l10n_br_chave_nf', 'l10n_br_situacao_nf'],
        limit=1
    )
    return faturas[0] if faturas else {}


def buscar_dados_picking(odoo, picking_id: int) -> Dict[str, Any]:
    """Busca os dados do picking"""
    pickings = odoo.search_read(
        'stock.picking',
        [['id', '=', picking_id]],
        ['id', 'name', 'state', 'date_done'],
        limit=1
    )
    return pickings[0] if pickings else {}


# ==============================================================================
# FUNÇÃO PRINCIPAL
# ==============================================================================

def emitir_nf_pallet(
    empresa: str,
    cliente_id: int,
    transportadora_id: int,
    quantidade: int,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Emite uma NF de Pallet completa (picking + fatura)

    Args:
        empresa: Código da empresa (CD, FB, SC)
        cliente_id: ID do cliente no Odoo (res.partner)
        transportadora_id: ID da transportadora no Odoo (delivery.carrier)
        quantidade: Quantidade de pallets
        dry_run: Se True, apenas simula sem criar registros

    Returns:
        Dict com os dados do picking e fatura criados:
        {
            'sucesso': bool,
            'picking': {'id': int, 'name': str, ...},
            'fatura': {'id': int, 'name': str, 'l10n_br_numero_nota_fiscal': str, ...},
            'etapas': [str, ...],
            'erro': str or None
        }
    """
    resultado = {
        'sucesso': False,
        'empresa': empresa,
        'cliente_id': cliente_id,
        'transportadora_id': transportadora_id,
        'quantidade': quantidade,
        'dry_run': dry_run,
        'picking': None,
        'fatura': None,
        'erro': None,
        'etapas': []
    }

    # Validar empresa
    if empresa not in EMPRESA_CONFIG:
        resultado['erro'] = f"Empresa inválida: {empresa}. Use: CD, FB ou SC"
        return resultado

    config = EMPRESA_CONFIG[empresa]
    resultado['config'] = {
        'company_name': config['company_name'],
        'picking_type_name': config['picking_type_name'],
        'journal_id': config['journal_id'],
    }

    try:
        # Conectar ao Odoo
        odoo = get_odoo_connection()
        if not odoo.authenticate():
            resultado['erro'] = "Falha na autenticação com Odoo"
            return resultado

        resultado['etapas'].append("Conectado ao Odoo")

        # Validar cliente
        cliente = validar_cliente(odoo, cliente_id)
        resultado['cliente'] = cliente
        resultado['etapas'].append(f"Cliente validado: {cliente['name']}")

        # Validar transportadora
        transportadora = validar_transportadora(odoo, transportadora_id)
        resultado['transportadora'] = transportadora
        resultado['etapas'].append(f"Transportadora validada: {transportadora['name']}")

        if dry_run:
            resultado['etapas'].append("Modo DRY-RUN: nenhum registro será criado")
            resultado['sucesso'] = True
            resultado['picking'] = {'simulado': True}
            resultado['fatura'] = {'simulado': True}
            return resultado

        # ETAPA 1: Criar picking
        picking_id = criar_picking(odoo, config, cliente_id, transportadora_id, quantidade)
        resultado['etapas'].append(f"Picking criado: ID {picking_id}")

        # ETAPA 2: Confirmar picking
        confirmar_picking(odoo, picking_id)
        resultado['etapas'].append("Picking confirmado")

        # ETAPA 3: Atribuir estoque
        atribuir_picking(odoo, picking_id)
        resultado['etapas'].append("Estoque atribuído")

        # ETAPA 4: Preencher quantidade feita
        preencher_quantidade_feita(odoo, picking_id, quantidade)
        resultado['etapas'].append(f"Quantidade preenchida: {quantidade}")

        # ETAPA 5: Validar picking
        validar_picking(odoo, picking_id)
        resultado['etapas'].append("Picking validado (done)")

        # Buscar dados do picking
        picking_data = buscar_dados_picking(odoo, picking_id)
        resultado['picking'] = picking_data

        # ETAPA 6: Criar fatura
        invoice_id = criar_fatura(odoo, config, cliente_id, transportadora_id,
                                 picking_id, quantidade)  # type: ignore
        resultado['etapas'].append(f"Fatura criada: ID {invoice_id}")

        # ETAPA 7: Postar fatura (emitir NF-e)
        postar_fatura(odoo, invoice_id)
        resultado['etapas'].append("Fatura postada (NF-e emitida)")

        # Buscar dados da fatura
        fatura_data = buscar_dados_fatura(odoo, invoice_id)
        resultado['fatura'] = fatura_data

        resultado['sucesso'] = True
        resultado['etapas'].append(f"CONCLUÍDO - NF-e: {fatura_data.get('l10n_br_numero_nota_fiscal', 'N/A')}")

    except Exception as e:
        resultado['erro'] = str(e)
        resultado['etapas'].append(f"ERRO: {str(e)}")

    return resultado
