#!/usr/bin/env python3
"""route_template_audit (B2) — lint deterministico de wiring rota->template.

Bloqueia commit que referencia, via `render_template('x.html')` LITERAL, um template
que NAO existe em nenhuma pasta de template do projeto (typo / arquivo ausente ->
500 em runtime).

Decisoes (ver design 2026-06-14-guardrails-integridade-compatibilidade):
- So argumento LITERAL ('..' / "..") e auditado; `render_template(var)` / f-string
  sao nao-decidiveis estaticamente -> ignorados. Chamada em COMENTARIO -> ignorada.
- Resolucao TOLERANTE a template_folder: o template existe se houver, em qualquer
  pasta de template sob app/ (app/templates/ + os template_folder proprios de
  blueprints, ex: app/agente/templates/), um arquivo cujo caminho case com o nome
  (exato OU por sufixo "/<nome>"). Falso-positivo e' inaceitavel num gate
  (levaria a --no-verify); raro falso-negativo e' aceitavel.
- BASELINE (scripts/audits/route_template_baseline.json): rotas legadas ja
  quebradas sao congeladas — o gate so bloqueia achados NOVOS (nao trava legado).
  `--update-baseline` regrava o baseline com o estado atual.

Modos: --staged (default, pre-commit: .py em status A/C/M) | --all (app/**/*.py) |
--files f1 f2 | --report-only (mostra TUDO, exit 0) | --update-baseline.
Exit 0 OK / 1 bloqueado / 2 erro.
"""
from __future__ import annotations
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.audits.artefato_lint import findings  # noqa: E402

APP_DIR = ROOT / "app"
BASELINE_PATH = ROOT / "scripts" / "audits" / "route_template_baseline.json"

# render_template ( <ws> <quote> <name> <same quote>  -> captura literal; se o 1o
# argumento nao for string (variavel), o padrao nao casa -> ignorado de proposito.
_CALL_RE = re.compile(r"""render_template\s*\(\s*(['"])(?P<name>[^'"]+)\1""")
# extrai o nome do template da message (formato fixo "...: '<name>'") p/ a chave.
_KEY_RE = re.compile(r"'([^']+)'\s*$")


def extract_calls(source: str) -> list[tuple[str, int]]:
    """Retorna [(template_name, lineno)] de cada render_template('literal').

    Ignora chamada cujo `render_template` esteja apos um `#` na mesma linha
    (comentario / string de exemplo).
    """
    out: list[tuple[str, int]] = []
    for m in _CALL_RE.finditer(source):
        start = m.start()
        line_start = source.rfind("\n", 0, start) + 1
        if "#" in source[line_start:start]:  # comentario antes da chamada
            continue
        lineno = source.count("\n", 0, start) + 1
        out.append((m.group("name"), lineno))
    return out


def template_exists(name: str, index) -> bool:
    """True se `name` casa com algum caminho de template conhecido (exato ou sufixo)."""
    name = name.strip().lstrip("/")
    if not name:
        return False
    if name in index:
        return True
    suffix = "/" + name
    return any(p.endswith(suffix) for p in index)


def build_index(app_dir: Path = APP_DIR) -> set[str]:
    """Indexa todos os .html sob app/ (caminho relativo a app/, '/' normalizado).

    Cobre app/templates/** e os template_folder proprios de blueprints
    (app/<mod>/templates/**), sem precisar resolver cada template_folder a mao.
    """
    idx: set[str] = set()
    for p in app_dir.rglob("*.html"):
        idx.add(str(p.relative_to(app_dir)).replace("\\", "/"))
    return idx


def finding_key(f) -> str:
    """Chave estavel do achado p/ baseline: '<path>::<template_name>' (sem a linha,
    que muda ao editar o arquivo)."""
    m = _KEY_RE.search(f.message)
    return f"{f.path}::{m.group(1)}" if m else f"{f.path}::{f.line}"


def load_baseline(path=BASELINE_PATH) -> set:
    """Carrega o baseline (lista JSON de chaves). Ausente/invalido -> set vazio."""
    try:
        return set(json.loads(Path(path).read_text(encoding="utf-8")))
    except (FileNotFoundError, ValueError):
        return set()


def audit_source(source: str, index, rel_path: str = "<mem>", baseline=None) -> list:
    """Finding (block) por template inexistente, exceto os presentes no baseline."""
    baseline = baseline or set()
    out = []
    for name, lineno in extract_calls(source):
        if template_exists(name, index):
            continue
        f = findings.Finding(
            code="B2TPL",
            path=rel_path,
            line=lineno,
            message=f"render_template aponta p/ template inexistente: '{name}'",
            severity="block",
        )
        if finding_key(f) in baseline:
            continue
        out.append(f)
    return out


def audit_file(py_path, index, root: Path = ROOT, baseline=None) -> list:
    """Audita um arquivo .py no disco contra o index de templates."""
    py_path = Path(py_path)
    try:
        rel = str(py_path.resolve().relative_to(root))
    except ValueError:
        rel = str(py_path)
    source = py_path.read_text(encoding="utf-8", errors="replace")
    return audit_source(source, index, rel, baseline)


def _audit_paths(names) -> list[str]:
    """Filtra para .py sob app/ — rotas Flask vivem la. tests/, scripts/, migrations/
    contem render_template em strings/docstrings que NAO sao rotas reais (auditar
    auto-bloquearia o proprio gate)."""
    return [n for n in names if n.strip().endswith(".py") and n.strip().startswith("app/")]


def _staged_py(root: Path) -> list[str]:
    """.py de app/ staged para commit (Added/Copied/Modified)."""
    r = subprocess.run(
        ["git", "diff", "--cached", "--diff-filter=ACM", "--name-only"],
        cwd=root, capture_output=True, text=True,
    )
    return _audit_paths(r.stdout.splitlines())


def _collect_files(args) -> list:
    if args.files:
        return [ROOT / f for f in args.files]
    if args.all or args.update_baseline:
        return list(APP_DIR.rglob("*.py"))
    return [ROOT / f for f in _staged_py(ROOT)]  # --staged (default)


def main() -> int:
    ap = argparse.ArgumentParser(description="Audita wiring render_template -> template.")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--staged", action="store_true", help="audita .py staged (pre-commit; default)")
    g.add_argument("--all", action="store_true", help="audita app/**/*.py")
    g.add_argument("--files", nargs="+", help="lista explicita de arquivos .py")
    ap.add_argument("--report-only", action="store_true", help="mostra TUDO (ignora baseline), exit 0")
    ap.add_argument("--update-baseline", action="store_true", help="regrava o baseline com o estado atual")
    args = ap.parse_args()

    try:
        index = build_index()
        # report-only e update-baseline veem TUDO (baseline nao aplicado).
        baseline = set() if (args.report_only or args.update_baseline) else load_baseline()
        all_findings = []
        for f in _collect_files(args):
            if Path(f).is_file():
                all_findings += audit_file(f, index, baseline=baseline)
    except Exception as e:  # exit 2 = erro de execucao
        print(f"erro: {e}", file=sys.stderr)
        return 2

    if args.update_baseline:
        keys = sorted({finding_key(f) for f in all_findings})
        BASELINE_PATH.write_text(json.dumps(keys, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"baseline atualizado: {len(keys)} entradas -> {BASELINE_PATH.relative_to(ROOT)}")
        return 0

    print(findings.render(all_findings))
    if args.report_only:
        return 0
    return findings.exit_code(all_findings)


if __name__ == "__main__":
    raise SystemExit(main())
