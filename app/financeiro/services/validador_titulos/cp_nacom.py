"""
Leitura da aba CP-NACOM (Contas a Pagar) para validacao de recompra.

Um titulo pode legitimamente estar em 2 bancos quando houve recompra. A recompra
e validada contra a aba 'CP - NACOM' do arquivo CONTAS A PAGAR: se o mesmo
titulo+parcela estiver lancado la, o titulo em 2 bancos e valido.

Produz um conjunto de chaves NF-PARC (Titulo + Parc) presentes no CP.
"""

from typing import List, Set

from app.financeiro.services.validador_titulos.normalizador import montar_nf_parc_partes
from app.financeiro.services.validador_titulos.parsers_bancos import (
    _achar_coluna,
    _celula,
    _norm_col,
    ler_arquivo,
)

ABA_CP_NACOM = "CP - NACOM"
COL_TITULO = "Titulo"
COL_PARC = "Parc"


def extrair_recompras(linhas: List[list]) -> Set[str]:
    """
    Extrai o conjunto de NF-PARC lancados na aba CP-NACOM.

    Localiza as colunas 'Titulo' e 'Parc' pelo nome (linha de cabecalho detectada
    dinamicamente) e monta a chave NF-PARC de cada linha valida.
    """
    alvo_titulo = _norm_col(COL_TITULO)
    alvo_parc = _norm_col(COL_PARC)

    idx_header = None
    col_titulo = col_parc = None
    for idx, linha in enumerate(linhas):
        normalizadas = [_norm_col(c) for c in linha]
        ct = _achar_coluna(normalizadas, alvo_titulo)
        cp = _achar_coluna(normalizadas, alvo_parc)
        if ct is not None and cp is not None:
            idx_header, col_titulo, col_parc = idx, ct, cp
            break
    if idx_header is None:
        raise ValueError(
            "Colunas 'Titulo' e 'Parc' nao encontradas — "
            "o arquivo nao parece a aba CP-NACOM."
        )

    recompras: Set[str] = set()
    for linha in linhas[idx_header + 1:]:
        nf_parc = montar_nf_parc_partes(
            _celula(linha, col_titulo), _celula(linha, col_parc)
        )
        if nf_parc:
            recompras.add(nf_parc)
    return recompras


def ler_cp_nacom(caminho: str) -> Set[str]:
    """Le a aba CP-NACOM do arquivo de Contas a Pagar e extrai as recompras."""
    linhas = ler_arquivo(caminho, aba=ABA_CP_NACOM)
    return extrair_recompras(linhas)
