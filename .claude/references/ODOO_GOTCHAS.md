# GOTCHAS Criticos - Integracao Odoo

**Ultima verificacao:** Janeiro/2026

---

## Conexao e Timeout

| Gotcha | Impacto | Solucao |
|--------|---------|---------|
| `action_gerar_po_dfe` demora 60-90s | Timeout padrao (90s) pode falhar | `timeout_override=180` |
| Sessao PostgreSQL expira em ops longas | Dados nao salvos | `db.session.commit()` ANTES de ops Odoo longas |
| Circuit Breaker abre apos 5 falhas | Todas chamadas rejeitadas por 30s | Retry com backoff exponencial |
| XML-RPC nao suporta streaming | Memoria alta em grandes payloads | Paginacao com `limit` e `offset` |

### Timeout Override

```python
# Para operacoes longas (action_gerar_po_dfe, etc)
resultado = self.odoo.execute_kw(
    'l10n_br_ciel_it_account.dfe',
    'action_gerar_po_dfe',
    [[dfe_id]],
    {},
    timeout_override=180  # 3 minutos
)
```

### Commit Preventivo

```python
# ANTES de operacao Odoo longa (>30s)
db.session.commit()

# Operacao longa
po_id = self._gerar_po_odoo(dfe_id)  # 60-90s

# Re-buscar entidade (sessao pode ter expirado)
entidade = db.session.get(MinhaEntidade, entidade_id)
```

---

## Campos e Modelos que NAO EXISTEM

| Campo ERRADO | Modelo | Campo CORRETO |
|--------------|--------|---------------|
| `nfe_infnfe_dest_xnome` | dfe | NAO EXISTE - buscar via `res.partner` pelo CNPJ |
| `reserved_uom_qty` | stock.move.line | `quantity` (reservado) ou `qty_done` (realizado) |
| `lines_ids` | dfe | NAO EXISTE - buscar via `dfe.line` com filtro `dfe_id` |
| `odoo.execute()` | OdooConnection | `odoo.execute_kw()` |

### Exemplo Correto - Buscar Razao Social

```python
# ERRADO:
dfe = odoo.read('dfe', [dfe_id], ['nfe_infnfe_dest_xnome'])  # Campo NAO existe!

# CORRETO:
dfe = odoo.read('dfe', [dfe_id], ['partner_id'])
partner_id = dfe[0]['partner_id'][0]
partner = odoo.read('res.partner', [partner_id], ['name', 'l10n_br_cnpj'])
razao_social = partner[0]['name']
```

### Exemplo Correto - stock.move.line

```python
# ERRADO:
move_line = odoo.read('stock.move.line', [line_id], ['reserved_uom_qty'])  # NAO existe!

# CORRETO:
move_line = odoo.read('stock.move.line', [line_id], ['quantity', 'qty_done'])
qtd_reservada = move_line[0]['quantity']
qtd_realizada = move_line[0]['qty_done']
```

---

## Formato de Campos

| Tipo | Retorno Odoo | Como Tratar |
|------|--------------|-------------|
| many2one | `[123, 'Nome']` ou `False` | `if campo: id = campo[0]` |
| many2many | `[1, 2, 3]` ou `[]` | Lista de IDs |
| date/datetime | String ISO | `datetime.fromisoformat()` |
| monetary | Float | `Decimal(str(valor))` para precisao |

```python
# Tratamento seguro de many2one
partner = record.get('partner_id')
if partner:
    partner_id = partner[0]    # 123
    partner_name = partner[1]  # 'Empresa X'
else:
    partner_id = None
```

---

## Comportamentos Inesperados

| Comportamento | Contexto | Solucao |
|---------------|----------|---------|
| `button_validate` retorna `None` | stock.picking | **SUCESSO!** `if 'cannot marshal None' in str(e): pass` |
| PO criado com operacao fiscal ERRADA | Tomador FB mas PO vai para CD | Mapeamento de-para `OPERACAO_DE_PARA[op_atual][company_destino]` |
| Impostos ZERADOS apos write no header | account.move | Re-buscar valor do DFe; chamar `onchange_l10n_br_calcular_imposto` |
| Lote duplicado | stock.lot | Verificar existencia antes de `lot_name`, usar `lot_id` se existir |
| Quality checks pendentes | button_validate falha | Processar TODOS checks (`do_pass`/`do_fail`/`do_measure`) ANTES |

### Tratamento button_validate

```python
try:
    resultado = odoo.execute_kw('stock.picking', 'button_validate', [[picking_id]])
except Exception as e:
    if 'cannot marshal None' in str(e):
        # SUCESSO! button_validate retorna None que XML-RPC nao consegue serializar
        pass
    else:
        raise
```

### Quality Checks - Ordem Critica

```python
# PROCESSAR ANTES de button_validate!
quality_checks = odoo.search_read('quality.check',
    [['picking_id', '=', picking_id], ['quality_state', '=', 'none']],
    ['id', 'test_type'])

for qc in quality_checks:
    if qc['test_type'] == 'passfail':
        odoo.execute_kw('quality.check', 'do_pass', [[qc['id']]])
    elif qc['test_type'] == 'measure':
        odoo.write('quality.check', [qc['id']], {'measure': valor_medido})
        odoo.execute_kw('quality.check', 'do_measure', [[qc['id']]])

# SO DEPOIS validar picking
odoo.execute_kw('stock.picking', 'button_validate', [[picking_id]])
```

---

## Ordem de Operacoes Critica

| Operacao | Dependencia | Erro se Inverter |
|----------|-------------|------------------|
| Sync FATURAMENTO | Antes de CARTEIRA | Tags sobrescritas, dados inconsistentes |
| Quality checks | Antes de button_validate | `UserError: You need to pass the quality checks` |
| Recalcular impostos | Apos configurar campos Invoice | Valores zerados ou incorretos |
| `db.session.commit()` | Antes de ops Odoo longas (>30s) | Sessao PostgreSQL expira |

---

## Matriz de Erros

| Erro | Causa | Solucao |
|------|-------|---------|
| `Authentication failed` | Credenciais invalidas | Verificar `odoo_config.py` |
| `Circuit breaker is OPEN` | 5 falhas consecutivas | Aguardar 30s ou verificar Odoo |
| `cannot marshal None` | Metodo retornou None | **SUCESSO!** Tratar com try/except |
| `OperationalError` | Conexao DB local | Verificar PostgreSQL |
| `Timeout` | Operacao lenta | Usar `timeout_override` |
| `Field 'X' does not exist` | Versao Odoo diferente | Usar `SafeConnection` |
| `N+1 query detected` | Loop com queries | Cache local + batch |
| `Duplicate key` | Registro ja existe | Verificar antes de criar |

---

## Circuit Breaker

```
CLOSED ──5 falhas──→ OPEN ──30s──→ HALF_OPEN ──1 sucesso──→ CLOSED
                                      │ 1 falha → OPEN
```

- **CLOSED:** Operacao normal
- **OPEN:** Rejeita todas as chamadas
- **HALF_OPEN:** Testa uma chamada

**Arquivo:** `app/odoo/utils/circuit_breaker.py`
