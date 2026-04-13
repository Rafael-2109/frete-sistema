# Quality Review: system_prompt.md v4.2.0

**Versao**: 1.0 (review) — findings aplicados em 2026-04-12 (tarde) como v4.3.0
**Data**: 2026-04-12
**Objeto avaliado**: `app/agente/prompts/system_prompt.md` (v4.2.0 @ review, v4.3.0 apos aplicacao)

> **UPDATE 2026-04-12 (tarde)**: Findings Q2, Q3, Q4, Q5, Q6, Q7, Q8 + CG1, CG2, CG5, CG6 APLICADOS em commit coerente. Q1 (few-shot) NAO aplicado — empurrado para R17 (progressive disclosure em skills). Ver [ROADMAP_PROMPT_ENGINEERING_2026.md](ROADMAP_PROMPT_ENGINEERING_2026.md) changelog 2026-04-12 (tarde). Prompt agora em v4.3.0.
**Tamanho**: ~407 linhas / ~2.7K tokens
**Rubrica**: [STUDY_PROMPT_ENGINEERING_2026.md](STUDY_PROMPT_ENGINEERING_2026.md) secoes A-M
**Companion**: [ROADMAP_PROMPT_ENGINEERING_2026.md](ROADMAP_PROMPT_ENGINEERING_2026.md)

---

## Context

Os audits anteriores (R1-R4 + baseline) cobriram **seguranca e conformidade tecnica** — contagem de linguagem agressiva, prompt injection defenses, session_context audit, prefill conformance — mas nao avaliaram a **qualidade intrinseca** do system_prompt como documento operacional.

Este review preenche esse gap com:
- Score por dimensao A-M da rubrica STUDY
- Findings concretos (linha:trecho + issue + recomendacao)
- Issues priorizados P0-P2
- Coverage gaps (cenarios operacionais nao cobertos)
- Token efficiency analysis
- Golden Rule assessment

**Escopo**: avaliar o documento **como esta** (v4.2.0), nao propor v5. Recomendacoes concretas sao acionaveis mas nao aplicadas.

---

## Executive Summary

### Overall Score: **4.3 / 5** (MUITO BOM)

System prompt maduro, bem estruturado, com aplicacao consciente de best practices Anthropic. Principais pontos fortes sao **Memory Protocol (R0)**, **reversibility awareness (R3)**, **coordination protocol (H2/H3/H5)** e **separacao estrutural para prompt caching (L1-L6)**. Principais gaps sao **ausencia de few-shot examples formais**, **constitutional hierarchy L1-L4 nao explicita** (apesar de presente nos subagents), e **nao mencao de parallel tool calls** — todos corrigiveis com baixo risco.

### Top 7 Strengths

1. **Memory protocol R0 exemplar** — completo, prescritivo, com timing ("IMEDIATAMENTE"), triggers especificos (8 categorias), constraints e formato narrativo
2. **Uso de `<why>` blocks** — R2/R3/R4/R9 tem motivacao explicita do por que, alinhado com A2 (Anthropic Golden Rule sobre contexto)
3. **R3 Confirmação Obrigatória** — aplica reversibility awareness (G1) com criterios literais ("opção A", "confirmar", "sim")
4. **Coordination protocol para subagents** — primeira regra e "prefira resolver direto" → H5 Anthropic aplicado corretamente, contra-pattern de overspawning
5. **Prompt caching architecture** — vars dinamicas (`data_atual`, `user_id`, `user_name`) extraidas do template e injetadas via hook, mantendo system prompt estatico (L1-L6)
6. **Tool descriptions auto-descritas** — R5 diz "MCP tools (mcp__server__tool) sao in-process — suas descricoes definem quando usar cada uma", alinhado com D3 Anthropic (nao duplicar em prompt)
7. **Progressive disclosure via skills** — comentario HTML documenta que "Descriptions completas estao no YAML de cada SKILL.md e sao carregadas automaticamente pelo CLI" (I1-I2)

### Top 8 Issues (priorizadas)

| # | Issue | Severidade | Dimensao |
|---|-------|------------|----------|
| Q1 | Zero few-shot examples formais (`<example>` tags) | Media | A3 |
| Q2 | Constitutional hierarchy L1-L4 ausente (mas presente em agents) | Media | M1 |
| Q3 | Parallel tool calls nao mencionado | Baixa | D2 |
| Q4 | Self-check pre-return ausente (para decisoes criticas) | Media | E5 |
| Q5 | Context awareness prompt ausente | Baixa (ROADMAP R7 cobre) | F5 |
| Q6 | Tag inconsistency em regras R0-R0d (5 tags distintas) | Baixa | B1 |
| Q7 | `<current_context>` mistura business snapshot + role definition | Muito baixa | A6 |
| Q8 | Tratamento de erros transientes (Odoo/SSW timeout) nao especificado | Media | F4 |

---

## Score Card (Rubrica A-M)

Notas: 1 (ausente/errado) → 5 (exemplar)

### A. Fundamentos (General Principles)

