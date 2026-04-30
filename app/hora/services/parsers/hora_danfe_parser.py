"""Subclasse do `DanfePDFParser` (CarVia) com hook de append-prompt HORA.

REGRA DE FRONTEIRA: nao editar `app/carvia/services/parsers/danfe_pdf_parser.py`.
A integracao especifica HORA (append-prompt aprendido por feedback) e
implementada via subclasse aqui.

A subclasse sobrescreve `_extrair_veiculos_llm` apenas para PREFIXAR o
`texto_secao` com o append-prompt ativo (lido de
`app.hora.services.parser_append_service.texto_append_ativo`). O LLM
recebe instrucoes adicionais como parte do contexto e segue normalmente.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from app.carvia.services.parsers.danfe_pdf_parser import DanfePDFParser

logger = logging.getLogger(__name__)


class HoraDanfePDFParser(DanfePDFParser):
    """Parser DANFE com append-prompt HORA injetado no prompt do LLM."""

    def _extrair_veiculos_llm(
        self,
        model: str,
        texto_secao: str,
        qtd_esperada: Optional[int] = None,
        ja_extraidos: Optional[List[Dict]] = None,
        itens_contexto: Optional[List[Dict]] = None,
    ) -> Optional[List[Dict]]:
        # Le append ativo do banco. Em runtime sem app context (testes),
        # cai no comportamento padrao sem append.
        append = ''
        try:
            from app.hora.services.parser_append_service import (
                texto_append_ativo,
            )
            append = (texto_append_ativo() or '').strip()
        except Exception:
            logger.exception(
                'HoraDanfePDFParser: falha ao ler append ativo — '
                'continuando sem append.'
            )
            append = ''

        if append:
            texto_secao = (
                "INSTRUCOES OPERACIONAIS ADICIONAIS DA HORA "
                "(aprendidas por feedback do operador — RESPEITE):\n"
                f"{append}\n"
                "--- FIM DAS INSTRUCOES ADICIONAIS ---\n\n"
                f"{texto_secao}"
            )

        return super()._extrair_veiculos_llm(
            model=model,
            texto_secao=texto_secao,
            qtd_esperada=qtd_esperada,
            ja_extraidos=ja_extraidos,
            itens_contexto=itens_contexto,
        )
