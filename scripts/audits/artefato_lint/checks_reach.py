from __future__ import annotations
import re
from collections import deque
from pathlib import Path
from .findings import Finding
from .text_utils import fenced_lines, resolve_ref, MD_LINK

PATH_REF = re.compile(r"`?([\w./-]+\.md)`?")  # code-span ou path nu -> .md (especifico do C8)

def _is_hub(rel: str, tipo: str) -> bool:
    """Nos que PROPAGAM reachability: index declarado OU MOC de-facto por nome."""
    return tipo == "index" or Path(rel).name in ("INDEX.md", "README.md", "CLAUDE.md")

def _is_tool_reachable(rel: str, cfg) -> bool:
    from . import zones
    globs = cfg.raw.get("tool_reachable_globs", [])
    return zones._match_any(rel, globs)

def extract_refs(text: str, file_path: Path, root: Path, managed: set[str]) -> set[str]:
    """Refs de saida -> rel-paths gerenciados. Credita markdown-link E code-span/path,
    pulando linhas fenced (exemplos de codigo nao sao arestas reais). Resolucao
    puramente C7-shared via resolve_ref (C8 == C7, sem fallback)."""
    out: set[str] = set()
    fenced = fenced_lines(text)
    for i, line in enumerate(text.splitlines(), 1):
        if i in fenced:
            continue
        for target in list(MD_LINK.findall(line)) + list(PATH_REF.findall(line)):
            cand = resolve_ref(file_path, target, root)
            if cand is not None:
                _add(out, cand, root, managed)
    return out

def _add(out: set[str], cand: Path, root: Path, managed: set[str]) -> None:
    rel = _rel(cand, root)
    if rel in managed:
        out.add(rel)

def _rel(cand: Path, root: Path) -> str | None:
    try:
        return str(cand.relative_to(root))
    except ValueError:
        return None

def check_reachability(docs: dict[str, dict], cfg, root: Path) -> list[Finding]:
    """C8 global. docs: rel -> {'tipo': str, 'hub': str|None, 'text': str}.
    Emite C8-ORPHAN (nao alcancavel de CLAUDE.md via hubs), C8-BIDIR (item-9: doc
    declara hub que nao o lista de volta), C8-HUBFILE (hub declarado inexistente).
    Severidade 'block' (PAD-A Onda 4g, SELAGEM 2026-06-03): apos as Ondas 3-4 zerarem
    a divida (C8 global = 0) + OK do usuario (spec §8.5), C8 foi promovido de 'report'
    a 'block' — orfaos/hubs quebrados agora travam o commit, cumprindo a promessa da
    Onda 1 ('block pos-Onda 3-4'). Auto-skip sob escopo parcial (grafo incompleto)
    permanece no CLI (--skip-reach)."""
    root = Path(root).resolve()
    managed = set(docs.keys())
    refs = {rel: extract_refs(d["text"], root / rel, root, managed) for rel, d in docs.items()}
    hubs = {rel for rel, d in docs.items() if _is_hub(rel, d.get("tipo", ""))}
    roots = set(cfg.raw.get("reach_roots", ["CLAUDE.md"])) & managed

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
            out.append(Finding("C8", rel, 1, "orfao: nao alcancavel de CLAUDE.md via hubs", "block"))
        h = d.get("hub")
        if h and h not in ("—", "-") and rel not in hubs:
            if h not in managed:
                out.append(Finding("C8", rel, 1, f"hub declarado inexistente/nao-gerenciado: {h}", "block"))
            elif rel not in refs.get(h, set()):
                out.append(Finding("C8", rel, 1, f"hub {h} nao lista este doc de volta (item-9)", "block"))
    return out
