<!-- doc:meta
tipo: how-to
camada: L3
sot_de: plano de implementacao da Onda 3 do PAD-A (governanca dos 101 scripts de inventario/estoque)
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-02
-->

# PAD-A — Onda 3 (Governanca dos scripts inventario/estoque) Implementation Plan

> **Papel:** plano de execucao da Onda 3 do PAD-A — dar endereco/dono a cada script da zona, aposentar os mortos, e juntar estado/decisoes. **Abra quando:** for implementar a Onda 3 apos OK do Rafael (escopo = GOVERNANCA, escolhido 2026-06-02).
> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development ou superpowers:executing-plans. Steps usam checkbox (`- [ ]`).
> **Regras INVIOLAVEIS:** ver `docs/superpowers/specs/2026-06-01-arquitetura-de-artefatos-design.md` §8.5 (onda-a-onda c/ OK explicito, so a lista de arquivos do plano, sem refatorar fora de escopo, parametrizar>criar, completude antes de fechar, fato com fonte).

**Goal:** fazer o `script_audit.py` passar com 0 achados na zona (`scripts/inventario_2026_05/**` + `app/odoo/estoque/scripts/**`) via GOVERNANCA — indice navegavel + aposentar mortos + header de dono nos vivos + estado em 1 lugar + ADR-izar refutacoes — SEM re-arquitetar codigo vivo (a consolidacao real ja virou os atomos; o resto e demand-driven).

**Architecture:** 101 scripts (88 inventario + 13 atomos). Aposentar ~29 mortos movendo para `_deprecated/` (ja no `ignore_globs` do lint); indexar ~72 vivos em 2 `INDEX.md` dentro da zona (apontando para o `MAPA_SCRIPTS.md` rico, sem duplicar); adicionar header `# etapa:`/`# doc-dono:` nos vivos; consolidar estado disperso declarando `SOT.md` canonico e aposentando ~3 prompts redundantes; criar 2 ADRs arquiteturais. Cada mudanca tem fonte citada; ZERO mudanca de logica de negocio.

**Tech Stack:** `git mv` (preservar historico) + Markdown (INDEX/ADR) + edicao de header em `.py` (2 linhas comentario) + `scripts/audits/script_audit.py` como gate de verificacao. Sem novas dependencias.

