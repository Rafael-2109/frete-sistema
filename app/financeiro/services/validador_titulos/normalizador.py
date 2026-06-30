"""
Normalizador da chave NF-PARC do Validador de Titulos x Bancos.

Cada banco identifica o titulo num formato proprio (NF/parcela), mas todos
sao reduzidos a uma chave unica canonica:

    NF-PARC = "<numero da NF>-<parcela sem zeros a esquerda>"

Exemplos: "146299/003" -> "146299-3", "148466-001" -> "148466-1".
"""

import re
from typing import Optional

from app.financeiro.parcela_utils import parcela_to_int

_FLOAT_INTEIRO = re.compile(r"^\d+\.0+$")
# Caracteres de controle (NUL e demais C0/DEL) que alguns bancos grudam no numero.
# Precisam ser removidos: quebram o Excel e impedem o casamento da chave entre fontes.
_CONTROLE = re.compile(r"[\x00-\x1f\x7f]")


def limpar_controle(valor) -> str:
    """Remove caracteres de controle (NUL, etc.) de um valor textual."""
    if valor is None:
        return ""
    return _CONTROLE.sub("", str(valor))


def montar_nf_parc(identificador) -> Optional[str]:
    """
    Converte o identificador cru de um titulo na chave canonica NF-PARC.

    Regras:
    - Separador entre NF e parcela: "/" quando presente; senao o ultimo "-".
      Usar o ULTIMO "-" preserva NF com hifen interno (ex: "00103--2").
    - Parcela passa por `parcela_to_int` (remove zeros a esquerda, trata "003"/3.0).
    - Retorna None quando nao da para derivar com seguranca (sem separador,
      parcela nao numerica, NF vazia). None sinaliza "conferir manualmente".

    Returns:
        str canonica "NF-PARC" ou None se invalido/indeterminado.
    """
    if identificador is None:
        return None

    ident = limpar_controle(identificador).strip()
    if not ident:
        return None

    if "/" in ident:
        nf, _, parc = ident.rpartition("/")
    elif "-" in ident:
        nf, _, parc = ident.rpartition("-")
    else:
        return None

    parc_int = parcela_to_int(parc)
    if parc_int is None:
        return None

    nf = nf.strip()
    if not nf:
        return None

    return f"{nf}-{parc_int}"


def _limpar_nf(nf) -> str:
    """Normaliza o numero da NF preservando zeros a esquerda.

    Trata float vindo do Excel (2023.0 -> '2023') sem destruir zeros de
    strings como '00106' (que NAO devem virar '106').
    """
    if nf is None:
        return ""
    if isinstance(nf, float) and nf.is_integer():
        return str(int(nf))
    if isinstance(nf, int):
        return str(nf)
    txt = limpar_controle(nf).strip()
    if _FLOAT_INTEIRO.match(txt):
        txt = txt.split(".")[0]
    return txt


def montar_nf_parc_partes(nf, parcela) -> Optional[str]:
    """
    Monta a chave NF-PARC quando NF e parcela vem em colunas separadas
    (faturamento `contas_a_receber` e aba CP-NACOM).

    Returns:
        str "NF-PARC" ou None se NF vazia ou parcela invalida/ausente.
    """
    nf_limpo = _limpar_nf(nf)
    if not nf_limpo:
        return None

    if isinstance(parcela, str):
        parcela = limpar_controle(parcela)
    parc_int = parcela_to_int(parcela)
    if parc_int is None:
        return None

    return f"{nf_limpo}-{parc_int}"
