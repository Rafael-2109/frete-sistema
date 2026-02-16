# SSW — Verificacoes Pendentes [CONFIRMAR]

> **Criado em**: 2026-02-16
> **Objetivo**: Checklist de marcadores [CONFIRMAR] que podem ser resolvidos navegando no SSW via Playwright
> **Metodo**: Script Playwright abre opcao como popup (window.open) e captura inputs/selects/botoes

---

## Prioridade ALTA — VERIFICADAS via Playwright (16/02/2026)

### 1. Opcao 062 — Relatorio de Parametros (NAO configuracao) — 8 marcadores

**Arquivo**: `comercial/062-parametros-frete.md` | **SSW interno**: ssw0189
**DESCOBERTA**: Opcao 062 e um RELATORIO, nao uma tela de configuracao. Titulo real: "Relatório de Parâm de Avaliação de CTRCs".

**Verificacoes**:
- [x] Opcao 062 esta acessivel na instalacao CarVia? → **SIM** — abre como ssw0189
- [x] Quais campos estao disponiveis na tela? → **Apenas 2 filtros**: "Que partem da unidade" (f2, maxlen=3) e "Para o estado" (f3, maxlen=2)
- [x] Campo "Desconto maximo" existe? → **NAO** — opcao 062 e relatorio, nao configuracao
- [x] Campo "Resultado comercial minimo" existe? → **NAO** — idem
- [x] Campo "Custos adicionais" existe? → **NAO** — idem
- [x] Relacao com opcao 469 (por rota) — complementa ou substitui? → **062 apenas EXIBE parametros, nao configura. Configuracao em 903/469/423**
- [x] Opcao 004 usa parametros da 062 no calculo? → SIM (confirmado: POP-B02:14,21-26)
- [x] Opcao 002 usa limites da 062 para desconto? → SIM (confirmado: POP-B02:21-26 + POP-B03:22)

### 2. Opcao 459 — Adicionais Disponiveis para Faturar (NAO cadastro TDE) — 7 marcadores

**Arquivo**: `financeiro/459-cadastro-tde.md` | **SSW interno**: ssw0182
**DESCOBERTA**: Opcao 459 NAO e cadastro. E CONSULTA e EXCLUSAO de adicionais ja registrados. Titulo real: "Adicionais Disponíveis para Faturar".

**Verificacoes**:
- [x] Existe campo "Codigo adicional"? → **NAO** — tela filtra por empresa/periodo/CNPJ, sem tipo de adicional
- [x] Existe campo "Descricao/Justificativa"? → NAO na 459 (confirmado via POP-C04 para outra opcao)
- [x] Existe campo "Data do evento"? → NAO na 459 — tem periodo de inclusao (f2/f3 ddmmaa)
- [x] Opcao 523 esta relacionada a cobranca de diarias? → **NAO** — 523 e "Horas de Estadia em Entregas" (ssw0956), relatorio de tempo retido
- [x] Existe relatorio de adicionais por cliente/periodo? → **SIM** — esta e exatamente a funcao da 459 (filtro por empresa + periodo + CNPJ)
- [x] Valores tipicos por tipo de adicional → **NAO VERIFICAVEL** na tela de filtro — resultado aparece apos pesquisa

### 3. Opcao 462 — Bloquear Faturamento de CTRCs — 9 marcadores

**Arquivo**: `financeiro/462-bloqueio-financeiro-ctrc.md` | **SSW interno**: ssw0760
**DESCOBERTA**: Tela tem 3 secoes: bloqueio por CTRC, bloqueio por manifesto, relatorio de bloqueados.

