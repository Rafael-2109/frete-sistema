# 03 - Manutencao de Contexto

**Status**: PENDENTE
**Prioridade**: CRITICO
**Responsavel**: Claude
**Arquivo alvo**: `.claude/skills/gerindo-expedicao/SKILL.md`

---

## Problema

O agente tratou cada mensagem como **nova conversa** em vez de **continuacao**, resultando em:
- Dados inconsistentes entre respostas
- Perda de referencia ao cliente/grupo discutido
- Valores diferentes para o mesmo pedido

**Exemplo real da falha:**
```
MSG #1: Stephanie pergunta sobre Atacadao 183
MSG #5: Ainda sobre Atacadao 183
MSG #7: "esses pedidos" = Atacadao 183

Resultado:
MSG #6: VCD2564291 - R$ 50.385,70
MSG #8: VCD2564291 - R$ 148.932,06  [VALOR DIFERENTE SEM EXPLICACAO]
```

---

## Pesquisa Realizada

### Fonte 1: Anthropic Engineering - Effective Harnesses

> "Os agentes devem manter um arquivo `claude-progress.txt` que funciona como 'memoria' entre sessoes."

### Fonte 2: Building agents with Claude Agent SDK

> "The folder and file structure of an agent becomes a form of context engineering. Agents actively search and fetch their own context rather than relying on passive recall."

### Fonte 3: Feedback Loop

> O SDK opera atraves de um loop: "gather context -> take action -> verify work -> repeat."

---

## Solucao

Adicionar secao "Manutencao de Contexto" no SKILL.md (apos Termos Ambiguos).

---

## Conteudo Proposto

```markdown
---

## MANUTENCAO DE CONTEXTO - Conversas Multi-Turn

**ANTES de executar qualquer script em uma conversa com multiplas mensagens:**

### 1. Identificar Contexto Anterior

Verifique nas mensagens anteriores:
- Qual **cliente/grupo** esta sendo discutido?
- Qual **pedido** especifico foi mencionado?
- Qual **produto** foi consultado?

### 2. Manter Referencia

Se o usuario usar termos como:
- "esses pedidos" → Refere-se aos pedidos da resposta anterior
- "esse cliente" → Refere-se ao cliente/grupo ja mencionado
- "o mesmo produto" → Refere-se ao produto ja consultado

**NAO iniciar nova busca** - usar o contexto ja estabelecido.

### 3. Validar Consistencia

**ANTES de responder, verificar:**

| Verificacao | Acao |
|-------------|------|
| Mostrei valor X antes? | Se mostrar valor diferente, EXPLICAR a diferenca |
| Mostrei N itens antes? | Se mostrar quantidade diferente, EXPLICAR |
| Era sobre cliente Y? | Se mudar de cliente, CONFIRMAR com usuario |

**Exemplo de inconsistencia a evitar:**
```
ERRADO:
Resposta 1: Pedido VCD123 - R$ 50.000
Resposta 2: Pedido VCD123 - R$ 148.000

CORRETO:
Resposta 1: Pedido VCD123 (item ketchup) - R$ 50.000
Resposta 2: Pedido VCD123 (todos os itens) - R$ 148.000
            Nota: Valor maior porque agora inclui todos os 8 produtos do pedido.
```

### 4. Quando Contexto e Ambiguo

Se nao tiver certeza se usuario ainda fala do mesmo contexto:

**PERGUNTAR:** "Voce ainda esta falando sobre [cliente/pedido/produto anterior]?"

---
```

---

## Tarefas

- [ ] Claude inserir conteudo no SKILL.md
- [ ] Testar com conversa multi-turn simulada

---

## Casos de Teste

Apos implementar, testar com estas sequencias:

### Teste 1: Contexto de Cliente
```
Usuario: "tem pedido do atacadao 183?"
Agente: [responde sobre atacadao 183]
Usuario: "qual o valor total?"
Esperado: Agente mantem contexto de atacadao 183, NAO pergunta qual cliente
```

### Teste 2: Contexto de Produto
```
Usuario: "quanto tem de ketchup?"
Agente: [responde sobre ketchup]
Usuario: "e de palmito?"
Esperado: Agente entende que e outra consulta de produto, NAO mistura com ketchup
```

### Teste 3: Referencia Implicita
```
Usuario: "pedidos do assai SP"
Agente: [lista 5 pedidos]
Usuario: "qual a programacao de entrega desses?"
Esperado: Agente entende que "desses" = os 5 pedidos listados
```

---

## Perguntas para Rafael

1. O sistema de sessao do Agent SDK ja mantem historico de mensagens?
   - [ ] Sim, o agente tem acesso as mensagens anteriores
   - [ ] Nao, cada mensagem e isolada
   - [ ] Parcial: ___________

2. Devemos integrar com a skill `memoria-usuario` para contexto?
   - [ ] Sim, salvar contexto da conversa
   - [ ] Nao, instrucoes no SKILL.md sao suficientes
   - [ ] Avaliar depois

---

## Dependencias

- Depende de 02-termos-ambiguos.md (sera inserido logo apos)

---

## Referencias

| Tipo | Recurso | Secao Relevante |
|------|---------|-----------------|
| Anthropic | [Effective harnesses](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) | "claude-progress.txt como memoria" |
| Anthropic | [Building agents SDK](https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk) | "Folder structure as context engineering" |
| Anthropic | [Managing context](https://anthropic.com/news/context-management) | "Memory tool for state persistence" |
| Cookbook | [CONTEXT_COMPACTION.md](../cookbooks/CONTEXT_COMPACTION.md) | Tecnicas de compactacao |
| Cookbook | [memory_cookbook](https://github.com/anthropics/claude-cookbooks/blob/main/tool_use/memory_cookbook.ipynb) | Implementacao de memoria |

**Citacoes chave:**
> "Os agentes devem manter um arquivo claude-progress.txt que funciona como 'memoria' entre sessoes."

> "The folder and file structure of an agent becomes a form of context engineering."

---

## Historico

| Data | Alteracao | Autor |
|------|-----------|-------|
| 12/12/2025 | Criacao do documento | Claude |
| 12/12/2025 | Adicionadas referencias | Claude |
