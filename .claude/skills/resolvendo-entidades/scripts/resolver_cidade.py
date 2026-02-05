#!/usr/bin/env python3
"""
Script para resolver cidade com normalizacao de acentos.

Uso:
    python resolver_cidade.py --cidade "itanhaem"
    python resolver_cidade.py --cidade "Sao Paulo" --fonte entregas
"""

import argparse
import json
import sys
import os
import unicodedata

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))


def normalizar_texto(texto: str) -> str:
    """
    Normaliza texto removendo acentos e convertendo para minusculas.

    Args:
        texto: Texto original (ex: "Itanhaem", "Sao Paulo")

    Returns:
        str: Texto normalizado (ex: "itanhaem", "sao paulo")
    """
    if not texto:
        return ""
    # Remove acentos via NFD (decomposicao) e remove combining characters
    texto_sem_acento = ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )
    return texto_sem_acento.lower().strip()


def resolver_cidade(
    cidade: str,
    fonte: str = 'entregas',
    limite: int = 50
) -> dict:
    """
    Resolve termo de cidade para CNPJs/pedidos, normalizando acentos.

    Resolve problemas como:
    - "itanhaem" encontra "Itanhaem", "ITANHAEM", "itanhaem"
    - "peruibe" encontra "Peruibe", "PERUIBE"
    - "sao paulo" encontra "Sao Paulo", "SAO PAULO"

    Args:
        cidade: Nome da cidade (pode ter ou nao acentos)
        fonte: 'carteira', 'separacao' ou 'entregas'
        limite: Maximo de resultados

    Returns:
        dict: {
            'sucesso': bool,
            'cidade': str,
            'termo_normalizado': str,
            'cidades_encontradas': list,
            'clientes': list,
            'total': int
        }
    """
    from app import create_app, db
    from sqlalchemy import text

    termo_normalizado = normalizar_texto(cidade)

    resultado = {
        'sucesso': False,
        'cidade_original': cidade,
        'termo_normalizado': termo_normalizado,
        'cidades_encontradas': [],
        'clientes': [],
        'total': 0
    }

    if not termo_normalizado:
        resultado['erro'] = 'Termo de busca vazio'
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

            # Buscar cidades unicas que casam (usando ILIKE para case-insensitive)
            sql = f"""
                SELECT DISTINCT
                    {campo_cidade} as cidade,
                    {campo_uf} as uf
                FROM {tabela}
                WHERE {campo_cidade} IS NOT NULL
                  AND {campo_cidade} ILIKE :termo
                {filtro_ativo}
                ORDER BY {campo_cidade}
                LIMIT 20
            """
            result = db.session.execute(text(sql), {'termo': f'%{cidade}%'})
            cidades_encontradas = [(row[0], row[1]) for row in result.fetchall()]

            if not cidades_encontradas:
                resultado['erro'] = f"Cidade '{cidade}' nao encontrada"
                resultado['sugestao'] = "Verifique a grafia da cidade"
                return resultado

            resultado['cidades_encontradas'] = [
                {'cidade': c[0], 'uf': c[1]} for c in cidades_encontradas
            ]

            # Buscar clientes dessas cidades
            cidades_lista = [c[0] for c in cidades_encontradas]
            placeholders = ", ".join([f":cidade_{i}" for i in range(len(cidades_lista))])
            params = {f'cidade_{i}': c for i, c in enumerate(cidades_lista)}

            sql = f"""
                SELECT DISTINCT
                    {campo_cnpj} as cnpj,
                    {campo_nome} as nome,
                    {campo_cidade} as cidade,
                    {campo_uf} as uf
                FROM {tabela}
                WHERE {campo_cidade} IN ({placeholders})
                {filtro_ativo}
                ORDER BY {campo_nome}
                LIMIT {limite}
            """
            result = db.session.execute(text(sql), params)
            rows = result.fetchall()

            clientes = []
            for row in rows:
                clientes.append({
                    'cnpj': row[0],
                    'nome': row[1],
                    'cidade': row[2],
                    'uf': row[3]
                })

            resultado['sucesso'] = True
            resultado['clientes'] = clientes
            resultado['total'] = len(clientes)
            resultado['fonte'] = fonte

            return resultado

        except Exception as e:
            resultado['erro'] = str(e)
            return resultado


def main():
    parser = argparse.ArgumentParser(description='Resolve cidade com normalizacao de acentos')

    parser.add_argument('--cidade', type=str, required=True, help='Nome da cidade (com ou sem acentos)')
    parser.add_argument('--fonte', type=str, default='entregas',
                        choices=['carteira', 'separacao', 'entregas'],
                        help='Fonte de dados (default: entregas)')
    parser.add_argument('--limite', type=int, default=50, help='Maximo de registros')

    args = parser.parse_args()

    resultado = resolver_cidade(
        cidade=args.cidade,
        fonte=args.fonte,
        limite=args.limite
    )

    print(json.dumps(resultado, indent=2, ensure_ascii=False, default=str))


if __name__ == '__main__':
    main()
