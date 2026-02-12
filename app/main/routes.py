from flask import Blueprint, render_template, redirect, url_for, send_from_directory, current_app, request, jsonify, send_file
from flask_login import current_user, login_required
import os
from app.utils.api_helper import APIDataHelper, get_dashboard_stats, get_system_alerts
import tempfile
import pandas as pd
from datetime import datetime, timedelta
from app.utils.timezone import agora_utc_naive

from app import db
from app.pedidos.models import Pedido
from app.faturamento.models import RelatorioFaturamentoImportado
from app.monitoramento.models import EntregaMonitorada
from app.embarques.models import Embarque, EmbarqueItem
from app.fretes.models import Frete
from app.transportadoras.models import Transportadora
from sqlalchemy import desc
from sqlalchemy.orm import joinedload
main_bp = Blueprint('main', __name__)

@main_bp.route('/dashboard')
@main_bp.route('/main/dashboard')
@login_required
def dashboard():
    """Dashboard principal com dados da API"""
    # Verifica se o usuário é vendedor e redireciona para o dashboard comercial
    if current_user.perfil == 'vendedor':
        return redirect(url_for('comercial.dashboard_diretoria'))

    try:
        # Usa o API Helper para obter estatísticas
        stats_data = get_dashboard_stats()
        alertas_data = get_system_alerts()
        
        # Dados para o template
        estatisticas = stats_data.get('data', {}) if stats_data.get('success') else {}
        alertas = alertas_data.get('data', []) if alertas_data.get('success') else []
        
        return render_template('main/dashboard.html', 
                             usuario=current_user,
                             estatisticas=estatisticas,
                             alertas=alertas)
    except Exception as e:
        # Fallback em caso de erro
        return render_template('main/dashboard.html', 
                             usuario=current_user,
                             estatisticas={},
                             alertas=[])

@main_bp.route('/relatorio_gerencial')
@login_required
def relatorio_gerencial():
    """Relatório gerencial usando dados da API"""
    try:
        periodo = int(request.args.get('periodo', 30))
        
        # Obtém dados via API Helper
        stats_data = APIDataHelper.get_estatisticas_data(periodo_dias=periodo)
        embarques_data = APIDataHelper.get_embarques_data(limite=20)
        fretes_data = APIDataHelper.get_fretes_pendentes_data(limite=15)
        
        dados_relatorio = {
            'periodo': periodo,
            'estatisticas': stats_data.get('data', {}) if stats_data.get('success') else {},
            'embarques_recentes': embarques_data.get('data', []) if embarques_data.get('success') else [],
            'fretes_pendentes': fretes_data.get('data', []) if fretes_data.get('success') else [],
            'data_geracao': agora_utc_naive().strftime('%d/%m/%Y %H:%M:%S')
        }
        
        return render_template('main/relatorio_gerencial.html', **dados_relatorio)
        
    except Exception as e:
        return f"Erro ao gerar relatório: {str(e)}", 500

