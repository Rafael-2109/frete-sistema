# -*- coding: utf-8 -*-
"""
Rotas de Comprovantes de Pagamento de Boleto
=============================================

Hub com upload drag-and-drop de múltiplos PDFs,
extração via OCR e listagem dos comprovantes importados.

Rotas:
- /comprovantes/                       → Hub (upload + listagem)
- /comprovantes/api/upload             → Upload síncrono (poucos PDFs)
- /comprovantes/api/upload-batch       → Upload assíncrono via RQ (muitos PDFs)
- /comprovantes/api/batch/<id>/status  → Polling de progresso do batch
- /comprovantes/api/dados              → JSON para tabela

Autor: Sistema de Fretes
Data: 2026-01-29
"""

import os
import uuid
import logging
from io import BytesIO

from flask import render_template, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import desc
from werkzeug.utils import secure_filename

from app.financeiro.routes import financeiro_bp, UPLOAD_FOLDER
from app.financeiro.models_comprovante import ComprovantePagamentoBoleto
from app.utils.file_storage import get_file_storage

logger = logging.getLogger(__name__)

# Pasta de upload temporário para batches
COMPROVANTES_UPLOAD_DIR = os.path.join(UPLOAD_FOLDER, 'comprovantes')
os.makedirs(COMPROVANTES_UPLOAD_DIR, exist_ok=True)


# =============================================================================
# HUB - Tela principal com upload + listagem
# =============================================================================

@financeiro_bp.route('/comprovantes/')
@login_required
def comprovantes_hub():
    """Hub de Comprovantes: upload e listagem."""
    total = ComprovantePagamentoBoleto.query.count()
    return render_template(
        'financeiro/comprovantes_hub.html',
        total_comprovantes=total,
    )


# =============================================================================
# API - Upload síncrono (poucos PDFs, uso diário)
# =============================================================================

@financeiro_bp.route('/comprovantes/api/upload', methods=['POST'])
@login_required
def comprovantes_api_upload():
    """
    Upload síncrono de um ou mais PDFs de comprovantes.
    Ideal para poucos arquivos (1-20). Processa e retorna resumo.
    """
    from app.financeiro.services.comprovante_service import processar_pdf_comprovantes

    arquivos = request.files.getlist('arquivos')

    if not arquivos or all(not a.filename for a in arquivos):
        return jsonify({
            'sucesso': False,
            'mensagem': 'Nenhum arquivo enviado',
        }), 400

    # Filtrar apenas PDFs válidos
    arquivos_validos = [
        a for a in arquivos
        if a.filename and a.filename.lower().endswith('.pdf')
    ]

    if not arquivos_validos:
        return jsonify({
            'sucesso': False,
            'mensagem': 'Nenhum arquivo PDF válido encontrado',
        }), 400

    # Processar cada PDF
    resumo_geral = {
        'total_arquivos': len(arquivos_validos),
        'novos': 0,
        'duplicados': 0,
        'erros': 0,
        'arquivos': [],
    }

    for arquivo in arquivos_validos:
        nome = secure_filename(arquivo.filename)
        try:
            arquivo_bytes = arquivo.read()

            # Upload PDF ao S3 (antes do processamento OCR)
            s3_path = None
            try:
                storage = get_file_storage()
                pdf_io = BytesIO(arquivo_bytes)
                pdf_io.name = nome
                s3_path = storage.save_file(
                    file=pdf_io,
                    folder='comprovantes_pagamento',
                    allowed_extensions=['pdf'],
                )
            except Exception as e:
                logger.warning(f"Erro ao salvar PDF no S3: {nome}: {e}")

            resultado = processar_pdf_comprovantes(
                arquivo_bytes=arquivo_bytes,
                nome_arquivo=nome,
                usuario=current_user.nome if hasattr(current_user, 'nome') else current_user.username,
                arquivo_s3_path=s3_path,
            )

            resumo_geral['novos'] += resultado['novos']
            resumo_geral['duplicados'] += resultado['duplicados']
            resumo_geral['erros'] += resultado['erros']
            resumo_geral['arquivos'].append({
                'nome': nome,
                'novos': resultado['novos'],
                'duplicados': resultado['duplicados'],
                'erros': resultado['erros'],
                'detalhes': resultado['detalhes'],
            })

        except Exception as e:
            resumo_geral['erros'] += 1
            resumo_geral['arquivos'].append({
                'nome': nome,
                'novos': 0,
                'duplicados': 0,
                'erros': 1,
                'detalhes': [{
                    'pagina': 0,
                    'status': 'erro',
                    'mensagem': str(e),
                    'numero_agendamento': None,
                }],
            })

    resumo_geral['sucesso'] = True
    resumo_geral['mensagem'] = (
        f"{resumo_geral['novos']} novo(s), "
        f"{resumo_geral['duplicados']} duplicado(s), "
        f"{resumo_geral['erros']} erro(s)"
    )

    return jsonify(resumo_geral)


