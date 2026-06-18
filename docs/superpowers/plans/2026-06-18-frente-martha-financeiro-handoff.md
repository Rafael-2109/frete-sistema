<!-- doc:meta
tipo: how-to
camada: L3
sot_de: —
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-18
-->
# Handoff — Frente Martha (financeiro): skills + correções

> **Papel:** roteiro de próximos passos (multi-sessão) da frente que atende as 6 demandas
> da Martha (financeiro, user_id 82) via skills do Agente Web + correções de módulo.

## Contexto
A Martha usa o Agente Web para **6 tarefas de financeiro distintas**, fazendo tudo à mão via
scripts ad-hoc (11 sessões/17d, ~$258, 277 scripts só em 17/06). **Raiz comum:** a lógica
financeira robusta já existe no módulo web (`extrato_matching_service`, `ofx_parser_service`,
`pagamento_matching_service`, `baixa_pagamentos_service`, `extrato_conciliacao_service`) mas é
**inacessível ao agente** → ele reinventa parse+match+reconcile a cada sessão. **Correção =
skill thin-wrapper sobre o service.** Memória: `martha_financeiro_frente_skills`.

Trabalho em `frete_sistema_manutencao`, branch `cron/manutencao`, **SEM push** (revisão 4-mãos).

## Estado atual (já committed nesta branch)
- `07192c5c8` item 1 (reset Motos Assai recusado) · `0cbbbd9f6` fix validador SQL · `1761a6a27` estudo F2.
- `ab7cd1887` **Skill F** `gerando-controle-recebiveis` — FEITA, 5 testes, delegada ao `auditor-financeiro`.
- `16dc513f7` **Skill A** `baixando-credores-lote-odoo` — DESIGN + fundação (constants). **Código pendente.**

## Próximos passos (ordem de ROI)

### 1. Skill A — CÓDIGO (maior ROI; WRITE de pagamento real)
> Roteiro técnico completo: `.claude/skills/baixando-credores-lote-odoo/DESIGN.md`. Pré-flight Odoo já feito.
- [x] **1a. Parser + PREVIEW (READ, dry-run, ZERO escrita) — FEITO 2026-06-18.** Service `app/financeiro/services/baixa_credores_lote_service.py` + script `scripts/processar_baixas.py` + `SKILL.md` + `references/journals-e-cross-company.md` + 21 testes (`tests/financeiro/test_baixa_credores_lote.py`, todos verdes) + smoke test ao vivo (8 cenários). `--confirmar` recusado (WRITE = 1b). **Descobertas ao vivo:** (a) `name` de fatura COLIDE entre companies → desambiguação pela coluna EMPRESA (company efetiva ainda vem da fatura, O8); (b) journal DESÁGIO (1025) **só existe na FB** — LF com deságio = `BLOQUEADO_SEM_JOURNAL_DESAGIO`, LF sem deságio = só SICOOB; (c) faturas parceladas = N linhas payable, residual somado.
- [ ] **1b. WRITE FB/LF** reusando `BaixaPagamentosService` (`criar_pagamento_outbound`/`postar_pagamento`/`reconciliar`), com os **6 guards do pré-mortem**: pós-reconcile READ (`residual==0`); asserção `deságio<parcela` + `--confirmar-valor-total`; write-back ancorado por CMPMP (openpyxl ponta-a-ponta); write-ahead `BaixaPagamentoItem` PENDENTE + `idempotency_key` no `ref`; lookup casando company; gotchas O3/O6.
- [ ] **1c. `reverter_baixa.py --lote-id`** (action_draft+unlink, dry-run default) — entregar JUNTO.
- [ ] **1d. Validação ao vivo SUPERVISIONADA:** dry-run + 1 credor FB pequeno antes de uso real (não autônomo).
- [ ] **1e. Fase 2 (SC/CD):** SC(3)/CD(4) NÃO têm journal bancário → cross-company via conta-ponte PENDENTES 26868. Comprovado p/ *receber*, NÃO p/ *pagar* → inspecionar 1 pagamento real cross-company + dry-run **antes** de automatizar. Até lá: `BLOQUEADO_CROSS_COMPANY` (manual).

### 2. Quick-win — fix do parser OFX (destrava a demanda B)
- [ ] `app/financeiro/services/ofx_parser_service.py:89-99` (`_parsear_valor_ofx`) assume **ponto** decimal; aceitar **vírgula BR** (Bradesco `-1.597,44`). Conserta também `lendo-arquivos` + import web. Horas. Adicionar teste.

### 3. Skill B — dedup OFX × Odoo (após o fix do parser)
- [ ] Nova skill: ler OFX → cruzar FITID com `bank.statement.line` → agrupar duplicatas (**guard anti-falso-positivo:** 2 transações de mesmo valor/data com FITID distinto NÃO é duplicata) → excluir (reset-draft + unlink, **preservar conciliadas**). WRITE destrutivo → dry-run default + guard. (O agente já excluiu 4 linhas legítimas à mão — não repetir.)

### 4. Skill C — diff extrato banco (PDF) × Odoo
- [ ] Nova skill **wrapper** de `extrato_matching_service`/`extrato_pdf_srm_service`: residual exato + causa-raiz (move cancelada/órfã/inter-company). READ (baixo risco).

### 5. Estender `razao-geral-odoo` — demanda D
- [ ] Novo modo `conciliar-razao`: parear débito↔crédito sem par cancelador que somam o residual (`account.move.line`). Gap já nomeado em IMP-2026-06-10-002. **Estender** (não nova skill — Constituição §6).

### 6. Demanda E — Sendas (não é skill)
- [ ] Captura de dados: lançar abatimentos Sendas (`executando-odoo-financeiro`/`abatimentos.py`) + reativar a **conciliação Grafeno** (parada desde jan/2026 — ver estudo F2). Direcionar a Martha às skills existentes.

## Pendências / decisões abertas
- **Cross-company SC/CD (pagamento):** validar ao vivo antes de automatizar (Fase 2 de A).
- **Bug `EMPRESA_MAP`** (`constants.py:100` diz SC=2/CD=3; real FB=1/SC=3/CD=4/LF=5) — corrigir + auditar callers (tarefa própria, fora desta frente).
- **Skill F:** direcionar a Martha a usá-la (via `auditor-financeiro`); avaliar se o melhor é a skill OU adicionar **gestor no relatório da TELA** de contas a receber (a tela já faz vencidos + export). Limite MVP: `CONFIRMADO` vem de `parcela_paga` do Odoo (delta Grafeno não baixado fica Vencido).
- **Conciliação Grafeno parada desde jan/2026** (journal GRA1) — afeta E e o delta da skill F; investigar por que parou.

## Como começar a próxima sessão
1. `cd frete_sistema_manutencao` (branch `cron/manutencao`, sem push).
2. Ler: **este doc** + `.claude/skills/baixando-credores-lote-odoo/DESIGN.md` + memória `martha_financeiro_frente_skills`.
3. Conexão Odoo READ disponível no dev (`app.odoo.utils.connection.get_odoo_connection`). **WRITE no Odoo só com supervisão** (passo 1d).
4. Recomendação de início: **passo 1a (preview de A)** OU **passo 2 (fix parser OFX)** — ambos seguros/READ.
