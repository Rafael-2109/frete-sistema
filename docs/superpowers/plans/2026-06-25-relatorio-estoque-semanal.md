<!-- doc:meta
tipo: how-to
camada: L1
sot_de: —
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-25
-->
# Relatório Semanal de Estoque — Implementation Plan

> **Papel:** plano de implementação task-by-task do relatório semanal de estoque (comparativo segunda-a-segunda, entregue por e-mail toda segunda 8h). Spec par: `docs/superpowers/specs/2026-06-25-relatorio-estoque-semanal-design.md`.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

## Indice
- Goal / Architecture / Tech Stack
- Global Constraints
- Tasks (TDD, task-by-task)

**Goal:** Gerar um relatório semanal de estoque (saldo da segunda anterior vs. segunda atual, com entradas, consumos e ajustes) e entregá-lo por e-mail toda segunda às 8h.

**Architecture:** Camada de cálculo PURA (`estoque_semanal_calc.py`, sem `app`/db) com a régua de datas, a classificação de movimento por grupo e o fechamento da conta; camada de serviço (`estoque_semanal_service.py`) com as queries agregadas em `MovimentacaoEstoque`, a geração do `.xlsx` e o envio por e-mail; um job no scheduler existente, atrás de flag (default OFF). Espelha o padrão já em produção do faturamento diário no Teams.

**Tech Stack:** Python 3.12, Flask 3.1 + SQLAlchemy 2.0, pandas/openpyxl (Excel), APScheduler (job), `EmailSender` SMTP existente, pytest.

## Global Constraints

- Fonte única de dados: `MovimentacaoEstoque` (`app/estoque/models.py`); sempre filtrar `ativo.is_(True)`.
- `qtd_movimentacao` já vem com sinal (positivo entra, negativo sai).
- `tipo_movimentacao` de produção é gravado **com acento**: `'PRODUÇÃO'` e `'CONSUMO'` (aceitar `'PRODUCAO'` também por robustez).
- Datas: usar `agora_utc_naive()` de `app.utils.timezone` (convenção Brasil-naive do projeto). `data_movimentacao` é `date`.
- Camada `*_calc.py` NÃO importa nada de `app` (regra do projeto, espelha `relatorios_semanais_calc.py`).
- Classificação em grupos reusa `classificar_aba(cod, tipo_materia_prima, contexto='rel2')` de `app/manufatura/services/relatorios_semanais_calc.py` (`1+MP→MP_EXCLUIDO`, `1→INSUMOS`, `2→EMBALAGENS`, `4→PRODUTO_ACABADO`, resto→`OUTROS`).
- Unificação de códigos reusa `colapsar_por_unificacao(valores, mapa)` do mesmo módulo.
- Régua de datas (saldo de abertura): `estoque0 = SUM(qtd) WHERE data < seg_anterior`; `estoque_hoje = SUM(qtd) WHERE data < seg_atual`; período = `seg_anterior <= data < seg_atual`. Garante `estoque0 + entradas − consumos + outros == estoque_hoje`.
- Saldo **sem piso 0** (estoque negativo exibido como está — senão a conta não fecha).
- Flag de ativação `ESTOQUE_SEMANAL_EMAIL_ENABLED` (default `false`); `ESTOQUE_SEMANAL_EMAIL_TO` (csv, default `""`); `ESTOQUE_SEMANAL_EMAIL_HOUR` (default `8`). Job nunca derruba o scheduler.

---

## File Structure

- **Create** `app/manufatura/services/estoque_semanal_calc.py` — cálculo puro: `semanas_referencia`, `classificar_movimento`, `montar_abas`.
- **Create** `app/manufatura/services/estoque_semanal_service.py` — queries + Excel + `enviar_estoque_semanal_email`.
- **Modify** `app/scheduler/sincronizacao_incremental_definitiva.py` — `executar_estoque_semanal_email()` + `add_job` cron segunda.
- **Create** `tests/manufatura/test_estoque_semanal_calc.py` — testes da camada pura.
- **Create** `tests/manufatura/test_estoque_semanal_service.py` — geração de `.xlsx` + `dry_run`.
- **Modify** `app/manufatura/escopo.md` — documentar o novo relatório e as env vars.

---

### Task 1: Camada de cálculo pura (`estoque_semanal_calc.py`)

**Files:**
- Create: `app/manufatura/services/estoque_semanal_calc.py`
- Test: `tests/manufatura/test_estoque_semanal_calc.py`

