# Opção 427 — Resultado por Cliente

> **Módulo**: Comercial/Análise
> **Referência interna**: Opção 449
> **Páginas de ajuda**: 1 página consolidada
> **Atualizado em**: 2026-02-15

## Função

Gera relatório com Resultado Comercial das operações de um cliente, agrupado por faixas de peso. Mostra desconto em relação à tabela genérica NTC, resultado comercial e reajuste necessário para atingir resultado mínimo.

## Quando Usar

- Analisar rentabilidade de um cliente específico
- Identificar faixas de peso com resultado comercial negativo
- Calcular reajuste necessário para atingir resultado mínimo
- Comparar descontos praticados vs. tabela genérica NTC
- Subsidiar negociações comerciais com dados de resultado por faixa de peso

## Campos / Interface

### Tela de Parâmetros

**CNPJ/CPF do cliente**: Identificação do cliente a ser analisado

**Período de emissão**: Período de emissão dos CTRCs do cliente

## Relatório Gerado

### Colunas do Relatório

**FAIXAS Kg**: Faixas de pesos em que são agrupados os CTRCs

**DESNTC %**: Percentual de desconto que o frete de um determinado CTRC representa em relação ao que seria cobrado pela tabela genérica NTC (opção 427)
- Indica quanto o cliente paga a menos que a tabela padrão

**RESCOM R$/%**: Resultado comercial dos CTRCs da faixa de peso (opção 101/Resultado)
- Valores em reais e percentual
- Mostra lucratividade por faixa de peso

**REANEC %**: Reajuste necessário para atingir o Resultado Mínimo (opção 469)
- Percentual de aumento necessário para alcançar meta mínima de resultado

## Integração com Outras Opções

- **Opção 427**: Tabela genérica NTC (base de comparação para desconto)
- **Opção 101 (Resultado)**: Cálculo do resultado comercial
- **Opção 469**: Definição do Resultado Mínimo esperado

## Observações e Gotchas

### Análise por Faixa de Peso

Agrupamento por faixas de peso permite identificar qual perfil de carga do cliente é mais ou menos rentável. Exemplo:
- Cargas pequenas (até 100kg) podem ter desconto alto mas resultado positivo
- Cargas grandes (acima de 1000kg) podem ter desconto menor mas resultado negativo

### Desconto vs. Resultado

**DESNTC** alto não significa necessariamente resultado ruim. Cliente pode ter:
- Desconto de 30% sobre tabela NTC
- Mas ainda assim gerar resultado comercial positivo se operação for eficiente

### Reajuste Necessário (REANEC)

Percentual de reajuste calculado para alcançar o Resultado Mínimo configurado na opção 469. Ferramenta importante para:
- Negociações de reajuste de tabela
- Identificar clientes que precisam de revisão urgente de preços
- Simular impacto de reajustes seletivos por faixa de peso

### Uso em Negociação Comercial

Relatório fornece dados objetivos para:
- Justificar reajustes necessários
- Mostrar ao cliente faixas de peso deficitárias
- Propor alterações seletivas de tabela
- Demonstrar competitividade vs. tabela NTC

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-A03](../pops/POP-A03-cadastrar-cidades.md) | Cadastrar cidades |
| [POP-A07](../pops/POP-A07-cadastrar-tabelas-preco.md) | Cadastrar tabelas preco |
| [POP-B02](../pops/POP-B02-formacao-preco.md) | Formacao preco |
