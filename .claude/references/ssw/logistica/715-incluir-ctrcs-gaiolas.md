# Opção 715 — Incluir CTRCs em Gaiolas

> **Módulo**: Logística
> **Páginas de ajuda**: 1 página consolidada
> **Atualizado em**: 2026-02-14

## Função
Efetua a inclusão de CTRCs em gaiolas para controle de volumes.

## Quando Usar
**ATENÇÃO**: Esta opção é obsoleta. A operação ideal com gaiolas deve controlar volumes utilizando o SSWBar e a opção 020.

## Pré-requisitos
- Opção 021: Cadastramento das gaiolas e ajuste de estoques das unidades
- Opção 903/Operação: Ativar o uso das gaiolas

## Campos / Interface

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Gaiola | Sim | Número da gaiola cadastrada (opção 021) |
| CTRC/DACTE | Sim | Escolher entre digitação do CTRC ou captura de chave DACTE |
| Incluir CTRC/DACTE | Sim | Digitar o CTRC ou capturar a chave DACTE |
| Qtde vol | Não | Quantidade de volumes do CTRC incluída na gaiola |

## Fluxo de Uso

### Configuração Inicial
1. Opção 021: Cadastrar gaiolas e ajustar estoques das unidades
2. Opção 903/Operação: Ativar uso das gaiolas

### Operação
1. Opção 715: Incluir CTRCs em gaiolas (informar quantidade de volumes)
2. Opção 020: Informar gaiolas, pallets e chapas do Manifesto
3. Opção 025 e 030: Fazer saída e entrada de gaiolas/pallets/chapas via Manifestos
4. Opção 019 e 081: Consultar em qual gaiola o CTRC se encontra

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 021 | Cadastramento de gaiolas |
| 903 | Ativação do uso de gaiolas (Operação) |
| 020 | Informar gaiolas, pallets e chapas do Manifesto |
| 025 | Saída de gaiolas/pallets/chapas |
| 030 | Entrada de gaiolas/pallets/chapas |
| 019 | Consulta de gaiola do CTRC |
| 081 | Consulta de gaiola do CTRC |
| SSWBar | Ferramenta recomendada para controle de volumes |

## Observações e Gotchas
- **OPÇÃO OBSOLETA**: Esta opção 715 é obsoleta
- **Recomendação**: A operação ideal com gaiolas deve **controlar volumes** utilizando o SSWBar e a opção 020
- **Flexibilidade**: É possível informar quantidade específica de volumes do CTRC incluída na gaiola
- **Rastreamento**: Opções 019 e 081 permitem identificar em qual gaiola o CTRC se encontra
- **Integração com Manifestos**: Gaiolas transitam entre unidades via Manifestos (opções 025 e 030)
