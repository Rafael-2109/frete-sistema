"""
Utilitários de prompts do Claude AI Lite.

FUNÇÕES ATIVAS:
- _carregar_aprendizados_usuario(): Carrega conhecimento aprendido via chat
- _carregar_codigos_aprendidos(): Carrega códigos do IA Trainer

NOTA: A função gerar_prompt_classificacao() foi REMOVIDA (27/11/2025).
A classificação agora é feita pelo IntelligentExtractor (intelligent_extractor.py).

Atualizado: 27/11/2025 - Remoção de código morto
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def _carregar_aprendizados_usuario(usuario_id: int = None) -> str:
    """
    Carrega aprendizados do ClaudeAprendizado (caderno de dicas).

    Inclui aprendizados globais E do usuário específico.
    Estes são conhecimentos conceituais que ajudam o classificador
    a entender melhor o contexto do negócio.

    USADO POR:
    - orchestrator.py
    - auto_loader.py

    Args:
        usuario_id: ID do usuário (opcional, para aprendizados personalizados)

    Returns:
        String formatada com aprendizados relevantes para classificação
    """
    try:
        from ..models import ClaudeAprendizado

        # Busca aprendizados ativos (globais + usuario)
        query = ClaudeAprendizado.query.filter_by(ativo=True)

        if usuario_id:
            # Globais OU do usuário específico
            from sqlalchemy import or_
            query = query.filter(
                or_(
                    ClaudeAprendizado.usuario_id.is_(None),  # Globais
                    ClaudeAprendizado.usuario_id == usuario_id  # Do usuário
                )
            )
        else:
            # Apenas globais
            query = query.filter(ClaudeAprendizado.usuario_id.is_(None))

        aprendizados = query.order_by(
            ClaudeAprendizado.prioridade.desc(),
            ClaudeAprendizado.criado_em.desc()
        ).limit(30).all()  # Limita para não sobrecarregar o prompt

        if not aprendizados:
            return ''

        # Agrupa por categoria para melhor organização
        por_categoria = {}
        for a in aprendizados:
            cat = a.categoria.upper()
            if cat not in por_categoria:
                por_categoria[cat] = []
            por_categoria[cat].append(a.valor)

        # Formata para incluir no prompt de classificação
        linhas = ["\n=== CONHECIMENTO DO NEGOCIO (aprendido via chat) ==="]
        linhas.append("Use estas informações para entender melhor as perguntas:")
        for categoria, valores in por_categoria.items():
            linhas.append(f"\n[{categoria}]")
            for valor in valores:
                linhas.append(f"- {valor}")
        linhas.append("\n=== FIM DO CONHECIMENTO APRENDIDO ===\n")

        return "\n".join(linhas)

    except Exception as e:
        logger.debug(f"[INTENT_PROMPT] ClaudeAprendizado nao disponivel: {e}")
        return ''


def _carregar_codigos_aprendidos() -> dict:
    """
    Carrega códigos aprendidos do IA Trainer (receitas prontas).

    Returns:
        Dict com prompts, conceitos e entidades formatados
    """
    try:
        from ..ia_trainer.services.codigo_loader import (
            gerar_contexto_prompts,
            gerar_contexto_conceitos,
            gerar_contexto_entidades
        )

        return {
            'prompts': gerar_contexto_prompts(),
            'conceitos': gerar_contexto_conceitos(),
            'entidades': gerar_contexto_entidades()
        }
    except Exception as e:
        logger.debug(f"[INTENT_PROMPT] Codigos aprendidos nao disponiveis: {e}")
        return {'prompts': '', 'conceitos': '', 'entidades': ''}


# =============================================================================
# CÓDIGO REMOVIDO (27/11/2025)
# =============================================================================
# A função gerar_prompt_classificacao() foi REMOVIDA.
# Motivo: Era código legado não utilizado no fluxo principal.
# A classificação é feita pelo IntelligentExtractor (intelligent_extractor.py)
# que usa ToolRegistry para carregar capabilities dinamicamente.
# =============================================================================
