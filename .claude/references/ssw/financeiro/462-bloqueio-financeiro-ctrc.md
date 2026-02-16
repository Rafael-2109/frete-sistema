# Opcao 462 — Bloqueio Financeiro de CTRC

> **Modulo**: Financeiro
> **Status CarVia**: NAO IMPLANTADO
> **Atualizado em**: 2026-02-16

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
- [CONFIRMAR: se e necessario estar em unidade especifica para acessar 462]

## Campos / Interface

> **[CONFIRMAR]**: Campos inferidos do POP-F05 e das referencias indiretas na opcao 435. A opcao 462 NAO tem documentacao de ajuda SSW dedicada. Validar detalhes no ambiente SSW real.

### Tela de Bloqueio

| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| **Numero do CTRC** | Sim | Numero com serie do CTe a ser bloqueado |
| **[CONFIRMAR: Filial emissora]** | [CONFIRMAR] | Sigla da filial que emitiu o CTe |
| **Motivo do bloqueio** | Sim | Descricao textual justificando o bloqueio |
| **[CONFIRMAR: Tipo de bloqueio]** | [CONFIRMAR] | Pode haver tipos pre-cadastrados (operacional, comercial, fiscal) |
| **[CONFIRMAR: Data limite]** | [CONFIRMAR] | Data prevista para resolucao (se bloqueio temporario) |
| **[CONFIRMAR: Responsavel]** | [CONFIRMAR] | Login do usuario que registrou o bloqueio |

### Tela de Desbloqueio

| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| **Numero do CTRC** | Sim | CTRC a desbloquear |
| **Motivo do desbloqueio** | [CONFIRMAR] | Justificativa da resolucao |
| **[CONFIRMAR: Data resolucao]** | [CONFIRMAR] | Data em que a pendencia foi resolvida |

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
- **[CONFIRMAR]**: Verificar se existe historico de bloqueios/desbloqueios (auditoria)
- **[CONFIRMAR]**: Verificar se ha alerta automatico para bloqueios antigos (ex: > 30 dias)
- **[CONFIRMAR]**: Verificar se existe relatorio dedicado de CTRCs bloqueados
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
| **Adocao** | NAO IMPLANTADO — Rafael nunca bloqueou CTRC no SSW |
| **Hoje** | Se CTRC tem pendencia, Rafael simplesmente nao fatura. Risco de esquecer e nunca faturar |
| **Executor futuro** | Rafael (bloqueio/desbloqueio comercial) |
| **Impacto** | Sem controle formal: risco de faturar CTRC com pendencia ou esquecer de faturar apos resolucao |
| **POPs dependentes** | POP-F05 |
