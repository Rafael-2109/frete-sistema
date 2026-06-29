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


def montar_payload_pedido(venda) -> dict:
    """HoraVenda -> corpo do POST /pedidos (campos de IDENTIDADE + status).

    NAO inclui itens/cliente/faturas — isso entra na Fase 2b (wiring + to_nfe),
    reusando o mapeamento de produto/cliente do PayloadBuilder. O contrato
    TagPlus aceita pedido sem produtos ("corpo vazio"). `codigo_externo` e o
    elo com a venda (anti-loop na replicacao reversa).
    """
    payload = {
        'codigo_externo': str(venda.id),
        'status': mapear_status(venda.status),
        'integracao': INTEGRACAO_TAG,
    }
    if getattr(venda, 'observacoes', None):
        payload['observacoes'] = venda.observacoes
    return payload


def criar_pedido(api, venda, *, dry_run: bool = True) -> dict:
    """POST /pedidos. dry_run (default) ou flag OFF NAO chamam a API.

    Retorna {'dry_run', 'payload', 'tagplus_pedido_id', 'tagplus_pedido_numero',
             'status_code'}.
    """
    payload = montar_payload_pedido(venda)
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
    return {
        'dry_run': False, 'payload': payload,
        'tagplus_pedido_id': body.get('id'),
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
