"""
Vulnerabilidade Routes — CRUD + Remediacao
"""

from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.utils.auth_decorators import require_seguranca
from app.utils.timezone import agora_utc_naive
from app import db


def register_vulnerabilidade_routes(bp):

    @bp.route('/vulnerabilidades')
    @login_required
    @require_seguranca()
    def listar_vulnerabilidades():
        """Lista todas as vulnerabilidades com filtros"""
        from app.seguranca.models import SegurancaVulnerabilidade
        from app.auth.models import Usuario

        # Filtros
        filtro_status = request.args.get('status', 'ABERTA')
        filtro_categoria = request.args.get('categoria', '')
        filtro_severidade = request.args.get('severidade', '')
        filtro_usuario = request.args.get('user_id', '', type=str)

        query = SegurancaVulnerabilidade.query

        if filtro_status and filtro_status != 'TODAS':
            query = query.filter_by(status=filtro_status)
        if filtro_categoria:
            query = query.filter_by(categoria=filtro_categoria)
        if filtro_severidade:
            query = query.filter_by(severidade=filtro_severidade)
        if filtro_usuario:
            query = query.filter_by(user_id=int(filtro_usuario))

        vulnerabilidades = query.order_by(
            SegurancaVulnerabilidade.criado_em.desc()
        ).all()

        usuarios = Usuario.query.filter_by(status='ativo').order_by(
            Usuario.nome
        ).all()

        return render_template(
            'seguranca/vulnerabilidades/listar.html',
            vulnerabilidades=vulnerabilidades,
            usuarios=usuarios,
            filtro_status=filtro_status,
            filtro_categoria=filtro_categoria,
            filtro_severidade=filtro_severidade,
            filtro_usuario=filtro_usuario,
        )

    @bp.route('/vulnerabilidades/<int:vuln_id>')
    @login_required
    @require_seguranca()
    def detalhe_vulnerabilidade(vuln_id):
        """Detalhe de uma vulnerabilidade"""
        from app.seguranca.models import SegurancaVulnerabilidade

        vuln = SegurancaVulnerabilidade.query.get_or_404(vuln_id)

        return render_template(
            'seguranca/vulnerabilidades/detalhe.html',
            vuln=vuln,
        )

    @bp.route('/vulnerabilidades/<int:vuln_id>/remediar', methods=['POST'])
    @login_required
    @require_seguranca()
    def remediar_vulnerabilidade(vuln_id):
        """Atualiza status de remediacao"""
        from app.seguranca.models import SegurancaVulnerabilidade

        vuln = SegurancaVulnerabilidade.query.get_or_404(vuln_id)

        novo_status = request.form.get('status')
        if novo_status not in (
            'ABERTA', 'EM_ANDAMENTO', 'RESOLVIDA', 'ACEITA', 'FALSO_POSITIVO'
        ):
            flash('Status invalido.', 'danger')
            return redirect(url_for('seguranca.detalhe_vulnerabilidade', vuln_id=vuln_id))

        vuln.status = novo_status
        vuln.atualizado_em = agora_utc_naive()
        db.session.commit()

        # Recalcular score do usuario
        try:
            from app.seguranca.services.score_service import calcular_score_usuario
            calcular_score_usuario(vuln.user_id)
            db.session.commit()
        except Exception:
            pass

        flash(f'Vulnerabilidade marcada como {novo_status}.', 'success')
        return redirect(url_for('seguranca.detalhe_vulnerabilidade', vuln_id=vuln_id))

    @bp.route('/usuario/<int:user_id>')
    @login_required
    @require_seguranca()
    def perfil_seguranca_usuario(user_id):
        """Perfil de seguranca de um colaborador"""
        from app.seguranca.models import SegurancaVulnerabilidade, SegurancaScore
        from app.auth.models import Usuario

        usuario = Usuario.query.get_or_404(user_id)

        vulns = SegurancaVulnerabilidade.query.filter_by(
            user_id=user_id
        ).order_by(
            SegurancaVulnerabilidade.criado_em.desc()
        ).all()

        ultimo_score = SegurancaScore.query.filter_by(
            user_id=user_id
        ).order_by(SegurancaScore.calculado_em.desc()).first()

        return render_template(
            'seguranca/usuario/perfil_seguranca.html',
            usuario=usuario,
            vulnerabilidades=vulns,
            score=ultimo_score,
        )
