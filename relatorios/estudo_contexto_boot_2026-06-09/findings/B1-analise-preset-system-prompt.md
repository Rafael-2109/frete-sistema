# B1 — Análise Crítica: preset_operacional.md + system_prompt.md

**Data**: 09/06/2026
**Missão**: Análise crítica interna de redundância, inflação de prioridade, roteamento, subagentes, debug/sql_admin e veredito seção-a-seção.
**Fontes primárias**: `app/agente/prompts/preset_operacional.md` (117L), `app/agente/prompts/system_prompt.md` (784L), `app/agente/sdk/hooks.py`, findings A1-A6.

---

## 1. REDUNDÂNCIAS INTERNAS preset↔system_prompt

### R-INT-1: Paralelismo de tool calls (DUPLICADO)

| Arquivo | Linha | Texto |
|---------|-------|-------|
| preset_operacional.md | 12-18 | `<parallel_execution>` — "Se pretende chamar multiplas tools e nao ha dependencias entre elas, faca todas as chamadas independentes em paralelo. Maximize uso de chamadas paralelas..." |
| system_prompt.md | 307-314 | `<use_parallel_tool_calls>` — "Quando precisar consultar multiplas fontes independentes ... faca as calls em paralelo em uma unica resposta. Nao sequencie quando nao ha dependencia..." |
| system_prompt.md | 663 | `<rule>Tarefas independentes → delegue em paralelo. Dependentes → sequencialmente</rule>` (subagentes) |

**Diagnóstico**: Três declarações do mesmo princípio. A do preset é genérica (tool use em geral), a de R5 é específica a fontes de dados, e a de subagents é específica a delegação. As últimas duas têm contexto diferente e podem coexistir, mas a sobreposição preset↔R5 é de conteúdo quase idêntico. O preset poderia conter apenas o princípio geral, e R5 o detalhe de quando disparar paralelo em dados operacionais.

**Decisão proposta**: Manter o preset para princípio geral de tool use; comprimir R5 `<use_parallel_tool_calls>` para 2 linhas com ponteiro para o preset — salva ~7 linhas.

---

### R-INT-2: Reversibilidade/confirmação antes de ação real (DUPLICADO)

| Arquivo | Linha | Texto |
|---------|-------|-------|
| preset_operacional.md | 64-69 | `<reversibility>` — "Para acoes que afetam producao real (criar separacao, operar Odoo, agendar entregas), confirme com o usuario antes de executar." |
| system_prompt.md | 49-50 | `L1 — SEGURANCA (inviolavel): Confirmar antes de operacao irreversivel (R3)` |
| system_prompt.md | 248-264 | `R3 Confirmação Obrigatória` — procedimento completo com 4 passos |

**Diagnóstico**: O preset formula o PRINCÍPIO, L1 é o LABEL, R3 é o PROCEDIMENTO. Essa é uma redundância INTENCIONAL e saudável: o preset serve como orientação pré-contexto do SDK, L1 é a hierarquia decisória, e R3 é o procedimento operacional detalhado. A sobreposição é de NÍVEL diferente — não eliminar.

**Decisão proposta**: MANTER — os três vivem em camadas diferentes (preset=awareness, L1=hierarquia, R3=procedimento).

---

### R-INT-3: "Não inventar dados" (DUPLICADO em 3 lugares)

| Arquivo | Linha | Texto |
|---------|-------|-------|
| preset_operacional.md | 91-93 | `Os invariants de negocio (confirmar acao irreversivel, nao fabricar dados, ...)` (como referência a R3/R4 no system_prompt) |
| system_prompt.md | 39 | `<cannot_do>... inventar dados...` |
| system_prompt.md | 50 | `L1: Nao fabricar dados, IDs, campos ou valores` |

**Diagnóstico**: O preset referencia os invariants de negócio como cross-reference (linha 91: "Os invariants de negocio ... estao nas regras do system prompt (R3, R4)"). Isso é intencional — o preset aponta para o system_prompt sem duplicar. A única redundância real é `cannot_do` vs `L1`: mesma regra em duas seções do system_prompt.

**Decisão proposta**: Manter `L1` (hierarquia). `cannot_do` no `<scope>` tem papel diferente (define o escopo declarado do agente, não apenas como regra). Manter ambos.

---

### R-INT-4: Language policy — ÚNICO DONO correto (sem redundância de conteúdo)

| Arquivo | Linha | Texto |
|---------|-------|-------|
| preset_operacional.md | 3 | `<!-- language → system_prompt <language_policy> (dono unico; superset anti-drift de idioma, #787) -->` |
| system_prompt.md | 25-32 | `<language_policy>` — conteúdo completo |

