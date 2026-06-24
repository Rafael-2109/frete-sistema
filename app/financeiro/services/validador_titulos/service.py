"""
Orquestrador do Validador de Titulos x Bancos.

Junta as pecas do processo num unico ponto, chamado pela rota web:
parsers dos 4 bancos + recompras do CP-NACOM + faturamento (contas_a_receber)
+ comparador. Erro num banco e isolado (nao derruba os demais).
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.financeiro.services.validador_titulos.comparador import (
    ResultadoComparacao,
    comparar,
)
from app.financeiro.services.validador_titulos.cp_nacom import ler_cp_nacom
from app.financeiro.services.validador_titulos.faturamento import carregar_faturamento
from app.financeiro.services.validador_titulos.parsers_bancos import parsear_arquivo

logger = logging.getLogger(__name__)


@dataclass
class ResultadoValidacao:
    resultado: ResultadoComparacao
    boletos: List[dict] = field(default_factory=list)
    faturamento: List[dict] = field(default_factory=list)
    recompras: set = field(default_factory=set)
    resumo: Dict[str, int] = field(default_factory=dict)
    erros: Dict[str, str] = field(default_factory=dict)


def processar_validacao(
    caminhos_bancos: Dict[str, str],
    caminho_cp: Optional[str] = None,
    faturamento: Optional[List[dict]] = None,
    filtros_faturamento: Optional[dict] = None,
) -> ResultadoValidacao:
    """
    Executa o processo completo de validacao.

    Args:
        caminhos_bancos: {banco: caminho_do_arquivo} para SRM/GRAFENO/AGIS/VORTX.
        caminho_cp: caminho do arquivo CONTAS A PAGAR (aba CP-NACOM). Opcional.
        faturamento: faturamento ja montado (injecao p/ teste). Se None, busca no banco.
        filtros_faturamento: kwargs para carregar_faturamento.

    Returns:
        ResultadoValidacao com resultado dos 3 cruzamentos, resumo e erros.
    """
    boletos: List[dict] = []
    erros: Dict[str, str] = {}

    for banco, caminho in caminhos_bancos.items():
        try:
            boletos += parsear_arquivo(caminho, banco)
        except Exception as exc:  # noqa: BLE001 — erro por banco vira mensagem ao usuario
            logger.warning("Falha ao ler base do banco %s: %s", banco, exc)
            erros[banco] = str(exc)

    recompras = set()
    if caminho_cp:
        try:
            recompras = ler_cp_nacom(caminho_cp)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Falha ao ler CP-NACOM: %s", exc)
            erros["CP"] = str(exc)

    if faturamento is None:
        faturamento = carregar_faturamento(**(filtros_faturamento or {}))

    resultado = comparar(boletos, faturamento, recompras)

    resumo = {
        "qtd_boletos": len(boletos),
        "qtd_identificados": sum(1 for b in boletos if b.get("nf_parc")),
        "qtd_nao_identificados": len(resultado.nao_identificados),
        "qtd_recompras_cp": len(recompras),
        "qtd_faturamento": len(faturamento),
        "qtd_duplicados": len(resultado.duplicados),
        "qtd_duplicados_sem_recompra": sum(
            1 for d in resultado.duplicados if not d["tem_recompra"]
        ),
        "qtd_duplicados_com_recompra": sum(
            1 for d in resultado.duplicados if d["tem_recompra"]
        ),
        "qtd_faturado_sem_boleto": len(resultado.faturado_sem_boleto),
        "qtd_boleto_sem_nota": len(resultado.boleto_sem_nota),
    }

    return ResultadoValidacao(
        resultado=resultado,
        boletos=boletos,
        faturamento=faturamento,
        recompras=recompras,
        resumo=resumo,
        erros=erros,
    )