# =============================================================================
# API - Upload assíncrono em batch (muitos PDFs, via RQ)
# =============================================================================

@financeiro_bp.route('/comprovantes/api/upload-batch', methods=['POST'])
@login_required
def comprovantes_api_upload_batch():
    """
    Upload assíncrono de N PDFs via Redis Queue.

    Fluxo:
    1. Recebe PDFs via multipart/form-data
    2. Salva em disco: uploads/comprovantes/batch_{uuid}/
    3. Enfileira job no RQ
    4. Retorna batch_id para polling de progresso

    O frontend pode enviar em chunks de 50 para respeitar MAX_CONTENT_LENGTH.
    Se 'batch_id' for enviado como form field, adiciona ao batch existente.
    """
    from app.portal.workers import enqueue_job
    from app.financeiro.workers.comprovante_batch_jobs import processar_batch_comprovantes_job

    arquivos = request.files.getlist('arquivos')

    if not arquivos or all(not a.filename for a in arquivos):
        return jsonify({
            'sucesso': False,
            'mensagem': 'Nenhum arquivo enviado',
        }), 400

    # Filtrar apenas PDFs válidos
    arquivos_validos = [
        a for a in arquivos
        if a.filename and a.filename.lower().endswith('.pdf')
    ]

    if not arquivos_validos:
        return jsonify({
            'sucesso': False,
            'mensagem': 'Nenhum arquivo PDF válido encontrado',
        }), 400

    try:
        # Gerar batch_id
        batch_id = str(uuid.uuid4())

        # Criar pasta temporária para o batch
        pasta_batch = os.path.join(COMPROVANTES_UPLOAD_DIR, f'batch_{batch_id}')
        os.makedirs(pasta_batch, exist_ok=True)

        # Salvar PDFs no disco
        arquivos_info = []
        for arquivo in arquivos_validos:
            nome = secure_filename(arquivo.filename)
            # Garantir unicidade no nome (pode ter duplicatas de nomes)
            caminho = os.path.join(pasta_batch, f'{len(arquivos_info):05d}_{nome}')
            try:
                arquivo.save(caminho)
                arquivos_info.append({
                    'nome': nome,
                    'caminho': caminho,
                })
            except Exception as e:
                logger.warning(f"Erro ao salvar PDF {nome}: {e}")

        if not arquivos_info:
            return jsonify({
                'sucesso': False,
                'mensagem': 'Não foi possível salvar nenhum arquivo',
            }), 400

        # Nome do usuário
        usuario_nome = current_user.nome if hasattr(current_user, 'nome') else current_user.username

        # Enfileirar job no RQ
        job = enqueue_job(
            processar_batch_comprovantes_job,
            batch_id,
            arquivos_info,
            usuario_nome,
            queue_name='default',
            timeout='60m',
        )

        logger.info(
            f"[Comprovante Batch] Enfileirado - batch_id: {batch_id}, "
            f"arquivos: {len(arquivos_info)}, job_id: {job.id if job else 'N/A'}"
        )

        return jsonify({
            'sucesso': True,
            'batch_id': batch_id,
            'job_id': job.id if job else None,
            'total_arquivos': len(arquivos_info),
            'mensagem': f'{len(arquivos_info)} arquivo(s) enfileirado(s) para processamento',
        })

    except Exception as e:
        logger.error(f"Erro ao enfileirar batch de comprovantes: {e}")
        return jsonify({
            'sucesso': False,
            'mensagem': f'Erro ao enfileirar processamento: {str(e)}',
        }), 500


# =============================================================================
# API - Progresso do batch
# =============================================================================

