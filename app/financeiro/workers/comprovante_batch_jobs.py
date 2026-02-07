# -*- coding: utf-8 -*-
"""
Jobs assíncronos para processamento de comprovantes de pagamento em lote
========================================================================

Executados via Redis Queue na fila 'default'.

Fluxo:
1. Usuário faz upload de N PDFs via navegador
2. Rota faz upload dos PDFs para S3 e enfileira job com batch_id (UUID)
3. Worker baixa cada PDF do S3 e processa ISOLADAMENTE via OCR
4. Progresso armazenado no Redis para acompanhamento em tempo real
5. PDFs temporários removidos do S3 após processamento

Timeout: 60 minutos para batch completo (OCR é CPU-intensivo)

TRATAMENTO DE ERROS:
- Erro em arquivo 1 NÃO afeta processamento dos demais
- Cada comprovante tem commit isolado (via service)
- Retry automático em erros de SSL/conexão
"""

import json
import logging
import os
import traceback
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Timeout para batch completo (60 minutos — OCR consome tempo)
TIMEOUT_BATCH = 3600


# ========================================
# PROGRESSO EM TEMPO REAL VIA REDIS
# ========================================

def _get_redis_connection():
    """Obtém conexão Redis do RQ."""
    try:
        from app.portal.workers import get_redis_connection
        return get_redis_connection()
    except Exception:
        return None


def _atualizar_progresso(batch_id: str, progresso: dict):
    """
    Atualiza progresso do batch no Redis.

    Estrutura do progresso:
    {
        'batch_id': str,
        'status': 'processando' | 'concluido' | 'erro' | 'parcial',
        'total_arquivos': int,
        'arquivos_processados': int,
        'novos': int,
        'duplicados': int,
        'erros': int,
        'arquivo_atual': str,
        'ultimo_update': str,
        'detalhes': [...],
        'iniciado_em': str,
        'concluido_em': str | None
    }
    """
    try:
        redis_conn = _get_redis_connection()
        if redis_conn:
            progresso['ultimo_update'] = datetime.now().isoformat()
            key = f'comprovante_batch_progresso:{batch_id}'
            redis_conn.setex(key, 3600, json.dumps(progresso))  # Expira em 1 hora
    except Exception as e:
        logger.warning(f"Erro ao atualizar progresso do batch comprovante: {e}")


def obter_progresso_batch(batch_id: str) -> dict | None:
    """Obtém progresso do batch do Redis."""
    try:
        redis_conn = _get_redis_connection()
        if redis_conn:
            key = f'comprovante_batch_progresso:{batch_id}'
            data = redis_conn.get(key)
            if data:
                return json.loads(data)
    except Exception as e:
        logger.warning(f"Erro ao obter progresso do batch comprovante: {e}")
    return None


# ========================================
# CONTEXT MANAGER SEGURO
# ========================================

@contextmanager
def _app_context_safe():
    """
    Context manager seguro para execução no worker.

    Verifica se já existe um contexto ativo para evitar
    criar contextos aninhados que podem causar travamentos.
    """
    import sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

    from flask import has_app_context

    # Se já existe contexto ativo, apenas executa
    if has_app_context():
        logger.debug("[Context] Reutilizando contexto Flask existente")
        yield
        return

    # Criar novo contexto
    from app import create_app
    app = create_app()
    logger.debug("[Context] Novo contexto Flask criado para comprovante batch")

    with app.app_context():
        yield


# ========================================
# JOB PRINCIPAL: PROCESSAR BATCH DE PDFs
# ========================================

