# -*- coding: utf-8 -*-
"""
Rotas para Baixa de Pagamentos (Contas a Pagar)
===============================================

Hub para baixar pagamentos via extrato bancário:
1. Importar linhas de saída do extrato
2. Fazer matching com títulos a pagar
3. Aprovar matches
4. Processar baixas (criar payments outbound no Odoo)

Prefix: /financeiro/contas-pagar/baixas

Autor: Sistema de Fretes
Data: 2025-12-13
"""

import logging
import re
from datetime import datetime
from flask import render_template, request, jsonify, flash, redirect, url_for
from sqlalchemy import func, case

from app import db
from app.financeiro.routes import financeiro_bp
from app.financeiro.models import (
    BaixaPagamentoLote, BaixaPagamentoItem,
    ExtratoLote, ExtratoItem
)
from app.financeiro.services.baixa_pagamentos_service import BaixaPagamentosService

logger = logging.getLogger(__name__)


# =============================================================================
# HUB PRINCIPAL
# =============================================================================

@financeiro_bp.route('/contas-pagar/baixas')
def pagamentos_baixas_hub():
    """
    Hub principal de baixas de pagamentos.
    Lista lotes e permite criar novos.
    """
    # Filtros
    status_filtro = request.args.get('status', '')
    page = request.args.get('page', 1, type=int)
    per_page = 20

    # Query base
    query = BaixaPagamentoLote.query

    if status_filtro:
        query = query.filter(BaixaPagamentoLote.status == status_filtro)

    # Ordenar por data de criação (mais recente primeiro)
    query = query.order_by(BaixaPagamentoLote.criado_em.desc())

    # Paginar
    lotes = query.paginate(page=page, per_page=per_page, error_out=False)

    # Buscar extratos disponíveis para importar
    # Prioriza extratos de saída (tipo_transacao='saida'), mas mostra todos se não houver
    extratos_saida = ExtratoLote.query.filter(
        ExtratoLote.tipo_transacao == 'saida',
        ExtratoLote.status.in_(['IMPORTADO', 'AGUARDANDO_APROVACAO', 'CONCLUIDO'])
    ).order_by(ExtratoLote.criado_em.desc()).limit(20).all()

    if extratos_saida:
        extratos_disponiveis = extratos_saida
    else:
        # Se não houver extratos de saída, mostrar todos para permitir importação manual
        extratos_disponiveis = ExtratoLote.query.filter(
            ExtratoLote.status.in_(['IMPORTADO', 'AGUARDANDO_APROVACAO', 'CONCLUIDO'])
        ).order_by(ExtratoLote.criado_em.desc()).limit(20).all()

    return render_template(
        'financeiro/pagamentos_baixas_hub.html',
        lotes=lotes,
        extratos_disponiveis=extratos_disponiveis,
        status_filtro=status_filtro
    )


# =============================================================================
# IMPORTAR DO EXTRATO
# =============================================================================

