"""Testes do Recibo Simples de pecas/oficina (roadmap #1b).

Auto-contidos com uuid (loja_factory + peca_factory) — gerar_recibo faz commit
(fura savepoint), entao fixtures de id/nome fixo colidiriam. Ver memoria
[[gotcha_testes_hora_residuo]].

O PDF (weasyprint) e mockado: o foco e a logica (numeracao GLOBAL sequencial,
valor, status, validacao). A geracao real do PDF/S3 e best-effort no service.
"""
from decimal import Decimal

import pytest

from app import db as _db
from app.hora.services import recibo_service
from app.hora.models import HoraVenda, HoraVendaItemPeca
from app.utils.timezone import agora_utc_naive


def _venda(loja):
    v = HoraVenda(
        loja_id=loja.id, cpf_cliente='12345678909', nome_cliente='Cliente Teste',
        valor_total=0, status='COTACAO', data_venda=agora_utc_naive().date(),
        origem_criacao='MANUAL',
    )
    _db.session.add(v)
    _db.session.flush()
    return v


def _venda_com_peca(loja, peca, valor=Decimal('50')):
    v = _venda(loja)
    ip = HoraVendaItemPeca(
        venda_id=v.id, peca_id=peca.id, qtd=Decimal('1'),
        preco_unitario_referencia=valor, preco_final=valor,
    )
    _db.session.add(ip)
    _db.session.flush()
    return v


def test_gerar_recibo_sem_pecas_falha(db, loja_factory):
    v = _venda(loja_factory())  # sem peca
    with pytest.raises(recibo_service.ReciboError, match='peças'):
        recibo_service.gerar_recibo(v.id, usuario='tester')


def test_gerar_recibo_com_pecas(db, loja_factory, peca_factory, monkeypatch):
    monkeypatch.setattr(recibo_service, '_render_pdf_bytes', lambda venda, recibo: b'%PDF-fake')
    v = _venda_com_peca(loja_factory(), peca_factory(), Decimal('50'))
    recibo = recibo_service.gerar_recibo(v.id, usuario='tester')
    assert recibo.status == 'EMITIDO'
    assert recibo.numero >= 1
    assert recibo.valor_total == Decimal('50')
    assert recibo.numero_display.startswith('REC-')


def test_numero_sequencial_global(db, loja_factory, peca_factory, monkeypatch):
    monkeypatch.setattr(recibo_service, '_render_pdf_bytes', lambda venda, recibo: b'%PDF')
    loja, peca = loja_factory(), peca_factory()
    r1 = recibo_service.gerar_recibo(_venda_com_peca(loja, peca).id)
    r2 = recibo_service.gerar_recibo(_venda_com_peca(loja, peca).id)
    assert r2.numero > r1.numero  # sequencial global crescente


def test_render_pdf_html_nao_quebra(db, loja_factory, peca_factory):
    """Exercita o template recibo_pdf.html com dados reais (filtros/atributos)."""
    from app.hora.models import HoraRecibo
    loja, peca = loja_factory(), peca_factory()
    v = _venda_com_peca(loja, peca, Decimal('123.45'))
    recibo = HoraRecibo(
        numero=1, venda_id=v.id, valor_total=Decimal('123.45'),
        status='EMITIDO', emitido_em=agora_utc_naive(),
    )
    html = recibo_service.render_template(
        'hora/imprimir_recibo.html', venda=v, recibo=recibo, itens_peca=list(v.itens_peca),
    )
    assert 'REC-000001' in html
    assert 'NÃO-FISCAL' in html


def test_cancelar_recibo(db, loja_factory, peca_factory, monkeypatch):
    monkeypatch.setattr(recibo_service, '_render_pdf_bytes', lambda venda, recibo: b'%PDF')
    r = recibo_service.gerar_recibo(_venda_com_peca(loja_factory(), peca_factory()).id)
    recibo_service.cancelar_recibo(r.id, usuario='tester', motivo='engano')
    assert r.status == 'CANCELADO'
    assert r.cancelado_em is not None
    # idempotente
    recibo_service.cancelar_recibo(r.id, usuario='tester')
    assert r.status == 'CANCELADO'
