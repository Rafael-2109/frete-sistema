"""Backfill enriquecedor de HoraVenda via GET /pedidos/{id} TagPlus.

Tem dois universos:

1) **Universo "emissoes"** (`executar_backfill_pedidos`):
   itera HoraTagPlusNfeEmissao APROVADA com tagplus_nfe_id ja conhecido —
   path rapido, vendas emitidas pelo proprio sistema HORA via TagPlus.

2) **Universo "vendas legadas"** (`executar_backfill_pedidos_vendas_legadas`):
   itera HoraVenda FATURADO sem tagplus_pedido_id, incluindo vendas
   importadas via DANFE PDF antes da integracao TagPlus existir
   (origem='DANFE') ou criadas manualmente sem entrada em
   HoraTagPlusNfeEmissao. Para cada uma, descobre `tagplus_nfe_id` via
   GET /nfes em janela de datas (since=data_venda-7d, until=data_venda+7d)
   batendo por chave_acesso. Depois segue mesmo fluxo do path 1.

Campos enriquecidos (so se vazios — preserva edicoes manuais):
  - HoraVenda.vendedor              (NULL -> vendedor.nome)
  - HoraVenda.forma_pagamento       (NAO_INFORMADO -> faturas[0].forma_pagamento.id via mapa)
  - HoraVenda.tagplus_departamento  (raw da loja fisica para de-para posterior)
  - HoraVenda.tagplus_pedido_id     (sempre, redundancia para queries)
  - HoraVenda.tagplus_pedido_payload (sempre — auditoria + reprocessamento)
  - HoraTagPlusNfeEmissao.tagplus_pedido_id (espelho — apenas universo 1)

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


def _aplicar_pedido_em_venda(
    api: ApiClient,
    venda,  # HoraVenda
    pedido_id_tp: int,
    operador: Optional[str],
    emissao: Optional[HoraTagPlusNfeEmissao] = None,
) -> dict:
    """Faz GET /pedidos/{id} e aplica os campos em HoraVenda + (opcional) emissao.

    Reusa toda a logica de enriquecimento — usado pelos 2 universos
    (emissoes ja conhecidas e vendas legadas descobertas via API search).

    Returns dict com `status`, `venda_id`, `pedido_tagplus_id`,
    `alteracoes` (lista de str) ou `mensagem` (em caso de erro).

    Status possiveis:
      - 'enriquecida'  : pelo menos 1 campo foi preenchido.
      - 'inalterada'   : todos os campos ja estavam preenchidos.
      - 'erro_pedido'  : falha ao chamar GET /pedidos/{id}.
    """
    try:
        pedido = pedido_service.importar_pedido(api, pedido_id_tp)
    except ScopeInsuficienteError:
        # Propaga — caller para o backfill todo (sem scope, nada funciona).
        raise
    except PedidoTagPlusError as exc:
        return {
            'status': 'erro_pedido', 'venda_id': venda.id,
            'pedido_tagplus_id': pedido_id_tp,
            'mensagem': str(exc)[:300],
        }

    # Extrai dados.
    vendedor_nome = pedido_service.extrair_vendedor_nome(pedido)
    departamento_raw = pedido_service.extrair_departamento_descricao(pedido)
    departamento_norm = pedido_service.normalizar_departamento(departamento_raw)
    forma_id = pedido_service.extrair_forma_pagamento_id(pedido)
    forma_pgto = _resolver_forma_pagamento_via_id(forma_id)

    # Aplica em HoraVenda (so campos vazios para vendedor/forma; tagplus_* sempre).
    alteracoes = []

    if venda.tagplus_pedido_id != pedido_id_tp:
        venda.tagplus_pedido_id = pedido_id_tp
        alteracoes.append(f'tagplus_pedido_id={pedido_id_tp}')
    venda.tagplus_pedido_payload = sanitize_for_json(pedido)

    if emissao is not None and emissao.tagplus_pedido_id != pedido_id_tp:
        emissao.tagplus_pedido_id = pedido_id_tp

    if vendedor_nome and not (venda.vendedor or '').strip():
        venda.vendedor = vendedor_nome
        alteracoes.append(f'vendedor={vendedor_nome!r}')

    if forma_pgto and venda.forma_pagamento in (None, '', 'NAO_INFORMADO'):
        venda.forma_pagamento = forma_pgto
        alteracoes.append(f'forma_pagamento={forma_pgto}')

    if departamento_raw:
        if venda.tagplus_departamento != departamento_raw:
            venda.tagplus_departamento = departamento_raw
            alteracoes.append(f'departamento={departamento_raw!r}')
        if departamento_norm:
            _upsert_departamento_map(departamento_raw, departamento_norm)

    if not alteracoes:
        return {
            'status': 'inalterada', 'venda_id': venda.id,
            'pedido_tagplus_id': pedido_id_tp,
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
        'status': 'enriquecida', 'venda_id': venda.id,
        'pedido_tagplus_id': pedido_id_tp, 'alteracoes': alteracoes,
    }


def _extrair_pedido_id_da_nfe(api: ApiClient, tagplus_nfe_id: int) -> tuple:
    """GET /nfes/{id} -> (pedido_id_tp, status_diag, mensagem_erro).

    Retorna (None, 'erro_pedido', mensagem) em falha HTTP/JSON.
    Retorna (None, 'sem_pedido', mensagem) em NFe sem pedido_os_vinculada.
    Retorna (int, None, None) em sucesso.
    """
    nfe_resp = api.get(f'/nfes/{tagplus_nfe_id}')
    if nfe_resp.status_code != 200:
        return None, 'erro_pedido', f'GET /nfes/{tagplus_nfe_id} -> {nfe_resp.status_code}'
    try:
        nfe = nfe_resp.json()
    except ValueError:
        return None, 'erro_pedido', 'NFe response nao-JSON'
    pedido_vincul = nfe.get('pedido_os_vinculada') or {}
    pedido_id_tp = pedido_vincul.get('id') if isinstance(pedido_vincul, dict) else None
    if not isinstance(pedido_id_tp, int):
        return None, 'sem_pedido', 'NFe sem pedido_os_vinculada.id'
    return pedido_id_tp, None, None


def _enriquecer_uma_venda(
    api: ApiClient,
    emissao: HoraTagPlusNfeEmissao,
    operador: Optional[str],
) -> dict:
    """Enriquece uma HoraVenda via emissao ja conhecida. Retorna dict com status.

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

    if not emissao.tagplus_nfe_id:
        return {
            'status': 'sem_pedido', 'emissao_id': emissao.id,
            'mensagem': 'emissao sem tagplus_nfe_id',
        }

    pedido_id_tp, status_err, msg_err = _extrair_pedido_id_da_nfe(
        api, emissao.tagplus_nfe_id,
    )
    if pedido_id_tp is None:
        return {
            'status': status_err, 'emissao_id': emissao.id,
            'mensagem': msg_err,
        }

    res = _aplicar_pedido_em_venda(api, venda, pedido_id_tp, operador, emissao)
    res['emissao_id'] = emissao.id
    return res


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


