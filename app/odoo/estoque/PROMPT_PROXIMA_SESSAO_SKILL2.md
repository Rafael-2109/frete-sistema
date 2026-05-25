# PROMPT_PROXIMA_SESSAO_SKILL2 — FASE C bulk (153 cods restantes) + 12 pendencias

> **Sessao seguinte ao v10** (commit `b10e6653`): Skill 2 ja MATURADA com
> helper `distribuir_para_indisponivel` + CLI alto-nivel `transferir_para_indisp_em_lote.py`.
> Canary 5 cods PROD validado (15.224 un movidas). Falta executar bulk dos
> 153 cods restantes + resolver 12 pendencias.

> **Qual PROMPT usar?** Se FASE C bulk EXECUTADA com sucesso: usar
> `PROMPT_PROXIMA_SESSAO.md` (geral). Se ainda houver pendencias para
> processar: continuar este (`PROMPT_PROXIMA_SESSAO_SKILL2.md`).

---BEGIN---

Continue o trabalho do orquestrador-Odoo. Worktree: `/home/rafaelnascimento/projetos/frete_sistema_estoque_odoo` (branch `feat/estoque-odoo`, **commits ao fim de v10: bf53ea84 (v7) + 507e5e36 (v7-extras) + 4e30c468 (v8) + 6a73c6fa (v9 Skill 6 orchestrator) + 9fc7e712 (v9 code-review fixes) + 448ea62e (v9 docs PROMPT) + 79676cc1 (v10 PROMPT_SKILL2 inicial) + c73a6020 (v10 PROMPT regra) + b10e6653 (v10 Skill 2 distribuir + canary 5 cods PROD) sobre `main`@b4f7b24c**). `main` continua VIVO em paralelo — verificar avançou e considerar rebase incremental ANTES de iniciar.

## Setup OBRIGATÓRIO (worktree sem .env)

```bash
cd /home/rafaelnascimento/projetos/frete_sistema_estoque_odoo
source /home/rafaelnascimento/projetos/frete_sistema/.venv/bin/activate
set -a; . <(grep -E '^(DATABASE_URL|ODOO_)' /home/rafaelnascimento/projetos/frete_sistema/.env); set +a
```

## 🎯 OBJETIVO desta sessão (curta)

**Executar bulk dos 153 cods restantes da demanda v10** (saldo VIVO FB → FB/Indisponivel + MIGRAÇÃO POR PRODUTO). Depois decidir o que fazer com as 12 pendencias documentadas.

**Tempo estimado**: 30-60 min total (5-10 min execucao bulk + verificacao Odoo + analise pendencias + commit).

---

## 📋 PROTOCOLO DA SESSÃO

### 🔵 FASE C.1 — Re-confirmacao dry-run (saldo pode ter mudado)

Saldo Odoo eh vivo — outros operadores podem ter alterado entre v10 e agora.
Rodar dry-run novo da planilha restante:

```bash
python .claude/skills/transferindo-interno-odoo/scripts/transferir_para_indisp_em_lote.py \
    --planilha docs/inventario-2026-05/v10-skill2-indisp-em-lote/demanda_restantes_153.csv \
    --empresa FB \
    --resetar-reserva-origem \
    --csv-out /tmp/dry_run_153_audit.csv \
    --csv-pendencias /tmp/dry_run_153_pendencias.csv \
    --quiet > /tmp/dry_run_153.json
```

**Inspecionar sumario**: comparar `cods_por_status` com o esperado:
- ~140 DRY_RUN_OK
- ~9 DRY_RUN_PARCIAL (arredondamento + salmoura)
- 2 FALHA_PRODUTO (45121452 + 501)
- 1 FALHA_SEM_QUANT (104000011)

Se houver diferenca SIGNIFICATIVA (ex.: novos FALHA_SEM_QUANT, novos parciais grandes), PARAR e investigar — pode ter ocorrido movimentacao paralela. Re-verificar com Rafael.

### 🟢 FASE C.2 — Executar bulk

Se dry-run consistente com esperado, EFETIVAR:

```bash
time python .claude/skills/transferindo-interno-odoo/scripts/transferir_para_indisp_em_lote.py \
    --planilha docs/inventario-2026-05/v10-skill2-indisp-em-lote/demanda_restantes_153.csv \
    --empresa FB \
    --resetar-reserva-origem --confirmar \
    --csv-out /tmp/real_153_audit.csv \
    --csv-pendencias /tmp/real_153_pendencias.csv \
    --quiet > /tmp/real_153.json
```

**Tempo esperado**: 5-10 min (~2-3s por transferencia, ~493 transferencias estimadas).

