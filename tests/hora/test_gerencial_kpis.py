"""KPIs da seção Gerencial HORA — Executivo (F2) e Comercial (F3).

Fixtures criam vendas FATURADO + custo real (NF entrada por chassi) + brindes
para exercitar margem, cobertura, ticket, ranking e bucket sem-loja.
"""
import uuid
from datetime import date
from decimal import Decimal

import pytest

from app import db as _db
from app.hora.services.gerencial.filtros import Filtros

PERIODO_INI = date(2026, 6, 1)
PERIODO_FIM = date(2026, 6, 30)


def _filtros(loja_id=None, lojas_permitidas=None, granularidade='dia',
             ini=PERIODO_INI, fim=PERIODO_FIM):
    return Filtros(data_ini=ini, data_fim=fim, granularidade=granularidade,
                   loja_id=loja_id, lojas_permitidas=lojas_permitidas)


@pytest.fixture
def venda_factory(db, modelo_moto):
    """Cria HoraVenda FATURADO/etc. com itens-moto, custo (NF entrada) e brindes.

    item dict: {preco_final, preco_real(None=sem custo), preco_tabela, desconsiderado}
    """
    from app.hora.models import (
        HoraVenda, HoraVendaItem, HoraMoto, HoraNfEntrada, HoraNfEntradaItem,
        HoraVendaBrinde,
    )
    from app.utils.timezone import agora_brasil_naive

    def make(*, loja, status='FATURADO', data_venda=None, vendedor='VEND A',
             itens=None, origem_criacao='MANUAL', forma_pagamento='PIX',
             brinde_custo=None, peca=None):
        data_venda = data_venda or date(2026, 6, 15)
        venda = HoraVenda(
            loja_id=(loja.id if loja else None),
            cpf_cliente='12345678901', nome_cliente='Cliente Teste',
            data_venda=data_venda, status=status, valor_total=0,
            forma_pagamento=forma_pagamento, vendedor=vendedor,
            origem_criacao=origem_criacao,
            faturado_em=agora_brasil_naive(),
            criado_em=agora_brasil_naive(),
        )
        _db.session.add(venda)
        _db.session.flush()
        total = Decimal('0')
        for it in (itens or [{'preco_final': 1000, 'preco_real': 600}]):
            chassi = it.get('chassi') or f'C{uuid.uuid4().hex[:18].upper()}'
            if not HoraMoto.query.get(chassi):
                _db.session.add(HoraMoto(numero_chassi=chassi,
                                         modelo_id=modelo_moto.id, cor='PRETA'))
                _db.session.flush()
            pf = Decimal(str(it['preco_final']))
            ptab = Decimal(str(it.get('preco_tabela', it['preco_final'])))
            desc = ptab - pf
            _db.session.add(HoraVendaItem(
                venda_id=venda.id, numero_chassi=chassi,
                preco_tabela_referencia=ptab, preco_final=pf,
                desconto_aplicado=desc,
                desconto_percentual=(desc / ptab * 100 if ptab else 0),
            ))
            total += pf
            preco_real = it.get('preco_real')
            if preco_real is not None:
                uid = uuid.uuid4().hex[:12].upper()
                nf = HoraNfEntrada(
                    chave_44=uid.zfill(44), numero_nf=uid[:8],
                    cnpj_emitente='12345678000199',
                    cnpj_destinatario=(loja.cnpj if loja else '99999999000199'),
                    loja_destino_id=(loja.id if loja else None),
                    data_emissao=data_venda, valor_total=preco_real,
                    criado_em=agora_brasil_naive(),
                )
                _db.session.add(nf)
                _db.session.flush()
                _db.session.add(HoraNfEntradaItem(
                    nf_id=nf.id, numero_chassi=chassi,
                    preco_real=Decimal(str(preco_real)),
                    desconsiderado=it.get('desconsiderado', False),
                ))
        if brinde_custo is not None and peca is not None:
            c = Decimal(str(brinde_custo))
            _db.session.add(HoraVendaBrinde(
                venda_id=venda.id, peca_id=peca.id, qtd=1,
                custo_unitario=c, custo_total=c,
                criado_em=agora_brasil_naive(),
            ))
        venda.valor_total = total
        _db.session.flush()
        return venda
    return make


