"""Backfill: corrige a inflacao ~7x do custo do canal TEAMS (2026-06-28).

PROBLEMA: o path async do Teams (`app/teams/services.py` GAP 2) gravava
`agent_result.cost_usd` (= `ResultMessage.total_cost_usd`, ACUMULADO da sessao SDK)
CRU em `agent_session_costs.cost_usd` e somava em `agent_sessions.total_cost_usd`,
contando o acumulado N vezes -> inflacao ~Nx. O fix `0e9403082` (2026-06-19) corrigiu
o canal WEB mas NAO o Teams (o path Teams ficou de fora). Medido (30d): $320,87
gravado vs $46,65 real (fator 6,9x), 118 turnos 100% Opus.

FIX DE CODIGO (aplicado nesta sessao, services.py GAP 2 ~L2265): usa
`turn_cost_from_cumulative` (delta) igual ao web. Corrige o FUTURO.

ESTE SCRIPT corrige o HISTORICO ja gravado, APENAS para o canal Teams
(`agent_session_costs.message_id LIKE 'teams:%'`).

METODO = RECALCULO A PARTIR DOS TOKENS (nao o dedup-cumulativo do web). Razao: as
linhas Teams nos ultimos 30d sao uma MISTURA — as <=19/06 ja foram convertidas em
delta pelo backfill do web (que rodou sem filtro), as >19/06 ainda sao cumulativo
cru. Aplicar LAG-delta de novo estragaria as ja-delta. Os TOKENS (input/output/
cache) NUNCA foram afetados pelo bug — recalcular o custo deles com o pricing
oficial e o metodo CORRETO e UNIFORME, independente do que cada linha contem hoje.
E exatamente o calculo que produziu o $46,65 de referencia.

Pricing (skill claude-api, autoritativo):
  Opus 4.6/4.7/4.8 $5/$25 · Sonnet 4.5/4.6 $3/$15 · Haiku 4.5 $1/$5
  cache_read = 0,10x input · cache_creation = 1,25x input (assume TTL 5m)

IDEMPOTENTE + REVERSIVEL: cria backup com os valores ORIGINAIS (so das linhas/
sessoes Teams). Se o backup ja existe, --apply ABORTA; use --revert para desfazer.

CONEXAO: usa DATABASE_URL_PROD (escrita direta no prod; o MCP do Render e
read-only). NUNCA usa a DATABASE_URL local (banco de teste).

Uso:
    python scripts/migrations/2026_06_28_backfill_teams_cost.py            # dry-run
    python scripts/migrations/2026_06_28_backfill_teams_cost.py --apply    # efetiva (cria backup)
    python scripts/migrations/2026_06_28_backfill_teams_cost.py --revert   # restaura do backup
"""
import argparse
import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from sqlalchemy import create_engine, text  # noqa: E402

BKP_COSTS = 'bkp_teams_cost_backfill_costs'
BKP_SESSIONS = 'bkp_teams_cost_backfill_sessions'

# Expressao SQL do custo REAL do turno a partir dos tokens (pricing oficial).
# Aplicada por linha de agent_session_costs. Inputs em $/MTok.
RECALC = """
  CASE
    WHEN model LIKE '%opus%'   THEN (input_tokens*5 + cache_creation_tokens*5*1.25 + cache_read_tokens*5*0.10 + output_tokens*25)/1e6
    WHEN model LIKE '%sonnet%' THEN (input_tokens*3 + cache_creation_tokens*3*1.25 + cache_read_tokens*3*0.10 + output_tokens*15)/1e6
    WHEN model LIKE '%haiku%'  THEN (input_tokens*1 + cache_creation_tokens*1*1.25 + cache_read_tokens*1*0.10 + output_tokens*5)/1e6
    ELSE (input_tokens*5 + cache_creation_tokens*5*1.25 + cache_read_tokens*5*0.10 + output_tokens*25)/1e6
  END
"""

TEAMS_FILTER = "message_id LIKE 'teams:%'"


def _engine():
    url = os.environ.get('DATABASE_URL_PROD')
    if not url or not url.strip():
        print("ERRO: DATABASE_URL_PROD nao definida (ou vazia) no ambiente/.env.")
        print("      Defina a URL do Postgres de PRODUCAO antes de rodar (contem senha).")
        sys.exit(2)
    # Render usa 'postgres://'; SQLAlchemy quer 'postgresql://'
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)
    return create_engine(url)


def _table_exists(conn, name: str) -> bool:
    return bool(conn.execute(
        text("SELECT to_regclass(:n) IS NOT NULL"), {'n': f'public.{name}'}).scalar())


