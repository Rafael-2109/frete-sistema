"""
Scanner de Etiqueta Moto — Routes
==================================

POST /api/v1/scanner/moto — Recebe imagem JPEG base64 e retorna dados extraidos.
"""

import time
import logging

from flask import request, jsonify, session
from flask_login import login_required

from . import scanner_bp
from .service import ScannerMotoService

logger = logging.getLogger(__name__)

# Rate limiting in-memory (por sessao)
RATE_LIMIT_MAX = 10       # Max requests
RATE_LIMIT_WINDOW = 60    # Janela em segundos


def _check_rate_limit() -> bool:
    """
    Verifica rate limit por sessao Flask.
    Retorna True se dentro do limite, False se excedeu.
    """
    now = time.time()
    key = '_scanner_requests'

    timestamps = session.get(key, [])

    # Remover timestamps fora da janela
    timestamps = [t for t in timestamps if t > now - RATE_LIMIT_WINDOW]

    if len(timestamps) >= RATE_LIMIT_MAX:
        return False

    timestamps.append(now)
    session[key] = timestamps
    return True


@scanner_bp.route('/moto', methods=['POST'])
@login_required
def escanear_etiqueta_moto():
    """
    Escaneia etiqueta de moto via Claude Vision API.

    Request (JSON):
        {
            "imagem": "<base64-jpeg>"
        }

    Response (JSON):
        {
            "success": true,
            "data": {
                "modelo": "SCOOTER JET",
                "cor": "AZUL",
                "chassi": "MCBRJET2509250027",
                "numero_motor": "...",
                "confianca": 0.95
            }
        }
    """
    # Validar Content-Type
    if not request.is_json:
        return jsonify({
            'success': False,
            'error': 'Content-Type deve ser application/json',
            'code': 'INVALID_CONTENT_TYPE'
        }), 400

    # Rate limiting
    if not _check_rate_limit():
        return jsonify({
            'success': False,
            'error': 'Limite de leituras excedido. Aguarde um momento.',
            'code': 'RATE_LIMITED'
        }), 429

    # Extrair imagem
    data = request.get_json(silent=True)
    if not data or 'imagem' not in data:
        return jsonify({
            'success': False,
            'error': 'Campo "imagem" (base64 JPEG) e obrigatorio.',
            'code': 'MISSING_IMAGE'
        }), 400

    image_base64 = data['imagem']

    # Validar que e string
    if not isinstance(image_base64, str) or len(image_base64) < 100:
        return jsonify({
            'success': False,
            'error': 'Imagem invalida.',
            'code': 'INVALID_IMAGE'
        }), 400

    try:
        result = ScannerMotoService.ler_etiqueta(image_base64)

        response = {
            'success': True,
            'data': result
        }

        # Aviso de baixa confianca
        confianca = result.get('confianca', 0)
        if confianca < 0.5:
            response['aviso'] = 'Leitura com baixa confianca. Confirme os dados manualmente.'

        return jsonify(response)

    except ValueError as e:
        logger.warning("Validacao falhou no scanner: %s", e)
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'VALIDATION_ERROR'
        }), 422

    except RuntimeError as e:
        logger.error("Erro de runtime no scanner: %s", e)
        return jsonify({
            'success': False,
            'error': 'Erro ao processar imagem. Tente novamente.',
            'code': 'VISION_ERROR'
        }), 500

    except Exception as e:
        logger.exception("Erro inesperado no scanner: %s", e)
        return jsonify({
            'success': False,
            'error': 'Erro interno. Tente novamente.',
            'code': 'INTERNAL_ERROR'
        }), 500
