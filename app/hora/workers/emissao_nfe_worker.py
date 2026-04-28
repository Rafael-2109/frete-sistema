"""Worker RQ para emissao TagPlus.

Funcoes invocadas por jobs RQ:
  - processar_emissao(emissao_id)        — POST /nfes
  - processar_webhook(conta_id, event_type, data)  — handler webhook
  - polling_emissao(emissao_id)          — pingo TagPlus ate status final
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def _ensure_app_context():
    """Garante app_context. RQ pode invocar fora do contexto Flask."""
    from flask import current_app
    try:
        current_app._get_current_object()  # noqa: SLF001
        return None  # ja temos contexto
    except RuntimeError:
        from app import create_app
        app = create_app()
        ctx = app.app_context()
        ctx.push()
        return ctx


def processar_emissao(emissao_id: int) -> None:
    """Job RQ: chama EmissorNfeHora.processar."""
    ctx = _ensure_app_context()
    try:
        from app.hora.services.tagplus.emissor_nfe import EmissorNfeHora
        EmissorNfeHora.processar(emissao_id)
    finally:
        if ctx is not None:
            ctx.pop()


def processar_webhook(conta_id: int, event_type: str, data: list) -> None:
    """Job RQ: chama WebhookHandler.processar."""
    ctx = _ensure_app_context()
    try:
        from app.hora.services.tagplus.webhook_handler import WebhookHandler
        WebhookHandler.processar(conta_id, event_type, data)
    finally:
        if ctx is not None:
            ctx.pop()


# Backoff de polling: (limite_decorrido_segundos, proximo_delay_segundos).
# Inicio agressivo (10s) cobrindo casos triviais; depois afrouxa para nao
# bombardear API. Apos 1h desiste — cron de reconciliacao (30min) cuida.
_POLLING_BACKOFF = (
    (30,    10),    # ate 30s desde envio  -> proximo poll em 10s
    (120,   30),    # 30s-2min            -> 30s
    (600,   120),   # 2min-10min          -> 2min
    (3600,  300),   # 10min-1h            -> 5min
)


def _calcular_delay_polling(decorrido_segundos: float) -> int:
    """Retorna proximo delay (segundos) ou 0 se deve parar de pollar."""
    for limite, delay in _POLLING_BACKOFF:
        if decorrido_segundos < limite:
            return delay
    return 0  # alem de 1h: desiste


def polling_emissao(emissao_id: int) -> None:
    """Job RQ: puxa status atual do TagPlus e auto-reagenda com backoff.

    Para de re-agendar quando atinge status final (APROVADA, CANCELADA,
    REJEITADA_*, ERRO_INFRA) ou quando passa de 1h desde o envio (ai o cron
    periodico de reconciliacao assume).

    Idempotente: se o webhook ja chegou e marcou como APROVADA, polling vai
    ler status final e simplesmente nao re-agendar.
    """
    ctx = _ensure_app_context()
    try:
        from app.hora.models.tagplus import (
            HoraTagPlusNfeEmissao,
            NFE_STATUS_ENVIADA_SEFAZ,
            NFE_STATUS_CANCELAMENTO_SOLICITADO,
        )
        from app.hora.workers.reconciliacao_worker import reconciliar_uma_emissao
        from app.hora.services.tagplus.emissor_nfe import EmissorNfeHora
        from app.utils.timezone import agora_utc_naive

        emissao = HoraTagPlusNfeEmissao.query.get(emissao_id)
        if not emissao:
            return

        # Status final ou intermediario que nao polla
        if emissao.status not in (
            NFE_STATUS_ENVIADA_SEFAZ, NFE_STATUS_CANCELAMENTO_SOLICITADO,
        ):
            return
        if not emissao.tagplus_nfe_id:
            return

        # Marco temporal: para envio normal usa enviado_em; para
        # CANCELAMENTO_SOLICITADO usa cancelamento_solicitado_em.
        marco = emissao.enviado_em
        if emissao.status == NFE_STATUS_CANCELAMENTO_SOLICITADO:
            marco = emissao.cancelamento_solicitado_em or marco
        if not marco:
            marco = emissao.criado_em

        decorrido = (agora_utc_naive() - marco).total_seconds() if marco else 0
        proximo_delay = _calcular_delay_polling(decorrido)
        if proximo_delay == 0:
            logger.info(
                'polling_emissao: emissao=%s desistiu apos %.0fs (cron assume)',
                emissao_id, decorrido,
            )
            return

        resultado = reconciliar_uma_emissao(emissao_id)
        if resultado.get('acao_aplicada'):
            logger.info(
                'polling_emissao: emissao=%s resolvida (%s) apos %.0fs',
                emissao_id, resultado['acao_aplicada'], decorrido,
            )
            return

        # Ainda em processamento — re-agenda.
        EmissorNfeHora._enqueue_polling(emissao_id, delay=proximo_delay)  # noqa: SLF001
    finally:
        if ctx is not None:
            ctx.pop()