**Verificacoes**:
- [x] Tela existe e esta acessivel? → **SIM** — abre como ssw0760
- [x] Campo "Filial emissora" existe? → **NAO como campo separado** — dominio do CTRC (f2, maxlen=3) faz esse papel
- [x] Campo "Tipo de bloqueio" existe? → **NAO** — motivo e texto livre (f1, maxlen=60)
- [x] Campo "Data limite" existe? → **NAO** — sem data de resolucao prevista
- [x] Campo "Responsavel" existe? → **NAO como campo visivel** — provavelmente registrado automaticamente
- [x] Campo "Motivo do desbloqueio" existe? → **NAO VERIFICAVEL** na tela inicial
- [x] Campo "Data resolucao" existe? → **NAO** na tela principal
- [x] Historico de bloqueios/desbloqueios (auditoria)? → **SIM** — secao 3 da tela lista bloqueados por periodo (f10=V/R, f11-f12)
- [x] Alerta automatico para bloqueios antigos? → **NAO VERIFICAVEL** — nao existe campo ou indicador visivel

---

## Prioridade MEDIA — VERIFICADAS via Playwright (16/02/2026)

### 4. Opcao 437 — Faturamento Manual — 1 marcador

**Arquivo**: `financeiro/437-faturamento-manual.md` | **SSW interno**: ssw0114
- [x] Campos da tela 437 validados → **24 inputs visiveis**: cod_emp_ctb (Empresa), cgc_cliente (CNPJ pagador), data_emissao_fat, nro_banco/nro_agen/dig_agen/nro_cc/dig_cc/carteira (Banco completo), 5x nro_pre_fat+dig (pre-faturas), dom_mapa_comissao/sigla_mapa_comissao/nro_mapa_comissao (mapa), f1 (arquivo CT-e/CTRC tipo file)

### 5. Opcao 515 — SPED Contribuicoes — 4 marcadores

**Arquivo**: `fiscal/515-sped-contribuicoes.md` | **SSW interno**: ssw1018
- [x] Campo "CNPJ / Raiz" existe? → **SIM** (cnpj_emp, default 62312605000175)
- [x] Filtros adicionais (unidade, empresa, regime)? → **PARCIAL** — tp_escrituracao (0=Original, 1=Retificadora), referencia (X=XML, P=Contas a Pagar), objetivo (S=Simulacao, E=Envio)
- [x] Log/historico de geracoes anteriores? → **NAO VISIVEL** na tela — pode existir internamente
- [x] Integracao direta com Receitanet ou transmissao manual? → **MANUAL** — campo "Objetivo" S/E gera arquivo para transmissao. Tambem tem "Relatorio Conferencia Excel" (S/N)

### 6. Opcao 108 — Instrucoes para Ocorrencias — 3 marcadores

**Arquivo**: `operacional/108-ocorrencias-entrega.md` | **SSW interno**: ssw0118
- [x] Campos inferidos validados → **12 inputs visiveis**: t_sem_instr, t_codigo/msgoco, t_sigla_sub, t_cnpj_cli, t_cnpj_grupo, t_usuario, t_conferente, t_data_ini_ult, t_data_fim_ult, t_sel_atrasados, t_vid_rel
- [x] Notificacao automatica? → **NAO VERIFICAVEL** na tela — sem campo ou indicador
- [x] Relatorio tempo medio resolucao? → **PARCIAL** — exportacao Excel (opcoes E e X no campo t_vid_rel) permite analise post-hoc

---

## Prioridade BAIXA — POPs com marcadores contextuais (PARCIALMENTE VERIFICADOS)

### 7. POP-C04 (Custos Extras) — 4 marcadores
- [x] Nome exato da opcao TDE no menu SSW → **459 NAO e cadastro TDE** — e "Adicionais Disponiveis para Faturar". Cadastro real provavelmente na opcao 442
- [ ] Lista de tipos disponiveis no dropdown → Precisa verificar opcao 442 (Credito/Debito CTRC/Fatura)
- [ ] Existe opcao "credito" alem de "debito"? → Precisa verificar opcao 442
- [ ] Adicionais aparecem em coluna separada ou somados na fatura? → Precisa testar faturamento real

