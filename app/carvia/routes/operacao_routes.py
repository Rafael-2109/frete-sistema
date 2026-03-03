"""
Rotas de Operacoes CarVia — CRUD operacoes + subcontratos
"""

import logging
from flask import render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app import db
from app.carvia.models import (
    CarviaOperacao, CarviaSubcontrato, CarviaNf, CarviaOperacaoNf
)

logger = logging.getLogger(__name__)


def register_operacao_routes(bp):

    @bp.route('/operacoes')
    @login_required
    def listar_operacoes():
        """Lista operacoes com filtros e paginacao"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 25, type=int)
        status_filtro = request.args.get('status', '')
        busca = request.args.get('busca', '')
        tipo_filtro = request.args.get('tipo', '')
        sort = request.args.get('sort', 'criado_em')
        direction = request.args.get('direction', 'desc')

        # Subquery: contar NFs vinculadas a cada operacao
        subq_nfs = db.session.query(
            CarviaOperacaoNf.operacao_id,
            func.count(CarviaOperacaoNf.nf_id).label('qtd_nfs')
        ).group_by(CarviaOperacaoNf.operacao_id).subquery()

        query = db.session.query(
            CarviaOperacao, subq_nfs.c.qtd_nfs
        ).outerjoin(
            subq_nfs, CarviaOperacao.id == subq_nfs.c.operacao_id
        ).options(joinedload(CarviaOperacao.fatura_cliente))

        if status_filtro:
            query = query.filter(CarviaOperacao.status == status_filtro)

        if tipo_filtro:
            query = query.filter(CarviaOperacao.tipo_entrada == tipo_filtro)

        if busca:
            busca_like = f'%{busca}%'
            query = query.filter(
                db.or_(
                    CarviaOperacao.nome_cliente.ilike(busca_like),
                    CarviaOperacao.cnpj_cliente.ilike(busca_like),
                    CarviaOperacao.cte_numero.ilike(busca_like),
                    CarviaOperacao.cidade_destino.ilike(busca_like),
                )
            )

        # Ordenacao dinamica
        sortable_columns = {
            'cte_numero': CarviaOperacao.cte_numero,
            'nome_cliente': CarviaOperacao.nome_cliente,
            'peso_utilizado': CarviaOperacao.peso_utilizado,
            'cte_valor': CarviaOperacao.cte_valor,
            'status': CarviaOperacao.status,
            'criado_em': CarviaOperacao.criado_em,
        }
        sort_col = sortable_columns.get(sort, CarviaOperacao.criado_em)
        if direction == 'asc':
            query = query.order_by(sort_col.asc().nullslast())
        else:
            query = query.order_by(sort_col.desc().nullslast())

        paginacao = query.paginate(page=page, per_page=per_page, error_out=False)

        return render_template(
            'carvia/listar_operacoes.html',
            operacoes=paginacao.items,
            paginacao=paginacao,
            status_filtro=status_filtro,
            tipo_filtro=tipo_filtro,
            busca=busca,
            sort=sort,
            direction=direction,
        )

    @bp.route('/operacoes/<int:operacao_id>')
    @login_required
    def detalhe_operacao(operacao_id):
        """Detalhe de uma operacao com NFs e subcontratos"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        operacao = db.session.get(CarviaOperacao, operacao_id)
        if not operacao:
            flash('Operacao nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_operacoes'))

        nfs = operacao.nfs.all()
        subcontratos = operacao.subcontratos.all()

        # Cross-links: faturas transportadora via subcontratos
        from app.carvia.models import CarviaFaturaTransportadora
        fat_transp_ids = {
            s.fatura_transportadora_id for s in subcontratos
            if s.fatura_transportadora_id
        }
        faturas_transportadora = []
        if fat_transp_ids:
            faturas_transportadora = CarviaFaturaTransportadora.query.filter(
                CarviaFaturaTransportadora.id.in_(fat_transp_ids)
            ).all()

        return render_template(
            'carvia/detalhe_operacao.html',
            operacao=operacao,
            nfs=nfs,
            subcontratos=subcontratos,
            faturas_transportadora=faturas_transportadora,
        )

    # ==================== CRIAR OPERACAO MANUAL ====================

    @bp.route('/operacoes/criar', methods=['GET', 'POST'])
    @login_required
    def criar_operacao_manual():
        """Cria operacao manual (sem CTe) — suporta MANUAL_SEM_CTE e MANUAL_FRETEIRO"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        from app.carvia.forms import OperacaoManualForm
        form = OperacaoManualForm()

        # Tipo de entrada: do form POST ou query param GET (para pre-selecao via redirect)
        if request.method == 'POST':
            tipo_entrada = request.form.get('tipo_entrada', 'MANUAL_SEM_CTE')
        else:
            tipo_entrada = request.args.get('tipo', 'MANUAL_SEM_CTE')
        if tipo_entrada not in ('MANUAL_SEM_CTE', 'MANUAL_FRETEIRO'):
            tipo_entrada = 'MANUAL_SEM_CTE'

        if form.validate_on_submit():
            try:
                operacao = CarviaOperacao(
                    cnpj_cliente=form.cnpj_cliente.data.strip(),
                    nome_cliente=form.nome_cliente.data.strip(),
                    uf_origem=form.uf_origem.data.strip().upper() if form.uf_origem.data else None,
                    cidade_origem=form.cidade_origem.data.strip() if form.cidade_origem.data else None,
                    uf_destino=form.uf_destino.data.strip().upper(),
                    cidade_destino=form.cidade_destino.data.strip(),
                    peso_bruto=form.peso_bruto.data,
                    peso_utilizado=form.peso_bruto.data,
                    valor_mercadoria=form.valor_mercadoria.data,
                    tipo_entrada=tipo_entrada,
                    status='RASCUNHO',
                    observacoes=form.observacoes.data,
                    criado_por=current_user.email,
                )
                db.session.add(operacao)
                db.session.commit()
                flash(f'Operacao #{operacao.id} criada com sucesso.', 'success')
                return redirect(url_for('carvia.detalhe_operacao', operacao_id=operacao.id))
            except Exception as e:
                db.session.rollback()
                logger.error(f"Erro ao criar operacao manual: {e}")
                flash(f'Erro ao criar operacao: {e}', 'danger')

        return render_template(
            'carvia/criar_manual.html',
            form=form,
            tipo_entrada=tipo_entrada,
        )

    @bp.route('/operacoes/criar-freteiro', methods=['GET', 'POST'])
    @login_required
    def criar_operacao_freteiro():
        """Redireciona para criar_operacao_manual com tipo freteiro pre-selecionado"""
        return redirect(url_for('carvia.criar_operacao_manual', tipo='MANUAL_FRETEIRO'))

    # ==================== EDITAR OPERACAO ====================

    @bp.route('/operacoes/<int:operacao_id>/editar', methods=['GET', 'POST'])
    @login_required
    def editar_operacao(operacao_id):
        """Edita dados de uma operacao"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        operacao = db.session.get(CarviaOperacao, operacao_id)
        if not operacao:
            flash('Operacao nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_operacoes'))

        if operacao.status in ('FATURADO', 'CANCELADO'):
            flash('Operacao faturada ou cancelada nao pode ser editada.', 'warning')
            return redirect(url_for('carvia.detalhe_operacao', operacao_id=operacao_id))

        from app.carvia.forms import OperacaoManualForm
        form = OperacaoManualForm(obj=operacao)

        if form.validate_on_submit():
            try:
                operacao.cnpj_cliente = form.cnpj_cliente.data.strip()
                operacao.nome_cliente = form.nome_cliente.data.strip()
                operacao.uf_origem = form.uf_origem.data.strip().upper() if form.uf_origem.data else None
                operacao.cidade_origem = form.cidade_origem.data.strip() if form.cidade_origem.data else None
                operacao.uf_destino = form.uf_destino.data.strip().upper()
                operacao.cidade_destino = form.cidade_destino.data.strip()
                operacao.peso_bruto = form.peso_bruto.data
                operacao.valor_mercadoria = form.valor_mercadoria.data
                operacao.observacoes = form.observacoes.data
                operacao.calcular_peso_utilizado()
                db.session.commit()
                flash('Operacao atualizada com sucesso.', 'success')
                return redirect(url_for('carvia.detalhe_operacao', operacao_id=operacao_id))
            except Exception as e:
                db.session.rollback()
                logger.error(f"Erro ao editar operacao: {e}")
                flash(f'Erro ao editar: {e}', 'danger')

        return render_template(
            'carvia/editar_operacao.html',
            form=form,
            operacao=operacao,
        )

    # ==================== CANCELAR OPERACAO ====================

    @bp.route('/operacoes/<int:operacao_id>/cancelar', methods=['POST'])
    @login_required
    def cancelar_operacao(operacao_id):
        """Cancela uma operacao"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        operacao = db.session.get(CarviaOperacao, operacao_id)
        if not operacao:
            flash('Operacao nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_operacoes'))

        if operacao.status == 'FATURADO':
            flash('Operacao faturada nao pode ser cancelada.', 'warning')
            return redirect(url_for('carvia.detalhe_operacao', operacao_id=operacao_id))

        try:
            operacao.status = 'CANCELADO'
            # Cancelar subcontratos pendentes
            for sub in operacao.subcontratos.filter(
                CarviaSubcontrato.status.notin_(['FATURADO', 'CANCELADO'])
            ).all():
                sub.status = 'CANCELADO'
            db.session.commit()
            flash('Operacao cancelada.', 'success')
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao cancelar operacao: {e}")
            flash(f'Erro ao cancelar: {e}', 'danger')

        return redirect(url_for('carvia.detalhe_operacao', operacao_id=operacao_id))

    # ==================== CUBAGEM ====================

    @bp.route('/operacoes/<int:operacao_id>/cubagem', methods=['GET', 'POST'])
    @login_required
    def atualizar_cubagem(operacao_id):
        """Atualiza cubagem da operacao"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        operacao = db.session.get(CarviaOperacao, operacao_id)
        if not operacao:
            flash('Operacao nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_operacoes'))

        from app.carvia.forms import CubagemForm
        form = CubagemForm(obj=operacao)

        if form.validate_on_submit():
            try:
                if form.peso_cubado.data:
                    operacao.peso_cubado = form.peso_cubado.data
                else:
                    operacao.cubagem_comprimento = form.cubagem_comprimento.data
                    operacao.cubagem_largura = form.cubagem_largura.data
                    operacao.cubagem_altura = form.cubagem_altura.data
                    operacao.cubagem_fator = form.cubagem_fator.data
                    operacao.cubagem_volumes = form.cubagem_volumes.data
                    operacao.calcular_cubagem()

                operacao.calcular_peso_utilizado()
                db.session.commit()
                flash(
                    f'Cubagem atualizada. Peso utilizado: '
                    f'{float(operacao.peso_utilizado):.1f} kg',
                    'success'
                )
                return redirect(url_for('carvia.detalhe_operacao', operacao_id=operacao_id))
            except Exception as e:
                db.session.rollback()
                logger.error(f"Erro ao atualizar cubagem: {e}")
                flash(f'Erro: {e}', 'danger')

        return render_template(
            'carvia/cubagem.html',
            form=form,
            operacao=operacao,
        )

    # ==================== SUBCONTRATOS ====================

    @bp.route('/operacoes/<int:operacao_id>/subcontrato/adicionar', methods=['GET', 'POST'])
    @login_required
    def adicionar_subcontrato(operacao_id):
        """Adiciona subcontrato (transportadora) a uma operacao"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        operacao = db.session.get(CarviaOperacao, operacao_id)
        if not operacao:
            flash('Operacao nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_operacoes'))

        if operacao.status in ('FATURADO', 'CANCELADO'):
            flash('Operacao faturada/cancelada nao aceita subcontratos.', 'warning')
            return redirect(url_for('carvia.detalhe_operacao', operacao_id=operacao_id))

        if request.method == 'POST':
            transportadora_id = request.form.get('transportadora_id', type=int)
            valor_acertado = request.form.get('valor_acertado', type=float)
            observacoes = request.form.get('observacoes', '')

            if not transportadora_id:
                flash('Selecione uma transportadora.', 'warning')
                return redirect(url_for(
                    'carvia.adicionar_subcontrato', operacao_id=operacao_id
                ))

            try:
                # Verificar se ja existe subcontrato para esta transportadora
                existente = db.session.query(CarviaSubcontrato).filter(
                    CarviaSubcontrato.operacao_id == operacao_id,
                    CarviaSubcontrato.transportadora_id == transportadora_id,
                    CarviaSubcontrato.status != 'CANCELADO',
                ).first()

                if existente:
                    flash('Ja existe um subcontrato ativo para esta transportadora nesta operacao.', 'warning')
                    return redirect(url_for(
                        'carvia.adicionar_subcontrato', operacao_id=operacao_id
                    ))

                # Cotar automaticamente
                from app.carvia.services.cotacao_service import CotacaoService
                cotacao = CotacaoService().cotar_subcontrato(
                    operacao_id=operacao_id,
                    transportadora_id=transportadora_id,
                )

                # Gerar numero sequencial por transportadora
                max_seq = db.session.query(
                    db.func.max(CarviaSubcontrato.numero_sequencial_transportadora)
                ).filter(
                    CarviaSubcontrato.transportadora_id == transportadora_id,
                ).scalar() or 0

                subcontrato = CarviaSubcontrato(
                    operacao_id=operacao_id,
                    transportadora_id=transportadora_id,
                    numero_sequencial_transportadora=max_seq + 1,
                    valor_cotado=cotacao.get('valor_cotado') if cotacao.get('sucesso') else None,
                    tabela_frete_id=cotacao.get('tabela_frete_id') if cotacao.get('sucesso') else None,
                    valor_acertado=valor_acertado if valor_acertado else None,
                    status='COTADO' if cotacao.get('sucesso') else 'PENDENTE',
                    observacoes=observacoes or None,
                    criado_por=current_user.email,
                )
                db.session.add(subcontrato)

                # Atualizar status da operacao se necessario
                if operacao.status == 'RASCUNHO' and cotacao.get('sucesso'):
                    operacao.status = 'COTADO'

                db.session.commit()

                msg = f'Subcontrato adicionado.'
                if cotacao.get('sucesso'):
                    msg += f' Cotacao: R$ {cotacao["valor_cotado"]:.2f}'
                    if cotacao.get('tabela_nome'):
                        msg += f' (Tabela: {cotacao["tabela_nome"]})'
                else:
                    msg += f' Sem cotacao automatica: {cotacao.get("erro", "")}'

                flash(msg, 'success' if cotacao.get('sucesso') else 'warning')
                return redirect(url_for('carvia.detalhe_operacao', operacao_id=operacao_id))

            except Exception as e:
                db.session.rollback()
                logger.error(f"Erro ao adicionar subcontrato: {e}")
                flash(f'Erro: {e}', 'danger')

        # GET — pagina de selecao de transportadora
        is_freteiro = operacao.tipo_entrada == 'MANUAL_FRETEIRO'

        return render_template(
            'carvia/subcontrato/selecionar_transportadora.html',
            operacao=operacao,
            is_freteiro=is_freteiro,
        )

    @bp.route('/operacoes/<int:operacao_id>/subcontrato/<int:sub_id>/confirmar', methods=['POST'])
    @login_required
    def confirmar_subcontrato(operacao_id, sub_id):
        """Confirma um subcontrato (COTADO -> CONFIRMADO)"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        sub = db.session.get(CarviaSubcontrato, sub_id)
        if not sub or sub.operacao_id != operacao_id:
            flash('Subcontrato nao encontrado.', 'warning')
            return redirect(url_for('carvia.listar_operacoes'))

        if sub.status not in ('PENDENTE', 'COTADO'):
            flash(f'Subcontrato com status {sub.status} nao pode ser confirmado.', 'warning')
            return redirect(url_for('carvia.detalhe_operacao', operacao_id=operacao_id))

        try:
            sub.status = 'CONFIRMADO'

            # Atualizar operacao para CONFIRMADO se todos os subs estao confirmados
            operacao = db.session.get(CarviaOperacao, operacao_id)
            subs_ativos = operacao.subcontratos.filter(
                CarviaSubcontrato.status != 'CANCELADO'
            ).all()
            todos_confirmados = all(s.status == 'CONFIRMADO' for s in subs_ativos)
            if todos_confirmados and subs_ativos:
                operacao.status = 'CONFIRMADO'

            db.session.commit()
            flash('Subcontrato confirmado.', 'success')
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao confirmar subcontrato: {e}")
            flash(f'Erro: {e}', 'danger')

        return redirect(url_for('carvia.detalhe_operacao', operacao_id=operacao_id))

    @bp.route('/operacoes/<int:operacao_id>/subcontrato/<int:sub_id>/cancelar', methods=['POST'])
    @login_required
    def cancelar_subcontrato(operacao_id, sub_id):
        """Cancela um subcontrato"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        sub = db.session.get(CarviaSubcontrato, sub_id)
        if not sub or sub.operacao_id != operacao_id:
            flash('Subcontrato nao encontrado.', 'warning')
            return redirect(url_for('carvia.listar_operacoes'))

        if sub.status == 'FATURADO':
            flash('Subcontrato faturado nao pode ser cancelado.', 'warning')
            return redirect(url_for('carvia.detalhe_operacao', operacao_id=operacao_id))

        try:
            sub.status = 'CANCELADO'
            db.session.commit()
            flash('Subcontrato cancelado.', 'success')
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao cancelar subcontrato: {e}")
            flash(f'Erro: {e}', 'danger')

        return redirect(url_for('carvia.detalhe_operacao', operacao_id=operacao_id))

    @bp.route('/operacoes/<int:operacao_id>/subcontrato/<int:sub_id>/valor', methods=['POST'])
    @login_required
    def atualizar_valor_subcontrato(operacao_id, sub_id):
        """Atualiza valor acertado de um subcontrato"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        sub = db.session.get(CarviaSubcontrato, sub_id)
        if not sub or sub.operacao_id != operacao_id:
            flash('Subcontrato nao encontrado.', 'warning')
            return redirect(url_for('carvia.listar_operacoes'))

        try:
            valor_acertado = request.form.get('valor_acertado', type=float)
            sub.valor_acertado = valor_acertado
            db.session.commit()
            flash(f'Valor acertado atualizado: R$ {valor_acertado:.2f}' if valor_acertado else 'Valor acertado removido.', 'success')
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao atualizar valor: {e}")
            flash(f'Erro: {e}', 'danger')

        return redirect(url_for('carvia.detalhe_operacao', operacao_id=operacao_id))

    @bp.route('/operacoes/<int:operacao_id>/subcontrato/<int:sub_id>/recotar', methods=['POST'])
    @login_required
    def recotar_subcontrato(operacao_id, sub_id):
        """Recalcula cotacao de um subcontrato"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        sub = db.session.get(CarviaSubcontrato, sub_id)
        if not sub or sub.operacao_id != operacao_id:
            flash('Subcontrato nao encontrado.', 'warning')
            return redirect(url_for('carvia.listar_operacoes'))

        try:
            from app.carvia.services.cotacao_service import CotacaoService
            cotacao = CotacaoService().cotar_subcontrato(
                operacao_id=operacao_id,
                transportadora_id=sub.transportadora_id,
            )

            if cotacao.get('sucesso'):
                sub.valor_cotado = cotacao['valor_cotado']
                sub.tabela_frete_id = cotacao.get('tabela_frete_id')
                if sub.status == 'PENDENTE':
                    sub.status = 'COTADO'
                db.session.commit()
                flash(f'Recotacao: R$ {cotacao["valor_cotado"]:.2f}', 'success')
            else:
                flash(f'Erro na recotacao: {cotacao.get("erro")}', 'warning')

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao recotar: {e}")
            flash(f'Erro: {e}', 'danger')

        return redirect(url_for('carvia.detalhe_operacao', operacao_id=operacao_id))
