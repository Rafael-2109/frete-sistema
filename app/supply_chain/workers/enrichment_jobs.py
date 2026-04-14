"""
Jobs RQ para enriquecimento de eventos de supply chain.

Convertem chamadas sincronas pos-commit em processamento assincrono,
libertando o caller (sync jobs Odoo, rotas web) do custo de calcular
qtd_projetada_dia. Fila padrao: 'default' (ja consumida por worker_render.py
e worker_atacadao.py — sem necessidade de infra adicional).

Padrao seguido: app/recebimento/workers/recebimento_lf_jobs.py
(create_app + app_context dentro do job).
"""
import logging

logger = logging.getLogger(__name__)


def job_enriquecer_projecao(session_id: str) -> dict:
    """
    Job RQ: enriquece eventos de um ciclo de sync com qtd_projetada_dia.

    Chamado via enqueue_job() apos commit da operacao principal.
    NUNCA chamado diretamente — sempre via fila RQ (worker separado
    processa, o caller nao espera).

    A funcao enriquecer_projecao() ja tem try/except global e commit
    proprio — este wrapper so garante app_context e loga resultado.

    Args:
        session_id: ID do ciclo de sync (gerado por gerar_session_id())

    Returns:
        dict com status da execucao (consumido por RQ para log/debug).
    """
    from app import create_app

    app = create_app()
    with app.app_context():
        try:
            from app.supply_chain.services.enrichment_service import enriquecer_projecao
            enriquecer_projecao(session_id)
            logger.info(f"[JOB_ENRICH] Enrichment concluido para session={session_id}")
            return {'session_id': session_id, 'status': 'ok'}
        except Exception as e:
            logger.error(f"[JOB_ENRICH] Falha para session={session_id}: {e}")
            return {'session_id': session_id, 'status': 'erro', 'erro': str(e)}