@main_bp.route('/relatorio_gerencial/excel')
@login_required  
def relatorio_gerencial_excel():
    """Exporta relatório gerencial em Excel usando dados da API"""
    try:
        periodo = int(request.args.get('periodo', 30))
        
        # Obtém dados via API Helper
        stats_data = APIDataHelper.get_estatisticas_data(periodo_dias=periodo)
        embarques_data = APIDataHelper.get_embarques_data(limite=50)
        fretes_data = APIDataHelper.get_fretes_pendentes_data(limite=100)
        
        # Prepara dados para Excel
        dados_excel = {
            'Estatísticas': [],
            'Embarques': [],
            'Fretes_Pendentes': []
        }
        
        # Aba de estatísticas
        if stats_data.get('success'):
            stats = stats_data['data']
            dados_excel['Estatísticas'] = [
                {'Métrica': 'Total de Embarques', 'Valor': stats['embarques']['total']},
                {'Métrica': 'Embarques Ativos', 'Valor': stats['embarques']['ativos']},
                {'Métrica': 'Total de Fretes', 'Valor': stats['fretes']['total']},
                {'Métrica': 'Fretes Aprovados', 'Valor': stats['fretes']['aprovados']},
                {'Métrica': '% Aprovação', 'Valor': f"{stats['fretes']['percentual_aprovacao']}%"},
                {'Métrica': 'Total Entregas', 'Valor': stats['entregas']['total_monitoradas']},
                {'Métrica': 'Entregas Concluídas', 'Valor': stats['entregas']['entregues']},
                {'Métrica': 'Pendências Financeiras', 'Valor': stats['entregas']['pendencias_financeiras']},
                {'Métrica': '% Entregas', 'Valor': f"{stats['entregas']['percentual_entrega']}%"}
            ]
        
        # Aba de embarques
        if embarques_data.get('success'):
            for embarque in embarques_data['data']:
                dados_excel['Embarques'].append({
                    'ID': embarque['id'],
                    'Número': embarque['numero'],
                    'Status': embarque['status'],
                    'Data_Embarque': embarque['data_embarque'] or 'N/A',
                    'Transportadora': embarque['transportadora'] or 'N/A',
                    'Total_Fretes': embarque['total_fretes']
                })
        
        # Aba de fretes pendentes
        if fretes_data.get('success'):
            for frete in fretes_data['data']:
                dados_excel['Fretes_Pendentes'].append({
                    'ID': frete['id'],
                    'Embarque': frete['embarque_numero'] or 'N/A',
                    'Transportadora': frete['transportadora'] or 'N/A',
                    'Cliente': frete['cliente'],
                    'Destino': frete['destino'],
                    'Valor_Cotado': frete['valor_cotado'] or 0,
                    'Tem_CTe': 'Sim' if frete['tem_cte'] else 'Não'
                })
        
        # Cria arquivo Excel temporário
        arquivo_temp = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
        
        with pd.ExcelWriter(arquivo_temp.name, engine='xlsxwriter') as writer:
            # Cria cada aba
            for aba_nome, dados in dados_excel.items():
                if dados:
                    df = pd.DataFrame(dados)
                    df.to_excel(writer, sheet_name=aba_nome, index=False)
            
            # Aba de resumo
            resumo_data = [{
                'Relatório': 'Relatório Gerencial',
                'Período': f'Últimos {periodo} dias',
                'Data_Geração': agora_utc_naive().strftime('%d/%m/%Y %H:%M:%S'),
                'Usuário': current_user.nome,
                'Total_Abas': len([d for d in dados_excel.values() if d])
            }]
            
            df_resumo = pd.DataFrame(resumo_data)
            df_resumo.to_excel(writer, sheet_name='Resumo', index=False)
        
        arquivo_temp.close()
        
        # Nome do arquivo para download
        nome_arquivo = f"relatorio_gerencial_{periodo}dias_{agora_utc_naive().strftime('%Y%m%d_%H%M')}.xlsx"
        
        return send_file(
            arquivo_temp.name,
            as_attachment=True,
            download_name=nome_arquivo,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        return f"Erro ao gerar Excel: {str(e)}", 500

@main_bp.route('/api/dashboard/estatisticas')
@login_required
def api_dashboard_estatisticas():
    """Endpoint interno para estatísticas do dashboard"""
    try:
        periodo = int(request.args.get('periodo', 30))
        stats_data = APIDataHelper.get_estatisticas_data(periodo_dias=periodo)
        return jsonify(stats_data)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@main_bp.route('/api/dashboard/alertas')
@login_required
def api_dashboard_alertas():
    """Endpoint interno para alertas do dashboard"""
    try:
        alertas_data = APIDataHelper.get_alertas_sistema()
        return jsonify(alertas_data)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@main_bp.route('/consulta_rapida/<cliente_nome>')
@login_required
def consulta_rapida_cliente(cliente_nome):
    """Página de consulta rápida usando dados da API"""
    try:
        uf = request.args.get('uf', '')
        limite = int(request.args.get('limite', 10))
        
        # Usa API Helper para obter dados do cliente
        dados_cliente = APIDataHelper.get_cliente_data(
            cliente_nome=cliente_nome, 
            uf_filtro=uf if uf else None, 
            limite=limite
        )
        
        if dados_cliente.get('success'):
            return render_template('main/consulta_cliente.html', 
                                 dados=dados_cliente,
                                 cliente_nome=cliente_nome,
                                 uf_filtro=uf)
        else:
            return render_template('main/consulta_cliente.html', 
                                 erro=dados_cliente.get('error'),
                                 cliente_nome=cliente_nome,
                                 uf_filtro=uf)
        
    except Exception as e:
        return f"Erro na consulta: {str(e)}", 500

@main_bp.route('/')
def home():
    return redirect(url_for('auth.login'))

@main_bp.route('/favicon.ico')
def favicon():
    """Rota para o favicon.ico para evitar erros 404"""
    try:
        # Tenta servir favicon.ico da pasta static se existir
        static_dir = os.path.join(current_app.root_path, 'static')
        if os.path.exists(os.path.join(static_dir, 'favicon.ico')):
            return send_from_directory(static_dir, 'favicon.ico', mimetype='image/vnd.microsoft.icon')
    except:
        pass
    
    # Se não encontrar, retorna resposta vazia
    from flask import Response
    return Response('', status=204, mimetype='image/vnd.microsoft.icon')

@main_bp.route('/api/estatisticas-internas', methods=['GET'])
@login_required
def api_estatisticas_internas():
    """Estatísticas do sistema para dashboard interno (com autenticação de sessão)"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("🔍 Iniciando coleta de estatísticas internas")
        
        # Contar embarques
        logger.info("📊 Contando embarques...")
        total_embarques = Embarque.query.count()
        logger.info(f"📦 Total embarques: {total_embarques}")
        
        embarques_ativos = Embarque.query.filter(Embarque.status == 'ativo').count()
        logger.info(f"🟢 Embarques ativos: {embarques_ativos}")
        
        # Embarques pendentes (ativos sem data de embarque)
        embarques_pendentes = Embarque.query.filter(
            Embarque.status == 'ativo',
            Embarque.data_embarque == None
        ).count()
        logger.info(f"⏳ Embarques pendentes: {embarques_pendentes}")
        
        # Contar fretes
        logger.info("🚛 Contando fretes...")
        total_fretes = Frete.query.count()
        logger.info(f"📋 Total fretes: {total_fretes}")
        
        # Campo correto é 'status', não 'status_aprovacao'
        fretes_pendentes = Frete.query.filter(Frete.status == 'pendente').count()
        logger.info(f"⏳ Fretes pendentes: {fretes_pendentes}")
        
        fretes_aprovados = Frete.query.filter(Frete.status == 'aprovado').count()
        logger.info(f"✅ Fretes aprovados: {fretes_aprovados}")
        
        # Contar entregas monitoradas
        logger.info("📦 Contando entregas...")
        total_entregas = EntregaMonitorada.query.count()
        logger.info(f"📊 Total entregas: {total_entregas}")
        
        entregas_entregues = EntregaMonitorada.query.filter(
            EntregaMonitorada.status_finalizacao == 'Entregue'
        ).count()
        logger.info(f"✅ Entregas entregues: {entregas_entregues}")
        
        # Entregas pendentes (não entregues)
        entregas_pendentes = EntregaMonitorada.query.filter(
            EntregaMonitorada.entregue == False
        ).count()
        logger.info(f"📦 Entregas pendentes: {entregas_pendentes}")
        
        pendencias_financeiras = EntregaMonitorada.query.filter(
            EntregaMonitorada.pendencia_financeira == True
        ).count()
        logger.info(f"💰 Pendências financeiras: {pendencias_financeiras}")
        
        # Contar pedidos abertos
        logger.info("📋 Contando pedidos...")
        pedidos_abertos = Pedido.query.filter(
            Pedido.status == 'aberto'
        ).count()
        logger.info(f"📂 Pedidos abertos: {pedidos_abertos}")
        
        logger.info("🧮 Montando resultado...")
        resultado = {
            'embarques': {
                'total': total_embarques,
                'ativos': embarques_ativos,
                'pendentes': embarques_pendentes,
                'cancelados': total_embarques - embarques_ativos
            },
            'fretes': {
                'total': total_fretes,
                'pendentes_aprovacao': fretes_pendentes,
                'aprovados': fretes_aprovados,
                'percentual_aprovacao': round((fretes_aprovados / total_fretes * 100), 1) if total_fretes > 0 else 0
            },
            'entregas': {
                'total_monitoradas': total_entregas,
                'entregues': entregas_entregues,
                'pendentes': entregas_pendentes,
                'pendencias_financeiras': pendencias_financeiras,
                'percentual_entrega': round((entregas_entregues / total_entregas * 100), 1) if total_entregas > 0 else 0
            },
            'pedidos': {
                'abertos': pedidos_abertos
            }
        }
        
        logger.info("✅ Estatísticas coletadas com sucesso")
        
        return jsonify({
            'success': True,
            'data': resultado,
            'usuario': current_user.nome,
            'timestamp': agora_utc_naive().isoformat()
        })

    except Exception as e:
        logger.error(f"❌ Erro ao coletar estatísticas: {str(e)}")
        logger.error(f"📍 Tipo do erro: {type(e)}")
        import traceback
        logger.error(f"🔍 Traceback completo: {traceback.format_exc()}")
        
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': str(type(e))
        }), 500

@main_bp.route('/api/embarques-internos', methods=['GET'])
@login_required
def api_embarques_internos():
    """Lista embarques para dashboard interno (com autenticação de sessão)"""
    try:
        limite = int(request.args.get('limite', 8))
        
        embarques = Embarque.query.filter(
            Embarque.status == 'ativo'
        ).order_by(Embarque.id.desc()).limit(limite).all()
        
        resultado = []
        for embarque in embarques:
            modalidade = None
            if embarque.itens and len(embarque.itens) > 0:
                modalidade = embarque.itens[0].modalidade
            resultado.append({
                'id': embarque.id,
                'numero': embarque.numero,
                'status': embarque.status,
                'data_prevista_embarque': embarque.data_prevista_embarque.isoformat() if embarque.data_prevista_embarque else None,
                'tipo_carga': embarque.tipo_carga,
                'modalidade': modalidade,
                'transportadora': embarque.transportadora.razao_social if embarque.transportadora else None,
                'total_fretes': len(embarque.fretes) if embarque.fretes else 0,
                'valor_total': embarque.valor_total,
                'pallet_total': embarque.pallet_total,
                'peso_total': embarque.peso_total
            })
        
        return jsonify({
            'success': True,
            'data': resultado,
            'total': len(resultado),
            'usuario': current_user.nome,
            'timestamp': agora_utc_naive().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
       }), 500

# ==========================================
# 🔗 INTEGRAÇÃO ODOO
# ==========================================

@main_bp.route('/odoo-integration')
@login_required
def odoo_integration():
    """Página de integração com Odoo"""
    return render_template('main/odoo_integration.html')

@main_bp.route('/api/odoo/test', methods=['GET'])
@login_required
def test_odoo_connection():
    """Testar conexão com Odoo"""
    try:
        from app.utils.odoo_integration import get_odoo_integration
        
        integration = get_odoo_integration()
        result = integration.test_connection()
        
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Erro ao testar conexão Odoo: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Erro ao conectar com Odoo: {str(e)}'
        }), 500

@main_bp.route('/api/odoo/sync-customers', methods=['POST'])
@login_required
def sync_customers():
    """Sincronizar clientes do Odoo"""
    try:
        from app.utils.odoo_integration import get_odoo_integration
        
        limit = request.json.get('limit', 10) if request.json else 10
        
        integration = get_odoo_integration()
        result = integration.sync_customers_to_system(limit=limit)
        
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Erro ao sincronizar clientes: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Erro na sincronização: {str(e)}'
        }), 500

@main_bp.route('/api/odoo/sync-products', methods=['POST'])
@login_required
def sync_products():
    """Sincronizar produtos do Odoo"""
    try:
        from app.utils.odoo_integration import get_odoo_integration
        
        limit = request.json.get('limit', 10) if request.json else 10
        
        integration = get_odoo_integration()
        result = integration.sync_products_to_system(limit=limit)
        
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Erro ao sincronizar produtos: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Erro na sincronização: {str(e)}'
        }), 500

@main_bp.route('/api/odoo/sync-orders', methods=['POST'])
@login_required
def sync_orders():
    """Sincronizar pedidos do Odoo"""
    try:
        from app.utils.odoo_integration import get_odoo_integration
        
        data = request.json if request.json else {}
        limit = data.get('limit', 10)
        days_back = data.get('days_back', 7)
        
        integration = get_odoo_integration()
        result = integration.sync_orders_to_system(limit=limit, days_back=days_back)
        
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Erro ao sincronizar pedidos: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Erro na sincronização: {str(e)}'
        }), 500
