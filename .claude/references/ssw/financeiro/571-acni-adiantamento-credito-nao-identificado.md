# Opção 571 — ACNI (Adiantamento ou Crédito Não Identificado)

> **Módulo**: Financeiro/Cobrança
> **Páginas de ajuda**: 1 página consolidada
> **Atualizado em**: 2026-02-15

## Função
Lançar na conta corrente créditos não identificados do extrato bancário (ACNI — Adiantamento ou Crédito Não Identificado) para posterior uso na liquidação de CTRCs e faturas.

## Quando Usar
Quando ocorrer:
- Créditos no extrato bancário que não podem ser identificados imediatamente (cliente não informou número de fatura/CTRC)
- Adiantamentos de clientes sem vinculação a documentos específicos
- Necessidade de conciliar extrato bancário mesmo sem identificação completa do pagamento
- Posterior aplicação do crédito em CTRCs ou faturas quando identificação for possível

## Pré-requisitos
- Extrato bancário com crédito não identificado
- Conta corrente cadastrada
- Conciliação bancária em andamento (opção 452)
- Permissão de acesso à opção

## Campos / Interface

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Número ACNI (com DV) | - | Gerado automaticamente pelo sistema |
| CNPJ/CPF pagador | Sim | Cliente que efetuou o pagamento (se conhecido) |
| Valor | Sim | Valor do crédito não identificado |
| Data | Sim | Data do crédito no extrato bancário |
| Banco/Ag/CCor | Sim | Conta bancária onde o crédito foi recebido (opção 904) |
| Observações | Não | Anotações sobre a origem ou natureza do crédito |

## Fluxo de Uso

### Lançamento de ACNI (opção 571)
1. Acessar opção 571
2. Informar CNPJ/CPF pagador (se conhecido)
3. Informar valor, data e conta bancária
4. Adicionar observações se necessário
5. Salvar — sistema gera número ACNI com DV
6. ACNI é lançado na conta corrente automaticamente

### Uso de ACNI para Liquidação (opção 048)
7. Quando identificar CTRC/fatura a ser liquidado com ACNI:
8. Acessar opção 048 (Liquidação de CTRCs/faturas)
9. **Liquidar um frete**: Informar CTRC ou fatura e escolher forma de pagamento **ACNI**
10. **Liquidar diversos fretes**: Informar CNPJ pagador e marcar CTRCs/faturas, escolher **ACNI**
11. **Liquidar com arquivo**: Informar número ACNI (com DV) no campo próprio — sistema debita ACNI com relação de CTRCs/faturas do arquivo
12. Sistema debita ACNI e liquida documentos

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 452 | Conciliação bancária — créditos não identificados são lançados como ACNI |
| 048 | Liquidação de CTRCs/faturas — usa ACNI como forma de pagamento |
| 904 | Contas bancárias — define conta onde ACNI foi recebido |
| 456 | Conta Corrente — ACNI é lançado automaticamente a crédito |

## Observações e Gotchas

- **ACNI tem DV**: Número ACNI é gerado com dígito verificador — importante informar corretamente na opção 048

- **Conciliação primeiro**: Processo completo de conciliação bancária deve usar opção 452 — ACNI é usado quando não há identificação imediata

- **Três formas de liquidar com ACNI** (opção 048):
  1. **Um frete**: Escolher forma de pagamento ACNI ao liquidar CTRC ou fatura individual
  2. **Diversos fretes**: Marcar CTRCs/faturas de um cliente e liquidar em lote com ACNI
  3. **Arquivo**: Importar CSV com lista de CTRCs/faturas e informar ACNI no campo próprio

- **ACNI vs Banco no arquivo CSV**: Ao liquidar com arquivo (opção 048), ACNI e Banco/Ag/CCor são **mutuamente excludentes** — informar apenas um dos dois

- **ACNI parcial**: Um ACNI pode ser usado parcialmente — saldo remanescente fica disponível para futuras liquidações

- **Rastreabilidade**: Manter observações detalhadas no ACNI facilita identificação posterior e auditoria

- **Forma de pagamento**: CTRCs liquidados via ACNI ficam registrados com forma de pagamento "ACNI" (não "Dinheiro" ou "Cartão")

- **Repasse à agência**: ACNI pode ser usado para liquidar fretes cuja cobrança foi repassada à agência — debita CCF da agência (opção 486)

- **Arquivo CSV para liquidação em lote**:
  - Coluna A: Número CTRC/Fatura (com DV)
  - Coluna B: CNPJ/CPF pagador (só números)
  - Coluna C: Data pagamento (DD/MM/AA ou DD/MM/AAAA)
  - Coluna D: Valor total liquidado (fatura + juros)
  - Coluna E: Valor dos juros

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-F04](../pops/POP-F04-conciliacao-bancaria.md) | Conciliacao bancaria |
