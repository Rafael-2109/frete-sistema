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
from app.financeiro.models import ExtratoLote, ExtratoItem, ContasAReceber
from app.financeiro.services.extrato_service import ExtratoService


# =============================================================================
# HUB PRINCIPAL
# =============================================================================

@financeiro_bp.route('/extrato/')
@login_required
def extrato_hub():
    """Hub principal de conciliação via extrato."""
    # Filtro por journal
    journal_filter = request.args.get('journal')

    # Estatísticas dos lotes (consultas locais - rápidas)
    total_lotes = ExtratoLote.query.count()
    lotes_pendentes = ExtratoLote.query.filter(
        ExtratoLote.status.in_(['IMPORTADO', 'AGUARDANDO_APROVACAO'])
    ).count()

    # Últimos lotes
    ultimos_lotes = ExtratoLote.query.order_by(
        ExtratoLote.criado_em.desc()
    ).limit(5).all()

    # NÃO buscar statements aqui - será feito via AJAX para não travar a página
    # Os statements serão carregados pelo endpoint /extrato/api/statements

    return render_template(
        'financeiro/extrato_hub.html',
        total_lotes=total_lotes,
        lotes_pendentes=lotes_pendentes,
        ultimos_lotes=ultimos_lotes,
        journal_filter=journal_filter
    )


@financeiro_bp.route('/extrato/api/statements')
@login_required
def extrato_api_statements():
    """
    API para buscar statements do Odoo de forma assíncrona.
    Evita travar a página principal.
    """
    journal_filter = request.args.get('journal')

    try:
        service = ExtratoService()
        statements = service.listar_statements_disponiveis(journal_code=journal_filter)
        journals = service.listar_journals_disponiveis()

        return jsonify({
            'success': True,
            'statements': statements,
            'journals': journals
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'statements': [],
            'journals': []
        })


# =============================================================================
# IMPORTAÇÃO
# =============================================================================

@financeiro_bp.route('/extrato/importar-statement/<int:statement_id>', methods=['POST'])
@login_required
def extrato_importar_statement(statement_id):
    """Importa um statement específico do Odoo."""
    try:
        service = ExtratoService()
        lote = service.importar_statement(
            statement_id=statement_id,
            criado_por=current_user.nome if current_user else 'Sistema'
        )

        flash(
            f'Importação concluída: {lote.total_linhas} linhas de "{lote.statement_name}". '
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
    """Importa múltiplos statements de uma vez."""
    data = request.get_json()
    statement_ids = data.get('statement_ids', [])

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
                    criado_por=current_user.nome if current_user else 'Sistema'
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

@financeiro_bp.route('/extrato/lotes')
@login_required
def extrato_lotes():
    """Lista todos os lotes de extrato."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    query = ExtratoLote.query.order_by(ExtratoLote.criado_em.desc())

    # Filtros
    status = request.args.get('status')
    if status:
        query = query.filter(ExtratoLote.status == status)

    journal = request.args.get('journal')
    if journal:
        query = query.filter(ExtratoLote.journal_code == journal)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template(
        'financeiro/extrato_lotes.html',
        lotes=pagination.items,
        pagination=pagination
    )


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

    # Estatísticas (sem filtros - sempre mostra o total do lote)
    stats = {
        'total': lote.total_linhas,
        'com_match': ExtratoItem.query.filter_by(lote_id=lote_id, status_match='MATCH_ENCONTRADO').count(),
        'multiplos': ExtratoItem.query.filter_by(lote_id=lote_id, status_match='MULTIPLOS_MATCHES').count(),
        'sem_match': ExtratoItem.query.filter_by(lote_id=lote_id, status_match='SEM_MATCH').count(),
        'pendentes': ExtratoItem.query.filter_by(lote_id=lote_id, status_match='PENDENTE').count(),
        'aprovados': ExtratoItem.query.filter_by(lote_id=lote_id, aprovado=True).count(),
        'conciliados': ExtratoItem.query.filter_by(lote_id=lote_id, status='CONCILIADO').count(),
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

    # Estatísticas agregadas de todos os lotes
    stats = {
        'total': sum(l.total_linhas or 0 for l in lotes),
        'com_match': ExtratoItem.query.filter(
            ExtratoItem.lote_id.in_(lote_ids),
            ExtratoItem.status_match == 'MATCH_ENCONTRADO'
        ).count(),
        'multiplos': ExtratoItem.query.filter(
            ExtratoItem.lote_id.in_(lote_ids),
            ExtratoItem.status_match == 'MULTIPLOS_MATCHES'
        ).count(),
        'sem_match': ExtratoItem.query.filter(
            ExtratoItem.lote_id.in_(lote_ids),
            ExtratoItem.status_match == 'SEM_MATCH'
        ).count(),
        'pendentes': ExtratoItem.query.filter(
            ExtratoItem.lote_id.in_(lote_ids),
            ExtratoItem.status_match == 'PENDENTE'
        ).count(),
        'aprovados': ExtratoItem.query.filter(
            ExtratoItem.lote_id.in_(lote_ids),
            ExtratoItem.aprovado == True
        ).count(),
        'conciliados': ExtratoItem.query.filter(
            ExtratoItem.lote_id.in_(lote_ids),
            ExtratoItem.status == 'CONCILIADO'
        ).count(),
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
    item.titulo_id = None
    item.titulo_nf = None
    item.titulo_parcela = None
    item.titulo_valor = None
    item.titulo_vencimento = None
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

    if aprovar and not item.titulo_id:
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
        if item.titulo_id:
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

    if not item.titulo_id:
        return jsonify({
            'success': False,
            'error': 'Item não possui título vinculado'
        }), 400

    try:
        from app.financeiro.services.extrato_conciliacao_service import ExtratoConciliacaoService

        service = ExtratoConciliacaoService()
        resultado = service.conciliar_item(item)

        return jsonify({
            'success': True,
            'resultado': resultado
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
        if item.titulo_id:
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
