<!-- doc:meta
tipo: how-to
camada: L3
sot_de: plano fast-path deterministico de vinculacao/desvinculacao NF×PO (Gabriella, Teams) — FASE 3 da reducao de custo do Agente Web
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-08
-->

# Fast-path Vinculação NF×PO (Gabriella) — Implementation Plan

> **Papel:** plano executável e enxuto da **FASE 3** (pendente) da redução de custo do Agente Web — tira a operação repetitiva "vincular/desvincular pedido X na nota Y" (Gabriella, Teams) do caminho caro (subagente `gestor-recebimento` Opus xhigh) resolvendo-a por roteamento determinístico + Haiku de fallback, **reusando as funções de recebimento que já existem**. Origem: avaliação de custo 2026-06-08 (sessão Rafael + Opus 4.8). Princípio do Rafael: SEM over; concluir o item de maior ROI.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

## Indice

- [Resumo](#resumo)
- [Contexto verificado (fontes)](#contexto-verificado-fontes)
- [File Structure](#file-structure)
- [Task 1: Núcleo determinístico de vinculação por NF](#task-1-núcleo-determinístico-de-vinculação-por-nf)
- [Task 2: Detector regex N0](#task-2-detector-regex-n0-should_intercept_vinculacao)
- [Task 3: Camada Haiku N1 + orquestrador](#task-3-camada-haiku-n1-parser-de-fallback--orquestrador)
- [Task 4: Wiring Teams + Web + flag](#task-4-wiring-teams--web--flag)
- [Self-Review](#self-review)

## Resumo

**Goal:** Resolver a operação repetitiva "vincular/desvincular pedido X na nota Y" da Gabriella (Teams) SEM o subagente `gestor-recebimento` (Opus xhigh) no caminho feliz — caindo no LLM apenas quando há anomalia real.

**Architecture:** Roteamento determinístico que REUSA as funções já existentes do recebimento (`validar_dfe` + `consolidar_pos` + `reverter_consolidacao` — que já cobrem exact/split/n_pos via `_detectar_cenario`). Três camadas de custo crescente: **N0** regex extrai `(ação, NF, PO)` → núcleo determinístico (zero LLM); **N1** Haiku faz parse de fallback quando o regex não casa; **N2** o fluxo atual (`gestor-recebimento`) só para anomalias (`status != aprovado`, PO diverge, NF ambígua). Espelha o `baseline_fastpath.py` já em PROD (FASE 1).

**Tech Stack:** Python 3.12, Flask, SQLAlchemy 2.0, `anthropic` 0.98.1 (Haiku `claude-haiku-4-5-20251001`), pytest. Sem novas dependências.

---

## Contexto verificado (fontes)

| Fato | Fonte |
|---|---|
| Match determinístico já existe e retorna `status` ('aprovado'/'bloqueado'/'finalizado_odoo'/'erro') | `app/recebimento/services/validacao_nf_po_service.py:77` (`validar_dfe`) |
| Consolidação (vincular) reusável | `OdooPoService.consolidar_pos(validacao_id, pos_para_consolidar, usuario, quantidades_customizadas)` — chamada em `app/recebimento/routes/validacao_nf_po_routes.py:1361` |
| Montagem de `pos_para_consolidar` a partir dos matches | `validacao_nf_po_routes.py:1316-1354` (a EXTRAIR — Task 1) |
| Reverter (desvincular) reusável | `OdooPoService.reverter_consolidacao(validacao_id, usuario)` — `validacao_nf_po_routes.py:1396` |
| Resolver NF → validação | `ValidacaoNfPoDfe.query.filter_by(numero_nf=...)` (campos `numero_nf`, `odoo_dfe_id`, `status` confirmados no schema) |
| Padrão de wiring do fast-path no Teams | `app/teams/services.py:443-491` (baseline) |
| Padrão de chamada Haiku testável via mock | `app/agente/workers/subagent_validator.py:45-60` (`_call_haiku`) |
| Custo real medido (45d Gabriella/Teams) | ~$269; sessão de hoje $19.84/10 turnos (Sonnet + spawn `gestor-recebimento` Opus) |

**Mensagens reais da Gabriella (PROD, sessão 08/06):**
- `vincular o pedido C2620066 na nota 52019744 no odoo e no frete, validar se tem algum erro e faça o ajuste`
- `Desfazer a vinculação NF 52019744 x C2620066`
- `vincular o pedido C2620094 na nota 6935 no odoo e no frete, validar se tem algum erro e faça o ajuste`

---

## File Structure

| Arquivo | Responsabilidade |
|---|---|
| **Create** `app/recebimento/services/vinculacao_rapida_service.py` | Núcleo determinístico de domínio: resolve NF→validação, orquestra `validar_dfe` + consolidar/reverter, retorna resultado estruturado. NUNCA levanta. |
| **Modify** `app/recebimento/routes/validacao_nf_po_routes.py:1316-1354` | Extrair montagem de POs para `montar_pos_para_consolidar()` no service e chamar (DRY). |
| **Create** `app/agente/sdk/vinculacao_fastpath.py` | Detector regex N0 + parser Haiku N1 + orquestrador `executar_vinculacao_fastpath` (formata resposta, NUNCA levanta). Espelha `baseline_fastpath.py`. |
| **Modify** `app/agente/config/feature_flags.py` | Flag `AGENT_VINCULACAO_FASTPATH` (default ON). |
| **Modify** `app/teams/services.py:443-491` | Wire do novo fast-path ANTES do baseline (mesmo bloco try). |
| **Modify** `app/agente/routes/chat.py` | Wire no caminho Web (espelha baseline). |
| **Create** `tests/recebimento/test_vinculacao_rapida_service.py` | TDD do núcleo (mock dos services). |
| **Create** `tests/agente/test_vinculacao_fastpath.py` | TDD do detector regex + parser Haiku (zero-DB / mock). |

---

## Task 1: Núcleo determinístico de vinculação por NF

**Files:**
- Create: `app/recebimento/services/vinculacao_rapida_service.py`
- Modify: `app/recebimento/routes/validacao_nf_po_routes.py:1316-1366`
- Test: `tests/recebimento/test_vinculacao_rapida_service.py`

**Contrato de retorno** (dict), consumido pela camada de apresentação:
```python
# sucesso (vincular/desvincular):
{"ok": True, "acao": "vincular", "status": "consolidado", "nf": "52019744",
 "po": "C2620066", "resumo": {...}, "anomalia": None}
# já vinculado (idempotente):
{"ok": True, "acao": "vincular", "status": "finalizado_odoo", ...}
# anomalia -> caller decide N1/N2:
{"ok": False, "acao": "vincular", "status": "bloqueado", "nf": "...", "po": "...",
 "anomalia": {"tipo": "status_nao_aprovado"|"po_diverge"|"nf_nao_encontrada"|
              "nf_ambigua"|"erro_execucao", "detalhe": "...", "validacao_id": 123|None}}
```

- [ ] **Step 1: Escrever os testes (contrato)**

```python
# tests/recebimento/test_vinculacao_rapida_service.py
from unittest.mock import patch
from app.recebimento.services import vinculacao_rapida_service as svc


class _Val:
    def __init__(self, id, numero_nf, odoo_dfe_id, status):
        self.id = id; self.numero_nf = numero_nf
        self.odoo_dfe_id = odoo_dfe_id; self.status = status


def test_nf_nao_encontrada():
    with patch.object(svc, "_buscar_validacoes_por_nf", return_value=[]):
        r = svc.executar_vinculacao_por_nf("99999", "C1", "vincular", usuario="bot")
    assert r["ok"] is False and r["anomalia"]["tipo"] == "nf_nao_encontrada"


def test_nf_ambigua():
    vals = [_Val(1, "6935", 10, "aprovado"), _Val(2, "6935", 11, "aprovado")]
    with patch.object(svc, "_buscar_validacoes_por_nf", return_value=vals):
        r = svc.executar_vinculacao_por_nf("6935", None, "vincular", usuario="bot")
    assert r["ok"] is False and r["anomalia"]["tipo"] == "nf_ambigua"


def test_vincular_status_bloqueado_vira_anomalia():
    val = _Val(1, "52019744", 43946, "bloqueado")
    with patch.object(svc, "_buscar_validacoes_por_nf", return_value=[val]), \
         patch.object(svc, "ValidacaoNfPoService") as MV:
        MV.return_value.validar_dfe.return_value = {"status": "bloqueado",
            "itens_match": 0, "itens_total": 2}
        r = svc.executar_vinculacao_por_nf("52019744", "C2620066", "vincular", usuario="bot")
    assert r["ok"] is False and r["anomalia"]["tipo"] == "status_nao_aprovado"


def test_vincular_po_diverge_vira_anomalia():
    val = _Val(1, "52019744", 43946, "aprovado")
    with patch.object(svc, "_buscar_validacoes_por_nf", return_value=[val]), \
         patch.object(svc, "ValidacaoNfPoService") as MV, \
         patch.object(svc, "montar_pos_para_consolidar",
                      return_value=[{"po_id": 5, "po_name": "C9999999", "linhas": [], "valor_total": 1}]):
        MV.return_value.validar_dfe.return_value = {"status": "aprovado"}
        r = svc.executar_vinculacao_por_nf("52019744", "C2620066", "vincular", usuario="bot")
    assert r["ok"] is False and r["anomalia"]["tipo"] == "po_diverge"


def test_vincular_caminho_feliz():
    val = _Val(1, "52019744", 43946, "aprovado")
    with patch.object(svc, "_buscar_validacoes_por_nf", return_value=[val]), \
         patch.object(svc, "ValidacaoNfPoService") as MV, \
         patch.object(svc, "OdooPoService") as MO, \
         patch.object(svc, "montar_pos_para_consolidar",
                      return_value=[{"po_id": 5, "po_name": "C2620066", "linhas": [], "valor_total": 1}]):
        MV.return_value.validar_dfe.return_value = {"status": "aprovado"}
        MO.return_value.consolidar_pos.return_value = {"sucesso": True, "cenario": "exact_1po"}
        r = svc.executar_vinculacao_por_nf("52019744", "c2620066", "vincular", usuario="bot")
    assert r["ok"] is True and r["status"] == "consolidado"
    MO.return_value.consolidar_pos.assert_called_once()


def test_vincular_ja_finalizado_idempotente():
    val = _Val(1, "6935", 44026, "finalizado_odoo")
    with patch.object(svc, "_buscar_validacoes_por_nf", return_value=[val]), \
         patch.object(svc, "ValidacaoNfPoService") as MV:
        MV.return_value.validar_dfe.return_value = {"status": "finalizado_odoo",
            "odoo_po_vinculado_name": "C2620094"}
        r = svc.executar_vinculacao_por_nf("6935", "C2620094", "vincular", usuario="bot")
    assert r["ok"] is True and r["status"] == "finalizado_odoo"


def test_desvincular_caminho_feliz():
    val = _Val(1, "52019744", 43946, "consolidado")
    with patch.object(svc, "_buscar_validacoes_por_nf", return_value=[val]), \
         patch.object(svc, "OdooPoService") as MO:
        MO.return_value.reverter_consolidacao.return_value = {"sucesso": True}
        r = svc.executar_vinculacao_por_nf("52019744", "C2620066", "desvincular", usuario="bot")
    assert r["ok"] is True and r["status"] == "revertido"
    MO.return_value.reverter_consolidacao.assert_called_once()


def test_nunca_levanta_excecao():
    with patch.object(svc, "_buscar_validacoes_por_nf", side_effect=RuntimeError("boom")):
        r = svc.executar_vinculacao_por_nf("1", "C1", "vincular", usuario="bot")
    assert r["ok"] is False and r["anomalia"]["tipo"] == "erro_execucao"
```

- [ ] **Step 2: Rodar os testes — devem FALHAR**

Run: `source .venv/bin/activate && pytest tests/recebimento/test_vinculacao_rapida_service.py -v`
Expected: FAIL (`ModuleNotFoundError: app.recebimento.services.vinculacao_rapida_service`).

- [ ] **Step 3: Extrair `montar_pos_para_consolidar` no novo service**

Mover a lógica de `validacao_nf_po_routes.py:1316-1354` para o service (recebe `validacao_id`, retorna a lista ordenada de POs). Implementar em `vinculacao_rapida_service.py`:

```python
"""Núcleo determinístico de vinculação NF×PO por número de NF (sem LLM).

Reusa o pipeline existente do recebimento (validar_dfe + consolidar_pos +
reverter_consolidacao). NUNCA levanta — encapsula falha em {ok: False, anomalia}.
"""
from __future__ import annotations
import logging
from app import db
from app.recebimento.models import ValidacaoNfPoDfe, MatchNfPoItem
from app.recebimento.services.validacao_nf_po_service import ValidacaoNfPoService
from app.recebimento.services.odoo_po_service import OdooPoService

logger = logging.getLogger(__name__)


def _norm_po(s) -> str:
    return str(s or "").strip().upper()


def _buscar_validacoes_por_nf(numero_nf: str):
    return (ValidacaoNfPoDfe.query
            .filter_by(numero_nf=str(numero_nf).strip())
            .order_by(ValidacaoNfPoDfe.atualizado_em.desc().nullslast())
            .all())


def montar_pos_para_consolidar(validacao_id: int) -> list[dict]:
    """Agrupa MatchNfPoItem('match') por PO e ordena por valor desc.

    Extraído de validacao_nf_po_routes.consolidar_pos (DRY).
    """
    matches = (db.session.query(MatchNfPoItem)
               .filter_by(validacao_id=validacao_id, status_match="match").all())
    pos_dict: dict = {}
    for m in matches:
        if not m.odoo_po_id:
            continue
        d = pos_dict.setdefault(m.odoo_po_id, {
            "po_id": m.odoo_po_id, "po_name": m.odoo_po_name,
            "linhas": [], "valor_total": 0,
        })
        d["linhas"].append({"po_line_id": m.odoo_po_line_id, "qtd_nf": m.qtd_nf,
                            "qtd_po": m.qtd_po, "preco": m.preco_nf})
        d["valor_total"] += (m.qtd_nf or 0) * (m.preco_nf or 0)
    return sorted(pos_dict.values(), key=lambda x: x["valor_total"], reverse=True)
```

- [ ] **Step 4: Implementar `executar_vinculacao_por_nf`**

```python
def executar_vinculacao_por_nf(nf: str, po_esperado: str | None,
                               acao: str, usuario: str | None) -> dict:
    base = {"ok": False, "acao": acao, "nf": str(nf), "po": po_esperado,
            "status": None, "resumo": None, "anomalia": None}
    try:
        vals = _buscar_validacoes_por_nf(nf)
        if not vals:
            base["anomalia"] = {"tipo": "nf_nao_encontrada",
                "detalhe": f"NF {nf} não está na carteira de validação.", "validacao_id": None}
            return base
        if len(vals) > 1 and not po_esperado:
            base["anomalia"] = {"tipo": "nf_ambigua",
                "detalhe": f"{len(vals)} NFs com número {nf}; informe o fornecedor.",
                "validacao_id": None}
            return base
        val = vals[0]
        base["status"] = val.status

        if acao == "desvincular":
            res = OdooPoService().reverter_consolidacao(validacao_id=val.id, usuario=usuario)
            if res.get("sucesso"):
                base.update(ok=True, status="revertido", resumo=res); return base
            base["anomalia"] = {"tipo": "erro_execucao",
                "detalhe": res.get("erro", "reversão falhou"), "validacao_id": val.id}
            return base

        # acao == "vincular": rodar match determinístico
        res = ValidacaoNfPoService().validar_dfe(val.odoo_dfe_id)
        status = res.get("status")
        base["status"] = status
        if status == "finalizado_odoo":
            base.update(ok=True, resumo=res); return base
        if status != "aprovado":
            base["anomalia"] = {"tipo": "status_nao_aprovado", "detalhe": status,
                "validacao_id": val.id, "validacao": res}
            return base

        pos = montar_pos_para_consolidar(val.id)
        po_names = {_norm_po(p["po_name"]) for p in pos}
        if po_esperado and _norm_po(po_esperado) not in po_names:
            base["anomalia"] = {"tipo": "po_diverge",
                "detalhe": f"NF casou com {sorted(po_names)}, não com {po_esperado}.",
                "validacao_id": val.id}
            return base

        cons = OdooPoService().consolidar_pos(
            validacao_id=val.id, pos_para_consolidar=pos,
            usuario=usuario, quantidades_customizadas=None)
        if cons.get("sucesso"):
            base.update(ok=True, status="consolidado", resumo=cons); return base
        base["anomalia"] = {"tipo": "erro_execucao",
            "detalhe": cons.get("erro", "consolidação falhou"), "validacao_id": val.id}
        return base
    except Exception as e:
        logger.warning(f"[VINC-RAPIDA] falha (-> N2) nf={nf} po={po_esperado}: {e}", exc_info=True)
        base["anomalia"] = {"tipo": "erro_execucao", "detalhe": str(e), "validacao_id": None}
        return base
```

- [ ] **Step 5: Refatorar a rota para usar o helper (DRY)**

Em `validacao_nf_po_routes.py`, substituir o bloco 1316-1354 por:
```python
from app.recebimento.services.vinculacao_rapida_service import montar_pos_para_consolidar
pos_para_consolidar = montar_pos_para_consolidar(validacao_id)
if not pos_para_consolidar:
    return jsonify({'sucesso': False, 'erro': 'Nenhum match encontrado para consolidar'}), 400
```
(O `service.consolidar_pos(...)` em 1360-1366 permanece igual.)

- [ ] **Step 6: Rodar os testes — devem PASSAR**

Run: `source .venv/bin/activate && pytest tests/recebimento/test_vinculacao_rapida_service.py -v`
Expected: PASS (8 testes).

- [ ] **Step 7: Regressão da rota**

Run: `source .venv/bin/activate && pytest tests/recebimento/ -q`
Expected: PASS (sem regressão na consolidação existente).

- [ ] **Step 8: Commit**

```bash
git add app/recebimento/services/vinculacao_rapida_service.py \
        app/recebimento/routes/validacao_nf_po_routes.py \
        tests/recebimento/test_vinculacao_rapida_service.py
git commit -m "feat(recebimento): nucleo deterministico vinculacao NF×PO por NF (reusa validar_dfe/consolidar/reverter)"
```

---

## Task 2: Detector regex N0 (`should_intercept_vinculacao`)

**Files:**
- Create: `app/agente/sdk/vinculacao_fastpath.py` (parte 1: detector)
- Test: `tests/agente/test_vinculacao_fastpath.py` (parte 1)

- [ ] **Step 1: Escrever os testes do detector**

```python
# tests/agente/test_vinculacao_fastpath.py
from app.agente.sdk.vinculacao_fastpath import should_intercept_vinculacao as det


def test_vincular_molde_padrao():
    r = det("vincular o pedido C2620066 na nota 52019744 no odoo e no frete, validar se tem algum erro e faça o ajuste")
    assert r == {"acao": "vincular", "po": "C2620066", "nf": "52019744"}


def test_vincular_curto():
    r = det("vincular pedido C2620094 na nota 6935")
    assert r == {"acao": "vincular", "po": "C2620094", "nf": "6935"}


def test_desvincular_molde():
    r = det("Desfazer a vinculação NF 52019744 x C2620066")
    assert r == {"acao": "desvincular", "nf": "52019744", "po": "C2620066"}


def test_cancelar_isolado_nao_casa():
    assert det("cancelar") is None  # ambíguo -> LLM/AskUser


def test_pergunta_diagnostica_nao_casa():
    assert det("por que a nota 6935 está bloqueada?") is None


def test_vazio_nao_casa():
    assert det("") is None and det(None) is None
```

- [ ] **Step 2: Rodar — devem FALHAR**

Run: `source .venv/bin/activate && pytest tests/agente/test_vinculacao_fastpath.py -v`
Expected: FAIL (ImportError).

- [ ] **Step 3: Implementar o detector**

```python
# app/agente/sdk/vinculacao_fastpath.py
"""Fast-path determinístico de vinculação NF×PO (Gabriella, Nicoly).

FASE 3 do plano docs/superpowers/plans/2026-06-06-reducao-custo-agente-fast-path.md
(pendente até 08/06). Espelha baseline_fastpath.py. SÓ o caminho feliz é
interceptado; anomalia (status!=aprovado, PO diverge, NF ambígua) e falha CAEM no
LLM/gestor-recebimento (R-EXEC-6). Conservador: na dúvida, retorna None/ok=False.
"""
from __future__ import annotations
import logging, re
logger = logging.getLogger(__name__)

# "vincular (o) pedido <PO> na nota <NF>"  (PO antes, NF depois)
_RE_VINCULAR = re.compile(
    r"\bvincul\w*\s+(?:o\s+)?pedido\s+(?P<po>[A-Za-z0-9./-]+)\s+n[ao]\s+(?:nota|nf)\s+(?P<nf>\d+)\b",
    re.IGNORECASE)
# "desfazer/desvincular (a vinculação) (NF) <NF> x <PO>"  (NF antes, PO depois)
_RE_DESVINCULAR = re.compile(
    r"\b(?:desvincul\w*|desfaz\w*|desfac\w*)\b.*?\b(?:nota|nf)\s+(?P<nf>\d+)\s*x\s*(?P<po>[A-Za-z0-9./-]+)",
    re.IGNORECASE | re.DOTALL)


def should_intercept_vinculacao(mensagem: str | None) -> dict | None:
    """Retorna {acao, nf, po} se a msg é uma vinculação/desvinculação direta; senão None."""
    if not mensagem or not str(mensagem).strip():
        return None
    t = str(mensagem).strip()
    m = _RE_VINCULAR.search(t)
    if m:
        return {"acao": "vincular", "po": m.group("po"), "nf": m.group("nf")}
    m = _RE_DESVINCULAR.search(t)
    if m:
        return {"acao": "desvincular", "nf": m.group("nf"), "po": m.group("po")}
    return None
```

- [ ] **Step 4: Rodar — devem PASSAR**

Run: `source .venv/bin/activate && pytest tests/agente/test_vinculacao_fastpath.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/agente/sdk/vinculacao_fastpath.py tests/agente/test_vinculacao_fastpath.py
git commit -m "feat(agente): detector regex N0 do fast-path vinculacao NF×PO"
```

---

## Task 3: Camada Haiku N1 (parser de fallback) + orquestrador

**Files:**
- Modify: `app/agente/sdk/vinculacao_fastpath.py` (parte 2: Haiku + `executar_vinculacao_fastpath`)
- Test: `tests/agente/test_vinculacao_fastpath.py` (parte 2)

- [ ] **Step 1: Escrever os testes (parser Haiku + orquestrador)**

```python
# adicionar em tests/agente/test_vinculacao_fastpath.py
from unittest.mock import patch
import app.agente.sdk.vinculacao_fastpath as fp


def test_parse_haiku_extrai_json():
    with patch.object(fp, "_call_haiku", return_value='{"acao":"vincular","nf":"6935","po":"C2620094"}'):
        r = fp.parse_vinculacao_haiku("pode vincular a 6935 com o C2620094?")
    assert r == {"acao": "vincular", "nf": "6935", "po": "C2620094"}


def test_parse_haiku_acao_nula_retorna_none():
    with patch.object(fp, "_call_haiku", return_value='{"acao":null}'):
        assert fp.parse_vinculacao_haiku("bom dia, tudo certo com a nota?") is None


def test_parse_haiku_so_chama_se_keyword_recebimento():
    # sem keyword (nota/nf/pedido/vincul) nao gasta Haiku
    with patch.object(fp, "_call_haiku") as mock:
        assert fp.parse_vinculacao_haiku("qual o estoque de palmito?") is None
        mock.assert_not_called()


def test_orquestrador_caminho_feliz():
    with patch.object(fp, "should_intercept_vinculacao",
                      return_value={"acao": "vincular", "nf": "6935", "po": "C2620094"}), \
         patch.object(fp, "executar_vinculacao_por_nf",
                      return_value={"ok": True, "status": "consolidado", "nf": "6935",
                                    "po": "C2620094", "resumo": {"cenario": "exact_1po"}}):
        r = fp.executar_vinculacao_fastpath("vincular pedido C2620094 na nota 6935",
                                            session_id="s", user_id=69)
    assert r["ok"] is True and "6935" in r["resposta"] and "C2620094" in r["resposta"]


def test_orquestrador_anomalia_cai_no_llm():
    with patch.object(fp, "should_intercept_vinculacao",
                      return_value={"acao": "vincular", "nf": "1", "po": "C1"}), \
         patch.object(fp, "executar_vinculacao_por_nf",
                      return_value={"ok": False, "anomalia": {"tipo": "status_nao_aprovado"}}):
        r = fp.executar_vinculacao_fastpath("vincular pedido C1 na nota 1", session_id="s", user_id=69)
    assert r["ok"] is False  # caller cai no gestor-recebimento (N2)


def test_orquestrador_sem_match_e_sem_haiku_retorna_none():
    with patch.object(fp, "should_intercept_vinculacao", return_value=None), \
         patch.object(fp, "parse_vinculacao_haiku", return_value=None):
        r = fp.executar_vinculacao_fastpath("bom dia", session_id="s", user_id=69)
    assert r is None  # nada a interceptar -> fluxo LLM normal
```

- [ ] **Step 2: Rodar — devem FALHAR**

Run: `source .venv/bin/activate && pytest tests/agente/test_vinculacao_fastpath.py -v`
Expected: FAIL (atributos inexistentes).

- [ ] **Step 3: Implementar Haiku + orquestrador**

Acrescentar em `vinculacao_fastpath.py` (padrão de `subagent_validator.py:45-60`):

```python
import json
HAIKU_MODEL = "claude-haiku-4-5-20251001"
_KW_RECEBIMENTO = re.compile(r"\b(vincul\w*|desvincul\w*|nota|nf|pedido|po)\b", re.IGNORECASE)
_HAIKU_SYSTEM = (
    "Extraia de uma frase de operador de recebimento a ação de vincular/desvincular "
    "uma NOTA FISCAL a um PEDIDO de compra. Responda APENAS JSON: "
    '{"acao":"vincular"|"desvincular"|null,"nf":"<numero>"|null,"po":"<codigo>"|null}. '
    "Se a frase não for um pedido direto de (des)vinculação, retorne {\"acao\":null}.")


def _call_haiku(user_prompt: str) -> str:
    import anthropic
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=HAIKU_MODEL, max_tokens=120, system=_HAIKU_SYSTEM,
        messages=[{"role": "user", "content": user_prompt}])
    return resp.content[0].text if resp.content else ""


def parse_vinculacao_haiku(mensagem: str | None) -> dict | None:
    """Fallback N1: Haiku estrutura (acao, nf, po). Só dispara se houver keyword
    de recebimento (não gasta token em msg fora de domínio)."""
    if not mensagem or not _KW_RECEBIMENTO.search(str(mensagem)):
        return None
    try:
        raw = _call_haiku(str(mensagem))
        data = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
    except Exception as e:
        logger.info(f"[VINC-FASTPATH] Haiku parse falhou (-> LLM): {e}")
        return None
    if data.get("acao") in ("vincular", "desvincular") and data.get("nf") and data.get("po"):
        return {"acao": data["acao"], "nf": str(data["nf"]), "po": str(data["po"])}
    return None


def _montar_resposta(r: dict) -> str:
    acao = "vinculados" if r["acao"] == "vincular" else "desvinculados"
    if r.get("status") == "finalizado_odoo":
        return f"NF {r['nf']} x PO {r['po']} já estavam vinculados no Odoo. Nada a fazer."
    cen = (r.get("resumo") or {}).get("cenario")
    extra = f" (cenário {cen})" if cen else ""
    return f"Feito. NF {r['nf']} x PO {r['po']} {acao}{extra}."


def executar_vinculacao_fastpath(mensagem: str, session_id=None, user_id=None) -> dict | None:
    """Orquestra N0->N1->executor. Retorna:
       - {"ok": True, "resposta": str}  -> caminho feliz (pula LLM)
       - {"ok": False, ...}             -> anomalia (caller cai no gestor-recebimento)
       - None                            -> não é vinculação (fluxo LLM normal)
    NUNCA levanta."""
    try:
        parsed = should_intercept_vinculacao(mensagem) or parse_vinculacao_haiku(mensagem)
        if not parsed:
            return None
        r = executar_vinculacao_por_nf(parsed["nf"], parsed["po"], parsed["acao"],
                                       usuario=f"agente:{user_id}")
        if r["ok"]:
            logger.info(f"[VINC-FASTPATH] OK ({parsed['acao']}) sem subagente user={user_id} nf={parsed['nf']}")
            return {"ok": True, "resposta": _montar_resposta({**r, **parsed})}
        logger.info(f"[VINC-FASTPATH] anomalia {r['anomalia']['tipo']} -> N2 (gestor-recebimento) nf={parsed['nf']}")
        return {"ok": False, "anomalia": r["anomalia"], "parsed": parsed}
    except Exception as e:
        logger.warning(f"[VINC-FASTPATH] falha geral (-> LLM) user={user_id}: {e}", exc_info=True)
        return None


# import no escopo do MÓDULO para os testes mockarem via patch.object(fp, "executar_vinculacao_por_nf", ...)
from app.recebimento.services.vinculacao_rapida_service import executar_vinculacao_por_nf  # noqa: E402
```

> Nota ao executor: os testes fazem `patch.object(fp, "executar_vinculacao_por_nf", ...)` e `patch.object(fp, "should_intercept_vinculacao"/"parse_vinculacao_haiku", ...)`. Por isso o import de `executar_vinculacao_por_nf` fica como atributo do módulo (não import local dentro da função) e o orquestrador chama os 3 pelos nomes do módulo. Rode os testes para confirmar que os mocks pegam.

- [ ] **Step 4: Rodar — devem PASSAR**

Run: `source .venv/bin/activate && pytest tests/agente/test_vinculacao_fastpath.py -v`
Expected: PASS (12 testes).

- [ ] **Step 5: Commit**

```bash
git add app/agente/sdk/vinculacao_fastpath.py tests/agente/test_vinculacao_fastpath.py
git commit -m "feat(agente): camada Haiku N1 (parser fallback) + orquestrador do fast-path vinculacao"
```

---

## Task 4: Wiring Teams + Web + flag

**Files:**
- Modify: `app/agente/config/feature_flags.py`
- Modify: `app/teams/services.py:443-491`
- Modify: `app/agente/routes/chat.py` (espelhar baseline)

- [ ] **Step 1: Flag**

Em `feature_flags.py` (junto de `AGENT_BASELINE_FASTPATH`):
```python
AGENT_VINCULACAO_FASTPATH = os.getenv("AGENT_VINCULACAO_FASTPATH", "true").lower() == "true"
```

- [ ] **Step 2: Wire no Teams (ANTES do baseline, mesmo bloco try em `services.py:449`)**

Inserir antes do bloco `_fp_resposta` do baseline:
```python
_vinc_resposta = None
try:
    from app.agente.config.feature_flags import AGENT_VINCULACAO_FASTPATH
    from app.agente.sdk.vinculacao_fastpath import executar_vinculacao_fastpath
    if AGENT_VINCULACAO_FASTPATH:
        _vinc = executar_vinculacao_fastpath(mensagem, session_id=teams_session_id, user_id=teams_user_id)
        if _vinc and _vinc.get("ok"):
            _vinc_resposta = _vinc["resposta"]
            logger.info(f"[TEAMS-BOT] vinculacao fast-path (sem subagente) user={teams_user_id}")
        # _vinc com ok=False (anomalia) ou None -> segue p/ baseline/LLM (N2)
except Exception as _ve:
    logger.warning(f"[TEAMS-BOT] fast-path vinculacao ignorado (-> LLM): {_ve}")

if _vinc_resposta is not None:
    selected_model = 'fastpath-vinculacao'
    _sync_result = _error_stream_result(resposta_texto=_vinc_resposta, sdk_session_id=sdk_session_id)
else:
    # ... bloco baseline existente (linha 449+) inalterado ...
```
Atenção (R10/R5 do Teams CLAUDE.md): manter a persistência/cleanup do `finally` existente — o StreamResult sintético reusa o mesmo caminho do baseline. NÃO duplicar persistência.

- [ ] **Step 3: Wire no Web (`chat.py`, molde do baseline)**

Localizar o ponto onde o baseline é interceptado em `routes/chat.py` (`should_intercept_baseline`/`executar_baseline_fastpath`) e adicionar a interceptação de vinculação imediatamente antes, com a MESMA mecânica (short-circuit stream sintético + persistência só se a sessão já existe). Reusar `executar_vinculacao_fastpath(mensagem, session_id, user_id)`; se `ok` → responder sem LLM; senão → fluxo normal.

- [ ] **Step 4: Regressão dirigida**

Run: `source .venv/bin/activate && pytest tests/agente/ tests/recebimento/ -q`
Expected: PASS.

- [ ] **Step 5: Smoke manual em PROD (R-EXEC-1, igual baseline — sem pytest p/ I/O Odoo)**

Pelo Teams (ou Playwright local), com a conta de teste:
1. `vincular pedido <PO_real> na nota <NF_real>` → conferir resposta "Feito..." e verificar no Odoo (`dfe_id`/`purchase_id`) + `validacao_nf_po_dfe.status='consolidado'`.
2. `Desfazer a vinculação NF <NF> x <PO>` → conferir reversão no Odoo.
3. Uma NF bloqueada (sem De-Para) → confirmar que NÃO intercepta e cai no `gestor-recebimento`.
Conferir logs `[VINC-FASTPATH]` e que a sessão registra `model=fastpath-vinculacao` no caso feliz.

- [ ] **Step 6: Commit**

```bash
git add app/agente/config/feature_flags.py app/teams/services.py app/agente/routes/chat.py
git commit -m "feat(agente): wire fast-path vinculacao NF×PO no Teams+Web (flag AGENT_VINCULACAO_FASTPATH)"
```

---

## Self-Review

- **Cobertura:** N0 (Task 2) + N1 (Task 3) + executor determinístico reusando funções existentes (Task 1) + wiring/flag (Task 4). Anomalia cai no `gestor-recebimento` atual (N2) — sem regressão.
- **Reuso (correção do Rafael):** zero reimplementação de cenário — `validar_dfe`/`consolidar_pos`/`reverter_consolidacao` cobrem exact/split/n_pos. Montagem de POs extraída e compartilhada com a rota (DRY).
- **Segurança WRITE:** caminho feliz só executa com `status=aprovado` + PO confirmado; NF ambígua, PO divergente e bloqueio caem no LLM. `consolidar_pos` já tem guard de idempotência.
- **Consistência de tipos:** `executar_vinculacao_por_nf` retorna sempre o dict com chaves `ok`/`acao`/`nf`/`po`/`status`/`resumo`/`anomalia`; `executar_vinculacao_fastpath` retorna `{ok,resposta}` | `{ok:False,anomalia,parsed}` | `None`.
- **Gotcha de mock (Task 3 Step 3):** `executar_vinculacao_por_nf`, `should_intercept_vinculacao` e `parse_vinculacao_haiku` são atributos do módulo `fp` e chamados por esse nome — validar rodando os testes.
- **Pendência consciente:** medir economia real pós-deploy (sessões `model=fastpath-vinculacao` vs baseline F0) entra como verificação, não como nova fase.