**Interfaces:**
- Consumes: `classificar_aba`, `colapsar_por_unificacao` de `app.manufatura.services.relatorios_semanais_calc`.
- Produces:
  - `semanas_referencia(hoje: date) -> tuple[date, date]` → `(seg_anterior, seg_atual)`.
  - `classificar_movimento(grupo: str, tipo_mov: str, local_mov: str) -> str` → `'ENTRADA' | 'CONSUMO' | 'OUTRO'`.
  - `montar_abas(estoque0: dict[str,float], estoque_hoje: dict[str,float], movimentos: list[tuple[str,str,str,float]], cadastro: dict[str,dict[str,str]], mapa_unif: dict[str,str]) -> dict[str, list[dict]]`.

- [ ] **Step 1: Write the failing test** (`tests/manufatura/test_estoque_semanal_calc.py`)

```python
from datetime import date
from app.manufatura.services.estoque_semanal_calc import (
    semanas_referencia, classificar_movimento, montar_abas,
)


def test_semanas_referencia_normaliza_para_segunda():
    # Quarta 25/06/2026 -> seg_atual = 22/06, seg_anterior = 15/06
    seg_ant, seg_atual = semanas_referencia(date(2026, 6, 25))
    assert seg_atual == date(2026, 6, 22)
    assert seg_ant == date(2026, 6, 15)


def test_semanas_referencia_em_segunda():
    seg_ant, seg_atual = semanas_referencia(date(2026, 6, 22))
    assert seg_atual == date(2026, 6, 22)
    assert seg_ant == date(2026, 6, 15)


def test_classificar_movimento_componente():
    assert classificar_movimento("INSUMOS", "ENTRADA", "COMPRA") == "ENTRADA"
    assert classificar_movimento("EMBALAGENS", "CONSUMO", "PRODUCAO") == "CONSUMO"
    assert classificar_movimento("INSUMOS", "AJUSTE", "AJUSTE") == "OUTRO"
    # venda de insumo não é o "consumo" do grupo -> OUTRO
    assert classificar_movimento("INSUMOS", "SAIDA", "VENDA") == "OUTRO"


def test_classificar_movimento_produto_acabado():
    assert classificar_movimento("PRODUTO_ACABADO", "PRODUÇÃO", "PRODUCAO") == "ENTRADA"
    assert classificar_movimento("PRODUTO_ACABADO", "PRODUCAO", "PRODUCAO") == "ENTRADA"
    assert classificar_movimento("PRODUTO_ACABADO", "SAIDA", "VENDA") == "CONSUMO"
    assert classificar_movimento("PRODUTO_ACABADO", "ENTRADA", "DEVOLUCAO") == "OUTRO"


def test_montar_abas_fecha_a_conta_e_classifica():
    cadastro = {
        "1001": {"nome_produto": "Palmito granel", "tipo_materia_prima": "", "categoria": "Insumo", "embalagem": ""},
        "2001": {"nome_produto": "Tampa", "tipo_materia_prima": "", "categoria": "", "embalagem": "Tampa"},
        "4001": {"nome_produto": "Conserva 300g", "tipo_materia_prima": "", "categoria": "PA", "embalagem": ""},
    }
    estoque0 = {"1001": 1000.0, "2001": 5000.0, "4001": 200.0}
    estoque_hoje = {"1001": 1050.0, "2001": 5000.0, "4001": 150.0}
    # (cod, tipo, local, soma_qtd) — soma já com sinal
    movimentos = [
        ("1001", "ENTRADA", "COMPRA", 800.0),     # entrada insumo
        ("1001", "CONSUMO", "PRODUCAO", -750.0),   # consumo insumo
        ("2001", "ENTRADA", "COMPRA", 2000.0),
        ("2001", "CONSUMO", "PRODUCAO", -1800.0),
        ("2001", "AJUSTE", "AJUSTE", -200.0),      # outros
        ("4001", "PRODUÇÃO", "PRODUCAO", 100.0),   # entrada PA = produção
        ("4001", "SAIDA", "VENDA", -150.0),        # saída PA = venda
    ]
    abas = montar_abas(estoque0, estoque_hoje, movimentos, cadastro, {})

    insumo = next(l for l in abas["Insumos"] if l["cod_produto"] == "1001")
    assert insumo["estoque_seg_anterior"] == 1000.0
    assert insumo["entradas"] == 800.0
    assert insumo["consumos"] == 750.0          # exibido positivo
    assert insumo["outros_ajustes"] == 0.0
    assert insumo["estoque_seg_atual"] == 1050.0
    # fechamento: 1000 + 800 - 750 + 0 == 1050
    assert (insumo["estoque_seg_anterior"] + insumo["entradas"]
            - insumo["consumos"] + insumo["outros_ajustes"]
            == insumo["estoque_seg_atual"])

    emb = next(l for l in abas["Embalagens"] if l["cod_produto"] == "2001")
    assert emb["outros_ajustes"] == -200.0       # ajuste cai em outros
    assert (emb["estoque_seg_anterior"] + emb["entradas"]
            - emb["consumos"] + emb["outros_ajustes"] == emb["estoque_seg_atual"])

    pa = next(l for l in abas["Produto_Acabado"] if l["cod_produto"] == "4001")
    assert pa["entradas"] == 100.0               # produção
    assert pa["consumos"] == 150.0               # venda, exibida positiva
    assert (pa["estoque_seg_anterior"] + pa["entradas"]
            - pa["consumos"] + pa["outros_ajustes"] == pa["estoque_seg_atual"])


def test_montar_abas_ignora_produto_zerado_sem_movimento():
    cadastro = {"1001": {"nome_produto": "X", "tipo_materia_prima": "", "categoria": "", "embalagem": ""}}
    abas = montar_abas({"1001": 0.0}, {"1001": 0.0}, [], cadastro, {})
    assert abas["Insumos"] == []


def test_montar_abas_exibe_estoque_negativo_sem_piso():
    cadastro = {"1001": {"nome_produto": "X", "tipo_materia_prima": "", "categoria": "", "embalagem": ""}}
    abas = montar_abas({"1001": -50.0}, {"1001": -30.0},
                       [("1001", "ENTRADA", "COMPRA", 20.0)], cadastro, {})
    linha = abas["Insumos"][0]
    assert linha["estoque_seg_anterior"] == -50.0
    assert linha["estoque_seg_atual"] == -30.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/manufatura/test_estoque_semanal_calc.py -v`
