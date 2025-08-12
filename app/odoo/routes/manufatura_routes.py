"""
Rotas de Integração Manufatura com Odoo
=======================================

Implementa rotas para sincronização do módulo Manufatura/PCP com Odoo.
Segue o padrão estabelecido em faturamento e carteira.

Autor: Sistema de Fretes
Data: 2025-08-10
"""

from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
from flask_login import login_required
from datetime import datetime
import logging

from app.utils.auth_decorators import require_admin
from app.odoo.services.manufatura_service import ManufaturaOdooService
from app.manufatura.models import LogIntegracao
from app import db

logger = logging.getLogger(__name__)

# Blueprint para manufatura odoo
manufatura_odoo_bp = Blueprint('manufatura_odoo', __name__, url_prefix='/odoo/manufatura')

# Instância do serviço
manufatura_service = ManufaturaOdooService()

@manufatura_odoo_bp.route('/')
@login_required
def dashboard():
    """Dashboard de integração Manufatura/Odoo"""
    try:
        logger.info("📊 Carregando dashboard de integração Manufatura/Odoo...")
        
        # Buscar últimos logs de integração
        logs = LogIntegracao.query.filter(
            LogIntegracao.tipo_integracao.in_([
                'importar_requisicoes', 'importar_pedidos', 'sincronizar_producao',
                'gerar_ordens_mto', 'importar_historico'
            ])
        ).order_by(LogIntegracao.data_execucao.desc()).limit(20).all()
        
        # Estatísticas
        stats = {
            'total_sincronizacoes': len(logs),
            'sucesso': len([log for log in logs if log.status == 'sucesso']),
            'erro': len([log for log in logs if log.status == 'erro']),
            'registros_processados': sum(log.registros_processados or 0 for log in logs),
            'registros_erro': sum(log.registros_erro or 0 for log in logs)
        }
        
        return render_template(
            'odoo/manufatura/dashboard.html',
            logs=logs,
            stats=stats
        )
        
    except Exception as e:
        logger.error(f"❌ Erro no dashboard de integração Manufatura: {e}")
        flash(f"❌ Erro ao carregar dashboard: {str(e)}", 'error')
        return redirect(url_for('manufatura.dashboard'))

@manufatura_odoo_bp.route('/importar/requisicoes', methods=['POST'])
@login_required
def importar_requisicoes():
    """Importa requisições de compras do Odoo"""
    try:
        logger.info("🔄 Iniciando importação de requisições de compras...")
        
        resultado = manufatura_service.importar_requisicoes_compras()
        
        if resultado.get('sucesso'):
            flash(f"✅ {resultado['registros_importados']} requisições importadas com sucesso!", 'success')
            if resultado.get('novos'):
                flash(f"📝 {resultado['novos']} novas requisições criadas", 'info')
            if resultado.get('atualizados'):
                flash(f"🔄 {resultado['atualizados']} requisições atualizadas", 'info')
        else:
            flash(f"❌ Erro na importação: {resultado.get('erro', 'Erro desconhecido')}", 'error')
        
        return jsonify(resultado)
        
    except Exception as e:
        logger.error(f"❌ Erro ao importar requisições: {e}")
        return jsonify({'erro': str(e)}), 500

@manufatura_odoo_bp.route('/importar/pedidos', methods=['POST'])
@login_required
def importar_pedidos():
    """Importa pedidos de compras do Odoo"""
    try:
        logger.info("🔄 Iniciando importação de pedidos de compras...")
        
        resultado = manufatura_service.importar_pedidos_compras()
        
        if resultado.get('sucesso'):
            flash(f"✅ {resultado['registros_importados']} pedidos importados com sucesso!", 'success')
            if resultado.get('novos'):
                flash(f"📝 {resultado['novos']} novos pedidos criados", 'info')
            if resultado.get('atualizados'):
                flash(f"🔄 {resultado['atualizados']} pedidos atualizados", 'info')
        else:
            flash(f"❌ Erro na importação: {resultado.get('erro', 'Erro desconhecido')}", 'error')
        
        return jsonify(resultado)
        
    except Exception as e:
        logger.error(f"❌ Erro ao importar pedidos: {e}")
        return jsonify({'erro': str(e)}), 500

