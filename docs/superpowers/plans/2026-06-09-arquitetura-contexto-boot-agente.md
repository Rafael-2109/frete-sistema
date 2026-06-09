<!-- doc:meta
tipo: how-to
camada: L3
sot_de: plano e roadmap de implementacao da arquitetura de contexto do boot do Agente Web (PAD-CTX)
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-09
-->
# Arquitetura de Contexto do Boot do Agente Web — Plano + Roadmap

> **Papel:** plano executavel derivado do estudo 2026-06-09 (16 findings A1-A6/B1-B6/C1-C4 + matriz de 38 itens + red-team de 4 criticos). Implementa o padrao `.claude/references/ARQUITETURA_CONTEXTO_AGENTE.md` (PAD-CTX). **Abra quando:** for executar/retomar qualquer fase da reestruturacao do contexto do agente.

> Fronteira com o plano 2026-06-04 (refactor-governanca-prompt-agente): aquele governa o
> prompt ESTATICO — FASES 0, 1, 2, 4 e 5 FECHADAS; FASE 3 com T3.3/T3.4 + test vectors
> EM ABERTO e o escopo delas PERMANECE LA. Este plano governa o contexto COMPLETO
> (CLAUDE.md, listing de skills, hook dinamico, memorias) sem absorver tasks daquele.

> 🔵 **PROXIMA SESSAO — RETOMAR AQUI:** FASES 0, 1 e 2 CONCLUIDAS (2026-06-09, mesma
> sessao do estudo — ver Rastreamento). Comecar pela FASE 3 (CLAUDE.md alvo +
> compressoes B1, gated por mini-set). F4 depois (hook), F5 (memorias) exige migration.

## Indice