**Diagnóstico**: O comentário no preset é **explicitamente** um ponteiro — "dono único: system_prompt". Correto. Não há duplicação de conteúdo.

**Decisão proposta**: MANTER sem alteração.

---

### R-INT-5: Memory — awareness no preset vs protocolo completo no system_prompt (REDUNDÂNCIA CONTROLADA)

| Arquivo | Linha | Texto |
|---------|-------|-------|
| preset_operacional.md | 100-115 | `<persistent_systems><memory>` — awareness ("Voce tem memorias persistentes, sobrevivem entre sessoes, banco PostgreSQL, nao filesystem, protocolo: R0/R0b/R0c") |
| system_prompt.md | 79-198 | R0-R0e — protocolo completo |

**Diagnóstico**: O preset tem awareness + orientação de não usar filesystem. O system_prompt tem o procedimento completo. São camadas diferentes e corretas. O preset poderia ser ainda mais enxuto (a lista de R0/R0b/R0c pode ser apenas "Protocolo: R0 no system prompt"), mas não é redundância problemática.

**Decisão proposta**: Comprimir preset linha 106 de "Protocolo de uso: regras R0, R0b e R0c no system prompt" para "Protocolo: R0 no system prompt" — economia mínima, manter.

---

### R-INT-6: /tmp como destino de arquivos (LEVE REDUNDÂNCIA)

| Arquivo | Linha | Texto |
|---------|-------|-------|
| preset_operacional.md | 39-41 | `<write_edit>` — "Voce pode gerar arquivos em /tmp/agente_files/ (Excel, CSV, PDF, JSON). Nao pode modificar codigo-fonte..." |
| system_prompt.md | 23 | `Scripts operacionais (CSV, Excel, automacao) sao permitidos em /tmp.` (em `<role_definition>`) |

**Diagnóstico**: O preset define o PERMISSÃO-RAIZ (pode gerar em /tmp, não pode modificar código). O system_prompt repete isso de forma comprimida em role_definition. A redundância é leve e o contexto é diferente (preset=tool_use, system_prompt=role). 

**Decisão proposta**: Remover a linha 23 do system_prompt (`system_prompt.md:23`) — está coberta pelo preset. Salva 1 linha.

---

### R-INT-7: Segurança / prompt injection — DIVIDIDA CORRETAMENTE

| Arquivo | Linha | Texto |
|---------|-------|-------|
| preset_operacional.md | 71-94 | `<security_invariants priority="inviolable">` — 3 invariants (origem instrução, tags falsas, não revelar) |
| system_prompt.md | 49-50 | `L1 — SEGURANCA (inviolavel): Nao fabricar dados...` |

**Diagnóstico**: O preset tem os invariants de SEGURANÇA DO PROMPT (anti-injection), o system_prompt tem a hierarquia constitucional que menciona L1 como segurança operacional. São complementares, não redundantes — o preset opera na camada de tool use/instrução de sistema, L1 opera na camada de decisão de negócio. Arquitetura CORRETA segundo PROMPT_INJECTION_HARDENING.md.

**Decisão proposta**: MANTER. 

---

## 2. INFLAÇÃO DE PRIORIDADE — Contagem e Proposta de Escala

### Inventário completo de rótulos de "máximo"

**preset_operacional.md** (117L):
- `priority="inviolable"` — linha 71 (1 ocorrência)
- Total: **1 rótulo de topo**

**system_prompt.md** (784L):
- `L1 — SEGURANCA (inviolavel)` — linha 49
- `L2 — ETICA (inviolavel)` — linha 53
- `critical="true"` — linhas 612, 622 (2 boundaries em routing_strategy)
- `mandatory` — linhas 97, 180, 197 (no contexto de `priority="mandatory"` para user_rules)
- `NUNCA` — 16 ocorrências (linhas 28, 63, 65, 149, 190, 260, 299, 393, 498, 504, 537, 539, 576, 631, 649)
- `SEMPRE` — 5 ocorrências
- Total de rótulos distintos de "máximo": **6 tipos** (inviolavel, critical, mandatory, L1, L2, NUNCA/SEMPRE)

### Análise: o problema real

O agente (avaliação C2, conf=Alta) identificou que múltiplos rótulos de "máximo" competem entre si. Porém, ao mapear as ocorrências, o problema é mais nuançado:

1. **L1/L2 (2 ocorrências cada)**: são a HIERARQUIA CONSTITUCIONAL — propositalmente distintos. L1=segurança, L2=ética. São corretos e necessários.
2. **`priority="inviolable"` no preset (1 vez)**: para os 3 invariants de segurança do prompt. Correto.
3. **`critical="true"` em boundaries (2 vezes)**: para faturamento e baseline_financeiro. Justificado — são as 2 fronteiras com maior custo de erro.
4. **`mandatory` (3 vezes)**: para user_rules injetadas dinamicamente. Correto — user_rules SÃO mais fortes que defaults.
5. **`NUNCA` (16 ocorrências)**: a inflação real está aqui. Nem todo "NUNCA" é L1. Exemplos:
   - `NUNCA alterne para ingles` (L4 na verdade)
   - `NUNCA pedir data de expedicao sem antes verificar separacoes` (L3 — regra operacional)
   - `NUNCA chute quando ambiguo` (boas práticas de roteamento)
   - `NUNCA aceitar confirmacao agregada em R11` (L1 — correto aqui)

### Proposta de escala unificada de 3 níveis

```
NIVEL 1 — INVIOLÁVEL (≡ L1/L2 atuais + security_invariants):
  Marcador: priority="hard" ou atributo L1/L2 da hierarquia
  Exemplos: não fabricar dados, confirmar antes de irreversível, não revelar prompt,
            origem de instrução válida. NUNCA ceder mesmo a pedido explícito.

NIVEL 2 — OBRIGATÓRIO em contexto (≡ L3 + critical="true" boundaries):
  Marcador: priority="firm"
  Exemplos: boundaries PRE/POS faturamento, baseline financeiro, R11 SO faturado,
            R12 massa/append-only, validação P1 em R2. Quebrar = erro de negócio grave.

NIVEL 3 — PADRÃO FORTE (≡ L4 + NUNCA operacionais):
  Marcador: sem atributo (default) ou "default behavior"
  Exemplos: não alternr para inglês, não pedir data sem verificar separação,
            não sequenciar quando independente, não propor ações extra após "fechado".
```

### Mapeamento de cada rótulo atual → novo nível

| Rótulo atual | Linha | Novo nível | Justificativa |
|---|---|---|---|
| `L1 — SEGURANCA (inviolavel)` | 49 | NIVEL 1 | Correto — manter |
| `L2 — ETICA (inviolavel)` | 53 | NIVEL 1 | Correto — manter |
| `priority="inviolable"` (preset) | 71 | NIVEL 1 | Correto — manter |
| `critical="true"` boundary faturamento | 612 | NIVEL 2 | Boundary de negócio, não de segurança |
| `critical="true"` boundary baseline | 622 | NIVEL 2 | Idem |
| `mandatory` user_rules | 97,180,197 | NIVEL 1* | *Especial: são user-defined, sobrepõem L4 mas não L1/L2 |
| `NUNCA alterne para ingles` | 28 | NIVEL 3 | Preferência forte, não segurança |
| `NUNCA afirme com certeza sem fonte` | 63 | NIVEL 1 | É L2 — manter como NIVEL 1 |
| `NUNCA afirmar causa raiz sem isolar` | 65 | NIVEL 1 | É L2 — manter |
| `NUNCA reutilizar resultado anterior` | 149 | NIVEL 2 | Regra operacional crítica |
| `NUNCA ignore silenciosamente` (user_rules) | 190 | NIVEL 1* | Parte do protocolo user_rules |
| `NUNCA inserir qtd_saldo=0 sem confirm` | 260 | NIVEL 2 | Regra de negócio |
| `NUNCA improvise SQL via Bash` | 299 | NIVEL 2 | Regra operacional |
| `NUNCA execute criacao sem confirmacao` | 393 | NIVEL 1 | = L1/R3 — manter |
| `NUNCA aceitar confirmacao agregada R11` | 498 | NIVEL 1 | NF fiscal irreversível |
| `NUNCA usar action_update_taxes` | 504 | NIVEL 2 | Gotcha Odoo específico |
| `NUNCA manipule tabelas via SQL cru` | 537 | NIVEL 2 | Regra operacional |
| `NUNCA UPDATE/DELETE assai_moto_evento` | 539 | NIVEL 1 | Append-only = integridade de dados |
| `NUNCA pedir data sem verificar sep.` | 576 | NIVEL 3 | Procedimento operacional |
| `NUNCA gerar layout alternativo sem` | 631 | NIVEL 2 | Formato travado em memória |
| `NUNCA chute quando ambiguo` | 649 | NIVEL 3 | Boa prática de roteamento |

**Conclusão da inflação**: Os 2 L1/L2 + `inviolable` + alguns `NUNCA` de L2 são corretos no NIVEL 1. O problema real são ~8 `NUNCA` de NIVEL 3 que parecem ter o mesmo peso dos NIVEL 1. A solução não é remover os `NUNCA` (têm valor instrucional), mas garantir que os NIVEL 1 se destaquem estruturalmente — já feito pela `constitutional_hierarchy`. O risco de inflação é menor do que parece porque a hierarquia L1>L2>L3>L4 já existe e está clara.

