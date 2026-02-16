# POP-F02 — Gerenciar CCF (Conta Corrente do Fornecedor)

> **Categoria**: F — Financeiro: Pagaveis
> **Prioridade**: P1 (Alta — controle de saldo com parceiros)
> **Status anterior**: A IMPLANTAR
> **Criado em**: 2026-02-15
> **Executor atual**: Ninguem (nao faz no SSW)
> **Executor futuro**: Jaqueline

---

## Objetivo

Controlar o saldo financeiro entre a CarVia e cada transportadora parceira/agregado/carreteiro usando a Conta Corrente do Fornecedor (CCF, [opcao 486](../financeiro/486-conta-corrente-fornecedor.md)). A CCF funciona como um "extrato" do fornecedor: creditos vem de contratacoes (CTRB/OS via [opcao 072](../operacional/072-contratacao-de-veiculo-de-transferencia.md)), debitos vem de despesas (combustivel, pedagio, etc.). Permite acerto de saldo periodico sem necessidade de liquidar cada transacao individualmente.

---

## Trigger

- Transportadora parceira realiza fretes e acumula creditos
- Despesas do fornecedor precisam ser debitadas (combustivel, pedagio)
- Periodo de acerto de contas (semanal/quinzenal/mensal)
- Verificar saldo devedor/credor com parceiro

---

## Frequencia

Semanal (consulta de saldo) + por demanda (lancamentos).

---

## Pre-requisitos

| Requisito | Opcao SSW | O que verificar |
|-----------|-----------|-----------------|
| Fornecedor cadastrado | [478](../financeiro/478-cadastro-fornecedores.md) | CNPJ, dados bancarios |
| **CCF ativa** | [478](../financeiro/478-cadastro-fornecedores.md) | Campo "CCF ativa = S" obrigatorio |
| Categoria definida | [478](../financeiro/478-cadastro-fornecedores.md) | Agente/Parceiro, Proprietario, ou Motorista |
| Contratacao registrada | [072](../operacional/072-contratacao-de-veiculo-de-transferencia.md) | Recomendado: creditos via CTRB/OS (POP-D01) |

> **REGRA**: A CCF so funciona se o campo "CCF ativa" estiver como **S** no cadastro do fornecedor ([opcao 478](../financeiro/478-cadastro-fornecedores.md)).

---

## Passo-a-Passo

### OPERACAO 1 — Consultar Saldo

1. Acessar [opcao **486**](../financeiro/486-conta-corrente-fornecedor.md)
2. Informar **CNPJ/CPF** do fornecedor
3. Clicar em **Saldo** ou **Extrato**
4. Verificar:

| Informacao | Descricao |
|------------|-----------|
| **Creditos** | Fretes devidos ao fornecedor (CTRBs/OS emitidos na [072](../operacional/072-contratacao-de-veiculo-de-transferencia.md)) |
| **Debitos** | Despesas do fornecedor (combustivel, pedagio, adiantamentos) |
| **Saldo** | Diferenca (credito - debito) = quanto CarVia deve ao fornecedor |

> **Saldo positivo** = CarVia deve ao fornecedor. **Saldo negativo** = fornecedor deve a CarVia.

---

### OPERACAO 2 — Debito Manual (Despesa do Fornecedor)

> Usar quando o fornecedor tem despesa que deve ser debitada da CCF.

5. Acessar [opcao **486**](../financeiro/486-conta-corrente-fornecedor.md)
6. Selecionar fornecedor
7. Clicar em **Lancar**
8. Preencher:

| Campo | Valor | Observacao |
|-------|-------|------------|
| **Tipo** | Debito | Reduz saldo do fornecedor |
| **Valor** | Valor da despesa | Ex: R$ 500 combustivel |
| **Data** | Data do debito | Data do evento |
| **Historico** | Descricao | Ex: "Combustivel viagem SP-CGR 12/02" |

9. Confirmar lancamento
10. Sistema gera lancamento contabil automatico conforme categoria:

| Categoria fornecedor | Credito (seq.) | Debito (seq.) |
|---------------------|----------------|---------------|
| Coleta agregado | 42 | 25 |
| Transferencia agregado | 43 | 25 |
| Agente/Parceiro | 44 | 25 |
| Motorista Frota | 63/11 | 19 |

---

### OPERACAO 3 — Credito Automatico (Contratacao)

> Creditos sao gerados automaticamente pela [opcao 072](../operacional/072-contratacao-de-veiculo-de-transferencia.md) (POP-D01).

11. Ao emitir CTRB/OS ([opcao 072](../operacional/072-contratacao-de-veiculo-de-transferencia.md)):
    - Sistema credita CCF automaticamente
    - Valor = remuneracao da viagem
12. Verificar credito na CCF:
    - [Opcao 486](../financeiro/486-conta-corrente-fornecedor.md) → extrato → credito deve aparecer

> **Tambem geram credito**:
> - Opcao 075 (emissao de OS)
> - Lancamento manual na CCF (tipo = Credito)

---

### OPERACAO 4 — Acerto de Saldo (Pagamento)

> Usar quando o saldo acumulado precisa ser pago ao fornecedor.

13. Verificar saldo na CCF ([opcao 486](../financeiro/486-conta-corrente-fornecedor.md))
14. Programar acerto no **Contas a Pagar** ([opcao 475](../financeiro/475-contas-a-pagar.md), POP-F01):
    - Informar CNPJ do fornecedor
    - Selecionar evento de acerto
    - Valor = saldo da CCF
