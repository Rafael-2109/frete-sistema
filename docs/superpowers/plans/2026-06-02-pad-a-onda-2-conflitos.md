<!-- doc:meta
tipo: how-to
camada: L3
sot_de: plano de implementacao da Onda 2 do PAD-A (conflitos diagnosticados)
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-02
-->

# PAD-A — Onda 2 (Conflitos diagnosticados) Implementation Plan

> **Papel:** plano de execucao da Onda 2 do PAD-A (reconciliar conflitos de doc/memoria). **Abra quando:** for implementar a reconciliacao apos OK do Rafael.
> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development ou superpowers:executing-plans. Steps usam checkbox (`- [ ]`).
> **Regras INVIOLAVEIS:** ver `docs/superpowers/specs/2026-06-01-arquitetura-de-artefatos-design.md` §8.5 (onda-a-onda c/ OK explicito, so a lista de arquivos, sem refatorar fora de escopo, completude antes de fechar).

**Goal:** reconciliar os conflitos/inconsistencias de documentacao e memoria diagnosticados (spec §8 Onda 2), corrigir 1 bug real de config de worker PROD, e aposentar o vocabulario "gold-script" — SEM migrar headers (Onda 4+) nem consolidar scripts inventario (Onda 3).

**Architecture:** edicoes pontuais agrupadas por RISCO e por LOCAL (repo vs fora-do-repo). Fonte-da-verdade de cada correcao citada com `arquivo:linha`. Nenhuma mudanca de logica de negocio; 1 unica mudanca de codigo (config de fila de worker PROD).

**Tech Stack:** edicao de Markdown (docs/memoria) + 1 edicao de shell (`start_worker_render.sh`). Sem testes novos (mudancas declarativas); verificacao = grep + leitura.

