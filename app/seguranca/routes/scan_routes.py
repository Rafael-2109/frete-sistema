"""
Scan Routes — Disparar varredura e historico
"""

from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.utils.auth_decorators import require_seguranca


def register_scan_routes(bp):

    @bp.route('/varredura/executar', methods=['POST'])
    @login_required
    @require_seguranca()
    def executar_varredura():
        """Dispara varredura manual"""
        from app.seguranca.services.scan_orchestrator import executar_varredura as _executar

        tipo = request.form.get('tipo', 'FULL_SCAN')
        if tipo not in ('FULL_SCAN', 'EMAIL_BREACH', 'DOMAIN_EXPOSURE'):
            tipo = 'FULL_SCAN'

        resultado = _executar(
            tipo=tipo,
            disparado_por=current_user.email,
        )

        if resultado['sucesso']:
            flash(
                f'Varredura concluida! '
                f'{resultado["total_verificados"]} verificados, '
                f'{resultado["total_vulnerabilidades"]} vulnerabilidades encontradas.',
                'success'
            )
        else:
            flash(
                f'Erro na varredura: {resultado.get("erro", "Erro desconhecido")}',
                'danger'
            )

        return redirect(url_for('seguranca.dashboard'))

    @bp.route('/varreduras')
    @login_required
    @require_seguranca()
    def listar_varreduras():
        """Historico de varreduras"""
        from app.seguranca.models import SegurancaVarredura

        varreduras = SegurancaVarredura.query.order_by(
            SegurancaVarredura.iniciado_em.desc()
        ).limit(50).all()

        return render_template(
            'seguranca/varreduras/listar.html',
            varreduras=varreduras,
        )

    @bp.route('/varreduras/<int:varredura_id>')
    @login_required
    @require_seguranca()
    def detalhe_varredura(varredura_id):
        """Detalhe de uma varredura"""
        from app.seguranca.models import SegurancaVarredura

        varredura = SegurancaVarredura.query.get_or_404(varredura_id)

        return render_template(
            'seguranca/varreduras/detalhe.html',
            varredura=varredura,
        )
