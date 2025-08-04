"""
Rotas otimizadas usando cache de saldo de estoque
Performance target: < 1 segundo
"""
from flask import render_template, request, jsonify, flash
from flask_login import login_required, current_user
from app.estoque import estoque_bp
from app.estoque.models_cache import SaldoEstoqueCache, ProjecaoEstoqueCache
from app import db
import logging
from app.utils.timezone import agora_brasil

logger = logging.getLogger(__name__)


@estoque_bp.route('/saldo-estoque-v2')
@login_required
def saldo_estoque_v2():
    """
    Versão otimizada do saldo de estoque usando cache
    Performance: < 1 segundo para milhares de produtos
    """
    try:
        import time
        start_time = time.time()
        
        # Obter parâmetros
        codigo_produto = request.args.get('codigo_produto', '').strip()
        status_ruptura = request.args.get('status_ruptura', '').strip()
        limite = int(request.args.get('limite', '50'))
        page = int(request.args.get('page', '1'))
        ordem_coluna = request.args.get('ordem', 'codigo')
        ordem_direcao = request.args.get('dir', 'asc')
        
        # Validar limite
        if limite not in [50, 100, 200]:
            limite = 50
        
        # Query base no cache (muito rápida)
        query = SaldoEstoqueCache.query
        
        # Filtros
        if codigo_produto:
            query = query.filter(
                db.or_(
                    SaldoEstoqueCache.cod_produto.ilike(f'%{codigo_produto}%'),
                    SaldoEstoqueCache.nome_produto.ilike(f'%{codigo_produto}%')
                )
            )
        
        if status_ruptura:
            query = query.filter_by(status_ruptura=status_ruptura)
        
        # Ordenação no banco (muito mais eficiente)
        if ordem_coluna == 'codigo':
            query = query.order_by(
                SaldoEstoqueCache.cod_produto.desc() if ordem_direcao == 'desc' 
                else SaldoEstoqueCache.cod_produto
            )
        elif ordem_coluna == 'produto':
            query = query.order_by(
                SaldoEstoqueCache.nome_produto.desc() if ordem_direcao == 'desc' 
                else SaldoEstoqueCache.nome_produto
            )
        elif ordem_coluna == 'estoque':
            query = query.order_by(
                SaldoEstoqueCache.saldo_atual.desc() if ordem_direcao == 'desc' 
                else SaldoEstoqueCache.saldo_atual
            )
        elif ordem_coluna == 'carteira':
            query = query.order_by(
                SaldoEstoqueCache.qtd_carteira.desc() if ordem_direcao == 'desc' 
                else SaldoEstoqueCache.qtd_carteira
            )
        elif ordem_coluna == 'ruptura':
            query = query.order_by(
                SaldoEstoqueCache.previsao_ruptura_7d.desc() if ordem_direcao == 'desc' 
                else SaldoEstoqueCache.previsao_ruptura_7d
            )
        elif ordem_coluna == 'status':
            # Ordenar por prioridade
            case_expr = db.case(
                (SaldoEstoqueCache.status_ruptura == 'CRÍTICO', 1),
                (SaldoEstoqueCache.status_ruptura == 'ATENÇÃO', 2),
                (SaldoEstoqueCache.status_ruptura == 'OK', 3),
                else_=4
            )
            if ordem_direcao == 'desc':
                query = query.order_by(case_expr.desc())
            else:
                query = query.order_by(case_expr)
        
        # Paginação eficiente
        paginated = query.paginate(page=page, per_page=limite, error_out=False)
        
        # Estatísticas (queries agregadas otimizadas)
        estatisticas_query = db.session.query(
            db.func.count(SaldoEstoqueCache.id).label('total'),
            db.func.sum(db.case((SaldoEstoqueCache.status_ruptura == 'CRÍTICO', 1), else_=0)).label('criticos'),
            db.func.sum(db.case((SaldoEstoqueCache.status_ruptura == 'ATENÇÃO', 1), else_=0)).label('atencao'),
            db.func.sum(db.case((SaldoEstoqueCache.status_ruptura == 'OK', 1), else_=0)).label('ok')
        ).first()
        
        # Preparar dados para o template
        produtos_resumo = []
        for item in paginated.items:
            produtos_resumo.append({
                'cod_produto': item.cod_produto,
                'nome_produto': item.nome_produto,
                'estoque_inicial': float(item.saldo_atual),
                'qtd_total_carteira': float(item.qtd_carteira),
                'previsao_ruptura': float(item.previsao_ruptura_7d) if item.previsao_ruptura_7d else 0,
                'status_ruptura': item.status_ruptura or 'OK'
            })
        
        estatisticas = {
            'total_produtos': estatisticas_query.total or 0,
            'produtos_criticos': int(estatisticas_query.criticos or 0),
            'produtos_atencao': int(estatisticas_query.atencao or 0),
            'produtos_ok': int(estatisticas_query.ok or 0),
            'produtos_exibidos': len(produtos_resumo),
            'total_filtrado': paginated.total
        }
        
        # Tempo de processamento
        tempo_processamento = time.time() - start_time
        logger.info(f"✅ Saldo estoque V2 carregado em {tempo_processamento:.3f}s")
        
        if tempo_processamento > 1:
            logger.warning(f"⚠️ Performance abaixo do esperado: {tempo_processamento:.3f}s")
        
        return render_template('estoque/saldo_estoque.html',
                             produtos=produtos_resumo,
                             estatisticas=estatisticas,
                             limite_exibicao=False,
                             page=page,
                             total_paginas=paginated.pages,
                             limite=limite,
                             codigo_produto=codigo_produto,
                             status_ruptura=status_ruptura,
                             tempo_processamento=tempo_processamento)
        
    except Exception as e:
        logger.error(f"❌ Erro no saldo estoque V2: {str(e)}")
        flash(f'❌ Erro ao carregar saldo de estoque: {str(e)}', 'error')
        
        return render_template('estoque/saldo_estoque.html',
                             produtos=[],
                             estatisticas={'total_produtos': 0, 'produtos_exibidos': 0, 
                                         'produtos_criticos': 0, 'produtos_atencao': 0, 
                                         'produtos_ok': 0, 'total_filtrado': 0},
                             limite_exibicao=False,
                             page=1,
                             total_paginas=1,
                             limite=50,
                             codigo_produto='',
                             status_ruptura='')


