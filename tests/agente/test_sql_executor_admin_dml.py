"""
Testes do fix de escrita SQL para admins (causa raiz: executor quebrava em DML).

Determinísticos: NÃO dependem de DB real, Redis nem LLM.
- _is_dml_statement / validate_admin: funções puras (regex/string).
- SQLExecutor._execute_in_context: exercido com um fake db.session injetado
  (monkeypatch em `app.db`), reproduzindo o CursorResult do SQLAlchemy quando a
  query é DML sem RETURNING (returns_rows=False, .keys()/.fetchall() lançam
  "result object does not return rows").

Causa raiz: a tool consultar_sql em admin_mode chegava ao executor, mas
`columns = list(result.keys())` estourava ResourceClosedError em DELETE/UPDATE/
INSERT, o except fazia rollback e a escrita NUNCA persistia.

Política (2026-06-06): admin (USUARIOS_SQL_ADMIN) pode SELECT/INSERT/UPDATE/DELETE;
DDL (DROP/ALTER/TRUNCATE/...) e multi-statement permanecem bloqueados.
"""
import os
import sys

import pytest

# Tornar text_to_sql importável (mesmo pattern dos tools MCP em app/agente/tools/).
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_SCRIPTS_DIR = os.path.join(_REPO_ROOT, '.claude', 'skills', 'consultando-sql', 'scripts')
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import text_to_sql as T  # noqa: E402


# =====================================================================
# _is_dml_statement — detector de escrita DML (INSERT/UPDATE/DELETE)
# =====================================================================

class TestIsDmlStatement:
    @pytest.mark.parametrize("sql", [
        "DELETE FROM foo WHERE id = 1",
        "delete from foo where id = 1",
        "  \n DELETE FROM foo",
        "UPDATE foo SET a = 1 WHERE id = 2",
        "update foo set a = 1",
        "INSERT INTO foo (a) VALUES (1)",
        "insert into foo (a) values (1)",
    ])
    def test_dml_is_true(self, sql):
        assert T._is_dml_statement(sql) is True

    @pytest.mark.parametrize("sql", [
        "SELECT * FROM foo",
        "select a from foo",
        "WITH base AS (SELECT 1) SELECT * FROM base",
        "DROP TABLE foo",
        "TRUNCATE foo",
        "",
        "   ",
    ])
    def test_non_dml_is_false(self, sql):
        assert T._is_dml_statement(sql) is False


# =====================================================================
# SQLSafetyValidator.validate_admin — libera DML, bloqueia DDL
# =====================================================================

class TestValidateAdminAllowsDmlAndSelect:
    @pytest.mark.parametrize("sql", [
        "SELECT * FROM separacao WHERE id = 1",
        "DELETE FROM carvia_faturas WHERE id = 161",
        "UPDATE cadastro_palletizacao SET tipo_materia_prima = 'X' WHERE cod_produto = '123'",
        "INSERT INTO foo (a, b) VALUES (1, 2)",
        "WITH t AS (SELECT id FROM embarques) SELECT * FROM t",
    ])
    def test_admin_allows(self, sql):
        validator = T.SQLSafetyValidator()
        is_safe, concerns = validator.validate_admin(sql)
        assert is_safe is True, f"deveria liberar: {sql} (concerns={concerns})"


class TestValidateAdminBlocksDdlAndDanger:
    @pytest.mark.parametrize("sql,keyword", [
        ("DROP TABLE foo", "DROP"),
        ("TRUNCATE foo", "TRUNCATE"),
        ("ALTER TABLE foo DROP COLUMN x", "ALTER"),
        ("CREATE TABLE foo (id int)", "CREATE"),
        ("GRANT ALL ON foo TO bar", "GRANT"),
        ("REVOKE ALL ON foo FROM bar", "REVOKE"),
    ])
    def test_admin_blocks_ddl(self, sql, keyword):
        validator = T.SQLSafetyValidator()
        is_safe, concerns = validator.validate_admin(sql)
        assert is_safe is False, f"deveria bloquear DDL: {sql}"
        assert any(keyword in c.upper() for c in concerns), f"concern deveria citar {keyword}: {concerns}"

    def test_admin_blocks_multi_statement(self):
        validator = T.SQLSafetyValidator()
        is_safe, concerns = validator.validate_admin("DELETE FROM foo WHERE id=1; DROP TABLE bar")
        assert is_safe is False
        assert any("statement" in c.lower() for c in concerns)

    def test_admin_blocks_dangerous_function(self):
        validator = T.SQLSafetyValidator()
        is_safe, concerns = validator.validate_admin("SELECT pg_read_file('/etc/passwd')")
        assert is_safe is False
        assert any("pg_read_file" in c for c in concerns)

    def test_admin_blocks_select_into(self):
        validator = T.SQLSafetyValidator()
        is_safe, concerns = validator.validate_admin("SELECT * INTO nova_tabela FROM foo")
        assert is_safe is False


# =====================================================================
# SQLExecutor._execute_in_context — DML não quebra (causa raiz)
# =====================================================================

class _FakeResult:
    """Reproduz CursorResult do SQLAlchemy.

    Para DML sem RETURNING: returns_rows=False e .keys()/.fetchall() lançam
    ResourceClosedError ("result object does not return rows").
    """
    def __init__(self, returns_rows, columns=None, rows=None, rowcount=-1):
        self.returns_rows = returns_rows
        self._columns = columns or []
        self._rows = rows or []
        self.rowcount = rowcount

    def keys(self):
        if not self.returns_rows:
            raise Exception("This result object does not return rows. It has been closed automatically.")
        return self._columns

    def fetchall(self):
        if not self.returns_rows:
            raise Exception("This result object does not return rows. It has been closed automatically.")
        return self._rows


