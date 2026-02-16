# Opção 107 — Gerar Arquivo de Cidades Atendidas

> **Módulo**: Comercial
> **Referência interna**: Opção 601
> **Páginas de ajuda**: 1 página consolidada
> **Atualizado em**: 2026-02-15

## Função

Gera planilha Excel com dados de cidades atendidas pela transportadora, permitindo customização do layout através de até 9 colunas configuráveis.

## Quando Usar

- Exportar dados de cidades atendidas para análise externa
- Compartilhar informações de cobertura geográfica com clientes ou parceiros
- Gerar relatórios de praças e prazos de entrega por município
- Criar planilhas com layout específico conforme necessidade do usuário

## Campos / Interface

### Definição do Layout

O usuário pode configurar até 9 colunas (COLUNA 1 a COLUNA 9) selecionando as seguintes informações:

- **CEP inicial do município**
- **CEP final do município**
- **Nome da cidade atendida**
- **Estado (UF)** onde se encontra a cidade
- **Praça da Cidade** (cadastrada na opção 402)
- **Prazo de entrega da cidade** (cadastrado na opção 402)
- **Unidade que atende a cidade**
- **Unidade centralizadora** (cadastrada na opção 690)

### Filtros

- **Apenas dados da unidade**: Quando marcado, relaciona apenas cidades da unidade atual

## Integração com Outras Opções

- **Opção 402**: Cadastro de praças e prazos de entrega por cidade
- **Opção 690**: Cadastro de unidades centralizadoras

## Observações e Gotchas

- O layout é totalmente customizável, permitindo escolher quais informações aparecem e em qual ordem
- A ordem das colunas na planilha Excel corresponde à sequência configurada (COLUNA 1 = primeira coluna do Excel)
- Filtrar por unidade é útil quando se deseja gerar planilhas específicas por filial
- CEP inicial e final permitem identificar a faixa completa de atendimento por município