# ───────────────────────── Receita / Ticket / Volume ─────────────────────────

def test_receita_realizada_so_faturado(db, loja_factory, venda_factory):
    from app.hora.services.gerencial import kpi_service
    loja = loja_factory()
    venda_factory(loja=loja, status='FATURADO', itens=[{'preco_final': 1000, 'preco_real': 600}])
    venda_factory(loja=loja, status='COTACAO', itens=[{'preco_final': 500, 'preco_real': 300}])
    r = kpi_service.receita_realizada(_filtros())
    assert r['valor'] == Decimal('1000')
    assert r['qtd_vendas'] == 1


def test_ticket_medio_faturado(db, loja_factory, venda_factory):
    from app.hora.services.gerencial import kpi_service
    loja = loja_factory()
    venda_factory(loja=loja, itens=[{'preco_final': 1000, 'preco_real': 600}])
    venda_factory(loja=loja, itens=[{'preco_final': 2000, 'preco_real': 1200}])
    assert kpi_service.ticket_medio(_filtros()) == Decimal('1500')


def test_motos_vendidas_conta_itens(db, loja_factory, venda_factory):
    from app.hora.services.gerencial import kpi_service
    loja = loja_factory()
    venda_factory(loja=loja, itens=[{'preco_final': 1000, 'preco_real': 600},
                                    {'preco_final': 1000, 'preco_real': 600}])
    venda_factory(loja=loja, status='CANCELADO', itens=[{'preco_final': 1000, 'preco_real': 600}])
    assert kpi_service.motos_vendidas(_filtros()) == 2


# ───────────────────────── Margem + cobertura ─────────────────────────

def test_margem_desconta_custo(db, loja_factory, venda_factory):
    from app.hora.services.gerencial import kpi_service
    loja = loja_factory()
    venda_factory(loja=loja, itens=[{'preco_final': 1000, 'preco_real': 600}])
    m = kpi_service.margem_bruta(_filtros())
    assert m['margem_rs'] == Decimal('400')
    assert m['custo_total'] == Decimal('600')
    assert m['cobertura_pct'] == Decimal('100')


def test_margem_desconta_brinde(db, loja_factory, venda_factory, peca_factory):
    from app.hora.services.gerencial import kpi_service
    loja = loja_factory()
    peca = peca_factory()
    venda_factory(loja=loja, itens=[{'preco_final': 1000, 'preco_real': 600}],
                  brinde_custo=50, peca=peca)
    m = kpi_service.margem_bruta(_filtros())
    assert m['brinde_total'] == Decimal('50')
    assert m['margem_rs'] == Decimal('350')  # 1000 - 600 - 50


def test_margem_cobertura_exclui_item_sem_custo(db, loja_factory, venda_factory):
    from app.hora.services.gerencial import kpi_service
    loja = loja_factory()
    # 1 item com custo, 1 item sem custo (preco_real=None)
    venda_factory(loja=loja, itens=[
        {'preco_final': 1000, 'preco_real': 600},
        {'preco_final': 1000, 'preco_real': None},
    ])
    m = kpi_service.margem_bruta(_filtros())
    assert m['total_itens'] == 2
    assert m['itens_com_custo'] == 1
    assert m['cobertura_pct'] == Decimal('50')
    assert m['margem_rs'] == Decimal('400')  # só o item com custo


def test_margem_ignora_desconsiderado(db, loja_factory, venda_factory):
    from app.hora.services.gerencial import kpi_service
    loja = loja_factory()
    # item com NF entrada mas desconsiderado=True -> não conta como custo
    venda_factory(loja=loja, itens=[{'preco_final': 1000, 'preco_real': 600, 'desconsiderado': True}])
    m = kpi_service.margem_bruta(_filtros())
    assert m['itens_com_custo'] == 0
    assert m['cobertura_pct'] == Decimal('0')


