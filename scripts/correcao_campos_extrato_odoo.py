# -*- coding: utf-8 -*-
"""
Script de Correção: Campos do Extrato Bancário no Odoo
=====================================================

Corrige lançamentos feitos ANTES do commit 13cef821 (deploy 2026-02-03T21:48:25Z)
que não gravaram os 3 campos obrigatórios do extrato:

1. partner_id na account.bank.statement.line
2. payment_ref na account.bank.statement.line + name nas account.move.line
3. account_id na account.move.line (TRANSITÓRIA 22199 → PENDENTES 26868)

FONTE DE DADOS:
- Dados dos registros afetados: JSON extraído via MCP Render
- Operações no Odoo: XML-RPC via OdooConnection

TIPOS de registros afetados:
- TIPO 1: lancamento_comprovante (pagamentos fornecedor) — 20 registros (1 já correto)
- TIPO 2: extrato_item (conciliações de extrato/recebimento) — ~1.504 registros

Uso:
    # Verificar estado de 1 comprovante (sem alterar)
    python scripts/correcao_campos_extrato_odoo.py --verificar-comprovante 2

    # Corrigir 1 comprovante (teste)
    python scripts/correcao_campos_extrato_odoo.py --corrigir-comprovante 2

    # Verificar estado de 1 extrato_item (sem alterar)
    python scripts/correcao_campos_extrato_odoo.py --verificar-extrato 19305

    # Corrigir 1 extrato_item (teste)
    python scripts/correcao_campos_extrato_odoo.py --corrigir-extrato 19305

    # Corrigir TODOS os comprovantes
    python scripts/correcao_campos_extrato_odoo.py --batch-comprovantes

    # Corrigir TODOS os extratos (em lotes de 50)
    python scripts/correcao_campos_extrato_odoo.py --batch-extratos

    # Verificação final (amostragem)
    python scripts/correcao_campos_extrato_odoo.py --verificar-amostra
"""

import sys
import os
import json
import argparse
import time
import logging
import random

# Carregar .env ANTES de importar módulos do app
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
except ImportError:
    pass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.odoo.utils.connection import get_odoo_connection

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =========================================================================
# CONSTANTES
# =========================================================================

CONTA_TRANSITORIA = 22199
CONTA_PAGAMENTOS_PENDENTES = 26868

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COMPROVANTES_JSON = os.path.join(SCRIPT_DIR, 'dados_correcao_comprovantes.json')
EXTRATOS_JSON = os.path.join(SCRIPT_DIR, 'dados_correcao_extratos.json')


# =========================================================================
# CARREGAMENTO DE DADOS (JSON)
# =========================================================================

def carregar_comprovantes() -> list:
    """Carrega dados dos comprovantes do JSON extraído do Render."""
    with open(COMPROVANTES_JSON, 'r', encoding='utf-8') as f:
        return json.load(f)


def carregar_extratos() -> list:
    """Carrega dados dos extratos do JSON extraído do Render."""
    with open(EXTRATOS_JSON, 'r', encoding='utf-8') as f:
        return json.load(f)


def buscar_comprovante_por_id(lancamento_id: int) -> dict | None:
    """Busca um comprovante específico no JSON pelo ID."""
    comprovantes = carregar_comprovantes()
    for comp in comprovantes:
        if comp['id'] == lancamento_id:
            return comp
    return None


def buscar_extrato_por_id(item_id: int) -> dict | None:
    """Busca um extrato_item específico no JSON pelo ID."""
    extratos = carregar_extratos()
    for ext in extratos:
        if ext['id'] == item_id:
            return ext
    return None


# =========================================================================
# FORMATAÇÃO DE RÓTULO (reimplementado para não depender do Flask app)
# =========================================================================

def formatar_rotulo_pagamento(valor: float, nome_fornecedor: str, data_pagamento: str) -> str:
    """
    Formata o rótulo padrão para pagamentos de fornecedor.
    Reimplementação de BaixaPagamentosService.formatar_rotulo_pagamento()

    Padrão: "Pagamento de fornecedor R$ {valor} - {fornecedor} - {data}"
    """
    valor_formatado = f"{valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

    # data_pagamento vem como "2026-01-30" ou "2026-01-30T00:00:00Z"
    data_str = str(data_pagamento)[:10]  # Pegar apenas YYYY-MM-DD
    try:
        from datetime import datetime
        dt = datetime.strptime(data_str, '%Y-%m-%d')
        data_str = dt.strftime('%d/%m/%Y')
    except (ValueError, TypeError):
        pass

    return f"Pagamento de fornecedor R$ {valor_formatado} - {nome_fornecedor} - {data_str}"


