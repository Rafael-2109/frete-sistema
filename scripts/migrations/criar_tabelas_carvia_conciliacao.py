"""
Migration: Criar tabelas carvia_extrato_linhas e carvia_conciliacoes
=====================================================================

Conciliacao bancaria CarVia — cruzar extrato OFX com documentos financeiros.

Uso:
    source .venv/bin/activate
    python scripts/migrations/criar_tabelas_carvia_conciliacao.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db


def verificar_tabela_existe(tabela):
    result = db.session.execute(
        db.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
            "WHERE table_name = :tabela)"
        ),
        {'tabela': tabela},
    )
    return result.scalar()


def criar_tabelas():
    app = create_app()
    with app.app_context():
        print("=" * 60)
        print("Migration: Criar tabelas carvia_conciliacao")
        print("=" * 60)

        # --- carvia_extrato_linhas ---
        if verificar_tabela_existe('carvia_extrato_linhas'):
            print("[SKIP] carvia_extrato_linhas ja existe")
        else:
            db.session.execute(db.text("""
                CREATE TABLE carvia_extrato_linhas (
                    id SERIAL PRIMARY KEY,
                    fitid VARCHAR(100) NOT NULL,
                    data DATE NOT NULL,
                    valor NUMERIC(15, 2) NOT NULL,
                    tipo VARCHAR(10) NOT NULL,
                    descricao VARCHAR(500),
                    memo VARCHAR(500),
                    checknum VARCHAR(50),
                    refnum VARCHAR(50),
                    trntype VARCHAR(20),
                    status_conciliacao VARCHAR(20) NOT NULL DEFAULT 'PENDENTE',
                    total_conciliado NUMERIC(15, 2) NOT NULL DEFAULT 0,
                    arquivo_ofx VARCHAR(255) NOT NULL,
                    conta_bancaria VARCHAR(50),
                    criado_por VARCHAR(100) NOT NULL,
                    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT uq_carvia_extrato_fitid UNIQUE (fitid)
                )
            """))
            db.session.execute(db.text(
                "CREATE INDEX ix_carvia_extrato_data ON carvia_extrato_linhas (data)"
            ))
            db.session.execute(db.text(
                "CREATE INDEX ix_carvia_extrato_status ON carvia_extrato_linhas (status_conciliacao)"
            ))
            db.session.execute(db.text(
                "CREATE INDEX ix_carvia_extrato_arquivo ON carvia_extrato_linhas (arquivo_ofx)"
            ))
            print("[OK] carvia_extrato_linhas criada com 3 indices")

        # --- carvia_conciliacoes ---
        if verificar_tabela_existe('carvia_conciliacoes'):
            print("[SKIP] carvia_conciliacoes ja existe")
        else:
            db.session.execute(db.text("""
                CREATE TABLE carvia_conciliacoes (
                    id SERIAL PRIMARY KEY,
                    extrato_linha_id INTEGER NOT NULL
                        REFERENCES carvia_extrato_linhas(id) ON DELETE CASCADE,
                    tipo_documento VARCHAR(30) NOT NULL,
                    documento_id INTEGER NOT NULL,
                    valor_alocado NUMERIC(15, 2) NOT NULL,
                    conciliado_por VARCHAR(100) NOT NULL,
                    conciliado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT uq_carvia_conc_linha_doc
                        UNIQUE (extrato_linha_id, tipo_documento, documento_id),
                    CONSTRAINT ck_carvia_conc_valor CHECK (valor_alocado > 0)
                )
            """))
            db.session.execute(db.text(
                "CREATE INDEX ix_carvia_conc_linha ON carvia_conciliacoes (extrato_linha_id)"
            ))
            db.session.execute(db.text(
                "CREATE INDEX ix_carvia_conc_doc ON carvia_conciliacoes (tipo_documento, documento_id)"
            ))
            print("[OK] carvia_conciliacoes criada com 2 indices")

        db.session.commit()
        print("\n[DONE] Migration concluida com sucesso")

        # Verificacao
        for tabela in ('carvia_extrato_linhas', 'carvia_conciliacoes'):
            existe = verificar_tabela_existe(tabela)
            print(f"  {tabela}: {'OK' if existe else 'FALHOU'}")


if __name__ == '__main__':
    criar_tabelas()
