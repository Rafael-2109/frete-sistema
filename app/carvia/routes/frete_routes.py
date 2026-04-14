"""
Rotas de Fretes CarVia — Listagem, detalhe, edicao e vinculacao de CTe/Fatura

CarviaFrete e o eixo central: agrupa EmbarqueItems por (cnpj_emitente, cnpj_destino).
Tem 2 lados:
  - CUSTO (subcontrato): tabela Nacom, gera CarviaSubcontrato → Fatura Transportadora
  - VENDA (operacao):    tabela CarVia, gera CarviaOperacao → Fatura Cliente
"""

import logging
from flask import render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user

from app import db
from app.carvia.models import (
    CarviaFrete, CarviaOperacao, CarviaSubcontrato,
    CarviaFaturaCliente, CarviaFaturaTransportadora, CarviaNf,
)

logger = logging.getLogger(__name__)


def _build_cte_por_frete(frete_ids):
    """Retorna dict {frete_id: {'label': str, 'tipo': 'OPERACAO'|'SUBCONTRATO'|None}}.

    Resolve o "CTRC" de um CarviaFrete (que nao tem campo proprio) via 2 queries:
    1. CarviaOperacao.ctrc_numero (preferido — CTRC da venda CarVia)
    2. CarviaOperacao.cte_numero  (ex: CTe-042)
    3. CarviaSubcontrato.cte_numero (CTe do subcontrato — compra)
    4. None → template mostra "Pendente"

    Reusado em: listar_fretes_carvia, lancar_cte_carvia, nf_routes.detalhe_nf.
    Evita N+1 do padrao `frete.subcontratos.first()` no template (relationship
    e lazy='dynamic'). Inclui ORDER BY determinista e filtra subs CANCELADO.
    """
    cte_por_frete = {fid: {'label': None, 'tipo': None} for fid in frete_ids}
    if not frete_ids:
        return cte_por_frete

    # CTRC/CTe via operacao (venda)
    op_results = db.session.query(
        CarviaFrete.id, CarviaOperacao.ctrc_numero, CarviaOperacao.cte_numero,
    ).join(
        CarviaOperacao, CarviaFrete.operacao_id == CarviaOperacao.id,
    ).filter(CarviaFrete.id.in_(frete_ids)).all()
    for fid, ctrc, cte_num in op_results:
        if ctrc:
            cte_por_frete[fid] = {'label': ctrc, 'tipo': 'OPERACAO'}
        elif cte_num:
            cte_por_frete[fid] = {'label': cte_num, 'tipo': 'OPERACAO'}

    # CTe via subcontrato (compra) — preenche apenas fretes sem label ainda.
    # Order determinista por sub.id asc + filtro CANCELADO (consistente com
    # `subs_ativos` em detalhe_fatura_transportadora).
    sub_results = db.session.query(
        CarviaSubcontrato.frete_id, CarviaSubcontrato.cte_numero,
    ).filter(
        CarviaSubcontrato.frete_id.in_(frete_ids),
        CarviaSubcontrato.cte_numero.isnot(None),
        CarviaSubcontrato.status != 'CANCELADO',
    ).order_by(CarviaSubcontrato.id.asc()).all()
    for fid, cte_num in sub_results:
        if fid in cte_por_frete and not cte_por_frete[fid]['label']:
            cte_por_frete[fid] = {'label': cte_num, 'tipo': 'SUBCONTRATO'}

    return cte_por_frete


