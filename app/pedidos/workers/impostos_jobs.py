"""
Jobs assíncronos para cálculo de impostos no Odoo
Executados via Redis Queue na fila 'impostos'

Fluxo:
1. Pedido criado no Odoo via service.py
2. Job enfileirado na fila 'impostos' com order_id
3. Worker processa: chama onchange_l10n_br_calcular_imposto
4. CFOP e impostos preenchidos automaticamente

Resiliência (Fire-and-Poll):
- Dispara onchange com timeout curto (90s)
- Se timeout → Odoo continua processando server-side
- Polla a cada 15s verificando l10n_br_total_tributos > 0
- Máximo 10 minutos de polling (suficiente para picos de demanda)
"""

import logging
import socket
import ssl
import time
import xmlrpc.client
from datetime import datetime

logger = logging.getLogger(__name__)

# Fire-and-Poll — parâmetros para cálculo de impostos
FIRE_TIMEOUT = 90       # Timeout para disparar onchange (90s)
POLL_INTERVAL = 15      # Intervalo entre polls (15s)
MAX_POLL_TIME = 600     # Tempo máximo de polling (10 min)
POLL_TIMEOUT = 30       # Timeout para cada poll individual (30s)
COOLDOWN_ENTRE_CALCULOS = 30  # Pausa entre calculos para Odoo respirar
MAX_RECONEXOES_POLL = 2       # Maximo de reconexoes durante polling


def calcular_impostos_odoo(order_id: int, order_name: str = None):
    """
    Job para calcular impostos de um pedido no Odoo.

    Usa Fire-and-Poll: dispara onchange com timeout curto,
    polla resultado se demorar mais que FIRE_TIMEOUT.

    Args:
        order_id: ID do pedido no Odoo (sale.order)
        order_name: Nome do pedido para logs (ex: VCD2565531)

    Returns:
        dict com success, order_id, order_name, message
    """
    inicio = datetime.now()
    pedido_ref = order_name or f"ID:{order_id}"

    logger.info(f"[Job Impostos] Iniciando calculo para {pedido_ref}")

    try:
        from app.odoo.config.odoo_config import ODOO_CONFIG

        url = ODOO_CONFIG['url']
        database = ODOO_CONFIG['database']
        username = ODOO_CONFIG['username']
        api_key = ODOO_CONFIG['api_key']

        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        # Autenticação
        socket.setdefaulttimeout(POLL_TIMEOUT)
        common = xmlrpc.client.ServerProxy(
            f'{url}/xmlrpc/2/common',
            context=ssl_context,
            allow_none=True
        )
        uid = common.authenticate(database, username, api_key, {})

        if not uid:
            error_msg = f"Falha na autenticacao com Odoo para {pedido_ref}"
            logger.error(f"[Job Impostos] {error_msg}")
            return {
                'success': False,
                'order_id': order_id,
                'order_name': order_name,
                'message': error_msg,
                'error': 'AUTH_FAILED'
            }

        # 1. FIRE — dispara onchange com timeout curto
        logger.info(f"[Job Impostos] Disparando onchange_l10n_br_calcular_imposto para {pedido_ref}...")
        needs_polling = False

        try:
            socket.setdefaulttimeout(FIRE_TIMEOUT)
            models = xmlrpc.client.ServerProxy(
                f'{url}/xmlrpc/2/object',
                context=ssl_context,
                allow_none=True
            )
            models.execute_kw(
                database, uid, api_key,
                'sale.order',
                'onchange_l10n_br_calcular_imposto',
                [[order_id]]
            )
            # Completou dentro do timeout
            tempo_total = (datetime.now() - inicio).total_seconds()
            logger.info(f"[Job Impostos] {pedido_ref} calculado em {tempo_total:.1f}s")
            return _resultado_sucesso(order_id, order_name, tempo_total)

        except Exception as e:
            error_str = str(e)
            if 'cannot marshal None' in error_str:
                # Retorno None é esperado — onchange funcionou
                tempo_total = (datetime.now() - inicio).total_seconds()
                logger.info(f"[Job Impostos] {pedido_ref} calculado (marshal None) em {tempo_total:.1f}s")
                return _resultado_sucesso(order_id, order_name, tempo_total)

            if 'timed out' in error_str.lower() or 'timeout' in error_str.lower():
                logger.info(
                    f"[Job Impostos] Timeout ao disparar ({FIRE_TIMEOUT}s) para {pedido_ref} — "
                    f"esperado, iniciando polling..."
                )
                needs_polling = True
            else:
                raise

        # 2. POLL — verifica periodicamente se impostos foram calculados
        if needs_polling:
            elapsed = 0
            poll_count = 0
            reconexoes = 0

            # Reutilizar conexao: 1 chamada XML-RPC por poll (nao 3)
            socket.setdefaulttimeout(POLL_TIMEOUT)
            poll_models = xmlrpc.client.ServerProxy(
                f'{url}/xmlrpc/2/object',
                context=ssl_context,
                allow_none=True
            )
            poll_uid = uid  # uid da autenticacao inicial

            while elapsed < MAX_POLL_TIME:
                time.sleep(POLL_INTERVAL)
                elapsed += POLL_INTERVAL
                poll_count += 1

                impostos_ok = _verificar_impostos_calculados(
                    order_id, database, poll_uid, api_key, poll_models
                )

                # None = erro de conexao — reconectar e tentar novamente
                if impostos_ok is None and reconexoes < MAX_RECONEXOES_POLL:
                    reconexoes += 1
                    logger.info(
                        f"[Job Impostos] {pedido_ref} — reconectando "
                        f"({reconexoes}/{MAX_RECONEXOES_POLL})..."
                    )
                    try:
                        common_retry = xmlrpc.client.ServerProxy(
                            f'{url}/xmlrpc/2/common',
                            context=ssl_context,
                            allow_none=True
                        )
                        poll_uid = common_retry.authenticate(
                            database, username, api_key, {}
                        )
                        poll_models = xmlrpc.client.ServerProxy(
                            f'{url}/xmlrpc/2/object',
                            context=ssl_context,
                            allow_none=True
                        )
                    except Exception as e_reconn:
                        logger.warning(
                            f"[Job Impostos] Falha ao reconectar: {e_reconn}"
                        )
                    continue

                if impostos_ok:
                    tempo_total = (datetime.now() - inicio).total_seconds()
                    logger.info(
                        f"[Job Impostos] {pedido_ref} — Poll #{poll_count} ({elapsed}s): "
                        f"impostos calculados! Total: {tempo_total:.1f}s"
                    )
                    return _resultado_sucesso(order_id, order_name, tempo_total,
                                              f" (verificado apos {elapsed}s de polling)")

                logger.debug(
                    f"[Job Impostos] {pedido_ref} — Poll #{poll_count} ({elapsed}s): aguardando..."
                )

            # Polling expirou
            tempo_total = (datetime.now() - inicio).total_seconds()
            logger.error(
                f"[Job Impostos] {pedido_ref} — Polling expirou apos {MAX_POLL_TIME}s "
                f"({poll_count} tentativas)"
            )
            return {
                'success': False,
                'order_id': order_id,
                'order_name': order_name,
                'message': f'Timeout: impostos nao calculados apos {MAX_POLL_TIME}s de polling',
                'error': 'POLL_TIMEOUT',
                'tempo_segundos': tempo_total
            }

    except Exception as e:
        tempo_total = (datetime.now() - inicio).total_seconds()
        logger.error(f"[Job Impostos] Erro ao calcular {pedido_ref}: {e}")
        return {
            'success': False,
            'order_id': order_id,
            'order_name': order_name,
            'message': f'Erro ao calcular impostos',
            'error': str(e),
            'tempo_segundos': tempo_total
        }


