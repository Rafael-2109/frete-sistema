"""
Consolidação Periódica de Memórias via Sonnet.

Quando um usuário acumula muitas memórias (>15 arquivos ou >6000 chars totais),
consolida em resumos compactos para manter a injeção eficiente.

Custo estimado: ~$0.006 por consolidação (~4K input + ~800 output Sonnet).
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

SONNET_MODEL = "claude-sonnet-4-6"
CONSOLIDATION_MAX_TOKENS = 1200  # Tokens max para consolidação inicial
VERIFICATION_MAX_TOKENS = 800    # Tokens max para verificação de fatos
RETRY_MAX_TOKENS = 1200          # Tokens max para retry (mesmo que consolidação)
CONSOLIDATION_MAX_OUTPUT_CHARS = 2000  # Limite de caracteres do output final
INPUT_LIMIT = 12000  # Limite de input para ambas as chamadas Sonnet

# System prompt estático para consolidação — prompt caching (cache_control ephemeral)
CONSOLIDATION_SYSTEM_PROMPT = """Voce eh um consolidador de memorias de um sistema de logistica (Nacom Goya).
Consolide notas de memoria em UM resumo conciso.

REGRAS:
- Mantenha TODOS os fatos, preferencias, regras e correcoes — NAO perca informacao
- Elimine apenas redundancias, reformulacoes e informacoes duplicadas
- Organize por topico (preferencias, regras, correcoes, contexto)
- Formato: texto corrido organizado, maximo 1500 caracteres
- Linguagem: portugues brasileiro
- NAO adicione interpretacoes ou suposicoes — apenas o que esta escrito

PRIORIZACAO (essencial vs acidental):
Antes de consolidar, classifique mentalmente cada fato:
ESSENCIAL — se perdido, o agente cometeria erro em sessao futura
  (correcoes, regras de negocio, armadilhas, preferencias firmes do usuario)
ACIDENTAL — se perdido, nenhuma consequencia pratica
  (detalhes de formatacao redundante, contexto de sessao especifica ja encerrada)
Priorize essenciais. Acidentais podem ser omitidos se o limite de 1500 chars exigir."""

# System prompt estático para verificação — prompt caching
VERIFICATION_SYSTEM_PROMPT = """Voce eh um verificador de qualidade de consolidacao de memorias.
Compare notas originais com um resumo e identifique fatos perdidos.

