# Opcao 458 — Caixa Online

> **Modulo**: Financeiro
> **Paginas de ajuda**: 1 pagina consolidada
> **Atualizado em**: 2026-02-14

## Funcao
Controla lancamentos de entrada e saida de caixa em tempo real, incluindo saldo diario, conciliacao, e integracao com contas a pagar, contas a receber, desconto de duplicatas e conta corrente de fornecedores.

## Quando Usar
- Consultar saldo de caixa
- Visualizar entradas e saidas do dia
- Lancar movimentacoes de caixa (dinheiro em especie)
- Conciliar caixa com contagem fisica (gavetas, cofres)
- Acompanhar CTRCs disponiveis para faturar
- Verificar saldo de conta corrente de fornecedores com CCF
- Gerar relatorio de situacao do caixa (opcao 056 - Relatorio 100)

## Pre-requisitos
- Caixa cadastrado na opcao 904 (contas bancarias e caixas)
- Eventos de despesa cadastrados (opcao 477)
- Grupos de eventos configurados (opcao 503) para totalizacao

## Campos / Interface

### Consulta de Caixa
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Data inicio | Sim | Data inicial para visualizar lancamentos |
| Data fim | Sim | Data final para visualizar lancamentos |
| Caixa | Sim | Codigo do caixa (cadastrado na opcao 904) |

### Lancamentos
| Coluna | Descricao |
|--------|-----------|
| Data | Data do lancamento |
| Historico | Descricao da movimentacao |
| Entrada | Valor de entrada em caixa |
| Saida | Valor de saida de caixa |
| Saldo | Saldo apos o lancamento |
| Conciliado | Marcacao se lancamento conciliado com contagem fisica |

## Fluxo de Uso

### Consultar Saldo de Caixa
1. Acessar opcao 458
2. Selecionar caixa
3. Informar periodo de consulta
4. Visualizar lancamentos e saldo diario

### Lancar Movimentacao de Caixa
1. Acessar opcao 458
2. Selecionar caixa
3. Informar data, tipo (entrada/saida), valor e historico
4. Confirmar lancamento

### Conciliar Caixa com Contagem Fisica
1. Realizar contagem fisica de dinheiro (gaveta, cofre)
2. Acessar opcao 458 ou 569
3. Comparar saldo SSW com contagem fisica
4. Incluir lancamentos ausentes (se necessario)
5. Marcar dia como conciliado quando saldo SSW = contagem fisica

### Gerar Relatorio de Situacao do Caixa
1. Acessar opcao 056
2. Selecionar Relatorio 100 - Situacao do Caixa
3. Informar periodo
4. Gerar relatorio com:
   - Entradas nas contas (opcao 904)
   - CTRCs disponiveis para faturar (opcao 435)
   - Saidas totalizadas por Eventos (opcao 477)
   - Grupos de Eventos (opcao 503)
   - Saldo de Conta Corrente de Fornecedor (opcao 611)
   - Saldo diario geral da transportadora
   - Indicacao de dias conciliados (opcao 569)

## Integracao com Outras Opcoes

| Opcao | Relacao |
|-------|---------|
| 056 | Relatorios Gerenciais - Relatorio 100 (Situacao do Caixa) |
| 435 | CTRCs disponiveis para faturar - mostrado no relatorio 100 |
| 448 | Desconto de duplicatas - credita valor em caixa (se opcao selecionada) |
| 477 | Cadastro de eventos - saidas totalizadas no relatorio |
| 478 | Cadastro de fornecedores - define CCF ativado |
| 503 | Grupos de eventos - totalizacao de saidas no relatorio |
| 569 | Conciliacao bancaria - marca dias como conciliados |
| 611 | Conta Corrente de Fornecedor - saldo mostrado no relatorio 100 |
| 904 | Cadastro de contas bancarias e caixas - define caixas disponiveis |

## Observacoes e Gotchas

### Diferenca entre Caixa e Conta Corrente
- **Caixa (opcao 458)**: movimentacoes de dinheiro em especie (gavetas, cofres)
- **Conta Corrente (opcao 456)**: movimentacoes bancarias (debitos, creditos, transferencias)
- Ambos cadastrados na opcao 904

### Origem dos Lancamentos
- **Entradas**: liquidacao de CTRCs a vista, desconto de duplicatas (se opcao selecionada), transferencias
- **Saidas**: pagamentos a fornecedores em dinheiro, despesas em especie, transferencias

### Conciliacao de Caixa
- Similar a conciliacao bancaria (opcao 569), mas usa contagem fisica em vez de extrato
- Objetivo: igualar saldo SSW com dinheiro fisico em gavetas/cofres
- Dia conciliado indicado no relatorio 100

### Relatorio 100 - Situacao do Caixa
- **Horario de processamento**: timestamp de geracao do relatorio
- **Valores em R$ 1.000**: valores apresentados em milhares
- **Entradas**: contas cadastradas na opcao 904
- **CTRCs disponiveis para faturar**: opcao 435
- **Saidas**: eventos (opcao 477) agrupados (opcao 503)
- **Saldo CCF**: conta corrente de fornecedores com CCF ativado (opcao 478)
- **Saldo diario geral**: resultado do dia (entradas - saidas)
- **Dia conciliado**: marcacao de conciliacao (opcao 569)

### Desconto de Duplicatas
- Opcao 448 pode creditar valor do desconto em caixa (em vez de conta corrente)
- Util para operacoes com financeiras que pagam em dinheiro

### Saldo de Conta Corrente de Fornecedor (CCF)
- Mostrado no relatorio 100 para fornecedores com CCF ativado (opcao 478)
- Opcao 611 detalha saldo de CCF por fornecedor
- Util para acompanhar saldo devedor/credor com fornecedores estrategicos

### Grupos de Eventos
- Opcao 503 agrupa eventos (opcao 477) para totalizacao no relatorio
- Facilita analise de despesas por categoria (combustivel, manutencao, pessoal, etc)

### CTRCs Disponiveis para Faturar
- Opcao 435 lista CTRCs ainda nao faturados
- Valor mostrado no relatorio 100 como entrada potencial
- Importante para gestao de fluxo de caixa

### Conciliacao Manual vs Automatica
- Caixa (opcao 458): conciliacao manual via contagem fisica
- Conta Corrente (opcao 456): conciliacao com extrato CSV (opcao 669) ou manual (opcao 569)

### Cadastro de Caixas
- Realizado na opcao 904 (mesma opcao de contas bancarias)
- Define nome, codigo e tipo (caixa ou conta corrente)
- Caixas podem ser por filial, por tipo de operacao, etc

### Multiempresa
- Se configuracao multi-empresa ativada (opcao 401), caixas podem ser separados por empresa
- Relatorio 100 pode ser filtrado por empresa

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-E05](../pops/POP-E05-liquidar-fatura.md) | Liquidar fatura |
| [POP-F01](../pops/POP-F01-contas-a-pagar.md) | Contas a pagar |
| [POP-F03](../pops/POP-F03-liquidar-despesa.md) | Liquidar despesa |
