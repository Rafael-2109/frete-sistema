# -*- coding: utf-8 -*-
"""
Rotas de Matching: Comprovante <-> Fatura Odoo
==============================================

Endpoints para executar, consultar e confirmar/rejeitar matches
entre comprovantes de pagamento e faturas de fornecedor no Odoo.

O matching batch e executado via RQ (Redis Queue) em background,
com progresso em tempo real via polling Redis.

Rotas:
- /comprovantes/api/match/executar           -> Matching batch (via RQ)
- /comprovantes/api/match/progresso/<id>     -> Polling de progresso
- /comprovantes/api/match/<id>/candidatos    -> Candidatos individuais
- /comprovantes/api/match/<id>/confirmar     -> Confirmar match
- /comprovantes/api/match/<id>/rejeitar      -> Rejeitar match
- /comprovantes/api/match/resultados         -> Listagem de lancamentos
- /comprovantes/api/match/<id>/vincular-manual -> Vinculacao manual
"""

import logging
import uuid

from flask import request, jsonify
from flask_login import login_required, current_user

from app.financeiro.routes import financeiro_bp
from app.financeiro.models_comprovante import LancamentoComprovante

logger = logging.getLogger(__name__)


# =============================================================================
# MATCHING BATCH (via RQ)
# =============================================================================

@financeiro_bp.route('/comprovantes/api/match/executar', methods=['POST'])
@login_required
def comprovante_match_executar():
    """
    Enfileira matching batch via RQ para processamento em background.

    Retorna batch_id imediatamente para polling de progresso.

    Body JSON (opcional):
    {
        "comprovante_ids": [1, 2, 3],
        "data_inicio": "2026-01-01",
        "data_fim": "2026-01-31"
    }
    """
    try:
        from app.portal.workers import enqueue_job
        from app.financeiro.workers.comprovante_match_jobs import processar_match_comprovantes_job

        dados = request.get_json(silent=True) or {}
        comprovante_ids = dados.get('comprovante_ids')

        # Filtros de data (passados como string para o job)
        filtros = {}
        if dados.get('data_inicio'):
            filtros['data_inicio'] = dados['data_inicio']
        if dados.get('data_fim'):
            filtros['data_fim'] = dados['data_fim']

        batch_id = str(uuid.uuid4())
        usuario = current_user.nome if hasattr(current_user, 'nome') else str(current_user)

        job = enqueue_job(
            processar_match_comprovantes_job,
            batch_id,
            comprovante_ids,
            filtros if filtros else None,
            usuario,
            queue_name='default',
            timeout='60m',
        )

        logger.info(
            f"Match batch enfileirado: batch_id={batch_id}, job_id={job.id}, "
            f"ids={comprovante_ids or 'todos'}, usuario={usuario}"
        )

        return jsonify({
            'sucesso': True,
            'batch_id': batch_id,
            'job_id': job.id,
            'mensagem': 'Matching iniciado em background. Acompanhe o progresso abaixo.',
        })

    except Exception as e:
        logger.error(f"Erro ao enfileirar match batch: {e}", exc_info=True)
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


# =============================================================================
# PROGRESSO DO BATCH
# =============================================================================

@financeiro_bp.route('/comprovantes/api/match/progresso/<batch_id>')
@login_required
def comprovante_match_progresso(batch_id):
    """
    Retorna progresso do matching batch.

    O frontend faz polling a cada 2s ate o status ser 'concluido' ou 'erro'.
    """
    try:
        from app.financeiro.workers.comprovante_match_jobs import obter_progresso_match

        progresso = obter_progresso_match(batch_id)
        if progresso:
            return jsonify(progresso)
        else:
            return jsonify({'status': 'nao_encontrado', 'batch_id': batch_id})

    except Exception as e:
        logger.error(f"Erro ao obter progresso match: {e}", exc_info=True)
        return jsonify({'status': 'erro', 'erro': str(e)}), 500


# =============================================================================
# CANDIDATOS INDIVIDUAIS
# =============================================================================

@financeiro_bp.route('/comprovantes/api/match/<int:comprovante_id>/candidatos')
@login_required
def comprovante_match_candidatos(comprovante_id):
    """
    Retorna candidatos de match para um comprovante especifico.
    Nao persiste - apenas consulta ao Odoo.
    """
    try:
        from app.financeiro.services.comprovante_match_service import ComprovanteMatchService

        service = ComprovanteMatchService()
        resultado = service.buscar_candidatos_comprovante(comprovante_id)

        return jsonify(resultado)

    except Exception as e:
        logger.error(f"Erro buscar candidatos comp={comprovante_id}: {e}", exc_info=True)
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


# =============================================================================
# CONFIRMAR MATCH
# =============================================================================

