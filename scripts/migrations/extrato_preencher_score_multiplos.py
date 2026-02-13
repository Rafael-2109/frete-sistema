# -*- coding: utf-8 -*-
"""
Migration: Preencher match_score em itens MULTIPLOS_MATCHES
==========================================================

Itens com status_match='MULTIPLOS_MATCHES' que possuem matches_candidatos JSON
mas match_score IS NULL precisam ser atualizados com o score do melhor candidato.

Uso:
    source .venv/bin/activate
    python scripts/migrations/extrato_preencher_score_multiplos.py

Autor: Sistema de Fretes
Data: 2026-02-13
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db

app = create_app()


def executar():
    """Preenche match_score a partir do JSON matches_candidatos."""

    with app.app_context():
        # BEFORE: contar afetados
        with db.engine.connect() as conn:
            result = conn.execute(db.text("""
                SELECT COUNT(*) FROM extrato_item
                WHERE status_match = 'MULTIPLOS_MATCHES'
                  AND match_score IS NULL
                  AND matches_candidatos IS NOT NULL
            """))
            total_antes = result.scalar()
            print(f"[BEFORE] Itens MULTIPLOS_MATCHES sem score: {total_antes}")

            if total_antes == 0:
                print("Nada a fazer. Todos os itens já possuem match_score.")
                return

        # EXECUTE: buscar itens e atualizar
        with db.engine.begin() as conn:
            rows = conn.execute(db.text("""
                SELECT id, matches_candidatos FROM extrato_item
                WHERE status_match = 'MULTIPLOS_MATCHES'
                  AND match_score IS NULL
                  AND matches_candidatos IS NOT NULL
            """)).fetchall()

            atualizados = 0
            erros = 0

            for row in rows:
                item_id = row[0]
                candidatos_json = row[1]

                try:
                    candidatos = json.loads(candidatos_json)
                    if not candidatos:
                        continue

                    # Candidatos já estão ordenados DESC por score no JSON
                    melhor = candidatos[0]
                    score = melhor.get('score')
                    criterio = melhor.get('criterio', '')

                    if score is not None:
                        # Adicionar sufixo +MULTIPLOS(N)
                        n_candidatos = len(candidatos)
                        criterio_full = f"{criterio}+MULTIPLOS({n_candidatos})"

                        conn.execute(db.text("""
                            UPDATE extrato_item
                            SET match_score = :score,
                                match_criterio = :criterio
                            WHERE id = :id
                        """), {'score': int(score), 'criterio': criterio_full, 'id': item_id})
                        atualizados += 1

                except (json.JSONDecodeError, KeyError, IndexError) as e:
                    print(f"  ERRO item {item_id}: {e}")
                    erros += 1

            print(f"[EXECUTE] Atualizados: {atualizados} | Erros: {erros}")

        # AFTER: verificar resultado
        with db.engine.connect() as conn:
            result = conn.execute(db.text("""
                SELECT COUNT(*) FROM extrato_item
                WHERE status_match = 'MULTIPLOS_MATCHES'
                  AND match_score IS NULL
            """))
            restantes = result.scalar()
            print(f"[AFTER] Itens MULTIPLOS_MATCHES sem score restantes: {restantes}")

            # Distribuição de scores preenchidos
            result = conn.execute(db.text("""
                SELECT
                    CASE
                        WHEN match_score >= 90 THEN 'alto (>=90)'
                        WHEN match_score >= 70 THEN 'medio (70-89)'
                        ELSE 'baixo (<70)'
                    END AS faixa,
                    COUNT(*) AS qtd
                FROM extrato_item
                WHERE status_match = 'MULTIPLOS_MATCHES'
                  AND match_score IS NOT NULL
                GROUP BY 1
                ORDER BY 1
            """))
            print("\nDistribuição de scores em MULTIPLOS_MATCHES:")
            for row in result:
                print(f"  {row[0]}: {row[1]}")


if __name__ == '__main__':
    executar()
