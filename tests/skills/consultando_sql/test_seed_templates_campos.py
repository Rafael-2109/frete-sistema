"""Valida que os SEED_TEMPLATES (few-shot/atalho do text_to_sql) usam apenas
campos REAIS das tabelas — bug pré-existente descoberto no S2: vários seeds
citavam colunas inexistentes (valor_total_nf, data_emissao, qtd_produzida...),
que executam direto (similaridade>=0.92) ou viram few-shot e ensinam campo errado.

Determinístico: lê SEED_TEMPLATES + schemas JSON. Sem DB/LLM.
"""
import importlib.util
import json
import re
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
_TABLES = _REPO / ".claude/skills/consultando-sql/schemas/tables"

# campos por tabela
FIELDS = {}
for p in _TABLES.glob("*.json"):
    FIELDS[p.stem] = {f["name"].lower() for f in json.load(open(p)).get("fields", [])}


def _load_seed():
    path = _REPO / "app/embeddings/indexers/sql_template_indexer.py"
    spec = importlib.util.spec_from_file_location("sql_template_indexer_mod", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["sql_template_indexer_mod"] = mod
    spec.loader.exec_module(mod)
    return mod.SEED_TEMPLATES


_KW = {
    "select", "from", "where", "group", "by", "order", "having", "limit", "offset",
    "as", "and", "or", "not", "null", "nulls", "first", "last", "is", "in", "on",
    "join", "inner", "left", "right", "outer", "full", "distinct", "case", "when",
    "then", "else", "end", "asc", "desc", "union", "all", "between", "like", "ilike",
    "exists", "count", "sum", "avg", "max", "min", "round", "coalesce", "nullif",
    "cast", "extract", "to_char", "date_trunc", "current_date", "current_timestamp",
    "now", "interval", "month", "year", "day", "week", "true", "false", "numeric",
    "integer", "text", "date", "timestamp", "varchar", "abs", "length",
}


def _strip(sql: str) -> str:
    """Remove literais string ('...') para nao confundir valor com coluna."""
    return re.sub(r"'[^']*'", " ", sql)


def _alias_map(sql: str) -> dict:
    """Mapa alias->tabela (e tabela->tabela) a partir de FROM/JOIN <tabela> [alias]."""
    amap = {}
    for tab, alias in re.findall(r'(?:from|join)\s+([a-z_][a-z0-9_]*)(?:\s+(?:as\s+)?([a-z_][a-z0-9_]*))?', sql, re.I):
        amap[tab.lower()] = tab.lower()
        if alias and alias.lower() not in _KW:
            amap[alias.lower()] = tab.lower()
    return amap


def _out_aliases(sql: str):
    return {m.lower() for m in re.findall(r'\bas\s+([a-z_][a-z0-9_]*)', sql, re.I)}


def test_seed_templates_usam_campos_reais():
    seeds = _load_seed()
    erros = []
    for s in seeds:
        sql = _strip(s["sql_text"])
        amap = _alias_map(sql)
        tabelas = sorted({t for t in amap.values() if t in FIELDS})
        if not tabelas:
            continue
        out_al = _out_aliases(sql)

        # 1) colunas QUALIFICADAS alias.col -> resolve alias -> valida na tabela exata
        for alias, col in re.findall(r'\b([a-z_][a-z0-9_]*)\.([a-z_][a-z0-9_]*)\b', sql, re.I):
            tab = amap.get(alias.lower())
            if tab and col.lower() not in FIELDS[tab]:
                erros.append(f"[{s['question_text'][:38]}] {tab}.{col} NAO existe")

        # 2) colunas NAO-qualificadas: so quando o SEED e single-table (sem ambiguidade)
        if len(tabelas) == 1:
            tb = tabelas[0]
            validos = FIELDS[tb]
            qualificadas = {c.lower() for c in re.findall(r'\.([a-z_][a-z0-9_]*)\b', sql)}
            for tok in re.findall(r"\b([a-z][a-z0-9_]{2,})\b", sql, re.I):
                t = tok.lower()
                if t in _KW or t in out_al or t == tb or t in amap:
                    continue
                if t in qualificadas:
                    continue  # ja tratada no passo 1
                if t not in validos:
                    erros.append(f"[{s['question_text'][:38]}] {tb}.{t} NAO existe (nao-qualificada)")

    msg = "SEED_TEMPLATES com campos inexistentes:\n" + "\n".join(sorted(set(erros)))
    assert not erros, msg
