# AJUSTES - Skill gerindo-expedicao

**Data**: 10/12/2025
**Origem**: Analise de falha de comportamento do Agent SDK com usuario Stephanie
**Documento de referencia**: `app/agente/falha_conversa.md`

---

## 1. CONTEXTO DO PROBLEMA

### O Que Aconteceu

A usuaria Stephanie fez 4 perguntas sequenciais sobre o **mesmo contexto** (Atacadao 183):

| MSG | Pergunta | Esperado | O que o Agente Fez |
|-----|----------|----------|-------------------|
| #1 | "quantas caixa de ketchup tem pendentes para entregar no atacadao 183" | Consultar carteira do Atacadao 183, filtrar ketchup | Mostrou catalogo de produtos (script errado) |
| #3 | Stephanie especifica "KETCHUP - PET 12X200 G" | Ja deveria ter dados | Foi forcada a clarificar |
| #5 | "Qual a quantidade pendente para o atacadao 183" (tudo, nao so ketchup) | Mostrar todos os pedidos pendentes | Mostrou dados com inconsistencias (valores 0, pedidos zerados) |
| #7 | "qual a programacao de entrega para esses pedidos" | Mostrar datas de entrega/expedicao | **FALHOU COMPLETAMENTE** - dados contraditorios, valores diferentes, nao perguntou qual interpretacao |

### Inconsistencia de Dados Evidenciada

```
MSG #6: VCD2564291 - 5.495 unidades, R$ 50.385,70
MSG #8: VCD2564291 - 8 itens, R$ 148.932,06  [VALOR DIFERENTE]
```

### Commit Verificado

**Commit 8eeea75**: Adicionou funcionalidades (`--completo`, `--listar`), **NAO causou o problema**.
As mudancas sao adicoes de funcionalidade, nao alteracoes que quebrariam comportamento existente.

---

## 2. PROBLEMAS IDENTIFICADOS

### 2.1. Description da Skill Generica Demais

**Arquivo**: `.claude/skills/gerindo-expedicao/SKILL.md:3`

**Atual**:
```yaml
description: Consulta e opera dados logisticos da Nacom Goya. Consulta pedidos, estoque, disponibilidade, lead time. Cria separacoes. Resolve entidades (pedido, produto, cliente, grupo). Use para perguntas como 'tem pedido do Atacadao?', 'quanto tem de palmito?', 'quando fica disponivel?', 'crie separacao do VCD123'.
```

**Problema**: Diz "Consulta pedidos" mas nao especifica **qual dos 7 scripts usar**.

**Melhor Pratica Anthropic**:
> "The description field enables Skill discovery and should include both what the Skill does **and when to use it**. Be specific and include key terms."

**Status**: APROVADO para ajuste
**Responsavel**: Rafael + Claude

---

### 2.2. Falta de "Decision Tree" - Mapeamento Pergunta -> Script

**Evidencia**: Grep por "quando usar", "se.*pergunte", "ambiguo", "clarificar" retornou **nenhuma instrucao de clarificacao**.

A skill tem 7 scripts e 55+ parametros, mas **nenhum guia de decisao** sobre qual usar.

**Exemplo do problema**:
```
Pergunta: "quantas caixas de ketchup tem pendentes pro atacadao 183"

Scripts possiveis:
1. consultando_situacao_pedidos.py --grupo atacadao --produto ketchup
2. analisando_disponibilidade_estoque.py --grupo atacadao --loja 183
3. consultando_produtos_estoque.py --produto ketchup --pendente

Qual usar? NAO ESTA DOCUMENTADO.
```

**Esclarecimento sobre "Avoid too many options"**:

A recomendacao da Anthropic **NAO** significa "ter poucos parametros". Significa:
- **NAO apresentar** multiplas opcoes ao usuario sem orientacao
- **TER** um guia claro sobre qual opcao usar em cada situacao

Ou seja: **Ter 55 parametros esta OK, desde que exista um Decision Tree claro**.

**Status**: APROVADO para implementacao
**Responsavel**: Claude (precisa de input do Rafael sobre mapeamentos)

---

### 2.3. Termo "programacao de entrega" NAO MAPEADO

**Evidencia**:
```bash
grep -i "programacao de entrega" .claude/skills/gerindo-expedicao/*
# NENHUM RESULTADO
```

O termo tem **4 interpretacoes diferentes**:

