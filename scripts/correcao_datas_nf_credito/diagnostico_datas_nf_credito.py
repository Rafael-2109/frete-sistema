#!/usr/bin/env python3
"""
DIAGNÓSTICO - NFs de Crédito com Data de Lançamento Incorreta
==============================================================

Este script identifica todas as NFs de Crédito (out_refund) que tiveram a
data de lançamento (date) alterada incorretamente para a data de emissão (invoice_date).

Problema identificado:
- Um script alterou account_move.date para ser igual a account_move.invoice_date
- A data correta de lançamento pode ser recuperada via mail.tracking.value

Autor: Sistema de Fretes - Análise CIEL IT
Data: 11/12/2025
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.odoo.utils.connection import get_odoo_connection
from app.utils.timezone import agora_utc_naive


def diagnosticar_nfs_com_problema():
    """
    Identifica todas as NFs de crédito com data de lançamento incorreta
    e recupera a data original via tracking_values
    """
    odoo = get_odoo_connection()
    if not odoo.authenticate():
        print("ERRO: Falha na autenticação com Odoo")
        return None

    print("=" * 120)
    print("DIAGNÓSTICO - NFs de Crédito com Data de Lançamento Incorreta")
    print(f"Data de execução: {agora_utc_naive().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 120)

    # 1. Buscar tracking_values de alteração do campo date em julho/2025
    print("\n[1/4] Buscando alterações de data em julho/2025...")
    tracking_values = odoo.execute_kw(
        'mail.tracking.value', 'search_read',
        [[
            ['field_id', '=', 4333],  # Campo date
            ['create_date', '>=', '2025-07-01 00:00:00'],
            ['create_date', '<=', '2025-07-31 23:59:59']
        ]],
        {'fields': ['id', 'old_value_datetime', 'new_value_datetime', 'mail_message_id'], 'limit': 5000}
    )
    print(f"   Total de alterações encontradas: {len(tracking_values)}")

    # 2. Coletar IDs dos documentos
    print("\n[2/4] Identificando documentos afetados...")
    message_ids = list(set([t['mail_message_id'][0] for t in tracking_values if t['mail_message_id']]))

    messages = odoo.execute_kw(
        'mail.message', 'search_read',
        [[['id', 'in', message_ids], ['model', '=', 'account.move']]],
        {'fields': ['id', 'res_id'], 'limit': 5000}
    )
    move_ids = list(set([m['res_id'] for m in messages]))
    print(f"   Total de account.move com alterações: {len(move_ids)}")

    # 3. Filtrar apenas NFs de crédito com problema
    print("\n[3/4] Filtrando NFs de crédito com problema...")
    moves = odoo.execute_kw(
        'account.move', 'search_read',
        [[['id', 'in', move_ids], ['move_type', '=', 'out_refund'], ['state', '=', 'posted']]],
        {'fields': ['id', 'name', 'ref', 'invoice_date', 'date', 'create_date', 'partner_id'], 'limit': 5000}
    )

    # Filtrar NFs onde date == invoice_date MAS create_date é diferente
    problemas = []
    for m in moves:
        if m['date'] == m['invoice_date']:
            create_date = m['create_date'][:10] if m['create_date'] else None
            if create_date and create_date != m['invoice_date']:
                problemas.append(m)

    print(f"   Total de NFs de crédito com problema: {len(problemas)}")

    # 4. Recuperar data original de cada NF
    print("\n[4/4] Recuperando data original via tracking_values...")
    correcoes = []

    for idx, m in enumerate(problemas):
        if (idx + 1) % 20 == 0:
            print(f"   Processando {idx + 1}/{len(problemas)}...")

        move_id = m['id']

        # Buscar mensagens do documento
        msg = odoo.execute_kw(
            'mail.message', 'search_read',
            [[['model', '=', 'account.move'], ['res_id', '=', move_id]]],
            {'fields': ['tracking_value_ids'], 'limit': 100}
        )

        tracking_ids = []
        for ms in msg:
            tracking_ids.extend(ms['tracking_value_ids'])

        data_original = None
        if tracking_ids:
            tracks = odoo.execute_kw(
                'mail.tracking.value', 'search_read',
                [[['id', 'in', tracking_ids], ['field_id', '=', 4333]]],
                {'fields': ['old_value_datetime', 'create_date'], 'order': 'create_date asc', 'limit': 1}
            )

            if tracks and tracks[0]['old_value_datetime']:
                data_original = tracks[0]['old_value_datetime'][:10]

        # Se não encontrou via tracking, usar create_date como fallback
        if not data_original:
            data_original = m['create_date'][:10] if m['create_date'] else None

        correcoes.append({
            'id': move_id,
            'name': m['name'],
            'ref': m['ref'] or '',
            'partner_id': m['partner_id'][0] if m['partner_id'] else None,
            'partner_name': m['partner_id'][1] if m['partner_id'] else 'N/A',
            'invoice_date': m['invoice_date'],
            'date_atual': m['date'],
            'date_original': data_original,
            'create_date': m['create_date'][:10] if m['create_date'] else None
        })

    # Exibir resultados
    print("\n" + "=" * 120)
    print("RESULTADO DO DIAGNÓSTICO")
    print("=" * 120)

    print(f"\nTotal de NFs de crédito com problema: {len(correcoes)}")

    # Verificar quantas precisam de correção
    precisam_correcao = [c for c in correcoes if c['date_original'] and c['date_original'] != c['date_atual']]
    print(f"NFs que precisam de correção: {len(precisam_correcao)}")

    print("\n" + "-" * 120)
    print(f"{'ID':<8} | {'Nome':<22} | {'Data Atual':<12} | {'Data Original':<14} | {'Create Date':<12} | Parceiro")
    print("-" * 120)

    for c in sorted(correcoes, key=lambda x: x['invoice_date'] or '', reverse=True):
        precisa = "⚠️" if c['date_original'] and c['date_original'] != c['date_atual'] else "✓"
        print(f"{c['id']:<8} | {c['name']:<22} | {c['date_atual']:<12} | {c['date_original'] or 'N/A':<14} | {c['create_date']:<12} | {c['partner_name'][:30]} {precisa}")

    # Salvar resultado em JSON para uso pelo script de correção
    output_file = os.path.join(os.path.dirname(__file__), 'diagnostico_resultado.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'data_execucao': agora_utc_naive().isoformat(),
            'total_problemas': len(correcoes),
            'precisam_correcao': len(precisam_correcao),
            'correcoes': correcoes
        }, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Resultado salvo em: {output_file}")

    return correcoes


if __name__ == '__main__':
    diagnosticar_nfs_com_problema()
