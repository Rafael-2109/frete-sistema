"""
Rotas de Sincronização Integrada Segura
=======================================

Implementa sincronização na SEQUÊNCIA CORRETA:
FATURAMENTO → CARTEIRA

Elimina risco humano de executar na ordem errada.

Autor: Sistema de Fretes  
Data: 2025-07-21
"""

from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime
import logging

from app.utils.auth_decorators import require_admin
from app.odoo.services.sincronizacao_integrada_service import SincronizacaoIntegradaService

logger = logging.getLogger(__name__)

# Blueprint para sincronização integrada
sync_integrada_bp = Blueprint('sync_integrada', __name__, url_prefix='/odoo/sync-integrada')

# Instância do serviço
sync_service = SincronizacaoIntegradaService()

@sync_integrada_bp.route('/')
@login_required
def dashboard():
    """
    Dashboard principal da sincronização integrada segura
    """
    try:
        logger.info("📊 Carregando dashboard de sincronização integrada...")
        
        # Verificar status atual do sistema
        status = sync_service.verificar_status_sincronizacao()
        
        return render_template('odoo/sync_integrada/dashboard.html', status=status)
        
    except Exception as e:
        logger.error(f"❌ Erro no dashboard de sincronização integrada: {e}")
        flash(f"❌ Erro ao carregar dashboard: {str(e)}", 'error')
        return redirect(url_for('carteira.dashboard'))

