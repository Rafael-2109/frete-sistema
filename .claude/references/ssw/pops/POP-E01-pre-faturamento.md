# POP-E01 — Verificar CTRCs Disponiveis para Faturamento

> **Categoria**: E — Financeiro: Recebiveis
> **Prioridade**: P1 (Alta — verificacao antes de faturar)
> **Status anterior**: A IMPLANTAR
> **Criado em**: 2026-02-15
> **Executor atual**: Rafael (nao usa)
> **Executor futuro**: Jaqueline

---

## Objetivo

Verificar quais CTRCs estao disponiveis para faturamento, identificar pendencias (e-mail faltante, bloqueios, parametros incorretos) e garantir que o faturamento (POP-E02 ou POP-E03) sera executado sem erros. Este POP e uma etapa de VERIFICACAO que deve ser executada ANTES de faturar.

---

## Trigger

- Antes de executar faturamento manual (POP-E02, opcao 437) ou automatico (POP-E03, opcao 436)
- Periodicamente para monitorar CTRCs pendentes de faturamento
- Cliente reclama que nao recebeu fatura — investigar

---

## Frequencia

Semanal (antes do faturamento) ou por demanda.

---

## Pre-requisitos

| Requisito | Opcao SSW | O que verificar |
|-----------|-----------|-----------------|
| CTes autorizados | [007](../operacional/007-emissao-cte-complementar.md) | Ao menos 1 CTe autorizado no SEFAZ |
| Clientes cadastrados | [483](../cadastros/483-cadastro-clientes.md) | Clientes existem no SSW |
| Parametros de faturamento | [384](../financeiro/384-cadastro-clientes.md) | Tipo (A/M), periodicidade, banco, e-mail configurados |

---

## Passo-a-Passo

### ETAPA 1 — Acessar Opcao 435

1. Acessar [opcao **435**](../financeiro/435-pre-faturamento.md) (CTRCs Disponiveis para Faturamento)
2. Verificar unidade ativa — pode ser CAR ou MTZ (435 aceita ambas)

---

### ETAPA 2 — Configurar Filtros

3. Preencher filtros de selecao:

| Campo | Valor recomendado | Observacao |
|-------|-------------------|------------|
| **CTRCs autorizados ate** | Data atual | Ver todos os CTRCs autorizados ate hoje |
| **Sigla das filiais** | CAR (ou todas) | Filtrar por unidade |
| **CNPJ Cliente** | Deixar vazio (todos) | Ou informar CNPJ especifico |
| **Situacao do CTRC** | I (impressos) | I=impressos, E=arquivados, B=baixados |
| **Periodicidade** | T (todos) | Ou selecionar tipo especifico |
| **Considerar bloq. financeiro** | S | Para ver bloqueios |
| **Considerar CTRCs a vista** | N | Cuidado: normalmente ja cobrados na entrega |

4. Clicar em **Gerar relatorio**

---

### ETAPA 3 — Analisar Resultado

5. Verificar cada coluna do relatorio:

| Coluna | O que verificar | Acao se problema |
|--------|-----------------|------------------|
| **TIP** | A=automatico, M=manual | Se M: usar [opcao 437](../financeiro/437-faturamento-manual.md) (POP-E02) |
| **PER** | Periodicidade correta? | Se errado: corrigir [opcao 384](../financeiro/384-cadastro-clientes.md) |
| **BAN/CART** | Banco de cobranca definido? | Se vazio: cadastrar [opcao 384](../financeiro/384-cadastro-clientes.md) |
| **ENV / E-MAILS** | Cliente tem e-mail? | Se vazio: **fatura NAO sera enviada** por e-mail |
| **BLOQUEADO** | CTRC bloqueado? | Se sim: resolver [opcao 462](../financeiro/462-bloqueio-financeiro-ctrc.md) antes de faturar |
| **ARQUIVO MORTO** | CTRC no arquivo morto? | Se sim: retornar via [opcao 101](../comercial/101-resultado-ctrc.md) |

---

### ETAPA 4 — Resolver Pendencias

6. Para cada pendencia encontrada:

