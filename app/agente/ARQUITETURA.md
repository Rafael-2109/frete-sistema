# Arquitetura do Agente - Especificações Técnicas Anthropic

**Versão:** 2.0
**Data:** 29/11/2025
**Fontes:** Artigos oficiais Anthropic Engineering

---

# 1. FEEDBACK LOOP (Padrão Central)

```
┌─────────────────────────────────────────────────────────────┐
│  GATHER CONTEXT → TAKE ACTION → VERIFY WORK → REPEAT        │
└─────────────────────────────────────────────────────────────┘
```

## 1.1 Gather Context
- Usar bash utilities (grep, tail) para carregar seletivamente
- Folder structure como mecanismo de context engineering
- Agente decide o que entra no contexto

## 1.2 Take Action
- Tools: blocos primários de execução
- Code generation para outputs precisos e reusáveis
- MCPs para integrações padronizadas

## 1.3 Verify Work
- **Rule-based feedback**: regras explícitas, reportar falhas com razões
- **Visual feedback**: screenshots para validação de UI
- **LLM-as-Judge**: apenas para critérios fuzzy (trade-off: latência)

---

# 2. TOOL DEFINITIONS

## 2.1 Estrutura Completa de uma Tool

```json
{
  "name": "nome_da_tool",
  "description": "Descrição detalhada como explicaria a um novo funcionário...",
  "input_schema": {
    "type": "object",
    "properties": {
      "param_name": {
        "type": "string",
        "description": "Descrição do parâmetro"
      }
    },
    "required": ["param_name"]
  },
  "input_examples": [
    {"param_name": "exemplo_minimo"},
    {"param_name": "exemplo_completo", "param_opcional": "valor"}
  ],
  "defer_loading": false
}
```

## 2.2 Descrições Eficazes

**Estrutura obrigatória:**
1. O que a tool faz (1-2 frases)
2. Quando usar vs quando NÃO usar
3. Contexto implícito tornado explícito (terminologia, relacionamentos)
4. Formato de query especializado (se houver)
5. O que retorna

**Exemplo ruim:**
```
"description": "Busca pedidos"
```

**Exemplo bom:**
```
"description": "Busca pedidos na carteira de vendas. Use para consultas por cliente (nome parcial), número do pedido (exato) ou produto. NÃO use para pedidos já faturados (use tool X). Retorna: num_pedido, cliente, qtd_saldo, valor, status. Limite padrão: 50 registros."
```

## 2.3 Parâmetros

- Nomes auto-explicativos: `user_id` não `user`
- Incluir tipo e descrição
- Evitar ambiguidade via data models estritos

## 2.4 Response Format Enum

```python
class ResponseFormat(Enum):
    DETAILED = "detailed"  # Todos os campos, contexto completo
    CONCISE = "concise"    # ~1/3 dos tokens, campos essenciais
```

Implementar em tools que retornam muitos dados.

## 2.5 Erros Acionáveis

**Estrutura:**
```json
{
  "success": false,
  "error": {
    "message": "Cliente 'Atacado' não encontrado",
    "suggestion": "Você quis dizer 'Atacadão'?",
    "similar_matches": ["Atacadão", "Atacadista Silva"],
    "correct_format": "Nome parcial do cliente, ex: 'Atacadão'"
  }
}
```

**Proibido:**
- Códigos opacos (E001, E002)
- Stack traces
- Mensagens genéricas ("Erro ao processar")

## 2.6 Namespacing

**Por serviço:**
```
carteira_consultar_pedido
carteira_criar_separacao
estoque_consultar_saldo
```

**Por recurso:**
```
pedido_buscar
pedido_criar
pedido_atualizar
```

Testar ambos com evals - não há regra universal.

## 2.7 Consolidação de Tools

**Anti-pattern (evitar):**
```
list_clientes → list_pedidos → get_pedido_detalhes → check_estoque
```

**Pattern correto:**
```
analisar_disponibilidade_pedido
  → Recebe: num_pedido ou cliente
  → Faz internamente: busca pedido, verifica estoque, calcula opções
  → Retorna: análise completa com opções A/B/C
```

---

# 3. TOOL SEARCH TOOL

## 3.1 Quando Usar

| Critério | Usar Tool Search | Não usar |
|----------|------------------|----------|
| Definições de tools | >10K tokens | <10K tokens |
| Quantidade de tools | 10+ | <10 |
| Uso por sessão | Variado | Todas frequentes |

