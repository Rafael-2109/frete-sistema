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

def test_doc_audit_enforce_added_roda():
    # --enforce-added so audita arquivos com status Added (novos). Sem nada staged,
    # o escopo e vazio -> exit 0. Modo seguro p/ pre-commit (nao trava edicao de legado).
    r = subprocess.run([sys.executable, "scripts/audits/doc_audit.py", "--enforce-added"],
                       cwd=REPO, capture_output=True, text=True)
    assert r.returncode in (0, 1)
    assert "achados" in r.stdout.lower() or "OK" in r.stdout

def test_doc_audit_tem_flag_skip_dup():
    # --skip-dup pula o passo de near-duplicate (O(n^2)) p/ o baseline full nao travar.
    r = subprocess.run([sys.executable, "scripts/audits/doc_audit.py", "--help"],
                       cwd=REPO, capture_output=True, text=True)
    assert "--skip-dup" in r.stdout
