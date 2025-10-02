# 🚨 ANÁLISE DE IMPACTO: Remoção de Produtos Excluídos

## 📋 OBJETIVO DA MUDANÇA

Quando um produto é **excluído** de um pedido no Odoo:
- Atualmente: Produto **permanece** na CarteiraPrincipal com dados antigos
- Desejado: Produto deve ser **removido** após confirmação no Odoo

---

## 🔍 CÓDIGO ATUAL (Linhas 1692-1724)

### **Comportamento Atual:**

```python
# Linha 1694-1700: Busca TODOS os pedidos Odoo do banco
registros_odoo_existentes = {}
for item in db.session.query(CarteiraPrincipal).filter(
    or_(
        CarteiraPrincipal.num_pedido.like('VSC%'),
        CarteiraPrincipal.num_pedido.like('VCD%'),
        CarteiraPrincipal.num_pedido.like('VFB%')
    )
).all():
    registros_odoo_existentes[chave] = item

# Linha 1715-1721: Detecta mas NÃO remove
for chave, registro in registros_odoo_existentes.items():
    if chave not in chaves_novos_dados:
        pedidos_odoo_obsoletos += 1
        # COMENTADO: db.session.delete(registro)
```

**Problemas:**
1. ❌ Busca TODOS os pedidos, não apenas os sincronizados
2. ❌ Detecta falsos positivos (pedidos que não vieram na sincronização)
3. ❌ Não remove produtos excluídos

---

## 🎯 MUDANÇA PROPOSTA

### **Nova Lógica:**

```python
# ETAPA 1: Buscar APENAS pedidos que vieram na sincronização atual
pedidos_na_sincronizacao = set(item['num_pedido'] for item in dados_novos)

registros_odoo_existentes = {}
for item in CarteiraPrincipal.query.filter(
    CarteiraPrincipal.num_pedido.in_(pedidos_na_sincronizacao)  # ✅ APENAS sincronizados
).all():
    registros_odoo_existentes[chave] = item

# ETAPA 2: Identificar produtos que não vieram
produtos_suspeitos = []
for chave, registro in registros_odoo_existentes.items():
    if chave not in chaves_novos_dados:
        produtos_suspeitos.append((chave, registro))

# ETAPA 3: CONFIRMAR NO ODOO antes de deletar
for chave, registro in produtos_suspeitos:
    existe_no_odoo = verificar_produto_no_odoo(num_pedido, cod_produto)

    if not existe_no_odoo:
        db.session.delete(registro)  # ✅ Deletar apenas se confirmado
```

---

## 🚨 ANÁLISE DE IMPACTOS

### **IMPACTO 1: Separacao**

**Cenário:** Produto foi excluído do Odoo mas já foi separado

```sql
SELECT * FROM separacao
WHERE num_pedido = 'VCD2563863'
  AND cod_produto = '4210176';
```

**Risco:** ⚠️ **ALTO**
- Se produto tem Separacao com `sincronizado_nf=False` → Não pode deletar!
- Separação ficaria órfã (sem referência na CarteiraPrincipal)

**Proteção Necessária:**
```python
tem_separacao = Separacao.query.filter_by(
    num_pedido=num_pedido,
    cod_produto=cod_produto,
    sincronizado_nf=False
).first()

if tem_separacao:
    # NÃO DELETAR! Manter para histórico
    return False
```

---

### **IMPACTO 2: FaturamentoProduto**

**Cenário:** Produto foi excluído do Odoo mas já foi faturado

```sql
SELECT * FROM faturamento_produto
WHERE origem = 'VCD2563863'
  AND cod_produto = '4210176';
```

**Risco:** ⚠️ **ALTO**
- Se produto tem NF emitida → Não pode deletar!
- Faturamento ficaria inconsistente

**Proteção Necessária:**
```python
tem_faturamento = FaturamentoProduto.query.filter_by(
    origem=num_pedido,
    cod_produto=cod_produto
).filter(
    FaturamentoProduto.status_nf != 'Cancelado'
).first()

if tem_faturamento:
    # NÃO DELETAR! Produto foi faturado
    return False
```

---

### **IMPACTO 3: Pedido (VIEW)**

**Cenário:** Pedido é uma VIEW que agrega Separacao

```python
# app/pedidos/models.py
class Pedido:
    __table_args__ = {'info': {'is_view': True}}
```

**Risco:** ⚠️ **BAIXO**
- Pedido é VIEW, não tem FK para CarteiraPrincipal
- Deletar produto não afeta VIEW

**Proteção:** ✅ Não necessária

---

### **IMPACTO 4: Cotacao**

**Cenário:** Produto está em cotação de frete

```sql
SELECT * FROM cotacoes c
JOIN pedidos p ON c.id = p.cotacao_id
WHERE p.num_pedido = 'VCD2563863';
```

**Risco:** ⚠️ **MÉDIO**
- Se pedido tem cotação, remover produto pode afetar cálculo de frete
- Mas cotação está vinculada ao pedido (separacao_lote_id), não ao produto individual

**Proteção:** ⚠️ Avaliar se necessário

---

### **IMPACTO 5: Embarque**

**Cenário:** Produto está em embarque

```sql
SELECT * FROM embarque_itens
WHERE pedido = 'VCD2563863';
```