@manufatura_odoo_bp.route('/sincronizar/producao', methods=['POST'])
@login_required
def sincronizar_producao():
    """Sincroniza ordens de produção com Odoo"""
    try:
        logger.info("🔄 Iniciando sincronização de produção...")
        
        resultado = manufatura_service.sincronizar_producao()
        
        if resultado.get('sucesso'):
            flash(f"✅ {resultado['ordens_sincronizadas']} ordens sincronizadas com sucesso!", 'success')
            if resultado.get('exportadas'):
                flash(f"📤 {resultado['exportadas']} ordens exportadas para Odoo", 'info')
            if resultado.get('atualizadas'):
                flash(f"🔄 {resultado['atualizadas']} ordens atualizadas", 'info')
        else:
            flash(f"❌ Erro na sincronização: {resultado.get('erro', 'Erro desconhecido')}", 'error')
        
        return jsonify(resultado)
        
    except Exception as e:
        logger.error(f"❌ Erro ao sincronizar produção: {e}")
        return jsonify({'erro': str(e)}), 500

@manufatura_odoo_bp.route('/importar/historico', methods=['POST'])
@login_required
def importar_historico():
    """Importa histórico de pedidos do Odoo"""
    try:
        dados = request.json or {}
        mes = dados.get('mes')
        ano = dados.get('ano')
        
        if not mes or not ano:
            # Se não especificado, importa mês anterior
            hoje = datetime.now()
            mes = hoje.month - 1 if hoje.month > 1 else 12
            ano = hoje.year if hoje.month > 1 else hoje.year - 1
        
        logger.info(f"🔄 Iniciando importação de histórico {mes}/{ano}...")
        
        resultado = manufatura_service.importar_historico_pedidos(mes, ano)
        
        if resultado.get('sucesso'):
            flash(f"✅ Histórico {mes}/{ano} importado com sucesso!", 'success')
            flash(f"📊 {resultado['registros_importados']} registros processados", 'info')
        else:
            flash(f"❌ Erro na importação: {resultado.get('erro', 'Erro desconhecido')}", 'error')
        
        return jsonify(resultado)
        
    except Exception as e:
        logger.error(f"❌ Erro ao importar histórico: {e}")
        return jsonify({'erro': str(e)}), 500

