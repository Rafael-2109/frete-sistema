"""
Rotas Gerenciais CarVia — Metricas analiticas (admin-only)
==========================================================

Tela com valor por UF/mes, valor por unidade (moto), valor por kg cubado.
"""

import logging
from datetime import date

from flask import render_template, request
from flask_login import login_required, current_user

from app.utils.auth_decorators import require_admin

logger = logging.getLogger(__name__)


def register_gerencial_routes(bp):

    @bp.route('/gerencial')  # type: ignore
    @login_required
    @require_admin
    def gerencial():  # type: ignore
        """Tela gerencial — metricas agregadas por UF/mes"""
        if not getattr(current_user, 'sistema_carvia', False):
            from flask import flash, redirect, url_for
            flash('Acesso negado. Voce nao tem permissao para o sistema CarVia.', 'danger')
            return redirect(url_for('main.dashboard'))

        from app.carvia.services.gerencial_service import GerencialService
        from app.utils.timezone import agora_brasil_naive

        hoje = agora_brasil_naive().date()

        # Defaults: mes atual
        data_inicio_str = request.args.get('data_inicio')
        data_fim_str = request.args.get('data_fim')

        try:
            data_inicio = (
                date.fromisoformat(data_inicio_str)
                if data_inicio_str
                else hoje.replace(day=1)
            )
        except ValueError:
            data_inicio = hoje.replace(day=1)

        try:
            data_fim = (
                date.fromisoformat(data_fim_str)
                if data_fim_str
                else hoje
            )
        except ValueError:
            data_fim = hoje

        service = GerencialService()

        try:
            metricas = service.obter_metricas_por_uf_mes(data_inicio, data_fim)
            totais = service.obter_totais_periodo(data_inicio, data_fim)
        except Exception as e:
            logger.error(f"Erro ao carregar metricas gerenciais CarVia: {e}")
            metricas = []
            totais = {
                'valor_total': 0,
                'qtd_motos': 0,
                'peso_efetivo': 0,
                'valor_por_unidade': None,
                'valor_por_kg_cubado': None,
                'total_despesas': 0,
            }

        return render_template(
            'carvia/gerencial.html',
            metricas=metricas,
            totais=totais,
            data_inicio=data_inicio.isoformat(),
            data_fim=data_fim.isoformat(),
        )
