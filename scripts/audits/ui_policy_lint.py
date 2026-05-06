#!/usr/bin/env python3
"""
UI Policy Lint — vocabulario fechado, regras blockantes.

Diferente de ui_audit.py (catalogo estatico), este aplica POLITICA
restritiva — regras que devem ser respeitadas em PRs novos.

Modos:
  --enforce-new : so bloqueia violacoes em ARQUIVOS NOVOS ou linhas TOCADAS
                  no diff (HEAD vs base). Pre-commit/CI default.
  --strict      : bloqueia toda violacao (apenas para auditoria total)
  --report-only : reporta sem exit 1 (debug)

Regras (codigos P1-P9):
  P1 hex_in_template       — hex literal em template (#abc, #aabbcc)
  P2 hex_in_module_css     — hex literal em CSS modulo (fora de tokens/components/base)
  P3 inline_style_color    — style="color/background: ..." em template
  P4 style_block           — <style> block em template
  P5 rare_bs_var           — var(--bs-purple/pink/cyan/orange/teal/indigo)
  P6 untokenized_bs_var_in_module
                           — var(--bs-X-text-emphasis/bg-subtle/border-subtle) em CSS modulo
                             (deve usar --semantic-X-* ou tokens proprios)
  P7 antagonistic_combo    — bg-warning + text-white (ou outras combos baixo contraste)
  P8 important_outside_legacy
                           — !important em CSS modulo (fora de tokens/legacy/utilities)
  P9 rgb_rgba_in_module    — rgb()/rgba() literal em CSS modulo

Vocabulario PERMITIDO (cores e padroes):
  Backgrounds: var(--bg-dark|bg|bg-light|bg-button|amber-XX|semantic-X|semantic-X-subtle)
               OU classes Bootstrap canonical com tematizacao confirmada
               (bg-success|danger|warning|info|primary|secondary|light|dark|
                bg-X-subtle, bg-transparent, bg-white  ← bg-white so se acompanhado
                de override em dark mode)
  Texto:       var(--text|text-muted|amber-28|semantic-X|bs-X-text-emphasis)
  Borda:       var(--border|semantic-X|bs-X-border-subtle)

Saida:
  Console: tabela de violacoes
  exit 0 = OK
  exit 1 = bloqueado (violacao bloqueante encontrada)
  exit 2 = erro de execucao
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TEMPLATES = ROOT / "app" / "templates"
DEFAULT_CSS = ROOT / "app" / "static" / "css"

CSS_CANONICAL_DIRS = {"tokens", "vendor", "components", "base"}
CSS_LEGACY_DIRS = {"legacy"}
CSS_UTILITIES_LEGACY_FILES = {"_legacy.css"}

# ─── Regex ──────────────────────────────────────────────────────────────────

RE_HEX = re.compile(r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3,5})?\b")
RE_RGB_HSL = re.compile(r"\b(?:rgba?|hsla?)\s*\(", re.IGNORECASE)
RE_IMPORTANT = re.compile(r"!\s*important", re.IGNORECASE)
RE_INLINE_STYLE_COLOR = re.compile(
    r'style\s*=\s*"([^"]*?(?:\bcolor\b|\bbackground[\w-]*\b|\bborder-color\b|\bfill\b|\bstroke\b)[^"]*?)"',
    re.IGNORECASE,
)
RE_STYLE_BLOCK = re.compile(r"<style\b[^>]*>(.*?)</style>", re.IGNORECASE | re.DOTALL)
BS_RARE_VARS = (
    "purple", "pink", "cyan", "orange", "teal", "indigo",
    "yellow", "red", "green", "blue", "black", "gray", "gray-dark",
)
RE_RARE_BS_VAR = re.compile(
    r"var\(\s*--bs-(" + "|".join(re.escape(v) for v in BS_RARE_VARS) + r")\b",
    re.IGNORECASE,
)
RE_UNTOKENIZED_BS_VAR = re.compile(
    r"var\(\s*--bs-\w+-(text-emphasis|bg-subtle|border-subtle)\b",
    re.IGNORECASE,
)

# Combinacoes bg+text antagonistas em badges/cards
ANTAGONISTIC_PAIRS = [
    ("bg-warning", "text-white"),
    ("bg-light", "text-white"),
    ("bg-info", "text-dark"),
]
RE_GENERIC_ELEM_WITH_CLASS = re.compile(
    r'<\w+[^>]*class\s*=\s*"([^"]+)"',
    re.IGNORECASE | re.DOTALL,
)

# ─── Coletor ─────────────────────────────────────────────────────────────────

class PolicyReport:
    def __init__(self):
        self.violations: list[dict] = []
        self.totals = Counter()

    def add(self, file_path: Path, line: int, code: str, snippet: str, detail: str = ""):
        self.violations.append({
            "file": str(file_path.relative_to(ROOT)),
            "line": line,
            "code": code,
            "snippet": snippet[:200],
            "detail": detail,
        })
        self.totals[code] += 1


# ─── Linters por tipo de arquivo ────────────────────────────────────────────

def lint_template(file_path: Path, report: PolicyReport):
    try:
        text = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return

    # P3 inline style com cor
    for m in RE_INLINE_STYLE_COLOR.finditer(text):
        line = text[:m.start()].count("\n") + 1
        report.add(file_path, line, "P3_inline_style_color", m.group(0),
                   "use classe canonical em vez de inline style com cor")
        # P1 hex dentro do style inline
        for hm in RE_HEX.finditer(m.group(1)):
            report.add(file_path, line, "P1_hex_in_template", hm.group(0),
                       f"hex {hm.group(0)} em style inline")

    # P5 rare BS vars em template (em qualquer lugar)
    for i, line in enumerate(text.split("\n"), 1):
        for m in RE_RARE_BS_VAR.finditer(line):
            report.add(file_path, i, "P5_rare_bs_var", line.strip()[:160],
                       f"--bs-{m.group(1).lower()} nao tematizado pelo design system")

    # P4 style block
    for m in RE_STYLE_BLOCK.finditer(text):
        block = m.group(1)
        if re.search(r"color\s*:|background", block, re.IGNORECASE):
            line = text[:m.start()].count("\n") + 1
            report.add(file_path, line, "P4_style_block", "<style>...</style>",
                       "<style> em template — mover para css/modules/_X.css")

    # P7 combinacoes antagonistas
    for m in RE_GENERIC_ELEM_WITH_CLASS.finditer(text):
        line = text[:m.start()].count("\n") + 1
        classes = m.group(1)
        for bg, txt in ANTAGONISTIC_PAIRS:
            if bg in classes and txt in classes:
                report.add(file_path, line, "P7_antagonistic_combo", classes[:160],
                           f"{bg} + {txt} = baixo contraste")


def lint_css(file_path: Path, report: PolicyReport):
    rel_parts = file_path.relative_to(DEFAULT_CSS).parts if file_path.is_relative_to(DEFAULT_CSS) else file_path.parts
    parent_dir = rel_parts[0] if rel_parts else ""
    file_name = file_path.name
    is_canonical = parent_dir in CSS_CANONICAL_DIRS
    is_legacy = parent_dir in CSS_LEGACY_DIRS
    is_utilities_legacy = parent_dir == "utilities" and file_name in CSS_UTILITIES_LEGACY_FILES

    try:
        text = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return

    if is_canonical:
        # canonical pode usar hex/rgb/important — sao a fonte de verdade
        return

    for i, line in enumerate(text.split("\n"), 1):
        stripped = line.strip()
        if stripped.startswith("/*") or stripped.startswith("*") or stripped.startswith("//"):
            continue

        # P2 hex em modulo
        for m in RE_HEX.finditer(line):
            report.add(file_path, i, "P2_hex_in_module_css", line.strip()[:160],
                       f"hex {m.group(0)} em modulo — preferir token de _design-tokens.css")

        # P9 rgb/rgba/hsl em modulo (exceto dentro de var())
        if RE_RGB_HSL.search(line) and "var(" not in line:
            report.add(file_path, i, "P9_rgb_rgba_in_module", line.strip()[:160],
                       "preferir hsl/rgb dentro de var() ou em tokens canonical")

        # P8 !important fora de tokens/legacy/utilities
        if RE_IMPORTANT.search(line) and not (is_legacy or is_utilities_legacy):
            report.add(file_path, i, "P8_important_outside_legacy", line.strip()[:160],
                       "!important deve viver em tokens, legacy ou utilities apenas")

        # P5 rare BS vars
        for m in RE_RARE_BS_VAR.finditer(line):
            report.add(file_path, i, "P5_rare_bs_var", line.strip()[:160],
                       f"--bs-{m.group(1).lower()} nao tematizado")

        # P6 untokenized BS vars em modulo
        for m in RE_UNTOKENIZED_BS_VAR.finditer(line):
            suffix = m.group(1)
            report.add(file_path, i, "P6_untokenized_bs_var_in_module",
                       line.strip()[:160],
                       f"--bs-X-{suffix} em modulo — usar tokens proprios "
                       f"(--semantic-X-subtle ou hsl direto)")


# ─── Diff mode (so violations em arquivos novos/tocados) ─────────────────────

def get_changed_files(base_ref: str = "HEAD") -> set[Path]:
    """Retorna set de arquivos modificados/adicionados vs base_ref."""
    try:
        # Files em diff vs base_ref (staged + unstaged + untracked tracked-by-git)
        result = subprocess.run(
            ["git", "diff", "--name-only", base_ref],
            cwd=str(ROOT), capture_output=True, text=True, check=True,
        )
        files = {ROOT / line for line in result.stdout.strip().split("\n") if line}
        # Tambem incluir untracked novos
        untracked = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=str(ROOT), capture_output=True, text=True, check=True,
        )
        files |= {ROOT / line for line in untracked.stdout.strip().split("\n") if line}
        return files
    except (subprocess.CalledProcessError, FileNotFoundError):
        return set()


def get_changed_lines(file_path: Path, base_ref: str = "HEAD") -> set[int]:
    """Retorna set de linhas tocadas vs base_ref. Se arquivo novo, retorna todas."""
    try:
        result = subprocess.run(
            ["git", "diff", "-U0", base_ref, "--", str(file_path)],
            cwd=str(ROOT), capture_output=True, text=True,
        )
        if result.returncode != 0:
            # Arquivo novo
            try:
                lines = file_path.read_text(encoding="utf-8").count("\n") + 1
                return set(range(1, lines + 1))
            except Exception:
                return set()
        changed = set()
        for line in result.stdout.split("\n"):
            m = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", line)
            if m:
                start = int(m.group(1))
                count = int(m.group(2) or "1")
                changed.update(range(start, start + count))
        return changed
    except Exception:
        return set()


# ─── Main ───────────────────────────────────────────────────────────────────

def iter_files(root: Path, suffixes: tuple):
    if not root.exists():
        return
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in suffixes:
            if "vendor" in p.parts:
                continue
            yield p


POLICY_LABELS = {
    "P1_hex_in_template": "Hex literal em template",
    "P2_hex_in_module_css": "Hex literal em CSS modulo",
    "P3_inline_style_color": "Inline style com cor em template",
    "P4_style_block": "<style> block em template",
    "P5_rare_bs_var": "var(--bs-purple/pink/cyan/etc) — Bootstrap nao tematizado",
    "P6_untokenized_bs_var_in_module": "var BS subtle/emphasis em CSS modulo",
    "P7_antagonistic_combo": "Combinacao bg+text de baixo contraste",
    "P8_important_outside_legacy": "!important fora de tokens/legacy/utilities",
    "P9_rgb_rgba_in_module": "rgb/rgba/hsl literal em CSS modulo (sem var)",
}


def main():
    parser = argparse.ArgumentParser(description="UI Policy Lint")
    parser.add_argument("--enforce-new", action="store_true",
                        help="So bloqueia violacoes em arquivos/linhas modificadas vs base")
    parser.add_argument("--base-ref", default="HEAD",
                        help="Ref de comparacao no modo --enforce-new (default HEAD)")
    parser.add_argument("--strict", action="store_true",
                        help="Bloqueia toda violacao no codebase (auditoria total)")
    parser.add_argument("--report-only", action="store_true",
                        help="Reporta mas nao falha (debug)")
    parser.add_argument("--templates-dir", type=Path, default=DEFAULT_TEMPLATES)
    parser.add_argument("--css-dir", type=Path, default=DEFAULT_CSS)
    parser.add_argument("--max-shown", type=int, default=15,
                        help="Max violacoes mostradas por codigo (default 15)")
    args = parser.parse_args()

    if args.enforce_new and args.strict:
        print("[lint] --enforce-new e --strict sao mutuamente exclusivos", file=sys.stderr)
        sys.exit(2)

    report = PolicyReport()

    # Coletar todas as violacoes
    for tpl in iter_files(args.templates_dir, (".html",)):
        lint_template(tpl, report)
    for css in iter_files(args.css_dir, (".css",)):
        lint_css(css, report)

    # Filtrar por modo
    filtered = report.violations
    if args.enforce_new:
        changed = get_changed_files(args.base_ref)
        if not changed:
            print(f"[lint] sem mudancas vs {args.base_ref} — nada a checar")
            sys.exit(0)
        filtered = []
        # Para cada violacao, ver se o arquivo mudou e se a linha esta no diff
        line_cache: dict[Path, set] = {}
        for v in report.violations:
            file_abs = ROOT / v["file"]
            if file_abs not in changed:
                continue
            if file_abs not in line_cache:
                line_cache[file_abs] = get_changed_lines(file_abs, args.base_ref)
            if v["line"] in line_cache[file_abs]:
                filtered.append(v)

    # Reportar
    by_code: dict[str, list] = defaultdict(list)
    for v in filtered:
        by_code[v["code"]].append(v)

    mode = "ENFORCE-NEW" if args.enforce_new else ("STRICT" if args.strict else "REPORT-ONLY")
    print(f"[lint] Modo: {mode}")
    print(f"[lint] Violacoes encontradas: {len(filtered)}")
    print()

    for code in sorted(by_code, key=lambda c: -len(by_code[c])):
        viols = by_code[code]
        label = POLICY_LABELS.get(code, code)
        print(f"━━━ {code} — {label} ({len(viols)}) ━━━")
        for v in viols[:args.max_shown]:
            print(f"  {v['file']}:{v['line']}")
            print(f"    {v['snippet'][:120]}")
            if v["detail"]:
                print(f"    → {v['detail']}")
        if len(viols) > args.max_shown:
            print(f"  ... +{len(viols) - args.max_shown} mais")
        print()

    # Exit code
    if args.report_only or not filtered:
        sys.exit(0)

    if args.enforce_new or args.strict:
        print(f"[lint] FALHOU — {len(filtered)} violacoes da policy. Veja regras em "
              f".claude/references/design/GUIA_COMPONENTES_UI.md")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
