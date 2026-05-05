"""Backfill enriquecedor de HoraVenda via GET /pedidos/{id} TagPlus.

Itera HoraTagPlusNfeEmissao APROVADA, puxa pedido_os_vinculada via
GET /nfes/{id} (1 chamada por NFe — ja cacheado mas re-extraimos pedido),
e enriquece HoraVenda com dados do GET /pedidos/{id}.

Campos enriquecidos (so se vazios — preserva edicoes manuais):
  - HoraVenda.vendedor              (NULL -> vendedor.nome)
  - HoraVenda.forma_pagamento       (NAO_INFORMADO -> faturas[0].forma_pagamento.id via mapa)
  - HoraVenda.tagplus_departamento  (raw da loja fisica para de-para posterior)
  - HoraVenda.tagplus_pedido_id     (sempre, redundancia para queries)
  - HoraVenda.tagplus_pedido_payload (sempre — auditoria + reprocessamento)
  - HoraTagPlusNfeEmissao.tagplus_pedido_id (espelho)

NAO mexe em HoraVenda.loja_id — fica para job/UI de-para posterior usando
hora_tagplus_departamento_map.

Idempotente: rodar 2x nao causa dano (campos ja preenchidos sao pulados;
tagplus_pedido_payload e sobrescrito com payload mais recente).
"""
from __future__ import annotations

import logging
import os
from typing import Callable, Optional

from app import db
from app.hora.models import (
    HoraTagPlusBackfillJob,
    HoraTagPlusFormaPagamentoMap,
    HoraTagPlusNfeEmissao,
)
from app.hora.services import venda_audit
from app.hora.services.tagplus import pedido_service
from app.hora.services.tagplus.api_client import ApiClient
from app.hora.services.tagplus.pedido_service import (
    PedidoTagPlusError,
    ScopeInsuficienteError,
)
from app.utils.json_helpers import sanitize_for_json

logger = logging.getLogger(__name__)


def _resolver_forma_pagamento_via_id(forma_id: Optional[int]) -> Optional[str]:
    """ID inteiro TagPlus -> forma_pagamento_hora via mapa cadastrado.

    Reusa HoraTagPlusFormaPagamentoMap (de-para usado para emissao de NFe).
    Retorna None se ID e None ou nao mapeado (caller mantem NAO_INFORMADO).
    """
    if not isinstance(forma_id, int):
        return None
    mapa = HoraTagPlusFormaPagamentoMap.query.filter_by(
        tagplus_forma_id=forma_id
    ).first()
    return mapa.forma_pagamento_hora if mapa else None


def _upsert_departamento_map(
    departamento_raw: str, departamento_norm: str,
) -> None:
    """Cria/atualiza HoraTagPlusDepartamentoMap, incrementando contador.

    Idempotente. Se ja existir, soma 1 em qtd_vendas_observadas e atualiza
    departamento_raw para a forma mais recente (TagPlus pode ter variacoes
    de digitacao/maiuscula).

    Commita em sessao separada (nested transaction via SAVEPOINT) para
    nao ser perdido se o caller fizer rollback por falha na auditoria
    da venda. Sem isso, vendas com falha em registrar_auditoria perderiam
    tambem o mapa do departamento, e o operador ficaria com lista
    incompleta na tela /hora/tagplus/departamento-map.
    """
    from app.hora.models import HoraTagPlusDepartamentoMap

    try:
        with db.session.begin_nested():
            mapa = HoraTagPlusDepartamentoMap.query.filter_by(
                departamento_norm=departamento_norm
            ).first()
            if mapa is None:
                mapa = HoraTagPlusDepartamentoMap(
                    departamento_norm=departamento_norm,
                    departamento_raw=departamento_raw,
                    qtd_vendas_observadas=1,
                )
                db.session.add(mapa)
            else:
                mapa.qtd_vendas_observadas = (mapa.qtd_vendas_observadas or 0) + 1
                if mapa.departamento_raw != departamento_raw:
                    mapa.departamento_raw = departamento_raw
    except Exception:
        # Rollback do SAVEPOINT — nao propaga (best-effort).
        # Worker single-thread por queue garante que nao ha race; UNIQUE
        # violation seria bug em outro lugar.
        logger.exception(
            'Falha ao upsert departamento_map norm=%r', departamento_norm,
        )


