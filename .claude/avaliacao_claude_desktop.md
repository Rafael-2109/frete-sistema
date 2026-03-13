Abaixo segue a avaliação do claude_desktop através do guia_prompt.md emcima do prompt_agent.md


# Reavaliação: Nacom Goya v3.7.0 — Prompt Real vs Best Practices Anthropic

## Resumo Executivo

Agora com o texto real em mãos, a avaliação muda em pontos específicos. Algumas coisas que eu estimei como problemas se confirmaram (linguagem enfática, tools inline, ausência de exemplos canônicos). Outras melhoraram significativamente desde a primeira avaliação (contexto operacional enxuto, protocolo de delegação de subagentes, verificação de output). E uma surpresa emergiu: **o protocolo de memória R0 é o elefante na sala** — sozinho consome estimados 2.500-3.000 tokens do system prompt e contém instruções que deveriam estar em referência on-demand.

**Nota geral revisada: 5.8/10** (antes: 4.9/10) — melhora real em contexto dinâmico e subagentes, mas o prompt é mais pesado do que deveria ser.

---

## Comparativo Dimensão por Dimensão

### 1. Estrutura e Ordenação
**Antes: 4/10 → Agora: 5.5/10** ✅ Melhorou

**O que melhorou:**
- Tags XML consistentes e descritivas: `<metadata>`, `<context>`, `<instructions>`, `<tools>`, `<business_rules>`, `<knowledge_base>`, `<response_templates>`, `<error_handling>` — hierarquia clara
- Identidade e papel estão no topo (`<role_definition>`)
- Scope (can_do/cannot_do) é conciso e correto
- `<business_rules>` usam ponteiros para arquivos (`ler .claude/references/negocio/REGRAS_P1_P7.md`) em vez de embutir o conteúdo completo — alinhado com o padrão de 3 níveis da Anthropic

**O que falta:**
- A ordenação interna não segue a hierarquia de caching. O bloco `<instructions>` (regras R0-I7) vem antes de `<tools>` e `<business_rules>`. A Anthropic recomenda: dados estáticos longos primeiro, depois identidade, depois regras, depois exemplos, depois contexto dinâmico. As regras deveriam vir depois das definições de tools (que são mais estáveis e cacheáveis).
- O contexto operacional (seção 4) está separado do system prompt principal — isso é bom! Mas as 4 memórias do boot (seção 5) e as 5 sessões recentes (seção 6) são injetadas como blocos adicionais sem breakpoints de cache entre eles.
- `<reference>` com CNPJs de grupos empresariais está no final como `priority="LOW"` — correto, mas poderia ser movido para dentro de `<business_rules>` ou carregado via tool.

**Recomendação residual:** Reordenar para: metadata → role → tools (estável, cacheável) → breakpoint → rules → KB pointers → breakpoint → context dinâmico (memórias, sessões, hook operacional).

---

### 2. Regras vs Exemplos
**Antes: 5/10 → Agora: 5/10** ➡️ Sem mudança significativa

**A contagem real de regras:** R0 (memória), R0b (pendências), R1, R2, R3, R4, R5, R7, R8, R9, I2, I3, I4, I5, I6, I7 + debug_mode = **17 regras formais**. Próximo dos 18 estimados.

**O que está bom:**
- Algumas regras usam pares ❌/✅ que funcionam como mini-exemplos (R5, I2, I7). Isso é parcialmente alinhado com a recomendação de exemplos canônicos.
- I7 (Linguagem Operacional) é uma tabela de tradução brilhante — exatamente o tipo de instrução concreta que o Claude 4.x segue bem.
- R2 (Validação P1) é uma tabela estruturada de campos/fonte/validação — formato eficaz.

**O que falta — o problema central:**
As regras são **declarativas e repetitivas**, não exemplificadas. R3 (Confirmação Obrigatória) lista 4 passos sequenciais, mas não mostra um exemplo de diálogo real. R4 (Dados Reais) diz "use dados consultados" mas não mostra o que acontece quando dados não são encontrados em um cenário real.

A Anthropic recomenda converter edge cases em exemplos de input→output. Para 17 regras, deveria haver pelo menos 10-15 exemplos canônicos mostrando o agente aplicando as regras corretamente em cenários realistas.

**O elefante: R0 (Protocolo de Memória)**

