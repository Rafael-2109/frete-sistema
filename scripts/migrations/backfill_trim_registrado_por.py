# -*- coding: utf-8 -*-
"""
Backfill: TRIM de registrado_por em evento_supply_chain
========================================================

Aplica TRIM() em registrado_por nos eventos historicos afetados por
trailing spaces vindos de usuarios.nome.

Idempotente: pode rodar multiplas vezes sem efeito colateral.

Uso: python scripts/migrations/backfill_trim_registrado_por.py
Data: 2026-04-14
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def executar_backfill():
    app = create_app()
    with app.app_context():
        try:
            print("=" * 70)
            print("BACKFILL: Trim registrado_por em evento_supply_chain")
            print("=" * 70)

            # BEFORE
            afetados_antes = db.session.execute(text(
                "SELECT count(*) FROM evento_supply_chain "
                "WHERE registrado_por IS NOT NULL "
                "  AND registrado_por != TRIM(registrado_por)"
            )).scalar()
            print(f"\n[BEFORE] Eventos com whitespace em registrado_por: {afetados_antes}")

            if afetados_antes == 0:
                print("\n[OK] Nada a fazer — dados ja estao limpos.")
                return True

            # Amostra dos nomes afetados
            amostra = db.session.execute(text(
                "SELECT DISTINCT registrado_por "
                "FROM evento_supply_chain "
                "WHERE registrado_por IS NOT NULL "
                "  AND registrado_por != TRIM(registrado_por) "
                "LIMIT 10"
            )).fetchall()
            print("\n[AMOSTRA] Nomes afetados (ate 10):")
            for row in amostra:
                nome = row[0]
                print(f"  '{nome}' → '{nome.strip()}'")

            # UPDATE
            print(f"\n[EXEC] Aplicando TRIM em {afetados_antes} eventos...")
            result = db.session.execute(text(
                "UPDATE evento_supply_chain "
                "SET registrado_por = TRIM(registrado_por) "
                "WHERE registrado_por IS NOT NULL "
                "  AND registrado_por != TRIM(registrado_por)"
            ))
            db.session.commit()

            atualizados = result.rowcount
            print(f"[OK] {atualizados} eventos atualizados")

            # AFTER
            afetados_depois = db.session.execute(text(
                "SELECT count(*) FROM evento_supply_chain "
                "WHERE registrado_por IS NOT NULL "
                "  AND registrado_por != TRIM(registrado_por)"
            )).scalar()
            print(f"\n[AFTER] Eventos com whitespace restante: {afetados_depois}")

            print("\n" + "=" * 70)
            if afetados_depois == 0:
                print("BACKFILL CONCLUIDO COM SUCESSO")
            else:
                print("BACKFILL CONCLUIDO COM AVISOS — verificar itens acima")
            print("=" * 70)

            return afetados_depois == 0

        except Exception as e:
            db.session.rollback()
            print(f"\n[ERRO FATAL] Backfill falhou: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == '__main__':
    sucesso = executar_backfill()
    sys.exit(0 if sucesso else 1)
