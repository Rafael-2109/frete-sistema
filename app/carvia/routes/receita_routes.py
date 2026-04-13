"""
Rotas de Receitas CarVia — CRUD completo
"""

import logging
from datetime import date, datetime

from flask import render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError

from app import db
from app.carvia.models import CarviaReceita

logger = logging.getLogger(__name__)

STATUS_RECEITA = ['PENDENTE', 'RECEBIDO', 'CANCELADO']


def register_receita_routes(bp):

    @bp.route('/receitas') # type: ignore
    @login_required
    def listar_receitas(): # type: ignore
        """Lista receitas CarVia com filtros"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        page = request.args.get('page', 1, type=int)
        tipo_filtro = request.args.get('tipo', '')
        status_filtro = request.args.get('status', '')
        busca = request.args.get('busca', '')
        sort = request.args.get('sort', 'criado_em')
        direction = request.args.get('direction', 'desc')

        query = db.session.query(CarviaReceita)

        if tipo_filtro:
            query = query.filter(CarviaReceita.tipo_receita == tipo_filtro)
        if status_filtro:
            query = query.filter(CarviaReceita.status == status_filtro)
        if busca:
            busca_like = f'%{busca}%'
            query = query.filter(
                db.or_(
                    CarviaReceita.descricao.ilike(busca_like),
                    CarviaReceita.observacoes.ilike(busca_like),
                )
            )

        # Ordenacao dinamica
        sortable_columns = {
            'tipo_receita': CarviaReceita.tipo_receita,
            'valor': CarviaReceita.valor,
            'data_receita': CarviaReceita.data_receita,
            'data_vencimento': CarviaReceita.data_vencimento,
            'status': CarviaReceita.status,
            'criado_em': CarviaReceita.criado_em,
        }
        sort_col = sortable_columns.get(sort, CarviaReceita.criado_em)
        if direction == 'asc':
            query = query.order_by(sort_col.asc().nullslast())
        else:
            query = query.order_by(sort_col.desc().nullslast())

        paginacao = query.paginate(page=page, per_page=25, error_out=False)

        today = date.today()

        # Tipos existentes para filtro dinamico
        tipos_receita = [
            row[0] for row in
            db.session.query(CarviaReceita.tipo_receita)
            .distinct()
            .order_by(CarviaReceita.tipo_receita)
            .all()
            if row[0]
        ]

        return render_template(
            'carvia/receitas/listar.html',
            receitas=paginacao.items,
            paginacao=paginacao,
            tipo_filtro=tipo_filtro,
            status_filtro=status_filtro,
            busca=busca,
            sort=sort,
            direction=direction,
            tipos_receita=tipos_receita,
            today=today,
        )

    @bp.route('/receitas/criar', methods=['GET', 'POST']) # type: ignore
    @login_required
    def criar_receita(): # type: ignore
        """Cria nova receita"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        if request.method == 'POST':
            tipo_receita = request.form.get('tipo_receita', '').strip()
            descricao = request.form.get('descricao', '').strip()
            valor_str = request.form.get('valor', '').strip()
            data_receita_str = request.form.get('data_receita', '').strip()
            data_vencimento_str = request.form.get('data_vencimento', '').strip()
            observacoes = request.form.get('observacoes', '').strip()

            # Validacoes
            if not tipo_receita or not valor_str or not data_receita_str:
                flash('Tipo, valor e data da receita sao obrigatorios.', 'warning')
                return redirect(url_for('carvia.criar_receita'))

            try:
                # Aceitar virgula como separador decimal
                valor = float(valor_str.replace(',', '.'))
                if valor <= 0:
                    flash('Valor deve ser maior que zero.', 'warning')
                    return redirect(url_for('carvia.criar_receita'))

                data_receita = date.fromisoformat(data_receita_str)
                data_vencimento = date.fromisoformat(data_vencimento_str) if data_vencimento_str else None

                receita = CarviaReceita(
                    tipo_receita=tipo_receita,
                    descricao=descricao or None,
                    valor=valor,
                    data_receita=data_receita,
                    data_vencimento=data_vencimento,
                    status='PENDENTE',
                    observacoes=observacoes or None,
                    criado_por=current_user.email,
                )
                db.session.add(receita)
                db.session.commit()

                flash(f'Receita #{receita.id} criada com sucesso.', 'success')
                return redirect(url_for('carvia.detalhe_receita', receita_id=receita.id))

            except ValueError as ve:
                flash(f'Dados invalidos: {ve}', 'warning')
            except Exception as e:
                db.session.rollback()
                logger.error(f"Erro ao criar receita: {e}")
                flash(f'Erro: {e}', 'danger')

        return render_template('carvia/receitas/criar.html')

    @bp.route('/receitas/<int:receita_id>') # type: ignore
    @login_required
    def detalhe_receita(receita_id): # type: ignore
        """Detalhe de uma receita"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        receita = db.session.get(CarviaReceita, receita_id)
        if not receita:
            flash('Receita nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_receitas'))

        return render_template(
            'carvia/receitas/detalhe.html',
            receita=receita,
        )

    @bp.route('/receitas/<int:receita_id>/editar', methods=['GET', 'POST']) # type: ignore
    @login_required
    def editar_receita(receita_id): # type: ignore
        """Edita uma receita existente"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        receita = db.session.get(CarviaReceita, receita_id)
        if not receita:
            flash('Receita nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_receitas'))

        if receita.status == 'CANCELADO':
            flash('Nao e possivel editar receita cancelada.', 'warning')
            return redirect(url_for('carvia.detalhe_receita', receita_id=receita_id))

        if request.method == 'POST':
            tipo_receita = request.form.get('tipo_receita', '').strip()
            descricao = request.form.get('descricao', '').strip()
            valor_str = request.form.get('valor', '').strip()
            data_receita_str = request.form.get('data_receita', '').strip()
            data_vencimento_str = request.form.get('data_vencimento', '').strip()
            observacoes = request.form.get('observacoes', '').strip()

            if not tipo_receita or not valor_str or not data_receita_str:
                flash('Tipo, valor e data da receita sao obrigatorios.', 'warning')
                return redirect(url_for('carvia.editar_receita', receita_id=receita_id))

            try:
                valor = float(valor_str.replace(',', '.'))
                if valor <= 0:
                    flash('Valor deve ser maior que zero.', 'warning')
                    return redirect(url_for('carvia.editar_receita', receita_id=receita_id))

                receita.tipo_receita = tipo_receita
                receita.descricao = descricao or None
                receita.valor = valor
                receita.data_receita = date.fromisoformat(data_receita_str)
                receita.data_vencimento = date.fromisoformat(data_vencimento_str) if data_vencimento_str else None
                receita.observacoes = observacoes or None

                db.session.commit()
                flash('Receita atualizada com sucesso.', 'success')
                return redirect(url_for('carvia.detalhe_receita', receita_id=receita_id))

            except ValueError as ve:
                flash(f'Dados invalidos: {ve}', 'warning')
            except Exception as e:
                db.session.rollback()
                logger.error(f"Erro ao editar receita {receita_id}: {e}")
                flash(f'Erro: {e}', 'danger')

        return render_template(
            'carvia/receitas/editar.html',
            receita=receita,
        )

    @bp.route('/receitas/<int:receita_id>/status', methods=['POST']) # type: ignore
    @login_required
    def atualizar_status_receita(receita_id): # type: ignore
        """Atualiza status de uma receita"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        receita = db.session.get(CarviaReceita, receita_id)
        if not receita:
            flash('Receita nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_receitas'))

        novo_status = request.form.get('status')
        # W10 Nivel 2 (Sprint 4): apenas PENDENTE e CANCELADO aqui.
        # Para RECEBIDO, usar endpoint JSON /receitas/<id>/receber.
        if novo_status not in ('PENDENTE', 'CANCELADO'):
            flash(
                'Status invalido. Para marcar como RECEBIDO, use o botao "Receber".',
                'warning',
            )
            return redirect(url_for('carvia.detalhe_receita', receita_id=receita_id))

        # NC1: bloquear transicao RECEBIDO -> CANCELADO direta. R4 exige que
        # CANCELADO venha de PENDENTE — desfazer recebimento primeiro,
        # cancelar depois (2 acoes explicitas).
        if receita.status == 'RECEBIDO' and novo_status == 'CANCELADO':
            flash(
                'Nao e possivel cancelar receita RECEBIDA diretamente. '
                'Desfaca o recebimento primeiro (isso reverte para PENDENTE), '
                'depois cancele.',
                'warning',
            )
            return redirect(url_for(
                'carvia.detalhe_receita', receita_id=receita_id
            ))

        try:
            # Se revertendo de RECEBIDO, usar service de desfazer
            if receita.status == 'RECEBIDO':
                from app.carvia.services.financeiro.carvia_pagamento_service import (
                    CarviaPagamentoService, PagamentoError,
                )
                try:
                    CarviaPagamentoService.desfazer_pagamento(
                        'receita', receita_id, current_user.email
                    )
                except PagamentoError as e:
                    db.session.rollback()
                    flash(str(e), 'danger')
                    return redirect(url_for(
                        'carvia.detalhe_receita', receita_id=receita_id
                    ))
                # Compat historico (ContaMovimentacao legada) e feito
                # INTERNAMENTE por CarviaPagamentoService.desfazer_pagamento.

            receita.status = novo_status
            db.session.commit()
            flash(f'Status atualizado para {novo_status}.', 'success')

        except Exception as e:
            db.session.rollback()
            logger.exception(f"Erro ao atualizar status receita {receita_id}: {e}")
            flash(f'Erro: {e}', 'danger')

        return redirect(url_for('carvia.detalhe_receita', receita_id=receita_id))

    @bp.route('/receitas/<int:receita_id>/receber', methods=['POST']) # type: ignore
    @login_required
    def receber_receita(receita_id): # type: ignore
        """Marca receita como RECEBIDO via CarviaPagamentoService (JSON)."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        receita = db.session.get(CarviaReceita, receita_id)
        if not receita:
            return jsonify({'erro': 'Receita nao encontrada'}), 404

        data = request.get_json() or {}
        # Aceita tanto data_recebimento quanto data_pagamento (normalizacao)
        data_recebimento_str = (
            data.get('data_recebimento') or data.get('data_pagamento') or ''
        )
        extrato_linha_id = data.get('extrato_linha_id')
        conta_origem = data.get('conta_origem')
        descricao_pagamento = data.get('descricao_pagamento')

        if not data_recebimento_str:
            return jsonify({'erro': 'data_recebimento e obrigatoria'}), 400
        try:
            data_recebimento = date.fromisoformat(data_recebimento_str)
        except ValueError:
            return jsonify({'erro': 'Data de recebimento invalida'}), 400

        from app.carvia.services.financeiro.carvia_pagamento_service import (
            CarviaPagamentoService,
            DocumentoJaPagoError,
            DocumentoCanceladoError,
            DocumentoNaoEncontradoError,
            JaConciliadoError,
            ParametroInvalidoError,
            PagamentoError,
        )

        try:
            if extrato_linha_id:
                resultado = CarviaPagamentoService.pagar_com_conciliacao(
                    tipo_doc='receita',
                    doc_id=receita_id,
                    data_pagamento=data_recebimento,
                    extrato_linha_id=extrato_linha_id,
                    usuario=current_user.email,
                )
            else:
                resultado = CarviaPagamentoService.pagar_manual(
                    tipo_doc='receita',
                    doc_id=receita_id,
                    data_pagamento=data_recebimento,
                    conta_origem=conta_origem,
                    descricao_pagamento=descricao_pagamento,
                    usuario=current_user.email,
                )
            db.session.commit()
            return jsonify({
                'sucesso': True,
                'novo_status': resultado['novo_status'],
                'pago_em': (
                    receita.recebido_em.isoformat() if receita.recebido_em else None
                ),
                'pago_por': receita.recebido_por,
                'extrato_linha_id': resultado.get('extrato_linha_id'),
                'modo': resultado.get('modo'),
            })

        except DocumentoNaoEncontradoError as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 404
        except DocumentoJaPagoError as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 409
        except DocumentoCanceladoError as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 400
        except JaConciliadoError as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 400
        except ParametroInvalidoError as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 400
        except PagamentoError as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 400
        except Exception as e:
            db.session.rollback()
            logger.exception(f"Erro ao receber receita #{receita_id}: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/receitas/<int:receita_id>/desfazer-recebimento', methods=['POST']) # type: ignore
    @login_required
    def desfazer_recebimento_receita(receita_id): # type: ignore
        """Desfaz recebimento de receita (JSON)."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        from app.carvia.services.financeiro.carvia_pagamento_service import (
            CarviaPagamentoService,
            DocumentoNaoEncontradoError,
            PagamentoError,
        )

        try:
            resultado = CarviaPagamentoService.desfazer_pagamento(
                'receita', receita_id, current_user.email
            )
            # Compat historico (ContaMovimentacao legada) e feito
            # INTERNAMENTE por CarviaPagamentoService.desfazer_pagamento.
            db.session.commit()
            return jsonify({
                'sucesso': True,
                'novo_status': resultado['novo_status'],
            })
        except DocumentoNaoEncontradoError as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 404
        except PagamentoError as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 400
        except Exception as e:
            db.session.rollback()
            logger.exception(f"Erro desfazer receita #{receita_id}: {e}")
            return jsonify({'erro': str(e)}), 500