def _enriquecer_uma_venda(
    api: ApiClient,
    emissao: HoraTagPlusNfeEmissao,
    operador: Optional[str],
) -> dict:
    """Enriquece uma HoraVenda. Retorna dict com status e campos alterados.

    Status possiveis:
      - 'enriquecida'    : pelo menos 1 campo foi preenchido.
      - 'inalterada'     : todos os campos ja estavam preenchidos.
      - 'sem_pedido'     : NFe sem pedido_os_vinculada (raro).
      - 'erro_pedido'    : falha ao chamar GET /pedidos/{id}.
      - 'sem_venda'      : emissao sem venda associada (incoerencia).
    """
    venda = emissao.venda
    if venda is None:
        return {'status': 'sem_venda', 'emissao_id': emissao.id}

    # Passo 1: GET /nfes/{id} para extrair pedido_os_vinculada.
    if not emissao.tagplus_nfe_id:
        return {
            'status': 'sem_pedido', 'emissao_id': emissao.id,
            'mensagem': 'emissao sem tagplus_nfe_id',
        }

    nfe_resp = api.get(f'/nfes/{emissao.tagplus_nfe_id}')
    if nfe_resp.status_code != 200:
        return {
            'status': 'erro_pedido', 'emissao_id': emissao.id,
            'mensagem': f'GET /nfes/{emissao.tagplus_nfe_id} -> {nfe_resp.status_code}',
        }
    try:
        nfe = nfe_resp.json()
    except ValueError:
        return {
            'status': 'erro_pedido', 'emissao_id': emissao.id,
            'mensagem': 'NFe response nao-JSON',
        }

    pedido_vincul = nfe.get('pedido_os_vinculada') or {}
    pedido_id_tp = pedido_vincul.get('id') if isinstance(pedido_vincul, dict) else None
    if not isinstance(pedido_id_tp, int):
        return {
            'status': 'sem_pedido', 'emissao_id': emissao.id,
            'mensagem': 'NFe sem pedido_os_vinculada.id',
        }

    # Passo 2: GET /pedidos/{id}.
    try:
        pedido = pedido_service.importar_pedido(api, pedido_id_tp)
    except ScopeInsuficienteError:
        # Propaga — caller para o backfill todo (sem scope, nada funciona).
        raise
    except PedidoTagPlusError as exc:
        return {
            'status': 'erro_pedido', 'emissao_id': emissao.id,
            'pedido_tagplus_id': pedido_id_tp,
            'mensagem': str(exc)[:300],
        }

    # Passo 3: Extrai dados.
    vendedor_nome = pedido_service.extrair_vendedor_nome(pedido)
    departamento_raw = pedido_service.extrair_departamento_descricao(pedido)
    departamento_norm = pedido_service.normalizar_departamento(departamento_raw)
    forma_id = pedido_service.extrair_forma_pagamento_id(pedido)
    forma_pgto = _resolver_forma_pagamento_via_id(forma_id)

    # Passo 4: Aplica em HoraVenda (so campos vazios para vendedor/forma;
    # tagplus_* sempre).
    alteracoes = []

    # Sempre persiste tagplus_pedido_id + payload (auditoria/reprocesso).
    if venda.tagplus_pedido_id != pedido_id_tp:
        venda.tagplus_pedido_id = pedido_id_tp
        alteracoes.append(f'tagplus_pedido_id={pedido_id_tp}')
    venda.tagplus_pedido_payload = sanitize_for_json(pedido)
    # Espelha em emissao tambem (consulta direta sem JOIN).
    if emissao.tagplus_pedido_id != pedido_id_tp:
        emissao.tagplus_pedido_id = pedido_id_tp

    # Vendedor: so se NULL.
    if vendedor_nome and not (venda.vendedor or '').strip():
        venda.vendedor = vendedor_nome
        alteracoes.append(f'vendedor={vendedor_nome!r}')

    # Forma de pagamento: so se NAO_INFORMADO/NULL.
    if forma_pgto and venda.forma_pagamento in (None, '', 'NAO_INFORMADO'):
        venda.forma_pagamento = forma_pgto
        alteracoes.append(f'forma_pagamento={forma_pgto}')

    # Departamento raw: sempre atualiza (retrato mais recente). Tambem
    # alimenta o de-para hora_tagplus_departamento_map.
    if departamento_raw:
        if venda.tagplus_departamento != departamento_raw:
            venda.tagplus_departamento = departamento_raw
            alteracoes.append(f'departamento={departamento_raw!r}')
        if departamento_norm:
            _upsert_departamento_map(departamento_raw, departamento_norm)

    if not alteracoes:
        return {
            'status': 'inalterada', 'emissao_id': emissao.id,
            'venda_id': venda.id, 'pedido_tagplus_id': pedido_id_tp,
        }

    # Auditoria (apenas se houve mudanca real).
    venda_audit.registrar_auditoria(
        venda_id=venda.id, usuario=operador or '',
        acao='EDITOU_HEADER',
        detalhe=(
            f'Backfill TagPlus pedido #{pedido_id_tp} — '
            + ', '.join(alteracoes)
        ),
    )
    db.session.commit()
    return {
        'status': 'enriquecida', 'emissao_id': emissao.id,
        'venda_id': venda.id, 'pedido_tagplus_id': pedido_id_tp,
        'alteracoes': alteracoes,
    }


