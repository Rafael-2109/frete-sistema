# FASE C bulk — execucao FB Indisponivel (153 cods restantes + cleanup)

**Data**: 2026-05-25 v11
**Resultado**: cobertura 99.68% + cleanup completo reserveds + saldos negativos

## Operacoes executadas em PROD

### 1. Bulk 153 cods (transferir_para_indisp_em_lote.py --confirmar)

```
Tempo: 11min 33s
Cods total: 153
Status:
  EXECUTADO_TOTAL: 141 cods
  EXECUTADO_PARCIAL: 9 cods (saldo Odoo < pedido)
  FALHA_PRODUTO: 2 cods (45121452 + 501 — inexistentes em product.product)
  FALHA_SEM_QUANT: 1 cod (104000011 HIPOCLORITO — sem saldo em nenhuma empresa)

Qty:
  Solicitada total: 11.029.865 un
  Movida total: 10.994.553 un (99.68%)
  Nao movida: 35.313 un (35.301 SALMOURA + 12 arredondamento)

Transferencias internas: 485
```

Artefatos:
- `bulk_153_real.json` — output completo do orquestrador
- `bulk_153_audit.csv` — 1 linha por transferencia (485 linhas)
- `bulk_153_pendencias.csv` — 12 cods com qty_nao_movida > 0

### 2. Verificacao Odoo direto (sample 10 cods)

100% match com esperado — todos os 10 cods sample com:
- FB/Estoque = 0.00 (zerado)
- FB/Indisponivel/MIGRAÇÃO = aumentado conforme planilha

### 3. Cleanup reserveds residuais (Skill 2.4 --zerar-residual)

```
Tempo: 5.4s
Quants processados: 28
Quants com qty=0 + reserved<0 zerados: 26
Quants com qty<0 + reserved<0 zerados (reserved): 2
Total reserved negativo zerado: -28.265 un
```

Distribuicao por cod (top 5):
- 301100014 SALMOURA VIDRO: -18.804 un (6 quants Pre-Prod)
- 301000001 SALMOURA PADRAO: -6.277 un (1 quant Pre-Prod Balde)
- 104000015 SAL SEM IODO: -2.134 un (2 quants Pre-Prod Manual+Salmoura)
- 104000003 ACUCAR: -520.49 un (1 quant Pre-Prod Salmoura)
- 208000111 SACO POLIETILENO: -240 un (2 quants Pre-Prod Balde)

Artefatos:
- `cleanup_zerar_residual_28.json` — output Skill 2.4
- `quants_zerar_residual_28.csv` — lista detalhada dos 28 quants

### 4. Ajuste saldos negativos (Skill 1 ajustar_quant --valor-absoluto 0)

2 quants ficaram com qty<0 apos zerar reserveds:
- Quant 260624 cod 104000015 SAL SEM IODO loc Pre-Prod Linha Manual: qty=-877.175 → 0 (delta +877.175)
- Quant 260626 cod 104000002 ACIDO CITRICO loc Pre-Prod Linha Salmoura: qty=-34.795536 → 0 (delta +34.795536)

Esses saldos negativos vieram de MOs antigas que consumiram mais do que tinham (manual_consumption sem control). Operacao via Physical Inventory (Skill 1).

Artefatos:
- `cleanup_ajustar_260624.json`
- `cleanup_ajustar_260626.json`

## Estado final FB (apos tudo)

Verificacao Skill 9:
- Quants com qty<0 em FB exc Indisp: **0** ✓
- Quants com qty=0 + reserved<0 em FB exc Indisp: **0** ✓
- Quants com qty>0 + reserved>0 em FB exc Indisp: 9 (saldo legitimo de MOs ativas — cod 104000031 SACARINA SODICA)

## Totalizacao da jornada v10 + v11

