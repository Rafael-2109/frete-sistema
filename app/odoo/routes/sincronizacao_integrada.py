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
from flask_login import login_required
import logging

from app import db
from app.odoo.services.sincronizacao_integrada_service import SincronizacaoIntegradaService
from app.odoo.services.pedido_sync_service import PedidoSyncService
from app.separacao.models import Separacao
from sqlalchemy import func

logger = logging.getLogger(__name__)

# Blueprint para sincronização integrada
sync_integrada_bp = Blueprint('sync_integrada', __name__, url_prefix='/odoo/sync-integrada')

# Instância dos serviços
sync_service = SincronizacaoIntegradaService()
pedido_sync_service = PedidoSyncService()

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

        return render_template(
            'odoo/sync_integrada/dashboard.html',
            status=status
        )

    except Exception as e:
        logger.error(f"❌ Erro no dashboard de sincronização integrada: {e}")
        flash(f"❌ Erro ao carregar dashboard: {str(e)}", 'error')
        return redirect(url_for('carteira.dashboard'))


@sync_integrada_bp.route('/pedidos', methods=['GET'])
@login_required
def listar_pedidos_para_sincronizar():
    """
    Tela de listagem de pedidos com saldo para sincronização individual

    Suporta paginação (sem limites)
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 50  # Pedidos por página

        logger.info(f"📋 Carregando lista de pedidos para sincronização (página {page})...")

        # Query paginada
        query = db.session.query(
            Separacao.num_pedido,
            Separacao.raz_social_red,
            Separacao.nome_cidade,
            Separacao.cod_uf,
            Separacao.status,
            func.sum(Separacao.qtd_saldo).label('qtd_total'),
            func.sum(Separacao.valor_saldo).label('valor_total'),
            func.count(Separacao.cod_produto).label('total_itens'),
            func.max(Separacao.expedicao).label('data_expedicao')
        ).filter(
            Separacao.sincronizado_nf == False,
            Separacao.qtd_saldo > 0
        ).group_by(
            Separacao.num_pedido,
            Separacao.raz_social_red,
            Separacao.nome_cidade,
            Separacao.cod_uf,
            Separacao.status
        ).order_by(
            Separacao.num_pedido.desc()
        )

        # Paginação
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        pedidos = pagination.items

        logger.info(f"✅ {len(pedidos)} pedidos carregados (página {page}/{pagination.pages})")

        return render_template(
            'odoo/sync_integrada/listar_pedidos.html',
            pedidos=pedidos,
            pagination=pagination
        )

    except Exception as e:
        logger.error(f"❌ Erro ao listar pedidos para sincronizar: {e}")
        flash(f"❌ Erro ao carregar lista: {str(e)}", 'error')
        return redirect(url_for('sync_integrada.dashboard'))

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


@sync_integrada_bp.route('/sincronizar-pedido/<string:num_pedido>', methods=['POST'])
@login_required
def sincronizar_pedido_individual(num_pedido):
    """
    🔄 SINCRONIZA UM PEDIDO ESPECÍFICO COM O ODOO

    Comportamento:
    - Se encontrado no Odoo: ATUALIZA
    - Se NÃO encontrado no Odoo: EXCLUI (incluindo Separacao com sincronizado_nf=False)
    """
    try:
        logger.info(f"🔄 Sincronizando pedido individual: {num_pedido}")

        # Executar sincronização do pedido específico
        resultado = pedido_sync_service.sincronizar_pedido_especifico(num_pedido)

        # Processar resultado e mostrar feedback
        if resultado.get('sucesso'):
            acao = resultado.get('acao')
            mensagem = resultado.get('mensagem')
            tempo = resultado.get('tempo_execucao', 0)

            if acao == 'ATUALIZADO':
                flash(f"✅ {mensagem} ({tempo:.2f}s)", 'success')

                # Mostrar detalhes se houver
                detalhes = resultado.get('detalhes', {})
                if detalhes.get('itens_processados'):
                    flash(f"📦 {detalhes['itens_processados']} itens processados", 'info')

                alteracoes = detalhes.get('alteracoes', [])
                if alteracoes:
                    flash(f"🔄 {len(alteracoes)} alterações aplicadas", 'info')

            elif acao == 'EXCLUIDO':
                flash(f"🗑️ {mensagem} ({tempo:.2f}s)", 'warning')
                flash(f"✅ Todas as Separacao (sincronizado_nf=False) foram excluídas", 'info')

            else:
                flash(f"ℹ️ {mensagem}", 'info')

        else:
            erro = resultado.get('mensagem', 'Erro desconhecido')
            flash(f"❌ Erro ao sincronizar pedido: {erro}", 'error')

        return redirect(url_for('sync_integrada.dashboard'))

    except Exception as e:
        logger.error(f"❌ Erro ao sincronizar pedido {num_pedido}: {e}")
        flash(f"❌ Erro ao sincronizar pedido: {str(e)}", 'error')
        return redirect(url_for('sync_integrada.dashboard'))