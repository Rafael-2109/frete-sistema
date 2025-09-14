"""
Utilitário para buscar pedido_cliente (Pedido de Compra do Cliente) do Odoo
============================================================================

Este módulo fornece funções otimizadas para buscar o campo l10n_br_pedido_compra
diretamente do Odoo quando necessário.

Performance:
- Busca individual: ~50-200ms
- Busca em lote: ~100-300ms para até 100 pedidos

Autor: Sistema de Fretes
Data: 2025-01-13
"""

import logging
from typing import Dict, List, Optional
from app.odoo.utils.connection import get_odoo_connection

logger = logging.getLogger(__name__)


def buscar_pedido_cliente_odoo(num_pedido: str) -> Optional[str]:
    """
    Busca o campo pedido_cliente (l10n_br_pedido_compra) diretamente do Odoo.

    Esta função é otimizada para buscar apenas o campo necessário,
    minimizando o tráfego de rede e o tempo de resposta.

    Args:
        num_pedido (str): Número do pedido no formato Odoo (ex: VSC000123)

    Returns:
        str: Valor do pedido_cliente (pedido de compra do cliente)
        None: Se não encontrar o pedido ou em caso de erro

    Performance:
        - Tempo médio: 50-200ms por busca
        - Timeout: configurado na conexão

    Exemplo de uso:
        >>> from app.odoo.utils.pedido_cliente_utils import buscar_pedido_cliente_odoo
        >>> pedido_cliente = buscar_pedido_cliente_odoo('VSC000123')
        >>> if pedido_cliente:
        ...     print(f"Pedido de compra: {pedido_cliente}")
        ... else:
        ...     print("Pedido de compra não encontrado")
    """
    try:
        # Validar entrada
        if not num_pedido:
            logger.warning("buscar_pedido_cliente_odoo: num_pedido vazio")
            return None

        # Remover espaços e normalizar
        num_pedido = str(num_pedido).strip()

        # Obter conexão com Odoo
        connection = get_odoo_connection()
        if not connection:
            logger.error("Não foi possível obter conexão com Odoo")
            return None

        # Buscar apenas o campo necessário
        logger.debug(f"Buscando pedido_cliente para pedido {num_pedido}")

        pedidos = connection.search_read(
            'sale.order',
            [('name', '=', num_pedido)],
            ['l10n_br_pedido_compra', 'name', 'state'],  # Incluir state para debug
            limit=1
        )

        if pedidos and len(pedidos) > 0:
            pedido = pedidos[0]
            pedido_cliente = pedido.get('l10n_br_pedido_compra')

            if pedido_cliente:
                logger.info(f"✅ Pedido_cliente encontrado para {num_pedido}: {pedido_cliente}")
            else:
                logger.debug(f"⚠️ Pedido {num_pedido} existe mas sem pedido_cliente (state: {pedido.get('state')})")

            return pedido_cliente
        else:
            logger.debug(f"❌ Pedido {num_pedido} não encontrado no Odoo")
            return None

    except Exception as e:
        logger.error(f"❌ Erro ao buscar pedido_cliente do Odoo para {num_pedido}: {e}")
        return None


def buscar_pedidos_cliente_lote(nums_pedidos: List[str]) -> Dict[str, Optional[str]]:
    """
    Busca pedido_cliente para múltiplos pedidos de uma vez (otimizado para lote).

    Args:
        nums_pedidos (List[str]): Lista de números de pedidos

    Returns:
        Dict[str, str]: Dicionário {num_pedido: pedido_cliente}

    Performance:
        - Muito mais eficiente que buscar um por um
        - Tempo: ~100-300ms para até 100 pedidos

    Exemplo de uso:
        >>> from app.odoo.utils.pedido_cliente_utils import buscar_pedidos_cliente_lote
        >>> pedidos = ['VSC000123', 'VSC000124', 'VSC000125']
        >>> resultados = buscar_pedidos_cliente_lote(pedidos)
        >>> for num_pedido, pedido_cliente in resultados.items():
        ...     print(f"{num_pedido}: {pedido_cliente or 'Não encontrado'}")
    """
    try:
        if not nums_pedidos:
            return {}

        # Normalizar números de pedidos
        nums_pedidos = [str(p).strip() for p in nums_pedidos if p]

        if not nums_pedidos:
            return {}

        # Obter conexão com Odoo
        connection = get_odoo_connection()
        if not connection:
            logger.error("Não foi possível obter conexão com Odoo")
            return {num: None for num in nums_pedidos}

        logger.info(f"Buscando pedido_cliente para {len(nums_pedidos)} pedidos em lote")

        # Buscar todos de uma vez
        pedidos = connection.search_read(
            'sale.order',
            [('name', 'in', nums_pedidos)],
            ['name', 'l10n_br_pedido_compra'],
            limit=len(nums_pedidos)
        )

        # Criar dicionário de resultados
        resultado = {num: None for num in nums_pedidos}  # Inicializar todos como None

        for pedido in pedidos:
            num_pedido = pedido.get('name')
            pedido_cliente = pedido.get('l10n_br_pedido_compra')
            if num_pedido:
                resultado[num_pedido] = pedido_cliente

        # Log de estatísticas
        encontrados = sum(1 for v in resultado.values() if v is not None)
        logger.info(f"✅ Busca em lote concluída: {encontrados}/{len(nums_pedidos)} com pedido_cliente")

        return resultado

    except Exception as e:
        logger.error(f"❌ Erro ao buscar pedidos_cliente em lote: {e}")
        return {num: None for num in nums_pedidos}