| Termo | Campo | Tabela | Significado |
|-------|-------|--------|-------------|
| Data solicitada pelo cliente | `data_entrega_pedido` | CarteiraPrincipal | Quando cliente quer receber |
| Data de expedicao | `expedicao` | Separacao | Quando vamos embarcar |
| Data de agendamento | `agendamento` | Separacao | Quando vai chegar |
| Protocolo | `protocolo` | Separacao | Numero do agendamento |

**Status**: APROVADO para implementacao
**Local sugerido**: Seção "Termos Ambiguos" no SKILL.md (dentro do Decision Tree)

---

### 2.4. Examples.md Nao Tem Caso de Uso

**Arquivo**: `.claude/skills/gerindo-expedicao/examples.md` (395 linhas, 15 exemplos)

**Faltando**: Exemplos de "produto - cliente/grupo" como:
- "quantas caixas de ketchup tem pendentes pro atacadao 183"
- "quanto tem de palmito pro assai"

**Status**: APROVADO para implementacao
**Responsavel**: Rafael

---

### 2.5. Perda de Contexto Entre Mensagens

**Problema**: O agente tratou cada mensagem como nova conversa em vez de continuacao.

**Pesquisa Realizada - Solucoes da Anthropic**:

#### Solucao 1: Arquivo de Progresso Estruturado

Segundo [Anthropic Engineering](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents):
> "Os agentes devem manter um arquivo `claude-progress.txt` que funciona como 'memoria' entre sessoes."

**Aplicacao**: A skill poderia instruir o agente a manter estado da conversa.

#### Solucao 2: Folder/File Structure como Contexto

Segundo [Building agents with Claude Agent SDK](https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk):
> "The folder and file structure of an agent becomes a form of context engineering. Agents actively search and fetch their own context rather than relying on passive recall."

**Aplicacao**: O agente poderia "anotar" o contexto atual em memoria.

#### Solucao 3: Feedback Loop Estruturado

O SDK opera atraves de um loop: "gather context -> take action -> verify work -> repeat."

**Aplicacao na Skill**:

Adicionar instrucao no SKILL.md:
```markdown
## Manutencao de Contexto

ANTES de executar qualquer script em uma conversa multi-turn:

1. **IDENTIFICAR contexto anterior**: Qual cliente/grupo/pedido esta sendo discutido?
2. **MANTER referencia**: Se usuario diz "esses pedidos", refere-se ao contexto anterior
3. **VALIDAR consistencia**: Se mostrou R$ 50k antes, nao pode mostrar R$ 148k depois sem explicar
4. **SE AMBIGUO**: Perguntar "Voce ainda esta falando sobre [contexto anterior]?"
```

#### Solucao 4: Uso da Skill memoria-usuario

O sistema ja possui a skill `memoria-usuario` que pode armazenar contexto persistente.

**Aplicacao**: Instruir o agente a salvar contexto da conversa quando relevante.

**Status**: APROVADO para implementacao
**Abordagem escolhida**: Adicionar secao "Manutencao de Contexto" no SKILL.md + avaliar integracao com memoria-usuario

---

## 3. AVALIACOES DAS SUGESTOES

### 3.1. Decision Tree no SKILL.md

**Sugestao Original**: Adicionar tabela de mapeamento pergunta -> script

**Avaliacao**: EXCELENTE - Totalmente alinhado com melhores praticas Anthropic

**Status**: APROVADO
**Responsavel**: Claude (com input do Rafael)
**Perguntas pendentes**:
- Confirmar mapeamentos especificos de cada tipo de pergunta
- Validar quais scripts sao mais apropriados para cada caso

---

### 3.2. Atualizar Description da Skill

**Sugestao Original**: Expandir description com scripts e alertas

**Avaliacao**: BOM - Mas cuidado com limite de 1024 caracteres

**Status**: APROVADO com moderacao
**Responsavel**: Claude + Rafael

---

### 3.3. Mapeamento Rapido no inicio do examples.md

**Sugestao Original**: Adicionar tabela de navegacao no inicio

**Avaliacao**: OTIMO - Links de navegacao melhoram descoberta

**Status**: APROVADO
**Responsavel**: Claude
**Extensao**: Avaliar outros locais onde poderia ser implementado

---

### 3.4. Adicionar ao reference.md (em vez de novo glossario.md)

**Sugestao Original**: Criar glossario.md separado