# ============================================================================
# UNIVERSO 2: Backfill de vendas legadas (sem HoraTagPlusNfeEmissao)
# ============================================================================

# Janela de busca de NFe via /nfes ao redor de data_venda. Vendas DANFE
# legadas tem data_venda confiavel (vinda do parser CarVia), mas a
# data_emissao no TagPlus pode divergir em alguns dias quando o operador
# emitiu a NFe horas/dias depois da venda fisica.
JANELA_BUSCA_NFE_DIAS = 7


def _buscar_tagplus_nfe_id_para_venda(
    api: ApiClient, venda,
) -> tuple:
    """Localiza tagplus_nfe_id da NFe correspondente a uma venda legada.

    Estrategia (mais barata para mais cara):
      1) Se venda ja tem `HoraTagPlusNfeEmissao` com `tagplus_nfe_id`,
         usa direto. (Caso de borda — pedido_backfill ja teria coberto,
         mas nao custa nada validar.)
      2) Se venda tem `nf_saida_chave_44` ou `nf_saida_numero`, pagina
         /nfes em janela de [data_venda - JANELA, data_venda + JANELA]
         filtrando por X-Data-Filter: data_emissao. Bate primeiro pela
         chave_44 (44 chars exatos), fallback pelo numero.

    Returns:
        (tagplus_nfe_id, mensagem_diag) — int ou None + string com motivo.
    """
    from datetime import date as _date, timedelta

    # Path A: emissao ja tem o id.
    emissao = (
        HoraTagPlusNfeEmissao.query
        .filter(HoraTagPlusNfeEmissao.venda_id == venda.id)
        .filter(HoraTagPlusNfeEmissao.tagplus_nfe_id.isnot(None))
        .first()
    )
    if emissao and emissao.tagplus_nfe_id:
        return emissao.tagplus_nfe_id, 'via_emissao_existente'

    # Path B: precisa achar via API.
    chave_44 = (venda.nf_saida_chave_44 or '').strip() or None
    numero_nf = (venda.nf_saida_numero or '').strip() or None
    if not chave_44 and not numero_nf:
        return None, 'venda sem nf_saida_chave_44 nem nf_saida_numero'

    if not venda.data_venda:
        return None, 'venda sem data_venda — janela de busca indeterminada'

    base = venda.data_venda
    if isinstance(base, _date):
        since = base - timedelta(days=JANELA_BUSCA_NFE_DIAS)
        until = base + timedelta(days=JANELA_BUSCA_NFE_DIAS)
    else:
        return None, f'data_venda em formato inesperado: {type(base).__name__}'

    # Pagina /nfes na janela. Itera ate achar match ou esgotar paginas.
    # A funcao listar_nfes_emitidas (em backfill_service) faz a mesma
    # paginacao, mas nao quero criar dependencia circular — replico
    # logica simples aqui.
    page = 1
    per_page = 50
    candidatas: list[dict] = []
    while True:
        params = {'page': page, 'per_page': per_page}
        params['since'] = since.isoformat()
        params['until'] = until.isoformat()
        r = api.get(
            '/nfes',
            params=params,
            extra_headers={'X-Data-Filter': 'data_emissao'},
        )
        if r.status_code != 200:
            return None, (
                f'GET /nfes (page={page} since={since} until={until}) '
                f'retornou {r.status_code}: {r.text[:200]}'
            )
        try:
            lote = r.json()
        except ValueError:
            lote = []
        if not isinstance(lote, list) or not lote:
            break
        candidatas.extend(lote)
        if len(lote) < per_page:
            break
        page += 1
        # Defesa contra paginacao infinita (janela de 14 dias deveria
        # caber em <20 paginas — limite razoavel).
        if page > 40:
            break

    # Match exato pela chave (preferido).
    if chave_44:
        for nfe in candidatas:
            if not isinstance(nfe, dict):
                continue
            chave_api = (nfe.get('chave_acesso') or '').strip()
            if chave_api == chave_44:
                tp_id = nfe.get('id')
                if isinstance(tp_id, int):
                    return tp_id, f'chave_44 match em /nfes (since={since} until={until})'

    # Fallback pelo numero. Pode ter ambiguidade se 2 NFs com mesmo
    # numero existirem em series diferentes — preferimos a que tem chave
    # batendo com prefixos esperaveis. Em ambiguidade, retorna a primeira.
    if numero_nf:
        for nfe in candidatas:
            if not isinstance(nfe, dict):
                continue
            num_api = str(nfe.get('numero') or '').strip()
            if num_api == numero_nf:
                tp_id = nfe.get('id')
                if isinstance(tp_id, int):
                    return tp_id, (
                        f'numero match em /nfes (chave_44 nao bateu — '
                        f'fallback por numero)'
                    )

    return None, (
        f'NFe nao encontrada em /nfes na janela [{since}, {until}] '
        f'(testou chave={bool(chave_44)} numero={numero_nf!r}; '
        f'{len(candidatas)} NFs varridas)'
    )


