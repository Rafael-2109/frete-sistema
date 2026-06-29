"""MOTOR UNICO — ETAPA 1.1: get_settings parametrizado por perfil de agente.

Invariantes:
- default 'web' preserva identidade singleton (byte-identico p/ os ~8 callers sem arg);
- perfil 'lojas' retorna AgentLojasSettings (prompts proprios, SEM briefing Nacom);
- fail-closed: agente_id desconhecido NAO cai num default silencioso (D3).
"""
import pytest


def test_get_settings_default_e_web_sao_a_mesma_instancia():
    from app.agente.config.settings import get_settings, AgentSettings, reload_settings
    reload_settings()  # estado limpo
    s_default = get_settings()
    s_web = get_settings('web')
    assert isinstance(s_default, AgentSettings)
    assert s_default is s_web  # default e 'web' = MESMA instancia (singleton preservado)
    assert s_default.system_prompt_path == "app/agente/prompts/system_prompt.md"
    assert s_default.empresa_briefing_path == "app/agente/config/empresa_briefing.md"


def test_get_settings_lojas_retorna_perfil_isolado():
    from app.agente.config.settings import get_settings
    s = get_settings('lojas')
    assert s.__class__.__name__ == 'AgentLojasSettings'
    assert s.system_prompt_path == "app/agente_lojas/prompts/system_prompt.md"
    assert s.operational_preset_path == "app/agente_lojas/prompts/preset_operacional.md"
    assert s.empresa_briefing_path == ""  # isolamento HORA: nao injeta briefing Nacom


def test_get_settings_web_e_lojas_sao_distintos():
    from app.agente.config.settings import get_settings
    assert get_settings('web') is not get_settings('lojas')


def test_get_settings_lojas_e_singleton_por_perfil():
    from app.agente.config.settings import get_settings
    assert get_settings('lojas') is get_settings('lojas')


def test_get_settings_agente_desconhecido_falha_fechado():
    from app.agente.config.settings import get_settings
    with pytest.raises(ValueError):
        get_settings('inexistente')
