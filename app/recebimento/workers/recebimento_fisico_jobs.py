"""
Jobs RQ para Recebimento Fisico (Fase 4)
==========================================

Queue: 'recebimento'
Timeout: 10 minutos

Funcoes:
- processar_recebimento_job: Processa um recebimento no Odoo (7 passos)
- verificar_status_recebimento_job: Verifica estado do picking no Odoo

IMPORTANTE: Estas funcoes sao executadas pelo worker RQ (worker_render.py),
NAO pelo processo principal do Flask. Precisam criar app_context.
"""

import logging
import os
from redis import Redis

logger = logging.getLogger(__name__)

# Redis para progresso e locks
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
PROGRESSO_TTL = 3600  # 1 hora
LOCK_TTL = 1800  # 30 minutos


def _get_redis():
    """Obtem conexao Redis."""
    return Redis.from_url(REDIS_URL)


def _atualizar_progresso(recebimento_id, etapa, total, mensagem=''):
    """Atualiza progresso no Redis para consulta pela tela de status."""
    try:
        redis_conn = _get_redis()
        import json
        progresso = {
            'recebimento_id': recebimento_id,
            'etapa': etapa,
            'total': total,
            'percentual': int((etapa / total) * 100) if total > 0 else 0,
            'mensagem': mensagem,
        }
        redis_conn.setex(
            f'recebimento_progresso:{recebimento_id}',
            PROGRESSO_TTL,
            json.dumps(progresso)
        )
    except Exception as e:
        logger.warning(f"Erro ao atualizar progresso Redis: {e}")


def _adquirir_lock(picking_id):
    """Adquire lock para evitar processamento duplicado do mesmo picking."""
    try:
        redis_conn = _get_redis()
        lock_key = f'recebimento_lock:{picking_id}'
        return redis_conn.set(lock_key, '1', nx=True, ex=LOCK_TTL)
    except Exception:
        return True  # Se Redis falhar, permite prosseguir


def _liberar_lock(picking_id):
    """Libera lock apos processamento."""
    try:
        redis_conn = _get_redis()
        redis_conn.delete(f'recebimento_lock:{picking_id}')
    except Exception:
        pass


def processar_recebimento_job(recebimento_id, usuario_nome=None):
    """
    Job RQ que processa um recebimento no Odoo (7 passos).

    Este job e enfileirado ao salvar recebimento (fire-and-forget).
    O usuario nao espera — o resultado e consultado pela tela de status.

    Args:
        recebimento_id: ID do RecebimentoFisico local
        usuario_nome: Nome do usuario que iniciou

    Returns:
        Dict com resultado do processamento
    """
    from app import create_app

    app = create_app()
    with app.app_context():
        from app.recebimento.models import RecebimentoFisico
        from app.recebimento.services.recebimento_fisico_odoo_service import RecebimentoFisicoOdooService

        recebimento = RecebimentoFisico.query.get(recebimento_id)
        if not recebimento:
            logger.error(f"[Job] Recebimento {recebimento_id} nao encontrado")
            return {'status': 'erro', 'mensagem': 'Recebimento nao encontrado'}

        # Verificar lock (evitar duplicata)
        if not _adquirir_lock(recebimento.odoo_picking_id):
            logger.warning(
                f"[Job] Picking {recebimento.odoo_picking_id} ja esta sendo processado. "
                "Abortando."
            )
            return {'status': 'lock', 'mensagem': 'Picking ja em processamento'}

        try:
            _atualizar_progresso(recebimento_id, 0, 7, 'Iniciando processamento...')

            service = RecebimentoFisicoOdooService()
            resultado = service.processar_recebimento(recebimento_id, usuario_nome)

            _atualizar_progresso(recebimento_id, 7, 7, 'Processado com sucesso!')

            logger.info(
                f"[Job] Recebimento {recebimento_id} processado com sucesso "
                f"(picking={recebimento.odoo_picking_name})"
            )

            return resultado

        except Exception as e:
            logger.error(f"[Job] Erro ao processar recebimento {recebimento_id}: {e}")
            _atualizar_progresso(recebimento_id, 0, 7, f'Erro: {str(e)[:100]}')
            return {'status': 'erro', 'mensagem': str(e)[:500]}

        finally:
            _liberar_lock(recebimento.odoo_picking_id)


def verificar_status_recebimento_job(recebimento_id):
    """
    Job auxiliar para verificar estado do picking no Odoo.
    Usado pela tela de status para consulta independente.

    Args:
        recebimento_id: ID do RecebimentoFisico local

    Returns:
        Dict com estado do picking no Odoo
    """
    from app import create_app

    app = create_app()
    with app.app_context():
        from app.recebimento.services.recebimento_fisico_service import RecebimentoFisicoService

        service = RecebimentoFisicoService()
        return service.consultar_status_odoo(recebimento_id)
