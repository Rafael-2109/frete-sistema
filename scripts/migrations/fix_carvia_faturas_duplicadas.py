"""
Fix: Remover 21 faturas cliente duplicadas em carvia_faturas_cliente
=====================================================================

Problema:
  Mesmo PDF de faturas importado 2x no mesmo dia (12:49 e 17:28 de 2025-12-17).
  Criou 21 registros duplicados (IDs 27-47, copias exatas dos originais 6-26).
  0 movimentacoes financeiras vinculadas as duplicatas.
  0 duplicatas em carvia_faturas_transportadora.

Correcao:
  1. Diagnosticar duplicatas por (numero_fatura, cnpj_cliente)
  2. Remover itens das faturas duplicadas (rn > 1, ou seja, maior ID)
  3. Remover faturas duplicadas (manter menor ID por grupo)

Uso:
  python scripts/migrations/fix_carvia_faturas_duplicadas.py            # dry-run (default)
  python scripts/migrations/fix_carvia_faturas_duplicadas.py --execute  # aplica mudancas
"""
import argparse
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def diagnosticar():
    """Mostra estado atual dos registros duplicados"""
    print("\n" + "=" * 70)
    print("DIAGNOSTICO: Faturas cliente duplicadas")
    print("=" * 70)

    # Grupos de duplicatas
    grupos = db.session.execute(text("""
        SELECT numero_fatura, cnpj_cliente, count(*) as qtd,
               array_agg(id ORDER BY id) as ids
        FROM carvia_faturas_cliente
        GROUP BY numero_fatura, cnpj_cliente
        HAVING count(*) > 1
        ORDER BY numero_fatura
    """)).fetchall()

    if not grupos:
        print("\nNenhuma duplicata encontrada em carvia_faturas_cliente.")
        return False

    print(f"\n{len(grupos)} grupo(s) de duplicatas:")
    total_duplicatas = 0
    for g in grupos:
        ids = g.ids
        duplicatas = ids[1:]  # Todos exceto o primeiro (menor ID)
        total_duplicatas += len(duplicatas)
        print(f"  numero={g.numero_fatura} cnpj={g.cnpj_cliente} "
              f"IDs={ids} (manter={ids[0]}, remover={duplicatas})")

    print(f"\nTotal: {total_duplicatas} fatura(s) a remover")

    # Verificar se duplicatas tem movimentacoes financeiras
    dup_ids = db.session.execute(text("""
        SELECT id FROM (
            SELECT id,
                   ROW_NUMBER() OVER (
                       PARTITION BY numero_fatura, cnpj_cliente ORDER BY id
                   ) as rn
            FROM carvia_faturas_cliente
        ) sub WHERE rn > 1
    """)).fetchall()

    dup_id_list = [r.id for r in dup_ids]
    if dup_id_list:
        dup_ids_str = ', '.join(str(i) for i in dup_id_list)

        # Movimentacoes financeiras
        movs = db.session.execute(text(f"""
            SELECT count(*) FROM carvia_conta_movimentacoes
            WHERE tipo_doc = 'fatura_cliente'
              AND doc_id IN ({dup_ids_str})
        """)).scalar() or 0
        print(f"\nMovimentacoes financeiras nas duplicatas: {movs}")
        if movs > 0:
            print("  [AVISO] Existem movimentacoes! Revisao manual necessaria.")

        # Itens das duplicatas
        itens = db.session.execute(text(f"""
            SELECT count(*) FROM carvia_fatura_cliente_itens
            WHERE fatura_cliente_id IN ({dup_ids_str})
        """)).scalar() or 0
        print(f"Itens de fatura nas duplicatas: {itens}")

        # Operacoes vinculadas via fatura_cliente_id
        ops = db.session.execute(text(f"""
            SELECT count(*) FROM carvia_operacoes
            WHERE fatura_cliente_id IN ({dup_ids_str})
        """)).scalar() or 0
        print(f"Operacoes com fatura_cliente_id apontando para duplicatas: {ops}")
        if ops > 0:
            print("  [AVISO] Operacoes vinculadas! Precisam ser re-apontadas.")

    # Verificar transportadora
    print("\n--- carvia_faturas_transportadora ---")
    grupos_transp = db.session.execute(text("""
        SELECT numero_fatura, transportadora_id, count(*) as qtd
        FROM carvia_faturas_transportadora
        GROUP BY numero_fatura, transportadora_id
        HAVING count(*) > 1
    """)).fetchall()

    if grupos_transp:
        print(f"  {len(grupos_transp)} grupo(s) de duplicatas em transportadora!")
        for g in grupos_transp:
            print(f"    numero={g.numero_fatura} transp_id={g.transportadora_id} qtd={g.qtd}")
    else:
        print("  0 duplicatas em carvia_faturas_transportadora.")

    return True


