"""
Backfill: Promover origens de clientes para globais
Data: 30/03/2026
Descricao: Para cada CNPJ com tipo=ORIGEM, promove um registro para global
           (cliente_id=NULL). FKs de cotacoes existentes continuam validas.

Prerequisito: carvia_origens_globais_provisorio.py ja executado.

Uso:
    source .venv/bin/activate && python scripts/migrations/carvia_backfill_origens_globais.py
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
            print("=" * 60)
            print("Backfill: Promover origens para global")
            print("=" * 60)

            # 1. Listar CNPJs distintos com tipo=ORIGEM
            result = db.session.execute(text("""
                SELECT DISTINCT cnpj
                FROM carvia_cliente_enderecos
                WHERE tipo = 'ORIGEM'
                  AND cnpj IS NOT NULL
                  AND cliente_id IS NOT NULL
                ORDER BY cnpj
            """))
            cnpjs_origem = [r[0] for r in result.fetchall()]
            print(f"\nEncontrados {len(cnpjs_origem)} CNPJ(s) ORIGEM vinculados a clientes.")

            if not cnpjs_origem:
                print("Nenhuma origem para promover. Backfill concluido.")
                return

            promovidos = 0
            ja_globais = 0

            for cnpj in cnpjs_origem:
                # Verificar se ja existe origem global com este CNPJ
                existente = db.session.execute(text("""
                    SELECT id FROM carvia_cliente_enderecos
                    WHERE cnpj = :cnpj AND tipo = 'ORIGEM' AND cliente_id IS NULL
                    LIMIT 1
                """), {'cnpj': cnpj}).fetchone()

                if existente:
                    ja_globais += 1
                    continue

                # Pegar o registro mais relevante (principal=True primeiro, depois id DESC)
                registro = db.session.execute(text("""
                    SELECT id, cliente_id, razao_social, fisico_uf, fisico_cidade
                    FROM carvia_cliente_enderecos
                    WHERE cnpj = :cnpj AND tipo = 'ORIGEM'
                    ORDER BY principal DESC, id DESC
                    LIMIT 1
                """), {'cnpj': cnpj}).fetchone()

                if not registro:
                    continue

                reg_id = registro[0]
                old_cliente_id = registro[1]

                # Verificar se este registro e FK de alguma cotacao
                fk_count = db.session.execute(text("""
                    SELECT COUNT(*) FROM carvia_cotacoes
                    WHERE endereco_origem_id = :end_id
                """), {'end_id': reg_id}).fetchone()[0]

                # Promover para global: definir cliente_id = NULL
                db.session.execute(text("""
                    UPDATE carvia_cliente_enderecos
                    SET cliente_id = NULL
                    WHERE id = :end_id
                """), {'end_id': reg_id})

                promovidos += 1
                print(f"  CNPJ {cnpj}: id={reg_id} promovido (ex-cliente={old_cliente_id}, "
                      f"cidade={registro[4]}/{registro[3]}, cotacoes_vinculadas={fk_count})")

            db.session.commit()

            print(f"\nResumo:")
            print(f"  Promovidos para global: {promovidos}")
            print(f"  Ja eram globais: {ja_globais}")
            print(f"  Total CNPJs processados: {len(cnpjs_origem)}")

            # Verificacao final
            total_globais = db.session.execute(text("""
                SELECT COUNT(*) FROM carvia_cliente_enderecos
                WHERE tipo = 'ORIGEM' AND cliente_id IS NULL
            """)).fetchone()[0]
            print(f"  Total origens globais apos backfill: {total_globais}")

            print("\n" + "=" * 60)
            print("Backfill concluido com sucesso!")
            print("=" * 60)

        except Exception as e:
            db.session.rollback()
            print(f"\nERRO: {e}")
            raise


if __name__ == '__main__':
    executar_backfill()
