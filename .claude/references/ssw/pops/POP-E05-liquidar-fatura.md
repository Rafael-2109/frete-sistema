# POP-E05 — Liquidar/Baixar Fatura Recebida

> **Categoria**: E — Financeiro: Recebiveis
> **Prioridade**: P1 (Alta — fechar ciclo financeiro)
> **Status anterior**: A IMPLANTAR
> **Criado em**: 2026-02-15
> **Executor atual**: Ninguem (nao faz no SSW)
> **Executor futuro**: Jaqueline

---

## Objetivo

Registrar no SSW o recebimento do pagamento de faturas emitidas (POP-E02/E03). Sem esta liquidacao, os CTRCs ficam com status "em aberto" nos relatorios, impedindo analise de resultado real e poluindo relatorios gerenciais.

---

## Trigger

- Cliente pagou (deposito, transferencia, PIX, boleto)
- Extrato bancario mostra credito correspondente a fatura
- Controle interno indica recebimento

---

## Frequencia

Diaria ou semanal — conforme volume de recebimentos.

---

## Pre-requisitos

| Requisito | Opcao SSW | O que verificar |
|-----------|-----------|-----------------|
| Fatura emitida | 437 ou [436](../financeiro/436-faturamento-geral.md) | Fatura existe no SSW com numero e valor |
| Pagamento confirmado | Extrato bancario | Valor creditado na conta |
| Conta bancaria cadastrada | [904](../cadastros/904-bancos-contas-bancarias.md) | Conta(s) CarVia cadastrada(s) |

---

## Passo-a-Passo

### CENARIO A — Liquidacao de Frete FOB a Vista (Opcao 048)

> Usar quando o motorista recebe pagamento na entrega (frete FOB a vista).

1. Acessar [opcao **048**](../operacional/048-liquidacao-vista.md)
2. Informar dados do frete liquidado:
   - CTRC ou fatura
   - Valor recebido
   - Conta bancaria ([opcao 904](../cadastros/904-bancos-contas-bancarias.md))
3. Confirmar liquidacao
4. Sistema registra como "Liquidado a Vista"

**Verificacao pos-liquidacao**:
- Gerar relatorio opcao **452** para confrontar com extrato bancario
- Comparar totais liquidados vs creditos no extrato

---

### CENARIO B — Liquidacao via Caixa Online (Opcao 458)

> Usar para registrar recebimentos em dinheiro ou movimentacoes de caixa.

1. Acessar [opcao **458**](../financeiro/458-caixa-online.md)
2. Selecionar caixa (cadastrado na [opcao 904](../cadastros/904-bancos-contas-bancarias.md))
3. Informar periodo de consulta
4. Lancar movimentacao:

| Campo | Valor |
|-------|-------|
| **Data** | Data do recebimento |
| **Tipo** | Entrada |
| **Valor** | Valor recebido |
| **Historico** | Referencia da fatura (ex: "Fatura 001234 - MotoChefe") |

5. Confirmar lancamento

---

### CENARIO C — Liquidacao de Faturas (Opcao 457)

> Usar para liquidar faturas geradas pela [opcao 436](../financeiro/436-faturamento-geral.md)/[437](../financeiro/437-faturamento-manual.md) quando o pagamento e via deposito/transferencia.

1. Acessar [opcao **457**](../financeiro/457-manutencao-faturas.md) (Manutencao de Faturas)
2. Localizar fatura por numero ou cliente
3. Registrar liquidacao:

| Campo | Valor |
|-------|-------|
| **Data liquidacao** | Data do credito no extrato bancario |
| **Banco/Agencia/Conta** | Conta onde o pagamento foi creditado |
| **Valor** | Valor recebido |

4. Se valor pago DIFERENTE do valor da fatura:
   - Valor menor: registrar diferenca como **abatimento** ou **debito** no proximo faturamento
   - Valor maior: registrar diferenca como **credito** para proximo faturamento

