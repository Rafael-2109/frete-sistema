"""
Rotas de NF Venda CarVia — Listagem, detalhe e cancelamento de NFs importadas
"""

import logging
from collections import defaultdict
from datetime import datetime

from flask import render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func, text

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
        data_emissao_de = request.args.get('data_emissao_de', '')
        data_emissao_ate = request.args.get('data_emissao_ate', '')
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
            # Subquery: NF ids vinculadas a CTe com numero ou CTRC matching
            cte_match_subq = db.session.query(
                CarviaOperacaoNf.nf_id
            ).join(
                CarviaOperacao,
                CarviaOperacaoNf.operacao_id == CarviaOperacao.id
            ).filter(
                db.or_(
                    CarviaOperacao.cte_numero.ilike(busca_like),
                    CarviaOperacao.ctrc_numero.ilike(busca_like),
                )
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

        # Filtro date range
        if data_emissao_de:
            try:
                dt_de = datetime.strptime(data_emissao_de, '%Y-%m-%d').date()
                query = query.filter(CarviaNf.data_emissao >= dt_de)
            except ValueError:
                pass
        if data_emissao_ate:
            try:
                dt_ate = datetime.strptime(data_emissao_ate, '%Y-%m-%d').date()
                query = query.filter(CarviaNf.data_emissao <= dt_ate)
            except ValueError:
                pass

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
        ctes_por_nf = defaultdict(list)
        frete_id_por_nf = {}
        cotacao_id_por_nf = {}

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

            # Query 4: CTes vinculados por NF (numeros + ids para badges inline)
            rows_cte = db.session.query(
                CarviaOperacaoNf.nf_id,
                CarviaOperacao.id,
                CarviaOperacao.cte_numero,
                CarviaOperacao.ctrc_numero,
            ).join(
                CarviaOperacao,
                CarviaOperacaoNf.operacao_id == CarviaOperacao.id,
            ).filter(
                CarviaOperacaoNf.nf_id.in_(nf_ids)
            ).all()
            seen_cte = set()
            for nf_id, op_id, cte_num, ctrc_num in rows_cte:
                key = (nf_id, op_id)
                if key not in seen_cte:
                    seen_cte.add(key)
                    ctes_por_nf[nf_id].append({'id': op_id, 'cte_numero': cte_num, 'ctrc_numero': ctrc_num})

            # Query 5: Frete ID por NF (para indicador clicavel na listagem)
            from app.carvia.models import CarviaFrete

            rows_frete = db.session.query(
                CarviaOperacaoNf.nf_id,
                func.min(CarviaFrete.id).label('frete_id')
            ).join(
                CarviaFrete,
                CarviaFrete.operacao_id == CarviaOperacaoNf.operacao_id
            ).filter(
                CarviaOperacaoNf.nf_id.in_(nf_ids),
                CarviaFrete.status != 'CANCELADO'
            ).group_by(CarviaOperacaoNf.nf_id).all()
            frete_id_por_nf = {nf_id: frete_id for nf_id, frete_id in rows_frete}

            # Query 6: Cotacao ID por NF (via pedido_itens.numero_nf → pedido → cotacao)
            # numero_nf NAO e unique — multiplas NFs podem compartilhar o mesmo numero
            # (emitentes diferentes). Usar mapping 1:N para nao perder NFs.
            from app.carvia.models.cotacao import CarviaPedidoItem, CarviaPedido

            numero_to_nf_ids = defaultdict(list)
            for nf_item, _ in paginacao.items:
                if nf_item.numero_nf:
                    numero_to_nf_ids[nf_item.numero_nf].append(nf_item.id)

            cotacao_id_por_nf = {}
            if numero_to_nf_ids:
                rows_cot = db.session.query(
                    CarviaPedidoItem.numero_nf,
                    CarviaPedido.cotacao_id
                ).join(
                    CarviaPedido,
                    CarviaPedidoItem.pedido_id == CarviaPedido.id
                ).filter(
                    CarviaPedidoItem.numero_nf.in_(list(numero_to_nf_ids.keys())),
                    CarviaPedido.status != 'CANCELADO',
                    CarviaPedido.cotacao_id.isnot(None),
                ).distinct().all()
                for num_nf, cot_id in rows_cot:
                    for nf_id in numero_to_nf_ids.get(num_nf, []):
                        if nf_id not in cotacao_id_por_nf:
                            cotacao_id_por_nf[nf_id] = cot_id

        # Batch: peso cubado por NF (2 queries)
        from app.carvia.services.pricing.moto_recognition_service import MotoRecognitionService
        moto_svc = MotoRecognitionService()
        peso_cubado_por_nf = moto_svc.calcular_peso_cubado_batch(nf_ids) if nf_ids else {}

        # Batch: resolver clientes comerciais por CNPJ destinatario
        import re
        from app.carvia.services.clientes.cliente_service import CarviaClienteService
        cnpjs_dest = {nf.cnpj_destinatario for nf, _ in paginacao.items if nf.cnpj_destinatario}
        _resolved = CarviaClienteService.resolver_clientes_por_cnpjs(cnpjs_dest)
        clientes_por_cnpj = {
            cnpj: _resolved[re.sub(r'\D', '', cnpj)]
            for cnpj in cnpjs_dest
            if re.sub(r'\D', '', cnpj) in _resolved
        }

        return render_template(
            'carvia/nfs/listar.html',
            nfs=paginacao.items,
            paginacao=paginacao,
            busca=busca,
            tipo_filtro=tipo_filtro,
            status_filtro=status_filtro,
            cte_filtro=cte_filtro,
            uf_filtro=uf_filtro,
            data_emissao_de=data_emissao_de,
            data_emissao_ate=data_emissao_ate,
            sort=sort,
            direction=direction,
            faturas_por_nf=faturas_por_nf,
            subcontratos_por_nf=subcontratos_por_nf,
            faturas_transp_por_nf=faturas_transp_por_nf,
            ctes_por_nf=ctes_por_nf,
            peso_cubado_por_nf=peso_cubado_por_nf,
            clientes_por_cnpj=clientes_por_cnpj,
            frete_id_por_nf=frete_id_por_nf,
            cotacao_id_por_nf=cotacao_id_por_nf,
        )

    # ==================== HELPER: ÚLTIMOS FRETES ====================

    def _buscar_ultimos_fretes_destino(cnpj_destinatario, cidade_destinatario, nf_id_atual, limite=5):
        """Busca ultimos fretes (operacoes) para mesmo destinatario + cidade.

        Retorna {'moto': [...], 'geral': [...]} com ate `limite` registros cada.
        Moto = operacao tem itens com modelo_moto_id IS NOT NULL.
        Geral = sem itens moto.
        Contagem de motos via SUM(carvia_nf_itens.quantidade) — carvia_nf_veiculos nao populado.
        Peso cubado via peso_medio do modelo (todos os modelos possuem peso_medio).
        """
        sql = text("""
            WITH ops_destino AS (
                SELECT DISTINCT co.id as op_id, co.cte_valor, co.peso_bruto,
                       co.peso_utilizado, co.criado_em
                FROM carvia_operacoes co
                JOIN carvia_operacao_nfs con ON con.operacao_id = co.id
                JOIN carvia_nfs cn ON cn.id = con.nf_id
                WHERE cn.cnpj_destinatario = :cnpj_dest
                  AND UPPER(cn.cidade_destinatario) = UPPER(:cidade_dest)
                  AND cn.status = 'ATIVA'
                  AND co.cte_valor IS NOT NULL AND co.cte_valor > 0
                  AND co.status != 'CANCELADO'
                  AND NOT EXISTS (
                      SELECT 1 FROM carvia_operacao_nfs con_excl
                      WHERE con_excl.operacao_id = co.id AND con_excl.nf_id = :nf_id_atual
                  )
            )
            SELECT od.op_id, od.cte_valor, od.peso_bruto, od.peso_utilizado, od.criado_em,
                   (SELECT string_agg(DISTINCT cn2.numero_nf, ', ')
                    FROM carvia_operacao_nfs con2
                    JOIN carvia_nfs cn2 ON cn2.id = con2.nf_id
                    WHERE con2.operacao_id = od.op_id AND cn2.status = 'ATIVA') as numeros_nfs,
                   (SELECT COALESCE(SUM(cni.quantidade), 0)
                    FROM carvia_operacao_nfs con3
                    JOIN carvia_nf_itens cni ON cni.nf_id = con3.nf_id
                    WHERE con3.operacao_id = od.op_id AND cni.modelo_moto_id IS NOT NULL) as qtd_motos,
                   (SELECT COALESCE(SUM(cni.quantidade * mm.peso_medio), 0)
                    FROM carvia_operacao_nfs con4
                    JOIN carvia_nf_itens cni ON cni.nf_id = con4.nf_id
                    JOIN carvia_modelos_moto mm ON mm.id = cni.modelo_moto_id
                    WHERE con4.operacao_id = od.op_id AND cni.modelo_moto_id IS NOT NULL) as peso_cubado_motos
            FROM ops_destino od
            ORDER BY od.criado_em DESC
        """)

        try:
            rows = db.session.execute(sql, {
                'cnpj_dest': cnpj_destinatario,
                'cidade_dest': cidade_destinatario,
                'nf_id_atual': nf_id_atual,
            }).fetchall()
        except Exception:
            logger.exception('Erro ao buscar ultimos fretes destino')
            return {'moto': [], 'geral': []}

        moto_fretes = []
        geral_fretes = []

        for row in rows:
            qtd_motos = float(row.qtd_motos or 0)

            if qtd_motos > 0:
                if len(moto_fretes) < limite:
                    peso_cubado_medio = float(row.peso_cubado_motos or 0) / qtd_motos
                    frete_por_moto = float(row.cte_valor or 0) / qtd_motos
                    moto_fretes.append({
                        'operacao_id': row.op_id,
                        'numeros_nfs': row.numeros_nfs or '',
                        'qtd_motos': int(qtd_motos),
                        'peso_cubado_medio': round(peso_cubado_medio, 1),
                        'frete_por_moto': round(frete_por_moto, 2),
                        'frete_total': float(row.cte_valor or 0),
                    })
            else:
                if len(geral_fretes) < limite:
                    peso_total = float(row.peso_utilizado or row.peso_bruto or 0)
                    rs_por_kg = float(row.cte_valor or 0) / peso_total if peso_total > 0 else 0
                    geral_fretes.append({
                        'operacao_id': row.op_id,
                        'numeros_nfs': row.numeros_nfs or '',
                        'peso_total': round(peso_total, 1),
                        'rs_por_kg': round(rs_por_kg, 2),
                        'frete_total': float(row.cte_valor or 0),
                    })

            if len(moto_fretes) >= limite and len(geral_fretes) >= limite:
                break

        return {'moto': moto_fretes, 'geral': geral_fretes}

    # ==================== DETALHE NF ====================

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

        # Fretes CarVia vinculados a esta NF (por numero_nf + CNPJ emitente/destino)
        # Re-review Sprint 2 IMP-2: usar match por boundaries (como em
        # CarviaNf.pode_cancelar) para evitar false positives em display.
        # Ex: NF "123" nao deve bater com frete que tem numeros_nfs="1234,5678".
        from app.carvia.models import CarviaFrete
        fretes_nf = []
        if nf.numero_nf:
            fretes_nf = CarviaFrete.query.filter(
                CarviaFrete.cnpj_emitente == nf.cnpj_emitente,
                CarviaFrete.cnpj_destino == nf.cnpj_destinatario,
                CarviaFrete.status != 'CANCELADO',
                db.or_(
                    CarviaFrete.numeros_nfs == nf.numero_nf,
                    CarviaFrete.numeros_nfs.like(f"{nf.numero_nf},%"),
                    CarviaFrete.numeros_nfs.like(f"%,{nf.numero_nf},%"),
                    CarviaFrete.numeros_nfs.like(f"%,{nf.numero_nf}"),
                ),
            ).all()
        tem_frete = bool(fretes_nf)
        tem_cte = bool(operacoes)

        # Ultimos fretes para mesmo destino (referencia de precos)
        ultimos_fretes = {'moto': [], 'geral': []}
        nf_eh_moto = bool(resultado_cubagem and resultado_cubagem.get('itens'))
        if nf.cnpj_destinatario and nf.cidade_destinatario:
            ultimos_fretes = _buscar_ultimos_fretes_destino(
                nf.cnpj_destinatario, nf.cidade_destinatario, nf.id,
            )

        # Custos de entrega e CTes complementares via operacoes
        from app.carvia.models import CarviaCustoEntrega, CarviaCteComplementar
        custos_entrega = []
        ctes_complementares = []
        if op_ids:
            custos_entrega = CarviaCustoEntrega.query.filter(
                CarviaCustoEntrega.operacao_id.in_(op_ids)
            ).order_by(CarviaCustoEntrega.criado_em.desc()).all()
            ctes_complementares = CarviaCteComplementar.query.filter(
                CarviaCteComplementar.operacao_id.in_(op_ids)
            ).order_by(CarviaCteComplementar.criado_em.desc()).all()

        # Resolver cliente comercial por CNPJ destinatario
        import re
        from app.carvia.services.clientes.cliente_service import CarviaClienteService
        _clientes = CarviaClienteService.resolver_clientes_por_cnpjs({nf.cnpj_destinatario})
        cliente_destino = _clientes.get(re.sub(r'\D', '', nf.cnpj_destinatario or ''))

        # Indicador: cotacao vinculada? (com ID para link no header)
        from app.carvia.models.cotacao import CarviaPedidoItem, CarviaPedido
        cotacao_id_nf = None
        if nf.numero_nf:
            row_cot = db.session.query(CarviaPedido.cotacao_id).join(
                CarviaPedidoItem, CarviaPedidoItem.pedido_id == CarviaPedido.id
            ).filter(
                CarviaPedidoItem.numero_nf == nf.numero_nf,
                CarviaPedido.status != 'CANCELADO',
                CarviaPedido.cotacao_id.isnot(None),
            ).first()
            if row_cot:
                cotacao_id_nf = row_cot[0]

        # Indicador: fatura cliente paga?
        fat_cliente_paga = any(f.status == 'PAGA' for f in faturas_cliente)

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
            ultimos_fretes=ultimos_fretes,
            nf_eh_moto=nf_eh_moto,
            fretes_nf=fretes_nf,
            tem_frete=tem_frete,
            tem_cte=tem_cte,
            custos_entrega=custos_entrega,
            ctes_complementares=ctes_complementares,
            cliente_destino=cliente_destino,
            cotacao_id_nf=cotacao_id_nf,
            fat_cliente_paga=fat_cliente_paga,
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
                cte_data_emissao=nf.data_emissao,
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
        """Cancela uma NF (soft-delete conforme GAP-20).

        W2 (Sprint 2): bloqueia se NF esta vinculada a CTe CarVia,
        Fatura Cliente ou Fatura Transportadora. Usuario deve
        reverter docs superiores primeiro (ordem inversa do fluxo).
        """
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        nf = db.session.get(CarviaNf, nf_id)
        if not nf:
            flash('NF nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_nfs'))

        # Guard centralizado no model (Sprint 0)
        pode, razao = nf.pode_cancelar()
        if not pode:
            flash(razao, 'warning')
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

    # ==================== REPROCESSAR PDF (itens + motos) ====================

    @bp.route('/nfs/<int:nf_id>/reprocessar-pdf', methods=['POST'])
    @login_required
    def reprocessar_pdf_nf(nf_id):
        """Re-baixa PDF do S3, re-parseia itens e roda deteccao de motos.

        Util quando o parser foi corrigido apos a importacao original.
        Se a NF ja tem itens, apenas atualiza descricoes truncadas e re-roda motos.
        Se nao tem itens, insere todos do parse.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        nf = db.session.get(CarviaNf, nf_id)
        if not nf:
            return jsonify({'erro': 'NF nao encontrada.'}), 404

        if not nf.arquivo_pdf_path:
            return jsonify({'erro': 'NF sem arquivo PDF armazenado.'}), 400

        try:
            from app.utils.file_storage import get_file_storage
            from app.carvia.services.parsers.danfe_pdf_parser import DanfePDFParser
            from app.carvia.models import CarviaNfItem
            from app.carvia.services.pricing.moto_recognition_service import (
                MotoRecognitionService,
            )

            storage = get_file_storage()
            pdf_bytes = storage.download_file(nf.arquivo_pdf_path)
            if not pdf_bytes:
                return jsonify({'erro': 'Falha ao baixar PDF do storage.'}), 500

            parser = DanfePDFParser(pdf_bytes=pdf_bytes)
            if not parser.is_valid():
                return jsonify({'erro': 'PDF invalido pelo parser.'}), 400

            # Parse completo (header + itens + veiculos, com fallback LLM)
            dados = parser.get_todas_informacoes()

            # --- Atualizar campos header vazios/None ---
            campos_header_map = {
                'chave_acesso_nf': 'chave_acesso_nf',
                'numero_nf': 'numero_nf',
                'cnpj_emitente': 'cnpj_emitente',
                'nome_emitente': 'nome_emitente',
                'uf_emitente': 'uf_emitente',
                'cidade_emitente': 'cidade_emitente',
                'cnpj_destinatario': 'cnpj_destinatario',
                'nome_destinatario': 'nome_destinatario',
                'uf_destinatario': 'uf_destinatario',
                'cidade_destinatario': 'cidade_destinatario',
                'valor_total': 'valor_total',
                'data_emissao': 'data_emissao',
            }

            campos_atualizados = 0
            for campo_parser, campo_model in campos_header_map.items():
                valor_novo = dados.get(campo_parser)
                if valor_novo is not None:
                    valor_atual = getattr(nf, campo_model, None)
                    if not valor_atual:  # None ou string vazia
                        setattr(nf, campo_model, valor_novo)
                        campos_atualizados += 1
            db.session.flush()

            # --- Processar itens ---
            itens_parseados = dados.get('itens', [])
            itens_existentes = CarviaNfItem.query.filter_by(nf_id=nf.id).all()

            itens_inseridos = 0
            desc_atualizadas = 0

            if not itens_existentes:
                # Sem itens — inserir todos
                for item_data in itens_parseados:
                    item = CarviaNfItem(
                        nf_id=nf.id,
                        codigo_produto=item_data.get('codigo_produto'),
                        descricao=item_data.get('descricao'),
                        ncm=item_data.get('ncm'),
                        cfop=item_data.get('cfop'),
                        unidade=item_data.get('unidade'),
                        quantidade=item_data.get('quantidade'),
                        valor_unitario=item_data.get('valor_unitario'),
                        valor_total_item=item_data.get('valor_total_item'),
                    )
                    db.session.add(item)
                    itens_inseridos += 1
                db.session.flush()
            else:
                # Com itens existentes — atualizar descricoes truncadas
                for existente in itens_existentes:
                    for item_data in itens_parseados:
                        if (item_data.get('ncm') == existente.ncm
                                and item_data.get('codigo_produto') == existente.codigo_produto):
                            desc_nova = item_data.get('descricao', '')
                            desc_atual = existente.descricao or ''
                            if len(desc_nova) > len(desc_atual):
                                existente.descricao = desc_nova
                                desc_atualizadas += 1
                            break
                db.session.flush()

            # Persistir veiculos (chassi/modelo/cor) extraidos do DANFE
            from app.carvia.models import CarviaNfVeiculo
            veiculos_parseados = dados.get('veiculos', [])
            veic_inseridos = 0
            for v_data in veiculos_parseados:
                chassi = (v_data.get('chassi') or '').strip()
                if not chassi:
                    continue
                existente = CarviaNfVeiculo.query.filter_by(chassi=chassi).first()
                if existente:
                    continue
                db.session.add(CarviaNfVeiculo(
                    nf_id=nf.id,
                    chassi=chassi,
                    modelo=v_data.get('modelo'),
                    cor=v_data.get('cor'),
                    numero_motor=v_data.get('numero_motor'),
                    ano=v_data.get('ano_modelo'),
                ))
                veic_inseridos += 1

            # Rodar deteccao de motos
            moto_svc = MotoRecognitionService()
            moto_resultado = moto_svc.reprocessar_itens_nf(nf.id)
            db.session.commit()

            logger.info(
                "Reprocessamento PDF NF %d por %s: %d parseados, "
                "%d inseridos, %d desc atualizadas, %d motos, "
                "%d veiculos, %d campos header, metodo=%s",
                nf.id, current_user.email, len(itens_parseados),
                itens_inseridos, desc_atualizadas,
                moto_resultado.get('detectados', 0),
                veic_inseridos,
                campos_atualizados, dados.get('metodo_extracao', '?'),
            )

            return jsonify({
                'sucesso': True,
                'itens_parseados': len(itens_parseados),
                'itens_inseridos': itens_inseridos,
                'desc_atualizadas': desc_atualizadas,
                'veiculos_inseridos': veic_inseridos,
                'campos_header_atualizados': campos_atualizados,
                'motos_detectadas': moto_resultado.get('detectados', 0),
                'motos_limpas': moto_resultado.get('limpos', 0),
                'metodo_extracao': dados.get('metodo_extracao', 'REGEX'),
            })
        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao reprocessar PDF NF %d: %s", nf_id, e)
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
