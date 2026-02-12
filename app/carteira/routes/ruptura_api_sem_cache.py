"""
API Routes OTIMIZADA SEM CACHE para análise de ruptura de estoque
Versão focada em performance de queries sem dependência de cache
Ideal para ambientes com dados altamente dinâmicos
"""

from flask import jsonify
from app import db
from app.carteira.models import CarteiraPrincipal
from app.producao.models import ProgramacaoProducao
from app.carteira.main_routes import carteira_bp
from app.estoque.models import MovimentacaoEstoque
from app.estoque.models import UnificacaoCodigos
from app.utils.timezone import agora_utc_naive
from sqlalchemy import func, text
from sqlalchemy.orm import load_only
import logging
from datetime import datetime, date, timedelta
import time
from typing import Dict, List

logger = logging.getLogger(__name__)

# ============= FUNÇÃO AUXILIAR PARA EXPANDIR CÓDIGOS UNIFICADOS =============
def expandir_codigos_unificados(produtos):
    """
    Expande lista de produtos incluindo códigos unificados
    Retorna dict: {produto_principal: [lista_codigos_relacionados]}
    """
    produtos_expandidos = {}
    
    for produto in produtos:
        # Buscar todos os códigos relacionados (incluindo o próprio)
        codigos_relacionados = UnificacaoCodigos.get_todos_codigos_relacionados(produto)
        produtos_expandidos[produto] = list(codigos_relacionados)
        
        logger.debug(f"Produto {produto} expandido para: {codigos_relacionados}")
    
    return produtos_expandidos

# ============= QUERY OTIMIZADA COM CÓDIGOS EXPANDIDOS =============
def criar_query_estoque_batch_expandida(codigos_expandidos):
    """
    Query otimizada para trabalhar com códigos já expandidos (incluindo unificados)
    Retorna tupla: (query, params)
    """
    query_sql = """
    WITH estoque_atual AS (
        -- Calcular estoque atual para todos os códigos
        SELECT 
            cod_produto,
            COALESCE(SUM(qtd_movimentacao), 0) as estoque
        FROM movimentacao_estoque 
        WHERE cod_produto = ANY(:codigos_array)
          AND ativo = true
        GROUP BY cod_produto
    ),
    saidas_previstas AS (
        -- Saídas dos próximos 7 dias
        SELECT 
            cod_produto,
            expedicao as data,
            SUM(qtd_saldo) as quantidade
        FROM separacao 
        WHERE cod_produto = ANY(:codigos_array)
          AND sincronizado_nf = false
          AND expedicao BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7 days'
        GROUP BY cod_produto, expedicao
    ),
    producoes_previstas AS (
        -- Produções dos próximos 7 dias
        SELECT 
            cod_produto,
            data_programacao as data,
            SUM(qtd_programada) as quantidade
        FROM programacao_producao 
        WHERE cod_produto = ANY(:codigos_array)
          AND data_programacao BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7 days'
        GROUP BY cod_produto, data_programacao
    ),
    todos_codigos AS (
        -- Lista todos os códigos únicos das CTEs anteriores
        SELECT DISTINCT cod_produto FROM (
            SELECT cod_produto FROM estoque_atual
            UNION ALL
            SELECT cod_produto FROM saidas_previstas
            UNION ALL
            SELECT cod_produto FROM producoes_previstas
        ) sub
        WHERE cod_produto IS NOT NULL
    )
    SELECT 
        c.cod_produto,
        COALESCE(e.estoque, 0) as estoque_atual,
        COALESCE(json_agg(
            jsonb_build_object(
                'data', s.data,
                'tipo', 'saida',
                'qtd', s.quantidade
            ) ORDER BY s.data
        ) FILTER (WHERE s.data IS NOT NULL), '[]'::json) as saidas,
        COALESCE(json_agg(
            jsonb_build_object(
                'data', p.data,
                'tipo', 'producao',
                'qtd', p.quantidade
            ) ORDER BY p.data
        ) FILTER (WHERE p.data IS NOT NULL), '[]'::json) as producoes
    FROM todos_codigos c
    LEFT JOIN estoque_atual e ON e.cod_produto = c.cod_produto
    LEFT JOIN saidas_previstas s ON s.cod_produto = c.cod_produto
    LEFT JOIN producoes_previstas p ON p.cod_produto = c.cod_produto
    GROUP BY c.cod_produto, e.estoque
    """
    
    return text(query_sql), {'codigos_array': codigos_expandidos}

