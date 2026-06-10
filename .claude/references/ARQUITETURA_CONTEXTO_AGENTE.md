<!-- doc:meta
tipo: reference
camada: L2
sot_de: arquitetura de contexto do Agente Web (PAD-CTX)
hub: .claude/references/INDEX.md
superseded_by: —
atualizado: 2026-06-10
-->
# Arquitetura de Contexto do Agente Web (PAD-CTX)

> **Papel:** dono vigente do padrao de arquitetura de contexto do Agente Web — define O QUE pertence A CADA CAMADA do contexto de boot (preset, system_prompt, empresa_briefing, CLAUDE.md, skills, hook dinamico, references, memorias), os criterios de admissao, os caminhos de descoberta e as regras de redundancia. **Abra quando:** for adicionar/mover/remover conteudo de qualquer camada do contexto do agente, decidir "onde documento isso para o agente?", ou revisar a injecao de memorias/hook.

## Indice

- [Problema resolvido](#problema-resolvido)
- [Superficies do agente](#superficies-do-agente)
- [As camadas do contexto de boot](#as-camadas-do-contexto-de-boot)
- [Criterios de admissao (perguntas diagnosticas)](#criterios-de-admissao-perguntas-diagnosticas)
- [Papel detalhado por arquivo do prompt estatico](#papel-detalhado-por-arquivo-do-prompt-estatico)
- [CLAUDE.md raiz — o que fica para o agente web](#claudemd-raiz--o-que-fica-para-o-agente-web)
- [Skills — template de description e curadoria](#skills--template-de-description-e-curadoria)
- [Hook dinamico — layout, orcamento e ordem](#hook-dinamico--layout-orcamento-e-ordem)
- [Memorias — tipos, proveniencia, promocao](#memorias--tipos-proveniencia-promocao)
- [Caminhos de descoberta](#caminhos-de-descoberta)
- [Regra de redundancia e presenca obrigatoria](#regra-de-redundancia-e-presenca-obrigatoria)
- [Intocaveis e licoes aprendidas](#intocaveis-e-licoes-aprendidas)
- [Governanca e enforcement](#governanca-e-enforcement)
- [Fontes](#fontes)

## Problema resolvido

Sem um padrao, cada sessao de dev decide ad-hoc onde colocar informacao — o mesmo assunto
acaba fragmentado na linha 200, 600 e 1200 de documentos diferentes, com memorias
referenciando a mesma coisa (diagnostico RP-1, estudo 2026-06-09). O contexto cresceu por
acrecao (system_prompt: 136→862 linhas em 6 meses, 100 commits) e o gargalo migrou de
"falta regra" para "excesso de sinal competindo por atencao". Este padrao impoe criterio
de admissao POR CAMADA, fonte canonica unica por assunto e orcamento por bloco dinamico —
complementa o PAD-A (`ARQUITETURA_DE_ARTEFATOS.md`, que governa docs/scripts) governando
o CONTEUDO DO CONTEXTO DO AGENTE.

## Superficies do agente

Este padrao governa o agente PRINCIPAL. Mudancas em hook/whitelist/memorias tem alcance
diferente por superficie — declarar a superficie afetada em toda mudanca:

| Superficie | Client/hook | Whitelist de skills | Afetada por mudancas deste padrao |
|------------|-------------|---------------------|-----------------------------------|
| Agente Web (`/agente/*`) | `app/agente/sdk/` | deny-list `app/agente/config/skills_whitelist.py` | SIM |
| Teams bot (`app/teams/`) | MESMO client/hook do web | MESMA deny-list | SIM (sempre junto com web) |
| Agente Lojas HORA (`/agente-lojas/*`) | proprio (`app/agente_lojas/`) | ALLOW-list propria | NAO (isolado) |
| Subagentes (`.claude/agents/*.md`) | system prompt PROPRIO, SEM hook de memoria do turno | skills declaradas no proprio .md | NAO (contexto proprio) |

Consequencia: melhorias de orcamento do hook e proveniencia de memorias sao invisiveis
aos subagentes; skills removidas do listing do principal continuam disponiveis aos
subagentes que as declaram.

## As camadas do contexto de boot

O contexto do Agente Web e montado em 2 estagios: estatico (1x no connect, via
`_build_full_system_prompt()` em `app/agente/sdk/client.py` + `setting_sources=["project"]`)
e dinamico (todo turno, via hook `UserPromptSubmit` em `app/agente/sdk/hooks.py`).

| # | Camada | Arquivo/Fonte | Criterio dominante | Muda | Cacheavel |
|---|--------|---------------|--------------------|------|-----------|
| 0 | Tools | MCP + builtins | capacidade que o agente PODE precisar nesta superficie | mensal | sim |
| 1a | Preset | `app/agente/prompts/preset_operacional.md` | mecanica de operacao do harness (tool use, ambiente, anti-injection) | raro | sim |
| 1b | System prompt | `app/agente/prompts/system_prompt.md` | politica comportamental invariante do dominio (COMO agir) | semanal/raro | sim |
| 1c | Briefing | `app/agente/config/empresa_briefing.md` | conhecimento estavel da empresa (quem somos, vocabulario) | raro | sim |
| 2 | CLAUDE.md raiz | `CLAUDE.md` (via `setting_sources`) | mapa do territorio compartilhado (ponteiros, nao conteudo) | semanal | medio |
| 3 | Skills listing | `.claude/skills/*/SKILL.md` (YAML description) | gatilho de roteamento enxuto (≤500 chars) | mensal | sim |
| 3b | Skills body | `.claude/skills/*/SKILL.md` (corpo) | procedimento + gotchas da operacao + few-shot; carrega quando a Skill tool e invocada (nao por Read) | versionado | sob demanda |
| 4 | Hook dinamico | `app/agente/sdk/hooks.py` + `memory_injection.py` | estado autenticado da sessao/turno, com orcamento por bloco | por turno | nao |
| 5 | References | `.claude/references/**` | conhecimento profundo JIT (<20% das sessoes precisam; acesso via Read/Grep) | raro | n/a (JIT) |

**Regra mnemonica** (use ao decidir onde colocar algo):
- **Preset** = "como eu opero a maquina"
- **System prompt** = "como eu ajo" (politica do dominio)
- **Briefing** = "quem e a empresa"
- **CLAUDE.md** = "o que existe e onde esta" (mapa)
- **Skill** = "como eu faco X especificamente" (procedimento)
- **Hook** = "quem sou nesta sessao e o que ficou pendente" (estado)
- **Reference** = "o que consulto quando precisar aprofundar" (biblioteca)

**Regra de altitude**: conteudo de altitude baixa em camada alta = ruido; conteudo de
altitude alta em camada baixa = redundancia. Exemplo de violacao corrigida: a descricao
de 1.139 chars do `gestor-estoque-odoo` (status de skills, G021/G022, versoes) no
CLAUDE.md — procedimento de baixa altitude em camada de mapa; o detalhe vive em
`app/odoo/estoque/CLAUDE.md`.

## Criterios de admissao (perguntas diagnosticas)

Antes de adicionar conteudo a uma camada, responda as perguntas dela. Qualquer "NAO" =
o conteudo pertence a outra camada.

**System prompt (1a/1b/1c):**
1. Seria IDENTICO em 95%+ das sessoes do agente web?
2. E regra de COMPORTAMENTO (como agir), nao de CONHECIMENTO (o que saber)?
3. Sem isto aqui, o agente tomaria decisao errada MESMO com todas as tools/skills?
4. Que falha especifica e medida isto resolve? (sem falha documentada = nao entra)

**CLAUDE.md raiz:**
1. E relevante para o agente WEB? (conteudo dev-only mora em `~/.claude/CLAUDE.md`)
2. E um mapa/indice (ponteiro), nao o conteudo em si?
3. Toda secao nova declara a audiencia no proprio texto quando nao for obvia.

**Skill (listing/description):**
1. O agente desta superficie realmente usa (historico de 90 dias confirma ou skill nova
   com demanda concreta)?
2. A description segue o template enxuto (abaixo)?
3. E suficientemente distinta das demais (<50% overlap)? Sobreposicao alta = unificar.

**Skill (body):** conhecimento procedimental passo-a-passo, gotchas DA operacao e
few-shots (1 par bom/ruim para tarefas de alta frequencia — decisao R17/PM-2.2: few-shot
em skill, NUNCA no system_prompt).

**Hook dinamico:**
1. MUDA por sessao/turno?
2. E essencial para ESTE turno (nao generico)?
3. E `mandatory`/`critical` com efeito demonstrado? Bloco `advisory` so entra com
   evidencia de efeito (ablacao/eval) — sem evidencia, nao nasce.
4. Cabe no orcamento do bloco (tabela abaixo)?

**Reference (JIT):** necessario em <20% das sessoes + acessivel via Read/Grep + alcancavel
por um caminho de descoberta declarado (abaixo).

## Papel detalhado por arquivo do prompt estatico

**`preset_operacional.md`** — DEVE ter: ambiente/timezone, tool prioritization,
parallel execution, write/edit sandbox, security invariants anti-injection, ponteiros
para os sistemas persistentes (memoria/sessoes). NAO DEVE ter: regras de negocio,
identidade do agente, conhecimento de dominio.

**`system_prompt.md`** — DEVE ter: identidade/escopo, `constitutional_hierarchy` L1-L4,
regras R* como POLITICA (com `<why>`), fronteiras de routing CRITICAS (PRE/POS
faturamento, dominio Nacom/CarVia/HORA), `routing_confidence`, lista de subagentes com
`delegate_when` de 1-2 linhas, `business_context` minimo (P1-P7 resumo + ponteiro),
`critical_ids`/`critical_fields` (presenca obrigatoria — ver regra de redundancia),
`knowledge_base` (ponteiro para o INDICE). NAO DEVE ter: procedimento passo-a-passo
(→ skill), exemplos extensos de roteamento por skill (→ description da skill), gotchas
detalhados com pos-mortem (→ reference, deixar 1 linha + ponteiro), status/versao de
skills de subagente (→ CLAUDE.md do modulo), few-shot (→ skill body).

**`empresa_briefing.md`** — DEVE ter: quem e a empresa, cadeia de valor, sistemas,
dominios, gargalos, vocabulario. NAO DEVE ter: regras de comportamento, dados volateis
duplicados (percentuais de faturamento atualizam-se aqui e SO aqui — dono unico declarado).

## CLAUDE.md raiz — o que fica para o agente web

Vereditos secao a secao (estudo 2026-06-09, finding B2):
- TECH STACK: fica COMPRIMIDO (infra/Render/backend sim; detalhe frontend/build/mobile = dev-only → `~/.claude/CLAUDE.md`).
- DADOS: REESCRITO por superficie — para o agente web a fonte de dados de negocio e
  `mcp__sql__consultar_sql` + skills; `mcp__render__*` (wrapper proprio) cobre logs/erros/status.
  A instrucao "use exclusivamente o MCP do Render" + INFRAESTRUTURA.md e contexto DEV
  (a tool `query_render_postgres` NAO existe no agente web — instrucao incorreta induz erro).
- REGRAS UNIVERSAIS: ficam timezone e fonte-de-dados (reescrita); sai `source .venv` (dev).
- FORMATACAO NUMERICA (filtros Jinja2): dev-only → `~/.claude/CLAUDE.md`.
- MODELOS CRITICOS: fica (gotchas qtd_saldo = intocavel M4); sai a linha PAD-A
  "antes de criar/editar doc" (dev-only).
- INDICE DE REFERENCIAS: fica (load-bearing) + ponteiro PROEMINENTE no topo:
  "lista completa: `.claude/references/INDEX.md`". Subsecao Design System → 1 linha dev-only.
- CAMINHOS DO SISTEMA: fica; aviso "NAO ESTENDER main_routes" marcado dev-only.
- SUBAGENTES: fica como MAPA (tabela 1 linha por agente); descricoes longas comprimem
  (detalhe → CLAUDE.md do modulo). Fonte canonica = `.claude/agents/*.md` (e o que o SDK
  carrega); system_prompt e CLAUDE.md sao projecoes verificadas por lint de consistencia.

Trade-off declarado: `~/.claude/CLAUDE.md` e local do dev (fora do versionamento). Para o
cenario single-dev vigente isso segue a convencao ja estabelecida do projeto; se o time
crescer, promover o conteudo dev-only a um doc versionado proprio e apontar o
`~/.claude/CLAUDE.md` para ele.

## Skills — template de description e curadoria

Template do frontmatter (alvo ≤450 chars por skill; orcamento real do CLI = 8.000 chars
para o listing inteiro — estourar = truncamento silencioso exatamente das clausulas
finais). FORMULA DO CLI (extraida do binario 2.1.170, 2026-06-09 — o audit antigo somava
so descriptions e dava falso-OK): entrada por skill = `- {name}: {description}` →
`len(name)+4+len(desc)`, total += N-1 newlines; budget = contexto(200K) × 4 bytes/token
× fraction(0.01); escapes conscientes: env `SLASH_COMMAND_TOOL_CHAR_BUDGET` (absoluto)
ou setting `skillListingBudgetFraction` — o padrao e CABER no default, nao subir o teto:

```text
[1 frase de proposito ≤150c] + [3-5 gatilhos positivos ≤200c] +
[max 3 anti-gatilhos criticos com a skill correta ≤100c]
```

NAO repetir o ponteiro "Routing completo: ROUTING_SKILLS.md" em cada description —
o dono desse ponteiro e o system_prompt (`routing_strategy`) + CLAUDE.md INDICE;
repetir N vezes custou ~1,1K chars do orcamento na 1a aplicacao do template
(refinamento F2.4, 2026-06-09 — a propria regra de redundancia deste padrao).

Curadoria por superficie (deny-list em `app/agente/config/skills_whitelist.py`; todo
grupo novo DEVE entrar na uniao `SKILLS_DELEGADAS_SUBAGENTE` — fora da uniao nao exclui
nada; seguir a convencao de nomes existente `SKILLS_<ESCOPO>_<QUALIFICADOR>`):
- Skills dev-only (`consultando-sentry`, `diagnosticando-banco`, `padronizando-docs`):
  saem do listing web — uso em 90 dias: 0 a 2 invocacoes, todas admin.
- `gerindo-agente`: DECIDIDO 2026-06-09 (Rafael) — sai do listing (admin mantem a tela
  `/agente/memorias` e o Claude Code dev). Alternativa registrada no plano, SE surgir
  demanda via chat: gate por perfil em `can_use_tool` (`app/agente/config/permissions.py`
  — viavel via ContextVar de user_id), liberando `Skill:gerindo-agente` so para
  administrador.
- Skills user-scope (`~/.claude/skills/`: prd-generator, ralph-wiggum, skill-creator,
  resolvendo-problemas...): NAO requerem deny-list — com `setting_sources=["project"]`
  nunca carregam em producao.
- Dominios isolados: skill de dominio (HORA/Assai/Odoo-WRITE/SPED) entra no grupo do
  dominio, nunca no listing do principal.
- Invariante de nao-orfandade: toda skill em `SKILLS_DELEGADAS_SUBAGENTE` deve estar
  declarada em ao menos um `.claude/agents/*.md` (violacao conhecida: `faturando-odoo`).
- Sobreposicao: skills com >50% de overlap de gatilho unificam-se com roteamento interno
  por formato/extensao (caso `lendo-arquivos` + `lendo-documentos`). O SDK NAO tem alias
  de skill — transicao = comunicar usuarios + nota no SKILL.md unificado.

## Hook dinamico — layout, orcamento e ordem

Orcamento-alvo total: ≤15KB/turno (tipico ~7KB; baseline pre-padrao ~34KB). Ordem com
"aja-agora" no fim (mitiga lost-in-the-middle):

| Ordem | Bloco | Orcamento | Condicao |
|-------|-------|-----------|----------|
| 1 | resume_fallback | ~0,1KB | so 1a msg pos-falha de resume |
| 2 | session_context (data/usuario/permissoes) | ~0,1KB | sempre |
| 3 | user_rules (mandatory) | cap 12 regras (correction_count DESC — `MANDATORY_RULES_MAX_COUNT`) + **ENFORCED 350c/regra** (`USER_RULE_CHAR_CAP`, destilado preserva DO integral + ponteiro — F6 2026-06-10); meta de curadoria: ≤200c/regra; paths Tier 1 EXCLUIDOS do canal (dupla injecao) | se existir |
| 4 | user_memories: perfil (user/preferences/expertise) | **ENFORCED 1500c + 1200c + 1200c** (`TIER1_PATH_CAPS`, destilado + ponteiro — F6 2026-06-10; desvio declarado vs design 600/400/400: pre-medicao — resumo+contextualizacao reais do user.xml medem 1.0-1.9K e o cap preserva o pointer-mode curado) | sempre |
| 5 | user_memories: perfis empresa (Tier 1.5) | 400c/perfil | se existir |
| 6 | user_memories: Tier 2 RAG por INTENT DO TURNO | 4 × 300c | similaridade > threshold |
| 7 | operational_directives | constitucional + 2 por dominio | sempre |
| 8 | intersession_briefing (so partes operacionais) | ~0,4KB | se houver eventos |
| 9 | routing_context (active_traps corrigidas) | ~0,2KB | condicional |
| 10 | system_hint / correction_hint | ~0,2KB | condicional (regex) |
| 11 | debug_mode / sql_admin | 1-3 linhas cada | SO admin (ja condicional) |
| 12 | recent_sessions (5 resumos) | ~1,2KB | sempre |
| 13 | pendencias_acumuladas | 5 × 100c | ULTIMO — colado a mensagem |

**Overflow (prioridade de corte quando estourar o teto):** cortar primeiro Tier 2 RAG
(item 6), depois directives organicas (item 7, mantendo a constitucional), depois
routing_context (9). NUNCA cortar: session_context, user_rules, pendencias,
recent_sessions.

**Cap de blocos fixos (F6, 2026-06-10)**: os blocos INCORTAVEIS (itens 3-4) tem
enforcement proprio — destilar/ponteirar (como o Tier 2 com 300c), nunca cortar.
Evidencia tripla PROD (users 1/18/82): rules 6,2K + tier1 7,6-9,1K estouravam sozinhos
o teto 15K e a politica de overflow zerava TODO o adaptativo — os usuarios mais ativos
eram os que nada recebiam do retrieval. Implementacao: `TIER1_PATH_CAPS` +
`USER_RULE_CHAR_CAP` + `_distill_fixed_block`/`_distill_rule_content`
(`memory_injection.py`); kill-switch `AGENT_FIXED_BLOCKS_CAP=false`. Fix junto: paths
Tier 1 com priority=mandatory entravam 2x no payload (user_rules + Tier 1) — excluidos
do canal L1 (`_query_user_rules`).

Excluidos do boot operacional (acessiveis via skill `gerindo-agente`/tela admin):
`skill_hints`, `world_model` (removidos — decisao R-1), `stale_empresa`,
`improvement_responses`, `intelligence_report`. Excecao condicional: improvement_response
de `skill_bug` ATIVO pode voltar ao hook SOMENTE no turno que usa a skill afetada.

## Memorias — tipos, proveniencia, promocao

**Tipos** (cada um com destino proprio): regra-do-usuario (`user_rules`, mandatory) ·
perfil (Tier 1) · heuristica/armadilha empresa (Tier 2 RAG por intent) · episodica
(few-shot por topico, ex.: caso fatura 161-9 quando o turno tratar de fatura CarVia) ·
armadilha DETERMINISTICA (candidata a promocao para codigo — nao e memoria).

**Proveniencia** `[IMPLEMENTADO — F5 2026-06-09; migration
2026_06_09_agent_memories_proveniencia]`: `source_session_id` na tabela
`agent_memories`, populado no `save_memory` via `get_current_session_id()`
(ContextVar em `app/agente/config/permissions.py:78`; memorias criadas por
daemons pos-sessao recebem por parametro opcional — sem ele, NULL). Exposicao
na injecao COM protecao cross-user (`_memory_open_tag`):
- Memoria PESSOAL (escopo do proprio usuario): `<memory session="..." date="...">` —
  navegavel via `mcp__sessions__search_sessions`.
- Memoria EMPRESA (compartilhada): expor APENAS `created_by` + `date` (a sessao de origem
  pode ser de OUTRO usuario — `search_sessions` filtra por user_id e cross-user e gated
  por debug_mode; nao vazar UUID de sessao alheia). Admin em debug navega normalmente.
Objetivo: blindar contra memoria mal interpretada — o agente acessa o raw da sessao de
origem quando autorizado, e tira a propria conclusao.

**Frescor/confianca** `[IMPLEMENTADO — F5 2026-06-09]`: `last_confirmed` (create e
updates renovam; origem imutavel) + `confidence` (reservada, NULL = nao avaliada)
como metadados queryaveis; correcao nova SEMPRE prevalece sobre memoria antiga em
conflito.

**Teto por memoria injetada:** ~300 chars no Tier 2 (WHEN/DO destilado + ponteiro
`view_memories(path)` para o restante). Memoria de 27 linhas nao entra inteira no boot.

**Promocao memoria→codigo** (criterios — todos os 4): (1) comportamento deterministico,
(2) ponto unico de falha conhecido, (3) check binario implementavel, (4) reincidencia
registrada. Fluxo: `register_improvement(category=skill_bug)` → dev implementa guard →
memoria marcada como promovida (mecanismo F5.6: `is_cold=true` + `meta.promovida_para`
apontando o artefato — sai da injecao e da busca semantica, historico segue via
`search_cold_memories`; data-fix `2026_06_09_f5_memorias_datafix.py`). Exemplos ja
promovidos: TMPDIR divergente (`_constants.py` AGENTE_FILES_ROOT), verificacao de
arquivo existente (`files.py`; check de tamanho>0 JA implementado na skill
`exportando-arquivos` — `_verificar_entrega`, guard P7 #787).

## Caminhos de descoberta

Todo conhecimento JIT precisa de um caminho declarado a partir do boot, com no maximo
2 saltos e gatilho imperativo ("ANTES de X, LER Y") no primeiro elo:

- **Gotchas Odoo**: system_prompt `<knowledge_base>`/R7 → `ROUTING_SKILLS.md` (Passo 2) →
  `odoo/GOTCHAS.md`. Atalho: CLAUDE.md INDICE → GOTCHAS.md (1 salto). Mencoes inline no
  system_prompt viram ponteiro de 1 linha (nunca duplicar o conteudo — fica stale).
- **Campos de tabela**: `consultar_schema` (tool) ou
  `.claude/skills/consultando-sql/schemas/tables/{tabela}.json` — fonte que PROVA (L2).
- **Routing de skill**: description (gatilho) → `ROUTING_SKILLS.md` (arvore completa).
- **Lista completa de references**: CLAUDE.md INDICE → `.claude/references/INDEX.md`.

## Regra de redundancia e presenca obrigatoria

**1 dono por assunto; todo outro lugar e ponteiro.** Duas excecoes declaradas:

1. **Redundancia defensiva** (2 copias estaticas autorizadas): gotcha
   `qtd_saldo_produto_pedido` vs `qtd_saldo` — presente no system_prompt
   (`critical_fields`) E no CLAUDE.md raiz (dono:
   `modelos/REGRAS_CARTEIRA_SEPARACAO.md`); cada instancia marcada com comentario
   apontando o dono.
2. **Presenca obrigatoria na camada estatica** (nao e duplicata): `critical_ids`
   (company IDs Odoo FB=1/SC=3/CD=4/LF=5) no system_prompt — `odoo/IDS_FIXOS.md` e
   JIT-only, logo o bloco no prompt e a UNICA copia no boot; justificativa: erro de
   company e catastrofico e silencioso (L1).

Adicionar item a qualquer das listas exige justificativa L1 (erro silencioso +
catastrofico).

## Intocaveis e licoes aprendidas

NAO cortar/comprimir (evidencia empirica interna):
- Blocos `<why>` das regras (corte da FASE 2 foi REVERTIDO no mesmo dia — commit
  `fee8f1f17`; QUALITY_REVIEW marca como Top Strength).
- `constitutional_hierarchy` L1-L4 + exemplo trabalhado (unico desempate de conflitos).
- L2 grounding "fonte que PROVA vs DESCREVE" (anti-alucinacao).
- `critical_fields`/`critical_ids` (listas da secao anterior).
- R11/R12 confirmacao tipada em escrita Odoo/banco.
- `session_summaries` + `pendencias` + `user_rules` no hook (continuidade).

Licoes vigentes:
- NAO fazer dial-back de rotulos CRITICAL/NUNCA em lote (audit R1: 94% corretos);
  controle e FORWARD: rotulo novo exige justificativa L1-L4.
- Few-shot mora em skill, nao no system_prompt (PM-2.2, R17).
- Tokens de prompt estatico sao baratos (cache); o custo real e DILUICAO DE ATENCAO —
  poda-se por sinal, nao por byte.
- Mudanca comportamental no system_prompt/hook exige validacao (golden dataset — R5).

## Governanca e enforcement

- **Existente**: pre-commit `pre-commit-prompt-lint.sh` → `prompt_size_audit.py
  --check-delta` (baseline de linhas/tokens do prompt estatico). Crescimento legitimo =
  `--update-baseline` + justificativa.
- **Os 5 checks deste padrao — TODOS registrados no fluxo (F6, 2026-06-10), via
  `pre-commit-prompt-lint.sh`**: (1) consistencia de subagentes
  (`.claude/agents/*.md` ↔ system_prompt `<subagents>` ↔ CLAUDE.md SUBAGENTES) —
  `prompt_size_audit.py --check-consistency`;
  (2) orcamento do listing de skills (soma das descriptions ≤8K chars) —
  `skills_listing_audit.py --check`;
  (3) orcamento do hook por bloco (`tests/agente/sdk/test_hook_budget.py` — F4: ordem-alvo
  + caps Tier 2 + overflow + teto 15KB; F6: caps tier1/user_rules) — roda no pre-commit
  quando o pipeline de injecao (`memory_injection*.py`/`hooks.py`) e tocado;
  (4) invariante de nao-orfandade da deny-list (skill excluida ↔ declarada em
  agents/*.md) — mesmo `--check-consistency`;
  (5) checklist de admissao por camada (este doc) — apontado pelo item 4 do R-EXEC-5
  em `app/agente/CLAUDE.md` (dependencia declarada CUMPRIDA na F6).
- **Plano de implementacao**: ver
  `docs/superpowers/plans/2026-06-09-arquitetura-contexto-boot-agente.md`.

## Fontes

- FONTE: estudo completo do contexto de boot 2026-06-09 — 16 findings em
  `relatorios/estudo_contexto_boot_2026-06-09/findings/` (A1-A6 mapeamento de codigo,
  C1-C4 pesquisa externa, B1-B6 analise critica) + matriz consolidada de 38 itens (B5)
  + verificacao adversarial de 4 criticos. Anexos: dump real do boot (producao,
  09/06/2026), auto-avaliacao do agente (19 achados), avaliacao do Rafael (9 pontos +
  2 ponderacoes) — mesmo diretorio.
- FONTE: Anthropic — Effective Context Engineering for AI Agents; Equipping Agents with
  Agent Skills; Claude Code Best Practices; Prompt Caching docs; Agent SDK docs
  (setting_sources, hooks, subagents — subagentes NAO herdam system prompt do pai).
- FONTE: prior art interno —
  `docs/superpowers/plans/2026-06-04-refactor-governanca-prompt-agente.md`
  (FASES 0/1/2/4/5 fechadas; FASE 3 com T3.3/T3.4 abertas — escopo permanece la),
  `.claude/references/STUDY_PROMPT_ENGINEERING_2026.md`,
  `.claude/references/ROADMAP_PROMPT_ENGINEERING_2026.md` (R5/R17 abertos).
