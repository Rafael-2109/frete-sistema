"""
Testes da desnormalizacao de equipe_vendas em separacao (otimizacao lista_pedidos).

Contexto: a VIEW pedidos fazia LEFT JOIN com carteira_principal SO para trazer
equipe_vendas (97% do custo / ~710ms->~26ms ao remover). A solucao desnormaliza
equipe_vendas em `separacao` (mesmo padrao de tags_pedido), propagada no sync
do Odoo (AtualizarDadosService) e nos pontos de criacao de Separacao.

Estes testes sao DETERMINISTICOS (sem banco) e protegem o invariante contra
regressao: ninguem pode (a) re-adicionar o JOIN na VIEW, (b) criar Separacao com
tags_pedido sem equipe_vendas, ou (c) remover a propagacao no sync.

A equivalencia funcional v7 == v8 (0 divergencias de equipe por lote) foi
validada no banco local em transacao com rollback durante o desenvolvimento.
"""
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


def _read(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8') as f:
        return f.read()


def _strip_sql_comments(sql):
    """Remove linhas de comentario SQL (-- ...) para checar apenas o codigo."""
    return '\n'.join(l for l in sql.splitlines() if not l.strip().startswith('--'))


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------
def test_model_separacao_tem_equipe_vendas(app):
    """Separacao deve expor a coluna equipe_vendas VARCHAR(100)."""
    from app.separacao.models import Separacao
    col = Separacao.__table__.columns.get('equipe_vendas')
    assert col is not None, "Separacao.equipe_vendas ausente no model"
    assert col.type.length == 100, f"esperado length=100, achei {col.type.length}"
    assert col.nullable is True


# ---------------------------------------------------------------------------
# VIEW v8 + MV: sem JOIN carteira_principal, fonte = s.equipe_vendas
# ---------------------------------------------------------------------------
def test_view_v8_sql_nao_referencia_carteira_principal():
    """O SQL executavel da v8 (VIEW + MV) nao pode referenciar carteira_principal
    (so comentarios podem menciona-la)."""
    code = _strip_sql_comments(_read('scripts/migrations/alterar_view_pedidos_v8.sql'))
    assert 'carteira_principal' not in code, "VIEW/MV v8 ainda referencia carteira_principal!"


def test_view_v8_usa_min_s_equipe_vendas():
    """equipe_vendas deve vir de min(s.equipe_vendas) — 1x na VIEW + 1x na MV."""
    code = _strip_sql_comments(_read('scripts/migrations/alterar_view_pedidos_v8.sql'))
    assert code.count('min(s.equipe_vendas::text)') == 2
    assert 'min(cp.equipe_vendas' not in code
    # CarVia (Partes 2A/2B) preservadas
    assert 'CREATE VIEW pedidos AS' in code
    assert 'CREATE MATERIALIZED VIEW mv_pedidos AS' in code


# ---------------------------------------------------------------------------
# Backfill na migration da coluna
# ---------------------------------------------------------------------------
def test_migration_coluna_tem_add_e_backfill():
    sql = _read('scripts/migrations/add_equipe_vendas_separacao.sql')
    assert 'ADD COLUMN IF NOT EXISTS equipe_vendas' in sql
    # backfill replica o JOIN da v7 (num_pedido + cod_produto)
    assert 'UPDATE separacao s' in sql
    assert 's.num_pedido = cp.num_pedido' in sql
    assert 's.cod_produto = cp.cod_produto' in sql


# ---------------------------------------------------------------------------
# Propagacao: paridade tags_pedido <-> equipe_vendas nos callsites de criacao
# ---------------------------------------------------------------------------
CALLSITES_CRIACAO = [
    'app/carteira/utils/separacao_utils.py',
    'app/carteira/routes/separacao_api.py',
    'app/pedidos/services/sincronizar_items_service.py',
]


def test_paridade_tags_pedido_equipe_vendas_nos_callsites():
    """Todo ponto de criacao de Separacao que copia tags_pedido DEVE copiar
    equipe_vendas (mesmo padrao). Anti-regressao: impede adicionar um sem o outro."""
    for rel in CALLSITES_CRIACAO:
        src = _read(rel)
        n_tags = len(re.findall(r'tags_pedido\s*=', src))
        n_equipe = len(re.findall(r'equipe_vendas\s*=', src))
        assert n_tags == n_equipe, (
            f"{rel}: tags_pedido= ({n_tags}) != equipe_vendas= ({n_equipe}) "
            "— criacao de Separacao deve copiar ambos"
        )


def test_sync_odoo_propaga_equipe_vendas():
    """AtualizarDadosService (sync pos-Odoo) deve atualizar equipe_vendas a
    partir de carteira_principal — nucleo da estrategia (sync > JOIN)."""
    src = _read('app/carteira/services/atualizar_dados_service.py')
    assert 'separacao.equipe_vendas = item_produto.equipe_vendas' in src
    assert "campos_alterados.append('equipe_vendas')" in src
