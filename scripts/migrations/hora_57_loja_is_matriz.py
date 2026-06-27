"""Migration HORA 57: coluna is_matriz em hora_loja.

Marca a MATRIZ (emitente fiscal de todas as NFes — invariante CLAUDE.md secao 7)
como pseudo-loja que NAO vende. Toda NFe da HORA sai com o CNPJ da matriz, mas a
matriz nao e loja de venda. `is_matriz=True`:
  - EXCLUI a matriz das superficies de VENDA (rankings, escopos, dropdowns,
    contagens "Lojas ativas");
  - impede que o import/backfill grave loja_id=matriz numa venda (a loja real vem
    de tagplus_departamento -> hora_tagplus_departamento_map ou do SELECT manual).
A matriz permanece `ativa` (default de NF de ENTRADA e alvo do resolver de
divergencia CNPJ_DESCONHECIDO).

Identifica a matriz pelo CNPJ 62634044000120 ("HORA Comercio de Motocicletas
Eletricas LTDA"). Idempotente — ADD COLUMN IF NOT EXISTS + UPDATE guardado.

Uso:
    python scripts/migrations/hora_57_loja_is_matriz.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import inspect, text  # noqa: E402

from app import create_app, db  # noqa: E402

logger = logging.getLogger(__name__)

SQL_DDL = [
    "ALTER TABLE hora_loja ADD COLUMN IF NOT EXISTS is_matriz BOOLEAN NOT NULL DEFAULT FALSE",
]

SQL_MARCA_MATRIZ = text(
    "UPDATE hora_loja SET is_matriz = TRUE "
    "WHERE regexp_replace(cnpj, '\\D', '', 'g') = '62634044000120' "
    "AND is_matriz = FALSE"
)


def _colunas() -> list:
    return [c['name'] for c in inspect(db.engine).get_columns('hora_loja')]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        print('Estado antes:')
        print(f'  hora_loja.is_matriz existe? {"is_matriz" in _colunas()}')

        with db.engine.begin() as conn:
            for sql in SQL_DDL:
                conn.execute(text(sql))
            res = conn.execute(SQL_MARCA_MATRIZ)
            marcadas = res.rowcount

        existe = 'is_matriz' in _colunas()
        with db.engine.connect() as conn:
            total_matriz = conn.execute(
                text("SELECT count(*) FROM hora_loja WHERE is_matriz = TRUE")
            ).scalar()

        print('\nEstado depois:')
        print(f'  hora_loja.is_matriz existe? {existe}')
        print(f'  lojas marcadas como matriz nesta execucao: {marcadas}')
        print(f'  total de lojas com is_matriz=TRUE: {total_matriz}')

        if not existe:
            print('\nERRO: coluna nao foi criada.')
            sys.exit(1)
        if total_matriz == 0:
            print('\nAVISO: nenhuma loja marcada como matriz (CNPJ 62634044000120 '
                  'nao encontrado). Conferir cadastro de hora_loja.')

        print('\nMigration HORA 57 concluida com sucesso.')


if __name__ == '__main__':
    main()
