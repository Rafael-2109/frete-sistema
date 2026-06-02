from __future__ import annotations
import subprocess
from pathlib import Path

def changed_files(root: Path, base_ref: str | None) -> set[str]:
    """Arquivos novos/modificados vs base_ref + untracked. Espelha ui_policy_lint --enforce-new."""
    files: set[str] = set()
    if base_ref:
        d = subprocess.run(["git", "diff", "--name-only", base_ref], cwd=root, capture_output=True, text=True)
        files |= {l for l in d.stdout.splitlines() if l.strip()}
    u = subprocess.run(["git", "ls-files", "--others", "--exclude-standard"], cwd=root, capture_output=True, text=True)
    files |= {l for l in u.stdout.splitlines() if l.strip()}
    return files

def touched_files(root: Path) -> set[str]:
    """--enforce-touched: working tree (staged+unstaged+untracked)."""
    out: set[str] = set()
    for args in (["git", "diff", "--name-only"], ["git", "diff", "--name-only", "--cached"],
                 ["git", "ls-files", "--others", "--exclude-standard"]):
        r = subprocess.run(args, cwd=root, capture_output=True, text=True)
        out |= {l for l in r.stdout.splitlines() if l.strip()}
    return out

def added_files(root: Path) -> set[str]:
    """Arquivos com status Added (novos) staged para commit. Para o pre-commit
    (Anel 2 added-only): so NOVO artefato nao-conforme bloqueia; edicao de legado
    (Modified) NAO entra. Coerente com a migracao gradual (Ondas 1-4)."""
    r = subprocess.run(["git", "diff", "--cached", "--diff-filter=A", "--name-only"],
                       cwd=root, capture_output=True, text=True)
    return {l for l in r.stdout.splitlines() if l.strip()}
