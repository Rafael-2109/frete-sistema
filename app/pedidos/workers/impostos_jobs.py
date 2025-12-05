"""
Jobs assíncronos para cálculo de impostos no Odoo
Executados via Redis Queue na fila 'impostos'

Fluxo:
1. Pedido criado no Odoo via service.py
2. Job enfileirado na fila 'impostos' com order_id
3. Worker processa: chama onchange_l10n_br_calcular_imposto
4. CFOP e impostos preenchidos automaticamente

Timeout: 180 segundos (3 minutos) por pedido
"""

import logging
import socket
import ssl
import xmlrpc.client
from datetime import datetime

logger = logging.getLogger(__name__)

# Timeout para conexão XML-RPC com Odoo (3 minutos)
TIMEOUT_CALCULO_IMPOSTOS = 180


def calcular_impostos_odoo(order_id: int, order_name: str = None):
    """
    Job para calcular impostos de um pedido no Odoo

    Usa conexão XML-RPC direta com timeout de 180 segundos.
    Este job é processado pela fila 'impostos' do Redis Queue.

    Args:
        order_id: ID do pedido no Odoo (sale.order)
        order_name: Nome do pedido para logs (ex: VCD2565531)

    Returns:
        dict: Resultado do processamento
            - success: bool
            - order_id: int
            - order_name: str
            - message: str
            - error: str (se houver erro)
    """
    inicio = datetime.now()
    pedido_ref = order_name or f"ID:{order_id}"

    logger.info(f"🔄 [Job Impostos] Iniciando cálculo para {pedido_ref}")

    try:
        # Importar configurações do Odoo
        from app.odoo.config.odoo_config import ODOO_CONFIG

        url = ODOO_CONFIG['url']
        database = ODOO_CONFIG['database']
        username = ODOO_CONFIG['username']
        api_key = ODOO_CONFIG['api_key']

        # Configurar timeout para 180 segundos
        socket.setdefaulttimeout(TIMEOUT_CALCULO_IMPOSTOS)

        # SSL context
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        # Conexão para autenticação
        logger.info(f"📡 [Job Impostos] Conectando ao Odoo...")
        common = xmlrpc.client.ServerProxy(
            f'{url}/xmlrpc/2/common',
            context=ssl_context,
            allow_none=True
        )
        uid = common.authenticate(database, username, api_key, {})

        if not uid:
            error_msg = f"Falha na autenticação com Odoo para {pedido_ref}"
            logger.error(f"❌ [Job Impostos] {error_msg}")
            return {
                'success': False,
                'order_id': order_id,
                'order_name': order_name,
                'message': error_msg,
                'error': 'AUTH_FAILED'
            }

        # Conexão para models
        models = xmlrpc.client.ServerProxy(
            f'{url}/xmlrpc/2/object',
            context=ssl_context,
            allow_none=True
        )

        # Chamar método de cálculo de impostos
        logger.info(f"📊 [Job Impostos] Executando onchange_l10n_br_calcular_imposto para {pedido_ref}...")

        models.execute_kw(
            database, uid, api_key,
            'sale.order',
            'onchange_l10n_br_calcular_imposto',
            [[order_id]]
        )

        # Sucesso
        tempo_total = (datetime.now() - inicio).total_seconds()
        logger.info(f"✅ [Job Impostos] {pedido_ref} calculado em {tempo_total:.1f}s")

        return {
            'success': True,
            'order_id': order_id,
            'order_name': order_name,
            'message': f'Impostos calculados com sucesso em {tempo_total:.1f}s',
            'tempo_segundos': tempo_total
        }

    except Exception as e:
        error_str = str(e)
        tempo_total = (datetime.now() - inicio).total_seconds()

        # O erro "cannot marshal None" é esperado - o método funciona mesmo assim
        if "cannot marshal None" in error_str:
            logger.info(f"✅ [Job Impostos] {pedido_ref} calculado (marshal None) em {tempo_total:.1f}s")
            return {
                'success': True,
                'order_id': order_id,
                'order_name': order_name,
                'message': f'Impostos calculados com sucesso em {tempo_total:.1f}s',
                'tempo_segundos': tempo_total
            }

        # Erro real
        logger.error(f"❌ [Job Impostos] Erro ao calcular {pedido_ref}: {e}")
        return {
            'success': False,
            'order_id': order_id,
            'order_name': order_name,
            'message': f'Erro ao calcular impostos',
            'error': error_str,
            'tempo_segundos': tempo_total
        }
