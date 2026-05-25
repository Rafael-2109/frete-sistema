---
name: planejando-pre-etapa-odoo
description: >-
  Skill PLANNER+EXECUTOR (READ Odoo + WRITE banco local + WRITE Odoo via C3 macro)
  da PRE-ETAPA D007 do inventario CD/FB: substitui NFs inter-filial CD↔FB
  (R$ 32,9 mi) + INDISPONIBILIZAR_* (R$ 60,5 mi) por transferencias INTERNAS
  na company + residual minimo via ResidualFbCdPlanejado (CFOP 5152) +
  ajuste positivo puro residual. Modos:
  planejar (READ Odoo + grava JSON+Excel), propor (WRITE banco local
  DELETE+INSERT em ajuste_estoque_inventario com status=PROPOSTO), listar-onda
  (READ + hash sha256), aprovar-onda (WRITE banco local com hash check
  anti-replay), executar-onda (WRITE Odoo via orchestrator C3 macro que
  compoe Skills 1+2 sobre ajustes APROVADO — POS/NEG via Skill 2 v2 com
  delta_esperado propagado, PURO via Skill 1 ajustar_quant com guard CICLAMATO).
  Usar quando o pedido eh "planeja a pre-etapa CD", "propor pre-etapa CD para o
  ciclo INVENTARIO_2026_05", "lista a Onda 5", "aprova a Onda 5 com hash X",
  "executa a Onda 5 do CD", "executar 10 produtos da Onda 5", "executa o cod
  4310177 da Onda 5", "qual transferencia interna substitui a NF FB->CD?",
  "gera plano D007 para o CD pre-Onda 2", "regerar plano apos planilha nova".
  `--dry-run` eh o DEFAULT em todos os modos write (planejar NAO grava JSON/XLSX;
  propor NAO faz DELETE+INSERT; aprovar NAO altera status; executar NAO chama
  Odoo). listar-onda eh sempre READ-only (sem dry-run).
  NAO USAR PARA:
  - Ajustar quant pontual sem pre-etapa -> ajustando-quant-odoo
  - Transferir saldo cross loc+lote (sem ciclo de proposta) ->
    transferindo-interno-odoo
  - Outras ondas do ciclo (Onda 1/2/3/4) -> 04_propor_ajustes.py (operacao viva)
  - Auditoria pos-execucao de saldos -> consultando-quant-odoo
allowed-tools: Read, Bash, Glob, Grep
---

# planejando-pre-etapa-odoo (READ + WRITE banco local + WRITE Odoo C3 — 5 modos)

Skill **minimo viavel** (C1 mineracao ✅ · C2-C5 implementados para 5 modos · C6-C10 conforme uso). Construida em 2026-05-24 capinando os scripts-fonte `03b_planejar_pre_etapa_cd` (READ planner) + `04b_propor_pre_etapa_cd` (WRITE banco local + workflow hash) em sessao v6. **Estendida em 2026-05-25 sessao v9** capinando `09b_executar_pre_etapa` (executor C3 macro) para `app/odoo/estoque/orchestrators/pre_etapa_executor.py` — agora a skill cobre o ciclo completo planejar→propor→aprovar→executar.

**Decisao D007** (`docs/inventario-2026-05/00-decisoes/D007-pre-etapa-cd-fb-minimizar-nf.md`): substituir NFs inter-filial CD↔FB (~R$ 32,9 mi) + INDISPONIBILIZAR_LOTE/LOCAL (~R$ 60,5 mi) por **transferencias INTERNAS** dentro da company (mesma fronteira fiscal) + **residual minimo** FB→CD via NF (CFOP 5152) + **ajuste positivo puro** (inventory adjustment sem origem) quando ninguem doa. Onda 5 (CD) executa ANTES da Onda 2 (TRANSFERIR_FB_CD residual). Onda 6 (FB) futura.

Constituicao: `app/odoo/estoque/CLAUDE.md`. Service: `app/odoo/estoque/scripts/pre_etapa.py` (`PreEtapaEstoqueService.planejar()` por produto + helpers top-level `planejar_pre_etapa_batch_company`, `propor_ajustes_pre_etapa`, `listar_onda_pre_etapa`, `aprovar_onda_pre_etapa`). Shim em `services/pre_etapa_estoque_service.py` para 03b/04b/testes legacy.