## Indice
- [Premissas e anchor](#premissas)
- [Grupo A — Repo (committaveis no branch)](#grupo-a)
- [Grupo B — Fora do repo (memoria + CLAUDE.md global)](#grupo-b)
- [Grupo C — Codigo PROD (exige OK explicito)](#grupo-c)
- [Decisoes para o Rafael](#decisoes)
- [Fora de escopo Onda 2](#fora-escopo)
- [Riscos](#riscos)

## Premissas e anchor <a id="premissas"></a>

Onda 1 ja MERGEADA em local main (`fa84d1850`). Gotchas 1+2 no branch `feat/pad-a-gotcha1`. Exploracao da Onda 2: workflow `wf_5f07b214` (6 agentes), ground-truth no output do workflow. Contagem honesta: **6 conflitos de doc verificados + 1 bug de codigo (worker-RQ, NAO estava nos 6) + ~5 alvos gold-script**. Nenhum e bug de logica de negocio.

> **LOCAL dos arquivos:** memoria do agente e `CLAUDE.md` global vivem em `/home/rafaelnascimento/.claude/` (FORA do repo, FORA do git do projeto, FORA das zonas PAD-A). Edicoes la NAO sao commit; sao manutencao de memoria. So o Grupo A entra no branch/commit.

## Grupo A — Repo (committaveis no branch) <a id="grupo-a"></a>

- [ ] **A-B1 (ALTO valor) — status das skills Odoo no `CLAUDE.md` do projeto.** A linha do `gestor-estoque-odoo` diz "Demais atomos (escriturar, faturar IC) em construcao" — DEFASADO ~2 sprints. Trocar por: `escriturando-odoo V1 LIVE v17.5+ (ABRANGENTE 7 atomos v19+); faturando-odoo PIPELINE A-F LIVE v18`. FONTE: `app/odoo/estoque/CLAUDE.md:3` + `.claude/references/ROUTING_SKILLS.md:3`. **Risco evitado:** agente conclui que skills nao existem e recria logica.
- [ ] **A-D2 — docstring `app/odoo/estoque/scripts/__init__.py:1`.** Trocar `gold-scripts` por `services/primitivas (C1/C2) — ver app/odoo/estoque/CLAUDE.md §2`. FONTE: vocabulario vigente em `app/odoo/estoque/CLAUDE.md`.
- [ ] **A-D3 — banner de vocabulario** no topo de `docs/inventario-2026-05/consolidacao/MAPA_ASSUNTOS.md`, `MAPA_SCRIPTS.md`, `PLANO_MIGRACAO.md`, `manuais/stock_quant_adjustment_service.md`: nota "termo gold-script aposentado; constituicao atual = `app/odoo/estoque/CLAUDE.md`; estes docs sao mineracao transitoria valida (consolidacao real = Onda 3)". NAO mover para _deprecated. (Editar via Edit; sao docs legados Modified, fora do gate added-only.)
- [ ] **A-VERIF:** `python3 scripts/audits/doc_audit.py --enforce-touched --skip-dup` nao deve introduzir block NOVO nos arquivos tocados (sao Modified legados; ja falham C1, NAO regressar). `git add` + commit no branch.

## Grupo B — Fora do repo (memoria + CLAUDE.md global) <a id="grupo-b"></a>

Edicoes em `/home/rafaelnascimento/.claude/` — manutencao de memoria, sem commit. Preservar slugs/wikilinks `[[...]]` (so editar texto).

- [ ] **B-C1 — nginx → Caddy** no `~/.claude/CLAUDE.md` secao "WEB — NGINX SPLIT": o codigo real e Caddy (`Caddyfile` existe; `nginx.conf` NAO). Trocar texto factual nginx→Caddy, `nginx.conf`→`Caddyfile`, heading "NGINX SPLIT"→"CADDY SPLIT". **VERIFICAR ANTES** se a ancora `R-SPLIT-NGINX` existe literal em `app/agente/CLAUDE.md` (cross-ref) — se sim, NAO renomear a ancora. FONTE: `Caddyfile:1`, `start_render.sh`, `memory/render_gunicorn_caddy_split.md:3`.
- [ ] **B-A2 — `memory/worker_render_filas.md`:** atualizar `FILAS_PESADAS` de 5 para 7 (adicionar `inventario`, `agent_eval`). FONTE: `worker_render.py:212` (7 filas). Tornar nao-numerada a entrada `app/portal/workers/__init__.py` (gera confusao "4 vs 3 arquivos").
- [ ] **B-A3 — `~/.claude/CLAUDE.md` secao WORKER RQ:** refletir as 7 filas pesadas atuais. FONTE: `worker_render.py:212`.
- [ ] **B-C1mem — `memory/project_consolidacao_scripts_inventario.md:12`:** trocar `Constituicao: docs/.../ARQUITETURA_ORQUESTRADOR_ODOO.md` (stub movido) por `Constituicao ATUAL: app/odoo/estoque/CLAUDE.md`. FONTE: forward-pointer no proprio stub + `memory/arquitetura_orquestrador_odoo.md:16`.
- [ ] **B-C2 — `memory/feedback_constituicao_skill_so_responsabilidade.md:10`:** titulo diz "§6"; a regra-de-ouro vive em **§3** (`app/odoo/estoque/CLAUDE.md` `## 3. CONTRATO DE ATOMO COMPONIVEL`). Trocar `§6`→`§3 (regra de ouro)`.
- [ ] **B-D1 — `memory/feedback_mapear_profundo_antes_consolidar.md:19`:** "How to apply" ainda prescreve gold-script como metodologia ATIVA. Adicionar aviso "METODOLOGIA EVOLUIU — superada por skills-atomos, ver [[arquitetura_orquestrador_odoo]]".
- [ ] **B-E1 — `memory/gotcha_intercompany_via_po_nao_picking.md` (linha partner_ids):** adicionar 1 frase `(res.partner.id — NAO company_id; company_ids: FB=1/SC=3/CD=4/LF=5, ver [[gotcha_cd_company_id_odoo]])`. FONTE: `app/odoo/constants/operacoes_fiscais.py:53,57`.
- [ ] **B-F1 — `memory/MEMORY.md` 161→≤150 linhas.** Limite hard self-declarado = 150 (`MEMORY.md:8`); esta com 161. **REMOVER ~11 linhas** (truncar nao reduz linhas — entradas ja sao 1 linha fisica). Candidatos (estado de agente ja implementado, com topic file proprio): `b3-escalate-adiado`, `a3-baseline-fase2`, `wiring-agente-tarefa-1-2`, + consolidar 1-2 redundantes Onda D/E/F. **VERIFICAR** que cada topic file referenciado existe e tem o detalhe ANTES de remover do indice.

## Grupo C — Codigo PROD (exige OK explicito do Rafael) <a id="grupo-c"></a>

- [ ] **C-A1 (BUG REAL PROD) — `start_worker_render.sh:301`:** adicionar `agent_validation` na lista `--queues` (apos `agent_eval`). Hoje a fila existe no default de `worker_render.py:143` mas esta AUSENTE do `start.sh` → **em PROD, jobs em `agent_validation` nunca sao processados** (sintoma: polling `/status/{job_id}` retorna 404, igual ao bug historico). FONTE: `worker_render.py:143` (tem) vs `start_worker_render.sh:301` (nao tem). **Afeta runtime PROD ao deploy** — confirmar com Rafael que `agent_validation` DEVE rodar em PROD antes de aplicar.

## Decisoes para o Rafael <a id="decisoes"></a>

1. **C-A1** (acima): `agent_validation` deve rodar em PROD? (parece bug, mas confirmar intencao antes de mudar config de worker).
2. **`worker_atacadao.py` (DEV)** sem 7 filas PROD: corrigir coerencia DEV↔PROD ou foi intencional (DEV nao roda filas pesadas)? Default: NAO mexer (fora do escopo "consertar docs").
3. **Ancora `R-SPLIT-NGINX`** em `app/agente/CLAUDE.md`: manter o nome da ancora mesmo migrando o texto para Caddy? (renomear quebraria cross-refs).
4. **Estilo da citacao de constituicao** nas SKILL.md (escriturando/faturando): padronizar "§3/§6" ou so "Constituicao: app/odoo/estoque/CLAUDE.md" (como as outras 7 skills)? Decisao de estilo.

## Fora de escopo Onda 2 <a id="fora-escopo"></a>

- **Onda 3:** consolidar 59 scripts orfaos + 9 clusters de duplicacao (inventario). Onda 2 so poe banner de vocabulario (A-D3).
- **Onda 4+:** migrar headers `doc:meta` em massa. NAO tocar headers.
- **Tabela CAMINHOS espelhada** (projeto + global CLAUDE.md): limitacao arquitetural, a doc diz "manter sincronizado". Automatizar a sincronia = onda futura.
- **`faturando-odoo/SKILL.md:482+` (~80 LOC antipadroes inline):** verboso mas NAO errado (ja aponta §6.5 canonico). Deferir (refactor de skill, nao conflito).
- **Mover stubs forward-pointer** (`ARQUITETURA_ORQUESTRADOR_ODOO.md`, `ROADMAP_SKILLS.md`): ja corretos, nenhuma acao.

## Riscos <a id="riscos"></a>

- **Wikilinks `[[...]]`:** so editar texto, nunca renomear arquivo/slug (C8 reclama de link orfao).
- **MEMORY.md (B-F1):** remover entrada pode perder contexto — verificar topic file antes.
- **Ancora `R-SPLIT-NGINX`** (decisao 3): verificar `app/agente/CLAUDE.md` antes de tocar.
- **C-A1:** unica mudanca com efeito de DEPLOY (positivo: destrava fila). Tratar com cuidado de deploy + OK.
- **B1 muda `CLAUDE.md` do projeto** (lido por Claude Code E agente web): manter formato da tabela.
- **Gate C1 em `.claude/` global:** confirmar se o gate cobre `~/.claude/CLAUDE.md` (provavelmente nao — fora da zona); editar via Edit de qualquer forma.
