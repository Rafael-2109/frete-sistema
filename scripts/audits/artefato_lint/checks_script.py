from __future__ import annotations
import re
from pathlib import Path
from .findings import Finding
from . import meta as meta_mod

def check_file(path: Path, root: Path, cfg, index_basenames: set[str]) -> list[Finding]:
    rel = str(Path(path).resolve().relative_to(Path(root).resolve()))
    name = Path(path).name
    out: list[Finding] = []
    if re.search(cfg.id_hardcoded_regex, name):
        out.append(Finding("SC-ID", rel, 1, f"ID de objeto no nome do script: {name}", "block"))
    text = Path(path).read_text(encoding="utf-8")
    m = meta_mod.parse_script(text)
    if not ({"etapa", "doc-dono"} <= set(m.fields)):
        out.append(Finding("SC-HEADER", rel, 1, "header de script ausente (# etapa / # doc-dono / # hub)", "block"))
    if name not in index_basenames:
        out.append(Finding("SC-ORFAO", rel, 1, "script nao indexado em nenhum INDEX/MAPA da zona", "block"))
    return out

def collect_index_basenames(root: Path, cfg) -> set[str]:
    """Coleta basenames .py citados em qualquer INDEX.md/MAPA_SCRIPTS.md das zonas operacionais."""
    names: set[str] = set()
    for g in cfg.operational_script_globs:
        base = Path(root) / g.split("**")[0]
        for idx in list(base.rglob("INDEX.md")) + list(base.rglob("MAPA_SCRIPTS.md")):
            for mref in re.findall(r"[\w./-]+\.py", idx.read_text(encoding="utf-8")):
                names.add(Path(mref).name)
    return names
