"""
Onda 3 / D2 — Bootstrap de ontologia canônica no KG.

Testa `app/agente/services/ontology_bootstrap.py`:
- _ENTITY_SOURCE_MAP tem os 3 tipos (produto, transportadora, cliente)
- bootstrap_entities chama _upsert_entity com user_id=0, entity_type correto,
  entity_key e entity_name extraídos dos campos certos
- nomes/chaves vazios são pulados
- idempotência: chamadas repetidas não geram erro (passthrough do ON CONFLICT)
- bootstrap_all agrega os 3 tipos e retorna dict com contagens

SEM dependência de DB real — rows passadas como list[dict] fixos.
SEM chamada a Voyage.
"""
import pytest
from unittest.mock import MagicMock, call, patch


# ---------------------------------------------------------------------------
# Helpers de fixture
# ---------------------------------------------------------------------------

def _make_conn():
    """Cria um conn mock que simula _upsert_entity retornando entity_id."""
    return MagicMock()


# ---------------------------------------------------------------------------
# Testes de estrutura do mapa
# ---------------------------------------------------------------------------

class TestEntitySourceMap:
    def test_tres_tipos_presentes(self):
        from app.agente.services.ontology_bootstrap import _ENTITY_SOURCE_MAP
        assert "produto" in _ENTITY_SOURCE_MAP
        assert "transportadora" in _ENTITY_SOURCE_MAP
        assert "cliente" in _ENTITY_SOURCE_MAP

    def test_campos_produto(self):
        from app.agente.services.ontology_bootstrap import _ENTITY_SOURCE_MAP
        cfg = _ENTITY_SOURCE_MAP["produto"]
        assert cfg["tabela"] == "cadastro_palletizacao"
        assert cfg["key_field"] == "cod_produto"
        assert cfg["name_field"] == "nome_produto"

    def test_campos_transportadora(self):
        from app.agente.services.ontology_bootstrap import _ENTITY_SOURCE_MAP
        cfg = _ENTITY_SOURCE_MAP["transportadora"]
        assert cfg["tabela"] == "transportadoras"
        assert cfg["key_field"] == "cnpj"
        assert cfg["name_field"] == "razao_social"

    def test_campos_cliente(self):
        from app.agente.services.ontology_bootstrap import _ENTITY_SOURCE_MAP
        cfg = _ENTITY_SOURCE_MAP["cliente"]
        assert cfg["tabela"] == "carteira_principal"
        assert cfg["key_field"] == "cnpj_cpf"
        assert cfg["name_field"] == "raz_social"


# ---------------------------------------------------------------------------
# Testes de bootstrap_entities
# ---------------------------------------------------------------------------

