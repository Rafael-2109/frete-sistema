---
name: baixando-credores-lote-odoo
description: >-
  Skill de baixa de pagamentos em lote (contas a pagar) no Odoo a partir de uma
  planilha de credores: para cada fatura de compra (coluna FT REF) calcula o par
  account.payment SICOOB (parcela) + DESAGIO (desagio) por vencimento. Usar quando
  o pedido e "baixa os credores da planilha", "processa a planilha de pagamentos
  SICOOB/DESAGIO", "paga os credores em lote", "gera o plano de baixa de
  fornecedores da planilha". HOJE so faz PREVIEW (READ-only, dry-run, zero escrita):
  localiza a fatura, valida saldo/company/partner/journals e devolve relatorio +
  planilha anotada com o plano. O WRITE real (criar/postar/reconciliar) e Fase 1b,
  ainda NAO implementado. Escopo FB(1)/LF(5); SC(3)/CD(4) = BLOQUEADO_CROSS_COMPANY.
  NAO usar para baixa por EXTRATO bancario (-> executando-odoo-financeiro), nem para
  contas a RECEBER (-> baixa de titulos). Matriz USAR/NAO-USAR no corpo.
allowed-tools: Read, Bash, Glob, Grep
---

# baixando-credores-lote-odoo (pagamentos em lote payable)

A partir de uma **planilha de credores**, baixa contas a pagar no Odoo criando, por
data de vencimento, um par `account.payment` outbound/supplier — **SICOOB** (valor da
parcela, journal bancario) + **DESAGIO** (valor do desagio, journal cash 1025) —
reconciliado contra a linha payable da fatura de compra (coluna **FT REF** = `name`).

> **Estado (2026-06-18): so o PREVIEW (passo 1a) esta implementado.** READ-only,
> dry-run, **zero escrita no Odoo**. O WRITE (1b), o `reverter_baixa.py` (1c) e a
> Fase 2 cross-company (1e) ainda NAO existem. Design completo: `DESIGN.md`.

Service: `app/financeiro/services/baixa_credores_lote_service.py`.
Reference de mecanica: `references/journals-e-cross-company.md`.

## Quando usar / Quando NAO usar

**USAR QUANDO** o pedido envolve baixar credores de uma planilha pelo par SICOOB+DESAGIO:
- "baixa os credores da planilha", "processa a planilha de pagamentos SICOOB/DESAGIO",
  "gera o plano de baixa dos fornecedores", "paga em lote os credores da planilha".

**NAO USAR PARA:**
- baixa de pagamento a partir do **EXTRATO bancario** (matching extrato x titulo) ->
  `executando-odoo-financeiro` (usa `BaixaPagamentosService` por extrato).
- contas a **RECEBER** / baixa de titulos de cliente -> fluxo `baixas.py` (A7 do modulo).
- so **consultar/rastrear** uma NF/pagamento -> `rastreando-odoo`.
- **efetivar** o pagamento agora -> ainda nao implementado (1b); esta skill so faz preview.

## REGRAS CRITICAS
1. **PREVIEW e' READ-only.** Nada escreve no Odoo. `--confirmar` e' **recusado** de proposito
   (exit 2) ate o passo 1b existir — evita falsa sensacao de pagamento.
2. **Company vem da FATURA, nao da planilha** (gotcha O8). A coluna EMPRESA so' desambigua
   *qual* fatura quando o `name` colide entre companies.
3. **Escopo FB(1)/LF(5).** SC(3)/CD(4) nao tem journal bancario -> `BLOQUEADO_CROSS_COMPANY`
   (Fase 2 — pagamento cross-company via conta-ponte, ainda nao automatizado).
4. **DESAGIO so existe na FB.** Em LF ha SICOOB mas nao ha journal DESAGIO: desagio>0 em LF
   = `BLOQUEADO_SEM_JOURNAL_DESAGIO`; desagio==0 em LF lanca so o SICOOB.
5. **Sempre revisar o relatorio e a planilha anotada** antes de qualquer execucao futura.
   Nunca tratar `DRY_RUN_OK` como "pago".

