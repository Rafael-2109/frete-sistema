"""
Fix nome_emitente incorreto em 5 NFs CarVia (CNPJ 33119545000413)
===================================================================

Problema: O parser DANFE PDF parseava "Est D, 345" (endereco) como nome_emitente
em vez de "NOTCO BRASIL DISTRIBUICAO E COMERCI PRODUTOS ALIMENTICIOS LT".

Bug: regex de logradouro em get_nome_emitente() nao reconhecia abreviacoes
como "Est" (forma curta de ESTRADA). Corrigido no parser (danfe_pdf_parser.py).

Este script corrige os 5 registros ja importados com nome errado.

Idempotente: so atualiza registros com nome_emitente = 'Est D, 345'.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db


CNPJ = '33119545000413'
NOME_ERRADO = 'Est D, 345'
NOME_CORRETO = 'NOTCO BRASIL DISTRIBUICAO E COMERCI PRODUTOS ALIMENTICIOS LT'


def run_fix():
    """Corrige nome_emitente nas NFs afetadas."""
    # Diagnostico ANTES
    resultado = db.session.execute(
        db.text("""
            SELECT id, numero_nf, nome_emitente
            FROM carvia_nfs
            WHERE cnpj_emitente = :cnpj
              AND nome_emitente = :nome_errado
        """),
        {'cnpj': CNPJ, 'nome_errado': NOME_ERRADO},
    )
    rows = resultado.fetchall()

    print(f"=== ANTES do fix ===")
    print(f"NFs com nome_emitente errado ('{NOME_ERRADO}'): {len(rows)}")
    for row in rows:
        print(f"  ID={row[0]}, NF={row[1]}, nome='{row[2]}'")

    if not rows:
        print("\nNenhum registro para corrigir. Migration ja foi aplicada.")
        return

    # Executar fix
    result = db.session.execute(
        db.text("""
            UPDATE carvia_nfs
            SET nome_emitente = :nome_correto
            WHERE cnpj_emitente = :cnpj
              AND nome_emitente = :nome_errado
        """),
        {
            'cnpj': CNPJ,
            'nome_errado': NOME_ERRADO,
            'nome_correto': NOME_CORRETO,
        },
    )
    db.session.commit()

    print(f"\n=== FIX APLICADO ===")
    print(f"Registros atualizados: {result.rowcount}")

    # Diagnostico DEPOIS
    resultado = db.session.execute(
        db.text("""
            SELECT id, numero_nf, nome_emitente
            FROM carvia_nfs
            WHERE cnpj_emitente = :cnpj
        """),
        {'cnpj': CNPJ},
    )
    rows_after = resultado.fetchall()

    print(f"\n=== DEPOIS do fix ===")
    for row in rows_after:
        print(f"  ID={row[0]}, NF={row[1]}, nome='{row[2]}'")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        run_fix()
