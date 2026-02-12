"""
Worker novo para processamento de ruptura em lotes
Trabalha em conjunto com o sistema existente
"""

from app import create_app, db
from app.carteira.models import CarteiraPrincipal
from app.producao.models import ProgramacaoProducao
from app.estoque.services.estoque_simples import ServicoEstoqueSimples
from app.utils.timezone import agora_utc_naive
from sqlalchemy import func
from datetime import datetime
import logging
import json
import redis
import os
import time

logger = logging.getLogger(__name__)

# Conectar ao Redis
redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
redis_conn = redis.from_url(redis_url)

# TTL para resultados = 15 segundos
RESULTADO_TTL = 15


def processar_lote_com_publicacao(pedidos, session_id, worker_id, lote_index):
    """
    Processa lote de pedidos e salva resultados no Redis
    
    Args:
        pedidos: Lista de números de pedidos
        session_id: ID da sessão para agrupar resultados
        worker_id: ID do worker (1 ou 2)
        lote_index: Índice do lote sendo processado
    """
    app = create_app()
    with app.app_context():
        logger.info(f"🔧 Worker {worker_id} processando lote {lote_index} com {len(pedidos)} pedidos")
        
        resultados_acumulados = []
        contador = 0
        
        for i, num_pedido in enumerate(pedidos):
            try:
                # Processar pedido individual
                resultado = analisar_pedido_individual(num_pedido)
                
                # Adicionar metadados
                resultado['worker_id'] = worker_id
                resultado['lote_index'] = lote_index
                resultado['processado_em'] = agora_utc_naive().isoformat()
                
                # Acumular resultado
                resultados_acumulados.append(resultado)
                contador += 1
                
                # Salvar resultado individual no Redis imediatamente
                # Usar índice global único baseado no lote e posição
                indice_global = lote_index * 1000 + i  # Garante ordem única
                chave_resultado = f'ruptura:resultado:{session_id}:{indice_global:06d}'
                
                redis_conn.setex(
                    chave_resultado,
                    300,  # 5 minutos para resultados individuais
                    json.dumps(resultado)
                )
                
                # A cada 20 pedidos, publicar evento de atualização
                if contador % 20 == 0 or i == len(pedidos) - 1:
                    publicar_atualizacao(session_id, worker_id, resultados_acumulados, lote_index)
                    logger.info(f"  Worker {worker_id}: {contador}/{len(pedidos)} processados")
                    resultados_acumulados = []  # Limpar buffer
                    
            except Exception as e:
                logger.error(f"Erro ao processar pedido {num_pedido}: {e}")
                # Salvar erro como resultado
                resultado_erro = {
                    'num_pedido': num_pedido,
                    'success': False,
                    'error': str(e),
                    'worker_id': worker_id,
                    'lote_index': lote_index
                }
                
                indice_global = lote_index * 1000 + i
                chave_resultado = f'ruptura:resultado:{session_id}:{indice_global:06d}'
                redis_conn.setex(chave_resultado, 300, json.dumps(resultado_erro))
        
        # Publicar qualquer resultado restante
        if resultados_acumulados:
            publicar_atualizacao(session_id, worker_id, resultados_acumulados, lote_index)
        
        logger.info(f"✅ Worker {worker_id} completou lote {lote_index}")
        
        # Marcar lote como completo
        redis_conn.setex(
            f'ruptura:lote:{session_id}:{lote_index}:completo',
            60,  # 1 minuto
            json.dumps({
                'worker_id': worker_id,
                'total_processados': len(pedidos),
                'timestamp': agora_utc_naive().isoformat()
            })
        )
        
        return {
            'success': True,
            'worker_id': worker_id,
            'lote_index': lote_index,
            'total_processados': len(pedidos)
        }


