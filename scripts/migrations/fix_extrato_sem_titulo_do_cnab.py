"""
Script para corrigir extratos que têm CNAB vinculado mas não têm título.

Problema: Extratos com status_match = MATCH_ENCONTRADO mas titulo_receber_id = NULL,
         mesmo quando o CNAB vinculado TEM conta_a_receber_id preenchido.

Causa: Bug no _executar_matching_extrato() que não copiava informações do título
       para o extrato quando vinculava CNAB ↔ Extrato.

Solução: Copiar informações do título do CNAB para o extrato.

Uso:
    source .venv/bin/activate
    python scripts/migrations/fix_extrato_sem_titulo_do_cnab.py

Data: 2026-01-21
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def verificar_inconsistencias():
    """
    Verifica extratos que têm CNAB vinculado com título,
    mas o extrato não tem titulo_receber_id.
    """
    result = db.session.execute(text("""
        SELECT
            e.id as extrato_id,
            e.status_match as extrato_status_match,
            e.titulo_receber_id as extrato_titulo_id,
            e.titulo_nf as extrato_titulo_nf,
            c.id as cnab_id,
            c.nf_extraida as cnab_nf,
            c.parcela_extraida as cnab_parcela,
            c.conta_a_receber_id as cnab_titulo_id,
            c.status_match as cnab_status_match
        FROM extrato_item e
        JOIN cnab_retorno_item c ON c.extrato_item_id = e.id
        WHERE c.conta_a_receber_id IS NOT NULL
          AND e.titulo_receber_id IS NULL
        ORDER BY e.id
    """))

    inconsistencias = result.fetchall()
    return inconsistencias


def corrigir_extratos():
    """
    Copia informações do título do CNAB para o extrato.
    """
    # Buscar extratos que precisam ser corrigidos
    inconsistencias = verificar_inconsistencias()

    if not inconsistencias:
        print("   Nenhuma inconsistência encontrada!")
        return 0

    print(f"   Encontradas {len(inconsistencias)} inconsistências:")
    for inc in inconsistencias:
        print(f"   - Extrato {inc[0]}: status={inc[1]} | titulo_id={inc[2]} | "
              f"CNAB {inc[4]}: NF {inc[5]}/{inc[6]} | cnab_titulo_id={inc[7]}")

    # Corrigir cada extrato
    # NOTA: Campos corretos da tabela contas_a_receber:
    # - valor_titulo (não 'valor')
    # - vencimento (não 'data_vencimento')
    # - parcela é VARCHAR em contas_a_receber mas INTEGER em extrato_item
    result = db.session.execute(text("""
        UPDATE extrato_item e
        SET
            titulo_receber_id = c.conta_a_receber_id,
            titulo_nf = t.titulo_nf,
            titulo_parcela = CAST(t.parcela AS INTEGER),
            titulo_valor = t.valor_titulo,
            titulo_vencimento = t.vencimento,
            titulo_cliente = t.raz_social,
            titulo_cnpj = t.cnpj
        FROM cnab_retorno_item c
        JOIN contas_a_receber t ON c.conta_a_receber_id = t.id
        WHERE c.extrato_item_id = e.id
          AND c.conta_a_receber_id IS NOT NULL
          AND e.titulo_receber_id IS NULL
        RETURNING e.id
    """))

    corrigidos = result.fetchall()
    return len(corrigidos)


def main():
    app = create_app()
    with app.app_context():
        print("\n" + "="*70)
        print("CORREÇÃO #13: Extratos sem Título quando CNAB tem Título")
        print("="*70)

        try:
            # 1. Verificar estado atual
            print("\n1. Verificando inconsistências...")
            inconsistencias = verificar_inconsistencias()

            if inconsistencias:
                print(f"   Encontradas {len(inconsistencias)} extratos para corrigir")
            else:
                print("   Nenhuma inconsistência encontrada")
                print("\n" + "="*70)
                print("NADA A CORRIGIR")
                print("="*70 + "\n")
                return 0

            # 2. Corrigir extratos
            print("\n2. Copiando informações do título para extratos...")
            corrigidos = corrigir_extratos()
            print(f"   {corrigidos} extratos corrigidos")

            # 3. Verificar resultado
            print("\n3. Verificando resultado...")
            inconsistencias_apos = verificar_inconsistencias()
            if inconsistencias_apos:
                print(f"   ERRO: Ainda existem {len(inconsistencias_apos)} inconsistências!")
                db.session.rollback()
                return 1
            else:
                print("   OK: Nenhuma inconsistência restante")

            # 4. Mostrar extratos corrigidos
            print("\n4. Extratos corrigidos:")
            result = db.session.execute(text("""
                SELECT
                    e.id as extrato_id,
                    e.status_match,
                    e.titulo_receber_id,
                    e.titulo_nf,
                    e.titulo_parcela,
                    e.titulo_cliente
                FROM extrato_item e
                JOIN cnab_retorno_item c ON c.extrato_item_id = e.id
                WHERE c.conta_a_receber_id IS NOT NULL
                  AND e.titulo_receber_id IS NOT NULL
                ORDER BY e.id
            """))
            for r in result.fetchall():
                print(f"   ✓ Extrato {r[0]}: {r[1]} | Título {r[2]} | "
                      f"NF {r[3]}/{r[4]} | {r[5][:30] if r[5] else '-'}...")

            # 5. Commit
            db.session.commit()
            print("\n" + "="*70)
            print("CONCLUÍDO COM SUCESSO!")
            print(f"  - {corrigidos} extratos corrigidos")
            print("="*70 + "\n")

            return 0

        except Exception as e:
            print(f"\nERRO: {e}")
            db.session.rollback()
            import traceback
            traceback.print_exc()
            return 1


if __name__ == '__main__':
    sys.exit(main())
