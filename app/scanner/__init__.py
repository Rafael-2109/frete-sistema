"""
Scanner de Etiqueta de Motos — Modulo de leitura por camera
===========================================================

Componente reutilizavel que usa camera do celular/tablet para ler
etiquetas de motos (modelo, cor, chassi) via barcode + Claude Vision API.

Blueprint: /api/v1/scanner
"""

from flask import Blueprint

scanner_bp = Blueprint('scanner', __name__, url_prefix='/api/v1/scanner')

from . import routes  # noqa: E402,F401


def init_app(app):
    """Registra blueprint do scanner."""
    app.register_blueprint(scanner_bp)
    app.logger.info("Scanner de Etiqueta Moto registrado")
