"""
Jobs RQ para Recebimento LF (La Famiglia -> Nacom Goya)
========================================================

Queue: 'recebimento'
Timeout: 20 minutos (mais longo: inclui DFe + PO + Picking + Invoice)

Funcoes:
- processar_recebimento_lf_job: Processa um recebimento LF no Odoo (18 passos)

IMPORTANTE: Estas funcoes sao executadas pelo worker RQ (worker_render.py),
NAO pelo processo principal do Flask. Precisam criar app_context.
"""

import json
import logging
import os
from redis import Redis
from rq.timeouts import JobTimeoutException

logger = logging.getLogger(__name__)

# Redis para progresso e locks
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
PROGRESSO_TTL = 3600  # 1 hora
LOCK_TTL = 3600  # 1 hora — reduzido de 2h; cleanup de orphans complementa


def _get_redis():
    """Obtem conexao Redis."""
    return Redis.from_url(REDIS_URL)


def _atualizar_progresso(recebimento_id, fase, etapa, total, mensagem='', **extra):
    """Atualiza progresso no Redis para consulta pela tela de status."""
    try:
        redis_conn = _get_redis()
        progresso = {
            'recebimento_id': recebimento_id,
            'fase': fase,
            'etapa': etapa,
            'total_etapas': total,
            'percentual': int((etapa / total) * 100) if total > 0 else 0,
            'mensagem': mensagem,
        }
        # Campos extras (ex: transfer_status, status)
        progresso.update(extra)
        redis_conn.setex(
            f'recebimento_lf_progresso:{recebimento_id}',
            PROGRESSO_TTL,
            json.dumps(progresso)
        )
    except Exception as e:
        logger.warning(f"Erro ao atualizar progresso Redis: {e}")


def _adquirir_lock(dfe_id):
    """Adquire lock para evitar processamento duplicado do mesmo DFe."""
    try:
        redis_conn = _get_redis()
        lock_key = f'recebimento_lf_lock:{dfe_id}'
        return redis_conn.set(lock_key, '1', nx=True, ex=LOCK_TTL)
    except Exception:
        return True  # Se Redis falhar, permite prosseguir


def _liberar_lock(dfe_id):
    """Libera lock apos processamento."""
    try:
        redis_conn = _get_redis()
        redis_conn.delete(f'recebimento_lf_lock:{dfe_id}')
    except Exception:
        pass


def processar_recebimento_lf_job(recebimento_id, usuario_nome=None):
    """
    Job RQ que processa um Recebimento LF no Odoo (6 fases, 26 passos).

    Este job e enfileirado ao salvar recebimento (fire-and-forget).
    O usuario nao espera — o resultado e consultado pela tela de status.

    Args:
        recebimento_id: ID do RecebimentoLf local
        usuario_nome: Nome do usuario que iniciou

    Returns:
        Dict com resultado do processamento
    """
    from app import create_app

    app = create_app()
    with app.app_context():
        from app.recebimento.models import RecebimentoLf
        from app.recebimento.services.recebimento_lf_odoo_service import RecebimentoLfOdooService

        recebimento = RecebimentoLf.query.get(recebimento_id)
        if not recebimento:
            logger.error(f"[Job LF] Recebimento {recebimento_id} nao encontrado")
            return {'status': 'erro', 'mensagem': 'Recebimento nao encontrado'}

        from app import db

        # Verificar lock (evitar duplicata pelo DFe)
        if not _adquirir_lock(recebimento.odoo_dfe_id):
            logger.warning(
                f"[Job LF] DFe {recebimento.odoo_dfe_id} ja esta sendo processado. "
                "Abortando."
            )
            # Atualizar status no banco para nao ficar 'pendente' eternamente
            recebimento.status = 'erro'
            recebimento.erro_mensagem = 'DFe já em processamento por outro job'
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
            return {'status': 'lock', 'mensagem': 'DFe ja em processamento'}

        try:
            total = recebimento.total_etapas or 26
            _atualizar_progresso(recebimento_id, 0, 0, total, 'Iniciando processamento...')

            service = RecebimentoLfOdooService()
            resultado = service.processar_recebimento(recebimento_id, usuario_nome)

            rec_final = RecebimentoLf.query.get(recebimento_id)
            final_fase = rec_final.fase_atual if rec_final else 6
            final_etapa = rec_final.etapa_atual if rec_final else total
            final_transfer = rec_final.transfer_status if rec_final else None
            _atualizar_progresso(
                recebimento_id, final_fase, final_etapa, total,
                'Processado com sucesso!',
                transfer_status=final_transfer,
                status='processado',
            )

            logger.info(
                f"[Job LF] Recebimento {recebimento_id} processado com sucesso "
                f"(DFe={recebimento.odoo_dfe_id}, PO={recebimento.odoo_po_name})"
            )

            return resultado

        except JobTimeoutException as e:
            # Timeout RQ: salvar estado no DB mas RE-RAISE para que RQ acione Retry
            logger.error(
                f"[Job LF] TIMEOUT recebimento {recebimento_id} "
                f"(etapa_atual pode estar em checkpoint): {e}"
            )
            _atualizar_progresso(recebimento_id, 0, 0, total, f'Timeout: {str(e)[:100]}')
            try:
                recebimento = RecebimentoLf.query.get(recebimento_id)
                if recebimento:
                    recebimento.status = 'erro'
                    recebimento.erro_mensagem = f'Timeout RQ: {str(e)[:450]}'
                    db.session.commit()
            except Exception:
                db.session.rollback()
            raise  # Propagar para RQ → Retry(max=3) aciona

        except Exception as e:
            logger.error(f"[Job LF] Erro ao processar recebimento {recebimento_id}: {e}")
            _atualizar_progresso(recebimento_id, 0, 0, total, f'Erro: {str(e)[:100]}')
            # Atualizar status no banco (pode ja ter sido feito pelo OdooService)
            try:
                recebimento.status = 'erro'
                recebimento.erro_mensagem = str(e)[:500]
                db.session.commit()
            except Exception:
                db.session.rollback()
            return {'status': 'erro', 'mensagem': str(e)[:500]}

        finally:
            _liberar_lock(recebimento.odoo_dfe_id)


