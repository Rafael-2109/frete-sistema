"""Testes determinísticos da logica PURA dos scripts CT-e da skill `operando-ssw`.

CONTEXTO (Onda E da auditoria de skills):
Os 4 scripts fiscais CT-e (emitir 004, cancelar 004, complementar 222, fatura 437)
nao tinham nenhuma cobertura de teste. Eles sao automacoes Playwright que falam com
o SSW/SEFAZ — o FLUXO de browser nao e testavel de forma barata/segura. Mas a logica
FISCAL PURA (parse de CTRC, validacao de args, grossing up de ICMS) e o que quebra
silenciosamente, e ESSA da para testar em milissegundos, sem browser, sem SEFAZ,
sem custo de token (substitui a abordagem de evals LLM, cara de rodar).

ESTRATEGIA: carrega cada script via importlib (mesmo padrao de
tests/odoo/services/test_cleanup_pos_bulk.py) e exercita as funcoes module-level
puras. Nenhum browser e aberto e nenhuma chamada de rede e feita (as funcoes async
que falam com o SSW NAO sao chamadas).

Fontes (verificadas ao vivo 2026-06-01):
- emitir_cte_complementar_222.py:36-151 (constantes, validar_args, parsear_ctrc,
  _parse_valor_brasileiro, calcular_valor_cte_complementar)
- cancelar_cte_004.py:80-96 (validar_campos)
- SCRIPTS.md / references/CTE.md (regras de dominio)
"""
import argparse
import importlib.util
import os
import sys
from pathlib import Path

import pytest

# repo_root/.claude/skills/operando-ssw/scripts
# __file__ = repo_root/tests/skills/operando_ssw/test_cte_validacao.py
_SCRIPTS = (
    Path(__file__).resolve().parents[3]
    / ".claude/skills/operando-ssw/scripts"
)

# ssw_common (importado pelos scripts) precisa estar resolvivel no sys.path.
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

# Env dummy defensivo — credenciais SSW so sao usadas dentro das funcoes de
# browser (que NAO chamamos); setdefault nao sobrescreve um .env real.
for _k in ("SSW_URL", "SSW_DOMINIO", "SSW_CPF", "SSW_LOGIN", "SSW_SENHA"):
    os.environ.setdefault(_k, "test")

_CACHE = {}


