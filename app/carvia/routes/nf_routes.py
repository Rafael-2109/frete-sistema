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
        # NF Triangular: oculta transferencias efetivas por default
        mostrar_transferencias = request.args.get(
            'mostrar_transferencias', '0'
        ) == '1'
        # Filtro "Apenas NF nao entregues" — default OFF; '1' explicito liga
        apenas_nao_entregues = request.args.get('nao_entregue', '') == '1'
        # Filtro "Apenas Emb. Pendente" — default OFF; '1' liga. Mostra NFs que NAO
        # sairam da portaria (em embarque sem data_embarque OU sem embarque algum).
        emb_pendente = request.args.get('emb_pendente', '') == '1'

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

        # Filtro "Apenas NF nao entregues": exclui NFs cuja entrega (origem
        # CARVIA) ja foi realizada. Match por numero_nf (chave da entrega).
        # Lazy import R1-safe (CarVia nao depende de app/monitoramento).
        if apenas_nao_entregues:
            from app.monitoramento.models import EntregaMonitorada
            entregues_nums = db.session.query(
                EntregaMonitorada.numero_nf
            ).filter(
                EntregaMonitorada.entregue.is_(True),
                EntregaMonitorada.origem == 'CARVIA',
            )
            query = query.filter(CarviaNf.numero_nf.notin_(entregues_nums))

        # Filtro "Apenas Emb. Pendente": exclui NFs que JA sairam da portaria
        # (= embarque com data_embarque preenchida) por qualquer caminho. As que
        # restam estao em embarque sem saida OU nao constam em embarque nenhum.
        # Lazy import R1-safe. Match NF<->embarque por 2 vias (mesma uniao do badge):
        #   (a) embarque_itens CARVIA-* ativo (match por numero_nf);
        #   (b) operacao -> CarviaFrete -> Embarque (pega EI cancelado/ausente).
        if emb_pendente:
            from app.embarques.models import Embarque, EmbarqueItem
            from app.carvia.models import CarviaFrete
            saiu_ei_notas = db.session.query(
                EmbarqueItem.nota_fiscal
            ).join(
                Embarque, Embarque.id == EmbarqueItem.embarque_id
            ).filter(
                EmbarqueItem.separacao_lote_id.like('CARVIA-%'),
                EmbarqueItem.status == 'ativo',
                EmbarqueItem.nota_fiscal.isnot(None),
                Embarque.data_embarque.isnot(None),
            )
            # Via frete: so conta como "saiu" se a NF NAO tem EmbarqueItem CARVIA
            # (mesma regra do badge — EI ativo ja entra por saiu_ei_notas; EI cancelado
            # = a NF saiu daquele embarque, nao "saiu da portaria"). Alias evita colisao
            # com o CarviaNf da query externa.
            CarviaNfFrete = db.aliased(CarviaNf)
            saiu_frete_nf_ids = db.session.query(
                CarviaOperacaoNf.nf_id
            ).join(
                CarviaFrete, CarviaFrete.operacao_id == CarviaOperacaoNf.operacao_id
            ).join(
                Embarque, Embarque.id == CarviaFrete.embarque_id
            ).join(
                CarviaNfFrete, CarviaNfFrete.id == CarviaOperacaoNf.nf_id
            ).filter(
                CarviaFrete.status != 'CANCELADO',
                Embarque.data_embarque.isnot(None),
                ~db.session.query(EmbarqueItem.id).filter(
                    EmbarqueItem.nota_fiscal == CarviaNfFrete.numero_nf,
                    EmbarqueItem.separacao_lote_id.like('CARVIA-%'),
                ).exists(),
            )
            query = query.filter(
                CarviaNf.numero_nf.notin_(saiu_ei_notas),
                CarviaNf.id.notin_(saiu_frete_nf_ids),
            )

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

        # NF Triangular: filtra transferencias efetivas (default oculta)
        if not mostrar_transferencias:
            from app.carvia.models.documentos import CarviaNfVinculoTransferencia
            subq_transf_efetivas = db.session.query(
                CarviaNfVinculoTransferencia.nf_transferencia_id
            ).distinct().subquery()
            query = query.filter(~CarviaNf.id.in_(subq_transf_efetivas))

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
                CarviaOperacao.status,
            ).join(
                CarviaOperacao,
                CarviaOperacaoNf.operacao_id == CarviaOperacao.id,
            ).filter(
                CarviaOperacaoNf.nf_id.in_(nf_ids)
            ).all()
            seen_cte = set()
            for nf_id, op_id, cte_num, ctrc_num, op_status in rows_cte:
                key = (nf_id, op_id)
                if key not in seen_cte:
                    seen_cte.add(key)
                    ctes_por_nf[nf_id].append({
                        'id': op_id, 'cte_numero': cte_num,
                        'ctrc_numero': ctrc_num, 'status': op_status,
                    })

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

        # NF Triangular: marker de NFs que sao transferencia efetiva
        # (so eh util quando mostrar_transferencias=True)
        from app.carvia.models.documentos import CarviaNfVinculoTransferencia
        ids_transf_efetivas = set()
        if nf_ids:
            rows_vt = db.session.query(
                CarviaNfVinculoTransferencia.nf_transferencia_id
            ).filter(
                CarviaNfVinculoTransferencia.nf_transferencia_id.in_(nf_ids)
            ).distinct().all()
            ids_transf_efetivas = {r[0] for r in rows_vt}

        # NF Triangular: para cada NF venda nesta pagina, qual transferencia
        # esta vinculada. Dict {nf_venda_id: {'id': transf_id, 'numero': '####'}}
        num_nf_transf_por_venda = {}
        if nf_ids:
            NfTransf = db.aliased(CarviaNf, name='nf_transf')
            rows_vinc = db.session.query(
                CarviaNfVinculoTransferencia.nf_venda_id,
                NfTransf.id,
                NfTransf.numero_nf,
            ).join(
                NfTransf, NfTransf.id == CarviaNfVinculoTransferencia.nf_transferencia_id,
            ).filter(
                CarviaNfVinculoTransferencia.nf_venda_id.in_(nf_ids),
            ).all()
            num_nf_transf_por_venda = {
                venda_id: {'id': transf_id, 'numero': transf_num}
                for venda_id, transf_id, transf_num in rows_vinc
            }

        from app.carvia.services.documentos.comprovante_service import (
            CarviaComprovanteService,
        )
        tem_comprovante = CarviaComprovanteService.tem_comprovante_batch(
            'nf', [nf.id for nf, _ in paginacao.items]
        )

        # Batch: status de entrega/coleta/recebimento/embarque por NF (badges)
        # Todos lazy (R1) — CarVia nao depende de monitoramento/embarques.
        entregue_por_nf = {}        # nf_id -> data_hora_entrega_realizada
        coleta_receb_por_nf = {}    # nf_id -> {'coletado_em', 'recebido_em'}
        embarque_por_nf = {}        # nf_id -> {'id', 'numero'}
        if nf_ids:
            # 1) Entregue (EntregaMonitorada origem CARVIA, match por numero_nf)
            numeros_nf = {nf.numero_nf for nf, _ in paginacao.items if nf.numero_nf}
            if numeros_nf:
                from app.monitoramento.models import EntregaMonitorada
                rows_ent = db.session.query(
                    EntregaMonitorada.numero_nf,
                    EntregaMonitorada.data_hora_entrega_realizada,
                ).filter(
                    EntregaMonitorada.numero_nf.in_(list(numeros_nf)),
                    EntregaMonitorada.entregue.is_(True),
                    EntregaMonitorada.origem == 'CARVIA',
                ).all()
                ent_por_numero = {}
                for num, dt in rows_ent:
                    atual = ent_por_numero.get(num)
                    if num not in ent_por_numero or (
                        dt is not None and (atual is None or dt > atual)
                    ):
                        ent_por_numero[num] = dt
                for nf, _ in paginacao.items:
                    if nf.numero_nf in ent_por_numero:
                        entregue_por_nf[nf.id] = ent_por_numero[nf.numero_nf]

            # 2) Coleta + Recebimento (CarVia nativos; carvia_nf_id e UNIQUE)
            from app.carvia.models import (
                CarviaColeta, CarviaColetaNf, CarviaColetaRecebimento,
            )
            rows_col = db.session.query(
                CarviaColetaNf.carvia_nf_id,
                CarviaColeta.data_coletada_em,
                CarviaColetaRecebimento.status,
                CarviaColetaRecebimento.concluido_em,
            ).join(
                CarviaColeta, CarviaColeta.id == CarviaColetaNf.coleta_id
            ).outerjoin(
                CarviaColetaRecebimento,
                CarviaColetaRecebimento.coleta_id == CarviaColeta.id,
            ).filter(
                CarviaColetaNf.carvia_nf_id.in_(nf_ids),
            ).all()
            for cnf_id, col_em, rec_status, rec_concl in rows_col:
                if cnf_id not in coleta_receb_por_nf:
                    coleta_receb_por_nf[cnf_id] = {
                        'coletado_em': col_em,
                        'recebido_em': rec_concl if rec_status == 'CONCLUIDO' else None,
                    }

            # 3) Embarque — UNIAO de 2 caminhos (R1 lazy). data_embarque (carimbada
            # na portaria) = saida fisica do CD => badge verde com a data. Quando ha
            # mais de um embarque por NF, prioriza o que JA saiu (com data_embarque).
            #   (a) embarque_itens CARVIA-* ativo (match por numero_nf) — pega NFs em
            #       embarque AINDA SEM CTe/frete lancados (pre-portaria). Caminho que
            #       faltava: 61 de 330 NFs em embarque nao tinham badge (ex.: NF 2044).
            #   (b) operacao -> CarviaFrete -> Embarque — pega os casos cujo EI esta
            #       cancelado/ausente mas o frete segue vinculado ao embarque.
            from app.carvia.models import CarviaFrete
            from app.embarques.models import Embarque, EmbarqueItem

            def _registrar_embarque(nf_id_key, emb_id, emb_num, emb_data):
                atual = embarque_por_nf.get(nf_id_key)
                # registra se ainda nao ha, OU se este saiu da portaria e o anterior nao
                if atual is None or (
                    emb_data is not None and atual.get('data_embarque') is None
                ):
                    embarque_por_nf[nf_id_key] = {
                        'id': emb_id, 'numero': emb_num, 'data_embarque': emb_data,
                    }

            # mapa numero_nf -> nf_ids da pagina (numero_nf NAO e unico — R1)
            numero_to_nf_ids_emb = defaultdict(list)
            for nf_pg, _ in paginacao.items:
                if nf_pg.numero_nf:
                    numero_to_nf_ids_emb[nf_pg.numero_nf].append(nf_pg.id)

            # (a) via embarque_itens
            if numero_to_nf_ids_emb:
                rows_ei = db.session.query(
                    EmbarqueItem.nota_fiscal,
                    Embarque.id,
                    Embarque.numero,
                    Embarque.data_embarque,
                ).join(
                    Embarque, Embarque.id == EmbarqueItem.embarque_id
                ).filter(
                    EmbarqueItem.nota_fiscal.in_(list(numero_to_nf_ids_emb.keys())),
                    EmbarqueItem.separacao_lote_id.like('CARVIA-%'),
                    EmbarqueItem.status == 'ativo',
                ).all()
                for nota, emb_id, emb_num, emb_data in rows_ei:
                    for nf_id_e in numero_to_nf_ids_emb.get(nota, []):
                        _registrar_embarque(nf_id_e, emb_id, emb_num, emb_data)

            # NFs (da pagina) que TEM algum EmbarqueItem CARVIA (qualquer status):
            # a via (b) NAO vale para elas — EI ativo ja foi pego em (a); EI cancelado
            # sem ativo = a NF saiu daquele embarque (decisao 2026-06-23). A via (b) e
            # fallback so para NF SEM item (frete sem EmbarqueItem correspondente).
            notas_com_ei_carvia = set()
            if numero_to_nf_ids_emb:
                rows_tem_ei = db.session.query(
                    EmbarqueItem.nota_fiscal
                ).filter(
                    EmbarqueItem.nota_fiscal.in_(list(numero_to_nf_ids_emb.keys())),
                    EmbarqueItem.separacao_lote_id.like('CARVIA-%'),
                ).distinct().all()
                notas_com_ei_carvia = {r[0] for r in rows_tem_ei}
            nf_id_to_numero = {
                nf_pg.id: nf_pg.numero_nf for nf_pg, _ in paginacao.items
            }

            # (b) via operacao -> CarviaFrete -> Embarque (so NF SEM EI CARVIA)
            rows_emb = db.session.query(
                CarviaOperacaoNf.nf_id,
                Embarque.id,
                Embarque.numero,
                Embarque.data_embarque,
            ).join(
                CarviaFrete,
                CarviaFrete.operacao_id == CarviaOperacaoNf.operacao_id,
            ).join(
                Embarque, Embarque.id == CarviaFrete.embarque_id
            ).filter(
                CarviaOperacaoNf.nf_id.in_(nf_ids),
                CarviaFrete.status != 'CANCELADO',
                CarviaFrete.embarque_id.isnot(None),
            ).all()
            for nf_id_e, emb_id, emb_num, emb_data in rows_emb:
                if nf_id_to_numero.get(nf_id_e) in notas_com_ei_carvia:
                    continue
                _registrar_embarque(nf_id_e, emb_id, emb_num, emb_data)

        return render_template(
            'carvia/nfs/listar.html',
            nfs=paginacao.items,
            paginacao=paginacao,
            tem_comprovante=tem_comprovante,
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
            mostrar_transferencias=mostrar_transferencias,
            ids_transf_efetivas=ids_transf_efetivas,
            num_nf_transf_por_venda=num_nf_transf_por_venda,
            apenas_nao_entregues=apenas_nao_entregues,
            emb_pendente=emb_pendente,
            entregue_por_nf=entregue_por_nf,
            coleta_receb_por_nf=coleta_receb_por_nf,
            embarque_por_nf=embarque_por_nf,
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

        # Agregacao CTe por frete (evita N+1 no template que antes chamava
        # `frete.subcontratos.first()` em loop — lazy='dynamic')
        from app.carvia.routes.frete_routes import _build_cte_por_frete
        cte_por_frete = _build_cte_por_frete([f.id for f in fretes_nf])

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
        from app.carvia.models import CarviaCotacao
        cotacao_id_nf = None
        cotacao_obj = None
        pedidos_da_nf = []
        if nf.numero_nf:
            # Pedidos vinculados a esta NF
            pedidos_da_nf = (
                CarviaPedido.query
                .join(CarviaPedidoItem, CarviaPedidoItem.pedido_id == CarviaPedido.id)
                .filter(
                    CarviaPedidoItem.numero_nf == nf.numero_nf,
                    CarviaPedido.status != 'CANCELADO',
                )
                .distinct()
                .all()
            )
            if pedidos_da_nf:
                cotacao_id_nf = pedidos_da_nf[0].cotacao_id
                cotacao_obj = db.session.get(CarviaCotacao, cotacao_id_nf) if cotacao_id_nf else None

        # Indicador: fatura cliente paga?
        fat_cliente_paga = any(f.status == 'PAGA' for f in faturas_cliente)

        # NF Triangular: vinculo de transferencia (ambos os lados)
        from app.carvia.services.documentos.nf_transferencia_service import (
            CarviaNfTransferenciaService as _NFTS,
        )
        transf_vinculada = _NFTS.get_transferencia_de(nf.id)
        vendas_da_transf = _NFTS.get_vendas_de(nf.id)
        eh_transf_efetiva = bool(vendas_da_transf)
        eh_candidata_transf = _NFTS.eh_candidata_transferencia(nf)
        vinculo_transf_obj = _NFTS.get_vinculo_por_venda(nf.id)

        # Tomador do frete: primeira CarviaOperacao vinculada com cte_tomador populado
        from app.carvia.utils.tomador import tomador_label
        tomador_label_val = None
        for op in operacoes:
            if getattr(op, 'cte_tomador', None):
                tomador_label_val = tomador_label(op.cte_tomador)
                if tomador_label_val:
                    break

        # Ultima tentativa de emissao SSW (para banner de erro no modal)
        # Mostra status, etapa, erro_amigavel e filial usada na ultima rodada,
        # permitindo o operador entender o que deu errado antes de re-tentar.
        from app.carvia.models import CarviaEmissaoCte
        ultima_emissao_ssw = (
            CarviaEmissaoCte.query
            .filter_by(nf_id=nf.id)
            .order_by(CarviaEmissaoCte.id.desc())
            .first()
        )

        from app.carvia.services.documentos.comprovante_service import (
            CarviaComprovanteService,
        )
        comprovantes_nf = CarviaComprovanteService.listar('nf', nf.id)

        # Status de coleta/recebimento/embarque/entrega (badges) — todos lazy (R1)
        # Entregue: EntregaMonitorada origem CARVIA (match por numero_nf).
        # nf_entregue (bool) alinha o badge ao mesmo criterio do filtro
        # (entregue=True), mesmo que a data esteja ausente.
        entrega_data = None
        nf_entregue = False
        if nf.numero_nf:
            from app.monitoramento.models import EntregaMonitorada
            em = (
                EntregaMonitorada.query
                .filter(
                    EntregaMonitorada.numero_nf == nf.numero_nf,
                    EntregaMonitorada.entregue.is_(True),
                    EntregaMonitorada.origem == 'CARVIA',
                )
                .order_by(
                    EntregaMonitorada.data_hora_entrega_realizada.desc().nullslast()
                )
                .first()
            )
            if em:
                nf_entregue = True
                entrega_data = em.data_hora_entrega_realizada

        # Coleta + Recebimento (CarVia nativos; carvia_nf_id e UNIQUE → 0/1 linha)
        from app.carvia.models import CarviaColetaNf, CarviaColeta
        coleta_data = None
        recebimento_data = None
        col_nf = (
            CarviaColetaNf.query
            .filter(CarviaColetaNf.carvia_nf_id == nf.id)
            .first()
        )
        if col_nf:
            coleta = db.session.get(CarviaColeta, col_nf.coleta_id)
            if coleta:
                coleta_data = coleta.data_coletada_em
                rec = getattr(coleta, 'recebimento', None)
                if rec and rec.status == 'CONCLUIDO':
                    recebimento_data = rec.concluido_em

        # Embarque vinculado (primeiro frete com embarque)
        embarque_nf = None
        for f in fretes_nf:
            if getattr(f, 'embarque_id', None) and f.embarque is not None:
                embarque_nf = {
                    'id': f.embarque.id,
                    'numero': f.embarque.numero,
                    'data_embarque': getattr(f.embarque, 'data_embarque', None),
                }
                break

        return render_template(
            'carvia/nfs/detalhe.html',
            nf=nf,
            comprovantes_nf=comprovantes_nf,
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
            cotacao_obj=cotacao_obj,
            pedidos_da_nf=pedidos_da_nf,
            fat_cliente_paga=fat_cliente_paga,
            tomador_label=tomador_label_val,
            cte_por_frete=cte_por_frete,
            transf_vinculada=transf_vinculada,
            vendas_da_transf=vendas_da_transf,
            eh_transf_efetiva=eh_transf_efetiva,
            eh_candidata_transf=eh_candidata_transf,
            vinculo_transf_obj=vinculo_transf_obj,
            ultima_emissao_ssw=ultima_emissao_ssw,
            entrega_data=entrega_data,
            nf_entregue=nf_entregue,
            coleta_data=coleta_data,
            recebimento_data=recebimento_data,
            embarque_nf=embarque_nf,
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
            numero_nf_local = nf.numero_nf  # snapshot antes do commit
            nf.status = 'CANCELADA'
            nf.cancelado_em = agora_utc_naive()
            nf.cancelado_por = current_user.email
            nf.motivo_cancelamento = motivo
            db.session.commit()

            logger.info(
                f"NF cancelada: nf_id={nf.id} numero={numero_nf_local} "
                f"por={current_user.email} motivo={motivo}"
            )
            flash(f'NF {numero_nf_local} cancelada com sucesso.', 'success')

            # Hook monitoramento: marcar EntregaMonitorada CarVia como Cancelada
            # (nao-bloqueante: erro aqui nao reverte o cancelamento da NF)
            try:
                from app.utils.sincronizar_entregas_carvia import (
                    arquivar_entrega_carvia_cancelada,
                )
                arquivar_entrega_carvia_cancelada(numero_nf_local)
            except Exception as e_sync:
                logger.warning(
                    f"Sync monitoramento cancelamento NF {numero_nf_local} "
                    f"falhou: {e_sync}"
                )
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

    # ==================== DIVERGENCIA CNPJ vs COTACAO (Fase B4) ====================

    @bp.route('/nfs/<int:nf_id>/aplicar-cnpj-na-cotacao', methods=['POST'])
    @login_required
    def aplicar_cnpj_da_nf_na_cotacao(nf_id):
        """Aplica o CNPJ destinatario da NF na(s) cotacao(oes) vinculada(s).

        Fase B4 (2026-05-11). Usado quando a NF chegou com cnpj_destinatario
        diferente do cnpj do endereco destino da cotacao (sinalizado em
        carvia_nf.divergencia_cnpj_cotacao por expandir_provisorio).

        Acao:
            1. Para cada cotacao vinculada a NF (via CarviaPedido):
               - Procura CarviaClienteEndereco DESTINO ativo do cliente da
                 cotacao com cnpj == nf.cnpj_destinatario
               - Se nao existe: cria com dados da NF (uf, cidade, razao social)
               - Atualiza cotacao.endereco_destino_id
            2. Propaga para CarviaFretes vinculados ao embarque que ainda
               estao em PENDENTE (atualiza cnpj_destino, nome_destino, etc.).
            3. Limpa nf.divergencia_cnpj_cotacao = False
            4. Auditoria.

        Retorna JSON com resumo das mudancas.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.models import (
            CarviaPedido, CarviaPedidoItem,
            CarviaCotacao, CarviaClienteEndereco,
            CarviaFrete,
        )
        from app.embarques.models import EmbarqueItem

        nf = db.session.get(CarviaNf, nf_id)
        if not nf:
            return jsonify({'erro': 'NF nao encontrada.'}), 404

        if not nf.cnpj_destinatario:
            return jsonify({
                'erro': 'NF nao possui cnpj_destinatario para aplicar.'
            }), 400

        # 1. Encontrar cotacoes via CarviaPedidoItem.numero_nf
        cotacoes_ids = {
            cot_id for (cot_id,) in db.session.query(
                CarviaPedido.cotacao_id
            ).join(
                CarviaPedidoItem, CarviaPedidoItem.pedido_id == CarviaPedido.id
            ).filter(
                CarviaPedidoItem.numero_nf == nf.numero_nf,
                CarviaPedido.cotacao_id.isnot(None),
            ).distinct().all()
        }

        if not cotacoes_ids:
            return jsonify({
                'erro': (
                    f'Nenhuma cotacao encontrada para NF {nf.numero_nf}. '
                    'Verifique se ha CarviaPedidoItem vinculado.'
                ),
            }), 404

        resumo = {
            'nf_id': nf.id,
            'numero_nf': nf.numero_nf,
            'cnpj_aplicado': nf.cnpj_destinatario,
            'cotacoes_atualizadas': [],
            'enderecos_criados': [],
            'fretes_atualizados': [],
            'embarque_itens_atualizados': [],
        }

        try:
            for cot_id in cotacoes_ids:
                cotacao = db.session.get(CarviaCotacao, cot_id)
                if not cotacao or not cotacao.cliente_id:
                    continue
                # B4-Guard: nao tocar em cotacao CANCELADA (irrelevante) ou
                # FATURADO (alteracao retroativa quebraria auditoria — o
                # endereco que constou na fatura ja foi fechado).
                if cotacao.status in ('CANCELADO', 'FATURADO'):
                    logger.info(
                        "B4: cotacao %s status=%s — pulando atualizacao "
                        "(alteracao retroativa nao permitida).",
                        cotacao.id, cotacao.status,
                    )
                    continue

                # 2. Buscar endereco com CNPJ da NF para esse cliente
                endereco = CarviaClienteEndereco.query.filter_by(
                    cliente_id=cotacao.cliente_id,
                    cnpj=nf.cnpj_destinatario,
                    tipo='DESTINO',
                    ativo=True,
                ).first()

                # 3. Se nao existe, criar a partir dos dados da NF
                if not endereco:
                    endereco = CarviaClienteEndereco(
                        cliente_id=cotacao.cliente_id,
                        cnpj=nf.cnpj_destinatario,
                        razao_social=nf.nome_destinatario,
                        receita_uf=nf.uf_destinatario,
                        receita_cidade=nf.cidade_destinatario,
                        fisico_uf=nf.uf_destinatario,
                        fisico_cidade=nf.cidade_destinatario,
                        tipo='DESTINO',
                        principal=False,
                        provisorio=False,
                        ativo=True,
                        criado_por=current_user.email,
                    )
                    db.session.add(endereco)
                    db.session.flush()
                    resumo['enderecos_criados'].append({
                        'endereco_id': endereco.id,
                        'cnpj': endereco.cnpj,
                        'razao_social': endereco.razao_social,
                        'cliente_id': endereco.cliente_id,
                    })
                    logger.info(
                        "B4: novo CarviaClienteEndereco %s criado (cliente %s "
                        "cnpj %s) a partir da NF %s",
                        endereco.id, cotacao.cliente_id,
                        nf.cnpj_destinatario, nf.numero_nf,
                    )

                # 4. Atualizar endereco_destino_id da cotacao
                endereco_anterior_id = cotacao.endereco_destino_id
                cotacao.endereco_destino_id = endereco.id
                resumo['cotacoes_atualizadas'].append({
                    'cotacao_id': cotacao.id,
                    'numero_cotacao': cotacao.numero_cotacao,
                    'endereco_anterior_id': endereco_anterior_id,
                    'endereco_novo_id': endereco.id,
                })
                logger.info(
                    "B4: cotacao %s endereco_destino_id %s -> %s (cnpj %s)",
                    cotacao.id, endereco_anterior_id, endereco.id,
                    nf.cnpj_destinatario,
                )

            # 5. Propagar para EmbarqueItens da NF (defensivo —
            # expandir_provisorio ja faz isso, mas pode haver itens criados
            # antes da Fase B2 ou em fluxo manual).
            ei_atualizados = EmbarqueItem.query.filter_by(
                nota_fiscal=nf.numero_nf,
                status='ativo',
            ).all()
            for ei in ei_atualizados:
                if not str(ei.separacao_lote_id or '').startswith('CARVIA-'):
                    continue
                if ei.cnpj_cliente == nf.cnpj_destinatario:
                    continue
                cnpj_old = ei.cnpj_cliente
                ei.cnpj_cliente = nf.cnpj_destinatario
                if nf.nome_destinatario:
                    ei.cliente = nf.nome_destinatario
                if nf.uf_destinatario:
                    ei.uf_destino = nf.uf_destinatario
                if nf.cidade_destinatario:
                    ei.cidade_destino = nf.cidade_destinatario
                resumo['embarque_itens_atualizados'].append({
                    'embarque_item_id': ei.id,
                    'embarque_id': ei.embarque_id,
                    'cnpj_anterior': cnpj_old,
                    'cnpj_novo': nf.cnpj_destinatario,
                })

            # 6. Propagar para CarviaFretes PENDENTE com NF no CSV
            fretes_para_atualizar = CarviaFrete.query.filter(
                CarviaFrete.status == 'PENDENTE',
                CarviaFrete.numeros_nfs.isnot(None),
                db.or_(
                    CarviaFrete.numeros_nfs == nf.numero_nf,
                    CarviaFrete.numeros_nfs.like(f"{nf.numero_nf},%"),
                    CarviaFrete.numeros_nfs.like(f"%,{nf.numero_nf},%"),
                    CarviaFrete.numeros_nfs.like(f"%,{nf.numero_nf}"),
                ),
            ).all()
            for fr in fretes_para_atualizar:
                if fr.cnpj_destino == nf.cnpj_destinatario:
                    continue
                cnpj_old = fr.cnpj_destino
                fr.cnpj_destino = nf.cnpj_destinatario
                if nf.nome_destinatario:
                    fr.nome_destino = nf.nome_destinatario
                if nf.uf_destinatario:
                    fr.uf_destino = nf.uf_destinatario
                if nf.cidade_destinatario:
                    fr.cidade_destino = nf.cidade_destinatario
                resumo['fretes_atualizados'].append({
                    'frete_id': fr.id,
                    'cnpj_anterior': cnpj_old,
                    'cnpj_novo': nf.cnpj_destinatario,
                })

            # 7. Limpar flag da NF
            nf.divergencia_cnpj_cotacao = False

            db.session.commit()
            logger.info(
                "B4: aplicar_cnpj_na_cotacao concluido por %s: %s",
                current_user.email, resumo,
            )
            return jsonify({'sucesso': True, **resumo})
        except Exception as e:
            db.session.rollback()
            logger.error(
                "B4: erro em aplicar_cnpj_na_cotacao NF=%s: %s",
                nf_id, e, exc_info=True,
            )
            return jsonify({'erro': str(e)}), 500

    @bp.route('/nfs/<int:nf_id>/descartar-divergencia-cnpj', methods=['POST'])
    @login_required
    def descartar_divergencia_cnpj(nf_id):
        """Dispensa o alerta de divergencia CNPJ na NF (mantem cotacao).

        Fase B4b. Usado quando o operador opta por NAO atualizar a cotacao —
        EmbarqueItem ja foi atualizado pela Fase B2/B5, e a cotacao seguira
        com cnpj_destino divergente da NF. Limpa apenas a flag.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        nf = db.session.get(CarviaNf, nf_id)
        if not nf:
            return jsonify({'erro': 'NF nao encontrada.'}), 404

        nf.divergencia_cnpj_cotacao = False
        try:
            db.session.commit()
            logger.info(
                "B4b: divergencia CNPJ descartada para NF %s (numero=%s) por %s",
                nf.id, nf.numero_nf, current_user.email,
            )
            return jsonify({'sucesso': True, 'nf_id': nf.id})
        except Exception as e:
            db.session.rollback()
            logger.error("B4b: erro ao descartar divergencia NF %s: %s", nf_id, e)
            return jsonify({'erro': str(e)}), 500
