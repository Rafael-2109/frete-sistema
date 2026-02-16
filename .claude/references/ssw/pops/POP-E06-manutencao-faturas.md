# POP-E06 — Manter Faturas (Prorrogar, Protestar, Baixar)

> **Versao**: 1.0
> **Criado em**: 2026-02-16
> **Status CarVia**: A IMPLANTAR
> **Opcoes SSW**: [457](../financeiro/457-manutencao-faturas.md), [443](../financeiro/443-gera-arquivo-cobranca.md), [444](../financeiro/444-cobranca-bancaria.md), [384](../financeiro/384-cadastro-clientes.md), 532
> **Executor atual**: Rafael (nao usa — sem cobranca bancaria)
> **Executor futuro**: Jaqueline

---

## Objetivo

Realizar manutencao completa de faturas incluindo consulta de detalhes, alteracao de vencimento, envio de instrucoes bancarias (abater, prorrogar, protestar, sustar protesto, baixar), marcacao para Serasa/Equifax/SPC, retirada de CTRCs, lancamento de adicionais (credito/debito) e consulta de pagamentos parciais. Este POP cobre o ciclo de vida pos-emissao da fatura.

---

## Quando Executar (Trigger)

- Consultar detalhes de fatura especifica (CTRC incluidos, valor, situacao)
- Cliente solicita prorrogacao de vencimento
- Fatura vencida e cliente nao pagou (necessidade de protesto)
- Cliente pagou parcialmente (registrar pagamento parcial)
- Necessidade de abater valor (desconto concedido)
- Baixar fatura manualmente (por acordo comercial)
- Marcar inadimplente para Serasa/Equifax/SPC
- Retirar CTRC de fatura (para permitir estorno de liquidacao)
- Lancar adicional de credito/debito na fatura
- Verificar se fatura foi descontada ([opcao 448](../financeiro/448-desconto-duplicatas-cadastramento.md))

---

## Frequencia

Por demanda — conforme necessidade operacional/comercial.

---

## Pre-requisitos

| Requisito | Opcao SSW | O que verificar |
|-----------|-----------|-----------------|
| Fatura emitida | 436 ou 437 | Fatura existe no sistema |
| Numero da fatura | — | Numero com digito verificador (DV) |
| Banco de cobranca | [384](../financeiro/384-cadastro-clientes.md), [904](../cadastros/904-bancos-contas-bancarias.md) | Se instrucoes bancarias (A, P, R, S, B) |
| Ocorrencias bancarias | 912 | Instrucoes disponiveis para uso |
| Contrato Serasa/SPC | 334, 336, 337 | Se marcacao de inadimplencia |

---

## Passo-a-Passo

### ETAPA 1 — Consultar Fatura

1. Acessar [opcao **457**](../financeiro/457-manutencao-faturas.md) (Manutencao de Faturas)
2. Informar **numero da fatura com DV** (ex: 123456-7)
3. Sistema exibe detalhes completos:

| Informacao | Descricao |
|------------|-----------|
| Data emissao | Data de emissao da fatura |
| Data vencimento | Vencimento original ou alterado |
| Valor total | Valor total da fatura |
| Valor pago | Valor ja liquidado (se pagamento parcial) |
| Saldo | Saldo pendente (total - pago) |
| CNPJ pagador | CNPJ do cliente pagador |
| Banco/Ag/CCor/Cart | Banco de cobranca (999 = carteira propria) |
| Situacao | Liquidada, Pendente, Vencida, Perdida, Cancelada, Descontada, etc |
| CTRCs | Relacao de CTRCs incluidos na fatura |
| Adicionais | Creditos/debitos lancados ([opcao 459](../financeiro/459-cadastro-tde.md)) |
| Ocorrencias | Historico de instrucoes bancarias e eventos |

> **Situacao da fatura**: Indica o status atual. Liquidada = paga completamente. Pendente = aguardando pagamento. Vencida = passou do vencimento sem pagar.

---

### ETAPA 2 — Alterar Vencimento Individual

**Quando usar**: Cliente solicita prorrogacao de vencimento de fatura especifica.

