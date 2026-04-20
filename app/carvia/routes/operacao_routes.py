"""
Rotas de Operacoes CarVia — CRUD operacoes + subcontratos
"""

import logging
from collections import defaultdict
from datetime import datetime

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
        uf_filtro = request.args.get('uf_destino', '')
        uf_origem_filtro = request.args.get('uf_origem', '')
        data_emissao_de = request.args.get('data_emissao_de', '')
        data_emissao_ate = request.args.get('data_emissao_ate', '')
        sort = request.args.get('sort', 'cte_data_emissao')
        direction = request.args.get('direction', 'desc')
        # NF Triangular: oculta operacoes cujas NFs sao TODAS transferencias
        # efetivas (o CTe SP->RJ some quando a triangular esta fechada).
        incluir_transferencias = request.args.get(
            'incluir_transferencias', '0'
        ) == '1'

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

        if uf_filtro:
            query = query.filter(CarviaOperacao.uf_destino == uf_filtro.upper())

        if uf_origem_filtro:
            query = query.filter(CarviaOperacao.uf_origem == uf_origem_filtro.upper())

        if data_emissao_de:
            try:
                dt_de = datetime.strptime(data_emissao_de, '%Y-%m-%d').date()
                query = query.filter(CarviaOperacao.cte_data_emissao >= dt_de)
            except ValueError:
                pass
        if data_emissao_ate:
            try:
                dt_ate = datetime.strptime(data_emissao_ate, '%Y-%m-%d').date()
                query = query.filter(CarviaOperacao.cte_data_emissao <= dt_ate)
            except ValueError:
                pass

        if busca:
            busca_like = f'%{busca}%'
            # Subquery: buscar por embarcador/destinatario via NFs vinculadas
            from app.carvia.models import CarviaNf
            nf_match_subq = db.session.query(
                CarviaOperacaoNf.operacao_id
            ).join(
                CarviaNf, CarviaOperacaoNf.nf_id == CarviaNf.id
            ).filter(
                db.or_(
                    CarviaNf.nome_emitente.ilike(busca_like),
                    CarviaNf.nome_destinatario.ilike(busca_like),
                )
            ).subquery()

            query = query.filter(
                db.or_(
                    CarviaOperacao.nome_cliente.ilike(busca_like),
                    CarviaOperacao.cnpj_cliente.ilike(busca_like),
                    CarviaOperacao.cte_numero.ilike(busca_like),
                    CarviaOperacao.ctrc_numero.ilike(busca_like),
                    CarviaOperacao.cidade_destino.ilike(busca_like),
                    CarviaOperacao.id.in_(nf_match_subq),
                )
            )

        # NF Triangular: filtra operacoes 100% de transferencia
        if not incluir_transferencias:
            from app.carvia.models.documentos import CarviaNfVinculoTransferencia
            # op_ids que tem pelo menos 1 NF NAO transferencia (= devem aparecer)
            op_ids_com_nf_venda = db.session.query(
                CarviaOperacaoNf.operacao_id
            ).filter(
                ~CarviaOperacaoNf.nf_id.in_(
                    db.session.query(
                        CarviaNfVinculoTransferencia.nf_transferencia_id
                    )
                )
            ).distinct().subquery()
            query = query.filter(CarviaOperacao.id.in_(op_ids_com_nf_venda))

        # Ordenacao dinamica
        sortable_columns = {
            'cte_numero': func.lpad(func.coalesce(CarviaOperacao.cte_numero, ''), 20, '0'),
            'nome_cliente': CarviaOperacao.nome_cliente,
            'peso_utilizado': CarviaOperacao.peso_utilizado,
            'cte_valor': CarviaOperacao.cte_valor,
            'status': CarviaOperacao.status,
            'cte_data_emissao': CarviaOperacao.cte_data_emissao,
            'criado_em': CarviaOperacao.criado_em,
        }
        sort_col = sortable_columns.get(sort, CarviaOperacao.cte_data_emissao)
        if direction == 'asc':
            query = query.order_by(sort_col.asc().nullslast())
        else:
            query = query.order_by(sort_col.desc().nullslast())

        paginacao = query.paginate(page=page, per_page=per_page, error_out=False)

        # Batch: NFs vinculadas por operacao (numeros + ids para badges inline)
        # + destinatario/embarcador por operacao
        from app.carvia.models import CarviaNf
        nfs_por_op = defaultdict(list)
        dest_por_op = {}
        op_ids = [op.id for op, _ in paginacao.items]
        papeis_por_op = {}  # {op_id: {'emit': {...}, 'dest': {...}, 'tomador_label': ...}}
        if op_ids:
            from app.carvia.utils.tomador import tomador_label as _tomador_label
            # Batch: NFs + CNPJs/cidade/UF + cte_tomador da operacao via join
            rows_nf = db.session.query(
                CarviaOperacaoNf.operacao_id,
                CarviaOperacao.cte_tomador,
                CarviaNf.id,
                CarviaNf.numero_nf,
                CarviaNf.nome_emitente, CarviaNf.cnpj_emitente,
                CarviaNf.cidade_emitente, CarviaNf.uf_emitente,
                CarviaNf.nome_destinatario, CarviaNf.cnpj_destinatario,
                CarviaNf.cidade_destinatario, CarviaNf.uf_destinatario,
            ).join(
                CarviaOperacao, CarviaOperacaoNf.operacao_id == CarviaOperacao.id
            ).join(
                CarviaNf, CarviaOperacaoNf.nf_id == CarviaNf.id
            ).filter(
                CarviaOperacaoNf.operacao_id.in_(op_ids)
            ).all()
            seen_nf = set()
            for row in rows_nf:
                (oid, cte_tom, nf_id, num_nf,
                 emit_nome, emit_cnpj, emit_cidade, emit_uf,
                 dest_nome, dest_cnpj, dest_cidade, dest_uf) = row
                key = (oid, nf_id)
                if key not in seen_nf:
                    seen_nf.add(key)
                    nfs_por_op[oid].append({'id': nf_id, 'numero_nf': num_nf})
                if oid not in dest_por_op:
                    dest_por_op[oid] = {'destinatario': dest_nome, 'embarcador': emit_nome}
                # Papeis: regra CTe = 1 par unico, guarda primeira NF
                if oid not in papeis_por_op:
                    papeis_por_op[oid] = {
                        'emit': {
                            'nome': emit_nome, 'cnpj': emit_cnpj,
                            'cidade': emit_cidade, 'uf': emit_uf,
                        },
                        'dest': {
                            'nome': dest_nome, 'cnpj': dest_cnpj,
                            'cidade': dest_cidade, 'uf': dest_uf,
                        },
                        'tomador_label': _tomador_label(cte_tom),
                    }

        # Subquery: info de subcontrato (transportadora subcontratada + cte subcontrato)
        from app.transportadoras.models import Transportadora
        sub_info = {}
        if op_ids:
            sub_info_raw = db.session.query(
                CarviaSubcontrato.operacao_id,
                CarviaSubcontrato.id,
                Transportadora.razao_social,
                CarviaSubcontrato.cte_numero,
            ).join(
                Transportadora, CarviaSubcontrato.transportadora_id == Transportadora.id
            ).filter(
                CarviaSubcontrato.status != 'CANCELADO',
                CarviaSubcontrato.operacao_id.in_(op_ids),
            ).order_by(CarviaSubcontrato.operacao_id, CarviaSubcontrato.id).all()

            for op_id, sub_id, razao, cte_num in sub_info_raw:
                if op_id not in sub_info:
                    sub_info[op_id] = {
                        'sub_id': sub_id,
                        'transp_nome': razao,
                        'sub_cte': cte_num,
                        'count': 0,
                    }
                sub_info[op_id]['count'] += 1

        # Batch: resolver clientes comerciais via CNPJ DESTINATARIO da primeira NF
        # de cada operacao (regra de negocio — cliente = quem recebe a mercadoria,
        # nao o remetente/pagador que varia com o incoterm).
        from app.carvia.services.clientes.cliente_service import CarviaClienteService
        op_ids_pag = [op.id for op, _ in paginacao.items]
        clientes_por_op = CarviaClienteService.resolver_clientes_por_operacoes(op_ids_pag)

        # NF Triangular: badges de NF transferencia ao lado do emitente
        # Para cada operacao, identificar NFs venda que tem vinculo com
        # NF transf e coletar os dados dessa transferencia.
        transferencias_por_op = defaultdict(list)
        if op_ids:
            from app.carvia.models.documentos import CarviaNfVinculoTransferencia
            rows_transf = db.session.query(
                CarviaOperacaoNf.operacao_id,
                CarviaNfVinculoTransferencia.nf_transferencia_id,
                CarviaNf.numero_nf,
            ).join(
                CarviaNfVinculoTransferencia,
                CarviaNfVinculoTransferencia.nf_venda_id == CarviaOperacaoNf.nf_id,
            ).join(
                CarviaNf,
                CarviaNf.id == CarviaNfVinculoTransferencia.nf_transferencia_id,
            ).filter(
                CarviaOperacaoNf.operacao_id.in_(op_ids),
            ).distinct().all()
            seen = set()
            for op_id, transf_id, num_nf in rows_transf:
                key = (op_id, transf_id)
                if key in seen:
                    continue
                seen.add(key)
                transferencias_por_op[op_id].append({
                    'transf_id': transf_id,
                    'num_nf_transf': num_nf,
                })

        return render_template(
            'carvia/listar_operacoes.html',
            operacoes=paginacao.items,
            paginacao=paginacao,
            status_filtro=status_filtro,
            tipo_filtro=tipo_filtro,
            uf_filtro=uf_filtro,
            uf_origem_filtro=uf_origem_filtro,
            data_emissao_de=data_emissao_de,
            data_emissao_ate=data_emissao_ate,
            busca=busca,
            sort=sort,
            direction=direction,
            sub_info=sub_info,
            nfs_por_op=nfs_por_op,
            dest_por_op=dest_por_op,
            clientes_por_op=clientes_por_op,
            papeis_por_op=papeis_por_op,
            transferencias_por_op=transferencias_por_op,
            incluir_transferencias=incluir_transferencias,
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
        from app.carvia.models import (
            CarviaFaturaTransportadora, CarviaCteComplementar, CarviaCustoEntrega
        )
        fat_transp_ids = {
            s.fatura_transportadora_id for s in subcontratos
            if s.fatura_transportadora_id
        }
        faturas_transportadora = []
        if fat_transp_ids:
            faturas_transportadora = CarviaFaturaTransportadora.query.filter(
                CarviaFaturaTransportadora.id.in_(fat_transp_ids)
            ).all()

        # CTe Complementares vinculados a esta operacao
        ctes_complementares = db.session.query(CarviaCteComplementar).filter(
            CarviaCteComplementar.operacao_id == operacao_id
        ).order_by(CarviaCteComplementar.criado_em.desc()).all()

        # Custos de entrega vinculados a esta operacao
        custos_entrega = db.session.query(CarviaCustoEntrega).filter(
            CarviaCustoEntrega.operacao_id == operacao_id
        ).order_by(CarviaCustoEntrega.criado_em.desc()).all()

        # Resolver cliente comercial via CNPJ DESTINATARIO da primeira NF
        # (regra de negocio — cliente = quem recebe a mercadoria).
        from app.carvia.services.clientes.cliente_service import CarviaClienteService
        cliente_comercial = CarviaClienteService.resolver_clientes_por_operacoes(
            [operacao.id],
        ).get(operacao.id)

        # Papeis de frete (Emitente/Destinatario/Tomador) — regra: 1 CTe = 1 par unico.
        # Tomador vem EXCLUSIVAMENTE de cte_tomador (XML CTe ou wizard manual).
        # Removido fallback FOB/CIF em 2026-04-20 — SOT e o CTe, nao a fatura.
        from app.carvia.utils.tomador import resolver_tomador, tomador_label
        papeis = None
        if nfs:
            primeira = nfs[0]
            papeis = {
                'emit': {
                    'nome': primeira.nome_emitente,
                    'cnpj': primeira.cnpj_emitente,
                    'cidade': primeira.cidade_emitente,
                    'uf': primeira.uf_emitente,
                },
                'dest': {
                    'nome': primeira.nome_destinatario,
                    'cnpj': primeira.cnpj_destinatario,
                    'cidade': primeira.cidade_destinatario,
                    'uf': primeira.uf_destinatario,
                },
                'tomador_label': tomador_label(operacao.cte_tomador),
                'tomador': resolver_tomador(operacao.cte_tomador),
            }

        # A4.2 (2026-04-18): Historico de correcoes de endereco (CC-e / manual).
        # Lista ordenada desc por criado_em (usa indice criado na migration).
        from app.carvia.models import CarviaEnderecoCorrecao
        correcoes_endereco = (
            CarviaEnderecoCorrecao.query
            .filter_by(operacao_id=operacao.id)
            .order_by(CarviaEnderecoCorrecao.criado_em.desc())
            .limit(50)
            .all()
        )

        return render_template(
            'carvia/detalhe_operacao.html',
            operacao=operacao,
            nfs=nfs,
            subcontratos=subcontratos,
            faturas_transportadora=faturas_transportadora,
            ctes_complementares=ctes_complementares,
            custos_entrega=custos_entrega,
            cliente_comercial=cliente_comercial,
            papeis=papeis,
            correcoes_endereco=correcoes_endereco,
        )

    # ==================== CRIAR OPERACAO MANUAL ====================

    @bp.route('/operacoes/criar', methods=['GET', 'POST'])
    @login_required
    def criar_operacao_manual():
        """Cria operacao manual — wizard com selecao de NFs ou fluxo freteiro.

        Fluxo wizard (MANUAL_SEM_CTE):
            GET: Renderiza wizard com 2 secoes (NFs, valor)
            POST: Cria CarviaOperacao a partir de NFs selecionadas

        Fluxo freteiro (MANUAL_FRETEIRO):
            Preservado — redireciona para criar_freteiro.html com OperacaoManualForm
        """
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        # Detectar tipo de fluxo
        if request.method == 'GET':
            tipo = request.args.get('tipo', 'MANUAL_SEM_CTE')
        else:
            tipo = request.form.get('tipo_entrada', 'MANUAL_SEM_CTE')

        # ---- Fluxo freteiro: preservar comportamento existente ----
        if tipo == 'MANUAL_FRETEIRO':
            from app.carvia.forms import OperacaoManualForm
            form = OperacaoManualForm()

            if form.validate_on_submit():
                try:
                    # cte_tomador: obrigatorio (DataRequired no form.cte_tomador — forms.py:104).
                    # SOT do tomador quando o CTe e manual (sem XML). Defesa em profundidade:
                    # normalizamos aqui tambem caso o DataRequired seja removido no futuro.
                    tomador_valor = (form.cte_tomador.data or '').strip().upper() or None
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
                        cte_numero=CarviaOperacao.gerar_numero_cte(),
                        cte_tomador=tomador_valor,
                        tipo_entrada='MANUAL_FRETEIRO',
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
                    logger.error(f"Erro ao criar operacao freteiro: {e}")
                    flash(f'Erro ao criar operacao: {e}', 'danger')

            return render_template(
                'carvia/criar_freteiro.html',
                form=form,
                tipo_entrada='MANUAL_FRETEIRO',
            )

        # ---- Fluxo wizard: criar a partir de NFs ----
        # GAP-13: Wizard usa request.form direto (sem WTForms). CSRF protegido pelo
        # Flask-WTF global CSRF (CSRFProtect em app/__init__.py) + {{ csrf_token() }}
        # no template criar_manual.html. Nao necessita WTForms adicional.
        if request.method == 'GET':
            return render_template('carvia/criar_manual.html')

        # POST — processar wizard
        nf_ids_raw = request.form.getlist('nf_ids')
        cte_valor_raw = request.form.get('cte_valor', '').strip()
        observacoes = request.form.get('observacoes', '').strip()
        # Tomador do frete (OBRIGATORIO 2026-04-20). Valida contra whitelist SEFAZ.
        _tomador_raw = (request.form.get('cte_tomador') or '').strip().upper()
        _TOMADORES_VALIDOS = {
            'REMETENTE', 'EXPEDIDOR', 'RECEBEDOR', 'DESTINATARIO', 'TERCEIRO',
        }
        cte_tomador = _tomador_raw if _tomador_raw in _TOMADORES_VALIDOS else None

        # GAP-18: Preservar dados do formulario para re-render apos erro
        form_data = {
            'nf_ids': nf_ids_raw,
            'cte_valor': cte_valor_raw,
            'observacoes': observacoes,
            'cte_tomador': cte_tomador or '',
        }

        # Validar tomador obrigatorio — SOT do tomador para CTes sem XML.
        if not cte_tomador:
            flash('Tomador do frete e obrigatorio (Remetente/Expedidor/Recebedor/Destinatario/Terceiro).', 'warning')
            return render_template('carvia/criar_manual.html', form_data=form_data)

        # Validar NFs
        if not nf_ids_raw:
            flash('Selecione pelo menos uma NF.', 'warning')
            return render_template('carvia/criar_manual.html', form_data=form_data)

        # Parse nf_ids
        try:
            nf_ids = [int(x) for x in nf_ids_raw]
        except (ValueError, TypeError):
            flash('IDs de NF invalidos.', 'danger')
            return render_template('carvia/criar_manual.html', form_data=form_data)

        # Validar cte_valor (formato BR: "1.234,56" -> 1234.56)
        if not cte_valor_raw:
            flash('Informe o valor do CTe.', 'warning')
            return render_template('carvia/criar_manual.html', form_data=form_data)

        try:
            cte_valor = float(cte_valor_raw.replace('.', '').replace(',', '.'))
        except (ValueError, TypeError):
            flash('Valor do CTe invalido.', 'danger')
            return render_template('carvia/criar_manual.html', form_data=form_data)

        # Buscar NFs do banco
        nfs_encontradas = db.session.query(CarviaNf).filter(
            CarviaNf.id.in_(nf_ids)
        ).all()

        if len(nfs_encontradas) != len(nf_ids):
            flash('Uma ou mais NFs nao foram encontradas.', 'danger')
            return render_template('carvia/criar_manual.html', form_data=form_data)

        # Validar mesmo cnpj_emitente
        cnpjs = {nf.cnpj_emitente for nf in nfs_encontradas}
        if len(cnpjs) > 1:
            flash('NFs selecionadas pertencem a clientes diferentes. Selecione NFs do mesmo cliente.', 'danger')
            return render_template('carvia/criar_manual.html', form_data=form_data)

        try:
            # Somar peso_bruto e valor_total das NFs
            peso_total = sum(float(nf.peso_bruto or 0) for nf in nfs_encontradas)
            valor_total = sum(float(nf.valor_total or 0) for nf in nfs_encontradas)

            # Extrair dados da primeira NF (emitente = cliente, destinatario = destino)
            primeira_nf = nfs_encontradas[0]
            cnpj_cliente = primeira_nf.cnpj_emitente
            nome_cliente = primeira_nf.nome_emitente or cnpj_cliente
            uf_origem = primeira_nf.uf_emitente
            cidade_origem = primeira_nf.cidade_emitente
            uf_destino = primeira_nf.uf_destinatario
            cidade_destino = primeira_nf.cidade_destinatario

            # Warning se NFs tem destinos diferentes
            destinos = {
                (nf.uf_destinatario, nf.cidade_destinatario)
                for nf in nfs_encontradas
                if nf.uf_destinatario
            }
            if len(destinos) > 1:
                flash(
                    'NFs selecionadas tem destinos diferentes. '
                    f'Usando destino da primeira NF: {cidade_destino}/{uf_destino}.',
                    'warning'
                )

            # Validar campos obrigatorios
            if not uf_destino:
                flash('UF destino nao encontrada nas NFs selecionadas.', 'danger')
                return render_template('carvia/criar_manual.html', form_data=form_data)
            if not cidade_destino:
                flash('Cidade destino nao encontrada nas NFs selecionadas.', 'danger')
                return render_template('carvia/criar_manual.html', form_data=form_data)

            # Data emissao = maior data_emissao das NFs selecionadas
            datas_nfs = [nf.data_emissao for nf in nfs_encontradas if nf.data_emissao]
            data_emissao_cte = max(datas_nfs) if datas_nfs else None

            # Criar CarviaOperacao
            operacao = CarviaOperacao(
                cnpj_cliente=cnpj_cliente,
                nome_cliente=nome_cliente,
                uf_origem=uf_origem,
                cidade_origem=cidade_origem,
                uf_destino=uf_destino,
                cidade_destino=cidade_destino,
                peso_bruto=peso_total,
                valor_mercadoria=valor_total,
                cte_valor=cte_valor,
                cte_numero=CarviaOperacao.gerar_numero_cte(),
                cte_data_emissao=data_emissao_cte,
                cte_tomador=cte_tomador,
                tipo_entrada='MANUAL_SEM_CTE',
                status='RASCUNHO',
                observacoes=observacoes or None,
                criado_por=current_user.email,
            )
            # R3: calcular peso_utilizado
            operacao.calcular_peso_utilizado()
            db.session.add(operacao)
            db.session.flush()  # Obter operacao.id para junctions

            # Criar junctions CarviaOperacaoNf
            for nf in nfs_encontradas:
                junction = CarviaOperacaoNf(
                    operacao_id=operacao.id,
                    nf_id=nf.id,
                )
                db.session.add(junction)

            # Auto-cubagem para motos (se empresa configurada)
            try:
                from app.carvia.services.pricing.moto_recognition_service import (
                    MotoRecognitionService,
                )
                moto_svc = MotoRecognitionService()
                if cnpj_cliente and moto_svc.empresa_usa_cubagem(cnpj_cliente):
                    resultado_cubagem = moto_svc.calcular_peso_cubado_operacao(
                        operacao.id
                    )
                    if (
                        resultado_cubagem
                        and resultado_cubagem['peso_cubado_total'] > 0
                    ):
                        operacao.peso_cubado = resultado_cubagem[
                            'peso_cubado_total'
                        ]
                        operacao.calcular_peso_utilizado()  # R3
            except Exception as e_cub:
                logger.warning(f"Erro auto-cubagem op={operacao.id}: {e_cub}")

            db.session.commit()

            flash(f'Operacao #{operacao.id} criada com {len(nfs_encontradas)} NF(s).', 'success')
            return redirect(url_for('carvia.detalhe_operacao', operacao_id=operacao.id))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao criar operacao via wizard: {e}")
            flash(f'Erro ao criar operacao: {e}', 'danger')
            return render_template('carvia/criar_manual.html', form_data=form_data)

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

                # A4.2 (2026-04-18): Enderecos textuais + audit trail
                # Gate via feature flag (default False para rollout gradual).
                from flask import current_app as _cc_app
                _ativar_enderecos = _cc_app.config.get(
                    'CARVIA_FEATURE_EDITAR_ENDERECO_CCE', False
                )
                if _ativar_enderecos:
                    from app.carvia.models import CarviaEnderecoCorrecao
                    _campos_endereco = [
                        'remetente_logradouro', 'remetente_numero',
                        'remetente_bairro', 'remetente_cep',
                        'destinatario_logradouro', 'destinatario_numero',
                        'destinatario_bairro', 'destinatario_cep',
                    ]
                    _motivo = (form.motivo_correcao.data or 'CORRECAO_MANUAL').strip()
                    _numero_cce = (form.numero_cce.data or '').strip() or None
                    if _motivo == 'CC-E' and not _numero_cce:
                        # CC-e sem numero nao e fatal; grava mesmo assim
                        # (operador pode preencher depois). Log warning.
                        logger.warning(
                            'Operacao %s: CC-e sem numero informado',
                            operacao_id,
                        )
                    _correcoes = []
                    _usuario_str = getattr(current_user, 'email', None) or \
                        getattr(current_user, 'nome', None) or 'sistema'
                    for _campo in _campos_endereco:
                        _valor_novo = (getattr(form, _campo).data or '').strip() or None
                        _valor_anterior = getattr(operacao, _campo)
                        if (_valor_anterior or '') == (_valor_novo or ''):
                            continue
                        setattr(operacao, _campo, _valor_novo)
                        _correcoes.append(CarviaEnderecoCorrecao(
                            operacao_id=operacao.id,
                            campo=_campo,
                            valor_anterior=_valor_anterior,
                            valor_novo=_valor_novo,
                            motivo=_motivo,
                            numero_cce=_numero_cce,
                            criado_por=_usuario_str,
                        ))
                    for _c in _correcoes:
                        db.session.add(_c)
                    if _correcoes:
                        logger.info(
                            'Operacao %s: %d correcao(oes) de endereco '
                            'registrada(s) motivo=%s',
                            operacao_id, len(_correcoes), _motivo,
                        )

                # Re-executar auto-cubagem se empresa usa cubagem (R3)
                try:
                    from app.carvia.services.pricing.moto_recognition_service import MotoRecognitionService
                    moto_svc = MotoRecognitionService()
                    if operacao.cnpj_cliente and moto_svc.empresa_usa_cubagem(operacao.cnpj_cliente):
                        resultado_cub = moto_svc.calcular_peso_cubado_operacao(operacao.id)
                        if resultado_cub and resultado_cub.get('peso_cubado_total', 0) > 0:
                            operacao.peso_cubado = resultado_cub['peso_cubado_total']
                            operacao.calcular_peso_utilizado()
                except Exception as e_cub:
                    logger.warning(f"Auto-cubagem falhou na edicao (best-effort): {e_cub}")

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

    # ==================== CANCELAMENTO EM CASCATA (B3 2026-04-18) ====================

    @bp.route(
        '/operacoes/<int:operacao_id>/cascade/dependencias',
        methods=['GET'],
    )
    @login_required
    def api_cascade_dependencias(operacao_id):
        """B3: retorna JSON com dependencias ativas da operacao
        (sub/CTeComp/CE/CarviaFrete) — usado pelo modal de cancelamento."""
        if not getattr(current_user, 'sistema_carvia', False):
            from flask import jsonify
            return jsonify({'erro': 'Acesso negado'}), 403

        from flask import jsonify
        from app.carvia.services.documentos.operacao_cancel_service import (
            listar_dependencias_ativas,
        )
        dados = listar_dependencias_ativas(operacao_id)
        if dados.get('operacao') is None:
            return jsonify({'erro': 'Operacao nao encontrada'}), 404
        return jsonify(dados), 200

    @bp.route(
        '/operacoes/<int:operacao_id>/cascade/cancelar',
        methods=['POST'],
    )
    @login_required
    def api_cascade_cancelar(operacao_id):
        """B3: cancela lista de dependencias + operacao em uma transacao.

        Body JSON:
          {
            "subcontratos": [id, ...],
            "ctes_complementares": [id, ...],
            "custos_entrega": [id, ...],
            "carvia_fretes": [id, ...],
            "cancelar_operacao": bool,
            "motivo": str (opcional)
          }
        """
        from flask import jsonify, request as _req
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        # Feature flag para rollout gradual
        from flask import current_app as _cc_app
        if not _cc_app.config.get(
            'CARVIA_FEATURE_CASCADE_CANCELAMENTO', False
        ):
            return jsonify({
                'erro': 'Feature desabilitada. '
                'Use fluxo manual em cada dependencia.'
            }), 403

        from app.carvia.services.documentos.operacao_cancel_service import (
            executar_cancelamento_cascata,
        )
        payload = _req.get_json(silent=True) or {}
        usuario = (
            getattr(current_user, 'email', None)
            or getattr(current_user, 'nome', None)
            or 'sistema'
        )
        resultado = executar_cancelamento_cascata(
            operacao_id=operacao_id,
            ids_a_cancelar={
                'subcontratos': payload.get('subcontratos') or [],
                'ctes_complementares': payload.get('ctes_complementares') or [],
                'custos_entrega': payload.get('custos_entrega') or [],
                'carvia_fretes': payload.get('carvia_fretes') or [],
                'cancelar_operacao': bool(payload.get('cancelar_operacao')),
            },
            usuario=usuario,
            motivo=payload.get('motivo'),
        )
        status_http = 200 if resultado.get('status') in ('OK', 'PARCIAL') else 422
        return jsonify(resultado), status_http

    # ==================== CANCELAR OPERACAO ====================

    @bp.route('/operacoes/<int:operacao_id>/cancelar', methods=['POST'])
    @login_required
    def cancelar_operacao(operacao_id):
        """Cancela uma operacao.

        W6 (Sprint 1): NAO cascadeia mais o cancelamento de subcontratos.
        Bloqueia via operacao.pode_cancelar() se ha filhos ativos
        (subs, CTe Comp, CustoEntrega). O usuario deve cancelar cada
        dependencia manualmente, na ordem inversa do fluxo.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        operacao = db.session.get(CarviaOperacao, operacao_id)
        if not operacao:
            flash('Operacao nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_operacoes'))

        # Guard centralizado no model (Sprint 0) — bloqueia se FATURADO,
        # CANCELADO, ou se ha filhos ativos.
        pode, razao = operacao.pode_cancelar()
        if not pode:
            flash(razao, 'warning')
            return redirect(url_for('carvia.detalhe_operacao', operacao_id=operacao_id))

        try:
            # Re-review Sprint 1 CRIT: se a operacao chegou aqui via edge
            # case (FATURADO + fatura CANCELADA ou fatura orfa/None), limpar
            # o fatura_cliente_id para evitar FK dangling na operacao
            # CANCELADA.
            if operacao.status == 'FATURADO' and operacao.fatura_cliente_id:
                logger.info(
                    f"Operacao #{operacao_id}: limpando fatura_cliente_id "
                    f"({operacao.fatura_cliente_id}) antes de cancelar "
                    f"(fatura orfa ou CANCELADA)"
                )
                operacao.fatura_cliente_id = None
            operacao.status = 'CANCELADO'
            db.session.commit()
            logger.info(
                f"Operacao #{operacao_id} cancelada por {current_user.email}"
            )
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
                from app.carvia.services.pricing.cotacao_service import CotacaoService
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
                subcontrato.cte_numero = CarviaSubcontrato.gerar_numero_sub()
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

            # Phase C (2026-04-14): CC e aprovacoes operam em Frete.
            # Resolvemos frete_id via sub.frete_id se existir.
            if sub.frete_id:
                from app.carvia.services.financeiro.conta_corrente_service import (
                    ContaCorrenteService,
                )
                from app.carvia.services.documentos.aprovacao_frete_service import (
                    AprovacaoFreteService,
                )
                ContaCorrenteService.cancelar_movimentacoes(
                    frete_id=sub.frete_id,
                    motivo='Sub cancelado',
                    usuario=current_user.email,
                )
                AprovacaoFreteService().rejeitar_pendentes_de_frete(
                    frete_id=sub.frete_id,
                    motivo='Sub cancelado',
                    usuario=current_user.email,
                )

            # GAP-03: Downgrade operacao se nao ha mais subs ativos
            operacao = db.session.get(CarviaOperacao, operacao_id)
            if operacao and operacao.status not in ('FATURADO', 'CANCELADO'):
                subs_ativos = operacao.subcontratos.filter(
                    CarviaSubcontrato.status != 'CANCELADO'
                ).all()
                if not subs_ativos:
                    operacao.status = 'RASCUNHO'
                    logger.info(
                        f"Operacao #{operacao_id}: downgrade para RASCUNHO "
                        f"(ultimo sub ativo cancelado por {current_user.email})"
                    )
                elif operacao.status == 'CONFIRMADO':
                    todos_confirmados = all(
                        s.status == 'CONFIRMADO' for s in subs_ativos
                    )
                    if not todos_confirmados:
                        operacao.status = 'COTADO'
                        logger.info(
                            f"Operacao #{operacao_id}: downgrade para COTADO "
                            f"(nem todos subs confirmados apos cancelamento)"
                        )

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
        """Atualiza valor_acertado de um subcontrato.

        W4 (Sprint 2): quando o sub ja tem fatura transportadora vinculada,
        a regra e do model da fatura (ft.pode_editar_sub_valor) —
        bloqueia se FT esta CONFERIDA ou PAGA. Antes da anexacao a FT,
        o guard tradicional por status_subcontrato continua.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        sub = db.session.get(CarviaSubcontrato, sub_id)
        if not sub or sub.operacao_id != operacao_id:
            flash('Subcontrato nao encontrado.', 'warning')
            return redirect(url_for('carvia.listar_operacoes'))

        # GAP-04: Bloquear edicao de valor_acertado em subs CONFERIDO/FATURADO
        if sub.status in ('CONFERIDO', 'FATURADO'):
            flash(f'Subcontrato {sub.status} nao permite alteracao de valor.', 'warning')
            return redirect(url_for('carvia.detalhe_operacao', operacao_id=operacao_id))

        # W4: Se sub ja esta em fatura transportadora, delega para o guard da FT.
        # W4 fix (Sprint 2 followup): se FK existe mas relationship retorna None
        # (dangling reference), erro explicito — antes era silent bypass.
        if sub.fatura_transportadora_id:
            ft = sub.fatura_transportadora
            if ft is None:
                flash(
                    f'Subcontrato aponta para Fatura Transportadora '
                    f'#{sub.fatura_transportadora_id} que nao existe mais '
                    f'(dangling FK). Contate o admin.',
                    'danger',
                )
                return redirect(url_for('carvia.detalhe_operacao', operacao_id=operacao_id))
            pode, razao = ft.pode_editar_sub_valor()
            if not pode:
                flash(razao, 'warning')
                return redirect(url_for('carvia.detalhe_operacao', operacao_id=operacao_id))

        try:
            # GAP-17: Aceitar formato BR (1.234,56) e formato US (1234.56)
            valor_raw = request.form.get('valor_acertado', '').strip()
            if valor_raw:
                valor_acertado = float(valor_raw.replace('.', '').replace(',', '.'))
            else:
                valor_acertado = None
            sub.valor_acertado = valor_acertado
            db.session.commit()
            flash(f'Valor acertado atualizado: R$ {valor_acertado:.2f}' if valor_acertado else 'Valor acertado removido.', 'success')
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao atualizar valor: {e}")
            flash(f'Erro: {e}', 'danger')

        return redirect(url_for('carvia.detalhe_operacao', operacao_id=operacao_id))

    # ==================== DESVINCULAR FATURA ====================

    @bp.route('/operacoes/<int:operacao_id>/desvincular-fatura', methods=['POST'])
    @login_required
    def desvincular_fatura(operacao_id):
        """GAP-23: Desvincula fatura cliente de uma operacao FATURADO.

        Reverte operacao para CONFIRMADO, remove fatura_cliente_id.
        Itens de fatura mantidos (nao exclui fatura, apenas desvincula operacao).
        """
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        operacao = db.session.get(CarviaOperacao, operacao_id)
        if not operacao:
            flash('Operacao nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_operacoes'))

        if operacao.status != 'FATURADO':
            flash('Apenas operacoes FATURADO podem ter fatura desvinculada.', 'warning')
            return redirect(url_for('carvia.detalhe_operacao', operacao_id=operacao_id))

        if not operacao.fatura_cliente_id:
            flash('Operacao nao possui fatura vinculada.', 'warning')
            return redirect(url_for('carvia.detalhe_operacao', operacao_id=operacao_id))

        try:
            fatura_id = operacao.fatura_cliente_id

            # Remover FK da operacao e reverter status
            operacao.fatura_cliente_id = None
            operacao.status = 'CONFIRMADO'

            # Limpar operacao_id nos itens de fatura (nao exclui itens)
            from app.carvia.models import CarviaFaturaClienteItem, CarviaFrete
            itens = db.session.query(CarviaFaturaClienteItem).filter_by(
                fatura_cliente_id=fatura_id,
                operacao_id=operacao_id,
            ).all()
            for item in itens:
                item.operacao_id = None

            # Propagar para CarviaFrete (consistencia com api_desvincular_operacao_fatura_cliente)
            CarviaFrete.query.filter_by(operacao_id=operacao_id).update(
                {'fatura_cliente_id': None}
            )

            db.session.commit()

            logger.info(
                f"Operacao #{operacao_id}: fatura #{fatura_id} desvinculada, "
                f"status revertido para CONFIRMADO por {current_user.email}"
            )
            flash(
                f'Fatura #{fatura_id} desvinculada. Operacao revertida para CONFIRMADO.',
                'success',
            )
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao desvincular fatura da operacao #{operacao_id}: {e}")
            flash(f'Erro: {e}', 'danger')

        return redirect(url_for('carvia.detalhe_operacao', operacao_id=operacao_id))

    # ==================== EDITAR VALOR CTe ====================

    @bp.route('/operacoes/<int:operacao_id>/editar-cte-valor', methods=['POST'])
    @login_required
    def editar_cte_valor(operacao_id):
        """Edita cte_valor.

        W1 (Sprint 1): guard via operacao.pode_editar_valor() — bloqueia
        se fatura PAGA. Fatura e entidade independente, NAO recalcula
        automaticamente. Para alterar valor em fatura PAGA, o usuario
        deve reverter primeiro (desconciliar → desanexar).
        """
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        operacao = db.session.get(CarviaOperacao, operacao_id)
        if not operacao:
            flash('Operacao nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_operacoes'))

        # Guard centralizado no model (Sprint 0)
        pode, razao = operacao.pode_editar_valor()
        if not pode:
            flash(razao, 'warning')
            return redirect(url_for('carvia.detalhe_operacao', operacao_id=operacao_id))

        cte_valor_raw = request.form.get('cte_valor', '').strip()
        if not cte_valor_raw:
            flash('Informe o valor do CTe.', 'warning')
            return redirect(url_for('carvia.detalhe_operacao', operacao_id=operacao_id))

        try:
            # Parse formato BR: "1.234,56" -> 1234.56
            cte_valor = float(cte_valor_raw.replace('.', '').replace(',', '.'))
        except (ValueError, TypeError):
            flash('Valor invalido.', 'danger')
            return redirect(url_for('carvia.detalhe_operacao', operacao_id=operacao_id))

        try:
            valor_anterior = float(operacao.cte_valor or 0)
            operacao.cte_valor = cte_valor

            # NAO recalcular fatura.valor_total — fatura e entidade
            # independente (alinhado com modulo de fretes).

            db.session.commit()
            logger.info(
                f"Operacao #{operacao_id}: cte_valor alterado "
                f"R$ {valor_anterior:.2f} -> R$ {cte_valor:.2f} "
                f"por {current_user.email}"
            )
            flash(f'Valor CTe atualizado: R$ {cte_valor:.2f}', 'success')
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao editar cte_valor operacao #{operacao_id}: {e}")
            flash(f'Erro: {e}', 'danger')

        return redirect(url_for('carvia.detalhe_operacao', operacao_id=operacao_id))

    # ==================== VINCULAR/DESVINCULAR NFs ====================

    @bp.route('/api/operacao/<int:operacao_id>/vincular-nf', methods=['POST'])
    @login_required
    def api_vincular_nf_operacao(operacao_id):
        """Vincula NF a operacao via junction carvia_operacao_nfs."""
        if not getattr(current_user, 'sistema_carvia', False):
            return {'sucesso': False, 'erro': 'Acesso negado.'}, 403

        operacao = db.session.get(CarviaOperacao, operacao_id)
        if not operacao:
            return {'sucesso': False, 'erro': 'Operacao nao encontrada.'}, 404

        data = request.get_json()
        if not data:
            return {'sucesso': False, 'erro': 'Body JSON obrigatorio.'}, 400

        nf_id = data.get('nf_id')
        if not nf_id:
            return {'sucesso': False, 'erro': 'nf_id obrigatorio.'}, 400

        nf = db.session.get(CarviaNf, nf_id)
        if not nf:
            return {'sucesso': False, 'erro': 'NF nao encontrada.'}, 404

        try:
            # Verificar duplicata
            existente = db.session.query(CarviaOperacaoNf).filter_by(
                operacao_id=operacao_id, nf_id=nf_id
            ).first()
            if existente:
                return {'sucesso': False, 'erro': 'NF ja vinculada a esta operacao.'}, 400

            junction = CarviaOperacaoNf(operacao_id=operacao_id, nf_id=nf_id)
            db.session.add(junction)

            # Recalcular peso_bruto como soma das NFs.
            # W3 fix (Sprint 2 followup): assignment incondicional — simetria
            # com api_desvincular_nf_operacao. Antes tinha guard `if peso_total > 0`
            # que deixava peso stale ao vincular NF com peso=0.
            nfs_vinculadas = operacao.nfs.all()
            peso_total = (
                sum(float(n.peso_bruto or 0) for n in nfs_vinculadas)
                + float(nf.peso_bruto or 0)
            )
            operacao.peso_bruto = peso_total
            operacao.calcular_peso_utilizado()

            db.session.commit()

            logger.info(
                f"NF #{nf_id} vinculada a operacao #{operacao_id} por {current_user.email}"
            )
            return {
                'sucesso': True,
                'peso_utilizado': float(operacao.peso_utilizado or 0),
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao vincular NF #{nf_id} a operacao #{operacao_id}: {e}")
            return {'sucesso': False, 'erro': str(e)}, 500

    @bp.route('/api/operacao/<int:operacao_id>/desvincular-nf/<int:nf_id>', methods=['POST'])
    @login_required
    def api_desvincular_nf_operacao(operacao_id, nf_id):
        """Remove vinculo NF<->Operacao.

        W2 (Sprint 2): bloqueia se operacao FATURADA ou se NF esta em
        items de fatura. Tambem corrige bug do W3 — remover a ultima NF
        agora seta peso_bruto = 0 (antes mantinha valor stale).
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return {'sucesso': False, 'erro': 'Acesso negado.'}, 403

        operacao = db.session.get(CarviaOperacao, operacao_id)
        if not operacao:
            return {'sucesso': False, 'erro': 'Operacao nao encontrada.'}, 404

        nf = db.session.get(CarviaNf, nf_id)
        if not nf:
            return {'sucesso': False, 'erro': 'NF nao encontrada.'}, 404

        # Guard centralizado no model (Sprint 0)
        pode, razao = nf.pode_desvincular_de_operacao(operacao_id)
        if not pode:
            return {'sucesso': False, 'erro': razao}, 400

        try:
            deleted = CarviaOperacaoNf.query.filter_by(
                operacao_id=operacao_id, nf_id=nf_id
            ).delete()

            if not deleted:
                return {'sucesso': False, 'erro': 'Vinculo nao encontrado.'}, 404

            # Recalcular peso_bruto — W3: sempre setar, mesmo se 0
            nfs_vinculadas = operacao.nfs.all()
            peso_total = sum(float(n.peso_bruto or 0) for n in nfs_vinculadas)
            operacao.peso_bruto = peso_total
            operacao.calcular_peso_utilizado()

            db.session.commit()

            logger.info(
                f"NF #{nf_id} desvinculada de operacao #{operacao_id} por {current_user.email}"
            )
            return {
                'sucesso': True,
                'peso_utilizado': float(operacao.peso_utilizado or 0),
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao desvincular NF #{nf_id} de operacao #{operacao_id}: {e}")
            return {'sucesso': False, 'erro': str(e)}, 500

    @bp.route('/api/operacao/<int:operacao_id>/nfs-disponiveis')
    @login_required
    def api_nfs_disponiveis(operacao_id):
        """Lista NFs disponiveis para vinculacao (sem operacao ou do mesmo cliente)."""
        if not getattr(current_user, 'sistema_carvia', False):
            return {'sucesso': False, 'erro': 'Acesso negado.'}, 403

        operacao = db.session.get(CarviaOperacao, operacao_id)
        if not operacao:
            return {'sucesso': False, 'erro': 'Operacao nao encontrada.'}, 404

        busca = request.args.get('busca', '')

        # NFs que nao estao vinculadas a NENHUMA operacao
        subq_vinculadas = db.session.query(CarviaOperacaoNf.nf_id)
        query = db.session.query(CarviaNf).filter(
            CarviaNf.status == 'ATIVA',
            ~CarviaNf.id.in_(subq_vinculadas),
        )

        if busca:
            busca_like = f'%{busca}%'
            query = query.filter(
                db.or_(
                    CarviaNf.numero_nf.ilike(busca_like),
                    CarviaNf.nome_emitente.ilike(busca_like),
                    CarviaNf.cnpj_emitente.ilike(busca_like),
                )
            )

        nfs = query.order_by(CarviaNf.criado_em.desc()).limit(50).all()

        return {
            'sucesso': True,
            'nfs': [{
                'id': nf.id,
                'numero_nf': nf.numero_nf,
                'nome_emitente': nf.nome_emitente,
                'cnpj_emitente': nf.cnpj_emitente,
                'valor_total': float(nf.valor_total) if nf.valor_total else None,
                'peso_bruto': float(nf.peso_bruto) if nf.peso_bruto else None,
                'tipo_fonte': nf.tipo_fonte,
            } for nf in nfs],
        }

    @bp.route('/api/operacao/<int:operacao_id>/subcontrato/<int:sub_id>/simular-recotacao')
    @login_required
    def simular_recotacao(operacao_id, sub_id):
        """Retorna descritivo enriquecido da recotacao (AJAX GET)"""
        if not getattr(current_user, 'sistema_carvia', False):
            from flask import jsonify
            return jsonify({'erro': 'Acesso negado'}), 403

        sub = db.session.get(CarviaSubcontrato, sub_id)
        if not sub or sub.operacao_id != operacao_id:
            from flask import jsonify
            return jsonify({'erro': 'Subcontrato nao encontrado'}), 404

        try:
            from flask import jsonify
            from app.carvia.services.pricing.cotacao_service import CotacaoService
            resultado = CotacaoService().cotar_subcontrato_com_descritivo(
                operacao_id=operacao_id,
                transportadora_id=sub.transportadora_id,
            )
            return jsonify(resultado)

        except Exception as e:
            from flask import jsonify
            logger.error(f"Erro ao simular recotacao: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/operacoes/<int:operacao_id>/subcontrato/<int:sub_id>/recotar', methods=['POST'])
    @login_required
    def recotar_subcontrato_from_operacao(operacao_id, sub_id):
        """Recalcula cotacao de um subcontrato. Aceita valor_override opcional."""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        sub = db.session.get(CarviaSubcontrato, sub_id)
        if not sub or sub.operacao_id != operacao_id:
            flash('Subcontrato nao encontrado.', 'warning')
            return redirect(url_for('carvia.listar_operacoes'))

        try:
            # Verificar se usuario enviou valor manual (campo editavel do modal)
            valor_override_raw = request.form.get('valor_override', '').strip()
            valor_override = None
            if valor_override_raw:
                try:
                    valor_override = float(
                        valor_override_raw.replace('.', '').replace(',', '.')
                    )
                except (ValueError, TypeError):
                    pass

            from app.carvia.services.pricing.cotacao_service import CotacaoService
            cotacao = CotacaoService().cotar_subcontrato(
                operacao_id=operacao_id,
                transportadora_id=sub.transportadora_id,
            )

            if cotacao.get('sucesso'):
                # Se tem valor_override valido, usar em vez do calculado
                if valor_override and valor_override > 0:
                    sub.valor_cotado = valor_override
                    logger.info(
                        f"Recotacao sub #{sub_id}: valor override "
                        f"R$ {valor_override:.2f} (calculado: R$ {cotacao['valor_cotado']:.2f})"
                    )
                else:
                    sub.valor_cotado = cotacao['valor_cotado']

                sub.tabela_frete_id = cotacao.get('tabela_frete_id')
                if sub.status == 'PENDENTE':
                    sub.status = 'COTADO'
                db.session.commit()
                flash(f'Recotacao: R$ {float(sub.valor_cotado):.2f}', 'success')
            else:
                flash(f'Erro na recotacao: {cotacao.get("erro")}', 'warning')

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao recotar: {e}")
            flash(f'Erro: {e}', 'danger')

        return redirect(url_for('carvia.detalhe_operacao', operacao_id=operacao_id))
