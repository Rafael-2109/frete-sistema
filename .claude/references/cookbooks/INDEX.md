# Índice do Claude Cookbooks

**Repositório:** [anthropics/claude-cookbooks](https://github.com/anthropics/claude-cookbooks)

Este documento serve como índice de referência rápida para todos os recursos do Claude Cookbooks que podem ser úteis no projeto.

---

## 📁 Recursos Implementados Localmente

Guias detalhados na pasta `.claude/references/cookbooks/`:

| Arquivo | Descrição |
|---------|-----------|
| [CONTEXT_COMPACTION.md](CONTEXT_COMPACTION.md) | Reduzir tokens em sessões longas |
| [METAPROMPT.md](METAPROMPT.md) | Gerar prompts otimizados |
| [BUILDING_EVALS.md](BUILDING_EVALS.md) | Framework de avaliação de prompts |
| [PROMPT_CACHING.md](PROMPT_CACHING.md) | Cache para reduzir latência/custo |

---

## 📚 Índice Completo do Repositório

### 🤖 Claude Agent SDK (`claude_agent_sdk/`)

| Notebook | Descrição | Link |
|----------|-----------|------|
| **00_one_liner_research_agent** | Agente de pesquisa em 1 linha | [Link](https://github.com/anthropics/claude-cookbooks/blob/main/claude_agent_sdk/00_The_one_liner_research_agent.ipynb) |
| **01_chief_of_staff_agent** | Agente executivo completo (memory, hooks, plan mode) | [Link](https://github.com/anthropics/claude-cookbooks/blob/main/claude_agent_sdk/01_The_chief_of_staff_agent.ipynb) |
| **02_observability_agent** | Integração MCP (Git, GitHub) | [Link](https://github.com/anthropics/claude-cookbooks/blob/main/claude_agent_sdk/02_The_observability_agent.ipynb) |

### 🔧 Tool Use (`tool_use/`)

| Notebook | Descrição | Link |
|----------|-----------|------|
| **memory_cookbook** | Sistema de memória persistente | [Link](https://github.com/anthropics/claude-cookbooks/blob/main/tool_use/memory_cookbook.ipynb) |
| **memory_tool.py** | Implementação do Memory Tool | [Link](https://github.com/anthropics/claude-cookbooks/blob/main/tool_use/memory_tool.py) |
| **automatic-context-compaction** | Compactação automática de contexto | [Link](https://github.com/anthropics/claude-cookbooks/blob/main/tool_use/automatic-context-compaction.ipynb) |
| **parallel_tools** | Chamadas de ferramentas em paralelo | [Link](https://github.com/anthropics/claude-cookbooks/blob/main/tool_use/parallel_tools.ipynb) |
| **extended_thinking_with_tools** | Extended thinking + tool use | [Link](https://github.com/anthropics/claude-cookbooks/blob/main/extended_thinking/extended_thinking_with_tool_use.ipynb) |
| **customer_service_agent** | Agente de atendimento ao cliente | [Link](https://github.com/anthropics/claude-cookbooks/blob/main/tool_use/customer_service_agent.ipynb) |

### 🎨 Patterns/Agents (`patterns/agents/`)

| Notebook | Padrão | Link |
|----------|--------|------|
| **basic_workflows** | Chaining, Parallel, Routing | [Link](https://github.com/anthropics/claude-cookbooks/blob/main/patterns/agents/basic_workflows.ipynb) |
| **orchestrator_workers** | Orquestrador + Workers | [Link](https://github.com/anthropics/claude-cookbooks/blob/main/patterns/agents/orchestrator_workers.ipynb) |
| **evaluator_optimizer** | Generate + Evaluate loop | [Link](https://github.com/anthropics/claude-cookbooks/blob/main/patterns/agents/evaluator_optimizer.ipynb) |

### 🎯 Skills (`skills/`)

| Notebook | Descrição | Link |
|----------|-----------|------|
| **01_skills_introduction** | Introdução a Skills (Excel, PDF, PPT) | [Link](https://github.com/anthropics/claude-cookbooks/blob/main/skills/notebooks/01_skills_introduction.ipynb) |
| **02_skills_financial_applications** | Aplicações financeiras | [Link](https://github.com/anthropics/claude-cookbooks/blob/main/skills/notebooks/02_skills_financial_applications.ipynb) |
| **03_skills_custom_development** | Desenvolvimento de Skills customizados | [Link](https://github.com/anthropics/claude-cookbooks/blob/main/skills/notebooks/03_skills_custom_development.ipynb) |

### 📊 Capabilities (`capabilities/`)

| Pasta | Descrição | Link |
|-------|-----------|------|
| **text_to_sql** | Natural language → SQL | [Link](https://github.com/anthropics/claude-cookbooks/tree/main/capabilities/text_to_sql) |
| **classification** | Classificação com RAG | [Link](https://github.com/anthropics/claude-cookbooks/tree/main/capabilities/classification) |
| **summarization** | Sumarização avançada | [Link](https://github.com/anthropics/claude-cookbooks/tree/main/capabilities/summarization) |
| **retrieval_augmented_generation** | RAG otimizado | [Link](https://github.com/anthropics/claude-cookbooks/tree/main/capabilities/retrieval_augmented_generation) |
| **contextual-embeddings** | Embeddings com contexto | [Link](https://github.com/anthropics/claude-cookbooks/tree/main/capabilities/contextual-embeddings) |

### 🛠️ Misc (`misc/`)

| Notebook | Descrição | Link |
|----------|-----------|------|
| **metaprompt** | Gerar prompts otimizados | [Link](https://github.com/anthropics/claude-cookbooks/blob/main/misc/metaprompt.ipynb) |
| **prompt_caching** | Cache de prompts | [Link](https://github.com/anthropics/claude-cookbooks/blob/main/misc/prompt_caching.ipynb) |
| **building_evals** | Framework de avaliações | [Link](https://github.com/anthropics/claude-cookbooks/blob/main/misc/building_evals.ipynb) |
| **generate_test_cases** | Dados de teste sintéticos | [Link](https://github.com/anthropics/claude-cookbooks/blob/main/misc/generate_test_cases.ipynb) |
| **using_citations** | RAG com citações | [Link](https://github.com/anthropics/claude-cookbooks/blob/main/misc/using_citations.ipynb) |
| **how_to_enable_json_mode** | Forçar output JSON | [Link](https://github.com/anthropics/claude-cookbooks/blob/main/misc/how_to_enable_json_mode.ipynb) |
| **batch_processing** | Processamento em lote | [Link](https://github.com/anthropics/claude-cookbooks/blob/main/misc/batch_processing.ipynb) |
| **building_moderation_filter** | Filtros de moderação | [Link](https://github.com/anthropics/claude-cookbooks/blob/main/misc/building_moderation_filter.ipynb) |

### 💻 Coding (`coding/`)

| Notebook | Descrição | Link |
|----------|-----------|------|
| **prompting_for_frontend_aesthetics** | Gerar frontends bonitos | [Link](https://github.com/anthropics/claude-cookbooks/blob/main/coding/prompting_for_frontend_aesthetics.ipynb) |

### 🔗 Third Party (`third_party/`)

| Integração | Descrição |
|------------|-----------|
| **Pinecone** | Vector database |
| **MongoDB** | NoSQL database |
| **LlamaIndex** | RAG framework |
| **VoyageAI** | Embeddings |
| **Wikipedia** | Knowledge base |
| **WolframAlpha** | Computação |
| **Deepgram** | Speech-to-text |
| **ElevenLabs** | Text-to-speech |

---

## 🎯 Recursos por Caso de Uso

### Para Análise de Carteira
- Context Compaction (sessões longas)
- Orchestrator-Workers (análise multi-perspectiva)
- Building Evals (validar decisões)

### Para Comunicação PCP/Comercial
- Metaprompt (criar templates)
- Generate Test Cases (testar templates)

### Para Dashboards/Frontend
- Frontend Aesthetics (design distintivo)
- Skills (gerar Excel/PDF)

### Para Integração Odoo
- Tool Use patterns
- Memory Tool (aprender padrões)

### Para Processamento em Lote
- Batch Processing
- Context Compaction
- Parallel Tools

---

## 📖 Documentação Oficial

- [Claude API Docs](https://docs.anthropic.com/claude/docs)
- [Claude Code Docs](https://docs.claude.com/en/docs/claude-code)
- [Agent SDK Docs](https://docs.anthropic.com/en/docs/claude-code/sdk)
- [Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)
- [Effective Context Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

---

**Última atualização:** Dezembro 2024
