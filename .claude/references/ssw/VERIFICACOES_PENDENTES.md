# SSW — Verificacoes Pendentes [CONFIRMAR]

> **Criado em**: 2026-02-16
> **Objetivo**: Checklist de marcadores [CONFIRMAR] que podem ser resolvidos navegando no SSW via Playwright
> **Metodo**: browser_ssw_login + browser_ssw_navigate_option(NNN) + browser_read_content / browser_snapshot

---

## Prioridade ALTA — Opcoes desconhecidas pela CarVia

### 1. Opcao 062 — Parametros de Frete (8 marcadores)

**Arquivo**: `comercial/062-parametros-frete.md`
**POPs afetados**: B02 (formacao preco), B03 (parametros frete)
**Impacto**: PEND-07 — pode ser causa de calculos de frete incorretos

**Verificar no SSW**:
- [ ] Opcao 062 esta acessivel na instalacao CarVia?
- [ ] Quais campos estao disponiveis na tela?
- [ ] Campo "Desconto maximo" existe? Qual valor atual?
- [ ] Campo "Resultado comercial minimo" existe? Qual valor atual?
- [ ] Campo "Custos adicionais" existe? Quais opcoes?
- [ ] Relacao com opcao 469 (por rota) — complementa ou substitui?
- [x] Opcao 004 usa parametros da 062 no calculo? → SIM (confirmado: POP-B02:14,21-26)
- [x] Opcao 002 usa limites da 062 para desconto? → SIM (confirmado: POP-B02:21-26 + POP-B03:22)

**Como verificar**: `browser_ssw_navigate_option(62)` → `browser_snapshot` → documentar campos

### 2. Opcao 459 — Cadastro de TDE (7 marcadores)

**Arquivo**: `financeiro/459-cadastro-tde.md`
**POPs afetados**: C04 (custos extras), E02 (faturamento manual)
**Impacto**: PEND-07 adjacente — nao sabe onde cadastrar TDE/diaria

**Verificar no SSW**:
- [ ] Existe campo "Codigo adicional"? Quais tipos pre-cadastrados (TDE, diaria, pernoite)?
- [x] Existe campo "Descricao/Justificativa"? → SIM (confirmado: POP-C04:75 — "Justificativa (texto curto)")
- [x] Existe campo "Data do evento"? → SIM (confirmado: POP-C04:61-62)
- [ ] Opcao 523 esta relacionada a cobranca de diarias?
- [ ] Existe relatorio de adicionais por cliente/periodo?
- [ ] Valores tipicos por tipo de adicional

**Como verificar**: `browser_ssw_navigate_option(459)` → `browser_snapshot` → documentar campos

### 3. Opcao 462 — Bloqueio Financeiro CTRC (9 marcadores)

**Arquivo**: `financeiro/462-bloqueio-financeiro-ctrc.md`
**POPs afetados**: F05 (bloqueio financeiro)
**Nota**: NAO tem documentacao de ajuda SSW dedicada

**Verificar no SSW**:
- [ ] Tela existe e esta acessivel?
- [ ] Campo "Filial emissora" existe?
- [ ] Campo "Tipo de bloqueio" existe? (operacional, comercial, fiscal?)
- [ ] Campo "Data limite" existe?
- [ ] Campo "Responsavel" existe?
- [ ] Campo "Motivo do desbloqueio" existe?
- [ ] Campo "Data resolucao" existe?
- [ ] Historico de bloqueios/desbloqueios (auditoria)?
- [ ] Alerta automatico para bloqueios antigos (>30 dias)?

**Como verificar**: `browser_ssw_navigate_option(462)` → `browser_snapshot` → documentar campos

---

## Prioridade MEDIA — Complementar documentacao existente

### 4. Opcao 437 — Faturamento Manual (1 marcador)

**Arquivo**: `financeiro/437-faturamento-manual.md`
**POPs afetados**: E02

**Verificar no SSW**:
- [ ] Campos da tela 437 — validar contra inferencias do POP-E02 e opcao 436

### 5. Opcao 515 — SPED Contribuicoes (4 marcadores)

**Arquivo**: `fiscal/515-sped-contribuicoes.md`
**POPs afetados**: G04

**Verificar no SSW**:
- [x] Campo "CNPJ / Raiz" existe? → SIM, diferenciado da 512 (confirmado: proprio doc 515:11-21)
- [ ] Filtros adicionais (unidade, empresa, regime)?
- [ ] Log/historico de geracoes anteriores?
- [ ] Integracao direta com Receitanet ou transmissao manual?

### 6. Opcao 108 — Ocorrencias de Entrega (3 marcadores)

**Arquivo**: `operacional/108-ocorrencias-entrega.md`
**POPs afetados**: D06

**Verificar no SSW**:
- [ ] Campos inferidos do POP-D06 — validar no ambiente real
- [ ] Notificacao automatica quando instrucao e registrada?
- [ ] Relatorio de tempo medio de resolucao por tipo?

---

## Prioridade BAIXA — POPs com marcadores contextuais

### 7. POP-C04 (Custos Extras) — 4 marcadores
- [ ] Nome exato da opcao TDE no menu SSW
- [ ] Lista de tipos disponiveis no dropdown
- [ ] Existe opcao "credito" alem de "debito"?
- [ ] Adicionais aparecem em coluna separada ou somados na fatura?

### 8. POP-C03 (CTe Complementar) — 1 marcador
- [ ] Funcao de CTe complementar: menu lateral ou botao na tela inicial da 007?

### 9. POP-C06 (Cancelar CTe) — 1 marcador
- [ ] CCF ajustada apos cancelamento? Estorno automatico?

### 10. POP-E03 (Faturamento Automatico) — 2 marcadores
- [ ] Tipo "FOB Dirigido" existe na tabela de tipos?
- [ ] Tipo "K" (Peso KG) existe na tabela de tipos?

### 11. POP-F05 (Bloqueio Financeiro) — 1 marcador
- [ ] Motivo do bloqueio visivel na tela?

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

Quando o usuario pedir para verificar marcadores [CONFIRMAR]:

1. **Login**: `browser_ssw_login` (credenciais no .env)
2. **Navegar**: `browser_ssw_navigate_option(NNN)` para a opcao
3. **Capturar**: `browser_snapshot` + `browser_read_content`
4. **Identificar frames**: `browser_switch_frame(list_frames=true)` se snapshot vazio
5. **Documentar**: Atualizar arquivo .md correspondente, removendo [CONFIRMAR] e adicionando campos reais
6. **Priorizar**: Comecar pela opcao 062 (maior impacto no negocio)

---

## Historico

| Data | Acao |
|------|------|
| 2026-02-16 | Checklist criado com 42 marcadores identificados (28 verificaveis via SSW, 14 dependem de terceiros) |
| 2026-02-16 | 5 marcadores resolvidos via cross-reference (062:62-63, 459:38-39, 515:47). Total: 37 pendentes (23 verificaveis via SSW) |
