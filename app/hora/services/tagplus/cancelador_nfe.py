"""Cancelamento de NFe ja aprovada via PATCH /nfes/cancelar/{id}.

Regras (scripts/doc_tagplus.md:2467+):
- Prazo SEFAZ: 24h apos aprovacao para cancelamento simples.
- Justificativa obrigatoria com >= 15 caracteres.
- Confirmacao SEFAZ chega via webhook nfe_cancelada (assincrono).
"""
from __future__ import annotations

import logging

from app import db
from app.hora.models.tagplus import (
    HoraTagPlusNfeEmissao,
    NFE_STATUS_APROVADA,
    NFE_STATUS_CANCELADA,
    NFE_STATUS_CANCELAMENTO_SOLICITADO,
)
from app.hora.services.tagplus.api_client import ApiClient
from app.utils.json_helpers import sanitize_for_json
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)


JUSTIFICATIVA_MIN = 15


class CancelamentoBloqueadoError(Exception):
    pass


class CanceladorNfe:
    @staticmethod
    def cancelar(emissao_id: int, justificativa: str, usuario: str) -> HoraTagPlusNfeEmissao:
        """Solicita cancelamento ao TagPlus.

        Estado intermediario: NFE_STATUS_CANCELAMENTO_SOLICITADO.
        Confirmacao final (NFE_STATUS_CANCELADA) vem via webhook nfe_cancelada.
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
            # Append em response_inicial sem perder o original.
            existente = emissao.response_inicial or {}
            if not isinstance(existente, dict):
                existente = {'_original': existente}
            existente['_cancelamento_solicitado'] = sanitize_for_json(body)
            emissao.response_inicial = sanitize_for_json(existente)
            db.session.commit()
            logger.info(
                'Cancelamento solicitado emissao=%s tagplus_id=%s usuario=%s',
                emissao.id, emissao.tagplus_nfe_id, usuario,
            )
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
