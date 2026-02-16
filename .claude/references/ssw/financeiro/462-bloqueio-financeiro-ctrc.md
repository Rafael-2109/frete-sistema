# Opcao 462 — Bloqueio Financeiro de CTRC

> **Modulo**: Contas a Receber / CTRCs disponíveis (menu: Contas a Receber > CTRCs disponíveis > 462)
> **Status CarVia**: ACESSIVEL — tela verificada, NAO IMPLANTADO operacionalmente
> **Atualizado em**: 2026-02-16
> **SSW interno**: ssw0760 | Verificado via Playwright em 16/02/2026

## Funcao

Registra e gerencia bloqueios financeiros em CTRCs para impedir que sejam incluidos no faturamento (opcoes 436 e 437) ate a resolucao de pendencia operacional ou comercial. CTRCs bloqueados NAO aparecem como disponiveis para faturamento na opcao 435 (a menos que o filtro "Considerar bloq. financeiro = S" seja marcado) e NAO sao processados pelo faturamento automatico (opcao 436). Este mecanismo protege contra cobranca indevida de CTRCs com problemas pendentes.

## Quando Usar

- CTRC com pendencia operacional: avaria, extravio, atraso severo, entrega incompleta
- Cliente contesta valor do frete ANTES do faturamento
- Erro de emissao que impacta valor (peso, mercadoria, destino incorretos)
- Acordo comercial para suspender cobranca temporariamente
- CTe complementar pendente de emissao (aguardando correcao de diferenca)
- Extravio total — aguardando resolucao com seguradora

## Pre-requisitos

- CTRC emitido e autorizado pelo SEFAZ (opcao 007)
- CTRC ainda NAO faturado — se ja estiver em fatura, primeiro retirar da fatura (opcao 457)
- Motivo/justificativa clara para o bloqueio

## Campos / Interface — VERIFICADOS

> **Verificado via Playwright em 16/02/2026 contra o SSW real.**

A tela tem 3 secoes distintas: bloqueio por CTRC, bloqueio por manifesto, e relatorio de bloqueados.

### Secao 1: Bloquear por CTRC

| Campo | Name/ID | Obrigatorio | Descricao |
|-------|---------|-------------|-----------|
| **Motivo** | f1 / id=1 | Sim | Texto livre do motivo do bloqueio (maxlen=60) |
| **CTRC (com DV) — Dominio** | f2 / id=2 | Sim | Dominio do CTRC (maxlen=3) |
| **CTRC (com DV) — Numero** | f3 / id=3 | Sim | Numero do CTRC com digito verificador (maxlen=7) |

**Acao**: ► `ajaxEnvia('ENV_CTRC', 0)` — bloqueia o CTRC informado

### Secao 2: Bloquear por Manifesto

| Campo | Name/ID | Obrigatorio | Descricao |
|-------|---------|-------------|-----------|
| **Manifesto (com DV) — Dominio** | f6 / id=6 | Sim | Dominio do manifesto (maxlen=3) |
| **Manifesto (com DV) — Numero** | f7 / id=7 | Sim | Numero do manifesto com DV (maxlen=7) |

**Acao**: ► `ajaxEnvia('ENV_MAN', 0)` — bloqueia todos os CTRCs do manifesto

### Secao 3: Relatorio de CTRCs Bloqueados

| Campo | Name/ID | Obrigatorio | Descricao |
|-------|---------|-------------|-----------|
| **Listar em** | f10 / id=10 | Sim | "V" para video, "R" para relatorio (maxlen=1, default: V) |
| **Periodo de bloqueio (inicio)** | f11 / id=11 | Sim | Data inicio ddmmaa (maxlen=6) |
| **Periodo de bloqueio (fim)** | f12 / id=12 | Sim | Data fim ddmmaa (maxlen=6) |

**Acao**: ► `ajaxEnvia('PER', 1)` — gera relatorio dos bloqueados no periodo

### Campos NAO Encontrados (inferencia descartada)

| Campo Inferido | Status |
|----------------|--------|
| Filial emissora | **NAO EXISTE** como campo separado — dominio faz esse papel (f2) |
| Tipo de bloqueio (operacional/comercial/fiscal) | **NAO EXISTE** — motivo e texto livre (f1) |
| Data limite | **NAO EXISTE** — sem data de resolucao prevista |
| Responsavel | **NAO EXISTE** como campo visivel — provavelmente registrado automaticamente pelo SSW |
| Motivo do desbloqueio | **NAO VERIFICAVEL** na tela inicial — pode aparecer ao consultar CTRC bloqueado |
| Data resolucao | **NAO EXISTE** na tela principal |

