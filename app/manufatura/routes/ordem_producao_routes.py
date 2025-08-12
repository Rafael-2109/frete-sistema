"""
Rotas de Ordens de Produção
"""
from flask import render_template, jsonify, request
from flask_login import login_required, current_user
from app import db
from app.manufatura.models import OrdemProducao, ListaMateriais
from datetime import datetime


def register_ordem_producao_routes(bp):
    
    @bp.route('/ordens-producao')
    @login_required
    def ordens_producao():
        """Tela de gestão de ordens de produção"""
        return render_template('manufatura/ordens_producao.html')
    
    @bp.route('/api/ordens-producao/listar')
    @login_required
    def listar_ordens():
        """Lista ordens de produção"""
        try:
            status = request.args.get('status')
            
            query = OrdemProducao.query
            if status:
                query = query.filter_by(status=status)
            
            ordens = query.order_by(OrdemProducao.data_inicio_prevista.desc()).all()
            
            return jsonify([{
                'id': o.id,
                'numero_ordem': o.numero_ordem,
                'origem_ordem': o.origem_ordem,
                'status': o.status,
                'cod_produto': o.cod_produto,
                'nome_produto': o.nome_produto,
                'qtd_planejada': float(o.qtd_planejada or 0),
                'qtd_produzida': float(o.qtd_produzida or 0),
                'data_inicio_prevista': o.data_inicio_prevista.strftime('%Y-%m-%d') if o.data_inicio_prevista else None,
                'data_fim_prevista': o.data_fim_prevista.strftime('%Y-%m-%d') if o.data_fim_prevista else None,
                'linha_producao': o.linha_producao,
                # Campos MTO
                'separacao_lote_id': o.separacao_lote_id,
                'num_pedido_origem': o.num_pedido_origem,
                'raz_social_red': o.raz_social_red,
                'qtd_pedido_atual': float(o.qtd_pedido_atual or 0) if o.qtd_pedido_atual else None
            } for o in ordens])
            
        except Exception as e:
            return jsonify({'erro': str(e)}), 500
    
    @bp.route('/api/ordens-producao/<int:id>')
    @login_required
    def obter_ordem(id):
        """Obtém detalhes de uma ordem de produção"""
        try:
            ordem = OrdemProducao.query.get_or_404(id)
            
            return jsonify({
                'id': ordem.id,
                'numero_ordem': ordem.numero_ordem,
                'origem_ordem': ordem.origem_ordem,
                'status': ordem.status,
                'cod_produto': ordem.cod_produto,
                'nome_produto': ordem.nome_produto,
                'materiais_necessarios': ordem.materiais_necessarios,
                'qtd_planejada': float(ordem.qtd_planejada or 0),
                'qtd_produzida': float(ordem.qtd_produzida or 0),
                'data_inicio_prevista': ordem.data_inicio_prevista.strftime('%Y-%m-%d') if ordem.data_inicio_prevista else None,
                'data_fim_prevista': ordem.data_fim_prevista.strftime('%Y-%m-%d') if ordem.data_fim_prevista else None,
                'data_inicio_real': ordem.data_inicio_real.strftime('%Y-%m-%d') if ordem.data_inicio_real else None,
                'data_fim_real': ordem.data_fim_real.strftime('%Y-%m-%d') if ordem.data_fim_real else None,
                'linha_producao': ordem.linha_producao,
                'turno': ordem.turno,
                'lote_producao': ordem.lote_producao,
                'custo_previsto': float(ordem.custo_previsto or 0),
                'custo_real': float(ordem.custo_real or 0),
                # Campos MTO
                'separacao_lote_id': ordem.separacao_lote_id,
                'num_pedido_origem': ordem.num_pedido_origem,
                'raz_social_red': ordem.raz_social_red,
                'qtd_pedido_atual': float(ordem.qtd_pedido_atual or 0) if ordem.qtd_pedido_atual else None
            })
            
        except Exception as e:
            return jsonify({'erro': str(e)}), 500
    
    @bp.route('/api/ordens-producao/<int:id>/atualizar-status', methods=['POST'])
    @login_required
    def atualizar_status_ordem(id):
        """Atualiza status de uma ordem de produção"""
        try:
            ordem = OrdemProducao.query.get_or_404(id)
            dados = request.json
            
            novo_status = dados.get('status')
            if novo_status not in ['Planejada', 'Liberada', 'Em Produção', 'Concluída', 'Cancelada']:
                return jsonify({'erro': 'Status inválido'}), 400
            
            ordem.status = novo_status
            
            # Se iniciando produção, registra data de início
            if novo_status == 'Em Produção' and not ordem.data_inicio_real:
                ordem.data_inicio_real = datetime.now().date()
            
            # Se concluindo, registra data de fim
            if novo_status == 'Concluída' and not ordem.data_fim_real:
                ordem.data_fim_real = datetime.now().date()
            
            db.session.commit()
            
            return jsonify({'sucesso': True, 'novo_status': ordem.status})
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 500
    
    @bp.route('/api/ordens-producao/criar', methods=['POST'])
    @login_required
    def criar_ordem():
        """Cria nova ordem de produção"""
        try:
            from app.manufatura.services.ordem_producao_service import OrdemProducaoService
            
            dados = request.json
            dados['criado_por'] = current_user.username if current_user.is_authenticated else 'Sistema'
            
            service = OrdemProducaoService()
            ordem = service.criar_ordem(dados)
            
            return jsonify({
                'sucesso': True,
                'id': ordem.id,
                'numero_ordem': ordem.numero_ordem
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 500
    
    @bp.route('/api/ordens-producao/gerar-mto', methods=['POST'])
    @login_required
    def gerar_ordens_mto():
        """Gera ordens MTO automaticamente"""
        try:
            from app.manufatura.services.ordem_producao_service import OrdemProducaoService
            
            service = OrdemProducaoService()
            ordens = service.gerar_ordens_mto_automaticas()
            
            return jsonify({
                'sucesso': True,
                'mensagem': f'{len(ordens)} ordens MTO criadas automaticamente'
            })
            
        except Exception as e:
            return jsonify({'erro': str(e)}), 500
    
    @bp.route('/sequenciamento')
    @login_required
    def sequenciamento():
        """Tela de sequenciamento de produção"""
        return render_template('manufatura/sequenciamento.html')
    
    @bp.route('/api/sequenciamento/calcular')
    @login_required
    def calcular_sequenciamento():
        """Calcula sequenciamento de ordens"""
        try:
            from app.manufatura.services.ordem_producao_service import OrdemProducaoService
            from datetime import datetime, timedelta
            
            linha = request.args.get('linha_producao')
            data_inicio = request.args.get('data_inicio', datetime.now().date())
            data_fim = request.args.get('data_fim', (datetime.now() + timedelta(days=7)).date())
            
            if isinstance(data_inicio, str):
                data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            if isinstance(data_fim, str):
                data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
            
            service = OrdemProducaoService()
            sequencia = service.sequenciar_ordens(linha, data_inicio, data_fim)
            
            return jsonify(sequencia)
            
        except Exception as e:
            return jsonify({'erro': str(e)}), 500
    
    @bp.route('/api/ordens-producao/<int:id>/validar-mto')
    @login_required
    def validar_quantidade_mto(id):
        """Valida quantidade MTO de uma ordem"""
        try:
            from app.manufatura.services.ordem_producao_service import OrdemProducaoService
            
            service = OrdemProducaoService()
            resultado = service.validar_quantidade_mto(id)
            
            return jsonify(resultado)
            
        except Exception as e:
            return jsonify({'erro': str(e)}), 500