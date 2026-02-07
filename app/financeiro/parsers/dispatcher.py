# -*- coding: utf-8 -*-
"""
Dispatcher de Comprovantes — Detector de Tipo e Banco
======================================================

Detecta automaticamente se um PDF é comprovante de boleto ou PIX,
identifica o banco de origem, e direciona para o parser correto.

Extensível: para adicionar novo banco, criar parsers/pix_{banco}.py
com funções detectar_pix_{banco} e extrair_comprovantes_pix_{banco},
depois registrar em PARSERS_PIX.
"""

import logging
from typing import Optional

from app.financeiro.parsers.models import ComprovantePix

logger = logging.getLogger(__name__)


# ── Registro de parsers PIX por banco ────────────────────────────────────────

def _lazy_load_sicoob():
    """Lazy import do parser Sicoob (evitar import no boot do app)."""
    from app.financeiro.parsers.pix_sicoob import (
        detectar_pix_sicoob,
        extrair_comprovantes_pix_sicoob,
    )
    return {
        'detectar': detectar_pix_sicoob,
        'extrair': extrair_comprovantes_pix_sicoob,
    }


# Registry: banco → { 'detectar': fn(texto) -> bool, 'extrair': fn(bytes) -> list }
# Lazy-loaded na primeira chamada para não importar na inicialização
_PARSERS_PIX_CACHE: dict = {}


def _get_parsers_pix() -> dict:
    """Retorna registry de parsers PIX, inicializando lazy se necessário."""
    if not _PARSERS_PIX_CACHE:
        _PARSERS_PIX_CACHE['sicoob'] = _lazy_load_sicoob()
        # Futuro: _PARSERS_PIX_CACHE['grafeno'] = _lazy_load_grafeno()
    return _PARSERS_PIX_CACHE


# ── Funções públicas ─────────────────────────────────────────────────────────

def _ler_primeira_pagina(pdf_bytes: bytes) -> str:
    """Lê o texto da primeira página do PDF."""
    try:
        from pypdf import PdfReader
        from io import BytesIO
        reader = PdfReader(BytesIO(pdf_bytes))
        if reader.pages:
            return reader.pages[0].extract_text() or ''
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"[Dispatcher] Erro pypdf na primeira página: {e}")

    # Fallback pypdfium2
    try:
        import pypdfium2 as pdfium
        pdf = pdfium.PdfDocument(pdf_bytes)
        if len(pdf) > 0:
            page = pdf[0]
            return page.get_textpage().get_text_range()
    except Exception as e:
        logger.warning(f"[Dispatcher] Erro pypdfium2 na primeira página: {e}")

    return ''


def detectar_tipo_e_banco(pdf_bytes: bytes) -> tuple[str, Optional[str]]:
    """
    Detecta o tipo de comprovante e banco de origem a partir do PDF.

    Returns:
        Tupla (tipo, banco):
        - ('pix', 'sicoob') — PIX do Sicoob
        - ('pix', None) — PIX de banco não suportado
        - ('boleto', 'sicoob') — Boleto do Sicoob
        - ('desconhecido', None) — Tipo não reconhecido
    """
    texto_pag1 = _ler_primeira_pagina(pdf_bytes)

    if not texto_pag1.strip():
        return ('desconhecido', None)

    texto_upper = texto_pag1.upper()

    # Detectar PIX
    if 'PAGAMENTO PIX' in texto_upper or 'PAGAMENTO\nPIX' in texto_upper:
        parsers = _get_parsers_pix()
        for banco, funcs in parsers.items():
            if funcs['detectar'](texto_pag1):
                return ('pix', banco)
        return ('pix', None)  # PIX de banco não suportado

    # Detectar boleto
    if ('PAGAMENTO DE BOLETO' in texto_upper or
            'BOLETO BANCÁRIO' in texto_upper or
            'BOLETO BANCARIO' in texto_upper):
        return ('boleto', 'sicoob')

    return ('desconhecido', None)


def extrair_comprovantes_pix(pdf_bytes: bytes) -> list[ComprovantePix]:
    """
    Detecta banco e extrai comprovantes PIX usando parser correto.

    Args:
        pdf_bytes: Conteúdo binário do PDF.

    Returns:
        Lista de ComprovantePix extraídos.

    Raises:
        ValueError: Se tipo/banco não suportado.
    """
    tipo, banco = detectar_tipo_e_banco(pdf_bytes)

    if tipo != 'pix':
        raise ValueError(
            f"PDF não é comprovante PIX (tipo detectado: '{tipo}')"
        )

    if not banco:
        raise ValueError(
            "Comprovante PIX de banco não suportado. "
            "Bancos suportados: " + ', '.join(_get_parsers_pix().keys())
        )

    parsers = _get_parsers_pix()
    return parsers[banco]['extrair'](pdf_bytes)
