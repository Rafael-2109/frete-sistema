<!-- doc:meta
tipo: state
camada: L3
sot_de: —
hub: docs/inventario-2026-05/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# Pickings pendentes de invoice — Inventario 2026-05

> **Papel:** Pickings pendentes de invoice — Inventario 2026-05.

## Indice

- [Estado atual (2 pickings pendentes)](#estado-atual-2-pickings-pendentes)
  - [Detalhe do 317478 (Onda 2 batch 3a — RecLf 13)](#detalhe-do-317478-onda-2-batch-3a-reclf-13)
  - [Recovery picking 317478](#recovery-picking-317478)
  - [Pickings RESOLVIDOS na sessao 3 tarde](#pickings-resolvidos-na-sessao-3-tarde)
  - [Detalhe do 317346](#detalhe-do-317346)
  - [Por que ficou pendente](#por-que-ficou-pendente)
  - [Próximos passos quando invoice aparecer](#próximos-passos-quando-invoice-aparecer)
- [Pickings já concluidos (referencia)](#pickings-já-concluidos-referencia)
- [Comando rápido para checar status](#comando-rápido-para-checar-status)
- [Atualizado](#atualizado)
- [Estado atual](#estado-atual)
- [Pendencias](#pendencias)

**Atualizado**: 2026-05-18 ~17:30 UTC (sessao 3 fim)
**Propósito**: registrar pickings em `state=done` mas SEM invoice CIEL IT ainda criada, para não perdermos rastreabilidade nas próximas sessões.

---

## Estado atual (2 pickings pendentes)

| Picking ID | Name | State | Date_done | Tipo | Ajustes locais | Estoque |
|---|---|---|---|---|---|---|
| **317346** | FB/SAI/IND/01559 | done | 2026-05-18 14:19:50 | FB: Expedição Industrialização | 21 ajustes INDUSTRIALIZACAO_FB_LF | 1.079,56 kg / 1518 volumes em "Em Trânsito (Industrialização)" |
| **317478** | FB/SAI/INT/24008 | done | 2026-05-18 19:36:56 UTC | FB: Transferências Internas (FB→Parceiros/Clientes via RecLf 13) | 18 ajustes TRANSFERIR_FB_CD batch 3a (FBC_REC_13) | 30.062 un consolidadas em 18 cods (Onda 2) |

### Detalhe do 317478 (Onda 2 batch 3a — RecLf 13)

- **Origin**: `Transfer LF NF INV-FBC-20260518-1636`
- **Direção**: FB → Parceiros/Clientes (preparação para CD via DFe)
- **Produtos**: 18 cods diferentes (202000024, 202003944, 202004012, 202030019, 202260016, 202640012, 202640013, 202640014, 203003944, 203030010, 205030110, 205030170, 205400406, 205400931, 205460941, 208000026, 208000041, 4149304)
- **Total**: 30.062,688 un / R$ 28.619,25
- **Ajustes locais**: 18 em status=PROPOSTO, fase=FB_CD_PROCESSANDO, external_id_operacao=FBC_REC_13
- **Pendente**: Etapa 22 do `processar_transfer_only` — `action_liberar_faturamento` chamado mas robô CIEL IT não criou a invoice da transferência em 30min (polling expirou)

### Recovery picking 317478

```python
# 1. Verificar se invoice apareceu
p = odoo.read('stock.picking', [317478], ['state','invoice_ids'])
# 2. Se invoice_ids preenchido → retomar via job
from app.recebimento.workers.recebimento_lf_jobs import processar_transfer_fb_cd_job
processar_transfer_fb_cd_job(13)
# 3. Se invoice nunca aparecer → cancelar + reverter (ver G032)
```

Detalhes: gotcha G032 (robo CIEL IT travado em invoice de transferencia) — a documentar.

### Pickings RESOLVIDOS na sessao 3 tarde

| Picking | Resolvido com | Invoice LF | Invoice FB | Status |
|---------|---------------|-----------|-----------|--------|
| 317416 (G016 issue original) | sessao 3 (workaround manual via XML import) | 629363 | 629726 | ✅ COMPLETO |
| 317420 (batch 30) | sessao 3 (pipeline normal) | 629055 | 629191 | ✅ COMPLETO |
| 317460 (batch 15 v4) | sessao 3 (pipeline normal) | 629364 | 629567 | ✅ COMPLETO |
| 317461 (batch 15 v4) | sessao 3 (recovery G029) | 629376 | 629703 | ✅ COMPLETO |

### Detalhe do 317346

- **Origin**: `INV-INVENTARIO_2026_05-INDUSTRIALIZACAO-G001`
- **Direção**: FB → LF (industrialização)
- **Produtos**: 20 distintos (cogumelo, azeitona, pepino etc — onda 1)
- **Peso**: 1079,56 kg (G018 v2 setado)
- **Volumes**: 1518
- **Ajustes locais**: status=PROPOSTO, fase=F5c_LIBERADO, picking_id_odoo=317346 (21 linhas)

### Por que ficou pendente

Robô CIEL IT lento/parado no momento da execução (10:25-11:00 UTC).
F5d (aguardar_invoice) teve timeout de 1800s + SSL closed (G016 ainda não
estendido para F5d).

### Próximos passos quando invoice aparecer

1. **Verificar criação da invoice** no Odoo:
   ```python
   from app.odoo.utils.connection import get_odoo_connection
   odoo = get_odoo_connection()
   # Buscar invoices recentes com origin = picking.name
   invs = odoo.search_read('account.move',
       [['ref', 'ilike', 'INV-INVENTARIO_2026_05']],
       ['id', 'name', 'state', 'l10n_br_situacao_nf', 'create_date'],
       order='create_date desc', limit=5)
   ```

2. **Atualizar ajustes locais** com invoice_id_odoo:
   ```sql
   UPDATE ajuste_estoque_inventario
   SET invoice_id_odoo = <NOVO_ID>, fase_pipeline = 'F5d_INVOICE_GERADA'
   WHERE picking_id_odoo = 317346;
   ```

3. **Transmitir SEFAZ** (`--apenas-etapa=D`):
   ```bash
   python scripts/inventario_2026_05/09_executar_onda1_bulk.py \
     --company-id=5 --onda=1 --apenas-etapa=D \
     --confirmar --confirmar-sefaz --usuario=rafael
   ```

4. **Após SEFAZ OK**: criar **entrada LF manual** (replicar padrão do
   picking 317316):
   - location: 26489 (Estoque Virtual/Em Transito (Industrialização))
   - location_dest: 42 (LF/Estoque)
   - picking_type: 19 (LF: Recebimento)
   - **company_id=5 forçado no move** (gotcha conhecido)
   - origin: `INV-INVENTARIO_2026_05-ENTRADA-LF-NF<INVOICE_ID>`

---

## Pickings já concluidos (referencia)

Todas as NFs cross-company com entrada destino feita:

| Picking saída | Direção | NF | Entrada destino |
|---|---|---|---|
| 317290 LF/LF/SAI/RNA/00002 | LF→FB perda | 608607 | RecebimentoLf 4 processado ✓ |
| 317295 LF/LF/SAI/RNA/00004 | LF→FB perda | 608631 | RecebimentoLf 7 (invoice FB 608645 posted) ✓ |
| 317297 FB/SAI/IND/01554 | FB→LF industr | 608629 | Picking 317306 LF/IN/01733 ✓ |
| 317313 FB/SAI/IND/01558 | FB→LF industr | 627348 | Picking 317316 LF/IN/01734 ✓ |
| ~~317294 LF/LF/SAI/RNA/00003~~ | NF 13150 cancelada | — | Devolvido via 317303 ✓ |
| ~~317311 LF/LF/SAI/RNA/00007~~ | NF 626032 cancelada | — | Devolvido via 317315 ✓ |
| ~~317342-317345~~ | LF→FB perda canceladas | — | Cancelados sem NF ✓ |
| **317346 FB/SAI/IND/01559** | **FB→LF industr** | **PENDENTE** | **pendente** |

---

## Comando rápido para checar status

```bash
source .venv/bin/activate
python3 -c "
import sys; sys.path.insert(0, '.')
from app import create_app
from app.odoo.utils.connection import get_odoo_connection
app = create_app()
with app.app_context():
    odoo = get_odoo_connection()
    p = odoo.read('stock.picking', [317346],
        ['name', 'state', 'date_done'])
    print(p)
    # Buscar invoice criada com origin
    invs = odoo.search_read('account.move',
        [['ref', 'ilike', 'INV-INVENTARIO_2026_05-INDUSTRIALIZACAO-G001']],
        ['id', 'name', 'state', 'create_date'], limit=5)
    print(f'Invoices candidatas: {invs}')
"
```

## Atualizado

Ver datas no corpo do documento (registro historico).

## Estado atual

Ver secoes do corpo acima (estado registrado na epoca).

## Pendencias

Ver itens listados no corpo acima.
