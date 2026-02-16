# POP-E02 — Faturar Manualmente

> **Categoria**: E — Financeiro: Recebiveis
> **Prioridade**: P1 (Alta — processo ja existente, precisa padronizar)
> **Status anterior**: JA FAZ
> **Criado em**: 2026-02-15
> **Executor atual**: Rafael
> **Executor futuro**: Jaqueline

---

## Objetivo

Gerar faturas manualmente no SSW ([opcao 437](../financeiro/437-faturamento-manual.md)) para clientes com tipo de faturamento M (manual). Este e o processo que a CarVia ja usa hoje — Rafael seleciona CTRCs e gera a fatura. O POP padroniza o processo para que Jaqueline assuma.

---

## Trigger

- CTRCs autorizados pelo SEFAZ, prontos para cobranca
- Verificacao previa concluida (POP-E01 — recomendado)

---

## Frequencia

Semanal ou por demanda — conforme volume de CTRCs.

---

## Pre-requisitos

| Requisito | Opcao SSW | O que verificar |
|-----------|-----------|-----------------|
| CTe autorizado | [007](../operacional/007-emissao-cte-complementar.md) | CTe com status "Autorizado" no SEFAZ |
| Cliente cadastrado | [483](../cadastros/483-cadastro-clientes.md) | Cliente existe no SSW |
| Parametros de faturamento | [384](../financeiro/384-cadastro-clientes.md) | Tipo = M (manual), prazo vencimento, banco, e-mail |
| Unidade ativa = MTZ | — | Faturamento so em unidade MTZ (matriz) |
| Pre-faturamento verificado | [435](../financeiro/435-pre-faturamento.md) | Recomendado: verificar CTRCs disponiveis (POP-E01) |

---

## Passo-a-Passo

### ETAPA 1 — Trocar para Unidade MTZ

1. Verificar que a unidade ativa e **MTZ** (matriz)
   - Faturamento so pode ser feito na unidade MTZ
   - Se estiver em CAR ou outra unidade, trocar para MTZ

---

### ETAPA 2 — Verificar CTRCs Disponiveis (Recomendado)

2. Acessar [opcao **435**](../financeiro/435-pre-faturamento.md) e verificar:
   - CTRCs disponiveis para o cliente
   - Coluna E-MAILS — cliente tem e-mail cadastrado?
   - Coluna BLOQUEADO — algum CTRC bloqueado ([opcao 462](../financeiro/462-bloqueio-financeiro-ctrc.md))?
   - Se houver pendencia: resolver ANTES de faturar

> **Se pular esta etapa**: A fatura pode incluir CTRCs que nao deveriam ser faturados, ou ser gerada sem e-mail de destino.

---

### ETAPA 3 — Acessar Opcao 437

3. Acessar [opcao **437**](../financeiro/437-faturamento-manual.md) (Faturamento Manual)
4. Informar o **CNPJ do cliente pagador**
5. Sistema exibe CTRCs disponiveis para faturamento

---

### ETAPA 4 — Selecionar CTRCs

6. Revisar lista de CTRCs disponiveis:

| Verificacao | O que conferir |
|-------------|----------------|
| Numeros dos CTRCs | Estao corretos para este periodo? |
| Valores | Conferir valor de cada CTe |
| Datas | CTRCs dentro do periodo esperado? |
| Adicionais | Debitos/creditos da [opcao 459](../financeiro/459-cadastro-tde.md) incluidos? |

7. Selecionar os CTRCs que devem compor esta fatura
8. Verificar total da fatura

> **Se houver adicionais (debitos/creditos)**: Verificar [opcao 459](../financeiro/459-cadastro-tde.md) antes — debitos (TDE, diaria, etc.) e creditos (descontos) que devem constar na fatura.

---

### ETAPA 5 — Definir Dados da Fatura

9. Preencher/confirmar:

| Campo | Valor | Observacao |
|-------|-------|------------|
| **Data emissao** | Data atual ou data desejada | Ate 15 dias passados ou 5 dias futuros |
| **Vencimento** | Conforme 384 do cliente | Prazo cadastrado na [opcao 384](../financeiro/384-cadastro-clientes.md) |
| **Banco/Carteira** | Conforme [384](../financeiro/384-cadastro-clientes.md) do cliente | Carteira 999 = cobranca propria (sem boleto) |
| **Observacoes** | Opcional | Texto adicional na fatura |

---

### ETAPA 6 — Gerar e Confirmar Fatura

10. Conferir resumo da fatura:
    - Total de CTRCs
    - Valor total da fatura
    - Dados do cliente (CNPJ, razao social)
    - Vencimento
11. Clicar em **Confirmar** / **Gerar Fatura**
12. **Fatura gerada** — anotar o numero

---

### ETAPA 7 — Enviar ao Cliente

