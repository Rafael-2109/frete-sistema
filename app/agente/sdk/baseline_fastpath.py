"""
Fast-path deterministico do baseline de conciliacao (Marcus, user_id=18).

FASE 1 do plano docs/superpowers/plans/2026-06-06-reducao-custo-agente-fast-path.md.

Quando o usuario pede "atualizar baseline" (pedido TRIVIAL: curto, sem data nem
variacao de formato), o agente NAO precisa do loop LLM (nem Opus nem Sonnet): o
resultado e deterministico (script gerar_baseline.py + tabelas markdown). Este
modulo expoe:

  1. should_intercept_baseline(msg) -> bool   — decide se e o caminho trivial
  2. format_tabela_mes_journal / format_tabela_conciliacoes — tabelas markdown
  3. montar_resposta_baseline(...)            — resposta final (link + total + tabelas)
  4. executar_baseline_fastpath(...)          — orquestra: roda o script + monta resposta

Invariante (R-EXEC-6 do plano): SO o caminho feliz e interceptado. Data passada,
variacao de formato, outro dominio (CarVia), perguntas diagnosticas -> caem no LLM.
Falso NEGATIVO (deixa de economizar) e aceitavel; falso POSITIVO (rouba um caso
que precisa de LLM) e o perigo -> os guards sao conservadores por design.
"""
from __future__ import annotations

import logging
import os
import re

logger = logging.getLogger(__name__)

# Dominio de producao (espelha .claude/skills/exportando-arquivos/scripts/exportar.py:28).
_RENDER_DOMAIN = "https://sistema-fretes.onrender.com"

# ─────────────────────────────────────────────────────────── Detector
# Gatilho: mesma raiz do pattern `atualizar_baseline` do model_router
# (atualizar/atualiza, gerar/gera, rodar/roda) + "baseline".
_BASELINE_TRIGGER = re.compile(
    r"\b(atualizar?|gerar?|rodar?)\s+(o\s+)?baseline\b",
    re.IGNORECASE,
)

# Maximo de palavras para considerar TRIVIAL (proposta do Rafael: <= 4).
_MAX_PALAVRAS = 4

# Tokens que indicam VARIACAO (data, periodo, formato, outro dominio) -> LLM.
_VETO_TOKENS = frozenset({
    "ontem", "anteontem", "passado", "passada", "retroativo", "retroativa",
    "historico", "histórico", "foto", "formato", "layout", "ordem", "coluna",
    "colunas", "carvia", "semana", "mes", "mês", "meses", "ano", "anos",
    "dia", "dias", "data", "datas",
})

# Qualquer digito ou barra = data/numero explicito -> LLM.
_VETO_CHARS = re.compile(r"[\d/]")


def should_intercept_baseline(mensagem: str | None) -> bool:
    """True se a mensagem e um pedido TRIVIAL de baseline (caminho deterministico).

    Conservador por design: na duvida, retorna False (cai no LLM). Ver R-EXEC-6.
    """
    if not mensagem or not str(mensagem).strip():
        return False
    t = str(mensagem).strip().lower()
    if not _BASELINE_TRIGGER.search(t):
        return False
    if len(t.split()) > _MAX_PALAVRAS:
        return False
    if _VETO_CHARS.search(t):
        return False
    if set(re.findall(r"\w+", t, flags=re.UNICODE)) & _VETO_TOKENS:
        return False
    return True


# ─────────────────────────────────────────────────────────── Formatadores
def _mes_ano_sort_key(mes_ano: str):
    """'MM/YYYY' -> (YYYY, MM) para ordenacao cronologica.

    Sort lexicografico em 'MM/YYYY' inverte meses entre anos (espelha a mesma
    regra de gerar_baseline._mes_ano_sort_key — duplicado de proposito para nao
    acoplar este modulo de app/ ao script da skill em .claude/skills/).
    """
    if not mes_ano or "/" not in mes_ano:
        return (0, 0)
    try:
        m, y = mes_ano.split("/")
        return (int(y), int(m))
    except (ValueError, AttributeError):
        return (0, 0)


