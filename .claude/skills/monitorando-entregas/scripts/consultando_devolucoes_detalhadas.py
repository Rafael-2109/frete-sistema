#!/usr/bin/env python3
"""
Script para consultar devolucoes detalhadas com entity resolution.

Uso:
    python consultando_devolucoes_detalhadas.py --cliente "Sendas"
    python consultando_devolucoes_detalhadas.py --produto "palmito" --limite 30
    python consultando_devolucoes_detalhadas.py --ranking --limite 10
    python consultando_devolucoes_detalhadas.py --custo --de 2025-01-01 --ate 2025-12-31
"""

import argparse
import json
import sys
import os
from datetime import date, datetime
from decimal import Decimal

# Adiciona o diretorio raiz ao path para importar os modulos do app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))


class DecimalEncoder(json.JSONEncoder):
    """Encoder para serializar Decimal e datas para JSON"""
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        if isinstance(o, (date, datetime)):
            return o.isoformat()
        return super().default(o)


def consultar_por_cliente(cliente: str, data_de: str = None, data_ate: str = None,
                          incluir_custo: bool = False, limite: int = 50) -> dict:
    """
    Consulta historico de devolucoes por cliente.

    Args:
        cliente: Nome do cliente (LIKE no nome_emitente)
        data_de: Data inicio (YYYY-MM-DD)
        data_ate: Data fim (YYYY-MM-DD)
        incluir_custo: Se True, busca custos em despesas_extras
        limite: Max registros

    Returns:
        dict com sucesso, resumo e lista de NFDs
    """
    from app import create_app, db
    from sqlalchemy import text, bindparam

    app = create_app()
    with app.app_context():
        try:
            # Query base: NFDs do cliente
            sql = """
                SELECT
                    nfd.id,
                    nfd.numero_nfd,
                    nfd.serie_nfd,
                    nfd.nome_emitente,
                    nfd.cnpj_emitente,
                    nfd.data_emissao,
                    nfd.data_registro,
                    nfd.valor_total,
                    nfd.status,
                    nfd.motivo,
                    nfd.numero_nf_venda,
                    COUNT(DISTINCT nfdl.id) as total_linhas
                FROM nf_devolucao nfd
                LEFT JOIN nf_devolucao_linha nfdl ON nfdl.nf_devolucao_id = nfd.id
                WHERE nfd.nome_emitente ILIKE :cliente
            """
            params = {'cliente': f"%{cliente}%"}

            if data_de:
                sql += " AND nfd.data_registro >= :data_de"
                params['data_de'] = data_de
            if data_ate:
                sql += " AND nfd.data_registro <= :data_ate"
                params['data_ate'] = data_ate

            sql += """
                GROUP BY nfd.id
                ORDER BY nfd.data_registro DESC
                LIMIT :limite
            """
            params['limite'] = limite

            result = db.session.execute(text(sql), params)
            nfds = [dict(zip(result.keys(), row)) for row in result.fetchall()]

            # Total de NFDs e valor total
            sql_totais = """
                SELECT
                    COUNT(DISTINCT nfd.id) as total_nfds,
                    COALESCE(SUM(nfd.valor_total), 0) as valor_total_devolucoes
                FROM nf_devolucao nfd
                WHERE nfd.nome_emitente ILIKE :cliente
            """
            if data_de:
                sql_totais += " AND nfd.data_registro >= :data_de"
            if data_ate:
                sql_totais += " AND nfd.data_registro <= :data_ate"

            totais_result = db.session.execute(text(sql_totais), params)
            totais = dict(zip(totais_result.keys(), totais_result.fetchone()))

            # Buscar custos de devolucao se solicitado
            custo_total = None
            if incluir_custo and nfds:
                nfd_ids = tuple(nfd['id'] for nfd in nfds)
                sql_custo = """
                    SELECT COALESCE(SUM(de.valor_despesa), 0) as custo_total
                    FROM despesas_extras de
                    WHERE de.tipo_despesa = 'DEVOLUCAO'
                    AND de.nfd_id IN :nfd_ids
                """
                custo_result = db.session.execute(
                    text(sql_custo).bindparams(bindparam('nfd_ids', expanding=True)),
                    {'nfd_ids': list(nfd_ids)}
                )
                custo_total = custo_result.scalar()

            return {
                "sucesso": True,
                "modo": "cliente",
                "resumo": {
                    "mensagem": f"Historico de devolucoes de {totais['total_nfds']} NFDs do cliente '{cliente}'",
                    "total_nfds": totais['total_nfds'],
                    "exibindo": len(nfds),
                    "valor_total_devolucoes": totais['valor_total_devolucoes'],
                    "custo_total": custo_total if incluir_custo else None,
                    "cliente": cliente,
                    "periodo": {
                        "de": data_de,
                        "ate": data_ate
                    }
                },
                "nfds": nfds
            }

        except Exception as e:
            return {
                "sucesso": False,
                "erro": str(e),
                "modo": "cliente",
                "nfds": []
            }