# ============= QUERY OTIMIZADA COM CTE (MANTIDA PARA COMPATIBILIDADE) =============
def criar_query_estoque_batch():
    """
    Cria uma query super otimizada usando CTE (Common Table Expressions)
    para calcular tudo de uma vez no banco de dados
    """
    return text("""
    WITH produtos_unicos AS (
        -- Produtos únicos do pedido
        SELECT DISTINCT cod_produto 
        FROM carteira_principal 
        WHERE num_pedido = :num_pedido AND ativo = true
    ),
    -- SIMPLIFICADO: Sem unificação de códigos por enquanto
    -- Cada produto é tratado individualmente
    codigos_expandidos AS (
        SELECT DISTINCT
            cod_produto as cod_principal,
            cod_produto as cod_relacionado
        FROM produtos_unicos
    ),
    estoque_atual AS (
        -- Calcular estoque atual agrupado
        SELECT 
            ce.cod_principal,
            COALESCE(SUM(m.qtd_movimentacao), 0) as estoque
        FROM codigos_expandidos ce
        LEFT JOIN movimentacao_estoque m ON m.cod_produto = ce.cod_relacionado AND m.ativo = true
        GROUP BY ce.cod_principal
    ),
    saidas_previstas AS (
        -- Saídas dos próximos 7 dias
        SELECT 
            ce.cod_principal,
            s.expedicao as data,
            SUM(s.qtd_saldo) as quantidade
        FROM codigos_expandidos ce
        LEFT JOIN separacao s ON s.cod_produto = ce.cod_relacionado 
            AND s.sincronizado_nf = false
            AND s.expedicao BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7 days'
        WHERE s.expedicao IS NOT NULL
        GROUP BY ce.cod_principal, s.expedicao
    ),
    producoes_previstas AS (
        -- Produções dos próximos 7 dias
        SELECT 
            ce.cod_principal,
            pp.data_programacao as data,
            SUM(pp.qtd_programada) as quantidade
        FROM codigos_expandidos ce
        LEFT JOIN programacao_producao pp ON pp.cod_produto = ce.cod_relacionado
            AND pp.data_programacao BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7 days'
        WHERE pp.data_programacao IS NOT NULL
        GROUP BY ce.cod_principal, pp.data_programacao
    )
    -- Resultado final combinado (removido DISTINCT para evitar conflito com ORDER BY)
    SELECT 
        e.cod_principal as cod_produto,
        e.estoque as estoque_atual,
        COALESCE(json_agg(
            jsonb_build_object(
                'data', s.data,
                'tipo', 'saida',
                'qtd', s.quantidade
            ) ORDER BY s.data
        ) FILTER (WHERE s.data IS NOT NULL), '[]'::json) as saidas,
        COALESCE(json_agg(
            jsonb_build_object(
                'data', p.data,
                'tipo', 'producao',
                'qtd', p.quantidade
            ) ORDER BY p.data
        ) FILTER (WHERE p.data IS NOT NULL), '[]'::json) as producoes
    FROM estoque_atual e
    LEFT JOIN saidas_previstas s ON s.cod_principal = e.cod_principal
    LEFT JOIN producoes_previstas p ON p.cod_principal = e.cod_principal
    GROUP BY e.cod_principal, e.estoque
    """)

