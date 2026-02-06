"""
Jobs assíncronos para processamento de devoluções de pallet no Odoo.
Executado pelo worker via Redis Queue.

Fluxo:
1. Rota POST cria PalletNFSolucao localmente (odoo_status='pendente')
2. Enfileira este job no Redis Queue
3. Worker executa: OdooDevolucaoService.processar_devolucao_completa()
4. Atualiza PalletNFSolucao com odoo_picking_id + status

Padrão: app/fretes/workers/lancamento_odoo_jobs.py

Autor: Sistema de Fretes
Data: 2026-02-06
"""

import logging
from datetime import datetime
from contextlib import contextmanager
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


# ==============================================================================
# CONTEXTO FLASK PARA WORKER
# ==============================================================================

@contextmanager
def _app_context_safe():
    """
    Context manager seguro para execução no worker.

    Verifica se já existe um contexto ativo (ex: chamado de dentro de outro job)
    para evitar criar contextos aninhados que podem causar travamentos.

    Padrão: lancamento_odoo_jobs.py:122-152
    """
    from flask import has_app_context

    if has_app_context():
        logger.debug("[Context] Reutilizando contexto Flask existente")
        yield
        return

    from app import create_app
    app = create_app()
    logger.debug("[Context] Novo contexto Flask criado")

    with app.app_context():
        yield


# ==============================================================================
# JOB PRINCIPAL
# ==============================================================================

def processar_devolucao_odoo_job(
    solucao_ids: List[int],
    odoo_dfe_id: int,
    company_id: int,
    quantidade_total: int,
    vinculacoes: List[Dict],
    usuario: str
) -> Dict[str, Any]:
    """
    Job assíncrono: processa devolução de pallet no Odoo.

    Chamado via enqueue_job() após vinculação local ser concluída.

    Fluxo:
    1. Atualiza status das soluções para 'processando'
    2. Chama OdooDevolucaoService.processar_devolucao_completa()
    3. Atualiza soluções com odoo_picking_id + status 'concluido'
    4. Em caso de erro: status 'erro' + mensagem

    Args:
        solucao_ids: IDs das PalletNFSolucao criadas na etapa 1
        odoo_dfe_id: ID do DFe no Odoo
        company_id: ID da empresa (1=FB, 3=SC, 4=CD)
        quantidade_total: Soma das quantidades
        vinculacoes: Lista de {odoo_picking_remessa_id, quantidade}
        usuario: Nome do usuário que iniciou

    Returns:
        Dict com resultado (success, po_id, picking_id, etc.)
    """
    inicio = datetime.now()
    resultado = {
        'success': False,
        'solucao_ids': solucao_ids,
        'odoo_dfe_id': odoo_dfe_id,
        'po_id': None,
        'po_name': None,
        'picking_id': None,
        'picking_name': None,
        'error': None,
        'error_type': None,
        'tempo_segundos': 0
    }

    logger.info(
        f"[DevolucaoJob] Iniciando processamento: DFe={odoo_dfe_id}, "
        f"company={company_id}, qtd={quantidade_total}, "
        f"solucoes={solucao_ids}, usuario={usuario}"
    )

    try:
        with _app_context_safe():
            from app import db
            from app.pallet.models.nf_solucao import PalletNFSolucao
            from app.pallet.services.odoo_devolucao_service import OdooDevolucaoService

            # --- Marcar como 'processando' ---
            solucoes = PalletNFSolucao.query.filter(
                PalletNFSolucao.id.in_(solucao_ids)
            ).all()

            if not solucoes:
                raise ValueError(
                    f"Nenhuma PalletNFSolucao encontrada com IDs {solucao_ids}"
                )

            for s in solucoes:
                s.odoo_status = 'processando'
            db.session.commit()

            logger.info(
                f"[DevolucaoJob] {len(solucoes)} solucoes marcadas como 'processando'"
            )

            # --- Executar no Odoo ---
            odoo_service = OdooDevolucaoService()
            resultado_odoo = odoo_service.processar_devolucao_completa(
                dfe_id=odoo_dfe_id,
                company_id=company_id,
                quantidade_total=quantidade_total,
                vinculacoes=vinculacoes
            )

            picking_id = resultado_odoo.get('picking_id')

            # --- Atualizar soluções com resultado ---
            for s in solucoes:
                s.odoo_picking_id = picking_id
                s.odoo_status = 'concluido'
                s.odoo_erro = None
            db.session.commit()

            resultado['success'] = True
            resultado['po_id'] = resultado_odoo.get('po_id')
            resultado['po_name'] = resultado_odoo.get('po_name')
            resultado['picking_id'] = picking_id
            resultado['picking_name'] = resultado_odoo.get('picking_name')

            logger.info(
                f"[DevolucaoJob] DFe {odoo_dfe_id} processado com sucesso: "
                f"PO={resultado_odoo.get('po_name')}, "
                f"Picking={resultado_odoo.get('picking_name')}"
            )

    except Exception as e:
        resultado['error'] = str(e)
        resultado['error_type'] = _classificar_erro(str(e))
        logger.exception(
            f"[DevolucaoJob] Erro ao processar DFe {odoo_dfe_id}: {e}"
        )

        # Marcar soluções como erro
        try:
            with _app_context_safe():
                from app import db
                from app.pallet.models.nf_solucao import PalletNFSolucao

                solucoes = PalletNFSolucao.query.filter(
                    PalletNFSolucao.id.in_(solucao_ids)
                ).all()
                for s in solucoes:
                    s.odoo_status = 'erro'
                    s.odoo_erro = str(e)[:500]
                db.session.commit()

                logger.info(
                    f"[DevolucaoJob] {len(solucoes)} solucoes marcadas como 'erro'"
                )
        except Exception as e2:
            logger.error(
                f"[DevolucaoJob] Erro ao atualizar status de erro: {e2}"
            )

    finally:
        resultado['tempo_segundos'] = (
            datetime.now() - inicio
        ).total_seconds()

    return resultado


