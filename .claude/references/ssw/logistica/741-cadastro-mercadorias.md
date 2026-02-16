# Opção 741 — Cadastro de Mercadorias

> **Módulo**: Logística
> **Páginas de ajuda**: 1 página consolidada
> **Atualizado em**: 2026-02-14

## Função
Cadastra mercadorias/produtos do cliente consignatário (contratante do serviço) de Armazém Geral ou Operador Logístico.

## Quando Usar
- Antes de realizar entrada de produtos no estoque (opção 701)
- Para cadastrar produtos que serão armazenados pela transportadora
- Para consultar saldos de produtos em estoque

## Pré-requisitos
- Cliente consignatário cadastrado como ARMAZÉM GERAL ou OPERADOR LOGÍSTICO na opção 388

## Campos / Interface

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| CNPJ do Consignatário | Sim | Cliente proprietário dos produtos |
| Código do produto | Sim | Identificador único (números e letras) |
| Descrição | Sim | Descrição da mercadoria |
| Embalagem | Não | Descrição da embalagem |
| NCM/SH | Sim | Nomenclatura Comum do Mercosul |
| CEST | Condicional | Código especificador de substituição tributária (quando aplicável) |
| Cód. Benefício fiscal | Não | Código de benefício fiscal da UF (8 dígitos) |
| Custo unitário | Não | Valor unitário da mercadoria |
| GTIN | Não | Código identificador GS1 |
| KG/volume | Não | Peso em Kg de cada volume |
| L/volume | Não | Litros de cada volume |
| M3/volume | Não | Área em m3 que cada volume ocupa |
| M2/volume | Não | Área em m2 que cada volume ocupa |
| M2/volume empilhado | Não | Área em m2 quando empilhado |
| Saldo atual | Automático | Calculado pelo sistema (entradas - saídas) |
| Ativo | Sim | S para mercadoria ativa, N para desativada |
| FIFO | Não | Primeira Entrada, Primeira Saída (ainda sem uso no SSW) |
| Origem da mercadoria | Sim | Nacional ou estrangeira |
| CST | Condicional | Código de Situação Tributária de ICMS |
| CST IBS/CBS | Condicional | Código de Situação Tributária IBS/CBS |
| Classificação Tributária IBS/CBS | Condicional | Código de Classificação Tributária |
| Prazo de validade | Não | Prazo de validade da mercadoria (ainda sem uso) |
| Endereço | Não | Localização no armazém |
| Observação | Não | Observação sobre o produto |
| CNPJ emitente | Não | CNPJ emissor das NFs de entrada |
| Código do produto emitente | Não | Código usado pelo emitente para o produto |

## Fluxo de Uso
1. Informar CNPJ do consignatário
2. Informar código do produto (novo ou existente para alteração)
3. Preencher dados da mercadoria
4. Confirmar cadastro

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 701 | Entrada no estoque - utiliza mercadorias cadastradas |
| 702 | Saída do estoque - referencia mercadorias cadastradas |
| 721 | Situação do estoque - consulta saldos das mercadorias |
| 723 | Ajuste de estoque - ajusta saldos das mercadorias |
| 724 | Relatório de volumes disponíveis no estoque |

## Observações e Gotchas
- **Cadastro automático**: Ao importar XML da NF-e pela opção 701, os produtos são cadastrados automaticamente
- **M2 empilhado**: Área reduzida quando há empilhamento. Exemplo: volume de 1,2m2 com empilhamento de 5 = 1,2/5 = 0,24m2 por volume
- **Saldo atual**: É calculado automaticamente pelo sistema conforme entradas e saídas
- **Mercadorias desativadas**: Deixam de aparecer em listagens do cliente
- **Dados de tributação**: São salvos conforme NF-e de entrada
- **Consulta por embalagem**: Opção 724 permite classificar produtos por embalagem
