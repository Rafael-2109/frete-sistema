# -*- coding: utf-8 -*-
"""
Jobs assíncronos para processamento de arquivos CNAB400 em lote
===============================================================

Executados via Redis Queue na fila 'default'

Fluxo:
1. Usuário faz upload de N arquivos .ret
2. Rota cria batch_id (UUID) e enfileira job
3. Worker processa cada arquivo ISOLADAMENTE
4. Progresso armazenado no Redis para acompanhamento em tempo real
5. Cada arquivo cria seu próprio CnabRetornoLote com batch_id preenchido

Timeout: 300 segundos (5 minutos) por arquivo
Timeout Batch: 1800 segundos (30 minutos) para batch completo

TRATAMENTO DE ERROS:
- Erro em arquivo 1 NÃO afeta processamento dos demais
- Cada arquivo tem commit isolado
- Duplicados detectados pelo service (hash SHA256)
"""

import json
import logging
import traceback
from contextlib import contextmanager
from datetime import datetime
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# Timeout para processamento de arquivo individual (5 minutos)
TIMEOUT_ARQUIVO = 300

# Timeout para batch completo (30 minutos)
TIMEOUT_BATCH = 1800


# ========================================
# PROGRESSO EM TEMPO REAL VIA REDIS
# ========================================


def _get_redis_connection():
    """Obtém conexão Redis do RQ"""
    try:
        from app.portal.workers import get_redis_connection
        return get_redis_connection()
    except Exception:
        return None


def _atualizar_progresso_batch(batch_id: str, progresso: dict):
    """
    Atualiza progresso do batch no Redis para acompanhamento em tempo real.

    Estrutura do progresso:
    {
        'batch_id': str,
        'status': 'processando' | 'concluido' | 'erro' | 'parcial',
        'total_arquivos': int,
        'arquivos_processados': int,
        'arquivos_sucesso': int,
        'arquivos_erro': int,
        'arquivo_atual': str,  # Nome do arquivo sendo processado
        'ultimo_update': str,  # ISO timestamp
        'lotes': [  # Lista de lotes criados
            {
                'arquivo_nome': str,
                'lote_id': int,
                'status': 'sucesso' | 'erro' | 'duplicado',
                'erro_mensagem': str | None,
                'registros': int
            }
        ],
        'iniciado_em': str,
        'concluido_em': str | None
    }
    """
    try:
        redis_conn = _get_redis_connection()
        if redis_conn:
            progresso['ultimo_update'] = datetime.now().isoformat()
            key = f'cnab_batch_progresso:{batch_id}'
            redis_conn.setex(key, 3600, json.dumps(progresso))  # Expira em 1 hora
            logger.debug(f"[CNAB Batch] Progresso atualizado: {progresso.get('arquivo_atual', 'N/A')}")
    except Exception as e:
        logger.warning(f"Erro ao atualizar progresso do batch CNAB: {e}")


def obter_progresso_batch(batch_id: str) -> dict | None:
    """Obtém progresso do batch do Redis"""
    try:
        redis_conn = _get_redis_connection()
        if redis_conn:
            key = f'cnab_batch_progresso:{batch_id}'
            data = redis_conn.get(key)
            if data:
                return json.loads(data)
    except Exception as e:
        logger.warning(f"Erro ao obter progresso do batch CNAB: {e}")
    return None


def _limpar_progresso_batch(batch_id: str):
    """Remove progresso do batch do Redis após conclusão"""
    try:
        redis_conn = _get_redis_connection()
        if redis_conn:
            key = f'cnab_batch_progresso:{batch_id}'
            redis_conn.delete(key)
    except Exception as e:
        logger.warning(f"Erro ao limpar progresso do batch CNAB: {e}")


# ========================================
# CONTEXT MANAGER SEGURO
# ========================================


@contextmanager
def _app_context_safe():
    """
    Context manager seguro para execução no worker.

    IMPORTANTE: Verifica se já existe um contexto ativo para evitar
    criar contextos aninhados que podem causar travamentos.
    """
    import sys
    import os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

    from flask import has_app_context

    # Se já existe contexto ativo, apenas executa o código
    if has_app_context():
        logger.debug("[Context] Reutilizando contexto Flask existente")
        yield
        return

    # Criar novo contexto apenas quando necessário
    from app import create_app
    app = create_app()
    logger.debug("[Context] Novo contexto Flask criado")

    with app.app_context():
        yield