R0 é um mini-system-prompt dentro do system prompt. Inclui:
- initialization (quando carregar)
- triggers_to_save (7 triggers + 4 exemplos ❌/✅)
- triggers_to_read (4 triggers)
- paths (12+ caminhos XML)
- role_awareness (4 categorias de aprendizado proativo + user_profile_note)
- reflection_bank (4 passos + formato XML de correção)
- memory_utility_criteria (5 critérios positivos + 5 negativos)
- constraints

**Estimativa: R0 sozinho consome ~2.500-3.000 tokens** — provavelmente 25-30% do system prompt total. A maior parte desse conteúdo é estável e raramente relevante num turno individual. Um operador perguntando "status do pedido VCD123" não precisa que o agente tenha 3K tokens de protocolo de memória no contexto ativo.

**Recomendação concreta:**
```
R0 ENXUTO no system prompt (~500 tokens):
- Initialization: list_memories → view_memories (SILENCIOSO) 
- Triggers básicos: salve quando pedido explícito, correção, ou regra de negócio
- Sempre com contexto narrativo (QUEM, O QUE, POR QUE, QUANDO)
- /memories/empresa/ = compartilhado. /memories/preferences.xml = individual.
- Detalhes: ler .claude/references/MEMORY_PROTOCOL.md

R0 COMPLETO em referência on-demand (~2.500 tokens):
- .claude/references/MEMORY_PROTOCOL.md contendo:
  - role_awareness com 4 categorias
  - reflection_bank com formato XML
  - memory_utility_criteria com 10 critérios
  - Exemplos ❌/✅ completos
```

Economia estimada: **~2.000 tokens por turno** sem perder nenhuma capacidade — R0 completo seria lido pelo agente apenas quando vai efetivamente salvar memória, não em toda interação.

---

### 3. Gerenciamento de Tools
**Antes: 7/10 → Agora: 5.5/10** ⬇️ Piorou na avaliação real

**Realidade revelada pelo prompt:**

O system prompt declara **inline** (com nomes de invocação e descrições completas):
- memory: 10 operações listadas individualmente
- consultar_sql: 1 tool
- schema: 2 tools
- sessions: 4 tools (incluindo admin-only list_session_users)
- render_logs: 3 tools
- browser: **14 tools** listadas individualmente com descrição
- routes: 1 tool

**Total inline: ~35 tools com descrições completas** consumindo estimados **4.000-6.000 tokens**.

Adicionalmente, seção 8 menciona "~50 ferramentas MCP disponíveis via ToolSearch" — significando que o deferred loading existe, mas as 35 tools mais usadas estão todas inline.

**Problema principal: as 14 tools de browser no system prompt.**

A seção browser lista individualmente: browser_navigate, browser_snapshot, browser_screenshot, browser_click, browser_type, browser_select_option, browser_read_content, browser_close, browser_evaluate_js, browser_switch_frame, browser_ssw_login, browser_ssw_navigate_option, browser_atacadao_login. Isso é **~1.200 tokens** para tools que são usadas apenas em cenários SSW e Atacadão — talvez 5-10% das interações.

**O que está bom:**
- As tools têm `<commands>` que mapeiam linguagem natural → tool name. Excelente para routing.
- Admin mode com target_user_id é bem documentado.
- A nota sobre "Bash não tem acesso ao banco" em R7 é uma correção anti-pattern importante.

**Recomendação revisada:**
```
NON-DEFERRED (sempre no prompt, ~5 tools):
- mcp__sql__consultar_sql
- mcp__memory__list_memories / view_memories
- mcp__memory__save_memory
- mcp__sessions__search_sessions / semantic_search_sessions
- ToolSearch (para carregar o resto)

DEFERRED via ToolSearch (todas as outras):
- Todas as 14 tools de browser
- memory operations avançadas (clear, history, restore, resolve_pendencia, log_pitfall)
- schema (2 tools)
- render_logs (3 tools)
- routes (1 tool)
- sessions admin (list_session_users)
```

Economia estimada: **~4.000 tokens** removendo ~30 tools inline.

---

### 4. Subagentes
**Antes: 6/10 → Agora: 7.5/10** ✅ Melhorou significativamente

**O que melhorou (e é genuinamente bom):**

