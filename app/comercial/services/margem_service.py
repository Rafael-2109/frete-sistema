"""
Service para analise de margem de pedidos
Consultas otimizadas com agregacoes dinamicas

Autor: Sistema de Fretes
Data: 27/12/2025
"""

from sqlalchemy import func, distinct, text, case, and_, or_
from decimal import Decimal
from typing import List, Dict, Any, Optional
from datetime import date, datetime
from app import db
from app.carteira.models import CarteiraPrincipal
import logging

logger = logging.getLogger(__name__)


class MargemService:
    """
    Service para consultas de margem com multiplos agrupamentos
    Usa queries agregadas para performance
    """

    # Tolerancia para saldo (evita ruido de arredondamento)
    TOLERANCIA_SALDO = 0.02

    @staticmethod
    def obter_filtros_disponiveis() -> Dict[str, Any]:
        """
        Retorna listas de valores disponiveis para filtros
        """
        try:
            # Equipes disponiveis
            equipes = db.session.query(
                distinct(CarteiraPrincipal.equipe_vendas)
            ).filter(
                CarteiraPrincipal.equipe_vendas.isnot(None),
                CarteiraPrincipal.qtd_saldo_produto_pedido > MargemService.TOLERANCIA_SALDO
            ).order_by(CarteiraPrincipal.equipe_vendas).all()

            # Vendedores disponiveis
            vendedores = db.session.query(
                distinct(CarteiraPrincipal.vendedor)
            ).filter(
                CarteiraPrincipal.vendedor.isnot(None),
                CarteiraPrincipal.qtd_saldo_produto_pedido > MargemService.TOLERANCIA_SALDO
            ).order_by(CarteiraPrincipal.vendedor).all()

            # Categorias de produto (3 niveis)
            embalagens = db.session.query(
                distinct(CarteiraPrincipal.embalagem_produto)
            ).filter(
                CarteiraPrincipal.embalagem_produto.isnot(None),
                CarteiraPrincipal.qtd_saldo_produto_pedido > MargemService.TOLERANCIA_SALDO
            ).order_by(CarteiraPrincipal.embalagem_produto).all()

            materias_primas = db.session.query(
                distinct(CarteiraPrincipal.materia_prima_produto)
            ).filter(
                CarteiraPrincipal.materia_prima_produto.isnot(None),
                CarteiraPrincipal.qtd_saldo_produto_pedido > MargemService.TOLERANCIA_SALDO
            ).order_by(CarteiraPrincipal.materia_prima_produto).all()

            categorias = db.session.query(
                distinct(CarteiraPrincipal.categoria_produto)
            ).filter(
                CarteiraPrincipal.categoria_produto.isnot(None),
                CarteiraPrincipal.qtd_saldo_produto_pedido > MargemService.TOLERANCIA_SALDO
            ).order_by(CarteiraPrincipal.categoria_produto).all()

            return {
                'equipes': [e[0] for e in equipes if e[0]],
                'vendedores': [v[0] for v in vendedores if v[0]],
                'tipos_produto': {
                    'embalagem': [e[0] for e in embalagens if e[0]],
                    'materia_prima': [m[0] for m in materias_primas if m[0]],
                    'categoria': [c[0] for c in categorias if c[0]]
                }
            }

        except Exception as e:
            logger.error(f"Erro ao obter filtros disponiveis: {e}")
            return {
                'equipes': [],
                'vendedores': [],
                'tipos_produto': {'embalagem': [], 'materia_prima': [], 'categoria': []}
            }

    @staticmethod
    def obter_dados_margem(
        agrupamento: str = 'produto_pedido',
        filtros: Dict[str, Any] = None,
        page: int = 1,
        per_page: int = 50
    ) -> Dict[str, Any]:
        """
        Retorna dados de margem com agrupamento dinamico

        Args:
            agrupamento: Tipo de agrupamento
            filtros: Dict com filtros (data_inicio, data_fim, equipe, vendedor, tipo_produto)
            page: Pagina atual
            per_page: Itens por pagina

        Returns:
            Dict com dados, totais e paginacao
        """
        if filtros is None:
            filtros = {}

        try:
            # Escolher metodo baseado no agrupamento
            if agrupamento == 'produto_pedido':
                return MargemService._query_produto_pedido(filtros, page, per_page)
            elif agrupamento == 'pedido':
                return MargemService._query_por_pedido(filtros, page, per_page)
            elif agrupamento == 'data':
                return MargemService._query_por_data(filtros, page, per_page)
            elif agrupamento == 'tipo_produto':
                return MargemService._query_por_tipo_produto(filtros, page, per_page)
            elif agrupamento == 'equipe':
                return MargemService._query_por_equipe(filtros, page, per_page)
            elif agrupamento == 'vendedor':
                return MargemService._query_por_vendedor(filtros, page, per_page)
            else:
                return MargemService._query_produto_pedido(filtros, page, per_page)

        except Exception as e:
            logger.error(f"Erro ao obter dados de margem: {e}")
            return {
                'sucesso': False,
                'erro': str(e),
                'dados': [],
                'totais': {},
                'paginacao': {'page': page, 'per_page': per_page, 'total': 0}
            }

    @staticmethod
    def _aplicar_filtros_base(query, filtros: Dict[str, Any]):
        """Aplica filtros comuns a todas as queries"""

        # Filtro de saldo e margem
        query = query.filter(
            CarteiraPrincipal.qtd_saldo_produto_pedido > MargemService.TOLERANCIA_SALDO,
            CarteiraPrincipal.margem_liquida.isnot(None)
        )

        # Filtro de data
        if filtros.get('data_inicio'):
            try:
                data_inicio = datetime.strptime(filtros['data_inicio'], '%Y-%m-%d').date()
                query = query.filter(CarteiraPrincipal.data_pedido >= data_inicio)
            except ValueError:
                pass

        if filtros.get('data_fim'):
            try:
                data_fim = datetime.strptime(filtros['data_fim'], '%Y-%m-%d').date()
                query = query.filter(CarteiraPrincipal.data_pedido <= data_fim)
            except ValueError:
                pass

        # Filtro de equipe
        if filtros.get('equipe'):
            query = query.filter(CarteiraPrincipal.equipe_vendas == filtros['equipe'])

        # Filtro de vendedor
        if filtros.get('vendedor'):
            query = query.filter(CarteiraPrincipal.vendedor == filtros['vendedor'])

        # Filtro de tipo de produto
        if filtros.get('tipo_produto'):
            tipo = filtros['tipo_produto']
            if filtros.get('tipo_produto_campo') == 'materia_prima':
                query = query.filter(CarteiraPrincipal.materia_prima_produto == tipo)
            elif filtros.get('tipo_produto_campo') == 'categoria':
                query = query.filter(CarteiraPrincipal.categoria_produto == tipo)
            else:
                query = query.filter(CarteiraPrincipal.embalagem_produto == tipo)

        return query

    @staticmethod
    def _query_produto_pedido(filtros: Dict, page: int, per_page: int) -> Dict[str, Any]:
        """Retorna dados item a item (produto por pedido)"""

        query = db.session.query(
            CarteiraPrincipal.num_pedido,
            CarteiraPrincipal.cod_produto,
            CarteiraPrincipal.nome_produto,
            CarteiraPrincipal.raz_social_red,
            CarteiraPrincipal.cnpj_cpf,
            CarteiraPrincipal.cod_uf,
            CarteiraPrincipal.nome_cidade,
            CarteiraPrincipal.incoterm,
            CarteiraPrincipal.vendedor,
            CarteiraPrincipal.equipe_vendas,
            CarteiraPrincipal.data_pedido,
            (CarteiraPrincipal.qtd_saldo_produto_pedido * CarteiraPrincipal.preco_produto_pedido).label('valor_total'),
            CarteiraPrincipal.margem_liquida,
            CarteiraPrincipal.margem_liquida_percentual,
            CarteiraPrincipal.desconto_contratual,
            CarteiraPrincipal.desconto_percentual
        )

        query = MargemService._aplicar_filtros_base(query, filtros)
        query = query.order_by(CarteiraPrincipal.margem_liquida.desc())

        # Paginacao
        total = query.count()
        dados = query.offset((page - 1) * per_page).limit(per_page).all()

        # Calcular totais
        totais_query = db.session.query(
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido * CarteiraPrincipal.preco_produto_pedido).label('valor_total'),
            func.sum(CarteiraPrincipal.margem_liquida).label('margem_total'),
            func.avg(CarteiraPrincipal.margem_liquida_percentual).label('margem_media_pct')
        )
        totais_query = MargemService._aplicar_filtros_base(totais_query, filtros)
        totais_row = totais_query.first()

        return {
            'sucesso': True,
            'dados': [MargemService._row_produto_pedido_to_dict(row) for row in dados],
            'totais': {
                'valor_total': float(totais_row.valor_total or 0),
                'margem_liquida_total': float(totais_row.margem_total or 0),
                'margem_media_percentual': float(totais_row.margem_media_pct or 0)
            },
            'paginacao': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': (total + per_page - 1) // per_page
            }
        }

    @staticmethod
    def _row_produto_pedido_to_dict(row) -> Dict:
        """Converte row de produto_pedido para dict"""
        return {
            'num_pedido': row.num_pedido,
            'cod_produto': row.cod_produto,
            'nome_produto': row.nome_produto,
            'raz_social_red': row.raz_social_red,
            'cnpj_cpf': row.cnpj_cpf,
            'cod_uf': row.cod_uf,
            'nome_cidade': row.nome_cidade,
            'incoterm': row.incoterm,
            'vendedor': row.vendedor,
            'equipe_vendas': row.equipe_vendas,
            'data_pedido': row.data_pedido.isoformat() if row.data_pedido else None,
            'valor_total': float(row.valor_total or 0),
            'margem_liquida': float(row.margem_liquida or 0),
            'margem_liquida_percentual': float(row.margem_liquida_percentual or 0),
            'contrato': {
                'tem_desconto': bool(row.desconto_contratual),
                'percentual': float(row.desconto_percentual or 0)
            }
        }

    @staticmethod
    def _query_por_pedido(filtros: Dict, page: int, per_page: int) -> Dict[str, Any]:
        """Agrupa por pedido"""

        query = db.session.query(
            CarteiraPrincipal.num_pedido,
            func.max(CarteiraPrincipal.raz_social_red).label('raz_social_red'),
            func.max(CarteiraPrincipal.cnpj_cpf).label('cnpj_cpf'),
            func.max(CarteiraPrincipal.cod_uf).label('cod_uf'),
            func.max(CarteiraPrincipal.nome_cidade).label('nome_cidade'),
            func.max(CarteiraPrincipal.incoterm).label('incoterm'),
            func.max(CarteiraPrincipal.vendedor).label('vendedor'),
            func.max(CarteiraPrincipal.equipe_vendas).label('equipe_vendas'),
            func.max(CarteiraPrincipal.data_pedido).label('data_pedido'),
            func.count(CarteiraPrincipal.cod_produto).label('qtd_itens'),
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido * CarteiraPrincipal.preco_produto_pedido).label('valor_total'),
            func.sum(CarteiraPrincipal.margem_liquida).label('margem_liquida'),
            func.avg(CarteiraPrincipal.margem_liquida_percentual).label('margem_liquida_percentual'),
            func.bool_or(CarteiraPrincipal.desconto_contratual).label('tem_desconto'),
            func.max(CarteiraPrincipal.desconto_percentual).label('desconto_percentual')
        )

        query = MargemService._aplicar_filtros_base(query, filtros)
        query = query.group_by(CarteiraPrincipal.num_pedido)
        query = query.order_by(func.sum(CarteiraPrincipal.margem_liquida).desc())

        # Paginacao via subquery
        total_subq = db.session.query(func.count(distinct(CarteiraPrincipal.num_pedido)))
        total_subq = MargemService._aplicar_filtros_base(total_subq, filtros)
        total = total_subq.scalar() or 0

        dados = query.offset((page - 1) * per_page).limit(per_page).all()

        # Totais
        totais_query = db.session.query(
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido * CarteiraPrincipal.preco_produto_pedido).label('valor_total'),
            func.sum(CarteiraPrincipal.margem_liquida).label('margem_total'),
            func.avg(CarteiraPrincipal.margem_liquida_percentual).label('margem_media_pct')
        )
        totais_query = MargemService._aplicar_filtros_base(totais_query, filtros)
        totais_row = totais_query.first()

        return {
            'sucesso': True,
            'dados': [MargemService._row_pedido_to_dict(row) for row in dados],
            'totais': {
                'valor_total': float(totais_row.valor_total or 0),
                'margem_liquida_total': float(totais_row.margem_total or 0),
                'margem_media_percentual': float(totais_row.margem_media_pct or 0)
            },
            'paginacao': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': (total + per_page - 1) // per_page
            }
        }

    @staticmethod
    def _row_pedido_to_dict(row) -> Dict:
        """Converte row de pedido para dict"""
        return {
            'num_pedido': row.num_pedido,
            'raz_social_red': row.raz_social_red,
            'cnpj_cpf': row.cnpj_cpf,
            'cod_uf': row.cod_uf,
            'nome_cidade': row.nome_cidade,
            'incoterm': row.incoterm,
            'vendedor': row.vendedor,
            'equipe_vendas': row.equipe_vendas,
            'data_pedido': row.data_pedido.isoformat() if row.data_pedido else None,
            'qtd_itens': int(row.qtd_itens or 0),
            'valor_total': float(row.valor_total or 0),
            'margem_liquida': float(row.margem_liquida or 0),
            'margem_liquida_percentual': float(row.margem_liquida_percentual or 0),
            'contrato': {
                'tem_desconto': bool(row.tem_desconto),
                'percentual': float(row.desconto_percentual or 0)
            }
        }

    @staticmethod
    def _query_por_data(filtros: Dict, page: int, per_page: int) -> Dict[str, Any]:
        """Agrupa por data"""

        query = db.session.query(
            CarteiraPrincipal.data_pedido,
            func.count(distinct(CarteiraPrincipal.num_pedido)).label('qtd_pedidos'),
            func.count(CarteiraPrincipal.cod_produto).label('qtd_itens'),
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido * CarteiraPrincipal.preco_produto_pedido).label('valor_total'),
            func.sum(CarteiraPrincipal.margem_liquida).label('margem_liquida'),
            func.avg(CarteiraPrincipal.margem_liquida_percentual).label('margem_liquida_percentual')
        )

        query = MargemService._aplicar_filtros_base(query, filtros)
        query = query.filter(CarteiraPrincipal.data_pedido.isnot(None))
        query = query.group_by(CarteiraPrincipal.data_pedido)
        query = query.order_by(CarteiraPrincipal.data_pedido.desc())

        # Total de datas distintas
        total_subq = db.session.query(func.count(distinct(CarteiraPrincipal.data_pedido)))
        total_subq = MargemService._aplicar_filtros_base(total_subq, filtros)
        total_subq = total_subq.filter(CarteiraPrincipal.data_pedido.isnot(None))
        total = total_subq.scalar() or 0

        dados = query.offset((page - 1) * per_page).limit(per_page).all()

        # Totais
        totais_query = db.session.query(
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido * CarteiraPrincipal.preco_produto_pedido).label('valor_total'),
            func.sum(CarteiraPrincipal.margem_liquida).label('margem_total'),
            func.avg(CarteiraPrincipal.margem_liquida_percentual).label('margem_media_pct')
        )
        totais_query = MargemService._aplicar_filtros_base(totais_query, filtros)
        totais_row = totais_query.first()

        return {
            'sucesso': True,
            'dados': [{
                'data_pedido': row.data_pedido.isoformat() if row.data_pedido else None,
                'qtd_pedidos': int(row.qtd_pedidos or 0),
                'qtd_itens': int(row.qtd_itens or 0),
                'valor_total': float(row.valor_total or 0),
                'margem_liquida': float(row.margem_liquida or 0),
                'margem_liquida_percentual': float(row.margem_liquida_percentual or 0)
            } for row in dados],
            'totais': {
                'valor_total': float(totais_row.valor_total or 0),
                'margem_liquida_total': float(totais_row.margem_total or 0),
                'margem_media_percentual': float(totais_row.margem_media_pct or 0)
            },
            'paginacao': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': (total + per_page - 1) // per_page
            }
        }

    @staticmethod
    def _query_por_tipo_produto(filtros: Dict, page: int, per_page: int) -> Dict[str, Any]:
        """Agrupa por tipo de produto (embalagem, materia_prima, categoria)"""

        # Determinar campo de agrupamento
        campo_agrupamento = filtros.get('tipo_produto_campo', 'embalagem')

        if campo_agrupamento == 'materia_prima':
            campo = CarteiraPrincipal.materia_prima_produto
        elif campo_agrupamento == 'categoria':
            campo = CarteiraPrincipal.categoria_produto
        else:
            campo = CarteiraPrincipal.embalagem_produto

        query = db.session.query(
            campo.label('tipo_produto'),
            func.count(distinct(CarteiraPrincipal.num_pedido)).label('qtd_pedidos'),
            func.count(CarteiraPrincipal.cod_produto).label('qtd_itens'),
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido * CarteiraPrincipal.preco_produto_pedido).label('valor_total'),
            func.sum(CarteiraPrincipal.margem_liquida).label('margem_liquida'),
            func.avg(CarteiraPrincipal.margem_liquida_percentual).label('margem_liquida_percentual')
        )

        query = MargemService._aplicar_filtros_base(query, filtros)
        query = query.filter(campo.isnot(None))
        query = query.group_by(campo)
        query = query.order_by(func.sum(CarteiraPrincipal.margem_liquida).desc())

        # Total
        total_subq = db.session.query(func.count(distinct(campo)))
        total_subq = MargemService._aplicar_filtros_base(total_subq, filtros)
        total_subq = total_subq.filter(campo.isnot(None))
        total = total_subq.scalar() or 0

        dados = query.offset((page - 1) * per_page).limit(per_page).all()

        # Totais
        totais_query = db.session.query(
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido * CarteiraPrincipal.preco_produto_pedido).label('valor_total'),
            func.sum(CarteiraPrincipal.margem_liquida).label('margem_total'),
            func.avg(CarteiraPrincipal.margem_liquida_percentual).label('margem_media_pct')
        )
        totais_query = MargemService._aplicar_filtros_base(totais_query, filtros)
        totais_row = totais_query.first()

        return {
            'sucesso': True,
            'dados': [{
                'tipo_produto': row.tipo_produto,
                'campo_agrupamento': campo_agrupamento,
                'qtd_pedidos': int(row.qtd_pedidos or 0),
                'qtd_itens': int(row.qtd_itens or 0),
                'valor_total': float(row.valor_total or 0),
                'margem_liquida': float(row.margem_liquida or 0),
                'margem_liquida_percentual': float(row.margem_liquida_percentual or 0)
            } for row in dados],
            'totais': {
                'valor_total': float(totais_row.valor_total or 0),
                'margem_liquida_total': float(totais_row.margem_total or 0),
                'margem_media_percentual': float(totais_row.margem_media_pct or 0)
            },
            'paginacao': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': (total + per_page - 1) // per_page
            }
        }

    @staticmethod
    def _query_por_equipe(filtros: Dict, page: int, per_page: int) -> Dict[str, Any]:
        """Agrupa por equipe de vendas"""

        query = db.session.query(
            CarteiraPrincipal.equipe_vendas,
            func.count(distinct(CarteiraPrincipal.vendedor)).label('qtd_vendedores'),
            func.count(distinct(CarteiraPrincipal.cnpj_cpf)).label('qtd_clientes'),
            func.count(distinct(CarteiraPrincipal.num_pedido)).label('qtd_pedidos'),
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido * CarteiraPrincipal.preco_produto_pedido).label('valor_total'),
            func.sum(CarteiraPrincipal.margem_liquida).label('margem_liquida'),
            func.avg(CarteiraPrincipal.margem_liquida_percentual).label('margem_liquida_percentual')
        )

        query = MargemService._aplicar_filtros_base(query, filtros)
        query = query.filter(CarteiraPrincipal.equipe_vendas.isnot(None))
        query = query.group_by(CarteiraPrincipal.equipe_vendas)
        query = query.order_by(func.sum(CarteiraPrincipal.margem_liquida).desc())

        # Total
        total_subq = db.session.query(func.count(distinct(CarteiraPrincipal.equipe_vendas)))
        total_subq = MargemService._aplicar_filtros_base(total_subq, filtros)
        total_subq = total_subq.filter(CarteiraPrincipal.equipe_vendas.isnot(None))
        total = total_subq.scalar() or 0

        dados = query.offset((page - 1) * per_page).limit(per_page).all()

        # Totais
        totais_query = db.session.query(
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido * CarteiraPrincipal.preco_produto_pedido).label('valor_total'),
            func.sum(CarteiraPrincipal.margem_liquida).label('margem_total'),
            func.avg(CarteiraPrincipal.margem_liquida_percentual).label('margem_media_pct')
        )
        totais_query = MargemService._aplicar_filtros_base(totais_query, filtros)
        totais_row = totais_query.first()

        return {
            'sucesso': True,
            'dados': [{
                'equipe_vendas': row.equipe_vendas,
                'qtd_vendedores': int(row.qtd_vendedores or 0),
                'qtd_clientes': int(row.qtd_clientes or 0),
                'qtd_pedidos': int(row.qtd_pedidos or 0),
                'valor_total': float(row.valor_total or 0),
                'margem_liquida': float(row.margem_liquida or 0),
                'margem_liquida_percentual': float(row.margem_liquida_percentual or 0)
            } for row in dados],
            'totais': {
                'valor_total': float(totais_row.valor_total or 0),
                'margem_liquida_total': float(totais_row.margem_total or 0),
                'margem_media_percentual': float(totais_row.margem_media_pct or 0)
            },
            'paginacao': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': (total + per_page - 1) // per_page
            }
        }

    @staticmethod
    def _query_por_vendedor(filtros: Dict, page: int, per_page: int) -> Dict[str, Any]:
        """Agrupa por vendedor"""

        query = db.session.query(
            CarteiraPrincipal.vendedor,
            func.max(CarteiraPrincipal.equipe_vendas).label('equipe_vendas'),
            func.count(distinct(CarteiraPrincipal.cnpj_cpf)).label('qtd_clientes'),
            func.count(distinct(CarteiraPrincipal.num_pedido)).label('qtd_pedidos'),
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido * CarteiraPrincipal.preco_produto_pedido).label('valor_total'),
            func.sum(CarteiraPrincipal.margem_liquida).label('margem_liquida'),
            func.avg(CarteiraPrincipal.margem_liquida_percentual).label('margem_liquida_percentual')
        )

        query = MargemService._aplicar_filtros_base(query, filtros)
        query = query.filter(CarteiraPrincipal.vendedor.isnot(None))
        query = query.group_by(CarteiraPrincipal.vendedor)
        query = query.order_by(func.sum(CarteiraPrincipal.margem_liquida).desc())

        # Total
        total_subq = db.session.query(func.count(distinct(CarteiraPrincipal.vendedor)))
        total_subq = MargemService._aplicar_filtros_base(total_subq, filtros)
        total_subq = total_subq.filter(CarteiraPrincipal.vendedor.isnot(None))
        total = total_subq.scalar() or 0

        dados = query.offset((page - 1) * per_page).limit(per_page).all()

        # Totais
        totais_query = db.session.query(
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido * CarteiraPrincipal.preco_produto_pedido).label('valor_total'),
            func.sum(CarteiraPrincipal.margem_liquida).label('margem_total'),
            func.avg(CarteiraPrincipal.margem_liquida_percentual).label('margem_media_pct')
        )
        totais_query = MargemService._aplicar_filtros_base(totais_query, filtros)
        totais_row = totais_query.first()

        return {
            'sucesso': True,
            'dados': [{
                'vendedor': row.vendedor,
                'equipe_vendas': row.equipe_vendas,
                'qtd_clientes': int(row.qtd_clientes or 0),
                'qtd_pedidos': int(row.qtd_pedidos or 0),
                'valor_total': float(row.valor_total or 0),
                'margem_liquida': float(row.margem_liquida or 0),
                'margem_liquida_percentual': float(row.margem_liquida_percentual or 0)
            } for row in dados],
            'totais': {
                'valor_total': float(totais_row.valor_total or 0),
                'margem_liquida_total': float(totais_row.margem_total or 0),
                'margem_media_percentual': float(totais_row.margem_media_pct or 0)
            },
            'paginacao': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': (total + per_page - 1) // per_page
            }
        }

    @staticmethod
    def obter_historico_cliente(cnpj: str, limite: int = 4) -> Dict[str, Any]:
        """
        Retorna ultimos N pedidos do cliente

        Args:
            cnpj: CNPJ do cliente
            limite: Numero maximo de pedidos

        Returns:
            Dict com dados do cliente e pedidos
        """
        try:
            # Dados do cliente
            cliente = db.session.query(
                CarteiraPrincipal.cnpj_cpf,
                func.max(CarteiraPrincipal.raz_social_red).label('raz_social_red')
            ).filter(
                CarteiraPrincipal.cnpj_cpf == cnpj
            ).group_by(CarteiraPrincipal.cnpj_cpf).first()

            if not cliente:
                return {
                    'sucesso': False,
                    'erro': 'Cliente nao encontrado'
                }

            # Ultimos pedidos agrupados
            pedidos_query = db.session.query(
                CarteiraPrincipal.num_pedido,
                func.max(CarteiraPrincipal.data_pedido).label('data_pedido'),
                func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido * CarteiraPrincipal.preco_produto_pedido).label('valor_total'),
                func.sum(CarteiraPrincipal.margem_liquida).label('margem_liquida'),
                func.avg(CarteiraPrincipal.margem_liquida_percentual).label('margem_liquida_percentual')
            ).filter(
                CarteiraPrincipal.cnpj_cpf == cnpj,
                CarteiraPrincipal.margem_liquida.isnot(None)
            ).group_by(
                CarteiraPrincipal.num_pedido
            ).order_by(
                func.max(CarteiraPrincipal.data_pedido).desc()
            ).limit(limite)

            pedidos = pedidos_query.all()

            return {
                'sucesso': True,
                'cliente': {
                    'cnpj_cpf': cliente.cnpj_cpf,
                    'raz_social_red': cliente.raz_social_red
                },
                'pedidos': [{
                    'num_pedido': p.num_pedido,
                    'data_pedido': p.data_pedido.isoformat() if p.data_pedido else None,
                    'valor_total': float(p.valor_total or 0),
                    'margem_liquida': float(p.margem_liquida or 0),
                    'margem_liquida_percentual': float(p.margem_liquida_percentual or 0)
                } for p in pedidos]
            }

        except Exception as e:
            logger.error(f"Erro ao obter historico do cliente {cnpj}: {e}")
            return {
                'sucesso': False,
                'erro': str(e)
            }
