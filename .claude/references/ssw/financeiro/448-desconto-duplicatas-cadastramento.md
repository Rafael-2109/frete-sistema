# Opcao 448 — Desconto de Duplicatas - Cadastramento

> **Modulo**: Financeiro
> **Paginas de ajuda**: 4 paginas consolidadas
> **Atualizado em**: 2026-02-14

## Funcao
Cadastra o desconto de duplicatas em carteira junto a financeiras para antecipar recebimentos, registrando faixa de faturas, instituicao financeira, percentual de desconto, valor do credito e data de credito.

## Quando Usar
- Antecipar recebimentos de faturas em carteira (banco = 999)
- Necessidade de capital de giro mediante desconto de duplicatas
- Operacoes de factoring ou antecipacao bancaria

## Pre-requisitos
- Faturas devem estar em cobranca em **carteira** (banco = 999)
- Conta corrente da transportadora cadastrada (opcao 456) ou caixa (opcao 458)
- CNPJ da financeira cadastrado
- Duplicatas podem ser emitidas apos cadastro (opcao 439)

## Campos / Interface
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| UNIDADE CEDENTE | Sim | Unidade cedente das duplicatas (normalmente MTZ) |
| FAIXA DE FATURAS | Sim | Numero inicial/final (com DV) das faturas em carteira a serem descontadas |
| CNPJ DA FINANCEIRA | Sim | CNPJ e nome da instituicao financeira |
| Ender da financeira e CEP | Sim | Endereco completo da financeira |
| Cidade da financeira | Sim | Cidade da instituicao financeira |
| Fone da financeira | Sim | Telefone da instituicao |
| VALOR TOTAL DAS FATURAS | Automatico | Soma dos valores originais das faturas sendo descontadas |
| PERCENTUAL DE DESCONTO | Sim | Percentual de juros cobrado pela financeira |
| VALOR DO CREDITO | Sim | Valor efetivamente creditado (apos desconto) |
| DATA DO CREDITO | Sim | Data do credito na conta corrente ou caixa |
| CREDITADO NO BANCO | Sim | Conta bancaria da transportadora que sera creditada (opcao 456) |

## Fluxo de Uso
1. Acessar opcao 448
2. Informar unidade cedente (normalmente MTZ)
3. Informar faixa de faturas em carteira (com DV)
4. Cadastrar dados da financeira (CNPJ, endereco, telefone)
5. Sistema calcula valor total das faturas automaticamente
6. Informar percentual de desconto da operacao
7. Informar valor do credito (valor liquido apos desconto)
8. Informar data do credito
9. Selecionar conta bancaria que recebera o credito (opcao 456) ou caixa (opcao 458)
10. Gravar desconto
11. Sistema atualiza faturas (opcao 457) e caixa (opcao 458) automaticamente
12. Emitir duplicata fisica pela opcao 439 (se necessario)

## Integracao com Outras Opcoes

| Opcao | Relacao |
|-------|---------|
| 384 | Cadastro de clientes - unidade de cobranca usada se fatura em cobranca bancaria |
| 439 | Emissao de duplicatas - imprime duplicata fisica do desconto cadastrado |
| 441 | Relatorio de faturamento - filtra faturas descontadas |
| 444 | Arquivo de retorno - desconta faturas automaticamente (carteira de desconto) |
| 456 | Conta corrente - recebe credito do desconto |
| 457 | Manutencao de faturas - atualizada com realizacao do desconto |
| 458 | Caixa - recebe credito do desconto (se opcao selecionada) |
| 474 | Situacao das faturas descontadas - relatorio de acompanhamento |
| 492 | Estorno de desconto - reverte operacao de desconto |
| 904 | Carteira de desconto - configuracao de cobranca bancaria |

## Observacoes e Gotchas

### Faturas em Carteira
- Apenas faturas com banco = 999 (carteira) podem ser descontadas manualmente por esta opcao
- Faturas em cobranca bancaria podem ser descontadas automaticamente via arquivo de retorno (opcao 444) se conta configurada como CARTEIRA DE DESCONTO (opcao 904)

### Faixa de Faturas
- Informar numero inicial e final COM digito verificador (DV)
- Sistema valida se todas as faturas estao em carteira
- Valor total calculado automaticamente pelo sistema

### Atualizacao Automatica
- Sistema atualiza automaticamente:
  - Faturas (opcao 457): marca como descontada
  - Conta corrente (opcao 456) ou Caixa (opcao 458): registra credito
- Nao e necessario lancar manualmente em conta corrente/caixa

### Estorno
- Estorno de desconto realizado pela opcao 492
- Reverte atualizacoes em faturas e conta corrente/caixa

### Emissao de Duplicata
- Duplicata fisica emitida pela opcao 439 apos cadastro
- Dados impressos dependem da forma de cobranca:
  - Cobranca em carteira: usa dados da unidade de cobranca do cliente (opcao 384)
  - Cobranca bancaria: usa dados do cedente (opcao 904)

### Relatorios
- Opcao 441 (Relatorio de faturamento): filtra faturas descontadas
- Opcao 474 (Situacao das faturas descontadas): acompanhamento de faturas descontadas e respectivas situacoes

### Percentual de Desconto
- Percentual de juros cobrado pela financeira
- Usado para calcular valor do credito (valor total - desconto)
- Valor do credito deve ser informado manualmente (nao calculado automaticamente)

### Formas de Desconto no SSW
1. **Manual (opcao 448)**: para faturas em carteira, cadastro manual
2. **Automatica via arquivo de retorno (opcao 444)**: para faturas em cobranca bancaria com conta configurada como CARTEIRA DE DESCONTO (opcao 904)

### Data do Credito
- Data em que o valor sera efetivamente creditado na conta corrente ou caixa
- Importante para conciliacao bancaria

### Unidade Cedente
- Normalmente MTZ (matriz)
- Define responsavel pela operacao de desconto

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-E06](../pops/POP-E06-manutencao-faturas.md) | Manutencao faturas |
