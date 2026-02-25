# -*- coding: utf-8 -*-
"""
Job assincrono para correcao de datas de NFs de Credito
========================================================

Executado via Redis Queue na fila 'default'.

Fluxo:
1. Usuario seleciona documentos e solicita correcao
2. Rota enfileira job (retorna job_id imediatamente)
3. Worker processa: corrige cada documento no Odoo (XML-RPC)
4. Progresso atualizado no Redis a cada documento (polling pelo frontend)
5. Status final retornado via RQ result

Timeout: 600 segundos (10 minutos)
Cada documento leva ~5-15s (8-11 chamadas XML-RPC ao Odoo)

Autor: Sistema de Fretes
Data: 25/02/2026
"""

import json
import logging
import time
import traceback
from typing import Dict, Any, List

from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)

# Timeout para lote completo (10 minutos)
TIMEOUT_CORRECAO_DATAS = 600

# Intervalo entre documentos para nao saturar Odoo (segundos)
SLEEP_ENTRE_DOCS = 0.2

# A cada N documentos, libera objetos do SQLAlchemy
EXPIRE_BATCH_SIZE = 10


# ========================================
# REDIS CONNECTION
# ========================================

def _get_redis_connection():
    """Obtem conexao Redis do RQ."""
    try:
        from app.portal.workers import get_redis_connection
        return get_redis_connection()
    except Exception:
        return None


# ========================================
# PROGRESSO EM TEMPO REAL VIA REDIS
# ========================================

def _atualizar_progresso(job_id: str, progresso: dict):
    """
    Atualiza progresso da correcao no Redis para acompanhamento em tempo real.

    Estrutura do progresso:
    {
        'job_id': str,
        'status': 'processando' | 'concluido' | 'concluido_com_erros' | 'erro',
        'total': int,
        'processados': int,
        'sucesso': int,
        'erros': int,
        'item_atual': str,
        'ultimo_update': str,
        'detalhes': [...]
    }
    """
    try:
        redis_conn = _get_redis_connection()
        if redis_conn:
            progresso['ultimo_update'] = agora_utc_naive().isoformat()
            key = f'correcao_datas_progresso:{job_id}'
            redis_conn.setex(key, 3600, json.dumps(progresso))  # Expira em 1 hora
    except Exception as e:
        logger.warning(f"Erro ao atualizar progresso: {e}")


def obter_progresso_correcao(job_id: str) -> dict | None:
    """Obtem progresso da correcao do Redis."""
    try:
        redis_conn = _get_redis_connection()
        if redis_conn:
            key = f'correcao_datas_progresso:{job_id}'
            data = redis_conn.get(key)
            if data:
                return json.loads(data)
    except Exception as e:
        logger.warning(f"Erro ao obter progresso: {e}")
    return None


# ========================================
# JOB PRINCIPAL: PROCESSAR CORRECAO
# ========================================

