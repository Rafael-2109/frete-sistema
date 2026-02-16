# POP-F03 — Liquidar/Pagar Despesa

> **Categoria**: F — Financeiro: Pagaveis
> **Prioridade**: P1 (Alta — complemento do F01)
> **Status anterior**: A IMPLANTAR
> **Criado em**: 2026-02-15
> **Executor atual**: Ninguem (pagamentos fora do SSW)
> **Executor futuro**: Jaqueline

---

## Objetivo

Efetuar a liquidacao (pagamento efetivo) de despesas programadas no Contas a Pagar ([opcao 475](../financeiro/475-contas-a-pagar.md), POP-F01). A liquidacao registra que o pagamento saiu da conta bancaria, gerando lancamento contabil automatico e atualizando o caixa ([opcao 458](../financeiro/458-caixa-online.md)).

---

## Trigger

- Despesa programada no Contas a Pagar (POP-F01) com data de pagamento atingida
- Aprovacao centralizada concluida (se ativa, [opcao 560](../fiscal/560-aprovacao-despesas.md))
- Acerto de CCF (POP-F02) pronto para pagamento
- Pagamento de CTRB a carreteiro/agregado

---

## Frequencia

Semanal ou por demanda — conforme programacao de pagamentos.

---

## Pre-requisitos

| Requisito | Opcao SSW | O que verificar |
|-----------|-----------|-----------------|
| Despesa programada | [475](../financeiro/475-contas-a-pagar.md) | Numero de lancamento existe (POP-F01) |
| Aprovacao concluida | [560](../fiscal/560-aprovacao-despesas.md) | Se aprovacao centralizada ativa (903), despesa aprovada |
| Conta bancaria | [904](../cadastros/904-bancos-contas-bancarias.md) | Banco/agencia/conta cadastrados |
| Saldo disponivel | — | Conta com saldo suficiente |

---

## Passo-a-Passo

### CENARIO A — Liquidar Uma Despesa

#### ETAPA 1 — Localizar Despesa

1. Acessar [opcao **476**](../financeiro/476-liquidacao-despesas.md)
2. Informar uma das opcoes:

| Campo | Quando usar |
|-------|-------------|
| **Numero de Lancamento** | Sabe o numero (anotado no POP-F01) |
| **CTRB** | Liquidar contratacao especifica |
| **Periodo + Fornecedor** | Buscar por data e CNPJ |

---

#### ETAPA 2 — Escolher Forma de Pagamento

3. Selecionar forma de pagamento:

| Forma | Descricao | Quando usar |
|-------|-----------|-------------|
| **A vista** | Transferencia, PIX, dinheiro | Mais comum para CarVia |
| **Cheque** | Ate 10 cheques por despesa | Se pagamento via cheque |
| **PEF** | Pagamento Eletronico de Fretes | Para CTRBs (carreteiros) |

---

#### ETAPA 3 — Informar Dados do Pagamento

4. Preencher:

| Campo | Valor | Observacao |
|-------|-------|------------|
| **Banco/Agencia/Conta** | Conta CarVia | Cadastrada na [opcao 904](../cadastros/904-bancos-contas-bancarias.md) |
| **Data** | Data da liquidacao | Data em que o dinheiro saiu da conta |
| **Valor** | Valor do pagamento | Pode diferir do programado (juros/desconto) |
| **Juros** | Valor de juros | Se pagamento com atraso |
| **Desconto** | Valor de desconto | Se pagamento antecipado |

---

#### ETAPA 4 — Confirmar e Verificar

5. Conferir resumo:
   - Fornecedor correto
   - Valor correto (incluindo juros/desconto)
   - Conta bancaria correta
   - Data de liquidacao correta
6. Clicar em **Confirmar liquidacao**
7. Sistema gera lancamentos contabeis automaticos:

| Forma | Lancamento contabil |
|-------|---------------------|
| A vista | Credito seq. 63/11, Debito conta credito do evento |
| Cheque | Credito seq. 17, Debito conta credito do evento |
| Desconto | Credito seq. 38, Debito conta credito do evento |
| Juros | Credito conta credito do evento, Debito seq. 47 |

8. Se cheque: imprimir (continuo ou avulso)

---

### CENARIO B — Liquidar Diversas Despesas (Lote)