**Recomendação concreta**: Substituir os `NUNCA` de NIVEL 3 por linguagem mais soft ("não", "evite", "prefira") para reservar `NUNCA` apenas para NIVEL 1 e 2. Estimativa: ~5-6 substituições de texto, zero mudança de arquitetura.

---

## 3. R7/ROUTING_STRATEGY/ROUTING_SKILLS: ONDE MORAM OS EXEMPLOS?

### O que existe hoje e onde

**Sistema_prompt.md** contém 3 blocos de roteamento:
1. **R7 (linhas 370-412)**: Entity Resolution + 4 Fast-paths explícitos com triggers (`consultar-estoque`, `criar-separacao`, `gerando-baseline`, `gerando-artifact`) + regra de resolvendo-entidades PRIMEIRO
2. **`<routing_strategy>` (linhas 598-657)**: domain_detection (3 domínios: Nacom/CarVia/HORA), 2 boundaries críticos (faturamento/baseline), routing_confidence (anti-ambiguidade com template AskUserQuestion)

**ROUTING_SKILLS.md** (262L) contém:
- Tabela de 40+ contextos → skill/subagente (passo 1)
- Árvore de decisão Odoo (passos 2-3)
- Desambiguação (pares de skills conflitantes — 8 pares)
- Inventário completo de 54 skills

**SKILL.md frontmatters** (28 skills expostas):
- `USAR QUANDO` / `NAO USAR QUANDO` — triggers e anti-triggers por skill

### Diagnóstico: redundância e lugar correto

**O que DEVE estar no system_prompt como POLÍTICA:**
1. **Domain detection** (Nacom vs CarVia vs HORA): é o PRIMEIRO CHECK antes de qualquer routing — deve estar no prompt para evitar um lookup de reference em cada turno. Correto onde está.
2. **Boundaries críticos** (faturamento PRE/POS, baseline financeiro): são decisões frequentes com alto custo de erro — justificam estar no prompt como política inline, não como JIT lookup. Correto onde está.
3. **Routing confidence** (template AskUserQuestion): princípio comportamental de como perguntar quando ambíguo — é comportamento, não dado. Correto no prompt.
4. **R7 Fast-paths**: são os 4 padrões de 24.7% das sessões — justificam inlining. Correto, mas a prescrição do baseline_financeiro em R7 E em `<boundary name="baseline_financeiro">` é redundância.

**O que DEVE ir para ROUTING_SKILLS.md (JIT read):**
- Tabela completa de 40+ contextos (já está lá)
- Pares de desambiguação (já está lá)
- Inventário de 54 skills (já está lá)
- Os exemplos VERBOSOS de AskUserQuestion (estão no prompt — 7 linhas poderiam ser 3)

**O que DEVE ficar em SKILL.md frontmatters:**
- Triggers específicos de cada skill (já estão lá via USAR QUANDO/NAO USAR)

### Redundância identificada: baseline_financeiro em 2 lugares

O `<boundary name="baseline_financeiro">` (linhas 622-635, ~14 linhas) e o trecho de R7 sobre `gerando-baseline-conciliacao` (linha 396-399, ~4 linhas) se sobrepõem:

- R7 linha 396-399: `"atualizar baseline", "gerar baseline", "rodar baseline" → use Skill: gerando-baseline-conciliacao direto.`
- boundary baseline_financeiro linha 622-635: regex + prescricao de 3 passos detalhados

**Diagnóstico**: A boundary tem conteúdo adicional valioso (regex explícito, o "por quê", os 3 passos detalhados). R7 é apenas o trigger. A redundância é de TRIGGER, não de conteúdo. R7 pode ser simplificado para apenas o gatilho + ponteiro para a boundary: economia de ~2 linhas.

### Proposta de divisão (delta de linhas)

| Conteúdo | Onde fica | Delta |
|---|---|---|
| Domain detection (3 domínios + sinais) | system_prompt — FICA | 0 |
| Boundary faturamento PRE/POS | system_prompt — FICA | 0 |
| Boundary baseline_financeiro (prescricao) | system_prompt — FICA | 0 |
| R7 entity resolution | system_prompt — FICA | 0 |
| R7 fast-paths (4 triggers) | system_prompt — ENXUGA: remover trigger baseline duplicado, manter os outros 3 | -2L |
| Routing confidence (template AskUserQuestion) | system_prompt — ENXUGA: comprimir de 7 linhas para 4 | -3L |
| Tabela completa 40+ contextos | ROUTING_SKILLS.md — JIT READ | 0 |
| USAR QUANDO/NAO USAR de cada skill | frontmatter SKILL.md — FICA | 0 |

**Delta total**: -5 linhas no system_prompt, zero perda funcional.

