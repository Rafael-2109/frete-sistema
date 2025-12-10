# Guia de Metaprompt

**Fonte:** [claude-cookbooks/misc/metaprompt.ipynb](https://github.com/anthropics/claude-cookbooks/blob/main/misc/metaprompt.ipynb)

## O Que É

Metaprompt é uma técnica para **gerar prompts otimizados automaticamente**. Você descreve a tarefa que quer realizar e Claude gera um prompt bem estruturado para essa tarefa.

**Resolve o problema da "página em branco"** - não saber como começar a escrever um prompt eficiente.

## Quando Usar

- Criar novos skills
- Otimizar prompts existentes
- Gerar templates de comunicação
- Estruturar tarefas complexas
- Criar prompts para chatbots/agentes

## Como Funciona

### Input

Você fornece:
1. **Descrição da tarefa** (texto livre)
2. **Variáveis** (opcionais) - placeholders que serão preenchidos

### Output

Claude retorna:
1. **Inputs** - variáveis identificadas
2. **Instructions Structure** - planejamento da estrutura
3. **Instructions** - prompt final otimizado

## Exemplo Prático

### Tarefa
```
"Redigir um email respondendo a uma reclamação de cliente"
```

### Variáveis Identificadas
```
$CUSTOMER_EMAIL - O email original do cliente
$COMPANY_NAME - Nome da empresa respondendo
```

### Prompt Gerado

```xml
Você é um especialista em atendimento ao cliente da {{COMPANY_NAME}}.

Analise o email do cliente abaixo e redija uma resposta profissional e empática.

<email_cliente>
{{CUSTOMER_EMAIL}}
</email_cliente>

<instrucoes>
1. Reconheça o problema do cliente
2. Peça desculpas de forma genuína
3. Explique a solução ou próximos passos
4. Ofereça compensação se apropriado
5. Agradeça pelo feedback
</instrucoes>

<regras>
- Mantenha tom profissional mas caloroso
- NÃO faça promessas que não pode cumprir
- NÃO culpe o cliente
- Responda em português brasileiro
</regras>

<formato_saida>
Use <scratchpad> para planejar sua resposta.
Depois, forneça a resposta final em <email_response>.
</formato_saida>
```

## Template de Metaprompt

```python
METAPROMPT_TEMPLATE = """
<task>
{TASK_DESCRIPTION}
</task>

Baseado na tarefa acima, gere um prompt otimizado que:

1. Identifique as variáveis de input necessárias
2. Estruture as instruções de forma clara
3. Inclua exemplos de boas e más respostas
4. Use tags XML para demarcar seções
5. Especifique o formato de saída esperado

<planning>
Antes de gerar o prompt:
1. Qual é o objetivo principal?
2. Quais são as entradas necessárias?
3. Quais são os casos de erro comuns?
4. Como garantir consistência?
</planning>

<output>
Forneça o prompt completo em <instructions> tags.
</output>
"""
```

## Boas Práticas do Metaprompt

### 1. Tags XML
- Use para demarcar variáveis: `<customer_email>`, `<pedido>`
- Use para seções: `<instrucoes>`, `<regras>`, `<formato>`
- Use para output estruturado: `<thinking>`, `<answer>`

### 2. Monólogo Interno
Para tarefas complexas, peça raciocínio antes da resposta:
```xml
<scratchpad>
[Seu raciocínio aqui - não será mostrado ao usuário]
</scratchpad>

<resposta>
[Resposta final]
</resposta>
```

### 3. Exemplos
Inclua exemplos de boas e más respostas:
```xml
<exemplo_bom>
"Lamentamos sinceramente o ocorrido..."
</exemplo_bom>

<exemplo_ruim>
"Não é nossa culpa, você deveria ter lido os termos..."
</exemplo_ruim>
```

### 4. Variáveis
- Coloque variáveis longas ANTES das instruções
- Use nomes descritivos: `$CUSTOMER_EMAIL` vs `$INPUT`
- Liste variáveis mínimas necessárias (1-3)

## Aplicação no Frete Sistema

### Criar Skill de Comunicação PCP

**Tarefa:**
```
Gerar mensagem para PCP solicitando previsão de produção,
agregando por produto e listando pedidos afetados.
```

**Prompt gerado seria otimizado para:**
- Formato específico de mensagem
- Agregação correta por produto
- Tom profissional para Teams
- Informações completas (demanda, estoque, falta)

### Criar Skill de Análise de Ruptura

**Tarefa:**
```
Analisar pedido em ruptura, calcular percentual de falta por valor,
e recomendar ação (parcial/aguardar/escalar).
```

### Otimizar Prompts Existentes

Use metaprompt para revisar e melhorar:
- Templates do analista-carteira.md
- Instruções dos skills de consulta
- Mensagens para comercial

## Dicas de Uso

1. **Seja específico na tarefa** - quanto mais contexto, melhor o prompt
2. **Itere** - use o prompt gerado, teste, refine
3. **Mantenha variáveis simples** - deixe Claude inferir quando possível
4. **Revise sempre** - metaprompt é ponto de partida, não final

## Código Python

```python
from anthropic import Anthropic

client = Anthropic()

def generate_prompt(task_description: str, variables: list[str] = None):
    """Gera prompt otimizado usando metaprompt."""

    variables_str = "\n".join(variables) if variables else "[Claude infere]"

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=4000,
        messages=[{
            "role": "user",
            "content": f"""
            Gere um prompt otimizado para a seguinte tarefa:

            <task>{task_description}</task>

            Variáveis sugeridas: {variables_str}

            Retorne em <instructions> tags.
            """
        }]
    )

    return response.content[0].text

# Uso
prompt = generate_prompt(
    "Analisar carteira de pedidos e priorizar por algoritmo P1-P7",
    ["$CARTEIRA_JSON", "$DATA_ANALISE"]
)
```

## Referências

- [Metaprompt Notebook](https://github.com/anthropics/claude-cookbooks/blob/main/misc/metaprompt.ipynb)
- [Prompt Engineering Guide](https://docs.anthropic.com/claude/docs/prompt-engineering)
