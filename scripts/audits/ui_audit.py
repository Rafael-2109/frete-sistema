#!/usr/bin/env python3
"""
UI Audit — varre templates e CSS, detecta violações ao Design System Nacom Goya.

Sistema canonico (referencia em base.html / main.css):
  app/static/css/main.css            ← orquestrador (@layer + @import)
  app/static/css/tokens/             ← design tokens (HSL, semantic colors, --bs-*)
  app/static/css/components/         ← badges, tables, cards (theme-aware)
  app/static/css/modules/            ← por-modulo (_hora.css, _carteira.css, ...)
  app/static/css/utilities/          ← _legacy.css, _utilities.css
  app/static/css/base/               ← _navbar.css, _bootstrap-overrides.css

Violacoes detectadas:
  V1  inline_style_color       → style="color/background-color/..." em template
  V2  hex_in_template          → #abc / #aabbcc no atributo style/class de template
  V3  hex_in_css_module        → hex literal em CSS fora de tokens/vendor (anti-pattern)
  V4  rgb_rgba_in_css          → rgb()/rgba() em CSS fora de tokens (anti-pattern)
  V5  important_in_css         → !important em CSS fora de tokens/legacy/utilities
  V6  badge_bg_text_combo      → <badge bg-* text-white|text-dark> (derruba --_badge-color)
  V7  text_white_dark_combo    → text-white com bg-warning|bg-light (baixo contraste)
  V8  inline_color_class       → class="text-X" + bg-Y antagonico em mesmo elemento
  V9  module_css_hardcoded_bg  → background:#... em modulo (deveria ser var(--bg-*))
  V10 missing_data_bs_theme    → CSS sem suporte a [data-bs-theme="light"] em arquivo que usa var(--bg-*)

Saida:
  relatorios/ui_audit_YYYY-MM-DD.json   (machine-readable)
  relatorios/ui_audit_YYYY-MM-DD.md     (human-readable, top hotspots)

Uso:
  python scripts/audits/ui_audit.py
  python scripts/audits/ui_audit.py --json-only
  python scripts/audits/ui_audit.py --templates-dir app/templates/hora
"""

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

# ============================================================================
# CONFIGURACAO
# ============================================================================

ROOT = Path(__file__).resolve().parents[2]  # frete-sistema/
DEFAULT_TEMPLATES = ROOT / "app" / "templates"
DEFAULT_CSS = ROOT / "app" / "static" / "css"
DEFAULT_REPORTS = ROOT / "relatorios"

# Arquivos CSS canonicos: hex/!important AQUI eh OK (sao a fonte de verdade)
CSS_CANONICAL_DIRS = {"tokens", "vendor"}
# Arquivos CSS legados: hex/!important AQUI eh tolerado mas reportado como debt
CSS_LEGACY_DIRS = {"legacy"}
# Em utilities/_legacy.css o !important eh esperado (compat Bootstrap 4 -> 5)
CSS_UTILITIES_LEGACY_FILES = {"_legacy.css"}

# ============================================================================
# REGEX
# ============================================================================

# Hex: #RGB, #RRGGBB, #RRGGBBAA. Captura cores literais.
RE_HEX = re.compile(r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3,5})?\b")
# rgb / rgba / hsl / hsla
RE_RGB_HSL = re.compile(r"\b(?:rgba?|hsla?)\s*\(", re.IGNORECASE)
# !important
RE_IMPORTANT = re.compile(r"!\s*important", re.IGNORECASE)
# inline style attribute em template HTML
RE_INLINE_STYLE = re.compile(
    r'style\s*=\s*"([^"]*?(?:color|background|border-color|fill|stroke)[^"]*?)"',
    re.IGNORECASE,
)
# Captura class="..." inteiro (multi-line)
RE_CLASS_ATTR = re.compile(r'class\s*=\s*"([^"]+)"', re.DOTALL)
# Detecta presenca de tag badge
RE_BADGE_TAG = re.compile(
    r'<(span|div|a|button|li|i)[^>]*class\s*=\s*"([^"]*\bbadge\b[^"]*)"',
    re.IGNORECASE | re.DOTALL,
)
# Detecta presenca de elemento com class containing bg-* + text-*
RE_GENERIC_ELEM_WITH_CLASS = re.compile(
    r'<\w+[^>]*class\s*=\s*"([^"]*)"', re.IGNORECASE | re.DOTALL
)