| # | Dimensao | Nota | Justificativa |
|---|----------|------|---------------|
| A1 | Be clear and direct | **4/5** | `<role_definition>` e `<instructions>` claros. Golden Rule parcialmente satisfeito — colega tecnico entenderia, colega nao-tecnico nao. |
| A2 | Context/motivation (`<why>`) | **5/5** | R2, R3, R4, R9 tem `<why>` inline. Exemplo: R3 explica "Separação errada faz o armazém separar fisicamente itens indevidos → ocupa staging, restringe disponibilidade, pode gerar frete perdido". |
| A3 | Use examples (few-shot) | **1/5** | **AUSENTE**. Zero `<example>` tags no prompt inteiro. R8 tem exemplo em texto corrido, nao em tag formal. Oportunidade alta. |
| A4 | Give Claude a role | **5/5** | `<metadata><role>` + `<role_definition>` explicito: "Agente logistico Nacom Goya (chat operacional, ambiente de producao)". |
| A5 | Tell what to do (positivo) | **4/5** | Balanco correto — style em positivo ("Padrao: resultado direto, 2-3 paragrafos"), safety em negativo ("NUNCA chute quando ambiguo"). RT-5.1 do STUDY confirma esse split. |
| A6 | Match style | **4/5** | Prompt e prose+tabelas+listas, output esperado similar. Mas `<current_context>` mistura tom operacional com snapshot de negocio. |

**Media A**: **3.83 / 5**

### B. Estrutura XML

| # | Dimensao | Nota | Justificativa |
|---|----------|------|---------------|
| B1 | Consistent tag names | **3/5** | Inconsistencia: R0-R0d usam 5 tags distintas (`<memory_protocol>`, `<role_awareness>`, `<pendencia_protocol>`, `<scope_awareness>`, `<operational_directives_protocol>`), depois R1-R9 usam uniformemente `<rule id="Rx">`. Padronizacao melhoraria parsing. |
| B2 | Nested tags | **4/5** | Hierarquia natural: `<instructions>` > `<rule>`, `<tools>` > `<skills>` + `<subagents>` > `<agent>`, `<memory_protocol>` > `<auto_save>` + `<explicit_save>` + `<constraints>`. |
| B3 | Longform data top | N/A | Prompt nao tem longform data (pura instrucao). |
| B4 | Quotes grounding | N/A | N/A. |
| B5 | Reasoning/answer separation | N/A | N/A para system prompt. |

**Media B** (itens aplicaveis): **3.5 / 5**

### C. Output Control

| # | Dimensao | Nota | Justificativa |
|---|----------|------|---------------|
| C1 | Format indicators | **4/5** | R1 "Padrao: resultado direto, 2-3 paragrafos + 1 tabela resumo". I2/I3/I4 com format esperado. |
| C2 | Structured Outputs | N/A | Feature da API, nao do prompt. |
| C3 | Conciso | **4/5** | R1 "Comunicacao Direta" pede concisao. Alinhado com Claude 4.6 (mais conciso por default). |
| C4 | LaTeX | N/A | N/A (dominio de logistica, nao matematica). |

**Media C**: **4.0 / 5**

### D. Tool Use

| # | Dimensao | Nota | Justificativa |
|---|----------|------|---------------|
| D1 | Literal instructions | **4/5** | R3 e muito literal ("aguarde resposta explícita: 'opção A', 'confirmar', 'sim'"). R5 deixa implicito quando usar. |
| D2 | Parallel tool calls | **2/5** | **NAO MENCIONA**. Oportunidade perdida — agente logistico com queries multi-cliente se beneficiaria muito. Anthropic recomenda `<use_parallel_tool_calls>` bloco. |
| D3 | Tool descriptions auto-descritas | **5/5** | R5 explicitamente remove a tabela MCP (conforme CLAUDE.md v3: "R5: tabela MCP removida — ~150 tokens salvos"). Alinhado. |
| D4 | Namespacing | **5/5** | MCP tools usam `mcp__server__tool`. Padrao Anthropic. |
| D5 | Tool Search dinamico | N/A | Feature SDK. |
| D6 | Writing tools for agents | N/A | Sobre design de tools, nao uso. |

**Media D** (itens aplicaveis): **4.0 / 5**

### E. Thinking / Reasoning

| # | Dimensao | Nota | Justificativa |
|---|----------|------|---------------|
| E1 | Adaptive thinking | **3/5** | NAO menciona explicitamente. Pode ser deliberado (default do SDK), mas deveria ao menos ter "think thoroughly before recommending P1-P7". |
| E2 | Prefer general instructions | **4/5** | Aplicado implicitamente — regras sao narrativas, nao step-by-step prescritivo. |
| E3 | Multishot thinking tags | **1/5** | Sem examples, sem thinking tags em examples. Pareia com A3. |
| E4 | Manual CoT fallback | N/A | SDK tem adaptive on. |
| E5 | Self-check pre-return | **2/5** | **AUSENTE** no system_prompt (agents tem via AGENT_TEMPLATES). R2 Validação P1 seria o candidato ideal. |
| E6 | "Think" sensitivity | N/A | Relevante para agents com thinking off. |
| E7 | Prevent overthinking | **3/5** | Nao menciona. Pode ser issue com Claude 4.6 Opus (over-exploration). |