---

## REGRAS CRITICAS

1. **`--dry-run` eh o DEFAULT.** Sem `--confirmar`, modos `planejar`/`propor`/`aprovar-onda` so calculam o plano (exit 4). Modo `listar-onda` eh sempre READ-only.
2. **Pre-condicao da skill:** scripts 01 (`01_extrair_estoque_odoo.py`) e 02 (`02_carregar_inventario_xlsx.py`) ja rodaram, gerando `/tmp/estoque_odoo_2026_05.json` + `/tmp/inventario_fisico_2026_05.json` (ou paths customizados via `--input-estoque`/`--input-inv`). Sem esses inputs, `planejar` aborta com FALHA_INPUT_AUSENTE.
3. **D007 restricao temporal FB pos-etapa:** ENQUANTO FB nao tiver passado pela propria pre-etapa, qualquer lote FB pode doar para CD (passa `quants_complementar_raw=quants_fb_raw`). APOS pre-etapa FB, **so o lote MIGRAÇÃO da FB pode doar** (caller deve filtrar `quants_complementar_raw` para conter apenas quants com `lote_nome=MIGRAÇÃO`). A skill NAO infere esse estado — usuario decide via filtro.
4. **`propor` faz DELETE+INSERT** dos ajustes PROPOSTO da company do ciclo. Idempotente (reproduz a partir do plano JSON). **Backup pg_dump default OFF** — passar `--backup-pg-dump` para forcar (depende de `PGPASSWORD` no env).
5. **`aprovar-onda` exige `--hash` correto.** Bloqueia com FALHA_HASH_DIVERGENTE se hash atual != esperado (anti-replay). Sempre rodar `listar-onda` antes para pegar o hash atual.
6. **Outliers cod[0] nao 1-4 skipados:** filtro implicito do `planejar_pre_etapa_batch_company` (espelha 03b). Retornados em `outliers_skipados` do output JSON.

## Contrato — `planejar` (modo 1: READ Odoo + grava arquivos)

```
objeto:        PreEtapaEstoqueService.planejar (1 produto) compose-batch via
                planejar_pre_etapa_batch_company (1 company inteira)
input:         --modo planejar --company-id <4|1>
                 [--input-estoque /tmp/estoque_odoo_2026_05.json]
                 [--input-inv /tmp/inventario_fisico_2026_05.json]
                 [--output-json /tmp/plano_pre_etapa_<cid>.json]
                 [--output-xlsx docs/inventario-2026-05/07-relatorios/plano-pre-etapa-<cid>.xlsx]
                 [--cods 4310177,210030325,...]   (subset; default = todos validos)
                 [--complementar 1|none]          (CD pode puxar de FB ; FB so 1 ou skip)
                 [--confirmar]
output (JSON): {modo: planejar, status, company_id, produtos_processados,
                 produtos_sem_mudanca, outliers_skipados, total_pos, total_neg,
                 total_residual_fb_cd, total_positivos_puros, total_warnings,
                 output_json_path, output_xlsx_path, tempo_ms}
                 + dump do plano_total em output_json_path se --confirmar.
pre-condicoes: scripts 01 + 02 ja rodaram (inputs existem); odoo acessivel.
pos-condicoes: arquivos JSON + XLSX criados (se --confirmar). Odoo NAO eh
                modificado (READ-only).
gotchas-invariante:
   - FIFO determinístico por quant_id (svc.planejar usa sort estavel)
   - Lote inv sem nome agregado em 'P-15/05' (LOTE_DEFAULT_SEM_NOME)
   - MIGRAÇÃO nao-doadora-de-si-mesma (skip em loop doadores)
   - Custo medio ponderado D004 (value/quantity)
   - Warnings de reserva NAO bloqueiam (apenas alertam para revisao manual)
   - Outliers cod[0] nao in 1-4 skipados (retornados em outliers_skipados)
   - D007 restricao temporal FB pos-etapa: caller filtra complementar_raw
modos:         --dry-run (default, exit 4 — calcula mas NAO grava) -> --confirmar (exit 0)
status:        PLANEJADO · DRY_RUN_OK_PLANEJADO · FALHA_INPUT_AUSENTE · FALHA_ODOO
```