def processar_batch_comprovantes_job(
    batch_id: str,
    arquivos_info: List[Dict[str, str]],
    usuario_nome: str
) -> Dict[str, Any]:
    """
    Processa batch de comprovantes PDF de forma assíncrona.

    Cada arquivo é processado ISOLADAMENTE:
    - Baixa PDF do S3 (upload feito pelo web service)
    - OCR via tesserocr
    - Commit separado por comprovante
    - Erro em um não afeta os demais
    - Progresso atualizado no Redis após cada arquivo
    - PDFs temporários removidos do S3 após processamento

    Args:
        batch_id: UUID do batch
        arquivos_info: Lista de dicts com path S3 e nome dos PDFs:
            [{'nome': 'comprovante.pdf', 's3_path': 'comprovantes_pagamento/batch/...'}, ...]
        usuario_nome: Nome do usuário que fez upload

    Returns:
        Dict com resultado consolidado
    """
    logger.info(f"[Comprovante Batch] Iniciando - batch_id: {batch_id}")
    logger.info(f"[Comprovante Batch] Total de arquivos: {len(arquivos_info)}")
    logger.info(f"[Comprovante Batch] Usuário: {usuario_nome}")

    resultado = {
        'success': False,
        'batch_id': batch_id,
        'total_arquivos': len(arquivos_info),
        'novos': 0,
        'duplicados': 0,
        'erros': 0,
        'detalhes': [],
        'erro_geral': None,
    }

    # Inicializar progresso
    progresso = {
        'batch_id': batch_id,
        'status': 'processando',
        'total_arquivos': len(arquivos_info),
        'arquivos_processados': 0,
        'novos': 0,
        'duplicados': 0,
        'erros': 0,
        'arquivo_atual': None,
        'detalhes': [],
        'iniciado_em': datetime.now().isoformat(),
        'concluido_em': None,
    }
    _atualizar_progresso(batch_id, progresso)

    try:
        with _app_context_safe():
            from io import BytesIO
            from app.financeiro.services.comprovante_service import processar_pdf_comprovantes
            from app.financeiro.services.comprovante_pix_service import processar_pdf_comprovantes_pix
            from app.financeiro.parsers.dispatcher import detectar_tipo_e_banco
            from app.utils.file_storage import get_file_storage

            for idx, arq in enumerate(arquivos_info, 1):
                nome = arq.get('nome', f'arquivo_{idx}.pdf')
                batch_s3_path = arq.get('s3_path', '')

                logger.info(f"[Comprovante Batch] Processando {idx}/{len(arquivos_info)}: {nome}")

                # Atualizar progresso — arquivo atual
                progresso['arquivo_atual'] = f"{nome} ({idx}/{len(arquivos_info)})"
                _atualizar_progresso(batch_id, progresso)

                try:
                    # Baixar PDF do S3 (arquivo temporário do batch)
                    if not batch_s3_path:
                        raise FileNotFoundError(f"Caminho S3 não informado para: {nome}")

                    storage = get_file_storage()
                    pdf_bytes = storage.download_file(batch_s3_path)
                    if not pdf_bytes:
                        raise FileNotFoundError(f"Não foi possível baixar PDF do storage: {batch_s3_path}")

                    # Upload PDF definitivo ao S3 (path permanente)
                    s3_path_definitivo = None
                    try:
                        pdf_io = BytesIO(pdf_bytes)
                        pdf_io.name = nome
                        s3_path_definitivo = storage.save_file(
                            file=pdf_io,
                            folder='comprovantes_pagamento',
                            allowed_extensions=['pdf'],
                        )
                    except Exception as e:
                        logger.warning(f"[Comprovante Batch] Erro ao salvar PDF definitivo no S3: {nome}: {e}")

                    # Detectar tipo automaticamente (boleto ou PIX)
                    tipo_detectado, banco_det = detectar_tipo_e_banco(pdf_bytes)

                    if tipo_detectado == 'pix':
                        res = processar_pdf_comprovantes_pix(
                            arquivo_bytes=pdf_bytes,
                            nome_arquivo=nome,
                            usuario=usuario_nome,
                            arquivo_s3_path=s3_path_definitivo,
                        )
                    else:
                        # Default: boleto (OCR + persistência com retry)
                        res = processar_pdf_comprovantes(
                            arquivo_bytes=pdf_bytes,
                            nome_arquivo=nome,
                            usuario=usuario_nome,
                            arquivo_s3_path=s3_path_definitivo,
                        )

                    # Acumular stats
                    resultado['novos'] += res['novos']
                    resultado['duplicados'] += res['duplicados']
                    resultado['erros'] += res['erros']

                    progresso['novos'] += res['novos']
                    progresso['duplicados'] += res['duplicados']
                    progresso['erros'] += res['erros']

                    # Adicionar detalhes (limitar a últimos 200 para não estourar Redis)
                    for det in res['detalhes']:
                        det['arquivo'] = nome
                    resultado['detalhes'].extend(res['detalhes'])
                    progresso['detalhes'] = resultado['detalhes'][-200:]

                    logger.info(
                        f"[Comprovante Batch] ✅ {nome}: "
                        f"{res['novos']} novo(s), {res['duplicados']} dup, {res['erros']} erro(s)"
                    )

                except Exception as e:
                    logger.error(f"[Comprovante Batch] ❌ {nome}: {e}")
                    logger.error(traceback.format_exc())

                    resultado['erros'] += 1
                    progresso['erros'] += 1

                    erro_det = {
                        'pagina': 0,
                        'status': 'erro',
                        'mensagem': str(e),
                        'numero_agendamento': None,
                        'arquivo': nome,
                    }
                    resultado['detalhes'].append(erro_det)
                    progresso['detalhes'] = resultado['detalhes'][-200:]

                finally:
                    # Limpar PDF temporário do batch no S3 após processar
                    try:
                        if batch_s3_path:
                            storage = get_file_storage()
                            storage.delete_file(batch_s3_path)
                    except Exception as e:
                        logger.warning(f"Erro ao remover PDF temporário do S3 {batch_s3_path}: {e}")

                # Atualizar progresso — arquivo processado
                progresso['arquivos_processados'] = idx
                _atualizar_progresso(batch_id, progresso)

        # Finalizar
        resultado['success'] = True
        progresso['status'] = 'concluido'
        progresso['concluido_em'] = datetime.now().isoformat()
        progresso['arquivo_atual'] = None

    except Exception as e:
        logger.error(f"[Comprovante Batch] Erro geral: {e}")
        logger.error(traceback.format_exc())

        resultado['erro_geral'] = str(e)
        progresso['status'] = 'erro'
        progresso['concluido_em'] = datetime.now().isoformat()
        progresso['arquivo_atual'] = f"ERRO: {str(e)}"

    _atualizar_progresso(batch_id, progresso)

    # Limpar arquivos restantes do S3 (em caso de erro em algum arquivo)
    try:
        if arquivos_info:
            with _app_context_safe():
                from app.utils.file_storage import get_file_storage as _get_storage
                storage = _get_storage()
                for arq in arquivos_info:
                    s3_key = arq.get('s3_path', '')
                    if s3_key:
                        try:
                            storage.delete_file(s3_key)
                        except Exception:
                            pass  # Já pode ter sido deletado no finally
                logger.info(f"[Comprovante Batch] Limpeza S3 concluída para batch {batch_id}")
    except Exception as e:
        logger.warning(f"Erro ao limpar batch S3: {e}")

    logger.info(
        f"[Comprovante Batch] Concluído - batch_id: {batch_id} | "
        f"Novos: {resultado['novos']}, Dup: {resultado['duplicados']}, Erros: {resultado['erros']}"
    )

    return resultado
