"""Briefing inter-sessao do Agente."""

import logging

from flask import jsonify
from flask_login import login_required, current_user

from app.agente.routes import agente_bp

logger = logging.getLogger('sistema_fretes')


@agente_bp.route('/api/briefing', methods=['GET'])
@login_required
def api_get_briefing():
    """
    Retorna briefing inter-sessao como JSON estruturado.

    GET /agente/api/briefing

    Response:
    {
        "success": true,
        "has_content": true,
        "since": "04/04 09:30",
        "items": [
            {"type": "last_intent", "content": "..."},
            {"type": "odoo_errors", "total": 3, "top": "..."},
            {"type": "import_failures", "count": 2},
            {"type": "memory_alerts", "details": "..."},
            {"type": "stale_memories", "count": 5},
            {"type": "intelligence", "content": "..."}
        ]
    }
    """
    try:
        import re
        from app.agente.services.intersession_briefing import build_intersession_briefing

        xml_content = build_intersession_briefing(current_user.id)

        if not xml_content:
            return jsonify({
                'success': True,
                'has_content': False,
                'since': None,
                'items': [],
            })

        # Parsear XML para JSON estruturado (regex simples — XML pode ser malformado)
        items = []

        # Extrair since do header
        since_match = re.search(r'since="([^"]*)"', xml_content)
        since = since_match.group(1) if since_match else None

        # last_session_intent
        intent_match = re.search(
            r'<last_session_intent\s+type="([^"]*)"(?:\s+remaining="(\d+)")?>(.*?)</last_session_intent>',
            xml_content, re.DOTALL,
        )
        if intent_match:
            items.append({
                'type': 'last_intent',
                'intent_type': intent_match.group(1),
                'remaining': int(intent_match.group(2)) if intent_match.group(2) else 0,
                'content': intent_match.group(3).strip(),
            })

        # odoo_sync_errors
        odoo_match = re.search(
            r'<odoo_sync_errors\s+total="(\d+)"[^>]*>(.*?)</odoo_sync_errors>',
            xml_content, re.DOTALL,
        )
        if odoo_match:
            items.append({
                'type': 'odoo_errors',
                'total': int(odoo_match.group(1)),
                'details': odoo_match.group(2).strip(),
            })

        # import_failures
        import_match = re.search(
            r'<import_failures\s+count="(\d+)"',
            xml_content,
        )
        if import_match:
            items.append({
                'type': 'import_failures',
                'count': int(import_match.group(1)),
            })

        # memory_alerts, stale_memories, intelligence — omitidos do card do usuario
        # Sao informacoes internas da IA sem valor acionavel para operadores.
        # Permanecem no XML injetado no prompt do agente (intersession_briefing.py).

        return jsonify({
            'success': True,
            'has_content': len(items) > 0,
            'since': since,
            'items': items,
        })

    except Exception as e:
        logger.error(f"[BRIEFING] Erro ao gerar briefing: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
        }), 500
