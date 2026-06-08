"""Testes determinísticos S1 — key_fields por relevância + domínio no catálogo.

Subsistema S1 (progressive disclosure), achados N2 (key_fields = lixo: 3 primeiras
colunas) e dominio ausente. Ver MASTER text-to-sql.

Invariante 6 do MASTER: pytest determinístico, SEM evals LLM, SEM create_app/DB.
Usa Table SQLAlchemy sintético + valida o catalog.json REAL já gerado (read-only).
"""
import importlib.util
import json
import sys
from pathlib import Path

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
)

_REPO = Path(__file__).resolve().parents[3]
_SCRIPT = _REPO / ".claude/skills/consultando-sql/scripts/generate_schemas.py"
_CATALOG = _REPO / ".claude/skills/consultando-sql/schemas/catalog.json"


def _load():
    spec = importlib.util.spec_from_file_location("generate_schemas_s1", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["generate_schemas_s1"] = mod
    spec.loader.exec_module(mod)
    return mod


gs = _load()


def _carteira_like():
    """Table sintético espelhando carteira_principal (campos representativos)."""
    md = MetaData()
    return Table(
        "carteira_principal", md,
        Column("id", Integer, primary_key=True),
        Column("num_pedido", String(50)),
        Column("cod_produto", String(50)),
        Column("pedido_cliente", String(100)),
        Column("data_pedido", Date),
        Column("data_atual_pedido", Date),
        Column("status_pedido", String(30)),
        Column("cnpj_cpf", String(20)),
        Column("raz_social", String(255)),
        Column("qtd_saldo_produto_pedido", Numeric(15, 3)),
        Column("created_at", DateTime),
        Column("updated_at", DateTime),
        Column("ativo", Integer),
    )


# =====================================================================
# _select_key_fields (Table sintético, sem DB)
# =====================================================================
class TestSelectKeyFields:
    def test_inclui_chaves_de_negocio(self):
        kf = gs._select_key_fields(_carteira_like())
        assert "num_pedido" in kf
        assert "cod_produto" in kf
        assert "cnpj_cpf" in kf

    def test_exclui_id_e_auditoria(self):
        kf = gs._select_key_fields(_carteira_like())
        for proibido in ("id", "created_at", "updated_at", "ativo"):
            assert proibido not in kf

    def test_no_maximo_um_campo_data(self):
        kf = gs._select_key_fields(_carteira_like())
        datas = [c for c in kf if c.startswith("data_") or c.endswith("_data")]
        assert len(datas) <= 1, f"redundância de data: {datas}"

    def test_teto_5(self):
        assert len(gs._select_key_fields(_carteira_like())) <= 5

    def test_deterministico(self):
        a = gs._select_key_fields(_carteira_like())
        b = gs._select_key_fields(_carteira_like())
        assert a == b

    def test_fallback_sem_chaves_de_negocio(self):
        md = MetaData()
        t = Table(
            "x", md,
            Column("id", Integer, primary_key=True),
            Column("foo", String(10)),
            Column("bar", String(10)),
            Column("baz", String(10)),
        )
        kf = gs._select_key_fields(t)
        assert "id" not in kf
        assert len(kf) >= 1  # não retorna vazio mesmo sem campo "de negócio"


# =====================================================================
# _dominio_from_module
# =====================================================================
class TestDominio:
    def test_mapa_apps_conhecidos(self):
        assert gs._dominio_from_module("app.carteira.models", "carteira_principal") == "Carteira"
        assert gs._dominio_from_module("app.separacao.models", "separacao") == "Separação"
        assert gs._dominio_from_module("app.faturamento.models", "faturamento_produto") == "Faturamento"

    def test_submodulo_profundo(self):
        assert gs._dominio_from_module("app.pallet.models.credito", "pallet_creditos") == "Pallets"

    def test_fallback_sem_modulo_nao_vazio(self):
        assert gs._dominio_from_module(None, "carvia_sessoes_cotacao")

    def test_app_desconhecido_vira_titlecase(self):
        assert gs._dominio_from_module("app.foo_bar.models", "x") == "Foo Bar"


# =====================================================================
# generate_catalog_entry
# =====================================================================
class TestCatalogEntry:
    def test_entry_tem_dominio_e_key_fields(self):
        entry = gs.generate_catalog_entry("carteira_principal", _carteira_like(), None)
        assert "dominio" in entry and entry["dominio"]
        assert "key_fields" in entry and entry["key_fields"]
        assert "name" in entry and "description" in entry


# =====================================================================
# catalog.json REAL (valida a regeneração da Parte A)
# =====================================================================
class TestCatalogReal:
    @classmethod
    def setup_class(cls):
        cls.cat = json.loads(_CATALOG.read_text(encoding="utf-8"))
        cls.by_name = {e["name"]: e for e in cls.cat["tabelas"]}

    def test_todas_entries_tem_dominio(self):
        faltando = [e["name"] for e in self.cat["tabelas"] if not e.get("dominio")]
        assert not faltando, f"entries sem dominio: {faltando[:10]}"

    def test_todas_entries_tem_key_fields(self):
        faltando = [e["name"] for e in self.cat["tabelas"] if not e.get("key_fields")]
        assert not faltando, f"entries sem key_fields: {faltando[:10]}"

    def test_key_fields_carteira(self):
        kf = self.by_name["carteira_principal"]["key_fields"]
        assert {"num_pedido", "cod_produto", "cnpj_cpf"} <= set(kf)
        assert "id" not in kf
        # filtro útil (status) surge — trava o fix de _is_id_like (data_pedido/
        # status_pedido eram falso-positivo de "id" e roubavam o lugar)
        assert "status_pedido" in kf

    def test_key_fields_separacao(self):
        kf = self.by_name["separacao"]["key_fields"]
        assert {"num_pedido", "cod_produto"} <= set(kf)
        assert ("numero_nf" in kf) or ("separacao_lote_id" in kf)

    def test_key_fields_faturamento(self):
        kf = self.by_name["faturamento_produto"]["key_fields"]
        assert {"numero_nf", "cod_produto", "cnpj_cliente"} <= set(kf)

    def test_dominios_corretos(self):
        assert self.by_name["carteira_principal"]["dominio"] == "Carteira"
        assert self.by_name["separacao"]["dominio"] == "Separação"
        assert self.by_name["faturamento_produto"]["dominio"] == "Faturamento"

    def test_admin_tables_tem_dominio(self):
        for e in self.cat.get("tabelas_admin", []):
            assert e.get("dominio"), f"admin sem dominio: {e['name']}"
