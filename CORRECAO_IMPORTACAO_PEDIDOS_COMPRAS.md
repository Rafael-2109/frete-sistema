# Correção de Importação de Pedidos de Compras do Odoo

**Data:** 05/11/2025
**Problema:** Erro de chave duplicada na importação de pedidos de compras
**Status:** ✅ CORRIGIDO

---

## 🔴 PROBLEMA IDENTIFICADO

### Erro Original:
```
UniqueViolation: duplicate key value violates unique constraint "ix_pedido_compras_num_pedido"
DETAIL: Key (num_pedido)=(C2511843) already exists.
```

### Causa Raiz (2 problemas):

#### 1. **Constraint Incorreta no Modelo**
- **Local:** `app/manufatura/models.py:214`
- **Problema:** Campo `num_pedido` tinha `unique=True`
- **Impacto:** Não permitia múltiplos produtos no mesmo pedido

```python
# ❌ ANTES (INCORRETO):
num_pedido = db.Column(db.String(30), unique=True, nullable=False, index=True)
```

#### 2. **Lógica de Verificação Falha**
- **Local:** `app/odoo/services/manufatura_service.py:191-195`
- **Problema:** Verificava apenas `odoo_id` para pular pedidos já importados
- **Impacto:** Ao encontrar 1 produto importado, pulava TODOS os produtos daquele pedido

```python
# ❌ ANTES (INCORRETO):
existe = PedidoCompras.query.filter_by(odoo_id=str(ped_odoo['id'])).first()
if not existe:
    # Processar linhas...
```

**Cenário de Falha:**
- Pedido C2511843 do Odoo tem 3 produtos (A, B, C)
- Produto A: ✅ Insere OK (odoo_id=88278 não existe)
- Produto B: ❌ PULA (encontrou odoo_id=88278 do produto A)
- Produto C: ❌ PULA (encontrou odoo_id=88278 do produto A)
- Ao tentar inserir novamente: **Erro de chave duplicada**

---

## ✅ SOLUÇÃO IMPLEMENTADA

### 1. Correção do Modelo PedidoCompras

**Arquivo:** `app/manufatura/models.py`

```python
# ✅ DEPOIS (CORRETO):
num_pedido = db.Column(db.String(30), nullable=False, index=True)  # Removido unique=True

# Adicionado constraint composta:
__table_args__ = (
    db.UniqueConstraint('num_pedido', 'cod_produto', name='uq_pedido_compras_num_cod_produto'),
)

# Adicionado campo de auditoria:
atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

**Resultado:** Agora permite múltiplos produtos no mesmo `num_pedido`, garantindo unicidade pela combinação `(num_pedido, cod_produto)`.

---

### 2. Correção da Lógica de Importação

**Arquivo:** `app/odoo/services/manufatura_service.py`

```python
# ✅ DEPOIS (CORRETO):
for ped_odoo in pedidos:
    try:
        # Buscar linhas do pedido PRIMEIRO (não verifica odoo_id aqui)
        linhas = self.connection.search_read(
            'purchase.order.line',
            [['order_id', '=', ped_odoo['id']]],
            ['product_id', 'product_qty', 'price_unit', 'price_tax', 'price_total']
        )

        # Processar cada linha individualmente
        for linha in linhas:
            num_pedido = ped_odoo.get('name', f"PO-{ped_odoo['id']}")
            cod_produto = str(linha['product_id'][0]) if linha.get('product_id') else None

            # ✅ Verificar pela constraint REAL: (num_pedido, cod_produto)
            pedido_existente = PedidoCompras.query.filter_by(
                num_pedido=num_pedido,
                cod_produto=cod_produto
            ).first()

            if pedido_existente:
                # Atualizar
                pedido_existente.qtd_produto_pedido = Decimal(str(linha.get('product_qty', 0)))
                pedido_existente.status_odoo = ped_odoo.get('state', 'draft')
                pedido_existente.atualizado_em = datetime.now()
            else:
                # Criar novo
                pedido = PedidoCompras(...)
                db.session.add(pedido)
```

**Resultado:** Cada produto é verificado individualmente pela constraint real, permitindo múltiplos produtos no mesmo pedido.

---

## 📁 SCRIPTS DE MIGRAÇÃO

### Para Ambiente Local:
```bash
source venv/bin/activate
python3 scripts/corrigir_constraint_pedido_compras.py
```

### Para Render (Shell PostgreSQL):
```bash
# Copiar e executar o conteúdo de:
scripts/corrigir_constraint_pedido_compras.sql
```

**O que os scripts fazem:**
1. ✅ Remove índice único `ix_pedido_compras_num_pedido`
2. ✅ Cria índice normal (não-único) para `num_pedido`
3. ✅ Adiciona constraint composta `uq_pedido_compras_num_cod_produto`

---

## 🧪 TESTES

### Cenário de Teste:
```
Pedido Odoo: C2511843
Produtos:
  - 210003011 (FRASCO 200ML) - Qtd: 612
  - 210003012 (TAMPA)        - Qtd: 612
  - 210003013 (RÓTULO)       - Qtd: 1224
```

### Resultado Esperado:
```
✅ 3 registros em PedidoCompras:
  - (C2511843, 210003011)
  - (C2511843, 210003012)
  - (C2511843, 210003013)
```

### Antes da Correção:
```
❌ Produto 1: Inserido
❌ Produto 2: ERRO - duplicate key
❌ Produto 3: ERRO - duplicate key
```

### Depois da Correção:
```
✅ Produto 1: Inserido
✅ Produto 2: Inserido
✅ Produto 3: Inserido
```

---

## 📋 CHECKLIST DE DEPLOY

### Ambiente Local:
- [x] Modelo atualizado em `models.py`
- [x] Lógica de importação corrigida em `manufatura_service.py`
- [x] Script de migração criado
- [x] Script executado localmente
- [x] Constraint composta verificada

### Ambiente de Produção (Render):
- [ ] Fazer commit das alterações
- [ ] Executar script SQL no Shell do Render
- [ ] Verificar constraint no banco de produção
- [ ] Fazer deploy da aplicação
- [ ] Testar importação manual de pedidos
- [ ] Monitorar logs de importação automática

---

## 📚 REFERÊNCIAS

- **Modelo PedidoCompras:** `app/manufatura/models.py:210-249`
- **Serviço de Importação:** `app/odoo/services/manufatura_service.py:162-336`
- **Script Python:** `scripts/corrigir_constraint_pedido_compras.py`
- **Script SQL:** `scripts/corrigir_constraint_pedido_compras.sql`

---

## 🎯 IMPACTO DA CORREÇÃO

### Antes:
- ❌ Pedidos com múltiplos produtos falhavam
- ❌ Necessário importação manual produto por produto
- ❌ Rollback da transação em erro

### Depois:
- ✅ Pedidos com múltiplos produtos importam corretamente
- ✅ Sincronização automática funcional
- ✅ Atualização de pedidos existentes funcional
- ✅ Projeção de entradas de estoque precisa

---

**Responsável pela Correção:** Claude Code
**Aprovado por:** Rafael Nascimento
**Validado em:** [Data]
