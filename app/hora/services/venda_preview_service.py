"""Preview read-only da NFe antes da emissao.

Calcula a margem bruta da venda usando o CUSTO de cada item (nao o preco de
venda). Custos considerados:

  - Custo Moto    = HoraPedidoItem.preco_compra_esperado por chassi (ao vivo).
  - Custo Pecas   = soma de qtd * HoraVendaItemPeca.custo_unitario (snapshot
                    de hora_peca.custo gravado na venda — migration hora_59).
  - Custo Brindes = soma de HoraVendaBrinde.custo_total (snapshot de
                    hora_peca.custo — hora_59; antes usava preco_venda_padrao).

Formula (conforme especificacao do dono fiscal HORA, 2026-05-13; estendida em
2026-06-28 para custo de pecas vendidas):

    Venda Liquida = Venda - Frete - Custo Moto - Custo Pecas - Custo Brindes
    Margem Bruta  = Venda - Venda Liquida
    % Margem      = Margem Bruta / Venda * 100

Nota: a chave interna do dict permanece `liquido` (rename apenas no UI).

Onde:
  - Venda = HoraVenda.valor_total (soma dos preco_final dos itens moto + peca)
  - Frete = HoraVenda.valor_frete (0 quando NULL)

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
          - itens: lista [{numero_chassi, modelo, cor, preco_venda, custo_moto, sem_custo}]
          - pecas: lista [{descricao, qtd, preco_venda, custo_unitario, custo_total, sem_custo}]
          - venda_total, frete, custo_moto_total, custo_pecas_total,
            custo_brindes_total: Decimals
          - liquido, margem_bruta: Decimals
          - margem_pct: Decimal (ja em %, ex.: 28.50 = 28,50%)
          - tem_custo_faltante: bool — algum chassi sem preco_compra_esperado.
          - tem_peca_sem_custo: bool — alguma peca vendida com custo 0 (margem
            distorcida ate cadastrar o custo da peca).
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

    # Pecas vendidas (cobradas) — custo via snapshot custo_unitario (hora_59).
    pecas_preview = []
    custo_pecas_total = ZERO
    tem_peca_sem_custo = False
    for ip in (venda.itens_peca or []):
        qtd = Decimal(str(ip.qtd or 0))
        custo_uni = Decimal(str(ip.custo_unitario or 0))
        custo_linha = qtd * custo_uni
        custo_pecas_total += custo_linha
        sem_custo_peca = custo_uni <= ZERO and qtd > ZERO
        if sem_custo_peca:
            tem_peca_sem_custo = True
        pecas_preview.append({
            'descricao': ip.peca.descricao if ip.peca else '—',
            'qtd': qtd,
            'preco_venda': ip.preco_final or ZERO,
            'custo_unitario': custo_uni,
            'custo_total': custo_linha,
            'sem_custo': sem_custo_peca,
        })

    venda_total = venda.valor_total or ZERO
    frete = venda.valor_frete or ZERO

    # Brindes (#36): o custo entra na margem (reduz o liquido), mas NAO no valor
    # cobrado (valor_total). Custo = snapshot de hora_peca.custo (hora_59).
    custo_brindes_total = sum(
        (Decimal(str(b.custo_total or 0)) for b in (venda.brindes or [])), ZERO,
    )

    liquido = venda_total - frete - custo_total - custo_pecas_total - custo_brindes_total
    margem_bruta = venda_total - liquido

    if venda_total > ZERO:
        margem_pct = (margem_bruta / venda_total) * Decimal('100')
    else:
        margem_pct = ZERO

    return {
        'itens': itens_preview,
        'pecas': pecas_preview,
        'venda_total': venda_total,
        'frete': frete,
        'custo_moto_total': custo_total,
        'custo_pecas_total': custo_pecas_total,
        'custo_brindes_total': custo_brindes_total,
        'liquido': liquido,
        'margem_bruta': margem_bruta,
        'margem_pct': margem_pct,
        'tem_custo_faltante': tem_faltante,
        'tem_peca_sem_custo': tem_peca_sem_custo,
    }