def consultar_por_produto(produto: str, data_de: str = None, data_ate: str = None,
                         limite: int = 50) -> dict:
    """
    Consulta produtos devolvidos (LIKE no nome do produto).

    Args:
        produto: Nome do produto (LIKE)
        data_de: Data inicio
        data_ate: Data fim
        limite: Max registros

    Returns:
        dict com sucesso, resumo e lista de devolucoes
    """
    from app import create_app, db
    from sqlalchemy import text

    app = create_app()
    with app.app_context():
        try:
            sql = """
                SELECT
                    nfdl.id,
                    nfdl.descricao_produto_cliente,
                    nfdl.descricao_produto_interno,
                    nfdl.codigo_produto_interno,
                    nfdl.quantidade,
                    nfdl.unidade_medida,
                    nfdl.valor_total,
                    nfd.numero_nfd,
                    nfd.nome_emitente,
                    nfd.data_registro,
                    nfd.motivo
                FROM nf_devolucao_linha nfdl
                JOIN nf_devolucao nfd ON nfd.id = nfdl.nf_devolucao_id
                WHERE (
                    nfdl.descricao_produto_cliente ILIKE :produto
                    OR nfdl.descricao_produto_interno ILIKE :produto
                )
            """
            params = {'produto': f"%{produto}%"}

            if data_de:
                sql += " AND nfd.data_registro >= :data_de"
                params['data_de'] = data_de
            if data_ate:
                sql += " AND nfd.data_registro <= :data_ate"
                params['data_ate'] = data_ate

            sql += " ORDER BY nfd.data_registro DESC LIMIT :limite"
            params['limite'] = limite

            result = db.session.execute(text(sql), params)
            linhas = [dict(zip(result.keys(), row)) for row in result.fetchall()]

            # Totais
            sql_totais = """
                SELECT
                    COUNT(*) as total_devolucoes,
                    COALESCE(SUM(nfdl.quantidade), 0) as qtd_total,
                    COUNT(DISTINCT nfd.nome_emitente) as total_clientes
                FROM nf_devolucao_linha nfdl
                JOIN nf_devolucao nfd ON nfd.id = nfdl.nf_devolucao_id
                WHERE (
                    nfdl.descricao_produto_cliente ILIKE :produto
                    OR nfdl.descricao_produto_interno ILIKE :produto
                )
            """
            if data_de:
                sql_totais += " AND nfd.data_registro >= :data_de"
            if data_ate:
                sql_totais += " AND nfd.data_registro <= :data_ate"

            totais_result = db.session.execute(text(sql_totais), params)
            totais = dict(zip(totais_result.keys(), totais_result.fetchone()))

            return {
                "sucesso": True,
                "modo": "produto",
                "resumo": {
                    "mensagem": f"Produto '{produto}' devolvido {totais['total_devolucoes']} vezes por {totais['total_clientes']} clientes",
                    "total_devolucoes": totais['total_devolucoes'],
                    "qtd_total": totais['qtd_total'],
                    "total_clientes": totais['total_clientes'],
                    "exibindo": len(linhas),
                    "produto": produto,
                    "periodo": {
                        "de": data_de,
                        "ate": data_ate
                    }
                },
                "linhas": linhas
            }

        except Exception as e:
            return {
                "sucesso": False,
                "erro": str(e),
                "modo": "produto",
                "linhas": []
            }


