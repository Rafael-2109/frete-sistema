#!/usr/bin/env python3
"""
Script para resolver pedido por numero parcial ou termo.

Uso:
    python resolver_pedido.py --termo "VCD123"
    python resolver_pedido.py --termo "123" --fonte carteira
    python resolver_pedido.py --termo "atacadao 183" --fonte separacao
"""

import argparse
import json
import sys
import os
import re

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))


# Grupos empresariais para deteccao
GRUPOS_EMPRESARIAIS = {
    'atacadao': ['93.209.76', '75.315.33', '00.063.96'],
    'assai': ['06.057.22'],
    'tenda': ['01.157.55']
}


def resolver_pedido(
    termo: str,
    fonte: str = 'ambos',
    limite: int = 50
) -> dict:
    """
    Resolve termo de pedido para lista de pedidos.

    Estrategias de busca (em ordem de prioridade):
    1. Numero exato do pedido
    2. Numero parcial do pedido (LIKE)
    3. CNPJ direto
    4. Grupo empresarial + termo (ex: "atacadao 183")
    5. Cliente por nome parcial

    Args:
        termo: Termo de busca (numero, CNPJ, grupo+loja, nome cliente)
        fonte: 'carteira', 'separacao' ou 'ambos'
        limite: Maximo de resultados

    Returns:
        dict: {
            'sucesso': bool,
            'termo': str,
            'estrategia': str,
            'pedidos': list,
            'multiplos': bool,
            'total': int
        }
    """
    from app import create_app, db
    from sqlalchemy import text

    termo = termo.strip()

    resultado = {
        'sucesso': False,
        'termo_original': termo,
        'estrategia': None,
        'pedidos': [],
        'multiplos': False,
        'total': 0
    }

    if not termo:
        resultado['erro'] = 'Termo de busca vazio'
        return resultado

    app = create_app()
    with app.app_context():
        try:
            # Definir tabelas e campos
            fontes = []
            if fonte in ('carteira', 'ambos'):
                fontes.append({
                    'tabela': 'carteira_principal',
                    'nome': 'carteira',
                    'campo_cnpj': 'cnpj_cpf',
                    'campo_nome': 'raz_social_red',
                    'campo_uf': 'cod_uf',
                    'campo_cidade': 'nome_cidade',
                    'filtro_ativo': "AND qtd_saldo_produto_pedido > 0"
                })
            if fonte in ('separacao', 'ambos'):
                fontes.append({
                    'tabela': 'separacao',
                    'nome': 'separacao',
                    'campo_cnpj': 'cnpj_cpf',
                    'campo_nome': 'raz_social_red',
                    'campo_uf': 'cod_uf',
                    'campo_cidade': 'nome_cidade',
                    'filtro_ativo': "AND sincronizado_nf = false AND qtd_saldo > 0"
                })

            pedidos_encontrados = []

            for f in fontes:
                # ESTRATEGIA 1: Numero exato
                sql = f"""
                    SELECT DISTINCT
                        num_pedido,
                        {f['campo_cnpj']} as cnpj,
                        {f['campo_nome']} as cliente,
                        {f['campo_cidade']} as cidade,
                        {f['campo_uf']} as uf
                    FROM {f['tabela']}
                    WHERE num_pedido = :termo
                    {f['filtro_ativo']}
                    LIMIT {limite}
                """
                result = db.session.execute(text(sql), {'termo': termo})
                rows = result.fetchall()

                if rows:
                    resultado['estrategia'] = 'NUMERO_EXATO'
                    resultado['fonte'] = f['nome']
                    for row in rows:
                        pedidos_encontrados.append({
                            'num_pedido': row[0],
                            'cnpj': row[1],
                            'cliente': row[2],
                            'cidade': row[3],
                            'uf': row[4],
                            'fonte': f['nome']
                        })
                    break

            # ESTRATEGIA 2: Numero parcial (LIKE)
            if not pedidos_encontrados:
                for f in fontes:
                    sql = f"""
                        SELECT DISTINCT
                            num_pedido,
                            {f['campo_cnpj']} as cnpj,
                            {f['campo_nome']} as cliente,
                            {f['campo_cidade']} as cidade,
                            {f['campo_uf']} as uf
                        FROM {f['tabela']}
                        WHERE num_pedido ILIKE :termo
                        {f['filtro_ativo']}
                        ORDER BY num_pedido
                        LIMIT {limite}
                    """
                    result = db.session.execute(text(sql), {'termo': f'%{termo}%'})
                    rows = result.fetchall()

                    if rows:
                        resultado['estrategia'] = 'NUMERO_PARCIAL'
                        for row in rows:
                            pedidos_encontrados.append({
                                'num_pedido': row[0],
                                'cnpj': row[1],
                                'cliente': row[2],
                                'cidade': row[3],
                                'uf': row[4],
                                'fonte': f['nome']
                            })
                        break

            # ESTRATEGIA 3: CNPJ direto
            if not pedidos_encontrados:
                termo_limpo = re.sub(r'[^\d]', '', termo)
                parece_cnpj = len(termo_limpo) >= 8 or '/' in termo

                if parece_cnpj:
                    for f in fontes:
                        sql = f"""
                            SELECT DISTINCT
                                num_pedido,
                                {f['campo_cnpj']} as cnpj,
                                {f['campo_nome']} as cliente,
                                {f['campo_cidade']} as cidade,
                                {f['campo_uf']} as uf
                            FROM {f['tabela']}
                            WHERE ({f['campo_cnpj']} ILIKE :termo OR {f['campo_cnpj']} ILIKE :termo_limpo)
                            {f['filtro_ativo']}
                            ORDER BY num_pedido
                            LIMIT {limite}
                        """
                        result = db.session.execute(text(sql), {
                            'termo': f'%{termo}%',
                            'termo_limpo': f'%{termo_limpo[:8]}%'
                        })
                        rows = result.fetchall()

                        if rows:
                            resultado['estrategia'] = 'CNPJ_DIRETO'
                            for row in rows:
                                pedidos_encontrados.append({
                                    'num_pedido': row[0],
                                    'cnpj': row[1],
                                    'cliente': row[2],
                                    'cidade': row[3],
                                    'uf': row[4],
                                    'fonte': f['nome']
                                })
                            break

            # ESTRATEGIA 4: Grupo empresarial + termo
            if not pedidos_encontrados:
                partes = termo.lower().split()
                if len(partes) >= 2:
                    possivel_grupo = partes[0]
                    prefixos = GRUPOS_EMPRESARIAIS.get(possivel_grupo)

                    if prefixos:
                        busca_loja = ' '.join(partes[1:])
                        resultado['grupo_identificado'] = possivel_grupo

                        for f in fontes:
                            filtros_cnpj = " OR ".join([f"{f['campo_cnpj']} LIKE '{p}%'" for p in prefixos])
                            sql = f"""
                                SELECT DISTINCT
                                    num_pedido,
                                    {f['campo_cnpj']} as cnpj,
                                    {f['campo_nome']} as cliente,
                                    {f['campo_cidade']} as cidade,
                                    {f['campo_uf']} as uf
                                FROM {f['tabela']}
                                WHERE ({filtros_cnpj})
                                  AND {f['campo_nome']} ILIKE :loja
                                {f['filtro_ativo']}
                                ORDER BY num_pedido
                                LIMIT {limite}
                            """
                            result = db.session.execute(text(sql), {'loja': f'%{busca_loja}%'})
                            rows = result.fetchall()

                            if rows:
                                resultado['estrategia'] = 'GRUPO_LOJA'
                                resultado['loja_buscada'] = busca_loja
                                for row in rows:
                                    pedidos_encontrados.append({
                                        'num_pedido': row[0],
                                        'cnpj': row[1],
                                        'cliente': row[2],
                                        'cidade': row[3],
                                        'uf': row[4],
                                        'fonte': f['nome']
                                    })
                                break

            # ESTRATEGIA 5: Cliente por nome parcial
            if not pedidos_encontrados:
                for f in fontes:
                    sql = f"""
                        SELECT DISTINCT
                            num_pedido,
                            {f['campo_cnpj']} as cnpj,
                            {f['campo_nome']} as cliente,
                            {f['campo_cidade']} as cidade,
                            {f['campo_uf']} as uf
                        FROM {f['tabela']}
                        WHERE {f['campo_nome']} ILIKE :termo
                        {f['filtro_ativo']}
                        ORDER BY num_pedido
                        LIMIT {limite}
                    """
                    result = db.session.execute(text(sql), {'termo': f'%{termo}%'})
                    rows = result.fetchall()

                    if rows:
                        resultado['estrategia'] = 'CLIENTE_PARCIAL'
                        for row in rows:
                            pedidos_encontrados.append({
                                'num_pedido': row[0],
                                'cnpj': row[1],
                                'cliente': row[2],
                                'cidade': row[3],
                                'uf': row[4],
                                'fonte': f['nome']
                            })
                        break

            if not pedidos_encontrados:
                resultado['estrategia'] = 'NAO_ENCONTRADO'
                resultado['erro'] = f"Pedido '{termo}' nao encontrado"
                resultado['sugestao'] = "Tente numero parcial (ex: VCD123), grupo+loja (ex: atacadao 183), ou nome do cliente"
                return resultado

            # Remover duplicatas mantendo ordem
            pedidos_unicos = []
            nums_vistos = set()
            for p in pedidos_encontrados:
                if p['num_pedido'] not in nums_vistos:
                    nums_vistos.add(p['num_pedido'])
                    pedidos_unicos.append(p)

            resultado['sucesso'] = True
            resultado['pedidos'] = pedidos_unicos[:limite]
            resultado['multiplos'] = len(pedidos_unicos) > 1
            resultado['total'] = len(pedidos_unicos)

            return resultado

        except Exception as e:
            resultado['erro'] = str(e)
            return resultado


def main():
    parser = argparse.ArgumentParser(description='Resolve pedido por numero ou termo')

    parser.add_argument('--termo', type=str, required=True, help='Numero parcial ou termo de busca')
    parser.add_argument('--fonte', type=str, default='ambos',
                        choices=['carteira', 'separacao', 'ambos'],
                        help='Fonte de dados (default: ambos)')
    parser.add_argument('--limite', type=int, default=50, help='Maximo de registros')

    args = parser.parse_args()

    resultado = resolver_pedido(
        termo=args.termo,
        fonte=args.fonte,
        limite=args.limite
    )

    print(json.dumps(resultado, indent=2, ensure_ascii=False, default=str))


if __name__ == '__main__':
    main()