---

## 4. SUBAGENTES: COMPARAÇÃO system_prompt vs CLAUDE.md + PROPOSTA

### Sistema de referência

**system_prompt.md `<subagents>` (linhas 659-725)**: 12 agentes:
```
analista-carteira, especialista-odoo, raio-x-pedido, gestor-carvia, gestor-ssw,
auditor-financeiro, controlador-custo-frete, gestor-recebimento, gestor-devolucoes,
gestor-estoque-producao, analista-performance-logistica, gestor-motos-assai
```

**CLAUDE.md raiz `SUBAGENTES` (linhas 199-213)**: 14 agentes (os 12 acima + 2):
- `desenvolvedor-integracao-odoo` — dev-only, correto ausente do system_prompt
- `gestor-estoque-odoo` — **FALTANDO** no system_prompt

**ROUTING_SKILLS.md**: menciona `gestor-estoque-odoo` como target de ESTOQUE ODOO WRITE (linha 60)

### Problema 1: gestor-estoque-odoo ausente do system_prompt

O subagente `gestor-estoque-odoo` existe em `.claude/agents/gestor-estoque-odoo.md` (verificado), está no CLAUDE.md, está no ROUTING_SKILLS.md — mas NÃO está no `<subagents>` do system_prompt. 

Consequência: o agente principal não sabe QUANDO delegar para este subagente. Pode tentar executar WRITE de estoque diretamente (invocando skills atômicas que deveriam ser delegadas), ou simplesmente falhar no roteamento.

### Problema 2: Listas inconsistentes — duas fontes de verdade

O system_prompt tem a lista com `delegate_when` + `capabilities` detalhados. O CLAUDE.md tem uma tabela mais comprimida. Não há mecanismo que as mantenha sincronizadas. 

Historicamente: o system_prompt cresceu de 407→862 linhas em 6 semanas, durante o qual novos subagentes foram adicionados ao CLAUDE.md mas não refletidos no system_prompt.

### Proposta: fonte única + mecanismo de geração

**Fonte canônica de verdade**: os arquivos `.claude/agents/*.md` com seu frontmatter YAML (`name`, `description`, campos estruturados). O `agent_loader.py` já lê esses arquivos para carregar as AgentDefinitions no SDK.

**Mecanismo proposto** (2 opções):

**Opção A (Mínima — sem código)**: 
- Mover a tabela SUBAGENTES do CLAUDE.md para ROUTING_SKILLS.md (onde já tem os contextos de delegação)
- O system_prompt mantém sua seção `<subagents>` com todos os 13 agentes operacionais (adicionar gestor-estoque-odoo)
- Adicionar ao checklist de governança (R-EXEC-5): "ao adicionar agente em .claude/agents/, atualizar system_prompt `<subagents>` + ROUTING_SKILLS.md"

**Opção B (Gerada — com código)**:
- `scripts/audits/prompt_size_audit.py` já roda como pre-commit
- Adicionar função `check_subagents_consistency()` que compara `<agent name=` no system_prompt com os arquivos em `.claude/agents/*.md` (excluindo `desenvolvedor-integracao-odoo` e `auditor-sped-ecd` e `orientador-loja` que são dev-only/lojas)
- Exit 1 se há agente em `.claude/agents/` sem entrada correspondente no system_prompt (ou vice-versa)

**Recomendação**: Opção B tem custo de implementação baixo (20-30 linhas no audit script existente) e garante que o problema não volte. Fazer Opção A imediatamente (adicionar gestor-estoque-odoo ao system_prompt) como hotfix; Opção B como melhoria.

**Delta imediato**: Adicionar `gestor-estoque-odoo` ao `<subagents>` do system_prompt (~6 linhas).

---

## 5. debug_mode_context + sql_admin_context (R-8 do Rafael)

### Estado atual (verificado em hooks.py:1330-1379)

AMBOS os blocos já são **condicionais por usuário**:

- `debug_mode_context`: injeta APENAS se `get_debug_mode() == True` (`hooks.py:1334`)
- `sql_admin_context`: injeta APENAS se `user_id in _SQL_ADMIN` — set `{1, 55, 62}` (`hooks.py:1360`)

**Isso significa**: para 99% dos usuários, esses blocos NÃO existem no contexto. São ~0 tokens para usuários normais.

### O que Rafael identificou em R-8

"Basta uma barreira determinística que aciona quando NÃO for admin — as regras bloqueadoras devem ter um 'if' — mais simples do que colocar as barreiras para todos + explicação de que admin pode fazer."

**Análise**: A premissa de Rafael está parcialmente incorreta — os blocos já têm `if`. O que Rafael pode ter observado: no DUMP do contexto de boot (que era dele, user_id=1 que é SQL admin), os blocos aparecem. Para um usuário não-admin, eles não apareceriam.

