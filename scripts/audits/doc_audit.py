#!/usr/bin/env python3
"""doc_audit — lint deterministico de DOCUMENTOS do PAD-A.

Modos: --report-only (auditoria), --enforce-new (so novos/diff), --enforce-touched
(working tree), --strict (tudo). Exit 0 OK / 1 bloqueado / 2 erro.
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.audits.artefato_lint import config, zones, findings, gitdiff
from scripts.audits.artefato_lint import checks_struct, checks_content, checks_dup

def iter_docs(root: Path, cfg, scope: set[str] | None, path_filter: str | None):
    for p in root.rglob("*.md"):
        rel = str(p.relative_to(root))
        if not zones.is_managed_doc(rel, cfg):
            continue
        if path_filter and not rel.startswith(path_filter):
            continue
        if scope is not None and rel not in scope:
            continue
        if zones.is_scratch(p.read_text(encoding="utf-8")):
            continue
        yield p

def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--report-only", action="store_true")
    g.add_argument("--enforce-new", action="store_true")
    g.add_argument("--enforce-touched", action="store_true")
    g.add_argument("--enforce-added", action="store_true")
    g.add_argument("--strict", action="store_true")
    ap.add_argument("--base-ref", default="HEAD")
    ap.add_argument("--path", default=None, help="prefixo de path p/ filtrar (auditoria parcial)")
    args = ap.parse_args()
    cfg = config.load()
    scope = None
    if args.enforce_new:
        scope = gitdiff.changed_files(ROOT, args.base_ref)
    elif args.enforce_touched:
        scope = gitdiff.touched_files(ROOT)
    elif args.enforce_added:
        scope = gitdiff.added_files(ROOT)
    all_findings = []
    blocks = {}
    try:
        for p in iter_docs(ROOT, cfg, scope, args.path):
            all_findings += checks_struct.check_file(p, ROOT, cfg)
            all_findings += checks_content.check_file(p, ROOT, cfg)
            blocks[str(p.relative_to(ROOT))] = checks_content._body(p.read_text(encoding="utf-8"))
        all_findings += checks_dup.compare_blocks(blocks, cfg)
    except Exception as e:  # exit 2 = erro de execucao
        print(f"erro: {e}", file=sys.stderr)
        return 2
    print(findings.render(all_findings))
    if args.report_only:
        return 0
    return findings.exit_code(all_findings)

if __name__ == "__main__":
    raise SystemExit(main())
