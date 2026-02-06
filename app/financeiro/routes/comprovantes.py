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

import uuid
import logging
from io import BytesIO

from flask import render_template, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import desc
from werkzeug.utils import secure_filename

from app.financeiro.routes import financeiro_bp
from app.financeiro.models_comprovante import (
    ComprovantePagamentoBoleto,
    LancamentoComprovante,
)
from app.utils.file_storage import get_file_storage

logger = logging.getLogger(__name__)

# Pasta S3 para batches temporários de comprovantes
COMPROVANTES_BATCH_S3_FOLDER = 'comprovantes_pagamento/batch'


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
    2. Faz upload para S3: comprovantes_pagamento/batch/{batch_id}/
    3. Enfileira job no RQ com paths S3
    4. Retorna batch_id para polling de progresso

    O frontend pode enviar em chunks de 50 para respeitar MAX_CONTENT_LENGTH.
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

        # Upload PDFs para S3 (intermediário entre web service e worker)
        storage = get_file_storage()
        arquivos_info = []
        for arquivo in arquivos_validos:
            nome = secure_filename(arquivo.filename)
            try:
                # Ler bytes do arquivo
                pdf_bytes = arquivo.read()
                pdf_io = BytesIO(pdf_bytes)
                pdf_io.name = nome

                # Upload para S3 na pasta do batch
                s3_path = storage.save_file(
                    file=pdf_io,
                    folder=f'{COMPROVANTES_BATCH_S3_FOLDER}/{batch_id}',
                    filename=f'{len(arquivos_info):05d}_{nome}',
                    allowed_extensions=['pdf'],
                )

                if s3_path:
                    arquivos_info.append({
                        'nome': nome,
                        's3_path': s3_path,
                    })
                else:
                    logger.warning(f"Falha ao enviar PDF para S3: {nome}")
            except Exception as e:
                logger.warning(f"Erro ao enviar PDF {nome} para S3: {e}")

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
    """Retorna comprovantes em JSON para a tabela, com dados de lançamento."""
    comprovantes = ComprovantePagamentoBoleto.query.order_by(
        desc(ComprovantePagamentoBoleto.importado_em)
    ).all()

    # Buscar lançamentos associados (melhor match por comprovante)
    # Prioridade: LANCADO > CONFIRMADO > PENDENTE
    lancamentos_por_comp = {}
    lancamentos = LancamentoComprovante.query.filter(
        LancamentoComprovante.status.in_(['PENDENTE', 'CONFIRMADO', 'LANCADO'])
    ).all()

    for lanc in lancamentos:
        existente = lancamentos_por_comp.get(lanc.comprovante_id)
        prioridade = {'LANCADO': 3, 'CONFIRMADO': 2, 'PENDENTE': 1}
        prio_lanc = prioridade.get(lanc.status, 0)
        prio_exist = prioridade.get(existente.status, 0) if existente else -1
        if not existente or prio_lanc > prio_exist or (
            prio_lanc == prio_exist and (lanc.match_score or 0) > (existente.match_score or 0)
        ):
            lancamentos_por_comp[lanc.comprovante_id] = lanc

    dados = []
    for c in comprovantes:
        item = c.to_dict()

        # Enriquecer com dados do lançamento
        lanc = lancamentos_por_comp.get(c.id)
        if lanc:
            item['lancamento_id'] = lanc.id
            item['lancamento_status'] = lanc.status
            item['lancamento_odoo_payment_id'] = lanc.odoo_payment_id
            item['lancamento_odoo_payment_name'] = lanc.odoo_payment_name
            item['lancamento_lancado_em'] = (
                lanc.lancado_em.strftime('%d/%m/%Y %H:%M') if lanc.lancado_em else None
            )
            item['lancamento_erro'] = lanc.erro_lancamento
            item['lancamento_odoo_move_id'] = lanc.odoo_move_id
            item['lancamento_match_score'] = lanc.match_score
            # Enrichment: dados adicionais para UI compacta
            item['lancamento_nf_numero'] = lanc.nf_numero
            item['lancamento_parcela'] = lanc.parcela
            item['lancamento_odoo_partner_name'] = lanc.odoo_partner_name
            item['lancamento_odoo_move_name'] = lanc.odoo_move_name
            item['lancamento_diferenca_valor'] = float(lanc.diferenca_valor) if lanc.diferenca_valor else None
            item['lancamento_beneficiario_e_financeira'] = lanc.beneficiario_e_financeira
            item['lancamento_odoo_full_reconcile_id'] = lanc.odoo_full_reconcile_id
            item['lancamento_odoo_full_reconcile_extrato_id'] = lanc.odoo_full_reconcile_extrato_id
            # Campos adicionais para modal de detalhes
            item['lancamento_odoo_move_line_id'] = lanc.odoo_move_line_id
            item['lancamento_odoo_partner_id'] = lanc.odoo_partner_id
            item['lancamento_odoo_partner_cnpj'] = lanc.odoo_partner_cnpj
            item['lancamento_odoo_company_id'] = lanc.odoo_company_id
            item['lancamento_odoo_valor_original'] = float(lanc.odoo_valor_original) if lanc.odoo_valor_original else None
            item['lancamento_odoo_valor_residual'] = float(lanc.odoo_valor_residual) if lanc.odoo_valor_residual else None
            item['lancamento_odoo_valor_recalculado'] = float(lanc.odoo_valor_recalculado) if lanc.odoo_valor_recalculado else None
            item['lancamento_odoo_vencimento'] = lanc.odoo_vencimento.strftime('%d/%m/%Y') if lanc.odoo_vencimento else None
            item['lancamento_match_criterios'] = lanc.match_criterios
            item['lancamento_criado_em'] = lanc.criado_em.strftime('%d/%m/%Y %H:%M') if lanc.criado_em else None
            item['lancamento_confirmado_em'] = lanc.confirmado_em.strftime('%d/%m/%Y %H:%M') if lanc.confirmado_em else None
            item['lancamento_confirmado_por'] = lanc.confirmado_por
            item['lancamento_lancado_por'] = lanc.lancado_por
            item['lancamento_odoo_debit_line_id'] = lanc.odoo_debit_line_id
            item['lancamento_odoo_credit_line_id'] = lanc.odoo_credit_line_id
        else:
            item['lancamento_id'] = None
            item['lancamento_status'] = None
            item['lancamento_odoo_payment_id'] = None
            item['lancamento_odoo_payment_name'] = None
            item['lancamento_lancado_em'] = None
            item['lancamento_erro'] = None
            item['lancamento_odoo_move_id'] = None
            item['lancamento_match_score'] = None
            item['lancamento_nf_numero'] = None
            item['lancamento_parcela'] = None
            item['lancamento_odoo_partner_name'] = None
            item['lancamento_odoo_move_name'] = None
            item['lancamento_diferenca_valor'] = None
            item['lancamento_beneficiario_e_financeira'] = None
            item['lancamento_odoo_full_reconcile_id'] = None
            item['lancamento_odoo_full_reconcile_extrato_id'] = None
            item['lancamento_odoo_move_line_id'] = None
            item['lancamento_odoo_partner_id'] = None
            item['lancamento_odoo_partner_cnpj'] = None
            item['lancamento_odoo_company_id'] = None
            item['lancamento_odoo_valor_original'] = None
            item['lancamento_odoo_valor_residual'] = None
            item['lancamento_odoo_valor_recalculado'] = None
            item['lancamento_odoo_vencimento'] = None
            item['lancamento_match_criterios'] = None
            item['lancamento_criado_em'] = None
            item['lancamento_confirmado_em'] = None
            item['lancamento_confirmado_por'] = None
            item['lancamento_lancado_por'] = None
            item['lancamento_odoo_debit_line_id'] = None
            item['lancamento_odoo_credit_line_id'] = None

        dados.append(item)

    return jsonify({
        'sucesso': True,
        'dados': dados,
        'total': len(dados),
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