# =========================================================================
# FUNÇÕES DE VERIFICAÇÃO (READ-ONLY)
# =========================================================================

def verificar_statement_line(connection, statement_line_id: int) -> dict:
    """Busca estado atual de uma account.bank.statement.line no Odoo."""
    result = connection.search_read(
        'account.bank.statement.line',
        [['id', '=', statement_line_id]],
        fields=['id', 'partner_id', 'payment_ref', 'is_reconciled', 'amount'],
        limit=1
    )
    if not result:
        return {}
    return result[0]


def verificar_move_lines(connection, move_id: int) -> list:
    """Busca move lines de um account.move do extrato."""
    return connection.search_read(
        'account.move.line',
        [['move_id', '=', move_id]],
        fields=['id', 'name', 'account_id', 'debit', 'credit', 'partner_id', 'reconciled']
    )


def verificar_estado_completo(connection, statement_line_id: int, move_id: int) -> dict:
    """Verifica estado completo dos 3 campos no Odoo."""
    stmt = verificar_statement_line(connection, statement_line_id)
    lines = verificar_move_lines(connection, move_id)

    if not stmt:
        return {'erro': f'statement_line {statement_line_id} não encontrada'}

    # Analisar campos
    partner_ok = bool(stmt.get('partner_id') and stmt['partner_id'] is not False)
    payment_ref_ok = bool(stmt.get('payment_ref') and stmt['payment_ref'] is not False)

    # Verificar account_id das move lines
    # NOTA: Para pagamentos (fornecedor), a conta TRANSITÓRIA está na linha de DÉBITO
    #       Para recebimentos (extrato), a conta TRANSITÓRIA está na linha de CRÉDITO
    #       Verificamos AMBOS os casos
    conta_transitoria_encontrada = False
    conta_pendentes_encontrada = False
    for line in lines:
        account = line.get('account_id')
        account_id = account[0] if isinstance(account, (list, tuple)) else account
        has_value = line.get('debit', 0) > 0 or line.get('credit', 0) > 0
        if account_id == CONTA_TRANSITORIA and has_value:
            conta_transitoria_encontrada = True
        if account_id == CONTA_PAGAMENTOS_PENDENTES and has_value:
            conta_pendentes_encontrada = True

    account_ok = conta_pendentes_encontrada and not conta_transitoria_encontrada

    return {
        'statement_line': stmt,
        'move_lines': lines,
        'partner_ok': partner_ok,
        'partner_id': stmt.get('partner_id'),
        'payment_ref_ok': payment_ref_ok,
        'payment_ref': stmt.get('payment_ref'),
        'account_ok': account_ok,
        'conta_transitoria_encontrada': conta_transitoria_encontrada,
        'conta_pendentes_encontrada': conta_pendentes_encontrada,
        'is_reconciled': stmt.get('is_reconciled'),
        'todos_ok': partner_ok and payment_ref_ok and account_ok,
    }


# =========================================================================
# FUNÇÕES DE CORREÇÃO
# =========================================================================

