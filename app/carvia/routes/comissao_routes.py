"""
Rotas de Comissao CarVia — Fechamento, inclusao/exclusao CTe, pagamento
"""

import logging
from datetime import date
from decimal import Decimal

from flask import render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user

from app import db

logger = logging.getLogger(__name__)

STATUS_COMISSAO = ['PENDENTE', 'PAGO', 'CANCELADO']


def _pode_acessar_comissao():
    """Verifica acesso composto: sistema_carvia AND (acesso_comissao_carvia OR admin)."""
    return (
        getattr(current_user, 'sistema_carvia', False)
        and (
            getattr(current_user, 'acesso_comissao_carvia', False)
            or getattr(current_user, 'perfil', '') == 'administrador'
        )
    )


def register_comissao_routes(bp):

    # ==================== LISTAGEM ====================

    @bp.route('/comissoes')  # type: ignore
    @login_required
    def listar_comissoes():  # type: ignore
        """Lista fechamentos de comissao com filtros"""
        if not _pode_acessar_comissao():
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        from app.carvia.models.comissao import CarviaComissaoFechamento

        page = request.args.get('page', 1, type=int)
        status_filtro = request.args.get('status', '')
        vendedor_filtro = request.args.get('vendedor', '')
        sort = request.args.get('sort', 'data_inicio')
        direction = request.args.get('direction', 'desc')

        query = db.session.query(CarviaComissaoFechamento)

        if status_filtro:
            query = query.filter(CarviaComissaoFechamento.status == status_filtro)
        if vendedor_filtro:
            busca_like = f'%{vendedor_filtro}%'
            query = query.filter(
                db.or_(
                    CarviaComissaoFechamento.vendedor_nome.ilike(busca_like),
                    CarviaComissaoFechamento.vendedor_email.ilike(busca_like),
                )
            )

        sortable_columns = {
            'numero_fechamento': CarviaComissaoFechamento.numero_fechamento,
            'vendedor_nome': CarviaComissaoFechamento.vendedor_nome,
            'data_inicio': CarviaComissaoFechamento.data_inicio,
            'total_comissao': CarviaComissaoFechamento.total_comissao,
            'status': CarviaComissaoFechamento.status,
            'criado_em': CarviaComissaoFechamento.criado_em,
        }
        sort_col = sortable_columns.get(sort, CarviaComissaoFechamento.data_inicio)
        if direction == 'asc':
            query = query.order_by(sort_col.asc().nullslast())
        else:
            query = query.order_by(sort_col.desc().nullslast())

        paginacao = query.paginate(page=page, per_page=25, error_out=False)

        return render_template(
            'carvia/comissoes/listar.html',
            fechamentos=paginacao.items,
            paginacao=paginacao,
            status_filtro=status_filtro,
            vendedor_filtro=vendedor_filtro,
            sort=sort,
            direction=direction,
        )

    # ==================== CRIAR ====================

    @bp.route('/comissoes/criar', methods=['GET', 'POST'])  # type: ignore
    @login_required
    def criar_comissao():  # type: ignore
        """Cria novo fechamento de comissao"""
        if not _pode_acessar_comissao():
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        from app.carvia.services.financeiro.comissao_service import ComissaoService

        # Percentual default
        try:
            pct_default = ComissaoService.get_percentual_config()
            pct_display = float(pct_default * 100)
            pct_warning = None
        except ValueError as e:
            pct_display = None
            pct_warning = str(e)

        if request.method == 'POST':
            vendedor_nome = request.form.get('vendedor_nome', '').strip()
            vendedor_email = request.form.get('vendedor_email', '').strip()
            data_inicio_str = request.form.get('data_inicio', '').strip()
            data_fim_str = request.form.get('data_fim', '').strip()
            percentual_str = request.form.get('percentual', '').strip()
            observacoes = request.form.get('observacoes', '').strip()
            operacao_ids_raw = request.form.getlist('operacao_ids')

            # Validacoes basicas
            if not vendedor_nome:
                flash('Nome do vendedor e obrigatorio.', 'warning')
                return redirect(url_for('carvia.criar_comissao'))
            if not data_inicio_str or not data_fim_str:
                flash('Periodo e obrigatorio.', 'warning')
                return redirect(url_for('carvia.criar_comissao'))
            if not operacao_ids_raw:
                flash('Selecione ao menos um CTe.', 'warning')
                return redirect(url_for('carvia.criar_comissao'))

            try:
                data_inicio = date.fromisoformat(data_inicio_str)
                data_fim = date.fromisoformat(data_fim_str)

                percentual = None
                if percentual_str:
                    percentual = Decimal(percentual_str.replace(',', '.'))

                operacao_ids = [int(x) for x in operacao_ids_raw]

                fechamento = ComissaoService.criar_fechamento(
                    vendedor_nome=vendedor_nome,
                    vendedor_email=vendedor_email,
                    data_inicio=data_inicio,
                    data_fim=data_fim,
                    operacao_ids=operacao_ids,
                    criado_por=current_user.email,
                    percentual=percentual,
                    observacoes=observacoes,
                )

                flash(
                    f'Comissao {fechamento.numero_fechamento} criada: '
                    f'{fechamento.qtd_ctes} CTes, R$ {fechamento.total_comissao:,.2f}',
                    'success',
                )
                return redirect(url_for('carvia.detalhe_comissao', comissao_id=fechamento.id))

            except ValueError as ve:
                flash(str(ve), 'warning')
            except Exception as e:
                db.session.rollback()
                logger.error("Erro ao criar comissao: %s", e)
                flash(f'Erro: {e}', 'danger')

        return render_template(
            'carvia/comissoes/criar.html',
            pct_display=pct_display,
            pct_warning=pct_warning,
        )

    # ==================== DETALHE ====================

    @bp.route('/comissoes/<int:comissao_id>')  # type: ignore
    @login_required
    def detalhe_comissao(comissao_id):  # type: ignore
        """Detalhe de um fechamento de comissao"""
        if not _pode_acessar_comissao():
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        from app.carvia.models.comissao import (
            CarviaComissaoFechamento, CarviaComissaoFechamentoCte,
        )

        fechamento = db.session.get(CarviaComissaoFechamento, comissao_id)
        if not fechamento:
            flash('Fechamento nao encontrado.', 'warning')
            return redirect(url_for('carvia.listar_comissoes'))

        # CTes ativos (nao excluidos)
        ctes_ativos = CarviaComissaoFechamentoCte.query.filter_by(
            fechamento_id=comissao_id,
            excluido=False,
        ).order_by(CarviaComissaoFechamentoCte.cte_data_emissao.asc()).all()

        # CTes excluidos (para historico)
        ctes_excluidos = CarviaComissaoFechamentoCte.query.filter_by(
            fechamento_id=comissao_id,
            excluido=True,
        ).order_by(CarviaComissaoFechamentoCte.excluido_em.desc()).all()

        return render_template(
            'carvia/comissoes/detalhe.html',
            fechamento=fechamento,
            ctes_ativos=ctes_ativos,
            ctes_excluidos=ctes_excluidos,
        )

    # ==================== STATUS ====================

    @bp.route('/comissoes/<int:comissao_id>/status', methods=['POST'])  # type: ignore
    @login_required
    def atualizar_status_comissao(comissao_id):  # type: ignore
        """Atualiza status: PAGO ou CANCELADO"""
        if not _pode_acessar_comissao():
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        from app.carvia.services.financeiro.comissao_service import ComissaoService

        novo_status = request.form.get('status', '').strip()

        try:
            if novo_status == 'PAGO':
                data_pagamento_str = request.form.get('data_pagamento', '').strip()
                if not data_pagamento_str:
                    flash('Data de pagamento e obrigatoria.', 'warning')
                    return redirect(url_for('carvia.detalhe_comissao', comissao_id=comissao_id))
                data_pagamento = date.fromisoformat(data_pagamento_str)
                ComissaoService.marcar_pago(comissao_id, data_pagamento, current_user.email)
                flash('Comissao marcada como PAGA.', 'success')
            elif novo_status == 'CANCELADO':
                ComissaoService.cancelar(comissao_id, current_user.email)
                flash('Comissao cancelada.', 'success')
            else:
                flash('Status invalido.', 'warning')

        except ValueError as ve:
            flash(str(ve), 'warning')
        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao atualizar status comissao %d: %s", comissao_id, e)
            flash(f'Erro: {e}', 'danger')

        return redirect(url_for('carvia.detalhe_comissao', comissao_id=comissao_id))

    # ==================== API: CTes elegiveis ====================

    @bp.route('/api/comissoes/ctes-elegiveis')  # type: ignore
    @login_required
    def api_ctes_elegiveis():  # type: ignore
        """Retorna CTes elegiveis para o periodo (JSON)"""
        if not _pode_acessar_comissao():
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.services.financeiro.comissao_service import ComissaoService

        data_inicio_str = request.args.get('data_inicio', '')
        data_fim_str = request.args.get('data_fim', '')

        if not data_inicio_str or not data_fim_str:
            return jsonify({'erro': 'Periodo obrigatorio (data_inicio, data_fim).'}), 400

        try:
            data_inicio = date.fromisoformat(data_inicio_str)
            data_fim = date.fromisoformat(data_fim_str)
        except ValueError:
            return jsonify({'erro': 'Formato de data invalido (YYYY-MM-DD).'}), 400

        ctes = ComissaoService.buscar_ctes_elegiveis(data_inicio, data_fim)

        return jsonify({
            'sucesso': True,
            'qtd': len(ctes),
            'ctes': [
                {
                    'id': op.id,
                    'cte_numero': op.cte_numero,
                    'cte_data_emissao': op.cte_data_emissao.isoformat() if op.cte_data_emissao else None,
                    'cte_valor': float(op.cte_valor) if op.cte_valor else 0,
                    'cnpj_cliente': op.cnpj_cliente,
                    'nome_cliente': op.nome_cliente,
                    'uf_destino': op.uf_destino,
                    'cidade_destino': op.cidade_destino,
                    'status': op.status,
                }
                for op in ctes
            ],
        })

    # ==================== API: Incluir CTe ====================

    @bp.route('/api/comissoes/<int:comissao_id>/incluir-cte', methods=['POST'])  # type: ignore
    @login_required
    def api_incluir_cte(comissao_id):  # type: ignore
        """Inclui CTe no fechamento (JSON)"""
        if not _pode_acessar_comissao():
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.services.financeiro.comissao_service import ComissaoService

        data = request.get_json()
        if not data or not data.get('operacao_id'):
            return jsonify({'erro': 'operacao_id obrigatorio.'}), 400

        try:
            ComissaoService.incluir_cte(
                fechamento_id=comissao_id,
                operacao_id=int(data['operacao_id']),
                incluido_por=current_user.email,
            )

            # Retornar totais atualizados
            from app.carvia.models.comissao import CarviaComissaoFechamento
            fechamento = db.session.get(CarviaComissaoFechamento, comissao_id)

            return jsonify({
                'sucesso': True,
                'mensagem': 'CTe incluido com sucesso.',
                'totais': {
                    'qtd_ctes': fechamento.qtd_ctes,
                    'total_bruto': float(fechamento.total_bruto),
                    'total_comissao': float(fechamento.total_comissao),
                },
            })
        except ValueError as ve:
            return jsonify({'erro': str(ve)}), 400
        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao incluir CTe em comissao %d: %s", comissao_id, e)
            return jsonify({'erro': f'Erro: {e}'}), 500

    # ==================== API: Excluir CTe ====================

    @bp.route('/api/comissoes/<int:comissao_id>/excluir-cte', methods=['POST'])  # type: ignore
    @login_required
    def api_excluir_cte(comissao_id):  # type: ignore
        """Exclui (soft) CTe do fechamento (JSON)"""
        if not _pode_acessar_comissao():
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.services.financeiro.comissao_service import ComissaoService

        data = request.get_json()
        if not data or not data.get('operacao_id'):
            return jsonify({'erro': 'operacao_id obrigatorio.'}), 400

        try:
            ComissaoService.excluir_cte(
                fechamento_id=comissao_id,
                operacao_id=int(data['operacao_id']),
                excluido_por=current_user.email,
            )

            from app.carvia.models.comissao import CarviaComissaoFechamento
            fechamento = db.session.get(CarviaComissaoFechamento, comissao_id)

            return jsonify({
                'sucesso': True,
                'mensagem': 'CTe excluido do fechamento.',
                'totais': {
                    'qtd_ctes': fechamento.qtd_ctes,
                    'total_bruto': float(fechamento.total_bruto),
                    'total_comissao': float(fechamento.total_comissao),
                },
            })
        except ValueError as ve:
            return jsonify({'erro': str(ve)}), 400
        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao excluir CTe de comissao %d: %s", comissao_id, e)
            return jsonify({'erro': f'Erro: {e}'}), 500
