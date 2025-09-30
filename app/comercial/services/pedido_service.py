"""
Service para agregação e processamento de dados de pedidos
============================================================

Este módulo fornece funções para agregar informações completas de pedidos,
incluindo status de faturamento, entrega e valores.

Autor: Sistema de Fretes
Data: 2025-01-19
"""

from sqlalchemy import distinct, func, or_, case
from app import db
from app.carteira.models import CarteiraPrincipal
from app.faturamento.models import FaturamentoProduto
from app.monitoramento.models import EntregaMonitorada
from app.separacao.models import Separacao
from app.odoo.utils.pedido_cliente_utils import buscar_pedidos_cliente_lote
from app.odoo.utils.metodo_entrega_utils import buscar_metodos_entrega_lote
from decimal import Decimal
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class PedidoService:
    """Service para processar e agregar dados de pedidos"""

    @staticmethod
    def obter_detalhes_pedidos_cliente(
        cnpj: str,
        filtro_posicao: str = 'em_aberto',
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """
        Retorna informações detalhadas dos pedidos de um cliente com paginação.

        Args:
            cnpj (str): CNPJ do cliente
            filtro_posicao (str): 'em_aberto' ou 'todos'
            page (int): Página atual (começando de 1)
            per_page (int): Número de itens por página

        Returns:
            Dict contendo:
                - pedidos: Lista de dicionários com informações dos pedidos
                - total: Total de pedidos
                - page: Página atual
                - per_page: Itens por página
                - total_pages: Total de páginas
        """
        try:
            # Obter lista de pedidos do cliente
            pedidos_lista = PedidoService._obter_pedidos_filtrados(cnpj, filtro_posicao)

            # Calcular paginação
            total = len(pedidos_lista)
            total_pages = (total + per_page - 1) // per_page
            start = (page - 1) * per_page
            end = start + per_page
            pedidos_pagina = pedidos_lista[start:end]

            # Se não há pedidos na página, retornar vazio
            if not pedidos_pagina:
                return {
                    'pedidos': [],
                    'total': total,
                    'page': page,
                    'per_page': per_page,
                    'total_pages': total_pages
                }

            # Buscar informações detalhadas de cada pedido
            pedidos_detalhados = []

            # Preparar lista para busca em lote no Odoo
            nums_pedidos = [p for p in pedidos_pagina]

            # Buscar pedido_cliente em lote
            pedidos_cliente_map = buscar_pedidos_cliente_lote(nums_pedidos)

            # Buscar método de entrega em lote
            metodos_entrega_map = buscar_metodos_entrega_lote(nums_pedidos)

            for num_pedido in pedidos_pagina:
                detalhe = PedidoService._processar_pedido(
                    num_pedido,
                    cnpj,
                    pedidos_cliente_map.get(num_pedido),
                    metodos_entrega_map.get(num_pedido)
                )
                if detalhe:
                    pedidos_detalhados.append(detalhe)

            return {
                'pedidos': pedidos_detalhados,
                'total': total,
                'page': page,
                'per_page': per_page,
                'total_pages': total_pages
            }

        except Exception as e:
            logger.error(f"Erro ao obter detalhes dos pedidos do cliente {cnpj}: {e}")
            return {
                'pedidos': [],
                'total': 0,
                'page': 1,
                'per_page': per_page,
                'total_pages': 0
            }

    @staticmethod
    def _obter_pedidos_filtrados(cnpj: str, filtro_posicao: str) -> List[str]:
        """
        Obtém lista de pedidos do cliente conforme filtro.

        Args:
            cnpj (str): CNPJ do cliente
            filtro_posicao (str): 'em_aberto' ou 'todos'

        Returns:
            Lista de números de pedidos únicos
        """
        pedidos = set()

        if filtro_posicao == 'em_aberto':
            # 1. Pedidos em carteira
            pedidos_carteira = db.session.query(
                distinct(CarteiraPrincipal.num_pedido)
            ).filter(
                CarteiraPrincipal.cnpj_cpf == cnpj,
                CarteiraPrincipal.num_pedido.isnot(None)
            ).all()

            for p in pedidos_carteira:
                if p[0]:
                    pedidos.add(p[0])

            # 2. Pedidos faturados mas não totalmente entregues
            # Subquery para agrupar entregas por pedido
            subq_entregas = db.session.query(
                FaturamentoProduto.origem.label('pedido'),
                func.sum(FaturamentoProduto.valor_produto_faturado).label('valor_faturado'),
                func.sum(
                    case(
                        (EntregaMonitorada.status_finalizacao == 'Entregue',
                         EntregaMonitorada.valor_nf),
                        else_=0
                    )
                ).label('valor_entregue')
            ).outerjoin(
                EntregaMonitorada,
                FaturamentoProduto.numero_nf == EntregaMonitorada.numero_nf
            ).filter(
                FaturamentoProduto.cnpj_cliente == cnpj,
                FaturamentoProduto.origem.isnot(None)
            ).group_by(
                FaturamentoProduto.origem
            ).subquery()

            # Buscar pedidos onde valor_entregue < valor_faturado
            pedidos_nao_entregues = db.session.query(
                subq_entregas.c.pedido
            ).filter(
                or_(
                    subq_entregas.c.valor_entregue < subq_entregas.c.valor_faturado,
                    subq_entregas.c.valor_entregue.is_(None)
                )
            ).all()

            for p in pedidos_nao_entregues:
                if p[0]:
                    pedidos.add(p[0])

        else:  # todos
            # 1. Pedidos em carteira
            pedidos_carteira = db.session.query(
                distinct(CarteiraPrincipal.num_pedido)
            ).filter(
                CarteiraPrincipal.cnpj_cpf == cnpj,
                CarteiraPrincipal.num_pedido.isnot(None)
            ).all()

            for p in pedidos_carteira:
                if p[0]:
                    pedidos.add(p[0])

            # 2. Todos os pedidos faturados
            pedidos_faturados = db.session.query(
                distinct(FaturamentoProduto.origem)
            ).filter(
                FaturamentoProduto.cnpj_cliente == cnpj,
                FaturamentoProduto.origem.isnot(None)
            ).all()

            for p in pedidos_faturados:
                if p[0]:
                    pedidos.add(p[0])

        return sorted(list(pedidos))

    @staticmethod
    def _processar_pedido(
        num_pedido: str,
        cnpj: str,
        pedido_cliente: Optional[str],
        metodo_entrega: Optional[str]
    ) -> Dict[str, Any]:
        """
        Processa informações detalhadas de um pedido específico.

        Args:
            num_pedido (str): Número do pedido
            cnpj (str): CNPJ do cliente
            pedido_cliente (str): Pedido de compra do cliente (já buscado)
            metodo_entrega (str): Método de entrega (já buscado)

        Returns:
            Dicionário com todas as informações do pedido
        """
        try:
            resultado = {
                'num_pedido': num_pedido,
                'pedido_cliente': '-',
                'incoterm': '-',
                'metodo_entrega_pedido': '-',
                'data_pedido': None,
                'status': 'Em Aberto',
                'valor_total_pedido': Decimal('0.00'),
                'valor_total_faturado': Decimal('0.00'),
                'valor_entregue': Decimal('0.00'),
                'saldo_carteira': Decimal('0.00')
            }

            # 1. Buscar informações da CarteiraPrincipal (se existir)
            # Buscar dados agregados do pedido (somando TODOS os produtos sem GROUP BY)
            info_carteira = db.session.query(
                func.min(CarteiraPrincipal.data_pedido).label('data_pedido'),
                func.min(CarteiraPrincipal.incoterm).label('incoterm'),
                func.min(CarteiraPrincipal.metodo_entrega_pedido).label('metodo_entrega_pedido'),
                func.min(CarteiraPrincipal.pedido_cliente).label('pedido_cliente'),
                func.sum(
                    CarteiraPrincipal.qtd_produto_pedido *
                    CarteiraPrincipal.preco_produto_pedido
                ).label('valor_total'),
                func.sum(
                    CarteiraPrincipal.qtd_saldo_produto_pedido *
                    CarteiraPrincipal.preco_produto_pedido
                ).label('valor_saldo')
            ).filter(
                CarteiraPrincipal.cnpj_cpf == cnpj,
                CarteiraPrincipal.num_pedido == num_pedido
            ).first()  # Sem GROUP BY, já que filtramos por um pedido específico

            if info_carteira and info_carteira.valor_total:
                resultado['data_pedido'] = info_carteira.data_pedido
                resultado['incoterm'] = info_carteira.incoterm or '-'
                resultado['valor_total_pedido'] = Decimal(str(info_carteira.valor_total))
                resultado['saldo_carteira'] = Decimal(str(info_carteira.valor_saldo or 0))

                # Pedido cliente - prioridade: Separacao > CarteiraPrincipal > Odoo
                if not pedido_cliente:
                    # Tentar buscar de Separacao primeiro
                    pedido_cliente_sep = db.session.query(
                        Separacao.pedido_cliente
                    ).filter(
                        Separacao.num_pedido == num_pedido
                    ).first()

                    if pedido_cliente_sep and pedido_cliente_sep[0]:
                        pedido_cliente = pedido_cliente_sep[0]
                    elif info_carteira.pedido_cliente:
                        pedido_cliente = info_carteira.pedido_cliente

                # Método de entrega - prioridade: CarteiraPrincipal > Odoo
                if info_carteira.metodo_entrega_pedido:
                    resultado['metodo_entrega_pedido'] = info_carteira.metodo_entrega_pedido
                elif metodo_entrega:
                    resultado['metodo_entrega_pedido'] = metodo_entrega

            # 2. Se não tem dados na carteira, buscar de Separacao
            if not info_carteira:
                info_separacao = db.session.query(
                    Separacao.data_pedido,
                    Separacao.pedido_cliente
                ).filter(
                    Separacao.num_pedido == num_pedido,
                    Separacao.cnpj_cpf == cnpj
                ).first()

                if info_separacao:
                    resultado['data_pedido'] = info_separacao.data_pedido
                    if info_separacao.pedido_cliente and not pedido_cliente:
                        pedido_cliente = info_separacao.pedido_cliente

            # 3. Buscar informações de faturamento
            # CORREÇÃO: Remover GROUP BY do incoterm para somar TODOS os valores faturados
            valor_faturado = db.session.query(
                func.sum(FaturamentoProduto.valor_produto_faturado).label('valor_faturado')
            ).filter(
                FaturamentoProduto.cnpj_cliente == cnpj,
                FaturamentoProduto.origem == num_pedido,
                FaturamentoProduto.status_nf != 'Cancelado'
            ).scalar()

            # Buscar o primeiro incoterm do pedido (se precisar)
            primeiro_incoterm = None
            if resultado['incoterm'] == '-':
                primeiro_incoterm = db.session.query(
                    FaturamentoProduto.incoterm
                ).filter(
                    FaturamentoProduto.cnpj_cliente == cnpj,
                    FaturamentoProduto.origem == num_pedido,
                    FaturamentoProduto.status_nf != 'Cancelado',
                    FaturamentoProduto.incoterm.isnot(None)
                ).first()

            if valor_faturado:
                resultado['valor_total_faturado'] = Decimal(str(valor_faturado))

                # Se não tem valor total do pedido na carteira, usar valor faturado
                if resultado['valor_total_pedido'] == 0:
                    resultado['valor_total_pedido'] = resultado['valor_total_faturado']

            # Aplicar incoterm se encontrado
            if primeiro_incoterm and primeiro_incoterm[0]:
                resultado['incoterm'] = primeiro_incoterm[0]

            # 4. Buscar informações de entregas
            # CORREÇÃO: Como 1 NF = 1 Pedido, buscar NFs do pedido e verificar quais foram entregues
            # Primeiro, buscar as NFs distintas do pedido
            nfs_do_pedido = db.session.query(
                distinct(FaturamentoProduto.numero_nf)
            ).filter(
                FaturamentoProduto.cnpj_cliente == cnpj,
                FaturamentoProduto.origem == num_pedido,
                FaturamentoProduto.numero_nf.isnot(None),
                FaturamentoProduto.status_nf != 'Cancelado'
            ).subquery()

            # Depois, somar o valor das NFs entregues
            info_entregas = db.session.query(
                func.sum(EntregaMonitorada.valor_nf).label('valor_entregue')
            ).filter(
                EntregaMonitorada.numero_nf.in_(nfs_do_pedido),
                EntregaMonitorada.status_finalizacao == 'Entregue'
            ).scalar()

            if info_entregas:
                resultado['valor_entregue'] = Decimal(str(info_entregas or 0))

            # 5. Aplicar pedido_cliente e metodo_entrega do Odoo (já buscados)
            if pedido_cliente:
                resultado['pedido_cliente'] = pedido_cliente

            if metodo_entrega and resultado['metodo_entrega_pedido'] == '-':
                resultado['metodo_entrega_pedido'] = metodo_entrega

            # 6. Calcular status do pedido
            valor_total = resultado['valor_total_pedido']
            valor_faturado = resultado['valor_total_faturado']
            valor_entregue = resultado['valor_entregue']

            if valor_faturado == 0:
                resultado['status'] = 'Em Aberto'
            elif valor_faturado < valor_total:
                resultado['status'] = 'Parcialmente Faturado'
            elif valor_entregue < valor_total:
                resultado['status'] = 'Parcialmente Entregue'
            else: #valor_entregue >= valor_total
                resultado['status'] = 'Entregue'

            # 7. Calcular saldo em carteira
            # Se tem saldo da CarteiraPrincipal, usa ele
            # Senão, calcula como valor_total - valor_faturado
            if resultado['saldo_carteira'] == 0 and valor_total > 0:
                resultado['saldo_carteira'] = max(Decimal('0'), valor_total - valor_faturado)

            return resultado

        except Exception as e:
            logger.error(f"Erro ao processar pedido {num_pedido}: {e}")
            return {
                'num_pedido': num_pedido,
                'pedido_cliente': '-',
                'incoterm': '-',
                'metodo_entrega_pedido': '-',
                'data_pedido': None,
                'status': 'Erro',
                'valor_total_pedido': Decimal('0.00'),
                'valor_total_faturado': Decimal('0.00'),
                'valor_entregue': Decimal('0.00'),
                'saldo_carteira': Decimal('0.00')
            }