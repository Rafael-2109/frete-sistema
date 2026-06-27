"""Área de relatórios (F5): catálogo semântico, builder curado e export."""
from datetime import date
from decimal import Decimal

import pytest

from app import db as _db
from app.hora.services.gerencial.filtros import Filtros


def _filtros(lojas_permitidas=None, granularidade='dia'):
    return Filtros(data_ini=date(2026, 6, 1), data_fim=date(2026, 6, 30),
                   granularidade=granularidade, loja_id=None,
                   lojas_permitidas=lojas_permitidas)


# ───────────────────────── Catálogo semântico ───────────────────────────────

def test_validar_aceita_whitelist():
    from app.hora.services.gerencial import relatorio_catalogo as rc
    ok, erro = rc.validar_selecao(['loja'], ['receita', 'unidades'])
    assert ok and erro is None


def test_validar_rejeita_dimensao_desconhecida():
    from app.hora.services.gerencial import relatorio_catalogo as rc
    ok, erro = rc.validar_selecao(['hackeado'], ['receita'])
    assert not ok and erro


def test_validar_exige_metrica():
    from app.hora.services.gerencial import relatorio_catalogo as rc
    ok, erro = rc.validar_selecao(['loja'], [])
    assert not ok and erro


def test_validar_rejeita_metrica_desconhecida():
    from app.hora.services.gerencial import relatorio_catalogo as rc
    ok, erro = rc.validar_selecao(['loja'], ['drop_table'])
    assert not ok and erro


# ───────────────────────── Builder ──────────────────────────────────────────

def test_builder_agrupa_por_loja(db, loja_factory, venda_factory):
    from app.hora.services.gerencial import relatorio_service as rs
    loja = loja_factory()
    venda_factory(loja=loja, itens=[{'preco_final': 1000, 'preco_real': 600},
                                    {'preco_final': 500, 'preco_real': 300}])
    res = rs.gerar_builder(['loja'], ['receita', 'unidades'], _filtros(lojas_permitidas=[loja.id]))
    assert len(res['linhas']) == 1
    linha = res['linhas'][0]
    assert linha['receita'] == Decimal('1500')   # soma preco_final dos itens
    assert linha['unidades'] == 2
    assert [c['key'] for c in res['colunas']] == ['_dim', 'receita', 'unidades']


def test_builder_rejeita_fora_catalogo(db, loja_factory):
    from app.hora.services.gerencial import relatorio_service as rs
    with pytest.raises(ValueError):
        rs.gerar_builder(['hackeado'], ['receita'], _filtros())


def test_builder_reaplica_escopo_loja(db, loja_factory, venda_factory):
    from app.hora.services.gerencial import relatorio_service as rs
    loja_a = loja_factory()
    loja_b = loja_factory()
    venda_factory(loja=loja_a, itens=[{'preco_final': 1000, 'preco_real': 600}])
    venda_factory(loja=loja_b, itens=[{'preco_final': 9000, 'preco_real': 600}])
    res = rs.gerar_builder(['loja'], ['receita'], _filtros(lojas_permitidas=[loja_a.id]))
    assert len(res['linhas']) == 1
    assert res['linhas'][0]['receita'] == Decimal('1000')  # loja_b não vaza


def test_predefinido_margem_por_modelo(db, loja_factory, venda_factory):
    from app.hora.services.gerencial import relatorio_service as rs
    loja = loja_factory()
    venda_factory(loja=loja, itens=[{'preco_final': 1000, 'preco_real': 600}])
    res = rs.gerar_predefinido('margem_por_modelo', _filtros(lojas_permitidas=[loja.id]))
    assert res['linhas']
    assert any(l.get('margem_rs') == Decimal('400') for l in res['linhas'])


def test_predefinidos_especiais_geram_sem_erro(db, loja_factory, venda_factory):
    """Os 3 relatórios de grão não-venda (comissão/aging/divergências) geram."""
    from app.hora.services.gerencial import relatorio_service as rs
    loja = loja_factory()
    venda_factory(loja=loja, itens=[{'preco_final': 1000, 'preco_real': 600}])
    for slug in ('comissao_por_vendedor', 'aging_estoque', 'divergencias_recebimento'):
        res = rs.gerar_predefinido(slug, _filtros(lojas_permitidas=[loja.id]))
        assert 'colunas' in res and 'linhas' in res
        assert res['titulo']


