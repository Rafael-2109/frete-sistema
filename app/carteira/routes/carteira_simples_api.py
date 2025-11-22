"""
API para Carteira de Pedidos Simplificada
Carteira compacta com edição inline e cálculos dinâmicos
"""

from flask import Blueprint, render_template, request, jsonify
from datetime import date, datetime, timedelta
from sqlalchemy import and_, func
import logging

from app import db
from app.carteira.models import CarteiraPrincipal
from app.separacao.models import Separacao
from app.producao.models import CadastroPalletizacao
from app.estoque.services.estoque_simples import ServicoEstoqueSimples
from app.estoque.models import UnificacaoCodigos
from app.localidades.models import CadastroRota, CadastroSubRota
from app.carteira.utils.separacao_utils import (
    calcular_peso_pallet_produto,
    buscar_rota_por_uf,
    buscar_sub_rota_por_uf_cidade,
)
from app.utils.lote_utils import gerar_lote_id
from app.utils.timezone import agora_brasil
from app.embarques.models import Embarque, EmbarqueItem
from app.transportadoras.models import Transportadora

logger = logging.getLogger(__name__)

# Blueprint
# url_prefix='/simples' porque este blueprint é registrado DENTRO de carteira_bp (/carteira)
# URL final: /carteira + /simples = /carteira/simples
carteira_simples_bp = Blueprint('carteira_simples', __name__, url_prefix='/simples')


def validar_numero_json(valor, padrao, permitir_zero=True):
    """
    Valida um número para garantir que é JSON-serializável (não NaN/Infinity)

    Args:
        valor: Valor a validar
        padrao: Valor padrão caso validação falhe
        permitir_zero: Se True, aceita 0 como valor válido

    Returns:
        float válido ou valor padrão
    """
    try:
        numero = float(valor) if valor is not None else padrao
        # Verificar se é um número válido (não NaN, não Infinity)
        if numero != numero or numero == float('inf') or numero == float('-inf'):
            return padrao
        # Verificar se é negativo
        if numero < 0:
            return padrao
        # Verificar se é zero quando não permitido
        if not permitir_zero and numero == 0:
            return padrao
        return numero
    except (ValueError, TypeError, AttributeError):
        return padrao


def converter_entradas_para_frontend(entradas_dict):
    """
    Converte Dict[date, float] para List[Dict[str, Any]] esperado pelo frontend.

    Formato esperado pelo frontend:
    [
        {'data': '2025-01-07', 'qtd': 100.0},
        {'data': '2025-01-08', 'qtd': 200.0}
    ]

    Args:
        entradas_dict: Dict[date, float] retornado por ServicoEstoqueSimples

    Returns:
        List[Dict[str, Any]] no formato esperado pelo frontend
    """
    try:
        if not entradas_dict:
            return []

        programacao = []
        for data_entrada, qtd in entradas_dict.items():
            # Validar data
            if not isinstance(data_entrada, date):
                logger.warning(f"Data inválida ignorada: {data_entrada}")
                continue

            # Validar quantidade
            qtd_validada = validar_numero_json(qtd, 0, permitir_zero=True)

            if qtd_validada > 0:  # Só incluir se qtd > 0
                programacao.append({
                    'data': data_entrada.isoformat(),
                    'qtd': qtd_validada
                })

        # Ordenar por data (garantir ordem cronológica)
        programacao.sort(key=lambda x: x['data'])

        return programacao

    except Exception as e:
        logger.error(f"Erro ao converter entradas para frontend: {e}")
        return []


def atualizar_embarque_item_por_separacao(separacao_lote_id):
    """
    Atualiza EmbarqueItem quando uma Separacao do lote é modificada
    Recalcula peso, valor e pallets somando todas as Separacoes do lote

    Args:
        separacao_lote_id: ID do lote de separação

    Returns:
        bool: True se atualizou, False se não encontrou EmbarqueItem
    """
    try:
        if not separacao_lote_id:
            return False

        # Buscar EmbarqueItem correspondente (apenas ativos)
        embarque_item = EmbarqueItem.query.filter_by(
            separacao_lote_id=separacao_lote_id,
            status='ativo'
        ).first()

        if not embarque_item:
            logger.debug(f"[EMBARQUE] Lote {separacao_lote_id} não está embarcado")
            return False

        # Buscar TODAS as Separacoes deste lote
        separacoes_lote = Separacao.query.filter_by(
            separacao_lote_id=separacao_lote_id
        ).all()

        if not separacoes_lote:
            logger.warning(f"[EMBARQUE] ⚠️ Lote {separacao_lote_id} sem separações - zerando EmbarqueItem")
            embarque_item.peso = 0
            embarque_item.valor = 0
            embarque_item.pallets = 0
        else:
            # Recalcular totais somando todas as separações do lote
            embarque_item.peso = sum(float(s.peso or 0) for s in separacoes_lote)
            embarque_item.valor = sum(float(s.valor_saldo or 0) for s in separacoes_lote)
            embarque_item.pallets = sum(float(s.pallet or 0) for s in separacoes_lote)

            logger.info(
                f"[EMBARQUE] ✅ EmbarqueItem ID={embarque_item.id} atualizado: "
                f"Peso={embarque_item.peso:.2f}, Valor={embarque_item.valor:.2f}, "
                f"Pallets={embarque_item.pallets:.2f} (baseado em {len(separacoes_lote)} separações)"
            )

        # Commit das alterações (o trigger do banco atualizará o Embarque automaticamente)
        db.session.commit()

        return True

    except Exception as e:
        db.session.rollback()
        logger.error(f"[EMBARQUE] ❌ Erro ao atualizar EmbarqueItem do lote {separacao_lote_id}: {e}", exc_info=True)
        return False


@carteira_simples_bp.route('/')
def index():
    """Renderiza página da carteira simplificada"""
    return render_template('carteira/simples.html')