def desconciliar_move_extrato(connection, move_id: int) -> dict:
    """
    Desconcilia TODAS as move lines do extrato E coloca o move em draft.
    Retorna info para reconciliar novamente depois.

    Fluxo:
    1. Coletar partial reconciles e contrapartidas (identifica quem é do extrato vs payment)
    2. Deletar partial reconciles (desconciliar)
    3. Colocar move em draft (button_draft) para permitir edição

    Returns:
        Dict com partial_reconcile_ids e counterpart_ids (IDs das move lines do PAYMENT)
    """
    info = {'partial_ids': [], 'counterpart_ids': [], 'desconciliou': False, 'move_id': move_id}

    # Buscar TODAS as move lines do extrato
    linhas = connection.search_read(
        'account.move.line',
        [['move_id', '=', move_id]],
        fields=['id', 'reconciled', 'matched_debit_ids', 'matched_credit_ids']
    )

    extrato_line_ids = {ln['id'] for ln in linhas}

    for line in linhas:
        # Coletar de matched_credit_ids E matched_debit_ids
        all_pr_ids = list(line.get('matched_credit_ids', [])) + list(line.get('matched_debit_ids', []))

        for pr_id in all_pr_ids:
            if pr_id not in info['partial_ids']:
                pr = connection.search_read(
                    'account.partial.reconcile',
                    [['id', '=', pr_id]],
                    fields=['debit_move_id', 'credit_move_id'],
                    limit=1
                )
                if pr:
                    debit_id = pr[0]['debit_move_id']
                    credit_id = pr[0]['credit_move_id']
                    debit_id = debit_id[0] if isinstance(debit_id, (list, tuple)) else debit_id
                    credit_id = credit_id[0] if isinstance(credit_id, (list, tuple)) else credit_id

                    # Identificar qual é a CONTRAPARTIDA (move line do payment, não do extrato)
                    # A counterpart é a que NÃO pertence ao move do extrato
                    if debit_id in extrato_line_ids and credit_id not in extrato_line_ids:
                        info['counterpart_ids'].append(credit_id)
                    elif credit_id in extrato_line_ids and debit_id not in extrato_line_ids:
                        info['counterpart_ids'].append(debit_id)
                    else:
                        # Ambas do mesmo move (raro) ou ambas externas - salvar as duas
                        logger.warning(f"    desconciliar: Par ambíguo pr={pr_id}: debit={debit_id} credit={credit_id}")
                        if debit_id not in extrato_line_ids:
                            info['counterpart_ids'].append(debit_id)
                        if credit_id not in extrato_line_ids:
                            info['counterpart_ids'].append(credit_id)

                info['partial_ids'].append(pr_id)

    # 1. Deletar partial reconciles (desconciliar)
    if info['partial_ids']:
        connection.execute_kw(
            'account.partial.reconcile',
            'unlink',
            [info['partial_ids']]
        )
        info['desconciliou'] = True
        logger.info(f"    desconciliar: Removeu {len(info['partial_ids'])} partial_reconcile(s)")

    # 2. Colocar move em draft para permitir edição
    try:
        connection.execute_kw(
            'account.move',
            'button_draft',
            [[move_id]]
        )
        info['move_em_draft'] = True
        logger.info(f"    desconciliar: Move {move_id} → draft")
    except Exception as e:
        logger.warning(f"    desconciliar: ⚠️ Falha ao colocar move em draft: {e}")
        info['move_em_draft'] = False

    return info


def reconciliar_novamente(connection, info_desconciliacao: dict):
    """
    Re-posta o move e re-reconcilia.

    Após button_draft + action_post, as move lines podem ter NOVOS IDs.
    Por isso, precisamos buscar as novas linhas pela conta PENDENTES (debit)
    e reconciliar com a contrapartida do payment (credit na mesma conta).
    """
    move_id = info_desconciliacao.get('move_id')

    # 1. Re-postar o move (draft → posted)
    if info_desconciliacao.get('move_em_draft') and move_id:
        try:
            connection.execute_kw(
                'account.move',
                'action_post',
                [[move_id]]
            )
            logger.info(f"    reconciliar: Move {move_id} → posted")
        except Exception as e:
            logger.warning(f"    reconciliar: ⚠️ Falha ao postar move {move_id}: {e}")

    # 2. Buscar a NOVA move line do extrato (conta PENDENTES, não reconciliada)
    # Após action_post, o Odoo pode ter recriado as move lines com novos IDs
    new_pendentes_lines = connection.search_read(
        'account.move.line',
        [
            ['move_id', '=', move_id],
            ['account_id', '=', CONTA_PAGAMENTOS_PENDENTES],
            ['reconciled', '=', False]
        ],
        fields=['id', 'debit', 'credit'],
        limit=1
    )

    if not new_pendentes_lines:
        logger.info("    reconciliar: Sem linha PENDENTES não-reconciliada para reconciliar")
        return

    new_line_id = new_pendentes_lines[0]['id']

    # 3. Reconciliar a nova move line do extrato com as contrapartidas do payment
    # counterpart_ids são as move lines que NÃO pertencem ao move do extrato
    for counterpart_id in info_desconciliacao.get('counterpart_ids', []):
        try:
            connection.execute_kw(
                'account.move.line',
                'reconcile',
                [[new_line_id, counterpart_id]]
            )
            logger.info(f"    reconciliar: Re-reconciliado lines [{new_line_id}, {counterpart_id}]")
        except Exception as e:
            logger.warning(f"    reconciliar: ⚠️ Falha ao reconciliar [{new_line_id}, {counterpart_id}]: {e}")


