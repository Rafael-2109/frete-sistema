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
| `purchase_ids` | dfe | `purchase_id` (many2one → purchase.order, retorna `[id, 'name']` ou `False`) |
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
| Integer `0` buscado com `=` não encontra | Odoo armazena int 0 como `False` no PG | Usar `'in', [0, False]` |
| `button_validate` retorna `None` | stock.picking | **SUCESSO!** `if 'cannot marshal None' in str(e): pass` |
| PO criado com operacao fiscal ERRADA | Tomador FB mas PO vai para CD | Mapeamento de-para `OPERACAO_DE_PARA[op_atual][company_destino]` |
| Impostos ZERADOS apos write no header | account.move | Re-buscar valor do DFe; chamar `onchange_l10n_br_calcular_imposto` |
| Lote duplicado | stock.lot | Verificar existencia antes de `lot_name`, usar `lot_id` se existir |
| Quality checks pendentes | button_validate falha | Processar TODOS checks (`do_pass`/`do_fail`/`do_measure`) ANTES |

### Integer 0 vs False no ORM Odoo

O Odoo armazena campos Integer com valor `0` como `False` no PostgreSQL.
Buscar com `['campo', '=', 0]` **não encontra** esses registros.

```python
# ERRADO: não encontra registros com parcela=0 (armazenados como False)
titulos = odoo.search_read('account.move.line',
    [['l10n_br_cobranca_parcela', '=', 0]], ...)

# CORRETO: buscar tanto 0 quanto False
titulos = odoo.search_read('account.move.line',
    [['l10n_br_cobranca_parcela', 'in', [0, False]]], ...)

# CORRETO com variável condicional (quando parcela vem de input):
parcela_odoo = parcela_to_odoo(titulo.parcela)
if parcela_odoo:
    filtro = ['l10n_br_cobranca_parcela', '=', parcela_odoo]
else:
    filtro = ['l10n_br_cobranca_parcela', 'in', [0, False]]
```

**Campos afetados conhecidos:** `l10n_br_cobranca_parcela` (account.move.line)

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

## Extrato Bancario: 3 Campos que o Odoo NAO Preenche para Boletos

Para boletos bancarios, o Odoo **NAO** auto-preenche 3 campos do extrato porque o `payment_ref` eh generico ("DEB.TIT.COMPE"). O Odoo so auto-preenche para transacoes identificaveis (TED/PIX com CNPJ).

| Campo | Modelo | Problema | Correcao |
|-------|--------|----------|----------|
| `partner_id` | `account.bank.statement.line` | Fica `False` | Atualizar com `res.partner` do titulo |
| `account_id` | `account.move.line` (do extrato) | Fica na conta TRANSITORIA (22199) | Trocar para PENDENTES (26868) **ANTES** de reconciliar |
| `name` / `payment_ref` | `account.bank.statement.line` + `account.move.line` | Generico, sem identificacao | Atualizar com rotulo formatado |

**Rotulo padrao:** `"Pagamento de fornecedor R$ {valor_br} - {FORNECEDOR} - {DD/MM/YYYY}"`

### Regra: SEMPRE Usar preparar_extrato_para_reconciliacao() (corrigido 2026-02-19)

**NUNCA** fazer as operacoes em chamadas separadas (bug O11/O12). Usar metodo consolidado:

```python
from app.financeiro.services.baixa_pagamentos_service import BaixaPagamentosService

baixa_service = BaixaPagamentosService()

# 1. ANTES de reconciliar: preparar extrato (conta + partner + rotulo em UM ciclo)
rotulo = BaixaPagamentosService.formatar_rotulo_pagamento(
    valor=float(valor_pago),
    nome_fornecedor=nome_parceiro,
    data_pagamento=data_pagamento,
)
baixa_service.preparar_extrato_para_reconciliacao(
    move_id=extrato_move_id,
    statement_line_id=statement_line_id,
    partner_id=partner_id,
    rotulo=rotulo,
)

# 2. Buscar linha de debito do extrato (agora na conta PENDENTES)
debit_line_extrato = baixa_service.buscar_linha_debito_extrato(extrato_move_id)

# 3. Reconciliar POR ULTIMO
baixa_service.reconciliar(payment_credit_line_id, debit_line_extrato)
```

### Services que JA Implementam

| Service | Metodo Consolidado |
|---------|-------------------|
| `baixa_pagamentos_service.py` | `preparar_extrato_para_reconciliacao()` (publico, IDs raw) + helpers legados (`trocar_conta_move_line_extrato`, `atualizar_statement_line_partner`, `atualizar_rotulo_extrato`) |
| `comprovante_lancamento_service.py` | Usa `preparar_extrato_para_reconciliacao()` em `lancar_no_odoo()` e `_reconciliar_grupo_com_extrato()` |
| `extrato_conciliacao_service.py` | `_preparar_extrato_para_reconciliacao()` (privado, opera em ExtratoItem) |
| `vincular_extrato_fatura_excel.py` (script) | `batch_write_partner_statement_lines()`, `batch_write_conta_pendentes()`, `ajustar_name_linha_extrato()` |

### Services que NAO Precisam (referencia)

| Service | Motivo |
|---------|--------|
| `baixa_titulos_service.py` | So reconcilia payment↔titulo, **nunca** toca em extrato |
| `extrato_service.py` | Apenas importa extratos do Odoo (READ-ONLY) |
| `sincronizacao_extratos_service.py` | Sincroniza dados locais, nao faz reconcile no Odoo |

---

## Correcao Retroativa de Extrato Ja Reconciliado

Quando um extrato JA foi reconciliado (`is_reconciled=True`) mas os 3 campos estao incorretos (registros anteriores ao commit `13cef821` de 03/02/2026), a correcao exige um fluxo especifico de 7 passos.

