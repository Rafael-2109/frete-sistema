"""
Helpers compartilhados das rotas do Agente.

Funcoes usadas por multiplos sub-modulos E/OU importadas por app/teams/services.py.
Nenhuma destas e rota — sao funcoes auxiliares puras.

Exportadas tambem via routes/__init__.py para manter compatibilidade:
    from app.agente.routes import run_post_session_processing  # Teams
    from app.agente.routes import _calculate_cost               # Teams
    from app.agente.routes import _track_memory_effectiveness   # Teams
"""

import json
import logging

from app import db

from app.agente.routes._constants import (
    EFFECTIVENESS_COSINE_THRESHOLD,
    EFFECTIVENESS_RESPONSE_MAX_CHARS,
    EFFECTIVENESS_WORD_OVERLAP_THRESHOLD,
)

logger = logging.getLogger('sistema_fretes')


def _sse_event(event_type: str, data: dict) -> str:
    """Formata evento SSE."""
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def run_post_session_processing(
    app,
    session,
    session_id: str,
    user_id: int,
    user_message: str,
    assistant_message: str,
) -> None:
    """
    Post-session processing: summarization, pattern learning, extraction, embedding.

    Best-effort: cada etapa falha silenciosamente sem afetar as demais.
    DEVE ser chamado com app_context ativo (caller garante).

    Reutilizado por web (routes/chat.py) e Teams (teams/services.py).

    Args:
        app: Flask app
        session: AgentSession (ja carregada, com mensagens)
        session_id: Nosso session_id (UUID)
        user_id: ID do usuario
        user_message: Mensagem do usuario (pode ser None)
        assistant_message: Resposta do assistente (pode ser None)
    """
    # =================================================================
    # P0-2: Sumarizacao Estruturada
    # =================================================================
    try:
        from app.agente.config.feature_flags import USE_SESSION_SUMMARY, SESSION_SUMMARY_THRESHOLD

        if USE_SESSION_SUMMARY and session.needs_summarization(SESSION_SUMMARY_THRESHOLD):
            logger.info(
                f"[POST_SESSION] Trigger sumarizacao para sessao {session_id[:8]}... "
                f"(msgs={session.message_count}, threshold={SESSION_SUMMARY_THRESHOLD})"
            )
            from app.agente.services.session_summarizer import summarize_and_save
            summarize_and_save(
                app=app,
                session_id=session_id,
                user_id=user_id,
            )
    except Exception as summary_error:
        logger.warning(f"[POST_SESSION] Erro na sumarizacao (ignorado): {summary_error}")

    # =================================================================
    # P1-3: Aprendizado de Padroes
    # =================================================================
    patterns_already_ran = False
    try:
        from app.agente.config.feature_flags import USE_PATTERN_LEARNING, PATTERN_LEARNING_THRESHOLD

        if USE_PATTERN_LEARNING:
            from app.agente.services.pattern_analyzer import should_analyze_patterns, analyze_and_save as analyze_patterns_and_save

            if should_analyze_patterns(user_id, PATTERN_LEARNING_THRESHOLD):
                logger.info(
                    f"[POST_SESSION] Trigger analise de padroes para usuario {user_id} "
                    f"(threshold={PATTERN_LEARNING_THRESHOLD})"
                )
                analyze_patterns_and_save(app=app, user_id=user_id)
                patterns_already_ran = True
    except Exception as pattern_error:
        logger.warning(f"[POST_SESSION] Erro na analise de padroes (ignorado): {pattern_error}")

    # =================================================================
    # Behavioral Profile (user.xml — Tier 1, SEMPRE injetado)
    # analyze_and_save() faz piggyback de user.xml quando patterns roda —
    # skip para evitar double Sonnet call (~$0.006 duplicado)
    # =================================================================
    if not patterns_already_ran:
        try:
            from app.agente.config.feature_flags import USE_BEHAVIORAL_PROFILE, BEHAVIORAL_PROFILE_THRESHOLD
            if USE_BEHAVIORAL_PROFILE:
                from app.agente.services.pattern_analyzer import should_generate_profile, generate_and_save_profile
                if should_generate_profile(user_id, BEHAVIORAL_PROFILE_THRESHOLD):
                    logger.info(
                        f"[POST_SESSION] Trigger geracao de perfil para usuario {user_id} "
                        f"(threshold={BEHAVIORAL_PROFILE_THRESHOLD})"
                    )
                    generate_and_save_profile(app=app, user_id=user_id)
        except Exception as profile_err:
            logger.warning(f"[POST_SESSION] Erro geracao perfil (ignorado): {profile_err}")

    # =================================================================
    # PRD v2.1: Extracao pos-sessao de conhecimento organizacional
    # =================================================================
    try:
        from app.agente.config.feature_flags import (
            USE_POST_SESSION_EXTRACTION,
            POST_SESSION_EXTRACTION_MIN_MESSAGES,
        )

        if USE_POST_SESSION_EXTRACTION and user_message and assistant_message:
            msg_count = session.message_count or 0
            if msg_count >= POST_SESSION_EXTRACTION_MIN_MESSAGES:
                from threading import Thread
                from app.agente.services.pattern_analyzer import extrair_conhecimento_sessao

                # Copia mensagens para evitar race condition com a sessao
                messages_for_extraction = list(session.get_messages())

                def _run_extraction_background():
                    nonlocal messages_for_extraction
                    try:
                        with app.app_context():
                            extrair_conhecimento_sessao(
                                app=app,
                                user_id=user_id,
                                session_messages=messages_for_extraction,
                            )
                    except Exception as bg_err:
                        logger.warning(
                            f"[KNOWLEDGE_EXTRACTION] Background error: {bg_err}"
                        )
                    finally:
                        # Liberar referencia da closure
                        messages_for_extraction = None
                        # Liberar session do pool em thread manual
                        try:
                            with app.app_context():
                                db.session.remove()
                        except Exception as e:
                            logger.debug(f"[EXTRACTION] db.session.remove falhou em background: {e}")

                thread = Thread(
                    target=_run_extraction_background,
                    daemon=False,
                    name=f"knowledge-extraction-{user_id}",
                )
                thread.start()
                logger.info(
                    f"[POST_SESSION] Trigger extracao pos-sessao em background "
                    f"para usuario {user_id} (message_count={msg_count})"
                )
    except Exception as extraction_error:
        logger.warning(f"[POST_SESSION] Erro na extracao pos-sessao (ignorado): {extraction_error}")

    # =================================================================
    # Fase 4: Embedding de turn para busca semantica (best-effort)
    # =================================================================
    try:
        from app.agente.config.feature_flags import USE_SESSION_SEMANTIC_SEARCH
        if USE_SESSION_SEMANTIC_SEARCH and user_message and assistant_message:
            _embed_session_turn_best_effort(
                app, session_id, user_id,
                user_message, assistant_message, session
            )
    except Exception as emb_err:
        logger.debug(f"[POST_SESSION] Embedding turn falhou (ignorado): {emb_err}")

    # Nota: Improvement Dialogue (D8) roda via APScheduler batch (modulo 25, 07:00 e 10:00)
    # + crontab local (11:03 diario, Claude Code CLI com feature-dev).
    # NAO pos-sessao — garante cobertura de sessoes abandonadas e batch analysis cross-sessao.


