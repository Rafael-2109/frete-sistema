<!-- doc:meta
tipo: explanation
camada: L3
sot_de: arquitetura de handoff de sessao do Agente Web (reducao de custo + qualidade)
hub: docs/superpowers/specs/INDEX.md
superseded_by: —
atualizado: 2026-06-29
-->

# Handoff de Sessão do Agente Web — redução de custo + qualidade

> **Papel:** spec de design da rearquitetura de delegação do Agente Web — substituir o subagente efêmero (Task one-shot, re-spawnado a cada turno) por **handoff de sessão** (um especialista quente assume a conversa) + **subagente dedicado como executor atômico**. Consolida TODOS os achados, bugs e correções da sessão de investigação de custo de 2026-06-28 (SOT = export do Claude Console). Documento autossuficiente: feito para uma sessão limpa de implementação começar daqui sem re-descobrir.
>
> **Status:** PROPOSTA — aguardando aval para implementar. Bugs marcados ✅ FEITO já foram aplicados nesta sessão.

## Indice

- [Contexto](#contexto)
- [TL;DR](#tldr)
- [Achados de custo (SOT)](#achados-de-custo-verificados--sot)
- [Bugs e imprecisões encontrados](#bugs-e-imprecisoes-encontrados-com-estado)
- [A imprecisão do /tmp](#a-imprecisao-do-tmp-correcao-factual)
- [Solução proposta](#solucao-proposta)
- [Alternativas descartadas](#alternativas-avaliadas-e-descartadas-com-numeros)
- [Invariantes a preservar](#invariantes-a-preservar-nao-quebrar)
- [Plano faseado](#plano-faseado-gated)
- [Critérios de aceite](#criterios-de-aceite)
- [Arquivos relacionados](#arquivos-relacionados-mapa)
- [Referências](#referencias)

---

## Correção de premissa + Verificação pendente (2026-06-29)

> Adendo da sessão de avaliação do PR #28 (Claude Code dev). NÃO reescreve o design abaixo — corrige uma premissa de FATO e registra o que falta TESTAR antes de decidir o 8b. Hipóteses ainda NÃO confirmadas por execução; só por leitura de doc + inspeção do SDK instalado.

**PREMISSA CORRIGIDA.** Esta spec assume que o subagente Task é efêmero/amnésico e NÃO pode ser mantido quente nem re-endereçado (é a justificativa central do handoff). **Isso é FALSO no Claude Agent SDK 0.2.x.** A doc oficial tem a seção **"Resuming subagents"**: a tool `Agent` retorna `agentId` no resultado, e o subagente PODE ser retomado com **contexto completo** (histórico/tool-calls/raciocínio) via `resume=session_id` + `agentId` no prompt + a MESMA `AgentDefinition`. Confirmado contra o SDK INSTALADO (campos `resume`/`fork_session`/`session_store` em `ClaudeAgentOptions`; `SessionStorageKey.subpath="subagents/agent-{id}"`; `_internal/session_resume.py`).

**O que isso abre (3º caminho para o 8b):** **subagente retomável** dentro da sessão do principal — resolve a metade "re-descoberta" do custo, é mais simples que o pool-multi-cliente, e **NÃO tem** o risco de 2 subprocessos no mesmo `sdk_session_id` (o gap que travou o 8b). Porém **NÃO** resolve a outra metade ("principal re-medeia todo turno") — o handoff F1 resolve as duas. **Escolha = MEDIR, não deduzir.**

**HIPÓTESES A VALIDAR/REFUTAR NA PRÓXIMA SESSÃO (empírico > leitura; re-verificar a FONTE):**

| # | Hipótese | Como provar | Fonte a re-verificar |
|---|---|---|---|
| H1 ✅ | Subagente é retomável por `resume`+`agentId` com contexto completo — **CONFIRMADO POR EXECUÇÃO 2026-06-29** (ver bloco abaixo) | **RODAR** o exemplo `query()` da doc no `.venv` e confirmar que o subagente retomado NÃO re-lê arquivos / mantém histórico | doc "Resuming subagents" — `https://code.claude.com/docs/en/agent-sdk/subagents` (obtida via **WebFetch = resumo de modelo pequeno** → re-fetch RAW/browser; confirmar domínio oficial) + CHANGELOG `github.com/anthropics/claude-agent-sdk-python` |
| H2 | Resume-subagente compõe com `ClaudeSDKClient` (pool quente), não só `query()` | Testar `resume`+`agents`+`session_store` via `ClaudeSDKClient` no harness do pool (a doc só demonstra `query()`) | SDK instalado `_internal/session_resume.py` + `session_mutations.py::fork_session` |
| H3 ❌ | Resume-subagente é mais BARATO que o cliente quente — **REFUTADA 2026-06-29** (A custa 1.32x B; ver bloco abaixo) | Spike A/B numa tarefa real de recebimento: `cache_read` vs `cache_creation` + custo/turno | medição própria (sem doc) |
| H4 | PR #28 flag-off segue behavior-equivalent APÓS reconciliar com `origin/main` (8 commits behind) | merge main → re-rodar F1+permissões+Teams na base RECONSTRUÍDA; smoke Teams; log prod `"Dead client evicted"` | suíte local + MCP Render |
| H5 | Fix do blocker (eviction) funciona end-to-end (não só `evict_client` unitário) | teste de integração: handler ProcessError/CLIConnectionError → eviction → recriação no próximo turno | `client.py` (3 sites) + `client_pool.evict_client` |
| H6 | 4º produto **Managed Agents** (server-side, agente persistente por ID) — viável/custo? | só se H1–H3 não bastarem; é reescrita (sai do `claude-agent-sdk`/CLI) | skill `claude-api` §Managed Agents (re-verificar fonte) |

**Achados detalhados desta verificação (sessão CC, efêmeros):** `/tmp/subagent-findings/VEREDITO_SUBAGENT_RESUMIVEL.md` — re-gerar se sumirem.

### Resultado H1 — ✅ CONFIRMADO POR EXECUÇÃO (2026-06-29)

**Provado** (2 spikes no `.venv`, SDK 0.2.101 + CLI 2.1.195, custo total ~$0.21): o subagente Task **retém seu próprio transcript e é retomável por `agentId`**, condicionado a `resume=session_id`. Prova **isolada** (v2): segredo gerado DENTRO do subagente (passphrase 5 palavras), com o principal **sem** `Read/Grep/Bash` e que nunca viu o segredo → ao retomar, o subagente devolveu o segredo exato (iniciais batem com a âncora da 1ª invocação: `Q-M-T-V-S` → `Quixotic-Melancholy-Turbulent-Velvet-Serendipity`); **sem** `resume`, "no transcript / cleaned up". Fonte re-verificada em 3 níveis (doc `.md` oficial + CHANGELOG raw `#825`/`#805`/`#905` + símbolos do SDK instalado) — não mais WebFetch=resumo.

**Achado de design (muda o desenho do 8b):** no runtime atual o resume concreto é a tool **`SendMessage(to:<agentId>)`**, **ASSÍNCRONO** ("resumed from transcript in the background… you'll be notified when it finishes" + `Output:` path) — **não** "agentId em texto no prompt" como a doc conceitua. O handoff precisa lidar com notificação assíncrona (`TaskNotification`). SOT detalhado: `/tmp/subagent-findings/VEREDITO_SUBAGENT_RESUMIVEL.md`.

**Pendências reais (não cobertas por H1):** **H2** (compõe com `ClaudeSDKClient` quente? o padrão async cabe no loop request/response web/Teams?) e **H3** (custo A/B). H1 confirma a **viabilidade técnica** do 3º caminho; a ESCOLHA do 8b segue dependendo de H2+H3.

### Resultado H2+H3 (2026-06-29)

- **H2 ✅ CONFIRMADO** — `h2_client_resume.py`: dentro de UM `ClaudeSDKClient` persistente (pool quente), o subagente do turno 1 foi re-endereçado no turno 2 via `SendMessage` (mesma sessão automática, **sem** `resume` explícito; resposta assíncrona entregue no mesmo turno). O "subagente retomável" cabe no pool quente existente **sem 2º subprocesso** — derruba o gap "2 subprocessos no mesmo `sdk_session_id`".
- **H3 ❌ REFUTADA (direção)** — `h3_cost_ab.py` (4 turnos, mesmo doc de recebimento, Haiku): **A** subagente-retomável (principal re-medeia) = **$0.2704**; **B** especialista-quente direto = **$0.2056** → **A custa 1.32x B**. O subagente-retomável NÃO captura a economia (paga a mediação do principal todo turno; `cache_read` 4,7x maior). Em prod a vantagem de B tende a crescer (principal real carrega system_prompt + skills + MCP).
- **Direção do 8b (a ratificar 4-mãos):** manter o **handoff F1 (especialista quente conduz)** como solução de custo; **subagente-retomável** reservado ao **executor atômico** do ato irreversível — convergente com o design já escrito abaixo. Tabela comparativa dos 3 caminhos: `/tmp/subagent-findings/VEREDITO_SUBAGENT_RESUMIVEL.md` §Recomendação consolidada.

## Contexto

Investigação de custo conduzida em 2026-06-28 a partir do **SOT real** (export CSV do Claude Console — `claude_api_tokens_2026_0{5,6}.csv`, token-based, o que a Anthropic cobra), corrigindo o dashboard interno (`agent_sessions`/`agent_session_costs`), que estava inflado. A investigação descartou as soluções de fundo caras e localizou o driver estrutural real (multi-spawn de subagente). Esta spec consolida tudo para execução.

**Fronteira de faturas (premissa do usuário — confirmada):**
- **Fatura da API Anthropic** (api-key única `rafael-onboarding-api-key`, workspace `Default`) = **PRODUÇÃO**: agente web + Teams + agente lojas + eventuais `claude -p` de automação/cron.
- **Claude Code dev interativo = OUTRA fatura** (assinatura) — NÃO entra no CSV. Exceção: `claude -p` headless de automações.
- Logo, **não há "fatia de dev escondida"** na fatura da API. Modelos legados no CSV (`opus-4-7/4-6`, `sonnet-4-5`) = **agente web antes da migração para 4-8**, não dev.

---

## TL;DR

- O custo **real** do Agente Web (fatura Anthropic, token-based) é **~$1.830/mês (~R$9.900)**, não os ~$2k que o dashboard interno sugeria — e **cresceu +155% real de maio→junho** (volume novo + sessões longas). É curva, não platô.
- **Caching já está maximizado** (99,5% hit). **Self-host e troca de provedor são inviáveis** (provados com números). A economia "sem perder qualidade" é modesta (~15-20%) por otimizações pontuais — MAS a maior alavanca estrutural é **eliminar o multi-spawn de subagentes** (88% do custo de subagente = ~$636/mês), que também **degrada qualidade** (subagente amnésico re-pesquisa e fica incoerente entre spawns).
- **Solução:** o principal **passa a sessão a um especialista quente** (handoff), que conduz o assunto, responde direto ao usuário e mantém contexto. O **subagente dedicado vira executor atômico**, chamado pelo próprio especialista só para o ato irreversível (recebe pronto → executa → finaliza numa invocação). A **memória de trabalho** (`/tmp` + S3, que já existe e é compartilhada) cobre retomada.
- Ganho: **~$200-300/mês** de custo + **qualidade** (coerência, menos re-boot). 100% código nosso (não exige mudar o SDK).

---

## Achados de custo (verificados — SOT)

| Métrica | Valor | Fonte |
|---|---|---|
| Custo real maio | $742 (31d) | CSV Console maio |
| Custo real junho | $1.648 (27d) → **~$1.830/mês** | CSV Console junho |
| Crescimento real | **+155%/dia maio→junho** | CSV (por dia) |
| Composição junho | Opus48 ≤200k $777 (47%) · Sonnet46 ≤200k $604 (37%) · **Opus48 200k-1M $218 (13%)** · Haiku+resíduo $48 | CSV por modelo×tier |
| Subagentes (aditivo) | **~$719/mês**, 88% multi-spawn (~$636) | `agent_invocation_metrics` 30d |
| Top subagentes | gestor-estoque-odoo $281 · especialista-odoo $172 · gestor-recebimento $130 (= 81%) | `agent_invocation_metrics` GROUP BY agent_type |
| Cache hit | Opus 99,5% / Sonnet ~100% | `agent_session_costs` cache_*_tokens |
| Caso-ácido multi-spawn | $27 / 10,5M tokens p/ ajustar 2 itens (4 spawns) | memória `delegacao-subagente-custo-arquitetura` |

**Dois drivers do crescimento:** (1) **volume** (novos usuários pesados em junho: Sabrina, Rayssa, Martha); (2) **sessões longas** (contexto >200k: $37 maio → $231 junho, concentrando no fim do mês). Opus 4.x **não tem premium de long-context** — o custo dessas sessões é puramente o contexto grande re-enviado por turno.

**Pricing autoritativo (skill `claude-api` — corrige `pricing.py`):**
- Opus 4.6/4.7/4.8: **$5/$25** · Sonnet 4.5/4.6: **$3/$15** · **Haiku 4.5: $1/$5**.
- ⚠️ `app/agente/sdk/pricing.py` usa Haiku **$0,25/$1,25** — **subestima Haiku 4x**. Corrigir.
- Cache: read **0,10×** · write-5m **1,25×** · write-1h **2,0×** do input. Opus 1M = preço padrão (sem premium).

---

## Bugs e imprecisões encontrados (com estado)

| # | Item | Estado | Ação |
|---|---|---|---|
| B1 | **Inflação ~7x no custo Teams** — `_persist_cost_teams` gravava `agent_result.cost_usd` (cumulativo do SDK) cru, somando por turno. Medido: **$320,87 gravado vs $46,65 real** (30d, 118 turnos). | ✅ **CÓDIGO FEITO** (`services.py` GAP 2 ~L2265, working tree, não deployado) + ✅ **BACKFILL APLICADO PROD 2026-06-28** ($320,87→$46,65, verificado via MCP; `scripts/migrations/2026_06_28_backfill_teams_cost.py`, backup/revert). | Deployar o fix de código (senão re-infla). |
| B2 | **Teams 100% Opus em prod** — env var `TEAMS_DEFAULT_MODEL=claude-opus-4-8` no Render sobrepõe o default Sonnet do código (decisão 16/06 nunca efetivada). | ✅ **FEITO 2026-06-28** — env `TEAMS_DEFAULT_MODEL=claude-sonnet-4-6` aplicada (deploy `dep-d90sbskvikkc738omf8g`). | — |
| B3 | **`/tmp` "não atravessa processo" — IMPRECISO** (ver secao A imprecisão do /tmp). | ✅ **FEITO 2026-06-28** | Comentários corrigidos em `subagent_checkpoint.py:3-11` e `hooks.py` (#3b). /tmp absoluto ATRAVESSA processo; o elo partido era órfandade + efemeridade entre DEPLOYS. |
| B4 | **Checkpoint de subagente** (`AGENT_SUBAGENT_CHECKPOINT`) — shadow, nunca injeta nos alvos interativos; `PendingRollbackError` em 50%+ dos persists; bug truncação-de-cabeça corrigido 26/06 (`c34dac743`) mas efeito **inconclusivo** (data-starved). | Aberto / paliativo | **Substituído** pela arquitetura desta spec. Manter como rede até o handoff provar-se; depois aposentar. |
| B5 | **`vinculacao_fastpath` 0% eficácia** — N0 (regex) não casa; tudo cai no N2 (Opus). Só adiciona latência. | **DECISÃO 2026-06-28: DESLIGAR** | Recomendado `AGENT_VINCULACAO_FASTPATH=false` (env Render, reversível, como B2 — sem deploy). Racional: SOT diz 0% eficácia + tax de Haiku-N1 por mensagem; a F1 substitui o spawn de `gestor-recebimento` (caminho-feliz do fastpath fica redundante). NÃO consertar regex às cegas (sem telemetria que aponte a falha; N1 Haiku já existia p/ variações e tb não casa → problema não é só N0). Código (default `true`) **inalterado** — flag-off é o lever instantâneo. **Ação pendente do usuário** (aval prod). |
| B6 | **Fast-paths do `model_router` em parte letra-morta** — 8 dos 14 padrões com 0 hits; só 21 redirects web em junho (dead-zone de continuações curtas 3-15 palavras não coberto). | **DECISÃO 2026-06-28: NÃO adicionar padrões (defer p/ F1)** | Achado decisivo: `select_model` no web **só roda em sessão FRIA (1ª mensagem)** — sessão quente usa `pick_warm_model` e NÃO roteia; Teams está com `TEAMS_SMART_MODEL_ROUTING=false` (Sonnet fixo, B2). Logo as "continuações curtas" mid-sessão **nunca chegam** ao `select_model` → adicionar padrões = ROI ~zero + risco de rebaixar 1ª-msg complexa. O tratamento real de continuação é a **própria F1** (especialista quente acumula contexto). Sem mudança de código. |
| B7 | **`tool_name` 100% NULL** em `agent_session_costs` — impossível saber qual MCP tool consome mais output. | ✅ **FEITO 2026-06-28** | `_primary_tool_for_cost` (heurística documentada: delegação > skill > MCP > builtin) atribui 1 tool representativo do turno; threaded em `_persist_session_cost`. TDD em `tests/agente/sdk/test_cost_tool_attribution.py`. |
| B8 | **`pricing.py` Haiku 4x subestimado**. | ✅ **FEITO 2026-06-28** | `claude-haiku-4-5-20251001` = `(1.00, 5.00)`. Regressão em `tests/agente/sdk/test_pricing_table.py`. |

---

## A imprecisão do /tmp (correção factual)

A análise anterior afirmava que findings em `/tmp/subagent-findings` "não atravessam processo (TMPDIR divergente)". **Isso está errado.** O código prova (`app/agente/routes/_constants.py:11-17`):

1. **`/tmp` (raiz) é compartilhado** entre processos/workers no mesmo container — mesmo filesystem.
2. O TMPDIR divergente (`/tmp/claude-{uid}` no subprocesso do CLI vs `/tmp` no gunicorn) **só afeta quem usa `tempfile.gettempdir()`** — não um caminho **absoluto**.
3. `/tmp/subagent-findings` é caminho **absoluto** → **atravessa processo** no mesmo container. A frase em `subagent_checkpoint.py:6` e `hooks.py:1134` é factualmente incorreta.
4. **S3:** `session_archive.py:47-50` arquiva `/tmp/subagent-findings/<session>*.md` em tar.gz no S3 (`agent-archive/`) na expiração da sessão.

**O "elo partido" real NÃO é isolamento de filesystem. É:**
- (a) o principal **nunca lia** os findings — `get_subagent_findings` (`subagent_reader.py:604`) tinha **zero callers** no agente web. ✅ **LIGADO 2026-06-28**: read-back canônico (#3c) no `_subagent_stop_hook` do web, espelhando `_subagent_stop_audit` do agente_lojas — hoje observabilidade (prova de leitura); a F1 consome na retomada do especialista quente;
- (b) **efemeridade entre DEPLOYS** (Render recicla container) — não entre processos;
- (c) S3 só guarda no archive **pós-expiração** (cold), sem leitura ativa durante a sessão.

**Consequência para o design:** `/tmp` (vivo no container) + S3 (archive) já é um meio de memória de trabalho persistente — só não é lido. A solução abaixo o usa como rede de retomada.

---

## Solução proposta

### Princípio

Em vez de o principal **chamar um ajudante efêmero a cada turno**, ele **promove a sessão a um especialista quente** que vira o interlocutor: as próximas mensagens do usuário vão direto ao especialista, que responde direto e mantém o contexto. Quando o assunto muda, troca-se o agente ativo (outro especialista ou volta ao principal).

### Dois papéis distintos (decisão de design central)

| Papel | O que é | Como é invocado | Vida |
|---|---|---|---|
| **Especialista (quente)** | Assume a conversa sobre um domínio (estoque-odoo, recebimento...). Pensa, dialoga, planeja, confirma com o usuário. | **Handoff** do principal: troca do cliente ativo da sessão + contexto magro. | **Persistente** (sessão SDK quente, cache read, contexto acumula). |
| **Subagente dedicado (executor atômico)** | Executa UM ato irreversível (transmitir SEFAZ, validar picking). | Chamado **pelo próprio especialista** (não pelo principal), com TUDO pronto. | **One-shot**: recebe → processa → executa → **finaliza**. NUNCA "devolve e volta". |

> **Refinamento do usuário (D-1, central):** o subagente dedicado só se justifica quando **recebe, processa, executa e finaliza** numa única invocação. Usá-lo como "consultor" (devolve resposta, é re-chamado depois) recria o multi-spawn caro e sem efetividade (2 invocações frescas que não finalizam). Pensar/dialogar é função do **especialista quente**; o subagente é a barreira de atenção isolada **só do ato irreversível**.

### Componentes técnicos (camada da aplicação — não muda o SDK)

1. **Pool multi-agente por sessão** — estender `client_pool.py`: de UM cliente quente para **N clientes por papel** (principal + especialistas), cada um com seu `system_prompt`/`skills`/`tools` e sua sessão SDK quente.
2. **Roteador de agente** — irmão do `model_router.py` já existente. Decide qual cliente atende cada mensagem. Estado `agente_ativo` persistido em `AgentSession.data` (R7: `flag_modified`).
3. **Handoff via tool** — o principal ganha `transferir_para(especialista, contexto_magro)`. Em vez de spawnar Task, o roteador **troca o cliente ativo** e injeta `contexto_magro` (handoff **tipado magro**: entidades resolvidas, saldo, objetivo — NÃO a conversa inteira; estimativa estoque 43,5k→5k).
4. **Executor atômico** — o especialista chama o subagente dedicado (Task one-shot) **só** para o ato irreversível, passando os parâmetros já resolvidos. Dry-run/confirmação acontecem **no especialista quente** (barato), antes; o subagente só executa o `--confirmar` e encerra.
5. **Reversão** — `devolver_ao_principal()` quando o assunto sai do escopo, ou detecção no roteador.
6. **Memória de trabalho** — o especialista grava findings em `/tmp/subagent-findings` (já faz) e **lê os próprios findings no início** ao retomar; S3 archive cobre retomada cross-deploy. Liga o `get_subagent_findings` órfão.

### Por que reduz custo

Elimina os dois drivers do multi-spawn: **re-boot por turno** (sessão quente = cache *read*, não *creation* — corta a re-leitura do escudo de 41KB + auto-carga de skills) e **re-descoberta** (contexto acumula no especialista). Alvo: ~$636/mês de multi-spawn. **Ganho realista ~$200-300/mês** (eliminar metade do overhead medido em ~$520/mês upper-bound).

### Por que aumenta qualidade

- **Coerência**: hoje cada spawn é amnésico e pode chegar a conclusões diferentes a cada vez (inconsistência real medida — 3 dos 4 spawns abrindo idênticos, re-pesquisando). O especialista quente mantém o fio.
- Mais tokens para o trabalho real (menos boot).
- O usuário conversa com **um** especialista contínuo, não com N spawns desconectados.
- O ato irreversível ganha barreira de atenção isolada **e** finaliza (sem ida-e-volta que não conclui).

---

## Alternativas avaliadas e DESCARTADAS (com números)

| Alternativa | Veredito | Prova |
|---|---|---|
| Self-host (Llama/Qwen, 2× A100) | ❌ custa mais | ~$3.635/mês GPU > $1.830 fatura; qualidade inferior pt-BR + tool-calling Odoo/SEFAZ |
| Trocar provedor (DeepSeek/GPT/Gemini) | ❌ fora da janela | Agent SDK é Anthropic-only; reescrita 5-9 meses → payback mês 10-15 |
| Caching semântico de respostas | ❌ ROI baixo | Queries parametrizadas → hit 3-8%; fast-path determinístico cobre melhor |
| Batch API | ❌ irrelevante | SDK = subprocess streaming, incompatível; só background (~$5-10/mês) |
| Prompt caching | ✅ já no talo | 99,5% hit — sem ganho adicional |

**Critério do "payback de 9 meses":** serve só para REJEITAR as de fundo. As otimizações desta spec se pagam em semanas (investimento = tempo de dev).

---

## Invariantes a preservar (NÃO quebrar)

- **Dry-run default + R11/R12 + gate `permissions.py` por-nome-de-skill {1,55} + audit hook R9** — intactos no executor atômico.
- **Isolamento de atenção** para operações irreversíveis (SEFAZ/faturar) — mantido via subagente dedicado (agora chamado pelo especialista).
- **Governança do prompt** (`app/agente/CLAUDE.md` FASE 5): qualquer mudança em `system_prompt`/listing/hook passa pelo checklist PAD-CTX + `prompt_size_audit.py --check-delta`.
- **Regra de export Teams**: mudança em `client.py`/`permissions.py`/`feature_flags.py`/`models.py`/`session_persistence.py`/`pending_questions.py` DEVE ser testada no Teams.
- **Cache MODEL/TOOL-scoped**: trocar de agente invalida prefix → 1 cache-write por handoff (aceito; 1× por troca de assunto, não por turno). Handoff magro obrigatório.

---

## Plano faseado (gated)

- **F0 — quick wins independentes (baixo risco, rápido):** ✅ **CONCLUÍDA 2026-06-28** (resta a ação de prod de B5 — flag-off — a cargo do usuário).
  - ✅ Corrigir comentários `/tmp` (B3) + ligar `get_subagent_findings` (read-back canônico no SubagentStop do web).
  - ✅ Corrigir `pricing.py` Haiku (B8). ✅ Instrumentar `tool_name` (B7).
  - ✅ Remover env var Teams Opus (B2). ✅ Backfill custo Teams (B1). *(já fechados antes desta sessão)*
  - ✅ Decidido B5 (**desligar** via env — pendente aval prod) e B6 (**não adicionar** padrões; defer p/ F1 — `select_model` só roda em sessão fria).
- **F1 — piloto handoff (UM especialista):** `gestor-estoque-odoo` OU `gestor-recebimento` (interativos plano→confirma→executa). Pool multi-agente + roteador + tool `transferir_para` + handoff magro + reversão + executor atômico. Atrás de flag (off/shadow/on/admin). **Métrica de gate:** cache_read/creation e custo/sessão dos spawns não-primeiros, antes vs depois.
- **F2 — estender + memória de trabalho:** demais especialistas interativos + leitura de findings `/tmp` vivo + S3 retomada cross-deploy. Aposentar o checkpoint (B4) se o handoff superá-lo.
- **F3 — governança:** critério "merece especialista quente vs executor atômico vs principal direto"; baseline de custo com alarme.

> O **plano de execução TDD task-by-task** (par em `docs/superpowers/plans/`) é gerado na sessão de implementação a partir desta spec.

---

## Critérios de aceite

- [x] F0: comentários `/tmp` corrigidos; `get_subagent_findings` com caller ativo (read-back #3c no web); `pricing.py` Haiku = $1/$5; `tool_name` populado (`_primary_tool_for_cost`); env var Teams = Sonnet; backfill Teams aplicado (idempotente/reversível). *(B5 decidido = desligar; ação de env a cargo do usuário.)*
- [ ] F1: handoff de UM especialista em produção atrás de flag, com rollback instantâneo (flag off).
- [ ] F1: handoff magro mensurável (<10k tokens injetados no handoff típico).
- [ ] F1: GATE — custo médio por sessão multi-assunto do especialista cai vs baseline de multi-spawn, SEM aumento de num_turns por degradação (se turns sobe = perdeu contexto = reverter).
- [ ] F1: executor atômico preserva dry-run/R11/R12/gate/audit (testes verdes).
- [ ] Qualidade: ausência de re-descoberta nos spawns não-primeiros (cache_read não infla a cada confirmação).
- [ ] Irreversível (SEFAZ/faturar) continua isolado em subagente dedicado, chamado pelo especialista, finalizando em 1 invocação.

---

## Arquivos relacionados (mapa)

| Arquivo | Papel na solução |
|---|---|
| `app/agente/sdk/client_pool.py` | Pool de clientes — **estender p/ multi-agente por sessão** |
| `app/agente/sdk/model_router.py` | Modelo de roteador — **espelhar p/ agent_router** |
| `app/agente/routes/chat.py` | Loop SSE / persistência — ponto de roteamento por mensagem |
| `app/agente/sdk/subagent_checkpoint.py` | Paliativo atual (B4) — corrigir comentário /tmp; aposentar pós-F2 |
| `app/agente/sdk/subagent_reader.py:604` | `get_subagent_findings` órfão — **ligar (F0)** |
| `app/agente/sdk/hooks.py:1134` | Comentário /tmp impreciso (B3) + injeção PreToolUse Task |
| `app/agente/sdk/session_archive.py:47-50` | Archive S3 dos findings (memória de trabalho) |
| `app/agente/routes/_constants.py:11-17` | Prova do /tmp compartilhado + TMPDIR |
| `app/agente/sdk/pricing.py` | Tabela de preços (B8 Haiku) |
| `app/agente/config/feature_flags.py` | Flags (handoff, checkpoint, fastpaths, Teams) |
| `app/teams/services.py` (GAP 2 ~L2265) | ✅ fix B1 aplicado |
| `.claude/agents/*.md` | Frontmatter dos especialistas (model/effort/skills/tools) |

---

## Referências

- Memória `delegacao-subagente-custo-arquitetura` — análise do $680/30d, Rota A/B, roadmap F0-F4, caso-ácido.
- Memória `custo-agente-web-sot-2026-06` — SOT real, composição, drivers, bugs.
- Memória `bug-custo-agente-double-count-cumulativo` — fix web `0e9403082` (Teams era o resíduo, agora ✅).
- `app/agente/CLAUDE.md` — arquitetura 5 camadas, governança do prompt, telemetria subagent.
- `app/teams/CLAUDE.md` — drift Teams Opus + fix B1.
- `.claude/references/SUBAGENT_RELIABILITY.md` — findings via JSONL, /tmp como rede.
- skill `claude-api` — pricing autoritativo.
- SOT: `claude_api_tokens_2026_05.csv`, `claude_api_tokens_2026_06.csv` (Claude Console export).
