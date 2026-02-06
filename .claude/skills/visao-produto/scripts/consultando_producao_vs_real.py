#!/usr/bin/env python3
"""
Script: consultando_producao_vs_real.py
Compara producao PROGRAMADA (ProgramacaoProducao) vs REALIZADA (MovimentacaoEstoque tipo=PRODUCAO).

Usa resolver_produto() do resolver_entidades.py para resolver nomes de produto
com suporte a abreviacoes (AZ VF, CI, BD, MEZZANI, etc.) e score de relevancia.

Uso:
    python consultando_producao_vs_real.py --de 2026-01-01 --ate 2026-01-31
    python consultando_producao_vs_real.py --produto palmito --de 2026-01-01 --ate 2026-01-31
    python consultando_producao_vs_real.py --produto "CI vidro" --de 2026-01-01 --ate 2026-01-31
    python consultando_producao_vs_real.py --de 2026-01-01 --ate 2026-01-31 --limite 20
"""

import argparse
import json
import sys
import os
from decimal import Decimal
from datetime import date

# Path do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))
# Path do resolver_entidades (gerindo-expedicao)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../gerindo-expedicao/scripts')))


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, date):
            return obj.strftime('%d/%m/%Y')
        return super().default(obj)


def consultar_producao_vs_real(produto_termo: str = None,
                               data_de: str = None,
                               data_ate: str = None,
                               limite: int = 50) -> dict:
    """
    Compara producao programada vs realizada.

    Args:
        produto_termo: Nome/abreviacao do produto (opcional - se omitido, retorna todos)
        data_de: Data inicio YYYY-MM-DD (obrigatorio)
        data_ate: Data fim YYYY-MM-DD (obrigatorio)
        limite: Max resultados (default: 50)

    Returns:
        dict com comparativo por produto e resumo geral
    """
    from app import create_app, db
    from sqlalchemy import text

    if not data_de or not data_ate:
        return {
            "sucesso": False,
            "erro": "Parametros --de e --ate sao obrigatorios"
        }

    app = create_app()
    with app.app_context():
        # ============================================
        # PASSO 1: Resolver filtro de produto (opcional)
        # ============================================
        filtro_produtos = None  # None = todos os produtos

        if produto_termo:
            from resolver_entidades import resolver_produto

            candidatos = resolver_produto(produto_termo, limit=50)

            if not candidatos:
                return {
                    "sucesso": False,
                    "erro": f"Produto '{produto_termo}' nao encontrado",
                    "sugestao": "Tente usar nome parcial (ex: palmito) ou abreviacao (ex: AZ VF, CI)"
                }

            filtro_produtos = [c['cod_produto'] for c in candidatos]

        # ============================================
        # PASSO 2: Buscar PROGRAMADO
        # ============================================
        try:
            sql_programado = """
                SELECT
                    pp.cod_produto,
                    pp.nome_produto,
                    SUM(pp.qtd_programada) AS qtd_programada,
                    COUNT(*) AS registros_programacao
                FROM programacao_producao pp
                WHERE pp.data_programacao >= :data_de
                  AND pp.data_programacao <= :data_ate
            """
            params = {'data_de': data_de, 'data_ate': data_ate}

            if filtro_produtos:
                placeholders = ', '.join([f':prod_{i}' for i in range(len(filtro_produtos))])
                sql_programado += f" AND pp.cod_produto IN ({placeholders})"
                for i, cod in enumerate(filtro_produtos):
                    params[f'prod_{i}'] = cod

            sql_programado += """
                GROUP BY pp.cod_produto, pp.nome_produto
                ORDER BY qtd_programada DESC
            """

            programado_result = db.session.execute(text(sql_programado), params)
            programado_rows = programado_result.fetchall()

            # Mapear programado por cod_produto
            programado_map = {}
            for row in programado_rows:
                programado_map[row[0]] = {
                    'cod_produto': row[0],
                    'nome_produto': row[1],
                    'qtd_programada': float(row[2] or 0),
                    'registros_programacao': row[3] or 0
                }

        except Exception as e:
            return {"sucesso": False, "erro": f"Erro ao consultar programacao: {str(e)}"}

        # ============================================
        # PASSO 3: Buscar REALIZADO (MovimentacaoEstoque tipo=PRODUCAO)
        # ============================================
        try:
            sql_realizado = """
                SELECT
                    me.cod_produto,
                    me.nome_produto,
                    SUM(me.qtd_movimentacao) AS qtd_realizada,
                    COUNT(*) AS registros_producao
                FROM movimentacao_estoque me
                WHERE me.tipo_movimentacao = 'PRODUCAO'
                  AND me.data_movimentacao >= :data_de
                  AND me.data_movimentacao <= :data_ate
                  AND me.ativo = true
            """
            params_real = {'data_de': data_de, 'data_ate': data_ate}

            if filtro_produtos:
                placeholders = ', '.join([f':prod_{i}' for i in range(len(filtro_produtos))])
                sql_realizado += f" AND me.cod_produto IN ({placeholders})"
                for i, cod in enumerate(filtro_produtos):
                    params_real[f'prod_{i}'] = cod

            sql_realizado += """
                GROUP BY me.cod_produto, me.nome_produto
                ORDER BY qtd_realizada DESC
            """

            realizado_result = db.session.execute(text(sql_realizado), params_real)
            realizado_rows = realizado_result.fetchall()

            # Mapear realizado por cod_produto
            realizado_map = {}
            for row in realizado_rows:
                realizado_map[row[0]] = {
                    'cod_produto': row[0],
                    'nome_produto': row[1],
                    'qtd_realizada': float(row[2] or 0),
                    'registros_producao': row[3] or 0
                }

        except Exception as e:
            return {"sucesso": False, "erro": f"Erro ao consultar producao realizada: {str(e)}"}

        # ============================================
        # PASSO 4: Montar comparativo
        # ============================================
        todos_produtos = set(list(programado_map.keys()) + list(realizado_map.keys()))

        comparativo = []
        total_programado = 0
        total_realizado = 0

        for cod in todos_produtos:
            prog = programado_map.get(cod, {})
            real = realizado_map.get(cod, {})

            qtd_prog = prog.get('qtd_programada', 0)
            qtd_real = real.get('qtd_realizada', 0)
            diferenca = round(qtd_real - qtd_prog, 3)

            if qtd_prog > 0:
                percentual = round((qtd_real / qtd_prog) * 100, 1)
            elif qtd_real > 0:
                percentual = None  # Produziu sem programacao
            else:
                percentual = 0

            nome = prog.get('nome_produto') or real.get('nome_produto', 'N/A')

            comparativo.append({
                'cod_produto': cod,
                'nome_produto': nome,
                'qtd_programada': round(qtd_prog, 3),
                'qtd_realizada': round(qtd_real, 3),
                'diferenca': diferenca,
                'percentual_cumprimento': percentual,
                'status': _classificar_status(percentual, qtd_prog)
            })

            total_programado += qtd_prog
            total_realizado += qtd_real

        # Ordenar por diferenca absoluta (maior gap primeiro)
        comparativo.sort(key=lambda x: abs(x['diferenca']), reverse=True)
        comparativo = comparativo[:limite]

        # Resumo
        percentual_geral = round((total_realizado / total_programado) * 100, 1) if total_programado > 0 else 0

        return {
            "sucesso": True,
            "periodo": {"de": data_de, "ate": data_ate},
            "filtro_produto": produto_termo or "TODOS",
            "comparativo": comparativo,
            "resumo": {
                "total_produtos": len(todos_produtos),
                "total_programado": round(total_programado, 3),
                "total_realizado": round(total_realizado, 3),
                "diferenca_total": round(total_realizado - total_programado, 3),
                "percentual_geral": percentual_geral,
                "mensagem": _gerar_mensagem_resumo(percentual_geral, len(todos_produtos))
            }
        }


