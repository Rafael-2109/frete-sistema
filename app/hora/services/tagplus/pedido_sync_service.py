"""Push de pedido HORA -> TagPlus (Fase 2a — parte SEGURA, atras de flag).

Cobre criar (POST /pedidos), atualizar status (PATCH /pedidos/{id}) e cancelar
(PATCH status=C) com base no contrato `/pedidos` confirmado em
`docs/superpowers/specs/2026-06-29-hora-tagplus-sync-bidirecional-design.md`.

GUARDA DE SEGURANCA: nenhuma chamada real acontece a menos que a flag
`HORA_TAGPLUS_PUSH_PEDIDO=1` esteja ligada E `dry_run=False`. Default = dry-run.

FORA DESTE MODULO (Fase 2b — gated nas verificacoes de API):
  - itens/cliente/faturas no payload (reusa o mapeamento de produto/cliente);
  - emissao da NFe via GET /pedidos/to_nfe/{id} (evita pedido duplicado);
  - wiring nos pontos de transicao de venda_service (criar/confirmar/cancelar);
  - escolha PATCH status=C vs DELETE p/ cancelamento (verificacao #3).
Pre-requisito de producao: OAuth reautorizado com scope `write:pedidos`
(o token atual NAO tem — push real retorna 401 ate reautorizar).
"""
from __future__ import annotations

import logging
import os

from app.hora.models.venda import (
    VENDA_STATUS_CANCELADO,
    VENDA_STATUS_CONFIRMADO,
    VENDA_STATUS_COTACAO,
    VENDA_STATUS_FATURADO,
    VENDA_STATUS_INCOMPLETO,
)

logger = logging.getLogger(__name__)

INTEGRACAO_TAG = 'SISTEMA_HORA'

# Status do pedido no TagPlus: A=Em aberto, B=Confirmado, C=Cancelado.
TP_STATUS_ABERTO = 'A'
TP_STATUS_CONFIRMADO = 'B'
TP_STATUS_CANCELADO = 'C'

_STATUS_HORA_TO_TP = {
    VENDA_STATUS_INCOMPLETO: TP_STATUS_ABERTO,
    VENDA_STATUS_COTACAO: TP_STATUS_ABERTO,
    VENDA_STATUS_CONFIRMADO: TP_STATUS_CONFIRMADO,
    # FATURADO: o pedido permanece B; a NFe e vinculada via to_nfe (Fase 2b).
    VENDA_STATUS_FATURADO: TP_STATUS_CONFIRMADO,
    VENDA_STATUS_CANCELADO: TP_STATUS_CANCELADO,
}


def mapear_status(status_hora: str) -> str:
    """HoraVenda.status -> status TagPlus (A/B/C). Default 'A' p/ desconhecido."""
    return _STATUS_HORA_TO_TP.get(status_hora, TP_STATUS_ABERTO)


def push_habilitado() -> bool:
    """Flag de seguranca. Default OFF — push real so com HORA_TAGPLUS_PUSH_PEDIDO=1."""
    return os.environ.get('HORA_TAGPLUS_PUSH_PEDIDO', '0') in ('1', 'true', 'True')


def montar_payload_pedido(venda, builder=None) -> dict:
    """HoraVenda -> corpo do POST /pedidos.

    Sempre inclui IDENTIDADE (`codigo_externo` = elo com a venda p/ anti-loop,
    `status` A/B/C, `integracao`). Quando `builder` (PayloadBuilder) e' passado,
    mescla o CORPO FISCAL completo (cliente/itens/faturas/valores) em modo
    TOLERANTE (Fase 2b) — campos que nao resolvem sao omitidos. Sem builder,
    devolve so a identidade (compat Fase 2a / pedido "corpo vazio").
    """
    payload = {
        'codigo_externo': str(venda.id),
        'status': mapear_status(venda.status),
        'integracao': INTEGRACAO_TAG,
    }
    if builder is not None:
        payload.update(builder.montar_corpo_pedido(venda, estrito=False))
    if getattr(venda, 'observacoes', None):
        payload['observacoes'] = venda.observacoes
    return payload


def criar_pedido(api, venda, *, dry_run: bool = True, builder=None) -> dict:
    """POST /pedidos. dry_run (default) ou flag OFF NAO chamam a API.

    `builder` (PayloadBuilder) opcional: quando presente, o payload leva o corpo
    fiscal completo (cliente/itens/faturas) alem da identidade (Fase 2b).

    Retorna {'dry_run', 'payload', 'tagplus_pedido_id', 'tagplus_pedido_numero',
             'status_code'}.
    """
    payload = montar_payload_pedido(venda, builder=builder)
    if dry_run or not push_habilitado():
        return {
            'dry_run': True, 'payload': payload,
            'tagplus_pedido_id': None, 'tagplus_pedido_numero': None,
            'status_code': None,
        }
    r = api.post('/pedidos', json=payload)
    body = r.json() if r.status_code in (200, 201) else {}
    if not isinstance(body, dict):
        body = {}
    pedido_id = body.get('id')
    if r.status_code in (200, 201) and not pedido_id:
        # 2xx sem id deixaria tagplus_pedido_id NULL e abriria espaco p/
        # duplicar num retry — logar para visibilidade operacional.
        logger.warning(
            'POST /pedidos retornou %s SEM id no body (venda=%s) — '
            'tagplus_pedido_id ficara NULL. Body: %s',
            r.status_code, getattr(venda, 'id', None), str(body)[:300],
        )
    return {
        'dry_run': False, 'payload': payload,
        'tagplus_pedido_id': pedido_id,
        'tagplus_pedido_numero': body.get('numero'),
        'status_code': r.status_code,
    }


