import subprocess, sys, json
from pathlib import Path
REPO = Path(__file__).resolve().parents[2]

def _run(payload):
    return subprocess.run([sys.executable, ".claude/hooks/pad_creation_gate.py"],
                          cwd=REPO, input=json.dumps(payload), capture_output=True, text=True)

def test_gate_bloqueia_doc_sem_header():
    payload = {"tool_name": "Write", "tool_input": {"file_path": str(REPO/"docs/zz.md"), "content": "# sem header\n"}}
    r = _run(payload)
    out = json.loads(r.stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"

def test_gate_permite_fora_de_zona():
    payload = {"tool_name": "Write", "tool_input": {"file_path": "/tmp/x.md", "content": "qualquer"}}
    r = _run(payload)
    out = json.loads(r.stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] in ("allow", "ask", "")

def test_gate_permite_edit_fragmento():
    # Edit entrega new_string (fragmento sem header) -> o creation gate NAO pode
    # bloquear; edits sao validados no commit (Anel 2) e no Stop (Anel 3) sobre o
    # ARQUIVO COMPLETO. Bloquear o fragmento seria falso-positivo (C1).
    payload = {"tool_name": "Edit", "tool_input": {"file_path": str(REPO/"docs/zz.md"),
               "old_string": "foo", "new_string": "bar baz sem header"}}
    r = _run(payload)
    out = json.loads(r.stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] != "deny"
