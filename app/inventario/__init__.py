"""Módulo de Inventário — Relatório de Confronto.

Cruza inventário físico FB/CD/LF com movimentações Odoo pós-inventário,
estoque atual Odoo, movimentações do sistema_fretes e ajustes manuais.
Spec: docs/superpowers/specs/2026-05-26-relatorio-confronto-inventario-design.md
"""
from flask import Blueprint

inventario_bp = Blueprint(
    'inventario',
    __name__,
    url_prefix='/inventario',
    template_folder='../templates/inventario',
)

from app.inventario.routes import (  # noqa: E402, F401
    ciclo_routes,
    confronto_routes,
    ajustes_manuais_routes,
    snapshot_routes,
    movimentacoes_routes,
)
