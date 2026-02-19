"""
Script Retroativo: Preencher metodo_baixa em titulos existentes.

Ordem de prioridade (mais especifico primeiro):
1. CNAB → via FK (cnab_retorno_item.conta_a_receber_id IS NOT NULL)
2. CNAB → via NF+parcela fallback (cnab_retorno_item sem FK vinculada)
3. CNAB → via status_pagamento_odoo (PAGO_CNAB, PAGO_CNAB_AUTO)
4. EXCEL → contas_a_receber (via baixa_titulo_item, comparacao int)
5. COMPROVANTE → contas_a_pagar (via odoo_line_id + NF+parcela)
6. EXTRATO → contas_a_receber (via extrato_item FK ou extrato_item_titulo M:N)
7. EXTRATO → contas_a_pagar (via extrato_item FK ou extrato_item_titulo M:N)
8. ODOO_DIRETO → catch-all para parcela_paga=True sem metodo_baixa

Flags:
  --dry-run   Mostra quantos registros SERIAM afetados por cada passo (sem UPDATE)
  --reset     Limpa metodo_baixa antes de re-classificar (SET metodo_baixa = NULL)

IMPORTANTE: Executar APOS a migration adicionar_metodo_baixa.py
Executar: source .venv/bin/activate && python scripts/migrations/preencher_metodo_baixa_retroativo.py [--dry-run] [--reset]
"""
import re
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db

# ── Definicao dos passos (SQL de UPDATE) ──

PASSOS = [
    # ── 1. CNAB via FK → contas_a_receber ──
    ("1", "CNAB -> contas_a_receber (via FK)", """
        UPDATE contas_a_receber
        SET metodo_baixa = 'CNAB'
        WHERE parcela_paga = TRUE
          AND metodo_baixa IS NULL
          AND id IN (
              SELECT conta_a_receber_id
              FROM cnab_retorno_item
              WHERE conta_a_receber_id IS NOT NULL
                AND codigo_ocorrencia IN ('06', '10', '17')
          )
    """),

    # ── 2. CNAB via NF+parcela fallback → contas_a_receber ──
    # Para cnab_retorno_item com codigo liquidacao mas sem FK vinculada
    ("2", "CNAB -> contas_a_receber (via NF+parcela fallback)", """
        UPDATE contas_a_receber cr
        SET metodo_baixa = 'CNAB'
        WHERE cr.parcela_paga = TRUE
          AND cr.metodo_baixa IS NULL
          AND EXISTS (
              SELECT 1
              FROM cnab_retorno_item cri
              WHERE cri.conta_a_receber_id IS NULL
                AND cri.codigo_ocorrencia IN ('06', '10', '17')
                AND cri.nf_extraida = cr.titulo_nf
                AND cri.parcela_extraida = cr.parcela
          )
    """),

    # ── 3. CNAB via status_pagamento_odoo → contas_a_receber ──
    # Titulos marcados com status CNAB no Odoo mas sem vinculo ao retorno
    ("3", "CNAB -> contas_a_receber (via status_pagamento_odoo)", """
        UPDATE contas_a_receber
        SET metodo_baixa = 'CNAB'
        WHERE parcela_paga = TRUE
          AND metodo_baixa IS NULL
          AND status_pagamento_odoo IN ('PAGO_CNAB', 'PAGO_CNAB_AUTO')
    """),

    # ── 4. EXCEL via NF+parcela → contas_a_receber ──
    # Fix: comparacao como int (antes: CAST AS TEXT falhava '1' vs '01')
    ("4", "EXCEL -> contas_a_receber (via NF+parcela)", """
        UPDATE contas_a_receber cr
        SET metodo_baixa = 'EXCEL'
        WHERE cr.parcela_paga = TRUE
          AND cr.metodo_baixa IS NULL
          AND EXISTS (
              SELECT 1
              FROM baixa_titulo_item bti
              WHERE bti.nf_excel = cr.titulo_nf
                AND bti.status = 'SUCESSO'
                AND bti.parcela_excel = NULLIF(regexp_replace(cr.parcela, '[^0-9]', '', 'g'), '')::int
          )
    """),

    # ── 5a. COMPROVANTE → contas_a_pagar (via odoo_line_id) ──
    ("5a", "COMPROVANTE -> contas_a_pagar (via odoo_line_id)", """
        UPDATE contas_a_pagar cp
        SET metodo_baixa = 'COMPROVANTE'
        WHERE cp.parcela_paga = TRUE
          AND cp.metodo_baixa IS NULL
          AND cp.odoo_line_id IS NOT NULL
          AND EXISTS (
              SELECT 1
              FROM lancamento_comprovante lc
              WHERE lc.odoo_move_line_id = cp.odoo_line_id
                AND lc.status = 'LANCADO'
          )
    """),

    # ── 5b. COMPROVANTE → contas_a_pagar (via NF+parcela) ──
    ("5b", "COMPROVANTE -> contas_a_pagar (via NF+parcela)", """
        UPDATE contas_a_pagar cp
        SET metodo_baixa = 'COMPROVANTE'
        WHERE cp.parcela_paga = TRUE
          AND cp.metodo_baixa IS NULL
          AND EXISTS (
              SELECT 1
              FROM lancamento_comprovante lc
              WHERE lc.nf_numero = cp.titulo_nf
                AND CAST(lc.parcela AS TEXT) = NULLIF(regexp_replace(cp.parcela, '[^0-9]', '', 'g'), '')
                AND lc.status = 'LANCADO'
          )
    """),

    # ── 6a. EXTRATO → contas_a_receber (via FK legacy) ──
    ("6a", "EXTRATO -> contas_a_receber (via FK legacy)", """
        UPDATE contas_a_receber cr
        SET metodo_baixa = 'EXTRATO'
        WHERE cr.parcela_paga = TRUE
          AND cr.metodo_baixa IS NULL
          AND EXISTS (
              SELECT 1
              FROM extrato_item ei
              WHERE ei.titulo_receber_id = cr.id
                AND ei.status = 'CONCILIADO'
          )
    """),

    # ── 6b. EXTRATO → contas_a_receber (via M:N) ──
    ("6b", "EXTRATO -> contas_a_receber (via M:N)", """
        UPDATE contas_a_receber cr
        SET metodo_baixa = 'EXTRATO'
        WHERE cr.parcela_paga = TRUE
          AND cr.metodo_baixa IS NULL
          AND EXISTS (
              SELECT 1
              FROM extrato_item_titulo eit
              JOIN extrato_item ei ON ei.id = eit.extrato_item_id
              WHERE eit.titulo_receber_id = cr.id
                AND eit.status = 'CONCILIADO'
          )
    """),

    # ── 7a. EXTRATO → contas_a_pagar (via FK legacy) ──
    ("7a", "EXTRATO -> contas_a_pagar (via FK legacy)", """
        UPDATE contas_a_pagar cp
        SET metodo_baixa = 'EXTRATO'
        WHERE cp.parcela_paga = TRUE
          AND cp.metodo_baixa IS NULL
          AND EXISTS (
              SELECT 1
              FROM extrato_item ei
              WHERE ei.titulo_pagar_id = cp.id
                AND ei.status = 'CONCILIADO'
          )
    """),

    # ── 7b. EXTRATO → contas_a_pagar (via M:N) ──
    ("7b", "EXTRATO -> contas_a_pagar (via M:N)", """
        UPDATE contas_a_pagar cp
        SET metodo_baixa = 'EXTRATO'
        WHERE cp.parcela_paga = TRUE
          AND cp.metodo_baixa IS NULL
          AND EXISTS (
              SELECT 1
              FROM extrato_item_titulo eit
              JOIN extrato_item ei ON ei.id = eit.extrato_item_id
              WHERE eit.titulo_pagar_id = cp.id
                AND eit.status = 'CONCILIADO'
          )
    """),

    # ── 8a. ODOO_DIRETO → contas_a_receber (catch-all) ──
    ("8a", "ODOO_DIRETO -> contas_a_receber (catch-all)", """
        UPDATE contas_a_receber
        SET metodo_baixa = 'ODOO_DIRETO'
        WHERE parcela_paga = TRUE
          AND metodo_baixa IS NULL
    """),

    # ── 8b. ODOO_DIRETO → contas_a_pagar (catch-all) ──
    ("8b", "ODOO_DIRETO -> contas_a_pagar (catch-all)", """
        UPDATE contas_a_pagar
        SET metodo_baixa = 'ODOO_DIRETO'
        WHERE parcela_paga = TRUE
          AND metodo_baixa IS NULL
    """),
]


