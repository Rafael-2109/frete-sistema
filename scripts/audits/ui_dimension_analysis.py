#!/usr/bin/env python3
"""
UI Dimension Analysis — analise estrutural do design system.

Diferente de ui_audit.py (foca em SINTAXE proibida), este analisa as DIMENSOES
do problema:

  1. Tokens auto-validados   — WCAG ratio entre cada par bg/text do design system
  2. Vars Bootstrap raras    — --bs-purple/pink/cyan/orange/teal/indigo em uso
  3. Vars BS nao tematizadas — --bs-X-bg-subtle/text-emphasis/border-subtle
  4. Classes pastel BS       — bg-X-subtle em templates
  5. Bootstrap opacity       — bg-X bg-opacity-N
  6. Headers (semantica)     — variantes de modal-header/card-header (catalogo)
  7. <style> blocks          — em templates (proibido por convencao)
  8. Cores via JavaScript    — element.style.color/background = ... em JS inline
  9. Cores em SVG inline     — <svg fill="..."> em templates
 10. Cores condicionais Jinja — {{ 'X' if Y else 'Z' }} em style/class

Saida:
  relatorios/ui_dimension_analysis_YYYY-MM-DD.md  — humano-legivel
  relatorios/ui_dimension_analysis_YYYY-MM-DD.json — machine-readable

Uso:
  python scripts/audits/ui_dimension_analysis.py
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TEMPLATES = ROOT / "app" / "templates"
DEFAULT_CSS = ROOT / "app" / "static" / "css"
DEFAULT_REPORTS = ROOT / "relatorios"

# ════════════════════════════════════════════════════════════════════════════
# WCAG CONTRAST CALCULATION
# ════════════════════════════════════════════════════════════════════════════

def hsl_to_rgb(h: float, s: float, l: float) -> tuple[float, float, float]:
    """HSL (h em graus, s/l em [0,1]) → sRGB (cada canal em [0,1])."""
    s = max(0.0, min(1.0, s))
    l = max(0.0, min(1.0, l))
    c = (1 - abs(2 * l - 1)) * s
    h_prime = (h % 360) / 60.0
    x = c * (1 - abs(h_prime % 2 - 1))
    if 0 <= h_prime < 1:
        r1, g1, b1 = c, x, 0
    elif 1 <= h_prime < 2:
        r1, g1, b1 = x, c, 0
    elif 2 <= h_prime < 3:
        r1, g1, b1 = 0, c, x
    elif 3 <= h_prime < 4:
        r1, g1, b1 = 0, x, c
    elif 4 <= h_prime < 5:
        r1, g1, b1 = x, 0, c
    else:
        r1, g1, b1 = c, 0, x
    m = l - c / 2
    return (r1 + m, g1 + m, b1 + m)


def hex_to_rgb(hex_str: str) -> tuple[float, float, float]:
    """#RRGGBB ou #RGB → sRGB em [0,1]."""
    h = hex_str.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        raise ValueError(f"hex invalido: {hex_str}")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))  # type: ignore


