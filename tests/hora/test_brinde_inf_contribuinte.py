"""CORTESIA nas informacoes complementares (inf_contribuinte) da NF-e.

Brinde da venda deve aparecer no FINAL do inf_contribuinte como
"CORTESIA: <peca_1>, <peca_2>...". Sem brinde, nenhuma linha CORTESIA.

A peca de REVISAO (codigo_interno REVISAO, id 211 em PROD) e' tratada a' parte:
ganha um bloco institucional proprio (revisao gratuita de 3 meses) e NAO entra
na linha "CORTESIA: <pecas>".
"""
import unicodedata
from decimal import Decimal

from app import db as _db
from app.hora.models import HoraPeca, HoraVenda, HoraVendaBrinde
from app.hora.services import venda_service
from app.hora.services.tagplus.payload_builder import (
    TEXTO_CORTESIA_REVISAO,
    PayloadBuilder,
)
from app.utils.timezone import agora_utc_naive


def _norm(s):
    nfkd = unicodedata.normalize('NFKD', s or '')
    return ''.join(c for c in nfkd if not unicodedata.combining(c)).strip().upper()


def _reset_pecas_revisao():
    """Remove pecas residuais de revisao (services commitam e escapam o savepoint
    do fixture `db`; codigo_interno e' UNIQUE -> colidiria entre testes)."""
    pecas = [p for p in HoraPeca.query.all() if _norm(p.codigo_interno) == 'REVISAO']
    for p in pecas:
        HoraVendaBrinde.query.filter_by(peca_id=p.id).delete()
        _db.session.delete(p)
    _db.session.commit()


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


def test_inf_contribuinte_revisao_exibe_texto_institucional(db, loja_factory, peca_factory):
    _reset_pecas_revisao()
    v = _venda(loja_factory())
    p = peca_factory(codigo_interno='REVISÃO', descricao='SE - REVISÃO')
    p.preco_venda_padrao = Decimal('199.90')
    _db.session.flush()
    venda_service.adicionar_brinde(v.id, p.id, qtd=1, usuario='t')
    _db.session.refresh(v)

    texto = _inf(v)
    # Bloco institucional proprio da revisao
    assert TEXTO_CORTESIA_REVISAO in texto
    assert 'Revisão gratuita de 3 meses' in texto
    assert 'Será válida em apenas uma das lojas' in texto
    # NAO duplica: a descricao da peca nao vira item de "CORTESIA: <pecas>"
    assert 'SE - REVISÃO' not in texto
    assert 'CORTESIA:' not in texto
    # infCpl e' texto plano: marcadores markdown nao podem vazar para a NF
    assert '*' not in texto
    assert '_' not in texto


def test_inf_contribuinte_revisao_detecta_por_codigo_sem_acento(db, loja_factory, peca_factory):
    _reset_pecas_revisao()
    v = _venda(loja_factory())
    # 'revisao' (minusculo, sem acento) tem que disparar o mesmo tratamento.
    p = peca_factory(codigo_interno='revisao', descricao='Revisao Gratis')
    _db.session.flush()
    venda_service.adicionar_brinde(v.id, p.id, qtd=1, usuario='t')
    _db.session.refresh(v)

    texto = _inf(v)
    assert TEXTO_CORTESIA_REVISAO in texto
    assert 'Revisao Gratis' not in texto


def test_inf_contribuinte_revisao_mais_peca_fisica(db, loja_factory, peca_factory):
    _reset_pecas_revisao()
    v = _venda(loja_factory())
    rev = peca_factory(codigo_interno='REVISÃO', descricao='SE - REVISÃO')
    cap = peca_factory(descricao='CAPACETE PRETO')
    _db.session.flush()
    venda_service.adicionar_brinde(v.id, rev.id, qtd=1, usuario='t')
    venda_service.adicionar_brinde(v.id, cap.id, qtd=1, usuario='t')
    _db.session.refresh(v)

    texto = _inf(v)
    # Peca fisica continua na linha CORTESIA
    assert 'CORTESIA: CAPACETE PRETO' in texto
    # Revisao tem bloco proprio e nao entra na linha de pecas
    assert TEXTO_CORTESIA_REVISAO in texto
    assert 'SE - REVISÃO' not in texto