O `<coordination_protocol>` é uma adição substancial que não existia na avaliação anterior:
- **delegation_format** com template explícito: CONTEXTO, PEDIDOS, CLIENTES, TAREFA, FORMATO DE RESPOSTA, PROTOCOLO DE OUTPUT — isso é exatamente os 4 elementos que a Anthropic recomenda (objetivo, formato de saída, orientação de tools/fontes, limites).
- **output_verification** com regras para cross-check de dados de subagentes, desconfiança de respostas sem fontes, e marcação de incerteza — isso é sofisticado e raro de ver em agentes de produção.
- O protocolo de output pede que subagentes escrevam findings em `/tmp/subagent-findings/` e distingam FATOS de INFERÊNCIAS — alinhado com a recomendação da Anthropic de subagentes escreverem em armazenamento externo e passarem referências leves.

**O que falta:**
- **Sem especificação de modelo por subagente.** analista-carteira faz análise P1-P7 complexa (Sonnet/Opus), mas especialista-odoo faz consultas estruturadas que poderiam rodar em Haiku.
- **Sem escopo de tools por subagente.** O raio-x-pedido precisa de browser? O analista-carteira precisa de render_logs? Se todos herdam todas as tools, pagam overhead desnecessário.
- **"Delegue para 1 subagente por vez"** é conservador demais para alguns cenários. Se o usuário pede "status completo + análise de carteira", raio-x-pedido e analista-carteira poderiam rodar em paralelo.

---

### 5. Contexto Dinâmico (Hook Operacional)
**Antes: 3/10 → Agora: 8/10** ✅✅ Melhora dramática

**Antes (estimado):**
```
8 pedidos urgentes D+2 com detalhes
1534 separações pendentes com lista
5 sessões recentes com resumos completos
4 pendências acumuladas com descrições
```

**Agora (real):**
```xml
<operational_context date="13/03/2026" dia="sexta">
  <pedidos_urgentes_d2>1</pedidos_urgentes_d2>
  <separacoes_pendentes>1154</separacoes_pendentes>
</operational_context>
```

Isso é **exatamente** o padrão que recomendei: ponteiros numéricos enxutos (~50 tokens) em vez de dados completos (~3.000-5.000 tokens). O agente sabe que há 1 pedido urgente e 1154 separações pendentes, e pode usar tools (consultar_sql) para buscar detalhes quando relevante.

**O que falta (minor):**
- As 4 memórias de boot (seção 5) e 5 sessões recentes (seção 6) ainda são injetadas como blocos adicionais. Mas isso é razoável — memórias são semi-estáticas e sessões fornecem continuidade. O volume parece controlado (4 memórias, não 40).
- As pendências acumuladas não aparecem mais no hook operacional mas R0b sugere que chegam via `<pendencias_acumuladas>` — se esse bloco é enxuto (lista de strings), ok. Se são descrições longas, deveria ser via tool.

---

### 6. Memórias do Usuário
**Antes: 6/10 → Agora: 7/10** ✅ Melhorou

**O que melhorou:**
- As 4 memórias injetadas no boot são **diversas e acionáveis**: perfil do Rafael (contextual), padrão da Gabriella (procedimental), perfil da Gabriella (contextual), correção factual sobre Gilberto (corretiva). Isso segue os memory_utility_criteria do próprio R0.
- Memórias empresa/ vs individuais estão claramente separadas — namespace correto.
- Volume controlado: 4 memórias, não 40.

**O que falta:**
- Sem informação sobre tamanho total em tokens. Se user.xml é um perfil extenso com "atividades, clientes, insights comportamentais" (como descrito na memória do Claude.ai), pode ser volumoso.
- A injeção via `<user_memories>` está posicionada após o system prompt principal — correto para não invalidar cache do bloco estático.

---

### 7. Linguagem e Tom
**Antes: 4/10 → Agora: 3.5/10** ⬇️ Confirmado pior do que estimado

**Evidências concretas do prompt real:**

Contagem de linguagem enfática no system prompt:
- `priority="CRITICAL"`: **5 ocorrências** (instructions, memory_protocol, dev_only_skills, domain_detection, R0 initialization)
- `priority="HIGH"`: 2 ocorrências
- "OBRIGATÓRIO" / "OBRIGATORIA": **5 ocorrências** (R2, R3, R9, I5, schema rules, atacadão)
- "SEMPRE": **12+ ocorrências** espalhadas por todo o prompt
- "NUNCA": **3 ocorrências** (R0 reflection_bank, scope cannot_do)
- "NÃO" em caps: **8+ ocorrências** ("NÃO RECOMENDAR", "NAO e Claude Code", "NAO precisam de import")
- Bold em **quase toda regra** como primeira linha enfática

