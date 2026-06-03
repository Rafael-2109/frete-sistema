<!-- doc:meta
tipo: explanation
camada: L3
sot_de: reconciliacao da avaliacao de memoria com os eixos do blueprint do agente
hub: app/agente/CLAUDE.md
superseded_by: —
atualizado: 2026-06-02
-->

# RECONCILIAÇÃO — Avaliação do Sistema de Memória ↔ Blueprint do Agente

> **Papel:** conecta a avaliação dimensional do sistema de memória (02/06/2026) aos eixos existentes
> do `BLUEPRINT_MESTRE.md`. Objetivo: **não duplicar** o que já está em execução (D, E, A4) e
> **localizar as lacunas** num lar próprio. Este doc é o índice; o detalhe vive nos eixos
> (`eixos/C-vigilancia.md`, `eixos/G-memoria-pessoal.md`), no rastreador (`EXECUCAO.md`) e no
> plano executável (`docs/superpowers/plans/2026-06-02-loop-corretivo-pessoal.md`).
> Origem: pedido do Rafael (avaliação + planejamento de melhorias da memória). Sintoma-gatilho
> (Marcus, Controller Financeiro): *"expliquei pro agente e fez certo, mas na outra sessão fez tudo errado de novo."*

---

## Indice

- Contexto
- 1. O sintoma e a prova (por que isto importa)
- 2. A tese central (o que amarra a avaliação ao blueprint)
- 3. Mapa frente × eixo (10 frentes da avaliação)
- 4. O que NÃO refazer (já existe — evitar duplicata)
- 5. As lacunas e seu lar (o que esta avaliação adiciona)
- 6. Sequência (herda a regra de ouro do blueprint)
- 7. Estado e proveniência

## Contexto

O pedido original foi avaliar e planejar melhorias do *sistema de memória* do agente. Esta reconciliação garante que a avaliação se integre ao `BLUEPRINT_MESTRE.md` (eixos A/B/D/E/F) **sem duplicar** o que já está em execução, localizando as lacunas nos eixos C e G.

## 1. O sintoma e a prova (por que isto importa)

O agente **grava** as lições do usuário, mas elas **não voltam ao contexto** no fluxo de trabalho
recorrente. Prova empírica de produção (logs `[MEMORY_INJECT]`, web `sistema-fretes`, 29/05–02/06),
todas as sessões "atualizar baseline" do Marcus (user_id=18, Opus, budget ilimitado):

| Data/hora | prompt | semantic | tier2 (correções pessoais) | tier2b (empresa) |
|---|---|:--:|:--:|:--:|
| 29/05 11:11 | atualizar baseline | 0 | **0 chars** | 31.556 |
| 31/05 02:13 | atualizae baseline | 0 | **0 chars** | 31.570 |
| 01/06 17:01 | atualizar baseline data base 01/06 | 0 | **0 chars** | 36.466 |
| 02/06 11:27 | atualizar baseline | 0 | **0 chars** | 36.851 |

`semantic=0` + `tier2_chars=0` → **zero correções pessoais injetadas**; o contexto enche de memória da
empresa (fallback de recência). As 36 correções do Marcus (≈9 sobre o mesmo erro) **nunca chegam ao
modelo** no fluxo rotineiro. Reincidência confirmada: "não fazer JUROS (outros)" corrigido 09/04 **e de
novo** 10/04; "troca de escopo/cluster" ~9× entre 07–13/04.

## 2. A tese central (o que amarra a avaliação ao blueprint)

**O sistema não está mal arquitetado — está construído e desligado.** O padrão dominante não é "falta
código": é **infraestrutura pronta e OFF** + **features meio-construídas** + **2 lacunas conceituais
reais**. A maior alavancagem é **LIGAR + MEDIR**, em ordem (observabilidade antes de atuadores). Isto é
a mesma tese do `BLUEPRINT_MESTRE.md` — esta avaliação a estende para o pipeline de **memória pessoal e
recuperação**, que o blueprint subestimou.

## 3. Mapa frente × eixo (10 frentes da avaliação)

| Frente da avaliação | Eixo do blueprint | Status | Onde fica |
|---|---|:--:|---|
| **F5** Knowledge graph (recall/qualidade) | **D — Ontologia** | ✅ coberto | já é o eixo D (bi-temporal, entity_key, proveniência) |
| **F8** Observabilidade / avaliação | **E — Qualidade** | ✅ coberto | já é o eixo E (Quality Spine, PRM) |
| **F3** Conhecimento da empresa (user_id=0) | **A — Flywheel / D** | ✅ em execução | A4 (promoção de diretriz, LIVE PROD 01/06) |
| **F1** **Loop corretivo PESSOAL** (dor do Marcus) | A — Flywheel | ⚠️ **parcial** | A cobre credit-assignment + diretriz **empresa**; canal/promoção **pessoal** = LACUNA → **`eixos/G` + plano** |
| **F9** Gate de escrita no pool empresa | F — Governança | ⚠️ parcial | governança trata 5 camadas; escrita de memória empresa = item novo em F |
| Vigilância proativa · reflexão agendada (sleep-time) · staleness | **C — (referenciado, ausente)** | 🟦 a escrever | **`eixos/C-vigilancia.md`** |
| **F2** procedural positivo · **F4** perfil/budget · **F6** recuperação/HyDE · **F7** continuidade · **F10** amnésia de subagente | — (sem eixo) | 🆕 lacunas | **`eixos/G-memoria-pessoal.md`** |

