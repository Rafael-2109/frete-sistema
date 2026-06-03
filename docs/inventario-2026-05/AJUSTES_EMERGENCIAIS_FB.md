<!-- doc:meta
tipo: scratch
camada: L3
sot_de: —
hub: docs/inventario-2026-05/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# Ajustes emergenciais FB — 2026-05-18

**Status**: PROPOSTO (não registrado na base, não executado no Odoo)
**Empresa**: FB (`company_id=1`)
**Modalidade**: Transferência interna no Odoo (sem NF), lote DE → lote PARA
**Solicitante**: Rafael (mensagem 2026-05-18)
**Origem das quantidades**: lista informada pelo usuário (divergente da planilha COMPILADO INV. 16.05.2026.xlsx em 5 dos 9 itens — ver `PENDENCIAS.md` P4)

---

## 1. Resumo

Aplicar **antecipadamente** 9 transferências internas na FB para alinhar saldo físico ↔ Odoo nos lotes informados, fora do fluxo D004 cross-company da onda 1. Os lotes PARA seguem padronização parcial (`MI ` com espaço — ver `01-premissas/PADRONIZACAO_LOTES.md` §4).

**Quando reverter**: ver `PENDENCIAS.md` P2 (após onda 1+2 D004 concluídas e antes da padronização completa P1).

---

## 2. Tabela mestra dos ajustes

> Lote DE proposto: **`MIGRAÇÃO`** (consolidador histórico D004 FB) quando existir, caso contrário lote Odoo com maior saldo disponível.
> Lote DE pode ser substituído por outro lote do mesmo cod desde que saldo ≥ QTD.

| # | Cod | Lote DE (proposto) | Saldo DE (Odoo) | Lote PARA (canônico parcial) | QTD a transferir | Status DE no Odoo |
|---|---|---|---|---|---|---|
| E01 | 104000015 | `MIGRAÇÃO` | 290.520,63 | `MI 027-098/26` | 1.175 | OK (saldo ≫ QTD). Lote PARA já existe Odoo c/ 29.000 |
| E02 | 104000002 | `MIGRAÇÃO` | 24.054,00 | `MI 036-124/26` | 143,5 | **VERIFICAR**: lote PARA não está no inventário FB |
| E03 | 104000004 | `MIGRAÇÃO` | 16.553,83 | `MI 025-091/26` | 53 | OK (substitui `MI 025.091/26` planejado — separador `.` → `-`) |
| E04 | 104000018 | `MIGRAÇÃO` | 1.872,80 | `MI 168-349/25` | 35,4 | OK |
| E05 | 104000006 | `MIGRAÇÃO` | 333,88 | `MI 138-311/25` | 6,4 | OK (adiciona espaço em `MI138-311/25`) |
| E06 | 104000016 | `MIGRAÇÃO` | 54.142,51 | `T20241014` | 280,1 | OK (lote PARA já existe Odoo c/ 15.500 — **não tem prefixo MI**, mantém literal) |
| E07 | 104000001 | `MIGRAÇÃO` | 460,08 | `MI 031-092/25` | 6,635 | OK (adiciona prefixo MI ausente em `031-092/25`) |
| E08 | 104000037 | `MIGRAÇÃO` | 1.990,51 | `MI 074-177/25` | 5 | OK (adiciona espaço em `MI074-177/25`) |
| E09 | 104000003 | `0909` (id=39223) | 697,73 | `MI 021-065/26` | 30 | OK (cod sem MIGRAÇÃO; lote `1012/24` original tem 11.530 mas em FB/Pré-Produção/Linha Salmoura, não em FB/Estoque) |
| E10 | 102030201 | `0004/2025` (id=34910) | 179.241,52 | `135/26` | 2.700 | OK (MIGRAÇÃO existe id=30031 mas **fora de FB/Estoque** — está em Virtual/Linhas; lote PARA fora do padrão `MI ###-###/AA`) |

**Total transferido**: 1.733,635 (soma das 9 QTDs; cada cod isolado)

---

## 3. Detalhes por item

### E01 — 104000015 / 1.175 / `MI 027-098/26`