## 3.2 Estrutura de Configuração

```json
{
  "tools": [
    {
      "type": "tool_search_tool_regex_20251119",
      "name": "tool_search"
    },
    {
      "name": "ferramenta_frequente",
      "description": "...",
      "input_schema": {...},
      "defer_loading": false
    },
    {
      "name": "ferramenta_rara",
      "description": "...",
      "input_schema": {...},
      "defer_loading": true
    }
  ]
}
```

## 3.3 Marcação de Tools

```python
TOOLS_CORE = [
    {"name": "consultar_pedido", "defer_loading": False},  # Sempre carregada
    {"name": "analisar_disponibilidade", "defer_loading": False},
]

TOOLS_EXTRAS = [
    {"name": "relatorio_complexo", "defer_loading": True},  # Sob demanda
    {"name": "exportar_dados", "defer_loading": True},
]
```

## 3.4 Implementações de Busca

- **Regex**: busca por padrão no nome/descrição
- **BM25**: ranking por relevância
- **Embeddings**: busca semântica (mais complexo)

## 3.5 Resultado Esperado

- Tools com `defer_loading: false`: ~500 tokens no prompt
- Tools com `defer_loading: true`: ~72K tokens evitados
- Redução: **85% menos tokens** mantendo acesso completo

---

# 4. PROGRAMMATIC TOOL CALLING (PTC)

## 4.1 Quando Usar

| Cenário | Usar PTC | Não usar |
|---------|----------|----------|
| Dataset grande + agregação | ✓ | |
| 3+ chamadas dependentes | ✓ | |
| Operações paralelas | ✓ | |
| Filtros/transformações | ✓ | |
| Chamada única simples | | ✓ |
| Precisa ver intermediários | | ✓ |

## 4.2 Estrutura de Configuração

```json
{
  "tools": [
    {
      "type": "code_execution_20250825",
      "name": "code_execution"
    },
    {
      "name": "buscar_pedidos",
      "allowed_callers": ["code_execution_20250825"],
      "input_schema": {...}
    }
  ]
}
```

## 4.3 Formato do Código Gerado

Claude gera código Python que:
```python
# Exemplo de código gerado pelo Claude
pedidos = buscar_pedidos(cliente="Atacadão")
estoque = consultar_estoque(produtos=[p["cod_produto"] for p in pedidos])

resultado = []
for pedido in pedidos:
    cod = pedido["cod_produto"]
    disp = estoque.get(cod, 0) >= pedido["qtd_saldo"]
    resultado.append({
        "pedido": pedido["num_pedido"],
        "disponivel": disp
    })

print(json.dumps(resultado))
```

## 4.4 Resposta do Executor

```json
{
  "type": "code_execution_tool_result",
  "tool_use_id": "srvtoolu_abc",
  "content": {
    "stdout": "[{\"pedido\": \"VCD123\", \"disponivel\": true}]"
  }
}
```

## 4.5 Identificação do Caller

```json
{
  "caller": {
    "type": "code_execution_20250825",
    "tool_id": "srvtoolu_abc"
  }
}
```

---

# 5. TOOL USE EXAMPLES

## 5.1 Estrutura

```json
{
  "name": "criar_separacao",
  "input_schema": {...},
  "input_examples": [
    {
      "num_pedido": "VCD-2024-001234",
      "data_expedicao": "2024-12-15",
      "itens": [
        {"cod_produto": "AZ001", "quantidade": 100}
      ]
    },
    {
      "num_pedido": "VCD-2024-005678",
      "opcao": "A"
    },
    {
      "num_pedido": "VCD-2024-009999"
    }
  ]
}
```

## 5.2 Boas Práticas

| Prática | Especificação |
|---------|---------------|
| Quantidade | 1-5 exemplos por tool |
| Dados | Realistas, não placeholders |
| Cobertura | Mínimo, parcial e completo |
| Foco | Campos ambíguos não claros no schema |

## 5.3 Quando Usar

- Estruturas nested complexas
- Muitos parâmetros opcionais
- Convenções específicas do domínio
- Erros frequentes de formato

## 5.4 Resultado Esperado

Acurácia em parâmetros complexos: **72% → 90%**

---

# 6. CONTEXT ENGINEERING