@financeiro_bp.route('/contas-pagar/baixas/importar-extrato/<int:extrato_lote_id>', methods=['POST'])
def pagamentos_importar_extrato(extrato_lote_id):
    """
    Importa linhas de saída (amount < 0) de um extrato para criar lote de pagamentos.
    """
    try:
        # Buscar extrato
        extrato_lote = ExtratoLote.query.get_or_404(extrato_lote_id)

        # Verificar se já existe lote para este extrato
        lote_existente = BaixaPagamentoLote.query.filter_by(
            extrato_lote_id=extrato_lote_id
        ).first()

        if lote_existente:
            flash(f'Já existe um lote de pagamentos para este extrato (ID: {lote_existente.id})', 'warning')
            return redirect(url_for('financeiro.pagamentos_baixas_hub'))

        # Buscar linhas de SAÍDA do extrato (não reconciliadas)
        # Para pagamentos, precisamos buscar do ExtratoItem onde o valor seria negativo
        # Mas como ExtratoItem pode não ter linhas de saída, vamos buscar direto do Odoo

        service = BaixaPagamentosService()

        # Buscar statement_id do extrato
        statement_id = extrato_lote.statement_id
        if not statement_id:
            flash('Extrato não tem statement_id vinculado', 'error')
            return redirect(url_for('financeiro.pagamentos_baixas_hub'))

        # Buscar linhas de saída do Odoo
        linhas_saida = service.connection.search_read(
            'account.bank.statement.line',
            [
                ['statement_id', '=', statement_id],
                ['amount', '<', 0],  # SAÍDAS
                ['is_reconciled', '=', False]
            ],
            fields=[
                'id', 'move_id', 'date', 'amount', 'payment_ref',
                'partner_id', 'journal_id', 'company_id'
            ],
            limit=500
        )

        if not linhas_saida:
            flash('Nenhuma linha de saída não conciliada encontrada no extrato', 'warning')
            return redirect(url_for('financeiro.pagamentos_baixas_hub'))

        # Criar lote
        lote = BaixaPagamentoLote(
            extrato_lote_id=extrato_lote_id,
            nome=f"Pagamentos - {extrato_lote.statement_name or extrato_lote.nome}",
            journal_id=extrato_lote.journal_id,
            journal_code=extrato_lote.journal_code,
            journal_name=extrato_lote.statement_name.split()[0] if extrato_lote.statement_name else None,
            data_inicio=extrato_lote.data_extrato,
            data_fim=extrato_lote.data_extrato,
            status='IMPORTADO',
            criado_por='Sistema'
        )
        db.session.add(lote)
        db.session.flush()

        # Criar itens para cada linha de saída
        total_valor = 0
        for linha in linhas_saida:
            # Extrair dados do payment_ref
            dados_ref = service.extrair_dados_payment_ref(linha.get('payment_ref', ''))

            # Buscar linha de débito do extrato
            move_id_extrato = linha['move_id'][0] if linha.get('move_id') else None
            debit_line_id = None
            if move_id_extrato:
                debit_line_id = service.buscar_linha_debito_extrato(move_id_extrato)

            valor_abs = abs(linha['amount'])
            total_valor += valor_abs

            item = BaixaPagamentoItem(
                lote_id=lote.id,
                statement_line_id=linha['id'],
                move_id_extrato=move_id_extrato,
                data_transacao=datetime.strptime(linha['date'], '%Y-%m-%d').date() if isinstance(linha['date'], str) else linha['date'],
                valor=valor_abs,
                payment_ref=linha.get('payment_ref'),
                tipo_transacao=dados_ref.get('tipo_transacao'),
                nome_beneficiario=dados_ref.get('nome_beneficiario'),
                cnpj_beneficiario=dados_ref.get('cnpj_beneficiario'),
                debit_line_id_extrato=debit_line_id,
                status_match='PENDENTE',
                status='PENDENTE'
            )
            db.session.add(item)

        # Atualizar estatísticas do lote
        lote.total_linhas = len(linhas_saida)
        lote.valor_total = total_valor

        db.session.commit()

        flash(f'Lote criado com {len(linhas_saida)} linhas de pagamento. Valor total: R$ {total_valor:,.2f}', 'success')
        return redirect(url_for('financeiro.pagamentos_baixas_lote_detalhe', lote_id=lote.id))

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao importar extrato: {e}")
        flash(f'Erro ao importar extrato: {str(e)}', 'error')
        return redirect(url_for('financeiro.pagamentos_baixas_hub'))


# =============================================================================
# DETALHE DO LOTE
# =============================================================================

