"""
Rotas de Faturas CarVia — Cliente + Transportadora
"""

import logging
from datetime import date

from flask import render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import func

from app import db
from app.carvia.models import (
    CarviaFaturaCliente, CarviaFaturaTransportadora,
    CarviaOperacao, CarviaSubcontrato,
)

logger = logging.getLogger(__name__)


def register_fatura_routes(bp):

    # ===================== FATURAS CLIENTE =====================

    @bp.route('/faturas-cliente')
    @login_required
    def listar_faturas_cliente():
        """Lista faturas CarVia emitidas ao cliente"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        page = request.args.get('page', 1, type=int)
        status_filtro = request.args.get('status', '')
        busca = request.args.get('busca', '')
        sort = request.args.get('sort', 'criado_em')
        direction = request.args.get('direction', 'desc')

        query = db.session.query(CarviaFaturaCliente)
        if status_filtro:
            query = query.filter(CarviaFaturaCliente.status == status_filtro)
        if busca:
            busca_like = f'%{busca}%'
            query = query.filter(
                db.or_(
                    CarviaFaturaCliente.nome_cliente.ilike(busca_like),
                    CarviaFaturaCliente.cnpj_cliente.ilike(busca_like),
                    CarviaFaturaCliente.numero_fatura.ilike(busca_like),
                )
            )

        # Ordenacao dinamica
        sortable_columns = {
            'numero_fatura': func.lpad(func.coalesce(CarviaFaturaCliente.numero_fatura, ''), 20, '0'),
            'nome_cliente': CarviaFaturaCliente.nome_cliente,
            'data_emissao': CarviaFaturaCliente.data_emissao,
            'vencimento': CarviaFaturaCliente.vencimento,
            'valor_total': CarviaFaturaCliente.valor_total,
            'status': CarviaFaturaCliente.status,
            'criado_em': CarviaFaturaCliente.criado_em,
        }
        sort_col = sortable_columns.get(sort, CarviaFaturaCliente.criado_em)
        if direction == 'asc':
            query = query.order_by(sort_col.asc().nullslast())
        else:
            query = query.order_by(sort_col.desc().nullslast())

        paginacao = query.paginate(page=page, per_page=25, error_out=False)

        return render_template(
            'carvia/faturas_cliente/listar.html',
            faturas=paginacao.items,
            paginacao=paginacao,
            status_filtro=status_filtro,
            busca=busca,
            sort=sort,
            direction=direction,
        )

    @bp.route('/faturas-cliente/nova', methods=['GET', 'POST'])
    @login_required
    def nova_fatura_cliente():
        """Cria nova fatura para o cliente — agrupa operacoes confirmadas"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        if request.method == 'POST':
            cnpj_cliente = request.form.get('cnpj_cliente', '').strip()
            numero_fatura = request.form.get('numero_fatura', '').strip()
            data_emissao_str = request.form.get('data_emissao', '')
            vencimento_str = request.form.get('vencimento', '')
            observacoes = request.form.get('observacoes', '')
            operacao_ids = request.form.getlist('operacao_ids', type=int)

            if not cnpj_cliente or not numero_fatura or not data_emissao_str:
                flash('CNPJ, numero da fatura e data de emissao sao obrigatorios.', 'warning')
                return redirect(url_for('carvia.nova_fatura_cliente'))

            if not operacao_ids:
                flash('Selecione ao menos uma operacao.', 'warning')
                return redirect(url_for('carvia.nova_fatura_cliente'))

            try:
                data_emissao = date.fromisoformat(data_emissao_str)
                vencimento = date.fromisoformat(vencimento_str) if vencimento_str else None

                # Buscar operacoes selecionadas
                operacoes = db.session.query(CarviaOperacao).filter(
                    CarviaOperacao.id.in_(operacao_ids),
                    CarviaOperacao.cnpj_cliente == cnpj_cliente,
                    CarviaOperacao.status == 'CONFIRMADO',
                    CarviaOperacao.fatura_cliente_id.is_(None),
                ).all()

                if not operacoes:
                    flash('Nenhuma operacao valida selecionada.', 'warning')
                    return redirect(url_for('carvia.nova_fatura_cliente'))

                # Calcular valor total
                valor_total = sum(
                    float(op.cte_valor or 0) for op in operacoes
                )

                fatura = CarviaFaturaCliente(
                    cnpj_cliente=cnpj_cliente,
                    nome_cliente=operacoes[0].nome_cliente,
                    numero_fatura=numero_fatura,
                    data_emissao=data_emissao,
                    valor_total=valor_total,
                    vencimento=vencimento,
                    status='PENDENTE',
                    observacoes=observacoes or None,
                    criado_por=current_user.email,
                )
                db.session.add(fatura)
                db.session.flush()

                # Vincular operacoes
                for op in operacoes:
                    op.fatura_cliente_id = fatura.id
                    op.status = 'FATURADO'

                # Gerar itens de detalhe a partir das operacoes
                from app.carvia.services.linking_service import LinkingService
                LinkingService().criar_itens_fatura_cliente_from_operacoes(fatura.id)

                db.session.commit()

                flash(
                    f'Fatura {numero_fatura} criada. '
                    f'{len(operacoes)} operacoes vinculadas. '
                    f'Valor total: R$ {valor_total:.2f}',
                    'success'
                )
                return redirect(url_for('carvia.detalhe_fatura_cliente', fatura_id=fatura.id))

            except Exception as e:
                db.session.rollback()
                logger.error(f"Erro ao criar fatura cliente: {e}")
                flash(f'Erro: {e}', 'danger')

        # GET — listar clientes com operacoes confirmadas disponiveis
        clientes = db.session.query(
            CarviaOperacao.cnpj_cliente,
            CarviaOperacao.nome_cliente,
            db.func.count(CarviaOperacao.id).label('qtd_operacoes'),
            db.func.sum(CarviaOperacao.cte_valor).label('valor_total'),
        ).filter(
            CarviaOperacao.status == 'CONFIRMADO',
            CarviaOperacao.fatura_cliente_id.is_(None),
        ).group_by(
            CarviaOperacao.cnpj_cliente,
            CarviaOperacao.nome_cliente,
        ).all()

        # Se cnpj selecionado, buscar operacoes
        cnpj_selecionado = request.args.get('cnpj', '')
        operacoes_disponiveis = []
        if cnpj_selecionado:
            operacoes_disponiveis = db.session.query(CarviaOperacao).filter(
                CarviaOperacao.cnpj_cliente == cnpj_selecionado,
                CarviaOperacao.status == 'CONFIRMADO',
                CarviaOperacao.fatura_cliente_id.is_(None),
            ).order_by(CarviaOperacao.criado_em.desc()).all()

        return render_template(
            'carvia/faturas_cliente/nova.html',
            clientes=clientes,
            cnpj_selecionado=cnpj_selecionado,
            operacoes_disponiveis=operacoes_disponiveis,
        )

    @bp.route('/faturas-cliente/<int:fatura_id>')
    @login_required
    def detalhe_fatura_cliente(fatura_id):
        """Detalhe de uma fatura CarVia ao cliente"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        fatura = db.session.get(CarviaFaturaCliente, fatura_id)
        if not fatura:
            flash('Fatura nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_faturas_cliente'))

        operacoes = db.session.query(CarviaOperacao).filter(
            CarviaOperacao.fatura_cliente_id == fatura_id
        ).order_by(CarviaOperacao.criado_em.desc()).all()

        # Cross-links: itens, NFs, subcontratos, faturas transportadora
        from app.carvia.models import (
            CarviaFaturaClienteItem, CarviaNf, CarviaOperacaoNf,
        )
        itens = CarviaFaturaClienteItem.query.filter_by(
            fatura_cliente_id=fatura_id
        ).all()

        # NFs via operacoes
        op_ids = [op.id for op in operacoes]
        nfs = []
        if op_ids:
            nf_ids = db.session.query(CarviaOperacaoNf.nf_id).filter(
                CarviaOperacaoNf.operacao_id.in_(op_ids)
            ).distinct().all()
            nf_id_list = [r[0] for r in nf_ids]
            if nf_id_list:
                nfs = CarviaNf.query.filter(CarviaNf.id.in_(nf_id_list)).all()

        # Subcontratos via operacoes
        subcontratos = db.session.query(CarviaSubcontrato).filter(
            CarviaSubcontrato.operacao_id.in_(op_ids)
        ).all() if op_ids else []

        # Faturas transportadora via subcontratos
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
            'carvia/faturas_cliente/detalhe.html',
            fatura=fatura,
            operacoes=operacoes,
            itens=itens,
            nfs=nfs,
            subcontratos=subcontratos,
            faturas_transportadora=faturas_transportadora,
        )

    @bp.route('/faturas-cliente/<int:fatura_id>/editar-vencimento', methods=['POST'])
    @login_required
    def editar_vencimento_fatura_cliente(fatura_id):
        """Edita vencimento de uma fatura cliente"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        fatura = db.session.get(CarviaFaturaCliente, fatura_id)
        if not fatura:
            flash('Fatura nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_faturas_cliente'))

        if fatura.status == 'CANCELADA':
            flash('Nao e possivel editar vencimento de fatura cancelada.', 'warning')
            return redirect(url_for('carvia.detalhe_fatura_cliente', fatura_id=fatura_id))

        vencimento_str = request.form.get('vencimento', '').strip()
        if not vencimento_str:
            flash('Informe a data de vencimento.', 'warning')
            return redirect(url_for('carvia.detalhe_fatura_cliente', fatura_id=fatura_id))

        try:
            fatura.vencimento = date.fromisoformat(vencimento_str)
            db.session.commit()
            flash(f'Vencimento atualizado para {fatura.vencimento.strftime("%d/%m/%Y")}.', 'success')
        except ValueError:
            flash('Data de vencimento invalida.', 'danger')
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao editar vencimento fatura cliente {fatura_id}: {e}")
            flash(f'Erro: {e}', 'danger')

        return redirect(url_for('carvia.detalhe_fatura_cliente', fatura_id=fatura_id))

    @bp.route('/faturas-cliente/<int:fatura_id>/status', methods=['POST'])
    @login_required
    def atualizar_status_fatura_cliente(fatura_id):
        """Atualiza status de uma fatura cliente"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        fatura = db.session.get(CarviaFaturaCliente, fatura_id)
        if not fatura:
            flash('Fatura nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_faturas_cliente'))

        novo_status = request.form.get('status')
        if novo_status not in ('PENDENTE', 'EMITIDA', 'PAGA', 'CANCELADA'):
            flash('Status invalido.', 'warning')
            return redirect(url_for('carvia.detalhe_fatura_cliente', fatura_id=fatura_id))

        try:
            fatura.status = novo_status
            db.session.commit()
            flash(f'Status atualizado para {novo_status}.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro: {e}', 'danger')

        return redirect(url_for('carvia.detalhe_fatura_cliente', fatura_id=fatura_id))

    # ===================== FATURAS TRANSPORTADORA =====================

    @bp.route('/faturas-transportadora')
    @login_required
    def listar_faturas_transportadora():
        """Lista faturas recebidas dos subcontratados"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        page = request.args.get('page', 1, type=int)
        status_filtro = request.args.get('status', '')
        busca = request.args.get('busca', '')
        sort = request.args.get('sort', 'criado_em')
        direction = request.args.get('direction', 'desc')

        query = db.session.query(CarviaFaturaTransportadora)
        if status_filtro:
            query = query.filter(
                CarviaFaturaTransportadora.status_conferencia == status_filtro
            )
        if busca:
            busca_like = f'%{busca}%'
            query = query.filter(
                db.or_(
                    CarviaFaturaTransportadora.numero_fatura.ilike(busca_like),
                )
            )

        # Ordenacao dinamica
        sortable_columns = {
            'numero_fatura': func.lpad(func.coalesce(CarviaFaturaTransportadora.numero_fatura, ''), 20, '0'),
            'data_emissao': CarviaFaturaTransportadora.data_emissao,
            'vencimento': CarviaFaturaTransportadora.vencimento,
            'valor_total': CarviaFaturaTransportadora.valor_total,
            'status_conferencia': CarviaFaturaTransportadora.status_conferencia,
            'criado_em': CarviaFaturaTransportadora.criado_em,
        }
        sort_col = sortable_columns.get(sort, CarviaFaturaTransportadora.criado_em)
        if direction == 'asc':
            query = query.order_by(sort_col.asc().nullslast())
        else:
            query = query.order_by(sort_col.desc().nullslast())

        paginacao = query.paginate(page=page, per_page=25, error_out=False)

        return render_template(
            'carvia/faturas_transportadora/listar.html',
            faturas=paginacao.items,
            paginacao=paginacao,
            status_filtro=status_filtro,
            busca=busca,
            sort=sort,
            direction=direction,
        )

    @bp.route('/faturas-transportadora/nova', methods=['GET', 'POST'])
    @login_required
    def nova_fatura_transportadora():
        """Cria nova fatura de transportadora — agrupa subcontratos confirmados"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        if request.method == 'POST':
            transportadora_id = request.form.get('transportadora_id', type=int)
            numero_fatura = request.form.get('numero_fatura', '').strip()
            data_emissao_str = request.form.get('data_emissao', '')
            vencimento_str = request.form.get('vencimento', '')
            observacoes = request.form.get('observacoes', '')
            subcontrato_ids = request.form.getlist('subcontrato_ids', type=int)

            if not transportadora_id or not numero_fatura or not data_emissao_str:
                flash('Transportadora, numero da fatura e data de emissao sao obrigatorios.', 'warning')
                return redirect(url_for('carvia.nova_fatura_transportadora'))

            if not subcontrato_ids:
                flash('Selecione ao menos um subcontrato.', 'warning')
                return redirect(url_for('carvia.nova_fatura_transportadora'))

            try:
                data_emissao = date.fromisoformat(data_emissao_str)
                vencimento = date.fromisoformat(vencimento_str) if vencimento_str else None

                # Buscar subcontratos selecionados
                subcontratos = db.session.query(CarviaSubcontrato).filter(
                    CarviaSubcontrato.id.in_(subcontrato_ids),
                    CarviaSubcontrato.transportadora_id == transportadora_id,
                    CarviaSubcontrato.status == 'CONFIRMADO',
                    CarviaSubcontrato.fatura_transportadora_id.is_(None),
                ).all()

                if not subcontratos:
                    flash('Nenhum subcontrato valido selecionado.', 'warning')
                    return redirect(url_for('carvia.nova_fatura_transportadora'))

                # Calcular valor total (valor_final = valor_acertado ou valor_cotado)
                valor_total = sum(
                    float(sub.valor_final or sub.cte_valor or 0) for sub in subcontratos
                )

                fatura = CarviaFaturaTransportadora(
                    transportadora_id=transportadora_id,
                    numero_fatura=numero_fatura,
                    data_emissao=data_emissao,
                    valor_total=valor_total,
                    vencimento=vencimento,
                    status_conferencia='PENDENTE',
                    observacoes=observacoes or None,
                    criado_por=current_user.email,
                )
                db.session.add(fatura)
                db.session.flush()

                # Vincular subcontratos
                for sub in subcontratos:
                    sub.fatura_transportadora_id = fatura.id
                    sub.status = 'FATURADO'

                # Gerar itens de detalhe a partir dos subcontratos
                from app.carvia.services.linking_service import LinkingService
                LinkingService().criar_itens_fatura_transportadora(fatura.id)

                db.session.commit()

                flash(
                    f'Fatura {numero_fatura} criada. '
                    f'{len(subcontratos)} subcontratos vinculados. '
                    f'Valor total: R$ {valor_total:.2f}',
                    'success'
                )
                return redirect(url_for('carvia.detalhe_fatura_transportadora', fatura_id=fatura.id))

            except Exception as e:
                db.session.rollback()
                logger.error(f"Erro ao criar fatura transportadora: {e}")
                flash(f'Erro: {e}', 'danger')

        # GET — listar transportadoras com subcontratos confirmados disponiveis
        from app.transportadoras.models import Transportadora
        transportadoras_disponiveis = db.session.query(
            Transportadora.id,
            Transportadora.razao_social,
            Transportadora.cnpj,
            db.func.count(CarviaSubcontrato.id).label('qtd_subcontratos'),
        ).join(
            CarviaSubcontrato,
            CarviaSubcontrato.transportadora_id == Transportadora.id,
        ).filter(
            CarviaSubcontrato.status == 'CONFIRMADO',
            CarviaSubcontrato.fatura_transportadora_id.is_(None),
        ).group_by(
            Transportadora.id,
            Transportadora.razao_social,
            Transportadora.cnpj,
        ).all()

        # Se transportadora selecionada, buscar subcontratos
        transp_selecionada = request.args.get('transportadora_id', type=int)
        subcontratos_disponiveis = []
        if transp_selecionada:
            subcontratos_disponiveis = db.session.query(CarviaSubcontrato).filter(
                CarviaSubcontrato.transportadora_id == transp_selecionada,
                CarviaSubcontrato.status == 'CONFIRMADO',
                CarviaSubcontrato.fatura_transportadora_id.is_(None),
            ).order_by(CarviaSubcontrato.criado_em.desc()).all()

        return render_template(
            'carvia/faturas_transportadora/nova.html',
            transportadoras_disponiveis=transportadoras_disponiveis,
            transp_selecionada=transp_selecionada,
            subcontratos_disponiveis=subcontratos_disponiveis,
        )

    @bp.route('/faturas-transportadora/<int:fatura_id>')
    @login_required
    def detalhe_fatura_transportadora(fatura_id):
        """Detalhe de uma fatura de transportadora"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        fatura = db.session.get(CarviaFaturaTransportadora, fatura_id)
        if not fatura:
            flash('Fatura nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_faturas_transportadora'))

        subcontratos = db.session.query(CarviaSubcontrato).filter(
            CarviaSubcontrato.fatura_transportadora_id == fatura_id
        ).order_by(CarviaSubcontrato.criado_em.desc()).all()

        # Calcular totais para conferencia
        valor_cotado_total = sum(float(s.valor_cotado or 0) for s in subcontratos)
        valor_acertado_total = sum(float(s.valor_final or 0) for s in subcontratos)

        # Cross-links: itens, NFs, faturas cliente
        from app.carvia.models import (
            CarviaFaturaTransportadoraItem, CarviaNf,
            CarviaOperacaoNf, CarviaFaturaCliente,
        )
        itens = CarviaFaturaTransportadoraItem.query.filter_by(
            fatura_transportadora_id=fatura_id
        ).all()

        # NFs via subcontratos -> operacoes
        op_ids = list({s.operacao_id for s in subcontratos if s.operacao_id})
        nfs = []
        if op_ids:
            nf_ids = db.session.query(CarviaOperacaoNf.nf_id).filter(
                CarviaOperacaoNf.operacao_id.in_(op_ids)
            ).distinct().all()
            nf_id_list = [r[0] for r in nf_ids]
            if nf_id_list:
                nfs = CarviaNf.query.filter(CarviaNf.id.in_(nf_id_list)).all()

        # Faturas cliente via operacoes
        faturas_cliente = []
        if op_ids:
            fat_cli_ids = db.session.query(CarviaOperacao.fatura_cliente_id).filter(
                CarviaOperacao.id.in_(op_ids),
                CarviaOperacao.fatura_cliente_id.isnot(None),
            ).distinct().all()
            fat_cli_id_list = [r[0] for r in fat_cli_ids]
            if fat_cli_id_list:
                faturas_cliente = CarviaFaturaCliente.query.filter(
                    CarviaFaturaCliente.id.in_(fat_cli_id_list)
                ).all()

        # Operacoes CTe CarVia via subcontratos
        operacoes = []
        if op_ids:
            operacoes = CarviaOperacao.query.filter(
                CarviaOperacao.id.in_(op_ids)
            ).order_by(CarviaOperacao.criado_em.desc()).all()

        return render_template(
            'carvia/faturas_transportadora/detalhe.html',
            fatura=fatura,
            subcontratos=subcontratos,
            valor_cotado_total=valor_cotado_total,
            valor_acertado_total=valor_acertado_total,
            itens=itens,
            nfs=nfs,
            faturas_cliente=faturas_cliente,
            operacoes=operacoes,
        )

    @bp.route('/faturas-transportadora/<int:fatura_id>/editar-vencimento', methods=['POST'])
    @login_required
    def editar_vencimento_fatura_transportadora(fatura_id):
        """Edita vencimento de uma fatura transportadora"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        fatura = db.session.get(CarviaFaturaTransportadora, fatura_id)
        if not fatura:
            flash('Fatura nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_faturas_transportadora'))

        if fatura.status_conferencia == 'CONFERIDO':
            flash('Nao e possivel editar vencimento de fatura ja conferida.', 'warning')
            return redirect(url_for('carvia.detalhe_fatura_transportadora', fatura_id=fatura_id))

        vencimento_str = request.form.get('vencimento', '').strip()
        if not vencimento_str:
            flash('Informe a data de vencimento.', 'warning')
            return redirect(url_for('carvia.detalhe_fatura_transportadora', fatura_id=fatura_id))

        try:
            fatura.vencimento = date.fromisoformat(vencimento_str)
            db.session.commit()
            flash(f'Vencimento atualizado para {fatura.vencimento.strftime("%d/%m/%Y")}.', 'success')
        except ValueError:
            flash('Data de vencimento invalida.', 'danger')
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao editar vencimento fatura transportadora {fatura_id}: {e}")
            flash(f'Erro: {e}', 'danger')

        return redirect(url_for('carvia.detalhe_fatura_transportadora', fatura_id=fatura_id))

    @bp.route('/faturas-transportadora/<int:fatura_id>/conferencia', methods=['POST'])
    @login_required
    def conferir_fatura_transportadora(fatura_id):
        """Atualiza status de conferencia de uma fatura de transportadora"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        fatura = db.session.get(CarviaFaturaTransportadora, fatura_id)
        if not fatura:
            flash('Fatura nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_faturas_transportadora'))

        novo_status = request.form.get('status')
        if novo_status not in ('PENDENTE', 'EM_CONFERENCIA', 'CONFERIDO', 'DIVERGENTE'):
            flash('Status invalido.', 'warning')
            return redirect(url_for('carvia.detalhe_fatura_transportadora', fatura_id=fatura_id))

        try:
            from app.utils.timezone import agora_utc_naive
            fatura.status_conferencia = novo_status
            if novo_status == 'CONFERIDO':
                fatura.conferido_por = current_user.email
                fatura.conferido_em = agora_utc_naive()
                # Marcar subcontratos como conferidos
                for sub in fatura.subcontratos:
                    if sub.status == 'FATURADO':
                        sub.status = 'CONFERIDO'
            db.session.commit()
            flash(f'Status de conferencia atualizado para {novo_status}.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro: {e}', 'danger')

        return redirect(url_for('carvia.detalhe_fatura_transportadora', fatura_id=fatura_id))
