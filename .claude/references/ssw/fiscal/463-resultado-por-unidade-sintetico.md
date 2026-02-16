# Opcao 463 — Resultado por Unidade Sintetico

> **Modulo**: Fiscal
> **Paginas de ajuda**: 1 pagina consolidada
> **Atualizado em**: 2026-02-14

## Funcao
Apresenta o resultado financeiro das unidades de forma sintetica (totais por unidade), baseado em Contas a Receber e Contas a Pagar. Exibe totais de receita, despesa e resultado para visualizacao consolidada.

## Quando Usar
- Analise rapida de resultado financeiro por unidade
- Comparacao de performance entre unidades em formato resumido
- Relatorio gerencial sintetico de receitas vs despesas

## Pre-requisitos
- Cadastro de unidades configurado
- Clientes com unidade responsavel definida (opcao 483)
- Contas a Pagar lancadas com unidade (opcao 475)
- Contas a Receber gerados (fretes faturados)

## Campos / Interface
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Mes/ano | Sim | Periodo desejado para analise |
| Unidade | Nao | Filtro opcional (exclusivo para usuarios MTZ) |

## Fluxo de Uso
1. Acessar opcao 463
2. Informar mes/ano desejado
3. Opcionalmente filtrar por unidade (se MTZ)
4. Executar relatorio
5. Consultar resultado na opcao 156

## Integracao com Outras Opcoes
| Opcao | Relacao |
|-------|---------|
| 156 | Visualizacao do relatorio gerado |
| 464 | Versao analitica (detalhada por evento) |
| 056 | Relatorio 001-SITUACAO GERAL (valores compativeis) |
| 056 | Relatorio 168-RESULTADO DOS SERVICOS PRESTADOS (modelo alternativo) |
| 483 | Define unidade responsavel dos clientes (origem das receitas) |
| 475 | Cadastro de despesas por unidade |

## Observacoes e Gotchas
- **Criterio de receita**: considera fretes de clientes cuja unidade responsavel seja a unidade analisada
- **Criterio de despesa**: considera despesas com vencimento no periodo informado
- **Calculo**: Resultado = Receita - Despesa
- **Compatibilidade de valores**: totais devem bater com relatorio 001-SITUACAO GERAL (opcao 056)
- **Versoes disponiveis**: opcao 463 (sintetico) vs opcao 464 (analitico com detalhamento por evento)
- **Visao geral**: consultar documentacao "Visao Geral - Resultado" para entendimento completo do modelo