## Contrato — `propor` (modo 2: WRITE banco local)

```
objeto:        ajuste_estoque_inventario (DELETE+INSERT status=PROPOSTO)
input:         --modo propor --company-id <4|1>
                 [--plano-json /tmp/plano_pre_etapa_<cid>.json]   (saida de planejar)
                 [--ciclo INVENTARIO_2026_05]
                 [--usuario rafael]
                 [--backup-pg-dump]                                 (default OFF)
                 [--confirmar]
output (JSON): {modo: propor, status, ciclo, company_id, dry_run,
                 n_antes, n_apos (None se dry_run), n_deletados (None se dry_run),
                 contador (4 acoes), total_inserts, backup_path (None se OFF),
                 tempo_ms}
pre-condicoes: --plano-json existe (gerado por modo planejar); banco local
                tem `ajuste_estoque_inventario` schema.
pos-condicoes: --confirmar: DELETE old PROPOSTO + INSERT new (4 acoes:
                AJUSTE_{CD|FB}_TRANSF_INTERNA_POS/NEG, AJUSTE_{CD|FB}_POSITIVO_PURO,
                e TRANSFERIR_FB_CD para CD)
gotchas-invariante:
   - Idempotente (re-rodar sobre mesmo ciclo+company DELETE+INSERT zerado-reinit)
   - TRANSFERIR_FB_CD so existe para company_id=4 (CD na Onda 5)
   - tipo_produto = int(cod[0]) (1-4)
   - qtd_ajuste=0 para internas (POS+NEG); qtd_ajuste=+qty para PURO/FB_CD
   - lote_odoo=lote_origem nas internas; vazio nas PURO/FB_CD
   - backup pg_dump exige PGPASSWORD (passar via --backup-pg-dump-password ou env)
modos:         --dry-run (default, exit 4 — rollback) -> --confirmar (exit 0)
status:        PROPOSTO · DRY_RUN_OK_PROPOSTO · FALHA_PLANO_AUSENTE ·
               FALHA_BANCO · FALHA_BACKUP
```

## Contrato — `listar-onda` (modo 3: READ banco local)

```
objeto:        ajuste_estoque_inventario (READ-only)
input:         --modo listar-onda --company-id <4|1>
                 [--ciclo INVENTARIO_2026_05]
                 [--onda-num 5|6]                  (default inferido de cid)
output (JSON): {modo: listar-onda, status, ciclo, company_id, onda_num,
                 total, hash (sha256), por_acao {acao: {n, valor}},
                 valor_total, tempo_ms}
pre-condicoes: ajustes PROPOSTO da onda existem no banco local (modo propor
                ja rodou e --confirmar).
pos-condicoes: nenhuma (READ).
gotchas-invariante:
   - Hash sha256 = sha256(id|cod|cid|lote_odoo|qtd_ajuste|acao para todos
     ordenado por id)
   - Filtro: status=PROPOSTO + company_id + acoes da Onda
   - Valor = sum(abs(qtd_ajuste * custo_medio))
modos:         sempre READ (sem dry-run/confirmar)
status:        LISTADO · LISTADO_VAZIO · FALHA_BANCO
exit:          0 sempre (READ-only)
```

## Contrato — `aprovar-onda` (modo 4: WRITE banco local)

```
objeto:        ajuste_estoque_inventario (UPDATE status PROPOSTO -> APROVADO)
input:         --modo aprovar-onda --company-id <4|1> --hash <sha256>
                 [--ciclo INVENTARIO_2026_05]
                 [--usuario rafael]
                 [--onda-num 5|6]                  (default inferido de cid)
                 [--confirmar]
output (JSON): {modo: aprovar-onda, status, ciclo, company_id, onda_num,
                 ajustes_aprovados, hash_atual, hash_esperado,
                 ts_aprovacao (None se dry_run), tempo_ms}
pre-condicoes: --hash deve bater com listar-onda atual (anti-replay).
pos-condicoes: --confirmar: ajustes UPDATE status=APROVADO + aprovado_em +
                aprovado_por.
gotchas-invariante:
   - Bloqueia com FALHA_HASH_DIVERGENTE se hash atual != esperado
   - Idempotente em dry-run; UPDATE em --confirmar
   - ts_aprovacao = agora_utc_naive()
modos:         --dry-run (default, exit 4 — valida hash mas NAO altera) -> --confirmar (exit 0)
status:        APROVADO · DRY_RUN_OK_APROVADO · FALHA_HASH_DIVERGENTE ·
               FALHA_NENHUM_PROPOSTO · FALHA_BANCO
```