- **DE**: `MIGRAÇÃO` (saldo Odoo 290.520,63) — recomendado
- **PARA**: `MI 027-098/26` (lote PARA já existe Odoo com 29.000 — após ajuste fica 30.175)
- **Padronização aplicada**: usuário citou `MI027-098/26` (sem espaço) → grafia canônica
- **Atenção**: cod tem TAMBÉM lote `MIGRACAO` (sem cedilha) com 34.643,12 — diferente do `MIGRAÇÃO`. Confirmar qual é o DE no Odoo UI

### E02 — 104000002 / 143,5 / `MI 036-124/26`

- **DE**: `MIGRAÇÃO` (saldo Odoo 24.054)
- **PARA**: `MI 036-124/26` (com espaço)
- **PROBLEMA**: este lote **não foi inventariado na FB** (ausente em `ajuste_estoque_inventario` ciclo INVENTARIO_2026_05 cid=1). Implicações:
  - Lote PARA pode não existir como `stock.lot` no Odoo — talvez precise criar
  - Confirmar antes de transferir: `odoo.search_read('stock.lot', [['product_id.default_code', '=', '104000002'], ['name', 'ilike', '036-124']])`
- **Padronização aplicada**: usuário citou `MI036-124/26` (sem espaço) → canônico

### E03 — 104000004 / 53 / `MI 025-091/26`

- **DE**: `MIGRAÇÃO` (saldo Odoo 16.553,83)
- **PARA**: `MI 025-091/26` (hífen, não ponto)
- **Atenção**: planilha original tem este lote com 14,4 unidades em `MI 025.091/26` (com PONTO). Após o ajuste emergencial:
  - Lote `MI 025.091/26` (planejado RENOMEAR_LOTE para 14,4) **continuará no plano**
  - Lote `MI 025-091/26` (PARA emergencial) **passa a existir paralelamente** com 53
  - Resolver na padronização completa (P1): consolidar ambos

### E04 — 104000018 / 35,4 / `MI 168-349/25`

- **DE**: `MIGRAÇÃO` (saldo Odoo 1.872,80)
- **PARA**: `MI 168-349/25` (já é canônico — só copia)
- **Atenção**: planilha original tem 7 lotes Odoo (0409/24, 2207/24, 0908/24, 3107/24, 2708/24, 2507/24, 1908/24, 3007/24) RENOMEAR_LOTE somando 533,01 para este lote inv. Após ajuste emergencial, esse RENOMEAR_LOTE continua planejado — fica saldo PARA = 35,4 (emergencial) + 533,01 (D004 onda 4) = 568,41

### E05 — 104000006 / 6,4 / `MI 138-311/25`

- **DE**: `MIGRAÇÃO` (saldo Odoo 333,88)
- **PARA**: `MI 138-311/25` (com espaço — usuário citou `MI138-311/25` sem espaço)
- **Atenção**: planilha original tem 77,69 em `MI138-311/25` (sem espaço, RENOMEAR_LOTE do `2507/24`). Após emergencial, ficam 2 grafias paralelas no Odoo até P1 consolidar

### E06 — 104000016 / 280,1 / `T20241014`

- **DE**: `MIGRAÇÃO` (lot_id=30079, saldo 54.142,51 em FB/Estoque loc 8)
- **PARA**: `T20241014` (lot_id=17057 já existe — **não é lote MI**, não aplica padronização do §4 PADRONIZACAO_LOTES.md)
- **Achado dry-run**: lote PARA (id=17057) tem saldo **15.500 em `FB/Pré-Produção/Linha Salmoura` (loc 27458)** + saldo zero em FB/Estoque (loc 8). Após emergencial:
  - Quant NOVO em FB/Estoque com 280,1 para lote 17057
  - Quant existente em Salmoura permanece 15.500
  - **Total geral lote 17057 = 15.780,1** (em 2 locations diferentes)
- **Conflito com plano D004**: existe `INDISPONIBILIZAR_LOTE` planejado para zerar (qtd_inv 280,1 vs qtd_odoo 15.500 → ajuste -15.219,9). Após emergencial:
  - Saldo Odoo total do lote = 15.780,1 (15.500 Salmoura + 280,1 FB/Estoque)
  - Plano D004 ficou INVÁLIDO — recalcular ou aceitar drift (ver `PENDENCIAS.md` P5)

