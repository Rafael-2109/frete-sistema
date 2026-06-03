<!-- doc:meta
tipo: reference
camada: L3
sot_de: —
hub: docs/inventario-2026-05/02-gotchas/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# G031 — `stock.lot` é POR PRODUTO; `LOTES_MIGRACAO_POR_COMPANY` NÃO é FK universal

> **Papel:** G031 — `stock.lot` é POR PRODUTO; `LOTES_MIGRACAO_POR_COMPANY` NÃO é FK universal.

## Indice

- [Sintoma](#sintoma)
- [Causa raiz](#causa-raiz)
  - [Por que dry-run passou?](#por-que-dry-run-passou)
- [Solução](#solução)
  - [Constants documentadas](#constants-documentadas)
- [Onde está codificada a invariante](#onde-está-codificada-a-invariante)
- [Rollback do incidente 2026-05-24 v4](#rollback-do-incidente-2026-05-24-v4)
- [Outros lugares que podem ter mesma falha (auditar)](#outros-lugares-que-podem-ter-mesma-falha-auditar)
- [Ref](#ref)

**Descoberta**: 2026-05-24 v4 (Skill 2 modo C `transferir_para_indisponivel` 1ª execução PROD)
**Severidade**: HIGH (incidente real — 4.319,4019 un saíram de FB/Estoque sem chegar em FB/Indisp; rollback em ~10s)
**Status**: ✅ CORRIGIDO no service `app/odoo/estoque/scripts/transfer.py` (método `transferir_para_indisponivel` resolve POR PRODUTO via `lot_svc.criar_se_nao_existe`) + constants documentadas como histórico/exemplo

---

## Sintoma

`stock.quant.create` ou `stock.quant.write` com `lot_id` de outro produto retorna:

```
xmlrpc.client.Fault: <Fault 2: 'O número de lote/série (MIGRAÇÃO) está vinculado a outro produto.'>
```

No incidente 2026-05-24 v4: 16/16 produtos falharam em estado PARCIAL (origem reduzida em PROD, destino não creditado). Total impactado: 4.319,4019 un "desaparecidas" temporariamente até o rollback.

## Causa raiz

No Odoo CIEL IT, `stock.lot` tem campo `product_id` (NOT NULL). Cada produto tem seu PRÓPRIO `stock.lot.id` mesmo quando o nome é idêntico:

```
stock.lot:
  id=30482  name='MIGRAÇÃO'  product_id=X  company_id=1
  id=57932  name='MIGRAÇÃO'  product_id=Y  company_id=1
  id=30658  name='MIGRAÇÃO'  product_id=Z  company_id=1
  ...
```

A constant em `app/odoo/constants/locations.py`:

```python
LOTES_MIGRACAO_POR_COMPANY: Dict[int, int] = {
    1: 30482,  # FB — lote MIGRAÇÃO
    4: 30856,  # CD — lote MIGRAÇÃO
}
```

…tem apenas o `lot_id` de UM produto cada (escolhido como exemplo durante D011 do inventário 2026-05). Usar isso como FK universal em `stock.quant.create({product_id: Z, lot_id: 30482, ...})` viola a integridade `lot_id ↔ product_id` do Odoo.

### Por que dry-run passou?

O service `StockQuantAdjustmentService.ajustar_quant(criar_se_faltar=True)` em dry-run apenas **simula** a chave `(product, company, location, lot)` sem chamar `stock.quant.create` real. A validação FK só dispara em modo `--confirmar`.

## Solução

**REGRA INVIOLÁVEL**: NÃO usar `LOTES_MIGRACAO_POR_COMPANY` como `lot_id` em operações de escrita. Resolver POR PRODUTO sempre:

```python
# ❌ ERRADO (usa constant como FK universal):
from app.odoo.constants.locations import LOTES_MIGRACAO_POR_COMPANY
lot_id_destino = LOTES_MIGRACAO_POR_COMPANY[company_id]  # 30482 fixo

# ✅ CORRETO (resolve POR PRODUTO):
from app.odoo.services.stock_lot_service import StockLotService
lot_svc = StockLotService(odoo=odoo)
lot_id_destino, criado_agora = lot_svc.criar_se_nao_existe(
    nome='MIGRAÇÃO',
    product_id=pid,
    company_id=cid,
)
```

`StockLotService.criar_se_nao_existe` faz:
1. `buscar_por_nome('MIGRAÇÃO', pid, cid)` (usa operador `in` + fallback `=like` por G002)
2. Se existir → retorna `(lot_id, False)`
3. Se não existir → cria via `odoo.create('stock.lot', {name, product_id, company_id})` → `(novo_lot_id, True)`

### Constants documentadas

`app/odoo/constants/locations.py` agora tem (2026-05-24 v4):

- `LOTES_MIGRACAO_POR_COMPANY` — marcado como HISTÓRICO/EXEMPLO no comentário (NÃO usar como FK universal)
- `NOME_LOTE_MIGRACAO_POR_COMPANY` (NOVO) — apenas o nome canônico: `{1: 'MIGRAÇÃO', 4: 'MIGRAÇÃO'}` — para passar a `lot_svc.buscar_por_nome`/`criar_se_nao_existe`

## Onde está codificada a invariante

`app/odoo/estoque/scripts/transfer.py::transferir_para_indisponivel`:
- Aceita `nome_lote_destino: str = 'MIGRAÇÃO'` (default canônico)
- Em modo real: `lot_id_destino, criado = self.lot_svc.criar_se_nao_existe(nome, product_id, company_id)`
- Em dry-run: apenas `buscar_por_nome`; se não existir, retorna `FALHA_LOTE_DESTINO_INEXISTENTE`
- Reporta `lote_destino_criado_agora: bool` no output JSON (auditoria)

Cobertura pytest: 15 testes em `tests/odoo/services/test_stock_internal_transfer_service.py` (`test_transferir_para_indisponivel_*`). 3 testes específicos para o gotcha:
- `test_transferir_para_indisponivel_modo_real_cria_lote_destino` — chama `criar_se_nao_existe` POR PRODUTO
- `test_transferir_para_indisponivel_dry_run_lote_destino_inexistente` — retorna FALHA sem criar
- `test_transferir_para_indisponivel_nome_lote_destino_custom` — aceita nome alternativo

## Rollback do incidente 2026-05-24 v4

Após FALHA_AUMENTO em PROD (origem reduzida, destino não creditado), rollback executado via Skill 1 `ajustar_quant +qty` em cada lote origem com `criar_se_faltar=True` (defensivo caso Odoo tenha deletado quant zerado). 16/16 EXECUTADO; estado integral restaurado em ~10s. Log:

```
scripts/inventario_2026_05/auditoria/log_2.1_ROLLBACK_para_indisp_falha_20260524_105219.json
```

## Outros lugares que podem ter mesma falha (auditar)

Buscar uso de `LOTES_MIGRACAO_POR_COMPANY` como `lot_id` direto em operações de WRITE:

```bash
grep -rn "LOTES_MIGRACAO_POR_COMPANY\[" app/ scripts/ --include='*.py'
```

Toda referência precisa: (a) ser apenas leitura/comparação OU (b) ser refatorada para resolver via `lot_svc`. Verificado 2026-05-24 v4: apenas `transfer.py::transferir_para_indisponivel` usava (refatorado).

## Ref

- `app/odoo/estoque/scripts/transfer.py:797-1000` (`transferir_para_indisponivel`)
- `app/odoo/constants/locations.py:65-90` (constants documentadas)
- `tests/odoo/services/test_stock_internal_transfer_service.py:721-960` (15 testes modo C)
- `scripts/inventario_2026_05/auditoria/log_2.1_ROLLBACK_para_indisp_falha_20260524_105219.json` (rollback)
- `scripts/inventario_2026_05/auditoria/log_2.2_para_indisp_FIX_20260524_110128.json` (re-execução pós-fix, 16/16 OK)
- Memória `[[skill2_transfer_interno_pattern]]` §incidente 2026-05-24 v4
- G002 (lot.name search instável — relacionado a busca de lote)
