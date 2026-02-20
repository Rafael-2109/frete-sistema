"""
Correção direta no Odoo: reconcilia itens de extrato que falharam em 20/02/2026.

Conecta diretamente ao Odoo via XML-RPC (sem necessidade de banco de produção).
Dados dos itens obtidos via query ao Render Postgres.

Uso:
    source .venv/bin/activate
    python scripts/correcao_odoo_direto.py --diagnostico
    python scripts/correcao_odoo_direto.py --executar
    python scripts/correcao_odoo_direto.py --executar --item 19544
    python scripts/correcao_odoo_direto.py --executar-lancamento-12201
"""
import sys
import os
import argparse
import logging
from datetime import date  # noqa: F401

# Carregar .env
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
except ImportError:
    pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# DADOS DOS ITENS (obtidos via Render Postgres)
# ═══════════════════════════════════════════════════════════════
ITENS = [
    {"item_id": 19544, "move_id": 501482, "stmt_line_id": 34282, "valor": 41343.81, "nf": "274", "parcela": 1, "payment_id": None, "partner_id": 204585, "fornecedor": "E. A. DE JESUS", "titulo_line_id": 3095117, "titulo_move_id": 496273, "empresa": 1, "titulo_saldo": 41343.81, "data": "2026-02-18"},
    {"item_id": 19561, "move_id": 501499, "stmt_line_id": 34299, "valor": 13538.56, "nf": "1005", "parcela": 1, "payment_id": None, "partner_id": 80244, "fornecedor": "3CM SOLUTIONS", "titulo_line_id": 3095102, "titulo_move_id": 496270, "empresa": 1, "titulo_saldo": 13538.56, "data": "2026-02-18"},
    {"item_id": 19564, "move_id": 501502, "stmt_line_id": 34302, "valor": 9878.29, "nf": "972", "parcela": 1, "payment_id": None, "partner_id": 80230, "fornecedor": "DELFRAN REP COML", "titulo_line_id": 3094842, "titulo_move_id": 496215, "empresa": 1, "titulo_saldo": 9878.29, "data": "2026-02-18"},
    {"item_id": 19569, "move_id": 501507, "stmt_line_id": 34307, "valor": 8384.24, "nf": "34", "parcela": 1, "payment_id": None, "partner_id": 80241, "fornecedor": "PASSOS REP LTDA", "titulo_line_id": 3107536, "titulo_move_id": 498314, "empresa": 1, "titulo_saldo": 0.01, "data": "2026-02-18"},
    {"item_id": 19581, "move_id": 501519, "stmt_line_id": 34319, "valor": 6244.76, "nf": "1260", "parcela": 1, "payment_id": None, "partner_id": 80232, "fornecedor": "FENIX REPRESENTACOES", "titulo_line_id": 3108523, "titulo_move_id": 498575, "empresa": 1, "titulo_saldo": 6244.76, "data": "2026-02-18"},
    {"item_id": 19582, "move_id": 501520, "stmt_line_id": 34320, "valor": 5954.28, "nf": "330", "parcela": 1, "payment_id": None, "partner_id": 80252, "fornecedor": "DANIELA SOARES SANTOS", "titulo_line_id": 3107740, "titulo_move_id": 498356, "empresa": 1, "titulo_saldo": 5954.28, "data": "2026-02-18"},
    {"item_id": 19583, "move_id": 501521, "stmt_line_id": 34321, "valor": 5634.31, "nf": "939", "parcela": 1, "payment_id": None, "partner_id": 207765, "fornecedor": "GIAN E GIULIO MIRANTE", "titulo_line_id": 3096785, "titulo_move_id": 496752, "empresa": 1, "titulo_saldo": 5634.31, "data": "2026-02-18"},
    {"item_id": 19584, "move_id": 501522, "stmt_line_id": 34322, "valor": 5320.00, "nf": "1006", "parcela": 1, "payment_id": None, "partner_id": 80244, "fornecedor": "3CM SOLUTIONS", "titulo_line_id": 3095110, "titulo_move_id": 496272, "empresa": 1, "titulo_saldo": 5320.00, "data": "2026-02-18"},
    {"item_id": 19585, "move_id": 501523, "stmt_line_id": 34323, "valor": 4913.51, "nf": "1845", "parcela": 1, "payment_id": None, "partner_id": 80222, "fornecedor": "SOARES E SOARES REP", "titulo_line_id": 3107347, "titulo_move_id": 498267, "empresa": 1, "titulo_saldo": 4913.51, "data": "2026-02-18"},
    {"item_id": 19596, "move_id": 501534, "stmt_line_id": 34334, "valor": 2461.79, "nf": "1969", "parcela": 1, "payment_id": None, "partner_id": 97419, "fornecedor": "EDSON MONTE DE OLIVEIRA", "titulo_line_id": 3107525, "titulo_move_id": 498310, "empresa": 1, "titulo_saldo": 2461.79, "data": "2026-02-18"},
    {"item_id": 19601, "move_id": 501539, "stmt_line_id": 34339, "valor": 1741.47, "nf": "18", "parcela": 1, "payment_id": None, "partner_id": 80229, "fornecedor": "FORTES REPRESENTACOES", "titulo_line_id": 3101082, "titulo_move_id": 497331, "empresa": 1, "titulo_saldo": 1741.47, "data": "2026-02-18"},
    {"item_id": 19603, "move_id": 501541, "stmt_line_id": 34341, "valor": 1579.25, "nf": "314", "parcela": 1, "payment_id": None, "partner_id": 80243, "fornecedor": "MARIO EMILIO GASPAROTTI", "titulo_line_id": 3107529, "titulo_move_id": 498311, "empresa": 1, "titulo_saldo": 1579.25, "data": "2026-02-18"},
    {"item_id": 19606, "move_id": 501544, "stmt_line_id": 34344, "valor": 1372.53, "nf": "230", "parcela": 1, "payment_id": None, "partner_id": 204598, "fornecedor": "R T A CONSULTORIA", "titulo_line_id": 3113958, "titulo_move_id": 499584, "empresa": 1, "titulo_saldo": 1372.53, "data": "2026-02-18"},
    {"item_id": 19618, "move_id": 501557, "stmt_line_id": 34357, "valor": 767.20, "nf": "613", "parcela": 1, "payment_id": None, "partner_id": 80245, "fornecedor": "TEST REPRESENTACOES", "titulo_line_id": 3114737, "titulo_move_id": 499646, "empresa": 1, "titulo_saldo": 767.20, "data": "2026-02-18"},
    {"item_id": 19620, "move_id": 501559, "stmt_line_id": 34359, "valor": 688.24, "nf": "89", "parcela": 1, "payment_id": None, "partner_id": 208372, "fornecedor": "RAQUEL ALVES BELLONCI", "titulo_line_id": 3094740, "titulo_move_id": 496192, "empresa": 1, "titulo_saldo": 688.24, "data": "2026-02-18"},
    {"item_id": 19630, "move_id": 501569, "stmt_line_id": 34369, "valor": 336.84, "nf": "868", "parcela": 1, "payment_id": None, "partner_id": 97451, "fornecedor": "EXPRESSO VILA PAULISTA", "titulo_line_id": 2963617, "titulo_move_id": 471971, "empresa": 3, "titulo_saldo": 336.84, "data": "2026-02-18"},
    {"item_id": 19632, "move_id": 501571, "stmt_line_id": 34371, "valor": 235.98, "nf": "84", "parcela": 1, "payment_id": None, "partner_id": 204595, "fornecedor": "ROBIRAN TAVARES MAIA", "titulo_line_id": 3094950, "titulo_move_id": 496228, "empresa": 1, "titulo_saldo": 235.98, "data": "2026-02-18"},
    {"item_id": 19635, "move_id": 501574, "stmt_line_id": 34374, "valor": 106.76, "nf": "122", "parcela": 1, "payment_id": 36740, "partner_id": 205173, "fornecedor": "SCA REPRESENTACAO", "titulo_line_id": 3103939, "titulo_move_id": 497818, "empresa": 1, "titulo_saldo": 106.76, "data": "2026-02-18"},
]

