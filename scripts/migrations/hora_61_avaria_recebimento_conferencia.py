"""Migration HORA 61: vinculo HoraAvaria -> conferencia de recebimento.

Adiciona hora_avaria.recebimento_conferencia_id (FK opcional, espelha
hora_peca_faltando.recebimento_conferencia_id) para vincular a avaria criada no
recebimento (regra avaria=NAO-vendavel, 2026-06-28) a conferencia que a originou.
Permite excluir_recebimento limpar a avaria do recebimento e desmarcar avaria na
reconferencia resolver so a avaria daquela conferencia (nao a avaria manual).

Idempotente — pode rodar 2x (IF NOT EXISTS).

Uso:
    python scripts/migrations/hora_61_avaria_recebimento_conferencia.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import inspect, text  # noqa: E402

from app import create_app, db  # noqa: E402

logger = logging.getLogger(__name__)

SQL_DDL = [
    "ALTER TABLE hora_avaria ADD COLUMN IF NOT EXISTS recebimento_conferencia_id "
    "INTEGER REFERENCES hora_recebimento_conferencia (id)",
    "CREATE INDEX IF NOT EXISTS ix_hora_avaria_rec_conf "
    "ON hora_avaria (recebimento_conferencia_id)",
]


def _colunas(tabela: str) -> list:
    return [c['name'] for c in inspect(db.engine).get_columns(tabela)]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        print('Estado antes:')
        print(f"  hora_avaria.recebimento_conferencia_id existe? "
              f"{'recebimento_conferencia_id' in _colunas('hora_avaria')}")

        with db.engine.begin() as conn:
            for sql in SQL_DDL:
                conn.execute(text(sql))

        ok = 'recebimento_conferencia_id' in _colunas('hora_avaria')
        print('\nEstado depois:')
        print(f'  hora_avaria.recebimento_conferencia_id existe? {ok}')
        if not ok:
            print('\nERRO: migration HORA 61 incompleta.')
            sys.exit(1)
        print('\nMigration HORA 61 concluida com sucesso.')


if __name__ == '__main__':
    main()