## Indice
- [Premissas e anchor](#premissas)
- [Achados de seguranca (import scan)](#seguranca)
- [Fase 0 — Setup (FEITO)](#fase-0)
- [Fase 1 — Aposentar mortos](#fase-1)
- [Fase 2 — Indice navegavel na zona](#fase-2)
- [Fase 3 — Header de dono nos vivos](#fase-3)
- [Fase 4 — SC-ID residual](#fase-4)
- [Fase 5 — Estado em 1 lugar](#fase-5)
- [Fase 6 — ADR-izar refutacoes](#fase-6)
- [Fase 7 — Verde + review + regressao](#fase-7)
- [Decisoes para o Rafael](#decisoes)
- [Fora de escopo Onda 3](#fora-escopo)
- [Riscos](#riscos)

## Premissas e anchor <a id="premissas"></a>

- **origin/main = `be7283a9a`** (apos o merge da remessa FB->LF; worktree `feat-pad-a-onda-3` criada deste ponto).
- **Zona = 101 scripts** (re-ancorado em `be7283a9a`): `scripts/inventario_2026_05/` 88 `.py` + `app/odoo/estoque/scripts/` 13 `.py`. O merge da remessa so alterou CONTEUDO de 4 atomos (escrituracao/faturamento/picking/_invoice_helpers), nao a lista.
- **Detector (FONTE `python3 scripts/audits/script_audit.py --report-only`):** 101 SC-ORFAO + 101 SC-HEADER + 7 SC-ID. Todos orfaos porque o unico `MAPA_SCRIPTS.md` vive em `docs/inventario-2026-05/consolidacao/` (FORA da zona que o lint varre — `checks_script.collect_index_basenames` so le `INDEX.md`/`MAPA_SCRIPTS.md` sob os `operational_script_globs`).
- **Categorizacao (FONTE: workflow `wf_d0234780-fc7`, 9 agentes Explore que LERAM os arquivos):** DEAD 19 · SUPERSEDED 12 · VALIDATED_REF 16 · KEEP 21 · AUDIT 14 · MONITOR 6 = 88. Os agentes divergiram do `MAPA_SCRIPTS.md` em 22 casos (quase todos: MAPA otimista "AO-CAPINAR" vs realidade "DEAD/ja-executado"). A leitura dos agentes prevalece (o MAPA admite que sua coluna Situacao foi inferida, nao lida).
- **Baseline:** `pytest tests/audits/ -q` = **57 passed** (verificado em `be7283a9a`).
- **Mecanismo de aposentadoria:** `ignore_globs` do lint inclui `**/_deprecated/**`. Mover um script para um `_deprecated/` dentro da zona o tira do lint sem deletar (reversivel, preserva historico via `git mv`).

## Achados de seguranca (import scan) <a id="seguranca"></a>

`grep` de referencias entre scripts da zona (FONTE: scan 2026-06-02). Pares onde candidato-a-aposentar e referenciado por OUTRO script:

| Candidato (cat) | Referenciado por (cat) | Tratamento |
|---|---|---|
| `consolidar_lote_104000015_sal_fb` (DEAD) | `corrigir_fantasma_104000015_sal_fb` (DEAD) | movem JUNTOS para `_deprecated/` (import relativo preservado) |
| `13_transferencia_migracao_fb` (SUPERSEDED) | `15_transferencia_para_migracao` (SUPERSEDED) | movem JUNTOS |
| `17_transferir_preprod_lf_para_estoque` (SUPERSEDED) | `fat_lf_03_prestage` (SUPERSEDED) | movem JUNTOS |
| `transferir_indisp_para_estoque_p15_cd` (DEAD) | **`encontro_contas_lf` (KEEP)** | ⚠️ survivor depende → **NAO aposentar** (vira KEEP, indexa) ate verificar tipo de ref |
| `ajuste_inventario` (SUPERSEDED) | **`app/odoo/estoque/scripts/quant.py` (atomo)** | ⚠️ verificar se e import runtime ou so docstring; default **NAO aposentar** |
| `entrada_fb_piloto` (SUPERSEDED) | **`09_executar_onda1_bulk` (KEEP)** | ⚠️ survivor depende → **NAO aposentar** ate verificar |

**Regra:** nenhum script referenciado por um survivor e movido sem antes confirmar (Step de verificacao em Fase 1) que a referencia e inerte (docstring/comentario). Se for import runtime, o script PERMANECE (indexado como KEEP). Isso reduz os ~31 candidatos brutos para **~29 aposentaveis** (os 3 marcados ⚠️ default ficam).

## Fase 0 — Setup (FEITO) <a id="fase-0"></a>

- [x] Worktree `feat-pad-a-onda-3` criada off `be7283a9a`.
- [x] Baseline `pytest tests/audits/` = 57 passed.
- [x] Contagem re-ancorada: 101 scripts, 101 SC-ORFAO + 101 SC-HEADER + 7 SC-ID.

## Fase 1 — Aposentar mortos <a id="fase-1"></a>

**Files:**
- Create: `scripts/inventario_2026_05/_deprecated/` (+ `app/odoo/estoque/scripts/_deprecated/` se aplicavel — nao aplicavel: nenhum atomo e morto)
- Move (git mv): os scripts DEAD + SUPERSEDED-seguros (lista abaixo)

- [ ] **Step 1: Verificar os 3 casos ⚠️ (import runtime vs docstring)**

Run: `grep -nE "import|spec_from_file|importlib" scripts/inventario_2026_05/encontro_contas_lf.py | grep -i indisp; grep -nE "ajuste_inventario" app/odoo/estoque/scripts/quant.py; grep -nE "entrada_fb_piloto" scripts/inventario_2026_05/09_executar_onda1_bulk.py`
Expected: classificar cada um como `RUNTIME` (mantem o candidato como KEEP) ou `INERTE` (libera para mover). Registrar resultado. **Default conservador: se RUNTIME ou duvida → NAO mover (vira KEEP).**

- [ ] **Step 2: Criar `_deprecated/` e mover os DEAD inertes**

```bash
mkdir -p scripts/inventario_2026_05/_deprecated
# DEAD discovery F0 (5)
git mv scripts/inventario_2026_05/00_audit_odoo_realidade.py scripts/inventario_2026_05/00b_investigar_gotchas.py scripts/inventario_2026_05/00c_investigar_g003.py scripts/inventario_2026_05/00d_investigar_variacoes.py scripts/inventario_2026_05/00e_investigar_pickings.py scripts/inventario_2026_05/_deprecated/
# DEAD pontuais/debug (8)
git mv scripts/inventario_2026_05/ajuste_quant_cd.py scripts/inventario_2026_05/baixar_xml_preview_626032.py scripts/inventario_2026_05/debug_sefaz_608607.py scripts/inventario_2026_05/desfazer_ajustes_indevidos_lf.py scripts/inventario_2026_05/recuperar_aumentos_falhos.py scripts/inventario_2026_05/relotar_migracao_para_lotes_fb.py scripts/inventario_2026_05/transferir_fluxo_c.py scripts/inventario_2026_05/_deprecated/
# DEAD par 104000015 (movem juntos)
git mv scripts/inventario_2026_05/consolidar_lote_104000015_sal_fb.py scripts/inventario_2026_05/corrigir_fantasma_104000015_sal_fb.py scripts/inventario_2026_05/_deprecated/
# DEAD fat_lf diagnostico (4)
git mv scripts/inventario_2026_05/fat_lf_00_preflight.py scripts/inventario_2026_05/fat_lf_01_stock_audit.py scripts/inventario_2026_05/fat_lf_diag.py scripts/inventario_2026_05/fat_lf_inspect_invoice.py scripts/inventario_2026_05/_deprecated/
```

(NAO incluir `transferir_indisp_para_estoque_p15_cd` aqui se Step 1 deu RUNTIME para `encontro_contas_lf`.)

- [ ] **Step 3: Mover os SUPERSEDED inertes (movem juntos os pares)**

```bash
# par 13<-15 (movem juntos) + 15r
git mv scripts/inventario_2026_05/13_transferencia_migracao_fb.py scripts/inventario_2026_05/15_transferencia_para_migracao.py scripts/inventario_2026_05/15r_transferencia_reversa.py scripts/inventario_2026_05/_deprecated/
# par 17<-fat_lf_03 (movem juntos) + 15_preprod_fb
git mv scripts/inventario_2026_05/17_transferir_preprod_lf_para_estoque.py scripts/inventario_2026_05/fat_lf_03_prestage.py scripts/inventario_2026_05/15_transferir_preprod_para_estoque_fb.py scripts/inventario_2026_05/_deprecated/
# SUPERSEDED restantes inertes
git mv scripts/inventario_2026_05/corrigir_reserved_negativo_fb.py scripts/inventario_2026_05/fat_lf_02_carregar.py scripts/inventario_2026_05/fat_lf_04_executar.py scripts/inventario_2026_05/limpar_quants_ghost_210030005_fb.py scripts/inventario_2026_05/_deprecated/
```

(NAO incluir `ajuste_inventario` nem `entrada_fb_piloto` se Step 1 deu RUNTIME.)

- [ ] **Step 4: Criar `_deprecated/README.md` (manifesto do que foi aposentado e por que)**

Conteudo: 1 tabela `script | categoria | motivo (1 linha) | substituto`. doc:meta `tipo: reference`, `hub: scripts/inventario_2026_05/INDEX.md`. (Detalhe rico permanece no `MAPA_SCRIPTS.md`.)

- [ ] **Step 5: Verificar que nada quebrou + contagem caiu**

Run: `cd <worktree> && source .venv/bin/activate && python3 -c "import ast,glob,sys; [ast.parse(open(f).read()) for f in glob.glob('scripts/inventario_2026_05/**/*.py',recursive=True)]" && python3 scripts/audits/script_audit.py --report-only 2>/dev/null | grep -cE '^SC-ORFAO'`
Expected: AST parse de todos os survivors OK (sem SyntaxError por import quebrado nao pega, mas confirma arquivos validos); SC-ORFAO cai de 101 para ~72.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "chore(pad-a onda3): aposenta ~29 scripts mortos do inventario -> _deprecated/ (lint ignora) [skip render]"
```

## Fase 2 — Indice navegavel na zona <a id="fase-2"></a>

**Files:**
- Create: `scripts/inventario_2026_05/INDEX.md`
- Create: `app/odoo/estoque/scripts/INDEX.md`

- [ ] **Step 1: Criar `app/odoo/estoque/scripts/INDEX.md`**

doc:meta `tipo: index`, `camada: L1`, `hub: app/odoo/estoque/CLAUDE.md`. Lista os 13 atomos com 1 linha cada + link para `app/odoo/estoque/CLAUDE.md §6` (dono real). DEVE citar cada basename `.py` (o lint credita por basename).

- [ ] **Step 2: Criar `scripts/inventario_2026_05/INDEX.md`**

doc:meta `tipo: index`, `camada: L1`, `hub: docs/inventario-2026-05/INDEX.md`. Secoes: VIVOS (por sub-grupo: raiz/auditoria/monitor/_validados) citando cada survivor `.py`; ponteiro para `docs/inventario-2026-05/consolidacao/MAPA_SCRIPTS.md` (mineracao rica) e `_deprecated/README.md` (aposentados). NAO duplicar conteudo — so ponteiros + 1 linha por script.

- [ ] **Step 3: Verificar SC-ORFAO = 0**

Run: `python3 scripts/audits/script_audit.py --report-only 2>/dev/null | grep -cE '^SC-ORFAO'`
Expected: 0 (todo survivor citado em INDEX da zona).

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "docs(pad-a onda3): INDEX.md navegavel nas 2 zonas de script (resolve SC-ORFAO) [skip render]"
```

## Fase 3 — Header de dono nos vivos <a id="fase-3"></a>

**Files:** os ~72 survivors (13 atomos + ~59 inventario). Adicionar 2 linhas no topo (apos shebang/encoding se houver):
```python
# etapa: <C1|C2|READ|orquestrador|audit|monitor|validado|helper>
# doc-dono: <path>
```
`parse_script` exige as chaves `etapa` e `doc-dono` (regex `^#\s*([\w-]+)\s*:\s*(.*)$`).

- [ ] **Step 1: Atomos (13) — doc-dono = `app/odoo/estoque/CLAUDE.md §6`**

Para cada `app/odoo/estoque/scripts/*.py`: `# etapa: <C1/C2/...>` (ver tabela do workflow) + `# doc-dono: app/odoo/estoque/CLAUDE.md §6 Tabela 1 — <skill>`. Helpers (`_commit_helpers`,`_invoice_helpers`,`__init__`): `# etapa: helper` + `# doc-dono: app/odoo/estoque/CLAUDE.md §11`.

- [ ] **Step 2: Inventario survivors — doc-dono = `scripts/inventario_2026_05/INDEX.md`**

Para cada survivor em inventario (KEEP/AUDIT/MONITOR/VALIDATED_REF): `# etapa: <keep|audit|monitor|validado>` + `# doc-dono: scripts/inventario_2026_05/INDEX.md`. (O INDEX e o dono navegavel; a mineracao detalhada esta no MAPA_SCRIPTS via INDEX.)

- [ ] **Step 3: Verificar SC-HEADER = 0 + scripts ainda parseiam**

Run: `python3 scripts/audits/script_audit.py --report-only 2>/dev/null | grep -cE '^SC-HEADER'; python3 -c "import ast,glob; [ast.parse(open(f).read()) for f in glob.glob('scripts/inventario_2026_05/**/*.py',recursive=True)+glob.glob('app/odoo/estoque/scripts/*.py')]"`
Expected: SC-HEADER = 0; AST OK.

- [ ] **Step 4: Commit** `git commit -m "chore(pad-a onda3): header etapa/doc-dono nos ~72 scripts vivos (resolve SC-HEADER) [skip render]"`

## Fase 4 — SC-ID residual <a id="fase-4"></a>

Apos Fase 1, dos 7 SC-ID sobram 2 survivors: `substituir_lote_205030410_fb.py` (KEEP) e `teste_210030325_lf.py` (KEEP).

- [ ] **Step 1: Verificar imports dos 2** (`grep -rn "substituir_lote_205030410\|teste_210030325" scripts app`). Esperado: sem importadores.
- [ ] **Step 2: Renomear removendo o ID** via `git mv`: `substituir_lote_205030410_fb.py` → `substituir_lote_unico.py`; `teste_210030325_lf.py` → `teste_e2e_lf_exemplo.py`. Atualizar a citacao no `INDEX.md` (Fase 2). (Se Step 1 achar importador: ajustar o import junto.)
- [ ] **Step 3:** Run `python3 scripts/audits/script_audit.py --report-only 2>/dev/null | grep -cE '^SC-ID'` → Expected 0.
- [ ] **Step 4: Commit** `git commit -m "chore(pad-a onda3): remove ID de objeto do nome de 2 scripts vivos (resolve SC-ID) [skip render]"`

## Fase 5 — Estado em 1 lugar <a id="fase-5"></a>

Canonico (FONTE: workflow agente estado): `SOT.md` (macro) + `PENDENCIAS.md` + `INDEX.md` — estrutura JA existe e `INDEX.md` ja declara SOT.md como fonte. Trabalho = aposentar redundantes, **preservar HISTORICO intacto**.

- [ ] **Step 1:** Mover prompts/checkpoints REDUNDANTES para `docs/inventario-2026-05/99-historia/` (ja e a pasta de historia) via `git mv`: `QUICK_START_NEXT_SESSION.md` (red. por PROMPT_PROXIMA_SESSAO_LF), `99-historia/PROMPT_PROXIMA_SESSAO_2026_05_18B.md` ja esta la, `CHECKPOINT_2026_05_18_LF_FIM_SESSAO2.md` (raiz; red. por SESSAO3 em 99-historia). **NAO mover** os HISTORICO forenses (CHECKPOINT_CD_FINALIZADO, EXECUCAO_*, AUDIT_LOG, AJUSTES_EMERGENCIAIS).
- [ ] **Step 2:** Editar `docs/inventario-2026-05/INDEX.md` §Estado: remover ponteiro para o checkpoint movido; garantir que aponta SOT.md + PENDENCIAS.md + PROMPT_PROXIMA_SESSAO_LF como o trio vivo. Marcar `PICKINGS_PENDENTES_INVOICE.md` como "verificar status" (1 linha).
- [ ] **Step 3:** Rodar `python3 scripts/audits/doc_audit.py --report-only --skip-dup 2>/dev/null | grep -c "orfao"` antes/depois — nao pode AUMENTAR orfaos (mover dentro de pasta indexada). Verificar que C8 nao regrediu.
- [ ] **Step 4: Commit** `git commit -m "docs(pad-a onda3): consolida estado inventario (SOT canonico + aposenta 2-3 prompts redundantes) [skip render]"`

## Fase 6 — ADR-izar refutacoes <a id="fase-6"></a>

JA cobertas (so referenciar, NAO criar): D006 (renomeio refutado), D007 (INDISPONIBILIZAR refutado), D011 (Estoque Virtual id=28 refutado). FALTAM 2 ADRs arquiteturais (FONTE: workflow agente ADR):

- [ ] **Step 1: Criar `docs/inventario-2026-05/00-decisoes/D015-gold-script-aposentado-para-atomos.md`** — decisao de aposentar o vocabulario/abordagem "gold-script" em favor de atomos C1/C2 + subagente `gestor-estoque-odoo` + arvore de fluxos (demand-driven). FONTE: `app/odoo/estoque/CLAUDE.md`, MAPA_SCRIPTS §nota. Formato ADR (Contexto/Decisao/Consequencias). doc:meta `tipo: explanation`.
- [ ] **Step 2: Criar `docs/inventario-2026-05/00-decisoes/D016-evolucao-mecanismo-g1-g2-g3.md`** — decisao de depreciar G1 (NF-heavy via SEFAZ) em favor de G2 (pre-etapa interna) e G3 (inventory adjustment por planilha), por que cada geracao reduziu emissao de NF. FONTE: `MAPA_ASSUNTOS.md §1`. doc:meta `tipo: explanation`.
- [ ] **Step 3:** Registrar D015+D016 no indice de decisoes (se houver `00-decisoes/INDEX.md` ou no `docs/inventario-2026-05/INDEX.md`). Run `doc_audit --report-only` para garantir que os 2 ADRs novos passam (header/Contexto).
- [ ] **Step 4: Commit** `git commit -m "docs(pad-a onda3): ADR D015 (gold-script->atomos) + D016 (G1->G2->G3) [skip render]"`

## Fase 7 — Verde + review + regressao <a id="fase-7"></a>

- [ ] **Step 1: Adicionar teste de regressao** `tests/audits/test_zona_inventario_governada.py`:

```python
import subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]

def _audit_zone():
    out = subprocess.run([sys.executable, "scripts/audits/script_audit.py", "--report-only"],
                         cwd=ROOT, capture_output=True, text=True).stdout
    return [l for l in out.splitlines() if l.startswith("SC-")]

def test_zona_inventario_sem_orfao_header_id():
    findings = _audit_zone()
    assert findings == [], f"zona deve estar governada (0 achados), achou {len(findings)}: {findings[:10]}"
```

- [ ] **Step 2: Rodar e ver passar** Run `pytest tests/audits/test_zona_inventario_governada.py -v` → Expected PASS. E `pytest tests/audits/ -q` → Expected 58 passed (57 + 1 novo).
- [ ] **Step 3: script_audit final** Run `python3 scripts/audits/script_audit.py --report-only 2>/dev/null | grep -cE '^SC-'` → Expected 0.
- [ ] **Step 4: Review** — requesting-code-review (2 reviewers: conformidade PAD-A + nao-quebrou-nada). Verificar que nenhum survivor perdeu import.
- [ ] **Step 5: Commit** `git commit -m "test(pad-a onda3): regressao zona inventario governada (script_audit=0) [skip render]"`

## Decisoes para o Rafael <a id="decisoes"></a>

1. **Nome da pasta de aposentadoria:** `_deprecated/` (ja no ignore do lint, zero config). Alternativa `_historico/` exigiria 1 linha no config. **Default: `_deprecated/`.**
2. **Os 3 casos ⚠️ (import scan):** default conservador = NAO aposentar (ficam KEEP indexados). So aposentar se Step-1 da Fase 1 provar que a referencia e inerte.
3. **doc-dono dos inventario survivors:** aponta para `scripts/inventario_2026_05/INDEX.md` (hub navegavel) em vez de espalhar por fluxos. Simples e consistente.
4. **Pendencias herdadas da Onda 2** (decidir em paralelo, fora deste plano): MEMORY.md 155→≤150; worker_atacadao.py DEV sem 7 filas PROD.

## Fora de escopo Onda 3 <a id="fora-escopo"></a>

- **NAO** re-arquitetar/parametrizar codigo vivo (escopo Governanca escolhido; consolidacao real e demand-driven via atomos).
- **NAO** atacar headers de DOC (C1=645 — Onda 4+).
- **NAO** mexer nos `.sh` (`fat_lf_resume*.sh`) — fora do lint (`*.py` only); superados por `--modo resume` v18 mas nao bloqueiam.
- **NAO** atualizar numeros operacionais do SOT.md (exige dado Odoo ao vivo — fora de governanca).
- **NAO** deletar nada — so `git mv` para `_deprecated/`/`99-historia/` (reversivel).

## Riscos <a id="riscos"></a>

- **Import quebrado ao mover:** mitigado pelo import scan (3 casos ⚠️ travados) + Step de AST parse pos-move + os pares movem juntos.
- **Falso-verde do lint:** `collect_index_basenames` credita por basename — dois scripts com mesmo basename em subdirs poderiam mascarar. Mitigado: nomes unicos na zona (verificado).
- **Gate de criacao bloquear INDEX/ADR novos:** mitigado espelhando header conformante (doc:meta + Papel + Indice quando aplicavel).
- **C8 (doc_audit) regredir ao mover docs de estado:** Step 3 da Fase 5 compara orfaos antes/depois.
