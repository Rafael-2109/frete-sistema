"""Helpers para documento fiscal (CPF ou CNPJ) do destinatário/cliente.

Lojas HORA aceita venda B2C (consumidor PF) e ocasionalmente PJ (CNPJ).
O modelo HoraVenda.cpf_cliente é String(14) — comporta ambos.

Mantemos o nome `cpf_cliente` no banco (renomear teria custo > benefício),
mas semanticamente o campo é "documento fiscal do destinatário".
"""
from __future__ import annotations

import re
from typing import Optional, Tuple

# Tipos retornados (constantes locais para facilitar imports nos callers).
TIPO_CPF = 'F'   # Pessoa Física (TagPlus: tipo='F')
TIPO_CNPJ = 'J'  # Pessoa Jurídica (TagPlus: tipo='J')
TIPO_INVALIDO = ''


def so_digitos(valor: Optional[str]) -> str:
    """Mantém apenas dígitos. None/'' -> ''."""
    return re.sub(r'\D', '', valor or '')


def normalizar_documento(valor: Optional[str]) -> Tuple[str, str]:
    """Sanitiza e classifica documento fiscal.

    Returns:
        (digitos, tipo)
          - 11 dígitos -> ('xxx', 'F')  CPF (PF)
          - 14 dígitos -> ('xxx', 'J')  CNPJ (PJ)
          - outro      -> ('xxx', '')   inválido (caller decide se aceita)

    Não validamos dígito verificador — só comprimento. Validação CPF/CNPJ
    rigorosa fica a cargo da SEFAZ na emissão.
    """
    digitos = so_digitos(valor)
    if len(digitos) == 11:
        return digitos, TIPO_CPF
    if len(digitos) == 14:
        return digitos, TIPO_CNPJ
    return digitos, TIPO_INVALIDO


def documento_valido(valor: Optional[str]) -> bool:
    """True se for CPF (11) ou CNPJ (14)."""
    _, tipo = normalizar_documento(valor)
    return tipo != TIPO_INVALIDO


def inferir_consumidor_final(valor: Optional[str]) -> bool:
    """Infere o flag `consumidor_final` (NF-e) a partir do documento.

    Regra heuristica usada como DEFAULT quando o operador nao marcou
    explicitamente o checkbox no formulario:
      - CPF (PF, 11 digitos)  -> True  (B2C tipico de loja HORA)
      - CNPJ (PJ, 14 digitos) -> False (revenda / B2B)
      - documento invalido     -> True  (fallback seguro: B2C)

    Operador pode sobrescrever este default via `HoraVenda.consumidor_final`
    (UI: checkbox no /tagplus/pedido-venda/novo).
    """
    _, tipo = normalizar_documento(valor)
    if tipo == TIPO_CNPJ:
        return False
    return True