def consultar_ranking_produtos(data_de: str = None, data_ate: str = None,
                              limite: int = 10, ordenar_por: str = 'ocorrencias') -> dict:
    """
    Top N produtos mais devolvidos.

    Args:
        data_de: Data inicio
        data_ate: Data fim
        limite: Top N
        ordenar_por: 'ocorrencias' (count) ou 'quantidade' (sum qtd)

    Returns:
        dict com sucesso, resumo e ranking
    """
    from app import create_app, db
    from sqlalchemy import text

    app = create_app()
    with app.app_context():
        try:
            # Decisao de ordenacao
            order_clause = "total_ocorrencias DESC" if ordenar_por == 'ocorrencias' else "qtd_total DESC"

            sql = """
                SELECT
                    COALESCE(nfdl.codigo_produto_interno, nfdl.descricao_produto_cliente) as produto_referencia,
                    nfdl.descricao_produto_interno,
                    nfdl.descricao_produto_cliente,
                    COUNT(*) as total_ocorrencias,
                    COALESCE(SUM(nfdl.quantidade), 0) as qtd_total,
                    COUNT(DISTINCT nfd.id) as total_nfds,
                    COUNT(DISTINCT nfd.nome_emitente) as total_clientes
                FROM nf_devolucao_linha nfdl
                JOIN nf_devolucao nfd ON nfd.id = nfdl.nf_devolucao_id
                WHERE 1=1
            """
            params = {}

            if data_de:
                sql += " AND nfd.data_registro >= :data_de"
                params['data_de'] = data_de
            if data_ate:
                sql += " AND nfd.data_registro <= :data_ate"
                params['data_ate'] = data_ate

            sql += f"""
                GROUP BY
                    COALESCE(nfdl.codigo_produto_interno, nfdl.descricao_produto_cliente),
                    nfdl.descricao_produto_interno,
                    nfdl.descricao_produto_cliente
                ORDER BY {order_clause}
                LIMIT :limite
            """
            params['limite'] = limite

            result = db.session.execute(text(sql), params)
            ranking = [dict(zip(result.keys(), row)) for row in result.fetchall()]

            return {
                "sucesso": True,
                "modo": "ranking",
                "resumo": {
                    "mensagem": f"Top {len(ranking)} produtos mais devolvidos (ordenado por {ordenar_por})",
                    "criterio": ordenar_por,
                    "total_produtos": len(ranking),
                    "periodo": {
                        "de": data_de,
                        "ate": data_ate
                    }
                },
                "ranking": ranking
            }

        except Exception as e:
            return {
                "sucesso": False,
                "erro": str(e),
                "modo": "ranking",
                "ranking": []
            }


