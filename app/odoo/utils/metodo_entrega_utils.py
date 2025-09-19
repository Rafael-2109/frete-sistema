"""
Utilitário para buscar método de entrega (carrier_id) do Odoo
==============================================================

Este módulo fornece funções otimizadas para buscar o campo carrier_id
diretamente do Odoo quando necessário.

Performance:
- Busca individual: ~50-200ms
- Busca em lote: ~100-300ms para até 100 pedidos
- Cache Redis: TTL de 1 hora para evitar buscas repetitivas

Autor: Sistema de Fretes
Data: 2025-01-19
"""

import logging
from typing import Dict, List, Optional
from app.odoo.utils.connection import get_odoo_connection
from app.utils.redis_cache import RedisCache

logger = logging.getLogger(__name__)

# Inicializar cache Redis
cache = RedisCache()


def buscar_metodo_entrega_odoo(num_pedido: str, use_cache: bool = True) -> Optional[str]:
    """
    Busca o campo carrier_id (método de entrega) diretamente do Odoo.

    O carrier_id no Odoo já retorna o nome da transportadora diretamente.

    Args:
        num_pedido (str): Número do pedido no formato Odoo (ex: VSC000123)
        use_cache (bool): Se True, usa cache Redis (padrão: True)

    Returns:
        str: Nome do método de entrega/transportadora
        None: Se não encontrar o pedido ou em caso de erro

    Performance:
        - Com cache hit: ~1-5ms
        - Com cache miss: 50-200ms
        - TTL do cache: 3600 segundos (1 hora)

    Exemplo de uso:
        >>> from app.odoo.utils.metodo_entrega_utils import buscar_metodo_entrega_odoo
        >>> metodo = buscar_metodo_entrega_odoo('VSC000123')
        >>> if metodo:
        ...     print(f"Método de entrega: {metodo}")
        ... else:
        ...     print("Método de entrega não encontrado")
    """
    try:
        # Validar entrada
        if not num_pedido:
            return None

        num_pedido = str(num_pedido).strip()

        # Tentar buscar do cache primeiro
        if use_cache and cache.disponivel:
            chave_cache = f"metodo_entrega:{num_pedido}"
            valor_cache = cache.get(chave_cache)
            if valor_cache is not None:
                logger.debug(f"✅ Cache hit para método de entrega de {num_pedido}")
                return valor_cache

        # Obter conexão com Odoo
        connection = get_odoo_connection()
        if not connection:
            logger.error("Não foi possível obter conexão com Odoo")
            return None

        logger.debug(f"Buscando método de entrega no Odoo para pedido {num_pedido}")

        # Buscar pedido com campo carrier_id
        pedidos = connection.search_read(
            'sale.order',
            [('name', '=', num_pedido)],
            ['carrier_id', 'name', 'state'],  # carrier_id já retorna o nome
            limit=1
        )

        if pedidos and len(pedidos) > 0:
            pedido = pedidos[0]
            metodo_entrega = pedido.get('carrier_id')

            # Se carrier_id for uma tupla (id, nome), pegar o nome
            if isinstance(metodo_entrega, (list, tuple)) and len(metodo_entrega) > 1:
                metodo_entrega = metodo_entrega[1]  # Pegar o nome
            elif isinstance(metodo_entrega, bool) and not metodo_entrega:
                metodo_entrega = None

            if metodo_entrega:
                logger.info(f"✅ Método de entrega encontrado para {num_pedido}: {metodo_entrega}")

                # Salvar no cache
                if use_cache and cache.disponivel:
                    cache.set(chave_cache, metodo_entrega, ttl=3600)  # 1 hora
            else:
                logger.debug(f"⚠️ Pedido {num_pedido} existe mas sem método de entrega (state: {pedido.get('state')})")

            return metodo_entrega
        else:
            logger.debug(f"❌ Pedido {num_pedido} não encontrado no Odoo")
            return None

    except Exception as e:
        logger.error(f"❌ Erro ao buscar método de entrega do Odoo para {num_pedido}: {e}")
        return None


