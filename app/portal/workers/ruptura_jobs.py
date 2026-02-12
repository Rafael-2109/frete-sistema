"""
Jobs assíncronos para processamento de ruptura de estoque
Processa análises em lote para otimizar performance
SEM CACHE - processamento direto
"""

from app import create_app, db
from app.carteira.models import CarteiraPrincipal
from app.producao.models import ProgramacaoProducao
from app.estoque.services.estoque_simples import ServicoEstoqueSimples
from app.utils.timezone import agora_utc_naive
from sqlalchemy import func
from datetime import datetime
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


def processar_lote_ruptura(pedidos_ids, opcoes=None):
    """
    Processa análise de ruptura para um lote de pedidos
    
    Args:
        pedidos_ids: Lista de números de pedidos para analisar
        opcoes: Dicionário com opções de processamento
            - paralelo: bool (default True) - Processar em paralelo
            - max_workers: int (default 5) - Número de workers paralelos
            - salvar_redis: bool (default False) - Salvar no Redis
            - redis_prefix: str - Prefixo para chaves do Redis
            - redis_ttl: int - TTL em segundos para cache
    
    Returns:
        Dict com resultados de cada pedido e estatísticas
    """
    app = create_app()
    with app.app_context():
        inicio = time.time()
        
        opcoes = opcoes or {}
        paralelo = opcoes.get('paralelo', True)
        max_workers = opcoes.get('max_workers', 5)
        salvar_redis = opcoes.get('salvar_redis', False)
        redis_prefix = opcoes.get('redis_prefix', 'ruptura:resultado:')
        redis_ttl = opcoes.get('redis_ttl', 3600)
        
        logger.info(f"🚀 Processando {len(pedidos_ids)} pedidos")
        logger.info(f"   Modo: {'Paralelo' if paralelo else 'Sequencial'}")
        logger.info(f"   Workers: {max_workers if paralelo else 1}")
        logger.info(f"   Salvar Redis: {salvar_redis}")
        
        resultados = {}
        erros = []
        processados = 0
        
        if paralelo and len(pedidos_ids) > 1:
            # Processamento paralelo
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(analisar_pedido_worker, num_pedido): num_pedido 
                    for num_pedido in pedidos_ids
                }
                
                for future in as_completed(futures):
                    num_pedido = futures[future]
                    try:
                        resultado = future.result(timeout=30)
                        resultados[num_pedido] = resultado
                        processados += 1
                        
                        if processados % 10 == 0:
                            logger.info(f"   Processados: {processados}/{len(pedidos_ids)}")
                            
                    except Exception as e:
                        logger.error(f"❌ Erro ao processar {num_pedido}: {e}")
                        erros.append({
                            'pedido': num_pedido,
                            'erro': str(e)
                        })
                        resultados[num_pedido] = {
                            'success': False,
                            'error': str(e)
                        }
        else:
            # Processamento sequencial
            for num_pedido in pedidos_ids:
                try:
                    resultado = analisar_pedido_worker(num_pedido)
                    resultados[num_pedido] = resultado
                    processados += 1
                    
                except Exception as e:
                    logger.error(f"❌ Erro ao processar {num_pedido}: {e}")
                    erros.append({
                        'pedido': num_pedido,
                        'erro': str(e)
                    })
                    resultados[num_pedido] = {
                        'success': False,
                        'error': str(e)
                    }
        
        tempo_total = time.time() - inicio
        
        # Estatísticas do lote
        estatisticas = {
            'total_pedidos': len(resultados),
            'processados': processados,
            'erros': len(erros),
            'tempo_total_segundos': round(tempo_total, 2),
            'tempo_medio_ms': round((tempo_total / len(resultados) * 1000) if resultados else 0, 2)
        }
        
        # Contadores de status
        pedidos_ok = sum(1 for r in resultados.values() if r.get('pedido_ok') == True)
        pedidos_ruptura = sum(1 for r in resultados.values() if r.get('pedido_ok') == False and r.get('success'))
        
        estatisticas['pedidos_ok'] = pedidos_ok
        estatisticas['pedidos_com_ruptura'] = pedidos_ruptura
        
        logger.info(f"✅ Lote processado em {tempo_total:.2f}s")
        logger.info(f"   OK: {pedidos_ok} | Ruptura: {pedidos_ruptura} | Erros: {len(erros)}")
        
        # Salvar resultados no Redis se configurado
        if salvar_redis:
            try:
                import json
                import os
                from redis import Redis
                
                redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
                redis_conn = Redis.from_url(redis_url)
                
                # Salvar cada resultado individualmente no Redis
                for num_pedido, resultado in resultados.items():
                    chave = f"{redis_prefix}{num_pedido}"
                    valor = json.dumps(resultado)
                    redis_conn.setex(chave, redis_ttl, valor)
                
                logger.info(f"   💾 {len(resultados)} resultados salvos no Redis (TTL: {redis_ttl}s)")
                
            except Exception as e:
                logger.error(f"❌ Erro ao salvar no Redis: {e}")
        
        return resultados  # Retornar apenas resultados simplificado


