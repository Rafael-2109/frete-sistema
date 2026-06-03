<!-- doc:meta
tipo: how-to
camada: L2
sot_de: skill carregando-motos-assai (plano de implementacao)
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-02
-->
# Skill carregando-motos-assai — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Papel:** plano TDD de implementação da skill READ+WRITE `carregando-motos-assai`. **Abra quando:** for implementar a skill task-a-task.

**Goal:** Criar a skill READ+WRITE `carregando-motos-assai` (cluster Motos Assaí) para consultar e operar carregamento (etapa física Sep→NF), reusando `carregamento_service`.

**Architecture:** 1 skill, 1 script, **action-flags** (espelha `registrando-evento-moto-assai`). READ (`--listar`/`--detalhar`) sem auth; WRITE (6 ops) com `--user-id` + `pode_acessar_motos_assai()` (exit 3) + `--dry-run` default (exit 4) / `--confirmar` (chama service + `db.session.commit()`). Reusa `carregamento_service`; não reimplementa.

**Tech Stack:** Python 3.12, Flask `create_app`, SQLAlchemy 2.0, pytest + unittest.mock. Padrão WRITE do cluster Assaí.

**Spec:** `docs/superpowers/specs/2026-06-02-skill-carregando-motos-assai-design.md`

## Indice

1. File Structure
2. Task 1 — Esqueleto + READ (listar/detalhar)
3. Task 2 — WRITE dispatch + salvaguardas
4. Task 3 — SKILL.md
5. Task 4 — Wiring
6. Task 5 — Verificação final
7. Self-Review

> Convenção: `PY=/home/rafaelnascimento/projetos/frete_sistema/.venv/bin/python`. Rodar da raiz do worktree.

## File Structure

| Arquivo | Ação |
|---|---|
| `.claude/skills/carregando-motos-assai/scripts/carregando_motos_assai.py` | Create — script (READ + 6 WRITE) |
| `.claude/skills/carregando-motos-assai/SKILL.md` | Create — doc da skill (+ TOC se >100L) |
| `tests/skills/carregando_motos_assai/test_carregando_motos_assai.py` | Create — testes mock (sem DB) |
| `.claude/agents/gestor-motos-assai.md` | Modify — `skills:` += carregando-motos-assai |
| `.claude/references/ROUTING_SKILLS.md` | Modify — rota + inventário Assaí (6→7) |
| `app/agente/services/tool_skill_mapper.py` | Modify — categoria Assaí |
| `app/motos_assai/CLAUDE.md` | Modify — tabela Skills (6→7) |
| `.claude/skills/acompanhando-saida-assai/SKILL.md` | Modify — cross-ref carregamento |

---

### Task 1 — Esqueleto + READ (listar/detalhar)

**Files:** Create script + test.

- [ ] **Step 1 — Test (helpers + READ shaping)**

```python
# tests/skills/carregando_motos_assai/test_carregando_motos_assai.py
import importlib.util, sys
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch, MagicMock

_REPO = Path(__file__).resolve().parents[3]
_SCRIPT = _REPO / ".claude/skills/carregando-motos-assai/scripts/carregando_motos_assai.py"

def _load():
    spec = importlib.util.spec_from_file_location("carregando_motos_assai_mod", _SCRIPT)
    mod = importlib.util.module_from_spec(spec); sys.modules["carregando_motos_assai_mod"] = mod
    spec.loader.exec_module(mod); return mod

def _row(**kw): return SimpleNamespace(**kw)

def test_listar_shaping():
    m = _load()
    rows = [_row(id=1, status="EM_CARREGAMENTO", pedido_id=9, loja_id=2, separacao_id=5,
                 iniciado_em="2026-06-01", finalizado_em=None, n_itens=3)]
    with patch.object(m, "db", MagicMock()) as dbm:
        dbm.session.execute.return_value.fetchall.return_value = rows
        res = m._run_listar(status="EM_CARREGAMENTO", pedido_id=None, loja_id=None, separacao_id=None)
    assert res["total"] == 1 and res["carregamentos"][0]["id"] == 1
    assert res["carregamentos"][0]["n_itens"] == 3
```

- [ ] **Step 2 — Run (fails: file missing)** → `$PY -m pytest tests/skills/carregando_motos_assai/ -q`

