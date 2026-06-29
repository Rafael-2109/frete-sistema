"""Infra de runtime do subprocesso CLI do Agent SDK — PURA, sem dominio Nacom.

Consumida por AMBOS os clients (agente web `app/agente/sdk/client.py` e agente de
lojas `app/agente_lojas/sdk/client.py`) para eliminar a duplicacao do env dict
que driftou (o fork ficou sem o env por meses — ver F0 do plano de convergencia).

NAO importar `client.py` nem nada que puxe `AgentClient`/pool aqui: este modulo
precisa ser importavel de submodulo (`from app.agente.sdk.sdk_runtime import ...`)
sem side effects, inclusive pelo agente_lojas (contrato de isolamento HORA).
"""


def build_subprocess_env() -> dict:
    """Env vars do subprocesso CLI do Agent SDK.

    - ``HOME=/tmp``: no Render ``$HOME=/opt/render`` e read-only e o CLI crasha ao
      salvar ``.claude.json`` (ENOENT/EROFS). ``/tmp`` e sempre gravavel.
    - ``CLAUDE_CODE_STREAM_CLOSE_TIMEOUT=240000`` (ms): timeout de hooks/MCP.
      Default do SDK = 60s, que corta skill pesada (SQL analitico, Odoo) /
      subagente.

    Retorna um dict NOVO a cada chamada (cada client recebe sua copia; mutar uma
    nao contamina a outra).
    """
    return {
        "CLAUDE_CODE_STREAM_CLOSE_TIMEOUT": "240000",
        "HOME": "/tmp",
    }
