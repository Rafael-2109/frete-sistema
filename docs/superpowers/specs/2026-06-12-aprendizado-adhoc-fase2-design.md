<!-- doc:meta
tipo: explanation
camada: L3
sot_de: design da Fase 2 do aprendizado por efetividade — captura de scripts ad-hoc, cluster de demanda e promocao a skill (novo/extensao/roteamento)
hub: docs/superpowers/specs/INDEX.md
superseded_by: —
atualizado: 2026-06-12
-->

# Aprendizado por efetividade — Fase 2: scripts ad-hoc → skill

> **Papel:** design aprovado da Fase 2 da camada de aprendizado do Agente Web.
> Captura scripts ad-hoc (Bash substantivo) dos transcripts pos-sessao, agrupa por
> demanda (cluster semantico) e — cruzado o threshold — propoe na Inbox de Aprovacao
> um de 4 destinos: skill NOVA, EXTENSAO de skill existente, conserto de ROTEAMENTO
> (realimenta Fase 1) ou descarte com trava. Detalha a spec-mae
> [2026-06-07-aprendizado-efetividade-skills-design.md](2026-06-07-aprendizado-efetividade-skills-design.md)
> (secao "Fase 2 — design de alto nivel").
> **Separacao de competencias (inviolavel):** o avaliador DESCREVE com evidencia;
> quem cria/estende skill e o Claude Code, apos aprovacao humana na Inbox.

## Indice