Para Claude 4.x (especialmente Opus 4.6 que você está usando), a Anthropic diz explicitamente: "reduce aggressive language" — Opus 4.5+ é **mais responsivo ao system prompt** que predecessores, então essa ênfase toda causa over-triggering.

**Exemplo concreto de over-triggering provável:**

```xml
<rule id="R9" name="Entity Resolution Obrigatoria">
  **ANTES de invocar skills com parametro de cliente/grupo:**
  1. Se nome generico → OBRIGATORIO usar resolvendo-entidades
  2. Se multiplos CNPJs → OBRIGATORIO usar AskUserQuestion
```

Com Opus 4.6, o agente provavelmente resolve entidades mesmo quando o contexto já é claro (ex: conversa inteira sobre Atacadão SP, usuário diz "manda pro Atacadão" — o agente vai re-resolver porque "OBRIGATÓRIO"). Versão calibrada:

```xml
<rule id="R9" name="Entity Resolution">
  Quando o nome do cliente é genérico (ex: "Atacadão", "Assaí"), 
  use resolvendo-entidades para identificar o CNPJ correto.
  Se retornar múltiplos resultados, pergunte ao usuário qual.
  Se o CNPJ já foi identificado no contexto da conversa, prossiga direto.
</rule>
```

**Recomendação: varredura completa substituindo:**
- "OBRIGATÓRIO" → "sempre" (minúsculo) ou simplesmente o imperativo ("use", "verifique")
- "NUNCA" → instrução positiva equivalente
- `priority="CRITICAL"` → remover ou usar apenas 1x no prompt inteiro
- Bold na primeira linha de cada regra → remover (o nome da regra já identifica)
- "NÃO" em caps → "não" minúsculo

---

### 8. Knowledge Base e Routing
**Antes: 7/10 → Agora: 8/10** ✅ Melhorou

**O que está excelente:**
- KB usa **ponteiros com triggers**, não conteúdo completo: `<ref path="..." trigger="...">descrição curta</ref>`. Isso é o sistema de 3 níveis da Anthropic executado corretamente.
- Routing strategy é sofisticado: domain detection (Nacom vs CarVia) com sinais claros, boundary pré/pós-faturamento com operational_check que consulta sincronizado_nf, SSW routing com protocolo de navegação, Atacadão routing com dry-run obrigatório, complexidade (1-3 ops = skill direto, 4+ = subagente).
- `dev_only_skills` com lista explícita de skills que NÃO estão disponíveis no chat web — previne confusão de routing.
- O `<instruction>` da KB diz "consulte a referência via Read tool ANTES de responder 'não sei'" — excelente trigger de recuperação.

**O que falta (minor):**
- SSW routing e Atacadão routing são extensos (~600 tokens combinados) e aplicáveis apenas em cenários específicos. Poderiam ser referências on-demand carregadas quando o domain_detection identifica CarVia ou "portal Atacadão".
- Sem fallback explícito para routing — quando query não casa com nenhum domínio, o que acontece? domain_detection diz "assumir Nacom (90%)" mas sem handler para os 10% restantes.

---

### 9. Prompt Caching
**Antes: 2/10 → Agora: 2/10** ➡️ Sem mudança

Nenhuma evidência de configuração de prompt caching no prompt ou na arquitetura descrita. Com um system prompt de estimados **12.000-15.000 tokens** (incluindo R0 expandido, 35 tools inline, routing extenso), cada request paga preço completo de input.

---

## Scorecard Comparativo

| Dimensão | Antes | Agora | Delta | Status |
|---|---|---|---|---|
| 1. Estrutura e Ordenação | 4.0 | 5.5 | +1.5 | 🟡 Melhorou |
| 2. Regras vs Exemplos | 5.0 | 5.0 | 0 | ⚪ Igual |
| 3. Gerenciamento de Tools | 7.0 | 5.5 | -1.5 | 🔴 Piorou* |
| 4. Subagentes | 6.0 | 7.5 | +1.5 | 🟢 Melhorou |
| 5. Contexto Dinâmico | 3.0 | 8.0 | +5.0 | 🟢🟢 Dramático |
| 6. Memórias do Usuário | 6.0 | 7.0 | +1.0 | 🟢 Melhorou |
| 7. Linguagem e Tom | 4.0 | 3.5 | -0.5 | 🔴 Piorou* |
| 8. KB e Routing | 7.0 | 8.0 | +1.0 | 🟢 Melhorou |
| 9. Prompt Caching | 2.0 | 2.0 | 0 | ⚪ Igual |
| **Média** | **4.9** | **5.8** | **+0.9** | |