def relative_luminance(rgb: tuple[float, float, float]) -> float:
    """WCAG 2.1: relative luminance L."""
    def linearize(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (linearize(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(rgb1: tuple[float, float, float], rgb2: tuple[float, float, float]) -> float:
    """WCAG contrast ratio (1.0 a 21.0)."""
    l1 = relative_luminance(rgb1)
    l2 = relative_luminance(rgb2)
    lighter, darker = (l1, l2) if l1 > l2 else (l2, l1)
    return (lighter + 0.05) / (darker + 0.05)


def parse_color(value: str) -> tuple[float, float, float] | None:
    """Aceita 'hsl(H S% L%)' (espaco) ou '#RRGGBB' ou '#RGB' ou 'rgb(R, G, B)'."""
    value = value.strip().lower()
    # hex
    if value.startswith("#"):
        try:
            return hex_to_rgb(value)
        except Exception:
            return None
    # hsl com vírgulas: hsl(60, 70%, 45%)
    m = re.match(r"hsla?\s*\(\s*(-?\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)%\s*,\s*(\d+(?:\.\d+)?)%", value)
    if m:
        h, s, l = float(m.group(1)), float(m.group(2)) / 100, float(m.group(3)) / 100
        return hsl_to_rgb(h, s, l)
    # hsl moderno com espaços: hsl(60 70% 45%)
    m = re.match(r"hsla?\s*\(\s*(-?\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)%\s+(\d+(?:\.\d+)?)%", value)
    if m:
        h, s, l = float(m.group(1)), float(m.group(2)) / 100, float(m.group(3)) / 100
        return hsl_to_rgb(h, s, l)
    # rgb
    m = re.match(r"rgba?\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", value)
    if m:
        return tuple(int(g) / 255.0 for g in m.groups())  # type: ignore
    return None


WCAG_AA_NORMAL = 4.5
WCAG_AA_LARGE = 3.0
WCAG_AAA_NORMAL = 7.0


def wcag_status(ratio: float, large: bool = False) -> str:
    threshold = WCAG_AA_LARGE if large else WCAG_AA_NORMAL
    if ratio >= WCAG_AAA_NORMAL:
        return "AAA"
    if ratio >= threshold:
        return "AA"
    return "FAIL"


# ════════════════════════════════════════════════════════════════════════════
# TOKEN EXTRACTION (de _design-tokens.css)
# ════════════════════════════════════════════════════════════════════════════

# Tokens que sao COR (nao spacing, font, etc.)
COLOR_TOKEN_NAMES = {
    "bg-dark", "bg", "bg-light", "bg-button",
    "text", "text-muted", "border",
    "amber-28", "amber-40", "amber-50", "amber-55", "amber-60",
    "semantic-success", "semantic-danger", "semantic-warning", "semantic-info",
    "semantic-success-subtle", "semantic-danger-subtle",
    "semantic-warning-subtle", "semantic-info-subtle",
    "warning-outline-text", "highlight",
    "bs-primary", "bs-secondary", "bs-success", "bs-danger",
    "bs-warning", "bs-info", "bs-link-color",
    "bs-body-bg", "bs-body-color",
}


def extract_tokens_from_design_tokens() -> dict[str, dict[str, str]]:
    """Retorna {tema: {token_name: valor_css}} para light e dark."""
    path = DEFAULT_CSS / "tokens" / "_design-tokens.css"
    text = path.read_text(encoding="utf-8")

    # Detectar blocos [data-bs-theme="dark"] e [data-bs-theme="light"]
    # Tokens em :root tambem sao globais (aplicam a ambos via override do tema)
    tokens: dict[str, dict[str, str]] = {"dark": {}, "light": {}, "root": {}}

    # Captura blocos de seletor com seu conteudo
    # Para simplicidade: dividir o file em chunks por seletor inicial
    # Usa o approach: encontrar seletores e seus blocos {}

    selector_pattern = re.compile(
        r'(\[data-bs-theme="(dark|light)"\][^{]*\{|:root[^{]*\{)',
        re.MULTILINE,
    )
    matches = list(selector_pattern.finditer(text))
    for i, m in enumerate(matches):
        sel = m.group(1)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[start:end]
        # Tema
        if 'data-bs-theme="dark"' in sel:
            theme = "dark"
        elif 'data-bs-theme="light"' in sel:
            theme = "light"
        else:
            theme = "root"

        # Captura --token-name: valor;
        for var_match in re.finditer(r"--([\w-]+)\s*:\s*([^;\n]+)\s*;", block):
            name = var_match.group(1)
            value = var_match.group(2).strip()
            tokens[theme][name] = value

    return tokens


def resolve_token(token: str, tokens: dict[str, dict[str, str]], theme: str,
                  visited: set | None = None) -> str | None:
    """Resolve var(--X) recursivamente para valor literal."""
    if visited is None:
        visited = set()
    if token in visited:
        return None
    visited.add(token)

    # Procurar primeiro no tema, depois no root
    value = tokens.get(theme, {}).get(token) or tokens.get("root", {}).get(token)
    if value is None:
        return None

    # Se ainda contem var(...), resolver
    var_pattern = re.compile(r"var\(\s*--([\w-]+)\s*(?:,\s*[^)]+)?\)")
    while True:
        m = var_pattern.search(value)
        if not m:
            break
        inner_name = m.group(1)
        resolved = resolve_token(inner_name, tokens, theme, visited)
        if resolved is None:
            # Nao conseguiu resolver — retornar o que tem
            return value
        value = value[:m.start()] + resolved + value[m.end():]

    return value


# ════════════════════════════════════════════════════════════════════════════
# DIMENSAO 1 — TOKENS WCAG
# ════════════════════════════════════════════════════════════════════════════

# Pares (background_token, text_token, descricao) que o design system EXIGE
# que tenham contraste AA. Lista curada conforme uso real do sistema.
TOKEN_PAIRS_TO_CHECK = [
    # Tema base — texto sobre cada nivel de bg
    ("bg-dark", "text", "body sobre dark bg"),
    ("bg", "text", "surface sobre bg"),
    ("bg-light", "text", "card/input sobre bg-light"),
    ("bg-button", "text", "button neutro"),
    ("bg-light", "text-muted", "texto secundario em card"),

    # Badges com fundo colorido + branco (padrao filled)
    ("semantic-success", "white", "badge bg-success + texto branco"),
    ("semantic-danger", "white", "badge bg-danger + texto branco"),
    ("semantic-info", "white", "badge bg-info + texto branco"),

    # Badges/buttons amber + texto escuro fixo (api custom property)
    ("amber-50", "dark10", "badge bg-warning + texto escuro"),
    ("amber-55", "dark10", "btn-primary + texto escuro"),

    # Bootstrap mapping (bs-success no dark = semantic-success forte)
    ("bs-success", "white", "bg-success + texto branco"),
    ("bs-danger", "white", "bg-danger + texto branco"),
    ("bs-warning", "dark10", "bg-warning + texto escuro"),
    ("bs-info", "white", "bg-info + texto branco"),
    ("bs-primary", "dark10", "bg-primary (amber) + texto escuro"),
]

# Tokens "literais" especiais (nao em _design-tokens.css mas usados muito)
LITERAL_COLORS = {
    "white": "hsl(0 0% 100%)",
    "dark10": "hsl(0 0% 10%)",
    "dark5": "hsl(0 0% 5%)",
}


def analyze_token_pairs(tokens: dict[str, dict[str, str]]) -> list[dict]:
    """Calcula WCAG ratio para cada par TOKEN_PAIRS_TO_CHECK em ambos os temas."""
    results = []
    for theme in ("light", "dark"):
        for bg_name, text_name, desc in TOKEN_PAIRS_TO_CHECK:
            bg_value = (LITERAL_COLORS.get(bg_name)
                        or resolve_token(bg_name, tokens, theme))
            text_value = (LITERAL_COLORS.get(text_name)
                          or resolve_token(text_name, tokens, theme))

            if not bg_value or not text_value:
                results.append({
                    "theme": theme, "bg": bg_name, "text": text_name,
                    "bg_value": bg_value, "text_value": text_value,
                    "ratio": None, "status": "UNRESOLVED", "desc": desc,
                })
                continue

            bg_rgb = parse_color(bg_value)
            text_rgb = parse_color(text_value)
            if not bg_rgb or not text_rgb:
                results.append({
                    "theme": theme, "bg": bg_name, "text": text_name,
                    "bg_value": bg_value, "text_value": text_value,
                    "ratio": None, "status": "UNPARSEABLE", "desc": desc,
                })
                continue

            ratio = contrast_ratio(bg_rgb, text_rgb)
            results.append({
                "theme": theme, "bg": bg_name, "text": text_name,
                "bg_value": bg_value, "text_value": text_value,
                "ratio": round(ratio, 2),
                "status": wcag_status(ratio),
                "desc": desc,
            })
    return results


# ════════════════════════════════════════════════════════════════════════════
# DIMENSAO 2,3 — VARS BOOTSTRAP (raras + nao tematizadas)
# ════════════════════════════════════════════════════════════════════════════

BS_RARE_VARS = (
    "purple", "pink", "cyan", "orange", "teal", "indigo",
    "yellow", "red", "green", "blue", "gray-100", "gray-200", "gray-300",
    "gray-400", "gray-500", "gray-600", "gray-700", "gray-800", "gray-900",
    "gray", "gray-dark", "black",
)
BS_UNTOKENIZED_SUFFIXES = (
    "text-emphasis", "bg-subtle", "border-subtle",
)

# Detectar uso em template (style attribute)
RE_STYLE_ATTR = re.compile(r'style\s*=\s*"([^"]*)"', re.IGNORECASE)

# Detectar var(--bs-X) em qualquer arquivo
def find_bs_vars_usage(file_path: Path, file_kind: str) -> list[dict]:
    """Retorna lista de usos de --bs-X-* fora do permitido."""
    usages = []
    try:
        text = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return usages

    # Pattern 1: var(--bs-X) onde X = rare ou untokenized
    rare_pattern = re.compile(
        r"var\(\s*--bs-(" + "|".join(re.escape(v) for v in BS_RARE_VARS) + r")\b",
        re.IGNORECASE,
    )
    untokenized_pattern = re.compile(
        r"var\(\s*--bs-(\w+)-(" + "|".join(BS_UNTOKENIZED_SUFFIXES) + r")\b",
        re.IGNORECASE,
    )

    lines = text.split("\n")
    for i, line in enumerate(lines, 1):
        for m in rare_pattern.finditer(line):
            usages.append({
                "file": str(file_path.relative_to(ROOT)),
                "line": i,
                "kind": "rare_bs_var",
                "var": f"--bs-{m.group(1).lower()}",
                "snippet": line.strip()[:160],
                "file_kind": file_kind,
            })
        for m in untokenized_pattern.finditer(line):
            usages.append({
                "file": str(file_path.relative_to(ROOT)),
                "line": i,
                "kind": "untokenized_bs_var",
                "var": f"--bs-{m.group(1).lower()}-{m.group(2).lower()}",
                "snippet": line.strip()[:160],
                "file_kind": file_kind,
            })
    return usages


# ════════════════════════════════════════════════════════════════════════════
# DIMENSAO 4 — CLASSES PASTEL (bg-X-subtle)
# ════════════════════════════════════════════════════════════════════════════

RE_BS_SUBTLE_CLASS = re.compile(
    r'\bbg-(primary|secondary|success|danger|warning|info|light|dark)-subtle\b',
    re.IGNORECASE,
)
RE_BS_OPACITY_CLASS = re.compile(
    r'\bbg-opacity-(10|25|50|75)\b',
    re.IGNORECASE,
)


def find_pastel_classes(file_path: Path) -> list[dict]:
    """Encontra bg-X-subtle e bg-opacity-N em templates."""
    usages = []
    try:
        text = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return usages

    lines = text.split("\n")
    for i, line in enumerate(lines, 1):
        for m in RE_BS_SUBTLE_CLASS.finditer(line):
            usages.append({
                "file": str(file_path.relative_to(ROOT)),
                "line": i,
                "kind": "bg_subtle",
                "class": f"bg-{m.group(1).lower()}-subtle",
                "snippet": line.strip()[:160],
            })
        for m in RE_BS_OPACITY_CLASS.finditer(line):
            usages.append({
                "file": str(file_path.relative_to(ROOT)),
                "line": i,
                "kind": "bg_opacity",
                "class": f"bg-opacity-{m.group(1)}",
                "snippet": line.strip()[:160],
            })
    return usages


# ════════════════════════════════════════════════════════════════════════════
# DIMENSAO 6 — HEADERS (modal-header / card-header) — catalogo de variantes
# ════════════════════════════════════════════════════════════════════════════

RE_HEADER_TAG = re.compile(
    r'<(div|section|header|nav)\b[^>]*class\s*=\s*"([^"]*\b(?:modal-header|card-header)\b[^"]*)"[^>]*?(?:style\s*=\s*"([^"]*)")?[^>]*>',
    re.IGNORECASE | re.DOTALL,
)


def find_header_variants(file_path: Path) -> list[dict]:
    """Catalogar uso de modal-header e card-header com suas classes/styles."""
    usages = []
    try:
        text = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return usages

    for m in RE_HEADER_TAG.finditer(text):
        line = text[:m.start()].count("\n") + 1
        classes = m.group(2)
        style = m.group(3) or ""
        kind = "modal-header" if "modal-header" in classes else "card-header"

        # Identificar "signature" da variante: classes BG + style com cor
        bg_classes = re.findall(r"\bbg-[\w-]+", classes)
        opacity_classes = re.findall(r"\bbg-opacity-\d+", classes)
        text_classes = re.findall(r"\btext-[\w-]+", classes)

        has_inline_bg = bool(re.search(r"background", style, re.IGNORECASE))
        has_inline_color = bool(re.search(r"color\s*:", style, re.IGNORECASE))

        sig_parts = []
        if bg_classes:
            sig_parts.extend(sorted(bg_classes))
        if opacity_classes:
            sig_parts.extend(sorted(opacity_classes))
        if text_classes:
            sig_parts.extend(sorted(text_classes))
        if has_inline_bg:
            sig_parts.append("INLINE-BG")
        if has_inline_color:
            sig_parts.append("INLINE-COLOR")
        if not sig_parts:
            sig_parts.append("NEUTRO")

        signature = "+".join(sig_parts)
        usages.append({
            "file": str(file_path.relative_to(ROOT)),
            "line": line,
            "kind": kind,
            "signature": signature,
            "classes": classes[:120],
            "style": style[:120],
        })
    return usages


# ════════════════════════════════════════════════════════════════════════════
# DIMENSAO 7 — <style> blocks em templates
# ════════════════════════════════════════════════════════════════════════════

RE_STYLE_BLOCK = re.compile(r"<style\b[^>]*>(.*?)</style>", re.IGNORECASE | re.DOTALL)


def find_style_blocks(file_path: Path) -> list[dict]:
    usages = []
    try:
        text = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return usages
    for m in RE_STYLE_BLOCK.finditer(text):
        line = text[:m.start()].count("\n") + 1
        block = m.group(1)
        # So reportar se tem cor
        has_color = bool(re.search(r"color\s*:|background", block, re.IGNORECASE))
        if has_color:
            usages.append({
                "file": str(file_path.relative_to(ROOT)),
                "line": line,
                "size_chars": len(block),
                "preview": block.strip()[:120].replace("\n", " "),
            })
    return usages


# ════════════════════════════════════════════════════════════════════════════
# DIMENSAO 8 — JS color manipulation
# ════════════════════════════════════════════════════════════════════════════

RE_JS_COLOR = re.compile(
    r"\.style\.(background(?:Color)?|color)\s*=\s*['\"][^'\"]+['\"]",
    re.IGNORECASE,
)


def find_js_color_assignments(file_path: Path) -> list[dict]:
    usages = []
    try:
        text = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return usages
    for m in RE_JS_COLOR.finditer(text):
        line = text[:m.start()].count("\n") + 1
        usages.append({
            "file": str(file_path.relative_to(ROOT)),
            "line": line,
            "snippet": m.group(0)[:120],
        })
    return usages


# ════════════════════════════════════════════════════════════════════════════
# DIMENSAO 9 — SVG inline com cor
# ════════════════════════════════════════════════════════════════════════════

RE_SVG_COLOR = re.compile(
    r'(?:<svg|<path|<circle|<rect|<polygon|<line)[^>]*'
    r'(?:fill|stroke)\s*=\s*"(#[0-9a-fA-F]{3,8}|rgba?\([^)]+\))"',
    re.IGNORECASE | re.DOTALL,
)


def find_svg_colors(file_path: Path) -> list[dict]:
    usages = []
    try:
        text = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return usages
    for m in RE_SVG_COLOR.finditer(text):
        line = text[:m.start()].count("\n") + 1
        usages.append({
            "file": str(file_path.relative_to(ROOT)),
            "line": line,
            "color": m.group(1),
            "snippet": m.group(0)[:120],
        })
    return usages


# ════════════════════════════════════════════════════════════════════════════
# DIMENSAO 10 — Cores condicionais Jinja
# ════════════════════════════════════════════════════════════════════════════

# Pattern: {{ 'X' if Y else 'Z' }} OU {% if Y %}#XXX{% else %}#YYY{% endif %}
# em contexto de style ou class
RE_JINJA_COLOR_INLINE = re.compile(
    r'\{\{\s*[\'"](#[0-9a-fA-F]{3,8})[\'"]\s+if\s.*?else\s+[\'"](#[0-9a-fA-F]{3,8})[\'"]\s*\}\}',
    re.IGNORECASE,
)


def find_jinja_conditional_colors(file_path: Path) -> list[dict]:
    usages = []
    try:
        text = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return usages
    for m in RE_JINJA_COLOR_INLINE.finditer(text):
        line = text[:m.start()].count("\n") + 1
        usages.append({
            "file": str(file_path.relative_to(ROOT)),
            "line": line,
            "color1": m.group(1),
            "color2": m.group(2),
            "snippet": m.group(0)[:120],
        })
    return usages


# ════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════

def iter_files(root: Path, suffixes: tuple) -> Iterable[Path]:
    if not root.exists():
        return
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in suffixes:
            if "vendor" in p.parts:
                continue
            yield p


def write_md_report(payload: dict, out_path: Path) -> None:
    L = []
    L.append(f"# UI Dimension Analysis — Design System Coverage")
    L.append(f"**Data**: {payload['date']}")
    L.append("")
    L.append("Analise das **dimensoes que o ui_audit.py NAO cobria** — bugs visuais")
    L.append("invisiveis a regex tatico (contraste WCAG, vars BS nao tematizadas,")
    L.append("inconsistencia semantica de headers, etc).")
    L.append("")
    L.append("Este documento eh insumo para a Etapa 2-7 do plano de unificacao.")
    L.append("")

    # ─────────────────────────────────────────────────────────────
    # 1. WCAG dos tokens
    # ─────────────────────────────────────────────────────────────
    L.append("## 1. Tokens auto-validados (WCAG)")
    L.append("")
    L.append("Calcula contraste WCAG entre cada par bg/text que o design system EXIGE.")
    L.append("**FAIL** = abaixo de AA 4.5:1 (texto normal). Tokens com FAIL precisam")
    L.append("ser recalibrados.")
    L.append("")

    fails = [r for r in payload["dimension_1_token_pairs"] if r["status"] == "FAIL"]
    L.append(f"**{len(fails)} pares com FAIL contraste (de {len(payload['dimension_1_token_pairs'])} totais)**")
    L.append("")
    L.append("| Tema | Background | Text | Ratio | Status | Descricao |")
    L.append("|---|---|---|---:|---|---|")
    for r in payload["dimension_1_token_pairs"]:
        ratio = f"{r['ratio']:.2f}" if r["ratio"] is not None else "—"
        emoji = "❌" if r["status"] == "FAIL" else ("✅" if r["status"] == "AAA" else "✓")
        L.append(f"| {r['theme']} | `{r['bg']}` | `{r['text']}` | {ratio} | "
                 f"{emoji} {r['status']} | {r['desc']} |")
    L.append("")
    if fails:
        L.append("### Acao para tokens FAIL:")
        for r in fails:
            L.append(f"- **{r['theme']}**: `{r['bg']}` ({r['bg_value']}) + `{r['text']}` "
                     f"= {r['ratio']:.2f} → recalibrar `{r['bg']}` para escurecer/clarear "
                     f"ate atingir AA 4.5:1")
        L.append("")

    # ─────────────────────────────────────────────────────────────
    # 2-3. BS vars
    # ─────────────────────────────────────────────────────────────
    L.append("## 2. Vars Bootstrap raras / nao tematizadas")
    L.append("")
    L.append("Vars como `--bs-purple`, `--bs-cyan`, `--bs-X-bg-subtle`, `--bs-X-text-emphasis`")
    L.append("usadas em templates ou modulos. **Nao sao tematizadas** pelo design system —")
    L.append("herdam Bootstrap default (cores arbitrarias, podem violar contraste em dark).")
    L.append("")

    by_var: dict[str, list] = defaultdict(list)
    for u in payload["dimension_2_bs_vars"]:
        by_var[u["var"]].append(u)
    L.append(f"**{len(payload['dimension_2_bs_vars'])} usos** em "
             f"{len(set(u['file'] for u in payload['dimension_2_bs_vars']))} arquivos.")
    L.append("")
    L.append("| Var | Ocorrencias | Tipo | Onde |")
    L.append("|---|---:|---|---|")
    for var in sorted(by_var, key=lambda v: -len(by_var[v])):
        usages = by_var[var]
        templates_count = sum(1 for u in usages if u["file_kind"] == "template")
        css_count = sum(1 for u in usages if u["file_kind"] == "css")
        kind = usages[0]["kind"]
        kind_label = "RARA" if kind == "rare_bs_var" else "NAO-TEMATIZADA"
        L.append(f"| `var({var})` | {len(usages)} | {kind_label} | "
                 f"templates={templates_count}, css={css_count} |")
    L.append("")
    L.append("**Acao**: tematizar essas vars no `_design-tokens.css` em ambos os blocos")
    L.append("`[data-bs-theme=light]` e `[data-bs-theme=dark]`, OU bani-las do vocabulario.")
    L.append("")

    # ─────────────────────────────────────────────────────────────
    # 4. Pastel classes
    # ─────────────────────────────────────────────────────────────
    L.append("## 3. Classes Bootstrap pastel (`bg-X-subtle`, `bg-opacity-N`)")
    L.append("")
    L.append("Classes Bootstrap que aplicam cores pastel **nao tematizadas pelo design system**.")
    L.append("No dark mode podem virar tons claros que conflitam com texto branco/escuro herdado.")
    L.append("")
    by_class: dict[str, list] = defaultdict(list)
    for u in payload["dimension_3_pastel"]:
        by_class[u["class"]].append(u)
    L.append(f"**{len(payload['dimension_3_pastel'])} ocorrencias** em "
             f"{len(set(u['file'] for u in payload['dimension_3_pastel']))} arquivos.")
    L.append("")
    L.append("| Classe | Ocorrencias |")
    L.append("|---|---:|")
    for cls in sorted(by_class, key=lambda c: -len(by_class[c])):
        L.append(f"| `{cls}` | {len(by_class[cls])} |")
    L.append("")

    # ─────────────────────────────────────────────────────────────
    # 5. Headers — variantes
    # ─────────────────────────────────────────────────────────────
    L.append("## 4. Headers (modal-header / card-header) — catalogo de variantes")
    L.append("")
    L.append("Quantas variantes visuais coexistem para o mesmo elemento semantico?")
    L.append("Cada signature distinta = 1 variante. **Quanto mais variantes, mais inconsistencia.**")
    L.append("")
    headers = payload["dimension_4_headers"]
    by_kind = defaultdict(lambda: defaultdict(list))
    for h in headers:
        by_kind[h["kind"]][h["signature"]].append(h)

    for kind in sorted(by_kind):
        sigs = by_kind[kind]
        L.append(f"### `{kind}` — {len(sigs)} variantes em "
                 f"{sum(len(v) for v in sigs.values())} ocorrencias")
        L.append("")
        L.append("| Signature | Ocorrencias | Sample |")
        L.append("|---|---:|---|")
        for sig in sorted(sigs, key=lambda s: -len(sigs[s])):
            usages = sigs[sig]
            sample = usages[0]
            sample_loc = f"`{sample['file']}:{sample['line']}`"
            L.append(f"| `{sig}` | {len(usages)} | {sample_loc} |")
        L.append("")

    # ─────────────────────────────────────────────────────────────
    # 6. Style blocks em templates
    # ─────────────────────────────────────────────────────────────
    L.append("## 5. `<style>` blocks em templates")
    L.append("")
    L.append("Convencao DEV: nao usar `<style>` em template — CSS deve viver em `modules/_X.css`.")
    L.append("")
    L.append(f"**{len(payload['dimension_5_style_blocks'])} blocks** em "
             f"{len(set(u['file'] for u in payload['dimension_5_style_blocks']))} templates.")
    L.append("")
    L.append("| Arquivo | Linha | Tamanho | Preview |")
    L.append("|---|---:|---:|---|")
    for u in payload["dimension_5_style_blocks"][:30]:
        L.append(f"| `{u['file']}` | {u['line']} | {u['size_chars']} | "
                 f"{u['preview']} |")
    if len(payload["dimension_5_style_blocks"]) > 30:
        L.append(f"| ... | | | +{len(payload['dimension_5_style_blocks']) - 30} mais |")
    L.append("")

    # ─────────────────────────────────────────────────────────────
    # 7. JS color
    # ─────────────────────────────────────────────────────────────
    L.append("## 6. Cores via JavaScript")
    L.append("")
    L.append("`.style.background = '...'` ou `.style.color = '...'` em JS — bypass total")
    L.append("do design system (visual snapshot pega so estado pos-render).")
    L.append("")
    L.append(f"**{len(payload['dimension_6_js_colors'])} ocorrencias.**")
    L.append("")
    L.append("| Arquivo | Linha | Snippet |")
    L.append("|---|---:|---|")
    for u in payload["dimension_6_js_colors"][:20]:
        L.append(f"| `{u['file']}` | {u['line']} | `{u['snippet']}` |")
    if len(payload["dimension_6_js_colors"]) > 20:
        L.append(f"| ... | | +{len(payload['dimension_6_js_colors']) - 20} mais |")
    L.append("")

    # ─────────────────────────────────────────────────────────────
    # 8. SVG colors
    # ─────────────────────────────────────────────────────────────
    L.append("## 7. SVG inline com cor hardcoded")
    L.append("")
    L.append(f"**{len(payload['dimension_7_svg_colors'])} ocorrencias.**")
    L.append("")
    if payload["dimension_7_svg_colors"]:
        unique_colors = Counter(u["color"] for u in payload["dimension_7_svg_colors"])
        L.append("Cores mais usadas:")
        L.append("")
        for color, n in unique_colors.most_common(10):
            L.append(f"- `{color}`: {n} ocorrencias")
        L.append("")

    # ─────────────────────────────────────────────────────────────
    # 9. Jinja conditional colors
    # ─────────────────────────────────────────────────────────────
    L.append("## 8. Cores condicionais Jinja")
    L.append("")
    L.append("Patterns como `{{ '#XXX' if cond else '#YYY' }}` — cores hardcoded em logica template.")
    L.append("")
    L.append(f"**{len(payload['dimension_8_jinja_colors'])} ocorrencias.**")
    L.append("")
    for u in payload["dimension_8_jinja_colors"][:15]:
        L.append(f"- `{u['file']}:{u['line']}` — `{u['color1']}` ↔ `{u['color2']}`")
    L.append("")

    # ─────────────────────────────────────────────────────────────
    # Sumario priorizado
    # ─────────────────────────────────────────────────────────────
    L.append("## 9. Priorizacao Pareto (alcance da correcao)")
    L.append("")
    L.append("Ordem por **valor / esforco** — comecar pelo topo:")
    L.append("")

    priority = []
    if fails:
        priority.append({
            "rank": 1, "valor": "ALTO", "esforco": "BAIXO",
            "acao": f"Recalibrar {len(fails)} tokens com FAIL contraste",
            "alcance": "Todo modulo que use esses tokens (efeito cascata)",
        })

    rare_count = sum(1 for u in payload["dimension_2_bs_vars"] if u["kind"] == "rare_bs_var")
    untokenized_count = sum(1 for u in payload["dimension_2_bs_vars"] if u["kind"] == "untokenized_bs_var")
    if untokenized_count > 0:
        priority.append({
            "rank": 2, "valor": "ALTO", "esforco": "BAIXO",
            "acao": f"Tematizar {untokenized_count} usos de --bs-X-bg-subtle/text-emphasis no _design-tokens.css",
            "alcance": "Todos templates que usam essas vars",
        })
    if rare_count > 0:
        priority.append({
            "rank": 3, "valor": "MEDIO", "esforco": "MEDIO",
            "acao": f"Banir/substituir {rare_count} usos de --bs-purple/cyan/etc",
            "alcance": "N templates",
        })

    pastel_count = len(payload["dimension_3_pastel"])
    if pastel_count > 0:
        priority.append({
            "rank": 4, "valor": "ALTO", "esforco": "MEDIO",
            "acao": f"Substituir {pastel_count} bg-X-subtle/bg-opacity-N por classe canonical",
            "alcance": "N templates (criar 1-2 classes canonical, codemod massivo)",
        })

    headers_total = sum(len(sigs) for sigs in by_kind.values())
    headers_uses = sum(sum(len(v) for v in sigs.values()) for sigs in by_kind.values())
    if headers_total > 5:
        priority.append({
            "rank": 5, "valor": "ALTO", "esforco": "ALTO",
            "acao": f"Unificar {headers_total} variantes de header em 2-3 canonicas",
            "alcance": f"{headers_uses} ocorrencias em ~{len(set(h['file'] for h in headers))} templates",
        })

    style_blocks_count = len(payload["dimension_5_style_blocks"])
    if style_blocks_count > 0:
        priority.append({
            "rank": 6, "valor": "MEDIO", "esforco": "ALTO",
            "acao": f"Migrar {style_blocks_count} <style> blocks de templates para CSS modulo",
            "alcance": f"{len(set(u['file'] for u in payload['dimension_5_style_blocks']))} templates",
        })

    js_count = len(payload["dimension_6_js_colors"])
    if js_count > 0:
        priority.append({
            "rank": 7, "valor": "BAIXO", "esforco": "MEDIO",
            "acao": f"Substituir {js_count} `.style.background/color =` por toggle de classe",
            "alcance": "Pontos de manipulacao dinamica",
        })

    L.append("| # | Valor | Esforco | Acao | Alcance |")
    L.append("|---:|---|---|---|---|")
    for p in priority:
        L.append(f"| {p['rank']} | {p['valor']} | {p['esforco']} | {p['acao']} | {p['alcance']} |")
    L.append("")

    L.append("## 10. Pos-correcoes — pipeline preventivo")
    L.append("")
    L.append("Para evitar regressao em PRs futuros:")
    L.append("")
    L.append("1. **Lint bloqueador** (pre-commit + CI): rejeitar PR com")
    L.append("   - cor fora do vocabulario fechado (hex, rgb, var nao-canonical)")
    L.append("   - inline `style=color/background` em template")
    L.append("   - `bg-X-subtle | bg-opacity-N` (proibidos pos-unificacao)")
    L.append("   - combinacao bg+text com WCAG ratio < 4.5:1")
    L.append("")
    L.append("2. **Visual analysis com axe-core** (Playwright integration):")
    L.append("   - rodar `axe.run()` em cada pagina capturada")
    L.append("   - reportar violacoes WCAG (cor + outras)")
    L.append("")
    L.append("3. **Politica restritiva no GUIA_COMPONENTES_UI.md**:")
    L.append("   - vocabulario fechado de cores PERMITIDAS")
    L.append("   - lista explicita do que esta BANIDO")
    L.append("   - exemplos de violacoes + correcao")
    L.append("")

    out_path.write_text("\n".join(L), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="UI Dimension Analysis")
    parser.add_argument("--templates-dir", type=Path, default=DEFAULT_TEMPLATES)
    parser.add_argument("--css-dir", type=Path, default=DEFAULT_CSS)
    parser.add_argument("--reports-dir", type=Path, default=DEFAULT_REPORTS)
    args = parser.parse_args()

    args.reports_dir.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()

    print(f"[dim-analysis] Templates: {args.templates_dir}")
    print(f"[dim-analysis] CSS:       {args.css_dir}")

    # ─────────────────────────────────────────
    # 1. Tokens WCAG
    # ─────────────────────────────────────────
    print("\n[dim-analysis] Dimensao 1: WCAG dos tokens")
    tokens = extract_tokens_from_design_tokens()
    pair_results = analyze_token_pairs(tokens)
    fails = [r for r in pair_results if r["status"] == "FAIL"]
    print(f"  - {len(pair_results)} pares analisados, {len(fails)} FAIL")

    # ─────────────────────────────────────────
    # 2-3. BS vars
    # ─────────────────────────────────────────
    print("[dim-analysis] Dimensao 2-3: BS vars raras/nao tematizadas")
    bs_vars_usages = []
    for tpl in iter_files(args.templates_dir, (".html",)):
        bs_vars_usages.extend(find_bs_vars_usage(tpl, "template"))
    for css in iter_files(args.css_dir, (".css",)):
        bs_vars_usages.extend(find_bs_vars_usage(css, "css"))
    print(f"  - {len(bs_vars_usages)} usos")

    # ─────────────────────────────────────────
    # 4. Pastel
    # ─────────────────────────────────────────
    print("[dim-analysis] Dimensao 4: pastel classes")
    pastel = []
    for tpl in iter_files(args.templates_dir, (".html",)):
        pastel.extend(find_pastel_classes(tpl))
    print(f"  - {len(pastel)} ocorrencias")

    # ─────────────────────────────────────────
    # 5. Headers
    # ─────────────────────────────────────────
    print("[dim-analysis] Dimensao 5: headers")
    headers = []
    for tpl in iter_files(args.templates_dir, (".html",)):
        headers.extend(find_header_variants(tpl))
    print(f"  - {len(headers)} headers catalogados")

    # ─────────────────────────────────────────
    # 6. Style blocks
    # ─────────────────────────────────────────
    print("[dim-analysis] Dimensao 6: <style> blocks")
    style_blocks = []
    for tpl in iter_files(args.templates_dir, (".html",)):
        style_blocks.extend(find_style_blocks(tpl))
    print(f"  - {len(style_blocks)} blocos")

    # ─────────────────────────────────────────
    # 7. JS colors (em templates HTML inline + JS files)
    # ─────────────────────────────────────────
    print("[dim-analysis] Dimensao 7: JS colors")
    js_colors = []
    for tpl in iter_files(args.templates_dir, (".html",)):
        js_colors.extend(find_js_color_assignments(tpl))
    js_root = ROOT / "app" / "static" / "js"
    if js_root.exists():
        for js in iter_files(js_root, (".js",)):
            js_colors.extend(find_js_color_assignments(js))
    print(f"  - {len(js_colors)} ocorrencias")

    # ─────────────────────────────────────────
    # 8. SVG inline colors
    # ─────────────────────────────────────────
    print("[dim-analysis] Dimensao 8: SVG inline colors")
    svg_colors = []
    for tpl in iter_files(args.templates_dir, (".html",)):
        svg_colors.extend(find_svg_colors(tpl))
    print(f"  - {len(svg_colors)} ocorrencias")

    # ─────────────────────────────────────────
    # 9. Jinja conditional colors
    # ─────────────────────────────────────────
    print("[dim-analysis] Dimensao 9: Jinja conditional colors")
    jinja_colors = []
    for tpl in iter_files(args.templates_dir, (".html",)):
        jinja_colors.extend(find_jinja_conditional_colors(tpl))
    print(f"  - {len(jinja_colors)} ocorrencias")

    payload = {
        "date": today,
        "dimension_1_token_pairs": pair_results,
        "dimension_2_bs_vars": bs_vars_usages,
        "dimension_3_pastel": pastel,
        "dimension_4_headers": headers,
        "dimension_5_style_blocks": style_blocks,
        "dimension_6_js_colors": js_colors,
        "dimension_7_svg_colors": svg_colors,
        "dimension_8_jinja_colors": jinja_colors,
    }

    json_path = args.reports_dir / f"ui_dimension_analysis_{today}.json"
    md_path = args.reports_dir / f"ui_dimension_analysis_{today}.md"

    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    write_md_report(payload, md_path)

    print(f"\n[dim-analysis] JSON: {json_path}")
    print(f"[dim-analysis] MD:   {md_path}")


if __name__ == "__main__":
    main()
