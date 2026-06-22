---
name: reclassificando-amls-odoo
description: >-
  Skill WRITE (átomo) para RECLASSIFICAR em lote account.move.line de uma
  conta contábil para outra no Odoo (conta_origem -> conta_destino), por
  período/company/journal, preservando a chave fiscal via ciclo button_draft
  -> write account_id -> action_post por move. Usar quando o pedido é
  "reclassifica a conta X para a Y em setembro", "move os lançamentos da
  26784 pra 26844 na company 4", "troca a conta contábil desses débitos em
  lote". `--dry-run` é o DEFAULT (mostra plano + N moves/linhas/total);
  só efetiva com `--confirmar` + `--user-id`. NAO usar para apenas medir/
  validar/monitorar (não escreve) -> auditando-reclassificacao-odoo; nem para
  exportar razão geral -> razao-geral-odoo. Matriz USAR/NAO-USAR no corpo.
allowed-tools: Read, Bash, Glob, Grep
---

# reclassificando-amls-odoo (WRITE — átomo account.move.line)

## Indice
- [Quando usar / Quando NÃO usar](#quando-usar--quando-não-usar)
- [REGRAS CRÍTICAS](#regras-críticas)
- [Contrato (átomo)](#contrato-átomo)
- [Receitas](#receitas-caso-real---args)
- [Exemplos](#exemplos)
- [Armadilhas](#armadilhas)
- [Pendência (revisão dev)](#pendência-revisão-dev--não-resolvida-pela-skill)

Átomo de **reclassificação contábil em lote**: troca o `account_id` de
`account.move.line` da `conta_origem` para a `conta_destino`, num
período/company/journal, **preservando a chave fiscal**. Irmã **WRITE** da
READ-only `auditando-reclassificacao-odoo` (que só mede/valida/monitora). Reusa
o **mesmo domínio de busca** e o **CONTADOR REAL** (`validar_lote`) da READ —
NUNCA reimplementa contagem. Constituição: `app/odoo/estoque/CLAUDE.md`. Service:
`app/odoo/estoque/scripts/reclassificacao.py`.

## Quando usar / Quando NÃO usar

**USAR QUANDO** o pedido é trocar a conta contábil de lançamentos em lote:
"reclassifica a conta X para a Y em setembro", "move os débitos da 26784 pra
26844 na company 4 journal 845".

**NÃO USAR PARA:**

| Tarefa | Skill correta |
|--------|---------------|
| Medir / validar lote / monitorar (não escreve) | `auditando-reclassificacao-odoo` (READ) |
| Exportar razão geral / balancete | `razao-geral-odoo` |
| Rastrear UM lançamento/NF/PO | `rastreando-odoo` |
| Pagamento / reconciliação / baixa de título | `executando-odoo-financeiro` |
| Ajustar saldo de estoque (stock.quant) | `ajustando-quant-odoo` |

## REGRAS CRÍTICAS
1. **`--dry-run` é o DEFAULT** (exit 4). Apresente o plano (conta origem->destino,
   período, company, journal, N moves + N linhas + total_débito + skip_sefaz)
   antes de `--confirmar`.
2. **`--user-id` OBRIGATÓRIO**, validado contra `usuarios`. Propaga `executado_por`
   p/ o hook `operacao_odoo_auditoria` (button_draft/write/action_post na whitelist
   `app/utils/odoo_audit_helpers.py`).
3. **GUARD SEFAZ inviolável.** Move com `l10n_br_situacao_nf` in (`autorizado`,
   `excecao_autorizado`, `enviado`) NÃO entra no plano (status
   `SKIP_GUARD_SITUACAO_NF`) — `button_draft` invalidaria a chave fiscal. Vai p/
   `skip_sefaz`.
4. **Ciclo por move posted:** `button_draft` -> `write account_id=destino` (SÓ as
   linhas da conta_origem) -> `action_post`. NUNCA write direto em posted.
5. **INVARIANTE pós action_post:** re-lê `state`; se != `posted`, **FALHA e PARA o
   batch** (não deixa rascunho no razão).
6. **Reclassifica SÓ as linhas na conta_origem** — nunca as demais do move.
7. **CONTADOR REAL pós-write:** `validar_lote` da READ exige `integro==True` +
   `processadas==total` + `moves_draft==0`; senão `EXECUTADO_PARCIAL` expondo
   divergentes/ausentes/pendentes/moves_draft.
8. **Verificar no Odoo** após efetivar — operação viva.

## Contrato (átomo)
```
objeto:        account.move.line
input:         --conta-origem --conta-destino --data-inicio --data-fim
               [--company-id 4] [--journal-id 845] [--batch N] --user-id (OBRIG)
               [--confirmar] [--json]
output (JSON): {modo, user_id, executado_por, plano{conta_origem, conta_destino,
               company_id, journal_id, periodo, n_moves, n_linhas, total_debito,
               skip_sefaz[]}, resultado{status, moves_processados, linhas_escritas},
               validacao?{integro, processadas, pendentes, divergentes, ausentes,
               moves_draft, total_esperado}}
pré-condições: contas existem; moves state=posted no período; move NÃO em
               situacao_nf SEFAZ (senão skip_sefaz)
pós-condições: linhas da conta_origem migradas; moves re-postados; auditoria por
               button_draft/write/action_post
gotchas-invariante (no service reclassificacao.py):
  - GUARD SEFAZ (l10n_br_situacao_nf) — espelha _invoice_helpers.py:237-310,400-438
  - ciclo button_draft->write->action_post por move (nunca write em posted)
  - INVARIANTE pós-post: state != posted -> FALHA_POST_NAO_POSTED + PARA batch
  - SÓ linhas conta_origem (account_id [id,nome] via _acc_id)
  - CONTADOR REAL via validar_lote (salvaguarda da READ — não reimplementa)
modos:         --dry-run (default, exit 4) -> --confirmar (exit 0)
status:        DRY_RUN_OK · EXECUTADO · EXECUTADO_PARCIAL · FALHA_POST_NAO_POSTED ·
               FALHA_ODOO · FALHA_AUTORIZACAO
```

## Receitas (caso real -> args)
| Preciso de... | Args |
|---------------|------|
| Preview 26784->26844 (company 4, setembro) | `--conta-origem 26784 --conta-destino 26844 --data-inicio 2025-09-01 --data-fim 2025-09-30 --company-id 4 --user-id 74` |
| Efetivar a reclassificação acima | `... --confirmar` |
| Efetivar em lotes de 50 moves (retomável) | `... --batch 50 --confirmar` |
| Journal != 845 | `... --journal-id 900 --user-id 74` |

## Exemplos
```bash
SK=.claude/skills/reclassificando-amls-odoo/scripts/reclassificar_amls.py
# dry-run (default): preview 26784 -> 26844, company 4, journal 845
python "$SK" --conta-origem 26784 --conta-destino 26844 \
    --data-inicio 2025-09-01 --data-fim 2025-09-30 --company-id 4 --user-id 74
# efetivar (após revisar o plano + skip_sefaz)
python "$SK" --conta-origem 26784 --conta-destino 26844 \
    --data-inicio 2025-09-01 --data-fim 2025-09-30 --company-id 4 --user-id 74 --confirmar
```

## Armadilhas
- **`--user-id` ausente** = SystemExit argparse (exit 2). Usuário inexistente =
  `FALHA_AUTORIZACAO` (exit 1).
- **Move SEFAZ-autorizado** nunca é tocado (`skip_sefaz`); reclassificar conta de
  NF autorizada exige cancelar/recriar a NF (fora do escopo).
- **`EXECUTADO_PARCIAL`** (exit 1): write rodou mas validação pós achou
  pendentes/divergentes/ausentes/draft — investigue com a READ antes de re-rodar.
- **`--batch N`** processa só os N primeiros moves; re-rode p/ continuar
  (idempotente — moves migrados saem da conta_origem e não reentram).

## Pendência (revisão dev — NÃO resolvida pela skill)
- **Validar contra 1 move REAL da conta 26784 (company 4) no Odoo ANTES de
  `--confirmar` valer em prod** — confirmar COMO o ad-hoc do cluster 4 escreveu sem
  invalidar a chave fiscal (provável `move_type=entry`, sem NF SEFAZ). O guard SEFAZ
  é defensivo (testado só com FakeOdoo); a 1ª execução real = 1 move dry-run +
  inspeção direta no Odoo.
