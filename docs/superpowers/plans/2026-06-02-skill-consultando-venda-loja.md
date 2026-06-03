# Skill `consultando-venda-loja` — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Criar a skill READ `consultando-venda-loja` para o Agente Lojas HORA consultar vendas, validar preço/desconto e ver margem — respeitando escopo de loja, sem WRITE.

**Architecture:** 1 skill, 1 script com `--modo {vendas|preco|margem}`. `vendas` = SQL bruto sobre `hora_venda`/`_item`/`_divergencia`/`hora_tagplus_nfe_emissao`. `preco`/`margem` reusam services de `app/hora` (sem reimplementar fórmula). Um wrapper público novo em `venda_service` desacopla a validação de desconto. pytest determinístico (mock services, zero DB/PROD).

**Tech Stack:** Python 3.12, Flask app factory (`create_app`), SQLAlchemy 2.0 (raw `text()`), pytest + unittest.mock. Padrão do cluster HORA (`acompanhando_pedido.py`).

**Spec:** `docs/superpowers/specs/2026-06-02-skill-consultando-venda-loja-design.md`

---

## File Structure

| Arquivo | Responsabilidade | Ação |
|---|---|---|
| `app/hora/services/venda_service.py` | + `validar_desconto_tabela()` público (delega a `_resolver_preco_tabela`) | Modify (~L470) |
| `.claude/skills/consultando-venda-loja/scripts/consultando_venda_loja.py` | Script da skill (3 modos) | Create |
| `.claude/skills/consultando-venda-loja/SKILL.md` | Doc/description da skill | Create |
| `tests/hora/test_validar_desconto_tabela.py` | Teste do wrapper | Create |
| `tests/skills/consultando_venda_loja/test_consultando_venda_loja.py` | Testes do script (3 modos, mock) | Create |
| `app/agente_lojas/config/skills_whitelist.py` | Habilitar skill no agente Lojas | Modify (L22) |
| `app/agente_lojas/prompts/system_prompt.md` | Atualizar linha da skill | Modify (L60) |
| `.claude/skills/consultando-estoque-loja/SKILL.md` | Corrigir refs `registrando-venda` | Modify (L21,L44) |
| `.claude/references/ROUTING_SKILLS.md` | Roteamento + inventário cluster HORA | Modify (~L43, L210) |
| `app/agente/services/tool_skill_mapper.py` | Categoria de telemetria | Modify (~L163) |

**Convenção de comando** (todos os passos rodam da raiz do worktree):
`PY=/home/rafaelnascimento/projetos/frete_sistema/.venv/bin/python` (worktree não tem venv próprio).

---

### Task 1: Wrapper público `validar_desconto_tabela` em `venda_service`

**Files:**
- Modify: `app/hora/services/venda_service.py` (imports no topo + função após `_resolver_preco_tabela`, ~L470)
- Test: `tests/hora/test_validar_desconto_tabela.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/hora/test_validar_desconto_tabela.py
"""Teste do wrapper publico validar_desconto_tabela (Onda F)."""
import datetime
from decimal import Decimal
from unittest.mock import patch

from app.hora.services import venda_service


def test_delega_a_resolver_e_mapeia_para_dict():
    with patch.object(
        venda_service, "_resolver_preco_tabela",
        return_value=(Decimal("12990.00"), Decimal("990.00"), Decimal("7.62"), 5, False),
    ) as m:
        res = venda_service.validar_desconto_tabela(
            10, Decimal("12000.00"), "A_VISTA", na_data=datetime.date(2026, 6, 2)
        )
    assert res == {
        "modelo_id": 10,
        "preco_referencia": Decimal("12990.00"),
        "desconto_rs": Decimal("990.00"),
        "desconto_pct": Decimal("7.62"),
        "tabela_id": 5,
        "divergencia": False,
    }
    m.assert_called_once_with(10, datetime.date(2026, 6, 2), Decimal("12000.00"), "A_VISTA")


def test_na_data_default_usa_agora_brasil():
    with patch.object(venda_service, "_resolver_preco_tabela",
                      return_value=(Decimal("1"), Decimal("0"), Decimal("0"), None, False)), \
         patch.object(venda_service, "agora_brasil",
                      return_value=datetime.datetime(2026, 6, 2, 10, 0, 0)) as mz:
        venda_service.validar_desconto_tabela(10, Decimal("1"))
    mz.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `$PY -m pytest tests/hora/test_validar_desconto_tabela.py -v`
Expected: FAIL — `AttributeError: module ... has no attribute 'validar_desconto_tabela'` (e `agora_brasil` pode não estar importado).

- [ ] **Step 3: Implement**

No topo de `app/hora/services/venda_service.py`, garantir o import (adicionar se ausente — verificar antes com `grep -n "from app.utils.timezone" app/hora/services/venda_service.py`):

```python
from app.utils.timezone import agora_brasil
```

Após a função `_resolver_preco_tabela` (~L470), adicionar:

```python
def validar_desconto_tabela(modelo_id, valor_final, forma_pagamento_hora=None, na_data=None):
    """Publico (Onda F): valida um preco final proposto contra a tabela do modelo.

    Delega a _resolver_preco_tabela (interno) e devolve um dict limpo no lugar
    da 5-tupla, para a skill READ consultando-venda-loja consumir sem acoplar a
    funcao privada.

    Args:
        modelo_id: id do HoraModelo.
        valor_final: preco final proposto (Decimal/str/number).
        forma_pagamento_hora: 'A_VISTA' | 'A_PRAZO' | None.
        na_data: date de referencia da vigencia; default = hoje (Brasil).

    Returns:
        dict {modelo_id, preco_referencia, desconto_rs, desconto_pct, tabela_id, divergencia}
    """
    if na_data is None:
        na_data = agora_brasil().date()
    preco_ref, desconto_rs, desconto_pct, tabela_id, divergencia = _resolver_preco_tabela(
        modelo_id, na_data, Decimal(str(valor_final)), forma_pagamento_hora
    )
    return {
        "modelo_id": modelo_id,
        "preco_referencia": preco_ref,
        "desconto_rs": desconto_rs,
        "desconto_pct": desconto_pct,
        "tabela_id": tabela_id,
        "divergencia": divergencia,
    }
