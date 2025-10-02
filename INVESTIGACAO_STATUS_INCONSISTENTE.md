# 🔍 INVESTIGAÇÃO: Status Inconsistente em CarteiraPrincipal

## 📋 RESUMO DO PROBLEMA

**Sintoma**: Pedido `VCD2563375` tem:
- 18 itens com `status_pedido = 'Cotação'`
- 2 itens com `status_pedido = 'Pedido de venda'`

---

## 🎯 CAUSA RAIZ

### **TODAS as linhas VÊM do Odoo!**

Não há inserção manual. O problema está na **lógica de sincronização incremental**.

### **Como funciona a sincronização:**

#### **1. Busca no Odoo** ([carteira_service.py:129-138](app/odoo/services/carteira_service.py#L129-L138))

```python
domain = [
    ('order_id.write_date', '>=', data_corte),  # ⚠️ FILTRO POR PEDIDO
    ('order_id.state', 'in', ['draft', 'sent', 'sale']),
]
```

**Importante**: O filtro é `order_id.write_date` (data de modificação do **PEDIDO INTEIRO**)

#### **2. Mapeamento de Status** ([carteira_service.py:575](app/odoo/services/carteira_service.py#L575))

```python
'status_pedido': self._mapear_status_pedido(pedido.get('state', ''))
```

Cada linha recebe o status do **pedido completo** no momento da sincronização.

#### **3. UPSERT** ([carteira_service.py:1750-1756](app/odoo/services/carteira_service.py#L1750-L1756))

```python
if chave in registros_odoo_existentes:
    # ATUALIZAR
    for key, value in item.items():
        if hasattr(registro_existente, key) and key != 'id':
            setattr(registro_existente, key, value)  # ✅ ATUALIZA TUDO
```

**Chave**: `(num_pedido, cod_produto)` → **NÃO inclui status!**

---

## 🚨 CENÁRIOS POSSÍVEIS

### **Hipótese 1: Sincronização Parcial por Linhas Editadas**

```
No Odoo:
├─ Pedido VCD2563375 em 'draft' (Cotação)
├─ 20 linhas existem
└─ write_date do pedido: 2025-01-15 10:00

SINC 1 (10:30):
✅ Busca pedido com write_date >= últimos 40min
✅ TODAS as 20 linhas vêm com status="Cotação"

[Odoo] Usuário edita apenas 2 linhas (produtos 4639556, 4639590):
- linha.write_date = 11:05 ✅
- Outras 18 linhas NÃO editadas → write_date continua 10:00

SINC 2 (11:10) [modo incremental]:
❌ Busca apenas linhas com write_date >= 10:30
❌ Apenas 2 linhas vêm!
✅ Mas pedido foi confirmado → state='sale'
✅ As 2 linhas vêm com status="Pedido de venda"
✅ UPSERT atualiza apenas essas 2 linhas
❌ As outras 18 NÃO são atualizadas (não vieram do Odoo)
```

**❌ PROBLEMA**: Se o filtro for `sale.order.line.write_date` (linha individual)

### **Hipótese 2: Query Complexa com Subcondições**

Preciso verificar se a query usa `order_id.write_date` OU `line.write_date`.

---

## 🔬 SCRIPTS DE INVESTIGAÇÃO

### **1. SQL para Produção**

Arquivo: [`sql_investigar_status_inconsistente.sql`](sql_investigar_status_inconsistente.sql)

Execute na ordem:
1. Query 1-4: Verificar estado atual
2. Query 5: Buscar outros pedidos com problema
3. Query 6: Verificar duplicatas
4. Query 7-8: Análise detalhada

### **2. Python para Ambiente Local**

Arquivo: [`investigar_status_inconsistente.py`](investigar_status_inconsistente.py)

```bash
python investigar_status_inconsistente.py
```

---

## 🎯 PRÓXIMAS AÇÕES PARA VOCÊ

### **Passo 1: Confirmar no Render (Produção)**

Execute a Query 1 do SQL:

```sql
SELECT
    num_pedido,
    cod_produto,
    status_pedido,
    qtd_saldo_produto_pedido,
    expedicao
FROM carteira_principal
WHERE num_pedido = 'VCD2563375'
ORDER BY status_pedido, cod_produto;
```

**Me envie o resultado para analisarmos juntos.**

### **Passo 2: Verificar no Odoo**

1. Acesse o pedido `VCD2563375` no Odoo
2. Verifique:
   - ✅ Status ATUAL do pedido (`state`)
   - ✅ Quantas linhas ele tem
   - ✅ Se todas as linhas estão ativas

### **Passo 3: Investigar Código do Filtro**

Preciso verificar **EXATAMENTE** qual campo está sendo usado no filtro:
- `order_id.write_date` (pedido inteiro) → Teoricamente correto
- `write_date` (linha individual) → Causaria o problema

---

## 💡 SUSPEITAS PRINCIPAIS

### **1. Filtro Incremental Usa `line.write_date`**

Se a query for assim:
```python
domain = [
    ('write_date', '>=', data_corte),  # ❌ LINHA individual!
    ...
]
```

Apenas linhas editadas voltam → Inconsistência!

### **2. Odoo Tem Linhas com `state` Individual**

Improvável, mas possível: algumas linhas podem ter `state` próprio.

### **3. Cache Desatualizado**

Cache do sistema retorna pedidos antigos com status desatualizado.

---

## 🛠️ SOLUÇÕES PROPOSTAS

### **Solução 1: Correção Pós-Sincronização Automática**

Adicionar no final da sincronização:

```python
# Detectar pedidos com status inconsistente
pedidos_inconsistentes = detectar_status_inconsistente()

for num_pedido in pedidos_inconsistentes:
    # Buscar status correto no Odoo
    status_correto = buscar_status_odoo(num_pedido)

    # Atualizar TODOS os itens
    CarteiraPrincipal.query.filter_by(num_pedido=num_pedido).update({
        'status_pedido': status_correto
    })
```

### **Solução 2: Forçar Sincronização Completa de Pedidos Alterados**

Quando um pedido é detectado (por `order_id.write_date`), buscar **TODAS** as linhas dele:

```python
if modo_incremental:
    # Buscar pedidos alterados
    pedidos_alterados = buscar_pedidos_por_write_date()

    # Para cada pedido, buscar TODAS as linhas (não apenas alteradas)
    for pedido_id in pedidos_alterados:
        linhas = buscar_todas_linhas_pedido(pedido_id)
```

### **Solução 3: Alterar Chave de UPSERT**

**⚠️ NÃO RECOMENDADO**: Alterar chave para `(num_pedido, cod_produto, status_pedido)` causaria duplicatas!

---

## 📊 AGUARDANDO VALIDAÇÃO

**Execute a Query 1 do SQL e me envie o resultado!**

Com os dados reais, posso confirmar qual hipótese está correta e implementar a solução adequada.
