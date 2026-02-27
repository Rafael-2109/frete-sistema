---
name: conciliando-odoo-po
description: >-
  Use for split and consolidacao of purchase orders in Odoo to reconcile with
  a nota fiscal: consolidar POs de uma NF, executar split de pedido, criar PO
  Conciliador, reverter consolidacao, or ajustar quantidades de linhas de PO.
  Also use to debug errors during these operations (AttributeError, PO criado
  sem linhas corretas, fornecedor nao encontrado) or to explain conceptually
  how split/consolidacao works.
  Do NOT use for: read-only document queries (usar rastreando-odoo),
  NF x PO matching before consolidation (usar validacao-nf-po),
  financial payments (usar executando-odoo-financeiro),
  or exploring unknown Odoo model fields (usar descobrindo-odoo-estrutura).
allowed-tools: Read, Bash, Glob, Grep
---

## REGRAS CRITICAS — Anti-Alucinacao

1. **NUNCA usar `odoo.execute()`** — NAO EXISTE. Usar `odoo.execute_kw()` sempre
2. **NUNCA usar `odoo.create()` para PO** — Usar `copy()` que herda campos fiscais BR automaticamente
3. **Cada linha copia da SUA origem** — `aloc.odoo_po_line_id` (NAO da linha do PO de referencia)
4. **CNPJ DEVE ser formatado** — `l10n_br_cnpj` armazena `XX.XXX.XXX/XXXX-XX` (com pontuacao)
5. **Acumular consumo por linha** — Se 2 itens NF alocam da mesma linha PO, usar cache de consumo
6. **SEMPRE simular antes de executar** — `simular_consolidacao()` antes de `consolidar_pos()`
7. **Reversao e best-effort** — Pode nao restaurar estado exato, alertar usuario

---

## Quando NAO Usar Esta Skill

| Situacao | Skill Correta | Por que? |
|----------|--------------|----------|
| Validar match NF x PO | **validacao-nf-po** | Fase 2, anterior a consolidacao |
| Recebimento fisico (lotes/quality check) | **recebimento-fisico-odoo** | Fase 4, posterior |
| Pagamentos ou reconciliacao de extratos | **executando-odoo-financeiro** | Operacao financeira |
| Apenas consultar/rastrear documentos | **rastreando-odoo** | Esta skill modifica POs |
| Explorar modelo Odoo desconhecido | **descobrindo-odoo-estrutura** | Esta skill usa modelos mapeados |

---

# Conciliando Odoo PO

Skill para **EXECUTAR** operacoes de Split e Consolidacao de Pedidos de Compra no Odoo.

## DECISION TREE — Qual Operacao Usar?

| Se a pergunta menciona... | Operacao | Metodo |
|----------------------------|----------|--------|
| **Consolidar POs de uma NF** | Consolidacao completa | `consolidar_pos()` |
| **Simular antes de executar** | Simulacao (dry-run) | `simular_consolidacao()` |
| **Criar PO Conciliador** | Duplicar PO | `_criar_po_conciliador()` |
| **Ajustar quantidade** | Reduzir qtd original | `_ajustar_quantidade_linha()` |
| **Reverter consolidacao** | Desfazer (best-effort) | `reverter_consolidacao()` |
| **Vincular DFe ao PO** | Escrever dfe_id | `_vincular_dfe_ao_po()` |

### Regras de Decisao

1. **SEMPRE simular ANTES de executar**: `simular_consolidacao()` primeiro
2. **Consolidacao requer**: ValidacaoNfPoDfe com status='aprovado'
3. **Multi-PO**: Quando 1 item NF vem de N POs, usa MatchAlocacao
4. **PO sem saldo**: Pode ser cancelado via `_cancelar_po()`
5. **Reverter**: Best-effort — pode nao restaurar estado exato

## Contexto

Quando uma NF-e (DFe) chega com quantidades diferentes dos POs existentes, o sistema precisa:
1. Criar um **PO Conciliador** que casa 100% com a NF
2. Ajustar os POs originais para ficarem com o **saldo restante**
3. Vincular o DFe ao PO Conciliador

## Operacoes Suportadas

