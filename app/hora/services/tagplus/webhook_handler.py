"""Processa webhooks do TagPlus (nfe_aprovada, nfe_denegada, nfe_cancelada).

Race-safe: se o webhook chegar antes do commit local do worker que fez o POST,
o handler enfileira retry com 10s de delay (combina com job de reconciliacao
periodica para webhooks completamente perdidos).

Nota: TagPlus dispara `nfe_denegada` (nao `nfe_rejeitada`) — ver
`scripts/webhook.md` (commit db212bab). Internamente mapeamos para
status `REJEITADA_SEFAZ` (rejeicao generica de SEFAZ).
"""
from __future__ import annotations

import logging
from typing import Optional

from app import db
from app.hora.models.moto import HoraMotoEvento
from app.hora.models.tagplus import (
    HoraTagPlusConta,
    HoraTagPlusNfeEmissao,
    NFE_STATUS_APROVADA,
    NFE_STATUS_CANCELADA,
    NFE_STATUS_REJEITADA_SEFAZ,
)
from app.hora.services.tagplus.api_client import ApiClient
from app.utils.json_helpers import sanitize_for_json
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)


EVENT_NFE_APROVADA = 'nfe_aprovada'
EVENT_NFE_DENEGADA = 'nfe_denegada'
EVENT_NFE_CANCELADA = 'nfe_cancelada'


