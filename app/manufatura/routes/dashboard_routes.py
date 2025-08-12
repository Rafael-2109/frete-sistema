"""
Rotas do Dashboard do módulo de Manufatura
"""
from flask import render_template, jsonify
from flask_login import login_required
from app import db
from app.manufatura.services.dashboard_service import DashboardService
from datetime import datetime


def register_dashboard_routes(bp):
    
    @bp.route('/')
    @bp.route('/dashboard')
    @login_required
    def dashboard():
        """Tela principal do módulo de manufatura"""
        return render_template('manufatura/dashboard.html')
    
    @bp.route('/master')
    @login_required
    def master():
        """Central de controle master do módulo de manufatura"""
        from datetime import date
        anos_disponiveis = list(range(date.today().year - 1, date.today().year + 2))
        return render_template('manufatura/master.html',
                             anos_disponiveis=anos_disponiveis,
                             mes_atual=date.today().month,
                             ano_atual=date.today().year)
    
    @bp.route('/api/dashboard/metricas')
    @login_required
    def dashboard_metricas():
        """API para métricas do dashboard"""
        try:
            service = DashboardService()
            metricas = service.obter_metricas()
            return jsonify(metricas)
        except Exception as e:
            return jsonify({'erro': str(e)}), 500
    
    @bp.route('/api/dashboard/ordens-abertas')
    @login_required
    def dashboard_ordens_abertas():
        """API para ordens de produção abertas"""
        try:
            service = DashboardService()
            ordens = service.obter_ordens_abertas()
            return jsonify(ordens)
        except Exception as e:
            return jsonify({'erro': str(e)}), 500
    
    @bp.route('/api/dashboard/necessidades-compras')
    @login_required
    def dashboard_necessidades():
        """API para necessidades de compras"""
        try:
            service = DashboardService()
            necessidades = service.obter_necessidades_compras()
            return jsonify(necessidades)
        except Exception as e:
            return jsonify({'erro': str(e)}), 500
    
    @bp.route('/api/dashboard/alertas')
    @login_required
    def dashboard_alertas():
        """API para alertas do sistema"""
        try:
            service = DashboardService()
            alertas = service.obter_alertas() if hasattr(service, 'obter_alertas') else {'alertas': []}
            return jsonify(alertas)
        except Exception as e:
            return jsonify({'erro': str(e)}), 500