# Lançamento 12201
LANC_12201 = {
    "id": 12201,
    "odoo_payment_id": 36705,
    "odoo_credit_line_id": 3131608,
    "odoo_move_id": 418547,       # extrato move_id (via comprovante)
    "odoo_statement_line_id": 15889,
    "odoo_partner_id": 205237,
    "valor_pago": 3660.27,
    "odoo_company_id": 4,
}

# IDs fixos Odoo
CONTA_TRANSITORIA = 22199    # 1110100003
CONTA_PENDENTES = 26868      # 1110100004
JOURNAL_GRAFENO = 883        # GRA1


def get_connection():
    """Cria conexão Odoo via XML-RPC."""
    from app.odoo.config.odoo_config import ODOO_CONFIG, validate_odoo_config
    from app.odoo.utils.connection import OdooConnection

    validate_odoo_config()
    conn = OdooConnection(ODOO_CONFIG)
    uid = conn.authenticate()
    logger.info(f"Conectado ao Odoo: {ODOO_CONFIG['url']} (uid={uid})")
    return conn


def diagnostico(conn):
    """Diagnóstico: verifica estado atual de cada título e extrato no Odoo."""
    print(f"\n{'='*80}")
    print("DIAGNOSTICO: ESTADO ATUAL DOS 18 ITENS NO ODOO")
    print(f"{'='*80}\n")

    for item in ITENS:
        print(f"--- Item {item['item_id']} | NF {item['nf']} P{item['parcela']} | "
              f"R$ {item['valor']:,.2f} | {item['fornecedor']}")

        # 1. Verificar título no Odoo
        titulo_line = conn.search_read(
            'account.move.line',
            [['id', '=', item['titulo_line_id']]],
            fields=['amount_residual', 'reconciled', 'full_reconcile_id',
                    'move_id', 'company_id'],
            limit=1,
        )
        if titulo_line:
            tl = titulo_line[0]
            residual = abs(tl.get('amount_residual', 0))
            reconciled = tl.get('reconciled', False)
            full_rec = tl.get('full_reconcile_id', False)
            company = tl.get('company_id', [None, ''])
            print(f"     Titulo: residual={residual:.2f} reconciled={reconciled} "
                  f"full_rec={full_rec} company={company}")
        else:
            print(f"     Titulo: NAO ENCONTRADO (line_id={item['titulo_line_id']})")

        # 2. Verificar extrato (statement_line) no Odoo
        stmt = conn.search_read(
            'account.bank.statement.line',
            [['id', '=', item['stmt_line_id']]],
            fields=['is_reconciled', 'partner_id', 'payment_ref', 'move_id'],
            limit=1,
        )
        if stmt:
            s = stmt[0]
            is_rec = s.get('is_reconciled', False)
            partner = s.get('partner_id', False)
            print(f"     Extrato: is_reconciled={is_rec} partner={partner}")
        else:
            print(f"     Extrato: NAO ENCONTRADO (stmt_line_id={item['stmt_line_id']})")

        # 3. Verificar move_lines do extrato
        move_lines = conn.search_read(
            'account.move.line',
            [['move_id', '=', item['move_id']]],
            fields=['id', 'account_id', 'debit', 'credit', 'reconciled', 'name'],
        )
        if move_lines:
            for ml in move_lines:
                acc = ml.get('account_id', [None, ''])
                acc_id = acc[0] if isinstance(acc, (list, tuple)) else acc
                is_transit = ' [TRANSIT]' if acc_id == CONTA_TRANSITORIA else ''
                is_pend = ' [PENDENTES]' if acc_id == CONTA_PENDENTES else ''
                print(f"     Move line {ml['id']}: D={ml['debit']:.2f} C={ml['credit']:.2f} "
                      f"acc={acc}{is_transit}{is_pend} reconciled={ml['reconciled']}")
        else:
            print(f"     Move lines: NENHUMA para move_id={item['move_id']}")

        # 4. Se tem payment, verificar
        if item['payment_id']:
            pay = conn.search_read(
                'account.payment',
                [['id', '=', item['payment_id']]],
                fields=['state', 'amount', 'move_id'],
                limit=1,
            )
            if pay:
                print(f"     Payment {item['payment_id']}: state={pay[0]['state']} "
                      f"amount={pay[0]['amount']}")

        print()

    # Lançamento 12201
    print(f"\n{'='*80}")
    print("DIAGNOSTICO: LANCAMENTO 12201")
    print(f"{'='*80}\n")

    lanc = LANC_12201
    pay = conn.search_read(
        'account.payment',
        [['id', '=', lanc['odoo_payment_id']]],
        fields=['state', 'amount', 'move_id', 'paired_internal_transfer_payment_id'],
        limit=1,
    )
    if pay:
        print(f"Payment {lanc['odoo_payment_id']}: state={pay[0]['state']} amount={pay[0]['amount']}")

    # Credit line do payment
    cl = conn.search_read(
        'account.move.line',
        [['id', '=', lanc['odoo_credit_line_id']]],
        fields=['amount_residual', 'reconciled', 'full_reconcile_id', 'account_id'],
        limit=1,
    )
    if cl:
        print(f"Credit line {lanc['odoo_credit_line_id']}: residual={cl[0]['amount_residual']} "
              f"reconciled={cl[0]['reconciled']} full_rec={cl[0]['full_reconcile_id']} "
              f"acc={cl[0]['account_id']}")

    # Statement line do extrato
    stmt = conn.search_read(
        'account.bank.statement.line',
        [['id', '=', lanc['odoo_statement_line_id']]],
        fields=['is_reconciled', 'partner_id', 'move_id'],
        limit=1,
    )
    if stmt:
        print(f"Statement line {lanc['odoo_statement_line_id']}: "
              f"is_reconciled={stmt[0]['is_reconciled']} partner={stmt[0]['partner_id']}")

    # Move lines do extrato
    move_lines = conn.search_read(
        'account.move.line',
        [['move_id', '=', lanc['odoo_move_id']]],
        fields=['id', 'account_id', 'debit', 'credit', 'reconciled'],
    )
    for ml in move_lines:
        acc = ml.get('account_id', [None, ''])
        acc_id = acc[0] if isinstance(acc, (list, tuple)) else acc
        is_transit = ' [TRANSIT]' if acc_id == CONTA_TRANSITORIA else ''
        is_pend = ' [PENDENTES]' if acc_id == CONTA_PENDENTES else ''
        print(f"Move line {ml['id']}: D={ml['debit']:.2f} C={ml['credit']:.2f} "
              f"acc={acc}{is_transit}{is_pend} reconciled={ml['reconciled']}")