def executar_fix(dry_run: bool):
    """Executa a remocao de duplicatas"""
    modo = "DRY-RUN" if dry_run else "EXECUTANDO"
    print(f"\n{'=' * 70}")
    print(f"{modo}: Remocao de faturas cliente duplicadas")
    print(f"{'=' * 70}")

    # Identificar IDs duplicadas (rn > 1 = maior ID no grupo)
    dup_ids = db.session.execute(text("""
        SELECT id FROM (
            SELECT id,
                   ROW_NUMBER() OVER (
                       PARTITION BY numero_fatura, cnpj_cliente ORDER BY id
                   ) as rn
            FROM carvia_faturas_cliente
        ) sub WHERE rn > 1
        ORDER BY id
    """)).fetchall()

    dup_id_list = [r.id for r in dup_ids]
    if not dup_id_list:
        print("\nNenhuma duplicata encontrada. Nada a fazer.")
        return

    dup_ids_str = ', '.join(str(i) for i in dup_id_list)
    print(f"\nIDs a remover: {dup_id_list}")

    # Verificar bloqueadores: movimentacoes financeiras
    movs = db.session.execute(text(f"""
        SELECT count(*) FROM carvia_conta_movimentacoes
        WHERE tipo_doc = 'fatura_cliente'
          AND doc_id IN ({dup_ids_str})
    """)).scalar() or 0

    if movs > 0:
        print(f"\n[BLOQUEADO] {movs} movimentacao(oes) financeira(s) vinculadas!")
        print("Remocao automatica NAO segura. Revisao manual necessaria.")
        return

    # Verificar e corrigir operacoes que apontam para duplicatas
    ops_dup = db.session.execute(text(f"""
        SELECT o.id as op_id, o.fatura_cliente_id as dup_fatura_id,
               orig.id as orig_fatura_id
        FROM carvia_operacoes o
        JOIN carvia_faturas_cliente dup ON dup.id = o.fatura_cliente_id
        JOIN carvia_faturas_cliente orig ON (
            orig.numero_fatura = dup.numero_fatura
            AND orig.cnpj_cliente = dup.cnpj_cliente
            AND orig.id < dup.id
        )
        WHERE o.fatura_cliente_id IN ({dup_ids_str})
    """)).fetchall()

    if ops_dup:
        print(f"\n--- Re-apontar {len(ops_dup)} operacao(oes) ---")
        for op in ops_dup:
            print(f"  Operacao {op.op_id}: fatura_cliente_id {op.dup_fatura_id} -> {op.orig_fatura_id}")
            if not dry_run:
                db.session.execute(text("""
                    UPDATE carvia_operacoes
                    SET fatura_cliente_id = :orig_id
                    WHERE id = :op_id
                """), {'orig_id': op.orig_fatura_id, 'op_id': op.op_id})

    # PASSO 1: Remover itens das faturas duplicadas
    print(f"\n--- PASSO 1: Remover itens ---")
    itens_count = db.session.execute(text(f"""
        SELECT count(*) FROM carvia_fatura_cliente_itens
        WHERE fatura_cliente_id IN ({dup_ids_str})
    """)).scalar() or 0

    print(f"  {itens_count} item(ns) a remover")
    if not dry_run and itens_count > 0:
        db.session.execute(text(f"""
            DELETE FROM carvia_fatura_cliente_itens
            WHERE fatura_cliente_id IN ({dup_ids_str})
        """))
        print(f"  -> {itens_count} itens removidos.")

    # PASSO 2: Remover faturas duplicadas
    print(f"\n--- PASSO 2: Remover faturas ---")
    print(f"  {len(dup_id_list)} fatura(s) a remover: IDs {dup_id_list}")

    if not dry_run:
        result = db.session.execute(text(f"""
            DELETE FROM carvia_faturas_cliente
            WHERE id IN ({dup_ids_str})
        """))
        print(f"  -> {result.rowcount} faturas removidas.")

    # COMMIT ou ROLLBACK
    if dry_run:
        db.session.rollback()
        print(f"\n{'=' * 70}")
        print("DRY-RUN completo. Nenhuma mudanca aplicada.")
        print("Use --execute para aplicar as mudancas.")
        print(f"{'=' * 70}\n")
    else:
        db.session.commit()
        print(f"\n{'=' * 70}")
        print("CORRECAO APLICADA COM SUCESSO.")
        print(f"{'=' * 70}\n")


def verificar_pos_fix():
    """Verificacao pos-correcao"""
    print("\n" + "=" * 70)
    print("VERIFICACAO POS-CORRECAO")
    print("=" * 70)

    # Verificar que nao restam duplicatas
    grupos = db.session.execute(text("""
        SELECT numero_fatura, cnpj_cliente, count(*) as qtd
        FROM carvia_faturas_cliente
        GROUP BY numero_fatura, cnpj_cliente
        HAVING count(*) > 1
    """)).fetchall()

    status = "OK" if len(grupos) == 0 else "FALHA"
    print(f"\n  [{status}] Grupos duplicados restantes: {len(grupos)} (esperado: 0)")

    # Contagem total
    total = db.session.execute(text("""
        SELECT count(*) FROM carvia_faturas_cliente
    """)).scalar()
    print(f"  Total de faturas cliente: {total}")

    # Verificar que itens orfaos nao ficaram
    orfaos = db.session.execute(text("""
        SELECT count(*) FROM carvia_fatura_cliente_itens fci
        LEFT JOIN carvia_faturas_cliente fc ON fc.id = fci.fatura_cliente_id
        WHERE fc.id IS NULL
    """)).scalar()
    status2 = "OK" if orfaos == 0 else "FALHA"
    print(f"  [{status2}] Itens orfaos: {orfaos} (esperado: 0)")

    # Verificar operacoes
    ops_orfas = db.session.execute(text("""
        SELECT count(*) FROM carvia_operacoes o
        LEFT JOIN carvia_faturas_cliente fc ON fc.id = o.fatura_cliente_id
        WHERE o.fatura_cliente_id IS NOT NULL AND fc.id IS NULL
    """)).scalar()
    status3 = "OK" if ops_orfas == 0 else "FALHA"
    print(f"  [{status3}] Operacoes com fatura_cliente_id orfao: {ops_orfas} (esperado: 0)")

    print()


def main():
    parser = argparse.ArgumentParser(
        description='Fix: remover faturas cliente CarVia duplicadas'
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Aplicar mudancas (default: dry-run)'
    )
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        tem_problema = diagnosticar()

        if not tem_problema:
            return

        executar_fix(dry_run=not args.execute)

        if args.execute:
            verificar_pos_fix()


if __name__ == '__main__':
    main()
