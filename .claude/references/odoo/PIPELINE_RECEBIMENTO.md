# Pipeline de Recebimento de Compras - Fases 1-4

**Ultima verificacao:** Janeiro/2026

---

## Visao Geral

```
FASE 1: Validacao Fiscal
    ↓
FASE 2: Match NF x PO (Validacao Comercial)
    ↓
FASE 3: Consolidacao PO
    ↓
FASE 4: Recebimento Fisico
```

---

## FASE 1: Validacao Fiscal

**Service:** `app/recebimento/services/validacao_fiscal_service.py`
**Tela:** `/recebimento/divergencias-fiscais`

### Entrada
- DFE com `l10n_br_tipo_pedido='compra'` e `state='done'`

### Validacao
- NCM vs perfil fiscal
- CFOP vs operacao esperada
- CST vs regime tributario

### Status de Saida
| Status | Significado | Proxima Acao |
|--------|-------------|--------------|
| `pendente` | Aguardando validacao | Processar |
| `aprovado` | Passou validacao fiscal | Ir para Fase 2 |
| `bloqueado` | Divergencia fiscal grave | Revisar manualmente |
| `primeira_compra` | Produto novo sem De-Para | Cadastrar De-Para |

### Tabelas Locais
- `validacao_fiscal` - Registro de validacao
- `perfil_fiscal` - Configuracao esperada por fornecedor/produto

---

## FASE 2: Match NF x PO (Validacao Comercial)

**Service:** `app/recebimento/services/validacao_nf_po_service.py`
**Tela:** `/recebimento/validacoes-nf-po`

### Entrada
- DFE aprovado na Fase 1

### Tolerancias de Validacao
| Tipo | Percentual | Regra |
|------|------------|-------|
| Quantidade | 10% | `abs(qtd_nf - qtd_po) / qtd_po <= 0.10` |
| Preco | 0% | `preco_nf == preco_po` (exato) |
| Data entrega | -5 a +15 dias | Configuravel |

### Vinculacao DFE → PO

**3 Caminhos de Vinculacao:**

| # | Campo | Modelo | Estatistica |
|---|-------|--------|-------------|
| 1 | `purchase_id` | DFE → PO | 14.6% (excepcional) |
| 2 | `purchase_fiscal_id` | DFE → PO | 75% dos status=06 |
| **3** | **`PO.dfe_id`** | **PO → DFE** | **85.4% dos status=04** |

> **PRINCIPAL para status=04:** Caminho 3 (PO.dfe_id)

### Status de Saida
| Status | Significado | Divergencias |
|--------|-------------|--------------|
| `pendente` | Aguardando validacao | - |
| `aprovado` | Match OK | Nenhuma |
| `aprovado_divergencia` | Match com divergencias toleraveis | Lista de divergencias |
| `bloqueado` | Divergencia grave | Requer acao manual |

### Tabelas Locais
- `validacao_nf_po` - Registro de validacao
- `validacao_nf_po_item` - Itens validados
- `de_para_fornecedor` - Mapeamento codigo fornecedor → produto interno

---

## FASE 3: Consolidacao PO

**Service:** `app/recebimento/services/odoo_po_service.py`
**Tela:** `/recebimento/preview-consolidacao`

### Entrada
- Match aprovado na Fase 2

### Processo
1. **copy()** do PO original → PO Conciliador
2. Criar linhas do PO Conciliador (quantidades ajustadas)
3. Ajustar saldos no PO original
4. Vincular DFe ao PO Conciliador
5. Confirmar PO Conciliador

### Cenarios de Split

| Cenario | Acao |
|---------|------|
| NF = PO inteiro | Usa PO original |
| NF < PO (parcial) | Split → PO Conciliador |
| 1 NF = N POs | Consolida em 1 PO Conciliador |
| N NFs = 1 PO | Multiplos splits |