class _FakeSession:
    def __init__(self, main_result):
        self._main_result = main_result
        self.committed = False
        self.rolled_back = False

    def execute(self, clause):
        # SET TRANSACTION / SET LOCAL ... → result vazio dummy.
        text_str = str(clause).strip().upper()
        if text_str.startswith("SET "):
            return _FakeResult(returns_rows=False, rowcount=-1)
        return self._main_result

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


class _FakeDB:
    def __init__(self, session):
        self.session = session


@pytest.fixture
def patch_db(monkeypatch):
    """Injeta um fake db.session em `app.db` para o `from app import db` interno."""
    import app as app_module

    def _apply(main_result):
        session = _FakeSession(main_result)
        monkeypatch.setattr(app_module, 'db', _FakeDB(session))
        return session

    return _apply


class TestExecutorDmlNaoQuebra:
    def test_delete_retorna_linhas_afetadas_e_commita(self, patch_db):
        session = patch_db(_FakeResult(returns_rows=False, rowcount=3))
        executor = T.SQLExecutor()

        rows, columns = executor._execute_in_context(
            "DELETE FROM carvia_faturas WHERE id = 240", read_write=True
        )

        assert columns == ["linhas_afetadas"]
        assert rows == [{"linhas_afetadas": 3}]
        assert session.committed is True
        assert session.rolled_back is False

    def test_update_rowcount_indefinido_vira_zero(self, patch_db):
        session = patch_db(_FakeResult(returns_rows=False, rowcount=-1))
        executor = T.SQLExecutor()

        rows, columns = executor._execute_in_context(
            "UPDATE foo SET a = 1 WHERE id = 99", read_write=True
        )

        assert columns == ["linhas_afetadas"]
        assert rows == [{"linhas_afetadas": 0}]
        assert session.committed is True

    def test_select_inalterado_e_faz_rollback_em_readonly(self, patch_db):
        session = patch_db(
            _FakeResult(returns_rows=True, columns=["a", "b"], rows=[(1, 2), (3, 4)])
        )
        executor = T.SQLExecutor()

        rows, columns = executor._execute_in_context(
            "SELECT a, b FROM foo", read_write=False
        )

        assert columns == ["a", "b"]
        assert rows == [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
        assert session.rolled_back is True
        assert session.committed is False


# =====================================================================
# Integração do run(): bypass total do Evaluator p/ DML de admin
# (Generator/Evaluator/Executor monkeypatched — sem DB/LLM real)
# =====================================================================

def _boom(*args, **kwargs):
    raise AssertionError("Esta etapa NAO deveria ser chamada neste caminho")


@pytest.fixture(scope="module")
def pipeline():
    # Instancia o pipeline (carrega apenas schemas JSON — sem DB, sem LLM).
    return T.TextToSQLPipeline()


class TestRunAdminDmlBypass:
    def test_admin_dml_off_mode_pula_evaluator_e_executa_read_write(self, pipeline, monkeypatch):
        """admin + DELETE (sql_first OFF): Generator gera o SQL, mas o Evaluator
        Haiku NAO é chamado (bypass) e o executor roda em read_write."""
        captured = {}

        def fake_gen(q, catalog_text_override=None):
            return "DELETE FROM carvia_faturas WHERE id = 240"

        def fake_exec(sql, read_write=False):
            captured["rw"] = read_write
            captured["sql"] = sql
            return ([{"linhas_afetadas": 1}], ["linhas_afetadas"])

        monkeypatch.setattr(pipeline.generator, "generate", fake_gen)
        # Se o Evaluator for chamado, o teste falha (prova o bypass):
        monkeypatch.setattr(pipeline.evaluator, "evaluate", _boom)
        monkeypatch.setattr(pipeline.executor, "execute", fake_exec)

        res = pipeline.run(
            "DELETE FROM carvia_faturas WHERE id = 240",
            sql_first_mode="off", admin_mode=True,
        )

        assert res["sucesso"] is True
        assert captured["rw"] is True                       # admin -> read_write (persiste)
        assert res["etapas"].get("evaluator_skipped") == "admin_dml_bypass"

    def test_admin_ddl_bloqueado_mesmo_com_evaluator_aprovando(self, pipeline, monkeypatch):
        """admin + DROP: ainda que o Evaluator aprove, a ETAPA 3 (validate_admin)
        bloqueia DDL deterministicamente e o executor NAO é chamado."""
        def fake_gen(q, catalog_text_override=None):
            return "DROP TABLE carvia_faturas"

        def fake_eval(question, sql, schema_text, admin_mode=False, session_dml_context=None):
            return {"approved": True, "improved_sql": None, "reason": "haiku_aprovou"}

        monkeypatch.setattr(pipeline.generator, "generate", fake_gen)
        monkeypatch.setattr(pipeline.evaluator, "evaluate", fake_eval)
        monkeypatch.setattr(pipeline.executor, "execute", _boom)  # nao deve executar

        res = pipeline.run(
            "DROP TABLE carvia_faturas", sql_first_mode="off", admin_mode=True,
        )

        assert res["sucesso"] is False
        assert "bloqueada por seguranca" in (res.get("aviso") or "").lower()
        assert "DROP" in (res.get("aviso") or "").upper()
