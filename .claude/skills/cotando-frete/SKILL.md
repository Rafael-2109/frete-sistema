---
name: cotando-frete
description: |
  Consulta precos de frete por cidade, calcula cotacoes detalhadas e explica logica de calculo.

  USAR QUANDO:
  - Precos/tabelas: "qual preco para Manaus?", "tabelas que atendem Campinas"
  - Cotacao: "quanto sai 5000kg R$50mil para AM?", "frete para SP 3 toneladas"
  - Explicacao: "como funciona o calculo de frete?", "o que e GRIS?"
  - Pedidos: "frete do pedido VCD123", "recalcular frete da separacao"
  - Comparacao: "qual transportadora mais barata para RJ?"
  - Lead time: "prazo de entrega para Manaus?" (lead_time vem nos vinculos)

  NAO USAR QUANDO:
  - Criar embarque/separacao → usar **gerindo-expedicao**
  - Status de entrega pos-faturamento → usar **monitorando-entregas**
  - Consultas analiticas SQL → usar **consultando-sql**
  - Rastrear NF/PO no Odoo → usar **rastreando-odoo**
allowed-tools: Read, Bash, Glob, Grep
---

# Cotando Frete

Skill para consultar precos de frete, calcular cotacoes detalhadas e explicar a logica de calculo.

---

## Indice

