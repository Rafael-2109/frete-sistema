# G037 — Operação não cadastrada exige CFOP explícito

**Severidade**: HIGH
**Status**: ✅ IDENTIFICADO (2026-05-26 v18)
**Descoberto em**: Auditoria Rafael pós-v17.5 (correção das RESPOSTAS VALIDADAS Q3)

## Sintoma

NF inter-company gerada pelo motor fiscal do Odoo (CIEL IT) sem o CFOP
esperado quando a operação fiscal (`stock.picking.type.l10n_br_tipo_pedido`)
não está cadastrada/mapeada para a direção esperada. Resultado prático:

- ETAPA F (entrada destino manual) de `INDUSTRIALIZACAO_FB_LF` gera picking
  PT 19 LF/IN mas sem `l10n_br_cfop_id=1901` na linha do invoice → SEFAZ
  rejeita com cstat divergente OU NF é gerada com CFOP de default (não 1901).
- ETAPA E (RecebimentoLf via `escriturar_dfe_lf.py`) gera DFe com
  `l10n_br_tipo_pedido` faltando ou genérico ('aquisicao' em vez de
  'serv-industrializacao') → motor fiscal aplica CFOP genérico
  (ex.: 1933 'Aquisição', não 1901 'Industrialização').

## Causa raiz

O motor fiscal do Odoo CIEL IT deriva o CFOP a partir de:
1. `fiscal_position_id` do invoice/picking (mapeia impostos + CFOP por par
   {origem, destino, NCM, regime})
2. `l10n_br_tipo_pedido` no DFe (CHAVE para derivar CFOP correto na
   escrituração — ex.: `serv-industrializacao` → 1901; `aquisicao` → 1933)
3. Operação fiscal cadastrada no `stock.picking.type` (deriva
   `l10n_br_tipo_pedido` ao escolher picking_type_id; ex.: PT 53 FB/Exped/Industr
   → `tipo_pedido='industrializacao'`).

Se a operação NÃO está cadastrada (PT genérico, fiscal_position incompleta,
tipo_pedido genérico no DFe), o motor aplica CFOP de default — quase sempre
errado para inter-company customizado.

## Solução (V1 — paliativo dentro da Skill 8)

Quando a operação não estiver mapeada, setar o CFOP explícito via
`l10n_br_cfop_id` na linha do invoice/picking. A constante
`MATRIZ_INTERCOMPANY` (em `app/odoo/constants/operacoes_fiscais.py`) tem
o campo `cfop_esperado` justamente como fallback documentado.

```python
from app.odoo.constants.operacoes_fiscais import MATRIZ_INTERCOMPANY

matriz = MATRIZ_INTERCOMPANY['INDUSTRIALIZACAO_FB_LF']
cfop_esperado = matriz['cfop_esperado']  # '5901' (saída) / '1901' (entrada)

# Em ETAPA E (escriturando):
# DFe deve receber l10n_br_tipo_pedido='serv-industrializacao' para derivar
# CFOP 1901 — referência `scripts/inventario_2026_05/escriturar_dfe_lf.py`
# (FLUXO A correto da escrituração).

# Em ETAPA F (picking entrada manual — caminho B paliativo v17.5):
# Após criar stock.move, escrever:
odoo.write('stock.move', [move_id], {
    'l10n_br_cfop_id': resolver_cfop_id(cfop_esperado),
})
```

## Importância do `MATRIZ_INTERCOMPANY[acao]['cfop_esperado']`

Antes da auditoria Rafael v18 (2026-05-26), `cfop_esperado` era considerado
APENAS log/auditoria. **Não é**: tem USO PRÁTICO como fallback quando a
operação não está cadastrada no Odoo. Toda nova ação adicionada à matriz
DEVE preencher `cfop_esperado` corretamente.

## Solução (V2 — refator v19+ FLUXO L3 correto)

O caminho **fiscalmente correto** para ETAPA F é:

1. **Skill 7 `escriturando-odoo`** (refatorada — ABRANGENTE em v19+) — escritura
   o DFe da NF SEFAZ-OK com `l10n_br_tipo_pedido` apropriado.
2. **Odoo CIEL IT** — `action_gerar_po_dfe` gera PO confirmada.
3. **Picking nativo** — criado automaticamente pelo Odoo via PO, com
   `purchase_id` + `partner_id` corretos.
4. **Skill 5 `operando-picking-odoo`** — atomo novo `preencher_lotes_picking(picking_id, lote='MIGRAÇÃO')`.
5. **Skill 7** — `criar_invoice_from_po(po_id)` gera invoice com CFOP derivado
   corretamente do tipo_pedido.

Esse fluxo NÃO requer `cfop_esperado` como fallback — o motor fiscal deriva
1901 automaticamente. Ver `app/odoo/estoque/CLAUDE.md` §6 ANTIPADRÕES
DETECTADOS V17.5 + checklist v19+ em `.claude/skills/faturando-odoo/SKILL.md`.

## Relacionado

- `MATRIZ_INTERCOMPANY` em `app/odoo/constants/operacoes_fiscais.py` (campo `cfop_esperado` documentado)
- `ACAO_PARA_CFOP_ENTRADA` em mesmo arquivo (D17: 5xxx → 1xxx)
- G034 — robo CIEL IT aplica defaults PT 66 em DEV_*
- `l10n_br_ciel_it_account.dfe.l10n_br_tipo_pedido` — campo CHAVE no DFe para
  derivar CFOP correto na escrituração
- FLUXO A correto (refator v19+): `scripts/inventario_2026_05/escriturar_dfe_lf.py`
- Pattern análogo em `app/fretes/services/lancamento_odoo_service.py` (16 etapas — frete/CTe usa o mesmo motor fiscal)

## Histórico

- 2026-05-26 v18 — IDENTIFICADO via auditoria Rafael pós-v17.5 (validação
  Q3: "Os 4 conceitos operacao/tipo_pedido/CFOP/picking_type são ligados?").
  Resposta Rafael: PARCIALMENTE derivados, MAS CFOP NÃO é apenas
  informacional — se operação não cadastrada, é necessário setar CFOP.