- [Origem e evidencia](#origem-e-evidencia)
- [Visao das fases](#visao-das-fases)
- [FASE 0 — Quick wins](#fase-0--quick-wins)
- [FASE 1 — Bugs e consistencia](#fase-1--bugs-e-consistencia)
- [FASE 2 — Curadoria do listing de skills](#fase-2--curadoria-do-listing-de-skills)
- [FASE 3 — CLAUDE.md alvo + compressoes B1](#fase-3--claudemd-alvo--compressoes-b1)
- [FASE 4 — Hook: orcamento + ordenacao](#fase-4--hook-orcamento--ordenacao)
- [FASE 5 — Memorias: proveniencia + intent + frescor](#fase-5--memorias-proveniencia--intent--frescor)
- [FASE 6 — Governanca e validacao](#fase-6--governanca-e-validacao)
- [FASE 7 — Features opt-in](#fase-7--features-opt-in)
- [Backlog explicito](#backlog-explicito)
- [Mapa item-fase](#mapa-item-fase)
- [Fontes](#fontes)
- [Rastreamento de execucao (append-only)](#rastreamento-de-execucao-append-only)

## Origem e evidencia

- Estudo completo: `relatorios/estudo_contexto_boot_2026-06-09/` (dump do boot real,
  avaliacao do agente, avaliacao do Rafael, findings A1-A6/B1-B6/C1-C4, matriz B5).
- Matriz consolidada: 38 itens (9 R + 2 RP + 19 do agente + 8 lacunas novas N-1..N-8);
  vereditos: 22 CONFIRMADOS, 4 PARCIAIS, 5 NAO-VERIFICAVEIS-AINDA, 1 DECIDIDO.
- Descobertas-chave que motivam a ordem das fases:
  - `AGENT_SKILL_RAG=true` e `AGENT_WORLD_MODEL_INJECT=true` ATIVAS em PROD via env
    (default no codigo e `false`) — blocos com defeito confirmado injetados todo turno (N-7).
  - Listing de skills: ~25,6K chars vs orcamento efetivo ~8K do CLI → truncamento
    silencioso das clausulas "NAO USAR" (C6/A3).
  - Bug de duplicacao: memorias `mandatory` entram 2x no payload (`protected_ids` nao
    inclui as rules do L1 — `memory_injection.py:944`) (N-1).
  - Uso real 90d confirma R-3/R-7: `diagnosticando-banco`=0, `padronizando-docs`=0,
    `gerindo-agente`=1 (admin), `consultando-sentry`=2 (admins) (A5).
  - `agent_memories` NAO tem `source_session_id` — proveniencia navegavel impossivel hoje (A2).
- **Superficies afetadas**: toda fase que toca `hooks.py`/`memory_injection.py`/
  `skills_whitelist.py` afeta Web E Teams (mesmo client). `agente_lojas` tem allow-list
  e hooks proprios — NAO e afetado. Subagentes tem contexto proprio — NAO sao afetados
  (ver tabela de superficies no PAD-CTX).

## Visao das fases

| Fase | Tema | Esforco | Risco | Depende de |
|------|------|---------|-------|------------|
| 0 | Quick wins zero-codigo (env vars + deny-list) | S (horas) | minimo | — |
| 1 | Bugs e consistencia (dedup, subagentes, ponteiros, orfas) | S | baixo | — |
| 2 | Curadoria do listing de skills | S-M | baixo | F0 (deny-list) |
| 3 | CLAUDE.md alvo + compressoes B1 do system_prompt | M | baixo-medio | PAD-CTX publicado |
| 4 | Hook: orcamento + ordenacao | M | medio | F1; validacao p/ reorder |
| 5 | Memorias: proveniencia + intent + teto | M-L | medio-alto | migration; R5 p/ comportamento |
| 6 | Governanca: checks novos + golden dataset 50+ | M | — | habilita F4/F5 plenas |
| 7 | Features opt-in (health flag, painel, few-shot skills, carve-out owner) | S-M cada | baixo-medio | F0-F4 |

## FASE 0 — Quick wins

| # | Acao | Onde | Item |
|---|------|------|------|
| 0.1 | ✅ FEITA 2026-06-09 (Rafael): `AGENT_SKILL_RAG` e `AGENT_WORLD_MODEL_INJECT` setadas `false` no Render. Resta alinhar `.env` local | painel Render / `.env:254,256` | R-1, N-7, C4 |
| 0.2 | Adicionar `carregando-motos-assai` a `SKILLS_DOMINIO_ASSAI` e `consultando-venda-loja` a `SKILLS_DOMINIO_HORA` | `app/agente/config/skills_whitelist.py:99-104` | N-2 |
| 0.3 | Corrigir `_DOMAIN_SKILLS['admin']` (remover as 3 skills dev-only OU remover a entry) — resolve N-8 PARCIALMENTE; derivacao por dados reais fica no backlog | `app/agente/sdk/memory_injection.py:370-380` | R-7, N-8(parcial) |
| 0.4 | Mover changelog inline (~3K chars) do ROUTING_SKILLS.md para arquivo proprio/comentario — ANTES, confirmar via grep que nenhum codigo parseia a linha | `.claude/references/ROUTING_SKILLS.md:32` | N-4 |

**Aceite:** dump de boot novo sem `<skill_hints>`/`<world_model>`; listing sem as 2 skills
de dominio; routing_context sem skills dev-only; CI:
`tests/agente/sdk/test_context_enrichment.py::test_flags_off_por_default` passa sem as
env vars no ambiente. **Rollback:** religar env vars.

## FASE 1 — Bugs e consistencia

| # | Acao | Onde | Item |
|---|------|------|------|
| 1.1 | Dedup user_rules×user_memories: `_build_user_rules()` retorna `(str, ids)` (caller unico em `memory_injection.py:887`); popular `protected_ids` | `memory_injection.py:887-944` | N-1 |
| 1.2 | Adicionar `gestor-estoque-odoo` ao `<subagents>` do system_prompt (delegate_when 2 linhas) + `--update-baseline` (+ verificar assertions de `tests/agente/test_system_prompt_p4.py`) | `app/agente/prompts/system_prompt.md` (~L724) | N-6, R-9 |
| 1.3 | Check de consistencia de subagentes (agents/*.md ↔ system_prompt ↔ CLAUDE.md) no `prompt_size_audit.py` — incluir invariante de nao-orfandade: toda skill em `SKILLS_DELEGADAS_SUBAGENTE` declarada em ≥1 agents/*.md | `scripts/audits/prompt_size_audit.py` | R-9 |
| 1.4 | Ponteiro proeminente p/ INDEX.md completo na secao INDICE do CLAUDE.md | `CLAUDE.md` | N-3 |
| 1.5 | Substituir mencoes inline a GOTCHAS no system_prompt por ponteiro de 1 linha | `system_prompt.md` (R11.1/R11.2) | N-5 |
| 1.6 | Corrigir skill orfa: declarar `faturando-odoo` na secao skills de `.claude/agents/gestor-estoque-odoo.md` (esta na deny-list `skills_whitelist.py:79` sem dono) | `.claude/agents/gestor-estoque-odoo.md` | red-team V4 |

**Aceite:** payload sem memoria duplicada (teste em `tests/agente/sdk/`); lint de
consistencia verde (zero orfas); caminho de descoberta Odoo ≤2 saltos validado manualmente.

## FASE 2 — Curadoria do listing de skills

| # | Acao | Onde | Item |
|---|------|------|------|
| 2.1 | Criar grupo dev-only na deny-list (`consultando-sentry`, `diagnosticando-banco`, `padronizando-docs`) — ADICIONAR a uniao `SKILLS_DELEGADAS_SUBAGENTE` (fora da uniao nao exclui nada) e seguir convencao de nomes `SKILLS_<ESCOPO>_<QUALIFICADOR>` | `skills_whitelist.py` | R-3 |
| 2.2 | ✅ DECIDIDO 2026-06-09 (Rafael): opcao (a) — `gerindo-agente` SAI do listing (entra no grupo dev-only da deny-list); admin mantem tela `/agente/memorias` + Claude Code dev. Alternativa (b) gate por perfil fica registrada caso surja demanda via chat | `skills_whitelist.py` | R-3 |
| 2.3 | Unificar `lendo-arquivos` + `lendo-documentos` (roteamento interno por extensao; scripts fisicos inalterados). Tocar: SKILL.md×2, `tool_skill_mapper.py:108-109`, `ROUTING_SKILLS.md:49`, whitelist; atualizar comentario em `chat.py:2269` (documentacao apenas); `test_agente_files_root_consistency.py:22` so muda se o diretorio for renomeado. SEM alias (SDK nao suporta): comunicar os 3 usuarios de lendo-documentos + nota no SKILL.md unificado | multiplos | R-4 |
| 2.4 | Reescrever descriptions das skills restantes no template ≤500 chars (PAD-CTX) | `.claude/skills/*/SKILL.md` | C6, R-2 |
| 2.5 | Check de orcamento do listing (soma descriptions ≤8K) no pre-commit | `scripts/audits/` | C6 |

Nota (red-team V4): `prd-generator`, `ralph-wiggum`, `skill-creator`, `resolvendo-problemas`
sao user-scope (`~/.claude/skills/`) e NUNCA carregam em producao
(`setting_sources=["project"]`) — nenhuma acao de deny-list e necessaria para elas.

**Aceite:** listing ≤18 skills durante a transicao e ≤17 depois; soma ≤8K chars (sem
truncamento CLI); roteamento das top-skills inalterado em teste manual (mini-set de 10
perguntas tipicas). **Superficies:** afeta Web + Teams; subagentes inalterados.

## FASE 3 — CLAUDE.md alvo + compressoes B1

Aplicar os vereditos secao a secao do PAD-CTX (finding B2): TECH STACK comprimido; DADOS
reescrito por superficie (web = `mcp__sql` + skills; corrigir instrucao "exclusivamente
MCP Render" — a tool `query_render_postgres` NAO existe no agente web); remover
`source .venv`, FORMATACAO Jinja2 (→ `~/.claude/CLAUDE.md`; trade-off de versionamento
declarado no PAD-CTX), linha PAD-A, Design System → 1 linha; SUBAGENTES: comprimir
`gestor-estoque-odoo` (1.139→~120 chars), manter `desenvolvedor-integracao-odoo` marcado
dev-only; remover 3 refs dev-only de Confiabilidade. Alvo: 231→~186 linhas (-19%).

Compressoes B1 no system_prompt (gated por mini-set; aplicar SOMENTE as que passam no
criterio "poda por sinal"): R7 fast-paths → trigger 1 linha + ponteiro ROUTING_SKILLS.md
(~-15L, resolve R-2); metadata -6L; R5 parallel_calls -4L (dedup com preset); R10
exemplos → REGRAS_OUTPUT.md -9L; task_management -4L; routing_confidence -3L. Cada corte
respeita os intocaveis (NUNCA tocar `<why>`, hierarquia, critical_*).

**Aceite:** diff revisado pelo Rafael; agente web responde igual em 10 perguntas do
mini-set; validacao explicita do bug B2: pergunta "quantos pedidos abertos?" deve usar
`mcp__sql__consultar_sql` (nao tentar `query_render_postgres`); `~/.claude/CLAUDE.md`
recebe o conteudo movido (nada se perde para o dev).

## FASE 4 — Hook: orcamento + ordenacao

| # | Acao | Onde | Item |
|---|------|------|------|
| 4.1 | Relocar `stale_empresa` + `improvement_responses` do briefing para consulta on-demand (skill `gerindo-agente`/tela admin). Detalhe: a flag `AGENT_IMPROVEMENT_DIALOGUE` continua governando o DIALOGO; criar controle separado para a INJECAO no boot (remover as chamadas de `intersession_briefing.py:73,85-87` ou flag propria default off) | `app/agente/services/intersession_briefing.py` | C3, R-6 |
| 4.2 | Comprimir `debug_mode_context` (9→4 linhas) e `sql_admin_context` (12→6) — ja sao condicionais por user; so o texto e gordo | `hooks.py:1331-1381` | R-8 |
| 4.3 | Orcamento por bloco (tabela PAD-CTX) com ENFORCEMENT: teto ~300c por memoria Tier 2 (destilado + ponteiro `view_memories`); user_rules mantem cap vigente (`MANDATORY_RULES_MAX_COUNT=12`, correction_count DESC); implementar ordem de corte no overflow (Tier 2 → directives organicas → routing_context; nunca user_rules/pendencias) | `memory_injection.py` | R-6 |
| 4.4 | Implementar a ORDEM-ALVO COMPLETA da tabela PAD-CTX (nao so pendencias): (a) externalizar `pendencias_acumuladas` de `_build_session_window()` (`memory_injection.py:215-224`) retornando bloco separado; (b) reordenar a concatenacao em `hooks.py:1471` com pendencias por ULTIMO | `memory_injection.py` + `hooks.py:1471` | D3 |
| 4.5 | Excecao condicional: `improvement_response` de skill_bug ATIVO volta ao hook SOMENTE se o turno usar a skill afetada | `intersession_briefing.py` | C3/A3 |
| 4.6 | Criar `tests/agente/sdk/test_hook_budget.py`: mede payload tipico ≤15KB por modelo; valida ausencia de skill_hints/world_model; valida ordem dos blocos | `tests/agente/sdk/` | governanca PAD-CTX |

**Aceite:** hook tipico ≤15KB (medido pelo teste 4.6); zero regressao no mini-set; 4.4
validado com golden dataset (15 casos atuais + judge; ampliacao na F6).
**Superficies:** afeta Web + Teams; subagentes NAO recebem hook (mudanca invisivel a eles).

## FASE 5 — Memorias: proveniencia + intent + frescor

| # | Acao | Onde | Item |
|---|------|------|------|
| 5.1 | Migration (DDL .py + .sql): `agent_memories` + `source_session_id TEXT`, `last_confirmed TIMESTAMP`, `confidence TEXT` | `scripts/migrations/` | RP-2, A6 |
| 5.2 | Popular `source_session_id` no save_memory — callsite NOVO em `memory_mcp_tool.py:~2028-2035` (logica principal de create/update; os usos existentes de `get_current_session_id()` nas linhas 2106/2307/3468 sao SO do KG). Importar de `app/agente/config/permissions.py:78` (ha ContextVar local homonimo em `memory_mcp_tool.py:78` — nao confundir). Daemons pos-sessao (pattern_analyzer, session_summarizer): aceitar `session_id` por parametro opcional; sem ele, NULL | `memory_mcp_tool.py` | RP-2 |
| 5.3 | Expor proveniencia na injecao COM protecao cross-user (PAD-CTX): memoria pessoal → `session="..."`; memoria EMPRESA → apenas `created_by` + `date` (UUID de sessao alheia nao vaza; `search_sessions` e per-user e cross-user exige debug_mode). Instrucao de navegacao condicional no R0/MEMORY_PROTOCOL.md | `memory_injection.py` + `system_prompt.md` R0 + `MEMORY_PROTOCOL.md` | RP-2 |
| 5.4 | RAG por INTENT DO TURNO: embedding da mensagem atual como query do Tier 2 (substitui dominio historico); fallback de recencia so com teto 4×300c | `memory_injection.py` (Tier 2) | C5, RP-2 |
| 5.5 | Few-shot episodico condicional: turno sobre fatura CarVia → injetar caso 161-9 como exemplo (cosine >0,75) | `memory_injection.py` | RP-2, A4 |
| 5.6 | Formalizar promocao memoria→codigo (4 criterios PAD-CTX) no MEMORY_PROTOCOL.md + marcar promovidas (saem da injecao); aplicar as 2 ja-promovidas (tmpdir, arquivo-vazio — completar check tamanho>0 em `exportando-arquivos`) | `MEMORY_PROTOCOL.md` + dados | R-6 |
| 5.7 | Destilacao "top 3 erros recorrentes" no boot — SO quando `agent_skill_effectiveness` tiver ≥30 dias de dados | `intersession_briefing.py` | A3 |

**Aceite:** memoria pessoal nova navegavel ate o transcript; memoria empresa expoe
created_by sem vazar sessao; precision@k do Tier 2 medida antes/depois (amostra de 20
turnos reais); zero duplicata; mini-set sem regressao. **Superficies:** principal
(Web+Teams); subagentes nao recebem memorias injetadas — inalterados.

## FASE 6 — Governanca e validacao

- Ampliar golden dataset 15→50+ casos (R5 do ROADMAP — destrava validacao plena de F4/F5).
- Registrar os 5 checks do PAD-CTX (consistencia subagentes, orcamento listing, orcamento
  hook, nao-orfandade da deny-list, checklist de admissao) no fluxo R-EXEC-5/pre-commit.
- **Atualizar `app/agente/CLAUDE.md` (secao R-EXEC-5)** para apontar para o checklist de
  admissao do PAD-CTX — dependencia declarada no padrao; sem isso o check (5) nao existe
  no fluxo real.
- Documentar lista de intocaveis (M1-M6) — feito no PAD-CTX; referencia-la no checklist
  de mudanca de prompt.
- D1 (concisao vs seguranca): DECIDIDO — L1>L4; registrado no PAD-CTX.

## FASE 7 — Features opt-in

| # | Feature | Item | Nota |
|---|---------|------|------|
| 7.1 | Flag de saude no boot (estado do Circuit Breaker Odoo/SSW, 1 linha) | A2 | read-only, custo S |
| 7.2 | Painel opt-in de estado vivo (pedidos abertos, DFEs bloqueados) | A1 | quebra cache — so por comando/flag |
| 7.3 | Few-shot nas 2 skills top-frequencia (separacao, baseline) | A4/R17 | em SKILL.md, nunca no prompt |
| 7.4 | ✅ RESOLVIDO 2026-06-09 (Rafael): a necessidade real e admin consultar sessoes de outros usuarios — JA coberta por debug_mode (`target_user_id`, acesso logado). Sem carve-out de revelacao de prompt; friccao aceita | D2 | sem acao |
| 7.5 | `preferred_skills` derivado de dados reais (`agent_step.tools_used` por dominio) — completa N-8 | N-8(completo) | requer ≥30d de agent_step |

## Backlog explicito

- N-8(completo): derivacao de preferred_skills por uso real → F7.5.
- A3 destilacao de erros → F5.7 (gated por volume de dados).
- Compressoes B1 vetadas pelo mini-set (se houver): registrar aqui com motivo, nao
  re-tentar sem novo dado.
- Multi-dev: promover conteudo dev-only de `~/.claude/CLAUDE.md` a doc versionado
  (trade-off declarado no PAD-CTX) — sem acao enquanto single-dev.

## Mapa item-fase

F0: R-1, R-7, N-2, N-4, N-7, N-8(parcial), C4(parcial) ·
F1: N-1, N-3, N-5, N-6, R-9, faturando-odoo(orfa) ·
F2: R-3, R-4, C6, A5(dados de uso) ·
F3: R-5, R-2, C1, RP-1(aplicacao), compressoes B1 ·
F4: C3, R-6(orcamento), R-8, D3 ·
F5: RP-2, C5, R-6(teto+promocao), A6, A3, A4(parcial) ·
F6: C2, D1, M1-M6, R5-ROADMAP ·
F7: A1, A2, A4, D2(resolvido sem acao), N-8(completo) ·
Padrao em si (PAD-CTX publicado): RP-1, R-2(criterio), A5(roteamento), C1(fonte canonica).

## Fontes

- FONTE: `.claude/references/ARQUITETURA_CONTEXTO_AGENTE.md` (PAD-CTX — o padrao que este plano implementa).
- FONTE: `relatorios/estudo_contexto_boot_2026-06-09/` — findings A1-A6, B1-B6, C1-C4 + matriz B5 (38 itens) + anexos (dump do boot, avaliacoes) + red-team (4 criticos).
- FONTE: `docs/superpowers/plans/2026-06-04-refactor-governanca-prompt-agente.md` — prior art do prompt estatico (FASES 0/1/2/4/5 fechadas; FASE 3 T3.3/T3.4 abertas; baseline + pre-commit vigentes).

## Rastreamento de execucao (append-only)

- 2026-06-09 — Plano criado a partir do estudo (sessao "estudo do contexto de boot").
  Red-team de 4 criticos incorporado (correcoes de viabilidade, conformidade e
  cross-user). Nenhuma fase executada.
- 2026-06-09 (mesma sessao, decisoes do Rafael) — F0.1 EXECUTADA (env vars `false` no
  Render); F2.2 DECIDIDA (opcao a: deny-list); D2 RESOLVIDO (cross-user admin ja coberto
  por debug_mode; sem carve-out). Entregaveis commitados (sem push — deploy so no push).
- 2026-06-09 — **FASE 0 CONCLUIDA**: 0.2 (2 skills nos grupos de dominio na deny-list),
  0.3 (entry 'admin' REMOVIDA de `_DOMAIN_SKILLS` — dominio segue valido p/ armadilhas),
  0.4 (changelog de 3.847 chars do ROUTING_SKILLS.md:32 movido p/ comentario HTML ao fim;
  grep confirmou zero consumidores programaticos), `.env` local alinhado (flags `false`).
  Correcao de docs: caminho do ContextVar e `app/agente/config/permissions.py:78`
  (NAO `sdk/`; PAD-CTX e plano corrigidos). Aceite: 26 testes verdes
  (test_skills_whitelist_consolidation + test_context_enrichment, incl.
  test_flags_off_por_default).
- 2026-06-09 — **FASE 1 CONCLUIDA**: 1.1 dedup N-1 via TDD — desvio de implementacao
  registrado: em vez de mudar a assinatura de `_build_user_rules` (10 testes a quebrar),
  extraida query canonica `_query_user_rules` + nova `_get_user_rule_ids`; uniao em
  `protected_ids` condicionada a regras efetivamente injetadas (3 testes novos, 12/12).
  1.2 `gestor-estoque-odoo` no `<subagents>` (+4L; baseline 788L/986L atualizado +
  bloco auto-medido do CLAUDE.md do modulo). 1.3 `--check-consistency` no
  prompt_size_audit.py (3 projecoes + nao-orfandade da deny-list com excecoes
  declaradas: HORA→allow-list lojas, DEV_RESERVED→por design, consultando-sql sem
  SKILL.md) + hook pre-commit estendido (vigia agents/, whitelists, CLAUDE.md raiz).
  1.4 ponteiro INDEX.md no topo do INDICE do CLAUDE.md. 1.5 VERIFICADA SEM EDICAO —
  R11.1/R11.2 ja conformes (politica 1 linha + ponteiro GOTCHAS.md). 1.6
  `faturando-odoo` declarada no gestor-estoque-odoo.md (orfa resolvida). Aceite:
  17 testes verdes + check-consistency OK + check-delta OK.
- 2026-06-09 — **FASE 2 CONCLUIDA**: 2.1+2.2 grupo `SKILLS_DEV_RESERVED` na deny-list
  (consultando-sentry, diagnosticando-banco, padronizando-docs, gerindo-agente —
  decisao Rafael; admin mantem tela /agente/memorias) + 2 testes estruturais novos.
  2.3 UNIFICACAO lendo-arquivos+lendo-documentos: ler_doc.py/references/evals movidos
  para lendo-arquivos (mesma profundidade de sys.path), SKILL.md unificado com
  roteamento por extensao, SCRIPTS.md fundido (TOC), diretorio lendo-documentos
  REMOVIDO; consumidores atualizados (tool_skill_mapper com entry historica,
  ROUTING_SKILLS linhas 48-49/236, auditor-financeiro.md frontmatter+corpo, teste
  de path, comentario chat.py). Sem alias (SDK nao suporta) — nota de consolidacao
  na description. 2.4 VINTE descriptions reescritas no template (workflow 20 agentes
  + revisao); REFINAMENTO DO PADRAO descoberto na aplicacao: linha "Routing completo:
  ROUTING_SKILLS.md" repetida por skill custava ~1,1K chars (redundancia R-2 contra o
  proprio padrao) — removida do template (dono = system_prompt routing_strategy);
  PAD-CTX atualizado (alvo ≤450c/skill). 2.5 `skills_listing_audit.py` criado
  (--check: total ≤8K, aviso >500c/skill) + ligado ao pre-commit (gatilho SKILL.md/
  whitelist). RESULTADO: listing 28→21 skills, 25,6K→7.946 chars (-69%) — DENTRO do
  orcamento do CLI, fim do truncamento silencioso. Aceite: 43 testes verdes,
  check-consistency OK, listing audit OK, doc_audit 0 bloqueantes. Nota R2.2 NO-OP:
  prd-generator/ralph-wiggum/skill-creator/resolvendo-problemas sao user-scope
  (~/.claude/skills) e nunca carregam em prod — nenhuma deny-list necessaria
  (red-team V4).
