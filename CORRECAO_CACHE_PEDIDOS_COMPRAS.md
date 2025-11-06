# Correção: Cache de Pedidos com Chave Incorreta

**Data:** 05/11/2025
**Problema:** Erro de chave duplicada ao importar pedidos com múltiplos produtos
**Status:** ✅ CORRIGIDO

---

## 🔴 PROBLEMA IDENTIFICADO

### Erro Original:
```
UniqueViolation: duplicate key value violates unique constraint "uq_pedido_compras_num_cod_produto"
DETAIL: Key (num_pedido, cod_produto)=(C2510707, 104000015) already exists.
```

### Causa Raiz:

O cache de pedidos existentes estava usando **chave simples** (`num_pedido`) em vez de **chave composta** (`num_pedido + cod_produto`), causando sobrescrita no cache.

**Código problemático** ([pedido_compras_service.py:300](app/odoo/services/pedido_compras_service.py#L300)):

```python
# ❌ ANTES (INCORRETO):
cache = {
    'por_odoo_id': {},
    'por_num_pedido': {}  # ❌ Chave simples sobrescreve quando há múltiplos produtos
}

for pedido in todos_pedidos:
    cache['por_num_pedido'][pedido.num_pedido] = pedido  # ❌ SOBRESCREVE
```

**Fluxo do erro:**

Se o pedido C2510707 tem 3 produtos no banco:
1. Produto A (cod='104000015'): `cache['C2510707'] = pedido_A`
2. Produto B (cod='104000016'): `cache['C2510707'] = pedido_B` ❌ **SOBRESCREVE A**
3. Produto C (cod='104000017'): `cache['C2510707'] = pedido_C` ❌ **SOBRESCREVE B**

**Resultado:** Cache só tem produto C. Ao sincronizar, tenta inserir A e B novamente → **erro de chave duplicada**.

---

## ✅ SOLUÇÃO IMPLEMENTADA

### 1. Alteração do Cache para Chave Composta

**Arquivo:** `app/odoo/services/pedido_compras_service.py`

```python
# ✅ DEPOIS (CORRETO):
cache = {
    'por_odoo_id': {},           # odoo_id -> PedidoCompras
    'por_chave_composta': {}     # "num_pedido|cod_produto" -> PedidoCompras
}

for pedido in todos_pedidos:
    if pedido.odoo_id:
        cache['por_odoo_id'][pedido.odoo_id] = pedido
    # ✅ Chave composta reflete a constraint real do banco
    chave = f"{pedido.num_pedido}|{pedido.cod_produto}"
    cache['por_chave_composta'][chave] = pedido
```

### 2. Atualização da Busca no Cache

**Antes (linha 408-412):**
```python
# ❌ INCORRETO: Usava ID da linha (purchase.order.line.id)
odoo_id = str(linha_odoo['id'])
pedido_existente = pedidos_existentes_cache['por_odoo_id'].get(odoo_id)
```

**Depois:**
```python
# ✅ CORRETO: Usa chave composta que corresponde à constraint do banco
odoo_id_pedido = str(pedido_odoo['id'])
num_pedido = pedido_odoo['name']
chave_composta = f"{num_pedido}|{cod_produto}"
pedido_existente = pedidos_existentes_cache['por_chave_composta'].get(chave_composta)
```

### 3. Atualização do Cache Após Inserção

**Antes (linha 428-430):**
```python
# ❌ INCORRETO: Chave simples
pedidos_existentes_cache['por_num_pedido'][novo_pedido.num_pedido] = novo_pedido
```

**Depois:**
```python
# ✅ CORRETO: Chave composta
chave_nova = f"{novo_pedido.num_pedido}|{novo_pedido.cod_produto}"
pedidos_existentes_cache['por_chave_composta'][chave_nova] = novo_pedido
```

### 4. Correção de Linting (E711)

**Antes (linha 573):**
```python
PedidoCompras.odoo_id != None  # ❌ E711: comparison to None
```

**Depois:**
```python
PedidoCompras.odoo_id.isnot(None)  # ✅ Correto
```

---

## 🔍 ANÁLISE TÉCNICA

### Por que a Chave Composta é Necessária?

O modelo `PedidoCompras` tem constraint:
```python
__table_args__ = (
    db.UniqueConstraint('num_pedido', 'cod_produto',
                       name='uq_pedido_compras_num_cod_produto'),
)
```

**Isso permite:**
- Pedido C2510707 com produto A ✅
- Pedido C2510707 com produto B ✅
- Pedido C2510707 com produto C ✅

**Mas proíbe:**
- Pedido C2510707 com produto A (duplicado) ❌

**O cache DEVE refletir essa constraint** para funcionar corretamente!

### Formato da Chave Composta

```python
chave = f"{num_pedido}|{cod_produto}"
```

**Exemplos:**
- `"C2510707|104000015"` → Pedido C2510707, produto 104000015
- `"C2510707|104000016"` → Pedido C2510707, produto 104000016
- `"C2510708|104000015"` → Pedido C2510708, produto 104000015

Usamos `|` como separador para evitar colisões.

---

## 🧪 TESTES

### Cenário de Teste:

**Pedido do Odoo:** C2510707
**Produtos:**
- 104000015 (SAL SEM IODO) - Qtd: 25
- 104000016 (AÇÚCAR) - Qtd: 50
- 104000017 (FARINHA) - Qtd: 100

### Antes da Correção:
```
1ª Sincronização:
  ✅ Insere produto 104000015
  ✅ Insere produto 104000016
  ✅ Insere produto 104000017

2ª Sincronização:
  ❌ Cache só tem produto 104000017
  ❌ Tenta inserir 104000015 novamente → ERRO de chave duplicada
  ❌ Rollback da transação
```

### Depois da Correção:
```
1ª Sincronização:
  ✅ Insere produto 104000015 → cache["C2510707|104000015"]
  ✅ Insere produto 104000016 → cache["C2510707|104000016"]
  ✅ Insere produto 104000017 → cache["C2510707|104000017"]

2ª Sincronização:
  ✅ Encontra 104000015 no cache → Atualiza
  ✅ Encontra 104000016 no cache → Atualiza
  ✅ Encontra 104000017 no cache → Atualiza
  ✅ Nenhum erro!
```

---

## 📋 CORREÇÕES ADICIONAIS

### 1. Circuit Breaker - Timeout

**Arquivo:** `app/odoo/utils/connection.py`

**Problema:** Retry interno competindo com Circuit Breaker
**Solução:** Removido retry interno, deixar Circuit Breaker gerenciar

**Antes:**
```python
for attempt in range(self.retry_attempts):  # ❌ 3 tentativas x 30s = 90s
    try:
        self._uid = common.authenticate(...)
    except Exception as e:
        if attempt < self.retry_attempts - 1:
            time.sleep(1)  # ❌ Retry interno
```

**Depois:**
```python
# ✅ Sem retry interno - falha rápido para Circuit Breaker
try:
    self._uid = common.authenticate(...)
except Exception as e:
    raise  # ✅ Lança imediatamente
```

**Impacto:**
- Antes: 90s para detectar Odoo offline (3 × 30s)
- Depois: 30s para detectar Odoo offline (1 × 30s)

### 2. Campo atualizado_em Ausente

**Ver:** [CORRECAO_CAMPO_ATUALIZADO_EM.md](CORRECAO_CAMPO_ATUALIZADO_EM.md)

---

## 📊 IMPACTO GERAL

### Antes das Correções:
- ❌ Erro de chave duplicada em pedidos com múltiplos produtos
- ❌ Sistema travava 90s quando Odoo offline
- ❌ Campo atualizado_em causava erro SQL
- ❌ Impossível sincronizar pedidos

### Depois das Correções:
- ✅ Pedidos com múltiplos produtos funcionam
- ✅ Detecção de Odoo offline em 30s
- ✅ Campo atualizado_em presente no banco
- ✅ Sincronização funcional e rápida

---

## 🚀 DEPLOY

### Ambiente Local:
- [x] Cache corrigido para chave composta
- [x] Retry interno removido
- [x] Campo atualizado_em adicionado
- [x] Testes realizados

### Ambiente de Produção (Render):
- [ ] Executar SQL: `adicionar_atualizado_em_pedido_compras.sql`
- [ ] Fazer commit e push das alterações
- [ ] Deploy da aplicação
- [ ] Testar sincronização manual
- [ ] Monitorar logs

---

## 📚 ARQUIVOS MODIFICADOS

1. **app/odoo/services/pedido_compras_service.py**
   - Linha 291-302: Cache com chave composta
   - Linha 407-416: Busca com chave composta
   - Linha 433-437: Atualização do cache
   - Linha 573: Correção E711

2. **app/odoo/utils/connection.py**
   - Linha 98-119: Removido retry interno (authenticate)
   - Linha 153-170: Removido retry interno (execute_kw)

3. **app/manufatura/models.py**
   - Linha 242: Campo atualizado_em adicionado

---

**Responsável:** Claude Code
**Aprovado por:** Rafael Nascimento
**Data:** 05/11/2025
