# -*- coding: utf-8 -*-
"""
Utilitarios compartilhados para workers financeiros
====================================================

Context manager seguro para execucao em workers RQ.

Autor: Sistema de Fretes
Data: 2026-02-14
"""

import logging
import os
import sys
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@contextmanager
def app_context_safe():
    """
    Context manager seguro para execucao no worker RQ.

    Verifica se ja existe um contexto Flask ativo para evitar
    criar contextos aninhados que podem causar travamentos.

    Uso:
        with app_context_safe():
            # codigo que precisa de contexto Flask
    """
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

    from flask import has_app_context

    # Se ja existe contexto ativo, apenas executa o codigo (nao cria novo contexto)
    if has_app_context():
        logger.debug("[Context] Reutilizando contexto Flask existente")
        yield
        return

    # Criar novo contexto apenas quando necessario
    from app import create_app
    app = create_app()
    logger.debug("[Context] Novo contexto Flask criado")

    with app.app_context():
        yield
