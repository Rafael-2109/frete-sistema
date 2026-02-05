#!/usr/bin/env python3
"""
Script para resolver produto por termo ou abreviacao.

Uso:
    python resolver_produto.py --termo "palmito"
    python resolver_produto.py --termo "AZ VF"
    python resolver_produto.py --termo "mezzani balde"
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))


# ============================================================
# ABREVIACOES DE PRODUTO
# Mapeamento de abreviacoes conhecidas para busca EXATA
# Evita falsos positivos (ex: "CI" encontrando "INTENSA")
# ============================================================
ABREVIACOES_PRODUTO = {
    # Tipo Materia Prima (tipo_materia_prima) - busca EXATA
    'CI': {'campo': 'tipo_materia_prima', 'valor': 'CI', 'tipo': 'exato', 'descricao': 'Cogumelo Inteiro'},
    'CF': {'campo': 'tipo_materia_prima', 'valor': 'CF', 'tipo': 'exato', 'descricao': 'Cogumelo Fatiado'},
    'AZ VF': {'campo': 'tipo_materia_prima', 'valor': 'AZ VF', 'tipo': 'exato', 'descricao': 'Azeitona Verde Fatiada'},
    'AZ PF': {'campo': 'tipo_materia_prima', 'valor': 'AZ PF', 'tipo': 'exato', 'descricao': 'Azeitona Preta Fatiada'},
    'AZ VI': {'campo': 'tipo_materia_prima', 'valor': 'AZ VI', 'tipo': 'exato', 'descricao': 'Azeitona Verde Inteira'},
    'AZ PI': {'campo': 'tipo_materia_prima', 'valor': 'AZ PI', 'tipo': 'exato', 'descricao': 'Azeitona Preta Inteira'},
    'AZ VR': {'campo': 'tipo_materia_prima', 'valor': 'AZ VR', 'tipo': 'exato', 'descricao': 'Azeitona Verde Recheada'},
    'AZ VSC': {'campo': 'tipo_materia_prima', 'valor': 'AZ VSC', 'tipo': 'exato', 'descricao': 'Azeitona Verde Sem Caroco'},

    # Alias curtos para tipo_materia_prima
    'VF': {'campo': 'tipo_materia_prima', 'valor': '%VF%', 'tipo': 'like', 'descricao': 'Verde Fatiada'},
    'PF': {'campo': 'tipo_materia_prima', 'valor': '%PF%', 'tipo': 'like', 'descricao': 'Preta Fatiada'},

    # Tipo Embalagem (tipo_embalagem) - busca EXATA ou LIKE
    'BARRICA': {'campo': 'tipo_embalagem', 'valor': 'BARRICA', 'tipo': 'exato', 'descricao': 'Barrica'},
    'BR': {'campo': 'tipo_embalagem', 'valor': 'BARRICA', 'tipo': 'exato', 'descricao': 'Barrica (alias)'},
    'BD': {'campo': 'tipo_embalagem', 'valor': 'BD%', 'tipo': 'like', 'descricao': 'Balde'},
    'BALDE': {'campo': 'tipo_embalagem', 'valor': 'BD%', 'tipo': 'like', 'descricao': 'Balde'},
    'POUCH': {'campo': 'tipo_embalagem', 'valor': 'POUCH%', 'tipo': 'like', 'descricao': 'Pouch'},
    'SACHET': {'campo': 'tipo_embalagem', 'valor': 'SACHET%', 'tipo': 'like', 'descricao': 'Sachet'},
    'VIDRO': {'campo': 'tipo_embalagem', 'valor': 'VIDRO%', 'tipo': 'like', 'descricao': 'Vidro'},
    'VD': {'campo': 'tipo_embalagem', 'valor': 'VIDRO%', 'tipo': 'like', 'descricao': 'Vidro (alias)'},
    'GALAO': {'campo': 'tipo_embalagem', 'valor': 'GALAO%', 'tipo': 'like', 'descricao': 'Galao'},
    'GL': {'campo': 'tipo_embalagem', 'valor': 'GALAO%', 'tipo': 'like', 'descricao': 'Galao (alias)'},

    # Categorias/Marcas (categoria_produto) - busca EXATA
    'CAMPO BELO': {'campo': 'categoria_produto', 'valor': 'CAMPO BELO', 'tipo': 'exato', 'descricao': 'Marca Campo Belo'},
    'MEZZANI': {'campo': 'categoria_produto', 'valor': 'MEZZANI', 'tipo': 'exato', 'descricao': 'Marca Mezzani'},
    'BENASSI': {'campo': 'categoria_produto', 'valor': 'BENASSI', 'tipo': 'exato', 'descricao': 'Marca Benassi'},
    'IMPERIAL': {'campo': 'categoria_produto', 'valor': 'IMPERIAL', 'tipo': 'exato', 'descricao': 'Marca Imperial'},
    'INDUSTRIA': {'campo': 'categoria_produto', 'valor': 'INDUSTRIA', 'tipo': 'exato', 'descricao': 'Destinado a industria'},
    'IND': {'campo': 'categoria_produto', 'valor': 'INDUSTRIA', 'tipo': 'exato', 'descricao': 'Industria (alias)'},
}


def detectar_abreviacoes(tokens: list) -> tuple:
    """
    Detecta abreviacoes em lista de tokens, incluindo combinacoes.

    Exemplo: ['az', 'vf', 'pouch'] -> detecta 'AZ VF' como combinacao

    Args:
        tokens: Lista de tokens (ex: ['az', 'vf', 'pouch'])

    Returns:
        tuple: (abreviacoes_encontradas, tokens_restantes)
    """
    abreviacoes = []
    tokens_usados = set()

    # Primeiro, tentar combinacoes de 2 tokens (ex: 'AZ VF')
    for i in range(len(tokens) - 1):
        combo = f"{tokens[i]} {tokens[i+1]}".upper()
        if combo in ABREVIACOES_PRODUTO:
            abreviacoes.append(ABREVIACOES_PRODUTO[combo])
            tokens_usados.add(i)
            tokens_usados.add(i + 1)

    # Depois, tentar tokens individuais
    for i, token in enumerate(tokens):
        if i in tokens_usados:
            continue
        token_upper = token.upper()
        if token_upper in ABREVIACOES_PRODUTO:
            abreviacoes.append(ABREVIACOES_PRODUTO[token_upper])
            tokens_usados.add(i)

    # Tokens restantes
    tokens_restantes = [t for i, t in enumerate(tokens) if i not in tokens_usados]

    return abreviacoes, tokens_restantes


def resolver_produto(termo: str, limite: int = 50) -> dict:
    """
    Resolve termo de produto usando tokenizacao e busca em CadastroPalletizacao.

    Busca em: nome_produto, categoria_produto, subcategoria,
              tipo_embalagem, tipo_materia_prima

    Estrategia:
    1. Tokeniza o termo (ex: "az vf mezzani" -> ["az", "vf", "mezzani"])
    2. Detecta abreviacoes conhecidas (ex: "AZ VF" -> busca EXATA)
    3. Tokens restantes: busca parcial ILIKE em todos os campos
    4. Ordena por relevancia (mais matches = maior score)

    Args:
        termo: Termo de busca (pode ser abreviacao, nome parcial, combinacao)
        limite: Maximo de resultados

    Returns:
        dict: {
            'sucesso': bool,
            'termo': str,
            'abreviacoes_detectadas': list,
            'produtos': list,
            'total': int
        }
    """
    from app import create_app, db
    from sqlalchemy import text

    termo = termo.strip().lower()

    resultado = {
        'sucesso': False,
        'termo_original': termo,
        'abreviacoes_detectadas': [],
        'produtos': [],
        'total': 0
    }

    if not termo:
        resultado['erro'] = 'Termo de busca vazio'
        return resultado

    # Tokenizar
    tokens = termo.split()

    # Detectar abreviacoes conhecidas
    abreviacoes, tokens_restantes = detectar_abreviacoes(tokens)

    resultado['abreviacoes_detectadas'] = [a['descricao'] for a in abreviacoes]

    app = create_app()
    with app.app_context():
        try:
            # Montar filtros
            filtros = []
            params = {}

            # Filtros para ABREVIACOES (busca EXATA ou LIKE no campo especifico)
            for i, abrev in enumerate(abreviacoes):
                campo = abrev['campo']
                valor = abrev['valor']
                tipo = abrev['tipo']
                param_name = f'abrev_{i}'

                if tipo == 'exato':
                    filtros.append(f"UPPER({campo}) = UPPER(:{param_name})")
                    params[param_name] = valor
                else:  # tipo == 'like'
                    filtros.append(f"{campo} ILIKE :{param_name}")
                    params[param_name] = valor

            # Filtros para TOKENS RESTANTES (busca PARCIAL em qualquer campo)
            for i, token in enumerate(tokens_restantes):
                param_name = f'token_{i}'
                filtros.append(f"""
                    (cod_produto ILIKE :{param_name}
                     OR nome_produto ILIKE :{param_name}
                     OR tipo_materia_prima ILIKE :{param_name}
                     OR tipo_embalagem ILIKE :{param_name}
                     OR categoria_produto ILIKE :{param_name}
                     OR subcategoria ILIKE :{param_name})
                """)
                params[param_name] = f'%{token}%'

            if not filtros:
                resultado['erro'] = 'Nenhum criterio de busca'
                return resultado

            filtro_sql = " AND ".join(filtros)

            sql = f"""
                SELECT
                    cod_produto,
                    nome_produto,
                    tipo_embalagem,
                    tipo_materia_prima,
                    categoria_produto,
                    subcategoria,
                    palletizacao,
                    peso_bruto
                FROM cadastro_palletizacao
                WHERE ativo = true
                  AND produto_vendido = true
                  AND {filtro_sql}
                ORDER BY nome_produto
                LIMIT {limite * 2}
            """

            result = db.session.execute(text(sql), params)
            rows = result.fetchall()

            if not rows:
                resultado['erro'] = f"Produto '{termo}' nao encontrado"
                resultado['sugestao'] = "Tente usar nome parcial (ex: palmito) ou abreviacao (ex: AZ VF)"
                return resultado

            # Calcular score de relevancia
            produtos = []
            for row in rows:
                prod = {
                    'cod_produto': row[0],
                    'nome_produto': row[1],
                    'tipo_embalagem': row[2],
                    'tipo_materia_prima': row[3],
                    'categoria_produto': row[4],
                    'subcategoria': row[5],
                    'palletizacao': float(row[6]) if row[6] else 0,
                    'peso_bruto': float(row[7]) if row[7] else 0,
                    'score': 0,
                    'matches': []
                }

                # Score para abreviacoes encontradas (peso alto pois foi busca exata)
                for abrev in abreviacoes:
                    campo = abrev['campo']
                    valor_prod = prod.get(campo, '')
                    if valor_prod:
                        prod['score'] += 4
                        prod['matches'].append(f"{campo}:{abrev['descricao']}")

                # Score para tokens restantes
                for token in tokens_restantes:
                    token_lower = token.lower()

                    if prod['cod_produto'] and token_lower in prod['cod_produto'].lower():
                        prod['score'] += 5
                        prod['matches'].append(f"cod_produto:{token}")

                    if prod['nome_produto'] and token_lower in prod['nome_produto'].lower():
                        prod['score'] += 3
                        prod['matches'].append(f"nome_produto:{token}")

                    if prod['tipo_materia_prima'] and token_lower in prod['tipo_materia_prima'].lower():
                        prod['score'] += 2

                    if prod['tipo_embalagem'] and token_lower in prod['tipo_embalagem'].lower():
                        prod['score'] += 2

                    if prod['categoria_produto'] and token_lower in prod['categoria_produto'].lower():
                        prod['score'] += 2

                produtos.append(prod)

            # Ordenar por score (maior primeiro) e limitar
            produtos.sort(key=lambda x: -x['score'])
            produtos = produtos[:limite]

            resultado['sucesso'] = True
            resultado['produtos'] = produtos
            resultado['total'] = len(produtos)

            return resultado

        except Exception as e:
            resultado['erro'] = str(e)
            return resultado


def main():
    parser = argparse.ArgumentParser(description='Resolve produto por termo ou abreviacao')

    parser.add_argument('--termo', type=str, required=True, help='Nome, abreviacao ou caracteristica do produto')
    parser.add_argument('--limite', type=int, default=50, help='Maximo de registros')

    args = parser.parse_args()

    resultado = resolver_produto(
        termo=args.termo,
        limite=args.limite
    )

    print(json.dumps(resultado, indent=2, ensure_ascii=False, default=str))


if __name__ == '__main__':
    main()
