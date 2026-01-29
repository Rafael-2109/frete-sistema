# -*- coding: utf-8 -*-
"""
Parser OFX para Extrato Bancário (Sicoob)
==========================================

Parser manual (sem dependências externas) que extrai transações de arquivos OFX (SGML).

Extrai de cada <STMTTRN>:
- FITID, CHECKNUM, REFNUM, DTPOSTED, TRNAMT, MEMO, NAME, TRNTYPE

Extrai do header:
- DTSTART, DTEND (período do extrato)
- ACCTID (número da conta)

Uso:
    from app.financeiro.services.ofx_parser_service import parsear_ofx

    resultado = parsear_ofx(conteudo_bytes)
    # resultado = {
    #     'acctid': '450782',
    #     'dtstart': date(2026, 1, 28),
    #     'dtend': date(2026, 1, 28),
    #     'transacoes': [
    #         {
    #             'fitid': '202601281597021',
    #             'checknum': '20834751',
    #             'refnum': '20834751',
    #             'dtposted': date(2026, 1, 28),
    #             'trnamt': Decimal('-1597.02'),
    #             'memo': 'DÉB.TIT.COMPE EFETIVADO',
    #             'name': 'PAG BOLETO',
    #             'trntype': 'DEBIT',
    #         },
    #         ...
    #     ]
    # }
"""

import re
import logging
from datetime import date
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)


def _extrair_tag(conteudo: str, tag: str) -> str | None:
    """
    Extrai o valor de uma tag OFX (formato SGML).

    Formato SGML: <TAG>valor (sem tag de fechamento)
    Formato XML:  <TAG>valor</TAG>

    Retorna None se a tag não existir.
    """
    # Tenta SGML primeiro (mais comum em OFX brasileiro)
    padrao_sgml = re.compile(rf'<{tag}>([^<\r\n]+)', re.IGNORECASE)
    match = padrao_sgml.search(conteudo)
    if match:
        return match.group(1).strip()
    return None


def _parsear_data_ofx(valor: str | None) -> date | None:
    """
    Converte data OFX para datetime.date.

    Formatos aceitos:
    - 20260128 (YYYYMMDD)
    - 20260128120000 (YYYYMMDDHHMMSS)
    - 20260128120000[-3:BRT] (com timezone)
    """
    if not valor:
        return None

    try:
        # Pegar apenas os 8 primeiros caracteres (YYYYMMDD)
        data_str = valor[:8]
        return date(
            year=int(data_str[0:4]),
            month=int(data_str[4:6]),
            day=int(data_str[6:8]),
        )
    except (ValueError, IndexError):
        logger.warning(f"Data OFX inválida: {valor}")
        return None


def _parsear_valor_ofx(valor: str | None) -> Decimal | None:
    """
    Converte valor OFX para Decimal.

    Formato: -1597.02 (ponto como separador decimal, sinal negativo)
    """
    if not valor:
        return None

    try:
        return Decimal(valor.strip())
    except (InvalidOperation, ValueError):
        logger.warning(f"Valor OFX inválido: {valor}")
        return None


def _extrair_transacoes(conteudo: str) -> list[dict]:
    """
    Extrai todas as transações (<STMTTRN>...</STMTTRN>) do OFX.

    Retorna lista de dicts com os campos de cada transação.
    """
    transacoes = []

    # Encontrar todos os blocos <STMTTRN>...</STMTTRN>
    padrao = re.compile(
        r'<STMTTRN>(.*?)</STMTTRN>',
        re.DOTALL | re.IGNORECASE,
    )

    for match in padrao.finditer(conteudo):
        bloco = match.group(1)

        transacao = {
            'trntype': _extrair_tag(bloco, 'TRNTYPE'),
            'dtposted': _parsear_data_ofx(_extrair_tag(bloco, 'DTPOSTED')),
            'trnamt': _parsear_valor_ofx(_extrair_tag(bloco, 'TRNAMT')),
            'fitid': _extrair_tag(bloco, 'FITID'),
            'checknum': _extrair_tag(bloco, 'CHECKNUM'),
            'refnum': _extrair_tag(bloco, 'REFNUM'),
            'memo': _extrair_tag(bloco, 'MEMO'),
            'name': _extrair_tag(bloco, 'NAME'),
        }

        transacoes.append(transacao)

    return transacoes


def parsear_ofx(conteudo_bytes: bytes, encoding: str = 'latin-1') -> dict:
    """
    Parseia um arquivo OFX completo.

    Args:
        conteudo_bytes: Conteúdo do arquivo OFX em bytes.
        encoding: Encoding do arquivo (padrão: latin-1 para bancos brasileiros).

    Returns:
        dict com:
        - acctid: Número da conta
        - dtstart: Data início do período
        - dtend: Data fim do período
        - transacoes: Lista de transações
        - total_transacoes: Quantidade de transações
    """
    # Decodificar conteúdo
    try:
        conteudo = conteudo_bytes.decode(encoding)
    except UnicodeDecodeError:
        # Fallback para utf-8
        try:
            conteudo = conteudo_bytes.decode('utf-8')
        except UnicodeDecodeError:
            conteudo = conteudo_bytes.decode('latin-1', errors='replace')

    # Extrair dados do header
    acctid = _extrair_tag(conteudo, 'ACCTID')
    dtstart = _parsear_data_ofx(_extrair_tag(conteudo, 'DTSTART'))
    dtend = _parsear_data_ofx(_extrair_tag(conteudo, 'DTEND'))

    # Extrair transações
    transacoes = _extrair_transacoes(conteudo)

    logger.info(
        f"[OFX Parser] Arquivo parseado: conta={acctid}, "
        f"período={dtstart} a {dtend}, transações={len(transacoes)}"
    )

    return {
        'acctid': acctid,
        'dtstart': dtstart,
        'dtend': dtend,
        'transacoes': transacoes,
        'total_transacoes': len(transacoes),
    }
