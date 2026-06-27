"""CORTESIA nas informacoes complementares (inf_contribuinte) da NF-e.

Brinde da venda deve aparecer no FINAL do inf_contribuinte como
"CORTESIA: <peca_1>, <peca_2>...". Sem brinde, nenhuma linha CORTESIA.
"""
from decimal import Decimal

from app import db as _db
from app.hora.models import HoraVenda
from app.hora.services import venda_service
from app.hora.services.tagplus.payload_builder import PayloadBuilder
from app.utils.timezone import agora_utc_naive


def _venda(loja):
    v = HoraVenda(
        loja_id=loja.id, cpf_cliente='12345678909', nome_cliente='Cliente Teste',
        valor_total=Decimal('1000'), status='COTACAO',
        data_venda=agora_utc_naive().date(), origem_criacao='MANUAL',
    )
    _db.session.add(v)
    _db.session.flush()
    return v


def _inf(venda):
    # _montar_inf_contribuinte usa apenas venda/loja_label — instanciamos sem
    # __init__ para nao exigir HoraTagPlusConta/ApiClient.
    pb = PayloadBuilder.__new__(PayloadBuilder)
    return pb._montar_inf_contribuinte(venda, 'Loja Teste')


def test_inf_contribuinte_inclui_cortesia(db, loja_factory, peca_factory):
    v = _venda(loja_factory())
    p = peca_factory(descricao='CAPACETE PRETO')
    p.preco_venda_padrao = Decimal('50')
    _db.session.flush()
    venda_service.adicionar_brinde(v.id, p.id, qtd=1, usuario='t')
    _db.session.refresh(v)

    texto = _inf(v)
    assert 'CORTESIA:' in texto
    assert 'CAPACETE PRETO' in texto


def test_inf_contribuinte_cortesia_qtd_maior_que_um(db, loja_factory, peca_factory):
    v = _venda(loja_factory())
    p = peca_factory(descricao='RETROVISOR')
    p.preco_venda_padrao = Decimal('20')
    _db.session.flush()
    venda_service.adicionar_brinde(v.id, p.id, qtd=2, usuario='t')
    _db.session.refresh(v)

    texto = _inf(v)
    assert 'CORTESIA:' in texto
    assert '2x RETROVISOR' in texto


def test_inf_contribuinte_sem_brinde_nao_tem_cortesia(db, loja_factory):
    v = _venda(loja_factory())
    texto = _inf(v)
    assert 'CORTESIA' not in texto
