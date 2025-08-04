"""
API de Alertas Críticos da Carteira
===================================

Sistema de visualização e gerenciamento de alertas críticos detectados
durante sincronizações com Odoo.
"""

from flask import Blueprint, jsonify, render_template
from flask_login import login_required
from app.utils.logging_config import logger
from app.odoo.services.carteira_service import CarteiraService
from app.carteira.alert_system import AlertaSistemaCarteira
from datetime import datetime, timedelta
from app import db

# Blueprint para alertas
alertas_bp = Blueprint('alertas', __name__, url_prefix='/carteira/alertas')

@alertas_bp.route('/')
@login_required
def dashboard_alertas():
    """Dashboard principal de alertas críticos"""
    try:
        # Verificações em tempo real
        alertas = _executar_verificacoes_completas()
        
        # Histórico de alertas (últimas 24h)
        historico = _buscar_historico_alertas(horas=24)
        
        return render_template('carteira/alertas_dashboard.html',
                             alertas=alertas,
                             historico=historico,
                             timestamp=datetime.now())
                             
    except Exception as e:
        logger.error(f"Erro ao carregar dashboard de alertas: {e}")
        # Retornar estrutura completa mesmo em caso de erro
        alertas_vazio = {
            'separacoes_cotadas': {
                'quantidade': 0,
                'nivel': 'ERRO',
                'mensagem': 'Erro ao verificar separações',
                'separacoes_afetadas': []
            },
            'faturamento_pendente': {
                'quantidade': 0,
                'nivel': 'ERRO',
                'mensagem': 'Erro ao verificar faturamento',
                'pedidos_afetados': [],
                'percentual_risco': 0
            },
            'total_criticos': 0,
            'recomendacoes': []
        }
        return render_template('carteira/alertas_dashboard.html',
                             erro=str(e),
                             alertas=alertas_vazio,
                             historico=[])