def _enriquecer_venda_legada(
    api: ApiClient, venda, operador: Optional[str],
) -> dict:
    """Backfill de tagplus_pedido_id para uma HoraVenda legada.

    Status possiveis no retorno:
      - 'enriquecida' / 'inalterada' (mesmo significado de _aplicar_pedido_em_venda)
      - 'sem_nfe'    : nao foi possivel achar a NFe no TagPlus
      - 'sem_pedido' : NFe existe mas sem pedido_os_vinculada
      - 'erro_pedido': erro HTTP/JSON
    """
    tagplus_nfe_id, msg_busca = _buscar_tagplus_nfe_id_para_venda(api, venda)
    if tagplus_nfe_id is None:
        return {
            'status': 'sem_nfe', 'venda_id': venda.id,
            'mensagem': msg_busca,
        }

    pedido_id_tp, status_err, msg_err = _extrair_pedido_id_da_nfe(
        api, tagplus_nfe_id,
    )
    if pedido_id_tp is None:
        return {
            'status': status_err, 'venda_id': venda.id,
            'tagplus_nfe_id': tagplus_nfe_id,
            'mensagem': msg_err,
        }

    res = _aplicar_pedido_em_venda(api, venda, pedido_id_tp, operador, emissao=None)
    res['tagplus_nfe_id'] = tagplus_nfe_id
    return res


def _query_vendas_sem_pedido_id():
    """Universo do backfill legado: HoraVenda FATURADO sem tagplus_pedido_id."""
    from app.hora.models import HoraVenda
    from app.hora.models.venda import VENDA_STATUS_FATURADO

    return (
        HoraVenda.query
        .filter(HoraVenda.status == VENDA_STATUS_FATURADO)
        .filter(HoraVenda.tagplus_pedido_id.is_(None))
        .filter(HoraVenda.nf_saida_chave_44.isnot(None))  # precisa de algo p/ buscar
        .order_by(HoraVenda.data_venda.desc().nullslast(), HoraVenda.id.desc())
    )