# ========================================
# JOB PRINCIPAL: PROCESSAR BATCH DE ARQUIVOS
# ========================================


def processar_batch_cnab400_job(
    batch_id: str,
    arquivos_data: List[Dict[str, str]],
    usuario_nome: str
) -> Dict[str, Any]:
    """
    Processa batch de arquivos CNAB400 de forma assíncrona.

    Este job é enfileirado quando o usuário faz upload de múltiplos arquivos.
    Cada arquivo é processado ISOLADAMENTE:
    - Commit separado por arquivo
    - Erro em um não afeta os demais
    - Progresso atualizado no Redis após cada arquivo

    Args:
        batch_id: UUID do batch (usado para agrupar lotes e rastrear progresso)
        arquivos_data: Lista de dicionários com dados dos arquivos:
            [
                {'nome': 'arquivo1.ret', 'conteudo': '...'},
                {'nome': 'arquivo2.ret', 'conteudo': '...'},
            ]
        usuario_nome: Nome do usuário que fez o upload

    Returns:
        Dict com resultado:
        {
            'success': bool,
            'batch_id': str,
            'total_arquivos': int,
            'arquivos_sucesso': int,
            'arquivos_erro': int,
            'lotes': [
                {'arquivo_nome': str, 'lote_id': int, 'status': str, ...},
                ...
            ],
            'erro_geral': str | None
        }
    """
    logger.info(f"[CNAB Batch] Iniciando processamento - batch_id: {batch_id}")
    logger.info(f"[CNAB Batch] Total de arquivos: {len(arquivos_data)}")
    logger.info(f"[CNAB Batch] Usuário: {usuario_nome}")

    resultado = {
        'success': False,
        'batch_id': batch_id,
        'total_arquivos': len(arquivos_data),
        'arquivos_sucesso': 0,
        'arquivos_erro': 0,
        'lotes': [],
        'erro_geral': None
    }

    # Inicializar progresso
    progresso = {
        'batch_id': batch_id,
        'status': 'processando',
        'total_arquivos': len(arquivos_data),
        'arquivos_processados': 0,
        'arquivos_sucesso': 0,
        'arquivos_erro': 0,
        'arquivo_atual': None,
        'lotes': [],
        'iniciado_em': datetime.now().isoformat(),
        'concluido_em': None
    }
    _atualizar_progresso_batch(batch_id, progresso)

    try:
        with _app_context_safe():
            from app import db
            from app.financeiro.services.cnab400_processor_service import Cnab400ProcessorService

            processor = Cnab400ProcessorService()

            for idx, arquivo in enumerate(arquivos_data, 1):
                arquivo_nome = arquivo.get('nome', f'arquivo_{idx}.ret')
                arquivo_conteudo = arquivo.get('conteudo', '')

                logger.info(f"[CNAB Batch] Processando arquivo {idx}/{len(arquivos_data)}: {arquivo_nome}")

                # Atualizar progresso - arquivo atual
                progresso['arquivo_atual'] = f"{arquivo_nome} ({idx}/{len(arquivos_data)})"
                _atualizar_progresso_batch(batch_id, progresso)

                lote_info = {
                    'arquivo_nome': arquivo_nome,
                    'lote_id': None,
                    'status': 'erro',
                    'erro_mensagem': None,
                    'registros': 0
                }

                try:
                    # Processar arquivo com batch_id
                    lote = processor.processar_arquivo(
                        arquivo_conteudo=arquivo_conteudo,
                        arquivo_nome=arquivo_nome,
                        usuario=usuario_nome,
                        batch_id=batch_id
                    )

                    # Sucesso!
                    lote_info['lote_id'] = lote.id
                    lote_info['status'] = 'sucesso'
                    lote_info['registros'] = lote.total_registros or 0

                    resultado['arquivos_sucesso'] += 1
                    progresso['arquivos_sucesso'] += 1

                    logger.info(
                        f"[CNAB Batch] ✅ {arquivo_nome} processado - "
                        f"Lote #{lote.id} com {lote.total_registros} registros"
                    )

                except ValueError as e:
                    # Erros esperados: duplicado, arquivo inválido
                    erro_msg = str(e)
                    lote_info['erro_mensagem'] = erro_msg

                    # Verificar se é duplicado
                    if 'já foi importado' in erro_msg.lower() or 'mesmo conteúdo' in erro_msg.lower():
                        lote_info['status'] = 'duplicado'
                    else:
                        lote_info['status'] = 'erro'

                    resultado['arquivos_erro'] += 1
                    progresso['arquivos_erro'] += 1

                    logger.warning(f"[CNAB Batch] ⚠️ {arquivo_nome}: {erro_msg}")

                except Exception as e:
                    # Erros inesperados
                    erro_msg = f"Erro inesperado: {str(e)}"
                    lote_info['erro_mensagem'] = erro_msg
                    lote_info['status'] = 'erro'

                    resultado['arquivos_erro'] += 1
                    progresso['arquivos_erro'] += 1

                    logger.error(f"[CNAB Batch] ❌ {arquivo_nome}: {erro_msg}")
                    logger.error(traceback.format_exc())

                    # Rollback para limpar sessão após erro
                    db.session.rollback()

                # Adicionar info do lote ao resultado
                resultado['lotes'].append(lote_info)
                progresso['lotes'].append(lote_info)

                # Atualizar progresso - arquivo processado
                progresso['arquivos_processados'] += 1
                _atualizar_progresso_batch(batch_id, progresso)

            # Definir status final
            if resultado['arquivos_erro'] == 0:
                resultado['success'] = True
                progresso['status'] = 'concluido'
            elif resultado['arquivos_sucesso'] > 0:
                resultado['success'] = True  # Parcial conta como sucesso
                progresso['status'] = 'parcial'
            else:
                resultado['success'] = False
                progresso['status'] = 'erro'

            progresso['concluido_em'] = datetime.now().isoformat()
            progresso['arquivo_atual'] = None
            _atualizar_progresso_batch(batch_id, progresso)

            logger.info(
                f"[CNAB Batch] Batch {batch_id} finalizado - "
                f"Sucesso: {resultado['arquivos_sucesso']}, "
                f"Erro: {resultado['arquivos_erro']}"
            )

    except Exception as e:
        erro_geral = f"Erro crítico no job: {str(e)}"
        resultado['erro_geral'] = erro_geral
        resultado['success'] = False

        progresso['status'] = 'erro'
        progresso['erro_geral'] = erro_geral
        progresso['concluido_em'] = datetime.now().isoformat()
        _atualizar_progresso_batch(batch_id, progresso)

        logger.error(f"[CNAB Batch] Erro crítico: {erro_geral}")
        logger.error(traceback.format_exc())

    return resultado


