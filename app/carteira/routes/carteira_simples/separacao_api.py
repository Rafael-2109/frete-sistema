"""
Rotas de CRUD de Separacoes da Carteira Simplificada

- gerar_separacao: cria separacao com status='ABERTO'
- atualizar_qtd_separacao: atualiza qtd (se 0, deleta)
- atualizar_separacao_lote: atualiza campos do lote (expedicao, agendamento, protocolo)
- verificar_separacoes_existentes: verifica se pedido ja tem separacoes
- adicionar_itens_separacao: adiciona produtos a separacao existente
"""

from flask import request, jsonify
from datetime import date, datetime, timedelta
from sqlalchemy import and_, func
import logging

from app import db
from app.carteira.models import CarteiraPrincipal
from app.separacao.models import Separacao
from app.estoque.services.estoque_simples import ServicoEstoqueSimples
from app.carteira.utils.separacao_utils import (
    calcular_peso_pallet_produto,
    calcular_peso_pallet_com_map,
    carregar_pallet_map,
    buscar_rota_por_uf,
    buscar_sub_rota_por_uf_cidade,
)
from app.utils.lote_utils import gerar_lote_id
from app.utils.timezone import agora_utc_naive

from . import carteira_simples_bp
from .helpers import (
    atualizar_embarque_item_por_separacao,
)

logger = logging.getLogger(__name__)


def _calcular_estoque_separacoes(separacoes_lista):
    """
    Calcula estoque atual + programacao para produtos de uma lista de separacoes.
    Helper interno para evitar duplicacao entre gerar_separacao e adicionar_itens_separacao.

    OPT-B2: Usa calcular_estoque_batch (2 queries) em vez de loop individual (2N queries).

    Args:
        separacoes_lista: lista de objetos Separacao

    Returns:
        dict: {cod_produto: {'estoque_atual': float, 'programacao': list}}
    """
    hoje = date.today()
    data_fim = hoje + timedelta(days=28)

    produtos_unicos = list(set(sep.cod_produto for sep in separacoes_lista))

    if not produtos_unicos:
        return {}

    # Batch: 2 queries em vez de 2N
    estoque_map = ServicoEstoqueSimples.calcular_estoque_batch(
        codigos_produtos=produtos_unicos,
        data_fim=data_fim
    )

    return estoque_map


def _serializar_separacao_para_frontend(sep, estoque_map):
    """
    Serializa uma Separacao para o formato JSON esperado pelo frontend.
    Helper interno para evitar duplicacao.

    Args:
        sep: objeto Separacao
        estoque_map: dict com estoque por cod_produto

    Returns:
        dict com dados da separacao formatados
    """
    estoque_info = estoque_map.get(sep.cod_produto, {'estoque_atual': 0, 'programacao': []})

    # Extrair ultimos 10 digitos do lote_id
    lote_id_completo = sep.separacao_lote_id or ''
    lote_id_ultimos_10 = lote_id_completo[-10:] if len(lote_id_completo) >= 10 else lote_id_completo

    return {
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
        'municipio': lote_id_ultimos_10,
        'estado': sep.cod_uf,
        'cod_uf': sep.cod_uf,
        'rota': sep.rota,
        'sub_rota': sep.sub_rota,
        'data_pedido': sep.data_pedido.isoformat() if sep.data_pedido else None,
        'pedido_cliente': sep.pedido_cliente,
        'tipo': 'separacao',
        'status_calculado': sep.status_calculado,
        'estoque_atual': estoque_info['estoque_atual'],
        'programacao': estoque_info['programacao']
    }