15. Sistema gera lancamento automatico na CCF (debita o saldo)
16. Liquidar a despesa ([opcao 476](../financeiro/476-liquidacao-despesas.md), POP-F03)

```
Saldo CCF = R$ 5.000 (credor)
     ↓
Programar acerto no 475 (R$ 5.000)
     ↓
CCF debitada automaticamente
     ↓
Liquidar no 476 (transferencia bancaria ao fornecedor)
     ↓
Saldo CCF = R$ 0
```

---

### OPERACAO 5 — Consultar Todas as CCFs (Opcao 611)

17. Acessar opcao **611** para visao geral:
    - **T** = todos com CCF ativa
    - **A** = apenas agentes/parceiros
    - **P** = proprietarios de veiculos
    - **M** = motoristas
18. Verificar saldos de todos os fornecedores
19. Identificar fornecedores com saldo alto → programar acerto

> **Restricao**: Periodo do extrato limitado a 31 dias na opcao 611.

---

## Lancamentos Automaticos na CCF

| Evento | Tipo na CCF | Origem |
|--------|-------------|--------|
| CTRB emitido ([072](../operacional/072-contratacao-de-veiculo-de-transferencia.md)) | **Credito** | Contratacao de veiculo |
| OS emitida (075) | **Credito** | Ordem de servico |
| CTRB/OS cancelado (074) | **Debito** (estorno) | Cancelamento |
| Despesa com CCF ([475](../financeiro/475-contas-a-pagar.md)) | **Debito** | Contas a pagar com evento "Debita CCF" |
| Abastecimento interno (320) | **Debito** | Bomba interna (veiculos terceiros) |
| Acerto manual ([486](../financeiro/486-conta-corrente-fornecedor.md)) | **Debito/Credito** | Lancamento manual |

---

## Contexto CarVia

| Aspecto | Hoje | Futuro |
|---------|------|--------|
| Controle de saldo com parceiros | Manual/inexistente | CCF automatica ([486](../financeiro/486-conta-corrente-fornecedor.md)) |
| Debitos de combustivel/pedagio | Nao controla | Debito na CCF |
| Creditos de fretes | Nao registra | Automatico via [072](../operacional/072-contratacao-de-veiculo-de-transferencia.md) (CTRB) |
| Acerto de contas | Informal | Processo formal ([486](../financeiro/486-conta-corrente-fornecedor.md) → [475](../financeiro/475-contas-a-pagar.md) → [476](../financeiro/476-liquidacao-despesas.md)) |
| Visao consolidada | Nao tem | Opcao 611 (todos os fornecedores) |

---

## Erros Comuns e Solucoes

| Erro | Causa | Solucao |
|------|-------|---------|
| Fornecedor nao aparece na [486](../financeiro/486-conta-corrente-fornecedor.md) | CCF nao ativa no cadastro (478) | Ativar CCF na [opcao 478](../financeiro/478-cadastro-fornecedores.md) |
| Credito nao apareceu | CTRB/OS nao emitido | Verificar [opcao 072](../operacional/072-contratacao-de-veiculo-de-transferencia.md) (POP-D01) |
| CTRB nao pode ser cancelado | Data ja conciliada (569) | Verificar conciliacao bancaria |
| Saldo negativo inesperado | Debitos maiores que creditos | Verificar extrato detalhado na [486](../financeiro/486-conta-corrente-fornecedor.md) |
| Evento nao debita CCF | Evento 503 sem flag "Debita CCF" | Configurar evento na [opcao 503](../fiscal/503-manutencao-de-eventos.md) |
| Categoria contabil errada | Categoria do fornecedor incorreta | Corrigir na [opcao 478](../financeiro/478-cadastro-fornecedores.md) |

---

## Verificacao Playwright

| Ponto de verificacao | Como verificar |
|---------------------|----------------|
| CCF ativa | [Opcao 478](../financeiro/478-cadastro-fornecedores.md) → CNPJ → CCF = S |
| Saldo correto | [Opcao 486](../financeiro/486-conta-corrente-fornecedor.md) → fornecedor → saldo |
| Credito de CTRB | [Opcao 486](../financeiro/486-conta-corrente-fornecedor.md) → extrato → credito da contratacao [072](../operacional/072-contratacao-de-veiculo-de-transferencia.md) |
| Debito de despesa | [Opcao 486](../financeiro/486-conta-corrente-fornecedor.md) → extrato → debito da despesa [475](../financeiro/475-contas-a-pagar.md) |
| Visao geral | Opcao 611 → lista fornecedores com saldo |

---

## POPs Relacionados

| POP | Relacao |
|-----|---------|
| POP-D01 | Contratar veiculo — gera credito automatico na CCF |
| POP-F01 | Contas a pagar — lanca despesa que debita CCF |
| POP-F03 | Liquidar despesa — pagar acerto de CCF |
| POP-A05 | Cadastrar fornecedor — ativar CCF |
| POP-F04 | Conciliacao bancaria — conferir acertos pagos |

---

## Historico de Revisoes

| Data | Alteracao | Autor |
|------|-----------|-------|
| 2026-02-15 | Criacao inicial | Claude (Agente Logistico) |
