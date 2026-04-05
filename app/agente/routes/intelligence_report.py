"""Bridge D7 — Intelligence Report (Agent SDK <-> Claude Code cron)."""

import logging
import os

from flask import request, jsonify, Response
from flask_login import login_required

from app.agente.routes import agente_bp
from app import csrf, db

logger = logging.getLogger('sistema_fretes')


@agente_bp.route('/api/intelligence-report', methods=['POST'])
@csrf.exempt
def save_intelligence_report():
    """
    Persiste relatorio de inteligencia do agente (D7 do cron semanal).

    POST /agente/api/intelligence-report
    Headers:
        X-Cron-Key: <CRON_API_KEY>
    Body (JSON):
        {
            "report_date": "2026-03-28",
            "health_score": 78.0,
            "friction_score": 23.0,
            "recommendation_count": 3,
            "sessions_analyzed": 45,
            "report_json": {...},
            "report_markdown": "# Agent Intelligence Report...",
            "backlog_json": [...]
        }

    Autenticacao via CRON_API_KEY (env var no Render).
    Upsert: se ja existe relatorio para a data, atualiza.
    Backlog: o cron D7 faz o merge completo antes de enviar — server persiste como esta.
    """
    import hmac

    # ── Autenticacao ──
    cron_key = os.environ.get('CRON_API_KEY', '')
    if not cron_key:
        logger.error("[D7] CRON_API_KEY nao configurada no servidor")
        return jsonify({'error': 'Servico nao configurado'}), 500

    request_key = request.headers.get('X-Cron-Key', '')
    if not hmac.compare_digest(request_key, cron_key):
        logger.warning("[D7] Tentativa com chave invalida")
        return jsonify({'error': 'Nao autorizado'}), 401

    # ── Parse body ──
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Body JSON obrigatorio'}), 400

    required = ['report_date', 'report_json', 'report_markdown']
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({'error': f'Campos obrigatorios ausentes: {missing}'}), 400

    try:
        from datetime import date as date_type
        report_date = date_type.fromisoformat(data['report_date'])
    except (ValueError, TypeError):
        return jsonify({'error': 'report_date deve ser formato YYYY-MM-DD'}), 400

    # ── Validar campos numericos ──
    try:
        health_score = float(data.get('health_score', 0))
        friction_score = float(data.get('friction_score', 0))
        recommendation_count = int(data.get('recommendation_count', 0))
        sessions_analyzed = int(data.get('sessions_analyzed', 0))
    except (ValueError, TypeError) as e:
        return jsonify({'error': f'Campos numericos invalidos: {e}'}), 400

    # Backlog: cron D7 ja fez merge + auto-escalate — server persiste como esta
    backlog = data.get('backlog_json', [])
    if not isinstance(backlog, list):
        backlog = []

    # ── Upsert ──
    try:
        from app.agente.models import AgentIntelligenceReport

        report = AgentIntelligenceReport.upsert(
            report_date=report_date,
            health_score=health_score,
            friction_score=friction_score,
            recommendation_count=recommendation_count,
            sessions_analyzed=sessions_analyzed,
            report_json=data['report_json'],
            report_markdown=data['report_markdown'],
            backlog_json=backlog,
        )

        db.session.flush()
        db.session.commit()

        logger.info(
            f"[D7] Relatorio {report_date} salvo: "
            f"score={report.health_score}, recs={report.recommendation_count}, "
            f"sessoes={report.sessions_analyzed}, backlog={len(backlog)}"
        )

        return jsonify({
            'status': 'ok',
            'report_id': report.id,
            'report_date': str(report.report_date),
            'backlog_items': len(backlog),
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"[D7] Erro ao salvar relatorio: {e}")
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500


# TODO: wire no insights dashboard — endpoint pronto para consumo futuro
@agente_bp.route('/api/intelligence-report/latest', methods=['GET'])
@login_required
def get_latest_intelligence_report():
    """
    Retorna o relatorio de inteligencia mais recente.

    GET /agente/api/intelligence-report/latest
    Query params:
        format: json (default) | markdown

    Usado pelo dashboard de insights e para consulta direta.
    """
    try:
        from app.agente.models import AgentIntelligenceReport

        report = AgentIntelligenceReport.get_latest()
        if not report:
            return jsonify({'error': 'Nenhum relatorio disponivel'}), 404

        fmt = request.args.get('format', 'json')
        if fmt == 'markdown':
            return Response(report.report_markdown, mimetype='text/markdown')

        return jsonify({
            'report_date': str(report.report_date),
            'health_score': float(report.health_score or 0),
            'friction_score': float(report.friction_score or 0),
            'recommendation_count': report.recommendation_count,
            'sessions_analyzed': report.sessions_analyzed,
            'report_json': report.report_json,
            'backlog_json': report.backlog_json,
            'created_at': report.created_at.isoformat() if report.created_at else None,
            'updated_at': report.updated_at.isoformat() if report.updated_at else None,
        })

    except Exception as e:
        logger.error(f"[D7] Erro ao buscar relatorio: {e}")
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500
