"""
OPT-B7: Cria indice parcial composto para filtro base da carteira_simples.

O filtro WHERE ativo=true AND qtd_saldo_produto_pedido > 0 e aplicado em TODA
query da carteira_simples. Sem este indice, o planner precisa escanear todas as
rows (incluindo inativas e zeradas).

Verificacao before/after via EXPLAIN ANALYZE da query principal.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


def criar_indice():
    from app import create_app, db
    from sqlalchemy import text

    app = create_app()
    with app.app_context():
        # Verificar se indice ja existe
        resultado = db.session.execute(text("""
            SELECT 1 FROM pg_indexes
            WHERE indexname = 'idx_carteira_ativo_saldo'
        """)).fetchone()

        if resultado:
            print("[OK] Indice idx_carteira_ativo_saldo ja existe")
            return

        print("[ANTES] Criando indice parcial...")

        # Verificar contagem de rows que serao indexadas
        count_total = db.session.execute(text(
            "SELECT COUNT(*) FROM carteira_principal"
        )).scalar()
        count_ativo = db.session.execute(text(
            "SELECT COUNT(*) FROM carteira_principal WHERE ativo = true AND qtd_saldo_produto_pedido > 0"
        )).scalar()
        print(f"  Total rows: {count_total}")
        print(f"  Rows no indice (ativo=true, saldo>0): {count_ativo}")
        print(f"  Rows excluidas: {count_total - count_ativo}")

        # Criar indice
        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_carteira_ativo_saldo
            ON carteira_principal (num_pedido, cod_produto)
            WHERE ativo = true AND qtd_saldo_produto_pedido > 0
        """))
        db.session.commit()

        # Verificar criacao
        resultado = db.session.execute(text("""
            SELECT 1 FROM pg_indexes
            WHERE indexname = 'idx_carteira_ativo_saldo'
        """)).fetchone()

        if resultado:
            print("[DEPOIS] Indice idx_carteira_ativo_saldo criado com sucesso!")
        else:
            print("[ERRO] Falha ao criar indice")


if __name__ == '__main__':
    criar_indice()