### E07 — 104000001 / 6,635 / `MI 031-092/25`

- **DE**: `MIGRAÇÃO` (saldo Odoo 460,08)
- **PARA**: `MI 031-092/25` (prefixo MI adicionado, usuário citou `MI031-092/25`; planilha tem `031-092/25` sem MI)
- **Atenção**: planilha original tem 31,635 em `031-092/25` (RENOMEAR_LOTE em 3 lotes legados: 22/08, 31/07, 0208/24). Após emergencial, fica grafia paralela `MI 031-092/25` vs `031-092/25` (RENOMEAR_LOTE pendente)

### E08 — 104000037 / 5 / `MI 074-177/25`

- **DE**: `MIGRAÇÃO` (saldo Odoo 1.990,51)
- **PARA**: `MI 074-177/25` (com espaço)
- **Atenção**: planilha original tem 3,676 em `MI074-177/25` (sem espaço, RENOMEAR_LOTE em `2207/24` + `2507/24`). Após emergencial: 2 grafias paralelas

### E10 — 102030201 (AZEITONA VERDE FATIADA) / 2.700 / `135/26`

- **Produto**: cod 102030201, product_id=29788, ativo, name="AZEITONA VERDE FATIADA"
- **DE**: `0004/2025` (lot_id=34910, saldo livre 179.241,52 em FB/Estoque loc 8 — maior saldo livre disponível)
- **PARA**: `135/26` (lot_id=57351, criado nesta execução)
- **QTD**: 2.700 → saldo final do `135/26` = 2.700
- **MIGRAÇÃO desse cod (id=30031, total 161.230)**: distribuído em outras locations — **não há saldo em FB/Estoque (loc 8)**:
  - Estoque Virtual/Ajuste de Inventario (loc 14): -808.336 (saldo negativo virtual)
  - Estoque Virtual/Produção (loc 15): +659.097 livre
  - FB/Pré-Produção/Linha Vidro (loc 4066): 2.471 (toda reservada)
  - FB/Pré-Produção/Linha Balde (loc 4068): 144.215 (42.258 livre)
  - FB/Pré-Produção/Linha Manual (loc 4067): 14.544 (498 livre)
  - Parceiros/Clientes (loc 5): 140
- **Padronização não aplicada**: lote `135/26` informado pelo usuário tem só `n2/AA` (sem `n1`), **fora do padrão `MI ###-###/AA`**. Caso similar ao `MI 46 - 197/24` (n1=2 dígitos) — vai para revisão manual na padronização completa P1
- **Pickings ativos**: nenhum lote desse cod em loc 8 está reservado (todos os top 10 têm `LIVRE=qty`). Não há problema de reserva como cod 104000003

### E09 — 104000003 / 30 / `MI 021-065/26`

- **DE**: `0909` (lot_id=39223, saldo 697,73 em FB/Estoque loc 8)
  - **Mudança vs proposta inicial**: lote `1012/24` (lot_id=23189) tem 11.530 unidades, mas em `FB/Pré-Produção/Linha Salmoura` (loc 27458), **não em FB/Estoque (loc 8)**. Como a transferência interna opera em loc 8, foi escolhido `0909` (maior saldo legado em FB/Estoque)
- **PARA**: `MI 021-065/26` (com espaço — planilha tem `MI 021-065/26` em RENOMEAR_LOTE do `2708/24`)
- **Atenção**: planilha já tem este lote inv com 30 em RENOMEAR_LOTE → conflito potencial. Após emergencial: lote PARA fica com 30 (emergencial); RENOMEAR_LOTE de `2708/24`→`MI 021-065/26` ainda pendente adicionaria mais 30 → total 60. **Confirmar se intenção é manter só 30 ou substituir**

---

## 4. Procedimento Odoo (transferência interna)

**Tipo de operação**: `stock.picking` com `picking_type_id` = transferência interna FB

> ID do picking type interno FB: consultar `IDS_FIXOS.md` (não memorizado aqui — pode ter mudado)

**Localização DE**: `Estoque FB` (verificar `stock.location.id` no UI)
**Localização PARA**: `Estoque FB` (mesma — apenas muda lote, não local)

