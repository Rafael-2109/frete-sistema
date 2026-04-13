"""
Rotas de Despesas CarVia — CRUD completo
"""

import logging
from datetime import date, datetime

from flask import render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError

from app import db
from app.carvia.models import CarviaDespesa

logger = logging.getLogger(__name__)

TIPOS_DESPESA = ['CONTABILIDADE', 'GRIS', 'SEGURO', 'OUTROS', 'DESCONSIDERAR', 'COMISSAO']
STATUS_DESPESA = ['PENDENTE', 'PAGO', 'CANCELADO']


def register_despesa_routes(bp):

    @bp.route('/despesas') # type: ignore
    @login_required
    def listar_despesas(): # type: ignore
        """Lista despesas CarVia com filtros"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        page = request.args.get('page', 1, type=int)
        tipo_filtro = request.args.get('tipo', '')
        status_filtro = request.args.get('status', '')
        busca = request.args.get('busca', '')
        sort = request.args.get('sort', 'criado_em')
        direction = request.args.get('direction', 'desc')

        query = db.session.query(CarviaDespesa)

        if tipo_filtro:
            query = query.filter(CarviaDespesa.tipo_despesa == tipo_filtro)
        if status_filtro:
            query = query.filter(CarviaDespesa.status == status_filtro)
        if busca:
            busca_like = f'%{busca}%'
            query = query.filter(
                db.or_(
                    CarviaDespesa.descricao.ilike(busca_like),
                    CarviaDespesa.observacoes.ilike(busca_like),
                )
            )

        # Ordenacao dinamica
        sortable_columns = {
            'tipo_despesa': CarviaDespesa.tipo_despesa,
            'valor': CarviaDespesa.valor,
            'data_despesa': CarviaDespesa.data_despesa,
            'data_vencimento': CarviaDespesa.data_vencimento,
            'status': CarviaDespesa.status,
            'criado_em': CarviaDespesa.criado_em,
        }
        sort_col = sortable_columns.get(sort, CarviaDespesa.criado_em)
        if direction == 'asc':
            query = query.order_by(sort_col.asc().nullslast())
        else:
            query = query.order_by(sort_col.desc().nullslast())

        paginacao = query.paginate(page=page, per_page=25, error_out=False)

        today = date.today()

        return render_template(
            'carvia/despesas/listar.html',
            despesas=paginacao.items,
            paginacao=paginacao,
            tipo_filtro=tipo_filtro,
            status_filtro=status_filtro,
            busca=busca,
            sort=sort,
            direction=direction,
            tipos_despesa=TIPOS_DESPESA,
            today=today,
        )

    @bp.route('/despesas/criar', methods=['GET', 'POST']) # type: ignore
    @login_required
    def criar_despesa(): # type: ignore
        """Cria nova despesa"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        if request.method == 'POST':
            tipo_despesa = request.form.get('tipo_despesa', '').strip()
            descricao = request.form.get('descricao', '').strip()
            valor_str = request.form.get('valor', '').strip()
            data_despesa_str = request.form.get('data_despesa', '').strip()
            data_vencimento_str = request.form.get('data_vencimento', '').strip()
            observacoes = request.form.get('observacoes', '').strip()

            # Validacoes
            if not tipo_despesa or not valor_str or not data_despesa_str:
                flash('Tipo, valor e data da despesa sao obrigatorios.', 'warning')
                return redirect(url_for('carvia.criar_despesa'))

            if tipo_despesa not in TIPOS_DESPESA:
                flash('Tipo de despesa invalido.', 'warning')
                return redirect(url_for('carvia.criar_despesa'))

            # W13 (Sprint 1 followup): Despesas COMISSAO so podem ser criadas
            # pelo ComissaoService (via Fechamento de Comissao). Criar via UI
            # produz orfa permanentemente bloqueada.
            if tipo_despesa == 'COMISSAO':
                flash(
                    'Despesas de Comissao sao criadas automaticamente pelo '
                    'Fechamento de Comissao. Use o modulo de Comissao.',
                    'warning',
                )
                return redirect(url_for('carvia.criar_despesa'))

            try:
                # Aceitar virgula como separador decimal
                valor = float(valor_str.replace(',', '.'))
                if valor <= 0:
                    flash('Valor deve ser maior que zero.', 'warning')
                    return redirect(url_for('carvia.criar_despesa'))

                data_despesa = date.fromisoformat(data_despesa_str)
                data_vencimento = date.fromisoformat(data_vencimento_str) if data_vencimento_str else None

                despesa = CarviaDespesa(
                    tipo_despesa=tipo_despesa,
                    descricao=descricao or None,
                    valor=valor,
                    data_despesa=data_despesa,
                    data_vencimento=data_vencimento,
                    status='PENDENTE',
                    observacoes=observacoes or None,
                    criado_por=current_user.email,
                )
                db.session.add(despesa)
                db.session.commit()

                flash(f'Despesa #{despesa.id} criada com sucesso.', 'success')
                return redirect(url_for('carvia.detalhe_despesa', despesa_id=despesa.id))

            except ValueError as ve:
                flash(f'Dados invalidos: {ve}', 'warning')
            except Exception as e:
                db.session.rollback()
                logger.error(f"Erro ao criar despesa: {e}")
                flash(f'Erro: {e}', 'danger')

        return render_template(
            'carvia/despesas/criar.html',
            tipos_despesa=TIPOS_DESPESA,
        )

    @bp.route('/despesas/<int:despesa_id>') # type: ignore
    @login_required
    def detalhe_despesa(despesa_id): # type: ignore
        """Detalhe de uma despesa"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        despesa = db.session.get(CarviaDespesa, despesa_id)
        if not despesa:
            flash('Despesa nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_despesas'))

        return render_template(
            'carvia/despesas/detalhe.html',
            despesa=despesa,
        )

    @bp.route('/despesas/<int:despesa_id>/editar', methods=['GET', 'POST']) # type: ignore
    @login_required
    def editar_despesa(despesa_id): # type: ignore
        """Edita uma despesa existente.

        W13 (Sprint 1): Despesas tipo COMISSAO sao imutaveis via rotas
        normais — alteracoes devem passar pelo fluxo de ComissaoFechamento
        (que usa ComissaoService._sincronizar_despesa para consistencia).
        """
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        despesa = db.session.get(CarviaDespesa, despesa_id)
        if not despesa:
            flash('Despesa nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_despesas'))

        if despesa.status == 'CANCELADO':
            flash('Nao e possivel editar despesa cancelada.', 'warning')
            return redirect(url_for('carvia.detalhe_despesa', despesa_id=despesa_id))

        # W13: Despesa COMISSAO e imutavel via rotas normais
        if despesa.tipo_despesa == 'COMISSAO':
            flash(
                'Despesa de Comissao nao pode ser editada diretamente. '
                'Altere o percentual/CTes no Fechamento de Comissao '
                'correspondente — o valor da despesa sera recalculado '
                'automaticamente.',
                'warning',
            )
            return redirect(url_for('carvia.detalhe_despesa', despesa_id=despesa_id))

        if request.method == 'POST':
            tipo_despesa = request.form.get('tipo_despesa', '').strip()
            descricao = request.form.get('descricao', '').strip()
            valor_str = request.form.get('valor', '').strip()
            data_despesa_str = request.form.get('data_despesa', '').strip()
            data_vencimento_str = request.form.get('data_vencimento', '').strip()
            observacoes = request.form.get('observacoes', '').strip()

            if not tipo_despesa or not valor_str or not data_despesa_str:
                flash('Tipo, valor e data da despesa sao obrigatorios.', 'warning')
                return redirect(url_for('carvia.editar_despesa', despesa_id=despesa_id))

            if tipo_despesa not in TIPOS_DESPESA:
                flash('Tipo de despesa invalido.', 'warning')
                return redirect(url_for('carvia.editar_despesa', despesa_id=despesa_id))

            # W13 (Sprint 1 followup): nao permitir MUDAR tipo_despesa PARA
            # COMISSAO — criaria o mesmo estado orfao que criar_despesa evita.
            if tipo_despesa == 'COMISSAO':
                flash(
                    'Tipo COMISSAO e reservado para despesas criadas pelo '
                    'Fechamento de Comissao. Nao e possivel converter '
                    'manualmente.',
                    'warning',
                )
                return redirect(url_for('carvia.editar_despesa', despesa_id=despesa_id))

            try:
                valor = float(valor_str.replace(',', '.'))
                if valor <= 0:
                    flash('Valor deve ser maior que zero.', 'warning')
                    return redirect(url_for('carvia.editar_despesa', despesa_id=despesa_id))

                despesa.tipo_despesa = tipo_despesa
                despesa.descricao = descricao or None
                despesa.valor = valor
                despesa.data_despesa = date.fromisoformat(data_despesa_str)
                despesa.data_vencimento = date.fromisoformat(data_vencimento_str) if data_vencimento_str else None
                despesa.observacoes = observacoes or None

                db.session.commit()
                flash('Despesa atualizada com sucesso.', 'success')
                return redirect(url_for('carvia.detalhe_despesa', despesa_id=despesa_id))

            except ValueError as ve:
                flash(f'Dados invalidos: {ve}', 'warning')
            except Exception as e:
                db.session.rollback()
                logger.error(f"Erro ao editar despesa {despesa_id}: {e}")
                flash(f'Erro: {e}', 'danger')

        return render_template(
            'carvia/despesas/editar.html',
            despesa=despesa,
            tipos_despesa=TIPOS_DESPESA,
        )

    @bp.route('/despesas/<int:despesa_id>/status', methods=['POST']) # type: ignore
    @login_required
    def atualizar_status_despesa(despesa_id): # type: ignore
        """Atualiza status de uma despesa"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        despesa = db.session.get(CarviaDespesa, despesa_id)
        if not despesa:
            flash('Despesa nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_despesas'))

        novo_status = request.form.get('status')
        # W10 Nivel 2 (Sprint 4): apenas PENDENTE e CANCELADO aqui.
        # Para PAGO, usar endpoint JSON /despesas/<id>/pagar (service centralizado).
        if novo_status not in ('PENDENTE', 'CANCELADO'):
            flash(
                'Status invalido. Para marcar como PAGO, use o botao "Pagar".',
                'warning',
            )
            return redirect(url_for('carvia.detalhe_despesa', despesa_id=despesa_id))

        # W13: Despesa COMISSAO nao pode ser cancelada diretamente.
        if despesa.tipo_despesa == 'COMISSAO' and novo_status == 'CANCELADO':
            flash(
                'Despesa de Comissao nao pode ser cancelada diretamente. '
                'Cancele o Fechamento de Comissao correspondente.',
                'warning',
            )
            return redirect(url_for('carvia.detalhe_despesa', despesa_id=despesa_id))

        # NC1: bloquear transicao PAGO -> CANCELADO direta. R4 exige que
        # CANCELADO venha de PENDENTE — desfazer pagamento primeiro,
        # cancelar depois (2 acoes explicitas).
        if despesa.status == 'PAGO' and novo_status == 'CANCELADO':
            flash(
                'Nao e possivel cancelar despesa PAGA diretamente. '
                'Desfaca o pagamento primeiro (isso reverte para PENDENTE), '
                'depois cancele.',
                'warning',
            )
            return redirect(url_for(
                'carvia.detalhe_despesa', despesa_id=despesa_id
            ))

        try:
            # Se revertendo de PAGO, usar service de desfazer (desconcilia MANUAL)
            if despesa.status == 'PAGO':
                from app.carvia.services.financeiro.carvia_pagamento_service import (
                    CarviaPagamentoService, PagamentoError,
                )
                try:
                    CarviaPagamentoService.desfazer_pagamento(
                        'despesa', despesa_id, current_user.email
                    )
                except PagamentoError as e:
                    db.session.rollback()
                    flash(str(e), 'danger')
                    return redirect(url_for(
                        'carvia.detalhe_despesa', despesa_id=despesa_id
                    ))
                # Compat historico (ContaMovimentacao legada) e feito
                # INTERNAMENTE por CarviaPagamentoService.desfazer_pagamento.

            despesa.status = novo_status
            db.session.commit()
            flash(f'Status atualizado para {novo_status}.', 'success')

        except Exception as e:
            db.session.rollback()
            logger.exception(f"Erro ao atualizar status despesa {despesa_id}: {e}")
            flash(f'Erro: {e}', 'danger')

        return redirect(url_for('carvia.detalhe_despesa', despesa_id=despesa_id))

    @bp.route('/despesas/<int:despesa_id>/pagar', methods=['POST']) # type: ignore
    @login_required
    def pagar_despesa(despesa_id): # type: ignore
        """Paga despesa via CarviaPagamentoService (JSON).

        Modos: com_conciliacao (extrato_linha_id) ou manual (conta_origem).
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        despesa = db.session.get(CarviaDespesa, despesa_id)
        if not despesa:
            return jsonify({'erro': 'Despesa nao encontrada'}), 404

        data = request.get_json() or {}
        data_pagamento_str = data.get('data_pagamento', '')
        extrato_linha_id = data.get('extrato_linha_id')
        conta_origem = data.get('conta_origem')
        descricao_pagamento = data.get('descricao_pagamento')

        if not data_pagamento_str:
            return jsonify({'erro': 'data_pagamento e obrigatoria'}), 400
        try:
            data_pagamento = date.fromisoformat(data_pagamento_str)
        except ValueError:
            return jsonify({'erro': 'Data de pagamento invalida'}), 400

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
                    tipo_doc='despesa',
                    doc_id=despesa_id,
                    data_pagamento=data_pagamento,
                    extrato_linha_id=extrato_linha_id,
                    usuario=current_user.email,
                )
            else:
                resultado = CarviaPagamentoService.pagar_manual(
                    tipo_doc='despesa',
                    doc_id=despesa_id,
                    data_pagamento=data_pagamento,
                    conta_origem=conta_origem,
                    descricao_pagamento=descricao_pagamento,
                    usuario=current_user.email,
                )
            db.session.commit()
            return jsonify({
                'sucesso': True,
                'novo_status': resultado['novo_status'],
                'pago_em': despesa.pago_em.isoformat() if despesa.pago_em else None,
                'pago_por': despesa.pago_por,
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
            logger.exception(f"Erro ao pagar despesa #{despesa_id}: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/despesas/<int:despesa_id>/desfazer-pagamento', methods=['POST']) # type: ignore
    @login_required
    def desfazer_pagamento_despesa(despesa_id): # type: ignore
        """Desfaz pagamento da despesa (JSON)."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        from app.carvia.services.financeiro.carvia_pagamento_service import (
            CarviaPagamentoService,
            DocumentoNaoEncontradoError,
            PagamentoError,
        )

        try:
            resultado = CarviaPagamentoService.desfazer_pagamento(
                'despesa', despesa_id, current_user.email
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
            logger.exception(f"Erro desfazer despesa #{despesa_id}: {e}")
            return jsonify({'erro': str(e)}), 500