| Operacao | Metodo | Resultado |
|----------|--------|-----------|
| Simular consolidacao | `simular_consolidacao()` | Preview sem executar no Odoo |
| Executar consolidacao | `consolidar_pos()` | PO Conciliador criado + POs ajustados |
| Reverter consolidacao | `reverter_consolidacao()` | Desfaz acoes (best-effort) |
| Criar PO Conciliador | `_criar_po_conciliador()` | Duplica PO via copy() |
| Criar linha conciliador | `_criar_linha_po_conciliador()` | Duplica linha via copy() |
| Ajustar quantidade | `_ajustar_quantidade_linha()` | Reduz qtd no PO original |
| Vincular DFe ao PO | `_vincular_dfe_ao_po()` | Escreve dfe_id no PO |
| Cancelar PO vazio | `_cancelar_po()` | Cancela PO sem saldo |

## Arquivo Principal

`app/recebimento/services/odoo_po_service.py` (1281 linhas)

## Classe Principal

```python
from app.recebimento.services.odoo_po_service import OdooPoService

service = OdooPoService()
```

## Fluxo Completo de Consolidacao

```
ENTRADA:
  - validacao_id (ValidacaoNfPoDfe com status='aprovado')
  - pos_para_consolidar: [{'po_id': 123, 'po_name': 'PO00123'}, ...]

PASSO 1: Buscar fornecedor_id pelo CNPJ
  → odoo.search('res.partner', [('l10n_br_cnpj', '=', cnpj_formatado)])

PASSO 2: Criar PO Conciliador VAZIO
  → copy(PO de referencia) com overrides: partner_id, date_order, origin, state=draft, order_line=False
  → Fallback: se copy() copiar linhas, remove-las via unlink

PASSO 3: Para CADA item da NF com match:
  → Para cada MatchAlocacao (suporte multi-PO):
    a) copy(linha de referencia) → nova linha no PO Conciliador com qtd_nf e preco_nf
    b) write(linha original) → reduzir product_qty no PO original

PASSO 4: Confirmar PO Conciliador
  → execute_kw('purchase.order', 'button_confirm', [po_id])

PASSO 5: Vincular DFe ao PO Conciliador
  → write('purchase.order', po_id, {'dfe_id': dfe_id})
```

## Modelos Locais Envolvidos

| Modelo | Tabela | Uso |
|--------|--------|-----|
| `ValidacaoNfPoDfe` | `validacao_nf_po_dfe` | Validacao principal (status, resultado) |
| `MatchNfPoItem` | `match_nf_po_item` | Cada item da NF com match de PO |
| `MatchAlocacao` | `match_alocacao` | Alocacao multi-PO (1 item NF → N POs) |

## Modelos Odoo Envolvidos

| Modelo | Campos Principais | Operacoes |
|--------|-------------------|-----------|
| `purchase.order` | name, partner_id, date_order, origin, state, order_line, dfe_id | copy, write, button_confirm, button_cancel |
| `purchase.order.line` | order_id, product_id, product_qty, price_unit, qty_received | copy, write, unlink |
| `res.partner` | l10n_br_cnpj | search |

## Metodo de Conexao Odoo

```python
from app.odoo.utils.connection import get_odoo_connection

odoo = get_odoo_connection()
odoo.authenticate()

# UNICO metodo generico disponivel:
resultado = odoo.execute_kw(modelo, metodo, args, kwargs)

# Helpers especificos (wrapper de execute_kw):
odoo.search(modelo, domain, limit=None)
odoo.read(modelo, ids, fields)
odoo.write(modelo, id_ou_ids, values)
odoo.create(modelo, values)
```

## IMPORTANTE: NAO existe `odoo.execute()`

A classe `OdooConnection` (app/odoo/utils/connection.py) possui APENAS:
- `execute_kw(model, method, args, kwargs)` - generico
- `search()`, `read()`, `write()`, `create()` - helpers

**NUNCA usar `odoo.execute()`** — nao existe e causara AttributeError.

## Cenarios de Uso

### SPLIT (1 NF parcial de 1 PO)
```
PO Original: 500 un produto X
NF chegou: 400 un produto X

Resultado:
  PO Original: 100 un (saldo)
  PO Conciliador (NOVO): 400 un → vinculado a NF
```

### CONSOLIDACAO (1 NF com itens de N POs)
```
PO-A: 500 un produto X
PO-B: 500 un produto Y
NF chegou: 400 X + 400 Y

Resultado:
  PO-A: 100 un X (saldo)
  PO-B: 100 un Y (saldo)
  PO Conciliador (NOVO): 400 X + 400 Y → vinculado a NF
```