def _buscar_payment_via_titulo(conn, titulo_line_id):
    """
    Busca payment existente que reconciliou com o título.

    Usa matched_credit_ids e matched_debit_ids do título para encontrar
    as partial_reconciles, depois busca o payment associado.
    """
    # Buscar os IDs de partial_reconcile diretamente do título
    titulo = conn.search_read(
        'account.move.line',
        [['id', '=', titulo_line_id]],
        fields=['matched_credit_ids', 'matched_debit_ids'],
        limit=1,
    )
    if not titulo:
        return None

    # Coletar TODOS os partial_reconcile IDs (ambos os lados)
    partial_ids = []
    for field in ['matched_credit_ids', 'matched_debit_ids']:
        ids = titulo[0].get(field, [])
        if ids:
            partial_ids.extend(ids)

    if not partial_ids:
        logger.warning(f"  Titulo {titulo_line_id}: sem partial_reconciles (matched_*_ids vazios)")
        return None

    logger.info(f"  Titulo {titulo_line_id}: {len(partial_ids)} partial_reconciles encontrados")

    # Buscar os partial_reconciles para encontrar as linhas de contrapartida
    partials = conn.search_read(
        'account.partial.reconcile',
        [['id', 'in', partial_ids]],
        fields=['debit_move_id', 'credit_move_id'],
    )

    # Para cada partial, a "outra linha" (não o título) pode ser a do payment
    for pr in partials:
        for field in ['debit_move_id', 'credit_move_id']:
            mv = pr[field]
            mv_id = mv[0] if isinstance(mv, (list, tuple)) else mv
            if mv_id == titulo_line_id:
                continue  # Pular o próprio título

            # Verificar se esta linha pertence a um payment
            info = conn.search_read(
                'account.move.line',
                [['id', '=', mv_id]],
                fields=['payment_id', 'move_id'],
                limit=1,
            )
            if info and info[0].get('payment_id'):
                pay = info[0]['payment_id']
                pay_id = pay[0] if isinstance(pay, (list, tuple)) else pay
                logger.info(f"  Payment encontrado: {pay_id} (via partial_reconcile, line {mv_id})")
                return pay_id

    logger.warning(f"  Nenhum payment encontrado nos {len(partial_ids)} partial_reconciles")
    return None