**Media E** (itens aplicaveis): **2.6 / 5** — dimensao mais fraca

### F. Agentic Systems

| # | Dimensao | Nota | Justificativa |
|---|----------|------|---------------|
| F1 | Long-horizon state tracking | **4/5** | R0 auto_save + R0b pendencia_protocol + R6 sessoes anteriores cobrem. |
| F2 | Multi-context window | N/A | Chat web, sessao unica. |
| F3 | Structured state | N/A | N/A. |
| F4 | Verification tools | **3/5** | Implicito via R4 e R5. Poderia ser explicito: "Ao produzir dados criticos, validar via query de confirmacao". |
| F5 | Context awareness prompt | **2/5** | **AUSENTE**. ROADMAP R7 planeja adicionar. |
| F6 | Research pattern | **4/5** | `<routing_confidence>` tem pattern estruturado de desambiguacao. |

**Media F** (itens aplicaveis): **3.25 / 5**

### G. Safety / Autonomy

| # | Dimensao | Nota | Justificativa |
|---|----------|------|---------------|
| G1 | Reversibility-aware | **5/5** | R3 Confirmação Obrigatória e textbook. `<cannot_do>` lista operacoes irreversiveis. |
| G2 | Destructive shortcut | **4/5** | Implicito via R3 e `<cannot_do>`. Poderia ter "Quando encontrar obstaculo, investigar root cause". |
| G3 | Sandboxing | **4/5** | `<scope>` > `<can_do>`/`<cannot_do>` explicito. |

**Media G**: **4.33 / 5**

### H. Subagents / Orchestration

| # | Dimensao | Nota | Justificativa |
|---|----------|------|---------------|
| H1 | Flat hierarchy | **4/5** | Nao menciona (SDK enforça), mas 12 agents listados sem recursao. |
| H2 | Token multipliers awareness | **5/5** | `<coordination_protocol>` primeira regra: "Prefira resolver direto. Consulta simples → use mcp__sql ou skill diretamente. Delegue a subagente quando: cross-módulo, 4+ operações, ou análise complexa". **Exemplar** — alinhado com Claude 4.6 overuse guard. |
| H3 | Parent chains | **5/5** | "Tarefas independentes → delegue em paralelo. Dependentes → sequencialmente". |
| H4 | Model routing per subagent | **4/5** | Delegado para agent_loader (frontmatter de cada agent). Nao no prompt principal — correto arquiteturalmente. |
| H5 | Overuse guard | **5/5** | Ja coberto em H2. |
| H6 | Skill chaining > nesting | **4/5** | Implicito. 18+ skills + 12 agents bem separados. |

**Media H**: **4.5 / 5** — dimensao mais forte

### I. Progressive Disclosure (Skills)

| # | Dimensao | Nota | Justificativa |
|---|----------|------|---------------|
| I1 | Three levels | **5/5** | Comentario HTML documenta progressive disclosure: "Descriptions completas (USAR QUANDO / NAO USAR QUANDO) estão no YAML de cada SKILL.md e são carregadas automaticamente pelo CLI". |
| I2 | Scale awareness | **5/5** | Projeto tem 18+ skills, discovery ~1.5K tokens (median 80/skill). Eficiente. |
| I3 | Context budget | N/A | Operacional do SDK. |
| I4 | /clear equivalent | N/A | Chat web. |

**Media I** (itens aplicaveis): **5.0 / 5**

### J. Memoria

| # | Dimensao | Nota | Justificativa |
|---|----------|------|---------------|
| J1 | Memory protocol completo | **5/5** | R0 memory_protocol e o **ponto mais forte do prompt**. Auto_save com 8 categorias de triggers, explicit_save, constraints, timing ("IMEDIATAMENTE"), formato narrativo, dedup. Alinhado com MEMORY_PROTOCOL.md. |
| J2 | External artifacts | N/A | Chat web. |
| J3 | JSON para state | N/A | N/A. |

**Media J** (itens aplicaveis): **5.0 / 5**

### K. Context Management

| # | Dimensao | Nota | Justificativa |
|---|----------|------|---------------|
| K1 | /clear equivalent | N/A | Chat web tem session reset. |
| K2 | Compaction awareness | **4/5** | SDK gerencia. R0 memory protocol cobre persistencia. |
| K3 | /rewind | N/A | N/A. |
| K4 | Resume with context | **5/5** | `<pendencia_protocol>` R0b e exemplar: "Para CADA pendencia: avaliar, resolver, ou perguntar explicitamente". |

**Media K** (itens aplicaveis): **4.5 / 5**

### L. Prompt Caching