## 6.1 System Prompt - Estrutura

```xml
<background_information>
Persona e contexto do agente (2-3 linhas)
Data atual: {data}
</background_information>

<instructions>
Regras de comportamento essenciais
Quando pedir clarificação
Formato de resposta esperado
</instructions>

## Tool guidance
Lista de tools com descrições

## Output description
Formato JSON esperado nas respostas
```

## 6.2 Princípio de Altitude

| Nível | Problema | Solução |
|-------|----------|---------|
| Muito prescritivo | Lógica if-else hardcoded, brittle | Heurísticas fortes |
| Muito vago | Sem sinais concretos | Exemplos específicos |
| **Ideal** | Guia comportamento + flexibilidade | Princípios + exemplos |

## 6.3 Limite de Tokens

- **Meta**: Mínimo necessário que descreve comportamento completo
- **Sub-agentes**: Retornar resumos de 1.000-2.000 tokens
- **Context window**: 200.000 tokens (risco de truncamento)

---

# 7. COMPACTION (Resumo de Contexto)

## 7.1 Quando Ativar

- Conversa aproximando limite do context window
- Não há threshold numérico fixo - monitorar uso

## 7.2 O que Preservar

- Decisões arquiteturais
- Bugs não resolvidos
- Detalhes de implementação relevantes
- 5 arquivos/itens mais recentemente acessados

## 7.3 O que Descartar

- Outputs redundantes de tools
- Mensagens superseded
- Detalhes já consolidados

## 7.4 Implementação

```python
def compactar_contexto(mensagens, limite_tokens):
    # 1. Passar histórico para o modelo resumir
    resumo = claude.resumir(mensagens, preservar=[
        "decisoes_arquiteturais",
        "bugs_pendentes",
        "contexto_atual"
    ])

    # 2. Manter N itens recentes
    recentes = mensagens[-5:]

    # 3. Retornar contexto compactado
    return resumo + recentes
```

## 7.5 Tuning

1. **Primeiro**: Maximizar recall (capturar tudo relevante)
2. **Depois**: Iterar para melhorar precisão (eliminar supérfluo)

---

# 8. MEMÓRIA ESTRUTURADA (Structured Note-Taking)

## 8.1 Formato

Arquivo externo (ex: `NOTES.md`, `estado.json`) persistido fora do context window.

## 8.2 Conteúdo

```json
{
  "fatos": [
    {"tipo": "preferencia", "entidade": "cliente_X", "valor": "entrega_matutina"},
    {"tipo": "restricao", "entidade": "produto_Y", "valor": "nao_fracionar"}
  ],
  "tarefas_pendentes": [
    {"id": 1, "descricao": "Confirmar agendamento pedido VCD123"}
  ],
  "contexto_sessao": {
    "cliente_atual": "Atacadão",
    "ultima_acao": "consultar_pedido"
  }
}
```

## 8.3 Recuperação

- Agente lê notas após reset de contexto
- Permite continuar sessões longas (multi-hora)

---

# 9. JUST-IN-TIME CONTEXT

## 9.1 Princípio

Não carregar dados completos upfront. Manter identificadores leves.

## 9.2 Identificadores Leves

```python
contexto_minimo = {
    "cliente_id": "CLI-12345",      # Não: {nome, cnpj, endereco, ...}
    "pedido_ref": "VCD-2024-001",   # Não: {itens: [...], valores: {...}}
    "arquivo": "/path/to/data.json" # Não: conteúdo completo
}
```

## 9.3 Carregamento Dinâmico

```python
# Claude solicita dados quando necessário
tool_call = {"tool": "get_pedido_detalhes", "params": {"ref": "VCD-2024-001"}}

# Sistema carrega apenas o necessário
dados = carregar_pedido("VCD-2024-001")
```

## 9.4 Técnicas

- `grep`, `tail` para arquivos grandes
- Queries com `LIMIT` e filtros
- Paginação com cursores

---

# 10. SINGLE-AGENT VS MULTI-AGENT

## 10.1 Critérios de Decisão

| Cenário | Arquitetura | Tool calls |
|---------|-------------|------------|
| Busca simples, fato único | Single-agent | 3-10 |
| Comparações diretas | 2-4 sub-agents | 10-15 cada |
| Pesquisa complexa, múltiplas fontes | 10+ sub-agents | Dividido |

