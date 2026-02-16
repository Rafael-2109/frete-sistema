# Opção 494 — Reajuste de Tabelas por Volumes

> **Módulo**: Comercial
> **Páginas de ajuda**: 2 páginas consolidadas
> **Atualizado em**: 2026-02-15

## Função
Efetuar reajuste em massa de múltiplas Tabelas por Volume de uma só vez, aplicando percentuais de aumento, redução ou substituição de valores em parcelas de frete.

## Quando Usar
Quando for necessário atualizar valores de frete para múltiplos clientes simultaneamente devido a:
- Reajustes anuais ou sazonais
- Alterações de custos operacionais (combustível, pedágio)
- Correção de valores em lote
- Padronização de tabelas de clientes

## Pré-requisitos
- Tabelas por Volume cadastradas (opção 494)
- Clientes cadastrados (opção 483)
- Permissão de acesso à opção (risco alto de alteração em massa)
- ATENÇÃO: Utilização incorreta pode danificar definitivamente milhares de tabelas — em caso de dúvidas, contatar Equipe SSW antes de executar

## Campos / Interface

### Primeira Tela — Critérios de Seleção

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Filial responsável | Não | Sigla da unidade responsável pelo cliente (opção 483) |
| Cliente | Não | CNPJ ou CPF do cliente tomador (opção 494) |
| Praça origem | Não | Praça de origem da Tabela por Volume |
| Praça destino | Não | Praça de destino da Tabela por Volume |
| UF destino | Não | UF de destino da tabela |
| Cidade/UF destino | Não | Cidade/UF destino da Tabela por Volume |
| Código da mercadoria | Não | Código de mercadoria da Tabela por Volume |
| Vendedor | Não | Código do vendedor vinculado ao cliente (opção 415) |
| Tipo de tabela | Não | **N** (normais), **D** (FOB dirigido), **A** (ambas) |
| Período de inclusão | Não | Data de inclusão da tabela |
| Período de alteração | Não | Data da última alteração (útil para selecionar tabelas sem reajuste até data) |
| Reajustar | Não | **T** (todas), **E** (apenas não reajustadas na data corrente) |
| Operação | Sim | **A** (aumentar %), **D** (diminuir %), **T** (trocar valor) |

### Segunda Tela — Confirmação e Percentuais

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Quantidade de tabelas/clientes | - | Exibição da quantidade selecionada — AVALIAR se é a esperada |
| Parcelas de frete | Sim | Indicar quais parcelas serão reajustadas |
| Percentuais de reajuste | Condicional | Informar % para operações AUMENTA ou DIMINUI |
| Valores para trocar | Condicional | Informar valores fixos para operação TROCAR PARA |

## Fluxo de Uso

1. Acessar primeira tela e definir critérios de seleção (campos podem ser informados individualmente ou simultaneamente)
2. Informar operação (A/D/T) e período
3. Avançar para segunda tela
4. **AVALIAR** quantidade de tabelas e clientes selecionados na parte superior
5. Se quantidade não for a esperada, **VOLTAR** e revisar critérios — NÃO executar na dúvida
6. Indicar parcelas de frete a serem reajustadas
7. Informar percentuais (operações A/D) ou valores fixos (operação T)
8. Confirmar execução
9. Sistema grava ocorrência automaticamente em opção 385
10. Tabelas são automaticamente revalidadas conforme prazo definido em opção 903

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 494 | Tabela por Volume — tabelas reajustadas por esta opção |
| 483 | Cadastro de clientes — define filial responsável e classificação |
| 415 | Vendedores — usado como critério de seleção |
| 385 | Ocorrências do cliente — grava automaticamente registro do reajuste |
| 903 | Prazos — define prazo de revalidação automática das tabelas |
| 110 | Cotação de fretes pelo cliente — utiliza tabelas por volume (pares) |
| 002 | Consulta cotações — situação K |

## Observações e Gotchas

- **REAJUSTE SOMENTE PARA CLIENTES COMUNS**: CLIENTE ESPECIAL só é reajustável quando se informa especificamente seu CNPJ. De maneira geral, apenas clientes classificados como COMUM na opção 483 serão reajustados

- **TABELAS EM SIMULAÇÃO**: Tabelas SIMULAÇÃO não são reajustáveis

- **OCORRÊNCIAS AUTOMÁTICAS**: Com o reajuste, ocorrência será automaticamente gravada em opção 385

- **REVALIDAÇÃO AUTOMÁTICA**: Tabelas são automaticamente revalidadas conforme prazo definido em opção 903

- **VOLTANDO AO VALOR INICIAL**: Um valor aumentado em X% NÃO pode ser retornado ao inicial diminuindo o mesmo X% (bases diferentes)
  - Exemplo: Valor 100 aumentado em 10% = 110
  - Para retornar 110 para 100, precisa diminuir 9,09% (10/110 = 0,0909)
  - Fórmula: (Novo - Original) / Novo = % de redução

- **PEDÁGIO**: Operação DIMINUI de 100% faz tipo das tabelas passar para S (sem pedágio)

- **OPERAÇÃO TROCAR PARA**: Pode trocar parcelas zeradas por outros valores, mantendo a MESMA unidade de medida. Apenas alguns campos trocáveis estão disponíveis

- **PARCELAS EM PERCENTAGEM**: Sofrem reajuste com o percentual informado. Ex: Ad Valorem de 1,00% com aumento de 10% = 1,10%

- **QUANTIDADE DE PARES**: Tabelas podem ser negociadas por quantidade de pares de volumes — utilizada na opção 110 (cotação pelo cliente)
