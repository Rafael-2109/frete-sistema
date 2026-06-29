"""
F1.5(c): o fork NUNCA injeta o empresa_briefing Nacom (contrato isolamento HORA).

empresa_briefing_path e herdado de AgentSettings mas NAO e lido pelo
AgentLojasClient (_build_system_prompt concatena so preset + system_prompt).
Mantido vazio de proposito — apontar para o briefing Nacom quebraria o
isolamento se alguem "corrigir" _build_system_prompt para inclui-lo.
"""
from app.agente_lojas.sdk.client import get_lojas_client


def test_empresa_briefing_path_vazio():
    assert get_lojas_client().settings.empresa_briefing_path == ''


def test_system_prompt_nao_depende_do_briefing_path(monkeypatch):
    """Prova comportamental: mudar o path NAO altera o prompt (nao e lido)."""
    client = get_lojas_client()
    sp_antes = client._build_system_prompt()
    # Apontar para um arquivo real qualquer; se fosse lido, o prompt mudaria.
    monkeypatch.setattr(client.settings, 'empresa_briefing_path', 'README.md')
    assert client._build_system_prompt() == sp_antes
