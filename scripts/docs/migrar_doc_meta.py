"""Migrador de doc:meta (PAD-A Onda 4).

Carimbador idempotente: insere bloco <!-- doc:meta --> em docs sem header,
gerando Papel, TOC e stubs de secoes obrigatorias quando necessario.

CLI:
    python migrar_doc_meta.py --scope-root . --paths docs/foo.md --hub docs/INDEX.md
    python migrar_doc_meta.py ... --write   # efetiva gravacao
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
from pathlib import Path

# Garante que o root do projeto esta no path (para uso via `python scripts/docs/migrar_doc_meta.py`)
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.docs import _doc_meta
from scripts.audits.artefato_lint import config as lint_config
from scripts.audits.artefato_lint import checks_struct, checks_content
from scripts.audits.artefato_lint import meta


# ---------------------------------------------------------------------------
# 1. classify
# ---------------------------------------------------------------------------

def classify(rel: str, text: str) -> tuple[str, str]:
    """Retorna (tipo, camada).

    Retorna ("", "") para SKILL.md / frontmatter YAML — sinaliza PULAR.
    A primeira regra que casa vence.
    """
    basename = Path(rel).name

    # SKILL.md ou frontmatter YAML (name: ...) — pular
    if "/SKILL.md" in rel or rel.endswith("/SKILL.md") or basename == "SKILL.md":
        return ("", "")
    if re.match(r"\A---\s*\nname:", text):
        return ("", "")

    # INDEX.md / README.md
    if basename in ("INDEX.md", "README.md"):
        return ("index", "L1")

    # POPs
    if "/pops/" in rel or re.match(r"^POP-", basename):
        return ("how-to", "L2")

    # Fluxos
    if "/fluxos/" in rel or re.match(r"^F\d\d", basename):
        return ("explanation", "L3")

    # Historico / scratch (path checks antes do basename state para maior especificidade)
    if "/HISTORICO/" in rel or "/99-historia/" in rel or re.match(
        r"^PROMPT_PROXIMA", basename
    ):
        return ("scratch", "L3")

    # State / visao-geral
    if "/visao-geral/" in rel or re.match(
        r"(?i)(CHECKPOINT|AUDIT_LOG|^SOT|PENDENCIAS|STATUS)", basename
    ):
        return ("state", "L3")

    # Checklists / runbooks / guias -> procedimento (how-to: so Papel; evita stub Contexto oco)
    if re.search(r"(?i)(CHECKLIST|RUNBOOK|GUIA)", basename):
        return ("how-to", "L2")

    # ADR (D000-titulo.md)
    if re.match(r"^D\d{3}-", basename):
        return ("explanation", "L3")

    # CLAUDE.md de modulo ou raiz
    if re.match(r"app/[^/]+/CLAUDE\.md$", rel) or rel == "CLAUDE.md":
        return ("explanation", "L1")

    # references — raiz ou subpastas conhecidas
    if rel.startswith(".claude/references/"):
        rest = rel[len(".claude/references/"):]
        # raiz de references (sem subdir) ou em modelos/odoo/negocio
        if "/" not in rest or rest.startswith(("modelos/", "odoo/", "negocio/")):
            return ("reference", "L2")

    # default
    return ("explanation", "L3")


# ---------------------------------------------------------------------------
# 2. _build_candidate
# ---------------------------------------------------------------------------

def _build_candidate(
    rel: str,
    text: str,
    tipo: str,
    camada: str,
    hub: str,
    data: str,
    cfg,
) -> str:
    """Monta o texto com header doc:meta, Papel, TOC e stubs."""
    header = _doc_meta.build_header(tipo, hub, data, camada=camada)

    # scratch: so header + texto (sem Papel/TOC/stubs)
    if tipo == "scratch":
        result = header + text
        if not result.endswith("\n"):
            result += "\n"
        return result

    # --- localizar H1 ---
    lines = text.splitlines()
    h1_idx = None
    for i, line in enumerate(lines):
        if line.startswith("# "):
            h1_idx = i
            break

    if h1_idx is not None:
        title = lines[h1_idx][2:].strip()
    else:
        title = Path(rel).stem

    # --- Papel ---
    papel_str = f"> **Papel:** {title}."
    has_papel = bool(re.search(r"\*\*\s*papel\b", text, re.I))

    # --- stubs de secoes faltantes ---
    def _norm(s: str) -> str:
        import unicodedata
        s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().strip()
        return re.sub(r"\s+", " ", s)

    existing_headings = {_norm(h) for h in re.findall(r"^#{1,6}\s+(.*)$", text, re.M)}
    stub_headings = _doc_meta.required_section_stubs(tipo, cfg)
    stubs_to_add = []
    for stub_h in stub_headings:
        heading_text = stub_h[3:].strip()  # remove "## "
        if _norm(heading_text) not in existing_headings:
            stubs_to_add.append(
                f"{stub_h}\n\n_A completar (PAD-A Onda 4)._\n"
            )

    # --- reconstruir corpo ---
    if h1_idx is not None:
        before_h1 = lines[:h1_idx]
        h1_line = lines[h1_idx]
        after_h1 = lines[h1_idx + 1:]
    else:
        before_h1 = []
        h1_line = None
        after_h1 = lines

    # montar corpo provisorio para TOC (com Papel inserido)
    corpo_parts: list[str] = []
    if h1_line is not None:
        corpo_parts.append(h1_line)
    if not has_papel:
        corpo_parts.append("")
        corpo_parts.append(papel_str)
    corpo_parts.extend(after_h1)
    # adicionar stubs ao fim provisoriamente para TOC incluir
    for stub in stubs_to_add:
        corpo_parts.append("")
        corpo_parts.extend(stub.splitlines())

    corpo_provisorio = "\n".join(corpo_parts)

    # --- TOC ---
    toc_str = ""
    if tipo != "index":
        total_lines = len(header.splitlines()) + len(corpo_provisorio.splitlines())
        has_toc = bool(
            re.search(r"(?im)^#{1,3}\s*(indice|table of contents|toc)\b", corpo_provisorio)
        )
        if total_lines > cfg.toc_min_lines and not has_toc:
            toc_str = _doc_meta.gen_toc(corpo_provisorio)

    # --- montagem final do corpo ---
    final_parts: list[str] = []

    if before_h1:
        final_parts.extend(before_h1)

    if h1_line is not None:
        final_parts.append(h1_line)

    if not has_papel:
        final_parts.append("")
        final_parts.append(papel_str)

    if toc_str:
        final_parts.append("")
        final_parts.append(toc_str.rstrip())

    if after_h1:
        final_parts.extend(after_h1)

    for stub in stubs_to_add:
        final_parts.append("")
        final_parts.extend(stub.splitlines())

    corpo_final = "\n".join(final_parts)

    result = header + corpo_final
    # garantir exatamente 1 \n final
    result = result.rstrip("\n") + "\n"
    return result


# ---------------------------------------------------------------------------
# 3. run
# ---------------------------------------------------------------------------

def run(
    scope_root,
    paths: list[str],
    hub: str,
    write: bool = False,
    data: str = "2026-06-02",
    tipo_override: str | None = None,
    camada_override: str | None = None,
) -> int:
    cfg = lint_config.load()
    scope_root = Path(scope_root)

    for rel in paths:
        p = scope_root / rel
        text = p.read_text(encoding="utf-8")

        # idempotencia: ja tem header -> pular
        if meta.parse_doc(text).found:
            print(f"SKIP {rel} (ja tem header)")
            continue

        tipo, camada = classify(rel, text)
        if tipo == "":
            print(f"SKIP {rel} (SKILL/yaml)")
            continue
        if tipo_override:
            tipo = tipo_override
            if camada_override:
                camada = camada_override

        cand = _build_candidate(rel, text, tipo, camada, hub, data, cfg)

        if not write:
            # DRY-RUN: escreve em tempfile irmao, roda lint, descarta
            tmp_path_obj = None
            findings = []
            try:
                with tempfile.NamedTemporaryFile(
                    dir=p.parent,
                    suffix=".md",
                    delete=False,
                    mode="w",
                    encoding="utf-8",
                ) as tmp_f:
                    tmp_f.write(cand)
                    tmp_path_obj = Path(tmp_f.name)

                findings = (
                    checks_struct.check_file(tmp_path_obj, scope_root, cfg)
                    + checks_content.check_file(tmp_path_obj, scope_root, cfg)
                )
            finally:
                if tmp_path_obj and tmp_path_obj.exists():
                    os.unlink(tmp_path_obj)

            blockers = [(f.code, f.severity) for f in findings if f.severity == "block"]
            report_only = [(f.code, f.severity) for f in findings if f.severity == "report"]
            status = blockers if blockers else "VERDE"
            print(
                f"{rel} -> tipo={tipo} camada={camada} | residual: {status}"
            )
            if report_only:
                print(f"  report-only: {report_only}")
        else:
            # WRITE
            p.write_text(cand, encoding="utf-8")
            print(f"WRITE {rel} -> {tipo}")

    return 0


# ---------------------------------------------------------------------------
# 4. CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migrador doc:meta — carimba docs sem header (PAD-A Onda 4)."
    )
    parser.add_argument("--scope-root", default=".", help="Raiz do escopo (default: .)")
    parser.add_argument("--paths", nargs="+", required=True, help="Caminhos relativos dos docs")
    parser.add_argument("--hub", required=True, help="Caminho relativo do hub (INDEX.md)")
    parser.add_argument(
        "--write", action="store_true", help="Efetivar gravacao (ausente = dry-run)"
    )
    parser.add_argument("--data", default="2026-06-02", help="Data do carimbo (YYYY-MM-DD)")
    parser.add_argument("--tipo", default=None, help="Forca o tipo (override do classify) — p/ review de cluster")
    parser.add_argument("--camada", default=None, help="Forca a camada (L1|L2|L3) — usado com --tipo")
    args = parser.parse_args()

    run(
        scope_root=args.scope_root,
        paths=args.paths,
        hub=args.hub,
        write=args.write,
        data=args.data,
        tipo_override=args.tipo,
        camada_override=args.camada,
    )


if __name__ == "__main__":
    main()