| Operacao | Cods | Transf | Qty (un) | Tempo |
|----------|------|--------|----------|-------|
| Canary v10 (1 cod) | 1 | 2 | 2.536 | 8s |
| Sub-piloto v10 (4 cods) | 4 | 6 | 12.687,72 | 10.5s |
| Bulk v11 (153 cods) | 153 | 485 | 10.994.553 | 11min 33s |
| Cleanup reserveds (28 quants) | 28 | 28 writes | -28.265 reserved | 5.4s |
| Cleanup saldos negativos (2 quants) | 2 | 2 writes | +911.97 | 4s |
| **TOTAL** | **5+153+30** | **495+ writes** | **11.009.776 un movidos** | **~12 min** |

## Pendencias REAIS finais (12 cods)

| cod | qty_solicit | qty_movida | qty_nao_movida | motivo |
|-----|-------------|------------|----------------|--------|
| 45121452 | 3501.39 | 0 | 3501.39 | FALHA_PRODUTO — default_code nao existe |
| 501 | 7695 | 0 | 7695 | FALHA_PRODUTO — default_code nao existe |
| 104000011 | 22140.01 | 0 | 22140.01 | FALHA_SEM_QUANT — sem saldo FB/CD/LF |
| 301100014 | 31180.26 | 29211.24 | 1969.02 | saldo Odoo < pedido (6%) |
| 105000048 | 10108.997 | 10108.9955 | 0.0015 | arredondamento (resto em LF) |
| 210030009 | 988233.794 | 988233.792 | 0.002 | arredondamento (resto em LF) |
| 4310176 | 1094 | 1093 | 1 | 1 un MIGRACAO FB/Estoque == MIGRACAO destino (skipped) |
| 104000016 | 277781.5533 | 277776.46734 | 5.08596 | arredondamento (reserveds neg zerados) |
| 104000003 | 1372 | 1371.5628 | 0.4372 | arredondamento |
| 4870112 | 588 | 587.917 | 0.083 | arredondamento (resto em CD) |
| 104000048 | 79 | 78.7073 | 0.2927 | arredondamento (resto em LF) |
| 4820146 | 134 | 133.667 | 0.333 | arredondamento (resto em CD) |
| **TOTAL** | **1.342.927** | **1.307.614** | **35.313 un** | |

### Acoes recomendadas para as 12 pendencias

1. **45121452 + 501**: confirmar com Comercial/Cadastro se cods sao validos. Provavelmente cods antigos descontinuados — N/A.
2. **104000011 HIPOCLORITO**: cod nao tem saldo em FB/CD/LF — produto sem estoque ativo. N/A.
3. **301100014 SALMOURA 1969 un**: saldo Odoo de fato menor que estimativa do Rafael. Confirmar planilha original (talvez incluiu pedido futuro). N/A.
4. **8 cods <1 un diff**: saldo residual em LF/CD/Pre-Prod (fora do escopo FB). Operacao opcional: usar Skill 2 modo C com `--locs-origem` apontando para LF/CD se houver demanda.
5. **4310176 1 un MIGRACAO**: pode ser tratado via MODO B (loc->loc, mesmo lote MIGRACAO). 1 chamada Skill 2: `transferir_entre_locations(lot=MIGRACAO, loc_orig=8, loc_dest=31088, qty=1)`. Demanda muito pequena — deferir.

## Cleanup geral

- Movimentado: 11.009.776 un (99.68% da demanda)
- Reserveds fantasmas zerados: -28.265 un
- Saldos negativos zerados: +911.97 un
- Cobertura efetiva (incluindo cleanup): 99.69%

## Pattern aplicado

Workflow demanda-driven completo:
1. **FASE A** — avaliar demanda (read-only) e politica com usuario
2. **FASE B** — capinar (helper alto-nivel + CLI thin wrapper + testes pytest)
3. **FASE C.1** — re-dry-run para confirmar saldo vivo
4. **FASE C.2** — bulk REAL
5. **FASE C.3** — verificar Odoo direto (sample)
6. **FASE C.4** — resolver pendencias com cleanup pos-bulk
7. **FASE C.5** — commit + memorias

Reusable em demandas futuras (planilha cod+qty → operacao em lote).