### Passos Odoo UI

1. Operações > Transferências > Criar
2. Tipo: Transferência Interna (FB)
3. Origem: `INVENTARIO_2026_05/AJUSTE_EMERGENCIAL/<E01..E09>`
4. Linha de movimento:
   - Produto: cod_produto
   - Quantidade: QTD
   - De: Estoque FB / Lote DE
   - Para: Estoque FB / Lote PARA (criar `stock.lot` PARA se não existir, com nome canônico)
5. Confirmar → Reservar → Validar
6. Anotar `picking.name` (ex: `WH/INT/00XXX`) na coluna "Picking executado" da tabela abaixo

### Via XML-RPC (script alternativo)

> **NÃO CRIAR SCRIPT AINDA** — pendência de aprovação. Padrão referenciado em `app/odoo/services/stock_picking_service.py`.

```python
# Pseudocódigo — não executar
picking_vals = {
    'picking_type_id': PICKING_TYPE_INTERNAL_FB,
    'location_id': LOC_ESTOQUE_FB,
    'location_dest_id': LOC_ESTOQUE_FB,
    'origin': f'INVENTARIO_2026_05/AJUSTE_EMERGENCIAL/E{n:02d}',
    'company_id': 1,
}
move_vals = {
    'product_id': product_id,
    'product_uom_qty': qtd,
    'location_id': LOC_ESTOQUE_FB,
    'location_dest_id': LOC_ESTOQUE_FB,
    'lot_id': lot_id_DE,  # stock.lot existente
    # lote PARA criado em move_line após action_assign
}
```

---

## 5. Registro de execução

**Execução**: 2026-05-18 14:29 UTC via `scripts/inventario_2026_05/10_executar_emergenciais_fb.py --confirmar`
**Método**: `StockInternalTransferService.transferir_quantidade_para_lote()` (inventory adjustment, gera 1 stock.move automático com origem "Physical Inventory" em loc 8 FB/Estoque)

| # | Cod | Lote DE (id) | Lote PARA (id) | QTD | quant_origem_id | quant_destino_id | Saldo DE pós | Saldo PARA pós | Criou lote? | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| E01 | 104000015 | `MIGRAÇÃO` (30078) | `MI 027-098/26` (53776) | 1.175 | — | — | 290.520,63 - 1.175 = 289.345,63 | 29.000 + 1.175 = 30.175 | não (já existia) | **EXECUTADO** |
| E02 | 104000002 | `MIGRAÇÃO` (30070) | `MI 036-124/26` (57344) | 143,5 | — | — | 24.054 - 143,5 = 23.910,5 | 0 + 143,5 = 143,5 | **SIM** | **EXECUTADO** |
| E03 | 104000004 | `MIGRAÇÃO` (30072) | `MI 025-091/26` (57345) | 53 | — | — | 16.553,83 - 53 = 16.500,83 | 0 + 53 = 53 | **SIM** | **EXECUTADO** |
| E04 | 104000018 | `MIGRAÇÃO` (30080) | `MI 168-349/25` (57346) | 35,4 | — | — | 1.872,80 - 35,4 = 1.837,40 | 0 + 35,4 = 35,4 | **SIM** | **EXECUTADO** |
| E05 | 104000006 | `MIGRAÇÃO` (30073) | `MI 138-311/25` (57347) | 6,4 | 116760 | 229227 | 333,879 - 6,4 = 327,479 | 0 + 6,4 = 6,4 | **SIM** | **EXECUTADO** |
| E06 | 104000016 | `MIGRAÇÃO` (30079) | `T20241014` (17057) | 280,1 | 116772 | 229229 | 54.142,51 - 280,1 = 53.862,41 | 0 + 280,1 = 280,1 *em loc 8* (15.500 em Salmoura permanece) | não (existia em outra loc) | **EXECUTADO** |
| E07 | 104000001 | `MIGRAÇÃO` (30069) | `MI 031-092/25` (57348) | 6,635 | 116752 | 229231 | 460,076 - 6,635 = 453,441 | 0 + 6,635 = 6,635 | **SIM** | **EXECUTADO** |
| E08 | 104000037 | `MIGRAÇÃO` (30089) | `MI 074-177/25` (57349) | 5 | 116792 | 229233 | 1.990,51 - 5 = 1.985,51 | 0 + 5 = 5 | **SIM** | **EXECUTADO** |
| E09 | 104000003 | — (ajuste de inventário puro) | `MI 021-065/26` (57350) | 30 | n/a | 229239 | n/a | 0 + 30 = 30 | não (criado em tentativa anterior) | **EXECUTADO via inventory adjustment** (14:38) |
| E10 | 102030201 | `0004/2025` (34910) | `135/26` (57351) | 2.700 | 135942 | 229248 | 179.241,52 - 2.700 = 176.541,52 | 0 + 2.700 = 2.700 | **SIM** | **EXECUTADO** (15:00, tempo 1.453ms) |

