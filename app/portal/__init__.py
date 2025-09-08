"""
Módulo de Integração com Portais de Agendamento
Sistema para automatizar agendamentos em portais de clientes
"""

from flask import Blueprint

# Criar Blueprint para o módulo portal
portal_bp = Blueprint('portal', __name__, url_prefix='/portal')

# Importar rotas para registrá-las no blueprint
from app.portal import routes
from app.portal import routes_sessao  # Rotas de configuração de sessão
from app.portal import routes_async  # Rotas assíncronas com Redis Queue
from app.portal import verificacao_automatica  # Rotas de verificação de protocolos pendentes
# Removido: verificacao_lote era duplicado - usando verificacao_automatica e verificacao_protocolo

# Registrar rotas De-Para do Atacadão
from app.portal.atacadao.routes_depara import bp as depara_bp
portal_bp.register_blueprint(depara_bp)

# Registrar rotas de Agendamento do Atacadão
from app.portal.atacadao.routes_agendamento import bp as agendamento_bp
portal_bp.register_blueprint(agendamento_bp)

# Registrar rotas de Verificação de Protocolo do Atacadão
from app.portal.atacadao.verificacao_protocolo import verificacao_protocolo_bp
portal_bp.register_blueprint(verificacao_protocolo_bp, url_prefix='/atacadao')

# ========== PORTAL TENDA ==========

# Registrar rotas De-Para do Tenda
from app.portal.tenda.routes_depara import bp as tenda_depara_bp
portal_bp.register_blueprint(tenda_depara_bp)

# Registrar rotas de Agendamento do Tenda
from app.portal.tenda.routes_agendamento import bp as tenda_agendamento_bp
portal_bp.register_blueprint(tenda_agendamento_bp)

# Registrar rotas de Identificação de Portal
from app.portal.utils.identificacao_portal import identificacao_portal_bp
portal_bp.register_blueprint(identificacao_portal_bp, url_prefix='/utils')

# ========== PORTAL SENDAS ==========

# Registrar rotas De-Para do Sendas
from app.portal.sendas.routes_depara import bp as sendas_depara_bp
portal_bp.register_blueprint(sendas_depara_bp)