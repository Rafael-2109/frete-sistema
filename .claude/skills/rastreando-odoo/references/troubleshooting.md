# Troubleshooting - Rastreamento Odoo

## Busca nao encontra o PO

**Problema**: Buscar "C2513147" retorna "parceiro" em vez de "po"

**Solucao**: Verificar se o pattern aceita o formato. Formatos aceitos:
- `PO00123` - Padrao Odoo
- `C2513147` - Formato alternativo

## Busca inversa: Fatura para DFE

**Problema**: Tenho a Invoice e preciso do DFE vinculado

**Solucao**: Usar busca por `invoice_ids`:
```python
# Buscar DFE vinculado a Invoice 426987
dfes = odoo.search_read('l10n_br_ciel_it_account.dfe',
    [('invoice_ids', 'in', [426987])],
    fields=['id', 'protnfe_infnfe_chnfe', 'nfe_infnfe_ide_nnf'])
```

## Modelo DFE nao encontrado

**Problema**: Tentei buscar em `l10n_br_fiscal.document` sem sucesso

**Solucao**: O modelo correto eh `l10n_br_ciel_it_account.dfe`

## Campos de impostos nao aparecem

**Problema**: Campos como `vicms`, `vpis` nao retornam valores

**Solucao**: Usar nomes completos dos campos:
- `nfe_infnfe_total_icmstot_vicms` (ICMS)
- `nfe_infnfe_total_icmstot_vpis` (PIS)
- `nfe_infnfe_total_icmstot_vcofins` (COFINS)

## Fatura nao vinculada ao DFE

**Problema**: DFE existe mas `invoice_ids` esta vazio

**Solucao**: Verificar se o DFE foi manifestado e importado corretamente. Buscar fatura pela chave NF-e:
```python
faturas = odoo.search_read('account.move',
    [('l10n_br_chave_nf', '=', chave_44_digitos)],
    fields=['id', 'name', 'partner_id'])
```

## Titulos nao aparecem na fatura

**Problema**: Fatura existe mas titulos (account.move.line) nao retornam

**Solucao**: Filtrar apenas linhas com conta de pagavel/recebivel:
```python
titulos = odoo.search_read('account.move.line',
    [('move_id', '=', fatura_id),
     ('account_id.account_type', 'in', ['asset_receivable', 'liability_payable'])],
    fields=['id', 'date_maturity', 'debit', 'credit', 'reconciled'])
```

## Conciliacao parcial vs total

**Problema**: Titulo mostra `reconciled=False` mas tem pagamento parcial

**Solucao**: Verificar `matched_debit_ids` e `matched_credit_ids` para conciliacoes parciais. O campo `reconciled=True` so aparece quando totalmente conciliado.
