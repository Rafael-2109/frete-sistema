# Opcao 380 — Definicao do Orcamento

> **Modulo**: Comercial
> **Paginas de ajuda**: 1 pagina consolidada
> **Atualizado em**: 2026-02-14

## Funcao
Define limites de gastos (orcamentos) por EVENTO e UNIDADE, permitindo acompanhamento e controle (bloqueio opcional) de despesas lancadas no sistema. Despesas sao contabilizadas na DATA DE PAGAMENTO.

## Quando Usar
- Definir orcamento anual por evento e unidade
- Controlar gastos de despesas por categoria (evento) e local (unidade)
- Replicar orcamento de janeiro para demais meses do ano
- Duplicar orcamento de uma unidade referencia para outras unidades
- Planejar limites de gastos antes de iniciar novo ano fiscal

## Pre-requisitos
- Eventos cadastrados no sistema
- Unidades cadastradas
- Para controle com bloqueio: ativacao na opcao 903/Outros (sem ativacao, apenas acompanhamento)

## Campos / Interface

### Tela Inicial
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Ano | Sim | Ano que ocorrera o pagamento da despesa (opcao 475) e controle orcamentario (formato AA) |
| Unidade | Sim | Unidade da despesa |

### Duplicar e Replicar
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Ano | Condicional | Ano (AA) de referencia do orcamento, origem da duplicacao ou replicacao |
| Unidade referencia | Condicional | Origem da duplicacao ou replicacao |
| Replicar JANEIRO para demais meses | Nao | Replica orcamento do mes de janeiro para demais meses do ano de referencia, sobrepondo dados existentes |
| Duplicar para | Nao | Copia orcamento do ano e unidade para a unidade informada, sobrepondo dados existentes |

### Tela Principal
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Eventos x Meses (tabela) | Sim | Por Evento e mes, informar limites de gastos (considerar data de pagamento da opcao 475) |
| Totais mensais (topo) | Visualizacao | Totais mensais dos valores cadastrados por Evento |

## Fluxo de Uso

### Cadastro Normal
1. Selecionar ano (AA) e unidade
2. Preencher tabela de limites por Evento x Mes
3. Parte superior da tela mostra totais mensais automaticamente
4. Salvar orcamento
5. Despesas lancadas (opcao 475) serao contabilizadas na data de pagamento
6. Acompanhar via relatorios (opcao 056 ou 464)

### Replicar Janeiro para Demais Meses
1. Cadastrar orcamento de janeiro para todos os eventos
2. Usar funcao "Replicar JANEIRO para demais meses"
3. Sistema copia valores de janeiro para fevereiro-dezembro do mesmo ano
4. Dados existentes sao SOBREPOSTOS

### Duplicar Orcamento de Unidade Referencia
1. Definir ano e unidade de referencia (origem)
2. Informar unidade destino no campo "Duplicar para"
3. Sistema copia todo o orcamento do ano da unidade origem para unidade destino
4. Dados existentes sao SOBREPOSTOS

## Integracao com Outras Opcoes
| Opcao | Relacao |
|-------|---------|
| 475 | Lancamento de despesas — contabilizadas por Evento e Unidade na data de pagamento |
| 056 | Relatorio 001 "Situacao Geral" — acompanhamento do atingimento do orcamento |
| 464 | Relatorio "Situacao por Unidade" — acompanhamento do atingimento do orcamento |
| 903/Outros | Ativacao do controle orcamentario (bloqueio de despesas alem do orcamento) |

## Observacoes e Gotchas
- **Data de pagamento**: despesas sao contabilizadas na DATA DE PAGAMENTO (opcao 475), nao na data de lancamento
- **Ativacao de controle**: sem ativacao na opcao 903/Outros, sistema apenas ACOMPANHA (nao bloqueia despesas acima do orcamento)
- **Sobrepor dados**: funcoes "Replicar" e "Duplicar" SOBREPOEM dados existentes (nao adicionam)
- **Totais automaticos**: parte superior da tela mostra totais mensais calculados automaticamente conforme cadastro por evento
- **Formato AA**: ano deve ser informado com 2 digitos (ex: 26 para 2026)
- **Evento**: categoria de despesa (ex: combustivel, manutencao, pedagio, salarios, etc.)
- **Acompanhamento vs. Controle**:
  - Acompanhamento: visualiza se esta dentro do limite (via relatorios)
  - Controle: BLOQUEIA lancamento de despesa que ultrapasse limite (requer ativacao na 903)

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-F06](../pops/POP-F06-aprovar-despesas.md) | Aprovar despesas |
