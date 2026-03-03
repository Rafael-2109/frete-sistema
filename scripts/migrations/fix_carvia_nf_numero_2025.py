"""
Fix: DANFE parser capturou "ANO 2025" como numero_nf em 4 NFs de motos eletricas
====================================================================================

Problema:
  O regex do parser DANFE casava "ANO 2025" (nos DADOS ADICIONAIS) antes do numero
  real (ex: "N.: 000001710" no rodape). Resultado: 4 NFs com numero_nf='2025'.

  Quando faturas PDF foram importadas depois, o LinkingService nao encontrou as NFs
  pelo numero correto e criou stubs FATURA_REFERENCIA (IDs 41-44).

Correcao (4 passos):
  1. Corrigir numero_nf nas NFs reais usando chave_acesso_nf[25:34]
  2. Re-linkar itens de fatura dos stubs para as NFs reais
  3. Remover junctions dos stubs
  4. Remover itens e stubs orfaos

Uso:
  python scripts/migrations/fix_carvia_nf_numero_2025.py            # dry-run (default)
  python scripts/migrations/fix_carvia_nf_numero_2025.py --execute  # aplica mudancas
"""
import argparse
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def diagnosticar():
    """Mostra estado atual dos registros afetados"""
    print("\n" + "=" * 80)
    print("DIAGNOSTICO: NFs com numero_nf='2025'")
    print("=" * 80)

    # NFs com numero errado
    nfs_erradas = db.session.execute(text("""
        SELECT id, numero_nf, chave_acesso_nf, tipo_fonte, cnpj_emitente, nome_emitente,
               CAST(CAST(substring(chave_acesso_nf from 26 for 9) AS bigint) AS text)
                   AS numero_real_da_chave
        FROM carvia_nfs
        WHERE numero_nf = '2025'
          AND chave_acesso_nf IS NOT NULL
          AND length(chave_acesso_nf) = 44
        ORDER BY id
    """)).fetchall()

    if not nfs_erradas:
        print("\nNenhuma NF com numero_nf='2025' encontrada. Nada a corrigir.")
        return False

    print(f"\nNFs com numero errado: {len(nfs_erradas)}")
    for nf in nfs_erradas:
        print(f"  ID {nf.id}: numero_nf='{nf.numero_nf}' -> real={nf.numero_real_da_chave} "
              f"({nf.tipo_fonte}, emitente={nf.cnpj_emitente})")

    # Stubs FATURA_REFERENCIA que correspondem
    numeros_reais = [nf.numero_real_da_chave for nf in nfs_erradas]
    placeholders = ', '.join(f"'{n}'" for n in numeros_reais)

    stubs = db.session.execute(text(f"""
        SELECT id, numero_nf, tipo_fonte, cnpj_emitente
        FROM carvia_nfs
        WHERE tipo_fonte = 'FATURA_REFERENCIA'
          AND numero_nf IN ({placeholders})
        ORDER BY id
    """)).fetchall()

    print(f"\nStubs FATURA_REFERENCIA correspondentes: {len(stubs)}")
    for s in stubs:
        print(f"  ID {s.id}: numero_nf='{s.numero_nf}' ({s.tipo_fonte}, "
              f"cnpj_emitente={s.cnpj_emitente})")

    # Itens de fatura vinculados aos stubs
    stub_ids = [s.id for s in stubs]
    if stub_ids:
        stub_ids_str = ', '.join(str(i) for i in stub_ids)
        itens_fatura = db.session.execute(text(f"""
            SELECT id, fatura_cliente_id, nf_id, nf_numero, operacao_id
            FROM carvia_fatura_cliente_itens
            WHERE nf_id IN ({stub_ids_str})
            ORDER BY nf_id
        """)).fetchall()

        print(f"\nItens de fatura vinculados aos stubs: {len(itens_fatura)}")
        for item in itens_fatura:
            print(f"  Item ID {item.id}: fatura={item.fatura_cliente_id}, "
                  f"nf_id={item.nf_id}, nf_numero='{item.nf_numero}', "
                  f"operacao_id={item.operacao_id}")

    # Junctions dos stubs
    if stub_ids:
        junctions = db.session.execute(text(f"""
            SELECT id, operacao_id, nf_id
            FROM carvia_operacao_nfs
            WHERE nf_id IN ({stub_ids_str})
            ORDER BY nf_id
        """)).fetchall()

        print(f"\nJunctions (operacao<->nf) dos stubs: {len(junctions)}")
        for j in junctions:
            print(f"  Junction ID {j.id}: operacao_id={j.operacao_id}, nf_id={j.nf_id}")

    # NF itens dos stubs
    if stub_ids:
        nf_itens = db.session.execute(text(f"""
            SELECT id, nf_id
            FROM carvia_nf_itens
            WHERE nf_id IN ({stub_ids_str})
        """)).fetchall()

        print(f"\nItens de NF dos stubs: {len(nf_itens)}")

    print()
    return True


