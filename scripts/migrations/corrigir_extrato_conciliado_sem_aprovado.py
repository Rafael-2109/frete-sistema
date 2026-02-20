# -*- coding: utf-8 -*-
"""
Migration: Corrigir invariante CONCILIADO => aprovado=True
==========================================================

Problema: Itens com status='CONCILIADO' mas aprovado=NULL ou FALSE.
Isso viola a invariante: CONCILIADO e terminal e implica aprovacao.

Fix: Setar aprovado=True, aprovado_em e aprovado_por para todos
os itens CONCILIADO que nao estao aprovados.

Executar: python scripts/migrations/corrigir_extrato_conciliado_sem_aprovado.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db


def main():
    app = create_app()

    with app.app_context():
        # BEFORE: contar itens afetados
        with db.engine.connect() as conn:
            result = conn.execute(db.text("""
                SELECT count(*) as total
                FROM extrato_item
                WHERE status = 'CONCILIADO'
                  AND (aprovado IS NULL OR aprovado = FALSE)
            """))
            row = result.fetchone()
            total_antes = row[0] if row else 0

        print(f"[BEFORE] Itens CONCILIADO sem aprovado=True: {total_antes}")

        if total_antes == 0:
            print("Nenhum item para corrigir. Migration ja aplicada.")
            return

        # EXECUTE: corrigir invariante
        with db.engine.begin() as conn:
            result = conn.execute(db.text("""
                UPDATE extrato_item
                SET aprovado = TRUE,
                    aprovado_em = COALESCE(processado_em, NOW()),
                    aprovado_por = 'MIGRATION_FIX'
                WHERE status = 'CONCILIADO'
                  AND (aprovado IS NULL OR aprovado = FALSE)
            """))
            atualizados = result.rowcount
            print(f"[EXECUTE] Atualizados: {atualizados} itens")

        # AFTER: verificar invariante
        with db.engine.connect() as conn:
            result = conn.execute(db.text("""
                SELECT count(*) as total
                FROM extrato_item
                WHERE status = 'CONCILIADO'
                  AND (aprovado IS NULL OR aprovado = FALSE)
            """))
            row = result.fetchone()
            total_depois = row[0] if row else 0

        print(f"[AFTER] Itens CONCILIADO sem aprovado=True: {total_depois}")

        if total_depois == 0:
            print("Migration concluida com sucesso.")
        else:
            print(f"ERRO: Ainda restam {total_depois} itens sem aprovado=True!")
            sys.exit(1)


if __name__ == '__main__':
    main()
