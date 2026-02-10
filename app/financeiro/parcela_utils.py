"""
Utilitarios centralizados para conversao do campo `parcela`.

Problema:
    - contas_a_receber.parcela e contas_a_pagar.parcela sao VARCHAR(10)
    - extrato_item.titulo_parcela, extrato_item_titulo.titulo_parcela,
      baixa_pagamento_item.titulo_parcela, lancamento_comprovante.parcela
      sao INTEGER
    - Odoo l10n_br_cobranca_parcela e INTEGER

Este modulo elimina conversoes ad-hoc espalhadas pelo codigo,
tratando None, prefixo "P" (CNAB), strings invalidas, etc.
"""

import logging
from typing import Optional, Union

logger = logging.getLogger(__name__)


def parcela_to_int(parcela: Union[str, int, float, None]) -> Optional[int]:
    """
    Converte parcela de qualquer tipo para int.

    Trata:
    - None -> None (NUNCA retorna 0 para None)
    - int -> int passthrough
    - float -> int (ex: 3.0 -> 3)
    - str "3" -> 3
    - str "P3" -> 3 (prefixo CNAB)
    - str "" -> None
    - str "abc" -> None (com warning)
    - 0 explicito -> 0

    Returns:
        int ou None se valor invalido/ausente
    """
    if parcela is None:
        return None

    if isinstance(parcela, int):
        return parcela

    if isinstance(parcela, float):
        return int(parcela)

    if isinstance(parcela, str):
        cleaned = parcela.strip()
        if not cleaned:
            return None

        # Remover prefixo "P" comum em CNAB (ex: "P3" -> "3")
        cleaned = cleaned.upper().replace('P', '').strip()

        if not cleaned:
            return None

        try:
            return int(cleaned)
        except ValueError:
            logger.warning(f"parcela_to_int: valor invalido '{parcela}' -> None")
            return None

    logger.warning(f"parcela_to_int: tipo inesperado {type(parcela).__name__} -> None")
    return None


def parcela_to_str(parcela: Union[str, int, float, None]) -> Optional[str]:
    """
    Converte parcela de qualquer tipo para string.

    Trata:
    - None -> None
    - str -> str passthrough (strip)
    - int -> str (ex: 3 -> "3")
    - float -> str (ex: 3.0 -> "3")

    Returns:
        str ou None se valor ausente
    """
    if parcela is None:
        return None

    if isinstance(parcela, str):
        cleaned = parcela.strip()
        return cleaned if cleaned else None

    if isinstance(parcela, (int, float)):
        return str(int(parcela))

    logger.warning(f"parcela_to_str: tipo inesperado {type(parcela).__name__} -> None")
    return None


def parcela_to_odoo(parcela: Union[str, int, float, None]) -> Optional[int]:
    """
    Converte parcela para formato Odoo (l10n_br_cobranca_parcela = INTEGER).

    Alias semantico de parcela_to_int para explicitar intencao de uso com Odoo API.
    Retorna None (NAO 0) para valores invalidos — chamador deve tratar None.

    Returns:
        int ou None se valor invalido/ausente
    """
    return parcela_to_int(parcela)
