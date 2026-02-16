# POP-F06 — Aprovar Despesas Pendentes

> **Versao**: 1.0
> **Criado em**: 2026-02-16
> **Status CarVia**: A IMPLANTAR
> **Opcoes SSW**: [560](../fiscal/560-aprovacao-despesas.md), [475](../financeiro/475-contas-a-pagar.md), [476](../financeiro/476-liquidacao-despesas.md), [380](../comercial/380-definicao-orcamento.md), [903](../cadastros/903-parametros-gerais.md), [918](../cadastros/918-cadastro-grupos.md)
> **Executor atual**: Rafael (nao usa — sem aprovacao centralizada)
> **Executor futuro**: Rafael

---

## Objetivo

Aprovar centralizada de despesas para liberacao de liquidacao. Sistema controla aprovacao por PARCELA (nao por despesa completa), comparando com orcamento da unidade/evento/mes. Apenas despesas aprovadas podem ser liquidadas via [opcao 476](../financeiro/476-liquidacao-despesas.md). Este POP implementa governanca financeira com controle de orcamento.

---

## Quando Executar (Trigger)

- Despesa programada pelas unidades ([opcao 475](../financeiro/475-contas-a-pagar.md)) aguardando aprovacao gerencial
- Analise de orcamento vs comprometido (controle de gastos)
- Aprovacao de despesas urgentes (fora da programacao)
- Revisao semanal ou mensal de despesas pendentes
- Necessidade de reprovar despesa (saldo insuficiente ou justificativa inadequada)

---

## Frequencia

- **Semanal** (analise de parcelas a vencer na proxima semana)
- **Por demanda** (despesas urgentes)
- **Antes de liquidacao** ([opcao 476](../financeiro/476-liquidacao-despesas.md))

---

## Pre-requisitos

| Requisito | Opcao SSW | O que verificar |
|-----------|-----------|-----------------|
| Aprovacao centralizada ativa | [903](../cadastros/903-parametros-gerais.md)/Outros | Parametro de aprovacao centralizada LIGADO |
| Permissao do usuario | [918](../cadastros/918-cadastro-grupos.md) | Grupo do usuario aprovador tem [opcao 560](../fiscal/560-aprovacao-despesas.md) liberada |
| Despesas programadas | [475](../financeiro/475-contas-a-pagar.md) | Parcelas existem e estao aguardando aprovacao |
| Orcamentos cadastrados | [380](../comercial/380-definicao-orcamento.md) | Orcamento por unidade/evento/mes configurado |

> **ATENCAO**: [Opcao 560](../fiscal/560-aprovacao-despesas.md) so aparece para usuarios cujo grupo tem a opcao liberada na [opcao 918](../cadastros/918-cadastro-grupos.md) (Grupos de usuarios).

---

## Passo-a-Passo

### CONFIGURACAO INICIAL (Uma Vez)

#### ETAPA 1 — Ativar Aprovacao Centralizada

1. Acessar [opcao **903**](../cadastros/903-parametros-gerais.md) (Parametros Gerais)
2. Ir para aba **"Outros"**
3. Ativar parametro **"Aprovacao centralizada de despesas"**
4. Gravar

---

#### ETAPA 2 — Liberar Opcao para Aprovadores

5. Acessar [opcao **918**](../cadastros/918-cadastro-grupos.md) (Grupos de usuarios)
6. Selecionar grupo de usuarios aprovadores (ex: "Gerencial", "Financeiro")
7. Localizar [opcao **560**](../fiscal/560-aprovacao-despesas.md) (Aprovacao de despesas)
8. Marcar como **liberada**
9. Gravar
10. Usuarios deste grupo agora podem acessar [opcao 560](../fiscal/560-aprovacao-despesas.md)

---

#### ETAPA 3 — Cadastrar Orcamentos (Recomendado)

11. Acessar [opcao **380**](../comercial/380-definicao-orcamento.md) (Cadastro de orcamentos)
12. Cadastrar orcamento por:
    - **Unidade** (ex: CAR, MTZ)
    - **Evento de despesa** (ex: Combustivel, Manutencao, Frete subcontratado)
    - **Mes/Ano** (ex: 02/2026)
13. Informar **valor orcado**
14. Gravar

> **Sem orcamento cadastrado**: Sistema nao exibe saldo disponivel, mas ainda permite aprovar/reprovar.

---

### PROCESSO RECORRENTE

#### ETAPA 4 — Acessar Opcao 560