def executar_fix(dry_run: bool):
    """Executa a correcao em 4 passos"""
    modo = "DRY-RUN" if dry_run else "EXECUTANDO"
    print(f"\n{'=' * 80}")
    print(f"{modo}: Correcao de numero_nf='2025'")
    print(f"{'=' * 80}")

    # ---- PASSO 1: Corrigir numero_nf nas NFs reais ----
    print("\n--- PASSO 1: Corrigir numero_nf via chave de acesso ---")

    nfs_para_corrigir = db.session.execute(text("""
        SELECT id, numero_nf, chave_acesso_nf,
               CAST(CAST(substring(chave_acesso_nf from 26 for 9) AS bigint) AS text)
                   AS numero_real
        FROM carvia_nfs
        WHERE numero_nf = '2025'
          AND chave_acesso_nf IS NOT NULL
          AND length(chave_acesso_nf) = 44
        ORDER BY id
    """)).fetchall()

    if not nfs_para_corrigir:
        print("  Nenhuma NF com numero_nf='2025' encontrada. Abortando.")
        return

    mapeamento_id_numero = {}  # {nf_id: numero_real} para uso nos passos seguintes
    for nf in nfs_para_corrigir:
        mapeamento_id_numero[nf.id] = nf.numero_real
        print(f"  NF ID {nf.id}: '{nf.numero_nf}' -> '{nf.numero_real}'")

    if not dry_run:
        db.session.execute(text("""
            UPDATE carvia_nfs
            SET numero_nf = CAST(CAST(substring(chave_acesso_nf from 26 for 9) AS bigint) AS text)
            WHERE numero_nf = '2025'
              AND chave_acesso_nf IS NOT NULL
              AND length(chave_acesso_nf) = 44
        """))
        print(f"  -> {len(nfs_para_corrigir)} NFs corrigidas.")

    # ---- PASSO 2: Re-linkar itens de fatura dos stubs para NFs reais ----
    print("\n--- PASSO 2: Re-linkar itens de fatura ---")

    # Para cada NF real corrigida, encontrar stub correspondente pelo numero
    relinks = []
    for nf_real_id, numero_real in mapeamento_id_numero.items():
        stub = db.session.execute(text("""
            SELECT id FROM carvia_nfs
            WHERE tipo_fonte = 'FATURA_REFERENCIA'
              AND numero_nf = :numero
            ORDER BY id
            LIMIT 1
        """), {'numero': numero_real}).fetchone()

        if stub:
            relinks.append({'stub_id': stub.id, 'real_id': nf_real_id, 'numero': numero_real})
            print(f"  Stub ID {stub.id} (nf={numero_real}) -> NF real ID {nf_real_id}")

    if not relinks:
        print("  Nenhum stub correspondente encontrado.")
    else:
        # Re-linkar carvia_fatura_cliente_itens
        for r in relinks:
            count = db.session.execute(text("""
                SELECT count(*) FROM carvia_fatura_cliente_itens WHERE nf_id = :stub_id
            """), {'stub_id': r['stub_id']}).scalar() or 0

            if count > 0:
                print(f"  carvia_fatura_cliente_itens: {count} item(ns) nf_id={r['stub_id']} -> {r['real_id']}")
                if not dry_run:
                    db.session.execute(text("""
                        UPDATE carvia_fatura_cliente_itens
                        SET nf_id = :real_id
                        WHERE nf_id = :stub_id
                    """), {'real_id': r['real_id'], 'stub_id': r['stub_id']})

        # Re-linkar carvia_fatura_transportadora_itens (se houver)
        for r in relinks:
            count = db.session.execute(text("""
                SELECT count(*) FROM carvia_fatura_transportadora_itens WHERE nf_id = :stub_id
            """), {'stub_id': r['stub_id']}).scalar() or 0

            if count > 0:
                print(f"  carvia_fatura_transportadora_itens: {count} item(ns) nf_id={r['stub_id']} -> {r['real_id']}")
                if not dry_run:
                    db.session.execute(text("""
                        UPDATE carvia_fatura_transportadora_itens
                        SET nf_id = :real_id
                        WHERE nf_id = :stub_id
                    """), {'real_id': r['real_id'], 'stub_id': r['stub_id']})

    # ---- PASSO 3: Remover junctions dos stubs ----
    print("\n--- PASSO 3: Remover junctions dos stubs ---")

    stub_ids = [r['stub_id'] for r in relinks]
    if stub_ids:
        stub_ids_str = ', '.join(str(i) for i in stub_ids)
        junction_count = db.session.execute(text(f"""
            SELECT count(*) FROM carvia_operacao_nfs WHERE nf_id IN ({stub_ids_str})
        """)).scalar() or 0

        print(f"  {junction_count} junction(s) a remover para stub IDs: {stub_ids}")
        if not dry_run and junction_count > 0:
            db.session.execute(text(f"""
                DELETE FROM carvia_operacao_nfs WHERE nf_id IN ({stub_ids_str})
            """))
            print(f"  -> {junction_count} junctions removidas.")
    else:
        print("  Nenhum stub para limpar.")

    # ---- PASSO 4: Remover itens de NF e stubs orfaos ----
    print("\n--- PASSO 4: Remover stubs orfaos ---")

    if stub_ids:
        # Remover itens de NF dos stubs
        nf_itens_count = db.session.execute(text(f"""
            SELECT count(*) FROM carvia_nf_itens WHERE nf_id IN ({stub_ids_str})
        """)).scalar() or 0

        print(f"  {nf_itens_count} item(ns) de NF a remover")
        if not dry_run and nf_itens_count > 0:
            db.session.execute(text(f"""
                DELETE FROM carvia_nf_itens WHERE nf_id IN ({stub_ids_str})
            """))

        # Remover stubs
        print(f"  {len(stub_ids)} stub(s) FATURA_REFERENCIA a remover: IDs {stub_ids}")
        if not dry_run:
            db.session.execute(text(f"""
                DELETE FROM carvia_nfs WHERE id IN ({stub_ids_str})
            """))
            print(f"  -> {len(stub_ids)} stubs removidos.")
    else:
        print("  Nenhum stub para remover.")

    # ---- COMMIT ou ROLLBACK ----
    if dry_run:
        db.session.rollback()
        print(f"\n{'=' * 80}")
        print("DRY-RUN completo. Nenhuma mudanca aplicada.")
        print("Use --execute para aplicar as mudancas.")
        print(f"{'=' * 80}\n")
    else:
        db.session.commit()
        print(f"\n{'=' * 80}")
        print("CORRECAO APLICADA COM SUCESSO.")
        print(f"{'=' * 80}\n")