# ───────────────────────── Ranking / Tendência / Desconto ─────────────────────────

def test_ranking_lojas_ordena_por_receita(db, loja_factory, venda_factory):
    from app.hora.services.gerencial import kpi_service
    loja_a = loja_factory()
    loja_b = loja_factory()
    venda_factory(loja=loja_a, itens=[{'preco_final': 1000, 'preco_real': 600}])
    venda_factory(loja=loja_b, itens=[{'preco_final': 3000, 'preco_real': 1800}])
    rank = kpi_service.ranking_lojas(_filtros())
    assert rank[0]['loja_id'] == loja_b.id
    assert rank[0]['receita'] == Decimal('3000')
    assert rank[0]['unidades'] == 1


def test_ranking_bucket_sem_loja_so_irrestrito(db, loja_factory, venda_factory):
    from app.hora.services.gerencial import kpi_service
    loja = loja_factory()
    venda_factory(loja=loja, itens=[{'preco_final': 1000, 'preco_real': 600}])
    venda_factory(loja=None, itens=[{'preco_final': 500, 'preco_real': 300}])  # loja_id NULL
    # irrestrito (lojas_permitidas=None, loja_id=None) -> inclui bucket NULL
    rank_irrestrito = kpi_service.ranking_lojas(_filtros())
    assert any(r['loja_id'] is None for r in rank_irrestrito)
    # restrito a [loja.id] -> NÃO inclui bucket NULL
    rank_restrito = kpi_service.ranking_lojas(_filtros(lojas_permitidas=[loja.id]))
    assert all(r['loja_id'] is not None for r in rank_restrito)


def test_receita_por_periodo_agrupa_por_dia(db, loja_factory, venda_factory):
    from app.hora.services.gerencial import kpi_service
    loja = loja_factory()
    venda_factory(loja=loja, data_venda=date(2026, 6, 10), itens=[{'preco_final': 1000, 'preco_real': 600}])
    venda_factory(loja=loja, data_venda=date(2026, 6, 11), itens=[{'preco_final': 2000, 'preco_real': 1200}])
    serie = kpi_service.receita_por_periodo(_filtros())
    periodos = {p['periodo']: p['valor'] for p in serie}
    assert periodos['2026-06-10'] == Decimal('1000')
    assert periodos['2026-06-11'] == Decimal('2000')


def test_desconto_total_faturado(db, loja_factory, venda_factory):
    from app.hora.services.gerencial import kpi_service
    loja = loja_factory()
    venda_factory(loja=loja, itens=[{'preco_final': 900, 'preco_tabela': 1000, 'preco_real': 600}])
    assert kpi_service.desconto_total(_filtros()) == Decimal('100')


def test_escopo_loja_filtra_outra_loja(db, loja_factory, venda_factory):
    from app.hora.services.gerencial import kpi_service
    loja_a = loja_factory()
    loja_b = loja_factory()
    venda_factory(loja=loja_a, itens=[{'preco_final': 1000, 'preco_real': 600}])
    venda_factory(loja=loja_b, itens=[{'preco_final': 5000, 'preco_real': 600}])
    # gerente escopado à loja_a só vê a receita da loja_a
    r = kpi_service.receita_realizada(_filtros(lojas_permitidas=[loja_a.id]))
    assert r['valor'] == Decimal('1000')


# ───────────────────────── Smoke da tela (renderização autenticada) ──────────

def test_executivo_renderiza_autenticado(client_admin, loja_factory, venda_factory):
    loja = loja_factory()
    venda_factory(loja=loja, data_venda=date(2026, 6, 15),
                  itens=[{'preco_final': 1000, 'preco_real': 600}])
    r = client_admin.get('/hora/gerencial/executivo?data_ini=2026-06-01&data_fim=2026-06-30')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'Receita realizada' in body
    assert 'ger-chart-receita' in body          # canvas do gráfico de tendência
    assert '1.000,00' in body                   # receita formatada (valor_br)
