# Sistema de Hooks - Agent SDK

Sistema simplificado de hooks usando subagente Haiku para gerenciamento inteligente de memórias.

## Arquitetura

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FLUXO SIMPLIFICADO                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   [USUÁRIO ENVIA MENSAGEM]                                                  │
│        │                                                                    │
│        ▼                                                                    │
│   ┌─────────────────────────────────┐                                       │
│   │ PRE-HOOK                        │  ← Haiku analisa memórias existentes  │
│   │ get_relevant_context()          │    + prompt → retorna contexto        │
│   └─────────────────────────────────┘                                       │
│        │                                                                    │
│        ▼                                                                    │
│   [SDK PROCESSA + CLAUDE RESPONDE]                                          │
│        │                                                                    │
│        ▼                                                                    │
│   ┌─────────────────────────────────┐                                       │
│   │ POST-HOOK                       │  ← Haiku analisa conversa             │
│   │ analyze_and_save()              │    → detecta padrões/correções        │
│   │                                 │    → salva silenciosamente            │
│   └─────────────────────────────────┘                                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Componentes

| Componente | Arquivo | Responsabilidade |
|------------|---------|------------------|
| MemoryAgent | `memory_agent.py` | Subagente Haiku para PRE e POST hooks |

## Uso

```python
from app.agente.hooks import get_memory_agent

agent = get_memory_agent()

# PRE-HOOK: Antes de enviar ao SDK
context = agent.get_relevant_context(user_id, prompt)
if context:
    prompt_with_context = f"[CONTEXTO DO USUÁRIO]\n{context}\n\n{prompt}"

# ... SDK processa ...

# POST-HOOK: Após resposta (silencioso)
result = agent.analyze_and_save(user_id, prompt, response)
```

## O que o Haiku detecta e salva

### 1. TERMOS E SINÔNIMOS (category: sinonimos)
- Abreviações: "VCD", "PO", "NF", "CT-e"
- Vocabulário específico: como usuário se refere a entidades
- Exemplo: "pedido dele" = pedido_cliente

### 2. REGRAS DE NEGÓCIO (category: negocio)
- Políticas: "FOB sempre manda completo"
- Prioridades: "Atacadão 183 sempre por último"
- Restrições: "cliente X não aceita parcial"

### 3. PADRÕES DE TRABALHO (category: workflow)
- Sequências: "sempre verifico estoque antes de separar"
- Preferências: "começo pelo maior volume"
- Rotinas: "analiso Atacadão primeiro"

### 4. CORREÇÕES DE DOMÍNIO (category: dominio)
- Campos: "esse campo se chama X, não Y"
- Processos: "aqui fazemos assim, não assado"
- Terminologia: "chamamos de X, não de Y"

### 5. FATOS DO USUÁRIO (category: usuario)
- Cargo e responsabilidades
- Clientes que gerencia
- Produtos que acompanha

## O que NÃO é salvo

- Dados temporários ("pedido 12345 de hoje")
- Informações já existentes nas memórias
- Obviedades sem valor agregado

## Custo Estimado

Modelo: `claude-haiku-4-5-20251001`

| Operação | Tokens ~in | Tokens ~out | Custo |
|----------|-----------|-------------|-------|
| PRE-HOOK | 500 | 200 | ~$0.0015 |
| POST-HOOK | 1500 | 200 | ~$0.0015 |
| **Total/mensagem** | | | **~$0.003** |

## Estrutura de Memórias

As memórias são salvas na tabela `agent_memories` com paths organizados por categoria:

```
/memories/
├── preferences.xml           # Preferências de comunicação (feedback)
├── context/
│   └── usuario.xml           # Fatos do usuário (category: usuario)
├── learned/
│   ├── termos.xml            # Termos e sinônimos (category: sinonimos)
│   ├── regras.xml            # Regras de negócio (category: negocio)
│   ├── patterns.xml          # Padrões de trabalho (category: workflow)
│   └── auto_*.xml            # Detecções não categorizadas
└── corrections/
    ├── dominio.xml           # Correções de domínio (category: dominio)
    └── feedback_*.xml        # Correções via feedback
```

### Formato das Memórias

```xml
<memoria type="regra" category="negocio">
  <content>FOB sempre manda completo - não aceita parcial</content>
  <tags>FOB, parcial, regra</tags>
  <detected_at>2024-12-13T15:00:00Z</detected_at>
  <source>auto_haiku</source>
</memoria>
```

## Diferença da Versão Anterior

| Aspecto | Versão Antiga | Versão Nova |
|---------|---------------|-------------|
| Arquivos | 8 arquivos (~900 linhas) | 1 arquivo (~250 linhas) |
| Detecção | Regex frágeis | LLM (Haiku) inteligente |
| Custo extra | Zero | ~$0.003/mensagem |
| Falsos positivos | Muitos | Poucos (LLM entende contexto) |
| Feedback positive/negative | Código morto | Removido |
