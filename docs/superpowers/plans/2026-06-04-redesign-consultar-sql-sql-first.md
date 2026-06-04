<!-- doc:meta
tipo: how-to
camada: L3
sot_de: —
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-04
-->
# Redesign da consulta SQL do Agente — de "tradutor NL→SQL" para "executor SQL-first com guard-rail determinístico" — Design + Implementation Plan

> **Papel:** desenho e plano executável para corrigir a premissa invertida da tool `mcp__sql__consultar_sql`. Origem: avaliação da sessão #787 (2026-06-03, "Excel vazio") — o agente escreveu o SQL correto e o pipeline o descartou/degradou.
> **For agentic workers:** este doc é auto-contido. Antes de implementar, RELER os arquivos-âncora citados (a linha pode ter drifado). Usar `superpowers:test-driven-development` + `superpowers:writing-plans`/`executing-plans`. Mudança comportamental ampla → **flag OFF default + canary** (Task 6). NÃO fazer big-bang.

## Indice

- [Contexto e origem](#contexto-e-origem)
- [Diagnostico: a premissa esta invertida](#diagnostico-a-premissa-esta-invertida)
- [Componentes: dano vs valor (com fontes)](#componentes-dano-vs-valor-com-fontes)
- [O design proposto (SQL-first)](#o-design-proposto-sql-first)
- [Arquivos e linhas ancora](#arquivos-e-linhas-ancora)
- [Plano de implementacao (TDD)](#plano-de-implementacao-tdd)
- [Riscos, flag e canary](#riscos-flag-e-canary)
- [Criterios de aceite](#criterios-de-aceite)
- [Decisoes em aberto (decidir no inicio)](#decisoes-em-aberto-decidir-no-inicio)

---

## Contexto e origem

Na sessão web #787 (user_id=1 Rafael, Opus 4.8) o pedido foi "relatório Excel das motos HORA em estoque com pedido e NF de compra". O agente:
1. Investigou os schemas, **escreveu o SQL correto** (com a coluna real `timestamp` de evento).
2. Chamou `mcp__sql__consultar_sql` — e a tool **reescreveu/truncou/alucinou** a query: trocou `timestamp` por `ocorrido_em`, adicionou `ROUND`, cortou a CTE.
3. Sem caminho confiável, o agente **improvisou** um script Python com SQL bruto via Bash contra a `DATABASE_URL` de produção — e foi esse Bash que herdou o `TMPDIR` errado, causando o "arquivo vazio" (corrigido à parte — ver commit `fix(agente): alinha diretorio de arquivos via AGENTE_FILES_ROOT`).

A causa do passo 2 não é um bug pontual: é a **arquitetura da tool**. Este doc a reavalia.

## Diagnostico: a premissa esta invertida

A tool `consultar_sql` foi desenhada como **text-to-SQL**: assume que **quem chama não sabe SQL** e precisa de um tradutor (um LLM Haiku, o "Generator", que gera SQL do zero a partir de linguagem natural).

Mas o **único chamador real é o Agente principal (Opus)**, que:
- é um modelo **muito mais forte** que o Haiku do Generator;
- tem a tool `mcp__schema__consultar_schema` para **descobrir os campos reais** antes de escrever;
- tem o **contexto inteiro da conversa** (o Generator vê só a "pergunta" isolada + um catálogo leve);
- **já sabe escrever SQL** (na #787 escreveu o SQL certo, que foi descartado).

Logo o Generator não ajuda: ele **substitui a interpretação de um modelo superior pela de um inferior**. É uma camada de _downgrade_ obrigatória. A pergunta do dono do produto resume: *"eu sempre vou enviar a um agente; o agente que eu pedir vai saber mais que o Generator"* — sim, **sempre**.

> Importante separar dois papéis que hoje são confundidos sob "o Haiku":
> - **Generator** = papel CRIADOR (adivinha SQL + campos). É a FONTE da alucinação — **por design**.
> - **Deterministic Validator + schemas** = papel VALIDADOR (confere campos contra o schema real). É o que **de fato** ajuda a não errar nome — e está soterrado **depois** do criador.

## Componentes: dano vs valor (com fontes)

| Componente | O que vê | Papel hoje | Veredito |
|---|---|---|---|
| **Generator** (`SQLGenerator`, Haiku, `max_tokens=500`) | catálogo **leve**: `nome \| descrição \| 3 campos-chave` por tabela | cria SQL do zero; é **instruído a adivinhar campos** | ❌ **DANO** quando o chamador é o Opus |
| **Deterministic Validator** (`SQLDeterministicValidator`, sem LLM) | **schema real** (campos + tipos) | confere campos/tipos; hoje só decide se pula o Haiku | ✅ **VALOR REAL** (zero falso positivo) |
| **Evaluator** (Haiku) | schema detalhado | corrige o SQL do Generator | ⚠️ existe para consertar o adivinhador; redundante se o Generator sair |
| **schemas JSON + `query_hints` + regras de negócio** | a verdade dos campos/regras | hoje as regras estão **escondidas** no prompt do Generator (regras 9-13) | ✅ **VALOR** — deve ser exposto ao agente |

Evidências (reler — linhas podem ter drifado):
- Description da tool diz "linguagem natural": `app/agente/tools/text_to_sql_tool.py:396-413`.
- Admin por user_id (NÃO por flag): `text_to_sql_tool.py:460` → `USUARIOS_SQL_ADMIN`; set em `app/pessoal/__init__.py:23` = `{1, 55, 62}` (Rafael=1). Branch admin: `text_to_sql_tool.py:463-466`. Propaga `admin_mode`: `:495-502`.
- **Mesmo em admin, o SELECT passa pelo Generator** (não há execução literal): `text_to_sql.py:1768-1795` (o `else` SEMPRE chama `self.generator.generate(...)`); único skip é template semântico ≥0.92 (`:1738-1756`).
- Generator: `text_to_sql.py:618-691`. Docstring admite "**campos podem ser aproximados**" (`:621-622`). Regra 4 manda **adivinhar** campos por descrição (`:655`). Regra 8 força `ROUND(...::numeric,2)` (`:659`). `max_tokens=500` (`:675`) → trunca CTE.
- Catálogo do Generator = `nome | descrição | 3 key_fields` (`get_catalog_text`, `text_to_sql.py:333-388`, linha do format `:357`). Por isso usou `ocorrido_em` (era um dos key_fields da tabela de evento que ele escolheu).
- **Deterministic Validator**: `text_to_sql.py:738-842`. Valida campos qualificados (Check 1, `:811`), tipos (Check 2, `:815`), campos não-qualificados em tabela única (Check 3, `:822`). Retorna `issues` com motivo exato. Docstring (`:741`): *"Haiku evaluator é não-determinístico — alucina falsos positivos"*. **HOJE só usa o resultado para decidir `skip_haiku`** (`:835`) — não devolve feedback ao chamador.
- Schema detalhado + `query_hints`: `get_tables_schema_text`, `text_to_sql.py:415-515` (query_hints em `:463-468`).
- `exportar.py` da skill `exportando-arquivos` **só lê stdin** (`:296`), não consulta banco → não há caminho de 1ª classe "SQL → Excel".

## O design proposto (SQL-first)

Reposicionar `consultar_sql` de **tradutor** para **executor com guard-rail determinístico + feedback de schema**.

```
HOJE:
  Opus → [pergunta NL] → Generator Haiku (adivinha) → Validator → Evaluator → Executor
                              ↑ degrada o Opus, esconde o schema do chamador

PROPOSTA:
  Opus → [SQL próprio] → Deterministic Validator (schema real)
                              ├─ OK ............... → Safety → Executor → resultado
                              └─ campo/tabela inexistente → retorna {erro + SCHEMA REAL
                                   (campos disponíveis + query_hints)} → Opus corrige e re-chama
  (entrada que NÃO é SQL) → Generator Haiku [fallback opcional] → mesmo Validator → Executor
```

Princípios:
1. **SQL do agente é cidadão de 1ª classe.** Se a `pergunta` já é SQL (começa com `SELECT`/`WITH` após strip, e passa numa heurística de "é SQL completo"), **pular o Generator** e executar o SQL **literal** (sem reescrita, sem `ROUND` forçado, sem truncamento de 500 tokens). CTE complexa funciona.
2. **O Deterministic Validator vira o guard-rail de entrada** (a peça que tem o schema real). Em vez de só decidir `skip_haiku`, ele passa a **devolver feedback** quando acha `issues`: "campo `X` não existe em `tabela`; campos disponíveis: [...]; query_hints: [...]". O Opus (capaz) corrige na próxima chamada — a validação de nomes é feita pela peça certa, e o feedback chega a quem decide.
3. **As regras de negócio saem do esconderijo.** O que está embutido no prompt do Generator (regras 9-13: "pedidos pendentes = `qtd_saldo_produto_pedido>0 AND ativo=True`", etc.) já existe estruturado como `query_hints` no schema. Expor isso ao agente (no retorno do schema e/ou no erro do validator) **preserva e melhora** o único valor que o Generator agregava.
4. **Generator NL→SQL vira fallback opcional** — só roda quando a entrada NÃO é SQL (humano digitando NL, ou agente escolhendo descrever). Retrocompatível.
5. **Segurança inalterada**: safety regex (anti-DROP/ALTER/etc.), read-only para não-admin (`SET TRANSACTION READ ONLY`), admin pode DML. NÃO afrouxar.

Por que adiciona valor (não é só remover): aproveita o modelo forte (consumidor real); **promove o verifier determinístico** — coerente com a filosofia do blueprint (guard-rails determinísticos dominam: G021/G031 etc.); resolve a #787 na raiz; reduz custo/latência (menos chamadas Haiku); torna a validação de nomes **visível** ao agente.

## Arquivos e linhas ancora

| Arquivo | Papel | Pontos a tocar |
|---|---|---|
| `.claude/skills/consultando-sql/scripts/text_to_sql.py` | pipeline `TextToSQLPipeline.run()` | inserir branch SQL-first (~`:1714` antes da ETAPA 0); fazer o Validator retornar feedback (`:758-842`); fallback Generator (`:1768-1795`) |
| `app/agente/tools/text_to_sql_tool.py` | tool MCP `consultar_sql` | description (`:386-413`) — instruir "mande SQL quando souber; receberá schema real se errar campo"; propagar flag |
| `app/agente/config/feature_flags.py` | flags | nova flag `SQL_AGENT_SQL_FIRST` (default OFF) |
| `app/agente/prompts/system_prompt.md` | comportamento do agente | orientar: para consultas complexas, escrever SQL e usar `mcp__schema` antes (não depender do NL→SQL) |
| `.claude/skills/consultando-sql/` | docs da skill | refletir o novo contrato |
| (opcional) `.claude/skills/exportando-arquivos/` | export | avaliar um caminho "SQL→Excel" de 1ª classe (ver Decisões em aberto) |

## Plano de implementacao (TDD)

> Cada task: teste primeiro (vermelho), implementação (verde), flag OFF, sem baixar o baseline de pytest. Reler os arquivos-âncora antes (linhas podem ter drifado).

- [ ] **Task 1 — Detector "é SQL bruto".** Função pura `looks_like_raw_sql(texto) -> bool` (começa com `SELECT`/`WITH` após strip/comentários; não é frase NL). Testes: SELECT simples, CTE com `WITH`, NL ("top 10 clientes"), SQL com comentário no topo, string ambígua. Conservador: na dúvida, NÃO tratar como SQL (cai no fallback NL).
- [ ] **Task 2 — Branch SQL-first em `run()` atrás de flag.** Se `SQL_AGENT_SQL_FIRST` e `looks_like_raw_sql(pergunta)`: `sql = pergunta` (literal), **pular Generator E Evaluator**, ir para Validator→Safety→Executor. Flag OFF preserva 100% o fluxo atual. Testes: com flag ON, SQL literal não é reescrito (mock do Generator NÃO é chamado); com flag OFF, comportamento idêntico ao atual.
- [ ] **Task 3 — Validator com feedback de schema.** `SQLDeterministicValidator.validate` (ou um wrapper no `run`) passa a, quando há `issues`, montar uma mensagem estruturada com os campos REAIS das tabelas usadas (de `get_tables_schema_text`/schema JSON) + `query_hints`. O `run()` retorna esse feedback como `aviso`/`erro` estruturado (não executa SQL com campo inexistente). Testes: SQL com campo inexistente → retorno traz "campos disponíveis"; SQL válido → executa.
- [ ] **Task 4 — Description + system_prompt.** Atualizar a description da tool (`text_to_sql_tool.py:386-413`) e o `system_prompt.md`: "para consultas complexas (CTE, joins), descubra os campos com `mcp__schema` e **escreva o SQL**; a tool executa literal e devolve o schema real se um campo não existir". Teste: smoke de que a description não excede o budget de truncamento (ver `app/agente/SDK_CHANGELOG.md` Solução B, 16K chars do meta-tool Skill — aqui é a tool, mas validar tamanho).
- [ ] **Task 5 — Expor query_hints/regras ao agente.** Garantir que `mcp__schema__consultar_schema` (ou o retorno do validator) inclua `query_hints` e regras de negócio. Migrar as regras 9-13 do prompt do Generator para os schemas/query_hints onde ainda não estiverem. Testes: schema de `carteira_principal`/`separacao`/`faturamento_produto` expõe as regras como hints.
- [ ] **Task 6 — Canary + observabilidade.** Flag `SQL_AGENT_SQL_FIRST` OFF default. Ligar primeiro em **shadow/log** (registrar quando a entrada é SQL e o Validator achou issue, sem mudar comportamento), medir taxa de issues por uma janela; depois ligar para admins (1/55/62), depois geral. Logar `[SQL_FIRST]` no Render. Sem silenciar truncamento (logar quando cair no fallback NL).
- [ ] **Task 7 — Reproduzir a #787.** Teste/canary: o pedido "relatório motos HORA em estoque + pedido + NF" deve resolver com SQL-first (CTE literal), sem improviso Bash. Validar contra o banco PROD (read-only) que a CTE roda como escrita.

## Riscos, flag e canary

- **Mudança comportamental ampla** (afeta TODA consulta SQL do agente) → flag OFF default; canary shadow→admin→geral. NUNCA big-bang.
- **Regras de negócio "por sorte" do Generator**: o Generator às vezes acertava via regras embutidas (9-13). Mitigação: Task 5 expõe essas regras como `query_hints` ao agente — valor preservado e melhorado.
- **Heurística de detecção de SQL** (Task 1): falso positivo (tratar NL como SQL) quebraria; ser conservador (na dúvida, NL/fallback). Falso negativo apenas mantém o status quo (passa pelo Generator) — degradação aceitável transitória.
- **Segurança**: NÃO afrouxar o safety. SQL literal de não-admin continua read-only; admin mantém DML com os bloqueios atuais (DROP/ALTER/etc.).
- **Retrocompat**: o Generator NL→SQL permanece como fallback — nenhum caminho existente é removido nesta fase.

## Criterios de aceite

1. Com flag ON, uma CTE complexa escrita pelo agente roda **literal** (Generator NÃO é chamado; `timestamp` não vira `ocorrido_em`; sem `ROUND` forçado; sem truncamento).
2. Um SQL com campo inexistente retorna **feedback com os campos reais disponíveis** (+ query_hints), e o agente corrige numa segunda chamada.
3. Flag OFF → comportamento 100% idêntico ao atual (zero regressão; baseline pytest mantido).
4. A #787 é reproduzível: o pedido resolve sem improviso Bash.
5. Segurança intacta (testes de DROP/ALTER bloqueados; read-only para não-admin).

## Decisoes em aberto (decidir no inicio)

1. **Caminho "SQL → Excel" de 1ª classe?** Hoje `exportar.py` só lê stdin (`:296`). Opções: (a) deixar o agente compor `consultar_sql` (SQL-first) → `exportar.py` via stdin (suficiente após este redesign); (b) um modo `consultar_sql --export=excel` que já materializa o arquivo. Recomendado começar por (a); avaliar (b) se a composição via stdin ainda for atrito.
2. **Aposentar o Evaluator (Haiku)?** Sem o Generator, o Evaluator perde o propósito principal (corrigir o adivinhador). Decidir se vira "corretor opcional do SQL do agente" (questionável — o Opus já é melhor) ou se é removido após o canary. Recomendado: manter inerte atrás da flag e remover na limpeza pós-canary.
3. **Escopo da flag**: por-usuário (admin primeiro) vs global shadow. Recomendado shadow→admin→geral.

---

## Implementacao entregue (2026-06-04) + decisoes resolvidas

Branch `feat/agente-sql-first` (worktree), TDD, flag OFF default. Decisoes em aberto resolvidas no inicio: **#1 = (a)** compor `consultar_sql` SQL-first -> `exportar.py` via stdin (NAO tocar `exportar.py` agora); **#2 = manter Evaluator inerte** atras da flag (no SQL-first pula Generator E Evaluator), remover na limpeza pos-canary; **#3 = flag unica multivalor** `SQL_AGENT_SQL_FIRST in {off,shadow,admin,on}`.

| Task | Entrega |
|---|---|
| 1 | `looks_like_raw_sql` + `normalize_sql_candidate` (puras; guard anti-NL nao-ASCII E artigo ingles `the`/`an` fora de literal — F1; probe remove tambem identificadores `"..."`) |
| 2+3 | branch SQL-first em `run(sql_first_mode)`: executa literal; guard-rail deterministico bloqueia so' `campo_inexistente` e devolve o schema REAL (campos + query_hints) |
| 4 | `CONSULTAR_SQL_DESCRIPTION` (factual "quando habilitado") + `system_prompt.md` (nudge canary-safe) |
| 5 | **COMPLETA** — regras 9-13 nos `business_rules` das tabelas (`schema.json`), expostas ao agente pelo feedback SQL-first (`get_tables_schema_text` → `_build_schema_feedback`). A 13 (contas_a_receber) foi adicionada; 9-12 (carteira_principal/separacao/movimentacao_estoque/faturamento_produto) JA' existiam — verificado, ver nota de hardening. Travadas por `TestSchemaBusinessRulesExposed` (5 tabelas × 2 superficies). |
| 6 | `resolve_sql_first_mode(is_admin)` em `feature_flags.py` + wiring na tool |
| 7 | repro #787 deterministica (CTE complexa sobrevive literal, sem ROUND/reescrita) |

Cobertura: `tests/agente/test_text_to_sql_sql_first.py` (**79 testes** deterministicos, sem DB/LLM via Generator/Executor monkeypatched). Flag OFF = baseline pytest preservado.

### Hardening pos-auditoria adversarial (2026-06-04, pre-merge)

Auditoria adversarial multi-dimensional (52 subagentes, 6 dimensoes) — **0 bloqueantes; safety = OK** (SQLSafetyValidator + `SET TRANSACTION READ ONLY` para nao-admin preservados no caminho SQL-first; atalho pula SO Generator+Evaluator). Fechado antes de ligar a flag global:
- **F1 (detector):** guard anti-prosa-inglesa (`the`/`an` como palavra isolada fora de literal → NL) — fecha o falso positivo "Select the best option from the menu" (code-switch do Opus, P4). + `_sql_structural_probe` remove identificadores `"..."` → corrige falso negativo de identificador acentuado (`"Numero_produto"`). 8 testes.
- **F2 (testes de seguranca):** `TestSqlFirstSecurity` exercita o BLOQUEIO real de DML de nao-admin no atalho (DELETE/UPDATE barrados na ETAPA 3; SELECT nao-admin = read-only; DROP/ALTER/TRUNCATE nem sao detectados como raw_sql) — rede de regressao que faltava (os 56 originais monkeypatcham o executor). 7 testes, discriminantes (admin permite vs nao-admin bloqueia).
- **F3 + Task 5 reavaliada = COMPLETA:** o finding "regras 9-12 so' no Generator" foi **refutado por verificacao** — 9-12 ja' estavam em `business_rules` (carteira_principal/separacao/movimentacao_estoque/faturamento_produto) e expostas no feedback SQL-first; so' faltava a 13 (adicionada). Veredito raso do subagente (mesmo sintoma da "Nota de processo" do roadmap). Travado por `TestSchemaBusinessRulesExposed`. Cobertura 56→79.

## Runbook de canary (PROD, via env `SQL_AGENT_SQL_FIRST`)

> Avanco controlado por env var (lido FRESH a cada request em `resolve_sql_first_mode` — nao precisa rebuild). Reverter = voltar o valor.

1. **OFF (merge inicial)**: `SQL_AGENT_SQL_FIRST` ausente/`off`. Zero mudanca de comportamento (so' a description/system_prompt mudam, factuais).
2. **shadow** (`=shadow`): TODOS observam. Buscar nos logs Render `[SQL_FIRST] shadow:` — mede taxa de `raw_sql` detectado e `would_block`. Sem mudanca de comportamento. Janela 24-48h.
3. **admin** (`=admin`): admins (`USUARIOS_SQL_ADMIN`={1,55,62}) recebem SQL-first REAL; demais ficam em shadow. Validar com Rafael (user 1) o cenario #787 real (relatorio motos HORA): a CTE deve rodar literal, sem improviso Bash. Conferir `[SQL_FIRST] Executando SQL literal`.
4. **on** (`=on`): geral. Monitorar `[SQL_FIRST] BLOQUEADO por campo inexistente` (taxa de feedback de schema) e erros do executor.

**O que observar**: `would_block` alto em shadow = schema JSON possivelmente desatualizado (regenerar) OU agente errando campos (o feedback resolve). Fallback NL nao e' silenciado (a entrada que NAO e SQL cai no Generator normalmente).

**Validacao manual #787 (read-only PROD)**: com `admin`/`on`, pedir ao agente o relatorio de motos HORA em estoque + pedido + NF de compra; confirmar que resolve via `consultar_sql` (SQL-first, CTE literal) e NAO via `Bash python -c`.

## Backlog pos-canary
- Remover o Evaluator (Decisao #2) apos `on` estabilizado.
- Reavaliar Decisao #1 (b) (`consultar_sql --export=excel`) se compor via stdin ainda for atrito.
- P4-P7 do roadmap (idioma/descoberta-schema, detector de frustracao, summary enganoso, verifier de entrega) — ver `2026-06-04-roadmap-correcoes-agente-787.md`.

### Achados da auditoria adversarial (nao-bloqueantes — backlog)
- **(OPCIONAL) Des-duplicar regras do Generator:** as regras 9-13 vivem em DOIS lugares — no prompt do `SQLGenerator` (linhas ~778-782) E nos `business_rules` do `schema.json`. Nao e' lixo: o Generator usa o catalogo LEVE (nome+descricao+key_fields), NAO le `business_rules`, entao precisa das regras no proprio prompt. So' vale consolidar se/quando o Generator passar a ler `business_rules` (ou for aposentado pos-canary). Ate la', manter as duas fontes em sincronia ao editar qualquer regra.
- **Confusao diagnostica (MEDIUM):** quando um falso positivo residual do detector escapa, o validador deterministico pode reportar `campo_inexistente` em vez de o Postgres dar `syntax error`, confundindo o agente. Mitigado na origem por F1 (guard de artigo); melhoria opcional: se Postgres devolver `syntax error` numa entrada detectada como raw, logar como falso-positivo e cair no Generator automaticamente.
- **Multi-statement regex (MEDIUM, PRE-EXISTENTE ao SQL-first):** `SQLSafetyValidator` detecta `;` via regex que tem falsos positivos com escape `\'` e comentarios com `;` — bloqueia queries validas com apostrofo. Componente de seguranca compartilhado; tocar com cuidado (nao e' regressao do SQL-first, mas o atalho aumenta a exposicao a SQL literal complexo).
- **Guard-rail contornavel via `TEXT_TO_SQL_DETERMINISTIC_VALIDATOR=false` (MEDIUM):** se essa env var desabilitar o validador deterministico, o bloqueio de `campo_inexistente` do SQL-first e' pulado (NAO afeta o safety — DML de nao-admin continua barrado). Documentar a dependencia; nao setar `false` em PROD.
- **Testes extras (LOW):** flag OFF rodando o pipeline COMPLETO (Generator→Evaluator→Safety→Executor); shadow observando `would_block` sem bloquear; `SET TRANSACTION READ ONLY` em execucao real (integracao, nao monkeypatched).
