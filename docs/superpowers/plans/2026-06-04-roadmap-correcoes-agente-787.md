<!-- doc:meta
tipo: how-to
camada: L3
sot_de: —
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-04
-->
# Roadmap de Correções do Agente Web — achados da avaliação da sessão #787

> **Papel:** rastreador dos 7 achados (P1–P7) da avaliação da sessão web #787 ("gere um relatório em Excel das motos HORA" → "arquivo está vazio"). Garante que NENHUM fix se perca. **A próxima sessão começa pelo Fix B** (doc de design dedicado); P4–P7 ficam aqui como backlog com evidência.
> **For agentic workers:** este doc é um índice de prioridades, NÃO o plano de implementação. O plano do Fix B é `2026-06-04-redesign-consultar-sql-sql-first.md`. P4–P7 ainda precisam de brainstorming/plano antes de implementar.

## Indice

- [Como iniciar a próxima sessão](#como-iniciar-a-proxima-sessao)
- [Roadmap — status dos 7 achados](#roadmap-status-dos-7-achados)
- [P1 — TMPDIR / Excel vazio (FEITO)](#p1)
- [P2+P3 — mcp__sql reescreve SQL + sem caminho SQL→Excel (Fix B, PRÓXIMO)](#p2-p3)
- [P4 — Idioma (inglês) + descoberta de schema ineficiente](#p4)
- [P5 — Detector de frustração falhou (falso negativo)](#p5)
- [P6 — Summary da sessão enganoso (gerado no meio)](#p6)
- [P7 — Judge/verify shadow: detectam mas não previnem + lacuna de verifier de entrega](#p7)
- [Nota de processo — subagentes de leitura deram veredito raso](#nota-de-processo)
- [Contexto da sessão #787 (âncoras)](#contexto-da-sessao-787)

---

## Como iniciar a próxima sessão

1. ~~**Foco primário: Fix B**~~ ✅ **EM PROD** (2026-06-04, mergeado em `main` `e3bf4908c`, flag `SQL_AGENT_SQL_FIRST=on` LIVE + hardening F1/F2, 79 testes). Plano + runbook: `docs/superpowers/plans/2026-06-04-redesign-consultar-sql-sql-first.md`.
2. **P4–P7** na ordem — correções independentes, cada uma pequena. **P4 ✅ FEITO** (2026-06-04, branch `fix/agente-787-p4-p7`). Seguir **P5 → P6 → P7**. Cada item abaixo traz a evidência (arquivo:linha / id).
3. Regra: cada fix em PR próprio, flag/canary quando muda comportamento, teste antes (TDD).

## Roadmap — status dos 7 achados

| ID | Achado | Natureza | Status | Onde resolver |
|----|--------|----------|--------|---------------|
| **P1** | Excel "vazio" no download (TMPDIR mismatch) | I/O — causa-raiz | ✅ **FEITO** (origin/main `788f76f07`, deploy `dep-d8gqa8mrnols73cmjrng`) | — |
| **P2** | `mcp__sql` reescreve/trunca/alucina o SQL do agente | Ferramental | ✅ **EM PROD** (`main` `e3bf4908c`, SQL-first com `SQL_AGENT_SQL_FIRST=on` LIVE, 79 testes + hardening F1/F2) | Fix B (doc dedicado) |
| **P3** | Sem caminho de 1ª classe "SQL complexo → Excel" | Ferramental | ✅ **RESOLVIDO via Decisão #1 (a)** — agente compõe `consultar_sql` SQL-first → `exportar.py` via stdin (sem improviso Bash) | Fix B (Decisão em aberto #1) |
| **P4** | Agente escreve em inglês no meio do PT-BR + explora tabelas erradas | Prompt/descoberta | ✅ **FEITO** (branch `fix/agente-787-p4-p7`: `<language_policy>` + domínio HORA no `<domain_detection>`, 5 testes) | `system_prompt.md` |
| **P5** | `frustration_score=0` numa reclamação explícita | Sensor (E1) | 📋 backlog | `services/sentiment_detector.py` |
| **P6** | Summary afirma sucesso (gerado antes da falha) | Sensor (E) | 📋 backlog | `services/session_summarizer.py` |
| **P7** | Judge/verify detectam a falha mas não previnem; judge crédulo; sem verifier de ENTREGA | Atuador/blueprint | 📋 backlog | GATE-1/E3 + novo verifier de entrega |

---

<a id="p1"></a>
## P1 — TMPDIR / Excel vazio ✅ FEITO

`exportar.py` gravava em `tempfile.gettempdir()` = `/tmp/claude-{uid}/agente_files` (o CLI do Agent SDK seta `TMPDIR=/tmp/claude-{uid}` nos subprocessos Bash), enquanto o gunicorn servia o download de `/tmp/agente_files` → 404 "arquivo vazio". Fix: fonte única `AGENTE_FILES_ROOT` (default `/tmp`) nos 4 call-sites (gravação + leitura). Commit `788f76f07` + teste `tests/agente/test_agente_files_root_consistency.py` (3 casos). Em PROD via deploy `dep-d8gqa8mrnols73cmjrng`.

<a id="p2-p3"></a>
## P2+P3 — mcp__sql + caminho SQL→Excel 🔜 PRÓXIMO (Fix B)

**Plano completo e auto-contido:** `docs/superpowers/plans/2026-06-04-redesign-consultar-sql-sql-first.md`.

Resumo: a tool `consultar_sql` é um tradutor NL→SQL (Generator Haiku, `max_tokens=500`, instruído a **adivinhar** campos — `text_to_sql.py:655,675`), mas o chamador real é o Agente (Opus), que sabe mais que o Generator. O Generator vira camada de _downgrade_ que reescreve/trunca/alucina o SQL correto do agente. Proposta: **SQL-first** — o agente envia SQL; o `SQLDeterministicValidator` (schema real, sem LLM, já existe em `text_to_sql.py:738`) vira guard-rail de entrada e devolve os campos reais quando há erro; Generator NL→SQL vira fallback. Flag OFF + canary. P3 (export consulta banco) é a Decisão em aberto #1 do mesmo doc.

<a id="p4"></a>
## P4 — Idioma (inglês) + descoberta de schema ineficiente ✅ FEITO

**Resolvido (2026-06-04, branch `fix/agente-787-p4-p7`):** (1) **idioma** — bloco `<language_policy>` no topo do `system_prompt.md` (toda saída + raciocínio EXPOSTO em PT-BR, proíbe code-switch para inglês com exemplo); (2) **domínio HORA** — terceira entrada no `<domain_detection>` mapeando "motos/lojas HORA" → tabelas `hora_*` + `consultar_schema`, distinguindo de Nacom (alimentos) e Motos Assai (`assai_*`). Smoke `tests/agente/test_system_prompt_p4.py` (5 testes) trava a presença das regras. Nota: as descrições dos `schemas/tables/*.json` são auto-geradas/regeneradas (não editáveis de forma durável) — por isso a desambiguação vive no prompt.

**Evidência:** no turno 2 da #787 o agente escreveu, na resposta ao usuário PT-BR, trechos em inglês — *"The key tables are `moto`, `pedido_compras`. Let me look at their schemas."*, *"Let me filter them out."*, *"I need the columns…"*. Além disso, foi para `pedido_compras`/`moto` (que são da Nacom — matéria-prima) **antes** de descobrir que o correto era `hora_pedido`/`hora_nf_entrada` — gastando ~20K tokens de output só de exploração.

**Duas frentes:**
1. **Idioma:** reforçar no `app/agente/prompts/system_prompt.md` que TODA a resposta (inclusive o raciocínio exposto) é em PT-BR. Opus code-switcha para inglês sob carga; uma regra explícita + exemplo reduz.
2. **Descoberta de schema HORA:** o catálogo (`get_catalog_text`, `text_to_sql.py:333`) e o `mcp__schema` não tornam óbvio que "lojas HORA" → tabelas `hora_*` (e que `pedido_compras` é Nacom). Avaliar: (a) nota no catálogo desambiguando domínios HORA vs Nacom; (b) `query_hints`/descrição que apontem o conjunto `hora_*` para perguntas de motos/lojas. Conecta com o Fix B (expor schema/hints ao agente).

<a id="p5"></a>
## P5 — Detector de frustração falhou 📋

**Evidência:** `agent_step` id 203 (turno aberto pela mensagem *"Não gerou o excel, arquivo está vazio"*) tem `outcome_signal = {"frustration_score": 0}` — **falso negativo** numa reclamação explícita de falha. No agregado (4 dias, 203 steps): **100 com frustration>0 (49%)** — alto, sugere descalibração nos dois sentidos (excesso no geral, miss no caso óbvio).

**Onde:** `app/agente/services/sentiment_detector.py` (flag `USE_SENTIMENT_DETECTION`). Ação: calibrar — expressões como "não gerou", "está vazio", "não funcionou", "de novo" deveriam pontuar. Considerar few-shot/lexicon PT-BR de insatisfação operacional. Validar contra os 49% para reduzir falsos positivos junto.

<a id="p6"></a>
## P6 — Summary da sessão enganoso 📋

**Evidência:** `agent_sessions.summary` da #787 foi gerado às `2026-06-03T20:11:16` com `message_count=2` (a sessão terminou com 4 mensagens). O `resumo_geral` afirma que o agente *"gerou o arquivo Excel disponibilizando o link"* (= sucesso) — mas o 1º arquivo estava **quebrado** (404). O summary **não tem** o bug do TMPDIR (capturou só o alerta do `mcp__sql`) e `tarefas_pendentes` ficou vazio. Ou seja: registra **sucesso onde houve falha**.

**Onde:** `app/agente/services/session_summarizer.py` (flag `AGENT_SESSION_SUMMARY`). Ação: re-gerar/atualizar o summary **ao fim da sessão** (ou quando `message_count` cresce após o último summary), não congelar no meio. Idealmente, refletir reclamações do usuário e o desfecho real.

<a id="p7"></a>
## P7 — Judge/verify shadow + lacuna de verifier de ENTREGA 📋

**Evidência:** judge e verify (E2/B2) RODARAM na #787 (logs do worker 23:27–23:28 UTC; lag real ~14 min, **não 3h** — `created_at` é BRT-naive). O judge **detectou a falha** (step 202: `label=failure, score=35`, "faltou validação da entrega") — mas:
- a evidência do judge é **alucinada** ("URL truncada 'defau'"): a URL no log do web está completa; o judge recebeu input truncado;
- no step 203 o judge foi **crédulo** (`success 85`); só o `verify.adversarial` refutou ("objetivo alcançado prematuro sem validação independente");
- tudo é **shadow/assíncrono** → **não previne** a entrega ruim ao usuário.

**Dois encaminhamentos:**
1. **Calibração do judge (E3/GATE-1):** já existe plano — `docs/superpowers/plans/2026-06-03-gate1-calibracao-judge-online.md` e `docs/blueprint-agente/EXECUCAO.md:517` (achado T3: "judge dá success sem validar export"). Este caso é mais um dado para calibrar.
2. **Lacuna estrutural — verifier de ENTREGA:** a auditoria dos eixos/critica confirmou que **nenhum eixo do blueprint valida a entrega física ao usuário** (arquivo gerado é baixável? não-vazio?). Os verifiers (`arithmetic`/`adversarial`/`domain`) avaliam raciocínio/plano, não o artefato entregue. Proposta de roadmap do blueprint: um verifier/guard de entrega (pós-`exportar.py`/skills de arquivo) que confirme que o arquivo existe no diretório servido e é não-vazio **antes** de declarar sucesso. (Com o Fix A isso passa a ser verdade por construção; o verifier seria a rede de segurança.)

<a id="nota-de-processo"></a>
## Nota de processo — subagentes de leitura deram veredito raso

Na avaliação, os subagentes de leitura concluíram que "os bugs estão fora do escopo do blueprint" — um veredito **lexical/raso** (grep de palavras). Os FATOS deles eram sólidos (e verificáveis), mas o JULGAMENTO precisou ser refeito: a CAUSA é I/O (fora), mas o DESFECHO ("declarar sucesso sem validar a entrega") é exatamente o propósito do blueprint (dentro). Lição: filtrar criticamente vereditos interpretativos de subagentes; usar os dados, refazer o julgamento. (É o mesmo sintoma do agente web — sinal de subagente sem nuance.)

<a id="contexto-da-sessao-787"></a>
## Contexto da sessão #787 (âncoras)

- Sessão: `agent_sessions.id=787`, `session_id=bec19798-12d9-447d-acdf-9cd73908f39c`, user_id=1 (Rafael, admin), Opus 4.8, web, 2026-06-03 20:04–20:13 BRT, custo $8.45, 4 mensagens.
- Postgres PROD: `dpg-d13m38vfte5s738t6p50-a`. Web: `srv-d13m38vfte5s738t6p60`. Worker: `srv-d2muidggjchc73d4segg`.
- Logs web confirmam: 1º arquivo `2aad2f56_...xlsx` → **404** (23:11 UTC); 2º arquivo `704de0e5_...xlsx` → **200**, 16.942 bytes (23:13 UTC).
- `USUARIOS_SQL_ADMIN = {1,55,62}` (`app/pessoal/__init__.py:23`) — Rafael é admin, mas mesmo admin passa pelo Generator hoje.
