"""
Script para corrigir duplicatas de CNAB-Extrato e adicionar UNIQUE constraint.

Problema: Múltiplos CNABs podem estar vinculados ao mesmo extrato (match 2:1).
Solução: Limpar duplicatas mantendo apenas o primeiro vínculo, depois adicionar constraint.

Uso:
    source .venv/bin/activate
    python scripts/migrations/fix_cnab_extrato_duplicates.py

Data: 2026-01-21
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def verificar_duplicatas():
    """Verifica duplicatas antes de corrigir."""
    result = db.session.execute(text("""
        SELECT extrato_item_id, COUNT(*) as cnt,
               ARRAY_AGG(id ORDER BY id) as cnab_ids
        FROM cnab_retorno_item
        WHERE extrato_item_id IS NOT NULL
        GROUP BY extrato_item_id
        HAVING COUNT(*) > 1
        ORDER BY cnt DESC
    """))

    duplicatas = result.fetchall()
    return duplicatas


def limpar_duplicatas():
    """
    Remove duplicatas mantendo apenas o primeiro CNAB vinculado a cada extrato.

    Estratégia: Para cada extrato com múltiplos CNABs,
    manter o CNAB com menor ID (primeiro importado) e desvincula os outros.
    """
    # Encontrar duplicatas
    duplicatas = verificar_duplicatas()

    if not duplicatas:
        print("   Nenhuma duplicata encontrada!")
        return 0

    print(f"   Encontradas {len(duplicatas)} duplicatas:")
    total_corrigidos = 0

    for dup in duplicatas:
        extrato_id = dup[0]
        count = dup[1]
        cnab_ids = dup[2]

        # Manter o primeiro (menor ID), desvincula os outros
        keep_id = cnab_ids[0]
        remove_ids = cnab_ids[1:]

        print(f"   - Extrato {extrato_id}: {count} CNABs ({cnab_ids})")
        print(f"     Mantendo CNAB {keep_id}, desvinculando {remove_ids}")

        # Desvincular CNABs extras
        db.session.execute(text("""
            UPDATE cnab_retorno_item
            SET extrato_item_id = NULL,
                status_match_extrato = 'ERRO_MATCH_DUPLICADO',
                match_criterio_extrato = :criterio
            WHERE id = ANY(:ids)
        """), {
            'ids': remove_ids,
            'criterio': f'DESVINCULADO_DUPLICATA_MANTIDO_CNAB_{keep_id}'
        })

        total_corrigidos += len(remove_ids)

    return total_corrigidos


def adicionar_constraint():
    """Adiciona UNIQUE constraint na coluna extrato_item_id."""
    # Verificar se constraint já existe
    result = db.session.execute(text("""
        SELECT constraint_name
        FROM information_schema.table_constraints
        WHERE table_name = 'cnab_retorno_item'
        AND constraint_name = 'uq_cnab_extrato_item_unique'
    """))

    if result.fetchone():
        print("   Constraint já existe!")
        return False

    # Adicionar constraint
    db.session.execute(text("""
        ALTER TABLE cnab_retorno_item
        ADD CONSTRAINT uq_cnab_extrato_item_unique
        UNIQUE (extrato_item_id)
    """))

    return True


def main():
    app = create_app()
    with app.app_context():
        print("\n" + "="*60)
        print("CORREÇÃO: Match 2:1 CNAB→Extrato")
        print("="*60)

        try:
            # 1. Verificar estado atual
            print("\n1. Verificando duplicatas...")
            duplicatas = verificar_duplicatas()

            if duplicatas:
                print(f"   Encontradas {len(duplicatas)} duplicatas")
                for dup in duplicatas:
                    print(f"   - Extrato {dup[0]}: {dup[1]} CNABs")
            else:
                print("   Nenhuma duplicata encontrada")

            # 2. Limpar duplicatas
            print("\n2. Limpando duplicatas...")
            corrigidos = limpar_duplicatas()
            print(f"   {corrigidos} CNABs desvinculados")

            # 3. Verificar novamente
            print("\n3. Verificando resultado...")
            duplicatas_apos = verificar_duplicatas()
            if duplicatas_apos:
                print(f"   ERRO: Ainda existem {len(duplicatas_apos)} duplicatas!")
                db.session.rollback()
                return 1
            else:
                print("   OK: Nenhuma duplicata restante")

            # 4. Adicionar constraint
            print("\n4. Adicionando UNIQUE constraint...")
            if adicionar_constraint():
                print("   Constraint adicionada com sucesso!")

            # 5. Commit
            db.session.commit()
            print("\n" + "="*60)
            print("CONCLUÍDO COM SUCESSO!")
            print("="*60 + "\n")

            return 0

        except Exception as e:
            print(f"\nERRO: {e}")
            db.session.rollback()
            import traceback
            traceback.print_exc()
            return 1


if __name__ == '__main__':
    sys.exit(main())