**Avaliacao**: Melhor integrar ao reference.md existente (ja tem Glossario na linha 259)

**Motivo**: Evitar "deeply nested references" conforme Anthropic

**Status**: APROVADO integrar ao reference.md
**Responsavel**: Rafael

---

### 3.5. Workflow de Validacao

**Sugestao**: Verificar dados antes de responder

**Status**: APROVADO para proxima iteracao

---

### 3.6. Testar com Modelos Menores

**Sugestao**: Verificar se Haiku consegue usar a skill

**Status**: APROVADO para proxima iteracao

---

## 4. ROADMAP DE IMPLEMENTACAO

### Fase 1: CRITICO (Imediato)

| ID | Tarefa | Responsavel | Arquivo | Status |
|----|--------|-------------|---------|--------|
| 1.1 | Criar Decision Tree no SKILL.md | Claude | SKILL.md | PENDENTE |
| 1.2 | Adicionar secao "Termos Ambiguos" | Claude | SKILL.md | PENDENTE |
| 1.3 | Adicionar secao "Manutencao de Contexto" | Claude | SKILL.md | PENDENTE |
| 1.4 | Atualizar description da skill | Claude + Rafael | SKILL.md | PENDENTE |

### Fase 2: IMPORTANTE (Esta Semana)

| ID | Tarefa | Responsavel | Arquivo | Status |
|----|--------|-------------|---------|--------|
| 2.1 | Expandir glossario no reference.md | Rafael | reference.md | PENDENTE |
| 2.2 | Adicionar links de navegacao no examples.md | Claude | examples.md | PENDENTE |
| 2.3 | Adicionar exemplos "produto-cliente" | Rafael | examples.md | PENDENTE |

### Fase 3: DESEJAVEL (Proxima Iteracao)

| ID | Tarefa | Responsavel | Arquivo | Status |
|----|--------|-------------|---------|--------|
| 3.1 | Implementar workflow de validacao | A definir | SKILL.md | PENDENTE |
| 3.2 | Testar com Haiku/Sonnet | A definir | - | PENDENTE |
| 3.3 | Avaliar integracao com memoria-usuario | A definir | - | PENDENTE |

---

## 5. PERGUNTAS PENDENTES PARA RAFAEL

Para implementar a Fase 1, preciso de confirmacao:

### 5.1. Decision Tree - Mapeamentos

Para cada tipo de pergunta abaixo, confirme o script e parametros corretos:

| Tipo de Pergunta | Script Sugerido | Confirma? |
|------------------|-----------------|-----------|
| "quantas X tem pendentes pro Y" | `consultando_situacao_pedidos.py --grupo Y --produto X` | ? |
| "tem pedido do X?" | `consultando_situacao_pedidos.py --grupo X` | ? |
| "quando fica disponivel?" | `analisando_disponibilidade_estoque.py --pedido X` | ? |
| "quanto tem de X?" | `consultando_produtos_estoque.py --produto X --completo` | ? |
| "chegou X?" | `consultando_produtos_estoque.py --produto X --entradas` | ? |
| "o que vai dar falta?" | `consultando_produtos_estoque.py --ruptura --dias 7` | ? |

### 5.2. Termos Ambiguos Adicionais

Alem de "programacao de entrega", existem outros termos ambiguos que deveriam ser mapeados?

### 5.3. Prioridade dos Links de Navegacao

Alem do examples.md, onde mais seria util ter links de navegacao?
- [ ] SKILL.md
- [ ] reference.md
- [ ] Outro: ___________

---

## 6. REFERENCIAS

### Documentacao Anthropic Consultada

- [Skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)
- [Claude Code: Best practices for agentic coding](https://www.anthropic.com/engineering/claude-code-best-practices)
- [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- [Building agents with the Claude Agent SDK](https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk)
- [Managing context on the Claude Developer Platform](https://anthropic.com/news/context-management)

### Arquivos Relacionados

- `.claude/skills/gerindo-expedicao/SKILL.md` - Skill principal
- `.claude/skills/gerindo-expedicao/examples.md` - Exemplos de uso
- `.claude/skills/gerindo-expedicao/reference.md` - Referencia tecnica
- `app/agente/falha_conversa.md` - Registro da conversa com falha

---

## 7. HISTORICO DE ALTERACOES

| Data | Alteracao | Autor |
|------|-----------|-------|
| 10/12/2025 | Criacao do documento | Claude |
