# -*- coding: utf-8 -*-
"""
Rotas de Extrato Bancário - Conciliação via Extrato
===================================================

Hub para visualização e conciliação de linhas de extrato com títulos a receber.

Rotas:
- /extrato/ - Hub principal
- /extrato/importar - Importar linhas do Odoo
- /extrato/lotes - Lista de lotes
- /extrato/lote/<id> - Detalhes do lote com itens
- /extrato/executar-matching/<id> - Executar matching em um lote
- /extrato/api/titulos-candidatos/<item_id> - Buscar títulos candidatos para um item

Autor: Sistema de Fretes
Data: 2025-12-11
"""

import logging
from datetime import datetime
from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user

from app import db

logger = logging.getLogger(__name__)
from app.utils.timezone import agora_utc_naive
from app.financeiro.routes import financeiro_bp
from app.financeiro.models import ExtratoLote, ExtratoItem, ContasAReceber, ContasAPagar
from app.financeiro.services.extrato_service import ExtratoService


# =============================================================================
# HUB PRINCIPAL - TELA UNIFICADA
# =============================================================================

@financeiro_bp.route('/extrato/')
@login_required
def extrato_hub():
    """Redirect para extrato_itens (tela antiga removida)."""
    return redirect(url_for('financeiro.extrato_itens', **request.args))


# =============================================================================
# NOVA TELA UNIFICADA DE ITENS (lista corrida, DataTables + AJAX)
# =============================================================================

@financeiro_bp.route('/extrato/itens')
@login_required
def extrato_itens():
    """
    Nova tela unificada de itens de extrato em lista corrida.
    Todos os itens de todos os lotes, com DataTables + filtros avancados.
    Dados carregados via AJAX (GET /extrato/api/itens).
    """
    return render_template('financeiro/extrato_itens.html')


@financeiro_bp.route('/extrato/api/itens')
@login_required
def extrato_api_itens():
    """
    API JSON para DataTables — todos os itens de extrato enriquecidos.

    Retorna itens com dados do lote (journal, statement) e titulo vinculado.
    Otimizado com subquery para evitar N+1 no count de titulos M:N.
    """
    from sqlalchemy import func, case
    from app.financeiro.models import ExtratoItemTitulo

    # Subquery: count de titulos M:N por item
    titulos_sub = db.session.query(
        ExtratoItemTitulo.extrato_item_id,
        func.count(ExtratoItemTitulo.id).label('qtd_titulos'),
        func.sum(ExtratoItemTitulo.valor_alocado).label('valor_alocado_total')
    ).group_by(ExtratoItemTitulo.extrato_item_id).subquery()

    # Query principal com JOIN lote + LEFT JOIN titulos count
    rows = db.session.query(
        ExtratoItem,
        ExtratoLote.journal_code.label('lote_journal'),
        ExtratoLote.statement_name.label('lote_statement'),
        ExtratoLote.tipo_transacao.label('lote_tipo'),
        titulos_sub.c.qtd_titulos,
        titulos_sub.c.valor_alocado_total
    ).join(
        ExtratoLote, ExtratoItem.lote_id == ExtratoLote.id
    ).outerjoin(
        titulos_sub, ExtratoItem.id == titulos_sub.c.extrato_item_id
    ).order_by(
        ExtratoItem.data_transacao.desc(), ExtratoItem.id.desc()
    ).all()

    itens = []
    for item, journal, statement, tipo_lote, qtd_tit, val_aloc in rows:
        qtd = qtd_tit or 0
        has_fk = bool(item.titulo_receber_id or item.titulo_pagar_id)

        itens.append({
            'id': item.id,
            'data_transacao': item.data_transacao.strftime('%d/%m/%Y') if item.data_transacao else '',
            'data_transacao_iso': item.data_transacao.isoformat() if item.data_transacao else '',
            'valor': float(item.valor) if item.valor else 0,
            'tipo_transacao': item.tipo_transacao or '',
            'nome_pagador': item.nome_pagador or '',
            'cnpj_pagador': item.cnpj_pagador or '',
            'payment_ref': (item.payment_ref or '')[:120],
            'status_match': item.status_match or 'PENDENTE',
            'status': item.status or 'PENDENTE',
            'aprovado': item.aprovado,
            'match_score': item.match_score,
            'match_criterio': item.match_criterio or '',
            # Lote/Statement
            'lote_id': item.lote_id,
            'journal_code': journal or item.journal_code or '',
            'statement_name': statement or '',
            'tipo_lote': tipo_lote or 'entrada',
            # Titulo vinculado (cache no item)
            'titulo_nf': item.titulo_nf or '',
            'titulo_parcela': item.titulo_parcela,
            'titulo_valor': float(item.titulo_valor) if item.titulo_valor else None,
            'titulo_cliente': item.titulo_cliente or '',
            'titulo_cnpj': item.titulo_cnpj or '',
            'titulo_vencimento': item.titulo_vencimento.strftime('%d/%m/%Y') if item.titulo_vencimento else '',
            # M:N
            'tem_multiplos_titulos': qtd > 0,
            'qtd_titulos': qtd if qtd > 0 else (1 if has_fk else 0),
            'valor_alocado_total': float(val_aloc) if val_aloc else None,
            # IDs
            'titulo_receber_id': item.titulo_receber_id,
            'titulo_pagar_id': item.titulo_pagar_id,
            'payment_id': item.payment_id,
            'statement_line_id': item.statement_line_id,
        })

    # Stats agregados em single query
    # Excluir conciliados dos counts de match status e aprovados (evita dupla contagem)
    from sqlalchemy import and_
    _nao_conciliado = ExtratoItem.status != 'CONCILIADO'
    stats_q = db.session.query(
        func.count().label('total'),
        func.sum(case((and_(ExtratoItem.status_match == 'MATCH_ENCONTRADO', _nao_conciliado), 1), else_=0)).label('match_unico'),
        func.sum(case((and_(ExtratoItem.status_match == 'MULTIPLOS_VINCULADOS', _nao_conciliado), 1), else_=0)).label('vinculados'),
        func.sum(case((and_(ExtratoItem.status_match == 'MULTIPLOS_MATCHES', _nao_conciliado), 1), else_=0)).label('multiplos'),
        func.sum(case((and_(ExtratoItem.status_match == 'SEM_MATCH', _nao_conciliado), 1), else_=0)).label('sem_match'),
        func.sum(case((and_(ExtratoItem.status_match == 'PENDENTE', _nao_conciliado), 1), else_=0)).label('pendentes'),
        func.sum(case((and_(ExtratoItem.status_match == 'MATCH_CNAB_PENDENTE', _nao_conciliado), 1), else_=0)).label('cnab'),
        func.sum(case((and_(ExtratoItem.aprovado == True, _nao_conciliado), 1), else_=0)).label('aprovados'),
        func.sum(case((ExtratoItem.status == 'CONCILIADO', 1), else_=0)).label('conciliados'),
    ).first()

    stats = {
        'total': stats_q.total or 0,
        'match_unico': (stats_q.match_unico or 0) + (stats_q.vinculados or 0),
        'multiplos': stats_q.multiplos or 0,
        'sem_match': stats_q.sem_match or 0,
        'pendentes': stats_q.pendentes or 0,
        'cnab': stats_q.cnab or 0,
        'aprovados': stats_q.aprovados or 0,
        'conciliados': stats_q.conciliados or 0,
    }

    return jsonify({
        'success': True,
        'itens': itens,
        'stats': stats
    })