def _buscar_credit_line_payment(conn, payment_id):
    """Busca a credit_line do payment na conta PENDENTES (ou TRANSITÓRIA)."""
    pay_info = conn.search_read(
        'account.payment',
        [['id', '=', payment_id]],
        fields=['move_id'],
        limit=1,
    )
    if not pay_info:
        return None

    pay_move_id = pay_info[0]['move_id']
    pay_move_id_val = pay_move_id[0] if isinstance(pay_move_id, (list, tuple)) else pay_move_id

    # Tentar PENDENTES primeiro, depois TRANSITÓRIA
    pay_lines = conn.search_read(
        'account.move.line',
        [['move_id', '=', pay_move_id_val],
         ['account_id', 'in', [CONTA_PENDENTES, CONTA_TRANSITORIA]],
         ['credit', '>', 0],
         ['reconciled', '=', False]],
        fields=['id', 'credit', 'account_id', 'reconciled'],
    )
    if pay_lines:
        return pay_lines[0]['id']

    # Se todas reconciliadas, buscar qualquer credit line nessas contas
    pay_lines = conn.search_read(
        'account.move.line',
        [['move_id', '=', pay_move_id_val],
         ['account_id', 'in', [CONTA_PENDENTES, CONTA_TRANSITORIA]],
         ['credit', '>', 0]],
        fields=['id', 'credit', 'account_id', 'reconciled'],
    )
    if pay_lines:
        return pay_lines[0]['id']

    return None