def test_builder_dim_cor_e_metrica_desconto_pct(db, loja_factory, venda_factory):
    from app.hora.services.gerencial import relatorio_service as rs
    loja = loja_factory()
    venda_factory(loja=loja, itens=[{'preco_final': 900, 'preco_tabela': 1000, 'preco_real': 600}])
    res = rs.gerar_builder(['cor'], ['unidades', 'desconto_pct'], _filtros(lojas_permitidas=[loja.id]))
    assert res['linhas']
    assert [c['key'] for c in res['colunas']] == ['_dim', 'unidades', 'desconto_pct']


def test_galeria_tem_os_5_relatorios_do_spec(db):
    from app.hora.services.gerencial import relatorio_service as rs
    slugs = {r['slug'] for r in rs.RELATORIOS_PREDEFINIDOS}
    assert {'vendas_por_loja', 'margem_por_modelo', 'comissao_por_vendedor',
            'aging_estoque', 'divergencias_recebimento'} <= slugs


# ───────────────────────── Export ───────────────────────────────────────────

def test_exportar_xlsx_gera_bytes(db, loja_factory, venda_factory):
    from app.hora.services.gerencial import relatorio_service as rs
    loja = loja_factory()
    venda_factory(loja=loja, itens=[{'preco_final': 1000, 'preco_real': 600}])
    res = rs.gerar_builder(['loja'], ['receita'], _filtros(lojas_permitidas=[loja.id]))
    conteudo = rs.exportar(res, 'xlsx')
    assert isinstance(conteudo, (bytes, bytearray))
    assert len(conteudo) > 100


# ───────────────────────── Smoke das telas / rotas ──────────────────────────

def test_relatorios_galeria_renderiza(client_admin, loja_factory):
    loja_factory()
    r = client_admin.get('/hora/gerencial/relatorios')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'Relatórios prontos' in body
    assert 'Construtor de relatórios' in body


def test_relatorios_export_download(client_admin, loja_factory, venda_factory):
    loja = loja_factory()
    venda_factory(loja=loja, itens=[{'preco_final': 1000, 'preco_real': 600}])
    r = client_admin.get(
        f'/hora/gerencial/relatorios/export?relatorio=vendas_por_loja'
        f'&loja_id={loja.id}&data_ini=2026-06-01&data_fim=2026-06-30&formato=xlsx'
    )
    assert r.status_code == 200
    assert 'attachment' in r.headers.get('Content-Disposition', '')
    assert len(r.data) > 100


def test_relatorios_exige_permissao_propria(db, app, loja_factory):
    """Gerente com 'gerencial' mas sem 'gerencial_relatorios' acessa dashboards,
    NÃO a área de relatórios (decisão 4 — permissão separada)."""
    import uuid
    from werkzeug.security import generate_password_hash
    from app.auth.models import Usuario
    from app.hora.models import HoraUserPermissao
    loja_factory()
    u = Usuario(nome='Gerente Loja', email=f'g-{uuid.uuid4().hex[:10]}@t.local',
                perfil='vendedor', status='ativo', sistema_lojas=True)
    u.senha_hash = generate_password_hash('x')
    _db.session.add(u)
    _db.session.flush()
    _db.session.add(HoraUserPermissao(user_id=u.id, modulo='gerencial', pode_ver=True))
    _db.session.flush()
    c = app.test_client()
    with c.session_transaction() as sess:
        sess['_user_id'] = str(u.id)
    # dashboards (gerencial/ver) -> acessa
    assert c.get('/hora/gerencial/executivo?data_ini=2026-06-01&data_fim=2026-06-30').status_code == 200
    # relatórios (gerencial_relatorios/ver) -> bloqueado
    assert c.get('/hora/gerencial/relatorios').status_code in (302, 403)
