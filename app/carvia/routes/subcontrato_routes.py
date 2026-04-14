"""
Rotas de CTe Subcontrato CarVia — Listagem e detalhe de subcontratos
"""

import logging
from datetime import datetime

from flask import render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user

from app import db
from sqlalchemy import func
from app.carvia.models import CarviaSubcontrato, CarviaOperacao

logger = logging.getLogger(__name__)


def register_subcontrato_routes(bp):

    @bp.route('/subcontratos') # type: ignore
    @login_required
    def listar_subcontratos(): # type: ignore
        """Lista subcontratos com filtros e paginacao"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 25, type=int)
        status_filtro = request.args.get('status', '')
        busca = request.args.get('busca', '')
        transp_filtro = request.args.get('transportadora', '')
        transp_id_param = request.args.get('transportadora_id', type=int)
        fatura_filtro = request.args.get('fatura', '')
        data_emissao_de = request.args.get('data_emissao_de', '')
        data_emissao_ate = request.args.get('data_emissao_ate', '')
        uf_origem_filtro = request.args.get('uf_origem', '')
        sort = request.args.get('sort', 'cte_data_emissao')
        direction = request.args.get('direction', 'desc')

        query = db.session.query(CarviaSubcontrato).outerjoin(
            CarviaOperacao,
            CarviaSubcontrato.operacao_id == CarviaOperacao.id,
        )

        if status_filtro:
            query = query.filter(CarviaSubcontrato.status == status_filtro)

        if fatura_filtro == 'COM':
            query = query.filter(CarviaSubcontrato.fatura_transportadora_id.isnot(None))
        elif fatura_filtro == 'SEM':
            query = query.filter(CarviaSubcontrato.fatura_transportadora_id.is_(None))

        if data_emissao_de:
            try:
                dt_de = datetime.strptime(data_emissao_de, '%Y-%m-%d').date()
                query = query.filter(CarviaSubcontrato.cte_data_emissao >= dt_de)
            except ValueError:
                pass
        if data_emissao_ate:
            try:
                dt_ate = datetime.strptime(data_emissao_ate, '%Y-%m-%d').date()
                query = query.filter(CarviaSubcontrato.cte_data_emissao <= dt_ate)
            except ValueError:
                pass

        if uf_origem_filtro:
            query = query.filter(CarviaOperacao.uf_origem == uf_origem_filtro.upper())

        # Join Transportadora se transp_filtro ou busca precisam
        if transp_filtro or transp_id_param or busca:
            from app.transportadoras.models import Transportadora
            query = query.outerjoin(
                Transportadora,
                CarviaSubcontrato.transportadora_id == Transportadora.id,
            )

        if transp_id_param:
            from app.transportadoras.filter_utils import expandir_filtro_fk
            query = query.filter(expandir_filtro_fk(CarviaSubcontrato.transportadora_id, transp_id_param))
        elif transp_filtro:
            transp_like = f'%{transp_filtro}%'
            query = query.filter(Transportadora.razao_social.ilike(transp_like))

        if busca:
            busca_like = f'%{busca}%'
            query = query.filter(
                db.or_(
                    Transportadora.razao_social.ilike(busca_like),
                    Transportadora.cnpj.ilike(busca_like),
                    CarviaSubcontrato.cte_numero.ilike(busca_like),
                    CarviaOperacao.nome_cliente.ilike(busca_like),
                    CarviaOperacao.cidade_destino.ilike(busca_like),
                )
            )

        # Ordenacao dinamica
        sortable_columns = {
            'seq': CarviaSubcontrato.numero_sequencial_transportadora,
            # GAP-37: Usar COALESCE para ordenar por valor_final real
            'valor_final': func.coalesce(CarviaSubcontrato.valor_acertado, CarviaSubcontrato.valor_cotado),
            'status': CarviaSubcontrato.status,
            'cte_data_emissao': CarviaSubcontrato.cte_data_emissao,
            'criado_em': CarviaSubcontrato.criado_em,
        }
        sort_col = sortable_columns.get(sort, CarviaSubcontrato.cte_data_emissao)
        if direction == 'asc':
            query = query.order_by(sort_col.asc().nullslast())
        else:
            query = query.order_by(sort_col.desc().nullslast())

        paginacao = query.paginate(page=page, per_page=per_page, error_out=False)

        return render_template(
            'carvia/subcontratos/listar.html',
            subcontratos=paginacao.items,
            paginacao=paginacao,
            status_filtro=status_filtro,
            busca=busca,
            transp_filtro=transp_filtro,
            fatura_filtro=fatura_filtro,
            data_emissao_de=data_emissao_de,
            data_emissao_ate=data_emissao_ate,
            uf_origem_filtro=uf_origem_filtro,
            sort=sort,
            direction=direction,
        )

    @bp.route('/subcontratos/criar', methods=['GET', 'POST']) # type: ignore
    @login_required
    def criar_subcontrato(): # type: ignore
        """Cria subcontrato standalone — Passo 1: selecionar operacao, Passo 2: transportadora"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        operacao_id = request.args.get('operacao_id', type=int)
        operacao = None

        if operacao_id:
            operacao = db.session.get(CarviaOperacao, operacao_id)
            if not operacao:
                flash('CTe CarVia nao encontrado.', 'warning')
                return redirect(url_for('carvia.criar_subcontrato'))
            if operacao.status == 'CANCELADO':
                flash('CTe CarVia cancelado nao aceita subcontratos.', 'warning')
                return redirect(url_for('carvia.criar_subcontrato'))
            if operacao.status == 'FATURADO':
                flash(
                    'CTe CarVia ja faturado. O subcontrato sera criado de forma retroativa.',
                    'info',
                )

        if request.method == 'POST' and operacao:
            transportadora_id = request.form.get('transportadora_id', type=int)
            valor_acertado = request.form.get('valor_acertado', type=float)
            cte_numero = request.form.get('cte_numero', '').strip() or None
            cte_valor = request.form.get('cte_valor', type=float)
            observacoes = request.form.get('observacoes', '').strip() or None

            if not transportadora_id:
                flash('Selecione uma transportadora.', 'warning')
                return redirect(url_for(
                    'carvia.criar_subcontrato', operacao_id=operacao_id
                ))

            try:
                from app.carvia.models import CarviaSubcontrato as SubModel

                # Verificar se ja existe subcontrato ativo para esta transportadora
                existente = db.session.query(SubModel).filter(
                    SubModel.operacao_id == operacao_id,
                    SubModel.transportadora_id == transportadora_id,
                    SubModel.status != 'CANCELADO',
                ).first()

                if existente:
                    flash(
                        'Ja existe um subcontrato ativo para esta transportadora nesta operacao.',
                        'warning',
                    )
                    return redirect(url_for(
                        'carvia.criar_subcontrato', operacao_id=operacao_id
                    ))

                # Cotar automaticamente
                from app.carvia.services.pricing.cotacao_service import CotacaoService
                cotacao = CotacaoService().cotar_subcontrato(
                    operacao_id=operacao_id,
                    transportadora_id=transportadora_id,
                )

                # Gerar numero sequencial por transportadora
                max_seq = db.session.query(
                    db.func.max(SubModel.numero_sequencial_transportadora)
                ).filter(
                    SubModel.transportadora_id == transportadora_id,
                ).scalar() or 0

                subcontrato = SubModel(
                    operacao_id=operacao_id,
                    transportadora_id=transportadora_id,
                    numero_sequencial_transportadora=max_seq + 1,
                    cte_numero=cte_numero or SubModel.gerar_numero_sub(),
                    cte_valor=cte_valor if cte_valor else None,
                    valor_cotado=cotacao.get('valor_cotado') if cotacao.get('sucesso') else None,
                    tabela_frete_id=cotacao.get('tabela_frete_id') if cotacao.get('sucesso') else None,
                    valor_acertado=valor_acertado if valor_acertado else None,
                    status='COTADO' if cotacao.get('sucesso') else 'PENDENTE',
                    observacoes=observacoes,
                    criado_por=current_user.email,
                )
                db.session.add(subcontrato)

                # Atualizar status da operacao se necessario
                if operacao.status == 'RASCUNHO' and cotacao.get('sucesso'):
                    operacao.status = 'COTADO'

                db.session.commit()

                msg = f'CTe Subcontrato #{subcontrato.id} criado.'
                if cotacao.get('sucesso'):
                    msg += f' Cotacao: R$ {cotacao["valor_cotado"]:.2f}'
                    if cotacao.get('tabela_nome'):
                        msg += f' (Tabela: {cotacao["tabela_nome"]})'
                else:
                    msg += f' Sem cotacao automatica: {cotacao.get("erro", "")}'

                flash(msg, 'success' if cotacao.get('sucesso') else 'warning')
                return redirect(url_for('carvia.detalhe_subcontrato', sub_id=subcontrato.id))

            except Exception as e:
                db.session.rollback()
                logger.error(f"Erro ao criar subcontrato standalone: {e}")
                flash(f'Erro: {e}', 'danger')

        # GET — Passo 1 ou Passo 2
        operacoes_disponiveis = []
        busca_op = ''
        if not operacao:
            # Passo 1: listar operacoes disponiveis para subcontratacao
            busca_op = request.args.get('busca_op', '').strip()
            query_ops = db.session.query(CarviaOperacao).filter(
                CarviaOperacao.status != 'CANCELADO',
            )
            if busca_op:
                busca_like = f'%{busca_op}%'
                query_ops = query_ops.filter(db.or_(
                    CarviaOperacao.cte_numero.ilike(busca_like),
                    CarviaOperacao.nome_cliente.ilike(busca_like),
                    CarviaOperacao.cidade_destino.ilike(busca_like),
                ))
            operacoes_disponiveis = query_ops.order_by(
                CarviaOperacao.criado_em.desc()
            ).limit(100).all()

        return render_template(
            'carvia/subcontratos/criar.html',
            operacao=operacao,
            operacoes_disponiveis=operacoes_disponiveis,
            busca_op=busca_op,
        )

    @bp.route('/subcontratos/<int:sub_id>') # type: ignore
    @login_required
    def detalhe_subcontrato(sub_id): # type: ignore
        """Detalhe de um subcontrato com cross-links"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        sub = db.session.get(CarviaSubcontrato, sub_id)
        if not sub:
            flash('CTe Subcontrato nao encontrado.', 'warning')
            return redirect(url_for('carvia.listar_subcontratos'))

        operacao = db.session.get(CarviaOperacao, sub.operacao_id)

        # Cross-links: NFs via operacao, fatura cliente via operacao
        from app.carvia.models import CarviaNf, CarviaOperacaoNf, CarviaFaturaCliente
        nfs = []
        fatura_cliente = None
        if operacao:
            nf_ids = db.session.query(CarviaOperacaoNf.nf_id).filter(
                CarviaOperacaoNf.operacao_id == operacao.id
            ).all()
            nf_id_list = [r[0] for r in nf_ids]
            if nf_id_list:
                nfs = CarviaNf.query.filter(CarviaNf.id.in_(nf_id_list)).all()
            if operacao.fatura_cliente_id:
                fatura_cliente = db.session.get(CarviaFaturaCliente, operacao.fatura_cliente_id)

        # Custos de entrega e CTes complementares via operacao
        from app.carvia.models import CarviaCustoEntrega, CarviaCteComplementar
        custos_entrega = []
        ctes_complementares = []
        if operacao:
            custos_entrega = CarviaCustoEntrega.query.filter(
                CarviaCustoEntrega.operacao_id == operacao.id
            ).order_by(CarviaCustoEntrega.criado_em.desc()).all()
            ctes_complementares = CarviaCteComplementar.query.filter(
                CarviaCteComplementar.operacao_id == operacao.id
            ).order_by(CarviaCteComplementar.criado_em.desc()).all()

        # Despesas Extras (xerox DespesaExtra Nacom) — via CarviaFrete do sub
        # Mostra CEs vinculados ao frete do subcontrato (fluxo compra).
        despesas_extras = []
        if sub.frete_id:
            despesas_extras = CarviaCustoEntrega.query.filter(
                CarviaCustoEntrega.frete_id == sub.frete_id,
                CarviaCustoEntrega.status != 'CANCELADO',
            ).order_by(CarviaCustoEntrega.criado_em.desc()).all()

        # Valor Conciliado: rateio proporcional do total_conciliado da fatura
        # transportadora pai, baseado no valor_considerado de cada sub/CE.
        # Substitui o antigo "Valor Pago" (W4 manual do sub, que ficava NULL).
        valor_conciliado_sub = None
        fatura_transportadora = None
        if sub.fatura_transportadora_id:
            from app.carvia.models import CarviaFaturaTransportadora
            from app.carvia.services.financeiro.rateio_conciliacao_helper import (
                ratear_conciliacao_fatura,
            )
            fatura_transportadora = db.session.get(
                CarviaFaturaTransportadora, sub.fatura_transportadora_id,
            )
            if fatura_transportadora:
                subs_fatura = CarviaSubcontrato.query.filter(
                    CarviaSubcontrato.fatura_transportadora_id == sub.fatura_transportadora_id,
                    CarviaSubcontrato.status != 'CANCELADO',
                ).all()
                ces_fatura = CarviaCustoEntrega.query.filter(
                    CarviaCustoEntrega.fatura_transportadora_id == sub.fatura_transportadora_id,
                    CarviaCustoEntrega.status != 'CANCELADO',
                ).all()
                rateio = ratear_conciliacao_fatura(
                    fatura_transportadora, subs_fatura, ces_fatura,
                )
                valor_conciliado_sub = float(rateio['por_sub'].get(sub.id, 0))

        # Operacoes disponiveis para re-vinculacao (modal "Alterar CTe CarVia")
        operacoes_disponiveis = []
        if sub.status not in ('FATURADO', 'CANCELADO', 'CONFERIDO'):
            operacoes_disponiveis = db.session.query(CarviaOperacao).filter(
                CarviaOperacao.status != 'CANCELADO',
                CarviaOperacao.id != sub.operacao_id,
            ).order_by(CarviaOperacao.criado_em.desc()).limit(100).all()

        # Flag: subcontrato eh elegivel para hard delete como "orfao legado".
        # Espelha 1:1 os guards do AdminService.excluir_subcontrato_orfao
        # (se algum guard falhar, o botao da UI nao aparece — evita submit
        # que viraria flash de erro).
        pode_excluir_orfao = False
        if (
            getattr(current_user, 'perfil', None) == 'administrador'
            and sub.frete_id is None
            and sub.fatura_transportadora_id is None
            and sub.status not in ('FATURADO', 'CONFERIDO')
        ):
            from app.carvia.models import (
                CarviaFaturaTransportadoraItem,
                CarviaCustoEntrega,
                CarviaFrete,
                CarviaContaCorrenteTransportadora,
                CarviaConciliacao,
            )
            tem_vinculos = (
                db.session.query(CarviaFaturaTransportadoraItem.id)
                    .filter_by(subcontrato_id=sub.id).first() is not None
                or db.session.query(CarviaCustoEntrega.id)
                    .filter_by(subcontrato_id=sub.id).first() is not None
                or db.session.query(CarviaFrete.id)
                    .filter_by(subcontrato_id=sub.id).first() is not None
                or db.session.query(CarviaConciliacao.id)
                    .filter_by(tipo_documento='subcontrato', documento_id=sub.id)
                    .first() is not None
                # Phase 14 (2026-04-14): CC.subcontrato_id removido do modelo.
                # Registros CC agora vinculam por frete_id (Phase 5+).
                # Guard removido — nenhum novo CC aponta para sub por sub_id.
            )
            pode_excluir_orfao = not tem_vinculos

        return render_template(
            'carvia/subcontratos/detalhe.html',
            sub=sub,
            operacao=operacao,
            nfs=nfs,
            fatura_cliente=fatura_cliente,
            operacoes_disponiveis=operacoes_disponiveis,
            custos_entrega=custos_entrega,
            ctes_complementares=ctes_complementares,
            pode_excluir_orfao=pode_excluir_orfao,
            despesas_extras=despesas_extras,
            valor_conciliado_sub=valor_conciliado_sub,
            fatura_transportadora=fatura_transportadora,
        )

    @bp.route('/subcontratos/<int:sub_id>/vincular-operacao', methods=['POST']) # type: ignore
    @login_required
    def vincular_operacao_subcontrato(sub_id): # type: ignore
        """Re-vincula subcontrato a outra operacao (CTe CarVia)"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        sub = db.session.get(CarviaSubcontrato, sub_id)
        if not sub:
            flash('CTe Subcontrato nao encontrado.', 'warning')
            return redirect(url_for('carvia.listar_subcontratos'))

        if sub.status in ('FATURADO', 'CANCELADO', 'CONFERIDO'):
            flash(
                f'Subcontrato com status {sub.status} nao pode ser re-vinculado.',
                'warning',
            )
            return redirect(url_for('carvia.detalhe_subcontrato', sub_id=sub_id))

        nova_operacao_id = request.form.get('operacao_id', type=int)
        if not nova_operacao_id:
            flash('Selecione um CTe CarVia.', 'warning')
            return redirect(url_for('carvia.detalhe_subcontrato', sub_id=sub_id))

        nova_operacao = db.session.get(CarviaOperacao, nova_operacao_id)
        if not nova_operacao:
            flash('CTe CarVia nao encontrado.', 'warning')
            return redirect(url_for('carvia.detalhe_subcontrato', sub_id=sub_id))

        if nova_operacao.status == 'CANCELADO':
            flash('CTe CarVia cancelado nao aceita subcontratos.', 'warning')
            return redirect(url_for('carvia.detalhe_subcontrato', sub_id=sub_id))

        try:
            operacao_anterior_id = sub.operacao_id

            # GAP-15: Se sub era CONFIRMADO, downgrade para COTADO (cotacao mudou)
            if sub.status == 'CONFIRMADO':
                sub.status = 'COTADO'
                logger.info(
                    f"Subcontrato #{sub_id}: downgrade CONFIRMADO -> COTADO "
                    f"(re-vinculado a operacao #{nova_operacao_id})"
                )

            sub.operacao_id = nova_operacao_id

            # Recotar com base na nova operacao
            from app.carvia.services.pricing.cotacao_service import CotacaoService
            cotacao = CotacaoService().cotar_subcontrato(
                operacao_id=nova_operacao_id,
                transportadora_id=sub.transportadora_id,
            )
            if cotacao.get('sucesso'):
                sub.valor_cotado = cotacao['valor_cotado']
                sub.tabela_frete_id = cotacao.get('tabela_frete_id')

            # GAP-15: Verificar se operacao anterior precisa downgrade (GAP-03 composto)
            if operacao_anterior_id:
                operacao_anterior = db.session.get(CarviaOperacao, operacao_anterior_id)
                if operacao_anterior and operacao_anterior.status not in ('FATURADO', 'CANCELADO'):
                    subs_ativos = operacao_anterior.subcontratos.filter(
                        CarviaSubcontrato.status != 'CANCELADO'
                    ).all()
                    if not subs_ativos:
                        operacao_anterior.status = 'RASCUNHO'
                        logger.info(
                            f"Operacao #{operacao_anterior_id}: downgrade para RASCUNHO "
                            f"(sub #{sub_id} re-vinculado, sem subs restantes)"
                        )
                    elif operacao_anterior.status == 'CONFIRMADO':
                        todos_confirmados = all(
                            s.status == 'CONFIRMADO' for s in subs_ativos
                        )
                        if not todos_confirmados:
                            operacao_anterior.status = 'COTADO'
                            logger.info(
                                f"Operacao #{operacao_anterior_id}: downgrade para COTADO "
                                f"(nem todos subs confirmados apos re-vinculacao)"
                            )

            db.session.commit()

            msg = (
                f'Subcontrato re-vinculado: '
                f'CTe CarVia #{operacao_anterior_id} -> #{nova_operacao_id}.'
            )
            if cotacao.get('sucesso'):
                msg += f' Nova cotacao: R$ {cotacao["valor_cotado"]:.2f}'
            flash(msg, 'success')

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao re-vincular subcontrato: {e}")
            flash(f'Erro: {e}', 'danger')

        return redirect(url_for('carvia.detalhe_subcontrato', sub_id=sub_id))

    # ==================== COTAR SUBCONTRATO ====================

    @bp.route('/subcontratos/<int:sub_id>/cotar', methods=['POST']) # type: ignore
    @login_required
    def cotar_subcontrato(sub_id): # type: ignore
        """Aplica cotacao ao subcontrato (state-mutating: PENDENTE -> COTADO)."""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        sub = db.session.get(CarviaSubcontrato, sub_id)
        if not sub:
            flash('CTe Subcontrato nao encontrado.', 'warning')
            return redirect(url_for('carvia.listar_subcontratos'))

        if not sub.transportadora_id:
            flash('Subcontrato sem transportadora — impossivel cotar.', 'warning')
            return redirect(url_for('carvia.detalhe_subcontrato', sub_id=sub_id))

        try:
            from app.carvia.services.pricing.cotacao_service import CotacaoService
            cotacao = CotacaoService().cotar_subcontrato(
                operacao_id=sub.operacao_id,
                transportadora_id=sub.transportadora_id,
            )

            if cotacao.get('sucesso'):
                sub.valor_cotado = cotacao['valor_cotado']
                sub.tabela_frete_id = cotacao.get('tabela_frete_id')
                if sub.status == 'PENDENTE':
                    sub.status = 'COTADO'
                db.session.commit()
                flash(
                    f'Cotacao aplicada: R$ {cotacao["valor_cotado"]:.2f}'
                    + (f' (Tabela: {cotacao.get("tabela_nome", "")})' if cotacao.get('tabela_nome') else ''),
                    'success',
                )
            else:
                flash(f'Cotacao falhou: {cotacao.get("erro", "desconhecido")}', 'warning')

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao cotar subcontrato #{sub_id}: {e}")
            flash(f'Erro: {e}', 'danger')

        return redirect(url_for('carvia.detalhe_subcontrato', sub_id=sub_id))

    @bp.route('/subcontratos/<int:sub_id>/recotar', methods=['POST']) # type: ignore
    @login_required
    def recotar_subcontrato(sub_id): # type: ignore
        """Recota subcontrato com valor override opcional."""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        sub = db.session.get(CarviaSubcontrato, sub_id)
        if not sub:
            flash('CTe Subcontrato nao encontrado.', 'warning')
            return redirect(url_for('carvia.listar_subcontratos'))

        if sub.status in ('FATURADO', 'CANCELADO', 'CONFERIDO'):
            flash(f'Subcontrato com status {sub.status} nao pode ser recotado.', 'warning')
            return redirect(url_for('carvia.detalhe_subcontrato', sub_id=sub_id))

        try:
            valor_override_raw = request.form.get('valor_override', '').strip()

            if valor_override_raw:
                valor_override = float(valor_override_raw.replace('.', '').replace(',', '.'))
                sub.valor_cotado = valor_override
                msg = f'Valor recotado manualmente: R$ {valor_override:.2f}'
            else:
                from app.carvia.services.pricing.cotacao_service import CotacaoService
                cotacao = CotacaoService().cotar_subcontrato(
                    operacao_id=sub.operacao_id,
                    transportadora_id=sub.transportadora_id,
                )
                if cotacao.get('sucesso'):
                    sub.valor_cotado = cotacao['valor_cotado']
                    sub.tabela_frete_id = cotacao.get('tabela_frete_id')
                    msg = f'Recotacao: R$ {cotacao["valor_cotado"]:.2f}'
                else:
                    flash(f'Recotacao falhou: {cotacao.get("erro", "desconhecido")}', 'warning')
                    return redirect(url_for('carvia.detalhe_subcontrato', sub_id=sub_id))

            if sub.status == 'PENDENTE':
                sub.status = 'COTADO'

            db.session.commit()
            flash(msg, 'success')

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao recotar subcontrato #{sub_id}: {e}")
            flash(f'Erro: {e}', 'danger')

        return redirect(url_for('carvia.detalhe_subcontrato', sub_id=sub_id))

    @bp.route('/api/subcontrato/<int:sub_id>/simular-recotacao') # type: ignore
    @login_required
    def api_simular_recotacao_subcontrato(sub_id): # type: ignore
        """API read-only: simula cotacao para conferencia (card resultado)."""
        if not getattr(current_user, 'sistema_carvia', False):
            return {'sucesso': False, 'erro': 'Acesso negado.'}, 403

        sub = db.session.get(CarviaSubcontrato, sub_id)
        if not sub:
            return {'sucesso': False, 'erro': 'Subcontrato nao encontrado.'}, 404

        if not sub.transportadora_id:
            return {'sucesso': False, 'erro': 'Subcontrato sem transportadora.'}, 400

        try:
            from app.carvia.services.pricing.cotacao_service import CotacaoService
            cotacao = CotacaoService().cotar_subcontrato(
                operacao_id=sub.operacao_id,
                transportadora_id=sub.transportadora_id,
            )

            resultado = {
                'sucesso': cotacao.get('sucesso', False),
                'valor_cotado': cotacao.get('valor_cotado'),
                'tabela_nome': cotacao.get('tabela_nome'),
                'valor_cte': float(sub.cte_valor) if sub.cte_valor else None,
                'valor_cotado_atual': float(sub.valor_cotado) if sub.valor_cotado else None,
                'descritivo': cotacao.get('descritivo', []),
                'erro': cotacao.get('erro'),
            }

            if resultado['valor_cotado'] and resultado['valor_cte']:
                diff = resultado['valor_cte'] - resultado['valor_cotado']
                resultado['divergencia_valor'] = round(diff, 2)
                if resultado['valor_cotado'] > 0:
                    resultado['divergencia_pct'] = round((diff / resultado['valor_cotado']) * 100, 1)

            return resultado

        except Exception as e:
            logger.error(f"Erro ao simular cotacao subcontrato #{sub_id}: {e}")
            return {'sucesso': False, 'erro': str(e)}, 500

    # ==================================================================
    # Registrar pagamento manual do subcontrato — REMOVIDO em 2026-04-14
    # Campos valor_pago/valor_pago_em/valor_pago_por migrados para CarviaFrete.
    # Pagamento agora e feito via editar_frete_carvia (form de edicao do Frete).
    # Ref: docs/superpowers/plans/2026-04-14-carvia-frete-conferencia-migration.md
    # ==================================================================