# ============= CÁLCULO RÁPIDO EM MEMÓRIA =============
def calcular_projecao_em_memoria(estoque_atual: float, saidas: List, producoes: List) -> Dict:
    """
    Calcula projeção de 7 dias em memória (muito rápido)
    """
    data_inicio = date.today()
    projecao = []
    estoque_dia = float(estoque_atual)
    menor_estoque = estoque_dia
    
    # Criar dicionários para lookup O(1)
    saidas_por_data = {s['data']: float(s['qtd']) for s in saidas if s}
    producoes_por_data = {p['data']: float(p['qtd']) for p in producoes if p}
    
    # Projetar 7 dias
    for dias in range(8):
        data = data_inicio + timedelta(days=dias)
        data_str = data.isoformat()
        
        saida_dia = saidas_por_data.get(data_str, 0)
        entrada_dia = producoes_por_data.get(data_str, 0)
        
        estoque_inicial = estoque_dia
        estoque_dia = estoque_dia - saida_dia + entrada_dia
        menor_estoque = min(menor_estoque, estoque_dia)
        
        projecao.append({
            'data': data_str,
            'estoque_inicial': estoque_inicial,
            'saidas': saida_dia,
            'entradas': entrada_dia,
            'estoque_final': estoque_dia
        })
    
    return {
        'estoque_atual': estoque_atual,
        'menor_estoque_d7': menor_estoque,
        'projecao': projecao,
        'tem_ruptura': menor_estoque < 0
    }

