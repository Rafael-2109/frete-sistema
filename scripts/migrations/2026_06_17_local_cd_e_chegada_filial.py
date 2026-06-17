"""Migration: flag local_cd + chegada_filial (stream FUNDACAO — redesign CarVia).

Adiciona `local_cd` (VARCHAR NOT NULL default 'VICTORIO_MARCHEZINE') em
separacao, embarque_itens, controle_portaria, carvia_nfs, entregas_monitoradas e
`chegada_filial` (bool) + `chegada_filial_em` (timestamp) em entregas_monitoradas.

A logica SQL vive em `2026_06_17_local_cd_e_chegada_filial.sql` (fonte de verdade).
Este wrapper executa o .sql com verificacao before/after. Idempotente.

Uso:
    python scripts/migrations/2026_06_17_local_cd_e_chegada_filial.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import inspect, text  # noqa: E402
from app import create_app, db  # noqa: E402

logger = logging.getLogger(__name__)

# (tabela, colunas esperadas pos-migration)
ESPERADO = {
    'separacao': ['local_cd'],
    'embarque_itens': ['local_cd'],
    'controle_portaria': ['local_cd'],
    'carvia_nfs': ['local_cd'],
    'entregas_monitoradas': ['local_cd', 'chegada_filial', 'chegada_filial_em'],
}

SQL_FILE = os.path.join(os.path.dirname(__file__), '2026_06_17_local_cd_e_chegada_filial.sql')


def _faltando(insp):
    faltam = {}
    for tabela, cols in ESPERADO.items():
        existentes = {c['name'] for c in insp.get_columns(tabela)}
        ausentes = [c for c in cols if c not in existentes]
        if ausentes:
            faltam[tabela] = ausentes
    return faltam


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        insp = inspect(db.engine)
        print('Faltando ANTES:', _faltando(insp))

        with open(SQL_FILE, encoding='utf-8') as f:
            script = f.read()
        # Executa multiplos statements numa chamada (psycopg2 simple query protocol).
        db.session.connection().exec_driver_sql(script)
        db.session.commit()

        insp = inspect(db.engine)  # re-inspeciona (cache invalidado)
        faltando = _faltando(insp)
        print('Faltando DEPOIS:', faltando)
        assert not faltando, f'Migration nao aplicou todas as colunas: {faltando}'

        # Sanidade: nenhum NULL em local_cd (backfill default cobriu o historico)
        for tabela in ESPERADO:
            nulos = db.session.execute(
                text(f"SELECT COUNT(*) FROM {tabela} WHERE local_cd IS NULL")
            ).scalar()
            assert nulos == 0, f'{tabela} tem {nulos} linhas com local_cd NULL'
        db.session.rollback()
        print('OK — colunas local_cd/chegada_filial aplicadas e backfill VM consistente.')


if __name__ == '__main__':
    main()