**Risco:** ⚠️ **ALTO**
- Se produto está embarcado → Não pode deletar!
- EmbarqueItem tem campo `pedido` mas pode ter `separacao_lote_id`

**Proteção Necessária:**
```python
from app.embarques.models import EmbarqueItem

tem_embarque = EmbarqueItem.query.filter(
    EmbarqueItem.pedido == num_pedido
).filter(
    EmbarqueItem.status == 'ativo'
).first()

if tem_embarque:
    # Verificar se o produto específico está no embarque
    # (precisa verificar via separacao_lote_id ou outro campo)
    return False
```

---

### **IMPACTO 6: PreSeparacaoItem (DEPRECATED)**

**Cenário:** Produto está em pré-separação

```python
# DEPRECATED: Substituído por Separacao com status='PREVISAO'
```

**Risco:** ✅ **NENHUM**
- PreSeparacaoItem não é mais usado (adapter ativo)

**Proteção:** ✅ Não necessária

---

### **IMPACTO 7: SaldoStandby**

**Cenário:** Produto tem saldo reservado

```sql
SELECT * FROM saldo_standby
WHERE num_pedido = 'VCD2563863'
  AND cod_produto = '4210176';
```

**Risco:** ⚠️ **MÉDIO**
- Se produto tem SaldoStandby → Deve remover também

**Proteção Necessária:**
```python
# Remover SaldoStandby junto com o produto
SaldoStandby.query.filter_by(
    num_pedido=num_pedido,
    cod_produto=cod_produto
).delete()
```

---

## 🛡️ CHECKLIST DE SEGURANÇA

Antes de deletar um produto, verificar:

- [ ] ✅ Produto NÃO veio na sincronização
- [ ] ✅ Confirmado no Odoo que produto foi excluído
- [ ] ✅ Produto NÃO tem Separacao ativa (sincronizado_nf=False)
- [ ] ✅ Produto NÃO tem Faturamento (status != Cancelado)
- [ ] ✅ Produto NÃO está em Embarque ativo
- [ ] ✅ Remover SaldoStandby associado (se houver)

---

## 🎯 IMPLEMENTAÇÃO SEGURA

### **Opção 1: Deleção Condicional (RECOMENDADA)**

```python
def pode_deletar_produto(num_pedido, cod_produto):
    """
    Verifica se produto pode ser deletado com segurança
    """
    from app.separacao.models import Separacao
    from app.faturamento.models import FaturamentoProduto
    from app.embarques.models import EmbarqueItem

    # 1. Verificar Separacao
    tem_separacao = Separacao.query.filter_by(
        num_pedido=num_pedido,
        cod_produto=cod_produto,
        sincronizado_nf=False
    ).first()

    if tem_separacao:
        logger.warning(f"   ⚠️ Produto tem separação ativa: {num_pedido}/{cod_produto}")
        return False

    # 2. Verificar Faturamento
    tem_faturamento = FaturamentoProduto.query.filter_by(
        origem=num_pedido,
        cod_produto=cod_produto
    ).filter(
        FaturamentoProduto.status_nf != 'Cancelado'
    ).first()

    if tem_faturamento:
        logger.warning(f"   ⚠️ Produto já foi faturado: {num_pedido}/{cod_produto}")
        return False

    # 3. Verificar Embarque
    # TODO: Implementar verificação de embarque

    return True

def remover_produto_com_seguranca(registro):
    """
    Remove produto e seus relacionamentos
    """
    num_pedido = registro.num_pedido
    cod_produto = registro.cod_produto

    # Remover SaldoStandby
    from app.carteira.models import SaldoStandby
    SaldoStandby.query.filter_by(
        num_pedido=num_pedido,
        cod_produto=cod_produto
    ).delete()

    # Remover produto
    db.session.delete(registro)
    logger.info(f"   ✅ Produto removido: {num_pedido}/{cod_produto}")
```

### **Opção 2: Marcar como Cancelado (MAIS SEGURA)**

```python
def marcar_produto_cancelado(registro):
    """
    Marca produto como cancelado ao invés de deletar
    """
    registro.qtd_saldo_produto_pedido = 0
    registro.qtd_cancelada_produto_pedido = registro.qtd_produto_pedido
    registro.status_pedido = 'Cancelado'
    logger.info(f"   ⚠️ Produto marcado como cancelado: {registro.num_pedido}/{registro.cod_produto}")
```

---

## 📊 RECOMENDAÇÃO FINAL

### **Abordagem HÍBRIDA (mais segura):**

1. **Se produto NÃO tem movimento** (sem separação, faturamento, embarque):
   - ✅ **DELETAR** do banco

2. **Se produto TEM movimento:**
   - ⚠️ **MARCAR como Cancelado** (qtd_saldo = 0)
   - ✅ Manter para histórico

3. **Sempre:**
   - ✅ Confirmar no Odoo antes de qualquer ação
   - ✅ Log detalhado de todas as ações
   - ✅ Remover SaldoStandby associado

---

## ⚠️ PRÓXIMOS PASSOS

1. **VALIDAR** com você cada proteção listada
2. **TESTAR** em ambiente de desenvolvimento primeiro
3. **CRIAR** script de rollback (backup antes de deletar)
4. **IMPLEMENTAR** com todas as proteções
5. **MONITORAR** logs na primeira sincronização

**Aguardo sua confirmação para prosseguir! 🔒**
