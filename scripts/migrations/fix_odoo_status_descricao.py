#!/usr/bin/env python3
"""
Corrige odoo_status_descricao nas NFDs existentes
para bater com os valores corretos do Odoo DFE.

STATUS CORRETOS do DFE no Odoo (l10n_br_ciel_it_account.dfe):
- 01: Rascunho - NFD recebida, não processada
- 02: Sincronizado - NFD sincronizada
- 03: Ciência/Confirmado - NFD manifestada
- 04: PO - Pedido de Compra criado, PENDENTE entrada física
- 05: Rateio - Rateio de custos
- 06: Concluído - ENTRADA FÍSICA REALIZADA
- 07: Rejeitado - NFD rejeitada

Autor: Sistema de Fretes
Data: 11/01/2026
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text

# STATUS_MAP CORRETO (conforme Odoo DFE)
STATUS_MAP_CORRETO = {
    '01': 'Rascunho',
    '02': 'Sincronizado',
    '03': 'Ciência/Confirmado',
    '04': 'PO',
    '05': 'Rateio',
    '06': 'Concluído',
    '07': 'Rejeitado',
}


def corrigir_status_descricao():
    """Corrige odoo_status_descricao nas NFDs existentes"""
    app = create_app()
    with app.app_context():
        print("=" * 60)
        print("🔧 BACKFILL - Corrigindo odoo_status_descricao")
        print("=" * 60)

        total_atualizado = 0

        for codigo, descricao in STATUS_MAP_CORRETO.items():
            result = db.session.execute(text("""
                UPDATE nf_devolucao
                SET odoo_status_descricao = :descricao
                WHERE odoo_status_codigo = :codigo
                AND (odoo_status_descricao IS NULL OR odoo_status_descricao != :descricao)
            """), {'codigo': codigo, 'descricao': descricao})

            atualizados = result.rowcount
            total_atualizado += atualizados

            if atualizados > 0:
                print(f"   Status {codigo} → '{descricao}': {atualizados} registros")

        db.session.commit()

        print("\n" + "=" * 60)
        print("✅ BACKFILL CONCLUÍDO")
        print("=" * 60)
        print(f"\n📊 Total de registros atualizados: {total_atualizado}")

        # Verificação pós-correção
        print("\n📊 VERIFICAÇÃO PÓS-CORREÇÃO:")
        result = db.session.execute(text("""
            SELECT
                odoo_status_codigo,
                odoo_status_descricao,
                COUNT(*) as total
            FROM nf_devolucao
            WHERE ativo = true
            AND odoo_status_codigo IS NOT NULL
            GROUP BY odoo_status_codigo, odoo_status_descricao
            ORDER BY odoo_status_codigo
        """)).fetchall()

        for row in result:
            codigo = row[0] or 'NULL'
            descricao = row[1] or 'NULL'
            total = row[2]
            esperado = STATUS_MAP_CORRETO.get(codigo, '?')
            status = "✅" if descricao == esperado else "❌"
            print(f"   {status} {codigo}: '{descricao}' ({total} registros)")

        print("=" * 60)


if __name__ == '__main__':
    corrigir_status_descricao()