@carteira_simples_bp.route('/teste-fontes')
def teste_fontes():
    """Página de teste de fontes - TEMPORÁRIA"""
    return render_template('carteira/teste_fontes.html')


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
    import time
    tempo_inicio = time.time()
    tempos = {}  # 🚀 PROFILING: Rastrear tempo de cada etapa

    try:
        # Parâmetros de filtro
        busca_geral = request.args.get('busca_geral', '').strip()  # 🆕 Busca em múltiplos campos
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
        limit = int(request.args.get('limit', 10000))  # 🆕 Aumentado para remover paginação
        offset = int(request.args.get('offset', 0))

        # 🔧 CORREÇÃO: Query base com JOINs para Rota e Sub-rota
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
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        )

        # Aplicar filtros
        # 🆕 BUSCA GERAL: Busca em múltiplos campos simultaneamente (OR)
        if busca_geral:
            from sqlalchemy import or_
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

        # 🔧 CORREÇÃO CRÍTICA: Filtros de Rota considerando incoterm FOB/RED
        if rota:
            from sqlalchemy import or_
            # Se filtro é FOB ou RED, buscar por incoterm
            if rota in ['FOB', 'RED']:
                query = query.filter(CarteiraPrincipal.incoterm == rota)
            else:
                # Para outras rotas (CIF), buscar normalmente na tabela CadastroRota
                query = query.filter(CadastroRota.rota == rota)

        if sub_rota:
            query = query.filter(CadastroSubRota.sub_rota == sub_rota)

        # 🆕 ORDENAÇÃO - MESMA HIERARQUIA DA CARTEIRA AGRUPADA
        # 1º Rota (com tratamento especial para FOB/RED via CASE)
        # 2º Sub-rota
        # 3º CNPJ
        # 4º Num_pedido (para agrupar produtos do mesmo pedido)
        # 5º Cod_produto (para ordenar produtos dentro do pedido)
        from sqlalchemy import case

        # CASE para tratar Incoterm FOB/RED como rota especial
        rota_ordenacao = case(
            (CarteiraPrincipal.incoterm == 'FOB', 'FOB'),
            (CarteiraPrincipal.incoterm == 'RED', 'RED'),
            else_=func.coalesce(CadastroRota.rota, 'ZZZZZ')
        )

        query = query.order_by(
            rota_ordenacao.asc(),                                      # 1º Rota/Incoterm (A-Z, nulls no final)
            func.coalesce(CadastroSubRota.sub_rota, 'ZZZZZ').asc(),  # 2º Sub-rota (A-Z, nulls no final)
            func.coalesce(CarteiraPrincipal.cnpj_cpf, 'ZZZZZ').asc(), # 3º CNPJ (0-9, nulls no final)
            CarteiraPrincipal.num_pedido.asc(),                        # 4º Num_pedido
            CarteiraPrincipal.cod_produto.asc()                        # 5º Cod_produto
        )

        # ✅ BUSCAR TODOS os pedidos (sem paginação - Virtual Scrolling é no frontend)
        t1 = time.time()
        items = query.all()  # TODOS os pedidos filtrados (por rota, estado, etc.)
        total = len(items)
        tempos['query_items'] = time.time() - t1

        # Buscar dados de palletização (batch)
        t1 = time.time()
        codigos_produtos = [item.cod_produto for item in items]
        palletizacoes = db.session.query(CadastroPalletizacao).filter(
            CadastroPalletizacao.cod_produto.in_(codigos_produtos),
            CadastroPalletizacao.ativo == True
        ).all()
        tempos['palletizacoes'] = time.time() - t1

        # Criar mapa de palletização
        t1 = time.time()
        pallet_map = {p.cod_produto: p for p in palletizacoes}
        tempos['pallet_map'] = time.time() - t1

        # 🆕 GERAR MAPA DE CÓDIGOS UNIFICADOS para frontend
        # Formato: {cod_produto: [cod1, cod2, cod3]} - todos os códigos do mesmo grupo
        mapa_unificacao = {}
        for cod_produto in codigos_produtos:
            codigos_relacionados = UnificacaoCodigos.get_todos_codigos_relacionados(cod_produto)
            # Cada código aponta para a lista completa de códigos do grupo
            mapa_unificacao[cod_produto] = list(codigos_relacionados)

        # 🆕 CALCULAR QTD_CARTEIRA TOTAL POR PRODUTO (✅ COM UNIFICAÇÃO)
        qtd_carteira_por_produto = {}

        # Para cada código da página, calcular soma de TODOS os códigos unificados
        for cod_produto in codigos_produtos:
            codigos_relacionados = mapa_unificacao.get(cod_produto, [cod_produto])

            # Somar quantidades de TODOS os códigos relacionados
            resultados_soma = db.session.query(
                func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido).label('qtd_total')
            ).filter(
                CarteiraPrincipal.ativo == True,
                CarteiraPrincipal.cod_produto.in_(codigos_relacionados)  # ✅ USA UNIFICAÇÃO!
            ).scalar()

            qtd_carteira_por_produto[cod_produto] = float(resultados_soma or 0)

        # Buscar separações não sincronizadas (batch)
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

        # Criar mapa de separações
        sep_map = {(s.num_pedido, s.cod_produto): float(s.qtd_separada or 0) for s in separacoes}

        # 🚀 OTIMIZAÇÃO: Calcular estoque em BATCH para produtos únicos
        # 🔧 CORREÇÃO: Coletar TODOS os produtos (não só os com qtd_saldo > 0)
        produtos_unicos = {}
        for item in items:
            if item.cod_produto not in produtos_unicos:
                produtos_unicos[item.cod_produto] = {
                    'qtd_total_carteira': 0,
                    'expedicao': item.expedicao  # Usar primeira data de expedição encontrada
                }

            qtd_separada = sep_map.get((item.num_pedido, item.cod_produto), 0)
            qtd_saldo = float(item.qtd_saldo_produto_pedido or 0) - qtd_separada

            if qtd_saldo > 0:
                produtos_unicos[item.cod_produto]['qtd_total_carteira'] += qtd_saldo

        # 🚀 OTIMIZAÇÃO CRÍTICA: Calcular APENAS estoque atual (não projeção completa)
        # Front-end fará o cálculo dinâmico de projeção
        t1 = time.time()
        estoque_map = {}
        try:
            # Usar método otimizado de cálculo em batch
            codigos_produtos = list(produtos_unicos.keys())

            # ✅ PROTEÇÃO: Só calcular estoque se houver produtos
            if not codigos_produtos:
                logger.warning("⚠️ Nenhum produto para calcular estoque")
                tempos['estoque_batch'] = time.time() - t1
                # Pular para próxima etapa
            else:
                # ✅ MUDANÇA: Calcular APENAS estoque atual (performance 10x melhor)
                hoje = date.today()
                data_fim = hoje + timedelta(days=28)

                # Buscar estoque atual para todos os produtos em batch
                for cod_produto in codigos_produtos:
                    estoque_atual = ServicoEstoqueSimples.calcular_estoque_atual(cod_produto)

                    # ✅ USAR ServicoEstoqueSimples para buscar programação com UNIFICAÇÃO DE CÓDIGOS
                    # IMPORTANTE: entrada_em_d_plus_1=False porque frontend já aplica D+1 (linha 2444 JS)
                    entradas_dict = ServicoEstoqueSimples.calcular_entradas_previstas(
                        cod_produto,
                        hoje,
                        data_fim,
                        entrada_em_d_plus_1=False  # Frontend aplica D+1, então backend não deve aplicar
                    )

                    # Converter Dict[date, float] → List[Dict[str, Any]] para frontend
                    programacao = converter_entradas_para_frontend(entradas_dict)

                    estoque_map[cod_produto] = {
                        'estoque_atual': estoque_atual,
                        'programacao': programacao  # ✅ NOVO: Programação para front-end calcular
                    }

                logger.info(f"✅ Estoque atual calculado em BATCH para {len(codigos_produtos)} produtos")
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

        # 🆕 BUSCAR SEPARAÇÕES NÃO SINCRONIZADAS (sincronizado_nf=False)
        t1 = time.time()
        # Obter lista de pedidos da página atual
        pedidos_da_pagina = [item.num_pedido for item in items]

        # 🔧 CORREÇÃO: Buscar separações COM JOIN nas tabelas de Rota e Sub-rota
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

        # 🔧 APLICAR FILTROS DE ROTA E SUB-ROTA também nas separações (com incoterm FOB/RED)
        if rota:
            # 🆕 Se filtro é FOB ou RED, buscar por incoterm nas separações também
            # IMPORTANTE: Separacao não tem campo incoterm, então buscar pelo pedido original
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
                    # Não há pedidos FOB/RED, retornar vazio
                    separacoes_base = separacoes_base.filter(False)
            else:
                # Para outras rotas (CIF), filtrar normalmente
                separacoes_base = separacoes_base.filter(CadastroRota.rota == rota)

        if sub_rota:
            separacoes_base = separacoes_base.filter(CadastroSubRota.sub_rota == sub_rota)

        # ✅ EXECUTAR query de separações FILTRADAS (visíveis)
        separacoes_query = separacoes_base.order_by(
            Separacao.num_pedido,
            Separacao.separacao_lote_id,
            Separacao.id
        ).all()

        # ✅ BUSCAR TODAS as separações (SEM filtros de rota/sub-rota) dos produtos
        # ✅ INCLUINDO códigos unificados!
        codigos_expandidos = set()
        for cod in codigos_produtos:
            codigos_relacionados = UnificacaoCodigos.get_todos_codigos_relacionados(cod)
            codigos_expandidos.update(codigos_relacionados)

        logger.info(f"🔍 Códigos da página: {len(codigos_produtos)} → Expandidos com unificação: {len(codigos_expandidos)}")

        separacoes_todas_query = db.session.query(Separacao).filter(
            and_(
                Separacao.cod_produto.in_(list(codigos_expandidos)),  # ✅ Busca códigos unificados!
                Separacao.sincronizado_nf == False
            )
        )
        separacoes_todas = separacoes_todas_query.all()

        tempos['separacoes'] = time.time() - t1

        # 🆕 BUSCAR EMBARQUES E TRANSPORTADORAS (batch)
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

        # 🚀 OTIMIZAÇÃO: Pré-processar dados para evitar loops aninhados
        t1 = time.time()
        # Montar resposta - ESTRUTURA HIERÁRQUICA PLANA
        dados = []

        # 🔧 Agrupar produtos por pedido (uma vez só)
        produtos_por_pedido = {}
        for item in items:
            if item.num_pedido not in produtos_por_pedido:
                produtos_por_pedido[item.num_pedido] = []
            produtos_por_pedido[item.num_pedido].append(item)

        # 🔧 Agrupar separações por pedido e depois por lote (uma vez só)
        separacoes_por_pedido_lote = {}
        for sep in separacoes_query:
            if sep.num_pedido not in separacoes_por_pedido_lote:
                separacoes_por_pedido_lote[sep.num_pedido] = {}

            if sep.separacao_lote_id not in separacoes_por_pedido_lote[sep.num_pedido]:
                separacoes_por_pedido_lote[sep.num_pedido][sep.separacao_lote_id] = []

            separacoes_por_pedido_lote[sep.num_pedido][sep.separacao_lote_id].append(sep)

        # 🚀 OTIMIZAÇÃO: Pré-buscar produtos de referência para separações (evitar busca dentro de loop)
        produtos_ref_map = {}  # {(num_pedido, cod_produto): item}
        for item in items:
            chave = (item.num_pedido, item.cod_produto)
            if chave not in produtos_ref_map:
                produtos_ref_map[chave] = item

        # 🚀 OTIMIZAÇÃO: Pré-calcular TODAS as rotas em batch (evitar chamadas dentro do loop)
        rotas_cache = {}  # {(estado, municipio): (rota, sub_rota)}
        ufs_unicos = set()
        cidades_unicas = set()

        for item in items:
            if item.estado:
                ufs_unicos.add(item.estado)
                if item.municipio:
                    cidades_unicas.add((item.estado, item.municipio))

        # Pré-calcular rotas por UF (uma vez só)
        for uf in ufs_unicos:
            rota = buscar_rota_por_uf(uf)
            rotas_cache[(uf, None)] = (rota, None)

        # Pré-calcular sub-rotas por cidade (uma vez só)
        for uf, cidade in cidades_unicas:
            sub_rota = buscar_sub_rota_por_uf_cidade(uf, cidade)
            if (uf, None) in rotas_cache:
                rota_existente = rotas_cache[(uf, None)][0]
                rotas_cache[(uf, cidade)] = (rota_existente, sub_rota)

        logger.info(f"✅ Rotas pré-calculadas: {len(ufs_unicos)} UFs, {len(cidades_unicas)} cidades")

        # 🔧 NOVO: Renderizar hierarquicamente - PRIMEIRO PRODUTOS, DEPOIS SEPARAÇÕES
        pedidos_processados = set()

        for item in items:
            num_pedido = item.num_pedido

            # Se ainda não processamos este pedido, processar TUDO dele
            if num_pedido not in pedidos_processados:
                pedidos_processados.add(num_pedido)

                # 1️⃣ ADICIONAR TODOS OS PRODUTOS DO PEDIDO
                produtos_do_pedido = produtos_por_pedido.get(num_pedido, [])

                for produto in produtos_do_pedido:
                    # Calcular qtd_saldo (carteira - separações não sincronizadas)
                    qtd_separada = sep_map.get((produto.num_pedido, produto.cod_produto), 0)
                    qtd_saldo = float(produto.qtd_saldo_produto_pedido or 0) - qtd_separada

                    # Dados de palletização
                    pallet_info = pallet_map.get(produto.cod_produto)

                    # 🔧 CORREÇÃO: Validar para evitar NaN no JSON
                    palletizacao = validar_numero_json(
                        pallet_info.palletizacao if pallet_info else None,
                        100.0,
                        permitir_zero=False  # Palletizacao não pode ser 0
                    )
                    peso_bruto = validar_numero_json(
                        pallet_info.peso_bruto if pallet_info else None,
                        1.0,
                        permitir_zero=False  # Peso bruto não pode ser 0
                    )

                    # Calcular valores
                    preco_unitario = validar_numero_json(produto.preco_produto_pedido, 0)
                    valor_total = validar_numero_json(qtd_saldo * preco_unitario, 0)
                    pallets = validar_numero_json(qtd_saldo / palletizacao if palletizacao > 0 else 0, 0)
                    peso = validar_numero_json(qtd_saldo * peso_bruto, 0)

                    # Buscar dados de estoque (apenas estoque_atual + programação)
                    estoque_info = estoque_map.get(produto.cod_produto, {
                        'estoque_atual': 0,
                        'programacao': []
                    })

                    # 🚀 OTIMIZAÇÃO: BUSCAR ROTA E SUB_ROTA do cache pré-calculado
                    # 🔧 CORREÇÃO: SEMPRE verificar incoterm FOB/RED PRIMEIRO
                    if hasattr(produto, 'incoterm') and produto.incoterm in ['FOB', 'RED']:
                        rota_calculada = produto.incoterm
                        sub_rota_calculada = None  # FOB/RED não tem sub-rota
                    else:
                        rota_calculada = produto.rota
                        sub_rota_calculada = produto.sub_rota

                        if not rota_calculada or not sub_rota_calculada:
                            # Buscar do cache pré-calculado
                            chave_cache = (produto.estado, produto.municipio) if produto.municipio else (produto.estado, None)
                            rotas_cached = rotas_cache.get(chave_cache, (None, None))

                            if not rota_calculada:
                                rota_calculada = rotas_cached[0]
                            if not sub_rota_calculada:
                                sub_rota_calculada = rotas_cached[1]

                    # 🚀 OTIMIZAÇÃO: Pré-calcular datas (evitar strftime repetido)
                    data_pedido_str = produto.data_pedido.isoformat() if produto.data_pedido else None
                    data_entrega_str = produto.data_entrega_pedido.isoformat() if produto.data_entrega_pedido else None
                    expedicao_str = produto.expedicao.isoformat() if produto.expedicao else None
                    agendamento_str = produto.agendamento.isoformat() if produto.agendamento else None

                    # ✅ LINHA DO PEDIDO
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
                        'qtd_original_pedido': float(produto.qtd_saldo_produto_pedido or 0),  # 🆕 QTD ORIGINAL DESTE PEDIDO
                        'qtd_carteira': qtd_carteira_por_produto.get(produto.cod_produto, 0),  # 🆕 SOMA DE TODOS OS PEDIDOS
                        'preco_produto_pedido': preco_unitario,
                        'valor_total': valor_total,
                        'pallets': pallets,
                        'peso': peso,
                        'rota': rota_calculada,
                        'sub_rota': sub_rota_calculada,
                        'expedicao': expedicao_str,
                        'agendamento': agendamento_str,
                        'protocolo': produto.protocolo,
                        'agendamento_confirmado': produto.agendamento_confirmado,
                        'palletizacao': palletizacao,
                        'peso_bruto': peso_bruto,
                        'estoque_atual': estoque_info['estoque_atual'],
                        'programacao': estoque_info['programacao'],  # ✅ NOVO: Programação para front-end
                        # 🆕 OBSERVAÇÕES E TAGS PARA CARTEIRA SIMPLES
                        'observ_ped_1': produto.observ_ped_1[:200] if produto.observ_ped_1 else None,  # Truncado para tooltip
                        'tags_pedido': produto.tags_pedido  # JSON string das tags do Odoo
                    })

                # 2️⃣ ADICIONAR TODAS AS SEPARAÇÕES DO PEDIDO, AGRUPADAS POR LOTE
                separacoes_do_pedido = separacoes_por_pedido_lote.get(num_pedido, {})

                for separacao_lote_id, seps in separacoes_do_pedido.items():
                    for sep in seps:
                        # 🚀 OTIMIZAÇÃO: Buscar produto de referência do map pré-calculado
                        chave_ref = (sep.num_pedido, sep.cod_produto)
                        produto_ref = produtos_ref_map.get(chave_ref)

                        # Dados de palletização para separação
                        pallet_info_sep = pallet_map.get(sep.cod_produto)

                        # 🔧 CORREÇÃO: Validar para evitar NaN no JSON
                        palletizacao_sep = validar_numero_json(
                            pallet_info_sep.palletizacao if pallet_info_sep else None,
                            100.0,
                            permitir_zero=False  # Palletizacao não pode ser 0
                        )
                        peso_bruto_sep = validar_numero_json(
                            pallet_info_sep.peso_bruto if pallet_info_sep else None,
                            1.0,
                            permitir_zero=False  # Peso bruto não pode ser 0
                        )

                        # Buscar embarque + transportadora
                        embarque_info = embarques_map.get(sep.separacao_lote_id, {})
                        cliente_texto = ''
                        if embarque_info:
                            cliente_texto = f"Embarque #{embarque_info['numero']} - {embarque_info['transportadora']}"

                        # Calcular valores da separação
                        qtd_sep = float(sep.qtd_saldo or 0)
                        preco_sep = float(produto_ref.preco_produto_pedido or 0) if produto_ref else 0
                        valor_sep = qtd_sep * preco_sep
                        pallets_sep = qtd_sep / palletizacao_sep if palletizacao_sep > 0 else 0
                        peso_sep = qtd_sep * peso_bruto_sep

                        # Buscar estoque (apenas estoque_atual + programação)
                        estoque_info_sep = estoque_map.get(sep.cod_produto, {
                            'estoque_atual': 0,
                            'programacao': []
                        })

                        # 🚀 OTIMIZAÇÃO: Pré-calcular datas para separações
                        data_criacao_str = sep.criado_em.date().isoformat() if sep.criado_em else None
                        data_entrega_sep_str = produto_ref.data_entrega_pedido.isoformat() if (produto_ref and produto_ref.data_entrega_pedido) else None
                        expedicao_sep_str = sep.expedicao.isoformat() if sep.expedicao else None
                        agendamento_sep_str = sep.agendamento.isoformat() if sep.agendamento else None

                        # ✅ CORREÇÃO: Extrair últimos 10 dígitos do separacao_lote_id
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
                            'cnpj_cpf': sep.cnpj_cpf,  # ✅ CORREÇÃO: Usar CNPJ da separação
                            'raz_social_red': sep.raz_social_red,  # ✅ CORREÇÃO: Usar razão social da separação
                            'estado': produto_ref.estado if produto_ref else '',
                            'municipio': lote_id_ultimos_10,  # ✅ CORREÇÃO: Exibir últimos 10 dígitos do lote_id
                            'status_calculado': sep.status_calculado,
                            'cod_produto': sep.cod_produto,
                            'nome_produto': sep.nome_produto,
                            'qtd_saldo': qtd_sep,
                            'qtd_carteira': qtd_carteira_por_produto.get(sep.cod_produto, 0),  # 🆕 SOMA DE TODOS OS PEDIDOS
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
                            'programacao': estoque_info_sep['programacao']  # ✅ NOVO: Programação para front-end
                        })
        tempos['montar_resposta'] = time.time() - t1

        # 🆕 CALCULAR SAÍDAS NÃO VISÍVEIS (para cálculos de estoque completos)
        t1 = time.time()
        saidas_nao_visiveis = {}

        try:
            # ✅ Calcular saídas NÃO visíveis: TODAS - FILTRADAS
            saidas_nao_visiveis = calcular_saidas_nao_visiveis(
                codigos_produtos=codigos_produtos,
                separacoes_todas=separacoes_todas,  # TODAS as separações dos produtos
                separacoes_filtradas=separacoes_query  # Separações FILTRADAS (com rota/sub-rota)
            )

            tempos['saidas_nao_visiveis'] = time.time() - t1
            logger.info(f"✅ Saídas não visíveis calculadas em {tempos['saidas_nao_visiveis']:.3f}s")

        except Exception as e:
            logger.error(f"❌ Erro ao calcular saídas não visíveis (continuando sem elas): {e}", exc_info=True)
            saidas_nao_visiveis = {}
            tempos['saidas_nao_visiveis'] = time.time() - t1

        # 🚀 PROFILING: Log de tempos
        tempo_total = time.time() - tempo_inicio
        print(f"\n{'='*60}")
        print(f"⏱️ PROFILING /api/dados ({len(items)} itens, {len(dados)} linhas):")
        logger.info(f"⏱️ PROFILING /api/dados ({len(items)} itens, {len(dados)} linhas):")
        for chave, valor in tempos.items():
            print(f"  - {chave}: {valor:.3f}s")
            logger.info(f"  - {chave}: {valor:.3f}s")
        print(f"  ⏱️ TOTAL: {tempo_total:.3f}s")
        print(f"{'='*60}\n")
        logger.info(f"  ⏱️ TOTAL: {tempo_total:.3f}s")

        return jsonify({
            'success': True,
            'total': total,
            'limit': limit,
            'offset': offset,
            'dados': dados,
            'saidas_nao_visiveis': saidas_nao_visiveis,  # 🆕 Saídas não visíveis
            'mapa_unificacao': mapa_unificacao  # 🆕 NOVO: Mapa de códigos unificados
        })

    except Exception as e:
        logger.error(f"Erro ao obter dados da carteira: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def calcular_saidas_nao_visiveis(
    codigos_produtos,
    separacoes_todas,
    separacoes_filtradas
):
    """
    Calcula saídas NÃO visíveis usando: TODAS - FILTRADAS

    ⚠️ IMPORTANTE: Apenas Separacao.expedicao contém datas de saída.

    LÓGICA PERFEITA:
    1. Recebe separacoes_todas (todas as separações dos pedidos da página)
    2. Recebe separacoes_filtradas (separações que passaram pelos filtros)
    3. Calcula: NÃO VISÍVEIS = TODAS - FILTRADAS
    4. Agrupa por produto + data

    Args:
        codigos_produtos (list): Lista de códigos de produtos
        separacoes_todas (list): TODAS as separações dos pedidos (sem filtros)
        separacoes_filtradas (list): Separações FILTRADAS (visíveis)

    Returns:
        dict: {cod_produto: [{'data': '2025-10-23', 'qtd': 100.0}]}
    """
    try:
        logger.info(f"🔍 Calculando saídas NÃO visíveis (TODAS - FILTRADAS)...")

        # 1. Criar SET de IDs das separações FILTRADAS (visíveis)
        ids_filtradas = set(sep.id for sep in separacoes_filtradas)

        logger.info(f"   Total separações: {len(separacoes_todas)}")
        logger.info(f"   Separações filtradas (visíveis): {len(ids_filtradas)}")

        # 2. Filtrar separações NÃO VISÍVEIS = TODAS - FILTRADAS
        # ✅ INCLUIR separações sem data (expedicao is None) - serão agrupadas em hoje
        separacoes_nao_visiveis = [
            sep for sep in separacoes_todas
            if sep.id not in ids_filtradas
        ]

        logger.info(f"   Separações NÃO visíveis: {len(separacoes_nao_visiveis)}")

        # 3. ✅ Agrupar por produto + data COM UNIFICAÇÃO
        hoje = date.today()
        saidas_por_produto_data = {}

        for sep in separacoes_nao_visiveis:
            cod_prod_original = sep.cod_produto
            qtd = float(sep.qtd_saldo or 0)

            if qtd <= 0:
                continue

            # ✅ Agrupar separações sem data ou atrasadas em hoje
            if not sep.expedicao or sep.expedicao < hoje:
                data_exp = hoje.isoformat()
            else:
                data_exp = sep.expedicao.isoformat()

            # ✅ ADICIONAR apenas para o "código representante" do grupo (menor código)
            # Isso evita duplicação quando múltiplos códigos do mesmo grupo estão na página
            codigos_relacionados = UnificacaoCodigos.get_todos_codigos_relacionados(cod_prod_original)

            # Encontrar quais códigos do grupo estão na página
            codigos_na_pagina = [c for c in codigos_relacionados if c in codigos_produtos]

            if codigos_na_pagina:
                # Usar o MENOR código como representante (para consistência)
                codigo_representante = min(codigos_na_pagina)

                chave = (codigo_representante, data_exp)
                if chave in saidas_por_produto_data:
                    saidas_por_produto_data[chave] += qtd
                else:
                    saidas_por_produto_data[chave] = qtd

        # 4. Converter para formato final
        saidas_consolidadas = {}

        for cod_prod in codigos_produtos:
            saidas_consolidadas[cod_prod] = []

        for (cod_prod, data_exp), qtd in saidas_por_produto_data.items():
            if cod_prod in codigos_produtos:  # ✅ Garantir que código está na página
                saidas_consolidadas[cod_prod].append({
                    'data': data_exp,
                    'qtd': qtd
                })

        # 5. Ordenar por data
        for cod_prod in saidas_consolidadas:
            saidas_consolidadas[cod_prod].sort(key=lambda x: x['data'])

        # Log final
        total_saidas = sum(len(s) for s in saidas_consolidadas.values())
        logger.info(f"✅ Saídas NÃO visíveis: {total_saidas} saídas calculadas")

        return saidas_consolidadas

    except Exception as e:
        logger.error(f"❌ Erro ao calcular saídas não visíveis: {e}", exc_info=True)
        return {cod_prod: [] for cod_prod in codigos_produtos}


