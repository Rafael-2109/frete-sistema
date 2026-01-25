"""
Configuração de Conexão Odoo
============================

Centraliza todas as configurações de conexão com o Odoo ERP.

Autor: Sistema de Fretes
Data: 2025-07-14

IMPORTANTE: Todas as credenciais devem estar em variáveis de ambiente.
Variáveis necessárias:
- ODOO_URL: URL do servidor Odoo (default: https://odoo.nacomgoya.com.br)
- ODOO_DATABASE: Nome do banco de dados (default: odoo-17-ee-nacomgoya-prd)
- ODOO_USERNAME: Email/usuário de acesso
- ODOO_API_KEY: Chave de API gerada no Odoo
"""
import os

# Configuração global do módulo Odoo
ODOO_CONFIG = {
    'url': os.environ.get('ODOO_URL', 'https://odoo.nacomgoya.com.br'),
    'database': os.environ.get('ODOO_DATABASE', 'odoo-17-ee-nacomgoya-prd'),
    'username': os.environ.get('ODOO_USERNAME', ''),
    'api_key': os.environ.get('ODOO_API_KEY', ''),
    'timeout': 120,  # 🔧 Aumentado para 120s para evitar timeouts
    'retry_attempts': 3
}

# Validação de credenciais (só em runtime, não na importação)
def validate_odoo_config():
    """Valida se as credenciais Odoo estão configuradas."""
    if not ODOO_CONFIG['username']:
        raise ValueError("ODOO_USERNAME não está configurado nas variáveis de ambiente")
    if not ODOO_CONFIG['api_key']:
        raise ValueError("ODOO_API_KEY não está configurado nas variáveis de ambiente") 