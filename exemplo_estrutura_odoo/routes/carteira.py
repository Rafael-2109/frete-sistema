"""
Rotas de Carteira - Integração Odoo
===================================

Responsabilidades:
- Importação de carteira do Odoo
- Sincronização de dados
- Monitoramento de status
"""

from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Criar blueprint específico para carteira
carteira_bp = Blueprint('carteira', __name__, url_prefix='/carteira')

# Importar serviços com fallback
try:
    from ..services.carteira_service import CarteiraService
    from ..validators.carteira_validator import validate_carteira_data
    from ..utils.exceptions import OdooIntegrationError
    _services_available = True
except ImportError as e:
    logger.warning(f"⚠️ Serviços de carteira não disponíveis: {e}")
    _services_available = False

# =============================================================================
# ROTAS DE IMPORTAÇÃO
# =============================================================================

@carteira_bp.route('/importar', methods=['GET', 'POST'])
@login_required
def importar_carteira():
    """Importar carteira do Odoo"""
    if not _services_available:
        return jsonify({
            'success': False,
            'message': 'Serviços de carteira não disponíveis'
        }), 503
    
    if request.method == 'GET':
        # Exibir formulário de importação
        return render_template('odoo/carteira/importar.html')
    
    try:
        # Processar importação
        service = CarteiraService()
        
        # Validar dados da requisição
        filters = request.json.get('filters', {})
        
        # Executar importação
        result = service.import_from_odoo(
            filters=filters,
            user=current_user.nome
        )
        
        return jsonify({
            'success': True,
            'message': 'Carteira importada com sucesso',
            'data': result
        })
        
    except OdooIntegrationError as e:
        logger.error(f"❌ Erro na integração Odoo: {e}")
        return jsonify({
            'success': False,
            'message': f'Erro na integração: {str(e)}'
        }), 500
    except Exception as e:
        logger.error(f"❌ Erro inesperado: {e}")
        return jsonify({
            'success': False,
            'message': 'Erro interno do servidor'
        }), 500

@carteira_bp.route('/sincronizar', methods=['POST'])
@login_required
def sincronizar_carteira():
    """Sincronizar carteira com Odoo"""
    if not _services_available:
        return jsonify({
            'success': False,
            'message': 'Serviços de carteira não disponíveis'
        }), 503
    
    try:
        service = CarteiraService()
        
        # Configurações da sincronização
        config = {
            'incremental': request.json.get('incremental', True),
            'date_from': request.json.get('date_from'),
            'date_to': request.json.get('date_to'),
            'chunk_size': request.json.get('chunk_size', 100)
        }
        
        # Executar sincronização
        result = service.sync_with_odoo(config)
        
        return jsonify({
            'success': True,
            'message': 'Sincronização concluída',
            'data': result
        })
        
    except Exception as e:
        logger.error(f"❌ Erro na sincronização: {e}")
        return jsonify({
            'success': False,
            'message': f'Erro na sincronização: {str(e)}'
        }), 500

# =============================================================================
# ROTAS DE MONITORAMENTO
# =============================================================================

@carteira_bp.route('/status', methods=['GET'])
@login_required
def status_carteira():
    """Status da sincronização de carteira"""
    if not _services_available:
        return jsonify({
            'success': False,
            'message': 'Serviços de carteira não disponíveis'
        }), 503
    
    try:
        service = CarteiraService()
        status = service.get_sync_status()
        
        return jsonify({
            'success': True,
            'data': status
        })
        
    except Exception as e:
        logger.error(f"❌ Erro ao obter status: {e}")
        return jsonify({
            'success': False,
            'message': f'Erro ao obter status: {str(e)}'
        }), 500

@carteira_bp.route('/logs', methods=['GET'])
@login_required
def logs_carteira():
    """Logs de integração da carteira"""
    if not _services_available:
        return jsonify({
            'success': False,
            'message': 'Serviços de carteira não disponíveis'
        }), 503
    
    try:
        service = CarteiraService()
        
        # Parâmetros de consulta
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        level = request.args.get('level', 'INFO')
        
        logs = service.get_logs(
            limit=limit,
            offset=offset,
            level=level
        )
        
        return jsonify({
            'success': True,
            'data': logs
        })
        
    except Exception as e:
        logger.error(f"❌ Erro ao obter logs: {e}")
        return jsonify({
            'success': False,
            'message': f'Erro ao obter logs: {str(e)}'
        }), 500

# =============================================================================
# ROTAS DE CONFIGURAÇÃO
# =============================================================================

@carteira_bp.route('/config', methods=['GET', 'POST'])
@login_required
def config_carteira():
    """Configurações da integração de carteira"""
    if not _services_available:
        return jsonify({
            'success': False,
            'message': 'Serviços de carteira não disponíveis'
        }), 503
    
    service = CarteiraService()
    
    if request.method == 'GET':
        # Retornar configurações atuais
        try:
            config = service.get_config()
            return jsonify({
                'success': True,
                'data': config
            })
        except Exception as e:
            logger.error(f"❌ Erro ao obter configurações: {e}")
            return jsonify({
                'success': False,
                'message': f'Erro ao obter configurações: {str(e)}'
            }), 500
    
    # POST - Atualizar configurações
    try:
        new_config = request.json
        
        # Validar configurações
        if not validate_carteira_data(new_config):
            return jsonify({
                'success': False,
                'message': 'Dados de configuração inválidos'
            }), 400
        
        # Atualizar configurações
        service.update_config(new_config)
        
        return jsonify({
            'success': True,
            'message': 'Configurações atualizadas com sucesso'
        })
        
    except Exception as e:
        logger.error(f"❌ Erro ao atualizar configurações: {e}")
        return jsonify({
            'success': False,
            'message': f'Erro ao atualizar configurações: {str(e)}'
        }), 500

logger.info("🗂️ Rotas de carteira Odoo carregadas") 