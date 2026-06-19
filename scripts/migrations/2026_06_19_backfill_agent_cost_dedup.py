"""Backfill: corrige o DOUBLE-COUNTING de custo do Agente Web (2026-06-19).

PROBLEMA: `ResultMessage.total_cost_usd` do Claude Agent SDK e o custo ACUMULADO
da sessao SDK (running total que cresce a cada turno). O codigo gravava esse
acumulado por-turno em `agent_session_costs.cost_usd` e somava em
`agent_sessions.total_cost_usd` (`routes/chat.py:_save_messages_to_db`), contando
o acumulado N vezes -> inflacao ~Nx (N = turnos).

  Caso real (user_id 78, Rayssa):
    sessao 17b68633: reportado $223.59  -> real  $31.92  (13 turnos, 7.0x)
    sessao 92516689: reportado $102.90  -> real  $19.22  (17 turnos, 5.4x)
  Global 30d (medido em prod): reportado $1387.03 -> real ~$465.28 (3.0x).

FIX DE CODIGO (ja aplicado): `pricing.turn_cost_from_cumulative` converte o
acumulado no DELTA do turno; o acumulado anterior vive em
`agent_sessions.data['_sdk_cost_cumulative']`.

ESTE SCRIPT corrige o HISTORICO ja gravado:
  1. `agent_session_costs.cost_usd`  -> delta do turno (a partir do acumulado).
  2. `agent_sessions.total_cost_usd` -> soma dos deltas (= custo real).
  3. `agent_sessions.data['_sdk_cost_cumulative' / '_sdk_cost_session_id']` ->
     ultimo acumulado conhecido, para sessoes ANTIGAS que continuarem pos-fix
     calcularem o delta do proximo turno corretamente.

Deteccao de RESET de sessao SDK (resume/nova sessao): o acumulado CAI vs o turno
anterior (mesma logica do helper, por queda de valor). Cada segmento contribui
com seu pico -> custo real = soma dos picos.

IDEMPOTENTE + REVERSIVEL: cria tabelas de backup com os valores ORIGINAIS. Se o
backup ja existe, --apply ABORTA (ja aplicado); use --revert para desfazer.

ATENCAO (dados de PRODUCAO = Render): rodar no shell do Render (o MCP do Render e
read-only e nao aplica escrita). Local = banco de teste.

Uso:
    python scripts/migrations/2026_06_19_backfill_agent_cost_dedup.py            # dry-run (relatorio)
    python scripts/migrations/2026_06_19_backfill_agent_cost_dedup.py --apply    # efetiva (cria backup)
    python scripts/migrations/2026_06_19_backfill_agent_cost_dedup.py --revert   # restaura do backup
"""
import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import text  # noqa: E402

from app import create_app, db  # noqa: E402

logger = logging.getLogger(__name__)

BKP_COSTS = 'bkp_agent_cost_dedup_costs'
BKP_SESSIONS = 'bkp_agent_cost_dedup_sessions'


def _table_exists(name: str) -> bool:
    row = db.session.execute(
        text("SELECT to_regclass(:n) IS NOT NULL AS ok"), {'n': f'public.{name}'}
    ).scalar()
    return bool(row)


def _diagnostico():
    """Reportado (soma atual) vs real estimado (soma dos picos de segmento)."""
    sql = text("""
        WITH ordered AS (
          SELECT session_id, cost_usd,
                 LEAD(cost_usd) OVER (PARTITION BY session_id ORDER BY recorded_at, id) AS next_cost
          FROM agent_session_costs
        )
        SELECT
          ROUND(SUM(cost_usd), 2) AS reportado,
          ROUND(SUM(CASE WHEN next_cost IS NULL OR next_cost < cost_usd THEN cost_usd ELSE 0 END), 2) AS real_est,
          COUNT(DISTINCT session_id) AS sessoes,
          COUNT(*) AS linhas
        FROM ordered
    """)
    r = db.session.execute(sql).mappings().first()
    return dict(r) if r else {}


def _top_afetadas(limit=10):
    sql = text("""
        WITH ordered AS (
          SELECT session_id, user_id, cost_usd,
                 LEAD(cost_usd) OVER (PARTITION BY session_id ORDER BY recorded_at, id) AS next_cost
          FROM agent_session_costs
        )
        SELECT session_id, MAX(user_id) AS user_id, COUNT(*) AS turnos,
               ROUND(SUM(cost_usd), 2) AS reportado,
               ROUND(SUM(CASE WHEN next_cost IS NULL OR next_cost < cost_usd THEN cost_usd ELSE 0 END), 2) AS real_est
        FROM ordered
        GROUP BY session_id
        HAVING COUNT(*) > 1
        ORDER BY (SUM(cost_usd) - SUM(CASE WHEN next_cost IS NULL OR next_cost < cost_usd THEN cost_usd ELSE 0 END)) DESC
        LIMIT :lim
    """)
    return [dict(r) for r in db.session.execute(sql, {'lim': limit}).mappings()]


def _print_diag():
    d = _diagnostico()
    if not d or not d.get('linhas'):
        print('  (agent_session_costs vazia — nada a fazer)')
        return d
    inflado = (float(d['reportado']) / float(d['real_est'])) if d.get('real_est') else 0
    print(f"  Linhas: {d['linhas']} | Sessoes: {d['sessoes']}")
    print(f"  Reportado (atual): ${d['reportado']}")
    print(f"  Real estimado:     ${d['real_est']}   (fator {inflado:.1f}x)")
    print("\n  Top sessoes a corrigir (reportado -> real):")
    for s in _top_afetadas():
        print(f"    {s['session_id'][:12]}  u{s['user_id']}  {s['turnos']:>3} turnos  "
              f"${s['reportado']:>8} -> ${s['real_est']:>8}")
    return d


