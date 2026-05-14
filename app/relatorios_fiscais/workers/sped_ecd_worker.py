# -*- coding: utf-8 -*-
"""
Worker RQ para geracao assincrona de SPED ECD Centralizado
============================================================

Job RQ assincrono — geracao do arquivo demora 5-30 min para ano completo
(R4 do pre-mortem). Roda na fila 'sped_ecd' do worker_atacadao.

Fluxo:
1. Rota POST /relatorios-fiscais/sped-ecd/gerar enfileira job
2. Worker busca dados Odoo + monta arquivo + uploads S3
3. Frontend faz polling em /sped-ecd/status/<job_id>
4. Quando finished: redireciona para download via presigned URL

Autor: Sistema de Fretes
Data: 2026-05-14
"""

import json
import logging
import traceback
from datetime import datetime
from typing import Any, Dict

from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)


# ============================================================
# REDIS HELPERS (progresso)
# ============================================================

PROGRESSO_KEY_PREFIX = 'sped_ecd_progresso'


def _get_redis_connection():
    """Obtem conexao Redis do RQ."""
    try:
        from app.portal.workers import get_redis_connection
        return get_redis_connection()
    except Exception:
        return None


def _atualizar_progresso(job_id: str, progresso: dict):
    """Salva progresso no Redis (TTL 2h) para polling do frontend."""
    try:
        redis_conn = _get_redis_connection()
        if redis_conn:
            from app.relatorios_fiscais.services.sped_ecd_constantes import PROGRESSO_TTL
            progresso['ultimo_update'] = agora_utc_naive().isoformat()
            key = f'{PROGRESSO_KEY_PREFIX}:{job_id}'
            redis_conn.setex(key, PROGRESSO_TTL, json.dumps(progresso, default=str))
    except Exception as e:
        logger.warning(f'[SPED ECD Worker] Erro atualizar progresso: {e}')


def obter_progresso_sped(job_id: str) -> dict | None:
    """Obtem progresso do Redis (chamado pela rota /status/<job_id>)."""
    try:
        redis_conn = _get_redis_connection()
        if redis_conn:
            key = f'{PROGRESSO_KEY_PREFIX}:{job_id}'
            data = redis_conn.get(key)
            if data:
                return json.loads(data)
    except Exception as e:
        logger.warning(f'[SPED ECD Worker] Erro obter progresso: {e}')
    return None


# ============================================================
# JOB PRINCIPAL
# ============================================================