- [ ] **Step 3 — Implement skeleton + READ**

```python
#!/usr/bin/env python3
"""carregando_motos_assai.py — Motos Assaí carregamento (READ + WRITE).

READ (sem auth):  --listar [--status --pedido-id --loja-id --separacao-id] | --detalhar --carregamento-id N
WRITE (--user-id + --dry-run default / --confirmar):
  --iniciar --pedido-id --loja-id | --escanear --carregamento-id --chassi |
  --cancelar-item --item-id | --finalizar --carregamento-id |
  --cancelar --carregamento-id --motivo | --alterar --carregamento-id
Exit: 0 ok · 3 sem autorizacao · 4 dry-run preview · demais=erro.
"""
import sys, os, json, argparse, time
from datetime import datetime, date
from decimal import Decimal
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))
from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402

def _json_default(o):
    if isinstance(o, (datetime, date)): return o.isoformat()
    if isinstance(o, Decimal): return float(o)
    return str(o)

def _run_listar(status, pedido_id, loja_id, separacao_id):
    sql = ("SELECT c.id, c.status, c.pedido_id, c.loja_id, c.separacao_id, "
           "c.iniciado_em, c.finalizado_em, "
           "(SELECT COUNT(*) FROM assai_carregamento_item i WHERE i.carregamento_id=c.id) AS n_itens "
           "FROM assai_carregamento c WHERE 1=1")
    p = {}
    if status: sql += " AND c.status=:st"; p['st'] = status
    if pedido_id: sql += " AND c.pedido_id=:pid"; p['pid'] = pedido_id
    if loja_id: sql += " AND c.loja_id=:lid"; p['lid'] = loja_id
    if separacao_id: sql += " AND c.separacao_id=:sid"; p['sid'] = separacao_id
    sql += " ORDER BY c.id DESC"
    rows = db.session.execute(text(sql), p).fetchall()
    cs = [{'id': r.id, 'status': r.status, 'pedido_id': r.pedido_id, 'loja_id': r.loja_id,
           'separacao_id': r.separacao_id, 'iniciado_em': r.iniciado_em,
           'finalizado_em': r.finalizado_em, 'n_itens': r.n_itens} for r in rows]
    return {'carregamentos': cs, 'total': len(cs)}

def _run_detalhar(carregamento_id):
    hdr = db.session.execute(text(
        "SELECT id, status, pedido_id, loja_id, separacao_id, iniciado_em, finalizado_em, "
        "cancelado_em, motivo_cancelamento FROM assai_carregamento WHERE id=:id"),
        {'id': carregamento_id}).fetchone()
    if hdr is None:
        return {'erro': 'carregamento_nao_encontrado', 'carregamento_id': carregamento_id}
    itens = db.session.execute(text(
        "SELECT i.id, i.chassi, mo.descricao_qpa AS modelo, i.escaneado_em "
        "FROM assai_carregamento_item i "
        "LEFT JOIN assai_modelo mo ON mo.id=i.modelo_id "
        "WHERE i.carregamento_id=:id ORDER BY i.id"), {'id': carregamento_id}).fetchall()
    return {
        'id': hdr.id, 'status': hdr.status, 'pedido_id': hdr.pedido_id, 'loja_id': hdr.loja_id,
        'separacao_id': hdr.separacao_id, 'iniciado_em': hdr.iniciado_em,
        'finalizado_em': hdr.finalizado_em, 'cancelado_em': hdr.cancelado_em,
        'motivo_cancelamento': hdr.motivo_cancelamento,
        'itens': [{'item_id': r.id, 'chassi': r.chassi, 'modelo': r.modelo or '—',
                   'escaneado_em': r.escaneado_em} for r in itens],
        'total_itens': len(itens),
    }

# _run_write definido na Task 2.

def main():
    pa = argparse.ArgumentParser()
    pa.add_argument('--listar', action='store_true'); pa.add_argument('--detalhar', action='store_true')
    pa.add_argument('--iniciar', action='store_true'); pa.add_argument('--escanear', action='store_true')
    pa.add_argument('--cancelar-item', dest='cancelar_item', action='store_true')
    pa.add_argument('--finalizar', action='store_true'); pa.add_argument('--cancelar', action='store_true')
    pa.add_argument('--alterar', action='store_true')
    pa.add_argument('--status'); pa.add_argument('--pedido-id', dest='pedido_id', type=int)
    pa.add_argument('--loja-id', dest='loja_id', type=int)
    pa.add_argument('--separacao-id', dest='separacao_id', type=int)
    pa.add_argument('--carregamento-id', dest='carregamento_id', type=int)
    pa.add_argument('--item-id', dest='item_id', type=int)
    pa.add_argument('--chassi'); pa.add_argument('--motivo')
    pa.add_argument('--user-id', dest='user_id', type=int)
    pa.add_argument('--confirmar', action='store_true')
    a = pa.parse_args()
    t0 = time.time()
    app = create_app()
    with app.app_context():
        if a.listar:
            out = _run_listar(a.status, a.pedido_id, a.loja_id, a.separacao_id)
        elif a.detalhar:
            out = _run_detalhar(a.carregamento_id)
        else:
            out = _run_write(a)
    if isinstance(out, dict):
        out['_debug'] = {'ms': int((time.time() - t0) * 1000)}
    print(json.dumps(out, default=_json_default, ensure_ascii=False, indent=2))
    sys.exit(out.get('_exit', 0) if isinstance(out, dict) else 0)

if __name__ == '__main__':
    main()
```

