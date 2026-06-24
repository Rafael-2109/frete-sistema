"""
Normalizador da chave NF-PARC do Validador de Titulos x Bancos.

Cada banco identifica o titulo num formato proprio (NF/parcela), mas todos
sao reduzidos a uma chave unica canonica:

    NF-PARC = "<numero da NF>-<parcela sem zeros a esquerda>"

Exemplos: "146299/003" -> "146299-3", "148466-001" -> "148466-1".
"""

from typing import Optional

from app.financeiro.parcela_utils import parcela_to_int


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

    ident = str(identificador).strip()
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
