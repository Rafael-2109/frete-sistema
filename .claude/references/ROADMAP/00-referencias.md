# 00 - Referencias e Fontes

Documentacao oficial e recursos utilizados como base para as correcoes.

---

## Documentacao Oficial Anthropic

### Skills

| Recurso | Descricao | Uso no ROADMAP |
|---------|-----------|----------------|
| [Skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) | Guia completo de criacao de Skills | 01, 02, 04, 05 |
| [Skills overview](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview) | Arquitetura e estrutura de Skills | Geral |
| [Agent Skills in Claude Code](https://docs.claude.com/en/docs/claude-code/skills) | Skills no Claude Code | Geral |

### Prompt Engineering

| Recurso | Descricao | Uso no ROADMAP |
|---------|-----------|----------------|
| [Claude 4 best practices](https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/claude-4-best-practices) | Tecnicas para Claude 4.x | 02 |
| [Prompt engineering overview](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview) | Visao geral de prompting | Geral |

### Agentes e Contexto

| Recurso | Descricao | Uso no ROADMAP |
|---------|-----------|----------------|
| [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) | Como manter contexto em agentes | 03 |
| [Building agents with Claude Agent SDK](https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk) | Construcao de agentes | 03 |
| [Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) | Engenharia de contexto | 03 |
| [Managing context](https://anthropic.com/news/context-management) | Gerenciamento de contexto | 03 |
| [Claude Code best practices](https://www.anthropic.com/engineering/claude-code-best-practices) | Praticas para Claude Code | Geral |

---

## Cookbooks Locais

Arquivos em `.claude/references/cookbooks/`:

| Arquivo | Descricao | Uso no ROADMAP |
|---------|-----------|----------------|
| [METAPROMPT.md](../cookbooks/METAPROMPT.md) | Gerar prompts otimizados automaticamente | 01-decision-tree |
| [BUILDING_EVALS.md](../cookbooks/BUILDING_EVALS.md) | Framework de avaliacao de prompts | Fase 3 (testes) |
| [CONTEXT_COMPACTION.md](../cookbooks/CONTEXT_COMPACTION.md) | Reducao de tokens em sessoes longas | 03-contexto |
| [PROMPT_CACHING.md](../cookbooks/PROMPT_CACHING.md) | Cache para reducao de latencia | Futuro |

---

## Cookbooks Remotos (GitHub)

Repositorio: [anthropics/claude-cookbooks](https://github.com/anthropics/claude-cookbooks)

### Relevantes para Skills

| Notebook | Descricao | Uso no ROADMAP |
|----------|-----------|----------------|
| [01_skills_introduction](https://github.com/anthropics/claude-cookbooks/blob/main/skills/notebooks/01_skills_introduction.ipynb) | Introducao a Skills | Geral |
| [03_skills_custom_development](https://github.com/anthropics/claude-cookbooks/blob/main/skills/notebooks/03_skills_custom_development.ipynb) | Desenvolvimento customizado | 04-examples |

### Relevantes para Contexto/Memoria

| Notebook | Descricao | Uso no ROADMAP |
|----------|-----------|----------------|
| [memory_cookbook](https://github.com/anthropics/claude-cookbooks/blob/main/tool_use/memory_cookbook.ipynb) | Sistema de memoria persistente | 03-contexto |
| [automatic-context-compaction](https://github.com/anthropics/claude-cookbooks/blob/main/tool_use/automatic-context-compaction.ipynb) | Compactacao automatica | 03-contexto |

### Relevantes para Testes

| Notebook | Descricao | Uso no ROADMAP |
|----------|-----------|----------------|
| [building_evals](https://github.com/anthropics/claude-cookbooks/blob/main/misc/building_evals.ipynb) | Framework de avaliacoes | Fase 3 |
| [generate_test_cases](https://github.com/anthropics/claude-cookbooks/blob/main/misc/generate_test_cases.ipynb) | Gerar casos de teste | Fase 3 |

---

## Mapeamento: Tema -> Referencias

### 01-decision-tree

**Objetivo**: Mapear pergunta -> script correto

| Tipo | Recurso | Secao Relevante |
|------|---------|-----------------|
| Anthropic | [Skill best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) | "Set appropriate degrees of freedom" |
| Anthropic | [Skill best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) | "Avoid offering too many options" |
| Cookbook | [METAPROMPT.md](../cookbooks/METAPROMPT.md) | Gerar prompt otimizado para Decision Tree |

### 02-termos-ambiguos

**Objetivo**: Definir quando PERGUNTAR ao usuario

| Tipo | Recurso | Secao Relevante |
|------|---------|-----------------|
| Anthropic | [Claude 4 best practices](https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/claude-4-best-practices) | "Be Explicit and Specific" |
| Anthropic | [Skill best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) | "Use consistent terminology" |

### 03-manutencao-contexto

**Objetivo**: Instruir agente a manter estado em conversas

| Tipo | Recurso | Secao Relevante |
|------|---------|-----------------|
| Anthropic | [Effective harnesses](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) | "claude-progress.txt como memoria" |
| Anthropic | [Building agents SDK](https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk) | "Folder structure as context engineering" |
| Anthropic | [Managing context](https://anthropic.com/news/context-management) | "Memory tool for state persistence" |
| Cookbook | [CONTEXT_COMPACTION.md](../cookbooks/CONTEXT_COMPACTION.md) | Tecnicas de compactacao |
| Cookbook | [memory_cookbook](https://github.com/anthropics/claude-cookbooks/blob/main/tool_use/memory_cookbook.ipynb) | Implementacao de memoria |

### 04-examples-navegacao

**Objetivo**: Links de navegacao + exemplos produto-cliente

| Tipo | Recurso | Secao Relevante |
|------|---------|-----------------|
| Anthropic | [Skill best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) | "Progressive disclosure patterns" |
| Anthropic | [Skill best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) | "Structure longer reference files with TOC" |
| Cookbook | [03_skills_custom_development](https://github.com/anthropics/claude-cookbooks/blob/main/skills/notebooks/03_skills_custom_development.ipynb) | Estrutura de Skills |

### 05-description-skill

**Objetivo**: Atualizar description para ser mais especifica

| Tipo | Recurso | Secao Relevante |
|------|---------|-----------------|
| Anthropic | [Skill best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) | "Writing effective descriptions" |
| Anthropic | [Skill best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) | "Naming conventions" |

### Fase 3 - Testes

**Objetivo**: Validar implementacao

| Tipo | Recurso | Secao Relevante |
|------|---------|-----------------|
| Anthropic | [Skill best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) | "Test with all models you plan to use" |
| Anthropic | [Skill best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) | "Build evaluations first" |
| Cookbook | [BUILDING_EVALS.md](../cookbooks/BUILDING_EVALS.md) | Framework completo |
| Cookbook | [generate_test_cases](https://github.com/anthropics/claude-cookbooks/blob/main/misc/generate_test_cases.ipynb) | Gerar casos de teste |

---

## Citacoes Chave

### Sobre Decision Tree

> "Match the level of specificity to the task's fragility and variability."
> — Skill authoring best practices

### Sobre Termos Ambiguos

> "Use consistent terminology. Choose one term and use it throughout the Skill."
> — Skill authoring best practices

### Sobre Contexto

> "Os agentes devem manter um arquivo claude-progress.txt que funciona como 'memoria' entre sessoes."
> — Effective harnesses for long-running agents

> "The folder and file structure of an agent becomes a form of context engineering."
> — Building agents with Claude Agent SDK

### Sobre Description

> "The description field enables Skill discovery and should include both what the Skill does and when to use it."
> — Skill authoring best practices

### Sobre Testes

> "Create evaluations BEFORE writing extensive documentation. This ensures your Skill solves real problems."
> — Skill authoring best practices

---

## Historico

| Data | Alteracao | Autor |
|------|-----------|-------|
| 12/12/2025 | Criacao do documento | Claude |