### ⚠️ GOTCHAS Criticos

1. **Odoo RECRIA move lines ao voltar para draft**: Apos `button_draft` + qualquer edicao, os IDs das `account.move.line` mudam. Usar IDs antigos causa `MissingError`.
2. **`account_id` DEVE ser o ULTIMO campo alterado antes do `action_post`**: Write na `account.bank.statement.line` (partner_id, payment_ref) faz Odoo REGENERAR as `account.move.line` associadas, revertendo qualquer `account_id` ja escrito e potencialmente mudando IDs. Sempre re-buscar IDs apos write na statement_line.
3. **Assimetria debito/credito**: Para pagamentos (fornecedor), TRANSITORIA esta na linha de DEBITO. Para recebimentos (cliente), TRANSITORIA esta na linha de CREDITO. Sempre verificar AMBOS.

### Fluxo Completo (7 Passos)

```
1. DESCONCILIAR
   → Buscar account.partial.reconcile ligados ao move_id
   → Guardar counterpart_ids (lines do PAYMENT, nao do extrato)
   → Executar unlink nos partial_reconcile

2. BUTTON_DRAFT
   → connection.execute_kw('account.move', 'button_draft', [[move_id]])

3. ATUALIZAR PARTNER_ID
   → connection.execute_kw('account.bank.statement.line', 'write',
     [[statement_line_id], {'partner_id': partner_id}])

4. ATUALIZAR ROTULO
   → connection.execute_kw('account.bank.statement.line', 'write',
     [[statement_line_id], {'payment_ref': rotulo}])
   → Buscar NOVAS move lines: search_read('account.move.line', [['move_id', '=', move_id]])
   → connection.execute_kw('account.move.line', 'write', [line_ids, {'name': rotulo}])

5. TROCAR ACCOUNT_ID (ULTIMO antes do post!)
   → Buscar move line com account_id = TRANSITORIA (22199)
   → Verificar debit > 0 OU credit > 0 (ambos os lados!)
   → connection.execute_kw('account.move.line', 'write',
     [[line_id], {'account_id': CONTA_PAGAMENTOS_PENDENTES}])  # 26868

6. ACTION_POST
   → connection.execute_kw('account.move', 'action_post', [[move_id]])

7. RE-RECONCILIAR
   → Buscar NOVA move line com account_id = 26868 no move_id
   → Para cada counterpart_id guardado no passo 1:
     connection.execute_kw('account.move.line', 'reconcile',
       [[new_line_id, counterpart_id]])
```

### Identificacao de Counterparts (Passo 1)

```python
# Buscar move lines do extrato
linhas = connection.search_read('account.move.line', [['move_id', '=', move_id]], ['id'])
extrato_line_ids = {ln['id'] for ln in linhas}

# Para cada partial_reconcile, identificar qual lado eh o counterpart
for pr in partial_reconciles:
    debit_id = pr['debit_move_id'][0]
    credit_id = pr['credit_move_id'][0]
    if debit_id in extrato_line_ids and credit_id not in extrato_line_ids:
        counterpart_ids.append(credit_id)  # Line do payment
    elif credit_id in extrato_line_ids and debit_id not in extrato_line_ids:
        counterpart_ids.append(debit_id)   # Line do payment
```

### Script de Referencia

Script completo: `scripts/correcao_campos_extrato_odoo.py`

Modos disponiveis:
- `--verificar-comprovante ID` / `--corrigir-comprovante ID`
- `--verificar-extrato ID` / `--corrigir-extrato ID`
- `--batch-comprovantes` / `--batch-extratos`
- `--verificar-amostra`

> **Resultado da execucao (04/02/2026)**: 20 comprovantes (20/20 OK) + 1.504 extratos (1.504/1.504 OK). Total: 1.524 registros processados com 0 erros, 0 parciais.
>
> **Bug corrigido**: `_buscar_partner_do_titulo_odoo()` pegava o PRIMEIRO resultado de `account.move` com `ref ilike titulo_nf`, mas esse resultado podia ter `partner_id=False` (move de entry sem partner). Corrigido para iterar TODOS os resultados ate encontrar um com partner valido.

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

---

## Lotes com Data de Validade

| Gotcha | Impacto | Solucao |
|--------|---------|---------|
| `lot_name` NAO propaga `expiration_date` | Lote criado sem data de validade | Criar stock.lot manualmente primeiro |

### Exemplo Correto - Criar Lote com Validade

```python
# Verificar se produto usa validade
product = odoo.read('product.product', [product_id], ['tracking', 'use_expiration_date'])
if product[0].get('use_expiration_date'):
    # Verificar se lote ja existe
    lote_existente = odoo.search('stock.lot', [
        ['name', '=', nome_lote],
        ['product_id', '=', product_id],
        ['company_id', '=', company_id]
    ], limit=1)

    if lote_existente:
        # Atualizar validade se necessario
        odoo.write('stock.lot', lote_existente, {'expiration_date': '2026-06-15 00:00:00'})
        lot_id = lote_existente[0]
    else:
        # Criar lote manualmente
        lot_id = odoo.create('stock.lot', {
            'name': nome_lote,
            'product_id': product_id,
            'company_id': company_id,
            'expiration_date': '2026-06-15 00:00:00'  # Formato datetime string
        })

    # Usar lot_id (NAO lot_name!)
    odoo.write('stock.move.line', [line_id], {'lot_id': lot_id, 'quantity': qtd})
else:
    # Produto sem validade - usar lot_name normalmente
    odoo.write('stock.move.line', [line_id], {'lot_name': nome_lote, 'quantity': qtd})
```