def buscar_metodos_entrega_lote(nums_pedidos: List[str], use_cache: bool = True) -> Dict[str, Optional[str]]:
    """
    Busca método de entrega para múltiplos pedidos de uma vez (otimizado para lote).

    Args:
        nums_pedidos (List[str]): Lista de números de pedidos
        use_cache (bool): Se True, usa cache Redis (padrão: True)

    Returns:
        Dict[str, str]: Dicionário {num_pedido: metodo_entrega}

    Performance:
        - Muito mais eficiente que buscar um por um
        - Tempo: ~100-300ms para até 100 pedidos
        - Usa cache para pedidos já consultados

    Exemplo de uso:
        >>> from app.odoo.utils.metodo_entrega_utils import buscar_metodos_entrega_lote
        >>> pedidos = ['VSC000123', 'VSC000124', 'VSC000125']
        >>> resultados = buscar_metodos_entrega_lote(pedidos)
        >>> for num_pedido, metodo in resultados.items():
        ...     print(f"{num_pedido}: {metodo or 'Não encontrado'}")
    """
    try:
        if not nums_pedidos:
            return {}

        # Normalizar números de pedidos
        nums_pedidos = [str(p).strip() for p in nums_pedidos if p]

        if not nums_pedidos:
            return {}

        # Inicializar resultado
        resultado = {}
        pedidos_buscar = []

        # Verificar cache primeiro
        if use_cache and cache.disponivel:
            for num_pedido in nums_pedidos:
                chave_cache = f"metodo_entrega:{num_pedido}"
                valor_cache = cache.get(chave_cache)
                if valor_cache is not None:
                    resultado[num_pedido] = valor_cache
                    logger.debug(f"✅ Cache hit para {num_pedido}")
                else:
                    pedidos_buscar.append(num_pedido)
        else:
            pedidos_buscar = nums_pedidos

        # Se não há pedidos para buscar, retornar resultado do cache
        if not pedidos_buscar:
            logger.info(f"✅ Todos {len(nums_pedidos)} pedidos encontrados no cache")
            return resultado

        # Obter conexão com Odoo
        connection = get_odoo_connection()
        if not connection:
            logger.error("Não foi possível obter conexão com Odoo")
            # Retornar None para pedidos não encontrados no cache
            for num in pedidos_buscar:
                resultado[num] = None
            return resultado

        logger.info(f"Buscando método de entrega para {len(pedidos_buscar)} pedidos no Odoo")

        # Buscar todos de uma vez
        pedidos = connection.search_read(
            'sale.order',
            [('name', 'in', pedidos_buscar)],
            ['name', 'carrier_id'],
            limit=len(pedidos_buscar)
        )

        # Processar resultados
        for pedido in pedidos:
            num_pedido = pedido.get('name')
            metodo_entrega = pedido.get('carrier_id')

            # Se carrier_id for uma tupla (id, nome), pegar o nome
            if isinstance(metodo_entrega, (list, tuple)) and len(metodo_entrega) > 1:
                metodo_entrega = metodo_entrega[1]  # Pegar o nome
            elif isinstance(metodo_entrega, bool) and not metodo_entrega:
                metodo_entrega = None

            if num_pedido:
                resultado[num_pedido] = metodo_entrega

                # Salvar no cache
                if use_cache and cache.disponivel and metodo_entrega:
                    chave_cache = f"metodo_entrega:{num_pedido}"
                    cache.set(chave_cache, metodo_entrega, ttl=3600)  # 1 hora

        # Adicionar None para pedidos não encontrados
        for num in pedidos_buscar:
            if num not in resultado:
                resultado[num] = None

        # Log de estatísticas
        encontrados = sum(1 for v in resultado.values() if v is not None)
        logger.info(f"✅ Busca em lote concluída: {encontrados}/{len(nums_pedidos)} com método de entrega")

        return resultado

    except Exception as e:
        logger.error(f"❌ Erro ao buscar métodos de entrega em lote: {e}")
        return {num: None for num in nums_pedidos}


def limpar_cache_metodo_entrega(num_pedido: str = None):
    """
    Limpa o cache de método de entrega.

    Args:
        num_pedido (str, optional): Se fornecido, limpa apenas o cache deste pedido.
                                    Se None, limpa todo o cache de métodos de entrega.
    """
    try:
        if not cache.disponivel:
            return

        if num_pedido:
            chave_cache = f"metodo_entrega:{num_pedido}"
            cache.client.delete(chave_cache)
            logger.info(f"✅ Cache limpo para pedido {num_pedido}")
        else:
            # Limpar todos os caches de método de entrega
            pattern = "metodo_entrega:*"
            keys = cache.client.keys(pattern)
            if keys:
                cache.client.delete(*keys)
                logger.info(f"✅ Cache limpo para {len(keys)} pedidos")

    except Exception as e:
        logger.error(f"❌ Erro ao limpar cache: {e}")