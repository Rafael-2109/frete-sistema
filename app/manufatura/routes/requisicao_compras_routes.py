"""
Rotas de Requisição de Compras
"""
from flask import render_template, jsonify, request
from flask_login import login_required, current_user
from app import db
from app.manufatura.models import RequisicaoCompras, PedidoCompras
from datetime import datetime


def register_requisicao_compras_routes(bp):
    
    @bp.route('/requisicoes-compras')
    @login_required
    def requisicoes_compras():
        """Tela de gestão de requisições de compras"""
        return render_template('manufatura/requisicoes_compras.html')
    
    @bp.route('/api/requisicoes-compras/necessidades')
    @login_required
    def listar_necessidades():
        """Lista necessidades de compras (To-Do list)"""
        try:
            # Busca requisições com necessidade=True e sem pedido criado
            necessidades = RequisicaoCompras.query.filter_by(
                necessidade=True,
                status='Pendente'
            ).order_by(RequisicaoCompras.data_necessidade).all()
            
            return jsonify([{
                'id': n.id,
                'cod_produto': n.cod_produto,
                'nome_produto': n.nome_produto,
                'qtd_produto_requisicao': float(n.qtd_produto_requisicao or 0),
                'qtd_produto_sem_requisicao': float(n.qtd_produto_sem_requisicao or 0),
                'data_necessidade': n.data_necessidade.strftime('%Y-%m-%d') if n.data_necessidade else None,
                'lead_time_previsto': n.lead_time_previsto,
                'urgente': (n.data_necessidade - datetime.now().date()).days <= 7 if n.data_necessidade else False
            } for n in necessidades])
            
        except Exception as e:
            return jsonify({'erro': str(e)}), 500
    
    @bp.route('/api/requisicoes-compras/listar')
    @login_required
    def listar_requisicoes():
        """Lista requisições de compras"""
        try:
            status = request.args.get('status')
            
            query = RequisicaoCompras.query
            if status:
                query = query.filter_by(status=status)
            
            requisicoes = query.order_by(RequisicaoCompras.data_requisicao_criacao.desc()).all()
            
            return jsonify([{
                'id': r.id,
                'num_requisicao': r.num_requisicao,
                'data_requisicao_criacao': r.data_requisicao_criacao.strftime('%Y-%m-%d') if r.data_requisicao_criacao else None,
                'cod_produto': r.cod_produto,
                'nome_produto': r.nome_produto,
                'qtd_produto_requisicao': float(r.qtd_produto_requisicao or 0),
                'status': r.status,
                'importado_odoo': r.importado_odoo,
                'tem_pedido': bool(r.pedidos)
            } for r in requisicoes])
            
        except Exception as e:
            return jsonify({'erro': str(e)}), 500
    
    @bp.route('/api/requisicoes-compras/<int:id>/marcar-criada-odoo', methods=['POST'])
    @login_required
    def marcar_criada_odoo(id):
        """Marca uma necessidade como requisição criada no Odoo"""
        try:
            requisicao = RequisicaoCompras.query.get_or_404(id)
            
            requisicao.status = 'Requisitada'
            requisicao.usuario_requisicao_criacao = current_user.username if current_user.is_authenticated else 'PCP'
            requisicao.data_requisicao_criacao = datetime.now().date()
            
            db.session.commit()
            
            return jsonify({'sucesso': True, 'mensagem': 'Requisição marcada como criada no Odoo'})
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 500
    
    @bp.route('/api/pedidos-compras/listar')
    @login_required
    def listar_pedidos():
        """Lista pedidos de compras"""
        try:
            confirmado = request.args.get('confirmado', type=bool)
            
            query = PedidoCompras.query
            if confirmado is not None:
                query = query.filter_by(confirmacao_pedido=confirmado)
            
            pedidos = query.order_by(PedidoCompras.data_pedido_criacao.desc()).all()
            
            return jsonify([{
                'id': p.id,
                'num_pedido': p.num_pedido,
                'num_requisicao': p.num_requisicao,
                'cnpj_fornecedor': p.cnpj_fornecedor,
                'raz_social': p.raz_social,
                'cod_produto': p.cod_produto,
                'nome_produto': p.nome_produto,
                'qtd_produto_pedido': float(p.qtd_produto_pedido or 0),
                'preco_produto_pedido': float(p.preco_produto_pedido or 0),
                'data_pedido_previsao': p.data_pedido_previsao.strftime('%Y-%m-%d') if p.data_pedido_previsao else None,
                'confirmacao_pedido': p.confirmacao_pedido,
                'importado_odoo': p.importado_odoo
            } for p in pedidos])
            
        except Exception as e:
            return jsonify({'erro': str(e)}), 500