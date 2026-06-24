"""Resolvedor canonico do vinculo NF<->Embarque (CarVia) — fonte UNICA p/ todos os readers.

Mora em app/utils (zona neutra, R1-safe): importavel pelo CarVia sem violar o isolamento do
modulo (CarVia nao importa app/embarques direto). Centraliza a UNIAO das 2 vias que antes era
replicada em `nf_routes.py` (badge de `listar_nfs`) e DIVERGIA em `detalhe_nf` (que usava so a
via do CarviaFrete — NF em embarque pre-portaria, sem frete ainda, sumia do detalhe).

REGRA UNICA (a MESMA do filtro "emb_pendente" em listar_nfs):
  Uma NF esta "em embarque" se:
    (a) tem EmbarqueItem com separacao_lote_id LIKE 'CARVIA-%' e status='ativo',
        casado por nota_fiscal == CarviaNf.numero_nf; OU
    (b) tem operacao -> CarviaFrete (status != CANCELADO, embarque_id not null) -> Embarque,
        SO quando a NF NAO tem nenhum EmbarqueItem CARVIA-% (qualquer status).
        (EI cancelado sem ativo = a NF saiu daquele embarque — decisao 2026-06-23.)
  Com mais de um embarque para a NF, prioriza o que JA saiu da portaria
  (Embarque.data_embarque preenchida).
"""
from collections import defaultdict

from app import db


def resolve_embarque_por_nf_ids(nf_ids):
    """Resolve o embarque de cada NF (CarVia) pelas 2 vias canonicas.

    Args:
        nf_ids: iteravel de CarviaNf.id.

    Returns:
        dict {nf_id: {'id': embarque_id, 'numero': embarque_numero,
                      'data_embarque': datetime|None}}.
        NFs sem embarque ficam AUSENTES do dict. Retorna {} se nf_ids vazio/None.
    """
    if not nf_ids:
        return {}

    from app.carvia.models import CarviaNf, CarviaOperacaoNf, CarviaFrete
    from app.embarques.models import Embarque, EmbarqueItem

    nf_ids = list(nf_ids)

    # id <-> numero_nf (numero NAO e unico — R1: reemissao gera 2 ids c/ mesmo numero)
    rows_nf = db.session.query(CarviaNf.id, CarviaNf.numero_nf).filter(
        CarviaNf.id.in_(nf_ids)
    ).all()
    nf_id_to_numero = {i: n for i, n in rows_nf}
    numero_to_nf_ids = defaultdict(list)
    for i, n in rows_nf:
        if n:
            numero_to_nf_ids[n].append(i)

    resultado = {}

    def _registrar(nf_id_key, emb_id, emb_num, emb_data):
        # registra se ainda nao ha, OU se este saiu da portaria e o anterior nao
        atual = resultado.get(nf_id_key)
        if atual is None or (emb_data is not None and atual.get('data_embarque') is None):
            resultado[nf_id_key] = {
                'id': emb_id, 'numero': emb_num, 'data_embarque': emb_data,
            }

    # (a) via embarque_itens CARVIA ativos (match por numero_nf)
    if numero_to_nf_ids:
        rows_ei = db.session.query(
            EmbarqueItem.nota_fiscal, Embarque.id, Embarque.numero, Embarque.data_embarque,
        ).join(
            Embarque, Embarque.id == EmbarqueItem.embarque_id
        ).filter(
            EmbarqueItem.nota_fiscal.in_(list(numero_to_nf_ids.keys())),
            EmbarqueItem.separacao_lote_id.like('CARVIA-%'),
            EmbarqueItem.status == 'ativo',
        ).all()
        for nota, emb_id, emb_num, emb_data in rows_ei:
            for nf_id_e in numero_to_nf_ids.get(nota, []):
                _registrar(nf_id_e, emb_id, emb_num, emb_data)

    # NFs que TEM algum EmbarqueItem CARVIA (qualquer status): via (b) NAO vale p/ elas.
    notas_com_ei = set()
    if numero_to_nf_ids:
        rows_tem_ei = db.session.query(EmbarqueItem.nota_fiscal).filter(
            EmbarqueItem.nota_fiscal.in_(list(numero_to_nf_ids.keys())),
            EmbarqueItem.separacao_lote_id.like('CARVIA-%'),
        ).distinct().all()
        notas_com_ei = {r[0] for r in rows_tem_ei}

    # (b) via operacao -> CarviaFrete -> Embarque (so NF SEM EI CARVIA)
    rows_emb = db.session.query(
        CarviaOperacaoNf.nf_id, Embarque.id, Embarque.numero, Embarque.data_embarque,
    ).join(
        CarviaFrete, CarviaFrete.operacao_id == CarviaOperacaoNf.operacao_id
    ).join(
        Embarque, Embarque.id == CarviaFrete.embarque_id
    ).filter(
        CarviaOperacaoNf.nf_id.in_(nf_ids),
        CarviaFrete.status != 'CANCELADO',
        CarviaFrete.embarque_id.isnot(None),
    ).all()
    for nf_id_e, emb_id, emb_num, emb_data in rows_emb:
        if nf_id_to_numero.get(nf_id_e) in notas_com_ei:
            continue
        _registrar(nf_id_e, emb_id, emb_num, emb_data)

    return resultado