def _resultado_sucesso(order_id, order_name, tempo_total, sufixo=''):
    """Helper para montar resultado de sucesso. Inclui cooldown para Odoo respirar."""
    # Pausa entre calculos para Odoo respirar antes do proximo job
    try:
        pedido_ref = order_name or f"ID:{order_id}"
        logger.info(
            f"[Job Impostos] {pedido_ref} — aguardando {COOLDOWN_ENTRE_CALCULOS}s "
            f"para Odoo respirar..."
        )
        time.sleep(COOLDOWN_ENTRE_CALCULOS)
    except Exception:
        pass  # Nao falhar o job por causa da pausa

    return {
        'success': True,
        'order_id': order_id,
        'order_name': order_name,
        'message': f'Impostos calculados com sucesso em {tempo_total:.1f}s{sufixo}',
        'tempo_segundos': tempo_total
    }


def _verificar_impostos_calculados(order_id, database, uid, api_key, models_proxy):
    """
    Verifica se os impostos foram calculados no Odoo.

    Reutiliza models_proxy e uid pre-autenticados (1 chamada XML-RPC por poll).
    Retorna True (calculado), False (aguardando), ou None (erro de conexao).
    """
    try:
        socket.setdefaulttimeout(POLL_TIMEOUT)

        order_data = models_proxy.execute_kw(
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

        return bool(total_tributos > 0 and cfop)

    except Exception as e:
        error_str = str(e).lower()
        # Erros de conexao retornam None para sinalizar reconexao
        if any(kw in error_str for kw in ('timed out', 'timeout', 'eof', 'connection', 'broken pipe')):
            logger.warning(f"[Job Impostos] Erro de conexao no poll: {e}")
            return None
        logger.warning(f"[Job Impostos] Erro ao verificar impostos (poll): {e}")
        return False
