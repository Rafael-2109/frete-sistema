#!/usr/bin/env python3
"""
Script para Limpar Divergências Órfãs
=====================================

Limpa divergências pendentes de NFs que já foram finalizadas no Odoo
(status = 'finalizado_odoo').

Este script corrige o bug onde divergências não eram limpas quando
um DFE era marcado como finalizado_odoo.

Uso:
    python scripts/limpar_divergencias_orfas.py          # Modo diagnóstico
    python scripts/limpar_divergencias_orfas.py --fix    # Corrige os problemas
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text


def diagnosticar():
    """Lista divergências órfãs sem corrigir."""
    app = create_app()
    with app.app_context():
        print("=" * 80)
        print("DIAGNÓSTICO: DIVERGÊNCIAS ÓRFÃS")
        print("=" * 80)
        print()

        # Buscar divergências de validações já finalizadas
        query = text("""
            SELECT
                d.id as div_id,
                d.tipo_divergencia,
                d.status as div_status,
                d.cod_produto_fornecedor,
                v.numero_nf,
                v.status as val_status,
                v.odoo_po_vinculado_name,
                v.odoo_dfe_id
            FROM divergencia_nf_po d
            JOIN validacao_nf_po_dfe v ON d.validacao_id = v.id
            WHERE v.status = 'finalizado_odoo'
              AND d.status = 'pendente'
            ORDER BY v.numero_nf, d.tipo_divergencia
        """)

        result = db.session.execute(query)
        orfas = list(result)

        print(f"📊 Divergências órfãs encontradas: {len(orfas)}")
        print("-" * 80)

        if orfas:
            print("\nDivergências pendentes em NFs já finalizadas no Odoo:\n")
            for row in orfas:
                print(f"  Div ID: {row[0]} | NF: {row[4]} | Tipo: {row[1]}")
                print(f"    Código Forn: {row[3]} | PO Vinculado: {row[6]}")
                print()

            # Agrupar por NF para resumo
            nfs = {}
            for row in orfas:
                nf = row[4]
                if nf not in nfs:
                    nfs[nf] = {'count': 0, 'po': row[6], 'dfe_id': row[7]}
                nfs[nf]['count'] += 1

            print("\n" + "-" * 80)
            print("RESUMO POR NF:")
            for nf, info in sorted(nfs.items()):
                print(f"  NF {nf}: {info['count']} divergência(s) - PO: {info['po']}")

            print("\n" + "=" * 80)
            print("Para corrigir, execute:")
            print("  python scripts/limpar_divergencias_orfas.py --fix")
            print("=" * 80)

        else:
            print("\n✅ Nenhuma divergência órfã encontrada!")

        return len(orfas)


def corrigir():
    """Limpa divergências órfãs de NFs finalizadas."""
    app = create_app()
    with app.app_context():
        print("=" * 80)
        print("CORREÇÃO: LIMPANDO DIVERGÊNCIAS ÓRFÃS")
        print("=" * 80)
        print()

        # Contar antes
        count_antes = db.session.execute(text("""
            SELECT COUNT(*)
            FROM divergencia_nf_po d
            JOIN validacao_nf_po_dfe v ON d.validacao_id = v.id
            WHERE v.status = 'finalizado_odoo'
              AND d.status = 'pendente'
        """)).scalar()

        print(f"Divergências órfãs encontradas: {count_antes}")

        if count_antes == 0:
            print("✅ Nenhuma divergência órfã para limpar!")
            return

        # Executar limpeza
        result = db.session.execute(text("""
            DELETE FROM divergencia_nf_po
            WHERE id IN (
                SELECT d.id
                FROM divergencia_nf_po d
                JOIN validacao_nf_po_dfe v ON d.validacao_id = v.id
                WHERE v.status = 'finalizado_odoo'
                  AND d.status = 'pendente'
            )
        """))

        deleted = result.rowcount
        db.session.commit()

        print(f"\n✅ {deleted} divergências órfãs removidas!")

        # Verificar também matches órfãos
        count_matches = db.session.execute(text("""
            SELECT COUNT(*)
            FROM match_nf_po_item m
            JOIN validacao_nf_po_dfe v ON m.validacao_id = v.id
            WHERE v.status = 'finalizado_odoo'
        """)).scalar()

        if count_matches > 0:
            result_matches = db.session.execute(text("""
                DELETE FROM match_nf_po_item
                WHERE validacao_id IN (
                    SELECT id FROM validacao_nf_po_dfe
                    WHERE status = 'finalizado_odoo'
                )
            """))
            db.session.commit()
            print(f"✅ {result_matches.rowcount} matches órfãos também removidos!")

        print("\n" + "=" * 80)
        print("CORREÇÃO CONCLUÍDA")
        print("=" * 80)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--fix":
        confirma = input("⚠️  Tem certeza que deseja limpar as divergências órfãs? (sim/nao): ")
        if confirma.lower() == "sim":
            corrigir()
        else:
            print("Cancelado.")
    else:
        diagnosticar()
