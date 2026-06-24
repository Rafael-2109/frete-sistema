"""Valida o filtro de embarque ("emb_pendente") da listagem de NF Venda CarVia.

A rota `listar_nfs` exclui as NFs que JA sairam da portaria via 2 subqueries SQL
(pre-paginacao). Essas subqueries agora vivem no resolvedor CANONICO
(`app/utils/resolver_embarque_nf`), MESMA fonte do badge/detalhe — entao filtro e badge
nao podem mais divergir. Este teste pina o comportamento das 2 subqueries:
  - NF que saiu via EmbarqueItem CARVIA ativo (embarque com data_embarque) entra na
    subquery de notas-saidas; NF em embarque SEM data_embarque NAO entra.
  - NF sem EI mas com frete->embarque (com data_embarque) entra na subquery de nf_ids.
"""
from tests.carvia._embarque_builders import (
    mk_transportadora, mk_embarque, mk_nf, mk_embarque_item, mk_operacao_frete,
)
from app.utils.timezone import agora_utc_naive
import uuid


def test_notas_saidas_da_portaria_via_ei(db):
    from app.utils.resolver_embarque_nf import notas_saidas_da_portaria_subquery
    transp = mk_transportadora(db)
    emb_saiu = mk_embarque(db, transp, data_embarque=agora_utc_naive().date())
    emb_dentro = mk_embarque(db, transp, data_embarque=None)
    nf_saiu = mk_nf(db, 'NF-S-' + uuid.uuid4().hex[:6])
    nf_dentro = mk_nf(db, 'NF-D-' + uuid.uuid4().hex[:6])
    mk_embarque_item(db, emb_saiu, nf_saiu.numero_nf, status='ativo')
    mk_embarque_item(db, emb_dentro, nf_dentro.numero_nf, status='ativo')

    notas = {r[0] for r in notas_saidas_da_portaria_subquery().all()}

    assert nf_saiu.numero_nf in notas          # saiu (embarque com data)
    assert nf_dentro.numero_nf not in notas    # em embarque, mas sem saida


def test_nf_ids_saidos_da_portaria_via_frete(db):
    from app.utils.resolver_embarque_nf import nf_ids_saidos_da_portaria_subquery
    transp = mk_transportadora(db)
    emb = mk_embarque(db, transp, data_embarque=agora_utc_naive().date())
    nf = mk_nf(db, 'NF-F-' + uuid.uuid4().hex[:6])
    mk_operacao_frete(db, transp, emb, nf)  # frete->embarque, SEM EmbarqueItem

    ids = {r[0] for r in nf_ids_saidos_da_portaria_subquery().all()}

    assert nf.id in ids


def test_nf_com_ei_nao_entra_na_via_frete(db):
    """NF com EmbarqueItem CARVIA (mesmo cancelado) NAO conta como saiu via frete."""
    from app.utils.resolver_embarque_nf import nf_ids_saidos_da_portaria_subquery
    transp = mk_transportadora(db)
    emb = mk_embarque(db, transp, data_embarque=agora_utc_naive().date())
    nf = mk_nf(db, 'NF-G-' + uuid.uuid4().hex[:6])
    mk_embarque_item(db, emb, nf.numero_nf, status='cancelado')
    mk_operacao_frete(db, transp, emb, nf)

    ids = {r[0] for r in nf_ids_saidos_da_portaria_subquery().all()}

    assert nf.id not in ids


def test_filtro_completo_executa(db):
    """O filtro completo (como na rota) monta e executa o SQL (alias/EXISTS correlacionado)."""
    from app import db as _db
    from app.carvia.models import CarviaNf
    from app.utils.resolver_embarque_nf import (
        notas_saidas_da_portaria_subquery, nf_ids_saidos_da_portaria_subquery,
    )
    q = _db.session.query(CarviaNf).filter(
        CarviaNf.numero_nf.notin_(notas_saidas_da_portaria_subquery()),
        CarviaNf.id.notin_(nf_ids_saidos_da_portaria_subquery()),
    )
    assert isinstance(q.count(), int)