@financeiro_bp.route('/contas-pagar/baixas/lote/<int:lote_id>')
def pagamentos_baixas_lote_detalhe(lote_id):
    """
    Visualiza detalhes de um lote de pagamentos.
    """
    lote = BaixaPagamentoLote.query.get_or_404(lote_id)

    # Filtros
    status_match_filtro = request.args.get('status_match', '')
    status_filtro = request.args.get('status', '')
    page = request.args.get('page', 1, type=int)
    per_page = 50

    # Query base
    query = BaixaPagamentoItem.query.filter_by(lote_id=lote_id)

    if status_match_filtro:
        query = query.filter(BaixaPagamentoItem.status_match == status_match_filtro)
    if status_filtro:
        query = query.filter(BaixaPagamentoItem.status == status_filtro)

    # Ordenar
    query = query.order_by(BaixaPagamentoItem.data_transacao.desc(), BaixaPagamentoItem.valor.desc())

    # Paginar
    itens = query.paginate(page=page, per_page=per_page, error_out=False)

    # Estatísticas
    stats = db.session.query(
        func.count().label('total'),
        func.sum(case((BaixaPagamentoItem.status_match == 'MATCH_ENCONTRADO', 1), else_=0)).label('com_match'),
        func.sum(case((BaixaPagamentoItem.status_match == 'MULTIPLOS_MATCHES', 1), else_=0)).label('multiplos'),
        func.sum(case((BaixaPagamentoItem.status_match == 'SEM_MATCH', 1), else_=0)).label('sem_match'),
        func.sum(case((BaixaPagamentoItem.aprovado == True, 1), else_=0)).label('aprovados'),
        func.sum(case((BaixaPagamentoItem.status == 'SUCESSO', 1), else_=0)).label('processados'),
        func.sum(case((BaixaPagamentoItem.status == 'ERRO', 1), else_=0)).label('erros'),
    ).filter(BaixaPagamentoItem.lote_id == lote_id).first()

    return render_template(
        'financeiro/pagamentos_baixas_lote.html',
        lote=lote,
        itens=itens,
        stats=stats,
        status_match_filtro=status_match_filtro,
        status_filtro=status_filtro
    )


# =============================================================================
# MATCHING
# =============================================================================

@financeiro_bp.route('/contas-pagar/baixas/executar-matching/<int:lote_id>', methods=['POST'])
def pagamentos_executar_matching(lote_id):
    """
    Executa matching automático para todos os itens pendentes do lote.
    """
    try:
        lote = BaixaPagamentoLote.query.get_or_404(lote_id)

        # Buscar itens pendentes
        itens = BaixaPagamentoItem.query.filter_by(
            lote_id=lote_id,
            status_match='PENDENTE'
        ).all()

        if not itens:
            return jsonify({'success': False, 'message': 'Nenhum item pendente para matching'})

        service = BaixaPagamentosService()

        matches_encontrados = 0
        sem_match = 0
        multiplos = 0

        for item in itens:
            try:
                # Buscar títulos candidatos pelo CNPJ e valor
                if item.cnpj_beneficiario:
                    candidatos = service.buscar_titulos_por_cnpj_valor(
                        item.cnpj_beneficiario,
                        item.valor,
                        tolerancia=5.0  # R$ 5 de tolerância
                    )

                    if len(candidatos) == 1 and candidatos[0]['score'] >= 90:
                        # Match único com alta confiança
                        titulo = candidatos[0]['titulo']
                        item.status_match = 'MATCH_ENCONTRADO'
                        item.titulo_id = titulo['id']
                        item.titulo_move_id = titulo['move_id'][0] if titulo['move_id'] else None
                        item.titulo_move_name = titulo['move_id'][1] if titulo['move_id'] else None
                        item.titulo_nf = titulo.get('x_studio_nf_e')
                        item.titulo_parcela = titulo.get('l10n_br_cobranca_parcela')
                        item.titulo_valor = titulo.get('credit')
                        item.titulo_vencimento = datetime.strptime(titulo['date_maturity'], '%Y-%m-%d').date() if titulo.get('date_maturity') and isinstance(titulo['date_maturity'], str) else titulo.get('date_maturity')
                        item.partner_id = titulo['partner_id'][0] if titulo['partner_id'] else None
                        item.partner_name = titulo['partner_id'][1] if titulo['partner_id'] else None
                        item.company_id = titulo['company_id'][0] if titulo['company_id'] else None
                        item.match_score = candidatos[0]['score']
                        item.match_criterio = candidatos[0]['criterio']
                        matches_encontrados += 1

                    elif len(candidatos) > 1:
                        # Múltiplos candidatos
                        item.status_match = 'MULTIPLOS_MATCHES'
                        item.set_matches_candidatos([{
                            'titulo_id': c['titulo']['id'],
                            'nf': c['titulo'].get('x_studio_nf_e'),
                            'parcela': c['titulo'].get('l10n_br_cobranca_parcela'),
                            'valor': c['titulo'].get('credit'),
                            'vencimento': str(c['titulo'].get('date_maturity')),
                            'partner_name': c['titulo']['partner_id'][1] if c['titulo'].get('partner_id') else None,
                            'score': c['score'],
                            'criterio': c['criterio']
                        } for c in candidatos[:10]])
                        multiplos += 1

                    else:
                        item.status_match = 'SEM_MATCH'
                        sem_match += 1
                else:
                    item.status_match = 'SEM_MATCH'
                    item.mensagem = 'CNPJ não extraído do payment_ref'
                    sem_match += 1

            except Exception as e:
                logger.error(f"Erro no matching do item {item.id}: {e}")
                item.status_match = 'SEM_MATCH'
                item.mensagem = str(e)[:200]
                sem_match += 1

        # Atualizar estatísticas do lote
        lote.linhas_com_match = matches_encontrados
        lote.linhas_sem_match = sem_match
        lote.status = 'AGUARDANDO_APROVACAO'

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Matching concluído: {matches_encontrados} matches, {multiplos} múltiplos, {sem_match} sem match',
            'stats': {
                'matches': matches_encontrados,
                'multiplos': multiplos,
                'sem_match': sem_match
            }
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro no matching: {e}")
        return jsonify({'success': False, 'message': str(e)})