Expected: FAIL com `ModuleNotFoundError: app.manufatura.services.estoque_semanal_calc`.

- [ ] **Step 3: Write minimal implementation** (`app/manufatura/services/estoque_semanal_calc.py`)

```python
"""
Núcleo de cálculo PURO do Relatório Semanal de Estoque.

NÃO importa banco/app context/rede (apenas regras determinísticas), no mesmo
espírito de `relatorios_semanais_calc.py`. A orquestração (queries/Excel/e-mail)
vive em `estoque_semanal_service.py`.

Régua de datas (saldo de abertura):
  estoque0     = saldo até < seg_anterior
  estoque_hoje = saldo até < seg_atual
  período      = seg_anterior <= data < seg_atual
Garante por construção: estoque0 + entradas - consumos + outros == estoque_hoje.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Tuple

from app.manufatura.services.relatorios_semanais_calc import (
    classificar_aba,
    colapsar_por_unificacao,
)

# Sentido das colunas "Entradas"/"Consumos" por grupo.
_GRUPOS_COMPONENTE = ("INSUMOS", "EMBALAGENS")
_TIPOS_PRODUCAO = ("PRODUÇÃO", "PRODUCAO")  # gravado com acento; aceita ambos

# Aba de destino por classificação (MP_EXCLUIDO é descartado).
_ABA_POR_GRUPO = {
    "INSUMOS": "Insumos",
    "EMBALAGENS": "Embalagens",
    "PRODUTO_ACABADO": "Produto_Acabado",
    "OUTROS": "Outros",
}


def semanas_referencia(hoje: date) -> Tuple[date, date]:
    """(seg_anterior, seg_atual). Normaliza `hoje` para a segunda da semana."""
    seg_atual = hoje - timedelta(days=hoje.weekday())  # weekday(): seg=0
    seg_anterior = seg_atual - timedelta(days=7)
    return seg_anterior, seg_atual


def classificar_movimento(grupo: str, tipo_mov: str, local_mov: str) -> str:
    """'ENTRADA' | 'CONSUMO' | 'OUTRO' conforme o sentido do grupo."""
    t = (tipo_mov or "").strip().upper()
    l = (local_mov or "").strip().upper()
    if grupo in _GRUPOS_COMPONENTE:
        if t == "ENTRADA" and l == "COMPRA":
            return "ENTRADA"
        if t == "CONSUMO":
            return "CONSUMO"
        return "OUTRO"
    if grupo == "PRODUTO_ACABADO":
        if t in _TIPOS_PRODUCAO:
            return "ENTRADA"
        if t == "SAIDA" and l == "VENDA":
            return "CONSUMO"
        return "OUTRO"
    return "OUTRO"


def _round(v: float) -> float:
    return round(float(v or 0.0), 3)


def montar_abas(
    estoque0: Dict[str, float],
    estoque_hoje: Dict[str, float],
    movimentos: List[Tuple[str, str, str, float]],
    cadastro: Dict[str, Dict[str, str]],
    mapa_unif: Dict[str, str],
) -> Dict[str, List[Dict[str, Any]]]:
    """Monta as abas do relatório semanal a partir de dados já agregados."""
    estoque0 = colapsar_por_unificacao(estoque0, mapa_unif)
    estoque_hoje = colapsar_por_unificacao(estoque_hoje, mapa_unif)

    # entradas/consumos exibidos positivos, por código canônico
    entradas: Dict[str, float] = {}
    consumos: Dict[str, float] = {}
    for cod, tipo_mov, local_mov, qtd in movimentos:
        canon = mapa_unif.get(str(cod), str(cod))
        cad = cadastro.get(canon) or cadastro.get(str(cod)) or {}
        grupo = classificar_aba(canon, cad.get("tipo_materia_prima"), contexto="rel2")
        classe = classificar_movimento(grupo, tipo_mov, local_mov)
        if classe == "ENTRADA":
            entradas[canon] = entradas.get(canon, 0.0) + float(qtd)
        elif classe == "CONSUMO":
            consumos[canon] = consumos.get(canon, 0.0) - float(qtd)  # qtd é negativo -> positivo

    universo = set(estoque0) | set(estoque_hoje) | set(entradas) | set(consumos)
    abas: Dict[str, List[Dict[str, Any]]] = {
        "Insumos": [], "Embalagens": [], "Produto_Acabado": [], "Outros": []
    }
    for cod in sorted(universo):
        e0 = float(estoque0.get(cod, 0.0))
        e1 = float(estoque_hoje.get(cod, 0.0))
        ent = float(entradas.get(cod, 0.0))
        con = float(consumos.get(cod, 0.0))
        if e0 == 0 and e1 == 0 and ent == 0 and con == 0:
            continue  # zerado e sem movimento: não polui
        cad = cadastro.get(cod, {})
        grupo = classificar_aba(cod, cad.get("tipo_materia_prima"), contexto="rel2")
        if grupo == "MP_EXCLUIDO":
            continue
        destino = _ABA_POR_GRUPO.get(grupo, "Outros")
        outros = (e1 - e0) - ent + con  # fecha a conta por construção
        abas[destino].append({
            "cod_produto": cod,
            "nome_produto": cad.get("nome_produto", ""),
            "categoria": cad.get("categoria", ""),
            "estoque_seg_anterior": _round(e0),
            "entradas": _round(ent),
            "consumos": _round(con),
            "outros_ajustes": _round(outros),
            "estoque_seg_atual": _round(e1),
        })
    return abas
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/manufatura/test_estoque_semanal_calc.py -v`
Expected: PASS (todos).