- [Contexto](#contexto)
- [Decisoes fechadas](#decisoes-fechadas)
- [O que ja existe (mapa de reuso)](#o-que-ja-existe-mapa-de-reuso)
- [Criterios de promocao C1-C6](#criterios-de-promocao-c1-c6)
- [Arquitetura](#arquitetura)
- [Modelo de dados](#modelo-de-dados)
- [Feature flags](#feature-flags)
- [Custo e guardrails](#custo-e-guardrails)
- [Edge cases](#edge-cases)
- [Testes e verificacao](#testes-e-verificacao)
- [Camada A — universo dev (fase seguinte)](#camada-a-universo-dev-fase-seguinte)
- [Decisoes em aberto](#decisoes-em-aberto)
- [Arquivos-alvo](#arquivos-alvo)

---

## Contexto

Quando o Agente Web resolve um pedido com Bash ad-hoc (Python/SQL inline) em vez de
skill, tres informacoes se perdem hoje: (a) a DEMANDA recorrente que justificaria uma
skill nova; (b) a LIMITACAO de skill existente que forcou o fallback (ex.:
`exportando-arquivos/scripts/exportar.py:106-107` gera Excel de 1 aba — multi-aba cai
em ad-hoc); (c) a FALHA DE ROTEAMENTO (skill existia e cobria, mas nao foi invocada).
A Fase 1 (em PROD, flag `AGENT_SKILL_EVAL`) ja detecta "Bash logo apos skill" como
sinal de inefetividade (`skill_effectiveness_service.py:96-101`, sinal 3 do stage 0),
mas nao captura o conteudo do script nem agrega demanda entre sessoes.

Origem do design: sessao Claude Code 2026-06-12 (Rafael) — 4 perguntas (quando criar
skill; estrutura no script; determinismo; loop com checkpoint) + 3 revisoes (PAD-A
fora do caminho web; campos estruturados problema/session_id/timestamp; criterios
revisados) + o 4o destino (extensao de skill existente).

**Existem DOIS universos de script ad-hoc, com mecanismos distintos:**

| Universo | O que e | Mecanismo | Fase |
|----------|---------|-----------|------|
| **Web** | Bash inline no transcript do Agente Web (nao vira arquivo) | Job pos-sessao + tabela + cluster pgvector | **Esta spec** |
| **Dev** | Arquivo `.py` persistido no repo, criado pelo Claude Code local | Header PAD-A + gate Write + loop com sidecar | [Camada A](#camada-a-universo-dev-fase-seguinte) (fase seguinte) |

PAD-A (hooks `pad_creation_gate.py` etc.) NAO participa do caminho web: embora
`.claude/settings.json` seja versionado e o client carregue `setting_sources:
["project"]` (`app/agente/sdk/client.py:1588`), o gate so age em zona gerenciada de
arquivos — e o agente web roda Bash inline, nao cria arquivos no repo.

## Decisoes fechadas

| # | Topico | Decisao |
|---|--------|---------|
| 1 | Ordem de entrega | **B → A**: universo web primeiro (sinal de demanda real); camada dev depois |
| 2 | Checkpoint anti-revisita | Em TABELA (`suggestion_key` dedup do dialogue), nunca mutando script — mutacao quebraria content-hash e geraria ruido de commit |
| 3 | Campos de busca | `problema` (≤100 chars, Haiku com fallback deterministico), `session_id`, `criado_em` obrigatorios na captura |
| 4 | Embedding | Voyage sobre `problema + comando` (cluster mais semantico que comando bruto) |
| 5 | Similaridade de cluster | 0.85 (mesmo limiar validado no dedup F0 arquitetura-conhecimento) |
| 6 | Thresholds de disparo | 3 por usuario / 5 global (env) — herdado da spec-mae |
| 7 | Gap nomeado | `tipo_gap=skill_insuficiente` com skill identificada **bypassa threshold** (caso ja acionavel; dedup + cap diario seguram ruido) |
| 8 | Destino | `AgentImprovementDialogue(category='skill_suggestion')` reusada; `tipo_gap` diferencia no `evidence_json` (sem categoria nova — menor superficie) |
| 9 | C4 (responsabilidade unica) | E criterio de DESIGN na criacao da skill, nao de promocao do cluster |
| 10 | Avaliacao LLM | Sem evals LLM; cobertura = pytest deterministico (veto Rafael, ver memoria `feedback_evals_llm_caros_preferir_pytest`) |
| 11 | Calibracao | Empirica via Inbox: cada aceite/rejeicao registra motivo; revisar thresholds apos ~10 decisoes |

## O que ja existe (mapa de reuso)

| Peca | Onde | Uso na Fase 2 |
|------|------|----------------|
| Gatilho pos-sessao com `session_id`+`user_id` | `app/agente/routes/_helpers.py:271,549` (`_maybe_trigger_skill_eval`) | Job irmao enfileirado no mesmo ponto |
| Transcript com `tool_input` completo do Bash | `app/agente/sdk/session_store_adapter.py:319` (`load`) | Fonte da captura |
| Janela por skill (qual skill ativa quando o Bash rodou) | `skill_effectiveness_service.py:36` (`build_skill_windows`) | Preenche `skill_relacionada` |
| PII masking | `mask_pii` (ja usado na Fase 1) | `command_masked`, `contexto_user_msg` |
| Embeddings Voyage + pgvector | `app/embeddings/models.py` (`AgentMemoryEmbedding` como padrao) | Coluna `embedding` + busca de vizinho |
| Dialogue + dedup por `suggestion_key` | `app/agente/models.py:1196` (`AgentImprovementDialogue`, categoria `skill_suggestion` ja documentada em :1209) | Destino + checkpoint |
| Inbox de Aprovacao | `/agente/memorias` aba Pendentes (Fase 1) | UI de decisao — sem tela nova |
| Fila RQ `agent_background` | `app/agente/workers/background_jobs.py` | Execucao assincrona do job |
| Canal ativo de declaracao | tool `register_improvement` + diretiva constitucional `registro-melhorias` (commit `a184e571f`) | Complementar: agente declara limitacao na hora; captura pos-sessao e a rede deterministica |

## Criterios de promocao C1-C6

| Criterio | Pergunta | Como se mede |
|----------|----------|--------------|
| **C1 Demanda** | Ocorreu de verdade ≥N vezes? | Contagem de membros do cluster (por user / global). Nunca especulativo (principio demanda-driven) |
| **C2 Generalizavel** | Variacoes sobre um tema? | Dispersao INTERNA do cluster: parametros variam → skill; comando sempre identico → candidato a fast-path/cron, NAO skill |
| **C3 Cobertura** | Existe skill para isso? | Quadrifurcacao (tabela abaixo) |
| **C4 Responsabilidade unica** | A skill proposta faz UMA coisa? | Gate de DESIGN na criacao (Constituicao §6) — nao bloqueia promocao; cluster amplo pode gerar 2 skills |
| **C5 Superficie** | Quem consome? | Web → skill; dev-only recorrente → script promovido a zona PAD-A; nenhum → descarte |
| **C6 Friccao** | Quanto custou re-derivar? | Retries/erros de Bash no mesmo assunto na sessao + tamanho do comando. Acerto de primeira em 1 linha agrega pouco mesmo repetido; tateio com gotchas agrega muito (conhecimento nao-derivavel) |

**Quadrifurcacao do C3** (resultado do julgamento do cluster):

| `tipo_gap` | Diagnostico | Destino |
|------------|-------------|---------|
| `sem_skill` | Nenhuma skill cobre | Dialogue: skill NOVA (threshold C1 cheio) |
| `skill_nao_usada` | Skill cobre, nao foi invocada | Realimenta **Fase 1**: lembrete / ajuste de description (falha de roteamento — nao cria skill) |
| `skill_insuficiente` | Skill invocada, mas com limitacao | Dialogue: EXTENSAO da skill (bypass de threshold; `suggestion_key=skill-gap-<skill>-<slug>`) |
| `one_off` / rejeitado | Nao generaliza, ou Rafael rejeitou | Descarte; `suggestion_key` trava re-proposta mesmo se o cluster crescer |

## Arquitetura

### 1. Captura (job pos-sessao, custo ~zero)

- Gatilho: bloco best-effort em `run_post_session_processing` (mesmo padrao de
  `_maybe_trigger_skill_eval`), gated por `AGENT_ADHOC_CAPTURE`, enfileira job RQ
  `agent_background` (fallback inline se `AGENT_POST_SESSION_VIA_RQ=false`).
- Le o transcript (`session_store_adapter.load`) e filtra **Bash substantivo**
  (deterministico, zero token): contem `python -c`/heredoc/SQL DML **ou**
  comprimento > limiar. EXCLUI: comandos executando scripts de skill (path
  `.claude/skills/*/scripts/`), triviais (ls/cat/grep/git status), e duplicatas
  exatas na mesma sessao.
- Por script capturado: **1 chamada Haiku** extrai `problema` (≤100 chars) e
  `motivo_fallback` (≤150 chars, so quando ha `skill_relacionada`); fallback
  deterministico = truncate da ultima msg do usuario. Cap diario por env.
- `skill_relacionada` = skill da janela do transcript em que o Bash ocorreu
  (reusa `build_skill_windows`); NULL se nenhum (→ `tipo_gap=sem_skill` provisorio).
- Grava `agent_adhoc_script` com PII mascarado + embedding Voyage de
  `problema + comando`.

### 2. Clustering incremental (zero LLM)

Ao inserir: busca vizinho mais proximo via pgvector (cosine). Similaridade ≥
`AGENT_ADHOC_SIM` → herda `cluster_id` do vizinho; senao `cluster_id = id` proprio
(novo cluster). Contagem de demanda = `COUNT(*)` por cluster (por user e global).

### 3. Disparo (unico ponto Sonnet)

Condicoes (avaliadas no mesmo job, apos insert):
- cluster cruza threshold (C1) **ou** registro tem `tipo_gap=skill_insuficiente`
  com `skill_relacionada` + `motivo_fallback` preenchidos (bypass, decisao 7);
- nenhum dialogue existente com o `suggestion_key` do cluster/gap (checkpoint);
- cap diario de Sonnet nao estourado.

Sonnet recebe: membros do cluster (problemas + comandos mascarados), catalogo de
skills (nome + description, p/ C3), sinais C6 (retries da sessao). Julga C2/C3/C6 e
produz title + description + `tipo_gap` final. Resultado →
`AgentImprovementDialogue(category='skill_suggestion', evidence_json={tipo_gap,
skill_relacionada, cluster_id, membros, motivo_fallback})` → Inbox.

### 4. Pos-aprovacao

Rafael decide na Inbox. Aprovado → Claude Code implementa: skill nova segue
skill-creator + checklist padrao completo (`ROUTING_SKILLS.md`, `tool_skill_mapper`,
SCRIPTS.md, cross-refs); extensao edita a skill alvo. C4 e validado nesse momento.
`tipo_gap=skill_nao_usada` aprovado → acao da Fase 1 (lembrete/description), nao
gera skill.

## Modelo de dados

Tabela nova `agent_adhoc_script` (migracao em PAR: DDL `.sql` idempotente + script
Python — regra de dois artefatos):

| Campo | Tipo | Nota |
|-------|------|------|
| `id` | serial PK | tambem serve de `cluster_id` raiz |
| `session_id` | varchar, idx | FK logica `agent_sessions` |
| `user_id` | int, idx | |
| `problema` | varchar(120) | Haiku ≤100 chars; fallback truncate msg do usuario |
| `command_masked` | text | PII mascarado; truncado p/ armazenamento |
| `contexto_user_msg` | text | ultima msg do usuario antes do Bash, mascarada |
| `skill_relacionada` | varchar(80), nullable | da janela do transcript |
| `tipo_gap` | varchar(20) | na captura: `sem_skill` / `skill_insuficiente` / `desconhecido`; pos-julgamento Sonnet pode refinar p/ `skill_nao_usada` / `one_off` |
| `motivo_fallback` | varchar(200), nullable | por que o Bash apesar da skill |
| `retries_sessao` | smallint | sinal C6: tentativas Bash com erro no assunto |
| `embedding` | vector | Voyage sobre `problema + comando` |
| `cluster_id` | int, idx | incremental (sec. Arquitetura §2) |
| `criado_em` | timestamp | Brasil naive (`REGRAS_TIMEZONE.md`) |

Indices: pgvector (cosine) em `embedding`, btree em `cluster_id`, `user_id`,
`session_id`, `criado_em`.

## Feature flags

| Flag | Default | Papel |
|------|---------|-------|
| `AGENT_ADHOC_CAPTURE` | `true` (codigo) | master da captura — preferencia por flag ligada apos merge validado |
| `AGENT_ADHOC_SIM` | `0.85` | similaridade minima p/ herdar cluster |
| `AGENT_ADHOC_THRESHOLD_USER` | `3` | C1 por usuario |
| `AGENT_ADHOC_THRESHOLD_GLOBAL` | `5` | C1 global |
| `AGENT_ADHOC_MAX_HAIKU_DAY` | `100` | cap de extracoes na captura |
| `AGENT_ADHOC_MAX_SONNET_DAY` | `2` | cap de julgamentos/dialogues por dia |

## Custo e guardrails

- Captura: Haiku ~US$0,0005/script (≈US$0,05/dia a 100 capturas) + embedding Voyage
  (centavos/mes). Clustering e contagem = SQL puro.
- Sonnet so no disparo (raro, cap 2/dia). Sem evals LLM (decisao 10).
- Best-effort em TODO o caminho: try/except isolado, nunca quebra o chat nem as
  demais etapas pos-sessao (mesmo padrao Fase 1).
- Dedup: `suggestion_key` (dialogue) + duplicata exata de comando na sessao.
- Anti-ruido: dialogue rejeitado TRAVA o cluster (checkpoint definitivo).

## Edge cases

- **Teams degradado**: `tools_used` do Teams grava `"Skill"` sem nome
  (`app/teams/services.py:1294`; web grava `"Skill:<nome>"`, `chat.py:866`) →
  `skill_relacionada` indeterminavel → `tipo_gap='desconhecido'` (participa do
  cluster/C1, nao dispara bypass). Fechar o debito Teams (enriquecer tool_name)
  multiplica o valor desta fase — recomendado na fila.
- **Comando gigante** (heredoc longo): truncar p/ embedding e armazenamento;
  `problema` preserva a busca.
- **Sessao sem Bash substantivo**: job retorna cedo, custo zero.
- **Backfill historico**: FORA do escopo (captura so daqui pra frente); possivel
  comando manual futuro reusando o mesmo job sobre transcripts arquivados.
- **Cluster drift** (membros heterogeneos por 0.85 transitivo): mitigado pelo
  julgamento Sonnet no disparo (pode responder "cluster incoerente" → nao propoe;
  contagem segue).

## Testes e verificacao

Pytest deterministico (zero token): filtro Bash substantivo (inclusoes/exclusoes);
extracao com Haiku mockado + fallback; clustering com embeddings sinteticos
(herda/novo/threshold); disparo (threshold, bypass gap nomeado, caps, dedup
`suggestion_key`, trava de rejeitado); mascaramento PII; best-effort (excecao no job
nao propaga). Validacao manual pos-deploy: 1 sessao real com Bash ad-hoc → conferir
linha na tabela + (forcando threshold) dialogue na Inbox.

## Camada A — universo dev (fase seguinte)

Espelho desta fase para scripts `.py` persistidos no repo (~950 em `scripts/`,
~28 novos/semana). Alto nivel (spec propria quando chegar a vez):

- **Header obrigatorio na nascenca** (validado por `pad_creation_gate.py`, que ja
  roda em PreToolUse Write): `# problema:` (≤100 chars), `# sessao:` (session_id do
  payload do hook), `# data:`, `# skill-candidata: avaliar | nao (one-off) |
  coberto-por:<skill> | estende:<skill> — <limitacao>`.
- **Zona ampliada**: `operational_script_globs` passa a cobrir scripts NOVOS em
  `scripts/**` (enforce-added; sem retrofit dos ~950 existentes).
- **Loop periodico** (cron, espelho do D8): etapa deterministica (git diff desde
  checkpoint + header + cruzamento com clusters web p/ C1) → LLM so no residuo →
  veredito em sidecar `scripts/audits/skill_candidates.json` (path + content-hash +
  veredito + data; anti-revisita por hash) → candidatos → Inbox/dialogue.

## Decisoes em aberto

- Limiar exato de "Bash substantivo" (chars minimos; sugerido 200) — calibrar no
  plano de implementacao com transcripts reais.
- `retries_sessao`: heuristica exata de "tentativa com erro no mesmo assunto"
  (tool_result com exit code != 0 na mesma janela) — fechar no plano.

## Arquivos-alvo

| Arquivo | Mudanca |
|---------|---------|
| `app/agente/models.py` | model `AgentAdhocScript` |
| `migrations/...` (DDL + Python, par) | tabela + indices |
| `app/agente/services/adhoc_capture_service.py` (novo) | filtro, extracao, cluster, disparo |
| `app/agente/workers/background_jobs.py` | job + enqueue |
| `app/agente/routes/_helpers.py` | gatilho `_maybe_trigger_adhoc_capture` |
| `app/agente/config/feature_flags.py` | 6 flags |
| `tests/agente/services/test_adhoc_capture.py` (novo) | cobertura pytest |
