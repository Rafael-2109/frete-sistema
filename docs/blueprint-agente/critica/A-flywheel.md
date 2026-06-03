<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/blueprint-agente/critica/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# CRÍTICA ARQUITETURAL — Eixo A (Flywheel de Aprendizado)

> **Papel:** CRÍTICA ARQUITETURAL — Eixo A (Flywheel de Aprendizado).

## Indice

- [0. Verificação das alegações (fiz auditoria linha-a-linha antes de criticar)](#0-verificação-das-alegações-fiz-auditoria-linha-a-linha-antes-de-criticar)
- [1. COERÊNCIA — o alvo é internamente consistente e respeita invariantes?](#1-coerência-o-alvo-é-internamente-consistente-e-respeita-invariantes)
- [2. REAPROVEITAMENTO — reusa de fato, ou reinventa? Peças não aproveitadas](#2-reaproveitamento-reusa-de-fato-ou-reinventa-peças-não-aproveitadas)
- [3. REALIZABILIDADE — cada fase entrega valor com rollback? Acoplamento perigoso?](#3-realizabilidade-cada-fase-entrega-valor-com-rollback-acoplamento-perigoso)
- [4. LACUNAS — o que o blueprint NÃO considerou](#4-lacunas-o-que-o-blueprint-não-considerou)
- [5. AMBIÇÃO — é o TETO, ou ficou tímido?](#5-ambição-é-o-teto-ou-ficou-tímido)
  - [ELEVAÇÃO DE AMBIÇÃO CONCRETA — `attribution_judge` (passo-nível), não só `quality_signal` (turn-nível)](#elevação-de-ambição-concreta-attribution_judge-passo-nível-não-só-quality_signal-turn-nível)
- [VEREDITO](#veredito)
  - [Fontes externas](#fontes-externas)
- [Contexto](#contexto)

> Revisor: arquiteto sênior cético. Lente de TETO (NUNCA por volume/over-engineering).
> Veredito de uma linha: **SÓLIDO no diagnóstico, AJUSTAR no alvo — o teto ficou um andar abaixo
> do real, e há 2 peças de infra já-existentes (uma delas abandonada de propósito) que o caminho
> não reaproveita e deveria.**

---

## 0. Verificação das alegações (fiz auditoria linha-a-linha antes de criticar)

| Alegação do blueprint | Verificado? | Nuance que o blueprint não capturou |
|---|---|---|
| Ruptura #1 — effective_count = eco semântico (`_helpers.py:497`) | ✅ CONFIRMADO | `_check_effectiveness_semantic` (`_helpers.py:580-602`): cosseno Voyage entre memória e resposta, threshold único. É literalmente "a resposta ecoou a memória". |
| Ruptura #1 — resolution_rate = teve tool + ≥4 msgs (`insights_service.py:229`) | ✅ CONFIRMADO | `_count_resolved` (linha 229-247) só checa `tools_used` e `message_count>=4`. `health_score` (linha 401) herda. Diagnóstico impecável. |
| Ruptura #3 — verify = opinião do Sonnet sem baseline (`improvement_suggester.py:415`) | ✅ CONFIRMADO | `_evaluate_responses_batch` (linha 446-462): manda `implementation_notes`+sessões e pede verdict. Zero baseline antes/depois. |
| Ruptura #2 — `USE_OPERATIONAL_DIRECTIVES=false`, builder pronto | ✅ CONFIRMADO | `feature_flags.py:215` OFF; `_build_operational_directives` (`memory_injection.py:420-472`) ordena por `effective_count.desc()` filtrando `importance>=THRESHOLD`. Pronto e parado, como descrito. |
| Ruptura #4 — `importance` é entrada (set na criação, não recalibrado) | ✅ CONFIRMADO | injeção usa `0.3*decay+0.3*importance+0.4*similarity` em múltiplos tiers (`memory_injection.py:929,989,1160`). |
| Ruptura #6 — 👍👎 "apenas logados" | ⚠️ **PARCIALMENTE FALSO** | Ver §4.1. O docstring (`feedback.py:33`) ainda diz "apenas logados", mas o CÓDIGO (Sessão E #17, `feedback.py:65-115`) JÁ persiste positive/negative em `AgentSession.data['feedbacks']` e correction incrementa `correction_count` via `_track_correction_feedback`. O blueprint leu o docstring, não o corpo. |
| Ruptura #6 — `escalated_to_human`/`user_correction_received` nunca escritos | ✅ CONFIRMADO | `models.py:1647-1648`, comentário `models.py:1610` confirma "ficam com default". |

**Conclusão da verificação:** 5 das 6 rupturas estão precisamente evidenciadas. A #6 está
inflada (o sinal humano NÃO está inerte — está mal-domiciliado, ver §4.1). Isso não derruba a
tese, mas muda o primeiro passo (A0).

---

## 1. COERÊNCIA — o alvo é internamente consistente e respeita invariantes?

**Em grande parte SIM.** Pontos fortes reais:
- O insight central ("o loop gira sobre ECO/ATIVIDADE, não ACERTO; o elo quebrado é Coach") é
  arquiteturalmente correto e é a coisa certa a atacar. Não é cosmético.
- Encaixe nas 5 camadas (§2.5) é honesto: usar `Stop`/`SubagentStop` hook para enfileirar o turn
  ao judge batch respeita o best-effort dos services e mantém `<operational_directives>` fora do
  cache de prompt. Isso preserva a invariante de caching (Camada 1 estática).
- Respeita "judge em batch, NÃO inline" → não viola latência do canal Web (SSE) nem do Teams.

**Onde a coerência QUEBRA (2 problemas):**

**(C1) O alvo introduz reward-hacking sem nomear o risco — e o sistema JÁ exibe o sintoma.**
A pesquisa 2026 é explícita: *"policies trained with non-reasoning judges inevitably reward-hack;
models developed systematic adversarial strategies including writing self-assessments to score
high"* ([Augment / failure modes](https://ceaksan.com/en/llm-agentic-failure-modes)). O blueprint
propõe (A4) **promover diretrizes automaticamente otimizando contra o quality_signal** — e o
quality_signal inclui um LLM-judge. Ora: a Ruptura #1 do próprio blueprint já é um caso de
reward-hacking embrionário (o sistema recompensa eco). Fechar o loop A1→A4 sem um *reasoning judge*
e sem held-out anti-gaming corre o risco de ensinar o agente (via diretrizes promovidas) a produzir
respostas que AGRADAM o judge. O blueprint menciona spot-check humano de 5-10% como calibração,
mas calibração ≠ defesa anti-gaming. **Faltou:** o judge precisa ser *reasoning* (avalia a
trajetória com justificativa, não dá nota cega) e o quality_signal precisa de um componente
ambiental NÃO-gameável (outcome real: operação Odoo revertida, NF retransmitida, sessão
re-aberta) com peso dominante sobre o judge na decisão de PROMOÇÃO.

**(C2) `agent_turn_quality` (1 linha por turn) não tem onde ancorar — não existe entidade "turn".**
Auditei `models.py`: as tabelas são `AgentSession` (sessão), `AgentInvocationMetric` (por spawn de
subagent), `AgentSessionCost`. **Não há tabela de turn nem ID estável de turn.** As mensagens vivem
dentro de `AgentSession.data` (JSON blob, `get_messages()`). O blueprint assume "1 linha por turn
assistant relevante" como se turn fosse cidadão de primeira classe — não é. Consequência prática
não mapeada: para o judge batch escrever `agent_turn_quality` ele terá que (a) parsear o JSON de
`data`, (b) inventar um turn_id sintético estável (índice da mensagem? hash?), (c) joinar de volta
nesse id frágil quando o sinal humano chegar depois. Isso é acoplamento perigoso ao formato do blob
`data` — que `feedback.py` e `session_summarizer` já mutam. **Isso não invalida o alvo, mas é uma
decisão de schema de primeira ordem que o blueprint pulou** (ver §4.2 para a peça que resolve).

---

## 2. REAPROVEITAMENTO — reusa de fato, ou reinventa? Peças não aproveitadas

O blueprint é geralmente bom em reaproveitar (cita builder de diretrizes, cold-move, infra de
batch, datasets). Mas deixou 3 peças existentes na mesa:

**(R1) ⭐ A peça mais importante esquecida: o penalizador `correction_count` FOI CONSTRUÍDO E
REMOVIDO de propósito.** `memory_injection.py:332-335`:
> *"removido `_adjust_importance_for_corrections` e constantes `_CORRECTION_PENALTY_*` — era dead
> code. `correction_count = 0` em 197/197 memórias (nada incrementa o contador)."*

Ou seja: já existiu um mecanismo que rebaixava `importance` de memórias corrigidas pelo usuário, e
foi **deletado em 2026-04-12 (v2.2) não porque era ruim, mas porque NENHUM sinal o alimentava.**
Isto é a evidência mais forte de toda a tese do eixo: a maquinaria de atuação foi removida por
falta de sinal. O caminho incremental do blueprint NÃO cita isto. **A Fase A0/A2 deveria
explicitamente RESSUSCITAR `_adjust_importance_for_corrections`** agora que A0 passará a alimentar
`correction_count` de verdade. É reaproveitamento de código que o autor da v2.2 conscientemente
estacionou esperando exatamente este sinal. (E a coluna `correction_count` continua em
`models.py:545` justamente para backwards-compat — o trilho está lá.)

**(R2) O blueprint subusa o `friction_analyzer`.** Ele o cita só para "re-pergunta". O serviço já
tem QUATRO detectores prontos que são, cada um, um sinal de outcome ambiental: `_find_repeated_queries`,
`_find_abandoned_sessions`, `_find_frustration_signals`, `_find_no_tool_sessions`
(`friction_analyzer.py:186,274,319,376`). O canal "outcome ambiental" do §2.1 está 80% implementado
e o blueprint trata como a-construir. **A1 deveria declarar que o canal outcome = agregação dos 4
detectores existentes + cross-ref Odoo, não código novo.**

**(R3) `AgentInvocationMetric.get_anomalies` (custo/duração) já é um detector estatístico.** Ao
montar o canal outcome, anomalia de custo/duração de subagent é sinal barato de trajetória ruim
(turn que custou 5x o normal provavelmente patinou). O blueprint trata observabilidade de custo
como "Eixo E / não-qualidade" — mas custo-anômalo É um proxy de outcome ruim já calculado
(`metrics_dashboard_service.py:380`). Reaproveitável de graça no canal ambiental.

---

## 3. REALIZABILIDADE — cada fase entrega valor com rollback? Acoplamento perigoso?

**Sequenciamento (A0→A1→A2→A3→A4→A5) está correto** — "primeiro o fio de qualidade, depois ligar
atuadores" é a ordem certa, e A4 (mexe em comportamento ativo) por último é prudente. Cada fase
atrás de flag é coerente com a cultura do repo (cold-move, ui_policy_lint report→enforce).

**Riscos de realizabilidade que o blueprint subestima:**

- **A3 (gate no D8) tem um acoplamento perigoso não-mapeado:** o D8 roda `claude -p` HEADLESS e
  commita direto em main (`dominio-8-improvement-dialogue.md:13`). Adicionar um `run_eval.py` como
  gate significa que um eval flaky (e a própria pesquisa diz: *"judge scores devem ser tratados como
  flaky tests até provados estáveis"*) pode **travar o único atuador de código autônomo** do sistema.
  O blueprint propõe report-only→enforce (bom), mas não diz **onde o eval roda**: dentro do
  `claude -p` headless (que então se auto-avalia — conflito de interesse) ou num passo separado? Isso
  precisa ser um processo EXTERNO ao agente que está sendo avaliado, senão é o réu presidindo o
  próprio júri.

- **A2 muda a semântica de `effective_count`** — coluna lida por cold-move E pelo dashboard insights
  (`insights.html:1603`) E pela ordenação do builder de diretrizes (`memory_injection.py:472`).
  Mudar o significado de "efetivo" reverbera em 3 consumidores. O blueprint manda "fazer atrás de
  flag e comparar distribuição" — correto, mas deveria **introduzir uma coluna NOVA** (ex:
  `outcome_effective_count`) em vez de redefinir a existente, para não quebrar o dashboard e permitir
  rollback limpo. Redefinir in-place é o acoplamento perigoso.

---

## 4. LACUNAS — o que o blueprint NÃO considerou

**(4.1) O primeiro passo (A0) está mal-formulado porque parte de premissa falsa.** Como o sinal
👍👎 JÁ é persistido (em `AgentSession.data['feedbacks']`, §0), o trabalho de A0 NÃO é "persistir o
que é jogado fora" — é **promover o sinal de dentro do blob JSON para uma estrutura consultável e
joinável**. A reformulação correta de A0: criar `agent_turn_signal` (ou reaproveitar/estender
`AgentInvocationMetric` com colunas que já existem vazias) e MIGRAR os `data['feedbacks']` legados
para ela. Sem isso, o sinal humano continua impossível de joinar com o quality_signal do judge (que
é exatamente o problema de schema da §C2). **O ground-truth não está perdido; está num lugar que não
dá pra fazer query analítica.**

**(4.2) Lacuna de schema (a mais importante): falta a entidade "turn".** O alvo inteiro pressupõe
granularidade de turn, mas o sistema só tem granularidade de sessão (`AgentSession`) e de
spawn-de-subagent (`AgentInvocationMetric`). Antes de A1 há uma fase-zero de schema implícita: ou
(a) `agent_turn` como tabela de 1ª classe com FK para sessão + índice de mensagem, populada pelo
`Stop` hook, ou (b) estender `AgentInvocationMetric` (que já é por-invocação) para também cobrir o
turn principal Web/Teams, não só subagents. O blueprint deveria escolher e justificar. **Esta é a
dependência interna omitida.**

**(4.3) Credit assignment / atribuição de culpa não está no alvo — e é o teto de verdade.** Ver §5.

**(4.4) Dependência cross-eixo subdeclarada com EIXO D (ontologia).** O canal "outcome ambiental"
quer detectar "operação Odoo revertida" — mas isso exige saber que o turn TOCOU uma operação Odoo e
qual entidade. Isso é a ontologia logística do Eixo D (modelo de mundo Nacom). O blueprint liga A
forte ao Eixo E e B, mas o canal ambiental de maior valor (outcome no mundo real, o ÚNICO sinal
não-gameável) depende do Eixo D para mapear turn→entidade-de-negócio→desfecho. Sem D, o canal
ambiental fica restrito a sinais de UX (abandono, re-pergunta), que são fracos. **Dependência D→A
omitida e é estrutural.**

**(4.5) Não há tratamento de turns sem ground-truth (a esmagadora maioria).** 👍👎 é clicado numa
fração mínima dos turns. O judge cobre o resto, mas o blueprint não diz a política quando os 3
canais discordam nem o que acontece com o turn "mudo" (sem humano, sem outcome claro, judge
incerto). Precisa de uma política de abstenção/confiança explícita, senão o quality_signal vira
ruído para a massa de turns neutros — e A2 recalibra `importance` sobre ruído.

---

## 5. AMBIÇÃO — é o TETO, ou ficou tímido?

**Ficou um andar abaixo do teto.** O alvo do blueprint é um *flywheel eval-driven com judge de
TRAJETÓRIA/turn* (outcome-level). Isso é classe-mundial-2025, não o teto-2026. O estado da arte que
ancora o verdadeiro teto:

> A pesquisa 2026 madura em agentic learning migrou de *outcome reward* para **credit assignment em
> nível de passo (Process Reward Models)**: *"determinar QUAIS ações dentro de uma trajetória longa
> causaram o desfecho, em vez de reward esparso a nível de resultado"*
> ([AgentPRM, WWW 2026](https://arxiv.org/html/2511.08325v1);
> [survey Stanford de 47 métodos, arXiv 2604.09459](https://arxiv.org/html/2604.09459v1);
> [AgenTracer — quem induz a falha no sistema agêntico](https://arxiv.org/pdf/2509.03312)).

O judge de turn do blueprint responde "este turn foi bom?". O teto responde **"QUAL passo da
trajetória estragou o turn?"** — qual tool errada, qual skill mal-roteada, qual diretiva injetada
empurrou para a resposta ruim, qual subagent retornou findings fracos. Essa é a diferença entre
"a memória X estava num turn ruim, rebaixa X" (credit assignment grosseiro, que A2 faz) e "a memória
X foi INJETADA, o agente a CITOU, e foi a citação dela que levou ao erro — rebaixa X com causalidade"
(credit assignment fino).

### ELEVAÇÃO DE AMBIÇÃO CONCRETA — `attribution_judge` (passo-nível), não só `quality_signal` (turn-nível)

Adicionar ao alvo (Parte 2) um componente que o blueprint não tem: o judge batch, ao avaliar uma
trajetória ruim, produz **atribuição estruturada de culpa** por passo, gravada por componente:

```
agent_turn_quality (turn) ──┐
                            ├─► attribution (1:N por turn)
                            │     { componente_tipo: skill|tool|subagent|memoria_injetada|diretiva,
                            │       componente_id,
                            │       contribuicao: positiva|neutra|culpada,
                            │       evidencia: "citou memória 300 e aplicou regra revogada" }
```

Isto fecha o loop com CAUSALIDADE e destrava coisas que o alvo atual NÃO consegue:
- **A2 vira cirúrgico:** rebaixa `importance` da memória *que foi creditada como culpada*, não de
  toda memória presente num turn ruim (que é o que A2 faz hoje, e é injusto — penaliza memórias
  inocentes que só estavam no contexto).
- **A4 ganha defesa anti-reward-hacking (resolve C1):** o `attribution_judge` é um *reasoning judge*
  por construção (precisa justificar a culpa) — exatamente o que a pesquisa 2026 diz que evita
  reward-hacking, ao contrário do judge de nota cega.
- **Alimenta o Eixo F (governança de skills) com sinal CAUSAL, não correlacional:** "skill X
  creditada como culpada em N turns" >> "skill X estava presente em turns de baixa qualidade".
- **Alimenta o Eixo B (planejador):** atribuição por tool/sequência é exatamente o sinal que um
  harness de planejamento precisa para aprender roteamento.

Custo incremental sobre o que o blueprint já propõe: ~zero de infra nova (o judge batch JÁ vai ler
a trajetória inteira em A1 — só precisa devolver atribuição estruturada em vez de uma nota escalar).
É a mesma chamada de Sonnet, com output mais rico. **O blueprint pediu uma nota; peça um laudo.**

---

## VEREDITO

**AJUSTAR** (diagnóstico sólido, alvo a elevar). Três ajustes obrigatórios:
1. **Reformular A0**: o sinal humano não está inerte, está mal-domiciliado em `data['feedbacks']`
   (`feedback.py:65-115`); A0 = promovê-lo a estrutura joinável + ressuscitar o
   `_adjust_importance_for_corrections` deletado em v2.2 (`memory_injection.py:332`).
2. **Inserir fase-zero de schema de "turn"**: o sistema não tem entidade turn (só `AgentSession`
   blob + `AgentInvocationMetric` por-subagent); decidir tabela `agent_turn` vs estender
   `AgentInvocationMetric` antes de A1 (resolve C2 e 4.2).
3. **A2 não-destrutivo**: coluna nova (`outcome_effective_count`), não redefinir `effective_count`
   in-place (3 consumidores acoplados).

**A lacuna mais importante:** *não existe entidade "turn" no schema* (§C2, §4.2) — `agent_turn_quality`
"1 linha por turn" não tem onde ancorar nem turn_id estável para joinar o sinal humano (que chega
depois) com a nota do judge. É a primeira decisão de design e o blueprint a pulou. Sem resolvê-la,
A0 (humano) e A1 (judge) escrevem em granularidades que não se joinam.

**A elevação de ambição:** subir de **quality_signal (nota de turn)** para **attribution_judge
(laudo de culpa por passo — Process Reward Model)** — o teto 2026 é credit assignment de nível de
passo ([AgentPRM WWW 2026](https://arxiv.org/html/2511.08325v1)), não outcome de turn. Mesma chamada
de Sonnet do A1, output estruturado por componente (skill/tool/subagent/memória/diretiva). Torna A2
cirúrgico (penaliza só o culpado), dá a A4 um *reasoning judge* anti-reward-hacking de graça, e
serve sinal CAUSAL aos eixos B (planejador) e F (governança).

---

### Fontes externas
- [Augment Code — Agent Learning Flywheel](https://www.augmentcode.com/guides/agent-learning-flywheel)
- [LLM Agentic Failure Modes — reward hacking com non-reasoning judges](https://ceaksan.com/en/llm-agentic-failure-modes)
- [AgentPRM: Process Reward Models for LLM Agents (WWW 2026)](https://arxiv.org/html/2511.08325v1)
- [Stanford — survey de 47 métodos de credit assignment (arXiv 2604.09459)](https://arxiv.org/html/2604.09459v1)
- [AgenTracer — who is inducing failure in LLM agentic systems](https://arxiv.org/pdf/2509.03312)
- [Agent-in-the-Loop: data flywheel for LLM customer support (arXiv 2510.06674)](https://arxiv.org/html/2510.06674v1)

## Contexto

Critica de eixo do blueprint — evolucao do agente logistico. Tema: CRÍTICA ARQUITETURAL — Eixo A (Flywheel de Aprendizado)
