"""Testes da logica pura/mockavel da skill `conciliando-transferencias-internas`.

CONTEXTO (Onda E da auditoria de skills):
A skill e WRITE sobre extratos bancarios da NACOM GOYA em PRODUCAO e ate aqui tinha
ZERO cobertura de teste (auditoria 2026-05-29 classificou risco ALTA). O codigo
executavel NAO vive em um modulo `.py` — vive INLINE em
`.claude/skills/conciliando-transferencias-internas/references/codigo-operacional.md`
(5 funcoes + helper, rodadas via Bash pela skill). Logo, o "single source of truth"
e o proprio markdown.

ESTRATEGIA (sem mudanca de runtime, sem tocar PROD/Odoo/DB):
1. Extrai os blocos ```python``` do markdown (codigo REAL que a skill executa).
2. Neutraliza os imports `from app...` e injeta `get_odoo_connection` como um MagicMock
   controlavel (padrao de mock do repo — ver tests/odoo/services/*).
3. Exercita as unidades PURAS / MOCKAVEIS de maior valor (a logica-seguranca de
   matching de pares e o roteamento banco->journal — onde um bug gera WRITE errado).

Assim o teste valida o codigo que efetivamente embarca (e quebra se alguem corromper
o markdown), sem extrair a logica para um modulo novo (isso seria mudanca de runtime,
fora do escopo "baixo risco / nao-runtime" desta onda).

Fonte das funcoes: codigo-operacional.md (verificado ao vivo em 2026-06-01).
"""
import re
import pathlib

import pytest
from unittest.mock import MagicMock

# repo_root/.claude/skills/.../references/codigo-operacional.md
# __file__ = repo_root/tests/skills/conciliando_transferencias_internas/test_*.py
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
_MD = (
    _REPO_ROOT
    / ".claude/skills/conciliando-transferencias-internas/references/codigo-operacional.md"
)

# Nomes que DEVEM ser extraidos do markdown. Se algum sumir/quebrar, o assert
# em _load_namespace falha alto (em vez de silenciosamente nao testar nada).
_REQUIRED = [
    "preparar_extrato_e_reconciliar",
    "criar_transferencia_interna_e_conciliar",
    "conciliar_pagamento_transferencia_existente",
    "rastrear_cadeia_documental",
    "levantar_pares_transferencia_interna",
    "_extrair_journal_destino",
    "JOURNAL_MAP",
    "BANCO_JOURNAL_MAP",
]


def _strip_app_imports(code: str) -> str:
    """Remove imports de `app` — a conexao real e substituida por mock injetado."""
    code = re.sub(r"^\s*from app[.\s].*$", "", code, flags=re.M)
    code = re.sub(r"^\s*import app\b.*$", "", code, flags=re.M)
    return code


def _load_namespace(odoo_mock):
    """Extrai e executa os blocos python do markdown num namespace isolado.

    `get_odoo_connection()` retorna SEMPRE o mesmo `odoo_mock` (o codigo chama
    `odoo = get_odoo_connection()` dentro de cada funcao), permitindo ao teste
    controlar `odoo_mock.execute_kw`.

    Blocos-exemplo do markdown (ex.: secao "Execucao apos diagnostico", que tem
    chamadas top-level a variaveis indefinidas) levantam excecao no exec e sao
    ignorados de proposito; a integridade e garantida pelo assert dos _REQUIRED.
    """
    assert _MD.exists(), f"markdown da skill nao encontrado: {_MD}"
    src = _MD.read_text(encoding="utf-8")
    blocks = re.findall(r"```python\n(.*?)```", src, re.DOTALL)
    assert blocks, "nenhum bloco ```python``` encontrado no markdown"

    ns = {"get_odoo_connection": lambda: odoo_mock}
    for block in blocks:
        try:
            exec(compile(_strip_app_imports(block), str(_MD), "exec"), ns)
        except Exception:
            # bloco-exemplo (refs top-level indefinidas) — esperado, ignora
            continue

    missing = [n for n in _REQUIRED if n not in ns]
    assert not missing, f"funcoes nao extraidas do markdown: {missing}"
    return ns


@pytest.fixture
def odoo_mock():
    return MagicMock()


@pytest.fixture
def ns(odoo_mock):
    return _load_namespace(odoo_mock)


