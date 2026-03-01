"""
VACUUM ANALYZE em tabelas criticas com dead tuple ratio > 10%

Identificadas na avaliacao de 01/03/2026:
- picking_recebimento_quality_check: 20.09% dead tuples
- embarques: 15.71%
- baixa_titulo_item: 12.45% (NUNCA recebeu autovacuum)
- embarque_itens: 11.93% (NUNCA recebeu autovacuum)
- controle_portaria: 11.33% (NUNCA recebeu autovacuum)
- separacao: 10.84%
- lancamento_comprovante: 10.16% (NUNCA recebeu autovacuum)
- fretes: 10.20% (NUNCA recebeu autovacuum)

VACUUM nao pode rodar dentro de transacao.
Executar via: Render Shell (psql) ou este script Python com autocommit.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


TABELAS_CRITICAS = [
    'picking_recebimento_quality_check',
    'embarques',
    'baixa_titulo_item',
    'embarque_itens',
    'controle_portaria',
    'separacao',
    'lancamento_comprovante',
    'fretes',
]


def verificar_dead_tuples():
    """Verifica estado atual de dead tuples ANTES do vacuum"""
    app = create_app()
    with app.app_context():
        resultado = db.session.execute(text("""
            SELECT
                relname AS tabela,
                n_live_tup AS live,
                n_dead_tup AS dead,
                CASE WHEN n_live_tup > 0
                    THEN ROUND(100.0 * n_dead_tup / n_live_tup, 2)
                    ELSE 0
                END AS dead_ratio,
                last_autovacuum
            FROM pg_stat_user_tables
            WHERE relname = ANY(:tabelas)
            ORDER BY dead_ratio DESC
        """), {'tabelas': TABELAS_CRITICAS})

        rows = resultado.fetchall()

        print(f"\n{'='*80}")
        print(f"{'TABELA':<45} {'LIVE':>8} {'DEAD':>8} {'RATIO':>8} {'ULTIMO VACUUM'}")
        print(f"{'='*80}")

        for r in rows:
            status = 'CRITICO' if (r.dead_ratio or 0) > 10 else 'OK'
            ultimo = str(r.last_autovacuum)[:19] if r.last_autovacuum else 'NUNCA'
            print(f"  {r.tabela:<43} {r.live:>8} {r.dead:>8} {r.dead_ratio:>7}% {ultimo} [{status}]")

        return rows


def executar_vacuum():
    """Executa VACUUM ANALYZE em cada tabela critica"""
    app = create_app()
    with app.app_context():
        # VACUUM requer autocommit (nao pode rodar em transacao)
        engine = db.engine
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            for tabela in TABELAS_CRITICAS:
                print(f"\n  VACUUM ANALYZE {tabela}...", end=' ', flush=True)
                try:
                    conn.execute(text(f"VACUUM ANALYZE {tabela}"))
                    print("OK")
                except Exception as e:
                    print(f"ERRO: {e}")


if __name__ == '__main__':
    print("=" * 80)
    print("VACUUM ANALYZE — TABELAS CRITICAS (dead tuple ratio > 10%)")
    print("=" * 80)

    dry_run = '--execute' not in sys.argv

    print("\n[ANTES] Estado atual:")
    verificar_dead_tuples()

    if dry_run:
        print(f"\n{'='*80}")
        print("[DRY RUN] Nenhuma acao executada.")
        print(f"Para executar: python {__file__} --execute")
        print(f"Ou via Render Shell: copiar comandos de vacuum_analyze_tabelas_criticas.sql")
        print(f"{'='*80}")
    else:
        print(f"\n{'='*80}")
        print("EXECUTANDO VACUUM ANALYZE...")
        print(f"{'='*80}")
        executar_vacuum()

        print("\n[DEPOIS] Estado atualizado:")
        verificar_dead_tuples()

        print(f"\n{'='*80}")
        print("VACUUM ANALYZE concluido.")
        print(f"{'='*80}")
