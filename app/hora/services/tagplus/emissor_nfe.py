"""EmissorNfeHora — orquestra enfileiramento e processamento de emissao.

Fluxo (alto nivel):
  1) `enfileirar(venda_id)` — cria/reaproveita HoraTagPlusNfeEmissao + push RQ.
     Idempotente: bloqueia em status APROVADA/EM_ENVIO/ENVIADA_SEFAZ.
  2) Worker chama `processar(emissao_id)`:
     - PayloadBuilder.build()
     - POST /nfes
     - 201/202 -> ENVIADA_SEFAZ
     - 4xx     -> REJEITADA_LOCAL
     - 5xx/timeout -> ERRO_INFRA (RQ retry com backoff)
     - Webhook chega depois -> APROVADA / REJEITADA_SEFAZ.

Detalhes: app/hora/EMISSAO_NFE_ENGENHARIA.md secoes 5.1-5.4.
"""
from __future__ import annotations

import logging
import os
from datetime import timedelta

from requests.exceptions import ConnectionError as ReqConnError, Timeout

from app import db
from app.hora.models.tagplus import (
    HoraTagPlusConta,
    HoraTagPlusNfeEmissao,
    NFE_STATUS_APROVADA,
    NFE_STATUS_CANCELADA,
    NFE_STATUS_CANCELAMENTO_SOLICITADO,
    NFE_STATUS_EM_ENVIO,
    NFE_STATUS_ENVIADA_SEFAZ,
    NFE_STATUS_ERRO_INFRA,
    NFE_STATUS_PENDENTE,
    NFE_STATUS_REJEITADA_LOCAL,
    NFE_STATUS_REJEITADA_SEFAZ,
)
from app.hora.models.venda import (
    HoraVenda,
    VENDA_STATUS_CONFIRMADO,
    VENDA_STATUS_FATURADO,
)
from app.hora.services import venda_audit
from app.hora.services.tagplus.payload_builder import PayloadBuilder, PayloadBuilderError
from app.utils.json_helpers import sanitize_for_json
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)


# Status que NAO podem ser re-enfileirados (idempotencia em double-click / retry manual).
_STATUS_BLOQUEIA_REENFILEIRA = (
    NFE_STATUS_APROVADA,
    NFE_STATUS_EM_ENVIO,
    NFE_STATUS_ENVIADA_SEFAZ,
    NFE_STATUS_CANCELAMENTO_SOLICITADO,
    NFE_STATUS_CANCELADA,
)


class EmissaoBloqueadaError(Exception):
    """Tentativa de emitir NFe que ja foi emitida ou que nao deve emitir."""