### Tabelas Locais
- `consolidacao_po` - Registro de consolidacao
- `consolidacao_po_item` - Itens consolidados

---

## FASE 4: Recebimento Fisico

**Service:** `app/recebimento/services/recebimento_fisico_odoo_service.py`
**Tela:** `/recebimento/recebimento-fisico`
**Worker:** RQ async (Redis Queue)

### Entrada
- Picking com `state='assigned'`
- PO Conciliador confirmado

### 8 Passos do Recebimento

```
1. Validar picking existe e esta assigned
2. Buscar move_lines do picking
3. Para cada linha:
   3.1. Verificar/criar lote (stock.lot)
   3.2. Preencher qty_done
   3.3. Preencher lot_id ou lot_name
4. Processar quality checks
5. Validar picking (button_validate)
6. Atualizar status local
7. Registrar auditoria
8. Notificar conclusao
```

### Quality Checks (OBRIGATORIO antes de button_validate)

| Tipo | Metodo | Campos |
|------|--------|--------|
| `passfail` | `do_pass()` ou `do_fail()` | - |
| `measure` | `write({'measure': X})` + `do_measure()` | `measure` |

```python
# ORDEM CRITICA:
# 1. Processar TODOS quality checks
for qc in quality_checks:
    if qc['test_type'] == 'passfail':
        odoo.execute_kw('quality.check', 'do_pass', [[qc['id']]])
    elif qc['test_type'] == 'measure':
        odoo.write('quality.check', [qc['id']], {'measure': valor})
        odoo.execute_kw('quality.check', 'do_measure', [[qc['id']]])

# 2. SO DEPOIS validar picking
odoo.execute_kw('stock.picking', 'button_validate', [[picking_id]])
```

### Lotes (stock.lot)

```python
# Verificar se lote existe
lote_existente = odoo.search('stock.lot', [
    ['name', '=', nome_lote],
    ['product_id', '=', product_id]
], limit=1)

if lote_existente:
    # Usar lot_id
    odoo.write('stock.move.line', [line_id], {'lot_id': lote_existente[0]})
else:
    # Criar via lot_name
    odoo.write('stock.move.line', [line_id], {'lot_name': nome_lote})
```

### Status do Picking

| State | Significado | Acao |
|-------|-------------|------|
| `draft` | Rascunho | Aguardar |
| `waiting` | Aguardando | Aguardar |
| `confirmed` | Confirmado | Aguardar |
| `assigned` | **Pronto para recebimento** | **Processar** |
| `done` | Concluido | Finalizado |
| `cancel` | Cancelado | Ignorar |

### Tabelas Locais
- `recebimento_fisico` - Registro de recebimento
- `recebimento_fisico_item` - Itens recebidos
- `picking_recebimento` - Espelho do stock.picking
- `picking_recebimento_move_line` - Espelho do stock.move.line

---

## Fluxo de Status Completo

```
DFE (Odoo)
│
├─ l10n_br_status = 04 (PO Vinculado)
│
└─ FASE 1 (Local)
   validacao_fiscal.status = aprovado
   │
   └─ FASE 2 (Local)
      validacao_nf_po.status = aprovado
      │
      └─ FASE 3 (Odoo)
         purchase.order (Conciliador) state = purchase
         │
         └─ FASE 4 (Odoo)
            stock.picking.state = done
            │
            └─ DFE l10n_br_status = 06 (Concluido)
```

---

## Skills por Fase

| Fase | Skill | Uso |
|------|-------|-----|
| 1 | `validacao-nf-po` | Debug divergencias fiscais |
| 2 | `validacao-nf-po` | Debug match NF x PO, De-Para |
| 3 | `conciliando-odoo-po` | Criar PO Conciliador, split |
| 4 | `recebimento-fisico-odoo` | Lotes, quality checks, button_validate |
| Cross | `especialista-odoo` | Problemas entre fases |
| Cross | `rastreando-odoo` | Rastrear documentos |
