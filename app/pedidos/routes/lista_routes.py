"""Routes de listagem de pedidos."""
from flask import render_template, request
from flask_login import login_required
from sqlalchemy import distinct

from app import db
from app.pedidos.models import Pedido
from app.pedidos.forms import FiltroPedidosForm, CotarFreteForm
from app.cadastros_agendamento.models import ContatoAgendamento
from app.embarques.models import Embarque, EmbarqueItem
from datetime import datetime
from app.utils.timezone import agora_utc_naive


def register_lista_routes(bp):

    @bp.route('/lista_pedidos', methods=['GET','POST']) # type: ignore
    @login_required
    def lista_pedidos(): # type: ignore
        from app.pedidos.services.counter_service import PedidosCounterService
        from app.pedidos.services.lista_service import ListaPedidosService as Svc

        # --- Forms ---
        filtro_form = FiltroPedidosForm()
        rotas = db.session.query(distinct(Pedido.rota)).filter(Pedido.rota.isnot(None)).order_by(Pedido.rota).all()
        sub_rotas = db.session.query(distinct(Pedido.sub_rota)).filter(Pedido.sub_rota.isnot(None)).order_by(Pedido.sub_rota).all()
        filtro_form.rota.choices = [('', 'Todas')] + [(r[0], r[0]) for r in rotas if r[0]]
        filtro_form.sub_rota.choices = [('', 'Todas')] + [(sr[0], sr[0]) for sr in sub_rotas if sr[0]]
        cotar_form = CotarFreteForm()

        # --- Parametros ---
        filtro_status = request.args.get('status')
        filtro_data = request.args.get('data')
        sort_by = request.args.get('sort_by', 'expedicao')
        sort_order = request.args.get('sort_order', 'asc')

        # --- Contadores (Redis cache) ---
        hoje = agora_utc_naive().date()
        dados_contadores = PedidosCounterService.obter_contadores()
        contadores_data = dados_contadores['contadores_data']
        contadores_status = dados_contadores['contadores_status']

        for key, dados in contadores_data.items():
            if isinstance(dados['data'], str):
                dados['data'] = datetime.strptime(dados['data'], '%Y-%m-%d').date()

        # --- Contatos de agendamento (reusados no enriquecimento) ---
        contatos_agendamento_todos = ContatoAgendamento.query.filter(
            ContatoAgendamento.forma.isnot(None),
            ContatoAgendamento.forma != '',
            ContatoAgendamento.forma != 'SEM AGENDAMENTO'
        ).all()
        contatos_por_cnpj_global = {c.cnpj: c for c in contatos_agendamento_todos if c.cnpj}

        # --- Query base ---
        query = Pedido.query

        # 1. Filtros de status (botoes rapidos)
        query, _ = Svc.aplicar_filtros_status(
            query, filtro_status, filtro_data, hoje,
            cnpjs_validos_agendamento=dados_contadores['cnpjs_agendamento'],
            lotes_falta_item_ids=dados_contadores['lotes_falta_item'],
            lotes_falta_pagamento_ids=dados_contadores['lotes_falta_pgto']
        )

        # 2. Filtros de formulario
        aplicar_form = filtro_form.validate_on_submit() or (request.method == 'GET' and any([
            request.args.get('numero_pedido'), request.args.get('cnpj_cpf'),
            request.args.get('cliente'), request.args.get('status_form'),
            request.args.get('uf'), request.args.get('rota'), request.args.get('sub_rota')
        ]))
        if aplicar_form:
            query = Svc.aplicar_filtros_formulario(query, filtro_form)

        # 3. Ordenacao
        query = Svc.aplicar_ordenacao(query, sort_by, sort_order)

        # 4. Paginacao
        page = request.args.get('page', 1, type=int)
        paginacao = query.paginate(page=page, per_page=50, error_out=False)
        pedidos = paginacao.items

        # 5. Enriquecimento (embarques, contatos, flags)
        Svc.enriquecer_pedidos(pedidos, contatos_por_cnpj_global)

        # 6. URL helpers (closures simplificadas — sem POST branch)
        def sort_url(campo):
            return Svc.gerar_sort_url(request.args, campo)

        def filtro_url(**kwargs):
            return Svc.gerar_filtro_url(request.args, **kwargs)

        return render_template(
            'pedidos/lista_pedidos.html',
            filtro_form=filtro_form,
            cotar_form=cotar_form,
            pedidos=pedidos,
            paginacao=paginacao,
            contadores_data=contadores_data,
            contadores_status=contadores_status,
            filtro_status_ativo=filtro_status,
            filtro_data_ativo=filtro_data,
            sort_by=sort_by,
            sort_order=sort_order,
            sort_url=sort_url,
            filtro_url=filtro_url
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
