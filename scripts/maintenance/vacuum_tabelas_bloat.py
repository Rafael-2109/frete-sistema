#!/usr/bin/env python3
"""
VACUUM ANALYZE em tabelas com bloat >10%.

Diagnosticado em 2026-02-28:
- 7 tabelas NUNCA receberam autovacuum
- Dead tuples acumulando (total: ~20,483 tuplas mortas)
- Bloat entre 11.6% e 16.8%

Uso:
    # Render Shell (recomendado):
    source .venv/bin/activate
    python scripts/maintenance/vacuum_tabelas_bloat.py

    # Dry-run (mostra estado atual sem executar VACUUM):
    python scripts/maintenance/vacuum_tabelas_bloat.py --dry-run

    # Apenas uma tabela:
    python scripts/maintenance/vacuum_tabelas_bloat.py --tabela movimentacao_estoque

Notas:
    - VACUUM nao bloqueia leituras (safe para producao)
    - ANALYZE atualiza estatisticas do planner
    - Tempo estimado: <1 min por tabela
    - NAO pode rodar via MCP (query_render_postgres e read-only)
"""

import argparse
import os
import sys
import time

# Setup path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Tabelas diagnosticadas com bloat >10% em 2026-02-28
TABELAS_BLOAT = [
    {"tabela": "movimentacao_estoque",         "bloat": 16.5, "dead_tuples": 12222},
    {"tabela": "extrato_item",                 "bloat": 16.2, "dead_tuples": 3611},
    {"tabela": "nf_devolucao",                 "bloat": 16.8, "dead_tuples": 846},
    {"tabela": "baixa_titulo_item",            "bloat": 12.5, "dead_tuples": 678},
    {"tabela": "conhecimento_transporte",      "bloat": 12.0, "dead_tuples": 661},
    {"tabela": "entregas_monitoradas",         "bloat": 11.8, "dead_tuples": 1662},
    {"tabela": "comprovante_pagamento_boleto", "bloat": 11.6, "dead_tuples": 803},
]


def get_connection():
    """Conecta ao banco usando DATABASE_URL do ambiente."""
    try:
        import psycopg2
    except ImportError:
        print("[ERRO] psycopg2 nao instalado. Execute: pip install psycopg2-binary")
        sys.exit(1)

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        # Fallback: tentar carregar do Flask app
        try:
            from app import create_app
            app = create_app()
            database_url = app.config.get("SQLALCHEMY_DATABASE_URI")
        except Exception:
            pass

    if not database_url:
        print("[ERRO] DATABASE_URL nao definida. Defina a env var ou execute dentro do contexto Flask.")
        sys.exit(1)

    # psycopg2 precisa de postgresql:// (nao postgres://)
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    conn = psycopg2.connect(database_url)
    # VACUUM nao pode rodar dentro de transacao
    conn.autocommit = True
    return conn


def get_table_stats(conn, tabela):
    """Consulta estatisticas atuais de uma tabela."""
    cur = conn.cursor()
    cur.execute("""
        SELECT
            n_live_tup,
            n_dead_tup,
            CASE WHEN n_live_tup + n_dead_tup > 0
                 THEN ROUND(100.0 * n_dead_tup / (n_live_tup + n_dead_tup), 1)
                 ELSE 0
            END AS bloat_pct,
            last_autovacuum,
            last_vacuum,
            last_autoanalyze,
            last_analyze,
            pg_size_pretty(pg_total_relation_size(%s)) AS total_size
        FROM pg_stat_user_tables
        WHERE relname = %s
    """, (tabela, tabela))
    row = cur.fetchone()
    cur.close()
    if row:
        return {
            "live_tuples": row[0],
            "dead_tuples": row[1],
            "bloat_pct": float(row[2]),
            "last_autovacuum": row[3],
            "last_vacuum": row[4],
            "last_autoanalyze": row[5],
            "last_analyze": row[6],
            "total_size": row[7],
        }
    return None


def run_vacuum(conn, tabela, dry_run=False):
    """Executa VACUUM ANALYZE em uma tabela."""
    stats_before = get_table_stats(conn, tabela)
    if not stats_before:
        print(f"  [SKIP] Tabela '{tabela}' nao encontrada")
        return False

    print(f"\n{'='*60}")
    print(f"  Tabela: {tabela}")
    print(f"  Tamanho: {stats_before['total_size']}")
    print(f"  Live tuples: {stats_before['live_tuples']:,}")
    print(f"  Dead tuples: {stats_before['dead_tuples']:,}")
    print(f"  Bloat: {stats_before['bloat_pct']}%")
    print(f"  Last vacuum: {stats_before['last_vacuum'] or 'NUNCA'}")
    print(f"  Last autovacuum: {stats_before['last_autovacuum'] or 'NUNCA'}")

    if dry_run:
        print(f"  [DRY-RUN] Nao executando VACUUM ANALYZE")
        return True

    print(f"  Executando VACUUM ANALYZE...", end=" ", flush=True)
    start = time.time()

    cur = conn.cursor()
    cur.execute(f"VACUUM ANALYZE {tabela}")
    cur.close()

    elapsed = time.time() - start
    print(f"OK ({elapsed:.1f}s)")

    # Verificar resultado
    stats_after = get_table_stats(conn, tabela)
    if stats_after:
        print(f"  Dead tuples: {stats_before['dead_tuples']:,} -> {stats_after['dead_tuples']:,}")
        print(f"  Bloat: {stats_before['bloat_pct']}% -> {stats_after['bloat_pct']}%")
        print(f"  Tamanho: {stats_before['total_size']} -> {stats_after['total_size']}")

    return True


def main():
    parser = argparse.ArgumentParser(
        description='VACUUM ANALYZE em tabelas com bloat >10%%'
    )
    parser.add_argument('--dry-run', action='store_true',
                        help='Mostra estado atual sem executar VACUUM')
    parser.add_argument('--tabela', type=str,
                        help='Executar apenas em uma tabela especifica')

    args = parser.parse_args()

    print("=" * 60)
    print("VACUUM ANALYZE — Tabelas com Bloat >10%%")
    print(f"Data do diagnostico: 2026-02-28")
    if args.dry_run:
        print("[MODO DRY-RUN — nenhuma alteracao sera feita]")
    print("=" * 60)

    # Filtrar tabela especifica se solicitado
    tabelas = TABELAS_BLOAT
    if args.tabela:
        tabelas = [t for t in tabelas if t["tabela"] == args.tabela]
        if not tabelas:
            print(f"[ERRO] Tabela '{args.tabela}' nao esta na lista de bloat.")
            print(f"Tabelas disponiveis: {', '.join(t['tabela'] for t in TABELAS_BLOAT)}")
            sys.exit(1)

    conn = get_connection()
    print(f"\nConectado ao banco. {len(tabelas)} tabela(s) para processar.\n")

    sucesso = 0
    erros = 0

    for info in tabelas:
        try:
            ok = run_vacuum(conn, info["tabela"], dry_run=args.dry_run)
            if ok:
                sucesso += 1
        except Exception as e:
            print(f"  [ERRO] {info['tabela']}: {e}")
            erros += 1

    conn.close()

    print(f"\n{'='*60}")
    print(f"RESULTADO: {sucesso} sucesso, {erros} erros")
    if args.dry_run:
        print("(dry-run: nenhuma acao executada)")
    print("=" * 60)


if __name__ == "__main__":
    main()
