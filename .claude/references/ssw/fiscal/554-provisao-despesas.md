# Opcao 554 — Provisao de Despesas

> **Modulo**: Fiscal
> **Paginas de ajuda**: 1 pagina consolidada
> **Atualizado em**: 2026-02-14

## Funcao
Efetua provisionamento de despesas sem gerar lancamentos financeiros ou contabeis. Permite antecipar impacto de despesas em relatorios gerenciais (Situacao do Caixa, Resultado de Unidades) antes do lancamento definitivo.

## Quando Usar
- Antecipar despesas esperadas em relatorios gerenciais
- Visualizar impacto de despesas recorrentes antes do lancamento definitivo
- Evitar lancamento/estorno de despesas provisorias no Contas a Pagar
- Provisionar despesas mensais para analise de resultado

## Pre-requisitos
- Unidades cadastradas
- Fornecedores cadastrados (opcao 478)
- Eventos de despesa configurados (opcao 503)
- Entendimento de que provisao NAO gera lancamentos financeiros/contabeis

## Campos / Interface
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Unidade | Sim | Sigla da unidade para qual despesa sera provisionada |
| Ano | Sim | Ano de referencia para provisionamento mensal |
| Fornecedor | Sim | CNPJ/CPF do fornecedor (opcao 478) |
| Com Evento | Sim | Classificacao da despesa pela tabela de Eventos (opcao 503) |
| Emitir relatorio | - | Emite relatorio conforme parametros informados |

## Fluxo de Uso

### Provisionar Despesa
1. Acessar opcao 554
2. Informar unidade
3. Informar ano de referencia
4. Informar CNPJ/CPF do fornecedor (opcao 478)
5. Escolher evento da despesa (opcao 503)
6. Cadastrar valor provisionado por mes
7. Salvar provisao

### Consultar Provisoes
1. Acessar opcao 554
2. Informar parametros de filtro (unidade, ano, fornecedor, evento)
3. Emitir relatorio
4. Analisar valores provisionados (marcados com ***)

### Substituir por Despesa Real
1. Quando despesa real ocorrer, lancar via opcao 475
2. Informar MESMO evento e MESMA data da provisao
3. Sistema automaticamente deixa de considerar provisao
4. NAO e necessario apagar provisao manualmente

## Integracao com Outras Opcoes
| Opcao | Relacao |
|-------|---------|
| 056 | Relatorio 100-SITUACAO DO CAIXA (considera provisoes) |
| 464 | Resultado de Unidades (considera provisoes) |
| 475 | Contas a Pagar (despesa real substitui provisao) |
| 478 | Cadastro de fornecedores |
| 503 | Tabela de Eventos (classificacao da despesa) |

## Observacoes e Gotchas

### Relatorios com Provisao
Despesas provisionadas sao consideradas em:
- **Situacao do Caixa**: Relatorio 100 (opcao 056)
- **Resultado de Unidades**: Relatorio obtido pela opcao 464
- **Marcacao especial**: valores provisionados sao marcados com asterisco (***) nos relatorios

### Provisao NAO e Despesa
- **NAO gera lancamentos**: provisao NAO gera lancamentos financeiros nem contabeis
- **Apenas relatorios**: impacto so aparece em relatorios gerenciais especificos
- **Vantagem**: evita ter que lancar despesa provisoria (opcao 475) e depois estornar quando despesa real chegar

### Substituicao Automatica
- **Despesa real apaga provisao**: quando despesa definitiva e lancada (opcao 475) com MESMO evento e MESMA data da provisao, sistema automaticamente deixa de considerar provisao
- **NAO precisa apagar**: NAO e necessario apagar manualmente o provisionamento
- **Condicoes**: evento e data devem coincidir exatamente

### Provisionamento Mensal
- Campo "Ano" indica ano de referencia
- Sistema permite provisionar valores mensais (12 meses do ano)
- Util para despesas recorrentes (aluguel, seguros, manutencoes programadas)

### Uso Correto
- **Apenas gerencial**: provisao e ferramenta gerencial, NAO substitui lancamento de despesa real
- **Temporaria**: provisao e temporaria ate lancamento definitivo via opcao 475
- **Sem impacto fiscal/contabil**: NAO afeta apuracoes fiscais nem contabeis
