<!-- doc:meta
tipo: how-to
camada: L3
sot_de: plano de implementacao da Onda 4 do PAD-A (varredura por cluster — orfao-zero + link-rot-zero + migracao doc:meta)
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-02
-->

# PAD-A — Onda 4 (Varredura por cluster) Implementation Plan

> **Papel:** plano da Onda 4 do PAD-A — zerar a divida de documentacao do legado (647 docs sem header + 437 orfaos + 34 link-rot + 39 TOC), cluster a cluster, via uma toolchain de migracao + calibracao do lint. **Abra quando:** for implementar a Onda 4 apos OK do Rafael (escopo = VARREDURA do legado de docs; scripts ja governados na Onda 3).
> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recomendado) ou superpowers:executing-plans. Steps usam checkbox (`- [ ]`).
> **Regras INVIOLAVEIS:** ver `docs/superpowers/specs/2026-06-01-arquitetura-de-artefatos-design.md` §8.5 (onda-a-onda c/ OK explicito, so a lista de arquivos do plano, sem refatorar fora de escopo, parametrizar>criar, completude antes de fechar, fato com fonte, re-verificar diagnostico herdado).

**Goal:** levar o `doc_audit.py` a **0 achados** em todo o legado gerenciado (`docs/**`, `.claude/references/**`, `.claude/skills/**`, `app/*/CLAUDE.md`, `CLAUDE.md`) via **sub-ondas gated 4a–4g**, usando uma toolchain de migracao parametrizada (carimba header + injeta Papel/TOC + completa INDEX) + uma calibracao honesta do lint — e, ao fim, **promover C1/C7/C8 a `block`** (gate de commit real).

**Architecture:** a divida tem duas camadas: (1) **visivel** — 647 C1 (header ausente) + 437 C8 (orfao/bidir) + 34 C7 (link-rot) + 39 C6 (TOC) + 1 D3 = 1158 achados; (2) **mascarada** — `checks_struct` curto-circuita docs sem header (so emite C1), e `checks_content` (D2/D4/B5/D1) so dispara quando `tipo` ja existe; logo carimbar headers **desmascara** ~755 C5 + ~180 C6 + C3/C7/D2 latentes. A toolchain resolve isso com um **preview-de-desmascaramento** (dry-run que simula o lint pos-carimbo antes de escrever) + uma **classificacao de tipo que minimiza o desmascaramento** (prefere `explanation`/`how-to`/`state`, reserva `reference` so para SOT real) + uma **calibracao** que afrouxa 3 exigencias que viram "lint-teatro". Cada sub-onda e um checkpoint gated por audit-verde no escopo + OK do Rafael.

**Tech Stack:** Python 3.12 (stdlib: re, json, pathlib, argparse, dataclasses), pytest, `git mv` (preserva historico, arquivamento reversivel via `_deprecated/`), engine `scripts/audits/artefato_lint/` reusado. Sem dependencia externa nova. Reaproveita o scaffold `scripts/docs/novo_artefato.py` (extrai o builder de header para helper compartilhado — C2 parametrizar>criar).

## Indice