**Leitura:** metade já está no blueprint e em execução (D, E, A4). Esta avaliação **não substitui** —
preenche: (a) o **Eixo C** (já referenciado pela crítica de D, nunca escrito); (b) um **Eixo G** para
o pipeline de memória pessoal + recuperação; (c) o **loop corretivo pessoal** como plano executável.

## 4. O que NÃO refazer (já existe — evitar duplicata)

- **D — Ontologia / KG** (`eixos/D-ontologia.md`): bi-temporal, entity_key, proveniência, `query_graph_memories`.
- **E — Qualidade** (`eixos/E-qualidade.md`): Quality Spine step-level, outcome_signal, judge calibração.
- **A4 — Promoção de diretriz** (`EXECUCAO.md` item A4, LIVE PROD): reusa `_build_operational_directives` (`memory_injection.py:420`); `directive_status` migrado; `AGENT_OPERATIONAL_DIRECTIVES` **ON** em PROD (confirmado em logs — injeta 5 heurísticas empresa iguais para todos).

> Reconciliação de flags (logs PROD vs defaults do código): `USE_OPERATIONAL_DIRECTIVES`=**ON**;
> `USE_USER_RULES_CHANNEL`=**OFF** (canal pessoal desligado E vazio: 1/503 mandatory);
> `USE_USER_XML_POINTER`=**OFF**; pacote eval provável OFF (`outcome_signal=NULL` em PROD).

## 5. As lacunas e seu lar (o que esta avaliação adiciona)

### Eixo C — Vigilância proativa (`eixos/C-vigilancia.md`)
Reflexão agendada (sleep-time compute), detecção proativa de contradição/staleness, bi-temporal
(fato novo invalida o antigo). Já era referenciado por `critica/D-ontologia.md:213,237`. Pré-reqs
existem (scheduler D8, `memory_consolidator`, schema KG `valid_from/valid_to`).

### Eixo G — Memória pessoal & recuperação (`eixos/G-memoria-pessoal.md`)
O pipeline que entrega (ou não) a memória pessoal ao modelo:
- **F1** loop corretivo pessoal (gravar→reconciliar→promover→injetar-garantido→enquadrar→medir-outcome→retroalimentar);
- **F2** aprendizado procedural positivo (capturar o "jeito certo", não só o erro — ratio receita:armadilha ≈ 0:1);
- **F4** perfil do usuário + budget (`USE_USER_XML_POINTER` OFF zera o Tier 2);
- **F6** recuperação (HyDE + threshold adaptativo — 91% dos prompts <150 chars → `semantic=0`);
- **F7** continuidade entre sessões (work_context contaminado pela última sessão);
- **F10** injeção de memória em subagentes (hoje operam em amnésia).

### Plano executável (`docs/superpowers/plans/2026-06-02-loop-corretivo-pessoal.md`)
A primeira frente acionável de G — a dor do Marcus — em formato TDD, flag-OFF.

### Continuação (`PROMPT_PROXIMA_SESSAO_LOOP_CORRETIVO.md`)
Prompt rigoroso para a próxima sessão limpa: backfill do passivo do Marcus (dry-run+OK) + Fase 3 (medição por outcome + tuning de posição + frame imperativo). Estado: Fases 0/1/2 ✅ (commits no worktree, não pushados).

## 6. Sequência (herda a regra de ouro do blueprint)

**Medir antes de atuar.** A Onda 1 (observabilidade, eixo E) é pré-requisito de ligar qualquer atuador
de memória pessoal. A Onda 0 (governança/segurança, eixo F + gate de escrita empresa) é pré-condição de
ligar o canal de diretrizes. O detalhe do roadmap integrado (6 ondas) vive em `eixos/G` §3 e no
`EXECUCAO.md`.

## 7. Estado e proveniência

- Avaliação produzida em 02/06/2026 (Claude Code), via confronto produção (Render PROD) + logs runtime +
  forense de código + pesquisa verificada (Mem0, ACE, AgingBench, IFScale, Generative Agents, CoALA, Zep, Memp, Anthropic).
- **Nada implementado** — diagnóstico + plano. Itens rastreados em `EXECUCAO.md`.
- Hub: referenciado por `app/agente/CLAUDE.md` (junto de `EXECUCAO.md`).
