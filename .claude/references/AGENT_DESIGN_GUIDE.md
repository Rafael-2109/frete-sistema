# Agent Design Guide

**Ultima Atualizacao**: 2026-04-09
**Escopo**: Manual prescritivo para criar e editar subagents no sistema de fretes Nacom Goya.

---

## Contexto

Este guia foi criado na revisao de Abril/2026 dos 12 subagents existentes, apos descoberta de que varios campos oficiais do Claude Code CLI (`skills`, `memory`, `maxTurns`, `effort`) nao estavam sendo usados corretamente ou tinham formato errado.

**Objetivo**: garantir que novos agents ou edicoes de agents existentes sigam as convencoes corretas desde o inicio.

---

## Frontmatter — Campos Oficiais Suportados

Referencia oficial: https://code.claude.com/docs/en/sub-agents (secao "Supported frontmatter fields")

### Obrigatorios

| Campo | Tipo | Notas |
|-------|------|-------|
| `name` | string | Lowercase com hifens. Identificador unico. |
| `description` | string | Chave de routing — explica quando delegar ao agent. Incluir "NAO usar para X" quando relevante. |

### Recomendados

| Campo | Tipo | Notas |
|-------|------|-------|
| `tools` | string CSV ou lista YAML | Allowlist (principio de menor privilegio). Agents read-only: `Read, Bash, Glob, Grep`. Agents com escrita: inclui `Write, Edit`. |
| `model` | string | `opus`, `sonnet`, `haiku`, ou `inherit`. Default: `inherit`. Ver secao "Model Selection". |
| `skills` | **lista YAML** | Injeta conteudo completo das skills no contexto do subagent ao startup. **Formato obrigatorio e lista YAML**, nao string CSV. |

### Condicionais

| Campo | Tipo | Quando usar |
|-------|------|-------------|
| `memory` | `user`/`project`/`local` | **NAO USAR no contexto deste projeto**. Funciona apenas em Claude Code CLI dev — o `agent_loader.py` do agente web (producao) nao extrai este campo. **Persistencia em producao usa o MCP memory server** (`app/agente/tools/memory_mcp_tool.py`, 13 tools). Os 12 subagents ja tem acesso via 6 tools no allowlist (`mcp__memory__view_memories`, `list_memories`, `save_memory`, `update_memory`, `log_system_pitfall`, `query_knowledge_graph`) e instrucoes de uso via `.claude/references/AGENT_TEMPLATES.md#memory-usage`. |
| `disallowedTools` | string CSV ou lista | Denylist — inverso de `tools`. Use quando quer "todas menos X". |
| `permissionMode` | string | `default`/`acceptEdits`/`auto`/`dontAsk`/`bypassPermissions`/`plan`. Cuidado com `bypassPermissions` em producao. |
| `effort` | `low`/`medium`/`high`/`max` | Override do effort level da sessao. `max` apenas em Opus tier (Opus 4.5, 4.6, 4.7). Sonnet/Haiku fazem fallback para `high` no CLI. Opus 4.7 introduz `xhigh` (entre `high` e `max`) — ainda nao exposto no Literal type do SDK 0.1.60, usar via `extra_args` se necessario. |
| `color` | string | Display color: `red`, `blue`, `green`, `yellow`, `purple`, `orange`, `pink`, `cyan`. |
| `background` | bool | `true` = roda em background sempre. Default: `false`. |
| `isolation` | `worktree` | Roda em git worktree isolado. |
| `hooks` | dict | Lifecycle hooks (PreToolUse, PostToolUse, etc.) escopados ao agent. |
| `mcpServers` | dict | MCP servers disponiveis ao agent. |
| `initialPrompt` | string | Auto-submetido como primeiro user turn quando agent roda como main session. |

### NAO USAR

- **`maxTurns`**: **decisao consciente de NAO aplicar** nesta revisao. Risco de cortar operacoes multi-turn em meio de fluxo. Preferir controle manual pelo usuario. Reavaliar se agents comecarem a looping em producao.

---

## Formato `skills:` — Lista YAML Obrigatoria

**ERRADO** (string CSV — parsed como string unica, skills NAO sao carregadas):
```yaml
skills: consultando-sql, monitorando-entregas, resolvendo-entidades
```

**CORRETO** (lista YAML — skills sao injetadas no contexto):
```yaml
skills:
  - consultando-sql
  - monitorando-entregas
  - resolvendo-entidades
```

**Por que**: a funcao `_parse_skills` em `app/agente/config/agent_loader.py` aceita ambos os formatos (backwards compat), mas o parser YAML oficial do Claude Code CLI espera lista. Use sempre lista.

---

## Model Selection

| Modelo | Quando usar |
|--------|-------------|
| `opus` | Decisoes criticas com alto impacto (financeiro, operacional). Ex: analista-carteira, auditor-financeiro, especialista-odoo. |
| `sonnet` | Analises complexas sem escrita irreversivel. Ex: controlador-custo-frete, gestor-devolucoes, gestor-carvia. |
| `haiku` | Pesquisa rapida, exploracao de codigo. Ex: Explore agent built-in. |
| `inherit` | Default — herda do agent pai. |

