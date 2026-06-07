"""Testes do cadastro de comissao (roadmap #28, Fatia 1).

comissao_service faz commit (fura savepoint). Faixas/peca/modelo usam uuid /
limpeza local p/ isolamento. Ver [[gotcha_testes_hora_residuo]].
"""
import uuid
from decimal import Decimal

import pytest

from app import db as _db
from app.hora.services import comissao_service
from app.hora.models import HoraComissaoFaixaDesconto, HoraModelo


def _limpar_faixas():
    HoraComissaoFaixaDesconto.query.delete()
    _db.session.commit()


def _modelo():
    m = HoraModelo(nome_modelo=f'TST-{uuid.uuid4().hex[:8].upper()}', ativo=True)
    _db.session.add(m)
    _db.session.flush()
    return m


def test_get_config_cria_singleton(db):
    cfg = comissao_service.get_config()
    assert cfg.id == 1


def test_set_comissao_base_moto(db):
    comissao_service.set_comissao_base_moto('150,00', usuario='tester')
    assert comissao_service.get_config().comissao_base_moto == Decimal('150.00')


def test_set_comissao_base_negativo_falha(db):
    with pytest.raises(ValueError):
        comissao_service.set_comissao_base_moto('-10')


def test_criar_e_listar_faixa(db):
    _limpar_faixas()
    comissao_service.criar_faixa('100', '300', '20')
    faixas = comissao_service.listar_faixas()
    assert len(faixas) == 1
    assert faixas[0].desconto_min == Decimal('100')
    assert faixas[0].desconto_max == Decimal('300')
    assert faixas[0].reducao_comissao == Decimal('20')


def test_criar_faixa_max_menor_que_min_falha(db):
    with pytest.raises(ValueError):
        comissao_service.criar_faixa('300', '100', '20')


def test_remover_faixa(db):
    _limpar_faixas()
    f = comissao_service.criar_faixa('0', '50', '5')
    comissao_service.remover_faixa(f.id)
    assert HoraComissaoFaixaDesconto.query.get(f.id) is None


def test_reducao_comissao_para_desconto(db):
    _limpar_faixas()
    comissao_service.criar_faixa('0', '100', '0')
    comissao_service.criar_faixa('100', '300', '20')
    comissao_service.criar_faixa('300', '', '50')  # aberta superiormente
    assert comissao_service.reducao_comissao_para_desconto('50') == Decimal('0')
    assert comissao_service.reducao_comissao_para_desconto('150') == Decimal('20')
    assert comissao_service.reducao_comissao_para_desconto('1000') == Decimal('50')


def test_set_comissao_peca(db, peca_factory):
    p = peca_factory()
    comissao_service.set_comissao_peca(p.id, '12,50')
    assert p.valor_comissao == Decimal('12.50')


def test_set_teto_modelo_e_limpar(db):
    m = _modelo()
    comissao_service.set_teto_modelo(m.id, '500')
    assert m.desconto_maximo == Decimal('500')
    comissao_service.set_teto_modelo(m.id, '')  # vazio = sem teto
    assert m.desconto_maximo is None
