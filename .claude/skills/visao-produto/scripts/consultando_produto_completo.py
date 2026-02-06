#!/usr/bin/env python3
"""
Script: consultando_produto_completo.py
Visao 360 de um produto — cadastro, estoque, custo, demanda, faturamento, producao.

Usa resolver_produto_unico() do resolver_entidades.py para resolver nomes de produto
com suporte a abreviacoes (AZ VF, CI, BD, MEZZANI, etc.) e score de relevancia.

Uso:
    python consultando_produto_completo.py --produto palmito
    python consultando_produto_completo.py --produto "az vf pouch"
    python consultando_produto_completo.py --produto "MEZZANI balde"
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


def consultar_produto_completo(termo: str) -> dict:
    """
    Visao 360 de um produto.

    Fluxo:
    1. Resolve produto via resolver_produto_unico (tokenizacao + abreviacoes + score)
    2. Se ambiguo, retorna candidatos para IA decidir
    3. Se unico, consulta 7 tabelas com cod_produto

    Args:
        termo: Nome, codigo ou abreviacao do produto

    Returns:
        dict com secoes: cadastro, estoque, custo, demanda_carteira,
                         demanda_separacao, faturamento_30d, producao_14d
    """
    from resolver_entidades import resolver_produto_unico, formatar_sugestao_produto
    from app import create_app, db
    from sqlalchemy import text

    # ============================================
    # PASSO 1: Resolver produto
    # ============================================
    app = create_app()
    with app.app_context():
        produto, info = resolver_produto_unico(termo)

        # Ambiguidade: multiplos candidatos sem destaque claro
        if not info['encontrado'] and info['multiplos']:
            sugestao = formatar_sugestao_produto(info)
            return {
                "sucesso": False,
                "ambiguidade": True,
                "mensagem": sugestao,
                "candidatos": info.get('candidatos', []),
                "termo_original": termo
            }

        # Nao encontrado
        if not info['encontrado'] and not info['multiplos']:
            sugestao = formatar_sugestao_produto(info)
            return {
                "sucesso": False,
                "ambiguidade": False,
                "mensagem": sugestao or f"Produto '{termo}' nao encontrado",
                "termo_original": termo
            }

        # Produto unico encontrado
        cod_produto = produto['cod_produto']
        nome_produto = produto['nome_produto']

        resultado = {
            "sucesso": True,
            "produto": {
                "cod_produto": cod_produto,
                "nome_produto": nome_produto
            },
            "resolver_info": {
                "termo_original": termo,
                "score": produto.get('score', 0),
                "matches": produto.get('matches', [])
            }
        }

        # Se resolver encontrou com multiplos mas destacou o melhor
        if info.get('multiplos'):
            resultado["resolver_info"]["outros_candidatos"] = info.get('candidatos', [])

        # ============================================
        # PASSO 2: Consultar 7 tabelas
        # ============================================

        # --- CADASTRO (CadastroPalletizacao) ---
        try:
            sql_cadastro = """
                SELECT
                    cod_produto, nome_produto, palletizacao, peso_bruto,
                    tipo_embalagem, tipo_materia_prima, categoria_produto,
                    subcategoria, altura_cm, largura_cm, comprimento_cm,
                    produto_vendido, produto_comprado, produto_produzido,
                    lead_time_mto, linha_producao
                FROM cadastro_palletizacao
                WHERE cod_produto = :cod AND ativo = true
            """
            row = db.session.execute(text(sql_cadastro), {'cod': cod_produto}).fetchone()
            if row:
                keys = row.keys()
                resultado["cadastro"] = dict(zip(keys, row))
            else:
                resultado["cadastro"] = None
        except Exception as e:
            resultado["cadastro"] = {"erro": str(e)}

        # --- ESTOQUE (MovimentacaoEstoque) ---
        try:
            sql_estoque = """
                SELECT
                    SUM(CASE WHEN tipo_movimentacao = 'ENTRADA' THEN qtd_movimentacao ELSE 0 END) AS total_entradas,
                    SUM(CASE WHEN tipo_movimentacao = 'SAIDA' THEN qtd_movimentacao ELSE 0 END) AS total_saidas,
                    SUM(CASE WHEN tipo_movimentacao = 'PRODUCAO' THEN qtd_movimentacao ELSE 0 END) AS total_producao,
                    SUM(CASE WHEN tipo_movimentacao = 'AJUSTE' THEN qtd_movimentacao ELSE 0 END) AS total_ajustes,
                    MAX(data_movimentacao) AS ultima_movimentacao
                FROM movimentacao_estoque
                WHERE cod_produto = :cod AND ativo = true
            """
            row = db.session.execute(text(sql_estoque), {'cod': cod_produto}).fetchone()
            if row:
                entradas = float(row[0] or 0)
                saidas = float(row[1] or 0)
                producao = float(row[2] or 0)
                ajustes = float(row[3] or 0)
                resultado["estoque"] = {
                    "saldo_atual": round(entradas + producao + ajustes - saidas, 3),
                    "total_entradas": round(entradas, 3),
                    "total_saidas": round(saidas, 3),
                    "total_producao": round(producao, 3),
                    "total_ajustes": round(ajustes, 3),
                    "ultima_movimentacao": row[4].strftime('%d/%m/%Y') if row[4] else None
                }
            else:
                resultado["estoque"] = {"saldo_atual": 0, "mensagem": "Sem movimentacoes"}
        except Exception as e:
            resultado["estoque"] = {"erro": str(e)}

        # --- CUSTO (CustoConsiderado) ---
        try:
            sql_custo = """
                SELECT
                    tipo_custo_selecionado, custo_considerado,
                    custo_medio_mes, ultimo_custo, custo_medio_estoque,
                    custo_bom, tipo_produto, versao, custo_producao,
                    vigencia_inicio
                FROM custo_considerado
                WHERE cod_produto = :cod AND custo_atual = true
            """
            row = db.session.execute(text(sql_custo), {'cod': cod_produto}).fetchone()
            if row:
                keys = row.keys()
                resultado["custo"] = dict(zip(keys, row))
            else:
                resultado["custo"] = None
        except Exception as e:
            resultado["custo"] = {"erro": str(e)}

        # --- DEMANDA CARTEIRA (CarteiraPrincipal) ---
        try:
            sql_carteira = """
                SELECT
                    COUNT(DISTINCT num_pedido) AS pedidos_pendentes,
                    SUM(qtd_saldo_produto_pedido) AS qtd_pendente,
                    COUNT(*) AS linhas_pendentes
                FROM carteira_principal
                WHERE cod_produto = :cod
                  AND qtd_saldo_produto_pedido > 0
            """
            row = db.session.execute(text(sql_carteira), {'cod': cod_produto}).fetchone()
            if row:
                resultado["demanda_carteira"] = {
                    "pedidos_pendentes": row[0] or 0,
                    "qtd_pendente": float(row[1] or 0),
                    "linhas_pendentes": row[2] or 0
                }
            else:
                resultado["demanda_carteira"] = {"qtd_pendente": 0, "pedidos_pendentes": 0}
        except Exception as e:
            resultado["demanda_carteira"] = {"erro": str(e)}

        # --- DEMANDA SEPARACAO (Separacao) ---
        try:
            sql_separacao = """
                SELECT
                    COUNT(DISTINCT num_pedido) AS pedidos_separados,
                    SUM(qtd_saldo) AS qtd_separada,
                    COUNT(*) AS separacoes_ativas
                FROM separacao
                WHERE cod_produto = :cod
                  AND sincronizado_nf = false
                  AND qtd_saldo > 0
            """
            row = db.session.execute(text(sql_separacao), {'cod': cod_produto}).fetchone()
            if row:
                resultado["demanda_separacao"] = {
                    "pedidos_separados": row[0] or 0,
                    "qtd_separada": float(row[1] or 0),
                    "separacoes_ativas": row[2] or 0
                }
            else:
                resultado["demanda_separacao"] = {"qtd_separada": 0, "pedidos_separados": 0}
        except Exception as e:
            resultado["demanda_separacao"] = {"erro": str(e)}

        # --- FATURAMENTO RECENTE (FaturamentoProduto - ultimos 30 dias) ---
        try:
            sql_faturamento = """
                SELECT
                    COUNT(DISTINCT numero_nf) AS nfs_faturadas,
                    SUM(qtd_produto_faturado) AS qtd_faturada,
                    SUM(valor_produto_faturado) AS valor_faturado,
                    COUNT(DISTINCT cnpj_cliente) AS clientes_atendidos
                FROM faturamento_produto
                WHERE cod_produto = :cod
                  AND data_fatura >= CURRENT_DATE - INTERVAL '30 days'
                  AND revertida = false
            """
            row = db.session.execute(text(sql_faturamento), {'cod': cod_produto}).fetchone()
            if row:
                resultado["faturamento_30d"] = {
                    "nfs_faturadas": row[0] or 0,
                    "qtd_faturada": float(row[1] or 0),
                    "valor_faturado": float(row[2] or 0),
                    "clientes_atendidos": row[3] or 0
                }
            else:
                resultado["faturamento_30d"] = {"qtd_faturada": 0, "valor_faturado": 0}
        except Exception as e:
            resultado["faturamento_30d"] = {"erro": str(e)}

        # --- PRODUCAO PROGRAMADA (ProgramacaoProducao - proximos 14 dias) ---
        try:
            sql_producao = """
                SELECT
                    data_programacao, SUM(qtd_programada) AS qtd_programada,
                    linha_producao, ordem_producao
                FROM programacao_producao
                WHERE cod_produto = :cod
                  AND data_programacao >= CURRENT_DATE
                  AND data_programacao <= CURRENT_DATE + INTERVAL '14 days'
                GROUP BY data_programacao, linha_producao, ordem_producao
                ORDER BY data_programacao
            """
            rows = db.session.execute(text(sql_producao), {'cod': cod_produto}).fetchall()
            if rows:
                detalhes = []
                total_programado = 0
                for row in rows:
                    qtd = float(row[1] or 0)
                    total_programado += qtd
                    detalhes.append({
                        "data": row[0].strftime('%d/%m/%Y') if row[0] else None,
                        "qtd_programada": qtd,
                        "linha_producao": row[2],
                        "ordem_producao": row[3]
                    })
                resultado["producao_14d"] = {
                    "total_programado": round(total_programado, 3),
                    "detalhes": detalhes
                }
            else:
                resultado["producao_14d"] = {"total_programado": 0, "detalhes": []}
        except Exception as e:
            resultado["producao_14d"] = {"erro": str(e)}

        return resultado


def main():
    parser = argparse.ArgumentParser(
        description='Visao 360 de produto — cadastro, estoque, custo, demanda, faturamento, producao',
        epilog="""Exemplos:
  python consultando_produto_completo.py --produto palmito
  python consultando_produto_completo.py --produto "az vf pouch"
  python consultando_produto_completo.py --produto "MEZZANI balde"
  python consultando_produto_completo.py --produto "CI vidro"
        """
    )

    parser.add_argument('--produto', type=str, required=True,
                        help='Nome, codigo ou abreviacao do produto (ex: palmito, "az vf", CI)')

    args = parser.parse_args()

    resultado = consultar_produto_completo(args.produto)
    print(json.dumps(resultado, ensure_ascii=False, indent=2, cls=DecimalEncoder))


if __name__ == '__main__':
    main()
