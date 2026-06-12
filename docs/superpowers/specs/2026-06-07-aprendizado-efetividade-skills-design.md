<!-- doc:meta
tipo: explanation
camada: L3
sot_de: design da camada de aprendizado automatico por efetividade (skills + scripts ad-hoc) do Agente Web
hub: docs/superpowers/specs/INDEX.md
superseded_by: —
atualizado: 2026-06-12
-->

# Aprendizado automatico por efetividade — skills + scripts ad-hoc

> **Papel:** design aprovado de uma camada que, no fim de cada sessao do Agente Web,
> avalia se as skills invocadas resolveram o problema do usuario e — quando nao —
> decide automaticamente entre (a) lembrete por-usuario, (b) lembrete para todos
> (via aprovacao) ou (c) ajuste de codigo (improvement dialogue). Fase 2 estende a
> mesma logica para scripts ad-hoc (Bash) recorrentes via cluster semantico.
> **Filosofia central: ESTENDER o que existe, nao duplicar.** Esta spec cobre o
> design das 2 partes; a entrega e faseada (Fase 1 = skills + inbox; Fase 2 = ad-hoc).
> **Separacao de competencias:** o avaliador (Haiku/Sonnet) detecta e DESCREVE o
> problema (com evidencia) e pede ajuda; quem diagnostica e implementa codigo e o
> Claude Code. Vale tambem para o `improvement_suggester` (D8) padrao.

## Indice