class WebhookHandler:
    @staticmethod
    def processar(conta_id: int, event_type: str, data: list[dict]) -> None:
        conta = HoraTagPlusConta.query.get(conta_id)
        if not conta:
            logger.warning('Webhook conta_id=%s nao encontrado', conta_id)
            return

        client = ApiClient(conta)

        # Commita por item — falha em 1 nao perde os outros.
        for item in data or []:
            tagplus_nfe_id = WebhookHandler._coerce_id(item)
            if tagplus_nfe_id is None:
                logger.warning('Webhook com id invalido: %r', item)
                continue

            emissao = (
                HoraTagPlusNfeEmissao.query
                .filter_by(tagplus_nfe_id=tagplus_nfe_id)
                .first()
            )

            if not emissao:
                # Race: POST /nfes ainda nao commitou localmente.
                logger.info(
                    'Webhook chegou antes do commit local (tagplus_id=%s, event=%s) — '
                    'enfileirando retry +10s', tagplus_nfe_id, event_type,
                )
                from app.hora.services.tagplus.emissor_nfe import EmissorNfeHora
                EmissorNfeHora._enqueue_webhook(conta_id, event_type, item, delay=10)  # noqa: SLF001
                continue

            try:
                if event_type == EVENT_NFE_APROVADA:
                    WebhookHandler._handle_aprovada(emissao, client, tagplus_nfe_id)
                elif event_type == EVENT_NFE_DENEGADA:
                    WebhookHandler._handle_denegada(emissao, client, tagplus_nfe_id)
                elif event_type == EVENT_NFE_CANCELADA:
                    WebhookHandler._handle_cancelada(emissao, client, tagplus_nfe_id)
                else:
                    logger.warning('Evento desconhecido: %s', event_type)
                    continue
                db.session.commit()
            except Exception:
                logger.exception(
                    'Falha processando item webhook event=%s tagplus_id=%s',
                    event_type, tagplus_nfe_id,
                )
                db.session.rollback()
                # Continua para o proximo item.

    # ----------------------------------------------------------
    # Aprovada
    # ----------------------------------------------------------
    @staticmethod
    def _handle_aprovada(
        emissao: HoraTagPlusNfeEmissao,
        client: ApiClient,
        tagplus_nfe_id: int,
    ) -> None:
        # Idempotencia: se ja aprovada, nao re-processar (evita evento duplicado).
        if emissao.status == NFE_STATUS_APROVADA:
            logger.info(
                'Webhook nfe_aprovada para emissao %s ja APROVADA — skip',
                emissao.id,
            )
            return

        detalhes = WebhookHandler._buscar_detalhes(client, tagplus_nfe_id)

        emissao.status = NFE_STATUS_APROVADA
        emissao.aprovado_em = agora_utc_naive()
        emissao.response_webhook = sanitize_for_json(detalhes)

        # Estrategia defensiva: chave_44 e protocolo podem vir em varios nomes.
        emissao.chave_44 = (
            detalhes.get('chave_acesso')
            or detalhes.get('chave_nfe')
            or detalhes.get('chave')
            or emissao.chave_44
        )
        protocolo = (
            detalhes.get('protocolo_aprovacao')
            or detalhes.get('protocolo_autorizacao')
        )
        if not protocolo and isinstance(detalhes.get('protocolo'), dict):
            protocolo = detalhes['protocolo'].get('numero_protocolo')
        emissao.protocolo_aprovacao = protocolo
        if not emissao.numero_nfe:
            num = detalhes.get('numero')
            if num is not None:
                emissao.numero_nfe = str(num)
        if not emissao.serie_nfe:
            ser = detalhes.get('serie')
            if ser is not None:
                emissao.serie_nfe = str(ser)

        # Atualiza HoraVenda + emite eventos por chassi (idempotente: query antes).
        venda = emissao.venda
        if venda:
            venda.nf_saida_numero = emissao.numero_nfe
            if emissao.chave_44:
                venda.nf_saida_chave_44 = emissao.chave_44
            venda.nf_saida_emitida_em = emissao.aprovado_em

            # Idempotencia: nao duplica evento se ja registrado para esta emissao.
            chassis_existentes = {
                e.numero_chassi for e in HoraMotoEvento.query.filter_by(
                    origem_tabela='hora_tagplus_nfe_emissao',
                    origem_id=emissao.id,
                    tipo='NF_EMITIDA',
                ).all()
            }

            for vi in venda.itens:
                if vi.numero_chassi in chassis_existentes:
                    continue
                db.session.add(HoraMotoEvento(
                    numero_chassi=vi.numero_chassi,
                    tipo='NF_EMITIDA',
                    origem_tabela='hora_tagplus_nfe_emissao',
                    origem_id=emissao.id,
                    loja_id=venda.loja_id,
                    detalhe=(
                        f'NF {emissao.numero_nfe or "?"} '
                        f'chave {emissao.chave_44 or "?"}'
                    ),
                ))

        logger.info(
            'NFe aprovada emissao=%s nfe=%s chave=%s',
            emissao.id, emissao.numero_nfe, emissao.chave_44,
        )

    # ----------------------------------------------------------
    # Denegada (TagPlus emite `nfe_denegada` — internamente mapeia
    # para status REJEITADA_SEFAZ por compatibilidade com banco).
    # ----------------------------------------------------------
    @staticmethod
    def _handle_denegada(
        emissao: HoraTagPlusNfeEmissao,
        client: ApiClient,
        tagplus_nfe_id: int,
    ) -> None:
        if emissao.status == NFE_STATUS_REJEITADA_SEFAZ:
            return  # idempotente
        detalhes = WebhookHandler._buscar_detalhes(client, tagplus_nfe_id)
        emissao.status = NFE_STATUS_REJEITADA_SEFAZ
        emissao.response_webhook = sanitize_for_json(detalhes)
        emissao.error_message = WebhookHandler._extrair_motivo_denegacao(detalhes)
        logger.warning(
            'NFe denegada emissao=%s motivo=%s',
            emissao.id, emissao.error_message,
        )

    # ----------------------------------------------------------
    # Cancelada
    # ----------------------------------------------------------
    @staticmethod
    def _handle_cancelada(
        emissao: HoraTagPlusNfeEmissao,
        client: ApiClient,
        tagplus_nfe_id: int,
    ) -> None:
        # Idempotencia: se ja cancelada, nao re-processar.
        if emissao.status == NFE_STATUS_CANCELADA:
            logger.info(
                'Webhook nfe_cancelada para emissao %s ja CANCELADA — skip',
                emissao.id,
            )
            return

        detalhes = WebhookHandler._buscar_detalhes(client, tagplus_nfe_id)
        emissao.status = NFE_STATUS_CANCELADA
        emissao.cancelado_em = agora_utc_naive()
        emissao.response_webhook = sanitize_for_json(detalhes)

        # Evento por chassi (idempotente). Cancelar NFe NAO reverte a venda;
        # operador deve cancelar a venda separadamente via HoraVenda.
        venda = emissao.venda
        if venda:
            chassis_existentes = {
                e.numero_chassi for e in HoraMotoEvento.query.filter_by(
                    origem_tabela='hora_tagplus_nfe_emissao',
                    origem_id=emissao.id,
                    tipo='NF_CANCELADA',
                ).all()
            }
            for vi in venda.itens:
                if vi.numero_chassi in chassis_existentes:
                    continue
                db.session.add(HoraMotoEvento(
                    numero_chassi=vi.numero_chassi,
                    tipo='NF_CANCELADA',
                    origem_tabela='hora_tagplus_nfe_emissao',
                    origem_id=emissao.id,
                    loja_id=venda.loja_id,
                    detalhe=f'NF {emissao.numero_nfe or "?"} cancelada',
                ))

        logger.info('NFe cancelada emissao=%s', emissao.id)

    # ----------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------
    @staticmethod
    def _buscar_detalhes(client: ApiClient, tagplus_nfe_id: int) -> dict:
        try:
            r = client.get(f'/nfes/{tagplus_nfe_id}')
            if r.status_code == 200:
                return r.json() or {}
            logger.warning(
                'GET /nfes/%s status=%s body=%s',
                tagplus_nfe_id, r.status_code, r.text[:300],
            )
        except Exception as exc:
            logger.exception('Falha em GET /nfes/%s: %s', tagplus_nfe_id, exc)
        return {}

    @staticmethod
    def _coerce_id(item: dict) -> Optional[int]:
        # Webhook envia id como STRING (scripts/webhook.md:32). Converter.
        raw = item.get('id') if isinstance(item, dict) else None
        if raw is None:
            return None
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _extrair_motivo_denegacao(detalhes: dict) -> str:
        if not isinstance(detalhes, dict):
            return 'Denegacao sem detalhes — ver response_webhook.'
        candidatos = [
            detalhes.get('motivo_denegacao'),
            detalhes.get('motivo_rejeicao'),
            detalhes.get('motivo'),
            detalhes.get('mensagem_sefaz'),
            detalhes.get('xMotivo'),
        ]
        historico = detalhes.get('historico')
        if isinstance(historico, list) and historico:
            ult = historico[-1]
            if isinstance(ult, dict):
                candidatos.append(ult.get('descricao'))
                candidatos.append(ult.get('motivo'))
        for c in candidatos:
            if c:
                return str(c)[:1000]
        return 'Denegacao sem motivo identificavel — ver response_webhook.'