# Pares antagonicos comuns (texto vs fundo) — anti-pattern de baixo contraste
ANTAGONISTIC_PAIRS = [
    ("bg-warning", "text-white"),     # amarelo claro + texto branco = ilegivel light
    ("bg-light", "text-white"),       # fundo claro + texto branco = invisivel
    ("bg-info", "text-dark"),         # info eh cinza, dark fica baixo contraste
]
# Em badges, qualquer text-white|text-dark com bg-* derruba --_badge-color do design system
BADGE_OVERRIDE_TEXT = re.compile(r"\btext-(white|dark|light|black|muted)\b")
BADGE_BG_CLASS = re.compile(r"\bbg-(primary|secondary|success|danger|warning|info|light|dark)\b")


# ============================================================================
# COLETORES
# ============================================================================

class AuditReport:
    def __init__(self):
        self.violations = []      # lista de dicts: {file, line, code, snippet, detail}
        self.totals = Counter()
        self.by_file = defaultdict(Counter)
        self.by_module = defaultdict(Counter)
        self.unique_hex_in_css = Counter()
        self.unique_hex_in_templates = Counter()
        self.files_scanned = {"templates": 0, "css": 0}

    def add(self, file_path: Path, line: int, code: str, snippet: str, detail: str = ""):
        rel = str(file_path.relative_to(ROOT))
        self.violations.append({
            "file": rel,
            "line": line,
            "code": code,
            "snippet": snippet[:200],
            "detail": detail,
        })
        self.totals[code] += 1
        self.by_file[rel][code] += 1
        # modulo = primeira pasta apos templates/ ou modules/
        module = self._infer_module(rel)
        if module:
            self.by_module[module][code] += 1

    @staticmethod
    def _infer_module(rel: str) -> str:
        parts = rel.split("/")
        if "templates" in parts:
            i = parts.index("templates")
            if i + 1 < len(parts):
                return f"templates/{parts[i + 1]}"
        if "modules" in parts:
            i = parts.index("modules")
            if i + 1 < len(parts):
                return f"css/modules/{parts[i + 1]}"
        if "components" in parts:
            return "css/components"
        if "tokens" in parts:
            return "css/tokens"
        if "utilities" in parts:
            return "css/utilities"
        if "base" in parts:
            return "css/base"
        return parts[-2] if len(parts) >= 2 else "?"


# ============================================================================
# AUDITORES
# ============================================================================

def audit_template(file_path: Path, report: AuditReport) -> None:
    try:
        text = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return

    # V1 + V2: inline style com cor + hex em template
    for m in RE_INLINE_STYLE.finditer(text):
        line = text[:m.start()].count("\n") + 1
        style_content = m.group(1)
        report.add(file_path, line, "V1_inline_style_color", m.group(0), style_content[:120])
        # V2: hex dentro do style inline
        for hm in RE_HEX.finditer(style_content):
            report.add(file_path, line, "V2_hex_in_template", hm.group(0), f'em style: {style_content[:80]}')
            report.unique_hex_in_templates[hm.group(0).lower()] += 1

    # V6 + V7 + V8: badges e combinacoes antagonisticas
    for m in RE_BADGE_TAG.finditer(text):
        line = text[:m.start()].count("\n") + 1
        classes = m.group(2)
        bg_match = BADGE_BG_CLASS.search(classes)
        text_match = BADGE_OVERRIDE_TEXT.search(classes)
        if bg_match and text_match:
            report.add(
                file_path, line, "V6_badge_bg_text_combo",
                m.group(0)[:160],
                f'badge tem bg-{bg_match.group(1)} + text-{text_match.group(1)} (derruba --_badge-color)',
            )

    # V7: combinacoes antagonisticas em qualquer elemento (nao so badge)
    for m in RE_GENERIC_ELEM_WITH_CLASS.finditer(text):
        line = text[:m.start()].count("\n") + 1
        classes = m.group(1)
        for bg, txt in ANTAGONISTIC_PAIRS:
            if bg in classes and txt in classes:
                # Skip if already reported as badge V6
                if "badge" in classes:
                    continue
                report.add(
                    file_path, line, "V7_text_bg_combo",
                    classes[:160],
                    f'combinacao baixo contraste: {bg} + {txt}',
                )


