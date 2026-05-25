# v10 — Skill 2 `transferindo-interno-odoo` MATURADA (capinada + canary)

**Data**: 2026-05-25
**Branch**: `feat/estoque-odoo` (worktree)

## Contexto

Demanda real do Rafael: planilha CSV com 158 cods FB (apenas `cod`, `qty`, `nome`)
para mover saldo VIVO (FB/Estoque + Pos-Prod + Pre-Prod) para FB/Indisponivel
consolidando em lote MIGRAÇÃO POR PRODUTO.

## Capinagem (Fase B)

1. **Helper `distribuir_para_indisponivel`** adicionado a `app/odoo/estoque/scripts/transfer.py`.
   - Compoe `transferir_para_indisponivel` (modo C atomico) N vezes.
   - Politica MIGRACAO_FIRST_FIFO default + alternativas FIFO/MAIOR_SALDO.
   - Origem default: todas locs internas FB exceto Indisp (8, 48, 4066, 4067, 4068, 27458).
   - Greedy distribute com ValueError-handling (pula quant em pre-cond do atomo).

2. **CLI thin wrapper**: `.claude/skills/transferindo-interno-odoo/scripts/transferir_para_indisp_em_lote.py`.
   - `--planilha CSV_PATH` ou `--cods "C1=Q1,..."` inline.
   - `--dry-run` default; `--confirmar` efetiva.
   - `--csv-out` (audit) + `--csv-pendencias` (cods nao 100%).
   - Exit codes 0/1/2/4.

3. **17 testes pytest novos** em `tests/odoo/services/test_distribuir_para_indisponivel.py`.

4. **SKILL.md atualizado** com nova receita.

5. **Folha de fluxo**: `app/odoo/estoque/fluxos/2.2.j-para-indisponivel-em-lote.md`.

## Execucao parcial (Fase C — 5 de 158 cods)

**Canary + sub-piloto executados nesta sessao** (REAL PROD):

| cod | qty | transferencias | status | tempo |
|-----|-----|----------------|--------|-------|
| 210844125 ROTULO MOSTARDA DIJON | 2.536 | 2 (13203 + 13757) | EXECUTADO_TOTAL | ~3s |
| 3800005 BATELADA DE INGLES | 3.093,72 | 1 (INV-3800005...) | EXECUTADO_TOTAL | ~1,4s |
| 210881114 ROTULO MOLHO BARBECUE | 2.988 | 2 (13203 + 26910) | EXECUTADO_TOTAL | ~2,6s |
| 209751213 ROTULO OLEO MISTO GL | 3.047 | 2 (13201 + 241072) | EXECUTADO_TOTAL | ~2,5s |
| 210030214 CAIXA PAPELAO 220X145X110 | 3.559 | 1 (3208480) | EXECUTADO_TOTAL | ~1,3s |
| **TOTAL** | **15.224 un** | **8 transferencias** | **5/5 OK** | **~18s** |

Verificacao Odoo direta pos-execucao: 100% match com esperado (FB/Estoque
zerado para os lotes origem + FB/Indisp MIGRAÇÃO acrescido das qtds).

## Pendencias para proxima sessao (153 cods restantes)

Arquivos prontos para Rafael continuar (FASE C bulk):

- `demanda_restantes_153.csv` — planilha com os 153 cods que NAO foram executados nesta sessao.
- `pendencias_dry_run.csv` — 12 cods com pendencia em dry-run (PRE-EXECUCAO):
  - **2 FALHA_PRODUTO**: `45121452 COG FAT OUTBACK CX`, `501 AZEITONA VERDE GORDAL` (default_code nao existe no Odoo).
  - **1 FALHA_SEM_QUANT**: `104000011 HIPOCLORITO DE SODIO` (sem saldo em nenhuma empresa).
  - **9 DRY_RUN_PARCIAL**: 8 com diff <1% (arredondamento) + 1 com diff 6% (`301100014 SALMOURA AZEITONA VIDRO PADRAO` — saldo Odoo de fato menor que pedido).

## Comando para Rafael executar bulk em sessao 2

```bash
cd /home/rafaelnascimento/projetos/frete_sistema_estoque_odoo
source /home/rafaelnascimento/projetos/frete_sistema/.venv/bin/activate
set -a; . <(grep -E '^(DATABASE_URL|ODOO_)' /home/rafaelnascimento/projetos/frete_sistema/.env); set +a

# 1. Dry-run novo (saldo mudou desde primeiro dry-run; re-confirmar)
python .claude/skills/transferindo-interno-odoo/scripts/transferir_para_indisp_em_lote.py \
    --planilha docs/inventario-2026-05/v10-skill2-indisp-em-lote/demanda_restantes_153.csv \
    --empresa FB \
    --resetar-reserva-origem \
    --csv-out /tmp/dry_run_153_audit.csv \
    --csv-pendencias /tmp/dry_run_153_pendencias.csv \
    --quiet > /tmp/dry_run_153.json

# 2. Inspecionar sumario
python -c "
import json
d = json.load(open('/tmp/dry_run_153.json'))
print(d['sumario'])
"

# 3. Revisar pendencias (deve ficar parecido com pendencias_dry_run.csv — 11 cods)
cat /tmp/dry_run_153_pendencias.csv

# 4. EFETIVAR bulk (estimativa 5-10 min)
time python .claude/skills/transferindo-interno-odoo/scripts/transferir_para_indisp_em_lote.py \
    --planilha docs/inventario-2026-05/v10-skill2-indisp-em-lote/demanda_restantes_153.csv \
    --empresa FB \
    --resetar-reserva-origem --confirmar \
    --csv-out /tmp/real_153_audit.csv \
    --csv-pendencias /tmp/real_153_pendencias.csv \
    --quiet > /tmp/real_153.json

# 5. Verificar Odoo direto (Skill 9) para sample 10 cods
python .claude/skills/consultando-quant-odoo/scripts/consultar_quants.py \
    --modo quants --empresas "FB" --incluir-qty-zero --quiet --formato tabela \
    --cods "105000014,210842105,210833105,210881114,210841125,209751213,3800011,209029913,210030214,209029912"
```

## Tempo estimado

- Dry-run de re-confirmacao: ~50s
- Real bulk de 153 cods: estimativa **5-10 min** (extrapolando do sub-piloto 4 cods ~10s = 2.5s/cod; 153 cods × 2.5s = ~6 min).
- 12 pendencias resolvidas manual posteriormente (sessao curta separada).

## Garantias do orquestrador

1. `--dry-run` default (sem `--confirmar` so simula).
2. `delta_esperado` propagado em todas as chamadas internas a `ajustar_quant` (regra inviolavel 11).
3. G021/G022/G027/G028/G031 todos codificados no atomo `transferir_para_indisponivel`.
4. ValueError do atomo (pre-cond) NAO quebra o cod inteiro — pula o quant e segue greedy (fix v10).
5. CSV de pendencias documenta tudo que nao moveu 100% — auditoria completa.