| # | Dimensao | Nota | Justificativa |
|---|----------|------|---------------|
| L1 | Order fixa | N/A | Gerenciado pelo SDK. |
| L2 | Cache hit target | N/A | Medicao operacional. |
| L3 | Min cacheable | **5/5** | ~2.7K tokens > 1024 (Sonnet min). OK para cache. |
| L4 | cache_control | **5/5** | Aplicado no SDK (ver `app/agente/CLAUDE.md` secao "Prompt Cache Optimization"). |
| L5 | Separate tools from prompt | **5/5** | Tools em `<tools>` com referencia a skills externas, nao duplicado. |
| L6 | Dynamic via hook | **5/5** | `{data_atual}`, `{usuario_nome}`, `{user_id}` extraidos do template v4.2.0 e injetados via `_user_prompt_submit_hook`. Exemplar. |

**Media L** (itens aplicaveis): **5.0 / 5**

### M. Constitutional Hierarchy

| # | Dimensao | Nota | Justificativa |
|---|----------|------|---------------|
| M1 | L1-L4 explicita | **3/5** | **AUSENTE no system_prompt do agente web**. Agents de dominio tem via AGENT_TEMPLATES#constitutional-hierarchy, mas o **principal** nao. R0d menciona `priority="critical"` mas nao explicita L1-L4. |
| M2 | Conflict resolution | **3/5** | Implicito. Casos como "usuario quer rapido mas R3 exige confirmacao" nao documentados. |
| M3 | Constitutional AI | **5/5** | L1 invariants (safety, fabricacao, escrita sem confirmacao) espalhados em R3, R4, `<cannot_do>`. Funciona mas sem label explicita. |

**Media M**: **3.67 / 5**

### Scorecard Final

| Dimensao | Media | Peso | Contribuicao |
|----------|-------|------|--------------|
| A. Fundamentos | 3.83 | 1.5x | 5.75 |
| B. Estrutura XML | 3.50 | 1.0x | 3.50 |
| C. Output Control | 4.00 | 0.5x | 2.00 |
| D. Tool Use | 4.00 | 1.0x | 4.00 |
| E. Thinking | 2.60 | 1.0x | 2.60 |
| F. Agentic Systems | 3.25 | 1.0x | 3.25 |
| G. Safety | 4.33 | 2.0x | 8.66 |
| H. Subagents | 4.50 | 1.5x | 6.75 |
| I. Progressive Disclosure | 5.00 | 0.5x | 2.50 |
| J. Memoria | 5.00 | 1.5x | 7.50 |
| K. Context Management | 4.50 | 0.5x | 2.25 |
| L. Prompt Caching | 5.00 | 0.5x | 2.50 |
| M. Constitutional Hierarchy | 3.67 | 1.0x | 3.67 |

**Score ponderado**: **54.93 / 12.5** = **4.39 / 5** (MUITO BOM)

Dimensoes acima da media (ponto forte): I, J, L (5.0), H (4.5), K (4.5), G (4.33)
Dimensoes abaixo da media (alvo de melhoria): **E (2.6)**, F (3.25), B (3.5), M (3.67), A (3.83)

---

## Findings Concretos

### Q1. Zero few-shot examples formais (A3)

**Localizacao**: todo o prompt
**Severidade**: Media
**Issue**: Zero `<example>` ou `<examples>` tags. Anthropic recomenda explicitamente "3-5 examples" para steerability. R8 "Deteccao de Padroes Repetitivos" tem exemplo inline em texto, mas nao em tag formal.

**Recomendacao**: Adicionar `<example>` tags em 3 regras criticas:
1. **R2 Validação P1** — mostrar input valido e caso de falha
2. **R3 Confirmação Obrigatória** — mostrar fluxo completo A/B/C → resposta → execucao
3. **R8 Padroes Repetitivos** — formalizar o exemplo inline atual

**Ressalva**: few-shot custa tokens. Alternativa: adicionar examples em `app/agente/prompts/` como arquivo separado carregado via hook (progressive disclosure). ROADMAP R17 aborda isso em skills, poderia ser estendido para system_prompt.

---

### Q2. Constitutional hierarchy L1-L4 ausente (M1)

**Localizacao**: todo o prompt
**Severidade**: Media
**Issue**: Subagents tem `constitutional-hierarchy` via `AGENT_TEMPLATES.md` (L1 Safety > L2 Ethics > L3 Rules > L4 Utility), mas o agente principal NAO tem bloco explicito. R0d `operational_directives_protocol` menciona `priority="critical"` mas nao e a mesma coisa.

**Recomendacao**: Adicionar bloco `<constitutional_hierarchy>` no topo de `<instructions>`, logo apos `<context>`:

```xml
<constitutional_hierarchy>
  Quando regras conflitam, a prioridade e:
  L1 SEGURANCA (inviolavel): Nao fabricar dados, confirmar antes de irreversivel, escalar quando nao coberto pela doc.
  L2 ETICA (inviolavel): Declarar incertezas, reportar resultados negativos, distinguir fato de inferencia.
  L3 REGRAS DE NEGOCIO: P1-P7, R2 Validação, R3 Confirmação, I2-I4.
  L4 UTILIDADE: Concisao, formato BR, linguagem operacional (I5/I6).

  Exemplo: usuario pede "cria separacao rapido sem perguntar" → L1 prevalece sobre L4 → seguir R3 Confirmação.
</constitutional_hierarchy>
```