def _load(modname, fname):
    """Carrega um script da skill via importlib (sem rodar main/browser)."""
    if modname in _CACHE:
        return _CACHE[modname]
    path = _SCRIPTS / fname
    assert path.exists(), f"script nao encontrado: {path}"
    spec = importlib.util.spec_from_file_location(modname, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[modname] = mod  # permite imports relativos internos
    spec.loader.exec_module(mod)
    _CACHE[modname] = mod
    return mod


def _ns_222(**over):
    base = dict(ctrc_pai="CAR-113-9", motivo="D", valor_outros=None,
                valor_base=200.0, tp_doc="C", unid_emit="D")
    base.update(over)
    return argparse.Namespace(**base)


# ===========================================================================
# emitir_cte_complementar_222.py — opcao 222 (CT-e complementar)
# ===========================================================================
class TestComplementar222Constantes:
    def test_constantes(self):
        m = _load("emitir_cte_complementar_222", "emitir_cte_complementar_222.py")
        assert m.MOTIVOS_VALIDOS == {"C", "D", "V", "E", "R"}
        assert m.TP_DOC_VALIDOS == {"C"}
        assert m.UNID_EMIT_VALIDOS == {"D", "O"}
        assert m.PISCOFINS_DIVISOR == 0.9075


class TestComplementar222ValidarArgs:
    def setup_method(self):
        self.m = _load("emitir_cte_complementar_222", "emitir_cte_complementar_222.py")

    def test_args_validos_nao_levanta(self):
        # valor_base sozinho e suficiente (default do _ns_222)
        self.m.validar_args(_ns_222())

    def test_valor_outros_sozinho_ok(self):
        self.m.validar_args(_ns_222(valor_base=None, valor_outros=227.90))

    def test_nenhum_valor_levanta(self):
        with pytest.raises(ValueError, match="valor"):
            self.m.validar_args(_ns_222(valor_base=None, valor_outros=None))

    def test_ambos_valores_nao_levanta(self):
        # Comportamento REAL do script: passar ambos NAO levanta (auto-calc e
        # simplesmente pulado). A doc CTE.md gotcha 25 afirma o contrario —
        # follow-up de doc, nao bloqueia. Este teste pina o comportamento atual.
        self.m.validar_args(_ns_222(valor_base=200.0, valor_outros=227.90))

    def test_motivo_invalido_levanta(self):
        with pytest.raises(ValueError, match="motivo"):
            self.m.validar_args(_ns_222(motivo="X"))

    @pytest.mark.parametrize("motivo", ["C", "D", "V", "E", "R"])
    def test_todos_motivos_validos(self, motivo):
        self.m.validar_args(_ns_222(motivo=motivo))

    def test_tp_doc_invalido_levanta(self):
        with pytest.raises(ValueError, match="tp_doc"):
            self.m.validar_args(_ns_222(tp_doc="Z"))

    def test_unid_emit_invalido_levanta(self):
        with pytest.raises(ValueError, match="unid_emit"):
            self.m.validar_args(_ns_222(unid_emit="X"))

    def test_ctrc_pai_vazio_levanta(self):
        with pytest.raises(ValueError, match="ctrc_pai"):
            self.m.validar_args(_ns_222(ctrc_pai=""))


class TestComplementar222ParsearCtrc:
    def setup_method(self):
        self.m = _load("emitir_cte_complementar_222", "emitir_cte_complementar_222.py")

    def test_parse_ok(self):
        assert self.m.parsear_ctrc("CAR-113-9") == ("CAR", "113", "9")

    def test_concatenado_sem_hifen(self):
        # SSW [id=2] espera numero+dv concatenados (ex: "1139") — CTE.md gotcha 19
        _filial, num, dv = self.m.parsear_ctrc("CAR-113-9")
        assert f"{num}{dv}" == "1139"

    @pytest.mark.parametrize("ruim", ["CAR113-9", "CAR-113", "113", "CAR-1-1-3"])
    def test_formato_invalido_levanta(self, ruim):
        with pytest.raises(ValueError, match="formato invalido"):
            self.m.parsear_ctrc(ruim)


class TestComplementar222ParseValor:
    def setup_method(self):
        self.m = _load("emitir_cte_complementar_222", "emitir_cte_complementar_222.py")

    @pytest.mark.parametrize("entrada,esperado", [
        ("1.863,72", 1863.72),
        ("227,90", 227.90),
        ("0,00", 0.0),
        ("", 0.0),
        (None, 0.0),
        ("abc", 0.0),
    ])
    def test_parse_valor_brasileiro(self, entrada, esperado):
        assert self.m._parse_valor_brasileiro(entrada) == esperado


class TestComplementar222GrossingUp:
    def setup_method(self):
        self.m = _load("emitir_cte_complementar_222", "emitir_cte_complementar_222.py")

    def test_valor_conhecido(self):
        # 200 / 0.9075 / (1 - 0.12) = 250.44 (round 2)
        assert self.m.calcular_valor_cte_complementar(200, 12) == 250.44

    def test_aliquota_zero(self):
        # 100 / 0.9075 / 1 = 110.19
        assert self.m.calcular_valor_cte_complementar(100, 0) == 110.19

    def test_grossing_up_sempre_maior_que_base(self):
        # com aliquota > 0 o valor final e sempre > base (grossing up)
        assert self.m.calcular_valor_cte_complementar(500, 12) > 500

    def test_aliquota_100_levanta(self):
        with pytest.raises(ValueError, match="Aliquota"):
            self.m.calcular_valor_cte_complementar(200, 100)

    def test_aliquota_acima_de_100_levanta(self):
        with pytest.raises(ValueError, match="Aliquota"):
            self.m.calcular_valor_cte_complementar(200, 150)


# ===========================================================================
# cancelar_cte_004.py — opcao 004 (cancelamento, IRREVERSIVEL)
# ===========================================================================
def _ns_cancel(**over):
    base = dict(ctrc="66", serie="CAR 68-0", motivo="NF vinculada incorretamente")
    base.update(over)
    return argparse.Namespace(**base)


class TestCancelar004Validacao:
    def setup_method(self):
        self.m = _load("cancelar_cte_004", "cancelar_cte_004.py")

    def test_args_validos_sem_erros(self):
        assert self.m.validar_campos(_ns_cancel()) == []

    def test_ctrc_obrigatorio(self):
        erros = self.m.validar_campos(_ns_cancel(ctrc=""))
        assert any("ctrc" in e for e in erros)

    def test_serie_obrigatoria(self):
        erros = self.m.validar_campos(_ns_cancel(serie=""))
        assert any("serie" in e for e in erros)

    def test_motivo_minimo_5_caracteres(self):
        erros = self.m.validar_campos(_ns_cancel(motivo="abc"))
        assert any("motivo" in e for e in erros)

    def test_motivo_maximo_200_caracteres(self):
        erros = self.m.validar_campos(_ns_cancel(motivo="x" * 201))
        assert any("200" in e for e in erros)

    def test_motivo_no_limite_200_ok(self):
        assert self.m.validar_campos(_ns_cancel(motivo="y" * 200)) == []


# ===========================================================================
# emitir_cte_004.py e gerar_fatura_ssw_437.py — sem validador puro module-level.
# Smoke: o modulo carrega limpo e expoe os simbolos-chave do fluxo.
# (A regra "437 = filial MTZ" e a chave 44-digitos vivem dentro das funcoes
#  async de browser, fora do alcance de teste unitario barato.)
# ===========================================================================
class TestScriptsCarregam:
    def test_emitir_004_carrega_e_expoe_simbolos(self):
        m = _load("emitir_cte_004", "emitir_cte_004.py")
        assert hasattr(m, "emitir_cte")
        assert hasattr(m, "trocar_filial")
        assert hasattr(m, "main")

    def test_fatura_437_carrega_e_expoe_simbolos(self):
        m = _load("gerar_fatura_ssw_437", "gerar_fatura_ssw_437.py")
        assert hasattr(m, "gerar_fatura")
        # 437 troca para MTZ obrigatoriamente (SCRIPTS.md:191) — helper dedicado
        assert hasattr(m, "trocar_filial_mtz")
        assert hasattr(m, "main")