def contar_estado(conn, label):
    """Mostra distribuicao atual de metodo_baixa."""
    print(f"\n{'=' * 60}")
    print(f"{label}")
    print(f"{'=' * 60}")

    for tabela in ['contas_a_receber', 'contas_a_pagar']:
        result = conn.execute(db.text(f"""
            SELECT
                metodo_baixa,
                COUNT(*) as qtd
            FROM {tabela}
            WHERE parcela_paga = TRUE
            GROUP BY metodo_baixa
            ORDER BY metodo_baixa NULLS FIRST
        """))
        rows = result.fetchall()
        total = sum(r[1] for r in rows)
        print(f"\n  {tabela} (total pagos: {total}):")
        for row in rows:
            metodo = row[0] or '(NULL)'
            pct = (row[1] / total * 100) if total > 0 else 0
            print(f"    {metodo}: {row[1]} ({pct:.1f}%)")


def validar_inconsistencias(conn):
    """Mostra titulos com inconsistencias conhecidas apos o preenchimento."""
    print(f"\n{'=' * 60}")
    print("VALIDACAO: Inconsistencias de dados")
    print(f"{'=' * 60}")

    # 1. Contradicao: not_paid/reversed mas parcela_paga=True
    for tabela in ['contas_a_receber', 'contas_a_pagar']:
        result = conn.execute(db.text(f"""
            SELECT status_pagamento_odoo, COUNT(*) as qtd
            FROM {tabela}
            WHERE parcela_paga = TRUE
              AND status_pagamento_odoo IN ('not_paid', 'reversed')
            GROUP BY status_pagamento_odoo
            ORDER BY status_pagamento_odoo
        """))
        rows = result.fetchall()
        if rows:
            print(f"\n  AVISO {tabela}: parcela_paga=True com status inconsistente:")
            for row in rows:
                print(f"    {row[0]}: {row[1]} titulos")
        else:
            print(f"\n  OK {tabela}: sem contradicao parcela_paga vs status_pagamento_odoo")

    # 2. parcela_paga=True mas sem metodo_baixa (nao deveria existir apos script)
    for tabela in ['contas_a_receber', 'contas_a_pagar']:
        result = conn.execute(db.text(f"""
            SELECT COUNT(*)
            FROM {tabela}
            WHERE parcela_paga = TRUE AND metodo_baixa IS NULL
        """))
        nulls = result.scalar() or 0
        if nulls > 0:
            print(f"\n  AVISO: {tabela} ainda tem {nulls} pagos sem metodo_baixa!")
        else:
            print(f"\n  OK: {tabela} -- todos os pagos tem metodo_baixa preenchido")