def processar_correcao_datas_job(
    ids: List[int],
    usuario: str
) -> Dict[str, Any]:
    """
    Job RQ para correcao de datas de NFs de Credito.

    Fluxo:
    1. Instanciar CorrecaoDatasService
    2. Loop por documento com try/except + per-doc commit
    3. Atualizar progresso no Redis a cada doc
    4. sleep(0.2) entre documentos para nao saturar Odoo
    5. expire_all() a cada 10 docs para liberar memoria

    Args:
        ids: Lista de IDs da tabela correcao_data_nf_credito
        usuario: Nome do usuario que solicitou

    Returns:
        dict: {sucesso, total, corrigidos, erros, detalhes, tempo_segundos}
    """
    from rq import get_current_job
    from app.financeiro.workers.utils import app_context_safe

    inicio = agora_utc_naive()

    current_job = get_current_job()
    job_id = current_job.id if current_job else 'unknown'

    logger.info(
        f"[Job CorrecaoDatas] Iniciando correcao de {len(ids)} documentos "
        f"(Job ID: {job_id}, Usuario: {usuario})"
    )

    resultado = {
        'sucesso': False,
        'total': len(ids),
        'corrigidos': 0,
        'erros': 0,
        'detalhes': [],
        'tempo_segundos': 0,
        'error': None,
        'usuario': usuario
    }

    # Progresso inicial
    progresso = {
        'job_id': job_id,
        'status': 'processando',
        'total': len(ids),
        'processados': 0,
        'sucesso_count': 0,
        'erros': 0,
        'item_atual': 'Conectando ao Odoo...',
        'inicio': agora_utc_naive().isoformat(),
        'detalhes': []
    }
    _atualizar_progresso(job_id, progresso)

    try:
        with app_context_safe():
            from app import db
            from app.financeiro.models_correcao_datas import CorrecaoDataNFCredito
            from app.financeiro.services.correcao_datas_service import CorrecaoDatasService

            service = CorrecaoDatasService()

            if not service._conectar_odoo():
                resultado['error'] = 'Falha na conexao com Odoo'
                progresso['status'] = 'erro'
                progresso['item_atual'] = resultado['error']
                _atualizar_progresso(job_id, progresso)
                return resultado

            progresso['item_atual'] = 'Conexao Odoo OK. Iniciando correcoes...'
            _atualizar_progresso(job_id, progresso)

            for idx, correcao_id in enumerate(ids):
                correcao = db.session.get(CorrecaoDataNFCredito, correcao_id) if correcao_id else None
                if not correcao:
                    resultado['erros'] += 1
                    detalhe = {
                        'id': correcao_id,
                        'nome': f'ID {correcao_id}',
                        'sucesso': False,
                        'erro': 'Registro nao encontrado'
                    }
                    resultado['detalhes'].append(detalhe)
                    progresso['erros'] += 1
                    progresso['processados'] = idx + 1
                    progresso['item_atual'] = f'ID {correcao_id} nao encontrado ({idx + 1}/{len(ids)})'
                    _atualizar_progresso(job_id, progresso)
                    continue

                # Atualizar progresso com documento atual
                label = correcao.nome_documento or f'ID {correcao_id}'
                progresso['item_atual'] = f'{label} ({idx + 1}/{len(ids)})'
                _atualizar_progresso(job_id, progresso)

                try:
                    sucesso = service._corrigir_documento(
                        correcao.odoo_move_id,
                        correcao.data_correta.isoformat()
                    )

                    if sucesso:
                        # Buscar nova data das linhas
                        data_linhas_depois = service._buscar_data_linhas(correcao.odoo_move_id)

                        correcao.status = 'corrigido'
                        correcao.data_lancamento_depois = correcao.data_correta
                        if data_linhas_depois:
                            from datetime import datetime
                            correcao.data_lancamento_linhas_depois = (
                                datetime.strptime(data_linhas_depois, '%Y-%m-%d').date()
                            )
                        correcao.corrigido_em = agora_utc_naive()
                        correcao.corrigido_por = usuario

                        resultado['corrigidos'] += 1
                        progresso['sucesso_count'] += 1
                        resultado['detalhes'].append({
                            'id': correcao_id,
                            'nome': correcao.nome_documento,
                            'sucesso': True
                        })
                    else:
                        raise Exception("Falha na API do Odoo")

                except Exception as e:
                    correcao.status = 'erro'
                    correcao.erro_mensagem = str(e)[:500]
                    resultado['erros'] += 1
                    progresso['erros'] += 1
                    resultado['detalhes'].append({
                        'id': correcao_id,
                        'nome': correcao.nome_documento,
                        'sucesso': False,
                        'erro': str(e)[:200]
                    })
                    logger.error(f"[Job CorrecaoDatas] Erro no doc {correcao.nome_documento}: {e}")

                # Per-doc commit para isolamento de erros
                db.session.commit()

                progresso['processados'] = idx + 1
                _atualizar_progresso(job_id, progresso)

                # Libera objetos do SQLAlchemy a cada EXPIRE_BATCH_SIZE docs
                if (idx + 1) % EXPIRE_BATCH_SIZE == 0:
                    db.session.expire_all()
                    logger.debug(
                        f"[Job CorrecaoDatas] expire_all() apos {idx + 1} docs "
                        f"(sucesso: {resultado['corrigidos']}, erros: {resultado['erros']})"
                    )

                # Sleep entre documentos para nao saturar Odoo
                if idx < len(ids) - 1:
                    time.sleep(SLEEP_ENTRE_DOCS)

            # Finalizar
            tempo_total = (agora_utc_naive() - inicio).total_seconds()
            resultado['tempo_segundos'] = round(tempo_total, 1)
            resultado['sucesso'] = resultado['erros'] == 0

            # Progresso final
            progresso['status'] = 'concluido' if resultado['erros'] == 0 else 'concluido_com_erros'
            progresso['processados'] = len(ids)
            progresso['item_atual'] = 'Concluido!'
            progresso['fim'] = agora_utc_naive().isoformat()
            progresso['tempo_segundos'] = resultado['tempo_segundos']
            _atualizar_progresso(job_id, progresso)

            logger.info(
                f"[Job CorrecaoDatas] Concluido em {tempo_total:.1f}s - "
                f"Sucesso: {resultado['corrigidos']}, Erros: {resultado['erros']}"
            )

            return resultado

    except Exception as e:
        tempo_total = (agora_utc_naive() - inicio).total_seconds()
        resultado['tempo_segundos'] = round(tempo_total, 1)
        resultado['error'] = str(e)
        resultado['sucesso'] = False

        logger.error(f"[Job CorrecaoDatas] Erro geral: {e}")
        logger.error(traceback.format_exc())

        progresso['status'] = 'erro'
        progresso['item_atual'] = f'Erro: {str(e)[:100]}'
        progresso['fim'] = agora_utc_naive().isoformat()
        _atualizar_progresso(job_id, progresso)

        return resultado
