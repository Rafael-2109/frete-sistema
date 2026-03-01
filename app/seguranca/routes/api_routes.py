"""
API Routes — JSON endpoints para charts, DataTables, password check
"""

from flask import jsonify, request
from flask_login import login_required, current_user
from app.utils.auth_decorators import require_seguranca


def register_api_routes(bp):

    @bp.route('/api/scores/trend')
    @login_required
    @require_seguranca()
    def api_scores_trend():
        """Trend de scores da empresa para grafico"""
        from app.seguranca.models import SegurancaScore

        scores = SegurancaScore.query.filter_by(
            user_id=None  # Empresa
        ).order_by(
            SegurancaScore.calculado_em.asc()
        ).limit(30).all()

        data = {
            'labels': [
                s.calculado_em.strftime('%d/%m') if s.calculado_em else ''
                for s in scores
            ],
            'scores': [s.score for s in scores],
        }

        return jsonify(data)

    @bp.route('/api/vulnerabilidades/stats')
    @login_required
    @require_seguranca()
    def api_vulnerabilidades_stats():
        """Estatisticas de vulnerabilidades para charts"""
        from app.seguranca.models import SegurancaVulnerabilidade
        from sqlalchemy import func

        # Por categoria
        por_categoria = db_query_stats_por_campo(
            SegurancaVulnerabilidade, 'categoria'
        )

        # Por severidade
        por_severidade = db_query_stats_por_campo(
            SegurancaVulnerabilidade, 'severidade'
        )

        # Por status
        por_status = db_query_stats_por_campo(
            SegurancaVulnerabilidade, 'status'
        )

        return jsonify({
            'por_categoria': por_categoria,
            'por_severidade': por_severidade,
            'por_status': por_status,
        })

    @bp.route('/api/verificar-senha', methods=['POST'])
    @login_required
    @require_seguranca()
    def api_verificar_senha():
        """
        Verificacao AJAX de senha.
        SEGURANCA: Senha avaliada em memoria, NUNCA persistida.
        """
        from app.seguranca.services.password_health_service import avaliar_senha

        data = request.get_json(silent=True) or {}
        senha = data.get('senha', '')

        if not senha:
            return jsonify({'erro': 'Senha nao informada'}), 400

        resultado = avaliar_senha(senha, verificar_hibp=True)

        return jsonify(resultado)


def db_query_stats_por_campo(model, campo):
    """Helper para contar registros agrupados por campo"""
    from sqlalchemy import func
    from app import db

    resultados = db.session.query(
        getattr(model, campo),
        func.count(model.id)
    ).filter(
        model.status.in_(['ABERTA', 'EM_ANDAMENTO'])
    ).group_by(
        getattr(model, campo)
    ).all()

    return {str(r[0]): r[1] for r in resultados}