def executar_backfill_pedidos(
    operador: Optional[str] = None,
    limite: Optional[int] = None,
    progress_callback: Optional[Callable[[dict], None]] = None,
) -> dict:
    """Itera todas as emissoes APROVADA com tagplus_nfe_id e enriquece.

    Args:
        operador: nome para auditoria.
        limite: max emissoes processadas (None = todas).
        progress_callback: chamado apos cada emissao com snapshot incremental.

    Returns:
        dict com contadores e lista enxuta de erros (cap 500).
    """
    from app.hora.models import HoraTagPlusConta, NFE_STATUS_APROVADA

    contadores = {
        'processadas': 0,
        'enriquecidas': 0,
        'inalteradas': 0,
        'sem_pedido': 0,
        'erro_pedido': 0,
        'sem_venda': 0,
    }
    erros: list[dict] = []

    conta = HoraTagPlusConta.query.filter_by(ativo=True).first()
    if conta is None:
        raise RuntimeError(
            'Nenhuma HoraTagPlusConta ativa — configurar em /hora/tagplus/conta.'
        )
    api = ApiClient(conta)

    # Universo: APROVADA com tagplus_nfe_id, ordenado por data (recentes primeiro
    # — operador costuma se preocupar com vendas novas mais).
    q = (
        HoraTagPlusNfeEmissao.query
        .filter(HoraTagPlusNfeEmissao.status == NFE_STATUS_APROVADA)
        .filter(HoraTagPlusNfeEmissao.tagplus_nfe_id.isnot(None))
        .order_by(HoraTagPlusNfeEmissao.aprovado_em.desc().nullslast())
    )
    if limite:
        q = q.limit(limite)

    for emissao in q:
        try:
            res = _enriquecer_uma_venda(api, emissao, operador)
        except ScopeInsuficienteError as exc:
            # Sem scope, todas as proximas falham igual — para tudo.
            logger.error('Backfill pedidos abortado: scope insuficiente: %s', exc)
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                'Falha enriquecendo emissao %s', emissao.id,
            )
            try:
                db.session.rollback()
            except Exception:
                pass
            res = {
                'status': 'erro_pedido', 'emissao_id': emissao.id,
                'mensagem': f'{type(exc).__name__}: {exc}'[:300],
            }

        contadores['processadas'] += 1
        status_res = res['status']
        if status_res == 'enriquecida':
            contadores['enriquecidas'] += 1
        elif status_res == 'inalterada':
            contadores['inalteradas'] += 1
        elif status_res == 'sem_pedido':
            contadores['sem_pedido'] += 1
        elif status_res == 'erro_pedido':
            contadores['erro_pedido'] += 1
            if len(erros) < 500:
                erros.append({
                    'emissao_id': res['emissao_id'],
                    'mensagem': res.get('mensagem', ''),
                })
        elif status_res == 'sem_venda':
            contadores['sem_venda'] += 1

        if progress_callback:
            progress_callback({**contadores, 'erros': erros})

    return {**contadores, 'erros': erros}


# --------------------------------------------------------------------------
# Background: enfileiramento de jobs RQ
# --------------------------------------------------------------------------

QUEUE_BACKFILL = 'hora_backfill'


def enfileirar_backfill_pedidos_job(
    operador: Optional[str],
    limite: Optional[int] = None,
) -> int:
    """Cria HoraTagPlusBackfillJob (tipo=PEDIDO_ENRIQUECIMENTO) + enfileira RQ.

    Retorna job_id local. Levanta RuntimeError se REDIS_URL ausente.
    """
    from app.hora.models import (
        BACKFILL_JOB_STATUS_PENDENTE,
        BACKFILL_JOB_TIPO_PEDIDO_ENRIQ,
    )

    job = HoraTagPlusBackfillJob(
        tipo=BACKFILL_JOB_TIPO_PEDIDO_ENRIQ,
        status=BACKFILL_JOB_STATUS_PENDENTE,
        limite=limite,
        operador=operador,
    )
    db.session.add(job)
    db.session.commit()

    try:
        from rq import Queue, Retry
        from redis import Redis
    except ImportError:
        raise RuntimeError(
            'RQ/Redis nao instalado — backfill background indisponivel.'
        )

    redis_url = os.environ.get('REDIS_URL')
    if not redis_url:
        from app.hora.models import BACKFILL_JOB_STATUS_ERRO
        job.status = BACKFILL_JOB_STATUS_ERRO
        job.ultimo_erro = 'REDIS_URL ausente — job nao pode ser enfileirado.'
        db.session.commit()
        raise RuntimeError(job.ultimo_erro)

    redis_conn = Redis.from_url(redis_url)
    queue = Queue(QUEUE_BACKFILL, connection=redis_conn)
    rq_job = queue.enqueue(
        'app.hora.workers.pedido_backfill_worker.processar_backfill_pedidos_job',
        job.id,
        job_timeout=7200,
        result_ttl=86400,
        failure_ttl=86400,
        retry=Retry(max=1, interval=[120]),
        description=f'HORA backfill pedidos TagPlus job_id={job.id}',
    )
    job.rq_job_id = rq_job.id
    db.session.commit()
    return job.id