# ---------------------------------------------------------------------------
# Predicado SQL "NF saiu da portaria" — usado pelo filtro emb_pendente da listagem.
# E o SUBCONJUNTO da regra acima restrito a Embarque.data_embarque IS NOT NULL
# (so quem JA saiu fisicamente do CD). Vive aqui para que filtro e badge sejam a
# MESMA regra (so muda a condicao data_embarque). Sao subqueries (nao .all()) p/
# o caller aplicar `.notin_(...)` sobre a query externa de CarviaNf, pre-paginacao.
# ---------------------------------------------------------------------------

def notas_saidas_da_portaria_subquery():
    """Subquery de `EmbarqueItem.nota_fiscal` que JA saiu via EmbarqueItem CARVIA ativo
    (via a, restrita a Embarque.data_embarque IS NOT NULL)."""
    from app.embarques.models import Embarque, EmbarqueItem

    return db.session.query(EmbarqueItem.nota_fiscal).join(
        Embarque, Embarque.id == EmbarqueItem.embarque_id
    ).filter(
        EmbarqueItem.separacao_lote_id.like('CARVIA-%'),
        EmbarqueItem.status == 'ativo',
        EmbarqueItem.nota_fiscal.isnot(None),
        Embarque.data_embarque.isnot(None),
    )


def nf_ids_saidos_da_portaria_subquery():
    """Subquery de `CarviaOperacaoNf.nf_id` que JA saiu via operacao->CarviaFrete->Embarque
    (via b, restrita a Embarque.data_embarque IS NOT NULL), SO p/ NF sem EmbarqueItem CARVIA
    (EXISTS correlacionado com alias — mesma exclusao do badge)."""
    from app.carvia.models import CarviaNf, CarviaOperacaoNf, CarviaFrete
    from app.embarques.models import Embarque, EmbarqueItem

    CarviaNfFrete = db.aliased(CarviaNf)
    return db.session.query(CarviaOperacaoNf.nf_id).join(
        CarviaFrete, CarviaFrete.operacao_id == CarviaOperacaoNf.operacao_id
    ).join(
        Embarque, Embarque.id == CarviaFrete.embarque_id
    ).join(
        CarviaNfFrete, CarviaNfFrete.id == CarviaOperacaoNf.nf_id
    ).filter(
        CarviaFrete.status != 'CANCELADO',
        Embarque.data_embarque.isnot(None),
        ~db.session.query(EmbarqueItem.id).filter(
            EmbarqueItem.nota_fiscal == CarviaNfFrete.numero_nf,
            EmbarqueItem.separacao_lote_id.like('CARVIA-%'),
        ).exists(),
    )