@financeiro_bp.route('/comprovantes/api/batch/<batch_id>/status')
@login_required
def comprovantes_api_batch_status(batch_id):
    """Retorna progresso de um batch via Redis."""
    from app.financeiro.workers.comprovante_batch_jobs import obter_progresso_batch

    progresso = obter_progresso_batch(batch_id)

    if not progresso:
        return jsonify({
            'status': 'desconhecido',
            'mensagem': 'Batch não encontrado ou expirado',
        }), 404

    return jsonify(progresso)


# =============================================================================
# API - Upload OFX para vincular com comprovantes existentes
# =============================================================================

@financeiro_bp.route('/comprovantes/api/upload-ofx', methods=['POST'])
@login_required
def comprovantes_api_upload_ofx():
    """
    Upload de arquivo OFX para vincular com comprovantes existentes.

    Fluxo:
    1. Recebe arquivo .ofx via multipart/form-data
    2. Parseia OFX extraindo FITID + CHECKNUM de cada transação
    3. Vincula CHECKNUM com numero_agendamento dos comprovantes
    4. Busca linhas do extrato no Odoo (batch por período)
    5. Grava IDs do Odoo no comprovante vinculado
    6. Retorna resumo da vinculação
    """
    from app.financeiro.services.ofx_vinculacao_service import processar_ofx_e_vincular

    arquivo = request.files.get('arquivo_ofx')

    if not arquivo or not arquivo.filename:
        return jsonify({
            'sucesso': False,
            'mensagem': 'Nenhum arquivo OFX enviado',
        }), 400

    nome = secure_filename(arquivo.filename)
    if not nome.lower().endswith('.ofx'):
        return jsonify({
            'sucesso': False,
            'mensagem': 'Arquivo deve ser .ofx',
        }), 400

    try:
        arquivo_bytes = arquivo.read()

        usuario_nome = (
            current_user.nome
            if hasattr(current_user, 'nome')
            else current_user.username
        )

        resultado = processar_ofx_e_vincular(
            arquivo_bytes=arquivo_bytes,
            nome_arquivo=nome,
            usuario=usuario_nome,
        )

        return jsonify(resultado)

    except Exception as e:
        logger.error(f"[Comprovante OFX] Erro ao processar OFX: {e}")
        return jsonify({
            'sucesso': False,
            'mensagem': f'Erro ao processar OFX: {str(e)}',
        }), 500


# =============================================================================
# API - Dados para tabela
# =============================================================================

@financeiro_bp.route('/comprovantes/api/dados')
@login_required
def comprovantes_api_dados():
    """Retorna comprovantes em JSON para a tabela."""
    comprovantes = ComprovantePagamentoBoleto.query.order_by(
        desc(ComprovantePagamentoBoleto.importado_em)
    ).all()

    return jsonify({
        'sucesso': True,
        'dados': [c.to_dict() for c in comprovantes],
        'total': len(comprovantes),
    })


# =============================================================================
# API - Presigned URL do PDF original
# =============================================================================

@financeiro_bp.route('/comprovantes/api/<int:comprovante_id>/pdf')
@login_required
def comprovantes_api_pdf(comprovante_id):
    """
    Gera presigned URL (1h) do PDF original do comprovante no S3.

    Retorna JSON: { sucesso, url, arquivo, pagina }
    O frontend abre a URL em nova aba.
    """
    comp = ComprovantePagamentoBoleto.query.get_or_404(comprovante_id)

    if not comp.arquivo_s3_path:
        return jsonify({
            'sucesso': False,
            'mensagem': 'PDF nao disponivel no storage',
        }), 404

    try:
        storage = get_file_storage()
        url = storage.get_file_url(comp.arquivo_s3_path)

        if not url:
            return jsonify({
                'sucesso': False,
                'mensagem': 'Erro ao gerar URL do arquivo',
            }), 500

        return jsonify({
            'sucesso': True,
            'url': url,
            'arquivo': comp.arquivo_origem,
            'pagina': comp.pagina_origem,
        })

    except Exception as e:
        logger.error(f"Erro ao gerar URL PDF comprovante {comprovante_id}: {e}")
        return jsonify({
            'sucesso': False,
            'mensagem': str(e),
        }), 500
