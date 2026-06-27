"""Migration HORA 55: Recebimento por filial sem NF (NF provisória).

Adiciona hora_nf_entrada.tipo {PROVISORIA,REAL} e cria hora_recebimento_esperado
(snapshot congelado dos pedidos pendentes da filial usado como gabarito).

Idempotente — pode rodar 2x (IF NOT EXISTS).

Nota: planejado como hora_54 no spec, renumerado para 55 porque
      hora_54_aprovacoes_perm já existia no branch main.

Uso:
    python scripts/migrations/hora_55_recebimento_sem_nf.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import inspect, text  # noqa: E402

from app import create_app, db  # noqa: E402

logger = logging.getLogger(__name__)

SQL_DDL = [
    "ALTER TABLE hora_nf_entrada ADD COLUMN IF NOT EXISTS tipo VARCHAR(20) NOT NULL DEFAULT 'REAL'",
    """
    CREATE TABLE IF NOT EXISTS hora_recebimento_esperado (
        id                            SERIAL PRIMARY KEY,
        recebimento_id                INTEGER NOT NULL REFERENCES hora_recebimento (id),
        pedido_id                     INTEGER REFERENCES hora_pedido (id),
        pedido_item_id                INTEGER REFERENCES hora_pedido_item (id),
        modelo_id                     INTEGER REFERENCES hora_modelo (id),
        cor                           VARCHAR(50),
        chassi_esperado               VARCHAR(30),
        preco_esperado                NUMERIC(15, 2),
        consumido_por_conferencia_id  INTEGER REFERENCES hora_recebimento_conferencia (id),
        criado_em                     TIMESTAMP NOT NULL
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_hora_rec_esperado_rec ON hora_recebimento_esperado (recebimento_id)",
    "CREATE INDEX IF NOT EXISTS ix_hora_rec_esperado_rec_modelo ON hora_recebimento_esperado (recebimento_id, modelo_id)",
    "CREATE INDEX IF NOT EXISTS ix_hora_rec_esperado_rec_chassi ON hora_recebimento_esperado (recebimento_id, chassi_esperado)",
]


def _colunas(tabela: str) -> list:
    return [c['name'] for c in inspect(db.engine).get_columns(tabela)]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        insp = inspect(db.engine)
        print('Estado antes:')
        print(f"  hora_nf_entrada.tipo existe? {'tipo' in _colunas('hora_nf_entrada')}")
        print(f"  hora_recebimento_esperado existe? {'hora_recebimento_esperado' in insp.get_table_names()}")

        with db.engine.begin() as conn:
            for sql in SQL_DDL:
                conn.execute(text(sql))

        insp = inspect(db.engine)
        ok_col = 'tipo' in _colunas('hora_nf_entrada')
        ok_tab = 'hora_recebimento_esperado' in insp.get_table_names()
        print('\nEstado depois:')
        print(f'  hora_nf_entrada.tipo existe? {ok_col}')
        print(f'  hora_recebimento_esperado existe? {ok_tab}')
        if not (ok_col and ok_tab):
            print('\nERRO: migration HORA 55 incompleta.')
            sys.exit(1)
        print('\nMigration HORA 55 concluida com sucesso.')


if __name__ == '__main__':
    main()
