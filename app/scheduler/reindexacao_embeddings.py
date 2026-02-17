"""
Modulo de reindexacao diaria de embeddings.

Orquestra todos os indexers em sequencia:
1. Products (com aliases de_para)
2. Financial Entities (fornecedores/clientes)
3. Session Turns (catch-up para dados historicos)
4. Agent Memories (catch-up para dados historicos)

SSW docs sao estaticos — reindexar manualmente quando necessario.

Chamado pelo scheduler principal via cron trigger (default 03:00 AM Brasil).
Cada indexer tem stale detection (content_hash ou texto_embedado) — apenas
itens novos ou modificados sao re-embeddados.

Custo estimado: ~$0.025/dia, ~$0.75/mes

Uso standalone (teste):
    source .venv/bin/activate
    python -c "from app.scheduler.reindexacao_embeddings import executar_reindexacao; executar_reindexacao()"
"""

import logging
import time
from datetime import datetime

logger = logging.getLogger(__name__)


def executar_reindexacao():
    """
    Executa reindexacao incremental de todos os indexers.

    Cria um unico app context e executa todos os indexers em sequencia.
    Cada indexer roda em try/except independente — falha em um nao
    impede os demais.

    Returns:
        Dict com resultados por indexer, ou None se desabilitado
    """
    from app import create_app
    from app.embeddings.config import EMBEDDINGS_ENABLED

    if not EMBEDDINGS_ENABLED:
        logger.info("[EMBEDDINGS] Desabilitado via flag EMBEDDINGS_ENABLED. Skipping.")
        return None

    app = create_app()
    inicio = time.time()
    resultados = {}

    logger.info("=" * 60)
    logger.info("REINDEXACAO DIARIA DE EMBEDDINGS")
    logger.info("   Inicio: %s", datetime.now().strftime('%d/%m/%Y %H:%M:%S'))
    logger.info("=" * 60)

    with app.app_context():

        # ── 1. Products (com aliases de_para) ──
        try:
            logger.info("[1/4] Reindexando produtos...")
            from app.embeddings.indexers.product_indexer import collect_products, index_products

            produtos, _total = collect_products()
            if produtos:
                stats = index_products(produtos)
                resultados['products'] = stats
                logger.info("   Produtos: %d novos/atualizados, %d skipped",
                            stats.get('embedded', 0), stats.get('skipped', 0))
            else:
                resultados['products'] = {'embedded': 0, 'skipped': 0}
                logger.info("   Nenhum produto para indexar")
        except Exception as e:
            logger.error("   Erro em products: %s", e, exc_info=True)
            resultados['products'] = {'error': str(e)}

        # ── 2. Financial Entities ──
        try:
            logger.info("[2/4] Reindexando entidades financeiras...")
            from app.embeddings.indexers.entity_indexer import collect_entities, index_entities

            entities, _stats_collect = collect_entities()
            if entities:
                stats = index_entities(entities)
                resultados['entities'] = stats
                logger.info("   Entidades: %d novas, %d skipped",
                            stats.get('embedded', 0), stats.get('skipped', 0))
            else:
                resultados['entities'] = {'embedded': 0, 'skipped': 0}
                logger.info("   Nenhuma entidade para indexar")
        except Exception as e:
            logger.error("   Erro em entities: %s", e, exc_info=True)
            resultados['entities'] = {'error': str(e)}

        # ── 3. Session Turns (catch-up) ──
        try:
            logger.info("[3/4] Catch-up session turns...")
            from app.embeddings.indexers.session_turn_indexer import collect_turns, index_turns

            turns, _stats_collect = collect_turns()
            if turns:
                stats = index_turns(turns)
                resultados['session_turns'] = stats
                logger.info("   Turns: %d novos, %d skipped",
                            stats.get('embedded', 0), stats.get('skipped', 0))
            else:
                resultados['session_turns'] = {'embedded': 0, 'skipped': 0}
                logger.info("   Nenhum turn para indexar")
        except Exception as e:
            logger.error("   Erro em session_turns: %s", e, exc_info=True)
            resultados['session_turns'] = {'error': str(e)}

        # ── 4. Agent Memories (catch-up) ──
        try:
            logger.info("[4/4] Catch-up memorias...")
            from app.embeddings.indexers.memory_indexer import collect_memories, index_memories

            memories, _stats_collect = collect_memories()
            if memories:
                stats = index_memories(memories)
                resultados['memories'] = stats
                logger.info("   Memorias: %d novas/atualizadas, %d skipped",
                            stats.get('embedded', 0), stats.get('skipped', 0))
            else:
                resultados['memories'] = {'embedded': 0, 'skipped': 0}
                logger.info("   Nenhuma memoria para indexar")
        except Exception as e:
            logger.error("   Erro em memories: %s", e, exc_info=True)
            resultados['memories'] = {'error': str(e)}

    # ── Resumo ──
    elapsed = time.time() - inicio
    erros = sum(1 for v in resultados.values() if 'error' in v)

    logger.info("=" * 60)
    logger.info("REINDEXACAO COMPLETA em %.1fs (%d erros)", elapsed, erros)
    for key, stats in resultados.items():
        if 'error' in stats:
            logger.info("   %s: ERRO - %s", key, str(stats['error'])[:80])
        else:
            logger.info("   %s: %d embedded, %d skipped",
                        key, stats.get('embedded', 0), stats.get('skipped', 0))
    logger.info("=" * 60)

    return resultados
