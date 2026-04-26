"""Reconciliacao de webhooks perdidos.

Roda periodicamente (cron 30min). Reconsulta SEFAZ via GET /nfes/{id} para
emissoes em ENVIADA_SEFAZ ha mais de 10 minutos sem retorno do webhook.

Detalhes: app/hora/EMISSAO_NFE_ENGENHARIA.md secao 5.5.1.
"""
from __future__ import annotations

import logging
from datetime import timedelta

from app.hora.models.tagplus import (
    HoraTagPlusConta,
    HoraTagPlusNfeEmissao,
    NFE_STATUS_ENVIADA_SEFAZ,
    NFE_STATUS_CANCELAMENTO_SOLICITADO,
)
from app.hora.services.tagplus.api_client import ApiClient
from app.hora.services.tagplus.webhook_handler import (
    WebhookHandler,
    EVENT_NFE_APROVADA,
    EVENT_NFE_CANCELADA,
    EVENT_NFE_REJEITADA,
)
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)


# Status SEFAZ na resposta da API TagPlus (scripts/doc_tagplus.md):
#   A = Aprovada
#   S = Cancelada
#   2 = Denegada
#   4 = Rejeitada
#   N / E / D = Em digitacao / processamento / pendente
_STATUS_APROVADO = {'A', 'aprovada', 'APROVADA'}
_STATUS_CANCELADO = {'S', 'cancelada', 'CANCELADA'}
_STATUS_REJEITADO = {'2', '4', 'rejeitada', 'REJEITADA', 'denegada', 'DENEGADA'}


def reconciliar_enviadas(limit: int = 100) -> dict:
    """Roda 1 ciclo de reconciliacao. Retorna stats."""
    limite_envio = agora_utc_naive() - timedelta(minutes=10)

    pendentes_envio = (
        HoraTagPlusNfeEmissao.query
        .filter(HoraTagPlusNfeEmissao.status == NFE_STATUS_ENVIADA_SEFAZ)
        .filter(HoraTagPlusNfeEmissao.enviado_em < limite_envio)
        .filter(HoraTagPlusNfeEmissao.tagplus_nfe_id.isnot(None))
        .limit(limit)
        .all()
    )

    pendentes_cancelamento = (
        HoraTagPlusNfeEmissao.query
        .filter(HoraTagPlusNfeEmissao.status == NFE_STATUS_CANCELAMENTO_SOLICITADO)
        .filter(HoraTagPlusNfeEmissao.cancelamento_solicitado_em < limite_envio)
        .filter(HoraTagPlusNfeEmissao.tagplus_nfe_id.isnot(None))
        .limit(limit)
        .all()
    )

    pendentes = pendentes_envio + pendentes_cancelamento
    if not pendentes:
        logger.info('Reconciliacao: nenhuma emissao pendente.')
        return {'reconciliadas': 0, 'aprovadas': 0, 'rejeitadas': 0, 'canceladas': 0}

    stats = {'reconciliadas': 0, 'aprovadas': 0, 'rejeitadas': 0, 'canceladas': 0}

    # Agrupa por conta para reaproveitar token.
    por_conta: dict[int, list[HoraTagPlusNfeEmissao]] = {}
    for em in pendentes:
        por_conta.setdefault(em.conta_id, []).append(em)

    for conta_id, emissoes in por_conta.items():
        conta = HoraTagPlusConta.query.get(conta_id)
        if not conta:
            continue
        client = ApiClient(conta)
        for emissao in emissoes:
            try:
                r = client.get(f'/nfes/{emissao.tagplus_nfe_id}')
                if r.status_code != 200:
                    continue
                detalhes = r.json() or {}
                status_api = (detalhes.get('status') or detalhes.get('situacao') or '')
                stats['reconciliadas'] += 1

                evento_simulado = [{'id': str(emissao.tagplus_nfe_id)}]

                if status_api in _STATUS_APROVADO:
                    WebhookHandler.processar(conta_id, EVENT_NFE_APROVADA, evento_simulado)
                    stats['aprovadas'] += 1
                elif status_api in _STATUS_CANCELADO:
                    WebhookHandler.processar(conta_id, EVENT_NFE_CANCELADA, evento_simulado)
                    stats['canceladas'] += 1
                elif status_api in _STATUS_REJEITADO:
                    WebhookHandler.processar(conta_id, EVENT_NFE_REJEITADA, evento_simulado)
                    stats['rejeitadas'] += 1
                # Status em-andamento: aguarda proximo ciclo.

            except Exception as exc:
                logger.exception(
                    'Erro reconciliando emissao=%s tagplus=%s: %s',
                    emissao.id, emissao.tagplus_nfe_id, exc,
                )

    logger.info('Reconciliacao concluida: %s', stats)
    return stats


def reconciliar_emissoes_job() -> dict:
    """Wrapper para invocacao via RQ scheduler / crontab."""
    from app import create_app
    app = create_app()
    with app.app_context():
        return reconciliar_enviadas()
