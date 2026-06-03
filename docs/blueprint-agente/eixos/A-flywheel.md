<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/blueprint-agente/eixos/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# EIXO A — FLYWHEEL DE APRENDIZADO

> **Papel:** EIXO A — FLYWHEEL DE APRENDIZADO.

## Indice

- [PARTE 1 — ESTADO REAL (com evidência)](#parte-1-estado-real-com-evidência)
  - [1.1 O que existe e roda HOJE (sensores — ricos)](#11-o-que-existe-e-roda-hoje-sensores-ricos)
  - [1.2 ONDE O LOOP QUEBRA — quatro rupturas, da mais grave à menos](#12-onde-o-loop-quebra-quatro-rupturas-da-mais-grave-à-menos)
  - [1.3 Resposta à pergunta central](#13-resposta-à-pergunta-central)
- [PARTE 2 — ALVO ARQUITETURAL (o teto)](#parte-2-alvo-arquitetural-o-teto)
  - [2.1 Componente novo central: `quality_signal` (a camada Coach que falta)](#21-componente-novo-central-quality_signal-a-camada-coach-que-falta)
  - [2.2 `importance_score` vira saída, não entrada (fecha Ruptura #4)](#22-importance_score-vira-saída-não-entrada-fecha-ruptura-4)
  - [2.3 Promoção automática gated por eval (liga Ruptura #2 com segurança)](#23-promoção-automática-gated-por-eval-liga-ruptura-2-com-segurança)
  - [2.4 Eval-in-the-loop: golden dataset deixa de ser manual (fecha Ruptura #5)](#24-eval-in-the-loop-golden-dataset-deixa-de-ser-manual-fecha-ruptura-5)
  - [2.5 Encaixe nas 5 camadas do SDK](#25-encaixe-nas-5-camadas-do-sdk)
- [PARTE 3 — CAMINHO INCREMENTAL](#parte-3-caminho-incremental)
  - [Fase A0 — Ativar os sinais GRÁTIS que já são coletados e jogados fora (P, risco baixo)](#fase-a0-ativar-os-sinais-grátis-que-já-são-coletados-e-jogados-fora-p-risco-baixo)
  - [Fase A1 — Construir `quality_signal` (batch judge + outcome) (M, risco médio)](#fase-a1-construir-quality_signal-batch-judge-outcome-m-risco-médio)
  - [Fase A2 — Re-calibrar `importance`/`effective_count` por outcome (M, risco médio)](#fase-a2-re-calibrar-importanceeffective_count-por-outcome-m-risco-médio)
  - [Fase A3 — Eval runner automatizado + gate no D8 (M, risco médio-alto)](#fase-a3-eval-runner-automatizado-gate-no-d8-m-risco-médio-alto)
  - [Fase A4 — Promoção automática gated de diretrizes (G, risco alto)](#fase-a4-promoção-automática-gated-de-diretrizes-g-risco-alto)
  - [Fase A5 — Golden dataset auto-crescente (P contínuo, risco baixo)](#fase-a5-golden-dataset-auto-crescente-p-contínuo-risco-baixo)
- [RESUMO EXECUTIVO](#resumo-executivo)
- [Contexto](#contexto)

> Blueprint arquitetural. Lente de TETO: o agente JÁ tem mais maquinaria de aprendizado
> que a maioria dos produtos de IA em produção em 2026. O problema não é "falta de
> capacidade" nem "volume baixo" — é que o **circuito não fecha sobre QUALIDADE**.
> Ele aprende a ser mais *consistente consigo mesmo*, não a ser mais *correto*.

---

## PARTE 1 — ESTADO REAL (com evidência)

### 1.1 O que existe e roda HOJE (sensores — ricos)

O agente tem um sistema de aprendizado de 3 anéis, todos **ATIVOS em produção** (flags default ON):

**Anel 1 — Extração pós-sessão (descritivo→prescritivo):**
- `pattern_analyzer.extrair_conhecimento_sessao()` (empresa, user_id=0) e
  `extrair_insights_pessoais_sessao()` (pessoal) rodam em daemon thread a cada exchange
  (min 3 msgs), via Sonnet. Taxonomia de 5 níveis: só níveis 3-5
  (diagnóstico/armadilha/heurística) viram memória. Output PRESCRITIVO obrigatório
  (`pattern_analyzer.py:835-1550`; gotcha doc em `services/CLAUDE.md:64-99`).
- Dedup semântico pré-save (`_find_similar_empresa_memory`, threshold 0.80).
- Flags `USE_POST_SESSION_EXTRACTION` / `USE_POST_SESSION_PERSONAL_EXTRACTION` = ON
  (`feature_flags.py:130,147`).

**Anel 2 — Feedback de eficácia de memória (o sinal interno):**
- `memory_injection.py:1230` incrementa `usage_count` toda vez que injeta uma memória.
- `routes/_helpers.py:457 _track_memory_effectiveness()` incrementa `effective_count`
  pós-turno. Invocado de `chat.py:1854-1857` com os IDs reais injetados
  (`_client._last_injected_memory_ids`). **O dado É coletado.**
- `USE_COLD_MOVE` move para tier frio (não injetada, mas buscável) memórias com
  `usage_count >= 20 E effective_count/usage_count < 0.10` (`feature_flags.py:239-241`,
  `memory_consolidator.py:132-141`). Memória ruim "esfria"; após 90d, GC permanente
  (`USE_COLD_GC`, `feature_flags.py:251`).

**Anel 3 — Diálogo de melhoria com o Claude Code dev (o único ATUADOR de código real):**
- `improvement_suggester.executar_batch_improvement()` roda 2x/dia (APScheduler módulo 25,
  07:00 e 10:00 — `sincronizacao_incremental_definitiva.py:87-88,1837-1868`). Sonnet lê
  sessões das últimas 8h e gera 0-5 sugestões prescritivas em 6 categorias
  (skill_suggestion, instruction_request, prompt_feedback, gotcha_report,
  memory_feedback, skill_bug) → grava `AgentImprovementDialogue` (`models.py:1137`).
- O cron **D8** (`scripts/maintenance/run_d8_cron.sh`, 11:00) dispara
  `claude -p` headless com `dominio-8-improvement-dialogue.md`. O Claude Code dev LÊ as
  sugestões pendentes, **implementa via feature-dev, commita DIRETO em main e pusha**
  (`dominio-8-improvement-dialogue.md:108-159`). **Este é o único ponto onde aprendizado
  vira mudança de comportamento no código.**
- O agente também registra sugestões em real-time via MCP tool `register_improvement`
  (R9 do system_prompt).

**Telemetria (Fase A — em coleta):**
- `AgentInvocationMetric` (`models.py:1597`): 1 linha por spawn→stop de subagent.
  Captura cost/duration/tokens/turns. Dashboard admin com 10 endpoints
  (`metrics_dashboard_service.py`), anomaly detection por cost/duration
  (`get_anomalies`, linha 380).

### 1.2 ONDE O LOOP QUEBRA — quatro rupturas, da mais grave à menos

**RUPTURA #1 (a raiz) — O sinal de "qualidade" não mede qualidade.**
Há DOIS proxies, e os dois medem *atividade/consistência*, não *correção*:

- **"effective_count"** (`_helpers.py:497-501,532`) = similaridade cosseno Voyage entre
  o TEXTO da memória injetada e o TEXTO da resposta do agente. Ou seja: "a resposta
  ECOOU a memória?". Uma resposta confiante e ERRADA que cita a memória conta como
  "efetiva". O sinal recompensa eco, não acerto.
- **"resolution_rate"** (`insights_service.py:210-246`) = sessão teve ≥4 mensagens E usou
  ao menos uma tool. `_count_resolved` (linha 229) **não olha o conteúdo nem o desfecho** —
  só "houve ida-e-volta com tool". Um pedido mal respondido que o usuário abandonou
  frustrado, se teve 4 msgs e 1 tool, conta como "resolvido".
- `health_score` (`insights_service.py:368-401`) = `0.35*resolution_rate +
  0.25*(100-friction) + ...`. Construído sobre os dois proxies acima → herda a cegueira.

**Consequência:** o sistema documenta a própria falha. O comentário do flag
`USE_OPERATIONAL_DIRECTIVES` (`feature_flags.py:209-212`) cita a meta-heurística id=300
"Memórias de usuário devem funcionar como protocolo ativo" com **12% de efetividade** —
mas esses 12% são "12% de eco", não "12% de utilidade comprovada". O sistema não sabe
distinguir uma memória que mudou o desfecho de uma que foi ignorada.

**RUPTURA #2 — O atuador determinístico mais potente está DESLIGADO.**
`USE_OPERATIONAL_DIRECTIVES=false` (`feature_flags.py:215`). Quando ligado,
`_build_operational_directives()` (`memory_injection.py:420`) promoveria heurísticas
empresa de alta importância (`importance_score >= 0.7`, ordenadas por `effective_count`)
de "contexto passivo" (`<user_memories>`) para "diretriz obrigatória"
(`<operational_directives priority="critical">`), que o R0d do system_prompt
(`system_prompt.md:144`) instrui o agente a tratar como REGRA. **Este é exatamente o
"Distill→Deploy" do flywheel** — e está desligado porque (a) o critério de promoção é
`importance_score` (campo definido por quem? — ver Ruptura #4) ordenado por `effective_count`
(= eco, Ruptura #1); promover com base num sinal cego é arriscado, então ninguém liga.
O atuador depende de um sensor confiável que não existe → fica OFF por segurança.

**RUPTURA #3 — A "verificação" do diálogo de melhoria não mede impacto.**
O lifecycle de `AgentImprovementDialogue` é `proposed→responded→verified→closed`
(`models.py:1144`). Mas `verified` vem de `_evaluate_responses_batch()`
(`improvement_suggester.py:415-482`): o Sonnet recebe `implementation_notes` + sessões
recentes e julga "isso parece resolvido?". **Não há baseline antes / re-medição depois.**
Uma mudança de prompt pode ter shipado, o Sonnet diz "verified", e ninguém sabe se a
métrica de qualidade subiu — porque (Ruptura #1) não há métrica de qualidade. O loop
fecha no *commit do código*, nunca no *efeito do código*.

**RUPTURA #4 — `importance_score` é entrada, não saída do aprendizado.**
O critério de promoção a diretriz e de seleção em todo o pipeline de injeção
(`memory_injection.py:940,997,1168` usam `0.3*decay + 0.3*importance + 0.4*similarity`)
depende de `importance_score`. Mas `importance` é setado na CRIAÇÃO da memória (pela
extração Sonnet) e não é re-calibrado pelo desfecho. Memória nasce "importante" por
julgamento de um Sonnet que nunca viu se ela funcionou. O número que governa tudo é uma
*aposta inicial*, não um *aprendizado*.

**RUPTURA #5 — O golden dataset existe mas está fora do circuito.**
`.claude/evals/subagents/` tem datasets para 4 agentes (analista-carteira,
auditor-financeiro, controlador-custo-frete, gestor-motos-assai), formato
expected_behavior/must_not. Mas o README é explícito: **"Julgamento é MANUAL (não
automatizado por LLM)"** (`README.md:79`) e roda "antes de commit / release"
(linha 85) — ou seja, depende de o dev lembrar. Não há `run_eval.py` automatizado, não há
CI gate, não há ligação com o D8. O D8 commita direto em main (`dominio-8.md:13`) **sem
rodar eval nenhuma**. O ativo de ground-truth mais valioso do sistema é um documento que
um humano lê de vez em quando.

**RUPTURA #6 — Sinais humanos explícitos são capturados e jogados fora.**
`routes/feedback.py:66-90`: `positive`/`negative` (os botões 👍👎 que JÁ existem em
`chat.js:2681-2689`) são "apenas logados (analytics futuro)". `escalated_to_human` e
`user_correction_received` em `AgentInvocationMetric` (`models.py:1647-1648`) têm
default e **nunca são escritos** ("ficam para Fase D"). Os dois sinais de recompensa mais
limpos e baratos do sistema — o usuário disse explicitamente "bom"/"ruim", e a correção
explícita do usuário — estão inertes.

### 1.3 Resposta à pergunta central

**O sistema aprende sobre si mesmo de forma fechada, ou só acumula dados que ninguém
retroalimenta?**

Resposta precisa: **o circuito está fisicamente conectado de ponta a ponta — sensor
(extração) → memória (agent_memories) → atuador (D8 muda código; cold-move muda injeção)
→ re-leitura — MAS o "fio de qualidade" que deveria alimentar toda decisão de promoção e
verificação está desconectado.** O loop gira, porém sobre um sinal de recompensa que mede
ECO e ATIVIDADE, não ACERTO. Por isso o operador (Rafael/dev) ainda é o termômetro real:
ele percebe que o agente errou e abre uma sessão para corrigir. O sistema não fecha o
último centímetro: "isto melhorou o desfecho?".

Em termos do flywheel canônico **Execute → Coach → Distill → Improve**
([Augment Code](https://www.augmentcode.com/guides/agent-learning-flywheel)):
Execute=✅ (sessões logadas), Distill=✅ (extração prescritiva), Improve=✅ (D8 + cold-move).
**O elo quebrado é Coach** — "improvement signals" de qualidade (environmental outcome,
LLM-as-judge calibrado, human correction) não existem como número confiável.

---

## PARTE 2 — ALVO ARQUITETURAL (o teto)

Um **flywheel eval-driven** onde o sinal de recompensa é a QUALIDADE da trajetória, e onde
promoção de heurística → diretriz é AUTOMÁTICA, GATED por eval, e RE-MEDIDA. O teto não é
"adicionar um judge"; é tornar a qualidade a moeda que circula em todo o loop.

### 2.1 Componente novo central: `quality_signal` (a camada Coach que falta)

Uma tabela `agent_turn_quality` (1 linha por turn assistant relevante) que **funde três
fontes de sinal**, no espírito do "Coach" de 3 canais do flywheel:

| Canal | Fonte no sistema | Custo | Confiança |
|---|---|---|---|
| **Humano explícito** | `feedback.py` 👍/👎/correction (JÁ coletado) + `user_correction_received` | zero | alta (ground truth) |
| **Outcome ambiental** | derivado de comportamento: sessão abandonada pós-resposta? usuário re-perguntou o mesmo (friction)? tool falhou e não recuperou? operação Odoo revertida (cross-ref `operacao_odoo_auditoria`, R9 hook)? | zero | média |
| **LLM-as-judge** | judge Sonnet/Haiku sobre a trajetória (tool certa? respondeu o objetivo? citou fonte? alucinção?) — rodando em batch, NÃO inline | ~$0.002/turn | média-alta (85% concordância c/ humano, [Confident AI](https://www.confident-ai.com/blog/why-llm-as-a-judge-is-the-best-llm-evaluation-method)) |

Score final = combinação ponderada, com **humano sobrescrevendo** judge quando presente
(human-in-loop como teto de verdade). Calibração obrigatória: spot-check humano de 5-10%
das notas do judge ([Evidently](https://www.evidentlyai.com/llm-guide/llm-as-a-judge)).

Este score é a moeda. Tudo abaixo passa a consumi-lo.

### 2.2 `importance_score` vira saída, não entrada (fecha Ruptura #4)

`importance_score` de cada memória passa a ser re-calibrado por
`Σ quality_signal das sessões onde foi injetada` — um Bayesian update:
memória nasce com prior do Sonnet (como hoje), mas converge para a evidência de desfecho.
`effective_count` é redefinido: "memória injetada + turn com quality_signal alto", não
"memória ecoada". Cold-move (`memory_consolidator.py:132`) passa a usar este número honesto.

### 2.3 Promoção automática gated por eval (liga Ruptura #2 com segurança)

`USE_OPERATIONAL_DIRECTIVES` deixa de ser um interruptor manual binário e vira um
**pipeline de promoção**:

```
candidata a diretriz (heurística importance recalibrado >= 0.7, n>=N sessões)
  → SHADOW: injeta <operational_directives> só para % do tráfego (A/B)
  → mede Δ quality_signal (com-diretiva vs sem) por K sessões
  → REGRESSION GATE: roda golden dataset offline (sem regressão) + Δ positivo significativo
  → PROMOVE para diretriz ativa 100% + registra no audit
  → MONITORA drift; se quality cair, DESPROMOVE automático (rollback)
```

Espelha o padrão de classe mundial: "pre-production evaluations automatically convert into
production guardrails" e "regression-eval contra golden dataset confirma que a mudança não
regrediu antes de ligar em produção" ([FutureAGI](https://futureagi.com/blog/agent-evaluation-frameworks-2026),
[MLflow](https://mlflow.org/llm-as-a-judge)).

### 2.4 Eval-in-the-loop: golden dataset deixa de ser manual (fecha Ruptura #5)

- Os `dataset.yaml` ganham um runner automatizado (LLM-as-judge contra
  expected_behavior/must_not, calibrado contra os julgamentos manuais históricos).
- Vira **gate do D8**: nenhuma sugestão é marcada `verified`, e nenhum commit do D8 entra
  em main, sem o eval passar. `verified` deixa de ser "o Sonnet acha que resolveu"
  (Ruptura #3) e passa a ser "o eval e o Δ quality_signal das sessões pós-deploy
  confirmam". O lifecycle ganha `responded → measuring → verified|regressed`.
- O dataset **cresce sozinho**: toda sessão com 👎 + correção humana, ou quality_signal
  baixo cross-validado, vira candidato a novo caso de golden dataset (o "regression set é
  uma lista de ativações reais de produção" — [FutureAGI](https://futureagi.com/blog/claude-skills-evaluation-deep-dive-2026/)).

### 2.5 Encaixe nas 5 camadas do SDK

- **Camada 5 (Control/hooks)**: o `SubagentStop`/`Stop` hook (já existe,
  `hooks.py:_subagent_stop_hook`) passa a também enfileirar o turn para o judge batch e a
  preencher `escalated_to_human`/`user_correction_received` quando o sinal chega.
- **Camada 1 (system_prompt)**: estático; `<operational_directives>` continua injetado via
  hook (dinâmico, fora do cache) — sem mudança de cache.
- **Camadas 3/4 (skills/subagents)**: o quality_signal por agent_type alimenta o eixo F
  (governança/lifecycle de skills) — skill com quality cronicamente baixo é candidata a
  revisão. O golden dataset por subagent (já existe) é o gate.

---

## PARTE 3 — CAMINHO INCREMENTAL

Ordenado por alavancagem. Cada fase REAPROVEITA o existente. O princípio: **primeiro o fio
de qualidade (sem ele tudo a jusante é cego), depois ligar os atuadores que já estão prontos
e parados.**

### Fase A0 — Ativar os sinais GRÁTIS que já são coletados e jogados fora (P, risco baixo)
- **Destrava:** primeira gota de ground-truth real, sem custo de API.
- Persistir `feedback.py` positive/negative numa tabela em vez de só logar
  (`feedback.py:66-90`). Escrever `user_correction_received=true` no
  `AgentInvocationMetric`/turn quando há correction feedback. Derivar
  `escalated_to_human` de friction (`friction_analyzer` já detecta re-pergunta).
- **Reaproveita:** botões 👍👎 (`chat.js:2681`), endpoint feedback, friction_analyzer.
- **Risco:** mínimo (só escrita de dados já existentes). **Dependência:** nenhuma.

### Fase A1 — Construir `quality_signal` (batch judge + outcome) (M, risco médio)
- **Destrava:** a moeda do flywheel. O sinal de recompensa que falta.
- Tabela `agent_turn_quality`. Judge batch (espelha `improvement_suggester` — mesmo
  padrão APScheduler módulo, Sonnet, cache_control ephemeral, R1 best-effort). Combina os
  3 canais; humano sobrescreve. Spot-check de calibração de 5-10%.
- **Reaproveita:** infra de batch (`sincronizacao_incremental_definitiva.py` módulo 25),
  `_get_anthropic_client`, padrão de truncamento R3, Voyage (já integrado).
- **Risco:** custo do judge (mitigado por batch + Haiku para casos simples + amostragem);
  judge mal-calibrado (mitigado por spot-check humano). **Dependência:** **EIXO E**
  (qualidade/observabilidade) — A1 É a materialização do que o Eixo E pede. Devem ser
  desenhados juntos: o Eixo E define O QUE é qualidade; A1 fecha o loop COM esse número.

### Fase A2 — Re-calibrar `importance`/`effective_count` por outcome (M, risco médio)
- **Destrava:** todo o pipeline de injeção e cold-move passa a operar sobre verdade.
- Bayesian update de `importance_score` a partir do quality_signal das sessões da memória.
  Redefinir `_track_memory_effectiveness` para "injetada + turn de alta qualidade".
- **Reaproveita:** `usage_count`/`effective_count` (colunas e tracking já existem),
  cold-move/GC inteiros (só passam a ler número honesto).
- **Risco:** mudar a semântica de `effective_count` afeta cold-move — fazer atrás de flag
  e comparar distribuição antes/depois. **Dependência:** A1.

### Fase A3 — Eval runner automatizado + gate no D8 (M, risco médio-alto)
- **Destrava:** fecha Ruptura #5 e #3. Mudanças param de entrar cegas em main.
- `run_eval.py` que executa os `dataset.yaml` via judge calibrado. Adicionar PASSO ao
  `dominio-8-improvement-dialogue.md`: rodar eval do(s) agente(s) afetado(s) ANTES do commit;
  bloquear/registrar `regressed` se falhar. `verified` exige Δ quality_signal pós-deploy.
- **Reaproveita:** 4 datasets existentes, formato expected_behavior/must_not, fluxo D8 cron.
- **Risco:** o D8 hoje commita direto em main sem gate — adicionar gate pode travar o cron;
  mitigar com modo "report-only" antes de "enforce" (mesmo padrão do `ui_policy_lint`).
  **Dependência:** A1 (para o Δ quality); pode começar A3 com gate puramente offline
  (golden dataset) em paralelo a A1.

### Fase A4 — Promoção automática gated de diretrizes (G, risco alto)
- **Destrava:** liga `USE_OPERATIONAL_DIRECTIVES` com segurança (Ruptura #2). O loop
  Distill→Deploy autônomo de heurísticas.
- Pipeline shadow/A-B → regression gate → promote → monitor drift → auto-despromove
  (§2.3). Estado de cada diretiva (`candidata|shadow|ativa|despromovida`) numa tabela.
- **Reaproveita:** `_build_operational_directives` inteiro (a seleção, o XML, o R0d no
  system_prompt já estão escritos e testados — só falta o gate de promoção na frente);
  `model_router` (já faz A/B de modelo per-request — mesmo mecanismo serve para A/B de
  diretiva).
- **Risco:** alto (muda comportamento ativo do agente). Por isso vem por último, sobre A1+A2
  confiáveis e A3 como rede. **Dependência:** A1, A2, A3 (todas).

### Fase A5 — Golden dataset auto-crescente (P contínuo, risco baixo)
- **Destrava:** o flywheel passa a melhorar o próprio critério de avaliação.
- Sessão com 👎+correção ou quality baixo cross-validado → candidato a caso de eval
  (revisão humana leve antes de entrar no dataset).
- **Reaproveita:** A1 (sinal), A3 (runner), datasets existentes. **Dependência:** A1, A3.

---

## RESUMO EXECUTIVO

**Alavancas (estado → alvo, 1 frase cada):**
1. **Sinal de qualidade**: hoje "effective_count = eco semântico" e "resolution = teve tool"
   (`_helpers.py:497`, `insights_service.py:229`) → `agent_turn_quality` fundindo humano +
   outcome + judge calibrado como a moeda do loop.
2. **Sinais grátis inertes**: 👍👎 "apenas logados" e `escalated_to_human`/`user_correction`
   sempre default (`feedback.py:66`, `models.py:1647`) → persistidos e usados como ground truth.
3. **Atuador desligado**: `USE_OPERATIONAL_DIRECTIVES=false` (`feature_flags.py:215`) com
   `_build_operational_directives` pronto → promoção automática gated por eval + A/B + drift.
4. **Verificação sem impacto**: `verified` = Sonnet acha que resolveu
   (`improvement_suggester.py:415`) → `verified` = Δ quality medido + golden dataset não regrediu.
5. **Golden dataset fora do loop**: 4 datasets, julgamento MANUAL (`evals/README.md:79`) →
   runner automatizado + gate no D8 + dataset auto-crescente.

**Dependências cross-eixo:**
- **CRÍTICA com EIXO E (qualidade)**: A Fase A1 É a implementação do que o Eixo E pede.
  Eixo E define a *métrica* de qualidade; Eixo A constrói o *loop* que a consome. Desenhar
  o schema `agent_turn_quality` em conjunto. Sem o sinal do Eixo E, o flywheel gira no vácuo.
- **EIXO F (governança/lifecycle de skills)**: quality_signal por agent_type/skill alimenta
  decisões de lifecycle (skill com quality crônico baixo → revisão). A4 usa o namespacing
  de skills do Eixo F.
- **EIXO B (planejador)**: o judge de trajetória (A1) precisa enxergar a trajetória inteira;
  se o Eixo B tornar a orquestração um harness (não prosa), o judge ganha estrutura para
  avaliar tool-selection/planning, não só a resposta final.

**Primeiro passo de maior alavancagem:** Fase A0 — persistir os 👍👎 que já são clicados
(`feedback.py:66-90`) e escrever `user_correction_received` no turn quando há correction.
É P (uma tabela + duas escritas), risco mínimo, e produz IMEDIATAMENTE o primeiro lote de
ground-truth humano — o calibrador sem o qual o judge LLM da Fase A1 não tem como ser
confiável. Sem ground-truth humano, o flywheel só substitui um proxy cego (eco) por outro
(opinião de um Sonnet não-calibrado).

## Contexto

Eixo do blueprint — evolucao do agente logistico. Tema: EIXO A — FLYWHEEL DE APRENDIZADO
