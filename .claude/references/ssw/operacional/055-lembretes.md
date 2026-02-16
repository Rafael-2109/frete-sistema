# Opcao 055 — Lembretes do Cliente

> **Modulo**: Cadastro — Clientes
> **Paginas de ajuda**: Nao localizado arquivo consolidado
> **Atualizado em**: 2026-02-14

## Funcao
Cadastra lembretes do cliente ao usuario do SSW para diversos processos: coleta, coleta devolucao, destinatario, cotacao, digitacao CTRC, entrega, consulta cliente e faturamento.

## Quando Usar
- Cadastrar alertas/lembretes por cliente
- Orientar usuarios sobre particularidades do cliente
- Exibir observacoes importantes em telas operacionais

## Pre-requisitos
- Cliente cadastrado

## Tipos de Lembretes

| Tipo | Onde e Mostrado |
|------|-----------------|
| COLETA | Opcao 001 quando cliente e remetente (gravado na observacao + impresso na Ordem de Coleta) |
| COLETA DEVOL | Opcao 001 quando cliente e destinatario |
| DESTINATARIO | Opcao 001 quando cliente e destinatario de coleta |
| COTACAO | Opcao 002 quando cliente e pagador |
| DIGIT CTRC | Opcao 004 para Remetente, Destinatario ou Pagador |
| ENTREGA | Opcao 035 (Romaneio) e Opcao 081 (CTRCs Disponiveis) |
| CLIENTE | Opcao 102 (Situacao do Cliente) |
| FATURAMENTO | Opcao 384 e Opcao 435 quando cliente e pagador |

## Campos / Interface

| Campo | Descricao |
|-------|-----------|
| CNPJ/CPF | Cliente a receber lembrete |
| Tipo | Tipo do lembrete (ver tabela acima) |
| Texto | Mensagem do lembrete |

## Fluxo de Uso
1. Acessar Opcao 055
2. Informar CNPJ/CPF cliente
3. Selecionar tipo de lembrete
4. Digitar texto do lembrete
5. Gravar

## Integracao com Outras Opcoes

| Opcao | Relacao |
|-------|---------|
| 001 | Mostra lembrete em tela e imprime na Ordem de Coleta |
| 002 | Mostra lembrete ao simular cotacao |
| 004 | Mostra lembrete ao gravar CTRC |
| 005 | Sugerido em Instrucoes entrega (se tipo DIGIT CTRC) |
| 006 | Sugerido em Instrucoes entrega (se tipo DIGIT CTRC) |
| 035 | Mostra lembrete ao carregar Romaneio |
| 055 | Esta opcao |
| 059 | Observacoes impressas em CTRCs/boletos |
| 080 | Instrucoes entrega gravadas na NF |
| 081 | Mostra lembrete em relatorio CTRCs Disponiveis |
| 101 | Instrucao resgate mercadoria (ocorrencia SSW 88) |
| 102 | Mostra lembrete ao consultar cliente |
| 381 | Deixar DACTE em destinatario FOB |
| 384 | Mostra lembrete em cadastro faturamento |
| 435 | Mostra lembrete em CTRCs disponiveis faturar |
| 483 | Pegar canhoto NF assinado |

## Observacoes e Gotchas

### Emissao do CTRC
Observacao gravada por Opcao 055 e sugerida na geracao CTRC (Opcao 004, 005, 006) no campo "Instrucoes entrega". E impressa na DACTE e Romaneio de Entregas e mostrada no SSWMobile.

### Relacao de Clientes
Link "Relacao de clientes" traz relatorio relacionando todos clientes e seus lembretes cadastrados.

### Opcoes Relacionadas
- Opcao 101: Instrucao resgate mercadoria (codigo SSW 88)
- Opcao 055: Lembretes mostrados em tela/impressos
- Opcao 059: Observacoes impressas em CTRCs/boletos
- Opcao 080: Instrucoes entrega gravadas na NF
- Opcao 381: Deixar DACTE em destinatario FOB
- Opcao 483: Pegar canhoto NF assinado
