# Opção 438 — Repassa Faturas para Agência

> **Módulo**: Financeiro
> **Páginas de ajuda**: 1 página consolidada
> **Atualizado em**: 2026-02-14

## Função
Fatura CTRCs cuja unidade de cobrança é do parceiro e repassa automaticamente a fatura para a agência. A fatura é gerada já liquidada, pois a responsabilidade de cobrança passa para o parceiro.

## Quando Usar
- CTRCs com unidade de cobrança definida como do parceiro/agência
- Repasse de cobrança para agências/parceiros
- Faturamento de CTRCs gerenciados por parceiros

## Pré-requisitos
- CTRCs disponíveis com unidade de cobrança = parceiro
- Parceiro cadastrado com Conta Corrente do Fornecedor ativa (opção 486)
- CTRCs não faturados

## Campos / Interface

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| **Sigla do parceiro** | Sim | Sigla da unidade do parceiro/agência |

## Abas / Sub-telas

**Seleção de CTRCs:**
- Lista de CTRCs com cobrança na unidade do parceiro
- Marcar CTRCs para faturamento

## Fluxo de Uso

1. Acessar opção 438
2. Informar sigla do parceiro
3. Sistema relaciona CTRCs com cobrança nesta unidade
4. Marcar CTRCs desejados
5. Confirmar faturamento
6. Sistema:
   - Gera fatura
   - Debita valor na Conta Corrente do Parceiro (opção 486)
   - Marca fatura como liquidada (cobrança do parceiro)

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 384 | Define unidade de cobrança do cliente |
| 457 | Controle de faturas (pode repassar fatura ao parceiro) |
| 466 | Relação de faturas repassadas |
| 486 | Conta Corrente do Parceiro (debita valor da fatura) |

## Observações e Gotchas

- **Fatura liquidada**: Gerada automaticamente como liquidada (cobrança passa ao parceiro)
- **Débito CCF**: Valor integral da fatura é debitado na Conta Corrente do Parceiro (opção 486)
- **Alternativa**: Fatura pode ser repassada também pela opção 457
- **Relação de faturas**: Opção 466 relaciona todas as faturas repassadas
- **Unidade de cobrança**: Definida no cadastro do cliente (opção 384)
- **Parceiro responsável**: Após repasse, parceiro assume responsabilidade pela cobrança
