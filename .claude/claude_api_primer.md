# Guia básico de uso da API para Claude

Este guia foi projetado para dar ao Claude os fundamentos do uso da API do Claude. Ele fornece explicações e exemplos de IDs de modelo/API básica de mensagens, uso de ferramentas, streaming, pensamento estendido e nada mais.

---

# Guia básico de uso da API para Claude

> Este guia foi projetado para dar ao Claude os fundamentos do uso da API do Claude. Ele fornece explicações e exemplos de IDs de modelo/API básica de mensagens, uso de ferramentas, streaming, pensamento estendido e nada mais.

## Modelos

```
Modelo mais inteligente: Claude Sonnet 4.5: claude-sonnet-4-5-20250929
Para tarefas rápidas e econômicas: Claude Haiku 4.5: claude-haiku-4-5-20251001
```

## Chamando a API

### Requisição e resposta básicas

```python
import anthropic
import os

message = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY")).messages.create(
    model="claude-sonnet-4-5",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "Olá, Claude"}
    ]
)
print(message)
```

```json
{
  "id": "msg_01XFDUDYJgAACzvnptvVoYEL",
  "type": "message",
  "role": "assistant",
  "content": [
    {
      "type": "text",
      "text": "Olá!"
    }
  ],
  "model": "claude-sonnet-4-5",
  "stop_reason": "end_turn",
  "stop_sequence": null,
  "usage": {
    "input_tokens": 12,
    "output_tokens": 6
  }
}
```

### Múltiplas rodadas de conversa

A API de Mensagens é sem estado, o que significa que você sempre envia o histórico completo da conversa para a API. Você pode usar esse padrão para construir uma conversa ao longo do tempo. Rodadas anteriores de conversa não necessariamente precisam ter se originado do Claude — você pode usar mensagens sintéticas de `assistant`.

```python
import anthropic

message = anthropic.Anthropic().messages.create(
    model="claude-sonnet-4-5",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "Olá, Claude"},
        {"role": "assistant", "content": "Olá!"},
        {"role": "user", "content": "Você pode me descrever os LLMs?"}
    ],
)
print(message)
```

### Colocando palavras na boca do Claude

Você pode pré-preencher parte da resposta do Claude na última posição da lista de mensagens de entrada. Isso pode ser usado para moldar a resposta do Claude. O exemplo abaixo usa `"max_tokens": 1` para obter uma única resposta de múltipla escolha do Claude.

```python
message = anthropic.Anthropic().messages.create(
    model="claude-sonnet-4-5",
    max_tokens=1,
    messages=[
        {"role": "user", "content": "O que é formiga em latim? (A) Apoidea, (B) Rhopalocera, (C) Formicidae"},
        {"role": "assistant", "content": "A resposta é ("}
    ]
)
```

### Visão

Claude pode ler tanto texto quanto imagens nas requisições. Suportamos tipos de origem `base64` e `url` para imagens, e os tipos de mídia `image/jpeg`, `image/png`, `image/gif` e `image/webp`.

```python
import anthropic
import base64
import httpx

# Opção 1: Imagem codificada em Base64
image_url = "https://upload.wikimedia.org/wikipedia/commons/a/a7/Camponotus_flavomarginatus_ant.jpg"
image_media_type = "image/jpeg"
image_data = base64.standard_b64encode(httpx.get(image_url).content).decode("utf-8")

message = anthropic.Anthropic().messages.create(
    model="claude-sonnet-4-5",
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": image_media_type,
                        "data": image_data,
                    },
                },
                {
                    "type": "text",
                    "text": "O que há na imagem acima?"
                }
            ],
        }
    ],
)

# Opção 2: Imagem referenciada por URL
message_from_url = anthropic.Anthropic().messages.create(
    model="claude-sonnet-4-5",
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "url",
                        "url": "https://upload.wikimedia.org/wikipedia/commons/a/a7/Camponotus_flavomarginatus_ant.jpg",
                    },
                },
                {
                    "type": "text",
                    "text": "O que há na imagem acima?"
                }
            ],
        }
    ],
)
```

## Pensamento estendido

O pensamento estendido às vezes pode ajudar Claude com tarefas muito difíceis. Quando está habilitado, a temperatura deve ser definida como 1.

O pensamento estendido é suportado nos seguintes modelos:

