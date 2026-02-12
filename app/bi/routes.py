"""
Rotas e APIs do módulo BI
"""
from flask import render_template, jsonify, request
from flask_login import login_required
from app.bi import bi_bp
from app.bi.services import BiETLService
from app.bi.models import (
    BiFreteAgregado, BiDespesaDetalhada,
    BiPerformanceTransportadora, BiAnaliseRegional,
    BiIndicadorMensal
)
from app.utils.timezone import agora_utc_naive
from app import db
from datetime import datetime, date, timedelta
from sqlalchemy import func, and_, desc, distinct
import json

@bi_bp.route('/')
@bi_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard principal do BI"""
    return render_template('bi/dashboard.html')

@bi_bp.route('/transportadoras')
@login_required
def transportadoras():
    """Dashboard de análise de transportadoras"""
    return render_template('bi/transportadoras.html')

@bi_bp.route('/regional')
@login_required
def regional():
    """Dashboard de análise regional"""
    return render_template('bi/regional.html')

@bi_bp.route('/despesas')
@login_required
def despesas():
    """Dashboard de análise de despesas extras"""
    return render_template('bi/despesas.html')

# APIs para dados do dashboard

@bi_bp.route('/api/indicadores-principais')
def api_indicadores_principais():
    """Retorna indicadores principais para o dashboard"""
    try:
        # Período atual (últimos 60 dias para garantir dados)
        hoje = date.today()
        fim_periodo = hoje
        inicio_periodo = hoje - timedelta(days=60)

        # Período anterior (60 dias antes)
        fim_periodo_anterior = inicio_periodo
        inicio_periodo_anterior = inicio_periodo - timedelta(days=60)
        
        # Busca dados do mês atual
        dados_mes = db.session.query(
            func.sum(BiFreteAgregado.valor_pago_total).label('custo_total'),
            func.sum(BiFreteAgregado.valor_despesas_extras).label('despesas_total'),
            func.sum(BiFreteAgregado.peso_total_kg).label('peso_total'),
            func.sum(BiFreteAgregado.valor_total_nf).label('valor_faturado'),
            func.count(distinct(BiFreteAgregado.transportadora_id)).label('qtd_transportadoras'),
            func.avg(BiFreteAgregado.custo_por_kg).label('custo_medio_kg')
        ).filter(
            BiFreteAgregado.data_referencia >= inicio_periodo
        ).first()
        
        # Busca dados do mês anterior para comparação
        dados_mes_anterior = db.session.query(
            func.sum(BiFreteAgregado.valor_pago_total).label('custo_total')
        ).filter(
            and_(
                BiFreteAgregado.data_referencia >= inicio_periodo_anterior,
                BiFreteAgregado.data_referencia < inicio_periodo
            )
        ).first()
        
        # Calcula variações
        variacao_mes = 0
        if dados_mes_anterior and dados_mes_anterior.custo_total and dados_mes.custo_total:
            variacao_mes = ((dados_mes.custo_total - dados_mes_anterior.custo_total) / 
                           dados_mes_anterior.custo_total) * 100
        
        # Economia realizada (diferença entre cotado e pago)
        economia = db.session.query(
            func.sum(BiFreteAgregado.valor_cotado_total - BiFreteAgregado.valor_pago_total)
        ).filter(
            BiFreteAgregado.data_referencia >= inicio_periodo
        ).scalar() or 0
        
        return jsonify({
            'custo_total': float(dados_mes.custo_total or 0),
            'despesas_total': float(dados_mes.despesas_total or 0),
            'peso_total': float(dados_mes.peso_total or 0),
            'valor_faturado': float(dados_mes.valor_faturado or 0),
            'qtd_transportadoras': int(dados_mes.qtd_transportadoras or 0),
            'custo_medio_kg': float(dados_mes.custo_medio_kg or 0),
            'variacao_mes': float(variacao_mes),
            'economia_realizada': float(economia),
            'periodo': f'Últimos 60 dias'
        })
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@bi_bp.route('/api/evolucao-mensal')
def api_evolucao_mensal():
    """Retorna evolução mensal de custos"""
    try:
        # Últimos 3 meses com dados (junho a setembro)
        data_fim = date.today()
        data_inicio = data_fim - timedelta(days=90)
        
        dados = db.session.query(
            BiFreteAgregado.ano,
            BiFreteAgregado.mes,
            func.sum(BiFreteAgregado.valor_pago_total).label('custo_total'),
            func.sum(BiFreteAgregado.valor_despesas_extras).label('despesas'),
            func.sum(BiFreteAgregado.peso_total_kg).label('peso'),
            func.avg(BiFreteAgregado.custo_por_kg).label('custo_kg')
        ).filter(
            BiFreteAgregado.data_referencia >= data_inicio
        ).group_by(
            BiFreteAgregado.ano,
            BiFreteAgregado.mes
        ).order_by(
            BiFreteAgregado.ano,
            BiFreteAgregado.mes
        ).all()
        
        resultado = []
        for d in dados:
            resultado.append({
                'periodo': f"{d.mes:02d}/{d.ano}",
                'custo_total': float(d.custo_total or 0),
                'despesas': float(d.despesas or 0),
                'peso': float(d.peso or 0),
                'custo_kg': float(d.custo_kg or 0)
            })
        
        return jsonify(resultado)
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@bi_bp.route('/api/ranking-transportadoras')
def api_ranking_transportadoras():
    """Retorna ranking de transportadoras"""
    try:
        periodo = request.args.get('periodo', 'mes')  # mes, trimestre, ano
        
        # Define período
        hoje = date.today()
        if periodo == 'ano':
            data_inicio = hoje - timedelta(days=365)
        elif periodo == 'trimestre':
            data_inicio = hoje - timedelta(days=90)
        else:  # mes
            data_inicio = hoje - timedelta(days=30)
        
        # Busca dados agregados
        dados = db.session.query(
            BiFreteAgregado.transportadora_id,
            BiFreteAgregado.transportadora_nome,
            func.sum(BiFreteAgregado.valor_pago_total).label('valor_total'),
            func.sum(BiFreteAgregado.peso_total_kg).label('peso_total'),
            func.sum(BiFreteAgregado.valor_despesas_extras).label('despesas'),
            func.avg(BiFreteAgregado.custo_por_kg).label('custo_kg'),
            func.count(distinct(BiFreteAgregado.data_referencia)).label('dias_ativos')
        ).filter(
            BiFreteAgregado.data_referencia >= data_inicio
        ).group_by(
            BiFreteAgregado.transportadora_id,
            BiFreteAgregado.transportadora_nome
        ).order_by(
            desc('valor_total')
        ).limit(10).all()
        
        resultado = []
        for idx, d in enumerate(dados, 1):
            percentual_despesas = 0
            if d.valor_total:
                percentual_despesas = (d.despesas / d.valor_total) * 100
            
            resultado.append({
                'ranking': idx,
                'transportadora': d.transportadora_nome,
                'valor_total': float(d.valor_total or 0),
                'peso_total': float(d.peso_total or 0),
                'custo_kg': float(d.custo_kg or 0),
                'despesas': float(d.despesas or 0),
                'percentual_despesas': float(percentual_despesas),
                'dias_ativos': int(d.dias_ativos or 0)
            })
        
        return jsonify(resultado)
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@bi_bp.route('/api/analise-regional')
def api_analise_regional():
    """Retorna análise por região/UF"""
    try:
        # Últimos 60 dias
        hoje = date.today()
        inicio_mes = hoje - timedelta(days=60)
        
        # Busca dados por região
        dados = db.session.query(
            BiFreteAgregado.destino_regiao,
            BiFreteAgregado.destino_uf,
            func.sum(BiFreteAgregado.valor_pago_total).label('custo_total'),
            func.sum(BiFreteAgregado.peso_total_kg).label('peso_total'),
            func.avg(BiFreteAgregado.custo_por_kg).label('custo_medio_kg'),
            func.count(distinct(BiFreteAgregado.cliente_cnpj)).label('qtd_clientes')
        ).filter(
            BiFreteAgregado.data_referencia >= inicio_mes
        ).group_by(
            BiFreteAgregado.destino_regiao,
            BiFreteAgregado.destino_uf
        ).order_by(
            desc('custo_total')
        ).all()
        
        # Agrupa por região
        regioes = {}
        for d in dados:
            regiao = d.destino_regiao or 'Indefinido'
            if regiao not in regioes:
                regioes[regiao] = {
                    'regiao': regiao,
                    'custo_total': 0,
                    'peso_total': 0,
                    'estados': [],
                    'qtd_clientes': 0
                }
            
            regioes[regiao]['custo_total'] += float(d.custo_total or 0)
            regioes[regiao]['peso_total'] += float(d.peso_total or 0)
            regioes[regiao]['qtd_clientes'] += int(d.qtd_clientes or 0)
            regioes[regiao]['estados'].append({
                'uf': d.destino_uf,
                'custo': float(d.custo_total or 0),
                'peso': float(d.peso_total or 0),
                'custo_kg': float(d.custo_medio_kg or 0)
            })
        
        # Calcula custo médio por região
        for regiao in regioes.values():
            if regiao['peso_total'] > 0:
                regiao['custo_medio_kg'] = regiao['custo_total'] / regiao['peso_total']
            else:
                regiao['custo_medio_kg'] = 0
        
        return jsonify(list(regioes.values()))
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@bi_bp.route('/api/despesas-por-tipo')
def api_despesas_por_tipo():
    """Retorna análise de despesas por tipo"""
    try:
        # Últimos 60 dias
        hoje = date.today()
        inicio_mes = hoje - timedelta(days=60)
        
        # Busca despesas agregadas
        dados = db.session.query(
            BiDespesaDetalhada.tipo_despesa,
            BiDespesaDetalhada.setor_responsavel,
            func.sum(BiDespesaDetalhada.valor_total).label('valor'),
            func.sum(BiDespesaDetalhada.qtd_ocorrencias).label('qtd')
        ).filter(
            BiDespesaDetalhada.data_referencia >= inicio_mes
        ).group_by(
            BiDespesaDetalhada.tipo_despesa,
            BiDespesaDetalhada.setor_responsavel
        ).order_by(
            desc('valor')
        ).all()
        
        # Agrupa por tipo
        tipos = {}
        for d in dados:
            tipo = d.tipo_despesa
            if tipo not in tipos:
                tipos[tipo] = {
                    'tipo': tipo,
                    'valor_total': 0,
                    'qtd_total': 0,
                    'setores': {}
                }
            
            tipos[tipo]['valor_total'] += float(d.valor or 0)
            tipos[tipo]['qtd_total'] += int(d.qtd or 0)
            
            setor = d.setor_responsavel
            if setor not in tipos[tipo]['setores']:
                tipos[tipo]['setores'][setor] = {
                    'valor': 0,
                    'qtd': 0
                }
            
            tipos[tipo]['setores'][setor]['valor'] += float(d.valor or 0)
            tipos[tipo]['setores'][setor]['qtd'] += int(d.qtd or 0)
        
        # Converte para lista
        resultado = []
        for tipo, dados in tipos.items():
            resultado.append({
                'tipo': tipo,
                'valor': dados['valor_total'],
                'qtd': dados['qtd_total'],
                'setores': [
                    {
                        'nome': setor,
                        'valor': info['valor'],
                        'qtd': info['qtd']
                    }
                    for setor, info in dados['setores'].items()
                ]
            })
        
        return jsonify(resultado)
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@bi_bp.route('/api/custo-por-kg-uf')
def api_custo_por_kg_uf():
    """Retorna custo por kg por UF para mapa"""
    try:
        # Últimos 60 dias
        hoje = date.today()
        inicio_mes = hoje - timedelta(days=60)
        
        # Busca dados por UF
        dados = db.session.query(
            BiFreteAgregado.destino_uf,
            func.avg(BiFreteAgregado.custo_por_kg).label('custo_kg'),
            func.sum(BiFreteAgregado.peso_total_kg).label('peso_total'),
            func.sum(BiFreteAgregado.valor_pago_total).label('valor_total')
        ).filter(
            BiFreteAgregado.data_referencia >= inicio_mes
        ).group_by(
            BiFreteAgregado.destino_uf
        ).all()
        
        resultado = {}
        for d in dados:
            if d.destino_uf:
                resultado[d.destino_uf] = {
                    'custo_kg': float(d.custo_kg or 0),
                    'peso_total': float(d.peso_total or 0),
                    'valor_total': float(d.valor_total or 0)
                }
        
        return jsonify(resultado)
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

# Rotas de processamento ETL

@bi_bp.route('/api/executar-etl', methods=['POST'])
def api_executar_etl():
    """Executa o processo de ETL manualmente"""
    try:
        sucesso = BiETLService.executar_etl_completo()
        
        if sucesso:
            return jsonify({
                'sucesso': True,
                'mensagem': 'ETL executado com sucesso'
            })
        else:
            return jsonify({
                'sucesso': False,
                'mensagem': 'ETL executado com algumas falhas. Verifique os logs.'
            })
    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500

@bi_bp.route('/api/status-etl')
def api_status_etl():
    """Retorna status do último processamento ETL"""
    try:
        # Busca último processamento
        ultimo = db.session.query(
            func.max(BiFreteAgregado.processado_em)
        ).scalar()
        
        if ultimo:
            return jsonify({
                'ultimo_processamento': ultimo.isoformat(),
                'status': 'atualizado' if (agora_utc_naive() - ultimo).days < 1 else 'desatualizado'
            })
        else:
            return jsonify({
                'ultimo_processamento': None,
                'status': 'nunca_executado'
            })
    except Exception as e:
        return jsonify({'erro': str(e)}), 500