def _preparar_extrato(conn, move_id, stmt_line_id, partner_id, rotulo):
    """
    Prepara extrato para reconciliação: partner, rótulo, conta.

    Segue padrão GOTCHAS.md (7 passos) e gotcha O12 (account_id ÚLTIMO):
    1. button_draft
    2. Write partner_id + payment_ref na statement_line (pode regenerar lines)
    3. Re-fetch + write name nas move_lines (pode regenerar lines)
    4. Re-fetch + trocar conta TRANSITÓRIA → PENDENTES (ÚLTIMO write)
    5. action_post
    """
    # 1. button_draft
    conn.execute_kw('account.move', 'button_draft', [[move_id]])
    logger.info("    1. draft OK")

    # 2. Write partner + rotulo na statement_line
    conn.execute_kw(
        'account.bank.statement.line', 'write',
        [[stmt_line_id], {'partner_id': partner_id, 'payment_ref': rotulo}]
    )
    logger.info("    2. partner + rotulo OK")

    # 3. Re-fetch + write name
    move_lines = conn.search_read(
        'account.move.line',
        [['move_id', '=', move_id]],
        fields=['id', 'account_id', 'debit', 'credit'],
    )
    logger.info(f"    3. {len(move_lines)} move_lines re-fetched")
    for ml in move_lines:
        conn.execute_kw(
            'account.move.line', 'write',
            [[ml['id']], {'name': rotulo}]
        )

    # 4. Re-fetch + trocar conta (ÚLTIMO write per O12)
    move_lines = conn.search_read(
        'account.move.line',
        [['move_id', '=', move_id]],
        fields=['id', 'account_id', 'debit', 'credit'],
    )
    trocou = False
    for ml in move_lines:
        acc = ml.get('account_id', [None, ''])
        acc_id = acc[0] if isinstance(acc, (list, tuple)) else acc
        if acc_id == CONTA_TRANSITORIA and ml['debit'] > 0:
            conn.execute_kw(
                'account.move.line', 'write',
                [[ml['id']], {'account_id': CONTA_PENDENTES}]
            )
            logger.info(f"    4. Conta trocada: {ml['id']} TRANSIT -> PENDENTES")
            trocou = True
    if not trocou:
        logger.info("    4. Nenhuma conta TRANSITÓRIA para trocar (já em PENDENTES?)")

    # 5. action_post
    conn.execute_kw('account.move', 'action_post', [[move_id]])
    logger.info("    5. action_post OK")


def _buscar_debit_line_extrato(conn, move_id):
    """Busca debit_line FRESCA do extrato (após action_post)."""
    debit_lines = conn.search_read(
        'account.move.line',
        [['move_id', '=', move_id],
         ['account_id', 'in', [CONTA_TRANSITORIA, CONTA_PENDENTES]],
         ['debit', '>', 0]],
        fields=['id', 'debit', 'account_id', 'reconciled'],
    )
    if debit_lines:
        return debit_lines[0]['id']
    return None


