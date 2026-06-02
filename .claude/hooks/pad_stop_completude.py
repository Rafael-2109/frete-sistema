#!/usr/bin/env python3
"""PAD-A Stop hook (advisory). Roda doc_audit/script_audit --enforce-touched e
LISTA pendencias. NUNCA bloqueia (exit 0 sempre). Memoria: nao trava fim de sessao."""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]

def main() -> int:
    try: json.load(sys.stdin)
    except Exception: pass
    for cli in ("doc_audit.py", "script_audit.py"):
        r = subprocess.run([sys.executable, f"scripts/audits/{cli}", "--enforce-touched"],
                           cwd=ROOT, capture_output=True, text=True)
        if r.returncode == 1:
            print(f"\n[PAD-A] pendencias em arquivos tocados ({cli}):\n{r.stdout}", file=sys.stderr)
    return 0  # advisory

if __name__ == "__main__":
    raise SystemExit(main())
