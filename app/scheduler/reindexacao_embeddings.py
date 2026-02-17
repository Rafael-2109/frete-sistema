"""
Modulo de reindexacao de embeddings.

Orquestra todos os indexers em sequencia:
1. Products (com aliases de_para)
2. Financial Entities (fornecedores/clientes)
3. Session Turns (catch-up para dados historicos)
4. Agent Memories (catch-up para dados historicos)
5. SQL Templates (seed + runtime queries bem-sucedidas)
6. Payment Categories (categorias pre-definidas)
7. Devolucao Reasons (motivos de devolucao classificados)
8. Carriers (transportadoras com aliases)

SSW docs sao estaticos — reindexar manualmente quando necessario.

Duas formas de execucao:

1. Via scheduler (20o modulo): executar_reindexacao_no_contexto()
   - Chamado dentro de executar_sincronizacao(), app context ja ativo
   - Segue padrao do scheduler: cleanup db entre etapas
   - Frequencia: diaria, controlada pelo scheduler principal

2. Standalone (CLI/teste): executar_reindexacao()
   - Cria proprio create_app() + app_context()
   - Uso:
       source .venv/bin/activate
       python -c "from app.scheduler.reindexacao_embeddings import executar_reindexacao; executar_reindexacao()"

Cada indexer tem stale detection (content_hash ou texto_embedado) — apenas
itens novos ou modificados sao re-embeddados.

Custo estimado: ~$0.03/dia, ~$0.90/mes
"""

import logging
import time

from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)


def _cleanup_db():
    """Cleanup entre indexers (padrao do scheduler)."""
    try:
        from app import db
        db.session.remove()
        db.engine.dispose()
    except Exception:
        pass


