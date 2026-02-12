"""
Rotas do Dashboard de Métricas
==============================

Exibe métricas básicas do sistema:
- Total de pedidos no mês atual
- Total de separações pendentes (sincronizado_nf=False)
- Total de embarques do mês atual

Autor: Sistema de Fretes
Data: 2026-01-25
"""

from datetime import datetime
from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy import extract

from app import db
from app.carteira.models import CarteiraPrincipal
from app.separacao.models import Separacao
from app.embarques.models import Embarque
from app.utils.timezone import agora_utc_naive

metricas_bp = Blueprint('metricas', __name__, url_prefix='/metricas')


@metricas_bp.route('/')
@metricas_bp.route('/dashboard')
@login_required
def dashboard_metricas():
    """
    Dashboard de métricas básicas do sistema.

    Exibe 3 cards com:
    1. Total de pedidos no mês atual (CarteiraPrincipal)
    2. Total de separações pendentes (sincronizado_nf=False)
    3. Total de embarques do mês atual

    Consultas otimizadas com máximo de 3 queries SQL.
    """
    # Data atual para filtros
    agora = agora_utc_naive()
    mes_atual = agora.month
    ano_atual = agora.year

    try:
        # Query 1: Pedidos do mês atual
        total_pedidos_mes = CarteiraPrincipal.query.filter(
            extract('month', CarteiraPrincipal.data_pedido) == mes_atual,
            extract('year', CarteiraPrincipal.data_pedido) == ano_atual
        ).count()
    except Exception as e:
        total_pedidos_mes = 0
        db.session.rollback()

    try:
        # Query 2: Separações pendentes (sincronizado_nf=False)
        # Conforme CLAUDE.md: sincronizado_nf=False = item aparece na carteira e projeta estoque
        total_separacoes_pendentes = Separacao.query.filter_by(
            sincronizado_nf=False
        ).count()
    except Exception as e:
        total_separacoes_pendentes = 0
        db.session.rollback()

    try:
        # Query 3: Embarques do mês atual
        total_embarques_mes = Embarque.query.filter(
            extract('month', Embarque.data_embarque) == mes_atual,
            extract('year', Embarque.data_embarque) == ano_atual
        ).count()
    except Exception as e:
        total_embarques_mes = 0
        db.session.rollback()

    # Dados para o template
    metricas = {
        'pedidos_mes': total_pedidos_mes,
        'separacoes_pendentes': total_separacoes_pendentes,
        'embarques_mes': total_embarques_mes,
        'mes_referencia': agora.strftime('%B/%Y').capitalize(),
        'data_atualizacao': agora.strftime('%d/%m/%Y %H:%M')
    }

    return render_template('metricas/dashboard.html', metricas=metricas)
