# G037 — Picking ETAPA F criado manualmente sem PO precisa de `l10n_br_cfop_id` explícito (CAMINHO B PALIATIVO)

**Severidade**: MEDIUM (escopo restrito ao caminho B paliativo)
**Status**: ✅ DOCUMENTADO (2026-05-26 v18 Fase 0 — REESCRITO após auditoria Rafael que detectou premissa errada na versão original v18)
**Escopo**: APENAS o caminho B paliativo da ETAPA F do orchestrator Skill 8 `faturando-odoo`. **NÃO se aplica ao fluxo normal** (account.move criado via PO+fiscal_position).
**Refator v19+ remove o paliativo**: caminho A correto = DFe → `action_gerar_po_dfe` → PO → picking nativo (com `purchase_id` + `partner_id` + `fiscal_position_id`) → motor fiscal deriva CFOP automaticamente.

## Sintoma

Quando o orchestrator Skill 8 ETAPA F invoca o atomo Skill 5 `criar_picking_entrada_destino_manual` (caminho B paliativo — sem PO criada via DFe), o picking criado **NÃO tem `purchase_id` nem `partner_id` populados pelo motor fiscal**. Consequência:

- Se o caller NÃO setar `l10n_br_cfop_id` explícito no `stock.move`, o picking sai com CFOP de default (provavelmente errado para inter-company).
- Quando o operador faturar esse picking (via Odoo UI ou robô CIEL IT), a NF resultante terá CFOP incorreto.

## Causa raiz

`operacoes_fiscais.py:17-29` define explicitamente:

> "`cfop_esperado`: CFOP da SAIDA.
> * NO FLUXO NORMAL (account.move criado via PO+fiscal_position): **informacional/log**. Real e decidido pelo Odoo via fiscal_position + l10n_br_tipo_pedido. NAO hardcodar.
> * NO CAMINHO B PALIATIVO da ETAPA F (Skill 8) — picking criado MANUALMENTE pela Skill 5 atomo `criar_picking_entrada_destino_manual` SEM PO+partner+fiscal_position — vira FALLBACK NECESSARIO para setar `l10n_br_cfop_id` explicito no stock.move (G037)."

O motor fiscal do Odoo CIEL IT deriva CFOP via 2 caminhos:
1. **fiscal_position_id** do invoice/picking (mapeia impostos + CFOP por par {origem, destino, NCM, regime})
2. **l10n_br_tipo_pedido** no DFe → tipo do PO → tipo da fiscal_position selecionada

No caminho B paliativo, **nenhum dos dois é populado** — picking nasce sem PO+partner. Portanto, o motor fiscal não tem como derivar CFOP. Solução paliativa: setar `l10n_br_cfop_id` manualmente no `stock.move` após `create`.

## Solução V1 (paliativo dentro do orchestrator Skill 8)

Quando o picking é criado pelo atomo `criar_picking_entrada_destino_manual` (Skill 5), o orchestrator deve setar `l10n_br_cfop_id` explícito a partir de `MATRIZ_INTERCOMPANY[acao]['cfop_esperado']` + direção:

```python
from app.odoo.constants.operacoes_fiscais import (
    MATRIZ_INTERCOMPANY,
    ACAO_PARA_DIRECAO,
    ACAO_PARA_CFOP_ENTRADA,
)

matriz = MATRIZ_INTERCOMPANY['industrializacao']
tipo_op, co, cd = ACAO_PARA_DIRECAO['INDUSTRIALIZACAO_FB_LF']  # ('industrializacao', 1, 5)
cfop_entrada = ACAO_PARA_CFOP_ENTRADA['INDUSTRIALIZACAO_FB_LF']  # '1901'

# Após criar o picking via atomo Skill 5:
picking_id = svc_skill5.criar_picking_entrada_destino_manual(...)

# Setar CFOP explícito nos stock.moves do picking (paliativo G037):
moves = odoo.search('stock.move', [('picking_id', '=', picking_id)])
cfop_id = odoo.search('l10n_br_fiscal.cfop', [('code', '=', cfop_entrada)], limit=1)
if cfop_id:
    odoo.write('stock.move', moves, {'l10n_br_cfop_id': cfop_id[0]})
```