@alertas_bp.route('/api/verificar')
@login_required
def api_verificar_alertas():
    """API para verificação em tempo real dos alertas"""
    try:
        alertas = _executar_verificacoes_completas()
        return jsonify({
            'sucesso': True,
            'alertas': alertas,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Erro na API de alertas: {e}")
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500

@alertas_bp.route('/api/detalhes/<tipo_alerta>')
@login_required
def api_detalhes_alerta(tipo_alerta):
    """Retorna detalhes específicos de um tipo de alerta"""
    try:
        if tipo_alerta == 'separacoes_cotadas':
            detalhes = _detalhar_separacoes_cotadas()
        elif tipo_alerta == 'faturamento_pendente':
            detalhes = _detalhar_faturamento_pendente()
        else:
            return jsonify({'erro': 'Tipo de alerta inválido'}), 400
            
        return jsonify({
            'sucesso': True,
            'tipo': tipo_alerta,
            'detalhes': detalhes
        })
    except Exception as e:
        logger.error(f"Erro ao detalhar alerta {tipo_alerta}: {e}")
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500

def _executar_verificacoes_completas():
    """Executa todas as verificações de alertas críticos"""
    alertas = {
        'separacoes_cotadas': {
            'quantidade': 0,
            'nivel': 'OK',
            'mensagem': 'Nenhuma separação cotada em risco',
            'separacoes_afetadas': []
        },
        'faturamento_pendente': {
            'quantidade': 0,
            'nivel': 'OK',
            'mensagem': 'Nenhum faturamento pendente crítico',
            'pedidos_afetados': [],
            'percentual_risco': 0
        },
        'total_criticos': 0,
        'recomendacoes': []
    }
    
    try:
        # 1. Verificar separações cotadas
        resultado_cotadas = AlertaSistemaCarteira.verificar_separacoes_cotadas_antes_sincronizacao()
        if resultado_cotadas.get('alertas'):
            alertas['separacoes_cotadas']['quantidade'] = resultado_cotadas.get('quantidade', 0)
            alertas['separacoes_cotadas']['nivel'] = 'CRÍTICO'
            alertas['separacoes_cotadas']['mensagem'] = resultado_cotadas.get('mensagem', 'Separações cotadas detectadas')
            alertas['separacoes_cotadas']['separacoes_afetadas'] = resultado_cotadas.get('separacoes_afetadas', [])
            alertas['total_criticos'] += 1
            
        # 2. Verificar faturamento pendente
        service = CarteiraService()
        risco_faturamento = service._verificar_risco_faturamento_pendente()
        
        if risco_faturamento.get('risco_alto'):
            alertas['faturamento_pendente']['quantidade'] = risco_faturamento.get('pedidos_em_risco', 0)
            alertas['faturamento_pendente']['nivel'] = 'CRÍTICO'
            alertas['faturamento_pendente']['mensagem'] = risco_faturamento.get('mensagem', 'Faturamento pendente detectado')
            alertas['faturamento_pendente']['pedidos_afetados'] = risco_faturamento.get('lista_pedidos', [])
            alertas['faturamento_pendente']['percentual_risco'] = risco_faturamento.get('percentual_risco', 0)
            alertas['total_criticos'] += 1
            alertas['recomendacoes'].append('Execute sincronização de FATURAMENTO antes da carteira')
            
    except Exception as e:
        logger.error(f"Erro nas verificações: {e}")
        alertas['erro'] = str(e)
        
    return alertas

def _detalhar_separacoes_cotadas():
    """Retorna detalhes completos das separações cotadas"""
    from app.separacao.models import Separacao
    from app.pedidos.models import Pedido
    
    # Buscar todas as separações cotadas com detalhes
    separacoes = db.session.query(
        Separacao.separacao_lote_id,
        Separacao.num_pedido,
        Separacao.cod_produto,
        Separacao.nome_produto,
        Separacao.qtd_saldo,
        Separacao.expedicao,
        Pedido.raz_social_red.label('cliente'),
        Pedido.data_pedido
    ).join(
        Pedido, Separacao.separacao_lote_id == Pedido.separacao_lote_id
    ).filter(
        Pedido.status == 'COTADO'
    ).all()
    
    detalhes = []
    for sep in separacoes:
        detalhes.append({
            'lote_id': sep.separacao_lote_id,
            'num_pedido': sep.num_pedido,
            'cod_produto': sep.cod_produto,
            'nome_produto': sep.nome_produto,
            'qtd_saldo': float(sep.qtd_saldo),
            'expedicao': sep.expedicao.strftime('%Y-%m-%d') if sep.expedicao else None,
            'cliente': sep.cliente,
            'data_cotacao': sep.data_pedido.strftime('%Y-%m-%d') if sep.data_pedido else None
        })
        
    return detalhes

def _detalhar_faturamento_pendente():
    """Retorna detalhes dos pedidos cotados sem faturamento"""
    service = CarteiraService()
    risco = service._verificar_risco_faturamento_pendente()
    
    if not risco.get('lista_pedidos'):
        return []
        
    # Enriquecer com mais detalhes
    from app.pedidos.models import Pedido
    detalhes = []
    
    for item in risco['lista_pedidos']:
        pedido = Pedido.query.filter_by(
            num_pedido=item['num_pedido']
        ).first()
        
        if pedido:
            detalhes.append({
                **item,
                'cliente': pedido.raz_social_red,
                'data_pedido': pedido.data_pedido.strftime('%Y-%m-%d') if pedido.data_pedido else None,
                'valor_pedido': float(pedido.valor_saldo_total) if pedido.valor_saldo_total else 0
            })
        else:
            detalhes.append(item)
            
    return detalhes

def _buscar_historico_alertas(horas=24):
    """Busca histórico de alertas nas últimas X horas"""
    # Por enquanto retorna dados mockados
    # TODO: Implementar tabela de histórico de alertas
    return [
        {
            'timestamp': (datetime.now() - timedelta(hours=2)).strftime('%Y-%m-%d %H:%M'),
            'tipo': 'SEPARACOES_COTADAS',
            'quantidade': 205,
            'resolvido': False
        },
        {
            'timestamp': (datetime.now() - timedelta(hours=5)).strftime('%Y-%m-%d %H:%M'),
            'tipo': 'FATURAMENTO_PENDENTE',
            'quantidade': 38,
            'resolvido': True
        }
    ]