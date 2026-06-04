"""Smoke do system_prompt — P4 (#787): idioma PT-BR + descoberta de dominio HORA.

Deterministico: le o .md e verifica a PRESENCA das diretrizes (NAO valida o
comportamento do LLM — avals caros sao vetados; cobertura de prompt = pytest que
trava a regressao se alguem remover a regra).

Roadmap: docs/superpowers/plans/2026-06-04-roadmap-correcoes-agente-787.md (P4)
Evidencia #787: agente respondeu em ingles no meio do PT-BR e explorou tabelas
Nacom (pedido_compras/moto) antes de achar as tabelas hora_* corretas.
"""
import os

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PROMPT = os.path.join(_REPO_ROOT, "app", "agente", "prompts", "system_prompt.md")


def _prompt_text():
    with open(_PROMPT, encoding="utf-8") as f:
        return f.read()


# =====================================================================
# P4.1 — Politica de idioma: TODA a resposta (e o raciocinio) em PT-BR
# =====================================================================

class TestLanguagePolicy:
    def test_prompt_has_explicit_ptbr_language_policy(self):
        txt = _prompt_text()
        low = txt.lower()
        # diretriz dedicada e localizavel (tag propria) — saliencia alta
        assert "<language_policy>" in low, "falta a tag <language_policy> no system_prompt"
        assert "portugu" in low  # portugues do Brasil

    def _language_policy_block(self):
        txt = _prompt_text()
        start = txt.find("<language_policy>")
        end = txt.find("</language_policy>")
        assert start != -1 and end != -1 and end > start, "falta bloco <language_policy>"
        return txt[start:end].lower()

    def test_language_policy_covers_reasoning_not_only_final_answer(self):
        # O code-switch da #787 ocorreu no raciocinio EXPOSTO, nao so' na resposta.
        assert "racioc" in self._language_policy_block()  # raciocinio/raciocínio

    def test_language_policy_forbids_english_switch(self):
        # Proibicao explicita do code-switch DENTRO da politica (discriminante).
        assert "ingl" in self._language_policy_block()  # menciona ingles para proibir


# =====================================================================
# P4.2 — Descoberta de dominio HORA: "motos/lojas HORA" -> tabelas hora_*
# =====================================================================

class TestHoraDomainDisambiguation:
    def test_prompt_maps_hora_questions_to_hora_tables(self):
        low = _prompt_text().lower()
        assert "hora_" in low, "system_prompt nao mapeia o dominio HORA para tabelas hora_*"
        assert ("lojas hora" in low) or ("motos hora" in low)

    def test_hora_domain_is_in_domain_detection_section(self):
        # A desambiguacao deve viver no <domain_detection> (mesmo lugar de Nacom/CarVia).
        txt = _prompt_text()
        start = txt.find("<domain_detection>")
        end = txt.find("</domain_detection>")
        assert start != -1 and end != -1 and end > start
        bloco = txt[start:end].lower()
        assert "hora" in bloco and "hora_" in bloco
