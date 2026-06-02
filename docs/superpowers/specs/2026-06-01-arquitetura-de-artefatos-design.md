<!-- doc:meta
tipo: explanation
camada: L3
sot_de: desenho do Padrao de Arquitetura de Artefatos (PAD-A)
hub: docs/superpowers/specs/INDEX.md
superseded_by: —
atualizado: 2026-06-01
-->

# Spec / Design — Padrao de Arquitetura de Artefatos (PAD-A)

> **Papel deste doc:** desenho aprovado (spec) do padrao determinístico de documentacao **e** scripts do frete_sistema. Define regras, enforcement e migracao. **Nao** e a implementacao — e o blueprint que vira plano (writing-plans → ondas).
> **Abra quando:** for revisar/ajustar o padrao antes da implementacao, ou precisar do "porque" de uma regra.
> **Dono vigente apos implementacao:** `.claude/references/ARQUITETURA_DE_ARTEFATOS.md` (a ser criado na Onda 0). Esta spec passa a `explanation` historica e aponta para o dono.

---

## Contexto

Este desenho nasceu do diagnostico de desorganizacao documental cronica do frete_sistema (~1157 .md, 163 scripts, com orfaos, duplicacao e SOT bicefala — workflows wf_ba978431 e wf_f1b6c258). Define um padrao determinístico em que a forma do artefato e validada no momento da criacao e do commit (nao por memoria do agente), cobrindo docs **e** scripts. O detalhamento do problema com evidencia esta na secao 0.

