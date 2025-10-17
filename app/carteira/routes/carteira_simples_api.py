"""
API para Carteira de Pedidos Simplificada
Carteira compacta com edição inline e cálculos dinâmicos
"""

from flask import Blueprint, render_template, request, jsonify
from datetime import date, datetime, timedelta
from sqlalchemy import and_, or_, func
from decimal import Decimal
import logging

from app import db
from app.carteira.models import CarteiraPrincipal
from app.separacao.models import Separacao
from app.producao.models import CadastroPalletizacao
from app.estoque.services.estoque_simples import ServicoEstoqueSimples
from app.estoque.models import UnificacaoCodigos
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


@carteira_simples_bp.route('/')
def index():
    """Renderiza página da carteira simplificada"""
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
    try:
        # Parâmetros de filtro
        num_pedido = request.args.get('num_pedido', '').strip()
        cnpj_cpf = request.args.get('cnpj_cpf', '').strip()
        cod_produto = request.args.get('cod_produto', '').strip()
        data_pedido_de = request.args.get('data_pedido_de', '').strip()
        data_pedido_ate = request.args.get('data_pedido_ate', '').strip()
        data_entrega_de = request.args.get('data_entrega_de', '').strip()
        data_entrega_ate = request.args.get('data_entrega_ate', '').strip()
        estado = request.args.get('estado', '').strip()
        municipio = request.args.get('municipio', '').strip()
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))

        # Query base - apenas itens ativos
        query = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.ativo == True,
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        )

        # Aplicar filtros
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

        # Ordenação
        query = query.order_by(
            CarteiraPrincipal.data_pedido.desc(),
            CarteiraPrincipal.num_pedido.asc(),
            CarteiraPrincipal.cod_produto.asc()
        )

        # Total de registros
        total = query.count()

        # Paginação
        items = query.limit(limit).offset(offset).all()

        # Buscar dados de palletização (batch)
        codigos_produtos = [item.cod_produto for item in items]
        palletizacoes = db.session.query(CadastroPalletizacao).filter(
            CadastroPalletizacao.cod_produto.in_(codigos_produtos),
            CadastroPalletizacao.ativo == True
        ).all()

        # Criar mapa de palletização
        pallet_map = {p.cod_produto: p for p in palletizacoes}

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
        # Coletar produtos únicos com qtd_saldo > 0
        produtos_unicos = {}
        for item in items:
            qtd_separada = sep_map.get((item.num_pedido, item.cod_produto), 0)
            qtd_saldo = float(item.qtd_saldo_produto_pedido or 0) - qtd_separada

            if qtd_saldo > 0:
                if item.cod_produto not in produtos_unicos:
                    produtos_unicos[item.cod_produto] = {
                        'qtd_total_carteira': 0,
                        'expedicao': item.expedicao  # Usar primeira data de expedição encontrada
                    }
                produtos_unicos[item.cod_produto]['qtd_total_carteira'] += qtd_saldo

        # Calcular estoque para todos os produtos de uma vez
        estoque_map = {}
        try:
            for cod_produto, info in produtos_unicos.items():
                # Estoque atual
                estoque_atual = ServicoEstoqueSimples.calcular_estoque_atual(cod_produto)

                # Projeção de 28 dias (para navegação lateral)
                data_expedicao = info['expedicao'] or date.today()
                dias = max((data_expedicao - date.today()).days, 0) + 7  # Calcular até data + 7 dias

                projecao = ServicoEstoqueSimples.calcular_projecao(cod_produto, min(dias, 28))

                estoque_map[cod_produto] = {
                    'estoque_atual': estoque_atual,
                    'menor_estoque_d7': projecao.get('menor_estoque_d7', 0),
                    'projecoes': projecao.get('projecao', [])[:28]  # Limitar a 28 dias
                }
        except Exception as e:
            logger.error(f"Erro ao calcular estoques em batch: {e}", exc_info=True)

        # 🆕 BUSCAR SEPARAÇÕES NÃO SINCRONIZADAS (sincronizado_nf=False)
        # Obter lista de pedidos da página atual
        pedidos_da_pagina = [item.num_pedido for item in items]

        # Buscar separações não sincronizadas
        separacoes_query = db.session.query(Separacao).filter(
            and_(
                Separacao.num_pedido.in_(pedidos_da_pagina),
                Separacao.sincronizado_nf == False
            )
        ).order_by(
            Separacao.num_pedido,
            Separacao.separacao_lote_id,
            Separacao.id
        ).all()

        # 🆕 BUSCAR EMBARQUES E TRANSPORTADORAS (batch)
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

        # Montar resposta - ESTRUTURA HIERÁRQUICA PLANA
        dados = []

        # 🔧 CORREÇÃO: Agrupar separações por (num_pedido, cod_produto)
        separacoes_por_pedido_produto = {}
        for sep in separacoes_query:
            chave = (sep.num_pedido, sep.cod_produto)
            if chave not in separacoes_por_pedido_produto:
                separacoes_por_pedido_produto[chave] = []
            separacoes_por_pedido_produto[chave].append(sep)

        # Renderizar pedidos + separações hierarquicamente
        for item in items:
            # Calcular qtd_saldo (carteira - separações não sincronizadas)
            qtd_separada = sep_map.get((item.num_pedido, item.cod_produto), 0)
            qtd_saldo = float(item.qtd_saldo_produto_pedido or 0) - qtd_separada

            # Dados de palletização
            pallet_info = pallet_map.get(item.cod_produto)
            palletizacao = float(pallet_info.palletizacao) if pallet_info else 100.0
            peso_bruto = float(pallet_info.peso_bruto) if pallet_info else 1.0

            # Calcular valores
            preco_unitario = float(item.preco_produto_pedido or 0)
            valor_total = qtd_saldo * preco_unitario
            pallets = qtd_saldo / palletizacao if palletizacao > 0 else 0
            peso = qtd_saldo * peso_bruto

            # Buscar dados de estoque pré-calculados
            estoque_info = estoque_map.get(item.cod_produto, {
                'estoque_atual': 0,
                'menor_estoque_d7': 0,
                'projecoes': []
            })

            # ✅ LINHA DO PEDIDO
            dados.append({
                'tipo': 'pedido',  # 🆕 FLAG DE TIPO
                'id': item.id,
                'num_pedido': item.num_pedido,
                'pedido_cliente': item.pedido_cliente,
                'data_pedido': item.data_pedido.strftime('%Y-%m-%d') if item.data_pedido else None,
                'data_entrega_pedido': item.data_entrega_pedido.strftime('%Y-%m-%d') if item.data_entrega_pedido else None,
                'cnpj_cpf': item.cnpj_cpf,
                'raz_social_red': item.raz_social_red,
                'estado': item.estado,
                'municipio': item.municipio,
                'cod_produto': item.cod_produto,
                'nome_produto': item.nome_produto,
                'qtd_saldo': qtd_saldo,
                'qtd_carteira': float(item.qtd_saldo_produto_pedido or 0),
                'preco_produto_pedido': preco_unitario,
                'valor_total': valor_total,
                'pallets': pallets,
                'peso': peso,
                'rota': item.rota,
                'sub_rota': item.sub_rota,
                'expedicao': item.expedicao.strftime('%Y-%m-%d') if item.expedicao else None,
                'agendamento': item.agendamento.strftime('%Y-%m-%d') if item.agendamento else None,
                'protocolo': item.protocolo,
                'agendamento_confirmado': item.agendamento_confirmado,
                # Dados para cálculo de estoque
                'palletizacao': palletizacao,
                'peso_bruto': peso_bruto,
                # 🚀 ESTOQUE PRÉ-CALCULADO (1x por produto)
                'estoque_atual': estoque_info['estoque_atual'],
                'menor_estoque_d7': estoque_info['menor_estoque_d7'],
                'projecoes_estoque': estoque_info['projecoes']  # Array com 28 dias
            })

            # ✅ LINHAS DAS SEPARAÇÕES (se houver) - FILTRADAS POR PRODUTO
            chave_pedido_produto = (item.num_pedido, item.cod_produto)
            separacoes_do_item = separacoes_por_pedido_produto.get(chave_pedido_produto, [])

            for sep in separacoes_do_item:
                # Dados de palletização para separação
                pallet_info_sep = pallet_map.get(sep.cod_produto)
                palletizacao_sep = float(pallet_info_sep.palletizacao) if pallet_info_sep else 100.0
                peso_bruto_sep = float(pallet_info_sep.peso_bruto) if pallet_info_sep else 1.0

                # Buscar embarque + transportadora
                embarque_info = embarques_map.get(sep.separacao_lote_id, {})
                cliente_texto = ''
                if embarque_info:
                    cliente_texto = f"Embarque #{embarque_info['numero']} - {embarque_info['transportadora']}"

                # Calcular valores da separação
                qtd_sep = float(sep.qtd_saldo or 0)
                preco_sep = float(item.preco_produto_pedido or 0)  # Usar preço do pedido
                valor_sep = qtd_sep * preco_sep
                pallets_sep = qtd_sep / palletizacao_sep if palletizacao_sep > 0 else 0
                peso_sep = qtd_sep * peso_bruto_sep

                # Buscar estoque (mesmo do produto do pedido)
                estoque_info_sep = estoque_map.get(sep.cod_produto, {
                    'estoque_atual': 0,
                    'menor_estoque_d7': 0,
                    'projecoes': []
                })

                dados.append({
                    'tipo': 'separacao',  # 🆕 FLAG DE TIPO
                    'id': sep.id,
                    'separacao_id': sep.id,  # ID único da separação
                    'separacao_lote_id': sep.separacao_lote_id,
                    'num_pedido': sep.num_pedido,
                    'pedido_cliente': sep.pedido_cliente,
                    # 🆕 CAMPOS CUSTOMIZADOS PARA SEPARAÇÃO
                    'data_pedido': sep.criado_em.strftime('%Y-%m-%d') if sep.criado_em else None,  # criado_em
                    'data_entrega_pedido': item.data_entrega_pedido.strftime('%Y-%m-%d') if item.data_entrega_pedido else None,
                    'cnpj_cpf': sep.separacao_lote_id,  # separacao_lote_id na coluna CNPJ
                    'raz_social_red': cliente_texto,  # "Embarque #X - Transportadora"
                    'estado': item.estado,
                    'municipio': sep.status_calculado,  # status_calculado na coluna Município
                    'status_calculado': sep.status_calculado,  # Campo extra para cores
                    'cod_produto': sep.cod_produto,
                    'nome_produto': sep.nome_produto,
                    'qtd_saldo': qtd_sep,
                    'qtd_carteira': float(item.qtd_saldo_produto_pedido or 0),
                    'preco_produto_pedido': preco_sep,
                    'valor_total': valor_sep,
                    'pallets': pallets_sep,
                    'peso': peso_sep,
                    'rota': sep.rota,
                    'sub_rota': sep.sub_rota,
                    'expedicao': sep.expedicao.strftime('%Y-%m-%d') if sep.expedicao else None,
                    'agendamento': sep.agendamento.strftime('%Y-%m-%d') if sep.agendamento else None,
                    'protocolo': sep.protocolo,
                    'agendamento_confirmado': sep.agendamento_confirmado,
                    # Dados para cálculo de estoque
                    'palletizacao': palletizacao_sep,
                    'peso_bruto': peso_bruto_sep,
                    # 🚀 ESTOQUE PRÉ-CALCULADO (mesmo do produto)
                    'estoque_atual': estoque_info_sep['estoque_atual'],
                    'menor_estoque_d7': estoque_info_sep['menor_estoque_d7'],
                    'projecoes_estoque': estoque_info_sep['projecoes']
                })

        return jsonify({
            'success': True,
            'total': total,
            'limit': limit,
            'offset': offset,
            'dados': dados
        })

    except Exception as e:
        logger.error(f"Erro ao obter dados da carteira: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


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
        saidas = ServicoEstoqueSimples.calcular_saidas_previstas(cod_produto, hoje, data_fim)
        entradas = ServicoEstoqueSimples.calcular_entradas_previstas(cod_produto, hoje, data_fim)

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
                tipo_envio='total',  # Pode ser ajustado conforme lógica
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

        return jsonify({
            'success': True,
            'message': f'{len(separacoes_criadas)} separação(ões) criada(s) com sucesso',
            'separacao_lote_id': lote_id,
            'qtd_itens': len(separacoes_criadas)
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

        # Retornar dados atualizados
        return jsonify({
            'success': True,
            'message': 'Quantidade atualizada com sucesso',
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
    Confirma agendamento na CarteiraPrincipal

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

        # Buscar item na carteira
        item = CarteiraPrincipal.query.filter_by(
            num_pedido=num_pedido,
            cod_produto=cod_produto,
            ativo=True
        ).first()

        if not item:
            return jsonify({
                'success': False,
                'error': 'Item não encontrado na carteira'
            }), 404

        # Confirmar agendamento
        item.agendamento_confirmado = True
        item.protocolo = protocolo

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Agendamento confirmado com sucesso'
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao confirmar agendamento: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
