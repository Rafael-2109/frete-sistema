#!/usr/bin/env python3
"""
Script para resolver transportadora por nome (parcial ou completo).

Usa 3 estrategias em ordem de prioridade:
1. CNPJ direto (se termo parece CNPJ)
2. Busca semantica via carrier_embeddings (se disponivel)
3. ILIKE no banco (fallback)

Uso:
    python resolver_transportadora.py --termo "TAC"
    python resolver_transportadora.py --termo "Transmerc"
    python resolver_transportadora.py --termo "45.543.915"
"""

import argparse
import json
import sys
import os
import re

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))


def resolver_transportadora(
    termo: str,
    limite: int = 10
) -> dict:
    """
    Resolve termo de transportadora para registros do banco.

    Estrategias de busca:
    1. CNPJ direto (formato XX.XXX.XXX ou digitos)
    2. Busca semantica em carrier_embeddings
    3. ILIKE no banco de transportadoras

    Args:
        termo: Termo de busca (nome parcial ou CNPJ)
        limite: Maximo de resultados

    Returns:
        dict: {
            'sucesso': bool,
            'termo': str,
            'estrategia': str,
            'transportadoras': list,
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
        'transportadoras': [],
        'total': 0
    }

    if not termo or len(termo) < 2:
        resultado['erro'] = 'Termo muito curto (minimo 2 caracteres)'
        return resultado

    app = create_app()

    with app.app_context():
        # Estrategia 1: CNPJ direto
        digitos = re.sub(r'\D', '', termo)
        if len(digitos) >= 8:
            rows = db.session.execute(text("""
                SELECT id, cnpj, razao_social, cidade, uf, ativo
                FROM transportadoras
                WHERE REPLACE(REPLACE(REPLACE(cnpj, '.', ''), '/', ''), '-', '') LIKE :cnpj
                ORDER BY ativo DESC, razao_social
                LIMIT :limite
            """), {"cnpj": f"%{digitos}%", "limite": limite}).fetchall()

            if rows:
                resultado['estrategia'] = 'CNPJ'
                resultado['transportadoras'] = [
                    {
                        'id': r[0], 'cnpj': r[1], 'razao_social': r[2],
                        'cidade': r[3], 'uf': r[4], 'ativo': r[5]
                    }
                    for r in rows
                ]
                resultado['total'] = len(rows)
                resultado['sucesso'] = True
                return resultado

        # Estrategia 2: Busca semantica
        try:
            from app.embeddings.config import CARRIER_SEMANTIC_SEARCH, EMBEDDINGS_ENABLED
            if EMBEDDINGS_ENABLED and CARRIER_SEMANTIC_SEARCH:
                from app.embeddings.service import EmbeddingService
                svc = EmbeddingService()
                sem_results = svc.search_carriers(
                    termo, limit=limite, min_similarity=0.65
                )

                if sem_results:
                    # Buscar detalhes no banco para cada match
                    transportadoras = []
                    for sr in sem_results:
                        carrier_name = sr.get('carrier_name', '')
                        cnpj = sr.get('cnpj')
                        similarity = sr.get('similarity', 0)

                        # Tentar buscar registro canonico
                        if cnpj:
                            row = db.session.execute(text("""
                                SELECT id, cnpj, razao_social, cidade, uf, ativo
                                FROM transportadoras
                                WHERE cnpj = :cnpj
                                LIMIT 1
                            """), {"cnpj": cnpj}).fetchone()
                        else:
                            row = db.session.execute(text("""
                                SELECT id, cnpj, razao_social, cidade, uf, ativo
                                FROM transportadoras
                                WHERE UPPER(razao_social) = :nome
                                LIMIT 1
                            """), {"nome": carrier_name.upper()}).fetchone()

                        if row:
                            transportadoras.append({
                                'id': row[0], 'cnpj': row[1],
                                'razao_social': row[2],
                                'cidade': row[3], 'uf': row[4],
                                'ativo': row[5],
                                'similaridade': round(similarity, 3),
                            })
                        else:
                            # Transportadora so existe em embeddings (aliases)
                            transportadoras.append({
                                'id': None, 'cnpj': cnpj,
                                'razao_social': carrier_name,
                                'cidade': None, 'uf': None,
                                'ativo': None,
                                'similaridade': round(similarity, 3),
                            })

                    if transportadoras:
                        resultado['estrategia'] = 'SEMANTICO'
                        resultado['transportadoras'] = transportadoras
                        resultado['total'] = len(transportadoras)
                        resultado['sucesso'] = True
                        return resultado
        except Exception:
            pass  # Fallback para ILIKE

        # Estrategia 3: ILIKE (fallback)
        rows = db.session.execute(text("""
            SELECT id, cnpj, razao_social, cidade, uf, ativo
            FROM transportadoras
            WHERE UPPER(razao_social) LIKE :termo
            ORDER BY ativo DESC, razao_social
            LIMIT :limite
        """), {"termo": f"%{termo.upper()}%", "limite": limite}).fetchall()

        if rows:
            resultado['estrategia'] = 'ILIKE'
            resultado['transportadoras'] = [
                {
                    'id': r[0], 'cnpj': r[1], 'razao_social': r[2],
                    'cidade': r[3], 'uf': r[4], 'ativo': r[5]
                }
                for r in rows
            ]
            resultado['total'] = len(rows)
            resultado['sucesso'] = True
            return resultado

        resultado['erro'] = f'Nenhuma transportadora encontrada para "{termo}"'
        return resultado


def main():
    parser = argparse.ArgumentParser(description='Resolver transportadora por nome ou CNPJ')
    parser.add_argument('--termo', required=True, help='Nome parcial ou CNPJ')
    parser.add_argument('--limite', type=int, default=10, help='Maximo de resultados')

    args = parser.parse_args()
    resultado = resolver_transportadora(args.termo, limite=args.limite)

    print(json.dumps(resultado, ensure_ascii=False, indent=2, default=str))


if __name__ == '__main__':
    main()