1. Acessar [opcao **476**](../financeiro/476-liquidacao-despesas.md)
2. Selecionar filtros:

| Filtro | Valor |
|--------|-------|
| **Periodo de inclusao** | Data de lancamento das despesas |
| **Periodo de pagamento** | Data de pagamento programada |
| **Fornecedor** | CNPJ/CPF (ou vazio para todos) |

3. Sistema lista despesas que atendem aos filtros
4. Marcar despesas desejadas
5. Escolher forma: A vista ou 1 cheque
6. Confirmar liquidacao em lote
7. Sistema processa todas as despesas marcadas

---

### CENARIO C — Liquidar via Arquivo Bancario (Opcao 522)

> Opcao mais automatizada — troca de arquivos com o banco.

1. Gerar arquivo de remessa (opcao 522) com despesas programadas
2. Enviar arquivo ao banco
3. Banco processa pagamentos
4. Receber arquivo de retorno do banco
5. Importar retorno na opcao 522
6. Sistema liquida automaticamente despesas confirmadas pelo banco

> **Formatos suportados**: Boleto e PIX via arquivo bancario.

---

## Estorno de Liquidacao

Se uma liquidacao foi feita incorretamente:

1. Acessar [opcao **476**](../financeiro/476-liquidacao-despesas.md)
2. Informar a despesa liquidada (numero de lancamento)
3. Clicar em **"Estornar liquidacao"**
4. Confirmar estorno
5. Sistema reverte lancamentos contabeis automaticamente

> **Restricoes**: So pode estornar quem incluiu a despesa ou usuario MTZ.

---

## Fluxo Completo: Despesa → Pagamento

```
1. Receber NF/CT-e do fornecedor
        ↓
2. Lancar no Contas a Pagar (POP-F01, opcao 475)
        ↓
3. [Se aprovacao ativa] Aprovar (opcao 560)
        ↓
4. Liquidar/Pagar (ESTE POP, opcao 476)
        ↓
5. Caixa/Conta atualizado (opcao 458)
        ↓
6. Conciliacao bancaria (POP-F04, opcao 569)
```

---

## Erros Comuns e Solucoes

| Erro | Causa | Solucao |
|------|-------|---------|
| Despesa nao encontrada | Numero de lancamento incorreto | Verificar opcao 477 |
| Despesa nao aprovada | Aprovacao centralizada pendente | Aprovar na [opcao 560](../fiscal/560-aprovacao-despesas.md) |
| Conta bancaria invalida | Nao cadastrada em [904](../cadastros/904-bancos-contas-bancarias.md) | Cadastrar conta |
| Valor com juros nao registrado | Esqueceu de informar juros | Estornar e reliquidar com juros |
| Estorno nao permitido | Periodo ja conciliado ([569](../financeiro/569-conciliacao-bancaria.md)) | Reabrir conciliacao |
| Cheque nao conciliado | Falta compensar na [opcao 456](../financeiro/456-conta-corrente.md) | Conciliar cheque na 456 |

---

## Verificacao Playwright

| Ponto de verificacao | Como verificar |
|---------------------|----------------|
| Despesa liquidada | Opcao 477 → lancamento → status "Liquidado" |
| Valor correto | Opcao 477 → detalhe → valor liquidacao |
| Caixa atualizado | [Opcao 458](../financeiro/458-caixa-online.md) → periodo → saida registrada |
| Lancamento contabil | [Opcao 558](../contabilidade/558-lancamentos-manuais.md) → lancamento automatico gerado |
| CCF atualizada | [Opcao 486](../financeiro/486-conta-corrente-fornecedor.md) → fornecedor → extrato → acerto registrado |

---

## POPs Relacionados

| POP | Relacao |
|-----|---------|
| POP-F01 | Contas a pagar — pre-requisito (programar despesa) |
| POP-F02 | CCF — acerto de saldo gera despesa para liquidar |
| POP-D01 | Contratar veiculo — gera CTRB que pode ser liquidado aqui |
| POP-F04 | Conciliacao bancaria — conferir pagamentos no final |

---

## Historico de Revisoes

| Data | Alteracao | Autor |
|------|-----------|-------|
| 2026-02-15 | Criacao inicial | Claude (Agente Logistico) |
