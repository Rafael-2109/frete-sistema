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

> 🔵 **PROXIMA SESSAO — RETOMAR AQUI:** FASES 0-5 CONCLUIDAS + MIGRACAO
> voyage-4-large LIVE E VALIDADA EM PROD (2026-06-10: deploy 87bcf8c7f + reindex
> das 549 + env removida; validacao fim-a-fim: query real → top-1 0.5831
> injetavel, threshold 0.40 ativo nos logs — ver Rastreamento). Relatorio:
> `relatorios/estudo_contexto_boot_2026-06-09/precision_at_k_baseline_2026-06-10.md`
> (inclui A/B dedup: PERMANECE no lite — decisao medida).
> **F6 EXECUTADA 2026-06-10** (ver as 3 entradas F6 no Rastreamento): cap
> tier1/user_rules LIVE no codigo (TDD, 16 testes novos, suite verde, review
> adversarial 14 agentes com 3 findings corrigidos + bug do sanitize×pointer);
> 5 checks PAD-CTX registrados no pre-commit/R-EXEC-5; golden dataset 15→54
> (6 agentes R5, dado-apenas, A3 segue aposentado); ablacao por bloco medida
> (relatorio `ablacao_por_bloco_2026-06-10.md`: tier1 destilado 95% util,
> directives 0/20, routing com 2 riscos → evidencia p/ C5/F7.5).
> Proxima: (1) **pos-deploy** — validar logs [MEMORY_INJECT] PROD (users
> 1/18/82: overflow_cortes=[] e tier2>0) + mini-set; (2) fila de curadoria
> (REQUER OK do Rafael): 78 quase-duplicatas → memory_consolidator; user_rule
> "sessao N" (user 1) → empresa/heuristicas; CNPJ no caso af-01 pre-existente.
> Aceite formal F5: re-medir precision@k "depois" com o harness (~30min) apos
> dias de trafego. 5.7 acorda sozinho ~08/07 (gate 30d). F7 por ultimo
> (ablacao deu evidencia nova p/ F7.5 preferred_skills).

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

## Mini-set de validacao pos-deploy (F0-F3)

Rodar NO AGENTE WEB apos o push/deploy das fases (validacao comportamental que o
ambiente dev nao cobre). Criterio: roteamento correto + comportamento inalterado.

| # | Pergunta | Esperado |
|---|----------|----------|
| 1 | "tem pedido do Atacadao?" | gerindo-expedicao (PRE-faturamento) |
| 2 | "NF 12345 foi entregue?" | monitorando-entregas (POS) |
| 3 | "quanto tem de palmito?" | fast-path consultar-estoque/gerindo-expedicao |
| 4 | "crie separacao do VCD123 pra amanha" | criar-separacao + confirmacao R3 (nunca direto) |
| 5 | "atualizar baseline" | gerando-baseline-conciliacao (boundary — fast-path R7 removido) |
| 6 | "quantos pedidos abertos hoje?" | `mcp__sql__consultar_sql` (NUNCA tentar `query_render_postgres` — bug B2) |
| 7 | "rastreie NF 139310" | rastreando-odoo |
| 8 | anexo .xlsx "analise essa planilha" E anexo .ret "le esse retorno" | lendo-arquivos UNIFICADA roteia os dois |
| 9 | "monte um dashboard interativo de fretes" | gerando-artifact + marker [ARTIFACT:uuid] na resposta |
| 10 | "o que faz a opcao 436 do SSW?" | acessando-ssw |
| 11 | "zera o saldo do lote X no Odoo" | delega gestor-estoque-odoo (novo no `<subagents>`) |
| 12 | dump de boot novo | sem skill_hints/world_model; sem memoria mandatory duplicada; listing 21 skills sem truncar |

## Backlog explicito

- **skill_bug rastreando-odoo** (descoberto no mini-set item 7, 2026-06-09): o script
  trava no campo `account.full.reconcile`; o agente contornou via Odoo direto.
  Corrigir o script E investigar a NAO-adesao a R9 (agente nao registrou via
  register_improvement apesar de bug + workaround = sinal forte da diretiva).