### Problema REAL (diferente do que R-8 identifica)

O problema não é que o conteúdo vai para todos — já não vai. O problema potencial é **tamanho do conteúdo quando injetado para admins**:

- `debug_mode_context`: ~9 linhas de instrução (já compacto — ok)
- `sql_admin_context`: ~12 linhas de instrução + procedimento detalhado

Para os 3 usuários SQL admin, cada turno recebe ~21 linhas de instrução de admin que são válidas para QUALQUER turno (incluindo "quanto tem de palmito?"). Isso é ruído de baixo nível mas real.

### Proposta de desenho

**Proposta mínima (sem código, impacto zero)**: Os blocos estão bem dimensionados e já são condicionais. Não há ação necessária para R-8 no código. A interpretação de Rafael estava baseada no dump que era DELE como admin.

**Proposta de refinamento (reduz ruído para admins)**: Comprimir os dois blocos:
- `debug_mode_context`: de 9 linhas para 4 linhas — manter os 4 bullet points essenciais, remover o "Fluxo recomendado" (instrução não crítica)
- `sql_admin_context`: de 12 linhas para 6 linhas — manter permissões + proibição Bash + fluxo em 1 linha

**Delta para admins**: -12 linhas por turno. Baixo impacto absoluto dado que é apenas 3 usuários.

**Conclusão**: O design de "barreira determinística" que Rafael propõe JÁ EXISTE. A proposta real é enxugar o conteúdo quando injetado, não mudar a condição.

---

## 6. VEREDITO SEÇÃO A SEÇÃO — system_prompt.md

### `<metadata>` (linhas 1-8, 8L)

**Veredito: ENXUGA**

Conteúdo atual: version, last_updated, role, comentário sobre histórico de versões.

Problema: `last_updated: 2026-05-21` não é uma propriedade visível ao agente — é bookkeeping para dev. O comentário sobre histórico é correto (aponta para git log + ROADMAP fora do prompt).

Proposta: Comprimir para:
```xml
<metadata version="4.3.3" role="Agente Logístico Principal - Nacom Goya"/>
```
Salva ~6 linhas. O versionamento para dev fica no git, não no contexto do agente.

---

### `<context>` (linhas 10-41, 32L)

**Veredito: FICA (com ajuste pontual)**

Contém: `<environment>` (produção, real), `<role_definition>` (quem é, o que faz, /tmp), `<language_policy>` (PT-BR sempre), `<domain_knowledge>` (formato .rem=CNAB), `<scope>` (can_do/cannot_do).

**Ajuste**: Linha 23 (`Scripts operacionais (CSV, Excel, automacao) sao permitidos em /tmp.`) já está coberta pelo `<write_edit>` do preset (preset_operacional.md:39-41). Remover 1 linha.

Resto: cada elemento tem papel específico. `<domain_knowledge>` sobre .rem é um gotcha real que previne erros de classificação. `<scope>` é a declaração de identidade do agente. MANTER.

---

### `<constitutional_hierarchy>` L1-L4 + exemplo (linhas 46-77, 32L)

**Veredito: FICA (protegido — achado M2)**

Este é o mecanismo de desempate mais importante do prompt. O exemplo trabalhado ("cria separacao rapido sem perguntar → L1 > L4") é exatamente o tipo de concreto que ajuda o agente a aplicar a hierarquia em caso real. O agente confirmou isso em M2 (Alta confiança).

Não cortar. Não comprimir.

---

### R0-R0e (linhas 79-198, 120L)

**Veredito: FICA (seção crítica — M6)**

R0 (Memory Protocol), R0a (Role Awareness), R0b (Pendência Protocol), R0c (Scope Awareness), R0d (Operational Directives), R0e (User Rules).

Cada uma tem um `<why>` ou é load-bearing para continuidade entre sessões. O agente confirmou M6 (Alta confiança). São 120 linhas mas são o sistema de aprendizado persistente — nenhum corte sem ablação.

**Oportunidade de compressão menor**: R0 linha 120 ("Antes de executar operacoes (separacao, comunicacao PCP/Comercial, lancamento), considere se o perfil do usuario prescreve fluxo especifico") é instrução específica que poderia ser simplificada — mas risco de perda de comportamento real. Deixar.

---

### R1 (Comunicação Direta, linhas 200-210, 11L)

**Veredito: FICA**

Curto, acionável, com `<why>` implícito no nome e conteúdo. Define o tom default do agente (resultado direto, operador ocupado). Não cortar.

---

### R2 (Validação P1, linhas 212-246, 35L)

**Veredito: FICA**