- [ ] **Step 5: Commit**

```bash
git add app/manufatura/services/estoque_semanal_calc.py tests/manufatura/test_estoque_semanal_calc.py
git commit -m "feat(manufatura): calculo puro do relatorio semanal de estoque (regua datas + fechamento)"
```

---

### Task 2: Serviço (queries + Excel + e-mail) (`estoque_semanal_service.py`)

**Files:**
- Create: `app/manufatura/services/estoque_semanal_service.py`
- Test: `tests/manufatura/test_estoque_semanal_service.py`

**Interfaces:**
- Consumes: `montar_abas`, `semanas_referencia` (Task 1); `MovimentacaoEstoque` (`app.estoque.models`); `CadastroPalletizacao` (`app.producao.models`); `UnificacaoCodigos` (`app.estoque.models`); `EmailSender` (`app.notificacoes.email_sender`); `agora_utc_naive` (`app.utils.timezone`).
- Produces:
  - `gerar_planilha_bytes(abas: dict[str, list[dict]], seg_ant: date, seg_atual: date) -> bytes`.
  - `montar_relatorio_semanal() -> tuple[dict, date, date]` → `(abas, seg_ant, seg_atual)`.
  - `enviar_estoque_semanal_email(dry_run: bool = False) -> dict` → `{ok, motivo, ...}`.

- [ ] **Step 1: Write the failing test** (`tests/manufatura/test_estoque_semanal_service.py`)