## Contrato — `executar-onda` (modo 5: WRITE Odoo via orchestrator C3 macro)

```
objeto:        ajuste_estoque_inventario (status APROVADO -> EXECUTADO/FALHA)
                + stock.quant Odoo (via Skill 1 ajustar_quant)
                + stock.lot Odoo (via Skill 2 resolver_lote_destino + criar_se_nao_existe)
input:         --modo executar-onda --company-id <4|1>
                 [--ciclo INVENTARIO_2026_05]
                 [--usuario rafael]
                 [--onda-num 5|6]                  (default inferido de cid)
                 [--limite N]                       (sub-piloto: N primeiros)
                 [--cod-produto X]                  (1 produto especifico)
                 [--max-workers 5]                  (paralelizar; default=1 serial)
                 [--confirmar]
output (JSON): {modo: executar-onda, status, ciclo, company_id, onda_num,
                 ajustes_total, produtos_total, dry_run, max_workers, limite,
                 cod_produto_filter,
                 contadores: {produtos_ok, produtos_parcial, produtos_falha,
                              pos_ok, pos_falha, neg_ok, neg_falha,
                              puro_ok, puro_falha},
                 produtos: [{cod, product_id, sucessos, falhas,
                            pos/neg/puro_results}],
                 tempo_ms}
pre-condicoes:
   - Skill 6 modo aprovar-onda rodado (ajustes status='APROVADO').
   - Skills 1+2+9 services importaveis (validado em pytest baseline 230+21).
   - Odoo XML-RPC acessivel (ODOO_* env vars).
pos-condicoes: --confirmar:
   - POS/NEG: stock.quant origem reduzido + destino aumentado (via
     transferir_quantidade_para_lote_v2 = ajustar_quant x2 com
     delta_esperado=±qty propagado — guard CICLAMATO ativo).
   - PURO: stock.quant alvo criado/aumentado (via ajustar_quant
     criar_se_faltar=True + delta_esperado=qty).
   - ajuste.status = 'EXECUTADO' OU 'FALHA' (com fase_pipeline + erro_msg).
   - OperacaoOdooAuditoria.registrar para CADA ajuste tocado (SUCESSO/FALHA).
gotchas-invariante:
   - Guard delta_esperado em TODAS as 3 acoes (POS/NEG via Skill 2 v2; PURO via Skill 1)
     — protege contra bug CICLAMATO (politica homogenea em retomada de FALHA).
   - Produto inativo (active=False) NAO eh processado: ajuste FALHA com mensagem
     "product_id nao resolvido — produto arquivado".
   - Doador localizado por lote_nome exato (prefere menor sobra); fallback retorna
     primeiro do lote (caller bloqueia se saldo insuficiente).
   - Paralelizacao: cada thread tem app_context + conexao Odoo + session db
     proprios (Flask-SQLAlchemy scoped). max_workers=5 da ~5x speed em bulk.
   - Auditoria via OperacaoOdooAuditoria com pipeline_etapa='ONDA_5_PRE_ETAPA' e
     external_id unico (PREETAPA-<acao>-<ajuste_id>-<uuid8>).
modos:         --dry-run (default, exit 4 — calcula plano mas NAO chama Odoo) -> --confirmar (exit 0)
status:        EXECUTADO_ONDA · DRY_RUN_OK_EXECUTADO · FALHA_NENHUM_APROVADO ·
               FALHA_USO · FALHA_ODOO
```

## Receitas (caso real -> args)