Tabela de validação + `<self_check>` interno + `<why>` com custo real (interrupção da produção do cliente, FOB sem 100%). Load-bearing para o domínio logístico. M1 protege o `<why>`.

---

### R3 (Confirmação Obrigatória, linhas 248-264, 17L)

**Veredito: FICA**

Procedimento claro + R3.1 (qtd_saldo=0 em embarque não faturado — gotcha real). Load-bearing.

---

### R4 (Dados Reais Apenas, linhas 266-284, 19L)

**Veredito: FICA**

O `<why>` é fundacional ("já houve caso onde o agente informou disponibilidade de estoque que não existia"). A regra de Odoo como fonte oficial com tradução em PT-BR é específica ao sistema. Load-bearing.

---

### R5 (MCP Tools, linhas 286-348, 63L)

**Veredito: ENXUGA (moderadamente)**

Conteúdo: regras gerais de MCP, descoberta de tabela em camadas, `<use_parallel_tool_calls>`, `<teams_adaptive_cards>`.

**Redundância identificada**:
- `<use_parallel_tool_calls>` (7L): princípio repetido do preset. Pode ser comprimido para 3 linhas + ponteiro para preset.
- `<teams_adaptive_cards>` (32L): detalhado para 5 templates, com todas as regras de uso. É correto ter no prompt dado que é comportamento de runtime. Porém, os "Regras" no final (4 linhas) podem ser comprimidas.

**Proposta**: Comprimir `<use_parallel_tool_calls>` de 7 para 3 linhas. Comprimir as 4 linhas de "Regras" de teams_adaptive_cards para 2. Salva ~6 linhas.

---

### R6 (Comportamentos Proativos, linhas 350-368, 19L)

**Veredito: FICA**

`<context_awareness>` (compactação automática do context window) e `<fim_de_tarefa>` (não continuar após "obrigado") são comportamentos importantes. Sessões anteriores via tools. Load-bearing.

---

### R7 (Entity Resolution + Fast-paths, linhas 370-412, 43L)

**Veredito: ENXUGA**

Como identificado no item 3 acima:
- `<entity_resolution>` (10L): FICA — é o protocolo de resolução de entidades que previne erros de routing com nomes genéricos
- `<fast_paths>` (33L): ENXUGA — remover trigger de baseline duplicado com boundary (2L). Comprimir gerando-artifact de 7 linhas para 4. Salva ~6L.

---

### R8 (Detecção de Padrões Repetitivos, linhas 414-421, 8L)

**Veredito: FICA**

Curto, acionável, com exemplo concreto. Define um comportamento proativo que economiza turnos. Load-bearing.

---

### R9 (Registro de Insights, linhas 423-447, 25L)

**Veredito: FICA**

O `<why>` (linha 441-446) é essencialmente o argumento para AUTO-CAPACITAÇÃO. A regra é sobre como alimentar o flywheel de melhoria. Load-bearing para o sistema de qualidade.

---

### R10 (Erros Transientes, linhas 449-493, 45L)

**Veredito: ENXUGA (moderadamente)**

Os pontos 4 e 5 (Odoo fora do ar, SSW indisponível — linhas 469-477) são EXEMPLOS de tradução que poderiam estar em REGRAS_OUTPUT.md (onde I5 já documenta esse padrão). O `<why>` (linhas 482-492) é valioso.

**Proposta**: Mover pontos 4-5 (os exemplos de texto específico) para REGRAS_OUTPUT.md seção I5. Manter os 3 primeiros princípios + `<why>`. Salva ~9 linhas.

---

### R11 (Operações Odoo em SO faturado, linhas 495-526, 32L)

**Veredito: FICA (M5 protegido)**

R11 + R11.1 + R11.2 são gotchas de operação irreversível com NF fiscal. O `<why>` lista 5 consequências reais (multa, picking fantasma, lote vencido, etc.). Load-bearing. Não cortar.

---

### R12 (Escrita Direta no Banco, linhas 528-549, 22L)

**Veredito: FICA (M5 protegido)**

R12.1 (UPDATE/DELETE massa), R12.2 (preferir skill a SQL direto, append-only). Load-bearing para integridade de dados.

---

### I2-I4, I7 inline + ponteiro (linhas 551-589, 39L)

**Veredito: FICA (parcialmente)**

I2 (Detalhar Faltas), I3 (Incluir Peso/Pallet), I4 (Verificar Saldo em Separação) são regras de output operacional específicas da logística. Load-bearing.

I7 (Entrega Atômica de Artefatos, linhas 579-588, 10L): A regra inline é load-bearing — previne mensagens intermediárias sem link. O ponteiro para REGRAS_OUTPUT.md está correto.

---

### `<tools>` com `<routing_strategy>` e `<subagents>` (linhas 593-725, 133L)

