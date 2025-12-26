"""
Jobs assíncronos para cálculo de impostos no Odoo
Executados via Redis Queue na fila 'impostos'

Fluxo:
1. Pedido criado no Odoo via service.py
2. Job enfileirado na fila 'impostos' com order_id
3. Worker processa: chama onchange_l10n_br_calcular_imposto
4. CFOP e impostos preenchidos automaticamente

Timeout: 300 segundos (5 minutos) por pedido
- Se der timeout, verifica se impostos foram calculados no Odoo
- Se l10n_br_total_tributos > 0, considera sucesso
"""

import logging
import socket
import ssl
import xmlrpc.client
from datetime import datetime

logger = logging.getLogger(__name__)

# Timeout para conexão XML-RPC com Odoo (5 minutos)
# Aumentado de 180s para 300s devido a lentidão no cálculo de impostos
TIMEOUT_CALCULO_IMPOSTOS = 300


def calcular_impostos_odoo(order_id: int, order_name: str = None):
    """
    Job para calcular impostos de um pedido no Odoo

    Usa conexão XML-RPC direta com timeout de 300 segundos (5 minutos).
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

        # Configurar timeout para 300 segundos (5 minutos)
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

        # Timeout ou erro - verificar se impostos foram calculados mesmo assim
        is_timeout = 'timed out' in error_str.lower() or 'timeout' in error_str.lower()
        if is_timeout:
            logger.warning(f"⏱️ [Job Impostos] Timeout ao calcular {pedido_ref}, verificando se impostos foram calculados...")

            # Verificar se impostos foram calculados no Odoo
            impostos_ok = _verificar_impostos_calculados(order_id, url, database, username, api_key, ssl_context)
            if impostos_ok:
                logger.info(f"✅ [Job Impostos] {pedido_ref} - Impostos calculados (verificado após timeout) em {tempo_total:.1f}s")
                return {
                    'success': True,
                    'order_id': order_id,
                    'order_name': order_name,
                    'message': f'Impostos calculados com sucesso em {tempo_total:.1f}s (verificado após timeout)',
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


def _verificar_impostos_calculados(order_id: int, url: str, database: str,
                                    username: str, api_key: str, ssl_context) -> bool:
    """
    Verifica se os impostos foram calculados no Odoo.

    Usado após timeout para confirmar se o cálculo foi concluído.
    Se l10n_br_total_tributos > 0 e l10n_br_cfop_id está preenchido,
    considera que os impostos foram calculados com sucesso.

    Returns:
        bool: True se impostos foram calculados, False caso contrário
    """
    try:
        # Nova conexão com timeout curto (30s) apenas para verificação
        socket.setdefaulttimeout(30)

        common = xmlrpc.client.ServerProxy(
            f'{url}/xmlrpc/2/common',
            context=ssl_context,
            allow_none=True
        )
        uid = common.authenticate(database, username, api_key, {})

        if not uid:
            return False

        models = xmlrpc.client.ServerProxy(
            f'{url}/xmlrpc/2/object',
            context=ssl_context,
            allow_none=True
        )

        # Buscar campos de impostos do pedido
        order_data = models.execute_kw(
            database, uid, api_key,
            'sale.order', 'read',
            [[order_id]],
            {'fields': ['l10n_br_total_tributos', 'l10n_br_cfop_id']}
        )

        if not order_data or not isinstance(order_data, list) or len(order_data) == 0:
            return False

        order = order_data[0]
        if not isinstance(order, dict):
            return False

        total_tributos = order.get('l10n_br_total_tributos', 0) or 0
        cfop = order.get('l10n_br_cfop_id')

        # Considera calculado se tem tributos > 0 E CFOP preenchido
        return bool(total_tributos > 0 and cfop)

    except Exception as e:
        logger.warning(f"⚠️ [Job Impostos] Erro ao verificar impostos: {e}")
        return False
