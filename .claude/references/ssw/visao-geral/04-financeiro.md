# 04 — Financeiro

> **Fonte**: `visao_geral_financeiro.htm` (04/09/2020)
> **Links internos**: 15 | **Imagens**: 1

## Sumario

Visao geral do fluxo financeiro: Contas a Receber → Contas a Pagar → Financeiro → Conciliacao.

---

## Conceitos Fundamentais

1. **100%** — Todas as entradas (receitas) e saidas (despesas) DEVEM ser lancadas no SSW
2. **Simplicidade** — Ambiente online integrado permite poucas contas bancarias
3. **Contas a Pagar e formal** — Todo lancamento deve ser financeiro + fiscal + contabil. Informalidade compensada previamente no CCF
4. **Conciliacao** — Validacao do extrato SSW vs extrato bancario. Diferencas = processos nao executados

---

## Fluxo Financeiro

```
(1) Contas a Receber          (2) Contas a Pagar
    CTRCs →                       Despesas (475) →
    Faturamento (436)             Acertos CCF (486) → (3) CCF
    Liquidacao a vista (048)
    Cobranca bancaria (444)
           ↓                            ↓
         (4) FINANCEIRO (Caixa) ← ← ← ←
             opção 458
                ↓
         (6) CONCILIAÇÃO (569)
             vs Extrato bancário (5)
                ↓
         (7) Demais processos
             (Contabilidade, Fiscal, Frota...)
```

---

## Opcoes Principais

| Processo | Opcao | Descricao |
|----------|-------|-----------|
| Contas a Receber | [436](../financeiro/436-faturamento-geral.md) | Faturamento |
| Contas a Receber | [048](../operacional/048-liquidacao-vista.md) | Liquidacoes a vista |
| Contas a Receber | [444](../financeiro/444-cobranca-bancaria.md) | Cobranca bancaria |
| Contas a Pagar | [475](../financeiro/475-contas-a-pagar.md) | Lancamento de despesas |
| Contas a Pagar | [486](../financeiro/486-conta-corrente-fornecedor.md) | CCF — Conta Corrente do Fornecedor |
| Financeiro | [458](../financeiro/458-caixa-online.md) | Lancamentos de credito/debito no caixa |
| Conciliacao | [569](../financeiro/569-conciliacao-bancaria.md) | Validacao SSW vs extrato bancario |

---

## Regra do CCF (Conta Corrente do Fornecedor)

- CCF recebe creditos e debitos **informais**
- Somente o **saldo** (quando devido) vai para Contas a Pagar ([opção 475](../financeiro/475-contas-a-pagar.md))
- Contas a Pagar precisa de documento fiscal integral, sem rateio
- CCF e usado para: contratacao de veiculos, comissionamentos, acertos diversos

---

## Contexto CarVia

### Opcoes que CarVia usa

| Opcao | POP | Status | Quem Faz |
|-------|-----|--------|----------|
| [437](../financeiro/437-faturamento-manual.md) | E02 | ATIVO | Rafael (transicao para Jaqueline pendente) |

> Faturamento manual funcional, porem sem boleto. Unico processo financeiro ativo no SSW.

### Opcoes que CarVia NAO usa (mas deveria)

| Opcao | POP | Funcao | Impacto |
|-------|-----|--------|---------|
| [435](../financeiro/435-pre-faturamento.md) | E01 | Pre-faturamento (verificar CTRCs) | Nao verifica antes de faturar — risco de erro |
| [436](../financeiro/436-faturamento-geral.md) | E03 | Faturamento automatico | Volume atual (17 fretes/mes) nao justifica, mas escala futura sim |
| [444](../financeiro/444-cobranca-bancaria.md) | E04 | Cobranca bancaria (boleto) | Sem configuracao bancaria no SSW (PEND-03) |
| [048](../operacional/048-liquidacao-vista.md) | E05 | Liquidacao a vista | Cliente deposita, nao da baixa no SSW |
| [458](../financeiro/458-caixa-online.md) | E05 | Caixa online | Lancamentos nao registrados no SSW |
| [457](../financeiro/457-manutencao-faturas.md) | E06 | Manutencao de faturas | Nunca prorrogou/protestou fatura |
| [475](../financeiro/475-contas-a-pagar.md) | F01 | Contas a pagar | Pagamentos controlados fora do SSW (PEND-04) |
| [486](../financeiro/486-conta-corrente-fornecedor.md) | F02 | CCF — conta corrente fornecedor | Sem controle de saldo com parceiros |
| [476](../financeiro/476-liquidacao-despesas.md) | F03 | Liquidar despesa | Depende de F01 |
| [569](../financeiro/569-conciliacao-bancaria.md) | F04 | Conciliacao bancaria | Conciliacao manual — Rafael calcula fora do SSW |
| [462](../financeiro/462-bloqueio-financeiro-ctrc.md) | F05 | Bloqueio financeiro CTRC | Nunca bloqueou CTRC |
| [560](../fiscal/560-aprovacao-despesas.md) | F06 | Aprovacao de despesas | Depende de F01 |

### Responsaveis

- **Atual**: Rafael (faturamento manual)
- **Futuro**: Jaqueline (faturamento, cobranca, contas a pagar, liquidacao, conciliacao — pendentes PEND-04, PEND-05, PEND-10)
