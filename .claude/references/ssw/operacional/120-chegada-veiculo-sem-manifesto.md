# Opção 120 — Chegada de Veículo sem Manifesto

> **Módulo**: Operacional/Portaria
> **Referência interna**: Opção 130
> **Páginas de ajuda**: 1 página consolidada
> **Atualizado em**: 2026-02-15

## Função

Registra a chegada de veículo que possui Autorização emitida pela opção 120, mesmo sem manifesto prévio. Processo simplificado para controle de portaria.

## Quando Usar

- Registrar chegada de veículo com Autorização já emitida
- Dar entrada em veículo sem manifesto prévio
- Controlar portaria com veículos autorizados previamente

## Campos / Interface

### Tela Inicial

**Busca por:**
- **Número da AUTORIZAÇÃO** (com DV - dígito verificador)
- **Placa do VEÍCULO** (caso não tenha autorização emitida anteriormente)

### Tela Seguinte

- Sistema traz dados da Autorização e do veículo
- **Data/Hora de chegada**: Sugerida automaticamente (data/hora atuais)
- Confirmação: Clicar no botão ► para finalizar registro

## Integração com Outras Opções

- **Opção 120**: Emissão de Autorizações (pré-requisito para esta entrada)
- **Controle de Portarias**: Tutorial complementar disponível

## Observações e Gotchas

### Autorização Prévia

A opção assume que existe uma Autorização previamente emitida. Se o veículo não tiver autorização, o sistema permite busca apenas por placa.

### Dígito Verificador

Ao informar número da Autorização, é obrigatório incluir o DV (dígito verificador) completo.

### Data/Hora Automática

O sistema sugere automaticamente a data/hora atual, mas permite ajuste se necessário antes da confirmação.

### Veículos sem Manifesto

Esta opção é específica para veículos **sem manifesto**. Veículos com manifesto prévio devem usar processo diferente de entrada.
