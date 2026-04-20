"""Testes dos filtros de F1 (busca global e filtros avancados) em /pessoal/transacoes.

Testa a logica de query SQLAlchemy diretamente — mesma que a rota usa.
Evita o overhead do HTTP client e valida o comportamento do filtro em isolado.
"""
from decimal import Decimal

import pytest

from app.pessoal.models import PessoalTransacao
from app.pessoal.routes.transacoes import aplicar_filtros_extras as _aplicar_filtros


@pytest.mark.integration
def test_filtro_valor_min_retorna_apenas_acima(pessoal_ctx, make_transacao):
    t1 = make_transacao(historico='PEQUENA', valor=Decimal('50.00'))
    t2 = make_transacao(historico='MEDIA', valor=Decimal('300.00'))
    t3 = make_transacao(historico='GRANDE', valor=Decimal('1200.00'))

    ids_nossos = {t1.id, t2.id, t3.id}
    q = PessoalTransacao.query.filter(PessoalTransacao.id.in_(ids_nossos))
    q = _aplicar_filtros(q, valor_min=200)
    retornados = {t.id for t in q.all()}

    assert t2.id in retornados
    assert t3.id in retornados
    assert t1.id not in retornados


@pytest.mark.integration
def test_filtro_valor_max_retorna_apenas_abaixo(pessoal_ctx, make_transacao):
    t_barato = make_transacao(historico='BARATO', valor=Decimal('50.00'))
    t_caro = make_transacao(historico='CARO', valor=Decimal('999.00'))

    ids_nossos = {t_barato.id, t_caro.id}
    q = PessoalTransacao.query.filter(PessoalTransacao.id.in_(ids_nossos))
    q = _aplicar_filtros(q, valor_max=100)
    retornados = {t.id for t in q.all()}

    assert t_barato.id in retornados
    assert t_caro.id not in retornados


@pytest.mark.integration
def test_filtro_valor_min_e_max_range(pessoal_ctx, make_transacao):
    t_min = make_transacao(historico='MINVAL', valor=Decimal('10.00'))
    t_meio = make_transacao(historico='MEIOVAL', valor=Decimal('500.00'))
    t_max = make_transacao(historico='MAXVAL', valor=Decimal('2000.00'))

    ids_nossos = {t_min.id, t_meio.id, t_max.id}
    q = PessoalTransacao.query.filter(PessoalTransacao.id.in_(ids_nossos))
    q = _aplicar_filtros(q, valor_min=100, valor_max=1000)
    retornados = {t.id for t in q.all()}

    assert t_meio.id in retornados
    assert t_min.id not in retornados
    assert t_max.id not in retornados


@pytest.mark.integration
def test_filtro_tem_categoria_sim(pessoal_ctx, make_transacao, categoria_alimentacao):
    t_cat = make_transacao(historico='CATEGORIZADA',
                           categoria_id=categoria_alimentacao.id)
    t_sem = make_transacao(historico='SEM CAT')

    ids_nossos = {t_cat.id, t_sem.id}
    q = PessoalTransacao.query.filter(PessoalTransacao.id.in_(ids_nossos))
    q = _aplicar_filtros(q, tem_categoria='sim')
    retornados = {t.id for t in q.all()}

    assert t_cat.id in retornados
    assert t_sem.id not in retornados


@pytest.mark.integration
def test_filtro_tem_categoria_nao(pessoal_ctx, make_transacao, categoria_alimentacao):
    t_cat = make_transacao(historico='CATEGORIZADA2',
                           categoria_id=categoria_alimentacao.id)
    t_sem = make_transacao(historico='PENDENTE CAT')

    ids_nossos = {t_cat.id, t_sem.id}
    q = PessoalTransacao.query.filter(PessoalTransacao.id.in_(ids_nossos))
    q = _aplicar_filtros(q, tem_categoria='nao')
    retornados = {t.id for t in q.all()}

    assert t_sem.id in retornados
    assert t_cat.id not in retornados