**Regra pratica**: se o agent TOMA DECISOES que afetam dinheiro/operacao, use `opus`. Se so ANALISA dados, use `sonnet`. Se so BUSCA informacao, use `haiku`.

---

## Claude 4.6 Gotchas (adicionado 2026-04-12)

Claude Opus 4.6 e Sonnet 4.6 sao mais responsivos ao system prompt que versoes anteriores — o que significa que **linguagem agressiva agora causa overuse**, nao apenas compliance.

| Sintoma | Causa | Mitigacao ao criar agent |
|---------|-------|---------------------------|
| **Overtrigger** de tools/skills | "CRITICAL: You MUST use X" | Usar "Use X when..." em routing. Manter "NEVER" APENAS em safety invariants (L1) |
| **Overengineering** | Cria arquivos/abstracoes nao pedidos | Adicionar `<avoid_overengineering>` bloco quando agent faz escrita |
| **Subagent overspawning** | Delega mesmo para tarefas simples | Em agents orquestradores, adicionar `<when_subagents_warranted>` |
| **Latencia alta Sonnet 4.6** | Default `effort: high` | Setar `effort: low` ou `medium` explicito no frontmatter |
| **Prefill 400 error** | Deprecated em Claude 4.6 | NAO usar prefill em novos agents. Usar Structured Outputs |

**Ao criar novo agent**: escrever instrucoes positivas para style/routing ("Use X when...", "Prefer Y for..."), reservar negativas explicitas ("NEVER execute...", "NEVER fabricate...") para safety invariants do L1 constitutional.

**Ao editar agent existente**: rodar golden dataset baseline antes de dial back. PM-2.1 documenta cenario de falha (remocao de MUST pode quebrar compliance P1-P7 em analista-carteira).

> Pesquisa completa: [STUDY_PROMPT_ENGINEERING_2026.md](STUDY_PROMPT_ENGINEERING_2026.md) (pre-mortem + red team)
> Acao planejada: [ROADMAP_PROMPT_ENGINEERING_2026.md](ROADMAP_PROMPT_ENGINEERING_2026.md) R1 (audit + dial back)

---

## Secoes Obrigatorias no System Prompt

Todo agent deve ter estas secoes (ordem recomendada):

1. **Identidade / Missao** — "Voce eh o X da Nacom Goya. Seu papel eh..."
2. **Contexto + Referencias externas** — ponteiros para documentos (lazy loading)
3. **Armadilhas criticas / Guardrails** — gotchas do dominio que devem ser DECORADAS
4. **Arvore de Decisao ou Algoritmo** — como decidir entre skills/delegacoes
5. **Formato de Resposta** — contrato de output (ver `AGENT_TEMPLATES.md#output-format-padrao`)
6. **Boundary Check** — redirects para outros agents (ver `AGENT_TEMPLATES.md#boundary-check-padrao`)
7. **Protocolo de Confiabilidade** — findings file em `/tmp/subagent-findings/` (ver `AGENT_TEMPLATES.md#reliability-protocol-canonical`)

## Secoes Condicionais

- **PRE-MORTEM** — obrigatorio se agent executa acoes irreversiveis (Write, Playwright, reconcile, button_validate). Ver `AGENT_TEMPLATES.md#pre-mortem`. Cenarios devem ser ESPECIFICOS do dominio (nao genericos).
- **AUTO-VALIDACAO PRE-RETORNO (self-critique)** — obrigatorio se agent produz recomendacoes de alto impacto (decisoes P1-P7, reconciliacoes, divergencias). Ver `AGENT_TEMPLATES.md#self-critique`.

---

## Templates Reusaveis

Usar referencias aos blocos canonicos em vez de duplicar conteudo:

```markdown
## PRE-MORTEM

> Ref: `.claude/references/AGENT_TEMPLATES.md#pre-mortem`

**Trigger neste agent**: [situacao especifica]

**Cenarios conhecidos de falha**:
1. [cenario 1 do dominio]
2. [cenario 2 do dominio]
3. [cenario 3 do dominio]

**Decisao**:
- [ ] Prosseguir
- [ ] Prosseguir-com-salvaguarda
- [ ] Escalar-para-humano
```

Templates disponiveis em `.claude/references/AGENT_TEMPLATES.md`:
- `#pre-mortem` — bloco para acoes irreversiveis
- `#self-critique` — bloco de auto-validacao pre-return
- `#output-format-padrao` — formato de resposta base
- `#boundary-check-padrao` — tabela de redirects
- `#reliability-protocol-canonical` — protocolo de findings
- `#memory-usage` — protocolo MCP memory (quando consultar/salvar, taxonomia 5 niveis, formato prescritivo)
- `#constitutional-hierarchy` — L1 Seguranca > L2 Etica > L3 Regras > L4 Utilidade

