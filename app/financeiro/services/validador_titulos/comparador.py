"""
Comparador do Validador de Titulos x Bancos.

Recebe as listas ja normalizadas (boletos dos bancos, faturamento, recompras do CP)
e produz os 3 cruzamentos do processo de conferencia:

1. duplicados        — titulos presentes em 2+ bancos (com flag de recompra no CP)
2. faturado_sem_boleto — notas faturadas sem boleto em nenhum banco
3. boleto_sem_nota   — boletos que nao batem com nenhuma nota faturada

Boletos sem chave NF-PARC (dados sujos) nao podem casar e vao para
`nao_identificados`, para conferencia manual.

Logica pura, sem dependencia de Flask/banco.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set


@dataclass
class ResultadoComparacao:
    duplicados: List[dict] = field(default_factory=list)
    faturado_sem_boleto: List[dict] = field(default_factory=list)
    boleto_sem_nota: List[dict] = field(default_factory=list)
    nao_identificados: List[dict] = field(default_factory=list)


def comparar(
    boletos: List[dict],
    faturamento: List[dict],
    cp_recompras: Set[str],
) -> ResultadoComparacao:
    """
    Args:
        boletos: dicts com pelo menos 'nf_parc' e 'banco' (+ campos livres).
                 'nf_parc' None/vazio => boleto nao identificado.
        faturamento: dicts com pelo menos 'nf_parc' (+ campos livres).
        cp_recompras: conjunto de NF-PARC lancados na aba CP-NACOM.

    Returns:
        ResultadoComparacao com as 4 listas.
    """
    resultado = ResultadoComparacao()

    # Indexar boletos identificados por NF-PARC -> conjunto de bancos
    bancos_por_titulo: Dict[str, Set[str]] = {}
    for b in boletos:
        nf_parc = b.get("nf_parc")
        if not nf_parc:
            resultado.nao_identificados.append(b)
            continue
        bancos_por_titulo.setdefault(nf_parc, set()).add(b.get("banco"))

    titulos_com_boleto: Set[str] = set(bancos_por_titulo.keys())

    # 1) Duplicados: em 2+ bancos distintos
    for nf_parc in sorted(bancos_por_titulo):
        bancos = bancos_por_titulo[nf_parc]
        if len(bancos) >= 2:
            resultado.duplicados.append({
                "nf_parc": nf_parc,
                "bancos": sorted(bancos),
                "qtd_bancos": len(bancos),
                "tem_recompra": nf_parc in cp_recompras,
            })

    # 2) Faturado sem boleto
    for f in faturamento:
        nf_parc = f.get("nf_parc")
        if nf_parc and nf_parc not in titulos_com_boleto:
            resultado.faturado_sem_boleto.append(f)

    # 3) Boleto sem nota
    titulos_faturados: Set[str] = {
        f.get("nf_parc") for f in faturamento if f.get("nf_parc")
    }
    for nf_parc in sorted(bancos_por_titulo):
        if nf_parc not in titulos_faturados:
            resultado.boleto_sem_nota.append({
                "nf_parc": nf_parc,
                "bancos": sorted(bancos_por_titulo[nf_parc]),
            })

    return resultado