# ==============================================================================
# CLASSIFICACAO DE ERROS
# ==============================================================================

def _classificar_erro(error_msg: str) -> str:
    """
    Classifica tipo de erro para categorização.

    Padrão: lancamento_odoo_jobs.py:741-781
    """
    msg = error_msg.lower()

    if 'timeout' in msg:
        return 'ERRO_TIMEOUT'
    if 'autenticacao' in msg or 'authentication' in msg:
        return 'ERRO_AUTENTICACAO'
    if 'circuit breaker' in msg:
        return 'ERRO_CIRCUIT_BREAKER'
    if 'conexao' in msg or 'connection' in msg:
        return 'ERRO_CONEXAO'
    if 'purchase' in msg and ('create' in msg or 'confirm' in msg):
        return 'ERRO_PO'
    if 'picking' in msg:
        return 'ERRO_PICKING'
    if 'move' in msg and ('create' in msg or 'write' in msg):
        return 'ERRO_MOVES'
    if 'validate' in msg or 'button_validate' in msg:
        return 'ERRO_VALIDACAO'

    return 'ERRO_DESCONHECIDO'


# ==============================================================================
# STATUS DO JOB
# ==============================================================================

def get_devolucao_job_status(job_id: str) -> Dict[str, Any]:
    """
    Obtém status de um job de devolução pelo ID.

    Padrão: lancamento_odoo_jobs.py:784-838

    Args:
        job_id: ID do job no Redis Queue

    Returns:
        Dict com status, resultado ou erro
    """
    from rq.job import Job
    from app.portal.workers import get_redis_connection

    try:
        conn = get_redis_connection()
        job = Job.fetch(job_id, connection=conn)

        status_map = {
            'queued': 'Na fila',
            'started': 'Processando no Odoo',
            'finished': 'Concluído',
            'failed': 'Falhou',
            'deferred': 'Adiado',
            'scheduled': 'Agendado',
            'stopped': 'Parado',
            'canceled': 'Cancelado',
        }

        result = {
            'job_id': job_id,
            'status': job.get_status(),
            'status_display': status_map.get(
                job.get_status(), job.get_status()
            ),
            'created_at': (
                job.created_at.isoformat() if job.created_at else None
            ),
            'started_at': (
                job.started_at.isoformat() if job.started_at else None
            ),
            'ended_at': (
                job.ended_at.isoformat() if job.ended_at else None
            ),
            'result': job.result if job.is_finished else None,
            'error': str(job.exc_info) if job.is_failed else None,
        }

        # Calcular duração
        if job.started_at and job.ended_at:
            result['duracao_segundos'] = (
                job.ended_at - job.started_at
            ).total_seconds()
        elif job.started_at:
            from datetime import timezone
            now = datetime.now(timezone.utc)
            started = job.started_at
            if started.tzinfo is None:
                from datetime import timezone
                started = started.replace(tzinfo=timezone.utc)
            result['duracao_segundos'] = (now - started).total_seconds()

        return result

    except Exception as e:
        return {
            'job_id': job_id,
            'status': 'not_found',
            'status_display': 'Não encontrado',
            'error': str(e)
        }
