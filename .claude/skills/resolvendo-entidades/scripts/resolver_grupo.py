#!/usr/bin/env python3
"""
Script para resolver grupos empresariais em CNPJs.

Uso:
    python resolver_grupo.py --grupo atacadao
    python resolver_grupo.py --grupo assai --uf SP
    python resolver_grupo.py --grupo atacadao --loja 183
    python resolver_grupo.py --grupo tenda --fonte entregas
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))  # noqa: E402


# ============================================================
# GRUPOS EMPRESARIAIS
# Prefixos CNPJ (formato com pontos conforme banco)
# ============================================================
GRUPOS_EMPRESARIAIS = {
    'atacadao': ['93.209.76', '75.315.33', '00.063.96'],
    'assai': ['06.057.22'],
    'tenda': ['01.157.55']
}


def get_prefixos_grupo(grupo: str) -> list:
    """Retorna prefixos CNPJ de um grupo empresarial."""
    return GRUPOS_EMPRESARIAIS.get(grupo.lower().strip(), [])


def listar_grupos_disponiveis() -> list:
    """Retorna lista de grupos empresariais disponiveis."""
    return list(GRUPOS_EMPRESARIAIS.keys())


def resolver_grupo(
    grupo: str,
    uf: str = None,
    loja: str = None,
    fonte: str = 'entregas',
    limite: int = 100
) -> dict:
    """
    Resolve grupo empresarial retornando prefixos CNPJ + dados.

    Args:
        grupo: Nome do grupo (atacadao, assai, tenda)
        uf: Filtro opcional por UF (ex: 'SP')
        loja: Filtro opcional por identificador da loja (ex: '183')
        fonte: 'carteira', 'separacao' ou 'entregas'
        limite: Maximo de registros

    Returns:
        dict: {
            'sucesso': bool,
            'grupo': str,
            'prefixos_cnpj': list,
            'filtros_aplicados': dict,
            'cnpjs': list[str],  # CNPJs unicos encontrados
            'total': int,
            'erro': str (se sucesso=False)
        }
    """
    from app import create_app, db
    from sqlalchemy import text

    grupo_lower = grupo.lower().strip()
    prefixos = get_prefixos_grupo(grupo_lower)

    if not prefixos:
        return {
            'sucesso': False,
            'grupo': grupo,
            'erro': f"Grupo '{grupo}' nao encontrado",
            'grupos_disponiveis': listar_grupos_disponiveis()
        }

    filtros_aplicados = {}
    if uf:
        filtros_aplicados['uf'] = uf.upper()
    if loja:
        filtros_aplicados['loja'] = loja

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

            # Montar filtros de CNPJ
            filtros_cnpj = " OR ".join([f"{campo_cnpj} LIKE '{p}%'" for p in prefixos])

            sql = f"""
                SELECT DISTINCT
                    {campo_cnpj} as cnpj,
                    {campo_nome} as nome,
                    {campo_cidade} as cidade,
                    {campo_uf} as uf
                FROM {tabela}
                WHERE ({filtros_cnpj})
                {filtro_ativo}
            """
            params = {}

            if uf:
                sql += f" AND {campo_uf} = :uf"
                params['uf'] = uf.upper()

            if loja:
                sql += f" AND {campo_nome} ILIKE :loja"
                params['loja'] = f'%{loja}%'

            sql += f" ORDER BY {campo_nome} LIMIT {limite}"

            result = db.session.execute(text(sql), params)
            rows = result.fetchall()

            cnpjs = []
            clientes = []
            for row in rows:
                cnpjs.append(row[0])
                clientes.append({
                    'cnpj': row[0],
                    'nome': row[1],
                    'cidade': row[2],
                    'uf': row[3]
                })

            # Contar total
            sql_count = f"""
                SELECT COUNT(DISTINCT {campo_cnpj})
                FROM {tabela}
                WHERE ({filtros_cnpj})
                {filtro_ativo}
            """
            if uf:
                sql_count += f" AND {campo_uf} = :uf"
            if loja:
                sql_count += f" AND {campo_nome} ILIKE :loja"

            total = db.session.execute(text(sql_count), params).scalar()

            return {
                'sucesso': True,
                'grupo': grupo_lower,
                'prefixos_cnpj': prefixos,
                'filtros_aplicados': filtros_aplicados,
                'fonte': fonte,
                'cnpjs': cnpjs,
                'clientes': clientes,
                'total': total,
                'exibindo': len(cnpjs)
            }

        except Exception as e:
            return {
                'sucesso': False,
                'grupo': grupo,
                'erro': str(e),
                'prefixos_cnpj': prefixos
            }


def main():
    parser = argparse.ArgumentParser(description='Resolve grupo empresarial para CNPJs')

    parser.add_argument('--grupo', type=str, required=True, help='Nome do grupo (atacadao, assai, tenda)')
    parser.add_argument('--uf', type=str, help='Filtrar por UF (ex: SP)')
    parser.add_argument('--loja', type=str, help='Filtrar por identificador de loja (ex: 183)')
    parser.add_argument('--fonte', type=str, default='entregas',
                        choices=['carteira', 'separacao', 'entregas'],
                        help='Fonte de dados (default: entregas)')
    parser.add_argument('--limite', type=int, default=100, help='Maximo de registros')

    args = parser.parse_args()

    resultado = resolver_grupo(
        grupo=args.grupo,
        uf=args.uf,
        loja=args.loja,
        fonte=args.fonte,
        limite=args.limite
    )

    print(json.dumps(resultado, indent=2, ensure_ascii=False, default=str))


if __name__ == '__main__':
    main()