4. Na tela de consulta da fatura ([opcao 457](../financeiro/457-manutencao-faturas.md)), clicar em **"Alterar vencimento"**
5. Informar **nova data de vencimento**
6. Confirmar alteracao
7. Sistema atualiza vencimento

> **RESTRICOES**:
> - NAO permitido para faturas liquidadas, canceladas ou em arquivo de remessa
> - Se banco de cobranca (nao carteira 999): enviar instrucao P (prorrogar) via [opcao 443](../financeiro/443-gera-arquivo-cobranca.md)

**Alternativa em lote**: Usar opcao **532** para alterar vencimento de varias faturas de uma vez (por faixa de faturas ou periodo de vencimento).

---

### ETAPA 3 — Enviar Instrucao Bancaria

**Quando usar**: Fatura em cobranca bancaria (banco diferente de 999) e necessidade de abater, prorrogar, protestar ou baixar.

8. Na tela de consulta da fatura ([opcao 457](../financeiro/457-manutencao-faturas.md)), clicar em **"Instrucoes Gerais"**
9. Selecionar instrucao desejada:

| Sigla | Instrucao | Quando usar |
|-------|-----------|-------------|
| **A** | Abater | Reduzir valor da fatura (desconto concedido apos emissao) |
| **P** | Prorrogar | Alterar vencimento via banco (apos alterar na [opcao 457](../financeiro/457-manutencao-faturas.md) ou 532) |
| **R** | Protestar | Cliente inadimplente — iniciar protesto |
| **S** | Sustar Protesto | Cancelar protesto ja iniciado (cliente pagou) |
| **B** | Baixar | Baixar fatura no banco (por acordo, nao por pagamento) |

10. Confirmar instrucao
11. Instrucao gravada em **ocorrencias da fatura**
12. Instrucao sera enviada ao banco via arquivo de remessa ([opcao 443](../financeiro/443-gera-arquivo-cobranca.md))
13. Confirmacao recebida via arquivo de retorno ([opcao 444](../financeiro/444-cobranca-bancaria.md))

> **Instrucoes de recepcao** (T=Entrada Confirmada, L=Liquidado): SAO recebidas do banco via [opcao 444](../financeiro/444-cobranca-bancaria.md). NAO sao enviadas manualmente.

---

### ETAPA 4 — Marcar para Serasa/Equifax/SPC

**Quando usar**: Fatura vencida, cliente inadimplente, necessidade de registrar divida em orgao de protecao ao credito.

14. Na tela de consulta da fatura vencida ([opcao 457](../financeiro/457-manutencao-faturas.md)), clicar em **"Instrucoes Gerais"**
15. Selecionar instrucao **96** (envio ao Serasa/Equifax/SPC)
16. Confirmar marcacao
17. Instrucao gravada em ocorrencias
18. Gerar arquivo pela opcao 334 (Serasa), 336 (Equifax) ou 337 (SPC)
19. Enviar arquivo ao orgao de protecao ao credito

> **ATENCAO**: Envio ao Serasa/SPC e processo serio com implicacoes legais. Verificar com comercial antes de marcar.

**Baixar do Serasa/SPC** (cliente pagou):

20. Acessar [opcao 457](../financeiro/457-manutencao-faturas.md), informar numero da fatura
21. Clicar em **"Instrucoes Gerais"** → Selecionar instrucao **97** (baixa do Serasa/Equifax/SPC)
22. Confirmar baixa
23. Baixa seguira automaticamente no proximo arquivo (opcao 334, 336 ou 337)

---

### ETAPA 5 — Marcar Fatura como Perdida

**Quando usar**: Fatura irrecuperavel (cliente falido, empresa fechou, acordo de perdao de divida).

24. Na tela de consulta da fatura ([opcao 457](../financeiro/457-manutencao-faturas.md)), clicar em **"Marcar como perdida"**
25. Informar **motivo** (obrigatorio)
26. Confirmar
27. Valor aparece em Situacao Geral ([opcao 001](../operacional/001-cadastro-coletas.md)) como **"PERDIDO (E)"**