class TestBootstrapEntities:
    def _run(self, rows, entity_type="produto", upsert_mock=None):
        """
        Executa bootstrap_entities com _upsert_entity mockado.
        Retorna (count, calls).
        """
        from app.agente.services import ontology_bootstrap as mod

        if upsert_mock is None:
            upsert_mock = MagicMock(return_value=42)

        conn = _make_conn()
        with patch.object(mod, "_upsert_entity", upsert_mock):
            count = mod.bootstrap_entities(entity_type, rows, conn)

        return count, upsert_mock

    # --- user_id=0 ---
    def test_user_id_zero_produto(self):
        rows = [{"cod_produto": "101", "nome_produto": "PALMITO FATIADO"}]
        _, mock = self._run(rows, "produto")
        args = mock.call_args[0]
        assert args[1] == 0, "user_id deve ser 0 (empresa)"

    def test_user_id_zero_transportadora(self):
        rows = [{"cnpj": "12345678000199", "razao_social": "RODONAVES LTDA"}]
        _, mock = self._run(rows, "transportadora")
        args = mock.call_args[0]
        assert args[1] == 0

    def test_user_id_zero_cliente(self):
        rows = [{"cnpj_cpf": "33014556000196", "raz_social": "ATACADAO SA"}]
        _, mock = self._run(rows, "cliente")
        args = mock.call_args[0]
        assert args[1] == 0

    # --- entity_type correto ---
    def test_entity_type_produto(self):
        rows = [{"cod_produto": "101", "nome_produto": "PALMITO FATIADO"}]
        _, mock = self._run(rows, "produto")
        args = mock.call_args[0]
        assert args[2] == "produto"

    def test_entity_type_transportadora(self):
        rows = [{"cnpj": "12345678000199", "razao_social": "RODONAVES LTDA"}]
        _, mock = self._run(rows, "transportadora")
        args = mock.call_args[0]
        assert args[2] == "transportadora"

    def test_entity_type_cliente(self):
        rows = [{"cnpj_cpf": "33014556000196", "raz_social": "ATACADAO SA"}]
        _, mock = self._run(rows, "cliente")
        args = mock.call_args[0]
        assert args[2] == "cliente"

    # --- entity_key certo por tipo ---
    def test_entity_key_produto_e_cod_produto(self):
        rows = [{"cod_produto": "101", "nome_produto": "PALMITO FATIADO"}]
        _, mock = self._run(rows, "produto")
        # assinatura: _upsert_entity(conn, user_id, entity_type, entity_name, entity_key)
        # entity_key = 5o argumento
        _, kwargs = mock.call_args
        # pode ser posicional ou keyword
        all_args = mock.call_args[0]
        all_kw = mock.call_args[1] or {}
        entity_key = all_kw.get("entity_key") or (all_args[4] if len(all_args) > 4 else None)
        assert entity_key == "101"

    def test_entity_key_transportadora_e_cnpj(self):
        rows = [{"cnpj": "12345678000199", "razao_social": "RODONAVES LTDA"}]
        _, mock = self._run(rows, "transportadora")
        all_args = mock.call_args[0]
        all_kw = mock.call_args[1] or {}
        entity_key = all_kw.get("entity_key") or (all_args[4] if len(all_args) > 4 else None)
        assert entity_key == "12345678000199"

    def test_entity_key_cliente_e_cnpj_cpf(self):
        rows = [{"cnpj_cpf": "33014556000196", "raz_social": "ATACADAO SA"}]
        _, mock = self._run(rows, "cliente")
        all_args = mock.call_args[0]
        all_kw = mock.call_args[1] or {}
        entity_key = all_kw.get("entity_key") or (all_args[4] if len(all_args) > 4 else None)
        assert entity_key == "33014556000196"

    # --- entity_name ---
    def test_entity_name_produto(self):
        rows = [{"cod_produto": "101", "nome_produto": "PALMITO FATIADO"}]
        _, mock = self._run(rows, "produto")
        all_args = mock.call_args[0]
        all_kw = mock.call_args[1] or {}
        entity_name = all_kw.get("entity_name") or (all_args[3] if len(all_args) > 3 else None)
        assert entity_name == "PALMITO FATIADO"

    def test_entity_name_transportadora(self):
        rows = [{"cnpj": "12345678000199", "razao_social": "RODONAVES LTDA"}]
        _, mock = self._run(rows, "transportadora")
        all_args = mock.call_args[0]
        all_kw = mock.call_args[1] or {}
        entity_name = all_kw.get("entity_name") or (all_args[3] if len(all_args) > 3 else None)
        assert entity_name == "RODONAVES LTDA"

    # --- nome vazio é pulado ---
    def test_nome_vazio_pulado(self):
        rows = [
            {"cod_produto": "101", "nome_produto": ""},       # nome vazio
            {"cod_produto": "102", "nome_produto": None},     # nome None
            {"cod_produto": "103", "nome_produto": "VALIDO"}, # deve passar
        ]
        count, mock = self._run(rows, "produto")
        assert mock.call_count == 1
        assert count == 1

    # --- chave vazia é pulada ---
    def test_chave_vazia_pulada(self):
        rows = [
            {"cod_produto": "", "nome_produto": "PRODUTO SEM COD"},
            {"cod_produto": None, "nome_produto": "PRODUTO COD NONE"},
            {"cod_produto": "104", "nome_produto": "COM TUDO"},
        ]
        count, mock = self._run(rows, "produto")
        assert mock.call_count == 1
        assert count == 1

    # --- múltiplas rows ---
    def test_multiplas_rows_contagem(self):
        rows = [
            {"cod_produto": "201", "nome_produto": "AZEITE"},
            {"cod_produto": "202", "nome_produto": "VINAGRE"},
            {"cod_produto": "203", "nome_produto": "SAL"},
        ]
        count, mock = self._run(rows, "produto")
        assert mock.call_count == 3
        assert count == 3

    # --- idempotência: mesmo rows, segunda chamada não gera erro ---
    def test_idempotencia_segunda_chamada(self):
        rows = [{"cod_produto": "301", "nome_produto": "PALMEIRA VERDE"}]
        from app.agente.services import ontology_bootstrap as mod

        # _upsert_entity retorna 99 em ambas as chamadas (ON CONFLICT faz upsert)
        upsert_mock = MagicMock(return_value=99)
        conn = _make_conn()
        with patch.object(mod, "_upsert_entity", upsert_mock):
            c1 = mod.bootstrap_entities("produto", rows, conn)
            c2 = mod.bootstrap_entities("produto", rows, conn)

        assert c1 == 1
        assert c2 == 1
        assert upsert_mock.call_count == 2  # chamou duas vezes, nenhuma exceção

    # --- erro em uma row não aborta as demais (best-effort) ---
    def test_erro_em_row_nao_aborta(self):
        """Se _upsert_entity lança exceção em uma row, as demais continuam."""
        rows = [
            {"cod_produto": "401", "nome_produto": "AZEITONA"},
            {"cod_produto": "402", "nome_produto": "PASTA"},  # esta causa erro
            {"cod_produto": "403", "nome_produto": "AZEITE"},
        ]
        from app.agente.services import ontology_bootstrap as mod
        conn = _make_conn()

        call_count = 0
        def upsert_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:  # segunda chamada falha
                raise RuntimeError("DB error simulado")
            return call_count

        with patch.object(mod, "_upsert_entity", side_effect=upsert_side_effect):
            count = mod.bootstrap_entities("produto", rows, conn)

        # conta somente os sucedidos (2 de 3)
        assert count == 2


