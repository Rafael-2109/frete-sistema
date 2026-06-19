"""Backfill: corrige o FUSO de `agent_invocation_metrics.started_at` (2026-06-19).

PROBLEMA: `_parse_iso_timestamp` (sdk/subagent_reader.py) gravava o timestamp do
JSONL do subagente (ISO 'Z' = UTC) como UTC-naive, enquanto o resto do sistema usa
Brasil-naive (REGRAS_TIMEZONE.md) — inclusive `recorded_at`. Resultado: started_at
~3h ADIANTADO; 206/206 linhas com `started_at > recorded_at` (impossivel), quebrando
analise temporal por janela.

FIX DE CODIGO (ja aplicado): `_parse_iso_timestamp` converte UTC->Brasil antes do naive.
ESTE SCRIPT corrige as linhas ja gravadas: started_at (UTC-naive) -> Brasil-naive via
`started_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Sao_Paulo'` (lida com DST).

NAO afeta `duration_ms` (= last_ts - first_ts; o offset se cancela no delta).

Guard IDEMPOTENTE: so converte linhas com `started_at > recorded_at` (as bugadas).
Apos a conversao ficam < recorded_at -> re-rodar nao pega nada. Metricas NOVAS
(pos-deploy do fix) ja entram corretas -> o guard nao as toca. Backup p/ revert.

ATENCAO (dados PROD = Render): rodar no shell do Render / via DATABASE_URL_PROD
(MCP Render e read-only). Rodar APOS deploy do fix de codigo.

Uso:
    python scripts/migrations/2026_06_19_fix_invocation_metrics_started_at_tz.py           # dry-run
    python scripts/migrations/2026_06_19_fix_invocation_metrics_started_at_tz.py --apply   # efetiva
    python scripts/migrations/2026_06_19_fix_invocation_metrics_started_at_tz.py --revert  # restaura
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import text  # noqa: E402

from app import create_app, db  # noqa: E402

BKP = 'bkp_invocation_started_at_tz'
_CONV = "started_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Sao_Paulo'"


def _table_exists(name: str) -> bool:
    return bool(db.session.execute(
        text("SELECT to_regclass(:n) IS NOT NULL"), {'n': f'public.{name}'}).scalar())


def _diag():
    r = db.session.execute(text("""
        SELECT COUNT(*) AS total,
               COUNT(*) FILTER (WHERE started_at IS NOT NULL) AS com_started,
               COUNT(*) FILTER (WHERE started_at > recorded_at) AS bugadas,
               ROUND(AVG(EXTRACT(EPOCH FROM (started_at - recorded_at)))
                     FILTER (WHERE started_at > recorded_at)/3600.0, 2) AS avg_diff_h
        FROM agent_invocation_metrics
    """)).mappings().first()
    return dict(r) if r else {}


def _print_diag(titulo):
    d = _diag()
    print(f"  [{titulo}] linhas={d.get('total')} com_started={d.get('com_started')} "
          f"bugadas(started>recorded)={d.get('bugadas')} avg_desvio={d.get('avg_diff_h')}h")
    return d


def _apply():
    if _table_exists(BKP):
        print(f"ABORTADO: backup {BKP} ja existe (backfill ja aplicado). Use --revert.")
        return False
    _print_diag('ANTES')
    db.session.execute(text(
        f"CREATE TABLE {BKP} AS SELECT id, started_at FROM agent_invocation_metrics "
        f"WHERE started_at > recorded_at"))
    res = db.session.execute(text(
        f"UPDATE agent_invocation_metrics SET started_at = {_CONV} "
        f"WHERE started_at > recorded_at"))
    db.session.commit()
    print(f"  convertidas: {res.rowcount} linhas")
    _print_diag('DEPOIS')
    print(f"  Backup: {BKP}. OK — backfill aplicado.")
    return True


def _revert():
    if not _table_exists(BKP):
        print(f"ABORTADO: backup {BKP} nao encontrado. Nada a reverter.")
        return False
    db.session.execute(text(
        f"UPDATE agent_invocation_metrics m SET started_at = b.started_at "
        f"FROM {BKP} b WHERE m.id = b.id"))
    db.session.execute(text(f"DROP TABLE {BKP}"))
    db.session.commit()
    print("OK — started_at original restaurado e backup removido.")
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group()
    g.add_argument('--apply', action='store_true', help='efetiva (cria backup)')
    g.add_argument('--revert', action='store_true', help='restaura do backup')
    args = ap.parse_args()
    app = create_app()
    with app.app_context():
        if args.revert:
            _revert()
        elif args.apply:
            _apply()
        else:
            print("=== DRY-RUN (nenhuma escrita) ===")
            _print_diag('ATUAL')
            print("\nPara efetivar: --apply  |  Reverter: --revert")


if __name__ == '__main__':
    main()