# ========================================
# FUNÇÕES AUXILIARES
# ========================================


def verificar_status_batch(batch_id: str) -> Dict[str, Any]:
    """
    Verifica status de um batch consultando Redis e banco de dados.

    Usado pelo endpoint GET /cnab400/batch/<batch_id>/status

    Args:
        batch_id: UUID do batch

    Returns:
        Dict com status completo do batch
    """
    # Primeiro tentar Redis (mais rápido, tempo real)
    progresso_redis = obter_progresso_batch(batch_id)

    if progresso_redis:
        return {
            'fonte': 'redis',
            'batch_id': batch_id,
            **progresso_redis
        }

    # Se não está no Redis, buscar no banco
    try:
        with _app_context_safe():
            from app.financeiro.models import CnabRetornoLote

            lotes = CnabRetornoLote.query.filter_by(batch_id=batch_id).all()

            if not lotes:
                return {
                    'fonte': 'banco',
                    'batch_id': batch_id,
                    'status': 'nao_encontrado',
                    'mensagem': 'Batch não encontrado no Redis nem no banco'
                }

            # Agregar informações dos lotes
            return {
                'fonte': 'banco',
                'batch_id': batch_id,
                'status': 'concluido',
                'total_arquivos': len(lotes),
                'arquivos_sucesso': len(lotes),
                'arquivos_erro': 0,
                'lotes': [
                    {
                        'arquivo_nome': lote.arquivo_nome,
                        'lote_id': lote.id,
                        'status': lote.status,
                        'registros': lote.total_registros or 0,
                        'processado_por': lote.processado_por,
                        'data_processamento': lote.data_processamento.isoformat() if lote.data_processamento else None
                    }
                    for lote in lotes
                ]
            }

    except Exception as e:
        logger.error(f"Erro ao verificar status do batch {batch_id}: {e}")
        return {
            'fonte': 'erro',
            'batch_id': batch_id,
            'status': 'erro',
            'mensagem': str(e)
        }
