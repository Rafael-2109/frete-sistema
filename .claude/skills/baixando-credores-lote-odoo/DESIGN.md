<!-- doc:meta
tipo: explanation
camada: L2
sot_de: skill baixando-credores-lote-odoo (pagamentos em lote payable Odoo)
hub: .claude/references/INDEX.md
superseded_by: —
atualizado: 2026-06-18
-->
# DESIGN — Skill `baixando-credores-lote-odoo` (pagamentos em lote no Odoo)

> **Papel:** spec de design da skill de pagamentos em lote payable no Odoo (demanda A da Martha).

## Contexto
Demanda A da Martha (financeiro) — a mais recorrente das 6 mapeadas (4 sessoes/mes). Este doc consolida
o design aprovado + a pesquisa de reconciliacao cross-company para guiar a implementacao do codigo.

> **Status: passo 1a (PREVIEW READ-only) IMPLEMENTADO em 2026-06-18** (service
> `baixa_credores_lote_service.py` + `processar_baixas.py` + SKILL.md + reference + 21 testes
> + smoke test ao vivo). WRITE (1b) e demais passos pendentes — ver Roadmap.
> Origem: demanda A da Martha (financeiro), a mais recorrente das 6 mapeadas (4 sessões/mês).
>
> **Descobertas ao vivo (2026-06-18) que refinaram o design:**
> - O `name` da fatura **COLIDE entre companies** (mesmo `COM2/2026/06/NNNN` em FB/CD/LF). O lookup
>   por `name` retorna várias → a coluna **EMPRESA** da planilha desambigua (company efetiva ainda
>   vem da fatura, O8). Sem EMPRESA na colisão → `BLOQUEADO_AMBIGUO`.
> - Journal **DESÁGIO (1025) só existe na FB**. LF tem SICOOB (386) mas **não** DESÁGIO →
>   `desagio>0` em LF = `BLOQUEADO_SEM_JOURNAL_DESAGIO`; `desagio==0` em LF lança só o SICOOB.
> - Faturas parceladas têm **N linhas payable** abertas → residual = soma; mapear par↔parcela é tarefa do 1b.

## Objetivo
A partir de uma planilha de credores, criar **pagamentos em lote de contas a pagar** no Odoo:
para cada data de vencimento, um par `account.payment` outbound/supplier — **SICOOB** (valor parcela,
journal 10) + **DESÁGIO** (valor deságio, journal 1025) — postados e reconciliados contra a linha
payable do título da fatura (coluna FT REF), devolvendo a planilha com `REF PG SICOOB` preenchida com o
`name` PSIC + relatório.

## Escopo (decisão fundamentada — pré-flight Odoo 2026-06-18)
- **FB (company 1) e LF (5)** → têm journal bancário próprio. Caminho **same-company**, direto, comprovado. **Coberto.**
- **SC (3) e CD (4)** → **não têm NENHUM journal bancário** no Odoo. Pagar exige cross-company via
  conta-ponte PENDENTES **26868** — mecanismo comprovado para *receber* (NF 142211) mas **não para pagar**
  com este par, e o código de pagamento dá `ValueError` para SC/CD; as fontes se contradizem.
  → A skill marca **`BLOQUEADO_CROSS_COMPANY` (reconciliar manual)**. Automatizar SC/CD = **Fase 2**,
  só após inspecionar 1 pagamento real SC/CD + dry-run ao vivo. **NUNCA** criar payment com journal FB + company SC/CD (constraint Odoo: journal pertence a 1 company).

## Contrato CLI (`scripts/processar_baixas.py`, dry-run DEFAULT)
```
--planilha PATH            (obrigatorio)        --confirmar           (sem isso = PREVIEW; nada escreve)
--user-id INT              (obrig. p/ auditoria)--credor NOME         (opcional; default todos)
--saida PATH               (default <planilha>_PROCESSADO.xlsx)       --tolerancia-saldo 0.01
--confirmar-valor-total NNNNN.NN  (obrigatorio acima de limite — bate com o total calculado)
```

## Fluxo
1. Ler planilha (CREDOR, FT REF=CMPMP, VALOR PARCELA, VALOR DESÁGIO, DATAS 1..N, REF PG SICOOB=saída, empresa). Header dup `6/6.1` do pandas.
2. Localizar fatura por **`name`** (não `ref`): `search_read('account.move',[['name','=',CMPMP],['move_type','=','in_invoice']])` → **match único em `(name, company_id, partner_id)`**; >1 → `BLOQUEADO_AMBIGUO`.
3. Derivar company **da fatura** (não da planilha). Se company ∈ {3,4} → `BLOQUEADO_CROSS_COMPANY`.
4. Identificar a **linha payable aberta** (FORNECEDORES NACIONAIS, `reconciled=False`) — não o move `entry` residual 0.
5. **Guard de saldo**: `total=(parcela+desagio)*n_datas`; `abs(residual)+tol < total` → `BLOQUEADO_SALDO`, não cria nada.
6. (`--confirmar`) write-ahead `BaixaPagamentoItem` PENDENTE + `idempotency_key` no `ref` → criar par → postar → reconciliar → **pós-reconcile READ** (`residual==0`) → marcar CONFIRMADO.
7. Write-back **ancorado por CMPMP** via openpyxl ponta-a-ponta (nunca índice posicional) + validação de fechamento. Cópia `_PROCESSADO`, nunca destrói o original.

**Status:** `DRY_RUN_OK | EXECUTADO_OK | EXECUTADO_RESIDUAL | BLOQUEADO_SALDO | BLOQUEADO_AMBIGUO | BLOQUEADO_CROSS_COMPANY | PULADO_SEM_DADOS | JA_PROCESSADO`.

