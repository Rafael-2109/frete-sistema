"""Fase 2 — herança de local_cd na CRIACAO do EmbarqueItem CarVia (factory).

Causa-raiz do bug "pedido CarVia TM gravava VM": os criadores em cotacao/routes.py
instanciavam EmbarqueItem sem local_cd -> caia no default VM da coluna. A propagacao
pos-evento (propagar_local_cd_carvia) NAO fechava a janela: casa por nota_fiscal, e o
provisorio nasce SEM NF. O factory `criar_embarque_item_carvia` resolve o local_cd da
FONTE CANONICA (NF ATIVA -> senao cotacao -> senao DEFAULT) na PROPRIA criacao.
"""
import uuid

from app.utils.local_cd import (
    LOCAL_CD_TENENTE_MARQUES, LOCAL_CD_VICTORIO_MARCHEZINE, LOCAL_CD_DEFAULT,
)
from tests.carvia._embarque_builders import mk_nf, mk_cotacao


def test_resolver_local_cd_da_nf(db):
    from app.carvia.services.documentos.embarque_carvia_service import (
        resolver_local_cd_carvia,
    )
    nf = mk_nf(db, 'NF-LC-' + uuid.uuid4().hex[:6], local_cd=LOCAL_CD_TENENTE_MARQUES)

    assert resolver_local_cd_carvia(nota_fiscal=nf.numero_nf) == LOCAL_CD_TENENTE_MARQUES


def test_resolver_local_cd_da_cotacao(db):
    from app.carvia.services.documentos.embarque_carvia_service import (
        resolver_local_cd_carvia,
    )
    cot = mk_cotacao(db, local_cd=LOCAL_CD_TENENTE_MARQUES)

    assert resolver_local_cd_carvia(carvia_cotacao_id=cot.id) == LOCAL_CD_TENENTE_MARQUES


def test_resolver_nf_tem_prioridade_sobre_cotacao(db):
    from app.carvia.services.documentos.embarque_carvia_service import (
        resolver_local_cd_carvia,
    )
    nf = mk_nf(db, 'NF-P-' + uuid.uuid4().hex[:6], local_cd=LOCAL_CD_TENENTE_MARQUES)
    cot = mk_cotacao(db, local_cd=LOCAL_CD_VICTORIO_MARCHEZINE)

    assert resolver_local_cd_carvia(
        nota_fiscal=nf.numero_nf, carvia_cotacao_id=cot.id
    ) == LOCAL_CD_TENENTE_MARQUES


def test_resolver_default_sem_fonte(db):
    from app.carvia.services.documentos.embarque_carvia_service import (
        resolver_local_cd_carvia,
    )
    # sem NF e cotacao inexistente -> DEFAULT (VM)
    assert resolver_local_cd_carvia(nota_fiscal=None, carvia_cotacao_id=999_999_999) \
        == LOCAL_CD_DEFAULT


def test_factory_seta_local_cd_herdado_da_cotacao(db):
    from app.carvia.services.documentos.embarque_carvia_service import (
        criar_embarque_item_carvia,
    )
    cot = mk_cotacao(db, local_cd=LOCAL_CD_TENENTE_MARQUES)
    item = criar_embarque_item_carvia(
        embarque_id=1, separacao_lote_id=f'CARVIA-PED-{uuid.uuid4().hex[:6]}',
        cnpj_cliente='1', cliente='C', pedido='P', nota_fiscal=None,
        peso=1, valor=1, provisorio=True, carvia_cotacao_id=cot.id,
    )

    assert item.local_cd == LOCAL_CD_TENENTE_MARQUES


def test_factory_respeita_local_cd_explicito(db):
    from app.carvia.services.documentos.embarque_carvia_service import (
        criar_embarque_item_carvia,
    )
    cot = mk_cotacao(db, local_cd=LOCAL_CD_VICTORIO_MARCHEZINE)
    item = criar_embarque_item_carvia(
        embarque_id=1, separacao_lote_id=f'CARVIA-PED-{uuid.uuid4().hex[:6]}',
        cnpj_cliente='1', cliente='C', pedido='P', nota_fiscal=None,
        peso=1, valor=1, provisorio=True, carvia_cotacao_id=cot.id,
        local_cd=LOCAL_CD_TENENTE_MARQUES,
    )

    assert item.local_cd == LOCAL_CD_TENENTE_MARQUES
