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

Catalogos (apoio ao FINDINGS.md, nao bloqueantes):
  V11 catalog_badge_class      → cada classe .badge-* / .*-badge-* definida em modulo
  V12 catalog_table_row_class  → cada uso de class="...table-(secondary|light|dark)..." em row
  V14 untokenized_bs_var       → uso de --bs-*-text-emphasis|bg-subtle|border-subtle em modulo
                                 (essas vars sao Bootstrap-native, nao tematizadas pelo design system)

Saida:
  relatorios/ui_audit_YYYY-MM-DD.json       (machine-readable)
  relatorios/ui_audit_YYYY-MM-DD.md         (human-readable, top hotspots)
  relatorios/ui_audit_FINDINGS_YYYY-MM-DD.md (consolidado com catalogos e recomendacoes)

Uso:
  python scripts/audits/ui_audit.py
  python scripts/audits/ui_audit.py --json-only
  python scripts/audits/ui_audit.py --templates-dir app/templates/hora
  python scripts/audits/ui_audit.py --findings-only  # gera apenas o FINDINGS
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

# Arquivos CSS canonicos: hex/rgb/hsl literal AQUI eh OK (sao a fonte de verdade
# do design system). Tokens definem valores, components/base implementam APIs
# theme-aware com HSLA/HSL literal por design.
CSS_CANONICAL_DIRS = {"tokens", "vendor", "components", "base"}
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

# V11 — captura class definition: .nome-com-badge { ou , no inicio (lista de seletores)
# Aceita .badge-X, .X-badge, .X-badge-Y, etc. mas exclui :hover/:focus pseudo-classes
RE_BADGE_CLASS_DEF = re.compile(
    r"^\s*\.([a-z][\w-]*badge[\w-]*)(?=\s*[,{:])",
    re.IGNORECASE | re.MULTILINE,
)

# V12 — uso de table-secondary|light|dark em template (em class="...")
# Bootstrap nativo — nao tematizado pelo design system fora de _bootstrap-overrides.css
RE_TABLE_ROW_CLASS = re.compile(
    r'\btable-(secondary|light|dark|info)\b',
    re.IGNORECASE,
)