### 5.1 — E09 RESOLVIDO: ajuste de inventário puro (decisão usuário D, 2026-05-18 14:38)

**Tentativas anteriores (registradas para auditoria)**:

1. **Lote DE `1012/24` (id=23189)**: saldo total Odoo 11.530,2584 — mas em `FB/Pré-Produção/Linha Salmoura` (loc 27458), **não em FB/Estoque (loc 8)**. Script roda em loc 8 → lote não encontrado lá.
2. **Lote DE `0909` (id=39223)**: saldo 697,728 em FB/Estoque — **100% reservado em pickings ativos**. RuntimeError:
   > `Quant origem 155645 tem 697.728 un reservadas em pickings ativos. Saldo apos transferencia (667.728) ficaria < reserva.`
3. **Auditoria geral**: TODOS os 14 lotes top do cod 104000003 em FB/Estoque com qty > 30 estão **100% reservados** (`livre=0`).

**Causa raiz**: 19 pickings antigos (mais antigo de 09/09/2025, mais recente de 22/04/2026) em `state=assigned` reservaram todo estoque. Origens são cotações `C25.../C26...` ou ordens de produção `FB/OP/SALMOURA/...` que nunca foram validadas — possivelmente esquecidas/abandonadas. Lista completa em §6.

**Decisão**: opção D — **ajuste de inventário puro** (entrada nova de 30 un sem consumir outro lote). Equivale ao que faria operador na UI do Odoo: "Inventory > Physical Inventory > Adicionar linha".

**Execução real (2026-05-18 14:38 UTC)**:

```python
# 1. Garantir stock.lot existe
lot_id, criado = lot_svc.criar_se_nao_existe('MI 021-065/26', 30490, 1)
# Resultado: lot_id=57350, criado_agora=False (já existia da tentativa #2 acima — o
# StockInternalTransferService cria o lote ANTES de tentar a transferência, e
# permanece órfão após a falha. Reusado aqui.)

# 2. Criar quant em FB/Estoque com inventory_quantity=30
quant_id = odoo.create('stock.quant', {
    'product_id': 30490, 'company_id': 1, 'location_id': 8,
    'lot_id': 57350, 'inventory_quantity': 30,
})
# Resultado: quant_id=229239

# 3. Aplicar inventário (gera stock.move automático)
odoo.execute_kw('stock.quant', 'action_apply_inventory', [[229239]])
```

**Stock.move gerado**:
- `move_id=1098999`
- `date=2026-05-18 17:38:12`
- `Estoque Virtual/Ajuste de Inventario` (loc 14) → `FB/Estoque` (loc 8)
- `qty=30.0`
- `reference="Quantidade de produtos atualizada"`

**Diferença vs E01-E08 (transferência interna)**:

| Aspecto | E01-E08 (transfer interna) | E09 (inventory adjustment) |
|---|---|---|
| Saldo total cod no Odoo | inalterado (só muda lote) | **aumenta em 30 un** |
| Origem do estoque | outro lote físico (MIGRAÇÃO) | "do nada" (Estoque Virtual/Ajuste) |
| Reversão | transferência inversa | inventory adjustment com `inventory_quantity=0` |
| Auditoria | 1 stock.move "Physical Inventory" loc 8 → loc 8 | 1 stock.move "Quantidade de produtos atualizada" loc 14 → loc 8 |

**Implicação fiscal**: aumento de 30 un sem origem documental. Para regularizar contabilmente, precisa lançar ajuste contábil de inventário (não NF). Ver `PENDENCIAS.md` P8 (novo).