# ---------------------------------------------------------------------------
# Sanity: extracao + constantes (fonte de verdade = markdown)
# ---------------------------------------------------------------------------
class TestExtracao:
    def test_todas_funcoes_extraidas(self, ns):
        for nome in _REQUIRED:
            assert nome in ns

    def test_journal_map_valores(self, ns):
        # codigo-operacional.md secao "Levantamento em Lote"
        jm = ns["JOURNAL_MAP"]
        assert jm["GRAFENO"] == 883
        assert jm["SICOOB"] == 10
        assert jm["BRADESCO"] == 388
        assert jm["AGIS"] == 1046
        assert jm["VORTX GRAFENO"] == 1068

    def test_banco_journal_map_valores(self, ns):
        bm = ns["BANCO_JOURNAL_MAP"]
        assert bm["756"] == 10    # SICOOB
        assert bm["237"] == 388   # BRADESCO
        assert bm["033"] == 1046  # AGIS
        assert bm["274"] == 1068  # VORTX GRAFENO


# ---------------------------------------------------------------------------
# _extrair_journal_destino — funcao PURA (regex banco + fallback por nome)
# ---------------------------------------------------------------------------
class TestExtrairJournalDestino:
    @pytest.mark.parametrize(
        "payment_ref,esperado",
        [
            ("Banco 756 Agencia 4351 Conta 45078-2", 10),
            ("xx Banco 237 yy", 388),
            ("Banco 033 zz", 1046),
            ("Banco 274 ww", 1068),
            ("banco 756 caixa-baixa", 10),  # regex [Bb]anco e case-insensitive
        ],
    )
    def test_codigo_bancario(self, ns, payment_ref, esperado):
        assert ns["_extrair_journal_destino"](payment_ref) == esperado

    @pytest.mark.parametrize(
        "payment_ref,esperado",
        [
            ("transferencia SICOOB origem", 10),
            ("pagamento AGIS GARANTIDA", 1046),
            ("ref BRADESCO conta", 388),
        ],
    )
    def test_fallback_por_nome_nao_ambiguo(self, ns, payment_ref, esperado):
        # Sem "Banco <codigo>" no ref, cai no fallback que casa nome do journal.
        assert ns["_extrair_journal_destino"](payment_ref) == esperado

    def test_codigo_bancario_tem_precedencia_sobre_nome(self, ns):
        # "Banco 756" (=SICOOB 10) vence mesmo com "GRAFENO" no texto.
        assert ns["_extrair_journal_destino"]("Banco 756 GRAFENO mistura") == 10

    @pytest.mark.parametrize("payment_ref", [None, "", "sem pistas de banco"])
    def test_sem_match_retorna_none(self, ns, payment_ref):
        assert ns["_extrair_journal_destino"](payment_ref) is None

    def test_codigo_desconhecido_sem_nome_retorna_none(self, ns):
        assert ns["_extrair_journal_destino"]("Banco 999 inexistente") is None


# ---------------------------------------------------------------------------
# levantar_pares_transferencia_interna — logica de matching (CORE de seguranca)
# ---------------------------------------------------------------------------
def _linha(id_, amount, journal, date="2025-09-08", ref="NACOM GOYA transf"):
    return {
        "id": id_,
        "date": date,
        "amount": amount,
        "payment_ref": ref,
        "journal_id": list(journal),
    }


