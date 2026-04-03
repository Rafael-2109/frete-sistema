"""
Rotas de Faturas CarVia — Cliente + Transportadora
"""

import logging
from datetime import date, datetime

from flask import render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app import db
from app.carvia.models import (
    CarviaFaturaCliente, CarviaFaturaTransportadora,
    CarviaFaturaTransportadoraItem,
    CarviaOperacao, CarviaSubcontrato,
    CarviaCteComplementar, CarviaFrete,
)

logger = logging.getLogger(__name__)


def register_fatura_routes(bp):

    # ===================== FATURAS CLIENTE =====================

    @bp.route('/faturas-cliente') # type: ignore
    @login_required
    def listar_faturas_cliente(): # type: ignore
        """Lista faturas CarVia emitidas ao cliente"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        page = request.args.get('page', 1, type=int)
        status_filtro = request.args.get('status', '')
        busca = request.args.get('busca', '')
        tipo_frete_filtro = request.args.get('tipo_frete', '')
        sort = request.args.get('sort', 'data_emissao')
        direction = request.args.get('direction', 'desc')

        # Subquery: contar operacoes vinculadas a cada fatura
        subq_ops = db.session.query(
            CarviaOperacao.fatura_cliente_id,
            func.count(CarviaOperacao.id).label('qtd_ops')
        ).filter(
            CarviaOperacao.fatura_cliente_id.isnot(None)
        ).group_by(CarviaOperacao.fatura_cliente_id).subquery()

        query = db.session.query(
            CarviaFaturaCliente, subq_ops.c.qtd_ops
        ).outerjoin(
            subq_ops, CarviaFaturaCliente.id == subq_ops.c.fatura_cliente_id
        )

        if status_filtro:
            query = query.filter(CarviaFaturaCliente.status == status_filtro)
        if tipo_frete_filtro:
            query = query.filter(CarviaFaturaCliente.tipo_frete == tipo_frete_filtro)
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
        sort_col = sortable_columns.get(sort, CarviaFaturaCliente.data_emissao)
        if direction == 'asc':
            query = query.order_by(sort_col.asc().nullslast())
        else:
            query = query.order_by(sort_col.desc().nullslast())

        paginacao = query.paginate(page=page, per_page=25, error_out=False)

        today = date.today()

        return render_template(
            'carvia/faturas_cliente/listar.html',
            faturas=paginacao.items,
            paginacao=paginacao,
            status_filtro=status_filtro,
            tipo_frete_filtro=tipo_frete_filtro,
            busca=busca,
            sort=sort,
            direction=direction,
            today=today,
        )

    @bp.route('/faturas-cliente/nova', methods=['GET', 'POST']) # type: ignore
    @login_required
    def nova_fatura_cliente(): # type: ignore
        """Cria nova fatura para o cliente — agrupa operacoes confirmadas"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        if request.method == 'POST':
            cnpj_cliente = request.form.get('cnpj_cliente', '').strip()
            data_emissao_str = request.form.get('data_emissao', '')
            vencimento_str = request.form.get('vencimento', '')
            observacoes = request.form.get('observacoes', '')
            operacao_ids = request.form.getlist('operacao_ids', type=int)
            cte_comp_ids = request.form.getlist('cte_comp_ids', type=int)
            pagador_cnpj = request.form.get('pagador_cnpj', '').strip()
            pagador_nome = request.form.get('pagador_nome', '').strip()

            if not cnpj_cliente or not data_emissao_str:
                flash('CNPJ e data de emissao sao obrigatorios.', 'warning')
                return redirect(url_for('carvia.nova_fatura_cliente'))

            if not operacao_ids and not cte_comp_ids:
                flash('Selecione ao menos uma operacao ou CTe complementar.', 'warning')
                return redirect(url_for('carvia.nova_fatura_cliente'))

            try:
                data_emissao = date.fromisoformat(data_emissao_str)
                vencimento = date.fromisoformat(vencimento_str) if vencimento_str else None

                # Buscar operacoes selecionadas
                # GAP-29: FOR UPDATE para evitar faturamento duplo concorrente
                operacoes = []
                if operacao_ids:
                    operacoes = db.session.query(CarviaOperacao).filter(
                        CarviaOperacao.id.in_(operacao_ids),
                        CarviaOperacao.cnpj_cliente == cnpj_cliente,
                        CarviaOperacao.status.in_(['RASCUNHO', 'COTADO', 'CONFIRMADO']),
                        CarviaOperacao.fatura_cliente_id.is_(None),
                    ).with_for_update().all()

                # Buscar CTe Complementares selecionados
                ctes_comp = []
                if cte_comp_ids:
                    ctes_comp = db.session.query(CarviaCteComplementar).filter(
                        CarviaCteComplementar.id.in_(cte_comp_ids),
                        CarviaCteComplementar.cnpj_cliente == cnpj_cliente,
                        CarviaCteComplementar.status.in_(['RASCUNHO', 'EMITIDO']),
                        CarviaCteComplementar.fatura_cliente_id.is_(None),
                    ).with_for_update().all()

                if not operacoes and not ctes_comp:
                    flash('Nenhuma operacao ou CTe complementar valido selecionado.', 'warning')
                    return redirect(url_for('carvia.nova_fatura_cliente'))

                # Calcular valor total (operacoes + CTe complementares)
                valor_total = sum(
                    float(op.cte_valor or 0) for op in operacoes
                ) + sum(
                    float(comp.cte_valor or 0) for comp in ctes_comp
                )

                # GAP-24: Validar valor_total > 0
                if valor_total <= 0:
                    flash('Valor total da fatura deve ser maior que zero. Verifique os valores das operacoes.', 'warning')
                    return redirect(url_for('carvia.nova_fatura_cliente'))

                # Gerar numero automaticamente
                numero_fatura = CarviaFaturaCliente.gerar_numero_fatura()

                # Pagador: usar selecionado ou default (remetente)
                fatura_cnpj = pagador_cnpj if pagador_cnpj else cnpj_cliente
                fatura_nome = pagador_nome if pagador_cnpj else (
                    operacoes[0].nome_cliente if operacoes else
                    ctes_comp[0].nome_cliente if ctes_comp else ''
                )

                fatura = CarviaFaturaCliente(
                    cnpj_cliente=fatura_cnpj,
                    nome_cliente=fatura_nome,
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

                # Vincular operacoes + propagar para CarviaFrete
                for op in operacoes:
                    op.fatura_cliente_id = fatura.id
                    op.status = 'FATURADO'
                    # Retroativo: vincular CarviaFrete pela operacao_id
                    CarviaFrete.query.filter_by(operacao_id=op.id).update(
                        {'fatura_cliente_id': fatura.id}
                    )

                # Vincular CTe Complementares
                for comp in ctes_comp:
                    comp.fatura_cliente_id = fatura.id
                    comp.status = 'FATURADO'

                # Gerar itens de detalhe a partir das operacoes
                if operacoes:
                    from app.carvia.services.documentos.linking_service import LinkingService
                    linker = LinkingService()
                    linker.criar_itens_fatura_cliente_from_operacoes(fatura.id)
                    # Expandir: criar itens para NFs do CTe não presentes
                    linker.expandir_itens_com_nfs_do_cte(fatura.id)

                db.session.commit()

                partes_msg = []
                if operacoes:
                    partes_msg.append(f'{len(operacoes)} operacoes')
                if ctes_comp:
                    partes_msg.append(f'{len(ctes_comp)} CTe complementares')
                flash(
                    f'Fatura {numero_fatura} criada. '
                    f'{" + ".join(partes_msg)} vinculados. '
                    f'Valor total: R$ {valor_total:.2f}',
                    'success'
                )
                return redirect(url_for('carvia.detalhe_fatura_cliente', fatura_id=fatura.id))

            except Exception as e:
                db.session.rollback()
                logger.error(f"Erro ao criar fatura cliente: {e}")
                flash(f'Erro: {e}', 'danger')

        # GET — listar clientes com operacoes confirmadas disponiveis
        clientes_ops = db.session.query(
            CarviaOperacao.cnpj_cliente,
            CarviaOperacao.nome_cliente,
            db.func.count(CarviaOperacao.id).label('qtd_operacoes'),
            db.func.sum(CarviaOperacao.cte_valor).label('valor_total'),
        ).filter(
            CarviaOperacao.status.in_(['RASCUNHO', 'COTADO', 'CONFIRMADO']),
            CarviaOperacao.fatura_cliente_id.is_(None),
        ).group_by(
            CarviaOperacao.cnpj_cliente,
            CarviaOperacao.nome_cliente,
        ).all()

        # CTe Complementares disponiveis agrupados por cliente
        clientes_comp = db.session.query(
            CarviaCteComplementar.cnpj_cliente,
            CarviaCteComplementar.nome_cliente,
            db.func.count(CarviaCteComplementar.id).label('qtd_ctes_comp'),
            db.func.sum(CarviaCteComplementar.cte_valor).label('valor_total_comp'),
        ).filter(
            CarviaCteComplementar.status.in_(['RASCUNHO', 'EMITIDO']),
            CarviaCteComplementar.fatura_cliente_id.is_(None),
        ).group_by(
            CarviaCteComplementar.cnpj_cliente,
            CarviaCteComplementar.nome_cliente,
        ).all()

        # Merge: combinar operacoes + CTe complementares por CNPJ
        clientes_dict = {}
        for c in clientes_ops:
            clientes_dict[c.cnpj_cliente] = {
                'cnpj_cliente': c.cnpj_cliente,
                'nome_cliente': c.nome_cliente,
                'qtd_operacoes': c.qtd_operacoes,
                'qtd_ctes_comp': 0,
                'valor_total': float(c.valor_total or 0),
            }
        for c in clientes_comp:
            if c.cnpj_cliente in clientes_dict:
                clientes_dict[c.cnpj_cliente]['qtd_ctes_comp'] = c.qtd_ctes_comp
                clientes_dict[c.cnpj_cliente]['valor_total'] += float(c.valor_total_comp or 0)
            else:
                clientes_dict[c.cnpj_cliente] = {
                    'cnpj_cliente': c.cnpj_cliente,
                    'nome_cliente': c.nome_cliente,
                    'qtd_operacoes': 0,
                    'qtd_ctes_comp': c.qtd_ctes_comp,
                    'valor_total': float(c.valor_total_comp or 0),
                }

        # Converter para lista de objetos simples (SimpleNamespace para compatibilidade com template)
        from types import SimpleNamespace
        clientes = [SimpleNamespace(**v) for v in clientes_dict.values()]

        # Se cnpj selecionado, buscar operacoes e CTe complementares
        cnpj_selecionado = request.args.get('cnpj', '')
        operacoes_disponiveis = []
        ctes_comp_disponiveis = []
        if cnpj_selecionado:
            operacoes_disponiveis = db.session.query(CarviaOperacao).filter(
                CarviaOperacao.cnpj_cliente == cnpj_selecionado,
                CarviaOperacao.status.in_(['RASCUNHO', 'COTADO', 'CONFIRMADO']),
                CarviaOperacao.fatura_cliente_id.is_(None),
            ).order_by(CarviaOperacao.cte_data_emissao.desc().nullslast()).all()

            ctes_comp_disponiveis = db.session.query(CarviaCteComplementar).filter(
                CarviaCteComplementar.cnpj_cliente == cnpj_selecionado,
                CarviaCteComplementar.status.in_(['RASCUNHO', 'EMITIDO']),
                CarviaCteComplementar.fatura_cliente_id.is_(None),
            ).order_by(CarviaCteComplementar.cte_data_emissao.desc().nullslast()).all()

        # Extrair entidades pagador para selecao (step 2)
        entidades_pagador = []
        if cnpj_selecionado and operacoes_disponiveis:
            from app.carvia.models import CarviaOperacaoNf, CarviaNf

            # Remetente (= cnpj_cliente das operacoes, consistente por grupo)
            rem_nome = operacoes_disponiveis[0].nome_cliente or ''
            entidades_pagador.append({
                'cnpj': cnpj_selecionado,
                'nome': rem_nome,
                'papel': 'Remetente',
            })

            # Destinatarios (de NFs vinculadas, distintos, excluindo remetente)
            op_ids_disp = [op.id for op in operacoes_disponiveis]
            dest_rows = db.session.query(
                CarviaNf.cnpj_destinatario,
                CarviaNf.nome_destinatario
            ).join(
                CarviaOperacaoNf, CarviaNf.id == CarviaOperacaoNf.nf_id
            ).filter(
                CarviaOperacaoNf.operacao_id.in_(op_ids_disp),
                CarviaNf.cnpj_destinatario.isnot(None),
                CarviaNf.cnpj_destinatario != cnpj_selecionado,
            ).distinct().all()

            seen_cnpjs = {cnpj_selecionado}
            for cnpj_dest, nome_dest in dest_rows:
                if cnpj_dest and cnpj_dest not in seen_cnpjs:
                    entidades_pagador.append({
                        'cnpj': cnpj_dest,
                        'nome': nome_dest or '',
                        'papel': 'Destinatario',
                    })
                    seen_cnpjs.add(cnpj_dest)

        return render_template(
            'carvia/faturas_cliente/nova.html',
            clientes=clientes,
            cnpj_selecionado=cnpj_selecionado,
            operacoes_disponiveis=operacoes_disponiveis,
            ctes_comp_disponiveis=ctes_comp_disponiveis,
            entidades_pagador=entidades_pagador,
        )

    @bp.route('/faturas-cliente/<int:fatura_id>') # type: ignore
    @login_required
    def detalhe_fatura_cliente(fatura_id): # type: ignore
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
        ).order_by(CarviaOperacao.cte_data_emissao.desc().nullslast()).all()

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

        # CTe Complementares vinculados a esta fatura
        ctes_complementares = CarviaCteComplementar.query.filter_by(
            fatura_cliente_id=fatura_id
        ).all()

        # Condicoes comerciais via lookup fretes (sem colunas na fatura)
        condicoes_comerciais = None
        if op_ids:
            from app.carvia.models import CarviaFrete
            frete_com_cond = CarviaFrete.query.filter(
                CarviaFrete.operacao_id.in_(op_ids),
                db.or_(
                    CarviaFrete.condicao_pagamento.isnot(None),
                    CarviaFrete.responsavel_frete.isnot(None),
                ),
            ).first()
            if frete_com_cond:
                condicoes_comerciais = frete_com_cond

        # Entidades pagador para modal alterar-pagador
        entidades_pagador = []
        if operacoes:
            # Remetente
            rem_cnpj = operacoes[0].cnpj_cliente or ''
            rem_nome = operacoes[0].nome_cliente or ''
            entidades_pagador.append({
                'cnpj': rem_cnpj,
                'nome': rem_nome,
                'papel': 'Remetente',
                'atual': (rem_cnpj == fatura.cnpj_cliente),
            })

            # Destinatarios (das NFs ja carregadas)
            seen_cnpjs = {rem_cnpj} if rem_cnpj else set()
            for nf in nfs:
                cnpj_dest = nf.cnpj_destinatario
                if cnpj_dest and cnpj_dest not in seen_cnpjs:
                    entidades_pagador.append({
                        'cnpj': cnpj_dest,
                        'nome': nf.nome_destinatario or '',
                        'papel': 'Destinatario',
                        'atual': (cnpj_dest == fatura.cnpj_cliente),
                    })
                    seen_cnpjs.add(cnpj_dest)

            # Se pagador atual nao e nenhum dos acima (caso import PDF)
            if not any(e['atual'] for e in entidades_pagador):
                entidades_pagador.insert(0, {
                    'cnpj': fatura.cnpj_cliente or '',
                    'nome': fatura.nome_cliente or '',
                    'papel': 'Pagador Atual',
                    'atual': True,
                })

        return render_template(
            'carvia/faturas_cliente/detalhe.html',
            fatura=fatura,
            operacoes=operacoes,
            itens=itens,
            nfs=nfs,
            subcontratos=subcontratos,
            faturas_transportadora=faturas_transportadora,
            ctes_complementares=ctes_complementares,
            condicoes_comerciais=condicoes_comerciais,
            entidades_pagador=entidades_pagador,
        )

    @bp.route('/faturas-cliente/<int:fatura_id>/editar-valor', methods=['POST']) # type: ignore
    @login_required
    def editar_valor_fatura_cliente(fatura_id): # type: ignore
        """Edita valor total de uma fatura cliente (admin only)"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        if getattr(current_user, 'perfil', '') != 'administrador':
            flash('Apenas administradores podem editar o valor da fatura.', 'danger')
            return redirect(url_for('carvia.detalhe_fatura_cliente', fatura_id=fatura_id))

        fatura = db.session.get(CarviaFaturaCliente, fatura_id)
        if not fatura:
            flash('Fatura nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_faturas_cliente'))

        if fatura.status in ('PAGA', 'CANCELADA'):
            flash(f'Nao e possivel editar valor de fatura {fatura.status.lower()}.', 'warning')
            return redirect(url_for('carvia.detalhe_fatura_cliente', fatura_id=fatura_id))

        valor_raw = request.form.get('valor_total', '').strip()
        if not valor_raw:
            flash('Informe o valor.', 'warning')
            return redirect(url_for('carvia.detalhe_fatura_cliente', fatura_id=fatura_id))

        try:
            valor_total = float(valor_raw.replace('.', '').replace(',', '.'))
        except (ValueError, TypeError):
            flash('Valor invalido.', 'danger')
            return redirect(url_for('carvia.detalhe_fatura_cliente', fatura_id=fatura_id))

        try:
            valor_anterior = float(fatura.valor_total or 0)
            fatura.valor_total = valor_total
            db.session.commit()

            logger.info(
                f"Fatura cliente #{fatura_id}: valor alterado "
                f"R$ {valor_anterior:.2f} -> R$ {valor_total:.2f} "
                f"por {current_user.email}"
            )
            flash(f'Valor atualizado: R$ {valor_total:.2f}', 'success')
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao editar valor fatura cliente {fatura_id}: {e}")
            flash(f'Erro: {e}', 'danger')

        return redirect(url_for('carvia.detalhe_fatura_cliente', fatura_id=fatura_id))

    @bp.route('/faturas-cliente/<int:fatura_id>/editar-vencimento', methods=['POST']) # type: ignore
    @login_required
    def editar_vencimento_fatura_cliente(fatura_id): # type: ignore
        """Edita vencimento de uma fatura cliente"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        fatura = db.session.get(CarviaFaturaCliente, fatura_id)
        if not fatura:
            flash('Fatura nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_faturas_cliente'))

        # GAP-35: Bloquear edicao de vencimento em fatura PAGA ou CANCELADA
        if fatura.status in ('PAGA', 'CANCELADA'):
            flash(f'Nao e possivel editar vencimento de fatura {fatura.status.lower()}.', 'warning')
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

    @bp.route('/faturas-cliente/<int:fatura_id>/alterar-pagador', methods=['POST']) # type: ignore
    @login_required
    def alterar_pagador_fatura_cliente(fatura_id): # type: ignore
        """Altera o pagador (cnpj_cliente/nome_cliente) de uma fatura cliente."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        fatura = db.session.get(CarviaFaturaCliente, fatura_id)
        if not fatura:
            return jsonify({'erro': 'Fatura nao encontrada'}), 404

        if fatura.status in ('PAGA', 'CANCELADA'):
            return jsonify({
                'erro': f'Nao e possivel alterar pagador de fatura {fatura.status}'
            }), 400

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados nao fornecidos'}), 400

        novo_cnpj = data.get('cnpj', '').strip()
        novo_nome = data.get('nome', '').strip()

        if not novo_cnpj:
            return jsonify({'erro': 'CNPJ do pagador e obrigatorio'}), 400

        try:
            from sqlalchemy.exc import IntegrityError

            antigo_cnpj = fatura.cnpj_cliente
            fatura.cnpj_cliente = novo_cnpj
            fatura.nome_cliente = novo_nome or fatura.nome_cliente

            db.session.commit()

            logger.info(
                "Pagador fatura %s alterado: %s -> %s por %s",
                fatura.numero_fatura, antigo_cnpj, novo_cnpj,
                current_user.email
            )

            return jsonify({
                'sucesso': True,
                'cnpj_cliente': fatura.cnpj_cliente,
                'nome_cliente': fatura.nome_cliente,
            })

        except IntegrityError:
            db.session.rollback()
            return jsonify({
                'erro': 'Ja existe fatura com este numero para o novo pagador'
            }), 400
        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao alterar pagador fatura %s: %s", fatura_id, e)
            return jsonify({'erro': str(e)}), 500

    @bp.route('/faturas-cliente/<int:fatura_id>/status', methods=['POST']) # type: ignore
    @login_required
    def atualizar_status_fatura_cliente(fatura_id): # type: ignore
        """Atualiza status de uma fatura cliente"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        fatura = db.session.get(CarviaFaturaCliente, fatura_id)
        if not fatura:
            flash('Fatura nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_faturas_cliente'))

        novo_status = request.form.get('status')
        # GAP-01: EMITIDA removido do fluxo (status morto, nunca setado automaticamente)
        if novo_status not in ('PENDENTE', 'PAGA', 'CANCELADA'):
            flash('Status invalido.', 'warning')
            return redirect(url_for('carvia.detalhe_fatura_cliente', fatura_id=fatura_id))

        try:
            # GAP-05: Se revertendo de PAGA para outro status, remover movimentacao financeira
            if fatura.status == 'PAGA' and novo_status != 'PAGA':
                from app.carvia.routes.fluxo_caixa_routes import _remover_movimentacao
                _remover_movimentacao('fatura_cliente', fatura_id)
                fatura.pago_por = None
                fatura.pago_em = None
                logger.info(
                    f"Fatura cliente #{fatura_id}: movimentacao removida ao reverter "
                    f"PAGA -> {novo_status} por {current_user.email}"
                )

            fatura.status = novo_status

            # Ao marcar como PAGA: registrar pago_em/pago_por e criar movimentacao
            if novo_status == 'PAGA':
                data_pagamento_str = request.form.get('data_pagamento', '').strip()
                if not data_pagamento_str:
                    flash('Data de pagamento e obrigatoria para marcar como PAGA.', 'warning')
                    return redirect(url_for('carvia.detalhe_fatura_cliente', fatura_id=fatura_id))
                try:
                    data_pagamento = date.fromisoformat(data_pagamento_str)
                except ValueError:
                    flash('Data de pagamento invalida.', 'warning')
                    return redirect(url_for('carvia.detalhe_fatura_cliente', fatura_id=fatura_id))

                fatura.pago_em = datetime.combine(data_pagamento, datetime.min.time())
                fatura.pago_por = current_user.email

                # Criar movimentacao financeira na conta
                from app.carvia.routes.fluxo_caixa_routes import (
                    _criar_movimentacao, _gerar_descricao,
                )
                descricao = _gerar_descricao('fatura_cliente', fatura)
                _criar_movimentacao(
                    'fatura_cliente', fatura_id,
                    float(fatura.valor_total or 0), descricao, current_user.email,
                )

            db.session.commit()
            flash(f'Status atualizado para {novo_status}.', 'success')
        except IntegrityError:
            db.session.rollback()
            logger.warning(f"Movimentacao duplicada fatura cliente #{fatura_id}")
            flash('Este lancamento ja foi processado.', 'warning')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro: {e}', 'danger')

        return redirect(url_for('carvia.detalhe_fatura_cliente', fatura_id=fatura_id))

    # ===================== CRIAR FATURA RAPIDA =====================

    @bp.route('/faturas-cliente/criar-rapida', methods=['POST']) # type: ignore
    @login_required
    def criar_fatura_rapida(): # type: ignore
        """Cria fatura cliente a partir de uma unica operacao (atalho do detalhe)"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        operacao_id = request.form.get('operacao_id', type=int)
        data_emissao_str = request.form.get('data_emissao', '')
        vencimento_str = request.form.get('vencimento', '')
        observacoes = request.form.get('observacoes', '')

        if not operacao_id or not data_emissao_str:
            flash('Operacao e data de emissao sao obrigatorios.', 'warning')
            return redirect(request.referrer or url_for('carvia.listar_operacoes'))

        try:
            data_emissao = date.fromisoformat(data_emissao_str)
            vencimento = date.fromisoformat(vencimento_str) if vencimento_str else None

            # Buscar operacao com lock
            operacao = db.session.query(CarviaOperacao).filter(
                CarviaOperacao.id == operacao_id,
                CarviaOperacao.status.in_(['RASCUNHO', 'COTADO', 'CONFIRMADO']),
                CarviaOperacao.fatura_cliente_id.is_(None),
            ).with_for_update().first()

            if not operacao:
                flash('Operacao nao encontrada ou ja faturada.', 'warning')
                return redirect(url_for('carvia.listar_operacoes'))

            valor_total = float(operacao.cte_valor or 0)
            if valor_total <= 0:
                flash('Valor do CTe deve ser maior que zero.', 'warning')
                return redirect(url_for('carvia.detalhe_operacao', operacao_id=operacao_id))

            numero_fatura = CarviaFaturaCliente.gerar_numero_fatura()

            fatura = CarviaFaturaCliente(
                cnpj_cliente=operacao.cnpj_cliente,
                nome_cliente=operacao.nome_cliente,
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

            # Vincular operacao + propagar para CarviaFrete
            operacao.fatura_cliente_id = fatura.id
            operacao.status = 'FATURADO'
            CarviaFrete.query.filter_by(operacao_id=operacao.id).update(
                {'fatura_cliente_id': fatura.id}
            )

            # Gerar itens de detalhe
            from app.carvia.services.documentos.linking_service import LinkingService
            linker = LinkingService()
            linker.criar_itens_fatura_cliente_from_operacoes(fatura.id)
            # Expandir: criar itens para NFs do CTe não presentes
            linker.expandir_itens_com_nfs_do_cte(fatura.id)

            db.session.commit()

            flash(
                f'Fatura {numero_fatura} criada. Valor: R$ {valor_total:.2f}',
                'success'
            )
            return redirect(url_for('carvia.detalhe_fatura_cliente', fatura_id=fatura.id))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao criar fatura rapida: {e}")
            flash(f'Erro: {e}', 'danger')
            return redirect(url_for('carvia.detalhe_operacao', operacao_id=operacao_id))

    # ===================== FATURAS TRANSPORTADORA =====================

    @bp.route('/faturas-transportadora') # type: ignore
    @login_required
    def listar_faturas_transportadora(): # type: ignore
        """Lista faturas recebidas dos subcontratados"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        from app.carvia.forms import FiltroFaturasTransportadoraForm
        from app.transportadoras.models import Transportadora

        form = FiltroFaturasTransportadoraForm(request.args)
        transportadoras = Transportadora.query.filter_by(ativo=True).order_by(Transportadora.razao_social).all()
        form.transportadora_id.choices = [('', 'Todas as transportadoras')] + [
            (str(t.id), t.razao_social) for t in transportadoras
        ]

        sort = request.args.get('sort', 'data_emissao')
        direction = request.args.get('direction', 'desc')

        # Subquery: contar e somar valor dos subcontratos por fatura
        subq_subs = db.session.query(
            CarviaSubcontrato.fatura_transportadora_id,
            func.count(CarviaSubcontrato.id).label('qtd_subs'),
            func.sum(func.coalesce(CarviaSubcontrato.valor_acertado, CarviaSubcontrato.valor_cotado, 0)).label('valor_subs'),
        ).filter(
            CarviaSubcontrato.fatura_transportadora_id.isnot(None)
        ).group_by(CarviaSubcontrato.fatura_transportadora_id).subquery()

        query = db.session.query(
            CarviaFaturaTransportadora, subq_subs.c.qtd_subs, subq_subs.c.valor_subs
        ).outerjoin(
            subq_subs, CarviaFaturaTransportadora.id == subq_subs.c.fatura_transportadora_id
        )

        # Filtros via WTForms
        if form.numero_fatura.data:
            query = query.filter(
                CarviaFaturaTransportadora.numero_fatura.ilike(f'%{form.numero_fatura.data}%')
            )

        if form.transportadora_id.data:
            query = query.filter(
                CarviaFaturaTransportadora.transportadora_id == int(form.transportadora_id.data)
            )

        if form.numero_subcontrato.data:
            faturas_com_sub = db.session.query(
                CarviaSubcontrato.fatura_transportadora_id
            ).filter(
                CarviaSubcontrato.cte_numero.ilike(f'%{form.numero_subcontrato.data}%'),
                CarviaSubcontrato.fatura_transportadora_id.isnot(None),
            ).distinct().subquery()
            query = query.filter(CarviaFaturaTransportadora.id.in_(faturas_com_sub))

        if form.status_conferencia.data:
            query = query.filter(
                CarviaFaturaTransportadora.status_conferencia == form.status_conferencia.data
            )

        if form.status_pagamento.data:
            query = query.filter(
                CarviaFaturaTransportadora.status_pagamento == form.status_pagamento.data
            )

        if form.data_emissao_de.data:
            query = query.filter(CarviaFaturaTransportadora.data_emissao >= form.data_emissao_de.data)

        if form.data_emissao_ate.data:
            query = query.filter(CarviaFaturaTransportadora.data_emissao <= form.data_emissao_ate.data)

        if form.data_vencimento_de.data:
            query = query.filter(CarviaFaturaTransportadora.vencimento >= form.data_vencimento_de.data)

        if form.data_vencimento_ate.data:
            query = query.filter(CarviaFaturaTransportadora.vencimento <= form.data_vencimento_ate.data)

        # Ordenacao dinamica
        sortable_columns = {
            'numero_fatura': func.lpad(func.coalesce(CarviaFaturaTransportadora.numero_fatura, ''), 20, '0'),
            'data_emissao': CarviaFaturaTransportadora.data_emissao,
            'vencimento': CarviaFaturaTransportadora.vencimento,
            'valor_total': CarviaFaturaTransportadora.valor_total,
            'status_conferencia': CarviaFaturaTransportadora.status_conferencia,
            'criado_em': CarviaFaturaTransportadora.criado_em,
        }
        sort_col = sortable_columns.get(sort, CarviaFaturaTransportadora.data_emissao)
        if direction == 'asc':
            query = query.order_by(sort_col.asc().nullslast())
        else:
            query = query.order_by(sort_col.desc().nullslast())

        paginacao = query.paginate(page=request.args.get('page', 1, type=int), per_page=20, error_out=False)

        today = date.today()

        return render_template(
            'carvia/faturas_transportadora/listar.html',
            faturas=paginacao.items,
            paginacao=paginacao,
            form=form,
            sort=sort,
            direction=direction,
            today=today,
        )

    @bp.route('/faturas-transportadora/nova', methods=['GET', 'POST']) # type: ignore
    @login_required
    def nova_fatura_transportadora(): # type: ignore
        """Cria nova fatura de transportadora — form simplificado sem subcontratos"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        if request.method == 'POST':
            transportadora_id = request.form.get('transportadora_id', type=int)
            numero_fatura = request.form.get('numero_fatura', '').strip()
            valor_total_str = request.form.get('valor_total', '').strip()
            data_emissao_str = request.form.get('data_emissao', '')
            vencimento_str = request.form.get('vencimento', '')
            observacoes = request.form.get('observacoes', '')

            # Validacoes
            if not transportadora_id or not numero_fatura or not data_emissao_str or not vencimento_str:
                flash('Transportadora, numero da fatura, valor, data de emissao e vencimento sao obrigatorios.', 'warning')
                return redirect(url_for('carvia.nova_fatura_transportadora'))

            try:
                valor_total = float(valor_total_str.replace(',', '.')) if valor_total_str else 0
            except (ValueError, TypeError):
                flash('Valor total invalido.', 'warning')
                return redirect(url_for('carvia.nova_fatura_transportadora'))

            if valor_total <= 0:
                flash('Valor total deve ser maior que zero.', 'warning')
                return redirect(url_for('carvia.nova_fatura_transportadora'))

            # Validar transportadora existe
            from app.transportadoras.models import Transportadora
            transportadora = db.session.get(Transportadora, transportadora_id)
            if not transportadora:
                flash('Transportadora nao encontrada.', 'warning')
                return redirect(url_for('carvia.nova_fatura_transportadora'))

            try:
                data_emissao = date.fromisoformat(data_emissao_str)
                vencimento = date.fromisoformat(vencimento_str)

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

                # Upload de arquivo PDF (opcional)
                arquivo = request.files.get('arquivo_fatura')
                if arquivo and arquivo.filename:
                    from app.utils.file_storage import get_file_storage
                    storage = get_file_storage()
                    saved_path = storage.save_file(
                        arquivo, 'carvia/faturas_transportadora',
                        allowed_extensions=['pdf'],
                    )
                    if saved_path:
                        fatura.arquivo_pdf_path = saved_path
                        fatura.arquivo_nome_original = arquivo.filename

                db.session.commit()

                flash(
                    f'Fatura {numero_fatura} criada com sucesso. '
                    f'Valor: R$ {valor_total:.2f}. '
                    f'Anexe subcontratos na tela de detalhe.',
                    'success'
                )
                return redirect(url_for('carvia.detalhe_fatura_transportadora', fatura_id=fatura.id))

            except IntegrityError:
                db.session.rollback()
                flash(
                    'Erro de duplicidade ao criar fatura. Tente novamente.',
                    'warning'
                )
            except Exception as e:
                db.session.rollback()
                logger.error(f"Erro ao criar fatura transportadora: {e}")
                flash(f'Erro: {e}', 'danger')

        # GET — form simplificado
        data_hoje = date.today().isoformat()

        return render_template(
            'carvia/faturas_transportadora/nova.html',
            data_hoje=data_hoje,
        )

    # ===================== ANEXAR / DESANEXAR SUBCONTRATOS =====================

    @bp.route('/faturas-transportadora/<int:fatura_id>/anexar-subcontratos', methods=['POST']) # type: ignore
    @login_required
    def anexar_subcontratos_fatura_transportadora(fatura_id): # type: ignore
        """Anexa subcontratos confirmados a uma fatura de transportadora existente"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'sucesso': False, 'erro': 'Acesso negado'}), 403

        fatura = db.session.get(CarviaFaturaTransportadora, fatura_id)
        if not fatura:
            return jsonify({'sucesso': False, 'erro': 'Fatura nao encontrada'}), 404

        if fatura.status_conferencia == 'CONFERIDO':
            return jsonify({
                'sucesso': False,
                'erro': 'Nao e possivel anexar subcontratos a fatura ja conferida.'
            }), 400

        data = request.get_json(silent=True) or {}
        subcontrato_ids = data.get('subcontrato_ids', [])
        if not subcontrato_ids:
            return jsonify({'sucesso': False, 'erro': 'Nenhum subcontrato selecionado.'}), 400

        try:
            # FOR UPDATE para evitar vinculacao concorrente
            # lazyload('*') evita LEFT OUTER JOINs que conflitam com FOR UPDATE no PostgreSQL
            from sqlalchemy.orm import lazyload
            subcontratos = db.session.query(CarviaSubcontrato).options(
                lazyload('*')
            ).filter(
                CarviaSubcontrato.id.in_(subcontrato_ids),
                CarviaSubcontrato.transportadora_id == fatura.transportadora_id,
                CarviaSubcontrato.status.in_(['COTADO', 'CONFIRMADO']),
                CarviaSubcontrato.fatura_transportadora_id.is_(None),
            ).with_for_update().all()

            if not subcontratos:
                return jsonify({
                    'sucesso': False,
                    'erro': 'Nenhum subcontrato valido para anexar. '
                            'Verifique se estao COTADOS ou CONFIRMADOS e sem fatura vinculada.'
                }), 400

            # Vincular subcontratos + propagar para CarviaFrete
            for sub in subcontratos:
                sub.fatura_transportadora_id = fatura.id
                sub.status = 'FATURADO'
                # Retroativo: vincular CarviaFrete via frete_id (novo) ou subcontrato_id (deprecated)
                if sub.frete_id:
                    frete_vinc = db.session.get(CarviaFrete, sub.frete_id)
                    if frete_vinc:
                        frete_vinc.fatura_transportadora_id = fatura.id
                else:
                    CarviaFrete.query.filter_by(subcontrato_id=sub.id).update(
                        {'fatura_transportadora_id': fatura.id}
                    )

            # Gerar itens de detalhe incrementalmente
            from app.carvia.services.documentos.linking_service import LinkingService
            LinkingService().criar_itens_fatura_transportadora_incremental(
                fatura.id, [sub.id for sub in subcontratos]
            )

            db.session.commit()

            # Calcular soma total de TODOS os subcontratos vinculados (apos commit)
            todos_subs = db.session.query(CarviaSubcontrato).filter(
                CarviaSubcontrato.fatura_transportadora_id == fatura.id,
            ).all()
            soma_total = sum(float(s.valor_final or 0) for s in todos_subs)

            logger.info(
                f"Fatura transportadora #{fatura_id}: {len(subcontratos)} subcontratos "
                f"anexados por {current_user.email}. Soma total: {soma_total:.2f}"
            )

            return jsonify({
                'sucesso': True,
                'qtd_anexados': len(subcontratos),
                'soma_total_subcontratos': round(soma_total, 2),
                'valor_total_fatura': float(fatura.valor_total or 0),
            })

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao anexar subcontratos fatura #{fatura_id}: {e}")
            return jsonify({'sucesso': False, 'erro': str(e)}), 500

    @bp.route('/faturas-transportadora/<int:fatura_id>/desanexar-subcontrato/<int:sub_id>', methods=['POST']) # type: ignore
    @login_required
    def desanexar_subcontrato_fatura_transportadora(fatura_id, sub_id): # type: ignore
        """Desanexa um subcontrato de uma fatura de transportadora"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'sucesso': False, 'erro': 'Acesso negado'}), 403

        fatura = db.session.get(CarviaFaturaTransportadora, fatura_id)
        if not fatura:
            return jsonify({'sucesso': False, 'erro': 'Fatura nao encontrada'}), 404

        if fatura.status_conferencia == 'CONFERIDO':
            return jsonify({
                'sucesso': False,
                'erro': 'Nao e possivel desanexar subcontratos de fatura ja conferida.'
            }), 400

        try:
            sub = db.session.query(CarviaSubcontrato).filter(
                CarviaSubcontrato.id == sub_id,
                CarviaSubcontrato.fatura_transportadora_id == fatura_id,
            ).with_for_update().first()

            if not sub:
                return jsonify({
                    'sucesso': False,
                    'erro': 'Subcontrato nao encontrado nesta fatura.'
                }), 404

            # Reverter subcontrato + limpar CarviaFrete
            sub.fatura_transportadora_id = None
            sub.status = 'CONFIRMADO'
            # Propagar para CarviaFrete via frete_id (novo) ou subcontrato_id (deprecated)
            if sub.frete_id:
                frete_vinc = db.session.get(CarviaFrete, sub.frete_id)
                if frete_vinc:
                    frete_vinc.fatura_transportadora_id = None
            else:
                CarviaFrete.query.filter_by(subcontrato_id=sub.id).update(
                    {'fatura_transportadora_id': None}
                )

            # Remover item de detalhe
            CarviaFaturaTransportadoraItem.query.filter_by(
                fatura_transportadora_id=fatura_id,
                subcontrato_id=sub_id,
            ).delete()

            db.session.commit()

            # Calcular soma restante
            subs_restantes = db.session.query(CarviaSubcontrato).filter(
                CarviaSubcontrato.fatura_transportadora_id == fatura_id,
            ).all()
            soma_restantes = sum(float(s.valor_final or 0) for s in subs_restantes)

            logger.info(
                f"Fatura transportadora #{fatura_id}: subcontrato #{sub_id} "
                f"desanexado por {current_user.email}"
            )

            return jsonify({
                'sucesso': True,
                'soma_valores_restantes': round(soma_restantes, 2),
                'valor_total_fatura': float(fatura.valor_total or 0),
            })

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao desanexar subcontrato #{sub_id} da fatura #{fatura_id}: {e}")
            return jsonify({'sucesso': False, 'erro': str(e)}), 500

    @bp.route('/api/subcontratos-disponiveis/<int:transportadora_id>') # type: ignore
    @login_required
    def api_subcontratos_disponiveis(transportadora_id): # type: ignore
        """Lista subcontratos disponiveis para anexar a uma fatura"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        try:
            subcontratos = db.session.query(CarviaSubcontrato).filter(
                CarviaSubcontrato.transportadora_id == transportadora_id,
                CarviaSubcontrato.status.in_(['COTADO', 'CONFIRMADO']),
                CarviaSubcontrato.fatura_transportadora_id.is_(None),
            ).order_by(CarviaSubcontrato.cte_data_emissao.desc().nullslast()).all()

            resultado = []
            for sub in subcontratos:
                operacao = sub.operacao if hasattr(sub, 'operacao') else None
                resultado.append({
                    'id': sub.id,
                    'cte_numero': sub.cte_numero or f'#{sub.id}',
                    'cliente': operacao.nome_cliente if operacao else '-',
                    'destino': (
                        f"{operacao.cidade_destino}/{operacao.uf_destino}"
                        if operacao else '-'
                    ),
                    'valor_cotado': float(sub.valor_cotado or 0),
                    'valor_acertado': float(sub.valor_acertado or 0) if sub.valor_acertado else None,
                    'valor_final': float(sub.valor_final or 0),
                })

            return jsonify({'sucesso': True, 'subcontratos': resultado})

        except Exception as e:
            logger.error(f"Erro ao listar subcontratos disponiveis: {e}")
            return jsonify({'sucesso': False, 'erro': str(e)}), 500

    @bp.route('/faturas-transportadora/<int:fatura_id>/atualizar-valor', methods=['POST']) # type: ignore
    @login_required
    def atualizar_valor_fatura_transportadora(fatura_id): # type: ignore
        """Atualiza valor total de uma fatura de transportadora"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'sucesso': False, 'erro': 'Acesso negado'}), 403

        fatura = db.session.get(CarviaFaturaTransportadora, fatura_id)
        if not fatura:
            return jsonify({'sucesso': False, 'erro': 'Fatura nao encontrada'}), 404

        if fatura.status_conferencia == 'CONFERIDO':
            return jsonify({
                'sucesso': False,
                'erro': 'Nao e possivel alterar valor de fatura ja conferida.'
            }), 400

        data = request.get_json(silent=True) or {}
        try:
            valor_total = float(data.get('valor_total', 0))
        except (ValueError, TypeError):
            return jsonify({'sucesso': False, 'erro': 'Valor invalido.'}), 400

        if valor_total <= 0:
            return jsonify({'sucesso': False, 'erro': 'Valor deve ser maior que zero.'}), 400

        try:
            valor_anterior = float(fatura.valor_total or 0)
            fatura.valor_total = valor_total
            db.session.commit()

            logger.info(
                f"Fatura transportadora #{fatura_id}: valor atualizado "
                f"R$ {valor_anterior:.2f} -> R$ {valor_total:.2f} "
                f"por {current_user.email}"
            )

            return jsonify({
                'sucesso': True,
                'valor_total': round(valor_total, 2),
            })

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao atualizar valor fatura #{fatura_id}: {e}")
            return jsonify({'sucesso': False, 'erro': str(e)}), 500

    @bp.route('/faturas-transportadora/<int:fatura_id>') # type: ignore
    @login_required
    def detalhe_fatura_transportadora(fatura_id): # type: ignore
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
        ).order_by(CarviaSubcontrato.cte_data_emissao.desc().nullslast()).all()

        # Calcular totais para conferencia
        valor_cotado_total = sum(float(s.valor_cotado or 0) for s in subcontratos)
        valor_acertado_total = sum(float(s.valor_final or 0) for s in subcontratos)

        # Resumo de conferencia individual
        from app.carvia.services.documentos.conferencia_service import ConferenciaService
        conferencia_resumo = ConferenciaService().resumo_conferencia_fatura(fatura_id)

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
            ).order_by(CarviaOperacao.cte_data_emissao.desc().nullslast()).all()

        return render_template(
            'carvia/faturas_transportadora/detalhe.html',
            fatura=fatura,
            subcontratos=subcontratos,
            valor_cotado_total=valor_cotado_total,
            valor_acertado_total=valor_acertado_total,
            conferencia_resumo=conferencia_resumo,
            itens=itens,
            nfs=nfs,
            faturas_cliente=faturas_cliente,
            operacoes=operacoes,
        )

    @bp.route('/faturas-transportadora/<int:fatura_id>/editar-vencimento', methods=['POST']) # type: ignore
    @login_required
    def editar_vencimento_fatura_transportadora(fatura_id): # type: ignore
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

    @bp.route('/faturas-transportadora/<int:fatura_id>/conferencia', methods=['POST']) # type: ignore
    @login_required
    def conferir_fatura_transportadora(fatura_id): # type: ignore
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

            if novo_status == 'CONFERIDO':
                # Verificar se todos subcontratos tem conferencia individual APROVADO
                subs_pendentes = [
                    s for s in fatura.subcontratos
                    if s.status in ('FATURADO', 'CONFERIDO')
                    and s.status_conferencia != 'APROVADO'
                ]
                subs_divergentes = [
                    s for s in fatura.subcontratos
                    if s.status_conferencia == 'DIVERGENTE'
                ]
                if subs_divergentes:
                    flash(
                        f'{len(subs_divergentes)} subcontrato(s) com status DIVERGENTE. '
                        f'Resolva antes de conferir a fatura.',
                        'warning',
                    )
                    return redirect(url_for('carvia.detalhe_fatura_transportadora', fatura_id=fatura_id))
                if subs_pendentes:
                    flash(
                        f'{len(subs_pendentes)} subcontrato(s) ainda nao conferidos individualmente. '
                        f'Confira cada subcontrato antes de aprovar a fatura.',
                        'warning',
                    )
                    return redirect(url_for('carvia.detalhe_fatura_transportadora', fatura_id=fatura_id))

            fatura.status_conferencia = novo_status
            # GAP-32: Registrar autor/timestamp para TODOS os status de conferencia
            fatura.conferido_por = current_user.email
            fatura.conferido_em = agora_utc_naive()
            if novo_status == 'CONFERIDO':
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

    # ==================== VINCULAR/DESVINCULAR OPERACAO ↔ FATURA CLIENTE ====================

    @bp.route('/faturas-cliente/<int:fatura_id>/vincular-operacao', methods=['POST']) # type: ignore
    @login_required
    def api_vincular_operacao_fatura_cliente(fatura_id): # type: ignore
        """Vincula operacao a fatura cliente: status -> FATURADO, seta FK."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'sucesso': False, 'erro': 'Acesso negado'}), 403

        fatura = db.session.get(CarviaFaturaCliente, fatura_id)
        if not fatura:
            return jsonify({'sucesso': False, 'erro': 'Fatura nao encontrada'}), 404

        if fatura.status in ('PAGA', 'CANCELADA'):
            return jsonify({'sucesso': False, 'erro': f'Fatura {fatura.status} nao aceita vinculos.'}), 400

        data = request.get_json(silent=True) or {}
        operacao_id = data.get('operacao_id')
        if not operacao_id:
            return jsonify({'sucesso': False, 'erro': 'operacao_id obrigatorio.'}), 400

        try:
            operacao = db.session.query(CarviaOperacao).filter(
                CarviaOperacao.id == operacao_id,
                CarviaOperacao.status.in_(['RASCUNHO', 'COTADO', 'CONFIRMADO']),
                CarviaOperacao.fatura_cliente_id.is_(None),
            ).with_for_update().first()

            if not operacao:
                return jsonify({'sucesso': False, 'erro': 'Operacao nao encontrada ou ja faturada.'}), 400

            operacao.fatura_cliente_id = fatura.id
            operacao.status = 'FATURADO'
            # Retroativo: vincular CarviaFrete pela operacao_id
            CarviaFrete.query.filter_by(operacao_id=operacao.id).update(
                {'fatura_cliente_id': fatura.id}
            )

            # Recalcular valor_total da fatura
            soma = db.session.query(
                func.coalesce(func.sum(CarviaOperacao.cte_valor), 0)
            ).filter(CarviaOperacao.fatura_cliente_id == fatura.id).scalar()

            soma_comp = db.session.query(
                func.coalesce(func.sum(CarviaCteComplementar.cte_valor), 0)
            ).filter(CarviaCteComplementar.fatura_cliente_id == fatura.id).scalar()

            fatura.valor_total = (soma or 0) + (soma_comp or 0)
            db.session.commit()

            logger.info(
                f"Operacao #{operacao_id} vinculada a fatura cliente #{fatura_id} "
                f"por {current_user.email}. Valor total: R$ {fatura.valor_total:.2f}"
            )
            return jsonify({'sucesso': True, 'valor_total': float(fatura.valor_total or 0)})

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao vincular operacao #{operacao_id} a fatura #{fatura_id}: {e}")
            return jsonify({'sucesso': False, 'erro': str(e)}), 500

    @bp.route('/faturas-cliente/<int:fatura_id>/desvincular-operacao/<int:op_id>', methods=['POST']) # type: ignore
    @login_required
    def api_desvincular_operacao_fatura_cliente(fatura_id, op_id): # type: ignore
        """Desvincula operacao de fatura cliente: reverte status, limpa FK."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'sucesso': False, 'erro': 'Acesso negado'}), 403

        fatura = db.session.get(CarviaFaturaCliente, fatura_id)
        if not fatura:
            return jsonify({'sucesso': False, 'erro': 'Fatura nao encontrada'}), 404

        if fatura.status in ('PAGA', 'CANCELADA'):
            return jsonify({'sucesso': False, 'erro': f'Fatura {fatura.status} nao permite desvincular.'}), 400

        try:
            operacao = db.session.query(CarviaOperacao).filter(
                CarviaOperacao.id == op_id,
                CarviaOperacao.fatura_cliente_id == fatura_id,
            ).with_for_update().first()

            if not operacao:
                return jsonify({'sucesso': False, 'erro': 'Operacao nao encontrada nesta fatura.'}), 404

            operacao.fatura_cliente_id = None
            operacao.status = 'CONFIRMADO'
            # Retroativo: limpar CarviaFrete.fatura_cliente_id
            CarviaFrete.query.filter_by(operacao_id=operacao.id).update(
                {'fatura_cliente_id': None}
            )

            # Recalcular valor_total
            soma = db.session.query(
                func.coalesce(func.sum(CarviaOperacao.cte_valor), 0)
            ).filter(CarviaOperacao.fatura_cliente_id == fatura.id).scalar()

            soma_comp = db.session.query(
                func.coalesce(func.sum(CarviaCteComplementar.cte_valor), 0)
            ).filter(CarviaCteComplementar.fatura_cliente_id == fatura.id).scalar()

            fatura.valor_total = (soma or 0) + (soma_comp or 0)
            db.session.commit()

            logger.info(
                f"Operacao #{op_id} desvinculada de fatura cliente #{fatura_id} "
                f"por {current_user.email}"
            )
            return jsonify({'sucesso': True, 'valor_total': float(fatura.valor_total or 0)})

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao desvincular operacao #{op_id} de fatura #{fatura_id}: {e}")
            return jsonify({'sucesso': False, 'erro': str(e)}), 500

    @bp.route('/api/operacoes-disponiveis-fatura') # type: ignore
    @login_required
    def api_operacoes_disponiveis_fatura(): # type: ignore
        """Lista operacoes disponiveis para vincular a fatura cliente (R5)."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'sucesso': False, 'erro': 'Acesso negado'}), 403

        busca = request.args.get('busca', '')
        cnpj_cliente = request.args.get('cnpj_cliente', '')

        query = db.session.query(CarviaOperacao).filter(
            CarviaOperacao.status.in_(['RASCUNHO', 'COTADO', 'CONFIRMADO']),
            CarviaOperacao.fatura_cliente_id.is_(None),
        )

        if cnpj_cliente:
            query = query.filter(CarviaOperacao.cnpj_cliente == cnpj_cliente)

        if busca:
            busca_like = f'%{busca}%'
            query = query.filter(db.or_(
                CarviaOperacao.cte_numero.ilike(busca_like),
                CarviaOperacao.nome_cliente.ilike(busca_like),
                CarviaOperacao.cidade_destino.ilike(busca_like),
            ))

        operacoes = query.order_by(CarviaOperacao.cte_data_emissao.desc().nullslast()).limit(50).all()

        return jsonify({
            'sucesso': True,
            'operacoes': [{
                'id': op.id,
                'cte_numero': op.cte_numero,
                'nome_cliente': op.nome_cliente,
                'cnpj_cliente': op.cnpj_cliente,
                'cte_valor': float(op.cte_valor) if op.cte_valor else None,
                'status': op.status,
                'destino': f'{op.cidade_destino}/{op.uf_destino}' if op.cidade_destino else '-',
            } for op in operacoes],
        })
