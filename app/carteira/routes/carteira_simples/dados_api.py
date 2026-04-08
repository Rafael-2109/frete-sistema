"""
Rotas de consulta da Carteira Simplificada

- index: renderiza pagina
- obter_dados: query principal com filtros, estoque batch, separacoes
- autocomplete_produtos: busca produtos com saldo > 0
- rastrear_produto: separacoes de um produto (com codigos unificados)
- totais_protocolo: totais agregados por protocolo
"""

from flask import render_template, request, jsonify
from datetime import date, datetime, timedelta
from sqlalchemy import and_, func, or_, case
import logging
import time

from app import db
from app.carteira.models import CarteiraPrincipal, SaldoStandby
from app.separacao.models import Separacao
from app.producao.models import CadastroPalletizacao
from app.estoque.services.estoque_simples import ServicoEstoqueSimples
from app.estoque.models import UnificacaoCodigos
from app.localidades.models import CadastroRota, CadastroSubRota
from app.carteira.utils.separacao_utils import (
    buscar_rota_por_uf,
    buscar_sub_rota_por_uf_cidade,
)
from app.embarques.models import Embarque, EmbarqueItem
from app.transportadoras.models import Transportadora

from . import carteira_simples_bp
from .helpers import validar_numero_json, calcular_saidas_nao_visiveis

logger = logging.getLogger(__name__)


@carteira_simples_bp.route('/')
def index():
    """Renderiza pagina da carteira simplificada"""
    return render_template('carteira/simples.html')