## 10.2 Consumo de Tokens

| Tipo | Multiplicador vs Chat |
|------|----------------------|
| Single-agent | ~4x |
| Multi-agent | ~15x |

**Implicação**: Multi-agent só viável para tarefas de alto valor.

## 10.3 Estrutura do Orquestrador

```
LeadAgent:
  1. Analisa query
  2. Desenvolve estratégia
  3. Spawna 3-5 sub-agents em PARALELO
  4. Cada sub-agent recebe:
     - Objetivo específico
     - Formato de output
     - Orientação de tools
     - Limites da tarefa
  5. Consolida resultados
```

## 10.4 Retorno de Sub-Agents

- Lista de findings estruturados
- Armazenar em filesystem (evitar "telephone game")
- Resumos de 1.000-2.000 tokens

## 10.5 Decisão para Este Sistema

Para sistema logístico típico (consultas, separações, projeções):
- **80-90% dos casos**: Single-agent suficiente
- **Casos para multi-agent**: Análise de malha logística, centenas de clientes/UFs

---

# 11. EVALS (Avaliação)

## 11.1 Conjunto Inicial

**Quantidade**: ~20 queries representativas

**Categorias**:
- Consultas simples (5)
- Análises/projeções (5)
- Ações/criações (5)
- Edge cases (5)

## 11.2 Formato de Eval

```json
{
  "id": "eval_001",
  "query": "Quais pedidos do Atacadão estão pendentes?",
  "contexto_inicial": {
    "usuario_id": 1
  },
  "expectativas": {
    "tool_esperada": "consultar_pedido",
    "params_esperados": {
      "cliente": "Atacadão"
    },
    "campos_obrigatorios_resposta": ["num_pedido", "cliente", "status"],
    "condicao_sucesso": "resultados.length > 0 AND todos.cliente CONTAINS 'Atacadão'"
  }
}
```

## 11.3 LLM-as-Judge Rubric

```json
{
  "criterios": [
    {
      "nome": "factual_accuracy",
      "peso": 0.3,
      "pergunta": "As informações retornadas correspondem aos dados reais?"
    },
    {
      "nome": "completeness",
      "peso": 0.25,
      "pergunta": "Todos os aspectos solicitados foram cobertos?"
    },
    {
      "nome": "tool_efficiency",
      "peso": 0.2,
      "pergunta": "Usou as tools corretas com frequência razoável?"
    },
    {
      "nome": "response_quality",
      "peso": 0.15,
      "pergunta": "A resposta é clara e útil para o usuário?"
    },
    {
      "nome": "error_handling",
      "peso": 0.1,
      "pergunta": "Erros foram tratados adequadamente?"
    }
  ],
  "output": {
    "scores": {"factual_accuracy": 0.9, "...": "..."},
    "score_final": 0.85,
    "passou": true,
    "feedback": "..."
  }
}
```

## 11.4 Métricas

| Métrica | Como medir |
|---------|-----------|
| Acurácia | % de respostas corretas vs esperado |
| Latência | Tempo total de resposta |
| Tokens | Consumo médio por requisição |
| Tool accuracy | % de tools corretas selecionadas |
| Fallback rate | % que precisou de retry |

## 11.5 Processo

```
1. Executar 20 queries programaticamente
2. Coletar: resposta, tools usadas, tokens, tempo
3. Avaliar com rubric (manual ou LLM-as-Judge)
4. Identificar padrões de falha
5. Ajustar tools/prompt
6. Repetir
```

---

# 12. PERGUNTAS DIAGNÓSTICAS

Usar quando performance não está satisfatória:

| Sintoma | Pergunta | Ação |
|---------|----------|------|
| Mal interpretação | Falta informação na busca? | Melhorar API de busca |
| Falhas repetidas | Regras formais resolveriam? | Adicionar validação |
| Não consegue se corrigir | Faltam tools? | Adicionar tools alternativas |
| Performance varia | Precisa de test set? | Criar evals programáticos |

---

# 13. ANTI-PATTERNS

## 13.1 Arquitetura

| Anti-pattern | Por que evitar |
|--------------|----------------|
| Muitos sub-agents para query simples | 15x tokens, latência |
| Busca sem fim por fontes inexistentes | Desperdício de recursos |
| Instruções vagas | Duplicação de trabalho |
| Queries muito específicas/verbose | Falha em encontrar resultados |
| Context overflow sem compaction | Degradação de performance |