# ============= ENDPOINT PRINCIPAL SEM CACHE =============
@carteira_bp.route('/api/ruptura/sem-cache/analisar-pedido/<num_pedido>', methods=['GET'])
def analisar_ruptura_pedido_sem_cache(num_pedido):
    """
    Versão OTIMIZADA SEM CACHE - Ideal para dados dinâmicos
    
    Otimizações aplicadas:
    1. Query única com CTE para dados de estoque
    2. Load_only para campos necessários
    3. Cálculos em memória (não no banco)
    4. Sem overhead de cache/Redis
    5. Índices otimizados assumidos
    
    Performance esperada: 30-50ms por pedido
    """
    try:
        inicio_total = time.time()
        
        # ===== BUSCAR ITENS DO PEDIDO (Query Leve) =====
        # IMPORTANTE: Filtrar qtd_saldo_produto_pedido >= 0.001 para evitar analisar itens já faturados
        itens = db.session.query(CarteiraPrincipal).options(
            load_only(
                CarteiraPrincipal.cod_produto,
                CarteiraPrincipal.nome_produto,
                CarteiraPrincipal.qtd_saldo_produto_pedido,
                CarteiraPrincipal.preco_produto_pedido
            )
        ).filter(
            CarteiraPrincipal.num_pedido == num_pedido,
            CarteiraPrincipal.ativo == True,
            CarteiraPrincipal.qtd_saldo_produto_pedido >= 0.001  # Evita floats zerados (itens já faturados)
        ).all()

        if not itens:
            return jsonify({
                'success': False,
                'message': 'Pedido não encontrado ou todos os itens já foram faturados'
            }), 404
        
        produtos_unicos = list(set([item.cod_produto for item in itens]))
        
        # ===== EXPANDIR CÓDIGOS COM UNIFICAÇÃO =====
        produtos_expandidos = expandir_codigos_unificados(produtos_unicos)
        
        # Coletar todos os códigos únicos para a query
        todos_codigos = set()
        for codigos in produtos_expandidos.values():
            todos_codigos.update(codigos)
        
        
        # ===== EXECUTAR QUERY OTIMIZADA =====
        inicio_query = time.time()
        
        # Query com códigos expandidos
        query, params = criar_query_estoque_batch_expandida(list(todos_codigos))
        resultado_raw = db.session.execute(query, params).fetchall()
        
        # Converter resultado em dicionário e agregar por produto principal
        dados_por_codigo = {}
        for row in resultado_raw:
            cod_produto = row[0]
            estoque_atual = float(row[1] or 0)
            saidas = row[2] if row[2] else []
            producoes = row[3] if row[3] else []
            
            dados_por_codigo[cod_produto] = {
                'estoque': estoque_atual,
                'saidas': saidas,
                'producoes': producoes
            }
        
        # Agregar por produto principal
        dados_produtos = {}
        for produto_principal, codigos_relacionados in produtos_expandidos.items():
            estoque_total = 0
            todas_saidas = []
            todas_producoes = []
            
            # Somar dados de todos os códigos relacionados
            for codigo in codigos_relacionados:
                if codigo in dados_por_codigo:
                    estoque_total += dados_por_codigo[codigo]['estoque']
                    todas_saidas.extend(dados_por_codigo[codigo]['saidas'])
                    todas_producoes.extend(dados_por_codigo[codigo]['producoes'])
            
            # Calcular projeção com dados agregados
            dados_produtos[produto_principal] = calcular_projecao_em_memoria(
                estoque_total, todas_saidas, todas_producoes
            )
        
        # Fallback para produtos sem dados
        for cod in produtos_unicos:
            if cod not in dados_produtos:
                # Query rápida individual como fallback
                # Buscar todos os códigos relacionados (unificados)
                codigos_relacionados = UnificacaoCodigos.get_todos_codigos_relacionados(cod)
                
                estoque = db.session.query(
                    func.coalesce(func.sum(MovimentacaoEstoque.qtd_movimentacao), 0)
                ).filter(
                    MovimentacaoEstoque.cod_produto.in_(codigos_relacionados),
                    MovimentacaoEstoque.ativo == True
                ).scalar()
                
                dados_produtos[cod] = {
                    'estoque_atual': float(estoque or 0),
                    'menor_estoque_d7': float(estoque or 0),
                    'projecao': [],
                    'tem_ruptura': float(estoque or 0) < 0
                }
        
        tempo_query = (time.time() - inicio_query) * 1000
        
        # ===== BUSCAR PRODUÇÕES FUTURAS (Query Simples) =====
        # IMPORTANTE: Buscar produções para TODOS os códigos expandidos, não apenas os originais
        producoes_futuras = db.session.query(
            ProgramacaoProducao.cod_produto,
            ProgramacaoProducao.data_programacao,
            func.sum(ProgramacaoProducao.qtd_programada).label('qtd_producao')
        ).filter(
            ProgramacaoProducao.cod_produto.in_(list(todos_codigos)),  # Usar TODOS os códigos expandidos!
            ProgramacaoProducao.data_programacao >= agora_utc_naive().date()
        ).group_by(
            ProgramacaoProducao.cod_produto,
            ProgramacaoProducao.data_programacao
        ).order_by(
            ProgramacaoProducao.data_programacao
        ).all()
        
        # Organizar produções por produto PRINCIPAL (considerando unificação)
        producoes_por_produto = {}
        producoes_por_codigo_original = {}
        
        # Primeiro, guardar todas as produções por código original
        for prod in producoes_futuras:
            if prod.cod_produto not in producoes_por_codigo_original:
                producoes_por_codigo_original[prod.cod_produto] = []
            producoes_por_codigo_original[prod.cod_produto].append({
                'data': prod.data_programacao,
                'qtd': float(prod.qtd_producao)
            })
        
        # Depois, agregar por produto principal usando produtos_expandidos
        for produto_principal, codigos_relacionados in produtos_expandidos.items():
            todas_producoes = []
            for codigo in codigos_relacionados:
                if codigo in producoes_por_codigo_original:
                    todas_producoes.extend(producoes_por_codigo_original[codigo])
            
            # Agrupar produções por data e somar quantidades
            producoes_agrupadas = {}
            for prod in todas_producoes:
                data_str = prod['data'].isoformat() if hasattr(prod['data'], 'isoformat') else str(prod['data'])
                if data_str not in producoes_agrupadas:
                    producoes_agrupadas[data_str] = {'data': prod['data'], 'qtd': 0}
                producoes_agrupadas[data_str]['qtd'] += prod['qtd']
            
            # Converter de volta para lista ordenada por data
            producoes_por_produto[produto_principal] = sorted(
                producoes_agrupadas.values(), 
                key=lambda x: x['data']
            )
            
            # Log quando há produção unificada
            if len(codigos_relacionados) > 1 and producoes_por_produto[produto_principal]:
                total_producao = sum(p['qtd'] for p in producoes_por_produto[produto_principal])
                logger.info(f"🔀 Produto {produto_principal} tem produção unificada de {total_producao} un de {codigos_relacionados}")
        
        # ===== ANÁLISE RÁPIDA DOS ITENS =====
        itens_com_ruptura = []
        itens_disponiveis_lista = []
        valor_total_pedido = 0
        valor_com_ruptura = 0
        datas_producao_ruptura = []
        tem_item_sem_producao = False
        
        for item in itens:
            # Cálculos básicos
            qtd_saldo = float(item.qtd_saldo_produto_pedido)
            preco = float(item.preco_produto_pedido or 0)
            valor_item = qtd_saldo * preco
            valor_total_pedido += valor_item
            
            # Dados do produto
            dados = dados_produtos.get(item.cod_produto, {})
            estoque_d7 = dados.get('menor_estoque_d7', 0)
            
            if qtd_saldo > estoque_d7:
                # Item COM ruptura
                ruptura = qtd_saldo - estoque_d7
                valor_com_ruptura += valor_item
                
                # Verificar produção futura
                producoes = producoes_por_produto.get(item.cod_produto, [])
                data_disponivel = None
                primeira_producao = None
                qtd_primeira_producao = 0
                
                # Debug específico para produto 4759098
                if item.cod_produto == '4759098':
                    logger.info(f"🔍 DEBUG 4759098:")
                    logger.info(f"   - Estoque D+7: {estoque_d7}")
                    logger.info(f"   - Ruptura: {ruptura}")
                    logger.info(f"   - Produções encontradas: {len(producoes)} produções")
                    if producoes:
                        logger.info(f"   - Primeira produção: {producoes[0]}")
                    logger.info(f"   - Códigos unificados: {produtos_expandidos.get(item.cod_produto, [])}")
                
                if producoes:
                    primeira_producao = producoes[0]
                    qtd_primeira_producao = primeira_producao['qtd']
                    
                    # Calcular quando terá estoque
                    qtd_acumulada = estoque_d7
                    for prod in producoes:
                        qtd_acumulada += prod['qtd']
                        if qtd_acumulada >= qtd_saldo:
                            data_disponivel = prod['data']
                            # Adicionar 1 dia de lead time interno
                            from datetime import timedelta
                            data_disponivel = data_disponivel + timedelta(days=1)
                            break
                    
                    if data_disponivel:
                        datas_producao_ruptura.append(data_disponivel)
                else:
                    tem_item_sem_producao = True
                
                # Obter estoque atual do produto
                estoque_atual = dados_produtos.get(item.cod_produto, {}).get('estoque_atual', 0)
                
                itens_com_ruptura.append({
                    'cod_produto': item.cod_produto,
                    'nome_produto': item.nome_produto,
                    'qtd_saldo': int(qtd_saldo),
                    'estoque_atual': int(estoque_atual),  # Novo campo: estoque atual
                    'estoque_min_d7': int(estoque_d7),
                    'ruptura_qtd': int(ruptura),
                    'data_producao': primeira_producao['data'].isoformat() if primeira_producao else None,
                    'qtd_producao': int(qtd_primeira_producao),
                    'data_disponivel': data_disponivel.isoformat() if data_disponivel else None
                })
            else:
                # Item SEM ruptura (disponível)
                # Obter estoque atual do produto
                estoque_atual = dados_produtos.get(item.cod_produto, {}).get('estoque_atual', 0)
                
                itens_disponiveis_lista.append({
                    'cod_produto': item.cod_produto,
                    'nome_produto': item.nome_produto,
                    'qtd_saldo': int(qtd_saldo),
                    'estoque_atual': int(estoque_atual),  # Novo campo: estoque atual
                    'estoque_min_d7': int(estoque_d7),
                    'preco_unitario': preco,
                    'valor_total': valor_item
                })
        
        # ===== MONTAR RESULTADO FINAL =====
        tempo_total = (time.time() - inicio_total) * 1000
        
        if not itens_com_ruptura:
            # Pedido OK - Todos disponíveis
            resultado = {
                'success': True,
                'pedido_ok': True,
                'percentual_disponibilidade': 100,
                'data_disponibilidade_total': 'agora',
                'message': 'Pedido OK - Todos os itens disponíveis',
                'performance_ms': round(tempo_total, 2),
                'query_ms': round(tempo_query, 2),
                'sem_cache': True,
                'version': 'sem-cache-v1'
            }
            
            logger.info(f"✅ Pedido {num_pedido} OK em {tempo_total:.2f}ms (sem cache)")
            return jsonify(resultado)
        
        # Calcular métricas
        percentual_ruptura = (valor_com_ruptura / valor_total_pedido * 100) if valor_total_pedido > 0 else 0
        percentual_disponibilidade = 100 - percentual_ruptura
        
        # Data de disponibilidade total
        if tem_item_sem_producao:
            data_disponibilidade_total = None
        elif datas_producao_ruptura:
            data_disponibilidade_total = max(datas_producao_ruptura).isoformat()
        else:
            data_disponibilidade_total = None
        
        # Determinar criticidade
        qtd_itens_ruptura = len(itens_com_ruptura)
        if qtd_itens_ruptura > 3 and percentual_ruptura > 10:
            criticidade = 'CRITICA'
        elif qtd_itens_ruptura <= 3 and percentual_ruptura <= 10:
            criticidade = 'ALTA'
        elif qtd_itens_ruptura <= 2 and percentual_ruptura <= 5:
            criticidade = 'MEDIA'
        else:
            criticidade = 'BAIXA'
        
        resultado = {
            'success': True,
            'pedido_ok': False,
            'percentual_disponibilidade': round(percentual_disponibilidade, 0),
            'data_disponibilidade_total': data_disponibilidade_total,
            'resumo': {
                'num_pedido': num_pedido,
                'percentual_ruptura': round(percentual_ruptura, 2),
                'percentual_disponibilidade': round(percentual_disponibilidade, 0),
                'percentual_itens_disponiveis': round((len(itens_disponiveis_lista) / len(itens) * 100), 0),
                'qtd_itens_ruptura': qtd_itens_ruptura,
                'qtd_itens_disponiveis': len(itens_disponiveis_lista),
                'total_itens': len(itens),
                'criticidade': criticidade,
                'valor_total_pedido': round(valor_total_pedido, 2),
                'valor_disponivel': round(valor_total_pedido - valor_com_ruptura, 2),
                'valor_com_ruptura': round(valor_com_ruptura, 2),
                'data_disponibilidade_total': data_disponibilidade_total
            },
            'itens': itens_com_ruptura,
            'itens_disponiveis': itens_disponiveis_lista,
            'performance_ms': round(tempo_total, 2),
            'query_ms': round(tempo_query, 2),
            'sem_cache': True,
            'version': 'sem-cache-v1'
        }
        
        logger.info(f"⚠️ Pedido {num_pedido} com ruptura em {tempo_total:.2f}ms (sem cache)")
        return jsonify(resultado)
        
    except Exception as e:
        logger.error(f"Erro na análise sem cache: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
