# Guia de Context Compaction

**Fonte:** [claude-cookbooks/tool_use/automatic-context-compaction.ipynb](https://github.com/anthropics/claude-cookbooks/blob/main/tool_use/automatic-context-compaction.ipynb)

## O Que É

Context Compaction é uma técnica para gerenciar o crescimento de tokens em conversas longas, resumindo automaticamente o histórico quando um threshold é atingido.

**Resultado típico:** 58.6% de redução no consumo de tokens.

## O Problema

Sem compactação, em workflows agentic:
- Cada interação acumula histórico
- Tool results crescem linearmente
- Contexto pode estourar 200k tokens rapidamente
- Custo aumenta proporcionalmente

**Exemplo:**
- 5 tickets de suporte
- 7 passos por ticket
- ~37 turnos totais
- **208,838 tokens** (sem compactação)
- **86,446 tokens** (com compactação - 58.6% economia)

## Como Funciona

### Configuração via API

```python
runner = client.beta.messages.tool_runner(
    model="claude-sonnet-4-5",
    max_tokens=4096,
    tools=tools,
    messages=messages,
    compaction_control={
        "enabled": True,
        "context_token_threshold": 5000,  # Quando compactar
    },
)
```

### Parâmetros Disponíveis

| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| `enabled` | bool | Ativar/desativar compactação |
| `context_token_threshold` | int | Threshold de tokens para disparar (default: 100k) |
| `model` | str | Modelo para gerar resumo (opcional) |
| `summary_prompt` | str | Prompt customizado para resumo (opcional) |

### Processo de Compactação

1. **Monitoramento**: SDK rastreia uso de tokens por turno
2. **Trigger**: Quando threshold é excedido
3. **Injeção**: Injeta prompt de resumo como user turn
4. **Geração**: Claude gera resumo em tags `<summary></summary>`
5. **Limpeza**: Histórico completo é substituído pelo resumo
6. **Continuação**: Workflow retoma com contexto comprimido

### Exemplo de Resumo Gerado

```xml
<summary>
## Support Ticket Processing Progress Summary

### Tickets Completed (2 of 5)

**TICKET-1 (Cliente X) - COMPLETED**
- Issue: Problema descrito
- Category: billing
- Priority: high
- Status: resolved

**TICKET-2 (Cliente Y) - COMPLETED**
- Issue: Outro problema
- Category: technical
- Status: resolved

### Current Status
**TICKET-3 - IN PROGRESS**
- Steps remaining: 3, 4, 5, 6, 7
</summary>
```

## Recomendações de Threshold

| Threshold | Caso de Uso | Frequência |
|-----------|-------------|------------|
| **5k-20k** | Processamento sequencial (CTes, pedidos) | Frequente |
| **50k-100k** | Workflows multi-fase com checkpoints | Moderada |
| **100k-150k** | Tarefas que precisam contexto histórico | Rara |
| **100k (padrão)** | Equilíbrio geral | - |

## Quando Usar

### ✅ Casos Ideais
- Processamento sequencial de múltiplos itens (CTes, pedidos)
- Análise de carteira com muitos pedidos
- Workflows multi-fase com checkpoints naturais
- Operações em lote
- Sessões longas de análise

### ❌ Quando Evitar
- Tarefas curtas (< 50k tokens)
- Que exigem trilha de auditoria completa
- Refinamento iterativo onde cada passo depende de detalhes exatos
- Server-side sampling loops (busca web, extended thinking)

## Aplicação no Frete Sistema

### Cenários Recomendados

1. **Análise Completa de Carteira**
   - Threshold: 50k tokens
   - Resumo preserva: pedidos processados, ações tomadas, pendências

2. **Processamento de Múltiplos CTes**
   - Threshold: 20k tokens
   - Resumo preserva: CTes lançados, erros encontrados, totais

3. **Comunicação com PCP/Comercial**
   - Threshold: 30k tokens
   - Resumo preserva: produtos discutidos, decisões tomadas

### Implementação Sugerida

```python
# Para análise de carteira
compaction_control = {
    "enabled": True,
    "context_token_threshold": 50000,
    "summary_prompt": """
    Resuma o progresso da análise de carteira:
    1. Pedidos analisados e status
    2. Separações criadas
    3. Comunicações enviadas (PCP/Comercial)
    4. Pendências e próximos passos
    Preserve números de pedidos e valores críticos.
    """
}
```

## Limitações

1. **Perda de detalhes**: Informações são comprimidas
2. **Overhead**: Cada compactação adiciona latência
3. **Server-side loops**: Pode disparar prematuramente em buscas web
4. **Auditoria**: Resumo não substitui log completo

## Referências

- [Effective Context Engineering for AI Agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- Anthropic SDK >= 0.74.1 requerido
