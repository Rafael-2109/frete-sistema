---
name: comunicar-pcp
description: Gera mensagem formatada para comunicacao com PCP sobre producao
---

Gere uma mensagem formatada para o PCP solicitando previsao de producao.

## Formato da Mensagem (SEMPRE agregar por PRODUTO)

```
Ola PCP,

Preciso de previsao de producao para os seguintes produtos:

PRODUTO: [NOME_PRODUTO]
- Demanda total: [QTD_DEMANDADA] un
- Estoque atual: [ESTOQUE_ATUAL] un
- Falta: [QTD_FALTANTE] un
- Pedidos aguardando: [LISTA_PEDIDOS]

PRODUTO: [NOME_PRODUTO_2]
- Demanda total: [QTD_DEMANDADA] un
- Estoque atual: [ESTOQUE_ATUAL] un
- Falta: [QTD_FALTANTE] un
- Pedidos aguardando: [LISTA_PEDIDOS]

Consegue informar previsao de producao?
```

## Instrucoes

1. Primeiro, consulte a situacao de estoque dos produtos mencionados
2. Agregue por PRODUTO (nao por pedido)
3. Liste todos os pedidos que dependem de cada produto
4. Formate a mensagem para copiar/colar no Teams

## Canal de Comunicacao

- **Microsoft Teams**
- **SLA de resposta**: 30 minutos

## Respostas Esperadas do PCP

| Resposta | Acao |
|----------|------|
| "Sim, vou atualizar" | Aguardar atualizacao -> Programar expedicao |
| "Nao eh possivel" | Informar comercial |
| "Vou analisar" | Aguardar retorno |

$ARGUMENTS
