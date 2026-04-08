"""Routes de listagem de pedidos (Fase 1 — GET-only, sem WTForms)."""
from math import ceil

from flask import render_template, request
from flask_login import login_required
from sqlalchemy import func

from app import db
from app.pedidos.models import Pedido
from app.pedidos.forms import CotarFreteForm
from app.cadastros_agendamento.models import ContatoAgendamento
from app.embarques.models import Embarque, EmbarqueItem
from datetime import datetime
from app.utils.timezone import agora_utc_naive
from app.utils.ufs import UF_LIST


def register_lista_routes(bp):

    @bp.route('/lista_pedidos', methods=['GET']) # type: ignore
    @login_required
    def lista_pedidos(): # type: ignore
        from app.pedidos.services.counter_service import PedidosCounterService
        from app.pedidos.services.lista_service import ListaPedidosService as Svc

        # --- Choices data (cache Redis 5min) ---
        rotas_choices, sub_rotas_choices = PedidosCounterService.obter_rotas_choices()

        # CotarFreteForm ainda necessario para CSRF do form de cotacao
        cotar_form = CotarFreteForm()

        # --- Parametros de ordenacao ---
        sort_by = request.args.get('sort_by', 'expedicao')
        sort_order = request.args.get('sort_order', 'asc')

        # --- Dados auxiliares (Redis cache) ---
        hoje = agora_utc_naive().date()
        dados_contadores = PedidosCounterService.obter_contadores()

        # --- Contadores facetados (atualizam com filtros ativos) ---
        _filter_keys = [
            'status', 'cond_atrasados', 'cond_sem_data', 'cond_pend_embarque',
            'cond_agend_pendente', 'cond_ag_pagamento', 'cond_ag_item',
            'expedicao_de', 'expedicao_ate', 'uf', 'rota', 'sub_rota',
            'numero_pedido', 'cnpj_cpf', 'cliente', 'data',
        ]
        has_filters = any(request.args.get(k) for k in _filter_keys)

        if has_filters:
            # Contadores facetados (cache Redis 30s por fingerprint de filtros)
            contadores_calc = PedidosCounterService.obter_contadores_filtrados(
                request.args, hoje,
                cnpjs_agendamento=dados_contadores['cnpjs_agendamento'],
                lotes_item=dados_contadores['lotes_falta_item'],
                lotes_pgto=dados_contadores['lotes_falta_pgto']
            )
            contadores_data = contadores_calc['contadores_data']
            contadores_status = contadores_calc['contadores_status']
        else:
            # Sem filtros: usar contadores globais cacheados
            contadores_data = dados_contadores['contadores_data']
            contadores_status = dados_contadores['contadores_status']

        # Normalizar datas (Redis retorna strings)
        for _key, dados in contadores_data.items():
            if isinstance(dados['data'], str):
                dados['data'] = datetime.strptime(dados['data'], '%Y-%m-%d').date()

        # --- Query base + filtros compostos unificados ---
        query = Pedido.query
        query = Svc.aplicar_filtros_compostos(
            query, request.args, hoje,
            cnpjs_validos_agendamento=dados_contadores['cnpjs_agendamento'],
            lotes_falta_item_ids=dados_contadores['lotes_falta_item'],
            lotes_falta_pagamento_ids=dados_contadores['lotes_falta_pgto']
        )

        # --- Ordenacao ---
        query = Svc.aplicar_ordenacao(query, sort_by, sort_order)

        # --- Paginacao (count otimizado — Fixes PYTHON-FLASK-CH) ---
        page = request.args.get('page', 1, type=int)
        per_page = 50

        # Count otimizado: SELECT count(pedidos.id) FROM pedidos WHERE ...
        # Evita subquery com todas as colunas que paginate() gera
        total = query.with_entities(func.count(Pedido.id)).scalar()
        pedidos = query.limit(per_page).offset((page - 1) * per_page).all()

        # Objeto paginacao compativel com template
        total_pages = max(1, ceil(total / per_page))
        paginacao = type('Pag', (), {
            'page': page, 'per_page': per_page, 'total': total,
            'pages': total_pages, 'items': pedidos,
            'has_prev': page > 1, 'has_next': page < total_pages,
            'prev_num': page - 1 if page > 1 else None,
            'next_num': page + 1 if page < total_pages else None,
        })()

        # --- Contatos de agendamento (apenas CNPJs da pagina atual) ---
        cnpjs_pagina = list({p.cnpj_cpf for p in pedidos if p.cnpj_cpf})
        contatos_por_cnpj = {}
        if cnpjs_pagina:
            contatos = ContatoAgendamento.query.filter(
                ContatoAgendamento.cnpj.in_(cnpjs_pagina),
                ContatoAgendamento.forma.isnot(None),
                ContatoAgendamento.forma != '',
                ContatoAgendamento.forma != 'SEM AGENDAMENTO'
            ).all()
            contatos_por_cnpj = {c.cnpj: c for c in contatos if c.cnpj}

        # --- Enriquecimento (embarques, contatos, flags) ---
        Svc.enriquecer_pedidos(pedidos, contatos_por_cnpj)

        # --- URL helper para sort (usado pelo template) ---
        def sort_url(campo):
            return Svc.gerar_sort_url(request.args, campo)

        return render_template(
            'pedidos/lista_pedidos.html',
            cotar_form=cotar_form,
            pedidos=pedidos,
            paginacao=paginacao,
            contadores_data=contadores_data,
            contadores_status=contadores_status,
            filtro_args=request.args.to_dict(),
            rotas_choices=rotas_choices,
            sub_rotas_choices=sub_rotas_choices,
            uf_list=UF_LIST,
            sort_by=sort_by,
            sort_order=sort_order,
            sort_url=sort_url
        )

    @bp.route('/detalhes/<string:lote_id>') # type: ignore
    @login_required
    def detalhes_pedido(lote_id): # type: ignore
        """
        Visualiza detalhes completos de um pedido usando separacao_lote_id
        """
        pedido = Pedido.query.filter_by(separacao_lote_id=lote_id).first_or_404()

        # Buscar embarque relacionado se existir
        embarque = None
        if pedido.separacao_lote_id:
            item_embarque = (
                db.session.query(EmbarqueItem, Embarque)
                .join(Embarque, EmbarqueItem.embarque_id == Embarque.id)
                .filter(
                    EmbarqueItem.separacao_lote_id == pedido.separacao_lote_id,
                    EmbarqueItem.status == 'ativo',
                    Embarque.status == 'ativo'
                )
                .order_by(Embarque.numero.desc())
                .first()
            )

            if item_embarque:
                embarque = item_embarque[1]

        # Buscar contato de agendamento
        contato_agendamento = None
        if pedido.cnpj_cpf:
            contato_agendamento = ContatoAgendamento.query.filter_by(cnpj=pedido.cnpj_cpf).first()

        return render_template(
            'pedidos/detalhes_pedido.html',
            pedido=pedido,
            embarque=embarque,
            contato_agendamento=contato_agendamento
        )