def analisar_pedido_worker(num_pedido):
    """
    Worker para analisar um pedido individual
    Versão otimizada da análise de ruptura
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
                'message': 'Pedido não encontrado'
            }
        
        # Produtos únicos
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
            ).order_by(
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
        
        # Calcular projeções
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
        
        # Análise dos itens
        itens_com_ruptura = []
        itens_disponiveis = []
        valor_total_pedido = 0
        valor_com_ruptura = 0
        
        for item in itens:
            valor_item = float(item.qtd_saldo_produto_pedido * (item.preco_produto_pedido or 0))
            valor_total_pedido += valor_item
            
            projecao = projecoes_produtos.get(item.cod_produto, {})
            estoque_d7 = float(projecao.get('menor_estoque_d7', 0))
            qtd_saldo = float(item.qtd_saldo_produto_pedido)
            
            if qtd_saldo > estoque_d7:
                ruptura = qtd_saldo - estoque_d7
                valor_com_ruptura += valor_item
                
                producoes_futuras = producoes_por_produto.get(item.cod_produto, [])
                primeira_producao = producoes_futuras[0] if producoes_futuras else None
                
                itens_com_ruptura.append({
                    'cod_produto': item.cod_produto,
                    'nome_produto': item.nome_produto,
                    'qtd_saldo': int(qtd_saldo),
                    'estoque_min_d7': int(estoque_d7),
                    'ruptura_qtd': int(ruptura),
                    'data_producao': primeira_producao['data'].isoformat() if primeira_producao else None,
                    'qtd_producao': int(primeira_producao['qtd']) if primeira_producao else 0
                })
            else:
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
                'message': 'Pedido OK - Todos os itens disponíveis',
                'performance_ms': tempo_processamento
            }
        
        # Calcular criticidade
        percentual_ruptura = (valor_com_ruptura / valor_total_pedido * 100) if valor_total_pedido > 0 else 0
        qtd_itens_ruptura = len(itens_com_ruptura)
        
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
            'resumo': {
                'num_pedido': num_pedido,
                'percentual_ruptura': round(percentual_ruptura, 2),
                'qtd_itens_ruptura': qtd_itens_ruptura,
                'total_itens': len(itens),
                'criticidade': criticidade,
                'valor_total_pedido': valor_total_pedido,
                'valor_com_ruptura': valor_com_ruptura
            },
            'itens': itens_com_ruptura,
            'itens_disponiveis': itens_disponiveis,
            'performance_ms': tempo_processamento
        }
        
    except Exception as e:
        logger.error(f"Erro no worker para pedido {num_pedido}: {e}")
        return {
            'success': False,
            'num_pedido': num_pedido,
            'error': str(e)
        }