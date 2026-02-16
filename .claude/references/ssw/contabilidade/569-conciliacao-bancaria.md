# Opção 569 — Conciliação Bancária

> **Módulo**: Contabilidade
> **Páginas de ajuda**: Referenciada em múltiplas opções (540, 541)
> **Atualizado em**: 2026-02-14

## Função
Realiza a conciliação bancária, processo essencial para ativar o módulo de Contabilidade do SSW. Garante que os lançamentos bancários do sistema estejam em conformidade com os extratos bancários reais.

## Quando Usar
- **Pré-requisito obrigatório**: A contabilidade do SSW só pode ser utilizada se a conciliação bancária estiver em dia
- Mensalmente, para garantir conformidade entre sistema e banco
- Antes de ativar o módulo de Contabilidade
- Para identificar divergências entre lançamentos e extratos bancários

## Pré-requisitos
- Extratos bancários atualizados (opção 456)
- Lançamentos financeiros registrados no sistema
- Contas bancárias cadastradas

## Campos / Interface
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Banco/Agência/Conta | Sim | Identificação da conta bancária a conciliar |
| Período | Sim | Período de conciliação |

## Fluxo de Uso
1. Acessar opção 569
2. Selecionar banco, agência e conta corrente
3. Informar período de conciliação
4. Sistema compara lançamentos do SSW com extrato bancário
5. Marcar lançamentos conciliados
6. Investigar e corrigir divergências
7. Finalizar conciliação do período

## Integração com Outras Opções
| Opção | Relação |
|-------|---------|
| 456 | Extrato Bancário — fonte de dados para conciliação |
| 540 | Plano de Contas — só utilizável se conciliação estiver em dia |
| 541 | Lançamentos Automáticos — só utilizável se conciliação estiver em dia |
| 476 | Liquidação de Despesas — lançamentos a serem conciliados |

## Observações e Gotchas
- **Pré-requisito crítico**: Contabilidade SSW NUNCA pode ser ativada sem conciliação bancária em dia
- **Bloqueio sistêmico**: Opções 540 e 541 (Plano de Contas e Lançamentos Automáticos) não funcionam sem conciliação atualizada
- **Divergências comuns**: Cheques não compensados, transferências não identificadas, tarifas bancárias
- **Liquidação em cheque**: Cheques emitidos (opção 476) ficam em conta transitória "Cheques a Pagar" até compensação via conciliação bancária
- **Transferências**: Transferências entre contas (opção 456) geram lançamentos contábeis que devem ser conciliados