# V14 — vars Bootstrap-native sem tematizacao no design system
# --bs-*-text-emphasis, --bs-*-bg-subtle, --bs-*-border-subtle
RE_UNTOKENIZED_BS_VAR = re.compile(
    r"var\(\s*(--bs-(?:primary|secondary|success|danger|warning|info|light|dark)-(?:text-emphasis|bg-subtle|border-subtle))\b",
    re.IGNORECASE,
)


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
        # Catalogos (V11/V12/V14) — alimentam o FINDINGS report
        self.badge_classes = defaultdict(list)    # {classname: [(file, line)]} — V11
        self.table_row_uses = []                   # [{file, line, variant}] — V12
        self.untokenized_vars = defaultdict(list)  # {var_name: [(file, line)]} — V14

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
    except Exception:
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

    # V12 — catalogar uso de table-secondary/light/dark/info em rows
    # (table-info esta em _tables.css canonical, mas table-secondary/light/dark NAO estao)
    for m in RE_GENERIC_ELEM_WITH_CLASS.finditer(text):
        line = text[:m.start()].count("\n") + 1
        classes = m.group(1)
        for tm in RE_TABLE_ROW_CLASS.finditer(classes):
            variant = tm.group(1).lower()
            # tr/td sao os elementos relevantes; aceitar todos para nao perder casos
            report.table_row_uses.append({
                "file": str(file_path.relative_to(ROOT)),
                "line": line,
                "variant": variant,
                "classes": classes[:160],
            })
            report.add(
                file_path, line, "V12_table_row_class",
                classes[:160],
                f'uso de table-{variant} (variant {variant} {"OK" if variant == "info" else "NAO"} esta em _tables.css canonical)',
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

    # V11 — catalogar classes badge definidas em modulos (e components, para mapping canonical)
    # Apenas em components/ ou modules/ — vendor/legacy excluidos
    if parent_dir in ("components", "modules"):
        rel = str(file_path.relative_to(ROOT))
        for m in RE_BADGE_CLASS_DEF.finditer(text):
            class_name = m.group(1)
            line_num = text[:m.start()].count("\n") + 1
            origin = "canonical" if parent_dir == "components" else "modulo"
            report.badge_classes[class_name].append({
                "file": rel,
                "line": line_num,
                "origin": origin,
            })

    # V14 — vars Bootstrap-native sem tematizacao (nao detectaveis por outras regras)
    if parent_dir == "modules":
        for i, line_text in enumerate(lines, 1):
            stripped_l = line_text.strip()
            if stripped_l.startswith("/*") or stripped_l.startswith("*") or stripped_l.startswith("//"):
                continue
            for m in RE_UNTOKENIZED_BS_VAR.finditer(line_text):
                var_name = m.group(1)
                rel = str(file_path.relative_to(ROOT))
                report.untokenized_vars[var_name].append({"file": rel, "line": i})
                report.add(
                    file_path, i, "V14_untokenized_bs_var",
                    line_text.strip()[:160],
                    f"var Bootstrap-native '{var_name}' nao e tematizada pelo design system "
                    f"(usar token semantico do design system: --semantic-X, --amber-X, hsl direto, ou definir override)",
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
    "V12_table_row_class":        "Uso de table-secondary/light/dark/info em row",
    "V14_untokenized_bs_var":     "Var Bootstrap-native nao tematizada pelo design system",
}

# Classes canonical disponiveis em components/_badges.css (status badges).
# Usado pelo FINDINGS report para identificar duplicacoes em modulos.
CANONICAL_BADGE_CLASSES = {
    # Variants Bootstrap (filled + outline)
    "badge-primary", "badge-secondary", "badge-success", "badge-danger",
    "badge-warning", "badge-info", "badge-light", "badge-dark",
    "badge-outline-primary", "badge-outline-secondary", "badge-outline-success",
    "badge-outline-danger", "badge-outline-warning", "badge-outline-info",
    "badge-outline-light", "badge-outline-dark",
    # Status canonicos
    "badge-status-pendente", "badge-pendente",
    "badge-status-aprovado", "badge-aprovado",
    "badge-status-conferido", "badge-conferido",
    "badge-status-rejeitado", "badge-rejeitado",
    "badge-status-reprovado", "badge-reprovado",
    "badge-status-pago", "badge-pago",
    "badge-status-lancado", "badge-lancado",
    "badge-status-cancelado", "badge-cancelado",
    "badge-status-rascunho", "badge-rascunho",
    "badge-status-accent", "badge-status",
    "badge",  # base
}

# Status semanticos canonicos (mapping para identificar duplicacao por sufixo).
# Quando _hora.css define badge-status-cancelado e _badges.css ja tem o mesmo,
# isso e duplicacao real.
CANONICAL_STATUS_SUFFIXES = {
    "pendente", "aprovado", "conferido", "rejeitado", "reprovado",
    "pago", "lancado", "cancelado", "rascunho",
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


def write_findings_md_report(report: AuditReport, out: Path) -> None:
    """Gera FINDINGS consolidado: catalogos + recomendacoes (humano-legivel)."""
    L = []
    L.append("# UI Audit — FINDINGS Consolidados")
    L.append(f"**Data**: {date.today().isoformat()}")
    L.append("")
    L.append(f"**Arquivos escaneados**: {report.files_scanned['templates']} templates, "
             f"{report.files_scanned['css']} CSS")
    L.append(f"**Total de violacoes (V1-V10) + catalogo (V12, V14)**: {sum(report.totals.values())}")
    L.append("")
    L.append("> Este documento e um espelho legivel do estado atual. Para violacoes "
             "automatizaveis ver `ui_audit_<data>.md` (top hotspots).")
    L.append("> Para regras de uso correto ver `.claude/references/design/GUIA_COMPONENTES_UI.md`.")
    L.append("")

    # ────────────────────────────────────────────────────────────────────
    # 1. Sumario por categoria
    # ────────────────────────────────────────────────────────────────────
    L.append("## 1. Sumario por categoria")
    L.append("| Codigo | Descricao | Total |")
    L.append("|---|---|---:|")
    for code in sorted(report.totals, key=lambda c: -report.totals[c]):
        label = VIOLATION_LABELS.get(code, code)
        L.append(f"| `{code}` | {label} | {report.totals[code]} |")
    L.append("")

    # ────────────────────────────────────────────────────────────────────
    # 2. Catalogo de badges (V11) — duplicacao cross-modulo
    # ────────────────────────────────────────────────────────────────────
    L.append("## 2. Catalogo de classes badge")
    L.append("")
    L.append("Lista todas as classes `*badge*` definidas em `components/` (canonical) e "
             "`modules/` (modulo-especifico). Identifica duplicacao real (mesmo nome em multiplos "
             "arquivos) e duplicacao semantica (sufixo equivalente a um status canonical).")
    L.append("")

    # Duplicacao real: mesmo nome em 2+ arquivos DISTINTOS
    # (regex captura pseudoclasses como :hover/:focus separadamente, entao filtramos por file unicos)
    real_dup = {}
    for cls, entries in report.badge_classes.items():
        unique_files = set(e["file"] for e in entries)
        if len(unique_files) > 1:
            real_dup[cls] = entries
    L.append(f"### 2.1 Duplicacao REAL (mesmo nome em 2+ arquivos distintos): {len(real_dup)}")
    if real_dup:
        L.append("| Classe | Arquivos | Recomendacao |")
        L.append("|---|---|---|")
        for cls in sorted(real_dup):
            entries = real_dup[cls]
            # agrupar entries por arquivo e mostrar primeira linha de cada
            by_file = defaultdict(list)
            for e in entries:
                by_file[e["file"]].append(e["line"])
            locs = ", ".join(
                f"`{f}:{min(lines)}` ({entries[0]['origin'] if f == entries[0]['file'] else 'modulo'})"
                for f, lines in by_file.items()
            )
            in_canonical = any(e["origin"] == "canonical" for e in entries)
            rec = "Manter so canonical (modulo redefine)" if in_canonical else "Consolidar em canonical ou prefixar com modulo"
            L.append(f"| `.{cls}` | {locs} | {rec} |")
    else:
        L.append("Nenhuma.")
    L.append("")

    # Duplicacao semantica: sufixo igual a um status canonical mas em modulo
    L.append("### 2.2 Duplicacao SEMANTICA (sufixo equivale a status canonical mas vive em modulo)")
    L.append("Estes deveriam reusar a classe canonical de `_badges.css` em vez de redefinir.")
    L.append("")
    semantic_dup = []
    for cls, entries in report.badge_classes.items():
        # so reportar se NAO esta em canonical
        if any(e["origin"] == "canonical" for e in entries):
            continue
        # extrair sufixo: tudo apos -status- ou -badge-
        for suffix in CANONICAL_STATUS_SUFFIXES:
            if cls.endswith("-" + suffix) or cls == suffix:
                semantic_dup.append((cls, suffix, entries[0]))
                break
    if semantic_dup:
        L.append("| Classe modulo | Sufixo | Definida em | Canonical equivalente |")
        L.append("|---|---|---|---|")
        for cls, suffix, entry in sorted(semantic_dup):
            L.append(f"| `.{cls}` | `{suffix}` | `{entry['file']}:{entry['line']}` | "
                     f"`.badge-status-{suffix}` ou `.badge-{suffix}` |")
    else:
        L.append("Nenhuma.")
    L.append("")

    # Inventario completo por modulo (para visibilidade)
    L.append("### 2.3 Inventario completo por arquivo")
    L.append("")
    by_file_badges = defaultdict(list)
    for cls, entries in report.badge_classes.items():
        for e in entries:
            by_file_badges[e["file"]].append((cls, e["line"]))
    for file in sorted(by_file_badges):
        classes_in_file = sorted(by_file_badges[file], key=lambda x: x[1])
        L.append(f"**`{file}`** ({len(classes_in_file)} classes):")
        L.append("")
        for cls, line_n in classes_in_file:
            L.append(f"- L{line_n}: `.{cls}`")
        L.append("")

    # ────────────────────────────────────────────────────────────────────
    # 3. Catalogo de table rows (V12)
    # ────────────────────────────────────────────────────────────────────
    L.append("## 3. Catalogo de uso de `table-secondary/light/dark/info`")
    L.append("")
    L.append("`table-success/primary/warning/danger/info` estao tematizadas em "
             "`components/_tables.css`. **`table-secondary` e `table-light/dark` NAO estao** — "
             "usam default Bootstrap nativo, que quebra a hierarquia de elevacao no dark mode.")
    L.append("")
    by_variant = defaultdict(list)
    for u in report.table_row_uses:
        by_variant[u["variant"]].append(u)
    for variant in sorted(by_variant):
        entries = by_variant[variant]
        canonical_status = "OK (em _tables.css)" if variant == "info" else "**FALTANDO em _tables.css canonical**"
        L.append(f"### `table-{variant}` — {len(entries)} usos — {canonical_status}")
        L.append("")
        for e in entries[:20]:  # cap per variant
            L.append(f"- `{e['file']}:{e['line']}` — `{e['classes']}`")
        if len(entries) > 20:
            L.append(f"- ... e mais {len(entries) - 20} ocorrencias")
        L.append("")

    # ────────────────────────────────────────────────────────────────────
    # 4. Vars Bootstrap-native nao tematizadas (V14)
    # ────────────────────────────────────────────────────────────────────
    L.append("## 4. Vars Bootstrap-native nao tematizadas (V14)")
    L.append("")
    L.append("Estas vars (`--bs-*-text-emphasis`, `--bs-*-bg-subtle`, `--bs-*-border-subtle`) "
             "vem do Bootstrap default e NAO sao tematizadas pelo design system. No dark mode "
             "podem retornar valores incompativeis (ex: `--bs-warning-text-emphasis` retorna "
             "`#ffda6a` no dark do Bootstrap, criando 'amarelo claro sobre amarelo solido' em "
             "badges com `bg: var(--bs-warning)`).")
    L.append("")
    if report.untokenized_vars:
        L.append("| Var | Ocorrencias | Arquivos |")
        L.append("|---|---:|---|")
        for var in sorted(report.untokenized_vars):
            entries = report.untokenized_vars[var]
            files = sorted(set(e["file"] for e in entries))
            files_str = ", ".join(f"`{f}`" for f in files[:5])
            if len(files) > 5:
                files_str += f", +{len(files) - 5} outros"
            L.append(f"| `{var}` | {len(entries)} | {files_str} |")
    else:
        L.append("Nenhuma encontrada.")
    L.append("")

    # ────────────────────────────────────────────────────────────────────
    # 5. Casos especificos (curados manualmente — high-impact)
    # ────────────────────────────────────────────────────────────────────
    L.append("## 5. Casos high-impact (curados)")
    L.append("")
    L.append("Casos identificados manualmente que merecem prioridade pelo impacto visual.")
    L.append("")
    L.append("### 5.1 Badge 'Parcialmente Faturado' ilegivel no dark mode")
    L.append("")
    L.append("**Sintoma**: Em `/hora/pedidos`, dark mode, badge `Parcialmente Faturado` aparece "
             "como amarelo claro sobre amarelo solido (texto invisivel).")
    L.append("")
    L.append("**Fonte**: `app/static/css/modules/_hora.css:129-133`")
    L.append("```css")
    L.append(".badge-status-parcialmente_faturado,")
    L.append(".badge-status-em_conferencia {")
    L.append("    background-color: var(--bs-warning);")
    L.append("    color: var(--bs-warning-text-emphasis, #664d03);")
    L.append("}")
    L.append("```")
    L.append("")
    L.append("**Causa raiz**: `--bs-warning-text-emphasis` e Bootstrap-native, nao tematizada "
             "pelo design system. Fallback `#664d03` (escuro) so aplica se a var nao existir; mas "
             "Bootstrap define a var em ambos os temas com cores opostas (light: escuro, dark: claro).")
    L.append("")
    L.append("**Como deveria estar** (API canonical com cor fixa):")
    L.append("```css")
    L.append(".badge-status-parcialmente_faturado,")
    L.append(".badge-status-em_conferencia {")
    L.append("    --_badge-bg: var(--amber-50);")
    L.append("    --_badge-color: hsl(0 0% 10%);  /* fixo: contraste em ambos os temas */")
    L.append("}")
    L.append("```")
    L.append("")

    L.append("### 5.2 Tabela `/hora/estoque` com linhas que nao respeitam tema")
    L.append("")
    L.append("**Sintoma**: Linhas com `class=\"table-secondary text-muted\"` (motos fora de "
             "estoque) aparecem com fundo cinza claro Bootstrap-default em vez do tom escuro do tema.")
    L.append("")
    L.append("**Fonte**: `app/templates/hora/estoque_lista.html:344`")
    L.append("```html")
    L.append('<tr class="{% if not m.moto_disponivel %}table-secondary text-muted{% elif ... %}">')
    L.append("```")
    L.append("")
    L.append("**Causa raiz**: `_tables.css` e `_bootstrap-overrides.css` definem `.table-success/"
             "primary/warning/danger/info`. **`.table-secondary` nao esta no canonical** — usa o "
             "Bootstrap-default cinza-medio que ignora tokens.")
    L.append("")
    L.append("**Como deveria estar**: adicionar em `components/_tables.css`:")
    L.append("```css")
    L.append(".table-secondary {")
    L.append("    --_row-bg: hsla(0 0% 50% / 0.10);")
    L.append("    --_row-hover-bg: hsla(0 0% 50% / 0.20);")
    L.append("    background-color: var(--_row-bg);")
    L.append("}")
    L.append(".table-secondary:hover { background-color: var(--_row-hover-bg); }")
    L.append("```")
    L.append("")

    # ────────────────────────────────────────────────────────────────────
    # 6. Recomendacoes consolidadas
    # ────────────────────────────────────────────────────────────────────
    L.append("## 6. Recomendacoes consolidadas (proximas fases)")
    L.append("")
    L.append("Esta auditoria foi gerada pela Fase A do plano. As fases seguintes (B/C/E/F) "
             "deverao consumir este documento.")
    L.append("")
    L.append("### Fase B — Componentes canonicos")
    L.append("- `_badges.css`: adicionar status faltantes detectados em 2.2 (sufixo nao-canonical "
             "frequente em modulos: `aberto, faturado, em_andamento, em_separacao, em_transito, "
             "em_conferencia, parcialmente_faturado, com_divergencia, recebido, vendido, devolvido, "
             "reservado, avariado, ativo, resolvido, tratativa`)")
    L.append("- `_tables.css`: adicionar `.table-secondary` (e revisar se vale incluir overrides "
             "explicitos `.table-light/dark` em vez de manter no `_bootstrap-overrides.css`)")
    L.append("- Consolidar TODOS os overrides de tabela em `_tables.css` (mover de "
             "`_bootstrap-overrides.css` para reduzir fontes de verdade)")
    L.append("")
    L.append("### Fase C — Refatorar modulos")
    L.append("- **`_hora.css`**: trocar `background-color/color` direto por API "
             "`--_badge-bg/color`; remover uso de `--bs-warning-text-emphasis` (substituir por "
             "`hsl(0 0% 10%)` fixo); deletar classes que duplicam canonical (ver tabela 2.1)")
    L.append("- **`_pallet-unified.css`**: migrar `pu-badge-status--*` para API canonical (mantendo "
             "prefixo `pu-` se variante visual 'tinted' for intencional)")
    L.append("- **`_carvia.css`**: ~40 badges com prefixo `carvia-badge-*` — auditar se podem "
             "reutilizar canonical (rascunho, confirmado, cancelado, pendente, conferido, aprovado)")
    L.append("- **`_seguranca.css`**: ja usa API correta, apenas auditar coverage")
    L.append("")
    L.append("### Fase E — Templates")
    L.append("- Substituir `class=\"badge bg-X text-Y\"` redundantes por `badge badge-status-X` "
             f"({report.totals.get('V6_badge_bg_text_combo', 0)} ocorrencias)")
    L.append("- Limpar inline styles com cor "
             f"({report.totals.get('V1_inline_style_color', 0)} ocorrencias)")
    L.append("- Substituir `table-secondary` em `/hora/estoque` (e similares) por classe correta "
             "apos Fase B definir o canonical")
    L.append("")
    L.append("### Fase F — Wiring/Enforcement")
    L.append("- Pre-commit hook rodando `ui_audit.py --json-only` em modo baseline (so falha em "
             "regressao)")
    L.append("- CI check comparando audit do PR com `relatorios/ui_audit_baseline.json` commitado")
    L.append("- Atualizar `CLAUDE.md` apontando para fonte unica `GUIA_COMPONENTES_UI.md`")
    L.append("")

    out.write_text("\n".join(L), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="UI Audit — Nacom Goya Design System")
    parser.add_argument("--templates-dir", type=Path, default=DEFAULT_TEMPLATES,
                        help="Diretorio de templates a varrer")
    parser.add_argument("--css-dir", type=Path, default=DEFAULT_CSS,
                        help="Diretorio de CSS a varrer")
    parser.add_argument("--reports-dir", type=Path, default=DEFAULT_REPORTS,
                        help="Onde salvar JSON e MD")
    parser.add_argument("--json-only", action="store_true",
                        help="Gera apenas JSON (skip MD/FINDINGS)")
    parser.add_argument("--findings-only", action="store_true",
                        help="Gera apenas o FINDINGS report (skip JSON/MD top hotspots)")
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
    findings_path = args.reports_dir / f"ui_audit_FINDINGS_{today}.md"

    if not args.findings_only:
        write_json_report(report, json_path)
        print(f"[ui_audit] JSON:     {json_path}  ({sum(report.totals.values())} violacoes)")
        if not args.json_only:
            write_md_report(report, md_path)
            print(f"[ui_audit] MD:       {md_path}")

    if not args.json_only:
        write_findings_md_report(report, findings_path)
        print(f"[ui_audit] FINDINGS: {findings_path}")

    # Resumo no stdout
    print(f"\n[ui_audit] Files scanned: {report.files_scanned}")
    print(f"[ui_audit] Top violations:")
    for code, n in report.totals.most_common(10):
        print(f"  {code:35} {n:>6}")
    print(f"[ui_audit] Badge classes catalogadas: {len(report.badge_classes)} unicas")
    print(f"[ui_audit] Table row uses (sec/light/dark/info): {len(report.table_row_uses)}")
    print(f"[ui_audit] Untokenized BS vars: {sum(len(v) for v in report.untokenized_vars.values())}")


if __name__ == "__main__":
    main()
