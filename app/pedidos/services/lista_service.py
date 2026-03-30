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

        return {
            'status_list': status_list,
            'active_conds': active_conds,
            'dates': {'expedicao_de': expedicao_de, 'expedicao_ate': expedicao_ate},
            'refinements': refinements,
        }

    # ---------------------------------------------------------------
    # APPLY HELPERS — composiveis para query e contadores
    # ---------------------------------------------------------------
    @staticmethod
    def _apply_statuses(query, status_list):
        """Aplica filtro de status (OR) na query."""
        if not status_list:
            return query
        Svc = ListaPedidosService
        filters = [f for f in (Svc._get_status_filter(s) for s in status_list) if f is not None]
        if filters:
            query = query.filter(db.or_(*filters))
        return query

    @staticmethod
    def _apply_conditions(query, active_conds, hoje,
                          cnpjs_agendamento=None,
                          lotes_item=None, lotes_pgto=None):
        """Aplica filtros de condicao (AND) na query."""
        Svc = ListaPedidosService
        if active_conds.get('cond_atrasados'):
            query = query.filter(Svc._filtro_cond_atrasados(hoje))
        if active_conds.get('cond_sem_data'):
            query = query.filter(Svc._filtro_cond_sem_data())
        if active_conds.get('cond_pend_embarque'):
            query = query.filter(Pedido.data_embarque.is_(None))
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
        """Filtro unificado: status (OR), condicoes (AND), datas (range), refinamento."""
        Svc = ListaPedidosService
        p = Svc._parse_filter_params(args)
        query = Svc._apply_statuses(query, p['status_list'])
        query = Svc._apply_conditions(query, p['active_conds'], hoje,
                                      cnpjs_validos_agendamento,
                                      lotes_falta_item_ids,
                                      lotes_falta_pagamento_ids)
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

        # --- STATUS COUNTS: base = refinements + dates + conditions ---
        q_s = Pedido.query
        q_s = Svc._apply_refinements(q_s, p['refinements'])
        q_s = Svc._apply_date_range(q_s, p['dates'])
        q_s = Svc._apply_conditions(q_s, p['active_conds'], hoje,
                                    cnpjs_agendamento, lotes_item, lotes_pgto)

        sr = q_s.with_entities(
            func.count(),
            func.count(case((Pedido.status == 'ABERTO', 1))),
            func.count(case((db.and_(
                Pedido.cotacao_id.isnot(None), Pedido.data_embarque.is_(None),
                (Pedido.nf.is_(None)) | (Pedido.nf == ""), Pedido.nf_cd == False
            ), 1))),
            func.count(case((db.and_(
                (Pedido.nf.isnot(None)) & (Pedido.nf != ""), Pedido.nf_cd == False
            ), 1))),
            func.count(case((Pedido.nf_cd == True, 1))),
        ).one()

        # --- CONDITION COUNTS: base = refinements + dates + statuses ---
        q_c = Pedido.query
        q_c = Svc._apply_refinements(q_c, p['refinements'])
        q_c = Svc._apply_date_range(q_c, p['dates'])
        q_c = Svc._apply_statuses(q_c, p['status_list'])

        cr = q_c.with_entities(
            func.count(case((Svc._filtro_cond_atrasados(hoje), 1))),
            func.count(case((Svc._filtro_cond_sem_data(), 1))),
            func.count(case((Pedido.data_embarque.is_(None), 1))),
            func.count(case((Svc._expr_cond_agend_pendente(cnpjs_agendamento), 1))),
            func.count(case((Svc._expr_cond_lotes(lotes_pgto), 1))),
            func.count(case((Svc._expr_cond_lotes(lotes_item), 1))),
        ).one()

        # --- DATE COUNTS: base = refinements + statuses + conditions (sem datas) ---
        q_d = Pedido.query
        q_d = Svc._apply_refinements(q_d, p['refinements'])
        q_d = Svc._apply_statuses(q_d, p['status_list'])
        q_d = Svc._apply_conditions(q_d, p['active_conds'], hoje,
                                    cnpjs_agendamento, lotes_item, lotes_pgto)

        datas = [hoje + timedelta(days=i) for i in range(4)]
        date_cases = [func.count(case((func.date(Pedido.expedicao) == d, 1))) for d in datas]
        dr = q_d.with_entities(*date_cases).one()

        contadores_data = {}
        for i in range(4):
            contadores_data[f'd{i}'] = {
                'data': datas[i].isoformat(),
                'total': dr[i] or 0,
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
    def _get_status_filter(status_key):
        """Retorna clausula WHERE para um status individual."""
        if status_key == 'aberto':
            return Pedido.status == 'ABERTO'
        elif status_key == 'cotado':
            return db.and_(
                Pedido.cotacao_id.isnot(None),
                Pedido.data_embarque.is_(None),
                (Pedido.nf.is_(None)) | (Pedido.nf == ""),
                Pedido.nf_cd == False
            )
        elif status_key == 'faturado':
            return db.and_(
                (Pedido.nf.isnot(None)) & (Pedido.nf != ""),
                Pedido.nf_cd == False
            )
        elif status_key == 'nf_cd':
            return Pedido.nf_cd == True
        return None

    @staticmethod
    def _filtro_cond_atrasados(hoje):
        """Expression: pedidos atrasados (sem NF, expedicao < hoje)."""
        return db.and_(
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

    @staticmethod
    def _filtro_cond_sem_data():
        """Expression: pedidos sem data de expedicao."""
        return db.and_(
            Pedido.expedicao.is_(None),
            Pedido.nf_cd == False,
            (Pedido.nf.is_(None)) | (Pedido.nf == ""),
            Pedido.data_embarque.is_(None)
        )

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

        # --- CarVia: fallback para lotes sem EmbarqueItem ---
        for pedido in pedidos:
            if getattr(pedido, 'eh_carvia', False) and pedido.separacao_lote_id not in embarques_por_lote:
                lote = pedido.separacao_lote_id or ''
                cot_id = None
                try:
                    if lote.startswith('CARVIA-PED-'):
                        ped_id = int(lote.replace('CARVIA-PED-', ''))
                        from app.carvia.models import CarviaPedido as _CP
                        _p = db.session.get(_CP, ped_id)
                        cot_id = _p.cotacao_id if _p else None
                    elif lote.startswith('CARVIA-'):
                        cot_id = int(lote.replace('CARVIA-', ''))
                except (ValueError, TypeError):
                    pass
                if cot_id:
                    em_item = EmbarqueItem.query.filter(
                        EmbarqueItem.carvia_cotacao_id == cot_id,
                        EmbarqueItem.status == 'ativo',
                    ).first()
                    if em_item:
                        emb = db.session.get(Embarque, em_item.embarque_id)
                        if emb and emb.status == 'ativo':
                            embarques_por_lote[pedido.separacao_lote_id] = emb

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

        # --- CarVia: enriquecer obs_separacao de carvia_cotacoes ---
        carvia_lotes = [lid for lid in lotes_ids if str(lid).startswith('CARVIA-')]
        if carvia_lotes:
            from app.carvia.models import CarviaCotacao, CarviaPedido

            # Batch: buscar observações das cotações CarVia
            for lid in carvia_lotes:
                try:
                    if str(lid).startswith('CARVIA-PED-'):
                        ped_id = int(str(lid).replace('CARVIA-PED-', ''))
                        pedido_cv = db.session.get(CarviaPedido, ped_id)
                        obs = pedido_cv.cotacao.observacoes if pedido_cv and pedido_cv.cotacao else None
                    else:
                        cot_id = int(str(lid).replace('CARVIA-', ''))
                        cot = db.session.get(CarviaCotacao, cot_id)
                        obs = cot.observacoes if cot else None

                    info_separacao_por_lote[lid] = {
                        'tem_falta_item': False,
                        'tem_falta_pagamento': False,
                        'num_pedido': None,
                        'obs_separacao': obs,
                        'separacao_impressa': False,
                        'eh_antecipado': False
                    }
                except Exception:
                    pass

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