**Custo**: ~100 tokens. **Beneficio**: prevent ambiguidade em casos de conflito.

---

### Q3. Parallel tool calls nao mencionado (D2)

**Localizacao**: R5 MCP Tools
**Severidade**: Baixa
**Issue**: Anthropic recomenda explicitar parallel tool calling para boost de ~100%. Agente logistico tem casos obvios (multi-cliente, multi-periodo, multi-regra).

**Recomendacao**: Adicionar em R5 (ou como R5a):

```xml
<use_parallel_tool_calls>
Quando precisar consultar multiplas fontes independentes (ex: estoque de palmito + producao programada + pedidos Atacadao), faca as calls EM PARALELO numa unica resposta. Nao sequencie quando nao ha dependencia.
Exceção: quando o resultado de uma call e parametro da proxima (entity_id depois de entity_resolution).
</use_parallel_tool_calls>
```

**Custo**: ~80 tokens. **Beneficio**: latencia menor em queries comuns.

---

### Q4. Self-check pre-return ausente (E5)

**Localizacao**: R2 Validação P1 (candidato principal)
**Severidade**: Media
**Issue**: Agents criticos tem `self-critique` via AGENT_TEMPLATES. System_prompt nao tem equivalente. R2 recomenda embarque mas nao tem checklist antes de responder.

**Recomendacao**: Adicionar `<self_check>` em R2:

```xml
<rule id="R2" name="Validação P1">
  ...
  <self_check>
    Antes de recomendar embarque, verificar mentalmente:
    - [ ] data_entrega_pedido consultada e e <= D+2?
    - [ ] observ_ped_1 revisada e sem conflito?
    - [ ] Separação existente cruzada (sincronizado_nf=False)?
    - [ ] Se FOB: disponibilidade 100% confirmada?

    Se qualquer [ ] falhar → NAO recomende. Informe o gap ao usuario.
  </self_check>
</rule>
```

**Custo**: ~100 tokens. **Beneficio**: menos falsos positivos em recomendacao critica.

---

### Q5. Context awareness prompt ausente (F5)

**Localizacao**: ausente
**Severidade**: Baixa (ROADMAP R7 ja planeja)
**Issue**: Claude 4.6 rastreia seu proprio token budget nativamente, mas sem prompt para "nao parar cedo por orcamento de tokens", pode encurtar respostas.

**Recomendacao**: Ja planejado em ROADMAP R7. Adicionar bloco apos `<instructions>`.

---

### Q6. Tag inconsistency em regras R0-R0d (B1)

**Localizacao**: `<instructions>` linhas 32-114
**Severidade**: Baixa
**Issue**: R0-R0d usam 5 tags distintas:
- `<memory_protocol id="R0">`
- `<role_awareness id="R0a">`
- `<pendencia_protocol id="R0b">`
- `<scope_awareness id="R0c">`
- `<operational_directives_protocol id="R0d">`

Depois R1-R9 + I2-I4 usam uniformemente `<rule id="Rx" name="...">`. Inconsistencia.

**Recomendacao**: Padronizar tudo como `<rule id="R0" name="Memory Protocol">` etc. Isso reduz ambiguidade no parsing do modelo e facilita referencia cruzada. Esforco trivial (15 min), zero risco semantico.

---

### Q7. `<current_context>` mistura business + role (A6)

**Localizacao**: `<context>` linhas 12-18
**Severidade**: Muito baixa
**Issue**:
```xml
<current_context>
  Voce está no ambiente em produção.              ← role awareness
  Nacom Goya: industria de alimentos...           ← business snapshot
  Atacadao = ~50% do faturamento. Assai = ~13%.  ← business snapshot
  ~500 pedidos/mes.                                ← metric
  Gargalos recorrentes: agendas > materia-prima.  ← operational context
</current_context>
```

Mistura 4 tipos de informacao em 1 tag. Semantica e clara para humanos mas modelo pode parsear melhor com separacao.

**Recomendacao**: Separar em:
```xml
<environment>Producao. Operacoes reais.</environment>
<business_snapshot>
  Nacom Goya: industria de alimentos (~R$ 16MM/mes, ~500 pedidos/mes).
  Clientes principais: Atacadao ~50%, Assai ~13%.
  Gargalos recorrentes: agendas de entrega > materia-prima > capacidade producao.
</business_snapshot>
```

**Custo**: +20 tokens. **Beneficio**: marginal, mas limpa.

---

### Q8. Erros transientes (Odoo/SSW timeout) nao especificados (F4)

**Localizacao**: ausente no system_prompt
**Severidade**: Media
**Issue**: Odoo e SSW tem historicamente timeouts e Circuit Breaker aberto. Agente nao sabe como reagir:
- Tentar de novo?
- Informar e esperar usuario?
- Escalar para human?
- Usar fallback (mcp__sql direto)?

R5 MCP Tools diz "Se MCP tool falhar: informe o erro ao usuario. Bash nao substitui MCP." — cobre parcialmente, mas nao trata retry/fallback.