def update_para_count(sql_update):
    """Transforma UPDATE ... SET ... WHERE ... em SELECT COUNT(*) FROM ... WHERE ..."""
    # Encontra SET como palavra isolada (nao dentro de 'reset', 'offset', etc.)
    match_set = re.search(r'\bSET\b', sql_update, re.IGNORECASE)
    match_where = re.search(r'\bWHERE\b', sql_update, re.IGNORECASE)

    if not match_set or not match_where:
        raise ValueError(f"SQL invalido para conversao dry-run: {sql_update[:80]}...")

    # Tabela: entre UPDATE e SET
    update_pos = re.search(r'\bUPDATE\b', sql_update, re.IGNORECASE).end()
    tabela_part = sql_update[update_pos:match_set.start()].strip()

    # WHERE clause: do WHERE ate o final
    where_clause = sql_update[match_where.start():]

    return f"SELECT COUNT(*) FROM {tabela_part} {where_clause}"


def executar_passos(conn, passos, dry_run):
    """Executa todos os passos (UPDATE ou SELECT COUNT dry-run)."""
    total = 0
    for passo, descricao, sql in passos:
        if dry_run:
            sql_count = update_para_count(sql)
            result = conn.execute(db.text(sql_count))
            count = result.scalar() or 0
            print(f"  {passo}. {descricao}: {count} registros (dry-run)")
            total += count
        else:
            result = conn.execute(db.text(sql))
            print(f"  {passo}. {descricao}: {result.rowcount} registros")
            total += result.rowcount
    return total


def main():
    dry_run = '--dry-run' in sys.argv
    reset = '--reset' in sys.argv

    app = create_app()

    with app.app_context():
        # ── BEFORE ──
        with db.engine.connect() as conn:
            contar_estado(conn, "BEFORE: Estado antes do preenchimento")

        # ── RESET (opcional) ──
        if reset and not dry_run:
            print(f"\n{'=' * 60}")
            print("RESET: Limpando metodo_baixa para re-classificacao")
            print(f"{'=' * 60}")
            with db.engine.begin() as conn:
                for tabela in ['contas_a_receber', 'contas_a_pagar']:
                    result = conn.execute(db.text(f"""
                        UPDATE {tabela}
                        SET metodo_baixa = NULL
                        WHERE parcela_paga = TRUE
                    """))
                    print(f"  {tabela}: {result.rowcount} registros resetados")
        elif reset and dry_run:
            print(f"\n  (dry-run: --reset seria executado antes dos passos)")

        # ── EXECUTE ──
        modo = "DRY-RUN (nenhum dado sera alterado)" if dry_run else "Preenchendo metodo_baixa retroativo"
        print(f"\n{'=' * 60}")
        print(f"EXECUTE: {modo}")
        print(f"{'=' * 60}")

        if dry_run:
            # Dry-run: conexao read-only, sem transacao de escrita
            with db.engine.connect() as conn:
                total = executar_passos(conn, PASSOS, dry_run=True)
                print(f"\n  TOTAL: {total} registros seriam afetados")
                print("  NOTA: em dry-run, passos posteriores podem contar registros")
                print("  que seriam capturados por passos anteriores (contagem cumulativa)")
        else:
            # Execucao real: transacao unica com auto-commit
            with db.engine.begin() as conn:
                total = executar_passos(conn, PASSOS, dry_run=False)
                print(f"\n  TOTAL: {total} registros atualizados")

        # ── AFTER ──
        with db.engine.connect() as conn:
            contar_estado(conn, "AFTER: Estado apos preenchimento")
            validar_inconsistencias(conn)

        print(f"\n{'=' * 60}")
        if dry_run:
            print("DRY-RUN concluido. Nenhum dado foi alterado.")
            print("Para executar de verdade, remova --dry-run")
        else:
            print("Script retroativo concluido com SUCESSO!")
        print(f"{'=' * 60}")


if __name__ == '__main__':
    main()
