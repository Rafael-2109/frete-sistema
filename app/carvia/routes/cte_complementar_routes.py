"""
Rotas de CTe Complementar CarVia — CRUD completo
"""

import logging
from datetime import date, datetime

from flask import (
    render_template, request, flash, redirect, url_for, Response, jsonify,
)
from flask_login import login_required, current_user

from app import db
from app.carvia.models import (
    CarviaCteComplementar, CarviaOperacao, CarviaCustoEntrega,
    CarviaEmissaoCteComplementar,
)

logger = logging.getLogger(__name__)

STATUS_CTE_COMP = ['RASCUNHO', 'EMITIDO', 'FATURADO', 'CANCELADO']

# Tipos de custo aceitos no form de emissao SSW
# (espelha CarviaCustoEntrega.TIPOS_CUSTO + custo_entrega_routes.TIPO_CUSTO_MOTIVO_SSW)
TIPOS_CUSTO_EMISSAO = [
    'TAXA_DESCARGA', 'DIARIA', 'REENTREGA', 'DEVOLUCAO',
    'ARMAZENAGEM', 'AVARIA', 'PEDAGIO_EXTRA', 'GNRE_ICMS', 'OUTROS',
]


def register_cte_complementar_routes(bp):

    @bp.route('/ctes-complementares') # type: ignore
    @login_required
    def listar_ctes_complementares(): # type: ignore
        """Lista CTes complementares com filtros"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        page = request.args.get('page', 1, type=int)
        operacao_filtro = request.args.get('operacao', '', type=str)
        status_filtro = request.args.get('status', '')
        busca = request.args.get('busca', '')
        data_emissao_de = request.args.get('data_emissao_de', '')
        data_emissao_ate = request.args.get('data_emissao_ate', '')
        sort = request.args.get('sort', 'cte_data_emissao')
        direction = request.args.get('direction', 'desc')

        query = db.session.query(CarviaCteComplementar)

        if operacao_filtro:
            query = query.filter(CarviaCteComplementar.operacao_id == int(operacao_filtro))
        if status_filtro:
            query = query.filter(CarviaCteComplementar.status == status_filtro)

        if data_emissao_de:
            try:
                dt_de = datetime.strptime(data_emissao_de, '%Y-%m-%d').date()
                query = query.filter(CarviaCteComplementar.cte_data_emissao >= dt_de)
            except ValueError:
                pass
        if data_emissao_ate:
            try:
                dt_ate = datetime.strptime(data_emissao_ate, '%Y-%m-%d').date()
                query = query.filter(CarviaCteComplementar.cte_data_emissao <= dt_ate)
            except ValueError:
                pass

        if busca:
            busca_like = f'%{busca}%'
            # Busca tambem por NUMERO DE NF (via operacao pai -> NFs): permite
            # verificar se ha CTe Complementar emitido para uma dada NF.
            from app.carvia.models import CarviaOperacaoNf, CarviaNf
            sub_op_por_nf = db.session.query(
                CarviaOperacaoNf.operacao_id
            ).join(
                CarviaNf, CarviaNf.id == CarviaOperacaoNf.nf_id
            ).filter(
                CarviaNf.numero_nf.ilike(busca_like)
            ).distinct()
            query = query.filter(
                db.or_(
                    CarviaCteComplementar.numero_comp.ilike(busca_like),
                    CarviaCteComplementar.cte_numero.ilike(busca_like),
                    CarviaCteComplementar.cnpj_cliente.ilike(busca_like),
                    CarviaCteComplementar.nome_cliente.ilike(busca_like),
                    CarviaCteComplementar.ctrc_numero.ilike(busca_like),
                    CarviaCteComplementar.observacoes.ilike(busca_like),
                    CarviaCteComplementar.operacao_id.in_(sub_op_por_nf),
                )
            )

        # Ordenacao dinamica
        sortable_columns = {
            'numero_comp': CarviaCteComplementar.numero_comp,
            'cte_valor': CarviaCteComplementar.cte_valor,
            'cte_data_emissao': CarviaCteComplementar.cte_data_emissao,
            'status': CarviaCteComplementar.status,
            'criado_em': CarviaCteComplementar.criado_em,
        }
        sort_col = sortable_columns.get(sort, CarviaCteComplementar.cte_data_emissao)
        if direction == 'asc':
            query = query.order_by(sort_col.asc().nullslast())
        else:
            query = query.order_by(sort_col.desc().nullslast())

        paginacao = query.paginate(page=page, per_page=25, error_out=False)

        # Batch: buscar CTe pai (cte_numero + ctrc_numero) para evitar N+1
        op_ids = list({c.operacao_id for c in paginacao.items})
        op_info_map = {}
        if op_ids:
            ops = db.session.query(
                CarviaOperacao.id, CarviaOperacao.cte_numero, CarviaOperacao.ctrc_numero
            ).filter(CarviaOperacao.id.in_(op_ids)).all()
            op_info_map = {o_id: {'cte_numero': cte, 'ctrc_numero': ctrc} for o_id, cte, ctrc in ops}

        # Batch papeis (emit/dest/tomador) via operacao pai -> NFs
        from app.carvia.utils.papeis_frete import (
            batch_papeis_por_cte_complementar, tomador_como_cliente,
            batch_nfs_por_operacao,
        )
        comp_ids = [c.id for c in paginacao.items]
        papeis_por_comp = batch_papeis_por_cte_complementar(comp_ids)

        # Cliente exibido = TOMADOR do frete (SOT = cte_tomador do CTe pai),
        # NAO o nome_cliente herdado (que aponta sempre para o emitente). Para
        # tomador=DESTINATARIO o cliente correto e o destinatario da NF.
        cliente_tomador_por_comp = {
            cid: tomador_como_cliente(papeis_por_comp.get(cid))
            for cid in comp_ids
        }

        # NFs (numero_nf) por CTe Comp via operacao pai — exibe a quais NFs o
        # CTe Complementar se refere (verificar se ha CTe emitido para uma NF).
        nfs_por_operacao = batch_nfs_por_operacao(op_ids)
        nfs_por_comp = {
            c.id: nfs_por_operacao.get(c.operacao_id, [])
            for c in paginacao.items
        }

        return render_template(
            'carvia/ctes_complementares/listar.html',
            ctes_complementares=paginacao.items,
            paginacao=paginacao,
            op_info_map=op_info_map,
            papeis_por_comp=papeis_por_comp,
            cliente_tomador_por_comp=cliente_tomador_por_comp,
            nfs_por_comp=nfs_por_comp,
            operacao_filtro=operacao_filtro,
            status_filtro=status_filtro,
            busca=busca,
            data_emissao_de=data_emissao_de,
            data_emissao_ate=data_emissao_ate,
            sort=sort,
            direction=direction,
            status_list=STATUS_CTE_COMP,
        )

    @bp.route('/ctes-complementares/criar', methods=['GET', 'POST'])  # type: ignore
    @login_required
    def buscar_operacao_para_cte_complementar():  # type: ignore
        """Tela de busca por CTe pai (CTRC ou cte_numero) para criar CTe Comp.

        Espelha o fluxo `nova_despesa_extra_por_nf_carvia`. Submit redireciona
        para `criar_cte_complementar(operacao_id)`. Se houver match unico,
        redireciona direto; se multiplos, mostra lista; se nenhum, alerta.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        termo = (
            request.form.get('termo')
            or request.args.get('termo')
            or ''
        ).strip()

        if termo:
            like = f'%{termo}%'
            ops = (
                CarviaOperacao.query
                .filter(
                    db.or_(
                        CarviaOperacao.cte_numero.ilike(like),
                        CarviaOperacao.ctrc_numero.ilike(like),
                        CarviaOperacao.cte_chave_acesso == termo,
                    ),
                    CarviaOperacao.status != 'CANCELADO',
                )
                .order_by(CarviaOperacao.criado_em.desc())
                .limit(50)
                .all()
            )

            if not ops:
                flash(
                    f'Nenhum CTe CarVia encontrado para "{termo}". '
                    'Verifique CTRC ou numero do CTe.',
                    'warning',
                )
                return render_template(
                    'carvia/ctes_complementares/buscar.html',
                    termo=termo,
                )

            if len(ops) == 1:
                return redirect(url_for(
                    'carvia.criar_cte_complementar', operacao_id=ops[0].id
                ))

            return render_template(
                'carvia/ctes_complementares/buscar.html',
                termo=termo,
                operacoes_encontradas=ops,
            )

        return render_template(
            'carvia/ctes_complementares/buscar.html',
            termo='',
        )

    @bp.route('/ctes-complementares/criar/<int:operacao_id>', methods=['GET', 'POST'])  # type: ignore
    @login_required
    def criar_cte_complementar(operacao_id):  # type: ignore
        """Cria CTe Comp via emissao SSW 222 (modo unico).

        Refatorado em 2026-05-05: eliminado modo "input manual de chave/numero"
        (incoerente com status='RASCUNHO'). Toda criacao manual passa por
        emissao SSW (que preenche chave/numero pos-protocolo SEFAZ).

        Para registrar CTe ja emitido fora do sistema, usar o pipeline de
        importacao XML em `/carvia/importar`.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        operacao = db.session.get(CarviaOperacao, operacao_id)
        if not operacao:
            flash('Operacao nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_ctes_complementares'))

        from app.carvia.services.cte_complementar_service import (
            CteComplementarService,
        )
        from app.carvia.services.cte_complementar_persistencia import (
            extrair_icms_do_pai,
            calcular_valor_complementar,
        )

        # Pre-condicoes para emissao SSW (mostradas no template como gates)
        icms_info = extrair_icms_do_pai(operacao) if operacao else {}
        icms_aliquota = float(icms_info.get('aliquota_icms') or 0)
        pode_emitir = bool(operacao and operacao.ctrc_numero) and icms_aliquota > 0

        if request.method == 'POST':
            tipo_custo = (request.form.get('tipo_custo') or '').strip()
            valor_base_str = (request.form.get('valor_base') or '').strip()
            motivo_texto = (request.form.get('motivo_texto') or '').strip()
            ce_id_str = (request.form.get('custo_entrega_id') or '').strip()

            if tipo_custo not in TIPOS_CUSTO_EMISSAO:
                flash('Tipo de custo invalido.', 'warning')
                return redirect(url_for(
                    'carvia.criar_cte_complementar', operacao_id=operacao_id
                ))

            try:
                valor_base = float(valor_base_str.replace(',', '.'))
            except ValueError:
                flash('Valor base invalido.', 'warning')
                return redirect(url_for(
                    'carvia.criar_cte_complementar', operacao_id=operacao_id
                ))

            if valor_base <= 0:
                flash('Valor base deve ser maior que zero.', 'warning')
                return redirect(url_for(
                    'carvia.criar_cte_complementar', operacao_id=operacao_id
                ))

            if not motivo_texto:
                flash('Motivo (texto) e obrigatorio.', 'warning')
                return redirect(url_for(
                    'carvia.criar_cte_complementar', operacao_id=operacao_id
                ))

            ce_id = int(ce_id_str) if ce_id_str.isdigit() else None

            sucesso, mensagem, _emissao_id = (
                CteComplementarService.criar_para_emissao_ssw(
                    operacao_id=operacao.id,
                    valor_base=valor_base,
                    tipo_custo=tipo_custo,
                    motivo_texto=motivo_texto,
                    usuario=current_user.email,
                    custo_entrega_id=ce_id,
                )
            )
            if sucesso:
                flash(mensagem, 'success')
                return redirect(url_for('carvia.listar_ctes_complementares'))
            flash(mensagem, 'warning')

        # GET — preparar dropdown de CEs vinculaveis (mesma operacao, sem cte_comp)
        ces_elegiveis = (
            CarviaCustoEntrega.query
            .filter(
                CarviaCustoEntrega.operacao_id == operacao_id,
                CarviaCustoEntrega.cte_complementar_id.is_(None),
                CarviaCustoEntrega.status == 'PENDENTE',
            )
            .order_by(CarviaCustoEntrega.criado_em.desc())
            .all()
        )

        # Preview de calculo (so para exibicao default; JS recalcula on-input)
        preview_valor = None
        if pode_emitir and icms_aliquota > 0:
            try:
                preview_valor = calcular_valor_complementar(100.0, icms_aliquota)
            except ValueError:
                preview_valor = None

        return render_template(
            'carvia/ctes_complementares/criar.html',
            operacao=operacao,
            tipos_custo=TIPOS_CUSTO_EMISSAO,
            ces_elegiveis=ces_elegiveis,
            pode_emitir=pode_emitir,
            icms_aliquota=icms_aliquota,
            preview_valor_por_100=preview_valor,
        )

    @bp.route('/ctes-complementares/<int:cte_comp_id>') # type: ignore
    @login_required
    def detalhe_cte_complementar(cte_comp_id): # type: ignore
        """Detalhe de um CTe complementar com custos vinculados"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        cte_comp = db.session.get(CarviaCteComplementar, cte_comp_id)
        if not cte_comp:
            flash('CTe complementar nao encontrado.', 'warning')
            return redirect(url_for('carvia.listar_ctes_complementares'))

        # Custos de entrega vinculados a este CTe complementar
        custos_vinculados = db.session.query(CarviaCustoEntrega).filter(
            CarviaCustoEntrega.cte_complementar_id == cte_comp_id
        ).order_by(CarviaCustoEntrega.criado_em.desc()).all()

        # Despesas Extras (xerox Nacom) — reusa `custos_vinculados` que ja
        # filtra por cte_complementar_id. Card readonly no template.
        despesas_extras = [
            c for c in custos_vinculados if c.status != 'CANCELADO'
        ]

        # Papeis (emit/dest/tomador) via operacao pai -> primeira NF.
        # CTe Comp herda do CTe original porque nao tem emit/dest proprios.
        from app.carvia.utils.papeis_frete import (
            resolver_papeis_cte_complementar, tomador_como_cliente,
        )
        papeis = resolver_papeis_cte_complementar(cte_comp)

        # Cliente exibido = TOMADOR do frete (ver listar_ctes_complementares).
        cliente_tomador = tomador_como_cliente(papeis)

        # Preview: fatura pre-existente que referencia este CTe Comp por um item
        # com cte_complementar_id NULL (cenario "XML importado depois da fatura").
        # Habilita o botao "Vincular a fatura" so quando ha o que amarrar.
        fatura_candidata = None
        if cte_comp.fatura_cliente_id is None and cte_comp.cte_numero:
            from app.carvia.models import CarviaFaturaClienteItem, CarviaFaturaCliente
            cte_norm = str(cte_comp.cte_numero).lstrip('0') or '0'
            q_item = CarviaFaturaClienteItem.query.filter(
                db.func.ltrim(CarviaFaturaClienteItem.cte_numero, '0') == cte_norm,
                CarviaFaturaClienteItem.cte_complementar_id.is_(None),
            )
            if cte_comp.operacao_id is not None:
                q_item = q_item.filter(db.or_(
                    CarviaFaturaClienteItem.operacao_id.is_(None),
                    CarviaFaturaClienteItem.operacao_id == cte_comp.operacao_id,
                ))
            item_cand = q_item.first()
            if item_cand:
                fatura_candidata = db.session.get(
                    CarviaFaturaCliente, item_cand.fatura_cliente_id
                )

        return render_template(
            'carvia/ctes_complementares/detalhe.html',
            cte_comp=cte_comp,
            custos_vinculados=custos_vinculados,
            despesas_extras=despesas_extras,
            papeis=papeis,
            cliente_tomador=cliente_tomador,
            fatura_candidata=fatura_candidata,
        )

    @bp.route('/ctes-complementares/<int:cte_comp_id>/editar', methods=['GET', 'POST']) # type: ignore
    @login_required
    def editar_cte_complementar(cte_comp_id): # type: ignore
        """Edita um CTe complementar existente"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        cte_comp = db.session.get(CarviaCteComplementar, cte_comp_id)
        if not cte_comp:
            flash('CTe complementar nao encontrado.', 'warning')
            return redirect(url_for('carvia.listar_ctes_complementares'))

        if cte_comp.status in ('CANCELADO', 'FATURADO'):
            flash(
                f'Nao e possivel editar CTe complementar com status {cte_comp.status}.',
                'warning',
            )
            return redirect(url_for(
                'carvia.detalhe_cte_complementar', cte_comp_id=cte_comp_id
            ))

        if request.method == 'POST':
            cte_valor_str = request.form.get('cte_valor', '').strip()
            cte_data_emissao_str = request.form.get('cte_data_emissao', '').strip()
            cte_numero = request.form.get('cte_numero', '').strip()
            cte_chave_acesso = request.form.get('cte_chave_acesso', '').strip()
            cnpj_cliente = request.form.get('cnpj_cliente', '').strip()
            nome_cliente = request.form.get('nome_cliente', '').strip()
            observacoes = request.form.get('observacoes', '').strip()

            if not cte_valor_str:
                flash('Valor do CTe complementar e obrigatorio.', 'warning')
                return redirect(url_for(
                    'carvia.editar_cte_complementar', cte_comp_id=cte_comp_id
                ))

            try:
                cte_valor = float(cte_valor_str.replace(',', '.'))
                if cte_valor <= 0:
                    flash('Valor deve ser maior que zero.', 'warning')
                    return redirect(url_for(
                        'carvia.editar_cte_complementar', cte_comp_id=cte_comp_id
                    ))

                cte_comp.cte_valor = cte_valor
                cte_comp.cte_numero = cte_numero or None
                cte_comp.cte_chave_acesso = cte_chave_acesso or None
                cte_comp.cte_data_emissao = (
                    date.fromisoformat(cte_data_emissao_str)
                    if cte_data_emissao_str else None
                )
                cte_comp.cnpj_cliente = cnpj_cliente or cte_comp.cnpj_cliente
                cte_comp.nome_cliente = nome_cliente or cte_comp.nome_cliente
                cte_comp.observacoes = observacoes or None

                db.session.commit()
                flash('CTe complementar atualizado com sucesso.', 'success')
                return redirect(url_for(
                    'carvia.detalhe_cte_complementar', cte_comp_id=cte_comp_id
                ))

            except ValueError as ve:
                flash(f'Dados invalidos: {ve}', 'warning')
            except Exception as e:
                db.session.rollback()
                logger.error(f"Erro ao editar CTe complementar {cte_comp_id}: {e}")
                flash(f'Erro: {e}', 'danger')

        return render_template(
            'carvia/ctes_complementares/editar.html',
            cte_comp=cte_comp,
        )

    @bp.route('/ctes-complementares/<int:cte_comp_id>/status', methods=['POST']) # type: ignore
    @login_required
    def atualizar_status_cte_complementar(cte_comp_id): # type: ignore
        """Atualiza status de um CTe complementar"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        cte_comp = db.session.get(CarviaCteComplementar, cte_comp_id)
        if not cte_comp:
            flash('CTe complementar nao encontrado.', 'warning')
            return redirect(url_for('carvia.listar_ctes_complementares'))

        novo_status = request.form.get('status')
        if novo_status not in STATUS_CTE_COMP:
            flash('Status invalido.', 'warning')
            return redirect(url_for(
                'carvia.detalhe_cte_complementar', cte_comp_id=cte_comp_id
            ))

        try:
            # B1 (2026-04-18): Validar transicoes permitidas.
            # Espelha R4 CLAUDE.md — status irreversivel (exceto CANCELADO).
            # Matriz de transicoes validas:
            #   RASCUNHO   -> EMITIDO | CANCELADO
            #   EMITIDO    -> FATURADO | CANCELADO
            #   FATURADO   -> (nenhuma — terminal)
            #   CANCELADO  -> (nenhuma — terminal)
            TRANSICOES_VALIDAS = {
                'RASCUNHO': {'EMITIDO', 'CANCELADO'},
                'EMITIDO': {'FATURADO', 'CANCELADO'},
                'FATURADO': set(),
                'CANCELADO': set(),
            }
            status_atual = cte_comp.status or 'RASCUNHO'
            permitidas = TRANSICOES_VALIDAS.get(status_atual, set())

            if novo_status == status_atual:
                flash(
                    f'Status ja e {status_atual}. Nenhuma alteracao.', 'info'
                )
                return redirect(url_for(
                    'carvia.detalhe_cte_complementar', cte_comp_id=cte_comp_id
                ))

            if novo_status not in permitidas:
                flash(
                    f'Transicao {status_atual} -> {novo_status} nao permitida. '
                    f'Transicoes validas a partir de {status_atual}: '
                    f'{", ".join(sorted(permitidas)) or "(nenhuma — terminal)"}.',
                    'warning',
                )
                return redirect(url_for(
                    'carvia.detalhe_cte_complementar', cte_comp_id=cte_comp_id
                ))

            cte_comp.status = novo_status
            db.session.commit()
            flash(f'Status atualizado para {novo_status}.', 'success')

        except Exception as e:
            db.session.rollback()
            logger.error(
                f"Erro ao atualizar status CTe complementar {cte_comp_id}: {e}"
            )
            flash(f'Erro: {e}', 'danger')

        return redirect(url_for(
            'carvia.detalhe_cte_complementar', cte_comp_id=cte_comp_id
        ))

    # ── Downloads: XML e DACTE do CTe Complementar ─────────────────────────
    # SOT do DACTE = CarviaCteComplementar.cte_pdf_path (campo direto, alinhado
    # com CarviaOperacao/CarviaSubcontrato). resultado_json['dacte_s3_path']
    # da emissao permanece como fallback retrocompat para registros legados
    # ainda nao cobertos pelo backfill da migration de unificacao.
    # XML vem persistido em cte_comp.cte_xml_path (S3 ou local).
    # DACTE nao tem campo proprio no model — vive em emissao.resultado_json
    # ('dacte_s3_path') preenchido pelo worker apos emissao bem sucedida.

    @bp.route('/ctes-complementares/<int:cte_comp_id>/download/xml')  # type: ignore
    @login_required
    def download_cte_comp_xml(cte_comp_id):  # type: ignore
        """Download do XML do CTe Complementar (presigned S3 ou send_file local)."""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        cte_comp = db.session.get(CarviaCteComplementar, cte_comp_id)
        if not cte_comp or not cte_comp.cte_xml_path:
            flash('XML do CTe Complementar nao disponivel.', 'warning')
            return redirect(
                request.referrer
                or url_for('carvia.detalhe_cte_complementar', cte_comp_id=cte_comp_id)
            )

        filename = (
            cte_comp.cte_xml_nome_arquivo
            or (f"{cte_comp.cte_chave_acesso}-cte.xml"
                if cte_comp.cte_chave_acesso else 'cte-complementar.xml')
        )

        try:
            from app.utils.file_storage import get_file_storage
            storage = get_file_storage()

            # Tenta presigned URL (S3)
            url = storage.get_download_url(cte_comp.cte_xml_path, filename)
            if url:
                return redirect(url)

            # Fallback local: servir bytes diretamente
            data = storage.download_file(cte_comp.cte_xml_path)
            if data:
                return Response(
                    data,
                    mimetype='application/xml',
                    headers={
                        'Content-Disposition':
                        f'attachment; filename="{filename}"'
                    },
                )

            flash('Nao foi possivel baixar o XML.', 'warning')
        except Exception as e:
            logger.error(
                "Erro ao baixar XML do CTe Complementar %s: %s",
                cte_comp_id, e
            )
            flash(f'Erro ao baixar XML: {e}', 'danger')

        return redirect(
            request.referrer
            or url_for('carvia.detalhe_cte_complementar', cte_comp_id=cte_comp_id)
        )

    @bp.route('/ctes-complementares/<int:cte_comp_id>/download/dacte')  # type: ignore
    @login_required
    def download_cte_comp_dacte(cte_comp_id):  # type: ignore
        """Download do DACTE PDF do CTe Complementar.

        Le do campo `cte_pdf_path` (SOT). Cai em `resultado_json['dacte_s3_path']`
        da emissao SUCESSO mais recente apenas para registros legados ainda
        nao cobertos pelo backfill.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        cte_comp = db.session.get(CarviaCteComplementar, cte_comp_id)
        if not cte_comp:
            flash('CTe Complementar nao encontrado.', 'warning')
            return redirect(url_for('carvia.listar_ctes_complementares'))

        # 1. Fonte unica: campo direto no model
        dacte_path = cte_comp.cte_pdf_path

        # 2. Fallback retrocompat: resultado_json da emissao SUCESSO mais recente
        if not dacte_path:
            emissao = db.session.query(CarviaEmissaoCteComplementar).filter(
                CarviaEmissaoCteComplementar.cte_complementar_id == cte_comp_id,
                CarviaEmissaoCteComplementar.status == 'SUCESSO',
            ).order_by(
                CarviaEmissaoCteComplementar.criado_em.desc()
            ).first()

            if emissao and isinstance(emissao.resultado_json, dict):
                dacte_path = emissao.resultado_json.get('dacte_s3_path')

        if not dacte_path:
            flash('DACTE nao disponivel para este CTe Complementar.', 'warning')
            return redirect(
                request.referrer
                or url_for('carvia.detalhe_cte_complementar', cte_comp_id=cte_comp_id)
            )

        # Computa filename FRESH (ignora dacte_nome_arquivo legacy salvo
        # com ctrc_numero) para que registros antigos tambem se beneficiem
        # da prioridade cte_numero -> ctrc_numero -> numero_comp.
        filename = (
            f"{cte_comp.cte_numero or cte_comp.ctrc_numero or cte_comp.numero_comp}"
            f"-dacte.pdf"
        )

        try:
            from app.utils.file_storage import get_file_storage
            storage = get_file_storage()

            url = storage.get_download_url(dacte_path, filename)
            if url:
                return redirect(url)

            data = storage.download_file(dacte_path)
            if data:
                return Response(
                    data,
                    mimetype='application/pdf',
                    headers={
                        'Content-Disposition':
                        f'attachment; filename="{filename}"'
                    },
                )

            flash('Nao foi possivel baixar o DACTE.', 'warning')
        except Exception as e:
            logger.error(
                "Erro ao baixar DACTE do CTe Complementar %s: %s",
                cte_comp_id, e
            )
            flash(f'Erro ao baixar DACTE: {e}', 'danger')

        return redirect(
            request.referrer
            or url_for('carvia.detalhe_cte_complementar', cte_comp_id=cte_comp_id)
        )

    # =========================================================================
    # Vinculo CE <-> CTe Complementar (2026-05-05 — emissao desacoplada de CE)
    # =========================================================================

    @bp.route(
        '/api/ctes-complementares/<int:cte_comp_id>/ces-elegiveis',
        methods=['GET'],
    )  # type: ignore
    @login_required
    def api_ces_elegiveis_para_cte_comp(cte_comp_id):  # type: ignore
        """Retorna JSON com CEs elegiveis para vincular a este CTe Comp.

        Filtros deterministicos: mesma operacao_id, sem cte_complementar_id,
        status PENDENTE. Inclui flags valor_match/motivo_match.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'sucesso': False, 'erro': 'Acesso negado'}), 403

        from app.carvia.services.cte_complementar_service import (
            CteComplementarService,
        )
        try:
            ces = CteComplementarService.ces_elegiveis_para_vincular(cte_comp_id)
            return jsonify({'sucesso': True, 'ces': ces})
        except Exception as e:
            logger.error(
                'Erro ao buscar CEs elegiveis para cte_comp #%s: %s',
                cte_comp_id, e,
            )
            return jsonify({'sucesso': False, 'erro': str(e)}), 500

    @bp.route(
        '/ctes-complementares/<int:cte_comp_id>/vincular-ce',
        methods=['POST'],
    )  # type: ignore
    @login_required
    def vincular_ce_cte_complementar(cte_comp_id):  # type: ignore
        """Vincula um CarviaCustoEntrega a um CarviaCteComplementar.

        POST aceita JSON `{custo_entrega_id: N}` ou form-encoded.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'sucesso': False, 'erro': 'Acesso negado'}), 403

        payload = request.get_json(silent=True) or request.form
        ce_id = payload.get('custo_entrega_id') if payload else None
        try:
            ce_id = int(ce_id) if ce_id else None
        except (TypeError, ValueError):
            return jsonify(
                {'sucesso': False, 'erro': 'custo_entrega_id invalido'}
            ), 400

        if not ce_id:
            return jsonify(
                {'sucesso': False, 'erro': 'custo_entrega_id obrigatorio'}
            ), 400

        from app.carvia.services.cte_complementar_service import (
            CteComplementarService,
        )
        try:
            resultado = CteComplementarService.vincular_ce(
                cte_comp_id, ce_id, current_user.email
            )
            db.session.commit()
            return jsonify(resultado)
        except ValueError as e:
            db.session.rollback()
            return jsonify({'sucesso': False, 'erro': str(e)}), 400
        except Exception as e:
            db.session.rollback()
            logger.exception('Erro ao vincular CE #%s -> cte_comp #%s', ce_id, cte_comp_id)
            return jsonify({'sucesso': False, 'erro': str(e)}), 500

    @bp.route(
        '/ctes-complementares/desvincular-ce/<int:custo_entrega_id>',
        methods=['POST'],
    )  # type: ignore
    @login_required
    def desvincular_ce_cte_complementar(custo_entrega_id):  # type: ignore
        """Remove vinculo CE -> CTe Complementar."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'sucesso': False, 'erro': 'Acesso negado'}), 403

        from app.carvia.services.cte_complementar_service import (
            CteComplementarService,
        )
        try:
            resultado = CteComplementarService.desvincular_ce(
                custo_entrega_id, current_user.email
            )
            db.session.commit()
            return jsonify(resultado)
        except ValueError as e:
            db.session.rollback()
            return jsonify({'sucesso': False, 'erro': str(e)}), 400
        except Exception as e:
            db.session.rollback()
            logger.exception('Erro ao desvincular CE #%s', custo_entrega_id)
            return jsonify({'sucesso': False, 'erro': str(e)}), 500

    @bp.route(
        '/ctes-complementares/<int:cte_comp_id>/vincular-fatura',
        methods=['POST'],
    )  # type: ignore
    @login_required
    def vincular_fatura_cte_complementar(cte_comp_id):  # type: ignore
        """Fecha o vinculo de um CTe Comp com a fatura pre-existente que ja o
        referencia por um item (cenario "XML importado depois da fatura").

        Reusa `LinkingService.fechar_vinculo_cte_comp_fatura`: amarra o item
        existente (sem duplicar) e marca o CTe Comp FATURADO. Em fatura ja
        paga/conferida so prossegue se a amarracao NAO alterar o valor_total.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        cte_comp = db.session.get(CarviaCteComplementar, cte_comp_id)
        if not cte_comp:
            flash('CTe complementar nao encontrado.', 'warning')
            return redirect(url_for('carvia.listar_ctes_complementares'))

        from app.carvia.services.documentos.linking_service import LinkingService
        try:
            res = LinkingService().fechar_vinculo_cte_comp_fatura(cte_comp_id)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.exception(
                'Erro ao vincular CTe Comp %s a fatura', cte_comp_id
            )
            flash(f'Erro ao vincular a fatura: {e}', 'danger')
            return redirect(url_for(
                'carvia.detalhe_cte_complementar', cte_comp_id=cte_comp_id
            ))

        status = res.get('status')
        if status == 'VINCULADO':
            flash(
                f"CTe vinculado a fatura #{res.get('fatura_id')} "
                f"({res.get('items_atualizados')} item(ns) amarrado(s)).",
                'success',
            )
        elif status == 'SKIP':
            flash(
                f"CTe ja vinculado a fatura #{res.get('fatura_id')}.", 'info'
            )
        elif status == 'SEM_FATURA':
            flash(
                'Nenhuma fatura pre-existente referencia este CTe. '
                'Use "Nova Fatura" para fatura-lo.',
                'warning',
            )
        elif status == 'MULTIPLAS_FATURAS':
            flash(
                f"CTe referenciado em multiplas faturas "
                f"({res.get('fatura_ids')}) — investigacao manual.",
                'warning',
            )
        elif status == 'SKIP_FATURA_BLOQUEADA':
            flash(
                f"Fatura bloqueada para amarracao: {res.get('motivo')}. "
                'Reabra a conferencia / desconcilie antes (a amarracao '
                'mudaria o valor da fatura).',
                'warning',
            )
        else:
            flash(
                f"Nao foi possivel vincular: {res.get('motivo', status)}.",
                'danger',
            )
        return redirect(url_for(
            'carvia.detalhe_cte_complementar', cte_comp_id=cte_comp_id
        ))
