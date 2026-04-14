# -*- coding: utf-8 -*-
"""
Backfill: Session_id proxy para eventos USUARIO historicos
===========================================================

Atribui session_id no formato USUARIO_YYYYMMDDHHMI_{usuario} para eventos
origem=USUARIO com session_id NULL. Agrupa eventos do mesmo usuario na
mesma janela de 1 minuto em um mesmo session_id (proxy temporal).

NAO e o session_id original do request (impossivel reconstruir). E
suficiente para ML de padroes de uso e correlacao cross-entidade.

Idempotente: WHERE session_id IS NULL limita primeira execucao.

Uso: python scripts/migrations/backfill_session_id_usuario.py
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
            print("BACKFILL: Session_id proxy para eventos USUARIO historicos")
            print("=" * 70)

            # BEFORE
            nulos_antes = db.session.execute(text(
                "SELECT count(*) FROM evento_supply_chain "
                "WHERE session_id IS NULL AND origem = 'USUARIO'"
            )).scalar()
            print(f"\n[BEFORE] Eventos USUARIO sem session_id: {nulos_antes}")

            if nulos_antes == 0:
                print("\n[OK] Nada a fazer — todos eventos USUARIO ja tem session_id.")
                return True

            # Ler SQL de migracao
            sql_path = os.path.join(
                os.path.dirname(__file__),
                'backfill_session_id_usuario.sql'
            )
            with open(sql_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()

            print(f"\n[EXEC] Aplicando backfill em {nulos_antes} eventos...")
            db.session.execute(text(sql_content))
            db.session.commit()

            # AFTER
            nulos_depois = db.session.execute(text(
                "SELECT count(*) FROM evento_supply_chain "
                "WHERE session_id IS NULL AND origem = 'USUARIO'"
            )).scalar()
            print(f"\n[AFTER] Eventos USUARIO sem session_id: {nulos_depois}")

            sessoes_criadas = db.session.execute(text(
                "SELECT count(DISTINCT session_id) FROM evento_supply_chain "
                "WHERE session_id LIKE 'USUARIO_%'"
            )).scalar()
            print(f"[OK] Sessoes USUARIO_ geradas: {sessoes_criadas}")

            # Amostra
            amostra = db.session.execute(text(
                "SELECT session_id, count(*) AS qtd "
                "FROM evento_supply_chain "
                "WHERE session_id LIKE 'USUARIO_%' "
                "GROUP BY session_id "
                "ORDER BY qtd DESC "
                "LIMIT 5"
            )).fetchall()
            print("\n[AMOSTRA] Top 5 sessoes (maior volume):")
            for row in amostra:
                print(f"  {row[0]}: {row[1]} eventos")

            print("\n" + "=" * 70)
            if (nulos_depois or 0) == 0:
                print("BACKFILL CONCLUIDO COM SUCESSO")
            else:
                print("BACKFILL CONCLUIDO COM AVISOS — verificar itens acima")
            print("=" * 70)

            return (nulos_depois or 0) == 0

        except Exception as e:
            db.session.rollback()
            print(f"\n[ERRO FATAL] Backfill falhou: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == '__main__':
    sucesso = executar_backfill()
    sys.exit(0 if sucesso else 1)