## Contrato CLI (`scripts/processar_baixas.py`, PREVIEW = default)
```
--planilha PATH         (obrigatorio)         --saida PATH      (default <planilha>_PROCESSADO.xlsx)
--sheet NOME            (default: aba ativa)  --credor TEXTO    (filtra por substring do credor)
--tolerancia-saldo F    (default 0.01)        --user-id INT     (auditoria; obrig. no 1b)
--quiet                 (silencia boot)       --confirmar       (1b — RECUSADO nesta versao)

Saida: relatorio JSON no stdout (resumo_por_status + detalhe por linha) +
       planilha anotada <planilha>_PROCESSADO.xlsx (copia; nunca destroi o original).
Exit:  4 preview OK (dry-run) · 1 erro (arquivo/conexao) · 2 uso / --confirmar recusado.
```

Colunas esperadas na planilha (mapeadas POR NOME, nunca por posicao): **CREDOR**,
**FT REF** (= `name` da fatura, ex CMPMP/2026/06/0119), **VALOR PARCELA**, **VALOR DESAGIO**,
**EMPRESA** (FB/LF/...), **REF PG SICOOB** (saida — preenchido = `JA_PROCESSADO`) e uma ou
mais colunas de **DATA** de vencimento (detectadas pelos valores; aceita cabecalho duplicado).

## Status por linha
```
DRY_RUN_OK                    pronto para WRITE (1b): fatura achada, saldo cobre, plano calculado
BLOQUEADO_SALDO               total dos pares > residual em aberto (+tolerancia)
BLOQUEADO_AMBIGUO             >1 fatura com o name em companies/partners distintos (preencha EMPRESA)
BLOQUEADO_CROSS_COMPANY       fatura em SC(3)/CD(4) — Fase 2
BLOQUEADO_NAO_ENCONTRADA      nenhuma in_invoice posted com esse name
BLOQUEADO_VALOR               desagio >= parcela (guard F2)
BLOQUEADO_SEM_JOURNAL_SICOOB  company sem journal SICOOB
BLOQUEADO_SEM_JOURNAL_DESAGIO desagio>0 em company sem journal DESAGIO (LF)
BLOQUEADO_SEM_PAYABLE         fatura sem linha payable aberta (liability_payable, reconciled=False)
PULADO_SEM_DADOS              linha sem ft_ref, sem datas ou sem valor de parcela
JA_PROCESSADO                 REF PG SICOOB ja preenchido (idempotencia soft)
```

## Exemplos
```bash
SK=.claude/skills/baixando-credores-lote-odoo/scripts/processar_baixas.py
# Preview de toda a planilha (READ-only) -> JSON + <planilha>_PROCESSADO.xlsx
python "$SK" --planilha /caminho/credores.xlsx --quiet
# Preview de um credor especifico
python "$SK" --planilha /caminho/credores.xlsx --credor "GALVACO" --quiet
# (1b ainda nao implementado) --confirmar e recusado com exit 2
python "$SK" --planilha /caminho/credores.xlsx --confirmar    # -> RECUSADO
```

## Armadilhas
- **`name` de fatura COLIDE entre companies.** "COM2/2026/06/0020" existe em FB, CD e LF.
  Sem a coluna EMPRESA, vira `BLOQUEADO_AMBIGUO`. Preencher EMPRESA resolve.
- **Faturas parceladas** tem N linhas payable abertas: o residual e' a SOMA delas; o mapeamento
  de cada par a uma parcela e' responsabilidade do WRITE (1b). O preview anota o aviso.
- **`amount_residual` payable e NEGATIVO** (O3) — comparado em `abs()`.
- **Aviso de partner** (`credor` planilha != partner da fatura) e' so' alerta, nao bloqueia
  (nomes podem diferir de sufixo). Conferir antes do WRITE.

## Roadmap (incremental — move dinheiro real; ver DESIGN.md)
- [x] **1a. Parser + PREVIEW** (READ, dry-run) — ESTA skill.
- [ ] **1b. WRITE FB/LF** reusando `BaixaPagamentosService` + 6 guards do pre-mortem + write-ahead.
- [ ] **1c. `reverter_baixa.py --lote-id`** (action_draft + unlink, dry-run default).
- [ ] **1d. Validacao ao vivo supervisionada** (1 credor FB pequeno).
- [ ] **1e. Fase 2 (SC/CD)** cross-company via conta-ponte PENDENTES 26868.
