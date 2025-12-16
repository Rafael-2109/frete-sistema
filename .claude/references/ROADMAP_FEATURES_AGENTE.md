# ROADMAP DE FEATURES - AGENTE LOGISTICO

**Versao**: 1.2
**Data**: 03/12/2025
**Autor**: Claude Code (Pesquisa Profunda)
**Baseado em**: Documentacao Oficial Anthropic (Claude Agent SDK + Claude Code)

---

## SUMARIO

1. [Visao Geral](#1-visao-geral)
2. [Estado Atual da Implementacao](#2-estado-atual-da-implementacao)
3. [Catalogo Completo de Features](#3-catalogo-completo-de-features)
4. [Roadmap de Implementacao](#4-roadmap-de-implementacao)
5. [Especificacoes Tecnicas por Feature](#5-especificacoes-tecnicas-por-feature)
6. [Referencias Oficiais](#6-referencias-oficiais)

---

## 1. VISAO GERAL

### 1.1 Objetivo

Este documento cataloga todas as features disponiveis no Claude Agent SDK e Claude Code que podem ser implementadas na interface do Agente Logistico, organizadas em um roadmap de implementacao progressiva.

### 1.2 Fonte das Informacoes

| Fonte | URL | Conteudo |
|-------|-----|----------|
| Claude Code Docs | https://code.claude.com/docs/ | Features de UI, Hooks, Permissoes |
| Agent SDK | https://platform.claude.com/docs/en/agent-sdk/ | Streaming, Sessions, Tools |
| API Reference | https://docs.anthropic.com/en/api/ | Token Usage, Costs, Models |

### 1.3 Arquivos do Projeto Relacionados

| Arquivo | Funcao |
|---------|--------|
| `app/agente/routes.py` | Endpoints Flask (SSE streaming) |
| `app/agente/sdk/client.py` | Cliente do SDK (ClaudeAgentOptions) |
| `app/agente/sdk/cost_tracker.py` | Rastreamento de custos |
| `app/agente/templates/agente/chat.html` | Interface do chat |
| `app/agente/config/settings.py` | Configuracoes |
| `app/agente/config/permissions.py` | Callback de permissoes |

---

## 2. ESTADO ATUAL DA IMPLEMENTACAO

### 2.1 Features Ja Implementadas

| Feature | Status | Arquivo | Linha |
|---------|--------|---------|-------|
| Streaming SSE | :white_check_mark: Completo | routes.py | 84-96 |
| Session Management | :white_check_mark: Completo | client.py | 249-252 |
| Token Display | :white_check_mark: Admin only | chat.css | - |
| Cost Display | :white_check_mark: Admin only | chat.css | - |
| Tool Call Indicator | :white_check_mark: Basico | chat.js | - |
| Typing Indicator | :white_check_mark: Completo | chat.js | - |
| Modal Confirmacao | :white_check_mark: Basico | chat.html | - |
| Markdown Rendering | :white_check_mark: Basico | chat.js | - |
| Skills System | :white_check_mark: 8 skills | client.py | 262-268 |
| Permission Callback | :white_check_mark: Estrutura | client.py | 279-280 |
| Cost Tracker | :white_check_mark: Completo | cost_tracker.py | - |
| Health Check | :white_check_mark: Completo | routes.py | 255-285 |

### 2.2 FASE 1 - Implementada em 03/12/2025

| Feature | ID | Status | Arquivo |
|---------|-----|--------|---------|
| Seletor de Modelo | FEAT-001 | :white_check_mark: Completo | chat.html, routes.py, client.py |
| Toggle de Thinking | FEAT-002 | :white_check_mark: Completo | chat.html, routes.py, client.py |
| Painel de Thinking | FEAT-003 | :white_check_mark: Completo | chat.css, chat.js |
| Budget de Tokens Visual | FEAT-004 | :white_check_mark: Completo | chat.css, chat.js |
| Timeline de Acoes | FEAT-006 | :white_check_mark: Completo | chat.css, chat.js |
| Todo List Visual | FEAT-008 | :white_check_mark: Completo | chat.css, chat.js |

**Melhorias adicionais (03/12/2025):**
- Template modularizado (CSS e JS externos)
- Explicacao detalhada dos modelos com tooltips
- Extended Thinking com explicacao visual
- **CORRECAO**: Extended Thinking agora usa `max_thinking_tokens` (parametro correto do SDK)

### 2.3 FASE 2 - Implementada em 03/12/2025

| Feature | ID | Status | Arquivo |
|---------|-----|--------|---------|
| Barra de Progresso Geral | FEAT-009 | :white_check_mark: Completo | chat.html, chat.css, chat.js |
| Plan Mode Toggle | FEAT-010 | :white_check_mark: Completo | chat.html, chat.css, chat.js, routes.py, client.py |
| Markdown Avancado | FEAT-023 | :white_check_mark: Completo | chat.html, chat.css, chat.js |

**Melhorias adicionais (03/12/2025):**
- Barra de progresso geral sincronizada com Todo List
- Plan Mode com toggle visual e integracao backend
- Markdown avancado com marked.js + highlight.js (syntax highlighting)
- Tabelas estilizadas, blockquotes, codigo com cores

### 2.4 Gaps Restantes (Proximas Fases)

| Categoria | Implementado | Faltando |
|-----------|--------------|----------|
| Execucao | Streaming, Seletor Modelo, Thinking, Plan Mode | Dashboard Analytics |
| Metricas | Tokens/Custo, Budget Visual | - |
| Planejamento | Todo List, Timeline, Barra Progresso | - |
| Sessoes | Session ID | Lista Sessoes, Checkpoints |
| Aprovacao | Modal basico | Fila, Permissoes granulares |
| Transparencia | Timeline, Thinking Panel, Markdown Avancado | Diff Viewer |

---

## 3. CATALOGO COMPLETO DE FEATURES

### 3.1 EXECUCAO E CONTROLE DO AGENTE

#### 3.1.1 Seletor de Modelo

| Atributo | Valor |
|----------|-------|
| **ID** | FEAT-001 |
| **Nome** | Seletor de Modelo |
| **Descricao** | Dropdown para alternar entre Haiku, Sonnet e Opus |
| **Prioridade** | ALTA |
| **Complexidade** | Facil |
| **Tempo Estimado** | 30 minutos |
| **Dependencias** | Nenhuma |

**Modelos Disponiveis:**

| Alias | Model ID | Uso | Velocidade |
|-------|----------|-----|------------|
| haiku | claude-haiku-4-5-20251001 | Tarefas simples | Muito rapido |
| sonnet | claude-sonnet-4-5-20250929 | Equilibrado | Rapido |
| opus | claude-opus-4-5-20251101 | Complexo | Moderado |
| sonnet[1m] | claude-sonnet-4-5 (extended) | Contexto grande | Rapido |
| opusplan | Opus -> Sonnet | Planejamento hibrido | Variavel |

**Configuracao:**
```python
# Via SDK
options_dict["model"] = "claude-sonnet-4-5-20250929"

# Via CLI
claude --model sonnet
```

---

#### 3.1.2 Toggle de Extended Thinking

| Atributo | Valor |
|----------|-------|
| **ID** | FEAT-002 |
| **Nome** | Toggle de Thinking |
| **Descricao** | Switch para ativar/desativar pensamento profundo |
| **Prioridade** | ALTA |
| **Complexidade** | Facil |
| **Tempo Estimado** | 20 minutos |
| **Dependencias** | Nenhuma |

**Parametros:**

| Parametro | Tipo | Descricao |
|-----------|------|-----------|
| MAX_THINKING_TOKENS | number | Limite de tokens (10K-100K) |
| permission_mode | string | "plan" ativa thinking |

---

#### 3.1.3 Painel de Thinking

| Atributo | Valor |
|----------|-------|
| **ID** | FEAT-003 |
| **Nome** | Painel de Thinking |
| **Descricao** | Exibe o raciocinio do Claude em tempo real |
| **Prioridade** | MEDIA |
| **Complexidade** | Facil |
| **Tempo Estimado** | 15 minutos |
| **Dependencias** | FEAT-002 |

**Estilo Visual:**
- Background: #f8f9fa
- Border-left: 3px solid #667eea
- Font-style: italic
- Color: #666

---

#### 3.1.4 Budget de Tokens

| Atributo | Valor |
|----------|-------|
| **ID** | FEAT-004 |
| **Nome** | Budget de Tokens Visual |
| **Descricao** | Barra de progresso mostrando consumo vs limite |
| **Prioridade** | MEDIA |
| **Complexidade** | Facil |
| **Tempo Estimado** | 30 minutos |
| **Dependencias** | Nenhuma |

**Campos:**

| Campo | Tipo | Descricao |
|-------|------|-----------|
| input_tokens | int | Tokens de entrada |
| output_tokens | int | Tokens de saida |
| cache_read_tokens | int | Tokens do cache (90% desconto) |
| cache_creation_tokens | int | Tokens para criar cache |
| budget_total | int | Limite configurado |

---

### 3.2 OBSERVABILIDADE E METRICAS

#### 3.2.1 Dashboard de Metricas

| Atributo | Valor |
|----------|-------|
| **ID** | FEAT-005 |
| **Nome** | Dashboard de Metricas |
| **Descricao** | Painel com estatisticas da sessao |
| **Prioridade** | MEDIA |
| **Complexidade** | Media |
| **Tempo Estimado** | 2 horas |
| **Dependencias** | Nenhuma |

**Metricas Disponiveis:**

| Metrica | Unidade | Descricao |
|---------|---------|-----------|
| session.count | count | Sessoes iniciadas |
| lines_of_code.count | count | Linhas modificadas |
| cost.usage | USD | Custo da sessao |
| token.usage | tokens | Total de tokens |
| active_time.total | seconds | Tempo ativo |

---

#### 3.2.2 Timeline de Acoes

| Atributo | Valor |
|----------|-------|
| **ID** | FEAT-006 |
| **Nome** | Timeline de Acoes |
| **Descricao** | Historico visual de ferramentas usadas |
| **Prioridade** | ALTA |
| **Complexidade** | Media |
| **Tempo Estimado** | 1 hora |
| **Dependencias** | Nenhuma |

**Eventos Capturados:**

| Evento | Trigger | Dados |
|--------|---------|-------|
| tool_call | Inicio de ferramenta | tool_name, timestamp |
| tool_result | Fim de ferramenta | success, duration_ms |
| error | Falha | message, code |

---

#### 3.2.3 Console de Logs

| Atributo | Valor |
|----------|-------|
| **ID** | FEAT-007 |
| **Nome** | Console de Logs |
| **Descricao** | Aba com logs tecnicos, erros e avisos |
| **Prioridade** | BAIXA |
| **Complexidade** | Media |
| **Tempo Estimado** | 1.5 horas |
| **Dependencias** | Nenhuma |

**Niveis de Log:**
- ERROR (vermelho)
- WARNING (amarelo)
- INFO (azul)
- DEBUG (cinza)

---

### 3.3 PLANEJAMENTO E TO-DOS

#### 3.3.1 Todo List Visual

| Atributo | Valor |
|----------|-------|
| **ID** | FEAT-008 |
| **Nome** | Todo List Visual |
| **Descricao** | Exibe tarefas que o agente esta executando |
| **Prioridade** | ALTA |
| **Complexidade** | Media |
| **Tempo Estimado** | 1 hora |
| **Dependencias** | Nenhuma |

**Estrutura de Todo:**
```json
{
  "todos": [
    {
      "content": "Implementar autenticacao",
      "status": "pending|in_progress|completed",
      "activeForm": "Implementando autenticacao"
    }
  ]
}
```

**Estados:**

| Status | Icone | Cor |
|--------|-------|-----|
| pending | ○ | #6c757d |
| in_progress | ⏳ | #007bff |
| completed | ✓ | #28a745 |

---

#### 3.3.2 Barra de Progresso

| Atributo | Valor |
|----------|-------|
| **ID** | FEAT-009 |
| **Nome** | Barra de Progresso |
| **Descricao** | Progresso visual das tarefas |
| **Prioridade** | MEDIA |
| **Complexidade** | Facil |
| **Tempo Estimado** | 20 minutos |
| **Dependencias** | FEAT-008 |

---

#### 3.3.3 Plan Mode Toggle

| Atributo | Valor |
|----------|-------|
| **ID** | FEAT-010 |
| **Nome** | Plan Mode Toggle |
| **Descricao** | Modo somente leitura (dry-run) |
| **Prioridade** | MEDIA |
| **Complexidade** | Facil |
| **Tempo Estimado** | 30 minutos |
| **Dependencias** | Nenhuma |

**Comportamento em Plan Mode:**

| Permitido | Bloqueado |
|-----------|-----------|
| Leitura de arquivos | Edicao de arquivos |
| Listagem de diretorios | Execucao de comandos |
| Busca em codigo | Criacao de arquivos |
| Analise e planejamento | Delecao de arquivos |

---

### 3.4 SESSOES E CONTEXTO

#### 3.4.1 Lista de Sessoes

| Atributo | Valor |
|----------|-------|
| **ID** | FEAT-011 |
| **Nome** | Lista de Sessoes |
| **Descricao** | Conversas recentes com titulo e hora |
| **Prioridade** | MEDIA |
| **Complexidade** | Media |
| **Tempo Estimado** | 1.5 horas |
| **Dependencias** | Banco de dados |

**Campos por Sessao:**

| Campo | Tipo | Descricao |
|-------|------|-----------|
| session_id | string | ID unico |
| title | string | Titulo (auto-gerado) |
| created_at | datetime | Data de criacao |
| last_message | datetime | Ultima mensagem |
| message_count | int | Total de mensagens |
| total_cost | float | Custo acumulado |

---

#### 3.4.2 Checkpoints

| Atributo | Valor |
|----------|-------|
| **ID** | FEAT-012 |
| **Nome** | Checkpoints |
| **Descricao** | Pontos de salvamento para reverter |
| **Prioridade** | BAIXA |
| **Complexidade** | Complexa |
| **Tempo Estimado** | 3 horas |
| **Dependencias** | FEAT-011 |

**Opcoes de Reversao:**
1. Reverter apenas codigo (mantendo conversa)
2. Reverter apenas conversa (mantendo edicoes)
3. Restaurar ambos

**Limitacoes:**
- NAO rastreia modificacoes via bash
- NAO rastreia edicoes manuais fora do agente
- Funciona como "local undo" (nao substitui Git)
- Persistencia: 30 dias (configuravel)

---

#### 3.4.3 Resumo de Conversa

| Atributo | Valor |
|----------|-------|
| **ID** | FEAT-013 |
| **Nome** | Resumo de Conversa |
| **Descricao** | Botao para gerar resumo + proximos passos |
| **Prioridade** | BAIXA |
| **Complexidade** | Facil |
| **Tempo Estimado** | 30 minutos |
| **Dependencias** | Nenhuma |

---

### 3.5 SEGURANCA E APROVACOES

#### 3.5.1 Fila de Aprovacoes

| Atributo | Valor |
|----------|-------|
| **ID** | FEAT-014 |
| **Nome** | Fila de Aprovacoes |
| **Descricao** | Lista de acoes pendentes de aprovacao |
| **Prioridade** | MEDIA |
| **Complexidade** | Complexa |
| **Tempo Estimado** | 2 horas |
| **Dependencias** | Nenhuma |

**Decisoes Possiveis:**

| Decisao | Efeito |
|---------|--------|
| approve | Permite execucao |
| deny | Bloqueia execucao |
| always_approve | Permite sempre esta ferramenta |

---

#### 3.5.2 Perfis de Seguranca

| Atributo | Valor |
|----------|-------|
| **ID** | FEAT-015 |
| **Nome** | Perfis de Seguranca |
| **Descricao** | Modos: Leitor, Operador, Admin |
| **Prioridade** | BAIXA |
| **Complexidade** | Media |
| **Tempo Estimado** | 1.5 horas |
| **Dependencias** | FEAT-014 |

**Modos de Permissao:**

| Modo | Comportamento |
|------|---------------|
| default | Pede confirmacao na 1a vez |
| plan | Somente leitura (dry-run) |
| acceptEdits | Auto-aceita edicoes |
| bypassPermissions | Ignora prompts (CI/CD) |

---

#### 3.5.3 Trilha de Auditoria

| Atributo | Valor |
|----------|-------|
| **ID** | FEAT-016 |
| **Nome** | Trilha de Auditoria |
| **Descricao** | Historico de aprovacoes/rejeicoes |
| **Prioridade** | BAIXA |
| **Complexidade** | Media |
| **Tempo Estimado** | 1.5 horas |
| **Dependencias** | FEAT-014, Banco de dados |

---

### 3.6 SKILLS E SUBAGENTES

#### 3.6.1 Catalogo de Skills

| Atributo | Valor |
|----------|-------|
| **ID** | FEAT-017 |
| **Nome** | Catalogo de Skills |
| **Descricao** | Lista de skills com toggle ligar/desligar |
| **Prioridade** | BAIXA |
| **Complexidade** | Media |
| **Tempo Estimado** | 1 hora |
| **Dependencias** | Nenhuma |

**Skills Atuais:**

| Skill | Descricao |
|-------|-----------|
| gerindo-expedicao | Separacoes e estoque |
| rastreando-odoo | Rastreamento de fluxos documentais (NF, PO, SO, titulos, conciliacoes) |
| descobrindo-odoo-estrutura | Exploracao de modelos nao mapeados |
| integracao-odoo | Desenvolvimento de integracoes |

---

#### 3.6.2 Seletor de Subagente

| Atributo | Valor |
|----------|-------|
| **ID** | FEAT-018 |
| **Nome** | Seletor de Subagente |
| **Descricao** | Escolher tipo de agente especializado |
| **Prioridade** | BAIXA |
| **Complexidade** | Media |
| **Tempo Estimado** | 1 hora |
| **Dependencias** | Nenhuma |

**Tipos Disponiveis:**

| Tipo | Uso | Tools |
|------|-----|-------|
| general-purpose | Tarefas complexas | Todas |
| Explore | Explorar codebase | Glob, Grep, Read |
| Plan | Arquitetura | Todas |

---

#### 3.6.3 Command Palette

| Atributo | Valor |
|----------|-------|
| **ID** | FEAT-019 |
| **Nome** | Command Palette |
| **Descricao** | Interface para slash commands com autocomplete |
| **Prioridade** | BAIXA |
| **Complexidade** | Media |
| **Tempo Estimado** | 1.5 horas |
| **Dependencias** | Nenhuma |

**Comandos Built-in:**

| Comando | Descricao |
|---------|-----------|
| /help | Ajuda geral |
| /cost | Uso de tokens |
| /model [nome] | Trocar modelo |
| /clear | Limpar historico |
| /compact | Compactar conversa |

---

### 3.7 TRANSPARENCIA E EXPLICACAO

#### 3.7.1 Botao "Por que voce respondeu isso?"

| Atributo | Valor |
|----------|-------|
| **ID** | FEAT-020 |
| **Nome** | Explicacao de Resposta |
| **Descricao** | Botao para explicar logica e dados usados |
| **Prioridade** | BAIXA |
| **Complexidade** | Facil |
| **Tempo Estimado** | 30 minutos |
| **Dependencias** | Nenhuma |

---

#### 3.7.2 Modo Professor

| Atributo | Valor |
|----------|-------|
| **ID** | FEAT-021 |
| **Nome** | Modo Professor |
| **Descricao** | Respostas com explicacao didatica |
| **Prioridade** | BAIXA |
| **Complexidade** | Facil |
| **Tempo Estimado** | 20 minutos |
| **Dependencias** | Nenhuma |

---

#### 3.7.3 Diff Viewer

| Atributo | Valor |
|----------|-------|
| **ID** | FEAT-022 |
| **Nome** | Diff Viewer |
| **Descricao** | Antes/depois de edicoes com Aplicar/Desfazer |
| **Prioridade** | MEDIA |
| **Complexidade** | Complexa |
| **Tempo Estimado** | 2 horas |
| **Dependencias** | Nenhuma |

---

### 3.8 INTERFACE E EXPERIENCIA

#### 3.8.1 Markdown Avancado

| Atributo | Valor |
|----------|-------|
| **ID** | FEAT-023 |
| **Nome** | Markdown Avancado |
| **Descricao** | Syntax highlighting, tabelas, mermaid |
| **Prioridade** | MEDIA |
| **Complexidade** | Media |
| **Tempo Estimado** | 1 hora |
| **Dependencias** | Biblioteca (marked.js, highlight.js) |

---

#### 3.8.2 Temas (Dark Mode)

| Atributo | Valor |
|----------|-------|
| **ID** | FEAT-024 |
| **Nome** | Dark Mode |
| **Descricao** | Tema escuro para o chat |
| **Prioridade** | BAIXA |
| **Complexidade** | Facil |
| **Tempo Estimado** | 45 minutos |
| **Dependencias** | Nenhuma |

---

#### 3.8.3 Notificacoes

| Atributo | Valor |
|----------|-------|
| **ID** | FEAT-025 |
| **Nome** | Sistema de Notificacoes |
| **Descricao** | Toasts para eventos importantes |
| **Prioridade** | BAIXA |
| **Complexidade** | Facil |
| **Tempo Estimado** | 30 minutos |
| **Dependencias** | Nenhuma |

---

## 4. ROADMAP DE IMPLEMENTACAO

### 4.1 Visao Geral das Fases

```
FASE 1 (Sprint 1)     FASE 2 (Sprint 2)     FASE 3 (Sprint 3)     FASE 4 (Sprint 4)
    |                     |                     |                     |
    v                     v                     v                     v
+----------+         +----------+         +----------+         +----------+
| Controle |         |Planejam. |         | Sessoes  |         | Avancado |
|  Basico  |         | e Acoes  |         |e Segment.|         |          |
+----------+         +----------+         +----------+         +----------+
| FEAT-001 |         | FEAT-006 |         | FEAT-011 |         | FEAT-017 |
| FEAT-002 |         | FEAT-008 |         | FEAT-012 |         | FEAT-018 |
| FEAT-003 |         | FEAT-009 |         | FEAT-014 |         | FEAT-019 |
| FEAT-004 |         | FEAT-010 |         | FEAT-015 |         | FEAT-022 |
| FEAT-005 |         | FEAT-023 |         | FEAT-016 |         | FEAT-024 |
+----------+         +----------+         +----------+         +----------+
   ~4.5h                ~5h                  ~9h                  ~6h
```

---

### 4.2 FASE 1: Controle Basico (Sprint 1) - :white_check_mark: CONCLUIDA

**Objetivo:** Dar ao usuario controle sobre modelo e modo de operacao

**Data de Conclusao:** 03/12/2025

| Ordem | Feature | ID | Tempo | Status |
|-------|---------|-----|-------|--------|
| 1 | Seletor de Modelo | FEAT-001 | 30 min | :white_check_mark: Concluido |
| 2 | Toggle de Thinking | FEAT-002 | 20 min | :white_check_mark: Concluido |
| 3 | Painel de Thinking | FEAT-003 | 15 min | :white_check_mark: Concluido |
| 4 | Budget de Tokens Visual | FEAT-004 | 30 min | :white_check_mark: Concluido |
| 5 | Timeline de Acoes | FEAT-006 | 1h | :white_check_mark: Concluido |
| 6 | Todo List Visual | FEAT-008 | 1h | :white_check_mark: Concluido |

**Entregaveis:**
- [x] Dropdown de selecao de modelo no header com tooltips explicativos
- [x] Switch de Extended Thinking com explicacao visual
- [x] Painel colapsavel para exibir thinking em tempo real
- [x] Barra de progresso de tokens (admin only)
- [x] Timeline de acoes lateral
- [x] Todo list visual com progresso

**Criterios de Aceite:** :white_check_mark: TODOS ATENDIDOS
- Usuario pode alternar entre Haiku/Sonnet/Opus com explicacoes
- Thinking pode ser ativado/desativado com feedback visual
- Raciocinio do Claude e exibido quando ativado
- Consumo de tokens e visivel em tempo real

---

### 4.3 FASE 2: Planejamento e Acoes (Sprint 2) - :white_check_mark: CONCLUIDA

**Objetivo:** Transparencia sobre o que o agente esta fazendo

**Data de Conclusao:** 03/12/2025

| Ordem | Feature | ID | Tempo | Status |
|-------|---------|-----|-------|--------|
| 1 | Timeline de Acoes | FEAT-006 | 1h | :white_check_mark: Movido para FASE 1 |
| 2 | Todo List Visual | FEAT-008 | 1h | :white_check_mark: Movido para FASE 1 |
| 3 | Barra de Progresso | FEAT-009 | 20 min | :white_check_mark: Concluido |
| 4 | Plan Mode Toggle | FEAT-010 | 30 min | :white_check_mark: Concluido |
| 5 | Markdown Avancado | FEAT-023 | 1h | :white_check_mark: Concluido |

**Entregaveis:**
- [x] Timeline visual de ferramentas executadas (FASE 1)
- [x] Lista de tarefas com estados (FASE 1)
- [x] Barra de progresso geral sincronizada com Todo List
- [x] Toggle para modo dry-run (Plan Mode) com integracao backend
- [x] Syntax highlighting com highlight.js e tabelas estilizadas

**Criterios de Aceite:** :white_check_mark: TODOS ATENDIDOS
- Cada tool call aparece na timeline com status :white_check_mark:
- Tarefas do agente sao visiveis em tempo real :white_check_mark:
- Progresso geral e calculado automaticamente :white_check_mark:
- Plan mode bloqueia acoes destrutivas :white_check_mark:

---

### 4.4 FASE 3: Sessoes e Seguranca (Sprint 3) - EM ANDAMENTO

**Objetivo:** Persistencia e controle de acesso

**Duracao Estimada:** 9 horas

| Ordem | Feature | ID | Tempo | Status |
|-------|---------|-----|-------|--------|
| 1 | Lista de Sessoes | FEAT-011 | 1.5h | :white_check_mark: Concluido (03/12/2025) |
| 2 | Checkpoints | FEAT-012 | 3h | :arrow_right: Movido para Backlog |
| 3 | Fila de Aprovacoes | FEAT-014 | 2h | Pendente |
| 4 | Perfis de Seguranca | FEAT-015 | 1.5h | Pendente |
| 5 | Trilha de Auditoria | FEAT-016 | 1.5h | Pendente |

**Entregaveis:**
- [x] Sidebar colapsavel com conversas anteriores (FEAT-011)
- [x] Modelo SQLAlchemy AgentSession
- [x] API endpoints: GET/DELETE/PUT sessions
- [x] Persistencia automatica de sessoes
- [ ] Sistema de checkpoints com reversao (movido para backlog)
- [ ] Modal de aprovacao com fila
- [ ] Seletor de perfil (Leitor/Operador/Admin)
- [ ] Log de auditoria por sessao

**Criterios de Aceite FEAT-011:** :white_check_mark: ATENDIDO
- Sessoes anteriores podem ser retomadas via sidebar
- Usuario pode renomear e excluir sessoes
- Sessoes sao persistidas automaticamente no banco

**Dependencias:**
- [x] Tabela agent_sessions no banco de dados
- [ ] Tabela de auditoria
- [ ] Integracao com sistema de usuarios (para perfis)

---

### 4.5 FASE 4: Features Avancadas (Sprint 4)

**Objetivo:** Experiencia completa e polida

**Duracao Estimada:** 6 horas

| Ordem | Feature | ID | Tempo | Prioridade |
|-------|---------|-----|-------|------------|
| 1 | Catalogo de Skills | FEAT-017 | 1h | BAIXA |
| 2 | Seletor de Subagente | FEAT-018 | 1h | BAIXA |
| 3 | Command Palette | FEAT-019 | 1.5h | BAIXA |
| 4 | Diff Viewer | FEAT-022 | 2h | MEDIA |
| 5 | Dark Mode | FEAT-024 | 45 min | BAIXA |

**Entregaveis:**
- [ ] Interface de gerenciamento de skills
- [ ] Dropdown de tipo de agente
- [ ] Autocomplete para /comandos
- [ ] Visualizador de diferencas
- [ ] Tema escuro

**Criterios de Aceite:**
- Skills podem ser habilitadas/desabilitadas
- Tipo de agente pode ser alterado
- Comandos tem autocomplete funcional
- Diffs sao exibidos lado a lado
- Tema escuro e funcional e persistente

---

### 4.6 Backlog (Pos-MVP)

| Feature | ID | Tempo | Notas |
|---------|-----|-------|-------|
| Checkpoints | FEAT-012 | 3h | Complexo, baixo ROI - movido da FASE 3 |
| Console de Logs | FEAT-007 | 1.5h | Debug avancado |
| Resumo de Conversa | FEAT-013 | 30 min | Utility |
| Explicacao de Resposta | FEAT-020 | 30 min | Transparencia |
| Modo Professor | FEAT-021 | 20 min | Educacional |
| Notificacoes | FEAT-025 | 30 min | UX |

---

## 5. ESPECIFICACOES TECNICAS POR FEATURE

### 5.1 FEAT-001: Seletor de Modelo

#### Frontend (chat.html)

```html
<!-- Adicionar no .chat-header apos status-badge -->
<div class="model-selector-container ms-3">
    <select id="model-selector" class="form-select form-select-sm">
        <option value="claude-haiku-4-5-20251001">Haiku (Rapido)</option>
        <option value="claude-sonnet-4-5-20250929" selected>Sonnet (Equilibrado)</option>
        <option value="claude-opus-4-5-20251101">Opus (Potente)</option>
    </select>
</div>

<style>
.model-selector-container {
    min-width: 150px;
}
.model-selector-container select {
    background: rgba(255,255,255,0.1);
    border: 1px solid rgba(255,255,255,0.3);
    color: white;
    font-size: 0.85rem;
}
.model-selector-container select option {
    color: #333;
    background: white;
}
</style>

<script>
let currentModel = 'claude-sonnet-4-5-20250929';

document.getElementById('model-selector').addEventListener('change', function() {
    currentModel = this.value;
    // Opcional: notificar backend
    updateModelSetting(currentModel);
});

function updateModelSetting(model) {
    fetch('/agente/api/settings', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
        },
        body: JSON.stringify({ model: model })
    });
}

// Incluir modelo na requisicao de chat
body: JSON.stringify({
    message: message,
    session_id: sessionId,
    model: currentModel  // ADICIONAR
})
</script>
```

#### Backend (routes.py)

```python
@agente_bp.route('/api/settings', methods=['POST'])
@login_required
def api_settings():
    """Atualiza configuracoes da sessao."""
    data = request.get_json()
    model = data.get('model')

    if model and model in [
        'claude-haiku-4-5-20251001',
        'claude-sonnet-4-5-20250929',
        'claude-opus-4-5-20251101'
    ]:
        # Armazenar em sessao Flask
        session['agent_model'] = model
        return jsonify({'success': True, 'model': model})

    return jsonify({'success': False, 'error': 'Modelo invalido'}), 400
```

#### Modificar client.py

```python
def _build_options(self, model: str = None, ...):
    # Usar modelo passado ou default
    options_dict["model"] = model or self.settings.model
```

---

### 5.2 FEAT-002: Toggle de Thinking

#### Frontend (chat.html)

```html
<!-- Adicionar apos model-selector -->
<div class="thinking-toggle-container ms-3 d-flex align-items-center">
    <div class="form-check form-switch mb-0">
        <input class="form-check-input" type="checkbox" id="thinking-toggle">
        <label class="form-check-label text-white" for="thinking-toggle" title="Extended Thinking">
            <i class="fas fa-brain"></i>
        </label>
    </div>
</div>

<style>
.thinking-toggle-container .form-check-input:checked {
    background-color: #ffc107;
    border-color: #ffc107;
}
</style>

<script>
let thinkingEnabled = false;

document.getElementById('thinking-toggle').addEventListener('change', function() {
    thinkingEnabled = this.checked;

    // Feedback visual
    const label = this.nextElementSibling;
    label.style.opacity = this.checked ? '1' : '0.6';
});

// Incluir na requisicao
body: JSON.stringify({
    message: message,
    session_id: sessionId,
    model: currentModel,
    thinking_enabled: thinkingEnabled  // ADICIONAR
})
</script>
```

#### Backend (routes.py)

```python
def _stream_chat_response(..., thinking_enabled: bool = False):
    # Passar para o cliente
    async for event in client.stream_response(
        prompt=message,
        session_id=sdk_session_id,
        user_name=user_name,
        can_use_tool=can_use_tool,
        thinking_enabled=thinking_enabled,  # ADICIONAR
    ):
```

#### Modificar client.py

```python
def _build_options(self, thinking_enabled: bool = False, ...):
    if thinking_enabled:
        options_dict["permission_mode"] = "plan"  # Ativa thinking
        # Ou configurar budget especifico
        # options_dict["thinking_budget"] = 50000
```

---

### 5.3 FEAT-003: Painel de Thinking

#### Frontend (chat.html)

```html
<!-- Adicionar apos typing-container -->
<div id="thinking-panel" class="thinking-panel px-4 pb-2" style="display: none;">
    <div class="d-flex align-items-start">
        <div class="message-avatar thinking-avatar me-3">
            <i class="fas fa-brain"></i>
        </div>
        <div class="thinking-content">
            <div class="thinking-header">
                <small class="text-muted">
                    <i class="fas fa-lightbulb me-1"></i>
                    Pensando...
                </small>
                <button class="btn btn-sm btn-link p-0 ms-2" onclick="toggleThinkingPanel()">
                    <i class="fas fa-chevron-up" id="thinking-toggle-icon"></i>
                </button>
            </div>
            <div class="thinking-body" id="thinking-text"></div>
        </div>
    </div>
</div>

<style>
.thinking-panel {
    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
    border-left: 4px solid #667eea;
    margin: 0 1rem 1rem;
    border-radius: 0 8px 8px 0;
}

.thinking-avatar {
    width: 32px;
    height: 32px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 0.9rem;
}

.thinking-content {
    flex: 1;
    min-width: 0;
}

.thinking-header {
    display: flex;
    align-items: center;
    margin-bottom: 8px;
}

.thinking-body {
    font-style: italic;
    color: #495057;
    font-size: 0.9rem;
    max-height: 200px;
    overflow-y: auto;
    padding-right: 8px;
}

.thinking-body::-webkit-scrollbar {
    width: 4px;
}

.thinking-body::-webkit-scrollbar-thumb {
    background: #adb5bd;
    border-radius: 2px;
}
</style>

<script>
let thinkingCollapsed = false;

function toggleThinkingPanel() {
    const body = document.getElementById('thinking-text');
    const icon = document.getElementById('thinking-toggle-icon');

    thinkingCollapsed = !thinkingCollapsed;
    body.style.display = thinkingCollapsed ? 'none' : 'block';
    icon.className = thinkingCollapsed ? 'fas fa-chevron-down' : 'fas fa-chevron-up';
}

function showThinking(content) {
    const panel = document.getElementById('thinking-panel');
    const text = document.getElementById('thinking-text');

    panel.style.display = 'block';
    text.innerHTML += formatMessage(content);
    text.scrollTop = text.scrollHeight;
}

function clearThinking() {
    document.getElementById('thinking-panel').style.display = 'none';
    document.getElementById('thinking-text').innerHTML = '';
}

// No processSSEEvent:
case 'thinking':
    showThinking(data.content);
    break;
</script>
```

---

### 5.4 FEAT-006: Timeline de Acoes

#### Frontend (chat.html)

```html
<!-- Adicionar como sidebar ou section colapsavel -->
<div id="action-timeline-container" class="action-timeline-container">
    <div class="timeline-header" onclick="toggleTimeline()">
        <span><i class="fas fa-history me-2"></i>Acoes</span>
        <span class="badge bg-secondary" id="action-count">0</span>
    </div>
    <div class="timeline-body" id="timeline-body">
        <div class="timeline-empty text-muted text-center py-3">
            <i class="fas fa-clock"></i>
            <p class="mb-0 mt-2">Nenhuma acao ainda</p>
        </div>
        <div id="timeline-items"></div>
    </div>
</div>

<style>
.action-timeline-container {
    position: fixed;
    right: 20px;
    top: 100px;
    width: 280px;
    background: white;
    border-radius: 12px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    z-index: 100;
    max-height: 400px;
    overflow: hidden;
}

.timeline-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 12px 16px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    cursor: pointer;
}

.timeline-body {
    max-height: 340px;
    overflow-y: auto;
}

.timeline-item {
    display: flex;
    padding: 10px 16px;
    border-bottom: 1px solid #f0f0f0;
    align-items: flex-start;
}

.timeline-item:last-child {
    border-bottom: none;
}

.timeline-icon {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-right: 12px;
    flex-shrink: 0;
}

.timeline-icon.pending {
    background: #fff3cd;
    color: #856404;
}

.timeline-icon.success {
    background: #d4edda;
    color: #155724;
}

.timeline-icon.error {
    background: #f8d7da;
    color: #721c24;
}

.timeline-info {
    flex: 1;
    min-width: 0;
}

.timeline-info .tool-name {
    font-weight: 600;
    font-size: 0.9rem;
    margin-bottom: 2px;
}

.timeline-info .tool-details {
    font-size: 0.75rem;
    color: #6c757d;
}

.timeline-info .tool-duration {
    font-size: 0.7rem;
    color: #adb5bd;
}
</style>

<script>
const actionTimeline = [];

function addTimelineItem(action) {
    actionTimeline.unshift(action);  // Mais recente primeiro
    renderTimeline();

    document.getElementById('action-count').textContent = actionTimeline.length;
    document.querySelector('.timeline-empty').style.display = 'none';
}

function updateLastTimelineItem(updates) {
    if (actionTimeline.length > 0) {
        Object.assign(actionTimeline[0], updates);
        renderTimeline();
    }
}

function renderTimeline() {
    const container = document.getElementById('timeline-items');

    container.innerHTML = actionTimeline.slice(0, 20).map(a => `
        <div class="timeline-item">
            <div class="timeline-icon ${a.status}">
                ${a.status === 'success' ? '<i class="fas fa-check"></i>' :
                  a.status === 'error' ? '<i class="fas fa-times"></i>' :
                  '<i class="fas fa-spinner fa-spin"></i>'}
            </div>
            <div class="timeline-info">
                <div class="tool-name">${formatToolName(a.tool_name)}</div>
                <div class="tool-details">${a.details || ''}</div>
                ${a.duration_ms ? `<div class="tool-duration">${a.duration_ms}ms</div>` : ''}
            </div>
        </div>
    `).join('');
}

function formatToolName(name) {
    const icons = {
        'Bash': '<i class="fas fa-terminal me-1"></i>',
        'Read': '<i class="fas fa-file-alt me-1"></i>',
        'Skill': '<i class="fas fa-magic me-1"></i>',
        'Glob': '<i class="fas fa-search me-1"></i>',
        'Grep': '<i class="fas fa-filter me-1"></i>',
    };
    return (icons[name] || '<i class="fas fa-cog me-1"></i>') + name;
}

function toggleTimeline() {
    const body = document.getElementById('timeline-body');
    body.style.display = body.style.display === 'none' ? 'block' : 'none';
}

// No processSSEEvent:
case 'tool_call':
    addTimelineItem({
        tool_name: data.tool_name || data.content,
        status: 'pending',
        details: data.tool_id ? `ID: ${data.tool_id.slice(0, 8)}...` : '',
        timestamp: new Date()
    });
    break;

case 'tool_result':
    updateLastTimelineItem({
        status: 'success',
        duration_ms: data.duration_ms || 0
    });
    break;
</script>
```

---

### 5.5 FEAT-008: Todo List Visual

#### Frontend (chat.html)

```html
<!-- Adicionar abaixo da timeline ou em sidebar separada -->
<div id="todo-panel" class="todo-panel" style="display: none;">
    <div class="todo-header">
        <span><i class="fas fa-tasks me-2"></i>Tarefas</span>
        <span class="badge bg-primary" id="todo-progress-badge">0%</span>
    </div>
    <div class="todo-body">
        <ul id="todo-list" class="todo-list"></ul>
        <div class="todo-progress-container">
            <div class="progress">
                <div class="progress-bar progress-bar-striped progress-bar-animated"
                     id="todo-progress-bar"
                     role="progressbar"
                     style="width: 0%">
                </div>
            </div>
        </div>
    </div>
</div>

<style>
.todo-panel {
    position: fixed;
    right: 20px;
    top: 520px;  /* Abaixo da timeline */
    width: 280px;
    background: white;
    border-radius: 12px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    z-index: 100;
}

.todo-header {
    background: #28a745;
    color: white;
    padding: 12px 16px;
    border-radius: 12px 12px 0 0;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.todo-body {
    padding: 12px;
}

.todo-list {
    list-style: none;
    padding: 0;
    margin: 0 0 12px;
    max-height: 200px;
    overflow-y: auto;
}

.todo-item {
    display: flex;
    align-items: flex-start;
    padding: 8px 0;
    border-bottom: 1px solid #f0f0f0;
}

.todo-item:last-child {
    border-bottom: none;
}

.todo-status {
    width: 24px;
    height: 24px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-right: 10px;
    flex-shrink: 0;
    font-size: 0.75rem;
}

.todo-status.pending {
    background: #e9ecef;
    color: #6c757d;
}

.todo-status.in_progress {
    background: #cce5ff;
    color: #004085;
}

.todo-status.completed {
    background: #d4edda;
    color: #155724;
}

.todo-content {
    flex: 1;
    font-size: 0.85rem;
}

.todo-content.in_progress {
    font-weight: 600;
}

.todo-content.completed {
    text-decoration: line-through;
    color: #6c757d;
}

.todo-progress-container {
    padding-top: 8px;
    border-top: 1px solid #f0f0f0;
}

.todo-progress-container .progress {
    height: 8px;
    border-radius: 4px;
}
</style>

<script>
let currentTodos = [];

function updateTodoList(todos) {
    currentTodos = todos;
    const list = document.getElementById('todo-list');
    const progressBar = document.getElementById('todo-progress-bar');
    const progressBadge = document.getElementById('todo-progress-badge');
    const panel = document.getElementById('todo-panel');

    // Mostrar painel se houver todos
    if (todos.length > 0) {
        panel.style.display = 'block';
    }

    // Renderizar lista
    list.innerHTML = todos.map(todo => `
        <li class="todo-item">
            <span class="todo-status ${todo.status}">
                ${todo.status === 'completed' ? '<i class="fas fa-check"></i>' :
                  todo.status === 'in_progress' ? '<i class="fas fa-spinner fa-spin"></i>' :
                  '<i class="fas fa-circle"></i>'}
            </span>
            <span class="todo-content ${todo.status}">
                ${todo.status === 'in_progress' ? todo.activeForm : todo.content}
            </span>
        </li>
    `).join('');

    // Calcular progresso
    const completed = todos.filter(t => t.status === 'completed').length;
    const percent = todos.length > 0 ? Math.round((completed / todos.length) * 100) : 0;

    progressBar.style.width = percent + '%';
    progressBadge.textContent = percent + '%';

    // Cor do badge baseada no progresso
    progressBadge.className = 'badge ' + (
        percent === 100 ? 'bg-success' :
        percent > 50 ? 'bg-info' : 'bg-primary'
    );
}

// No processSSEEvent, adicionar:
case 'todos':
    updateTodoList(data.todos);
    break;
</script>
```

#### Backend - Emitir evento de todos

O agente ja usa TodoWrite internamente. Para exibir na UI, precisamos capturar quando o tool e chamado e emitir um evento SSE.

```python
# Em routes.py, no processamento de tool_result
if event.type == 'tool_result' and event.metadata.get('tool_name') == 'TodoWrite':
    # Parsear resultado e emitir evento de todos
    try:
        todos = json.loads(event.content)
        event_queue.put(_sse_event('todos', {'todos': todos.get('todos', [])}))
    except:
        pass
```

---

## 6. REFERENCIAS OFICIAIS

### 6.1 Documentacao Claude Code

| Recurso | URL |
|---------|-----|
| Claude Code Docs Map | https://code.claude.com/docs/en/claude_code_docs_map.md |
| Hooks Guide | https://code.claude.com/docs/en/hooks-guide.md |
| Hooks Reference | https://code.claude.com/docs/en/hooks.md |
| IAM & Permissions | https://code.claude.com/docs/en/iam.md |
| Security | https://code.claude.com/docs/en/security.md |
| Monitoring Usage | https://code.claude.com/docs/en/monitoring-usage.md |
| Costs | https://code.claude.com/docs/en/costs.md |
| Analytics | https://code.claude.com/docs/en/analytics.md |
| Checkpointing | https://code.claude.com/docs/en/checkpointing.md |
| Headless Mode | https://code.claude.com/docs/en/headless.md |
| Memory | https://code.claude.com/docs/en/memory.md |
| Common Workflows | https://code.claude.com/docs/en/common-workflows.md |
| Slash Commands | https://code.claude.com/docs/en/slash-commands.md |

### 6.2 Documentacao Agent SDK

| Recurso | URL |
|---------|-----|
| Agent SDK Overview | https://platform.claude.com/docs/en/agent-sdk/ |
| Skills | https://platform.claude.com/docs/en/agent-sdk/skills |
| Sessions | https://platform.claude.com/docs/en/agent-sdk/sessions |
| Streaming | https://platform.claude.com/docs/en/agent-sdk/streaming-vs-single-mode |
| Permissions | https://platform.claude.com/docs/en/agent-sdk/permissions |
| Cost Tracking | https://platform.claude.com/docs/en/agent-sdk/cost-tracking |
| MCP Integration | https://platform.claude.com/docs/en/agent-sdk/mcp-integration |
| System Prompts | https://platform.claude.com/docs/en/agent-sdk/modifying-system-prompts |

### 6.3 API Reference

| Recurso | URL |
|---------|-----|
| Messages API | https://docs.anthropic.com/en/api/messages |
| Streaming | https://docs.anthropic.com/en/api/streaming |
| Tool Use | https://docs.anthropic.com/en/docs/build-with-claude/tool-use |
| Extended Thinking | https://docs.anthropic.com/en/docs/build-with-claude/extended-thinking |
| Vision | https://docs.anthropic.com/en/docs/build-with-claude/vision |

---

## HISTORICO DE REVISOES

| Versao | Data | Autor | Descricao |
|--------|------|-------|-----------|
| 1.0 | 02/12/2025 | Claude Code | Documento inicial |
| 1.1 | 03/12/2025 | Claude Code | FASE 1 concluida: Seletor Modelo, Thinking, Budget, Timeline, Todo List. Template modularizado. |
| 1.2 | 03/12/2025 | Claude Code | FASE 2 concluida: Barra Progresso, Plan Mode, Markdown Avancado. Correcao Extended Thinking (max_thinking_tokens). |
| 1.3 | 03/12/2025 | Claude Code | FASE 3 iniciada: FEAT-011 (Lista de Sessoes) concluido com sidebar colapsavel, modelo AgentSession, API endpoints e persistencia automatica. FEAT-012 (Checkpoints) movido para backlog. Correcao de app context para threads. |
| 1.4 | 03/12/2025 | Claude Code | FEAT-024 (Layout Otimizado): Layout compacto maximizando area de chat (removido max-height, reduzido paddings). Timeline agora mostra descricoes amigaveis em vez de nomes de ferramentas (ex: "Lendo arquivo.py" em vez de "Read"). SDK emite eventos de TodoWrite para sincronizar lista de tarefas. |
| 2.0 | 03/12/2025 | Claude Code | FEAT-025 (Layout Fullscreen): Chat ocupa 100% da tela (position fixed, menos navbar). Sidebar de sessoes substituida por Modal centralizado. Header redesenhado com controles inline (modelo, thinking, plan mode). Toggles estilizados. CSS completamente reescrito para layout moderno. |
| 2.1 | 03/12/2025 | Claude Code | FEAT-026 (UX Melhorias): Tooltips hover nos controles do header. Input mudado para textarea com auto-resize. Shift+Enter = nova linha, Enter = envia. Botao Stop para interromper geracao (vermelho pulsante). Limite de 2000 caracteres. |
| 2.2 | 03/12/2025 | Claude Code | FEAT-027 (Layout Compacto): Removido max-width do chat (usa tela toda). Mensagens alinhadas a esquerda. Reduzido paddings (header, mensagens, input). Botao de fechar (X) nos paineis de Timeline e Todo. Avatares menores (30px). Paineis compactados. |
| 2.3 | 03/12/2025 | Claude Code | FEAT-028 (Upload/Download Arquivos): Botao de anexar (📎) no input. Upload de PDF, XLSX, CSV, imagens. Limite 10MB. Storage temporario por sessao. Area de anexos e downloads acima do input. Deteccao automatica de URLs de arquivos nas respostas. Endpoints: /api/upload, /api/files. |

---

## PROXIMOS PASSOS

Para iniciar a implementacao, siga esta ordem:

1. **Revisar este documento** - Confirmar se as prioridades estao corretas
2. **Criar branch** - `git checkout -b feature/agente-ui-improvements`
3. **Implementar FASE 1** - Comece por FEAT-001 (Seletor de Modelo)
4. **Testar cada feature** - Validar antes de prosseguir
5. **Commit por feature** - Manter historico limpo
6. **Code review** - Revisar antes de merge

**Comando para iniciar:**
```bash
git checkout -b feature/agente-ui-fase1
```

---

*Documento gerado automaticamente por Claude Code em 02/12/2025*
