#!/usr/bin/env python3
"""PreToolUse advisory: ao editar codigo em app/<mod>/, injeta additionalContext
apontando a SOT do modulo (app/<mod>/CLAUDE.md), se existir. Nunca bloqueia."""
from __future__ import annotations
import json, sys, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]

def main() -> int:
    try: payload = json.load(sys.stdin)
    except Exception: return 0
    fp = payload.get("tool_input", {}).get("file_path", "")
    m = re.search(r"app/([^/]+)/", fp)
    ctx = ""
    if m and fp.endswith(".py"):
        sot = ROOT / "app" / m.group(1) / "CLAUDE.md"
        if sot.exists():
            ctx = f"SOT do modulo {m.group(1)}: app/{m.group(1)}/CLAUDE.md — consulte antes de alterar."
    if ctx:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": ctx}}))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