```python
from datetime import date
import io
import pandas as pd
from app.manufatura.services import estoque_semanal_service as svc


def test_gerar_planilha_bytes_tem_abas_e_rotulos():
    abas = {
        "Insumos": [{
            "cod_produto": "1001", "nome_produto": "Palmito", "categoria": "Insumo",
            "estoque_seg_anterior": 1000.0, "entradas": 800.0, "consumos": 750.0,
            "outros_ajustes": 0.0, "estoque_seg_atual": 1050.0,
        }],
        "Embalagens": [], "Produto_Acabado": [], "Outros": [],
    }
    conteudo = svc.gerar_planilha_bytes(abas, date(2026, 6, 15), date(2026, 6, 22))
    assert isinstance(conteudo, bytes) and len(conteudo) > 0
    xls = pd.ExcelFile(io.BytesIO(conteudo))
    assert "Insumos" in xls.sheet_names
    df = pd.read_excel(xls, "Insumos")
    # rótulo do componente menciona "compra" e "produção"
    cols = " | ".join(df.columns)
    assert "compra" in cols.lower()
    assert "produ" in cols.lower()
    assert df.iloc[0]["Cód"] == 1001 or str(df.iloc[0]["Cód"]) == "1001"


def test_enviar_dry_run_nao_envia(monkeypatch):
    # Injeta dados sem tocar o banco
    monkeypatch.setattr(svc, "montar_relatorio_semanal",
                        lambda: ({"Insumos": [], "Embalagens": [],
                                  "Produto_Acabado": [], "Outros": []},
                                 date(2026, 6, 15), date(2026, 6, 22)))
    chamou = {"send": False}
    def _nao_chamar(*a, **k):
        chamou["send"] = True
    monkeypatch.setattr(svc.EmailSender, "send", _nao_chamar)
    res = svc.enviar_estoque_semanal_email(dry_run=True)
    assert res["ok"] is True
    assert res["motivo"] == "dry_run"
    assert chamou["send"] is False


def test_enviar_sem_destinatario_retorna_erro(monkeypatch):
    monkeypatch.setattr(svc, "montar_relatorio_semanal",
                        lambda: ({"Insumos": [], "Embalagens": [],
                                  "Produto_Acabado": [], "Outros": []},
                                 date(2026, 6, 15), date(2026, 6, 22)))
    monkeypatch.setenv("ESTOQUE_SEMANAL_EMAIL_TO", "")
    res = svc.enviar_estoque_semanal_email(dry_run=False)
    assert res["ok"] is False
    assert res["motivo"] == "sem_destinatario"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/manufatura/test_estoque_semanal_service.py -v`
Expected: FAIL com `AttributeError`/`ImportError` (módulo/funções inexistentes).

- [ ] **Step 3: Write minimal implementation** (`app/manufatura/services/estoque_semanal_service.py`)