@financeiro_bp.route('/comprovantes/api/match/<int:lancamento_id>/confirmar', methods=['POST'])
@login_required
def comprovante_match_confirmar(lancamento_id):
    """Confirma um match (PENDENTE -> CONFIRMADO)."""
    try:
        from app.financeiro.services.comprovante_match_service import ComprovanteMatchService

        usuario = current_user.nome if hasattr(current_user, 'nome') else str(current_user)

        service = ComprovanteMatchService()
        resultado = service.confirmar_match(lancamento_id, usuario)

        if resultado.get('sucesso'):
            return jsonify(resultado)
        else:
            return jsonify(resultado), 400

    except Exception as e:
        logger.error(f"Erro confirmar match {lancamento_id}: {e}", exc_info=True)
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


# =============================================================================
# CONFIRMAR MATCH EM BATCH
# =============================================================================

@financeiro_bp.route('/comprovantes/api/match/confirmar-batch', methods=['POST'])
@login_required
def comprovante_match_confirmar_batch():
    """
    Confirma multiplos matches de uma vez (PENDENTE -> CONFIRMADO).

    Body JSON:
    {
        "lancamento_ids": [1, 2, 3]
    }
    """
    try:
        from app.financeiro.services.comprovante_match_service import ComprovanteMatchService

        dados = request.get_json(silent=True) or {}
        lancamento_ids = dados.get('lancamento_ids', [])

        if not lancamento_ids:
            return jsonify({
                'sucesso': False,
                'erro': 'Nenhum lancamento_id informado',
            }), 400

        usuario = current_user.nome if hasattr(current_user, 'nome') else str(current_user)

        service = ComprovanteMatchService()
        confirmados = 0
        erros = []

        for lid in lancamento_ids:
            resultado = service.confirmar_match(lid, usuario)
            if resultado.get('sucesso'):
                confirmados += 1
            else:
                erros.append({
                    'lancamento_id': lid,
                    'erro': resultado.get('erro', 'Erro desconhecido'),
                })

        logger.info(
            f"Confirmar batch: {confirmados}/{len(lancamento_ids)} confirmados, "
            f"{len(erros)} erros, usuario={usuario}"
        )

        return jsonify({
            'sucesso': True,
            'total_solicitados': len(lancamento_ids),
            'confirmados': confirmados,
            'erros': erros,
        })

    except Exception as e:
        logger.error(f"Erro confirmar batch: {e}", exc_info=True)
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


# =============================================================================
# REJEITAR MATCH
# =============================================================================

@financeiro_bp.route('/comprovantes/api/match/<int:lancamento_id>/rejeitar', methods=['POST'])
@login_required
def comprovante_match_rejeitar(lancamento_id):
    """Rejeita um match (PENDENTE -> REJEITADO)."""
    try:
        from app.financeiro.services.comprovante_match_service import ComprovanteMatchService

        dados = request.get_json(silent=True) or {}
        motivo = dados.get('motivo', '')
        usuario = current_user.nome if hasattr(current_user, 'nome') else str(current_user)

        service = ComprovanteMatchService()
        resultado = service.rejeitar_match(lancamento_id, usuario, motivo)

        if resultado.get('sucesso'):
            return jsonify(resultado)
        else:
            return jsonify(resultado), 400

    except Exception as e:
        logger.error(f"Erro rejeitar match {lancamento_id}: {e}", exc_info=True)
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


# =============================================================================
# LISTAGEM DE RESULTADOS
# =============================================================================

@financeiro_bp.route('/comprovantes/api/match/resultados')
@login_required
def comprovante_match_resultados():
    """
    Lista lancamentos de match (para DataTable).

    Query params:
    - status: PENDENTE, CONFIRMADO, REJEITADO (opcional)
    - comprovante_id: filtrar por comprovante (opcional)
    """
    try:
        query = LancamentoComprovante.query

        status = request.args.get('status')
        if status:
            query = query.filter(LancamentoComprovante.status == status.upper())

        comprovante_id = request.args.get('comprovante_id', type=int)
        if comprovante_id:
            query = query.filter(LancamentoComprovante.comprovante_id == comprovante_id)

        lancamentos = query.order_by(
            LancamentoComprovante.match_score.desc(),
            LancamentoComprovante.criado_em.desc(),
        ).limit(500).all()

        # Enriquecer com dados do comprovante
        resultado = []
        for lanc in lancamentos:
            data = lanc.to_dict()
            comp = lanc.comprovante
            if comp:
                data['comprovante_numero_documento'] = comp.numero_documento
                data['comprovante_beneficiario'] = comp.beneficiario_razao_social
                data['comprovante_beneficiario_cnpj'] = comp.beneficiario_cnpj_cpf
                data['comprovante_valor_documento'] = float(comp.valor_documento) if comp.valor_documento else None
                data['comprovante_valor_pago'] = float(comp.valor_pago) if comp.valor_pago else None
                data['comprovante_data_pagamento'] = comp.data_pagamento.strftime('%d/%m/%Y') if comp.data_pagamento else None
                data['comprovante_data_vencimento'] = comp.data_vencimento.strftime('%d/%m/%Y') if comp.data_vencimento else None
            resultado.append(data)

        return jsonify({
            'sucesso': True,
            'total': len(resultado),
            'lancamentos': resultado,
        })

    except Exception as e:
        logger.error(f"Erro listagem match: {e}", exc_info=True)
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


