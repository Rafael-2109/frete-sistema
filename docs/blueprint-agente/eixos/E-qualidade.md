<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/blueprint-agente/eixos/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# EIXO E — Observabilidade de Qualidade

> **Papel:** EIXO E — Observabilidade de Qualidade.

## Indice

- [PARTE 1 — ESTADO REAL (com evidência arquivo:linha)](#parte-1-estado-real-com-evidência-arquivolinha)
  - [1.1 O que a telemetria mede HOJE: tudo menos qualidade](#11-o-que-a-telemetria-mede-hoje-tudo-menos-qualidade)
  - [1.2 Os dois campos de qualidade que EXISTEM no schema mas nunca foram escritos](#12-os-dois-campos-de-qualidade-que-existem-no-schema-mas-nunca-foram-escritos)
  - [1.3 O proxy de "resolução" é estrutural, não de qualidade (falso positivo sistemático)](#13-o-proxy-de-resolução-é-estrutural-não-de-qualidade-falso-positivo-sistemático)
  - [1.4 Os SINAIS de qualidade que JÁ EXISTEM — mas morrem no chão](#14-os-sinais-de-qualidade-que-já-existem-mas-morrem-no-chão)
  - [1.5 O que JÁ é LLM-as-judge no sistema (e por que não basta)](#15-o-que-já-é-llm-as-judge-no-sistema-e-por-que-não-basta)
  - [1.6 Golden datasets existem, com rubrica rica, mas julgamento é MANUAL](#16-golden-datasets-existem-com-rubrica-rica-mas-julgamento-é-manual)
  - [1.7 O ponto de injeção natural já está cabeado: `_stop_hook`](#17-o-ponto-de-injeção-natural-já-está-cabeado-_stop_hook)
  - [1.8 Diagnóstico em uma frase](#18-diagnóstico-em-uma-frase)
- [PARTE 2 — ALVO ARQUITETURAL (o teto)](#parte-2-alvo-arquitetural-o-teto)
  - [2.1 Princípio: um Quality Signal Spine — uma nota por turno, fundida de N fontes](#21-princípio-um-quality-signal-spine-uma-nota-por-turno-fundida-de-n-fontes)
  - [2.2 As cinco camadas do SDK — onde cada peça encaixa](#22-as-cinco-camadas-do-sdk-onde-cada-peça-encaixa)
  - [2.3 Modelo de dados-alvo](#23-modelo-de-dados-alvo)
  - [2.4 Online judge — reference-free, por turno, amostrado](#24-online-judge-reference-free-por-turno-amostrado)
  - [2.5 Offline judge + calibração (o que torna o sinal CONFIÁVEL)](#25-offline-judge-calibração-o-que-torna-o-sinal-confiável)
  - [2.6 Como vira combustível do Eixo A](#26-como-vira-combustível-do-eixo-a)
- [PARTE 3 — CAMINHO INCREMENTAL (reaproveitando o existente)](#parte-3-caminho-incremental-reaproveitando-o-existente)
  - [Fase E0 — Persistir os sinais implícitos que já existem (PARAR de jogar fora)](#fase-e0-persistir-os-sinais-implícitos-que-já-existem-parar-de-jogar-fora)
  - [Fase E1 — Detector de correção/escalada no turno N+1 (sinal implícito mais forte)](#fase-e1-detector-de-correçãoescalada-no-turno-n1-sinal-implícito-mais-forte)
  - [Fase E2 — Online judge do agente principal (cobertura onde não há feedback)](#fase-e2-online-judge-do-agente-principal-cobertura-onde-não-há-feedback)
  - [Fase E3 — Offline harness + calibração (tornar o judge CONFIÁVEL)](#fase-e3-offline-harness-calibração-tornar-o-judge-confiável)
  - [Fase E4 — Fusão + fechar o loop com o Eixo A](#fase-e4-fusão-fechar-o-loop-com-o-eixo-a)
  - [Não-sabido / não verificado](#não-sabido-não-verificado)
- [Fontes externas (ancoragem do alvo em padrões 2026)](#fontes-externas-ancoragem-do-alvo-em-padrões-2026)
- [Contexto](#contexto)

> A métrica que falta. FUNDAÇÃO do flywheel (Eixo A). Sem sinal de qualidade,
> o loop de aprendizado não tem combustível — ele otimiza no escuro.

Lente: TETO. Não julgo capacidade por volume. O alvo abaixo é de classe mundial
mesmo para 1 sessão/dia.

---

## PARTE 1 — ESTADO REAL (com evidência arquivo:linha)

### 1.1 O que a telemetria mede HOJE: tudo menos qualidade

Existem **DUAS** trilhas de telemetria, ambas operacionais (custo/latência/tokens),
**ZERO** sobre se a resposta foi boa.

| Trilha | Tabela | Granularidade | Mede | Evidência |
|---|---|---|---|---|
| CostTracker | `agent_session_costs` | por-mensagem | input/output/cache tokens, `cost_usd` | `models.py:1394-1437` (campos: linhas 1421-1431) |
| Telemetria subagent | `agent_invocation_metrics` | por-spawn de subagent | `duration_ms`, `num_turns`, `cost_usd`, tokens | `models.py:1620-1655` |

Nenhuma das duas tem uma coluna de qualidade. Confirmado por grep:
`quality_score|turn_quality|answer_quality|judge_score|correctness` → **0 ocorrências**
em todo `app/agente`.

### 1.2 Os dois campos de qualidade que EXISTEM no schema mas nunca foram escritos

`AgentInvocationMetric` declara, literalmente comentado como "Backfill posterior (Fase D)":

```
models.py:1647  escalated_to_human       = db.Column(db.Boolean, nullable=False, default=False)
models.py:1648  user_correction_received = db.Column(db.Boolean, nullable=True)
```

O docstring é explícito (`models.py:1610-1611`): *"Campos escalated_to_human e
user_correction_received ficam com default até Fase D do roadmap (loop de feedback fechado)."*

**Grep prova que NUNCA são escritos**: a única referência a esses nomes em
`app/agente/**/*.py` é a própria definição do modelo (`models.py:1647-1648` + docstring
1610). Não há um único `INSERT`/`UPDATE`/atribuição. A Fase D nunca chegou. São colunas
fantasma — a intenção foi codificada no schema e abandonada.

`app/agente/CLAUDE.md` corrobora na seção Telemetria → Roadmap:
*"A4/A5 — Coleta 14d + baseline: em coleta. Após baseline numérico estável:
prosseguir para Fase B (Quality)."* As Fases B/C/D nunca saíram do papel.

### 1.3 O proxy de "resolução" é estrutural, não de qualidade (falso positivo sistemático)

O dashboard de insights tem `resolution_rate` e `health_score`. Parecem qualidade.
Não são. `_count_resolved` (`insights_service.py:229-246`):

```python
if (s.message_count or 0) < 4:        # linha 233 — sessão "curta" não conta
    continue
for msg in messages:
    if msg.get('role') == 'assistant' and msg.get('tools_used'):
        has_tools = True               # linha 239 — basta UMA tool call
        break
if has_tools:
    count += 1                         # linha 244 — "resolvida"
```

Definição operacional de "resolvida" = **≥4 mensagens E ≥1 assistant chamou uma tool**.
Uma sessão onde o agente rodou SQL e devolveu o número **errado** conta como resolvida.
Uma sessão onde o usuário foi embora frustrado conta como resolvida. É um proxy de
*atividade*, não de *acerto*.

`_calc_health_score` (`insights_service.py:368-406`) compõe:
`resolution_rate*0.35 + (100-friction)*0.25 + cost_stability*0.20 + adoption*0.20`.
Três dos quatro termos (resolution, cost_stability, adoption) são operacionais.
O único termo que tangencia qualidade (`friction`) é heurístico e nunca cruzado com
ground truth.

### 1.4 Os SINAIS de qualidade que JÁ EXISTEM — mas morrem no chão

O sistema **já capta** sinais ricos de qualidade e os **descarta** ou usa para fins
estreitos. Este é o achado central: não falta sensor, falta *persistir o sinal como métrica*.

**(a) Sentiment — score calculado e jogado fora.**
`sentiment_detector.detect_frustration` (`sentiment_detector.py:76-167`) produz um
`score` inteiro e um booleano `is_frustrated` (>=3). `enrich_message_if_frustrated`
(`sentiment_detector.py:170-214`) usa o score só para decidir injetar um
`<system-reminder>` de tom (linha 208) e o guarda em `_session_scores`, um dict
**in-memory que perde no restart** (linha 27-28). O caller único
(`chat.py:553-558`) **não captura o retorno do score** — recebe só o prompt enriquecido.
O sinal de frustração por-turno existe por milissegundos e evapora.

**(b) Feedback explícito — 5 tipos capturados, consumidos como contador.**
`routes/feedback.py` aceita `positive|negative|correction|preference|suggestion_click`
(linha 56). O destino:
- `positive`/`negative`/`suggestion_click` → append em `AgentSession.data['feedbacks']`
  (JSONB) (linhas 73-83, 99-111, 172-181).
- `correction` → cria memória `/memories/corrections/feedback_*.xml` +
  `_track_correction_feedback` (linhas 123-139).
- `preference` → memória `preferences.xml` (linhas 145-156).

Quem **lê** esses feedbacks? Grep `feedbacks` (excluindo a própria rota) →
**uma única** consumidora: `insights_service.py:321-322`, e só conta cliques de sugestão
(`type == 'suggestion_click'`). Os thumbs up/down ficam no JSONB **sem nenhum consumidor**.
Não viram métrica, não calibram nada, não alimentam o health_score.

**(c) Correção implícita — já minerada para memória, nunca para métrica.**
`pattern_analyzer` extrai `anti_patterns: coisas que o agent fez e user corrigiu`
(`pattern_analyzer.py:6`) e o `correction_count` por memória é incrementado por
`_track_correction_feedback` (`memory_mcp_tool.py:1306-1359`, `SET correction_count =
correction_count + 1`). Ou seja: **o sistema já detecta que o usuário corrigiu o agente**
e usa isso para ranquear memórias (`insights_service.py:944-969`). Mas esse evento de
correção **nunca é atribuído a um turno como sinal negativo de qualidade**.

**(d) Friction — detecta repetição/abandono/frustração, só agrega offline.**
`friction_analyzer.analyze_friction` (`friction_analyzer.py:51`) computa
`repeated_queries`, `abandoned_sessions`, `frustration_signals`
(`friction_analyzer.py:319-373`) e `no_tool_sessions`. Roda em batch para o dashboard
admin. Não emite sinal por-turno, não retroalimenta a resposta. **Nota de dívida**:
mantém uma SEGUNDA lista de marcadores de frustração (`friction_analyzer.py:336-340`)
divergente da de `sentiment_detector.py:31-61` — duas fontes da verdade para o mesmo conceito.

### 1.5 O que JÁ é LLM-as-judge no sistema (e por que não basta)

`workers/subagent_validator.py` **já é um LLM-as-judge funcionando em produção**:
- Haiku 4.5 (`subagent_validator.py:28`) compara tool_calls+tool_results vs resposta
  final do **subagente** e retorna `{"score": 0-100, "reason", "flagged_claims"}`
  (system prompt em `subagent_validator.py:30-42`).
- Persiste em `AgentSession.data['subagent_validations']` (linha 170) e, se
  `score < threshold` (default 70, `USE_SUBAGENT_VALIDATION` ON), publica Redis pubsub
  → SSE `subagent_validation` → ícone ⚠ na UI (linhas 84-97, 194).

**Limite crítico**: ele julga **faithfulness de SUBAGENTES** (a resposta bate com as
tools que ele rodou?). Não julga:
- a resposta do **agente principal** (a maioria dos turnos não spawna subagent);
- **correção vs intenção do usuário** (faithfulness ≠ correctness — uma resposta pode
  ser fiel às tools e ainda assim resolver a pergunta errada);
- nada offline contra os golden datasets.

### 1.6 Golden datasets existem, com rubrica rica, mas julgamento é MANUAL

`.claude/evals/subagents/{analista-carteira,auditor-financeiro,gestor-motos-assai,
controlador-custo-frete}/dataset.yaml` têm casos com `input`, `context`,
`expected_behavior` (lista) e `must_not` (lista) — uma rubrica pronta para LLM-as-judge.
Exemplo `analista-carteira/dataset.yaml:11-28`. Mas `README.md:79` declara:
*"Julgamento é MANUAL (não automatizado por LLM). O desenvolvedor lê o output do agent
e compara com o dataset."* Só 4 dos 13 subagentes têm dataset; o agente principal tem zero.

### 1.7 O ponto de injeção natural já está cabeado: `_stop_hook`

`sdk/hooks.py:360` `_stop_hook` dispara ao fim de **todo turno** do agente principal
(registrado em `hooks.py:1321`). Hoje só faz log + archive S3 (linha 398-424). É o gancho
óbvio — e ocioso — para disparar um judge por-turno. O `_subagent_stop_hook`
(`hooks.py:542`) já faz exatamente isso para subagentes (persiste `AgentInvocationMetric`).

### 1.8 Diagnóstico em uma frase

O agente é **rico em sensores de qualidade** (sentiment score, 5 tipos de feedback,
correction_count, friction, um LLM-judge de subagente) e **pobre em persistir esses
sinais como métrica atribuível a um turno**. O resultado é a tese E confirmada: toda a
observabilidade mede CUSTO/latência; nenhuma mede ACERTO. E como o Eixo A (flywheel)
precisa de um sinal de recompensa para girar, ele gira no vácuo — daí
`USE_OPERATIONAL_DIRECTIVES=OFF` e Fases B/C/D nunca terem chegado.

---

## PARTE 2 — ALVO ARQUITETURAL (o teto)

### 2.1 Princípio: um Quality Signal Spine — uma nota por turno, fundida de N fontes

O estado-final é um **sinal de qualidade unificado por turno e por sessão**, persistido,
versionado e auditável, fundindo três classes de evidência (taxonomia que a literatura
2026 de agent evals consolidou — implícitos > explícitos em volume, judge para cobertura,
human corrections para calibração):

```
                    ┌─────────────────────────────────────────────┐
                    │           QUALITY SIGNAL SPINE              │
                    │   turn_quality (nova tabela, 1 linha/turno) │
                    └─────────────────────────────────────────────┘
        ┌───────────────────────┬───────────────────────┬──────────────────────┐
   IMPLÍCITOS (free)        EXPLÍCITOS (raros)        JUDGE (LLM)          GROUND TRUTH
   ──────────────────       ──────────────────       ───────────         ─────────────
   • correção no turno N+1  • thumbs up/down         • online judge        • golden dataset
     (re-pergunta, "errado")  (feedback.py)            por-turno (Haiku)     (.claude/evals)
   • frustração (sentiment    • correction text      • offline judge       • human label
     score já calculado)     • suggestion_click        vs rubrica            (calibração)
   • retry/edição do user                              expected/must_not
   • abandono (friction)
   • latência-para-resposta
   • escalada a humano
```

A nota por turno (`turn_quality_score ∈ [0,1]` + `label ∈ {good, mixed, bad, unknown}`)
é **derivada**, não uma única fonte. Cada fonte entra com seu peso e sua confiança.
Sinais implícitos têm volume alto e ruído alto; o judge dá cobertura onde não há feedback;
ground truth calibra o judge.

### 2.2 As cinco camadas do SDK — onde cada peça encaixa

| Camada SDK | Componente do alvo |
|---|---|
| **5. Control (hooks)** | `_stop_hook` dispara `quality_probe` por-turno (implícitos baratos, síncrono) + enfileira `quality_judge_job` (LLM, assíncrono via RQ) — espelha o que `_subagent_stop_hook` já faz |
| **2. Tools** | nova tool MCP `report_outcome` opcional p/ o agente auto-declarar "respondi / não consegui / escalei" (sinal de auto-avaliação barato; complementa, não substitui) |
| **4. Subagents** | novo subagent **`avaliador-qualidade`** (Haiku, read-only) — o judge offline que roda golden datasets e amostra produção; reusa o padrão de `subagent_validator` |
| **3. Skills** | skill `avaliando-qualidade-agente` (offline harness): lê `dataset.yaml`, roda agente, chama judge, calcula agreement |
| **1. System prompt** | a nota agregada **não** vai pro prompt cru; vira *operational directive* (Eixo A) quando confiável — fecha o loop |

### 2.3 Modelo de dados-alvo

**Nova tabela `turn_quality`** (1 linha por turno do agente principal; sem FK, mesmo
padrão de `agent_session_costs` p/ sobreviver a cascade):

| Campo | Origem |
|---|---|
| `session_id`, `user_id`, `turn_index`, `message_id` | contexto do turno |
| `implicit_score`, `implicit_signals` (JSONB) | quality_probe (sentiment, correção N+1, abandono, retry, latência) |
| `explicit_feedback` (`+1/-1/null`), `explicit_text` | feedback.py (migrado p/ cá) |
| `judge_score` (0-100), `judge_label`, `judge_reason`, `judge_flagged` (JSONB) | online judge Haiku |
| `judge_model`, `judge_prompt_version` | versionamento p/ calibração |
| `fused_score` (0-1), `fused_label` | fusão ponderada das fontes |
| `correction_received` (bool) | detectado no turno N+1 (resolve `user_correction_received` órfão) |
| `escalated_to_human` (bool) | detectado por marcador/handoff (resolve a outra coluna órfã) |
| `ground_truth_label`, `labeled_by` | calibração humana (nullable) |

**Promover os dois campos órfãos**: `escalated_to_human` e `user_correction_received`
do `AgentInvocationMetric` ganham, finalmente, gravação real — e migram para o nível de
turno (mais granular que por-spawn-de-subagent).

### 2.4 Online judge — reference-free, por turno, amostrado

Espelha `subagent_validator` mas para o **agente principal** e com critério de
*correctness vs intenção*, não só faithfulness:
- Input: pergunta do user + resposta do agente + tool_calls/results do turno + (se houver)
  contexto de domínio.
- Output: `{score 0-100, label, reason, flagged_claims, unmet_intent}`.
- **Amostragem** (`QUALITY_JUDGE_SAMPLE_RATE`, default p.ex. 0.3) — controla custo (padrão
  2026 de online eval). Turnos com thumbs-down ou correção detectada → **sempre** julgados
  (sinal barato dispara judge caro só onde importa).
- Modelo: Haiku para volume, escalando p/ Sonnet em turnos flagueados (judge tiering).

### 2.5 Offline judge + calibração (o que torna o sinal CONFIÁVEL)

1. **Harness offline** (skill + subagent `avaliador-qualidade`): roda os `dataset.yaml`,
   pontua `expected_behavior`/`must_not` automaticamente, produz agreement.
2. **Calibração com correções humanas** (padrão LangChain 2026): quando Rafael/admin
   discorda do judge (UI de revisão), a correção vira **few-shot contra-exemplo** no
   prompt do judge — exatamente o mecanismo que `sql_evaluator_falses_service.py` já
   implementa para o SQL evaluator (embedding do par → `cosine_similarity > threshold` →
   injeta contra-exemplo, `sql_evaluator_falses_service.py:1-21`). Reusar essa máquina
   inteira para o judge de qualidade.
3. **Métrica de agreement** rastreada no tempo (judge vs humano) — meta de literatura
   ~80%+; alvo é subir agreement com calibração (MemAlign-style, 30-50% de ganho relatado).

### 2.6 Como vira combustível do Eixo A

`turn_quality.fused_score` agregado por (skill, subagent, tipo de pergunta, usuário)
produz o **sinal de recompensa** que hoje não existe. Aí sim:
- `pattern_analyzer` prioriza extrair padrões de turnos **bons** e anti-padrões de turnos
  **ruins** (hoje extrai sem saber qual deu certo).
- `USE_OPERATIONAL_DIRECTIVES` pode ligar com segurança: uma heurística só vira regra se
  os turnos que a aplicaram tiverem `fused_score` alto.
- O dashboard ganha o eixo que falta: custo POR ACERTO, não custo por atividade.

---

## PARTE 3 — CAMINHO INCREMENTAL (reaproveitando o existente)

> Ordenado por alavancagem. Cada fase diz: o que destrava, esforço (P/M/G), risco,
> dependências cross-eixo, e o que REUSA.

### Fase E0 — Persistir os sinais implícitos que já existem (PARAR de jogar fora)
**Esforço P · Risco baixo.** O maior ganho/custo do eixo: nada de LLM novo.
- Capturar o `score` que `sentiment_detector.detect_frustration` **já calcula**
  (`sentiment_detector.py:159`) no callsite `chat.py:554` — hoje descartado.
- Criar `turn_quality` (migration dupla .py+.sql, regra do projeto) e gravá-la no
  `_stop_hook` (`hooks.py:360`) com: sentiment score, latência-para-resposta, e flag de
  abandono. Reusa o SAVEPOINT pattern de `AgentInvocationMetric.insert_metric`
  (`models.py:1664-1719`).
- **Migrar feedback.py para escrever `turn_quality.explicit_feedback`** em vez de só
  empilhar em JSONB sem consumidor (`feedback.py:73-181`).
- **Destrava**: primeira coluna de qualidade real do sistema; baseline implícito grátis.
- **Dependência**: nenhuma. É a fundação. Todo o resto depende DELA.

### Fase E1 — Detector de correção/escalada no turno N+1 (sinal implícito mais forte)
**Esforço M · Risco baixo.** A correção do usuário é o sinal de qualidade mais confiável
da literatura ("re-pergunta = falha; copiou output = sucesso").
- No início de cada turno, classificar se a mensagem do user corrige/repete o turno
  anterior. **Reusar** os marcadores que já existem (`sentiment_detector.py:31-61`) —
  e de quebra **unificar** com a lista duplicada de `friction_analyzer.py:336-340`
  (eliminar a divergência apontada em 1.4d).
- **Reusar** `_track_correction_feedback` (`memory_mcp_tool.py:1306`) como gatilho: quando
  ele incrementa `correction_count`, gravar `turn_quality.correction_received=true` no
  turno anterior.
- Finalmente **escrever** os campos órfãos `user_correction_received` e
  `escalated_to_human` (`models.py:1647-1648`) — a "Fase D" que nunca veio.
- **Destrava**: sinal negativo de alta confiança, grátis, retroativo (dá p/ backfill
  varrendo `AgentSession.data` histórico).
- **Dependência**: E0 (precisa da tabela). Habilita Eixo A (anti-padrões com label).

### Fase E2 — Online judge do agente principal (cobertura onde não há feedback)
**Esforço M · Risco médio (custo de API, latência).**
- **Clonar** `workers/subagent_validator.py` → `workers/turn_quality_judge.py`. O esqueleto
  está pronto: Haiku, JSON `{score,reason,flagged}`, persistência, Redis pubsub/SSE
  (`subagent_validator.py:30-42, 84-97, 117-194`). Trocar o critério de *faithfulness de
  subagent* para *correctness vs intenção do user* no agente principal.
- Disparo via `_stop_hook` enfileirando job RQ (espelha `_subagent_stop_hook`,
  `hooks.py:542`). Fila `agent_validation` já existe e é leve (worker 0 light-reserved).
- **Amostragem** + escalonamento: julga 100% dos turnos com sinal implícito ruim (E0/E1),
  amostra o resto. Flag `USE_TURN_QUALITY_JUDGE` + `QUALITY_JUDGE_SAMPLE_RATE`.
- **Destrava**: cobertura de qualidade nos ~95% de turnos sem feedback explícito.
- **Dependência**: E0 (tabela), E1 (gating barato). Risco infra = volume (dimensiona nº de
  workers, NÃO o valor da capacidade — lente de teto).

### Fase E3 — Offline harness + calibração (tornar o judge CONFIÁVEL)
**Esforço G · Risco baixo (não toca produção).**
- Skill `avaliando-qualidade-agente` + subagent `avaliador-qualidade` que roda os
  `dataset.yaml` existentes (`.claude/evals/subagents/*/dataset.yaml`) e pontua
  `expected_behavior`/`must_not` automaticamente — automatiza o que o `README.md:79` diz
  ser manual. Expandir datasets p/ o agente principal (hoje só 4 subagentes têm).
- **Reusar integralmente `sql_evaluator_falses_service.py`** como motor de calibração:
  discordância humana → embedding → contra-exemplo few-shot no prompt do judge. Rastrear
  agreement judge↔humano ao longo do tempo (UI de revisão admin, reusar
  `routes/insights.py` + template).
- **Destrava**: confiança no `judge_score` (sem isso o sinal do E2 é ruidoso); regression
  testing antes de mudar prompt/modelo.
- **Dependência**: E2 (o judge a calibrar). Habilita Eixo F (governança: medir skills por
  qualidade, não só por uso) e Eixo A (sinal confiável vira directive).

### Fase E4 — Fusão + fechar o loop com o Eixo A
**Esforço M · Risco médio.**
- Função de fusão `fused_score` (ponderação calibrada empiricamente das fontes
  implícito/explícito/judge/ground-truth). Substituir o `resolution_rate` estrutural
  (`insights_service.py:229`) por qualidade real no `health_score`
  (`_calc_health_score`, `insights_service.py:368`) → custo POR ACERTO.
- Expor `fused_score` agregado a `pattern_analyzer` (priorizar turnos bons) e ao
  gate de `USE_OPERATIONAL_DIRECTIVES` (`feature_flags.py:215`) — heurística só promove a
  regra se os turnos que a usaram tiverem qualidade alta.
- **Destrava**: o flywheel gira. É o entregável que justifica E0-E3.
- **Dependência**: TODAS as anteriores + é a interface formal com o Eixo A (planejador) e
  Eixo D (ontologia — labels de qualidade por entidade de domínio).

### Não-sabido / não verificado
- Volume real de feedback explícito histórico em `AgentSession.data['feedbacks']` (não
  consultei o banco PROD; afeta quão rica é a calibração inicial do E3).
- Se o `_stop_hook` recebe `message_id`/turn boundaries de forma confiável em todos os
  paths (web vs Teams vs persistente) — precisa verificar antes do E0 para a chave do turno.
- Custo agregado do online judge em volume real (dimensiona infra do E2; não muda o desenho).

---

## Fontes externas (ancoragem do alvo em padrões 2026)

- LangChain — *How to Calibrate LLM-as-a-Judge with Human Corrections*
  (collect corrections → few-shot → track agreement; online com sampling rate; criteria/
  pairwise/reference-based). https://www.langchain.com/articles/llm-as-a-judge
- *Chapter 8: Agent Evaluation for LLMs — Tools, Trajectories, and LLM-as-Judge* (Medium,
  mai/2026). https://medium.com/@vinodkrane/chapter-8-agent-evaluation-for-llms-how-to-test-tools-trajectories-and-llm-as-judge-788f6f3e0d52
- *Production-Ready LLM Agents: Framework for Offline Evaluation* (Towards Data Science) —
  sequência offline→coverage→alignment→online.
  https://towardsdatascience.com/production-ready-llm-agents-a-comprehensive-framework-for-offline-evaluation/
- *When AIs Judge AIs: Agent-as-a-Judge* (arXiv 2508.02994) — judge com tool use/memória.
  https://arxiv.org/pdf/2508.02994
- LangChain *State of AI Agents 2026* (citado): qualidade = barreira #1 p/ deploy; sinais
  implícitos (re-pergunta/cópia/escalada) > star ratings.

## Contexto

Eixo do blueprint — evolucao do agente logistico. Tema: EIXO E — Observabilidade de Qualidade
