from __future__ import annotations
import re
from collections import deque
from pathlib import Path
from .findings import Finding
from .text_utils import fenced_lines, resolve_ref

MD_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
PATH_REF = re.compile(r"`?([\w./-]+\.md)`?")  # code-span ou path nu -> .md

def _is_hub(rel: str, tipo: str) -> bool:
    """Nos que PROPAGAM reachability: index declarado OU MOC de-facto por nome."""
    return tipo == "index" or Path(rel).name in ("INDEX.md", "README.md", "CLAUDE.md")

def _is_tool_reachable(rel: str, cfg) -> bool:
    from . import zones
    globs = cfg.raw.get("tool_reachable_globs", [])
    return zones._match_any(rel, globs)

def extract_refs(text: str, file_path: Path, root: Path, managed: set[str]) -> set[str]:
    """Refs de saida -> rel-paths gerenciados. Credita markdown-link E code-span/path,
    pulando linhas fenced (exemplos de codigo nao sao arestas reais).
    Resolucao C7-shared (resolve_ref) + fallback root-relative: um nome nu (`a.md`)
    citado por um hub em subdir (docs/INDEX.md) deve creditar o doc root-level `a.md`
    se a resolucao file-relativa nao bater num doc gerenciado. So credita arestas
    para docs GERENCIADOS, entao o fallback nunca inventa no fora-do-grafo."""
    out: set[str] = set()
    fenced = fenced_lines(text)
    for i, line in enumerate(text.splitlines(), 1):
        if i in fenced:
            continue
        for target in list(MD_LINK.findall(line)) + list(PATH_REF.findall(line)):
            cand = resolve_ref(file_path, target, root)
            if cand is not None:
                _add(out, cand, target, root, managed)
    return out

def _add(out: set[str], cand: Path, target: str, root: Path, managed: set[str]) -> None:
    rel = _rel(cand, root)
    if rel in managed:
        out.add(rel)
        return
    # Fallback root-relative SO p/ nome nu (sem '/', sem './' '../'): citado por hub
    # em subdir, credita o doc root-level. resolve_ref ja trata nomes nus como
    # file-relativos; este fallback cobre o caso topo-de-arvore.
    t = target.split("#")[0].strip()
    if not t or "/" in t:
        return
    alt = (root / t).resolve()
    rel_alt = _rel(alt, root)
    if rel_alt in managed:
        out.add(rel_alt)

def _rel(cand: Path, root: Path) -> str | None:
    try:
        return str(cand.relative_to(root))
    except ValueError:
        return None

def check_reachability(docs: dict[str, dict], cfg, root: Path) -> list[Finding]:
    """C8 global (advisory). docs: rel -> {'tipo': str, 'hub': str|None, 'text': str}.
    Emite C8-ORPHAN (nao alcancavel de CLAUDE.md via hubs), C8-BIDIR (item-9: doc
    declara hub que nao o lista de volta), C8-HUBFILE (hub declarado inexistente).
    Severidade 'report': mede a divida, nao trava commit. Promover a 'block' SO apos
    Ondas 3-4 reduzirem a divida + OK do usuario (spec §8.5)."""
    root = Path(root).resolve()
    managed = set(docs.keys())
    refs = {rel: extract_refs(d["text"], root / rel, root, managed) for rel, d in docs.items()}
    hubs = {rel for rel, d in docs.items() if _is_hub(rel, d.get("tipo", ""))}
    roots = {"CLAUDE.md"} & managed

    # BFS: a fronteira expande SO por hubs + roots
    reached: set[str] = set()
    q = deque(roots)
    while q:
        cur = q.popleft()
        if cur in reached:
            continue
        reached.add(cur)
        if cur in hubs or cur in roots:
            for nxt in refs.get(cur, ()):
                if nxt not in reached:
                    q.append(nxt)

    out: list[Finding] = []
    for rel, d in sorted(docs.items()):
        if rel in roots:
            continue
        if _is_tool_reachable(rel, cfg):
            continue  # reachable-by-tool (skills): fora do grafo de hubs por design
        if rel not in reached:
            out.append(Finding("C8", rel, 1, "orfao: nao alcancavel de CLAUDE.md via hubs", "report"))
        h = d.get("hub")
        if h and h not in ("—", "-") and rel not in hubs:
            if h not in managed:
                out.append(Finding("C8", rel, 1, f"hub declarado inexistente/nao-gerenciado: {h}", "report"))
            elif rel not in refs.get(h, set()):
                out.append(Finding("C8", rel, 1, f"hub {h} nao lista este doc de volta (item-9)", "report"))
    return out