@manufatura_odoo_bp.route('/gerar/ordens-mto', methods=['POST'])
@login_required
def gerar_ordens_mto():
    """Gera ordens MTO automaticamente"""
    try:
        logger.info("🔄 Iniciando geração automática de ordens MTO...")
        
        from app.manufatura.services.ordem_producao_service import OrdemProducaoService
        
        service = OrdemProducaoService()
        ordens = service.gerar_ordens_mto_automaticas()
        
        resultado = {
            'sucesso': True,
            'ordens_criadas': len(ordens),
            'mensagem': f'{len(ordens)} ordens MTO criadas automaticamente'
        }
        
        # Registrar no log
        if ordens:
            log = LogIntegracao(
                tipo_integracao='gerar_ordens_mto',
                status='sucesso',
                mensagem=resultado['mensagem'],
                registros_processados=len(ordens),
                registros_erro=0
            )
            db.session.add(log)
            db.session.commit()
        
        flash(f"✅ {len(ordens)} ordens MTO criadas com sucesso!", 'success')
        
        return jsonify(resultado)
        
    except Exception as e:
        logger.error(f"❌ Erro ao gerar ordens MTO: {e}")
        
        # Registrar erro no log
        log = LogIntegracao(
            tipo_integracao='gerar_ordens_mto',
            status='erro',
            mensagem=str(e),
            registros_processados=0,
            registros_erro=1
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({'erro': str(e)}), 500

@manufatura_odoo_bp.route('/sincronizacao-completa', methods=['POST'])
@login_required
@require_admin
def sincronizacao_completa():
    """
    Executa sincronização completa na sequência correta:
    1. Importar requisições
    2. Importar pedidos
    3. Sincronizar produção
    4. Gerar ordens MTO
    """
    try:
        logger.info("🚀 Iniciando sincronização completa Manufatura/Odoo...")
        
        resultados = {
            'sucesso': True,
            'etapas': [],
            'tempo_total': 0
        }
        
        inicio = datetime.now()
        
        # 1. Importar requisições
        try:
            resultado_req = manufatura_service.importar_requisicoes_compras()
            resultados['etapas'].append({
                'etapa': 'Importar Requisições',
                'sucesso': resultado_req.get('sucesso', False),
                'registros': resultado_req.get('registros_importados', 0),
                'erro': resultado_req.get('erro')
            })
        except Exception as e:
            logger.error(f"Erro ao importar requisições: {e}")
            resultados['etapas'].append({
                'etapa': 'Importar Requisições',
                'sucesso': False,
                'erro': str(e)
            })
        
        # 2. Importar pedidos
        try:
            resultado_ped = manufatura_service.importar_pedidos_compras()
            resultados['etapas'].append({
                'etapa': 'Importar Pedidos',
                'sucesso': resultado_ped.get('sucesso', False),
                'registros': resultado_ped.get('registros_importados', 0),
                'erro': resultado_ped.get('erro')
            })
        except Exception as e:
            logger.error(f"Erro ao importar pedidos: {e}")
            resultados['etapas'].append({
                'etapa': 'Importar Pedidos',
                'sucesso': False,
                'erro': str(e)
            })
        
        # 3. Sincronizar produção
        try:
            resultado_prod = manufatura_service.sincronizar_producao()
            resultados['etapas'].append({
                'etapa': 'Sincronizar Produção',
                'sucesso': resultado_prod.get('sucesso', False),
                'registros': resultado_prod.get('ordens_sincronizadas', 0),
                'erro': resultado_prod.get('erro')
            })
        except Exception as e:
            logger.error(f"Erro ao sincronizar produção: {e}")
            resultados['etapas'].append({
                'etapa': 'Sincronizar Produção',
                'sucesso': False,
                'erro': str(e)
            })
        
        # 4. Gerar ordens MTO
        try:
            from app.manufatura.services.ordem_producao_service import OrdemProducaoService
            service = OrdemProducaoService()
            ordens = service.gerar_ordens_mto_automaticas()
            
            resultados['etapas'].append({
                'etapa': 'Gerar Ordens MTO',
                'sucesso': True,
                'registros': len(ordens)
            })
        except Exception as e:
            logger.error(f"Erro ao gerar ordens MTO: {e}")
            resultados['etapas'].append({
                'etapa': 'Gerar Ordens MTO',
                'sucesso': False,
                'erro': str(e)
            })
        
        # Calcular tempo total
        fim = datetime.now()
        resultados['tempo_total'] = (fim - inicio).total_seconds()
        
        # Verificar sucesso geral
        resultados['sucesso'] = all(etapa.get('sucesso', False) for etapa in resultados['etapas'])
        
        # Registrar no log
        log = LogIntegracao(
            tipo_integracao='sincronizacao_completa',
            status='sucesso' if resultados['sucesso'] else 'erro',
            mensagem=f"Sincronização completa - {len(resultados['etapas'])} etapas executadas",
            registros_processados=sum(etapa.get('registros', 0) for etapa in resultados['etapas']),
            registros_erro=len([etapa for etapa in resultados['etapas'] if not etapa.get('sucesso', False)]),
            tempo_execucao=resultados['tempo_total'],
            detalhes=resultados
        )
        db.session.add(log)
        db.session.commit()
        
        # Flash messages
        if resultados['sucesso']:
            flash(f"✅ Sincronização completa executada com sucesso em {resultados['tempo_total']:.1f}s!", 'success')
        else:
            flash(f"⚠️ Sincronização parcial - algumas etapas falharam", 'warning')
        
        for etapa in resultados['etapas']:
            if etapa['sucesso']:
                flash(f"✅ {etapa['etapa']}: {etapa.get('registros', 0)} registros", 'info')
            else:
                flash(f"❌ {etapa['etapa']}: {etapa.get('erro', 'Erro desconhecido')}", 'error')
        
        return jsonify(resultados)
        
    except Exception as e:
        logger.error(f"❌ Erro crítico na sincronização completa: {e}")
        return jsonify({'erro': str(e)}), 500

@manufatura_odoo_bp.route('/logs')
@login_required
def visualizar_logs():
    """Visualiza logs de integração"""
    try:
        # Parâmetros de filtro
        tipo = request.args.get('tipo')
        status = request.args.get('status')
        limite = int(request.args.get('limite', 50))
        
        # Query base
        query = LogIntegracao.query
        
        # Aplicar filtros
        if tipo:
            query = query.filter_by(tipo_integracao=tipo)
        if status:
            query = query.filter_by(status=status)
        
        # Ordenar e limitar
        logs = query.order_by(LogIntegracao.data_execucao.desc()).limit(limite).all()
        
        # Formatar para JSON
        logs_json = []
        for log in logs:
            logs_json.append({
                'id': log.id,
                'tipo': log.tipo_integracao,
                'status': log.status,
                'mensagem': log.mensagem,
                'registros_processados': log.registros_processados,
                'registros_erro': log.registros_erro,
                'data_execucao': log.data_execucao.strftime('%Y-%m-%d %H:%M:%S') if log.data_execucao else None,
                'tempo_execucao': log.tempo_execucao,
                'detalhes': log.detalhes
            })
        
        return jsonify(logs_json)
        
    except Exception as e:
        logger.error(f"❌ Erro ao visualizar logs: {e}")
        return jsonify({'erro': str(e)}), 500