@financeiro_bp.route('/extrato/api/aprovar-itens', methods=['POST'])
@login_required
def extrato_aprovar_itens():
    """Aprova multiplos itens por IDs (batch para a tela unificada)."""
    data = request.get_json()
    item_ids = data.get('item_ids', [])

    if not item_ids:
        return jsonify({'success': False, 'error': 'item_ids e obrigatorio'}), 400

    itens = ExtratoItem.query.filter(
        ExtratoItem.id.in_(item_ids),
        ExtratoItem.aprovado == False
    ).all()

    aprovados = 0
    for item in itens:
        # Verificar se tem titulo vinculado (1:1 via FK OU M:N via tabela associativa)
        if item.titulo_receber_id or item.titulo_pagar_id or item.tem_multiplos_titulos:
            item.aprovado = True
            item.aprovado_em = agora_utc_naive()
            item.aprovado_por = current_user.nome if current_user else 'Sistema'
            item.status = 'APROVADO'
            aprovados += 1

    db.session.commit()

    return jsonify({
        'success': True,
        'aprovados': aprovados
    })


@financeiro_bp.route('/extrato/api/conciliar-itens', methods=['POST'])
@login_required
def extrato_conciliar_itens():
    """
    Enfileira conciliacao de multiplos itens aprovados via Redis Queue.

    Retorna job_id imediatamente. Frontend faz polling em
    /extrato/api/conciliar-itens/status/<job_id> para acompanhar progresso.
    """
    from app.portal.workers import enqueue_job, get_redis_connection
    from app.financeiro.workers.extrato_conciliacao_jobs import processar_conciliacao_extrato_job

    data = request.get_json()
    item_ids = data.get('item_ids', [])

    if not item_ids:
        return jsonify({'success': False, 'error': 'item_ids e obrigatorio'}), 400

    # Verificar itens validos
    itens = ExtratoItem.query.filter(
        ExtratoItem.id.in_(item_ids),
        ExtratoItem.aprovado == True,
        ExtratoItem.status != 'CONCILIADO'
    ).all()

    if not itens:
        return jsonify({'success': False, 'error': 'Nenhum item valido para conciliar'}), 400

    item_ids_validos = [i.id for i in itens]

    # Verificar lock (itens ja em processamento por outro job)
    try:
        redis_conn = get_redis_connection()
        bloqueados = []
        for iid in item_ids_validos:
            if redis_conn.exists(f'extrato_conciliacao_lock:{iid}'):
                bloqueados.append(iid)
        if bloqueados:
            return jsonify({
                'success': False,
                'error': f'{len(bloqueados)} item(ns) ja esta(o) sendo processado(s)',
                'itens_bloqueados': bloqueados
            }), 409
    except Exception:
        pass  # Se Redis falhar na verificacao, lock sera checado no job

    usuario_nome = current_user.nome if current_user else 'Sistema'

    job = enqueue_job(
        processar_conciliacao_extrato_job,
        item_ids_validos,
        usuario_nome,
        queue_name='default',
        timeout='30m'
    )

    return jsonify({
        'success': True,
        'job_id': job.id,
        'total_itens': len(item_ids_validos),
        'message': f'{len(item_ids_validos)} item(ns) enfileirado(s) para conciliacao'
    })


@financeiro_bp.route('/extrato/api/conciliar-itens/status/<job_id>')
@login_required
def extrato_conciliar_status(job_id):
    """
    Retorna status e progresso de um job de conciliacao.
    Usado pelo frontend para polling a cada 2s.
    """
    from app.financeiro.workers.extrato_conciliacao_jobs import get_job_status, obter_progresso

    status = get_job_status(job_id)
    progresso = obter_progresso(job_id)
    if progresso:
        status['progresso'] = progresso

    return jsonify({'success': True, **status})