def format_tabela_mes_journal(agg: dict) -> str:
    """Tabela markdown 'Pendentes Mes x Journal' (resumo da Aba 1 do baseline).

    agg: dict[(mes, journal)] -> {linhas, pgtos, recebs, vl_deb, vl_cred}
    """
    linhas_md = [
        "| Mes | Journal | Linhas | PGTOS | RECEB. |",
        "|-----|---------|-------:|------:|-------:|",
    ]
    tot_l = tot_p = tot_r = 0
    for chave in sorted(agg.keys(), key=lambda k: (_mes_ano_sort_key(k[0]), k[1])):
        mes, journal = chave
        d = agg[chave]
        linhas_md.append(
            f"| {mes} | {journal} | {d['linhas']} | {d['pgtos']} | {d['recebs']} |"
        )
        tot_l += d["linhas"]
        tot_p += d["pgtos"]
        tot_r += d["recebs"]
    linhas_md.append(f"| **TOTAL** |  | **{tot_l}** | **{tot_p}** | **{tot_r}** |")
    return "\n".join(linhas_md)


def format_tabela_conciliacoes(por_usuario: dict, label_data: str) -> str:
    """Tabela markdown de conciliacoes por usuario (D-1 ou D-0).

    por_usuario: dict[nome] -> {linhas, pgtos, recebs, vl_deb, vl_cred}
    label_data: rotulo da data (ex.: '16/04/2026') usado na msg de vazio.
    """
    if not por_usuario:
        return f"Nenhuma conciliacao registrada em {label_data}."
    linhas_md = [
        "| Usuario | Linhas | Pgtos | Rec |",
        "|---------|-------:|------:|----:|",
    ]
    tot_l = tot_p = tot_r = 0
    for nome in sorted(por_usuario.keys(),
                       key=lambda n: por_usuario[n]["linhas"], reverse=True):
        d = por_usuario[nome]
        linhas_md.append(f"| {nome} | {d['linhas']} | {d['pgtos']} | {d['recebs']} |")
        tot_l += d["linhas"]
        tot_p += d["pgtos"]
        tot_r += d["recebs"]
    linhas_md.append(f"| **TOTAL** | **{tot_l}** | **{tot_p}** | **{tot_r}** |")
    return "\n".join(linhas_md)


# ─────────────────────────────────────────────────────────── Montagem da resposta
def montar_resposta_baseline(
    total,
    url,
    data_ref_label: str,
    agg: dict,
    d1: dict,
    d0: dict,
    d1_label: str,
    d0_label: str,
) -> str:
    """Monta a resposta final do fast-path (entrega ATOMICA I7 da SKILL.md).

    Replica a mensagem-template canonica: link + total + Tabela 1 (Mes x Journal)
    + Tabela D-1 + Tabela D-0, tudo numa unica mensagem (a SKILL proibe entregar
    so o link). SEM delta numerico (decisao MVP — analise/variacao caem no LLM).

    Guard de entrega (P7 #787): se `url` for None/vazio (arquivo nao gerou ou veio
    vazio), NAO forja link — reporta os numeros conferidos direto no Odoo.
    """
    partes = []
    if url:
        partes.append(f"Baseline canonico de {data_ref_label} gerado: {url}")
    else:
        partes.append(
            f"Baseline de {data_ref_label} calculado, mas o arquivo Excel ficou "
            "indisponivel (nao gerou ou veio vazio). Numeros abaixo conferidos "
            "direto no Odoo."
        )
    partes.append(f"Total de extratos pendentes: {total}")
    partes.append("")
    partes.append("**Pendentes por Mes x Journal:**")
    partes.append(format_tabela_mes_journal(agg))
    partes.append("")
    partes.append(f"**Conciliacoes em D-1 ({d1_label}) por usuario:**")
    partes.append(format_tabela_conciliacoes(d1, d1_label))
    partes.append("")
    partes.append(f"**Conciliacoes em D-0 ({d0_label}) por usuario:**")
    partes.append(format_tabela_conciliacoes(d0, d0_label))
    if url:
        partes.append("")
        partes.append("Arquivo Excel completo (4 abas) disponivel no link acima.")
    return "\n".join(partes)


# ─────────────────────────────────────────────────────────── Execucao (I/O)
# A logica de I/O abaixo NAO tem pytest (depende de Odoo + DB) — validada por
# spot-check (R-EXEC-1 do plano). A montagem da resposta (montar_resposta_baseline)
# e o detector (should_intercept_baseline) tem cobertura ZERO-DB acima.