# =============================================================================
# VINCULACAO MANUAL
# =============================================================================

@financeiro_bp.route('/comprovantes/api/match/<int:comprovante_id>/vincular-manual', methods=['POST'])
@login_required
def comprovante_match_vincular_manual(comprovante_id):
    """
    Vinculacao manual: usuario informa NF + parcela + company_id.

    Body JSON:
    {
        "nf": "12345",
        "parcela": 1,
        "company_id": 1
    }
    """
    try:
        from app.financeiro.services.comprovante_match_service import ComprovanteMatchService

        dados = request.get_json(silent=True) or {}
        nf = dados.get('nf')
        parcela = dados.get('parcela')
        company_id = dados.get('company_id')

        if not nf or parcela is None or not company_id:
            return jsonify({
                'sucesso': False,
                'erro': 'Campos obrigatorios: nf, parcela, company_id',
            }), 400

        usuario = current_user.nome if hasattr(current_user, 'nome') else str(current_user)

        service = ComprovanteMatchService()
        resultado = service.vincular_manual(
            comprovante_id=comprovante_id,
            nf=str(nf),
            parcela=int(parcela),
            company_id=int(company_id),
            usuario=usuario,
        )

        if resultado.get('sucesso'):
            return jsonify(resultado)
        else:
            return jsonify(resultado), 400

    except Exception as e:
        logger.error(f"Erro vincular manual comp={comprovante_id}: {e}", exc_info=True)
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


# =============================================================================
# LANÇAMENTO NO ODOO (INDIVIDUAL - SÍNCRONO)
# =============================================================================

@financeiro_bp.route('/comprovantes/api/match/<int:lancamento_id>/lancar', methods=['POST'])
@login_required
def comprovante_lancamento_individual(lancamento_id):
    """
    Lança um comprovante confirmado no Odoo (CONFIRMADO → LANCADO).

    Cria account.payment outbound, posta, reconcilia com título e extrato.
    """
    try:
        from app.financeiro.services.comprovante_lancamento_service import (
            ComprovanteLancamentoService,
        )

        usuario = current_user.nome if hasattr(current_user, 'nome') else str(current_user)

        service = ComprovanteLancamentoService()
        resultado = service.lancar_no_odoo(lancamento_id, usuario)

        if resultado.get('sucesso'):
            return jsonify(resultado)
        else:
            return jsonify(resultado), 400

    except Exception as e:
        logger.error(f"Erro lançamento individual {lancamento_id}: {e}", exc_info=True)
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


# =============================================================================
# LANÇAMENTO BATCH (ASSÍNCRONO VIA RQ)
# =============================================================================

@financeiro_bp.route('/comprovantes/api/lancamento/executar', methods=['POST'])
@login_required
def comprovante_lancamento_batch():
    """
    Enfileira lançamento batch via RQ para processamento em background.

    Body JSON (opcional):
    {
        "lancamento_ids": [1, 2, 3]   // IDs específicos ou omitir para todos CONFIRMADOS
    }
    """
    try:
        from app.portal.workers import enqueue_job
        from app.financeiro.workers.comprovante_lancamento_jobs import (
            processar_lancamento_comprovantes_job,
        )

        dados = request.get_json(silent=True) or {}
        lancamento_ids = dados.get('lancamento_ids')

        batch_id = str(uuid.uuid4())
        usuario = current_user.nome if hasattr(current_user, 'nome') else str(current_user)

        job = enqueue_job(
            processar_lancamento_comprovantes_job,
            batch_id,
            lancamento_ids,
            usuario,
            queue_name='default',
            timeout='60m',
        )

        logger.info(
            f"Lancamento batch enfileirado: batch_id={batch_id}, job_id={job.id}, "
            f"ids={lancamento_ids or 'todos confirmados'}, usuario={usuario}"
        )

        return jsonify({
            'sucesso': True,
            'batch_id': batch_id,
            'job_id': job.id,
            'mensagem': 'Lançamento iniciado em background. Acompanhe o progresso abaixo.',
        })

    except Exception as e:
        logger.error(f"Erro ao enfileirar lancamento batch: {e}", exc_info=True)
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


# =============================================================================
# PROGRESSO DO LANÇAMENTO BATCH
# =============================================================================

@financeiro_bp.route('/comprovantes/api/lancamento/progresso/<batch_id>')
@login_required
def comprovante_lancamento_progresso(batch_id):
    """
    Retorna progresso do lançamento batch.

    O frontend faz polling a cada 2s até o status ser 'concluido' ou 'erro'.
    """
    try:
        from app.financeiro.workers.comprovante_lancamento_jobs import (
            obter_progresso_lancamento,
        )

        progresso = obter_progresso_lancamento(batch_id)
        if progresso:
            return jsonify(progresso)
        else:
            return jsonify({'status': 'nao_encontrado', 'batch_id': batch_id})

    except Exception as e:
        logger.error(f"Erro ao obter progresso lancamento: {e}", exc_info=True)
        return jsonify({'status': 'erro', 'erro': str(e)}), 500
