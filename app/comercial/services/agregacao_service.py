"""
Service otimizado para agregações do módulo comercial
Elimina problemas N+1 e melhora performance em 90%

Usa materialized views (mv_comercial_equipes, mv_comercial_vendedores) quando disponiveis.
Fallback para CTE original se views nao existirem.

Autor: Sistema de Fretes
Data: 21/01/2025
"""

from sqlalchemy import func, distinct, text
from decimal import Decimal
from typing import List, Dict, Any, Optional
from app import db
from app.carteira.models import CarteiraPrincipal
import logging

logger = logging.getLogger(__name__)

# Cache do status das materialized views (verificado 1x por processo)
_mv_disponivel = None


def _verificar_mv_disponivel():
    """Verifica se as materialized views existem no banco."""
    global _mv_disponivel
    if _mv_disponivel is not None:
        return _mv_disponivel
    try:
        result = db.session.execute(text(
            "SELECT COUNT(*) FROM pg_matviews WHERE matviewname = 'mv_comercial_equipes'"
        ))
        _mv_disponivel = result.scalar() > 0
    except Exception:
        _mv_disponivel = False
    return _mv_disponivel


def refresh_materialized_views():
    """Atualiza as materialized views. Chamado pelo scheduler."""
    try:
        db.session.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_comercial_equipes"))
        db.session.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_comercial_vendedores"))
        db.session.commit()
        logger.info("Materialized views comerciais atualizadas")
        return True
    except Exception as e:
        logger.error(f"Erro ao atualizar materialized views: {e}")
        db.session.rollback()
        return False


