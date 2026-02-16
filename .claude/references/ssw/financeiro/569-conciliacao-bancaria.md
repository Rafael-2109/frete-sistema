# Opção 569 — Conciliação Bancária

> **Módulo**: Financeiro
> **Páginas de ajuda**: 3 páginas consolidadas
> **Atualizado em**: 2026-02-14

## Função
Pré-requisito obrigatório para uso da contabilidade do SSW. Controla e valida todas as movimentações financeiras comparando lançamentos do sistema com extratos bancários. Impede alterações retroativas em períodos conciliados, garantindo integridade contábil.

## Quando Usar
- **OBRIGATÓRIO**: Antes de usar qualquer funcionalidade contábil do SSW
- Diariamente ou periodicamente conforme controle financeiro da empresa
- Após recebimento de extratos bancários
- Antes de fechamento contábil mensal

## Pré-requisitos
- Extratos bancários disponíveis
- Lançamentos financeiros registrados (Contas a Pagar, Contas a Receber)
- Opção 456 (Extrato Bancário) para conciliar movimentações
- Opção 571 (Razão Contábil) para adiantamentos e créditos não identificados

## Campos / Interface

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| **Banco/Agência/Conta/Carteira** | Sim | Conta bancária a ser conciliada |
| **Data de conciliação** | Sim | Até qual data a conciliação é válida |
| **Saldo conciliado** | Sim | Saldo do extrato bancário na data |

## Abas / Sub-telas

**Conciliar:**
- Informar banco, data e saldo
- Confirmar conciliação

**Consultar:**
- Verificar última data conciliada por banco
- Histórico de conciliações

## Fluxo de Uso

### Conciliação Diária/Periódica
1. Obter extrato bancário
2. Conciliar movimentações via opção 456:
   - Cheques compensados
   - Transferências entre contas
   - Tarifas bancárias
3. Lançar adiantamentos/créditos não identificados (opção 571):
   - Crédito sequência 82
   - Débito sequência 63/11
4. Acessar opção 569
5. Informar banco/agência/conta/carteira
6. Informar data de conciliação
7. Informar saldo conciliado (do extrato)
8. Confirmar conciliação
9. Sistema valida e bloqueia período

### Verificação de Conciliação
1. Acessar opção 569 modo consulta
2. Verificar última data conciliada por banco
3. Identificar períodos pendentes

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 074 | Cancelamento CTRB/OS impedido se alterar data conciliada |
| 456 | Extrato bancário (conciliar cheques, transferências) |
| 476 | Liquidação com cheques (compensação via opção 456) |
| 540 | Plano de contas (pré-requisito para contabilidade) |
| 541 | Lançamentos automáticos (pré-requisito para contabilidade) |
| 558 | Lançamentos manuais (impedidos em período conciliado) |
| 559 | Fechamento contábil (após conciliação) |
| 567 | Fechamento fiscal (considera conciliação) |
| 571 | Razão contábil (adiantamentos/créditos não identificados) |

## Observações e Gotchas

- **OBRIGATÓRIO para contabilidade**: SSW só permite contabilidade se conciliação estiver em dia
- **Bloqueio retroativo**: Período conciliado não permite alterações financeiras/contábeis
- **Impedimentos automáticos**:
  - Cancelamento de CTRB/OS em data conciliada (opção 074)
  - Lançamentos manuais contábeis em período conciliado (opção 558)
  - Alteração de despesas em data conciliada (opção 475)
- **Sistema não é de custos**: Plano de contas não deve possuir centros de custos
- **Compensação de cheques**: Liquidação com cheques (opção 476) gera:
  - Crédito sequência 17
  - Débito conta crédito do evento
  - Compensação via opção 456: Crédito seq. 11, Débito seq. 17
- **Transferências entre contas** (opção 456):
  - Crédito sequência 63/11
  - Débito sequência 63/11
- **Adiantamentos/créditos não identificados** (opção 571):
  - Crédito sequência 82
  - Débito sequência 63/11
- **Plano de Contas Referencial**: Usado no SPED Contábil
- **Contas utilizadas na conciliação**:
  - Seq. 11: Banco Conta Movimento (complemento: BANCO+CARTEIRA)
  - Seq. 17: Cheques a Pagar (complemento: BANCO+CARTEIRA)
  - Seq. 63: Banco Conta Movimento (alternativa seq. 11)
  - Seq. 82: Adiantamentos/Créditos Não Identificados
- **Validação de saldo**: Sistema compara saldo informado com movimentações registradas
- **Histórico**: Mantém registro de todas as conciliações realizadas
- **Recomendação**: Conciliar diariamente para detectar divergências rapidamente

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-E05](../pops/POP-E05-liquidar-fatura.md) | Liquidar fatura |
| [POP-F03](../pops/POP-F03-liquidar-despesa.md) | Liquidar despesa |
| [POP-F04](../pops/POP-F04-conciliacao-bancaria.md) | Conciliacao bancaria |
