# Contexto Operacional - Nacom Goya

Contexto da empresa, clientes e operacao para tomada de decisao.

> **Quando usar:** Consulte quando precisar entender contexto para priorizar, escalar decisao, ou entender comportamento de cliente.

---

## Indice

1. [A Empresa](#a-empresa)
2. [Gargalos Operacionais](#gargalos-operacionais)
3. [Top Clientes](#top-clientes)
4. [Tipos de Clientes](#tipos-de-clientes)
5. [SLAs por Cliente](#slas-por-cliente)
6. [Contexto Estrategico](#contexto-estrategico)
7. [Sazonalidade](#sazonalidade)
8. [Quando Escalar para Humano](#quando-escalar-para-humano)

---

## A Empresa

| Aspecto | Valor |
|---------|-------|
| Faturamento | R$ 16.000.000/mes |
| Volume | ~1.000.000 kg/mes |
| Pedidos | ~500 pedidos/mes (media 2.000 kg/pedido) |
| CD | Capacidade 4.000 pallets, expedicao ~500 pallets/dia |

**Estrutura:**
- Planta Fabril (conservas): 7 maquinas envase
- La Famiglia (subcontratada): Molhos e oleos
- CD/Armazem: 2km das fabricas

---

## Gargalos Operacionais

**Ordem de frequencia (do mais comum para o menos):**

| # | Gargalo | Impacto |
|---|---------|---------|
| 1 | **Agendas** | Cliente DEMORA para aprovar (nao e dia da semana, e tempo de resposta) |
| 2 | **Materia-prima** | Importada, lead time longo |
| 3 | **Producao** | Capacidade de linhas |

**Insight critico sobre Agendas:**
```
O PROBLEMA NAO E: "Cliente so aceita terca e quinta"
O PROBLEMA E: "Cliente DEMORA para aprovar a agenda"

EXEMPLO:
- Programamos expedicao dia 10
- Solicitamos agenda
- Cliente so responde aprovando dia 25
- RESULTADO: 15 dias de atraso por espera de agenda
```

---

## Top Clientes

| # | Cliente | Fat/Mes | % Total | Comportamento Agenda | Gestor |
|---|---------|---------|---------|----------------------|--------|
| 1 | Atacadao | R$ 8MM | **50%** | Ruim de aprovar | Junior |
| 2 | Assai | R$ 2.1MM | 13% | Ruim de aprovar | Junior (SP) / Miler |
| 3 | Gomes da Costa | R$ 700K | 4% | Ja vem programado | Fernando |
| 4 | Mateus | R$ 500K | 3% | Variavel por loja | Miler |
| 5 | Dia a Dia | R$ 350K | 2% | FOB (eles coletam) | Miler |
| 6 | Tenda | R$ 350K | 2% | Meio ruim | Junior |

**REGRA CRITICA:** Atacadao = 50% do faturamento. Se Atacadao atrasa, a empresa SENTE.

---

## Tipos de Clientes

| Tipo | Volume | Margem | Fidelidade | Caracteristica |
|------|--------|--------|------------|----------------|
| Atacadistas | Alto | Media | Alta | Exigem servico, promocao, atendimento |
| Varejistas | Medio | Alta | Alta | Foco em embalagem e promocao |
| Distribuidores | Alto | Baixa | **Baixa** | Leiloeiros |
| Industria | Programado | **Mais alta** | **Mais fiel** | Homologacao demorada |

**Identificar cliente industria:**
- Produtos com sufixo "INDUSTRIA"
- Embalagem "BD IND"
- Normalmente tem `data_entrega_pedido`

---

## SLAs por Cliente

| Cliente | Limite Entrega | Excecao |
|---------|----------------|---------|
| Atacadao | 45 dias | AM/RR = 60 dias |
| Assai | Cobra muito | - |
| Outros | Nao formalizado | - |

---

## Contexto Estrategico

```
FUNDOS DE INVESTIMENTO (donos dos atacarejos)
└── Foco: Balanco, gerar caixa
    └── Resultado: Estoques cada vez mais LIMITADOS

COMPRADORES (operacao)
└── Querem: Estoque, acoes de vendas
└── Realidade: Nao podem comprar livremente

RESULTADO: Rupturas frequentes em loja

POR ISSO: Entrega agil = Loja abastecida = Mais pedido
```

**Implicacao:** Entrega rapida nao e so "atender bem" - e estrategia de CRESCIMENTO de vendas.

---

## Sazonalidade

**Epocas de pico:**
- Natal
- Pascoa

**Produtos sazonais:**

| Produto | Periodo | Motivo |
|---------|---------|--------|
| Almofadas (SACHET 80G) | Final do ano | Cestas de natal |

---

## Quando Escalar para Humano

**Situacoes que EXIGEM decisao humana:**

| # | Situacao | Tipo |
|---|----------|------|
| 1 | Divergencia valor cobrado vs tabela (transportadora nao concorda) | Comercial |
| 2 | Freteiro nao sabe se aguarda ou volta | Operacional |
| 3 | Frete esporadico sem precificacao | Tecnico |
| 4 | Situacao nao coberta pelas regras | Geral |

**Fases de autonomia do agente:**

| Fase | Acao | Status |
|------|------|--------|
| FASE 1 (Atual) | Criar separacao | SUGERIR (usuario confirma) |
| FASE 2 (Futuro) | Criar separacao | Autonomo |

---

**Fonte:** Extraido de `historia_organizada.md` - entrevistas com Rafael (dono).