## 13.2 Tools

| Anti-pattern | Por que evitar |
|--------------|----------------|
| Wrapper de API sem otimização | Não considera contexto do agente |
| Tools demais com sobreposição | Confusão na seleção |
| `list_all_X` sem filtro | Desperdiça contexto |
| Erros com códigos opacos | Agente não consegue se corrigir |

## 13.3 Contexto

| Anti-pattern | Por que evitar |
|--------------|----------------|
| Prompts com if-else hardcoded | Brittle, difícil manter |
| Prompts vagos sem exemplos | Comportamento inconsistente |
| Exemplos exaustivos de edge cases | Poluem contexto |
| Compaction agressiva demais | Perde contexto crítico |

---

# 14. CHECKLIST DE IMPLEMENTAÇÃO

## Fase 1: Fundação
- [ ] System prompt estruturado (<100 linhas)
- [ ] 3-5 tools CORE com descrições completas
- [ ] input_examples para cada tool
- [ ] Formato de erro acionável

## Fase 2: Execução
- [ ] Executor de tools
- [ ] Response format (DETAILED/CONCISE)
- [ ] Tratamento de erros

## Fase 3: Contexto
- [ ] Identificadores leves (just-in-time)
- [ ] Compaction básica
- [ ] Memória estruturada (se necessário)

## Fase 4: Avaliação
- [ ] 20 queries de eval definidas
- [ ] Script de execução programática
- [ ] Rubric de avaliação
- [ ] Baseline medido

## Fase 5: Otimização
- [ ] Tool Search (se >10 tools)
- [ ] PTC (se operações complexas)
- [ ] Ajustes baseados em evals

---

# 15. AGENT SKILLS (Padrão Anthropic)

## 15.1 Conceito

Skills são pastas organizadas com instruções, scripts e recursos que agentes podem descobrir e carregar dinamicamente. Transformam agentes genéricos em especializados.

**Fonte oficial**: [Equipping agents for the real world with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)

## 15.2 Estrutura de Diretório

```
skill-name/
├── SKILL.md              # OBRIGATÓRIO - Entry point com YAML frontmatter
├── references/           # Documentação carregada sob demanda
│   ├── queries.md
│   └── domain-rules.md
├── scripts/              # Scripts executáveis
│   └── *.py
└── assets/               # Templates, arquivos binários
```

## 15.3 Formato do SKILL.md

```yaml
---
name: skill-name-here
description: O que faz e quando usar. Máximo 1024 caracteres.
---

# Título da Skill

## Quando Usar
- Condição 1
- Condição 2

## Fluxo de Trabalho
1. Passo 1
2. Passo 2

## Scripts Disponíveis
| Script | Propósito |
|--------|-----------|

## Regras do Domínio
...

## Referências
- Para detalhes: ver [arquivo.md](references/arquivo.md)
```

## 15.4 Regras de Nomenclatura

### Campo `name` (YAML frontmatter)

| Regra | Especificação |
|-------|---------------|
| Máximo | 64 caracteres |
| Caracteres | Letras minúsculas, números, hífens |
| Proibido | Tags XML, palavras reservadas (anthropic, claude) |
| Formato preferido | **Gerund form** (verbo + -ing) |

### Padrões Aceitos

| Padrão | Exemplo | Uso |
|--------|---------|-----|
| **Gerund form** ✅ | `querying-freight-orders` | RECOMENDADO |
| Frase nominal | `freight-order-query` | Aceitável |
| Orientado à ação | `query-freight-orders` | Aceitável |

### Exemplos Bons vs Ruins

| ✅ BOM | ❌ RUIM | Motivo |
|--------|--------|--------|
| `analyzing-order-availability` | `agente-logistico` | Gerund form descreve ação |
| `diagnosing-shipping-delays` | `helper` | Específico vs genérico |
| `querying-stock-status` | `utils` | Descritivo vs vago |

## 15.5 Campo `description`

| Regra | Especificação |
|-------|---------------|
| Máximo | 1024 caracteres |
| Conteúdo | O que faz + quando usar |
| Pessoa | **Terceira pessoa** (não "eu posso") |
| Objetivo | Permitir seleção entre 100+ skills |

### Exemplo de Descrição Eficaz