def contar_universo_vendas_legadas() -> int:
    """Tamanho do universo do backfill de vendas legadas (read-only)."""
    return _query_vendas_sem_pedido_id().count()


def executar_backfill_pedidos_vendas_legadas(
    operador: Optional[str] = None,
    limite: Optional[int] = None,
    progress_callback: Optional[Callable[[dict], None]] = None,
) -> dict:
    """Backfill de tagplus_pedido_id para vendas FATURADO sem pedido vinculado.

    Coberturas (em ordem de tentativa):
      - Vendas que tem HoraTagPlusNfeEmissao com tagplus_nfe_id (path rapido).
      - Vendas DANFE legadas / origem MANUAL sem emissao — busca via
        GET /nfes com janela de datas + match por chave_acesso (fallback numero).

    Args:
        operador: nome para auditoria.
        limite: max vendas processadas (None = todas).
        progress_callback: chamado apos cada venda com snapshot incremental.

    Returns:
        dict com contadores:
          - processadas, enriquecidas, inalteradas, sem_pedido,
            sem_nfe, erro_pedido
          - erros: lista enxuta (cap 500) p/ tela de detalhe
    """
    from app.hora.models import HoraTagPlusConta

    contadores = {
        'processadas': 0,
        'enriquecidas': 0,
        'inalteradas': 0,
        'sem_pedido': 0,
        'sem_nfe': 0,
        'erro_pedido': 0,
    }
    erros: list[dict] = []

    conta = HoraTagPlusConta.query.filter_by(ativo=True).first()
    if conta is None:
        raise RuntimeError(
            'Nenhuma HoraTagPlusConta ativa — configurar em /hora/tagplus/conta.'
        )
    api = ApiClient(conta)

    q = _query_vendas_sem_pedido_id()
    if limite:
        q = q.limit(limite)

    for venda in q:
        try:
            res = _enriquecer_venda_legada(api, venda, operador)
        except ScopeInsuficienteError as exc:
            logger.error(
                'Backfill vendas legadas abortado: scope insuficiente: %s', exc,
            )
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                'Falha enriquecendo venda %s', venda.id,
            )
            try:
                db.session.rollback()
            except Exception:
                pass
            res = {
                'status': 'erro_pedido', 'venda_id': venda.id,
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
        elif status_res == 'sem_nfe':
            contadores['sem_nfe'] += 1
            if len(erros) < 500:
                erros.append({
                    'venda_id': res['venda_id'],
                    'mensagem': res.get('mensagem', ''),
                })
        elif status_res == 'erro_pedido':
            contadores['erro_pedido'] += 1
            if len(erros) < 500:
                erros.append({
                    'venda_id': res['venda_id'],
                    'mensagem': res.get('mensagem', ''),
                })

        if progress_callback:
            progress_callback({**contadores, 'erros': erros})

    return {**contadores, 'erros': erros}


def enfileirar_backfill_pedidos_vendas_legadas_job(
    operador: Optional[str],
    limite: Optional[int] = None,
) -> int:
    """Cria HoraTagPlusBackfillJob (tipo=PEDIDO_VENDAS_LEGADAS) + enfileira RQ.

    Espelho de `enfileirar_backfill_pedidos_job` mas com discriminador de
    tipo distinto e worker dedicado (`processar_backfill_pedidos_vendas_legadas_job`)
    para que tela de detalhe + UI saibam qual universo esta rodando.

    Retorna job_id local. Levanta RuntimeError se REDIS_URL ausente.
    """
    from app.hora.models import (
        BACKFILL_JOB_STATUS_PENDENTE,
        BACKFILL_JOB_TIPO_PEDIDO_VENDAS_LEGADAS,
    )

    job = HoraTagPlusBackfillJob(
        tipo=BACKFILL_JOB_TIPO_PEDIDO_VENDAS_LEGADAS,
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
        'app.hora.workers.pedido_backfill_worker.processar_backfill_pedidos_vendas_legadas_job',
        job.id,
        job_timeout=7200,
        result_ttl=86400,
        failure_ttl=86400,
        retry=Retry(max=1, interval=[120]),
        description=f'HORA backfill pedidos vendas legadas job_id={job.id}',
    )
    job.rq_job_id = rq_job.id
    db.session.commit()
    return job.id
