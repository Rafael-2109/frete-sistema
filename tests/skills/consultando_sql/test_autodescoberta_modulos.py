"""Testes da auto-descoberta de modulos + allow-list de orfaos vivos + fix do bug
getdoc herdado (subsistema S0b — complemento do S0 gerador idempotente).

Causa raiz (verificada): a lista hardcoded `model_modules` esquecia modulos novos
(ex: app.teams.models -> schema de teams_tasks defasado). Fix: `_discover_model_modules`
varre app/ por NOME (models.py / models_*.py / *_models.py / pacote models/) E confirma
por CONTEUDO (`__tablename__` presente) — unida a um legado de garantia (nunca perde o
que ja funcionava). Falsos positivos que casam o nome mas NAO sao ORM (utils/ml_models,
agente/sdk/model_router, financeiro/parsers/models, carteira/models_adapter_presep) sao
excluidos pelo filtro de conteudo.

Allow-list ORFAOS_VIVOS_PRESERVAR: verificada contra PROD (MCP Render 2026-06-07) — as
5 "orfas" EXISTEM no banco; 4 sem modelo ORM nunca devem ser apagadas por prune.

Bug getdoc: `inspect.getdoc` herda a docstring de `db.Model` via MRO quando a classe nao
tem docstring propria -> injetava "The base class ..." como descricao de tabela (5
tabelas afetadas ja na main). Fix usa `__doc__` direto.

Determinístico, SEM create_app/DB (invariante 6 do MASTER).
"""
import importlib.util
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
_SCRIPT = _REPO / ".claude/skills/consultando-sql/scripts/generate_schemas.py"


def _load():
    spec = importlib.util.spec_from_file_location("generate_schemas_s0b", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["generate_schemas_s0b"] = mod
    spec.loader.exec_module(mod)
    return mod


gs = _load()


# ---------------------------------------------------------------------------
# auto-descoberta de modulos
# ---------------------------------------------------------------------------

def test_descobre_teams_models():
    """A causa raiz: app.teams.models faltava -> teams_tasks defasava."""
    assert "app.teams.models" in gs._discover_model_modules()


def test_descobre_embeddings_orm():
    """embeddings/models.py tem 12 tabelas ORM (__tablename__) -> deve entrar."""
    assert "app.embeddings.models" in gs._discover_model_modules()


def test_exclui_falsos_positivos_nao_orm():
    """Casam o padrao de nome mas NAO tem __tablename__ -> filtro de conteudo exclui."""
    d = gs._discover_model_modules()
    for fp in (
        "app.utils.ml_models",
        "app.agente.sdk.model_router",
        "app.financeiro.parsers.models",
        "app.carteira.models_adapter_presep",
    ):
        assert fp not in d, f"falso positivo nao filtrado: {fp}"


def test_superset_do_legado():
    """Amostra de modulos legados (inclusive nomes atipicos) deve estar na descoberta."""
    d = gs._discover_model_modules()
    for m in (
        "app.agente.models",
        "app.carteira.models_alertas",      # models_*
        "app.fretes.email_models",          # *_models
        "app.motochefe.models.cadastro",    # pacote models/
        "app.pedidos.integracao_odoo.models",
    ):
        assert m in d, f"legado perdido na descoberta: {m}"


def test_descoberta_deterministica():
    """Duas chamadas retornam o mesmo conjunto (compativel com idempotencia S0)."""
    assert gs._discover_model_modules() == gs._discover_model_modules()


# ---------------------------------------------------------------------------
# allow-list de orfaos vivos (preservacao)
# ---------------------------------------------------------------------------

def test_orfaos_vivos_preservar_contem_os_4():
    assert gs.ORFAOS_VIVOS_PRESERVAR == {
        "claude_session_store",
        "carvia_sessoes_cotacao",
        "carvia_sessao_demandas",
        "carvia_aprovacoes_subcontrato",
    }


def test_prune_preserva_orfao_vivo():
    """Mesmo com --prune-orphans + import completo, NAO apaga orfao vivo do PROD."""
    res = gs._resolve_orphans_to_delete(
        ["claude_session_store", "tabela_removida_xyz"],
        import_complete=True,
        do_prune=True,
    )
    assert "claude_session_store" not in res
    assert "tabela_removida_xyz" in res


# ---------------------------------------------------------------------------
# fix do bug getdoc herdado
# ---------------------------------------------------------------------------

class _BaseModel:
    """The base class of the :attr:`.SQLAlchemy.Model` declarative model class."""


class _SemDocstring(_BaseModel):
    pass


class _ComDocstring(_BaseModel):
    """Pedidos de venda da carteira do cliente."""


def test_docstring_nao_herda_da_base():
    """getdoc herdava a docstring da base; __doc__ nao -> '' p/ classe sem doc propria."""
    assert gs.extract_class_docstring(_SemDocstring) == ""


def test_docstring_propria_preservada():
    """Classe COM docstring propria continua sendo extraida."""
    assert "Pedidos de venda" in gs.extract_class_docstring(_ComDocstring)
