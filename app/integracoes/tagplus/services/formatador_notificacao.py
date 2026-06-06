# app/integracoes/tagplus/services/formatador_notificacao.py
"""Formata pedido/NF do TagPlus em texto WhatsApp-friendly (regra R8).

Sem tabela markdown, sem headers (##), sem code block. Usa *bold*, emojis e
listas. Valores em R$ no padrão brasileiro.
"""
from __future__ import annotations

from typing import Optional

MAX_ITENS = 30


def _valor_br(v) -> str:
    try:
        n = float(v or 0)
    except (TypeError, ValueError):
        n = 0.0
    return f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _data_br(s) -> str:
    if not s or not isinstance(s, str):
        return ""
    d = s[:10]  # 'YYYY-MM-DD...'
    partes = d.split("-")
    if len(partes) == 3:
        return f"{partes[2]}/{partes[1]}/{partes[0]}"
    return d


def _linhas_itens(itens: list, chave_produto: str) -> list[str]:
    linhas = []
    total = len(itens or [])
    for item in (itens or [])[:MAX_ITENS]:
        prod = item.get(chave_produto) or {}
        cod = prod.get("codigo", "") or item.get("item", "")
        desc = prod.get("descricao", "") or ""
        qtd = item.get("qtd", 0) or 0
        vu = _valor_br(item.get("valor_unitario", 0))
        linhas.append(f"- {cod} {desc} — {qtd} x R$ {vu}")
    if total > MAX_ITENS:
        linhas.append(f"… (+{total - MAX_ITENS} itens)")
    return linhas


def formatar_nfe(nfe: dict, vendedor_nome: Optional[str] = None) -> str:
    numero = nfe.get("numero", "?")
    serie = nfe.get("serie", "?")
    dest = nfe.get("destinatario") or {}
    cliente = dest.get("razao_social", "") or ""
    valor = _valor_br(nfe.get("valor_nota", 0))
    data = _data_br(nfe.get("data_emissao"))

    linhas = [f"🧾 *Nova NF emitida — Nº {numero}/{serie}*"]
    if cliente:
        linhas.append(f"👤 Cliente: {cliente}")
    if vendedor_nome:
        linhas.append(f"🧑‍💼 Vendedor: {vendedor_nome}")
    linhas.append(f"💰 Valor: R$ {valor}")
    if data:
        linhas.append(f"📅 {data}")
    itens = _linhas_itens(nfe.get("itens"), "produto")
    if itens:
        linhas.append("")
        linhas.append("Itens:")
        linhas.extend(itens)
    return "\n".join(linhas)


def formatar_pedido(pedido: dict) -> str:
    numero = pedido.get("numero", "?")
    cliente = (pedido.get("cliente") or {}).get("razao_social", "") or ""
    vendedor = (pedido.get("vendedor") or {}).get("nome", "") or ""
    valor = _valor_br(pedido.get("valor_total", 0))
    entrega = _data_br(pedido.get("data_entrega"))
    obs = (pedido.get("observacoes") or "").strip()

    linhas = [f"🛒 *Novo pedido — Nº {numero}*"]
    if cliente:
        linhas.append(f"👤 Cliente: {cliente}")
    if vendedor:
        linhas.append(f"🧑‍💼 Vendedor: {vendedor}")
    linhas.append(f"💰 Valor: R$ {valor}")
    if entrega:
        linhas.append(f"🚚 Entrega: {entrega}")
    if obs:
        linhas.append(f"📝 {obs[:200]}")
    itens = _linhas_itens(pedido.get("itens"), "produto_servico")
    if itens:
        linhas.append("")
        linhas.append("Itens:")
        linhas.extend(itens)
    return "\n".join(linhas)
