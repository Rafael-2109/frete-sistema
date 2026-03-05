#!/usr/bin/env python3
"""
Diagnostico: Por que NFs de devolucao nao aparecem no relatorio IBS/CBS?

Queries read-only no Odoo para identificar NFs com operacao "DEVOLUCAO DE VENDAS"
e verificar se o domain do relatorio as capturaria.

Uso:
    source .venv/bin/activate
    python scripts/diagnostico_devolucoes_ibscbs.py
"""

import sys
import os
from datetime import date, timedelta
from collections import Counter

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.odoo.utils.connection import get_odoo_connection


def main():
    odoo = get_odoo_connection()
    if not odoo.authenticate():
        print("FALHA na autenticacao com Odoo")
        return

    print("=" * 80)
    print("DIAGNOSTICO: DEVOLUCOES NO RELATORIO IBS/CBS")
    print("=" * 80)

    # ================================================================
    # STEP 1: Encontrar TODAS as operacoes de devolucao
    # ================================================================
    print("\n--- STEP 1: Operacoes de devolucao no Odoo ---")
    operacoes = odoo.search_read(
        'l10n_br_ciel_it_account.operacao',
        [['name', 'ilike', 'devol']],
        ['id', 'name', 'company_id'],
        limit=0
    )
    print(f"Encontradas {len(operacoes)} operacoes com 'devol' no nome:")
    for op in operacoes:
        company = op.get('company_id', [None, ''])
        company_name = company[1] if isinstance(company, list) else str(company)
        print(f"  ID={op['id']:>4} | Company={company_name:<30} | {op['name']}")

    if not operacoes:
        print("NENHUMA operacao de devolucao encontrada. Tentando busca mais ampla...")
        operacoes = odoo.search_read(
            'l10n_br_ciel_it_account.operacao',
            [],
            ['id', 'name', 'company_id'],
            limit=0
        )
        print(f"\nTODAS as {len(operacoes)} operacoes fiscais:")
        for op in operacoes:
            company = op.get('company_id', [None, ''])
            company_name = company[1] if isinstance(company, list) else str(company)
            print(f"  ID={op['id']:>4} | Company={company_name:<30} | {op['name']}")
        return

    operacao_ids = [op['id'] for op in operacoes]
    operacao_map = {op['id']: op['name'] for op in operacoes}

    # ================================================================
    # STEP 2: Encontrar account.move.line com essas operacoes (90 dias)
    # ================================================================
    print("\n--- STEP 2: Linhas de fatura com operacoes de devolucao (ultimos 90 dias) ---")
    data_corte = (date.today() - timedelta(days=90)).isoformat()

    lines = odoo.search_read(
        'account.move.line',
        [
            ['l10n_br_operacao_id', 'in', operacao_ids],
            ['date', '>=', data_corte],
            ['display_type', '=', 'product'],
        ],
        ['id', 'move_id', 'l10n_br_operacao_id'],
        limit=0
    )
    print(f"Encontradas {len(lines)} linhas de produto com operacao de devolucao")

    if not lines:
        print("NENHUMA linha encontrada. Tentando SEM filtro display_type...")
        lines = odoo.search_read(
            'account.move.line',
            [
                ['l10n_br_operacao_id', 'in', operacao_ids],
                ['date', '>=', data_corte],
            ],
            ['id', 'move_id', 'l10n_br_operacao_id', 'display_type'],
            limit=0
        )
        print(f"Encontradas {len(lines)} linhas (qualquer display_type)")
        display_types = Counter(ln.get('display_type', 'None') for ln in lines)
        print(f"  display_type: {dict(display_types)}")
        if not lines:
            print("ZERO linhas encontradas. Abortando.")
            return

    # Coletar move_ids unicos
    move_ids = list(set(ln['move_id'][0] for ln in lines if ln.get('move_id')))
    print(f"  -> {len(move_ids)} faturas (account.move) distintas")

    # ================================================================
    # STEP 3: Ler cabecalhos das faturas
    # ================================================================
    print("\n--- STEP 3: Detalhes das faturas de devolucao ---")
    moves = odoo.search_read(
        'account.move',
        [['id', 'in', move_ids]],
        ['id', 'name', 'move_type', 'state', 'invoice_date', 'date',
         'company_id', 'l10n_br_tipo_pedido', 'l10n_br_tipo_pedido_entrada',
         'l10n_br_operacao_id', 'l10n_br_numero_nf', 'amount_total'],
        limit=0
    )
    print(f"Lidos {len(moves)} cabecalhos de fatura")

    # Mapear operacao da line para o move (ja que l10n_br_operacao_id pode ser False no move)
    move_operacao_from_line = {}
    for ln in lines:
        mid = ln['move_id'][0] if ln.get('move_id') else None
        op_id = ln['l10n_br_operacao_id'][0] if ln.get('l10n_br_operacao_id') else None
        if mid and op_id:
            move_operacao_from_line[mid] = operacao_map.get(op_id, f'ID={op_id}')

    # ================================================================
    # STEP 4: Diagnostico detalhado
    # ================================================================
    print("\n--- STEP 4: DIAGNOSTICO ---")

    # Contadores
    move_types = Counter()
    states = Counter()
    companies = Counter()
    operacoes_count = Counter()
    excluidos_motivo = Counter()

    # Domain do relatorio atual
    tipos_relatorio = {'out_invoice', 'out_refund', 'in_invoice', 'in_refund'}

    print(f"\n{'='*120}")
    print(f"{'Fatura':<25} {'NF':>8} {'move_type':<15} {'state':<10} {'invoice_date':>12} {'date':>12} {'Company':<8} {'tipo_ped_saida':<20} {'tipo_ped_entrada':<20} {'Operacao (move)':<35} {'Operacao (line)':<35} {'Valor':>12} {'Incluida?':<10}")
    print(f"{'='*120}")

    for m in sorted(moves, key=lambda x: x.get('date', '') or ''):
        move_type = m.get('move_type', '')
        state = m.get('state', '')
        invoice_date = m.get('invoice_date', '')
        dt = m.get('date', '')
        company = m.get('company_id', [None, ''])
        company_name = company[1] if isinstance(company, list) else str(company)
        company_short = company_name[:7] if company_name else ''
        tipo_saida = m.get('l10n_br_tipo_pedido', '') or ''
        tipo_entrada = m.get('l10n_br_tipo_pedido_entrada', '') or ''
        operacao_move = ''
        if m.get('l10n_br_operacao_id'):
            if isinstance(m['l10n_br_operacao_id'], list):
                operacao_move = m['l10n_br_operacao_id'][1]
            else:
                operacao_move = str(m['l10n_br_operacao_id'])
        operacao_line = move_operacao_from_line.get(m['id'], '')
        valor = m.get('amount_total', 0)
        nf = m.get('l10n_br_numero_nf', '') or ''

        # Verificar se seria incluida pelo domain do relatorio
        motivos_exclusao = []
        if move_type not in tipos_relatorio:
            motivos_exclusao.append(f"move_type={move_type}")
        if state != 'posted':
            motivos_exclusao.append(f"state={state}")

        incluida = "SIM" if not motivos_exclusao else "NAO"

        move_types[move_type] += 1
        states[state] += 1
        companies[company_short] += 1
        operacoes_count[operacao_line or operacao_move] += 1

        if motivos_exclusao:
            for motivo in motivos_exclusao:
                excluidos_motivo[motivo] += 1

        print(f"{m.get('name', ''):<25} {str(nf):>8} {move_type:<15} {state:<10} {str(invoice_date):>12} {str(dt):>12} {company_short:<8} {tipo_saida:<20} {tipo_entrada:<20} {operacao_move:<35} {operacao_line:<35} {valor:>12,.2f} {incluida:<10} {' | '.join(motivos_exclusao)}")

    # ================================================================
    # STEP 5: Resumo
    # ================================================================
    print(f"\n{'='*80}")
    print("RESUMO")
    print(f"{'='*80}")

    print(f"\nTotal de NFs de devolucao encontradas: {len(moves)}")

    print(f"\nPor move_type:")
    for mt, count in move_types.most_common():
        in_report = "INCLUIDO no relatorio" if mt in tipos_relatorio else "*** EXCLUIDO do relatorio ***"
        print(f"  {mt:<15} = {count:>4}  ({in_report})")

    print(f"\nPor state:")
    for st, count in states.most_common():
        print(f"  {st:<15} = {count:>4}")

    print(f"\nPor company:")
    for comp, count in companies.most_common():
        print(f"  {comp:<20} = {count:>4}")

    print(f"\nPor operacao:")
    for op, count in operacoes_count.most_common():
        print(f"  {op:<40} = {count:>4}")

    if excluidos_motivo:
        print(f"\n*** MOTIVOS DE EXCLUSAO DO RELATORIO ***")
        for motivo, count in excluidos_motivo.most_common():
            print(f"  {motivo:<30} = {count:>4} NFs excluidas")
    else:
        print(f"\nTodas as NFs de devolucao SERIAM incluidas pelo domain atual do relatorio.")
        print("Se nao estao aparecendo, o problema pode ser:")
        print("  1. Periodo (datas) selecionado nao cobre essas NFs")
        print("  2. Checkboxes 'Saidas'/'Entradas' desmarcados")
        print("  3. l10n_br_operacao_id retorna False no account.move (computed, store=false)")


if __name__ == '__main__':
    main()