**Recomendacao**: Adicionar `<rule id="R10" name="Erros Transientes">`:

```xml
<rule id="R10" name="Erros Transientes">
  Quando uma tool falhar (timeout, connection error, Circuit Breaker aberto):
  1. Informe ao usuario o erro EXATO (nao resuma como "erro")
  2. Ofereca alternativa: "Posso tentar via mcp__sql direto? Ou aguardar e tentar de novo em 30s?"
  3. NUNCA invente dados para contornar a falha
  4. Se Odoo Circuit Breaker aberto: informe que esta aberto, sugira Render MCP para diagnosticar
  5. Se SSW indisponivel: informe e aguarde confirmacao antes de retry
  <why>
    Retry automatico pode agravar saturacao (Odoo). Inventar dados causa decisao errada.
  </why>
</rule>
```

**Custo**: ~150 tokens. **Beneficio**: alto — evita frustracao em falhas comuns.

---

## Coverage Gaps (cenarios operacionais nao cobertos)

Alem dos findings Q1-Q8, analisei cenarios operacionais reais e encontrei gaps:

### CG1. Fim de sessao gracioso

**Cenario**: Usuario diz "obrigado, e so isso". Agente deveria:
- Salvar contexto (ja faz via R0)
- NAO continuar propondo acoes
- Confirmar entrega de toda informacao solicitada

**Status atual**: sem instrucao. Agente pode continuar tentando ser util demais.

**Recomendacao**: adicionar 1 linha em R1 ou R6: "Quando usuario sinalizar fim de tarefa ('obrigado', 'so isso', 'fechado'), confirme brevemente e nao continue propondo acoes."

---

### CG2. Dados contraditorios (local vs Odoo)

**Cenario**: Local diz pedido faturado, Odoo diz em aberto. Qual fonte vence?

**Status atual**: CLAUDE.md raiz diz "Se encontrar inconsistencias em dados locais/Render originados do Odoo, TAMBEM verificar direto no Odoo", mas o system_prompt nao reforca. R4 Dados Reais nao distingue fontes.

**Recomendacao**: adicionar em R4 ou como R4a:

```xml
Quando dados locais divergem do Odoo (ex: status NF, reconciliacao),
Odoo e a fonte canonica. Informe a divergencia ao usuario explicitamente.
```

---

### CG3. Usuario frustrado / emocional

**Cenario**: Usuario: "ISSO JA ESTA ERRADO HA 3 DIAS, TO FURIOSO". Agente deveria:
- Reconhecer a frustracao
- Priorizar solucao
- Escalar se necessario

**Status atual**: sem guidance. Agente pode seguir protocolo normal (frio), aumentando frustracao.

**Recomendacao**: baixa prioridade. Pode ser heuristica via memoria (R0 auto-save).

---

### CG4. Multi-turn analysis (conversa longa)

**Cenario**: Usuario faz 15 perguntas sobre a mesma carteira ao longo de 30 min. Agente pode perder contexto, repetir queries, gerar inconsistencia.

**Status atual**: R0 memory protocol + R6 comportamentos proativos cobrem parcialmente.

**Recomendacao**: nao adicionar — ja coberto pelo SDK (compaction) e pela memoria.

---

### CG5. Ambiguidade em timezone

**Cenario**: Usuario: "pedido de amanha". Amanha e D+1 hoje ou D+1 quando o pedido foi solicitado?

**Status atual**: `<session_context>` tem `data_atual` injetada. Mas system_prompt nao orienta sobre "quando usuario diz 'amanha', referencia data_atual".

**Recomendacao**: adicionar 1 linha: "Referencias temporais relativas ('hoje', 'amanha', 'essa semana') usam `<data_atual>` como referencia."

---

### CG6. Confidencialidade cross-user

**Cenario**: Usuario A pergunta "o que usuario B perguntou ontem?". Agente NAO deveria vazar.

**Status atual**: `<cannot_do>` lista "acessar ou mencionar tabelas pessoal_*". Mas NAO lista "nao vazar sessoes de outros users" explicitamente.

**Recomendacao**: adicionar em `<cannot_do>`:
```
...acessar ou mencionar conteudo de sessoes de outros usuarios (exceto em debug_mode, onde cross-user e autorizado e logado).
```

---

## Token Efficiency Analysis

**Tamanho atual**: ~407 linhas / ~2.7K tokens (estimado)

### Breakdown aproximado

| Bloco | Tokens estimados | % |
|-------|------------------|---|
| `<metadata>` | ~40 | 1.5% |
| `<context>` | ~250 | 9.3% |
| `<instructions>` R0-R0d | ~800 | 29.6% |
| `<instructions>` R1-R9 | ~900 | 33.3% |
| `<instructions>` I2-I4 | ~200 | 7.4% |
| `<tools>` coordination | ~200 | 7.4% |
| `<tools>` 11 agents | ~200 | 7.4% |
| `<business_context>` | ~100 | 3.7% |
| `<knowledge_base>` | ~30 | 1.1% |

### Oportunidades de enxugamento (~15% ou ~400 tokens)

