#!/usr/bin/env python3
"""Scaffold de artefato conforme PAD-A: nasce com header + secoes obrigatorias do tipo."""
from __future__ import annotations
import argparse, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.audits.artefato_lint import config
from scripts.docs import _doc_meta

def build(tipo, tema, hub, data) -> str:
    cfg = config.load()
    secoes = cfg.required_sections.get(tipo, [])
    header = _doc_meta.build_header(tipo, hub, data, camada="L2", sot_de=tema)
    body = [f"# {tema}", "", "> **Papel:** <1 linha>.  **Abra quando:** <...>", ""]
    for s in secoes:
        if s == "Papel":
            continue
        body += [f"## {s}", "", "<...>", ""]
    return header + "\n".join(body) + "\n"

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tipo", required=True)
    ap.add_argument("--tema", required=True)
    ap.add_argument("--hub", required=True)
    ap.add_argument("--data", default="2026-06-01")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(build(a.tipo, a.tema, a.hub, a.data), encoding="utf-8")
    print(f"criado: {a.out}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
