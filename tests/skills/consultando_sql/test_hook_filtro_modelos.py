"""Salvaguarda do filtro do hook lembrar-regenerar-schemas (S0).

Garante que o hook PostToolUse dispara para TODO arquivo de modelo SQLAlchemy
(definido por __tablename__), varrendo os arquivos reais de app/. Nasceu de uma
regressão real: o filtro antigo (`endswith("models.py")`) perdia models_*.py,
*_models.py (email_models.py, frota_models.py) e o diretório models/.

Determinístico, sem DB. Usa o próprio app/ do repositório como fonte de verdade.
"""
import importlib.util
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
_HOOK = _REPO / ".claude/hooks/lembrar-regenerar-schemas.py"


def _load_hook():
    spec = importlib.util.spec_from_file_location("lembrar_regenerar_schemas_mod", _HOOK)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["lembrar_regenerar_schemas_mod"] = mod
    spec.loader.exec_module(mod)
    return mod


hook = _load_hook()


def _arquivos_de_modelo():
    """Todos os .py em app/ que definem __tablename__ (fonte de verdade viva)."""
    out = subprocess.run(
        ["grep", "-rln", "__tablename__", str(_REPO / "app"), "--include=*.py"],
        capture_output=True, text=True,
    ).stdout
    return [l for l in out.splitlines() if l.strip()]


def test_hook_captura_todos_os_arquivos_de_modelo_reais():
    files = _arquivos_de_modelo()
    assert len(files) > 50, f"sanity: poucos arquivos de modelo encontrados ({len(files)})"
    perdidos = [f for f in files if not hook._is_model_file(f)]
    assert perdidos == [], f"o hook NÃO dispararia para estes modelos: {perdidos}"


def test_hook_filtro_casos_positivos():
    for p in [
        "app/x/models.py",
        "app/carteira/models_alertas.py",      # prefixo models_
        "app/fretes/email_models.py",          # sufixo _models
        "app/fretes/frota_models.py",          # sufixo _models
        "app/carvia/models/admin.py",          # diretório models/
        "app/x/model.py",                      # singular
        "app/x/model_foo.py",                  # singular prefixo
        "app/x/model/foo.py",                  # diretório model/ singular
        "/abs/CAMINHO/Models.py",              # case-insensitive
    ]:
        assert hook._is_model_file(p), f"deveria capturar: {p}"


def test_hook_filtro_casos_negativos():
    for p in [
        "app/x/routes.py",
        "app/x/services.py",
        "app/x/models.txt",                    # não-.py
        "app/x/test_models.py",                # teste, não modelo
        "app/x/__init__.py",
    ]:
        assert not hook._is_model_file(p), f"NÃO deveria capturar: {p}"