| Preciso de... | Modo | Args |
|---------------|------|------|
| Planejar pre-etapa CD (default) | planejar | `--modo planejar --company-id 4 --confirmar` |
| Re-planejar apos planilha nova | planejar | `--modo planejar --company-id 4 --input-inv /tmp/inv_v2.json --confirmar` |
| Planejar so 1 produto (debug) | planejar | `--modo planejar --company-id 4 --cods 210030325` |
| Planejar FB Onda 6 (futura) | planejar | `--modo planejar --company-id 1 --complementar none --confirmar` |
| Planejar dry-run (preview) | planejar | `--modo planejar --company-id 4` |
| Propor ajustes pos-planejar | propor | `--modo propor --company-id 4 --usuario rafael --confirmar` |
| Propor com backup pg_dump | propor | `--modo propor --company-id 4 --backup-pg-dump --confirmar` |
| Listar Onda 5 + hash | listar-onda | `--modo listar-onda --company-id 4` |
| Aprovar Onda 5 com hash | aprovar-onda | `--modo aprovar-onda --company-id 4 --hash abc123... --usuario rafael --confirmar` |
| **Executar Onda canary (1 produto)** | executar-onda | `--modo executar-onda --company-id 4 --limite 1 --usuario rafael --confirmar` |
| **Executar Onda sub-piloto (10 produtos)** | executar-onda | `--modo executar-onda --company-id 4 --limite 10 --usuario rafael --confirmar` |
| **Executar Onda bulk paralelo (todos)** | executar-onda | `--modo executar-onda --company-id 4 --max-workers 5 --usuario rafael --confirmar` |
| **Executar 1 produto especifico (debug)** | executar-onda | `--modo executar-onda --company-id 4 --cod-produto 4310177 --usuario rafael --confirmar` |
| **Dry-run da Onda (preview sem tocar Odoo)** | executar-onda | `--modo executar-onda --company-id 4 --limite 10` |

## Composicao em FLUXOS

> Numeracao canonica em [`app/odoo/estoque/fluxos/4.1-pre-etapa-cd-d007.md`](../../../app/odoo/estoque/fluxos/4.1-pre-etapa-cd-d007.md) (galho 4.1 da arvore — ver `fluxos/README.md`).

- **Fluxo 4.1 — gerar Onda 5 (CD) ponta-a-ponta** (pre-etapa CD; sub-caso default):
  1. Rodar scripts 01 + 02 (operacao viva — geram JSONs em /tmp).
  2. `planejar_pre_etapa.py --modo planejar --company-id 4 --confirmar`
     → JSON `/tmp/plano_pre_etapa_4.json` + Excel `docs/inventario-2026-05/07-relatorios/plano-pre-etapa-4.xlsx`.
  3. Revisar Excel (4 abas: Internas, Residual FB-CD, Positivos Puros, Warnings).
  4. `planejar_pre_etapa.py --modo propor --company-id 4 --usuario X --confirmar`
     → DELETE old PROPOSTO + INSERT 4 acoes no banco local.
  5. `planejar_pre_etapa.py --modo listar-onda --company-id 4` → pegar hash + valor total.
  6. `planejar_pre_etapa.py --modo aprovar-onda --company-id 4 --hash <h> --usuario X --confirmar` → APROVADO.
  7. **EXECUTAR (DESTA SKILL — orquestrador C3 macro compoe Skills 1+2):**
     - **Canary primeiro** (1 produto): `planejar_pre_etapa.py --modo executar-onda --company-id 4 --limite 1 --usuario X --confirmar`
     - **Sub-piloto** (10 produtos): `planejar_pre_etapa.py --modo executar-onda --company-id 4 --limite 10 --usuario X --confirmar`
     - **Bulk depois** (todos, paralelo): `planejar_pre_etapa.py --modo executar-onda --company-id 4 --max-workers 5 --usuario X --confirmar`

- **Sub-fluxo 4.1.a — preview ANTES de regenerar planilha** (avaliar impacto):
  1. `planejar_pre_etapa.py --modo planejar --company-id 4` (dry-run — calcula mas NAO grava).
  2. Saida JSON com sumarios (total_pos, total_neg, total_residual_fb_cd) sem tocar disco.
  3. Decidir se inventario fisico precisa de revisao (ex.: muitos positivos puros sinalizam contagem faltando).