1. **R5 MCP Tools + R4 Dados Reais** — algum overlap. "Use dados consultados, nao invente" aparece em ambos. **Economia**: ~50 tokens
2. **R0 memory_protocol** — `<auto_save>` tem 8 categorias, algumas podem consolidar ("Correcao" + "Regra de negocio" sao quasi-sinonimos). **Economia**: ~60 tokens
3. **`<coordination_protocol>` repete principios de H2/H3 em multiplas `<rule>` entries** — consolidar. **Economia**: ~80 tokens
4. **Cada `<agent>` tem `<delegate_when>` + `<capabilities>`** — muitas vezes redundantes. Pode virar 1 campo `<when>` com descricao unificada. **Economia**: ~100 tokens
5. **`<business_context>` duplica info de `<current_context>`** — P1-P7 aparece em ambos. **Economia**: ~40 tokens
6. **Comentarios HTML extensos** — validos para devs mas custam tokens em cache. Mover para `.md` externo (nao via hook). **Economia**: ~70 tokens

**Total potencial**: ~400 tokens (15% reducao) sem perda semantica.

**Ressalva**: tokens baratos (cache hit 10% do custo). ROI de enxugamento e **baixo** — prioridade nao alta. So fazer se adicionar novos blocos (Q1-Q8) para manter budget.

---

## Golden Rule Assessment ("show to colleague")

Anthropic Golden Rule: "Mostre seu prompt a um colega sem contexto. Se eles ficariam confusos, Claude tambem vai ficar."

### Pergunta: um operador logistico novo conseguiria seguir o system_prompt?

**Partes claras (passam)**:
- `<role_definition>`: ✅ claro
- R1 Comunicacao Direta: ✅ claro
- R3 Confirmação Obrigatória: ✅ claro (exemplos literais)
- `<scope>` can_do/cannot_do: ✅ claro
- R4 Dados Reais: ✅ claro (com `<why>`)

**Partes obscuras (falham)**:
- R0d operational_directives_protocol: ❌ colega nao sabe o que e `<operational_directives priority="critical">` — e meta-instrucao. **Fix**: renomear para "Protocolo de Diretivas do Sistema" ou explicar inline.
- R5 MCP Tools "consulta simples → mcp__sql direto, operacao com logica → skill apropriada": ❌ colega nao sabe o que e "logica". Exemplo ajudaria.
- `<routing_confidence>` "Exponha o criterio de decisao, nao a duvida generica": ❌ abstrato. Exemplos do proprio prompt sao bons, mas precisam ser em `<example>` formal.
- `<coordination_protocol>` "Consulta simples (1-2 tabelas, dados de 1 módulo) → mcp__sql": ❌ colega nao sabe contar "tabelas" e "modulos" de um query SQL textual.

### Pergunta: um Claude 4.6 seguiria?

**Sim, com alta fidelidade**. O prompt e estruturado, XML consistente em rules, `<why>` inline. Claude 4.6 e bom em instruction following.

**Issues secundarias**:
- Claude 4.6 pode overtrigger `consultar_schema` porque R5 diz "Obrigatorio antes de Bash com python -c" — a palavra "Obrigatorio" soma com "MUST" em linguagem treinada. Nao e bug, mas e o cenario overtriggering descrito no STUDY insight 1.

---

## Recomendacoes Priorizadas

### P0 (fazer se/quando redesenhar prompt)

Nenhum item bloqueia o uso atual. O prompt e funcional e seguro.

### P1 (proximo refactor — adicionar valor claro)

| # | Acao | Custo | Beneficio |
|---|------|-------|-----------|
| Q2 | Constitutional hierarchy L1-L4 bloco | +100 tokens | Resolucao explicita de conflitos |
| Q4 | Self-check pre-return em R2 | +100 tokens | Reduz falsos positivos em embarque |
| Q8 | R10 Erros Transientes | +150 tokens | UX em falhas Odoo/SSW |
| CG2 | Odoo como fonte canonica em R4 | +30 tokens | Resolve divergencia local vs Odoo |

**Total P1**: +380 tokens (~14% do prompt atual)

### P2 (melhorias quando houver motivo para mexer)

| # | Acao | Custo | Beneficio |
|---|------|-------|-----------|
| Q1 | Few-shot examples em R2, R3, R8 | +400 tokens | Melhor instruction following (mas ROI baixo — Claude 4.6 ja e bom) |
| Q3 | Parallel tool calls bloco | +80 tokens | Latencia menor em queries multi-cliente |
| Q5 | Context awareness prompt (ROADMAP R7) | +50 tokens | Nao parar cedo |
| Q6 | Padronizar tags R0-R0d como `<rule>` | 0 tokens | Consistencia, parseamento |
| Q7 | Separar `<environment>` de `<business_snapshot>` | +20 tokens | Marginal |
| CG1 | Fim de sessao gracioso | +30 tokens | UX |
| CG5 | Timezone relativa | +20 tokens | Elimina ambiguidade |
| CG6 | Confidencialidade cross-user em `<cannot_do>` | +20 tokens | Seguranca |

