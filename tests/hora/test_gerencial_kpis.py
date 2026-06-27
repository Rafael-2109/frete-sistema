"""KPIs da seção Gerencial HORA — Executivo (F2) e Comercial (F3).

Fixtures criam vendas FATURADO + custo real (NF entrada por chassi) + brindes
para exercitar margem, cobertura, ticket, ranking e bucket sem-loja.
"""
from datetime import date
from decimal import Decimal

from app import db as _db
from app.hora.services.gerencial.filtros import Filtros

PERIODO_INI = date(2026, 6, 1)
PERIODO_FIM = date(2026, 6, 30)


def _filtros(loja_id=None, lojas_permitidas=None, granularidade='dia',
             ini=PERIODO_INI, fim=PERIODO_FIM):
    return Filtros(data_ini=ini, data_fim=fim, granularidade=granularidade,
                   loja_id=loja_id, lojas_permitidas=lojas_permitidas)


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


def test_margem_usa_custo_da_nf_mais_recente(db, loja_factory, venda_factory):
    """Chassi com 2 NFs de entrada -> custo = NF mais recente (maior id), não MIN."""
    import uuid
    from app.hora.models import HoraNfEntrada, HoraNfEntradaItem
    from app.utils.timezone import agora_brasil_naive
    from app.hora.services.gerencial import kpi_service
    loja = loja_factory()
    chassi = 'CHS' + uuid.uuid4().hex[:14].upper()
    venda_factory(loja=loja, itens=[{'chassi': chassi, 'preco_final': 1000, 'preco_real': 600}])
    uid = uuid.uuid4().hex[:12].upper()
    nf2 = HoraNfEntrada(
        chave_44=uid.zfill(44), numero_nf=uid[:8], cnpj_emitente='12345678000199',
        cnpj_destinatario=loja.cnpj, loja_destino_id=loja.id,
        data_emissao=date(2026, 6, 16), valor_total=700, criado_em=agora_brasil_naive(),
    )
    _db.session.add(nf2)
    _db.session.flush()
    _db.session.add(HoraNfEntradaItem(nf_id=nf2.id, numero_chassi=chassi,
                                      preco_real=Decimal('700'), desconsiderado=False))
    _db.session.flush()
    m = kpi_service.margem_bruta(_filtros(lojas_permitidas=[loja.id]))
    assert m['custo_total'] == Decimal('700')   # NF mais recente, não MIN(600)
    assert m['margem_rs'] == Decimal('300')


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


# ═══════════════════════════ F3 — Comercial & Vendedores ═══════════════════════

def test_conversao_funil_so_manual(db, loja_factory, venda_factory):
    from app.hora.services.gerencial import comercial_kpi_service as cks
    loja = loja_factory()
    venda_factory(loja=loja, status='COTACAO', origem_criacao='MANUAL', itens=[{'preco_final': 1000, 'preco_real': 600}])
    venda_factory(loja=loja, status='CONFIRMADO', origem_criacao='MANUAL', itens=[{'preco_final': 1000, 'preco_real': 600}])
    venda_factory(loja=loja, status='FATURADO', origem_criacao='MANUAL', itens=[{'preco_final': 1000, 'preco_real': 600}])
    venda_factory(loja=loja, status='FATURADO', origem_criacao='DANFE', itens=[{'preco_final': 1000, 'preco_real': 600}])
    # escopa à loja única do teste (isola de vendas residuais COTACAO/CONFIRMADO no banco local)
    f = cks.conversao_funil(_filtros(lojas_permitidas=[loja.id]))
    assert f['cotacao'] == 1 and f['confirmado'] == 1 and f['faturado'] == 1
    assert f['taxa'] == Decimal('1') / Decimal('3') * 100  # 1 faturado de 3 no funil


