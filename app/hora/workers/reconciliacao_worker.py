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
    NFE_STATUS_APROVADA,
    NFE_STATUS_ENVIADA_SEFAZ,
    NFE_STATUS_CANCELAMENTO_SOLICITADO,
)
from app.hora.services.tagplus.api_client import ApiClient
from app.hora.services.tagplus.webhook_handler import (
    WebhookHandler,
    EVENT_NFE_APROVADA,
    EVENT_NFE_CANCELADA,
    EVENT_NFE_DENEGADA,
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


def _tem_xml_cancelamento(detalhes: dict) -> bool:
    """Detecta cancelamento via campo `xml_cancelamento` do GET /nfes/{id}.

    TagPlus pode retornar status='A' por horas mesmo apos cancelamento solicitado
    (ex.: Emissor Online TagPlus offline durante a janela). Mas quando a SEFAZ
    aprova o cancelamento, o XML do protocolo aparece em `xml_cancelamento`.
    Isso e sinal definitivo de cancelamento, mesmo quando `status` ainda nao
    transicionou.

    Vazio considerado: None, '', '[]' (TagPlus retorna `[]` antes do protocolo).
    """
    xml = detalhes.get('xml_cancelamento') if isinstance(detalhes, dict) else None
    if not xml:
        return False
    if isinstance(xml, str):
        s = xml.strip()
        return bool(s) and s != '[]'
    if isinstance(xml, list):
        return len(xml) > 0
    return True


def _is_cancelado(status_api: str, detalhes: dict) -> bool:
    """Cancelamento detectado por status='S' OU xml_cancelamento nao vazio."""
    if status_api in _STATUS_CANCELADO:
        return True
    return _tem_xml_cancelamento(detalhes)


def _decidir_acao_reconciliacao(
    emissao: HoraTagPlusNfeEmissao,
    detalhes: dict,
) -> tuple[str | None, str]:
    """Decide qual evento simular com base no estado local + resposta TagPlus.

    Retorna (event_type, descricao_acao):
      - ('nfe_cancelada', 'CANCELADA') quando ha sinal de cancelamento.
      - ('nfe_aprovada',  'APROVADA')  quando aprovada e local nao esta em
        CANCELAMENTO_SOLICITADO.
      - ('nfe_denegada',  'REJEITADA') quando denegada/rejeitada.
      - (None, '<motivo>') quando ainda em processamento ou aguardando.

    Regra crucial (bug 2026-04-29): se o estado local e CANCELAMENTO_SOLICITADO
    OU APROVADA com cancelamento_solicitado_em preenchido, NAO regredir para
    APROVADA so porque o TagPlus retornou status='A' — significa que o
    cancelamento ainda esta na fila do Emissor Online TagPlus. Continuar
    aguardando ate vir 'S' OU xml_cancelamento ser preenchido.
    """
    status_api = (
        (detalhes.get('status') or detalhes.get('situacao') or '').strip()
    )
    aguardando_cancelamento = (
        emissao.status == NFE_STATUS_CANCELAMENTO_SOLICITADO
        or (
            emissao.status == NFE_STATUS_APROVADA
            and emissao.cancelamento_solicitado_em is not None
            and emissao.cancelado_em is None
        )
    )

    # Sinal forte de cancelamento (status='S' OU xml_cancelamento preenchido).
    if _is_cancelado(status_api, detalhes):
        return EVENT_NFE_CANCELADA, 'CANCELADA'

    # Aguardando cancelamento mas TagPlus ainda nao processou:
    # NAO simular nfe_aprovada (regrediria) — apenas reportar pendencia.
    if aguardando_cancelamento:
        return None, (
            f'Cancelamento aguardando processamento na TagPlus '
            f'(status atual="{status_api or "?"}"). Tente sincronizar de novo '
            f'em alguns minutos.'
        )

    if status_api in _STATUS_APROVADO:
        return EVENT_NFE_APROVADA, 'APROVADA'
    if status_api in _STATUS_REJEITADO:
        return EVENT_NFE_DENEGADA, 'REJEITADA'

    return None, (
        f'TagPlus reporta status "{status_api or "?"}" (em processamento).'
    )


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

    # Emissoes que regrediram para APROVADA com cancelamento_solicitado_em
    # preenchido — bug 2026-04-29 onde `_handle_aprovada` regredia o estado.
    # Apos o fix, _handle_aprovada nao regride mais, mas linhas existentes
    # precisam ser reconciliadas.
    pendentes_bagunca = (
        HoraTagPlusNfeEmissao.query
        .filter(HoraTagPlusNfeEmissao.status == NFE_STATUS_APROVADA)
        .filter(HoraTagPlusNfeEmissao.cancelamento_solicitado_em.isnot(None))
        .filter(HoraTagPlusNfeEmissao.cancelado_em.is_(None))
        .filter(HoraTagPlusNfeEmissao.tagplus_nfe_id.isnot(None))
        .limit(limit)
        .all()
    )

    pendentes = pendentes_envio + pendentes_cancelamento + pendentes_bagunca
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
                stats['reconciliadas'] += 1

                event_type, acao = _decidir_acao_reconciliacao(emissao, detalhes)
                if not event_type:
                    continue  # em-processamento, aguarda proximo ciclo

                evento_simulado = [{'id': str(emissao.tagplus_nfe_id)}]
                WebhookHandler.processar(conta_id, event_type, evento_simulado)
                if acao == 'APROVADA':
                    stats['aprovadas'] += 1
                elif acao == 'CANCELADA':
                    stats['canceladas'] += 1
                elif acao == 'REJEITADA':
                    stats['rejeitadas'] += 1

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


def reconciliar_uma_emissao(emissao_id: int) -> dict:
    """Forca reconciliacao de UMA emissao especifica (botao "Sincronizar agora").

    Sem filtro de tempo — usado quando o operador quer puxar status do TagPlus
    imediatamente (ex.: NFe foi aprovada no portal mas webhook nao chegou no
    sistema). Retorna dict com {acao_aplicada, status_api, ok, mensagem}.
    """
    emissao = HoraTagPlusNfeEmissao.query.get(emissao_id)
    if not emissao:
        return {'ok': False, 'mensagem': f'Emissao {emissao_id} nao encontrada.'}
    if not emissao.tagplus_nfe_id:
        return {
            'ok': False,
            'mensagem': (
                f'Emissao {emissao_id} sem tagplus_nfe_id — '
                f'a NFe nem foi enviada ao TagPlus ainda.'
            ),
        }
    conta = emissao.conta
    if not conta:
        return {'ok': False, 'mensagem': 'Conta TagPlus da emissao nao existe mais.'}

    client = ApiClient(conta)
    try:
        r = client.get(f'/nfes/{emissao.tagplus_nfe_id}')
    except Exception as exc:
        return {
            'ok': False,
            'mensagem': f'Falha ao consultar TagPlus: {exc}',
        }
    if r.status_code != 200:
        # 5xx do TagPlus e comum quando o Emissor Online esta reiniciando
        # (visto em 2026-04-29). Mensagem amigavel + nao tratar como erro fatal.
        if 500 <= r.status_code < 600:
            return {
                'ok': False,
                'status_http': r.status_code,
                'mensagem': (
                    f'TagPlus instavel agora (HTTP {r.status_code}). Pode ser '
                    f'reinicio do Emissor Online — tente novamente em 1-2 min.'
                ),
            }
        return {
            'ok': False,
            'status_http': r.status_code,
            'mensagem': (
                f'TagPlus retornou HTTP {r.status_code} para '
                f'/nfes/{emissao.tagplus_nfe_id}: {r.text[:200]}'
            ),
        }
    try:
        detalhes = r.json() or {}
    except ValueError:
        return {'ok': False, 'mensagem': 'TagPlus retornou body nao-JSON.'}

    status_api = (detalhes.get('status') or detalhes.get('situacao') or '').strip()
    event_type, acao = _decidir_acao_reconciliacao(emissao, detalhes)

    if event_type is None:
        # Em-processamento ou aguardando cancelamento. acao traz a mensagem.
        return {
            'ok': True, 'status_api': status_api, 'acao_aplicada': None,
            'mensagem': acao,
        }

    evento_simulado = [{'id': str(emissao.tagplus_nfe_id)}]
    WebhookHandler.processar(conta.id, event_type, evento_simulado)

    mensagens = {
        'APROVADA': 'NFe aprovada — status sincronizado.',
        'CANCELADA': 'NFe cancelada na SEFAZ — status sincronizado.',
        'REJEITADA': 'NFe rejeitada/denegada SEFAZ — status sincronizado.',
    }
    return {
        'ok': True, 'status_api': status_api, 'acao_aplicada': acao,
        'mensagem': mensagens.get(acao, f'Acao aplicada: {acao}'),
    }
