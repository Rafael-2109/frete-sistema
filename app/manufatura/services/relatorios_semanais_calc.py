"""
Núcleo de cálculo PURO dos Relatórios Semanais de Manufatura.

Este módulo NÃO importa nada de `app` (sem banco, sem app context, sem rede):
contém apenas as regras algorítmicas determinísticas dos 3 relatórios, para
poderem ser testadas isoladamente. A orquestração com banco/Excel vive em
`relatorios_semanais_service.py`.

Relatórios:
  1. Consumo Componentes  → classificar_aba(contexto='rel1') + flatten_bom_folhas
  2. Estoques             → classificar_aba(contexto='rel2')
  3. Tempo de Estoque     → simular_producao_pa + tempo_estoque_sem_pa / _com_pa
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

# Horizonte da simulação de buffer de Produto Acabado (Relatório 3)
MESES_HORIZONTE = 12
# Conversão mês → dias usada em todos os tempos de estoque
DIAS_MES = 30


def classificar_aba(
    cod_produto: str,
    tipo_materia_prima: Optional[str],
    *,
    contexto: str,
) -> str:
    """
    Classifica um produto na aba de destino conforme o prefixo do código e,
    no Relatório 2, o flag de matéria-prima.

    Args:
        cod_produto: código do produto (o prefixo é o 1º dígito).
        tipo_materia_prima: valor de CadastroPalletizacao.tipo_materia_prima.
        contexto: 'rel1' (Consumo) ou 'rel2' (Estoques).

    Returns:
        'INSUMOS' | 'EMBALAGENS' | 'PRODUTO_ACABADO' | 'MP_EXCLUIDO' | 'OUTROS'

    Regras:
        rel1 (Consumo Componentes): 1→INSUMOS, 2→EMBALAGENS, resto→OUTROS.
              NÃO exclui matéria-prima (todo código 1 é Insumo).
        rel2 (Estoques): 1+MP→MP_EXCLUIDO, 1→INSUMOS, 2→EMBALAGENS,
              4→PRODUTO_ACABADO, resto→OUTROS.
    """
    prefixo = (cod_produto or "").strip()[:1]
    eh_mp = (tipo_materia_prima or "").strip().upper() == "MP"

    if contexto == "rel2":
        if prefixo == "1":
            return "MP_EXCLUIDO" if eh_mp else "INSUMOS"
        if prefixo == "2":
            return "EMBALAGENS"
        if prefixo == "4":
            return "PRODUTO_ACABADO"
        return "OUTROS"

    # contexto == 'rel1'
    if prefixo == "1":
        return "INSUMOS"
    if prefixo == "2":
        return "EMBALAGENS"
    return "OUTROS"


def flatten_bom_folhas(bom_node: Dict[str, Any]) -> Dict[str, float]:
    """
    Percorre a árvore retornada por `ServicoBOM.explodir_bom` e acumula a
    `qtd_necessaria` (já escalada pela recursão) dos nós FOLHA — aqueles sem
    `componentes`. Códigos repetidos em branches diferentes são somados.

    Nós com `tipo == 'ERRO'` (loop infinito / profundidade excedida) são
    ignorados. Nós `DESCONHECIDO` (componente sem cadastro) NÃO são ignorados:
    são folhas reais de uma BOM e entram no consumo (apenas faltam metadados).

    Observação: se a própria raiz não tiver estrutura (PA sem BOM), ela é a
    folha e retorna {cod_raiz: qtd}. Cabe ao caller usar `tem_estrutura` para
    rotular "S/ Estrutura" e não tratar a raiz como componente.
    """
    acumulado: Dict[str, float] = {}

    def _walk(node: Dict[str, Any]) -> None:
        componentes = node.get("componentes") or []
        if componentes:
            for filho in componentes:
                _walk(filho)
            return
        # nó folha
        if node.get("tipo") == "ERRO":
            return
        cod = node.get("cod_produto")
        if cod is None:
            return
        acumulado[cod] = acumulado.get(cod, 0.0) + float(node.get("qtd_necessaria") or 0.0)

    _walk(bom_node)
    return acumulado


def colapsar_por_unificacao(
    valores: Dict[str, float],
    mapa_unificacao: Dict[str, str],
) -> Dict[str, float]:
    """
    Consolida um dict {cod_produto: valor} sob o código CANÔNICO de cada grupo
    de unificação, somando substitutos. Garante que consumo, venda e estoque
    sejam contados UMA vez por grupo (não duplicados entre código origem e
    destino).

    Args:
        valores: {cod_produto: valor} (consumo, saldo, qtd pedida, ...).
        mapa_unificacao: {cod_origem: cod_canonico}. Códigos ausentes do mapa
            ficam como estão (sem unificação).
    """
    consolidado: Dict[str, float] = {}
    for cod, valor in valores.items():
        canonico = mapa_unificacao.get(cod, cod)
        consolidado[canonico] = consolidado.get(canonico, 0.0) + float(valor)
    return consolidado


def simular_producao_pa(
    estoque_pa: float,
    venda_media_mes: float,
    meses: int = MESES_HORIZONTE,
) -> List[float]:
    """
    Necessidade de produção por mês de um Produto Acabado, absorvendo o estoque
    atual de PA (buffer) contra a venda média mensal (Relatório 3, Variante B).

    Para cada mês:
        producao = max(0, venda_media - saldo_pa)   # parcial no mês que esgota
        saldo_pa = max(0, saldo_pa - venda_media)

    Returns:
        Lista de `meses` valores (necessidade de produção por mês).
    """
    # Estoque de PA negativo (oversold / dado inconsistente) NÃO é buffer real:
    # clampa em 0 para não inflar a produção do primeiro mês.
    saldo = max(0.0, float(estoque_pa))
    venda = float(venda_media_mes)
    producao: List[float] = []
    for _ in range(meses):
        prod = venda - saldo
        producao.append(prod if prod > 0 else 0.0)
        saldo = saldo - venda
        if saldo < 0:
            saldo = 0.0
    return producao


def tempo_estoque_sem_pa(
    estoque_componente: float,
    consumo_medio_mes: float,
    dias_mes: int = DIAS_MES,
) -> float:
    """
    Tempo de Estoque S/ PA (Variante A): divisão direta do estoque do
    componente pelo consumo médio mensal, convertido em dias.

    Consumo <= 0 → cobertura infinita (sem consumo no horizonte).
    Estoque <= 0 → 0 dias (sem cobertura; negativo não vira dias negativos).
    """
    if consumo_medio_mes <= 0:
        return float("inf")
    if estoque_componente <= 0:
        return 0.0
    return (float(estoque_componente) / float(consumo_medio_mes)) * dias_mes


def tempo_estoque_com_pa(
    estoque_componente: float,
    consumo_por_mes: List[float],
    dias_mes: int = DIAS_MES,
) -> float:
    """
    Tempo de Estoque C/ PA (Variante B): caminhada mês a mês na agenda de
    consumo do componente (já deslocada pelo buffer de PA).

    Regra (design):
        - consumo do mês == 0  → soma 30 dias "grátis" (mês coberto por PA).
        - estoque >= consumo   → abate o consumo, soma 30 dias, segue.
        - estoque <  consumo   → soma 30 * (saldo/consumo) e encerra.
        - sobreviveu ao horizonte → cap = len(consumo_por_mes) * 30 dias.

    Estoque negativo é clampado em 0 (sem cobertura; não gera dias negativos).
    """
    saldo = max(0.0, float(estoque_componente))
    dias = 0.0
    for consumo in consumo_por_mes:
        c = float(consumo)
        if c <= 0:
            dias += dias_mes
            continue
        if saldo >= c:
            saldo -= c
            dias += dias_mes
        else:
            dias += dias_mes * (saldo / c)
            return dias
    return dias
