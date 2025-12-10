# Guia de Prompt Caching

**Fonte:** [claude-cookbooks/misc/prompt_caching.ipynb](https://github.com/anthropics/claude-cookbooks/blob/main/misc/prompt_caching.ipynb)

## O Que É

Prompt Caching permite armazenar e reutilizar contexto dentro do seu prompt, reduzindo:
- **Latência:** >2x mais rápido
- **Custo:** até 90% de redução

## Quando Usar

- Documentos longos reutilizados em múltiplas perguntas
- Instruções detalhadas repetidas
- Exemplos de contexto fixos
- Base de conhecimento estática

## Como Funciona

### Configuração Básica

```python
messages = [
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": "<documento>" + documento_longo + "</documento>",
                "cache_control": {"type": "ephemeral"}  # <-- Ativa cache
            },
            {
                "type": "text",
                "text": "Sua pergunta aqui"
            }
        ]
    }
]

response = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=300,
    messages=messages
)
```

### Métricas de Cache

A resposta inclui informações de uso:

```python
response.usage = {
    "input_tokens": 17,              # Tokens sem cache
    "output_tokens": 8,              # Tokens gerados
    "cache_read_input_tokens": 187354,    # Lidos do cache
    "cache_creation_input_tokens": 36     # Escritos no cache
}
```

## Resultados Típicos

### Sem Cache (primeira chamada)
```
Tempo: 20.37 segundos
Cache creation: 187,354 tokens
Cache read: 0
```

### Com Cache (chamadas subsequentes)
```
Tempo: 2.92 segundos (7x mais rápido!)
Cache read: 187,354 tokens
Cache creation: 36 tokens
```

## Multi-turn com Cache Incremental

### Estratégia

Adicione `cache_control` ao **último bloco do usuário** para otimizar:

```python
class ConversationWithCache:
    def __init__(self):
        self.turns = []

    def add_user_turn(self, content: str):
        self.turns.append({
            "role": "user",
            "content": [{
                "type": "text",
                "text": content,
                "cache_control": {"type": "ephemeral"}  # Cache no último user turn
            }]
        })

    def add_assistant_turn(self, content: str):
        self.turns.append({
            "role": "assistant",
            "content": [{"type": "text", "text": content}]
        })

    def get_messages(self):
        # Aplica cache_control apenas no último user turn
        messages = []
        user_turns = [i for i, t in enumerate(self.turns) if t["role"] == "user"]

        for i, turn in enumerate(self.turns):
            if i == user_turns[-1]:  # Último user turn
                messages.append({
                    "role": "user",
                    "content": [{
                        "type": "text",
                        "text": turn["content"][0]["text"],
                        "cache_control": {"type": "ephemeral"}
                    }]
                })
            else:
                messages.append(turn)

        return messages
```

### Resultados Multi-turn

| Turn | Pergunta | Tempo | % Cached |
|------|----------|-------|----------|
| 1 | "Qual o título?" | 20.37s | 0% |
| 2 | "Quem são os personagens?" | 7.53s | 100% |
| 3 | "Qual o tema?" | 6.76s | 100% |
| 4 | "Resuma o enredo" | 7.13s | 100% |

## Aplicação no Frete Sistema

### Cenário: Análise de Regras de Negócio

```python
# Carrega regras uma vez, consulta múltiplas vezes
regras_negocio = open(".claude/references/REGRAS_NEGOCIO.md").read()

messages = [
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": f"<regras>\n{regras_negocio}\n</regras>",
                "cache_control": {"type": "ephemeral"}
            },
            {
                "type": "text",
                "text": "Qual a prioridade do Atacadão?"
            }
        ]
    }
]
```

### Cenário: Múltiplas Consultas no CLAUDE.md

```python
claude_md = open("CLAUDE.md").read()

# Primeira consulta - cria cache
consulta_1 = ask_with_cache(claude_md, "Quais campos a Separação tem?")

# Segunda consulta - usa cache (muito mais rápido)
consulta_2 = ask_with_cache(claude_md, "Como calcular lead time?")
```

## Limitações

1. **Cache ephemeral:** Persiste por **5 minutos** apenas
2. **Tamanho mínimo:** Conteúdo deve ser significativo para valer o cache
3. **Ordem importa:** Cache é sensível à ordem dos blocos
4. **Modelos suportados:** Claude 3.5+

## Melhores Práticas

### 1. Coloque Conteúdo Cacheável Primeiro
```python
# BOM - documento cacheável antes da pergunta
[documento_cache, pergunta]

# RUIM - pergunta antes quebra o cache
[pergunta, documento_cache]
```

### 2. Use para Conteúdo Estável
- ✅ Documentação, regras de negócio, exemplos
- ❌ Dados que mudam frequentemente

### 3. Monitore Uso de Cache
```python
def log_cache_usage(response):
    usage = response.usage
    cached = usage.cache_read_input_tokens
    created = usage.cache_creation_input_tokens
    total = usage.input_tokens + cached + created

    cache_ratio = cached / total if total > 0 else 0
    print(f"Cache ratio: {cache_ratio:.1%}")
```

## Referências

- [Prompt Caching Notebook](https://github.com/anthropics/claude-cookbooks/blob/main/misc/prompt_caching.ipynb)
- [Anthropic API Docs - Caching](https://docs.anthropic.com/claude/docs/prompt-caching)
