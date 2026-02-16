# Opcao 548 — NCMs com Impostos Creditaveis

> **Modulo**: Fiscal
> **Paginas de ajuda**: 1 pagina consolidada
> **Atualizado em**: 2026-02-14

## Funcao
Define os NCMs (Nomenclatura Comum do Mercosul) de produtos que sao creditaveis para ICMS e PIS/COFINS. Permite cadastrar a partir do nivel de Capitulo (2 digitos).

## Quando Usar
- Configurar NCMs creditaveis para ICMS por UF
- Configurar NCMs creditaveis para PIS/COFINS (tabela unica nacional)
- Preparacao para geracao de SPED FISCAL Debito/Credito (opcao 512)
- Preparacao para geracao SPED Contribuicoes Nao-Cumulativa (opcao 515)

## Pre-requisitos
- Conhecimento da estrutura de codigos NCM
- Legislacao de creditos de ICMS por UF
- Legislacao de creditos PIS/COFINS (regime nao-cumulativo)
- Entendimento de ativo imobilizado creditavel (se aplicavel)

## Campos / Interface
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Imposto | Sim | ICMS ou PIS/COFINS |
| UF | Sim* | Unidade Federativa (apenas para ICMS) |
| Codigo NCM | Sim | NCM creditavel (pode ser a partir de 2 digitos - Capitulo) |

*Obrigatorio apenas para ICMS (por UF); PIS/COFINS usa tabela unica nacional

## Fluxo de Uso

### Cadastrar NCMs Creditaveis ICMS
1. Acessar opcao 584 (NCMs com impostos creditaveis)
2. Escolher imposto: ICMS
3. Selecionar UF
4. Cadastrar NCMs creditaveis (minimo 2 digitos - Capitulo)
5. Repetir para cada UF necessaria

### Cadastrar NCMs Creditaveis PIS/COFINS
1. Acessar opcao 584
2. Escolher imposto: PIS/COFINS
3. Cadastrar NCMs creditaveis (tabela unica nacional)
4. NCMs podem ser cadastrados a partir de 2 digitos (Capitulo)

## Integracao com Outras Opcoes
| Opcao | Relacao |
|-------|---------|
| 512 | SPED FISCAL Debito/Credito (usa NCMs creditaveis ICMS) |
| 515 | SPED Contribuicoes Nao-Cumulativa (usa NCMs creditaveis PIS/COFINS) |
| 704 | Cadastro ativo imobilizado (credito imobilizado) |
| 546 | Livro CIAP (credito ICMS imobilizado, 48 meses) |

## Observacoes e Gotchas

### Estrutura NCM
- **NCM**: Nomenclatura Comum do Mercosul
- **Niveis hierarquicos**:
  - Capitulo: 2 digitos
  - Posicao: 4 digitos
  - Subposicao: 6 digitos
  - Item: 8 digitos
- **Cadastro flexivel**: opcao 548 permite cadastrar a partir do Capitulo (2 digitos), facilitando configuracao de grupos inteiros de produtos

### Tabelas por Imposto
- **ICMS**: tabela POR UF (legislacao varia entre estados)
- **PIS/COFINS**: tabela UNICA para todo o pais (legislacao federal)

### Uso em SPED
- **SPED FISCAL**: usa NCMs ICMS cadastrados para apuracao Debito/Credito (opcao 512)
- **SPED Contribuicoes**: usa NCMs PIS/COFINS cadastrados para regime Nao-Cumulativo (opcao 515)

### Credito Imobilizado
Ativos imobilizados creditaveis sao tratados de forma especial:
- **Cadastro**: opcao 704 (cadastro do bem)
- **ICMS**: credito via livro CIAP (opcao 546), apropriacao em 48 meses
- **PIS/COFINS**: quantidade de parcelas e tipo de credito definidos na tela de cadastro do bem (opcao 704)

### Nivel de Detalhe
- **Capitulo (2 digitos)**: cadastrar quando TODOS os produtos do capitulo sao creditaveis
- **Posicao/Subposicao/Item**: cadastrar niveis mais detalhados quando apenas subgrupos especificos sao creditaveis
- **Exemplo**: NCM 4011 (pneumaticos novos de borracha) pode ser cadastrado como "40" (Capitulo - borracha) se TODOS os produtos de borracha forem creditaveis, ou "4011" se apenas pneumaticos forem creditaveis

### Legislacao
- **ICMS por UF**: consultar legislacao estadual (cada UF tem lista propria)
- **PIS/COFINS**: consultar legislacao federal (lista unica, regime nao-cumulativo)
- NCMs creditaveis variam conforme atividade da empresa e regime tributario
