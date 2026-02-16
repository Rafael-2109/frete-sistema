# Opcao 108 — Instrucoes para Ocorrencias de Entrega

> **Modulo**: Operacional
> **Status CarVia**: NAO IMPLANTADO
> **Atualizado em**: 2026-02-16

## Funcao

Gerencia instrucoes para CTRCs com ocorrencias pendentes de resolucao. Enquanto a opcao 133 permite ao usuario acompanhar "Minhas Ocorrencias" (ocorrencias registradas pelo proprio usuario ou pela sua unidade de origem), a opcao 108 e usada pela unidade destino para enviar instrucoes de resolucao e pela unidade origem para consultar sobras nao identificadas. Tambem serve para registrar baixas de sobras quando o CTRC correspondente e localizado.

## Diferenca entre Opcao 108 e Opcao 133

| Aspecto | Opcao 108 | Opcao 133 |
|---------|-----------|-----------|
| **Perspectiva** | Unidade DESTINO (recebeu CTRC com problema) | Unidade ORIGEM (enviou CTRC que teve problema) |
| **Funcao principal** | Enviar instrucoes de resolucao | Acompanhar ocorrencias registradas |
| **Quem usa** | Operador da base destino | Operador da base origem |
| **Acao principal** | Instruir o que fazer com CTRC pendente | Ler instrucao e tomar acao |
| **Complementar a** | Opcao 033 (registro) e 038 (baixa) | Opcao 108 (instrucoes) |

## Quando Usar

- Diariamente: consultar CTRCs com ocorrencia pendente de instrucao na unidade destino
- Apos registro de ocorrencia (opcao 033 ou 038): enviar instrucao de resolucao
- Para registrar contato com remetente/destinatario e orientar proximos passos
- Consultar sobras de volumes nao identificados (referenciado na opcao 133)
- Final do dia: garantir que NENHUM CTRC reste sem instrucao (regra SSW)
- Controlar prazo de resolucao de ocorrencias

## Pre-requisitos

- Ocorrencia registrada previamente (opcao 033 para transferencia ou 038 para entrega)
- Tabela de ocorrencias configurada (opcao 405)
- Acesso com perfil operacional na unidade destino
- [CONFIRMAR: se unidade especifica e necessaria para acessar]

## Campos / Interface

> **[CONFIRMAR]**: Os campos abaixo sao inferidos do contexto do POP-D06 e da documentacao da opcao 133. Validar no ambiente SSW real.

### Tela Inicial — Lista de CTRCs Pendentes

| Campo | Descricao |
|-------|-----------|
| **CTRC** | Numero do CTRC com ocorrencia pendente |
| **Ocorrencia** | Codigo e descricao da ocorrencia (opcao 405) |
| **Data ocorrencia** | Data/hora em que a ocorrencia foi registrada |
| **Unidade origem** | Unidade que expediu o CTRC |
| **Status** | Aguardando instrucao / Instrucao enviada / Resolvido |
| **[CONFIRMAR: Dias pendente]** | Tempo desde registro da ocorrencia |

### Tela de Instrucao

| Campo | Descricao |
|-------|-----------|
| **Instrucao** | Texto descritivo da acao a ser tomada (ex: "Reagendar entrega para 20/02", "Devolver ao remetente") |
| **[CONFIRMAR: Tipo de instrucao]** | Pode haver tipos pre-cadastrados (reagendar, devolver, descartar, etc.) |
| **[CONFIRMAR: Data prevista]** | Data prevista para resolucao |
| **Observacoes** | Campo adicional para registro de tentativas de contato |

## Fluxo de Uso

### Enviar Instrucao (Unidade Destino)

1. Acessar opcao 108
2. Sistema exibe lista de CTRCs da unidade com ocorrencia pendente de instrucao
3. Selecionar CTRC
4. Analisar tipo de ocorrencia:
   - **Pendencia do Cliente**: Contatar remetente/destinatario para obter orientacao
   - **Responsabilidade Transportadora**: Definir acao operacional (reentrega, devolucao, etc.)
5. Preencher instrucao no sistema
6. Confirmar envio
7. Sistema notifica unidade origem (visivel na opcao 133)

### Consultar Sobras

1. Acessar opcao 108
2. Navegar para funcao de sobras [CONFIRMAR: caminho exato]
3. Consultar volumes nao identificados
4. Quando CTRC correspondente for localizado: registrar baixa da sobra

## Integracao com Outras Opcoes

| Opcao | Relacao |
|-------|---------|
| 033 | Registrar ocorrencias de transferencia — gera pendencias para a 108 |
| 038 | Registrar baixa de entregas — gera pendencias de ocorrencia para a 108 |
| 133 | Minhas Ocorrencias (unidade origem) — recebe instrucoes enviadas pela 108 |
| 138 | Estornar baixa de entrega — usado para corrigir ocorrencia registrada incorretamente |
| 291 | Segregar volumes com instrucao automatica — gera instrucao automatica na 108 |
| 405 | Tabela de ocorrencias — define codigos de ocorrencia usados |
| 943 | Liberar ocorrencias finalizadoras para EDI — controla envio de status a clientes |

## Observacoes e Gotchas

- **Regra SSW critica**: Nenhum CTRC com ocorrencia deve restar sem instrucao ao final do dia
- **Diferente da opcao 133**: A 108 e para a unidade DESTINO instruir; a 133 e para a unidade ORIGEM acompanhar
- **Segregacao**: Se ocorrencia exige segregacao fisica, a opcao 291 pode gerar instrucao automatica
- **[CONFIRMAR]**: Verificar se ha notificacao automatica quando instrucao e registrada
- **[CONFIRMAR]**: Verificar se existe relatorio de tempo medio de resolucao por tipo de ocorrencia

## POPs Relacionados

| POP | Relacao |
|-----|---------|
| POP-D06 | Registrar ocorrencias — POP completo que usa esta opcao como passo central (ETAPA 2) |
| POP-D05 | Baixa de entrega — ocorrencias de entrega sao registradas durante baixa (opcao 038) |
| POP-D04 | Chegada de veiculo — ocorrencias de transferencia registradas na chegada (opcao 033) |

## Status CarVia

| Aspecto | Status |
|---------|--------|
| **Adocao** | NAO IMPLANTADO |
| **Hoje** | Ocorrencias tratadas via telefone/WhatsApp, sem registro formal no SSW |
| **Executor futuro** | Stephanie (monitoramento diario), Rafael (escalacao apos 3 dias) |
| **Pendencia** | PEND-08 — Treinar Stephanie em baixa/ocorrencias |
| **POPs dependentes** | POP-D06 |