def atualizar_status_pedido(api, tagplus_pedido_id: int, status_tp: str, *, dry_run: bool = True) -> dict:
    """PATCH /pedidos/{id} com novo status (A/B/C). dry_run/flag-OFF nao chamam."""
    payload = {'status': status_tp}
    if dry_run or not push_habilitado():
        return {'dry_run': True, 'pedido_id': tagplus_pedido_id, 'payload': payload, 'status_code': None}
    r = api.patch(f'/pedidos/{tagplus_pedido_id}', json=payload)
    return {'dry_run': False, 'pedido_id': tagplus_pedido_id, 'payload': payload, 'status_code': r.status_code}


def cancelar_pedido(api, tagplus_pedido_id: int, *, dry_run: bool = True) -> dict:
    """Cancela o pedido no TagPlus via PATCH status=C (preserva o registro).

    DELETE /pedidos/{id} (apagar, com X-Apagar-Financeiro) e a alternativa —
    decisao gated na verificacao #3 (comportamento com NFe emitida). Default
    e PATCH status=C por ser reversivel e preservar historico.
    """
    return atualizar_status_pedido(api, tagplus_pedido_id, TP_STATUS_CANCELADO, dry_run=dry_run)


# --------------------------------------------------------------------
# Wiring de alto nivel (chamado POS-COMMIT pelos pontos de transicao do
# venda_service). Regras invioláveis:
#   - No-op silencioso se a flag HORA_TAGPLUS_PUSH_PEDIDO estiver OFF.
#   - TOLERANTE a falha: NUNCA levanta — uma falha de rede/TagPlus jamais
#     pode travar/reverter a venda local (que ja foi commitada). O scheduler
#     reverso (Fase 3) reconcilia o que faltar.
# --------------------------------------------------------------------
# Status da venda em que faz sentido CRIAR o pedido no TagPlus (push). FATURADO
# ja tem NF (criar = pedido orfao desvinculado da NF original); CANCELADO nao
# deve nascer como pedido. So' estes 3 disparam POST /pedidos.
_STATUS_PERMITE_CRIAR = (
    VENDA_STATUS_INCOMPLETO, VENDA_STATUS_COTACAO, VENDA_STATUS_CONFIRMADO,
)


def _conta_builder():
    """(conta ativa, PayloadBuilder). Isolado p/ mock em teste."""
    from app.hora.models.tagplus import HoraTagPlusConta
    from app.hora.services.tagplus.payload_builder import PayloadBuilder
    conta = HoraTagPlusConta.ativa()
    return conta, PayloadBuilder(conta)


def push_criar_pedido(venda):
    """POST /pedidos pos-commit; grava tagplus_pedido_id + tagplus_pedido_numero.

    Idempotente: no-op se a venda ja tem `tagplus_pedido_id` (evita duplicar).
    No-op tambem se o status nao permite criar (FATURADO ja tem NF; CANCELADO).
    """
    if not push_habilitado():
        return None
    if getattr(venda, 'status', None) not in _STATUS_PERMITE_CRIAR:
        return None
    from app import db
    try:
        if getattr(venda, 'tagplus_pedido_id', None):
            return None
        _conta, builder = _conta_builder()
        res = criar_pedido(builder.api, venda, dry_run=False, builder=builder)
        if res and res.get('tagplus_pedido_id'):
            venda.tagplus_pedido_id = res['tagplus_pedido_id']
            if res.get('tagplus_pedido_numero') is not None:
                venda.tagplus_pedido_numero = res['tagplus_pedido_numero']
            db.session.commit()
        return res
    except Exception as exc:
        logger.exception(
            'push_criar_pedido venda=%s falhou (tolerante, venda local preservada): %s',
            getattr(venda, 'id', None), exc,
        )
        try:
            db.session.rollback()
        except Exception:
            pass
        return None


def push_atualizar_status(venda):
    """PATCH /pedidos/{id} status = mapear_status(venda.status). No-op sem pedido."""
    if not push_habilitado():
        return None
    try:
        pid = getattr(venda, 'tagplus_pedido_id', None)
        if not pid:
            return None
        _conta, builder = _conta_builder()
        return atualizar_status_pedido(builder.api, pid, mapear_status(venda.status), dry_run=False)
    except Exception as exc:
        logger.exception(
            'push_atualizar_status venda=%s falhou (tolerante): %s',
            getattr(venda, 'id', None), exc,
        )
        return None


def push_cancelar(venda):
    """Cancela o pedido no TagPlus (PATCH status=C). No-op sem pedido."""
    if not push_habilitado():
        return None
    try:
        pid = getattr(venda, 'tagplus_pedido_id', None)
        if not pid:
            return None
        _conta, builder = _conta_builder()
        return cancelar_pedido(builder.api, pid, dry_run=False)
    except Exception as exc:
        logger.exception(
            'push_cancelar venda=%s falhou (tolerante): %s',
            getattr(venda, 'id', None), exc,
        )
        return None