- **Sub-fluxo 4.1.b — re-aprovar onda apos correcao** (alguem mudou ajustes manualmente):
  1. `listar-onda` → pega hash atual.
  2. Comparar com hash anterior (auditoria).
  3. `aprovar-onda --hash <novo>` bloqueia se ajustes foram alterados sem replanejar — usuario deve refazer planejar+propor.

- **Sub-fluxo 4.1.c — Onda 6 FB futura:** `planejar --company-id 1 --complementar none --confirmar` (FB nao tem complementar; positivos puros cobrem deficits).

- **Sub-fluxo 4.1.d — subset de produtos (debug):** `--cods 210030325,4310177` restringe processamento.

- **Sub-fluxo 4.1.e — executar Onda APROVADA (NOVO 2026-05-25 v9 — orchestrator C3):**
  1. **Pre-cond inviolavel**: passos 1-6 do fluxo 4.1 rodados (ajustes status='APROVADO').
  2. **Canary OBRIGATORIO** (1 produto, dry-run primeiro): `--modo executar-onda --company-id 4 --limite 1`.
  3. Revisar JSON output (campos `contadores`, `produtos[0].pos_results/neg_results/puro_results`).
  4. **Canary real**: `--modo executar-onda --company-id 4 --limite 1 --confirmar`. Verificar DIRETO no Odoo o quant tocado.
  5. **Sub-piloto** (10 produtos serial): `--modo executar-onda --company-id 4 --limite 10 --confirmar`.
  6. **Bulk paralelo**: `--modo executar-onda --company-id 4 --max-workers 5 --confirmar`. **Cuidado**: max_workers > 5 pode sobrecarregar Odoo XML-RPC.
  7. Auditar pos-execucao: `OperacaoOdooAuditoria` tem registros com pipeline_etapa='ONDA_5_PRE_ETAPA' por ajuste. Tabela `ajuste_estoque_inventario.status` migra para 'EXECUTADO' OU 'FALHA' (com erro_msg).
  8. **Retomada de FALHAs**: re-rodar `--modo executar-onda --cod-produto <X>` so reprocessa ajustes APROVADO (FALHA volta a fila apenas via correcao manual + UPDATE status='APROVADO' do operador).

## Armadilhas

- **D007 restricao temporal FB pos-etapa**: a skill NAO infere se FB ja passou pela propria pre-etapa. Caller decide se passar `quants_complementar_raw=quants_fb` (qualquer lote OK) ou filtrado (so MIGRAÇÃO FB OK). Se FB pos-etapa, passar JSON pre-filtrado.
- **MIGRAÇÃO como lote inv**: se o inventario fisico lista MIGRAÇÃO explicitamente, o algoritmo trata como lote alvo (pode receber doacao). Se ausente, MIGRAÇÃO eh consolidador NEG (recebe sobras dos doadores).
- **Lote inv sem nome agregado em 'P-15/05'**: multiplas linhas inv sem lote viram 1 so quant alvo de nome 'P-15/05' (LOTE_DEFAULT_SEM_NOME). Cuidado: se o operador escrever "P-15/05" explicitamente em outra linha do inv, sera agregado tambem.
- **Outliers cod[0] != 1-4 skipados**: produtos com cod estranho (X-prefix, alfanumerico) saem do plano. Verificar `outliers_skipados` no JSON output para garantir que nenhum produto critico foi excluido.
- **FB → CD residual: lote sugerido eh o MAIOR saldo da FB**: nao FIFO, nao MIGRAÇÃO automatico. Operador decide qual lote real puxar.
- **Custo medio ponderado D004**: usa apenas quants com `qty > 0 AND value != 0`. Quants com value=0 (saldo sem custo) sao excluidos da media — pode levar a custo_medio=0 se TODOS os quants tem value=0. NAO bloqueia (positivo puro com custo zero eh aceito).
- **Hash sha256 muda se mudar QUALQUER campo**: id, cod, cid, lote_odoo, qtd_ajuste, acao. Ordem dos ajustes (sort por id) garante determinismo.
- **Backup pg_dump exige PGPASSWORD**: passa `--backup-pg-dump-password XXX` OU define `PGPASSWORD` no env antes de rodar. Sem isso, RuntimeError no propor.
- **Idempotencia do propor**: DELETE+INSERT zera+reinit. Re-rodar sobre mesmo ciclo+company gera novos IDs (hash muda!). Se precisar replanejar, refazer planejar -> propor -> listar -> aprovar.
- **executar-onda: produto inativo NAO eh skip silencioso** — ajuste fica FALHA com mensagem clara ("product_id nao resolvido — produto arquivado..."). Operador decide se reativa OU cancela manualmente o ajuste.
- **executar-onda: doador insuficiente bloqueia** — se `localizar_doador` retorna quant com `qty < pedida`, o ajuste falha sem chamar Skill 2 (mensagem: "quant origem X tem Y un, ajuste pede Z"). Tipicamente significa que outro fluxo movimentou o lote entre propor e executar. Replanejar+repropor pode resolver.
- **executar-onda: paralelizacao tem trade-off** — max_workers > 5 sobrecarrega Odoo XML-RPC (rate limit + timeouts). 1 (serial, default) eh seguro; 5 eh sweet spot para bulk de 100+ produtos.
- **executar-onda: FALHA_AUMENTO em transferencia = ESTADO PARCIAL** — Skill 2 v2 reduziu origem mas falhou em aumentar destino (lote_destino corrompido, etc). Ajuste fica FALHA com `detalhes_v2.qty_reduzida_origem` informando o debito parcial efetivado. Rollback manual via Skill 1 `ajustar_quant +qty_reduzida_origem` no lote origem (ver `[[gotcha_inventory_adjustment_quant_negativo]]`).
- **executar-onda: nao mexer ajuste APROVADO entre aprovar-onda e executar-onda** — bypassa auditoria do hash. Se precisar corrigir, refazer ciclo completo (planejar+propor+listar+aprovar).

