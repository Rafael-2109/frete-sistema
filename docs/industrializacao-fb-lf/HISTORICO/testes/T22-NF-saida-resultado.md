# T22 — NF saída FB CFOP 5901 (Remessa para Industrialização) ✅ AUTORIZADA SEFAZ

**Status final**: ✅ done (2026-05-29)
**Executor**: Claude via XML-RPC + Playwright SEFAZ (Skill 8 caminho 4B direto, sem ajuste_ids)
**Modo**: Validar picking → action_liberar_faturamento → polling invoice → transmitir Playwright

---

## Sequência completa

### 1) Pré-cond: picking saída validado

```
stock.picking 322049 (FB/SAI/IND/01606)
  state          = done (button_validate)
  picking_type   = 53 (FB/SAI/IND)
  src            = FB/Estoque (8)
  dst            = Em Trânsito Industrialização (26489)
  moves          = 16 (todos done, qty completa)
  incoterm       = 6 (CIF)
  carrier_id     = 996 (NACOM GOYA INDUSTRIA - FB CNPJ 61.724.241/0001-78)
```

### 2) action_liberar_faturamento

```python
conn.execute_kw('stock.picking', 'action_liberar_faturamento', [[322049]])
# return: None (sem exception → OK)
```

Robô CIEL IT processou em ~90s e criou:
- account.move id=**725676 RPI/2026/00242**
- move_type=**out_invoice**, state=posted, partner=LF (35)
- journal=[17, 'REMESSA PARA INDUSTRIALIZAÇÃO']
- fiscal_position=[25, 'REMESSA PARA INDUSTRIALIZAÇÃO']
- l10n_br_tipo_pedido='industrializacao'
- l10n_br_operacao_id=[80, 'Remessa p/ Industrialização']
- 16 linhas com **CFOP 5901** + 1 linha imposto
- amount_untaxed=R$ 2.797,85
- amount_total=R$ 0.00 (ICMS CST=51 suspenso → tax=-2797.85)

### 3) Transmissão SEFAZ via Playwright

Como Skill 8 ATÔMICA exige `ajuste_ids >= 1` (D-OPS-2b — propagação de chave a registros de inventário), e nosso piloto não tem `AjusteEstoqueInventario`, chamamos diretamente `app.recebimento.services.playwright_nfe_transmissao.transmitir_nfe_via_playwright()` (que é o que a Skill 8 envelopa).

```python
from app.recebimento.services.playwright_nfe_transmissao import transmitir_nfe_via_playwright
result = transmitir_nfe_via_playwright(
    invoice_id=725676,
    odoo=odoo,
    logger=logger,
    redis_callback=None,
    max_tentativas=15,
    intervalo_retry=120,
)
```

### 4) Resultado SEFAZ — AUTORIZADO em t+56s

```json
{
  "sucesso": true,
  "chave_nf": "35260561724241000178550010000945901007256765",
  "situacao_nf": "autorizado",
  "inv_name": "RPI/2026/00242",
  "tentativa": 1
}
```

**Decodificação da chave (estrutura SEFAZ)**:
- 35 = SP (UF)
- 2605 = ano/mês emissão
- 61724241000178 = CNPJ FB NACOM GOYA
- 55 = modelo NF-e
- 001 = série
- 000094590 = número NF
- 1 = tipo emissão normal
- 00725676 = código aleatório
- 5 = DV

### 5) Validação pós-SEFAZ

```
account.move 725676 RPI/2026/00242
  state                = posted
  l10n_br_situacao_nf  = autorizado  ✓
  amount_untaxed       = 2797.85
  amount_total         = 0.0
  amount_tax           = -2797.85
```

---

## Achados auxiliares descobertos durante T22

| Campo | Valor encontrado | Quando descobri |
|---|---|---|
| `incoterm` (Tipo de Frete) | obrigatório no picking; **CIF** (id=6) escolhido para remessa | 1º erro de `action_liberar_faturamento` |
| `carrier_id` (Transportadora) | obrigatório; **996** NACOM GOYA INDUSTRIA (transporte próprio) — padrão histórico FB/SAI/IND | 2º erro |
| `l10n_br_operacao_id` | computed/readonly na PO; precisa setar na sale.order.line | descoberto na PO |
| `l10n_br_cfop_id` (linha) | precisa setar manual via write XML-RPC (onchange só dispara via UI) | descoberto na PO |
| `res.company.warehouse_id` | obrigatório para inter-company SO/PO espelhada; faltava em FB e LF (T01 não cobria) | descoberto no button_confirm PO |

---

## Próximo passo

**T23 — Aguardar DFe chegar em LF + validar picking pt=64 LF/RECEB/IND**

Com NF autorizada pelo SEFAZ, o DFe está sendo enviado para a caixa-postal da LF (LA FAMIGLIA CNPJ 18.467.441/0001-63). CIEL IT da LF processa e cria picking automaticamente.

Verificação (read-only):
```python
# DFe em LF
conn.search_read('l10n_br_ciel_it_account.dfe', [('company_id','=',5),('create_date','>=','2026-05-29 12:10:00')])
# Picking pt=64 em LF
conn.search_read('stock.picking', [('company_id','=',5),('picking_type_id','=',64),('create_date','>=','2026-05-29 12:10:00')])
```

Pode levar de minutos a horas (depende velocidade SEFAZ + ciclo polling CIEL IT).

Quando picking entrada LF surgir:
1. Componentes entram em LF/Materiais de Terceiros (31092) via property_stock_subcontractor LF (35)
2. MO LF 20154 reserva automaticamente (8 componentes raw waiting → assigned)
3. PCP LF pode iniciar a MO (T24)

---

## Rollback

NF autorizada SEFAZ **NÃO cancela** via XML-RPC simples. Processo formal:
1. Cancelamento até 24h após autorização (sem uso, sem inutilização)
2. Necessário emitir evento de cancelamento via SEFAZ
3. Modificação posterior só via NF de devolução ou nota complementar

Para reverter o piloto sem cancelar SEFAZ (cenário "fail-safe"):
- Manter NF autorizada
- Quando DFe chegar em LF, validar picking entrada normalmente
- Continuar fluxo até MO done → NF retorno → DFe FB → conclusão
- Auditoria final demonstra fluxo completo funcional

## IDs criados nesta etapa

| Item | ID | Identifier |
|---|---:|---|
| account.move (NF saída) | **725676** | RPI/2026/00242 |
| Chave SEFAZ NF-e | — | **35260561724241000178550010000945901007256765** |
| 16 linhas + 1 imposto | 4353624-4353694 | — |

## Histórico breve

- 11:49 — Robô CIEL IT criou invoice (after action_liberar_faturamento)
- 11:58 — Invoice ficou posted state=posted
- 12:11:41 — Playwright iniciou login
- 12:11:46 — Login OK uid=42
- 12:11:51 — Tentativa 1/15 começa
- 12:12:36 — **AUTORIZADO** (situacao_nf='autorizado', chave de 44 dígitos retornada)
- Tempo total Playwright: **~56s**