**Monitorar exit code**: 0 = total OK, 1 = alguma falha/parcial (esperado por causa das 12 pendencias).

### 🟡 FASE C.3 — Verificar Odoo direto (regra inviolavel 6)

Sample 10 cods aleatorios via Skill 9:

```bash
python .claude/skills/consultando-quant-odoo/scripts/consultar_quants.py \
    --modo quants --empresas "FB" --incluir-qty-zero --quiet --formato tabela \
    --cods "105000014,210842105,210833105,210881116,210841125,209751213,3800011,209029913,210030214,209029912"
```

Esperado: FB/Estoque zerado para esses cods (qty=0 nos lotes que foram drenados) + FB/Indisp MIGRACAO acrescido.

### 🟣 FASE C.4 — Resolver pendencias (opcional, decidir com Rafael)

Os 12 cods em `/tmp/real_153_pendencias.csv` exigem decisao:

1. **2 FALHA_PRODUTO** (`45121452`, `501`):
   - cods nao existem em product.product — confirmar com Rafael se sao cods antigos/erro de digitacao.
   - Acao: marcar como N/A, sem movimento.

2. **1 FALHA_SEM_QUANT** (`104000011 HIPOCLORITO DE SODIO`):
   - Sem saldo em FB/CD/LF (qty=0 em todos os lotes).
   - Acao: marcar como N/A (nada a mover).

3. **9 DRY_RUN_PARCIAL** (8 arredondamento + 1 salmoura):
   - 8 com diff <1 un: arredondamento — confirmar com Rafael se quer mover o residual via Skill 1 (ajustar_quant) ou aceitar parcial.
   - 1 SALMOURA `301100014` com diff ~1969 un (~6%): saldo Odoo realmente menor que pedido. Acao: confirmar com Rafael (talvez planilha tinha estimativa, saldo real eh o que tem).

### 🔵 FASE C.5 — Commit + Atualizar PROMPT

Apos FASE C completa:
- Commit consolidado: "feat(estoque): v11 — bulk 153 cods FASE C executada"
- Atualizar `PROMPT_PROXIMA_SESSAO.md` (geral, NAO _SKILL2) para v12 ou v11.
- Arquivar `PROMPT_PROXIMA_SESSAO_SKILL2.md` (este) ou mover para `_validados/` com nota de "fechado".
- Dizer ao Rafael: "Proxima sessao = abrir `PROMPT_PROXIMA_SESSAO.md` (geral) para outras maturacoes (Skill 7? Skill 8? Skill D?)".

---

## ⚠️ REGRAS INVIOLAVEIS aplicaveis (herdadas v7-v9 + v10)

1. **`--dry-run` ANTES de `--confirmar`** sempre.
2. **`delta_esperado` propagado** em todas as chamadas internas a `ajustar_quant`.
3. **PRE-CHECK reserva** — fluxo 2.6 se algum cod tiver reserva legitima de picking ativo (alem do `--resetar-reserva-origem`).
4. **Verificar Odoo DIRETO** apos `--confirmar` (regra 6) — nao confiar so no output JSON.
5. **Stop imediato** se >2 FALHA_AUMENTO no bulk (estado parcial — origem reduzida, destino nao creditado).
6. **CSV de pendencias** documenta tudo — auditoria essencial.

## NÃO-FAZER (red flags v10)

- ❌ Pular dry-run de re-confirmacao (saldo eh vivo).
- ❌ Tentar mover os 3 cods de FALHA (45121452, 501, 104000011) — sem saldo, nada a fazer.
- ❌ Re-executar os 5 cods da v10 (ja zerados em FB/Estoque — vao dar FALHA_SEM_QUANT esperado).
- ❌ Modificar `transfer.py` ou o CLI sem mineracao de novo caso real (regra inviolavel 4 — demanda-driven).
- ❌ Esquecer o `--resetar-reserva-origem` (sem isso, ~28 cods CAT_4 ficam parciais por reserva ativa).

## ARTEFATOS DE REFERENCIA (commit v10 b10e6653)

- `docs/inventario-2026-05/v10-skill2-indisp-em-lote/README.md` — overview completo
- `demanda_completa_158.csv` — planilha original Rafael
- `demanda_restantes_153.csv` — planilha do bulk (sem 5 ja exec)
- `pendencias_dry_run.csv` — 12 cods para revisar manual
- `audit_dry_run.csv` — log dry-run completo (38KB, 491 transferencias)
- `canary1_5cods.json` + `sub_piloto_4cods.json` — resultados PROD validados

---END---