def audit_css(file_path: Path, report: AuditReport) -> None:
    rel_parts = file_path.relative_to(DEFAULT_CSS).parts if file_path.is_relative_to(DEFAULT_CSS) else file_path.parts
    parent_dir = rel_parts[0] if rel_parts else ""
    file_name = file_path.name
    is_canonical = parent_dir in CSS_CANONICAL_DIRS
    is_legacy_dir = parent_dir in CSS_LEGACY_DIRS
    is_utilities_legacy = parent_dir == "utilities" and file_name in CSS_UTILITIES_LEGACY_FILES

    try:
        text = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return

    lines = text.split("\n")

    for i, line in enumerate(lines, 1):
        # Skip linhas de comentario obvias
        stripped = line.strip()
        if stripped.startswith("/*") or stripped.startswith("*") or stripped.startswith("//"):
            continue

        # V3: hex literal em CSS fora de tokens/vendor
        for m in RE_HEX.finditer(line):
            hex_value = m.group(0).lower()
            report.unique_hex_in_css[hex_value] += 1
            if not is_canonical:
                severity = "low" if is_legacy_dir else "high"
                report.add(
                    file_path, i, "V3_hex_in_css_module",
                    line.strip()[:160],
                    f'cor literal {hex_value} (severidade: {severity}) — preferir token CSS',
                )

        # V4: rgb/rgba/hsl/hsla em CSS fora de tokens
        if RE_RGB_HSL.search(line) and not is_canonical:
            # tolerar uso em vars (color-mix, etc)
            if "var(" not in line:
                report.add(
                    file_path, i, "V4_rgb_in_css",
                    line.strip()[:160],
                    "preferir hsl(...) em token + var(--token)",
                )

        # V5: !important em CSS fora de tokens/_legacy
        if RE_IMPORTANT.search(line) and not (is_canonical or is_utilities_legacy):
            report.add(
                file_path, i, "V5_important_in_css",
                line.strip()[:160],
                "!important deveria viver em tokens ou _legacy.css apenas",
            )

    # V10: arquivo de modulo que usa var(--bg-*) sem block [data-bs-theme="light"]
    # Heuristica simples: se usa --bg/--text mas nao tem nenhum hex theme-specific, OK.
    # Se tem hex hardcoded sem tema light, alerta.
    if parent_dir == "modules":
        has_var_usage = "var(--bg" in text or "var(--text" in text or "var(--border" in text
        has_dark_only_hex = bool(re.search(r"background\s*:\s*#[0-9a-fA-F]{3,8}", text, re.IGNORECASE))
        has_light_block = "data-bs-theme=\"light\"" in text or "data-theme=\"light\"" in text or "[data-bs-theme=\"light\"]" in text
        if has_dark_only_hex and not has_light_block and not has_var_usage:
            report.add(
                file_path, 1, "V10_missing_data_bs_theme",
                "(arquivo inteiro)",
                "modulo usa hex hardcoded sem bloco [data-bs-theme=\"light\"] — quebra no light mode",
            )


# ============================================================================
# MAIN
# ============================================================================

def scan_dir(root: Path, suffixes: tuple, audit_fn, report: AuditReport, kind: str) -> None:
    if not root.exists():
        return
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in suffixes:
            # Skip vendor (Bootstrap, etc)
            if "vendor" in path.parts and kind == "css":
                # vendor ainda eh contado como scanned mas nao audited
                report.files_scanned[kind] += 1
                continue
            report.files_scanned[kind] += 1
            audit_fn(path, report)


def write_json_report(report: AuditReport, out: Path) -> None:
    payload = {
        "generated_at": date.today().isoformat(),
        "files_scanned": report.files_scanned,
        "totals_by_violation": dict(report.totals),
        "totals_by_module": {k: dict(v) for k, v in report.by_module.items()},
        "top_files": [
            {"file": f, "violations": dict(c), "total": sum(c.values())}
            for f, c in sorted(report.by_file.items(), key=lambda x: -sum(x[1].values()))[:50]
        ],
        "unique_hex_in_css_top": report.unique_hex_in_css.most_common(30),
        "unique_hex_in_templates_top": report.unique_hex_in_templates.most_common(30),
        "violations": report.violations,
    }
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


VIOLATION_LABELS = {
    "V1_inline_style_color":     "Inline style com cor (color/background/border)",
    "V2_hex_in_template":         "Hex literal dentro de style= em template",
    "V3_hex_in_css_module":       "Hex literal em CSS fora de tokens/vendor",
    "V4_rgb_in_css":              "rgb/rgba/hsl literal em CSS (preferir token)",
    "V5_important_in_css":        "!important em CSS fora de tokens/_legacy",
    "V6_badge_bg_text_combo":     "Badge com bg-* + text-* (derruba design system)",
    "V7_text_bg_combo":           "Combinacao bg + text antagonistica (baixo contraste)",
    "V8_inline_color_class":      "(reservado para extensao)",
    "V9_module_css_hardcoded_bg": "(reservado para extensao)",
    "V10_missing_data_bs_theme":  "Modulo CSS sem suporte a light mode",
}


