<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/inventario-2026-05/00-decisoes/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# D008 — Lições de segurança operacional: scripts ad-hoc em PROD (E1 + E2)

> **Papel:** D008 — Lições de segurança operacional: scripts ad-hoc em PROD (E1 + E2).

## Indice

- [E1 — Re-execução acidental causou duplicação no Odoo PROD](#e1-re-execução-acidental-causou-duplicação-no-odoo-prod)
  - [O que aconteceu](#o-que-aconteceu)
  - [Como foi descoberto](#como-foi-descoberto)
  - [Recuperação](#recuperação)
  - [Lição (PADRÃO OBRIGATÓRIO para scripts ad-hoc)](#lição-padrão-obrigatório-para-scripts-ad-hoc)
- [E2 — Reinventei busca de `stock.lot` ignorando workaround existente](#e2-reinventei-busca-de-stocklot-ignorando-workaround-existente)
  - [O que aconteceu](#o-que-aconteceu)
  - [Workaround correto JÁ EXISTE no código do projeto](#workaround-correto-já-existe-no-código-do-projeto)
  - [Recuperação](#recuperação)
  - [Lição (PADRÃO OBRIGATÓRIO)](#lição-padrão-obrigatório)
- [Por que documentar como D008 (decisão) e não G028 (gotcha)](#por-que-documentar-como-d008-decisão-e-não-g028-gotcha)
- [Ref](#ref)
- [Contexto](#contexto)

**Data**: 2026-05-18 07:00-07:30 (sessão CD pré-etapa, fim de tarde)
**Origem**: extraído de `CHECKPOINT_2026_05_18_CD_FINALIZADO.md` §4.1 antes do arquivamento parcial
**Status**: lição aplicável a TODO script ad-hoc futuro em PROD (não-bloqueante; padrão a seguir)
**Contexto**: durante resolução de 12 ajustes APROVADO race condition residual, foram criados scripts ad-hoc em `/tmp/`. 2 erros operacionais foram cometidos e recuperados — virou padrão de prevenção.

---

## E1 — Re-execução acidental causou duplicação no Odoo PROD

### O que aconteceu

Script `/tmp/resolver_9_bloq.py` foi escrito para tratar 9 ajustes `BLOQ_VIRTUAL_INV` (Cat 3). O script:

1. Usou `IDS_BLOQ = [163406, 164064, ...]` hardcoded
2. **NÃO filtrou** por `status='FALHA'` no SQL antes de iterar
3. Lia ajustes e operava `stock.quant.action_apply_inventory` no Odoo

Após 2 sub-pilotos individuais terem executado os IDs 163406 e 164764 manualmente, o batch foi rodado novamente:

- Quant 218656 (cod=204030500 lote=003-007/25): qty subiu de 66800 → **78800** (+12000 duplicado)
- Quant 176702 (cod=4100161 lote=MIGRAÇÃO): qty subiu 1898.5028 → **1898.6698** (+0.167 duplicado)

### Como foi descoberto

Validação pós-execução cruzou Odoo vs ajustes locais — detectou drift de +12000 un que não correspondia a nenhum ajuste pendente.

### Recuperação

Script `/tmp/reverter_duplicacoes.py --confirmar` aplicou IA (inventory adjustment) negativo:
- quant 218656: 78800 → 66800
- quant 176702: 1898.6698 → 1898.5028

### Lição (PADRÃO OBRIGATÓRIO para scripts ad-hoc)

**Scripts de resolução SEMPRE devem filtrar por `status='FALHA'` (ou `'APROVADO'` ou estado esperado) ANTES de processar.** Idealmente verificar o estado do Odoo (`stock.quant.quantity` esperado) antes de operar.

#### Checklist mínimo para script ad-hoc em PROD

- [ ] Filtro WHERE explícito por `status` no SQL inicial (não confiar em IDs hardcoded)
- [ ] Verificação pré-operação do estado Odoo (snapshot antes/depois)
- [ ] `--dry-run` por default, requer `--confirmar` para executar
- [ ] Backup do estado DB antes da operação (`pg_dump` da tabela ou SELECT INTO snapshot)
- [ ] Após cada operação Odoo, persistir IMEDIATAMENTE `status='EXECUTADO'` no DB local para impedir re-processamento

#### Template seguro

```python
ajustes = (
    AjusteEstoqueInventario.query
    .filter_by(ciclo='INVENTARIO_2026_05', company_id=COMPANY)
    .filter(AjusteEstoqueInventario.status == 'FALHA')  # ← FILTRO OBRIGATÓRIO
    .filter(AjusteEstoqueInventario.id.in_(IDS_ESPECIFICOS))
    .all()
)

for a in ajustes:
    # 1. Snapshot pré-op
    snapshot_antes = odoo.read('stock.quant', [a.quant_id], ['quantity'])

    # 2. Sanity check: o estado Odoo bate com a expectativa do ajuste?
    if abs(snapshot_antes[0]['quantity'] - a.qtd_odoo) > 0.001:
        logger.warning(f'Drift detectado em quant {a.quant_id}: '
                       f'esperado={a.qtd_odoo}, real={snapshot_antes[0]["quantity"]}')
        continue  # pula — operador decide

    # 3. Operação real
    odoo.execute_kw('stock.quant', 'action_apply_inventory', [[a.quant_id]])

    # 4. Persiste IMEDIATAMENTE (impede re-processamento se script for re-executado)
    a.status = 'EXECUTADO'
    db.session.commit()
```

---

## E2 — Reinventei busca de `stock.lot` ignorando workaround existente

### O que aconteceu

Script `/tmp/resolver_9_bloq.py:buscar_saldo_virtual()` usou:

```python
lots = odoo.search_read('stock.lot', [['name', '=', lote_nome]], ['id', 'product_id'])
```

Esbarrou no [bug do Odoo `stock.lot.name=`](../../../app/odoo/services/stock_lot_service.py#L39-L52) que retorna vazio intermitente.

Caso 168026 cod=4360162 lote=218/25 falhou silenciosamente — o lote **EXISTE** (`id=42812`) mas a busca retornou vazio. Script tratou como "lote não encontrado" e pulou.

### Workaround correto JÁ EXISTE no código do projeto

`StockLotService.buscar_por_nome` (`app/odoo/services/stock_lot_service.py:39-52`):
- Tentativa primária: `['name', 'in', [nome]]` (operador `in` evita bug)
- Fallback: `['name', '=like', nome]`

Também em:
- `recebimento_lf_odoo_service._buscar_stock_lot_existente` (linha 4188-4204)
- `recebimento_lf_odoo_service._criar_stock_lot_com_fallback` (linha 4206-4275)

### Recuperação

Script `/tmp/resolver_168026.py` com `lot_id=42812` hardcoded como workaround pontual.

### Lição (PADRÃO OBRIGATÓRIO)

**SEMPRE usar `StockLotService` (já tem o workaround) em vez de chamar `odoo.search_read('stock.lot', [..., 'name', '=', ...])` direto.**

#### Antes de escrever código que busca por nome de `stock.lot`

1. Verificar se `StockLotService.buscar_por_nome` cobre o caso (95% dos casos cobre)
2. Se precisar customizar: copiar o padrão do service (`name in [nome]` primário + `name =like nome` fallback), nunca usar `name = nome` direto

#### Onde NÃO usar `['stock.lot.name', '=', ...]`

- ❌ scripts ad-hoc em `/tmp/`
- ❌ helpers internos de scripts em `scripts/inventario_2026_05/`
- ❌ services novos sob `app/odoo/services/`

#### Onde já está correto

- ✅ `StockLotService.buscar_por_nome`
- ✅ `recebimento_lf_odoo_service._buscar_stock_lot_existente`
- ✅ `recebimento_lf_odoo_service._criar_stock_lot_com_fallback`

---

## Por que documentar como D008 (decisão) e não G028 (gotcha)

Esta NÃO é uma armadilha do Odoo descoberta agora — são **decisões de padrão operacional** que viraram norma do projeto após dois incidentes recuperáveis. Devem influenciar como TODO script ad-hoc futuro é estruturado, independente de em qual ciclo de inventário rode.

E1 e E2 estão relacionados pelo padrão maior: **scripts ad-hoc em PROD precisam tratar idempotência (E1) e reusar workarounds testados (E2)**, não apenas "resolver o problema imediato".

---

## Ref

- `CHECKPOINT_2026_05_18_CD_FINALIZADO.md` §4.1 — narrativa original com IDs reais (218656, 176702, 168026, 42812)
- `app/odoo/services/stock_lot_service.py:39-52` — `buscar_por_nome` com workaround
- `app/odoo/services/recebimento_lf_odoo_service.py` linhas 4188-4275 — outro caso do mesmo workaround
- `02-gotchas/G027-09b-bugs-latentes-b1-b2.md` — bugs do `09b` descobertos na mesma sessão (B1 não persistir FALHA + B2 não somar quants)
- `08-execucoes/EXECUCAO_PRE_ETAPA_CD_2026_05_18.md` — execução completa da pré-etapa CD

## Contexto

ADR (decisao de arquitetura) — ciclo de inventario NACOM/LF/CD/FB 2026-05. Tema: Lições de segurança operacional: scripts ad-hoc em PROD (E1 + E2)