def processar_transfer_fb_cd_job(recebimento_id):
    """
    Job RQ que processa APENAS a transferencia FB -> CD (etapas 19-26).

    Usado para retry isolado quando o recebimento FB (etapas 1-18) ja concluiu
    mas a transferencia falhou.

    Args:
        recebimento_id: ID do RecebimentoLf local

    Returns:
        Dict com resultado da transferencia
    """
    from app import create_app

    app = create_app()
    with app.app_context():
        from app.recebimento.models import RecebimentoLf
        from app.recebimento.services.recebimento_lf_odoo_service import RecebimentoLfOdooService

        recebimento = RecebimentoLf.query.get(recebimento_id)
        if not recebimento:
            logger.error(f"[Job Transfer] Recebimento {recebimento_id} nao encontrado")
            return {'status': 'erro', 'mensagem': 'Recebimento nao encontrado'}

        total = recebimento.total_etapas or 26
        _atualizar_progresso(
            recebimento_id, 6, 19, total, 'Iniciando transferencia FB->CD...',
            transfer_status='processando',
        )

        try:
            service = RecebimentoLfOdooService()
            resultado = service.processar_transfer_only(recebimento_id)

            _atualizar_progresso(
                recebimento_id, 6, 26, total, 'Transferencia concluida!',
                transfer_status='concluido',
                status='processado',
            )

            logger.info(
                f"[Job Transfer] Recebimento {recebimento_id} transferencia concluida"
            )
            return resultado

        except JobTimeoutException as e:
            # Timeout RQ: salvar estado no DB mas RE-RAISE para que RQ acione Retry
            logger.error(
                f"[Job Transfer] TIMEOUT transferencia {recebimento_id}: {e}"
            )
            _atualizar_progresso(
                recebimento_id, 6, 0, total, f'Timeout: {str(e)[:100]}',
                transfer_status='erro',
                status='processado',
            )
            try:
                from app import db
                rec = RecebimentoLf.query.get(recebimento_id)
                if rec:
                    rec.transfer_status = 'erro'
                    rec.transfer_erro_mensagem = f'Timeout RQ: {str(e)[:450]}'
                    db.session.commit()
            except Exception:
                pass
            raise  # Propagar para RQ → Retry(max=2) aciona

        except Exception as e:
            logger.error(
                f"[Job Transfer] Erro na transferencia {recebimento_id}: {e}"
            )
            _atualizar_progresso(
                recebimento_id, 6, 0, total, f'Erro transfer: {str(e)[:100]}',
                transfer_status='erro',
                status='processado',
            )
            return {'status': 'erro', 'mensagem': str(e)[:500]}
