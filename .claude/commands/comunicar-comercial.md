---
name: comunicar-comercial
description: Gera mensagem formatada para comunicacao com Comercial sobre ruptura
---

Gere uma mensagem formatada para o gestor comercial sobre ruptura de pedido.

## Gestores por Cliente

| Cliente | Gestor | Canal |
|---------|--------|-------|
| Atacadao, Assai SP, Tenda, Spani | Junior | WhatsApp |
| Assai (outros), Mateus, Dia a Dia | Miler | WhatsApp |
| Industrias | Fernando | WhatsApp |
| Vendas internas | Denise | Teams |

## Formato da Mensagem

```
Ola [GESTOR],

Pedido com ruptura - preciso de orientacao:

PEDIDO: [NUM_PEDIDO]
CLIENTE: [RAZ_SOCIAL_RED]
VALOR TOTAL: R$ [VALOR]

ITENS EM FALTA:
- [PRODUTO_1]: precisa [QTD], tem [ESTOQUE] (falta [X]%)

PREVISAO DE PRODUCAO: [DATA] (em [N] dias)

OPCOES:
1. Embarcar PARCIAL agora (R$ [VALOR_DISPONIVEL])
2. AGUARDAR producao (entrega em [DATA_PREVISTA])
3. SUBSTITUIR expedicao de outro pedido

Qual a orientacao?
```

## Instrucoes

1. Identifique o gestor correto pelo cliente
2. Calcule o percentual de falta por VALOR (nao por linhas)
3. Busque a previsao de producao dos itens faltantes
4. Liste opcoes claras para decisao

## Regras de Envio Parcial (referencia)

| Falta | Demora | Decisao |
|-------|--------|---------|
| <=10% | >3 dias | PARCIAL automatico |
| 10-20% | >3 dias | Consultar comercial |
| >20% | >3 dias | Consultar comercial |

$ARGUMENTS
