# Opcao 108 — Instrucoes para Ocorrencias de Entrega

> **Modulo**: Cliente / Ocorrências (menu: Cliente > Ocorrências > 108)
> **Status CarVia**: ACESSIVEL — NAO IMPLANTADO operacionalmente
> **Atualizado em**: 2026-02-16
> **SSW interno**: ssw0118 | Verificado via Playwright em 16/02/2026

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
- Acesso com perfil operacional na unidade

## Campos / Interface — VERIFICADOS

> **Verificado via Playwright em 16/02/2026 contra o SSW real.**
>
> Titulo real: "Instruções para ocorrências" (ssw0118). Tela muito completa com 12 inputs visiveis e multiplas secoes de filtro/pesquisa.

### Secao 1: Sem Instrucao

| Campo | Name/ID | Descricao |
|-------|---------|-----------|
| **Sem instrucao (S/N)** | t_sem_instr | Default "S" — filtra CTRCs sem instrucao (maxlen=2) |

**Acao**: ► `ajaxEnvia('PES_SEM', 1)` — pesquisa CTRCs sem instrucao

### Secao 2: Filtros por Tipo

| Campo | Name/ID | Descricao |
|-------|---------|-----------|
| **Codigo de ocorrencia** | t_codigo / msgoco | Codigo da ocorrencia (maxlen=2) + descricao. Link "findocor" abre lookup |
| **Sigla do subcontratante** | t_sigla_sub | Filtra por parceiro (maxlen=5). Link "findtra" |
| **CNPJ do cliente** | t_cnpj_cli | Filtra por cliente (maxlen=14). Link "findcli" |
| **CNPJ do grupo** | t_cnpj_grupo | Filtra por grupo economico (maxlen=14). Link para lookup |
| **Usuario** | t_usuario | Filtra por usuario registrador (maxlen=8). Link "findusu" |
| **Conferente** | t_conferente | Filtra por conferente (maxlen=4). Link "findcon" |

Cada filtro tem seu proprio ► de pesquisa independente (`PES_OCO`, `PES_SUB`, `PES_CLI`, `PES_GRU`, `PES_USU`, `PES_CON`).

### Secao 3: Pesquisa por Responsabilidade

| Botao | Acao |
|-------|------|
| **Ocorrencias resp. cliente com origem aqui** | `ajaxEnvia('PES_RES', 1)` |
| **Ocorrencias resp. transportadora** | `ajaxEnvia('PES_RE2', 1)` |

### Secao 4: Relatorio por Periodo

| Campo | Name/ID | Descricao |
|-------|---------|-----------|
| **Periodo de ocorrencias (inicio)** | t_data_ini_ult | Data inicio ddmmaa (maxlen=6, default: 3 meses atras) |
| **Periodo de ocorrencias (fim)** | t_data_fim_ult | Data fim ddmmaa (maxlen=6, default: hoje) |
| **Selecionar** | t_sel_atrasados | "A" = atrasados, "T" = todos (maxlen=1, default: T) |
| **Mostrar em** | t_vid_rel | "V" = video, "R" = relatorio, "E" = excel ocor+instr, "X" = excel ocorrencias (maxlen=1, default: V) |

### Acoes Adicionais

| Botao | Acao |
|-------|------|
| **Minhas Ocorrencias** | `ajaxEnvia('', 1, 'ssw1184')` — abre tela de ocorrencias do usuario |
| **Localizacao de SOBRAS** | `ajaxEnvia('SOB', 0)` — busca sobras nao identificadas |

### Campos Inferidos vs Reais

| Inferido | Status Real |
|----------|-------------|
| Status (aguardando/enviada/resolvido) | **NAO como campo visivel** — filtro "Sem instrucao S/N" indica se tem ou nao instrucao |
| Dias pendente | **NAO como campo** — periodo de datas serve este proposito |
| Tipo de instrucao (reagendar/devolver/descartar) | **NAO EXISTE** — instrucao e acao dentro do resultado da pesquisa, nao tipo pre-cadastrado |
| Data prevista resolucao | **NAO EXISTE** na tela de filtros |
| Notificacao automatica | **NAO VERIFICAVEL** na tela — pode existir internamente |
| Relatorio tempo medio resolucao | **SIM** — exportacao para Excel (opcoes E e X no campo t_vid_rel) permite analise |

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