REGRA: Liste APENAS os fatos que estao nas notas originais mas NAO estao no resumo.
Se TODOS os fatos foram preservados, responda exatamente: "TODOS_PRESERVADOS"."""

# Diretórios protegidos — NUNCA consolidar estes arquivos
PROTECTED_PATHS = {
    "/memories/user.xml",
    "/memories/preferences.xml",
}

# Diretórios candidatos à consolidação (pessoal)
CONSOLIDATION_DIRS = [
    "/memories/learned",
    "/memories/corrections",
    "/memories/context",
]

# Diretórios candidatos à consolidação (empresa, user_id=0)
CONSOLIDATION_DIRS_EMPRESA = [
    "/memories/empresa/protocolos",
    "/memories/empresa/armadilhas",
    "/memories/empresa/heuristicas",
]

# Thresholds empresa — mais altos pois empresa cresce de múltiplos usuários
EMPRESA_CONSOLIDATION_THRESHOLD_FILES = 30
EMPRESA_CONSOLIDATION_THRESHOLD_CHARS = 12000


def maybe_move_to_cold(user_id: int) -> int:
    """
    Move memorias ineficazes para tier frio baseado em taxa de eficacia.

    Criterio: usage_count >= MIN_USAGE E (effective_count / usage_count) < MAX_EFFICACY.
    Thresholds configuraveis via env vars (ver feature_flags.py).

    Memorias no tier frio:
    - NAO sao injetadas automaticamente no contexto
    - SAO buscaveis via tool search_cold_memories
    - NAO sao consolidadas

    Chamado junto com maybe_consolidate, best-effort.
    Funciona para memorias pessoais (user_id > 0) e empresa (user_id = 0).

    Args:
        user_id: ID do usuario (0 = empresa)

    Returns:
        Numero de memorias movidas para cold
    """
    try:
        from ..config.feature_flags import (
            USE_COLD_MOVE, COLD_MOVE_MIN_USAGE, COLD_MOVE_MAX_EFFICACY,
        )
        if not USE_COLD_MOVE:
            return 0

        from ..models import AgentMemory
        from app import db
        from sqlalchemy import case, cast, Float

        # Eficacia = effective / usage. Sem uso = 1.0 (nao mover)
        efficacy = case(
            (AgentMemory.usage_count > 0,
             cast(AgentMemory.effective_count, Float) / cast(AgentMemory.usage_count, Float)),
            else_=1.0,
        )

        candidates = AgentMemory.query.filter(
            AgentMemory.user_id == user_id,
            AgentMemory.is_directory == False,  # noqa: E712
            AgentMemory.is_cold == False,  # noqa: E712
            AgentMemory.category != 'permanent',  # permanentes sao imunes
            AgentMemory.priority != 'mandatory',  # Proteção: mandatory nunca vai para cold
            AgentMemory.effective_count < 50,  # Proteção: memorias comprovadamente uteis (Task 8)
            AgentMemory.usage_count >= COLD_MOVE_MIN_USAGE,
            efficacy < COLD_MOVE_MAX_EFFICACY,
        ).all()

        if not candidates:
            return 0

        moved = 0
        for mem in candidates:
            eff_rate = (mem.effective_count / mem.usage_count) if mem.usage_count > 0 else 0
            mem.is_cold = True
            moved += 1
            logger.info(
                f"[MEMORY_CONSOLIDATOR] Movida para cold: {mem.path} "
                f"(usage={mem.usage_count}, effective={mem.effective_count}, "
                f"efficacy={eff_rate:.1%})"
            )

        if moved > 0:
            try:
                db.session.commit()
                logger.info(
                    f"[MEMORY_CONSOLIDATOR] {moved} memorias movidas para tier frio "
                    f"(user_id={user_id}, threshold=efficacy<{COLD_MOVE_MAX_EFFICACY:.0%})"
                )
            except Exception as commit_err:
                db.session.rollback()
                logger.warning(
                    f"[MEMORY_CONSOLIDATOR] Erro ao committar cold move (rollback): {commit_err}"
                )
                return 0

        return moved

    except Exception as e:
        logger.warning(f"[MEMORY_CONSOLIDATOR] Cold move falhou (ignorado): {e}")
        return 0


def maybe_cleanup_low_value() -> int:
    """
    Sanitiza memorias empresa (user_id=0) com baixa eficacia.

    Delega para maybe_move_to_cold(user_id=0) que usa os mesmos criterios
    configuraveis (eficacia < threshold, usage >= min). Cobre TODOS os paths
    empresa (termos, protocolos, armadilhas, heuristicas, regras, etc).

    Controlada por flag USE_COLD_MOVE_EMPRESA (independente de USE_COLD_MOVE).

    Returns:
        Numero de memorias movidas para cold.
    """
    try:
        from ..config.feature_flags import USE_COLD_MOVE_EMPRESA
        if not USE_COLD_MOVE_EMPRESA:
            return 0
        return maybe_move_to_cold(user_id=0)
    except Exception as e:
        logger.warning(f"[MEMORY_CONSOLIDATOR] Cleanup empresa falhou (ignorado): {e}")
        return 0


def maybe_gc_cold_memories(user_id: int) -> int:
    """
    Garbage collection: remove memorias cold sem atividade por 90+ dias.

    Implementa a regra do MEMORY_PROTOCOL.md:
    "cold sem acesso por 90+ dias PODEM ser removidas."

    Protecoes:
    - Apenas memorias com is_cold=True (ja classificadas como ineficazes)
    - Apenas memorias com updated_at < now() - max_age_days
    - Memorias permanent sao imunes (defense-in-depth, embora nao devam chegar a cold)
    - Embeddings e KG links removidos junto (cascade manual)

    Best-effort: falhas logadas, nunca propagadas.
    Chamado junto com maybe_consolidate e maybe_move_to_cold.
    Flag independente: USE_COLD_GC (pausar cold move nao impede GC).

    Args:
        user_id: ID do usuario (0 = empresa)

    Returns:
        Numero de memorias removidas
    """
    try:
        from ..config.feature_flags import USE_COLD_GC, COLD_GC_MAX_AGE_DAYS
        if not USE_COLD_GC:
            return 0

        from ..models import AgentMemory
        from app import db
        from app.utils.timezone import agora_utc_naive
        from datetime import timedelta

        cutoff = agora_utc_naive() - timedelta(days=COLD_GC_MAX_AGE_DAYS)

        candidates = AgentMemory.query.filter(
            AgentMemory.user_id == user_id,
            AgentMemory.is_directory == False,  # noqa: E712
            AgentMemory.is_cold == True,  # noqa: E712
            AgentMemory.category != 'permanent',  # defense-in-depth
            AgentMemory.updated_at < cutoff,
        ).all()

        if not candidates:
            return 0

        removed = 0
        for mem in candidates:
            logger.info(
                f"[MEMORY_GC] Removendo cold memory: {mem.path} "
                f"(user_id={user_id}, updated_at={mem.updated_at}, "
                f"usage={mem.usage_count}, effective={mem.effective_count})"
            )
            # Remover embeddings associados
            try:
                from sqlalchemy import text as sql_text
                db.session.execute(sql_text("""
                    DELETE FROM agent_memory_embeddings
                    WHERE memory_id = :mem_id
                """), {"mem_id": mem.id})
            except Exception:
                pass  # Tabela pode nao existir

            # Remover KG links
            try:
                from sqlalchemy import text as sql_text
                db.session.execute(sql_text("""
                    DELETE FROM agent_memory_entity_links
                    WHERE memory_id = :mem_id
                """), {"mem_id": mem.id})
            except Exception:
                pass  # Tabela pode nao existir

            db.session.delete(mem)
            removed += 1

        if removed > 0:
            try:
                db.session.commit()
                logger.info(
                    f"[MEMORY_GC] {removed} memorias cold removidas "
                    f"(user_id={user_id}, cutoff={COLD_GC_MAX_AGE_DAYS}d)"
                )
            except Exception as commit_err:
                db.session.rollback()
                logger.warning(
                    f"[MEMORY_GC] Erro ao committar GC (rollback): {commit_err}"
                )
                return 0

        return removed

    except Exception as e:
        logger.warning(f"[MEMORY_GC] Garbage collection falhou (ignorado): {e}")
        return 0


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

        result = _consolidate_if_needed(
            user_id=user_id,
            threshold_files=MEMORY_CONSOLIDATION_THRESHOLD_FILES,
            threshold_chars=MEMORY_CONSOLIDATION_THRESHOLD_CHARS,
            min_group=MEMORY_CONSOLIDATION_MIN_GROUP,
        )

        # Consolidar empresa (user_id=0) também — aproveitando o trigger
        if user_id != 0:
            try:
                _consolidate_if_needed(
                    user_id=0,
                    threshold_files=EMPRESA_CONSOLIDATION_THRESHOLD_FILES,
                    threshold_chars=EMPRESA_CONSOLIDATION_THRESHOLD_CHARS,
                    min_group=MEMORY_CONSOLIDATION_MIN_GROUP,
                    consolidation_dirs=CONSOLIDATION_DIRS_EMPRESA,
                )
            except Exception as emp_err:
                logger.debug(f"[MEMORY_CONSOLIDATOR] Empresa consolidation falhou (ignorado): {emp_err}")

        return result

    except Exception as e:
        logger.warning(f"[MEMORY_CONSOLIDATOR] Erro (ignorado): {e}")
        return None


def _consolidate_if_needed(
    user_id: int,
    threshold_files: int = 15,
    threshold_chars: int = 6000,
    min_group: int = 3,
    consolidation_dirs: Optional[list] = None,
) -> Optional[Dict[str, Any]]:
    """
    Core da consolidação. Verifica thresholds e executa.

    Args:
        user_id: ID do usuário
        threshold_files: Máximo de arquivos antes de consolidar
        threshold_chars: Máximo de chars totais antes de consolidar
        min_group: Mínimo de arquivos em um diretório para consolidar
        consolidation_dirs: Diretórios candidatos (default: CONSOLIDATION_DIRS)

    Returns:
        Dict com métricas ou None
    """
    from ..models import AgentMemory
    from app import db

    dirs = consolidation_dirs or CONSOLIDATION_DIRS

    try:
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

            # Memory v2: memórias permanentes ou com alta importância são imunes
            if getattr(mem, 'category', '') == 'permanent':
                logger.debug(f"[MEMORY_CONSOLIDATOR] Imune (permanent): {mem.path}")
                continue
            if (getattr(mem, 'importance_score', 0) or 0) >= 0.7:
                logger.debug(f"[MEMORY_CONSOLIDATOR] Imune (importance={mem.importance_score:.2f}): {mem.path}")
                continue

            # Extrair diretório pai
            parts = mem.path.rsplit("/", 1)
            if len(parts) == 2:
                parent_dir = parts[0]
            else:
                continue

            # Só consolidar diretórios candidatos (exact ou prefix match)
            if any(parent_dir == d or parent_dir.startswith(d + '/') for d in dirs):
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

        # 5. Commit transação se houve consolidações bem-sucedidas
        if consolidated_count > 0:
            try:
                db.session.commit()
                logger.info(
                    f"[MEMORY_CONSOLIDATOR] Consolidação concluída com sucesso: "
                    f"{consolidated_count} grupos, "
                    f"{archived_count} arquivos arquivados, "
                    f"{chars_saved} chars economizados"
                )
            except Exception as commit_err:
                db.session.rollback()
                logger.error(
                    f"[MEMORY_CONSOLIDATOR] Erro ao committar consolidação (rollback): {commit_err}"
                )
                return None

        return {
            "consolidated": consolidated_count,
            "archived": archived_count,
            "chars_saved": chars_saved,
        } if consolidated_count > 0 else None

    except Exception as e:
        logger.error(
            f"[MEMORY_CONSOLIDATOR] Erro crítico em _consolidate_if_needed: {e}"
        )
        try:
            db.session.rollback()
        except Exception:
            pass
        return None


def _consolidate_group(
    user_id: int,
    dir_path: str,
    memories: list,
) -> Optional[Dict[str, Any]]:
    """
    Consolida um grupo de memórias em um único arquivo via Sonnet.

    Args:
        user_id: ID do usuário
        dir_path: Path do diretório (ex: /memories/learned)
        memories: Lista de AgentMemory para consolidar

    Returns:
        Dict com métricas ou None se falha
    """
    from ..models import AgentMemory, AgentMemoryVersion
    from app import db

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

    # Chamar Sonnet para consolidar

    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=SONNET_MODEL,
            max_tokens=CONSOLIDATION_MAX_TOKENS,
            system=[{
                "type": "text",
                "text": CONSOLIDATION_SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{
                "role": "user",
                "content": (
                    f"Consolide estas {len(memory_texts)} notas em UM resumo.\n\n"
                    f"NOTAS PARA CONSOLIDAR:\n{memories_text[:INPUT_LIMIT]}\n\n"
                    f"RESUMO CONSOLIDADO:"
                ),
            }],
        )

        consolidated_content = response.content[0].text.strip()

        if not consolidated_content or len(consolidated_content) < 20:
            logger.warning(
                f"[MEMORY_CONSOLIDATOR] Sonnet retornou conteúdo insuficiente "
                f"para {dir_path} ({len(consolidated_content)} chars)"
            )
            return None

        # T2-4: Verificação de preservação de fatos
        # Cross-check: perguntar ao Sonnet se algum fato foi perdido
        # NOTA: Usar mesmo limite de truncamento que a consolidação
        try:
            verify_response = client.messages.create(
                model=SONNET_MODEL,
                max_tokens=VERIFICATION_MAX_TOKENS,
                system=[{
                    "type": "text",
                    "text": VERIFICATION_SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }],
                messages=[{
                    "role": "user",
                    "content": (
                        f"NOTAS ORIGINAIS:\n{memories_text[:INPUT_LIMIT]}\n\n"
                        f"RESUMO:\n{consolidated_content}\n\n"
                        f"FATOS PERDIDOS (ou \"TODOS_PRESERVADOS\"):"
                    ),
                }],
            )

            verify_text = verify_response.content[0].text.strip()

            if "TODOS_PRESERVADOS" not in verify_text.upper():
                # Fatos perdidos detectados — re-consolidar com instrução mais explícita
                logger.warning(
                    f"[MEMORY_CONSOLIDATOR] Fatos perdidos detectados em {dir_path}: "
                    f"{verify_text[:200]}"
                )

                # Re-consolidar incluindo os fatos perdidos como instrução adicional
                retry_prompt = (
                    f"Consolide estas {len(memory_texts)} notas em UM resumo. "
                    f"ATENÇÃO: O resumo anterior perdeu estes fatos — INCLUA-OS obrigatoriamente:\n"
                    f"{verify_text}\n\n"
                    f"NOTAS:\n{memories_text[:INPUT_LIMIT]}\n\n"
                    f"RESUMO CONSOLIDADO (máximo {CONSOLIDATION_MAX_OUTPUT_CHARS} caracteres):"
                )

                retry_response = client.messages.create(
                    model=SONNET_MODEL,
                    max_tokens=RETRY_MAX_TOKENS,
                    system=[{
                        "type": "text",
                        "text": CONSOLIDATION_SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }],
                    messages=[{"role": "user", "content": retry_prompt}],
                )
                retry_content = retry_response.content[0].text.strip()

                # Validar re-consolidação: mínimo 20 chars + máximo respeitado
                if retry_content and len(retry_content) >= 20 and len(retry_content) <= CONSOLIDATION_MAX_OUTPUT_CHARS:
                    consolidated_content = retry_content
                    logger.info(
                        f"[MEMORY_CONSOLIDATOR] Re-consolidação para {dir_path}: "
                        f"{len(consolidated_content)} chars (com fatos recuperados)"
                    )
                else:
                    # Truncar se excedeu limite, com warning
                    if len(retry_content) > CONSOLIDATION_MAX_OUTPUT_CHARS:
                        logger.warning(
                            f"[MEMORY_CONSOLIDATOR] Re-consolidação excedeu {CONSOLIDATION_MAX_OUTPUT_CHARS} chars "
                            f"({len(retry_content)} chars), truncando"
                        )
                        consolidated_content = retry_content[:CONSOLIDATION_MAX_OUTPUT_CHARS].rstrip()
                    else:
                        logger.warning(
                            f"[MEMORY_CONSOLIDATOR] Re-consolidação insuficiente para {dir_path} "
                            f"({len(retry_content)} chars), mantendo consolidado original"
                        )
            else:
                logger.info(
                    f"[MEMORY_CONSOLIDATOR] Verificação OK para {dir_path}: "
                    f"todos os fatos preservados"
                )

        except Exception as verify_err:
            # Verificação falhou — usar consolidado original (melhor que nada)
            logger.debug(
                f"[MEMORY_CONSOLIDATOR] Verificação falhou (usando consolidado original): "
                f"{verify_err}"
            )

    except Exception as e:
        logger.warning(
            f"[MEMORY_CONSOLIDATOR] Erro ao chamar Sonnet para {dir_path}: {e}"
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
                changed_by='sonnet',
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
                changed_by='sonnet',
            )

        # Renomear para _archived_
        old_name = mem.path.split("/")[-1]
        archived_path = f"{dir_path}/_archived_{old_name}"
        mem.path = archived_path
        mem.is_cold = True  # Excluir da injeção automática
        archived += 1

    # Remover embeddings stale das memórias archived
    try:
        from sqlalchemy import text as sql_text
        archived_ids = [m.id for m in memories if m.path != consolidated_path]
        if archived_ids:
            db.session.execute(sql_text("""
                DELETE FROM agent_memory_embeddings
                WHERE memory_id = ANY(:ids)
            """), {"ids": archived_ids})
    except Exception as emb_err:
        logger.debug(f"[MEMORY_CONSOLIDATOR] Embedding cleanup falhou (ignorado): {emb_err}")

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