> **RESTRICAO**: Apenas faturas em carteira (banco = 999). Faturas em cobranca bancaria devem ser baixadas primeiro (instrucao B).

**Marcacao em lote**: Usar opcao **357** (Faturas Perdidas) para marcar varias faturas de uma vez (por faixa ou periodo de vencimento).

---

### ETAPA 6 — Retirar CTRC de Fatura

**Quando usar**: CTRC liquidado incorretamente (opcao 429) ou necessidade de estornar liquidacao de CTRC.

28. Na tela de consulta da fatura ([opcao 457](../financeiro/457-manutencao-faturas.md)), clicar em **"Retirar CTRC"**
29. Selecionar CTRC a ser retirado
30. Confirmar retirada
31. CTRC fica disponivel para novo faturamento ([opcao 435](../financeiro/435-pre-faturamento.md))

> **Pre-requisito obrigatorio**: Retirar CTRC da fatura ANTES de estornar liquidacao (opcao 429). Sistema nao permite estorno com CTRC em fatura.

---

### ETAPA 7 — Lancar Adicional (Credito/Debito)

**Quando usar**: Adicionar credito (desconto, devolucao) ou debito (multa, taxa de reentrega) APOS emissao da fatura.

32. Na tela de consulta da fatura ([opcao 457](../financeiro/457-manutencao-faturas.md)), clicar em **"Adicional"**
33. Informar:
    - **Tipo**: Credito (reduz valor) ou Debito (aumenta valor)
    - **Valor**: Valor do adicional
    - **Motivo**: Descricao (ex: "Desconto comercial 5%", "Taxa de reentrega")
34. Confirmar lancamento
35. Sistema atualiza valor da fatura

> **Credito**: Reduz valor da fatura. Ex: desconto concedido, devolucao de mercadoria.
> **Debito**: Aumenta valor da fatura. Ex: multa, taxa de reentrega.

**Origem dos adicionais**: Podem ser lancados aqui ([opcao 457](../financeiro/457-manutencao-faturas.md)) ou vir de CTR/fatura ([opcao 442](../financeiro/442-credito-debito-ctrc-fatura.md)). Relacao de adicionais por cliente disponivel na [opcao 459](../financeiro/459-cadastro-tde.md).

---

### ETAPA 8 — Repassar para Agencia

**Quando usar**: Frete repassado para agencia (opcao 466) — registro de transferencia de credito.

36. Na tela de consulta da fatura ([opcao 457](../financeiro/457-manutencao-faturas.md)), clicar em **"Repassar para agencia"**
37. Selecionar **agencia** (opcao 466)
38. Confirmar repasse
39. Sistema:
    - Lanca valor via CCF ([opcao 486](../financeiro/486-conta-corrente-fornecedor.md))
    - Lanca em SAIDAS (despesas) na Situacao Geral ([opcao 001](../operacional/001-cadastro-coletas.md))
40. Fatura nao pode mais ter banco trocado (opcao 465)

> **Contexto CarVia**: Repasse para agencia NAO se aplica a operacao CarVia (nao ha agencias). Incluido por completude do POP.

---

### ETAPA 9 — Consultar Pagamentos Parciais

**Quando usar**: Cliente pagou parte da fatura, verificar saldo pendente.

41. Na tela de consulta da fatura ([opcao 457](../financeiro/457-manutencao-faturas.md)), verificar campos:
    - **Valor pago**: Quanto ja foi liquidado
    - **Saldo**: Quanto ainda falta liquidar
42. Sistema exibe historico de pagamentos parciais
43. Fatura com pagamento parcial NAO pode ter banco trocado (opcao 465)

---

## Tarifa Bancaria

Se ocorrencia configurada como **"COBRA CLIENTE = S"** (opcao 912):
- Tarifa bancaria ([opcao 904](../cadastros/904-bancos-contas-bancarias.md)) cobrada na proxima fatura
- Cliente deve estar configurado para cobranca de tarifa ([opcao 384](../financeiro/384-cadastro-clientes.md))

