"""
Rotas de NF Venda CarVia — Listagem, detalhe e cancelamento de NFs importadas
"""

import logging
from collections import defaultdict
from flask import render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func

from app import db
from app.carvia.models import (
    CarviaNf, CarviaOperacao, CarviaOperacaoNf,
    CarviaFaturaCliente, CarviaFaturaClienteItem,
    CarviaSubcontrato,
    CarviaFaturaTransportadora, CarviaFaturaTransportadoraItem,
)
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)


def register_nf_routes(bp):

    @bp.route('/nfs')
    @login_required
    def listar_nfs():
        """Lista NFs importadas com filtros e paginacao"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 25, type=int)
        busca = request.args.get('busca', '')
        tipo_filtro = request.args.get('tipo_fonte', '')
        status_filtro = request.args.get('status', '')
        cte_filtro = request.args.get('cte', '')
        uf_filtro = request.args.get('uf_destino', '')
        sort = request.args.get('sort', 'data_emissao')
        direction = request.args.get('direction', 'desc')

        # Subquery: contar CTes vinculados a cada NF
        subq_ctes = db.session.query(
            CarviaOperacaoNf.nf_id,
            func.count(CarviaOperacaoNf.operacao_id).label('qtd_ctes')
        ).group_by(CarviaOperacaoNf.nf_id).subquery()

        query = db.session.query(
            CarviaNf, subq_ctes.c.qtd_ctes
        ).outerjoin(
            subq_ctes, CarviaNf.id == subq_ctes.c.nf_id
        )

        # Filtro de status: por padrao exclui CANCELADA
        if status_filtro == 'CANCELADA':
            query = query.filter(CarviaNf.status == 'CANCELADA')
        elif status_filtro == 'TODAS':
            pass  # Sem filtro de status
        else:
            # Padrao: apenas ATIVA
            query = query.filter(CarviaNf.status != 'CANCELADA')

        if tipo_filtro:
            query = query.filter(CarviaNf.tipo_fonte == tipo_filtro)

        if busca:
            busca_like = f'%{busca}%'
            # Subquery: NF ids vinculadas a CTe com numero matching
            cte_match_subq = db.session.query(
                CarviaOperacaoNf.nf_id
            ).join(
                CarviaOperacao,
                CarviaOperacaoNf.operacao_id == CarviaOperacao.id
            ).filter(
                CarviaOperacao.cte_numero.ilike(busca_like)
            ).subquery()

            query = query.filter(
                db.or_(
                    CarviaNf.numero_nf.ilike(busca_like),
                    CarviaNf.nome_emitente.ilike(busca_like),
                    CarviaNf.cnpj_emitente.ilike(busca_like),
                    CarviaNf.nome_destinatario.ilike(busca_like),
                    CarviaNf.chave_acesso_nf.ilike(busca_like),
                    CarviaNf.cidade_destinatario.ilike(busca_like),
                    CarviaNf.cnpj_destinatario.ilike(busca_like),
                    CarviaNf.id.in_(cte_match_subq),
                )
            )

        # Filtro CTe: com/sem CTe vinculado
        if cte_filtro == 'COM':
            query = query.filter(subq_ctes.c.qtd_ctes > 0)
        elif cte_filtro == 'SEM':
            query = query.filter(
                db.or_(subq_ctes.c.qtd_ctes.is_(None), subq_ctes.c.qtd_ctes == 0)
            )

        # Filtro UF destinatario (exact match)
        if uf_filtro:
            query = query.filter(CarviaNf.uf_destinatario == uf_filtro.upper())

        # Ordenacao dinamica
        sortable_columns = {
            'numero_nf': func.lpad(func.coalesce(CarviaNf.numero_nf, ''), 20, '0'),
            'emitente': CarviaNf.nome_emitente,
            'valor_total': CarviaNf.valor_total,
            'data_emissao': CarviaNf.data_emissao,
            'criado_em': CarviaNf.criado_em,
        }
        sort_col = sortable_columns.get(sort, CarviaNf.data_emissao)
        if direction == 'asc':
            query = query.order_by(sort_col.asc().nullslast())
        else:
            query = query.order_by(sort_col.desc().nullslast())

        paginacao = query.paginate(page=page, per_page=per_page, error_out=False)

        # Batch queries para colunas vinculadas (evita N+1)
        nf_ids = [nf.id for nf, _ in paginacao.items]

        faturas_por_nf = defaultdict(list)
        subcontratos_por_nf = defaultdict(list)
        faturas_transp_por_nf = defaultdict(list)

        if nf_ids:
            # Query 1: Faturas cliente via itens
            rows_fat = db.session.query(
                CarviaFaturaClienteItem.nf_id,
                CarviaFaturaCliente
            ).join(
                CarviaFaturaCliente,
                CarviaFaturaClienteItem.fatura_cliente_id == CarviaFaturaCliente.id
            ).filter(
                CarviaFaturaClienteItem.nf_id.in_(nf_ids)
            ).all()
            seen_fat = set()
            for nf_id, fatura in rows_fat:
                key = (nf_id, fatura.id)
                if key not in seen_fat:
                    seen_fat.add(key)
                    faturas_por_nf[nf_id].append(fatura)

            # Query 2: Subcontratos via junction -> operacao -> subcontrato
            rows_sub = db.session.query(
                CarviaOperacaoNf.nf_id,
                CarviaSubcontrato
            ).join(
                CarviaSubcontrato,
                CarviaOperacaoNf.operacao_id == CarviaSubcontrato.operacao_id
            ).filter(
                CarviaOperacaoNf.nf_id.in_(nf_ids)
            ).all()
            seen_sub = set()
            for nf_id, sub in rows_sub:
                key = (nf_id, sub.id)
                if key not in seen_sub:
                    seen_sub.add(key)
                    subcontratos_por_nf[nf_id].append(sub)

            # Query 3: Faturas transportadora via itens
            rows_fat_transp = db.session.query(
                CarviaFaturaTransportadoraItem.nf_id,
                CarviaFaturaTransportadora
            ).join(
                CarviaFaturaTransportadora,
                CarviaFaturaTransportadoraItem.fatura_transportadora_id == CarviaFaturaTransportadora.id
            ).filter(
                CarviaFaturaTransportadoraItem.nf_id.in_(nf_ids)
            ).all()
            seen_fat_transp = set()
            for nf_id, fat_transp in rows_fat_transp:
                key = (nf_id, fat_transp.id)
                if key not in seen_fat_transp:
                    seen_fat_transp.add(key)
                    faturas_transp_por_nf[nf_id].append(fat_transp)

        # Batch: peso cubado por NF (2 queries)
        from app.carvia.services.pricing.moto_recognition_service import MotoRecognitionService
        moto_svc = MotoRecognitionService()
        peso_cubado_por_nf = moto_svc.calcular_peso_cubado_batch(nf_ids) if nf_ids else {}

        return render_template(
            'carvia/nfs/listar.html',
            nfs=paginacao.items,
            paginacao=paginacao,
            busca=busca,
            tipo_filtro=tipo_filtro,
            status_filtro=status_filtro,
            cte_filtro=cte_filtro,
            uf_filtro=uf_filtro,
            sort=sort,
            direction=direction,
            faturas_por_nf=faturas_por_nf,
            subcontratos_por_nf=subcontratos_por_nf,
            faturas_transp_por_nf=faturas_transp_por_nf,
            peso_cubado_por_nf=peso_cubado_por_nf,
        )

    @bp.route('/nfs/<int:nf_id>')
    @login_required
    def detalhe_nf(nf_id):
        """Detalhe de uma NF com itens e cross-link para CTes CarVia"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        nf = db.session.get(CarviaNf, nf_id)
        if not nf:
            flash('NF nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_nfs'))

        itens = nf.itens.all()
        veiculos = nf.veiculos.all()

        # Operacoes vinculadas (CTes CarVia) via junction
        operacoes = nf.operacoes.all()

        # Cross-links: subcontratos, faturas cliente, faturas transportadora
        from app.carvia.models import CarviaSubcontrato
        op_ids = [op.id for op in operacoes]
        subcontratos = []
        if op_ids:
            subcontratos = CarviaSubcontrato.query.filter(
                CarviaSubcontrato.operacao_id.in_(op_ids)
            ).all()

        faturas_cliente = nf.get_faturas_cliente()
        faturas_transportadora = nf.get_faturas_transportadora()

        # Peso cubado a partir do modelo_moto_id persistido nos itens
        from app.carvia.services.pricing.moto_recognition_service import MotoRecognitionService
        moto_svc = MotoRecognitionService()
        resultado_cubagem = moto_svc.calcular_peso_cubado_nf(nf.id)
        peso_cubado = (
            resultado_cubagem['peso_cubado_total']
            if resultado_cubagem else None
        )
        # Mapa item_id -> dados cubagem (peso, modelo, dimensoes) para exibir por linha
        cubagem_por_item = {}
        if resultado_cubagem and resultado_cubagem.get('itens'):
            for ic in resultado_cubagem['itens']:
                cubagem_por_item[ic['item_id']] = ic

        # Peso para cotacao: max(bruto, cubado)
        peso_para_cotacao = max(
            float(nf.peso_bruto or 0),
            float(peso_cubado or 0),
        )

        return render_template(
            'carvia/nfs/detalhe.html',
            nf=nf,
            itens=itens,
            veiculos=veiculos,
            operacoes=operacoes,
            subcontratos=subcontratos,
            faturas_cliente=faturas_cliente,
            faturas_transportadora=faturas_transportadora,
            peso_cubado=peso_cubado,
            cubagem_por_item=cubagem_por_item,
            peso_para_cotacao=peso_para_cotacao,
        )

    # ==================== CRIAR CTE VIA NF ====================

    @bp.route('/nfs/<int:nf_id>/criar-cte', methods=['POST'])
    @login_required
    def criar_cte_from_nf(nf_id):
        """Cria CTe CarVia (CarviaOperacao) a partir de uma NF"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        nf = db.session.get(CarviaNf, nf_id)
        if not nf:
            flash('NF nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_nfs'))

        if nf.status == 'CANCELADA':
            flash('NF cancelada nao pode gerar CTe.', 'warning')
            return redirect(url_for('carvia.detalhe_nf', nf_id=nf_id))

        # Parse valor CTe (formato BR: "1.234,56" -> 1234.56)
        cte_valor_raw = request.form.get('cte_valor', '').strip()
        if not cte_valor_raw:
            flash('Informe o valor do CTe.', 'warning')
            return redirect(url_for('carvia.detalhe_nf', nf_id=nf_id))

        try:
            cte_valor = float(cte_valor_raw.replace('.', '').replace(',', '.'))
        except (ValueError, TypeError):
            flash('Valor do CTe invalido.', 'danger')
            return redirect(url_for('carvia.detalhe_nf', nf_id=nf_id))

        observacoes = request.form.get('observacoes', '').strip()

        try:
            operacao = CarviaOperacao(
                cnpj_cliente=nf.cnpj_emitente,
                nome_cliente=nf.nome_emitente or nf.cnpj_emitente,
                uf_origem=nf.uf_emitente,
                cidade_origem=nf.cidade_emitente,
                uf_destino=nf.uf_destinatario or '',
                cidade_destino=nf.cidade_destinatario or '',
                peso_bruto=nf.peso_bruto,
                valor_mercadoria=nf.valor_total,
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
            db.session.flush()

            # Criar junction NF <-> Operacao
            junction = CarviaOperacaoNf(
                operacao_id=operacao.id,
                nf_id=nf.id,
            )
            db.session.add(junction)
            db.session.commit()

            logger.info(
                f"CTe CarVia #{operacao.id} ({operacao.cte_numero}) criado a partir de NF #{nf.id} "
                f"por {current_user.email}"
            )
            flash(
                f'CTe CarVia {operacao.cte_numero} criado com sucesso a partir da NF {nf.numero_nf}.',
                'success'
            )
            return redirect(url_for('carvia.detalhe_operacao', operacao_id=operacao.id))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao criar CTe via NF {nf_id}: {e}")
            flash(f'Erro ao criar CTe: {e}', 'danger')
            return redirect(url_for('carvia.detalhe_nf', nf_id=nf_id))

    # ==================== CANCELAR NF ====================

    @bp.route('/nfs/<int:nf_id>/cancelar', methods=['POST'])
    @login_required
    def cancelar_nf(nf_id):
        """Cancela uma NF (soft-delete conforme GAP-20)"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        nf = db.session.get(CarviaNf, nf_id)
        if not nf:
            flash('NF nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_nfs'))

        if nf.status == 'CANCELADA':
            flash('NF ja esta cancelada.', 'warning')
            return redirect(url_for('carvia.detalhe_nf', nf_id=nf_id))

        motivo = request.form.get('motivo_cancelamento', '').strip()
        if not motivo:
            flash('Motivo de cancelamento e obrigatorio.', 'warning')
            return redirect(url_for('carvia.detalhe_nf', nf_id=nf_id))

        try:
            nf.status = 'CANCELADA'
            nf.cancelado_em = agora_utc_naive()
            nf.cancelado_por = current_user.email
            nf.motivo_cancelamento = motivo
            db.session.commit()

            logger.info(
                f"NF cancelada: nf_id={nf.id} numero={nf.numero_nf} "
                f"por={current_user.email} motivo={motivo}"
            )
            flash(f'NF {nf.numero_nf} cancelada com sucesso.', 'success')
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao cancelar NF {nf_id}: {e}")
            flash(f'Erro ao cancelar NF: {e}', 'danger')

        return redirect(url_for('carvia.detalhe_nf', nf_id=nf_id))

    # ==================== RE-PROCESSAR MOTOS ====================

    @bp.route('/nfs/<int:nf_id>/reprocessar-motos', methods=['POST'])
    @login_required
    def reprocessar_motos_nf(nf_id):
        """Re-roda deteccao de motos nos itens da NF e persiste resultado."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        nf = db.session.get(CarviaNf, nf_id)
        if not nf:
            return jsonify({'erro': 'NF nao encontrada.'}), 404

        try:
            from app.carvia.services.pricing.moto_recognition_service import (
                MotoRecognitionService,
            )
            moto_svc = MotoRecognitionService()
            resultado = moto_svc.reprocessar_itens_nf(nf.id)
            db.session.commit()

            logger.info(
                "Re-processamento motos NF %d por %s: %s",
                nf.id, current_user.email, resultado,
            )
            return jsonify({
                'sucesso': True,
                'total_itens': resultado['total_itens'],
                'detectados': resultado['detectados'],
                'limpos': resultado['limpos'],
            })
        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao reprocessar motos NF %d: %s", nf_id, e)
            return jsonify({'erro': str(e)}), 500

    # ==================== EDITAR MODELO MOTO EM ITEM ====================

    @bp.route('/api/nf-item/<int:item_id>/modelo-moto', methods=['POST'])
    @login_required
    def editar_modelo_moto_item(item_id):
        """Altera o modelo de moto de um item de NF (override manual)."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.models import CarviaNfItem

        item = db.session.get(CarviaNfItem, item_id)
        if not item:
            return jsonify({'erro': 'Item nao encontrado.'}), 404

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados JSON invalidos.'}), 400

        modelo_moto_id = data.get('modelo_moto_id')

        # None/0 = limpar modelo
        if not modelo_moto_id:
            item.modelo_moto_id = None
            db.session.commit()
            logger.info(
                "Modelo moto removido: item_id=%d por=%s",
                item_id, current_user.email,
            )
            return jsonify({'sucesso': True, 'modelo_moto_id': None, 'modelo_nome': None})

        # Validar que modelo existe
        from app.carvia.models import CarviaModeloMoto
        modelo = db.session.get(CarviaModeloMoto, modelo_moto_id)
        if not modelo:
            return jsonify({'erro': f'Modelo {modelo_moto_id} nao encontrado.'}), 404

        item.modelo_moto_id = modelo.id
        db.session.commit()

        logger.info(
            "Modelo moto alterado: item_id=%d modelo=%s por=%s",
            item_id, modelo.nome, current_user.email,
        )
        return jsonify({
            'sucesso': True,
            'modelo_moto_id': modelo.id,
            'modelo_nome': modelo.nome,
        })
