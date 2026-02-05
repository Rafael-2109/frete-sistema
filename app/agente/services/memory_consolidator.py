"""
Consolidação Periódica de Memórias via Haiku.

Quando um usuário acumula muitas memórias (>15 arquivos ou >6000 chars totais),
consolida em resumos compactos para manter a injeção eficiente.

Custo estimado: ~$0.002 por consolidação (~4K input + ~800 output Haiku).
Frequência: ~1x por semana por usuário ativo.

Uso:
    Este módulo é chamado por memory_mcp_tool.py após cada save_memory.
    Verifica thresholds e consolida se necessário.

    A consolidação é best-effort: falhas são logadas mas não propagadas.
    Nunca bloqueia o salvamento de memórias nem o stream SSE.
    Memórias originais são preservadas (renomeadas com prefixo _archived_).
"""

import logging
from collections import defaultdict
from typing import Dict, Any, Optional

import anthropic

logger = logging.getLogger(__name__)

HAIKU_MODEL = "claude-haiku-4-5-20251001"

CONSOLIDATION_PROMPT = """Consolide estas {count} notas de memória de um usuário em UM resumo conciso.

REGRAS:
- Mantenha TODOS os fatos, preferências, regras e correções — NÃO perca informação
- Elimine apenas redundâncias, reformulações e informações duplicadas
- Organize por tópico (preferências, regras, correções, contexto)
- Formato: texto corrido organizado, máximo 800 caracteres
- Linguagem: português brasileiro
- NÃO adicione interpretações ou suposições — apenas o que está escrito

NOTAS PARA CONSOLIDAR:
{memories}

RESUMO CONSOLIDADO:"""

# Diretórios protegidos — NUNCA consolidar estes arquivos
PROTECTED_PATHS = {
    "/memories/user.xml",
    "/memories/preferences.xml",
}

# Diretórios candidatos à consolidação
CONSOLIDATION_DIRS = [
    "/memories/learned",
    "/memories/corrections",
    "/memories/context",
]