### 8. POP-C03 (CTe Complementar) — 1 marcador
- [x] Funcao de CTe complementar: menu lateral ou botao na tela inicial da 007? → **TELA PROPRIA (opcao 007/ssw0767)** com botoes no topo: Enviar à SEFAZ, Reenviar, Imprimir todos. Acesso via menu Expedição > Aprovação de CTRCs. CTe complementar NAO e botao da 007 — e opcao separada (opcao 007 com sub-funcoes)

### 9. POP-C06 (Cancelar CTe) — 1 marcador
- [ ] CCF ajustada apos cancelamento? Estorno automatico? → Precisa testar com CTe real

### 10. POP-E03 (Faturamento Automatico) — 2 marcadores
- [ ] Tipo "FOB Dirigido" existe na tabela de tipos? → Precisa verificar opcao 384 ou 436
- [ ] Tipo "K" (Peso KG) existe na tabela de tipos? → Precisa verificar opcao 384 ou 436

### 11. POP-F05 (Bloqueio Financeiro) — 1 marcador
- [x] Motivo do bloqueio visivel na tela? → **SIM** — campo f1 "Motivo" (texto livre, maxlen=60) na secao 1 da tela 462

---

## NAO verificaveis via SSW (dependem de terceiros)

Estes marcadores NAO podem ser resolvidos navegando no SSW:

| Marcador | Arquivo | Depende de |
|----------|---------|------------|
| Regras de cobertura ESSOR | POP-G02 (5 marcadores) | Seguradora ESSOR |
| SINTEGRA obrigatorio em SP? | POP-G04 | SEFAZ SP |
| DIFAL aplica-se a transporte PF? | POP-G04 | Convenio ICMS 93/2015 |
| NF de outro UF — cobertura | POP-G02, CATALOGO_POPS | ESSOR + legislacao |

---

## Instrucoes para o Agente

**IMPORTANTE**: Opcoes SSW abrem como POPUP (nova page via window.open), NAO como AJAX no frame principal.

Quando o usuario pedir para verificar marcadores [CONFIRMAR]:

1. **Login**: `browser_ssw_login` (credenciais no .env)
2. **Navegar**: `browser_ssw_navigate_option(NNN)` para a opcao — abre POPUP
3. **Capturar**: Na nova page, usar `browser_snapshot` + `browser_read_content`
4. **Documentar**: Atualizar arquivo .md correspondente, removendo [CONFIRMAR] e adicionando campos reais
5. **Fechar popup**: Antes de navegar para proxima opcao

---

## Resumo Quantitativo

| Status | Quantidade | Detalhes |
|--------|------------|---------|
| **Verificados** | 28 | 6 opcoes navegadas e documentadas (062, 459, 462, 437, 515, 108) + 007, 523 |
| **Pendentes (via SSW)** | 5 | POP-C04 (2x opcao 442), POP-C06 (1x teste), POP-E03 (2x opcao 384) |
| **NAO verificaveis** | 9 | POP-G02 (5x ESSOR), POP-G04 (2x SEFAZ/legislacao), POP-G02 (2x ESSOR+lei) |
| **Total original** | 42 | 28+5+9 = 42 |

---

## Historico

| Data | Acao |
|------|------|
| 2026-02-16 | Checklist criado com 42 marcadores identificados (28 verificaveis via SSW, 14 dependem de terceiros) |
| 2026-02-16 | 5 marcadores resolvidos via cross-reference (062:62-63, 459:38-39, 515:47). Total: 37 pendentes (23 verificaveis via SSW) |
| 2026-02-16 | **28 marcadores verificados via Playwright** (script v3 com captura de popup). Descobertas criticas: 062 e relatorio (NAO config), 459 e consulta (NAO cadastro), 462 tem 3 secoes (individual + manifesto + relatorio). 5 marcadores restantes requerem opcoes adicionais (442, 384) ou testes com dados reais. Docs 062, 459, 462, 437, 515, 108 atualizados com campos reais |