**Status v18**: este paliativo NÃO ESTÁ codificado ainda no orchestrator atual — pickings criados em PROD via ETAPA F v17.5 + v18 podem ter CFOP de default. Necessário auditoria dos 8 pickings INV-* PT 19 históricos (317306, 317316, 320467, 320476 + 4 outros) para confirmar se cfop está correto.

## Solução V2 (refator v19+ — caminho A correto)

O caminho **fiscalmente correto** elimina o paliativo:

1. **Skill 7 `escriturando-odoo`** (refatorada ABRANGENTE em v19+) escritura o DFe da NF SEFAZ-OK no destino, com `l10n_br_tipo_pedido` apropriado (ex.: `'serv-industrializacao'`).
2. **Odoo CIEL IT** — `action_gerar_po_dfe` gera PO confirmada (com `partner_id` + `fiscal_position_id`).
3. **Picking nativo** — criado automaticamente pelo Odoo via PO, com `purchase_id` + `partner_id` corretos.
4. **Skill 5 `preencher_lotes_picking(picking_id, lote='MIGRAÇÃO')`** (átomo novo v19+) preenche lotes do picking nativo.
5. **Skill 7 `criar_invoice_from_po(po_id)`** gera invoice com CFOP derivado corretamente do `l10n_br_tipo_pedido`.

Esse fluxo **NÃO requer** `cfop_esperado` como fallback — motor fiscal deriva 1901 automaticamente. **G037 deixa de ser necessário pós-refator v19+**.

Ver `app/odoo/estoque/CLAUDE.md §6.5` (antipadrões AP1+AP2+AP3 — refator v19+) + `app/odoo/estoque/PROTECAO_PROXIMA_SESSAO.md`.

## Por que esta versão foi reescrita (lição AP5)

A versão original do G037 v18 dizia:
> "MATRIZ_INTERCOMPANY[acao]['cfop_esperado'] tem USO PRATICO (nao apenas log). Operacao nao cadastrada exige CFOP explicito."

**Premissa errada**. `operacoes_fiscais.py:17` JÁ DIZIA "informacional/log. Real e decidido pelo Odoo" (para o fluxo normal). O Rafael perguntou explicitamente: "voce leu esses 2 arquivos?" e expôs o desvio.

**Causa raiz do erro**: criei G037 baseado em "intuição de uso prático" sem ler `operacoes_fiscais.py` + `picking_types.py` INTEIROS.

**Antipadrão codificado**: AP5 em `app/odoo/estoque/CLAUDE.md §6.5` — "Criar gotcha sem ler docstrings de CONSTANTS". Próximas sessões DEVEM ler constants inteiras antes de criar gotchas sobre operações fiscais.

## Relacionado

- `MATRIZ_INTERCOMPANY` em `app/odoo/constants/operacoes_fiscais.py:53+` (campo `cfop_esperado` documentado com 2 papéis: informacional VS fallback paliativo)
- `ACAO_PARA_CFOP_ENTRADA` em `app/odoo/constants/operacoes_fiscais.py:393+` (D17: 5xxx → 1xxx)
- G034 — robô CIEL IT aplica defaults PT 66 em DEV_*
- `app/odoo/estoque/CLAUDE.md §6.5 AP1/AP2/AP3` — antipadrões que refator v19+ remove
- `app/odoo/estoque/PROTECAO_PROXIMA_SESSAO.md` — escudo contra desvios reincidentes
- `app/odoo/estoque/scripts/picking.py:criar_picking_entrada_destino_manual` — Skill 5 atomo do caminho B paliativo
- `app/odoo/estoque/orchestrators/faturamento_pipeline.py:executar_etapa_f` — orchestrator que invoca o atomo paliativo

## Histórico

- 2026-05-26 v18 (versão original) — Premissa errada: "cfop_esperado tem USO PRATICO geral".
- 2026-05-26 v18 Fase 0 (REESCRITO) — Escopo restrito ao caminho B paliativo da ETAPA F. Premissa alinhada com `operacoes_fiscais.py:17`. AP5 codificado.