def executar_reindexacao_no_contexto():
    """
    Executa reindexacao dentro de app context ja ativo.

    Chamado pelo scheduler principal como 20o modulo de executar_sincronizacao().
    Segue o padrao do scheduler: cleanup db entre etapas, try/except independente.
    NAO cria create_app() — assume que o caller ja tem app context.

    Returns:
        Dict com resultados por indexer, ou None se desabilitado
    """
    from app.embeddings.config import EMBEDDINGS_ENABLED

    if not EMBEDDINGS_ENABLED:
        logger.info("[EMBEDDINGS] Desabilitado via flag EMBEDDINGS_ENABLED. Skipping.")
        return None

    inicio = time.time()
    resultados = {}

    logger.info("   REINDEXACAO DE EMBEDDINGS")
    logger.info("   Inicio: %s", agora_utc_naive().strftime('%d/%m/%Y %H:%M:%S'))

    total_steps = 8

    # ── 1. Products (com aliases de_para) ──
    try:
        logger.info("   [1/%d] Reindexando produtos...", total_steps)
        from app.embeddings.indexers.product_indexer import collect_products, index_products

        produtos, _total = collect_products()
        if produtos:
            stats = index_products(produtos)
            resultados['products'] = stats
            logger.info("      Produtos: %d novos/atualizados, %d skipped",
                        stats.get('embedded', 0), stats.get('skipped', 0))
        else:
            resultados['products'] = {'embedded': 0, 'skipped': 0}
            logger.info("      Nenhum produto para indexar")
    except Exception as e:
        logger.error("      Erro em products: %s", e, exc_info=True)
        resultados['products'] = {'error': str(e)}

    _cleanup_db()

    # ── 2. Financial Entities ──
    try:
        logger.info("   [2/%d] Reindexando entidades financeiras...", total_steps)
        from app.embeddings.indexers.entity_indexer import collect_entities, index_entities

        entities, _stats_collect = collect_entities()
        if entities:
            stats = index_entities(entities)
            resultados['entities'] = stats
            logger.info("      Entidades: %d novas, %d skipped",
                        stats.get('embedded', 0), stats.get('skipped', 0))
        else:
            resultados['entities'] = {'embedded': 0, 'skipped': 0}
            logger.info("      Nenhuma entidade para indexar")
    except Exception as e:
        logger.error("      Erro em entities: %s", e, exc_info=True)
        resultados['entities'] = {'error': str(e)}

    _cleanup_db()

    # ── 3. Session Turns (catch-up) ──
    try:
        logger.info("   [3/%d] Catch-up session turns...", total_steps)
        from app.embeddings.indexers.session_turn_indexer import collect_turns, index_turns

        turns, _stats_collect = collect_turns()
        if turns:
            stats = index_turns(turns)
            resultados['session_turns'] = stats
            logger.info("      Turns: %d novos, %d skipped",
                        stats.get('embedded', 0), stats.get('skipped', 0))
        else:
            resultados['session_turns'] = {'embedded': 0, 'skipped': 0}
            logger.info("      Nenhum turn para indexar")
    except Exception as e:
        logger.error("      Erro em session_turns: %s", e, exc_info=True)
        resultados['session_turns'] = {'error': str(e)}

    _cleanup_db()

    # ── 4. Agent Memories (catch-up) ──
    try:
        logger.info("   [4/%d] Catch-up memorias...", total_steps)
        from app.embeddings.indexers.memory_indexer import collect_memories, index_memories

        memories, _stats_collect = collect_memories()
        if memories:
            stats = index_memories(memories)
            resultados['memories'] = stats
            logger.info("      Memorias: %d novas/atualizadas, %d skipped",
                        stats.get('embedded', 0), stats.get('skipped', 0))
        else:
            resultados['memories'] = {'embedded': 0, 'skipped': 0}
            logger.info("      Nenhuma memoria para indexar")
    except Exception as e:
        logger.error("      Erro em memories: %s", e, exc_info=True)
        resultados['memories'] = {'error': str(e)}

    _cleanup_db()

    # ── 5. SQL Templates (seed + runtime) ──
    try:
        from app.embeddings.config import SQL_TEMPLATE_SEARCH
        if SQL_TEMPLATE_SEARCH:
            logger.info("   [5/%d] Reindexando SQL templates...", total_steps)
            from app.embeddings.indexers.sql_template_indexer import (
                collect_seed_templates, index_sql_templates
            )

            templates = collect_seed_templates()
            if templates:
                stats = index_sql_templates(templates)
                resultados['sql_templates'] = stats
                logger.info("      SQL Templates: %d novos, %d skipped",
                            stats.get('embedded', 0), stats.get('skipped', 0))
            else:
                resultados['sql_templates'] = {'embedded': 0, 'skipped': 0}
        else:
            logger.info("   [5/%d] SQL Templates desabilitado (SQL_TEMPLATE_SEARCH=false)", total_steps)
            resultados['sql_templates'] = {'skipped_flag': True}
    except Exception as e:
        logger.error("      Erro em sql_templates: %s", e, exc_info=True)
        resultados['sql_templates'] = {'error': str(e)}

    _cleanup_db()

    # ── 6. Payment Categories ──
    try:
        from app.embeddings.config import PAYMENT_CATEGORY_SEMANTIC
        if PAYMENT_CATEGORY_SEMANTIC:
            logger.info("   [6/%d] Reindexando categorias de pagamento...", total_steps)
            from app.embeddings.indexers.payment_category_indexer import (
                collect_categories, index_payment_categories
            )

            categories = collect_categories()
            if categories:
                stats = index_payment_categories(categories)
                resultados['payment_categories'] = stats
                logger.info("      Payment Categories: %d novos, %d skipped",
                            stats.get('embedded', 0), stats.get('skipped', 0))
            else:
                resultados['payment_categories'] = {'embedded': 0, 'skipped': 0}
        else:
            logger.info("   [6/%d] Payment Categories desabilitado", total_steps)
            resultados['payment_categories'] = {'skipped_flag': True}
    except Exception as e:
        logger.error("      Erro em payment_categories: %s", e, exc_info=True)
        resultados['payment_categories'] = {'error': str(e)}

    _cleanup_db()

    # ── 7. Devolucao Reasons ──
    try:
        from app.embeddings.config import DEVOLUCAO_REASON_SEMANTIC
        if DEVOLUCAO_REASON_SEMANTIC:
            logger.info("   [7/%d] Reindexando motivos de devolucao...", total_steps)
            from app.embeddings.indexers.devolucao_reason_indexer import (
                collect_devolucao_reasons, index_devolucao_reasons
            )

            reasons = collect_devolucao_reasons()
            if reasons:
                stats = index_devolucao_reasons(reasons)
                resultados['devolucao_reasons'] = stats
                logger.info("      Devolucao Reasons: %d novos, %d skipped",
                            stats.get('embedded', 0), stats.get('skipped', 0))
            else:
                resultados['devolucao_reasons'] = {'embedded': 0, 'skipped': 0}
        else:
            logger.info("   [7/%d] Devolucao Reasons desabilitado", total_steps)
            resultados['devolucao_reasons'] = {'skipped_flag': True}
    except Exception as e:
        logger.error("      Erro em devolucao_reasons: %s", e, exc_info=True)
        resultados['devolucao_reasons'] = {'error': str(e)}

    _cleanup_db()

    # ── 8. Carriers (transportadoras) ──
    try:
        from app.embeddings.config import CARRIER_SEMANTIC_SEARCH
        if CARRIER_SEMANTIC_SEARCH:
            logger.info("   [8/%d] Reindexando transportadoras...", total_steps)
            from app.embeddings.indexers.carrier_indexer import (
                collect_carriers, index_carriers
            )

            carriers = collect_carriers()
            if carriers:
                stats = index_carriers(carriers)
                resultados['carriers'] = stats
                logger.info("      Carriers: %d novos, %d skipped",
                            stats.get('embedded', 0), stats.get('skipped', 0))
            else:
                resultados['carriers'] = {'embedded': 0, 'skipped': 0}
        else:
            logger.info("   [8/%d] Carriers desabilitado", total_steps)
            resultados['carriers'] = {'skipped_flag': True}
    except Exception as e:
        logger.error("      Erro em carriers: %s", e, exc_info=True)
        resultados['carriers'] = {'error': str(e)}

    # ── Resumo ──
    elapsed = time.time() - inicio
    erros = sum(1 for v in resultados.values() if 'error' in v)

    logger.info("   REINDEXACAO concluida em %.1fs (%d erros)", elapsed, erros)
    for key, stats in resultados.items():
        if 'error' in stats:
            logger.info("      %s: ERRO - %s", key, str(stats['error'])[:80])
        elif 'skipped_flag' in stats:
            logger.info("      %s: desabilitado por flag", key)
        else:
            logger.info("      %s: %d embedded, %d skipped",
                        key, stats.get('embedded', 0), stats.get('skipped', 0))

    return resultados


def executar_reindexacao():
    """
    Executa reindexacao standalone (CLI/teste).

    Cria proprio create_app() + app_context().
    Para uso via scheduler, usar executar_reindexacao_no_contexto().

    Uso:
        source .venv/bin/activate
        python -c "from app.scheduler.reindexacao_embeddings import executar_reindexacao; executar_reindexacao()"

    Returns:
        Dict com resultados por indexer, ou None se desabilitado
    """
    from app import create_app
    from app.embeddings.config import EMBEDDINGS_ENABLED

    if not EMBEDDINGS_ENABLED:
        logger.info("[EMBEDDINGS] Desabilitado via flag EMBEDDINGS_ENABLED. Skipping.")
        return None

    app = create_app()

    logger.info("=" * 60)
    logger.info("REINDEXACAO DE EMBEDDINGS (standalone)")
    logger.info("=" * 60)

    with app.app_context():
        return executar_reindexacao_no_contexto()
