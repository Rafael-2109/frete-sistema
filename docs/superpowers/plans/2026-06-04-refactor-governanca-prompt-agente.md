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

> 🔵 **PRÓXIMA SESSÃO — RETOMAR AQUI:** **FASES 0, 1, 2 e 5 FECHADAS** (em PROD; ver
> [Nota FASE 2](#nota-de-execucao-fase-2-2026-06-05) + [Rastreamento](#rastreamento-de-execucao-append-only)).
> FASE 2: gate `action_update_taxes` em código (T2.1, `8954563fe`) + poda de altitude `system_prompt`
> 858→765 (−93L; T2.2 `1c60d0bfe` + correção `fee8f1f17`). **Lição (após ler as FONTES STUDY+QUALITY_REVIEW):**
> a meta NÃO é tamanho (STUDY #7: Anthropic não segue "short prompts"; QUALITY_REVIEW: ROI de enxugar
> BAIXO) — é **altitude** (procedimento→Camada 1) preservando forças (os `<why>` = A2 Top Strength 5/5).
> **Frente PARALELA escolhida (2026-06-05):** próxima sessão = **T4.3** (POC custom-string vs `preset:"claude_code"`+append, zona `client.py` isolada — escopo/premissa na linha T4.3 do rastreamento). FASE 5 roda em outra sessão simultânea (zona `scripts/audits/`+`CLAUDE.md`). **Decisão ainda aberta:** expandir altitude p/ R0/routing (só se a altitude justificar, não o número).
> **T0.2 RESOLVIDO** (`dadf7f1ba`+`95421b1b6`): o custo SEMPRE esteve em `agent_sessions.total_cost_usd`
> (coluna; 55/56 sessões/7d = $533,76); `agent_session_costs` (2ª via, breakdown de cache) ficava vazia
> porque `record_cost` persistia via SAVEPOINT SEM commit no loop de streaming — movido p/
> `_persist_session_cost` em `_save_messages_to_db` (context que commita). Diagnóstico "flag OFF" estava ERRADO.
> FASE 3: **T3.1 (robustez no PRESET, `785298a97`) + T3.2 (RAG injection — buraco `<system-reminder>`,
> `c616916ac`) FEITAS.** Falta: **T3.3** (`session_context` granularidade minuto — pode ser no-op, é
> additionalContext fora do cache; medir antes), **T3.4** (budget de injeção Opus ilimitado — MEDIR
> lost-in-the-middle antes de capar), **T3.1 test vectors §11** (Rafael faz no agente web).
> Princípios desta linha (NÃO reabrir): refactor **NÃO usa LLM eval** — prova **determinística**
> (pytest do gate + `prompt_size_audit` + smoke); **hipótese barata primeiro**; **verificar a
> premissa de cada task** (R-EXEC-3).

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

- [x] T0.1 matriz de provas determinísticas (task → critério pytest/medição) — DEFINIDA na Nota FASE 0; golden dataset LLM descartado. Refinar por-task no início da FASE 2.
- [x] T0.2 instrumentação — **RESOLVIDO 2026-06-05** (commits main `7824e39c8`): causa = flag `AGENT_COST_TRACKER_PERSIST` OFF (H1). H3 "savepoint órfão" REFUTADO por TDD (commit-on-teardown `app/__init__.py:1415` salva o `begin_nested()`). Flag LIGADA em PROD (`update_environment_variables`) + deploy `dep-d8h4i2d8nd3s73brctsg`. Regressão travada (`tests/agente/sdk/test_cost_tracker_persist.py`, 3 verdes). ⚠️ **1º ato da próxima sessão: confirmar que `agent_session_costs` está populando** (fecha H1 empírico + dá custo/cache do T0.3).
  - **⛔ CORREÇÃO FINAL 2026-06-05** (após o Rafael perguntar se não era duplicação de local — o diagnóstico acima estava ERRADO): (1) o custo NUNCA esteve perdido — sempre gravado em `agent_sessions.total_cost_usd` (coluna; 55/56 sessões/7d = **$533,76**, via `_save_messages_to_db` que commita). `agent_session_costs` é uma **2ª via per-message** (breakdown de cache). (2) A flag tem default `true` → "flag OFF" (H1) era falso e ligá-la não populou. (3) **Causa raiz REAL** = H3 estava certo na essência: `record_cost._persist_to_db` usava `begin_nested()` (SAVEPOINT) **SEM commit**, no app_context do loop de streaming que **não consolida** o savepoint (o TDD do `7824e39c8` mascarou usando um `with app.app_context()` limpo, que commita no teardown). **Fix (`dadf7f1ba` + `95421b1b6`):** persistência movida para `_persist_session_cost`, chamado em `_save_messages_to_db` (context que commita, junto de `total_cost_usd`); via deprecada `_persist_to_db` + seu teste removidos; novo `tests/agente/sdk/test_cost_persist_fix.py` (reprodução da causa + persistência + idempotência + flag OFF). Regressão: 211 verdes em `tests/agente/sdk/`.
- [~] T0.3 baseline OBJETIVO: **tamanho congelado = 1036 linhas / ~17,4K tok** (`prompt_size_audit`, pós-dedup FASE 1) + rodar suíte pytest do agente (verde) no início da FASE 2; custo/cache de produção vem de `agent_session_costs` (pós-validação T0.2).
- [x] T1.1 cutoff "May 2025" removido (`preset_operacional.md`) — commit main 2026-06-04
- [x] T1.2 dedup — `<context_awareness>` (dono=`system_prompt` R6) + **`<language>` do preset removido 2026-06-05**: dono único = `<language_policy>` no `system_prompt` (superset anti-drift #787). Verificação corrigiu a avaliação conservadora da FASE 1 — o preset `<language>` ERA subconjunto literal, dedup limpa. communication_style/reversibility = sobreposição complementar (mantidos); prompt_injection = instância única. — commit main 2026-06-05
- [x] T1.3 business_snapshot — **FEITO 2026-06-05 como dedup limpa** (NÃO comportamental — premissa do "adiado" estava errada): `empresa_briefing` JÁ é injetado no prompt (`client.py:506-541`) e contém os mesmos dados (50%/13%/R$16MM/~500 ped/gargalos) + detalhe único + serve o `pattern_analyzer`. Removido `<business_snapshot>` do `system_prompt`; dono único = briefing. Info 100% preservada (smoke + diff). — commit main 2026-06-05
- [x] T1.4 doc auto-medida + `scripts/audits/prompt_size_audit.py` — commit main 2026-06-04
- [x] T2.1 gate runtime estendido — **`action_update_taxes` (R11.1) bloqueado UNIVERSAL** (deny via Bash/Write/Edit + marcador de execução RPC), flag `USE_ODOO_TAX_GATE` default ON; 10 testes TDD; 63 verdes na suíte do gate. R12.1 (UPDATE/DELETE massa) segue só avisando (decisão Rafael). _SHA: 8954563fe_
- [x] T2.2 prompt comprimido (princípio fica, detalhe sai) — **858→750 linhas (−108L / ~14.9K→~13.0K tok)**: R3.1→`REGRAS_MODELOS.md`, R11.2→`GOTCHAS.md`, I7→`REGRAS_OUTPUT.md`; R11(3-riscos)/R12 enxugados in-place; 7 pós-mortems `sessao <hex>` removidos; smoke 11/11 (princípio no prompt + procedimento na ref). _SHA: 1c60d0bfe_
- [~] T2.3 re-medição (prova determinística, sem LLM): **765L / ~13.3K tok** (TOTAL estático 1036→943 / ~15.8K), balanço de tags OK, regressão verde. **Reposicionamento (após ler as FONTES — STUDY + QUALITY_REVIEW, que NÃO haviam sido lidas antes da T2.2):** o alvo "−150/−250 linhas" é métrica de baixo valor — STUDY insight #7 (Anthropic NÃO segue "short prompts"; prompt vazado ~200K tok, redundância intencional) + QUALITY_REVIEW ("ROI de enxugamento BAIXO; tokens baratos via cache"). A meta REAL é **altitude** (procedimento→Camada 1), cumprida. Os `<why>` (A2 = Top Strength 5/5) foram cortados na 1ª tentativa (perseguindo o número) e **restaurados** em `fee8f1f17`. Resultado final **−93L** vindo SÓ de altitude.
- [x] T3.1 security_invariants + meta_instruction_alert — **no PRESET, não no SP** (decisão arquitetural Anthropic-best-practice: o preset é dono de safety/injection e já tinha `<prompt_injection>`/`<tool_results>`; o SP não tinha NADA de injection → pôr no SP criaria drift). Consolida a defesa de injection (resolve a duplicação interna `tool_results`↔`prompt_injection`) + meta-instruction §5.2; invariants de negócio R3/R4/`<scope>` **referenciados, não duplicados**. preset 97→117L; smoke 8/8; regressão 15 verdes. Test vectors §11 = spot-check manual pendente (exige rodar o agente). _SHA: 785298a97_
- [x] T3.2 memory injection validation — **escape-na-injeção já existia (G4, 4 tiers de `_load_user_memories_for_context`); fechado o BURACO `<system-reminder>`** (vazava CRU — `_SUSPICIOUS_TAGS` tinha 'system' mas não a variante com hífen; o `(?:\s[^>]*)?/?>` funciona como word-boundary e o hífen quebrava o match) + teste adversarial (11 casos). Fortalece `sanitize_memory_content` (RAG) E `sanitize_user_input` (/api/chat). 35 verdes, 0 regressão. _SHA: c616916ac_
- [ ] T3.3 session_context granularidade — _SHA:_
- [ ] T3.4 budget injeção medido — _SHA:_
- [ ] T4.1 imperativos re-validados sob 4.8 — _SHA:_
- [ ] T4.2 adaptive thinking — _SHA:_
- [ ] T4.3 custom vs preset+append — **🟢 PRÓXIMA SESSÃO PARALELA (decisão Rafael 2026-06-05; a FASE 5 roda em outra sessão simultânea).** Zona `client.py` / `feature_flags.py` **ISOLADA** — não toca `system_prompt`/`preset`/`CLAUDE.md` nem os arquivos da FASE 5. **Escopo:** POC determinístico comparando o modo atual (`USE_CUSTOM_SYSTEM_PROMPT=true` → string custom em `_build_full_system_prompt`, `client.py:1655-1674`) vs `preset:"claude_code" + append + excludeDynamicSections`. **Premissa a verificar 1º (R-EXEC-3):** o preset `claude_code` do SDK 0.2.89 ainda existe e o que ele injeta hoje (tom/tools/safety) — a string custom "apodrece" porque o preset evolui (a FASE 1 já provou drift). **Critério:** medir tamanho/tokens + cache-prefix + DIFF do que cada modo injeta; **SEM LLM eval** (prova determinística + spot-check). **Coordenação:** editar SÓ esta linha do rastreamento e rebase no push (a FASE 5 também edita este plano). _SHA:_
- [x] T5.1 gatilho de poda — **delta-based** (`prompt_size_audit.py --check-delta` + baseline.json + hook `pre-commit-prompt-lint.sh` wired no wrapper PAD-A; bloqueia crescimento vs baseline, redução sempre passa; só dispara se o commit toca um dos 3 prompts). 11 pytest + smoke e2e do hook. _SHA: 25c1a860d_
- [x] T5.2 doc auto-medida — **bloco entre marcadores `<!-- prompt-size:start/end -->` no `app/agente/CLAUDE.md`, reescrito por `--update-claude-md`** (idempotente; números manuais defasados "~17.5K/~14.9K/103L" removidos → apontam para o bloco). _SHA: 68b190a57_
- [x] T5.3 checklist princípio/procedimento — **seção "Governança do prompt" em `app/agente/CLAUDE.md`** (R-EXEC-5: C0 vs C1; "remove causa erro?"; `<why>`=força, comprimir só procedimento). _SHA: 2b0346b30_
- [x] T5.4 cadência de review religada — **trimestral** (última v4.2.0 abr/2026; **próxima jul/2026**) + gatilho "bypass `--no-verify`/baseline subiu → re-review". Mesma seção. _SHA: 2b0346b30_

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

### Nota de execução — FASE 0 (2026-06-05)

R-EXEC-3 aplicado sobre o próprio R-EXEC-1 (a pedido do Rafael). 3 premissas do plano
original **não se sustentaram** — verificadas com fonte, não de cabeça:

- **P1 — golden dataset apontava para o alvo errado.** T0.1 dizia "expandir ROADMAP R5"
  (`.claude/evals/subagents/`), mas esse dataset roda **subagentes** via `claude -p --agent`
  (`eval_runner.py:77-88`) — NÃO passa pelo `system_prompt.md` que este refactor edita.
  Quem exercita o system_prompt do **Agente Web** é `tests/agent_evals/run_evals.py`
  (`:268` → `POST /agente/api/chat`).
- **P2 — cobertura insuficiente.** As 20 tasks de `tests/agent_evals/tasks.json` cobrem
  consulta/rastreamento/análise/memória/segurança, mas NÃO confirmação R3, Odoo-write
  R11/R12, routing PRE/POS nem idioma PT-BR (as regras que a FASE 2 comprime).
- **P3 — T0.2 não é "instrumentar do zero" (ROADMAP R11 vencido).** `cost_tracker.py` já
  calcula breakdown de cache + `cache_hit_rate()` (G2, 2026-04-15, depois do baseline de
  abril); `agent_session_costs` existe com schema completo; `insights.py` o expõe. MAS a
  tabela está **VAZIA em PROD** (0 linhas, verificado via MCP Render) → T0.2 vira
  "investigar por que + ligar + validar".

**Decisão estruturante (Rafael, 2026-06-05):** o refactor do system_prompt **NÃO depende de
LLM eval** ("custou fortuna e nada foi conclusivo"). A intenção de R-EXEC-1 ("não mudar
comportamento às cegas") permanece inviolável; o **instrumento** muda de "golden dataset LLM
antes/depois" para **prova determinística**:
- **FASE 2:** T2.1 (gate runtime `permissions.py`) testável por pytest; a ordem T2.1→T2.2
  faz a *segurança* virar código ANTES de o texto sair do prompt → poda provada por "pytest
  do gate verde + diff revisado + tamanho caiu (`prompt_size_audit.py`)".
- **FASE 3:** T3.2/T3.3 são código (pytest: escape/blocklist em `memory_injection.py`,
  granularidade em `hooks.py`); T3.1 = presença por grep + spot-check manual de 2-3 vetores
  `HARDENING §11`.
- **FASE 4:** T4.1 = revisão manual dos ~7 soft candidates (R1 audit `ROADMAP:200-232` já
  fez o pesado: 94% são safety L1/L3); T4.2 = métrica de produção (`agent_session_costs`).

**FASE 0 reenquadrada:** T0.1 → matriz de provas determinísticas (não casos LLM);
T0.2 → ligar a instrumentação de custo (diagnóstico em andamento); T0.3 → baseline objetivo
(tamanho + suíte pytest verde + custo/cache de produção). Efeito colateral bom: a FASE 0
deixa de ser "geração de casos LLM chata que nunca acontece" e vira "ligar instrumentação +
escrever a matriz" — o risco de virar roadmap parado encolhe.

**Resíduo não-determinístico assumido** (idioma PT-BR, qualidade do routing conversacional,
"pedir confirmação proativamente"): tratado por **spot-check manual pontual** (ler 2-3
saídas), NÃO framework LLM. A *segurança* desse resíduo está no gate (T2.1), não no
comportamento conversacional probabilístico.

**Diagnóstico T0.2 — causa raiz (2026-06-05, CORRIGIDO via TDD):** o cálculo de custo FUNCIONA
(logs PROD: dezenas de `[COST_TRACKER] Registrado` com `cache_read/cache_write/hit_rate`), mas
`agent_session_costs` está vazia desde a migration (2026-05-09). **Causa real = a flag
`AGENT_COST_TRACKER_PERSIST` está OFF em PROD (H1)** — `_persist_to_db` nunca é chamado.
A 1ª hipótese ("savepoint órfão na thread daemon", H3) foi **REFUTADA pelo TDD**: o projeto tem
**commit-on-teardown** (`app/__init__.py:1404-1415` — `@app.teardown_appcontext` faz
`db.session.commit()` quando não há exceção), que consolida o `begin_nested()` do `insert_entry` no
fim de QUALQUER `app_context`, inclusive o manual da thread daemon (`chat.py:483`). Teste + experimento
direto provam que o código persiste com a flag ON (`flush` sem commit explícito persiste; `rollback`
explícito reverte). O contraste `agent_invocation_metrics`=69 vs cost=0 NÃO indica "falta commit" —
indica **flags diferentes**: a telemetria A1 tem flag própria ON (`AGENT_INVOCATION_METRICS_PERSIST`),
o cost tem `AGENT_COST_TRACKER_PERSIST` OFF. **Lição (R-EXEC-3):** o diagnóstico por leitura de código
parecia sólido mas ignorou o commit-on-teardown global; só o TDD pegou — exatamente por isso a régua
exige prova, não inferência. **Fix real:** ligar `AGENT_COST_TRACKER_PERSIST=true` no Render (env +
deploy), não mudar código. Regressão travada em `tests/agente/sdk/test_cost_tracker_persist.py` (3 verdes).

**Premissa a verificar em T2.1 (não antes):** o gate runtime cobre 100% do que R11/R12
defendem? `action_update_taxes` (R11.1) hoje NÃO está coberto (`:136`); UPDATE/DELETE em
massa via `Bash`/SQL pode não ser interceptável como as tools Odoo nomeadas. Trecho que só o
prompt protege NÃO pode ser podado (T2.2) sem defesa equivalente — senão é "fazer pela metade".

### Nota de execução — FASE 2 (2026-06-05)

T2.1 → T2.2 → T2.3 na ordem inviolável (defesa em código ANTES de podar o prompt). Em PROD (main).

- **T2.1 (gate) — premissa confirmada:** `action_update_taxes` NÃO existe no codebase; o agente o
  executa via script Python ad-hoc (`execute_kw`) rodado por Bash OU escrito em /tmp. Logo o gate
  (`_classify_odoo_tax_gate`) intercepta pelo CONTEÚDO (Bash.command / Write.content / Edit.new_string
  + marcador RPC) e roda ANTES dos early-returns de /tmp do Write/Edit (senão o vetor "escreve script
  + roda" ficaria descoberto). Deny UNIVERSAL (sem allowlist — decisão Rafael). Best-effort
  (evasível por string dinâmica) → princípio R11.1 PERMANECE no prompt. R12.1 ficou só avisando.

- **T2.2 (poda):** 1ª tentativa foi conservadora demais (−34L, só pós-mortem + `<why>`) — Rafael
  apontou como "cosmética" e fora do plano. Refeita FIEL: princípio+gatilho na Camada 0, procedimento
  na Camada 1 (R3.1→`REGRAS_MODELOS`, R11.2→`GOTCHAS`, I7→`REGRAS_OUTPUT`), 100% das regras
  comportamentais preservadas (smoke 11/11). Resultado **−108L**.

- **Reposicionamento da meta (R-EXEC-6, após ler as FONTES):** eu NÃO havia lido `STUDY` /
  `QUALITY_REVIEW` antes da T2.2 e tratei "−150/−250 linhas" como o objetivo — erro apontado pelo
  Rafael. As fontes corrigem: **tamanho NÃO é a meta** (STUDY insight #7: prompt Anthropic ~200K tok
  com redundância intencional; QUALITY_REVIEW: "ROI de enxugamento BAIXO, tokens baratos via cache").
  A meta da FASE 2 é **altitude** — procedimento hiper-específico → Camada 1 (progressive disclosure)
  — **preservando as forças**, em especial os `<why>` (A2 = Top Strength 5/5, "explicar o porquê
  melhora instruction following"). 1ª tentativa cortou os `<why>` (degradou força → erro); corrigido
  em `fee8f1f17`. Resultado **−93L** vindo SÓ de altitude. **Lição p/ FASE 3+: comprimir só onde for
  PROCEDIMENTO, nunca motivação; não perseguir contagem de linhas.** Expandir para R0/routing só se a
  altitude (não o número) justificar.

- **Pendência T0.2 / `agent_session_costs` (não bloqueia a FASE 2):** o 1º ato da sessão (confirmar que
  a tabela populou) FALHOU — VAZIA com 11 sessões/48h (última pós-deploy). Como `feature_flags.py:794`
  tem default `true`, o diagnóstico H1 ("flag OFF") é DUVIDOSO (igual ao H3 que ele refutou). Suspeita
  não confirmada: `record_cost` (`chat.py:978`, handler do `done`) não alcançado no path persistente de
  PROD. NÃO investigado a fundo (decisão Rafael: seguir FASE 2). Retomar isto antes de confiar em
  custo/cache de produção.

### Nota de execução — FASE 3 / T3.1 (2026-06-05)

Gatilho: o Rafael perguntou (a) se as duplicidades do preset foram resolvidas e (b) se a robustez vai
no system_prompt ou no preset. Autorizou "fazer o melhor pelas best practices Anthropic".

- **Decisão (T3.1) — robustez no PRESET, não no SP.** O HARDENING §5 e a tabela da T3.1 diziam
  "system_prompt", mas o HARDENING usa "system_prompt" como sinônimo de "Camada 0 estática" (preset+SP
  são concatenados) e foi escrito sem considerar o preset. Verificado: a defesa de injection JÁ vive no
  preset (`<safety><prompt_injection>` + `<tool_results>`); o SP não tem nada de injection (grep vazio).
  Pôr no SP duplicaria a defesa em 2 arquivos (drift). Por separação de responsabilidades (preset =
  safety/awareness; SP = comportamento/negócio), `<security_invariants>` + meta-instruction foram para o
  **preset**, e os invariants de negócio (R3/R4/scope) são **referenciados**, não duplicados.

- **Duplicidades do preset — status real (verificado):** ✅ resolvidas na FASE 1 (`language`,
  `context_awareness`, `data_integrity`) + ✅ agora a duplicação interna de injection (`tool_results`↔
  `prompt_injection`). ⚠️ **Permanecem (decisão: deixar — complementares, ROI baixo per QUALITY_REVIEW
  "ROI de enxugamento BAIXO"):** `<communication_style>` (preset) ↔ R1 (SP); `<safety><reversibility>`
  (preset) ↔ R3/L1 (SP); `<environment>` (preset, factual+TZ) ↔ `<environment>` (SP, motivação). São
  facetas complementares (awareness vs regra/motivação), não drift factual — não justificam mexer.

- **FASE 3 — próximos passos (premissas JÁ verificadas nesta sessão, R-EXEC-3):**
  - **T3.2 ✅ FEITO** (`c616916ac`): buraco `<system-reminder>` na sanitização de memória + teste
    adversarial. O escape-na-injeção já existia (G4); a entrega foi fechar o vazamento + travar com teste.
  - **T3.3 — `session_context` granularidade (`hooks.py:1369`).** Hoje
    `data_hora = strftime("%d/%m/%Y %H:%M")` → granularidade **minuto**. ⚠️ **Premissa a confirmar ANTES
    de mexer:** o `session_context` é injetado via hook UserPromptSubmit como **`additionalContext` (nas
    messages), NÃO no `system_prompt` estático** — logo a variação por-minuto **não invalida o cache do
    system prompt** (que já é estável). Ganho de reduzir p/ hora/período pode ser ~zero. AÇÃO: medir o
    impacto real de cache (depende de `agent_session_costs` popular — ligado à pendência T0.2) ANTES de
    reduzir; só mexer se houver dano mensurável. **Pode ser um no-op** (como o T0.2).
  - **T3.4 — budget de injeção Tier 2 (`memory_injection.py:1079`).** Confirmado: no Opus,
    "sem limite (1M context) — injetar TODAS as memórias retornadas" (`budget=None`). AÇÃO: **MEDIR** se
    isso dilui (lost-in-the-middle) ANTES de capar — decisão por evidência, não a priori. Sem framework
    LLM (veto Rafael): comparar `step_quality`/judge entre sessões com muitas vs poucas memórias, ou
    spot-check manual. Só capar se houver dano mensurável.
  - **T3.1 test vectors §11** (direct/meta-instruction/scope): **Rafael faz com o agente web** (exige
    rodar o chat; não executável daqui).

### Nota de execução — FASE 5 (2026-06-06)

Sessão da FASE 5 (zona `scripts/audits/` + `app/agente/CLAUDE.md`), paralela à T4.3
(zona `client.py`, isolada — sem colisão de arquivos). Toda a fase é **dev-tooling +
doc**: zero DDL, zero runtime do agente, zero PROD; reversível por `git revert`.

- **1º ato (confirmação empírica do estado, R-EXEC-3):** a pendência T0.2 do handoff já
  estava **fechada** pelo Rafael (`dadf7f1ba`+`95421b1b6`+`8f3a86d32`). Verifiquei via MCP
  Render: `agent_session_costs` **popula** (7 registros com `model`+`cache_read`; `recorded_at`
  confirmado UTC pelo epoch do `message_id`); o fix `dadf7f1ba` está **live** (deploy
  `dep-d8hkdd5ckfvc73fqggf0`, 22:06 UTC 05/06) mas **sem tráfego desde 19:51 UTC** → "0 custos
  pós-deploy" = falta de uso, **não regressão**. Cleanup do teste obsoleto: o Rafael já o
  removera (`95421b1b6`); meu commit do delete foi no-op.

- **T5.1 — gatilho de poda (decisão de design):** o `--check N` (teto absoluto, T1.4) foi
  mantido por retrocompat, mas o gatilho real é **delta-based** — bloqueia o que o plano-raiz
  combate (acreção: adição sem poda), não um teto arbitrário (alinhado à lição "tamanho NÃO é
  a meta"). Baseline persistido (`prompt_size_baseline.json`) + comparação por `system_prompt`
  E total; **redução nunca bloqueia**. Hook dispara **só** se o commit toca um dos 3 prompts.
  Prova: 11 pytest (funções puras `snapshot`/`comparar_delta`/`atualizar_bloco_marcado`) +
  smoke e2e (crescimento +2L staged → exit 1; revertido).

- **T5.2 — doc auto-medida:** marcadores no CLAUDE.md + `--update-claude-md` (idempotente).
  A defasagem de 6,5x que originou o plano era número manual; agora a fonte é o bloco gerado.

- **T5.3/T5.4 — processo:** checklist C0-vs-C1 + cadência trimestral (próxima jul/2026) na
  seção "Governança do prompt". O gatilho técnico (T5.1) materializa o "editou prompt →
  re-review" (todo crescimento força decisão consciente no pre-commit).

- **Pendências reais que sobram (não-FASE-5):** T3.3/T3.4 (bloqueadas por medição de
  cache/custo — depende de tráfego pós-fix; T3.3 provável no-op), FASE 4 (T4.1/T4.2 + T4.3 em
  sessão paralela), T3.1 test vectors §11 (Rafael no agente web).

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