Para agents Odoo, tambem ver `.claude/references/odoo/AGENT_BOILERPLATE.md`:
- `#regra-zero` — executar rastrear.py ANTES de qualquer coisa
- `#scripts-disponiveis` — scripts comuns Odoo
- `#conexao-odoo` — padrao de conexao com `get_odoo_connection()`
- `#checklist-extrato-bancario` — sequencia draft→write→post→reconcile

---

## Anti-Patterns (NAO FAZER)

1. **Linguagem proativa em agent destrutivo** — remover "Substitui [Rafael] na analise", "Executa automaticamente X", "Decide autonomamente Y" em agents com Write/Edit. Use linguagem descritiva.

2. **Formato `skills:` como string CSV** — `skills: a, b, c` e parseado como string e skills NAO sao carregadas. Usar lista YAML.

3. **Output format ausente** — agents sem contrato de output produzem respostas inconsistentes. Adicionar secao FORMATO DE RESPOSTA.

4. **Boundary check inline em texto** — usar tabela formal, nao bullets soltos. Facilita localizacao visual.

5. **Protocolo simplificado sem as 4 categorias** — Fatos Verificados / Inferencias / Nao Encontrado / Assuncoes. Omitir uma categoria cria ambiguidade.

6. **Duplicar conteudo entre agents** — extrair para reference externa (AGENT_TEMPLATES ou AGENT_BOILERPLATE) e referenciar.

7. **Inventar campos Odoo** — usar `descobrindo.py --listar-campos` ou `MODELOS_CAMPOS.md` para validar nomes.

8. **Pre-mortem generico** — cenarios devem ser ESPECIFICOS do dominio. Nao copiar cenarios de outro agent sem adaptar.

9. **Usar `maxTurns`** — decidido nao aplicar nesta revisao. Risco de cortar fluxo multi-turn.

10. **`description` vaga** — deve explicar QUANDO usar E quando NAO usar. Ex: "Use para X. NAO usar para Y (usar agent-Y)".

---

## Decision Tree: Novo Agent ou Skill?

```
TAREFA A IMPLEMENTAR
│
├─ Orquestra varias skills em sequencia ou arvore de decisao?
│  └─ SIM → AGENT
│
├─ Toma decisoes com impacto financeiro/operacional?
│  └─ SIM → AGENT (com model: opus + pre-mortem + self-critique)
│
├─ Delega para outros agents (orquestrador)?
│  └─ SIM → AGENT
│
├─ Funcionalidade atomica (1 script, 1 query)?
│  └─ SIM → SKILL
│
├─ Sem logica de decisao complexa?
│  └─ SIM → SKILL
│
└─ Duvida? → comecar como SKILL e promover a AGENT se crescer
```

---

## Validacao Antes de Commit

1. **Parse YAML OK**: rodar `python3 -c "import yaml; yaml.safe_load(open('agent.md').read().split('---')[1])"`
2. **Agent loader OK**: rodar agent_loader.py e verificar que o agent e carregado sem warnings
3. **Golden dataset** (se existir): rodar os casos do agent em `.claude/evals/subagents/{agent-name}/dataset.yaml`
4. **Comparar output com `expected_behavior`**: manual, pelo desenvolvedor
5. **Verificar que nenhum item de `must_not` foi violado**

---

## Como Criar Novo Agent

1. Decidir tipo (AGENT vs SKILL) usando decision tree acima
2. Criar arquivo em `.claude/agents/{nome}.md`
3. Frontmatter com campos obrigatorios + skills em lista YAML
4. System prompt com secoes obrigatorias
5. Adicionar pre-mortem se executa acoes irreversiveis
6. Adicionar self-critique se produz recomendacoes
7. Criar golden dataset em `.claude/evals/subagents/{nome}/dataset.yaml` (5+ casos)
8. Atualizar `ROUTING_SKILLS.md` com regras de desambiguacao
9. Atualizar `CLAUDE.md` subagents table (se subagent de dominio)
10. Testar via Task tool e validar contra dataset

---

## Como Editar Agent Existente

1. Ler o agent COMPLETO primeiro (nao editar por partes)
2. Rodar golden dataset antes da edicao (baseline)
3. Aplicar edicao
4. Rodar golden dataset depois (verificar nenhuma regressao)
5. Se caso falhou: corrigir agent OU adicionar caso novo que captura o cenario
6. Commit com mensagem explicando o "por que"

---

## Referencias

- [Documentacao oficial Claude Code subagents](https://code.claude.com/docs/en/sub-agents)
- `.claude/references/AGENT_TEMPLATES.md` — blocos reusaveis
- `.claude/references/odoo/AGENT_BOILERPLATE.md` — boilerplate Odoo
- `.claude/references/SUBAGENT_RELIABILITY.md` — protocolo de confiabilidade
- `.claude/references/ROUTING_SKILLS.md` — routing entre agents e skills
- `.claude/evals/subagents/README.md` — framework de avaliacao offline
- `app/agente/config/agent_loader.py` — loader local do agente web (referencia de parsing)
