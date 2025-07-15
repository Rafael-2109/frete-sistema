"""
Rotas de Faturamento Odoo
=========================

Rotas para gerenciar faturamento por produto do Odoo ERP.
Implementa consulta de faturamento com filtros específicos.

Autor: Sistema de Fretes
Data: 2025-07-14
"""

from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime, date
import logging

from app.utils.auth_decorators import require_admin
from app.odoo.services.faturamento_service import FaturamentoService

logger = logging.getLogger(__name__)

# Blueprint para rotas de faturamento
faturamento_bp = Blueprint('faturamento_odoo', __name__, url_prefix='/faturamento')

# Instância do serviço
faturamento_service = FaturamentoService()

@faturamento_bp.route('/dashboard')
@login_required
@require_admin()
def dashboard():
    """Dashboard principal do faturamento Odoo"""
    try:
        # Obter dados básicos do faturamento
        resultado = faturamento_service.obter_faturamento_produtos(
            data_inicio=None, 
            data_fim=None, 
            nfs_especificas=None
        )
        
        return render_template('odoo/faturamento/dashboard.html', 
                             resultado=resultado)
        
    except Exception as e:
        logger.error(f"Erro no dashboard: {e}")
        flash(f"Erro ao carregar dashboard: {str(e)}", 'error')
        # Renderizar página de erro ao invés de redirect
        return render_template('odoo/faturamento/dashboard.html', 
                             resultado={'error': str(e), 'success': False})

@faturamento_bp.route('/produtos', methods=['GET', 'POST'])
@login_required
@require_admin()
def produtos():
    """Obtém faturamento por produto do Odoo"""
    if request.method == 'GET':
        return render_template('odoo/faturamento/produtos.html')
    
    try:
        # Obter parâmetros da requisição
        data_inicio = request.form.get('data_inicio')
        data_fim = request.form.get('data_fim')
        nfs_especificas = request.form.get('nfs_especificas', '').strip()
        
        # Converter datas
        data_inicio_obj = None
        data_fim_obj = None
        
        if data_inicio:
            data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d').date()
        
        if data_fim:
            data_fim_obj = datetime.strptime(data_fim, '%Y-%m-%d').date()
        
        # Processar NFs específicas
        nfs_lista = None
        if nfs_especificas:
            nfs_lista = [nf.strip() for nf in nfs_especificas.split(',') if nf.strip()]
        
        # Obter faturamento por produto
        resultado = faturamento_service.obter_faturamento_produtos(
            data_inicio=data_inicio_obj,
            data_fim=data_fim_obj,
            nfs_especificas=nfs_lista
        )
        
        # Exibir resultado
        if resultado['sucesso']:
            flash(f"✅ {resultado['mensagem']}", 'success')
            flash(f"📊 Total de registros: {resultado['total_registros']}", 'info')
            
            # Mostrar estatísticas
            stats = resultado['estatisticas']
            flash(f"📈 Estatísticas: {stats['total_nfs']} NFs, "
                  f"{stats['total_produtos']} produtos, "
                  f"R$ {stats['valor_total']:,.2f}", 'info')
        else:
            flash(f"❌ Erro: {resultado['mensagem']}", 'error')
        
        return render_template('odoo/faturamento/produtos.html', resultado=resultado)
        
    except Exception as e:
        logger.error(f"Erro ao obter faturamento por produto: {e}")
        flash(f"❌ Erro: {str(e)}", 'error')
        return redirect(url_for('faturamento_odoo.produtos'))

