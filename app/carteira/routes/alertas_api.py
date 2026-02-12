"""
API de Alertas Críticos da Carteira
===================================

API JSON para verificação em tempo real de alertas críticos detectados
durante sincronizações com Odoo.

NOTA: O dashboard visual está em alertas_visualizacao.py (/carteira/alertas/dashboard)
Este módulo fornece apenas endpoints de API JSON.
"""

from flask import Blueprint, jsonify, redirect, url_for
from flask_login import login_required
from app.utils.logging_config import logger
from app.carteira.alert_system import AlertaSistemaCarteira
from app.notificacoes.models import AlertaNotificacao
from datetime import datetime, timedelta
from app import db
from app.utils.timezone import agora_utc_naive

# Blueprint para API de alertas (apenas endpoints JSON)
alertas_bp = Blueprint('alertas', __name__, url_prefix='/carteira/alertas')


@alertas_bp.route('/')
@login_required
def dashboard_alertas():
    """
    Redireciona para o dashboard visual em alertas_visualizacao.

    Esta rota existe para manter compatibilidade com links antigos.
    O dashboard real está em /carteira/alertas/dashboard.
    """
    return redirect(url_for('carteira.alertas_visualizacao.dashboard'))

@alertas_bp.route('/api/verificar')
@login_required
def api_verificar_alertas():
    """
    API para verificação em tempo real dos alertas.

    Verifica:
    - Separações COTADAS que podem ser afetadas por sincronização
    - Histórico de alertas recentes (últimas 24h)

    Returns:
        JSON: {sucesso, alertas, timestamp}
    """
    try:
        alertas = _executar_verificacoes_completas()
        return jsonify({
            'sucesso': True,
            'alertas': alertas,
            'timestamp': agora_utc_naive().isoformat()
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
    """
    Retorna detalhes específicos de um tipo de alerta.

    Args:
        tipo_alerta: 'separacoes_cotadas' ou 'historico_recente'

    Returns:
        JSON: {sucesso, tipo, detalhes}
    """
    try:
        if tipo_alerta == 'separacoes_cotadas':
            detalhes = _detalhar_separacoes_cotadas()
        elif tipo_alerta == 'historico_recente':
            detalhes = _buscar_historico_alertas(horas=24)
        else:
            return jsonify({
                'erro': f'Tipo de alerta inválido: {tipo_alerta}. Tipos válidos: separacoes_cotadas, historico_recente'
            }), 400

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
    """
    Executa todas as verificações de alertas críticos.

    Verificações realizadas:
    1. Separações COTADAS em risco (via AlertaSistemaCarteira)
    2. Histórico de alertas recentes (últimas 24h)

    Returns:
        dict: Estrutura com alertas e recomendações
    """
    alertas = {
        'separacoes_cotadas': {
            'quantidade': 0,
            'nivel': 'OK',
            'mensagem': 'Nenhuma separação cotada em risco',
            'separacoes_afetadas': []
        },
        'historico_recente': {
            'quantidade': 0,
            'nivel': 'OK',
            'mensagem': 'Nenhum alerta nas últimas 24h',
            'alertas_recentes': []
        },
        'total_criticos': 0,
        'recomendacoes': []
    }

    try:
        # 1. Verificar separações cotadas (usa AlertaSistemaCarteira existente)
        resultado_cotadas = AlertaSistemaCarteira.verificar_separacoes_cotadas_antes_sincronizacao()
        if resultado_cotadas.get('alertas'):
            alertas['separacoes_cotadas']['quantidade'] = resultado_cotadas.get('quantidade', 0)
            alertas['separacoes_cotadas']['nivel'] = 'CRÍTICO'
            alertas['separacoes_cotadas']['mensagem'] = resultado_cotadas.get('mensagem', 'Separações cotadas detectadas')
            alertas['separacoes_cotadas']['separacoes_afetadas'] = resultado_cotadas.get('separacoes_afetadas', [])
            alertas['total_criticos'] += 1
            alertas['recomendacoes'].append('Verifique separações COTADAS antes de sincronizar')

        # 2. Buscar histórico de alertas recentes (últimas 24h)
        historico = _buscar_historico_alertas(horas=24)
        alertas_criticos = [h for h in historico if h.get('nivel') == 'CRITICO']

        if alertas_criticos:
            alertas['historico_recente']['quantidade'] = len(alertas_criticos)
            alertas['historico_recente']['nivel'] = 'ATENÇÃO'
            alertas['historico_recente']['mensagem'] = f'{len(alertas_criticos)} alerta(s) crítico(s) nas últimas 24h'
            alertas['historico_recente']['alertas_recentes'] = alertas_criticos[:10]  # Limita a 10

    except Exception as e:
        logger.error(f"Erro nas verificações: {e}")
        alertas['erro'] = str(e)

    return alertas

def _detalhar_separacoes_cotadas():
    """Retorna detalhes completos das separações cotadas"""
    from app.separacao.models import Separacao
    
    # MIGRADO: Removido JOIN com Pedido VIEW, usa campos direto de Separacao
    # Buscar todas as separações cotadas com detalhes
    separacoes = db.session.query(
        Separacao.separacao_lote_id,
        Separacao.num_pedido,
        Separacao.cod_produto,
        Separacao.nome_produto,
        Separacao.qtd_saldo,
        Separacao.expedicao,
        Separacao.raz_social_red.label('cliente'),
        Separacao.data_pedido
    ).filter(
        Separacao.status == 'COTADO',
        Separacao.sincronizado_nf == False  # Garantir que não foi sincronizado
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

def _buscar_historico_alertas(horas=24):
    """
    Busca histórico REAL de alertas nas últimas X horas.

    Consulta a tabela alerta_notificacoes para obter alertas reais
    que foram gerados pelo sistema (alert_system, sincronização, etc).

    Args:
        horas: Número de horas para buscar histórico (default: 24)

    Returns:
        Lista de dicts com formato:
        - timestamp: Data/hora do alerta (formato brasileiro)
        - tipo: Tipo do alerta (SEPARACOES_COTADAS, etc)
        - quantidade: Quantidade de itens afetados (do campo dados)
        - resolvido: True se status_envio == 'lido'
        - id: ID do alerta (para futuras ações)
        - nivel: Nível de severidade (CRITICO, ATENCAO, INFO)
    """
    try:
        # Calcular limite de tempo
        data_limite = agora_utc_naive() - timedelta(hours=horas)

        # Buscar alertas do período
        alertas = AlertaNotificacao.query.filter(
            AlertaNotificacao.criado_em >= data_limite
        ).order_by(
            AlertaNotificacao.criado_em.desc()
        ).limit(100).all()

        # Se não houver alertas, retornar lista vazia
        if not alertas:
            return []

        # Formatar para o frontend
        historico = []
        for alerta in alertas:
            # Extrair quantidade do campo dados (JSON)
            dados = alerta.dados or {}
            quantidade = (
                dados.get('quantidade') or
                dados.get('total') or
                len(dados.get('separacoes_afetadas', [])) or
                len(dados.get('itens', [])) or
                1  # Default: 1 se não encontrar
            )

            historico.append({
                'timestamp': alerta.criado_em.strftime('%d/%m/%Y %H:%M') if alerta.criado_em else None,
                'tipo': alerta.tipo,
                'quantidade': quantidade,
                'resolvido': alerta.status_envio == 'lido',
                'id': alerta.id,
                'nivel': alerta.nivel,
                'titulo': alerta.titulo,
                'mensagem': alerta.mensagem[:100] + '...' if len(alerta.mensagem or '') > 100 else alerta.mensagem
            })

        return historico

    except Exception as e:
        logger.error(f"Erro ao buscar histórico de alertas: {e}")
        # Em caso de erro, retornar lista vazia (fail-safe)
        return []