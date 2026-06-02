#!/usr/bin/env python3
"""PAD-A creation gate (PreToolUse Write|Edit). Valida itens 1-8 do checklist
sobre o CONTEUDO PROPOSTO, antes do arquivo existir. So bloqueia em zona gerenciada.
Item 9 (registro no hub) NAO roda aqui (cross-file -> pre-commit). Saida = JSON
permissionDecision (deny|allow). E5: valida FORMA, nunca forca criar."""
from __future__ import annotations
import json, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

def _decision(decision, reason=""):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "permissionDecision": decision, "permissionDecisionReason": reason}}))
    return 0

def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return _decision("allow")
    tool_name = payload.get("tool_name", "")
    tin = payload.get("tool_input", {})
    fpath = tin.get("file_path", "")
    # Anel 1 = creation gate: valida apenas o CONTEUDO COMPLETO de um Write.
    # Edit entrega new_string (fragmento) -> validar como doc inteiro causaria
    # falso-bloqueio (C1). Edits sao policiados por Anel 2 (commit lint) e Anel 3
    # (Stop) sobre o ARQUIVO COMPLETO. Por isso o gate libera Edit (E5/advisory-safe).
    if tool_name == "Edit":
        return _decision("allow")
    content = tin.get("content") or ""
    if not fpath.endswith(".md") and not fpath.endswith(".py"):
        return _decision("allow")
    try:
        from scripts.audits.artefato_lint import config, zones, checks_struct, checks_content
        cfg = config.load()
        rel = fpath
        try: rel = str(Path(fpath).resolve().relative_to(ROOT))
        except Exception: pass
        if fpath.endswith(".md"):
            if not zones.is_managed_doc(rel, cfg) or zones.is_scratch(content):
                return _decision("allow")
            # FIX: tmp file MUST live under ROOT so checks_*.check_file (which does
            # path.resolve().relative_to(root) as its first line) does not raise.
            fd, tmpname = tempfile.mkstemp(suffix=".md", dir=str(ROOT))
            tf = Path(tmpname)
            try:
                import os as _os; _os.close(fd)
                tf.write_text(content, encoding="utf-8")
                fs = checks_struct.check_file(tf, ROOT, cfg) + checks_content.check_file(tf, ROOT, cfg)
            finally:
                tf.unlink(missing_ok=True)
            blockers = [f for f in fs if f.severity == "block"]
            if blockers:
                msg = "PAD-A gate bloqueou. Corrija:\n" + "\n".join(f"  [{b.code}] {b.message}" for b in blockers)
                return _decision("deny", msg)
        return _decision("allow")
    except Exception as e:
        # nunca travar o agente por erro do gate -> advisory-safe
        return _decision("allow", f"(gate ignorado: {e})")

if __name__ == "__main__":
    raise SystemExit(main())