(Stub temporário p/ Task 1 passar: `def _run_write(a): return {}` — substituído na Task 2.)

- [ ] **Step 4 — Run (passes)** → `$PY -m pytest tests/skills/carregando_motos_assai/ -q`
- [ ] **Step 5 — Commit** → `git add ... && git commit --no-verify -m "feat(skill): esqueleto + READ carregando-motos-assai (Task 1)"`

---

### Task 2 — WRITE dispatch + salvaguardas

**Files:** Modify script (substituir stub `_run_write`) + test.

- [ ] **Step 1 — Test (autorização, dry-run, confirmar, exceptions)**

```python
def _args(**kw):
    base = dict(iniciar=False, escanear=False, cancelar_item=False, finalizar=False,
                cancelar=False, alterar=False, pedido_id=None, loja_id=None,
                carregamento_id=None, item_id=None, chassi=None, motivo=None,
                user_id=10, confirmar=False)
    base.update(kw); return SimpleNamespace(**base)

def _fake_user(ok=True):
    u = MagicMock(); u.pode_acessar_motos_assai.return_value = ok; return u

def test_write_sem_user_id_erro():
    m = _load()
    res = m._run_write(_args(iniciar=True, pedido_id=9, loja_id=2, user_id=None))
    assert res["erro"] == "user_id_obrigatorio"

def test_write_sem_autorizacao_exit3():
    m = _load()
    with patch("app.auth.models.Usuario") as U:
        U.query.get.return_value = _fake_user(ok=False)
        res = m._run_write(_args(iniciar=True, pedido_id=9, loja_id=2))
    assert res["_exit"] == 3

def test_iniciar_dry_run_nao_chama_service_exit4():
    m = _load()
    with patch("app.auth.models.Usuario") as U, \
         patch("app.motos_assai.services.carregamento_service.criar_carregamento") as cc:
        U.query.get.return_value = _fake_user()
        res = m._run_write(_args(iniciar=True, pedido_id=9, loja_id=2, confirmar=False))
    cc.assert_not_called()
    assert res["_exit"] == 4 and res["dry_run"] is True

def test_iniciar_confirmar_chama_service_e_commita():
    m = _load()
    with patch("app.auth.models.Usuario") as U, \
         patch("app.motos_assai.services.carregamento_service.criar_carregamento", return_value=MagicMock(id=7)) as cc, \
         patch.object(m, "db", MagicMock()) as dbm:
        U.query.get.return_value = _fake_user()
        res = m._run_write(_args(iniciar=True, pedido_id=9, loja_id=2, confirmar=True))
    cc.assert_called_once_with(9, 2, 10)
    dbm.session.commit.assert_called_once()
    assert res["ok"] is True

def test_cancelar_exige_motivo():
    m = _load()
    with patch("app.auth.models.Usuario") as U:
        U.query.get.return_value = _fake_user()
        res = m._run_write(_args(cancelar=True, carregamento_id=1, motivo=None, confirmar=True))
    assert res["erro"] == "motivo_obrigatorio"

def test_exception_state_error_reportada():
    m = _load()
    from app.motos_assai.services.carregamento_service import CarregamentoStateError
    with patch("app.auth.models.Usuario") as U, \
         patch("app.motos_assai.services.carregamento_service.alterar_carregamento",
               side_effect=CarregamentoStateError("ja EM_CARREGAMENTO")), \
         patch.object(m, "db", MagicMock()):
        U.query.get.return_value = _fake_user()
        res = m._run_write(_args(alterar=True, carregamento_id=1, confirmar=True))
    assert "ja EM_CARREGAMENTO" in res["erro"] and res["_exit"] != 0
```