def corrigir_account_id(connection, move_id: int) -> bool:
    """
    Troca account_id de TRANSITÓRIA → PENDENTES.
    NOTA: Move DEVE estar em draft para esta operação funcionar.
    Após button_draft, as move lines podem ter sido recriadas com novos IDs.

    Busca linha com account_id=TRANSITÓRIA (tanto debit quanto credit),
    pois pagamentos usam debit e recebimentos usam credit.
    """
    linhas = connection.search_read(
        'account.move.line',
        [
            ['move_id', '=', move_id],
            ['account_id', '=', CONTA_TRANSITORIA],
        ],
        fields=['id', 'debit', 'credit'],
        limit=1
    )

    if not linhas:
        logger.info(f"    account_id: Já OK (não encontrou linha com conta {CONTA_TRANSITORIA})")
        return False

    line_id = linhas[0]['id']
    connection.execute_kw(
        'account.move.line',
        'write',
        [[line_id], {'account_id': CONTA_PAGAMENTOS_PENDENTES}]
    )
    logger.info(f"    account_id: Corrigido move_line {line_id} → {CONTA_TRANSITORIA} → {CONTA_PAGAMENTOS_PENDENTES}")
    return True


def corrigir_partner_id(connection, statement_line_id: int, partner_id: int) -> bool:
    """Operação 2: Atualizar partner_id na statement line."""
    stmt = verificar_statement_line(connection, statement_line_id)
    if not stmt:
        logger.warning(f"    partner_id: statement_line {statement_line_id} não encontrada!")
        return False

    current_partner = stmt.get('partner_id')
    current_partner_id = current_partner[0] if isinstance(current_partner, (list, tuple)) else current_partner

    if current_partner_id == partner_id:
        logger.info(f"    partner_id: Já OK (partner_id={partner_id})")
        return False

    connection.execute_kw(
        'account.bank.statement.line',
        'write',
        [[statement_line_id], {'partner_id': partner_id}]
    )
    logger.info(f"    partner_id: Corrigido statement_line {statement_line_id} → partner_id={partner_id}")
    return True


def corrigir_rotulo(connection, statement_line_id: int, move_id: int, rotulo: str) -> bool:
    """Operação 3: Atualizar payment_ref na statement line + name nas move lines."""
    # 1. Atualizar payment_ref da statement line
    connection.execute_kw(
        'account.bank.statement.line',
        'write',
        [[statement_line_id], {'payment_ref': rotulo}]
    )

    # 2. Atualizar name das move lines do extrato
    linhas = connection.search_read(
        'account.move.line',
        [['move_id', '=', move_id]],
        fields=['id']
    )
    if linhas:
        line_ids = [ln['id'] for ln in linhas]
        connection.execute_kw(
            'account.move.line',
            'write',
            [line_ids, {'name': rotulo}]
        )

    rotulo_preview = rotulo[:60] + '...' if len(rotulo) > 60 else rotulo
    logger.info(f"    rótulo: Corrigido → '{rotulo_preview}'")
    return True


# =========================================================================
# CORREÇÃO TIPO 1: COMPROVANTES DE PAGAMENTO
# =========================================================================

def verificar_comprovante(connection, lancamento_id: int):
    """Verifica estado de 1 comprovante no Odoo."""
    comp = buscar_comprovante_por_id(lancamento_id)
    if not comp:
        logger.error(f"Lançamento {lancamento_id} não encontrado no JSON")
        return None

    logger.info("=" * 70)
    logger.info(f"VERIFICANDO COMPROVANTE - Lançamento ID: {lancamento_id}")
    logger.info(f"  NF: {comp['nf_numero']}")
    logger.info(f"  Fornecedor: {comp['odoo_partner_name']} (partner_id={comp['odoo_partner_id']})")
    logger.info(f"  Valor: R$ {comp['valor_pago']:.2f}")
    logger.info(f"  Data pagamento: {comp['data_pagamento']}")
    logger.info(f"  Statement Line ID: {comp['odoo_statement_line_id']}")
    logger.info(f"  Move ID (extrato): {comp['odoo_move_id']}")
    logger.info("-" * 70)

    estado = verificar_estado_completo(connection, comp['odoo_statement_line_id'], comp['odoo_move_id'])

    if estado.get('erro'):
        logger.error(f"  ❌ {estado['erro']}")
        return None

    logger.info(f"  partner_id: {'✅ OK' if estado['partner_ok'] else '❌ FALTA'} → {estado['partner_id']}")
    logger.info(f"  payment_ref: {'✅ OK' if estado['payment_ref_ok'] else '❌ FALTA'} → {estado['payment_ref']}")
    logger.info(f"  account_id: {'✅ OK' if estado['account_ok'] else '❌ INCORRETO (TRANSITÓRIA)'}")
    logger.info(f"  is_reconciled: {estado['is_reconciled']}")
    logger.info(f"  TODOS OK: {'✅ SIM' if estado['todos_ok'] else '❌ NÃO - PRECISA CORREÇÃO'}")

    # Mostrar move lines
    for line in estado['move_lines']:
        account = line.get('account_id')
        account_str = f"{account[0]} ({account[1]})" if isinstance(account, (list, tuple)) else str(account)
        partner = line.get('partner_id')
        partner_str = f"{partner[0]} ({partner[1]})" if isinstance(partner, (list, tuple)) else str(partner)
        logger.info(
            f"    move_line {line['id']}: "
            f"D={line.get('debit', 0):.2f} C={line.get('credit', 0):.2f} "
            f"conta={account_str} partner={partner_str} name='{line.get('name', '')[:50]}'"
        )

    return estado