class EmissorNfeHora:
    """Orquestra o ciclo de vida da emissao."""

    QUEUE_NAME = 'hora_nfe'

    # ----------------------------------------------------------
    # API publica
    # ----------------------------------------------------------
    @classmethod
    def enfileirar(cls, venda_id: int) -> int:
        """Cria/reaproveita HoraTagPlusNfeEmissao e enfileira processamento.

        Retorna emissao_id. Levanta EmissaoBloqueadaError se a venda ja tem
        NF emitida ou se a emissao ativa esta em estado terminal/em_voo.
        """
        venda = HoraVenda.query.get(venda_id)
        if not venda:
            raise EmissaoBloqueadaError(f'Venda {venda_id} nao encontrada.')

        # Bloqueio defensivo: pedido importado de DANFE legado ja nasce FATURADO
        # com chave_44 — nao deve emitir NFe pelo TagPlus.
        if venda.nf_saida_chave_44:
            raise EmissaoBloqueadaError(
                f'Pedido {venda_id} ja tem NF (chave {venda.nf_saida_chave_44}). '
                f'Para re-emissao, cancelar a existente primeiro.'
            )

        if venda.status not in (VENDA_STATUS_CONFIRMADO, VENDA_STATUS_FATURADO):
            raise EmissaoBloqueadaError(
                f'Pedido {venda_id} em status {venda.status}; '
                f'so CONFIRMADO emite NFe (FATURADO ja tem NF).'
            )

        conta = HoraTagPlusConta.ativa()

        emissao = (
            HoraTagPlusNfeEmissao.query
            .filter_by(venda_id=venda_id)
            .first()
        )
        if emissao and emissao.status in _STATUS_BLOQUEIA_REENFILEIRA:
            logger.info(
                'Emissao venda=%s ja em estado %s — nao re-enfileira.',
                venda_id, emissao.status,
            )
            return emissao.id

        if not emissao:
            emissao = HoraTagPlusNfeEmissao(
                venda_id=venda_id,
                conta_id=conta.id,
                status=NFE_STATUS_PENDENTE,
            )
            db.session.add(emissao)
        else:
            # Retry de REJEITADA_LOCAL / REJEITADA_SEFAZ / ERRO_INFRA.
            # Limpa campos de NF anterior para nao confundir auditoria
            # (nova emissao gera nova chave_44/numero quando aprovada).
            emissao.status = NFE_STATUS_PENDENTE
            emissao.error_code = None
            emissao.error_message = None
            emissao.conta_id = conta.id
            emissao.tagplus_nfe_id = None
            emissao.numero_nfe = None
            emissao.serie_nfe = None
            emissao.chave_44 = None
            emissao.protocolo_aprovacao = None

        venda_audit.registrar_auditoria(
            venda_id=venda_id, usuario='sistema',
            acao='EMITIU_NFE',
            detalhe=f'Emissao enfileirada (id={emissao.id} conta={conta.id}).',
        )

        # Commit ANTES de enfileirar — evita race com worker em outro processo.
        db.session.commit()
        emissao_id = emissao.id

        cls._enqueue_processar(emissao_id)
        return emissao_id

    @classmethod
    def processar(cls, emissao_id: int) -> None:
        """Executa o POST /nfes. Idempotente para o worker do RQ.

        Recupera o registro, transiciona PENDENTE/ERRO_INFRA -> EM_ENVIO,
        envia ao TagPlus, persiste resposta e estado final.
        """
        emissao = HoraTagPlusNfeEmissao.query.get(emissao_id)
        if not emissao:
            logger.warning('processar: emissao %s nao encontrada', emissao_id)
            return

        if emissao.status not in (NFE_STATUS_PENDENTE, NFE_STATUS_ERRO_INFRA):
            logger.info(
                'processar: emissao %s em estado %s — skip',
                emissao_id, emissao.status,
            )
            return

        # Bloqueio em ambiente de homologacao (TagPlus nao tem homologacao real).
        if (emissao.conta.ambiente or 'producao') != 'producao':
            emissao.status = NFE_STATUS_REJEITADA_LOCAL
            emissao.error_code = 'ambiente_homologacao'
            emissao.error_message = (
                'Conta TagPlus marcada como ambiente=homologacao; '
                'POST /nfes bloqueado (TagPlus nao tem ambiente de homologacao).'
            )
            db.session.commit()
            return

        emissao.status = NFE_STATUS_EM_ENVIO
        emissao.enviado_em = agora_utc_naive()
        emissao.tentativas = (emissao.tentativas or 0) + 1
        db.session.commit()

        venda = emissao.venda
        conta = emissao.conta

        # 1) Build payload (validacao local). Pode levantar PayloadBuilderError.
        builder = PayloadBuilder(conta)
        try:
            payload = builder.build(venda)
        except PayloadBuilderError as exc:
            db.session.rollback()
            emissao = HoraTagPlusNfeEmissao.query.get(emissao_id)
            if emissao:
                emissao.status = NFE_STATUS_REJEITADA_LOCAL
                emissao.error_code = exc.code
                emissao.error_message = exc.message
                db.session.commit()
            return
        except Exception as exc:  # pragma: no cover defensivo
            logger.exception('Erro inesperado no PayloadBuilder venda=%s', venda.id)
            db.session.rollback()
            emissao = HoraTagPlusNfeEmissao.query.get(emissao_id)
            if emissao:
                emissao.status = NFE_STATUS_REJEITADA_LOCAL
                emissao.error_code = 'payload_builder_excecao'
                emissao.error_message = str(exc)[:500]
                db.session.commit()
            return

        emissao.payload_enviado = sanitize_for_json(payload)
        db.session.commit()

        # 2) Emissao: to_nfe (a partir do pedido, sem duplicar) quando a flag
        #    HORA_TAGPLUS_PUSH_PEDIDO esta ON e a venda tem pedido; senao POST /nfes.
        client = builder.api
        try:
            response = cls._enviar_nfe(client, builder, venda, payload)
        except PayloadBuilderError as exc:
            # Caminho to_nfe (flag ON): corpo estrito invalido ou PATCH do pedido
            # rejeitado -> erro de DADOS, nao de infra. Marca REJEITADA_LOCAL
            # (nao re-tenta) em vez de deixar a emissao presa em EM_ENVIO.
            emissao.status = NFE_STATUS_REJEITADA_LOCAL
            emissao.error_code = exc.code
            emissao.error_message = exc.message
            db.session.commit()
            return
        except (ReqConnError, Timeout) as exc:
            emissao.status = NFE_STATUS_ERRO_INFRA
            emissao.error_code = 'rede_timeout'
            emissao.error_message = f'Timeout/conexao: {exc}'[:500]
            db.session.commit()
            raise  # RQ re-tenta com backoff configurado

        # 3) Interpretar resposta.
        try:
            body = response.json()
        except ValueError:
            body = {'_raw': response.text[:1000]}

        if response.status_code in (200, 201, 202):
            emissao.status = NFE_STATUS_ENVIADA_SEFAZ
            if isinstance(body, dict):
                emissao.tagplus_nfe_id = body.get('id')
                emissao.numero_nfe = (
                    str(body.get('numero')) if body.get('numero') is not None else None
                )
                emissao.serie_nfe = (
                    str(body.get('serie')) if body.get('serie') is not None else None
                )
                # chave_44 e protocolo virao via webhook nfe_aprovada (GET /nfes/{id})
                # OU via job de polling (fallback se webhook nao chegar).
            emissao.response_inicial = sanitize_for_json(body)
            # Inicia polling agressivo (10s, backoff ate 1h). Idempotente com
            # webhook — se webhook chegar antes, polling so confirma e desiste.
            cls._enqueue_polling(emissao_id, delay=10)
        elif 400 <= response.status_code < 500:
            emissao.status = NFE_STATUS_REJEITADA_LOCAL
            emissao.error_code = (
                body.get('error_code') if isinstance(body, dict) else None
            ) or f'http_{response.status_code}'
            emissao.error_message = (
                (body.get('message') or body.get('dev_message') or body.get('error'))
                if isinstance(body, dict) else None
            ) or str(body)[:500]
            emissao.response_inicial = sanitize_for_json(body)
        else:  # 5xx ou outros
            emissao.status = NFE_STATUS_ERRO_INFRA
            emissao.error_code = f'http_{response.status_code}'
            emissao.error_message = str(body)[:500]
            emissao.response_inicial = sanitize_for_json(body)
            db.session.commit()
            raise RuntimeError(
                f'TagPlus respondeu {response.status_code}; emissao {emissao.id} marcada ERRO_INFRA.'
            )

        db.session.commit()

    # ----------------------------------------------------------
    # Caminho de emissao (POST /nfes vs to_nfe a partir do pedido)
    # ----------------------------------------------------------
    @staticmethod
    def _enviar_nfe(client, builder, venda, payload):
        """Decide o caminho de emissao da NFe e devolve a requests.Response.

        - Flag HORA_TAGPLUS_PUSH_PEDIDO ON E `venda.tagplus_pedido_id` presente:
          emite A PARTIR DO PEDIDO via GET /pedidos/to_nfe/{id} — evita o pedido
          duplicado que o POST /nfes auto-cria (Fase 2b, spec secao 4). Antes,
          PATCH /pedidos/{id} com o corpo COMPLETO (estrito) + status=B para a
          NFe sair consistente com o estado atual da venda (o pedido pode ter
          sido criado incompleto, ex.: sem faturas, quando a venda nasceu
          INCOMPLETO).
        - Senao (DEFAULT, flag OFF): POST /nfes — caminho fiscal vigente,
          inalterado (zero regressao quando a flag esta desligada).

        GATE (verificacao #1 da spec, NAO resolvida): nao foi confirmado se o
        `to_nfe` transmite a SEFAZ / aceita X-Enviar-Nota — nao testavel sem
        emitir NF fiscal real (TagPlus sem homologacao). A flag OFF mantem o
        POST /nfes ate o dono validar o comportamento e ligar a flag em PROD.
        Os headers X-Enviar-Nota / X-Calculo-Trib-Automatico sao os mesmos do
        POST /nfes (melhor aposta a confirmar no go-live).
        """
        from app.hora.services.tagplus import pedido_sync_service
        headers = {'X-Enviar-Nota': 'true', 'X-Calculo-Trib-Automatico': 'true'}
        pid = getattr(venda, 'tagplus_pedido_id', None)
        if pedido_sync_service.push_habilitado() and pid:
            corpo = builder.montar_corpo_pedido(venda, estrito=True)
            corpo['status'] = 'B'
            # ApiClient NAO faz raise_for_status: um 4xx/5xx no PATCH passaria
            # silencioso e o to_nfe emitiria a NFe a partir do pedido NAO
            # atualizado (status A, sem faturas). Validar antes de emitir.
            r_patch = client.patch(f'/pedidos/{pid}', json=corpo)
            if getattr(r_patch, 'status_code', None) not in (200, 201, 202, 204):
                raise PayloadBuilderError(
                    'patch_pedido_falhou',
                    f'PATCH /pedidos/{pid} retornou '
                    f'{getattr(r_patch, "status_code", "?")}: '
                    f'{getattr(r_patch, "text", "")[:200]} — to_nfe abortado para '
                    f'nao emitir NFe de pedido desatualizado.',
                )
            return client.get(f'/pedidos/to_nfe/{pid}', extra_headers=headers)
        return client.post('/nfes', json=payload, headers=headers)

    # ----------------------------------------------------------
    # RQ enqueue
    # ----------------------------------------------------------
    @classmethod
    def _enqueue_processar(cls, emissao_id: int) -> None:
        try:
            from rq import Queue, Retry
            from redis import Redis
        except ImportError:  # pragma: no cover
            logger.warning('RQ/Redis nao instalado — emissao %s NAO enfileirada.', emissao_id)
            return

        redis_url = os.environ.get('REDIS_URL')
        if not redis_url:
            logger.warning(
                'REDIS_URL ausente — emissao %s NAO enfileirada. '
                'Configurar antes de produzir.', emissao_id,
            )
            return

        try:
            redis_conn = Redis.from_url(redis_url)
            queue = Queue(cls.QUEUE_NAME, connection=redis_conn)
            queue.enqueue(
                'app.hora.workers.emissao_nfe_worker.processar_emissao',
                emissao_id,
                retry=Retry(max=3, interval=[10, 60, 300]),
                job_timeout=180,
                description=f'NFe HORA emissao={emissao_id}',
            )
        except Exception as exc:  # pragma: no cover
            logger.exception('Falha ao enfileirar emissao %s: %s', emissao_id, exc)

    @classmethod
    def _enqueue_polling(cls, emissao_id: int, delay: int = 10) -> None:
        """Enfileira polling de status (job auto-reagenda com backoff).

        Chamado apos envio bem-sucedido (ENVIADA_SEFAZ) e apos solicitacao de
        cancelamento (CANCELAMENTO_SOLICITADO). Reduz dependencia do webhook —
        TagPlus pode falhar em entregar o evento mas a NFe ja esta resolvida no
        portal.
        """
        try:
            from rq import Queue
            from redis import Redis
        except ImportError:  # pragma: no cover
            return
        redis_url = os.environ.get('REDIS_URL')
        if not redis_url:
            logger.warning(
                'REDIS_URL ausente — polling de emissao %s NAO enfileirado.',
                emissao_id,
            )
            return
        try:
            redis_conn = Redis.from_url(redis_url)
            queue = Queue(cls.QUEUE_NAME, connection=redis_conn)
            queue.enqueue_in(
                timedelta(seconds=delay),
                'app.hora.workers.emissao_nfe_worker.polling_emissao',
                emissao_id,
            )
        except Exception as exc:  # pragma: no cover
            logger.warning(
                'Falha ao enfileirar polling emissao=%s: %s',
                emissao_id, exc,
            )

    @classmethod
    def _enqueue_webhook(cls, conta_id: int, event_type: str, item: dict, delay: int = 0) -> None:
        try:
            from rq import Queue
            from redis import Redis
        except ImportError:  # pragma: no cover
            return
        redis_url = os.environ.get('REDIS_URL')
        if not redis_url:
            return
        redis_conn = Redis.from_url(redis_url)
        queue = Queue(cls.QUEUE_NAME, connection=redis_conn)
        if delay:
            queue.enqueue_in(
                timedelta(seconds=delay),
                'app.hora.workers.emissao_nfe_worker.processar_webhook',
                conta_id, event_type, [item],
            )
        else:
            queue.enqueue(
                'app.hora.workers.emissao_nfe_worker.processar_webhook',
                conta_id, event_type, [item],
            )


__all__ = [
    'EmissorNfeHora',
    'EmissaoBloqueadaError',
    'NFE_STATUS_PENDENTE',
    'NFE_STATUS_EM_ENVIO',
    'NFE_STATUS_ENVIADA_SEFAZ',
    'NFE_STATUS_APROVADA',
    'NFE_STATUS_REJEITADA_LOCAL',
    'NFE_STATUS_REJEITADA_SEFAZ',
    'NFE_STATUS_ERRO_INFRA',
    'NFE_STATUS_CANCELAMENTO_SOLICITADO',
    'NFE_STATUS_CANCELADA',
]