def _reconciliar(conn, credit_line_id, debit_line_id):
    """Reconcilia credit_line (payment) com debit_line (extrato). Trata gotcha O6."""
    logger.info(f"  Reconciliando: credit={credit_line_id} <-> debit={debit_line_id}")
    try:
        conn.execute_kw(
            'account.move.line', 'reconcile', [[credit_line_id, debit_line_id]]
        )
        logger.info("  RECONCILIADO com sucesso!")
        return True
    except Exception as e:
        if 'cannot marshal None' in str(e):
            logger.info("  'cannot marshal None' = SUCESSO (gotcha O6)")
            return True
        else:
            logger.error(f"  ERRO na reconciliacao: {e}")
            return False


def executar_reconciliacao_item(conn, item):
    """
    Executa a reconciliação do extrato bancário de um item.

    Diagnóstico mostrou 3 cenários:
    A) 16 itens: título JÁ reconciliado (payment existe) → encontrar payment → preparar extrato → reconciliar
    B) item 19561: título NÃO reconciliado → criar payment → preparar extrato → reconciliar
    C) item 19569: título saldo=0.01 (quase quitado) → criar payment → preparar extrato → reconciliar
    """
    item_id = item['item_id']
    logger.info(f"\n{'='*60}")
    logger.info(f"ITEM {item_id} | NF {item['nf']} P{item['parcela']} | R$ {item['valor']:,.2f}")
    logger.info(f"{'='*60}")

    # 1. Verificar extrato — se já reconciliado, nada a fazer
    stmt = conn.search_read(
        'account.bank.statement.line',
        [['id', '=', item['stmt_line_id']]],
        fields=['is_reconciled'],
        limit=1,
    )
    if not stmt:
        logger.error(f"  Statement line {item['stmt_line_id']} nao encontrada!")
        return False
    if stmt[0]['is_reconciled']:
        logger.info("  Extrato ja reconciliado! Nada a fazer.")
        return True

    # 2. Verificar título no Odoo
    titulo_line = conn.search_read(
        'account.move.line',
        [['id', '=', item['titulo_line_id']]],
        fields=['amount_residual', 'reconciled', 'company_id'],
        limit=1,
    )
    if not titulo_line:
        logger.error(f"  Titulo line {item['titulo_line_id']} nao encontrado!")
        return False

    tl = titulo_line[0]
    residual = abs(tl['amount_residual'])
    logger.info(f"  Titulo: residual={residual:.2f} reconciled={tl['reconciled']}")

    # 3. Obter credit_line_id do payment
    credit_line_id = None
    payment_id = item['payment_id']

    if tl['reconciled']:
        # CENÁRIO A: título já reconciliado → payment existe, buscar via partial_reconcile
        logger.info("  Cenario A: titulo reconciliado, buscando payment existente...")
        payment_id = _buscar_payment_via_titulo(conn, item['titulo_line_id'])
        if payment_id:
            logger.info(f"  Payment encontrado: {payment_id}")
            credit_line_id = _buscar_credit_line_payment(conn, payment_id)
            if credit_line_id:
                logger.info(f"  Credit line: {credit_line_id}")
            else:
                logger.error("  Credit line do payment NAO encontrada!")
                return False
        else:
            logger.error("  Payment NAO encontrado via partial_reconcile!")
            return False

    elif payment_id:
        # Payment fornecido nos dados (item 19635)
        logger.info(f"  Payment fornecido: {payment_id}")
        credit_line_id = _buscar_credit_line_payment(conn, payment_id)
        if not credit_line_id:
            logger.error("  Credit line do payment NAO encontrada!")
            return False
        logger.info(f"  Credit line: {credit_line_id}")

    else:
        # CENÁRIO B/C: título NÃO reconciliado, precisa criar payment
        logger.info(f"  Cenario B/C: titulo nao reconciliado, criando payment...")

        wizard_context = {
            'active_model': 'account.move.line',
            'active_ids': [item['titulo_line_id']],
        }

        # Journal: Grafeno (883) para empresa 1 (FB).
        # Para outra empresa, NAO passar journal_id — wizard usa default.
        wizard_vals = {'payment_date': item['data']}
        if item['empresa'] == 1:
            wizard_vals['journal_id'] = JOURNAL_GRAFENO
        else:
            logger.info(f"  Empresa {item['empresa']} != 1: wizard usara journal default")

        wizard_id = conn.execute_kw(
            'account.payment.register', 'create',
            [wizard_vals],
            {'context': wizard_context},
        )
        logger.info(f"  Wizard criado: {wizard_id}")

        try:
            conn.execute_kw(
                'account.payment.register', 'action_create_payments',
                [[wizard_id]],
                {'context': wizard_context},
            )
            logger.info("  Payment criado e postado!")
        except Exception as e:
            if 'cannot marshal None' in str(e):
                logger.info("  'cannot marshal None' = SUCESSO (gotcha O6)")
            else:
                raise

        # Buscar payment via partial_reconcile (wizard reconcilia automaticamente)
        payment_id = _buscar_payment_via_titulo(conn, item['titulo_line_id'])
        if payment_id:
            logger.info(f"  Payment criado: {payment_id}")
            credit_line_id = _buscar_credit_line_payment(conn, payment_id)
        else:
            # Fallback: buscar por partner+amount
            payments = conn.search_read(
                'account.payment',
                [['partner_id', '=', item['partner_id']],
                 ['state', '=', 'posted'],
                 ['journal_id', '=', JOURNAL_GRAFENO]],
                fields=['id', 'amount'],
                order='id desc',
                limit=5,
            )
            for p in payments:
                if abs(p['amount'] - item['valor']) < 0.02 or abs(p['amount'] - residual) < 0.02:
                    payment_id = p['id']
                    logger.info(f"  Payment encontrado por valor: {payment_id} (R${p['amount']:.2f})")
                    credit_line_id = _buscar_credit_line_payment(conn, payment_id)
                    break

        if not credit_line_id:
            logger.error("  Nao encontrou credit_line apos criar payment!")
            return False
        logger.info(f"  Credit line: {credit_line_id}")

    # 4. Preparar extrato (partner, rótulo, conta TRANSITÓRIA → PENDENTES)
    rotulo = f"PIX R$ {item['valor']:,.2f} - {item['fornecedor']} ({item['data']})"
    logger.info(f"  Preparando extrato...")
    _preparar_extrato(conn, item['move_id'], item['stmt_line_id'], item['partner_id'], rotulo)

    # 5. Buscar debit_line FRESCA do extrato
    debit_line_id = _buscar_debit_line_extrato(conn, item['move_id'])
    if not debit_line_id:
        logger.error("  Debit line do extrato nao encontrada!")
        return False
    logger.info(f"  Debit line extrato (fresca): {debit_line_id}")

    # 6. Reconciliar credit_line (payment) com debit_line (extrato)
    return _reconciliar(conn, credit_line_id, debit_line_id)


