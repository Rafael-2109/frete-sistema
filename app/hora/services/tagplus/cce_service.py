"""Carta de Correcao Eletronica (CC-e) — POST /nfes/gerar_cce/{id}.

Permite corrigir campos nao-financeiros (observacao, transportadora, etc.).
NUNCA permite alterar valor, destinatario ou descricao essencial do produto.

Texto da correcao: minimo 15 caracteres (regra SEFAZ).
"""
from __future__ import annotations

import logging

from app.hora.models.tagplus import HoraTagPlusNfeEmissao, NFE_STATUS_APROVADA
from app.hora.services.tagplus.api_client import ApiClient

logger = logging.getLogger(__name__)


CCE_TEXTO_MIN = 15


class CceError(Exception):
    pass


class CceService:
    @staticmethod
    def gerar(emissao_id: int, texto_correcao: str) -> dict:
        if not texto_correcao or len(texto_correcao.strip()) < CCE_TEXTO_MIN:
            raise ValueError(f'texto_correcao deve ter >= {CCE_TEXTO_MIN} caracteres.')

        emissao = HoraTagPlusNfeEmissao.query.get(emissao_id)
        if not emissao:
            raise CceError(f'Emissao {emissao_id} nao encontrada.')

        if emissao.status != NFE_STATUS_APROVADA:
            raise CceError(
                f'CC-e exige NFe APROVADA; estado atual: {emissao.status}.'
            )

        if not emissao.tagplus_nfe_id:
            raise CceError(f'Emissao {emissao_id} sem tagplus_nfe_id.')

        client = ApiClient(emissao.conta)
        response = client.post(
            f'/nfes/gerar_cce/{emissao.tagplus_nfe_id}',
            json={'descricao_correcao': texto_correcao.strip()},
        )

        try:
            body = response.json()
        except ValueError:
            body = {'_raw': response.text[:500]}

        if response.status_code in (200, 201, 202):
            logger.info(
                'CC-e emitida emissao=%s tagplus_id=%s',
                emissao.id, emissao.tagplus_nfe_id,
            )
            return body if isinstance(body, dict) else {'_raw': body}

        raise CceError(
            f'TagPlus respondeu {response.status_code}: {str(body)[:300]}'
        )
