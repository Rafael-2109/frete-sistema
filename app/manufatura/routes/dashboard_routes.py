"""
Rotas do Dashboard do módulo de Manufatura
"""
from flask import render_template, jsonify, request
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
    
    @bp.route('/api/dashboard/plano-mestre')
    @login_required
    def dashboard_plano_mestre():
        """API para resumo do plano mestre de produção"""
        try:
            mes = request.args.get('mes', datetime.now().month, type=int)
            ano = request.args.get('ano', datetime.now().year, type=int)
            
            service = DashboardService()
            plano_resumo = service.obter_plano_mestre_resumo(mes, ano)
            return jsonify(plano_resumo)
        except Exception as e:
            return jsonify({'erro': str(e)}), 500
    
    @bp.route('/api/dashboard/demanda-ativa')
    @login_required
    def dashboard_demanda_ativa():
        """API para demanda ativa consolidada"""
        try:
            from app.manufatura.services.demanda_service import DemandaService
            
            mes = request.args.get('mes', datetime.now().month, type=int)
            ano = request.args.get('ano', datetime.now().year, type=int)
            cod_produto = request.args.get('cod_produto')
            
            service = DemandaService()
            demanda = service.calcular_demanda_ativa(mes, ano, cod_produto)
            
            # Resumo agregado
            total_demanda = sum(d['qtd_demanda'] for d in demanda)
            
            return jsonify({
                'mes': mes,
                'ano': ano,
                'total_demanda': total_demanda,
                'total_produtos': len(demanda),
                'detalhes': demanda[:20]  # Limitar a 20 produtos
            })
        except Exception as e:
            return jsonify({'erro': str(e)}), 500