def executar_lancamento_12201(conn):
    """
    Completa a reconciliação extrato do lançamento 12201.

    Diagnóstico mostrou:
    - credit_line 3131608: residual=-3660.27, reconciled=False, acc=PENDENTES (26868)
    - debit_line 2715259: D=3660.27, reconciled=False, acc=PENDENTES (26868)
    - statement_line 15889: is_reconciled=True (partner/rotulo já setados)
    - Ambas as lines já estão em PENDENTES → NÃO precisa do ciclo 7 passos
    - Basta reconciliar credit ↔ debit diretamente
    """
    lanc = LANC_12201
    logger.info(f"\n{'='*60}")
    logger.info(f"LANCAMENTO 12201 (payment {lanc['odoo_payment_id']})")
    logger.info(f"{'='*60}")

    # 1. Verificar credit_line do payment (indicador real de reconciliação)
    cl = conn.search_read(
        'account.move.line',
        [['id', '=', lanc['odoo_credit_line_id']]],
        fields=['amount_residual', 'reconciled', 'account_id'],
        limit=1,
    )
    if not cl:
        logger.error(f"  Credit line {lanc['odoo_credit_line_id']} nao encontrada!")
        return False

    cl_data = cl[0]
    acc = cl_data.get('account_id', [None, ''])
    acc_id = acc[0] if isinstance(acc, (list, tuple)) else acc
    logger.info(f"  Credit line {lanc['odoo_credit_line_id']}: "
                f"residual={cl_data['amount_residual']} reconciled={cl_data['reconciled']} acc_id={acc_id}")

    if cl_data['reconciled']:
        logger.info("  Credit line ja reconciliada! Nada a fazer.")
        return True

    # 2. Buscar debit_line do extrato (em PENDENTES)
    debit_lines = conn.search_read(
        'account.move.line',
        [['move_id', '=', lanc['odoo_move_id']],
         ['account_id', 'in', [CONTA_PENDENTES, CONTA_TRANSITORIA]],
         ['debit', '>', 0]],
        fields=['id', 'debit', 'account_id', 'reconciled'],
    )
    if not debit_lines:
        logger.error("  Debit line do extrato nao encontrada!")
        return False

    debit = debit_lines[0]
    debit_acc = debit.get('account_id', [None, ''])
    debit_acc_id = debit_acc[0] if isinstance(debit_acc, (list, tuple)) else debit_acc
    logger.info(f"  Debit line {debit['id']}: D={debit['debit']:.2f} "
                f"acc_id={debit_acc_id} reconciled={debit['reconciled']}")

    if debit['reconciled']:
        logger.info("  Debit line ja reconciliada! Nada a fazer.")
        return True

    # 3. Se debit_line ainda em TRANSITÓRIA, precisa do ciclo completo
    if debit_acc_id == CONTA_TRANSITORIA:
        logger.info("  Debit line em TRANSITORIA — executando ciclo completo...")
        partner_name = ''
        partner_info = conn.search_read(
            'res.partner',
            [['id', '=', lanc['odoo_partner_id']]],
            fields=['name'],
            limit=1,
        )
        if partner_info:
            partner_name = partner_info[0]['name']

        rotulo = f"PGTO R$ {lanc['valor_pago']:,.2f} - {partner_name}"
        _preparar_extrato(conn, lanc['odoo_move_id'], lanc['odoo_statement_line_id'],
                          lanc['odoo_partner_id'], rotulo)

        # Re-buscar debit_line fresca
        debit_line_id = _buscar_debit_line_extrato(conn, lanc['odoo_move_id'])
        if not debit_line_id:
            logger.error("  Debit line nao encontrada apos preparar extrato!")
            return False
        logger.info(f"  Debit line fresca: {debit_line_id}")
    else:
        # Já em PENDENTES — reconciliar diretamente
        debit_line_id = debit['id']
        logger.info(f"  Ambas em PENDENTES — reconciliacao direta")

    # 4. Reconciliar
    return _reconciliar(conn, lanc['odoo_credit_line_id'], debit_line_id)