class TestLevantarPares:
    def test_par_simples_casado(self, ns, odoo_mock):
        odoo_mock.execute_kw.return_value = [
            _linha(1, -5203.82, (883, "GRAFENO")),
            _linha(2, 5203.82, (10, "SICOOB")),
        ]
        pares = ns["levantar_pares_transferencia_interna"]()
        assert len(pares) == 1
        p = pares[0]
        assert p["pag_id"] == 1 and p["rec_id"] == 2
        assert p["amount"] == 5203.82 and p["date"] == "2025-09-08"

    def test_exclui_fav_e_movimentacao(self, ns, odoo_mock):
        odoo_mock.execute_kw.return_value = [
            _linha(1, -100.0, (883, "GRAFENO"), ref="FAV fornecedor terceiro"),
            _linha(2, 100.0, (10, "SICOOB"), ref="Movimentação avulsa"),
        ]
        pares = ns["levantar_pares_transferencia_interna"]()
        assert pares == []

    def test_mesmo_journal_nao_e_par(self, ns, odoo_mock):
        # Regra: journals DEVEM ser diferentes (transferencia entre contas).
        odoo_mock.execute_kw.return_value = [
            _linha(1, -100.0, (883, "GRAFENO")),
            _linha(2, 100.0, (883, "GRAFENO")),
        ]
        assert ns["levantar_pares_transferencia_interna"]() == []

    def test_valores_diferentes_nao_casam(self, ns, odoo_mock):
        odoo_mock.execute_kw.return_value = [
            _linha(1, -100.0, (883, "GRAFENO")),
            _linha(2, 100.5, (10, "SICOOB")),
        ]
        assert ns["levantar_pares_transferencia_interna"]() == []

    def test_datas_diferentes_nao_casam(self, ns, odoo_mock):
        odoo_mock.execute_kw.return_value = [
            _linha(1, -100.0, (883, "GRAFENO"), date="2025-09-08"),
            _linha(2, 100.0, (10, "SICOOB"), date="2025-09-09"),
        ]
        assert ns["levantar_pares_transferencia_interna"]() == []

    def test_credito_nao_e_reutilizado(self, ns, odoo_mock):
        # 2 debitos, 1 credito que casa: apenas 1 par (credito usado uma vez).
        odoo_mock.execute_kw.return_value = [
            _linha(1, -100.0, (883, "GRAFENO")),
            _linha(3, -100.0, (388, "BRADESCO")),
            _linha(2, 100.0, (10, "SICOOB")),
        ]
        pares = ns["levantar_pares_transferencia_interna"]()
        assert len(pares) == 1

    def test_filtro_valor(self, ns, odoo_mock):
        odoo_mock.execute_kw.return_value = [
            _linha(1, -100.0, (883, "GRAFENO")),
            _linha(2, 100.0, (10, "SICOOB")),
            _linha(3, -200.0, (883, "GRAFENO")),
            _linha(4, 200.0, (10, "SICOOB")),
        ]
        pares = ns["levantar_pares_transferencia_interna"](valor=200.0)
        assert len(pares) == 1 and pares[0]["amount"] == 200.0

    def test_resolucao_journal_por_nome_monta_domain(self, ns, odoo_mock):
        odoo_mock.execute_kw.return_value = []
        ns["levantar_pares_transferencia_interna"](journal="GRAFENO")
        domain = odoo_mock.execute_kw.call_args[0][2][0]
        assert ["journal_id", "=", 883] in domain

    def test_resolucao_journal_por_id(self, ns, odoo_mock):
        odoo_mock.execute_kw.return_value = []
        ns["levantar_pares_transferencia_interna"](journal=883)
        domain = odoo_mock.execute_kw.call_args[0][2][0]
        assert ["journal_id", "=", 883] in domain

    def test_domain_base_filtra_nacom_e_flags(self, ns, odoo_mock):
        odoo_mock.execute_kw.return_value = []
        ns["levantar_pares_transferencia_interna"](
            data_inicio="2025-09-01", data_fim="2025-09-30"
        )
        domain = odoo_mock.execute_kw.call_args[0][2][0]
        # Estrutura do OR: '|' e binario e cobre EXATAMENTE as 2 condicoes
        # payment_ref (NACOM GOYA / CNPJ). Pinar a estrutura, nao so a presenca,
        # protege contra mover o '|' ou meter condicao errada dentro do OR.
        assert domain[0] == "|"
        assert domain[1] == ["payment_ref", "ilike", "NACOM GOYA"]
        assert domain[2] == ["payment_ref", "ilike", "61.724.241"]
        # Filtros inviolaveis (REGRAS ANTI-ALUCINACAO do SKILL.md)
        assert ["is_reconciled", "=", False] in domain
        assert ["to_check", "=", False] in domain
        assert ["date", ">=", "2025-09-01"] in domain
        assert ["date", "<=", "2025-09-30"] in domain


