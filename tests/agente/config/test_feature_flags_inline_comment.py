"""PYTHON-FLASK-XS/XT: env var com comentario inline nao pode derrubar o boot.

Carrega feature_flags.py ISOLADO (so depende de os/logging — nao importa o app)
com os.environ poluido e verifica que os parsers toleram '5.0 # OK' / 'true # ok'
em vez de crashar com ValueError (que derrubava o boot inteiro do app.agente).
"""
import importlib.util
from pathlib import Path

FF_PATH = (
    Path(__file__).resolve().parents[3]
    / "app" / "agente" / "config" / "feature_flags.py"
)


def _load_feature_flags():
    """Carrega o modulo isolado (depende so de os/logging — nao sobe o app)."""
    spec = importlib.util.spec_from_file_location("feature_flags_isolated", FF_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_float_com_comentario_inline_nao_crasha(monkeypatch):
    # Cenario real do Render Dashboard: valor colado com '# OK' verbatim.
    monkeypatch.setenv("AGENT_MAX_BUDGET_USD", "5.0 # OK")
    mod = _load_feature_flags()
    assert mod.MAX_BUDGET_USD == 5.0


def test_int_com_comentario_inline_nao_crasha(monkeypatch):
    monkeypatch.setenv("AGENT_SESSION_SUMMARY_THRESHOLD", "3  # default")
    mod = _load_feature_flags()
    assert mod.SESSION_SUMMARY_THRESHOLD == 3


def test_bool_com_comentario_inline_nao_inverte(monkeypatch):
    # Antes do fix: 'true # ok'.lower() != 'true' -> False silencioso (flag invertida).
    monkeypatch.setenv("AGENT_CONTEXT_CLEARING", "true # ok")
    mod = _load_feature_flags()
    assert mod.USE_CONTEXT_CLEARING is True


def test_valor_invalido_cai_no_default(monkeypatch):
    monkeypatch.setenv("AGENT_MAX_BUDGET_USD", "lixo")
    mod = _load_feature_flags()
    assert mod.MAX_BUDGET_USD == 5.0  # fallback no default, sem crashar


def test_sem_env_usa_default(monkeypatch):
    monkeypatch.delenv("AGENT_MAX_BUDGET_USD", raising=False)
    mod = _load_feature_flags()
    assert mod.MAX_BUDGET_USD == 5.0
