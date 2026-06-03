<!-- doc:meta
tipo: reference
camada: L2
sot_de: —
hub: .claude/references/INDEX.md
superseded_by: —
atualizado: 2026-06-02
-->
# História do Conhecimento - Agente Logístico Nacom Goya

> **Papel:** História do Conhecimento - Agente Logístico Nacom Goya.

## Indice

- [PARTE 1: A EMPRESA](#parte-1-a-empresa)
  - [1.1 Identidade](#11-identidade)
  - [1.2 Estrutura do Grupo](#12-estrutura-do-grupo)
  - [1.3 Marcas](#13-marcas)
  - [1.4 Produtos](#14-produtos)
  - [1.5 Modelo de Produção](#15-modelo-de-produção)
  - [1.6 Características de Produção](#16-características-de-produção)
  - [1.7 Gargalos (Ordem de Frequência)](#17-gargalos-ordem-de-frequência)
- [PARTE 2: OS CLIENTES](#parte-2-os-clientes)
  - [2.1 Top Clientes (75% do Faturamento)](#21-top-clientes-75-do-faturamento)
  - [2.2 Tipos de Clientes](#22-tipos-de-clientes)
  - [2.3 Clientes Indústria](#23-clientes-indústria)
  - [2.4 Clientes Problemáticos](#24-clientes-problemáticos)
  - [2.5 SLAs e Limites](#25-slas-e-limites)
  - [2.6 Bloqueios](#26-bloqueios)
  - [2.7 Contexto Estratégico de Mercado](#27-contexto-estratégico-de-mercado)
- [PARTE 3: ESTRUTURA COMERCIAL](#parte-3-estrutura-comercial)
  - [3.1 Gestores e Territórios](#31-gestores-e-territórios)
- [PARTE 4: FLUXO OPERACIONAL](#parte-4-fluxo-operacional)
  - [4.1 Equipe](#41-equipe)
  - [4.2 Fluxo Completo (Swimlane)](#42-fluxo-completo-swimlane)
  - [4.3 Transporte](#43-transporte)
  - [4.4 Regras de Roteirização](#44-regras-de-roteirização)
  - [4.5 Cotação de Frete (3 Níveis)](#45-cotação-de-frete-3-níveis)
  - [4.6 Problemas Frequentes](#46-problemas-frequentes)
  - [4.7 Quando Rafael é Acionado](#47-quando-rafael-é-acionado)
- [PARTE 5: ALGORITMO DE PRIORIZAÇÃO (P1-P7)](#parte-5-algoritmo-de-priorização-p1-p7)
  - [5.1 Ordem de Análise da Carteira](#51-ordem-de-análise-da-carteira)
  - [5.2 Hierarquia de Priorização (Regra de Ouro)](#52-hierarquia-de-priorização-regra-de-ouro)
- [PARTE 6: REGRAS DE ENVIO PARCIAL](#parte-6-regras-de-envio-parcial)
  - [6.1 Tabela de Decisão](#61-tabela-de-decisão)
  - [6.2 Limites de Carga (SEMPRE parcial se exceder)](#62-limites-de-carga-sempre-parcial-se-exceder)
  - [6.3 Casos Especiais](#63-casos-especiais)
- [PARTE 7: COMUNICAÇÃO](#parte-7-comunicação)
  - [7.1 Comunicação com PCP](#71-comunicação-com-pcp)
  - [7.2 Comunicação com Comercial](#72-comunicação-com-comercial)
- [PARTE 8: FLUXO DE AGENDAMENTO](#parte-8-fluxo-de-agendamento)
  - [8.1 Estados](#81-estados)
  - [8.2 Estratégia](#82-estratégia)
- [PARTE 9: LEADTIMES DE PLANEJAMENTO](#parte-9-leadtimes-de-planejamento)
  - [9.1 Com data_entrega_pedido Definida](#91-com-data_entrega_pedido-definida)
  - [9.2 Necessita de Agendamento](#92-necessita-de-agendamento)
  - [9.3 Outros Casos](#93-outros-casos)
- [PARTE 10: VOCABULÁRIO INTERNO](#parte-10-vocabulário-interno)
  - [10.1 Gírias da Operação](#101-gírias-da-operação)
  - [10.2 Limites de Veículos](#102-limites-de-veículos)
  - [10.3 Siglas de Produtos](#103-siglas-de-produtos)
- [PARTE 11: ESCOPO DO AGENTE LOGÍSTICO](#parte-11-escopo-do-agente-logístico)
  - [11.1 Objetivo](#111-objetivo)
  - [11.2 Fases de Autonomia](#112-fases-de-autonomia)
  - [11.3 Quando Escalar para Humano](#113-quando-escalar-para-humano)
  - [11.4 Limitação](#114-limitação)
- [PARTE 12: SAZONALIDADE E EXCEÇÕES](#parte-12-sazonalidade-e-exceções)
  - [12.1 Épocas de Pico](#121-épocas-de-pico)
  - [12.2 Produtos Sazonais](#122-produtos-sazonais)
  - [12.3 Produtos Especiais](#123-produtos-especiais)
- [PARTE 13: IMPLEMENTAÇÃO TÉCNICA](#parte-13-implementação-técnica)
  - [13.1 Constantes do Sistema](#131-constantes-do-sistema)
  - [13.2 Grupos Empresariais (Prefixos CNPJ)](#132-grupos-empresariais-prefixos-cnpj)
  - [13.3 Script Principal](#133-script-principal)
  - [13.4 Prioridades no Sistema](#134-prioridades-no-sistema)
- [PARTE 14: HISTÓRICO DE CORREÇÕES](#parte-14-histórico-de-correções)
  - [14.1 Correções Implementadas no Script](#141-correções-implementadas-no-script)
  - [14.2 Fluxo para Outras Regiões (não SP/RED/SC-PR)](#142-fluxo-para-outras-regiões-não-spredsc-pr)

> Documento histórico de descoberta de conhecimento tácito do Rafael (dono) para criar o Agente Logístico.
> Objetivo: Economizar 2-3 horas/dia de análise de carteira.

---

## PARTE 1: A EMPRESA

### 1.1 Identidade

| Aspecto | Detalhe |
|---------|---------|
| Nome | Nacom Goya |
| Tipo | Fabricante de conservas, molhos e óleos |
| Faturamento | R$ 16.000.000/mês |
| Volume | ~1.000.000 kg/mês |
| Pedidos | ~500 pedidos/mês (média 2.000 kg/pedido) |

### 1.2 Estrutura do Grupo

```
NACOM GOYA (Empresa Principal)
│
├── PLANTA FABRIL (Conservas)
│   ├── Embalagens flexíveis: 7 máquinas de envase
│   │   ├── 2 máquinas pouch 120-180g
│   │   ├── 2 máquinas pouch 80-100g
│   │   ├── 2 máquinas sachet 60-80g (almofada 4 soldas)
│   │   └── 1 máquina pouch 300-400g
│   ├── Baldes: 1 máquina envase 1-2kg
│   ├── Vidro: 1 máquina envase 100-500g
│   └── Linha manual: pouch 1kg, bag 1kg, barricas, baldes industriais
│
├── LA FAMIGLIA (Subcontratada)
│   ├── Galpão Molhos
│   │   ├── 6 tanques de preparo (20/30.000L)
│   │   └── 6 máquinas de envase por tipo de embalagem
│   └── Galpão Óleos (estrutura separada)
│
└── CD / ARMAZÉM (2km das fábricas)
    ├── Capacidade: 4.000 pallets
    ├── Expedição: ~500 pallets/dia
    └── Recebe PA de todas as plantas + embalagens
```

### 1.3 Marcas

| Tipo | Marcas |
|------|--------|
| Próprias | Campo Belo, La Famiglia, St Isabel, Casablanca, Dom Gameiro |
| Terceiros (Private Label) | Tback, Benassi, Imperial, Camil, GDC, Uniagro, Cabana, Senhora do Viso, Bidolux |

### 1.4 Produtos

**Conservas** (Importadas em bombonas, fracionadas):
- Azeitona: Inteira, Recheada, Fatiada, Sem Caroço, Picada, Pasta
- Cogumelo: Inteiro, Fatiado, Picado
- Pepino: Inteiro, Fatiado, Relish
- Picles Misto
- Cebolinha Cristal
- Pimenta Biquinho: Inteira, Picada
- Palmito: Tolete, Picado, Rodela

**Molhos** (La Famiglia): Ketchup, Mostarda, Shoyu, Pimenta, Alho, etc.

**Óleos** (La Famiglia): Misto soja + oliva (garrafa 500ml, galão 5L, pet 200ml)

### 1.5 Modelo de Produção

| Tipo | Modelo | Gatilho |
|------|--------|---------|
| Marcas próprias | Para estoque (MTS) | Programação PCP |
| Marcas terceiros | Sob demanda (MTO) | Pedido |
| Indústria | Sob demanda (MTO) | Pedido |
| Institucional | Sob demanda (MTO) | Pedido |

**Modelo de Negócio Private Label:**

| Modelo | Fluxo | Clientes |
|--------|-------|----------|
| Venda PA | Compra embalagem → Envasa → Vende PA | Tback, Benassi, Imperial, Camil, GDC, Uniagro, Cabana, Senhora do Viso |
| Industrialização | Cliente envia embalagem → Vende MP → Remessa industrialização → Retorno → Cobra serviço | Bidolux |

### 1.6 Características de Produção

**Conservas:**
- Linhas mais flexíveis (ex: balde pode produzir 3 itens/dia)
- Linhas mais engessadas (ex: pouch - troca de bobinas trabalhosa)
- Lead time não medido formalmente

**Molhos:**
- Processo trabalhoso com tubulações
- Necessário CIP após troca de produto
- Apenas 1 linha de produção
- Se 5 SKUs diferentes → ~8-9 dias (produtos alto giro produzem 2 dias seguidos)

### 1.7 Gargalos (Ordem de Frequência)

1. 🥇 **Agendas** (clientes demoram para aprovar)
2. 🥈 **Matéria-prima** (importada, lead time longo)
3. 🥉 **Produção** (capacidade de linhas)

**Insight sobre Agendas:**
```
O PROBLEMA NÃO É:
  "Cliente só aceita terça e quinta"

O PROBLEMA É:
  "Cliente DEMORA para aprovar a agenda"

EXEMPLO:
  - Programamos expedição dia 10
  - Solicitamos agenda
  - Cliente só responde aprovando dia 25
  - RESULTADO: 15 dias de atraso por espera de agenda

RESTRIÇÃO REAL:
  - Não é dia da semana
  - É HORÁRIO de recebimento
```

---

## PARTE 2: OS CLIENTES

### 2.1 Top Clientes (75% do Faturamento)

| # | Cliente | Tipo | Faturamento/Mês | % Total | Comportamento Agenda | Gestor |
|---|---------|------|-----------------|---------|----------------------|--------|
| 1 | Atacadão | Atacarejo | R$ 8MM | **50%** | Ruim de aprovar | Junior |
| 2 | Assaí | Atacarejo | R$ 2.1MM | 13% | Ruim de aprovar | Junior (SP) / Miler |
| 3 | Gomes da Costa | Indústria | R$ 700K | 4% | Já vem programado | Fernando |
| 4 | Mateus | Atacarejo | R$ 500K | 3% | Variável por loja | Miler |
| 5 | Dia a Dia | Atacarejo | R$ 350K | 2% | FOB (eles coletam) | Miler |
| 6 | Tenda | Atacarejo | R$ 350K | 2% | Meio ruim | Junior |

**⚠️ REGRA CRÍTICA:** Atacadão = 50% do faturamento. Se Atacadão atrasa, a empresa SENTE.

### 2.2 Tipos de Clientes

| Tipo | Comportamento | Margem | Fidelidade |
|------|---------------|--------|------------|
| Atacadistas | Volume alto, exigem serviço de entrega, promoção, atendimento | Média | Alta |
| Varejistas | Produtos com maior valor agregado, foco em embalagem e promoção | Alta | Alta |
| Distribuidores | Volumes expressivos, muito leiloeiros | Baixa | Baixa |
| Indústria | Compram por programação, alto poder de compra, homologação demorada | **Mais alta** | **Mais fiéis** |

### 2.3 Clientes Indústria

Identificação:
- Produtos com sufixo "INDUSTRIA"
- Produtos com embalagem "BD IND"
- Normalmente contém `data_entrega_pedido`

Exemplos: Camil, Seara, Heinz, Gomes da Costa

### 2.4 Clientes Problemáticos

Exemplo citado: **Coml W**
- Compra 2k/3k
- Tem horário para entrega
- Já cancelou pedido pois disse que "pediu por engano"
- Já rejeitou carro que chegou 2 minutos atrasado
- Para receber 10 caixas de 6 baldes de cogumelo de 2kg

> "Clientes pequenos que se acham grandes"

### 2.5 SLAs e Limites

| Cliente | Limite Entrega | Exceção |
|---------|----------------|---------|
| Atacadão | 45 dias | AM/RR = 60 dias |
| Assaí | Cobra muito | - |
| Outros | Não formalizado | - |

### 2.6 Bloqueios

| Tipo | Existe? | Critério |
|------|---------|----------|
| Blacklist formal | ❌ | - |
| Bloqueio financeiro | ✅ | Inadimplência |

### 2.7 Contexto Estratégico de Mercado

```
┌─────────────────────────────────────────────────────────┐
│  FUNDOS DE INVESTIMENTO (donos dos atacarejos)          │
│  └── Foco: Balanço, gerar caixa                         │
│      └── Resultado: Estoques cada vez mais LIMITADOS    │
├─────────────────────────────────────────────────────────┤
│  COMPRADORES (operação)                                 │
│  └── Querem: Estoque, ações de vendas                   │
│  └── Realidade: Não podem comprar livremente            │
│      ├── Muito produto de outra marca na categoria      │
│      └── Baixo giro de outras lojas consumindo "budget" │
├─────────────────────────────────────────────────────────┤
│  RESULTADO: Rupturas frequentes em loja                 │
│                                                         │
│  POR ISSO: Entrega ágil = Loja abastecida = Mais pedido│
└─────────────────────────────────────────────────────────┘
```

**Implicação:** Entrega rápida não é só "atender bem" - é estratégia de crescimento de vendas.

---

## PARTE 3: ESTRUTURA COMERCIAL

### 3.1 Gestores e Territórios

```
├── MILER (~50 vendedores)
│   ├── Território: Brasil EXCETO SP
│   ├── Clientes: Assaí (fora SP), Mateus, Dia a Dia
│   └── Canal: WhatsApp
│
├── JUNIOR (~4-5 vendedores) ⭐ KEY ACCOUNTS
│   ├── Território: Grandes redes
│   ├── Clientes: Atacadão (Brasil), Assaí SP (40% do Assaí), Tenda, Spani
│   └── Canal: WhatsApp
│
├── FERNANDO (~4-5 vendedores)
│   ├── Território: Indústrias
│   ├── Clientes: Gomes da Costa, Camil, Seara, Heinz, etc.
│   └── Canal: WhatsApp
│
└── DENISE (2 vendedoras)
    ├── Território: Vendas internas
    └── Canal: Microsoft Teams
```

**⚠️ REGRA:** Vendedor NÃO tem peso na priorização.

---

## PARTE 4: FLUXO OPERACIONAL

### 4.1 Equipe

| Área | Qtd | Funções |
|------|-----|---------|
| Transporte | 8 | Roteirização, Monitoramento, Devoluções, Prospecção, Auditoria |
| Armazém | 8 | Separação, Faturamento, Expedição, Portaria |

### 4.2 Fluxo Completo (Swimlane)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           FLUXO DE EXPEDIÇÃO NACOM                              │
└─────────────────────────────────────────────────────────────────────────────────┘

RAFAEL (Dono) ─────────────────────────────────────────────────────────────────────
    │
    ├─1→ Analisa carteira (pedidos novos + datas disponibilidade)
    │
    ├─2→ Se disponível 4/5+ dias → Questiona PCP
    │    │
    │    └── PCP retorna: analisar / alterar programação / confirmar compras / não possível
    │
    ├─3→ Informa Comercial da falta/atraso
    │    │
    │    └── Comercial retorna: aguarda / autoriza parcial / vai resolver
    │
    ├─4→ Gera SEPARAÇÃO (ou aguarda)
    │
    ├─5→ Solicita AGENDAS (mesmo sem itens às vezes - agenda é gargalo)
    │
    └─6→ Extrai retorno agendamentos → Altera expedições
         │
         ▼
ROTEIRIZADOR ──────────────────────────────────────────────────────────────────────
    │
    ├─7→ Pega separações → Agrupa por região
    │
    ├─8→ Contrata fretes (otimizando ocupação veículos)
    │    │
    │    ├── Até 4 entregas próximas (sem agenda)
    │    ├── Até 3 entregas não tão próximas
    │    └── 1 com agenda + 1 outro
    │
    ├─9→ Gera EMBARQUE → Imprime separações
    │
    └─10→ Confirma com transportadora/freteiro (informa nº embarque)
          │
          ▼
SEPARADOR ─────────────────────────────────────────────────────────────────────────
    │
    ├─11→ Separa fisicamente
    │     │
    │     └── Se falta → PCP (previsão) → Aguarda ou ajusta
    │
    └─12→ Entrega para FATURAMENTO
          │
          ▼
FATURAMENTO ───────────────────────────────────────────────────────────────────────
    │
    ├─13→ Picking no Odoo → Robô gera fatura
    │
    ├─14→ Transmite NF → Imprime NF + Boletos + Protocolo agenda
    │
    └─15→ Entrega à EXPEDIÇÃO
          │
          ▼
PORTARIA ──────────────────────────────────────────────────────────────────────────
    │
    ├─16→ Registra chegada frete (nº embarque)
    │
    ├─17→ Atualiza status (caminhão entrando)
    │
    └─18→ Registra SAÍDA → Atualiza data_embarque (Embarque + EntregaMonitorada)
          │
          ▼
SISTEMA (Automático) ──────────────────────────────────────────────────────────────
    │
    ├─19→ FaturamentoService importa NF do Odoo
    │
    ├─20→ ProcessadorFaturamento identifica pedido (score) → Vincula ao Embarque
    │
    └─21→ Calcula data_entrega (leadtime CidadeAtendida) para sem agendamento
          │
          ▼
MONITORAMENTO (Torre de Controle) ─────────────────────────────────────────────────
    │
    ├─22→ Cobra posição transportadoras/freteiros
    │
    ├─23→ Registra entregas + Importa canhotos
    │
    ├─24→ Resolve ocorrências
    │
    └─25→ Solicita REAGENDA (perda de agenda ou rejeição)
          │
          ▼
DEVOLUÇÕES ────────────────────────────────────────────────────────────────────────
    │
    ├─26→ Identifica causa
    │
    ├─27→ Se tratável: cota retrabalho + envia caixas
    │
    ├─28→ Se não tratável: cota frete retorno
    │
    └─29→ Se não vale retornar: autoriza DESCARTE
          │
          ▼
AUDITORIA ─────────────────────────────────────────────────────────────────────────
    │
    └─30→ Confere fretes → Lança no Odoo
```

### 4.3 Transporte

| Aspecto | Detalhe |
|---------|---------|
| Frota própria | 1% |
| Terceirizada | 99% |
| Freteiros | ~100 |
| Transportadoras | ~20 |
| Preferência | Definida por preço via CalculadoraFrete |

### 4.4 Regras de Roteirização

| Cenário | Máximo Entregas | Condição |
|---------|-----------------|----------|
| Clientes próximos sem agenda | 4 | - |
| Clientes não tão próximos | 3 | - |
| Com agendamento | 1 + 1 | 1 agendado + 1 outro |
| Carreta direta | 1-3 | ≥26 pallets OU ≥20.000 kg |

### 4.5 Cotação de Frete (3 Níveis)

```
NÍVEL 1: Carga Direta
├── Volume ≥ 26 pallets OU ≥ 20.000 kg
└── Sistema indica opções de carreta

NÍVEL 2: Fracionado por Transportadora
├── Agrupa pedidos por melhor custo
└── Sistema mostra blocos por transportadora

NÍVEL 3: Por Pedido
├── Última opção
└── Mostra todas opções para cada pedido
```

### 4.6 Problemas Frequentes

| # | Problema | Frequência |
|---|----------|------------|
| 1 | Perda de agenda | Alta |
| 2 | Inversão de mercadoria (produto/qtd errado) | ~1x/semana |
| 3 | Falta de mercadoria | Média |

### 4.7 Quando Rafael é Acionado

| Situação | Tipo |
|----------|------|
| Divergência valor vs tabela (transportadora não concorda) | Comercial |
| Freteiro não sabe se aguarda ou volta | Operacional |
| Frete esporádico sem precificação | Técnico |
| Alguém não consegue/tem coragem de decidir | Geral |

---

## PARTE 5: ALGORITMO DE PRIORIZAÇÃO (P1-P7)

### 5.1 Ordem de Análise da Carteira

```
PRIORIDADE 1: Pedidos com data_entrega_pedido
├── NÃO AVALIAR, apenas EXECUTAR
├── Verificar com PCP: produção ok?
│   ├── SIM → Programar expedição
│   └── NÃO → Comercial verificar alteração de data
└── Regra de Expedição:
    ├── SP ou RED (incoterm): expedição = D-1
    ├── SC/PR + peso > 2.000kg: expedição = D-2
    └── Outras regiões: calcular frete → usar lead_time

PRIORIDADE 2: FOB (cliente coleta)
├── SEMPRE mandar COMPLETO
├── Se não for completo: saldo geralmente CANCELADO
└── Cliente não quer vir 2x ao CD

PRIORIDADE 3: Cargas Diretas fora de SP (≥26 pallets OU ≥20.000 kg)
├── Verificar: precisa agenda?
├── SIM → SUGERIR agendamento para D+3 + leadtime
│   └── D+0: Solicita agenda
│   └── D+2: Retorno do cliente
│   └── D+3: Expedição se aprovado
│   └── D+3+leadtime: Entrega
└── NÃO → Programar expedição normal

PRIORIDADE 4: Atacadão (EXCETO loja 183)
└── 50% do faturamento - priorizar sempre

PRIORIDADE 5: Assaí
└── Junior atende SP, Miler atende demais estados

PRIORIDADE 6: Resto
└── Ordenar por data_pedido (mais antigo primeiro)

PRIORIDADE 7: Atacadão 183 (POR ÚLTIMO)
├── Compram muito volume com muitas opções de montagem
└── Se priorizado, pode gerar ruptura em outros clientes
└── Melhor atender o resto e formar carga com o que sobra
```

### 5.2 Hierarquia de Priorização (Regra de Ouro)

```python
def priorizar_pedido():
    # NÍVEL 1: Data já negociada com comercial
    if data_entrega_pedido IS NOT NULL:
        return PRIORIDADE_ALTA  # "Cliente já combinou data"

    # NÍVEL 2: Cliente grande que precisa de agenda
    if cnpj IN ContatoAgendamento AND forma != "SEM AGENDAMENTO":
        return PRIORIDADE_MEDIA_ALTA  # "Cliente grande, dar atenção"

    # NÍVEL 3: Tamanho do pedido
    return ordenar_por_valor_pedido_desc()  # Maior primeiro

# CRITÉRIOS DE ATENÇÃO ESPECIAL:
# - Indústria: sufixo "INDUSTRIA" ou embalagem "BD IND"
# - Top 6 clientes
# - Pedidos > R$ 50K
```

---

## PARTE 6: REGRAS DE ENVIO PARCIAL

### 6.1 Tabela de Decisão

| Falta | Demora | Valor | Decisão |
|-------|--------|-------|---------|
| ≤10% | >3 dias | Qualquer | **PARCIAL automático** |
| 10-20% | >3 dias | Qualquer | **Consultar comercial** |
| >20% | >3 dias | >R$10K | **Consultar comercial** |

### 6.2 Limites de Carga (SEMPRE parcial se exceder)

| Limite | Valor | Comportamento |
|--------|-------|---------------|
| Pallets | ≥30 | PARCIAL obrigatório (max carreta) |
| Peso | ≥25.000 kg | PARCIAL obrigatório |

### 6.3 Casos Especiais

| Situação | Comportamento |
|----------|---------------|
| Pedido FOB | SEMPRE COMPLETO (saldo cancelado se não for) |
| Pedido pequeno (<R$15.000) + Falta ≥10% | AGUARDAR COMPLETO |
| Pedido pequeno (<R$15.000) + Falta <10% + demora ≤5 dias | AGUARDAR |
| Pedido pequeno (<R$15.000) + Falta <10% + demora >5 dias | PARCIAL |

**IMPORTANTE:** Percentual de falta calculado por **VALOR**, não por linhas.

---

## PARTE 7: COMUNICAÇÃO

### 7.1 Comunicação com PCP

| Aspecto | Detalhe |
|---------|---------|
| Canal | Microsoft Teams (ramal como backup) |
| SLA | 30 minutos (máximo) |

**Pergunta padrão:** "Consegue realocar a produção para atender o pedido [X]?"

| Resposta PCP | Ação |
|--------------|------|
| "Sim, vou atualizar" | Aguardar → Programar expedição |
| "Não é possível" | Informar comercial |
| "Vou analisar" | Aguardar retorno |

**Modelo de Mensagem:**
```
Olá PCP,

Preciso de posição sobre produção para atender o pedido [NUM_PEDIDO]:

Cliente: [RAZ_SOCIAL_RED]
Valor: R$ [VALOR]
Itens em falta:
- [PRODUTO_1]: precisa [QTD], tem [ESTOQUE]

Consegue realocar a produção para atender até [DATA]?
```

### 7.2 Comunicação com Comercial

| Cliente | Gestor | Canal |
|---------|--------|-------|
| Atacadão, Assaí SP, Tenda, Spani | Junior | WhatsApp |
| Assaí (outros), Mateus, Dia a Dia | Miler | WhatsApp |
| Indústrias | Fernando | WhatsApp |
| Vendas internas | Denise | Teams |

**Informações que Rafael envia:**
- Itens em falta (lista)
- Previsão de produção (data)
- Outros pedidos que usam mesmos itens (concorrência)
- Causa da falta: ESTOQUE (falta absoluta) ou DEMANDA (falta relativa)

**Perguntas que Rafael faz:**
- Embarcar PARCIAL?
- AGUARDAR produção?
- SUBSTITUIR expedição de outro pedido?

**Modelo de Mensagem:**
```
Olá [GESTOR],

Pedido com ruptura - preciso de orientação:

PEDIDO: [NUM_PEDIDO]
CLIENTE: [RAZ_SOCIAL_RED]
VALOR TOTAL: R$ [VALOR]

ITENS EM FALTA:
- [PRODUTO_1]: precisa [QTD], tem [ESTOQUE] (falta [X]%)

PREVISÃO DE PRODUÇÃO: [DATA] (em [N] dias)

OPÇÕES:
1. Embarcar PARCIAL agora (R$ [VALOR_DISPONIVEL])
2. AGUARDAR produção (entrega em [DATA_PREVISTA])
3. SUBSTITUIR expedição de outro pedido

Qual a orientação?
```

---

## PARTE 8: FLUXO DE AGENDAMENTO

### 8.1 Estados

```
1. Criar separação com data desejada
   → agendamento = data_sugerida
   → agendamento_confirmado = False

2. Solicitar agenda (portal/planilha/email)
   → Aguardar ~2 dias úteis

3a. Cliente aprova na data
   → agendamento_confirmado = True

3b. Cliente aprova OUTRA data
   → agendamento = nova_data
   → agendamento_confirmado = True

4. Se não responde em 2 dias
   → Torre de controle LIGA cobrando
```

### 8.2 Estratégia

- Solicitar agendamento mesmo sem itens (agenda é gargalo #1)
- Pouco adianta saber se terá estoque em 3 ou 5 dias se cliente aprovou agenda para 15 dias

---

## PARTE 9: LEADTIMES DE PLANEJAMENTO

### 9.1 Com data_entrega_pedido Definida

| Destino | Expedição |
|---------|-----------|
| SC/PR (>2.000kg) | data_entrega_pedido - 2 dias úteis |
| SP | data_entrega_pedido - 1 dia útil |
| RED (redespacho) | data_entrega_pedido - 1 dia útil |

### 9.2 Necessita de Agendamento

| Campo | Cálculo |
|-------|---------|
| Expedição | D+3 |
| Agendamento sugerido | D+3 + leadtime |

Fluxo:
- D+0: Solicita agenda
- D+2: Retorno do cliente
- D+3: Expedição (se aprovado)
- D+3+leadtime: Entrega

### 9.3 Outros Casos

| Expedição |
|-----------|
| D+1 |

---

## PARTE 10: VOCABULÁRIO INTERNO

### 10.1 Gírias da Operação

| Termo | Significado |
|-------|-------------|
| "Matar pedido" | Completar 100% do pedido |
| "Formar uma {veículo}" | Chegar próximo à capacidade do veículo |
| "Formar uma carreta" | Formar separação(ões) do mesmo cliente somando até 30 pallets |
| "Lote" | Cargas para RJ - operação pulverizada, pedidos a partir de R$1.500 |
| "Cliente indústria" | Compram embalagens institucionais (BD IND, barricas, tambores, bombonas, MP, BAG) |
| "Vai ter corte" | Pergunta sobre se pedido vai parcial |
| Ruptura / Falta | Falta de estoque |
| Atrasado | Pedido atrasado |

### 10.2 Limites de Veículos

| Veículo | Limite Peso | Limite Pallets |
|---------|-------------|----------------|
| Até Toco | Peso | - |
| Truck | - | 16 pallets |
| Carreta | 24-32 toneladas | 26-30 pallets |

### 10.3 Siglas de Produtos

Produtos são identificados por combinações de:
- Tipo: AZ (Azeitona), COG (Cogumelo), PAL (Palmito), etc.
- Corte: I (Inteira), F (Fatiada), P (Picada), etc.
- Embalagem: POUCH, SACHET, BD (Balde), BD IND (Balde Industrial), etc.

---

## PARTE 11: ESCOPO DO AGENTE LOGÍSTICO

### 11.1 Objetivo

| Métrica | Antes | Depois |
|---------|-------|--------|
| Tempo do Rafael/dia | 2-3 horas | ~30 min (supervisão) |
| Decisões manuais | Todas | Automáticas (seguindo regras) |
| Conhecimento documentado | Na cabeça do Rafael | Sistema |

### 11.2 Fases de Autonomia

**FASE 1 (Atual): SUGERIR**
- Analisar carteira: **Autônomo**
- Identificar rupturas: **Autônomo**
- Comunicar PCP: **Autônomo**
- Comunicar Comercial: **Autônomo**
- Criar separação: **SUGERIR** (usuário confirma)
- Solicitar agendamento: **Autônomo** (só Atacadão)

**FASE 2 (Futuro): AUTOMÁTICO**
- Criar separação: **Autônomo**
- Solicitar todos agendamentos: **Autônomo**

### 11.3 Quando Escalar para Humano

1. Divergência de valor cobrado vs tabela
2. Freteiro não sabe se aguarda ou volta
3. Frete esporádico sem precificação
4. Situação não coberta pelas regras

### 11.4 Limitação

> "Não há algo que eu nunca delegaria pois eu estou disposto a passar quaisquer regras que eu considero para avaliar uma situação" - Rafael

---

## PARTE 12: SAZONALIDADE E EXCEÇÕES

### 12.1 Épocas de Pico

- Natal
- Páscoa

### 12.2 Produtos Sazonais

| Produto | Comportamento |
|---------|---------------|
| Almofadas (tipo_embalagem=SACHET 80 G) | Demanda expressiva no final do ano (cestas de natal) |

### 12.3 Produtos Especiais

| Aspecto | Status |
|---------|--------|
| Shelf life curto | Não existe |
| Produtos que encalham | Sim, mas não conseguem avaliar/controlar hoje |

---

## PARTE 13: IMPLEMENTAÇÃO TÉCNICA

### 13.1 Constantes do Sistema

```python
# Limites para carga direta (exige agendamento)
LIMITE_PALLETS_CARGA_DIRETA = 26
LIMITE_PESO_CARGA_DIRETA = 20000  # kg

# Limites para envio parcial obrigatório
LIMITE_PALLETS_ENVIO_PARCIAL = 30
LIMITE_PESO_ENVIO_PARCIAL = 25000  # kg

# Regras de parcial
LIMITE_FALTA_PARCIAL_AUTO = 0.10        # 10%
LIMITE_FALTA_CONSULTAR = 0.20           # 20%
DIAS_DEMORA_PARA_PARCIAL = 3
VALOR_MINIMO_CONSULTAR_COMERCIAL = 10000
VALOR_PEDIDO_PEQUENO = 15000

# SC/PR com carga direta > 2.000kg = D-2
UFS_CARGA_DIRETA_D2 = ['SC', 'PR']
LIMITE_PESO_CARGA_DIRETA_SC_PR = 2000  # kg

# Atacadão 183 (último na priorização)
IDENTIFICADOR_ATACADAO_183 = '183'
```

### 13.2 Grupos Empresariais (Prefixos CNPJ)

```python
GRUPOS_EMPRESARIAIS = {
    'atacadao': ['93.209.76', '75.315.33', '00.063.96'],
    'assai': ['06.057.22'],
    'tenda': ['01.157.55']
}
```

### 13.3 Script Principal

**Arquivo:** `.claude/skills/gerindo-expedicao/scripts/analisando_carteira_completa.py`

**Saída:**
```json
{
    "pedidos_disponiveis": [...],
    "pcp": [{
        "produto": "PALMITO 500G",
        "qtd_demandada": 50000,
        "estoque_atual": 9967,
        "qtd_faltante": 40033,
        "pedidos_afetados": ["VCD123", "VCD456"]
    }],
    "comercial": {
        "Junior": [{
            "pedido": "VCD123",
            "cliente": "ATACADAO 183",
            "produtos_faltantes": ["PALMITO", "COGUMELO"],
            "percentual_falta": 15,
            "dias_para_disponivel": 5
        }]
    },
    "separacoes_sugeridas": [{
        "pedido": "VCD123",
        "comando": "--pedido VCD123 --expedicao 2025-12-10"
    }],
    "sugestoes_ajuste": [...]
}
```

### 13.4 Prioridades no Sistema

| Código | Descrição |
|--------|-----------|
| 1_data_entrega | Pedidos com data_entrega_pedido |
| 2_fob | FOB (cliente coleta) |
| 3_carga_direta | Cargas diretas fora de SP |
| 4_atacadao | Atacadão (exceto 183) |
| 5_assai | Assaí |
| 6_resto | Resto ordenado por data_pedido |
| 7_atacadao_183 | Atacadão 183 (por último) |

---

## PARTE 14: HISTÓRICO DE CORREÇÕES

### 14.1 Correções Implementadas no Script

| Item | Antes | Depois |
|------|-------|--------|
| Cálculo PCP | Somava falta por pedido | falta = max(0, demanda_total - estoque_atual) |
| Ordem de prioridades | P1-P5 | P1-P7 (adicionado FOB e Atacadão 183) |
| P6 ordenação | Por valor | Por data_pedido (mais antigo primeiro) |
| Regra FOB | Não implementada | AGUARDAR_COMPLETO_FOB |
| Pedido pequeno | Não implementada | <R$15K → tentar COMPLETO |
| Faixa 10-20% | AGUARDAR genérico | CONSULTAR_COMERCIAL |
| Sugestão agendamento P3 | Não calculava | D+3 + leadtime |

### 14.2 Fluxo para Outras Regiões (não SP/RED/SC-PR)

```
1. Buscar cidade por codigo_ibge em CidadeAtendida
2. Para cada transportadora/tabela encontrada:
   ├── Calcular frete (calcular_fretes_possiveis)
   ├── Obter lead_time da CidadeAtendida
   └── data_expedicao = data_entrega - lead_time dias
3. RETORNAR 2 OPÇÕES:
   ├── Mais barata
   └── Mais rápida
```

---

*Documento gerado a partir de entrevistas com Rafael (dono) para transferência de conhecimento tácito ao Agente Logístico.*