15. Acessar [opcao **560**](../fiscal/560-aprovacao-despesas.md) (Aprovacao de Despesas)
16. Sistema exibe tela de filtros

---

#### ETAPA 5 — Filtrar Parcelas a Aprovar

17. Preencher filtros:

| Campo | Valor | Observacao |
|-------|-------|------------|
| **Pagamentos no periodo** | Data inicio e fim | Periodo de pagamento das parcelas (obrigatorio) |
| **Unidade** | [Vazio = todas] | Filtrar despesas de unidade especifica |
| **Numero de Lancamento** | [Vazio] | Filtrar parcelas de despesa especifica (se urgente) |

18. Confirmar filtros
19. Sistema exibe lista de parcelas nao liquidadas aguardando aprovacao

---

#### ETAPA 6 — Analisar Parcelas

20. Para cada parcela, sistema exibe:

| Coluna | Descricao |
|--------|-----------|
| **Numero Lancamento** | ID da despesa ([opcao 475](../financeiro/475-contas-a-pagar.md)) |
| **Fornecedor** | CNPJ/nome do fornecedor |
| **Evento** | Tipo de despesa ([opcao 503](../fiscal/503-manutencao-de-eventos.md)) |
| **Valor** | Valor da parcela |
| **Data Pagamento** | Data prevista |
| **Orcamento** | Valor estabelecido para unidade/evento/mes ([opcao 380](../comercial/380-definicao-orcamento.md)) |
| **Comprometido** | Parcelas ja liquidadas + aprovadas no evento/mes/unidade |
| **Saldo** | Orcamento - Comprometido |
| **Este pagamento** | Valor a aprovar (COR VERMELHA se saldo insuficiente) |
| **Comentario** | Campo para comentario do aprovador |
| **Marca de aprovacao** | Checkbox (ultima coluna) |

21. Verificar para cada parcela:
    - Fornecedor correto
    - Evento correto (classificacao fiscal/contabil)
    - Valor coerente com documento fiscal
    - Saldo orcamentario disponivel

> **Alerta visual**: "Este pagamento" fica VERMELHO se saldo orcamentario insuficiente. Sistema ALERTA mas NAO impede aprovacao.

---

#### ETAPA 7 — Aprovar ou Reprovar

22. **Para APROVAR parcela**:
    - Marcar checkbox na ultima coluna
    - Opcionalmente adicionar comentario (ex: "Aprovado conforme orcamento")

23. **Para REPROVAR parcela** (ou deixar pendente):
    - NAO marcar checkbox
    - Adicionar comentario obrigatorio (ex: "Reprovar: saldo insuficiente", "Aguardar aprovacao diretoria")

24. Confirmar aprovacoes
25. Sistema grava marcas de aprovacao

> **Total dos pagamentos marcados**: Atualizado dinamicamente a cada parcela marcada. Facilita visualizacao do impacto total.

---

#### ETAPA 8 — Liquidar Parcelas Aprovadas

26. Acessar [opcao **476**](../financeiro/476-liquidacao-despesas.md) (Liquidacao de Despesas, POP-F03)
27. Sistema exibe APENAS parcelas aprovadas (marcadas na [opcao 560](../fiscal/560-aprovacao-despesas.md))
28. Liquidar normalmente (ver POP-F03)

> **REGRA**: [Opcao 476](../financeiro/476-liquidacao-despesas.md) so permite liquidar parcelas com marca de aprovacao. Parcelas nao aprovadas ficam bloqueadas.

---

### DESAPROVAR (Remover Marca)

**Quando usar**: Parcela foi aprovada por engano ou orcamento mudou.

29. Acessar [opcao **560**](../fiscal/560-aprovacao-despesas.md)
30. Filtrar por periodo
31. Localizar parcela aprovada (marcada)
32. Desmarcar checkbox
33. Adicionar comentario (ex: "Desaprovado: prioridade alterada")
34. Confirmar

> **RESTRICAO**: Marca so pode ser retirada ENQUANTO parcela nao foi liquidada. Apos liquidacao ([opcao 476](../financeiro/476-liquidacao-despesas.md)), marca e permanente.

---

## Fluxo Completo de Aprovacao

```
Unidade programa despesa (opcao 475)
      ↓
Parcela aguarda aprovacao
      ↓
Aprovador acessa opcao 560
      ↓
Analisa: orcamento, comprometido, saldo
      ↓
Marca parcelas aprovadas
      ↓
Sistema libera para liquidacao
      ↓
Unidade liquida (opcao 476) — APENAS aprovadas
      ↓
Marca de aprovacao torna-se permanente
```