- **Fallback de recencia injeta ~63KB/turno** (logs [MEMORY_INJECT] do mini-set,
  user_id=74/bot): semantic=0 + fallback=True em TODOS os turnos → 15 memorias
  empresa por RECENCIA (irrelevantes ao prompt) + tier2b ~51KB + budget=unlimited
  (Opus). Confirma C5/RP-2 em grau PIOR que o dump do estudo; F4.3 (teto por bloco)
  e F5.4 (intent + teto no fallback) atacam exatamente isso — considerar PRIORIZAR.
  Investigar tambem por que semantic=0 p/ user 74 (embeddings ausentes?).
- **system-pitfalls duplicado**: `/memories/empresa/armadilhas/system-pitfalls.xml`
  E `.json` injetados JUNTOS todo turno (mesmo conteudo, 2 formatos) — consolidar
  em 1 registro (dado, nao codigo).
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
- 2026-06-09 — **FASE 3 CONCLUIDA**: (a) CLAUDE.md raiz por superficie — Contexto e
  DADOS reescritos (bug B2: agente web NAO tem `query_render_postgres`; fonte web =
  mcp__sql + skills), TECH STACK -5 linhas dev-only, FORMATACAO Jinja2 e Design System
  e linha PAD-A e 3 refs de criacao de subagents MOVIDAS para `~/.claude/CLAUDE.md`
  (TECH STACK COMPLEMENTO + DESIGN SYSTEM + REGRAS DEV 4-5 + REFERENCIAS DEV-ONLY),
  `gestor-estoque-odoo` comprimido 1.139→~230c (detalhe → app/odoo/estoque/CLAUDE.md),
  "NAO ESTENDER" marcado (dev). **OVERRIDE de B2 com evidencia**: regra AMBIENTE
  VIRTUAL FICA — o runtime do Render cria `.venv` na raiz e as skills do agente web
  usam `source .venv/bin/activate` em PROD (B2/A4 erraram ao marcar dev-only).
  (b) Compressoes B1 no system_prompt v4.3.3→4.4.0: metadata 1 linha (-6L),
  role_definition /tmp dedup preset (-1L), R5 parallel 7→4L, R7 fast-path baseline
  REMOVIDO (dono = boundary baseline_financeiro, fecha R-CROSS-1/R-2) + artifact
  comprimido, R10 frases-modelo Odoo/SSW MOVIDAS p/ REGRAS_OUTPUT.md I5 (+ ponteiro),
  routing_confidence template comprimido, delegation_pattern em bullets. system_prompt
  788→763L (-25L); total estatico 986→961L (~16,3K tok); baseline TRAVADO no valor
  novo (crescimento futuro bloqueia no pre-commit). Lint pegou 2 hedges ("alguns"/
  "varios") nas frases movidas + 1 PRE-existente no I7 — corrigidos. Aceite: 23 testes
  verdes, check-delta/consistency/listing OK, doc_audit 0 bloqueantes. Validacao
  comportamental: mini-set de 12 itens documentado acima — PENDENTE pos-deploy
  (ambiente dev nao roda o agente web).
- 2026-06-09 — **PUSH + DEPLOY + MINI-SET**: push `3173bab60..4e7574133` (7 commits);
  deploy `dep-d8k8cl5dt1ts73atk4m0` live em 7min. Mini-set executado via Playwright
  no agente web PROD: itens 1-6, 10, 11 ✅ (roteamento PRE/POS correto, fast-path
  estoque com projecao, separacao validou pedido inexistente SEM criar, baseline
  canonico via boundary SEM o fast-path removido, SQL direto sem query_render_postgres
  — bug B2 confirmado corrigido, SSW doc completa, estoque Odoo AO VIVO com zero
  execucao e pedido de confirmacao via caminho gestor-estoque-odoo). Item 7 🟡:
  roteamento rastreando-odoo correto MAS bug real do script descoberto
  (`account.full.reconcile`) + agente contornou SEM registrar R9 — ambos no backlog.
  Item 9 🟡 parcial: fluxo gerando-artifact iniciou correto (consultas paralelas);
  conclusao do build nao confirmada na janela de captura (sessao 24836bfe ainda
  processando) — reverificar `agente_artifacts`. Itens 8 (anexo .xlsx/.ret na skill
  unificada) e 12 (dump de boot novo) PENDENTES de validacao manual do Rafael.
  Gotcha de medicao: timestamps de agent_sessions sao BRT-naive vs NOW() UTC.