Instrucoes que podem gerar tarifa: A (abater), P (prorrogar), R (protestar), S (sustar protesto), B (baixar).

---

## Situacoes que Impedem Operacoes

| Operacao | Impedimentos |
|----------|--------------|
| Alterar vencimento | Fatura liquidada, cancelada ou em arquivo de remessa |
| Trocar banco (opcao 465) | Pagamento parcial, em remessa, repassada, descontada |
| Estornar liquidacao (opcao 429) | CTRC ainda na fatura (retirar primeiro) |
| Marcar como perdida | Fatura em cobranca bancaria (baixar primeiro) |

---

## Contexto CarVia

### Hoje

- Rafael NAO usa [opcao 457](../financeiro/457-manutencao-faturas.md)
- SEM cobranca bancaria (banco = 999, carteira propria)
- SEM boleto
- Cliente deposita diretamente
- SEM controle de faturas vencidas
- SEM protesto, SEM Serasa

### Futuro (com POP implantado)

- Jaqueline monitora faturas vencidas semanalmente
- Prorrogacao de vencimento (ETAPA 2) para clientes parceiros
- Marcacao de inadimplentes para Serasa (ETAPA 4) — comercial autoriza
- Instrucoes bancarias (ETAPA 3) quando migrar para cobranca bancaria (POP-E04)
- Adicionais (ETAPA 7) para taxas de reentrega, descontos

---

## Erros Comuns e Solucoes

| Erro | Causa | Solucao |
|------|-------|---------|
| Fatura nao encontrada | Numero incorreto ou DV errado | Verificar numero na [opcao 056](../relatorios/056-informacoes-gerenciais.md) ou 437 |
| Vencimento nao pode ser alterado | Fatura liquidada, cancelada ou em remessa | Verificar situacao da fatura |
| Instrucao bancaria nao enviada | Fatura em carteira (999) | Instrucoes bancarias so para cobranca bancaria |
| CTRC nao pode ser retirado | CTRC ja liquidado ou fatura conciliada (569) | Desconciliar antes ou estornar liquidacao |
| Tarifa nao cobrada | Ocorrencia sem "COBRA CLIENTE = S" (912) | Configurar ocorrencia ou cliente ([384](../financeiro/384-cadastro-clientes.md)) |
| Fatura perdida rejeitada | Banco diferente de 999 | Baixar fatura primeiro (instrucao B) |
| Adicional nao incluso | Lancado apos faturamento | Adicional so aparece na proxima fatura |

---

## Verificacao Playwright

| Ponto de verificacao | Como verificar |
|---------------------|----------------|
| Fatura existe | [Opcao 457](../financeiro/457-manutencao-faturas.md) → informar numero → detalhe exibido |
| Vencimento alterado | [Opcao 457](../financeiro/457-manutencao-faturas.md) → detalhe → data vencimento = nova data |
| Instrucao gravada | [Opcao 457](../financeiro/457-manutencao-faturas.md) → ocorrencias → instrucao aparece |
| Adicional lancado | [Opcao 457](../financeiro/457-manutencao-faturas.md) → adicionais → credito/debito registrado |
| CTRC retirado | [Opcao 457](../financeiro/457-manutencao-faturas.md) → CTRCs → CTRC nao aparece mais |
| Marcada como perdida | [Opcao 001](../operacional/001-cadastro-coletas.md) → Situacao Geral → PERDIDO (E) |

---

## POPs Relacionados

| POP | Relacao |
|-----|---------|
| POP-E02 | Faturamento manual — gera faturas |
| POP-E03 | Faturamento automatico — gera faturas |
| POP-E04 | Cobranca bancaria — pre-requisito para instrucoes |
| POP-E05 | Liquidar fatura — proximo passo (registrar pagamento) |
| POP-F04 | Conciliacao bancaria — impede estorno se conciliada |
| POP-E01 | Pre-faturamento — verificar antes de faturar |

---

## Historico

| Data | Versao | Alteracao |
|------|--------|-----------|
| 2026-02-16 | 1.0 | Criacao inicial (Onda 5) |
