from __future__ import annotations
import json, re
from pathlib import Path
from .findings import Finding
from . import meta as meta_mod

TABLE_FIELD = re.compile(r"\b([A-Z][a-zA-Z_]+)\.([a-z_][a-z0-9_]+)\b")  # Modelo.campo

def _body(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)

def check_file(path: Path, root: Path, cfg) -> list[Finding]:
    rel = str(Path(path).resolve().relative_to(Path(root).resolve()))
    text = Path(path).read_text(encoding="utf-8")
    tipo = meta_mod.parse_doc(text).fields.get("tipo", "")
    body = _body(text)
    out: list[Finding] = []
    # B5 markers proibidos (so em reference)
    if tipo == "reference":
        for i, line in enumerate(body.splitlines(), 1):
            for pat in cfg.forbidden_markers_reference:
                if re.search(pat, line):
                    out.append(Finding("B5", rel, i, f"marker proibido em reference: /{pat}/", "block"))
    # D4 hedge/time-sensitive (so em reference)
    if tipo == "reference":
        for i, line in enumerate(body.splitlines(), 1):
            ll = line.lower()
            for w in cfg.banned_hedge + cfg.banned_time_sensitive:
                if re.search(rf"\b{re.escape(w)}\b", ll):
                    out.append(Finding("D4", rel, i, f"termo vago/time-sensitive em reference: {w!r}", "block"))
    # D2 citacao em reference
    if tipo == "reference":
        if not re.search(r"(?im)^#{1,4}\s*fontes\b", text) and "FONTE:" not in text:
            out.append(Finding("D2", rel, 1, "reference sem '## Fontes' nem 'FONTE:'", "block"))
    # D3 acuracia de campos vs schema JSON
    sd = Path(root) / cfg.schemas_tables_dir
    if sd.exists():
        for i, line in enumerate(body.splitlines(), 1):
            for modelo, campo in TABLE_FIELD.findall(line):
                tbl = sd / f"{modelo.lower()}.json"
                if tbl.exists():
                    cols = {c.get("name") for c in json.loads(tbl.read_text()).get("fields", [])}
                    if campo not in cols:
                        out.append(Finding("D3", rel, i, f"{modelo}.{campo} nao existe no schema {tbl.name}", "block"))
    # D1 glossario fica em check separado (precisa do GLOSSARIO.md — Task 12); placeholder de interface:
    return out
