"""
Rotas de Carteira Odoo
======================

Rotas para gerenciar carteira pendente do Odoo ERP.
Implementa consulta de carteira pendente com filtros.

Autor: Sistema de Fretes
Data: 2025-07-14
"""

from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime, date
import logging

from app.utils.auth_decorators import require_admin
from app.odoo.services.carteira_service import CarteiraService

logger = logging.getLogger(__name__)

# Blueprint para rotas de carteira
carteira_bp = Blueprint('carteira_odoo', __name__, url_prefix='/carteira')

# Instância do serviço
carteira_service = CarteiraService()

@carteira_bp.route('/dashboard')
@login_required
@require_admin()
def dashboard():
    """Dashboard principal da carteira Odoo"""
    try:
        # Obter dados básicos da carteira
        resultado = carteira_service.obter_carteira_pendente()
        
        return render_template('odoo/carteira/dashboard.html', 
                             resultado=resultado)
        
    except Exception as e:
        logger.error(f"Erro no dashboard: {e}")
        flash(f"Erro ao carregar dashboard: {str(e)}", 'error')
        # Renderizar página de erro ao invés de redirect
        return render_template('odoo/carteira/dashboard.html', 
                             resultado={'error': str(e), 'success': False})

@carteira_bp.route('/pendente', methods=['GET', 'POST'])
@login_required
@require_admin()
def pendente():
    """Obtém carteira pendente do Odoo"""
    if request.method == 'GET':
        return render_template('odoo/carteira/pendente.html')
    
    try:
        # Obter parâmetros da requisição
        data_inicio = request.form.get('data_inicio')
        data_fim = request.form.get('data_fim')
        pedidos_especificos = request.form.get('pedidos_especificos', '').strip()
        
        # Converter datas
        data_inicio_obj = None
        data_fim_obj = None
        
        if data_inicio:
            data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d').date()
        
        if data_fim:
            data_fim_obj = datetime.strptime(data_fim, '%Y-%m-%d').date()
        
        # Processar pedidos específicos
        pedidos_lista = None
        if pedidos_especificos:
            pedidos_lista = [p.strip() for p in pedidos_especificos.split(',') if p.strip()]
        
        # Obter carteira pendente
        resultado = carteira_service.obter_carteira_pendente(
            data_inicio=data_inicio_obj,
            data_fim=data_fim_obj,
            pedidos_especificos=pedidos_lista
        )
        
        # Exibir resultado
        if resultado['sucesso']:
            flash(f"✅ {resultado['mensagem']}", 'success')
            flash(f"📊 Total de registros: {resultado['total_registros']}", 'info')
            
            # Mostrar estatísticas
            stats = resultado['estatisticas']
            flash(f"📈 Estatísticas: {stats['total_pedidos']} pedidos, "
                  f"R$ {stats['valor_total']:,.2f}, "
                  f"Saldo: {stats['saldo_total']:,.2f}", 'info')
        else:
            flash(f"❌ Erro: {resultado['mensagem']}", 'error')
        
        return render_template('odoo/carteira/pendente.html', resultado=resultado)
        
    except Exception as e:
        logger.error(f"Erro ao obter carteira pendente: {e}")
        flash(f"❌ Erro: {str(e)}", 'error')
        return redirect(url_for('odoo.carteira_odoo.pendente'))

# === APIs REST ===

@carteira_bp.route('/api/pendente', methods=['GET'])
@login_required
def api_pendente():
    """API para obter carteira pendente"""
    try:
        # Obter parâmetros opcionais
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        pedidos_especificos = request.args.get('pedidos_especificos')
        
        data_inicio_obj = None
        data_fim_obj = None
        pedidos_lista = None
        
        if data_inicio:
            data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d').date()
        
        if data_fim:
            data_fim_obj = datetime.strptime(data_fim, '%Y-%m-%d').date()
        
        if pedidos_especificos:
            pedidos_lista = [p.strip() for p in pedidos_especificos.split(',') if p.strip()]
        
        # Obter carteira pendente
        resultado = carteira_service.obter_carteira_pendente(
            data_inicio=data_inicio_obj,
            data_fim=data_fim_obj,
            pedidos_especificos=pedidos_lista
        )
        
        return jsonify(resultado)
        
    except Exception as e:
        logger.error(f"Erro na API de carteira pendente: {e}")
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500

# === Rotas de Teste ===

@carteira_bp.route('/teste-conexao')
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
        
        return redirect(url_for('odoo.carteira_odoo.dashboard'))
        
    except Exception as e:
        logger.error(f"Erro no teste de conexão: {e}")
        flash(f"❌ Erro no teste: {str(e)}", 'error')
        return redirect(url_for('odoo.carteira_odoo.dashboard'))

@carteira_bp.route('/api/teste-conexao')
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

@carteira_bp.route('/sincronizar', methods=['GET'])
@login_required
@require_admin()
def sincronizar_carteira_get():
    """
    Rota GET para sincronização - redireciona para dashboard com mensagem
    """
    flash('⚠️ A sincronização deve ser executada via formulário no dashboard.', 'warning')
    return redirect(url_for('odoo.carteira_odoo.dashboard'))

@carteira_bp.route('/sincronizar', methods=['POST'])
@login_required
@require_admin()
def sincronizar_carteira():
    """
    Sincroniza carteira do Odoo por substituição completa da CarteiraPrincipal
    """
    try:
        from app.odoo.services.carteira_service import sincronizar_carteira_odoo
        
        # Pegar parâmetro do checkbox
        usar_filtro = request.form.get('usar_filtro_pendente') == 'on'
        
        # Executar sincronização
        resultado = sincronizar_carteira_odoo(usar_filtro_pendente=usar_filtro)
        
        if resultado['sucesso']:
            # Mensagem de sucesso
            mensagem = f"✅ Sincronização da carteira concluída! "
            mensagem += f"Registros: {resultado['registros_importados']} importados, {resultado['registros_removidos']} removidos."
            
            flash(mensagem, 'success')
            
            # Mostrar erros se houver
            if resultado.get('erros'):
                for erro in resultado['erros']:
                    flash(f"⚠️ {erro}", 'warning')
        else:
            flash(f"❌ Erro na sincronização: {resultado['erro']}", 'error')
        
        return redirect(url_for('carteira_odoo.dashboard'))
        
    except Exception as e:
        flash(f"❌ Erro durante sincronização: {str(e)}", 'error')
        return redirect(url_for('carteira_odoo.dashboard')) 