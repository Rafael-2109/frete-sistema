#!/usr/bin/env python3
"""
Script para resolver UF para lista de CNPJs/pedidos.

Uso:
    python resolver_uf.py --uf SP
    python resolver_uf.py --uf RJ --fonte entregas
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))


# Lista de UFs validas
UFS_VALIDAS = [
    'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
    'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN',
    'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'
]


def resolver_uf(
    uf: str,
    fonte: str = 'entregas',
    limite: int = 100
) -> dict:
    """
    Resolve UF para lista de CNPJs/clientes.

    Args:
        uf: Sigla da UF (ex: 'SP', 'RJ')
        fonte: 'carteira', 'separacao' ou 'entregas'
        limite: Maximo de resultados

    Returns:
        dict: {
            'sucesso': bool,
            'uf': str,
            'clientes': list,
            'cidades': list,
            'total': int
        }
    """
    from app import create_app, db
    from sqlalchemy import text

    uf_upper = uf.upper().strip()

    resultado = {
        'sucesso': False,
        'uf': uf_upper,
        'clientes': [],
        'cidades': [],
        'total': 0
    }

    if uf_upper not in UFS_VALIDAS:
        resultado['erro'] = f"UF '{uf}' invalida"
        resultado['ufs_validas'] = UFS_VALIDAS
        return resultado

    app = create_app()
    with app.app_context():
        try:
            # Escolher tabela baseado na fonte
            if fonte == 'carteira':
                tabela = 'carteira_principal'
                campo_cnpj = 'cnpj_cpf'
                campo_nome = 'raz_social_red'
                campo_uf = 'cod_uf'
                campo_cidade = 'nome_cidade'
                filtro_ativo = "AND qtd_saldo_produto_pedido > 0"
            elif fonte == 'separacao':
                tabela = 'separacao'
                campo_cnpj = 'cnpj_cpf'
                campo_nome = 'raz_social_red'
                campo_uf = 'cod_uf'
                campo_cidade = 'nome_cidade'
                filtro_ativo = "AND sincronizado_nf = false AND qtd_saldo > 0"
            else:  # entregas
                tabela = 'entregas_monitoradas'
                campo_cnpj = 'cnpj_cliente'
                campo_nome = 'cliente'
                campo_uf = 'uf'
                campo_cidade = 'municipio'
                filtro_ativo = "AND status_finalizacao IS NULL"

            # Buscar clientes da UF
            sql = f"""
                SELECT DISTINCT
                    {campo_cnpj} as cnpj,
                    {campo_nome} as nome,
                    {campo_cidade} as cidade,
                    {campo_uf} as uf
                FROM {tabela}
                WHERE {campo_uf} = :uf
                {filtro_ativo}
                ORDER BY {campo_nome}
                LIMIT {limite}
            """
            result = db.session.execute(text(sql), {'uf': uf_upper})
            rows = result.fetchall()

            if not rows:
                resultado['erro'] = f"Nenhum registro encontrado para UF {uf_upper}"
                return resultado

            clientes = []
            cidades_set = set()
            for row in rows:
                clientes.append({
                    'cnpj': row[0],
                    'nome': row[1],
                    'cidade': row[2],
                    'uf': row[3]
                })
                if row[2]:
                    cidades_set.add(row[2])

            # Contar total
            sql_count = f"""
                SELECT COUNT(DISTINCT {campo_cnpj})
                FROM {tabela}
                WHERE {campo_uf} = :uf
                {filtro_ativo}
            """
            total = db.session.execute(text(sql_count), {'uf': uf_upper}).scalar()

            resultado['sucesso'] = True
            resultado['clientes'] = clientes
            resultado['cidades'] = sorted(list(cidades_set))
            resultado['total'] = total
            resultado['exibindo'] = len(clientes)
            resultado['fonte'] = fonte

            return resultado

        except Exception as e:
            resultado['erro'] = str(e)
            return resultado


def main():
    parser = argparse.ArgumentParser(description='Resolve UF para lista de clientes')

    parser.add_argument('--uf', type=str, required=True, help='Sigla da UF (ex: SP, RJ)')
    parser.add_argument('--fonte', type=str, default='entregas',
                        choices=['carteira', 'separacao', 'entregas'],
                        help='Fonte de dados (default: entregas)')
    parser.add_argument('--limite', type=int, default=100, help='Maximo de registros')

    args = parser.parse_args()

    resultado = resolver_uf(
        uf=args.uf,
        fonte=args.fonte,
        limite=args.limite
    )

    print(json.dumps(resultado, indent=2, ensure_ascii=False, default=str))


if __name__ == '__main__':
    main()