def main():
    parser = argparse.ArgumentParser(description='Correcao direta no Odoo')
    parser.add_argument('--diagnostico', action='store_true', help='Apenas diagnosticar estado no Odoo')
    parser.add_argument('--executar', action='store_true', help='Executar reconciliacao dos 18 itens')
    parser.add_argument('--item', type=int, help='Executar apenas um item especifico')
    parser.add_argument('--executar-lancamento-12201', action='store_true', help='Executar correcao do lanc 12201')
    args = parser.parse_args()

    if not any([args.diagnostico, args.executar, args.executar_lancamento_12201]):
        parser.print_help()
        return

    # Inicializar app (para carregar config e conexao)
    from app import create_app
    app = create_app()

    with app.app_context():
        conn = get_connection()

        if args.diagnostico:
            diagnostico(conn)

        if args.executar:
            itens_alvo = ITENS
            if args.item:
                itens_alvo = [i for i in ITENS if i['item_id'] == args.item]
                if not itens_alvo:
                    print(f"Item {args.item} nao encontrado!")
                    return

            sucesso = 0
            erros = 0
            for item in itens_alvo:
                try:
                    ok = executar_reconciliacao_item(conn, item)
                    if ok:
                        sucesso += 1
                    else:
                        erros += 1
                except Exception as e:
                    logger.error(f"EXCEPTION item {item['item_id']}: {e}", exc_info=True)
                    erros += 1

            print(f"\nRESULTADO: {sucesso} sucesso, {erros} erros de {len(itens_alvo)}")

        if args.executar_lancamento_12201:
            try:
                ok = executar_lancamento_12201(conn)
                print(f"\nLANCAMENTO 12201: {'SUCESSO' if ok else 'FALHOU'}")
            except Exception as e:
                logger.error(f"EXCEPTION lancamento 12201: {e}", exc_info=True)


if __name__ == '__main__':
    main()