1. [Quando NAO Usar Esta Skill](#quando-nao-usar-esta-skill)
2. [DECISION TREE - Qual Script Usar?](#decision-tree---qual-script-usar)
3. [Regras de Negocio (Anti-Alucinacao)](#regras-de-negocio-anti-alucinacao)
4. [Scripts Disponiveis](#scripts-disponiveis)
5. [Exemplos de Uso](#exemplos-de-uso)
6. [Referencia Cruzada](#referencia-cruzada)
7. [References](#references)

---

## Quando NAO Usar Esta Skill

| Situacao | Usar em vez desta |
|----------|-------------------|
| Criar embarque/separacao | **gerindo-expedicao** |
| Status de entrega pos-faturamento | **monitorando-entregas** |
| Consultas analiticas SQL complexas | **consultando-sql** |
| Rastrear NF/PO/pagamento no Odoo | **rastreando-odoo** |
| Analise completa da carteira (P1-P7) | **analista-carteira** (subagente) |

---

## DECISION TREE - Qual Script Usar?

### Mapeamento Rapido

| Se a pergunta menciona... | Use este script | Com estes parametros |
|---------------------------|-----------------|----------------------|
| **Tabelas/precos para cidade** | `buscar_tabelas_cidade.py` | `--cidade "Manaus" --uf AM` |
| **Tabelas por tipo de carga** | `buscar_tabelas_cidade.py` | `--cidade "SP" --uf SP --tipo-carga FRACIONADA` |
| **Cotacao com peso/valor** | `calcular_cotacao.py` | `--peso 5000 --valor 50000 --cidade "Manaus" --uf AM` |
| **Cotacao detalhada (breakdown)** | `calcular_cotacao.py` | `--peso 5000 --valor 50000 --cidade "SP" --uf SP --detalhado` |
| **Menor prazo** | `calcular_cotacao.py` | `--peso X --valor Y --cidade Z --ordenar menor_prazo` |
| **Carga direta especifica** | `calcular_cotacao.py` | `--peso 25000 --valor 200000 --cidade "Curitiba" --uf PR --tipo-carga DIRETA` |
| **Frete de pedido existente** | `consultar_pedido_frete.py` | `--pedido VCD2565291` |
| **Frete de separacao** | `consultar_pedido_frete.py` | `--separacao SEP-2025-001` |
| **Frete de NF** | `consultar_pedido_frete.py` | `--nf 144533` |
| **Recalcular frete** | `consultar_pedido_frete.py` | `--pedido VCD123 --recalcular` |

### Regras de Decisao (em ordem de prioridade)

1. **Se pergunta sobre TABELAS/PRECOS de uma cidade (sem peso/valor):**
   → Use `buscar_tabelas_cidade.py`
   → Exemplo: "quais transportadoras atendem Manaus?" → `--cidade "Manaus" --uf AM`

2. **Se pergunta sobre COTACAO com peso e valor:**
   → Use `calcular_cotacao.py`
   → Exemplo: "quanto sai 5t R$50mil para Manaus?" → `--peso 5000 --valor 50000 --cidade "Manaus" --uf AM`

3. **Se pergunta sobre frete de PEDIDO/SEPARACAO/NF existente:**
   → Use `consultar_pedido_frete.py`
   → Exemplo: "frete do pedido VCD123" → `--pedido VCD123`

4. **Se pergunta sobre EXPLICACAO do calculo:**
   → Leia `references/calculo_frete.md` e explique o passo relevante

5. **Se pergunta sobre TERMOS (GRIS, ADV, etc.):**
   → Leia `references/glossario_frete.md` e explique

### Fluxo de Ambiguidade de Cidade

Se o script retornar `ambiguidade: true`:

```
1. Script retorna: {"ambiguidade": true, "opcoes_uf": ["MG", "SP"]}
2. Agente DEVE perguntar ao usuario: "A cidade X existe em MG e SP. Qual estado?"
3. Usar AskUserQuestion com as opcoes de UF
4. Re-executar script com --uf informada
```

---

## Regras de Negocio (Anti-Alucinacao)

### O Agente PODE Afirmar:

- Precos e valores retornados pelos scripts (baseados em tabelas REAIS)
- Lead time em dias uteis (campo `lead_time` dos vinculos)
- Comparacoes entre transportadoras (baseadas nos resultados)
- Tipo de carga (DIRETA/FRACIONADA) e modalidades disponiveis

### O Agente NAO PODE Inventar:

- Precos de frete sem executar o script
- Lead times sem dados no sistema
- Tabelas de frete que nao existem
- Descontos ou negociacoes especiais
- Capacidade de veiculos sem consultar
- ICMS de cidades sem dados

### Formulas CORRETAS

| Calculo | Formula |
|---------|---------|
| Frete base | `(peso × valor_kg) + (valor_mercadoria × percentual_valor%)` — e SOMA, nao MAX |
| GRIS | `max(valor × percentual_gris%, gris_minimo)` |
| ADV | `max(valor × percentual_adv%, adv_minimo)` |
| RCA | `valor × percentual_rca%` (sem minimo) |
| Pedagio (fracao) | `ceil(peso/100) × pedagio_por_100kg` |
| Pedagio (exato) | `(peso/100) × pedagio_por_100kg` |
| ICMS (nao incluso) | `frete_liquido / (1 - icms)` |
| Valor liquido (optante) | `= valor_com_icms` |
| Valor liquido (nao optante) | `valor_com_icms × (1 - icms)` |

### Frete Minimo - CONFUSAO COMUM

- `frete_minimo_peso` = PESO minimo em kg (NAO e valor em R$)
- `frete_minimo_valor` = VALOR minimo em R$ (piso do frete)
- Sao conceitos DIFERENTES aplicados em momentos DIFERENTES do calculo

---

## Scripts Disponiveis

### 1. buscar_tabelas_cidade.py

Busca todas as tabelas de frete que atendem uma cidade.

```bash
source .venv/bin/activate && python .claude/skills/cotando-frete/scripts/buscar_tabelas_cidade.py [opcoes]
```

**Parametros:**

| Param | Obrig | Descricao |
|-------|-------|-----------|
| `--cidade` | Sim | Nome da cidade (com ou sem acentos) |
| `--uf` | Condicional | Obrigatorio se cidade existir em multiplos estados |
| `--tipo-carga` | Nao | DIRETA ou FRACIONADA |
| `--uf-origem` | Nao | UF de origem (default: SP) |

**Retorno esperado:**
```json
{
  "sucesso": true,
  "cidade": "MANAUS",
  "uf": "AM",
  "codigo_ibge": "1302603",
  "icms_cidade": 0.07,
  "total_tabelas": 5,
  "tabelas": [
    {
      "transportadora": "BRASPRESS",
      "transportadora_id": 42,
      "optante": false,
      "nome_tabela": "TABELA AM 2025",
      "tipo_carga": "FRACIONADA",
      "modalidade": "FRETE PESO",
      "lead_time": 12,
      "valor_kg": 0.85,
      "percentual_valor": 0.30,
      "frete_minimo_peso": 100,
      "frete_minimo_valor": 350.00,
      "percentual_gris": 0.30,
      "gris_minimo": 25.00,
      "percentual_adv": 0.10,
      "adv_minimo": 0,
      "percentual_rca": 0,
      "pedagio_por_100kg": 5.50,
      "valor_tas": 0,
      "valor_despacho": 50.00,
      "valor_cte": 0,
      "icms_incluso": false
    }
  ]
}
```

### 2. calcular_cotacao.py

Calcula cotacao de frete detalhada para peso/valor/destino.

```bash
source .venv/bin/activate && python .claude/skills/cotando-frete/scripts/calcular_cotacao.py [opcoes]
```

**Parametros:**

| Param | Obrig | Descricao |
|-------|-------|-----------|
| `--peso` | Sim | Peso em kg |
| `--valor` | Sim | Valor da mercadoria em R$ |
| `--cidade` | Sim | Nome da cidade destino |
| `--uf` | Condicional | Se cidade ambigua |
| `--tipo-carga` | Nao | DIRETA ou FRACIONADA |
| `--uf-origem` | Nao | UF de origem (default: SP) |
| `--detalhado` | Nao | Flag para breakdown completo |
| `--ordenar` | Nao | menor_valor (default) ou menor_prazo |
| `--limite` | Nao | Max opcoes (default: 10) |

**Retorno esperado:**
```json
{
  "sucesso": true,
  "parametros": {"peso": 5000, "valor": 50000, "cidade": "MANAUS", "uf": "AM"},
  "total_opcoes": 3,
  "melhor_opcao": {
    "transportadora": "BRASPRESS",
    "valor_com_icms": 3495.16,
    "criterio": "menor_valor"
  },
  "opcoes": [
    {
      "posicao": 1,
      "transportadora": "BRASPRESS",
      "nome_tabela": "TABELA AM 2025",
      "tipo_carga": "FRACIONADA",
      "modalidade": "FRETE PESO",
      "lead_time": 12,
      "valor_bruto": 3250.50,
      "valor_com_icms": 3495.16,
      "valor_liquido": 3250.50,
      "frete_por_kg": 0.699,
      "percentual_sobre_valor": 6.99
    }
  ]
}
```

### 3. consultar_pedido_frete.py

Consulta dados de frete de pedidos existentes.

```bash
source .venv/bin/activate && python .claude/skills/cotando-frete/scripts/consultar_pedido_frete.py [opcoes]
```

**Parametros:**

| Param | Obrig | Descricao |
|-------|-------|-----------|
| `--pedido` | * | Numero do pedido (VCD/VFB). Busca em separacao E carteira. Se multiplos contextos, retorna `resumo.requer_clarificacao=true` |
| `--separacao` | * | Lote de separacao |
| `--nf` | * | Numero da NF |
| `--recalcular` | Nao | Recalcular com tabelas atuais |

\* Pelo menos um obrigatorio

**Fontes de dados por parametro:**
- `--pedido` → busca UNIFICADA: `separacao` (sincronizado_nf=false) + `carteira_principal` (saldo ativo). Retorna todos os contextos do pedido
- `--separacao` → busca em `separacao` (sincronizado_nf=false, qtd_saldo>0)
- `--nf` → busca em `faturamento_produto`

**Quando --pedido retorna multiplos contextos:**

O mesmo pedido pode ter simultaneamente:
- 1 ou mais separacoes (`separacao_lote_id`) com `sincronizado_nf=False`
- Saldo remanescente na `carteira_principal` (parte nao separada)

Se `resumo.requer_clarificacao = true`:
1. Apresentar os contextos ao usuario (separacao X, separacao Y, saldo carteira)
2. Usar AskUserQuestion para o usuario escolher qual contexto
3. NAO calcular frete de todos sem perguntar — cada contexto tem peso/valor diferente

Se `resumo.requer_clarificacao = false` (1 unico contexto):
- Usar direto, sem perguntar

**Retorno esperado (--pedido):**
```json
{
  "sucesso": true,
  "fonte": "pedido_unificado",
  "total": 3,
  "resumo": {
    "tem_separacao": true,
    "tem_carteira": true,
    "qtd_separacoes": 2,
    "separacoes": ["SEP-2025-001", "SEP-2025-002"],
    "qtd_carteira": 1,
    "requer_clarificacao": true
  },
  "pedidos": [
    {
      "tipo": "separacao",
      "separacao_lote_id": "SEP-2025-001",
      "num_pedido": "VCD2565291",
      "cnpj": "12345678000190",
      "cliente": "ATACADAO SA",
      "cidade": "MANAUS",
      "uf": "AM",
      "codigo_ibge": "1302603",
      "valor_total": 45000.00,
      "peso_total": 3500,
      "peso_fonte": "separacao"
    },
    {
      "tipo": "carteira",
      "num_pedido": "VCD2565291",
      "cnpj": "12345678000190",
      "cliente": "ATACADAO SA",
      "cidade": "MANAUS",
      "uf": "AM",
      "valor_total": 12000.00,
      "peso_total": 800,
      "peso_fonte": "palletizacao_estimado",
      "incoterm": "CIF"
    }
  ]
}
```

---

## Exemplos de Uso

### Cenario 1: Tabelas para uma cidade

```
Pergunta: "quais transportadoras atendem Manaus?"
Raciocinio: Pergunta sobre TABELAS/PRECOS → buscar_tabelas_cidade.py
Comando: --cidade "Manaus" --uf AM
Resultado: "Encontrei 5 tabelas de frete para Manaus/AM: [lista com transportadora, tipo, lead_time]"
```

### Cenario 2: Cotacao com peso e valor

```
Pergunta: "quanto sai frete de 5 toneladas, R$ 50 mil para Manaus?"
Raciocinio: Peso + valor + cidade → calcular_cotacao.py
Comando: --peso 5000 --valor 50000 --cidade "Manaus" --uf AM
Resultado: "A melhor opcao e BRASPRESS por R$ 3.495,16 (com ICMS). Lead time: 12 dias uteis."
```

### Cenario 3: Comparacao entre transportadoras

```
Pergunta: "qual transportadora mais barata para Curitiba com 3 toneladas?"
Raciocinio: Comparacao → calcular_cotacao.py (lista todas ordenadas)
Comando: --peso 3000 --valor 30000 --cidade "Curitiba" --uf PR
Resultado: Tabela comparativa com top opcoes ordenadas por valor
```

### Cenario 4: Frete de pedido existente (unico contexto)

```
Pergunta: "qual o frete do pedido VCD2565291?"
Raciocinio: Pedido existente → consultar_pedido_frete.py
Comando: --pedido VCD2565291
Se resumo.requer_clarificacao=false (1 contexto):
  Resultado: "O pedido VCD2565291 (ATACADAO SA, Sao Paulo/SP) tem peso 12.500kg, valor R$ 85.000."
Se resumo.requer_clarificacao=true (multiplos contextos):
  Resultado: AskUserQuestion com opcoes:
    - "Separacao SEP-001 (3.500kg, R$ 45.000)"
    - "Separacao SEP-002 (1.200kg, R$ 18.000)"
    - "Saldo em carteira (800kg, R$ 12.000)"
```

### Cenario 5: Recalcular frete de pedido

```
Pergunta: "recalcula o frete do VCD2565291 com as tabelas atuais"
Raciocinio: Pedido + recalcular → consultar_pedido_frete.py --recalcular
Comando: --pedido VCD2565291 --recalcular
Resultado: "Recalculei com tabelas atuais. Melhor opcao: [transportadora] por R$ [valor]."
```

### Cenario 6: Explicar calculo de frete

```
Pergunta: "como funciona o calculo de frete?"
Raciocinio: Pergunta explicativa → ler references/calculo_frete.md
Acao: Ler o reference e explicar os 10 passos ao usuario
```

---

## Referencia Cruzada

| Skill | Quando usar em vez desta |
|-------|--------------------------|
| **gerindo-expedicao** | Criar embarque/separacao (antes de faturar) |
| **monitorando-entregas** | Status de entrega (apos faturar) |
| **consultando-sql** | Consultas analiticas complexas (rankings, agregacoes) |
| **rastreando-odoo** | Rastrear NF/PO/pagamento no Odoo |
| **resolvendo-entidades** | Resolver cliente/cidade para IDs (usar antes se necessario) |

---

## References (sob demanda)

| Gatilho na Pergunta | Reference a Ler | Motivo |
|---------------------|-----------------|--------|
| "como funciona o calculo?", "explique o calculo", "por que esse valor?" | `references/calculo_frete.md` | Logica completa passo-a-passo (10 passos) |
| "o que e GRIS?", "significado de ADV", "termos de frete" | `references/glossario_frete.md` | Terminologia e definicoes |
| "o que e frete minimo peso?", "diferenca entre peso e valor minimo" | `references/calculo_frete.md` Passo 2 e Passo 6 | Confusao comum |
| "como funciona ICMS no frete?", "optante vs nao optante" | `references/calculo_frete.md` Passo 8 e Passo 9 | Logica ICMS |
| "direta vs fracionada", "o que e carga direta?" | `references/glossario_frete.md` + `references/calculo_frete.md` | Tipos de carga |

---

## Tabelas do Dominio

| Tabela | Descricao | Usada por |
|--------|-----------|-----------|
| `cidades` | Cadastro de cidades com ICMS e codigo_ibge | Resolucao de cidade |
| `cidades_atendidas` | Vinculos transportadora ↔ cidade (lead_time) | buscar_tabelas_cidade.py |
| `tabelas_frete` | Tabelas de preco por transportadora/UF/tipo | buscar_tabelas_cidade.py, calcular_cotacao.py |
| `transportadoras` | Cadastro com flags aplica_*_pos_minimo | Calculo de frete |
| `veiculos` | Capacidade por tipo (VAN, TOCO, etc.) | Carga DIRETA |
| `carteira_principal` | Pedidos em carteira com saldo | consultar_pedido_frete.py |
| `separacao` | Separacoes com peso real | consultar_pedido_frete.py |
| `faturamento_produto` | NFs faturadas | consultar_pedido_frete.py |