_script_module_cache = None


def _find_project_root() -> str:
    """Raiz do projeto via walk-up por app/__init__.py + fallbacks (PROD/dev).

    Espelha gerar_baseline._find_project_root — este modulo esta em
    app/agente/sdk/, entao 3 niveis acima e a raiz.
    """
    candidato = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    if os.path.isfile(os.path.join(candidato, "app", "__init__.py")):
        return candidato
    atual = os.path.abspath(os.getcwd())
    while atual and atual != "/":
        if os.path.isfile(os.path.join(atual, "app", "__init__.py")):
            return atual
        atual = os.path.dirname(atual)
    for fb in ("/opt/render/project/src", "/home/rafaelnascimento/projetos/frete_sistema"):
        if os.path.isfile(os.path.join(fb, "app", "__init__.py")):
            return fb
    raise RuntimeError("Nao foi possivel localizar a raiz do projeto (app/__init__.py).")


def _carregar_script_baseline():
    """Importa gerar_baseline.py (script da skill) via importlib, com cache.

    O script vive em .claude/skills/ (fora do package app) — nao e importavel por
    caminho normal. Cache evita re-exec a cada turno.
    """
    global _script_module_cache
    if _script_module_cache is not None:
        return _script_module_cache
    import importlib.util
    caminho = os.path.join(
        _find_project_root(),
        ".claude", "skills", "gerando-baseline-conciliacao", "scripts", "gerar_baseline.py",
    )
    if not os.path.isfile(caminho):
        raise RuntimeError(f"Script de baseline nao encontrado: {caminho}")
    spec = importlib.util.spec_from_file_location("gerar_baseline_runtime", caminho)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _script_module_cache = mod
    return mod


def _baseline_output_dir() -> str:
    """Diretorio servido pelo download do agente.

    Espelha exportar.py.get_upload_folder (pasta 'default', comprovada em PROD com
    /agente/api/files/default/<file>). NAO usar _get_session_folder (inclui user_id
    e diverge do que o exportar.py — e o download — usam). Ver bug #787.
    """
    base = os.path.join(os.environ.get("AGENTE_FILES_ROOT", "/tmp"), "agente_files", "default")
    os.makedirs(base, exist_ok=True)
    return base


def executar_baseline_fastpath(session_id=None, user_id=None) -> dict:
    """Executa o baseline DETERMINISTICAMENTE (sem LLM) e devolve a resposta pronta.

    REQUER um Flask app_context ativo (chamado de dentro de um request Teams/Web).
    NUNCA levanta — encapsula falhas em {ok: False, ...} para o caller cair no LLM
    (fallback R-EXEC-6). Reexecuta sempre (sem cache — alinhado a IMP-2026-05-13-001).

    Returns dict: {ok, resposta, url, total, erro}.
    """
    from datetime import timedelta
    try:
        mod = _carregar_script_baseline()
        dados = mod.gerar_baseline_arquivo(data_ref=None, output_dir=_baseline_output_dir())

        # Guard de ENTREGA (P7 #787): so vira link se o arquivo existe e e nao-vazio.
        filepath = dados.get("output_file")
        url = None
        if filepath and os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            url = f"{_RENDER_DOMAIN}/agente/api/files/default/{os.path.basename(filepath)}"

        data_ref = dados["data_ref"]
        d0_label = data_ref.strftime("%d/%m/%Y")
        d1_label = (data_ref - timedelta(days=1)).strftime("%d/%m/%Y")
        resposta = montar_resposta_baseline(
            total=dados["total"], url=url, data_ref_label=d0_label,
            agg=dados["agg"], d1=dados["d1"], d0=dados["d0"],
            d1_label=d1_label, d0_label=d0_label,
        )
        logger.info(
            f"[BASELINE_FASTPATH] OK user={user_id} session={str(session_id)[:12]} "
            f"total={dados['total']} url={'sim' if url else 'nao'}"
        )
        return {"ok": True, "resposta": resposta, "url": url,
                "total": dados["total"], "erro": None}
    except Exception as e:
        logger.warning(
            f"[BASELINE_FASTPATH] falha (fallback ao LLM) user={user_id}: {e}",
            exc_info=True,
        )
        return {"ok": False, "resposta": None, "url": None, "total": None, "erro": str(e)}