@sync_integrada_bp.route('/executar', methods=['POST'])
@login_required
def executar_sincronizacao_segura():
    """
    🔄 EXECUTA SINCRONIZAÇÃO INTEGRADA SEGURA
    
    Sequência FIXA e SEGURA:
    1. FATURAMENTO primeiro
    2. CARTEIRA depois
    
    Elimina risco de perda de dados por ordem incorreta
    """
    try:
        # Parâmetros da requisição
        usar_filtro_carteira = request.form.get('usar_filtro_carteira') == 'on'
        
        logger.info(f"🚀 INICIANDO sincronização integrada segura (filtro carteira: {usar_filtro_carteira})")
        
        # ✅ EXECUTAR SINCRONIZAÇÃO INTEGRADA
        resultado = sync_service.executar_sincronizacao_completa_segura(
            usar_filtro_carteira=usar_filtro_carteira
        )
        
        # ✅ PROCESSAR RESULTADO E MOSTRAR FEEDBACK DETALHADO
        if resultado.get('sucesso') or resultado.get('sucesso_parcial'):
            # Sucesso total ou parcial
            stats = resultado.get('estatisticas', {})
            etapas = resultado.get('etapas_executadas', [])
            
            # Mensagem principal
            if resultado.get('operacao_completa'):
                flash(f"✅ SINCRONIZAÇÃO INTEGRADA COMPLETA!", 'success')
                flash(f"🔄 Sequência segura executada: FATURAMENTO → CARTEIRA", 'success')
            else:
                flash(f"⚠️ SINCRONIZAÇÃO PARCIAL concluída", 'warning')
            
            # Estatísticas de tempo
            tempo_total = resultado.get('tempo_total', 0)
            flash(f"⏱️ Operação concluída em {tempo_total}s", 'info')
            
            # Resultados do faturamento
            fat_resultado = resultado.get('faturamento_resultado', {})
            if fat_resultado.get('sucesso'):
                fat_registros = fat_resultado.get('registros_importados', 0)
                movimentacoes_criadas = fat_resultado.get('movimentacoes_criadas', 0)
                
                if fat_resultado.get('simulado'):
                    flash(f"📊 Faturamento: Sincronização simulada (implementar método real)", 'info')
                else:
                    flash(f"📊 Faturamento: {fat_registros} registros sincronizados", 'success')
                    if movimentacoes_criadas > 0:
                        flash(f"🏭 Estoque: {movimentacoes_criadas} movimentações criadas automaticamente", 'success')
                    
                    # Detalhes do processamento de estoque
                    detalhes_estoque = fat_resultado.get('detalhes_estoque', {})
                    if detalhes_estoque.get('processadas', 0) > 0:
                        casos = []
                        if detalhes_estoque.get('caso1_direto', 0) > 0:
                            casos.append(f"{detalhes_estoque['caso1_direto']} diretas")
                        if detalhes_estoque.get('caso2_parcial', 0) > 0:
                            casos.append(f"{detalhes_estoque['caso2_parcial']} com divergência")
                        if detalhes_estoque.get('caso3_cancelado', 0) > 0:
                            casos.append(f"{detalhes_estoque['caso3_cancelado']} canceladas")
                        
                        if casos:
                            flash(f"📋 Processamento: {', '.join(casos)}", 'info')
            else:
                flash(f"❌ Faturamento: {fat_resultado.get('erro', 'Erro desconhecido')}", 'error')
            
            # Resultados da carteira
            cart_resultado = resultado.get('carteira_resultado', {})
            if cart_resultado.get('sucesso'):
                cart_stats = cart_resultado.get('estatisticas', {})
                registros_inseridos = cart_stats.get('registros_inseridos', 0)
                registros_removidos = cart_stats.get('registros_removidos', 0)
                recomposicoes = cart_stats.get('recomposicao_sucesso', 0)
                
                flash(f"🔄 Carteira: {registros_inseridos} inseridos, {registros_removidos} removidos", 'success')
                if recomposicoes > 0:
                    flash(f"🔄 Pré-separações: {recomposicoes} recompostas automaticamente", 'success')
                
                # Alertas da carteira se houver
                alertas_pre = cart_resultado.get('alertas_pre_sync', {})
                if alertas_pre.get('total_alertas', 0) > 0:
                    flash(f"⚠️ {alertas_pre['total_alertas']} alertas detectados (já protegidos)", 'warning')
                
            else:
                flash(f"❌ Carteira: {cart_resultado.get('erro', 'Erro desconhecido')}", 'error')
            
            # Alertas gerais se houver
            alertas_gerais = resultado.get('alertas', [])
            for alerta in alertas_gerais[:3]:  # Máximo 3 alertas
                nivel = alerta.get('nivel', 'INFO')
                mensagem = alerta.get('mensagem', 'Alerta sem detalhes')
                
                if nivel == 'ERRO':
                    flash(f"❌ {mensagem}", 'error')
                elif nivel == 'AVISO':
                    flash(f"⚠️ {mensagem}", 'warning')
                else:
                    flash(f"ℹ️ {mensagem}", 'info')
            
            # Informações de segurança
            if stats.get('sequencia_segura_executada'):
                flash(f"🛡️ Sequência segura executada - risco de perda de NFs ELIMINADO", 'success')
        
        else:
            # ❌ FALHA COMPLETA
            erro = resultado.get('erro', 'Erro desconhecido')
            tempo_erro = resultado.get('tempo_total', 0)
            etapas = resultado.get('etapas_executadas', [])
            
            flash(f"❌ FALHA na sincronização integrada: {erro}", 'error')
            flash(f"⏱️ Processo interrompido após {tempo_erro}s", 'error')
            
            # Mostrar em que etapa falhou
            if etapas:
                ultima_etapa = etapas[-1] if etapas else 'INICIO'
                flash(f"🔍 Falha na etapa: {ultima_etapa}", 'warning')
        
        return redirect(url_for('sync_integrada.dashboard'))
        
    except Exception as e:
        logger.error(f"❌ ERRO CRÍTICO na execução da sincronização integrada: {e}")
        flash(f"❌ ERRO CRÍTICO: {str(e)}", 'error')
        flash("🔧 Contate o administrador do sistema se o erro persistir", 'error')
        return redirect(url_for('sync_integrada.dashboard'))

@sync_integrada_bp.route('/status', methods=['GET'])
@login_required
def verificar_status():
    """
    API para verificar status atual do sistema
    """
    try:
        status = sync_service.verificar_status_sincronizacao()
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"❌ Erro ao verificar status: {e}")
        return jsonify({
            'erro': str(e),
            'pode_sincronizar': False,
            'nivel_risco': 'ALTO'
        }), 500

@sync_integrada_bp.route('/widget')
@login_required
def widget_sincronizacao():
    """
    Widget de sincronização para incluir em outras páginas
    """
    try:
        status = sync_service.verificar_status_sincronizacao()
        return render_template('odoo/sync_integrada/widget.html', status=status)
        
    except Exception as e:
        logger.error(f"❌ Erro no widget: {e}")
        return render_template('odoo/sync_integrada/widget.html', status={
            'erro': str(e),
            'pode_sincronizar': False
        })