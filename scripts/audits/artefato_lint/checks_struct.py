from __future__ import annotations
import re
from pathlib import Path
from unicodedata import normalize
from .findings import Finding
from . import meta as meta_mod
from .text_utils import fenced_lines, resolve_ref

MD_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
HEADING = re.compile(r"^#{1,6}\s+(.*)$", re.M)
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PAPEL_BLOCKQUOTE = re.compile(r"\*\*\s*papel\b", re.IGNORECASE)

def _norm(s: str) -> str:
    s = normalize("NFKD", s).encode("ascii", "ignore").decode().lower().strip()
    return re.sub(r"\s+", " ", s)

def check_file(path: Path, root: Path, cfg) -> list[Finding]:
    rel = str(Path(path).resolve().relative_to(Path(root).resolve()))
    text = Path(path).read_text(encoding="utf-8")
    out: list[Finding] = []
    m = meta_mod.parse_doc(text)
    # C1 header
    if not m.found:
        out.append(Finding("C1", rel, 1, "header doc:meta ausente", "block"))
        return out
    tipo = m.fields.get("tipo", "")
    if tipo not in cfg.valid_tipos and m.source != "yaml":
        out.append(Finding("C1", rel, 1, f"tipo invalido: {tipo!r}", "block"))
    if m.fields.get("camada") not in cfg.valid_camadas and m.source != "yaml":
        out.append(Finding("C1", rel, 1, "camada ausente/invalida", "block"))
    if not DATE.match(m.fields.get("atualizado", "")) and m.source != "yaml":
        out.append(Finding("C1", rel, 1, "atualizado ausente/invalida (YYYY-MM-DD)", "block"))
    # C2 sot_de
    if "sot_de" not in m.fields and m.source != "yaml":
        out.append(Finding("C2", rel, 1, "sot_de ausente (tema ou '—')", "block"))
    # C3 hub existe
    hub = m.fields.get("hub", "")
    if hub and hub not in ("—", "-"):
        if not (Path(root) / hub).exists():
            out.append(Finding("C3", rel, 1, f"hub inexistente: {hub}", "block"))
    elif m.source != "yaml":
        out.append(Finding("C3", rel, 1, "hub ausente", "block"))
    # C5 secoes por tipo
    headings = {_norm(h) for h in HEADING.findall(text)}
    for req in cfg.required_sections.get(tipo, []):
        # "Papel" e convencao de blockquote (`> **Papel:** ...`), nao heading.
        if _norm(req) == "papel":
            present = bool(PAPEL_BLOCKQUOTE.search(text))
        else:
            present = _norm(req) in headings
        if not present:
            out.append(Finding("C5", rel, 1, f"secao obrigatoria ausente p/ {tipo}: {req}", "block"))
    # C6 TOC se >100 linhas
    nlines = text.count("\n") + 1
    if nlines > cfg.toc_min_lines and not re.search(r"(?im)^#{1,3}\s*(indice|table of contents|toc)\b", text):
        out.append(Finding("C6", rel, 1, f"arquivo {nlines} linhas sem TOC", "block"))
    # C7 link-rot (apenas links relativos a arquivos .md/.py/dir)
    # Resolution rule:
    #   - links starting with './' or '../' OR containing no '/' → relative to FILE's directory
    #   - links containing '/' but NOT starting with '.' → relative to ROOT
    fenced = fenced_lines(text)
    for i, line in enumerate(text.splitlines(), 1):
        if i in fenced:
            continue  # links em exemplos de codigo (``` ```) nao sao referencias reais
        for target in MD_LINK.findall(line):
            t = target.split("#")[0].strip()
            cand = resolve_ref(Path(path), target, Path(root))
            if cand is None:
                continue
            if not cand.exists():
                out.append(Finding("C7", rel, i, f"link morto: {t}", "block"))
    # hub so ponteiros
    if tipo == "index":
        prose = _prose_block_lines(text)
        if prose > cfg.hub_max_prose_lines:
            out.append(Finding("HUB", rel, 1, f"hub com {prose} linhas de prosa nao-ponteiro (>{cfg.hub_max_prose_lines})", "block"))
    return out

def _prose_block_lines(text: str) -> int:
    """Maior bloco contiguo de linhas que nao sejam ponteiro/heading/meta/branco."""
    best = cur = 0
    in_meta = False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("<!--"): in_meta = True
        if in_meta:
            if "-->" in s: in_meta = False
            continue
        is_pointer = s.startswith(("-", "*", "#", ">", "|")) or s == "" or bool(MD_LINK.search(s))
        cur = 0 if is_pointer else cur + 1
        best = max(best, cur)
    return best