5. Confirmar liquidacao

---

## Fluxo Atual vs Futuro

| Aspecto | Hoje | Futuro |
|---------|------|--------|
| Registro de recebimento | Nao registra no SSW | Liquidar no SSW ([457](../financeiro/457-manutencao-faturas.md)/[048](../operacional/048-liquidacao-vista.md)/[458](../financeiro/458-caixa-online.md)) |
| Conferencia | Rafael calcula manualmente | Opcao 452/[458](../financeiro/458-caixa-online.md) confronta com extrato |
| Resultado por CTRC | Impossivel (fatura aberta) | Disponivel apos liquidacao ([opcao 101](../comercial/101-resultado-ctrc.md)) |
| Conciliacao bancaria | Nao faz | [Opcao 569](../financeiro/569-conciliacao-bancaria.md) (POP-F04) |
| Relatorios gerenciais | Poluidos (CTRCs abertos) | Precisos (CTRCs liquidados) |

---

## Impacto da NAO Liquidacao

| Consequencia | Gravidade |
|-------------|-----------|
| CTRCs aparecem como "em aberto" nos relatorios | Alta |
| Resultado por CTRC ([opcao 101](../comercial/101-resultado-ctrc.md)) fica incompleto | Alta |
| Conciliacao bancaria ([opcao 569](../financeiro/569-conciliacao-bancaria.md)) impossivel | Alta |
| Relatorios gerenciais ([opcao 056](../relatorios/056-informacoes-gerenciais.md)) imprecisos | Media |
| Analise de fluxo de caixa incorreta | Media |

---

## Erros Comuns e Solucoes

| Erro | Causa | Solucao |
|------|-------|---------|
| Fatura nao encontrada | Numero incorreto ou nao emitida | Verificar [opcao 457](../financeiro/457-manutencao-faturas.md) |
| Valor pago difere do faturado | Desconto, juros, ou pagamento parcial | Registrar diferenca na liquidacao |
| Conta bancaria invalida | Conta nao cadastrada em 904 | Cadastrar conta na [opcao 904](../cadastros/904-bancos-contas-bancarias.md) |
| Liquidacao retroativa rejeitada | Periodo ja conciliado ([569](../financeiro/569-conciliacao-bancaria.md)) | Reabrir conciliacao ou usar data posterior |
| Duplicidade de liquidacao | Fatura ja liquidada | Verificar [opcao 457](../financeiro/457-manutencao-faturas.md) antes |

---

## Verificacao Playwright

| Ponto de verificacao | Como verificar |
|---------------------|----------------|
| Fatura liquidada | [Opcao 457](../financeiro/457-manutencao-faturas.md) → pesquisar fatura → status "Liquidado" |
| Valor correto | [Opcao 457](../financeiro/457-manutencao-faturas.md) → detalhe fatura → valor liquidacao = valor pago |
| CTRCs atualizados | [Opcao 101](../comercial/101-resultado-ctrc.md) → CTRC → resultado disponivel (receita + custo) |
| Caixa atualizado | [Opcao 458](../financeiro/458-caixa-online.md) → periodo → lancamento de entrada registrado |
| Relatorio confrontado | Opcao 452 → periodo → totais batem com extrato |

---

## POPs Relacionados

| POP | Relacao |
|-----|---------|
| POP-E02 | Faturar manualmente — gera fatura que sera liquidada |
| POP-E03 | Faturar automaticamente — gera fatura que sera liquidada |
| POP-E01 | Pre-faturamento — etapa anterior ao faturamento |
| POP-F04 | Conciliacao bancaria — proximo passo (conferir tudo) |
| POP-E06 | Manter faturas — prorrogar, protestar, abater |

---

## Historico de Revisoes

| Data | Alteracao | Autor |
|------|-----------|-------|
| 2026-02-15 | Criacao inicial | Claude (Agente Logistico) |
