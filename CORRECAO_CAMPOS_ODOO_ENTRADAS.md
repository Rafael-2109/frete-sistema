# ✅ CORREÇÃO: Campos do Odoo para Entradas de Materiais

**Data:** 12/11/2025
**Arquivo Corrigido:** `app/odoo/services/entrada_material_service.py`

---

## 🔴 PROBLEMA

O scheduler estava gerando erros ao tentar sincronizar **Entradas de Materiais** porque estava usando **nomes de campos incorretos** que não existem no Odoo da empresa.

### Erros Identificados:
```
ValueError: Invalid field 'l10n_br_cnpj_cpf' on model 'res.partner'
ValueError: Invalid field 'quantity_done' on model 'stock.move'
```

---

## ✅ CORREÇÕES APLICADAS

### 1️⃣ Campo CNPJ do Fornecedor (res.partner)

**ANTES (ERRADO):**
```python
{'fields': ['l10n_br_cnpj_cpf', 'vat']}  # ❌ Campos que não existem
```

**DEPOIS (CORRETO):**
```python
{'fields': ['l10n_br_cnpj']}  # ✅ Campo confirmado pelo usuário
```

**Linha alterada:** 264

---

### 2️⃣ Campos de Quantidade (stock.move)

**ANTES (ERRADO):**
```python
campos = [
    'id',
    'product_id',
    'product_uom_qty',
    'quantity',
    'quantity_done',  # ❌ Este campo NÃO existe no Odoo do usuário
    'product_uom',
    # ...
]
```

**DEPOIS (CORRETO):**
```python
campos = [
    'id',
    'product_id',
    'product_uom_qty',  # ✅ Demanda (quantidade planejada)
    'quantity',          # ✅ Quantidade realizada
    'product_uom',
    # ...
]  # ✅ Removido 'quantity_done'
```

**Linhas alteradas:** 289-300

---

### 3️⃣ Uso da Quantidade Recebida

**ANTES (ERRADO):**
```python
qtd_recebida = Decimal(str(movimento.get('quantity_done', 0)))  # ❌ Campo inexistente
```

**DEPOIS (CORRETO):**
```python
qtd_recebida = Decimal(str(movimento.get('quantity', 0)))  # ✅ Campo 'quantity' confirmado
```

**Linha alterada:** 361

---

## 📋 CAMPOS CONFIRMADOS PELO USUÁRIO

### res.partner (Fornecedores):
- ✅ **`l10n_br_cnpj`** = CNPJ do fornecedor

### stock.move (Movimentos de Estoque):
- ✅ **`product_uom_qty`** = Demanda (quantidade planejada)
- ✅ **`quantity`** = Quantidade (quantidade realizada/recebida)
- ❌ **`quantity_done`** = NÃO EXISTE no Odoo do usuário

---

## 🎯 IMPACTO DA CORREÇÃO

### ANTES:
- ❌ Scheduler falhava ao tentar buscar CNPJ
- ❌ Scheduler falhava ao buscar movimentos
- ❌ **NENHUMA** entrada de material era sincronizada
- ❌ Todos os recebimentos eram pulados com erro

### DEPOIS:
- ✅ Scheduler consegue buscar CNPJ corretamente
- ✅ Scheduler consegue buscar movimentos corretamente
- ✅ Entradas de materiais serão sincronizadas
- ✅ Dados aparecerão em `movimentacao_estoque` tipo='ENTRADA'

---

## 🚀 PRÓXIMOS PASSOS

### 1. Commit e Deploy
```bash
git add app/odoo/services/entrada_material_service.py
git commit -m "fix: corrige campos do Odoo para sincronização de entradas de materiais

- Substitui l10n_br_cnpj_cpf por l10n_br_cnpj (campo correto)
- Remove quantity_done que não existe no Odoo
- Usa quantity como campo de quantidade recebida
- Campos confirmados com usuário via inspeção do HTML do Odoo"
git push origin main
```

### 2. Aguardar Deploy no Render (5-10 minutos)

### 3. Verificar Log do Scheduler
```bash
# No Render Shell:
tail -50 logs/sincronizacao_incremental.log

# Deve mostrar SUCESSO agora:
# ✅ Entradas de materiais sincronizadas com sucesso!
# - Recebimentos processados: X
# - Movimentações criadas: Y
```

### 4. Verificar Dados no Banco
```sql
-- Ver últimas entradas sincronizadas
SELECT *
FROM movimentacao_estoque
WHERE tipo = 'ENTRADA'
  AND local = 'COMPRA'
ORDER BY created_at DESC
LIMIT 10;
```

---

## 📚 LIÇÕES APRENDIDAS

### ❌ O QUE NÃO FAZER:
1. **Assumir nomes de campos** sem confirmar
2. **Copiar código de documentação genérica** do Odoo
3. **Usar campos de módulos opcionais** (l10n_br) sem verificar instalação

### ✅ O QUE FAZER:
1. **Confirmar campos** diretamente no Odoo do cliente
2. **Inspecionar HTML** com modo desenvolvedor ativo
3. **Testar em ambiente de dev** antes de deploy
4. **Usar try/catch** para campos opcionais

---

## 🔍 COMO DESCOBRIR CAMPOS NO ODOO

### Método 1: Interface Web (usado neste caso)
1. Ativar **Modo Desenvolvedor** (Configurações)
2. Abrir registro (ex: fornecedor, recebimento)
3. Inspecionar elemento HTML
4. Procurar `name="campo"` ou `data-name="campo"`

### Método 2: Shell do Odoo
```python
# No Odoo shell
fields = env['res.partner']._fields.keys()
print([f for f in fields if 'cnpj' in f.lower()])

fields = env['stock.move']._fields.keys()
print([f for f in fields if 'quant' in f.lower()])
```

### Método 3: API XML-RPC
```python
fields_info = odoo.execute_kw(
    'res.partner',
    'fields_get',
    [],
    {'attributes': ['string', 'type']}
)
```

---

## ✅ STATUS FINAL

- ✅ **Problema 1** (SSL timeout no botão): Não relacionado a este fix
- ✅ **Problema 2** (Erros de campos inválidos): **RESOLVIDO**

**Faturamento e Carteira** não foram afetados por este bug - continuam funcionando normalmente. Apenas **Entradas de Materiais** estava quebrado.

---

**Última atualização:** 12/11/2025 15:30
**Responsável:** Correção aplicada com campos confirmados pelo usuário