@carteira_simples_bp.route('/api/gerar-separacao', methods=['POST'])
def gerar_separacao():
    """
    Gera separacao (Separacao) com status='ABERTO'

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
                'error': 'Dados invalidos. Esperado: {num_pedido, produtos}'
            }), 400

        num_pedido = dados['num_pedido']
        produtos = dados['produtos']

        if not produtos or not isinstance(produtos, list):
            return jsonify({
                'success': False,
                'error': 'Lista de produtos vazia ou invalida'
            }), 400

        # Gerar lote_id unico
        lote_id = gerar_lote_id()

        # Determinar tipo_envio CORRETAMENTE: verificar se esta separando TODOS os produtos
        from app.carteira.utils.separacao_utils import determinar_tipo_envio

        # Buscar produtos na carteira para validacao
        produtos_carteira = {}
        for item in CarteiraPrincipal.query.filter_by(num_pedido=num_pedido, ativo=True).all():
            produtos_carteira[item.cod_produto] = item

        tipo_envio_correto = determinar_tipo_envio(num_pedido, produtos, produtos_carteira)
        logger.info(f"tipo_envio determinado: {tipo_envio_correto} para pedido {num_pedido}")

        logger.info(f"Recebidos {len(produtos)} produtos para pedido {num_pedido}: {[p.get('cod_produto') for p in produtos]}")

        separacoes_criadas = []
        itens_rejeitados = []

        # OPT-B4: Pre-fetch batch de qtd ja separada (1 query em vez de N)
        cod_list = [p.get('cod_produto') for p in produtos if p.get('cod_produto')]
        sep_totals = db.session.query(
            Separacao.cod_produto,
            func.sum(Separacao.qtd_saldo).label('total')
        ).filter(
            and_(
                Separacao.num_pedido == num_pedido,
                Separacao.cod_produto.in_(cod_list),
                Separacao.sincronizado_nf == False
            )
        ).group_by(Separacao.cod_produto).all()
        sep_map = {r.cod_produto: float(r.total or 0) for r in sep_totals}

        # OPT-B5: Pre-carregar palletizacao em batch (1 query em vez de N)
        pallet_map = carregar_pallet_map(cod_list)

        for produto in produtos:
            cod_produto = produto.get('cod_produto')
            quantidade = float(produto.get('quantidade', 0))
            expedicao_str = produto.get('expedicao', '')
            agendamento_str = produto.get('agendamento', '')
            protocolo = produto.get('protocolo', '')

            if not cod_produto or quantidade <= 0:
                logger.warning(f"Produto ignorado (dados invalidos): cod={cod_produto}, qtd={quantidade}")
                itens_rejeitados.append({
                    'cod_produto': cod_produto or 'VAZIO',
                    'motivo': 'Quantidade invalida ou codigo vazio'
                })
                continue

            # OPT-B3: Usar dict ja carregado em vez de query individual
            item_carteira = produtos_carteira.get(cod_produto)

            if not item_carteira:
                logger.warning(f"Item nao encontrado na carteira: {num_pedido}/{cod_produto}")
                itens_rejeitados.append({
                    'cod_produto': cod_produto,
                    'motivo': 'Item nao encontrado na carteira (ativo=False ou nao existe)'
                })
                continue

            # OPT-B4: Usar mapa pre-calculado em vez de query individual
            qtd_separada = sep_map.get(cod_produto, 0)

            qtd_disponivel = float(item_carteira.qtd_saldo_produto_pedido or 0) - float(qtd_separada)

            if quantidade > qtd_disponivel:
                return jsonify({
                    'success': False,
                    'error': f'Quantidade indisponivel para {cod_produto}. Disponivel: {qtd_disponivel:.2f}'
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

            # OPT-B5: Usar mapa pre-carregado em vez de query individual
            peso_calculado, pallet_calculado = calcular_peso_pallet_com_map(cod_produto, quantidade, pallet_map)

            # Buscar rota
            if hasattr(item_carteira, 'incoterm') and item_carteira.incoterm in ["RED", "FOB"]:
                rota_calculada = item_carteira.incoterm
            else:
                rota_calculada = buscar_rota_por_uf(item_carteira.cod_uf or 'SP')

            sub_rota_calculada = buscar_sub_rota_por_uf_cidade(
                item_carteira.cod_uf or '',
                item_carteira.nome_cidade or ''
            )

            # Criar separacao
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
                tipo_envio=tipo_envio_correto,
                status='ABERTO',
                sincronizado_nf=False,
                criado_em=agora_utc_naive()
            )

            db.session.add(separacao)
            separacoes_criadas.append(separacao)

        if not separacoes_criadas:
            return jsonify({
                'success': False,
                'error': 'Nenhuma separacao foi criada'
            }), 400

        db.session.commit()

        # Preparar dados das separacoes criadas para o frontend
        estoque_map = _calcular_estoque_separacoes(separacoes_criadas)
        produtos_afetados = set()

        separacoes_retorno = []
        for sep in separacoes_criadas:
            separacoes_retorno.append(_serializar_separacao_para_frontend(sep, estoque_map))
            produtos_afetados.add(sep.cod_produto)

        logger.info(f"Lote {lote_id}: {len(separacoes_criadas)} separacao(oes) criada(s)")

        if itens_rejeitados:
            logger.warning(f"{len(itens_rejeitados)} item(ns) rejeitado(s) para pedido {num_pedido}: {itens_rejeitados}")

        return jsonify({
            'success': True,
            'message': f'{len(separacoes_criadas)} separacao(oes) criada(s) com sucesso',
            'separacao_lote_id': lote_id,
            'qtd_itens': len(separacoes_criadas),
            'separacoes': separacoes_retorno,
            'produtos_afetados': list(produtos_afetados),
            'itens_rejeitados': itens_rejeitados
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao gerar separacao: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@carteira_simples_bp.route('/api/atualizar-qtd-separacao', methods=['POST'])
def atualizar_qtd_separacao():
    """
    Atualiza quantidade de uma separacao em tempo real

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
                'error': 'Dados invalidos. Esperado: {separacao_id, nova_qtd}'
            }), 400

        if dados['separacao_id'] is None or dados['nova_qtd'] is None:
            return jsonify({
                'success': False,
                'error': 'separacao_id e nova_qtd nao podem ser nulos'
            }), 400

        try:
            separacao_id = int(dados['separacao_id'])
            nova_qtd = float(dados['nova_qtd'])
        except (ValueError, TypeError):
            return jsonify({
                'success': False,
                'error': 'separacao_id deve ser inteiro e nova_qtd deve ser numerico'
            }), 400

        if nova_qtd < 0:
            return jsonify({
                'success': False,
                'error': 'Quantidade deve ser maior ou igual a zero'
            }), 400

        # Buscar separacao
        separacao = db.session.get(Separacao, separacao_id) if separacao_id else None

        if not separacao:
            return jsonify({
                'success': False,
                'error': 'Separacao nao encontrada'
            }), 404

        # Buscar item da carteira para validacao
        item_carteira = CarteiraPrincipal.query.filter_by(
            num_pedido=separacao.num_pedido,
            cod_produto=separacao.cod_produto,
            ativo=True
        ).first()

        if not item_carteira:
            return jsonify({
                'success': False,
                'error': 'Item nao encontrado na carteira'
            }), 404

        # Calcular total ja separado (excluindo esta separacao)
        total_separado = db.session.query(
            func.sum(Separacao.qtd_saldo)
        ).filter(
            and_(
                Separacao.num_pedido == separacao.num_pedido,
                Separacao.cod_produto == separacao.cod_produto,
                Separacao.sincronizado_nf == False,
                Separacao.id != separacao_id
            )
        ).scalar() or 0

        # Validar se nova quantidade nao excede disponivel
        qtd_disponivel = float(item_carteira.qtd_saldo_produto_pedido or 0) - float(total_separado)

        if nova_qtd > qtd_disponivel:
            return jsonify({
                'success': False,
                'error': f'Quantidade indisponivel. Disponivel: {qtd_disponivel:.2f}'
            }), 400

        # SE NOVA QTD = 0 -> DELETAR SEPARACAO DO BANCO DE DADOS
        if nova_qtd == 0:
            logger.info(f"Deletando separacao ID={separacao_id} (qtd=0)")

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

            # ATUALIZAR EmbarqueItem se esta separacao estiver embarcada
            atualizar_embarque_item_por_separacao(separacao_lote_id_deletado)

            logger.info(f"Separacao ID={separacao_id} deletada com sucesso")

            # Retornar resposta indicando delecao
            return jsonify({
                'success': True,
                'message': 'Separacao deletada com sucesso (qtd=0)',
                'deletado': True,
                'separacao': separacao_deletada
            })

        # SE QTD > 0 -> ATUALIZAR QUANTIDADE (comportamento original)
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

        # ATUALIZAR EmbarqueItem se esta separacao estiver embarcada
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
            # Retornar qtd disponivel no pedido atualizada
            'qtd_disponivel_pedido': qtd_disponivel - nova_qtd
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao atualizar quantidade separacao: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@carteira_simples_bp.route('/api/atualizar-separacao-lote', methods=['POST'])
def atualizar_separacao_lote():
    """
    Atualiza campos de TODAS as separacoes de um lote

    Body JSON:
    {
        "separacao_lote_id": "ABC123",
        "expedicao": "2025-01-20",
        "agendamento": "2025-01-19",
        "protocolo": "PROT123",
        "agendamento_confirmado": true/false
    }
    """
    try:
        dados = request.get_json()

        if not dados or 'separacao_lote_id' not in dados:
            return jsonify({
                'success': False,
                'error': 'Dados invalidos. Esperado: {separacao_lote_id, [expedicao|agendamento|protocolo]}'
            }), 400

        separacao_lote_id = dados['separacao_lote_id']

        # Campos permitidos para atualizacao
        campos_atualizaveis = {}

        # Processar expedicao
        if 'expedicao' in dados:
            try:
                campos_atualizaveis['expedicao'] = datetime.strptime(dados['expedicao'], '%Y-%m-%d').date() if dados['expedicao'] else None
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'error': 'Data de expedicao invalida. Use formato YYYY-MM-DD'
                }), 400

        # Processar agendamento
        if 'agendamento' in dados:
            try:
                campos_atualizaveis['agendamento'] = datetime.strptime(dados['agendamento'], '%Y-%m-%d').date() if dados['agendamento'] else None
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'error': 'Data de agendamento invalida. Use formato YYYY-MM-DD'
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
                'error': 'Nenhum campo valido para atualizar. Use: expedicao, agendamento, protocolo ou agendamento_confirmado'
            }), 400

        # OPT-B9: Bulk UPDATE (1 query em vez de N updates individuais).
        # SEGURO para expedicao/agendamento/protocolo/agendamento_confirmado:
        # event listeners de Separacao sao no-op para esses campos
        # (nao afetam status_calculado, peso, valor nem embarque).
        # CUIDADO: Se futuro campo afetando status for adicionado, revisar este bulk.
        qtd_atualizada = Separacao.query.filter_by(
            separacao_lote_id=separacao_lote_id
        ).update(campos_atualizaveis, synchronize_session='fetch')

        if qtd_atualizada == 0:
            return jsonify({
                'success': False,
                'error': 'Nenhuma separacao encontrada para este lote'
            }), 404

        db.session.commit()

        # Buscar separacoes para recalculo de estoque (se necessario)
        separacoes_lote = Separacao.query.filter_by(
            separacao_lote_id=separacao_lote_id
        ).all()

        # RECALCULAR ESTOQUE PROJETADO (apenas se alterou expedicao)
        estoque_atualizado = {}
        if 'expedicao' in campos_atualizaveis:
            # Obter codigos de produtos afetados (unicos)
            codigos_afetados = list(set(sep.cod_produto for sep in separacoes_lote))

            # OPT-B8: Batch em vez de loop individual (2 queries em vez de 3N)
            try:
                hoje = date.today()
                data_fim = hoje + timedelta(days=28)
                batch_result = ServicoEstoqueSimples.calcular_estoque_batch(
                    codigos_produtos=codigos_afetados,
                    data_fim=data_fim
                )
                for cod_produto, info in batch_result.items():
                    estoque_atualizado[cod_produto] = {
                        'estoque_atual': info.get('estoque_atual', 0),
                        'menor_estoque_d7': 0,  # Frontend recalcula localmente
                        'projecoes': []  # Frontend recalcula localmente
                    }
            except Exception as e:
                logger.error(f"Erro ao recalcular estoque batch: {e}")

        campos_atualizados = ', '.join(campos_atualizaveis.keys())
        logger.info(f"Lote {separacao_lote_id}: {len(separacoes_lote)} separacao(oes) atualizada(s) - Campos: {campos_atualizados}")

        # SINCRONIZAR com EmbarqueItem (se existir) quando campos de agendamento foram alterados
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
                        logger.info(f"[SINCRONIZACAO] Tabelas atualizadas: {', '.join(tabelas_sincronizadas)}")
            except Exception as sync_error:
                logger.warning(f"Aviso na sincronizacao: {sync_error}")

        return jsonify({
            'success': True,
            'message': f'{len(separacoes_lote)} separacao(oes) atualizada(s) com sucesso ({campos_atualizados})',
            'qtd_atualizada': len(separacoes_lote),
            'separacao_lote_id': separacao_lote_id,
            'campos_atualizados': list(campos_atualizaveis.keys()),
            'estoque_atualizado': estoque_atualizado if estoque_atualizado else None,
            'tabelas_sincronizadas': tabelas_sincronizadas
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao atualizar separacao em lote: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@carteira_simples_bp.route('/api/verificar-separacoes-existentes', methods=['POST'])
def verificar_separacoes_existentes():
    """
    Verifica se um pedido ja possui separacoes nao sincronizadas
    e retorna os lotes agrupados com totais

    Body JSON:
    {
        "num_pedido": "123456"
    }
    """
    try:
        dados = request.get_json()

        if not dados or 'num_pedido' not in dados:
            return jsonify({
                'success': False,
                'error': 'Dados invalidos. Esperado: {num_pedido}'
            }), 400

        num_pedido = dados['num_pedido']

        # Buscar separacoes nao sincronizadas do pedido
        separacoes_pedido = db.session.query(Separacao).filter(
            and_(
                Separacao.num_pedido == num_pedido,
                Separacao.sincronizado_nf == False
            )
        ).all()

        if not separacoes_pedido or len(separacoes_pedido) == 0:
            return jsonify({
                'success': True,
                'tem_separacoes': False,
                'lotes': []
            })

        # Agrupar por separacao_lote_id e calcular totais
        lotes_map = {}

        for sep in separacoes_pedido:
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

        logger.info(f"Pedido {num_pedido} possui {len(lotes_list)} lote(s) de separacao")

        return jsonify({
            'success': True,
            'tem_separacoes': True,
            'lotes': lotes_list
        })

    except Exception as e:
        logger.error(f"Erro ao verificar separacoes existentes: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@carteira_simples_bp.route('/api/adicionar-itens-separacao', methods=['POST'])
def adicionar_itens_separacao():
    """
    Adiciona novos itens a uma separacao existente

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
                'error': 'Dados invalidos. Esperado: {separacao_lote_id, num_pedido, produtos}'
            }), 400

        separacao_lote_id = dados['separacao_lote_id']
        num_pedido = dados['num_pedido']
        produtos = dados['produtos']

        if not produtos or len(produtos) == 0:
            return jsonify({
                'success': False,
                'error': 'Nenhum produto informado'
            }), 400

        # Buscar uma separacao do lote para copiar os campos
        separacao_referencia = Separacao.query.filter_by(
            separacao_lote_id=separacao_lote_id
        ).first()

        if not separacao_referencia:
            return jsonify({
                'success': False,
                'error': f'Lote {separacao_lote_id} nao encontrado'
            }), 404

        # Copiar campos da separacao de referencia
        expedicao = separacao_referencia.expedicao
        agendamento = separacao_referencia.agendamento
        protocolo = separacao_referencia.protocolo
        agendamento_confirmado = separacao_referencia.agendamento_confirmado

        itens_criados = []
        itens_atualizados = []

        # OPT-B5: Pre-carregar palletizacao e carteira em batch
        cod_list_add = [p['cod_produto'] for p in produtos if p.get('cod_produto')]
        pallet_map_add = carregar_pallet_map(cod_list_add)
        produtos_carteira_add = {}
        for item in CarteiraPrincipal.query.filter_by(num_pedido=num_pedido, ativo=True).all():
            produtos_carteira_add[item.cod_produto] = item

        for produto in produtos:
            cod_produto = produto['cod_produto']
            quantidade = float(produto['quantidade'])

            # OPT-B3: Usar dict pre-carregado em vez de query individual
            item_carteira = produtos_carteira_add.get(cod_produto)

            if not item_carteira:
                logger.warning(f"Item {cod_produto} do pedido {num_pedido} nao encontrado na carteira")
                continue

            # VERIFICAR SE O PRODUTO JA EXISTE NA SEPARACAO
            separacao_existente = Separacao.query.filter_by(
                separacao_lote_id=separacao_lote_id,
                num_pedido=num_pedido,
                cod_produto=cod_produto,
                sincronizado_nf=False
            ).first()

            if separacao_existente:
                # PRODUTO JA EXISTE -> SOMAR QUANTIDADES
                logger.info(f"Produto {cod_produto} ja existe no lote {separacao_lote_id}, somando quantidades")

                qtd_anterior = float(separacao_existente.qtd_saldo or 0)
                qtd_nova = qtd_anterior + quantidade

                # OPT-B5: Usar mapa pre-carregado
                peso_calculado, pallet_calculado = calcular_peso_pallet_com_map(cod_produto, qtd_nova, pallet_map_add)

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

                logger.info(f"Produto {cod_produto}: {qtd_anterior} + {quantidade} = {qtd_nova}")

            else:
                # PRODUTO NAO EXISTE -> CRIAR NOVO REGISTRO
                logger.info(f"Produto {cod_produto} nao existe no lote {separacao_lote_id}, criando novo registro")

                # OPT-B5: Usar mapa pre-carregado
                peso_calculado, pallet_calculado = calcular_peso_pallet_com_map(cod_produto, quantidade, pallet_map_add)

                # Calcular valor
                preco_unitario = float(item_carteira.preco_produto_pedido or 0)
                valor_calculado = quantidade * preco_unitario

                # Buscar rota e sub-rota
                if hasattr(item_carteira, 'incoterm') and item_carteira.incoterm in ['FOB', 'RED']:
                    rota_calc = item_carteira.incoterm
                    sub_rota_calc = None
                else:
                    rota_calc = buscar_rota_por_uf(item_carteira.cod_uf or 'SP')
                    sub_rota_calc = buscar_sub_rota_por_uf_cidade(
                        item_carteira.cod_uf or '',
                        item_carteira.nome_cidade or ''
                    )

                # Criar novo registro de Separacao
                # Copiar status e cotacao_id da separacao de referencia
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
                    nome_cidade=item_carteira.nome_cidade,
                    cod_uf=item_carteira.cod_uf,
                    rota=rota_calc,
                    sub_rota=sub_rota_calc,
                    data_pedido=item_carteira.data_pedido,
                    pedido_cliente=item_carteira.pedido_cliente,
                    # COPIAR CAMPOS DA SEPARACAO DE REFERENCIA
                    expedicao=expedicao,
                    agendamento=agendamento,
                    protocolo=protocolo,
                    agendamento_confirmado=agendamento_confirmado,
                    status=separacao_referencia.status,
                    cotacao_id=separacao_referencia.cotacao_id,
                    sincronizado_nf=False,
                    criado_em=agora_utc_naive()
                )

                db.session.add(nova_separacao)
                itens_criados.append({
                    'cod_produto': cod_produto,
                    'quantidade': quantidade,
                    'valor': valor_calculado
                })

        db.session.commit()

        # Buscar TODAS as separacoes do lote para retornar ao frontend
        separacoes_atualizadas = Separacao.query.filter_by(
            separacao_lote_id=separacao_lote_id
        ).all()

        estoque_map = _calcular_estoque_separacoes(separacoes_atualizadas)
        produtos_afetados = set()

        separacoes_retorno = []
        for sep in separacoes_atualizadas:
            separacoes_retorno.append(_serializar_separacao_para_frontend(sep, estoque_map))
            produtos_afetados.add(sep.cod_produto)

        # Montar mensagem descritiva
        total_operacoes = len(itens_criados) + len(itens_atualizados)
        mensagem_partes = []

        if len(itens_criados) > 0:
            mensagem_partes.append(f'{len(itens_criados)} item(ns) criado(s)')

        if len(itens_atualizados) > 0:
            mensagem_partes.append(f'{len(itens_atualizados)} item(ns) atualizado(s)')

        mensagem = f"{' e '.join(mensagem_partes)} na separacao {separacao_lote_id}"

        logger.info(f"{mensagem}")

        return jsonify({
            'success': True,
            'message': mensagem,
            'separacao_lote_id': separacao_lote_id,
            'qtd_itens_criados': len(itens_criados),
            'qtd_itens_atualizados': len(itens_atualizados),
            'total_operacoes': total_operacoes,
            'itens_criados': itens_criados,
            'itens_atualizados': itens_atualizados,
            'separacoes': separacoes_retorno,
            'produtos_afetados': list(produtos_afetados)
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao adicionar itens a separacao: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
