#!/usr/bin/env python3
"""
Script para resolver cliente nao-grupo por CNPJ parcial ou nome.

Uso:
    python resolver_cliente.py --termo "Supermercado Bom Preco"
    python resolver_cliente.py --termo "45.543.915"
    python resolver_cliente.py --termo "Padaria" --fonte entregas
"""

import argparse
import json
import sys
import os
import re

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))


def resolver_cliente(
    termo: str,
    fonte: str = 'entregas',
    limite: int = 50
) -> dict:
    """
    Resolve termo de cliente para CNPJs.

    Estrategias de busca:
    1. CNPJ direto (formato XX.XXX.XXX, XXXXXXXX, ou completo)
    2. Nome parcial

    NOTA: Para grupos empresariais (Atacadao, Assai, Tenda), use resolver_grupo.py

    Args:
        termo: Termo de busca (CNPJ ou nome parcial)
        fonte: 'carteira', 'separacao' ou 'entregas'
        limite: Maximo de resultados

    Returns:
        dict: {
            'sucesso': bool,
            'termo': str,
            'estrategia': str,  # 'CNPJ' ou 'NOME_PARCIAL'
            'clientes': list,  # Lista de clientes unicos
            'total': int,
            'erro': str (se sucesso=False)
        }
    """
    from app import create_app, db
    from sqlalchemy import text

    termo = termo.strip()

    resultado = {
        'sucesso': False,
        'termo_original': termo,
        'estrategia': None,
        'clientes': [],
        'total': 0
    }

    if not termo:
        resultado['erro'] = 'Termo de busca vazio'
        return resultado

    # Detectar se parece CNPJ
    termo_limpo = re.sub(r'[^\d]', '', termo)
    parece_cnpj = (
        len(termo_limpo) >= 8 or
        re.match(r'^\d{2}\.\d{3}\.\d{3}', termo) or
        '/' in termo
    )

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

            params = {}

            # Estrategia 1: CNPJ
            if parece_cnpj and len(termo_limpo) >= 8:
                resultado['estrategia'] = 'CNPJ'
                sql = f"""
                    SELECT DISTINCT
                        {campo_cnpj} as cnpj,
                        {campo_nome} as nome,
                        {campo_cidade} as cidade,
                        {campo_uf} as uf
                    FROM {tabela}
                    WHERE ({campo_cnpj} ILIKE :termo OR {campo_cnpj} ILIKE :termo_limpo)
                    {filtro_ativo}
                    ORDER BY {campo_nome}
                    LIMIT {limite}
                """
                params = {'termo': f'%{termo}%', 'termo_limpo': f'%{termo_limpo[:8]}%'}
            else:
                # Estrategia 2: Nome parcial
                resultado['estrategia'] = 'NOME_PARCIAL'
                sql = f"""
                    SELECT DISTINCT
                        {campo_cnpj} as cnpj,
                        {campo_nome} as nome,
                        {campo_cidade} as cidade,
                        {campo_uf} as uf
                    FROM {tabela}
                    WHERE {campo_nome} ILIKE :termo
                    {filtro_ativo}
                    ORDER BY {campo_nome}
                    LIMIT {limite}
                """
                params = {'termo': f'%{termo}%'}

            result = db.session.execute(text(sql), params)
            rows = result.fetchall()

            if not rows:
                resultado['erro'] = f"Cliente '{termo}' nao encontrado"
                resultado['sugestao'] = "Tente buscar por CNPJ (ex: 45.543.915) ou nome parcial"
                return resultado

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
    parser = argparse.ArgumentParser(description='Resolve cliente por CNPJ ou nome')

    parser.add_argument('--termo', type=str, required=True, help='CNPJ parcial ou nome do cliente')
    parser.add_argument('--fonte', type=str, default='entregas',
                        choices=['carteira', 'separacao', 'entregas'],
                        help='Fonte de dados (default: entregas)')
    parser.add_argument('--limite', type=int, default=50, help='Maximo de registros')

    args = parser.parse_args()

    resultado = resolver_cliente(
        termo=args.termo,
        fonte=args.fonte,
        limite=args.limite
    )

    print(json.dumps(resultado, indent=2, ensure_ascii=False, default=str))


if __name__ == '__main__':
    main()