# =============================================================================
# VINCULAÇÃO MANUAL
# =============================================================================

@financeiro_bp.route('/contas-pagar/baixas/api/vincular-titulo', methods=['POST'])
def pagamentos_vincular_titulo():
    """
    Vincula manualmente um título a um item.
    """
    try:
        data = request.get_json()
        item_id = data.get('item_id')
        titulo_id = data.get('titulo_id')

        item = BaixaPagamentoItem.query.get_or_404(item_id)

        service = BaixaPagamentosService()
        titulo = service.buscar_titulo_por_id(titulo_id)

        if not titulo:
            return jsonify({'success': False, 'message': 'Título não encontrado'})

        # Atualizar item
        item.titulo_id = titulo['id']
        item.titulo_move_id = titulo['move_id'][0] if titulo['move_id'] else None
        item.titulo_move_name = titulo['move_id'][1] if titulo['move_id'] else None
        item.titulo_nf = titulo.get('x_studio_nf_e')
        item.titulo_parcela = titulo.get('l10n_br_cobranca_parcela')
        item.titulo_valor = titulo.get('credit')
        item.titulo_vencimento = datetime.strptime(titulo['date_maturity'], '%Y-%m-%d').date() if titulo.get('date_maturity') and isinstance(titulo['date_maturity'], str) else titulo.get('date_maturity')
        item.partner_id = titulo['partner_id'][0] if titulo['partner_id'] else None
        item.partner_name = titulo['partner_id'][1] if titulo['partner_id'] else None
        item.company_id = titulo['company_id'][0] if titulo['company_id'] else None
        item.status_match = 'MATCH_ENCONTRADO'
        item.match_score = 100
        item.match_criterio = 'MANUAL'

        db.session.commit()

        return jsonify({'success': True, 'message': 'Título vinculado com sucesso'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


@financeiro_bp.route('/contas-pagar/baixas/api/buscar-titulos', methods=['GET'])
def pagamentos_buscar_titulos():
    """
    Busca títulos a pagar por NF ou CNPJ.
    """
    try:
        nf = request.args.get('nf', '')
        cnpj = request.args.get('cnpj', '')
        valor = request.args.get('valor', 0, type=float)

        service = BaixaPagamentosService()

        if nf:
            # Buscar por NF
            titulos = service.connection.search_read(
                'account.move.line',
                [
                    ['x_studio_nf_e', 'ilike', nf],
                    ['account_type', '=', 'liability_payable'],
                    ['parent_state', '=', 'posted'],
                    ['reconciled', '=', False]
                ],
                fields=['id', 'move_id', 'partner_id', 'credit', 'date_maturity',
                        'x_studio_nf_e', 'l10n_br_cobranca_parcela', 'company_id'],
                limit=20
            )

            resultados = [{
                'titulo_id': t['id'],
                'nf': t.get('x_studio_nf_e'),
                'parcela': t.get('l10n_br_cobranca_parcela'),
                'valor': t.get('credit'),
                'vencimento': t.get('date_maturity'),
                'partner_name': t['partner_id'][1] if t.get('partner_id') else None,
                'company': t['company_id'][1] if t.get('company_id') else None
            } for t in titulos]

        elif cnpj and valor:
            # Buscar por CNPJ e valor
            candidatos = service.buscar_titulos_por_cnpj_valor(cnpj, valor, tolerancia=50)
            resultados = [{
                'titulo_id': c['titulo']['id'],
                'nf': c['titulo'].get('x_studio_nf_e'),
                'parcela': c['titulo'].get('l10n_br_cobranca_parcela'),
                'valor': c['titulo'].get('credit'),
                'vencimento': c['titulo'].get('date_maturity'),
                'partner_name': c['titulo']['partner_id'][1] if c['titulo'].get('partner_id') else None,
                'score': c['score'],
                'criterio': c['criterio']
            } for c in candidatos]
        else:
            resultados = []

        return jsonify({'success': True, 'titulos': resultados})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


# =============================================================================
# APROVAÇÃO
# =============================================================================

@financeiro_bp.route('/contas-pagar/baixas/api/aprovar-item', methods=['POST'])
def pagamentos_aprovar_item():
    """
    Aprova um item para processamento.
    """
    try:
        data = request.get_json()
        item_id = data.get('item_id')
        aprovar = data.get('aprovar', True)

        item = BaixaPagamentoItem.query.get_or_404(item_id)

        if aprovar and not item.titulo_id:
            return jsonify({'success': False, 'message': 'Item não tem título vinculado'})

        item.aprovado = aprovar
        item.aprovado_em = datetime.utcnow() if aprovar else None
        item.aprovado_por = 'Usuario' if aprovar else None
        item.status = 'APROVADO' if aprovar else 'PENDENTE'

        db.session.commit()

        return jsonify({'success': True, 'message': 'Item aprovado' if aprovar else 'Aprovação removida'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


@financeiro_bp.route('/contas-pagar/baixas/api/aprovar-todos/<int:lote_id>', methods=['POST'])
def pagamentos_aprovar_todos(lote_id):
    """
    Aprova todos os itens com match encontrado.
    """
    try:
        count = BaixaPagamentoItem.query.filter_by(
            lote_id=lote_id,
            status_match='MATCH_ENCONTRADO',
            aprovado=False
        ).update({
            'aprovado': True,
            'aprovado_em': datetime.utcnow(),
            'aprovado_por': 'Usuario',
            'status': 'APROVADO'
        })

        # Atualizar lote
        lote = db.session.get(BaixaPagamentoLote,lote_id) if lote_id else None
        if lote:
            lote.linhas_aprovadas = BaixaPagamentoItem.query.filter_by(
                lote_id=lote_id,
                aprovado=True
            ).count()

        db.session.commit()

        return jsonify({'success': True, 'message': f'{count} itens aprovados'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


# =============================================================================
# PROCESSAMENTO
# =============================================================================

@financeiro_bp.route('/contas-pagar/baixas/processar/<int:lote_id>', methods=['POST'])
def pagamentos_processar_lote(lote_id):
    """
    Processa todos os itens aprovados do lote.
    """
    try:
        service = BaixaPagamentosService()
        estatisticas = service.processar_lote(lote_id)

        return jsonify({
            'success': True,
            'message': f'Processamento concluído: {estatisticas["sucesso"]} sucesso, {estatisticas["erro"]} erros',
            'estatisticas': estatisticas
        })

    except Exception as e:
        logger.error(f"Erro no processamento: {e}")
        return jsonify({'success': False, 'message': str(e)})


@financeiro_bp.route('/contas-pagar/baixas/api/processar-item/<int:item_id>', methods=['POST'])
def pagamentos_processar_item(item_id):
    """
    Processa um item individual.
    """
    try:
        item = BaixaPagamentoItem.query.get_or_404(item_id)

        if not item.aprovado:
            return jsonify({'success': False, 'message': 'Item não está aprovado'})

        if item.status == 'SUCESSO':
            return jsonify({'success': False, 'message': 'Item já foi processado'})

        service = BaixaPagamentosService()
        service.processar_item(item)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Item processado com sucesso. Payment: {item.payment_name}',
            'payment_name': item.payment_name,
            'saldo_antes': item.saldo_antes,
            'saldo_depois': item.saldo_depois
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao processar item: {e}")
        return jsonify({'success': False, 'message': str(e)})