def maybe_consolidate(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Verifica se memórias do usuário excedem thresholds e consolida se necessário.

    Chamado após cada save_memory como best-effort.
    NÃO propaga exceções — falhas são logadas silenciosamente.

    Args:
        user_id: ID do usuário no banco

    Returns:
        Dict com métricas da consolidação ou None se não necessário
    """
    try:
        from ..config.feature_flags import (
            USE_MEMORY_CONSOLIDATION,
            MEMORY_CONSOLIDATION_THRESHOLD_FILES,
            MEMORY_CONSOLIDATION_THRESHOLD_CHARS,
            MEMORY_CONSOLIDATION_MIN_GROUP,
        )

        if not USE_MEMORY_CONSOLIDATION:
            return None

        return _consolidate_if_needed(
            user_id=user_id,
            threshold_files=MEMORY_CONSOLIDATION_THRESHOLD_FILES,
            threshold_chars=MEMORY_CONSOLIDATION_THRESHOLD_CHARS,
            min_group=MEMORY_CONSOLIDATION_MIN_GROUP,
        )

    except Exception as e:
        logger.warning(f"[MEMORY_CONSOLIDATOR] Erro (ignorado): {e}")
        return None


def _consolidate_if_needed(
    user_id: int,
    threshold_files: int = 15,
    threshold_chars: int = 6000,
    min_group: int = 3,
) -> Optional[Dict[str, Any]]:
    """
    Core da consolidação. Verifica thresholds e executa.

    Args:
        user_id: ID do usuário
        threshold_files: Máximo de arquivos antes de consolidar
        threshold_chars: Máximo de chars totais antes de consolidar
        min_group: Mínimo de arquivos em um diretório para consolidar

    Returns:
        Dict com métricas ou None
    """
    from ..models import AgentMemory
    from app import db

    # 1. Carregar todas as memórias do usuário (exceto diretórios)
    memories = AgentMemory.query.filter_by(
        user_id=user_id,
        is_directory=False,
    ).all()

    if not memories:
        return None

    # 2. Verificar thresholds
    total_files = len(memories)
    total_chars = sum(len(m.content or "") for m in memories)

    if total_files <= threshold_files and total_chars <= threshold_chars:
        logger.debug(
            f"[MEMORY_CONSOLIDATOR] Abaixo do threshold: "
            f"{total_files} arquivos, {total_chars} chars"
        )
        return None

    logger.info(
        f"[MEMORY_CONSOLIDATOR] Threshold excedido: "
        f"{total_files} arquivos (max {threshold_files}), "
        f"{total_chars} chars (max {threshold_chars}). "
        f"Iniciando consolidação para user_id={user_id}"
    )

    # 3. Agrupar memórias por diretório
    groups: Dict[str, list] = defaultdict(list)
    for mem in memories:
        if mem.path in PROTECTED_PATHS:
            continue

        # Extrair diretório pai
        parts = mem.path.rsplit("/", 1)
        if len(parts) == 2:
            parent_dir = parts[0]
        else:
            continue

        # Só consolidar diretórios candidatos
        if parent_dir in CONSOLIDATION_DIRS:
            groups[parent_dir].append(mem)

    # 4. Consolidar cada grupo que excede min_group
    consolidated_count = 0
    archived_count = 0
    chars_saved = 0

    for dir_path, dir_memories in groups.items():
        if len(dir_memories) < min_group:
            logger.debug(
                f"[MEMORY_CONSOLIDATOR] Pulando {dir_path}: "
                f"{len(dir_memories)} arquivos (min {min_group})"
            )
            continue

        # Excluir consolidated.xml existente (se houver) do grupo
        to_consolidate = [
            m for m in dir_memories
            if not m.path.endswith("/consolidated.xml")
        ]

        if len(to_consolidate) < min_group:
            continue

        result = _consolidate_group(user_id, dir_path, to_consolidate)
        if result:
            consolidated_count += 1
            archived_count += result["archived"]
            chars_saved += result["chars_saved"]

    if consolidated_count > 0:
        db.session.commit()
        logger.info(
            f"[MEMORY_CONSOLIDATOR] Consolidação concluída: "
            f"{consolidated_count} grupos, "
            f"{archived_count} arquivos arquivados, "
            f"{chars_saved} chars economizados"
        )

    return {
        "consolidated": consolidated_count,
        "archived": archived_count,
        "chars_saved": chars_saved,
    } if consolidated_count > 0 else None


def _consolidate_group(
    user_id: int,
    dir_path: str,
    memories: list,
) -> Optional[Dict[str, Any]]:
    """
    Consolida um grupo de memórias em um único arquivo via Haiku.

    Args:
        user_id: ID do usuário
        dir_path: Path do diretório (ex: /memories/learned)
        memories: Lista de AgentMemory para consolidar

    Returns:
        Dict com métricas ou None se falha
    """
    from ..models import AgentMemory, AgentMemoryVersion

    # Formatar memórias para o prompt
    memory_texts = []
    original_chars = 0
    for mem in memories:
        content = (mem.content or "").strip()
        if content:
            filename = mem.path.split("/")[-1]
            memory_texts.append(f"[{filename}]\n{content}")
            original_chars += len(content)

    if not memory_texts:
        return None

    memories_text = "\n\n---\n\n".join(memory_texts)

    # Chamar Haiku para consolidar
    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=1200,
            messages=[{
                "role": "user",
                "content": CONSOLIDATION_PROMPT.format(
                    count=len(memory_texts),
                    memories=memories_text[:6000],  # Limitar input
                ),
            }],
        )

        consolidated_content = response.content[0].text.strip()

        if not consolidated_content or len(consolidated_content) < 20:
            logger.warning(
                f"[MEMORY_CONSOLIDATOR] Haiku retornou conteúdo insuficiente "
                f"para {dir_path} ({len(consolidated_content)} chars)"
            )
            return None

    except Exception as e:
        logger.warning(
            f"[MEMORY_CONSOLIDATOR] Erro ao chamar Haiku para {dir_path}: {e}"
        )
        return None

    # Salvar consolidated.xml
    consolidated_path = f"{dir_path}/consolidated.xml"
    existing = AgentMemory.get_by_path(user_id, consolidated_path)

    if existing:
        # Versionar conteúdo anterior
        if existing.content:
            AgentMemoryVersion.save_version(
                memory_id=existing.id,
                content=existing.content,
                changed_by='haiku',
            )
        existing.content = consolidated_content
    else:
        AgentMemory.create_file(user_id, consolidated_path, consolidated_content)

    # Arquivar originais (renomear com prefixo _archived_)
    archived = 0
    for mem in memories:
        if mem.path == consolidated_path:
            continue

        # Versionar antes de arquivar
        if mem.content:
            AgentMemoryVersion.save_version(
                memory_id=mem.id,
                content=mem.content,
                changed_by='haiku',
            )

        # Renomear para _archived_
        old_name = mem.path.split("/")[-1]
        archived_path = f"{dir_path}/_archived_{old_name}"
        mem.path = archived_path
        archived += 1

    chars_saved = original_chars - len(consolidated_content)

    logger.info(
        f"[MEMORY_CONSOLIDATOR] Grupo {dir_path}: "
        f"{len(memories)} → 1 arquivo, "
        f"{original_chars} → {len(consolidated_content)} chars "
        f"(economia: {chars_saved} chars)"
    )

    return {
        "archived": archived,
        "chars_saved": max(0, chars_saved),
    }
