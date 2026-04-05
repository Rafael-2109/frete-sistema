"""Rotas do dashboard pessoal — KPIs, graficos e tabela resumo."""
from datetime import date

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user

from app.pessoal import pode_acessar_pessoal
from app.pessoal.services.dashboard_service import (
    calcular_resumo_mensal, gastos_por_categoria, tendencia_mensal,
)

dashboard_bp = Blueprint('pessoal_dashboard', __name__)


def _parse_mes(mes_str):
    """Extrai (ano, mes) de 'YYYY-MM'. Fallback: mes atual."""
    try:
        partes = mes_str.split('-')
        return int(partes[0]), int(partes[1])
    except (ValueError, IndexError, AttributeError):
        hoje = date.today()
        return hoje.year, hoje.month


@dashboard_bp.route('/dashboard')
@login_required
def index():
    """Pagina principal do dashboard pessoal."""
    if not pode_acessar_pessoal(current_user):
        return 'Acesso restrito.', 403

    return render_template('pessoal/dashboard.html')


@dashboard_bp.route('/api/dashboard/resumo')
@login_required
def api_resumo():
    """KPIs do mes selecionado."""
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False}), 403

    ano, mes = _parse_mes(request.args.get('mes'))
    resumo = calcular_resumo_mensal(ano, mes)
    return jsonify({'sucesso': True, **resumo})


@dashboard_bp.route('/api/dashboard/categorias')
@login_required
def api_categorias():
    """Gastos por categoria do mes selecionado."""
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False}), 403

    ano, mes = _parse_mes(request.args.get('mes'))
    categorias = gastos_por_categoria(ano, mes)
    return jsonify({'sucesso': True, 'categorias': categorias})


@dashboard_bp.route('/api/dashboard/tendencia')
@login_required
def api_tendencia():
    """Tendencia mensal dos ultimos N meses."""
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False}), 403

    n_meses = request.args.get('meses', 6, type=int)
    if n_meses < 2:
        n_meses = 2
    elif n_meses > 12:
        n_meses = 12
    dados = tendencia_mensal(n_meses)
    return jsonify({'sucesso': True, 'tendencia': dados})
