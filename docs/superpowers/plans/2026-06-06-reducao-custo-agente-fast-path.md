<!-- doc:meta
tipo: how-to
camada: L3
sot_de: plano de reducao de custo do Agente Web via fast-path deterministico + downgrade de modelo para rotinas
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-06
-->

# Redução de Custo do Agente — Fast-path Determinístico + Downgrade de Modelo

> **Papel:** plano executável e blindado para reduzir o custo do Agente Web **sem cortar
> conversa e sem prejudicar resultado**, tirando tarefas ROTINEIRAS + ESTRUTURADAS do loop
> Opus (caro) e resolvendo-as por (a) fast-path determinístico ou (b) modelo mais barato.
> Origem: avaliação de custo 2026-06-06 (sessão Rafael + Opus 4.8).

> 🔵 **PRÓXIMA SESSÃO — COMECE AQUI.** Leia primeiro: (1) **Regras de execução INVIOLÁVEIS**,
> (2) **O que JÁ EXISTE (não reinventar)**, (3) **Premissas a verificar ANTES**. Depois rode a
> **FASE 0** (medir o baseline de custo) e siga **FASE 1 → 2 → 3** na ordem (gated). Cada FASE
> tem critério de aceitação **determinístico** (pytest + diagnóstico de custo antes/depois — **SEM
> LLM eval**, veto do Rafael). NÃO pule a verificação de premissa: 3 das minhas hipóteses
> anteriores estavam erradas até eu checar o código (ver Gotchas). A meta é cortar **~32% do
> custo** ($520/45d ≈ $347/mês) sem tocar o uso genuíno (51% = `conversa_analise`).

