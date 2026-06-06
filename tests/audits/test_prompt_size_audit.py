"""
Testes determinísticos do gatilho de poda do prompt (FASE 5 — governança).

Cobre a régua do plano docs/superpowers/plans/2026-06-04-refactor-governanca-prompt-agente.md:
- T5.1: comparar_delta bloqueia crescimento do system_prompt / total vs baseline.
- T5.2: bloco_md + atualizar_bloco_marcado mantêm a doc auto-medida (nunca diverge).

Sem DB, sem app context — puro filesystem (tmp_path) e funções puras.
Padrão do projeto: carrega o script via importlib (cobertura de script sem pacote).
"""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/audits/prompt_size_audit.py"


def _carregar_modulo():
    spec = importlib.util.spec_from_file_location("prompt_size_audit", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mod = _carregar_modulo()


def _snap(system_linhas, total_linhas, total_bytes=1000):
    """Snapshot sintético mínimo no formato esperado por comparar_delta."""
    return {
        "arquivos": {
            "system_prompt.md": {"linhas": system_linhas, "bytes": 100, "tokens": 28},
        },
        "total": {"linhas": total_linhas, "bytes": total_bytes, "tokens": 285},
    }


# ----------------------------------------------------------------- T5.1 snapshot

def test_snapshot_conta_linhas_e_bytes(tmp_path):
    a = tmp_path / "a.md"
    a.write_text("um\ndois\ntres\n", encoding="utf-8")  # 3 linhas
    b = tmp_path / "b.md"
    b.write_text("x\ny\n", encoding="utf-8")  # 2 linhas
    snap = mod.snapshot([("a.md", a), ("b.md", b)])
    assert snap["arquivos"]["a.md"]["linhas"] == 3
    assert snap["arquivos"]["b.md"]["linhas"] == 2
    assert snap["total"]["linhas"] == 5
    assert snap["total"]["bytes"] == a.stat().st_size + b.stat().st_size


def test_snapshot_arquivo_ausente_nao_quebra(tmp_path):
    a = tmp_path / "a.md"
    a.write_text("um\n", encoding="utf-8")
    falta = tmp_path / "naoexiste.md"
    snap = mod.snapshot([("a.md", a), ("naoexiste.md", falta)])
    assert snap["arquivos"]["a.md"]["linhas"] == 1
    assert snap["total"]["linhas"] == 1  # ausente não conta


# -------------------------------------------------------------- T5.1 comparar_delta

def test_comparar_delta_igual_ok():
    base = _snap(system_linhas=765, total_linhas=963)
    ok, msgs = mod.comparar_delta(base, base)
    assert ok is True
    assert msgs == []


def test_comparar_delta_system_prompt_cresceu_bloqueia():
    base = _snap(system_linhas=765, total_linhas=963)
    atual = _snap(system_linhas=780, total_linhas=978)
    ok, msgs = mod.comparar_delta(atual, base)
    assert ok is False
    assert any("system_prompt.md" in m for m in msgs)


def test_comparar_delta_total_cresceu_bloqueia():
    base = _snap(system_linhas=765, total_linhas=963)
    # system_prompt estável, mas outro arquivo inchou o total
    atual = _snap(system_linhas=765, total_linhas=985)
    ok, msgs = mod.comparar_delta(atual, base)
    assert ok is False
    assert any("total" in m.lower() for m in msgs)


def test_comparar_delta_reducao_sempre_ok():
    base = _snap(system_linhas=765, total_linhas=963)
    atual = _snap(system_linhas=700, total_linhas=900)  # podou
    ok, msgs = mod.comparar_delta(atual, base)
    assert ok is True
    assert msgs == []


# ------------------------------------------------------------- T5.1 baseline I/O

def test_baseline_roundtrip(tmp_path):
    p = tmp_path / "baseline.json"
    snap = _snap(system_linhas=765, total_linhas=963)
    mod.salvar_baseline(p, snap)
    carregado = mod.carregar_baseline(p)
    assert carregado["arquivos"]["system_prompt.md"]["linhas"] == 765
    assert carregado["total"]["linhas"] == 963


def test_carregar_baseline_ausente_retorna_none(tmp_path):
    assert mod.carregar_baseline(tmp_path / "naoexiste.json") is None


# ----------------------------------------------------------- T5.2 doc auto-medida

def test_atualizar_bloco_marcado_substitui_miolo():
    ini = "<!-- prompt-size:start -->"
    fim = "<!-- prompt-size:end -->"
    texto = f"antes\n{ini}\nNUMERO VELHO\n{fim}\ndepois\n"
    novo = mod.atualizar_bloco_marcado(texto, "NUMERO NOVO", ini, fim)
    assert "NUMERO NOVO" in novo
    assert "NUMERO VELHO" not in novo
    assert novo.startswith("antes\n")
    assert novo.rstrip().endswith("depois")
    # marcadores preservados (idempotência de re-execução)
    assert ini in novo and fim in novo


def test_atualizar_bloco_marcado_idempotente():
    ini = "<!-- prompt-size:start -->"
    fim = "<!-- prompt-size:end -->"
    texto = f"x\n{ini}\nA\n{fim}\ny\n"
    uma = mod.atualizar_bloco_marcado(texto, "BLOCO", ini, fim)
    duas = mod.atualizar_bloco_marcado(uma, "BLOCO", ini, fim)
    assert uma == duas


def test_atualizar_bloco_marcado_sem_marcador_levanta():
    with pytest.raises(ValueError):
        mod.atualizar_bloco_marcado("sem marcadores aqui", "BLOCO",
                                    "<!-- start -->", "<!-- end -->")
