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
                    CarviaOperacao.cidade_destino.ilike(busca_like),
                    CarviaOperacao.id.in_(nf_match_subq),
                )
            )

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
        if op_ids:
            rows_nf = db.session.query(
                CarviaOperacaoNf.operacao_id,
                CarviaNf.id,
                CarviaNf.numero_nf,
                CarviaNf.nome_destinatario,
                CarviaNf.nome_emitente,
            ).join(
                CarviaNf, CarviaOperacaoNf.nf_id == CarviaNf.id
            ).filter(
                CarviaOperacaoNf.operacao_id.in_(op_ids)
            ).all()
            seen_nf = set()
            for oid, nf_id, num_nf, dest, emit in rows_nf:
                key = (oid, nf_id)
                if key not in seen_nf:
                    seen_nf.add(key)
                    nfs_por_op[oid].append({'id': nf_id, 'numero_nf': num_nf})
                if oid not in dest_por_op:
                    dest_por_op[oid] = {'destinatario': dest, 'embarcador': emit}

        # Subquery: info de subcontrato (transportadora subcontratada + cte subcontrato)
        from app.transportadoras.models import Transportadora
        sub_info = {}
        if op_ids:
            sub_info_raw = db.session.query(
                CarviaSubcontrato.operacao_id,
                Transportadora.razao_social,
                CarviaSubcontrato.cte_numero,
            ).join(
                Transportadora, CarviaSubcontrato.transportadora_id == Transportadora.id
            ).filter(
                CarviaSubcontrato.status != 'CANCELADO',
                CarviaSubcontrato.operacao_id.in_(op_ids),
            ).order_by(CarviaSubcontrato.operacao_id, CarviaSubcontrato.id).all()

            for op_id, razao, cte_num in sub_info_raw:
                if op_id not in sub_info:
                    sub_info[op_id] = {'transp_nome': razao, 'sub_cte': cte_num, 'count': 0}
                sub_info[op_id]['count'] += 1

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

        return render_template(
            'carvia/detalhe_operacao.html',
            operacao=operacao,
            nfs=nfs,
            subcontratos=subcontratos,
            faturas_transportadora=faturas_transportadora,
            ctes_complementares=ctes_complementares,
            custos_entrega=custos_entrega,
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

        # GAP-18: Preservar dados do formulario para re-render apos erro
        form_data = {
            'nf_ids': nf_ids_raw,
            'cte_valor': cte_valor_raw,
            'observacoes': observacoes,
        }

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
            # GAP-02: CONFERIDO e pos-FATURADO, nao deve ser cancelado em cascata
            for sub in operacao.subcontratos.filter(
                CarviaSubcontrato.status.notin_(['FATURADO', 'CONFERIDO', 'CANCELADO'])
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
        """Atualiza valor acertado de um subcontrato"""
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
            from app.carvia.models import CarviaFaturaClienteItem
            itens = db.session.query(CarviaFaturaClienteItem).filter_by(
                fatura_cliente_id=fatura_id,
                operacao_id=operacao_id,
            ).all()
            for item in itens:
                item.operacao_id = None

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
        """Edita valor do CTe CarVia. Se FATURADO, recalcula valor_total da fatura."""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        operacao = db.session.get(CarviaOperacao, operacao_id)
        if not operacao:
            flash('Operacao nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_operacoes'))

        if operacao.status == 'CANCELADO':
            flash('Operacao cancelada nao pode ser editada.', 'warning')
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

            # Se operacao faturada, recalcular valor_total da fatura
            if operacao.fatura_cliente_id:
                fatura = operacao.fatura_cliente
                if fatura:
                    soma = db.session.query(
                        func.coalesce(func.sum(CarviaOperacao.cte_valor), 0)
                    ).filter(
                        CarviaOperacao.fatura_cliente_id == fatura.id,
                    ).scalar()
                    fatura.valor_total = soma
                    logger.info(
                        f"Fatura #{fatura.id}: valor_total recalculado para {soma} "
                        f"(editar CTe #{operacao_id} por {current_user.email})"
                    )

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

            # Recalcular peso_bruto como soma das NFs
            nfs_vinculadas = operacao.nfs.all()
            peso_total = sum(float(n.peso_bruto or 0) for n in nfs_vinculadas) + float(nf.peso_bruto or 0)
            if peso_total > 0:
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
        """Remove vinculo NF<->Operacao."""
        if not getattr(current_user, 'sistema_carvia', False):
            return {'sucesso': False, 'erro': 'Acesso negado.'}, 403

        operacao = db.session.get(CarviaOperacao, operacao_id)
        if not operacao:
            return {'sucesso': False, 'erro': 'Operacao nao encontrada.'}, 404

        try:
            deleted = CarviaOperacaoNf.query.filter_by(
                operacao_id=operacao_id, nf_id=nf_id
            ).delete()

            if not deleted:
                return {'sucesso': False, 'erro': 'Vinculo nao encontrado.'}, 404

            # Recalcular peso_bruto
            nfs_vinculadas = operacao.nfs.all()
            peso_total = sum(float(n.peso_bruto or 0) for n in nfs_vinculadas)
            if peso_total >= 0:
                operacao.peso_bruto = peso_total if peso_total > 0 else operacao.peso_bruto
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