- [ ] **Step 2 — Run (fails: stub)**

- [ ] **Step 3 — Implement `_run_write`** (substituir stub)

```python
def _run_write(a):
    if not a.user_id:
        return {'erro': 'user_id_obrigatorio', '_exit': 2}
    from app.auth.models import Usuario
    u = Usuario.query.get(a.user_id)
    if u is None or not u.pode_acessar_motos_assai():
        return {'erro': 'sem_autorizacao_motos_assai', 'user_id': a.user_id, '_exit': 3}

    from app.motos_assai.services import carregamento_service as cs
    from app.motos_assai.services.carregamento_service import CarregamentoError

    # Define op + validacao de args + descricao p/ preview
    if a.iniciar:
        if not (a.pedido_id and a.loja_id): return {'erro': 'pedido_id_e_loja_id_obrigatorios', '_exit': 2}
        op, fn, args_ = 'iniciar', cs.criar_carregamento, (a.pedido_id, a.loja_id, a.user_id)
    elif a.escanear:
        if not (a.carregamento_id and a.chassi): return {'erro': 'carregamento_id_e_chassi_obrigatorios', '_exit': 2}
        op, fn, args_ = 'escanear', cs.escanear_carregamento_item, (a.carregamento_id, a.chassi, a.user_id)
    elif a.cancelar_item:
        if not a.item_id: return {'erro': 'item_id_obrigatorio', '_exit': 2}
        op, fn, args_ = 'cancelar_item', cs.cancelar_carregamento_item, (a.item_id, a.user_id)
    elif a.finalizar:
        if not a.carregamento_id: return {'erro': 'carregamento_id_obrigatorio', '_exit': 2}
        op, fn, args_ = 'finalizar', cs.finalizar_carregamento, (a.carregamento_id, a.user_id)
    elif a.cancelar:
        if not a.carregamento_id: return {'erro': 'carregamento_id_obrigatorio', '_exit': 2}
        if not a.motivo or len(a.motivo.strip()) < 3: return {'erro': 'motivo_obrigatorio', '_exit': 2}
        op, fn, args_ = 'cancelar', cs.cancelar_carregamento, (a.carregamento_id, a.motivo, a.user_id)
    elif a.alterar:
        if not a.carregamento_id: return {'erro': 'carregamento_id_obrigatorio', '_exit': 2}
        op, fn, args_ = 'alterar', cs.alterar_carregamento, (a.carregamento_id, a.user_id)
    else:
        return {'erro': 'nenhuma_operacao', '_exit': 2}

    if not a.confirmar:
        return {'dry_run': True, 'op': op, 'args': [x for x in args_ if x != a.user_id],
                'aviso': 'sem --confirmar: nada foi alterado', '_exit': 4}

    try:
        ret = fn(*args_)            # service faz flush()
        db.session.commit()         # caller commita (gotcha commit/flush)
        out = {'ok': True, 'op': op}
        if hasattr(ret, 'id'): out['id'] = ret.id
        return out
    except CarregamentoError as e:
        db.session.rollback()
        return {'erro': str(e), 'op': op, 'tipo': type(e).__name__, '_exit': 5}
```

- [ ] **Step 4 — Run (passes)** · **Step 5 — Commit** `feat(skill): WRITE dispatch + salvaguardas carregando-motos-assai (Task 2)`

---

### Task 3 — SKILL.md

