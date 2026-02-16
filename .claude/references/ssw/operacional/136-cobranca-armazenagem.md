# Opção 136 — Cobrança de Armazenagem

> **Módulo**: Operacional/Comercial
> **Referência interna**: Opção 199
> **Páginas de ajuda**: 1 página consolidada
> **Atualizado em**: 2026-02-15

## Função

Permite emissão de CTRCs ou RPS cobrando armazenagem de mercadoria no depósito da filial. Sistema calcula valor com base em dias de armazenagem e taxa do cliente ou tabela genérica.

## Quando Usar

- Cobrar armazenagem de mercadorias que ficaram no depósito além do prazo
- Emitir CTRC ou RPS de armazenagem referenciando CTRC original
- Consultar CTRCs que podem ter cobrança de armazenagem (opção 136)

## Campos / Interface

### Tela Inicial

**CTRC REFERÊNCIA (COM DV)**: Informe o número do CTRC original e clique no ► para abrir tela de emissão

**Link especial**: "CTRCs que podem ser cobradas a armazenagem" - Abre opção 136 para consultar conhecimentos elegíveis para cobrança via opção 199

### Tela Seguinte

Sistema mostra dados básicos do CTRC original e campos:

**QTDE DE DIAS DE ARMAZENAGEM**: Quantidade de dias que a mercadoria ficou armazenada no depósito da filial

**VALOR A COBRAR** (opcional): Valor a ser cobrado pela armazenagem. Se não informado, sistema usa:
- Taxa definida para o cliente, OU
- Taxa da **Tabela Genérica** (opção 423)

**TIPO DO DOCUMENTO**:
- **C** - emitir **CTRC**
- **R** - emitir **RPS**
- Campo aparece somente na emissão de Reentrega

**IMPRIMIR CTRC/NFPS**:
- **O** - emissão na unidade que emitiu o CTRC de referência (origem)
- **D** - emissão na unidade de destino do CTRC de referência
- Quando CTRC de referência for de carga fechada (destino FEC), unidade emissora será a de Origem

**OBSERVAÇÃO** (opcional): Observação a ser impressa no CTRC a ser emitido

## Integração com Outras Opções

- **Opção 136**: Consulta de CTRCs elegíveis para cobrança de armazenagem
- **Opção 423**: Tabela Genérica de taxas de armazenagem (quando cliente não tem taxa específica)
- **Opção 401**: Cadastro de Inscrição Municipal da unidade (obrigatório para emissão de RPS)

## Observações e Gotchas

### Emissão de RPS

Quando tipo de documento escolhido for **RPS**, sistema só permitirá emissão se a unidade de origem OU destino tiver **Inscrição Municipal** cadastrada na opção 401.

### Cálculo do Valor

Se valor não for informado manualmente, sistema usa hierarquia:
1. Taxa específica do cliente
2. Taxa da Tabela Genérica (opção 423)

### Carga Fechada (FEC)

Para CTRCs de carga fechada (destino FEC), a unidade emissora do CTRC de armazenagem será **sempre a de Origem**, independente do campo "IMPRIMIR CTRC/NFPS".

### Tutorial Complementar

Documentação disponível: "Complementação de frete: Conceitos" para mais informações sobre processos relacionados.
