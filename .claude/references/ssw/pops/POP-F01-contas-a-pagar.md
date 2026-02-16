# POP-F01 — Lancar Contas a Pagar (Despesa)

> **Categoria**: F — Financeiro: Pagaveis
> **Prioridade**: P1 (Alta — pagar transportadoras no SSW)
> **Status anterior**: A IMPLANTAR
> **Criado em**: 2026-02-15
> **Executor atual**: Ninguem (controle fora do SSW)
> **Executor futuro**: Jaqueline

---

## Objetivo

Lancar despesas no SSW para programacao de pagamento a fornecedores, especialmente transportadoras subcontratadas. A [opcao 475](../financeiro/475-contas-a-pagar.md) integra dados fiscais (NF-e/CT-e), financeiros (parcelas, vencimentos) e contabeis (lancamentos automaticos). HOJE a CarVia controla pagamentos fora do SSW — este POP formaliza o processo.

---

## Trigger

- Receber fatura/NF de transportadora subcontratada
- Receber CT-e de parceiro (transferencia)
- Qualquer despesa operacional ou administrativa a programar

---

## Frequencia

Por demanda — a cada NF/CT-e recebido de fornecedor.

---

## Pre-requisitos

| Requisito | Opcao SSW | O que verificar |
|-----------|-----------|-----------------|
| Fornecedor cadastrado | [478](../financeiro/478-cadastro-fornecedores.md) | CNPJ, dados bancarios, CCF ativa (se aplicavel) |
| Evento de despesa | [503](../fiscal/503-manutencao-de-eventos.md) | Evento que classifica a despesa (financeiro/fiscal/contabil) |
| NF-e/CT-e do fornecedor | SEFAZ ou manual | Chave de 44 digitos ou dados manuais |
| Plano de contas | [540](../contabilidade/540-plano-de-contas.md) | Configurado para lancamentos automaticos |
| Certificado digital | [903](../cadastros/903-parametros-gerais.md) | Ativo para busca automatica de XMLs (recomendado) |

---

## Passo-a-Passo

### METODO A — Inclusao Manual

#### ETAPA 1 — Acessar e Identificar Fornecedor

1. Acessar [opcao **475**](../financeiro/475-contas-a-pagar.md)
2. Informar identificacao:

| Campo | Opcao | Quando usar |
|-------|-------|-------------|
| **Chave NF-e/CT-e** | 44 digitos | Se tiver o XML ou DANFE/DACTE |
| **CNPJ/CPF** | CNPJ do fornecedor | Se nao tiver chave |

3. Sistema busca dados do fornecedor ([opcao 478](../financeiro/478-cadastro-fornecedores.md))

> **Se fornecedor nao cadastrado**: Cadastrar na [opcao 478](../financeiro/478-cadastro-fornecedores.md) primeiro.

---

#### ETAPA 2 — Selecionar Evento de Despesa

4. Selecionar **Evento** ([opcao 503](../fiscal/503-manutencao-de-eventos.md)) que classifica a despesa:

| Evento tipico CarVia | Descricao | Quando usar |
|----------------------|-----------|-------------|
| Frete subcontratado | Pagamento a transportadora parceira | Mais frequente |
| Combustivel | Abastecimento de frota propria | Caminhoes VUC/Truck |
| Pedagio | Despesas de pedagio | Cargas diretas |
| Manutencao | Manutencao de veiculos | Frota propria |
| Seguro | ESSOR e outros seguros | Mensal |

> **ATENCAO**: O evento define o tratamento fiscal, contabil e financeiro da despesa. Usar evento errado = lancamento contabil incorreto.

---

#### ETAPA 3 — Preencher Dados Fiscais

5. Preencher dados do documento fiscal:

| Campo | Valor | Observacao |
|-------|-------|------------|
| **Modelo de documento** | 55=NF-e, 57=CT-e, 95=Boleto, 99=NFS-e | Selecionar tipo correto |
| **CFOP entrada** | Definido pelo evento ou CFOP saida (432) | Automatico na maioria dos casos |
| **Data de entrada** | Data de recebimento | Afeta credito ICMS/PIS/COFINS |
| **Numero NF/CT** | Numero do documento | Copiar do DANFE/DACTE |
| **Serie** | Serie do documento | Se aplicavel |
| **Valor total** | Valor total da NF-e/CT-e | Conferir com documento |
| **Base ICMS** | Base de calculo ICMS | Para credito real |
| **Valor ICMS** | Valor do ICMS | Para credito real |

---

#### ETAPA 4 — Informar Retencoes (Se Houver)

6. Preencher retencoes aplicaveis:

| Retencao | Quando aplicar |
|----------|----------------|
| **IRRF** | Servicos acima de R$ 666,67 (aliquota 1,5% geral) |
| **INSS** | Se habilitado no evento (servicos com cessao de mao de obra) |
| **ISS Retido** | NFS-e modelo 99 com ISS retido |
| **PIS/COFINS/CSLL** | Servicos acima de R$ 215,05 |

> **Nota**: Para transportadoras subcontratadas (CT-e), as retencoes sao menos comuns. Verificar com contabilidade.

---

#### ETAPA 5 — Definir Pagamento e Parcelas

7. Preencher dados do pagamento:

| Campo | Valor | Observacao |
|-------|-------|------------|
| **Data de pagamento** | Data prevista para pagar | Afeta caixa ([opcao 458](../financeiro/458-caixa-online.md)) |
| **Mes de competencia** | Mes da despesa | Para relatorios (opcao 477) |
| **Cod barras boleto** | Codigo de barras | Se pagamento via boleto |
| **QR Code PIX** | Copia e cola do PIX | Se pagamento via PIX |

8. Se necessario, **adicionar parcelas** (mensal, bimestral, trimestral)

---

#### ETAPA 6 — Gravar Lancamento

9. Conferir todos os dados
10. Clicar em **Gravar**
11. **Anotar Numero de Lancamento** — identificador unico da despesa

> **REGRA**: Anotar numero de lancamento no documento fisico para facilitar rastreamento.

12. Sistema automaticamente:
    - Confirma recebimento da NF-e ao SEFAZ
    - Gera lancamento contabil automatico (se configurado)
    - Debita CCF do fornecedor (se CCF ativa)

---

### METODO B — Importacao de NF-e Disponivel

> Mais rapido — usa XMLs automaticamente importados do SEFAZ.

1. Acessar [opcao **475**](../financeiro/475-contas-a-pagar.md)
2. Clicar em **"Disponiveis para programacao"**
3. Sistema lista NF-es dos ultimos 90 dias nao programadas
4. Localizar NF-e na lista
5. Clicar em **"Incluir despesa"**
6. **Dados importados automaticamente** — conferir:
   - CNPJ fornecedor
   - Numero e serie da NF
   - Valores (total, ICMS, PIS, COFINS)
7. Selecionar **Evento** (obrigatorio)
8. Ajustar data de pagamento e parcelas
9. Gravar lancamento

> **Requisito**: Certificado digital ativo ([opcao 903](../cadastros/903-parametros-gerais.md)) para importacao automatica de XMLs.

---

## CCF — Integracao Automatica

Se o fornecedor tem CCF ativa ([opcao 478](../financeiro/478-cadastro-fornecedores.md)):

```
Lancar despesa (475)
      ↓
Sistema debita CCF automaticamente (486)
      ↓
Saldo CCF atualizado
      ↓
Acerto de saldo via 486 → gera lancamento em 475
      ↓
Liquidacao (476, POP-F03)
```

> **Para transportadoras subcontratadas**: CCF permite controlar saldo devedor/credor. Creditos vem da contratacao ([opcao 072](../operacional/072-contratacao-de-veiculo-de-transferencia.md), POP-D01), debitos vem das despesas (este POP).

---

## Contexto CarVia

| Aspecto | Hoje | Futuro |
|---------|------|--------|
| Onde controla pagamentos | Fora do SSW (planilha/manual) | SSW [opcao 475](../financeiro/475-contas-a-pagar.md) |
| Conferencia de NF do parceiro | Manual | Importacao automatica de XML |
| Registro de custos por CTRC | Nao faz | Automatico via evento + CTRB |
| Resultado por CTRC (101) | Incompleto (so receita) | Completo (receita - custo = resultado) |
| CCF com transportadoras | Nao controla | Saldo automatico via [486](../financeiro/486-conta-corrente-fornecedor.md) |

---

## Erros Comuns e Solucoes

| Erro | Causa | Solucao |
|------|-------|---------|
| Fornecedor nao encontrado | CNPJ nao cadastrado em [478](../financeiro/478-cadastro-fornecedores.md) | Cadastrar fornecedor primeiro |
| Evento nao definido | Nao selecionou evento [503](../fiscal/503-manutencao-de-eventos.md) | Selecionar evento correto |
| Despesa duplicada | Mesmo CNPJ + NF no periodo de 180 dias | Sistema bloqueia — verificar se ja lançada |
| Valor ICMS incorreto | Conferir com XML da NF-e | Corrigir valor ou importar via XML |
| Lancamento retroativo rejeitado | Periodo conciliado (569) ou fiscal fechado (567) | Usar data posterior |
| CCF nao debitada | Fornecedor sem CCF ativa | Ativar CCF na [opcao 478](../financeiro/478-cadastro-fornecedores.md) |

---

## Verificacao Playwright

| Ponto de verificacao | Como verificar |
|---------------------|----------------|
| Despesa lancada | Opcao 477 → pesquisar por lancamento → existe |
| Valor correto | Opcao 477 → detalhe → valor = NF do fornecedor |
| CCF debitada | [Opcao 486](../financeiro/486-conta-corrente-fornecedor.md) → fornecedor → extrato → debito registrado |
| NF confirmada ao SEFAZ | Lancamento com chave NF-e → confirmacao automatica |
| Evento correto | Opcao 477 → detalhe → evento = tipo correto |
| Data pagamento | Opcao 477 → detalhe → data pagamento programada |

---

## POPs Relacionados

| POP | Relacao |
|-----|---------|
| POP-F02 | CCF — controle de saldo com fornecedores |
| POP-F03 | Liquidar despesa — proximo passo (pagar) |
| POP-D01 | Contratar veiculo — gera credito na CCF |
| POP-A05 | Cadastrar fornecedor — pre-requisito |
| POP-F04 | Conciliacao bancaria — conferir tudo no final |

---

## Historico de Revisoes

| Data | Alteracao | Autor |
|------|-----------|-------|
| 2026-02-15 | Criacao inicial | Claude (Agente Logistico) |