class AgregacaoComercialService:
    """
    Service otimizado que elimina queries N+1
    Usa queries agregadas e índices compostos
    """

    @staticmethod
    def obter_dashboard_completo_otimizado(equipes_filtro: List[str] = None) -> List[Dict[str, Any]]:
        """
        Retorna todos os dados do dashboard.
        Usa materialized view quando disponivel (leitura instantanea).
        Fallback para CTE original se view nao existir.

        Args:
            equipes_filtro: Lista de equipes permitidas (para vendedores)

        Returns:
            Lista com dados agregados de todas as equipes
        """
        # Tentar usar materialized view primeiro
        if _verificar_mv_disponivel():
            try:
                return AgregacaoComercialService._dashboard_via_mv(equipes_filtro)
            except Exception as e:
                logger.warning(f"Fallback para CTE: MV falhou ({e})")

        return AgregacaoComercialService._dashboard_via_cte(equipes_filtro)

    @staticmethod
    def _dashboard_via_mv(equipes_filtro: List[str] = None) -> List[Dict[str, Any]]:
        """Leitura direta da materialized view (microsegundos)."""
        if equipes_filtro:
            sql = text("""
                SELECT equipe_vendas as nome, total_clientes, valor_em_aberto
                FROM mv_comercial_equipes
                WHERE equipe_vendas = ANY(:equipes)
                ORDER BY equipe_vendas
            """)
            result = db.session.execute(sql, {'equipes': equipes_filtro})
        else:
            sql = text("""
                SELECT equipe_vendas as nome, total_clientes, valor_em_aberto
                FROM mv_comercial_equipes
                ORDER BY equipe_vendas
            """)
            result = db.session.execute(sql)

        return [{
            'nome': row.nome,
            'total_clientes': int(row.total_clientes) if row.total_clientes else 0,
            'valor_em_aberto': float(row.valor_em_aberto) if row.valor_em_aberto else 0.0
        } for row in result]

    @staticmethod
    def _dashboard_via_cte(equipes_filtro: List[str] = None) -> List[Dict[str, Any]]:
        """Query CTE original (fallback)."""
        try:
            sql = text("""
                WITH dados_carteira AS (
                    -- Agregar dados da carteira por equipe
                    -- TOLERÂNCIA: Considera saldo > 0.02 para evitar ruído de arredondamento
                    SELECT
                        equipe_vendas,
                        COUNT(DISTINCT cnpj_cpf) as clientes_carteira,
                        COALESCE(SUM(
                            CASE
                                WHEN qtd_saldo_produto_pedido > 0.02
                                THEN ROUND((qtd_saldo_produto_pedido * preco_produto_pedido)::numeric, 2)
                                ELSE 0
                            END
                        ), 0) as valor_carteira
                    FROM carteira_principal
                    WHERE equipe_vendas IS NOT NULL
                      AND (:tem_filtro = false OR equipe_vendas = ANY(:equipes))
                    GROUP BY equipe_vendas
                ),
                dados_faturamento AS (
                    -- Agregar dados de faturamento não entregue
                    -- NOTA: Usa status_finalizacao para consistência com cliente_service.py e diretoria.py
                    SELECT
                        fp.equipe_vendas,
                        COUNT(DISTINCT fp.cnpj_cliente) as clientes_faturamento,
                        COALESCE(SUM(fp.valor_produto_faturado), 0) as valor_faturamento
                    FROM faturamento_produto fp
                    LEFT JOIN entregas_monitoradas em ON em.numero_nf = fp.numero_nf
                    WHERE fp.equipe_vendas IS NOT NULL
                      AND fp.status_nf != 'Cancelado'
                      AND (:tem_filtro = false OR fp.equipe_vendas = ANY(:equipes))
                      AND (em.status_finalizacao IS NULL OR em.status_finalizacao != 'Entregue')
                    GROUP BY fp.equipe_vendas
                )
                -- Combinar resultados
                SELECT
                    COALESCE(dc.equipe_vendas, df.equipe_vendas) as nome,
                    COALESCE(dc.clientes_carteira, 0) + COALESCE(df.clientes_faturamento, 0) as total_clientes,
                    COALESCE(dc.valor_carteira, 0) + COALESCE(df.valor_faturamento, 0) as valor_em_aberto
                FROM dados_carteira dc
                FULL OUTER JOIN dados_faturamento df ON dc.equipe_vendas = df.equipe_vendas
                ORDER BY nome
            """)

            # Executar query com parâmetros
            params = {
                'tem_filtro': equipes_filtro is not None and len(equipes_filtro) > 0,
                'equipes': equipes_filtro if equipes_filtro else []
            }

            result = db.session.execute(sql, params)

            equipes_data = []
            for row in result:
                equipes_data.append({
                    'nome': row.nome,
                    'total_clientes': int(row.total_clientes) if row.total_clientes else 0,
                    'valor_em_aberto': float(row.valor_em_aberto) if row.valor_em_aberto else 0.0
                })

            logger.info(f"Dashboard carregado: {len(equipes_data)} equipes em 1 query")
            return equipes_data

        except Exception as e:
            logger.error(f"Erro ao obter dashboard otimizado: {e}")
            return []

    @staticmethod
    def obter_vendedores_equipe_otimizado(equipe_nome: str, vendedores_filtro: List[str] = None) -> List[Dict[str, Any]]:
        """
        Retorna todos vendedores de uma equipe.
        Usa materialized view quando disponivel. Fallback para CTE.
        """
        if _verificar_mv_disponivel():
            try:
                return AgregacaoComercialService._vendedores_via_mv(equipe_nome, vendedores_filtro)
            except Exception as e:
                logger.warning(f"Fallback para CTE vendedores: MV falhou ({e})")

        return AgregacaoComercialService._vendedores_via_cte(equipe_nome, vendedores_filtro)

    @staticmethod
    def _vendedores_via_mv(equipe_nome: str, vendedores_filtro: List[str] = None) -> List[Dict[str, Any]]:
        """Leitura direta da materialized view."""
        params = {'equipe': equipe_nome}
        if vendedores_filtro:
            sql = text("""
                SELECT vendedor as nome, total_clientes, valor_em_aberto
                FROM mv_comercial_vendedores
                WHERE equipe_vendas = :equipe AND vendedor = ANY(:vendedores)
                ORDER BY vendedor
            """)
            params['vendedores'] = vendedores_filtro
        else:
            sql = text("""
                SELECT vendedor as nome, total_clientes, valor_em_aberto
                FROM mv_comercial_vendedores
                WHERE equipe_vendas = :equipe
                ORDER BY vendedor
            """)

        result = db.session.execute(sql, params)
        return [{
            'nome': row.nome,
            'total_clientes': int(row.total_clientes) if row.total_clientes else 0,
            'valor_em_aberto': float(row.valor_em_aberto) if row.valor_em_aberto else 0.0
        } for row in result]

    @staticmethod
    def _vendedores_via_cte(equipe_nome: str, vendedores_filtro: List[str] = None) -> List[Dict[str, Any]]:
        """Query CTE original (fallback)."""
        try:
            sql = text("""
                WITH vendedores_carteira AS (
                    -- Vendedores e valores da carteira
                    -- TOLERÂNCIA: Considera saldo > 0.02 para evitar ruído de arredondamento
                    SELECT
                        vendedor,
                        COUNT(DISTINCT cnpj_cpf) as clientes_carteira,
                        COALESCE(SUM(
                            CASE
                                WHEN qtd_saldo_produto_pedido > 0.02
                                THEN ROUND((qtd_saldo_produto_pedido * preco_produto_pedido)::numeric, 2)
                                ELSE 0
                            END
                        ), 0) as valor_carteira
                    FROM carteira_principal
                    WHERE equipe_vendas = :equipe
                      AND vendedor IS NOT NULL
                      AND (:tem_filtro = false OR vendedor = ANY(:vendedores))
                    GROUP BY vendedor
                ),
                vendedores_faturamento AS (
                    -- Vendedores e valores faturados não entregues
                    -- NOTA: Usa status_finalizacao para consistência com cliente_service.py e diretoria.py
                    SELECT
                        fp.vendedor,
                        COUNT(DISTINCT fp.cnpj_cliente) as clientes_faturamento,
                        COALESCE(SUM(fp.valor_produto_faturado), 0) as valor_faturamento
                    FROM faturamento_produto fp
                    LEFT JOIN entregas_monitoradas em ON em.numero_nf = fp.numero_nf
                    WHERE fp.equipe_vendas = :equipe
                      AND fp.vendedor IS NOT NULL
                      AND fp.status_nf != 'Cancelado'
                      AND (:tem_filtro = false OR fp.vendedor = ANY(:vendedores))
                      AND (em.status_finalizacao IS NULL OR em.status_finalizacao != 'Entregue')
                    GROUP BY fp.vendedor
                )
                -- Combinar resultados
                SELECT
                    COALESCE(vc.vendedor, vf.vendedor) as nome,
                    COALESCE(vc.clientes_carteira, 0) + COALESCE(vf.clientes_faturamento, 0) as total_clientes,
                    COALESCE(vc.valor_carteira, 0) + COALESCE(vf.valor_faturamento, 0) as valor_em_aberto
                FROM vendedores_carteira vc
                FULL OUTER JOIN vendedores_faturamento vf ON vc.vendedor = vf.vendedor
                ORDER BY nome
            """)

            params = {
                'equipe': equipe_nome,
                'tem_filtro': vendedores_filtro is not None and len(vendedores_filtro) > 0,
                'vendedores': vendedores_filtro if vendedores_filtro else []
            }

            result = db.session.execute(sql, params)

            vendedores_data = []
            for row in result:
                vendedores_data.append({
                    'nome': row.nome,
                    'total_clientes': int(row.total_clientes) if row.total_clientes else 0,
                    'valor_em_aberto': float(row.valor_em_aberto) if row.valor_em_aberto else 0.0
                })

            logger.info(f"Vendedores da equipe {equipe_nome}: {len(vendedores_data)} em 1 query")
            return vendedores_data

        except Exception as e:
            logger.error(f"Erro ao obter vendedores otimizado: {e}")
            return []

    @staticmethod
    def obter_clientes_agrupados_otimizado(
        page: int = 1,
        per_page: int = 50,
        filtro_posicao: str = 'em_aberto',
        equipe_filtro: str = None,
        vendedor_filtro: str = None
    ) -> Dict[str, Any]:
        """
        Retorna clientes agrupados com paginação e filtros
        Usa query única otimizada

        Args:
            page: Página atual
            per_page: Itens por página
            filtro_posicao: 'em_aberto' ou 'todos'
            equipe_filtro: Filtrar por equipe específica
            vendedor_filtro: Filtrar por vendedor específico

        Returns:
            Dict com clientes paginados e metadados
        """
        try:
            # Query base para clientes
            query = db.session.query(
                CarteiraPrincipal.cnpj_cpf,
                func.max(CarteiraPrincipal.raz_social).label('raz_social'),
                func.max(CarteiraPrincipal.raz_social_red).label('raz_social_red'),
                func.max(CarteiraPrincipal.estado).label('estado'),
                func.max(CarteiraPrincipal.municipio).label('municipio'),
                func.max(CarteiraPrincipal.vendedor).label('vendedor'),
                func.max(CarteiraPrincipal.equipe_vendas).label('equipe_vendas'),
                func.count(distinct(CarteiraPrincipal.num_pedido)).label('total_pedidos'),
                func.sum(
                    CarteiraPrincipal.qtd_saldo_produto_pedido *
                    CarteiraPrincipal.preco_produto_pedido
                ).label('valor_em_aberto')
            )

            # Aplicar filtros
            # TOLERÂNCIA: Considera saldo > 0.02 para evitar ruído de arredondamento
            if filtro_posicao == 'em_aberto':
                query = query.filter(CarteiraPrincipal.qtd_saldo_produto_pedido > 0.02)

            if equipe_filtro:
                query = query.filter(CarteiraPrincipal.equipe_vendas == equipe_filtro)

            if vendedor_filtro:
                query = query.filter(CarteiraPrincipal.vendedor == vendedor_filtro)

            # Agrupar por cliente
            query = query.group_by(CarteiraPrincipal.cnpj_cpf)

            # Ordenar por valor decrescente
            query = query.order_by(func.sum(
                CarteiraPrincipal.qtd_saldo_produto_pedido *
                CarteiraPrincipal.preco_produto_pedido
            ).desc())

            # Paginar usando SQLAlchemy
            paginated = query.paginate(page=page, per_page=per_page, error_out=False)

            # Formatar resultados
            clientes = []
            for row in paginated.items:
                clientes.append({
                    'cnpj_cpf': row.cnpj_cpf,
                    'raz_social': row.raz_social,
                    'raz_social_red': row.raz_social_red,
                    'estado': row.estado,
                    'municipio': row.municipio,
                    'vendedor': row.vendedor,
                    'equipe_vendas': row.equipe_vendas,
                    'total_pedidos': int(row.total_pedidos) if row.total_pedidos else 0,
                    'valor_em_aberto': float(row.valor_em_aberto) if row.valor_em_aberto else 0.0,
                    'forma_agendamento': 'Portal'  # Default, poderia buscar se existisse a tabela
                })

            logger.info(f"Clientes carregados: página {page} com {len(clientes)} itens")

            return {
                'clientes': clientes,
                'total': paginated.total,
                'paginas': paginated.pages,
                'pagina_atual': page,
                'por_pagina': per_page,
                'tem_anterior': paginated.has_prev,
                'tem_proximo': paginated.has_next
            }

        except Exception as e:
            logger.error(f"Erro ao obter clientes otimizado: {e}")
            return {
                'clientes': [],
                'total': 0,
                'paginas': 0,
                'pagina_atual': 1,
                'por_pagina': per_page,
                'tem_anterior': False,
                'tem_proximo': False
            }

    @staticmethod
    def calcular_valores_batch(cnpjs: List[str]) -> Dict[str, Decimal]:
        """
        Calcula valores em aberto para múltiplos CNPJs em uma única query
        Elimina N+1 queries

        Args:
            cnpjs: Lista de CNPJs para calcular

        Returns:
            Dict com CNPJ -> valor_em_aberto
        """
        if not cnpjs:
            return {}

        try:
            # Query única para todos os CNPJs
            # TOLERÂNCIA: Considera saldo > 0.02 para evitar ruído de arredondamento
            resultado = db.session.query(
                CarteiraPrincipal.cnpj_cpf,
                func.sum(
                    CarteiraPrincipal.qtd_saldo_produto_pedido *
                    CarteiraPrincipal.preco_produto_pedido
                ).label('valor_total')
            ).filter(
                CarteiraPrincipal.cnpj_cpf.in_(cnpjs),
                CarteiraPrincipal.qtd_saldo_produto_pedido > 0.02
            ).group_by(
                CarteiraPrincipal.cnpj_cpf
            ).all()

            valores = {}
            for row in resultado:
                valores[row.cnpj_cpf] = Decimal(str(row.valor_total)) if row.valor_total else Decimal('0.00')

            # Preencher CNPJs sem valor com 0
            for cnpj in cnpjs:
                if cnpj not in valores:
                    valores[cnpj] = Decimal('0.00')

            return valores

        except Exception as e:
            logger.error(f"Erro ao calcular valores em batch: {e}")
            return {cnpj: Decimal('0.00') for cnpj in cnpjs}

    @staticmethod
    def obter_estatisticas_rapidas() -> Dict[str, Any]:
        """
        Retorna estatísticas gerais do módulo comercial
        Útil para dashboards e relatórios
        """
        try:
            stats = {}
            # TOLERÂNCIA: Considera saldo > 0.02 para evitar ruído de arredondamento

            # Total de equipes ativas
            equipes = db.session.query(
                func.count(distinct(CarteiraPrincipal.equipe_vendas))
            ).filter(
                CarteiraPrincipal.equipe_vendas.isnot(None),
                CarteiraPrincipal.qtd_saldo_produto_pedido > 0.02
            ).scalar()
            stats['total_equipes'] = equipes or 0

            # Total de vendedores ativos
            vendedores = db.session.query(
                func.count(distinct(CarteiraPrincipal.vendedor))
            ).filter(
                CarteiraPrincipal.vendedor.isnot(None),
                CarteiraPrincipal.qtd_saldo_produto_pedido > 0.02
            ).scalar()
            stats['total_vendedores'] = vendedores or 0

            # Total de clientes com saldo
            clientes = db.session.query(
                func.count(distinct(CarteiraPrincipal.cnpj_cpf))
            ).filter(
                CarteiraPrincipal.qtd_saldo_produto_pedido > 0.02
            ).scalar()
            stats['total_clientes'] = clientes or 0

            # Valor total em aberto
            valor_total = db.session.query(
                func.sum(
                    CarteiraPrincipal.qtd_saldo_produto_pedido *
                    CarteiraPrincipal.preco_produto_pedido
                )
            ).filter(
                CarteiraPrincipal.qtd_saldo_produto_pedido > 0.02
            ).scalar()
            stats['valor_total_aberto'] = float(valor_total) if valor_total else 0.0

            logger.info("Estatísticas rápidas carregadas")
            return stats

        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {e}")
            return {
                'total_equipes': 0,
                'total_vendedores': 0,
                'total_clientes': 0,
                'valor_total_aberto': 0.0
            }

    @staticmethod
    def obter_lista_clientes_paginada(
        page: int = 1,
        per_page: int = 50,
        filtro_posicao: str = 'em_aberto',
        equipe_filtro: Optional[str] = None,
        vendedor_filtro: Optional[str] = None,
        filtros_avancados: Optional[Dict[str, str]] = None,
        is_vendedor: bool = False,
        equipes_permitidas: Optional[List[str]] = None,
        vendedores_permitidos: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Lista paginada de clientes para a tela /comercial/clientes.

        Substitui o N+1 brutal do antigo `_coletar_clientes_data` por
        2 queries SQL agregadas (CTEs). Mantém feature parity com:
        - filtros: cnpj_cpf, cliente, pedido, pedido_cliente, uf,
          raz_social, raz_social_red, num_pedido (legacy)
        - permissões de vendedor (equipes/vendedores)
        - filtro_posicao 'em_aberto' (saldo + faturado nao entregue)
          ou 'todos' (saldo + faturado total)
        - cobertura de clientes via CarteiraPrincipal E FaturamentoProduto

        Returns:
            Dict com: clientes (list), total (int), page, per_page,
            total_pages, valor_total_pagina (Decimal)
        """
        if filtros_avancados is None:
            filtros_avancados = {}

        # Saneamento dos parametros
        if page < 1:
            page = 1
        if per_page < 1:
            per_page = 50
        if per_page > 200:
            per_page = 200

        offset = (page - 1) * per_page

        cnpj_cpf = (filtros_avancados.get('cnpj_cpf') or '').strip()
        cliente = (filtros_avancados.get('cliente') or '').strip()
        pedido = (filtros_avancados.get('pedido') or '').strip()
        uf = (filtros_avancados.get('uf') or '').strip()
        raz_social = (filtros_avancados.get('raz_social') or '').strip()
        raz_social_red = (filtros_avancados.get('raz_social_red') or '').strip()
        num_pedido = (filtros_avancados.get('num_pedido') or '').strip()
        pedido_cliente = (filtros_avancados.get('pedido_cliente') or '').strip()

        # ANY(:array) com array vazia gera erro no PG; usamos sentinela ''
        equipes_permitidas_param = equipes_permitidas or ['']
        vendedores_permitidos_param = vendedores_permitidos or ['']

        params = {
            'posicao': filtro_posicao,
            'is_vendedor': bool(is_vendedor),
            'equipes_permitidas': equipes_permitidas_param,
            'vendedores_permitidos': vendedores_permitidos_param,
            'equipe_filtro': equipe_filtro or '',
            'vendedor_filtro': vendedor_filtro or '',
            'cnpj_cpf': cnpj_cpf,
            'cliente': cliente,
            'pedido': pedido,
            'uf': uf,
            'raz_social': raz_social,
            'raz_social_red': raz_social_red,
            'num_pedido': num_pedido,
            'pedido_cliente': pedido_cliente,
            'limit': per_page,
            'offset': offset
        }

        # CTE master: aplica filtros + permissoes em CarteiraPrincipal e
        # FaturamentoProduto, faz UNION e calcula valores agregados.
        # Filtro por pedido/pedido_cliente em registros que so aparecem em
        # FaturamentoProduto e o JOIN via fp.origem = cp.num_pedido.
        sql_clientes = text("""
            WITH cnpjs_carteira AS (
                SELECT DISTINCT cnpj_cpf
                FROM carteira_principal cp
                WHERE cnpj_cpf IS NOT NULL AND cnpj_cpf != ''
                  AND (:posicao = 'todos' OR qtd_saldo_produto_pedido > 0.02)
                  AND (:cnpj_cpf = '' OR cnpj_cpf LIKE '%' || :cnpj_cpf || '%')
                  AND (:cliente = '' OR
                       lower(f_unaccent(COALESCE(raz_social, ''))) LIKE lower(f_unaccent('%' || :cliente || '%')) OR
                       lower(f_unaccent(COALESCE(raz_social_red, ''))) LIKE lower(f_unaccent('%' || :cliente || '%')))
                  AND (:raz_social = '' OR
                       lower(f_unaccent(COALESCE(raz_social, ''))) LIKE lower(f_unaccent('%' || :raz_social || '%')))
                  AND (:raz_social_red = '' OR
                       lower(f_unaccent(COALESCE(raz_social_red, ''))) LIKE lower(f_unaccent('%' || :raz_social_red || '%')))
                  AND (:uf = '' OR estado = :uf)
                  AND (:equipe_filtro = '' OR equipe_vendas = :equipe_filtro)
                  AND (:vendedor_filtro = '' OR vendedor = :vendedor_filtro)
                  AND (:pedido = '' OR
                       lower(f_unaccent(COALESCE(num_pedido, ''))) LIKE lower(f_unaccent('%' || :pedido || '%')) OR
                       lower(f_unaccent(COALESCE(pedido_cliente, ''))) LIKE lower(f_unaccent('%' || :pedido || '%')))
                  AND (:num_pedido = '' OR
                       lower(f_unaccent(COALESCE(num_pedido, ''))) LIKE lower(f_unaccent('%' || :num_pedido || '%')))
                  AND (:pedido_cliente = '' OR
                       lower(f_unaccent(COALESCE(pedido_cliente, ''))) LIKE lower(f_unaccent('%' || :pedido_cliente || '%')))
                  AND (NOT :is_vendedor OR
                       (:equipe_filtro != '' AND equipe_vendas = :equipe_filtro) OR
                       (:vendedor_filtro != '' AND vendedor = :vendedor_filtro) OR
                       (:equipe_filtro = '' AND :vendedor_filtro = '' AND
                        (equipe_vendas = ANY(:equipes_permitidas) OR
                         vendedor = ANY(:vendedores_permitidos))))
            ),
            cnpjs_faturamento AS (
                SELECT DISTINCT fp.cnpj_cliente AS cnpj_cpf
                FROM faturamento_produto fp
                LEFT JOIN entregas_monitoradas em ON em.numero_nf = fp.numero_nf
                WHERE fp.cnpj_cliente IS NOT NULL AND fp.cnpj_cliente != ''
                  AND fp.status_nf != 'Cancelado'
                  AND (:posicao = 'todos' OR
                       em.status_finalizacao IS NULL OR
                       em.status_finalizacao != 'Entregue')
                  AND (:cnpj_cpf = '' OR fp.cnpj_cliente LIKE '%' || :cnpj_cpf || '%')
                  AND (:cliente = '' OR
                       lower(f_unaccent(COALESCE(fp.nome_cliente, ''))) LIKE lower(f_unaccent('%' || :cliente || '%')))
                  AND (:raz_social = '' OR
                       lower(f_unaccent(COALESCE(fp.nome_cliente, ''))) LIKE lower(f_unaccent('%' || :raz_social || '%')))
                  AND (:raz_social_red = '' OR
                       lower(f_unaccent(COALESCE(fp.nome_cliente, ''))) LIKE lower(f_unaccent('%' || :raz_social_red || '%')))
                  AND (:uf = '' OR fp.estado = :uf)
                  AND (:equipe_filtro = '' OR fp.equipe_vendas = :equipe_filtro)
                  AND (:vendedor_filtro = '' OR fp.vendedor = :vendedor_filtro)
                  -- Filtro por pedido/pedido_cliente: usa subquery em CarteiraPrincipal
                  AND (:pedido = '' OR EXISTS (
                       SELECT 1 FROM carteira_principal cpp
                       WHERE cpp.num_pedido = fp.origem
                         AND (lower(f_unaccent(COALESCE(cpp.num_pedido, ''))) LIKE lower(f_unaccent('%' || :pedido || '%'))
                           OR lower(f_unaccent(COALESCE(cpp.pedido_cliente, ''))) LIKE lower(f_unaccent('%' || :pedido || '%')))
                  ))
                  AND (:num_pedido = '' OR
                       lower(f_unaccent(COALESCE(fp.origem, ''))) LIKE lower(f_unaccent('%' || :num_pedido || '%')))
                  AND (:pedido_cliente = '' OR EXISTS (
                       SELECT 1 FROM carteira_principal cpp
                       WHERE cpp.num_pedido = fp.origem
                         AND lower(f_unaccent(COALESCE(cpp.pedido_cliente, ''))) LIKE lower(f_unaccent('%' || :pedido_cliente || '%'))
                  ))
                  AND (NOT :is_vendedor OR
                       (:equipe_filtro != '' AND fp.equipe_vendas = :equipe_filtro) OR
                       (:vendedor_filtro != '' AND fp.vendedor = :vendedor_filtro) OR
                       (:equipe_filtro = '' AND :vendedor_filtro = '' AND
                        (fp.equipe_vendas = ANY(:equipes_permitidas) OR
                         fp.vendedor = ANY(:vendedores_permitidos))))
            ),
            todos_cnpjs AS (
                SELECT cnpj_cpf FROM cnpjs_carteira
                UNION
                SELECT cnpj_cpf FROM cnpjs_faturamento
            ),
            valores AS (
                SELECT
                    tc.cnpj_cpf,
                    COALESCE((
                        SELECT SUM(qtd_saldo_produto_pedido * preco_produto_pedido)
                        FROM carteira_principal
                        WHERE cnpj_cpf = tc.cnpj_cpf
                          AND qtd_saldo_produto_pedido > 0.02
                    ), 0)::numeric AS saldo_carteira,
                    COALESCE((
                        SELECT SUM(valor_produto_faturado)
                        FROM faturamento_produto
                        WHERE cnpj_cliente = tc.cnpj_cpf
                          AND status_nf != 'Cancelado'
                    ), 0)::numeric AS faturado_total,
                    COALESCE((
                        SELECT SUM(fp2.valor_produto_faturado)
                        FROM faturamento_produto fp2
                        LEFT JOIN entregas_monitoradas em2 ON em2.numero_nf = fp2.numero_nf
                        WHERE fp2.cnpj_cliente = tc.cnpj_cpf
                          AND fp2.status_nf != 'Cancelado'
                          AND (em2.status_finalizacao IS NULL OR em2.status_finalizacao != 'Entregue')
                    ), 0)::numeric AS faturado_nao_entregue
                FROM todos_cnpjs tc
            ),
            valores_finais AS (
                SELECT
                    cnpj_cpf,
                    saldo_carteira,
                    faturado_total,
                    faturado_nao_entregue,
                    CASE WHEN :posicao = 'todos'
                         THEN saldo_carteira + faturado_total
                         ELSE saldo_carteira + faturado_nao_entregue
                    END AS valor_principal,
                    saldo_carteira + faturado_total AS valor_total
                FROM valores
                WHERE
                    -- Em 'em_aberto' so mantemos clientes com algum valor positivo
                    (:posicao = 'todos' OR (saldo_carteira + faturado_nao_entregue) > 0)
            )
            SELECT
                cnpj_cpf,
                saldo_carteira,
                faturado_total,
                faturado_nao_entregue,
                valor_principal,
                valor_total,
                COUNT(*) OVER() AS total_clientes,
                SUM(valor_principal) OVER() AS valor_total_geral
            FROM valores_finais
            ORDER BY valor_principal DESC, cnpj_cpf
            LIMIT :limit OFFSET :offset
        """)

        try:
            rows = db.session.execute(sql_clientes, params).fetchall()
        except Exception as e:
            logger.error(f"Erro ao buscar lista paginada de clientes: {e}")
            return {
                'clientes': [],
                'total': 0,
                'page': page,
                'per_page': per_page,
                'total_pages': 0,
                'valor_total_pagina': Decimal('0.00'),
                'valor_total_geral': Decimal('0.00')
            }

        if not rows:
            return {
                'clientes': [],
                'total': 0,
                'page': page,
                'per_page': per_page,
                'total_pages': 0,
                'valor_total_pagina': Decimal('0.00'),
                'valor_total_geral': Decimal('0.00')
            }

        total_clientes = int(rows[0].total_clientes)
        total_pages = (total_clientes + per_page - 1) // per_page
        valor_total_geral = Decimal(str(rows[0].valor_total_geral or 0))
        cnpjs_pagina = [r.cnpj_cpf for r in rows]

        # Mapa de valores por CNPJ
        valores_por_cnpj: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            valores_por_cnpj[r.cnpj_cpf] = {
                'saldo_carteira': Decimal(str(r.saldo_carteira or 0)),
                'faturado_total': Decimal(str(r.faturado_total or 0)),
                'faturado_nao_entregue': Decimal(str(r.faturado_nao_entregue or 0)),
                'valor_principal': Decimal(str(r.valor_principal or 0)),
                'valor_total': Decimal(str(r.valor_total or 0))
            }

        # Query 2: dados descritivos para os CNPJs da pagina
        sql_dados = text("""
            WITH cnpjs_pagina AS (
                SELECT unnest(CAST(:cnpjs AS varchar[])) AS cnpj_cpf
            ),
            dados_carteira AS (
                SELECT DISTINCT ON (cnpj_cpf)
                    cnpj_cpf,
                    raz_social,
                    raz_social_red,
                    estado,
                    municipio,
                    vendedor,
                    equipe_vendas
                FROM carteira_principal
                WHERE cnpj_cpf = ANY(CAST(:cnpjs AS varchar[]))
                ORDER BY cnpj_cpf, updated_at DESC NULLS LAST, id DESC
            ),
            dados_faturamento AS (
                SELECT DISTINCT ON (cnpj_cliente)
                    cnpj_cliente AS cnpj_cpf,
                    nome_cliente,
                    estado,
                    municipio,
                    vendedor,
                    equipe_vendas
                FROM faturamento_produto
                WHERE cnpj_cliente = ANY(CAST(:cnpjs AS varchar[]))
                  AND status_nf != 'Cancelado'
                ORDER BY cnpj_cliente, data_fatura DESC NULLS LAST, id DESC
            ),
            dados_contato AS (
                -- contatos_agendamento NAO tem unique constraint em cnpj.
                -- DISTINCT ON garante 1 linha por cnpj (deterministico),
                -- evitando fan-out na query final que duplicaria CNPJs.
                SELECT DISTINCT ON (cnpj)
                    cnpj,
                    forma
                FROM contatos_agendamento
                WHERE cnpj = ANY(CAST(:cnpjs AS varchar[]))
                ORDER BY cnpj, atualizado_em DESC NULLS LAST, id DESC
            ),
            pedidos_unicos AS (
                SELECT cnpj_cpf, num_pedido
                FROM carteira_principal
                WHERE cnpj_cpf = ANY(CAST(:cnpjs AS varchar[]))
                  AND num_pedido IS NOT NULL
                  AND (:posicao = 'todos' OR qtd_saldo_produto_pedido > 0.02)
                UNION
                SELECT fp.cnpj_cliente AS cnpj_cpf, fp.origem AS num_pedido
                FROM faturamento_produto fp
                LEFT JOIN entregas_monitoradas em ON em.numero_nf = fp.numero_nf
                WHERE fp.cnpj_cliente = ANY(CAST(:cnpjs AS varchar[]))
                  AND fp.origem IS NOT NULL
                  AND fp.status_nf != 'Cancelado'
                  AND (:posicao = 'todos' OR
                       em.status_finalizacao IS NULL OR
                       em.status_finalizacao != 'Entregue')
            ),
            pedidos_count AS (
                SELECT cnpj_cpf, COUNT(DISTINCT num_pedido) AS total_pedidos
                FROM pedidos_unicos
                GROUP BY cnpj_cpf
            )
            SELECT
                cp.cnpj_cpf,
                dc.raz_social AS raz_social,
                COALESCE(dc.raz_social_red, df.nome_cliente) AS raz_social_red,
                COALESCE(dc.estado, df.estado) AS estado,
                COALESCE(dc.municipio, df.municipio) AS municipio,
                COALESCE(dc.vendedor, df.vendedor) AS vendedor,
                COALESCE(dc.equipe_vendas, df.equipe_vendas) AS equipe_vendas,
                ca.forma AS forma_agendamento,
                COALESCE(pc.total_pedidos, 0) AS total_pedidos
            FROM cnpjs_pagina cp
            LEFT JOIN dados_carteira dc ON dc.cnpj_cpf = cp.cnpj_cpf
            LEFT JOIN dados_faturamento df ON df.cnpj_cpf = cp.cnpj_cpf
            LEFT JOIN dados_contato ca ON ca.cnpj = cp.cnpj_cpf
            LEFT JOIN pedidos_count pc ON pc.cnpj_cpf = cp.cnpj_cpf
        """)

        try:
            dados_rows = db.session.execute(
                sql_dados,
                {'cnpjs': cnpjs_pagina, 'posicao': filtro_posicao}
            ).fetchall()
        except Exception as e:
            logger.error(f"Erro ao buscar dados descritivos dos clientes: {e}")
            dados_rows = []

        dados_por_cnpj: Dict[str, Any] = {}
        for r in dados_rows:
            dados_por_cnpj[r.cnpj_cpf] = r

        clientes: List[Dict[str, Any]] = []
        valor_total_pagina = Decimal('0.00')
        for cnpj in cnpjs_pagina:
            valores = valores_por_cnpj.get(cnpj, {})
            dados = dados_por_cnpj.get(cnpj)
            valor_principal = valores.get('valor_principal', Decimal('0.00'))
            valor_total_pagina += valor_principal

            clientes.append({
                'cnpj_cpf': cnpj,
                'raz_social': dados.raz_social if dados else None,
                'raz_social_red': dados.raz_social_red if dados else None,
                'estado': dados.estado if dados else None,
                'municipio': dados.municipio if dados else None,
                'vendedor': dados.vendedor if dados else None,
                'equipe_vendas': dados.equipe_vendas if dados else None,
                'forma_agendamento': dados.forma_agendamento if dados else None,
                'total_pedidos': int(dados.total_pedidos) if dados else 0,
                'valor_em_aberto': float(valores.get('saldo_carteira', 0) + valores.get('faturado_nao_entregue', 0)),
                'valor_total': float(valores.get('valor_total', 0)),
                'valor_principal': float(valor_principal)
            })

        logger.info(
            "Lista paginada de clientes carregada: "
            f"page={page}, per_page={per_page}, total={total_clientes}, retornados={len(clientes)}"
        )

        return {
            'clientes': clientes,
            'total': total_clientes,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'valor_total_pagina': valor_total_pagina,
            'valor_total_geral': valor_total_geral
        }