- Claude Opus 4.1 (`claude-opus-4-1-20250805`)
- Claude Opus 4 (`claude-opus-4-20250514`)
- Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`)

### Como funciona o pensamento estendido

Quando o pensamento estendido está ativado, Claude cria blocos de conteúdo `thinking` onde produz seu raciocínio interno. A resposta da API incluirá blocos de conteúdo `thinking`, seguidos por blocos de conteúdo `text`.

```python
import anthropic

client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=16000,
    thinking={
        "type": "enabled",
        "budget_tokens": 10000
    },
    messages=[{
        "role": "user",
        "content": "Existe um número infinito de números primos tal que n mod 4 == 3?"
    }]
)

# A resposta conterá blocos de pensamento resumidos e blocos de texto
for block in response.content:
    if block.type == "thinking":
        print(f"\nResumo do pensamento: {block.thinking}")
    elif block.type == "text":
        print(f"\nResposta: {block.text}")
```

O parâmetro `budget_tokens` determina o número máximo de tokens que Claude pode usar para seu processo de raciocínio interno. Nos modelos Claude 4, esse limite se aplica aos tokens de pensamento completos, e não à saída resumida. Orçamentos maiores podem melhorar a qualidade da resposta ao permitir uma análise mais completa para problemas complexos. Uma regra: o valor de max_tokens deve ser estritamente maior que o valor de budget_tokens para que Claude tenha espaço para escrever sua resposta após o pensamento estar completo.

## Pensamento estendido com uso de ferramentas

O pensamento estendido pode ser usado junto com o uso de ferramentas, permitindo que Claude raciocine através da seleção de ferramentas e processamento de resultados.

Limitações importantes:

1. **Limitação de escolha de ferramenta**: Suporta apenas `tool_choice: {"type": "auto"}` (padrão) ou `tool_choice: {"type": "none"}`.
2. **Preservando blocos de pensamento**: Durante o uso de ferramentas, você deve passar blocos `thinking` de volta para a API para a última mensagem do assistente.

### Preservando blocos de pensamento

```python
# Primeira requisição - Claude responde com pensamento e requisição de ferramenta
response = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=16000,
    thinking={
        "type": "enabled",
        "budget_tokens": 10000
    },
    tools=[weather_tool],
    messages=[
        {"role": "user", "content": "Qual é o clima em Paris?"}
    ]
)

# Extrair bloco de pensamento e bloco de uso de ferramenta
thinking_block = next((block for block in response.content
                      if block.type == 'thinking'), None)
tool_use_block = next((block for block in response.content
                      if block.type == 'tool_use'), None)