@faturamento_bp.route('/consolidado', methods=['GET', 'POST'])
@login_required
@require_admin()
def consolidado():
    """Exibe faturamento consolidado por NF"""
    if request.method == 'GET':
        return render_template('odoo/faturamento/consolidado.html')
    
    try:
        # Obter parâmetros da requisição
        data_inicio = request.form.get('data_inicio')
        data_fim = request.form.get('data_fim')
        nfs_especificas = request.form.get('nfs_especificas', '').strip()
        
        # Converter datas
        data_inicio_obj = None
        data_fim_obj = None
        
        if data_inicio:
            data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d').date()
        
        if data_fim:
            data_fim_obj = datetime.strptime(data_fim, '%Y-%m-%d').date()
        
        # Processar NFs específicas
        nfs_lista = None
        if nfs_especificas:
            nfs_lista = [nf.strip() for nf in nfs_especificas.split(',') if nf.strip()]
        
        # Obter faturamento por produto
        resultado = faturamento_service.obter_faturamento_produtos(
            data_inicio=data_inicio_obj,
            data_fim=data_fim_obj,
            nfs_especificas=nfs_lista
        )
        
        # Consolidar dados
        if resultado['sucesso'] and resultado['dados']:
            dados_consolidados = faturamento_service.consolidar_para_relatorio(resultado['dados'])
            
            resultado['dados_consolidados'] = dados_consolidados
            resultado['total_consolidados'] = len(dados_consolidados)
            
            flash(f"✅ {resultado['mensagem']}", 'success')
            flash(f"📋 NFs consolidadas: {len(dados_consolidados)}", 'info')
        else:
            flash(f"❌ Erro: {resultado['mensagem']}", 'error')
        
        return render_template('odoo/faturamento/consolidado.html', resultado=resultado)
        
    except Exception as e:
        logger.error(f"Erro na consolidação: {e}")
        flash(f"❌ Erro: {str(e)}", 'error')
        return redirect(url_for('faturamento_odoo.consolidado'))

# === APIs REST ===

@faturamento_bp.route('/api/produtos', methods=['GET'])
@login_required
def api_produtos():
    """API para obter faturamento por produto"""
    try:
        # Obter parâmetros opcionais
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        nfs_especificas = request.args.get('nfs_especificas')
        
        data_inicio_obj = None
        data_fim_obj = None
        nfs_lista = None
        
        if data_inicio:
            data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d').date()
        
        if data_fim:
            data_fim_obj = datetime.strptime(data_fim, '%Y-%m-%d').date()
        
        if nfs_especificas:
            nfs_lista = [nf.strip() for nf in nfs_especificas.split(',') if nf.strip()]
        
        # Obter faturamento por produto
        resultado = faturamento_service.obter_faturamento_produtos(
            data_inicio=data_inicio_obj,
            data_fim=data_fim_obj,
            nfs_especificas=nfs_lista
        )
        
        return jsonify(resultado)
        
    except Exception as e:
        logger.error(f"Erro na API de faturamento por produto: {e}")
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500

@faturamento_bp.route('/api/consolidado', methods=['GET'])
@login_required
def api_consolidado():
    """API para obter faturamento consolidado"""
    try:
        # Obter parâmetros opcionais
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        nfs_especificas = request.args.get('nfs_especificas')
        
        data_inicio_obj = None
        data_fim_obj = None
        nfs_lista = None
        
        if data_inicio:
            data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d').date()
        
        if data_fim:
            data_fim_obj = datetime.strptime(data_fim, '%Y-%m-%d').date()
        
        if nfs_especificas:
            nfs_lista = [nf.strip() for nf in nfs_especificas.split(',') if nf.strip()]
        
        # Obter faturamento por produto
        resultado = faturamento_service.obter_faturamento_produtos(
            data_inicio=data_inicio_obj,
            data_fim=data_fim_obj,
            nfs_especificas=nfs_lista
        )
        
        # Consolidar dados
        if resultado['sucesso'] and resultado['dados']:
            dados_consolidados = faturamento_service.consolidar_para_relatorio(resultado['dados'])
            
            resultado['dados_consolidados'] = dados_consolidados
            resultado['total_consolidados'] = len(dados_consolidados)
        
        return jsonify(resultado)
        
    except Exception as e:
        logger.error(f"Erro na API de faturamento consolidado: {e}")
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500

# === Rotas de Teste ===

@faturamento_bp.route('/teste-conexao')
@login_required
@require_admin()
def teste_conexao():
    """Testa conexão com Odoo"""
    try:
        from ..utils.connection import test_connection, get_odoo_version
        
        # Testar conexão
        conexao_ok = test_connection()
        versao = get_odoo_version()
        
        if conexao_ok:
            flash(f"✅ Conexão com Odoo estabelecida! Versão: {versao}", 'success')
        else:
            flash("❌ Falha na conexão com Odoo", 'error')
        
        return redirect(url_for('faturamento_odoo.dashboard'))
        
    except Exception as e:
        logger.error(f"Erro no teste de conexão: {e}")
        flash(f"❌ Erro no teste: {str(e)}", 'error')
        return redirect(url_for('faturamento_odoo.dashboard'))