```yaml
description: >-
  Queries and analyzes freight order data including pending orders,
  stock availability, delivery forecasts, and shipping bottlenecks.
  Use when user asks about order status, stock projections,
  delivery dates, or wants to identify shipping issues.
```

## 15.6 Progressive Disclosure

Skills implementam carregamento progressivo em 3 níveis:

| Nível | O que carrega | Quando |
|-------|---------------|--------|
| 1 | Apenas `name` + `description` | Sempre (startup) |
| 2 | SKILL.md completo | Quando skill é ativada |
| 3 | Arquivos referenciados | Quando necessários |

**Benefício**: Economia de tokens - apenas ~50 tokens por skill no nível 1.

## 15.7 Limites e Boas Práticas

| Aspecto | Limite/Recomendação |
|---------|---------------------|
| SKILL.md | < 500 linhas |
| Arquivos referenciados | 1 nível de profundidade máximo |
| Arquivos > 100 linhas | Incluir índice no topo |
| Scripts Python | snake_case para arquivos, lowercase-hyphens para name |

## 15.8 Nomenclatura de Scripts

### Padrão para nomes de scripts

Seguir mesmo princípio de clareza das skills:

| Padrão | Exemplo Script | Exemplo Name |
|--------|----------------|--------------|
| Ação + Objeto | `query_orders.py` | `querying-orders` |
| Verbo + Domínio | `analyze_availability.py` | `analyzing-availability` |
| Diagnóstico | `diagnose_delays.py` | `diagnosing-delays` |

### Consolidação vs Granularidade

**Regra Anthropic**: "If a human engineer can't definitively say which tool should be used in a given situation, an AI agent can't be expected to do better."

| Cenário | Decisão |
|---------|---------|
| 2+ scripts com lógica ~80% similar | CONSOLIDAR com flags |
| Scripts com domínios distintos | MANTER separados |
| Script cobre 1 query trivial | CONSIDERAR consolidar |
| Script cobre 3+ queries relacionadas | OK manter separado |

### Identificação de Redundância via Nomes

Simular nomes Anthropic para cada script ajuda identificar sobreposição:

```
analisar_disponibilidade.py → analyzing-order-availability
analisar_gargalos.py        → analyzing-shipping-bottlenecks

# Ambos são "analyzing-*" - verificar se podem consolidar
# em "analyzing-availability" com flags --pedido vs --grupo
```

## 15.9 Checklist de Criação de Skill

### Estrutura
- [ ] Diretório com nome em lowercase-hyphens
- [ ] SKILL.md com frontmatter YAML válido
- [ ] Campo `name` seguindo gerund form
- [ ] Campo `description` com "o que faz" + "quando usar"
- [ ] Referências em `references/` (se > 500 linhas total)

### Nomenclatura
- [ ] Nome simula ação clara (não genérico)
- [ ] Scripts com propósitos distintos (não sobrepostos)
- [ ] Cada script cobre queries relacionadas semanticamente

### Conteúdo
- [ ] SKILL.md < 500 linhas
- [ ] Índice em arquivos > 100 linhas
- [ ] Referências max 1 nível de profundidade
- [ ] Exemplos concretos (não abstratos)

### Qualidade
- [ ] Testado com Haiku, Sonnet, Opus
- [ ] Mínimo 3 evals criados
- [ ] Feedback incorporado

---

# 16. REFERÊNCIAS

| Artigo | URL | Foco |
|--------|-----|------|
| Building Agents with Claude Agent SDK | anthropic.com/engineering/building-agents-with-the-claude-agent-sdk | Feedback loop, verificação |
| Writing Tools for Agents | anthropic.com/engineering/writing-tools-for-agents | Tool definitions, consolidação |
| Effective Context Engineering | anthropic.com/engineering/effective-context-engineering-for-ai-agents | Prompts, compaction, memória |
| Advanced Tool Use | anthropic.com/engineering/advanced-tool-use | Tool Search, PTC, Examples |
| Multi-Agent Research System | anthropic.com/engineering/multi-agent-research-system | Orquestração, evals, métricas |
| **Equipping agents with Skills** | anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills | Skills, progressive disclosure |
| **Skill Authoring Best Practices** | platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices | Formato SKILL.md, nomenclatura |
| **Anthropic Skills Repository** | github.com/anthropics/skills | Exemplos oficiais, templates |
