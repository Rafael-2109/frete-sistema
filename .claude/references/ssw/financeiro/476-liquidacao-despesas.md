# Opção 476 — Liquidação de Despesas

> **Módulo**: Financeiro
> **Páginas de ajuda**: 1 página consolidada (mais referência ssw0095.htm)
> **Atualizado em**: 2026-02-14

## Função
Efetua a liquidação (pagamento) de despesas programadas no Contas a Pagar. Suporta liquidação à vista, com cheques (contínuos ou avulsos) e Pagamento Eletrônico de Fretes (PEF). Gera lançamentos contábeis automáticos.

## Quando Usar
- Pagamento de despesas programadas (opção 475)
- Liquidação de CTRBs (fretes de agregados/carreteiros)
- Pagamento com cheques (impressão incluída)
- Pagamento via PEF (Pagamento Eletrônico de Fretes)
- Liquidação via arquivo bancário (opção 522)

## Pré-requisitos
- Despesa programada no Contas a Pagar (opção 475)
- Aprovação centralizada concluída (se ativa, opção 560)
- Saldo bancário disponível
- Impressora de cheques configurada (se liquidação com cheque)

## Campos / Interface

### Tela Inicial
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| **Número de Lançamento** | Condicional | Para liquidar uma despesa específica |
| **CTRB** | Condicional | Para liquidar CTRB específico |
| **Período de inclusão** | Não | Filtro para liquidar diversas despesas |
| **Período de pagamento** | Não | Filtro por data de pagamento programada |
| **Fornecedor** | Não | Filtro por CNPJ/CPF do fornecedor |
| **Imprimir cheque** | Sim | S=imprime cheque, N=não imprime |

### Tela de Liquidação
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| **Forma de pagamento** | Sim | À vista, cheque, PEF |
| **Banco/Agência/Conta** | Sim | Conta bancária para pagamento |
| **Data** | Sim | Data de liquidação (saída do caixa) |
| **Valor** | Sim | Valor do pagamento (pode incluir juros/descontos) |
| **Juros** | Não | Valor de juros (se houver) |
| **Desconto** | Não | Valor de desconto (se houver) |

## Abas / Sub-telas

**Liquidar uma despesa:**
- Forma: À vista ou até 10 cheques
- Impressão: Contínuos ou avulsos (CHECK-PRONTO, BEMATECH)
- PEF: Pagamento Eletrônico de Fretes (CTRBs)

**Liquidar diversas despesas:**
- Seleção múltipla por filtros
- Forma: À vista ou 1 cheque

**Estornar liquidação:**
- Disponível para usuário que incluiu despesa ou usuário MTZ
- Reverte lançamentos contábeis

## Fluxo de Uso

### Liquidar Uma Despesa
1. Acessar opção 476
2. Informar Número de Lançamento ou CTRB
3. Escolher forma de pagamento:
   - À vista (dinheiro, transferência)
   - Cheque (até 10 cheques)
   - PEF (para CTRBs)
4. Informar banco/agência/conta
5. Informar data de liquidação
6. Ajustar valor (juros/desconto se houver)
7. Confirmar liquidação
8. Se cheque: Imprimir (contínuo ou avulso)

### Liquidar Diversas Despesas
1. Acessar opção 476
2. Selecionar filtros:
   - Período de inclusão
   - Período de pagamento
   - Fornecedor
3. Marcar despesas desejadas
4. Escolher forma: À vista ou 1 cheque
5. Confirmar liquidação em lote

### Estornar Liquidação
1. Acessar opção 476
2. Informar despesa liquidada
3. Clicar em "Estornar liquidação"
4. Confirmar estorno
5. Sistema reverte lançamentos contábeis

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 032 | Relação de despesas liquidadas (relatório) |
| 456 | Conciliação bancária (compensação de cheques) |
| 475 | Programação de despesas (origem das despesas) |
| 477 | Consultas de despesas |
| 522 | Liquidação via arquivo bancário (boleto/PIX) |
| 541 | Lançamentos automáticos contábeis |
| 560 | Aprovação centralizada de despesas |

## Observações e Gotchas

- **Usuário MTZ**: Pode liquidar despesas de todas as unidades
- **Aprovação centralizada**: Se ativa (opção 903), despesa deve ser aprovada (opção 560) antes de liquidar
- **Lançamentos contábeis automáticos**:
  - **À vista**: Crédito seq. 63/11, Débito conta crédito do evento
  - **Cheque**: Crédito seq. 17, Débito conta crédito do evento
  - **Compensação cheque** (opção 456): Crédito seq. 11, Débito seq. 17
  - **Desconto**: Crédito seq. 38, Débito conta crédito do evento
  - **Juros**: Crédito conta crédito do evento, Débito seq. 47
- **Impressoras de cheques avulsos**:
  - CHECK-PRONTO: Editar sswchp.ini para porta COM1/COM2
  - BEMATECH: Editar BemaDP32.ini para porta
  - Fonte: Modo DRAFT
- **PEF**: Pagamento Eletrônico de Fretes (específico para CTRBs)
- **Estorno**: Apenas usuário que incluiu ou usuário MTZ
- **Data de liquidação**: Afeta saída do Caixa (opção 458)
- **Relatório**: Opção 032 gera relação de despesas liquidadas
- **Período ilimitado**: Relatório opção 032 considera despesas desde início do SSW
- **Filtros**:
  - Período liquidação: Data "Agendado para/Bom para" da liquidação
  - Período pagamento: Data programada na despesa (opção 475)
- **Conciliação**: Cheques devem ser conciliados via opção 456 para contabilização completa
- **Liquidação via arquivo**: Opção 522 permite liquidação via troca de arquivos com banco (boleto/PIX)

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-F02](../pops/POP-F02-ccf-conta-corrente-fornecedor.md) | Ccf conta corrente fornecedor |
| [POP-F03](../pops/POP-F03-liquidar-despesa.md) | Liquidar despesa |
| [POP-F06](../pops/POP-F06-aprovar-despesas.md) | Aprovar despesas |
