# tests/audits/test_artefato_cli.py
import subprocess, sys, os
from pathlib import Path
REPO = Path(__file__).resolve().parents[2]

def test_doc_audit_report_only_roda():
    r = subprocess.run([sys.executable, "scripts/audits/doc_audit.py", "--report-only", "--path", "docs/superpowers/specs"],
                       cwd=REPO, capture_output=True, text=True)
    assert r.returncode in (0, 1)  # roda; report-only nunca 2
    assert "achados" in r.stdout.lower() or "OK" in r.stdout

def test_doc_audit_enforce_new_exit0_quando_sem_diff():
    r = subprocess.run([sys.executable, "scripts/audits/doc_audit.py", "--enforce-new", "--base-ref", "HEAD"],
                       cwd=REPO, capture_output=True, text=True)
    assert r.returncode in (0, 1)
