"""
Config Routes — Configuracao do modulo de seguranca
"""

from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.utils.auth_decorators import require_seguranca
from app import db


def register_config_routes(bp):

    @bp.route('/configuracao', methods=['GET', 'POST'])
    @login_required
    @require_seguranca()
    def configuracao():
        """Pagina de configuracao do modulo"""
        from app.seguranca.models import SegurancaConfig

        if request.method == 'POST':
            campos = [
                'hibp_api_key', 'scan_interval_hours',
                'password_min_entropy', 'domains_to_monitor',
                'auto_scan_enabled',
            ]
            for campo in campos:
                valor = request.form.get(campo, '')
                SegurancaConfig.set_valor(
                    campo, valor, atualizado_por=current_user.email
                )

            db.session.commit()
            flash('Configuracoes salvas com sucesso.', 'success')
            return redirect(url_for('seguranca.configuracao'))

        # GET
        configs = {}
        for config in SegurancaConfig.query.all():
            configs[config.chave] = {
                'valor': config.valor,
                'descricao': config.descricao,
                'atualizado_em': config.atualizado_em,
                'atualizado_por': config.atualizado_por,
            }

        # Garantir defaults existem
        for chave, default in SegurancaConfig.DEFAULTS.items():
            if chave not in configs:
                configs[chave] = {
                    'valor': default['valor'],
                    'descricao': default['descricao'],
                    'atualizado_em': None,
                    'atualizado_por': None,
                }

        return render_template(
            'seguranca/configuracao.html',
            configs=configs,
        )