def write_md_report(report: AuditReport, out: Path) -> None:
    lines = []
    lines.append(f"# UI Audit — Nacom Goya Design System")
    lines.append(f"**Data**: {date.today().isoformat()}")
    lines.append("")
    lines.append(f"**Arquivos escaneados**: {report.files_scanned['templates']} templates, {report.files_scanned['css']} CSS")
    lines.append(f"**Total de violacoes**: {sum(report.totals.values())}")
    lines.append("")

    lines.append("## Resumo por categoria")
    lines.append("| Codigo | Descricao | Total |")
    lines.append("|---|---|---:|")
    for code in sorted(report.totals, key=lambda c: -report.totals[c]):
        label = VIOLATION_LABELS.get(code, code)
        lines.append(f"| `{code}` | {label} | {report.totals[code]} |")
    lines.append("")

    lines.append("## Top 30 hotspots (arquivos com mais violacoes)")
    lines.append("| # | Arquivo | Total | Detalhes |")
    lines.append("|---:|---|---:|---|")
    for i, (file, counts) in enumerate(sorted(report.by_file.items(), key=lambda x: -sum(x[1].values()))[:30], 1):
        total = sum(counts.values())
        details = ", ".join(f"{c}={n}" for c, n in counts.most_common())
        lines.append(f"| {i} | `{file}` | {total} | {details} |")
    lines.append("")

    lines.append("## Violacoes por modulo")
    lines.append("| Modulo | Total | Por categoria |")
    lines.append("|---|---:|---|")
    mod_sorted = sorted(report.by_module.items(), key=lambda x: -sum(x[1].values()))
    for mod, counts in mod_sorted:
        total = sum(counts.values())
        details = ", ".join(f"{c}={n}" for c, n in counts.most_common())
        lines.append(f"| `{mod}` | {total} | {details} |")
    lines.append("")

    lines.append("## Cores hex mais frequentes em templates")
    lines.append("| Hex | Ocorrencias |")
    lines.append("|---|---:|")
    for hex_val, n in report.unique_hex_in_templates.most_common(15):
        lines.append(f"| `{hex_val}` | {n} |")
    lines.append("")

    lines.append("## Cores hex mais frequentes em CSS (fora de tokens)")
    lines.append("| Hex | Ocorrencias |")
    lines.append("|---|---:|")
    for hex_val, n in report.unique_hex_in_css.most_common(15):
        lines.append(f"| `{hex_val}` | {n} |")
    lines.append("")

    # Exemplos concretos das 5 categorias com mais violacoes
    lines.append("## Exemplos concretos (top 5 violacoes mais frequentes)")
    top_codes = [c for c, _ in report.totals.most_common(5)]
    for code in top_codes:
        lines.append(f"### `{code}` — {VIOLATION_LABELS.get(code, '')}")
        examples = [v for v in report.violations if v["code"] == code][:8]
        for v in examples:
            lines.append(f"- `{v['file']}:{v['line']}` — {v['detail']}")
            lines.append(f"  ```\n  {v['snippet']}\n  ```")
        lines.append("")

    out.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="UI Audit — Nacom Goya Design System")
    parser.add_argument("--templates-dir", type=Path, default=DEFAULT_TEMPLATES,
                        help="Diretorio de templates a varrer")
    parser.add_argument("--css-dir", type=Path, default=DEFAULT_CSS,
                        help="Diretorio de CSS a varrer")
    parser.add_argument("--reports-dir", type=Path, default=DEFAULT_REPORTS,
                        help="Onde salvar JSON e MD")
    parser.add_argument("--json-only", action="store_true",
                        help="Gera apenas JSON (skip MD)")
    args = parser.parse_args()

    args.reports_dir.mkdir(parents=True, exist_ok=True)
    report = AuditReport()

    print(f"[ui_audit] Templates: {args.templates_dir}")
    print(f"[ui_audit] CSS:       {args.css_dir}")

    scan_dir(args.templates_dir, (".html",), audit_template, report, "templates")
    scan_dir(args.css_dir, (".css",), audit_css, report, "css")

    today = date.today().isoformat()
    json_path = args.reports_dir / f"ui_audit_{today}.json"
    md_path = args.reports_dir / f"ui_audit_{today}.md"

    write_json_report(report, json_path)
    print(f"[ui_audit] JSON: {json_path}  ({sum(report.totals.values())} violacoes)")

    if not args.json_only:
        write_md_report(report, md_path)
        print(f"[ui_audit] MD:   {md_path}")

    # Resumo no stdout
    print(f"\n[ui_audit] Files scanned: {report.files_scanned}")
    print(f"[ui_audit] Top violations:")
    for code, n in report.totals.most_common(10):
        print(f"  {code:35} {n:>6}")


if __name__ == "__main__":
    main()