@carteira_simples_bp.route('/api/estoque-projetado')
def obter_estoque_projetado():
    """
    Calcula estoque projetado para um produto em uma data
    considerando uma quantidade que será separada

    Query params:
    - cod_produto: string (required)
    - data_expedicao: YYYY-MM-DD (required)
    - qtd_editavel: float (required)
    - dias: int (7 ou 28, default 7)
    """
    try:
        cod_produto = request.args.get('cod_produto', '').strip()
        data_expedicao_str = request.args.get('data_expedicao', '').strip()
        qtd_editavel = float(request.args.get('qtd_editavel', 0))
        dias = int(request.args.get('dias', 7))

        if not cod_produto or not data_expedicao_str:
            return jsonify({
                'success': False,
                'error': 'Parâmetros obrigatórios: cod_produto, data_expedicao'
            }), 400

        # Converter data
        data_expedicao = datetime.strptime(data_expedicao_str, '%Y-%m-%d').date()

        # Obter códigos relacionados
        codigos = UnificacaoCodigos.get_todos_codigos_relacionados(cod_produto)

        # Estoque atual
        estoque_atual = ServicoEstoqueSimples.calcular_estoque_atual(cod_produto)

        # Calcular projeção para os próximos dias
        hoje = date.today()
        data_inicio = max(hoje, data_expedicao)
        data_fim = data_inicio + timedelta(days=dias)

        # Projeção diária
        projecoes = []
        estoque_dia = estoque_atual
        menor_estoque = estoque_atual

        # Obter saídas e entradas previstas
        # ✅ USAR entrada_em_d_plus_1=True NA CARTEIRA SIMPLES
        saidas = ServicoEstoqueSimples.calcular_saidas_previstas(cod_produto, hoje, data_fim)
        entradas = ServicoEstoqueSimples.calcular_entradas_previstas(
            cod_produto, hoje, data_fim,
            entrada_em_d_plus_1=True  # Programação entra em D+1 (apenas Carteira Simples)
        )

        for i in range(dias + 1):
            dia = data_inicio + timedelta(days=i)

            # Saída do dia
            saida_dia = saidas.get(dia, 0)

            # Se for o dia da expedição editável, adicionar qtd_editavel nas saídas
            if dia == data_expedicao and qtd_editavel > 0:
                saida_dia += qtd_editavel

            # Entrada do dia
            entrada_dia = entradas.get(dia, 0)

            # Calcular estoque do dia
            estoque_dia = estoque_dia - saida_dia + entrada_dia

            # Atualizar menor estoque
            if estoque_dia < menor_estoque:
                menor_estoque = estoque_dia

            projecoes.append({
                'data': dia.strftime('%Y-%m-%d'),
                'dia_nome': dia.strftime('%a'),  # Seg, Ter, Qua...
                'estoque': round(estoque_dia, 2),
                'saida': round(saida_dia, 2),
                'entrada': round(entrada_dia, 2)
            })

        # Estoque na data de expedição (considerando qtd_editavel)
        estoque_na_data = estoque_atual
        for dia in range((data_expedicao - hoje).days + 1):
            dia_calc = hoje + timedelta(days=dia)
            saida = saidas.get(dia_calc, 0)
            entrada = entradas.get(dia_calc, 0)

            # Adicionar qtd_editavel no dia da expedição
            if dia_calc == data_expedicao:
                saida += qtd_editavel

            estoque_na_data = estoque_na_data - saida + entrada

        return jsonify({
            'success': True,
            'estoque_atual': round(estoque_atual, 2),
            'estoque_na_data': round(estoque_na_data, 2),
            'menor_estoque_7d': round(menor_estoque, 2),
            'projecoes': projecoes
        })

    except Exception as e:
        logger.error(f"Erro ao calcular estoque projetado: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@carteira_simples_bp.route('/api/gerar-separacao', methods=['POST'])
def gerar_separacao():
    """
    Gera separação (Separacao) com status='ABERTO'

    Body JSON:
    {
        "num_pedido": "123456",
        "produtos": [
            {
                "cod_produto": "ABC123",
                "quantidade": 100.0,
                "expedicao": "2025-10-20",
                "agendamento": "2025-10-19",
                "protocolo": "PROT123"
            }
        ]
    }
    """
    try:
        dados = request.get_json()

        if not dados or 'num_pedido' not in dados or 'produtos' not in dados:
            return jsonify({
                'success': False,
                'error': 'Dados inválidos. Esperado: {num_pedido, produtos}'
            }), 400

        num_pedido = dados['num_pedido']
        produtos = dados['produtos']

        if not produtos or not isinstance(produtos, list):
            return jsonify({
                'success': False,
                'error': 'Lista de produtos vazia ou inválida'
            }), 400

        # Gerar lote_id único
        lote_id = gerar_lote_id()

        # 🔧 DETERMINAR tipo_envio CORRETAMENTE: verificar se está separando TODOS os produtos
        from app.carteira.utils.separacao_utils import determinar_tipo_envio

        # Buscar produtos na carteira para validação
        produtos_carteira = {}
        for item in CarteiraPrincipal.query.filter_by(num_pedido=num_pedido, ativo=True).all():
            produtos_carteira[item.cod_produto] = item

        tipo_envio_correto = determinar_tipo_envio(num_pedido, produtos, produtos_carteira)
        logger.info(f"✅ tipo_envio determinado: {tipo_envio_correto} para pedido {num_pedido}")

        separacoes_criadas = []

        for produto in produtos:
            cod_produto = produto.get('cod_produto')
            quantidade = float(produto.get('quantidade', 0))
            expedicao_str = produto.get('expedicao', '')
            agendamento_str = produto.get('agendamento', '')
            protocolo = produto.get('protocolo', '')

            if not cod_produto or quantidade <= 0:
                continue

            # Buscar item na carteira
            item_carteira = CarteiraPrincipal.query.filter_by(
                num_pedido=num_pedido,
                cod_produto=cod_produto,
                ativo=True
            ).first()

            if not item_carteira:
                logger.warning(f"Item não encontrado na carteira: {num_pedido}/{cod_produto}")
                continue

            # Verificar se quantidade está disponível
            # Buscar separações não sincronizadas
            qtd_separada = db.session.query(
                func.sum(Separacao.qtd_saldo)
            ).filter(
                and_(
                    Separacao.num_pedido == num_pedido,
                    Separacao.cod_produto == cod_produto,
                    Separacao.sincronizado_nf == False
                )
            ).scalar() or 0

            qtd_disponivel = float(item_carteira.qtd_saldo_produto_pedido or 0) - float(qtd_separada)

            if quantidade > qtd_disponivel:
                return jsonify({
                    'success': False,
                    'error': f'Quantidade indisponível para {cod_produto}. Disponível: {qtd_disponivel:.2f}'
                }), 400

            # Converter datas
            try:
                expedicao = datetime.strptime(expedicao_str, '%Y-%m-%d').date() if expedicao_str else None
            except (ValueError, TypeError):
                expedicao = None

            try:
                agendamento = datetime.strptime(agendamento_str, '%Y-%m-%d').date() if agendamento_str else None
            except (ValueError, TypeError):
                agendamento = None

            # Calcular valores
            preco_unitario = float(item_carteira.preco_produto_pedido or 0)
            valor_separacao = quantidade * preco_unitario

            # Calcular peso e pallet
            peso_calculado, pallet_calculado = calcular_peso_pallet_produto(cod_produto, quantidade)

            # Buscar rota
            if hasattr(item_carteira, 'incoterm') and item_carteira.incoterm in ["RED", "FOB"]:
                rota_calculada = item_carteira.incoterm
            else:
                rota_calculada = buscar_rota_por_uf(item_carteira.cod_uf or 'SP')

            sub_rota_calculada = buscar_sub_rota_por_uf_cidade(
                item_carteira.cod_uf or '',
                item_carteira.nome_cidade or ''
            )

            # Criar separação
            separacao = Separacao(
                separacao_lote_id=lote_id,
                num_pedido=num_pedido,
                data_pedido=item_carteira.data_pedido,
                cnpj_cpf=item_carteira.cnpj_cpf,
                raz_social_red=item_carteira.raz_social_red,
                nome_cidade=item_carteira.nome_cidade,
                cod_uf=item_carteira.cod_uf,
                cod_produto=cod_produto,
                nome_produto=item_carteira.nome_produto,
                qtd_saldo=quantidade,
                valor_saldo=valor_separacao,
                peso=peso_calculado,
                pallet=pallet_calculado,
                rota=rota_calculada,
                sub_rota=sub_rota_calculada,
                observ_ped_1=item_carteira.observ_ped_1[:700] if item_carteira.observ_ped_1 else None,
                roteirizacao=None,
                expedicao=expedicao,
                agendamento=agendamento,
                protocolo=protocolo,
                pedido_cliente=item_carteira.pedido_cliente,
                tipo_envio=tipo_envio_correto,  # 🔧 CORRIGIDO: Usa determinar_tipo_envio()
                status='ABERTO',
                sincronizado_nf=False,
                criado_em=agora_brasil()
            )

            db.session.add(separacao)
            separacoes_criadas.append(separacao)

        if not separacoes_criadas:
            return jsonify({
                'success': False,
                'error': 'Nenhuma separação foi criada'
            }), 400

        db.session.commit()

        # ✅ Preparar dados das separações criadas para o frontend
        separacoes_retorno = []
        produtos_afetados = set()

        # 🆕 Calcular estoque atual + programação para produtos afetados
        hoje = date.today()
        data_fim = hoje + timedelta(days=28)

        estoque_map = {}
        produtos_unicos = list(set([sep.cod_produto for sep in separacoes_criadas]))

        for cod_produto in produtos_unicos:
            estoque_atual = ServicoEstoqueSimples.calcular_estoque_atual(cod_produto)

            # ✅ USAR ServicoEstoqueSimples para buscar programação com UNIFICAÇÃO DE CÓDIGOS
            # IMPORTANTE: entrada_em_d_plus_1=False porque frontend já aplica D+1
            entradas_dict = ServicoEstoqueSimples.calcular_entradas_previstas(
                cod_produto,
                hoje,
                data_fim,
                entrada_em_d_plus_1=False  # Frontend aplica D+1, então backend não deve aplicar
            )

            # Converter Dict[date, float] → List[Dict[str, Any]] para frontend
            programacao = converter_entradas_para_frontend(entradas_dict)

            estoque_map[cod_produto] = {
                'estoque_atual': estoque_atual,
                'programacao': programacao
            }

        for sep in separacoes_criadas:
            estoque_info = estoque_map.get(sep.cod_produto, {'estoque_atual': 0, 'programacao': []})

            # ✅ Extrair últimos 10 dígitos do lote_id
            lote_id_completo = sep.separacao_lote_id or ''
            lote_id_ultimos_10 = lote_id_completo[-10:] if len(lote_id_completo) >= 10 else lote_id_completo

            separacoes_retorno.append({
                'id': sep.id,
                'separacao_lote_id': sep.separacao_lote_id,
                'num_pedido': sep.num_pedido,
                'cod_produto': sep.cod_produto,
                'nome_produto': sep.nome_produto,
                'qtd_saldo': float(sep.qtd_saldo),
                'valor_saldo': float(sep.valor_saldo or 0),
                'peso': float(sep.peso or 0),
                'pallet': float(sep.pallet or 0),
                'expedicao': sep.expedicao.isoformat() if sep.expedicao else None,
                'agendamento': sep.agendamento.isoformat() if sep.agendamento else None,
                'protocolo': sep.protocolo,
                'agendamento_confirmado': sep.agendamento_confirmado or False,
                'cnpj_cpf': sep.cnpj_cpf,
                'raz_social_red': sep.raz_social_red,
                'nome_cidade': sep.nome_cidade,
                'municipio': lote_id_ultimos_10,  # ✅ Últimos 10 dígitos do lote (padrão da tela)
                'estado': sep.cod_uf,  # ✅ UF no campo estado
                'cod_uf': sep.cod_uf,
                'rota': sep.rota,
                'sub_rota': sep.sub_rota,
                'data_pedido': sep.data_pedido.isoformat() if sep.data_pedido else None,
                'pedido_cliente': sep.pedido_cliente,
                'tipo': 'separacao',
                'status_calculado': sep.status or 'ABERTO',  # ✅ Status para cor amarela
                'estoque_atual': estoque_info['estoque_atual'],
                'programacao': estoque_info['programacao']
            })
            produtos_afetados.add(sep.cod_produto)

        logger.info(f"✅ Lote {lote_id}: {len(separacoes_criadas)} separação(ões) criada(s)")

        return jsonify({
            'success': True,
            'message': f'{len(separacoes_criadas)} separação(ões) criada(s) com sucesso',
            'separacao_lote_id': lote_id,
            'qtd_itens': len(separacoes_criadas),
            'separacoes': separacoes_retorno,  # ✅ Dados completos para frontend
            'produtos_afetados': list(produtos_afetados)  # ✅ Para recalcular estoques
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao gerar separação: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@carteira_simples_bp.route('/api/atualizar-qtd-separacao', methods=['POST'])
def atualizar_qtd_separacao():
    """
    Atualiza quantidade de uma separação em tempo real

    Body JSON:
    {
        "separacao_id": 123,
        "nova_qtd": 50.5
    }
    """
    try:
        dados = request.get_json()

        if not dados or 'separacao_id' not in dados or 'nova_qtd' not in dados:
            return jsonify({
                'success': False,
                'error': 'Dados inválidos. Esperado: {separacao_id, nova_qtd}'
            }), 400

        separacao_id = int(dados['separacao_id'])
        nova_qtd = float(dados['nova_qtd'])

        if nova_qtd < 0:
            return jsonify({
                'success': False,
                'error': 'Quantidade deve ser maior ou igual a zero'
            }), 400

        # Buscar separação
        separacao = Separacao.query.get(separacao_id)

        if not separacao:
            return jsonify({
                'success': False,
                'error': 'Separação não encontrada'
            }), 404

        # Buscar item da carteira para validação
        item_carteira = CarteiraPrincipal.query.filter_by(
            num_pedido=separacao.num_pedido,
            cod_produto=separacao.cod_produto,
            ativo=True
        ).first()

        if not item_carteira:
            return jsonify({
                'success': False,
                'error': 'Item não encontrado na carteira'
            }), 404

        # Calcular total já separado (excluindo esta separação)
        total_separado = db.session.query(
            func.sum(Separacao.qtd_saldo)
        ).filter(
            and_(
                Separacao.num_pedido == separacao.num_pedido,
                Separacao.cod_produto == separacao.cod_produto,
                Separacao.sincronizado_nf == False,
                Separacao.id != separacao_id  # Excluir esta separação
            )
        ).scalar() or 0

        # Validar se nova quantidade não excede disponível
        qtd_disponivel = float(item_carteira.qtd_saldo_produto_pedido or 0) - float(total_separado)

        if nova_qtd > qtd_disponivel:
            return jsonify({
                'success': False,
                'error': f'Quantidade indisponível. Disponível: {qtd_disponivel:.2f}'
            }), 400

        # 🆕 SE NOVA QTD = 0 → DELETAR SEPARAÇÃO DO BANCO DE DADOS
        if nova_qtd == 0:
            logger.info(f"🗑️ Deletando separação ID={separacao_id} (qtd=0)")

            # Guardar dados antes de deletar (para retornar ao frontend)
            separacao_lote_id_deletado = separacao.separacao_lote_id
            separacao_deletada = {
                'id': separacao.id,
                'num_pedido': separacao.num_pedido,
                'cod_produto': separacao.cod_produto,
                'separacao_lote_id': separacao.separacao_lote_id,
                'qtd_saldo': 0,
                'valor_saldo': 0,
                'peso': 0,
                'pallet': 0
            }

            # DELETAR do banco de dados
            db.session.delete(separacao)
            db.session.commit()

            # ✅ ATUALIZAR EmbarqueItem se esta separação estiver embarcada
            atualizar_embarque_item_por_separacao(separacao_lote_id_deletado)

            logger.info(f"✅ Separação ID={separacao_id} deletada com sucesso")

            # Retornar resposta indicando deleção
            return jsonify({
                'success': True,
                'message': 'Separação deletada com sucesso (qtd=0)',
                'deletado': True,
                'separacao': separacao_deletada
            })

        # SE QTD > 0 → ATUALIZAR QUANTIDADE (comportamento original)
        # Atualizar quantidade
        separacao.qtd_saldo = nova_qtd

        # Recalcular valores
        preco_unitario = float(item_carteira.preco_produto_pedido or 0)
        separacao.valor_saldo = nova_qtd * preco_unitario

        # Recalcular peso e pallet
        peso_calculado, pallet_calculado = calcular_peso_pallet_produto(
            separacao.cod_produto,
            nova_qtd
        )
        separacao.peso = peso_calculado
        separacao.pallet = pallet_calculado

        db.session.commit()

        # ✅ ATUALIZAR EmbarqueItem se esta separação estiver embarcada
        atualizar_embarque_item_por_separacao(separacao.separacao_lote_id)

        # Retornar dados atualizados
        return jsonify({
            'success': True,
            'message': 'Quantidade atualizada com sucesso',
            'deletado': False,
            'separacao': {
                'id': separacao.id,
                'qtd_saldo': float(separacao.qtd_saldo),
                'valor_saldo': float(separacao.valor_saldo or 0),
                'peso': float(separacao.peso or 0),
                'pallet': float(separacao.pallet or 0)
            },
            # Retornar qtd disponível no pedido atualizada
            'qtd_disponivel_pedido': qtd_disponivel - nova_qtd
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao atualizar quantidade separação: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@carteira_simples_bp.route('/api/confirmar-agendamento', methods=['POST'])
def confirmar_agendamento():
    """
    ✅ CORRIGIDO: Confirma agendamento em Separacao (não CarteiraPrincipal)

    Body JSON:
    {
        "num_pedido": "123456",
        "cod_produto": "ABC123",
        "protocolo": "PROT123"
    }
    """
    try:
        dados = request.get_json()

        if not dados or 'num_pedido' not in dados or 'cod_produto' not in dados:
            return jsonify({
                'success': False,
                'error': 'Dados inválidos. Esperado: {num_pedido, cod_produto, protocolo}'
            }), 400

        num_pedido = dados['num_pedido']
        cod_produto = dados['cod_produto']
        protocolo = dados.get('protocolo', '')

        if not protocolo:
            return jsonify({
                'success': False,
                'error': 'Protocolo é obrigatório para confirmação'
            }), 400

        # ✅ CORREÇÃO: Buscar separações não sincronizadas (não CarteiraPrincipal)
        separacoes = Separacao.query.filter_by(
            num_pedido=num_pedido,
            cod_produto=cod_produto,
            sincronizado_nf=False  # Apenas separações ativas
        ).all()

        if not separacoes or len(separacoes) == 0:
            return jsonify({
                'success': False,
                'error': 'Nenhuma separação ativa encontrada para este pedido/produto'
            }), 404

        # ✅ CORREÇÃO: Atualizar TODAS as separações do produto
        qtd_atualizadas = 0
        lotes_afetados = set()
        for sep in separacoes:
            sep.agendamento_confirmado = True
            sep.protocolo = protocolo
            qtd_atualizadas += 1
            if sep.separacao_lote_id:
                lotes_afetados.add(sep.separacao_lote_id)

        db.session.commit()

        logger.info(f"✅ Agendamento confirmado: {qtd_atualizadas} separação(ões) de {num_pedido}/{cod_produto}")

        # ✅ SINCRONIZAR com EmbarqueItem (se existir)
        tabelas_sincronizadas = []
        try:
            from app.pedidos.services.sincronizacao_agendamento_service import SincronizadorAgendamentoService

            sincronizador = SincronizadorAgendamentoService(usuario='Sistema')
            for lote_id in lotes_afetados:
                resultado_sync = sincronizador.sincronizar_desde_separacao(
                    separacao_lote_id=lote_id,
                    criar_agendamento=False
                )
                if resultado_sync['success']:
                    tabelas = resultado_sync.get('tabelas_atualizadas', [])
                    tabelas_sincronizadas.extend(tabelas)

            if tabelas_sincronizadas:
                logger.info(f"[SINCRONIZAÇÃO] Tabelas atualizadas: {', '.join(set(tabelas_sincronizadas))}")
        except Exception as sync_error:
            logger.warning(f"Aviso na sincronização: {sync_error}")

        return jsonify({
            'success': True,
            'message': f'Agendamento confirmado com sucesso ({qtd_atualizadas} separação(ões))',
            'tabelas_sincronizadas': list(set(tabelas_sincronizadas))
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao confirmar agendamento: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@carteira_simples_bp.route('/api/atualizar-separacao-lote', methods=['POST'])
def atualizar_separacao_lote():
    """
    ✅ REFATORADO: Atualiza campos de TODAS as separações de um lote

    Body JSON:
    {
        "separacao_lote_id": "ABC123",
        "expedicao": "2025-01-20"              // opcional
        "agendamento": "2025-01-19"            // opcional
        "protocolo": "PROT123"                 // opcional
        "agendamento_confirmado": true/false   // opcional
    }
    """
    try:
        dados = request.get_json()

        if not dados or 'separacao_lote_id' not in dados:
            return jsonify({
                'success': False,
                'error': 'Dados inválidos. Esperado: {separacao_lote_id, [expedicao|agendamento|protocolo]}'
            }), 400

        separacao_lote_id = dados['separacao_lote_id']

        # Campos permitidos para atualização
        campos_atualizaveis = {}

        # Processar expedicao
        if 'expedicao' in dados:
            try:
                campos_atualizaveis['expedicao'] = datetime.strptime(dados['expedicao'], '%Y-%m-%d').date() if dados['expedicao'] else None
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'error': 'Data de expedição inválida. Use formato YYYY-MM-DD'
                }), 400

        # Processar agendamento
        if 'agendamento' in dados:
            try:
                campos_atualizaveis['agendamento'] = datetime.strptime(dados['agendamento'], '%Y-%m-%d').date() if dados['agendamento'] else None
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'error': 'Data de agendamento inválida. Use formato YYYY-MM-DD'
                }), 400

        # Processar protocolo
        if 'protocolo' in dados:
            campos_atualizaveis['protocolo'] = dados['protocolo']

        # Processar agendamento_confirmado
        if 'agendamento_confirmado' in dados:
            campos_atualizaveis['agendamento_confirmado'] = bool(dados['agendamento_confirmado'])

        if not campos_atualizaveis:
            return jsonify({
                'success': False,
                'error': 'Nenhum campo válido para atualizar. Use: expedicao, agendamento, protocolo ou agendamento_confirmado'
            }), 400

        # Buscar TODAS as separações do lote
        separacoes = Separacao.query.filter_by(
            separacao_lote_id=separacao_lote_id
        ).all()

        if not separacoes:
            return jsonify({
                'success': False,
                'error': 'Nenhuma separação encontrada para este lote'
            }), 404

        # Atualizar campos de TODAS as separações do lote
        for sep in separacoes:
            for campo, valor in campos_atualizaveis.items():
                setattr(sep, campo, valor)

        db.session.commit()
        db.session.expire_all()  # ✅ INVALIDAR Identity Map (cache da sessão)

        # 🆕 RECALCULAR ESTOQUE PROJETADO (apenas se alterou expedicao)
        estoque_atualizado = {}
        if 'expedicao' in campos_atualizaveis:
            # Obter códigos de produtos afetados (únicos)
            codigos_afetados = list(set([sep.cod_produto for sep in separacoes]))

            # Calcular novo estoque projetado
            for cod_produto in codigos_afetados:
                try:
                    projecao = ServicoEstoqueSimples.calcular_projecao(
                        cod_produto, 28, entrada_em_d_plus_1=True  # ✅ D+1 na Carteira Simples
                    )

                    estoque_atualizado[cod_produto] = {
                        'estoque_atual': projecao.get('estoque_atual', 0),
                        'menor_estoque_d7': projecao.get('menor_estoque_d7', 0),
                        'projecoes': projecao.get('projecao', [])
                    }
                except Exception as e:
                    logger.error(f"Erro ao recalcular estoque de {cod_produto}: {e}")

        campos_atualizados = ', '.join(campos_atualizaveis.keys())
        logger.info(f"✅ Lote {separacao_lote_id}: {len(separacoes)} separação(ões) atualizada(s) - Campos: {campos_atualizados}")

        # ✅ SINCRONIZAR com EmbarqueItem (se existir) quando campos de agendamento foram alterados
        tabelas_sincronizadas = []
        campos_agendamento = {'agendamento', 'protocolo', 'agendamento_confirmado'}
        if campos_agendamento.intersection(campos_atualizaveis.keys()):
            try:
                from app.pedidos.services.sincronizacao_agendamento_service import SincronizadorAgendamentoService

                sincronizador = SincronizadorAgendamentoService(usuario='Sistema')
                resultado_sync = sincronizador.sincronizar_desde_separacao(
                    separacao_lote_id=separacao_lote_id,
                    criar_agendamento=False
                )

                if resultado_sync['success']:
                    tabelas_sincronizadas = resultado_sync.get('tabelas_atualizadas', [])
                    if tabelas_sincronizadas:
                        logger.info(f"[SINCRONIZAÇÃO] Tabelas atualizadas: {', '.join(tabelas_sincronizadas)}")
            except Exception as sync_error:
                logger.warning(f"Aviso na sincronização: {sync_error}")

        return jsonify({
            'success': True,
            'message': f'{len(separacoes)} separação(ões) atualizada(s) com sucesso ({campos_atualizados})',
            'qtd_atualizada': len(separacoes),
            'separacao_lote_id': separacao_lote_id,
            'campos_atualizados': list(campos_atualizaveis.keys()),
            'estoque_atualizado': estoque_atualizado if estoque_atualizado else None,
            'tabelas_sincronizadas': tabelas_sincronizadas
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao atualizar separação em lote: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@carteira_simples_bp.route('/api/verificar-separacoes-existentes', methods=['POST'])
def verificar_separacoes_existentes():
    """
    Verifica se um pedido já possui separações não sincronizadas
    e retorna os lotes agrupados com totais

    Body JSON:
    {
        "num_pedido": "123456"
    }

    Response:
    {
        "success": true,
        "tem_separacoes": true,
        "lotes": [
            {
                "separacao_lote_id": "SEP-2025-001",
                "expedicao": "2025-01-20",
                "agendamento": "2025-01-21",
                "protocolo": "ABC123",
                "agendamento_confirmado": false,
                "qtd_itens": 3,
                "valor_total": 15000.00,
                "pallet_total": 5.50,
                "peso_total": 2500.0
            }
        ]
    }
    """
    try:
        dados = request.get_json()

        if not dados or 'num_pedido' not in dados:
            return jsonify({
                'success': False,
                'error': 'Dados inválidos. Esperado: {num_pedido}'
            }), 400

        num_pedido = dados['num_pedido']

        # Buscar separações não sincronizadas do pedido
        separacoes = db.session.query(Separacao).filter(
            and_(
                Separacao.num_pedido == num_pedido,
                Separacao.sincronizado_nf == False
            )
        ).all()

        if not separacoes or len(separacoes) == 0:
            return jsonify({
                'success': True,
                'tem_separacoes': False,
                'lotes': []
            })

        # Agrupar por separacao_lote_id e calcular totais
        lotes_map = {}

        for sep in separacoes:
            lote_id = sep.separacao_lote_id

            if lote_id not in lotes_map:
                lotes_map[lote_id] = {
                    'separacao_lote_id': lote_id,
                    'expedicao': sep.expedicao.isoformat() if sep.expedicao else None,
                    'agendamento': sep.agendamento.isoformat() if sep.agendamento else None,
                    'protocolo': sep.protocolo,
                    'agendamento_confirmado': sep.agendamento_confirmado or False,
                    'qtd_itens': 0,
                    'valor_total': 0.0,
                    'pallet_total': 0.0,
                    'peso_total': 0.0
                }

            # Somar totais
            lotes_map[lote_id]['qtd_itens'] += 1
            lotes_map[lote_id]['valor_total'] += float(sep.valor_saldo or 0)
            lotes_map[lote_id]['pallet_total'] += float(sep.pallet or 0)
            lotes_map[lote_id]['peso_total'] += float(sep.peso or 0)

        # Converter para lista
        lotes_list = list(lotes_map.values())

        logger.info(f"Pedido {num_pedido} possui {len(lotes_list)} lote(s) de separação")

        return jsonify({
            'success': True,
            'tem_separacoes': True,
            'lotes': lotes_list
        })

    except Exception as e:
        logger.error(f"Erro ao verificar separações existentes: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@carteira_simples_bp.route('/api/rastrear-produto')
def rastrear_produto():
    """
    Retorna todas as separações não sincronizadas de um produto específico

    Query params:
    - cod_produto: string (required)

    Response:
    {
        "success": true,
        "separacoes": [
            {
                "separacao_lote_id": "SEP-2025-001",
                "raz_social_red": "Cliente XYZ",
                "qtd_saldo": 100.0,
                "expedicao": "2025-10-20",
                "valor_saldo": 5000.0,
                "status": "ABERTO",
                "status_calculado": "ABERTO"
            }
        ]
    }
    """
    try:
        cod_produto = request.args.get('cod_produto', '').strip()

        if not cod_produto:
            return jsonify({
                'success': False,
                'error': 'Parâmetro cod_produto é obrigatório'
            }), 400

        # Buscar TODAS as separações não sincronizadas deste produto
        separacoes = Separacao.query.filter_by(
            cod_produto=cod_produto,
            sincronizado_nf=False
        ).order_by(
            Separacao.expedicao.asc()
        ).all()

        # Formatar resposta
        separacoes_formatadas = []

        for sep in separacoes:
            separacoes_formatadas.append({
                'separacao_lote_id': sep.separacao_lote_id,
                'raz_social_red': sep.raz_social_red,
                'qtd_saldo': float(sep.qtd_saldo or 0),
                'expedicao': sep.expedicao.isoformat() if sep.expedicao else None,
                'valor_saldo': float(sep.valor_saldo or 0),
                'status': sep.status,
                'status_calculado': sep.status_calculado  # Propriedade calculada dinamicamente
            })

        logger.info(f"✅ Rastreamento produto {cod_produto}: {len(separacoes_formatadas)} separações encontradas")

        return jsonify({
            'success': True,
            'separacoes': separacoes_formatadas,
            'total': len(separacoes_formatadas)
        })

    except Exception as e:
        logger.error(f"Erro ao rastrear produto: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@carteira_simples_bp.route('/api/adicionar-itens-separacao', methods=['POST'])
def adicionar_itens_separacao():
    """
    Adiciona novos itens a uma separação existente

    Body JSON:
    {
        "separacao_lote_id": "SEP-2025-001",
        "num_pedido": "123456",
        "produtos": [
            {
                "cod_produto": "ABC123",
                "quantidade": 100
            }
        ]
    }
    """
    try:
        dados = request.get_json()

        if not dados or 'separacao_lote_id' not in dados or 'num_pedido' not in dados or 'produtos' not in dados:
            return jsonify({
                'success': False,
                'error': 'Dados inválidos. Esperado: {separacao_lote_id, num_pedido, produtos}'
            }), 400

        separacao_lote_id = dados['separacao_lote_id']
        num_pedido = dados['num_pedido']
        produtos = dados['produtos']

        if not produtos or len(produtos) == 0:
            return jsonify({
                'success': False,
                'error': 'Nenhum produto informado'
            }), 400

        # Buscar uma separação do lote para copiar os campos
        separacao_referencia = Separacao.query.filter_by(
            separacao_lote_id=separacao_lote_id
        ).first()

        if not separacao_referencia:
            return jsonify({
                'success': False,
                'error': f'Lote {separacao_lote_id} não encontrado'
            }), 404

        # Copiar campos da separação de referência
        expedicao = separacao_referencia.expedicao
        agendamento = separacao_referencia.agendamento
        protocolo = separacao_referencia.protocolo
        agendamento_confirmado = separacao_referencia.agendamento_confirmado

        itens_criados = []
        itens_atualizados = []

        for produto in produtos:
            cod_produto = produto['cod_produto']
            quantidade = float(produto['quantidade'])

            # Buscar item da carteira
            item_carteira = CarteiraPrincipal.query.filter_by(
                num_pedido=num_pedido,
                cod_produto=cod_produto,
                ativo=True
            ).first()

            if not item_carteira:
                logger.warning(f"Item {cod_produto} do pedido {num_pedido} não encontrado na carteira")
                continue

            # 🆕 VERIFICAR SE O PRODUTO JÁ EXISTE NA SEPARAÇÃO
            separacao_existente = Separacao.query.filter_by(
                separacao_lote_id=separacao_lote_id,
                num_pedido=num_pedido,
                cod_produto=cod_produto,
                sincronizado_nf=False
            ).first()

            if separacao_existente:
                # 🆕 PRODUTO JÁ EXISTE → SOMAR QUANTIDADES
                logger.info(f"🔄 Produto {cod_produto} já existe no lote {separacao_lote_id}, somando quantidades")

                qtd_anterior = float(separacao_existente.qtd_saldo or 0)
                qtd_nova = qtd_anterior + quantidade

                # Recalcular peso e pallet com a nova quantidade total
                peso_calculado, pallet_calculado = calcular_peso_pallet_produto(cod_produto, qtd_nova)

                # Recalcular valor com a nova quantidade total
                preco_unitario = float(item_carteira.preco_produto_pedido or 0)
                valor_calculado = qtd_nova * preco_unitario

                # Atualizar registro existente
                separacao_existente.qtd_saldo = qtd_nova
                separacao_existente.valor_saldo = valor_calculado
                separacao_existente.peso = peso_calculado
                separacao_existente.pallet = pallet_calculado

                itens_atualizados.append({
                    'cod_produto': cod_produto,
                    'quantidade_anterior': qtd_anterior,
                    'quantidade_adicionada': quantidade,
                    'quantidade_nova': qtd_nova,
                    'valor': valor_calculado
                })

                logger.info(f"✅ Produto {cod_produto}: {qtd_anterior} + {quantidade} = {qtd_nova}")

            else:
                # 🆕 PRODUTO NÃO EXISTE → CRIAR NOVO REGISTRO
                logger.info(f"➕ Produto {cod_produto} não existe no lote {separacao_lote_id}, criando novo registro")

                # Calcular peso e pallet
                peso_calculado, pallet_calculado = calcular_peso_pallet_produto(cod_produto, quantidade)

                # Calcular valor
                preco_unitario = float(item_carteira.preco_produto_pedido or 0)
                valor_calculado = quantidade * preco_unitario

                # Buscar rota e sub-rota
                # 🔧 CORREÇÃO: SEMPRE verificar incoterm FOB/RED PRIMEIRO
                if hasattr(item_carteira, 'incoterm') and item_carteira.incoterm in ['FOB', 'RED']:
                    rota = item_carteira.incoterm
                    sub_rota = None  # FOB/RED não tem sub-rota
                else:
                    rota = buscar_rota_por_uf(item_carteira.estado) if item_carteira.estado else None
                    sub_rota = buscar_sub_rota_por_uf_cidade(item_carteira.estado, item_carteira.municipio) \
                        if item_carteira.estado and item_carteira.municipio else None

                # Criar novo registro de Separacao
                # ✅ CORREÇÃO: Copiar status e cotacao_id da separação de referência
                nova_separacao = Separacao(
                    separacao_lote_id=separacao_lote_id,
                    num_pedido=num_pedido,
                    cod_produto=cod_produto,
                    nome_produto=item_carteira.nome_produto,
                    qtd_saldo=quantidade,
                    valor_saldo=valor_calculado,
                    peso=peso_calculado,
                    pallet=pallet_calculado,
                    cnpj_cpf=item_carteira.cnpj_cpf,
                    raz_social_red=item_carteira.raz_social_red,
                    nome_cidade=item_carteira.municipio,
                    cod_uf=item_carteira.estado,
                    rota=rota,
                    sub_rota=sub_rota,
                    data_pedido=item_carteira.data_pedido,
                    pedido_cliente=item_carteira.pedido_cliente,
                    # 🆕 COPIAR CAMPOS DA SEPARAÇÃO DE REFERÊNCIA
                    expedicao=expedicao,
                    agendamento=agendamento,
                    protocolo=protocolo,
                    agendamento_confirmado=agendamento_confirmado,
                    status=separacao_referencia.status,  # ✅ COPIAR STATUS
                    cotacao_id=separacao_referencia.cotacao_id,  # ✅ COPIAR COTACAO_ID
                    sincronizado_nf=False,
                    criado_em=agora_brasil()
                )

                db.session.add(nova_separacao)
                itens_criados.append({
                    'cod_produto': cod_produto,
                    'quantidade': quantidade,
                    'valor': valor_calculado
                })

        db.session.commit()

        # ✅ Buscar TODAS as separações do lote para retornar ao frontend
        separacoes_atualizadas = Separacao.query.filter_by(
            separacao_lote_id=separacao_lote_id
        ).all()

        separacoes_retorno = []
        produtos_afetados = set()

        # 🆕 Calcular estoque atual + programação para produtos afetados
        hoje = date.today()
        data_fim = hoje + timedelta(days=28)

        estoque_map = {}
        produtos_unicos = list(set([sep.cod_produto for sep in separacoes_atualizadas]))

        for cod_produto in produtos_unicos:
            estoque_atual = ServicoEstoqueSimples.calcular_estoque_atual(cod_produto)

            # ✅ USAR ServicoEstoqueSimples para buscar programação com UNIFICAÇÃO DE CÓDIGOS
            # IMPORTANTE: entrada_em_d_plus_1=False porque frontend já aplica D+1
            entradas_dict = ServicoEstoqueSimples.calcular_entradas_previstas(
                cod_produto,
                hoje,
                data_fim,
                entrada_em_d_plus_1=False  # Frontend aplica D+1, então backend não deve aplicar
            )

            # Converter Dict[date, float] → List[Dict[str, Any]] para frontend
            programacao = converter_entradas_para_frontend(entradas_dict)

            estoque_map[cod_produto] = {
                'estoque_atual': estoque_atual,
                'programacao': programacao
            }

        for sep in separacoes_atualizadas:
            estoque_info = estoque_map.get(sep.cod_produto, {'estoque_atual': 0, 'programacao': []})

            # ✅ Extrair últimos 10 dígitos do lote_id
            lote_id_completo = sep.separacao_lote_id or ''
            lote_id_ultimos_10 = lote_id_completo[-10:] if len(lote_id_completo) >= 10 else lote_id_completo

            separacoes_retorno.append({
                'id': sep.id,
                'separacao_lote_id': sep.separacao_lote_id,
                'num_pedido': sep.num_pedido,
                'cod_produto': sep.cod_produto,
                'nome_produto': sep.nome_produto,
                'qtd_saldo': float(sep.qtd_saldo),
                'valor_saldo': float(sep.valor_saldo or 0),
                'peso': float(sep.peso or 0),
                'pallet': float(sep.pallet or 0),
                'expedicao': sep.expedicao.isoformat() if sep.expedicao else None,
                'agendamento': sep.agendamento.isoformat() if sep.agendamento else None,
                'protocolo': sep.protocolo,
                'agendamento_confirmado': sep.agendamento_confirmado or False,
                'cnpj_cpf': sep.cnpj_cpf,
                'raz_social_red': sep.raz_social_red,
                'nome_cidade': sep.nome_cidade,
                'municipio': lote_id_ultimos_10,  # ✅ Últimos 10 dígitos do lote (padrão da tela)
                'estado': sep.cod_uf,  # ✅ UF no campo estado
                'cod_uf': sep.cod_uf,
                'rota': sep.rota,
                'sub_rota': sep.sub_rota,
                'data_pedido': sep.data_pedido.isoformat() if sep.data_pedido else None,
                'pedido_cliente': sep.pedido_cliente,
                'tipo': 'separacao',
                'status_calculado': sep.status or 'ABERTO',  # ✅ Status para cor amarela
                'estoque_atual': estoque_info['estoque_atual'],
                'programacao': estoque_info['programacao']
            })
            produtos_afetados.add(sep.cod_produto)

        # Montar mensagem descritiva
        total_operacoes = len(itens_criados) + len(itens_atualizados)
        mensagem_partes = []

        if len(itens_criados) > 0:
            mensagem_partes.append(f'{len(itens_criados)} item(ns) criado(s)')

        if len(itens_atualizados) > 0:
            mensagem_partes.append(f'{len(itens_atualizados)} item(ns) atualizado(s)')

        mensagem = f"{' e '.join(mensagem_partes)} na separação {separacao_lote_id}"

        logger.info(f"✅ {mensagem}")

        return jsonify({
            'success': True,
            'message': mensagem,
            'separacao_lote_id': separacao_lote_id,
            'qtd_itens_criados': len(itens_criados),
            'qtd_itens_atualizados': len(itens_atualizados),
            'total_operacoes': total_operacoes,
            'itens_criados': itens_criados,
            'itens_atualizados': itens_atualizados,
            'separacoes': separacoes_retorno,  # ✅ Dados completos
            'produtos_afetados': list(produtos_afetados)  # ✅ Para recalcular estoques
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao adicionar itens à separação: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@carteira_simples_bp.route('/api/totais-protocolo', methods=['GET'])
def totais_protocolo():
    """
    Buscar totais agregados de todas as separações com um protocolo específico

    Query params:
        protocolo (str): Protocolo para buscar totais

    Returns:
        JSON com valor_total, peso_total, pallet_total e qtd_separacoes
    """
    try:
        protocolo = request.args.get('protocolo', '').strip()

        if not protocolo:
            return jsonify({
                'erro': 'Protocolo não informado'
            }), 400

        # Buscar todas as separações com este protocolo (sincronizado_nf=False)
        separacoes = Separacao.query.filter(
            and_(
                Separacao.protocolo == protocolo,
                Separacao.sincronizado_nf == False  # Apenas separações não faturadas
            )
        ).all()

        if not separacoes:
            return jsonify({
                'protocolo': protocolo,
                'qtd_separacoes': 0,
                'valor_total': 0,
                'peso_total': 0,
                'pallet_total': 0,
                'mensagem': 'Nenhuma separação encontrada com este protocolo'
            })

        # Agregar totais
        valor_total = 0
        peso_total = 0
        pallet_total = 0

        for sep in separacoes:
            valor_total += float(sep.valor_saldo or 0)
            peso_total += float(sep.peso or 0)
            pallet_total += float(sep.pallet or 0)

        return jsonify({
            'protocolo': protocolo,
            'qtd_separacoes': len(separacoes),
            'valor_total': round(valor_total, 2),
            'peso_total': round(peso_total, 2),
            'pallet_total': round(pallet_total, 2)
        })

    except Exception as e:
        logger.error(f"Erro ao buscar totais do protocolo: {e}", exc_info=True)
        return jsonify({
            'erro': f'Erro ao buscar totais: {str(e)}'
        }), 500