### MULTI-PO SPLIT (1 item NF → N POs)
```
PO-A: 200 un produto X
PO-B: 300 un produto X
NF chegou: 450 un produto X

Resultado (via MatchAlocacao):
  PO-A: 0 un (consumido total, pode ser cancelado)
  PO-B: 50 un (saldo)
  PO Conciliador: 200 X (do PO-A) + 250 X (do PO-B) = 450 X
```

## Pre-requisitos para Consolidacao

1. Validacao com `status='aprovado'`
2. MatchNfPoItem com `status_match='match'` para cada item
3. MatchAlocacao com `odoo_po_line_id` preenchido para multi-PO
4. Conexao Odoo funcional

## Diagnostico Rapido de Erros

| Erro / Sintoma | Causa Provavel | Solucao |
|----------------|---------------|---------|
| `AttributeError: no attribute 'execute'` | Usando `odoo.execute()` | Trocar para `odoo.execute_kw()` |
| `Required field(s) missing` | Usando `create()` em vez de `copy()` | Usar `copy()` com `default` |
| `Expected singleton or list of IDs` | `unlink` com formato errado | `unlink([lista_ids])` em uma chamada |
| CFOP/impostos errados no conciliador | Copiando linha do PO de ref | Copiar de `aloc.odoo_po_line_id` |
| Linhas duplicadas apos copy() | `order_line=False` ignorado | Fallback: buscar e `unlink` linhas |
| Saldo maior que esperado | 2 itens NF na mesma linha PO | Cache `linhas_processadas` por `po_line_id` |
| Fornecedor nao encontrado | CNPJ sem formatacao | Formatar para `XX.XXX.XXX/XXXX-XX` |
| Quantidades imprecisas | Aritmetica com float | Usar `Decimal` para calculos |
| `Cannot confirm order with empty lines` | Todas linhas falharam | Verificar se PO tem linhas antes de confirmar |

## Checklist de Depuracao (ordem)

1. `odoo.authenticate()` retornou True?
2. CNPJ formatado encontrado em `res.partner`?
3. `pos_para_consolidar[0]['po_id']` existe no Odoo?
4. `copy()` retornou `novo_po_id` nao-None?
5. PO Conciliador esta limpo (sem linhas indesejadas)?
6. Cada `aloc.odoo_po_line_id` existe e tem `product_id`?
7. `product_qty` e `qty_received` sao numeros validos?
8. PO tem pelo menos 1 linha antes de `button_confirm`?
9. Campo `dfe_id` existe no modelo `purchase.order`?

## Ponto Critico: Multi-PO com copy()

```
Cabecalho: copy(PO-1) - herda empresa, fiscal, picking_type de PO-1
Linha A: copy(linha 101 do PO-1) - CFOP/impostos do PO-1
Linha B: copy(linha 202 do PO-2) - CFOP/impostos do PO-2  (NAO do PO-1!)
Linha C: copy(linha 303 do PO-3) - CFOP/impostos do PO-3  (NAO do PO-1!)
```

O PO de referencia (primeiro da lista) define APENAS o cabecalho.
Cada LINHA e copiada da sua propria origem via `aloc.odoo_po_line_id`.

## Cache de Consumo (mesma linha, multiplos itens NF)

```python
linhas_processadas = {}  # {po_line_id: Decimal total_consumido}

for aloc in alocacoes:
    consumo_anterior = linhas_processadas.get(aloc.odoo_po_line_id, Decimal('0'))
    consumo_total = consumo_anterior + qtd_alocada
    linhas_processadas[aloc.odoo_po_line_id] = consumo_total
    saldo = qtd_po_original - qtd_recebida - consumo_total
```

## Referencia Cruzada com Outras Skills

| Skill | Quando usar em vez desta |
|-------|--------------------------|
| `validacao-nf-po` | ANTES da consolidacao (match, de-para, divergencias) |
| `rastreando-odoo` | CONSULTAR documentos (nao executar) |
| `descobrindo-odoo-estrutura` | Explorar campos nao documentados |
| `executando-odoo-financeiro` | Operacoes financeiras (pagamentos, extratos) |
