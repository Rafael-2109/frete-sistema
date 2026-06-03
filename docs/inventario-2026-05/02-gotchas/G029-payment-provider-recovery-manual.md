<!-- doc:meta
tipo: reference
camada: L3
sot_de: —
hub: docs/inventario-2026-05/02-gotchas/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# G029 — payment_provider_id ausente em recovery manual de NF

> **Papel:** G029 — payment_provider_id ausente em recovery manual de NF.

## Indice

- [Sintoma](#sintoma)
- [Causa raiz](#causa-raiz)
- [Diagnóstico](#diagnóstico)
- [Workaround imediato](#workaround-imediato)
- [Fix proposto (não implementado)](#fix-proposto-não-implementado)
- [Casos observados (2026-05-18)](#casos-observados-2026-05-18)
- [Quando ocorre](#quando-ocorre)
- [Ref](#ref)

**Descoberta**: 2026-05-18 sessao 3 tarde (recovery 317461, 317416)
**Severidade**: HIGH (NF fica em rascunho permanente, SEFAZ não autoriza)
**Status**: ⚠️ **WORKAROUND** (set manual via XML-RPC) — fix code pendente

---

## Sintoma

NF in_invoice ou out_invoice criada pelo robô CIEL IT fica em
`l10n_br_situacao_nf='rascunho'` indefinidamente após `action_post`.
Playwright tenta transmitir SEFAZ várias vezes (até 15 tentativas em
`f5e_transmitir_sefaz`) e SEFAZ **não retorna** (cstat=False,
xmotivo=False, situacao_nf permanece rascunho).

```
[playwright] NF-e RETNA/2026/00037 nao autorizada
(tentativa 12/15, situacao=rascunho, cstat=False, xmotivo=False)
```

## Causa raiz

Invoice está com `payment_provider_id=False` (vazio). O Odoo CIEL IT
exige `payment_provider_id` populado para transmitir SEFAZ.

A função `InventarioPipelineService._garantir_payment_provider`
(`app/odoo/services/inventario_pipeline_service.py:201-280`) é chamada
APENAS em `f5d_aguardar_invoices` (etapa C do pipeline). Em fluxos de
**recovery manual** (ETAPA C interrompida por SSL crash, depois rodar
ETAPA D diretamente via `--apenas-etapa=D`), esta função **NÃO é
acionada** — ETAPA D assume que F5d.5 já rodou.

## Diagnóstico

```python
inv = odoo.read('account.move', [invoice_id],
    ['payment_provider_id', 'l10n_br_situacao_nf'])[0]
# payment_provider_id: False  ← BUG
# l10n_br_situacao_nf: rascunho
```

Comparando com invoice OK no mesmo batch:
```
629364 (OK):    payment_provider_id=[38, 'SEM PAGAMENTO']  sit=autorizado
629376 (FALHA): payment_provider_id=False                  sit=rascunho
```

## Workaround imediato

Setar manualmente via XML-RPC antes de re-rodar ETAPA D:

```python
odoo.write('account.move', [invoice_id], {'payment_provider_id': 38})
# 38 = 'SEM PAGAMENTO' (PAYMENT_PROVIDER_SEM_PAGAMENTO em inventario_pipeline_service.py:156)
```

Após este write, ETAPA D Playwright transmite SEFAZ em ~1-2 min.

## Fix proposto (não implementado)

Chamar `_garantir_payment_provider` também **no inicio de
`f5e_transmitir_sefaz`** (idempotente: já tem skip se já setado):

```python
def f5e_transmitir_sefaz(self, ajustes, executado_por='sistema'):
    for inv_id in invoices_distintas:
        # G029: garantir payment_provider antes de SEFAZ (recovery manual)
        try:
            self._garantir_payment_provider(inv_id, ajs[0], executado_por)
        except Exception as e:
            logger.warning(f'G029 payment_provider write falhou: {e}')
        # ... rest of SEFAZ transmission
```

Trade-off: 1 read extra por invoice (~50ms). Vale para evitar recovery
manual.

## Casos observados (2026-05-18)

| Invoice | Picking | payment_provider antes recovery | SEFAZ após write manual |
|---------|---------|--------------------------------|------------------------|
| 629376 | 317461 LF/LF/SAI/RNA/00036 | False | ✅ autorizado em 2min |
| 629363 | 317416 LF/LF/SAI/RNA/00017 | False | ✅ autorizado em 1min |
| 629364 | 317460 LF/LF/SAI/RNA/00035 | [38] (já setado via F5d.5) | ✅ autorizado normal |

## Quando ocorre

- ETAPA C interrompida (SSL crash, kill, Claude Code restart)
- Operador atualiza DB local manualmente: `fase_pipeline='F5d_INVOICE_GERADA'`
  + `invoice_id_odoo=<inv>` para pular para ETAPA D
- ETAPA D Playwright tenta transmitir SEFAZ → rascunho permanente

## Ref

- `app/odoo/services/inventario_pipeline_service.py:201-280`
  (`_garantir_payment_provider`, sequência F5d.5)
- `app/odoo/services/inventario_pipeline_service.py:920-929`
  (chamada em `f5d_aguardar_invoices`)
- G016 SSL crash que causou os recovery manuais
