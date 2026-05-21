"""
Migration: criar tabela carvia_anexos (anexos polimorficos Frete + Subcontrato)
================================================================================

Anexos comprovatorios (S3) para CarviaFrete e CarviaSubcontrato — paridade com
a Nacom (DespesaExtra.comprovante + EmailAnexado). Polimorfico via
(entidade_tipo, entidade_id).

Despesas (CarviaCustoEntrega) MANTEM sua tabela carvia_custo_entrega_anexos
intacta — sem migracao de dados (decisao 2026-05-20).

Idempotente: usa CREATE TABLE IF NOT EXISTS via metadata SQLAlchemy.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import text

from app import create_app, db


def tabela_existe(conn, tabela):
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = :tabela
        )
    """), {'tabela': tabela})
    return result.scalar()


def main():
    app = create_app()
    with app.app_context():
        # Import garante que o modelo esta registrado no metadata
        from app.carvia.models.anexos import CarviaAnexo

        tabela = CarviaAnexo.__tablename__  # 'carvia_anexos'
        conn = db.session.connection()

        print(f"\n=== Migration: criar tabela {tabela} ===\n")

        # BEFORE
        existe_antes = tabela_existe(conn, tabela)
        print(f"--- BEFORE: {tabela} {'JA EXISTE' if existe_antes else 'NAO EXISTE'} ---")

        if not existe_antes:
            # create_all so cria tabelas faltantes; checkfirst=True garante
            # idempotencia sem afetar outras tabelas.
            CarviaAnexo.__table__.create(bind=db.session.get_bind(), checkfirst=True)
            db.session.commit()
            print(f"  + Tabela {tabela} criada (com indices)")
        else:
            print(f"  ~ Tabela {tabela} ja existe (skip)")

        # AFTER (nova conexao apos commit)
        conn2 = db.session.connection()
        existe_depois = tabela_existe(conn2, tabela)
        print(f"\n--- AFTER: {tabela} {'OK' if existe_depois else 'FALHA'} ---")

        print("\n=== Migration concluida ===\n")


if __name__ == '__main__':
    main()
