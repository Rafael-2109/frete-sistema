<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/blueprint-agente/eixos/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# EIXO B — DE ROTEADOR A PLANEJADOR

> **Papel:** EIXO B — DE ROTEADOR A PLANEJADOR.

## Indice

- [PARTE 1 — ESTADO REAL (com evidência)](#parte-1-estado-real-com-evidência)
  - [1.1 O loop é single-shot reativo. Não existe fase de planejamento.](#11-o-loop-é-single-shot-reativo-não-existe-fase-de-planejamento)
  - [1.2 Roteamento vive como PROSA. Zero enforcement.](#12-roteamento-vive-como-prosa-zero-enforcement)
  - [1.3 Task* tools (SDK 0.2.82+) são COSMÉTICOS para orquestração.](#13-task-tools-sdk-0282-são-cosméticos-para-orquestração)
  - [1.4 Auto-verificação: dois sensores passivos, zero atuador.](#14-auto-verificação-dois-sensores-passivos-zero-atuador)
  - [1.5 Subagentes são FOLHAS. Topologia fan-out de 2 níveis, sem coordenação.](#15-subagentes-são-folhas-topologia-fan-out-de-2-níveis-sem-coordenação)
  - [1.6 Retries existem — mas SÓ de conexão, nunca de tarefa.](#16-retries-existem-mas-só-de-conexão-nunca-de-tarefa)
  - [1.7 `plan_mode` existe e está fiado — mas é só "read-only", não plan-and-execute.](#17-plan_mode-existe-e-está-fiado-mas-é-só-read-only-não-plan-and-execute)
- [PARTE 2 — ALVO ARQUITETURAL (o teto)](#parte-2-alvo-arquitetural-o-teto)
  - [2.1 Tese de desenho: um MODO PLANEJADOR como super-loop determinístico](#21-tese-de-desenho-um-modo-planejador-como-super-loop-determinístico)
  - [2.2 Componentes nas 5 camadas do SDK](#22-componentes-nas-5-camadas-do-sdk)
  - [2.3 Contratos de dados (o que precisa existir como estado)](#23-contratos-de-dados-o-que-precisa-existir-como-estado)
  - [2.4 Fluxo de dados do super-loop](#24-fluxo-de-dados-do-super-loop)
  - [2.5 Por que isto é o TETO e não "uma melhoria"](#25-por-que-isto-é-o-teto-e-não-uma-melhoria)
- [PARTE 3 — CAMINHO INCREMENTAL (reaproveitando o existente)](#parte-3-caminho-incremental-reaproveitando-o-existente)
  - [Fase B0 — TRIAGE determinístico + flag de modo (esforço P, risco baixo)](#fase-b0-triage-determinístico-flag-de-modo-esforço-p-risco-baixo)
  - [Fase B1 — PlanState durável + Plan tools (promoção dos Task*) (esforço M, risco médio)](#fase-b1-planstate-durável-plan-tools-promoção-dos-task-esforço-m-risco-médio)
  - [Fase B2 — VERIFY como gate (promover os 2 sensores a atuadores) (esforço M, risco médio)](#fase-b2-verify-como-gate-promover-os-2-sensores-a-atuadores-esforço-m-risco-médio)
  - [Fase B3 — REPLAN com budget + escalonamento (esforço M, risco médio)](#fase-b3-replan-com-budget-escalonamento-esforço-m-risco-médio)
  - [Fase B4 — Verifier como subagente + scatter-gather paralelo (esforço G, risco médio)](#fase-b4-verifier-como-subagente-scatter-gather-paralelo-esforço-g-risco-médio)
  - [B5 — Prosa migra para tese (esforço P, risco baixo)](#b5-prosa-migra-para-tese-esforço-p-risco-baixo)
  - [Dependências cross-eixo](#dependências-cross-eixo)
  - [O que NÃO consegui verificar / ressalvas](#o-que-não-consegui-verificar-ressalvas)
  - [Primeiro passo de maior alavancagem](#primeiro-passo-de-maior-alavancagem)
- [Contexto](#contexto)

> Orquestração como MECANISMO, não como prosa.
> Lente de TETO: o objetivo é ELEVAR o que o agente pode fazer, não podar.
> Toda evidência citada como `arquivo:linha`. READ-ONLY.

---

## PARTE 1 — ESTADO REAL (com evidência)

### 1.1 O loop é single-shot reativo. Não existe fase de planejamento.

O dispatch inteiro do agente é uma única chamada de streaming: `stream_response()`
→ `_stream_response_persistent()` → SDK `ClaudeSDKClient`. Não há laço externo de
planejamento/execução/verificação. Quem decide "skill vs subagente vs SQL" é o
MODELO, lendo a prosa do `system_prompt.md`, dentro de UM turno multi-tool.

- `app/agente/sdk/client.py:1430` — `stream_response(...)` é a porta única; delega
  direto a `_stream_response_persistent` (`client.py:1474`). Não há nó "planner",
  "executor" ou "replanner".
- `_build_options` (`client.py:1492`) monta `ClaudeAgentOptions` e **não injeta
  `max_turns`** por padrão (`client.py:1614-1617`, comentário "sem limite"). O loop
  ReAct interno do CLI roda até `end_turn`. É um ReAct puro, sem plano upfront.

**Conclusão**: a "inteligência de orquestração" não é um componente — é texto. O
modelo pode segui-lo ou não, e nada no harness mede se seguiu.

### 1.2 Roteamento vive como PROSA. Zero enforcement.

O `system_prompt.md` carrega quatro blocos de orquestração, TODOS instrução textual:

- `<routing_strategy>` — `system_prompt.md:664-718`. `domain_detection`,
  `boundary name="faturamento"` (`:673`), `boundary name="baseline_financeiro"`
  (`:683`), `routing_confidence` (`:697`). Tudo "se ambíguo, pergunte"; nenhum gate
  determinístico verifica se o domínio foi de fato detectado.
- `<coordination_protocol>` — `system_prompt.md:721-733`. "Prefira resolver direto…
  delegue quando cross-módulo, 4+ operações…". É uma heurística sugerida ao modelo.
- `<output_verification>` — `system_prompt.md:727-732`. "Se decisão CRÍTICA…
  cross-check… Desconfie de respostas sem citação… inclua no prompt 'Escreva
  findings em /tmp/subagent-findings/'". **Verificação é instrução, não passo.**
- `<task_management>` — `system_prompt.md:822-838`. Manda usar TaskCreate/Update;
  `<delegation_pattern>` (`:830`) descreve 4 passos manuais que o modelo deve
  executar disciplinadamente para que a UI mostre progresso.

O `model_router.select_model` (`sdk/model_router.py:104`) é o **único classificador
determinístico de complexidade que já existe** — escolhe Opus vs Sonnet por
`word_count > 15` → `"prompt_complexo"` (`model_router.py:150-151`) e por patterns de
intent. Mas seu output só troca o MODELO; não dispara modo de planejamento nem
qualquer mudança de fluxo de orquestração.

### 1.3 Task* tools (SDK 0.2.82+) são COSMÉTICOS para orquestração.

O agente tem `TaskCreate/TaskUpdate/TaskGet/TaskList` (SDK 0.2.82+, substituiu
TodoWrite). Mas o backend só os parseia para PINTAR a UI:

- `client.py:637-666` — detecta os tool names e chama `_build_task_event`.
- `_build_task_event` (`client.py:696-739`) — produz `{action: created|updated|
  snapshot, ...}` que vira evento SSE `task_event`. **Nenhuma lógica lê a lista de
  tasks para forçar sequência, bloquear avanço, ou verificar conclusão.** O CLI
  mantém o estado das tasks; o nosso backend é observador passivo.

Ou seja: o "plano" (lista de tasks) existe como artefato visual, não como contrato
executável. Se o modelo pular uma task, ninguém percebe.

### 1.4 Auto-verificação: dois sensores passivos, zero atuador.

Há DOIS mecanismos de verificação, ambos **advisory append-only / fire-and-forget**:

**(a) `_self_correct_response`** — `client.py:792-857`. Pós-resposta, chama Sonnet
4.6 para checar SÓ inconsistência aritmética, SÓ se há tabela markdown
(`re.search(r'\|.*\d.*\|')`, `:819`) e `len > 500` (`:814`). Quando acha erro, o
resultado é **anexado como caveat** ao texto:
`client.py:1378-1383` → `f"\n\n⚠️ Observação de validação: {correction}"`. NÃO
re-gera, NÃO re-planeja, NÃO instrui o modelo a corrigir — empurra a ressalva pro
usuário. E está **OFF por padrão**: `USE_SELF_CORRECTION` default `false`
(`feature_flags.py:48`).

**(b) Validador anti-alucinação de subagente** — `workers/subagent_validator.py`.
Enfileirado no `SubagentStop` (`hooks.py:870-898`), roda Haiku, dá score 0-100.
Quando `score < threshold` (default 70, `feature_flags.py:520`) só faz
`_push_validation_event` → badge SSE (`subagent_validator.py:194-195`). **NÃO bloqueia
a resposta, NÃO re-roda o subagente, NÃO informa o orquestrador.** É telemetria de UI.
O orquestrador (modelo principal) nunca vê esse veredito.

### 1.5 Subagentes são FOLHAS. Topologia fan-out de 2 níveis, sem coordenação.

- Os 13 subagentes (`.claude/agents/*.md`) **não têm `Agent` nem `Task` tool**
  (frontmatter `tools:` só Read/Bash/Glob/Grep + mcp memory; ex.
  `analista-carteira.md:4`). Logo: sem recursão, sem sub-delegação, sem
  scatter-gather, sem debate/cross-check entre eles. Único topo: principal → folha.
- `_SUBAGENT_DENY_POLICIES` está **vazio** (`permissions.py:263` = `{}`), então o
  gate per-subagent (`permissions.py:438-447`) é inerte hoje.
- O `can_use_tool` (`permissions.py:395`) é puramente segurança/safety: deny-list
  vazia, allowlist de write-path (`:483`), AskUserQuestion (`:561`), aviso de ação
  destrutiva, gating de skills WRITE de estoque (`_classify_estoque_restricao`,
  `:320`). **Nenhum gate de plano/checkpoint/verificação de conclusão.**
- O findings do subagente é lido por `get_subagent_summary`/`subagent_reader`
  (`hooks.py:843-852`) APENAS para custo e badge de UI — o orquestrador recebe o
  resumo do subagente via contexto do SDK (mecanismo do CLI), nunca o lê
  programaticamente para verificar/replanejar.

### 1.6 Retries existem — mas SÓ de conexão, nunca de tarefa.

`grep retry client.py` → tudo é resiliência de transporte: `rate_limit`
(`client.py:1090`), `context_overflow` (`:1096`), `retry SEM resume` por sessão
quebrada (`:2191, :2478-2498, :2533-2544`), evict de client morto do pool (`:2573`).
**Zero retry de passo de tarefa, zero re-planejamento em falha de skill/subagente,
zero reflexão.** Se um subagente falha ou retorna lixo, o turno simplesmente segue
ou termina.

### 1.7 `plan_mode` existe e está fiado — mas é só "read-only", não plan-and-execute.

`plan_mode` cruza todo o stack: `chat.js` → `routes/chat.py:166,421,570,1075` →
`client.py:1436` → `_build_options:1549` → `permission_mode = "plan"`. Mas no SDK
isso significa **modo somente-leitura** (não executa writes). NÃO produz um artefato
de plano aprovável, NÃO há gate de "aprovar plano → executar". É um interruptor de
permissão, não um orquestrador.

> **Síntese do estado**: o agente tem TODOS os primitivos de um "deep agent" 2026
> (planning-tool=Task*, subagent-spawn=Agent, filesystem=/tmp+S3, skills=47), mas
> nenhum deles está LIGADO COMO MECANISMO de orquestração. Planning é cosmético,
> verificação é advisory e desligada, subagentes são folhas sem coordenação,
> re-planejamento inexiste. Hoje o **Claude Code (este harness) orquestra melhor o
> próprio agente do que ele se orquestra** — exatamente a tese B.

---

## PARTE 2 — ALVO ARQUITETURAL (o teto)

### 2.1 Tese de desenho: um MODO PLANEJADOR como super-loop determinístico

O padrão de classe mundial 2026 para tarefas complexas é **Plan-and-Execute outer
loop com executores ReAct e um Reflection/verification gate** — exatamente o que
frameworks como Deep Agents (planning + task subagents + filesystem + skills) e
LangGraph (ciclo condicional com critic + router + budget de correção)
consolidaram ([Deep Agents — LangChain](https://docs.langchain.com/oss/python/deepagents/overview);
[Plan-and-Execute — LangChain](https://blog.langchain.com/planning-agents/);
[ReAct vs Plan-Execute vs Reflexion 2026](https://dev.to/gabrielanhaia/react-plan-and-execute-or-reflection-the-three-agent-patterns-every-engineer-needs-in-2026-355p)).

O agente NÃO precisa virar LangGraph. Ele precisa de uma **camada de orquestração
determinística por cima do SDK** que transforme os primitivos cosméticos atuais em
mecanismo. O modo simples (single-shot ReAct atual) permanece como caminho rápido;
o modo PLANEJADOR é acionado para tarefas complexas.

```
                       ┌─────────────────────────────────────────────────┐
  prompt ─► TRIAGE ───►│  caminho SIMPLES (ReAct atual, 1 turno)          │─► resposta
   (det.)   (model_    └─────────────────────────────────────────────────┘
            router +    ┌─────────────────────────────────────────────────────────────┐
            complexity  │  caminho PLANEJADOR (super-loop determinístico)               │
            score)  ───►│                                                               │
                        │  ① PLAN  → plano estruturado (JSON: steps[, deps, verify])    │
                        │  ② (opcional) APROVAÇÃO humana do plano (reusa plan_mode UI)   │
                        │  ③ EXECUTE step k → skill | subagente | SQL                    │
                        │        ↑                              │                        │
                        │        │  ④ VERIFY (gate real, hook) ─┘                        │
                        │        │     pass → próximo step                               │
                        │        └──── fail → ⑤ REPLAN (budget N) ── escalate p/ humano  │
                        │  ⑥ SYNTHESIZE (consolida steps + verifica plano completo)      │
                        └─────────────────────────────────────────────────────────────┘
```

### 2.2 Componentes nas 5 camadas do SDK

| Camada SDK | Componente do ALVO | Papel |
|---|---|---|
| **5. Control (hooks + can_use_tool)** | **PlanState** (durable, JSONB em `AgentSession.data`) + **VerifyGate hook** | O coração: o plano vira estado persistido; o `PostToolUse`/Stop hook lê o step corrente, verifica e roteia para next/replan. Determinístico. |
| **4. Subagents** | **Verifier subagent** (Haiku/Sonnet adversarial) + subagentes-executores existentes | Verificação vira PASSO: um verifier-subagente (não folha — invocado pelo loop) julga o output do step com rubrica. Reusa `subagent_validator` promovido de sensor a atuador. |
| **3. Skills** | Skills como STEP-EXECUTORS tipados | Cada step do plano referencia uma skill/subagente com `expected_artifact`; skills WRITE já têm `--dry-run` (ex. todas as skills Odoo), que vira o "verify before commit" natural. |
| **2. Tools** | **Plan tools** (`PlanCreate`/`PlanStep`/`PlanVerify`/`PlanReplan`) — promoção dos Task* | Substituem os Task* cosméticos por tools que o BACKEND interpreta como contrato (não só pinta UI). |
| **1. System prompt** | Prosa REDUZIDA — vira tese, não algoritmo | `routing_strategy`/`coordination_protocol`/`output_verification` migram de "instrução que o modelo pode ignorar" para "comportamento garantido pelo harness"; o prompt só descreve QUANDO planejar. |

### 2.3 Contratos de dados (o que precisa existir como estado)

**PlanState** (novo, persistido em `AgentSession.data['plan']` — JSONB, reusa R7
`flag_modified`):
```jsonc
{
  "plan_id": "uuid", "goal": "audita carteira completa e comunica PCP",
  "status": "executing|done|failed|awaiting_approval",
  "steps": [
    { "id": 1, "kind": "subagent|skill|sql", "target": "analista-carteira",
      "input_summary": "P1 entregas vencidas", "depends_on": [],
      "verify": { "rubric": "tem citação de fonte? números batem?",
                  "verifier": "adversarial|arithmetic|none" },
      "status": "pending|running|verified|failed|skipped",
      "attempts": 0, "max_attempts": 2,
      "artifact_ref": "/tmp/subagent-findings/step1.json",
      "verdict": { "score": 0-100, "reasons": [...] } }
  ],
  "replan_budget": 3, "replans_used": 0
}
```

**Contrato de verificação** (o gate real): cada step declara COMO é verificado.
Três verifiers, escolhidos pelo `kind`/criticidade:
1. `arithmetic` — promove `_self_correct_response` (`client.py:792`) de advisory para
   gate que BLOQUEIA e força retry com a correção no contexto.
2. `adversarial` — promove `subagent_validator` (Haiku, `workers/subagent_validator.py`)
   de badge para veredito que o loop CONSOME: `score < threshold` → step `failed` →
   replan.
3. `none` — steps triviais (consulta read-only de baixo risco).

### 2.4 Fluxo de dados do super-loop

1. **TRIAGE** (determinístico, zero LLM extra): reusa `model_router.select_model`
   (`model_router.py:104`). Se `reason == "prompt_complexo"` OU heurística de
   multi-domínio/multi-step → entra modo PLANEJADOR. Senão, single-shot atual.
2. **PLAN**: 1 chamada ao modelo com `output_format` (structured output nativo do SDK
   — já suportado, `client.py:1463,1501`) produzindo o `PlanState.steps`. Plano é
   persistido ANTES de executar (durabilidade — sobrevive a crash/resume, reusa
   `PostgresSessionStore`).
3. **APROVAÇÃO** (opcional, reusa `plan_mode`): se step contém WRITE crítico, emite
   o plano via AskUserQuestion-like e aguarda OK (mecanismo `pending_questions.py` +
   Redis cross-worker, R-MULTIWORKER, já existe).
4. **EXECUTE**: para cada step (respeitando `depends_on`; independentes em paralelo —
   o `coordination_protocol:724` "independentes → paralelo" vira realidade no
   harness): invoca skill/subagente. Subagente escreve em `artifact_ref`
   (`/tmp/subagent-findings/`, protocolo já documentado em `output_verification:731`).
5. **VERIFY** (PASSO real, não instrução): hook lê `artifact_ref`, roda o verifier
   declarado. `pass` → marca `verified`, avança. `fail` → step `failed`.
6. **REPLAN**: em falha, se `replans_used < replan_budget` (budget de correção é
   requisito de produção — [Reflexion/PRM 2026](https://zylos.ai/research/2026-05-12-agent-self-correction-reflexion-to-prm)),
   re-chama o planner com o veredito + reflexão verbal anexados (Reflexion: carrega
   lição adiante). Senão → `escalate` (define `escalated_to_human=True`, que HOJE é
   campo morto reservado pra "Fase D" em `AgentInvocationMetric`).
7. **SYNTHESIZE**: consolida os artefatos verificados em resposta final; verificação
   de plano-completo (todos steps `verified`?) antes do `done`.

### 2.5 Por que isto é o TETO e não "uma melhoria"

- **Verificação deixa de ser fé**: o veredito do verifier É a aresta do grafo que
  decide avançar/repetir — o padrão orchestrator+verifier adversarial de 2026
  ([Agent-as-a-Judge survey](https://arxiv.org/pdf/2601.05111);
  [Verified Multi-Agent Orchestration plan-execute](https://arxiv.org/pdf/2603.11445)).
- **Falha vira recuperação, não morte**: replanejamento com budget + escalonamento
  humano fecha o loop que hoje termina em silêncio.
- **Plano é durável e auditável**: sobrevive a resume/crash, é inspecionável, e gera
  o **sinal de qualidade por-step** que o Eixo E precisa para fechar o flywheel.
- **Subagentes viram nós coordenados**: scatter-gather paralelo real + verifier
  como nó, não folhas isoladas.

---

## PARTE 3 — CAMINHO INCREMENTAL (reaproveitando o existente)

> Princípio: cada fase liga UM primitivo cosmético existente como mecanismo, sem
> reescrever o stream. O modo SIMPLES nunca é tocado (zero risco de regressão no
> caminho quente diário).

### Fase B0 — TRIAGE determinístico + flag de modo (esforço P, risco baixo)
- **O que destrava**: ponto de entrada do modo planejador. Em `_stream_response_persistent`,
  antes do loop, chamar `model_router.select_model` (já existe, `model_router.py:104`)
  + heurística multi-domínio; setar `plan_track=True` quando `prompt_complexo`.
- **Reusa**: `model_router` inteiro; `feature_flags.py` para a flag
  `AGENT_PLANNER_MODE` (default OFF, padrão de adoção do projeto).
- **Risco**: baixo — sem flag, comportamento idêntico ao atual.
- **Depende de**: nada.

### Fase B1 — PlanState durável + Plan tools (promoção dos Task*) (esforço M, risco médio)
- **O que destrava**: plano deixa de ser cosmético. Backend passa a INTERPRETAR a
  lista de tasks como contrato persistido.
- **Reusa**: parser `_build_task_event` (`client.py:696`) — estender de "emitir
  evento UI" para "materializar/atualizar `PlanState` em `AgentSession.data`"
  (R7 `flag_modified`, R10 persistência). `output_format` nativo (`client.py:1463`)
  para o planner produzir steps tipados. `PostgresSessionStore` para durabilidade.
- **Risco**: médio — toca persistência JSONB; mitigável atrás da flag.
- **Depende de**: B0.

### Fase B2 — VERIFY como gate (promover os 2 sensores a atuadores) (esforço M, risco médio)
- **O que destrava**: auto-verificação vira PASSO. É a maior alavanca de qualidade.
- **Reusa DIRETAMENTE**:
  - `_self_correct_response` (`client.py:792`) — mudar o sink: em vez de anexar
    caveat (`client.py:1378-1383`), retornar veredito ao loop → força retry do step
    com a correção no contexto. Ligar `USE_SELF_CORRECTION` (hoje OFF, `:48`).
  - `subagent_validator.validate_subagent_output` (`workers/subagent_validator.py:114`)
    — promover de `_push_validation_event` (badge) para veredito SÍNCRONO consumido
    pelo loop quando o step é `kind=subagent`. O score 0-100 + threshold (`:520`) já
    existem.
- **Risco**: médio — verifier mal calibrado gera loops (mitigar com `replan_budget`
  + o "self-critique paradox": verificador erra onde mais importa
  ([Snorkel 2026](https://snorkel.ai/blog/the-self-critique-paradox-why-ai-verification-fails-where-its-needed-most/)) →
  começar com verifiers `arithmetic` (alta precisão) e `none`, ligar `adversarial`
  só em steps críticos).
- **Depende de**: B1 (precisa de PlanState com `verify` declarado). **Produz o sinal
  de qualidade por-step que o Eixo E consome.**

### Fase B3 — REPLAN com budget + escalonamento (esforço M, risco médio)
- **O que destrava**: falha vira recuperação. Fecha o loop.
- **Reusa**: o padrão de retry-resiliente já existe em `client.py` (`:2478+`) — copiar
  a DISCIPLINA (budget, transparência) para nível de tarefa. `escalated_to_human`
  (campo morto em `AgentInvocationMetric`, "Fase D") finalmente recebe escrita.
  `pending_questions.py` (R4/R-MULTIWORKER) para a aprovação humana do replano.
- **Risco**: médio — risco de availability por loop infinito; budget + escalation
  path são requisito ([RAC, budget de correção 2026](https://arxiv.org/html/2605.03409)).
- **Depende de**: B2.

### Fase B4 — Verifier como subagente + scatter-gather paralelo (esforço G, risco médio)
- **O que destrava**: coordenação multi-agente real. Subagentes-folha viram nós;
  steps independentes rodam em paralelo de verdade (não só "instrução para paralelo").
- **Reusa**: os 13 subagentes existentes como executores; `coordination_protocol:724`
  vira mecanismo; `subagent_reader`/`get_subagent_summary` (`hooks.py:843`) passa a
  ser LIDO pelo loop (não só p/ custo). Introduzir um `verifier` subagente dedicado
  (Sonnet, rubrica) para os steps `adversarial` — padrão orchestrator+prover+verifier
  ([adversarial verification 2026](https://arxiv.org/abs/2602.09341)).
- **Risco**: médio-alto — paralelismo + verificação adversarial multiplica custo de
  tokens; a LENTE DE TETO diz que isso é legítimo (custo dimensiona infra, não
  decide a capacidade) — mas exige `replan_budget` e teto de fan-out.
- **Depende de**: B1-B3. Cross-eixo F (governança: lifecycle/namespacing dos
  subagentes-executores e do verifier).

### B5 — Prosa migra para tese (esforço P, risco baixo)
- **O que destrava**: coerência. `routing_strategy`/`coordination_protocol`/
  `output_verification`/`task_management` no `system_prompt.md:664-838` ENCOLHEM:
  param de algoritmo (que o modelo pode ignorar) para descrição de QUANDO o harness
  ativa o planejador. Reduz tokens e remove o conflito "instrução vs mecanismo".
- **Reusa**: o próprio prompt; só poda.
- **Risco**: baixo (feito por último, após o mecanismo provar-se).
- **Depende de**: B0-B4 estáveis.

### Dependências cross-eixo
- **CONSOME do Eixo D (ontologia)**: o TRIAGE e o planner precisam de um modelo de
  mundo Nacom para decompor metas em steps com `target` corretos (qual subagente/
  skill, quais entidades). Plano de qualidade exige ontologia, não regex de domínio.
- **PRODUZ para o Eixo E (qualidade)**: o veredito por-step (B2) + outcome de replan/
  escalonamento (B3) são EXATAMENTE o "sinal de qualidade" que hoje não existe
  (observabilidade só mede custo/latência). B preenche `escalated_to_human` /
  `user_correction_received` (campos mortos da Fase D em `AgentInvocationMetric`).
- **Liga ao Eixo A (flywheel)**: com sinal de qualidade real (E) e atuadores (B),
  `USE_OPERATIONAL_DIRECTIVES` (OFF, `feature_flags.py:215`) pode promover heurística
  de plano que funcionou → diretriz ativa.
- **Toca Eixo F**: B4 introduz um subagente verifier e usa subagentes como
  executores — exige o modelo de escopo/lifecycle de F.

### O que NÃO consegui verificar / ressalvas
- Não medi se o SDK 0.2.87 permite invocar um subagente DE DENTRO de um hook
  síncrono (verifier-como-passo, B4); pode exigir orquestrar o verifier no nível do
  `_stream_response_persistent` (loop Python externo) em vez de hook puro. A
  arquitetura suporta ambos; a escolha é de implementação.
- Não confirmei o custo real de tokens do modo planejador no volume Nacom — mas pela
  LENTE DE TETO isso dimensiona infra, não decide a capacidade.
- `output_format` (structured output) está fiado (`client.py:1463`) mas não verifiquei
  se já é exercitado em produção — assumi disponível para o planner.

### Primeiro passo de maior alavancagem
**Fase B2 sobre B1 mínimo**: ligar `USE_SELF_CORRECTION` e redirecionar seu sink de
"anexar caveat" (`client.py:1378-1383`) para "veredito que força retry do step". É a
mudança que converte o primeiro sensor em atuador e prova o conceito de verificação-
como-passo com o MENOR raio de impacto — todo o aparato (Sonnet validator, score,
detecção de tabela) já existe; falta só fechar a aresta do grafo.

## Contexto

Eixo do blueprint — evolucao do agente logistico. Tema: EIXO B — DE ROTEADOR A PLANEJADOR
