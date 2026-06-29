"""Cron da descoberta reversa HORA<->TagPlus (Fase 3, numero-walk +3).

Entry point para agendamento periodico (RQ scheduler / crontab Render, padrao
do `reconciliacao_worker.reconciliar_emissoes_job`). Descobre pedidos criados
direto no TagPlus e os replica como HoraVenda INCOMPLETO (origem TAGPLUS).

GATE: roda apenas com a flag HORA_TAGPLUS_REVERSO ligada (default OFF) — a
descoberta CRIA vendas, entao fica desligada ate o numero-walk ser validado em
PROD. Independente da flag de push/to_nfe (HORA_TAGPLUS_PUSH_PEDIDO).

Agendamento (acao de infra, nao automatica): registrar um cron (ex.: 30min)
que invoque `descobrir_e_replicar_job`, espelhando o cron de reconciliacao.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def descobrir_e_replicar_job() -> dict:
    """1 ciclo da descoberta reversa. Wrapper create_app (cron / crontab).

    Retorna stats: {flag_off, replicados, numeros}.
    """
    from app import create_app
    app = create_app()
    with app.app_context():
        from app.hora.services.tagplus import pedido_reverso_service as rev

        if not rev.reverso_habilitado():
            logger.info(
                'descobrir_e_replicar_job: flag HORA_TAGPLUS_REVERSO OFF — skip.'
            )
            return {'flag_off': True, 'replicados': 0, 'numeros': []}

        from app.hora.models.tagplus import HoraTagPlusConta
        from app.hora.services.tagplus.api_client import ApiClient

        conta = HoraTagPlusConta.ativa()
        replicados = rev.descobrir_e_replicar(ApiClient(conta), conta)
        numeros = [v.tagplus_pedido_numero for v in replicados]
        logger.info('descobrir_e_replicar_job: %s replicado(s) %s', len(replicados), numeros)
        return {'flag_off': False, 'replicados': len(replicados), 'numeros': numeros}
