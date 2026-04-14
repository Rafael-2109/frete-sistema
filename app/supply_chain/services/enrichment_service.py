"""
Enrichment Service — Enriquece eventos de auditoria com qtd_projetada_dia.

Chamado no FINAL de cada ciclo de sync, APOS o commit principal.
Calcula a projecao D0 (estoque atual) para cada produto tocado no sync
e atualiza os eventos correspondentes em batch.

Estrategia:
  1. SELECT DISTINCT cod_produto WHERE session_id = :sid AND qtd_projetada_dia IS NULL
  2. Calcular D0 via ServicoEstoqueSimples.calcular_estoque_atual() (1x por produto)
  3. UPDATE em batch: SET qtd_projetada_dia = :val WHERE session_id = :sid AND cod_produto = :cod

Graceful degradation: Se falhar, eventos ficam com qtd_projetada_dia=NULL.
O ML pode ignorar ou recalcular depois.
"""
import logging

from sqlalchemy import text

logger = logging.getLogger(__name__)


def enriquecer_projecao(session_id):
    """
    Enriquece eventos de um ciclo de sync com a projecao D0 de cada produto.

    DEVE ser chamado APOS o commit da operacao de negocio.
    Roda em sua propria transacao (commit independente).
    NUNCA propaga excecoes.

    Args:
        session_id: ID do ciclo de sync (gerado por gerar_session_id())
    """
    if not session_id or not session_id.strip():
        return

    try:
        from app import db

        # 1. Buscar produtos distintos sem projecao neste session
        result = db.session.execute(text(
            "SELECT DISTINCT cod_produto "
            "FROM evento_supply_chain "
            "WHERE session_id = :sid AND qtd_projetada_dia IS NULL AND cod_produto IS NOT NULL"
        ), {'sid': session_id}).fetchall()

        produtos = [r[0] for r in result]

        if not produtos:
            logger.debug(f"[ENRICH] Nenhum produto para enriquecer em {session_id}")
            return

        logger.info(f"[ENRICH] Enriquecendo {len(produtos)} produtos para session {session_id}")

        # 2. Calcular D0 para cada produto
        try:
            from app.estoque.services.estoque_simples import ServicoEstoqueSimples
        except ImportError:
            logger.warning("[ENRICH] ServicoEstoqueSimples nao disponivel — pulando enriquecimento")
            return

        atualizacoes = 0
        for cod_produto in produtos:
            try:
                estoque_d0 = ServicoEstoqueSimples.calcular_estoque_atual(cod_produto)

                if estoque_d0 is not None:
                    db.session.execute(text(
                        "UPDATE evento_supply_chain "
                        "SET qtd_projetada_dia = :qtd "
                        "WHERE session_id = :sid AND cod_produto = :cod AND qtd_projetada_dia IS NULL"
                    ), {
                        'qtd': float(estoque_d0),
                        'sid': session_id,
                        'cod': cod_produto,
                    })
                    atualizacoes += 1
            except Exception as e:
                logger.debug(f"[ENRICH] Erro ao calcular D0 para {cod_produto}: {e}")
                continue

        if atualizacoes > 0:
            db.session.commit()
            logger.info(f"[ENRICH] {atualizacoes}/{len(produtos)} produtos enriquecidos com projecao D0")
        else:
            logger.debug(f"[ENRICH] Nenhuma projecao calculada para session {session_id}")

    except Exception as e:
        logger.error(f"[ENRICH] Erro ao enriquecer projecao para {session_id}: {e}")
        try:
            from app import db
            db.session.rollback()
        except Exception:
            pass


def enqueue_enrichment(session_id):
    """
    Fire-and-forget: enfileira job RQ de enrichment para um session_id.

    Chamado por sync jobs Odoo (carteira, faturamento, compras) e rotas web
    apos commit da operacao principal. NUNCA propaga excecao — falha no
    enqueue (Redis offline, fila indisponivel) deve apenas logar e seguir.

    Fila: 'default' (ja consumida por worker_render.py e worker_atacadao.py).
    Timeout: 5m (enrichment tipicamente < 30s).
    Retry: None — se falhar, eventos ficam com qtd_projetada_dia=NULL (ML tolera).

    Args:
        session_id: ID do ciclo de sync (gerado por gerar_session_id())

    Returns:
        None. Logs sucesso (INFO) ou falha (ERROR).
    """
    if not session_id or not str(session_id).strip():
        return

    try:
        from app.portal.workers import enqueue_job
        from app.supply_chain.workers.enrichment_jobs import job_enriquecer_projecao

        enqueue_job(
            job_enriquecer_projecao,
            session_id,
            queue_name='default',
            timeout='5m',
            retry=None,
        )
        logger.info(f"[ENRICH] Job enfileirado para session={session_id}")
    except Exception as e:
        # Falha no enqueue NAO deve abortar o sync principal.
        # Graceful degradation: evento fica com qtd_projetada_dia=NULL.
        logger.error(f"[ENRICH] Falha ao enfileirar job para session={session_id}: {e}")