def verificar_pos_fix():
    """Verificacao pos-correcao"""
    print("\n" + "=" * 80)
    print("VERIFICACAO POS-CORRECAO")
    print("=" * 80)

    # Verificar que nao existem mais NFs com numero 2025
    restantes = db.session.execute(text("""
        SELECT count(*) FROM carvia_nfs WHERE numero_nf = '2025'
    """)).scalar()
    status1 = "OK" if restantes == 0 else "FALHA"
    print(f"\n  [{status1}] NFs com numero_nf='2025': {restantes} (esperado: 0)")

    # Verificar que NFs reais tem numero correto
    nfs_corrigidas = db.session.execute(text("""
        SELECT id, numero_nf, tipo_fonte FROM carvia_nfs
        WHERE id IN (18, 19, 20, 21)
        ORDER BY id
    """)).fetchall()
    print(f"\n  NFs corrigidas:")
    for nf in nfs_corrigidas:
        print(f"    ID {nf.id}: numero_nf='{nf.numero_nf}' ({nf.tipo_fonte})")

    # Verificar que stubs foram removidos
    stubs_restantes = db.session.execute(text("""
        SELECT count(*) FROM carvia_nfs WHERE id IN (41, 42, 43, 44)
    """)).scalar()
    status2 = "OK" if stubs_restantes == 0 else "FALHA"
    print(f"\n  [{status2}] Stubs restantes (IDs 41-44): {stubs_restantes} (esperado: 0)")

    # Verificar itens de fatura apontam para NFs reais
    itens_ok = db.session.execute(text("""
        SELECT fci.id, fci.nf_id, fci.nf_numero, cn.numero_nf as nf_numero_real
        FROM carvia_fatura_cliente_itens fci
        LEFT JOIN carvia_nfs cn ON cn.id = fci.nf_id
        WHERE fci.nf_id IN (18, 19, 20, 21)
        ORDER BY fci.nf_id
    """)).fetchall()
    print(f"\n  Itens de fatura vinculados a NFs reais: {len(itens_ok)}")
    for item in itens_ok:
        print(f"    Item ID {item.id}: nf_id={item.nf_id}, "
              f"nf_numero='{item.nf_numero}', nf_real='{item.nf_numero_real}'")

    print()


def main():
    parser = argparse.ArgumentParser(
        description='Fix: corrigir numero_nf=2025 extraido de "ANO 2025" no DANFE'
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
