# Opcao 456 — Conta Corrente

> **Modulo**: Financeiro
> **Paginas de ajuda**: 2 paginas consolidadas
> **Atualizado em**: 2026-02-14

## Funcao
Controla lancamentos de debitos e creditos nas contas correntes bancarias da transportadora, incluindo saldo diario, conciliacao bancaria, e integracao com contas a pagar, contas a receber, aplicacoes financeiras, emprestimos e ACNI (Adiantamentos e Creditos Nao Identificados).

## Quando Usar
- Consultar saldo de conta corrente bancaria
- Visualizar lancamentos de debitos e creditos
- Conciliar conta corrente com extrato bancario (opcoes 569 e 669)
- Lancar e conciliar despesas diretamente na conta
- Verificar integracao com contas a pagar e receber
- Acompanhar descontos de duplicatas (opcao 448)
- Monitorar aplicacoes financeiras (opcao 470) e emprestimos (opcao 416)

## Pre-requisitos
- Conta corrente bancaria cadastrada (banco, agencia, conta)
- Empresa configurada (se multi-empresa via opcao 401)
- Acesso ao extrato bancario (para conciliacao)

## Campos / Interface

### Consulta de Conta Corrente
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Empresa | Condicional | Numero da empresa (se multi-empresa) |
| Banco/Ag/CCor | Sim | Conta corrente a ser consultada |
| Data inicio | Sim | Data inicial para visualizar lancamentos |
| Data fim | Sim | Data final para visualizar lancamentos |

### Lancamentos
| Coluna | Descricao |
|--------|-----------|
| Data | Data do lancamento |
| Historico | Descricao do lancamento (origem, CTRC, fatura, etc) |
| Debito | Valor debitado da conta |
| Credito | Valor creditado na conta |
| Saldo | Saldo apos o lancamento |
| Conciliado | Marcacao se lancamento conciliado com extrato |
| seq_extr | Sequencia do extrato (contas conciliadas tem mesmo seq_extr) |

### Lancamento Manual (Link: Lancar e conciliar despesas)
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Data lancamento | Sim | Data do debito/credito |
| Valor | Sim | Valor do lancamento |
| Historico | Sim | Descricao do lancamento |
| Tipo | Sim | Debito ou Credito |

## Fluxo de Uso

### Consultar Saldo e Lancamentos
1. Acessar opcao 456
2. Selecionar conta corrente (Banco/Ag/CCor)
3. Informar periodo de consulta
4. Visualizar lancamentos e saldo diario

### Lancar Despesa Diretamente na Conta
1. Acessar opcao 456
2. Selecionar conta corrente
3. Clicar em "Lancar e conciliar despesas"
4. Informar data, valor, historico e tipo (debito/credito)
5. Confirmar lancamento
6. Lancamento entra automaticamente como conciliado

### Conciliar Conta Corrente (Versao Antiga - Opcao 569)
1. Acessar opcao 569
2. Selecionar conta corrente
3. Informar dia a conciliar
4. Marcar lancamentos conferidos com extrato bancario
5. Incluir lancamentos ausentes (via opcoes 475, 476, 048, 571, 470, 416)
6. Confirmar conciliacao quando saldo SSW = saldo extrato

### Conciliar Conta Corrente (Versao Nova - Opcao 669)
1. Obter extrato bancario em CSV do banco
2. Acessar opcao 669
3. Selecionar conta corrente
4. Importar arquivo CSV do extrato
5. Configurar colunas (Data, Historico, Debito, Credito)
6. Configurar filtros de texto (nao importar aplicacoes automaticas)
7. Sistema concilia automaticamente lancamentos unicos coincidentes
8. Marcar pares de lancamentos manualmente (SSW x extrato)
9. Criar ACNI para creditos nao identificados (link em tela)
10. Lancar despesas para debitos ausentes (link em tela)
11. Confirmar conciliacao quando "Dif SSW-extr" = 0

## Integracao com Outras Opcoes

