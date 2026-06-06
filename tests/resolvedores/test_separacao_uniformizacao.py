"""TDD — uniformizacao do filtro de saldo em separacao (decisao Rafael 2026-06-01).

As funcoes RICAS resolver_cliente/grupo/uf para fonte='separacao' agora filtram
`qtd_saldo > 0` (alem de `sincronizado_nf == False`), igualando as funcoes _cli.
Validacao por equivalencia: a saida da funcao == query de referencia com qtd_saldo>0.
"""
import pytest

from app.resolvedores.grupo import resolver_grupo
from app.resolvedores.uf import resolver_uf
from app.resolvedores.cliente import resolver_cliente

PREFIXOS_ATACADAO = ['93.209.76', '75.315.33', '00.063.96']


def test_resolver_grupo_separacao_equivale_query_referencia(db):
    from app.separacao.models import Separacao
    from sqlalchemy import or_

    r = resolver_grupo('atacadao', fonte='separacao')
    nums_func = {p['num_pedido'] for p in r.get('pedidos', [])} if r.get('sucesso') else set()

    ref = Separacao.query.with_entities(Separacao.num_pedido).filter(
        or_(*[Separacao.cnpj_cpf.like(f'{p}%') for p in PREFIXOS_ATACADAO]),
        Separacao.sincronizado_nf == False,
        Separacao.qtd_saldo > 0,
    ).distinct().all()
    nums_ref = {n[0] for n in ref}

    assert nums_func == nums_ref


def test_resolver_uf_separacao_so_pedidos_com_saldo(db):
    from app.separacao.models import Separacao

    r = resolver_uf('SP', fonte='separacao')
    if not r.get('sucesso'):
        pytest.skip("sem pedidos SP em separacao com saldo")
    for p in r['pedidos']:
        cnt = Separacao.query.filter(
            Separacao.num_pedido == p['num_pedido'],
            Separacao.sincronizado_nf == False,
            Separacao.qtd_saldo > 0,
        ).count()
        assert cnt > 0, f"pedido {p['num_pedido']} sem item saldo>0 em separacao"


def test_resolver_cliente_separacao_so_pedidos_com_saldo(db):
    from app.separacao.models import Separacao

    row = Separacao.query.with_entities(Separacao.raz_social_red).filter(
        Separacao.sincronizado_nf == False,
        Separacao.qtd_saldo > 0,
        Separacao.raz_social_red.isnot(None),
    ).first()
    if row is None:
        pytest.skip("sem separacao com saldo no banco")
    r = resolver_cliente(row[0], fonte='separacao')
    if not r.get('sucesso'):
        pytest.skip("cliente nao resolveu em separacao")
    for p in r['pedidos']:
        cnt = Separacao.query.filter(
            Separacao.num_pedido == p['num_pedido'],
            Separacao.sincronizado_nf == False,
            Separacao.qtd_saldo > 0,
        ).count()
        assert cnt > 0, f"pedido {p['num_pedido']} sem item saldo>0 em separacao"