```python
"""
Relatório Semanal de Estoque — orquestração (queries + Excel + e-mail).

Gera UM .xlsx (Insumos / Embalagens / Produto_Acabado [/ Outros]) comparando o
saldo da segunda anterior com o da segunda atual, com entradas, consumos e
"outros ajustes". Entregue por e-mail toda segunda às 8h (job no scheduler,
atrás da flag ESTOQUE_SEMANAL_EMAIL_ENABLED). Regras puras em
`estoque_semanal_calc.py`.
"""
from __future__ import annotations

import io
import logging
import os
from datetime import date
from typing import Any, Dict, List, Tuple

import pandas as pd
from sqlalchemy import func

from app import db
from app.utils.timezone import agora_utc_naive
from app.estoque.models import MovimentacaoEstoque, UnificacaoCodigos
from app.producao.models import CadastroPalletizacao
from app.notificacoes.email_sender import EmailSender
from app.manufatura.services.estoque_semanal_calc import (
    semanas_referencia, montar_abas,
)

logger = logging.getLogger(__name__)

ARQUIVO = "estoque_semanal.xlsx"

# Rótulos das colunas de movimento por aba (sentido do grupo).
_ROTULOS = {
    "Insumos": ("Entradas (compras)", "Consumos (produção)"),
    "Embalagens": ("Entradas (compras)", "Consumos (produção)"),
    "Produto_Acabado": ("Entradas (produção)", "Saídas (vendas)"),
    "Outros": ("Entradas", "Consumos/Saídas"),
}


# ---------------------------------------------------------------- queries --
def _saldo_ate(data_limite: date) -> Dict[str, float]:
    rows = (
        db.session.query(
            MovimentacaoEstoque.cod_produto,
            func.sum(MovimentacaoEstoque.qtd_movimentacao),
        )
        .filter(
            MovimentacaoEstoque.ativo.is_(True),
            MovimentacaoEstoque.data_movimentacao < data_limite,
        )
        .group_by(MovimentacaoEstoque.cod_produto)
        .all()
    )
    return {str(c): float(s or 0) for c, s in rows}


def _movimentos_periodo(ini: date, fim: date) -> List[Tuple[str, str, str, float]]:
    rows = (
        db.session.query(
            MovimentacaoEstoque.cod_produto,
            MovimentacaoEstoque.tipo_movimentacao,
            MovimentacaoEstoque.local_movimentacao,
            func.sum(MovimentacaoEstoque.qtd_movimentacao),
        )
        .filter(
            MovimentacaoEstoque.ativo.is_(True),
            MovimentacaoEstoque.data_movimentacao >= ini,
            MovimentacaoEstoque.data_movimentacao < fim,
        )
        .group_by(
            MovimentacaoEstoque.cod_produto,
            MovimentacaoEstoque.tipo_movimentacao,
            MovimentacaoEstoque.local_movimentacao,
        )
        .all()
    )
    return [(str(c), t, l, float(q or 0)) for c, t, l, q in rows]


def _cadastro_map() -> Dict[str, Dict[str, str]]:
    rows = CadastroPalletizacao.query.filter_by(ativo=True).all()
    return {
        str(r.cod_produto): {
            "nome_produto": r.nome_produto or "",
            "categoria": r.categoria_produto or "",
            "tipo_materia_prima": r.tipo_materia_prima or "",
            "embalagem": r.tipo_embalagem or "",
        }
        for r in rows
    }


def _mapa_unificacao() -> Dict[str, str]:
    rows = (
        db.session.query(
            UnificacaoCodigos.codigo_origem, UnificacaoCodigos.codigo_destino
        )
        .filter(UnificacaoCodigos.ativo.is_(True))
        .all()
    )
    return {str(o): str(d) for o, d in rows}


# ---------------------------------------------------------- composição -----
def montar_relatorio_semanal() -> Tuple[Dict[str, List[Dict[str, Any]]], date, date]:
    seg_ant, seg_atual = semanas_referencia(agora_utc_naive().date())
    estoque0 = _saldo_ate(seg_ant)
    estoque_hoje = _saldo_ate(seg_atual)
    movimentos = _movimentos_periodo(seg_ant, seg_atual)
    abas = montar_abas(estoque0, estoque_hoje, movimentos,
                       _cadastro_map(), _mapa_unificacao())
    return abas, seg_ant, seg_atual


# ------------------------------------------------------------------ Excel --
_COLS_ORDEM = [
    "cod_produto", "nome_produto", "categoria",
    "estoque_seg_anterior", "entradas", "consumos",
    "outros_ajustes", "estoque_seg_atual",
]


def gerar_planilha_bytes(abas: Dict[str, List[Dict[str, Any]]],
                         seg_ant: date, seg_atual: date) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        escreveu = False
        for aba in ("Insumos", "Embalagens", "Produto_Acabado", "Outros"):
            linhas = abas.get(aba) or []
            if aba == "Outros" and not linhas:
                continue
            rot_ent, rot_con = _ROTULOS[aba]
            colunas = {
                "cod_produto": "Cód", "nome_produto": "Produto", "categoria": "Categoria",
                "estoque_seg_anterior": f"Estoque seg {seg_ant.strftime('%d/%m')}",
                "entradas": rot_ent, "consumos": rot_con,
                "outros_ajustes": "Outros ajustes",
                "estoque_seg_atual": f"Estoque seg {seg_atual.strftime('%d/%m')}",
            }
            df = pd.DataFrame(linhas, columns=_COLS_ORDEM).rename(columns=colunas)
            df.to_excel(writer, sheet_name=aba[:31], index=False)
            escreveu = True
        if not escreveu:
            pd.DataFrame([]).to_excel(writer, sheet_name="Vazio", index=False)
    return buffer.getvalue()


# ------------------------------------------------------------------ e-mail --
def enviar_estoque_semanal_email(dry_run: bool = False) -> dict:
    abas, seg_ant, seg_atual = montar_relatorio_semanal()
    conteudo = gerar_planilha_bytes(abas, seg_ant, seg_atual)
    periodo = f"{seg_ant.strftime('%d/%m')} a {seg_atual.strftime('%d/%m/%Y')}"
    total_linhas = sum(len(v) for v in abas.values())
    resultado = {"ok": True, "periodo": periodo, "linhas": total_linhas,
                 "dry_run": dry_run, "arquivo": ARQUIVO}

    if dry_run:
        resultado["motivo"] = "dry_run"
        return resultado

    destinos = [e.strip() for e in os.getenv("ESTOQUE_SEMANAL_EMAIL_TO", "").split(",") if e.strip()]
    if not destinos:
        logger.warning("[ESTOQUE-SEMANAL] sem destinatário (ESTOQUE_SEMANAL_EMAIL_TO vazio)")
        return {"ok": False, "motivo": "sem_destinatario", "periodo": periodo}

    sender = EmailSender()
    assunto = f"Relatório semanal de estoque — semana de {periodo}"
    corpo = (
        f"<p>Segue em anexo o relatório semanal de estoque "
        f"(comparativo {periodo}).</p>"
        f"<p>Abas: Insumos, Embalagens e Produto Acabado. "
        f"Colunas: estoque na segunda anterior, entradas, consumos/saídas, "
        f"outros ajustes e estoque na segunda atual.</p>"
    )
    res = sender.send(
        to=destinos[0], subject=assunto, body_html=corpo,
        cc=destinos[1:] or None,
        attachments=[(ARQUIVO, conteudo)],
    )
    resultado["ok"] = bool(res.get("success"))
    resultado["motivo"] = "enviado" if res.get("success") else "falha_envio"
    resultado["email"] = res
    return resultado
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/manufatura/test_estoque_semanal_service.py -v`
Expected: PASS (3 testes).