@faturamento_bp.route('/api/teste-conexao')
@login_required
def api_teste_conexao():
    """API para testar conexão com Odoo"""
    try:
        from ..utils.connection import test_connection, get_odoo_version
        
        # Testar conexão
        conexao_ok = test_connection()
        versao = get_odoo_version()
        
        return jsonify({
            'sucesso': conexao_ok,
            'versao': versao,
            'mensagem': 'Conexão estabelecida' if conexao_ok else 'Falha na conexão'
        })
        
    except Exception as e:
        logger.error(f"Erro na API de teste: {e}")
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500 

@faturamento_bp.route('/sincronizar', methods=['GET'])
@login_required
def sincronizar_faturamento_get():
    """
    Rota GET para sincronização - redireciona para dashboard com mensagem
    """
    flash('⚠️ A sincronização deve ser executada via formulário no dashboard.', 'warning')
    return redirect(url_for('odoo.faturamento_odoo.dashboard'))

@faturamento_bp.route('/sincronizar', methods=['POST'])
@login_required
def sincronizar_faturamento():
    """
    Sincroniza faturamento do Odoo para FaturamentoProduto e RelatorioFaturamentoImportado
    """
    try:
        from app.odoo.services.faturamento_service import sincronizar_faturamento_odoo
        
        # Pegar parâmetro do checkbox
        usar_filtro = request.form.get('usar_filtro_venda_bonificacao') == 'on'
        
        # Executar sincronização
        resultado = sincronizar_faturamento_odoo(usar_filtro_venda_bonificacao=usar_filtro)
        
        if resultado['sucesso']:
            # Mensagem de sucesso
            mensagem = f"✅ Sincronização concluída! "
            mensagem += f"Produtos: {resultado['produtos_importados']} importados, {resultado['produtos_atualizados']} atualizados. "
            mensagem += f"NFs consolidadas: {resultado['nfs_consolidadas']}"
            
            flash(mensagem, 'success')
            
            # Mostrar erros se houver
            if resultado.get('erros'):
                for erro in resultado['erros']:
                    flash(f"⚠️ {erro}", 'warning')
        else:
            flash(f"❌ Erro na sincronização: {resultado['erro']}", 'error')
        
        return redirect(url_for('faturamento_odoo.dashboard'))
        
    except Exception as e:
        flash(f"❌ Erro durante sincronização: {str(e)}", 'error')
        return redirect(url_for('faturamento_odoo.dashboard'))

@faturamento_bp.route('/produtos/sincronizar', methods=['POST'])
@login_required
def sincronizar_produtos():
    """
    Sincroniza apenas produtos do faturamento (sem consolidar relatório)
    """
    try:
        from app.odoo.services.faturamento_service import sincronizar_faturamento_odoo
        
        # Pegar parâmetro do checkbox
        usar_filtro = request.form.get('usar_filtro_venda_bonificacao') == 'on'
        
        # Executar sincronização
        resultado = sincronizar_faturamento_odoo(usar_filtro_venda_bonificacao=usar_filtro)
        
        if resultado['sucesso']:
            # Mensagem de sucesso
            mensagem = f"✅ Sincronização de produtos concluída! "
            mensagem += f"{resultado['produtos_importados']} importados, {resultado['produtos_atualizados']} atualizados"
            
            flash(mensagem, 'success')
            
            # Mostrar erros se houver
            if resultado.get('erros'):
                for erro in resultado['erros']:
                    flash(f"⚠️ {erro}", 'warning')
        else:
            flash(f"❌ Erro na sincronização: {resultado['erro']}", 'error')
        
        return redirect(url_for('faturamento_odoo.produtos'))
        
    except Exception as e:
        flash(f"❌ Erro durante sincronização: {str(e)}", 'error')
        return redirect(url_for('faturamento_odoo.produtos')) 