- [Premissas e anchor](#premissas)
- [Decisoes consolidadas (4 forks do Rafael)](#decisoes)
- [Mapa de clusters VERIFICADO](#mapa)
- [Calibracao do PAD-A (3 pontos do hibrido)](#calibracao)
- [Roadmap das sub-ondas 4a–4g](#roadmap)
- [Sub-onda 4a — Fundacao & Calibracao (DETALHADA)](#sub-onda-4a)
  - [Task 1 — config: reference exige so Papel](#t1)
  - [Task 2 — D2 (Fontes) vira advisory](#t2)
  - [Task 3 — SKILL.md isento de C6](#t3)
  - [Task 4 — helper compartilhado `_doc_meta.py`](#t4)
  - [Task 5 — gerador de TOC](#t5)
  - [Task 6 — classificador de tipo](#t6)
  - [Task 7 — migrador dry-run (preview-desmascaramento)](#t7)
  - [Task 8 — migrador --write (carimbo idempotente)](#t8)
  - [Task 9 — completar_index.py](#t9)
  - [Task 10 — Canary docs/hora (prova end-to-end)](#t10)
  - [Task 11 — verde + regressao + review](#t11)
- [Decisoes para o Rafael (residuais)](#decisoes-residuais)
- [Fora de escopo Onda 4](#fora-escopo)
- [Riscos](#riscos)
- [Self-Review](#self-review)

---

## Premissas e anchor <a id="premissas"></a>

ANTES de qualquer task, ancorar em verdade (NAO confiar nesta doc cega):

```bash
MAIN=/home/rafaelnascimento/projetos/frete_sistema
git -C "$MAIN" rev-parse --short origin/main          # 9715c8f3d (ou descendente)
PY=$MAIN/.venv/bin/python   # os 2 audits NAO importam o app Flask: ROOT=Path(__file__).parents[2]
$PY $MAIN/scripts/audits/script_audit.py --report-only 2>/dev/null | grep -cE '^SC-'   # 0 (zona scripts governada na Onda 3)
$PY $MAIN/scripts/audits/doc_audit.py --report-only --skip-dup 2>/dev/null | grep -oE '^C[0-9]+|^D[0-9]+' | sort | uniq -c
# Esperado: 647 C1 + 437 C8 + 39 C6 + 34 C7 + 1 D3  (total 1158)
$PY -m pytest $MAIN/tests/audits/ -q                  # 58 passed
```

Se nao bater, RE-INVESTIGUE (NAO assumir). Worktree desta onda: `.claude/worktrees/feat-pad-a-onda-4` (branch `feat/pad-a-onda-4`, base `origin/main 9715c8f3d`).

**Baseline VERIFICADO 2026-06-02 (este plano):**

- **717 docs gerenciados** (nao-scratch); **70 ja com header** (51 YAML de skill + 19 `doc:meta`); **647 sem header = 647 C1**.
- Breakdown por codigo (FONTE: `doc_audit --report-only --skip-dup`, 2026-06-02): **C1=647, C8=437, C6=39, C7=34, D3=1** (total 1158).
- Soma por cluster confere 647: ssw 309 + inventario 97 + skills 56 + superpowers 52 + industrializacao 38 + references(nao-ssw) 42 + blueprint 17 + docs-misc 20 + app-modulos 15 + raiz 1.
- **Os 2 audits sao filesystem+git puros** (nao importam Flask) → rodam pelo caminho ABSOLUTO do `$MAIN` mesmo de outra worktree (ROOT vem de `__file__`). Isso evita a trap cd-na-raiz.

**Insight-chave (a divida real e maior que 1148):** carimbar `doc:meta` **desmascara** findings hoje ocultos:
- `checks_struct` faz `if not m.found: append(C1); return` → **C3, C5, C6, C7, HUB** ficam invisiveis ate o header existir.
- `checks_content` le `tipo` do header; **D2 (Fontes), D4 (hedge), B5 (markers), D1 (glossario)** so disparam quando `tipo == "reference"` → carimbar `tipo:reference` desmascara TODOS eles; `tipo:explanation`/`how-to`/`state` NAO disparam nenhum (sao mais "baratos" e honestos).
- Estimativa de desmascaramento (FONTE: workflow `wf_24e60ea1`, 6 agentes Explore): **~755 C5 + ~180 C6 (TOC)** no agregado SSW+inventario+superpowers.
- **Consequencia de design:** o migrador NUNCA carimba as cegas — roda um **preview** que simula o lint pos-header (Task 7); e a classificacao **prefere os tipos baratos** (Task 6), reservando `reference` so para SOT real.

---

## Decisoes consolidadas (4 forks do Rafael) <a id="decisoes"></a>

Respondidas em 2026-06-02 (AskUserQuestion). Sao **vinculantes** para esta onda:

1. **Cadencia = sub-ondas gated 4a–4g.** Cada cluster = 1 checkpoint com audit-verde no escopo + OK explicito antes da proxima. Este doc = roadmap completo + detalhe da 4a; cada sub-onda seguinte ganha seu proprio plano detalhado quando chegar a vez.
2. **Conformidade = HIBRIDO (injetar honesto + calibrar pesados).** Migrador injeta header + `Papel` (blockquote, sempre honesto) + TOC auto-gerado. Calibra-se 3 pontos que virariam teatro: (a) `reference` exige so `Papel` (Fontes opcional); (b) `SKILL.md` isento de C6; (c) POP NAO e forcado a `runbook` (vira `how-to`/`explanation`). Ver [Calibracao](#calibracao).
3. **Enforcement = promover C1+C7+C8 a `block`** ao fim da 4g (cumpre a promessa da Onda 1: "block pos-Onda 3-4 + OK Rafael").
4. **Arquivo = arquivar HISTORICO/checkpoints velhos como `scratch`/`_deprecated`** (isenta do lint, preserva conteudo); VIVOS (gotchas G014/G017/G038, ADRs D007-D016, SOT, v10 canary) ganham conformance real.

---

## Mapa de clusters VERIFICADO <a id="mapa"></a>

FONTE: `doc_audit` parseado por cluster + verificacao direta no disco (2026-06-02). Ordenado por carga total:

| Cluster | C1 | C6 | C7 | C8 | total | sub-onda |
|---|---:|---:|---:|---:|---:|---|
| `.claude/references/ssw` | 309 | 0 | 0 | 274 | **583** | 4g |
| `docs/inventario-2026-05` | 97 | 0 | 0 | 75 | 172 | 4f |
| `.claude/skills` (nao-SKILL) | 56 | 39 | 34 | 0 | 129 | 4c |
| `docs/superpowers` | 52 | 0 | 0 | 41 | 93 | 4d |
| `docs/industrializacao-fb-lf` | 38 | 0 | 0 | 30 | 68 | 4f |
| `.claude/references` (nao-ssw) | 42 | 0 | 0 | 4 | 47 (+1 D3) | 4b |
| `docs/blueprint-agente` | 17 | 0 | 0 | 13 | 30 | 4f |
| `docs/(raiz)`+pallet+hora+planos | 20 | 0 | 0 | 0 | 20 | 4b/4a-canary |
| `app/*/CLAUDE.md` (15) + raiz (1) | 16+1 | 0 | 0 | 0 | 17 | 4e |

**Fatos verificados que o plano usa (com FONTE):**

- **SSW (583 = 50% do backlog):** 309 docs em 13 subdirs. So `comercial`(73), `fluxos`(21), `operacional`(48) tem `INDEX.md` — e **incompletos** (comercial lista 14/73; operacional 18/48). **10 subdirs SEM INDEX**: `cadastros`(13), `contabilidade`(6), `edi`(4), `embarcador`(4), `financeiro`(28), `fiscal`(22), `logistica`(14), `pops`(45), `relatorios`(12), `visao-geral`(12) → causa-raiz dos 274 C8. Taxonomia: 227 opcoes + 45 POPs + 20 fluxos + 12 visao-geral + 5 transversais na raiz. (FONTE: `find .claude/references/ssw/*/` + leitura dos INDEX.)
- **C7 (34) — reclassificado contra o disco (NAO e bug do lint; a regra de resolucao e deliberada da Onda 1):**
  - **31 "existe, falta `./`":** links bare `references/X.md` e `scripts/X.py` em SKILL.md → a regra resolve root-relative (por design). Os arquivos EXISTEM (verificado: `operando-ssw/references/CADASTROS.md`, `executando-odoo-financeiro/references/erros-comuns.md`, `rastreando-odoo/scripts/rastrear.py` etc.). **Fix = reescrever o link para `./references/...` no SKILL.md** (NUNCA enfraquecer o `resolve_ref`).
  - **2 genuinamente mortos:** `../integracao-odoo/SKILL.md` (de `executando-odoo-financeiro` e `rastreando-odoo`) — `.claude/skills/integracao-odoo/SKILL.md` **nao existe** no disco. Fix = repontar ou remover o link.
  - **1 profundidade errada:** `consultando-quant-odoo/SKILL.md` usa `../../scripts/...` (deveria `../../../scripts/...`); o `VALIDACAO.md` alvo existe. Fix = corrigir o `../`.
- **D3 (1):** `.claude/references/odoo/GOTCHAS.md:490` aponta o campo `observacoes` como pertencente ao model `Separacao` (nao existe). Campo real = `observ_ped_1` (separacao.json:75) ou `obs_separacao` (:190). Ironia: o doc ENSINA isso na linha "ERRADO/CORRETO"; o linter pega o proprio exemplo "ERRADO". **Fix = cercar o exemplo num bloco fenced (linhas fenced sao puladas pelo D3).** (Este plano sofreu o mesmo: ver Self-Review.)
- **Lifecycle dos historicos (FONTE: workflow `wf_24e60ea1`):** `inventario-2026-05`=SEMI_LIVE (gotchas/ADRs/v10 vivos; 99-historia arquivavel); `industrializacao-fb-lf/HISTORICO`(29 docs)=arquivo ("NAO SEGUIR" no README); `blueprint-agente`=LIVE (sem INDEX, precisa criar).

---

## Calibracao do PAD-A (3 pontos do hibrido) <a id="calibracao"></a>

Decisao 2 (hibrido) autoriza afrouxar 3 exigencias que virariam "lint-teatro". Implementadas na 4a com TESTE antes:

1. **`reference` exige so `Papel`** (C5): `required_sections.reference` passa de `["Papel","Fontes"]` para `["Papel"]`. Justificativa: forcar `## Fontes` em ~240 references de conhecimento acumulado geraria secao oca; a citacao continua sendo boa pratica, mas advisory (ponto 2).
2. **D2 (Fontes em reference) vira advisory:** novo flag de config `"require_fontes_reference": false`; `checks_content` emite D2 com severidade `report` (medido, nao bloqueante) quando o flag e false. Mantem visibilidade ("quais references nao citam fonte") sem travar.
3. **`SKILL.md` isento de C6 (TOC):** novo `"toc_exempt_globs": [".claude/skills/**/SKILL.md"]`; `checks_struct` pula C6 nesses paths. Justificativa: `SKILL.md` ja e isento de C1 (usa YAML de skill); um TOC no corpo de uma skill viva e ruido invasivo. (Os 39 C6 atuais somem por aqui — sem tocar 39 arquivos vivos.)

> O ponto (c) da decisao 2 ("POP nao forcado a runbook") **nao e mudanca de config** — e escolha do classificador (Task 6): POPs viram `how-to` (so `Papel`) ou `explanation`, nunca `runbook` (que exigiria Rollback/Verificacao reais). Sem isso, 45 POPs gerariam C5 falso.

**Tudo o que a calibracao NAO faz:** nao remove D3 (acuracia de campo — queremos), nao remove D4/B5 (so disparam em `reference`, e o classificador evita `reference` em doc com hedge/marker), nao cria `tipo` novo (usa os 8 existentes), nao mexe em `script_audit` (zona ja governada).

---

## Roadmap das sub-ondas 4a–4g <a id="roadmap"></a>

Ordenado por **risco crescente da ferramenta** e **dependencia**: constroi e prova a toolchain no menor risco; ataca o elefante (SSW) por ultimo; sela (promove a block) no fim. Cada sub-onda = checkpoint gated por `audit-verde no escopo` + OK explicito do Rafael, com seu **proprio plano detalhado** (este doc detalha so a 4a).

| Sub-onda | Escopo | Entrega | Gate de saida |
|---|---|---|---|
| **4a** | Fundacao & Calibracao + canary `docs/hora` | migrador + completar_index + 3 calibracoes + helper + testes; prova em 2 docs | `doc_audit --path docs/hora` = 0; calibracao testada; 58→~61 pytest |
| **4b** | `references` nao-ssw (42) + `docs/pallet,planos` (5) + D3 fix | carimbo + INDEX pallet/planos + fence D3 + fix perms tier-frio | `--path .claude/references` (nao-ssw) e `--path docs/pallet|planos` sem C1/C7/D3 |
| **4c** | `.claude/skills` (56 C1 + 34 C7) | carimbo 56 nao-SKILL; reescreve 31 links `./`; repoint 2 mortos; fix 1 depth | skills C1=0, C7=0 (C6 ja zerado na 4a) |
| **4d** | `docs/superpowers` (52 C1 + 41 C8) — DOGFOODING | carimbo + completa plans/specs/reports INDEX + TOC | superpowers C1=0, C8=0, C6=0 |
| **4e** | `app/*/CLAUDE.md` (16) + `CLAUDE.md` raiz — L1 CIRURGICO | carimbo `tipo:explanation` (Papel+Contexto); controlador faz, NAO delega | 17 docs C1=0; L1 intacto |
| **4f** | historicos: `inventario-2026-05`+`industrializacao-fb-lf`+`blueprint-agente` | arquiva HISTORICO/velhos (scratch/_deprecated); conformance nos vivos; completa/cria INDEX | 3 clusters C1=0, C8=0 |
| **4g** | `.claude/references/ssw` (309 + 10 INDEX) + **SELAGEM** | 10 INDEX + completa 3 + carimbo 309 + TOC; depois promove C1/C7/C8 a `block` + regressao + atualiza `CLAUDE.md` L1 | `doc_audit --report-only` = 0 GLOBAL; pre-commit bloqueia; pytest verde |

**Ordem inviolavel intra-cluster (licao do SSW agent, risk R2):** para cada cluster — (1) **estrutura primeiro** (criar/completar INDEX → zera C8), (2) **depois carimbo** (header → zera C1 sem desmascarar C8 novo), (3) **depois desmascarados** (C5/C6/C7 que emergirem). O preview (Task 7) mostra os 3 antes de tocar.

---

## Sub-onda 4a — Fundacao & Calibracao (DETALHADA) <a id="sub-onda-4a"></a>

**Goal da 4a:** entregar a toolchain (`migrar_doc_meta.py` + `completar_index.py` + helper `_doc_meta.py`) e as 3 calibracoes, com TESTE antes de cada, provadas end-to-end num canary minimo (`docs/hora`, 2 docs) — para que 4b–4g sejam migracao mecanica com visibilidade total do desmascaramento.

**File Structure (4a):**

```
scripts/audits/artefato_lint.config.json        # MODIFICAR: required_sections.reference, +require_fontes_reference, +toc_exempt_globs
scripts/audits/artefato_lint/checks_content.py   # MODIFICAR: D2 le flag e vira report
scripts/audits/artefato_lint/checks_struct.py    # MODIFICAR: C6 pula toc_exempt_globs
scripts/audits/artefato_lint/config.py           # MODIFICAR (se preciso): expor novos campos no objeto cfg
scripts/docs/_doc_meta.py                        # CRIAR: build_header() + required_section_stubs() + gen_toc() (shared)
scripts/docs/novo_artefato.py                    # MODIFICAR: reusa _doc_meta.build_header (C2 parametrizar>criar)
scripts/docs/migrar_doc_meta.py                  # CRIAR: classify() + preview(dry-run) + apply(--write)
scripts/docs/completar_index.py                  # CRIAR: lista leaves + garante listagem no INDEX (idempotente)
tests/audits/test_calibracao_onda4.py            # CRIAR: TDD das 3 calibracoes
tests/docs/test_migrar_doc_meta.py               # CRIAR: TDD classificador + preview + apply (fixtures inline)
tests/docs/test_completar_index.py               # CRIAR: TDD completar_index
docs/hora/INDEX.md                               # CRIAR (canary): hub de docs/hora
docs/hora/*.md (2)                               # MODIFICAR (canary): carimbo via migrador
docs/INDEX.md                                    # MODIFICAR (canary): +ponteiro docs/hora/INDEX.md (item-9)
```

> **Disciplina de execucao da 4a:** Tasks 1–9 (toolchain/lint) podem ser delegadas a subagente com a lista de arquivos TRANCADA + `--no-verify` PROIBIDO. Task 10 (canary, toca DOC vivo) e Task 11 = **controlador faz cirurgico** (licao Onda 3 Fase 4). Verificar output de subagente INDEPENDENTEMENTE (rodar o audit, nao confiar no resumo).

### Task 1 — config: `reference` exige so `Papel` <a id="t1"></a>

**Files:**
- Modify: `scripts/audits/artefato_lint.config.json`
- Test: `tests/audits/test_calibracao_onda4.py`

- [ ] **Step 1: Escrever o teste que falha**

```python
# tests/audits/test_calibracao_onda4.py
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.audits.artefato_lint import config, checks_struct

def _write(tmp_path, rel, text):
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p

def test_reference_sem_fontes_nao_gera_c5(tmp_path):
    cfg = config.load()
    doc = ("<!-- doc:meta\ntipo: reference\ncamada: L2\nsot_de: x\n"
           "hub: docs/INDEX.md\nsuperseded_by: —\natualizado: 2026-06-02\n-->\n"
           "# T\n\n> **Papel:** y.\n\n## Conteudo\n\nfoo\n")
    p = _write(tmp_path, "docs/x.md", doc)
    (tmp_path / "docs" / "INDEX.md").write_text("# i", encoding="utf-8")
    codes = [f.code for f in checks_struct.check_file(p, tmp_path, cfg)]
    assert "C5" not in codes, f"Fontes nao deve mais ser obrigatoria em reference; achou {codes}"
```

- [ ] **Step 2: Rodar e ver falhar** — `Run: $PY -m pytest tests/audits/test_calibracao_onda4.py::test_reference_sem_fontes_nao_gera_c5 -v` · Expected: FAIL (C5 "Fontes" presente).

- [ ] **Step 3: Editar o config** — em `scripts/audits/artefato_lint.config.json`, trocar `"reference": ["Papel", "Fontes"]` por `"reference": ["Papel"]`.

- [ ] **Step 4: Rodar e ver passar** — `Run: $PY -m pytest tests/audits/test_calibracao_onda4.py::test_reference_sem_fontes_nao_gera_c5 -v` · Expected: PASS.

- [ ] **Step 5: Commit** — `git commit -m "feat(pad-a onda4): reference exige so Papel (Fontes opcional via C5) [skip render]"`

### Task 2 — D2 (Fontes) vira advisory <a id="t2"></a>

**Files:**
- Modify: `scripts/audits/artefato_lint.config.json` (+ `"require_fontes_reference": false`)
- Modify: `scripts/audits/artefato_lint/config.py` (expor `require_fontes_reference` em `cfg`, default `False`)
- Modify: `scripts/audits/artefato_lint/checks_content.py:38-40` (D2)
- Test: `tests/audits/test_calibracao_onda4.py`

- [ ] **Step 1: Teste que falha**

```python
def test_d2_fontes_advisory_quando_flag_false(tmp_path):
    from scripts.audits.artefato_lint import checks_content
    cfg = config.load()
    doc = ("<!-- doc:meta\ntipo: reference\ncamada: L2\nsot_de: x\n"
           "hub: docs/INDEX.md\nsuperseded_by: —\natualizado: 2026-06-02\n-->\n"
           "# T\n\n> **Papel:** y.\n\n## Conteudo\n\nfoo sem citacao\n")
    p = _write(tmp_path, "docs/y.md", doc)
    fs = checks_content.check_file(p, tmp_path, cfg)
    d2 = [f for f in fs if f.code == "D2"]
    assert d2, "D2 ainda deve ser EMITIDO (visibilidade)"
    assert all(f.severity == "report" for f in d2), f"D2 deve ser advisory, nao block: {[f.severity for f in d2]}"
```

- [ ] **Step 2: Rodar e ver falhar** — `Run: $PY -m pytest tests/audits/test_calibracao_onda4.py::test_d2_fontes_advisory_quando_flag_false -v` · Expected: FAIL (D2 vem como `block`).

- [ ] **Step 3: Implementar**
  - No config: adicionar `"require_fontes_reference": false`.
  - Em `config.py`: garantir que o objeto `cfg` exponha `require_fontes_reference` (ler de `raw`, default `False`).
  - Em `checks_content.py` D2, trocar a severidade por advisory quando o flag e false:

```python
    # D2 citacao em reference
    if tipo == "reference":
        if not re.search(r"(?im)^#{1,4}\s*fontes\b", text) and "FONTE:" not in text:
            sev = "block" if getattr(cfg, "require_fontes_reference", False) else "report"
            out.append(Finding("D2", rel, 1, "reference sem '## Fontes' nem 'FONTE:'", sev))
```

- [ ] **Step 4: Rodar e ver passar** — `Run: $PY -m pytest tests/audits/test_calibracao_onda4.py::test_d2_fontes_advisory_quando_flag_false -v` · Expected: PASS.

- [ ] **Step 5: Commit** — `git commit -m "feat(pad-a onda4): D2 Fontes vira advisory (require_fontes_reference=false) [skip render]"`

### Task 3 — `SKILL.md` isento de C6 (TOC) <a id="t3"></a>

**Files:**
- Modify: `scripts/audits/artefato_lint.config.json` (+ `"toc_exempt_globs": [".claude/skills/**/SKILL.md"]`)
- Modify: `scripts/audits/artefato_lint/config.py` (expor `toc_exempt_globs`, default `[]`)
- Modify: `scripts/audits/artefato_lint/checks_struct.py:53-56` (C6)
- Test: `tests/audits/test_calibracao_onda4.py`

- [ ] **Step 1: Teste que falha**

```python
def test_skill_md_isento_de_c6(tmp_path):
    cfg = config.load()
    body = "---\nname: foo\ndescription: bar\n---\n\n# Skill\n" + ("\nlinha" * 130)
    p = _write(tmp_path, ".claude/skills/foo/SKILL.md", body)
    codes = [f.code for f in checks_struct.check_file(p, tmp_path, cfg)]
    assert "C6" not in codes, f"SKILL.md deve ser isento de C6; achou {codes}"
```

- [ ] **Step 2: Rodar e ver falhar** — Expected: FAIL (C6 presente, >100 linhas sem TOC).

- [ ] **Step 3: Implementar**
  - Config: `"toc_exempt_globs": [".claude/skills/**/SKILL.md"]`.
  - `config.py`: expor `toc_exempt_globs` (default `[]`).
  - `checks_struct.py` C6 — pular se o path casa um toc_exempt_glob:

```python
    # C6 TOC se >100 linhas
    from . import zones
    nlines = text.count("\n") + 1
    toc_exempt = zones._match_any(rel, getattr(cfg, "toc_exempt_globs", []))
    if nlines > cfg.toc_min_lines and not toc_exempt and not re.search(
            r"(?im)^#{1,3}\s*(indice|table of contents|toc)\b", text):
        out.append(Finding("C6", rel, 1, f"arquivo {nlines} linhas sem TOC", "block"))
```

- [ ] **Step 4: Rodar e ver passar** — Expected: PASS. E confirmar globalmente que C6 cai: `Run: $PY scripts/audits/doc_audit.py --report-only --skip-dup 2>/dev/null | grep -c '^C6'` · Expected: 0.

- [ ] **Step 5: Commit** — `git commit -m "feat(pad-a onda4): SKILL.md isento de C6/TOC (toc_exempt_globs) [skip render]"`

### Task 4 — helper compartilhado `_doc_meta.py` <a id="t4"></a>

**Files:**
- Create: `scripts/docs/_doc_meta.py`
- Modify: `scripts/docs/novo_artefato.py` (reusa o helper — C2 parametrizar>criar)
- Test: `tests/docs/test_migrar_doc_meta.py` (suite shared)

- [ ] **Step 1: Teste que falha**

```python
# tests/docs/test_migrar_doc_meta.py
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.docs import _doc_meta

def test_build_header_campos_obrigatorios():
    h = _doc_meta.build_header(tipo="explanation", tema="X", hub="docs/INDEX.md",
                               data="2026-06-02", camada="L3", sot_de="—")
    for campo in ("tipo: explanation", "camada: L3", "sot_de: —",
                  "hub: docs/INDEX.md", "superseded_by: —", "atualizado: 2026-06-02"):
        assert campo in h, f"header faltando {campo!r}: {h}"
    assert h.startswith("<!-- doc:meta") and "-->" in h
```

- [ ] **Step 2: Rodar e ver falhar** — Expected: FAIL (modulo `_doc_meta` nao existe).

- [ ] **Step 3: Implementar `_doc_meta.py`**

```python
# scripts/docs/_doc_meta.py
"""Helpers compartilhados de doc:meta (scaffold + migrador). Sem dependencia do app."""
from __future__ import annotations
import re

def build_header(tipo: str, tema: str, hub: str, data: str,
                 camada: str = "L2", sot_de: str = "—", superseded_by: str = "—") -> str:
    return (f"<!-- doc:meta\ntipo: {tipo}\ncamada: {camada}\nsot_de: {sot_de}\n"
            f"hub: {hub}\nsuperseded_by: {superseded_by}\natualizado: {data}\n-->\n")

def required_section_stubs(tipo: str, cfg) -> list[str]:
    """Headings minimos honestos por tipo (Papel sai como blockquote, nao heading)."""
    secs = [s for s in cfg.required_sections.get(tipo, []) if s.lower() != "papel"]
    return [f"## {s}" for s in secs]

_H = re.compile(r"^(#{2,3})\s+(.*)$")
def slug(s: str) -> str:
    s = re.sub(r"[^\w\s-]", "", s.lower()).strip()
    return re.sub(r"\s+", "-", s)

def gen_toc(text: str) -> str:
    """Gera '## Indice' a partir de headings H2/H3 (pula linhas fenced e o proprio Indice)."""
    out, in_fence = [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence; continue
        if in_fence:
            continue
        m = _H.match(line)
        if not m:
            continue
        depth, title = len(m.group(1)) - 2, m.group(2).strip()
        if re.match(r"(?i)(indice|table of contents|toc)\b", title):
            continue
        out.append(f"{'  ' * depth}- [{title}](#{slug(title)})")
    return "## Indice\n\n" + "\n".join(out) + "\n" if out else ""
```

- [ ] **Step 4: Refatorar `novo_artefato.py:build`** para chamar `_doc_meta.build_header(...)` em vez de montar a string inline (mantem comportamento; o teste de `novo_artefato` — se existir — continua verde; senao smoke: `Run: $PY scripts/docs/novo_artefato.py --tipo reference --tema T --hub docs/INDEX.md --out /tmp/_smoke.md && head -3 /tmp/_smoke.md`).

- [ ] **Step 5: Rodar e ver passar** — `Run: $PY -m pytest tests/docs/test_migrar_doc_meta.py::test_build_header_campos_obrigatorios -v` · Expected: PASS.

- [ ] **Step 6: Commit** — `git commit -m "feat(pad-a onda4): helper _doc_meta compartilhado (header/stubs/toc) + novo_artefato reusa [skip render]"`

### Task 5 — gerador de TOC <a id="t5"></a>

**Files:**
- Modify: `scripts/docs/_doc_meta.py` (ja tem `gen_toc` da Task 4 — aqui so o teste)
- Test: `tests/docs/test_migrar_doc_meta.py`

- [ ] **Step 1: Teste que falha**

```python
def test_gen_toc_pula_fenced_e_gera_anchors():
    txt = ("# T\n\n## Alpha\n\ntexto\n\n```\n## NaoConta\n```\n\n## Beta Dois\n\nfim\n")
    toc = _doc_meta.gen_toc(txt)
    assert "## Indice" in toc
    assert "- [Alpha](#alpha)" in toc
    assert "- [Beta Dois](#beta-dois)" in toc
    assert "NaoConta" not in toc, "heading dentro de fence nao entra no TOC"
```

- [ ] **Step 2: Rodar e ver passar** (gen_toc ja implementado na Task 4) — `Run: $PY -m pytest tests/docs/test_migrar_doc_meta.py::test_gen_toc_pula_fenced_e_gera_anchors -v` · Expected: PASS. (Se FAIL, corrigir `gen_toc`.)

- [ ] **Step 3: Commit** — `git commit -m "test(pad-a onda4): cobertura gen_toc (fenced + anchors) [skip render]"`

### Task 6 — classificador de tipo <a id="t6"></a>

**Files:**
- Create: `scripts/docs/migrar_doc_meta.py` (so o `classify` + CLI esqueleto nesta task)
- Test: `tests/docs/test_migrar_doc_meta.py`

Heuristica (minimiza desmascaramento — prefere tipos baratos; reserva `reference` para SOT real; arquiva HISTORICO):

| Padrao de path/conteudo | tipo | camada |
|---|---|---|
| `**/SKILL.md` ou YAML `name:` | (pular — ja conforme) | — |
| basename `INDEX.md`/`README.md` | `index` | L1 |
| `**/pops/**` ou basename `POP-*` | `how-to` | L2 |
| `**/fluxos/**` ou basename `F\d\d-` | `explanation` | L3 |
| `**/visao-geral/**`, `CHECKPOINT*`, `AUDIT_LOG*`, `SOT*`, `PENDENCIAS*`, `*STATUS*` | `state` | L3 |
| `**/HISTORICO/**`, `**/99-historia/**`, `PROMPT_PROXIMA*` | `scratch` | — |
| basename `D\d{3}-*` (ADR) | `explanation` | L3 |
| `app/*/CLAUDE.md`, `CLAUDE.md` | `explanation` | L1 |
| em `.claude/references/` raiz/`modelos`/`odoo`/`negocio` (SOT) | `reference` | L2 |
| default (doc de conhecimento) | `explanation` | L3 |

- [ ] **Step 1: Teste que falha**

```python
def test_classify_minimiza_desmascaramento(tmp_path):
    from scripts.docs import migrar_doc_meta as M
    casos = {
        ".claude/references/ssw/pops/POP-D06-x.md": "how-to",
        ".claude/references/ssw/fluxos/F01-x.md": "explanation",
        ".claude/references/ssw/visao-geral/x.md": "state",
        "docs/inventario-2026-05/99-historia/CHECKPOINT_x.md": "scratch",
        "docs/inventario-2026-05/00-decisoes/D007-x.md": "explanation",
        "app/odoo/CLAUDE.md": "explanation",
        ".claude/references/INFRAESTRUTURA.md": "reference",
        "docs/blueprint-agente/eixo-x.md": "explanation",
    }
    for rel, esperado in casos.items():
        tipo, _camada = M.classify(rel, "conteudo qualquer")
        assert tipo == esperado, f"{rel}: esperava {esperado}, veio {tipo}"
```

- [ ] **Step 2: Rodar e ver falhar** — Expected: FAIL (`migrar_doc_meta` nao existe).

- [ ] **Step 3: Implementar `classify(rel, text) -> (tipo, camada)`** com a tabela acima (regex por path; ordem do mais especifico ao default). Sem efeito colateral (funcao pura).

- [ ] **Step 4: Rodar e ver passar** — Expected: PASS.

- [ ] **Step 5: Commit** — `git commit -m "feat(pad-a onda4): classificador de tipo (minimiza desmascaramento) [skip render]"`

### Task 7 — migrador dry-run (preview-desmascaramento) <a id="t7"></a>

**Files:**
- Modify: `scripts/docs/migrar_doc_meta.py` (modo `--dry-run`, DEFAULT)
- Test: `tests/docs/test_migrar_doc_meta.py`

O dry-run e o coracao da onda: para cada doc do scope, classifica, monta o header, e **simula o lint pos-header** (escreve numa copia em memoria/tmp e roda `checks_struct`+`checks_content`) para listar o que **desmascararia** (C5/C6/C7/D2...). NAO escreve no doc real.

- [ ] **Step 1: Teste que falha**

```python
def test_dry_run_nao_escreve_e_preve_desmascaramento(tmp_path, capsys):
    from scripts.docs import migrar_doc_meta as M
    (tmp_path / "docs").mkdir(parents=True)
    (tmp_path / "docs" / "INDEX.md").write_text("# i", encoding="utf-8")
    alvo = tmp_path / "docs" / "longo.md"
    alvo.write_text("# Titulo\n\n" + "\n".join(f"## S{i}\n\ntexto" for i in range(40)), encoding="utf-8")
    antes = alvo.read_text(encoding="utf-8")
    rc = M.run(scope_root=tmp_path, paths=["docs/longo.md"], write=False)
    assert rc == 0
    assert alvo.read_text(encoding="utf-8") == antes, "dry-run NAO pode escrever"
    out = capsys.readouterr().out
    assert "docs/longo.md" in out and ("C6" in out or "TOC" in out or "Indice" in out)
```

- [ ] **Step 2: Rodar e ver falhar** — Expected: FAIL (`M.run` nao existe).

- [ ] **Step 3: Implementar `run(scope_root, paths, write=False)`** — para cada path: ler, `classify`, `build_header` + `Papel` + stubs + (se >100 linhas e tipo!=index) `gen_toc`; montar o texto candidato em memoria; rodar `checks_struct.check_file`/`checks_content.check_file` sobre um arquivo temporario com o candidato; imprimir relatorio `path | tipo | findings-que-restariam`. `write=False` nunca toca o disco real. Idempotente: se ja tem header, pular.

- [ ] **Step 4: Rodar e ver passar** — Expected: PASS.

- [ ] **Step 5: Commit** — `git commit -m "feat(pad-a onda4): migrador dry-run com preview de desmascaramento [skip render]"`

### Task 8 — migrador `--write` (carimbo idempotente) <a id="t8"></a>

**Files:**
- Modify: `scripts/docs/migrar_doc_meta.py` (modo `--write`)
- Test: `tests/docs/test_migrar_doc_meta.py`

- [ ] **Step 1: Teste que falha**

```python
def test_write_carimba_e_fica_verde(tmp_path):
    from scripts.docs import migrar_doc_meta as M
    from scripts.audits.artefato_lint import config, checks_struct, checks_content
    (tmp_path / "docs").mkdir(parents=True)
    (tmp_path / "docs" / "INDEX.md").write_text("# i", encoding="utf-8")
    alvo = tmp_path / "docs" / "conhecimento.md"
    alvo.write_text("# Conhecimento\n\n" + "\n".join(f"## S{i}\n\ntexto" for i in range(40)), encoding="utf-8")
    assert M.run(scope_root=tmp_path, paths=["docs/conhecimento.md"], write=True) == 0
    cfg = config.load()
    fs = checks_struct.check_file(alvo, tmp_path, cfg) + checks_content.check_file(alvo, tmp_path, cfg)
    blk = [f for f in fs if f.severity == "block"]
    assert blk == [], f"pos-carimbo deve ficar SEM bloqueante; restou {[(f.code,f.message) for f in blk]}"
    # idempotencia
    txt1 = alvo.read_text(encoding="utf-8")
    M.run(scope_root=tmp_path, paths=["docs/conhecimento.md"], write=True)
    assert alvo.read_text(encoding="utf-8") == txt1, "segundo --write nao pode re-carimbar"
```

- [ ] **Step 2: Rodar e ver falhar** — Expected: FAIL (write nao implementado).

- [ ] **Step 3: Implementar o ramo `write=True`** — prepende header; garante `> **Papel:** <derivado do titulo/1a frase>`; insere os stubs de secao (com 1 linha-ponteiro honesta, ex.: `<!-- preencher: ... -->` NAO — usar ponteiro real ou `> ver fonte`); insere `## Indice` (gen_toc) logo apos o bloco Papel se >100 linhas e tipo != index. Idempotente (skip se `parse_doc().found`). Preserva o `# Titulo` e corpo.

- [ ] **Step 4: Rodar e ver passar** — Expected: PASS.

- [ ] **Step 5: Commit** — `git commit -m "feat(pad-a onda4): migrador --write idempotente (header+Papel+TOC+stubs) [skip render]"`

### Task 9 — `completar_index.py` <a id="t9"></a>

**Files:**
- Create: `scripts/docs/completar_index.py`
- Test: `tests/docs/test_completar_index.py`

- [ ] **Step 1: Teste que falha**

```python
# tests/docs/test_completar_index.py
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.docs import completar_index as CI

def test_cria_index_listando_todos_os_leaves(tmp_path):
    d = tmp_path / "docs" / "area"
    d.mkdir(parents=True)
    (d / "a.md").write_text("# A", encoding="utf-8")
    (d / "b.md").write_text("# B", encoding="utf-8")
    rc = CI.run(scope_root=tmp_path, subdir="docs/area", create=True, write=True)
    assert rc == 0
    idx = (d / "INDEX.md").read_text(encoding="utf-8")
    assert "tipo: index" in idx
    assert "a.md" in idx and "b.md" in idx, "INDEX deve listar todos os leaves"
```

- [ ] **Step 2: Rodar e ver falhar** — Expected: FAIL (`completar_index` nao existe).

- [ ] **Step 3: Implementar `run(scope_root, subdir, create, write)`** — lista `*.md` (exceto o proprio INDEX); se `create` e nao existe INDEX, cria com header `tipo:index, camada:L1, hub:<self>` + 1 item de lista por leaf apontando para o arquivo (titulo lido do H1 de cada); se ja existe, **adiciona apenas os faltantes** (idempotente; nao reordena/duplica). `write=False` = dry-run.

- [ ] **Step 4: Rodar e ver passar** — Expected: PASS.

- [ ] **Step 5: Commit** — `git commit -m "feat(pad-a onda4): completar_index.py (cria/completa INDEX listando leaves) [skip render]"`

### Task 10 — Canary `docs/hora` (prova end-to-end) <a id="t10"></a>

**Files (CONTROLADOR faz, nao delega):**
- Modify: `docs/hora/*.md` (2 docs) via migrador
- Create: `docs/hora/INDEX.md` via completar_index
- Modify: `docs/INDEX.md` (+1 ponteiro `docs/hora/INDEX.md`)

- [ ] **Step 1: Dry-run e revisar o preview** — `Run: $PY scripts/docs/migrar_doc_meta.py --scope-root . --paths docs/hora/INVARIANTES.md docs/hora/<segundo>.md` (ajustar nomes via `ls docs/hora/`). Expected: preview mostra `tipo` classificado + 0 findings residuais bloqueantes (ou listar os que precisam de ajuste manual).

- [ ] **Step 2: Aplicar carimbo** — `Run: $PY scripts/docs/migrar_doc_meta.py --scope-root . --paths docs/hora/*.md --write` · Expected: 2 docs carimbados; idempotente na 2a chamada.

- [ ] **Step 3: Criar o hub** — `Run: $PY scripts/docs/completar_index.py --scope-root . --subdir docs/hora --create --write` · Expected: `docs/hora/INDEX.md` criado listando os 2 docs.

- [ ] **Step 4: Ligar ao mestre (item-9 + C8)** — editar `docs/INDEX.md`: adicionar 1 ponteiro de corpo para `docs/hora/INDEX.md` na secao apropriada (alimenta o BFS do C8; NAO usar campo `hub:`).

- [ ] **Step 5: Verificar verde no escopo** — `Run: $PY scripts/audits/doc_audit.py --report-only --skip-dup 2>/dev/null | grep -E 'docs/hora'` · Expected: vazio (0 achados em docs/hora). E `--path docs/hora` strict: `$PY scripts/audits/doc_audit.py --strict --path docs/hora 2>/dev/null; echo "exit=$?"` · Expected: exit 0.

- [ ] **Step 6: Commit** — `git commit -m "docs(pad-a onda4a): canary docs/hora carimbado + INDEX + ligado ao mestre [skip render]"`

### Task 11 — verde + regressao + review <a id="t11"></a>

**Files:**
- Create: `tests/audits/test_onda4a_toolchain.py` (regressao: calibracao + canary conformes)
- Modify: `docs/superpowers/plans/INDEX.md` (+ ponteiro para este plano — item-9, se ainda nao listado)

- [ ] **Step 1: Teste de regressao**

```python
# tests/audits/test_onda4a_toolchain.py
import subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]

def _audit(args):
    return subprocess.run([sys.executable, "scripts/audits/doc_audit.py", *args],
                          cwd=ROOT, capture_output=True, text=True).stdout

def test_canary_hora_conforme():
    out = _audit(["--report-only", "--skip-dup"])
    assert not [l for l in out.splitlines() if l.startswith(("C1","C3","C5","C6","C7")) and "docs/hora" in l]

def test_c6_zerado_apos_isencao_skill_md():
    out = _audit(["--report-only", "--skip-dup"])
    assert sum(1 for l in out.splitlines() if l.startswith("C6")) == 0
```

- [ ] **Step 2: Rodar a suite inteira** — `Run: $PY -m pytest tests/audits/ tests/docs/ -q` · Expected: tudo verde (58 antigos + novos da 4a).

- [ ] **Step 3: Confirmar que o legado NAO regrediu** — `Run: $PY scripts/audits/doc_audit.py --report-only --skip-dup 2>/dev/null | grep -oE '^C[0-9]+|^D[0-9]+' | sort | uniq -c` · Expected: C1 inalterado (~635, -2 do canary), **C6=0** (isencao), C7/C8/D3 inalterados. Nenhum codigo NOVO de bloqueio em massa (prova que a calibracao nao quebrou docs ja-headerados).

- [ ] **Step 4: Review** — requesting-code-review (2 lentes: conformidade PAD-A + o migrador nao corrompe corpo de doc). Verificar manualmente o diff dos 2 docs do canary (corpo intacto, header correto).

- [ ] **Step 5: Registrar este plano** — garantir `docs/superpowers/plans/INDEX.md` lista `2026-06-02-pad-a-onda-4-varredura-cluster.md` (item-9). Commit: `git commit -m "test(pad-a onda4a): regressao toolchain + registra plano no INDEX [skip render]"`

- [ ] **Step 6: GATE 4a** — apresentar ao Rafael: `doc_audit --path docs/hora` = 0, C6 global = 0, pytest verde. **NAO iniciar 4b sem OK explicito.**

---

## Decisoes para o Rafael (residuais) <a id="decisoes-residuais"></a>

As 4 grandes ja decididas ([Decisoes consolidadas](#decisoes)). Residuais (defaults propostos; veta se quiser):

1. **Canary da 4a = `docs/hora` (2 docs).** Menor cluster seguro que exercita header+Papel+TOC+INDEX+C8 end-to-end. `pallet`/`planos` ficam p/ 4b por terem perms tier-frio (600/700) — risco de o git marcar como deleted (verificar `git config core.fileMode` antes). Alternativa: canary em `.claude/references/modelos` (exercita `reference`+D2-advisory). **Default: docs/hora.**
2. **tipo de `app/*/CLAUDE.md` = `explanation`** (Papel+Contexto), NAO `reference` (evita desmascarar D2/D3/D4/B5 nos L1) nem `index` (HUB-check de prosa). Confirmar na 4e.
3. **`scratch` vs `_deprecated/`** para arquivar historicos: `scratch` (header `tipo: scratch`, fica no lugar, isenta) e menos invasivo que `git mv` para `_deprecated/`. **Default: `tipo: scratch` in-place** para docs isolados; `_deprecated/` so para subpastas inteiras (ex.: `industrializacao-fb-lf/HISTORICO/`).
4. **`integracao-odoo/SKILL.md` ausente (2 C7 reais):** existe a *skill* `integracao-odoo` no catalogo, mas nao o arquivo no disco — investigar na 4c se foi movida/renomeada (repontar) ou se o link deve apontar para o doc real. **Nao assumir; verificar na 4c.**
5. **Ordem 4b–4g:** proposta no [roadmap](#roadmap). Reavaliavel a cada gate (ex.: antecipar 4e se quiser os L1 conformes antes).

---

## Fora de escopo Onda 4 <a id="fora-escopo"></a>

- **NAO** mexer em `script_audit`/zona de scripts (governada na Onda 3).
- **NAO** enfraquecer a regra `resolve_ref` (C7 deliberada da Onda 1) — C7 se resolve no DOC (`./` prefix), nao no lint.
- **NAO** reorganizar/mover docs alem do necessario para hub/arquivo (ex.: NAO migrar `pallet` para dentro de `industrializacao-fb-lf` — sugestao de subagente recusada; fora de escopo §8.5 regra 4).
- **NAO** criar `tipo` novo (`module-guide` etc.) nem fase `--check-d3` no lint — usar os 8 tipos existentes; D3 ja roda.
- **NAO** atualizar conteudo operacional/numerico dos docs (so estrutura/header/links/TOC; correcao de fato so no D3 pontual).
- **NAO** tocar memorias (`MEMORY.md` 155→≤150 e pendencia separada da Onda 2) nem `worker_atacadao.py` (fora de docs).
- **NAO** mergear em `main` sem OK explicito; commits de doc/lint com `[skip render]`.

## Riscos <a id="riscos"></a>

- **Desmascaramento surpresa (R-PRINCIPAL):** carimbar header revela C5/C6/C7 ocultos. Mitigado pelo **preview (Task 7)** rodado ANTES de todo `--write`, e pela classificacao que prefere tipos baratos. Cada gate confere o agregado de codigos antes/depois.
- **Migrador corrompe corpo de doc:** mitigado por idempotencia + Task 8 teste de re-run + review manual do diff no canary + `--write` so apos dry-run revisado.
- **C8 nao zera so com header:** C8 e estrutural (INDEX). Ordem inviolavel: **estrutura (INDEX) ANTES do carimbo**. O completar_index (Task 9) zera C8 por cluster; o header zera C1.
- **Creation gate bloquear os proprios artefatos novos** (INDEX/plano): mitigado escrevendo-os ja conformes (header + Papel + Indice) — este plano e prova (dogfooding).
- **Cross-worktree hook / cwd orfao:** rodar tudo pelo caminho ABSOLUTO ou `git -C`; NAO `cd` na raiz; NAO remover a worktree de dentro dela (licao Onda 3).
- **Promocao a block (4g) quebrar commits de outras frentes:** so promover apos `doc_audit --report-only` = 0 GLOBAL; `--enforce-touched` so pega arquivos do diff, entao frentes que nao tocam doc nao sofrem. Anunciar a promocao.
- **Perms tier-frio (pallet/planos):** `git config core.fileMode` pode marcar deleted ao tocar; verificar antes (4b).

## Self-Review <a id="self-review"></a>

- **Cobertura do spec §8 Onda 4** ("cada cluster → orfao-zero + link-rot-zero"): C8 (orfao) coberto por completar_index em cada sub-onda; C7 (link-rot) coberto na 4c (skills) + onde emergir; C1 (migracao header) em todas; C6 zerado por isencao (4a) + TOC (migrador). ✓
- **Placeholders:** nenhuma Task usa "TBD/implementar depois"; todo Step de codigo tem o codigo. As partes "ajustar nomes via ls" (Task 10) sao operacionais do canary, nao placeholders de design. ✓
- **Consistencia de tipos:** `_doc_meta.build_header`/`required_section_stubs`/`gen_toc` usados igual em novo_artefato + migrador; `M.run(scope_root, paths, write)` e `CI.run(scope_root, subdir, create, write)` assinaturas estaveis entre Tasks 7/8/9/10. ✓
- **Decisoes do Rafael refletidas:** sub-ondas gated (cadencia), hibrido (calibracao Tasks 1-3 + classificador Task 6), promocao a block (4g), arquivo scratch (4f + decisao residual 3). ✓
