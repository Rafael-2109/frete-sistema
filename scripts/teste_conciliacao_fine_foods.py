#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste: Conciliação Fine Foods NF 2113 P5 com fix draft→write→post

Caso: contas_a_pagar.id=918, odoo_line_id=2670685, NF 2113 P5, R$ 10.766,67
Payment: PSIC/2026/00503 (ID 35539) — já criado, título reconciliado
Statement line 31117: is_reconciled=False, partner_id=False

Etapas:
1. Atualizar statement line 31117 (partner_id + payment_ref) via draft→write→post
2. Trocar conta transitória (22199) → pendentes (26868) no move do extrato
3. Reconciliar payment ↔ extrato
4. Verificar resultado final
"""

import sys
import os
import json
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Constantes do caso
STATEMENT_LINE_ID = 31117
STATEMENT_MOVE_ID = 465926  # SIC/2026/00062
PAYMENT_ID = 35539  # PSIC/2026/00503
PARTNER_ID_FINE_FOODS = 205491
CONTA_TRANSITORIA = 22199
CONTA_PENDENTES = 26868
VALOR = 10766.67
PAYMENT_REF = "NF 2113 P5 - Fine Foods Industria"


def main():
    from app import create_app
    app = create_app()

    with app.app_context():
        from app.odoo.utils.connection import get_odoo_connection
        conn = get_odoo_connection()
        if not conn.authenticate():
            print(json.dumps({"sucesso": False, "erro": "Falha na autenticação Odoo"}))
            return

        print("=" * 70)
        print("TESTE: Conciliação Fine Foods NF 2113 P5")
        print("=" * 70)

        # =====================================================================
        # VERIFICAÇÃO INICIAL - Estado atual
        # =====================================================================
        print("\n--- VERIFICAÇÃO INICIAL ---")

        # Statement line 31117
        stmt = conn.search_read(
            'account.bank.statement.line',
            [['id', '=', STATEMENT_LINE_ID]],
            fields=['id', 'date', 'amount', 'payment_ref', 'partner_id',
                    'is_reconciled', 'move_id'],
            limit=1
        )
        if not stmt:
            print(json.dumps({"sucesso": False, "erro": f"Statement line {STATEMENT_LINE_ID} não encontrada"}))
            return

        st = stmt[0]
        print(f"  Statement line {STATEMENT_LINE_ID}:")
        print(f"    date: {st['date']}")
        print(f"    amount: {st['amount']}")
        print(f"    payment_ref: {st['payment_ref']}")
        print(f"    partner_id: {st['partner_id']}")
        print(f"    is_reconciled: {st['is_reconciled']}")
        move_id_raw = st['move_id']
        move_id = move_id_raw[0] if isinstance(move_id_raw, (list, tuple)) else move_id_raw
        print(f"    move_id: {move_id}")

        if st['is_reconciled']:
            print("\n  ⚠ Statement line JÁ está reconciliada. Nada a fazer.")
            print(json.dumps({"sucesso": True, "mensagem": "Já reconciliada"}))
            return

        # Payment PSIC/2026/00503
        payment = conn.search_read(
            'account.payment',
            [['id', '=', PAYMENT_ID]],
            fields=['id', 'name', 'state', 'amount', 'partner_id',
                    'reconciled_statement_line_ids'],
            limit=1
        )
        if not payment:
            print(json.dumps({"sucesso": False, "erro": f"Payment {PAYMENT_ID} não encontrado"}))
            return

        pay = payment[0]
        print(f"\n  Payment {PAYMENT_ID}:")
        print(f"    name: {pay['name']}")
        print(f"    state: {pay['state']}")
        print(f"    amount: {pay['amount']}")
        print(f"    partner_id: {pay['partner_id']}")
        print(f"    reconciled_statement_line_ids: {pay['reconciled_statement_line_ids']}")

        # =====================================================================
        # ETAPA 1: Atualizar statement line 31117 (partner_id + payment_ref)
        # =====================================================================
        print("\n--- ETAPA 1: Atualizar statement line (draft→write→post) ---")

        try:
            # 1a. button_draft no move
            print(f"  1a. button_draft no move {move_id}...")
            conn.execute_kw('account.move', 'button_draft', [[move_id]])
            print("      OK")

            # 1b. write na statement line
            vals_stmt = {
                'partner_id': PARTNER_ID_FINE_FOODS,
                'payment_ref': PAYMENT_REF,
            }
            print(f"  1b. write na statement line {STATEMENT_LINE_ID}: {vals_stmt}...")
            conn.execute_kw(
                'account.bank.statement.line', 'write',
                [[STATEMENT_LINE_ID], vals_stmt]
            )
            print("      OK")

            # 1c. action_post no move
            print(f"  1c. action_post no move {move_id}...")
            conn.execute_kw('account.move', 'action_post', [[move_id]])
            print("      OK")

        except Exception as e:
            print(f"  ERRO na Etapa 1: {e}")
            # Tentar repostar o move se ficou em draft
            try:
                conn.execute_kw('account.move', 'action_post', [[move_id]])
                print("  (move repostado após erro)")
            except Exception:
                pass
            print(json.dumps({"sucesso": False, "erro": f"Etapa 1 falhou: {e}"}))
            return

        # Verificar se partner_id foi atualizado
        stmt_after = conn.search_read(
            'account.bank.statement.line',
            [['id', '=', STATEMENT_LINE_ID]],
            fields=['partner_id', 'payment_ref'],
            limit=1
        )
        if stmt_after:
            print(f"  Verificação: partner_id={stmt_after[0]['partner_id']}, payment_ref={stmt_after[0]['payment_ref']}")

        # =====================================================================
        # ETAPA 2: Trocar conta transitória → pendentes no move do extrato
        # =====================================================================
        print("\n--- ETAPA 2: Trocar conta transitória → pendentes ---")

        # 2a. Buscar move lines do move 465926
        move_lines = conn.search_read(
            'account.move.line',
            [['move_id', '=', move_id]],
            fields=['id', 'account_id', 'debit', 'credit', 'name', 'reconciled',
                    'full_reconcile_id', 'partner_id'],
        )
        print(f"  Move lines do move {move_id}:")
        line_transitoria = None
        for ml in move_lines:
            acc_id = ml['account_id'][0] if isinstance(ml['account_id'], (list, tuple)) else ml['account_id']
            acc_name = ml['account_id'][1] if isinstance(ml['account_id'], (list, tuple)) else ''
            print(f"    id={ml['id']}: account={acc_id} ({acc_name}), "
                  f"debit={ml['debit']}, credit={ml['credit']}, "
                  f"reconciled={ml['reconciled']}, full_reconcile={ml['full_reconcile_id']}")
            if acc_id == CONTA_TRANSITORIA:
                line_transitoria = ml
                print(f"    → ENCONTRADA linha na conta transitória: id={ml['id']}")

        if not line_transitoria:
            # Verificar se já está na conta pendentes
            for ml in move_lines:
                acc_id = ml['account_id'][0] if isinstance(ml['account_id'], (list, tuple)) else ml['account_id']
                if acc_id == CONTA_PENDENTES:
                    print(f"  ⚠ Linha já está na conta PENDENTES (id={ml['id']}). Pulando etapa 2.")
                    line_transitoria = ml  # usar para etapa 3
                    break

            if not line_transitoria:
                print(f"  ERRO: Nenhuma linha na conta transitória ({CONTA_TRANSITORIA}) nem pendentes ({CONTA_PENDENTES})")
                # Listar todas as contas para debug
                for ml in move_lines:
                    acc_id = ml['account_id'][0] if isinstance(ml['account_id'], (list, tuple)) else ml['account_id']
                    print(f"    Debug: id={ml['id']} account={acc_id}")
                print(json.dumps({"sucesso": False, "erro": "Linha transitória/pendentes não encontrada"}))
                return
        else:
            # Trocar conta
            line_id = line_transitoria['id']
            try:
                print(f"  2a. button_draft no move {move_id}...")
                conn.execute_kw('account.move', 'button_draft', [[move_id]])
                print("      OK")

                print(f"  2b. write account_id={CONTA_PENDENTES} na line {line_id}...")
                conn.execute_kw(
                    'account.move.line', 'write',
                    [[line_id], {'account_id': CONTA_PENDENTES}]
                )
                print("      OK")

                print(f"  2c. action_post no move {move_id}...")
                conn.execute_kw('account.move', 'action_post', [[move_id]])
                print("      OK")

            except Exception as e:
                print(f"  ERRO na Etapa 2: {e}")
                try:
                    conn.execute_kw('account.move', 'action_post', [[move_id]])
                    print("  (move repostado após erro)")
                except Exception:
                    pass
                print(json.dumps({"sucesso": False, "erro": f"Etapa 2 falhou: {e}"}))
                return

        # =====================================================================
        # ETAPA 3: Reconciliar payment ↔ extrato
        # =====================================================================
        print("\n--- ETAPA 3: Reconciliar payment ↔ extrato ---")

        # 3a. Buscar credit line do payment na conta PENDENTES
        print(f"  3a. Buscando credit line do payment {PAYMENT_ID} na conta pendentes ({CONTA_PENDENTES})...")
        payment_move = conn.search_read(
            'account.payment',
            [['id', '=', PAYMENT_ID]],
            fields=['move_id'],
            limit=1
        )
        if not payment_move:
            print(json.dumps({"sucesso": False, "erro": "Payment move não encontrado"}))
            return

        pay_move_id_raw = payment_move[0]['move_id']
        pay_move_id = pay_move_id_raw[0] if isinstance(pay_move_id_raw, (list, tuple)) else pay_move_id_raw
        print(f"     Payment move_id: {pay_move_id}")

        pay_move_lines = conn.search_read(
            'account.move.line',
            [
                ['move_id', '=', pay_move_id],
                ['account_id', '=', CONTA_PENDENTES],
                ['reconciled', '=', False],
            ],
            fields=['id', 'account_id', 'debit', 'credit', 'amount_residual',
                    'reconciled', 'partner_id'],
        )
        print(f"     Payment move lines na conta pendentes (não reconciliadas):")
        for ml in pay_move_lines:
            print(f"       id={ml['id']}: debit={ml['debit']}, credit={ml['credit']}, "
                  f"residual={ml['amount_residual']}, reconciled={ml['reconciled']}")

        if not pay_move_lines:
            print("  ⚠ Nenhuma linha não-reconciliada do payment na conta pendentes.")
            print("  Verificando TODAS as linhas do payment move...")
            all_pay_lines = conn.search_read(
                'account.move.line',
                [['move_id', '=', pay_move_id]],
                fields=['id', 'account_id', 'debit', 'credit', 'amount_residual',
                        'reconciled', 'partner_id'],
            )
            for ml in all_pay_lines:
                acc = ml['account_id']
                acc_id = acc[0] if isinstance(acc, (list, tuple)) else acc
                acc_name = acc[1] if isinstance(acc, (list, tuple)) else ''
                print(f"    id={ml['id']}: account={acc_id} ({acc_name}), "
                      f"debit={ml['debit']}, credit={ml['credit']}, "
                      f"residual={ml['amount_residual']}, reconciled={ml['reconciled']}")

            # Tentar buscar na conta pendentes COM reconciled
            pay_move_lines_all = conn.search_read(
                'account.move.line',
                [
                    ['move_id', '=', pay_move_id],
                    ['account_id', '=', CONTA_PENDENTES],
                ],
                fields=['id', 'debit', 'credit', 'amount_residual', 'reconciled'],
            )
            if pay_move_lines_all:
                print(f"\n  Linhas do payment na conta pendentes (incluindo reconciliadas):")
                for ml in pay_move_lines_all:
                    print(f"    id={ml['id']}: debit={ml['debit']}, credit={ml['credit']}, "
                          f"residual={ml['amount_residual']}, reconciled={ml['reconciled']}")

        # 3b. Buscar debit line do statement na conta PENDENTES
        print(f"\n  3b. Buscando debit line do statement {move_id} na conta pendentes ({CONTA_PENDENTES})...")
        stmt_move_lines = conn.search_read(
            'account.move.line',
            [
                ['move_id', '=', move_id],
                ['account_id', '=', CONTA_PENDENTES],
                ['reconciled', '=', False],
            ],
            fields=['id', 'account_id', 'debit', 'credit', 'amount_residual',
                    'reconciled', 'partner_id'],
        )
        print(f"     Statement move lines na conta pendentes (não reconciliadas):")
        for ml in stmt_move_lines:
            print(f"       id={ml['id']}: debit={ml['debit']}, credit={ml['credit']}, "
                  f"residual={ml['amount_residual']}, reconciled={ml['reconciled']}")

        if not stmt_move_lines:
            print("  ⚠ Nenhuma linha não-reconciliada do statement na conta pendentes.")
            # Re-ler move lines após etapa 2
            all_stmt_lines = conn.search_read(
                'account.move.line',
                [['move_id', '=', move_id]],
                fields=['id', 'account_id', 'debit', 'credit', 'amount_residual',
                        'reconciled', 'partner_id'],
            )
            for ml in all_stmt_lines:
                acc = ml['account_id']
                acc_id = acc[0] if isinstance(acc, (list, tuple)) else acc
                acc_name = acc[1] if isinstance(acc, (list, tuple)) else ''
                print(f"    id={ml['id']}: account={acc_id} ({acc_name}), "
                      f"debit={ml['debit']}, credit={ml['credit']}, "
                      f"residual={ml['amount_residual']}, reconciled={ml['reconciled']}")

        # 3c. Reconciliar se encontramos as duas linhas
        if pay_move_lines and stmt_move_lines:
            credit_line_id = pay_move_lines[0]['id']
            debit_line_id = stmt_move_lines[0]['id']
            line_ids = [credit_line_id, debit_line_id]

            print(f"\n  3c. Reconciliando lines {line_ids}...")
            try:
                result = conn.execute_kw(
                    'account.move.line', 'reconcile', [line_ids]
                )
                print(f"      Resultado: {result}")
                print("      OK - Reconciliação executada!")
            except Exception as e:
                print(f"      ERRO na reconciliação: {e}")
                print(json.dumps({"sucesso": False, "erro": f"Reconciliação falhou: {e}"}))
                return
        else:
            print("\n  ⚠ Não foi possível reconciliar: linhas não encontradas.")
            print("  Verifique manualmente no Odoo os IDs acima.")

        # =====================================================================
        # ETAPA 4: Verificação final
        # =====================================================================
        print("\n--- ETAPA 4: Verificação final ---")

        # Statement line
        stmt_final = conn.search_read(
            'account.bank.statement.line',
            [['id', '=', STATEMENT_LINE_ID]],
            fields=['id', 'partner_id', 'payment_ref', 'is_reconciled'],
            limit=1
        )
        if stmt_final:
            sf = stmt_final[0]
            print(f"  Statement line {STATEMENT_LINE_ID}:")
            print(f"    partner_id: {sf['partner_id']}")
            print(f"    payment_ref: {sf['payment_ref']}")
            print(f"    is_reconciled: {sf['is_reconciled']}")

        # Payment
        pay_final = conn.search_read(
            'account.payment',
            [['id', '=', PAYMENT_ID]],
            fields=['id', 'name', 'reconciled_statement_line_ids'],
            limit=1
        )
        if pay_final:
            pf = pay_final[0]
            print(f"\n  Payment {PAYMENT_ID} ({pf['name']}):")
            print(f"    reconciled_statement_line_ids: {pf['reconciled_statement_line_ids']}")

        # Resultado
        sucesso = (
            stmt_final and stmt_final[0].get('is_reconciled', False) and
            pay_final and STATEMENT_LINE_ID in pay_final[0].get('reconciled_statement_line_ids', [])
        )

        print("\n" + "=" * 70)
        if sucesso:
            print("✓ TESTE PASSOU: Conciliação Fine Foods NF 2113 P5 completa!")
        else:
            print("⚠ TESTE PARCIAL: Verificar resultados acima manualmente.")
        print("=" * 70)

        resultado = {
            "sucesso": sucesso,
            "statement_line": STATEMENT_LINE_ID,
            "payment_id": PAYMENT_ID,
            "is_reconciled": stmt_final[0].get('is_reconciled') if stmt_final else None,
            "reconciled_statement_line_ids": pay_final[0].get('reconciled_statement_line_ids') if pay_final else None,
            "partner_id": stmt_final[0].get('partner_id') if stmt_final else None,
        }
        print(f"\n{json.dumps(resultado, default=str, indent=2)}")


if __name__ == '__main__':
    main()
