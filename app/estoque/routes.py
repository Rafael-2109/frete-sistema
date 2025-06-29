from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.estoque.models import MovimentacaoEstoque
from app.utils.auth_decorators import require_admin

# 📦 Blueprint do estoque (seguindo padrão dos outros módulos)
estoque_bp = Blueprint('estoque', __name__, url_prefix='/estoque')

@estoque_bp.route('/')
@login_required
def index():
    """Dashboard do módulo estoque"""
    try:
        from sqlalchemy import func, extract
        from datetime import datetime
        
        # ✅ SEGURO: Verifica se tabela existe antes de fazer query
        if db.engine.has_table('movimentacao_estoque'):
            total_movimentacoes = MovimentacaoEstoque.query.count()
            
            # Movimentações do mês atual
            mes_atual = datetime.now().month
            ano_atual = datetime.now().year
            
            entradas_mes = MovimentacaoEstoque.query.filter(
                MovimentacaoEstoque.tipo_movimentacao.ilike('%entrada%'),
                extract('month', MovimentacaoEstoque.data_movimentacao) == mes_atual,
                extract('year', MovimentacaoEstoque.data_movimentacao) == ano_atual
            ).count()
            
            saidas_mes = MovimentacaoEstoque.query.filter(
                MovimentacaoEstoque.tipo_movimentacao.ilike('%saida%'),
                extract('month', MovimentacaoEstoque.data_movimentacao) == mes_atual,
                extract('year', MovimentacaoEstoque.data_movimentacao) == ano_atual
            ).count()
            
            # Produtos únicos movimentados
            produtos_movimentados = MovimentacaoEstoque.query.with_entities(
                MovimentacaoEstoque.cod_produto
            ).distinct().count()
            
            # Locais únicos de movimentação
            locais_movimentacao = MovimentacaoEstoque.query.with_entities(
                MovimentacaoEstoque.local_movimentacao
            ).filter(MovimentacaoEstoque.local_movimentacao.isnot(None)).distinct().count()
            
            # Quantidade total movimentada
            qtd_total_movimentada = db.session.query(
                func.sum(MovimentacaoEstoque.qtd_movimentacao)
            ).scalar() or 0
            
            # Movimentações recentes (últimos 10 registros)
            movimentacoes_recentes = MovimentacaoEstoque.query.order_by(
                MovimentacaoEstoque.data_movimentacao.desc()
            ).limit(10).all()
            
            # Tipos de movimentação do último mês
            tipos_movimentacao = db.session.query(
                MovimentacaoEstoque.tipo_movimentacao,
                func.count(MovimentacaoEstoque.id).label('quantidade')
            ).filter(
                extract('month', MovimentacaoEstoque.data_movimentacao) == mes_atual,
                extract('year', MovimentacaoEstoque.data_movimentacao) == ano_atual
            ).group_by(MovimentacaoEstoque.tipo_movimentacao).all()
        else:
            total_movimentacoes = entradas_mes = saidas_mes = produtos_movimentados = 0
            locais_movimentacao = qtd_total_movimentada = 0
            movimentacoes_recentes = tipos_movimentacao = []
            
    except Exception as e:
        # ✅ FALLBACK: Se der erro, zera tudo
        total_movimentacoes = entradas_mes = saidas_mes = produtos_movimentados = 0
        locais_movimentacao = qtd_total_movimentada = 0
        movimentacoes_recentes = tipos_movimentacao = []
    
    return render_template('estoque/dashboard.html',
                         total_movimentacoes=total_movimentacoes,
                         entradas_mes=entradas_mes,
                         saidas_mes=saidas_mes,
                         produtos_movimentados=produtos_movimentados,
                         locais_movimentacao=locais_movimentacao,
                         qtd_total_movimentada=qtd_total_movimentada,
                         movimentacoes_recentes=movimentacoes_recentes,
                         tipos_movimentacao=tipos_movimentacao)

@estoque_bp.route('/movimentacoes')
@login_required
def listar_movimentacoes():
    """Lista movimentações de estoque"""
    # Filtros
    cod_produto = request.args.get('cod_produto', '')
    tipo_movimentacao = request.args.get('tipo_movimentacao', '')
    
    try:
        if db.engine.has_table('movimentacao_estoque'):
            # Query base
            query = MovimentacaoEstoque.query
            
            # Aplicar filtros
            if cod_produto:
                query = query.filter(MovimentacaoEstoque.cod_produto.ilike(f'%{cod_produto}%'))
            if tipo_movimentacao:
                query = query.filter(MovimentacaoEstoque.tipo_movimentacao == tipo_movimentacao)
            
            # Ordenação (limitado a 100 registros mais recentes)
            movimentacoes = query.order_by(MovimentacaoEstoque.data_movimentacao.desc()).limit(100).all()
        else:
            movimentacoes = []
    except Exception:
        movimentacoes = []
    
    return render_template('estoque/listar_movimentacoes.html',
                         movimentacoes=movimentacoes,
                         cod_produto=cod_produto,
                         tipo_movimentacao=tipo_movimentacao)

@estoque_bp.route('/api/estatisticas')
@login_required
def api_estatisticas():
    """API para estatísticas do módulo estoque"""
    try:
        from sqlalchemy import func
        
        # Estatísticas básicas
        stats = {
            'total_movimentacoes': MovimentacaoEstoque.query.count(),
            'movimentacoes_mes': MovimentacaoEstoque.query.filter(
                func.extract('month', MovimentacaoEstoque.data_movimentacao) == func.extract('month', func.now())
            ).count()
        }
        
        return jsonify({'success': True, 'data': stats})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@estoque_bp.route('/importar')
@login_required
@require_admin()
def importar_estoque():
    """Tela para importar dados de estoque"""
    return render_template('estoque/importar_estoque.html')

# TODO: Implementar outras rotas conforme necessário
# - POST /importar (upload e processamento de arquivos)
# - /movimentar (nova movimentação manual)
# - /relatorios (relatórios específicos) 