## Guards (do pré-mortem — não-negociáveis, "erro que parece sucesso")
1. **F4 pós-reconcile READ**: confirmar `reconciled==True` E `residual==0` antes de qualquer OK. "Não lançou exceção" ≠ prova.
2. **F2 valor**: asserção `deságio < parcela`; mapear colunas por NOME (nunca posição); preview lado-a-lado `SICOOB=Rx(j10) | DESÁGIO=Ry(j1025)`; `--confirmar-valor-total` acima de limite.
3. **F5 write-back**: ancorar por CMPMP, openpyxl ponta-a-ponta, validação de fechamento (cada PSIC = payment.name do CMPMP).
4. **F3 idempotência**: write-ahead PENDENTE + `idempotency_key` determinístico no `ref`; busca de existência por essa chave (não por partner+amount+date, que tem colisões legítimas).
5. **F1 lookup**: match único `(name, company_id, partner_id)`; company derivada ANTES do lookup.
6. **F7 rollback**: entregar `reverter_baixa.py --lote-id` JUNTO (action_draft+unlink, dry-run default).

## Mecânica Odoo / IDs / gotchas (pesquisa 2026-06-18)
- Journals (`constants.py`): SICOOB `{1:10, 5:386}`, DESÁGIO `1025` (FB). SC/CD sem journal.
- Companies REAIS: FB=1, SC=3, CD=4, LF=5 (**não** usar `EMPRESA_MAP`, divergente).
- `amount_residual` payable é **NEGATIVO** (O3) → `abs()`. `reconcile()` retorna None = **sucesso** (O6) → não retry (duplica).
- Cross-company (Fase 2): conta-ponte **PENDENTES 26868** (existe em todas companies, reconciliável); payment↔título + PENDENTES_payment↔PENDENTES_extrato (2 pernas). Conta juros por company `{1:22769,3:24051,4:25335,5:26619}`. Linha extrato: TRANSITORIA 22199→PENDENTES 26868 antes de reconciliar (O1/O11/O12); `account_id` é o ÚLTIMO write antes de `action_post`, re-buscar IDs.
- Lote **homogêneo por company** (validação rejeita company_ids divergentes).

## Reuso (não reinventar — `BaixaPagamentosService`)
`criar_pagamento_outbound(partner_id, valor, journal_id, ref, data, company_id)` (L364), `postar_pagamento` (545),
`buscar_linhas_payment` (561), `reconciliar` (599), `buscar_titulo_por_id` (127), `capturar_snapshot` (1035).
Tabelas `BaixaPagamentoLote/Item` (idempotência/auditoria — `payment_ref`, `status`, `saldo_antes/depois`).
Write-back/entrega via `exportando-arquivos`; leitura via `lendo-arquivos`.

## Arquivos
- **Criar:** `SKILL.md`, `scripts/processar_baixas.py`, `scripts/reverter_baixa.py`, `references/journals-e-cross-company.md`.
- **Tocar:** `app/financeiro/constants.py` (✅ journals adicionados); follow-up: `comprovante_lancamento_service` importar `SICOOB_JOURNAL_POR_COMPANY` de constants.

## Roadmap de implementação (incremental — move dinheiro real)
1. **Parser + PREVIEW** (READ, dry-run): planilha → localiza fatura → valida saldo/company/partner → calcula pares → relatório + planilha anotada. **Zero escrita. ✅ FEITO 2026-06-18.**
2. **WRITE FB/LF** com os 6 guards + write-ahead idempotência.
3. **`reverter_baixa.py`**.
4. **Validação ao vivo**: dry-run + 1 credor FB pequeno supervisionado antes de uso real.
5. **Fase 2 (SC/CD)**: inspecionar pagamento real cross-company + dry-run; só então automatizar.

## Riscos / pendências de validação ao vivo
- Contradição nas fontes sobre payment cross-company (company título vs banco) — resolver com inspeção real (Fase 2).
- `EMPRESA_MAP` divergente em `constants.py:100` — bug latente (fora do escopo desta skill; anotado).
- WRITE real não pode ser validado autonomamente — exige supervisão (passo 4).

## Pendências para o passo 1b (do review adversarial 2026-06-18)
- **Idempotência (ADESAO-004):** `BaixaPagamentoItem` **NÃO tem** coluna `idempotency_key` (tem `payment_ref`, semântica do fluxo EXTRATO). O write-ahead do guard F3 do 1b precisa: (a) adicionar `idempotency_key` (migration DDL + Python — par obrigatório) **ou** (b) ancorar a chave determinística no `ref`/`payment_ref` (CMPMP+venc+valor) e buscar existência por ela. Decidir no 1b antes de escrever.
- **Consolidar SICOOB (REUSO-001):** `comprovante_lancamento_service.SICOOB_JOURNAL_POR_COMPANY` duplica `constants.JOURNAL_SICOOB_POR_COMPANY` (e `extrato_conciliacao_service` importa do service, não de constants). Follow-up: importar de `constants` (toca 2 callers — fora do 1a).

## Notas de implementação do 1a (parser)
- **Datas aceitas:** datas nativas do xlsx (openpyxl), strings BR (`dd/mm/aaaa`, `dd-mm-aaaa`) e ISO (`aaaa-mm-dd`). Ano de 2 dígitos **não** é aceito; ano fora de [2000, 2100] em string → ignorado.
- **Detecção de coluna de vencimento (PARSER-004):** por valor (suporta cabeçalho `6`/`6.1`), mas colunas cujo header contenha `EMISSAO/NF/NOTA/NUMERO/COMPETENCIA/PAGAMENTO/BAIXA/...` são **excluídas** (não confundir data de emissão/NF com vencimento). Conferir as datas no `plano` do relatório.
- **Deságio:** `0 <= deságio < parcela` (negativo também é `BLOQUEADO_VALOR`).