def atualizar_pedido_cliente_separacao(separacao_id: int) -> bool:
    """
    Atualiza o campo pedido_cliente de um registro de Separacao
    buscando o valor diretamente do Odoo.

    Args:
        separacao_id (int): ID do registro de Separacao

    Returns:
        bool: True se atualizou com sucesso, False caso contrário

    Exemplo de uso:
        >>> from app.odoo.utils.pedido_cliente_utils import atualizar_pedido_cliente_separacao
        >>> if atualizar_pedido_cliente_separacao(123):
        ...     print("Pedido_cliente atualizado com sucesso")
    """
    try:
        from app.separacao.models import Separacao
        from app import db

        # Buscar o registro de Separacao
        separacao = Separacao.query.get(separacao_id)
        if not separacao:
            logger.warning(f"Separacao {separacao_id} não encontrada")
            return False

        if not separacao.num_pedido:
            logger.warning(f"Separacao {separacao_id} sem num_pedido")
            return False

        # Buscar pedido_cliente do Odoo
        pedido_cliente = buscar_pedido_cliente_odoo(separacao.num_pedido)

        if pedido_cliente:
            # Atualizar o registro
            separacao.pedido_cliente = pedido_cliente
            db.session.commit()
            logger.info(f"✅ Separacao {separacao_id} atualizada com pedido_cliente: {pedido_cliente}")
            return True
        else:
            logger.debug(f"Pedido_cliente não encontrado para Separacao {separacao_id} (pedido {separacao.num_pedido})")
            return False

    except Exception as e:
        logger.error(f"❌ Erro ao atualizar pedido_cliente da Separacao {separacao_id}: {e}")
        return False


def buscar_pedido_cliente_com_fallback(num_pedido: str, separacao_id: Optional[int] = None) -> Optional[str]:
    """
    Busca pedido_cliente primeiro localmente na Separacao,
    se não encontrar busca no Odoo.

    Args:
        num_pedido (str): Número do pedido
        separacao_id (int, optional): ID da Separacao para busca local

    Returns:
        str: Valor do pedido_cliente
        None: Se não encontrar

    Exemplo de uso:
        >>> from app.odoo.utils.pedido_cliente_utils import buscar_pedido_cliente_com_fallback
        >>> pedido_cliente = buscar_pedido_cliente_com_fallback('VSC000123', separacao_id=456)
        >>> print(f"Pedido de compra: {pedido_cliente or 'Não encontrado'}")
    """
    try:
        # Tentar buscar localmente primeiro se tiver separacao_id
        if separacao_id:
            from app.separacao.models import Separacao

            separacao = Separacao.query.get(separacao_id)
            if separacao and separacao.pedido_cliente:
                logger.debug(f"Pedido_cliente encontrado localmente para Separacao {separacao_id}")
                return separacao.pedido_cliente

        # Se não encontrou localmente, buscar no Odoo
        logger.debug(f"Buscando pedido_cliente no Odoo para {num_pedido}")
        return buscar_pedido_cliente_odoo(num_pedido)

    except Exception as e:
        logger.error(f"❌ Erro em buscar_pedido_cliente_com_fallback: {e}")
        return None


# Função de teste/exemplo
if __name__ == "__main__":
    # Testar busca individual
    print("🧪 Testando busca individual...")
    pedido_teste = "VSC000123"  # Substitua por um pedido real
    resultado = buscar_pedido_cliente_odoo(pedido_teste)
    print(f"Resultado para {pedido_teste}: {resultado}")

    # Testar busca em lote
    print("\n🧪 Testando busca em lote...")
    pedidos_teste = ["VSC000123", "VSC000124", "VSC000125"]  # Substitua por pedidos reais
    resultados = buscar_pedidos_cliente_lote(pedidos_teste)
    for num, pc in resultados.items():
        print(f"  {num}: {pc or 'Não encontrado'}")