- 2026-06-09 — **FASE 4 CONCLUIDA** (TDD: 29 testes novos escritos ANTES — red
  confirmado — em `tests/agente/sdk/test_hook_budget.py` +
  `tests/agente/test_intersession_briefing_boot.py`):
  4.1 `stale_empresa` E `intelligence_report` REMOVIDOS do briefing de boot
  (funcoes deletadas; info on-demand via tela admin + rotas D7) — DESVIO
  declarado: a tarefa citava so stale+improvement, mas o PAD-CTX lista
  intelligence_report nos "excluidos do boot operacional" (padrao > plano);
  `improvement_responses` gated por flag NOVA `AGENT_IMPROVEMENT_INJECT_BOOT`
  default off (`AGENT_IMPROVEMENT_DIALOGUE` segue governando SO o dialogo D8).
  4.2 `debug_mode_context` 9→4 linhas e `sql_admin_context` 12→6 (conteudo
  essencial preservado: target_user_id/auditoria; DML so via MCP + confirmacao R3).
  4.3 `TIER2_MEMORY_CHAR_CAP=300` (destilado meta WHEN/DO + ponteiro
  `view_memories(path)` via `_distill_tier2_content`) + `TIER2_MAX_MEMORIES=4`
  + `_fit_hook_budget` (teto `HOOK_CONTEXT_TARGET_CHARS=15000`; ordem de corte
  tier2 → directives organicas [constitucional fica] → routing; NUNCA
  user_rules/tier1/briefing/sessions/pendencias). Budget por modelo mantido
  como teto ADICIONAL — Opus deixa de ser unlimited na pratica (ataca o
  backlog "fallback injeta ~63KB/turno"; teste reproduz o cenario: 15 mems
  empresa de 4KB → payload ≤15KB e ≤4 injetadas). user_rules: cap vigente intocado.
  4.4 ORDEM-ALVO completa: `_build_session_window` retorna `(sessions,
  pendencias)`; `_load_user_memories_for_context` retorna `(main, tail, ids)`
  — main = user_rules→user_memories→directives→briefing→routing; tail =
  recent_sessions→pendencias; cache de sessao virou 5-tuple;
  `_build_routing_context` NAO embute mais directives (split
  `_build_operational_directives_parts` const/organicas; wrapper publico
  preservado p/ testes); montagem final em `hooks.py` via funcao pura
  `_compose_hook_context` com pendencias por ULTIMO (debug/sql_admin antes
  do tail). R0b do system_prompt segue valido (bloco continua existindo).
  4.5 `get_skill_bug_responses_for_skill` (intersession_briefing) consumida
  por `_build_skill_pretool_context` no PreToolUse Skill (junto ao lembrete
  AGENT_SKILL_EVAL, mas SEM gate de flag — query leve best-effort); match por
  `evidence_json['skill']` OU mencao em title/description (responses do
  register_improvement real-time nao gravam o campo skill).
  4.6 `test_hook_budget.py` cobre ordem, caps, overflow, teto 15KB e ausencia
  de skill_hints/world_model. Aceite: 29 novos verdes + suite `tests/agente`
  1336 passed (1 flake pre-existente `test_client_pool::test_pool_status_healthy`
  — passa isolado; teardown async do pool, area nao tocada). PAD-CTX: check (3)
  marcado como criado. PENDENTE pos-deploy: mini-set + dump de boot novo
  (ordem real dos blocos, payload, sem stale/intelligence) + golden dataset
  para validacao plena do 4.4 (F6).
- 2026-06-09 — **CORRECAO F2.5 (fórmula real do CLI)**: log debug do CLI pre-push
  acusou "Skill listing over budget: 21 skills, 8448 chars > 8000" enquanto o
  `skills_listing_audit.py` dava OK em 7.946 — o audit somava SO descriptions.
  Formula REAL extraida do binario CLI 2.1.170: entrada = `- {name}: {desc}` →
  `len(name)+4+len(desc)`; total += N-1 newlines; budget = 200K tok × 4 × 1% =
  8.000; escapes: env `SLASH_COMMAND_TOOL_CHAR_BUDGET` / setting
  `skillListingBudgetFraction` (registrados no PAD-CTX como escape consciente —
  o padrao e caber no default). Audit CORRIGIDO para a formula real (validada:
  reproduziu 8.448 exato) + guard de `whenToUse` (CLI concatena na description;
  nenhuma skill usa hoje). PODA fina em 16 descriptions (gatilhos/anti-gatilhos
  preservados; fundidos semi-duplicados; removidos detalhes internos ler.py/
  ler_doc.py e nota de consolidacao): 8.448 → **7.929 ≤ 8.000 na medicao do
  CLI** — fim REAL do truncamento silencioso (a F2 havia fechado so na medicao
  parcial). Atencao: o deploy do push `c104a52fc` NAO contem este fix — exige
  novo push.