## Exemplos

```bash
SK=.claude/skills/planejando-pre-etapa-odoo/scripts/planejar_pre_etapa.py

# 1) Planejar CD (dry-run — preview)
python "$SK" --modo planejar --company-id 4

# 2) Planejar CD (efetiva — grava JSON + Excel)
python "$SK" --modo planejar --company-id 4 --confirmar

# 3) Planejar 1 produto especifico (debug)
python "$SK" --modo planejar --company-id 4 --cods 210030325

# 4) Planejar FB Onda 6 (futura)
python "$SK" --modo planejar --company-id 1 --complementar none --confirmar

# 5) Propor ajustes da Onda 5 (banco local)
python "$SK" --modo propor --company-id 4 --usuario rafael --confirmar

# 6) Propor com backup pg_dump (cinto+suspensorio)
export PGPASSWORD='frete_senha_2024'
python "$SK" --modo propor --company-id 4 --backup-pg-dump --confirmar

# 7) Listar Onda 5 + hash
python "$SK" --modo listar-onda --company-id 4
# → { ..., "hash": "abc123def456...", "valor_total": "32956127.45" }

# 8) Aprovar Onda 5 com hash (anti-replay)
python "$SK" --modo aprovar-onda --company-id 4 \
  --hash abc123def456... --usuario rafael --confirmar

# 9) Executar Onda 5 — CANARY (1 produto, dry-run primeiro)
python "$SK" --modo executar-onda --company-id 4 --limite 1 --usuario rafael
# → revisar JSON output (produtos[0].pos_results/neg_results/puro_results)

# 10) Executar Onda 5 — CANARY real
python "$SK" --modo executar-onda --company-id 4 --limite 1 --usuario rafael --confirmar
# → verificar DIRETO no Odoo o quant tocado antes de prosseguir

# 11) Executar Onda 5 — sub-piloto 10 produtos (serial)
python "$SK" --modo executar-onda --company-id 4 --limite 10 --usuario rafael --confirmar

# 12) Executar Onda 5 — bulk paralelo (todos)
python "$SK" --modo executar-onda --company-id 4 --max-workers 5 --usuario rafael --confirmar

# 13) Executar Onda 5 — 1 produto especifico (debug FALHA)
python "$SK" --modo executar-onda --company-id 4 --cod-produto 4310177 --usuario rafael --confirmar
```

## Validacao