def corrigir_comprovante(connection, lancamento_id: int) -> dict:
    """
    Corrige os 3 campos de 1 comprovante no Odoo.

    Fluxo:
    1. Desconciliar move do extrato (liberar para edição)
    2. Trocar account_id (TRANSITÓRIA → PENDENTES)
    3. Atualizar partner_id na statement_line
    4. Atualizar rótulo (payment_ref + name)
    5. Reconciliar novamente
    """
    comp = buscar_comprovante_por_id(lancamento_id)
    if not comp:
        return {'erro': f'Lançamento {lancamento_id} não encontrado no JSON'}

    logger.info("=" * 70)
    logger.info(f"CORRIGINDO COMPROVANTE - Lançamento ID: {lancamento_id}")
    logger.info(f"  NF: {comp['nf_numero']} | Fornecedor: {comp['odoo_partner_name']}")
    logger.info(f"  Valor: R$ {comp['valor_pago']:.2f} | Data: {comp['data_pagamento']}")

    # Verificar estado ANTES
    estado_antes = verificar_estado_completo(connection, comp['odoo_statement_line_id'], comp['odoo_move_id'])
    if estado_antes.get('todos_ok'):
        logger.info("  ✅ Já está correto - pulando")
        return {'sucesso': True, 'ja_correto': True}

    # PASSO 1: Desconciliar + button_draft (liberar para edição)
    info_recon = desconciliar_move_extrato(connection, comp['odoo_move_id'])

    # PASSO 2: Atualizar partner_id (statement_line - não recria move lines)
    corrigiu_partner = corrigir_partner_id(connection, comp['odoo_statement_line_id'], comp['odoo_partner_id'])

    # PASSO 3: Atualizar rótulo (payment_ref + name - pode recriar move lines)
    rotulo = formatar_rotulo_pagamento(
        valor=float(comp['valor_pago']),
        nome_fornecedor=comp['odoo_partner_name'] or '',
        data_pagamento=comp['data_pagamento'],
    )
    corrigiu_rotulo = corrigir_rotulo(connection, comp['odoo_statement_line_id'], comp['odoo_move_id'], rotulo)

    # PASSO 4: Trocar account_id (POR ÚLTIMO - após todas as recriações de move lines)
    corrigiu_conta = corrigir_account_id(connection, comp['odoo_move_id'])

    # PASSO 5: action_post + Reconciliar novamente
    reconciliar_novamente(connection, info_recon)

    # Verificar estado DEPOIS
    estado_depois = verificar_estado_completo(connection, comp['odoo_statement_line_id'], comp['odoo_move_id'])

    logger.info(f"  RESULTADO: {'✅ CORRIGIDO' if estado_depois.get('todos_ok') else '⚠️ PARCIAL'}")

    return {
        'sucesso': True,
        'lancamento_id': lancamento_id,
        'corrigiu_conta': corrigiu_conta,
        'corrigiu_partner': corrigiu_partner,
        'corrigiu_rotulo': corrigiu_rotulo,
        'estado_depois': estado_depois,
    }


# =========================================================================
# CORREÇÃO TIPO 2: EXTRATOS DE RECEBIMENTO
# =========================================================================