---

## Contexto CarVia

### Hoje

- Rafael NAO usa aprovacao centralizada
- Jaqueline pagara despesas SEM controle orcamentario formal
- SEM orcamento por evento/mes
- SEM bloqueio para despesas nao aprovadas

### Futuro (com POP implantado)

- Rafael como aprovador (grupo gerencial)
- Orcamento mensal por evento ([380](../comercial/380-definicao-orcamento.md)):
  - Combustivel: R$ 5.000/mes
  - Manutencao: R$ 3.000/mes
  - Frete subcontratado: conforme demanda (sem limite)
- Jaqueline programa despesas ([475](../financeiro/475-contas-a-pagar.md))
- Rafael aprova semanalmente ([560](../fiscal/560-aprovacao-despesas.md))
- Jaqueline liquida apenas aprovadas ([476](../financeiro/476-liquidacao-despesas.md))

**Vantagem**: Controle de gastos operacionais (combustivel, manutencao) vs orcamento. Frete subcontratado sem limite (receita vinculada).

---

## Erros Comuns e Solucoes

| Erro | Causa | Solucao |
|------|-------|---------|
| [Opcao 560](../fiscal/560-aprovacao-despesas.md) nao aparece | Usuario sem permissao ([opcao 918](../cadastros/918-cadastro-grupos.md)) | Liberar [opcao 560](../fiscal/560-aprovacao-despesas.md) para grupo do usuario |
| Lista de parcelas vazia | Nenhuma despesa programada ou todas liquidadas | Verificar [opcao 475](../financeiro/475-contas-a-pagar.md) |
| Saldo negativo (vermelho) | Orcamento insuficiente | Aprovar mesmo assim OU reprovar e ajustar orcamento ([380](../comercial/380-definicao-orcamento.md)) |
| Parcela nao aparece em [476](../financeiro/476-liquidacao-despesas.md) | Nao aprovada na [opcao 560](../fiscal/560-aprovacao-despesas.md) | Aprovar na [opcao 560](../fiscal/560-aprovacao-despesas.md) primeiro |
| Desaprovar nao funciona | Parcela ja liquidada | Marca permanente apos liquidacao |
| Orcamento nao exibido | Nao cadastrado na [opcao 380](../comercial/380-definicao-orcamento.md) | Cadastrar orcamento por unidade/evento/mes |

---

## Indicadores de Saude

| Indicador | Bom | Atencao | Critico |
|-----------|-----|---------|---------|
| Parcelas aguardando aprovacao | 0-5 | 6-10 | 11+ |
| Parcelas com saldo negativo | 0-1 | 2-3 | 4+ |
| Dias ate vencimento medio | 7+ | 3-6 | 0-2 |

**Acao se critico**: Aprovar urgentemente ou reprovar com justificativa. Revisar orcamentos se saldos negativos recorrentes.

---

## Verificacao Playwright

| Ponto de verificacao | Como verificar |
|---------------------|----------------|
| Aprovacao centralizada ativa | [Opcao 903](../cadastros/903-parametros-gerais.md) → Outros → parametro LIGADO |
| Usuario com permissao | [Opcao 918](../cadastros/918-cadastro-grupos.md) → grupo → [opcao 560](../fiscal/560-aprovacao-despesas.md) liberada |
| Orcamento cadastrado | [Opcao 380](../comercial/380-definicao-orcamento.md) → unidade/evento/mes → valor orcado |
| Parcela aguardando aprovacao | [Opcao 560](../fiscal/560-aprovacao-despesas.md) → filtrar periodo → lista nao vazia |
| Parcela aprovada | [Opcao 560](../fiscal/560-aprovacao-despesas.md) → parcela marcada → comentario registrado |
| Liquidacao bloqueada | [Opcao 476](../financeiro/476-liquidacao-despesas.md) → parcela nao aprovada NAO aparece |

---

## POPs Relacionados

| POP | Relacao |
|-----|---------|
| POP-F01 | Lancar contas a pagar — origem das parcelas |
| POP-F03 | Liquidar despesa — proximo passo (apenas aprovadas) |
| POP-F04 | Conciliacao bancaria — conferir tudo no final |
| POP-F02 | CCF — controle de saldo com fornecedores |

---

## Historico

| Data | Versao | Alteracao |
|------|--------|-----------|
| 2026-02-16 | 1.0 | Criacao inicial (Onda 5) |
