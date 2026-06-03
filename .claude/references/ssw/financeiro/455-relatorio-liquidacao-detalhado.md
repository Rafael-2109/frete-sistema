<!-- doc:meta
tipo: how-to
camada: L2
sot_de: —
hub: .claude/references/ssw/financeiro/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# Opcao 455 — Relatorio de Liquidacao Detalhado

> **Papel:** Opcao 455 — Relatorio de Liquidacao Detalhado.

## Indice

- [Funcao](#funcao)
- [Quando Usar](#quando-usar)
- [Pre-requisitos](#pre-requisitos)
- [Campos / Interface](#campos-interface)
  - [Filtros Disponiveis](#filtros-disponiveis)
  - [Colunas do Relatorio](#colunas-do-relatorio)
- [Fluxo de Uso](#fluxo-de-uso)
  - [Gerar Relatorio de Liquidacao](#gerar-relatorio-de-liquidacao)
  - [Identificar CTRCs com Bloqueio Financeiro](#identificar-ctrcs-com-bloqueio-financeiro)
  - [Obter Arquivo CSV Base para Atualizacao de Previsao de Entrega](#obter-arquivo-csv-base-para-atualizacao-de-previsao-de-entrega)
- [Integracao com Outras Opcoes](#integracao-com-outras-opcoes)
- [Observacoes e Gotchas](#observacoes-e-gotchas)
  - [Valor do Frete vs Base de Calculo](#valor-do-frete-vs-base-de-calculo)
  - [Bloqueio Financeiro](#bloqueio-financeiro)
  - [Descontos Financeiros](#descontos-financeiros)
  - [Arquivo CSV Base](#arquivo-csv-base)
  - [CTRCs Desconsiderados](#ctrcs-desconsiderados)
  - [Periodo de Pesquisa](#periodo-de-pesquisa)
  - [Cancelados/Anulados](#canceladosanulados)
  - [Juros e Descontos](#juros-e-descontos)
  - [Multi-empresa](#multi-empresa)

> **Modulo**: Financeiro
> **Paginas de ajuda**: 2 paginas consolidadas
> **Atualizado em**: 2026-02-14

## Funcao
Gera relatorio detalhado de liquidacao de CTRCs e faturas com filtros avancados, incluindo coluna de descontos (banco e financeira), situacao de bloqueio financeiro e arquivo CSV base para atualizacao em lote de previsao de entrega.

## Quando Usar
- Detalhar valores de CTRCs liquidados vs nao liquidados
- Identificar CTRCs com bloqueio financeiro (liquidacao = B)
- Obter arquivo CSV base para atualizar previsao de entrega em lote (opcao 948)
- Verificar descontos financeiros (banco e financeira) de faturas
- Analisar CTRCs cancelados/anulados
- Comparar valor de frete (a receber) vs base de calculo

## Pre-requisitos
- CTRCs emitidos e autorizados no sistema
- Faturas geradas (se analise de faturamento)
- Periodo de consulta definido

## Campos / Interface

### Filtros Disponiveis
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Periodo de pesquisa | Sim | Data de emissao/autorizacao dos CTRCs |
| Empresa | Condicional | Numero da empresa (se multi-empresa) |
| Unidade | Nao | Unidade fiscal ou de cobranca |
| CNPJ pagador | Nao | CNPJ do cliente pagador |
| Liquidacao | Nao | Situacao: B = Bloqueio Financeiro |
| Tipo de arquivo | Nao | CSV para exportacao |

### Colunas do Relatorio
| Coluna | Descricao |
|--------|-----------|
| CTRC | Serie e numero do CTRC |
| Data autorizacao | Data de autorizacao do CT-e |
| Valor do Frete | Valor a receber (difere da Base de Calculo) |
| Base de Calculo | Valor total do frete (usado na opcao 001) |
| Situacao | Liquidado, Nao Liquidado, Bloqueado, etc |
| DESCONTADA (BANCO) | Desconto bancario (opcao 448) |
| DESCONTADA (FINANCEIRA) | Desconto em financeira (opcao 448) |
| Bloqueio | Motivo do bloqueio financeiro (opcao 462) |

## Fluxo de Uso

### Gerar Relatorio de Liquidacao
1. Acessar opcao 455
2. Informar periodo de pesquisa
3. Selecionar filtros adicionais (empresa, unidade, CNPJ, etc)
4. Escolher tipo de arquivo (PDF ou CSV)
5. Gerar relatorio

### Identificar CTRCs com Bloqueio Financeiro
1. Acessar opcao 455
2. Informar periodo de pesquisa
3. Selecionar liquidacao = B (Bloqueio Financeiro)
4. Gerar relatorio
5. Analisar motivos do bloqueio (coluna Bloqueio)
6. Remover bloqueio pela opcao 462 (se necessario)

### Obter Arquivo CSV Base para Atualizacao de Previsao de Entrega
1. Acessar opcao 455
2. Informar periodo de pesquisa
3. Selecionar tipo de arquivo = CSV
4. Gerar relatorio
5. Baixar arquivo CSV
6. Adicionar coluna "Nova data de previsao de entrega"
7. Importar pela opcao 948

## Integracao com Outras Opcoes

| Opcao | Relacao |
|-------|---------|
| 001 | Situacao Geral - referencia opcao 455 para detalhamento de liquidacao e descontos financeiros |
| 411 | Liquidacao de CTRCs - detalhamento de juros obtidos e descontos concedidos |
| 435 | CTRCs disponiveis para faturar - complementa analise de nao liquidados |
| 441 | Relatorio de faturamento - usa valor do frete (diferente de base de calculo) |
| 448 | Desconto de duplicatas - detalhamento de descontos (banco e financeira) |
| 450 | Relatorio de CTRCs cancelados/anulados |
| 457 | Manutencao de faturas - situacao de faturas perdidas |
| 462 | Bloqueio financeiro - identifica CTRCs bloqueados (liquidacao = B) |
| 520 | Anulacao/substituicao de CTRCs - detalhamento de cancelados e substituidos |
| 948 | Atualizar previsao de entrega em lote - usa arquivo CSV base gerado |

## Observacoes e Gotchas

### Valor do Frete vs Base de Calculo
- **Valor do Frete**: valor a receber (usado nesta opcao 455)
- **Base de Calculo**: valor total do frete (usado na opcao 001 - Situacao Geral)
- Valores podem diferir devido a impostos, descontos e acrescimos

### Bloqueio Financeiro
- CTRCs com liquidacao = B estao bloqueados financeiramente
- Nao podem ser faturados ate desbloqueio (opcao 462)
- Coluna Bloqueio mostra motivo do bloqueio
- Valor de CTRCs bloqueados aparece em Situacao Geral (001) como "BLOQUEIO FINANCEIRO (D)"

### Descontos Financeiros
- Coluna DESCONTADA (BANCO): descontos via arquivo de retorno (opcao 444)
- Coluna DESCONTADA (FINANCEIRA): descontos manuais (opcao 448)
- Detalhamento pode ser obtido para complementar Situacao Geral (001)

### Arquivo CSV Base
- Layout gerado: sigla CTRC; numero CTRC (sem DV); data autorizacao; [campo vazio para nova previsao]
- Usado pela opcao 948 para atualizar previsao de entrega em lote
- Datas devem ter formato DD/MM/AA ou DD/MM/AAAA

### CTRCs Desconsiderados
- CTRCs emitidos pela MTZ (matriz)
- Serie = 999
- CTRCs de anulacao e anulados (opcao 520)
- CTRCs somente para efeito fiscal (opcao 531)

### Periodo de Pesquisa
- Data inicio anterior a 90 dias consulta arquivo morto
- Periodo amplo pode gerar relatorios pesados (considerar usar filtros adicionais)

### Cancelados/Anulados
- Relacao completa obtida pela opcao 450
- Anulacao ocorre pela opcao 520
- Valor aparece em Situacao Geral (001) como "CANCELADOS/ANULADOS (07)"

### Juros e Descontos
- **Juros obtidos**: na liquidacao do CTRC (opcao 411)
- **Descontos concedidos**: diferenca entre valor CTRC e valor liquidado (opcao 411)
- Ambos nao compoem valor de "EMITIDOS" na Situacao Geral (001)

### Multi-empresa
- Campo Empresa disponivel se configuracao multi-empresa ativada (opcao 401)
- Permite filtrar por empresa especifica
