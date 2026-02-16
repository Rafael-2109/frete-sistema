# Opção 492 — Cancelamento do Desconto de Duplicatas

> **Módulo**: Comercial/Financeiro
> **Páginas de ajuda**: 1 página consolidada
> **Atualizado em**: 2026-02-15

## Função
Cancela desconto de duplicata efetuado anteriormente, revertendo a operação de antecipação de recebíveis.

## Quando Usar
Quando houver necessidade de desfazer um desconto de duplicata já processado, seja por erro operacional, devolução de mercadoria, acordo com banco ou qualquer outra situação que exija o estorno da operação.

## Pré-requisitos
- Desconto de duplicata previamente efetuado
- Permissão de acesso à opção 492

## Campos / Interface

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| (campos não especificados na documentação) | - | Interface permite selecionar desconto a ser cancelado |

## Fluxo de Uso

1. Acessar opção 492
2. Localizar desconto de duplicata a ser cancelado
3. Confirmar cancelamento
4. Sistema atualiza automaticamente Faturas (457), Conta Corrente (456) e Caixa (458)

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 457 | Faturas — atualizada automaticamente no cancelamento |
| 456 | Conta Corrente — atualizada automaticamente no cancelamento |
| 458 | Caixa — atualizada automaticamente no cancelamento |

## Observações e Gotchas

- **Cancelamento obrigatório via opção**: O cancelamento DEVE ser efetuado exclusivamente por esta opção 492 — não tentar reverter manualmente em outras telas

- **Atualização automática**: A opção atualiza automaticamente três módulos inter-relacionados (Faturas, Conta Corrente e Caixa) — não é necessário fazer ajustes manuais nessas telas

- **Integridade financeira**: Como o desconto afeta múltiplos registros contábeis, utilizar esta opção garante a integridade dos dados financeiros