**Total P2**: +620 tokens

### Enxugamento compensatorio (se aplicar todas P1+P2)

Opportunities identificadas em "Token Efficiency Analysis": ~400 tokens removiveis.

**Delta liquido se aplicar TUDO**: +380 (P1) + +620 (P2) - 400 (enxugamento) = **+600 tokens** (~22% crescimento)

Novo tamanho projetado: ~3.3K tokens (ainda cacheavel, ainda <10% de context window).

---

## Comparacao com leaked Opus 4.6 system prompt

Para contextualizar o score:

| Aspecto | Nacom v4.2.0 | Anthropic Opus 4.6 leaked |
|---------|--------------|---------------------------|
| Tamanho | ~2.7K tokens | ~200K tokens |
| Estrutura XML | Consistente em rules, inconsistente em R0-R0d | Hierarchico com 17 secoes tematicas |
| Few-shot | 0 | Muitos (memory, file handling, visual output) |
| Redundancia | Baixa | Intencional (safety rules repetidas com escalating specificity) |
| Constitutional hierarchy | Implicita | Explicita com exceptions |
| Meta-instruction alerts | Ausente | Presente |
| `<why>` blocks | Presente (otimo) | Presente |

**Conclusao**: Nacom prompt e dramaticamente mais enxuto (2.7K vs 200K) por 2 razoes:
1. Escopo restrito (logistica Nacom, nao assistente geral)
2. Progressive disclosure via skills (SKILL.md carregam sob demanda)

Nao e necessario imitar a Anthropic em tamanho. Mas **alguns padroes** podem ser adotados:
- Meta-instruction alert (**ja planejado em R3b via PROMPT_INJECTION_HARDENING.md**)
- Constitutional hierarchy explicita (**Q2 P1**)
- Redundancia intencional em safety rules criticas (R3 poderia aparecer em 2 lugares)

---

## Veredito Final

### System prompt v4.2.0 e **MUITO BOM** (4.39/5)

**Nao precisa de refactor urgente**. Funciona, e seguro, segue best practices em 10 de 13 dimensoes.

**Gaps priorizados para proximo ciclo**:
1. **Q2 M1** — Constitutional hierarchy explicita (P1)
2. **Q4 E5** — Self-check pre-return em R2 (P1)
3. **Q8 F4** — R10 Erros Transientes (P1)
4. **CG2** — Odoo como fonte canonica (P1)

**Gaps menores opcional**:
5. Q1 few-shot (P2, ROI baixo em Claude 4.6)
6. Q6 padronizar tags (P2, 15 min)
7. Q3 parallel tool calls (P2)
8. CG1/CG5/CG6 (P2)

**Nao fazer**:
- Dial back "SEMPRE/NUNCA/OBRIGATORIO" — confirmado PM-2.1 (audit R1)
- Remover `<why>` blocks — sao ponto forte
- Adicionar tool descriptions MCP inline — conforme D3

---

## Proxima Revisao

Sugestao: re-avaliar quando:
- `system_prompt.md` for editado (qualquer change material)
- `claude-agent-sdk >= 0.2.0` for lancado
- Golden dataset pass rate cair > 5%
- Trimestralmente (proxima: 2026-07)

---

## Appendix A: Metodologia

**Ferramentas**:
- Leitura completa do `system_prompt.md` v4.2.0 (linhas 1-407)
- Rubrica: secoes A-M de `STUDY_PROMPT_ENGINEERING_2026.md`
- Cross-reference: `app/agente/CLAUDE.md` secao "Arquitetura de Prompts"
- Comparacao com leaked Opus 4.6 estrutura (via STUDY)
- Audit complementar aos findings de R1 (117 ocorrencias classificadas)

**Limitacoes**:
- Avaliacao baseada em **analise textual** do prompt, nao em golden dataset empirico
- Score subjetivo (1-5 por dimensao) com justificativa mas sem validacao quantitativa
- Nao testei adversarialmente (R9 do ROADMAP faz isso)
- Nao medi latencia/custo antes/depois de mudancas propostas

**Confianca nos findings**:
- Alta em: presenca/ausencia de elementos (Q1 few-shot, Q2 L1-L4, Q3 parallel)
- Media em: priorizacao (depende de metas de produto)
- Baixa em: estimativas de token savings (precisa executar tokenizer)

---

## Appendix B: Fontes

- `app/agente/prompts/system_prompt.md` v4.2.0 (auditado)
- `app/agente/CLAUDE.md` (arquitetura de prompts v3)
- [STUDY_PROMPT_ENGINEERING_2026.md](STUDY_PROMPT_ENGINEERING_2026.md) (rubrica A-M)
- [Anthropic Claude 4.6 best practices](https://platform.claude.com/docs/en/docs/build-with-claude/prompt-engineering/claude-4-best-practices)
- `.claude/references/AGENT_TEMPLATES.md` (cross-ref para constitutional hierarchy)
- `.claude/references/MEMORY_PROTOCOL.md` (cross-ref para R0)
- `.claude/references/REGRAS_OUTPUT.md` (cross-ref para I5/I6)
