"""
Job RQ: Sincronizacao de Entregas em Lote
==========================================

Enfileirado pelo FaturamentoService.sincronizar_faturamento_incremental() apos
persistir NFs novas/atualizadas. Substitui o loop sincrono (gargalo O4, 2026-04-14)
que bloqueava o Step 1 do scheduler chamando sincronizar_entrega_por_nf() para
cada NF dentro do ciclo de 30 minutos.

Fluxo:
1. FaturamentoService identifica NFs novas e atualizadas
2. Apos commit, enfileira sincronizar_entregas_batch(nfs) na fila 'default'
3. RQ worker pega o job e processa as entregas em background
4. Scheduler segue para Step 2 (Carteira) sem esperar

Fila 'default': consumida por sistema-fretes-worker-atacadao conforme
start_worker_render.sh (--queues atacadao,odoo_lancamento,impostos,recebimento,high,default).

Beneficio: libera o scheduler mais cedo e paraleliza com o worker RQ,
sem aumentar carga no Odoo (nao ha chamada Odoo nesta etapa — apenas SQL local).
"""

import logging
from typing import List

logger = logging.getLogger(__name__)

QUEUE_NAME = 'default'
JOB_TIMEOUT = '15m'


def sincronizar_entregas_batch(nfs: List[str]) -> dict:
    """
    Processa sincronizacao de entregas para um lote de NFs.

    Executa dentro de app_context (criado aqui porque RQ worker nao fornece).

    Args:
        nfs: Lista de numeros de NF para sincronizar

    Returns:
        Dict com estatisticas: {sucesso, total, erros}
    """
    from app import create_app

    if not nfs:
        return {'sucesso': 0, 'total': 0, 'erros': []}

    app = create_app()
    with app.app_context():
        from app.utils.sincronizar_entregas import sincronizar_entrega_por_nf

        stats = {
            'sucesso': 0,
            'total': len(nfs),
            'erros': []
        }

        logger.info(f"[JOB sincronizar_entregas_batch] Iniciando processamento de {len(nfs)} NFs")

        for numero_nf in nfs:
            try:
                sincronizar_entrega_por_nf(numero_nf)
                stats['sucesso'] += 1
            except Exception as e:
                erro_msg = f"NF {numero_nf}: {str(e)[:200]}"
                logger.error(f"[JOB sincronizar_entregas_batch] {erro_msg}")
                stats['erros'].append(erro_msg)

        logger.info(
            f"[JOB sincronizar_entregas_batch] Concluido: "
            f"{stats['sucesso']}/{stats['total']} NFs sincronizadas "
            f"({len(stats['erros'])} erros)"
        )
        return stats
