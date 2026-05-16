"""
Ingestor: JSONL dev (Claude Code CLI) -> tabela agent_invocation_metrics.

Le todos os arquivos em /tmp/agent_invocation_metrics_dev/*.jsonl
(produzidos por .claude/hooks/agent_metrics_dev_hook.py) e insere
linhas em `agent_invocation_metrics` com `source='dev'`.

Idempotente:
- UNIQUE(agent_id) ja existe na tabela. Insert duplicado e ignorado
  silenciosamente via SAVEPOINT pattern (AgentInvocationMetric.insert_metric)
- Pode rodar N vezes sem efeito colateral
- agent_id e SEMPRE gerado deterministicamente do payload do hook
  PostToolUse — mesmo se rodar varias vezes, mesma linha do JSONL gera
  mesmo agent_id (vide _build_agent_id())

Schema do JSONL (.claude/hooks/agent_metrics_dev_hook.py):
{
  "schema_version": "v1",
  "timestamp": "ISO-8601 UTC",
  "session_id": "uuid Claude Code",
  "agent_type": "<subagent_type>",
  "tool_name": "Agent",
  "duration_ms": int|null,
  "cost_usd": float|null,
  "input_tokens": int,
  "output_tokens": int,
  "source": "dev"
}

NOTA: hook dev nao tem acesso a transcript do subagent (Claude Code CLI
nao expoe via PostToolUse). Entao cache_read/cache_create ficam 0 e
duration/cost podem ser None — populamos com os valores disponiveis e o
restante fica como zeros/NULL na tabela.

Usage:
    python scripts/migrations/2026_05_16_agent_invocation_metrics_dev_ingestor.py
    python scripts/migrations/2026_05_16_agent_invocation_metrics_dev_ingestor.py \
        --dir /tmp/agent_invocation_metrics_dev \
        --since 2026-05-01

Saida:
    [info] arquivos processados: N
    [info] linhas lidas: N | inseridas: N | duplicadas: N | erros: N
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from app import create_app, db  # noqa: E402
from app.agente.models import AgentInvocationMetric  # noqa: E402


DEFAULT_DIR = Path("/tmp/agent_invocation_metrics_dev")


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    """Parse ISO-8601 -> datetime naive UTC. None se invalido."""
    if not value:
        return None
    try:
        normalized = value.replace('Z', '+00:00') if value.endswith('Z') else value
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is not None:
            return parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed
    except (ValueError, TypeError):
        return None


def _build_agent_id(record: dict) -> str:
    """Gera agent_id deterministico do payload do hook dev.

    Hook dev nao recebe agent_id real (Claude Code CLI nao expoe via
    PostToolUse). Geramos hash estavel de (timestamp + session_id + agent_type
    + tokens). Mesma linha JSONL -> mesmo agent_id -> dedup automatico via
    UNIQUE constraint.

    Prefixo 'dev_' deixa explicito que e sintetico (vs UUID real em PROD).
    """
    key = '|'.join([
        str(record.get('timestamp') or ''),
        str(record.get('session_id') or ''),
        str(record.get('agent_type') or ''),
        str(record.get('input_tokens') or 0),
        str(record.get('output_tokens') or 0),
    ])
    digest = hashlib.sha256(key.encode('utf-8')).hexdigest()[:24]
    return f"dev_{digest}"


def _ingest_record(record: dict, stats: dict) -> None:
    """Insere uma linha do JSONL. Atualiza stats in-place."""
    schema = record.get('schema_version')
    if schema != 'v1':
        stats['errors'] += 1
        return

    agent_type = record.get('agent_type') or 'unknown'
    timestamp = _parse_iso(record.get('timestamp'))
    if timestamp is None:
        timestamp = datetime.now(timezone.utc).replace(tzinfo=None)

    agent_id = _build_agent_id(record)

    cost_raw = record.get('cost_usd')
    cost_usd = None
    if cost_raw is not None:
        try:
            cost_usd = float(cost_raw)
        except (TypeError, ValueError):
            cost_usd = None

    duration_raw = record.get('duration_ms')
    duration_ms = None
    if duration_raw is not None:
        try:
            duration_ms = int(duration_raw)
        except (TypeError, ValueError):
            duration_ms = None

    metric = AgentInvocationMetric.insert_metric(
        agent_id=agent_id,
        agent_type=agent_type,
        session_id=record.get('session_id') or None,
        user_id=None,  # dev nao tem user_id (Rafael em Claude Code local)
        started_at=timestamp,
        duration_ms=duration_ms,
        num_turns=None,  # nao disponivel via PostToolUse Agent
        stop_reason='end_turn',  # PostToolUse so dispara em sucesso
        cost_usd=cost_usd,
        input_tokens=int(record.get('input_tokens') or 0),
        output_tokens=int(record.get('output_tokens') or 0),
        cache_read_tokens=0,
        cache_creation_tokens=0,
        source=AgentInvocationMetric.SOURCE_DEV,
    )
    if metric is None:
        stats['duplicates'] += 1
    else:
        stats['inserted'] += 1


def _process_file(path: Path, since: Optional[datetime], stats: dict) -> None:
    """Le um JSONL e ingere linhas. `since` filtra por timestamp."""
    print(f"[file] {path}")
    with path.open('r', encoding='utf-8') as f:
        for line_num, raw in enumerate(f, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                record = json.loads(raw)
            except json.JSONDecodeError as e:
                print(f"  [skip] linha {line_num}: JSON invalido: {e}")
                stats['errors'] += 1
                continue

            stats['read'] += 1

            if since is not None:
                ts = _parse_iso(record.get('timestamp'))
                if ts is not None and ts < since:
                    stats['filtered'] += 1
                    continue

            try:
                _ingest_record(record, stats)
            except Exception as e:
                print(f"  [erro] linha {line_num}: {type(e).__name__}: {e}")
                stats['errors'] += 1
                try:
                    db.session.rollback()
                except Exception:
                    pass


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Ingestor JSONL dev -> agent_invocation_metrics'
    )
    parser.add_argument(
        '--dir',
        type=Path,
        default=DEFAULT_DIR,
        help=f'Diretorio com *.jsonl (default {DEFAULT_DIR})',
    )
    parser.add_argument(
        '--since',
        type=str,
        default=None,
        help='Filtrar timestamp >= YYYY-MM-DD (UTC) — opcional',
    )
    args = parser.parse_args()

    since: Optional[datetime] = None
    if args.since:
        try:
            since = datetime.strptime(args.since, '%Y-%m-%d').replace(tzinfo=None)
        except ValueError:
            print(f"[erro] --since invalido: {args.since!r} (use YYYY-MM-DD)")
            return 1

    if not args.dir.exists():
        print(f"[info] diretorio {args.dir} nao existe — nada a fazer")
        return 0

    jsonl_files = sorted(args.dir.glob('*.jsonl'))
    if not jsonl_files:
        print(f"[info] nenhum *.jsonl em {args.dir} — nada a fazer")
        return 0

    print(f"[info] {len(jsonl_files)} arquivo(s) a processar em {args.dir}")
    if since:
        print(f"[info] filtro: timestamp >= {since.isoformat()}")

    stats = {
        'read': 0,
        'inserted': 0,
        'duplicates': 0,
        'filtered': 0,
        'errors': 0,
    }

    app = create_app()
    with app.app_context():
        for path in jsonl_files:
            _process_file(path, since, stats)
        # Commit final — insert_metric usa SAVEPOINT, precisa flush
        try:
            db.session.commit()
        except Exception as e:
            print(f"[erro] commit final falhou: {e}")
            try:
                db.session.rollback()
            except Exception:
                pass
            return 1

    print(
        f"[done] arquivos={len(jsonl_files)} | "
        f"linhas={stats['read']} | "
        f"inseridas={stats['inserted']} | "
        f"duplicadas={stats['duplicates']} | "
        f"filtradas={stats['filtered']} | "
        f"erros={stats['errors']}"
    )
    return 0 if stats['errors'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
