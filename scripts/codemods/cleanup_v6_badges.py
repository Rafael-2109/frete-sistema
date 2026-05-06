#!/usr/bin/env python3
"""
Cleanup V6 — remove `text-white|text-dark|text-light|text-black` redundante de
elementos `badge bg-X` em templates.

Por que e idempotente (visual identico antes/depois):
  - components/_badges.css linhas 53-91 definem --_badge-color por bg-* class
  - base/_bootstrap-overrides.css linhas 675-687 forcam color: hsl(0 0% 10%)
    em badge bg-warning (em ambos os temas)
  - base/_bootstrap-overrides.css linhas 298-300 escopam --bs-white-rgb para
    escuro em badge bg-primary (resolvendo branco-em-amber)

Logo classes text-* em badge bg-* sao SEMPRE redundantes ou contra-producentes
(quando contradiz a API custom property).

Whitelist (NAO remover):
  - Elementos que NAO sao badge (ex: text-dark em <p> ou <h*>)
  - text-* fora de class (ex: em data-* ou comentario)
  - text-dark em .bg-warning quando usado em ALERTAS (.bg-warning sozinho fora
    de badge precisa do contraste manual). Cobertura: regex so age dentro de
    elementos com class contendo "badge".

Uso:
  python scripts/codemods/cleanup_v6_badges.py                # dry-run (default)
  python scripts/codemods/cleanup_v6_badges.py --apply        # aplica mudancas
  python scripts/codemods/cleanup_v6_badges.py --templates-dir app/templates/hora

Saida:
  exit 0 → OK
  exit 1 → erro
"""

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TEMPLATES = ROOT / "app" / "templates"

# Captura class="..." que contem "badge" + "text-(white|dark|light|black)"
# Usa lookahead para preservar o resto da class string.
# Regex multi-step:
#   1. Match class="..." que contem 'badge'
#   2. Dentro dela, remove ' text-(white|dark|light|black)' (com espaco antes)
#   ou 'text-(...)' no inicio (sem espaco)

# Pattern busca atributo class= com badge dentro
RE_CLASS_WITH_BADGE = re.compile(
    r'(class\s*=\s*"([^"]*\bbadge\b[^"]*)")',
    re.DOTALL,
)

# Pattern para remover text-X dentro do conteudo da classe
RE_TEXT_REDUNDANT = re.compile(
    r'\s+text-(white|dark|light|black)\b'
    r'|^text-(white|dark|light|black)\b\s*'
    r'|\btext-(white|dark|light|black)\b\s+',
)


def cleanup_class_value(class_value: str) -> tuple[str, list[str]]:
    """Remove text-X redundantes do valor de class. Retorna (novo_valor, removidos)."""
    removed = []

    def _replace(match: re.Match) -> str:
        # Captura qual variante (white/dark/light/black) e registra
        groups = match.groups()
        kind = next((g for g in groups if g), None)
        if kind:
            removed.append(f"text-{kind}")
        # Substituir por espaco simples (preserva separacao com proxima classe)
        return " "

    new_value = RE_TEXT_REDUNDANT.sub(_replace, class_value)
    # Normalizar espacos multiplos
    new_value = re.sub(r"\s+", " ", new_value).strip()
    return new_value, removed


def process_file(path: Path, apply: bool) -> tuple[int, list[dict]]:
    """Processa um template. Retorna (n_replacements, list_of_changes)."""
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"[codemod] ERRO lendo {path}: {e}", file=sys.stderr)
        return 0, []

    changes = []
    n_replacements = 0

    def _process_class_attr(match: re.Match) -> str:
        nonlocal n_replacements
        full_attr = match.group(1)  # class="..."
        class_value = match.group(2)  # ...

        new_value, removed = cleanup_class_value(class_value)

        if not removed:
            return full_attr  # nada mudou

        n_replacements += len(removed)
        line_num = text[:match.start()].count("\n") + 1
        changes.append({
            "line": line_num,
            "before": class_value[:120],
            "after": new_value[:120],
            "removed": removed,
        })
        return f'class="{new_value}"'

    new_text = RE_CLASS_WITH_BADGE.sub(_process_class_attr, text)

    if apply and n_replacements > 0:
        path.write_text(new_text, encoding="utf-8")

    return n_replacements, changes


def main():
    parser = argparse.ArgumentParser(description="Cleanup V6 — text-* redundante em badges")
    parser.add_argument("--apply", action="store_true",
                        help="Aplica mudancas (default: dry-run)")
    parser.add_argument("--templates-dir", type=Path, default=DEFAULT_TEMPLATES,
                        help="Diretorio de templates (default: app/templates)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Mostra cada mudanca")
    args = parser.parse_args()

    if not args.templates_dir.exists():
        print(f"[codemod] ERRO: {args.templates_dir} nao existe", file=sys.stderr)
        sys.exit(1)

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"[codemod] Modo: {mode}")
    print(f"[codemod] Templates: {args.templates_dir}")

    total_replacements = 0
    files_changed = 0
    by_kind = Counter()

    for tpl_path in sorted(args.templates_dir.rglob("*.html")):
        n, changes = process_file(tpl_path, args.apply)
        if n > 0:
            files_changed += 1
            total_replacements += n
            rel = tpl_path.relative_to(ROOT)
            for ch in changes:
                for kind in ch["removed"]:
                    by_kind[kind] += 1
            if args.verbose:
                print(f"\n  {rel} ({n} mudancas)")
                for ch in changes:
                    print(f"    L{ch['line']}: -{','.join(ch['removed'])}")
                    if len(ch["before"]) < 100:
                        print(f"      {ch['before']!r}")
                        print(f"   -> {ch['after']!r}")

    print(f"\n[codemod] Files affected: {files_changed}")
    print(f"[codemod] Total removals:  {total_replacements}")
    print(f"[codemod] Por tipo:")
    for kind, n in by_kind.most_common():
        print(f"  {kind:15} {n:>5}")

    if not args.apply:
        print(f"\n[codemod] DRY-RUN: nada foi salvo. Use --apply para aplicar.")
    else:
        print(f"\n[codemod] APPLIED: {files_changed} files modificados.")
        print(f"[codemod] Validar com:")
        print(f"  python scripts/audits/ui_audit_regression.py")
        print(f"  python tests/visual/capture.py --target current && python tests/visual/compare.py")

    sys.exit(0)


if __name__ == "__main__":
    main()