def _buscar_partner_do_titulo_odoo(connection, titulo_nf: str) -> tuple:
    """
    Busca partner_id e partner_name do título no Odoo via NF.

    A NF do título fica no campo 'ref' do account.move, no formato:
    "NF-e: 141401 Série: 1 - VND/2025/03333 - Parcela: 1 - ..."

    Returns:
        Tuple (partner_id, partner_name) ou (None, None)
    """
    # Busca 1: Por ref do account.move (formato "NF-e: XXXXX")
    moves = connection.search_read(
        'account.move',
        [
            ['ref', 'ilike', titulo_nf],
            ['move_type', 'in', ['out_invoice', 'in_invoice', 'entry']],
        ],
        fields=['partner_id'],
        limit=5
    )

    if moves:
        partner = moves[0].get('partner_id')
        if isinstance(partner, (list, tuple)) and partner:
            return partner[0], partner[1]
        return partner, ''

    # Busca 2: Fallback por move_line (caso raro)
    titulos = connection.search_read(
        'account.move.line',
        [
            ['move_id.ref', 'ilike', titulo_nf],
            ['account_id.account_type', 'in', ['asset_receivable', 'liability_payable']],
        ],
        fields=['partner_id'],
        limit=5
    )

    if not titulos:
        return None, None

    partner = titulos[0].get('partner_id')
    if isinstance(partner, (list, tuple)):
        return partner[0], partner[1]
    return partner, ''


def verificar_extrato_item(connection, item_id: int):
    """Verifica estado de 1 extrato_item no Odoo."""
    item = buscar_extrato_por_id(item_id)
    if not item:
        logger.error(f"ExtratoItem {item_id} não encontrado no JSON")
        return None

    logger.info("=" * 70)
    logger.info(f"VERIFICANDO EXTRATO_ITEM - ID: {item_id}")
    logger.info(f"  Pagador: {item.get('nome_pagador')}")
    logger.info(f"  Valor: R$ {item['valor']:.2f}")
    logger.info(f"  Statement Line ID: {item['statement_line_id']}")
    logger.info(f"  Move ID (extrato): {item['move_id']}")
    logger.info(f"  Título NF: {item.get('titulo_nf')}")
    logger.info(f"  Payment Ref: {(item.get('payment_ref') or '')[:80]}")
    logger.info("-" * 70)

    estado = verificar_estado_completo(connection, item['statement_line_id'], item['move_id'])

    if estado.get('erro'):
        logger.error(f"  ❌ {estado['erro']}")
        return None

    logger.info(f"  partner_id: {'✅ OK' if estado['partner_ok'] else '❌ FALTA'} → {estado['partner_id']}")
    logger.info(f"  payment_ref: {'✅ OK' if estado['payment_ref_ok'] else '❌ FALTA'} → {estado['payment_ref']}")
    logger.info(f"  account_id: {'✅ OK' if estado['account_ok'] else '❌ INCORRETO (TRANSITÓRIA)'}")
    logger.info(f"  is_reconciled: {estado['is_reconciled']}")
    logger.info(f"  TODOS OK: {'✅ SIM' if estado['todos_ok'] else '❌ NÃO - PRECISA CORREÇÃO'}")

    for line in estado['move_lines']:
        account = line.get('account_id')
        account_str = f"{account[0]} ({account[1]})" if isinstance(account, (list, tuple)) else str(account)
        partner = line.get('partner_id')
        partner_str = f"{partner[0]} ({partner[1]})" if isinstance(partner, (list, tuple)) else str(partner)
        logger.info(
            f"    move_line {line['id']}: "
            f"D={line.get('debit', 0):.2f} C={line.get('credit', 0):.2f} "
            f"conta={account_str} partner={partner_str} name='{line.get('name', '')[:50]}'"
        )

    return estado


