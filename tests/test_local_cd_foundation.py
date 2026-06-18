"""Testes da FUNDACAO da flag local_cd + chegada_filial (redesign CarVia, stream 1).

Cobre:
- constantes/helpers de app/utils/local_cd.py (puros, sem DB);
- presenca das colunas local_cd nas 5 tabelas + chegada_filial em entregas_monitoradas;
- a VIEW pedidos expoe local_cd (Nacom = VM; CarVia = NULL ate a Coleta);
- backfill: zero NULL em local_cd nas tabelas base.
"""
import pytest
from sqlalchemy import text

from app.utils.local_cd import (
    LOCAL_CD_VICTORIO_MARCHEZINE,
    LOCAL_CD_TENENTE_MARQUES,
    LOCAL_CD_DEFAULT,
    LOCAL_CD_LABELS,
    label_local_cd,
    normalizar_local_cd,
)

TABELAS_LOCAL_CD = [
    'separacao', 'embarque_itens', 'controle_portaria',
    'carvia_nfs', 'entregas_monitoradas',
]


# --------------------------------------------------------------------------- #
# 1. Constantes / helpers (puros)
# --------------------------------------------------------------------------- #
def test_default_e_victorio():
    assert LOCAL_CD_DEFAULT == LOCAL_CD_VICTORIO_MARCHEZINE
    assert LOCAL_CD_VICTORIO_MARCHEZINE in LOCAL_CD_LABELS
    assert LOCAL_CD_TENENTE_MARQUES in LOCAL_CD_LABELS


@pytest.mark.parametrize('entrada,esperado', [
    ('VICTORIO_MARCHEZINE', LOCAL_CD_VICTORIO_MARCHEZINE),
    ('TENENTE_MARQUES', LOCAL_CD_TENENTE_MARQUES),
    ('vm', LOCAL_CD_VICTORIO_MARCHEZINE),
    ('TM', LOCAL_CD_TENENTE_MARQUES),
    ('Victorio Marchezine', LOCAL_CD_VICTORIO_MARCHEZINE),
    ('Tenente Marques', LOCAL_CD_TENENTE_MARQUES),
    ('victório marchezine', LOCAL_CD_VICTORIO_MARCHEZINE),
    ('CD Tenente Marques', LOCAL_CD_TENENTE_MARQUES),
    ('', None),
    (None, None),
    ('qualquer coisa', None),
])
def test_normalizar(entrada, esperado):
    assert normalizar_local_cd(entrada) == esperado


def test_label():
    assert label_local_cd(LOCAL_CD_TENENTE_MARQUES) == 'Tenente Marques'
    assert label_local_cd(LOCAL_CD_VICTORIO_MARCHEZINE, curto=True) == 'V. Marchezine'
    assert label_local_cd('inexistente') == ''


# --------------------------------------------------------------------------- #
# 2. Schema: colunas existem (pg_attribute cobre tabela, view e matview)
# --------------------------------------------------------------------------- #
def _tem_coluna(db, relname, colname):
    return db.session.execute(text(
        "SELECT COUNT(*) FROM pg_attribute a JOIN pg_class c ON c.oid = a.attrelid "
        "WHERE c.relname = :t AND a.attname = :col AND a.attnum > 0 AND NOT a.attisdropped"
    ), {'t': relname, 'col': colname}).scalar()


@pytest.mark.parametrize('tabela', TABELAS_LOCAL_CD)
def test_coluna_local_cd_existe(db, tabela):
    assert _tem_coluna(db, tabela, 'local_cd') == 1, f'local_cd ausente em {tabela}'


def test_chegada_filial_existe(db):
    assert _tem_coluna(db, 'entregas_monitoradas', 'chegada_filial') == 1
    assert _tem_coluna(db, 'entregas_monitoradas', 'chegada_filial_em') == 1


def test_view_e_mv_expoem_local_cd(db):
    assert _tem_coluna(db, 'pedidos', 'local_cd') == 1
    assert _tem_coluna(db, 'mv_pedidos', 'local_cd') == 1


# --------------------------------------------------------------------------- #
# 3. Backfill: zero NULL em local_cd nas tabelas base
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize('tabela', TABELAS_LOCAL_CD)
def test_backfill_sem_nulos(db, tabela):
    nulos = db.session.execute(
        text(f"SELECT COUNT(*) FROM {tabela} WHERE local_cd IS NULL")
    ).scalar()
    assert nulos == 0, f'{tabela} tem {nulos} linhas com local_cd NULL'


# --------------------------------------------------------------------------- #
# 4. VIEW pedidos: Nacom = VM; CarVia = NULL (ate a Coleta atribuir)
# --------------------------------------------------------------------------- #
def test_view_nacom_e_carvia_default_vm(db):
    # Nacom (lote NAO 'CARVIA-%') que tenha local_cd preenchido -> tem que ser VM
    nacom_nao_vm = db.session.execute(text(
        "SELECT COUNT(*) FROM pedidos "
        "WHERE separacao_lote_id NOT LIKE 'CARVIA-%' "
        "AND local_cd IS NOT NULL AND local_cd <> 'VICTORIO_MARCHEZINE'"
    )).scalar()
    assert nacom_nao_vm == 0, 'Pedido Nacom com local_cd != VM na VIEW'

    # CarVia: VIEW v11 (4B) expoe default VICTORIO_MARCHEZINE (nao mais NULL)
    carvia_null = db.session.execute(text(
        "SELECT COUNT(*) FROM pedidos "
        "WHERE separacao_lote_id LIKE 'CARVIA-%' AND local_cd IS NULL"
    )).scalar()
    assert carvia_null == 0, 'Pedido CarVia com local_cd NULL (esperado VM default na v11)'