# Segunda requisição - Incluir bloco de pensamento e resultado da ferramenta
continuation = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=16000,
    thinking={
        "type": "enabled",
        "budget_tokens": 10000
    },
    tools=[weather_tool],
    messages=[
        {"role": "user", "content": "Qual é o clima em Paris?"},
        # Note que o thinking_block é passado junto com o tool_use_block
        {"role": "assistant", "content": [thinking_block, tool_use_block]},
        {"role": "user", "content": [{
            "type": "tool_result",
            "tool_use_id": tool_use_block.id,
            "content": f"Temperatura atual: {weather_data['temperature']}°F"
        }]}
    ]
)
```

### Pensamento intercalado

O pensamento estendido com uso de ferramentas nos modelos Claude 4 suporta pensamento intercalado, que permite ao Claude pensar entre chamadas de ferramentas. Para habilitar, adicione o cabeçalho beta `interleaved-thinking-2025-05-14` à sua requisição da API.

```python
response = client.beta.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=16000,
    thinking={
        "type": "enabled",
        "budget_tokens": 10000
    },
    tools=[calculator_tool, database_tool],
    messages=[{
        "role": "user",
        "content": "Qual é a receita total se vendêssemos 150 unidades do produto A a $50 cada?"
    }],
    betas=["interleaved-thinking-2025-05-14"]
)
```

Com pensamento intercalado e APENAS com pensamento intercalado (não pensamento estendido regular), o `budget_tokens` pode exceder o parâmetro `max_tokens`, pois `budget_tokens` neste caso representa o orçamento total em todos os blocos de pensamento dentro de uma rodada do assistente.

## Uso de Ferramentas

### Especificando ferramentas do cliente

As ferramentas do cliente são especificadas no parâmetro de nível superior `tools` da requisição da API. Cada definição de ferramenta inclui:

| Parâmetro      | Descrição |
| :--- | :--- |
| `name`         | O nome da ferramenta. Deve corresponder à regex `^[a-zA-Z0-9_-]{1,64}$`. |
| `description`  | Uma descrição detalhada em texto simples do que a ferramenta faz, quando deve ser usada e como se comporta. |
| `input_schema` | Um objeto [JSON Schema](https://json-schema.org/) definindo os parâmetros esperados para a ferramenta.     |

```json
{
  "name": "get_weather",
  "description": "Obter o clima atual em um local específico",
  "input_schema": {
    "type": "object",
    "properties": {
      "location": {
        "type": "string",
        "description": "A cidade e estado, ex: São Francisco, CA"
      },
      "unit": {
        "type": "string",
        "enum": ["celsius", "fahrenheit"],
        "description": "A unidade de temperatura, 'celsius' ou 'fahrenheit'"
      }
    },
    "required": ["location"]
  }
}
```

### Melhores práticas para definições de ferramentas

**Forneça descrições extremamente detalhadas.** Este é de longe o fator mais importante no desempenho das ferramentas. Suas descrições devem explicar todos os detalhes sobre a ferramenta, incluindo:

- O que a ferramenta faz
- Quando deve ser usada (e quando não deve)
- O que cada parâmetro significa e como afeta o comportamento da ferramenta
- Quaisquer ressalvas ou limitações importantes

Exemplo de uma boa descrição de ferramenta:

```json
{
  "name": "get_stock_price",
  "description": "Recupera o preço atual da ação para um símbolo ticker específico. O símbolo ticker deve ser um símbolo válido para uma empresa de capital aberto em uma grande bolsa de valores dos EUA como NYSE ou NASDAQ. A ferramenta retornará o preço da última negociação em USD. Deve ser usada quando o usuário pergunta sobre o preço atual ou mais recente de uma ação específica. Não fornecerá nenhuma outra informação sobre a ação ou empresa.",
  "input_schema": {
    "type": "object",
    "properties": {
      "ticker": {
        "type": "string",
        "description": "O símbolo ticker da ação, ex: AAPL para Apple Inc."
      }
    },
    "required": ["ticker"]
  }
}
```

## Controlando a saída do Claude

### Forçando o uso de ferramentas

Você pode forçar Claude a usar uma ferramenta específica especificando a ferramenta no campo `tool_choice`:

```python
tool_choice = {"type": "tool", "name": "get_weather"}
```

Ao trabalhar com o parâmetro tool_choice, temos quatro opções possíveis:

- `auto` permite que Claude decida se deve chamar qualquer uma das ferramentas fornecidas ou não (padrão).
- `any` diz ao Claude que ele deve usar uma das ferramentas fornecidas.
- `tool` nos permite forçar Claude a sempre usar uma ferramenta específica.
- `none` impede Claude de usar qualquer ferramenta.

### Saída JSON

As ferramentas não necessariamente precisam ser funções do cliente — você pode usar ferramentas sempre que quiser que o modelo retorne saída JSON que segue um esquema fornecido.

### Cadeia de pensamento

Ao usar ferramentas, Claude frequentemente mostrará sua "cadeia de pensamento", ou seja, o raciocínio passo a passo que usa para quebrar o problema e decidir quais ferramentas usar.

```json
{
  "role": "assistant",
  "content": [
    {
      "type": "text",
      "text": "<thinking>Para responder a esta pergunta, eu vou: 1. Usar a ferramenta get_weather para obter o clima atual em São Francisco. 2. Usar a ferramenta get_time para obter a hora atual no fuso horário America/Los_Angeles, que cobre São Francisco, CA.</thinking>"
    },
    {
      "type": "tool_use",
      "id": "toolu_01A09q90qw90lq917835lq9",
      "name": "get_weather",
      "input": { "location": "São Francisco, CA" }
    }
  ]
}
```

### Uso paralelo de ferramentas

Por padrão, Claude pode usar múltiplas ferramentas para responder a uma consulta do usuário. Você pode desabilitar esse comportamento definindo `disable_parallel_tool_use=true`.

## Manipulando blocos de conteúdo de uso de ferramenta e resultado de ferramenta

### Manipulando resultados de ferramentas do cliente

A resposta terá um `stop_reason` de `tool_use` e um ou mais blocos de conteúdo `tool_use` que incluem:

- `id`: Um identificador único para este bloco específico de uso de ferramenta.
- `name`: O nome da ferramenta sendo usada.
- `input`: Um objeto contendo a entrada sendo passada para a ferramenta.

Quando você recebe uma resposta de uso de ferramenta, você deve:

1. Extrair o `name`, `id` e `input` do bloco `tool_use`.
2. Executar a ferramenta real em sua base de código correspondente a esse nome de ferramenta.
3. Continuar a conversa enviando uma nova mensagem com um `tool_result`:

```json
{
  "role": "user",
  "content": [
    {
      "type": "tool_result",
      "tool_use_id": "toolu_01A09q90qw90lq917835lq9",
      "content": "15 graus"
    }
  ]
}
```

### Manipulando o motivo de parada `max_tokens`

Se a resposta do Claude for cortada devido ao atingimento do limite `max_tokens` durante o uso de ferramentas, tente novamente a requisição com um valor `max_tokens` maior.

### Manipulando o motivo de parada `pause_turn`

Ao usar ferramentas de servidor como busca na web, a API pode retornar um motivo de parada `pause_turn`. Continue a conversa passando a resposta pausada de volta como está em uma requisição subsequente.

## Solucionando erros

### Erro de execução de ferramenta

Se a própria ferramenta gerar um erro durante a execução, retorne a mensagem de erro com `"is_error": true`:

```json
{
  "role": "user",
  "content": [
    {
      "type": "tool_result",
      "tool_use_id": "toolu_01A09q90qw90lq917835lq9",
      "content": "ConnectionError: a API do serviço meteorológico não está disponível (HTTP 500)",
      "is_error": true
    }
  ]
}
```

### Nome de ferramenta inválido

Se a tentativa de uso de uma ferramenta pelo Claude for inválida (ex: parâmetros obrigatórios ausentes), tente a requisição novamente com valores de `description` mais detalhados em suas definições de ferramentas.

## Streaming de Mensagens

Ao criar uma Mensagem, você pode definir `"stream": true` para transmitir incrementalmente a resposta usando eventos enviados pelo servidor (SSE).

### Streaming com SDKs

```python
import anthropic