def _calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calcula custo aproximado baseado no modelo (delega para settings)."""
    from app.agente.config import get_settings
    settings = get_settings()
    return settings.calculate_cost(input_tokens, output_tokens, model=model)


def _track_memory_effectiveness(user_id: int, assistant_message: str, injected_memory_ids: list[int] = None) -> None:
    """
    Memory v2 — Feedback Loop: rastreia se memorias injetadas foram usadas.

    Abordagem hibrida:
    - Primaria: Voyage AI cosine similarity >= threshold (batch unico ~200ms)
    - Fallback: Word overlap relaxado (>= 35%) OU entity overlap (>= 1 entidade em comum)

    Best-effort: falhas silenciosas, nao afeta fluxo principal.
    """
    try:
        if not injected_memory_ids:
            return

        from app.agente.models import AgentMemory
        from app.agente.services.knowledge_graph_service import clean_for_comparison
        from sqlalchemy import text as sql_text

        # Buscar memorias pelos IDs exatos injetados neste turno
        injected_memories = AgentMemory.query.filter(
            AgentMemory.id.in_(injected_memory_ids),
        ).all()

        if not injected_memories:
            return

        # Preparar conteudos limpos (strip XML tags + decode entities)
        memory_contents = {}  # {mem.id: clean_content}
        for mem in injected_memories:
            content = (mem.content or "").strip()
            if not content or len(content) < 15:
                continue
            clean_content = clean_for_comparison(content)
            if clean_content and len(clean_content) >= 15:
                memory_contents[mem.id] = clean_content

        if not memory_contents:
            return

        # Primaria: similaridade semantica via Voyage AI
        effective_ids = _check_effectiveness_semantic(memory_contents, assistant_message)

        # Se semantico falhou (retornou None), usar fallback heuristico
        if effective_ids is None:
            effective_ids = _check_effectiveness_heuristic(memory_contents, assistant_message)
            method = "heuristic"
        else:
            method = "semantic"

        if effective_ids:
            db.session.execute(sql_text("""
                UPDATE agent_memories
                SET effective_count = effective_count + 1
                WHERE id = ANY(:ids)
            """), {"ids": effective_ids})
            db.session.commit()
            logger.debug(
                f"[MEMORY_FEEDBACK] effective_count incremented for "
                f"{len(effective_ids)}/{len(injected_memory_ids)} memories "
                f"(user_id={user_id}, method={method})"
            )
        else:
            logger.debug(
                f"[MEMORY_FEEDBACK] No effective memories detected "
                f"(user_id={user_id}, injected={len(injected_memory_ids)}, method={method})"
            )

    except Exception as e:
        logger.warning(f"[MEMORY_FEEDBACK] Tracking falhou (ignorado): {e}")
        try:
            db.session.rollback()
        except Exception:
            pass


def _check_effectiveness_semantic(
    memory_contents: dict[int, str],
    assistant_message: str,
) -> list[int] | None:
    """
    Verifica efetividade via Voyage AI cosine similarity (primaria).

    Faz um batch unico de embeddings: N conteudos de memoria + 1 resposta truncada.
    Calcula cosine similarity entre cada memoria e a resposta.

    Returns:
        list[int] de IDs efetivos, ou None se embedding falhou (signal para fallback).
    """
    import math

    try:
        from app.embeddings.config import EMBEDDINGS_ENABLED
        if not EMBEDDINGS_ENABLED:
            return None  # Signal fallback

        from app.embeddings.service import EmbeddingService

        # Preparar textos para batch: memorias + resposta truncada
        mem_ids = list(memory_contents.keys())
        mem_texts = list(memory_contents.values())
        response_text = assistant_message[:EFFECTIVENESS_RESPONSE_MAX_CHARS]

        # Batch unico: [mem1, mem2, ..., memN, response]
        all_texts = mem_texts + [response_text]

        svc = EmbeddingService()
        embeddings = svc.embed_texts(all_texts, input_type="document")

        if not embeddings or len(embeddings) != len(all_texts):
            return None  # Signal fallback

        # Ultimo embedding e a resposta
        response_embedding = embeddings[-1]
        effective_ids = []

        for i, mem_id in enumerate(mem_ids):
            mem_embedding = embeddings[i]

            # Cosine similarity (Voyage retorna L2-normalized, dot = cosine)
            dot = sum(a * b for a, b in zip(mem_embedding, response_embedding))
            norm_a = math.sqrt(sum(a * a for a in mem_embedding))
            norm_b = math.sqrt(sum(b * b for b in response_embedding))

            if norm_a == 0 or norm_b == 0:
                continue

            cosine = dot / (norm_a * norm_b)

            if cosine >= EFFECTIVENESS_COSINE_THRESHOLD:
                effective_ids.append(mem_id)
                logger.debug(
                    f"[MEMORY_FEEDBACK] Semantic match: mem_id={mem_id}, cosine={cosine:.3f}"
                )

        return effective_ids

    except Exception as e:
        logger.debug(f"[MEMORY_FEEDBACK] Semantic check falhou, usando fallback: {e}")
        return None  # Signal fallback


def _check_effectiveness_heuristic(
    memory_contents: dict[int, str],
    assistant_message: str,
) -> list[int]:
    """
    Verifica efetividade via heuristica relaxada (fallback).

    Duas estrategias (OR):
    1. Word overlap >= 35% (relaxado de 60%)
    2. Entity overlap >= 1 entidade em comum (CNPJs, UFs, IDs numericos, codigos)

    Returns:
        list[int] de IDs efetivos (pode ser vazia).
    """
    import re

    assistant_lower = assistant_message.lower()
    assistant_words = set(assistant_lower.split())
    assistant_entities = _extract_entities_for_matching(assistant_message)
    effective_ids = []

    for mem_id, clean_content in memory_contents.items():
        # Estrategia 1: Word overlap relaxado
        sentences = [
            s.strip() for s in re.split(r'[.!?\n]+', clean_content)
            if len(s.strip()) >= 15
        ][:5]

        word_match = False
        for sentence in sentences:
            words = sentence.lower().split()
            if not words:
                continue
            overlap = sum(1 for w in words if w in assistant_words)
            if overlap / len(words) >= EFFECTIVENESS_WORD_OVERLAP_THRESHOLD:
                word_match = True
                logger.debug(
                    f"[MEMORY_FEEDBACK] Word overlap match: mem_id={mem_id}, "
                    f"overlap={overlap}/{len(words)}={overlap/len(words):.2f}"
                )
                break

        if word_match:
            effective_ids.append(mem_id)
            continue

        # Estrategia 2: Entity overlap
        mem_entities = _extract_entities_for_matching(clean_content)
        common_entities = mem_entities & assistant_entities
        if common_entities:
            effective_ids.append(mem_id)
            logger.debug(
                f"[MEMORY_FEEDBACK] Entity match: mem_id={mem_id}, "
                f"entities={list(common_entities)[:5]}"
            )

    return effective_ids


def _extract_entities_for_matching(text: str) -> set[str]:
    """
    Extrai entidades estruturadas de um texto para matching de efetividade.

    Extrai:
    - CNPJs (14 digitos, com/sem formatacao)
    - UFs brasileiras (26 siglas, case-sensitive, word boundary)
    - IDs numericos >= 4 digitos
    - Codigos alfanumericos (min 3 chars, pelo menos 1 letra + 1 digito)

    Returns:
        set[str] de entidades normalizadas.
    """
    import re

    entities = set()

    if not text:
        return entities

    # CNPJs: 14 digitos (com ou sem formatacao XX.XXX.XXX/XXXX-XX)
    cnpjs_formatted = re.findall(r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}', text)
    for cnpj in cnpjs_formatted:
        entities.add(re.sub(r'[./-]', '', cnpj))  # Normaliza para so digitos

    cnpjs_raw = re.findall(r'\b\d{14}\b', text)
    for cnpj in cnpjs_raw:
        entities.add(cnpj)

    # UFs brasileiras (case-sensitive, word boundary)
    UFS_BR = {
        'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO',
        'MA', 'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI',
        'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO',
    }
    words = re.findall(r'\b[A-Z]{2}\b', text)
    for w in words:
        if w in UFS_BR:
            entities.add(f"UF:{w}")

    # IDs numericos >= 4 digitos (pedidos, NFs, etc.)
    ids_numericos = re.findall(r'\b\d{4,}\b', text)
    for id_num in ids_numericos:
        # Ignorar CNPJs ja capturados (14 digitos)
        if len(id_num) != 14:
            entities.add(f"ID:{id_num}")

    # Codigos alfanumericos (cod_produto, num_pedido): min 3 chars, >= 1 letra + >= 1 digito
    codigos = re.findall(r'\b[A-Za-z0-9]{3,}\b', text)
    for cod in codigos:
        has_letter = any(c.isalpha() for c in cod)
        has_digit = any(c.isdigit() for c in cod)
        if has_letter and has_digit:
            entities.add(f"COD:{cod.upper()}")

    return entities


def _embed_session_turn_best_effort(app, session_id, user_id, user_message, assistant_message, session):
    """
    Gera embedding de um turn (par user+assistant) para busca semantica.

    Best-effort: falhas sao silenciosas e nao afetam o fluxo principal.
    O embedding e gerado inline (~150ms) e salvo via upsert.
    """
    import hashlib
    from sqlalchemy import text as sql_text

    try:
        from app.embeddings.config import SESSION_SEMANTIC_SEARCH, VOYAGE_DEFAULT_MODEL
        if not SESSION_SEMANTIC_SEARCH:
            return

        from app.embeddings.service import EmbeddingService

        # Calcular turn_index (pares de mensagens na sessao)
        msg_count = session.message_count or 0
        turn_index = max(0, (msg_count - 1) // 2)

        # Build texto embedado
        from app.embeddings.config import ASSISTANT_SUMMARY_MAX_CHARS
        assistant_summary = (assistant_message or '')[:ASSISTANT_SUMMARY_MAX_CHARS]
        texto_embedado = f"[USER]: {user_message}\n[ASSISTANT]: {assistant_summary}"

        # Content hash para stale detection
        c_hash = hashlib.md5(texto_embedado.encode('utf-8')).hexdigest()

        # Verificar se ja existe com mesmo hash (skip)
        existing = db.session.execute(sql_text("""
            SELECT content_hash FROM session_turn_embeddings
            WHERE session_id = :session_id AND turn_index = :turn_index
        """), {"session_id": session_id, "turn_index": turn_index}).fetchone()

        if existing and existing[0] == c_hash:
            return  # Conteudo nao mudou

        # Gerar embedding
        svc = EmbeddingService()
        embeddings = svc.embed_texts([texto_embedado], input_type="document")

        if not embeddings:
            return

        import json as _json
        embedding_str = _json.dumps(embeddings[0])

        # Upsert
        db.session.execute(sql_text("""
            INSERT INTO session_turn_embeddings
                (session_id, user_id, turn_index,
                 user_content, assistant_summary, texto_embedado,
                 embedding, model_used, content_hash,
                 session_title, session_created_at)
            VALUES
                (:session_id, :user_id, :turn_index,
                 :user_content, :assistant_summary, :texto_embedado,
                 :embedding, :model_used, :content_hash,
                 :session_title, :session_created_at)
            ON CONFLICT ON CONSTRAINT uq_session_turn
            DO UPDATE SET
                user_content = EXCLUDED.user_content,
                assistant_summary = EXCLUDED.assistant_summary,
                texto_embedado = EXCLUDED.texto_embedado,
                embedding = EXCLUDED.embedding,
                model_used = EXCLUDED.model_used,
                content_hash = EXCLUDED.content_hash,
                session_title = EXCLUDED.session_title,
                updated_at = NOW()
        """), {
            "session_id": session_id,
            "user_id": user_id,
            "turn_index": turn_index,
            "user_content": user_message,
            "assistant_summary": assistant_summary if assistant_summary else None,
            "texto_embedado": texto_embedado,
            "embedding": embedding_str,
            "model_used": VOYAGE_DEFAULT_MODEL,
            "content_hash": c_hash,
            "session_title": session.title,
            "session_created_at": session.created_at,
        })
        db.session.commit()

        logger.debug(
            f"[AGENTE] Embedding turn {turn_index} salvo para sessao {session_id[:8]}"
        )

    except Exception as e:
        logger.debug(f"[AGENTE] _embed_session_turn_best_effort falhou: {e}")
        try:
            db.session.rollback()
        except Exception:
            pass