---

## 6. Procedimento de reversão

**Quando**: ver `PENDENCIAS.md` P2 (após onda 1+2 D004 concluídas)

**Como**: para cada E01..E09 executado, criar transferência interna **espelho**:

- Origem: `INVENTARIO_2026_05/AJUSTE_EMERGENCIAL/REVERSAO/E<n>`
- DE: lote PARA do ajuste original (mesma quantidade)
- PARA: lote DE do ajuste original

Alternativa: usar `stock.return.picking` wizard sobre o picking original (Odoo gera automaticamente o reverso).

Tabela de reversão (a preencher):

| # | Picking reversão | Data | Validou? |
|---|---|---|---|
| E01 | — | — | — |
| ... | — | — | — |

---

## 5.2 — Atenção: lotes ficaram em FB/Estoque, não em Linha de Pré-Produção

Os 9 lotes pós-emergencial estão em `FB/Estoque (loc 8)`. **Para apontamento de `mrp.production` FB, o estoque precisa estar em `FB/Pré-Produção/Linha XXX`** (Salmoura/Balde/Vidro/Manual/Retrabalho/Industrialização LF — ver `PENDENCIAS.md` P10 para mapa completo).

Se algum desses lotes for usado em produção, Odoo gera automaticamente um picking de embalagem (`FB/FB/EMB/*`) ao confirmar a OP, movendo de FB/Estoque para a Linha correspondente. Ver `PENDENCIAS.md` P10.

---

## 6. Auditoria de contexto E09 — Pickings antigos do cod 104000003

Consulta executada 2026-05-18 14:37 UTC. Filtro: `stock.move.line` com `product_id=30490`, `company_id=1`, `location_id=8`, `state not in ['done','cancel']`. Resultado: 19 pickings ativos.

| picking_id | name | state | origin | create_date | scheduled_date | idade |
|---|---|---|---|---|---|---|
| 272269 | FB/INT/03746 | assigned | C2510312 | 2025-09-09 | 2025-09-09 | **252 dias** |
| 284527 | FB/INT/04228 | assigned | C2511863 | 2025-11-05 | 2025-11-05 | 195 dias |
| 284549 | FB/INT/04242 | assigned | C2511763 | 2025-11-05 | 2025-11-05 | 195 dias |
| 287134 | FB/INT/04322 | assigned | C2512220 | 2025-11-17 | 2025-11-17 | 183 dias |
| 287165 | FB/INT/04328 | assigned | C2512229 | 2025-11-17 | 2025-11-17 | 183 dias |
| 290316 | FB/INT/04468 | assigned | C2512748 | 2025-12-01 | 2025-12-01 | 169 dias |
| 290333 | FB/INT/04472 | assigned | C2512680 | 2025-12-01 | 2025-12-01 | 169 dias |
| 290286 | FB/FB/EMB/09461 | assigned | FB/OP/SALMOURA/04641 | 2025-12-01 | 2025-12-02 | 169 dias |
| 291616 | FB/FB/EMB/09540 | assigned | FB/OP/SALMOURA/04679 | 2025-12-04 | 2025-12-06 | 166 dias |
| 292256 | FB/INT/04537 | assigned | C2512900 | 2025-12-09 | 2025-12-09 | 161 dias |
| 294053 | FB/INT/04658 | assigned | C2513215 | 2025-12-17 | 2025-12-17 | 153 dias |
| 301462 | FB/INT/04932 | assigned | C2614744 | 2026-02-04 | 2026-02-04 | 104 dias |
| 301563 | FB/INT/04936 | assigned | C2614745 | 2026-02-05 | 2026-02-05 | 103 dias |
| 301572 | FB/INT/04944 | assigned | C2614793 | 2026-02-05 | 2026-02-05 | 103 dias |
| 301600 | FB/INT/04946 | assigned | C2614791 | 2026-02-05 | 2026-02-05 | 103 dias |
| 301604 | FB/INT/04950 | assigned | C2614781 | 2026-02-05 | 2026-02-05 | 103 dias |
| 303038 | FB/INT/05014 | assigned | (sem) | 2026-02-18 | 2026-02-18 | 90 dias |
| 308648 | FB/INT/05215 | assigned | (sem) | 2026-03-24 | 2026-03-24 | 56 dias |
| 313308 | FB/INT/05410 | assigned | (sem) | 2026-04-22 | 2026-04-22 | 26 dias |