client = anthropic.Anthropic()

with client.messages.stream(
    max_tokens=1024,
    messages=[{"role": "user", "content": "Olá"}],
    model="claude-sonnet-4-5",
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)
```

### Tipos de eventos

Cada evento enviado pelo servidor inclui um tipo de evento nomeado e dados JSON associados. Cada stream usa o seguinte fluxo de eventos:

1. `message_start`: contém um objeto `Message` com `content` vazio.
2. Uma série de blocos de conteúdo, cada um com `content_block_start`, um ou mais eventos `content_block_delta` e `content_block_stop`.
3. Um ou mais eventos `message_delta`, indicando mudanças de nível superior no objeto `Message` final.
4. Um evento final `message_stop`.

**Aviso**: As contagens de tokens mostradas no campo `usage` do evento `message_delta` são _cumulativas_.

### Tipos de delta de bloco de conteúdo

#### Delta de texto

```json
{
  "type": "content_block_delta",
  "index": 0,
  "delta": { "type": "text_delta", "text": "Olá amig" }
}
```

#### Delta de JSON de entrada

Para blocos de conteúdo `tool_use`, os deltas são _strings JSON parciais_:

```json
{"type": "content_block_delta","index": 1,"delta": {"type": "input_json_delta","partial_json": "{\"location\": \"São Fra"}}
```

#### Delta de pensamento

Ao usar pensamento estendido com streaming:

```json
{
  "type": "content_block_delta",
  "index": 0,
  "delta": {
    "type": "thinking_delta",
    "thinking": "Deixe-me resolver isso passo a passo..."
  }
}
```

### Exemplo básico de requisição de streaming

```json
event: message_start
data: {"type": "message_start", "message": {"id": "msg_1nZdL29xx5MUA1yADyHTEsnR8uuvGzszyY", "type": "message", "role": "assistant", "content": [], "model": "claude-sonnet-4-5", "stop_reason": null, "stop_sequence": null, "usage": {"input_tokens": 25, "output_tokens": 1}}}

event: content_block_start
data: {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}}

event: content_block_delta
data: {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Olá"}}

event: content_block_delta
data: {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "!"}}

event: content_block_stop
data: {"type": "content_block_stop", "index": 0}

event: message_delta
data: {"type": "message_delta", "delta": {"stop_reason": "end_turn", "stop_sequence":null}, "usage": {"output_tokens": 15}}

event: message_stop
data: {"type": "message_stop"}
```