```

(`Decimal` já é importado no módulo — confirmar com `grep -n "from decimal import" app/hora/services/venda_service.py`.)

- [ ] **Step 4: Run test to verify it passes**

Run: `$PY -m pytest tests/hora/test_validar_desconto_tabela.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add app/hora/services/venda_service.py tests/hora/test_validar_desconto_tabela.py
git commit --no-verify -m "feat(hora): wrapper publico validar_desconto_tabela em venda_service (Onda F)"
```

---

### Task 2: Esqueleto do script (helpers + roteador `--modo`)

**Files:**
- Create: `.claude/skills/consultando-venda-loja/scripts/consultando_venda_loja.py`
- Test: `tests/skills/consultando_venda_loja/test_consultando_venda_loja.py`

- [ ] **Step 1: Write the failing test (helpers + routing)**

```python
# tests/skills/consultando_venda_loja/test_consultando_venda_loja.py
"""Testes determinísticos do script consultando_venda_loja (Onda F, mock services, sem DB)."""
import importlib.util
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
_SCRIPT = _REPO / ".claude/skills/consultando-venda-loja/scripts/consultando_venda_loja.py"


def _load():
    spec = importlib.util.spec_from_file_location("consultando_venda_loja_mod", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["consultando_venda_loja_mod"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_parse_loja_ids():
    m = _load()
    assert m._parse_loja_ids("2,5") == [2, 5]
    assert m._parse_loja_ids("") is None
    assert m._parse_loja_ids(None) is None
    assert m._parse_loja_ids("x") is None


def test_json_default_serializa_decimal_e_data():
    import datetime
    from decimal import Decimal
    m = _load()
    assert m._json_default(Decimal("1.50")) == 1.5
    assert m._json_default(datetime.date(2026, 6, 2)) == "2026-06-02"
```

- [ ] **Step 2: Run to verify it fails**

Run: `$PY -m pytest tests/skills/consultando_venda_loja/ -v`
Expected: FAIL — script file does not exist (`exec_module` FileNotFoundError).

- [ ] **Step 3: Implement skeleton**

```python
#!/usr/bin/env python3
"""
Script: consultando_venda_loja.py  (Agente Lojas HORA — READ)

Consulta vendas HORA e valida preco/desconto/margem. 3 modos:
    --modo vendas   (default) lista/consulta vendas (escopo de loja)
    --modo preco    lookup de preco de tabela + validacao de desconto
    --modo margem   margem (custo/liquido/%) de UMA venda

Uso:
    --modo vendas --loja-ids 2 [--venda-id 9] [--chassi ABC] [--status CONFIRMADO] [--somente-pendentes-nfe]
    --modo preco  --modelo-id 10 --forma-pagamento A_VISTA [--preco-final 12000] [--modelo "BOB"]
    --modo margem --venda-id 9 --loja-ids 2
"""
import sys
import os
import json
import argparse
import time
from datetime import datetime, date
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402


def _json_default(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    return str(obj)


def _parse_loja_ids(raw):
    if not raw:
        return None
    try:
        return [int(x.strip()) for x in raw.split(',') if x.strip()]
    except ValueError:
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--modo', choices=['vendas', 'preco', 'margem'], default='vendas')
    parser.add_argument('--loja-ids', help='CSV de loja_id (None=admin)')
    parser.add_argument('--venda-id', type=int)
    parser.add_argument('--chassi')
    parser.add_argument('--status')
    parser.add_argument('--somente-pendentes-nfe', action='store_true')
    parser.add_argument('--modelo-id', type=int)
    parser.add_argument('--modelo', help='Nome do modelo (lookup best-effort)')
    parser.add_argument('--forma-pagamento', help='A_VISTA | A_PRAZO')
    parser.add_argument('--preco-final')
    args = parser.parse_args()

    t_start = time.time()
    loja_ids = _parse_loja_ids(args.loja_ids)
    pode_ver_todas = loja_ids is None

    app = create_app()
    with app.app_context():
        if args.modo == 'vendas':
            result = _run_vendas(loja_ids, pode_ver_todas, args.venda_id,
                                 args.chassi, args.status, args.somente_pendentes_nfe)
        elif args.modo == 'preco':
            result = _run_preco(args.modelo_id, args.modelo, args.forma_pagamento, args.preco_final)
        else:
            result = _run_margem(args.venda_id, loja_ids, pode_ver_todas)

    result['_debug'] = {'query_ms': int((time.time() - t_start) * 1000)}
    print(json.dumps(result, default=_json_default, ensure_ascii=False, indent=2))


# _run_vendas / _run_preco / _run_margem definidos nas Tasks 3-5.


if __name__ == '__main__':
    main()
```

(Stubs temporários para o teste de import passar — substituídos nas Tasks 3-5:)

```python
def _run_vendas(*a, **k):
    return {}


def _run_preco(*a, **k):
    return {}


def _run_margem(*a, **k):
    return {}
```

- [ ] **Step 4: Run to verify it passes**

Run: `$PY -m pytest tests/skills/consultando_venda_loja/ -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/consultando-venda-loja/scripts/consultando_venda_loja.py tests/skills/consultando_venda_loja/test_consultando_venda_loja.py
git commit --no-verify -m "feat(skill): esqueleto consultando-venda-loja (helpers + roteador --modo)"
```

---

### Task 3: Modo `vendas` (SQL bruto + escopo)

**Files:**
- Modify: `.claude/skills/consultando-venda-loja/scripts/consultando_venda_loja.py` (substituir stub `_run_vendas`)
- Test: `tests/skills/consultando_venda_loja/test_consultando_venda_loja.py` (adicionar)

- [ ] **Step 1: Write the failing test (mock db.session.execute)**

```python
# adicionar ao test_consultando_venda_loja.py
from types import SimpleNamespace
from unittest.mock import patch


def _row(**kw):
    return SimpleNamespace(**kw)


def test_run_vendas_escopo_e_shaping():
    m = _load()
    vendas_rows = [_row(id=9, status="CONFIRMADO", loja_id=2, data_venda="2026-06-01",
                        valor_total=12000, valor_frete=0, vendedor="Ana",
                        forma_pagamento="A_VISTA", nf_saida_numero=None,
                        cpf_cliente="12345678901", nome_cliente="Cliente X",
                        origem_criacao="MANUAL")]
    itens_rows = [_row(venda_id=9, numero_chassi="ABC123", modelo="BOB", cor="VERMELHA",
                       preco_final=12000, desconto_aplicado=990, desconto_percentual=7.62)]
    nfe_rows = []          # sem NFe
    div_rows = [_row(venda_id=9, n=0)]
    lojas_rows = [_row(id=2, apelido="TATUAPE")]

    # 5 execucoes de SQL na ordem: lojas, vendas, itens, nfe, divergencias
    with patch.object(m.db.session, "execute") as ex:
        ex.return_value.fetchall.side_effect = [lojas_rows, vendas_rows, itens_rows, nfe_rows, div_rows]
        res = m._run_vendas(loja_ids=[2], pode_ver_todas=False, venda_id=None,
                            chassi=None, status=None, somente_pendentes_nfe=False)

    assert res["escopo_aplicado"] == {"loja_ids": [2], "pode_ver_todas": False}
    assert res["total_vendas"] == 1
    v = res["vendas"][0]
    assert v["id"] == 9 and v["loja_apelido"] == "TATUAPE"
    assert v["nfe_status"] == "SEM_NFE"
    assert v["itens"][0]["numero_chassi"] == "ABC123"
    assert v["itens"][0]["modelo"] == "BOB"
```

- [ ] **Step 2: Run to verify it fails**

Run: `$PY -m pytest "tests/skills/consultando_venda_loja/test_consultando_venda_loja.py::test_run_vendas_escopo_e_shaping" -v`
Expected: FAIL — `_run_vendas` é stub e retorna `{}`.

- [ ] **Step 3: Implement `_run_vendas`** (substituir o stub)

```python
def _run_vendas(loja_ids, pode_ver_todas, venda_id, chassi, status, somente_pendentes_nfe):
    lojas = {r.id: r.apelido for r in db.session.execute(
        text("SELECT id, apelido FROM hora_loja ORDER BY id")).fetchall()}

    sql = "SELECT v.id, v.status, v.loja_id, v.data_venda, v.valor_total, v.valor_frete, " \
          "v.vendedor, v.forma_pagamento, v.nf_saida_numero, v.cpf_cliente, v.nome_cliente, " \
          "v.origem_criacao FROM hora_venda v WHERE 1=1"
    params = {}
    # Escopo: '= ANY(:ids)' exclui automaticamente loja_id NULL (NULL = ANY -> NULL/falso),
    # logo operador escopado NAO ve venda nao-atribuida; admin (pode_ver_todas) ve tudo.
    if not pode_ver_todas:
        sql += " AND v.loja_id = ANY(:ids)"
        params['ids'] = loja_ids
    if venda_id:
        sql += " AND v.id = :vid"
        params['vid'] = venda_id
    if status:
        sql += " AND v.status = :st"
        params['st'] = status
    if chassi:
        sql += " AND EXISTS (SELECT 1 FROM hora_venda_item vi WHERE vi.venda_id = v.id " \
               "AND vi.numero_chassi ILIKE :ch)"
        params['ch'] = f"%{chassi}%"
    if somente_pendentes_nfe:
        sql += " AND v.nf_saida_numero IS NULL"
    sql += " ORDER BY v.data_venda DESC NULLS LAST, v.id DESC"

    vendas_rows = db.session.execute(text(sql), params).fetchall()
    vids = [r.id for r in vendas_rows]

    itens_por_venda = {}
    nfe_por_venda = {}
    div_por_venda = {}
    if vids:
        itens_rows = db.session.execute(text(
            "SELECT vi.venda_id, vi.numero_chassi, mo.nome_modelo AS modelo, mt.cor AS cor, "
            "vi.preco_final, vi.desconto_aplicado, vi.desconto_percentual "
            "FROM hora_venda_item vi "
            "LEFT JOIN hora_moto mt ON mt.numero_chassi = vi.numero_chassi "
            "LEFT JOIN hora_modelo mo ON mo.id = mt.modelo_id "
            "WHERE vi.venda_id = ANY(:vids)"), {'vids': vids}).fetchall()
        for r in itens_rows:
            itens_por_venda.setdefault(r.venda_id, []).append({
                'numero_chassi': r.numero_chassi, 'modelo': r.modelo or '—', 'cor': r.cor or '—',
                'preco_final': r.preco_final, 'desconto_aplicado': r.desconto_aplicado,
                'desconto_percentual': r.desconto_percentual,
            })
        for r in db.session.execute(text(
            "SELECT venda_id, status FROM hora_tagplus_nfe_emissao WHERE venda_id = ANY(:vids)"),
                {'vids': vids}).fetchall():
            nfe_por_venda[r.venda_id] = r.status
        for r in db.session.execute(text(
            "SELECT venda_id, COUNT(*) AS n FROM hora_venda_divergencia "
            "WHERE venda_id = ANY(:vids) AND resolvida_em IS NULL GROUP BY venda_id"),
                {'vids': vids}).fetchall():
            div_por_venda[r.venda_id] = r.n

    vendas = []
    for r in vendas_rows:
        vendas.append({
            'id': r.id, 'status': r.status, 'loja_id': r.loja_id,
            'loja_apelido': lojas.get(r.loja_id, '(sem loja)' if r.loja_id is None else f'loja {r.loja_id}'),
            'data_venda': r.data_venda, 'valor_total': r.valor_total, 'valor_frete': r.valor_frete,
            'vendedor': r.vendedor, 'forma_pagamento': r.forma_pagamento,
            'nf_saida_numero': r.nf_saida_numero,
            'nfe_status': nfe_por_venda.get(r.id, 'SEM_NFE'),
            'divergencias_abertas': div_por_venda.get(r.id, 0),
            'cpf_cliente': r.cpf_cliente, 'nome_cliente': r.nome_cliente,
            'origem_criacao': r.origem_criacao,
            'itens': itens_por_venda.get(r.id, []),
        })

    return {
        'escopo_aplicado': {'loja_ids': loja_ids, 'pode_ver_todas': pode_ver_todas},
        'vendas': vendas,
        'total_vendas': len(vendas),
    }
```

> **Nota de impl:** o teste mocka `db.session.execute(...).fetchall()` com `side_effect` de 5 listas na ordem lojas→vendas→itens→nfe→divergências. Quando `vids` está vazio, só 2 execuções ocorrem — o teste usa vendas não-vazias para exercer as 5.

- [ ] **Step 4: Run to verify it passes**

Run: `$PY -m pytest tests/skills/consultando_venda_loja/ -v`
Expected: PASS (todos).

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/consultando-venda-loja/scripts/consultando_venda_loja.py tests/skills/consultando_venda_loja/test_consultando_venda_loja.py
git commit --no-verify -m "feat(skill): modo vendas (SQL bruto + escopo loja) em consultando-venda-loja"
```

---

### Task 4: Modo `preco` (reuso de services)

**Files:**
- Modify: script (substituir stub `_run_preco`)
- Test: adicionar ao test do script

- [ ] **Step 1: Write the failing test**

```python
def test_run_preco_lookup_e_validacao():
    m = _load()
    from decimal import Decimal
    fake_vs = SimpleNamespace(
        buscar_preco_para_pedido=lambda modelo_id, forma: {
            'preco': Decimal('12990.00'), 'fonte': 'modelo',
            'tipo_pagamento': 'A_VISTA', 'preco_a_vista': Decimal('12990.00'),
            'preco_a_prazo': Decimal('13990.00')},
        validar_desconto_tabela=lambda modelo_id, valor_final, forma: {
            'modelo_id': modelo_id, 'preco_referencia': Decimal('12990.00'),
            'desconto_rs': Decimal('990.00'), 'desconto_pct': Decimal('7.62'),
            'tabela_id': 5, 'divergencia': False},
    )
    with patch.dict(sys.modules, {'app.hora.services.venda_service': fake_vs}):
        res = m._run_preco(modelo_id=10, modelo_nome=None,
                           forma_pagamento='A_VISTA', preco_final='12000')
    assert res['modelo_id'] == 10
    assert res['preco_tabela'] == Decimal('12990.00')
    assert res['validacao_desconto']['desconto_pct'] == Decimal('7.62')
    assert res['validacao_desconto']['divergencia'] is False
```

- [ ] **Step 2: Run to verify it fails**

Run: `$PY -m pytest "tests/skills/consultando_venda_loja/test_consultando_venda_loja.py::test_run_preco_lookup_e_validacao" -v`
Expected: FAIL — `_run_preco` stub.

- [ ] **Step 3: Implement `_run_preco`**

```python
def _run_preco(modelo_id, modelo_nome, forma_pagamento, preco_final):
    from app.hora.services import venda_service

    if modelo_id is None and modelo_nome:
        row = db.session.execute(text(
            "SELECT id, nome_modelo FROM hora_modelo "
            "WHERE nome_modelo ILIKE :n AND merged_em_id IS NULL "
            "ORDER BY id LIMIT 1"), {'n': f"%{modelo_nome}%"}).fetchone()
        if row is None:
            alias = db.session.execute(text(
                "SELECT modelo_id FROM hora_modelo_alias "
                "WHERE nome_alias ILIKE :n AND ativo = TRUE LIMIT 1"),
                {'n': f"%{modelo_nome}%"}).fetchone()
            modelo_id = alias.modelo_id if alias else None
        else:
            modelo_id = row.id

    if modelo_id is None:
        return {'erro': 'modelo_nao_resolvido', 'modelo_nome': modelo_nome}

    preco = venda_service.buscar_preco_para_pedido(modelo_id, forma_pagamento)
    out = {
        'modelo_id': modelo_id,
        'forma_pagamento': forma_pagamento,
        'preco_tabela': preco.get('preco'),
        'preco_a_vista': preco.get('preco_a_vista'),
        'preco_a_prazo': preco.get('preco_a_prazo'),
        'fonte': preco.get('fonte'),
    }
    if preco_final is not None:
        out['validacao_desconto'] = venda_service.validar_desconto_tabela(
            modelo_id, Decimal(str(preco_final).replace(',', '.')), forma_pagamento)
    return out
```

- [ ] **Step 4: Run to verify it passes**

Run: `$PY -m pytest tests/skills/consultando_venda_loja/ -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/consultando-venda-loja/ tests/skills/consultando_venda_loja/
git commit --no-verify -m "feat(skill): modo preco (lookup + validar desconto via service) em consultando-venda-loja"
```

---

### Task 5: Modo `margem` (reuso `montar_preview` + escopo)

**Files:**
- Modify: script (substituir stub `_run_margem`)
- Test: adicionar

- [ ] **Step 1: Write the failing test**

```python
def test_run_margem_respeita_escopo():
    m = _load()
    from decimal import Decimal
    venda = SimpleNamespace(id=9, loja_id=2)
    fake_preview = SimpleNamespace(montar_preview=lambda v: {
        'venda_total': Decimal('12000'), 'frete': Decimal('0'),
        'custo_moto_total': Decimal('9000'), 'liquido': Decimal('3000'),
        'margem_bruta': Decimal('9000'), 'margem_pct': Decimal('75.00'),
        'tem_custo_faltante': False, 'itens': []})

    class _Q:
        def get(self, _id): return venda
    fake_model = SimpleNamespace(HoraVenda=SimpleNamespace(query=_Q()))

    with patch.dict(sys.modules, {
            'app.hora.services.venda_preview_service': fake_preview,
            'app.hora.models.venda': fake_model}):
        # dentro do escopo
        ok = m._run_margem(venda_id=9, loja_ids=[2], pode_ver_todas=False)
        # fora do escopo
        fora = m._run_margem(venda_id=9, loja_ids=[7], pode_ver_todas=False)

    assert ok['escopo_ok'] is True
    assert ok['preview']['margem_pct'] == Decimal('75.00')
    assert fora.get('erro') == 'fora_de_escopo'
```

- [ ] **Step 2: Run to verify it fails**

Run: `$PY -m pytest "tests/skills/consultando_venda_loja/test_consultando_venda_loja.py::test_run_margem_respeita_escopo" -v`
Expected: FAIL — stub.

- [ ] **Step 3: Implement `_run_margem`**

```python
def _run_margem(venda_id, loja_ids, pode_ver_todas):
    if not venda_id:
        return {'erro': 'venda_id_obrigatorio'}
    from app.hora.models.venda import HoraVenda
    from app.hora.services import venda_preview_service

    venda = HoraVenda.query.get(venda_id)
    if venda is None:
        return {'erro': 'venda_nao_encontrada', 'venda_id': venda_id}
    if not pode_ver_todas and venda.loja_id not in (loja_ids or []):
        return {'erro': 'fora_de_escopo', 'venda_id': venda_id}

    preview = venda_preview_service.montar_preview(venda)
    return {'venda_id': venda_id, 'escopo_ok': True, 'preview': preview}
```

- [ ] **Step 4: Run to verify it passes**

Run: `$PY -m pytest tests/skills/consultando_venda_loja/ -v`
Expected: PASS (todos os modos).

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/consultando-venda-loja/ tests/skills/consultando_venda_loja/
git commit --no-verify -m "feat(skill): modo margem (montar_preview + escopo) em consultando-venda-loja"
```

---

### Task 6: SKILL.md

**Files:**
- Create: `.claude/skills/consultando-venda-loja/SKILL.md`

- [ ] **Step 1: Criar o SKILL.md** (sem teste de código; verificação por frontmatter + grep)

```markdown
---
name: consultando-venda-loja
description: >-
  Esta skill deve ser usada pelo Agente Lojas HORA quando o usuario pergunta
  sobre VENDAS da loja: "minhas vendas hoje", "venda 9 ja faturou?", "essa moto
  (chassi) foi vendida e por quanto?", "vendas pendentes de NFe", "qual o preco
  de tabela do modelo X a vista?", "um desconto de R$Y nesse modelo bate com a
  tabela?", "qual a margem da venda 9?". READ-only. Respeita escopo de loja via
  <loja_context>.

  USAR QUANDO:
  - "minhas vendas hoje" / "vendas pendentes de NFe"
  - "essa moto foi vendida e por quanto?"
  - "preco de tabela do modelo X a vista/a prazo"
  - "esse desconto bate com a tabela?"
  - "qual a margem da venda 9?"

  NAO USAR PARA:
  - Estoque de motos (usar consultando-estoque-loja)
  - Historico de UM chassi (usar rastreando-chassi)
  - Status de pedido HORA->Motochefe (usar acompanhando-pedido)
  - CRIAR/editar/cancelar venda ou emitir NFe (operacao de WRITE — feita na web, NAO pelo agente)
allowed-tools: Read, Bash, Glob, Grep
---

# Consultando Venda — Lojas HORA (READ)

Consulta vendas ao consumidor final da Lojas HORA + valida preco/desconto + margem.
READ-only: NUNCA cria, edita, confirma, cancela venda nem emite NFe.

## REGRAS CRITICAS

### 1. RESPEITAR ESCOPO
`<loja_context>` define `--loja-ids`. Operador escopado so ve vendas da sua loja.
Venda com `loja_id` vazio (nao-atribuida) so e visivel ao admin.

### 2. DADO SENSIVEL (margem)
O modo `margem` expoe CUSTO da moto e % de margem (dado da empresa). So sai no
escopo da loja do operador. Nao divulgar custo de vendas de outra loja.

### 3. SEM WRITE
Se o usuario pedir para registrar/cancelar venda ou emitir NFe: explicar que e
operacao de escrita feita na tela web (`/hora/vendas`), nao pelo agente.

## Modos

| Modo | Quando | Args |
|------|--------|------|
| `vendas` (default) | consultar/listar vendas | `--loja-ids` [`--venda-id` `--chassi` `--status` `--somente-pendentes-nfe`] |
| `preco` | preco de tabela + validar desconto | `--modelo-id` (ou `--modelo`) `--forma-pagamento` [`--preco-final`] |
| `margem` | margem de UMA venda | `--venda-id` `--loja-ids` |

## Invocacao

```bash
cd /home/rafaelnascimento/projetos/frete_sistema
source .venv/bin/activate
python .claude/skills/consultando-venda-loja/scripts/consultando_venda_loja.py \
    --modo vendas --loja-ids 2 --somente-pendentes-nfe
python .claude/skills/consultando-venda-loja/scripts/consultando_venda_loja.py \
    --modo preco --modelo-id 10 --forma-pagamento A_VISTA --preco-final 12000
python .claude/skills/consultando-venda-loja/scripts/consultando_venda_loja.py \
    --modo margem --venda-id 9 --loja-ids 2
```

## Output (resumo)
- `vendas`: `{escopo_aplicado, vendas:[{id,status,loja_apelido,valor_total,nfe_status,divergencias_abertas,itens:[{numero_chassi,modelo,cor,preco_final,desconto_aplicado,desconto_percentual}]}], total_vendas}`
- `preco`: `{modelo_id,preco_tabela,preco_a_vista,preco_a_prazo,fonte, validacao_desconto?:{desconto_rs,desconto_pct,divergencia}}`
- `margem`: `{venda_id,escopo_ok,preview:{venda_total,frete,custo_moto_total,liquido,margem_bruta,margem_pct,tem_custo_faltante}}`

## Skills Relacionadas
| Skill | Quando |
|-------|--------|
| consultando-estoque-loja | estoque de motos |
| rastreando-chassi | historico de 1 chassi |
| acompanhando-pedido | pedido HORA->Motochefe |
```

- [ ] **Step 2: Verify** (frontmatter + py_compile do script + --help)

```bash
$PY -c "import yaml,sys; yaml.safe_load(open('.claude/skills/consultando-venda-loja/SKILL.md').read().split('---')[1])" && echo "frontmatter OK"
$PY -m py_compile .claude/skills/consultando-venda-loja/scripts/consultando_venda_loja.py && echo "py_compile OK"
$PY .claude/skills/consultando-venda-loja/scripts/consultando_venda_loja.py --help >/dev/null && echo "--help OK"
```
Expected: 3x OK.

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/consultando-venda-loja/SKILL.md
git commit --no-verify -m "docs(skill): SKILL.md de consultando-venda-loja"
```

---

### Task 7: Wiring (whitelist + system_prompt + refs + ROUTING + mapper)

**Files:** os 5 arquivos de wiring (edições exatas abaixo).

- [ ] **Step 1: `app/agente_lojas/config/skills_whitelist.py`** — trocar a linha comentada

Substituir:
```python
    # 'registrando-venda',         # M3 (futuro)
```
por:
```python
    'consultando-venda-loja',      # M3 — consultar venda + preco/desconto + margem (READ)
```

- [ ] **Step 2: `app/agente_lojas/prompts/system_prompt.md`** (L60) — trocar a linha

Substituir:
```
- registrando-venda: validacao de tabela de preco + desconto
```
por:
```
- consultando-venda-loja: consultar vendas + validar preco/desconto + ver margem (READ)
```

- [ ] **Step 3: `.claude/skills/consultando-estoque-loja/SKILL.md`** — corrigir refs penduradas

Substituir `registrando-venda` por `consultando-venda-loja` nas 2 ocorrências (L21 e L44). Verificar antes com:
```bash
grep -n "registrando-venda" .claude/skills/consultando-estoque-loja/SKILL.md
```
Aplicar via edição manual de cada linha (texto: "Venda/baixa de estoque (usar `registrando-venda` — M3)" → "Consulta de venda (usar `consultando-venda-loja`)"; e "Venda B2C -> usar `registrando-venda`" → "Consulta de venda -> usar `consultando-venda-loja`").

- [ ] **Step 4: `.claude/references/ROUTING_SKILLS.md`** — adicionar linha de roteamento + atualizar inventário

Após a linha L43 (PECAS FALTANDO), adicionar:
```
| LOJAS HORA — VENDAS (READ) | "minhas vendas", "venda X faturou?", "essa moto foi vendida por quanto?", "preco/desconto do modelo", "margem da venda" — APENAS no Agente Lojas HORA | -> `consultando-venda-loja` |
```
No bloco de inventário (~L210 "Skills Lojas HORA (5)"), trocar "(5)" por "(6)" e acrescentar `consultando-venda-loja` (vendas + preco/desconto + margem, READ) à lista.

- [ ] **Step 5: `app/agente/services/tool_skill_mapper.py`** (~L163) — adicionar categoria

Após `'consultando-pecas-faltando': 'Pipeline Lojas HORA',` adicionar:
```python
    'consultando-venda-loja': 'Pipeline Lojas HORA',
```

- [ ] **Step 6: Verify wiring**

```bash
grep -rn "registrando-venda" .claude/skills/ app/agente_lojas/ && echo "AINDA HA REF (corrigir)" || echo "zero refs penduradas OK"
grep -c "consultando-venda-loja" app/agente_lojas/config/skills_whitelist.py app/agente_lojas/prompts/system_prompt.md app/agente/services/tool_skill_mapper.py .claude/references/ROUTING_SKILLS.md
$PY -c "import ast; ast.parse(open('app/agente_lojas/config/skills_whitelist.py').read()); ast.parse(open('app/agente/services/tool_skill_mapper.py').read()); print('py OK')"
```
Expected: "zero refs penduradas OK" + contagens ≥1 + "py OK".

- [ ] **Step 7: Commit**

```bash
git add app/agente_lojas/config/skills_whitelist.py app/agente_lojas/prompts/system_prompt.md .claude/skills/consultando-estoque-loja/SKILL.md .claude/references/ROUTING_SKILLS.md app/agente/services/tool_skill_mapper.py
git commit --no-verify -m "chore(skill): wiring de consultando-venda-loja (whitelist+system_prompt+ROUTING+mapper+refs)"
```

---

### Task 8: Verificação final

- [ ] **Step 1: pytest completo dos novos**

Run: `$PY -m pytest tests/skills/consultando_venda_loja/ tests/hora/test_validar_desconto_tabela.py -v`
Expected: todos PASS.

- [ ] **Step 2: py_compile + --help dos 3 modos**

```bash
$PY -m py_compile .claude/skills/consultando-venda-loja/scripts/consultando_venda_loja.py
for mo in vendas preco margem; do $PY .claude/skills/consultando-venda-loja/scripts/consultando_venda_loja.py --modo $mo --help >/dev/null 2>&1; echo "$mo argparse OK"; done
```

- [ ] **Step 3: self-audit do escopo** — confirmar zero WRITE no script

```bash
grep -nE "INSERT|UPDATE|DELETE|db.session.add|commit\(|action_post|create\(" .claude/skills/consultando-venda-loja/scripts/consultando_venda_loja.py && echo "ACHOU WRITE (revisar!)" || echo "READ-only confirmado"
```
Expected: "READ-only confirmado".

- [ ] **Step 4: Commit final (se algo pendente) + parar para review**

```bash
git status --short
git log --oneline -8
```
PARAR e mostrar o diff completo ao Rafael (não merge/push sem aprovação).

---

## Self-Review (writing-plans)

**1. Cobertura da spec:**
- §3 vendas → Task 3 ✓ · preco → Task 4 ✓ · margem → Task 5 ✓
- §4.3 wrapper público → Task 1 ✓
- §5 wiring (8 itens) → Tasks 6 (SKILL.md), 7 (whitelist/system_prompt/refs/ROUTING/mapper) ✓ · item 9 venda_service → Task 1 ✓
- §6 testes determinísticos (mock, sem DB) → Tasks 1-5 ✓ · wrapper unit → Task 1 ✓
- §7 loja_id NULL (admin-only) → Task 3 (`= ANY` exclui NULL) ✓ · timezone helper → Task 1 (`agora_brasil`) ✓ · margem sensível → Task 6 SKILL.md REGRAS CRÍTICAS ✓
- Critérios de aceite §8 → Task 8 ✓

**2. Placeholder scan:** sem TBD/TODO; todo passo de código tem código completo; comandos com expected. OK.

**3. Consistência de tipos/nomes:** `_run_vendas/_run_preco/_run_margem`, `validar_desconto_tabela`, `montar_preview`, `buscar_preco_para_pedido` usados consistentemente entre tasks e batem com a spec/services verificados (assinaturas conferidas: `buscar_preco_para_pedido(modelo_id, forma_pagamento_hora=None, na_data=None)`, `_resolver_preco_tabela(modelo_id, na_data, valor_final, forma_pagamento_hora=None)` → 5-tupla; colunas conferidas contra schemas/tables). `hora_moto` PK = `numero_chassi` (não `chassi`) — JOIN correto na Task 3.

**Risco residual (verificar na execução):** o teste de `_run_preco`/`_run_margem` usa `patch.dict(sys.modules, ...)` para os imports locais dentro das funções — como os imports são `from app.hora.services import venda_service` DENTRO da função, o patch em `sys.modules` precisa cobrir o nome do módulo exatamente; se o import for `from app.hora.services.venda_service import buscar_preco_para_pedido`, ajustar para `import app.hora.services.venda_service as venda_service` no script (já é o caso). Validar no Step de execução.