**Observação**: o picking mais antigo (FB/INT/03746) está reservado há 8+ meses. A reserva mantém o saldo travado em FB/Estoque indefinidamente. Não foi tratado nesta sessão emergencial (decisão usuário D = ajuste de inventário) — fica como nova pendência P8 (rastrear / cancelar / validar esses pickings).

---

## 6.1 Auditoria de contexto E09 — Histórico do lote `1012/24` (id=23189) em Linha Salmoura

Lote tem 11.530,2584 un parados em `FB/Pré-Produção/Linha Salmoura` (loc 27458). Histórico:

| Data | Movimento | Qty | Ref / Origin |
|---|---|---|---|
| 2024-12-10 11:11:59 | **Entrada inicial em Linha Salmoura** | **12.759,20** | `FB/INT/01535` |
| 2025-01-10 15:35:42 | Entrada (FB/Estoque → Salmoura via EMB) | 418,50 | `FB/FB/EMB/04134` (origin `FB/OP/SALMOURA/02052`) |
| 2025-01-18 13:04:04 | Entrada (FB/Estoque → Salmoura) | 129,60 | `FB/FB/EMB/04342` (origin `FB/OP/SALMOURA/02093`) |
| 2025-01-31 17:28:06 | Entrada (FB/Estoque → Salmoura) | 237,60 | `FB/FB/EMB/04688` |
| 2025-01-31 17:30:39 | Entrada (FB/Estoque → Linha Manual) | 18,00 | `FB/FB/EMB/04689` |
| 2025-01-31 17:31:16 | Saída (Linha Manual → Produção) | 18,00 | `FB/OP/MANUAL/00566` |
| 2025-02-03 14:01:59 | Entrada (FB/Estoque → Salmoura) | 81,00 | `FB/FB/EMB/04706` |
| 2025-02-03 14:02:27 | Saída (Salmoura → Produção) | 81,00 | `FB/OP/SALMOURA/02209` |
| 2025-02-05 18:22:59 | Entrada (FB/Estoque → Salmoura) | 770,866 | `FB/FB/EMB/04784` |
| 2025-02-05 18:23:25 | Saída (Salmoura → Produção) | 770,866 | `FB/OP/SALMOURA/02274` |
| 2025-02-19 12:42:08 | Saída (Salmoura → Produção) | 237,60 | `FB/OP/SALMOURA/02348` |
| 2025-11-28 18:21:42 | Saída (Salmoura → Produção) | 26,9196 | `FB/OP/SALMOURA/04555` |
| 2025-12-01 10:48:09 | **Última saída registrada** (Salmoura → Produção) | **846,18** | `FB/OP/SALMOURA/04621` |

**Padrão**: lote entrou em Salmoura em dez/2024, foi sendo consumido por ordens de produção `FB/OP/SALMOURA/...` até dez/2025. Após 01/12/2025, **sem movimentação** — saldo residual de 11.530 un parado há 5,5 meses.

**Implicações**:
- Lote `1012/24` está "esquecido" em Salmoura (sem produção consumindo desde dez/2025)
- Saldo 11.530 não está reservado por picking nenhum
- Era candidato ideal para E09 via transferência interna, mas exigiria mudar location (loc 27458) — bloqueado pela automação por mudança de parâmetro não pré-aprovada
- Em alternativa, decisão D (ajuste de inventário) foi mais simples e auditável

---

## 7. Referências

- `01-premissas/PADRONIZACAO_LOTES.md` — regra canônica `MI ###-###/AA`
- `PENDENCIAS.md` — P1 (padronização completa) + P2 (reverter emergenciais) + P3 (104000002 ausente) + P4 (divergências de quantidade)
- `SOT.md §7.4` — estratégia D004 (RENOMEAR_LOTE + diferença líquida)
- `CHECKPOINT_2026_05_18_LF_FIM_SESSAO2.md` — estado atual do inventário (foco LF)