Skill **construida em 2026-05-24** (sessao v6 "Skill 6 nasce") capinando 03b + 04b. **Estendida em 2026-05-25 sessao v9** capinando 09b (executor C3 macro):
- C1: 3 scripts-fonte minerados integral (`03b_planejar_pre_etapa_cd`, `04b_propor_pre_etapa_cd`, `09b_executar_pre_etapa`) + decisao D007 + 13 testes existentes lidos. **v9**: 09b (746 LOC) remineracao + 4 services minerados (quant.py, transfer.py v2, pre_etapa.py, _cli_utils.py).
- C2: service `app/odoo/estoque/scripts/pre_etapa.py` (capinado de `app/odoo/services/`) estendido com 7 helpers top-level + 4 constantes do workflow. Shim em `services/`. **v9**: novo orchestrator `app/odoo/estoque/orchestrators/pre_etapa_executor.py` (~580 LOC) compondo Skills 1+2. **21 testes pytest novos verdes para orchestrator** + 21 testes service preservados = **42 testes pytest Skill 6 verdes** (251 total baseline estoque).
- C3: contrato de **5 modos** definido (planejar, propor, listar-onda, aprovar-onda, executar-onda).
- C4: SKILL.md com receitas, fluxos 4.1/4.1.a-e, armadilhas (incluindo armadilhas executar-onda v9), exemplos.
- C5: `scripts/planejar_pre_etapa.py` (CLI **5 modos**, `--dry-run` default em modos write, exit codes 0/1/2/4). **v9**: novo `modo_executar_onda` + args `--limite/--cod-produto/--max-workers`.
- C6: 3 smokes CLI iniciais (FALHA_INPUT_AUSENTE exit 1, FALHA_USO exit 2, DRY_RUN_OK exit 4); log em `/tmp/log_skill6_C6_validacao_dry_run.json`. **v9**: smokes executar-onda em dry-run (`FALHA_USO` company_id invalido, `FALHA_NENHUM_APROVADO` ciclo inexistente — cobertos por pytest).
- C7-C10: cross-refs + arquivamento `_validados/planejando-pre-etapa-odoo/` (03b + 04b **+ 09b v9**) + ROADMAP + MAPA_SCRIPTS + folha de fluxo 4.1 (com sub-caso 4.1.e v9).

Mapeamento script-fonte -> atomo no `docs/inventario-2026-05/consolidacao/MAPA_SCRIPTS.md`. Resultado da validacao em `_validados/planejando-pre-etapa-odoo/VALIDACAO.md`.

## NAO-FAZER (red flags)

- ❌ Rodar `propor` antes de `planejar` (FALHA_PLANO_AUSENTE).
- ❌ Rodar `aprovar-onda` sem `listar-onda` antes (FALHA_HASH_DIVERGENTE — hash precisa ser fresh).
- ❌ Rodar `executar-onda` antes de `aprovar-onda` (executor exige status='APROVADO'; retorna FALHA_NENHUM_APROVADO).
- ❌ **(v9) Rodar `executar-onda --confirmar` sem canary primeiro** — SEMPRE rodar `--limite 1 --confirmar` antes de bulk. Verificar Odoo diretamente. Sem canary, FALHAS bulk podem cascatear silenciosamente em produtos similares.
- ❌ **(v9) Rodar `executar-onda --max-workers > 5`** — sobrecarrega Odoo XML-RPC (rate limit). 5 eh sweet spot para 100+ produtos; serial (1) eh seguro.
- ❌ **(v9) Re-rodar `executar-onda` sobre ajustes FALHA** sem corrigir o root cause — FALHA fica no status FALHA ate operador alterar manualmente para APROVADO. Re-rodar sobre APROVADO restantes funciona normalmente (apenas FALHA fica de fora).
- ❌ Misturar Ondas: cada `propor` DELETE+INSERT zera apenas a Onda DESTE company_id. Outras ondas (1-4) intactas.
- ❌ Passar `--complementar=fb` apos FB ja ter passado pela propria pre-etapa SEM filtrar quants_fb_raw para conter so MIGRAÇÃO (caller decide).
- ❌ Editar ajustes APROVADO manualmente — quebra a auditoria do hash; refazer o ciclo planejar→propor→listar→aprovar.
- ❌ Confiar em `custo_medio=0` para positivos puros — pode indicar quants sem value (D004 ignorou). Revisar manualmente.