| Opcao | Relacao |
|-------|---------|
| 048 | Liquidacao de CTRCs e faturas - credita valores na conta corrente |
| 416 | Emprestimo bancario - lanca debitos/creditos na conta |
| 448 | Desconto de duplicatas - credita valor do desconto na conta |
| 470 | Aplicacao financeira - debita aplicacoes e credita resgates |
| 475, 476 | Contas a Pagar - debita pagamentos na conta |
| 569 | Conciliacao bancaria (versao antiga) - marca lancamentos como conciliados |
| 571 | ACNI - lanca creditos nao identificados na conta |
| 669 | Conciliacao bancaria com CSV (versao nova) - concilia usando extrato CSV |

## Observacoes e Gotchas

### Origem dos Lancamentos
- **Contas a Pagar**: debitos via opcoes 475 e 476
- **Contas a Receber**: creditos via opcao 048 (liquidacao de CTRCs, faturas)
- **ACNI**: creditos via opcao 571 (adiantamentos e creditos nao identificados)
- **Aplicacao financeira**: debitos (aplicacao) e creditos (resgate) via opcao 470
- **Emprestimo bancario**: debitos e creditos via opcao 416
- **Desconto de duplicatas**: creditos via opcao 448
- **Lancamento manual**: debitos/creditos diretos na opcao 456 (ja entram conciliados)

### Conciliacao Bancaria
- **Objetivo basico**: tornar contas financeiras do SSW aderentes ao mundo real (extrato bancario)
- **Consistencia geral**: conciliacao do financeiro provoca consistencia de contas a pagar, contas a receber, contabil e fiscal
- **Lancamento conciliado**: valor encontrado no extrato bancario ou cofre/gaveta
- **Dia conciliado**: saldo final SSW = saldo final extrato

### Duas Versoes de Conciliacao
- **Opcao 569 (antiga)**: marca lancamentos manualmente como conciliados usando extrato em papel
- **Opcao 669 (nova)**: importa extrato CSV, concilia automaticamente lancamentos unicos coincidentes, permite filtros de texto

### Filtros de Texto (Opcao 669)
- Lancamentos com texto especifico no historico podem ser excluidos da importacao
- Util para aplicacoes e resgates automaticos
- Texto configurado pela Equipe SSW (pode ser ajustado)

### seq_extr
- Sequencia de controle de conciliacao
- Contas conciliadas apresentam o mesmo seq_extr
- Desconciliar: desmarcar X na coluna seq_extr

### ACNI - Adiantamentos e Creditos Nao Identificados
- Criados pela opcao 571 quando credito existe no extrato mas nao na conta SSW
- Permitem conciliar conta mesmo sem identificar origem do credito
- Posteriormente podem ser liquidados (opcao 048) quando fatura/CTRC identificado
- Podem ser alterados ou excluidos se nenhuma identificacao foi efetuada e conta nao conciliada

### Lancamentos que Entram Automaticamente Conciliados
- ACNI (opcao 571)
- Aplicacao financeira (opcao 470)
- Emprestimo bancario (opcao 416)
- Lancar e conciliar despesas (opcao 456 - lancamento manual)

### Busca de Lancamentos (Opcao 669)
- **Busca no Historico**: localiza lancamentos por palavra no historico
- **Busca numero**: localiza por valor em colunas de debito e credito

### Multi-empresa
- Campo Empresa disponivel se configuracao multi-empresa ativada (opcao 401)
- Cada empresa possui contas correntes separadas

### Layout CSV (Opcao 669)
- **Data**: DD/MM/AA, DD/MM/AAAA ou DD
- **Historico**: ate 4 colunas podem compor historico
- **Debito**: coluna exclusiva para debitos
- **Credito**: coluna exclusiva para creditos
- **Debito/credito**: coluna unica com debitos e creditos (sinal negativo) - nao pode ser usada junto com colunas separadas

### Limitacoes
- Alteracao e exclusao de ACNI apenas se conta nao conciliada
- Alteracao de ACNI apenas se nenhuma identificacao foi efetuada

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-F03](../pops/POP-F03-liquidar-despesa.md) | Liquidar despesa |
| [POP-F04](../pops/POP-F04-conciliacao-bancaria.md) | Conciliacao bancaria |
