"""
Dashboard Routes — Seguranca
"""

from flask import render_template
from flask_login import login_required, current_user
from app.utils.auth_decorators import require_seguranca


def register_dashboard_routes(bp):

    @bp.route('/')
    @login_required
    @require_seguranca()
    def dashboard():
        """Dashboard de seguranca com score empresa e top riscos"""
        from app.seguranca.models import (
            SegurancaVulnerabilidade, SegurancaScore, SegurancaVarredura
        )
        from app.seguranca.services.score_service import calcular_score_empresa
        from app.auth.models import Usuario

        # Score da empresa (ultimo calculado ou calcula agora)
        ultimo_score = SegurancaScore.query.filter_by(
            user_id=None
        ).order_by(SegurancaScore.calculado_em.desc()).first()

        if ultimo_score:
            score_empresa = {
                'score': ultimo_score.score,
                'componentes': ultimo_score.componentes or {},
                'vulnerabilidades_abertas': ultimo_score.vulnerabilidades_abertas,
                'vulnerabilidades_criticas': ultimo_score.vulnerabilidades_criticas,
            }
        else:
            score_empresa = {
                'score': 100,
                'componentes': {
                    'email_breach': 100,
                    'password_health': 100,
                    'domain': 100,
                    'remediacao': 100,
                },
                'vulnerabilidades_abertas': 0,
                'vulnerabilidades_criticas': 0,
            }

        # Contadores por severidade
        stats_severidade = {}
        for sev in ['CRITICA', 'ALTA', 'MEDIA', 'BAIXA', 'INFO']:
            stats_severidade[sev] = SegurancaVulnerabilidade.query.filter_by(
                severidade=sev,
            ).filter(
                SegurancaVulnerabilidade.status.in_(['ABERTA', 'EM_ANDAMENTO'])
            ).count()

        # Top 5 vulnerabilidades mais criticas
        top_vulnerabilidades = SegurancaVulnerabilidade.query.filter(
            SegurancaVulnerabilidade.status.in_(['ABERTA', 'EM_ANDAMENTO'])
        ).order_by(
            # Ordenar por severidade (CRITICA primeiro)
            db_case_severidade(),
            SegurancaVulnerabilidade.criado_em.desc()
        ).limit(10).all()

        # Ultima varredura
        ultima_varredura = SegurancaVarredura.query.order_by(
            SegurancaVarredura.iniciado_em.desc()
        ).first()

        # Total de usuarios ativos
        total_usuarios = Usuario.query.filter_by(status='ativo').count()

        return render_template(
            'seguranca/dashboard.html',
            score_empresa=score_empresa,
            stats_severidade=stats_severidade,
            top_vulnerabilidades=top_vulnerabilidades,
            ultima_varredura=ultima_varredura,
            total_usuarios=total_usuarios,
        )

    @bp.route('/verificar-senha')
    @login_required
    @require_seguranca()
    def verificar_senha():
        """Pagina self-check de senhas (resultado NAO persistido)"""
        return render_template('seguranca/verificar_senha.html')


def db_case_severidade():
    """Helper para ORDER BY severidade"""
    from sqlalchemy import case
    from app.seguranca.models import SegurancaVulnerabilidade

    return case(
        (SegurancaVulnerabilidade.severidade == 'CRITICA', 0),
        (SegurancaVulnerabilidade.severidade == 'ALTA', 1),
        (SegurancaVulnerabilidade.severidade == 'MEDIA', 2),
        (SegurancaVulnerabilidade.severidade == 'BAIXA', 3),
        (SegurancaVulnerabilidade.severidade == 'INFO', 4),
        else_=5,
    )