- [ ] **Step 5: Commit**

```bash
git add app/manufatura/services/estoque_semanal_service.py tests/manufatura/test_estoque_semanal_service.py
git commit -m "feat(manufatura): servico do relatorio semanal de estoque (queries + Excel + e-mail)"
```

---

### Task 3: Job no scheduler (segunda 8h, atrás de flag)

**Files:**
- Modify: `app/scheduler/sincronizacao_incremental_definitiva.py` (função nova após `executar_faturamento_diario_teams`, ~linha 2466; `add_job` no `main()`, após o bloco do faturamento, ~linha 2544).

**Interfaces:**
- Consumes: `enviar_estoque_semanal_email` (Task 2).

- [ ] **Step 1: Adicionar a função do job** (após `executar_faturamento_diario_teams`, antes de `def main()`)

```python
def executar_estoque_semanal_email():
    """Job (segunda): envia por e-mail o relatório semanal de estoque.

    Comparativo segunda anterior vs. atual (entradas/consumos/ajustes), anexo
    .xlsx. Best-effort, NUNCA derruba o scheduler. Atrás da flag
    ESTOQUE_SEMANAL_EMAIL_ENABLED. Mesmo padrão de executar_faturamento_diario_teams
    (cria app por execução + dispose de conexões).
    """
    try:
        from app import create_app, db
        from app.manufatura.services.estoque_semanal_service import (
            enviar_estoque_semanal_email,
        )
        app = create_app()
        with app.app_context():
            try:
                db.session.close()
                db.engine.dispose()
            except Exception:
                pass
            res = enviar_estoque_semanal_email()
            logger.info(f"📦 [ESTOQUE-SEMANAL] {res}")
    except Exception as e:
        logger.error(f"❌ [ESTOQUE-SEMANAL] job falhou: {e}", exc_info=True)
```

- [ ] **Step 2: Registrar o `add_job`** (no `main()`, logo após o bloco `if ... FATURAMENTO_DIARIO_TEAMS_ENABLED ... else ...`, antes de `logger.info("=" * 60)`)

```python
    # Relatorio semanal de estoque por e-mail (segunda 8h). Default OFF ate o
    # Rafael definir destinatario e ativar (flag ESTOQUE_SEMANAL_EMAIL_ENABLED).
    if os.getenv("ESTOQUE_SEMANAL_EMAIL_ENABLED", "false").lower() in ("1", "true", "yes", "on"):
        _est_hour = int(os.getenv("ESTOQUE_SEMANAL_EMAIL_HOUR", "8"))
        scheduler.add_job(
            func=executar_estoque_semanal_email,
            trigger="cron",
            day_of_week="mon",
            hour=_est_hour,
            minute=0,
            id="estoque_semanal_email",
            name="Relatorio semanal de estoque por e-mail (segunda)",
            max_instances=1,
            misfire_grace_time=3600,
            replace_existing=True,
        )
        logger.info(f"   10. Estoque semanal e-mail: segunda às {_est_hour:02d}:00 (ENABLED)")
    else:
        logger.info("   10. Estoque semanal e-mail: DESABILITADO (ESTOQUE_SEMANAL_EMAIL_ENABLED=false)")
```