def consultar_custo_total(data_de: str = None, data_ate: str = None) -> dict:
    """
    Total geral de custos de devolucao (via despesas_extras).

    Args:
        data_de: Data inicio
        data_ate: Data fim

    Returns:
        dict com sucesso, custo total e breakdown
    """
    from app import create_app, db
    from sqlalchemy import text

    app = create_app()
    with app.app_context():
        try:
            # Query de custos
            sql = """
                SELECT
                    COUNT(*) as total_despesas,
                    COALESCE(SUM(de.valor_despesa), 0) as custo_total,
                    COUNT(DISTINCT de.nfd_id) as total_nfds_com_custo
                FROM despesas_extras de
                WHERE de.tipo_despesa = 'DEVOLUCAO'
            """
            params = {}

            if data_de:
                sql += " AND de.criado_em >= :data_de"
                params['data_de'] = data_de
            if data_ate:
                sql += " AND de.criado_em <= :data_ate"
                params['data_ate'] = data_ate

            result = db.session.execute(text(sql), params)
            totais = dict(zip(result.keys(), result.fetchone()))

            # Breakdown por mes
            sql_breakdown = """
                SELECT
                    TO_CHAR(de.criado_em, 'YYYY-MM') as mes,
                    COUNT(*) as qtd_despesas,
                    COALESCE(SUM(de.valor_despesa), 0) as custo_mes
                FROM despesas_extras de
                WHERE de.tipo_despesa = 'DEVOLUCAO'
            """
            if data_de:
                sql_breakdown += " AND de.criado_em >= :data_de"
            if data_ate:
                sql_breakdown += " AND de.criado_em <= :data_ate"

            sql_breakdown += """
                GROUP BY TO_CHAR(de.criado_em, 'YYYY-MM')
                ORDER BY mes DESC
            """

            breakdown_result = db.session.execute(text(sql_breakdown), params)
            breakdown = [dict(zip(breakdown_result.keys(), row)) for row in breakdown_result.fetchall()]

            return {
                "sucesso": True,
                "modo": "custo",
                "resumo": {
                    "mensagem": f"Custo total de devolucoes: R$ {totais['custo_total']:.2f}",
                    "custo_total": totais['custo_total'],
                    "total_despesas": totais['total_despesas'],
                    "total_nfds_com_custo": totais['total_nfds_com_custo'],
                    "periodo": {
                        "de": data_de,
                        "ate": data_ate
                    }
                },
                "breakdown_mensal": breakdown
            }

        except Exception as e:
            return {
                "sucesso": False,
                "erro": str(e),
                "modo": "custo",
                "breakdown_mensal": []
            }


def main():
    parser = argparse.ArgumentParser(description='Consulta devolucoes detalhadas')

    # Modos de operacao (mutualmente exclusivos)
    grupo_modo = parser.add_mutually_exclusive_group(required=True)
    grupo_modo.add_argument('--cliente', type=str, help='Historico de devolucoes por cliente (LIKE no nome)')
    grupo_modo.add_argument('--produto', type=str, help='Produtos devolvidos (LIKE no nome do produto)')
    grupo_modo.add_argument('--ranking', action='store_true', help='Top N produtos devolvidos')
    grupo_modo.add_argument('--custo', action='store_true', help='Custo total de devolucoes')

    # Filtros gerais
    parser.add_argument('--de', type=str, dest='data_de', help='Data inicio (YYYY-MM-DD)')
    parser.add_argument('--ate', type=str, dest='data_ate', help='Data fim (YYYY-MM-DD)')
    parser.add_argument('--limite', type=int, default=50, help='Max resultados (default: 50)')

    # Opcoes especificas
    parser.add_argument('--incluir-custo', action='store_true', dest='incluir_custo',
                       help='Incluir custo de devolucao (apenas com --cliente)')
    parser.add_argument('--ordenar-por', choices=['ocorrencias', 'quantidade'], default='ocorrencias',
                       help='Criterio de ordenacao do ranking (default: ocorrencias)')

    args = parser.parse_args()

    # Dispatch
    if args.cliente:
        resultado = consultar_por_cliente(
            cliente=args.cliente,
            data_de=args.data_de,
            data_ate=args.data_ate,
            incluir_custo=args.incluir_custo,
            limite=args.limite
        )
    elif args.produto:
        resultado = consultar_por_produto(
            produto=args.produto,
            data_de=args.data_de,
            data_ate=args.data_ate,
            limite=args.limite
        )
    elif args.ranking:
        resultado = consultar_ranking_produtos(
            data_de=args.data_de,
            data_ate=args.data_ate,
            limite=args.limite,
            ordenar_por=args.ordenar_por
        )
    elif args.custo:
        resultado = consultar_custo_total(
            data_de=args.data_de,
            data_ate=args.data_ate
        )
    else:
        resultado = {
            "sucesso": False,
            "erro": "Nenhum modo de operacao especificado"
        }

    print(json.dumps(resultado, ensure_ascii=False, indent=2, cls=DecimalEncoder))


if __name__ == '__main__':
    main()
