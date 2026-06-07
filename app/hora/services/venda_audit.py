"""Auditoria append-only de pedidos de venda HORA.

Padrao identico a recebimento_audit / transferencia_audit: nunca UPDATE/DELETE,
registra em hora_venda_auditoria.

Acoes registradas:
  CRIOU                  pedido criado (manual ou DANFE legado).
  EDITOU_HEADER          campo do header alterado (vendedor, contato, endereco,
                         observacoes, forma_pagamento).
  EDITOU_ITEM            campo do item alterado (chassi, preco, desconto).
  ADICIONOU_ITEM         item adicionado ao pedido (so em COTACAO).
  REMOVEU_ITEM           item removido do pedido (so em COTACAO).
  CONFIRMOU              transicao COTACAO -> CONFIRMADO.
  EMITIU_NFE             enfileirou emissao TagPlus.
  FATURADO               webhook nfe_aprovada -> CONFIRMADO -> FATURADO.
  CANCELOU_NFE           solicitou cancelamento NFe (PATCH /nfes/cancelar).
  NFE_CANCELADA_SEFAZ    webhook nfe_cancelada confirmou cancelamento na SEFAZ.
  EMITIU_CCE             carta de correcao emitida.
  CANCELOU               transicao * -> CANCELADO.
  DESCARTOU_TESTE        descarte de NF de teste pos janela 24h SEFAZ
                         (nao cancela na SEFAZ; status -> CANCELADO).
  RESOLVEU_DIVERGENCIA   divergencia marcada como resolvida.
  DEFINIU_LOJA           CNPJ_DESCONHECIDO resolvido manualmente.
  ENVIOU_NF_EMAIL        NF (DANFE PDF) enviada por e-mail ao cliente (roadmap #4).
  ADICIONOU_ITEM_PECA    peca adicionada ao pedido (so em COTACAO).
  REMOVEU_ITEM_PECA      peca removida do pedido (so em COTACAO).
  ADICIONOU_BRINDE       brinde (peca) adicionado ao pedido (roadmap #36).
  REMOVEU_BRINDE         brinde removido do pedido (roadmap #36).
"""
from __future__ import annotations

from typing import Optional

from app import db
from app.hora.models import HoraVendaAuditoria


ACOES_VALIDAS = {
    'CRIOU',
    'EDITOU_HEADER',
    'EDITOU_ITEM',
    'ADICIONOU_ITEM',
    'REMOVEU_ITEM',
    'CONFIRMOU',
    'EMITIU_NFE',
    'FATURADO',
    'CANCELOU_NFE',
    'NFE_CANCELADA_SEFAZ',
    'EMITIU_CCE',
    'CANCELOU',
    'DESCARTOU_TESTE',
    'RESOLVEU_DIVERGENCIA',
    'DEFINIU_LOJA',
    # Adicionado 2026-05-07: trigger 'Voltar para COTACAO' em
    # venda_detalhe.html chama venda_service.voltar_para_cotacao, que
    # registra esta acao de auditoria. Sem esta entrada, o set rejeita
    # e a request quebra com ValueError. Bug introduzido com o workflow
    # do pedido (commit 8d77276f) e corrigido durante review desta sessao.
    'VOLTOU_PARA_COTACAO',
    # Roadmap #4: envio da NF (DANFE PDF) por e-mail ao cliente.
    'ENVIOU_NF_EMAIL',
    # Pecas em pedido de venda (estavam em uso em venda_service mas faltavam
    # aqui — registrar_auditoria levantava ValueError ao add/remover peca).
    'ADICIONOU_ITEM_PECA',
    'REMOVEU_ITEM_PECA',
    # Roadmap #36: brindes (peca dada de brinde).
    'ADICIONOU_BRINDE',
    'REMOVEU_BRINDE',
}


def registrar_auditoria(
    venda_id: int,
    usuario: str,
    acao: str,
    *,
    item_id: Optional[int] = None,
    campo_alterado: Optional[str] = None,
    valor_antes: Optional[str] = None,
    valor_depois: Optional[str] = None,
    detalhe: Optional[str] = None,
) -> HoraVendaAuditoria:
    if acao not in ACOES_VALIDAS:
        raise ValueError(f"acao invalida: {acao}. Aceitos: {sorted(ACOES_VALIDAS)}")
    audit = HoraVendaAuditoria(
        venda_id=venda_id,
        item_id=item_id,
        usuario=usuario or 'desconhecido',
        acao=acao,
        campo_alterado=campo_alterado,
        valor_antes=str(valor_antes) if valor_antes is not None else None,
        valor_depois=str(valor_depois) if valor_depois is not None else None,
        detalhe=detalhe,
    )
    db.session.add(audit)
    db.session.flush()
    return audit


__all__ = ['registrar_auditoria', 'ACOES_VALIDAS']