## Indice
- [Contexto e diagnóstico](#contexto-e-diagnostico)
- [Princípio organizador](#principio-organizador)
- [O que JÁ EXISTE (não reinventar) — premissas verificadas 2026-06-06](#o-que-ja-existe-nao-reinventar)
- [Regras de execução INVIOLÁVEIS](#regras-de-execucao-inviolaveis)
- [Arquitetura-alvo (os 2 mecanismos)](#arquitetura-alvo)
- [FASE 0 — Baseline de custo + flags](#fase-0-baseline)
- [FASE 1 — Quick win: baseline do Marcus (sai do Opus)](#fase-1-baseline-marcus)
- [FASE 2 — Downgrade de modelo das rotinas (model_router)](#fase-2-downgrade)
- [FASE 3 — Fast-path determinístico da vinculação NF×PO (Gabriella)](#fase-3-vinculacao)
- [FASE 4 — Medir economia real](#fase-4-medir)
- [FASE 5 — Governança](#fase-5-governanca)
- [Mapa de dependências / GATED](#mapa-de-dependencias)
- [Rastreamento (append-only)](#rastreamento)
- [Gotchas desta investigação](#gotchas)
- [Fontes](#fontes)

---

## Contexto e diagnóstico

Medição de custo em PROD (via MCP Render + `agent_sessions.total_cost_usd`, fonte robusta):

| Métrica | Valor |
|---|---|
| Custo all-time | $2.611 (777 sessões) · 30d $1.382 · 7d $562 |
| Média/sessão (7d) | $9,37 · sessão mais cara $151,80 (306 msgs) |
| Cache hit Opus | **81,8%** (já automático, prompt estático — não há ganho aqui) |
| Thinking | **off** por default (output já mínimo) |

**Diagnóstico determinístico** (`scripts/audits/session_automation_audit.py`, 45d, 338 sessões, $1624):
classificou a 1ª mensagem de cada sessão por template regex. **41% do custo ($667) é rotina
estruturada**; economia estimada **$520/45d (~$347/mês, ~32%)**. Os **51% restantes
(`conversa_analise`, $823) são uso genuíno** (dev, análise ad-hoc, problemas pontuais) — **NÃO TOCAR**.

| Categoria (rotina) | Sess | Custo/45d | Tier-alvo | Economia~ | Alvo |
|---|--:|--:|---|--:|---|
| vinculacao_nf_po (Gabriella id 69) | 24 | $238 | sonnet/tier0 | $167 | **FASE 3** |
| recalculo_frete_carvia (Talita id 17) | 4 | $120 | sonnet | $84 | FASE 2/3 |
| baseline (Marcus id 18) | 36 | $90 | **tier0 (script já existe)** | $81 | **FASE 1** |
| consulta_estoque / movimentacao / cotacao | 23 | $155 | tier0 | $139 | FASE 2 |
| faturamento (Sabrina id 83) | 3 | $32 | sonnet (SEFAZ — cuidado) | $23 | FASE 2 |

> Caso canônico (Gabriella, ~diário no Teams): `"vincular o pedido C2615918 na nota 439871 no
> odoo e no frete, validar se tem algum erro e faça o ajuste"` — sempre o mesmo procedimento.

**Becos sem saída já investigados (NÃO repetir):** prompt caching já em 81,8% (automático, não
configurável: `cache_control`/TTL não exposto no SDK 0.2.87 nem no CLI 2.1.167); chamadas LLM
auxiliares **já** em Haiku/Sonnet; subagentes já segmentados (9 opus / 7 sonnet). O único Opus
"caro e mexível" é o **loop principal** — e baixá-lo no geral está **vetado** (prejudica resultado).
A alavanca é **tirar a ROTINA do loop**, não rebaixar o loop.

---

## Princípio organizador

> **Tarefa rotineira + input estruturado + procedimento já codificado = não precisa de Opus a cada
> vez.** O trabalho determinístico JÁ EXISTE (scripts/serviços/skills); o custo é usar o Opus como
> interface conversacional para ele. Resolver = rotear para o determinístico (Tier 0) ou para um
> modelo barato (Sonnet/Haiku), deixando o Opus só para o que é genuinamente ambíguo/conversacional.

**Duas invariantes de qualidade (inviolar):**
1. **Não cortar conversa:** a conversa real continua no Opus (Tier 3). Só sai do Opus o que casa
   um template estável.
2. **Não prejudicar resultado:** operação estruturada tem resultado **determinístico** (mais
   confiável que o LLM). Onde houver ambiguidade (De-Para errado, PO homônimo, SEFAZ), **fallback
   para o LLM** — nunca forçar o fast-path num caso ambíguo.

---

## O que JÁ EXISTE (não reinventar)

> **Verificado por leitura de código em 2026-06-06.** O próximo agente DEVE reler estes arquivos
> antes de propor qualquer coisa — eles encurtam drasticamente o trabalho.

| Recurso | Onde | Implicação |
|---|---|---|
| **Roteador de modelo por regex** | `app/agente/sdk/model_router.py` (`select_model`, `_FAST_MODEL_PATTERNS` ~:28, `log_routing_decision`) | A FASE 2 **estende** isto, não cria. Já mapeia padrão→modelo. |
| Routing já ligado no **Web** | `app/agente/routes/chat.py:143-164` (`select_model(...)`), flag `WEB_SMART_MODEL_ROUTING` | Ponto onde o modelo do turno é escolhido. |
| Routing já ligado no **Teams** | `app/teams/services.py:235 _select_model_for_message` → `model_router.select_model`, flag `TEAMS_SMART_MODEL_ROUTING` | Gabriella/Talita/Sabrina/Marcus são **Teams**. |
| **Script de baseline standalone** | `.claude/skills/gerando-baseline-conciliacao/scripts/gerar_baseline.py` (+ `references/`) | FASE 1: baseline vira cron/botão — o motor já existe. |
| Backend validação NF×PO | `app/recebimento/routes/validacao_nf_po_routes.py`, `services/odoo_po_service.py`, `jobs/validacao_fiscal_job.py` | FASE 3: a vinculação tem backend; falta o orquestrador "(pedido,nota)→vincula". |
| Ponto de entrada Web | `app/agente/routes/chat.py:67 api_chat`, `:631 _stream_chat_response` | Onde um fast-path Tier-0 interceptaria antes do SDK. |
| Diagnóstico de custo | `scripts/audits/session_automation_audit.py` (`--dias N`, `--json`) | Régua de medição antes/depois (FASE 0 e 4). |
| Cálculo de frete | `CalculadoraFrete` (ver skill `cotando-frete`) | FASE 2/3: recálculo CarVia / cotação. |

---

## Regras de execução INVIOLÁVEIS

Herdadas do plano de governança do prompt (validadas pelo Rafael). Valem para QUALQUER sessão.

- **R-EXEC-1 — Prova DETERMINÍSTICA, nunca LLM eval.** Rafael VETA eval LLM ("custou fortuna, nada
  conclusivo"). Cada task prova-se por: **pytest** (lógica) + **`session_automation_audit.py` antes/depois**
  (custo) + **spot-check manual** (qualidade, 2-3 casos). Resíduo de qualidade não-mensurável é aceito
  via spot-check, não framework.
- **R-EXEC-2 — Verificar a premissa ANTES de cada task.** 3 hipóteses minhas estavam erradas até checar
  o código (ver Gotchas). Cada FASE abaixo lista "Premissa a verificar 1º". Se a premissa falhar → a
  task vira **verificação**, não execução.
- **R-EXEC-3 — 1 commit por task; feature flag em toda mudança comportamental; rollback documentado.**
  Sem `[skip render]` (regra global). Flag pronta antes de mergear.
- **R-EXEC-4 — Hipótese barata primeiro.** Se uma rotina "não some do custo", a 1ª suspeita é flag
  (routing desligado), não código.
- **R-EXEC-5 — NÃO baixar o loop principal Opus no geral** (vetado: prejudica resultado). Só rebaixar
  o que casa template estável. `conversa_analise` (default) PERMANECE Opus.
- **R-EXEC-6 — Fallback obrigatório em caso ambíguo.** Fast-path/Sonnet só no caminho feliz; qualquer
  ambiguidade (De-Para inválido, PO homônimo, divergência, SEFAZ) → cai no LLM (gestor-recebimento/Opus).
  "Fazer pela metade" = automatizar o ambíguo. Completude > economia.

---

## Arquitetura-alvo

Dois mecanismos independentes, do mais barato/seguro ao mais ambicioso:

- **Mecanismo A — Tirar do LLM (Tier 0).** A rotina vira uma **ação determinística** (script/cron/botão
  na UI, ou serviço chamado diretamente) que o usuário aciona **sem abrir sessão no agente**. Ex.:
  baseline (FASE 1). Economia ~90%. Risco: nenhum (não passa por LLM).
- **Mecanismo B — Rebaixar o modelo (Tier 1/2).** A rotina continua no agente, mas o **`model_router`**
  escolhe Haiku/Sonnet em vez de Opus quando a 1ª mensagem casa o padrão. Ex.: consultas, cotação,
  CarVia (FASE 2). Economia ~70-90% no turno. Risco: qualidade — mitigado por flag + spot-check + R-EXEC-6.

Tiers de referência (in/out por Mtok): tier0 sem LLM ($0) < Haiku ($0,25/$1,25) < Sonnet ($3/$15) <
Opus ($5/$25). **Output custa 5× o input** — respostas de fast-path devem ser **concisas** (status, não
narração) para economizar output também.

---

## FASE 0 — Baseline de custo + flags

**Gate de tudo (R-EXEC-1).** Sem o baseline congelado, não há como provar economia depois.

| Task | Ação | Critério de aceitação |
|---|---|---|
| T0.1 | Rodar `python scripts/audits/session_automation_audit.py --dias 45 --json` (env `DATABASE_URL_PROD`) e **congelar** o output num snapshot datado (custo total, ranking por categoria, economia estimada). | snapshot salvo (data + números) no rastreamento |
| T0.2 | Verificar estado das flags de routing: `WEB_SMART_MODEL_ROUTING`, `TEAMS_SMART_MODEL_ROUTING` (`config/feature_flags.py` + Render env). Ler `_FAST_MODEL_PATTERNS` atuais (`model_router.py`) e listar quais das categorias-alvo **já** são roteadas. | tabela "padrão→modelo atual" documentada; flags on/off registradas |

**Checkpoint 0 🔴 (Rafael):** baseline confiável + se as flags estão como esperado. Se uma rotina-alvo
já está roteada e ainda aparece cara, R-EXEC-4 (flag/efeito) antes de código.

---

## FASE 1 — Quick win: baseline do Marcus sai do Opus

**Mecanismo A. Maior ROI/esforço.** Marcus (id 18) abre ~36 sessões/45d ($90) só para disparar o
baseline — que **já é um script determinístico** (`gerar_baseline.py`). Tirar do agente = economia
quase total, risco zero.

**Premissa a verificar 1º (R-EXEC-2):** `gerar_baseline.py` roda standalone (lê env/DB, gera Excel)
sem depender do contexto do agente? Confirmar entrypoint, args e saída (provavelmente Excel via skill
`exportando-arquivos` ou S3). Ler `SKILL.md` + `references/FORMATO_ABAS.md`.

| Task | Ação | Critério |
|---|---|---|
| T1.1 | Expor o baseline como **ação determinística**: rota/botão no módulo financeiro (Marcus é Controller) **ou** cron diário (Marcus pede "atualizar baseline" ~diário). Reusar `gerar_baseline.py` (NÃO reescrever a lógica). Verificar se já há tela/menu no financeiro onde encaixar (REGRA DEV: toda tela tem link no menu). | botão/rota OU cron que gera o baseline sem abrir sessão no agente |
| T1.2 | Se cron: registrar conforme `~/.claude/CLAUDE.md` (worker RQ exige 3 arquivos OU OpenClaw cron OU crontab — ver memória `worker_render_filas` e `feedback_openclaw_cron`). Se botão: pytest da rota (auth + gera arquivo). | pytest verde; acesso via UI rastreável (base.html→menu→tela→botão) |
| T1.3 | Comunicar Marcus que o baseline tem caminho próprio (sem agente). | — |

**Checkpoint 1:** Marcus gera baseline sem o agente; pytest verde; (medição em FASE 4: sessões "baseline"
de Marcus despencam).

---

## FASE 2 — Downgrade de modelo das rotinas (model_router)

**Mecanismo B. Alto ROI, baixo esforço (estende o que existe).** As rotinas de **consulta/cálculo**
(consulta_estoque, consulta_movimentacao, cotacao, monitoramento_entrega) e **CarVia recálculo** não
precisam de Opus.

**Premissa a verificar 1º (R-EXEC-2):** ler `_FAST_MODEL_PATTERNS` (`model_router.py:~28`) — quais
padrões já existem e para qual modelo? NÃO duplicar. Entender como `select_model` decide e como o
caller (chat.py:147 / teams services.py) aplica.

| Task | Ação | Critério |
|---|---|---|
| T2.1 | Adicionar/ajustar padrões em `_FAST_MODEL_PATTERNS` para as categorias **tier0/consulta** → **Haiku**, e CarVia/cotação → **Sonnet**. Reusar os regex **já testados** em `scripts/audits/session_automation_audit.py` (`_TEMPLATES`) como ponto de partida — eles foram ancorados em mensagens reais. | pytest do `model_router` (mensagem real → modelo esperado); `conversa_analise` (default) permanece **Opus** |
| T2.2 | Garantir flags `WEB_SMART_MODEL_ROUTING` + `TEAMS_SMART_MODEL_ROUTING` ligadas (R-EXEC-4). | flags on em PROD (env) |
| T2.3 | **NÃO** rebaixar: vinculacao_nf_po (FASE 3, tem ambiguidade), faturamento SEFAZ (irreversível — manter Opus ou gate explícito), financeiro (julgamento). | esses padrões NÃO entram no downgrade automático |

**Checkpoint 2 🔴 (Rafael):** spot-check manual (R-EXEC-1) — 2-3 consultas reais respondidas em
Haiku/Sonnet mantêm qualidade. Se degradar → reverter o padrão (flag/lista). Sem golden LLM.

---

## FASE 3 — Fast-path determinístico da vinculação NF×PO (Gabriella)

**Maior ROI absoluto ($167/45d), maior esforço.** Mecanismo A+B combinados.

**Premissa a verificar 1º (R-EXEC-2):** mapear o fluxo end-to-end que o `gestor-recebimento`/skills
`validacao-nf-po`+`conciliando-odoo-po` executam para "vincular pedido C-XXX na nota YYY no odoo e no
frete". Existe um **serviço orquestrador** ou é o LLM que encadeia? Ler `app/recebimento/services/
odoo_po_service.py`, `jobs/validacao_fiscal_job.py`, `routes/validacao_nf_po_routes.py` (CRUD De-Para
já existe; achar o endpoint/serviço de **vínculo + finalização** `bloqueado→finalizado_odoo`).

| Task | Ação | Critério |
|---|---|---|
| T3.1 | **Mapear** (subagente Explore/Plan, read-only) o caminho determinístico: dado `(num_pedido, num_nota)` → match itens (tolerâncias preço 0%/qtd 10% da skill) → resolver `sem_po` falso-positivo (PO sincronizou após match) → apontar PO↔DFE no Odoo + atualizar validação no frete. Identificar o que já é serviço vs o que o LLM faz. | documento de fluxo com gaps (o que falta para ser 1 chamada determinística) |
| T3.2 | Implementar/expor **serviço orquestrador** `vincular_pedido_nota(pedido, nota)` reusando os serviços existentes (NÃO reescrever Odoo calls). Casos ambíguos (De-Para inválido, PO homônimo, divergência fora de tolerância) → **retorna "precisa humano/LLM"** (R-EXEC-6), não tenta adivinhar. | pytest do serviço (caminho feliz + cada caso ambíguo retornando fallback) |
| T3.3 | Acionamento: (a) regex no `model_router`/fast-path intercepta `vincular .* pedido C\d+ .* nota \d+` → chama o serviço → resposta concisa; (b) fallback ao `gestor-recebimento` (Opus) quando o serviço sinaliza ambíguo. Decidir Web vs Teams (Gabriella é Teams). | trivial vinculado sem Opus; ambíguo cai no LLM; pytest do roteamento |

**Checkpoint 3 🔴 (Rafael):** spot-check com vinculações reais recentes da Gabriella (summaries de
sessões dela) — caminho feliz idêntico ao do agente; ambíguo corretamente desviado. **Sem isso, não
ligar** (flag).

---

## FASE 4 — Medir economia real

| Task | Ação | Critério |
|---|---|---|
| T4.1 | Após ≥1 semana com as FASES ligadas, re-rodar `session_automation_audit.py --dias 14` e comparar com o baseline (FASE 0). | delta de custo por categoria documentado |
| T4.2 | Validar que o uso genuíno (`conversa_analise`) **não** caiu (sinal de over-routing — rotinas legítimas viradas fast-path por engano). | conversa_analise estável; sem reclamação de qualidade |

---

## FASE 5 — Governança

| Task | Ação | Critério |
|---|---|---|
| T5.1 | Documentar em `app/agente/CLAUDE.md` o mecanismo (fast-path + model_router) e o **checklist** "antes de rotear uma rotina: tem fallback para ambíguo? mede custo antes/depois?". | seção registrada |
| T5.2 | Adicionar `session_automation_audit.py` à cadência de review de custo (ex.: mensal). | gatilho registrado |

---

## Mapa de dependências / GATED

```
FASE 0 (baseline) ──► FASE 1 (baseline Marcus, independente, quick win)
                 └──► FASE 2 (downgrade modelo) ──► FASE 3 (fast-path vinculação)
                                                          └──► FASE 4 (medir) ──► FASE 5 (governança)
```
- FASE 1 é independente e de maior ROI/esforço → **comece por ela após a FASE 0**.
- FASE 3 depende do mapeamento (T3.1) — não implementar antes de entender o fluxo existente.
- Uma sessão produtiva = **FASE 0 + FASE 1 + FASE 2** (quick wins, baixo risco). FASE 3 pode ser sessão própria.

---

## Rastreamento (append-only)

> Marcar `[x]` + SHA conforme completa. NÃO reescrever histórico.

- [ ] T0.1 baseline de custo congelado — _snapshot:_
- [ ] T0.2 flags + padrões atuais mapeados — _SHA:_
- [ ] T1.1 baseline como ação determinística — _SHA:_
- [ ] T1.2 cron/rota + pytest + acesso UI — _SHA:_
- [ ] T1.3 Marcus comunicado — _data:_
- [ ] T2.1 padrões no model_router — _SHA:_
- [ ] T2.2 flags de routing on — _SHA:_
- [ ] T2.3 exclusões (vinculação/SEFAZ/financeiro) garantidas — _SHA:_
- [ ] T3.1 mapa do fluxo de vinculação — _doc:_
- [ ] T3.2 serviço orquestrador + fallback — _SHA:_
- [ ] T3.3 acionamento + fallback LLM — _SHA:_
- [ ] T4.1 re-medição vs baseline — _snapshot:_
- [ ] T4.2 conversa_analise estável — _verificação:_
- [ ] T5.1 doc do mecanismo — _SHA:_
- [ ] T5.2 cadência de review de custo — _SHA:_

**Checkpoints:** C0 🔴 → C1 → C2 🔴 → C3 🔴 → C4 → C5. 🔴 = exige OK do Rafael.

---

## Gotchas

> Erros que EU cometi/quase cometi nesta sessão. O próximo agente NÃO deve repetir.

1. **`agent_session_costs` é deprecated.** 2ª via per-message que nunca populou de forma confiável.
   **Use `agent_sessions.total_cost_usd`** (coluna, sempre funcionou) para custo. Para breakdown de
   cache/modelo, `agent_invocation_metrics` ou logs `[COST_TRACKER]`.
2. **`recorded_at` é UTC; `agent_sessions.created_at` parece UTC aqui** (confirmei via epoch do
   `message_id`). Mas há gotcha histórico de BRT-naive em algumas tabelas — confira antes de janelar.
3. **Análise por `tipo_atividade` do summary ENGANA (multi-label).** Uma sessão conta o custo inteiro
   em cada atividade → inflou "monitoramento_entrega" para $880 (era artefato). A atribuição correta é
   por **1ª mensagem** (assunto dominante) = `session_automation_audit.py`. monitoramento como assunto
   principal é só ~$21.
4. **Classificar pela 1ª mensagem SUBESTIMA** (saudações/contexto antes do pedido). O número é um
   **piso**. Ao refinar regex, ancore em mensagens REAIS (amostre as caras via MCP) e adicione testes.
5. **Não baixar o loop principal Opus** (vetado) e **não automatizar `conversa_analise`** (uso genuíno,
   51% do custo). Faturamento toca SEFAZ (irreversível) — NÃO automatizar full.
6. **Cache/TTL não é alavanca:** já 81,8% automático; `cache_control`/TTL não exposto no SDK 0.2.87 nem
   no CLI 2.1.167. Não perca tempo aqui.
7. **Output custa 5× input** e, em sessão longa, vira input dos turnos seguintes (efeito composto).
   Respostas de fast-path devem ser concisas.
8. **Há sessão(ões) paralela(s) do Rafael** (ele roda múltiplas). Antes de push: `git log
   origin/main..HEAD` pode ter commits dele; coordene (rebase). Veja memória `feedback_pedir_permissao_branch`.

---

## Fontes
- `scripts/audits/session_automation_audit.py` (diagnóstico; 13 pytest em `tests/audits/`)
- `app/agente/sdk/model_router.py` (`select_model`, `_FAST_MODEL_PATTERNS`), `app/agente/routes/chat.py:67,143,631`
- `app/teams/services.py:235` (`_select_model_for_message`)
- `.claude/skills/gerando-baseline-conciliacao/scripts/gerar_baseline.py`
- `app/recebimento/routes/validacao_nf_po_routes.py`, `services/odoo_po_service.py`, `jobs/validacao_fiscal_job.py`
- Skills: `validacao-nf-po`, `conciliando-odoo-po`, `cotando-frete`, `gerindo-carvia`; subagente `gestor-recebimento`
- Custo PROD: MCP Render `dpg-d13m38vfte5s738t6p50-a` (`agent_sessions.total_cost_usd`)
- Plano-irmão (mesmas R-EXEC): `docs/superpowers/plans/2026-06-04-refactor-governanca-prompt-agente.md`
