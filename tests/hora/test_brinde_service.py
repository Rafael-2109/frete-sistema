"""Testes de Brindes de venda (roadmap #36).

Brinde = peca do catalogo: custo = peca.custo (snapshot — hora_59), NAO cobrado
(fora do valor_total), NAO abate estoque. Custo reduz a margem (preview).

Auto-contidos com uuid — adicionar_brinde faz commit (fura savepoint). Ver
[[gotcha_testes_hora_residuo]].
"""
from decimal import Decimal

import pytest

from app import db as _db
from app.hora.services import venda_service, venda_preview_service
from app.hora.models import HoraVenda, HoraVendaBrinde, HoraPecaMovimento
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


def _peca(peca_factory, custo=Decimal('30')):
    p = peca_factory()
    # preco de venda intencionalmente != custo p/ provar que a margem usa o CUSTO.
    p.preco_venda_padrao = custo + Decimal('100')
    p.custo = custo  # custo real usado na margem (hora_59)
    _db.session.flush()
    return p


def test_adicionar_brinde_usa_custo_real(db, loja_factory, peca_factory):
    v = _venda(loja_factory())
    p = _peca(peca_factory, Decimal('30'))
    brinde = venda_service.adicionar_brinde(v.id, p.id, qtd=2, usuario='tester')
    assert brinde.custo_unitario == Decimal('30')  # custo, NAO preco_venda_padrao
    assert brinde.custo_total == Decimal('60')  # 2 * 30


def test_brinde_nao_soma_valor_total(db, loja_factory, peca_factory):
    v = _venda(loja_factory())
    p = _peca(peca_factory, Decimal('30'))
    total_antes = v.valor_total
    venda_service.adicionar_brinde(v.id, p.id, qtd=1, usuario='tester')
    assert v.valor_total == total_antes  # brinde nao entra no valor cobrado


def test_brinde_nao_abate_estoque(db, loja_factory, peca_factory):
    v = _venda(loja_factory())
    p = _peca(peca_factory, Decimal('30'))
    venda_service.adicionar_brinde(v.id, p.id, qtd=5, usuario='tester')
    # nenhum movimento de estoque criado para a peca
    assert HoraPecaMovimento.query.filter_by(peca_id=p.id).count() == 0


def test_preview_inclui_custo_brindes(db, loja_factory, peca_factory):
    v = _venda(loja_factory())
    p = _peca(peca_factory, Decimal('40'))
    venda_service.adicionar_brinde(v.id, p.id, qtd=1, usuario='tester')
    _db.session.refresh(v)
    preview = venda_preview_service.montar_preview(v)
    assert preview['custo_brindes_total'] == Decimal('40')
    # liquido = venda_total - frete - custo_moto - custo_brindes; sem moto/frete:
    assert preview['liquido'] == Decimal('1000') - Decimal('40')


def test_remover_brinde(db, loja_factory, peca_factory):
    v = _venda(loja_factory())
    p = _peca(peca_factory, Decimal('30'))
    brinde = venda_service.adicionar_brinde(v.id, p.id, qtd=1, usuario='tester')
    venda_service.remover_brinde(v.id, brinde.id, usuario='tester')
    assert HoraVendaBrinde.query.get(brinde.id) is None


def test_adicionar_brinde_fora_cotacao_falha(db, loja_factory, peca_factory):
    """CONFIRMADO/FATURADO bloqueiam (preserva a aprovacao gerencial de brinde)."""
    v = _venda(loja_factory())
    v.status = 'CONFIRMADO'
    _db.session.flush()
    p = _peca(peca_factory, Decimal('30'))
    with pytest.raises(venda_service.TransicaoInvalidaError):
        venda_service.adicionar_brinde(v.id, p.id, qtd=1, usuario='tester')


def test_adicionar_brinde_em_incompleto_funciona(db, loja_factory, peca_factory):
    """Brinde gerenciavel em INCOMPLETO (alinha com itens — pedido nasce INCOMPLETO)."""
    v = _venda(loja_factory())
    v.status = 'INCOMPLETO'
    _db.session.flush()
    p = _peca(peca_factory, Decimal('30'))
    brinde = venda_service.adicionar_brinde(v.id, p.id, qtd=1, usuario='tester')
    assert HoraVendaBrinde.query.get(brinde.id) is not None


def test_remover_brinde_em_incompleto_funciona(db, loja_factory, peca_factory):
    v = _venda(loja_factory())
    p = _peca(peca_factory, Decimal('30'))
    brinde = venda_service.adicionar_brinde(v.id, p.id, qtd=1, usuario='tester')
    v.status = 'INCOMPLETO'
    _db.session.flush()
    venda_service.remover_brinde(v.id, brinde.id, usuario='tester')
    assert HoraVendaBrinde.query.get(brinde.id) is None