def _diag(conn):
    r = conn.execute(text(f"""
        SELECT COUNT(*) AS linhas,
               COUNT(DISTINCT session_id) AS sessoes,
               ROUND(SUM(cost_usd)::numeric, 2) AS gravado,
               ROUND(SUM({RECALC})::numeric, 2) AS real_recalc
        FROM agent_session_costs WHERE {TEAMS_FILTER}
    """)).mappings().first()
    return dict(r) if r else {}


def _print_diag(conn):
    d = _diag(conn)
    if not d or not d.get('linhas'):
        print('  (nenhuma linha Teams em agent_session_costs)')
        return d
    g, rr = float(d['gravado'] or 0), float(d['real_recalc'] or 0)
    fator = (g / rr) if rr else 0
    print(f"  Linhas Teams: {d['linhas']} | Sessoes: {d['sessoes']}")
    print(f"  cost_usd gravado (atual): ${g:,.2f}")
    print(f"  Real (recalc tokens):     ${rr:,.2f}   (fator {fator:.1f}x)")
    return d


def _apply(conn):
    if _table_exists(conn, BKP_COSTS) or _table_exists(conn, BKP_SESSIONS):
        print(f"ABORTADO: backup ja existe ({BKP_COSTS}/{BKP_SESSIONS}) = backfill ja aplicado.")
        print("Para reverter:  --revert")
        return
    print("=== ANTES ===")
    _print_diag(conn)

    # 1) Backup dos valores ORIGINAIS (so Teams).
    conn.execute(text(
        f"CREATE TABLE {BKP_COSTS} AS "
        f"SELECT id, cost_usd FROM agent_session_costs WHERE {TEAMS_FILTER}"))
    conn.execute(text(
        f"CREATE TABLE {BKP_SESSIONS} AS "
        f"SELECT DISTINCT s.session_id, s.total_cost_usd "
        f"FROM agent_sessions s "
        f"WHERE EXISTS (SELECT 1 FROM agent_session_costs c "
        f"             WHERE c.session_id = s.session_id AND c.{TEAMS_FILTER})"))

    # 2) cost_usd da linha = custo real recalculado dos tokens (so Teams).
    conn.execute(text(
        f"UPDATE agent_session_costs SET cost_usd = {RECALC} WHERE {TEAMS_FILTER}"))

    # 3) total_cost_usd da sessao = soma dos cost_usd (ja recalculados) das suas linhas.
    #    Restrito as sessoes que tem linhas Teams (do backup).
    conn.execute(text(f"""
        UPDATE agent_sessions s
        SET total_cost_usd = COALESCE(agg.soma, 0)
        FROM (SELECT session_id, SUM(cost_usd) AS soma
              FROM agent_session_costs GROUP BY session_id) agg
        WHERE s.session_id = agg.session_id
          AND s.session_id IN (SELECT session_id FROM {BKP_SESSIONS})
    """))
    conn.commit()

    print("\n=== DEPOIS ===")
    _print_diag(conn)
    print(f"  Backup criado: {BKP_COSTS}, {BKP_SESSIONS}")
    print("  OK — backfill Teams aplicado.")


def _revert(conn):
    if not (_table_exists(conn, BKP_COSTS) and _table_exists(conn, BKP_SESSIONS)):
        print(f"ABORTADO: backup nao encontrado ({BKP_COSTS}/{BKP_SESSIONS}). Nada a reverter.")
        return
    conn.execute(text(
        f"UPDATE agent_session_costs c SET cost_usd = b.cost_usd "
        f"FROM {BKP_COSTS} b WHERE c.id = b.id"))
    conn.execute(text(
        f"UPDATE agent_sessions s SET total_cost_usd = b.total_cost_usd "
        f"FROM {BKP_SESSIONS} b WHERE s.session_id = b.session_id"))
    conn.execute(text(f"DROP TABLE {BKP_COSTS}"))
    conn.execute(text(f"DROP TABLE {BKP_SESSIONS}"))
    conn.commit()
    print("OK — valores originais (Teams) restaurados e backup removido.")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group()
    g.add_argument('--apply', action='store_true', help='efetiva o backfill (cria backup)')
    g.add_argument('--revert', action='store_true', help='restaura do backup e remove')
    args = ap.parse_args()

    eng = _engine()
    with eng.connect() as conn:
        host = str(eng.url.host)
        print(f"Conectado em: {host}\n")
        if args.revert:
            _revert(conn)
        elif args.apply:
            _apply(conn)
        else:
            print("=== DRY-RUN (nenhuma escrita) ===")
            _print_diag(conn)
            print("\nPara efetivar:  --apply   |   Para reverter depois:  --revert")


if __name__ == '__main__':
    main()