def test_vendas_por_vendedor_agrupa(db, loja_factory, venda_factory):
    from app.hora.services.gerencial import comercial_kpi_service as cks
    loja = loja_factory()
    venda_factory(loja=loja, vendedor='ANA', itens=[{'preco_final': 1000, 'preco_real': 600}])
    venda_factory(loja=loja, vendedor='ANA', itens=[{'preco_final': 2000, 'preco_real': 600}])
    venda_factory(loja=loja, vendedor='BIA', itens=[{'preco_final': 500, 'preco_real': 600}])
    rows = cks.vendas_por_vendedor(_filtros())
    ana = next(r for r in rows if r['vendedor'] == 'ANA')
    assert ana['unidades'] == 2 and ana['receita'] == Decimal('3000')
    assert rows[0]['vendedor'] == 'ANA'  # ordenado por receita desc


def test_comissao_por_vendedor_respeita_escopo(db, loja_factory, venda_factory):
    from app.hora.services.gerencial import comercial_kpi_service as cks
    loja_a = loja_factory()
    loja_b = loja_factory()
    venda_factory(loja=loja_a, vendedor='ANA', itens=[{'preco_final': 1000, 'preco_real': 600}])
    venda_factory(loja=loja_b, vendedor='BIA', itens=[{'preco_final': 1000, 'preco_real': 600}])
    rows = cks.comissao_por_vendedor(_filtros(lojas_permitidas=[loja_a.id]))
    vendedores = {r['vendedor'] for r in rows}
    assert 'ANA' in vendedores
    assert 'BIA' not in vendedores  # escopo de loja oculta vendedor de outra loja


def test_aprovacoes_pendentes_por_tipo(db, loja_factory, venda_factory):
    from app.hora.services.gerencial import comercial_kpi_service as cks
    from app.hora.models import HoraAprovacaoDesconto
    loja = loja_factory()
    v = venda_factory(loja=loja, itens=[{'preco_final': 1000, 'preco_real': 600}])
    _db.session.add(HoraAprovacaoDesconto(venda_id=v.id, tipo='DESCONTO', status='PENDENTE'))
    _db.session.add(HoraAprovacaoDesconto(venda_id=v.id, tipo='FRETE', status='PENDENTE'))
    _db.session.add(HoraAprovacaoDesconto(venda_id=v.id, tipo='DESCONTO', status='APROVADO'))
    _db.session.flush()
    # escopa à loja única do teste (isola de aprovações residuais no banco local)
    ap = cks.aprovacoes_pendentes(_filtros(lojas_permitidas=[loja.id]))
    assert ap['DESCONTO'] == 1 and ap['FRETE'] == 1 and ap['BRINDE'] == 0


def test_mix_pagamento_soma_por_forma(db, loja_factory, venda_factory):
    from app.hora.services.gerencial import comercial_kpi_service as cks
    from app.hora.models import HoraVendaPagamento
    from app.utils.timezone import agora_brasil_naive
    loja = loja_factory()
    v = venda_factory(loja=loja, itens=[{'preco_final': 1500, 'preco_real': 600}])
    _db.session.add(HoraVendaPagamento(venda_id=v.id, forma_pagamento_hora='PIX', valor=Decimal('1000'), criado_em=agora_brasil_naive()))
    _db.session.add(HoraVendaPagamento(venda_id=v.id, forma_pagamento_hora='CARTAO', valor=Decimal('500'), criado_em=agora_brasil_naive()))
    _db.session.flush()
    mix = {m['forma']: m['valor'] for m in cks.mix_pagamento(_filtros())}
    assert mix['PIX'] == Decimal('1000') and mix['CARTAO'] == Decimal('500')


def test_custo_brindes_soma(db, loja_factory, venda_factory, peca_factory):
    from app.hora.services.gerencial import comercial_kpi_service as cks
    loja = loja_factory()
    peca = peca_factory()
    venda_factory(loja=loja, itens=[{'preco_final': 1000, 'preco_real': 600}], brinde_custo=80, peca=peca)
    assert cks.custo_brindes(_filtros()) == Decimal('80')


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


def test_comercial_renderiza_autenticado(client_admin, loja_factory, venda_factory):
    loja = loja_factory()
    venda_factory(loja=loja, vendedor='ANA', data_venda=date(2026, 6, 15),
                  itens=[{'preco_final': 1000, 'preco_real': 600}])
    r = client_admin.get('/hora/gerencial/comercial?data_ini=2026-06-01&data_fim=2026-06-30')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'Conversão' in body
    assert 'Vendedores' in body
    assert 'Aprovações pendentes' in body