@carteira_simples_bp.route('/api/dados')
def obter_dados():
    """
    Retorna dados da carteira com filtros aplicados

    Query params:
    - num_pedido: string
    - cnpj_cpf: string
    - cod_produto: string
    - data_pedido_de: YYYY-MM-DD
    - data_pedido_ate: YYYY-MM-DD
    - data_entrega_de: YYYY-MM-DD
    - data_entrega_ate: YYYY-MM-DD
    - estado: string (UF)
    - municipio: string
    - limit: int (default 100)
    - offset: int (default 0)
    """
    tempo_inicio = time.time()
    tempos = {}

    try:
        # Parametros de filtro
        busca_geral = request.args.get('busca_geral', '').strip()
        num_pedido = request.args.get('num_pedido', '').strip()
        cnpj_cpf = request.args.get('cnpj_cpf', '').strip()
        cod_produto = request.args.get('cod_produto', '').strip()
        data_pedido_de = request.args.get('data_pedido_de', '').strip()
        data_pedido_ate = request.args.get('data_pedido_ate', '').strip()
        data_entrega_de = request.args.get('data_entrega_de', '').strip()
        data_entrega_ate = request.args.get('data_entrega_ate', '').strip()
        estado = request.args.get('estado', '').strip()
        municipio = request.args.get('municipio', '').strip()
        rota = request.args.get('rota', '').strip()
        sub_rota = request.args.get('sub_rota', '').strip()
        limit = int(request.args.get('limit', 10000))
        offset = int(request.args.get('offset', 0))

        # Query base com JOINs para Rota e Sub-rota
        # OPT-B6: NOT EXISTS em vez de NOT IN (melhor plano de execucao, correto com NULLs)
        standby_exists = db.session.query(SaldoStandby.id).filter(
            SaldoStandby.num_pedido == CarteiraPrincipal.num_pedido,
            SaldoStandby.status_standby.in_(['ATIVO', 'BLOQ. COML.', 'SALDO'])
        ).correlate(CarteiraPrincipal).exists()

        query = db.session.query(CarteiraPrincipal).outerjoin(
            CadastroRota,
            CarteiraPrincipal.estado == CadastroRota.cod_uf
        ).outerjoin(
            CadastroSubRota,
            and_(
                CarteiraPrincipal.estado == CadastroSubRota.cod_uf,
                CarteiraPrincipal.municipio == CadastroSubRota.nome_cidade
            )
        ).filter(
            CarteiraPrincipal.ativo == True,
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0,
            ~standby_exists
        )

        # Aplicar filtros
        # BUSCA GERAL: Busca em multiplos campos simultaneamente (OR)
        if busca_geral:
            query = query.filter(
                or_(
                    CarteiraPrincipal.num_pedido.ilike(f'%{busca_geral}%'),
                    CarteiraPrincipal.raz_social_red.ilike(f'%{busca_geral}%'),
                    CarteiraPrincipal.pedido_cliente.ilike(f'%{busca_geral}%'),
                    CarteiraPrincipal.cnpj_cpf.ilike(f'%{busca_geral}%')
                )
            )

        if num_pedido:
            query = query.filter(CarteiraPrincipal.num_pedido.ilike(f'%{num_pedido}%'))

        if cnpj_cpf:
            query = query.filter(CarteiraPrincipal.cnpj_cpf.ilike(f'%{cnpj_cpf}%'))

        if cod_produto:
            query = query.filter(CarteiraPrincipal.cod_produto.ilike(f'%{cod_produto}%'))

        if data_pedido_de:
            query = query.filter(CarteiraPrincipal.data_pedido >= datetime.strptime(data_pedido_de, '%Y-%m-%d').date())

        if data_pedido_ate:
            query = query.filter(CarteiraPrincipal.data_pedido <= datetime.strptime(data_pedido_ate, '%Y-%m-%d').date())

        if data_entrega_de:
            query = query.filter(CarteiraPrincipal.data_entrega_pedido >= datetime.strptime(data_entrega_de, '%Y-%m-%d').date())

        if data_entrega_ate:
            query = query.filter(CarteiraPrincipal.data_entrega_pedido <= datetime.strptime(data_entrega_ate, '%Y-%m-%d').date())

        if estado:
            query = query.filter(CarteiraPrincipal.estado == estado)

        if municipio:
            query = query.filter(CarteiraPrincipal.municipio.ilike(f'%{municipio}%'))

        # Filtros de Rota considerando incoterm FOB/RED
        if rota:
            # Se filtro e FOB ou RED, buscar por incoterm
            if rota in ['FOB', 'RED']:
                query = query.filter(CarteiraPrincipal.incoterm == rota)
            else:
                # Para outras rotas (CIF), buscar normalmente na tabela CadastroRota
                query = query.filter(CadastroRota.rota == rota)

        if sub_rota:
            query = query.filter(CadastroSubRota.sub_rota == sub_rota)

        # ORDENACAO - MESMA HIERARQUIA DA CARTEIRA AGRUPADA
        # 1 Rota (com tratamento especial para FOB/RED via CASE)
        # 2 Sub-rota
        # 3 CNPJ
        # 4 Num_pedido (para agrupar produtos do mesmo pedido)
        # 5 Cod_produto (para ordenar produtos dentro do pedido)

        # CASE para tratar Incoterm FOB/RED como rota especial
        rota_ordenacao = case(
            (CarteiraPrincipal.incoterm == 'FOB', 'FOB'),
            (CarteiraPrincipal.incoterm == 'RED', 'RED'),
            else_=func.coalesce(CadastroRota.rota, 'ZZZZZ')
        )

        query = query.order_by(
            rota_ordenacao.asc(),
            func.coalesce(CadastroSubRota.sub_rota, 'ZZZZZ').asc(),
            func.coalesce(CarteiraPrincipal.cnpj_cpf, 'ZZZZZ').asc(),
            CarteiraPrincipal.num_pedido.asc(),
            CarteiraPrincipal.cod_produto.asc()
        )

        # BUSCAR TODOS os pedidos (sem paginacao - Virtual Scrolling e no frontend)
        t1 = time.time()
        items = query.all()
        total = len(items)
        tempos['query_items'] = time.time() - t1

        # Buscar dados de palletizacao (batch)
        t1 = time.time()
        codigos_produtos = [item.cod_produto for item in items]
        palletizacoes = db.session.query(CadastroPalletizacao).filter(
            CadastroPalletizacao.cod_produto.in_(codigos_produtos),
            CadastroPalletizacao.ativo == True
        ).all()
        tempos['palletizacoes'] = time.time() - t1

        # Criar mapa de palletizacao
        t1 = time.time()
        pallet_map = {p.cod_produto: p for p in palletizacoes}
        tempos['pallet_map'] = time.time() - t1

        # GERAR MAPA DE CODIGOS UNIFICADOS em BATCH (1 query em vez de N)
        # Formato: {cod_produto: [cod1, cod2, cod3]} - todos os codigos do mesmo grupo
        t1_unif = time.time()
        mapa_unificacao = UnificacaoCodigos.get_todos_codigos_relacionados_batch(codigos_produtos)
        logger.info(f"Unificacao batch: {(time.time() - t1_unif)*1000:.1f}ms para {len(codigos_produtos)} produtos")

        # CALCULAR QTD_CARTEIRA TOTAL EM BATCH (1 query em vez de N)
        t1_qtd = time.time()
        qtd_carteira_por_produto = {}

        # Expandir todos os codigos (incluindo unificados)
        todos_codigos_expandidos = set()
        for cod, relacionados in mapa_unificacao.items():
            todos_codigos_expandidos.update(relacionados)

        if todos_codigos_expandidos:
            # UMA query agregada para todos os produtos
            resultados_qtd = db.session.query(
                CarteiraPrincipal.cod_produto,
                func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido).label('qtd_total')
            ).filter(
                CarteiraPrincipal.ativo == True,
                CarteiraPrincipal.qtd_saldo_produto_pedido > 0,
                CarteiraPrincipal.cod_produto.in_(list(todos_codigos_expandidos)),
                ~standby_exists
            ).group_by(
                CarteiraPrincipal.cod_produto
            ).all()

            # Mapear resultados por codigo
            qtd_por_codigo = {str(r.cod_produto): float(r.qtd_total or 0) for r in resultados_qtd}

            # Agregar para cada produto original (somando codigos unificados)
            for cod_original in codigos_produtos:
                codigos_relacionados = mapa_unificacao.get(cod_original, [cod_original])
                qtd_carteira_por_produto[cod_original] = sum(
                    qtd_por_codigo.get(str(cod), 0) for cod in codigos_relacionados
                )
        else:
            # Sem codigos, todos com qtd 0
            for cod in codigos_produtos:
                qtd_carteira_por_produto[cod] = 0

        logger.info(f"Qtd carteira batch: {(time.time() - t1_qtd)*1000:.1f}ms")

        # Buscar separacoes nao sincronizadas (batch)
        separacoes = db.session.query(
            Separacao.num_pedido,
            Separacao.cod_produto,
            func.sum(Separacao.qtd_saldo).label('qtd_separada')
        ).filter(
            and_(
                Separacao.num_pedido.in_([item.num_pedido for item in items]),
                Separacao.cod_produto.in_(codigos_produtos),
                Separacao.sincronizado_nf == False
            )
        ).group_by(
            Separacao.num_pedido,
            Separacao.cod_produto
        ).all()

        # Criar mapa de separacoes
        sep_map = {(s.num_pedido, s.cod_produto): float(s.qtd_separada or 0) for s in separacoes}

        # Coletar produtos unicos para calculo de estoque em batch
        produtos_unicos = {}
        for item in items:
            if item.cod_produto not in produtos_unicos:
                produtos_unicos[item.cod_produto] = True

        # Calcular estoque em BATCH (2 queries em vez de N*2)
        # Front-end fara o calculo dinamico de projecao
        t1 = time.time()
        estoque_map = {}
        try:
            # Usar metodo otimizado de calculo em batch
            codigos_produtos_estoque = list(produtos_unicos.keys())

            if not codigos_produtos_estoque:
                logger.warning("Nenhum produto para calcular estoque")
                tempos['estoque_batch'] = time.time() - t1
            else:
                hoje = date.today()
                data_fim = hoje + timedelta(days=28)

                # Usar metodo batch (2 queries em vez de N*2)
                estoque_map = ServicoEstoqueSimples.calcular_estoque_batch(
                    codigos_produtos=codigos_produtos_estoque,
                    data_fim=data_fim,
                    mapa_unificacao=mapa_unificacao
                )

                logger.info(f"Estoque batch: {len(codigos_produtos_estoque)} produtos em {(time.time() - t1)*1000:.1f}ms")
                tempos['estoque_batch'] = time.time() - t1

        except Exception as e:
            logger.error(f"Erro ao calcular estoques em batch: {e}", exc_info=True)
            tempos['estoque_batch'] = time.time() - t1
            # Fallback: retornar estoque 0 para produtos com erro
            for cod_produto in list(produtos_unicos.keys()):
                if cod_produto not in estoque_map:
                    estoque_map[cod_produto] = {
                        'estoque_atual': 0,
                        'programacao': []
                    }

        # BUSCAR SEPARACOES NAO SINCRONIZADAS (sincronizado_nf=False)
        t1 = time.time()
        # Obter lista de pedidos da pagina atual
        pedidos_da_pagina = [item.num_pedido for item in items]

        # Buscar separacoes COM JOIN nas tabelas de Rota e Sub-rota
        separacoes_base = db.session.query(Separacao).outerjoin(
            CadastroRota,
            Separacao.cod_uf == CadastroRota.cod_uf
        ).outerjoin(
            CadastroSubRota,
            and_(
                Separacao.cod_uf == CadastroSubRota.cod_uf,
                Separacao.nome_cidade == CadastroSubRota.nome_cidade
            )
        ).filter(
            and_(
                Separacao.num_pedido.in_(pedidos_da_pagina),
                Separacao.sincronizado_nf == False
            )
        )

        # Aplicar filtro de produto tambem nas separacoes
        if cod_produto:
            separacoes_base = separacoes_base.filter(
                Separacao.cod_produto.ilike(f'%{cod_produto}%')
            )

        # APLICAR FILTROS DE ROTA E SUB-ROTA tambem nas separacoes (com incoterm FOB/RED)
        if rota:
            # Se filtro e FOB ou RED, buscar por incoterm nas separacoes tambem
            # IMPORTANTE: Separacao nao tem campo incoterm, entao buscar pelo pedido original
            if rota in ['FOB', 'RED']:
                # Buscar pedidos com incoterm FOB/RED
                pedidos_fob_red = db.session.query(CarteiraPrincipal.num_pedido).filter(
                    CarteiraPrincipal.incoterm == rota
                ).distinct().all()
                nums_pedidos_fob_red = [p[0] for p in pedidos_fob_red]

                if nums_pedidos_fob_red:
                    separacoes_base = separacoes_base.filter(
                        Separacao.num_pedido.in_(nums_pedidos_fob_red)
                    )
                else:
                    # Nao ha pedidos FOB/RED, retornar vazio
                    separacoes_base = separacoes_base.filter(False)
            else:
                # Para outras rotas (CIF), filtrar normalmente
                separacoes_base = separacoes_base.filter(CadastroRota.rota == rota)

        if sub_rota:
            separacoes_base = separacoes_base.filter(CadastroSubRota.sub_rota == sub_rota)

        # EXECUTAR query de separacoes FILTRADAS (visiveis)
        separacoes_query = separacoes_base.order_by(
            Separacao.num_pedido,
            Separacao.separacao_lote_id,
            Separacao.id
        ).all()

        # BUSCAR TODAS as separacoes (SEM filtros de rota/sub-rota) dos produtos
        # INCLUINDO codigos unificados!
        # OPT-B1: Reusar todos_codigos_expandidos ja calculado na linha 206-208
        # em vez de N queries individuais get_todos_codigos_relacionados()
        codigos_expandidos = todos_codigos_expandidos

        logger.info(f"Codigos da pagina: {len(codigos_produtos)} -> Expandidos com unificacao: {len(codigos_expandidos)}")

        separacoes_todas_query = db.session.query(Separacao).filter(
            and_(
                Separacao.cod_produto.in_(list(codigos_expandidos)),
                Separacao.sincronizado_nf == False
            )
        )
        separacoes_todas = separacoes_todas_query.all()

        tempos['separacoes'] = time.time() - t1

        # BUSCAR EMBARQUES E TRANSPORTADORAS (batch)
        t1 = time.time()
        separacao_lote_ids = [s.separacao_lote_id for s in separacoes_query if s.separacao_lote_id]
        embarques_map = {}

        if separacao_lote_ids:
            embarques_data = db.session.query(
                EmbarqueItem.separacao_lote_id,
                Embarque.numero,
                Transportadora.razao_social
            ).join(
                Embarque, EmbarqueItem.embarque_id == Embarque.id
            ).outerjoin(
                Transportadora, Embarque.transportadora_id == Transportadora.id
            ).filter(
                EmbarqueItem.separacao_lote_id.in_(separacao_lote_ids)
            ).all()

            for sep_lote_id, embarque_num, transp_nome in embarques_data:
                embarques_map[sep_lote_id] = {
                    'numero': embarque_num,
                    'transportadora': transp_nome or 'Sem transportadora'
                }
        tempos['embarques'] = time.time() - t1

        # Pre-processar dados para evitar loops aninhados
        t1 = time.time()
        # Montar resposta - ESTRUTURA HIERARQUICA PLANA
        dados = []

        # Agrupar produtos por pedido (uma vez so)
        produtos_por_pedido = {}
        for item in items:
            if item.num_pedido not in produtos_por_pedido:
                produtos_por_pedido[item.num_pedido] = []
            produtos_por_pedido[item.num_pedido].append(item)

        # Agrupar separacoes por pedido e depois por lote (uma vez so)
        separacoes_por_pedido_lote = {}
        for sep in separacoes_query:
            if sep.num_pedido not in separacoes_por_pedido_lote:
                separacoes_por_pedido_lote[sep.num_pedido] = {}

            if sep.separacao_lote_id not in separacoes_por_pedido_lote[sep.num_pedido]:
                separacoes_por_pedido_lote[sep.num_pedido][sep.separacao_lote_id] = []

            separacoes_por_pedido_lote[sep.num_pedido][sep.separacao_lote_id].append(sep)

        # Pre-buscar produtos de referencia para separacoes (evitar busca dentro de loop)
        produtos_ref_map = {}
        for item in items:
            chave = (item.num_pedido, item.cod_produto)
            if chave not in produtos_ref_map:
                produtos_ref_map[chave] = item

        # Pre-calcular TODAS as rotas em batch (evitar chamadas dentro do loop)
        rotas_cache = {}
        ufs_unicos = set()
        cidades_unicas = set()

        for item in items:
            if item.estado:
                ufs_unicos.add(item.estado)
                if item.municipio:
                    cidades_unicas.add((item.estado, item.municipio))

        # Pre-calcular rotas por UF (uma vez so)
        for uf in ufs_unicos:
            rota_calc = buscar_rota_por_uf(uf)
            rotas_cache[(uf, None)] = (rota_calc, None)

        # Pre-calcular sub-rotas por cidade (uma vez so)
        for uf, cidade in cidades_unicas:
            sub_rota_calc = buscar_sub_rota_por_uf_cidade(uf, cidade)
            if (uf, None) in rotas_cache:
                rota_existente = rotas_cache[(uf, None)][0]
                rotas_cache[(uf, cidade)] = (rota_existente, sub_rota_calc)

        logger.info(f"Rotas pre-calculadas: {len(ufs_unicos)} UFs, {len(cidades_unicas)} cidades")

        # Renderizar hierarquicamente - PRIMEIRO PRODUTOS, DEPOIS SEPARACOES
        pedidos_processados = set()

        for item in items:
            num_pedido_item = item.num_pedido

            # Se ainda nao processamos este pedido, processar TUDO dele
            if num_pedido_item not in pedidos_processados:
                pedidos_processados.add(num_pedido_item)

                # 1. ADICIONAR TODOS OS PRODUTOS DO PEDIDO
                produtos_do_pedido = produtos_por_pedido.get(num_pedido_item, [])

                for produto in produtos_do_pedido:
                    # Calcular qtd_saldo (carteira - separacoes nao sincronizadas)
                    qtd_separada = sep_map.get((produto.num_pedido, produto.cod_produto), 0)
                    qtd_saldo = float(produto.qtd_saldo_produto_pedido or 0) - qtd_separada

                    # Dados de palletizacao
                    pallet_info = pallet_map.get(produto.cod_produto)

                    palletizacao = validar_numero_json(
                        pallet_info.palletizacao if pallet_info else None,
                        100.0,
                        permitir_zero=False
                    )
                    peso_bruto = validar_numero_json(
                        pallet_info.peso_bruto if pallet_info else None,
                        1.0,
                        permitir_zero=False
                    )

                    # Calcular valores
                    preco_unitario = validar_numero_json(produto.preco_produto_pedido, 0)
                    valor_total = validar_numero_json(qtd_saldo * preco_unitario, 0)
                    pallets = validar_numero_json(qtd_saldo / palletizacao if palletizacao > 0 else 0, 0)
                    peso = validar_numero_json(qtd_saldo * peso_bruto, 0)

                    # Buscar dados de estoque (apenas estoque_atual + programacao)
                    estoque_info = estoque_map.get(produto.cod_produto, {
                        'estoque_atual': 0,
                        'programacao': []
                    })

                    # BUSCAR ROTA E SUB_ROTA do cache pre-calculado
                    # SEMPRE verificar incoterm FOB/RED PRIMEIRO
                    if hasattr(produto, 'incoterm') and produto.incoterm in ['FOB', 'RED']:
                        rota_calculada = produto.incoterm
                        sub_rota_calculada = None
                    else:
                        chave_cache = (produto.estado, produto.municipio) if produto.municipio else (produto.estado, None)
                        rotas_cached = rotas_cache.get(chave_cache, (None, None))
                        rota_calculada = rotas_cached[0]
                        sub_rota_calculada = rotas_cached[1]

                    data_pedido_str = produto.data_pedido.isoformat() if produto.data_pedido else None
                    data_entrega_str = produto.data_entrega_pedido.isoformat() if produto.data_entrega_pedido else None

                    # LINHA DO PEDIDO
                    dados.append({
                        'tipo': 'pedido',
                        'id': produto.id,
                        'num_pedido': produto.num_pedido,
                        'pedido_cliente': produto.pedido_cliente,
                        'data_pedido': data_pedido_str,
                        'data_entrega_pedido': data_entrega_str,
                        'cnpj_cpf': produto.cnpj_cpf,
                        'raz_social_red': produto.raz_social_red,
                        'estado': produto.estado,
                        'municipio': produto.municipio,
                        'cod_produto': produto.cod_produto,
                        'nome_produto': produto.nome_produto,
                        'qtd_saldo': qtd_saldo,
                        'qtd_original_pedido': float(produto.qtd_saldo_produto_pedido or 0),
                        'qtd_carteira': qtd_carteira_por_produto.get(produto.cod_produto, 0),
                        'preco_produto_pedido': preco_unitario,
                        'valor_total': valor_total,
                        'pallets': pallets,
                        'peso': peso,
                        'rota': rota_calculada,
                        'sub_rota': sub_rota_calculada,
                        'expedicao': None,
                        'agendamento': None,
                        'protocolo': None,
                        'agendamento_confirmado': False,
                        'palletizacao': palletizacao,
                        'peso_bruto': peso_bruto,
                        'estoque_atual': estoque_info['estoque_atual'],
                        'programacao': estoque_info['programacao'],
                        'observ_ped_1': produto.observ_ped_1[:200] if produto.observ_ped_1 else None,
                        'tags_pedido': produto.tags_pedido,
                        'equipe_vendas': produto.equipe_vendas or ''
                    })

                # 2. ADICIONAR TODAS AS SEPARACOES DO PEDIDO, AGRUPADAS POR LOTE
                separacoes_do_pedido = separacoes_por_pedido_lote.get(num_pedido_item, {})

                for separacao_lote_id, seps in separacoes_do_pedido.items():
                    for sep in seps:
                        # Buscar produto de referencia do map pre-calculado
                        chave_ref = (sep.num_pedido, sep.cod_produto)
                        produto_ref = produtos_ref_map.get(chave_ref)

                        # Dados de palletizacao para separacao
                        pallet_info_sep = pallet_map.get(sep.cod_produto)

                        palletizacao_sep = validar_numero_json(
                            pallet_info_sep.palletizacao if pallet_info_sep else None,
                            100.0,
                            permitir_zero=False
                        )
                        peso_bruto_sep = validar_numero_json(
                            pallet_info_sep.peso_bruto if pallet_info_sep else None,
                            1.0,
                            permitir_zero=False
                        )

                        # Buscar embarque + transportadora
                        embarque_info = embarques_map.get(sep.separacao_lote_id, {})
                        cliente_texto = ''
                        if embarque_info:
                            cliente_texto = f"Embarque #{embarque_info['numero']} - {embarque_info['transportadora']}"

                        # Calcular valores da separacao
                        qtd_sep = float(sep.qtd_saldo or 0)
                        preco_sep = float(produto_ref.preco_produto_pedido or 0) if produto_ref else 0
                        valor_sep = qtd_sep * preco_sep
                        pallets_sep = qtd_sep / palletizacao_sep if palletizacao_sep > 0 else 0
                        peso_sep = qtd_sep * peso_bruto_sep

                        # Buscar estoque (apenas estoque_atual + programacao)
                        estoque_info_sep = estoque_map.get(sep.cod_produto, {
                            'estoque_atual': 0,
                            'programacao': []
                        })

                        data_criacao_str = sep.criado_em.date().isoformat() if sep.criado_em else None
                        data_entrega_sep_str = produto_ref.data_entrega_pedido.isoformat() if (produto_ref and produto_ref.data_entrega_pedido) else None
                        expedicao_sep_str = sep.expedicao.isoformat() if sep.expedicao else None
                        agendamento_sep_str = sep.agendamento.isoformat() if sep.agendamento else None

                        # Extrair ultimos 10 digitos do separacao_lote_id
                        lote_id_completo = sep.separacao_lote_id or ''
                        lote_id_ultimos_10 = lote_id_completo[-10:] if len(lote_id_completo) >= 10 else lote_id_completo

                        dados.append({
                            'tipo': 'separacao',
                            'id': sep.id,
                            'separacao_id': sep.id,
                            'separacao_lote_id': sep.separacao_lote_id,
                            'num_pedido': sep.num_pedido,
                            'pedido_cliente': sep.pedido_cliente,
                            'data_pedido': data_criacao_str,
                            'data_entrega_pedido': data_entrega_sep_str,
                            'cnpj_cpf': sep.cnpj_cpf,
                            'raz_social_red': sep.raz_social_red,
                            'estado': produto_ref.estado if produto_ref else '',
                            'municipio': lote_id_ultimos_10,
                            'status_calculado': sep.status_calculado,
                            'cod_produto': sep.cod_produto,
                            'nome_produto': sep.nome_produto,
                            'qtd_saldo': qtd_sep,
                            'qtd_carteira': qtd_carteira_por_produto.get(sep.cod_produto, 0),
                            'preco_produto_pedido': preco_sep,
                            'valor_total': valor_sep,
                            'pallets': pallets_sep,
                            'peso': peso_sep,
                            'rota': sep.rota,
                            'sub_rota': sep.sub_rota,
                            'expedicao': expedicao_sep_str,
                            'agendamento': agendamento_sep_str,
                            'protocolo': sep.protocolo,
                            'agendamento_confirmado': sep.agendamento_confirmado,
                            'palletizacao': palletizacao_sep,
                            'peso_bruto': peso_bruto_sep,
                            'estoque_atual': estoque_info_sep['estoque_atual'],
                            'programacao': estoque_info_sep['programacao'],
                            'observ_ped_1': sep.observ_ped_1[:200] if sep.observ_ped_1 else None,
                            'tags_pedido': produto_ref.tags_pedido if produto_ref else None,
                            'equipe_vendas': produto_ref.equipe_vendas if produto_ref else ''
                        })
        tempos['montar_resposta'] = time.time() - t1

        # CALCULAR SAIDAS NAO VISIVEIS (para calculos de estoque completos)
        t1 = time.time()
        saidas_nao_visiveis = {}

        try:
            saidas_nao_visiveis = calcular_saidas_nao_visiveis(
                codigos_produtos=codigos_produtos,
                separacoes_todas=separacoes_todas,
                separacoes_filtradas=separacoes_query,
                mapa_unificacao=mapa_unificacao
            )

            tempos['saidas_nao_visiveis'] = time.time() - t1
            logger.info(f"Saidas nao visiveis calculadas em {tempos['saidas_nao_visiveis']:.3f}s")

        except Exception as e:
            logger.error(f"Erro ao calcular saidas nao visiveis (continuando sem elas): {e}", exc_info=True)
            saidas_nao_visiveis = {}
            tempos['saidas_nao_visiveis'] = time.time() - t1

        # PROFILING: Log de tempos
        tempo_total = time.time() - tempo_inicio
        logger.info(f"PROFILING /api/dados ({len(items)} itens, {len(dados)} linhas):")
        for chave, valor in tempos.items():
            logger.info(f"  - {chave}: {valor:.3f}s")
        logger.info(f"  TOTAL: {tempo_total:.3f}s")

        return jsonify({
            'success': True,
            'total': total,
            'limit': limit,
            'offset': offset,
            'dados': dados,
            'saidas_nao_visiveis': saidas_nao_visiveis,
            'mapa_unificacao': mapa_unificacao
        })

    except Exception as e:
        logger.error(f"Erro ao obter dados da carteira: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@carteira_simples_bp.route('/api/autocomplete-produtos')
def autocomplete_produtos():
    """
    Autocomplete para busca de produtos na carteira.
    Busca APENAS produtos que existem na carteira ativa (com saldo > 0).

    Query params:
    - termo: string (min 2 caracteres)
    - limit: int (default 20)

    Returns:
    - Lista de {cod_produto, nome_produto}
    """
    try:
        termo = request.args.get('termo', '').strip()
        limit_param = int(request.args.get('limit', 20))

        # Minimo 2 caracteres para buscar
        if not termo or len(termo) < 2:
            return jsonify([])

        # Buscar produtos DISTINTOS da CarteiraPrincipal onde tem saldo > 0
        subquery = db.session.query(
            CarteiraPrincipal.cod_produto,
            func.min(CarteiraPrincipal.nome_produto).label('nome_produto')
        ).filter(
            CarteiraPrincipal.ativo == True,
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0,
            or_(
                CarteiraPrincipal.cod_produto.ilike(f'%{termo}%'),
                CarteiraPrincipal.nome_produto.ilike(f'%{termo}%')
            )
        ).group_by(
            CarteiraPrincipal.cod_produto
        ).order_by(
            # Priorizar codigos que comecam com o termo
            case(
                (CarteiraPrincipal.cod_produto.ilike(f'{termo}%'), 0),
                else_=1
            ),
            CarteiraPrincipal.cod_produto
        ).limit(limit_param).all()

        resultado = [{
            'cod_produto': row.cod_produto,
            'nome_produto': row.nome_produto
        } for row in subquery]

        logger.debug(f"[AUTOCOMPLETE] Termo: '{termo}' -> {len(resultado)} produtos encontrados")

        return jsonify(resultado)

    except Exception as e:
        logger.error(f"[AUTOCOMPLETE] Erro ao buscar produtos: {e}", exc_info=True)
        return jsonify({'erro': str(e)}), 500


@carteira_simples_bp.route('/api/rastrear-produto')
def rastrear_produto():
    """
    Retorna todas as separacoes nao sincronizadas de um produto especifico,
    considerando codigos unificados (produtos equivalentes).

    Query params:
    - cod_produto: string (required)
    """
    try:
        cod_produto = request.args.get('cod_produto', '').strip()

        if not cod_produto:
            return jsonify({
                'success': False,
                'error': 'Parametro cod_produto e obrigatorio'
            }), 400

        # Buscar TODOS os codigos unificados (produtos equivalentes)
        codigos_unificados = UnificacaoCodigos.get_todos_codigos_relacionados(cod_produto)
        codigos_lista = list(codigos_unificados)

        logger.info(f"Rastreamento produto {cod_produto} - Codigos unificados: {codigos_lista}")

        # Buscar TODAS as separacoes nao sincronizadas de TODOS os codigos unificados
        separacoes_rastreio = Separacao.query.filter(
            Separacao.cod_produto.in_(codigos_lista),
            Separacao.sincronizado_nf == False
        ).order_by(
            Separacao.expedicao.asc(),
            Separacao.cod_produto.asc()
        ).all()

        # Formatar resposta
        separacoes_formatadas = []

        for sep in separacoes_rastreio:
            separacoes_formatadas.append({
                'separacao_lote_id': sep.separacao_lote_id,
                'cod_produto': sep.cod_produto,
                'raz_social_red': sep.raz_social_red,
                'qtd_saldo': float(sep.qtd_saldo or 0),
                'expedicao': sep.expedicao.isoformat() if sep.expedicao else None,
                'valor_saldo': float(sep.valor_saldo or 0),
                'status': sep.status,
                'status_calculado': sep.status_calculado
            })

        logger.info(f"Rastreamento produto {cod_produto}: {len(separacoes_formatadas)} separacoes encontradas (codigos unificados: {len(codigos_lista)})")

        return jsonify({
            'success': True,
            'cod_produto_pesquisado': cod_produto,
            'codigos_unificados': codigos_lista,
            'separacoes': separacoes_formatadas,
            'total': len(separacoes_formatadas)
        })

    except Exception as e:
        logger.error(f"Erro ao rastrear produto: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@carteira_simples_bp.route('/api/totais-protocolo', methods=['GET'])
def totais_protocolo():
    """
    Buscar totais agregados de todas as separacoes com um protocolo especifico

    Query params:
        protocolo (str): Protocolo para buscar totais

    Returns:
        JSON com valor_total, peso_total, pallet_total e qtd_separacoes
    """
    try:
        protocolo_param = request.args.get('protocolo', '').strip()

        if not protocolo_param:
            return jsonify({
                'erro': 'Protocolo nao informado'
            }), 400

        # Buscar todas as separacoes com este protocolo (sincronizado_nf=False)
        separacoes_proto = Separacao.query.filter(
            and_(
                Separacao.protocolo == protocolo_param,
                Separacao.sincronizado_nf == False
            )
        ).all()

        if not separacoes_proto:
            return jsonify({
                'protocolo': protocolo_param,
                'qtd_separacoes': 0,
                'valor_total': 0,
                'peso_total': 0,
                'pallet_total': 0,
                'mensagem': 'Nenhuma separacao encontrada com este protocolo'
            })

        # Agregar totais
        valor_total = 0
        peso_total = 0
        pallet_total = 0

        for sep in separacoes_proto:
            valor_total += float(sep.valor_saldo or 0)
            peso_total += float(sep.peso or 0)
            pallet_total += float(sep.pallet or 0)

        return jsonify({
            'protocolo': protocolo_param,
            'qtd_separacoes': len(separacoes_proto),
            'valor_total': round(valor_total, 2),
            'peso_total': round(peso_total, 2),
            'pallet_total': round(pallet_total, 2)
        })

    except Exception as e:
        logger.error(f"Erro ao buscar totais do protocolo: {e}", exc_info=True)
        return jsonify({
            'erro': f'Erro ao buscar totais: {str(e)}'
        }), 500
