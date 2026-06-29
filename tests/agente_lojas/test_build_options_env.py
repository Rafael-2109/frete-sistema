"""
Regressao F0 (env dict): build_options do AgentLojasClient deve setar `env` com
HOME=/tmp e CLAUDE_CODE_STREAM_CLOSE_TIMEOUT=240000 (espelha o agente web,
app/agente/sdk/client.py:1629-1634).

Por que importa:
  - HOME=/tmp: no Render, $HOME=/opt/render e read-only -> o CLI crasha ao tentar
    salvar .claude.json (ENOENT/EROFS).
  - CLAUDE_CODE_STREAM_CLOSE_TIMEOUT=240000: timeout de hooks/MCP. Sem ele, o
    default do SDK (60s) corta skill pesada (SQL analitico) / subagente
    orientador-loja.
"""
from app.agente_lojas.sdk.client import get_lojas_client


def _build():
    client = get_lojas_client()
    return client.build_options(
        user_id=1,
        user_name='Test',
        perfil='administrador',
        loja_hora_id=None,
    )


class TestEnvDict:
    def test_env_seta_home_tmp(self):
        """HOME=/tmp evita crash do CLI no Render (/opt/render read-only)."""
        o = _build()
        assert (o.env or {}).get('HOME') == '/tmp'

    def test_env_seta_stream_close_timeout_240s(self):
        """240s p/ hooks/MCP (default SDK = 60s corta skill pesada/subagente)."""
        o = _build()
        assert (o.env or {}).get('CLAUDE_CODE_STREAM_CLOSE_TIMEOUT') == '240000'