## Indice
- [Contexto](#contexto)
- [0. Problema (com evidencia)](#0-problema)
- [1. Objetivo e principios](#1-objetivo)
- [2. Modelo: artefato, tipo, camada](#2-modelo)
- [3. Regras (A–E)](#3-regras)
- [4. Enforcement: 3 aneis](#4-enforcement)
- [5. Checklist de criacao + schema por tipo](#5-checklist)
- [6. Conteudo: 3 faixas](#6-conteudo)
- [7. Artefatos a construir](#7-artefatos)
- [8. Migracao (5 ondas)](#8-migracao)
- [8.5 Regras de execucao (ANTI-DESVIO) + worktree](#8-5-anti-desvio)
- [9. Riscos e calibracao](#9-riscos)
- [10. Nao-objetivos](#10-nao-objetivos)
- [11. Fontes](#11-fontes)

---

## 0. Problema <a id="0-problema"></a>

Diagnostico de 2026-06-01 (2 workflows, 9 subagentes, leitura terceirizada — citacoes em §11):

- **~1.157 arquivos `.md`** no projeto. Clusters orfaos sem ponto de entrada navegavel a partir do CLAUDE.md: **62 `.md` soltos na raiz**, **`docs/` inteiro (223 `.md`) com 0 links diretos do CLAUDE.md**, 9 em `.claude/` raiz, 30 em `scripts/`, 24 em `_deprecated/`.
- **163 scripts `.py`** no ecossistema inventario/estoque. **59 orfaos (35%)** sem citacao em nenhum `.md` vivo; **9 clusters de duplicacao** cobrindo 37 scripts (`14_..._v2`, `fat_lf_05_executar_clean`, dois `15_`, `00b/c/d/e`); **8 scripts com ID de objeto hardcoded no nome**.
- **Os 4 problemas do usuario** confirmados com evidencia:
  - **P1 duplica/quadriplica** — divergencias reais: "3 arquivos pra fila RQ" dito de 3 formas em 3 memorias; `company_id`(CD=4) vs `partner_id`(CD=34); tabela CAMINHOS espelhada manualmente em 2 CLAUDE.md.
  - **P2 achados desconectados** — `industrializacao-fb-lf`: SOT bicefala, `ACHADOS` virou log append-only datado, refutacoes preservadas lado-a-lado com a correcao.
  - **P3 nao acha SOT, re-pesquisa** — `docs/` inalcancavel pelo indice; "constituicao" do orquestrador-Odoo aponta para **2 lugares**.
  - **P4 nao segue linha entre sessoes** — estado replicado em 4 docs; "gold-script" superseded ainda vivo; `MEMORY.md` viola a propria regra (157 > limite 150).
- **Descoberta-chave (arqueologia das correcoes):** **todo mecanismo "mole" ja foi furado.** SOT + indice + constituicao §6 + spec escrita pelo proprio agente + lint de UI + memoria duravel "docs centralizados" — todos existiam, e a falha ocorreu **na sessao seguinte mesmo assim**. 17 modos de falha catalogados; o erro real do `j1001` veio de **decisao duplicada README↔SOT** que divergiu.

**Conclusao operacional:** o que nao e determinístico **no momento da decisao** nao segura. O padrao precisa ser aplicado por maquina (gate/lint/hook), nao por memoria do agente.

---

## 1. Objetivo e principios <a id="1-objetivo"></a>

**Objetivo:** o menor conjunto de tokens de alto sinal que maximiza a chance de acao correta, com a **forma de criacao** determinística e o **conteudo** padronizado ate o teto do que e mecanizavel.

**Principios (convergencia de Anthropic context-engineering + Agent Skills + Diataxis + ADR + SSOT/MOC — §11):**
1. **SSOT por ponteiro** — 1 fato = 1 arquivo dono; os demais apontam por caminho, nunca copiam.
2. **Context rot e real** — doc inchado sempre-carregado degrada o recall; progressive disclosure e performance, nao estetica.
3. **Just-in-time** — caminho de arquivo e o "lightweight identifier"; carrega sob demanda.
4. **Determinismo > confianca na memoria** — cada regra mecanizavel vira gate/lint; o resto e advisory + review, declarado como tal.
5. **Custo de token e bem publico** — cada bloco precisa justificar seu custo ("removing this would cause a mistake?").

---

## 2. Modelo: artefato, tipo, camada <a id="2-modelo"></a>

**Artefato** = documento (`.md`) **ou** script (`.py`) sob zona gerenciada. Ambos governados (a doenca e a mesma).

**Zonas gerenciadas:** `docs/`, `.claude/references/`, `.claude/skills/`, `app/*/CLAUDE.md`, zonas operacionais de `scripts/`. **Fora:** `/tmp`, fixtures de teste, rascunhos (`tipo: scratch` ou path). O gate so dispara em zona gerenciada.

**Tipos** (Diataxis adaptado para agente + harness):

| Tipo | Dono de | Camada típica |
|---|---|---|
| `reference` | fatos, campos, IDs, regras (estavel) | L2 |
| `how-to` / `runbook` | procedimento acionavel | L2 |
| `explanation` | o porque (sem passos) | L3 |
| `adr` | uma decisao datada (imutavel) | L3 |
| `state` | estado vivo/mutavel (progresso, inventario, checkpoint) | L3 |
| `index` / `hub` | so ponteiros (MOC) | L1 |
| `scratch` | efemero, fora de enforcement | — |

**Camadas:**
- **L1** sempre carregado: CLAUDE.md + hubs/INDEX. MINIMO.
- **L2** por tarefa: doc canonico do tema.
- **L3** sob demanda: porque/historico/estado/ADR. Custo zero ate ser lido.

**Header `doc:meta`** (machine-checkable; em `.md` via comentario HTML, em skills/memoria via YAML ja existente):
```
<!-- doc:meta
tipo: <enum>
camada: L1|L2|L3
sot_de: <tema dono>  (ou "—")
hub: <caminho do indice que lista este artefato>
superseded_by: <caminho do ADR/doc que o substitui>  (ou "—")
atualizado: YYYY-MM-DD
-->
```
Scripts usam header equivalente em docstring: `# tipo:`, `# etapa:`, `# doc-dono:`, `# hub:`.

---

## 3. Regras (A–E) <a id="3-regras"></a>

### A. Fundamentos
- **A1** Artefato = docs **+** scripts; ambos governados.
- **A2** `tipo` + `camada` declarados no header.
- **A3** SSOT: 1 fato = 1 dono; demais apontam por caminho, **nunca copiam**.
- **A4** Progressive disclosure 3 camadas. Vai pra **L1** so se (≥3 modulos/contextos **E** muda raramente **E** ausencia causa erro). `>100 linhas` → TOC obrigatorio. Corpo de hub/skill `<500 linhas` → fatiar por dominio.
- **A5** Links **1 nivel de profundidade** a partir do hub (sem cadeia hub→A→B→C).

### B. Anti-vazamento de conteudo
- **B1** **Schema de conteudo por tipo** (seccoes obrigatorias fechadas — §5).
- **B2** **Protocolo anti-achado-solto:** todo achado aterrissa em (a) dono canonico reescrito, (b) ADR datado, ou (c) `state` — **+** linkado de 1 hub.
- **B3** Mudanca = **ADR append-only** + `Superseded by`; nunca reescrever historico no corpo de `reference`.
- **B4** Estado mutavel isolado em **1** `ESTADO.md`/`state.json` por projeto; demais apontam.
- **B5** Sem markers proibidos em `reference`: `✔v\d`, `~~tachado~~`, `ACHADO 20\d\d-`, `TABELA REFUTADA`, `🔴`.
- **B6** `superseded_by` no header + **banner obrigatorio** em doc movido (metodologia/estado vigente sempre descobrivel — mata "gold-script ainda vivo").

### C. Scripts
- **C1** Indice **script→etapa→doc-dono** por zona operacional (`scripts/<op>/INDEX.md` ou `MAPA_SCRIPTS.md`).
- **C2** **Anti-recriacao / parametrizar > criar:** antes de criar `.py`/`.md` em zona operacional, buscar similares; alta similaridade → parametrizar o existente. (O gate **roda a busca** — §4.)
- **C3** Sem ID de objeto hardcoded no nome (`\d{5,}`); operacao especifica = caso de uso de script parametrizado.

### D. Conteudo (qualidade)
- **D1** **Terminologia unica** por conceito (glossario de sinonimos-banidos).
- **D2** **Citacao obrigatoria** em `reference`/investigacao (`FONTE:` ou seccao `## Fontes`) — operacionaliza a regra precision-engineer "toda afirmacao requer prova".
- **D3** **Acuracia de campos:** doc cita `Tabela.campo` → cruzar com `.claude/skills/consultando-sql/schemas/tables/*.json`; campo inexistente = falha.
- **D4** Frases banidas/placeholder/hedge: `TBD`/`TODO` em doc estavel; time-sensitive ("atualmente", "por enquanto"); hedge ("dezenas", "varios", "alguns") em `reference`.
- **D5** **Near-duplicate** textual (`difflib`/n-grama) **+ semantico** (Voyage/pgvector — pega duplicacao de significado, ex.: a mesma regra dita de 3 formas).
- **D6** **Eval LLM-judge** (advisory) de clareza/sinal/"cada paragrafo justifica seu custo" — so em L2 de alto trafego (references/skills), sob demanda + baseline na Onda 0.

### E. Enforcement (regras de processo — detalhadas em §4)
- **E1** Anel 1 — **Creation gate** (PreToolUse block) + scaffold + checklist de 9 itens.
- **E2** Anel 2 — **commit lint** (`doc_audit.py` + `script_audit.py`) encadeado, modos `--report-only`/`--enforce-touched`/`--enforce-new`.
- **E3** Anel 3 — **Stop hook** de completude (advisory).
- **E4** PreToolUse advisory ao editar **codigo** (`app/<mod>/**`): injeta SOT do modulo.
- **E5** **Salvaguarda de autorizacao:** o gate valida a **forma** de uma criacao ja decidida; **nunca forca criar**. "Aterrissar achado" = registrar pendencia leve (livre); reescrever dono / criar ADR / editar canonico = exige **verbo de acao explicito** do usuario. Hooks e skill sao **advisory**, nunca gate que obrigue criar arquivo.

---

## 4. Enforcement: 3 aneis <a id="4-enforcement"></a>

Do mais forte (nascimento) ao mais leve (fim de sessao):

### Anel 1 — Creation gate (determinístico, bloqueante)
**Hook `PreToolUse` em `Write`/`Edit`** de artefato em zona gerenciada. Roda os **itens 1–8** do checklist (§5) sobre o **conteudo proposto** e **nega a escrita** se item mecanico falhar, devolvendo a lista do que corrigir. Determinístico: o harness barra.
- **Momento:** **PRE-ESCRITA** — roda *antes* do arquivo existir no disco. Nao e "pos-registro": o arquivo torto nunca chega a ser criado.
- **Cobertura:** so dispara nas escritas via ferramentas do Claude Code (escritas DO AGENTE). Edicao manual no editor do usuario **nao** passa por aqui — e pega no Anel 2.
- **Escopo do gate:** itens **1–8** (intrinsecos ao arquivo). O **item 9 (registro no hub) NAO roda aqui** — ver §5 "Por que o item 9 e pre-commit".
- **Scaffold** `scripts/docs/novo_artefato.py` emite o esqueleto ja com header + seccoes obrigatorias do tipo → caminho mais facil ja nasce conforme.

### Anel 2 — Commit lint (determinístico, bloqueante no commit)
- **Momento:** **NO COMMIT** (`git commit`). **Cobertura:** TUDO que entra no commit, qualquer origem (agente, edicao manual, script).
- `scripts/audits/doc_audit.py` — header, link-rot, orfao + **item 9 (cross-ref bidirecional hub↔artefato)**, SOT unica, tamanho/TOC, markers proibidos, schema-por-tipo, glossario, citacao, acuracia-vs-schema, frases banidas, near-duplicate textual+semantico.
- `scripts/audits/script_audit.py` — `.py` orfao (nao indexado), ID hardcoded, near-duplicate de scripts, falta de header.
- **Pre-commit encadeado:** wrapper `scripts/hooks/pre-commit` que chama, em sequencia, `pre-commit-ui-lint.sh` (existente) + `doc-lint` + `script-lint`. **Nao sobrescrever** o hook atual.
- Modos: `--report-only` (auditoria full do legado), `--enforce-touched` (arquivos do diff/sessao — capina legado por onda), `--enforce-new` (so artefatos novos).

> **Resumo dos momentos (sua pergunta 2026-06-01):** itens **1–8 = PRE-ESCRITA** (gate, so escritas do agente); item **9 = PRE-COMMIT** (lint, qualquer origem); pendencias de sessao = **STOP** (advisory). Os tres momentos sao complementares em TEMPO e em COBERTURA — confiar num so sempre furou (arqueologia).

### Anel 3 — Stop hook (advisory)
**Hook `Stop`/`SessionEnd`** roda audit sobre arquivos tocados na sessao (`git diff` + editados) e **LISTA** achados/markers/orfaos/pendencias nao aterrizados. **Avisa, nao bloqueia** (operacao viva frequentemente nao commita).

### Transversal — PreToolUse advisory em codigo (E4)
Ao editar `app/<mod>/**` nao-`.md`: injeta `additionalContext` com a SOT do modulo (`app/<mod>/CLAUDE.md`) → forca **considerar** a doc ao mexer no codigo, sem bloquear.

---

## 5. Checklist de criacao + schema por tipo <a id="5-checklist"></a>

**Checklist (cada item = verificacao mecanica do gate; auto-atestado e proibido):**

| # | Criterio | Verificacao | **Quando** | Falha |
|---|---|---|---|---|
| 1 | Header `doc:meta` completo, enums validos, `atualizado` data | parse | **pre-escrita** | bloqueia |
| 2 | `sot_de:` declarado (tema ou `—`) | campo presente | **pre-escrita** | bloqueia |
| 3 | `hub:` aponta para indice **existente** | resolve path | **pre-escrita** | bloqueia |
| 4 | Nao recria dono existente | gate **roda busca** textual+semantica; ratio alto → `--override`+justificativa | **pre-escrita** | bloqueia c/ override |
| 5 | Seccoes obrigatorias do `tipo` presentes (schema abaixo) | headings | **pre-escrita** | bloqueia |
| 6 | TOC se >100 linhas; sem markers proibidos em `reference` | conta linhas + regex | **pre-escrita** | bloqueia |
| 7 | Links relativos resolvem | resolve path | **pre-escrita** | bloqueia |
| 8 | (scripts) sem ID hardcoded; header `# etapa:`/`# doc-dono:` | regex | **pre-escrita** | bloqueia |
| 9 | Artefato listado no `hub` declarado (cross-ref bidirecional) | hub aponta de volta p/ o artefato | **pre-commit** | bloqueia commit |

**Schema de conteudo por tipo (seccoes obrigatorias fechadas):**

| Tipo | Seccoes obrigatorias | Impede |
|---|---|---|
| `reference` | Papel · (fatos/tabela) · **Fontes** | nao ha onde "colar achado datado" |
| `runbook`/`how-to` | Papel · Pre-condicoes · Passos · **Rollback** · **Verificacao** | procedimento sem rollback/verificacao |
| `adr` | **Status** · Contexto · Decisao · Consequencias · *(Superseded by)* | decisao reescrevendo reference |
| `explanation` | Papel · Contexto · *(sem passos acionaveis)* | "porque" vazando pra reference |
| `state` | Atualizado · Estado atual · Pendencias | estado replicado em N docs |
| `index`/`hub` | **so ponteiros** (paragrafo de conteudo > 3 linhas que nao seja ponteiro = falha) | hub virar catalogo |

### 5.1 Por que o item 9 e pre-commit (nao creation gate)

E **cross-file**. Ao criar um doc novo declarando `hub: X.md`, o indice `X.md` ainda **nao** referencia esse arquivo (ele acabou de nascer). O creation gate ve **uma escrita por vez** e nao sabe se a proxima acao vai registrar no hub — checar registro no nascimento seria circular/sempre-falha. O cross-ref artefato↔hub so e consistente quando **ambos** os arquivos existem, e o momento determinístico pra isso e o **pre-commit**. (O item 3 — `hub:` aponta para indice existente — esse SIM e pre-escrita, porque so checa que o indice-alvo existe, nao que ele ja aponta de volta.)

### 5.2 Definicoes e limiares FIXADOS (anti-ambiguidade)

Valores iniciais calibraveis; ficam num arquivo de config do lint (`scripts/audits/artefato_lint.config.json`) decidido na Onda 0. **Sem valor implícito "a criterio do agente".**

| Parametro | Valor inicial fixado |
|---|---|
| **Zona gerenciada (docs)** | allowlist explicita: `docs/`, `.claude/references/`, `.claude/skills/`, `app/*/CLAUDE.md` |
| **Zona operacional (scripts)** | allowlist explicita em config (ex.: `scripts/inventario_2026_05/`, `app/odoo/estoque/scripts/`); diretorio so vira "operacional" se constar na allowlist |
| **Escape hatch** | `tipo: scratch` no header OU path em ignore-list (`/tmp`, `**/tests/fixtures/**`) |
| **TOC obrigatorio** | arquivo > 100 linhas |
| **Corpo de hub/skill** | alerta > 500 linhas (fatiar) |
| **Hub "so ponteiros"** | paragrafo nao-ponteiro > 3 linhas = falha |
| **Near-duplicate textual** | `difflib ratio` ≥ 0.85 → bloqueia c/ `--override`; 0.75–0.85 → report |
| **Near-duplicate semantico** | cosseno ≥ 0.92 → bloqueia c/ `--override`; 0.85–0.92 → report |
| **Match de seccao obrigatoria** | heading comparado case-insensitive + accent-insensitive |
| **ID hardcoded em nome de script** | regex `\d{5,}` no basename |
| **Hedge banido em `reference`** | lista fechada: "dezenas", "varios", "alguns", "muitos", "aproximadamente" (sem numero adjacente) |
| **Time-sensitive banido** | lista fechada: "atualmente", "por enquanto", "recentemente", "hoje em dia", datas relativas |

---

## 6. Conteudo: 3 faixas <a id="6-conteudo"></a>

| Faixa | Mecanismo | Bloqueia? | Onde aplica |
|---|---|---|---|
| **Determinística** (D1–D4, B1, B5) | lint/gate/scaffold (regex/parse/cross-ref) | sim | todos artefatos gerenciados |
| **Semantica** (D5) | embeddings Voyage/pgvector | bloqueia em cosseno muito alto; senao report | docs do mesmo hub; modo periodico |
| **Probabilística** (D6) | LLM-as-judge (infra `.claude/evals`) | nao (advisory) | L2 alto trafego; sob demanda + baseline Onda 0 |
| **Convencao** (insight, exemplo, modelo mental) | skill + review | nao | guia, nao enforca |

**Honestidade (teto de determinismo):** estrutura = 100% mecanica. Conteudo decai: schema/glossario/citacao/acuracia = determinístico; significado-duplicado = semantico (probabilístico calibrado); qualidade-de-redacao = LLM-judge (advisory); qualidade-de-insight = so review. O residuo irredutivel ("este e mesmo o SOT certo?" — granularidade de tema) e mitigado pelo gate mostrando near-duplicates, mas a decisao final e humana/agente.

---

## 7. Artefatos a construir <a id="7-artefatos"></a>

| Artefato | Papel | Tipo |
|---|---|---|
| `.claude/references/ARQUITETURA_DE_ARTEFATOS.md` | **SOT do padrao** (dono vigente; esta spec aponta pra ele) | reference |
| `.claude/skills/padronizando-docs/SKILL.md` | how-to: arvore de decisao (dono/ADR/state) + template + checklist | how-to |
| `scripts/audits/doc_audit.py` | lint de docs (Anel 2) | script |
| `scripts/audits/script_audit.py` | lint de scripts (Anel 2) | script |
| `scripts/docs/novo_artefato.py` | scaffold (Anel 1) | script |
| `scripts/hooks/pre-commit` (wrapper) + `pre-commit-doc-lint.sh` + `pre-commit-script-lint.sh` | encadeamento com ui-lint | script |
| `.claude/hooks/creation_gate.py` | PreToolUse block (Anel 1) | script |
| `.claude/hooks/stop_completude.py` | Stop hook (Anel 3) | script |
| `.claude/hooks/pretool_sot_modulo.py` | PreToolUse advisory em codigo (E4) | script |
| `.claude/references/GLOSSARIO.md` | terminologia unica (D1) | reference |
| `.claude/evals/docs/` | eval LLM-judge (D6) | — |
| integracao Voyage/pgvector | near-duplicate semantico (D5) | script |
| Atualizacao `CLAUDE.md` (projeto + global) | link L1 para o padrao; remover espelho divergente CAMINHOS | reference |

**Settings:** os 3 hooks vao em `settings.json`/`settings.local.json` (skill `update-config` ou edicao direta — confirmar com usuario antes).

---

## 8. Migracao (5 ondas) <a id="8-migracao"></a>

Cada onda = 1 checkpoint, gated por audit-verde no escopo.

- **Onda 0 — Fundacao:** os 2 lints + 3 hooks + pre-commit encadeado + scaffold + skill + `ARQUITETURA_DE_ARTEFATOS.md` + GLOSSARIO + baseline LLM-judge + setup semantico + link no CLAUDE.md. Roda `--report-only` → **inventario de divida** (docs **e** scripts).
- **Onda 1 — Indice mestre:** hubs faltantes (`docs/INDEX.md`, raiz, `.claude/` raiz, `scripts/`) e **ligar `docs/` ao CLAUDE.md**. Resolve P3.
- **Onda 2 — Conflitos diagnosticados:** 6 conflitos de memoria + divergencias worker-RQ/company_id + aposentar "gold-script" + unificar constituicao orquestrador-Odoo + consertar `MEMORY.md`.
- **Onda 3 — Piloto inventario/estoque:** consolidar 163 scripts (indice + aposentar 59 orfaos + parametrizar 9 clusters duplicados) + SOT unica + estado em 1 lugar + ADR-izar refutacoes. **Prova o padrao no pior caso.**
- **Onda 4+ — Varredura por cluster** guiada pelo relatorio (raiz → docs/ → references/ → skills → app/*), cada cluster → orfao-zero + link-rot-zero.

---

## 8.5 Regras de execucao (ANTI-DESVIO) + worktree <a id="8-5-anti-desvio"></a>

> O usuario sinalizou (2026-06-01) que o agente **tem costume de desviar do plano** — confirmado pela arqueologia (FM: "metodologia mudou no meio", "violou padrao documentado", "refatorou o que nao devia", "implementou sem autorizacao", "checkpoint marcado sem entregar"). Estas regras sao o **trilho explicito** da implementacao. Sao INVIOLAVEIS; valem para esta iniciativa inteira.

1. **Worktree isolado.** ✅ CRIADO 2026-06-01: `/home/rafaelnascimento/projetos/frete_sistema_pad_a` (branch `feat/pad-a-artefatos`, base `origin/main` c4f3e8ccc). Esta spec ja foi movida para ca. Nada em `main` sem OK explicito; merge só com OK.
2. **Onda a onda.** NAO iniciar a Onda N+1 sem: (a) audit verde no escopo da Onda N, **e** (b) OK explicito do usuario. Cada onda comeca com mini-plano + confirmacao.
3. **So a lista §7.** NAO criar artefato que nao esteja na lista §7 / na onda vigente. Artefato novo nao-previsto exige confirmacao ANTES de criar.
4. **Sem refatorar fora de escopo.** NAO reorganizar/renomear/mover nada alem do que a onda define. Melhoria avulsa observada → anotar como pendencia, NAO executar.
5. **Confirmar diagnostico ≠ autorizar implementacao.** "1-sim, 2-sim" sobre um diagnostico NAO autoriza escrita. Escrita so apos verbo de acao explicito ("implemente", "crie", "execute"). (E5; [[confirmar-diagnostico-nao-e-autorizar-implementacao]])
6. **Parametrizar > criar.** Antes de qualquer script novo: rodar a busca (C2). Se houver similar, parametrizar o existente; criar novo so com justificativa registrada.
7. **Completude antes de fechar onda.** Onda so e "feita" quando o artefato existe E o audit do escopo passa. Proibido marcar checkpoint sem entregar (FM13). Reportar com numeros exatos + FONTE, sem "varios/dezenas".
8. **SOT primeiro, fato com fonte.** Antes de escrever um fato, achar o dono existente (gate/busca). Reportar fato verificado com citacao; inferencia, se houver, em secao separada — nao deduzir no lugar de reportar.
9. **Commits descritivos por onda** no branch do worktree; merge para `main` so com OK do usuario (preferencia: nao commitar/pushar sem pedido).
10. **Re-verificar diagnostico herdado.** Conclusao de sessao anterior (inclusive desta spec) e re-checada contra a fonte viva antes de virar acao — nao tomar como verdade cega.

**Auto-aplicacao (meta):** esta iniciativa segue o proprio padrao desde a Onda 0 (dogfooding). Se o PAD-A nao consegue se governar, nao governa o resto.

---

## 9. Riscos e calibracao <a id="9-riscos"></a>

- **Falso-positivo near-duplicate (D5):** comeca com bloqueio + `--override` justificado; limiar aperta com maturidade.
- **Latencia do creation gate:** validacao leve (parse/regex/grep); near-duplicate semantico so consulta indice pre-computado, nao recomputa embeddings a cada Write.
- **Pre-commit chaining:** wrapper unico; testar que ui-lint continua disparando.
- **Escape hatch:** `tipo: scratch` e paths fora de zona gerenciada nunca disparam o gate (evita fricção em arquivo bobo).
- **Salvaguarda de autorizacao (E5):** gate valida forma, nunca forca criar; respeitada a preferencia "confirmar diagnostico ≠ autorizar implementacao".
- **Legado congelado:** `--enforce-touched` + deadline por onda evita que a regra vire teatro so para novos.
- **Custo LLM-judge/Voyage:** advisory/periodico, fora do caminho quente; so paga onde agrega (L2 alto trafego / dup de significado).

---

## 10. Nao-objetivos <a id="10-nao-objetivos"></a>

Fora do escopo deste padrao (sao disciplina de output/CLAUDE.md, nao estrutura de artefato): escrever sem autorizacao, deduzir em vez de reportar, propagar diagnostico stale, erro aritmetico, ler semantica de planilha errada. O padrao e desenhado para **nao piorar** o de autorizacao (E5); os demais ficam para uma frente separada se desejado.

---

## 11. Fontes <a id="11-fontes"></a>

- Diagnostico topologia/duplicacao/conflitos/exemplo/best-practices: workflow `wf_ba978431-a59` (2026-06-01).
- Estresse inventario/scripts/arqueologia/stress-test: workflow `wf_f1b6c258-6c5` (2026-06-01); findings em `/tmp/doc-standard-research/`.
- Memorias-base (concordancia): `feedback_docs_centralizados_indice.md`, `feedback_mapear_profundo_antes_consolidar.md`, `feedback_parametrizar_scripts_existentes.md`, `feedback_constituicao_skill_so_responsabilidade.md`, `feedback_incompletude_quebra_regras.md`, `confirmar-diagnostico-nao-e-autorizar-implementacao.md`, `regra_direcao_migracao_diff_qtd.md`.
- Precedente de enforcement no repo: `scripts/audits/ui_policy_lint.py` (`--enforce-new`) + `scripts/hooks/pre-commit-ui-lint.sh`.
- Externas: Anthropic "effective context engineering for AI agents"; Anthropic Agent Skills best-practices (platform.claude.com); code.claude.com CLAUDE.md best-practices; Diataxis (diataxis.fr); ADR (martinfowler.com/bliki/ArchitectureDecisionRecord.html); SSOT (en.wikipedia.org/wiki/Single_source_of_truth); Progressive Disclosure (nngroup.com); MOC (dsebastien.net).

---

## Status

> **Auto-achado (dogfooding):** esta spec declara `hub: docs/superpowers/specs/INDEX.md`, que **ainda nao existe** — o proprio lint reprovaria por link-rot/orfao. E intencional: prova o problema. Criar `docs/superpowers/specs/INDEX.md` e registrar esta spec nele e entregavel da **Onda 1**; ate la a spec e um "primeiro candidato de migracao".

**DESENHO APROVADO INCREMENTALMENTE** (sessao 2026-06-01) nas 4 decisoes do usuario: enforcement maximo (hook+lint+skill), migracao completa do legado, todos os clusters, conteudo no escopo maximo (determinístico + semantico + LLM-judge). **Aguardando revisao final desta spec** antes de `writing-plans`.
