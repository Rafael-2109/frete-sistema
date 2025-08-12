"""
Rotas de Integração com Odoo
"""
from flask import render_template, jsonify, request
from flask_login import login_required
from app.manufatura.models import LogIntegracao


def register_integracao_routes(bp):
    
    @bp.route('/integracao')
    @login_required
    def integracao():
        """Tela de gestão de integrações"""
        return render_template('manufatura/integracao.html')
    
    @bp.route('/api/integracao/requisicoes/importar', methods=['POST'])
    @login_required
    def importar_requisicoes():
        """Importa requisições de compras do Odoo"""
        try:
            # Import tardio para evitar circular import
            from app.odoo.services.manufatura_service import ManufaturaOdooService
            
            service = ManufaturaOdooService()
            resultado = service.importar_requisicoes_compras()
            
            return jsonify(resultado)
            
        except Exception as e:
            return jsonify({'erro': str(e)}), 500
    
    @bp.route('/api/integracao/pedidos/importar', methods=['POST'])
    @login_required
    def importar_pedidos():
        """Importa pedidos de compras do Odoo"""
        try:
            # Import tardio para evitar circular import
            from app.odoo.services.manufatura_service import ManufaturaOdooService
            
            service = ManufaturaOdooService()
            resultado = service.importar_pedidos_compras()
            
            return jsonify(resultado)
            
        except Exception as e:
            return jsonify({'erro': str(e)}), 500
    
    @bp.route('/api/integracao/producao/sincronizar', methods=['POST'])
    @login_required
    def sincronizar_producao():
        """Sincroniza ordens de produção com Odoo"""
        try:
            # Import tardio para evitar circular import
            from app.odoo.services.manufatura_service import ManufaturaOdooService
            
            service = ManufaturaOdooService()
            resultado = service.sincronizar_producao()
            
            return jsonify(resultado)
            
        except Exception as e:
            return jsonify({'erro': str(e)}), 500
    
    @bp.route('/api/integracao/historico/importar', methods=['POST'])
    @login_required
    def importar_historico():
        """Importa histórico de pedidos do Odoo"""
        try:
            # Import tardio para evitar circular import
            from app.odoo.services.manufatura_service import ManufaturaOdooService
            
            dados = request.json if request.is_json else request.form
            mes = dados.get('mes', type=int) if dados else None
            ano = dados.get('ano', type=int) if dados else None
            
            service = ManufaturaOdooService()
            resultado = service.importar_historico_pedidos(mes, ano)
            
            return jsonify(resultado)
            
        except Exception as e:
            return jsonify({'erro': str(e)}), 500
    
    @bp.route('/api/integracao/logs')
    @login_required
    def listar_logs():
        """Lista logs de integração"""
        try:
            limite = request.args.get('limite', 50, type=int)
            tipo = request.args.get('tipo')
            
            query = LogIntegracao.query
            
            if tipo:
                query = query.filter(LogIntegracao.tipo_integracao.like(f'%{tipo}%'))
            
            logs = query.order_by(LogIntegracao.data_execucao.desc()).limit(limite).all()
            
            return jsonify([{
                'id': log.id,
                'tipo': log.tipo_integracao,
                'status': log.status,
                'mensagem': log.mensagem,
                'processados': log.registros_processados,
                'erros': log.registros_erro,
                'data': log.data_execucao.strftime('%d/%m/%Y %H:%M:%S') if log.data_execucao else None,
                'tempo': log.tempo_execucao
            } for log in logs])
            
        except Exception as e:
            return jsonify({'erro': str(e)}), 500