- 2026-06-09 — **VALIDACAO POS-DEPLOY F4 EM PROD** (deploy `dep-d8k9t5647okc73bi6qug`,
  commit `ae601defb` = F4 + fix listing, live 23:22 UTC): log real
  `[MEMORY_INJECT] user_id=74` (o caso EXATO do backlog 63KB: semantic=0 +
  fallback=True) mostrou `total_chars=13071` ≤ 15.000 (**-79%** vs ~63KB),
  `total_injected=5` com `skipped_budget=11/15` (cap TIER2_MAX_MEMORIES=4
  cortando o fallback guloso), `main_chars=10117`/`tail_chars=2954` (split
  main/tail ativo — campos so existem na F4), `overflow_cortes=[]` (caps
  bastaram). Roteamento sem regressao: PRE-faturamento ("tem pedido do
  Atacadao?" → carteira 100 pedidos) e POS ("entregas pendentes" → NFs/
  embarques/previsoes). Warning "Skill listing over budget" nao aparece nos
  app logs do Render (stderr de debug do CLI nao chega la — verificacao por
  log INCONCLUSIVA em PROD; garantia = formula validada que reproduziu o
  8.448 exato, agora 7.929). PENDENTES: semantic=0 p/ user 74 persiste
  (investigacao F5.4 — embeddings ausentes?); dump de boot completo (ordem
  visual dos blocos) segue como item 12 manual.