## Fluxo de Uso

### Bloquear CTRC

1. Acessar opcao 462
2. Informar numero do CTRC a ser bloqueado
3. Sistema exibe dados do CTRC (numero, serie, data, cliente, valor, situacao)
4. Preencher motivo do bloqueio (obrigatorio)
5. Confirmar bloqueio
6. CTRC removido da lista de disponiveis para faturamento (opcao 435)

### Verificar Bloqueio

1. Acessar opcao 435 (CTRCs Disponiveis para Faturamento)
2. Marcar filtro "Considerar bloq. financeiro = S"
3. Gerar relatorio
4. Coluna BLOQUEADO indica CTRCs com bloqueio financeiro ativo

### Desbloquear CTRC

1. Acessar opcao 462
2. Informar numero do CTRC bloqueado
3. Localizar bloqueio ativo
4. Informar motivo do desbloqueio
5. Confirmar desbloqueio
6. CTRC volta a aparecer como disponivel para faturamento (opcao 435)

## Integracao com Outras Opcoes

| Opcao | Relacao |
|-------|---------|
| 435 | Pre-faturamento — coluna BLOQUEADO indica CTRCs com bloqueio financeiro. Filtro "Considerar bloq. financeiro" controla visibilidade |
| 436 | Faturamento geral — CTRCs bloqueados NAO sao incluidos no faturamento automatico |
| 437 | Faturamento manual — CTRCs bloqueados NAO aparecem na lista de disponiveis |
| 457 | Manutencao de faturas — se CTRC ja faturado, primeiro retirar da fatura aqui antes de bloquear |
| 459 | Relacao de adicionais — apos desbloquear, pode ser necessario cadastrar adicional (desconto por avaria, etc.) |
| 007 | Emissao CTe complementar — cenario de bloqueio por erro de valor: emitir complementar antes de desbloquear |

## Observacoes e Gotchas

- **So funciona ANTES do faturamento**: Se CTRC ja foi incluido em fatura, nao pode ser bloqueado. Primeiro retirar da fatura na opcao 457 (POP-E06)
- **Nao impede emissao**: O bloqueio e apenas financeiro (impede faturamento). O CTe continua valido fiscalmente
- **Visibilidade na 435**: Por padrao, CTRCs bloqueados NAO aparecem na opcao 435. Para visualiza-los, marcar "Considerar bloq. financeiro = S"
- **Bloqueio por manifesto**: Permite bloquear TODOS os CTRCs de um manifesto de uma vez (secao 2 da tela)
- **Relatorio de bloqueados EXISTE**: Secao 3 da tela (campo f10=V/R, periodo f11-f12) lista CTRCs bloqueados
- **Motivo e texto livre**: Maximo 60 caracteres. NAO ha tipos pre-cadastrados (operacional/comercial/fiscal)
- **Sem data limite**: NAO existe campo de previsao de resolucao. Bloqueio e permanente ate desbloqueio manual
- **Risco sem bloqueio**: Se CTRC com pendencia nao for bloqueado, pode ser faturado acidentalmente pelo faturamento automatico (opcao 436)

## POPs Relacionados

| POP | Relacao |
|-----|---------|
| POP-F05 | Bloqueio financeiro de CTRC — POP completo passo-a-passo para esta opcao |
| POP-E01 | Pre-faturamento — identifica CTRCs bloqueados na coluna BLOQUEADO |
| POP-E02 | Faturamento manual — CTRCs bloqueados nao aparecem |
| POP-E03 | Faturamento automatico — CTRCs bloqueados nao sao incluidos |
| POP-E06 | Manutencao de faturas — retirar CTRC de fatura existente para permitir bloqueio |
| POP-C03 | CTe complementar — cenario de bloqueio por erro de emissao |

## Status CarVia

| Aspecto | Status |
|---------|--------|
| **Adocao** | VERIFICADO — tela acessivel (ssw0760). NAO IMPLANTADO operacionalmente |
| **Hoje** | Se CTRC tem pendencia, Rafael simplesmente nao fatura. Risco de esquecer e nunca faturar |
| **Executor futuro** | Rafael (bloqueio/desbloqueio comercial) |
| **Impacto** | Sem controle formal: risco de faturar CTRC com pendencia ou esquecer de faturar apos resolucao |
| **Funcionalidades confirmadas** | Bloqueio individual (por CTRC), bloqueio em massa (por manifesto), relatorio de bloqueados por periodo |
| **POPs dependentes** | POP-F05 |