# ---------------------------------------------------------------------------
# preparar_extrato_e_reconciliar — invariante CRITICA: account_id e o ULTIMO
# write antes do action_post (GOTCHA do SKILL.md: write na statement_line
# regenera move_lines e reverteria account_id se feito antes).
# ---------------------------------------------------------------------------
class TestOrdemDeWrites:
    def _side_effect(self):
        def se(model, method, args, kwargs=None):
            if model == "account.bank.statement.line" and method == "search_read":
                fields = (kwargs or {}).get("fields", [])
                if "is_reconciled" in fields:  # verificacao final (passo 10)
                    return [{"is_reconciled": True, "amount_residual": 0.0}]
                return [{"move_id": [99, "mv"], "payment_ref": "Banco 274 ref orig"}]
            if model == "account.move.line" and method == "search_read":
                return [
                    {"id": 201, "account_id": [22199, "TRANSITORIA"],
                     "debit": 0.0, "credit": 5203.82},
                    {"id": 202, "account_id": [26868, "PENDENTES"],
                     "debit": 5203.82, "credit": 0.0},
                ]
            return True  # button_draft / write / action_post / reconcile
        return se

    @staticmethod
    def _idx(calls, predicate):
        for i, c in enumerate(calls):
            if predicate(c.args):
                return i
        return None

    def test_account_id_e_ultimo_write_antes_do_post(self, ns, odoo_mock):
        odoo_mock.execute_kw.side_effect = self._side_effect()

        ok = ns["preparar_extrato_e_reconciliar"](
            stmt_line_id=10050, payment_pendentes_line_id=777,
            partner_id=1, ref="TRANSF-INT/2025-09-08",
        )
        assert ok is True

        calls = odoo_mock.execute_kw.call_args_list

        def is_write(a, model, key):
            return (
                a[0] == model and a[1] == "write"
                and len(a[2]) > 1 and isinstance(a[2][1], dict) and key in a[2][1]
            )

        idx_stmt_write = self._idx(
            calls, lambda a: is_write(a, "account.bank.statement.line", "partner_id"))
        idx_name_write = self._idx(
            calls, lambda a: is_write(a, "account.move.line", "name"))
        idx_acct_write = self._idx(
            calls, lambda a: is_write(a, "account.move.line", "account_id"))
        idx_post = self._idx(calls, lambda a: a[1] == "action_post")
        idx_reconcile = self._idx(calls, lambda a: a[1] == "reconcile")

        # todos os passos ocorreram
        assert idx_stmt_write is not None
        assert idx_name_write is not None
        assert idx_acct_write is not None
        assert idx_post is not None
        assert idx_reconcile is not None
        # INVARIANTE: account_id depois do write da statement_line e do name,
        # e antes do post; reconcile por ultimo.
        assert idx_stmt_write < idx_acct_write
        assert idx_name_write < idx_acct_write
        assert idx_acct_write < idx_post < idx_reconcile

    def test_account_id_destino_e_pendentes_26868(self, ns, odoo_mock):
        odoo_mock.execute_kw.side_effect = self._side_effect()
        ns["preparar_extrato_e_reconciliar"](10050, 777, ref="X")
        calls = odoo_mock.execute_kw.call_args_list
        acct_writes = [
            c.args for c in calls
            if c.args[0] == "account.move.line" and c.args[1] == "write"
            and len(c.args[2]) > 1 and isinstance(c.args[2][1], dict)
            and "account_id" in c.args[2][1]
        ]
        assert acct_writes, "nenhum write de account_id"
        # TRANSITORIA (22199) -> PENDENTES (26868)
        assert acct_writes[0][2][1]["account_id"] == 26868
        # foi aplicado na linha cujo account_id era 22199
        assert acct_writes[0][2][0] == [201]


# ---------------------------------------------------------------------------
# conciliar_pagamento_transferencia_existente — auto-escalacao Sit 2 -> Sit 2b
# quando a busca direta por payment (amount+date) nao acha nada.
# ---------------------------------------------------------------------------
class TestAutoEscalacao2b:
    def test_busca_direta_vazia_escala_para_cadeia(self, ns, odoo_mock):
        # Todas as buscas de account.payment retornam vazio -> escala para
        # rastrear_cadeia_documental. Fazemos a cadeia terminar sem achar
        # credito (retorna {'error': ...}); a funcao entao retorna o erro
        # COM 'cadeia_resultado' preenchido (prova de que escalou e rastreou).
        def se(model, method, args, kwargs=None):
            if model == "account.payment" and method == "search_read":
                return []  # busca direta + busca ampliada falham
            if model == "account.bank.statement.line" and method == "search_read":
                # stmt do rastreador: nao reconciliado, ref resolvivel p/ journal
                return [{
                    "id": 10050, "move_id": [99, "mv"], "amount": -5203.82,
                    "date": "2025-09-08", "payment_ref": "Banco 274 origem",
                    "journal_id": [883, "GRAFENO"], "is_reconciled": False,
                }]
            # creditos no destino: nenhum -> cadeia retorna erro (sem found)
            return []
        odoo_mock.execute_kw.side_effect = se

        res = ns["conciliar_pagamento_transferencia_existente"](
            stmt_pag_id=10050, amount=5203.82, date="2025-09-08", journal_pag_id=883,
        )
        # nao casou diretamente, nem por cadeia -> erro COM diagnostico de cadeia
        assert "error" in res
        assert "cadeia_resultado" in res
        # a cadeia foi de fato rastreada (rastrear_cadeia_documental rodou e
        # retornou um dict de erro de cadeia — prova que houve escalacao real,
        # nao um short-circuit que apenas devolve cadeia_resultado=None)
        assert res["cadeia_resultado"] is not None
        assert res["cadeia_resultado"].get("error")