def register_frete_routes(bp):

    # ------------------------------------------------------------------
    # Listar
    # ------------------------------------------------------------------

    @bp.route('/fretes')  # type: ignore
    @login_required
    def listar_fretes_carvia():  # type: ignore
        """Lista CarviaFretes com filtros e paginacao."""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        page = request.args.get('page', 1, type=int)
        per_page = 50

        # Filtros
        filtro_id = request.args.get('id', '', type=str).strip()
        filtro_embarque = request.args.get('embarque', '', type=str).strip()
        filtro_emitente = request.args.get('emitente', '', type=str).strip()
        filtro_destino = request.args.get('destino', '', type=str).strip()
        filtro_nf = request.args.get('nf', '', type=str).strip()
        filtro_status = request.args.get('status', '', type=str).strip()
        filtro_transportadora = request.args.get('transportadora', '', type=str).strip()
        filtro_data_de = request.args.get('data_de', '', type=str).strip()
        filtro_data_ate = request.args.get('data_ate', '', type=str).strip()

        query = CarviaFrete.query

        if filtro_id:
            # CarviaFrete nao tem `ctrc_numero` proprio — o CTe real esta em
            # CarviaSubcontrato.cte_numero (compra) e CarviaOperacao.ctrc_numero/cte_numero (venda).
            # Filtra via EXISTS nesses dois + id numerico direto (backcompat).
            # Filtra subcontratos CANCELADO (consistente com a agregacao usada
            # na coluna CTRC — ver _build_cte_por_frete).
            like = f'%{filtro_id}%'
            conditions = []
            try:
                conditions.append(CarviaFrete.id == int(filtro_id))
            except ValueError:
                pass
            conditions.append(
                db.exists().where(
                    db.and_(
                        CarviaSubcontrato.frete_id == CarviaFrete.id,
                        CarviaSubcontrato.cte_numero.ilike(like),
                        CarviaSubcontrato.status != 'CANCELADO',
                    )
                )
            )
            conditions.append(
                db.exists().where(
                    db.and_(
                        CarviaOperacao.id == CarviaFrete.operacao_id,
                        db.or_(
                            CarviaOperacao.ctrc_numero.ilike(like),
                            CarviaOperacao.cte_numero.ilike(like),
                        ),
                    )
                )
            )
            query = query.filter(db.or_(*conditions))
        if filtro_embarque:
            from app.embarques.models import Embarque
            query = query.join(Embarque).filter(Embarque.numero.ilike(f'%{filtro_embarque}%'))
        if filtro_emitente:
            query = query.filter(
                db.or_(
                    CarviaFrete.cnpj_emitente.ilike(f'%{filtro_emitente}%'),
                    CarviaFrete.nome_emitente.ilike(f'%{filtro_emitente}%'),
                )
            )
        if filtro_destino:
            query = query.filter(
                db.or_(
                    CarviaFrete.cnpj_destino.ilike(f'%{filtro_destino}%'),
                    CarviaFrete.nome_destino.ilike(f'%{filtro_destino}%'),
                )
            )
        if filtro_nf:
            query = query.filter(CarviaFrete.numeros_nfs.ilike(f'%{filtro_nf}%'))
        if filtro_status:
            query = query.filter(CarviaFrete.status == filtro_status)
        transportadora_id_param = request.args.get('transportadora_id', type=int)
        if transportadora_id_param:
            from app.transportadoras.filter_utils import expandir_filtro_fk
            query = query.filter(expandir_filtro_fk(CarviaFrete.transportadora_id, transportadora_id_param))
        elif filtro_transportadora:
            from app.transportadoras.models import Transportadora
            query = query.join(Transportadora).filter(
                Transportadora.razao_social.ilike(f'%{filtro_transportadora}%')
            )
        if filtro_data_de:
            from datetime import datetime as dt_mod
            query = query.filter(CarviaFrete.criado_em >= dt_mod.strptime(filtro_data_de, '%Y-%m-%d'))
        if filtro_data_ate:
            from datetime import datetime as dt_mod
            dt_ate = dt_mod.strptime(filtro_data_ate, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            query = query.filter(CarviaFrete.criado_em <= dt_ate)

        paginacao = query.order_by(CarviaFrete.id.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        # Agregacao CTe por frete (evita N+1 do template)
        cte_por_frete = _build_cte_por_frete([f.id for f in paginacao.items])

        return render_template(
            'carvia/fretes/listar.html',
            fretes=paginacao.items,
            paginacao=paginacao,
            cte_por_frete=cte_por_frete,
            filtro_id=filtro_id,
            filtro_embarque=filtro_embarque,
            filtro_emitente=filtro_emitente,
            filtro_destino=filtro_destino,
            filtro_nf=filtro_nf,
            filtro_status=filtro_status,
            filtro_transportadora=filtro_transportadora,
            filtro_data_de=filtro_data_de,
            filtro_data_ate=filtro_data_ate,
        )

    # ------------------------------------------------------------------
    # Detalhe
    # ------------------------------------------------------------------

    @bp.route('/fretes/<int:id>')  # type: ignore
    @login_required
    def detalhe_frete_carvia(id):  # type: ignore
        """Detalhe de um CarviaFrete com paineis CUSTO e VENDA."""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        frete = CarviaFrete.query.get_or_404(id)

        # Carregar entidades vinculadas
        operacao = frete.operacao if frete.operacao_id else None
        subcontratos_list = frete.subcontratos.all()
        # Backward compat: se nao tem via frete_id mas tem via subcontrato_id (deprecated)
        if not subcontratos_list and frete.subcontrato_id:
            sub_legacy = frete.subcontrato
            subcontratos_list = [sub_legacy] if sub_legacy else []
        subcontrato = subcontratos_list[0] if subcontratos_list else None
        fatura_cliente = frete.fatura_cliente_rel if frete.fatura_cliente_id else None
        fatura_transportadora = frete.fatura_transportadora_rel if frete.fatura_transportadora_id else None

        # --- Buscar cotacao de venda via embarque (tabela CarVia) ---
        cotacao_venda = None
        cotacao_qtd_motos = 0
        frete_eh_moto = False

        if frete.embarque_id:
            from app.embarques.models import EmbarqueItem
            from app.carvia.models import CarviaCotacao

            item_cot = EmbarqueItem.query.filter(
                EmbarqueItem.embarque_id == frete.embarque_id,
                EmbarqueItem.carvia_cotacao_id.isnot(None),
                EmbarqueItem.status == 'ativo',
                EmbarqueItem.cnpj_cliente == frete.cnpj_destino,
            ).first()

            if item_cot:
                cotacao_venda = db.session.get(CarviaCotacao, item_cot.carvia_cotacao_id)

        # Determinar tipo material e pre-computar dados de moto
        if cotacao_venda:
            frete_eh_moto = (cotacao_venda.tipo_material == 'MOTO')
            if frete_eh_moto:
                cotacao_qtd_motos = cotacao_venda.qtd_total_motos
        elif operacao:
            # Fallback: detectar moto via CarviaNfVeiculo das NFs da operacao
            from app.carvia.models.documentos import CarviaNfVeiculo, CarviaOperacaoNf
            frete_eh_moto = db.session.query(
                db.exists().where(
                    db.and_(
                        CarviaNfVeiculo.nf_id == CarviaOperacaoNf.nf_id,
                        CarviaOperacaoNf.operacao_id == operacao.id,
                    )
                )
            ).scalar() or False

        # Despesas Extras (CarviaCustoEntrega) — xerox DespesaExtra Nacom
        # Mostra CEs vinculados ao frete (excluindo CANCELADOS)
        from app.carvia.models import CarviaCustoEntrega
        despesas_extras = CarviaCustoEntrega.query.filter(
            CarviaCustoEntrega.frete_id == frete.id,
            CarviaCustoEntrega.status != 'CANCELADO',
        ).order_by(CarviaCustoEntrega.criado_em.desc()).all()

        return render_template(
            'carvia/fretes/detalhe.html',
            frete=frete,
            operacao=operacao,
            subcontrato=subcontrato,
            subcontratos=subcontratos_list,
            fatura_cliente=fatura_cliente,
            fatura_transportadora=fatura_transportadora,
            cotacao_venda=cotacao_venda,
            cotacao_qtd_motos=cotacao_qtd_motos,
            frete_eh_moto=frete_eh_moto,
            despesas_extras=despesas_extras,
        )

    # ------------------------------------------------------------------
    # Editar
    # ------------------------------------------------------------------

    @bp.route('/fretes/<int:id>/editar', methods=['GET', 'POST'])  # type: ignore
    @login_required
    def editar_frete_carvia(id):  # type: ignore
        """Tela de preenchimento de CTe — espelho de fretes/editar_frete.

        Apos escolher o frete em lancar_cte_carvia, usuario preenche:
        numero_cte, valor_cte, valor_considerado, valor_pago.
        numero_cte → CarviaSubcontrato.cte_numero
        valores → CarviaFrete + sync CarviaSubcontrato
        """
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        frete = CarviaFrete.query.get_or_404(id)

        # Guard: sem fatura transportadora nao pode lancar CTe
        if not frete.fatura_transportadora_id:
            flash(
                'Este frete nao possui fatura transportadora vinculada. '
                'Para lancar CTe, vincule primeiro via Lancar CTe.',
                'danger',
            )
            return redirect(url_for('carvia.detalhe_frete_carvia', id=frete.id))

        from app.carvia.forms import CarviaEditarCteForm

        # Buscar subcontrato via novo path (frete_id) com fallback para deprecated (subcontrato_id)
        sub = frete.subcontratos.first()
        if not sub and frete.subcontrato_id:
            sub = CarviaSubcontrato.query.get(frete.subcontrato_id)
        fatura = frete.fatura_transportadora_rel

        form = CarviaEditarCteForm()

        if form.validate_on_submit():
            try:
                from app.utils.valores_brasileiros import converter_valor_brasileiro

                # Gravar numero_cte no subcontrato
                if sub:
                    sub.cte_numero = form.numero_cte.data.strip()

                # Gravar valores no frete
                frete.valor_cte = converter_valor_brasileiro(form.valor_cte.data)
                frete.valor_considerado = converter_valor_brasileiro(form.valor_considerado.data)
                frete.valor_pago = (
                    converter_valor_brasileiro(form.valor_pago.data)
                    if form.valor_pago.data else None
                )
                frete.observacoes = form.observacoes.data

                # Sincronizar CarviaFrete → CarviaSubcontrato
                if sub:
                    if frete.valor_cte:
                        sub.cte_valor = frete.valor_cte
                        sub.valor_acertado = frete.valor_cte
                    if frete.valor_considerado:
                        sub.valor_considerado = frete.valor_considerado

                db.session.commit()
                flash('Frete atualizado com sucesso!', 'success')

                # Detectar acao do botao
                acao = request.form.get('acao')
                if acao == 'salvar_e_lancar_cte':
                    return redirect(url_for(
                        'carvia.lancar_cte_carvia',
                        fatura_id=frete.fatura_transportadora_id,
                    ))
                elif acao == 'salvar_e_visualizar_fatura':
                    return redirect(url_for(
                        'carvia.detalhe_fatura_transportadora',
                        fatura_id=frete.fatura_transportadora_id,
                    ))
                else:
                    return redirect(url_for('carvia.detalhe_frete_carvia', id=frete.id))

            except Exception as e:
                db.session.rollback()
                logger.exception(f'Erro ao atualizar frete CarVia #{id}: {e}')
                flash(f'Erro ao atualizar frete: {e}', 'danger')

        elif request.method == 'GET':
            # Pre-popular form com dados existentes
            if sub and sub.cte_numero:
                form.numero_cte.data = sub.cte_numero
            if frete.valor_cte:
                form.valor_cte.data = f'{frete.valor_cte:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
            if frete.valor_considerado:
                form.valor_considerado.data = f'{frete.valor_considerado:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
            if frete.valor_pago:
                form.valor_pago.data = f'{frete.valor_pago:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
            if frete.observacoes:
                form.observacoes.data = frete.observacoes

        return render_template(
            'carvia/fretes/editar.html',
            frete=frete,
            form=form,
            sub=sub,
            fatura=fatura,
        )

    # ------------------------------------------------------------------
    # Backfill Frete (criar CarviaFrete retroativamente)
    # ------------------------------------------------------------------

    @bp.route('/fretes/backfill', methods=['GET', 'POST'])  # type: ignore
    @login_required
    def backfill_frete_carvia():  # type: ignore
        """Criar CarviaFrete retroativamente para NFs sem embarque.

        GET: Exibe NFs com mesmo emitente+destinatario + parametros da tabela.
        POST: Cria CarviaFrete com parametros (possivelmente editados).
        """
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        nf_id = request.args.get('nf_id', type=int)

        if request.method == 'GET':
            if not nf_id:
                flash('NF semente nao informada.', 'danger')
                return redirect(url_for('carvia.listar_nfs'))

            seed_nf = CarviaNf.query.get_or_404(nf_id)
            if seed_nf.status != 'ATIVA':
                flash('NF cancelada nao pode ser usada como semente.', 'danger')
                return redirect(url_for('carvia.detalhe_nf', nf_id=nf_id))

            # Buscar todas NFs com mesmo emitente + destinatario
            todas_nfs = CarviaNf.query.filter(
                CarviaNf.cnpj_emitente == seed_nf.cnpj_emitente,
                CarviaNf.cnpj_destinatario == seed_nf.cnpj_destinatario,
                CarviaNf.status == 'ATIVA',
            ).order_by(CarviaNf.criado_em.desc()).all()

            # Carregar operacoes vinculadas para cada NF (CTe CarVia info)
            from app.carvia.models import CarviaOperacaoNf
            nf_operacoes = {}
            operacao_ids_set = set()
            for nf in todas_nfs:
                junctions = CarviaOperacaoNf.query.filter_by(nf_id=nf.id).all()
                ops = []
                for j in junctions:
                    op = CarviaOperacao.query.get(j.operacao_id)
                    if op:
                        ops.append(op)
                        operacao_ids_set.add(op.id)
                nf_operacoes[nf.id] = ops

            # Auto-link: se exatamente 1 CarviaOperacao compartilhada
            auto_operacao = None
            if len(operacao_ids_set) == 1:
                auto_operacao = CarviaOperacao.query.get(operacao_ids_set.pop())

            valor_venda_sugerido = None
            if auto_operacao and auto_operacao.cte_valor:
                valor_venda_sugerido = float(auto_operacao.cte_valor)

            # Calcular peso cubado por NF (motos com modelo cadastrado)
            peso_cubado_por_nf = {}
            try:
                from app.carvia.services.pricing.moto_recognition_service import MotoRecognitionService
                moto_svc = MotoRecognitionService()
                nf_ids = [nf.id for nf in todas_nfs]
                peso_cubado_por_nf = moto_svc.calcular_peso_cubado_batch(nf_ids) if nf_ids else {}
            except Exception as e:
                logger.warning('Erro ao calcular peso cubado batch: %s', e)

            return render_template(
                'carvia/fretes/backfill.html',
                seed_nf=seed_nf,
                todas_nfs=todas_nfs,
                nf_operacoes=nf_operacoes,
                auto_operacao=auto_operacao,
                valor_venda_sugerido=valor_venda_sugerido,
                peso_cubado_por_nf=peso_cubado_por_nf,
            )

        # --- POST: Criar CarviaFrete ---
        from app.utils.timezone import agora_utc_naive
        from app.utils.valores_brasileiros import converter_valor_brasileiro

        seed_nf_id = request.form.get('seed_nf_id', type=int)
        if not seed_nf_id:
            flash('NF semente nao informada.', 'danger')
            return redirect(url_for('carvia.listar_nfs'))

        seed_nf = CarviaNf.query.get_or_404(seed_nf_id)
        nf_ids = request.form.getlist('nf_ids', type=int)
        tipo_carga = request.form.get('tipo_carga', '').strip()
        transportadora_id = request.form.get('transportadora_id', type=int)

        # Validacoes
        if not nf_ids:
            flash('Selecione pelo menos uma NF.', 'danger')
            return redirect(url_for('carvia.backfill_frete_carvia', nf_id=seed_nf_id))

        if tipo_carga not in ('FRACIONADA', 'DIRETA'):
            flash('Tipo de carga invalido.', 'danger')
            return redirect(url_for('carvia.backfill_frete_carvia', nf_id=seed_nf_id))

        if not transportadora_id:
            flash('Selecione uma transportadora.', 'danger')
            return redirect(url_for('carvia.backfill_frete_carvia', nf_id=seed_nf_id))

        # Carregar NFs selecionadas
        selected_nfs = CarviaNf.query.filter(
            CarviaNf.id.in_(nf_ids),
            CarviaNf.status == 'ATIVA',
        ).all()

        if not selected_nfs:
            flash('Nenhuma NF ativa selecionada.', 'danger')
            return redirect(url_for('carvia.backfill_frete_carvia', nf_id=seed_nf_id))

        # Validar UF destino
        uf_destino = seed_nf.uf_destinatario or ''
        cidade_destino = seed_nf.cidade_destinatario or ''
        if not uf_destino:
            flash('NF semente sem UF destinatario — nao e possivel criar frete.', 'danger')
            return redirect(url_for('carvia.backfill_frete_carvia', nf_id=seed_nf_id))

        # Dedup: verificar overlap com fretes backfill existentes (excluir cancelados)
        submitted_nf_nums = {nf.numero_nf for nf in selected_nfs}
        fretes_existentes = CarviaFrete.query.filter(
            CarviaFrete.embarque_id.is_(None),
            CarviaFrete.cnpj_emitente == seed_nf.cnpj_emitente,
            CarviaFrete.cnpj_destino == seed_nf.cnpj_destinatario,
            CarviaFrete.status != 'CANCELADO',
        ).all()

        for fe in fretes_existentes:
            existing_nums = set((fe.numeros_nfs or '').split(','))
            overlap = submitted_nf_nums & existing_nums
            if overlap:
                flash(
                    f'NFs {", ".join(sorted(overlap))} ja existem no frete backfill #{fe.id}.',
                    'danger',
                )
                return redirect(url_for('carvia.backfill_frete_carvia', nf_id=seed_nf_id))

        # Agregar totais
        peso_total = sum(float(nf.peso_bruto or 0) for nf in selected_nfs)
        valor_total_nfs = sum(float(nf.valor_total or 0) for nf in selected_nfs)
        numeros_nfs = ','.join(nf.numero_nf for nf in selected_nfs if nf.numero_nf)

        # Obter valor_cotado (custo)
        valor_cotado_str = request.form.get('valor_cotado', '').strip()
        try:
            valor_cotado = converter_valor_brasileiro(valor_cotado_str) if valor_cotado_str else 0
        except (ValueError, TypeError):
            valor_cotado = 0

        # Obter valor_venda
        valor_venda_str = request.form.get('valor_venda', '').strip()
        try:
            valor_venda = converter_valor_brasileiro(valor_venda_str) if valor_venda_str else None
        except (ValueError, TypeError):
            valor_venda = None

        # Auto-link operacao (re-validar no POST)
        from app.carvia.models import CarviaOperacaoNf
        operacao_ids_post = set()
        for nf in selected_nfs:
            junctions = CarviaOperacaoNf.query.filter_by(nf_id=nf.id).all()
            for j in junctions:
                operacao_ids_post.add(j.operacao_id)
        auto_operacao_id = operacao_ids_post.pop() if len(operacao_ids_post) == 1 else None

        try:
            frete = CarviaFrete(
                embarque_id=None,  # backfill — sem embarque
                transportadora_id=transportadora_id,
                cnpj_emitente=seed_nf.cnpj_emitente,
                nome_emitente=seed_nf.nome_emitente or '',
                cnpj_destino=seed_nf.cnpj_destinatario,
                nome_destino=seed_nf.nome_destinatario or '',
                uf_destino=uf_destino,
                cidade_destino=cidade_destino,
                tipo_carga=tipo_carga,
                peso_total=peso_total,
                valor_total_nfs=valor_total_nfs,
                quantidade_nfs=len(selected_nfs),
                numeros_nfs=numeros_nfs,
                valor_cotado=float(valor_cotado) if valor_cotado else 0,
                valor_considerado=float(valor_cotado) if valor_cotado else 0,
                valor_venda=float(valor_venda) if valor_venda else None,
                operacao_id=auto_operacao_id,
                status='PENDENTE',
                criado_em=agora_utc_naive(),
                criado_por=current_user.email,
                observacoes=request.form.get('observacoes', '').strip() or 'Backfill manual',
            )

            # Salvar snapshot da tabela (parametros possivelmente editados)
            tabela_campos = {
                'tabela_nome_tabela': 'tabela_nome_tabela',
                'tabela_valor_kg': 'tabela_valor_kg',
                'tabela_percentual_valor': 'tabela_percentual_valor',
                'tabela_frete_minimo_valor': 'tabela_frete_minimo_valor',
                'tabela_frete_minimo_peso': 'tabela_frete_minimo_peso',
                'tabela_icms_proprio': 'tabela_icms_proprio',
                'tabela_icms_incluso': 'tabela_icms_incluso',
                'tabela_percentual_gris': 'tabela_percentual_gris',
                'tabela_gris_minimo': 'tabela_gris_minimo',
                'tabela_pedagio_por_100kg': 'tabela_pedagio_por_100kg',
                'tabela_valor_tas': 'tabela_valor_tas',
                'tabela_percentual_adv': 'tabela_percentual_adv',
                'tabela_adv_minimo': 'tabela_adv_minimo',
                'tabela_percentual_rca': 'tabela_percentual_rca',
                'tabela_valor_despacho': 'tabela_valor_despacho',
                'tabela_valor_cte': 'tabela_valor_cte',
            }
            for form_name, attr_name in tabela_campos.items():
                raw = request.form.get(form_name, '').strip()
                if raw:
                    if attr_name == 'tabela_nome_tabela':
                        setattr(frete, attr_name, raw)
                    elif attr_name == 'tabela_icms_incluso':
                        setattr(frete, attr_name, raw.lower() in ('true', '1', 'on'))
                    else:
                        try:
                            setattr(frete, attr_name, float(raw))
                        except (ValueError, TypeError):
                            pass

            db.session.add(frete)

            # Propagar fatura_cliente_id se operacao auto-linkada tiver fatura
            if auto_operacao_id:
                op_backfill = db.session.get(CarviaOperacao, auto_operacao_id)
                if op_backfill and op_backfill.fatura_cliente_id:
                    frete.fatura_cliente_id = op_backfill.fatura_cliente_id

            db.session.commit()

            flash(f'Frete backfill #{frete.id} criado com sucesso!', 'success')
            return redirect(url_for('carvia.detalhe_frete_carvia', id=frete.id))

        except Exception as e:
            db.session.rollback()
            logger.exception('Erro ao criar frete backfill: %s', e)
            flash(f'Erro ao criar frete: {e}', 'danger')
            return redirect(url_for('carvia.backfill_frete_carvia', nf_id=seed_nf_id))

    # ------------------------------------------------------------------
    # Lancar CTe (busca por NF)
    # ------------------------------------------------------------------

    @bp.route('/fretes/lancar-cte', methods=['GET'])  # type: ignore
    @login_required
    def lancar_cte_carvia():  # type: ignore
        """Busca CarviaFrete por NF para vincular CTe (CUSTO ou VENDA).

        Tabs: CUSTO (Subcontrato+Fatura) | VENDA (Operacao).
        Param ?tipo=venda controla tab ativa.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        # Faturas transportadora disponiveis (nao conferidas)
        faturas = CarviaFaturaTransportadora.query.filter(
            CarviaFaturaTransportadora.status_conferencia != 'CONFERIDO'
        ).order_by(
            CarviaFaturaTransportadora.id.desc()
        ).limit(50).all()

        fatura_id = request.args.get('fatura_id', type=int)
        numero_nf = request.args.get('nf', '').strip()
        tipo = request.args.get('tipo', 'custo').strip()
        fretes_encontrados = []

        if numero_nf:
            # Busca CarviaFretes que contem essa NF
            fretes_encontrados = CarviaFrete.query.filter(
                CarviaFrete.numeros_nfs.ilike(f'%{numero_nf}%')
            ).order_by(CarviaFrete.id.desc()).all()

        # Pre-computa IDs do grupo empresarial por transportadora
        # para matching fatura↔frete (grupo > prefixo CNPJ > exato)
        grupo_ids_por_transp = {}
        if fretes_encontrados and tipo != 'venda':
            from app.utils.grupo_empresarial import GrupoEmpresarialService
            grupo_svc = GrupoEmpresarialService()
            transp_ids_vistos = set()
            for frete in fretes_encontrados:
                if frete.transportadora_id and frete.transportadora_id not in transp_ids_vistos:
                    transp_ids_vistos.add(frete.transportadora_id)
                    grupo_ids_por_transp[frete.transportadora_id] = set(
                        grupo_svc.obter_transportadoras_grupo(frete.transportadora_id)
                    )

        # Agregacao CTe por frete (evita N+1 no template que antes chamava
        # `frete.subcontratos.first()` em loop — lazy='dynamic')
        cte_por_frete = _build_cte_por_frete([f.id for f in fretes_encontrados])

        return render_template(
            'carvia/fretes/lancar_cte.html',
            faturas=faturas,
            fatura_id=fatura_id,
            numero_nf=numero_nf,
            tipo=tipo,
            fretes_encontrados=fretes_encontrados,
            grupo_ids_por_transp=grupo_ids_por_transp,
            cte_por_frete=cte_por_frete,
        )

    # ------------------------------------------------------------------
    # Processar CTe Subcontrato (vincula Frete+Sub a Fatura)
    # Espelho de fretes/routes.py processar_cte_frete_existente
    # ------------------------------------------------------------------

    @bp.route('/fretes/processar-cte-subcontrato', methods=['POST'])  # type: ignore
    @login_required
    def processar_cte_subcontrato():  # type: ignore
        """CRIA CarviaSubcontrato e vincula a CarviaFrete + CarviaFaturaTransportadora.

        Fluxo identico ao Nacom (processar_cte_frete_existente):
        Fatura criada sem vinculos → CTe criado dentro da Fatura vinculando fretes.
        Cadeia: FaturaTransportadora ← CarviaSubcontrato ← CarviaFrete
        """
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        frete_id = request.form.get('frete_id', type=int)
        fatura_id = request.form.get('fatura_id', type=int)

        if not frete_id:
            flash('ID do frete nao informado.', 'danger')
            return redirect(url_for('carvia.lancar_cte_carvia'))

        if not fatura_id:
            flash('Selecione uma fatura transportadora.', 'danger')
            return redirect(url_for('carvia.lancar_cte_carvia'))

        try:
            frete = CarviaFrete.query.get_or_404(frete_id)
            fatura = CarviaFaturaTransportadora.query.get_or_404(fatura_id)

            # Validar que frete nao esta ja vinculado a outra fatura
            if frete.fatura_transportadora_id and frete.fatura_transportadora_id != fatura_id:
                fatura_atual = CarviaFaturaTransportadora.query.get(frete.fatura_transportadora_id)
                flash(
                    f'Frete #{frete.id} ja esta vinculado a fatura '
                    f'{fatura_atual.numero_fatura if fatura_atual else frete.fatura_transportadora_id}. '
                    f'Desanexe primeiro.',
                    'warning',
                )
                return redirect(url_for('carvia.lancar_cte_carvia', fatura_id=fatura_id))

            # Validar transportadora match (grupo empresarial > prefixo CNPJ > exato)
            if frete.transportadora_id != fatura.transportadora_id:
                from app.utils.grupo_empresarial import GrupoEmpresarialService
                from app.transportadoras.models import Transportadora
                grupo_ids = set(GrupoEmpresarialService().obter_transportadoras_grupo(frete.transportadora_id))

                if fatura.transportadora_id in grupo_ids:
                    flash(
                        'Transportadoras diferentes mas do mesmo grupo. Vinculacao permitida.',
                        'info',
                    )
                else:
                    transp_frete = Transportadora.query.get(frete.transportadora_id)
                    transp_fatura = Transportadora.query.get(fatura.transportadora_id)
                    nome_frete = transp_frete.razao_social if transp_frete else str(frete.transportadora_id)
                    nome_fatura = transp_fatura.razao_social if transp_fatura else str(fatura.transportadora_id)
                    flash(
                        f'Transportadora da fatura ({nome_fatura}) e diferente da transportadora do frete ({nome_frete}).',
                        'danger',
                    )
                    return redirect(url_for('carvia.lancar_cte_carvia', fatura_id=fatura_id))

            # Validar que fatura nao esta conferida
            if fatura.status_conferencia == 'CONFERIDO':
                flash('Fatura ja conferida. Nao e possivel vincular novos CTes.', 'danger')
                return redirect(url_for('carvia.lancar_cte_carvia', fatura_id=fatura_id))

            # === CRIAR CarviaSubcontrato (se nao existe) ===
            from app.utils.timezone import agora_utc_naive
            from decimal import Decimal

            # Verificar se ja tem subcontrato vinculado (novo path via frete_id)
            sub_existente = frete.subcontratos.first()
            # Fallback deprecated
            if not sub_existente and frete.subcontrato_id:
                sub_existente = CarviaSubcontrato.query.get(frete.subcontrato_id)

            if sub_existente:
                # Subcontrato ja existe (criado anteriormente) — reusar
                sub = sub_existente
            else:
                # CRIAR novo CarviaSubcontrato
                # cte_numero=None — usuario preenche na tela seguinte (editar_frete_carvia)
                sub = CarviaSubcontrato(
                    operacao_id=frete.operacao_id,  # pode ser NULL
                    transportadora_id=frete.transportadora_id,
                    cte_numero=None,
                    valor_cotado=Decimal(str(frete.valor_cotado)) if frete.valor_cotado else None,
                    fatura_transportadora_id=fatura.id,
                    status='PENDENTE',
                    criado_por=current_user.email,
                    criado_em=agora_utc_naive(),
                    observacoes=f'Criado via Lancar CTe — frete #{frete.id}',
                    frete_id=frete.id,  # N:1 — novo path
                )
                db.session.add(sub)
                db.session.flush()  # sub.id disponivel

                # Backward compat: popular deprecated FK tambem
                frete.subcontrato_id = sub.id

            # === VINCULAR ===
            # 1. Subcontrato → Fatura (se ainda nao vinculado)
            if not sub.fatura_transportadora_id:
                sub.fatura_transportadora_id = fatura.id
                sub.status = 'FATURADO'

            # 2. CarviaFrete → Fatura
            frete.fatura_transportadora_id = fatura.id

            # 3. valor_cte fica vazio — usuario preenche na tela de edicao
            # valor_considerado inicia com valor_cotado (editavel)
            if not frete.valor_considerado and frete.valor_cotado:
                frete.valor_considerado = frete.valor_cotado

            db.session.flush()

            # 4. Gerar itens de detalhe da fatura
            from app.carvia.services.documentos.linking_service import LinkingService
            linker = LinkingService()
            linker.criar_itens_fatura_transportadora_incremental(fatura.id, [sub.id])

            db.session.commit()

            flash(
                f'Frete #{frete.id} vinculado a fatura {fatura.numero_fatura}. '
                f'Preencha os dados do CTe.',
                'success',
            )
            return redirect(url_for('carvia.editar_frete_carvia', id=frete.id))

        except Exception as e:
            db.session.rollback()
            logger.exception(f'Erro ao processar CTe subcontrato: {e}')
            flash(f'Erro ao processar CTe: {e}', 'danger')
            return redirect(url_for('carvia.lancar_cte_carvia', fatura_id=fatura_id))

    # ------------------------------------------------------------------
    # Processar CTe Operacao (cria CarviaOperacao e vincula ao Frete)
    # Lado VENDA — espelho do processar_cte_subcontrato (lado CUSTO)
    # ------------------------------------------------------------------

    @bp.route('/fretes/processar-cte-operacao', methods=['POST'])  # type: ignore
    @login_required
    def processar_cte_operacao():  # type: ignore
        """CRIA CarviaOperacao e vincula ao CarviaFrete (lado VENDA).

        Diferente do CUSTO, nao requer fatura — R12 diz que CTe e criado
        antes da fatura no lado VENDA. Campos derivados do frete.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        frete_id = request.form.get('frete_id', type=int)

        if not frete_id:
            flash('ID do frete nao informado.', 'danger')
            return redirect(url_for('carvia.lancar_cte_carvia', tipo='venda'))

        try:
            frete = CarviaFrete.query.get_or_404(frete_id)

            # Validar que frete nao tem operacao ja vinculada
            if frete.operacao_id:
                op_existente = CarviaOperacao.query.get(frete.operacao_id)
                flash(
                    f'Frete #{frete.id} ja possui CTe CarVia vinculado '
                    f'({op_existente.cte_numero if op_existente else frete.operacao_id}).',
                    'warning',
                )
                return redirect(url_for('carvia.detalhe_frete_carvia', id=frete.id))

            # === CRIAR CarviaOperacao ===
            from app.utils.timezone import agora_utc_naive
            from decimal import Decimal

            op = CarviaOperacao(
                cnpj_cliente=frete.cnpj_destino,
                nome_cliente=frete.nome_destino,
                uf_destino=frete.uf_destino,
                cidade_destino=frete.cidade_destino,
                cte_numero=CarviaOperacao.gerar_numero_cte(),
                cte_valor=Decimal(str(frete.valor_venda)) if frete.valor_venda else None,
                tipo_entrada='MANUAL_SEM_CTE',
                status='RASCUNHO',
                peso_bruto=frete.peso_total if frete.peso_total else None,
                valor_mercadoria=frete.valor_total_nfs if frete.valor_total_nfs else None,
                criado_por=current_user.email,
                criado_em=agora_utc_naive(),
                observacoes=f'Criado via Lancar CTe CarVia — frete #{frete.id}',
            )
            db.session.add(op)
            db.session.flush()  # op.id disponivel

            # Vincular operacao ao frete
            frete.operacao_id = op.id

            # Auto-preencher valor_venda se nao preenchido
            if op.cte_valor and not frete.valor_venda:
                frete.valor_venda = float(op.cte_valor)

            # Criar junctions CarviaOperacaoNf para NFs do frete
            if frete.numeros_nfs:
                from app.carvia.models import CarviaOperacaoNf
                nfs_lista = [nf.strip() for nf in frete.numeros_nfs.split(',') if nf.strip()]
                datas_nfs = []
                for nf_num in nfs_lista:
                    carvia_nf = CarviaNf.query.filter_by(
                        numero_nf=nf_num, status='ATIVA'
                    ).first()
                    if carvia_nf:
                        if carvia_nf.data_emissao:
                            datas_nfs.append(carvia_nf.data_emissao)
                        existe = CarviaOperacaoNf.query.filter_by(
                            operacao_id=op.id, nf_id=carvia_nf.id
                        ).first()
                        if not existe:
                            junction = CarviaOperacaoNf(
                                operacao_id=op.id, nf_id=carvia_nf.id
                            )
                            db.session.add(junction)

                # Preencher data emissao do CTe com a maior data das NFs
                if datas_nfs and not op.cte_data_emissao:
                    op.cte_data_emissao = max(datas_nfs)

            db.session.commit()

            flash(
                f'CTe CarVia {op.cte_numero} criado e vinculado ao frete #{frete.id}.',
                'success',
            )
            return redirect(url_for('carvia.detalhe_frete_carvia', id=frete.id))

        except Exception as e:
            db.session.rollback()
            logger.exception(f'Erro ao processar CTe operacao: {e}')
            flash(f'Erro ao processar CTe CarVia: {e}', 'danger')
            return redirect(url_for('carvia.lancar_cte_carvia', tipo='venda'))

    # ------------------------------------------------------------------
    # Vincular CTe Subcontrato ao frete
    # ------------------------------------------------------------------

    @bp.route('/fretes/<int:id>/vincular-subcontrato', methods=['POST'])  # type: ignore
    @login_required
    def vincular_subcontrato_frete(id):  # type: ignore
        """Vincula um CarviaSubcontrato ao CarviaFrete."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        frete = CarviaFrete.query.get_or_404(id)
        subcontrato_id = request.form.get('subcontrato_id', type=int)

        if not subcontrato_id:
            flash('Subcontrato nao informado.', 'danger')
            return redirect(url_for('carvia.detalhe_frete_carvia', id=id))

        sub = CarviaSubcontrato.query.get_or_404(subcontrato_id)
        # N:1 — novo path via frete_id
        sub.frete_id = frete.id
        # Backward compat: popular deprecated FK tambem
        frete.subcontrato_id = sub.id

        # Atualizar valor_cte com o valor do subcontrato
        if sub.valor_final:
            frete.valor_cte = float(sub.valor_final)

        db.session.commit()
        flash(f'CTe Subcontrato {sub.cte_numero} vinculado ao frete.', 'success')
        return redirect(url_for('carvia.detalhe_frete_carvia', id=id))

    # ------------------------------------------------------------------
    # Vincular CTe CarVia (Operacao) ao frete
    # ------------------------------------------------------------------

    @bp.route('/fretes/<int:id>/vincular-operacao', methods=['POST'])  # type: ignore
    @login_required
    def vincular_operacao_frete(id):  # type: ignore
        """Vincula uma CarviaOperacao ao CarviaFrete."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        frete = CarviaFrete.query.get_or_404(id)
        operacao_id = request.form.get('operacao_id', type=int)

        if not operacao_id:
            flash('Operacao nao informada.', 'danger')
            return redirect(url_for('carvia.detalhe_frete_carvia', id=id))

        op = CarviaOperacao.query.get_or_404(operacao_id)

        # Guard: nao reassociar se frete ja tem operacao diferente
        if frete.operacao_id and frete.operacao_id != op.id:
            flash('Frete ja possui CTe CarVia vinculado.', 'warning')
            return redirect(url_for('carvia.detalhe_frete_carvia', id=id))

        frete.operacao_id = op.id

        # Atualizar valor_venda com o valor do CTe CarVia
        if op.cte_valor:
            frete.valor_venda = float(op.cte_valor)

        # Propagar fatura_cliente_id se operacao ja tiver fatura vinculada
        # e frete ainda nao tem fatura (evita sobrescrever silenciosamente)
        if op.fatura_cliente_id and not frete.fatura_cliente_id:
            frete.fatura_cliente_id = op.fatura_cliente_id

        db.session.commit()
        flash(f'CTe CarVia {op.cte_numero} vinculado ao frete.', 'success')
        return redirect(url_for('carvia.detalhe_frete_carvia', id=id))

    # ------------------------------------------------------------------
    # Desvincular CTe Subcontrato do frete (fluxo reverso CUSTO)
    # ------------------------------------------------------------------

    @bp.route('/fretes/<int:id>/desvincular-subcontrato', methods=['POST'])  # type: ignore
    @login_required
    def desvincular_subcontrato_frete(id):  # type: ignore
        """Desvincula CarviaSubcontrato + FaturaTransportadora do CarviaFrete."""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        frete = CarviaFrete.query.get_or_404(id)

        # Buscar subcontrato via novo path (frete_id) com fallback deprecated
        sub = frete.subcontratos.first()
        if not sub and frete.subcontrato_id:
            sub = CarviaSubcontrato.query.get(frete.subcontrato_id)

        if not sub:
            flash('Frete nao possui CTe Subcontrato vinculado.', 'warning')
            return redirect(url_for('carvia.detalhe_frete_carvia', id=id))

        # Guard: fatura conferida bloqueia
        if frete.fatura_transportadora_id:
            fat = CarviaFaturaTransportadora.query.get(frete.fatura_transportadora_id)
            if fat and fat.status_conferencia == 'CONFERIDO':
                flash('Nao e possivel desvincular — fatura transportadora ja conferida.', 'danger')
                return redirect(url_for('carvia.detalhe_frete_carvia', id=id))

        try:
            # Limpar FK novo (frete_id) no subcontrato
            # Status reverte para PENDENTE: subcontratos criados via processar_cte_subcontrato
            # nunca passaram pelo fluxo manual de COTADO→CONFIRMADO.
            # (diferente de fatura_routes.py que reverte para CONFIRMADO — la o sub
            # foi confirmado manualmente antes de ser anexado a fatura)
            sub.frete_id = None
            sub.fatura_transportadora_id = None
            sub.status = 'PENDENTE'

            # Limpar FKs no frete (deprecated + valores)
            frete.subcontrato_id = None
            frete.fatura_transportadora_id = None
            frete.valor_cte = None
            frete.valor_considerado = None
            frete.valor_pago = None

            db.session.commit()
            logger.info(
                'CTe Subcontrato desvinculado do frete #%d por %s',
                id, current_user.email,
            )
            flash('CTe Subcontrato desvinculado com sucesso.', 'success')

        except Exception as e:
            db.session.rollback()
            logger.exception(f'Erro ao desvincular subcontrato do frete #{id}: {e}')
            flash(f'Erro ao desvincular: {e}', 'danger')

        return redirect(url_for('carvia.detalhe_frete_carvia', id=id))

    # ------------------------------------------------------------------
    # Desvincular CTe CarVia (Operacao) do frete (fluxo reverso VENDA)
    # ------------------------------------------------------------------

    @bp.route('/fretes/<int:id>/desvincular-operacao', methods=['POST'])  # type: ignore
    @login_required
    def desvincular_operacao_frete(id):  # type: ignore
        """Desvincula CarviaOperacao do CarviaFrete."""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        frete = CarviaFrete.query.get_or_404(id)

        if not frete.operacao_id:
            flash('Frete nao possui CTe CarVia vinculado.', 'warning')
            return redirect(url_for('carvia.detalhe_frete_carvia', id=id))

        # Guard: fatura cliente impede
        if frete.fatura_cliente_id:
            flash('Nao e possivel desvincular — frete vinculado a fatura cliente.', 'danger')
            return redirect(url_for('carvia.detalhe_frete_carvia', id=id))

        try:
            frete.operacao_id = None

            db.session.commit()
            logger.info(
                'CTe CarVia desvinculado do frete #%d por %s',
                id, current_user.email,
            )
            flash('CTe CarVia desvinculado com sucesso.', 'success')

        except Exception as e:
            db.session.rollback()
            logger.exception(f'Erro ao desvincular operacao do frete #{id}: {e}')
            flash(f'Erro ao desvincular: {e}', 'danger')

        return redirect(url_for('carvia.detalhe_frete_carvia', id=id))

    # ------------------------------------------------------------------
    # Cancelar frete
    # ------------------------------------------------------------------

    @bp.route('/fretes/<int:id>/cancelar', methods=['POST'])  # type: ignore
    @login_required
    def cancelar_frete_carvia(id):  # type: ignore
        """Cancela um CarviaFrete."""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        frete = CarviaFrete.query.get_or_404(id)

        if frete.fatura_cliente_id or frete.fatura_transportadora_id:
            flash('Nao e possivel cancelar frete vinculado a fatura.', 'danger')
            return redirect(url_for('carvia.detalhe_frete_carvia', id=id))

        frete.status = 'CANCELADO'
        db.session.commit()
        flash('Frete cancelado.', 'warning')
        return redirect(url_for('carvia.detalhe_frete_carvia', id=id))

    # ------------------------------------------------------------------
    # API: Buscar CTes por NF (AJAX)
    # ------------------------------------------------------------------

    @bp.route('/api/fretes/buscar-ctes', methods=['POST'])  # type: ignore
    @login_required
    def api_buscar_ctes_frete():  # type: ignore
        """Busca CTes Subcontrato/CarVia por numero NF (AJAX)."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        data = request.get_json() or {}
        numero_nf = data.get('numero_nf', '').strip()
        tipo = data.get('tipo', 'subcontrato')  # subcontrato | operacao

        if not numero_nf:
            return jsonify({'resultados': []})

        # Busca CarviaNf pela NF
        carvia_nf = CarviaNf.query.filter_by(numero_nf=numero_nf, status='ATIVA').first()
        if not carvia_nf:
            return jsonify({'resultados': [], 'mensagem': f'NF {numero_nf} nao encontrada'})

        resultados = []
        from app.carvia.models import CarviaOperacaoNf

        # Busca operacoes vinculadas a esta NF
        junctions = CarviaOperacaoNf.query.filter_by(nf_id=carvia_nf.id).all()

        for j in junctions:
            if tipo == 'subcontrato':
                subs = CarviaSubcontrato.query.filter_by(operacao_id=j.operacao_id).all()
                for sub in subs:
                    resultados.append({
                        'id': sub.id,
                        'tipo': 'subcontrato',
                        'cte_numero': sub.cte_numero,
                        'transportadora': sub.transportadora.razao_social if sub.transportadora else '',
                        'valor': float(sub.valor_final) if sub.valor_final else 0,
                        'status': sub.status,
                    })
            else:
                op = CarviaOperacao.query.get(j.operacao_id)
                if op:
                    resultados.append({
                        'id': op.id,
                        'tipo': 'operacao',
                        'cte_numero': op.cte_numero,
                        'cliente': op.nome_cliente or '',
                        'valor': float(op.cte_valor) if op.cte_valor else 0,
                        'status': op.status,
                    })

        return jsonify({'resultados': resultados})
