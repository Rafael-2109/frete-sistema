"""
ListaPedidosService — Logica de filtros, ordenacao e enriquecimento
para a rota lista_pedidos.

Extraido de routes.py lista_pedidos() (531 linhas → metodos composiveis).
Fase 1: filtros compostos + contadores facetados.
"""
from datetime import datetime, timedelta
from urllib.parse import urlencode

from flask import url_for
from sqlalchemy import func, case
from sqlalchemy.orm import load_only

from app import db
from app.pedidos.models import Pedido


class ListaPedidosService:
    """Service com metodos estaticos para cada etapa da lista_pedidos."""

    # ---------------------------------------------------------------
    # CONSTANTES
    # ---------------------------------------------------------------
    _COMPAT_STATUS = {
        'abertos': 'aberto',
        'cotados': 'cotado',
    }
    _COMPAT_CONDITION = {
        'atrasados': 'cond_atrasados',
        'sem_data': 'cond_sem_data',
        'pend_embarque': 'cond_pend_embarque',
        'agend_pendente': 'cond_agend_pendente',
        'ag_pagamento': 'cond_ag_pagamento',
        'ag_item': 'cond_ag_item',
    }
    _VALID_STATUSES = {'aberto', 'cotado', 'faturado', 'nf_cd'}
    _COND_KEYS = [
        'cond_atrasados', 'cond_sem_data', 'cond_pend_embarque',
        'cond_agend_pendente', 'cond_ag_pagamento', 'cond_ag_item',
    ]

    # ---------------------------------------------------------------
    # PARSE — extrai params normalizados de request.args
    # ---------------------------------------------------------------
    @staticmethod
    def _parse_filter_params(args):
        """
        Parse e normaliza todos os filter params de request.args.
        Retorna dict com: status_list, active_conds, dates, refinements.
        Trata backward compat de URLs antigas.
        """
        Svc = ListaPedidosService

        status_raw = args.get('status', '')
        cond_overrides = {}

        # Backward compat: status antigo → condicao
        if status_raw in Svc._COMPAT_CONDITION:
            cond_overrides[Svc._COMPAT_CONDITION[status_raw]] = '1'
            status_raw = ''

        if status_raw == 'atrasados_abertos':
            status_raw = 'aberto'
            cond_overrides['cond_atrasados'] = '1'

        if status_raw in Svc._COMPAT_STATUS:
            status_raw = Svc._COMPAT_STATUS[status_raw]

        # Status list
        status_list = [s.strip() for s in status_raw.split(',') if s.strip()]
        status_list = [s for s in status_list if s in Svc._VALID_STATUSES]

        # Active conditions (merged com compat overrides)
        active_conds = {}
        for key in Svc._COND_KEYS:
            active_conds[key] = bool(cond_overrides.get(key) or args.get(key))

        # Dates (com backward compat ?data=)
        data_compat = args.get('data', '')
        expedicao_de = args.get('expedicao_de', '')
        expedicao_ate = args.get('expedicao_ate', '')
        if data_compat and not expedicao_de:
            expedicao_de = data_compat
            expedicao_ate = data_compat

        # Refinements
        refinements = {
            'numero_pedido': args.get('numero_pedido', '').strip(),
            'cnpj_cpf': args.get('cnpj_cpf', '').strip(),
            'cliente': args.get('cliente', '').strip(),
            'uf': args.get('uf', '').strip(),
            'rota': args.get('rota', '').strip(),
            'sub_rota': args.get('sub_rota', '').strip(),
        }

        # Escopo: NACOM / CARVIA / GERAL (vazio)
        origem = (args.get('origem', '') or '').strip().upper()
        if origem not in ('NACOM', 'CARVIA'):
            origem = ''

        return {
            'status_list': status_list,
            'active_conds': active_conds,
            'dates': {'expedicao_de': expedicao_de, 'expedicao_ate': expedicao_ate},
            'refinements': refinements,
            'origem': origem,
        }

    # ---------------------------------------------------------------
    # APPLY HELPERS — composiveis para query e contadores
    # ---------------------------------------------------------------
    @staticmethod
    def _apply_origem(query, origem):
        """Aplica filtro de escopo NACOM/CARVIA via prefixo separacao_lote_id."""
        if origem == 'CARVIA':
            query = query.filter(Pedido.separacao_lote_id.like('CARVIA-%'))
        elif origem == 'NACOM':
            query = query.filter(
                db.or_(
                    Pedido.separacao_lote_id.is_(None),
                    ~Pedido.separacao_lote_id.like('CARVIA-%')
                )
            )
        return query

    @staticmethod
    def _apply_statuses(query, status_list, carvia_sets=None):
        """Aplica filtro de status (OR) na query.

        `carvia_sets` e opcional — pass-through para `_get_status_filter`
        evitar recomputar sets CarVia em chamadas multiplas.
        """
        if not status_list:
            return query
        Svc = ListaPedidosService
        filters = [
            f for f in (Svc._get_status_filter(s, carvia_sets) for s in status_list)
            if f is not None
        ]
        if filters:
            query = query.filter(db.or_(*filters))
        return query

    @staticmethod
    def _apply_conditions(query, active_conds, hoje,
                          cnpjs_agendamento=None,
                          lotes_item=None, lotes_pgto=None,
                          carvia_sets=None):
        """Aplica filtros de condicao (AND) na query."""
        Svc = ListaPedidosService
        if active_conds.get('cond_atrasados'):
            query = query.filter(Svc._filtro_cond_atrasados(hoje, carvia_sets))
        if active_conds.get('cond_sem_data'):
            query = query.filter(Svc._filtro_cond_sem_data(carvia_sets))
        if active_conds.get('cond_pend_embarque'):
            query = query.filter(Svc._filtro_cond_pend_embarque(carvia_sets))
        if active_conds.get('cond_agend_pendente'):
            query = Svc._apply_cond_agend_pendente(query, cnpjs_agendamento)
        if active_conds.get('cond_ag_pagamento'):
            query = Svc._apply_cond_lotes(query, lotes_pgto)
        if active_conds.get('cond_ag_item'):
            query = Svc._apply_cond_lotes(query, lotes_item)
        return query

    @staticmethod
    def _apply_date_range(query, date_params):
        """Aplica filtro de range de datas na query."""
        de = date_params.get('expedicao_de', '')
        ate = date_params.get('expedicao_ate', '')
        if de:
            try:
                query = query.filter(Pedido.expedicao >= datetime.strptime(de, '%Y-%m-%d').date())
            except ValueError:
                pass
        if ate:
            try:
                query = query.filter(Pedido.expedicao <= datetime.strptime(ate, '%Y-%m-%d').date())
            except ValueError:
                pass
        return query

    @staticmethod
    def _apply_refinements(query, refinements):
        """Aplica filtros de refinamento (texto, selects) na query."""
        if refinements.get('numero_pedido'):
            query = query.filter(Pedido.num_pedido.ilike(f"%{refinements['numero_pedido']}%"))
        if refinements.get('cnpj_cpf'):
            query = query.filter(Pedido.cnpj_cpf.ilike(f"%{refinements['cnpj_cpf']}%"))
        if refinements.get('cliente'):
            query = query.filter(Pedido.raz_social_red.ilike(f"%{refinements['cliente']}%"))

        uf = refinements.get('uf', '')
        if uf:
            if uf == 'FOB':
                query = query.filter(Pedido.rota == 'FOB')
            elif uf == 'SP':
                query = query.filter(
                    (Pedido.cod_uf == 'SP') | (Pedido.rota == 'RED')
                ).filter(Pedido.rota != 'FOB')
            else:
                query = query.filter(Pedido.cod_uf == uf, Pedido.rota != 'RED', Pedido.rota != 'FOB')

        if refinements.get('rota'):
            query = query.filter(Pedido.rota == refinements['rota'])
        if refinements.get('sub_rota'):
            query = query.filter(Pedido.sub_rota == refinements['sub_rota'])
        return query

    # ---------------------------------------------------------------
    # FILTRO PRINCIPAL — composicao dos helpers
    # ---------------------------------------------------------------
    @staticmethod
    def aplicar_filtros_compostos(query, args, hoje,
                                  cnpjs_validos_agendamento=None,
                                  lotes_falta_item_ids=None,
                                  lotes_falta_pagamento_ids=None):
        """Filtro unificado: origem (escopo), status (OR), condicoes (AND), datas (range), refinamento."""
        Svc = ListaPedidosService
        p = Svc._parse_filter_params(args)
        carvia_sets = Svc._carvia_lotes_por_status()
        query = Svc._apply_origem(query, p['origem'])
        query = Svc._apply_statuses(query, p['status_list'], carvia_sets)
        query = Svc._apply_conditions(query, p['active_conds'], hoje,
                                      cnpjs_validos_agendamento,
                                      lotes_falta_item_ids,
                                      lotes_falta_pagamento_ids,
                                      carvia_sets=carvia_sets)
        query = Svc._apply_date_range(query, p['dates'])
        query = Svc._apply_refinements(query, p['refinements'])
        return query

    # ---------------------------------------------------------------
    # CONTADORES FACETADOS
    # ---------------------------------------------------------------
    @staticmethod
    def calcular_contadores_filtrados(args, hoje,
                                      cnpjs_agendamento=None,
                                      lotes_item=None,
                                      lotes_pgto=None):
        """
        Contadores contextuais (faceted search).

        - Status counts: base = refinements + dates + conditions (sem status)
        - Condition counts: base = refinements + dates + statuses (sem conditions)
        - Date counts: base = refinements + statuses + conditions (sem datas)

        Retorna dict com contadores_status e contadores_data no mesmo formato
        que PedidosCounterService.obter_contadores().
        """
        Svc = ListaPedidosService
        p = Svc._parse_filter_params(args)
        carvia_sets = Svc._carvia_lotes_por_status()

        # --- STATUS COUNTS: base = origem + refinements + dates + conditions ---
        q_s = Pedido.query
        q_s = Svc._apply_origem(q_s, p['origem'])
        q_s = Svc._apply_refinements(q_s, p['refinements'])
        q_s = Svc._apply_date_range(q_s, p['dates'])
        q_s = Svc._apply_conditions(q_s, p['active_conds'], hoje,
                                    cnpjs_agendamento, lotes_item, lotes_pgto,
                                    carvia_sets=carvia_sets)

        # Contadores usam _get_status_filter (cobre NACOM + CarVia)
        f_aberto = Svc._get_status_filter('aberto', carvia_sets)
        f_cotado = Svc._get_status_filter('cotado', carvia_sets)
        f_faturado = Svc._get_status_filter('faturado', carvia_sets)
        f_nf_cd = Svc._get_status_filter('nf_cd', carvia_sets)

        sr = q_s.with_entities(
            func.count(),
            func.count(case((f_aberto, 1))),
            func.count(case((f_cotado, 1))),
            func.count(case((f_faturado, 1))),
            func.count(case((f_nf_cd, 1))),
        ).one()

        # --- CONDITION COUNTS: base = origem + refinements + dates + statuses ---
        q_c = Pedido.query
        q_c = Svc._apply_origem(q_c, p['origem'])
        q_c = Svc._apply_refinements(q_c, p['refinements'])
        q_c = Svc._apply_date_range(q_c, p['dates'])
        q_c = Svc._apply_statuses(q_c, p['status_list'], carvia_sets)

        cr = q_c.with_entities(
            func.count(case((Svc._filtro_cond_atrasados(hoje, carvia_sets), 1))),
            func.count(case((Svc._filtro_cond_sem_data(carvia_sets), 1))),
            func.count(case((Svc._filtro_cond_pend_embarque(carvia_sets), 1))),
            func.count(case((Svc._expr_cond_agend_pendente(cnpjs_agendamento), 1))),
            func.count(case((Svc._expr_cond_lotes(lotes_pgto), 1))),
            func.count(case((Svc._expr_cond_lotes(lotes_item), 1))),
        ).one()

        # --- DATE COUNTS: base = origem + refinements + statuses + conditions (sem datas) ---
        q_d = Pedido.query
        q_d = Svc._apply_origem(q_d, p['origem'])
        q_d = Svc._apply_refinements(q_d, p['refinements'])
        q_d = Svc._apply_statuses(q_d, p['status_list'], carvia_sets)
        q_d = Svc._apply_conditions(q_d, p['active_conds'], hoje,
                                    cnpjs_agendamento, lotes_item, lotes_pgto,
                                    carvia_sets=carvia_sets)

        datas = [hoje + timedelta(days=i) for i in range(4)]
        date_cases = [func.count(case((func.date(Pedido.expedicao) == d, 1))) for d in datas]
        dr = q_d.with_entities(*date_cases).one()

        contadores_data = {}
        for i in range(4):
            contadores_data[f'd{i}'] = {
                'data': datas[i].isoformat(),
                'total': dr[i] or 0,
                'pend_embarque': 0,
                'abertos': 0,
            }

        return {
            'contadores_data': contadores_data,
            'contadores_status': {
                'todos': sr[0] or 0,
                'abertos': sr[1] or 0,
                'cotados': sr[2] or 0,
                'faturados': sr[3] or 0,
                'nf_cd': sr[4] or 0,
                'atrasados': cr[0] or 0,
                'sem_data': cr[1] or 0,
                'pend_embarque': cr[2] or 0,
                'agend_pendente': cr[3] or 0,
                'ag_pagamento': cr[4] or 0,
                'ag_item': cr[5] or 0,
            },
        }

    # ---------------------------------------------------------------
    # EXPRESSIONS — para uso em case() dentro de contadores
    # ---------------------------------------------------------------
    @staticmethod
    def _carvia_lotes_por_status():
        """Classifica separacao_lote_id CarVia em 'cotado' vs 'embarcado'.

        - 'cotado' = separacao_lote_id CarVia cujo pedido/cotacao esta em embarque
          ativo SEM data_embarque preenchida (aguardando saida).
        - 'embarcado' = idem, mas COM data_embarque preenchida.

        Mapeia 2 caminhos:
          (a) CARVIA-PED-{ped_id} via CarviaPedidoItem.numero_nf → CarviaNf.id
              → EmbarqueItem separacao_lote_id='CARVIA-NF-{nf_id}'.
          (b) EmbarqueItem.separacao_lote_id diretamente CARVIA-* (provisorio
              ou legado) com provisorio=True; lote do proprio EmbarqueItem mais
              lotes CARVIA-PED-{id} dos pedidos sem NF da mesma cotacao.

        Returns:
            dict {'cotado': set[str], 'embarcado': set[str]}
        """
        from app.embarques.models import EmbarqueItem, Embarque
        from app.carvia.models import CarviaPedido, CarviaPedidoItem, CarviaNf

        cotado = set()
        embarcado = set()

        # (a) PED via NF expandida
        rows_nf = db.session.query(
            CarviaPedido.id.label('ped_id'),
            Embarque.data_embarque.label('data_embarque'),
        ).join(
            CarviaPedidoItem, CarviaPedidoItem.pedido_id == CarviaPedido.id
        ).join(
            CarviaNf, CarviaNf.numero_nf == CarviaPedidoItem.numero_nf
        ).join(
            EmbarqueItem,
            EmbarqueItem.separacao_lote_id == (
                db.literal('CARVIA-NF-') + db.cast(CarviaNf.id, db.String)
            ),
        ).join(
            Embarque, Embarque.id == EmbarqueItem.embarque_id
        ).filter(
            EmbarqueItem.status == 'ativo',
            Embarque.status == 'ativo',
        ).all()
        for row in rows_nf:
            lote = f'CARVIA-PED-{row.ped_id}'
            (embarcado if row.data_embarque else cotado).add(lote)

        # (b) Provisorio direto
        rows_prov = db.session.query(
            EmbarqueItem.separacao_lote_id.label('lote'),
            EmbarqueItem.carvia_cotacao_id.label('cot_id'),
            Embarque.data_embarque.label('data_embarque'),
        ).join(
            Embarque, Embarque.id == EmbarqueItem.embarque_id
        ).filter(
            EmbarqueItem.status == 'ativo',
            Embarque.status == 'ativo',
            EmbarqueItem.provisorio == True,  # noqa: E712
        ).all()

        # Mapa cotacao_id → [pedidos sem NF] para propagar status aos PEDs irmaos
        peds_sem_nf_por_cot = {}
        if rows_prov:
            cot_ids = {r.cot_id for r in rows_prov if r.cot_id}
            if cot_ids:
                # NOT EXISTS correlacionado: muito mais eficiente que NOT IN
                # com subquery irrestrita (evita full-scan em carvia_pedido_itens)
                has_nf_subq = db.session.query(CarviaPedidoItem).filter(
                    CarviaPedidoItem.pedido_id == CarviaPedido.id,
                    CarviaPedidoItem.numero_nf.isnot(None),
                    CarviaPedidoItem.numero_nf != '',
                ).exists()
                peds_sem_nf = CarviaPedido.query.filter(
                    CarviaPedido.cotacao_id.in_(list(cot_ids)),
                    ~has_nf_subq,
                    CarviaPedido.status != 'CANCELADO',
                ).all()
                for p in peds_sem_nf:
                    peds_sem_nf_por_cot.setdefault(p.cotacao_id, []).append(p.id)

        for row in rows_prov:
            lote = row.lote
            target = embarcado if row.data_embarque else cotado
            target.add(lote)
            if row.cot_id and row.cot_id in peds_sem_nf_por_cot:
                for ped_id in peds_sem_nf_por_cot[row.cot_id]:
                    lote_ped = f'CARVIA-PED-{ped_id}'
                    if lote_ped not in cotado and lote_ped not in embarcado:
                        target.add(lote_ped)

        return {'cotado': cotado, 'embarcado': embarcado}

    @staticmethod
    def _get_status_filter(status_key, carvia_sets=None):
        """Retorna clausula WHERE para um status individual.

        Semantica unificada NACOM + CarVia (definicao baseada em embarque):
          - aberto    = SEM embarque ativo
          - cotado    = EM embarque ativo, sem data_embarque
          - faturado  = APENAS NACOM (nf preenchida e nao no CD)
          - nf_cd     = nf_cd=True (NACOM)

        CarVia EMBARCADO (com data_embarque) nao cai em nenhum dos 3 filtros
        de status: aparece apenas na lista "Todos" e nos filtros de condicao.

        NACOM filtra com `~CARVIA-%` para evitar capturar CarVia por engano
        (CarVia 2B na VIEW pedidos tem `nf` preenchida assim que NF e anexada).
        """
        if carvia_sets is None:
            carvia_sets = ListaPedidosService._carvia_lotes_por_status()
        cotados = list(carvia_sets['cotado']) or ['_NONE_']
        embarcados = list(carvia_sets['embarcado']) or ['_NONE_']
        carvia_prefix = Pedido.separacao_lote_id.like('CARVIA-%')
        nao_carvia = ~carvia_prefix

        if status_key == 'aberto':
            # NACOM: status=ABERTO E nao e CarVia
            nacom = db.and_(nao_carvia, Pedido.status == 'ABERTO')
            # CarVia: lote NAO esta em set cotado nem embarcado
            carvia = db.and_(
                carvia_prefix,
                Pedido.separacao_lote_id.notin_(cotados),
                Pedido.separacao_lote_id.notin_(embarcados),
            )
            return db.or_(nacom, carvia)
        elif status_key == 'cotado':
            # NACOM: tem cotacao_id, sem data_embarque, sem nf, nao e CarVia
            nacom = db.and_(
                nao_carvia,
                Pedido.cotacao_id.isnot(None),
                Pedido.data_embarque.is_(None),
                (Pedido.nf.is_(None)) | (Pedido.nf == ""),
                Pedido.nf_cd == False
            )
            # CarVia: lote em set cotado (embarque sem data_embarque)
            carvia = db.and_(
                carvia_prefix,
                Pedido.separacao_lote_id.in_(cotados),
            )
            return db.or_(nacom, carvia)
        elif status_key == 'faturado':
            # APENAS NACOM (CarVia embarcado nao entra)
            return db.and_(
                nao_carvia,
                (Pedido.nf.isnot(None)) & (Pedido.nf != ""),
                Pedido.nf_cd == False
            )
        elif status_key == 'nf_cd':
            return Pedido.nf_cd == True
        return None

    @staticmethod
    def _filtro_cond_atrasados(hoje, carvia_sets=None):
        """Expression: pedidos atrasados (expedicao < hoje, ainda nao saiu).

        NACOM: sem NF, sem data_embarque, expedicao < hoje
        CarVia: lote NAO em set embarcado, expedicao < hoje
        """
        if carvia_sets is None:
            carvia_sets = ListaPedidosService._carvia_lotes_por_status()
        embarcados = list(carvia_sets['embarcado']) or ['_NONE_']
        carvia_prefix = Pedido.separacao_lote_id.like('CARVIA-%')
        nao_carvia = ~carvia_prefix

        nacom = db.and_(
            nao_carvia,
            db.or_(
                db.and_(Pedido.cotacao_id.isnot(None), Pedido.data_embarque.is_(None),
                        (Pedido.nf.is_(None)) | (Pedido.nf == "")),
                db.and_(Pedido.cotacao_id.is_(None),
                        (Pedido.nf.is_(None)) | (Pedido.nf == ""))
            ),
            Pedido.nf_cd == False,
            Pedido.expedicao < hoje,
            (Pedido.nf.is_(None)) | (Pedido.nf == "")
        )
        carvia = db.and_(
            carvia_prefix,
            Pedido.separacao_lote_id.notin_(embarcados),
            Pedido.expedicao < hoje,
        )
        return db.or_(nacom, carvia)

    @staticmethod
    def _filtro_cond_sem_data(carvia_sets=None):
        """Expression: pedidos sem data de expedicao.

        NACOM: expedicao IS NULL e ainda nao saiu/faturou
        CarVia: expedicao IS NULL e lote NAO em set embarcado
        """
        if carvia_sets is None:
            carvia_sets = ListaPedidosService._carvia_lotes_por_status()
        embarcados = list(carvia_sets['embarcado']) or ['_NONE_']
        carvia_prefix = Pedido.separacao_lote_id.like('CARVIA-%')
        nao_carvia = ~carvia_prefix

        nacom = db.and_(
            nao_carvia,
            Pedido.expedicao.is_(None),
            Pedido.nf_cd == False,
            (Pedido.nf.is_(None)) | (Pedido.nf == ""),
            Pedido.data_embarque.is_(None)
        )
        carvia = db.and_(
            carvia_prefix,
            Pedido.expedicao.is_(None),
            Pedido.separacao_lote_id.notin_(embarcados),
        )
        return db.or_(nacom, carvia)

    @staticmethod
    def _filtro_cond_pend_embarque(carvia_sets=None):
        """Expression: pedidos pendentes de embarque (sem data_embarque).

        NACOM: data_embarque IS NULL (inclui NF no CD)
        CarVia: lote NAO em set embarcado (VIEW expoe data_embarque sempre NULL
        para CarVia, entao usar set para coerencia).
        """
        if carvia_sets is None:
            carvia_sets = ListaPedidosService._carvia_lotes_por_status()
        embarcados = list(carvia_sets['embarcado']) or ['_NONE_']
        carvia_prefix = Pedido.separacao_lote_id.like('CARVIA-%')
        nao_carvia = ~carvia_prefix

        nacom = db.and_(nao_carvia, Pedido.data_embarque.is_(None))
        carvia = db.and_(
            carvia_prefix,
            Pedido.separacao_lote_id.notin_(embarcados),
        )
        return db.or_(nacom, carvia)

    @staticmethod
    def _expr_cond_agend_pendente(cnpjs_agendamento):
        """Expression para agend_pendente (para case())."""
        from app.pedidos.services.counter_service import CNPJS_EXCLUIR_AGENDAMENTO
        if not cnpjs_agendamento:
            return Pedido.separacao_lote_id == 'IMPOSSIVEL'
        cnpj_raiz = func.left(func.regexp_replace(Pedido.cnpj_cpf, '[^0-9]', '', 'g'), 8)
        return db.and_(
            Pedido.cnpj_cpf.in_(cnpjs_agendamento),
            Pedido.agendamento.is_(None),
            Pedido.nf_cd == False,
            (Pedido.nf.is_(None)) | (Pedido.nf == ""),
            Pedido.data_embarque.is_(None),
            (Pedido.cod_uf == 'SP') | (Pedido.rota == 'FOB'),
            ~cnpj_raiz.in_(CNPJS_EXCLUIR_AGENDAMENTO)
        )

    @staticmethod
    def _expr_cond_lotes(lotes_ids):
        """Expression para lotes com falta (para case())."""
        if not lotes_ids:
            return Pedido.separacao_lote_id == 'IMPOSSIVEL'
        return db.and_(
            Pedido.separacao_lote_id.in_(lotes_ids),
            Pedido.nf_cd == False,
            (Pedido.nf.is_(None)) | (Pedido.nf == "")
        )

    @staticmethod
    def _apply_cond_agend_pendente(query, cnpjs_agendamento):
        """Aplica filtro agend_pendente na query."""
        Svc = ListaPedidosService
        return query.filter(Svc._expr_cond_agend_pendente(cnpjs_agendamento))

    @staticmethod
    def _apply_cond_lotes(query, lotes_ids):
        """Aplica filtro de lotes com falta na query."""
        Svc = ListaPedidosService
        return query.filter(Svc._expr_cond_lotes(lotes_ids))

    # ---------------------------------------------------------------
    # DEPRECATED — Fase 0 (manter para rollback seguro)
    # ---------------------------------------------------------------
    @staticmethod
    def aplicar_filtros_status(query, filtro_status, filtro_data, hoje,
                               cnpjs_validos_agendamento=None,
                               lotes_falta_item_ids=None,
                               lotes_falta_pagamento_ids=None):
        """DEPRECATED - Fase 1: usar aplicar_filtros_compostos()."""
        from app.pedidos.services.counter_service import CNPJS_EXCLUIR_AGENDAMENTO

        filtros_aplicados = False

        if filtro_status:
            filtros_aplicados = True

            if filtro_status == 'abertos':
                query = query.filter(
                    db.or_(Pedido.status == 'ABERTO', Pedido.nf_cd == True)
                )
            elif filtro_status == 'cotados':
                query = query.filter(
                    Pedido.cotacao_id.isnot(None),
                    Pedido.data_embarque.is_(None),
                    (Pedido.nf.is_(None)) | (Pedido.nf == ""),
                    Pedido.nf_cd == False
                )
            elif filtro_status == 'nf_cd':
                query = query.filter(Pedido.nf_cd == True)
            elif filtro_status == 'atrasados':
                query = query.filter(
                    db.or_(
                        db.and_(Pedido.cotacao_id.isnot(None), Pedido.data_embarque.is_(None),
                                (Pedido.nf.is_(None)) | (Pedido.nf == "")),
                        db.and_(Pedido.cotacao_id.is_(None),
                                (Pedido.nf.is_(None)) | (Pedido.nf == ""))
                    ),
                    Pedido.nf_cd == False,
                    Pedido.expedicao < hoje,
                    (Pedido.nf.is_(None)) | (Pedido.nf == "")
                )
            elif filtro_status == 'atrasados_abertos':
                query = query.filter(
                    Pedido.cotacao_id.is_(None),
                    (Pedido.nf.is_(None)) | (Pedido.nf == ""),
                    Pedido.nf_cd == False,
                    Pedido.expedicao < hoje
                )
            elif filtro_status == 'agend_pendente':
                if cnpjs_validos_agendamento:
                    cnpj_raiz = func.left(func.regexp_replace(Pedido.cnpj_cpf, '[^0-9]', '', 'g'), 8)
                    query = query.filter(
                        Pedido.cnpj_cpf.in_(cnpjs_validos_agendamento),
                        Pedido.agendamento.is_(None),
                        Pedido.nf_cd == False,
                        (Pedido.nf.is_(None)) | (Pedido.nf == ""),
                        Pedido.data_embarque.is_(None),
                        (Pedido.cod_uf == 'SP') | (Pedido.rota == 'FOB'),
                        ~cnpj_raiz.in_(CNPJS_EXCLUIR_AGENDAMENTO)
                    )
                else:
                    query = query.filter(Pedido.separacao_lote_id == 'IMPOSSIVEL')
            elif filtro_status == 'sem_data':
                query = query.filter(
                    Pedido.expedicao.is_(None),
                    Pedido.nf_cd == False,
                    (Pedido.nf.is_(None)) | (Pedido.nf == ""),
                    Pedido.data_embarque.is_(None)
                )
            elif filtro_status == 'ag_pagamento':
                if lotes_falta_pagamento_ids:
                    query = query.filter(
                        Pedido.separacao_lote_id.in_(lotes_falta_pagamento_ids),
                        Pedido.nf_cd == False,
                        (Pedido.nf.is_(None)) | (Pedido.nf == "")
                    )
                else:
                    query = query.filter(Pedido.separacao_lote_id == 'IMPOSSIVEL')
            elif filtro_status == 'ag_item':
                if lotes_falta_item_ids:
                    query = query.filter(
                        Pedido.separacao_lote_id.in_(lotes_falta_item_ids),
                        Pedido.nf_cd == False,
                        (Pedido.nf.is_(None)) | (Pedido.nf == "")
                    )
                else:
                    query = query.filter(Pedido.separacao_lote_id == 'IMPOSSIVEL')
            elif filtro_status == 'pend_embarque':
                query = query.filter(Pedido.data_embarque.is_(None))

        if filtro_data:
            filtros_aplicados = True
            try:
                data_selecionada = datetime.strptime(filtro_data, '%Y-%m-%d').date()
                query = query.filter(func.date(Pedido.expedicao) == data_selecionada)
            except ValueError:
                pass

        return query, filtros_aplicados

    @staticmethod
    def aplicar_filtros_formulario(query, filtro_form):
        """DEPRECATED - Fase 1: usar aplicar_filtros_compostos()."""
        if filtro_form.numero_pedido.data:
            query = query.filter(
                Pedido.num_pedido.ilike(f"%{filtro_form.numero_pedido.data}%")
            )
        if filtro_form.cnpj_cpf.data:
            query = query.filter(
                Pedido.cnpj_cpf.ilike(f"%{filtro_form.cnpj_cpf.data}%")
            )
        if filtro_form.cliente.data:
            query = query.filter(
                Pedido.raz_social_red.ilike(f"%{filtro_form.cliente.data}%")
            )
        if filtro_form.status.data:
            status_filtro = filtro_form.status.data
            if status_filtro == 'NF no CD':
                query = query.filter(Pedido.nf_cd == True)
            elif status_filtro == 'FATURADO':
                query = query.filter(
                    (Pedido.nf.isnot(None)) & (Pedido.nf != ""),
                    Pedido.nf_cd == False
                )
            elif status_filtro == 'COTADO':
                query = query.filter(
                    Pedido.cotacao_id.isnot(None),
                    Pedido.data_embarque.is_(None),
                    (Pedido.nf.is_(None)) | (Pedido.nf == ""),
                    Pedido.nf_cd == False
                )
            elif status_filtro == 'ABERTO':
                query = query.filter(Pedido.status == 'ABERTO')

        if filtro_form.pendente_cotacao.data:
            query = query.filter(Pedido.cotacao_id.is_(None))
        if filtro_form.somente_sem_nf.data:
            query = query.filter((Pedido.nf.is_(None)) | (Pedido.nf == ""))

        if filtro_form.uf.data:
            if filtro_form.uf.data == 'FOB':
                query = query.filter(Pedido.rota == 'FOB')
            elif filtro_form.uf.data == 'SP':
                query = query.filter(
                    (Pedido.cod_uf == 'SP') | (Pedido.rota == 'RED')
                ).filter(Pedido.rota != 'FOB')
            else:
                query = query.filter(
                    Pedido.cod_uf == filtro_form.uf.data,
                    Pedido.rota != 'RED',
                    Pedido.rota != 'FOB'
                )

        if filtro_form.rota.data:
            query = query.filter(Pedido.rota == filtro_form.rota.data)
        if filtro_form.sub_rota.data:
            query = query.filter(Pedido.sub_rota == filtro_form.sub_rota.data)
        if filtro_form.expedicao_inicio.data:
            query = query.filter(Pedido.expedicao >= filtro_form.expedicao_inicio.data)
        if filtro_form.expedicao_fim.data:
            query = query.filter(Pedido.expedicao <= filtro_form.expedicao_fim.data)

        return query

    # ---------------------------------------------------------------
    # 3. ORDENACAO
    # ---------------------------------------------------------------
    @staticmethod
    def aplicar_ordenacao(query, sort_by, sort_order):
        """Aplica ordenacao dinamica com hierarquia padrao como criterio secundario."""
        campos_ordenacao = {
            'num_pedido': Pedido.num_pedido,
            'cnpj_cpf': Pedido.cnpj_cpf,
            'raz_social_red': Pedido.raz_social_red,
            'nome_cidade': Pedido.nome_cidade,
            'cod_uf': Pedido.cod_uf,
            'valor_saldo_total': Pedido.valor_saldo_total,
            'peso_total': Pedido.peso_total,
            'rota': Pedido.rota,
            'sub_rota': Pedido.sub_rota,
            'expedicao': Pedido.expedicao,
            'agendamento': Pedido.agendamento,
            'protocolo': Pedido.protocolo,
            'nf': Pedido.nf,
            'data_embarque': Pedido.data_embarque
        }

        hierarquia = [
            Pedido.rota.asc().nullslast(),
            Pedido.sub_rota.asc().nullslast(),
            Pedido.cnpj_cpf.asc().nullslast(),
            Pedido.expedicao.asc().nullslast(),
        ]

        if sort_by in campos_ordenacao and sort_by != 'expedicao':
            campo = campos_ordenacao[sort_by]
            primary = campo.desc() if sort_order == 'desc' else campo.asc()
            query = query.order_by(primary, *hierarquia)
        else:
            query = query.order_by(*hierarquia)

        return query

    # ---------------------------------------------------------------
    # 4. ENRIQUECIMENTO DE PEDIDOS
    # ---------------------------------------------------------------
    @staticmethod
    def enriquecer_pedidos(pedidos, contatos_por_cnpj_global):
        """
        Busca embarques, contatos de agendamento, flags de separacao
        e adiciona como atributos em cada pedido.
        """
        from app.embarques.models import Embarque, EmbarqueItem
        from app.separacao.models import Separacao
        from app.carteira.models import CarteiraPrincipal

        lotes_ids = [p.separacao_lote_id for p in pedidos if p.separacao_lote_id]

        # --- Embarques por lote ---
        embarques_por_lote = {}
        if lotes_ids:
            itens_embarque = (
                db.session.query(EmbarqueItem, Embarque)
                .join(Embarque, EmbarqueItem.embarque_id == Embarque.id)
                .filter(
                    EmbarqueItem.separacao_lote_id.in_(lotes_ids),
                    EmbarqueItem.status == 'ativo',
                    Embarque.status == 'ativo'
                )
                .order_by(Embarque.numero.desc())
                .all()
            )
            for item, embarque in itens_embarque:
                if item.separacao_lote_id not in embarques_por_lote:
                    embarques_por_lote[item.separacao_lote_id] = embarque

        # --- CarVia: fallback batch para lotes sem EmbarqueItem direto ---
        # Regra: o badge de embarque respeita o EmbarqueItem REAL do sub-pedido.
        # Se o pedido tem CarviaPedidoItem.numero_nf, procuramos CARVIA-NF-{nf_id}.
        # Se nao acha NF expandida, NAO associa o badge (evita "pedido fantasma"
        # herdando embarque de outro pedido da mesma cotacao).
        # Fallback via carvia_cotacao_id so roda quando ainda ha PROVISORIO ativo
        # (provisorio=True) — caso de pedido sem NF aguardando expansao.
        carvia_sem_embarque = [
            p for p in pedidos
            if getattr(p, 'eh_carvia', False)
            and p.separacao_lote_id not in embarques_por_lote
        ]
        if carvia_sem_embarque:
            from app.carvia.models import (
                CarviaPedido as _CP, CarviaPedidoItem as _CPI, CarviaNf as _CN,
            )

            # 1. Resolver por NF propria (CARVIA-NF-{nf_id})
            # Coleta: ped_ids de CARVIA-PED-* e cot_ids de CARVIA-{cot_id}
            ped_ids_com_lote = []  # [(ped_id, lote_key)]
            lote_to_cot_id = {}    # para fallback por cotacao_id adiante
            for p in carvia_sem_embarque:
                lote = p.separacao_lote_id or ''
                try:
                    if lote.startswith('CARVIA-PED-'):
                        ped_ids_com_lote.append(
                            (int(lote.replace('CARVIA-PED-', '')), lote)
                        )
                    elif lote.startswith('CARVIA-'):
                        cid = int(lote.replace('CARVIA-', ''))
                        lote_to_cot_id[lote] = cid
                except (ValueError, TypeError):
                    pass

            # Batch load CarviaPedido → cotacao_id
            ped_id_to_cot = {}
            if ped_ids_com_lote:
                ids_unicos = list({pid for (pid, _) in ped_ids_com_lote})
                for cp in _CP.query.filter(_CP.id.in_(ids_unicos)).all():
                    if cp.cotacao_id:
                        ped_id_to_cot[cp.id] = cp.cotacao_id

            # Batch load NFs dos pedidos (CarviaPedidoItem.numero_nf)
            nf_nums_por_ped = {}  # ped_id → set[numero_nf]
            if ped_ids_com_lote:
                ids_unicos = list({pid for (pid, _) in ped_ids_com_lote})
                rows = db.session.query(
                    _CPI.pedido_id, _CPI.numero_nf
                ).filter(
                    _CPI.pedido_id.in_(ids_unicos),
                    _CPI.numero_nf.isnot(None),
                    _CPI.numero_nf != '',
                ).distinct().all()
                for pid, nf_num in rows:
                    nf_nums_por_ped.setdefault(pid, set()).add(str(nf_num))

            # Batch load CarviaNf para mapear numero_nf → id
            todos_nf_nums = set()
            for s in nf_nums_por_ped.values():
                todos_nf_nums.update(s)
            nf_num_to_id = {}
            if todos_nf_nums:
                for nf_obj in _CN.query.filter(
                    _CN.numero_nf.in_(list(todos_nf_nums))
                ).all():
                    nf_num_to_id[str(nf_obj.numero_nf)] = nf_obj.id

            # Para cada pedido CARVIA-PED-*, se tem NF: resolver via CARVIA-NF-{nf_id}
            lotes_resolvidos = set()  # lotes que ja sao "decididos" (com ou sem embarque)
            todos_nf_lotes = []
            lote_ped_to_nf_lotes = {}  # lote_ped → [lote_nf, ...]
            for ped_id, lote_ped in ped_ids_com_lote:
                nfs = nf_nums_por_ped.get(ped_id, set())
                if nfs:
                    lote_nfs = [
                        f'CARVIA-NF-{nf_num_to_id[n]}'
                        for n in nfs if n in nf_num_to_id
                    ]
                    lote_ped_to_nf_lotes[lote_ped] = lote_nfs
                    todos_nf_lotes.extend(lote_nfs)
                    # Pedido tem NF → nao cai no fallback de provisorio
                    lotes_resolvidos.add(lote_ped)

            # Batch load EmbarqueItems ativos pelos lotes CARVIA-NF-*
            nf_lote_to_embarque = {}
            if todos_nf_lotes:
                rows = (
                    db.session.query(EmbarqueItem, Embarque)
                    .join(Embarque, EmbarqueItem.embarque_id == Embarque.id)
                    .filter(
                        EmbarqueItem.separacao_lote_id.in_(list(set(todos_nf_lotes))),
                        EmbarqueItem.status == 'ativo',
                        Embarque.status == 'ativo',
                    )
                    .order_by(Embarque.numero.desc())
                    .all()
                )
                for ei, emb in rows:
                    if ei.separacao_lote_id not in nf_lote_to_embarque:
                        nf_lote_to_embarque[ei.separacao_lote_id] = emb

            # Atribuir embarque aos pedidos com NF (se encontrado)
            for lote_ped, lote_nfs in lote_ped_to_nf_lotes.items():
                for lote_nf in lote_nfs:
                    if lote_nf in nf_lote_to_embarque:
                        embarques_por_lote[lote_ped] = nf_lote_to_embarque[lote_nf]
                        break
                # Se nenhum achou: deixa sem badge (decidido via lotes_resolvidos)

            # 2. Fallback por carvia_cotacao_id APENAS para lotes ainda nao decididos
            #    (pedidos sem NF + lotes CARVIA-{cot_id} puros)
            lote_to_cot_id_filtrado = {
                lote: cid for lote, cid in lote_to_cot_id.items()
                if lote not in lotes_resolvidos
            }
            for ped_id, lote_ped in ped_ids_com_lote:
                if lote_ped not in lotes_resolvidos:
                    cot_id = ped_id_to_cot.get(ped_id)
                    if cot_id:
                        lote_to_cot_id_filtrado[lote_ped] = cot_id

            all_cot_ids = list(set(lote_to_cot_id_filtrado.values()))
            if all_cot_ids:
                # CRITICO: filtrar provisorio=True — garante que so associa se
                # a cotacao ainda tem PROVISORIO ativo (nao expandido).
                cv_em_items = EmbarqueItem.query.filter(
                    EmbarqueItem.carvia_cotacao_id.in_(all_cot_ids),
                    EmbarqueItem.provisorio == True,  # noqa: E712
                    EmbarqueItem.status == 'ativo',
                ).all()
                cv_embarque_ids = {
                    ei.embarque_id for ei in cv_em_items if ei.embarque_id
                }
                cv_embarques = {}
                if cv_embarque_ids:
                    for emb in Embarque.query.filter(
                        Embarque.id.in_(list(cv_embarque_ids)),
                        Embarque.status == 'ativo',
                    ).all():
                        cv_embarques[emb.id] = emb

                cot_to_embarque = {}
                for ei in cv_em_items:
                    if ei.carvia_cotacao_id and ei.embarque_id in cv_embarques:
                        cot_to_embarque[ei.carvia_cotacao_id] = (
                            cv_embarques[ei.embarque_id]
                        )

                for lote_key, cot_id in lote_to_cot_id_filtrado.items():
                    emb = cot_to_embarque.get(cot_id)
                    if emb:
                        embarques_por_lote[lote_key] = emb

        # --- Contatos de agendamento ---
        cnpjs_pedidos = [p.cnpj_cpf for p in pedidos if p.cnpj_cpf]
        contatos_por_cnpj = {
            cnpj: contatos_por_cnpj_global[cnpj]
            for cnpj in cnpjs_pedidos
            if cnpj in contatos_por_cnpj_global
        }

        # --- Atribuir embarque + contato ---
        for pedido in pedidos:
            pedido.ultimo_embarque = embarques_por_lote.get(pedido.separacao_lote_id)
            pedido.contato_agendamento = contatos_por_cnpj.get(pedido.cnpj_cpf)

        # --- Info separacao (falta item, pagamento, obs, impressao) ---
        info_separacao_por_lote = {}
        if lotes_ids:
            itens_separacao = Separacao.query.filter(
                Separacao.separacao_lote_id.in_(lotes_ids)
            ).options(load_only(
                Separacao.separacao_lote_id,
                Separacao.num_pedido,
                Separacao.falta_item,
                Separacao.falta_pagamento,
                Separacao.obs_separacao,
                Separacao.separacao_impressa
            )).all()

            for item in itens_separacao:
                lid = item.separacao_lote_id
                if lid not in info_separacao_por_lote:
                    info_separacao_por_lote[lid] = {
                        'tem_falta_item': False,
                        'tem_falta_pagamento': False,
                        'num_pedido': item.num_pedido,
                        'obs_separacao': item.obs_separacao,
                        'separacao_impressa': False
                    }
                if item.falta_item:
                    info_separacao_por_lote[lid]['tem_falta_item'] = True
                if item.falta_pagamento:
                    info_separacao_por_lote[lid]['tem_falta_pagamento'] = True
                if item.separacao_impressa:
                    info_separacao_por_lote[lid]['separacao_impressa'] = True

        # --- CarVia: enriquecer obs_separacao via batch ---
        carvia_lotes = [lid for lid in lotes_ids if str(lid).startswith('CARVIA-')]
        if carvia_lotes:
            from app.carvia.models import CarviaCotacao, CarviaPedido
            from sqlalchemy.orm import joinedload

            # Separar lotes por tipo
            cv_ped_ids = []
            cv_cot_ids = []
            for lid in carvia_lotes:
                try:
                    if str(lid).startswith('CARVIA-PED-'):
                        cv_ped_ids.append(int(str(lid).replace('CARVIA-PED-', '')))
                    else:
                        cv_cot_ids.append(int(str(lid).replace('CARVIA-', '')))
                except (ValueError, TypeError):
                    pass

            # Batch load com joinedload para cotacao
            obs_por_lote = {}
            if cv_ped_ids:
                peds = CarviaPedido.query.filter(
                    CarviaPedido.id.in_(cv_ped_ids)
                ).options(joinedload(CarviaPedido.cotacao)).all()
                for p in peds:
                    obs_por_lote[f'CARVIA-PED-{p.id}'] = (
                        p.cotacao.observacoes if p.cotacao else None
                    )

            if cv_cot_ids:
                cots = CarviaCotacao.query.filter(
                    CarviaCotacao.id.in_(cv_cot_ids)
                ).all()
                for c in cots:
                    obs_por_lote[f'CARVIA-{c.id}'] = c.observacoes

            for lid in carvia_lotes:
                info_separacao_por_lote.setdefault(lid, {
                    'tem_falta_item': False,
                    'tem_falta_pagamento': False,
                    'num_pedido': None,
                    'obs_separacao': obs_por_lote.get(lid),
                    'separacao_impressa': False,
                    'eh_antecipado': False
                })
                # Sempre atualizar obs_separacao do CarVia (fonte primaria)
                info_separacao_por_lote[lid]['obs_separacao'] = obs_por_lote.get(lid)

        # --- Pagamento antecipado via CarteiraPrincipal ---
        num_pedidos = list(set([
            info['num_pedido']
            for info in info_separacao_por_lote.values()
            if info.get('num_pedido')
        ]))
        if num_pedidos:
            itens_carteira = CarteiraPrincipal.query.filter(
                CarteiraPrincipal.num_pedido.in_(num_pedidos)
            ).all()
            cond_pgto_por_pedido = {}
            for item in itens_carteira:
                if item.num_pedido not in cond_pgto_por_pedido:
                    cond_pgto_por_pedido[item.num_pedido] = item.cond_pgto_pedido
            for lid, info in info_separacao_por_lote.items():
                num_ped = info.get('num_pedido')
                if num_ped:
                    cond_pgto = cond_pgto_por_pedido.get(num_ped, '')
                    info['eh_antecipado'] = cond_pgto and 'ANTECIPADO' in cond_pgto.upper()

        # --- Atribuir flags ---
        for pedido in pedidos:
            info = info_separacao_por_lote.get(pedido.separacao_lote_id, {})
            pedido.tem_falta_item = info.get('tem_falta_item', False)
            pedido.tem_falta_pagamento = info.get('tem_falta_pagamento', False)
            pedido.eh_pagamento_antecipado = info.get('eh_antecipado', False)
            pedido.obs_separacao = info.get('obs_separacao')
            pedido.separacao_impressa = info.get('separacao_impressa', False)

    # ---------------------------------------------------------------
    # 5. URL HELPERS
    # ---------------------------------------------------------------
    @staticmethod
    def gerar_sort_url(request_args, campo):
        """Gera URL de ordenacao preservando filtros atuais."""
        params = request_args.to_dict() if hasattr(request_args, 'to_dict') else dict(request_args)

        nova_ordem = 'asc'
        if params.get('sort_by') == campo and params.get('sort_order') == 'asc':
            nova_ordem = 'desc'

        params['sort_by'] = campo
        params['sort_order'] = nova_ordem

        return url_for('pedidos.lista_pedidos') + '?' + urlencode(params)

    @staticmethod
    def gerar_filtro_url(request_args, **kwargs):
        """DEPRECATED - Fase 1: filtro_url nao e mais usado pelo template."""
        params = request_args.to_dict() if hasattr(request_args, 'to_dict') else dict(request_args)

        for chave, valor in kwargs.items():
            if valor is None:
                params.pop(chave, None)
            else:
                params[chave] = valor

        return url_for('pedidos.lista_pedidos') + '?' + urlencode(params)
