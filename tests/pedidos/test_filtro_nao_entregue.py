"""Regressao do filtro "Apenas NF nao entregues" (lista_pedidos + NF CarVia).

Contexto (2026-06-22): toggle default ON que oculta pedidos/NFs cuja entrega
(EntregaMonitorada.entregue) ja foi realizada. Cobre o parsing do parametro e a
forma do filtro SQL (NOT EXISTS em pedidos / NOT IN na CarVia), sem depender de
dados reais — so a construcao da query.
"""
from app.pedidos.services.lista_service import ListaPedidosService as Svc
from app.pedidos.models import Pedido


# --- Parsing do parametro (puro) ---

def test_parse_default_on():
    """Ausente => filtro LIGADO (default)."""
    assert Svc._parse_filter_params({})['apenas_nao_entregues'] is True


def test_parse_zero_desliga():
    """'nao_entregue=0' => desliga."""
    assert Svc._parse_filter_params({'nao_entregue': '0'})['apenas_nao_entregues'] is False


def test_parse_um_liga():
    """Qualquer valor != '0' (inclusive '1') => ligado."""
    assert Svc._parse_filter_params({'nao_entregue': '1'})['apenas_nao_entregues'] is True


# --- Forma do filtro SQL ---

def test_filtro_pedidos_on_gera_not_exists(app):
    with app.app_context():
        q = Svc._apply_apenas_nao_entregues(Pedido.query, True)
        sql = str(q.statement.compile(compile_kwargs={'literal_binds': True}))
    assert 'entregas_monitoradas' in sql
    assert 'NOT (EXISTS' in sql or 'NOT EXISTS' in sql


def test_filtro_pedidos_off_nao_altera(app):
    with app.app_context():
        q = Svc._apply_apenas_nao_entregues(Pedido.query, False)
        sql = str(q.statement.compile())
    assert 'entregas_monitoradas' not in sql


def test_filtro_carvia_not_in_entregas(app):
    with app.app_context():
        from app import db
        from app.carvia.models import CarviaNf
        from app.monitoramento.models import EntregaMonitorada
        sub = db.session.query(EntregaMonitorada.numero_nf).filter(
            EntregaMonitorada.entregue.is_(True),
            EntregaMonitorada.origem == 'CARVIA',
        )
        q = db.session.query(CarviaNf).filter(CarviaNf.numero_nf.notin_(sub))
        sql = str(q.statement.compile(compile_kwargs={'literal_binds': True}))
    assert 'NOT IN' in sql
    assert 'entregas_monitoradas' in sql
