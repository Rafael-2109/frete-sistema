"""Testes determinísticos do gerador de schemas — subsistema S0 (idempotência).

Cobrem a CAUSA RAIZ provada no Passo 0 (ver MASTER text-to-sql): a serialização
iterava coleções que em SQLAlchemy são `set` — `table.indexes`,
`table.constraints` e `col.foreign_keys` — cuja ordem de iteração varia entre
processos Python. Resultado: 163/304 `tables/*.json` mudavam entre duas
execuções SEM mudança de modelo, poluindo o git. `catalog.json`/
`relationships.json` já eram estáveis (iteram `sorted(...)`).

O fix torna a serialização canônica (ordenação estável) + grava write-if-changed
(não reescreve conteúdo idêntico).

Invariante 6 do MASTER: pytest determinístico, SEM evals LLM, SEM create_app/DB.
Usa objetos `Table` SQLAlchemy sintéticos — rápido e isolado.
"""
import importlib.util
import json
import sys
from pathlib import Path

from sqlalchemy import (
    Column,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    UniqueConstraint,
)

_REPO = Path(__file__).resolve().parents[3]
_SCRIPT = _REPO / ".claude/skills/consultando-sql/scripts/generate_schemas.py"


def _load():
    spec = importlib.util.spec_from_file_location("generate_schemas_mod", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["generate_schemas_mod"] = mod
    spec.loader.exec_module(mod)
    return mod


gs = _load()


# ---------------------------------------------------------------------------
# helpers de construção de Table sintético
# ---------------------------------------------------------------------------

def _tabela_com_indices(nomes_indices):
    """Tabela com 1 índice por nome, TODOS na coluna 'a' (columns idêntico ->
    o discriminador de ordenação é o nome)."""
    md = MetaData()
    t = Table(
        "tbl_idx",
        md,
        Column("id", Integer, primary_key=True),
        Column("a", String(10)),
        Column("b", String(10)),
    )
    for n in nomes_indices:
        Index(n, t.c.a)
    return t


# ---------------------------------------------------------------------------
# CAUSA RAIZ: indices (table.indexes é set)
# ---------------------------------------------------------------------------

def test_indices_saem_ordenados_por_nome():
    # 16 nomes embaralhados. Sem ordenação canônica, seguiriam a ordem
    # imprevisível de iteração do set -> probabilidade ínfima (1/16!) de
    # saírem ordenados por acaso. Com o fix, sempre ordenados.
    nomes = [f"ix_{c}" for c in "ztmbyxcwdvfushrg"]  # 16 chars distintos
    t = _tabela_com_indices(nomes)
    schema = gs.extract_table_schema("tbl_idx", t)
    got = [i["name"] for i in schema["indices"]]
    assert got == sorted(nomes), f"indices não-canônicos: {got}"


def test_indices_invariantes_a_ordem_de_definicao():
    """Duas tabelas idênticas, índices definidos em ordem oposta -> mesma saída."""
    nomes = [f"ix_{c}" for c in "ztmbyxcw"]
    s1 = gs.extract_table_schema("tbl_idx", _tabela_com_indices(nomes))
    s2 = gs.extract_table_schema("tbl_idx", _tabela_com_indices(list(reversed(nomes))))
    assert s1["indices"] == s2["indices"]


# ---------------------------------------------------------------------------
# DEFENSIVO: unique_constraints (table.constraints é set)
# ---------------------------------------------------------------------------

def test_unique_constraints_ordenadas():
    md = MetaData()
    t = Table(
        "tbl_uc",
        md,
        Column("id", Integer, primary_key=True),
        Column("w", String(10)),
        Column("x", String(10)),
        Column("y", String(10)),
        Column("z", String(10)),
        UniqueConstraint("z", "y", name="uq_zy"),
        UniqueConstraint("x", "w", name="uq_xw"),
        UniqueConstraint("y", "z", name="uq_yz"),
        UniqueConstraint("w", "x", name="uq_wx"),
    )
    schema = gs.extract_table_schema("tbl_uc", t)
    ucs = schema["unique_constraints"]
    assert ucs == sorted(ucs), f"unique_constraints não-canônicas: {ucs}"


# ---------------------------------------------------------------------------
# DEFENSIVO: foreign_keys deterministicamente estáveis entre chamadas
# ---------------------------------------------------------------------------

def test_foreign_keys_estaveis():
    md = MetaData()
    Table("parent", md, Column("id", Integer, primary_key=True))
    t = Table(
        "tbl_fk",
        md,
        Column("id", Integer, primary_key=True),
        Column("z_id", Integer, ForeignKey("parent.id")),
        Column("a_id", Integer, ForeignKey("parent.id")),
    )
    s1 = gs.extract_table_schema("tbl_fk", t)
    s2 = gs.extract_table_schema("tbl_fk", t)
    assert s1.get("foreign_keys") == s2.get("foreign_keys")


# ---------------------------------------------------------------------------
# relationships ordenadas canonicamente
# ---------------------------------------------------------------------------

def test_relationships_ordenadas_canonicamente():
    md = MetaData()
    Table("parent", md, Column("id", Integer, primary_key=True))
    # FKs em colunas fora de ordem alfabética (z_id antes de a_id)
    Table(
        "child",
        md,
        Column("id", Integer, primary_key=True),
        Column("z_id", Integer, ForeignKey("parent.id")),
        Column("a_id", Integer, ForeignKey("parent.id")),
    )
    rels = gs.extract_relationships(md)
    keys = [
        (r["from_table"], r["from_column"], r["to_table"], r["to_column"])
        for r in rels
    ]
    assert keys == sorted(keys), f"relationships não-canônicas: {keys}"


# ---------------------------------------------------------------------------
# _dump_canonical: serialização estável + newline final
# ---------------------------------------------------------------------------

def test_dump_canonical_estavel_com_newline():
    obj = {"name": "tbl", "description": "x", "fields": [{"name": "a"}, {"name": "b"}]}
    s1 = gs._dump_canonical(obj)
    s2 = gs._dump_canonical(obj)
    assert s1 == s2
    assert s1.endswith("\n"), "canonical dump deve terminar com newline"
    # round-trip válido
    assert json.loads(s1) == obj


def test_dump_canonical_preserva_ordem_de_chaves():
    # NÃO usar sort_keys global (decisão 4): preserva ordem de inserção/coluna.
    obj = {"zeta": 1, "alpha": 2}
    s = gs._dump_canonical(obj)
    assert s.index('"zeta"') < s.index('"alpha"')


# ---------------------------------------------------------------------------
# _write_if_changed: idempotência de escrita
# ---------------------------------------------------------------------------

def test_write_if_changed(tmp_path):
    p = tmp_path / "x.json"
    assert gs._write_if_changed(str(p), "conteudo\n") is True  # criou
    assert p.read_text(encoding="utf-8") == "conteudo\n"
    assert gs._write_if_changed(str(p), "conteudo\n") is False  # inalterado
    assert gs._write_if_changed(str(p), "novo\n") is True  # mudou
    assert p.read_text(encoding="utf-8") == "novo\n"


def test_write_if_changed_nao_toca_arquivo_identico(tmp_path):
    p = tmp_path / "y.json"
    p.write_text("igual\n", encoding="utf-8")
    mtime_antes = p.stat().st_mtime_ns
    changed = gs._write_if_changed(str(p), "igual\n")
    assert changed is False
    assert p.stat().st_mtime_ns == mtime_antes  # não reescreveu


# ---------------------------------------------------------------------------
# idempotência composta: schema serializado é byte-idêntico entre chamadas
# ---------------------------------------------------------------------------

def test_schema_tabela_idempotente_serializado():
    nomes = [f"ix_{c}" for c in "cbazy"]
    s1 = gs.extract_table_schema("tbl_idx", _tabela_com_indices(nomes))
    s2 = gs.extract_table_schema("tbl_idx", _tabela_com_indices(nomes))
    assert gs._dump_canonical(s1) == gs._dump_canonical(s2)


# ---------------------------------------------------------------------------
# Órfãos: detecção + salvaguarda de remoção (decisão do usuário 2026-06-07)
# ---------------------------------------------------------------------------

def test_find_orphan_schemas(tmp_path):
    d = tmp_path / "tables"
    d.mkdir()
    (d / "viva.json").write_text("{}", encoding="utf-8")
    (d / "orfa.json").write_text("{}", encoding="utf-8")
    (d / "naojson.txt").write_text("x", encoding="utf-8")  # ignorado
    assert gs._find_orphan_schemas(str(d), {"viva"}) == ["orfa"]


def test_find_orphan_schemas_dir_inexistente(tmp_path):
    assert gs._find_orphan_schemas(str(tmp_path / "nao_existe"), {"x"}) == []


def test_resolve_orphans_import_parcial_nunca_apaga():
    # GATE S0: import parcial NUNCA apaga, mesmo com --prune-orphans.
    assert gs._resolve_orphans_to_delete(["a", "b"], import_complete=False, do_prune=True) == []


def test_resolve_orphans_automatico_nunca_apaga():
    # Fluxo automático/hook (sem flag) NUNCA apaga, mesmo com import completo.
    assert gs._resolve_orphans_to_delete(["a", "b"], import_complete=True, do_prune=False) == []


def test_resolve_orphans_apaga_so_com_flag_e_import_completo():
    assert gs._resolve_orphans_to_delete(
        ["a", "b"], import_complete=True, do_prune=True
    ) == ["a", "b"]