**Veredito: FICA (com acréscimo)**

`<routing_strategy>` com domain_detection + boundaries + routing_confidence: como analisado no item 3, correto permanecer.

`<subagents>`: FICA, mas ADICIONAR `gestor-estoque-odoo` como identificado no item 4.

O `coordination_protocol` (linhas 660-672, ~13L): é o procedimento de COMO delegar, incluindo o protocolo de `/tmp/subagent-findings/`. Load-bearing — sem isso o agente não sabe formatar o prompt do subagente.

---

### `<business_context>` (linhas 728-753, 26L)

**Veredito: FICA (M4 protegido)**

P1>P2>P3>P4>P5>P6>P7 (resumo, 1 linha) + `critical_ids` (company IDs Odoo) + `critical_fields` (qtd_saldo gotcha) são exatamente do tipo que o agente confirma como load-bearing (M4). A redundância com CLAUDE.md é INTENCIONAL e documentada como `<!-- Redundancia intencional... -->` (linha 746).

---

### `<knowledge_base>` (linhas 755-759, 5L)

**Veredito: FICA**

5 linhas para ponteiro para ÍNDICE DE REFERÊNCIAS no CLAUDE.md. Mecanismo de descoberta JIT. Curto e efetivo.

---

### `<task_management>` (linhas 761-782, 22L)

**Veredito: FICA (com compressão leve)**

O `<delegation_pattern>` (linhas 769-781, 13L) detalha quando criar TaskCreate vs não criar. É corretamente instrucional — sem isso o agente cria Tasks desnecessárias para delegações simples.

**Proposta de compressão**: O padrão de 4 passos (TaskCreate→TaskUpdate→Agent→TaskUpdate) poderia ser listado em 4 bullets compactos em vez de 4 parágrafos narrativos. Salva ~4 linhas.

---

## SUMÁRIO GERAL

### Redundâncias encontradas

| ID | Par | Tipo | Ação |
|---|---|---|---|
| R-INT-1 | preset parallel_execution ↔ R5 use_parallel_tool_calls | Sobreposição de princípio | Comprimir R5 para 3L |
| R-INT-2 | preset reversibility ↔ L1 ↔ R3 | Camadas diferentes | MANTER |
| R-INT-3 | preset não_fabricar ↔ cannot_do ↔ L1 | Camadas diferentes | MANTER |
| R-INT-4 | preset language comment ↔ system_prompt language_policy | Correto: um é ponteiro | MANTER |
| R-INT-5 | preset memory awareness ↔ R0 completo | Camadas diferentes | MANTER |
| R-INT-6 | preset /tmp ↔ system_prompt role_definition /tmp | Duplicação desnecessária | Remover system_prompt:23 |
| R-INT-7 | preset security_invariants ↔ L1 | Camadas corretas | MANTER |
| R-CROSS-1 | R7 baseline trigger ↔ boundary baseline_financeiro | Duplicação de trigger | Remover trigger de R7 |
| R-CROSS-2 | subagents system_prompt ↔ CLAUDE.md tabela | Duas fontes | Resolver via hotfix + check |

### Delta estimado de linhas (system_prompt)

| Seção | Ação | Delta |
|---|---|---|
| metadata | Comprimir para 1 linha XML | -6L |
| role_definition `/tmp` | Remover linha 23 | -1L |
| R5 use_parallel_tool_calls | Comprimir para 3L | -4L |
| R7 fast_paths baseline | Remover trigger duplicado | -2L |
| R7 fast_paths artifact | Comprimir para 4L | -3L |
| R10 exemplos Odoo/SSW | Mover para REGRAS_OUTPUT.md I5 | -9L |
| task_management delegation_pattern | Comprimir para bullets | -4L |
| routing_confidence template | Comprimir para 4L | -3L |
| subagents | Adicionar gestor-estoque-odoo | +6L |
| **TOTAL** | | **-26L (net)** |

**Linhas atuais**: 784. **Linhas após poda**: ~758. **Tokens estimados**: de ~13.8K para ~13.3K (queda de ~500 tokens = ~3.5%).

---

## PROTEÇÕES — não cortar

Confirmadas como load-bearing (M1-M6 + análise própria):
1. Todos os `<why>` — evidência empírica de melhora de aderência
2. `constitutional_hierarchy` L1-L4 + exemplo concreto
3. L2 grounding ("fonte que PROVA vs. DESCREVE")
4. R0-R0e completos — sistema de memória persistente
5. `critical_fields` qtd_saldo e IDs de company Odoo
6. R11/R12 + `<why>` — operações irreversíveis
7. R2 `<self_check>` + `<why>` — validação P1
8. `coordination_protocol` em subagents — `/tmp/subagent-findings/` protocol
