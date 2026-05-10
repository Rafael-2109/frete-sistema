"""
Migration: Partial UNIQUE em custo_considerado.cod_produto WHERE custo_atual=TRUE
Previne race condition que poderia gerar 2 versoes ativas para mesmo produto.

Antes de aplicar: valida que NAO HA duplicatas (custo_atual=TRUE multiplo) — se
existir, aborta com erro. Em prod (10/05/2026), validacao confirmou 0 duplicatas.

Data: 2026-05-10 (Sprint 2 - C8 da auditoria de custeio)
"""
import sys
import os

# Path setup obrigatorio para Render Shell (regra CLAUDE.md global)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db


def run():
    app = create_app()
    with app.app_context():
        # 1. Validar que nao ha duplicatas antes
        result = db.session.execute(db.text("""
            SELECT cod_produto, COUNT(*) AS atuais
            FROM custo_considerado
            WHERE custo_atual = TRUE
            GROUP BY cod_produto
            HAVING COUNT(*) > 1
        """)).fetchall()

        if result:
            print(f"ERRO: {len(result)} produtos com 2+ versoes custo_atual=TRUE.")
            print("Resolver duplicatas antes de aplicar esta migration:")
            for cod, qtd in result[:10]:
                print(f"  - cod_produto={cod}: {qtd} versoes ativas")
            sys.exit(1)

        # 2. Verificar se index ja existe (idempotencia)
        existe = db.session.execute(db.text("""
            SELECT 1 FROM pg_indexes
            WHERE tablename = 'custo_considerado'
              AND indexname = 'uq_custo_considerado_atual_unico'
        """)).first()

        if existe:
            print("OK index uq_custo_considerado_atual_unico ja existe.")
            return

        # 3. Aplicar
        db.session.execute(db.text("""
            CREATE UNIQUE INDEX uq_custo_considerado_atual_unico
              ON custo_considerado(cod_produto)
              WHERE custo_atual = TRUE
        """))
        db.session.commit()
        print("OK index uq_custo_considerado_atual_unico criado.")


if __name__ == '__main__':
    run()