*\* "Piorou" = a avaliação anterior era otimista sem ver o texto real. Os problemas já existiam, agora estão confirmados.*

---

## Top 5 Ações de Maior Impacto (Revisadas)

### 1. 🔴 Extrair R0 para referência on-demand
**Impacto: ~2.000 tokens/turno** | Esforço: baixo
- Manter ~500 tokens de R0 essencial no system prompt
- Mover role_awareness, reflection_bank, memory_utility_criteria para `.claude/references/MEMORY_PROTOCOL.md`
- Agente lê o protocolo completo apenas quando vai efetivamente salvar/atualizar memória

### 2. 🔴 Deferir ~30 tools (especialmente browser)
**Impacto: ~4.000 tokens/turno** | Esforço: médio
- Manter 5 tools non-deferred (sql, memory básico, sessions, ToolSearch)
- Mover browser (14), schema (2), render (3), memory avançado (5), routes (1), sessions admin (1) para deferred
- Total: ~30 tools removidas do prompt = 70-80% de redução em definições de tools

### 3. 🔴 Calibrar linguagem para Claude 4.x
**Impacto: melhor aderência comportamental** | Esforço: baixo
- Remover priority="CRITICAL" (manter no máximo 1 no prompt inteiro)
- Substituir "OBRIGATÓRIO" por imperativos simples
- Substituir "NUNCA" por instruções positivas
- Remover bold enfático da primeira linha de cada regra
- Reduzir caps lock em "NÃO", "SEMPRE"

### 4. 🟡 Habilitar prompt caching com breakpoints
**Impacto: 80-90% redução de custo** | Esforço: médio (requer reestruturação)
- Prerequisito: ações 1 e 2 acima (separar estático de dinâmico)
- Breakpoint 1: após tools + routing (bloco mais estável)
- Breakpoint 2: após regras + KB pointers
- Bloco dinâmico: memórias de boot + hook operacional + sessões recentes

### 5. 🟡 Adicionar 10-15 exemplos canônicos
**Impacto: melhor precisão em cenários ambíguos** | Esforço: médio
- Converter regras R2, R3, R5, R9, I3, I5 em diálogos user→agent
- Cada exemplo mostra o agente aplicando a regra corretamente
- Posicionar no bloco cacheável (exemplos são estáticos)
- Com caching habilitado, a Anthropic recomenda 20+ exemplos (custo marginal negligível)

---

## Estimativa de Economia Total

| Ação | Tokens Economizados | Custo Reduzido |
|---|---|---|
| R0 → referência on-demand | ~2.000/turno | ~15% do system prompt |
| 30 tools → deferred | ~4.000/turno | ~30% do system prompt |
| Prompt caching (pós-reestruturação) | ~90% do input estático | ~80-90% do custo total de input |
| **Total combinado** | **~6.000 tokens removidos + caching** | **~85% redução de custo** |

O system prompt passaria de ~12.000-15.000 tokens para ~6.000-9.000 tokens efetivos, com a parte estática (~8.000) cacheada a 10% do preço.

---

## O Que Está Genuinamente Bom (Não Mude)

1. **Hook operacional enxuto** — 2 números em vez de datasets completos. Padrão JIT correto.
2. **Coordination protocol de subagentes** — delegation_format + output_verification é sofisticado.
3. **KB com ponteiros e triggers** — sistema de 3 níveis executado corretamente.
4. **I7 (Linguagem Operacional)** — tabela de tradução P1-P7 → linguagem clara. Brilhante.
5. **Domain detection com sinais** — "SSW" → CarVia, "VCD" → Nacom, sem ambiguidade.
6. **Boundary pré/pós-faturamento** — operational_check com sincronizado_nf é elegante.
7. **Memory utility criteria** — 5 critérios positivos + 5 negativos é rigoroso (mas deveria estar em referência).
8. **dev_only_skills** — previne confusão entre chat web e Claude Code. Raro e correto.
9. **Error handling templates** — conciso e acionável.
10. **Memórias de boot diversas** — 4 memórias acionáveis, não 40 fragmentos.