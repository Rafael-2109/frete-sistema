# Templates de Comunicacao

Templates para comunicacao com PCP e Comercial.

> **Quando usar:** Consulte quando precisar gerar mensagem estruturada para PCP ou Comercial sobre ruptura, producao ou decisao de envio.

---

## Indice

1. [Mapeamento Gestor-Canal](#mapeamento-gestor-canal)
2. [Template PCP](#template-pcp)
3. [Template Comercial](#template-comercial)

---

## Mapeamento Gestor-Canal

| Cliente | Gestor | Canal | Territorio |
|---------|--------|-------|------------|
| Atacadao (Brasil) | Junior | WhatsApp | Key Accounts |
| Assai SP | Junior | WhatsApp | Key Accounts |
| Tenda, Spani | Junior | WhatsApp | Key Accounts |
| Assai (outros estados) | Miler | WhatsApp | Brasil exceto SP |
| Mateus, Dia a Dia | Miler | WhatsApp | Brasil exceto SP |
| Industrias (GDC, Camil, Seara, Heinz) | Fernando | WhatsApp | Industrias |
| Vendas internas | Denise | **Teams** | Interno |

**REGRA:** Vendedor NAO tem peso na priorizacao.

---

## Template PCP

**Canal:** Microsoft Teams (ramal como backup)
**SLA:** 30 minutos (maximo)

### Pergunta Padrao
> "Consegue realocar a producao para atender o pedido [X]?"

### Respostas Esperadas

| Resposta PCP | Acao |
|--------------|------|
| "Sim, vou atualizar" | Aguardar → Programar expedicao |
| "Nao e possivel" | Informar comercial |
| "Vou analisar" | Aguardar retorno |

### Modelo de Mensagem

```
Ola PCP,

Preciso de posicao sobre producao para atender o pedido {NUM_PEDIDO}:

Cliente: {RAZ_SOCIAL_RED}
Valor: R$ {VALOR}
Itens em falta:
- {PRODUTO_1}: precisa {QTD}, tem {ESTOQUE}

Consegue realocar a producao para atender ate {DATA}?
```

---

## Template Comercial

**Canal:** WhatsApp (exceto Denise = Teams)

### Informacoes a Enviar

| Info | Descricao |
|------|-----------|
| Itens em falta | Lista de produtos |
| Previsao producao | Data estimada |
| Concorrencia | Outros pedidos que usam mesmos itens |
| Causa da falta | ESTOQUE (absoluta) ou DEMANDA (relativa) |

### Perguntas a Fazer

1. Embarcar **PARCIAL**?
2. **AGUARDAR** producao?
3. **SUBSTITUIR** expedicao de outro pedido?

### Modelo de Mensagem

```
Ola {GESTOR},

Pedido com ruptura - preciso de orientacao:

PEDIDO: {NUM_PEDIDO}
CLIENTE: {RAZ_SOCIAL_RED}
VALOR TOTAL: R$ {VALOR}

ITENS EM FALTA:
- {PRODUTO_1}: precisa {QTD}, tem {ESTOQUE} (falta {PERCENTUAL}%)

PREVISAO DE PRODUCAO: {DATA} (em {N_DIAS} dias)

OPCOES:
1. Embarcar PARCIAL agora (R$ {VALOR_DISPONIVEL})
2. AGUARDAR producao (entrega em {DATA_PREVISTA})
3. SUBSTITUIR expedicao de outro pedido

Qual a orientacao?
```

---

## Fluxo de Comunicacao

```
RUPTURA DETECTADA
       │
       ▼
┌──────────────────┐
│ Falta ABSOLUTA?  │──SIM──▶ Comunicar PCP primeiro
│ (estoque < dda)  │         "Consegue realocar?"
└────────┬─────────┘              │
         │                        ▼
        NAO              ┌────────────────┐
         │               │ PCP pode fazer │
         ▼               └───────┬────────┘
┌──────────────────┐             │
│ Falta RELATIVA   │       SIM◀─┴─▶NAO
│ (outros pedidos) │        │       │
└────────┬─────────┘        ▼       ▼
         │            Aguardar  Comercial
         ▼                      "Parcial ou
    Comercial                    aguardar?"
    "Adiar outro
     pedido?"
```

---

**Fonte:** Extraido de `historia_organizada.md` - entrevistas com Rafael (dono).