def _classificar_status(percentual, qtd_prog):
    """Classifica status do cumprimento de producao."""
    if percentual is None:
        return "SEM_PROGRAMACAO"  # Produziu sem ter sido programado
    if percentual == 0 and qtd_prog == 0:
        return "INATIVO"
    if percentual == 0:
        return "NAO_INICIADO"
    if percentual < 50:
        return "CRITICO"
    if percentual < 80:
        return "ATENCAO"
    if percentual < 100:
        return "QUASE_OK"
    if percentual == 100:
        return "CUMPRIDO"
    return "EXCEDIDO"  # > 100%


def _gerar_mensagem_resumo(percentual_geral, total_produtos):
    """Gera mensagem legivel para o resumo."""
    if percentual_geral >= 100:
        return f"Producao geral EXCEDEU a programacao ({percentual_geral}%) para {total_produtos} produtos"
    if percentual_geral >= 90:
        return f"Producao geral esta em {percentual_geral}% da programacao para {total_produtos} produtos — BOM"
    if percentual_geral >= 70:
        return f"Producao geral esta em {percentual_geral}% da programacao para {total_produtos} produtos — ATENCAO"
    return f"Producao geral esta em {percentual_geral}% da programacao para {total_produtos} produtos — CRITICO"


def main():
    parser = argparse.ArgumentParser(
        description='Compara producao PROGRAMADA vs REALIZADA',
        epilog="""Exemplos:
  python consultando_producao_vs_real.py --de 2026-01-01 --ate 2026-01-31
  python consultando_producao_vs_real.py --produto palmito --de 2026-01-01 --ate 2026-01-31
  python consultando_producao_vs_real.py --produto "CI vidro" --de 2026-01-01 --ate 2026-01-31
  python consultando_producao_vs_real.py --de 2026-01-01 --ate 2026-01-31 --limite 20
        """
    )

    parser.add_argument('--produto', type=str, default=None,
                        help='Nome/abreviacao do produto (opcional - se omitido, retorna todos)')
    parser.add_argument('--de', dest='data_de', type=str, required=True,
                        help='Data inicio (YYYY-MM-DD)')
    parser.add_argument('--ate', dest='data_ate', type=str, required=True,
                        help='Data fim (YYYY-MM-DD)')
    parser.add_argument('--limite', type=int, default=50,
                        help='Max resultados (default: 50)')

    args = parser.parse_args()

    resultado = consultar_producao_vs_real(
        produto_termo=args.produto,
        data_de=args.data_de,
        data_ate=args.data_ate,
        limite=args.limite
    )

    print(json.dumps(resultado, ensure_ascii=False, indent=2, cls=DecimalEncoder))


if __name__ == '__main__':
    main()
