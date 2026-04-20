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
from app.carvia.services.financeiro.rateio_conciliacao_helper import (
    ratear_conciliacao_fatura,
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
        cliente_filtro = request.args.get('cliente', '')
        tipo_frete_filtro = request.args.get('tipo_frete', '')
        data_emissao_de = request.args.get('data_emissao_de', '')
        data_emissao_ate = request.args.get('data_emissao_ate', '')
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
        if cliente_filtro:
            cliente_like = f'%{cliente_filtro}%'
            query = query.filter(
                db.or_(
                    CarviaFaturaCliente.nome_cliente.ilike(cliente_like),
                    CarviaFaturaCliente.cnpj_cliente.ilike(cliente_like),
                )
            )
        if busca:
            busca_like = f'%{busca}%'
            query = query.filter(
                CarviaFaturaCliente.numero_fatura.ilike(busca_like),
            )

        if data_emissao_de:
            try:
                dt_de = datetime.strptime(data_emissao_de, '%Y-%m-%d').date()
                query = query.filter(CarviaFaturaCliente.data_emissao >= dt_de)
            except ValueError:
                pass
        if data_emissao_ate:
            try:
                dt_ate = datetime.strptime(data_emissao_ate, '%Y-%m-%d').date()
                query = query.filter(CarviaFaturaCliente.data_emissao <= dt_ate)
            except ValueError:
                pass

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

        # Batch: CTes vinculados por fatura (numeros + ids para badges inline)
        from collections import defaultdict
        ops_por_fatura = defaultdict(list)
        fat_ids = [f.id for f, _ in paginacao.items]
        if fat_ids:
            rows_ops = db.session.query(
                CarviaOperacao.fatura_cliente_id,
                CarviaOperacao.id,
                CarviaOperacao.cte_numero,
            ).filter(
                CarviaOperacao.fatura_cliente_id.in_(fat_ids)
            ).all()
            for fat_id, op_id, cte_num in rows_ops:
                ops_por_fatura[fat_id].append({'id': op_id, 'cte_numero': cte_num})

        # Batch papeis (emit/dest/tomador) via helper centralizado que:
        # - faz join operacao -> NF (caminho principal)
        # - faz fallback via CTe Complementar -> operacao pai -> NF
        # - faz fallback final via tipo_frete (FOB/CIF) quando nao ha NF
        from app.carvia.utils.papeis_frete import batch_papeis_por_fatura_cliente
        tipo_frete_por_fat = {f.id: f.tipo_frete for f, _ in paginacao.items if f.tipo_frete}
        papeis_por_fatura = batch_papeis_por_fatura_cliente(fat_ids, tipo_frete_por_fat)

        today = date.today()

        # Batch: resolver clientes comerciais por CNPJ cliente
        import re
        from app.carvia.services.clientes.cliente_service import CarviaClienteService
        cnpjs_cli = {f.cnpj_cliente for f, _ in paginacao.items if f.cnpj_cliente}
        _resolved = CarviaClienteService.resolver_clientes_por_cnpjs(cnpjs_cli)
        clientes_por_cnpj = {
            cnpj: _resolved[re.sub(r'\D', '', cnpj)]
            for cnpj in cnpjs_cli
            if re.sub(r'\D', '', cnpj) in _resolved
        }

        return render_template(
            'carvia/faturas_cliente/listar.html',
            faturas=paginacao.items,
            paginacao=paginacao,
            status_filtro=status_filtro,
            tipo_frete_filtro=tipo_frete_filtro,
            busca=busca,
            cliente_filtro=cliente_filtro,
            data_emissao_de=data_emissao_de,
            data_emissao_ate=data_emissao_ate,
            sort=sort,
            direction=direction,
            today=today,
            ops_por_fatura=ops_por_fatura,
            clientes_por_cnpj=clientes_por_cnpj,
            papeis_por_fatura=papeis_por_fatura,
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
            # tipo_frete: FOB/CIF para habilitar fallback do Tomador no Excel
            # quando o CTe e criado manualmente (cte_tomador NULL na operacao).
            tipo_frete_raw = (request.form.get('tipo_frete') or '').strip().upper()
            tipo_frete = tipo_frete_raw if tipo_frete_raw in ('FOB', 'CIF') else None

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
                    tipo_frete=tipo_frete,
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

                # PRE-VINCULO: resolver pre-vinculos extrato<->cotacao da cadeia da fatura
                try:
                    from app.carvia.services.financeiro.previnculo_service import (
                        CarviaPreVinculoService,
                    )
                    # FIX C2: SAVEPOINT isola erros do resolver da transacao da fatura.
                    # Sem isso, um IntegrityError no flush do resolver polui a session
                    # e o db.session.commit() subsequente da rota falha, causando
                    # rollback completo da criacao da fatura (sintoma: fatura criada
                    # com sucesso no UI mas some do banco).
                    with db.session.begin_nested():
                        CarviaPreVinculoService.resolver_para_fatura(
                            fatura.id, current_user.email,
                        )
                except Exception as _e:
                    logger.warning(
                        'Falha ao resolver pre-vinculos fatura %s: %s', fatura.id, _e
                    )

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

            ctes_comp_disponiveis = db.session.query(CarviaCteComplementar).options(
                db.joinedload(CarviaCteComplementar.operacao)
            ).filter(
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

        # CTe Complementares vinculados a esta fatura (joinedload para evitar N+1
        # quando o template acessa comp.operacao.cte_numero/ctrc_numero)
        ctes_complementares = CarviaCteComplementar.query.options(
            db.joinedload(CarviaCteComplementar.operacao)
        ).filter_by(fatura_cliente_id=fatura_id).all()

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

        # Custos de entrega via operacoes (joinedload para evitar N+1 no template
        # que acessa custo.operacao.cte_numero/ctrc_numero)
        from app.carvia.models import CarviaCustoEntrega
        custos_entrega = []
        if op_ids:
            custos_entrega = CarviaCustoEntrega.query.options(
                db.joinedload(CarviaCustoEntrega.operacao)
            ).filter(
                CarviaCustoEntrega.operacao_id.in_(op_ids)
            ).order_by(CarviaCustoEntrega.criado_em.desc()).all()

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

        # Resolver cliente comercial por CNPJ cliente
        import re
        from app.carvia.services.clientes.cliente_service import CarviaClienteService
        _clientes = CarviaClienteService.resolver_clientes_por_cnpjs({fatura.cnpj_cliente})
        cliente_comercial = _clientes.get(re.sub(r'\D', '', fatura.cnpj_cliente or ''))

        # Papeis de frete via helper centralizado (cobre operacao + CTe Comp fallback + tipo_frete)
        from app.carvia.utils.papeis_frete import resolver_papeis_fatura_cliente
        papeis = resolver_papeis_fatura_cliente(fatura)

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
            custos_entrega=custos_entrega,
            cliente_comercial=cliente_comercial,
            papeis=papeis,
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

        # Refator 2.1: fatura CONFERIDA bloqueia edicao ate ser reaberta
        if fatura.status_conferencia == 'CONFERIDO':
            flash(
                'Fatura conferida nao pode ter valor alterado. '
                'Reabra a conferencia antes de editar.',
                'warning',
            )
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

        # Refator 2.1: fatura CONFERIDA bloqueia edicao ate ser reaberta
        if fatura.status_conferencia == 'CONFERIDO':
            flash(
                'Fatura conferida nao pode ter vencimento alterado. '
                'Reabra a conferencia antes de editar.',
                'warning',
            )
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

        # Refator 2.1: fatura CONFERIDA bloqueia alteracao ate ser reaberta
        if fatura.status_conferencia == 'CONFERIDO':
            return jsonify({
                'erro': (
                    'Fatura conferida nao pode ter pagador alterado. '
                    'Reabra a conferencia antes.'
                )
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
        """Atualiza status da fatura para PENDENTE ou CANCELADA.

        Para pagamento (PAGA), usar endpoint JSON
        /faturas-cliente/<id>/pagar via CarviaPagamentoService.
        W10 Nivel 2 (Sprint 4): pagamento centralizado no service.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        fatura = db.session.get(CarviaFaturaCliente, fatura_id)
        if not fatura:
            flash('Fatura nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_faturas_cliente'))

        novo_status = request.form.get('status')
        if novo_status not in ('PENDENTE', 'CANCELADA'):
            flash(
                'Status invalido. Para marcar como PAGA, use o botao "Pagar".',
                'warning',
            )
            return redirect(url_for('carvia.detalhe_fatura_cliente', fatura_id=fatura_id))

        # NC1: bloquear transicao PAGA -> CANCELADA direta. R4 exige que
        # CANCELADA venha de PENDENTE — desfazer pagamento primeiro,
        # cancelar depois (2 acoes explicitas).
        if fatura.status == 'PAGA' and novo_status == 'CANCELADA':
            flash(
                'Nao e possivel cancelar fatura PAGA diretamente. '
                'Desfaca o pagamento primeiro (isso reverte para PENDENTE), '
                'depois cancele.',
                'warning',
            )
            return redirect(url_for(
                'carvia.detalhe_fatura_cliente', fatura_id=fatura_id
            ))

        # Refator 2.1: fatura CONFERIDA bloqueia mudanca de status.
        # Cancelar fatura conferida e contraditorio — exige reabrir conferencia primeiro.
        # Nota: a rota /aprovar pode aprovar fatura PAGA, mas /status (cancelamento/retorno
        # para PENDENTE) deve respeitar a trava da conferencia.
        if fatura.status_conferencia == 'CONFERIDO':
            flash(
                'Fatura conferida nao pode ter status alterado. '
                'Reabra a conferencia antes de cancelar ou reverter status.',
                'warning',
            )
            return redirect(url_for('carvia.detalhe_fatura_cliente', fatura_id=fatura_id))

        try:
            # Se revertendo de PAGA, usar service de desfazer (desconcilia MANUAL)
            if fatura.status == 'PAGA':
                from app.carvia.services.financeiro.carvia_pagamento_service import (
                    CarviaPagamentoService, PagamentoError,
                )
                try:
                    CarviaPagamentoService.desfazer_pagamento(
                        'fatura_cliente', fatura_id, current_user.email
                    )
                except PagamentoError as e:
                    db.session.rollback()
                    flash(str(e), 'danger')
                    return redirect(url_for(
                        'carvia.detalhe_fatura_cliente', fatura_id=fatura_id
                    ))
                # Compat historico (ContaMovimentacao legada) e feito
                # INTERNAMENTE por CarviaPagamentoService.desfazer_pagamento.

            # Aplicar novo status (apos desfazer, pode ir para CANCELADA)
            fatura.status = novo_status
            db.session.commit()
            flash(f'Status atualizado para {novo_status}.', 'success')

        except Exception as e:
            db.session.rollback()
            logger.exception(f"Erro ao atualizar status fatura cliente #{fatura_id}: {e}")
            flash(f'Erro: {e}', 'danger')

        return redirect(url_for('carvia.detalhe_fatura_cliente', fatura_id=fatura_id))

    # ==================== CONFERENCIA GERENCIAL (Refator 2.1) ====================
    # Aprovacao manual sem gate automatico — decisao do usuario confirmada.
    # Pagamento (status=PAGA) permanece independente desta auditoria.
    # Ao CONFERIDO, pode_editar() bloqueia todas as alteracoes ate reabrir.

    @bp.route('/faturas-cliente/<int:fatura_id>/aprovar', methods=['POST']) # type: ignore
    @login_required
    def aprovar_fatura_cliente(fatura_id): # type: ignore
        """Aprova conferencia gerencial de uma fatura cliente.

        Gate: MANUAL puro — nao valida soma de CTes nem status das operacoes.
        A aprovacao e uma decisao gerencial registrada com auditoria.
        Permite aprovar fatura em qualquer `status` (PENDENTE ou PAGA).
        """
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        fatura = db.session.get(CarviaFaturaCliente, fatura_id)
        if not fatura:
            flash('Fatura nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_faturas_cliente'))

        # Defesa: garantir que o valor atual esta na lista de statuses validos
        if fatura.status_conferencia not in CarviaFaturaCliente.STATUSES_CONFERENCIA:
            flash(
                f'Estado de conferencia invalido ({fatura.status_conferencia}). '
                f'Contate o suporte.',
                'danger',
            )
            return redirect(url_for('carvia.detalhe_fatura_cliente', fatura_id=fatura_id))

        if fatura.status_conferencia == 'CONFERIDO':
            flash('Fatura ja esta conferida.', 'info')
            return redirect(url_for('carvia.detalhe_fatura_cliente', fatura_id=fatura_id))

        if fatura.status == 'CANCELADA':
            flash('Fatura cancelada nao pode ser conferida.', 'warning')
            return redirect(url_for('carvia.detalhe_fatura_cliente', fatura_id=fatura_id))

        observacoes = (request.form.get('observacoes_conferencia', '') or '').strip()

        try:
            from app.utils.timezone import agora_utc_naive

            fatura.status_conferencia = 'CONFERIDO'
            fatura.conferido_por = current_user.email
            fatura.conferido_em = agora_utc_naive()
            if observacoes:
                timestamp = agora_utc_naive().strftime('%d/%m/%Y %H:%M')
                entry = f'[{timestamp}] APROVADO por {current_user.email}: {observacoes}'
                fatura.observacoes_conferencia = (
                    f'{fatura.observacoes_conferencia}\n{entry}'
                    if fatura.observacoes_conferencia else entry
                )

            db.session.commit()

            logger.info(
                f"Fatura cliente #{fatura_id} APROVADA por {current_user.email}"
            )
            flash(f'Fatura {fatura.numero_fatura} aprovada com sucesso.', 'success')

        except Exception as e:
            db.session.rollback()
            logger.exception(f"Erro ao aprovar fatura cliente #{fatura_id}: {e}")
            flash(f'Erro: {e}', 'danger')

        return redirect(url_for('carvia.detalhe_fatura_cliente', fatura_id=fatura_id))

    @bp.route('/faturas-cliente/<int:fatura_id>/reabrir-conferencia', methods=['POST']) # type: ignore
    @login_required
    def reabrir_conferencia_fatura_cliente(fatura_id): # type: ignore
        """Reabre conferencia de uma fatura cliente (CONFERIDO -> PENDENTE).

        Libera a fatura para edicao novamente. Requer motivo obrigatorio
        para auditoria. Historico preservado em observacoes_conferencia.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        fatura = db.session.get(CarviaFaturaCliente, fatura_id)
        if not fatura:
            flash('Fatura nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_faturas_cliente'))

        # Defesa: garantir que o valor atual esta na lista de statuses validos
        if fatura.status_conferencia not in CarviaFaturaCliente.STATUSES_CONFERENCIA:
            flash(
                f'Estado de conferencia invalido ({fatura.status_conferencia}). '
                f'Contate o suporte.',
                'danger',
            )
            return redirect(url_for('carvia.detalhe_fatura_cliente', fatura_id=fatura_id))

        if fatura.status_conferencia != 'CONFERIDO':
            flash('Apenas faturas CONFERIDAS podem ser reabertas.', 'warning')
            return redirect(url_for('carvia.detalhe_fatura_cliente', fatura_id=fatura_id))

        motivo = (request.form.get('motivo_reabertura', '') or '').strip()
        if not motivo:
            flash('Motivo da reabertura e obrigatorio.', 'warning')
            return redirect(url_for('carvia.detalhe_fatura_cliente', fatura_id=fatura_id))

        try:
            from app.utils.timezone import agora_utc_naive

            timestamp = agora_utc_naive().strftime('%d/%m/%Y %H:%M')
            aprovado_por_anterior = fatura.conferido_por or '(desconhecido)'
            entry = (
                f'[{timestamp}] REABERTA por {current_user.email} '
                f'(aprovada anteriormente por {aprovado_por_anterior}). Motivo: {motivo}'
            )

            fatura.status_conferencia = 'PENDENTE'
            fatura.conferido_por = None
            fatura.conferido_em = None
            fatura.observacoes_conferencia = (
                f'{fatura.observacoes_conferencia}\n{entry}'
                if fatura.observacoes_conferencia else entry
            )

            db.session.commit()

            logger.info(
                f"Fatura cliente #{fatura_id} REABERTA por {current_user.email}: {motivo}"
            )
            flash(f'Fatura {fatura.numero_fatura} reaberta. Edicao liberada.', 'success')

        except Exception as e:
            db.session.rollback()
            logger.exception(f"Erro ao reabrir fatura cliente #{fatura_id}: {e}")
            flash(f'Erro: {e}', 'danger')

        return redirect(url_for('carvia.detalhe_fatura_cliente', fatura_id=fatura_id))

    @bp.route('/faturas-cliente/<int:fatura_id>/pagar', methods=['POST']) # type: ignore
    @login_required
    def pagar_fatura_cliente(fatura_id): # type: ignore
        """Paga fatura cliente via CarviaPagamentoService (JSON).

        Dois modos:
        1. Com conciliacao: {data_pagamento, extrato_linha_id}
        2. Manual: {data_pagamento, conta_origem, descricao_pagamento}
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        fatura = db.session.get(CarviaFaturaCliente, fatura_id)
        if not fatura:
            return jsonify({'erro': 'Fatura nao encontrada'}), 404

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
                    tipo_doc='fatura_cliente',
                    doc_id=fatura_id,
                    data_pagamento=data_pagamento,
                    extrato_linha_id=extrato_linha_id,
                    usuario=current_user.email,
                )
            else:
                resultado = CarviaPagamentoService.pagar_manual(
                    tipo_doc='fatura_cliente',
                    doc_id=fatura_id,
                    data_pagamento=data_pagamento,
                    conta_origem=conta_origem,
                    descricao_pagamento=descricao_pagamento,
                    usuario=current_user.email,
                )
            db.session.commit()

            return jsonify({
                'sucesso': True,
                'novo_status': resultado['novo_status'],
                'pago_em': fatura.pago_em.isoformat() if fatura.pago_em else None,
                'pago_por': fatura.pago_por,
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
            logger.exception(f"Erro ao pagar fatura cliente #{fatura_id}: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/faturas-cliente/<int:fatura_id>/desfazer-pagamento', methods=['POST']) # type: ignore
    @login_required
    def desfazer_pagamento_fatura_cliente(fatura_id): # type: ignore
        """Desfaz pagamento via CarviaPagamentoService (JSON)."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        from app.carvia.services.financeiro.carvia_pagamento_service import (
            CarviaPagamentoService,
            DocumentoNaoEncontradoError,
            PagamentoError,
        )

        try:
            resultado = CarviaPagamentoService.desfazer_pagamento(
                'fatura_cliente', fatura_id, current_user.email
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
            logger.exception(f"Erro desfazer fatura cliente #{fatura_id}: {e}")
            return jsonify({'erro': str(e)}), 500

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

            # PRE-VINCULO: resolver pre-vinculos extrato<->cotacao da cadeia
            try:
                from app.carvia.services.financeiro.previnculo_service import (
                    CarviaPreVinculoService,
                )
                # FIX C2: SAVEPOINT isola erros do resolver da transacao da fatura.
                # Sem isso, um IntegrityError no flush do resolver polui a session
                # e o db.session.commit() subsequente da rota falha, causando
                # rollback completo da criacao da fatura (sintoma: fatura criada
                # com sucesso no UI mas some do banco).
                with db.session.begin_nested():
                    CarviaPreVinculoService.resolver_para_fatura(
                        fatura.id, current_user.email,
                    )
            except Exception as _e:
                logger.warning(
                    'Falha ao resolver pre-vinculos fatura %s: %s', fatura.id, _e
                )

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

        sort = request.args.get('sort', 'id')
        direction = request.args.get('direction', 'desc')

        # Subquery: contar e somar valor dos subcontratos por fatura
        # Phase C (2026-04-14): valor_considerado migrou para CarviaFrete.
        # Hierarquia: frete.valor_considerado > sub.valor_acertado > sub.valor_cotado.
        # LEFT JOIN CarviaFrete via sub.frete_id (pode ser NULL para legados).
        subq_subs = db.session.query(
            CarviaSubcontrato.fatura_transportadora_id,
            func.count(CarviaSubcontrato.id).label('qtd_subs'),
            func.sum(
                func.coalesce(
                    CarviaFrete.valor_considerado,
                    CarviaSubcontrato.valor_acertado,
                    CarviaSubcontrato.valor_cotado,
                    0,
                )
            ).label('valor_subs'),
        ).outerjoin(
            CarviaFrete, CarviaSubcontrato.frete_id == CarviaFrete.id,
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
            'id': CarviaFaturaTransportadora.id,
            'numero_fatura': func.lpad(func.coalesce(CarviaFaturaTransportadora.numero_fatura, ''), 20, '0'),
            'data_emissao': CarviaFaturaTransportadora.data_emissao,
            'vencimento': CarviaFaturaTransportadora.vencimento,
            'valor_total': CarviaFaturaTransportadora.valor_total,
            'status_conferencia': CarviaFaturaTransportadora.status_conferencia,
            'criado_em': CarviaFaturaTransportadora.criado_em,
        }
        sort_col = sortable_columns.get(sort, CarviaFaturaTransportadora.id)
        if direction == 'asc':
            query = query.order_by(sort_col.asc().nullslast())
        else:
            query = query.order_by(sort_col.desc().nullslast())

        paginacao = query.paginate(page=request.args.get('page', 1, type=int), per_page=20, error_out=False)

        today = date.today()

        # Batch papeis (emit/dest/tomador) para coluna Emitente/Destinatario
        from app.carvia.utils.papeis_frete import (
            batch_papeis_por_fatura_transportadora,
        )
        fat_ids = [f.id for f, _qtd, _val in paginacao.items]
        papeis_por_fatura = batch_papeis_por_fatura_transportadora(fat_ids)

        return render_template(
            'carvia/faturas_transportadora/listar.html',
            faturas=paginacao.items,
            paginacao=paginacao,
            form=form,
            sort=sort,
            direction=direction,
            today=today,
            papeis_por_fatura=papeis_por_fatura,
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
        """Desanexa um subcontrato de uma fatura de transportadora.

        W4 (Sprint 2): guard via ft.pode_desanexar_subcontrato() que
        bloqueia tanto CONFERIDO quanto PAGO (status_pagamento). Antes
        so bloqueava CONFERIDO — faturas PAGAS passavam.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'sucesso': False, 'erro': 'Acesso negado'}), 403

        fatura = db.session.get(CarviaFaturaTransportadora, fatura_id)
        if not fatura:
            return jsonify({'sucesso': False, 'erro': 'Fatura nao encontrada'}), 404

        # Guard centralizado no model (Sprint 0) — CONFERIDO + PAGO + conciliada
        pode, razao = fatura.pode_desanexar_subcontrato()
        if not pode:
            return jsonify({'sucesso': False, 'erro': razao}), 400

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

            # Nota: CEs vinculados a esta FT tem FK direta (fatura_transportadora_id),
            # nao dependem do sub. Desanexar o sub nao afeta o vinculo CE->FT.
            # Para desvincular um CE da FT, usar POST /custos-entrega/<id>/desvincular-fatura
            # (CustoEntregaFaturaService.desvincular).

            # Reverter subcontrato + limpar CarviaFrete
            # Status reverte para CONFIRMADO: subcontratos anexados manualmente
            # passaram pelo fluxo COTADO→CONFIRMADO antes de FATURADO.
            # (diferente de frete_routes.py que reverte para PENDENTE — la o sub
            # foi auto-criado via processar_cte_subcontrato sem confirmacao manual)
            sub.fatura_transportadora_id = None
            sub.status = 'CONFIRMADO'
            # Phase C: sub.requer_aprovacao removido — flag agora e frete.requer_aprovacao

            # Hook: cancelar movimentacoes CC ativas + rejeitar aprovacoes pendentes
            # (a diferenca considerado-pago nao se aplica mais sem fatura vinculada)
            # Phase C: CC e aprovacoes operam em Frete — resolvemos frete via sub.frete_id
            from app.carvia.services.financeiro.conta_corrente_service import (
                ContaCorrenteService,
            )
            from app.carvia.services.documentos.aprovacao_frete_service import (
                AprovacaoFreteService,
            )
            if sub.frete_id:
                ContaCorrenteService.cancelar_movimentacoes(
                    frete_id=sub.frete_id,
                    motivo=f'Desanexado da fatura #{fatura_id}',
                    usuario=current_user.email,
                )
                AprovacaoFreteService().rejeitar_pendentes_de_frete(
                    frete_id=sub.frete_id,
                    motivo=f'Desanexado da fatura #{fatura_id}',
                    usuario=current_user.email,
                )
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
                # Phase C (2026-04-14): valor_considerado migrou para CarviaFrete.
                # Leitura via sub.frete. Hierarquia preservada:
                # frete.valor_considerado > sub.valor_acertado > sub.valor_cotado.
                valor_considerado = (
                    sub.frete.valor_considerado if sub.frete else None
                )
                valor_previsto = (
                    valor_considerado
                    or sub.valor_acertado
                    or sub.valor_cotado
                    or 0
                )
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
                    'valor_considerado': float(valor_considerado or 0) if valor_considerado else None,
                    # valor_final mantido por compat com JS (detalhe.js:293)
                    'valor_final': float(valor_previsto),
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

        pode, razao = fatura.pode_editar()
        if not pode:
            return jsonify({'sucesso': False, 'erro': razao}), 400

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
        """Tela de VISUALIZAR uma fatura de transportadora.

        Paridade Nacom: equivalente a `fretes.visualizar_fatura` —
        mostra dados basicos, resumo, tabelas de subcontratos e custos
        de entrega, e informacoes de conferencia (quando CONFERIDO).

        Endpoint name mantido como `detalhe_fatura_transportadora` para
        preservar compatibilidade com ~15 templates que usam
        `url_for('carvia.detalhe_fatura_transportadora', ...)`.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        fatura = db.session.get(CarviaFaturaTransportadora, fatura_id)
        if not fatura:
            flash('Fatura nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_faturas_transportadora'))

        subcontratos = db.session.query(CarviaSubcontrato).options(
            db.joinedload(CarviaSubcontrato.operacao)
        ).filter(
            CarviaSubcontrato.fatura_transportadora_id == fatura_id
        ).order_by(CarviaSubcontrato.cte_data_emissao.desc().nullslast()).all()

        # Totais do card "Resumo" (card de stats — paridade Nacom)
        # Subs CANCELADO excluidos (consistente com conferencia)
        subs_ativos = [s for s in subcontratos if s.status != 'CANCELADO']
        total_subcontratos = len(subs_ativos)
        # Phase 14 (2026-04-14): `sub.valor_considerado` removido; fonte
        # canonica agora eh `sub.frete.valor_considerado`. Fallback para
        # `sub.valor_acertado`/`sub.valor_cotado` (campos de CTe legados,
        # nao removidos) quando o sub nao tem frete vinculado.
        def _valor_base_sub(s):
            if s.frete is not None and s.frete.valor_considerado is not None:
                return float(s.frete.valor_considerado)
            return float(s.valor_acertado or s.valor_cotado or 0)
        valor_total_subcontratos = sum(
            _valor_base_sub(s) for s in subs_ativos
        )

        # Cross-links: itens, NFs, faturas cliente
        from app.carvia.models import (
            CarviaFaturaTransportadoraItem, CarviaNf,
            CarviaOperacaoNf, CarviaFaturaCliente,
        )
        itens = CarviaFaturaTransportadoraItem.query.filter_by(
            fatura_transportadora_id=fatura_id
        ).all()

        # Agregacao NFs por subcontrato — alimenta coluna "NFs" no card
        # "Subcontratos Vinculados" (elimina card duplicado "Itens de Detalhe").
        # Estrutura: {sub_id: [item, item, ...]}  (mesmos objetos do `itens`)
        nfs_por_subcontrato = {}
        itens_sem_sub_list = []
        for _it in itens:
            if _it.subcontrato_id:
                nfs_por_subcontrato.setdefault(_it.subcontrato_id, []).append(_it)
            else:
                itens_sem_sub_list.append(_it)

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

        # Custos de entrega vinculados DIRETAMENTE a esta FT via fatura_transportadora_id
        # (padrao DespesaExtra.fatura_frete_id do Nacom — FK direta, sem juncao por operacao)
        from app.carvia.models import CarviaCustoEntrega
        custos_entrega_ft = CarviaCustoEntrega.query.filter(
            CarviaCustoEntrega.fatura_transportadora_id == fatura_id
        ).order_by(CarviaCustoEntrega.criado_em.desc()).all()

        # Totais do card "Resumo" — custos de entrega
        custos_entrega_ativos = [
            ce for ce in custos_entrega_ft if ce.status != 'CANCELADO'
        ]
        total_custos_entrega = len(custos_entrega_ativos)
        valor_total_custos_entrega = sum(
            float(ce.valor or 0) for ce in custos_entrega_ativos
        )
        total_calculado = valor_total_subcontratos + valor_total_custos_entrega

        # CTes complementares via operacoes (caminho fiscal do CTe Comp — cobra cliente)
        ctes_complementares_ft = []
        if op_ids:
            ctes_complementares_ft = CarviaCteComplementar.query.filter(
                CarviaCteComplementar.operacao_id.in_(op_ids)
            ).order_by(CarviaCteComplementar.criado_em.desc()).all()

        # Rateio de "Valor Conciliado" proporcional ao valor_considerado de cada
        # sub/CE. Usa fatura.total_conciliado (SUM de CarviaConciliacao.valor_alocado
        # mantido pelo CarviaConciliacaoService). Quando fatura nao esta conciliada,
        # todos os valores rateados ficam 0.
        rateio_conc = ratear_conciliacao_fatura(
            fatura, subs_ativos, custos_entrega_ativos,
        )
        valor_conciliado_por_sub = {
            sid: float(v) for sid, v in rateio_conc['por_sub'].items()
        }
        valor_conciliado_por_ce = {
            cid: float(v) for cid, v in rateio_conc['por_ce'].items()
        }
        valor_total_conciliado = float(rateio_conc['total'])

        # Papeis (emitente/destinatario/tomador) via primeiro subcontrato → operacao → NFs.
        # CarVia e tomadora do subcontrato, mas o relatorio mostra emit/dest da mercadoria
        # transportada e o cte_tomador do CTe original emitido ao cliente final (quando houver).
        from app.carvia.utils.papeis_frete import (
            resolver_papeis_fatura_transportadora,
        )
        papeis = resolver_papeis_fatura_transportadora(fatura)

        return render_template(
            'carvia/faturas_transportadora/visualizar.html',
            fatura=fatura,
            subcontratos=subcontratos,
            total_subcontratos=total_subcontratos,
            valor_total_subcontratos=valor_total_subcontratos,
            total_custos_entrega=total_custos_entrega,
            valor_total_custos_entrega=valor_total_custos_entrega,
            total_calculado=total_calculado,
            valor_total_conciliado=valor_total_conciliado,
            valor_conciliado_por_sub=valor_conciliado_por_sub,
            valor_conciliado_por_ce=valor_conciliado_por_ce,
            itens=itens,
            nfs_por_subcontrato=nfs_por_subcontrato,
            itens_sem_sub_list=itens_sem_sub_list,
            nfs=nfs,
            faturas_cliente=faturas_cliente,
            operacoes=operacoes,
            custos_entrega=custos_entrega_ft,
            ctes_complementares=ctes_complementares_ft,
            papeis=papeis,
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

        pode, razao = fatura.pode_editar()
        if not pode:
            flash(razao, 'warning')
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

    @bp.route('/faturas-transportadora/<int:fatura_id>/conferir') # type: ignore
    @login_required
    def conferir_fatura_transportadora(fatura_id): # type: ignore
        """Tela de CONFERIR fatura de transportadora (paridade Nacom).

        GET. Equivalente a `fretes.conferir_fatura` — monta analise de
        valores, tabela unificada de documentos (subs + CEs) e flags
        de validacao. O POST de aprovacao vai em
        `aprovar_conferencia_fatura_transportadora`.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        fatura = db.session.get(CarviaFaturaTransportadora, fatura_id)
        if not fatura:
            flash('Fatura nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_faturas_transportadora'))

        # Fretes ativos vinculados (exclui CANCELADO) — paridade Nacom
        # `conferir_fatura` que itera Frete.query.filter(fatura_frete_id=X).
        # CarviaFrete e "o eixo central" (ver documentos.py:587): tem os 4
        # valores (cotado, cte, considerado, pago) preenchidos no form
        # `/carvia/fretes/<id>/editar`. Iterar Frete garante que lemos os
        # mesmos campos que o form escreve.
        fretes = CarviaFrete.query.filter(
            CarviaFrete.fatura_transportadora_id == fatura_id,
            CarviaFrete.status != 'CANCELADO',
        ).all()

        # Custos de entrega ativos (padrao DespesaExtra.fatura_frete_id do Nacom)
        from app.carvia.models import CarviaCustoEntrega
        custos_entrega = CarviaCustoEntrega.query.filter(
            CarviaCustoEntrega.fatura_transportadora_id == fatura_id,
            CarviaCustoEntrega.status != 'CANCELADO',
        ).all()

        # Monta tabela unificada "Status dos Documentos" — paridade
        # Nacom `conferir_fatura` (fretes/routes.py:2083-2177).
        documentos_status = []
        valor_total_cotado = 0.0
        valor_total_cte = 0.0
        valor_total_considerado = 0.0
        valor_total_pago = 0.0

        # 1) Fretes (equivalente ao loop de Frete Nacom)
        for frete in fretes:
            # Phase 14 (2026-04-14): conferencia consolidada no Frete.
            # Os gates de bloqueio leem status_conferencia/requer_aprovacao
            # DIRETO do frete (fonte canonica). Nao iteramos mais subs para
            # isso — Sub tornou-se "documento CTe puro".
            #
            # Subs do frete sao resolvidos APENAS para exibicao:
            # cte_numero, cliente (via operacao) e indicador multi-leg.
            subs_do_frete = list(frete.subcontratos.all())
            n_ctes = len(subs_do_frete)
            primary_sub = subs_do_frete[0] if subs_do_frete else None

            # Status doc derivado diretamente do Frete (paridade Nacom)
            if frete.status_conferencia == 'DIVERGENTE' or frete.requer_aprovacao:
                status_doc = 'EM_TRATATIVA'
            elif frete.status_conferencia == 'APROVADO':
                # Paridade Nacom linha 2101: exige numero_cte + valor_cte +
                # valor_pago para status_doc='LANÇADO'. Sem valor_pago, nao
                # pode ser LANÇADO — fica APROVADO (nao passa Gate).
                if frete.valor_cte and frete.valor_pago:
                    status_doc = 'LANÇADO'
                else:
                    status_doc = 'APROVADO'
            else:
                status_doc = 'PENDENTE'

            # Numero do CTe: primary sub ou fallback. Multi-leg: anota "(N CTes)".
            if primary_sub and primary_sub.cte_numero:
                numero_display = primary_sub.cte_numero
            elif primary_sub:
                numero_display = f'Sub #{primary_sub.id}'
            else:
                numero_display = f'Frete #{frete.id}'
            if n_ctes > 1:
                numero_display = f'{numero_display} ({n_ctes} CTes)'

            # Cliente: primary sub → operacao → cliente, ou fallback para destino do frete
            cliente = '-'
            if primary_sub and primary_sub.operacao and primary_sub.operacao.nome_cliente:
                cliente = primary_sub.operacao.nome_cliente
            elif frete.nome_destino:
                cliente = frete.nome_destino

            documentos_status.append({
                'tipo': 'CTe',
                'numero': numero_display,
                'descricao': '',
                'valor_cotado': float(frete.valor_cotado or 0),
                'valor_cte': float(frete.valor_cte or 0),
                'valor_considerado': float(frete.valor_considerado or 0),
                'valor_pago': float(frete.valor_pago or 0),
                'status': status_doc,
                'cliente': cliente,
                'frete_id': frete.id,
                'sub_id': primary_sub.id if primary_sub else None,
            })

            valor_total_cotado += float(frete.valor_cotado or 0)
            valor_total_cte += float(frete.valor_cte or 0)
            valor_total_considerado += float(frete.valor_considerado or 0)
            valor_total_pago += float(frete.valor_pago or 0)

        # 2) Custos de Entrega (equivalente das Despesas Extras Nacom).
        # Paridade Nacom linhas 2132-2177: CE entra nos totais cotado/cte/
        # considerado/pago com mesmo valor (sem distincao — CE e um unico valor).
        for ce in custos_entrega:
            # CE vinculada a FT e sempre "LANÇADA" na conferencia
            # (espelha a regra Nacom: DespesaExtra com numero_documento +
            # valor + fatura_frete_id != NULL).
            if ce.numero_custo and ce.valor and ce.fatura_transportadora_id:
                status_doc = 'LANÇADO'
            else:
                status_doc = 'PENDENTE'

            documentos_status.append({
                'tipo': 'Despesa',
                'numero': ce.numero_custo or f'CE #{ce.id}',
                'descricao': ce.tipo_custo or 'Custo de Entrega',
                'valor_cotado': float(ce.valor or 0),
                'valor_cte': float(ce.valor or 0),
                'valor_considerado': float(ce.valor or 0),
                'valor_pago': float(ce.valor or 0),
                'status': status_doc,
                'cliente': 'Custo de Entrega',
                'ce_id': ce.id,
            })

            valor_total_cotado += float(ce.valor or 0)
            valor_total_cte += float(ce.valor or 0)
            valor_total_considerado += float(ce.valor or 0)
            valor_total_pago += float(ce.valor or 0)

        # Flags de bloqueio para UI (paridade Nacom)
        tem_sub_em_tratativa = any(
            doc['status'] == 'EM_TRATATIVA' for doc in documentos_status
        )
        tem_sub_rejeitado = any(
            doc['status'] == 'REJEITADO' for doc in documentos_status
        )

        # todos_aprovados: true se nao ha pendentes/tratativas/rejeitados
        if len(documentos_status) == 0:
            # Fatura vazia: considerar aprovada (mesmo comportamento Nacom)
            todos_aprovados = True
        else:
            todos_aprovados = all(
                doc['status'] in ('APROVADO', 'LANÇADO')
                for doc in documentos_status
            )

        # Gate 2: tolerancia de R$ 1,00 entre valor_total_fatura e considerado
        # (criterio identico ao Nacom fretes/routes.py:2231).
        valor_fatura = float(fatura.valor_total or 0)
        diferenca_fatura_considerado = abs(valor_fatura - valor_total_considerado)
        fatura_dentro_tolerancia = diferenca_fatura_considerado <= 1.00

        # Paridade Nacom fretes/routes.py:2243-2253
        analise_valores = {
            'valor_fatura': valor_fatura,
            'valor_cotado': valor_total_cotado,
            'valor_total_cte': valor_total_cte,
            'valor_total_considerado': valor_total_considerado,
            'valor_total_pago': valor_total_pago,
            'diferenca_fatura_considerado': diferenca_fatura_considerado,
            'fatura_dentro_tolerancia': fatura_dentro_tolerancia,
            'diferenca_considerado_pago': abs(
                valor_total_considerado - valor_total_pago
            ),
        }

        pode_aprovar = todos_aprovados and fatura_dentro_tolerancia

        return render_template(
            'carvia/faturas_transportadora/conferir.html',
            fatura=fatura,
            documentos_status=documentos_status,
            analise_valores=analise_valores,
            todos_aprovados=todos_aprovados,
            tem_sub_em_tratativa=tem_sub_em_tratativa,
            tem_sub_rejeitado=tem_sub_rejeitado,
            pode_aprovar=pode_aprovar,
        )

    @bp.route(
        '/faturas-transportadora/<int:fatura_id>/aprovar-conferencia',
        methods=['POST'],
    ) # type: ignore
    @login_required
    def aprovar_conferencia_fatura_transportadora(fatura_id): # type: ignore
        """Aprova a conferencia de uma fatura de transportadora.

        Paridade Nacom: equivalente a `fretes.aprovar_conferencia_fatura`.
        Recebe `valor_final` e `observacoes_conferencia` do form.
        Defense in depth: re-valida Gate 1 e Gate 2 server-side.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        fatura = db.session.get(CarviaFaturaTransportadora, fatura_id)
        if not fatura:
            flash('Fatura nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_faturas_transportadora'))

        from app.utils.timezone import agora_utc_naive

        # Fretes da fatura (exclui CANCELADO) — paridade Nacom, Frete e a
        # unidade de conferencia (Phase C refactor 2026-04-14)
        fretes_ativos = CarviaFrete.query.filter(
            CarviaFrete.fatura_transportadora_id == fatura_id,
            CarviaFrete.status != 'CANCELADO',
        ).all()

        # Gate 1: todos fretes APROVADO (defense in depth).
        # 3 checks: DIVERGENTE (frete reprovado), requer_aprovacao (tratativa
        # D4 pendente no AprovacaoFreteService) e ausencia de conferencia
        # individual. Espelha classificacao de status_doc na rota GET /conferir
        # para evitar bypass via POST direto.
        fretes_divergentes = [
            f for f in fretes_ativos if f.status_conferencia == 'DIVERGENTE'
        ]
        fretes_em_tratativa = [
            f for f in fretes_ativos
            if getattr(f, 'requer_aprovacao', False)
        ]
        fretes_pendentes = [
            f for f in fretes_ativos
            if f.status_conferencia not in ('APROVADO', 'DIVERGENTE')
            and not getattr(f, 'requer_aprovacao', False)
        ]
        if fretes_divergentes:
            flash(
                f'Fatura nao pode ser conferida: '
                f'{len(fretes_divergentes)} frete(s) DIVERGENTE. '
                f'Resolva em Aprovacoes antes de aprovar.',
                'danger',
            )
            return redirect(
                url_for('carvia.conferir_fatura_transportadora', fatura_id=fatura_id)
            )
        if fretes_em_tratativa:
            flash(
                f'Fatura nao pode ser conferida: '
                f'{len(fretes_em_tratativa)} frete(s) com tratativa pendente '
                f'(D4). Resolva em Aprovacoes antes de aprovar.',
                'danger',
            )
            return redirect(
                url_for('carvia.conferir_fatura_transportadora', fatura_id=fatura_id)
            )
        if fretes_pendentes:
            flash(
                f'Fatura nao pode ser conferida: '
                f'{len(fretes_pendentes)} frete(s) sem conferencia individual. '
                f'Confira cada frete antes de aprovar a fatura.',
                'danger',
            )
            return redirect(
                url_for('carvia.conferir_fatura_transportadora', fatura_id=fatura_id)
            )

        try:
            valor_final_str = request.form.get('valor_final', '').strip()
            observacoes = request.form.get('observacoes', '').strip()

            # Converte valor final (paridade Nacom: troca virgula por ponto).
            # O JS do template ja restringe a digitos e virgula antes do POST.
            if valor_final_str:
                try:
                    valor_final_float = float(
                        valor_final_str.replace(',', '.')
                    )
                except ValueError:
                    flash('Valor final invalido.', 'danger')
                    return redirect(
                        url_for(
                            'carvia.conferir_fatura_transportadora',
                            fatura_id=fatura_id,
                        )
                    )
            else:
                # Se nao informado, usa soma dos valor_pago dos Fretes + CEs.
                # Paridade Nacom fretes/routes.py:2327:
                #   valor_final_float = sum(f.valor_pago or 0 for f in fretes)
                #                       + sum(d.valor_despesa for d in despesas_extras)
                # IMPORTANTE: iterar CarviaFrete (nao Sub) porque valor_pago e
                # preenchido no form /carvia/fretes/<id>/editar. Sync frete→sub
                # garante paridade, mas Frete e a fonte canonica.
                # fretes_ativos ja foi carregado acima para os gates — reusar.
                from app.carvia.models import CarviaCustoEntrega
                soma_pago_fretes = sum(
                    float(f.valor_pago or 0) for f in fretes_ativos
                )
                soma_ces = db.session.query(
                    func.coalesce(func.sum(CarviaCustoEntrega.valor), 0)
                ).filter(
                    CarviaCustoEntrega.fatura_transportadora_id == fatura_id,
                    CarviaCustoEntrega.status != 'CANCELADO',
                ).scalar() or 0
                valor_final_float = float(soma_pago_fretes) + float(soma_ces)

            # Gate 2: tolerancia de R$ 1,00 sobre o valor final informado
            # (se usuario ajustou valor_final, a comparacao e contra esse)
            from app.carvia.services.documentos.conferencia_service import (
                ConferenciaService,
            )
            resumo = ConferenciaService().resumo_conferencia_fatura(fatura_id)
            soma_considerado = float(resumo.get('soma_considerado', 0) or 0)
            soma_custos_entrega = float(
                resumo.get('soma_custos_entrega', 0) or 0
            )
            valor_conferido_total = float(
                resumo.get(
                    'valor_conferido_total',
                    soma_considerado + soma_custos_entrega,
                ) or 0
            )
            diferenca = abs(valor_final_float - valor_conferido_total)
            if diferenca > 1.00:
                flash(
                    f'Diferenca de R$ {diferenca:.2f} entre valor final '
                    f'(R$ {valor_final_float:.2f}) e soma conferida '
                    f'(R$ {valor_conferido_total:.2f}). Tolerancia: R$ 1,00.',
                    'danger',
                )
                return redirect(
                    url_for(
                        'carvia.conferir_fatura_transportadora',
                        fatura_id=fatura_id,
                    )
                )

            # Atualiza fatura
            fatura.valor_total = valor_final_float
            fatura.status_conferencia = 'CONFERIDO'
            fatura.conferido_por = current_user.email
            fatura.conferido_em = agora_utc_naive()
            fatura.observacoes_conferencia = observacoes or None

            # Marcar fretes como conferidos (FATURADO -> CONFERIDO)
            # Phase C: iteramos fretes_ativos (ja carregado acima) em vez de subs
            for frete in fretes_ativos:
                if frete.status == 'FATURADO':
                    frete.status = 'CONFERIDO'

            db.session.commit()
            flash(
                f'Fatura {fatura.numero_fatura} conferida com sucesso! '
                f'Valor atualizado para R$ {valor_final_float:.2f}.',
                'success',
            )
            return redirect(
                url_for(
                    'carvia.detalhe_fatura_transportadora',
                    fatura_id=fatura_id,
                )
            )

        except Exception as e:
            db.session.rollback()
            logger.exception(
                f'Erro ao aprovar conferencia fatura transportadora {fatura_id}'
            )
            flash(f'Erro ao conferir fatura: {e}', 'danger')
            return redirect(
                url_for(
                    'carvia.conferir_fatura_transportadora', fatura_id=fatura_id
                )
            )

    @bp.route(
        '/faturas-transportadora/<int:fatura_id>/reabrir', methods=['POST'],
    ) # type: ignore
    @login_required
    def reabrir_fatura_transportadora(fatura_id): # type: ignore
        """Reabre uma fatura conferida (paridade Nacom).

        Recebe `motivo_reabertura` obrigatorio e prepend ao historico de
        `observacoes_conferencia`. Subs CONFERIDO voltam para FATURADO.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        fatura = db.session.get(CarviaFaturaTransportadora, fatura_id)
        if not fatura:
            flash('Fatura nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_faturas_transportadora'))

        if fatura.status_conferencia != 'CONFERIDO':
            flash(
                'Apenas faturas CONFERIDAS podem ser reabertas.', 'warning'
            )
            return redirect(url_for('carvia.listar_faturas_transportadora'))

        if fatura.status_pagamento == 'PAGO':
            flash(
                'Fatura ja paga. Desconcilie via Extrato Bancario antes '
                'de reabrir a conferencia.',
                'warning',
            )
            return redirect(
                url_for(
                    'carvia.conferir_fatura_transportadora', fatura_id=fatura_id
                )
            )

        motivo = request.form.get('motivo_reabertura', '').strip()
        if not motivo:
            flash('Informe o motivo da reabertura.', 'warning')
            return redirect(
                url_for(
                    'carvia.conferir_fatura_transportadora',
                    fatura_id=fatura_id,
                )
            )

        try:
            from app.utils.timezone import agora_utc_naive

            # Historico: prepend com timestamp + usuario + motivo.
            # Paridade Nacom (fretes/routes.py:2398): SEM .strip() no fim —
            # preserva separador \n\n entre entradas historicas para o
            # render <pre style="white-space: pre-wrap"> do template.
            agora_str = agora_utc_naive().strftime('%d/%m/%Y %H:%M')
            obs_anterior = fatura.observacoes_conferencia or ''
            fatura.observacoes_conferencia = (
                f'REABERTA EM {agora_str} por {current_user.email} '
                f'- {motivo}\n\n{obs_anterior}'
            )
            fatura.status_conferencia = 'PENDENTE'
            fatura.conferido_por = None
            fatura.conferido_em = None

            # Libera subs conferidos (CONFERIDO -> FATURADO) — legado
            subs_ativos = CarviaSubcontrato.query.filter(
                CarviaSubcontrato.fatura_transportadora_id == fatura_id,
                CarviaSubcontrato.status != 'CANCELADO',
            ).all()
            for sub in subs_ativos:
                if sub.status == 'CONFERIDO':
                    sub.status = 'FATURADO'

            # Phase C (2026-04-14): fretes tambem vao CONFERIDO em aprovar_conferencia.
            # Reverter para permitir reconferencia apos reabrir.
            fretes_ativos = CarviaFrete.query.filter(
                CarviaFrete.fatura_transportadora_id == fatura_id,
                CarviaFrete.status != 'CANCELADO',
            ).all()
            for frete in fretes_ativos:
                if frete.status == 'CONFERIDO':
                    frete.status = 'FATURADO'
                # Resetar conferencia individual tambem
                if frete.status_conferencia == 'APROVADO':
                    frete.status_conferencia = 'PENDENTE'
                    frete.conferido_por = None
                    frete.conferido_em = None

            db.session.commit()
            flash(
                f'Fatura {fatura.numero_fatura} reaberta com sucesso! '
                f'Subcontratos liberados para nova conferencia.',
                'success',
            )
            return redirect(
                url_for('carvia.listar_faturas_transportadora')
            )

        except Exception as e:
            db.session.rollback()
            logger.exception(
                f'Erro ao reabrir fatura transportadora {fatura_id}'
            )
            flash(f'Erro ao reabrir fatura: {e}', 'danger')
            return redirect(
                url_for(
                    'carvia.conferir_fatura_transportadora', fatura_id=fatura_id
                )
            )

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

        # Refator 2.1: fatura CONFERIDA bloqueia vinculacao de novas operacoes
        if fatura.status_conferencia == 'CONFERIDO':
            return jsonify({
                'sucesso': False,
                'erro': (
                    'Fatura conferida nao aceita novas operacoes. '
                    'Reabra a conferencia antes de vincular.'
                )
            }), 400

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

            # PRE-VINCULO: nova operacao pode completar cadeia para cotacao com pre-vinculo
            try:
                from app.carvia.services.financeiro.previnculo_service import (
                    CarviaPreVinculoService,
                )
                # FIX C2: SAVEPOINT isola erros do resolver da transacao da fatura.
                # Sem isso, um IntegrityError no flush do resolver polui a session
                # e o db.session.commit() subsequente da rota falha, causando
                # rollback completo da criacao da fatura (sintoma: fatura criada
                # com sucesso no UI mas some do banco).
                with db.session.begin_nested():
                    CarviaPreVinculoService.resolver_para_fatura(
                        fatura.id, current_user.email,
                    )
            except Exception as _e:
                logger.warning(
                    'Falha ao resolver pre-vinculos fatura %s: %s', fatura.id, _e
                )

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

        # Refator 2.1: fatura CONFERIDA bloqueia desvinculacao de operacoes
        if fatura.status_conferencia == 'CONFERIDO':
            return jsonify({
                'sucesso': False,
                'erro': (
                    'Fatura conferida nao permite desvincular operacoes. '
                    'Reabra a conferencia antes de alterar.'
                )
            }), 400

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
                'ctrc_numero': op.ctrc_numero,
                'nome_cliente': op.nome_cliente,
                'cnpj_cliente': op.cnpj_cliente,
                'cte_valor': float(op.cte_valor) if op.cte_valor else None,
                'status': op.status,
                'destino': f'{op.cidade_destino}/{op.uf_destino}' if op.cidade_destino else '-',
            } for op in operacoes],
        })

    # ==================== VINCULAR/DESVINCULAR CTe COMP ↔ FATURA CLIENTE ====================

    @bp.route('/faturas-cliente/<int:fatura_id>/vincular-cte-comp', methods=['POST']) # type: ignore
    @login_required
    def api_vincular_cte_comp_fatura_cliente(fatura_id): # type: ignore
        """Vincula CTe complementar a fatura cliente: status -> FATURADO, seta FK."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'sucesso': False, 'erro': 'Acesso negado'}), 403

        fatura = db.session.get(CarviaFaturaCliente, fatura_id)
        if not fatura:
            return jsonify({'sucesso': False, 'erro': 'Fatura nao encontrada'}), 404

        if fatura.status in ('PAGA', 'CANCELADA'):
            return jsonify({'sucesso': False, 'erro': f'Fatura {fatura.status} nao aceita vinculos.'}), 400

        # Refator 2.1: fatura CONFERIDA bloqueia vinculacao de novos CTe Comp
        if fatura.status_conferencia == 'CONFERIDO':
            return jsonify({
                'sucesso': False,
                'erro': (
                    'Fatura conferida nao aceita novos CTe Complementares. '
                    'Reabra a conferencia antes de vincular.'
                )
            }), 400

        data = request.get_json(silent=True) or {}
        cte_comp_id = data.get('cte_comp_id')
        if not cte_comp_id:
            return jsonify({'sucesso': False, 'erro': 'cte_comp_id obrigatorio.'}), 400

        try:
            cte_comp = db.session.query(CarviaCteComplementar).filter(
                CarviaCteComplementar.id == cte_comp_id,
                CarviaCteComplementar.status.in_(['RASCUNHO', 'EMITIDO']),
                CarviaCteComplementar.fatura_cliente_id.is_(None),
            ).with_for_update().first()

            if not cte_comp:
                return jsonify({'sucesso': False, 'erro': 'CTe complementar nao encontrado ou ja faturado.'}), 400

            cte_comp.fatura_cliente_id = fatura.id
            cte_comp.status = 'FATURADO'

            # Recalcular valor_total da fatura
            soma_ops = db.session.query(
                func.coalesce(func.sum(CarviaOperacao.cte_valor), 0)
            ).filter(CarviaOperacao.fatura_cliente_id == fatura.id).scalar()

            soma_comp = db.session.query(
                func.coalesce(func.sum(CarviaCteComplementar.cte_valor), 0)
            ).filter(CarviaCteComplementar.fatura_cliente_id == fatura.id).scalar()

            fatura.valor_total = (soma_ops or 0) + (soma_comp or 0)

            # PRE-VINCULO: novo CTe Comp pode completar cadeia para cotacao com pre-vinculo
            try:
                from app.carvia.services.financeiro.previnculo_service import (
                    CarviaPreVinculoService,
                )
                # FIX C2: SAVEPOINT isola erros do resolver da transacao da fatura.
                # Sem isso, um IntegrityError no flush do resolver polui a session
                # e o db.session.commit() subsequente da rota falha, causando
                # rollback completo da criacao da fatura (sintoma: fatura criada
                # com sucesso no UI mas some do banco).
                with db.session.begin_nested():
                    CarviaPreVinculoService.resolver_para_fatura(
                        fatura.id, current_user.email,
                    )
            except Exception as _e:
                logger.warning(
                    'Falha ao resolver pre-vinculos fatura %s: %s', fatura.id, _e
                )

            db.session.commit()

            logger.info(
                f"CTe Comp #{cte_comp_id} ({cte_comp.numero_comp}) vinculado a fatura "
                f"cliente #{fatura_id} por {current_user.email}. "
                f"Valor total: R$ {fatura.valor_total:.2f}"
            )
            return jsonify({'sucesso': True, 'valor_total': float(fatura.valor_total or 0)})

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao vincular CTe Comp #{cte_comp_id} a fatura #{fatura_id}: {e}")
            return jsonify({'sucesso': False, 'erro': str(e)}), 500

    # ==================== D5 (2026-04-19): RECALCULAR VALOR_TOTAL DA FATURA ====================

    @bp.route(
        '/faturas-cliente/<int:fatura_id>/recalcular-valor',
        methods=['POST'],
    )  # type: ignore
    @login_required
    def api_recalcular_valor_fatura_cliente(fatura_id):  # type: ignore
        """D5 (2026-04-19): recalcula valor_total da fatura = soma dos
        cte_valor das operacoes + CTe Comps vinculados.

        Gate: fatura.pode_editar() (NN3). Se fatura esta CONFERIDA/PAGA/
        CANCELADA, retorna 422. Usa lock (NN1) para evitar race com
        conciliacao.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'sucesso': False, 'erro': 'Acesso negado'}), 403

        try:
            from sqlalchemy import func as sa_func

            fatura = (
                db.session.query(CarviaFaturaCliente)
                .filter(CarviaFaturaCliente.id == fatura_id)
                .with_for_update()
                .first()
            )
            if not fatura:
                return jsonify({
                    'sucesso': False, 'erro': 'Fatura nao encontrada'
                }), 404

            pode, razao = fatura.pode_editar()
            if not pode:
                return jsonify({
                    'sucesso': False,
                    'erro': razao or 'Fatura nao pode ser editada',
                    'status': fatura.status,
                    'status_conferencia': fatura.status_conferencia,
                }), 422

            valor_anterior = float(fatura.valor_total or 0)

            soma_ops = db.session.query(
                sa_func.coalesce(sa_func.sum(CarviaOperacao.cte_valor), 0)
            ).filter(
                CarviaOperacao.fatura_cliente_id == fatura_id
            ).scalar()

            soma_comp = db.session.query(
                sa_func.coalesce(
                    sa_func.sum(CarviaCteComplementar.cte_valor), 0
                )
            ).filter(
                CarviaCteComplementar.fatura_cliente_id == fatura_id
            ).scalar()

            novo_total = float(soma_ops or 0) + float(soma_comp or 0)
            fatura.valor_total = novo_total
            db.session.commit()

            logger.info(
                'D5 recalcular_valor fatura=%s: R$%.2f -> R$%.2f '
                '(ops=%.2f + comps=%.2f)',
                fatura_id, valor_anterior, novo_total,
                float(soma_ops or 0), float(soma_comp or 0),
            )

            return jsonify({
                'sucesso': True,
                'fatura_id': fatura_id,
                'valor_anterior': valor_anterior,
                'valor_novo': novo_total,
                'soma_operacoes': float(soma_ops or 0),
                'soma_complementares': float(soma_comp or 0),
            })
        except Exception as e:
            db.session.rollback()
            logger.exception(
                'D5 recalcular_valor fatura=%s: erro %s', fatura_id, e
            )
            return jsonify({'sucesso': False, 'erro': str(e)}), 500

    @bp.route('/faturas-cliente/<int:fatura_id>/desvincular-cte-comp/<int:cte_comp_id>', methods=['POST']) # type: ignore
    @login_required
    def api_desvincular_cte_comp_fatura_cliente(fatura_id, cte_comp_id): # type: ignore
        """Desvincula CTe complementar de fatura cliente: reverte status, limpa FK."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'sucesso': False, 'erro': 'Acesso negado'}), 403

        fatura = db.session.get(CarviaFaturaCliente, fatura_id)
        if not fatura:
            return jsonify({'sucesso': False, 'erro': 'Fatura nao encontrada'}), 404

        if fatura.status in ('PAGA', 'CANCELADA'):
            return jsonify({'sucesso': False, 'erro': f'Fatura {fatura.status} nao permite desvincular.'}), 400

        # Refator 2.1: fatura CONFERIDA bloqueia desvinculacao de CTe Comp
        if fatura.status_conferencia == 'CONFERIDO':
            return jsonify({
                'sucesso': False,
                'erro': (
                    'Fatura conferida nao permite desvincular CTe Complementares. '
                    'Reabra a conferencia antes de alterar.'
                )
            }), 400

        try:
            cte_comp = db.session.query(CarviaCteComplementar).filter(
                CarviaCteComplementar.id == cte_comp_id,
                CarviaCteComplementar.fatura_cliente_id == fatura_id,
            ).with_for_update().first()

            if not cte_comp:
                return jsonify({'sucesso': False, 'erro': 'CTe complementar nao encontrado nesta fatura.'}), 404

            cte_comp.fatura_cliente_id = None
            cte_comp.status = 'EMITIDO'

            # Recalcular valor_total
            soma_ops = db.session.query(
                func.coalesce(func.sum(CarviaOperacao.cte_valor), 0)
            ).filter(CarviaOperacao.fatura_cliente_id == fatura.id).scalar()

            soma_comp = db.session.query(
                func.coalesce(func.sum(CarviaCteComplementar.cte_valor), 0)
            ).filter(CarviaCteComplementar.fatura_cliente_id == fatura.id).scalar()

            fatura.valor_total = (soma_ops or 0) + (soma_comp or 0)
            db.session.commit()

            logger.info(
                f"CTe Comp #{cte_comp_id} desvinculado de fatura cliente #{fatura_id} "
                f"por {current_user.email}"
            )
            return jsonify({'sucesso': True, 'valor_total': float(fatura.valor_total or 0)})

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao desvincular CTe Comp #{cte_comp_id} de fatura #{fatura_id}: {e}")
            return jsonify({'sucesso': False, 'erro': str(e)}), 500

    @bp.route('/api/ctes-comp-disponiveis-fatura') # type: ignore
    @login_required
    def api_ctes_comp_disponiveis_fatura(): # type: ignore
        """Lista CTe complementares disponiveis para vincular a fatura cliente (R5)."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'sucesso': False, 'erro': 'Acesso negado'}), 403

        busca = request.args.get('busca', '')
        cnpj_cliente = request.args.get('cnpj_cliente', '')

        query = db.session.query(CarviaCteComplementar).filter(
            CarviaCteComplementar.status.in_(['RASCUNHO', 'EMITIDO']),
            CarviaCteComplementar.fatura_cliente_id.is_(None),
        )

        if cnpj_cliente:
            query = query.filter(CarviaCteComplementar.cnpj_cliente == cnpj_cliente)

        if busca:
            busca_like = f'%{busca}%'
            query = query.filter(db.or_(
                CarviaCteComplementar.numero_comp.ilike(busca_like),
                CarviaCteComplementar.cte_numero.ilike(busca_like),
                CarviaCteComplementar.nome_cliente.ilike(busca_like),
                CarviaCteComplementar.observacoes.ilike(busca_like),
            ))

        comps = query.options(
            db.joinedload(CarviaCteComplementar.operacao)
        ).order_by(CarviaCteComplementar.cte_data_emissao.desc().nullslast()).limit(50).all()

        return jsonify({
            'sucesso': True,
            'ctes_comp': [{
                'id': c.id,
                'numero_comp': c.numero_comp,
                'cte_numero': c.cte_numero,
                'ctrc_numero': c.ctrc_numero,
                'nome_cliente': c.nome_cliente,
                'cnpj_cliente': c.cnpj_cliente,
                'cte_valor': float(c.cte_valor) if c.cte_valor else None,
                'status': c.status,
                'operacao_id': c.operacao_id,
                'operacao_cte_numero': c.operacao.cte_numero if c.operacao else None,
                'operacao_ctrc_numero': c.operacao.ctrc_numero if c.operacao else None,
            } for c in comps],
        })
