<!-- doc:meta
tipo: how-to
camada: L3
sot_de: plano de refactor e governanca do prompt do Agente Web (system_prompt + preset + injecoes)
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-04
-->

# Refactor & Governança do Prompt do Agente Web — Implementation Plan

> **Papel:** plano executável, blindado e gated, para corrigir o prompt do Agente Web
> (`preset_operacional.md` + `system_prompt.md` + injeções de runtime) e instalar a
> governança que impede o problema de voltar. Origem: avaliação de 2026-06-04.

> 🔵 **PRÓXIMA SESSÃO — RETOMAR AQUI:** FASE 1 ✅ feita (ver [Rastreamento](#rastreamento-de-execucao-append-only)).
> O próximo passo é a **FASE 0 (golden dataset + instrumentação)** — bloqueante, sem gate
> fácil. **NÃO pular para a FASE 2**: ela depende da FASE 0. O risco real é a FASE 0 (chata)
> nunca acontecer e este plano virar mais um roadmap parado. Abrir este doc e seguir o
> rastreamento; aplicar R-EXEC-1 (sem golden dataset, mudança comportamental não vai).

## Indice

- [Contexto e diagnóstico](#contexto-e-diagnostico)
- [Princípio organizador (o meta-problema)](#principio-organizador-o-meta-problema)
- [Regras de execução INVIOLÁVEIS](#regras-de-execucao-inviolaveis)
- [Premissas já verificadas nesta sessão (não refazer)](#premissas-ja-verificadas-nesta-sessao-nao-refazer)
- [FASE 0 — Instrumentação (desbloqueio)](#fase-0-instrumentacao-desbloqueio)
- [FASE 1 — Higiene factual (sem mudança comportamental)](#fase-1-higiene-factual-sem-mudanca-comportamental)
- [FASE 2 — Poda de altitude](#fase-2-poda-de-altitude)
- [FASE 3 — Robustez (destravar o que foi proposto e nunca aplicado)](#fase-3-robustez-destravar-o-que-foi-proposto-e-nunca-aplicado)
- [FASE 4 — Re-validação estratégica](#fase-4-re-validacao-estrategica)
- [FASE 5 — Governança permanente](#fase-5-governanca-permanente)
- [Mapa de dependências / o que está GATED](#mapa-de-dependencias-o-que-esta-gated)
- [Rastreamento de execução (append-only)](#rastreamento-de-execucao-append-only)
- [Fontes](#fontes)
- [Contexto](#contexto)

---

## Contexto e diagnóstico

Avaliação de 2026-06-04 (sessão Rafael + Opus 4.8) sobre o prompt que o Agente Web
recebe ao iniciar conversa. Achados factuais **medidos** (não estimados de cabeça):

| Fato | Valor medido | Fonte |
|------|--------------|-------|
| `system_prompt.md` | **862 linhas / 52.021 bytes / ~15K tok** | `wc`, Read |
| Total estático (preset+system+briefing) | **1.054 linhas / 61.468 bytes / ~17,5K tok** | `wc` |
| Documentação afirma | "~2,1K tok / ~2,7K total" | `app/agente/CLAUDE.md` |
| **Defasagem da doc** | **~6,5x** | — |
| Crescimento desde a review (abr, v4.2.0) | **407 → 862 linhas (>2x em ~6 semanas)** | `QUALITY_REVIEW.md:75` vs `wc` |
| Acreção reativa | 22 `<rule>`, 8 `<why>`, 6 "Anti-padrao", 6 refs `sessao <hex>`, 5 sub-regras (R3.1/R11.1/R11.2/R12.1/R12.2) | `grep` |
| Linguagem imperativa (só system_prompt) | NUNCA=18, NAO(caps)=29, OBRIGAT*=7, SEMPRE=5, DEVE=5, PROIBIDO=1 | `grep` |
| Erro factual | `preset_operacional.md:11` → "Knowledge cutoff: May 2025" (modelo é Opus 4.8, cutoff jan/2026) | Read |
| Duplicação | `<context_awareness>` em preset:84 **e** system_prompt:367; `<language>` em ambos; business_snapshot em system_prompt:17 **e** empresa_briefing:9 | `grep` |

O score "4,39/5 MUITO BOM, não precisa refactor" (`QUALITY_REVIEW.md:99`) avaliou um
artefato que **não existe mais**. O problema de 2026 não é falta de regra — é **excesso,
altitude errada e governança que não acompanhou o ritmo de crescimento**.

---

## Princípio organizador (o meta-problema)

> **O prompt tem processo de ADIÇÃO (todo incidente vira regra) mas nenhum processo de
> PODA. Por isso dobrou. E a energia foi para incêndio reativo (R11/R12) em vez do
> roadmap que o próprio projeto definiu e deixou parado.**

Evidência do desalinhamento (verificada nesta sessão):
- `PROMPT_INJECTION_HARDENING.md` §5.1/§5.2 **propôs** `<security_invariants>` +
  `<meta_instruction_alert>` em 2026-04-12 → **nunca aplicados** ao system_prompt.
- `ROADMAP_PROMPT_ENGINEERING_2026.md` R5 (golden dataset), R7 (context awareness — na
  verdade aplicado), R8 (memory validation), R11 (cache instrumentation) → **parados
  desde 2026-04-12**.
- No mesmo período, R11/R12/R3.1/I7 (procedimento Odoo/banco hiper-específico) **foram
  adicionados** ao prompt.

**Consequência para este plano:** ele NÃO é um roadmap novo. É a **consolidação** do que
já está planejado e parado (HARDENING §5/§8, ROADMAP R5/R6/R8/R11) + o **delta novo**
(higiene factual + poda de altitude + governança), com gates de disciplina. Criar um
terceiro roadmap paralelo seria repetir o erro.

**Arquitetura-alvo (a régua):** 3 camadas por volatilidade × altitude.
- **Camada 0 (system prompt, estático):** identidade + constituição + regras de negócio
  como PRINCÍPIO + routing de alto nível. Toda linha passa em "remover causa erro?".
- **Camada 1 (skills/refs/hook, sob demanda):** procedimento hiper-específico + enforcement
  determinístico. R11.x/R12.x/R3.1 pertencem aqui.
- **Camada 2 (injeção por turno):** memórias/diretrizes com TETO em todos os modelos,
  ordenadas estável→volátil, contrato prompt↔código testado.

---

## Regras de execução INVIOLÁVEIS

Estas regras blindam a execução contra pressa, contra "seguir na risca cego" e contra
auto-engano. Valem para QUALQUER sessão que executar este plano.

- **R-EXEC-1 — Golden dataset antes/depois para TODA mudança comportamental.**
  Higiene factual (FASE 1) é isenta (não muda comportamento). Tudo o mais é GATED.
  Repetir `ROADMAP:111` (aplicar sem eval, "risco aceito") é **proibido**.
  Base: `STUDY` PM-2.1, PM-4; `ROADMAP` princípio 1.

- **R-EXEC-2 — 1 commit por task; feature flag quando toca comportamento; rollback
  documentado na própria task.** Sem `[skip render]` (regra global). Flag pronta antes
  de mergear.

- **R-EXEC-3 — Verificar a premissa ANTES de executar cada task.** Lição desta sessão:
  a recomendação original "mover R11 para skill" estava errada porque a premissa (quem
  executa Odoo-write) não foi checada. Se a premissa de uma task falhar → a task vira
  **verificação**, não execução. Não seguir este plano "na risca" sem re-checar.

- **R-EXEC-4 — Não confiar em auto-avaliação.** `STUDY` RT-8.4: self-critique do mesmo
  modelo é teatro (mesmo viés). Gate de cada fase = **métrica objetiva** (golden dataset,
  tokens, cache, test vectors) **+ OK explícito do Rafael** nos checkpoints marcados 🔴.

- **R-EXEC-5 — Toda regra nova ou mantida no prompt passa em 2 testes:**
  (a) "é princípio (Camada 0) ou procedimento (Camada 1)?" — procedimento sai do prompt;
  (b) "remover causa erro mensurável?" (`STUDY` A-pruning / P1) — se não, corta.

- **R-EXEC-6 — Re-medir o tamanho real após cada fase e atualizar a doc auto-medida.**
  Nunca hardcode de tamanho. A defasagem de 6,5x existiu porque o número era manual.

---

## Premissas já verificadas nesta sessão (não refazer)

Registro para a próxima sessão não gastar turno re-descobrindo:

- ✅ **Tamanho real** medido por `wc` (ver tabela de diagnóstico). Não confiar no CLAUDE.md.
- ✅ **G1 — quem opera Odoo-write:** o **agente principal** opera direto (R11/R12 são 1ª
  pessoa, `system_prompt.md:504,561`). Skills Odoo-write são deny-listed do principal
  (`skills_whitelist.py:99`). Existe **gate runtime PreToolUse** que já intercepta
  `ajustando-quant-odoo`/`transferindo-interno-odoo`/`planejando-pre-etapa-odoo`
  (`permissions.py:306-375`) com `reversibility:'irreversible'` (`917-950`) +
  `destructive_action_warning` (`847`) sob flag `USE_REVERSIBILITY_CHECK`.
  **`action_update_taxes` (R11.1) NÃO está coberto por esse gate hoje** — defesa é só o
  prompt. → FASE 2 estende o gate, depois comprime o prompt.
- ✅ **Modo de prompt:** `USE_CUSTOM_SYSTEM_PROMPT=true` → string custom
  (`client.py:1655-1674`), não preset claude_code. Escolha defensável; re-avaliar em T4.3.
- ✅ **Cache macro OK:** vars dinâmicas fora do system prompt via hook
  (`AGENT_PROMPT_CACHE_OPTIMIZATION`). Furo fino: `session_context` granularidade minuto.
- ✅ **HARDENING §5.1/§5.2 (security_invariants, meta_instruction_alert) NÃO estão no
  system_prompt** (confirmado por Read integral). São Camada-0 legítima → FASE 3.

---

## FASE 0 — Instrumentação (desbloqueio)

**Gate de tudo que é comportamental (FASES 2-4).** Sem isto, não há como cumprir R-EXEC-1.
Estes itens JÁ estão no ROADMAP e estão parados — este plano os destrava.

| Task | Ação | Critério de aceitação | Fonte |
|------|------|----------------------|-------|
| T0.1 | Expandir golden dataset (mín. viável: casos de routing PRE/POS, confirmação R3, Odoo-write R11/R12, output I2/I7, idioma PT-BR) | ≥ 30 casos cobrindo as regras que FASES 2-4 tocam; pass-rate baseline documentado | ROADMAP R5 |
| T0.2 | Instrumentar token breakdown + cache hit rate em `agent_sessions.data` | `cache_read/input/output` persistidos; cache hit rate calculável por sessão | ROADMAP R11 |
| T0.3 | Baseline ANTES: rodar golden dataset + medir tokens/turn, custo/msg, cache hit, latência p95 | Números congelados num snapshot datado | ROADMAP métricas |

**Checkpoint 0** 🔴 (Rafael): baseline existe e é confiável? Se não, FASES 2-4 ficam
bloqueadas (e isso é correto — não furar R-EXEC-1). FASE 1 segue independente.

---

## FASE 1 — Higiene factual (sem mudança comportamental)

**Isenta de golden dataset (R-EXEC-1).** Corrige erro factual, ruído e duplicação. Risco
baixo, ROI alto. Pode ir em paralelo à FASE 0.

| Task | Ação | Arquivo:linha | Critério | Rollback |
|------|------|---------------|----------|----------|
| T1.1 | Corrigir cutoff factual | `preset_operacional.md:11` "May 2025" → cutoff real do modelo vigente (ou remover a linha — o SDK já informa) | linha corrigida; grep não acha "May 2025" | git revert |
| T1.2 | Deduplicar preset↔system_prompt: decidir **dono único** de `context_awareness` (preset:84 vs sp:367), `language` (preset:3 vs sp:29), `communication_style`/`reversibility`/`prompt_injection` | preset + system_prompt | cada conceito em 1 lugar só; preset vira exclusivo (só o que sp NÃO diz) | git revert |
| T1.3 | Remover `business_snapshot` duplicado | `system_prompt.md:17-21` (mantém) vs `empresa_briefing.md:9` OU vice-versa | info aparece 1x no bloco estático | git revert |
| T1.4 | Doc de arquitetura com tamanho REAL **auto-medido** + script de medição | `app/agente/CLAUDE.md` seção "Arquitetura de Prompts" | número bate com `wc`; script reproduzível | git revert |

**Checkpoint 1:** `ET.fromstring` (XML parse) OK; smoke test de boot do agente; diff
revisado linha a linha. Sem regressão de conteúdo (só remoção de duplicata/erro).

---

## FASE 2 — Poda de altitude

**COMPORTAMENTAL → gated por FASE 0.** Tira procedimento da Camada 0, mas **sem remover
defesa** — primeiro garante a defesa determinística (R-EXEC-3).

| Task | Ação | Detalhe | Critério |
|------|------|---------|----------|
| T2.1 | **Estender o gate runtime PreToolUse** para cobrir as operações de R11.1 (`action_update_taxes` em SO faturado) e R12.1 (UPDATE/DELETE em massa via Bash/SQL) | `permissions.py` (espelhar o padrão `306-375` + `917-950`) | a operação perigosa dispara `destructive_action_warning`/bloqueio **independente do prompt** |
| T2.2 | **Só após T2.1 verde:** comprimir R3.1, R11/R11.1/R11.2, R12.1/R12.2, I7 no prompt — manter **princípio + gatilho** (3-5 linhas); mover detalhe de implementação (`onchange_l10n_br_calcular_imposto`, wizard validade, location 32) + pós-mortems (`sessao <hex>`) para `GOTCHAS.md` / reference de incidentes | `system_prompt.md:253-269, 502-595, 625-665` → `.claude/references/odoo/GOTCHAS.md` (R11.1 já aponta lá em `:528`) | princípio preservado; detalhe fora do prompt global; pós-mortem em reference dev |
| T2.3 | Re-medir tamanho (R-EXEC-6) + golden dataset DEPOIS | — | tamanho caiu (alvo −150 a −250 linhas); zero regressão em confirmação/Odoo/escrita |

**Checkpoint 2** 🔴 (Rafael): golden dataset não regride nas regras tocadas E o agente
ainda recusa/confirma corretamente operações Odoo-write faturadas (teste manual dos
cenários das sessões `4722693c`, `26d43e5f`). Sem isso, **não mergear** — rollback flag.

---

## FASE 3 — Robustez (destravar o que foi proposto e nunca aplicado)

**COMPORTAMENTAL → gated por FASE 0.** Aplica o que o HARDENING/ROADMAP já especificou.

| Task | Ação | Fonte | Critério |
|------|------|-------|----------|
| T3.1 | Adicionar `<security_invariants>` + `<meta_instruction_alert>` ao system_prompt (Camada 0 legítima) | `HARDENING §5.1/§5.2` | blocos presentes; test vectors `HARDENING §11` (direct/meta-instruction/scope) passam |
| T3.2 | Memory injection validation: XML escape + blocklist de tags em `memory_injection.py` (não só no save) | `ROADMAP R8` + `HARDENING §8.1/§8.3` | memória com `<system>...` é escapada/rejeitada na injeção; teste adversarial RAG passa |
| T3.3 | `session_context`: reduzir granularidade temporal (minuto → período do dia/hora) + medir efeito | `hooks.py` (session_context) | referência temporal ainda resolve "hoje/amanhã"; variação por-turno reduzida |
| T3.4 | Budget de injeção: **MEDIR** se ilimitado-no-Opus dilui (lost-in-the-middle) ANTES de capar | `memory_injection.py` (Tier 2 budget) | decisão baseada em medição; só capar se houver dano mensurável (R-EXEC-3) |

**Checkpoint 3:** test vectors `HARDENING §11` passam; golden dataset estável; R3b
(XML escape de `user_name`, `ROADMAP R3b`) fechado junto se barato.

---

## FASE 4 — Re-validação estratégica

**Alto risco → gated por FASE 0 + Rafael.** Decisões tomadas sob Opus 4.6 que merecem
re-exame sob Opus 4.8 (mais literal). Nenhuma em lote (PM-2.1).

| Task | Ação | Cuidado | Fonte |
|------|------|---------|-------|
| T4.1 | Re-validar linguagem imperativa (65 imperativos) sob Opus 4.8 | dial-back **individual** com golden dataset, NÃO em lote; manter safety L1/L3 negativo (RT-5.1) | ROADMAP R1 (era 4.6) |
| T4.2 | Adaptive thinking p/ decisões críticas (P1-P7, Odoo-write) | flag `USE_ADAPTIVE_THINKING` + rollout 1→5→all; medir latência/custo | ROADMAP R6 |
| T4.3 | Re-avaliar custom string vs `preset:"claude_code" + append + excludeDynamicSections` | POC comparativo; preset evolui e a versão artesanal apodrece (FASE 1 provou) | §2 da avaliação |

**Checkpoint 4** 🔴 (Rafael): cada decisão documentada com a medição que a sustenta.
Nenhuma mudança sem evidência. Reverter qualquer item que regrida o golden dataset.

---

## FASE 5 — Governança permanente

**O que impede o problema de voltar.** Sem isto, qualquer poda volta a inchar em 2 meses.

| Task | Ação | Critério |
|------|------|----------|
| T5.1 | Gatilho de poda: audit/CI que **alerta** quando `system_prompt.md` cresce > X% ou > N linhas sem poda compensatória | hook/script roda no pre-commit ou no `ui_audit`-equivalente; alerta visível |
| T5.2 | Doc de tamanho **auto-medida** (script no build/audit que reescreve o número no CLAUDE.md) | número nunca mais diverge do real |
| T5.3 | Checklist "princípio (Camada 0) vs procedimento (Camada 1)" no processo de adicionar regra | registrado em `app/agente/CLAUDE.md`; toda regra nova responde antes de entrar |
| T5.4 | Religar a cadência de review (trimestral foi prometida em `QUALITY_REVIEW:725` e não cumprida) | próxima review agendada; gatilho "editou system_prompt → re-review" |

**Checkpoint 5:** o processo existe, está documentado e tem um dono. A review trimestral
volta ao calendário.

---

## Mapa de dependências / o que está GATED

```
FASE 1 (higiene) ──────────────► pode ir JÁ (isenta de eval)
FASE 0 (instrumentação) ───┐
                           ├──► FASE 2 (poda) ──► FASE 3 (robustez) ──► FASE 4 (estratégica)
                           │     (T2.1 antes de T2.2: defesa antes de remover do prompt)
FASE 5 (governança) ───────┴──► transversal; T5.1/T5.2 idealmente antes de FASE 2 fechar
```

- **Bloqueante:** FASE 0 trava FASES 2-4. Se o golden dataset não for expandido, as
  mudanças comportamentais **não acontecem** — e isso é o comportamento correto, não uma
  falha do plano.
- **Independente:** FASE 1 não depende de nada. Maior ROI imediato, risco mínimo.
- **Ordem interna crítica:** T2.1 (gate runtime) **sempre** antes de T2.2 (comprimir prompt).

---

## Rastreamento de execução (append-only)

> Atualizar com `[x]` + commit SHA conforme cada task completa. NÃO reescrever histórico.

- [ ] T0.1 golden dataset expandido — _SHA:_
- [ ] T0.2 token/cache instrumentado — _SHA:_
- [ ] T0.3 baseline ANTES congelado — _SHA:_
- [x] T1.1 cutoff "May 2025" removido (`preset_operacional.md`) — commit main 2026-06-04
- [x] T1.2 dedup — **PARCIAL**: só `<context_awareness>` (dedup limpa; dono único = `system_prompt` R6). language / communication_style / reversibility = NÃO eram dedup limpa → adiados; prompt_injection = instância única (não dup) → mantido. Ver nota FASE 1.
- [~] T1.3 business_snapshot — **ADIADO p/ FASE 2**: contém Atacadão 50% / Assai 13% (insumo de P1-P7) = comportamental, não higiene
- [x] T1.4 doc auto-medida + `scripts/audits/prompt_size_audit.py` — commit main 2026-06-04
- [ ] T2.1 gate runtime estendido — _SHA:_
- [ ] T2.2 prompt comprimido (princípio fica, detalhe sai) — _SHA:_
- [ ] T2.3 re-medição + golden DEPOIS — _SHA:_
- [ ] T3.1 security_invariants + meta_instruction_alert — _SHA:_
- [ ] T3.2 memory injection validation — _SHA:_
- [ ] T3.3 session_context granularidade — _SHA:_
- [ ] T3.4 budget injeção medido — _SHA:_
- [ ] T4.1 imperativos re-validados sob 4.8 — _SHA:_
- [ ] T4.2 adaptive thinking — _SHA:_
- [ ] T4.3 custom vs preset+append — _SHA:_
- [ ] T5.1 gatilho de poda — _SHA:_
- [ ] T5.2 doc auto-medida — _SHA:_
- [ ] T5.3 checklist princípio/procedimento — _SHA:_
- [ ] T5.4 cadência de review religada — _SHA:_

**Checkpoints (gates):** C0 🔴 → C1 → C2 🔴 → C3 → C4 🔴 → C5. 🔴 = exige OK do Rafael.

### Nota de execução — FASE 1 (2026-06-04)

A execução com rigor (R-EXEC-3) **encolheu a FASE 1** vs o plano original — disciplina
funcionando, não desvio:
- **Feito (zero risco comportamental):** T1.1 (cutoff factual), T1.2-`context_awareness`
  (dedup literal; equivalência preservada em `system_prompt` R6 + instrução de salvar
  antes da compactação intacta), T1.4 (doc auto-medida + `prompt_size_audit.py`).
- **Adiado p/ fase comportamental (com golden dataset):** T1.3 business_snapshot e
  T1.2-language tocam P1-P7 / idioma (#787) — não são higiene.
- **Não era duplicação:** prompt_injection está só no preset (instância única);
  communication_style/reversibility = sobreposição complementar, não dup limpa.
- **Correção do Checkpoint 1:** o critério "XML parse OK" era **premissa falsa** — os
  prompts nunca foram XML estrito (loader lê como texto puro; `system_prompt.md` intocado
  também falha `ET.fromstring`). Critério corrigido: **balanço de tags de bloco + smoke
  loader** (preset = zero desbalanço; 3 arquivos concatenam OK).
- **Tamanho pós-FASE 1:** 1.046 linhas / ~17,5K tok (preset 111→103 linhas).

---

## Fontes

- `app/agente/prompts/system_prompt.md` v4.3.3 (862 linhas — Read integral)
- `app/agente/prompts/preset_operacional.md` v2.0.0 (111 linhas — Read integral)
- `app/agente/config/empresa_briefing.md` (81 linhas — Read integral)
- `app/agente/sdk/client.py:1655-1674` (modo custom), `permissions.py:306-375,847,917-950` (gate runtime)
- `app/agente/config/skills_whitelist.py:99` (deny-list)
- `.claude/references/STUDY_PROMPT_ENGINEERING_2026.md` (red team RT-1..14, pre-mortem PM-1..2.7, gaps)
- `.claude/references/STUDY_PROMPT_ENGINEERING_2026_QUALITY_REVIEW.md` (review v4.2.0, score 4,39/5)
- `.claude/references/ROADMAP_PROMPT_ENGINEERING_2026.md` (R1-R17, status)
- `.claude/references/PROMPT_INJECTION_HARDENING.md` (§5.1/§5.2/§8 propostos, não aplicados)
- `/tmp/subagent-findings/anthropic_best_practices.md` (pesquisa Anthropic 2026, URLs)
- `/tmp/subagent-findings/runtime_injections.md` (mapa das 10 injeções)

## Contexto

Plano nascido da avaliação 2026-06-04. A avaliação cumpriu R-EXEC-3 sobre si mesma:
2 recomendações iniciais (G1 "mover para skill", G4 "capar budget Opus") foram corrigidas
após verificação de premissa. Este plano consolida — não duplica — o roadmap de prompt
engineering existente (parado desde 2026-04-12) e adiciona o delta pós-abril + governança.
