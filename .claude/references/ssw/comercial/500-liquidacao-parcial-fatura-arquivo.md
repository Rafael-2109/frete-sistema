# Opção 500 — Liquidação Parcial de Fatura via Arquivo

> **Módulo**: Comercial/Financeiro
> **Páginas de ajuda**: 2 páginas consolidadas
> **Atualizado em**: 2026-02-15

## Função
Importar arquivo CSV de grandes clientes contendo NFs ou CT-es para liquidar parcialmente CTRCs de faturas, permitindo que clientes liquidem conforme sua conveniência.

## Quando Usar
Quando grandes clientes:
- Enviam arquivo CSV com relação de NFs ou CT-es que desejam liquidar
- Liquidam CTRCs de faturas conforme sua conveniência (não necessariamente fatura completa)
- Precisam ter saldo remanescente na fatura após liquidação parcial

## Pré-requisitos
- Arquivo CSV do cliente com NFs ou CT-es
- CTRCs faturados no sistema
- Conta corrente cadastrada para crédito
- Permissão de acesso à opção

## Campos / Interface

### Tela Inicial — Importação

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| CNPJ cliente | Sim | CNPJ do cliente remetente do arquivo |
| Tipo de CTRC | Sim | **N** (Normal), **D** (Devolução), **R** (Reentrega) |
| Tipo de dado | Sim | Conteúdo do arquivo CSV: **N** (Nota Fiscal), **C** (CT-e) — ambos liquidam CTRCs |
| Coluna da Série | Sim | Número da coluna do arquivo CSV para Série do dado |
| Coluna do Número | Sim | Número da coluna do arquivo CSV para Número do dado |
| Linha de/até | Sim | Faixa de linhas do arquivo a serem importadas |
| Arquivo | Sim | Localização (no micro) do arquivo CSV a ser importado |

### Tela Principal — Processamento

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| CNPJ Cliente | - | Cliente pagador, remetente do arquivo (exibição) |
| Registros lidos | - | Quantidade de linhas importadas |
| CTRCs não encontrados | - | Quantidade de CTRCs lidos mas não localizados no SSW |
| CTRCs liquidados | - | Quantidade de CTRCs já liquidados — nada será feito |
| CTRCs cancelados | - | Quantidade de CTRCs já cancelados — nada será feito |
| CTRCs pendentes | - | Quantidade de CTRCs ainda não faturados — nada será feito |
| CTRCs faturados | - | Quantidade de CTRCs faturados e liquidáveis — valor total exibido |
| Data de pagamento | Sim | Data de liquidação dos CTRCs e crédito na conta corrente — só considera faturas emitidas ≤ esta data |
| C Corrente crédito | Sim | Conta em que o crédito dos CTRCs liquidados ocorrerá |

## Fluxo de Uso

1. Receber arquivo CSV do cliente com NFs ou CT-es
2. Acessar tela inicial da opção 500
3. Informar CNPJ cliente, tipo de CTRC, tipo de dado (N ou C)
4. Configurar colunas (Série, Número) e faixa de linhas do arquivo
5. Selecionar arquivo CSV
6. Sistema importa e exibe tela principal com estatísticas:
   - Registros lidos, CTRCs não encontrados, liquidados, cancelados, pendentes, faturados
7. **Opção 1 — Apenas validar**: Clicar "Gravar retorno no arquivo CSV"
   - Sistema grava situação no próprio arquivo CSV (colunas não utilizadas)
   - Situações: **L** (liquidado), **C** (cancelado), **P** (pendente), **B** (bloqueado), **F** (faturado, liquidável)
   - **NÃO efetua liquidação** — apenas retorna status
8. **Opção 2 — Liquidar**: Informar data de pagamento e conta corrente, clicar "Atualizar CTRCs/Faturas"
   - Sistema liquida CTRCs com situação = F
   - Lança **1 único valor** a crédito na conta corrente (opção 456)
9. Acessar opção 441 para gerar relatório de saldos de faturas
10. Liquidar manualmente faturas parcialmente liquidadas na opção 457

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 457 | Faturas — liquidação manual após avaliação de saldos (instrução 73) |
| 456 | Conta Corrente — recebe crédito em lote (1 valor total) |
| 441 | Relatório de saldos de faturas — usado para avaliar faturas parcialmente liquidadas |
| 411 | Relação de CTRCs liquidados — gera relatório incluindo faturas parcialmente liquidadas |

## Observações e Gotchas

- **Liquidação sempre em CTRCs**: Embora Notas Fiscais possam ser importadas, o processamento e liquidação sempre ocorrem em CTRCs (não em NFs)

- **Liquidação parcial de fatura**: Como toda liquidação é parcial em CTRCs, as liquidações das faturas (opção 457) devem ser efetuadas **manualmente** após avaliação dos saldos — utilizar relatório da opção 441

- **Opção 457 — Instrução 73 vs 89**:
  - **Instrução 73**: CTRCs parcialmente liquidados são considerados no relatório 411
  - **Instrução 89**: CTRCs parcialmente liquidados NÃO são considerados no relatório 411

- **Gravar retorno no CSV**: Função permite validar arquivo SEM efetuar liquidação — útil para conferência antes de processar

- **Situações possíveis no retorno CSV**:
  - **L**: Liquidado (já processado anteriormente)
  - **C**: Cancelado (não será liquidado)
  - **P**: Pendente (ainda não faturado)
  - **B**: Bloqueado (não pode ser liquidado)
  - **F**: Faturado (pode ser liquidado — único status que permite liquidação)

- **Data de pagamento**: Só serão considerados CTRCs cujas faturas foram emitidas **igual ou antes** desta data

- **Crédito único**: Sistema lança apenas 1 valor total na conta corrente (não 1 por CTRC)

- **Arquivo CSV modificado**: Função "Gravar retorno no arquivo CSV" escreve em colunas não utilizadas do próprio arquivo — manter backup do arquivo original se necessário

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-A06](../pops/POP-A06-cadastrar-custos-comissoes.md) | Cadastrar custos comissoes |
| [POP-A07](../pops/POP-A07-cadastrar-tabelas-preco.md) | Cadastrar tabelas preco |
| [POP-A10](../pops/POP-A10-implantar-nova-rota.md) | Implantar nova rota |
| [POP-B01](../pops/POP-B01-cotar-frete.md) | Cotar frete |