def _apply():
    if _table_exists(BKP_COSTS) or _table_exists(BKP_SESSIONS):
        print(f"ABORTADO: backup ja existe ({BKP_COSTS}/{BKP_SESSIONS}) = backfill ja aplicado.")
        print("Para reverter:  --revert")
        return False

    print("=== ANTES ===")
    _print_diag()

    # 1) Backup dos valores ORIGINAIS (fonte de verdade p/ revert + idempotencia).
    db.session.execute(text(
        f"CREATE TABLE {BKP_COSTS} AS SELECT id, cost_usd FROM agent_session_costs"))
    db.session.execute(text(
        f"CREATE TABLE {BKP_SESSIONS} AS "
        f"SELECT session_id, total_cost_usd FROM agent_sessions"))

    # 2) cost_usd por turno = delta vs acumulado anterior (reset = queda de valor).
    db.session.execute(text("""
        WITH base AS (
          SELECT id, cost_usd,
                 LAG(cost_usd) OVER (PARTITION BY session_id ORDER BY recorded_at, id) AS prev
          FROM agent_session_costs
        )
        UPDATE agent_session_costs c
        SET cost_usd = CASE
              WHEN b.prev IS NULL        THEN b.cost_usd          -- 1o turno do segmento
              WHEN b.cost_usd < b.prev   THEN b.cost_usd          -- reset (acumulado caiu)
              ELSE b.cost_usd - b.prev                            -- delta normal
            END
        FROM base b
        WHERE c.id = b.id
    """))

    # 3) total_cost_usd da sessao = soma dos deltas.
    db.session.execute(text("""
        UPDATE agent_sessions s
        SET total_cost_usd = COALESCE(agg.soma, 0)
        FROM (SELECT session_id, SUM(cost_usd) AS soma
              FROM agent_session_costs GROUP BY session_id) agg
        WHERE s.session_id = agg.session_id
    """))

    # 4) Memoriza o ULTIMO acumulado (do backup) p/ sessoes antigas que continuarem
    #    calcularem o delta do proximo turno corretamente (espelha o fix de codigo).
    db.session.execute(text(f"""
        UPDATE agent_sessions s
        SET data = jsonb_set(
                     jsonb_set(COALESCE(s.data, '{{}}'::jsonb),
                               '{{_sdk_cost_cumulative}}', to_jsonb(lc.last_cumulative)),
                     '{{_sdk_cost_session_id}}', COALESCE(s.data->'sdk_session_id', 'null'::jsonb))
        FROM (
          SELECT b.id, asc2.session_id, b.cost_usd AS last_cumulative,
                 ROW_NUMBER() OVER (PARTITION BY asc2.session_id
                                    ORDER BY asc2.recorded_at DESC, asc2.id DESC) AS rn
          FROM {BKP_COSTS} b
          JOIN agent_session_costs asc2 ON asc2.id = b.id
        ) lc
        WHERE s.session_id = lc.session_id AND lc.rn = 1
    """))

    db.session.commit()

    print("\n=== DEPOIS ===")
    d = _diagnostico()
    print(f"  total_cost_usd somado (linhas): ${d.get('reportado')}")
    print(f"  Backup criado: {BKP_COSTS}, {BKP_SESSIONS}")
    print("  OK — backfill aplicado.")
    return True


def _revert():
    if not (_table_exists(BKP_COSTS) and _table_exists(BKP_SESSIONS)):
        print(f"ABORTADO: backup nao encontrado ({BKP_COSTS}/{BKP_SESSIONS}). Nada a reverter.")
        return False

    db.session.execute(text(f"""
        UPDATE agent_session_costs c SET cost_usd = b.cost_usd
        FROM {BKP_COSTS} b WHERE c.id = b.id
    """))
    db.session.execute(text(f"""
        UPDATE agent_sessions s SET total_cost_usd = b.total_cost_usd
        FROM {BKP_SESSIONS} b WHERE s.session_id = b.session_id
    """))
    # Remove as chaves de estado introduzidas pelo backfill.
    db.session.execute(text("""
        UPDATE agent_sessions
        SET data = (data - '_sdk_cost_cumulative') - '_sdk_cost_session_id'
        WHERE data ? '_sdk_cost_cumulative' OR data ? '_sdk_cost_session_id'
    """))
    db.session.execute(text(f"DROP TABLE {BKP_COSTS}"))
    db.session.execute(text(f"DROP TABLE {BKP_SESSIONS}"))
    db.session.commit()
    print("OK — valores originais restaurados e backup removido.")
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group()
    g.add_argument('--apply', action='store_true', help='efetiva o backfill (cria backup)')
    g.add_argument('--revert', action='store_true', help='restaura do backup e remove o estado')
    args = ap.parse_args()

    app = create_app()
    with app.app_context():
        if args.revert:
            _revert()
        elif args.apply:
            _apply()
        else:
            print("=== DRY-RUN (nenhuma escrita) ===")
            _print_diag()
            print("\nPara efetivar:  --apply   |   Para reverter depois:  --revert")


if __name__ == '__main__':
    main()