13. **Envio automatico por e-mail**: Se cliente tem e-mail cadastrado na [384](../financeiro/384-cadastro-clientes.md), a fatura e enviada automaticamente nas primeiras horas do dia seguinte

14. **Envio manual (processo atual CarVia)**:
    - Imprimir/exportar fatura
    - Enviar para Jessica
    - Jessica envia ao cliente

> **Objetivo futuro**: Migrar para envio automatico por e-mail (cadastrar e-mail na [opcao 384](../financeiro/384-cadastro-clientes.md)).

---

## Fluxo Atual vs Futuro

| Aspecto | Hoje (Rafael) | Futuro (Jaqueline) |
|---------|---------------|-------------------|
| Quem fatura | Rafael | Jaqueline |
| Pre-faturamento ([435](../financeiro/435-pre-faturamento.md)) | Nao usa | Usar ANTES de faturar |
| Envio ao cliente | Manual (Rafael → Jessica → cliente) | Automatico por e-mail |
| Cobranca | Deposito na conta (sem boleto) | Boleto via 444 (POP-E04) |
| Liquidacao | Nao faz | Registrar recebimento (POP-E05) |

---

## Separacao de Faturas

[Opcao 384](../financeiro/384-cadastro-clientes.md) define como separar faturas por cliente:

| Codigo | Separa por | Quando usar |
|--------|-----------|-------------|
| 1 | CIF / FOB / Terceiro | Quando cliente tem fretes CIF e FOB |
| 2 | Codigo mercadoria | Quando mercadorias devem ser faturadas separadamente |
| 3 | Complementar | Separar CTes complementares |
| 4 | ICMS / ISS | Quando tributacao diferente |
| 5 | Adicionais / Abatimentos | Separar debitos e creditos |
| 6 | Unidade expedidora | Por filial que expediu |
| 7 | UF destino | Por estado de destino |
| J | CNPJ | Por CNPJ do destinatario |

> **Configurar na opcao [384](../financeiro/384-cadastro-clientes.md)** de cada cliente. Para CarVia, a maioria dos clientes nao precisa separacao.

---

## Erros Comuns e Solucoes

| Erro | Causa | Solucao |
|------|-------|---------|
| Nenhum CTRC disponivel | CTRCs nao autorizados ou ja faturados | Verificar [opcao 435](../financeiro/435-pre-faturamento.md) |
| Fatura com valor zero | Creditos maiores que debitos | Verificar [opcao 459](../financeiro/459-cadastro-tde.md) |
| Unidade nao MTZ | Tentou faturar em CAR | Trocar para MTZ |
| E-mail nao enviado | Cliente sem e-mail na 384 | Cadastrar e-mail na [opcao 384](../financeiro/384-cadastro-clientes.md) |
| Vencimento incorreto | Prazo nao configurado na 384 | Ajustar [opcao 384](../financeiro/384-cadastro-clientes.md) |
| CTRC bloqueado na fatura | Bloqueio financeiro (462) | Resolver na [opcao 462](../financeiro/462-bloqueio-financeiro-ctrc.md) |
| Faturamento retroativo rejeitado | Mes contabil fechado (559) | Reabrir mes ou usar data corrente |

---

## Verificacao Playwright

| Ponto de verificacao | Como verificar |
|---------------------|----------------|
| Unidade ativa = MTZ | Menu principal → unidade selecionada |
| Fatura gerada | [Opcao 457](../financeiro/457-manutencao-faturas.md) → pesquisar fatura → existe com valor correto |
| CTRCs na fatura | [Opcao 457](../financeiro/457-manutencao-faturas.md) → detalhe da fatura → lista CTRCs |
| E-mail do cliente | [Opcao 384](../financeiro/384-cadastro-clientes.md) → CNPJ → campo e-mail preenchido |
| Adicionais incluidos | [Opcao 459](../financeiro/459-cadastro-tde.md) → verificar se debitos/creditos foram incluidos |

---

## POPs Relacionados

| POP | Relacao |
|-----|---------|
| POP-E01 | Pre-faturamento — verificar CTRCs antes (recomendado) |
| POP-A01 | Cadastrar cliente — pre-requisito (inclui [opcao 384](../financeiro/384-cadastro-clientes.md)) |
| POP-C01 | Emitir CTe fracionado — gera CTRCs para faturar |
| POP-C02 | Emitir CTe carga direta — gera CTRCs para faturar |
| POP-E05 | Liquidar fatura — proximo passo (registrar pagamento) |
| POP-E04 | Cobranca bancaria — alternativa ao deposito direto |

---

## Historico de Revisoes

| Data | Alteracao | Autor |
|------|-----------|-------|
| 2026-02-15 | Criacao inicial | Claude (Agente Logistico) |
