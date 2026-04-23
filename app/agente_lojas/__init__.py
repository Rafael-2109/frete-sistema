"""
Agente Lojas HORA — Claude Agent SDK

Agente dedicado ao pessoal das Lojas Motochefe (HORA), isolado do agente
logistico Nacom Goya (`app/agente/`). Compartilha infra do SDK mas tem:

- System prompt proprio (`prompts/system_prompt.md`)
- Whitelist de skills/subagents especificos
- Escopo por loja (`loja_hora_id`) injetado no contexto
- Sessoes e memorias particionadas via coluna `agente='lojas'`

Autorizacao: flag `sistema_lojas=True` OU `perfil='administrador'`.

Versao: 0.1 (M0 — esqueleto)
Data: 2026-04-22
"""

from .routes import agente_lojas_bp


def init_app(app):
    """Registra blueprint do agente Lojas HORA na aplicacao Flask."""
    app.register_blueprint(agente_lojas_bp)
    app.logger.info(
        "[AGENTE_LOJAS] Modulo inicializado | agente='lojas'"
    )


__all__ = ['agente_lojas_bp', 'init_app']
