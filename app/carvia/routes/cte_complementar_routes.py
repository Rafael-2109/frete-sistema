"""
Rotas de CTe Complementar CarVia — CRUD completo
"""

import logging
from datetime import date, datetime

from flask import (
    render_template, request, flash, redirect, url_for, Response,
)
from flask_login import login_required, current_user

from app import db
from app.carvia.models import (
    CarviaCteComplementar, CarviaOperacao, CarviaCustoEntrega,
    CarviaEmissaoCteComplementar,
)

logger = logging.getLogger(__name__)

STATUS_CTE_COMP = ['RASCUNHO', 'EMITIDO', 'FATURADO', 'CANCELADO']


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
            query = query.filter(
                db.or_(
                    CarviaCteComplementar.numero_comp.ilike(busca_like),
                    CarviaCteComplementar.cnpj_cliente.ilike(busca_like),
                    CarviaCteComplementar.nome_cliente.ilike(busca_like),
                    CarviaCteComplementar.ctrc_numero.ilike(busca_like),
                    CarviaCteComplementar.observacoes.ilike(busca_like),
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

        return render_template(
            'carvia/ctes_complementares/listar.html',
            ctes_complementares=paginacao.items,
            paginacao=paginacao,
            op_info_map=op_info_map,
            operacao_filtro=operacao_filtro,
            status_filtro=status_filtro,
            busca=busca,
            data_emissao_de=data_emissao_de,
            data_emissao_ate=data_emissao_ate,
            sort=sort,
            direction=direction,
            status_list=STATUS_CTE_COMP,
        )

    @bp.route('/ctes-complementares/criar/<int:operacao_id>', methods=['GET', 'POST']) # type: ignore
    @login_required
    def criar_cte_complementar(operacao_id): # type: ignore
        """Cria novo CTe complementar vinculado a uma operacao"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        operacao = db.session.get(CarviaOperacao, operacao_id)
        if not operacao:
            flash('Operacao nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_ctes_complementares'))

        if request.method == 'POST':
            cte_valor_str = request.form.get('cte_valor', '').strip()
            cte_data_emissao_str = request.form.get('cte_data_emissao', '').strip()
            cte_numero = request.form.get('cte_numero', '').strip()
            cte_chave_acesso = request.form.get('cte_chave_acesso', '').strip()
            observacoes = request.form.get('observacoes', '').strip()

            # Validacoes
            if not cte_valor_str:
                flash('Valor do CTe complementar e obrigatorio.', 'warning')
                return redirect(url_for(
                    'carvia.criar_cte_complementar', operacao_id=operacao_id
                ))

            try:
                cte_valor = float(cte_valor_str.replace(',', '.'))
                if cte_valor <= 0:
                    flash('Valor deve ser maior que zero.', 'warning')
                    return redirect(url_for(
                        'carvia.criar_cte_complementar', operacao_id=operacao_id
                    ))

                cte_data_emissao = (
                    date.fromisoformat(cte_data_emissao_str)
                    if cte_data_emissao_str else None
                )

                numero_comp = CarviaCteComplementar.gerar_numero_comp()

                cte_comp = CarviaCteComplementar(
                    numero_comp=numero_comp,
                    operacao_id=operacao_id,
                    cte_valor=cte_valor,
                    cte_numero=cte_numero or None,
                    cte_chave_acesso=cte_chave_acesso or None,
                    cte_data_emissao=cte_data_emissao,
                    cnpj_cliente=operacao.cnpj_cliente,
                    nome_cliente=operacao.nome_cliente,
                    status='RASCUNHO',
                    observacoes=observacoes or None,
                    criado_por=current_user.email,
                )
                db.session.add(cte_comp)
                db.session.flush()

                # Vincular ao CarviaFrete pela operacao_id
                if cte_comp.operacao_id:
                    from app.carvia.models import CarviaFrete
                    frete = CarviaFrete.query.filter_by(
                        operacao_id=cte_comp.operacao_id
                    ).first()
                    if frete:
                        cte_comp.frete_id = frete.id

                db.session.commit()

                flash(
                    f'CTe Complementar {cte_comp.numero_comp} criado com sucesso.',
                    'success',
                )
                return redirect(url_for(
                    'carvia.detalhe_cte_complementar', cte_comp_id=cte_comp.id
                ))

            except ValueError as ve:
                flash(f'Dados invalidos: {ve}', 'warning')
            except Exception as e:
                db.session.rollback()
                logger.error(f"Erro ao criar CTe complementar: {e}")
                flash(f'Erro: {e}', 'danger')

        return render_template(
            'carvia/ctes_complementares/criar.html',
            operacao=operacao,
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

        return render_template(
            'carvia/ctes_complementares/detalhe.html',
            cte_comp=cte_comp,
            custos_vinculados=custos_vinculados,
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
            # Validar transicoes permitidas
            if novo_status == 'EMITIDO' and cte_comp.status != 'RASCUNHO':
                flash('Somente CTe em RASCUNHO pode ser EMITIDO.', 'warning')
                return redirect(url_for(
                    'carvia.detalhe_cte_complementar', cte_comp_id=cte_comp_id
                ))

            if novo_status == 'CANCELADO' and cte_comp.status == 'FATURADO':
                flash('Nao e possivel cancelar CTe complementar FATURADO.', 'warning')
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
        """Download do DACTE PDF do CTe Complementar (via emissao.resultado_json)."""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        cte_comp = db.session.get(CarviaCteComplementar, cte_comp_id)
        if not cte_comp:
            flash('CTe Complementar nao encontrado.', 'warning')
            return redirect(url_for('carvia.listar_ctes_complementares'))

        # Localizar caminho do DACTE no resultado_json da emissao vinculada
        dacte_path = None
        dacte_filename = None
        emissao = db.session.query(CarviaEmissaoCteComplementar).filter(
            CarviaEmissaoCteComplementar.cte_complementar_id == cte_comp_id,
            CarviaEmissaoCteComplementar.status == 'SUCESSO',
        ).order_by(
            CarviaEmissaoCteComplementar.criado_em.desc()
        ).first()

        if emissao and isinstance(emissao.resultado_json, dict):
            dacte_path = emissao.resultado_json.get('dacte_s3_path')
            dacte_filename = emissao.resultado_json.get('dacte_nome_arquivo')

        if not dacte_path:
            flash('DACTE nao disponivel para este CTe Complementar.', 'warning')
            return redirect(
                request.referrer
                or url_for('carvia.detalhe_cte_complementar', cte_comp_id=cte_comp_id)
            )

        filename = (
            dacte_filename
            or f"{cte_comp.ctrc_numero or cte_comp.numero_comp}-dacte.pdf"
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
