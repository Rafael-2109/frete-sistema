# Opção 731 — Impressão de Ordem de Serviço

> **Módulo**: Logística
> **Páginas de ajuda**: 1 página consolidada
> **Atualizado em**: 2026-02-14

## Função
Efetua a impressão das Ordens de Serviço (OS) digitadas pela opção 731.

## Quando Usar
Após a digitação de Ordens de Serviço para controle de movimentação de cargas em portos e terminais de containers, utilizar esta opção para imprimir as OSs geradas.

## Pré-requisitos
- Ordens de Serviço previamente digitadas pela opção 731

## Campos / Interface

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Tipo de Serviço | Sim | C para Coleta, E para Entrega, D para Devolução |
| Imprimir OSs | Não | Digitados por mim (M) ou por todos (T) |
| Reimprimir OSs | Não | Faixa de OSs a serem reimpressos (com dígito verificador) |
| Selecionar | Não | M para OSs emitidas por mim, T para todas |

## Fluxo de Uso
1. Selecionar o tipo de serviço (Coleta, Entrega ou Devolução)
2. Escolher entre imprimir OSs novas ou reimprimir OSs existentes
3. Para impressão de novas: selecionar digitados por mim ou por todos
4. Para reimpressão: informar faixa de OSs com dígito verificador
5. Confirmar a impressão

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 731 | Digitação de Ordem de Serviço - origem das OSs a serem impressas |

## Observações e Gotchas
- A opção de impressão (732) é complementar à opção de digitação (731)
- OSs podem ser filtradas por responsável (digitados por mim ou por todos)
- Para reimpressão, é necessário informar o número da OS com dígito verificador
- OSs não possuem valor fiscal e não geram movimentação financeira
- Cobrança dos serviços deve ser realizada com emissão de RPS (opção 733)
