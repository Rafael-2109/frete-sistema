# Opção 541 — Lançamentos Automáticos

> **Módulo**: Contabilidade
> **Páginas de ajuda**: 1 página consolidada
> **Atualizado em**: 2026-02-14

## Função
Configura os lançamentos automáticos gerais na Contabilidade, permitindo que 90% dos lançamentos contábeis sejam realizados automaticamente pelo sistema, conforme as operações da transportadora.

## Quando Usar
- Configuração inicial do módulo de Contabilidade
- Alteração de contas contábeis utilizadas nos lançamentos automáticos
- Mapeamento de contas do Plano de Contas para processos do SSW

## Pré-requisitos
- Conciliação bancária em dia (opção 569) — **obrigatório**
- Plano de Contas configurado (opção 540)
- Conhecimento dos processos contábeis da empresa

## Campos / Interface
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Sequência | Auto | Numeração interna do SSW para identificar tipo de lançamento |
| Identificação SSW | Auto | Nome funcional dado pelo SSW ao tipo de lançamento |
| Conta Contábil | Sim | Conta do Plano de Contas a ser utilizada |
| Complemento | Auto | Complemento automático (unidade, CNPJ, banco, etc.) |

## Fluxo de Uso
1. Acessar opção 541
2. Para cada sequência listada, informar a conta contábil correspondente
3. Sistema valida se conta existe no Plano de Contas (opção 540)
4. Princípios contábeis devem ser observados no mapeamento
5. Processos do SSW passam a utilizar as contas configuradas automaticamente

## Integração com Outras Opções
| Opção | Relação |
|-------|---------|
| 540 | Plano de Contas — fonte das contas utilizadas no mapeamento |
| 526 | Lançamentos Automáticos - Despesas — configuração específica para eventos de despesa |
| 558 | Lançamentos Manuais — complementa os 10% não automatizados |
| 569 | Conciliação Bancária — pré-requisito obrigatório |
| 545 | Livro Diário — exibe lançamentos automáticos gerados |
| 556 | Livro Auxiliar de Saídas — detalha lotes de CTRCs lançados automaticamente |

## Principais Sequências (Exemplos)
| Sequência | Identificação | Uso |
|-----------|---------------|-----|
| 11, 63 | Banco Conta Movimento | Movimentações bancárias |
| 12, 15 | CTRCs Disponíveis para Faturar | CTRCs pendentes de faturamento |
| 13, 14 | Faturas a Receber | Faturas em carteira ou banco |
| 21, 22 | ICMS a Recolher | Débito de ICMS |
| 25 | Conta Corrente Fornecedor | Passivo com fornecedores |
| 30, 31 | Receita de Fretes | Receitas operacionais |
| 69 | Apuração de Resultado (ARE) | Conta transitória de apuração |

## Observações e Gotchas
- **Pré-requisito crítico**: Conciliação bancária (opção 569) DEVE estar em dia antes de utilizar esta opção
- **SSW não é Sistema de Custos**: Plano de Contas NÃO deve possuir centros de custos
- **90% de automatização**: Com opções 541 e 526 configuradas, 90% dos lançamentos são automáticos; 10% restantes via opção 558 (longo prazo e patrimônio líquido)
- **Lançamento em lotes**: Saídas (CTRCs, Subcontratos, RPSs) são agrupadas automaticamente em lotes homogêneos nas primeiras horas do dia seguinte
- **Plano sugerido**: SSW já sugere mapeamento padrão conforme Plano de Contas também sugerido
- **Sequências 10 e 62**: Sugeridas no Ativo, mas podem ser trocadas para Passivo conforme critério do contador
- **Complemento automático**: Sistema preenche automaticamente conforme tipo de conta (unidade, CNPJ, banco, etc.)
- **Venda de imobilizado**: Usar sequências 102 e 105 para NF-es com CFOP 5551/6551 (opção 551 + opção 547)

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-F04](../pops/POP-F04-conciliacao-bancaria.md) | Conciliacao bancaria |