| Pendencia | Como resolver |
|-----------|---------------|
| **Cliente sem e-mail** | [Opcao 384](../financeiro/384-cadastro-clientes.md) → cadastrar e-mail do pagador |
| **CTRC bloqueado** | [Opcao 462](../financeiro/462-bloqueio-financeiro-ctrc.md) → verificar motivo → desbloquear se resolvido |
| **Periodicidade errada** | [Opcao 384](../financeiro/384-cadastro-clientes.md) → corrigir campo periodicidade |
| **Banco nao cadastrado** | [Opcao 384](../financeiro/384-cadastro-clientes.md) → informar banco/carteira |
| **CTRC no arquivo morto** | [Opcao 101](../comercial/101-resultado-ctrc.md) → retornar do arquivo morto |
| **Tipo faturamento errado** | [Opcao 384](../financeiro/384-cadastro-clientes.md) → corrigir tipo (A=auto, M=manual) |

---

### ETAPA 5 — Exportar Relatorio (Opcional)

7. Clicar em **Gerar em Excel** para exportar relatorio completo
8. Usar Excel para:
   - Conferir valores por cliente
   - Identificar CTRCs antigos nao faturados
   - Comparar com controle interno

---

### ETAPA 6 — Prosseguir para Faturamento

9. Apos resolver pendencias:
   - **Cliente tipo M** → POP-E02 ([opcao 437](../financeiro/437-faturamento-manual.md), faturamento manual)
   - **Cliente tipo A** → POP-E03 ([opcao 436](../financeiro/436-faturamento-geral.md), faturamento automatico)

---

## Indicadores de Saude

| Indicador | Bom | Atencao | Critico |
|-----------|-----|---------|---------|
| CTRCs sem faturar (> 30 dias) | 0 | 1-3 | 4+ |
| Clientes sem e-mail | 0 | — | Qualquer |
| CTRCs bloqueados | 0 | 1-2 | 3+ |
| CTRCs no arquivo morto | 0 | — | Qualquer |

---

## Erros Comuns e Solucoes

| Erro | Causa | Solucao |
|------|-------|---------|
| Lista vazia | Nenhum CTe autorizado ou todos ja faturados | Verificar [opcao 007](../operacional/007-emissao-cte-complementar.md) |
| Cliente aparece sem dados | [Opcao 384](../financeiro/384-cadastro-clientes.md) nao configurada | Configurar [384](../financeiro/384-cadastro-clientes.md) antes |
| CTRC aparece como serie 999 | Serie 999 nao e considerada disponivel | Verificar emissao |
| CTRC nao aparece na lista | Ja em fatura, nao na unidade, ou serie 999 | Consultar [opcao 101](../comercial/101-resultado-ctrc.md) |

---

## Verificacao Playwright

| Ponto de verificacao | Como verificar |
|---------------------|----------------|
| CTRCs disponiveis existem | [Opcao 435](../financeiro/435-pre-faturamento.md) → gerar relatorio → lista nao vazia |
| E-mail cadastrado | [Opcao 384](../financeiro/384-cadastro-clientes.md) → CNPJ → campo e-mail preenchido |
| Sem bloqueios | [Opcao 435](../financeiro/435-pre-faturamento.md) → coluna BLOQUEADO = vazio para todos |
| Tipo faturamento correto | [Opcao 384](../financeiro/384-cadastro-clientes.md) → CNPJ → campo tipo = M ou A |
| Banco cadastrado | [Opcao 384](../financeiro/384-cadastro-clientes.md) → CNPJ → banco/carteira preenchidos |

---

## POPs Relacionados

| POP | Relacao |
|-----|---------|
| POP-E02 | Faturar manualmente — proximo passo (tipo M) |
| POP-E03 | Faturar automaticamente — proximo passo (tipo A) |
| POP-A01 | Cadastrar cliente — inclui configuracao da opcao 384 |
| POP-C01 | Emitir CTe fracionado — gera CTRCs para faturar |
| POP-C02 | Emitir CTe carga direta — gera CTRCs para faturar |

---

## Historico de Revisoes

| Data | Alteracao | Autor |
|------|-----------|-------|
| 2026-02-15 | Criacao inicial | Claude (Agente Logistico) |