- 2026-06-10 — **FASE 5 CONCLUIDA** (diagnostico ANTES de codar, conforme ponteiro):
  **(diag-1) Causa raiz do semantic=0 NAO era embeddings** (cobertura 199/200
  empresa, 3/3 user 74): env PROD `AGENT_MEMORY_MIN_SIMILARITY=0.55` esta ACIMA
  de quase toda a distribuicao do voyage-4-lite (medicao empirica: 70 scores
  contra o indice PROD, 1 unico >=0.55) → semantic=0 em 100% dos turnos de TODOS
  os usuarios; fallback de recencia rodava sempre. `.env` local tem flag morta
  `AGENT_MEMORY_SEMANTIC_SEARCH` (nenhum codigo le; o nome real e
  `MEMORY_SEMANTIC_SEARCH`, default true).
  **(diag-2) precision@k baseline** (20 turnos reais, 9 usuarios, 20 judges
  Sonnet via workflow; relatorio
  `relatorios/estudo_contexto_boot_2026-06-09/precision_at_k_baseline_2026-06-10.md`):
  fallback PROD = **0.013** (1 util/80); lite@0.45 = 0.558 (15/20); + A/B
  voyage-4-large no MESMO corpus (361 memorias, re-embed local read-only):
  large@0.45 = **0.842**, large@0.40 = 0.673 com 18/20 — large rankeia ~+50%
  melhor; escala de similarity NAO transfere entre modelos. 2/20 turnos
  irrecuperaveis por embedding (anafora; pergunta factual de skill).
  **Implementacao via TDD** (27 testes novos; suite tests/agente 1365+ verde;
  1 falha de residuo KG dos proprios testes corrigida — fixture neutraliza
  embed/KG via monkeypatch + 50 entidades orfas limpas do banco local):
  5.1 migration `2026_06_09_agent_memories_proveniencia.{py,sql}` (3 colunas +
  indice; aplicada LOCAL; schema JSON regenerado — incluiu o `meta` de 06-08
  que faltava). 5.2 helpers `_apply_provenance_on_create`/`_touch_last_confirmed`
  em memory_mcp_tool (create/update + update_memory) + session_summarizer
  (`_SUMMARY_MEMORY_PATH` extraida; origem acompanha o resumo) + cadeia
  pattern_analyzer (4 funcoes com `session_id=None` opcional). 5.3
  `_memory_open_tag` cross-user-safe (pessoal: session=+date=; empresa:
  created_by=+date=; UUID alheio nunca vaza) + R0 instrucao de navegacao (+5L;
  baseline re-travado 768L/966L) + MEMORY_PROTOCOL.md §Proveniencia. 5.4
  REINTERPRETADA pelo diagnostico: a query semantica JA ERA o prompt do turno
  (plano estava desatualizado) e o teto do fallback JA veio da F4.3 — entregue:
  filtro `is_cold` no SQL da busca (pgvector + fallback python; `_archived_*`
  poluiam 3/10 do top-10) + calibracao de threshold (acao de env = Rafael).
  5.5 few-shot episodico com DESVIO DECLARADO (cosine 0.75 do plano e
  inatingivel na distribuicao real; default `AGENT_FEWSHOT_MIN_SIMILARITY=0.55`
  + `_is_episodic_memory` + cap 1200c em `_render_tier2_candidate`). 5.6
  MEMORY_PROTOCOL.md §Promocao (4 criterios; mecanismo is_cold +
  meta.promovida_para; check tamanho>0 em exportando-arquivos JA EXISTIA —
  guard `_verificar_entrega` P7 #787) + data-fix
  `2026_06_09_f5_memorias_datafix.py` (2 promovidas + system-pitfalls.json →
  cold; dry-run default; PENDENTE rodar em PROD). 5.7 `_check_recurring_errors`
  no briefing (top-3 skills 2+ falhas/30d; gate >=30d de historico — DORMANTE
  ate ~08/07; flag `AGENT_RECURRING_ERRORS_BOOT` default true). Backlog
  system-pitfalls consolidado via data-fix (o .json e fonte do tool
  log_system_pitfall, lido por get_by_path que ignora is_cold; o .xml segue
  como formato injetado). DADO NOVO p/ F6: blocos fixos grandes estouram o
  teto 15K e cortam TODO o adaptativo (user 18: rules 6,2K + tier1 7,6K →
  overflow_cortes=['tier2','directives_organicas','routing']) — candidato a
  cap de tier1/user_rules na F6.
- 2026-06-10 — **POS-F5: acoes PROD do Rafael EXECUTADAS + migracao voyage-4-large
  IMPLEMENTADA**: (a) migration proveniencia RODADA em PROD; (b) env
  `AGENT_MEMORY_MIN_SIMILARITY` ajustada no Render; (c) data-fix APLICADO em PROD
  (ids 433 system-pitfalls.json, 868 tmpdir, 871 arquivo-vazio → cold/promovidas).
  (d) MIGRACAO LARGE (decisao Rafael, base no relatorio precision@k):
  `VOYAGE_MEMORY_MODEL` (default voyage-4-large) governa SO o retrieval de
  memorias — query da busca + coluna `embedding` + memory_indexer; DEDUP
  permanece no DEFAULT lite (thresholds 0.85/0.80 nao medidos no large);
  busca filtra `model_used = VOYAGE_MEMORY_MODEL` (janela deploy→reindex nunca
  compara cross-model); fallback do dedup (101 linhas dedup_embedding NULL em
  PROD) re-embeda a query no modelo da coluna; threshold default 0.45→0.40
  (calibrado p/ large: cobertura 18/20, precision 0.673). `.env` LOCAL tinha o
  MESMO 0.55 assassino — removido. Reindex: script
  `2026_06_10_reindex_memorias_voyage4large.py` (--confirmar; re-embeda
  texto_embedado EXISTENTE, 549 linhas em PROD, dedup/content_hash intactos) —
  RODAR NO RENDER SHELL APOS O DEPLOY. ATENCAO: env de PROD deve ficar SEM
  AGENT_MEMORY_MIN_SIMILARITY (ou =0.40) apos o deploy large.
  **Item 12 do mini-set FECHADO**: dump de boot real (capturado pelo Rafael
  08:12) valida o contrato F4 em PROD — sem skill_hints/world_model; ordem
  main/tail exata com pendencias por ULTIMO; tier2/routing cortados no turno
  por overflow de blocos fixos do user 1 (rules+tier1 grandes — mesmo padrao
  user 18, refor a o cap de tier1 na F6). Listing nao aparece no dump (vive na
  description da tool Skill).
  **Skill exportando-arquivos ganhou formato `md`** (caso real da conversa
  10/06: dump .md exigiu workaround manual com risco TMPDIR): `copiar_texto`
  + `--formato md --arquivo <path>` com guard de entrega P7; SKILL.md/
  SCRIPTS.md atualizados; listing 7.971≤8.000. Drift v4.3.3→v4.4.0 no
  CLAUDE.md do agente corrigido (achado do proprio agente no dump).
  PENDENTE (curadoria, decisao agente/Rafael): user_rule "sessao N" do user 1
  e heuristica generica de roteamento — candidata a empresa/heuristicas.
- 2026-06-10 (cont.) — **A/B DO DEDUP MEDIDO** (pergunta do Rafael "migrar tudo p/
  large?"): dedup_texto real de 358 memorias, 54.461 pares doc-doc nos 2 modelos.
  Spearman 0.9155; equating quase 1:1 (0.85->0.8506); MAS overlap top-50 = 34/50 e
  as classes se SOBREPOEM na fronteira (min bloqueado 0.8116 < p99.9 nao-bloqueado
  0.8317 no large) — ~30% de discordancia sem ground truth. **VEREDITO: dedup
  permanece no lite** (gate binario != ranking; ganho zero demonstrado). Reabrir SE
  conjunto rotulado mostrar separacao melhor no large. ACHADO: 78 pares de
  quase-duplicatas RESIDENTES no estore (>=0.85 co-existindo) — candidatos ao
  memory_consolidator. Detalhe no relatorio precision_at_k_baseline (secao A/B
  DEDUP). Reindex large das 549 RODADO em PROD pelo Rafael; env removida.
- 2026-06-10 (F6 inicio) — **CAP DE TIER1/USER_RULES NO HOOK (prioridade da F6)
  IMPLEMENTADO via TDD** (14 testes novos; test_hook_budget.py 31 verdes; suite
  tests/agente completa verde). Medicao PROD pre-design (query agent_memories):
  tier1 real 6,6-9,1K/usuario ativo; resumo+contextualizacao do user.xml 1,0-1,9K;
  preferences/expertise = listas de itens 2,4-2,9K; regras mandatory 380-560c.
  BUG EXTRA descoberto na medicao: preferences.xml do user 18 tem priority=
  mandatory → entrava 2x no payload (canal L1 <user_rules> E Tier 1). E o pointer
  legado USE_USER_XML_POINTER so disparava com budget finito — NUNCA no Opus
  (budget=None), o modelo exato dos users afetados. Design: destilar/ponteirar
  (nunca cortar — intocaveis): `TIER1_PATH_CAPS` (user.xml 1500 via pointer-mode
  curado com fallback truncamento em linha / preferences 1200 / expertise 1200) +
  `USER_RULE_CHAR_CAP` 350 (`_distill_rule_content` preserva DO INTEGRAL > WHEN >
  titulo + ponteiro) + exclusao dos paths Tier 1 do canal L1 (so rows do PROPRIO
  usuario; rows empresa ficam — Tier 1 e user-scoped e nao as injeta). DESVIO
  DECLARADO vs tabela de design (600/400/400): valores eram pre-medicao; tabela
  PAD-CTX atualizada com os ENFORCED. Kill-switch `AGENT_FIXED_BLOCKS_CAP`
  (default true; exclusao da dupla injecao e incondicional — bug fix). RED
  reproduziu a evidencia tripla (cenario user-18-like: 17.943c, overflow cortava
  tier2+organicas+routing); GREEN: ≤15K e adaptativo sobrevive. PROJECAO PROD
  pos-cap (SQL, blocos fixos rules+tier1): user 18 12.391→6.746 · user 1
  10.623→5.580 · user 83 9.678→4.260 · user 55 9.194→4.260 · user 82 8.976→4.260
  · user 17 8.213→5.140 — todos os fixos ≤6,8K, sobra ≥8K p/ adaptativo no teto
  15K. REVIEW ADVERSARIAL (workflow 14 agentes, 10 findings → 3 confirmados →
  TODOS corrigidos): edge empresa na exclusao L1; teste flag-off cobria so rules
  (adicionado p/ tier1); assert de fronteira de linha fraco (endurecido); nota de
  rollback na flag. GOVERNANCA F6 JUNTO: 5 checks PAD-CTX registrados no
  pre-commit (`pre-commit-prompt-lint.sh`: (1)+(4) --check-consistency, (2)
  listing, (3) NOVO — test_hook_budget.py roda quando memory_injection*/hooks.py
  tocados, (5) checklist de admissao = item 4 NOVO do R-EXEC-5 em
  app/agente/CLAUDE.md). PENDENTE pos-deploy: validar logs [MEMORY_INJECT] PROD
  (users 1/18/82: overflow_cortes=[] e tier2>0) + mini-set.
- 2026-06-10 (F6 cont.) — **GOLDEN DATASET 15→54 NOS 6 AGENTES DO R5** (workflow
  3 fases draft→verify-adversarial→apply, 18 agentes): analista-carteira 5→9,
  auditor-financeiro 5→9, controlador-custo-frete 5→9, especialista-odoo 0→9,
  raio-x-pedido 0→9, gestor-carvia 0→9 (54 casos nos 6; 74 no total com os 20
  de gestor-motos-assai). Casos ancorados nas references reais (grounding
  verificado caso-a-caso na fase verify; privacy scrub VCD{NUM}/sem CNPJ novo)
  + linguagem calibrada em sessoes PROD. **DADO-APENAS — A3 segue aposentado**
  (veto a evals LLM agendados respeitado): nenhuma flag/scheduler/eval_runner
  tocado; baseline pass-rate do criterio R5 fica para medicao on-demand SO com
  ok explicito do Rafael. NOTA curadoria: af-01 (caso PRE-existente) contem
  CNPJ 33652456000178 — avaliar scrub retroativo.
- 2026-06-10 (F6 cont.) — **ABLACAO POR BLOCO EXECUTADA** (relatorio
  `relatorios/estudo_contexto_boot_2026-06-09/ablacao_por_bloco_2026-06-10.md`):
  payload POS-F6 reconstruido p/ os MESMOS 20 turnos reais do precision@k
  (script read-only PROD + helpers reais de destilacao) + 20 judges Sonnet
  ceticos, veredito por bloco. Resultado (% muda_resposta): tier1 destilado 95%
  (cap F6 preservou o valor com ~metade do tamanho) · recent_sessions 75% ·
  tier2 large@0.40 72% (retrieval consertado entrega) · user_rules 50% ·
  pendencias 29% · tier15 25% · routing 20% **com 2 RISCOS** (preferred_skills
  por dominio historico induz skill errada — evidencia nova p/ C5/F7.5) ·
  **operational_directives 0/20** (4,3KB/turno; organicas nao tocaram nenhum
  turno; constitucional fora do criterio turn-level — candidato a injecao por
  intent, DECISAO FUTURA gated por validacao no golden dataset). BONUS: a
  ablacao achou e consertou bug real do cap — sanitize DEPOIS do pointer
  neutralizava o wrapper legitimo <user_profile_partial> (blocklist
  anti-spoofing); fix = sanitize do conteudo BRUTO antes do cap (TDD; suite
  verde). F6 COMPLETA exceto: validacao pos-deploy em PROD (logs
  [MEMORY_INJECT] users 1/18/82 + mini-set) e fila de curadoria (requer ok).
- 2026-06-10 (F6 validacao PROD) — **CAP VALIDADO EM TRAFEGO REAL + 2o hog
  fechado**: deploy dep-d8kocrmk1jcs739ngjm0 live 15:49Z; turno real do user 18
  as 15:53Z mostrou o cap funcionando (tier1 7,6K→4,0K: user.xml 2906→1464,
  prefs 2541→1235, expertise 1349→1124; rules 6137→3451 com preferences FORA
  do canal; total 13.582 ≤15K; routing SOBREVIVEU). MAS tier2 ainda caiu no
  turno: hogs restantes = recent_sessions ~2,9K (docstring promete ~150c/
  sessao e tabela ~1,2KB — nada enforcava) + operational_directives 4,3K
  (0/20 na ablacao). FECHADO o primeiro: SESSION_RESUMO_CHAR_CAP=240 (TDD,
  3 testes; flag-gated no mesmo kill-switch). O segundo (directives por
  intent OU swap da ordem de corte tier2<->organicas — a ordem atual corta
  o bloco de 72% de utilidade antes do de 0%) = DECISAO Rafael (proposta
  registrada; mexe na politica de overflow do PAD-CTX).
