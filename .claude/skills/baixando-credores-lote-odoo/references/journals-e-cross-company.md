<!-- doc:meta
tipo: reference
camada: L3
sot_de: mecanica Odoo do par SICOOB+DESAGIO e cross-company da skill baixando-credores-lote-odoo
hub: .claude/skills/baixando-credores-lote-odoo/SKILL.md
superseded_by: —
atualizado: 2026-06-18
-->
# Journals, companies e cross-company — par SICOOB + DESAGIO

> **Papel:** referencia de mecanica Odoo da skill `baixando-credores-lote-odoo`.
> Fatos validados AO VIVO no Odoo de producao em 2026-06-18 (READ-only).

## Journals por company (validado ao vivo)

| Company | id | SICOOB (bank) | DESAGIO (cash) |
|---------|----|---------------|----------------|
| FB | 1 | **10** (code SIC) | **1025** (code DESAG) |
| LF | 5 | **386** (code SIC) | **— NAO EXISTE** |
| SC | 3 | — (sem journal bancario) | — |
| CD | 4 | — (sem journal bancario) | — |

- O par completo **SICOOB + DESAGIO so e estruturalmente possivel na FB**. Em LF ha
  SICOOB (386) mas nao ha journal DESAGIO -> `desagio>0` em LF = `BLOQUEADO_SEM_JOURNAL_DESAGIO`;
  `desagio==0` lanca so o SICOOB.
- FB tem outros journals "SIC*" (SIC1 cartao 1032, SICAP aplicacao 1076) — NAO confundir:
  o SICOOB operacional e' `code == 'SIC' AND name == 'SICOOB' AND type == 'bank'`.
- A skill **resolve os journals AO VIVO** por company (`search_read account.journal`), com
  fallback para `constants.JOURNAL_SICOOB_POR_COMPANY` / `JOURNAL_DESAGIO_ID`. Fonte canonica:
  `app/financeiro/constants.py` (NAO usar `EMPRESA_MAP`, divergente).

## Companies REAIS (NAO usar EMPRESA_MAP)
`COMPANY_IDS_ODOO = {'FB':1, 'SC':3, 'CD':4, 'LF':5}`. `COMPANIES_SEM_JOURNAL_BANCARIO = {3,4}`.

## `name` de fatura COLIDE entre companies
A numeracao de `account.move.name` (ex `COM2/2026/06/0020`) **se repete entre companies** —
o mesmo numero existe em FB, CD e LF com partners diferentes. Logo:
- buscar so por `name` retorna mais de uma fatura (uma por company) -> a coluna **EMPRESA** da planilha desambigua;
- a **company efetiva vem da fatura resolvida** (autoridade — gotcha O8), nunca do texto da planilha;
- sem EMPRESA quando ha colisao -> `BLOQUEADO_AMBIGUO` (operador resolve).

Prefixos observados: `CMPMP` (compra materia-prima, journal 11 FB), `CMPUC`, `COM2`,
`ENTSI` (entrada servico industrializacao), `COM` etc. — sempre `PREFIXO/AAAA/MM/NNNN`.

## Linha payable
- `account.move.line` com `account_type == 'liability_payable'`, `reconciled == False`.
- Conta tipica: **11038 FORNECEDORES NACIONAIS** (FB). `credit > 0`, `name` geralmente vazio.
- `amount_residual` e' **NEGATIVO** (gotcha O3) -> usar `abs()`.
- **Faturas parceladas** tem N linhas payable abertas; o residual em aberto e' a SOMA.

## Cross-company (Fase 2 — NAO implementado)
SC(3)/CD(4) nao tem journal bancario proprio. Pagar exige cross-company via conta-ponte
**PENDENTES 26868** (existe em todas as companies, reconciliavel). Mecanismo **comprovado para
RECEBER** (NF 142211) mas **nao comprovado para PAGAR** com este par — fontes se contradizem.
Ate validar 1 pagamento real cross-company + dry-run ao vivo: `BLOQUEADO_CROSS_COMPANY` (manual).
Conta juros pagamento por company: `{1:22769, 3:24051, 4:25335, 5:26619}`.

## Gotchas de WRITE (relevantes ao 1b, nao ao preview)
- `reconcile()` retorna `None` -> XML-RPC levanta "cannot marshal None" = **SUCESSO** (O6); NAO repetir.
- `action_post()` idem. Reconciliacao do extrato exige TRANSITORIA 22199 -> PENDENTES 26868 (O1)
  e `account_id` como ULTIMO write antes de `action_post` (O12).
- Reuso obrigatorio: `BaixaPagamentosService` (`criar_pagamento_outbound`, `postar_pagamento`,
  `buscar_linhas_payment`, `reconciliar`) — nao reinventar.

## Fontes
- FONTE: pre-flight Odoo PROD ao vivo 2026-06-18 (READ-only) — journals SICOOB/DESAGIO por company,
  estrutura da linha payable (`account_type`, sinal de `amount_residual`), colisao de `name` entre
  companies e contagem de `in_invoice` por company.
- FONTE: `app/financeiro/constants.py` (`JOURNAL_SICOOB_POR_COMPANY`, `JOURNAL_DESAGIO_ID`,
  `COMPANY_IDS_ODOO`, `COMPANIES_SEM_JOURNAL_BANCARIO`).
- FONTE: `app/financeiro/CLAUDE.md` / `GOTCHAS.md` (gotchas O1/O3/O6/O8/O11/O12).
