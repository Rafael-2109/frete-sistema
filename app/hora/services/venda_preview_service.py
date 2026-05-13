"""Preview read-only da NFe antes da emissao.

Calcula a margem bruta da venda usando como custo o `preco_compra_esperado`
do pedido de compra (HoraPedidoItem) buscado pelo chassi.

Formula (conforme especificacao do dono fiscal HORA, 2026-05-13):

    Venda Liquida = Venda - Frete - Custo Moto
    Margem Bruta  = Venda - Venda Liquida   (= Frete + Custo Moto)
    % Margem      = Margem Bruta / Venda * 100

Nota: a chave interna do dict permanece `liquido` (rename apenas no UI).

Onde:
  - Venda      = HoraVenda.valor_total (soma dos preco_final dos itens)
  - Frete      = HoraVenda.valor_frete (0 quando NULL)
  - Custo Moto = soma de HoraPedidoItem.preco_compra_esperado por chassi

Read-only: nao escreve em DB, nao tem efeitos colaterais.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from app.hora.models.compra import HoraPedidoItem
from app.hora.models.venda import HoraVenda

ZERO = Decimal('0')


def _custo_moto_por_chassi(chassi: str) -> Optional[Decimal]:
    """Retorna `preco_compra_esperado` da ultima linha de pedido de compra
    que aponta para o chassi. None se nao houver pedido (moto importada
    direto via NF de entrada sem pedido previo).
    """
    item = (
        HoraPedidoItem.query
        .filter(HoraPedidoItem.numero_chassi == chassi)
        .order_by(HoraPedidoItem.id.desc())
        .first()
    )
    if item is None:
        return None
    return item.preco_compra_esperado


def montar_preview(venda: HoraVenda) -> dict:
    """Monta payload read-only para a tela de preview.

    Returns:
        dict com:
          - itens: lista [{chassi, modelo, cor, preco_venda, custo_moto, sem_custo}]
          - venda_total, frete, custo_moto_total: Decimals
          - liquido, margem_bruta: Decimals
          - margem_pct: Decimal (ja em %, ex.: 28.50 = 28,50%)
          - tem_custo_faltante: bool — True se algum chassi nao tem
            preco_compra_esperado (margem fica distorcida).
    """
    itens_preview = []
    custo_total = ZERO
    tem_faltante = False

    for item in venda.itens:
        custo = _custo_moto_por_chassi(item.numero_chassi)
        sem_custo = custo is None
        if sem_custo:
            tem_faltante = True
        else:
            custo_total += custo

        modelo_nome = '—'
        cor = '—'
        if item.moto is not None:
            cor = item.moto.cor or '—'
            if item.moto.modelo is not None:
                modelo_nome = item.moto.modelo.nome_modelo or '—'

        itens_preview.append({
            'numero_chassi': item.numero_chassi,
            'modelo': modelo_nome,
            'cor': cor,
            'preco_venda': item.preco_final or ZERO,
            'custo_moto': custo,
            'sem_custo': sem_custo,
        })

    venda_total = venda.valor_total or ZERO
    frete = venda.valor_frete or ZERO

    liquido = venda_total - frete - custo_total
    margem_bruta = venda_total - liquido

    if venda_total > ZERO:
        margem_pct = (margem_bruta / venda_total) * Decimal('100')
    else:
        margem_pct = ZERO

    return {
        'itens': itens_preview,
        'venda_total': venda_total,
        'frete': frete,
        'custo_moto_total': custo_total,
        'liquido': liquido,
        'margem_bruta': margem_bruta,
        'margem_pct': margem_pct,
        'tem_custo_faltante': tem_faltante,
    }
