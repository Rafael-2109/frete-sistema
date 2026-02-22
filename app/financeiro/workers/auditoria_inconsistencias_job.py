# -*- coding: utf-8 -*-
"""
Worker: Auditoria de Inconsistências Local × Odoo
==================================================

Job RQ para detecção periódica de inconsistências em contas_a_receber.

Uso manual:
    python -c "
    from app.financeiro.workers.auditoria_inconsistencias_job import executar_auditoria_inconsistencias
    executar_auditoria_inconsistencias()
    "

Uso via RQ:
    from app.portal.workers import enqueue_job
    from app.financeiro.workers.auditoria_inconsistencias_job import executar_auditoria_inconsistencias
    enqueue_job(executar_auditoria_inconsistencias, queue_name='default', timeout='10m')

Data: 2026-02-21
"""

import logging

from app.financeiro.workers.utils import app_context_safe

logger = logging.getLogger(__name__)


def executar_auditoria_inconsistencias(
    empresa: int = None,
    dry_run: bool = False,
    apenas_pagos: bool = True,
) -> dict:
    """
    Job: Detecta inconsistências Local × Odoo.

    Args:
        empresa: Filtrar por empresa (1=FB, 2=SC, 3=CD). None = todas.
        dry_run: Se True, apenas lista sem atualizar flags.
        apenas_pagos: Se True, verifica apenas registros com parcela_paga=True.

    Returns:
        Dict com estatísticas da auditoria.
    """
    with app_context_safe():
        from app.financeiro.services.auditoria_inconsistencias_service import (
            AuditoriaInconsistenciasService,
        )

        logger.info(
            f"[AuditoriaJob] Iniciando (empresa={empresa}, "
            f"dry_run={dry_run}, apenas_pagos={apenas_pagos})"
        )

        service = AuditoriaInconsistenciasService()
        resultado = service.detectar_inconsistencias(
            empresa=empresa,
            dry_run=dry_run,
            apenas_pagos=apenas_pagos,
        )

        logger.info(
            f"[AuditoriaJob] Concluído — "
            f"{resultado.get('inconsistencias_detectadas', 0)} detectadas, "
            f"{resultado.get('inconsistencias_limpas', 0)} resolvidas, "
            f"{resultado.get('duracao_segundos', 0)}s"
        )

        # Remover lista detalhada do resultado para não sobrecarregar Redis
        resultado.pop('inconsistencias', None)

        return resultado


def limpar_inconsistencias_resolvidas(empresa: int = None) -> dict:
    """
    Job: Re-verifica registros flagados e limpa os resolvidos.

    Args:
        empresa: Filtrar por empresa. None = todas.

    Returns:
        Dict com contagens de limpas/mantidas.
    """
    with app_context_safe():
        from app.financeiro.services.auditoria_inconsistencias_service import (
            AuditoriaInconsistenciasService,
        )

        logger.info(f"[AuditoriaJob] Limpando inconsistências resolvidas (empresa={empresa})")

        service = AuditoriaInconsistenciasService()
        resultado = service.limpar_inconsistencias_resolvidas(empresa=empresa)

        logger.info(
            f"[AuditoriaJob] Limpeza concluída — "
            f"{resultado.get('limpas', 0)} limpas, "
            f"{resultado.get('mantidas', 0)} mantidas"
        )

        return resultado
