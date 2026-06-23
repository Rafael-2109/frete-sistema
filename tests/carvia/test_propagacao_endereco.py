"""Propagação de cidade/UF do endereço destino CarVia para registros em aberto.

Fase A do plano docs/superpowers/plans/2026-06-23-carvia-propagacao-endereco-cce.md.
"""
from app import db as _db
from app.utils.propagacao_endereco_carvia import propagar_cidade_uf_carvia


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #

def _embarque_item_carvia(numero_nf, cidade, uf, lote='CARVIA-NF-1', status='ativo'):
    from app.embarques.models import Embarque, EmbarqueItem
    from app.utils.timezone import agora_utc_naive
    emb = Embarque(numero=None, status=status, criado_em=agora_utc_naive())
    _db.session.add(emb)
    _db.session.flush()
    item = EmbarqueItem(
        embarque_id=emb.id, separacao_lote_id=lote, nota_fiscal=numero_nf,
        cliente='C', pedido='P', cidade_destino=cidade, uf_destino=uf, status=status,
    )
    _db.session.add(item)
    _db.session.flush()
    return item


def _entrega_carvia(numero_nf, cidade, uf, entregue=False):
    from app.monitoramento.models import EntregaMonitorada
    e = EntregaMonitorada(numero_nf=numero_nf, cliente='C', municipio=cidade, uf=uf,
                          origem='CARVIA', entregue=entregue)
    _db.session.add(e)
    _db.session.flush()
    return e


# --------------------------------------------------------------------------- #
# A1 — helper R1-safe                                                          #
# --------------------------------------------------------------------------- #

def test_propaga_cidade_uf_para_embarque_item_carvia_aberto(db):
    item = _embarque_item_carvia('555', 'Cidade Velha', 'RJ')
    res = propagar_cidade_uf_carvia(['555'], [], 'Cidade Nova', 'SP')
    db.session.refresh(item)
    assert item.cidade_destino == 'Cidade Nova'
    assert item.uf_destino == 'SP'
    assert res['embarque_itens'] == 1


def test_nao_toca_entrega_ja_entregue(db):
    e = _entrega_carvia('556', 'Cidade Velha', 'RJ', entregue=True)
    res = propagar_cidade_uf_carvia(['556'], [], 'Cidade Nova', 'SP')
    db.session.refresh(e)
    assert e.municipio == 'Cidade Velha'  # intacta
    assert res['entregas'] == 0
