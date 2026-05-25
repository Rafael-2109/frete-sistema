---
name: planejando-pre-etapa-odoo
description: >-
  Skill PLANNER (READ Odoo + WRITE banco local) da PRE-ETAPA D007 do inventario
  CD/FB: substitui NFs inter-filial CD↔FB (R$ 32,9 mi) + INDISPONIBILIZAR_*
  (R$ 60,5 mi) por transferencias INTERNAS na company + residual minimo via
  ResidualFbCdPlanejado (CFOP 5152) + ajuste positivo puro residual. Modos:
  planejar (READ Odoo + grava JSON+Excel), propor (WRITE banco local DELETE+INSERT
  em ajuste_estoque_inventario com status=PROPOSTO), listar-onda (READ + hash
  sha256), aprovar-onda (WRITE banco local com hash check anti-replay).
  Usar quando o pedido eh "planeja a pre-etapa CD", "propor pre-etapa CD para o
  ciclo INVENTARIO_2026_05", "lista a Onda 5", "aprova a Onda 5 com hash X",
  "qual transferencia interna substitui a NF FB->CD?", "gera plano D007 para o
  CD pre-Onda 2", "regerar plano apos planilha nova", "qual valor da Onda 5?".
  `--dry-run` eh o DEFAULT em todos os modos write (planejar NAO grava JSON/XLSX;
  propor NAO faz DELETE+INSERT; aprovar NAO altera status). listar-onda eh
  sempre READ-only (sem dry-run).
  NAO USAR PARA:
  - EXECUTAR pre-etapa em PROD (chama transferencias reais no Odoo) -> use
    `09b_executar_pre_etapa.py` (composicao C3 macro de Skills 1+2; capina-se
    para `orchestrators/pre_etapa_executor.py` em sessao futura quando demanda)
  - Ajustar quant pontual sem pre-etapa -> ajustando-quant-odoo
  - Transferir saldo cross loc+lote (sem ciclo de proposta) ->
    transferindo-interno-odoo
  - Outras ondas do ciclo (Onda 1/2/3/4) -> 04_propor_ajustes.py (operacao viva)
  - Auditoria pos-execucao de saldos -> consultando-quant-odoo
allowed-tools: Read, Bash, Glob, Grep
---

# planejando-pre-etapa-odoo (READ + WRITE banco local — atomo C2)

Skill **minimo viavel** (C1 mineracao ✅ · C2-C5 implementados para 4 modos · C6-C10 conforme uso). Construida em 2026-05-24 capinando os scripts-fonte `03b_planejar_pre_etapa_cd` (READ planner) + `04b_propor_pre_etapa_cd` (WRITE banco local + workflow hash). O executor `09b_executar_pre_etapa` permanece VIVO em `scripts/inventario_2026_05/` pois e **composicao C3 macro** de Skills 1 (`ajustando-quant-odoo`) + 2 (`transferindo-interno-odoo`) com auditoria/paralelizacao — NAO eh atomo desta skill.

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
  7. **EXECUTAR (FORA DESTA SKILL — orquestrador C3 macro compoe Skills 1+2):**
     - **Canary primeiro** (1 produto): `09b_executar_pre_etapa.py --company-id 4 --confirmar --limite 1 --usuario X`
     - **Bulk depois** (todos): `09b_executar_pre_etapa.py --company-id 4 --confirmar --usuario X`

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
```

## Validacao

Skill **construida em 2026-05-24** (sessao "Skill 6 nasce") capinando 03b + 04b:
- C1: 3 scripts-fonte minerados integral (`03b_planejar_pre_etapa_cd`, `04b_propor_pre_etapa_cd`, `09b_executar_pre_etapa`) + decisao D007 + 13 testes existentes lidos.
- C2: service `app/odoo/estoque/scripts/pre_etapa.py` (capinado de `app/odoo/services/`) estendido com 7 helpers top-level + 4 constantes do workflow. Shim em `services/`. **19 testes pytest verdes (13 originais preservados via shim + 6 helpers novos cobrindo enriquecer/batch_company/hash).**
- C3: contrato de 4 modos definido (planejar, propor, listar-onda, aprovar-onda).
- C4: SKILL.md com receitas, fluxos 6.1/6.2/6.3, armadilhas, exemplos.
- C5: `scripts/planejar_pre_etapa.py` (CLI 4 modos, `--dry-run` default em modos write, exit codes 0/1/2/4).
- C6: 3 smokes CLI validados (FALHA_INPUT_AUSENTE exit 1, FALHA_USO exit 2, DRY_RUN_OK inputs vazios exit 4); log em `/tmp/log_skill6_C6_validacao_dry_run.json`. Limitacoes documentadas: listar-onda/aprovar-onda em PG local (tabela migrada — sessao futura); batch real com Odoo PROD (scripts 01+02 nao rodaram nesta worktree — sessao futura).
- C7-C10: cross-refs + arquivamento `_validados/planejando-pre-etapa-odoo/` (03b + 04b) + ROADMAP + MAPA_SCRIPTS + folha de fluxo 6.

Mapeamento script-fonte -> atomo no `docs/inventario-2026-05/consolidacao/MAPA_SCRIPTS.md`. Resultado da validacao em `_validados/planejando-pre-etapa-odoo/VALIDACAO.md`.

## NAO-FAZER (red flags)

- ❌ Rodar `propor` antes de `planejar` (FALHA_PLANO_AUSENTE).
- ❌ Rodar `aprovar-onda` sem `listar-onda` antes (FALHA_HASH_DIVERGENTE — hash precisa ser fresh).
- ❌ Executar `09b_executar_pre_etapa.py` antes de `aprovar-onda` (executor exige status=APROVADO).
- ❌ Misturar Ondas: cada `propor` DELETE+INSERT zera apenas a Onda DESTE company_id. Outras ondas (1-4) intactas.
- ❌ Passar `--complementar=fb` apos FB ja ter passado pela propria pre-etapa SEM filtrar quants_fb_raw para conter so MIGRAÇÃO (caller decide).
- ❌ Editar ajustes APROVADO manualmente — quebra a auditoria do hash; refazer o ciclo planejar→propor→listar→aprovar.
- ❌ Confiar em `custo_medio=0` para positivos puros — pode indicar quants sem value (D004 ignorou). Revisar manualmente.
