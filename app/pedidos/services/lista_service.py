"""
ListaPedidosService — Logica de filtros, ordenacao e enriquecimento
para a rota lista_pedidos.

Extraido de routes.py lista_pedidos() (531 linhas → metodos composiveis).
"""
from datetime import datetime
from urllib.parse import urlencode

from flask import url_for
from sqlalchemy import func
from sqlalchemy.orm import load_only

from app import db
from app.pedidos.models import Pedido


class ListaPedidosService:
    """Service com metodos estaticos para cada etapa da lista_pedidos."""

    # ---------------------------------------------------------------
    # 1. FILTROS DE STATUS (botoes rapidos)
    # ---------------------------------------------------------------
    @staticmethod
    def aplicar_filtros_status(query, filtro_status, filtro_data, hoje,
                               cnpjs_validos_agendamento=None,
                               lotes_falta_item_ids=None,
                               lotes_falta_pagamento_ids=None):
        """
        Aplica filtros de atalho (botoes rapidos) na query.
        Retorna (query, filtros_aplicados).
        """
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
            # 'todos' nao aplica filtro

        if filtro_data:
            filtros_aplicados = True
            try:
                data_selecionada = datetime.strptime(filtro_data, '%Y-%m-%d').date()
                query = query.filter(func.date(Pedido.expedicao) == data_selecionada)
            except ValueError:
                pass

        return query, filtros_aplicados

    # ---------------------------------------------------------------
    # 2. FILTROS DE FORMULARIO
    # ---------------------------------------------------------------
    @staticmethod
    def aplicar_filtros_formulario(query, filtro_form):
        """Aplica filtros do formulario (texto, selects, datas) na query."""
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
        params = dict(request_args)

        nova_ordem = 'asc'
        if params.get('sort_by') == campo and params.get('sort_order') == 'asc':
            nova_ordem = 'desc'

        params['sort_by'] = campo
        params['sort_order'] = nova_ordem

        return url_for('pedidos.lista_pedidos') + '?' + urlencode(params)

    @staticmethod
    def gerar_filtro_url(request_args, **kwargs):
        """Gera URL para filtros preservando todos os parametros atuais."""
        params = dict(request_args)

        for chave, valor in kwargs.items():
            if valor is None:
                params.pop(chave, None)
            else:
                params[chave] = valor

        return url_for('pedidos.lista_pedidos') + '?' + urlencode(params)
