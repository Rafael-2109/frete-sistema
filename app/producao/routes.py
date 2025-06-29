from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.producao.models import ProgramacaoProducao, CadastroPalletizacao
from app.utils.auth_decorators import require_admin

# 📦 Blueprint da produção (seguindo padrão dos outros módulos)
producao_bp = Blueprint('producao', __name__, url_prefix='/producao')

@producao_bp.route('/')
@login_required
def index():
    """Dashboard do módulo produção"""
    try:
        from sqlalchemy import func
        
        # ✅ SEGURO: Verifica se tabelas existem antes de fazer query
        if db.engine.has_table('programacao_producao'):
            total_programacao = ProgramacaoProducao.query.count()
            
            # Produtos únicos programados
            produtos_programados = ProgramacaoProducao.query.with_entities(
                ProgramacaoProducao.cod_produto
            ).distinct().count()
            
            # Linhas de produção únicas
            linhas_producao = ProgramacaoProducao.query.with_entities(
                ProgramacaoProducao.linha_producao
            ).filter(ProgramacaoProducao.linha_producao.isnot(None)).distinct().count()
            
            # Quantidade total programada
            qtd_total_programada = db.session.query(
                func.sum(ProgramacaoProducao.qtd_programada)
            ).scalar() or 0
            
            # Programação recente (últimos 10)
            programacao_recente = ProgramacaoProducao.query.order_by(
                ProgramacaoProducao.data_programacao.desc()
            ).limit(10).all()
        else:
            total_programacao = produtos_programados = linhas_producao = 0
            qtd_total_programada = 0
            programacao_recente = []
        
        # Dados de palletização
        if db.engine.has_table('cadastro_palletizacao'):
            produtos_palletizados = CadastroPalletizacao.query.filter_by(ativo=True).count()
            
            # Peso total estimado (soma dos pesos)
            peso_total_estimado = db.session.query(
                func.sum(CadastroPalletizacao.peso_bruto)
            ).filter_by(ativo=True).scalar() or 0
            
            # Palletização recente (últimos 10)
            palletizacao_recente = CadastroPalletizacao.query.filter_by(
                ativo=True
            ).order_by(CadastroPalletizacao.updated_at.desc()).limit(10).all()
        else:
            produtos_palletizados = peso_total_estimado = 0
            palletizacao_recente = []
            
    except Exception as e:
        # ✅ FALLBACK: Se der erro, zera tudo
        total_programacao = produtos_programados = linhas_producao = 0
        qtd_total_programada = peso_total_estimado = produtos_palletizados = 0
        programacao_recente = palletizacao_recente = []
    
    return render_template('producao/dashboard.html',
                         total_programacao=total_programacao,
                         produtos_programados=produtos_programados,
                         produtos_palletizados=produtos_palletizados,
                         linhas_producao=linhas_producao,
                         qtd_total_programada=qtd_total_programada,
                         peso_total_estimado=peso_total_estimado,
                         programacao_recente=programacao_recente,
                         palletizacao_recente=palletizacao_recente)

@producao_bp.route('/programacao')
@login_required
def listar_programacao():
    """Lista programação de produção"""
    # Filtros
    cod_produto = request.args.get('cod_produto', '')
    status = request.args.get('status', '')
    
    try:
        if db.engine.has_table('programacao_producao'):
            # Query base
            query = ProgramacaoProducao.query
            
            # Aplicar filtros
            if cod_produto:
                query = query.filter(ProgramacaoProducao.cod_produto.ilike(f'%{cod_produto}%'))
            if status:
                query = query.filter(ProgramacaoProducao.status == status)
            
            # Ordenação
            programacoes = query.order_by(ProgramacaoProducao.data_programacao).all()
        else:
            programacoes = []
    except Exception:
        programacoes = []
    
    return render_template('producao/listar_programacao.html',
                         programacoes=programacoes,
                         cod_produto=cod_produto,
                         status=status)

# 🚚 ROTAS MOVIDAS PARA /localidades/ pois são cadastros de regiões/destinos
# - /localidades/rotas (lista rotas por UF)
# - /localidades/sub-rotas (lista sub-rotas por cidade)

@producao_bp.route('/palletizacao')
@login_required
def listar_palletizacao():
    """Lista cadastro de palletização (com medidas!)"""
    # Filtros
    cod_produto = request.args.get('cod_produto', '')
    
    try:
        if db.engine.has_table('cadastro_palletizacao'):
            # Query base
            query = CadastroPalletizacao.query.filter_by(ativo=True)
            
            # Aplicar filtros
            if cod_produto:
                query = query.filter(CadastroPalletizacao.cod_produto.ilike(f'%{cod_produto}%'))
            
            # Ordenação
            palletizacoes = query.order_by(CadastroPalletizacao.cod_produto).all()
        else:
            palletizacoes = []
    except Exception:
        palletizacoes = []
    
    return render_template('producao/listar_palletizacao.html',
                         palletizacoes=palletizacoes,
                         cod_produto=cod_produto)

@producao_bp.route('/api/estatisticas')
@login_required
def api_estatisticas():
    """API para estatísticas do módulo produção"""
    try:
        from sqlalchemy import func
        
        # Estatísticas básicas (apenas de produção)
        stats = {
            'total_ops': ProgramacaoProducao.query.count() if db.engine.has_table('programacao_producao') else 0,
            'ops_atrasadas': ProgramacaoProducao.query.filter_by(status='PROGRAMADA').count() if db.engine.has_table('programacao_producao') else 0,
            'produtos_palletizados': CadastroPalletizacao.query.filter_by(ativo=True).count() if db.engine.has_table('cadastro_palletizacao') else 0
        }
        
        return jsonify({'success': True, 'data': stats})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@producao_bp.route('/importar')
@login_required
@require_admin()
def importar_producao():
    """Tela para importar dados de produção"""
    return render_template('producao/importar_producao.html')

# TODO: Implementar outras rotas conforme necessário
# - POST /importar (upload e processamento de arquivos)
# - /criar_op (nova ordem de produção)
# - /editar_rota/<id> (edição de rotas)
# - /relatorios (relatórios específicos) 