"""Migration HORA 49: Comissao de vendas (roadmap #28, Fatia 1 — cadastro).

Cria:
  1. hora_comissao_config (singleton id=1: comissao_base_moto).
  2. hora_comissao_faixa_desconto (faixas de desconto R$ -> reducao R$).
  3. hora_peca.valor_comissao (comissao por unidade da peca).
  4. hora_modelo.desconto_maximo (teto de desconto R$ por modelo; NULL = sem teto).

Idempotente — pode rodar 2x (IF NOT EXISTS + INSERT condicional do singleton).

Uso:
    python scripts/migrations/hora_49_comissao.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import inspect, text  # noqa: E402

from app import create_app, db  # noqa: E402

logger = logging.getLogger(__name__)

SQL_DDL = [
    """
    CREATE TABLE IF NOT EXISTS hora_comissao_config (
        id                  SERIAL PRIMARY KEY,
        comissao_base_moto  NUMERIC(15, 2) NOT NULL DEFAULT 0,
        atualizado_em       TIMESTAMP NOT NULL,
        atualizado_por      VARCHAR(100)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS hora_comissao_faixa_desconto (
        id                  SERIAL PRIMARY KEY,
        desconto_min        NUMERIC(15, 2) NOT NULL DEFAULT 0,
        desconto_max        NUMERIC(15, 2),
        reducao_comissao    NUMERIC(15, 2) NOT NULL DEFAULT 0,
        ativo               BOOLEAN NOT NULL DEFAULT TRUE,
        criado_em           TIMESTAMP NOT NULL
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_hora_comissao_faixa_ativo "
    "ON hora_comissao_faixa_desconto (ativo);",
    "ALTER TABLE hora_peca "
    "ADD COLUMN IF NOT EXISTS valor_comissao NUMERIC(15, 2) NOT NULL DEFAULT 0;",
    "ALTER TABLE hora_modelo "
    "ADD COLUMN IF NOT EXISTS desconto_maximo NUMERIC(15, 2);",
]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        tabelas = set(inspector.get_table_names())
        print('Estado antes:')
        print(f'  hora_comissao_config? {"hora_comissao_config" in tabelas}')
        print(f'  hora_comissao_faixa_desconto? {"hora_comissao_faixa_desconto" in tabelas}')

        with db.engine.begin() as conn:
            for sql in SQL_DDL:
                conn.execute(text(sql))
            # Singleton id=1 (idempotente).
            from app.utils.timezone import agora_utc_naive
            conn.execute(
                text(
                    "INSERT INTO hora_comissao_config (id, comissao_base_moto, atualizado_em) "
                    "VALUES (1, 0, :ts) ON CONFLICT (id) DO NOTHING"
                ),
                {'ts': agora_utc_naive()},
            )

        inspector = inspect(db.engine)
        tabelas = set(inspector.get_table_names())
        cols_peca = {c['name'] for c in inspector.get_columns('hora_peca')}
        cols_modelo = {c['name'] for c in inspector.get_columns('hora_modelo')}
        print('\nEstado depois:')
        print(f'  hora_comissao_config? {"hora_comissao_config" in tabelas}')
        print(f'  hora_comissao_faixa_desconto? {"hora_comissao_faixa_desconto" in tabelas}')
        print(f'  hora_peca.valor_comissao? {"valor_comissao" in cols_peca}')
        print(f'  hora_modelo.desconto_maximo? {"desconto_maximo" in cols_modelo}')

        ok = (
            'hora_comissao_config' in tabelas
            and 'hora_comissao_faixa_desconto' in tabelas
            and 'valor_comissao' in cols_peca
            and 'desconto_maximo' in cols_modelo
        )
        if not ok:
            print('\nERRO: migration incompleta.')
            sys.exit(1)
        print('\nMigration HORA 49 concluida com sucesso.')


if __name__ == '__main__':
    main()