def gerar_sped_ecd_async(
    date_ini_iso: str,
    date_fim_iso: str,
    qualif_socio: str,
    user_id: int,
    user_nome: str,
    notas_explicativas: str = '',
) -> Dict[str, Any]:
    """
    Job RQ — gera SPED ECD centralizado e faz upload S3.

    V1.2: cpf_contador e email_contato removidos da assinatura — agora
    sao constantes em sped_ecd_constantes.py (CONTADOR_CPF, CONTADOR_EMAIL).

    Args:
        date_ini_iso: 'YYYY-MM-DD'
        date_fim_iso: 'YYYY-MM-DD'
        qualif_socio: codigo qualif (001-999)
        user_id: ID usuario solicitante
        user_nome: nome usuario (para logs)
        notas_explicativas: texto opcional para J800 (V1.1)

    Returns:
        {
            'sucesso': bool,
            's3_key': str (chave S3 do arquivo gerado),
            'tamanho_bytes': int,
            'duracao_segundos': float,
            'erro': str | None,
        }
    """
    from rq import get_current_job
    from app.financeiro.workers.utils import app_context_safe

    inicio = agora_utc_naive()
    current_job = get_current_job()
    job_id = current_job.id if current_job else 'unknown'

    logger.info(
        f'[SPED ECD Worker] Iniciando job {job_id} | '
        f'Periodo: {date_ini_iso} a {date_fim_iso} | '
        f'Usuario: {user_nome} (id={user_id})'
    )

    resultado: Dict[str, Any] = {
        'sucesso': False,
        's3_key': None,
        'tamanho_bytes': 0,
        'duracao_segundos': 0,
        'erro': None,
        'periodo': f'{date_ini_iso} a {date_fim_iso}',
        'usuario': user_nome,
    }

    progresso = {
        'job_id': job_id,
        'status': 'processando',
        'etapa': 'iniciando',
        'mensagem': 'Conectando ao Odoo...',
        'inicio': inicio.isoformat(),
    }
    _atualizar_progresso(job_id, progresso)

    try:
        with app_context_safe():
            from app.odoo.utils.connection import get_odoo_connection
            from app.relatorios_fiscais.services.sped_ecd_service import (
                gerar_sped_ecd_centralizado,
                upload_sped_to_s3,
            )

            # Parsear datas
            date_ini = datetime.strptime(date_ini_iso, '%Y-%m-%d').date()
            date_fim = datetime.strptime(date_fim_iso, '%Y-%m-%d').date()

            # Conectar Odoo
            connection = get_odoo_connection()
            if not connection.authenticate():
                raise RuntimeError('Falha na autenticacao com Odoo')

            progresso['mensagem'] = 'Conexao Odoo OK. Iniciando extracao de dados...'
            _atualizar_progresso(job_id, progresso)

            # Callback de progresso (chamado pelo service em cada etapa)
            def cb_progresso(info: dict):
                progresso.update(info)
                progresso['ultimo_update'] = agora_utc_naive().isoformat()
                _atualizar_progresso(job_id, progresso)

            # Gerar arquivo SPED
            params = {
                'date_ini': date_ini,
                'date_fim': date_fim,
                'qualif_socio': qualif_socio,
                'notas_explicativas': notas_explicativas,
            }

            sped_buffer = gerar_sped_ecd_centralizado(
                connection, params, progresso_callback=cb_progresso
            )

            # Upload S3
            progresso['etapa'] = 'upload_s3'
            progresso['mensagem'] = 'Enviando arquivo para S3...'
            _atualizar_progresso(job_id, progresso)

            sped_buffer.seek(0, 2)  # SEEK_END
            tamanho = sped_buffer.tell()
            sped_buffer.seek(0)

            s3_key = upload_sped_to_s3(sped_buffer, user_id, date_ini, date_fim)

            # Sucesso
            duracao = (agora_utc_naive() - inicio).total_seconds()
            resultado['sucesso'] = True
            resultado['s3_key'] = s3_key
            resultado['tamanho_bytes'] = tamanho
            resultado['duracao_segundos'] = round(duracao, 1)

            progresso['status'] = 'concluido'
            progresso['etapa'] = 'finalizado'
            progresso['mensagem'] = f'Arquivo gerado com sucesso ({tamanho / 1024 / 1024:.2f} MB)'
            progresso['s3_key'] = s3_key
            progresso['tamanho_bytes'] = tamanho
            progresso['duracao_segundos'] = duracao
            progresso['fim'] = agora_utc_naive().isoformat()
            _atualizar_progresso(job_id, progresso)

            logger.info(
                f'[SPED ECD Worker] Job {job_id} CONCLUIDO em {duracao:.1f}s | '
                f'Arquivo: {tamanho / 1024 / 1024:.2f} MB | s3_key: {s3_key}'
            )

            return resultado

    except Exception as e:
        duracao = (agora_utc_naive() - inicio).total_seconds()
        resultado['erro'] = str(e)
        resultado['duracao_segundos'] = round(duracao, 1)

        logger.error(f'[SPED ECD Worker] Job {job_id} FALHOU: {e}')
        logger.error(traceback.format_exc())

        progresso['status'] = 'erro'
        progresso['etapa'] = 'erro'
        progresso['mensagem'] = f'Erro: {str(e)[:200]}'
        progresso['fim'] = agora_utc_naive().isoformat()
        _atualizar_progresso(job_id, progresso)

        return resultado
