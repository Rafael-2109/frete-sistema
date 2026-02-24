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
from app.carteira.models import CarteiraPrincipal
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

    ✅ BUSCA DA CARTEIRA PRINCIPAL (fonte da verdade)
    - Apenas pedidos com qtd_saldo_produto_pedido > 0
    - Permite sincronizar pedidos que ainda não viraram Separação

    Suporta paginação e filtros
    """
    try:
        # Parâmetros de paginação
        page = request.args.get('page', 1, type=int)
        per_page = 50  # Pedidos por página

        # Parâmetros de filtro
        filtro_pedido = request.args.get('num_pedido', '').strip()
        filtro_cliente = request.args.get('cliente', '').strip()
        filtro_cidade = request.args.get('cidade', '').strip()
        filtro_uf = request.args.get('uf', '').strip()

        logger.info(f"📋 Carregando lista de pedidos da CARTEIRA PRINCIPAL para sincronização (página {page})...")

        # ✅ QUERY DA CARTEIRA PRINCIPAL: Apenas pedidos com saldo > 0
        query = db.session.query(
            CarteiraPrincipal.num_pedido,
            CarteiraPrincipal.raz_social_red,
            CarteiraPrincipal.nome_cidade,
            CarteiraPrincipal.cod_uf,
            CarteiraPrincipal.status_pedido.label('status'),
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido).label('qtd_total'),
            func.sum(
                CarteiraPrincipal.qtd_saldo_produto_pedido *
                CarteiraPrincipal.preco_produto_pedido
            ).label('valor_total'),
            func.count(CarteiraPrincipal.cod_produto).label('total_itens'),
            # NOTA: Campo expedicao foi REMOVIDO de CarteiraPrincipal - usar data_pedido
            func.max(CarteiraPrincipal.data_pedido).label('data_expedicao')
        ).filter(
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0  # ✅ Apenas itens com saldo
        )

        # Aplicar filtros se fornecidos
        if filtro_pedido:
            query = query.filter(CarteiraPrincipal.num_pedido.ilike(f'%{filtro_pedido}%'))
            logger.info(f"   🔍 Filtro pedido: {filtro_pedido}")

        if filtro_cliente:
            query = query.filter(CarteiraPrincipal.raz_social_red.ilike(f'%{filtro_cliente}%'))
            logger.info(f"   🔍 Filtro cliente: {filtro_cliente}")

        if filtro_cidade:
            query = query.filter(CarteiraPrincipal.nome_cidade.ilike(f'%{filtro_cidade}%'))
            logger.info(f"   🔍 Filtro cidade: {filtro_cidade}")

        if filtro_uf:
            query = query.filter(CarteiraPrincipal.cod_uf == filtro_uf.upper())
            logger.info(f"   🔍 Filtro UF: {filtro_uf}")

        # Agrupar e ordenar
        query = query.group_by(
            CarteiraPrincipal.num_pedido,
            CarteiraPrincipal.raz_social_red,
            CarteiraPrincipal.nome_cidade,
            CarteiraPrincipal.cod_uf,
            CarteiraPrincipal.status_pedido
        ).order_by(
            CarteiraPrincipal.num_pedido.desc()
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
            pagination=pagination,
            filtro_pedido=filtro_pedido,
            filtro_cliente=filtro_cliente,
            filtro_cidade=filtro_cidade,
            filtro_uf=filtro_uf
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
        periodo_minutos = request.form.get('periodo_recuperacao', 11520, type=int)
        # Clampar entre 120 (2h) e 43200 (30d) para segurança
        periodo_minutos = max(120, min(43200, periodo_minutos))

        logger.info(f"🚀 INICIANDO sincronização integrada segura (filtro carteira: {usar_filtro_carteira}, período: {periodo_minutos} min)")

        # ✅ EXECUTAR SINCRONIZAÇÃO INTEGRADA
        resultado = sync_service.executar_sincronizacao_completa_segura(
            usar_filtro_carteira=usar_filtro_carteira,
            periodo_minutos=periodo_minutos
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


# ============================================================================
# ROTAS: IMPORTAÇÃO FALLBACK (2º FALLBACK)
# ============================================================================

@sync_integrada_bp.route('/fallback')
@login_required
def fallback_dashboard():
    """
    Dashboard de importação fallback

    Permite importar pedidos e NFs do Odoo que não foram
    capturados pela sincronização automática.
    """
    try:
        logger.info("📥 Carregando dashboard de importação fallback...")
        return render_template('odoo/sync_integrada/fallback.html')

    except Exception as e:
        logger.error(f"❌ Erro no dashboard fallback: {e}")
        flash(f"❌ Erro ao carregar dashboard: {str(e)}", 'error')
        return redirect(url_for('sync_integrada.dashboard'))


@sync_integrada_bp.route('/fallback/importar-pedido', methods=['POST'])
@login_required
def importar_pedido_fallback():
    """
    Importa um pedido específico do Odoo (2º fallback)

    Funciona mesmo se o pedido NÃO existir no sistema local.
    Útil para pedidos com tipos não filtrados (ex: venda-industrializacao)
    """
    try:
        from app.odoo.services.importacao_fallback_service import ImportacaoFallbackService

        num_pedido = request.form.get('num_pedido', '').strip().upper()

        if not num_pedido:
            flash("❌ Número do pedido é obrigatório", 'error')
            return redirect(url_for('sync_integrada.fallback_dashboard'))

        logger.info(f"📥 Importação fallback do pedido: {num_pedido}")

        service = ImportacaoFallbackService()
        resultado = service.importar_pedido_por_numero(num_pedido)

        if resultado.get('sucesso'):
            dados = resultado.get('dados_odoo', {})
            tempo = resultado.get('tempo_execucao', 0)

            flash(f"✅ Pedido {num_pedido} importado com sucesso ({tempo:.2f}s)", 'success')

            if dados:
                flash(f"📦 Cliente: {dados.get('cliente', ['', 'N/A'])[1] if isinstance(dados.get('cliente'), list) else 'N/A'}", 'info')
                flash(f"📝 Tipo: {dados.get('tipo_pedido', 'N/A')}", 'info')
                flash(f"💰 Valor: R$ {dados.get('valor_total', 0):,.2f}", 'info')
        else:
            flash(f"❌ {resultado.get('mensagem', 'Erro ao importar pedido')}", 'error')

        return redirect(url_for('sync_integrada.fallback_dashboard'))

    except Exception as e:
        logger.error(f"❌ Erro na importação fallback: {e}")
        flash(f"❌ Erro ao importar pedido: {str(e)}", 'error')
        return redirect(url_for('sync_integrada.fallback_dashboard'))


@sync_integrada_bp.route('/fallback/importar-pedidos-por-data', methods=['POST'])
@login_required
def importar_pedidos_por_data_fallback():
    """
    Importa pedidos do Odoo por data de criação (2º fallback)
    """
    try:
        from app.odoo.services.importacao_fallback_service import ImportacaoFallbackService

        data_inicio = request.form.get('data_inicio', '').strip()
        data_fim = request.form.get('data_fim', '').strip() or None

        if not data_inicio:
            flash("❌ Data inicial é obrigatória", 'error')
            return redirect(url_for('sync_integrada.fallback_dashboard'))

        logger.info(f"📥 Importação fallback por data: {data_inicio} a {data_fim}")

        service = ImportacaoFallbackService()
        resultado = service.importar_pedidos_por_data(data_inicio, data_fim)

        if resultado.get('sucesso'):
            total = resultado.get('total_encontrados', 0)
            tempo = resultado.get('tempo_execucao', 0)

            if total > 0:
                flash(f"✅ {total} pedidos encontrados e importados ({tempo:.2f}s)", 'success')

                pedidos = resultado.get('pedidos_encontrados', [])
                if pedidos and len(pedidos) <= 10:
                    flash(f"📦 Pedidos: {', '.join(pedidos)}", 'info')
                elif pedidos:
                    flash(f"📦 Primeiros 10: {', '.join(pedidos[:10])}...", 'info')
            else:
                flash(f"ℹ️ Nenhum pedido encontrado no período", 'info')
        else:
            flash(f"❌ {resultado.get('mensagem', 'Erro ao importar pedidos')}", 'error')

        return redirect(url_for('sync_integrada.fallback_dashboard'))

    except Exception as e:
        logger.error(f"❌ Erro na importação fallback por data: {e}")
        flash(f"❌ Erro ao importar pedidos: {str(e)}", 'error')
        return redirect(url_for('sync_integrada.fallback_dashboard'))


@sync_integrada_bp.route('/fallback/importar-faturamento', methods=['POST'])
@login_required
def importar_faturamento_fallback():
    """
    Importa uma NF específica do Odoo (fallback de faturamento)
    """
    try:
        from app.odoo.services.importacao_fallback_service import ImportacaoFallbackService

        numero_nf = request.form.get('numero_nf', '').strip()

        if not numero_nf:
            flash("❌ Número da NF é obrigatório", 'error')
            return redirect(url_for('sync_integrada.fallback_dashboard'))

        logger.info(f"📥 Importação fallback da NF: {numero_nf}")

        service = ImportacaoFallbackService()
        resultado = service.importar_faturamento_por_nf(numero_nf)

        if resultado.get('sucesso'):
            itens = resultado.get('itens_importados', 0)
            tempo = resultado.get('tempo_execucao', 0)
            dados = resultado.get('dados_nf', {})

            if resultado.get('cancelada'):
                flash(f"🚨 NF {numero_nf} cancelada localmente ({tempo:.2f}s)", 'warning')
            elif itens > 0:
                flash(f"✅ NF {numero_nf} importada: {itens} itens ({tempo:.2f}s)", 'success')
            else:
                flash(f"ℹ️ NF {numero_nf} já existe no sistema ou não tem itens", 'info')

            if dados and not resultado.get('cancelada'):
                flash(f"📝 Origem: {dados.get('origem', 'N/A')}", 'info')
        else:
            if resultado.get('cancelada'):
                flash(f"⚠️ {resultado.get('mensagem', 'NF cancelada no Odoo')}", 'warning')
            else:
                flash(f"❌ {resultado.get('mensagem', 'Erro ao importar NF')}", 'error')

        return redirect(url_for('sync_integrada.fallback_dashboard'))

    except Exception as e:
        logger.error(f"❌ Erro na importação fallback da NF: {e}")
        flash(f"❌ Erro ao importar NF: {str(e)}", 'error')
        return redirect(url_for('sync_integrada.fallback_dashboard'))


@sync_integrada_bp.route('/fallback/importar-faturamento-por-periodo', methods=['POST'])
@login_required
def importar_faturamento_por_periodo_fallback():
    """
    Importa NFs do Odoo por período (fallback de faturamento)
    """
    try:
        from app.odoo.services.importacao_fallback_service import ImportacaoFallbackService

        data_inicio = request.form.get('data_inicio', '').strip()
        data_fim = request.form.get('data_fim', '').strip() or None

        if not data_inicio:
            flash("❌ Data inicial é obrigatória", 'error')
            return redirect(url_for('sync_integrada.fallback_dashboard'))

        logger.info(f"📥 Importação fallback de faturamento: {data_inicio} a {data_fim}")

        service = ImportacaoFallbackService()
        resultado = service.importar_faturamento_por_periodo_batch(data_inicio, data_fim)

        if resultado.get('sucesso'):
            total = resultado.get('total_encontradas', 0)
            importadas = resultado.get('total_importadas', 0)
            canceladas = resultado.get('total_canceladas', 0)
            ignoradas_cancel = resultado.get('total_ignoradas_cancel', 0)
            erros = resultado.get('total_erros', 0)
            tempo = resultado.get('tempo_execucao', 0)

            if total > 0:
                if importadas > 0:
                    flash(f"✅ {importadas}/{total} NFs importadas ({tempo:.2f}s)", 'success')
                if canceladas > 0:
                    flash(f"🚨 {canceladas} NFs canceladas no Odoo — status atualizado localmente", 'warning')
                if ignoradas_cancel > 0:
                    flash(f"ℹ️ {ignoradas_cancel} NFs canceladas no Odoo sem registro local (ignoradas)", 'info')
                if erros > 0:
                    flash(f"⚠️ {erros} NFs com erro", 'warning')
                if importadas == 0 and canceladas == 0:
                    flash(f"ℹ️ Todas as {total} NFs do período já existem no sistema ({tempo:.2f}s)", 'info')
            else:
                flash(f"ℹ️ Nenhuma NF encontrada no período", 'info')
        else:
            flash(f"❌ {resultado.get('mensagem', 'Erro ao importar faturamento')}", 'error')

        return redirect(url_for('sync_integrada.fallback_dashboard'))

    except Exception as e:
        logger.error(f"❌ Erro na importação fallback de faturamento: {e}")
        flash(f"❌ Erro ao importar faturamento: {str(e)}", 'error')
        return redirect(url_for('sync_integrada.fallback_dashboard'))


@sync_integrada_bp.route('/fallback/reparar-orfaos', methods=['POST'])
@login_required
def reparar_orfaos_faturamento():
    """
    Repara NFs orfas: existem em FaturamentoProduto mas nao em RelatorioFaturamentoImportado.
    Scan completo — uso manual via dashboard fallback.
    """
    try:
        from app.odoo.services.importacao_fallback_service import ImportacaoFallbackService

        logger.info("🔧 Reparacao manual de NFs orfas iniciada")
        service = ImportacaoFallbackService()
        resultado = service.reparar_orfaos_faturamento()

        if resultado.get('sucesso'):
            encontradas = resultado.get('orfas_encontradas', 0)
            reparadas = resultado.get('orfas_reparadas', 0)
            movimentacoes = resultado.get('movimentacoes_criadas', 0)

            if encontradas == 0:
                flash("✅ Nenhuma NF orfa encontrada — pipeline consistente", 'success')
            else:
                flash(
                    f"🔧 {reparadas}/{encontradas} NFs orfas reparadas, "
                    f"{movimentacoes} movimentacoes de estoque criadas",
                    'success'
                )
                if resultado.get('erros'):
                    flash(
                        f"⚠️ {len(resultado['erros'])} erros: {'; '.join(resultado['erros'][:3])}",
                        'warning'
                    )
        else:
            erros = resultado.get('erros', [])
            flash(f"❌ Erro ao reparar NFs orfas: {'; '.join(erros[:3])}", 'error')

        return redirect(url_for('sync_integrada.fallback_dashboard'))

    except Exception as e:
        logger.error(f"❌ Erro na reparacao de NFs orfas: {e}")
        flash(f"❌ Erro ao reparar NFs orfas: {str(e)}", 'error')
        return redirect(url_for('sync_integrada.fallback_dashboard'))