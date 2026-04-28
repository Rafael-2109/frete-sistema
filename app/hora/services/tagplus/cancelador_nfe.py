"""Cancelamento de NFe ja aprovada via PATCH /nfes/cancelar/{id}.

Regras:
- Prazo SEFAZ: 24h apos aprovacao para cancelamento simples (validado LOCAL
  em _validar_janela + validado novamente pela SEFAZ via TagPlus).
- Justificativa obrigatoria com >= 15 caracteres.
- Confirmacao SEFAZ chega via webhook nfe_cancelada (assincrono).
- Auditoria: registra acao CANCELOU_NFE em hora_venda_auditoria.
"""
from __future__ import annotations

import logging
from datetime import timedelta

from app import db
from app.hora.models.tagplus import (
    HoraTagPlusNfeEmissao,
    NFE_STATUS_APROVADA,
    NFE_STATUS_CANCELADA,
    NFE_STATUS_CANCELAMENTO_SOLICITADO,
)
from app.hora.services import venda_audit
from app.hora.services.tagplus.api_client import ApiClient
from app.utils.json_helpers import sanitize_for_json
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)


JUSTIFICATIVA_MIN = 15
JANELA_CANCELAMENTO_HORAS = 24


class CancelamentoBloqueadoError(Exception):
    pass


class CanceladorNfe:
    @staticmethod
    def _validar_janela(emissao: HoraTagPlusNfeEmissao) -> None:
        """Levanta CancelamentoBloqueadoError se a janela de 24h ja passou.

        Janela e contada a partir de aprovado_em (timestamp setado pelo webhook
        nfe_aprovada). Se aprovado_em e NULL (estado inconsistente), bloqueia
        para forcar reconciliacao manual.
        """
        if not emissao.aprovado_em:
            raise CancelamentoBloqueadoError(
                f'Emissao {emissao.id} sem aprovado_em — reconciliar antes de cancelar.'
            )
        decorrido = agora_utc_naive() - emissao.aprovado_em
        if decorrido > timedelta(hours=JANELA_CANCELAMENTO_HORAS):
            horas = decorrido.total_seconds() / 3600.0
            raise CancelamentoBloqueadoError(
                f'Janela SEFAZ de {JANELA_CANCELAMENTO_HORAS}h encerrada '
                f'(transcorridas {horas:.1f}h desde aprovacao). '
                'Trate como devolucao em /hora/devolucoes.'
            )

    @staticmethod
    def cancelar(emissao_id: int, justificativa: str, usuario: str) -> HoraTagPlusNfeEmissao:
        """Solicita cancelamento ao TagPlus.

        Validacoes locais (antes de qualquer chamada HTTP):
          - justificativa >= 15 chars (SEFAZ)
          - status == APROVADA
          - tagplus_nfe_id presente
          - janela de 24h desde aprovado_em (alem da SEFAZ que tambem valida)

        Estado intermediario: NFE_STATUS_CANCELAMENTO_SOLICITADO.
        Confirmacao final (NFE_STATUS_CANCELADA) vem via webhook nfe_cancelada.
        Auditoria: CANCELOU_NFE.
        """
        if not justificativa or len(justificativa.strip()) < JUSTIFICATIVA_MIN:
            raise ValueError(
                f'Justificativa deve ter >= {JUSTIFICATIVA_MIN} caracteres '
                f'(SEFAZ exige).'
            )

        emissao = HoraTagPlusNfeEmissao.query.get(emissao_id)
        if not emissao:
            raise CancelamentoBloqueadoError(f'Emissao {emissao_id} nao encontrada.')

        if emissao.status not in (NFE_STATUS_APROVADA,):
            raise CancelamentoBloqueadoError(
                f'NFe em status {emissao.status} nao pode ser cancelada. '
                f'So APROVADA aceita cancelamento.'
            )

        if not emissao.tagplus_nfe_id:
            raise CancelamentoBloqueadoError(
                f'Emissao {emissao_id} sem tagplus_nfe_id — sincronizar via reconciliacao.'
            )

        CanceladorNfe._validar_janela(emissao)

        client = ApiClient(emissao.conta)
        response = client.patch(
            f'/nfes/cancelar/{emissao.tagplus_nfe_id}',
            json={'justificativa': justificativa.strip()},
        )

        try:
            body = response.json()
        except ValueError:
            body = {'_raw': response.text[:500]}

        if response.status_code in (200, 202):
            emissao.status = NFE_STATUS_CANCELAMENTO_SOLICITADO
            emissao.cancelamento_justificativa = justificativa.strip()
            emissao.cancelamento_solicitado_por = usuario
            emissao.cancelamento_solicitado_em = agora_utc_naive()
            existente = emissao.response_inicial or {}
            if not isinstance(existente, dict):
                existente = {'_original': existente}
            existente['_cancelamento_solicitado'] = sanitize_for_json(body)
            emissao.response_inicial = sanitize_for_json(existente)

            venda_audit.registrar_auditoria(
                venda_id=emissao.venda_id, usuario=usuario,
                acao='CANCELOU_NFE',
                detalhe=(
                    f'Justificativa: {justificativa.strip()[:200]} | '
                    f'tagplus_nfe_id={emissao.tagplus_nfe_id}'
                ),
            )

            db.session.commit()
            logger.info(
                'Cancelamento solicitado emissao=%s tagplus_id=%s usuario=%s',
                emissao.id, emissao.tagplus_nfe_id, usuario,
            )
            # Polling para puxar nfe_cancelada se webhook nao chegar.
            from app.hora.services.tagplus.emissor_nfe import EmissorNfeHora
            EmissorNfeHora._enqueue_polling(emissao.id, delay=10)  # noqa: SLF001
            return emissao

        logger.error(
            'Cancelamento falhou status=%s body=%s',
            response.status_code, str(body)[:500],
        )
        raise CancelamentoBloqueadoError(
            f'TagPlus respondeu {response.status_code}: {str(body)[:300]}'
        )

    @staticmethod
    def confirmar_cancelamento(emissao_id: int) -> None:
        """Marca como CANCELADA apos webhook nfe_cancelada."""
        emissao = HoraTagPlusNfeEmissao.query.get(emissao_id)
        if not emissao:
            return
        emissao.status = NFE_STATUS_CANCELADA
        emissao.cancelado_em = agora_utc_naive()
        db.session.commit()