# ---------------------------------------------------------------------------
# Testes de bootstrap_all (mock da query DB)
# ---------------------------------------------------------------------------

class TestBootstrapAll:
    def test_retorna_dict_tres_tipos(self):
        """bootstrap_all deve retornar dict com as 3 chaves."""
        from app.agente.services import ontology_bootstrap as mod

        conn = _make_conn()
        upsert_mock = MagicMock(return_value=1)

        fake_rows = {
            "produto": [{"cod_produto": "P1", "nome_produto": "PROD1"}],
            "transportadora": [{"cnpj": "11111111000100", "razao_social": "TAC"}],
            "cliente": [{"cnpj_cpf": "22222222000100", "raz_social": "CLIENTE A"}],
        }

        def fake_read_tabela(entity_type, conn_arg, limit=None):
            return fake_rows[entity_type]

        with patch.object(mod, "_upsert_entity", upsert_mock), \
             patch.object(mod, "_read_tabela", fake_read_tabela):
            result = mod.bootstrap_all(conn)

        assert set(result.keys()) == {"produto", "transportadora", "cliente"}
        assert result["produto"] == 1
        assert result["transportadora"] == 1
        assert result["cliente"] == 1

    def test_limit_propagado(self):
        """bootstrap_all com limit=5 deve passar limit para _read_tabela."""
        from app.agente.services import ontology_bootstrap as mod

        conn = _make_conn()
        calls_limit = {}

        def fake_read_tabela(entity_type, conn_arg, limit=None):
            calls_limit[entity_type] = limit
            return []

        with patch.object(mod, "_upsert_entity", MagicMock(return_value=1)), \
             patch.object(mod, "_read_tabela", fake_read_tabela):
            mod.bootstrap_all(conn, limit=5)

        for et in ("produto", "transportadora", "cliente"):
            assert calls_limit[et] == 5

    def test_zero_voyage_chamado(self):
        """D2 deve ter CUSTO ZERO: Voyage não é chamado."""
        from app.agente.services import ontology_bootstrap as mod
        import app.embeddings  # import para verificar que nada de Voyage é invocado

        conn = _make_conn()

        voyage_called = []
        def fake_voyage(*a, **kw):
            voyage_called.append(True)

        def fake_read_tabela(entity_type, conn_arg, limit=None):
            return [{"cod_produto": "X1", "nome_produto": "TESTE",
                     "cnpj": "11111111000100", "razao_social": "T1",
                     "cnpj_cpf": "22222222000100", "raz_social": "C1"}.copy()]

        with patch.object(mod, "_upsert_entity", MagicMock(return_value=1)), \
             patch.object(mod, "_read_tabela", fake_read_tabela), \
             patch("app.embeddings.voyage_client", None, create=True):
            mod.bootstrap_all(conn)

        assert len(voyage_called) == 0, "Voyage NÃO deve ser chamado em D2"