- [ ] **Step 3: Verificar import (sintaxe)**

Run: `python -c "import ast; ast.parse(open('app/scheduler/sincronizacao_incremental_definitiva.py', encoding='utf-8').read()); print('OK')"`
Expected: `OK`.

- [ ] **Step 4: Smoke test do dry_run com app context**

Run: `python -c "from app import create_app; app=create_app();\nimport app.manufatura.services.estoque_semanal_service as s\nwith app.app_context():\n print(s.enviar_estoque_semanal_email(dry_run=True))"`
Expected: dict com `'ok': True` e `'motivo': 'dry_run'` (usa banco local de teste; valida que as queries rodam sem erro).

- [ ] **Step 5: Commit**

```bash
git add app/scheduler/sincronizacao_incremental_definitiva.py
git commit -m "feat(scheduler): job semanal do relatorio de estoque por e-mail (segunda 8h, flag off)"
```

---

### Task 4: Documentação (env vars + novo relatório)

**Files:**
- Modify: `app/manufatura/escopo.md`

**Interfaces:** nenhuma (documentação).

- [ ] **Step 1: Acrescentar seção ao fim de `app/manufatura/escopo.md`**

```markdown
## Relatório Semanal de Estoque (e-mail, segunda 8h)

Complementa o relatório de "estoques" com a dimensão semanal. Gera
`estoque_semanal.xlsx` (Insumos / Embalagens / Produto_Acabado) comparando o
saldo da segunda anterior com o da segunda atual:

| Coluna | Insumos/Embalagens | Produto Acabado |
|--------|--------------------|-----------------|
| Entradas | recebimento de compra | produção |
| Consumos/Saídas | consumo na produção | vendas |

`Outros ajustes` fecha a conta (`seg0 + entradas − consumos + outros = hoje`).
Fonte: `MovimentacaoEstoque` (`ativo=True`). Código: `estoque_semanal_service.py`
(+ `estoque_semanal_calc.py`). Envio: job no scheduler `executar_estoque_semanal_email`.

**Variáveis de ambiente:**
- `ESTOQUE_SEMANAL_EMAIL_ENABLED` (default `false`) — liga o envio automático.
- `ESTOQUE_SEMANAL_EMAIL_TO` — destinatário(s), separados por vírgula.
- `ESTOQUE_SEMANAL_EMAIL_HOUR` (default `8`) — hora do envio na segunda.
- Reusa `EMAIL_*` (SMTP) já existentes.

Teste manual: `enviar_estoque_semanal_email(dry_run=True)` (gera sem enviar).
```

- [ ] **Step 2: Commit**

```bash
git add app/manufatura/escopo.md
git commit -m "docs(manufatura): documenta relatorio semanal de estoque e env vars"
```

---

## Self-Review

**Spec coverage:**
- §3 decisões (3 grupos, e-mail, destinatário configurável, 8h, coluna outros) → Tasks 1–3 (grupos/colunas no calc; e-mail/flag no service+scheduler). ✓
- §4 modelo de dados (entrada=compra, consumo=produção, PA=produção/venda, acento em PRODUÇÃO) → `classificar_movimento` (Task 1). ✓
- §5 régua de datas + sem piso → `semanas_referencia` + `_saldo_ate(< data)` (Tasks 1–2); teste de negativo. ✓
- §6 sentido por grupo + outros ajustes + universo de linhas → `montar_abas` (Task 1). ✓
- §7 arquitetura (calc puro / service / scheduler / env vars) → Tasks 1–3. ✓
- §8 erros (job best-effort, sem destinatário, e-mail não configurado) → Task 3 try/except + Task 2 `sem_destinatario`. ✓
- §9 testes → Tasks 1–2. ✓
- §10 ativação/teste → Task 4 docs + smoke test Task 3. ✓

**Placeholder scan:** sem TBD/TODO; todo step tem código/comando real. ✓

**Type consistency:** `montar_abas`/`semanas_referencia` mesma assinatura em Task 1 (def) e Task 2 (uso); chaves de linha (`estoque_seg_anterior`, `entradas`, `consumos`, `outros_ajustes`, `estoque_seg_atual`) idênticas entre calc, service (`_COLS_ORDEM`) e testes. `enviar_estoque_semanal_email(dry_run)` idem Task 2/3. ✓
