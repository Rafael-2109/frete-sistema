# -*- coding: utf-8 -*-
"""
Parser OFX CarVia + Importacao com Dedup
=========================================

COPIA das funcoes puras do parser financeiro (R1: isolamento CarVia).
FONTE: app/financeiro/services/ofx_parser_service.py

Extrai transacoes de arquivos OFX (SGML) e importa com dedup por FITID.
"""

import re
import logging
from datetime import date
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)


# ===================================================================
# Parser OFX (funcoes puras — copiadas do financeiro)
# ===================================================================

def _extrair_tag(conteudo: str, tag: str) -> str | None:
    """Extrai valor de tag OFX (SGML ou XML)."""
    padrao_sgml = re.compile(rf'<{tag}>([^<\r\n]+)', re.IGNORECASE)
    match = padrao_sgml.search(conteudo)
    if match:
        return match.group(1).strip()
    return None


def _parsear_data_ofx(valor: str | None) -> date | None:
    """Converte data OFX (YYYYMMDD...) para datetime.date."""
    if not valor:
        return None
    try:
        data_str = valor[:8]
        return date(
            year=int(data_str[0:4]),
            month=int(data_str[4:6]),
            day=int(data_str[6:8]),
        )
    except (ValueError, IndexError):
        logger.warning(f"Data OFX invalida: {valor}")
        return None


def _parsear_valor_ofx(valor: str | None) -> Decimal | None:
    """Converte valor OFX para Decimal (ponto decimal, sinal negativo)."""
    if not valor:
        return None
    try:
        return Decimal(valor.strip())
    except (InvalidOperation, ValueError):
        logger.warning(f"Valor OFX invalido: {valor}")
        return None


def _extrair_transacoes(conteudo: str) -> list[dict]:
    """Extrai todas as transacoes (<STMTTRN>) do OFX."""
    transacoes = []
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
    """Parseia arquivo OFX completo.

    Returns:
        dict com acctid, dtstart, dtend, transacoes, total_transacoes
    """
    try:
        conteudo = conteudo_bytes.decode(encoding)
    except UnicodeDecodeError:
        try:
            conteudo = conteudo_bytes.decode('utf-8')
        except UnicodeDecodeError:
            conteudo = conteudo_bytes.decode('latin-1', errors='replace')

    acctid = _extrair_tag(conteudo, 'ACCTID')
    dtstart = _parsear_data_ofx(_extrair_tag(conteudo, 'DTSTART'))
    dtend = _parsear_data_ofx(_extrair_tag(conteudo, 'DTEND'))
    transacoes = _extrair_transacoes(conteudo)

    logger.info(
        f"[CarVia OFX] Arquivo parseado: conta={acctid}, "
        f"periodo={dtstart} a {dtend}, transacoes={len(transacoes)}"
    )

    return {
        'acctid': acctid,
        'dtstart': dtstart,
        'dtend': dtend,
        'transacoes': transacoes,
        'total_transacoes': len(transacoes),
    }


# ===================================================================
# Importacao com Dedup por FITID
# ===================================================================

def importar_extrato_ofx(conteudo_bytes, arquivo_nome, usuario):
    """Parseia OFX e insere linhas com dedup por FITID.

    Args:
        conteudo_bytes: Conteudo do arquivo OFX em bytes
        arquivo_nome: Nome original do arquivo
        usuario: Email do usuario que importou

    Returns:
        dict com total_importadas, total_duplicadas, periodo
    """
    from app import db
    from app.carvia.models import CarviaExtratoLinha

    resultado_ofx = parsear_ofx(conteudo_bytes)
    transacoes = resultado_ofx['transacoes']

    total_importadas = 0
    total_duplicadas = 0

    for trn in transacoes:
        fitid = trn.get('fitid')
        trnamt = trn.get('trnamt')

        if not fitid or trnamt is None:
            logger.warning(f"[CarVia OFX] Transacao ignorada (sem FITID ou valor): {trn}")
            continue

        # Dedup por FITID
        existente = CarviaExtratoLinha.query.filter_by(fitid=fitid).first()
        if existente:
            total_duplicadas += 1
            continue

        # Determinar tipo baseado no sinal
        tipo = 'CREDITO' if trnamt > 0 else 'DEBITO'

        # Montar descricao a partir de name e/ou memo
        descricao_parts = []
        if trn.get('name'):
            descricao_parts.append(trn['name'])
        if trn.get('memo') and trn.get('memo') != trn.get('name'):
            descricao_parts.append(trn['memo'])
        descricao = ' - '.join(descricao_parts) if descricao_parts else None

        linha = CarviaExtratoLinha(
            fitid=fitid,
            data=trn['dtposted'],
            valor=trnamt,
            tipo=tipo,
            descricao=descricao,
            memo=trn.get('memo'),
            checknum=trn.get('checknum'),
            refnum=trn.get('refnum'),
            trntype=trn.get('trntype'),
            arquivo_ofx=arquivo_nome,
            conta_bancaria=resultado_ofx.get('acctid'),
            criado_por=usuario,
        )
        db.session.add(linha)
        total_importadas += 1

    if total_importadas > 0:
        db.session.flush()

    periodo = None
    if resultado_ofx['dtstart'] and resultado_ofx['dtend']:
        periodo = {
            'inicio': resultado_ofx['dtstart'].strftime('%d/%m/%Y'),
            'fim': resultado_ofx['dtend'].strftime('%d/%m/%Y'),
        }

    logger.info(
        f"[CarVia OFX] Importacao: {total_importadas} novas, "
        f"{total_duplicadas} duplicadas, arquivo={arquivo_nome}"
    )

    return {
        'total_importadas': total_importadas,
        'total_duplicadas': total_duplicadas,
        'periodo': periodo,
    }
