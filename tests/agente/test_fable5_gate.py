"""Testes do gate de modelo Fable 5 (opt-in por user_id).

Cobre app/agente/config/feature_flags.py:
  - is_fable5_allowed(user_id): allowlist por user_id, fail-closed
  - _parse_allowed_user_ids_csv: parse do CSV da env var

Contexto (2026-06-10): `claude-fable-5` e' o modelo mais caro; a opcao so' e'
exposta na UI (chat.html, via `pode_usar_fable5`) e aceita no backend (chat.py,
gate defense-in-depth) para user_ids na whitelist AGENT_FABLE5_ALLOWED_USER_IDS
(default "1" = Rafael). Espelha o padrao de ESTOQUE_RESTRICAO_ALLOWED_USER_IDS.
"""
import pytest

from app.agente.config import feature_flags as ff
from app.agente.config.feature_flags import (
    FABLE5_MODEL_ID,
    _parse_allowed_user_ids_csv,
    is_fable5_allowed,
)


@pytest.fixture(autouse=True)
def _whitelist_default(monkeypatch):
    """Forca a whitelist default {1} por teste (isola de env var local)."""
    monkeypatch.setattr(ff, "FABLE5_ALLOWED_USER_IDS", {1}, raising=False)
    yield


def test_model_id_constante():
    assert FABLE5_MODEL_ID == "claude-fable-5"


class TestIsFable5Allowed:
    def test_autorizado_int(self):
        assert is_fable5_allowed(1) is True

    def test_autorizado_str_numerica(self):
        # request JSON / contextvar podem trazer user_id como string
        assert is_fable5_allowed("1") is True

    def test_nao_autorizado(self):
        assert is_fable5_allowed(99) is False

    def test_none_fail_closed(self):
        # current_user sem id (anonimo) -> NUNCA libera modelo caro
        assert is_fable5_allowed(None) is False

    def test_str_invalida_fail_closed(self):
        assert is_fable5_allowed("abc") is False

    def test_respeita_whitelist_ampliada(self, monkeypatch):
        monkeypatch.setattr(ff, "FABLE5_ALLOWED_USER_IDS", {1, 55, 62}, raising=False)
        assert is_fable5_allowed(55) is True
        assert is_fable5_allowed(62) is True
        assert is_fable5_allowed(7) is False


class TestParseCsv:
    def test_csv_simples(self):
        assert _parse_allowed_user_ids_csv("1,55") == {1, 55}

    def test_espacos_e_vazios(self):
        assert _parse_allowed_user_ids_csv(" 1 , , 55 ,") == {1, 55}

    def test_invalido_ignorado(self):
        # typo na env var nao deve explodir; valor invalido e' descartado
        assert _parse_allowed_user_ids_csv("1,foo,55") == {1, 55}

    def test_vazio(self):
        assert _parse_allowed_user_ids_csv("") == set()
