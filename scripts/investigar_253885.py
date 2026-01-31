#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Investigacao da Fatura 253885 (NF 134244) no Odoo

Verifica:
- Estado da fatura
- Desconto do parceiro
- Todas as linhas contabeis (debit/credit)
- Titulos CLIENTES (e se ha titulo ano 2000)
- Linhas de desconto
- Equilibrio da fatura

Autor: Sistema de Fretes / Rafael Nascimento
Data: 2026-01-30
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app

app = create_app()

with app.app_context():
    from app.odoo.utils.connection import get_odoo_connection

    MOVE_ID = 253885

    print("\n" + "=" * 80)
    print(f"INVESTIGACAO DA FATURA {MOVE_ID}")
    print("=" * 80)

    # Conectar ao Odoo
    print("\nConectando ao Odoo...")
    conn = get_odoo_connection()
    print("Conectado com sucesso.")

    # =========================================================================
    # (a) Estado da fatura
    # =========================================================================
    print("\n" + "-" * 80)
    print("(a) ESTADO DA FATURA")
    print("-" * 80)

    move = conn.search_read('account.move', [['id', '=', MOVE_ID]], [
        'name', 'state', 'amount_total', 'amount_residual', 'payment_state', 'partner_id'
    ])

    if not move:
        print(f"ERRO: Fatura {MOVE_ID} nao encontrada!")
        sys.exit(1)

    m = move[0]
    partner_id = m['partner_id'][0] if m['partner_id'] else None
    partner_name = m['partner_id'][1] if m['partner_id'] else 'N/A'

    print(f"  Nome: {m['name']}")
    print(f"  Estado: {m['state']}")
    print(f"  Valor Total: R$ {m['amount_total']:.2f}")
    print(f"  Residual: R$ {m['amount_residual']:.2f}")
    print(f"  Payment State: {m['payment_state']}")
    print(f"  Parceiro: {partner_name} (ID: {partner_id})")

    # =========================================================================
    # (b) Desconto do parceiro
    # =========================================================================
    print("\n" + "-" * 80)
    print("(b) DESCONTO DO PARCEIRO")
    print("-" * 80)

    desconto_pct = 0
    if partner_id:
        partner = conn.search_read('res.partner', [['id', '=', partner_id]], [
            'name', 'x_studio_desconto_contratual', 'x_studio_desconto'
        ])
        if partner:
            p = partner[0]
            print(f"  Nome: {p['name']}")
            print(f"  Desconto Contratual: {p.get('x_studio_desconto_contratual', False)}")
            desconto_pct = p.get('x_studio_desconto', 0) or 0
            print(f"  Percentual Desconto: {desconto_pct}%")
        else:
            print(f"  Parceiro {partner_id} nao encontrado!")
    else:
        print("  Sem parceiro associado!")

    # =========================================================================
    # (c) TODAS as linhas contabeis
    # =========================================================================
    print("\n" + "-" * 80)
    print("(c) TODAS AS LINHAS CONTABEIS")
    print("-" * 80)

    lines = conn.search_read('account.move.line', [['move_id', '=', MOVE_ID]], [
        'id', 'name', 'debit', 'credit', 'date_maturity', 'account_id', 'amount_residual'
    ])

    total_debit = 0
    total_credit = 0

    print(f"\n  {'ID':<10} {'CONTA':<45} {'DEBITO':>15} {'CREDITO':>15} {'RESIDUAL':>15} {'VENCIMENTO':<12} {'DESCRICAO'}")
    print("  " + "-" * 150)

    for line in lines:
        acc_name = line['account_id'][1] if line['account_id'] else 'N/A'
        acc_id = line['account_id'][0] if line['account_id'] else 'N/A'
        debit = line['debit'] or 0
        credit = line['credit'] or 0
        residual = line['amount_residual'] or 0
        venc = line['date_maturity'] or 'N/A'
        name = (line['name'] or '')[:50]

        total_debit += debit
        total_credit += credit

        print(f"  {line['id']:<10} {acc_name:<45} {debit:>15.2f} {credit:>15.2f} {residual:>15.2f} {venc:<12} {name}")

    print("  " + "-" * 150)
    print(f"  {'TOTAL':<10} {'':<45} {total_debit:>15.2f} {total_credit:>15.2f}")
    print(f"\n  Diferenca (Debit - Credit): R$ {total_debit - total_credit:.2f}")
    print(f"  Equilibrada: {'SIM' if abs(total_debit - total_credit) < 0.01 else 'NAO'}")

    # =========================================================================
    # (d) Identificacao de titulos e descontos
    # =========================================================================
    print("\n" + "-" * 80)
    print("(d) IDENTIFICACAO DE TITULOS E DESCONTOS")
    print("-" * 80)

    # Titulos CLIENTES com debit > 0
    titulos = []
    titulos_2000 = []
    titulo_valido = None

    for line in lines:
        acc_name = line['account_id'][1] if line['account_id'] else ''
        if 'CLIENTES' in acc_name.upper() and (line['debit'] or 0) > 0:
            titulos.append(line)
            ano = line['date_maturity'][:4] if line['date_maturity'] else 'N/A'
            if ano == '2000':
                titulos_2000.append(line)
            else:
                titulo_valido = line

    print(f"\n  TITULOS A RECEBER (conta CLIENTES, debit > 0): {len(titulos)}")
    for t in titulos:
        ano = t['date_maturity'][:4] if t['date_maturity'] else 'N/A'
        status = "*** ANO 2000 (BUG) ***" if ano == '2000' else "VALIDO"
        print(f"    ID {t['id']}: Debit=R$ {t['debit']:.2f} | Residual=R$ {t['amount_residual']:.2f} | Venc={t['date_maturity']} | {status}")

    # Linhas de desconto
    descontos = []
    for line in lines:
        acc_name = line['account_id'][1] if line['account_id'] else ''
        if 'DESCONTO' in acc_name.upper():
            descontos.append(line)

    print(f"\n  LINHAS DE DESCONTO: {len(descontos)}")
    for d in descontos:
        acc_name = d['account_id'][1] if d['account_id'] else 'N/A'
        debit = d['debit'] or 0
        credit = d['credit'] or 0
        print(f"    ID {d['id']}: Debit=R$ {debit:.2f} | Credit=R$ {credit:.2f} | Conta={acc_name}")

    # =========================================================================
    # (e) Diagnostico
    # =========================================================================
    print("\n" + "-" * 80)
    print("(e) DIAGNOSTICO")
    print("-" * 80)

    equilibrada = abs(total_debit - total_credit) < 0.01
    tem_titulo_2000 = len(titulos_2000) > 0
    tem_desconto = len(descontos) > 0

    print(f"  Fatura equilibrada: {'SIM' if equilibrada else 'NAO'}")
    print(f"  Tem titulo ano 2000: {'SIM ({} titulo(s))'.format(len(titulos_2000)) if tem_titulo_2000 else 'NAO'}")
    print(f"  Tem linha de desconto: {'SIM ({} linha(s))'.format(len(descontos)) if tem_desconto else 'NAO'}")
    print(f"  Desconto contratual parceiro: {desconto_pct}%")

    if tem_titulo_2000:
        soma_titulos = sum(t['debit'] for t in titulos)
        soma_2000 = sum(t['debit'] for t in titulos_2000)
        titulo_valido_valor = titulo_valido['debit'] if titulo_valido else 0
        valor_desconto_existente = sum(d['debit'] for d in descontos if (d['debit'] or 0) > 0)

        print(f"\n  DETALHES DO BUG:")
        print(f"    Soma todos os titulos: R$ {soma_titulos:.2f}")
        print(f"    Titulo valido: R$ {titulo_valido_valor:.2f} (ID: {titulo_valido['id'] if titulo_valido else 'N/A'})")
        print(f"    Titulo(s) ano 2000: R$ {soma_2000:.2f}")
        print(f"    Desconto existente (debit): R$ {valor_desconto_existente:.2f}")
        print(f"    Desconto calculado ({desconto_pct}%): R$ {soma_titulos * (desconto_pct / 100):.2f}" if desconto_pct > 0 else "")

        print(f"\n  CORRECAO NECESSARIA: SIM")
        print(f"    1. Despublicar fatura")
        print(f"    2. Zerar titulo(s) ano 2000 (IDs: {[t['id'] for t in titulos_2000]})")
        print(f"    3. Configurar desconto: primeira linha recebe R$ {valor_desconto_existente:.2f}")
        print(f"    4. Ajustar titulo valido (ID {titulo_valido['id'] if titulo_valido else 'N/A'}): debit = R$ {soma_titulos:.2f}")
        print(f"    5. Verificar equilibrio")
        print(f"    6. Republicar")
    else:
        print(f"\n  CORRECAO NECESSARIA: NAO (sem titulo ano 2000)")

    print("\n" + "=" * 80)
    print("FIM DA INVESTIGACAO")
    print("=" * 80 + "\n")
