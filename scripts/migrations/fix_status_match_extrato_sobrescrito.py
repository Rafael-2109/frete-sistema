"""
Script para corrigir CNABs que tiveram status_match_extrato sobrescrito incorretamente.

Problema: CNABs com extrato_item_id preenchido mas status_match_extrato = NAO_APLICAVEL
         quando deveria ser MATCH_SEM_TITULO.

Causa: Bug na linha 128-129 de cnab400_processor_service.py que chamava
       _executar_matching_extrato() para itens SEM_MATCH, sobrescrevendo o
       status já definido por _executar_matching_extrato_sem_titulo().

Solução: Corrigir o status_match_extrato dos CNABs afetados.

Uso:
    source .venv/bin/activate
    python scripts/migrations/fix_status_match_extrato_sobrescrito.py

Data: 2026-01-21
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def verificar_inconsistencias():
    """Verifica CNABs com status inconsistente."""
    result = db.session.execute(text("""
        SELECT
            c.id as cnab_id,
            c.nf_extraida,
            c.parcela_extraida,
            c.status_match,
            c.status_match_extrato,
            c.extrato_item_id,
            e.data_transacao,
            e.valor,
            c.lote_id
        FROM cnab_retorno_item c
        LEFT JOIN extrato_item e ON c.extrato_item_id = e.id
        WHERE c.extrato_item_id IS NOT NULL
          AND c.status_match_extrato = 'NAO_APLICAVEL'
        ORDER BY c.lote_id, c.id
    """))

    inconsistencias = result.fetchall()
    return inconsistencias


def corrigir_status():
    """
    Corrige status_match_extrato de NAO_APLICAVEL para MATCH_SEM_TITULO
    quando extrato_item_id está preenchido.
    """
    # Verificar inconsistências
    inconsistencias = verificar_inconsistencias()

    if not inconsistencias:
        print("   Nenhuma inconsistência encontrada!")
        return 0

    print(f"   Encontradas {len(inconsistencias)} inconsistências:")
    for inc in inconsistencias:
        print(f"   - CNAB {inc[0]}: NF {inc[1]}/{inc[2]} | status_match={inc[3]} | "
              f"status_extrato={inc[4]} | extrato_id={inc[5]}")

    # Corrigir status
    result = db.session.execute(text("""
        UPDATE cnab_retorno_item
        SET
            status_match_extrato = 'MATCH_SEM_TITULO',
            match_criterio_extrato = COALESCE(match_criterio_extrato, 'DATA+VALOR_SEM_TITULO_LOCAL'),
            match_score_extrato = COALESCE(match_score_extrato, 60)
        WHERE extrato_item_id IS NOT NULL
          AND status_match_extrato = 'NAO_APLICAVEL'
        RETURNING id
    """))

    corrigidos = result.fetchall()
    return len(corrigidos)


def atualizar_extratos_vinculados():
    """
    Atualiza status dos extratos que estão vinculados a CNABs
    mas ainda têm status_match = PENDENTE.
    """
    result = db.session.execute(text("""
        UPDATE extrato_item e
        SET
            status_match = 'MATCH_CNAB_PENDENTE',
            match_criterio = 'VIA_CNAB_SEM_TITULO',
            match_score = 60
        FROM cnab_retorno_item c
        WHERE c.extrato_item_id = e.id
          AND c.status_match_extrato = 'MATCH_SEM_TITULO'
          AND e.status_match IN ('PENDENTE', 'SEM_MATCH')
        RETURNING e.id
    """))

    atualizados = result.fetchall()
    return len(atualizados)


def main():
    app = create_app()
    with app.app_context():
        print("\n" + "="*60)
        print("CORREÇÃO: Status Match Extrato Sobrescrito")
        print("="*60)

        try:
            # 1. Verificar estado atual
            print("\n1. Verificando inconsistências...")
            inconsistencias = verificar_inconsistencias()

            if inconsistencias:
                print(f"   Encontradas {len(inconsistencias)} CNABs com status inconsistente")
            else:
                print("   Nenhuma inconsistência encontrada")
                print("\n" + "="*60)
                print("NADA A CORRIGIR")
                print("="*60 + "\n")
                return 0

            # 2. Corrigir status dos CNABs
            print("\n2. Corrigindo status_match_extrato...")
            corrigidos = corrigir_status()
            print(f"   {corrigidos} CNABs corrigidos")

            # 3. Atualizar extratos vinculados
            print("\n3. Atualizando extratos vinculados...")
            extratos_atualizados = atualizar_extratos_vinculados()
            print(f"   {extratos_atualizados} extratos atualizados")

            # 4. Verificar resultado
            print("\n4. Verificando resultado...")
            inconsistencias_apos = verificar_inconsistencias()
            if inconsistencias_apos:
                print(f"   ERRO: Ainda existem {len(inconsistencias_apos)} inconsistências!")
                db.session.rollback()
                return 1
            else:
                print("   OK: Nenhuma inconsistência restante")

            # 5. Commit
            db.session.commit()
            print("\n" + "="*60)
            print("CONCLUÍDO COM SUCESSO!")
            print(f"  - {corrigidos} CNABs corrigidos")
            print(f"  - {extratos_atualizados} extratos atualizados")
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