def corrigir_extrato_item(connection, item_id: int) -> dict:
    """
    Corrige os 3 campos de 1 extrato_item no Odoo.

    Fluxo:
    1. Desconciliar move do extrato
    2. Trocar account_id (TRANSITÓRIA → PENDENTES)
    3. Atualizar partner_id na statement_line
    4. Atualizar rótulo (payment_ref + name)
    5. Reconciliar novamente
    """
    item = buscar_extrato_por_id(item_id)
    if not item:
        return {'erro': f'ExtratoItem {item_id} não encontrado no JSON'}

    logger.info("=" * 70)
    logger.info(f"CORRIGINDO EXTRATO_ITEM - ID: {item_id}")
    logger.info(f"  Pagador: {item.get('nome_pagador')} | Valor: R$ {item['valor']:.2f}")

    # Verificar estado ANTES
    estado_antes = verificar_estado_completo(connection, item['statement_line_id'], item['move_id'])
    if estado_antes.get('todos_ok'):
        logger.info("  ✅ Já está correto - pulando")
        return {'sucesso': True, 'ja_correto': True}

    # Obter partner_id do título no Odoo
    partner_id = None
    partner_name = None

    titulo_nf = item.get('titulo_nf')
    if titulo_nf:
        partner_id, partner_name = _buscar_partner_do_titulo_odoo(connection, titulo_nf)
        if partner_id:
            logger.info(f"  Partner do título Odoo: {partner_id} ({partner_name})")

    if not partner_id:
        logger.warning(f"  ⚠️ Não foi possível obter partner_id para item {item_id}")

    # PASSO 1: Desconciliar + button_draft (liberar para edição)
    info_recon = desconciliar_move_extrato(connection, item['move_id'])

    # PASSO 2: Atualizar partner_id (statement_line - não recria move lines)
    corrigiu_partner = False
    if partner_id:
        corrigiu_partner = corrigir_partner_id(connection, item['statement_line_id'], partner_id)

    # PASSO 3: Atualizar rótulo (payment_ref + name - pode recriar move lines)
    rotulo = item.get('payment_ref') or f"Recebimento R$ {item['valor']:.2f} - {item.get('nome_pagador') or 'N/A'}"
    corrigiu_rotulo = corrigir_rotulo(connection, item['statement_line_id'], item['move_id'], rotulo)

    # PASSO 4: Trocar account_id (POR ÚLTIMO - após todas as recriações de move lines)
    corrigiu_conta = corrigir_account_id(connection, item['move_id'])

    # PASSO 5: action_post + Reconciliar novamente
    reconciliar_novamente(connection, info_recon)

    # Verificar estado DEPOIS
    estado_depois = verificar_estado_completo(connection, item['statement_line_id'], item['move_id'])

    logger.info(f"  RESULTADO: {'✅ CORRIGIDO' if estado_depois.get('todos_ok') else '⚠️ PARCIAL'}")

    return {
        'sucesso': True,
        'item_id': item_id,
        'corrigiu_conta': corrigiu_conta,
        'corrigiu_partner': corrigiu_partner,
        'corrigiu_rotulo': corrigiu_rotulo,
        'estado_depois': estado_depois,
    }


# =========================================================================
# BATCH PROCESSING
# =========================================================================

def batch_comprovantes(connection):
    """Corrige TODOS os comprovantes."""
    comprovantes = carregar_comprovantes()

    total = len(comprovantes)
    logger.info(f"\n{'=' * 70}")
    logger.info(f"BATCH COMPROVANTES: {total} registros para corrigir")
    logger.info(f"{'=' * 70}\n")

    stats = {'total': total, 'corrigidos': 0, 'ja_corretos': 0, 'erros': 0, 'pulados': 0}

    for idx, comp in enumerate(comprovantes, 1):
        logger.info(f"\n[{idx}/{total}] Lançamento ID: {comp['id']} | NF: {comp['nf_numero']}")
        try:
            resultado = corrigir_comprovante(connection, comp['id'])
            if resultado.get('ja_correto'):
                stats['ja_corretos'] += 1
            elif resultado.get('erro'):
                stats['erros'] += 1
                logger.error(f"  Erro: {resultado['erro']}")
            elif resultado.get('sucesso'):
                stats['corrigidos'] += 1
            else:
                stats['erros'] += 1
        except Exception as e:
            stats['erros'] += 1
            logger.error(f"  ❌ Exceção: {e}")

        time.sleep(0.5)

    logger.info(f"\n{'=' * 70}")
    logger.info(f"BATCH COMPROVANTES CONCLUÍDO:")
    logger.info(f"  Total: {stats['total']}")
    logger.info(f"  Corrigidos: {stats['corrigidos']}")
    logger.info(f"  Já corretos: {stats['ja_corretos']}")
    logger.info(f"  Pulados: {stats['pulados']}")
    logger.info(f"  Erros: {stats['erros']}")
    logger.info(f"{'=' * 70}\n")

    return stats