- [Contexto](#contexto)
- [Decisoes fechadas](#decisoes-fechadas)
- [O que ja existe (mapa de reuso)](#o-que-ja-existe-mapa-de-reuso)
- [Arquitetura — Fase 1 (efetividade de skill)](#arquitetura-fase-1-efetividade-de-skill)
- [Inbox de Aprovacao unificada](#inbox-de-aprovacao-unificada)
- [Modelo de dados](#modelo-de-dados)
- [Feature flags](#feature-flags)
- [Fluxo de dados ponta a ponta](#fluxo-de-dados-ponta-a-ponta)
- [Custo e guardrails](#custo-e-guardrails)
- [UI e acesso pelo menu](#ui-e-acesso-pelo-menu)
- [Fase 2 — scripts ad-hoc (design de alto nivel)](#fase-2-scripts-ad-hoc-design-de-alto-nivel)
- [Edge cases](#edge-cases)
- [Pre-mortem](#pre-mortem)
- [Testes e verificacao](#testes-e-verificacao)
- [Decisoes em aberto](#decisoes-em-aberto)
- [Conformidade](#conformidade)
- [Arquivos-alvo](#arquivos-alvo)

---

## Contexto

O Agente Web (Claude Agent SDK) invoca skills (`Skill:<nome>`) para resolver pedidos.
Hoje **nao ha medicao de efetividade por invocacao de skill**: se a skill nao resolve
e o usuario pede ajuste, reclama, ou o agente cai num script Bash ad-hoc para o mesmo
assunto, esse sinal se perde. O `improvement_suggester` (D8) existe, mas e **batch
global** (janela 8h, todas as sessoes), nao ancorado numa skill nem por-usuario.

Objetivo: capturar esse sinal **ancorado na invocacao da skill**, decidir a correcao
certa (lembrete vs codigo), aplicar o que e seguro automaticamente e enfileirar o
resto para aprovacao humana — de forma barata e sem poluir o contexto.

**Gap pre-existente descoberto durante o design (sera consertado aqui):** o
`directive_promotion` cria diretrizes em `directive_status='shadow'` mas **nao existe
nenhuma interface (rota ou tela) que promova `shadow -> ativa`** (`grep directive_status`
em `routes/` e `templates/` = vazio). Diretrizes nascem e travam em shadow. O
`improvement_dialogue` tambem nao tem tela — so API JSON consumida pelo Claude Code
via cron. Resultado: o administrador (Rafael) nao tem **onde** revisar/aprovar nada.

## Decisoes fechadas

Decisoes tomadas com o usuario na fase de brainstorming (2026-06-07):

| # | Decisao | Escolha |
|---|---------|---------|
| 1 | Estrategia de construcao | **Estender** o existente (nao camada paralela) |
| 2 | Quando avaliar | **Fim de sessao** — via `run_post_session_processing` (NAO o SDK Stop hook) |
| 3 | Aplicacao do resultado | Lembrete **por-usuario auto**; codigo sempre **via revisao** |
| 4 | "Mesmo assunto" (Fase 2) | **Embedding / cluster semantico** (pgvector) |
| 5 | Entrega do lembrete ("via hook") | **Injecao cirurgica** no PreToolUse (so quando a skill e invocada) |
| 6 | Faseamento | **Fase 1 = skills + inbox**; **Fase 2 = scripts ad-hoc** |
| 7 | Inbox de aprovacao | **Unificada**: lembretes-todos + diretrizes shadow + improvement dialogues |
| 8 | Ramo "lembrete para todos" | **Via inbox** (aprovacao humana antes de afetar todos) |

> Correcao tecnica importante da decisao 2: o `_stop_hook` do SDK
> (`app/agente/sdk/hooks.py:464`) dispara **por turno** (apos cada `ResultMessage`),
> e best-effort (logs/S3) e **nao tem o nosso `session_id`** no escopo
> (`hooks.py:498-500`). O ponto canonico de pos-sessao e
> `run_post_session_processing` (`app/agente/routes/_helpers.py:187`) — **recebe
> `session_id` + `user_id` como parametros explicitos** (`_helpers.py:189-191`),
> garantidos sem depender de ContextVar nem de closure; ja roda summarizer/pattern_analyzer
> e ja enfileira RQ. A semantica ("avaliar no fim, em background") e identica; o mecanismo
> e o certo. Conclusao da duvida: a feature **tem o session_id garantido**; nao e preciso
> consertar o `_stop_hook` (segue so para logs/S3).

## O que ja existe (mapa de reuso)

| Capacidade | Reuso | Fonte |
|---|---|---|
| Gatilho pos-sessao (session_id+user_id, best-effort, flag-gated) | ✅ | `app/agente/routes/_helpers.py:187` |
| Enfileiramento RQ pos-sessao (padrao `try_enqueue_*`) | ✅ | `_helpers.py:246-297`, `app/agente/workers/background_jobs.py:145-199` |
| Historico em ordem (`AgentSession.data['messages']`) | ✅ | `app/agente/models.py:168` (`get_messages`) |
| Skill invocada gravada como `"Skill:<nome>"` em `tools_used` | ✅ | `app/agente/routes/chat.py:866` |
| Pre-filtro de frustracao custo-zero (regex) | ✅ | `app/agente/services/sentiment_detector.py` |
| Padrao de chamada sub-LLM (Haiku/Sonnet) via job RQ | ✅ | `app/agente/workers/step_judge.py:66` |
| IDs de modelo | ✅ | Haiku `claude-haiku-4-5-20251001`, Sonnet `claude-sonnet-4-6` |
| Criar memoria programaticamente | ✅ | `AgentMemory.create_file()` `app/agente/models.py:666` |
| Lembrete = `priority='mandatory'` + `category='permanent'` | ✅ | `app/agente/models.py:488+` (canal `<user_rules>`) |
| Invalidar cache de injecao | ✅ | `app/agente/sdk/memory_injection.py` (`invalidate_injection_cache_for_user`) |
| Injecao cirurgica antes de uma tool | ✅ | `app/agente/sdk/hooks.py:143` (`_keep_stream_open` PreToolUse) |
| Ramo codigo (sugestao) | ✅ | `AgentImprovementDialogue.create_suggestion` `app/agente/models.py:1169` |
| Padrao de review admin (promote/reject) | ✅ | `app/agente/services/sql_evaluator_falses_service.py:305` (`_update_status`) |
| Padrao de rota PUT admin-only de memoria | ✅ | `app/agente/routes/memories.py:257` (`review`) |
| Tela `/agente/memorias` no menu (admin) | ✅ | `app/templates/_sidebar.html:878`, `app/agente/routes/memories.py:382` |
| Embeddings pgvector (Fase 2) | ✅ | `app/embeddings/models.py:218` (`AgentMemoryEmbedding`) |
| Transcript com `tool_input` completo do Bash (Fase 2) | ✅ | `app/agente/sdk/session_store_adapter.py:319` (`load`) |
| Diretriz so injeta quando `directive_status='ativa'` | ✅ (alvo da inbox) | `app/agente/sdk/memory_injection.py:505` |

Componentes **novos**: o avaliador por-skill (job), a montagem de janela ancorada,
a injecao cirurgica por-skill, a Inbox de Aprovacao (rotas+UI), e 2 tabelas.

## Arquitetura — Fase 1 (efetividade de skill)

### 1. Gatilho

Em `run_post_session_processing` (`_helpers.py:187`), adicionar mais um bloco
best-effort (try/except isolado, igual aos demais), gated por flag `AGENT_SKILL_EVAL`:

```python
# Avaliacao de efetividade de skill (best-effort, nao afeta as demais etapas)
try:
    from app.agente.config.feature_flags import AGENT_SKILL_EVAL
    if AGENT_SKILL_EVAL:
        from app.agente.workers.background_jobs import try_enqueue_skill_effectiveness
        if not try_enqueue_skill_effectiveness(session_id, user_id):
            # fallback inline so se RQ indisponivel (mesmo padrao try_enqueue_summarize)
            from app.agente.services.skill_effectiveness_service import evaluate_session
            evaluate_session(session_id=session_id, user_id=user_id)
except Exception as e:
    logger.warning(f"[POST_SESSION] skill effectiveness (ignorado): {e}")
```

Fila RQ: `agent_background` (reusa — ja registrada nos 3 perfis de worker). **Nenhuma
fila nova** (evita o checklist de 3 arquivos do `worker_render`).

### 2. Job + montagem da janela

Worker `skill_effectiveness_job(session_id, user_id)` em `background_jobs.py` (delega a
um service novo `services/skill_effectiveness_service.py:evaluate_session`):

1. Carrega `AgentSession.get_messages()` (lista ordenada de `{role, content, timestamp, tools_used}`).
2. Para cada msg `role='assistant'` cujo `tools_used` contem `"Skill:<X>"`, define a
   **ancora** (essa msg) e monta a janela do pedido:
   - `msg_anterior` = ultima msg `role='user'` antes da ancora;
   - `resposta_invocacao` = a propria ancora (texto do agente que invocou);
   - `proximas_user[:2]` = ate 2 msgs `role='user'` apos a ancora;
   - `proximas_assistant[:2]` = ate 2 msgs `role='assistant'` apos a ancora.
3. **Janela fechada** = existem >= 2 `proximas_user` (a "2 proximas mensagens do
   usuario" do pedido ja aconteceu). So avalia invocacoes com janela fechada **e nao
   avaliadas** (idempotencia via tabela, abaixo). Invocacoes no fim da sessao sem janela
   completa ficam para o proximo `run_post_session_processing` (que roda a cada
   exchange) — se a conversa morrer, ficam sem avaliacao (aceitavel; um sweeper batch
   opcional pode varrer depois).

### 3. Pipeline de avaliacao em 3 estagios (barato -> caro)

- **Estagio 0 (custo-zero):** roda `sentiment_detector` na janela + regex de marcadores
  ("nao era isso", "errado", "ajusta", pedido de correcao) **e** deteccao de Bash no
  mesmo assunto da skill nas `proximas_assistant`. Sem nenhum sinal -> grava
  `resolveu=true, stage_reached=0` e encerra. Filtra a maioria.
- **Estagio 1 (Haiku `claude-haiku-4-5-20251001`):** so com sinal fraco. Classifica
  `{resolveu: bool, suspeita_ajuste: bool, motivo: str, sinais: [str]}`. Padrao de
  chamada identico a `step_judge._call_haiku_judge` (`step_judge.py:66`),
  `temperature=0`, `max_tokens` baixo. Sem suspeita -> grava `stage_reached=1` e encerra.
- **Estagio 2 (Sonnet `claude-sonnet-4-6`):** so se `suspeita_ajuste=true`. Recebe a
  janela + nome da skill + a description da skill e decide o **ramo** com o prompt do
  pedido ("voce e um avaliador de solucoes, foi chamado pela suspeita de necessidade de
  ajuste na skill <X>. Avalie se a solucao e: lembrete a esse usuario / lembrete a todos
  / ajuste de codigo"). **Separacao de competencias (regra inviolavel — ver Principio):**
  no ramo `ajuste_codigo` o avaliador **NAO prescreve a solucao** de codigo — ele
  DESCREVE o problema + a evidencia e **pede ajuda**; o COMO (diagnostico + implementacao)
  e trabalho do Claude Code. Output estruturado:
  ```json
  {
    "ramo": "lembrete_usuario | lembrete_todos | ajuste_codigo | nada",
    "titulo": "...",
    "conteudo_lembrete": "texto do lembrete (so ramos lembrete_*; vazio se ajuste_codigo)",
    "problema": "descricao do problema observado + por que a skill nao resolveu (so ajuste_codigo)",
    "evidencia": "trechos da janela que sustentam o problema (so ajuste_codigo)",
    "categoria_codigo": "skill_bug | skill_suggestion | instruction_request | prompt_feedback",
    "justificativa": "...",
    "confianca": 0.0
  }
  ```
  Mapeamento p/ `ajuste_codigo`: `problema`->`description`, `evidencia`->`evidence_json`;
  `affected_files`/`implementation_notes` ficam **vazios** — o Claude Code os preenche
  ao implementar (via `improvement_dialogue.py` POST). O avaliador entrega um *pedido de
  ajuda acionavel*, nao uma correcao.

### 4. Ramos e aplicacao (decisoes 3 e 8)

| Ramo | Acao | Auto/Revisao |
|---|---|---|
| `lembrete_usuario` | `AgentMemory.create_file(user_id=N, path=/memories/lembretes_skill/<skill>.xml)` + `priority='mandatory'`, `category='permanent'`, `error_signature` para dedup + `invalidate_injection_cache_for_user(N)` | **Auto** (reversivel em `/agente/memorias`) |
| `lembrete_todos` | Cria item pendente na **Inbox de Aprovacao** (nao cria memoria ainda) | **Via inbox** |
| `ajuste_codigo` | `AgentImprovementDialogue.create_suggestion(...)` com **so problema + evidencia** (pedido de ajuda, SEM solucao prescrita), `author='agent_sdk'`, `status='proposed'` -> Inbox + cron D8. Claude Code preenche `implementation_notes`/`affected_files` ao resolver | **Via inbox + cron** |
| `nada` | grava `stage_reached=2, ramo='nada'` | — |

Dedup do ramo `lembrete_usuario`: o `path` `/memories/lembretes_skill/<skill>.xml` e
unico por `(user_id, path)` (constraint em `models.py:612`); se ja existir, faz
`update` consolidando (mantem 1 lembrete por skill por usuario, evita inflar contexto).
`error_signature` (gerado por Haiku, padrao `pattern_analyzer.py:1957`) agrupa o
"assunto" para nao recriar lembrete redundante com texto diferente.

### 5. Entrega do lembrete — injecao cirurgica (decisao 5)

No `_keep_stream_open` (PreToolUse, `hooks.py:143`), quando `tool_name == 'Skill'`:

1. Extrai `skill = tool_input.get('skill')`.
2. Consulta um **dict em memoria por-sessao** `skill -> lembrete` (carregado 1x por
   sessao a partir de `AgentMemory` com path `/memories/lembretes_skill/*` do usuario;
   reusa o cache de injecao TTL 30min para nao consultar o banco no caminho quente).
3. Se houver lembrete para `skill`, injeta via `hookSpecificOutput.additionalContext`
   (`<skill_reminder skill="X">...</skill_reminder>`) — **so naquele momento**.

Vantagem vs. memoria sempre-no-topo: zero poluicao de contexto quando a skill nao e
usada; e literalmente "lembrete ao invocar a skill". Reusa o padrao exato ja existente
para o tool de SQL (`hooks.py:143`).

## Inbox de Aprovacao unificada

Nova **aba dentro de `/agente/memorias`** (ja no menu, admin-only — `_sidebar.html:878`),
chamada "Pendentes de Aprovacao". Conserta o gap do `directive_promotion` de quebra.

**Itens listados** (decisao 7 — unificada):
1. Lembretes-para-todos propostos (ramo `lembrete_todos`).
2. Diretrizes empresa em `directive_status='shadow'` (do `directive_promotion` existente).
3. Improvement dialogues `status='proposed'` (o admin passa a ver; o cron continua).

**Cada item exibe:** tipo, titulo, **evidencia** (link para a sessao/janela que originou),
conteudo proposto, origem (skill, usuario, data).

**Acoes (rotas PUT admin-only, reusando `_update_status(id, status, reviewer_user_id)`
do padrao `sql_evaluator_falses_service.py:305` + padrao de `memories.py:257`):**
- **Aprovar**:
  - `lembrete_todos` -> cria `AgentMemory(user_id=0, priority='mandatory', category='permanent')` + invalida cache (passa a injetar para todos via `<user_rules>`).
  - diretriz `shadow` -> seta `directive_status='ativa'` (passa a ser injetada — `memory_injection.py:505`). **Este e o botao que nunca existiu.**
  - improvement dialogue -> marca `verified`/relevante (implementacao segue com o Claude Code).
- **Editar e aprovar**: ajusta o `conteudo` antes de aplicar.
- **Rejeitar**: status `rejected` (+ dedup, nao reaparece).

> O service de promocao de diretriz deve expor uma funcao `promover_diretriz(id, reviewer)`
> simetrica a `promote_to_active` do sql_evaluator — hoje inexistente. Esta spec a cria.

## Modelo de dados

Duas tabelas novas. Migrations com DOIS artefatos (`.py` + `.sql` idempotente) por
regra do projeto.

### `agent_skill_effectiveness` (Fase 1)

| Coluna | Tipo | Nota |
|---|---|---|
| `id` | Integer PK | |
| `user_id` | Integer FK usuarios.id, NOT NULL, index | |
| `session_id` | String, NOT NULL, index | nosso UUID |
| `skill_name` | String(80), NOT NULL, index | sem o prefixo `Skill:` |
| `anchor_msg_id` | String, NOT NULL | id da msg que invocou (idempotencia) |
| `stage_reached` | SmallInteger | 0/1/2 |
| `resolveu` | Boolean nullable | resultado da avaliacao |
| `ramo` | String(20) nullable | lembrete_usuario / lembrete_todos / ajuste_codigo / nada |
| `confidence` | Float nullable | confianca da decisao do estagio que decidiu (Sonnet stage 2 / Haiku stage 1); base do guardrail de auto-aplicacao e da calibracao do limiar |
| `action_ref` | String(120) nullable | `memory:<id>` ou `dialogue:<id>` ou `approval:<id>` |
| `error_signature` | String(64) nullable | agrupa "assunto" (reusa helper Haiku) |
| `evidencia_json` | JSON | janela compactada (para a inbox exibir) |
| `created_at` | DateTime default `agora_utc_naive()` | |

Constraint **unica `(session_id, anchor_msg_id)`** = idempotencia (cada invocacao
avaliada 1x). Tambem habilita metrica "qual skill mais falha" (group by skill_name,
resolveu).

### `agent_adhoc_script` (Fase 2)

| Coluna | Tipo | Nota |
|---|---|---|
| `id` | Integer PK | |
| `user_id` | Integer FK, index | |
| `session_id` | String, index | |
| `tool_use_id` | String | de-dup do mesmo Bash |
| `comando` | Text | comando resumido/normalizado |
| `confidence` | Float nullable | relevancia do comando como sinal de skill faltante (pondera a contagem do cluster; semantica refinada na Fase 2) |
| `embedding` | Vector | pgvector (mesmo padrao `AgentMemoryEmbedding`) |
| `cluster_id` | Integer nullable, index | preenchido pelo job de cluster |
| `created_at` | DateTime default `agora_utc_naive()` | |

### Inbox

A inbox **nao exige tabela nova**: e uma VIEW logica sobre fontes ja existentes
(`AgentImprovementDialogue.status='proposed'`, `AgentMemory.directive_status='shadow'`).
Para `lembrete_todos`, **decisao recomendada:** representa-lo como
`AgentMemory(user_id=0, directive_status='shadow', priority='mandatory', escopo='empresa')`
— assim a aprovacao (shadow->ativa) usa exatamente o mesmo caminho da diretriz, e a
inbox tem so 2 tipos de fonte (AgentMemory shadow + ImprovementDialogue proposed).

## Feature flags

Em `app/agente/config/feature_flags.py` (padrao `os.getenv(...) == 'true'`):

| Flag | Default | Efeito |
|---|---|---|
| `AGENT_SKILL_EVAL` | `false` -> `true` apos smoke | Liga o gatilho + job de avaliacao |
| `AGENT_SKILL_EVAL_APPLY_USER` | `true` | Ramo `lembrete_usuario` aplica auto (se `false`, vira shadow tambem) |
| `AGENT_SKILL_EVAL_SONNET` | `true` | Permite escalonar ao estagio 2 (se `false`, para no Haiku — modo observacao) |
| `AGENT_ADHOC_TRACKING` | `false` | Fase 2: captura scripts ad-hoc |
| `AGENT_ADHOC_CLUSTER` | `false` | Fase 2: cluster + sugestao |

`AGENT_SKILL_EVAL` nasce `false` para 1 ciclo de smoke (avaliar logando, conferir
ruido), depois liga — alinhado a preferencia "ligar feature pronta" sem o risco de
escrever memoria errada no primeiro dia.

## Fluxo de dados ponta a ponta

```
[Fase 1 — captura/decisao, assincrono]
Sessao encerra exchange
  -> run_post_session_processing (_helpers.py:187)
  -> try_enqueue_skill_effectiveness -> RQ 'agent_background'
  -> skill_effectiveness_job
       -> get_messages() -> acha "Skill:X" -> monta janela -> janela fechada?
       -> Estagio 0 (sentiment/regex)  [maioria para aqui]
       -> Estagio 1 (Haiku)            [sinal fraco]
       -> Estagio 2 (Sonnet)           [suspeita] -> ramo
       -> aplica: AgentMemory(user) auto | inbox(todos) | ImprovementDialogue(codigo)
       -> grava agent_skill_effectiveness (idempotente)

[Fase 1 — entrega do lembrete, no caminho quente]
Usuario manda msg -> agente decide invocar Skill X
  -> PreToolUse _keep_stream_open (hooks.py:143)
  -> dict por-sessao skill->lembrete (cache 30min)
  -> injeta <skill_reminder> via additionalContext  [so se houver lembrete p/ X]

[Fase 1 — aprovacao, UI]
Admin abre /agente/memorias -> aba "Pendentes de Aprovacao"
  -> lista AgentMemory(shadow) + ImprovementDialogue(proposed)
  -> Aprovar -> PUT admin-only -> shadow->ativa (memoria) | verified (dialogue)
  -> passa a ser injetado nos proximos turnos
```

## Custo e guardrails

- Funil 0->1->2: estagio 0 gratis filtra a maioria; Haiku so em sinal fraco; Sonnet so
  em suspeita. Custo esperado por sessao ~ proximo de zero na maioria.
- **Cap** por sessao (ex.: max 3 escalonamentos a Sonnet/sessao) e por usuario/dia
  (env). Evita explosao em sessoes longas.
- Dedup triplo: `path` unico (memoria), `suggestion_key` (dialogue, ja existe), e
  `error_signature` (assunto). Lembrete por-usuario = 1 por skill (update, nao insert).
- Anti-ruido: `lembrete_usuario` so com `confidence >= limiar` (coluna persistida) do
  Sonnet; abaixo disso vira `ajuste_codigo`/inbox (revisao) em vez de auto.
- Best-effort: todo o bloco e try/except isolado — **nunca** quebra o chat nem as
  demais etapas pos-sessao.

## UI e acesso pelo menu

- **Sem tela nova obrigatoria.** A Inbox e uma aba na pagina ja existente
  `/agente/memorias` (`memorias.html`), que ja tem link no menu
  (`_sidebar.html:878`, admin-only). Satisfaz a regra "toda tela com acesso via UI".
- Metricas de efetividade por skill (`agent_skill_effectiveness`) podem ganhar um card
  na pagina de Insights (`insights.html`) — **opcional**, nao bloqueia a Fase 1.

## Fase 2 — scripts ad-hoc (design de alto nivel)

> **Spec propria ESCRITA em 2026-06-12:**
> [2026-06-12-aprendizado-adhoc-fase2-design.md](2026-06-12-aprendizado-adhoc-fase2-design.md)
> — detalha e REVISA este esboco (campos estruturados `problema`/`session_id`,
> criterios C1-C6, quadrifurcacao com EXTENSAO de skill, bypass p/ gap nomeado).
> O esboco abaixo permanece como registro historico da decisao 6.

Esboco original:

- "Script ad-hoc" = uso de `Bash` (Python/SQL inline) pelo agente fora de skill.
- **Captura:** o `skill_effectiveness_job` (ou job irmao) le o **transcript**
  (`session_store_adapter.load`, `session_store_adapter.py:319` — tem o `tool_input`
  completo, diferente do `tools_used` que so guarda o nome). Filtra Bash "substantivo"
  e grava em `agent_adhoc_script` com `embedding` (Voyage + pgvector).
- **Cluster + contagem (decisao 4):** agrupa por similaridade de embedding. "Mesmo
  assunto" = mesmo cluster. A **contagem** (a duvida original do usuario) = numero de
  membros do cluster, por `user_id` e/ou global.
- **Disparo:** cluster cruza threshold (default 3 por-usuario / 5 global, env) ->
  Sonnet resume o cluster -> `AgentImprovementDialogue(category='skill_suggestion')`
  ("deveria existir skill para X") -> Inbox.

## Edge cases

- **Janela incompleta no fim da sessao:** so avalia com >= 2 `proximas_user`; senao
  espera o proximo exchange. Documentado como aceitavel.
- **Multiplas invocacoes da mesma skill na sessao:** cada `anchor_msg_id` e avaliado
  independentemente (constraint unica por ancora).
- **Skill invocada por subagente:** o `tools_used` do agente principal e a fonte; skills
  internas de subagente nao entram (escopo: skills do agente principal).
- **Usuario corrige por motivo nao-relacionado a skill:** estagio 2 (Sonnet) tem ramo
  `nada`; alem disso so escala com sinal do estagio 1.
- **Conteudo sensivel (PII) na janela:** reusar `_sanitization.py` / `pii_masker.py`
  antes de mandar a janela ao LLM.
- **Lembrete que vira ruido:** reversivel em `/agente/memorias`; metrica de efetividade
  por skill ajuda a detectar lembretes inuteis (skill que continua falhando apesar do lembrete).

## Pre-mortem

- **Risco: avaliacao gera lembretes demais (polui contexto).** Mitigacao: injecao
  cirurgica (so na skill), 1 lembrete/skill/usuario, limiar de confianca, cap/dia.
- **Risco: custo de LLM cresce.** Mitigacao: funil 0->1->2, cap por sessao, flag
  `AGENT_SKILL_EVAL_SONNET` para travar no Haiku.
- **Risco: inbox vira backlog ignorado** (como o shadow hoje). Mitigacao: KPI de
  pendentes na pagina + (opcional) aviso no chat in-app para admin.
- **Risco: tocar `_helpers.py` / `hooks.py` quebra Teams** (export critico — CLAUDE.md).
  Mitigacao: bloco isolado try/except; testar Teams; flags default-off no merge.
- **Risco: `directive_promotion` ativacao causa injecao indevida.** Mitigacao: aprovacao
  e explicita e por-item; preview do conteudo antes de aprovar.

## Testes e verificacao

Pytest **deterministico** (preferencia registrada: evals LLM caros -> pytest; mock
Haiku/Sonnet). Cobertura minima:

- Montagem da janela: ancora correta, `msg_anterior`, `proximas_user[:2]`, `proximas_assistant[:2]`.
- Janela fechada vs aberta (skip quando < 2 proximas_user).
- Idempotencia: 2 execucoes nao duplicam `agent_skill_effectiveness`.
- Estagio 0 filtra (sem sinal -> sem chamada LLM).
- Roteamento ramo -> acao (mock Sonnet): cria memoria user / item inbox / dialogue.
- Dedup: 2 lembretes da mesma skill = 1 registro (update).
- Flags OFF = noop (gatilho nao enfileira; apply_user off = shadow).
- Inbox: aprovar shadow -> `directive_status='ativa'`; aprovar lembrete_todos -> memoria
  empresa; rejeitar -> `rejected`.
- Permissao: rotas da inbox negam nao-admin.
- (Fase 2) cluster: contagem por cluster, threshold dispara sugestao.

## Decisoes em aberto

- Representacao de `lembrete_todos`: como `AgentMemory(shadow,empresa)` (recomendado,
  reusa caminho de ativacao da diretriz) vs. nova categoria em `AgentImprovementDialogue`.
  **Recomendacao: AgentMemory shadow** — confirmar no review do plano.
- Limiar de `confidence` (coluna) para auto-aplicar lembrete_usuario (sugerido 0.7).
- Cap exato (escalonamentos Sonnet por sessao/dia).

## Conformidade

- **PAD-A:** este doc segue o header `doc:meta` (tipo=explanation, L3) e e
  registrado em `docs/superpowers/specs/INDEX.md`.
- **Migrations:** 2 tabelas -> 2 pares `.py`+`.sql` idempotentes em `scripts/migrations/`.
- **Worker RQ:** reusa fila `agent_background` (sem novas filas; nao exige editar
  `worker_render.py` + `start_worker_render.sh`).
- **Timezone:** colunas `created_at` usam `agora_utc_naive()` (padrao do projeto).
- **Export critico Teams:** mudancas em `_helpers.py`/`hooks.py` exigem teste no Teams.
- **UI:** Inbox como aba em pagina ja linkada no menu (sem tela orfa).
- **JSON sanitization:** `evidencia_json` via `sanitize_for_json()` ao gravar.

## Arquivos-alvo

**Novos:**
- `app/agente/services/skill_effectiveness_service.py` — `evaluate_session`, 3 estagios, roteamento.
- `app/agente/services/directive_approval_service.py` — `promover_diretriz`, `rejeitar`, fonte da inbox (ou estender service existente).
- `scripts/migrations/2026_06_07_agent_skill_effectiveness.{py,sql}`
- `scripts/migrations/2026_06_07_agent_adhoc_script.{py,sql}` (Fase 2)
- Testes em `tests/agente/` (pytest).

**Modificados:**
- `app/agente/routes/_helpers.py` — bloco gatilho em `run_post_session_processing`.
- `app/agente/workers/background_jobs.py` — `try_enqueue_skill_effectiveness` + `skill_effectiveness_job`.
- `app/agente/sdk/hooks.py` — injecao cirurgica em `_keep_stream_open` (tool=Skill).
- `app/agente/sdk/memory_injection.py` — carga do dict por-sessao `skill->lembrete` (cache).
- `app/agente/models.py` — `AgentSkillEffectiveness`, `AgentAdhocScript` (Fase 2).
- `app/agente/routes/memories.py` — rotas da aba "Pendentes de Aprovacao".
- `app/agente/templates/agente/memorias.html` — aba inbox.
- `app/agente/config/feature_flags.py` — flags novas.
- `app/agente/services/improvement_suggester.py` — ajustar system prompt (D8 padrao): sugestoes sao **descricao de problema + pedido de ajuda**, NAO solucao prescrita (separacao de competencias).
- (opcional) `app/agente/templates/agente/insights.html` — card de efetividade por skill.
