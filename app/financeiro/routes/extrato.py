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

from datetime import datetime, date
from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user

from app import db
from app.financeiro.routes import financeiro_bp
from app.financeiro.models import ExtratoLote, ExtratoItem, ContasAReceber, ContasAPagar
from app.financeiro.services.extrato_service import ExtratoService


# =============================================================================
# HUB PRINCIPAL - TELA UNIFICADA
# =============================================================================

@financeiro_bp.route('/extrato/')
@login_required
def extrato_hub():
    """
    Tela unificada de extratos bancários.

    Combina:
    - Extratos importados (com datas De/Até calculadas)
    - Extratos pendentes de importação (do Odoo)
    - Estatísticas de Recebimentos E Pagamentos
    - Filtros inteligentes
    """
    from sqlalchemy import func, case

    # === PARÂMETROS DE FILTRO ===
    filtro_data_de = request.args.get('data_de')
    filtro_data_ate = request.args.get('data_ate')
    filtro_status = request.args.get('status')
    filtro_journal = request.args.get('journal')
    filtro_tipo = request.args.get('tipo')  # 'entrada', 'saida' ou vazio para todos
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    # === QUERY DE LOTES COM DATAS CALCULADAS ===
    # Subquery para calcular MIN/MAX das datas das linhas de cada lote
    datas_subquery = db.session.query(
        ExtratoItem.lote_id,
        func.min(ExtratoItem.data_transacao).label('data_de'),
        func.max(ExtratoItem.data_transacao).label('data_ate'),
        func.count(ExtratoItem.id).label('total_itens')
    ).group_by(ExtratoItem.lote_id).subquery()

    # Query principal com JOIN
    query = db.session.query(
        ExtratoLote,
        datas_subquery.c.data_de,
        datas_subquery.c.data_ate,
        datas_subquery.c.total_itens
    ).outerjoin(
        datas_subquery, ExtratoLote.id == datas_subquery.c.lote_id
    )

    # === FILTRAR POR TIPO DE TRANSAÇÃO (se especificado) ===
    if filtro_tipo:
        query = query.filter(ExtratoLote.tipo_transacao == filtro_tipo)

    # === APLICAR FILTROS ===
    if filtro_status:
        query = query.filter(ExtratoLote.status == filtro_status)

    if filtro_journal:
        query = query.filter(ExtratoLote.journal_code == filtro_journal)

    if filtro_data_de:
        try:
            data_de = datetime.strptime(filtro_data_de, '%Y-%m-%d').date()
            query = query.filter(datas_subquery.c.data_de >= data_de)
        except ValueError:
            pass

    if filtro_data_ate:
        try:
            data_ate = datetime.strptime(filtro_data_ate, '%Y-%m-%d').date()
            query = query.filter(datas_subquery.c.data_ate <= data_ate)
        except ValueError:
            pass

    # Ordenar por data mais recente
    query = query.order_by(ExtratoLote.criado_em.desc())

    # Buscar TODOS os lotes para agrupar corretamente
    # A paginação será aplicada após o agrupamento por statement
    lotes_raw = query.all()

    # Transformar resultado em lista de dicts e AGRUPAR por statement_id
    # Isso permite mostrar recebimentos e pagamentos do mesmo statement na mesma linha
    lotes_por_statement = {}
    lotes_sem_statement = []  # Lotes antigos sem statement_id

    for lote, data_de, data_ate, total_itens in lotes_raw:
        item = {
            'lote': lote,
            'data_de': data_de,
            'data_ate': data_ate,
            'total_itens': total_itens or lote.total_linhas
        }

        if lote.statement_id:
            key = lote.statement_id
            if key not in lotes_por_statement:
                lotes_por_statement[key] = {
                    'statement_id': lote.statement_id,
                    'statement_name': lote.statement_name or lote.nome,
                    'journal_code': lote.journal_code,
                    'data_extrato': lote.data_extrato,
                    'entrada': None,
                    'saida': None,
                    'data_de': data_de,
                    'data_ate': data_ate,
                }

            # Atualizar datas (pegar a menor data_de e maior data_ate)
            if data_de and (not lotes_por_statement[key]['data_de'] or data_de < lotes_por_statement[key]['data_de']):
                lotes_por_statement[key]['data_de'] = data_de
            if data_ate and (not lotes_por_statement[key]['data_ate'] or data_ate > lotes_por_statement[key]['data_ate']):
                lotes_por_statement[key]['data_ate'] = data_ate

            # Associar ao tipo correto
            if lote.tipo_transacao == 'entrada':
                lotes_por_statement[key]['entrada'] = item
            elif lote.tipo_transacao == 'saida':
                lotes_por_statement[key]['saida'] = item
        else:
            # Lotes sem statement_id (legado) - mostrar individualmente
            lotes_sem_statement.append(item)

    # Converter para lista ordenada por data
    lotes_agrupados = list(lotes_por_statement.values())
    lotes_agrupados.sort(key=lambda x: x.get('data_extrato') or x.get('data_de') or date.min, reverse=True)

    # Adicionar lotes sem statement ao final
    todos_lotes = lotes_agrupados + [{'entrada': item, 'saida': None, 'statement_id': None, **item} for item in lotes_sem_statement]

    # PAGINAÇÃO: Aplicar sobre os statements agrupados (não lotes individuais)
    total_lotes = len(todos_lotes)  # Total de linhas VISÍVEIS na tabela
    offset = (page - 1) * per_page
    lotes = todos_lotes[offset:offset + per_page]  # Aplicar paginação

    # === ESTATÍSTICAS DE RECEBIMENTOS (entrada) ===
    stats_recebimentos = {
        'total_lotes': ExtratoLote.query.filter(ExtratoLote.tipo_transacao == 'entrada').count(),
        'lotes_pendentes': ExtratoLote.query.filter(
            ExtratoLote.tipo_transacao == 'entrada',
            ExtratoLote.status.in_(['IMPORTADO', 'AGUARDANDO_APROVACAO'])
        ).count(),
        'lotes_concluidos': ExtratoLote.query.filter(
            ExtratoLote.tipo_transacao == 'entrada',
            ExtratoLote.status == 'CONCLUIDO'
        ).count(),
        'total_linhas': db.session.query(func.sum(ExtratoLote.total_linhas)).filter(
            ExtratoLote.tipo_transacao == 'entrada'
        ).scalar() or 0,
        'linhas_conciliadas': db.session.query(func.sum(ExtratoLote.linhas_conciliadas)).filter(
            ExtratoLote.tipo_transacao == 'entrada'
        ).scalar() or 0,
        'valor_total': db.session.query(func.sum(ExtratoLote.valor_total)).filter(
            ExtratoLote.tipo_transacao == 'entrada'
        ).scalar() or 0
    }

    # === ESTATÍSTICAS DE PAGAMENTOS (saida) ===
    stats_pagamentos = {
        'total_lotes': ExtratoLote.query.filter(ExtratoLote.tipo_transacao == 'saida').count(),
        'lotes_pendentes': ExtratoLote.query.filter(
            ExtratoLote.tipo_transacao == 'saida',
            ExtratoLote.status.in_(['IMPORTADO', 'AGUARDANDO_APROVACAO'])
        ).count(),
        'lotes_concluidos': ExtratoLote.query.filter(
            ExtratoLote.tipo_transacao == 'saida',
            ExtratoLote.status == 'CONCLUIDO'
        ).count(),
        'total_linhas': db.session.query(func.sum(ExtratoLote.total_linhas)).filter(
            ExtratoLote.tipo_transacao == 'saida'
        ).scalar() or 0,
        'linhas_conciliadas': db.session.query(func.sum(ExtratoLote.linhas_conciliadas)).filter(
            ExtratoLote.tipo_transacao == 'saida'
        ).scalar() or 0,
        'valor_total': db.session.query(func.sum(ExtratoLote.valor_total)).filter(
            ExtratoLote.tipo_transacao == 'saida'
        ).scalar() or 0
    }

    # === ESTATÍSTICAS GERAIS (compatibilidade) ===
    stats = {
        'total_lotes': stats_recebimentos['total_lotes'] + stats_pagamentos['total_lotes'],
        'lotes_pendentes': stats_recebimentos['lotes_pendentes'] + stats_pagamentos['lotes_pendentes'],
        'lotes_concluidos': stats_recebimentos['lotes_concluidos'] + stats_pagamentos['lotes_concluidos'],
        'total_linhas': stats_recebimentos['total_linhas'] + stats_pagamentos['total_linhas']
    }

    # === JOURNALS DISPONÍVEIS PARA FILTRO ===
    journals = db.session.query(
        ExtratoLote.journal_code
    ).filter(
        ExtratoLote.journal_code.isnot(None)
    ).distinct().all()
    journals = [j[0] for j in journals if j[0]]

    # Calcular paginação
    total_pages = (total_lotes + per_page - 1) // per_page

    return render_template(
        'financeiro/extrato_unificado.html',
        lotes=lotes,
        stats=stats,
        stats_recebimentos=stats_recebimentos,
        stats_pagamentos=stats_pagamentos,
        journals=journals,
        # Filtros atuais
        filtro_data_de=filtro_data_de,
        filtro_data_ate=filtro_data_ate,
        filtro_status=filtro_status,
        filtro_journal=filtro_journal,
        filtro_tipo=filtro_tipo,
        # Paginação
        page=page,
        per_page=per_page,
        total_lotes=total_lotes,
        total_pages=total_pages
    )


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

        tipo_label = 'recebimentos' if tipo_transacao == 'entrada' else 'pagamentos'
        flash(
            f'Importação concluída: {lote.total_linhas} linhas de "{lote.statement_name}" ({tipo_label}). '
            f'CNPJs identificados: {service.estatisticas["com_cnpj"]}',
            'success'
        )

        return redirect(url_for('financeiro.extrato_lote_detalhe', lote_id=lote.id))

    except Exception as e:
        flash(f'Erro na importação: {e}', 'error')
        return redirect(url_for('financeiro.extrato_hub'))


