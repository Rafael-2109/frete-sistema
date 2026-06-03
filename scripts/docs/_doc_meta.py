"""Helpers compartilhados de doc:meta (scaffold + migrador). Sem dependencia do app."""
from __future__ import annotations
import re

def build_header(tipo: str, hub: str, data: str,
                 camada: str = "L2", sot_de: str = "—", superseded_by: str = "—") -> str:
    return (f"<!-- doc:meta\ntipo: {tipo}\ncamada: {camada}\nsot_de: {sot_de}\n"
            f"hub: {hub}\nsuperseded_by: {superseded_by}\natualizado: {data}\n-->\n")

def required_section_stubs(tipo: str, cfg) -> list[str]:
    """Headings minimos honestos por tipo (Papel sai como blockquote, nao heading)."""
    secs = [s for s in cfg.required_sections.get(tipo, []) if s.lower() != "papel"]
    return [f"## {s}" for s in secs]

_H = re.compile(r"^(#{2,3})\s+(.*)$")

def slug(s: str) -> str:
    s = re.sub(r"[^\w\s-]", "", s.lower()).strip()
    return re.sub(r"\s+", "-", s)

def gen_toc(text: str) -> str:
    """Gera '## Indice' a partir de headings H2/H3 (pula linhas fenced e o proprio Indice)."""
    out, in_fence = [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = _H.match(line)
        if not m:
            continue
        depth, title = len(m.group(1)) - 2, m.group(2).strip()
        if re.match(r"(?i)(indice|table of contents|toc)\b", title):
            continue
        out.append(f"{'  ' * depth}- [{title}](#{slug(title)})")
    return "## Indice\n\n" + "\n".join(out) + "\n" if out else ""