@estoque_bp.route('/saldo-estoque-v2/api/produto/<cod_produto>')
@login_required
def api_saldo_produto_v2(cod_produto):
    """
    API otimizada para obter projeção de um produto do cache
    """
    try:
        # Buscar do cache (instantâneo)
        cache = SaldoEstoqueCache.query.filter_by(cod_produto=str(cod_produto)).first()
        
        if not cache:
            return jsonify({'error': 'Produto não encontrado no cache'}), 404
        
        # Buscar projeção do cache
        projecoes = ProjecaoEstoqueCache.query.filter_by(
            cod_produto=str(cod_produto)
        ).order_by(ProjecaoEstoqueCache.dia_offset).all()
        
        # Se não houver projeção no cache, calcular sob demanda
        if not projecoes:
            ProjecaoEstoqueCache.atualizar_projecao(cod_produto)
            projecoes = ProjecaoEstoqueCache.query.filter_by(
                cod_produto=str(cod_produto)
            ).order_by(ProjecaoEstoqueCache.dia_offset).all()
        
        # Montar resposta
        projecao_29_dias = []
        for proj in projecoes:
            projecao_29_dias.append({
                'dia': proj.dia_offset,
                'data': proj.data_projecao,
                'data_formatada': proj.data_projecao.strftime('%d/%m'),
                'estoque_inicial': float(proj.estoque_inicial),
                'saida_prevista': float(proj.saida_prevista),
                'producao_programada': float(proj.producao_programada),
                'estoque_final': float(proj.estoque_final)
            })
        
        resumo = {
            'cod_produto': cache.cod_produto,
            'nome_produto': cache.nome_produto,
            'estoque_inicial': float(cache.saldo_atual),
            'qtd_total_carteira': float(cache.qtd_carteira),
            'previsao_ruptura': float(cache.previsao_ruptura_7d) if cache.previsao_ruptura_7d else 0,
            'status_ruptura': cache.status_ruptura or 'OK',
            'projecao_29_dias': projecao_29_dias
        }
        
        return jsonify({
            'success': True,
            'produto': resumo
        })
        
    except Exception as e:
        logger.error(f"Erro na API V2 produto {cod_produto}: {str(e)}")
        return jsonify({'error': str(e)}), 500


@estoque_bp.route('/saldo-estoque-v2/atualizar-cache', methods=['POST'])
@login_required
def atualizar_cache_manual():
    """
    Endpoint para forçar atualização do cache
    """
    if current_user.nivel != 'admin':
        return jsonify({'error': 'Acesso negado'}), 403
    
    try:
        tipo = request.json.get('tipo', 'parcial')  # parcial ou completo
        cod_produto = request.json.get('cod_produto')
        
        if tipo == 'completo':
            # Reconstruir todo o cache
            from app.estoque.models_cache import SaldoEstoqueCache
            sucesso = SaldoEstoqueCache.inicializar_cache_completo()
            
            if sucesso:
                return jsonify({
                    'success': True,
                    'message': '✅ Cache reconstruído completamente'
                })
            else:
                return jsonify({'error': 'Erro ao reconstruir cache'}), 500
                
        elif tipo == 'parcial' and cod_produto:
            # Atualizar apenas um produto
            cache = SaldoEstoqueCache.query.filter_by(cod_produto=str(cod_produto)).first()
            if cache:
                SaldoEstoqueCache.atualizar_carteira(cod_produto)
                ProjecaoEstoqueCache.atualizar_projecao(cod_produto)
                
                return jsonify({
                    'success': True,
                    'message': f'✅ Cache atualizado para {cod_produto}'
                })
            else:
                return jsonify({'error': 'Produto não encontrado'}), 404
        
        return jsonify({'error': 'Parâmetros inválidos'}), 400
        
    except Exception as e:
        logger.error(f"Erro ao atualizar cache: {str(e)}")
        return jsonify({'error': str(e)}), 500


@estoque_bp.route('/saldo-estoque-v2/status-cache')
@login_required
def status_cache():
    """
    Mostra estatísticas do cache
    """
    try:
        from datetime import datetime, timedelta
        
        # Estatísticas do cache
        total_produtos = SaldoEstoqueCache.query.count()
        
        # Produtos desatualizados (mais de 1 hora)
        uma_hora_atras = agora_brasil() - timedelta(hours=1)
        desatualizados = SaldoEstoqueCache.query.filter(
            db.or_(
                SaldoEstoqueCache.ultima_atualizacao_saldo < uma_hora_atras,
                SaldoEstoqueCache.ultima_atualizacao_saldo.is_(None)
            )
        ).count()
        
        # Produtos com projeção
        com_projecao = db.session.query(
            db.func.count(db.func.distinct(ProjecaoEstoqueCache.cod_produto))
        ).scalar()
        
        return jsonify({
            'total_produtos': total_produtos,
            'produtos_desatualizados': desatualizados,
            'produtos_com_projecao': com_projecao,
            'percentual_atualizado': round((total_produtos - desatualizados) / total_produtos * 100, 1) if total_produtos > 0 else 0,
            'ultima_verificacao': agora_brasil().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500