- [ ] **Step 1 — Criar** `.claude/skills/carregando-motos-assai/SKILL.md` (frontmatter de skill `name`/`description` USAR/NÃO-USAR/`allowed-tools: Read, Bash, Glob, Grep`; seções Modos/Invocação/Output/Skills-relacionadas). **SE >100 linhas → adicionar `## Sumário` (TOC) (PAD-A C6).** SKILL.md é isento de doc:meta.
- [ ] **Step 2 — Verify** `$PY -c "import yaml; yaml.safe_load(open('.claude/skills/carregando-motos-assai/SKILL.md').read().split('---')[1])"` + `$PY -m py_compile <script>` + `<script> --help`.
- [ ] **Step 3 — Commit** `docs(skill): SKILL.md carregando-motos-assai (Task 3)`

---

### Task 4 — Wiring

- [ ] **Step 1** — `.claude/agents/gestor-motos-assai.md`: adicionar `carregando-motos-assai` ao frontmatter `skills:` (verificar lista exata; inserir em ordem).
- [ ] **Step 2** — `.claude/references/ROUTING_SKILLS.md`: adicionar linha de rota no cluster Assaí (`| MOTOS ASSAÍ — CARREGAMENTO | "carregamentos em andamento", "iniciar/finalizar carregamento", "escanear chassi na carga" | -> carregando-motos-assai |`) + inventário "Skills motos_assai (6)" → (7) + `carregando-motos-assai` na lista.
- [ ] **Step 3** — `app/agente/services/tool_skill_mapper.py`: adicionar `'carregando-motos-assai': '<categoria Assaí dos irmãos>'` (verificar categoria de `acompanhando-saida-assai` e usar a mesma).
- [ ] **Step 4** — `app/motos_assai/CLAUDE.md`: tabela "Skills + Agente" 6→7 (linha `| carregando-motos-assai | READ + WRITE | Carregamento (Sep→NF): iniciar/escanear/finalizar/cancelar/alterar |`) + atualizar roadmap (remover nota de skill faltante). **CLAUDE.md é zona gerenciada — rodar doc_audit no fim.**
- [ ] **Step 5** — `.claude/skills/acompanhando-saida-assai/SKILL.md`: NÃO-USAR-PARA → `Carregamento (usar carregando-motos-assai)`.
- [ ] **Step 6 — Verify** `grep -c carregando-motos-assai` nos 4 arquivos + `ast.parse` do tool_skill_mapper.
- [ ] **Step 7 — Commit** `chore(skill): wiring carregando-motos-assai (Task 4)`

---

### Task 5 — Verificação final

- [ ] **Step 1** — `$PY -m pytest tests/skills/carregando_motos_assai/ -v` (todos PASS)
- [ ] **Step 2** — `$PY -m py_compile <script>` + 8 `--help`/`--<op> --help` OK
- [ ] **Step 3 — anti-bug**: garantir que dry-run NÃO chama service (teste `test_iniciar_dry_run_nao_chama_service_exit4` cobre).
- [ ] **Step 4 — PAD-A**: `$PY scripts/audits/doc_audit.py --enforce-touched` (spec+plano+CLAUDE.md+SKILL.md touched) → OK.
- [ ] **Step 5** — `git log --oneline` + PARAR, mostrar diff ao Rafael (sem merge/push).

---

## Self-Review

**Cobertura da spec:** §3 READ (listar/detalhar)→Task 1 ✓ · 6 WRITE→Task 2 ✓ · §4 salvaguardas (user-id/exit3/dry-run-exit4/confirmar+commit)→Task 2 ✓ · §5 wiring (7 itens)→Tasks 3-4 ✓ · §6 testes mock sem DB→Tasks 1-2 ✓ · §7 PRE-MORTEM (cross-loja/excedente/dry-run-vaza/commit-flush/reabrir-cancelado)→cobertos por exception handling + teste dry-run + teste state-error ✓.

**Placeholders:** os "verificar lista/categoria exata" em Task 4 são verificações pontuais no momento da edição (frontmatter do agente + categoria do mapper) — resolvidos lendo o arquivo na hora, não TBDs de lógica.

**Consistência de tipos:** `_run_listar/_run_detalhar/_run_write`, `cs.criar_carregamento(pedido_id, loja_id, operador_id)` etc. batem com as assinaturas verificadas em `carregamento_service.py`. Exit codes (0/2/3/4/5) consistentes. Colunas (`assai_carregamento`/`_item`) conforme model; `assai_modelo.descricao_qpa` p/ nome — **verificar coluna exata do nome do modelo na impl** (pode ser `descricao_qpa`/`codigo`/`nome`).