@financeiro_bp.route('/extrato/importar', methods=['POST'])
@login_required
def extrato_importar():
    """Importa linhas de extrato não conciliadas do Odoo (legado - por journal)."""
    journal_code = request.form.get('journal_code')
    limit = request.form.get('limit', 100, type=int)

    if not journal_code:
        flash('Selecione um journal', 'error')
        return redirect(url_for('financeiro.extrato_hub'))

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
        return redirect(url_for('financeiro.extrato_hub'))


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
    from sqlalchemy import func, case, or_
    stats_query = db.session.query(
        func.count().label('total'),
        func.sum(case((ExtratoItem.status_match == 'MATCH_ENCONTRADO', 1), else_=0)).label('com_match'),
        func.sum(case((ExtratoItem.status_match == 'MULTIPLOS_MATCHES', 1), else_=0)).label('multiplos'),
        func.sum(case((ExtratoItem.status_match == 'MULTIPLOS_VINCULADOS', 1), else_=0)).label('vinculados'),
        func.sum(case((ExtratoItem.status_match == 'SEM_MATCH', 1), else_=0)).label('sem_match'),
        func.sum(case((ExtratoItem.status_match == 'PENDENTE', 1), else_=0)).label('pendentes'),
        func.sum(case((ExtratoItem.aprovado == True, 1), else_=0)).label('aprovados'),
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
        return redirect(url_for('financeiro.extrato_hub'))

    try:
        lote_ids = [int(x.strip()) for x in lotes_param.split(',') if x.strip()]
    except ValueError:
        flash('IDs de lotes inválidos', 'error')
        return redirect(url_for('financeiro.extrato_hub'))

    if not lote_ids:
        flash('Nenhum lote selecionado', 'warning')
        return redirect(url_for('financeiro.extrato_hub'))

    # Buscar lotes
    lotes = ExtratoLote.query.filter(ExtratoLote.id.in_(lote_ids)).all()
    if not lotes:
        flash('Lotes não encontrados', 'error')
        return redirect(url_for('financeiro.extrato_hub'))

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
    from sqlalchemy import func, case
    stats_query = db.session.query(
        func.count().label('total'),
        func.sum(case((ExtratoItem.status_match == 'MATCH_ENCONTRADO', 1), else_=0)).label('com_match'),
        func.sum(case((ExtratoItem.status_match == 'MULTIPLOS_MATCHES', 1), else_=0)).label('multiplos'),
        func.sum(case((ExtratoItem.status_match == 'SEM_MATCH', 1), else_=0)).label('sem_match'),
        func.sum(case((ExtratoItem.status_match == 'PENDENTE', 1), else_=0)).label('pendentes'),
        func.sum(case((ExtratoItem.aprovado == True, 1), else_=0)).label('aprovados'),
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
    from sqlalchemy import func, case, or_
    stats_query = db.session.query(
        func.count().label('total'),
        func.sum(case((ExtratoItem.status_match == 'MATCH_ENCONTRADO', 1), else_=0)).label('com_match'),
        func.sum(case((ExtratoItem.status_match == 'MULTIPLOS_MATCHES', 1), else_=0)).label('multiplos'),
        func.sum(case((ExtratoItem.status_match == 'MULTIPLOS_VINCULADOS', 1), else_=0)).label('vinculados'),
        func.sum(case((ExtratoItem.status_match == 'SEM_MATCH', 1), else_=0)).label('sem_match'),
        func.sum(case((ExtratoItem.status_match == 'PENDENTE', 1), else_=0)).label('pendentes'),
        func.sum(case((ExtratoItem.aprovado == True, 1), else_=0)).label('aprovados'),
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

    return render_template(
        'financeiro/extrato_lote_pagamentos_detalhe.html',
        lote=lote,
        itens=itens,
        stats=stats,
        pagination=pagination,
        per_page=per_page,
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
    item.titulo_receber_id = None  # FK correta para clientes
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


@financeiro_bp.route('/extrato/api/aprovar-item', methods=['POST'])
@login_required
def extrato_aprovar_item():
    """Aprova um item para conciliação."""
    data = request.get_json()
    item_id = data.get('item_id')
    aprovar = data.get('aprovar', True)

    item = ExtratoItem.query.get_or_404(item_id)

    # Verificar se tem título vinculado (1:1 via FK OU M:N via tabela associativa)
    if aprovar and not item.titulo_receber_id and not item.tem_multiplos_titulos:
        return jsonify({
            'success': False,
            'error': 'Item não possui título vinculado'
        }), 400

    item.aprovado = aprovar
    item.aprovado_em = datetime.utcnow() if aprovar else None
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
        if item.titulo_receber_id:  # FK correta para clientes
            item.aprovado = True
            item.aprovado_em = datetime.utcnow()
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
    if not item.titulo_receber_id and not item.tem_multiplos_titulos:
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
        lote.processado_em = datetime.utcnow()
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
        if item.titulo_receber_id:  # FK correta para clientes
            item.aprovado = True
            item.aprovado_em = datetime.utcnow()
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
            lote = ExtratoLote.query.get(lote_id)
            if not lote:
                continue

            lote.status = 'CONCILIANDO'
            db.session.commit()

            resultado = service.conciliar_lote(lote_id)
            total_conciliados += resultado.get('conciliados', 0)
            total_erros += resultado.get('erros', 0)

            lote.linhas_conciliadas = (lote.linhas_conciliadas or 0) + resultado['conciliados']
            lote.linhas_erro = (lote.linhas_erro or 0) + resultado['erros']
            lote.processado_em = datetime.utcnow()
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
    return redirect(url_for('financeiro.extrato_hub'))