def batch_extratos(connection, batch_size: int = 50):
    """Corrige TODOS os extrato_item."""
    items = carregar_extratos()

    total = len(items)
    logger.info(f"\n{'=' * 70}")
    logger.info(f"BATCH EXTRATOS: {total} registros para corrigir (batches de {batch_size})")
    logger.info(f"{'=' * 70}\n")

    stats = {'total': total, 'corrigidos': 0, 'ja_corretos': 0, 'erros': 0, 'pulados': 0}

    for idx, item in enumerate(items, 1):
        logger.info(f"\n[{idx}/{total}] ExtratoItem ID: {item['id']}")
        try:
            resultado = corrigir_extrato_item(connection, item['id'])
            if resultado.get('ja_correto'):
                stats['ja_corretos'] += 1
            elif resultado.get('erro'):
                stats['erros'] += 1
                logger.error(f"  Erro: {resultado['erro']}")
            elif resultado.get('sucesso'):
                stats['corrigidos'] += 1
            else:
                stats['erros'] += 1
        except Exception as e:
            stats['erros'] += 1
            logger.error(f"  ❌ Exceção: {e}")

        time.sleep(0.3)

        if idx % batch_size == 0:
            logger.info(f"\n  ⏳ Batch {idx // batch_size} concluído. Aguardando 3s...")
            time.sleep(3)

    logger.info(f"\n{'=' * 70}")
    logger.info(f"BATCH EXTRATOS CONCLUÍDO:")
    logger.info(f"  Total: {stats['total']}")
    logger.info(f"  Corrigidos: {stats['corrigidos']}")
    logger.info(f"  Já corretos: {stats['ja_corretos']}")
    logger.info(f"  Pulados: {stats['pulados']}")
    logger.info(f"  Erros: {stats['erros']}")
    logger.info(f"{'=' * 70}\n")

    return stats


def verificar_amostra(connection, n: int = 5):
    """Verifica amostra aleatória de registros para validação final."""
    logger.info(f"\n{'=' * 70}")
    logger.info(f"VERIFICAÇÃO DE AMOSTRA: {n} registros de cada tipo")
    logger.info(f"{'=' * 70}\n")

    # Amostra de comprovantes
    comprovantes = carregar_comprovantes()
    amostra_comp = random.sample(comprovantes, min(n, len(comprovantes)))

    logger.info(f"\n--- COMPROVANTES ({len(amostra_comp)} amostras) ---\n")
    for comp in amostra_comp:
        verificar_comprovante(connection, comp['id'])

    # Amostra de extratos
    extratos = carregar_extratos()
    amostra_ext = random.sample(extratos, min(n, len(extratos)))

    logger.info(f"\n--- EXTRATOS ({len(amostra_ext)} amostras) ---\n")
    for ext in amostra_ext:
        verificar_extrato_item(connection, ext['id'])


# =========================================================================
# MAIN
# =========================================================================

def main():
    parser = argparse.ArgumentParser(description='Correção de campos do extrato no Odoo')

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--verificar-comprovante', type=int, metavar='ID',
                       help='Verificar estado de 1 comprovante (sem alterar)')
    group.add_argument('--corrigir-comprovante', type=int, metavar='ID',
                       help='Corrigir 1 comprovante')
    group.add_argument('--verificar-extrato', type=int, metavar='ID',
                       help='Verificar estado de 1 extrato_item (sem alterar)')
    group.add_argument('--corrigir-extrato', type=int, metavar='ID',
                       help='Corrigir 1 extrato_item')
    group.add_argument('--batch-comprovantes', action='store_true',
                       help='Corrigir TODOS os comprovantes')
    group.add_argument('--batch-extratos', action='store_true',
                       help='Corrigir TODOS os extratos')
    group.add_argument('--verificar-amostra', action='store_true',
                       help='Verificar amostra aleatória para validação')

    parser.add_argument('--batch-size', type=int, default=50,
                       help='Tamanho do batch para extratos (default: 50)')

    args = parser.parse_args()

    # Conectar ao Odoo
    connection = get_odoo_connection()
    result = connection.test_connection()
    if not result.get('success'):
        logger.error("❌ Falha na conexão com Odoo!")
        sys.exit(1)
    logger.info("✅ Conexão com Odoo OK")

    if args.verificar_comprovante:
        verificar_comprovante(connection, args.verificar_comprovante)
    elif args.corrigir_comprovante:
        corrigir_comprovante(connection, args.corrigir_comprovante)
    elif args.verificar_extrato:
        verificar_extrato_item(connection, args.verificar_extrato)
    elif args.corrigir_extrato:
        corrigir_extrato_item(connection, args.corrigir_extrato)
    elif args.batch_comprovantes:
        batch_comprovantes(connection)
    elif args.batch_extratos:
        batch_extratos(connection, args.batch_size)
    elif args.verificar_amostra:
        verificar_amostra(connection)


if __name__ == '__main__':
    main()
