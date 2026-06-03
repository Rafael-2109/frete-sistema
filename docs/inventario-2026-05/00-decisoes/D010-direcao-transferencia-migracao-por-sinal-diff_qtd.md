<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/inventario-2026-05/00-decisoes/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# D010 — Direção das transferências MIGRAÇÃO baseada no sinal de `diff_qtd`

> **Papel:** D010 — Direção das transferências MIGRAÇÃO baseada no sinal de `diff_qtd`.

## Indice

- [Contexto](#contexto)
- [Regra (INVIOLÁVEL — CORRIGIDA 2026-05-19 08:30 BRT)](#regra-inviolável-corrigida-2026-05-19-0830-brt)
  - [Por que essa é a interpretação correta](#por-que-essa-é-a-interpretação-correta)
- [Implementação (scripts vigentes)](#implementação-scripts-vigentes)
  - [`15_transferencia_para_migracao.py`](#15_transferencia_para_migracaopy)
  - [`15r_transferencia_reversa.py`](#15r_transferencia_reversapy)
  - [Resultado acumulado (2026-05-19 manhã)](#resultado-acumulado-2026-05-19-manhã)
- [Armadilha histórica (evitar)](#armadilha-histórica-evitar)
- [Como aplicar a NOVA execução baseada em MONITOR_DIFF](#como-aplicar-a-nova-execução-baseada-em-monitor_diff)
- [Casos especiais (tratamento)](#casos-especiais-tratamento)
- [Referências cruzadas](#referências-cruzadas)

**Data**: 2026-05-19
**Status**: VIGENTE — SOT para qualquer script que opere sobre planilhas geradas pelo pipeline `monitor/`
**Validado por**: usuário (Rafael) após inflate de 50M un em MIGRAÇÃO FB causado por interpretação incorreta da regra

---

## Contexto

O pipeline `scripts/inventario_2026_05/monitor/` gera planilhas `MONITOR_DIFF_<timestamp>.xlsx` com a coluna `diff_qtd` calculada em `4_gerar_diffs.py:77`:

```python
diff_qtd = qtd_teorica - qtd_odoo_atual
```

- `qtd_teorica` = saldo do inventário físico em 16/05/2026 + movs entrada - movs saída (até a geração do monitor)
- `qtd_odoo_atual` = saldo atual no Odoo (`stock.quant.quantity` agregado por filial+cod+lote)

Quando o agente recebe planilhas derivadas (`TRANS PARA MIGRAÇÃO.xlsx`, `transf para MIGRAÇÃO.xlsx`) ou opera diretamente sobre a aba `5_Diff_Por_Lote` do MONITOR_DIFF, a direção da movimentação é **determinada pelo SINAL** do `diff_qtd`.

---

## Regra (INVIOLÁVEL — CORRIGIDA 2026-05-19 08:30 BRT)

**Interpretação SEMÂNTICA correta** (`diff_qtd = qtd_teorica - qtd_odoo_atual`):

> `diff_qtd` indica a quantidade a ser ALTERADA no lote da linha.
> - `diff_qtd > 0` → lote PRECISA DE quantidade (teórico > atual) → **MIGRAÇÃO supre o lote**
> - `diff_qtd < 0` → lote TEM EXCESSO (teórico < atual) → **lote devolve para MIGRAÇÃO**

| `diff_qtd` | Significado | Operação no Odoo | Efeito |
|-----------|-------------|------------------|--------|
| **`> 0`** | Lote PRECISA DE qty | **`MIGRAÇÃO → lote`** | MIGRAÇÃO perde `diff_qtd`, lote ganha `diff_qtd` |
| **`< 0`** | Lote TEM EXCESSO | **`lote → MIGRAÇÃO`** | lote perde `abs(diff_qtd)`, MIGRAÇÃO ganha `abs(diff_qtd)` |
| **`≈ 0`** | Conciliado | SKIP | — |

**Quantidade efetiva** sempre = `abs(diff_qtd)`. O sinal é APENAS direção.

### Por que essa é a interpretação correta

`qtd_teorica` = saldo esperado (inventário físico + movs)
`qtd_odoo_atual` = saldo registrado no Odoo
`diff_qtd > 0` → teórico > atual → falta qty no Odoo → lote precisa GANHAR
`diff_qtd < 0` → teórico < atual → sobra qty no Odoo → lote precisa PERDER

MIGRAÇÃO funciona como **contrapartida contábil global** — para cada ajuste em lote real, há ajuste oposto em MIGRAÇÃO (mantém saldo total constante por produto).

---

## Implementação (scripts vigentes)

### `15_transferencia_para_migracao.py`
- Filtra `diff_qtd < 0` (4880 linhas na MONITOR_DIFF 2026-05-19_07-58)
- Direção: **`lote_origem → MIGRAÇÃO`** (lote tem excesso, devolve) ✓

### `15r_transferencia_reversa.py`
- Filtra `diff_qtd > 0` (401 linhas na MONITOR_DIFF 2026-05-19_07-58)
- Direção: **`MIGRAÇÃO → lote_origem`** (lote precisa, supre de MIGRAÇÃO) ✓
- Flag `--criar-lote-migracao`: cria lote MIGRAÇÃO com `expiration_date=hoje+1` se não existir

### Resultado acumulado (2026-05-19 manhã)
- Planilha antiga (`transf para MIGRAÇÃO.xlsx`, 4888 linhas, todas `diff_qtd<0`): ~1.901 EXECUTADO
- Planilha nova (`TRANS PARA MIGRAÇÃO.xlsx`, 11.351 linhas):
  - script 15 (diff<0, 11.064 linhas): 9.612 EXECUTADO
  - script 15r (diff>0, 287 linhas): 249 EXECUTADO
- **Total: ~11.762 transferências aplicadas em produção Odoo**

---

## Armadilha histórica (evitar)

Durante a sessão 2026-05-19, houve confusão de terminologia mas a IMPLEMENTAÇÃO sempre esteve correta:

1. **Interpretação inicial (correta) do agente**: `diff_qtd>0 → MIGRAÇÃO supre, diff_qtd<0 → MIGRAÇÃO recebe`. Scripts 15 e 15r foram criados com essa regra.

2. **Mal-entendido verbal**: usuário disse "se for negativo eh destino → origem, Se for positivo eh origem → destino" — agente interpretou ao pé da letra (LOTE DESTINO=MIGRAÇÃO é sempre o "destino" das colunas), o que pareceu INVERTER a regra.

3. **Reconciliação (validação Rafael 2026-05-19)**:
   > "Qdo diff_qtd for > 0, significa q o lote da linha precisa de qtd. Qdo diff<0, significa q tem mais do q deveria. (diff_qtd indica a qtd a ser alterada nesse lote)"
   >
   > "Qtd positiva = migracao → lote da linha"
   > "Qtd negativa = lote da linha → migracao"

A interpretação correta é **SEMÂNTICA** (o sinal indica o que acontece no LOTE da linha), não literal das colunas. Os scripts 15 e 15r já implementam isso corretamente.

**Lição**: ao receber explicações sobre direção, sempre validar com EXEMPLO CONCRETO antes de tomar ação reversa.

---

## Como aplicar a NOVA execução baseada em MONITOR_DIFF

1. Rodar pipeline monitor: `python scripts/inventario_2026_05/monitor/0_pipeline.py`
2. Output em `docs/inventario-2026-05/07-relatorios/MONITOR_DIFF_<ts>.xlsx`
3. Trabalhar com aba **`5_Diff_Por_Lote`** (lotes ATIVOS, sem MIGRAÇÃO)
4. Filtrar `abs(diff_qtd) > 0.01` (linhas com `diff_qtd≈0` são SKIP — já OK)
5. Para cada linha:
   - `diff_qtd > 0`: **`MIGRAÇÃO → lote`** (qty = diff_qtd) — lote precisa
   - `diff_qtd < 0`: **`lote → MIGRAÇÃO`** (qty = abs(diff_qtd)) — lote tem excesso

---

## Casos especiais (tratamento)

| Caso | Descrição | Ação |
|------|-----------|------|
| **`LOTE ORIGEM = 'P-15/05'`** | Proxy criado para "sem lote" (lot_id=False) | Operar sobre `lot_id=False` no Odoo, não lote nominal |
| **Lote `LOTE ORIGEM` não existe** | Lote físico mas não cadastrado no Odoo | Criar `stock.lot` antes da operação |
| **Lote MIGRAÇÃO não existe** | Produto novo | Criar com `expiration_date=hoje+1` (flag `--criar-lote-migracao`) |
| **MIGRAÇÃO sem saldo livre para diff<0** | Produto não tinha MIGRAÇÃO antes | Permitir saldo negativo OU SKIP (depende da config `allow_negative` do produto) |
| **Lote 100% reservado em pickings antigos** | Lote real com saldo todo reservado por pickings fantasmas | Cancelar pickings antes (script 16) |
| **`cobertura = SO_ODOO`** sem lote (NaN) | Quants sem identificação no Odoo, sem contagem física | Fora do escopo automático — análise manual |

---

## Referências cruzadas

- `monitor/4_gerar_diffs.py:77` — fonte da fórmula
- `monitor/_comum.py:LOTES_PROXY_VAZIO` — convenção P-15/05
- `scripts/inventario_2026_05/15_transferencia_para_migracao.py` — script para `diff<0`
- `scripts/inventario_2026_05/15r_transferencia_reversa.py` — script para `diff>0`
- `scripts/inventario_2026_05/16_cancelar_pickings_fantasmas.py` — pré-requisito quando lotes 100% reservados
- D004 — rename lote FIFO ate cobrir inv + diferença líquida
- D005 — MIGRAÇÃO como consolidador
- D006 — TRANSFERIR vs RENOMEAR (escolha do D005)