def analisar_pedido_individual(num_pedido):
    """
    Analisa ruptura de um pedido individual
    Reutiliza lógica do sistema existente
    """
    try:
        inicio = time.time()
        
        # Buscar itens do pedido
        itens = db.session.query(
            CarteiraPrincipal.cod_produto,
            CarteiraPrincipal.nome_produto,
            CarteiraPrincipal.qtd_saldo_produto_pedido,
            CarteiraPrincipal.preco_produto_pedido
        ).filter(
            CarteiraPrincipal.num_pedido == num_pedido,
            CarteiraPrincipal.ativo == True
        ).all()
        
        if not itens:
            return {
                'success': False,
                'num_pedido': num_pedido,
                'message': 'Pedido não encontrado'
            }
        
        # Buscar produtos únicos
        produtos_unicos = list(set([item.cod_produto for item in itens]))
        
        # Buscar produções futuras
        producoes_por_produto = {}
        if produtos_unicos:
            producoes = db.session.query(
                ProgramacaoProducao.cod_produto,
                ProgramacaoProducao.data_programacao,
                func.sum(ProgramacaoProducao.qtd_programada).label('qtd_producao')
            ).filter(
                ProgramacaoProducao.cod_produto.in_(produtos_unicos),
                ProgramacaoProducao.data_programacao >= agora_utc_naive().date()
            ).group_by(
                ProgramacaoProducao.cod_produto,
                ProgramacaoProducao.data_programacao
            ).all()
            
            for prod in producoes:
                if prod.cod_produto not in producoes_por_produto:
                    producoes_por_produto[prod.cod_produto] = []
                producoes_por_produto[prod.cod_produto].append({
                    'data': prod.data_programacao,
                    'qtd': float(prod.qtd_producao)
                })
        
        # Calcular projeções de estoque
        projecoes_produtos = {}
        for cod_produto in produtos_unicos:
            try:
                projecoes_produtos[cod_produto] = ServicoEstoqueSimples.get_projecao_completa(
                    cod_produto, 
                    dias=7
                )
            except Exception as e:
                logger.warning(f"Erro ao projetar {cod_produto}: {e}")
                projecoes_produtos[cod_produto] = {'menor_estoque_d7': 0}
        
        # Analisar ruptura
        itens_com_ruptura = []
        itens_disponiveis = []
        valor_total_pedido = 0
        valor_com_ruptura = 0
        tem_item_sem_producao = False
        datas_producao_ruptura = []
        
        for item in itens:
            valor_item = float(item.qtd_saldo_produto_pedido * (item.preco_produto_pedido or 0))
            valor_total_pedido += valor_item
            
            projecao = projecoes_produtos.get(item.cod_produto, {})
            estoque_d7 = float(projecao.get('menor_estoque_d7', 0))
            qtd_saldo = float(item.qtd_saldo_produto_pedido)
            
            if qtd_saldo > estoque_d7:
                # Item com ruptura
                ruptura = qtd_saldo - estoque_d7
                valor_com_ruptura += valor_item
                
                producoes_futuras = producoes_por_produto.get(item.cod_produto, [])
                
                # Calcular quando terá estoque
                data_disponivel = None
                qtd_acumulada = estoque_d7
                primeira_producao = producoes_futuras[0] if producoes_futuras else None
                
                if producoes_futuras:
                    for prod in producoes_futuras:
                        qtd_acumulada += prod['qtd']
                        if qtd_acumulada >= qtd_saldo:
                            data_disponivel = prod['data']
                            break
                    
                    if data_disponivel:
                        datas_producao_ruptura.append(data_disponivel)
                else:
                    tem_item_sem_producao = True
                
                itens_com_ruptura.append({
                    'cod_produto': item.cod_produto,
                    'nome_produto': item.nome_produto,
                    'qtd_saldo': int(qtd_saldo),
                    'estoque_min_d7': int(estoque_d7),
                    'ruptura_qtd': int(ruptura),
                    'data_producao': primeira_producao['data'].isoformat() if primeira_producao else None,
                    'qtd_producao': int(primeira_producao['qtd']) if primeira_producao else 0,
                    'data_disponivel': data_disponivel.isoformat() if data_disponivel else None
                })
            else:
                # Item disponível
                itens_disponiveis.append({
                    'cod_produto': item.cod_produto,
                    'nome_produto': item.nome_produto,
                    'qtd_saldo': int(qtd_saldo),
                    'estoque_min_d7': int(estoque_d7)
                })
        
        tempo_processamento = (time.time() - inicio) * 1000
        
        # Se não há ruptura
        if not itens_com_ruptura:
            return {
                'success': True,
                'pedido_ok': True,
                'num_pedido': num_pedido,
                'percentual_disponibilidade': 100,
                'data_disponibilidade_total': 'agora',
                'message': 'Pedido OK - Todos os itens disponíveis',
                'performance_ms': tempo_processamento
            }
        
        # Calcular métricas
        percentual_ruptura = (valor_com_ruptura / valor_total_pedido * 100) if valor_total_pedido > 0 else 0
        percentual_disponibilidade = 100 - percentual_ruptura
        qtd_itens_ruptura = len(itens_com_ruptura)
        qtd_itens_disponiveis = len(itens_disponiveis)
        total_itens = len(itens)
        
        # Determinar data de disponibilidade total
        if tem_item_sem_producao:
            data_disponibilidade_total = None
        elif datas_producao_ruptura:
            data_disponibilidade_total = max(datas_producao_ruptura).isoformat()
        else:
            data_disponibilidade_total = None
        
        # Determinar criticidade
        if qtd_itens_ruptura > 3 and percentual_ruptura > 10:
            criticidade = 'CRITICA'
        elif qtd_itens_ruptura <= 3 and percentual_ruptura <= 10:
            criticidade = 'ALTA'
        elif qtd_itens_ruptura <= 2 and percentual_ruptura <= 5:
            criticidade = 'MEDIA'
        else:
            criticidade = 'BAIXA'
        
        return {
            'success': True,
            'pedido_ok': False,
            'num_pedido': num_pedido,
            'percentual_disponibilidade': round(percentual_disponibilidade, 0),
            'data_disponibilidade_total': data_disponibilidade_total,
            'resumo': {
                'num_pedido': num_pedido,
                'percentual_ruptura': round(percentual_ruptura, 2),
                'percentual_disponibilidade': round(percentual_disponibilidade, 0),
                'percentual_itens_disponiveis': round((qtd_itens_disponiveis / total_itens * 100) if total_itens > 0 else 0, 0),
                'qtd_itens_ruptura': qtd_itens_ruptura,
                'qtd_itens_disponiveis': qtd_itens_disponiveis,
                'total_itens': total_itens,
                'criticidade': criticidade,
                'valor_total_pedido': valor_total_pedido,
                'valor_disponivel': valor_total_pedido - valor_com_ruptura,
                'valor_com_ruptura': valor_com_ruptura,
                'data_disponibilidade_total': data_disponibilidade_total
            },
            'itens': itens_com_ruptura,
            'itens_disponiveis': itens_disponiveis,
            'performance_ms': tempo_processamento
        }
        
    except Exception as e:
        logger.error(f"Erro ao analisar pedido {num_pedido}: {e}")
        return {
            'success': False,
            'num_pedido': num_pedido,
            'error': str(e)
        }


def publicar_atualizacao(session_id, worker_id, resultados, lote_index):
    """
    Publica atualização de progresso
    """
    try:
        evento = {
            'tipo': 'atualizacao_lote',
            'session_id': session_id,
            'worker_id': worker_id,
            'lote_index': lote_index,
            'qtd_resultados': len(resultados),
            'timestamp': agora_utc_naive().isoformat()
        }
        
        # Publicar no canal da sessão
        canal = f'ruptura:updates:{session_id}'
        redis_conn.publish(canal, json.dumps(evento))
        
        logger.info(f"📢 Publicado evento de atualização: {len(resultados)} resultados")
        
    except Exception as e:
        logger.error(f"Erro ao publicar atualização: {e}")


def limpar_sessao(session_id):
    """
    Limpa dados de uma sessão do Redis
    """
    try:
        pattern = f'ruptura:*{session_id}*'
        keys = redis_conn.keys(pattern)
        if keys:
            redis_conn.delete(*keys)
            logger.info(f"Sessão {session_id} limpa: {len(keys)} chaves removidas")
    except Exception as e:
        logger.error(f"Erro ao limpar sessão: {e}")