@financeiro_bp.route('/extrato/api/executar-matching-itens', methods=['POST'])
@login_required
def extrato_executar_matching_itens():
    """
    Executa matching para itens pendentes da tela unificada.

    Aceita:
      - item_ids: lista de IDs especificos (selecionados pelo usuario)
      - todos_pendentes: true → roda em TODOS os lotes com itens PENDENTE

    Agrupa itens por lote e chama o service correto (recebimentos ou pagamentos).
    """
    data = request.get_json()
    item_ids = data.get('item_ids', [])
    todos_pendentes = data.get('todos_pendentes', False)

    try:
        from app.financeiro.services.extrato_matching_service import ExtratoMatchingService
        from app.financeiro.services.pagamento_matching_service import PagamentoMatchingService

        if todos_pendentes:
            # Descobrir lotes que tem itens PENDENTE
            lotes_pendentes = db.session.query(
                ExtratoItem.lote_id
            ).filter(
                ExtratoItem.status_match == 'PENDENTE'
            ).distinct().all()
            lote_ids = [r[0] for r in lotes_pendentes]
        elif item_ids:
            # Itens especificos — descobrir seus lotes
            lote_ids = [r[0] for r in db.session.query(
                ExtratoItem.lote_id
            ).filter(
                ExtratoItem.id.in_(item_ids),
                ExtratoItem.status_match == 'PENDENTE'
            ).distinct().all()]
        else:
            return jsonify({'success': False, 'error': 'Informe item_ids ou todos_pendentes=true'}), 400

        if not lote_ids:
            return jsonify({'success': True, 'processados': 0, 'mensagem': 'Nenhum item pendente encontrado'})

        total_stats = {'processados': 0, 'com_match': 0, 'multiplos': 0, 'sem_match': 0}
        erros_lotes = []

        for lote_id in lote_ids:
            lote = db.session.get(ExtratoLote, lote_id)
            if not lote:
                continue

            try:
                if lote.tipo_transacao == 'saida':
                    service = PagamentoMatchingService()
                else:
                    service = ExtratoMatchingService()

                resultado = service.executar_matching_lote(lote_id)

                # Atualizar lote
                lote.status = 'AGUARDANDO_APROVACAO'
                lote.linhas_com_match = resultado.get('com_match', 0)
                lote.linhas_sem_match = resultado.get('sem_match', 0)
                db.session.commit()

                # Acumular stats
                for k in total_stats:
                    total_stats[k] += resultado.get(k, 0)

            except Exception as e:
                erros_lotes.append({'lote_id': lote_id, 'erro': str(e)})

        return jsonify({
            'success': True,
            'lotes_processados': len(lote_ids),
            'resultado': total_stats,
            'erros': erros_lotes if erros_lotes else None
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@financeiro_bp.route('/extrato/api/statements')
@login_required
def extrato_api_statements():
    """
    API para buscar statements do Odoo de forma assíncrona.
    Evita travar a página principal.

    Parâmetros:
    - journal: Filtrar por código do journal
    - tipo: 'entrada' (recebimentos), 'saida' (pagamentos), 'ambos' (default)
    """
    journal_filter = request.args.get('journal')
    tipo_transacao = request.args.get('tipo', 'ambos')

    try:
        service = ExtratoService()

        # Buscar statements para recebimentos
        statements_entrada = []
        if tipo_transacao in ['entrada', 'ambos']:
            statements_entrada = service.listar_statements_disponiveis(
                journal_code=journal_filter,
                tipo_transacao='entrada'
            )
            for st in statements_entrada:
                st['tipo'] = 'entrada'

        # Buscar statements para pagamentos
        statements_saida = []
        if tipo_transacao in ['saida', 'ambos']:
            statements_saida = service.listar_statements_disponiveis(
                journal_code=journal_filter,
                tipo_transacao='saida'
            )
            for st in statements_saida:
                st['tipo'] = 'saida'

        # Combinar e ordenar por data
        statements = statements_entrada + statements_saida

        journals = service.listar_journals_disponiveis(tipo_transacao=tipo_transacao)

        return jsonify({
            'success': True,
            'statements': statements,
            'statements_entrada': statements_entrada,
            'statements_saida': statements_saida,
            'journals': journals
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'statements': [],
            'statements_entrada': [],
            'statements_saida': [],
            'journals': []
        })


# =============================================================================
# IMPORTAÇÃO
# =============================================================================

@financeiro_bp.route('/extrato/importar-statement/<int:statement_id>', methods=['POST'])
@login_required
def extrato_importar_statement(statement_id):
    """
    Importa um statement específico do Odoo.

    Parâmetros:
    - tipo: 'entrada' (recebimentos) ou 'saida' (pagamentos) - via form ou query
    """
    tipo_transacao = request.form.get('tipo') or request.args.get('tipo', 'entrada')

    try:
        service = ExtratoService()
        lote = service.importar_statement(
            statement_id=statement_id,
            criado_por=current_user.nome if current_user else 'Sistema',
            tipo_transacao=tipo_transacao
        )

        # Pipeline de resolução de favorecido/pagador
        msg_resolver = ''
        if lote.total_linhas > 0:
            try:
                if tipo_transacao == 'saida':
                    from app.financeiro.services.favorecido_resolver_service import FavorecidoResolverService
                    resolver = FavorecidoResolverService(connection=service._connection)
                    stats = resolver.resolver_lote(lote.id)
                    msg_resolver = f' Favorecidos resolvidos: {stats["resolvidos"]}/{stats["total"]}.'
                elif tipo_transacao == 'entrada':
                    from app.financeiro.services.recebimento_resolver_service import RecebimentoResolverService
                    resolver = RecebimentoResolverService(connection=service._connection)
                    stats = resolver.resolver_lote(lote.id)
                    msg_resolver = f' Pagadores resolvidos: {stats["resolvidos"]}/{stats["total"]}.'
            except Exception as e_resolver:
                logger.warning(f"Erro ao resolver favorecidos/pagadores do lote {lote.id}: {e_resolver}")
                msg_resolver = ' (Erro na resolução de favorecidos/pagadores)'

        tipo_label = 'recebimentos' if tipo_transacao == 'entrada' else 'pagamentos'
        flash(
            f'Importação concluída: {lote.total_linhas} linhas de "{lote.statement_name}" ({tipo_label}). '
            f'CNPJs identificados: {service.estatisticas["com_cnpj"]}.{msg_resolver}',
            'success'
        )

        return redirect(url_for('financeiro.extrato_lote_detalhe', lote_id=lote.id))

    except Exception as e:
        flash(f'Erro na importação: {e}', 'error')
        return redirect(url_for('financeiro.extrato_itens'))


@financeiro_bp.route('/extrato/importar', methods=['POST'])
@login_required
def extrato_importar():
    """Importa linhas de extrato não conciliadas do Odoo (legado - por journal)."""
    journal_code = request.form.get('journal_code')
    limit = request.form.get('limit', 100, type=int)

    if not journal_code:
        flash('Selecione um journal', 'error')
        return redirect(url_for('financeiro.extrato_itens'))

    try:
        service = ExtratoService()
        lote = service.importar_extrato(
            journal_code=journal_code,
            limit=limit,
            criado_por=current_user.nome if current_user else 'Sistema'
        )

        flash(
            f'Importação concluída: {lote.total_linhas} linhas do {journal_code}. '
            f'CNPJs identificados: {service.estatisticas["com_cnpj"]}',
            'success'
        )

        return redirect(url_for('financeiro.extrato_lote_detalhe', lote_id=lote.id))

    except Exception as e:
        flash(f'Erro na importação: {e}', 'error')
        return redirect(url_for('financeiro.extrato_itens'))


@financeiro_bp.route('/extrato/importar-multiplos', methods=['POST'])
@login_required
def extrato_importar_multiplos():
    """
    Importa múltiplos statements de uma vez.

    Parâmetros JSON:
    - statement_ids: Lista de IDs dos statements
    - tipo: 'entrada' (recebimentos) ou 'saida' (pagamentos)
    """
    data = request.get_json()
    statement_ids = data.get('statement_ids', [])
    tipo_transacao = data.get('tipo', 'entrada')

    if not statement_ids:
        return jsonify({'success': False, 'error': 'Nenhum statement selecionado'}), 400

    try:
        service = ExtratoService()
        importados = 0
        total_linhas = 0
        erros = []

        for statement_id in statement_ids:
            try:
                # Resetar estatísticas para cada statement
                service.estatisticas = {
                    'importados': 0,
                    'com_cnpj': 0,
                    'sem_cnpj': 0,
                    'erros': 0
                }

                lote = service.importar_statement(
                    statement_id=int(statement_id),
                    criado_por=current_user.nome if current_user else 'Sistema',
                    tipo_transacao=tipo_transacao
                )
                importados += 1
                total_linhas += lote.total_linhas
            except ValueError as e:
                # Statement já importado - ignorar
                erros.append(str(e))
            except Exception as e:
                erros.append(f"Statement {statement_id}: {str(e)}")

        return jsonify({
            'success': True,
            'importados': importados,
            'total_linhas': total_linhas,
            'erros': erros if erros else None
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# =============================================================================
# LOTES
# =============================================================================

@financeiro_bp.route('/extrato/lote/<int:lote_id>')
@login_required
def extrato_lote_detalhe(lote_id):
    """Detalhes de um lote com seus itens."""
    lote = ExtratoLote.query.get_or_404(lote_id)

    # Parâmetros de paginação
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)  # Limite padrão: 20

    # Filtros para itens
    status_match = request.args.get('status_match')
    status = request.args.get('status')
    filtro_cnpj = request.args.get('cnpj', '').strip()
    filtro_data_inicio = request.args.get('data_inicio')
    filtro_data_fim = request.args.get('data_fim')

    query = ExtratoItem.query.filter_by(lote_id=lote_id)

    if status_match:
        query = query.filter(ExtratoItem.status_match == status_match)
    if status:
        query = query.filter(ExtratoItem.status == status)

    # Filtro por CNPJ (busca parcial - funciona com ou sem formatação)
    if filtro_cnpj:
        # Buscar tanto o valor original quanto apenas dígitos
        from sqlalchemy import or_, func
        cnpj_limpo = ''.join(c for c in filtro_cnpj if c.isdigit())
        query = query.filter(
            or_(
                # Busca direta (se usuário digitou formatado)
                ExtratoItem.cnpj_pagador.ilike(f'%{filtro_cnpj}%'),
                # Busca por dígitos (remove formatação do campo via regexp)
                func.regexp_replace(ExtratoItem.cnpj_pagador, r'\D', '', 'g').ilike(f'%{cnpj_limpo}%')
            )
        )

    # Filtro por data
    if filtro_data_inicio:
        try:
            data_inicio = datetime.strptime(filtro_data_inicio, '%Y-%m-%d').date()
            query = query.filter(ExtratoItem.data_transacao >= data_inicio)
        except ValueError:
            pass

    if filtro_data_fim:
        try:
            data_fim = datetime.strptime(filtro_data_fim, '%Y-%m-%d').date()
            query = query.filter(ExtratoItem.data_transacao <= data_fim)
        except ValueError:
            pass

    # Ordenar e paginar
    query = query.order_by(ExtratoItem.data_transacao.desc(), ExtratoItem.id)

    # Se per_page = 0, retorna todos (sem paginação)
    if per_page == 0:
        itens = query.all()
        pagination = None
    else:
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        itens = pagination.items

    # OTIMIZAÇÃO: Estatísticas em uma única query com GROUP BY
    # Excluir conciliados dos counts de match status e aprovados (evita dupla contagem)
    from sqlalchemy import func, case, or_, and_
    _nao_conciliado = ExtratoItem.status != 'CONCILIADO'
    stats_query = db.session.query(
        func.count().label('total'),
        func.sum(case((and_(ExtratoItem.status_match == 'MATCH_ENCONTRADO', _nao_conciliado), 1), else_=0)).label('com_match'),
        func.sum(case((and_(ExtratoItem.status_match == 'MULTIPLOS_MATCHES', _nao_conciliado), 1), else_=0)).label('multiplos'),
        func.sum(case((and_(ExtratoItem.status_match == 'MULTIPLOS_VINCULADOS', _nao_conciliado), 1), else_=0)).label('vinculados'),
        func.sum(case((and_(ExtratoItem.status_match == 'SEM_MATCH', _nao_conciliado), 1), else_=0)).label('sem_match'),
        func.sum(case((and_(ExtratoItem.status_match == 'PENDENTE', _nao_conciliado), 1), else_=0)).label('pendentes'),
        func.sum(case((and_(ExtratoItem.status_match == 'MATCH_CNAB_PENDENTE', _nao_conciliado), 1), else_=0)).label('via_cnab'),
        func.sum(case((and_(ExtratoItem.aprovado == True, _nao_conciliado), 1), else_=0)).label('aprovados'),
        func.sum(case((ExtratoItem.status == 'CONCILIADO', 1), else_=0)).label('conciliados'),
    ).filter(ExtratoItem.lote_id == lote_id).first()

    # com_match inclui MATCH_ENCONTRADO e MULTIPLOS_VINCULADOS (ambos prontos para aprovar)
    com_match_total = (stats_query.com_match or 0) + (stats_query.vinculados or 0) if stats_query else 0

    stats = {
        'total': lote.total_linhas or (stats_query.total if stats_query else 0),
        'com_match': com_match_total,
        'multiplos': stats_query.multiplos or 0 if stats_query else 0,
        'vinculados': stats_query.vinculados or 0 if stats_query else 0,
        'sem_match': stats_query.sem_match or 0 if stats_query else 0,
        'pendentes': stats_query.pendentes or 0 if stats_query else 0,
        'via_cnab': stats_query.via_cnab or 0 if stats_query else 0,
        'aprovados': stats_query.aprovados or 0 if stats_query else 0,
        'conciliados': stats_query.conciliados or 0 if stats_query else 0,
    }

    return render_template(
        'financeiro/extrato_lote_detalhe.html',
        lote=lote,
        itens=itens,
        stats=stats,
        pagination=pagination,
        per_page=per_page,
        filtro_cnpj=filtro_cnpj,
        filtro_data_inicio=filtro_data_inicio,
        filtro_data_fim=filtro_data_fim
    )


@financeiro_bp.route('/extrato/lotes-detalhe')
@login_required
def extrato_lotes_detalhe():
    """Visualiza itens de múltiplos lotes juntos."""
    # Pegar IDs dos lotes da query string (formato: ?lotes=1,2,3)
    lotes_param = request.args.get('lotes', '')
    if not lotes_param:
        flash('Nenhum lote selecionado', 'warning')
        return redirect(url_for('financeiro.extrato_itens'))

    try:
        lote_ids = [int(x.strip()) for x in lotes_param.split(',') if x.strip()]
    except ValueError:
        flash('IDs de lotes inválidos', 'error')
        return redirect(url_for('financeiro.extrato_itens'))

    if not lote_ids:
        flash('Nenhum lote selecionado', 'warning')
        return redirect(url_for('financeiro.extrato_itens'))

    # Buscar lotes
    lotes = ExtratoLote.query.filter(ExtratoLote.id.in_(lote_ids)).all()
    if not lotes:
        flash('Lotes não encontrados', 'error')
        return redirect(url_for('financeiro.extrato_itens'))

    # Parâmetros de paginação e filtros
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    status_match = request.args.get('status_match')
    filtro_cnpj = request.args.get('cnpj', '').strip()
    filtro_data_inicio = request.args.get('data_inicio')
    filtro_data_fim = request.args.get('data_fim')

    # Query de itens de todos os lotes selecionados
    query = ExtratoItem.query.filter(ExtratoItem.lote_id.in_(lote_ids))

    if status_match:
        query = query.filter(ExtratoItem.status_match == status_match)

    # Filtro por CNPJ
    if filtro_cnpj:
        from sqlalchemy import or_, func
        cnpj_limpo = ''.join(c for c in filtro_cnpj if c.isdigit())
        query = query.filter(
            or_(
                ExtratoItem.cnpj_pagador.ilike(f'%{filtro_cnpj}%'),
                func.regexp_replace(ExtratoItem.cnpj_pagador, r'\D', '', 'g').ilike(f'%{cnpj_limpo}%')
            )
        )

    # Filtro por data
    if filtro_data_inicio:
        try:
            data_inicio = datetime.strptime(filtro_data_inicio, '%Y-%m-%d').date()
            query = query.filter(ExtratoItem.data_transacao >= data_inicio)
        except ValueError:
            pass

    if filtro_data_fim:
        try:
            data_fim = datetime.strptime(filtro_data_fim, '%Y-%m-%d').date()
            query = query.filter(ExtratoItem.data_transacao <= data_fim)
        except ValueError:
            pass

    # Ordenar e paginar
    query = query.order_by(ExtratoItem.data_transacao.desc(), ExtratoItem.id)

    if per_page == 0:
        itens = query.all()
        pagination = None
    else:
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        itens = pagination.items

    # OTIMIZAÇÃO: Estatísticas agregadas em uma única query
    # Excluir conciliados dos counts de match status e aprovados (evita dupla contagem)
    from sqlalchemy import func, case, and_
    _nao_conciliado = ExtratoItem.status != 'CONCILIADO'
    stats_query = db.session.query(
        func.count().label('total'),
        func.sum(case((and_(ExtratoItem.status_match == 'MATCH_ENCONTRADO', _nao_conciliado), 1), else_=0)).label('com_match'),
        func.sum(case((and_(ExtratoItem.status_match == 'MULTIPLOS_MATCHES', _nao_conciliado), 1), else_=0)).label('multiplos'),
        func.sum(case((and_(ExtratoItem.status_match == 'SEM_MATCH', _nao_conciliado), 1), else_=0)).label('sem_match'),
        func.sum(case((and_(ExtratoItem.status_match == 'PENDENTE', _nao_conciliado), 1), else_=0)).label('pendentes'),
        func.sum(case((and_(ExtratoItem.aprovado == True, _nao_conciliado), 1), else_=0)).label('aprovados'),
        func.sum(case((ExtratoItem.status == 'CONCILIADO', 1), else_=0)).label('conciliados'),
    ).filter(ExtratoItem.lote_id.in_(lote_ids)).first()

    stats = {
        'total': sum(lote.total_linhas or 0 for lote in lotes),
        'com_match': stats_query.com_match or 0 if stats_query else 0,
        'multiplos': stats_query.multiplos or 0 if stats_query else 0,
        'sem_match': stats_query.sem_match or 0 if stats_query else 0,
        'pendentes': stats_query.pendentes or 0 if stats_query else 0,
        'aprovados': stats_query.aprovados or 0 if stats_query else 0,
        'conciliados': stats_query.conciliados or 0 if stats_query else 0,
    }

    return render_template(
        'financeiro/extrato_lotes_detalhe.html',
        lotes=lotes,
        lotes_param=lotes_param,
        itens=itens,
        stats=stats,
        pagination=pagination,
        per_page=per_page,
        filtro_cnpj=filtro_cnpj,
        filtro_data_inicio=filtro_data_inicio,
        filtro_data_fim=filtro_data_fim
    )


# =============================================================================
# LOTE DE PAGAMENTOS (SAÍDA)
# =============================================================================

@financeiro_bp.route('/extrato/pagamentos/lote/<int:lote_id>')
@login_required
def extrato_lote_pagamentos_detalhe(lote_id):
    """
    Detalhes de um lote de PAGAMENTOS (tipo_transacao='saida').
    Similar ao extrato_lote_detalhe mas para pagamentos, usando ContasAPagar.
    """
    lote = ExtratoLote.query.get_or_404(lote_id)

    # Verificar se é lote de pagamentos
    if lote.tipo_transacao != 'saida':
        flash('Este lote não é de pagamentos', 'warning')
        return redirect(url_for('financeiro.extrato_lote_detalhe', lote_id=lote_id))

    # Parâmetros de paginação
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    # Filtros para itens
    status_match = request.args.get('status_match')
    status = request.args.get('status')
    filtro_cnpj = request.args.get('cnpj', '').strip()
    filtro_data_inicio = request.args.get('data_inicio')
    filtro_data_fim = request.args.get('data_fim')

    query = ExtratoItem.query.filter_by(lote_id=lote_id)

    if status_match:
        query = query.filter(ExtratoItem.status_match == status_match)
    if status:
        query = query.filter(ExtratoItem.status == status)

    # Filtro por CNPJ (busca parcial)
    if filtro_cnpj:
        from sqlalchemy import or_, func
        cnpj_limpo = ''.join(c for c in filtro_cnpj if c.isdigit())
        query = query.filter(
            or_(
                ExtratoItem.cnpj_pagador.ilike(f'%{filtro_cnpj}%'),
                func.regexp_replace(ExtratoItem.cnpj_pagador, r'\D', '', 'g').ilike(f'%{cnpj_limpo}%')
            )
        )

    # Filtro por data
    if filtro_data_inicio:
        try:
            data_inicio = datetime.strptime(filtro_data_inicio, '%Y-%m-%d').date()
            query = query.filter(ExtratoItem.data_transacao >= data_inicio)
        except ValueError:
            pass

    if filtro_data_fim:
        try:
            data_fim = datetime.strptime(filtro_data_fim, '%Y-%m-%d').date()
            query = query.filter(ExtratoItem.data_transacao <= data_fim)
        except ValueError:
            pass

    # Ordenar e paginar
    query = query.order_by(ExtratoItem.data_transacao.desc(), ExtratoItem.id)

    if per_page == 0:
        itens = query.all()
        pagination = None
    else:
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        itens = pagination.items

    # Estatísticas
    # Excluir conciliados dos counts de match status e aprovados (evita dupla contagem)
    from sqlalchemy import func, case, or_, and_
    _nao_conciliado = ExtratoItem.status != 'CONCILIADO'
    stats_query = db.session.query(
        func.count().label('total'),
        func.sum(case((and_(ExtratoItem.status_match == 'MATCH_ENCONTRADO', _nao_conciliado), 1), else_=0)).label('com_match'),
        func.sum(case((and_(ExtratoItem.status_match == 'MULTIPLOS_MATCHES', _nao_conciliado), 1), else_=0)).label('multiplos'),
        func.sum(case((and_(ExtratoItem.status_match == 'MULTIPLOS_VINCULADOS', _nao_conciliado), 1), else_=0)).label('vinculados'),
        func.sum(case((and_(ExtratoItem.status_match == 'SEM_MATCH', _nao_conciliado), 1), else_=0)).label('sem_match'),
        func.sum(case((and_(ExtratoItem.status_match == 'PENDENTE', _nao_conciliado), 1), else_=0)).label('pendentes'),
        func.sum(case((and_(ExtratoItem.aprovado == True, _nao_conciliado), 1), else_=0)).label('aprovados'),
        func.sum(case((ExtratoItem.status == 'CONCILIADO', 1), else_=0)).label('conciliados'),
    ).filter(ExtratoItem.lote_id == lote_id).first()

    # com_match inclui MATCH_ENCONTRADO e MULTIPLOS_VINCULADOS (ambos prontos para aprovar)
    com_match_total = (stats_query.com_match or 0) + (stats_query.vinculados or 0) if stats_query else 0

    stats = {
        'total': lote.total_linhas or (stats_query.total if stats_query else 0),
        'com_match': com_match_total,
        'multiplos': stats_query.multiplos or 0 if stats_query else 0,
        'vinculados': stats_query.vinculados or 0 if stats_query else 0,
        'sem_match': stats_query.sem_match or 0 if stats_query else 0,
        'pendentes': stats_query.pendentes or 0 if stats_query else 0,
        'aprovados': stats_query.aprovados or 0 if stats_query else 0,
        'conciliados': stats_query.conciliados or 0 if stats_query else 0,
    }

    # Cross-reference: buscar comprovantes vinculados por statement_line_id
    from app.financeiro.models_comprovante import ComprovantePagamentoBoleto
    statement_line_ids_itens = [i.statement_line_id for i in itens if i.statement_line_id]
    comprovantes_por_stl = {}
    if statement_line_ids_itens:
        comps = ComprovantePagamentoBoleto.query.filter(
            ComprovantePagamentoBoleto.odoo_statement_line_id.in_(statement_line_ids_itens)
        ).all()
        for c in comps:
            comprovantes_por_stl[c.odoo_statement_line_id] = c

    return render_template(
        'financeiro/extrato_lote_pagamentos_detalhe.html',
        lote=lote,
        itens=itens,
        stats=stats,
        pagination=pagination,
        per_page=per_page,
        comprovantes_por_stl=comprovantes_por_stl,
        filtro_cnpj=filtro_cnpj,
        filtro_data_inicio=filtro_data_inicio,
        filtro_data_fim=filtro_data_fim
    )


@financeiro_bp.route('/extrato/pagamentos/executar-matching/<int:lote_id>', methods=['POST'])
@login_required
def extrato_pagamentos_executar_matching(lote_id):
    """Executa o matching de títulos a PAGAR para um lote de pagamentos."""
    lote = ExtratoLote.query.get_or_404(lote_id)

    if lote.tipo_transacao != 'saida':
        return jsonify({
            'success': False,
            'error': 'Este lote não é de pagamentos'
        }), 400

    try:
        from app.financeiro.services.pagamento_matching_service import PagamentoMatchingService

        service = PagamentoMatchingService()
        resultado = service.executar_matching_lote(lote_id)

        lote.status = 'AGUARDANDO_APROVACAO'
        lote.linhas_com_match = resultado['com_match']
        lote.linhas_sem_match = resultado['sem_match']
        db.session.commit()

        return jsonify({
            'success': True,
            'resultado': resultado
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@financeiro_bp.route('/extrato/pagamentos/api/titulos-candidatos/<int:item_id>')
@login_required
def extrato_pagamentos_titulos_candidatos(item_id):
    """
    Busca títulos A PAGAR candidatos para um item de extrato.
    """
    item = ExtratoItem.query.get_or_404(item_id)

    try:
        from app.financeiro.services.pagamento_matching_service import PagamentoMatchingService

        service = PagamentoMatchingService()
        # Valor do pagamento é negativo no extrato
        valor = abs(item.valor) if item.valor else 0

        candidatos = service.buscar_titulos_candidatos(
            cnpj=item.cnpj_pagador,
            valor=valor,
            data_pagamento=item.data_transacao
        )

        return jsonify({
            'success': True,
            'item': item.to_dict(),
            'candidatos': candidatos
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@financeiro_bp.route('/extrato/pagamentos/api/selecionar-titulo', methods=['POST'])
@login_required
def extrato_pagamentos_selecionar_titulo():
    """Seleciona manualmente um título A PAGAR para um item de extrato."""
    data = request.get_json()
    item_id = data.get('item_id')
    titulo_id = data.get('titulo_id')

    if not item_id or not titulo_id:
        return jsonify({'success': False, 'error': 'item_id e titulo_id são obrigatórios'}), 400

    item = ExtratoItem.query.get_or_404(item_id)

    try:
        from app.financeiro.services.pagamento_matching_service import PagamentoMatchingService

        service = PagamentoMatchingService()
        service.vincular_titulo_manual(item, titulo_id)

        return jsonify({
            'success': True,
            'message': f'Título {titulo_id} vinculado ao item {item_id}'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# =============================================================================
# MATCHING
# =============================================================================

@financeiro_bp.route('/extrato/executar-matching/<int:lote_id>', methods=['POST'])
@login_required
def extrato_executar_matching(lote_id):
    """Executa o matching de títulos para um lote."""
    lote = ExtratoLote.query.get_or_404(lote_id)

    try:
        from app.financeiro.services.extrato_matching_service import ExtratoMatchingService

        service = ExtratoMatchingService()
        resultado = service.executar_matching_lote(lote_id)

        lote.status = 'AGUARDANDO_APROVACAO'
        lote.linhas_com_match = resultado['com_match']
        lote.linhas_sem_match = resultado['sem_match']
        db.session.commit()

        return jsonify({
            'success': True,
            'resultado': resultado
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@financeiro_bp.route('/extrato/api/titulos-candidatos/<int:item_id>')
@login_required
def extrato_titulos_candidatos(item_id):
    """
    Busca títulos candidatos para um item de extrato.
    Retorna todos os matches possíveis para análise manual.
    """
    item = ExtratoItem.query.get_or_404(item_id)

    try:
        from app.financeiro.services.extrato_matching_service import ExtratoMatchingService

        service = ExtratoMatchingService()
        candidatos = service.buscar_titulos_candidatos(
            cnpj=item.cnpj_pagador,
            valor=item.valor,
            data_pagamento=item.data_transacao
        )

        return jsonify({
            'success': True,
            'item': item.to_dict(),
            'candidatos': candidatos
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@financeiro_bp.route('/extrato/api/selecionar-titulo', methods=['POST'])
@login_required
def extrato_selecionar_titulo():
    """Seleciona manualmente um título para um item de extrato."""
    data = request.get_json()
    item_id = data.get('item_id')
    titulo_id = data.get('titulo_id')

    if not item_id or not titulo_id:
        return jsonify({'success': False, 'error': 'item_id e titulo_id são obrigatórios'}), 400

    item = ExtratoItem.query.get_or_404(item_id)

    try:
        from app.financeiro.services.extrato_matching_service import ExtratoMatchingService

        service = ExtratoMatchingService()
        service.vincular_titulo_manual(item, titulo_id)

        return jsonify({
            'success': True,
            'message': f'Título {titulo_id} vinculado ao item {item_id}'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@financeiro_bp.route('/extrato/api/desvincular-titulo', methods=['POST'])
@login_required
def extrato_desvincular_titulo():
    """Desvincula um título de um item de extrato."""
    data = request.get_json()
    item_id = data.get('item_id')

    if not item_id:
        return jsonify({'success': False, 'error': 'item_id é obrigatório'}), 400

    item = ExtratoItem.query.get_or_404(item_id)

    # Não permitir desvincular se já foi conciliado
    if item.status == 'CONCILIADO':
        return jsonify({
            'success': False,
            'error': 'Item já foi conciliado, não é possível desvincular'
        }), 400

    # Limpar dados do título
    titulo_antigo = item.titulo_nf
    item.titulo_receber_id = None  # FK para clientes (recebimentos)
    item.titulo_pagar_id = None    # FK para fornecedores (pagamentos)
    item.titulo_nf = None
    item.titulo_parcela = None
    item.titulo_valor = None
    item.titulo_vencimento = None
    item.titulo_cliente = None
    item.titulo_cnpj = None
    item.match_score = None
    item.match_criterio = None
    item.status_match = 'PENDENTE'
    item.aprovado = False
    item.aprovado_em = None
    item.aprovado_por = None
    item.status = 'PENDENTE'

    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'Título {titulo_antigo} desvinculado do item {item_id}'
    })


@financeiro_bp.route('/extrato/api/desconciliar-item', methods=['POST'])
@login_required
def extrato_desconciliar_item():
    """
    Reverte um item CONCILIADO localmente para APROVADO.

    Permitido APENAS para itens sem payment_id (marcação local).
    Se o item tem payment_id, significa que um pagamento foi criado no Odoo
    e a reversão não pode ser feita automaticamente.
    """
    data = request.get_json()
    item_id = data.get('item_id')

    if not item_id:
        return jsonify({'success': False, 'error': 'item_id é obrigatório'}), 400

    item = ExtratoItem.query.get_or_404(item_id)

    if item.status != 'CONCILIADO':
        return jsonify({
            'success': False,
            'error': f'Item não está CONCILIADO (status atual: {item.status})'
        }), 400

    if item.payment_id:
        return jsonify({
            'success': False,
            'error': (
                f'Item tem payment no Odoo (ID {item.payment_id}). '
                'Não é possível reverter automaticamente — '
                'reverta o pagamento no Odoo antes.'
            )
        }), 400

    # Resetar campos de conciliação
    item.status = 'APROVADO'
    item.processado_em = None
    item.mensagem = None
    item.partial_reconcile_id = None
    item.full_reconcile_id = None
    item.snapshot_antes = None
    item.snapshot_depois = None
    item.titulo_saldo_antes = None
    item.titulo_saldo_depois = None

    # Manter: titulo_pagar_id, titulo_nf, titulo_parcela (vínculo), aprovado=True

    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'Item {item_id} revertido para APROVADO',
        'item': item.to_dict()
    })


@financeiro_bp.route('/extrato/api/aprovar-item', methods=['POST'])
@login_required
def extrato_aprovar_item():
    """Aprova um item para conciliação."""
    data = request.get_json()
    item_id = data.get('item_id')
    aprovar = data.get('aprovar', True)

    item = ExtratoItem.query.get_or_404(item_id)

    # Verificar se tem título vinculado (1:1 via FK OU M:N via tabela associativa)
    if aprovar and not item.titulo_receber_id and not item.titulo_pagar_id and not item.tem_multiplos_titulos:
        return jsonify({
            'success': False,
            'error': 'Item não possui título vinculado'
        }), 400

    item.aprovado = aprovar
    item.aprovado_em = agora_utc_naive() if aprovar else None
    item.aprovado_por = current_user.nome if current_user and aprovar else None
    item.status = 'APROVADO' if aprovar else item.status_match

    db.session.commit()

    return jsonify({
        'success': True,
        'item': item.to_dict()
    })


@financeiro_bp.route('/extrato/api/aprovar-todos', methods=['POST'])
@login_required
def extrato_aprovar_todos():
    """Aprova todos os itens com match único de um lote."""
    data = request.get_json()
    lote_id = data.get('lote_id')

    if not lote_id:
        return jsonify({'success': False, 'error': 'lote_id é obrigatório'}), 400

    # Buscar itens com match único não aprovados
    itens = ExtratoItem.query.filter_by(
        lote_id=lote_id,
        status_match='MATCH_ENCONTRADO',
        aprovado=False
    ).all()

    aprovados = 0
    for item in itens:
        if item.titulo_receber_id or item.titulo_pagar_id:  # FK 1:1 (receber ou pagar)
            item.aprovado = True
            item.aprovado_em = agora_utc_naive()
            item.aprovado_por = current_user.nome if current_user else 'Sistema'
            item.status = 'APROVADO'
            aprovados += 1

    db.session.commit()

    return jsonify({
        'success': True,
        'aprovados': aprovados
    })


# =============================================================================
# VINCULAÇÃO MÚLTIPLA (M:N)
# =============================================================================

@financeiro_bp.route('/extrato/api/vincular-multiplos', methods=['POST'])
@login_required
def extrato_vincular_multiplos():
    """
    Vincula múltiplos títulos a uma linha de extrato.

    Body:
    {
        "item_id": 123,
        "titulos": [
            {"titulo_id": 1, "valor_alocado": 5000.00},
            {"titulo_id": 2, "valor_alocado": 7000.00},
            {"titulo_id": 3, "valor_alocado": 3000.00}
        ],
        "tipo": "receber"  # ou "pagar"
    }
    """
    data = request.get_json()
    item_id = data.get('item_id')
    titulos = data.get('titulos', [])
    tipo = data.get('tipo', 'receber')  # 'receber' ou 'pagar'

    if not item_id:
        return jsonify({'success': False, 'error': 'item_id é obrigatório'}), 400

    if not titulos:
        return jsonify({'success': False, 'error': 'Lista de títulos é obrigatória'}), 400

    item = ExtratoItem.query.get_or_404(item_id)

    # Não permitir vincular se já foi conciliado
    if item.status == 'CONCILIADO':
        return jsonify({
            'success': False,
            'error': 'Item já foi conciliado, não é possível vincular novos títulos'
        }), 400

    try:
        from app.financeiro.services.extrato_matching_service import ExtratoMatchingService

        service = ExtratoMatchingService()
        service.vincular_multiplos_titulos(
            item=item,
            titulos=titulos,
            tipo=tipo,
            usuario=current_user.nome if current_user else 'Sistema'
        )

        return jsonify({
            'success': True,
            'message': f'{len(titulos)} títulos vinculados ao item {item_id}',
            'item': item.to_dict()
        })

    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@financeiro_bp.route('/extrato/api/desvincular-multiplos', methods=['POST'])
@login_required
def extrato_desvincular_multiplos():
    """
    Remove todos os títulos vinculados (M:N) de um item de extrato.

    Body:
    {
        "item_id": 123
    }
    """
    data = request.get_json()
    item_id = data.get('item_id')

    if not item_id:
        return jsonify({'success': False, 'error': 'item_id é obrigatório'}), 400

    item = ExtratoItem.query.get_or_404(item_id)

    # Não permitir desvincular se já foi conciliado
    if item.status == 'CONCILIADO':
        return jsonify({
            'success': False,
            'error': 'Item já foi conciliado, não é possível desvincular'
        }), 400

    try:
        from app.financeiro.services.extrato_matching_service import ExtratoMatchingService

        service = ExtratoMatchingService()
        removidos = service.desvincular_titulos(item)

        return jsonify({
            'success': True,
            'message': f'{removidos} títulos desvinculados do item {item_id}',
            'item': item.to_dict()
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@financeiro_bp.route('/extrato/api/titulos-agrupados/<int:item_id>')
@login_required
def extrato_titulos_agrupados(item_id):
    """
    Busca sugestões de agrupamento de títulos para um item de extrato.

    Retorna combinações de títulos cujas somas aproximam ou igualam o valor do extrato.

    Query params:
    - tipo: 'receber' ou 'pagar' (default: inferido do lote)
    - tolerancia: tolerância percentual para match (default: 0.05 = 5%)
    """
    item = ExtratoItem.query.get_or_404(item_id)

    # Inferir tipo do lote
    lote = item.lote
    if lote and lote.tipo_transacao == 'saida':
        tipo_default = 'pagar'
    else:
        tipo_default = 'receber'

    tipo = request.args.get('tipo', tipo_default)
    tolerancia = request.args.get('tolerancia', 0.05, type=float)

    try:
        from app.financeiro.services.extrato_matching_service import ExtratoMatchingService

        service = ExtratoMatchingService()
        valor = abs(item.valor) if item.valor else 0

        sugestoes = service.buscar_titulos_agrupados(
            cnpj=item.cnpj_pagador,
            valor_total=valor,
            tolerancia=tolerancia,
            tipo=tipo
        )

        return jsonify({
            'success': True,
            'item': item.to_dict(),
            'valor_extrato': float(valor),
            'sugestoes': sugestoes,
            'total_sugestoes': len(sugestoes)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@financeiro_bp.route('/extrato/api/titulos-vinculados/<int:item_id>')
@login_required
def extrato_titulos_vinculados(item_id):
    """
    Lista os títulos vinculados a um item de extrato (via M:N).
    """
    from app.financeiro.models import ExtratoItemTitulo

    item = ExtratoItem.query.get_or_404(item_id)

    # Buscar vínculos M:N
    vinculos = ExtratoItemTitulo.query.filter_by(extrato_item_id=item_id).all()

    titulos = []
    for v in vinculos:
        titulos.append({
            'vinculo_id': v.id,
            'titulo_id': v.titulo_receber_id or v.titulo_pagar_id,
            'tipo': 'receber' if v.titulo_receber_id else 'pagar',
            'valor_alocado': float(v.valor_alocado) if v.valor_alocado else 0,
            'valor_titulo_original': float(v.valor_titulo_original) if v.valor_titulo_original else None,
            'percentual_alocado': float(v.percentual_alocado) if v.percentual_alocado else None,
            'titulo_nf': v.titulo_nf,
            'titulo_parcela': v.titulo_parcela,
            'titulo_vencimento': v.titulo_vencimento.isoformat() if v.titulo_vencimento else None,
            'titulo_cliente': v.titulo_cliente,
            'titulo_cnpj': v.titulo_cnpj,
            'status': v.status,
            'aprovado': v.aprovado,
            'match_score': v.match_score,
            'match_criterio': v.match_criterio
        })

    # Calcular totais
    valor_total_alocado = sum(t['valor_alocado'] for t in titulos)
    valor_extrato = abs(item.valor) if item.valor else 0
    diferenca = valor_extrato - valor_total_alocado

    return jsonify({
        'success': True,
        'item_id': item_id,
        'valor_extrato': float(valor_extrato),
        'valor_total_alocado': float(valor_total_alocado),
        'diferenca': float(diferenca),
        'tem_multiplos_titulos': len(titulos) > 1,
        'titulos': titulos,
        'total_titulos': len(titulos)
    })


# =============================================================================
# CONCILIAÇÃO
# =============================================================================

@financeiro_bp.route('/extrato/api/conciliar-item', methods=['POST'])
@login_required
def extrato_conciliar_item():
    """Executa a conciliação de um item aprovado no Odoo."""
    data = request.get_json()
    item_id = data.get('item_id')

    item = ExtratoItem.query.get_or_404(item_id)

    if not item.aprovado:
        return jsonify({
            'success': False,
            'error': 'Item não está aprovado'
        }), 400

    # Verificar se tem título vinculado (1:1 via FK OU M:N via tabela associativa)
    if not item.titulo_receber_id and not item.titulo_pagar_id and not item.tem_multiplos_titulos:
        return jsonify({
            'success': False,
            'error': 'Item não possui título vinculado'
        }), 400

    try:
        from app.financeiro.services.extrato_conciliacao_service import ExtratoConciliacaoService

        service = ExtratoConciliacaoService()
        resultado = service.conciliar_item(item)
        db.session.commit()

        return jsonify({
            'success': True,
            'resultado': resultado,
            'sincronizado_do_odoo': resultado.get('sincronizado_do_odoo', False)
        })

    except Exception as e:
        item.status = 'ERRO'
        item.mensagem = str(e)
        db.session.commit()

        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@financeiro_bp.route('/extrato/api/conciliar-lote', methods=['POST'])
@login_required
def extrato_conciliar_lote():
    """Executa a conciliação de todos os itens aprovados de um lote."""
    data = request.get_json()
    lote_id = data.get('lote_id')

    if not lote_id:
        return jsonify({'success': False, 'error': 'lote_id é obrigatório'}), 400

    lote = ExtratoLote.query.get_or_404(lote_id)

    try:
        from app.financeiro.services.extrato_conciliacao_service import ExtratoConciliacaoService

        lote.status = 'CONCILIANDO'
        db.session.commit()

        service = ExtratoConciliacaoService()
        resultado = service.conciliar_lote(lote_id)

        lote.status = 'CONCLUIDO'
        lote.linhas_conciliadas = resultado['conciliados']
        lote.linhas_erro = resultado['erros']
        lote.processado_em = agora_utc_naive()
        lote.processado_por = current_user.nome if current_user else 'Sistema'
        db.session.commit()

        return jsonify({
            'success': True,
            'resultado': resultado
        })

    except Exception as e:
        lote.status = 'ERRO'
        db.session.commit()

        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@financeiro_bp.route('/extrato/api/aprovar-todos-multiplos', methods=['POST'])
@login_required
def extrato_aprovar_todos_multiplos():
    """Aprova todos os itens com match único de múltiplos lotes."""
    data = request.get_json()
    lote_ids = data.get('lote_ids', [])

    if not lote_ids:
        return jsonify({'success': False, 'error': 'lote_ids é obrigatório'}), 400

    # Buscar itens com match único não aprovados de todos os lotes
    itens = ExtratoItem.query.filter(
        ExtratoItem.lote_id.in_(lote_ids),
        ExtratoItem.status_match == 'MATCH_ENCONTRADO',
        ExtratoItem.aprovado == False
    ).all()

    aprovados = 0
    for item in itens:
        if item.titulo_receber_id or item.titulo_pagar_id:  # FK 1:1 (receber ou pagar)
            item.aprovado = True
            item.aprovado_em = agora_utc_naive()
            item.aprovado_por = current_user.nome if current_user else 'Sistema'
            item.status = 'APROVADO'
            aprovados += 1

    db.session.commit()

    return jsonify({
        'success': True,
        'aprovados': aprovados
    })


@financeiro_bp.route('/extrato/api/conciliar-multiplos', methods=['POST'])
@login_required
def extrato_conciliar_multiplos():
    """Executa a conciliação de todos os itens aprovados de múltiplos lotes."""
    data = request.get_json()
    lote_ids = data.get('lote_ids', [])

    if not lote_ids:
        return jsonify({'success': False, 'error': 'lote_ids é obrigatório'}), 400

    try:
        from app.financeiro.services.extrato_conciliacao_service import ExtratoConciliacaoService

        service = ExtratoConciliacaoService()
        total_conciliados = 0
        total_erros = 0

        for lote_id in lote_ids:
            lote = db.session.get(ExtratoLote,lote_id) if lote_id else None
            if not lote:
                continue

            lote.status = 'CONCILIANDO'
            db.session.commit()

            resultado = service.conciliar_lote(lote_id)
            total_conciliados += resultado.get('conciliados', 0)
            total_erros += resultado.get('erros', 0)

            lote.linhas_conciliadas = (lote.linhas_conciliadas or 0) + resultado['conciliados']
            lote.linhas_erro = (lote.linhas_erro or 0) + resultado['erros']
            lote.processado_em = agora_utc_naive()
            lote.processado_por = current_user.nome if current_user else 'Sistema'

            # Só marca como concluído se todos os aprovados foram conciliados
            aprovados_restantes = ExtratoItem.query.filter_by(
                lote_id=lote_id,
                aprovado=True
            ).filter(ExtratoItem.status != 'CONCILIADO').count()

            if aprovados_restantes == 0:
                lote.status = 'CONCLUIDO'
            else:
                lote.status = 'AGUARDANDO_APROVACAO'

            db.session.commit()

        return jsonify({
            'success': True,
            'conciliados': total_conciliados,
            'erros': total_erros
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# =============================================================================
# EXCLUIR LOTE
# =============================================================================

@financeiro_bp.route('/extrato/excluir-lote/<int:lote_id>', methods=['POST'])
@login_required
def extrato_excluir_lote(lote_id):
    """Exclui um lote e seus itens."""
    lote = ExtratoLote.query.get_or_404(lote_id)

    # Não permitir excluir lotes com itens conciliados
    conciliados = ExtratoItem.query.filter_by(
        lote_id=lote_id,
        status='CONCILIADO'
    ).count()

    if conciliados > 0:
        flash(f'Não é possível excluir lote com {conciliados} itens já conciliados', 'error')
        return redirect(url_for('financeiro.extrato_lote_detalhe', lote_id=lote_id))

    nome = lote.nome
    db.session.delete(lote)
    db.session.commit()

    flash(f'Lote "{nome}" excluído com sucesso', 'success')
    return redirect(url_for('financeiro.extrato_itens'))
