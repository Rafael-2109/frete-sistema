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
    # D1 glossario check
    out += check_glossario(path, root, cfg)
    return out


GLOSSARIO_REL = ".claude/references/GLOSSARIO.md"
# linha de tabela markdown: | conceito | canonico | banidos |
_TABLE_ROW = re.compile(r"^\s*\|(.+)\|(.+)\|(.+)\|\s*$")


def _load_glossario(root: Path) -> dict[str, str]:
    """Le a tabela do GLOSSARIO.md -> {termo_banido_lower: termo_canonico}.
    Coluna 3 ('Banidos') = lista separada por virgula; '—'/'-'/vazio = sem banidos."""
    g: dict[str, str] = {}
    p = Path(root) / GLOSSARIO_REL
    if not p.exists():
        return g
    for line in p.read_text(encoding="utf-8").splitlines():
        m = _TABLE_ROW.match(line)
        if not m:
            continue
        canonico = m.group(2).strip()
        banidos_raw = m.group(3).strip()
        # pula a linha de cabecalho e a linha separadora (---)
        if canonico.lower() in ("termo canonico", "") or set(canonico) <= set("-: "):
            continue
        if banidos_raw in ("—", "-", ""):
            continue
        for b in banidos_raw.split(","):
            b = b.strip().lower()
            if b and b not in ("—", "-"):
                g[b] = canonico
    return g


def check_glossario(path: Path, root: Path, cfg, glossario: dict[str, str] | None = None) -> list[Finding]:
    """D1: uso de termo nao-canonico (banido pelo GLOSSARIO) em doc reference.
    Severidade 'report' na Onda 0 (advisory) — sinonimos sao FP-prone ate calibracao
    da Onda 2. O proprio GLOSSARIO.md e pulado (ele DEFINE os termos, nao se auto-acusa)."""
    rel = str(Path(path).resolve().relative_to(Path(root).resolve()))
    text = Path(path).read_text(encoding="utf-8")
    if meta_mod.parse_doc(text).fields.get("tipo", "") != "reference":
        return []
    if Path(path).name == "GLOSSARIO.md":
        return []
    if glossario is None:
        glossario = _load_glossario(root)
    if not glossario:
        return []
    out: list[Finding] = []
    body = _body(text)
    for i, line in enumerate(body.splitlines(), 1):
        ll = line.lower()
        for banido, canonico in glossario.items():
            if re.search(rf"\b{re.escape(banido)}\b", ll):
                out.append(Finding("D1", rel, i, f"termo nao-canonico {banido!r} — use {canonico!r}", "report"))
    return out
