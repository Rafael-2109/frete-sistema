#!/usr/bin/env python3
"""script_audit — lint deterministico de SCRIPTS do PAD-A."""
from __future__ import annotations
import argparse, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.audits.artefato_lint import config, zones, findings, gitdiff, checks_script

def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--report-only", action="store_true")
    g.add_argument("--enforce-new", action="store_true")
    g.add_argument("--enforce-touched", action="store_true")
    g.add_argument("--strict", action="store_true")
    ap.add_argument("--base-ref", default="HEAD")
    args = ap.parse_args()
    cfg = config.load()
    scope = gitdiff.changed_files(ROOT, args.base_ref) if args.enforce_new else (
            gitdiff.touched_files(ROOT) if args.enforce_touched else None)
    idx = checks_script.collect_index_basenames(ROOT, cfg)
    fs = []
    try:
        for p in ROOT.rglob("*.py"):
            rel = str(p.relative_to(ROOT))
            if not zones.is_operational_script(rel, cfg):
                continue
            if scope is not None and rel not in scope:
                continue
            fs += checks_script.check_file(p, ROOT, cfg, idx)
    except Exception as e:
        print(f"erro: {e}", file=sys.stderr); return 2
    print(findings.render(fs))
    return 0 if args.report_only else findings.exit_code(fs)

if __name__ == "__main__":
    raise SystemExit(main())
