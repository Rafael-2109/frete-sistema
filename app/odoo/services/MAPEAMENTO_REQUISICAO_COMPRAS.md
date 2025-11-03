# 📋 Mapeamento Completo - RequisicaoCompras

**Data**: 31/10/2025
**Modelo**: `RequisicaoCompras` ([app/manufatura/models.py](../../../app/manufatura/models.py:176-203))

---

## 🎯 REGRAS DE IMPORTAÇÃO DEFINIDAS

1. **Filtro de Produtos**: `detailed_type = 'product'` (produto armazenável)
2. **Código do Produto**: Buscar `default_code` via query em `product.product` (NÃO usar regex)
3. **Nome do Produto**: Extrair de `name` do `product.product`

---

## 📊 MAPEAMENTO COMPLETO DE CAMPOS

### Modelo Local: `RequisicaoCompras`

```python
__tablename__ = 'requisicao_compras'
```

---

## 🔢 CAMPO 1: `id`

| Propriedade | Valor |
|-------------|-------|
| **Tipo** | `db.Integer` |
| **Primary Key** | ✅ Sim |
| **Nullable** | ❌ Não (auto) |
| **Origem** | 🔧 **AUTO_INCREMENT** (banco de dados) |
| **Mapeamento Odoo** | ❌ Não mapeia |
| **Observações** | Gerado automaticamente pelo banco |

---

## 📝 CAMPO 2: `num_requisicao`

| Propriedade | Valor |
|-------------|-------|
| **Tipo** | `db.String(30)` |
| **Unique** | ✅ Sim |
| **Nullable** | ❌ Não |
| **Index** | ✅ Sim |
| **Origem Odoo** | ✅ `purchase.request.name` |
| **Exemplo Odoo** | `"REQ/FB/06614"` |
| **Processamento** | Direto (sem transformação) |
| **Obrigatório** | ✅ Sim |

**Código**:
```python
num_requisicao = requisicao_odoo['name']  # "REQ/FB/06614"
```

---

## 📅 CAMPO 3: `data_requisicao_criacao`

| Propriedade | Valor |
|-------------|-------|
| **Tipo** | `db.Date` |
| **Nullable** | ❌ Não |
| **Origem Odoo** | ✅ `purchase.request.create_date` |
| **Exemplo Odoo** | `"2025-10-30 13:39:06"` |
| **Processamento** | Converter para `date` (remover hora) |
| **Obrigatório** | ✅ Sim |

**Código**:
```python
from datetime import datetime

# Odoo retorna: "2025-10-30 13:39:06"
data_str = requisicao_odoo['create_date']
data_requisicao_criacao = datetime.strptime(data_str, '%Y-%m-%d %H:%M:%S').date()
# Resultado: date(2025, 10, 30)
```

---

## 👤 CAMPO 4: `usuario_requisicao_criacao`

| Propriedade | Valor |
|-------------|-------|
| **Tipo** | `db.String(100)` |
| **Nullable** | ✅ Sim |
| **Origem Odoo** | ✅ `purchase.request.requested_by[1]` |
| **Exemplo Odoo** | `[21, "Polyanna Alves de Souza"]` |
| **Processamento** | Extrair índice [1] (nome) |
| **Obrigatório** | ❌ Não |

**Código**:
```python
# Odoo retorna: [21, "Polyanna Alves de Souza"]
usuario_requisicao_criacao = requisicao_odoo['requested_by'][1] if requisicao_odoo.get('requested_by') else None
# Resultado: "Polyanna Alves de Souza"
```

---

## ⏱️ CAMPO 5: `lead_time_requisicao`

| Propriedade | Valor |
|-------------|-------|
| **Tipo** | `db.Integer` |
| **Nullable** | ✅ Sim |
| **Origem** | 🔧 **CALCULADO** |
| **Cálculo** | Dias entre `date_start` e `date_required` |
| **Obrigatório** | ❌ Não |

**Código**:
```python
from datetime import datetime

# Odoo:
# date_start: "2025-10-30"
# date_required: "2025-11-13" (da linha)

date_start = datetime.strptime(requisicao_odoo['date_start'], '%Y-%m-%d').date()
date_required = datetime.strptime(linha_odoo['date_required'], '%Y-%m-%d').date()

lead_time_requisicao = (date_required - date_start).days if date_required and date_start else None
# Resultado: 14 dias
```

---

## 📆 CAMPO 6: `lead_time_previsto`

| Propriedade | Valor |
|-------------|-------|
| **Tipo** | `db.Integer` |
| **Nullable** | ✅ Sim |
| **Origem** | ⚠️ **NÃO DISPONÍVEL** no Odoo |
| **Sugestão** | Copiar de `lead_time_requisicao` ou deixar NULL |
| **Obrigatório** | ❌ Não |

**Código**:
```python
# Opção 1: Copiar do calculado
lead_time_previsto = lead_time_requisicao

# Opção 2: Deixar NULL
lead_time_previsto = None
```

---

## 📅 CAMPO 7: `data_requisicao_solicitada`

| Propriedade | Valor |
|-------------|-------|
| **Tipo** | `db.Date` |
| **Nullable** | ✅ Sim |
| **Origem Odoo** | ✅ `purchase.request.date_start` |
| **Exemplo Odoo** | `"2025-10-30"` |
| **Processamento** | Converter string para `date` |
| **Obrigatório** | ❌ Não |

**Código**:
```python
from datetime import datetime

# Odoo retorna: "2025-10-30"
data_str = requisicao_odoo['date_start']
data_requisicao_solicitada = datetime.strptime(data_str, '%Y-%m-%d').date() if data_str else None
# Resultado: date(2025, 10, 30)
```

---

## 🏷️ CAMPO 8: `cod_produto`

| Propriedade | Valor |
|-------------|-------|
| **Tipo** | `db.String(50)` |
| **Nullable** | ❌ Não |
| **Index** | ✅ Sim |
| **Origem Odoo** | ✅ `product.product.default_code` |
| **Query Adicional** | ✅ **SIM** - Buscar em `product.product` |
| **Filtro Crítico** | ✅ `detailed_type = 'product'` |
| **Obrigatório** | ✅ Sim |

**Código**:
```python
# Linha da requisição tem:
# linha_odoo['product_id'] = [36788, "[210639522] ROTULO..."]

product_id_odoo = linha_odoo['product_id'][0]  # 36788

# QUERY ADICIONAL no product.product:
produto_odoo = conn.read(
    'product.product',
    [product_id_odoo],
    fields=['id', 'default_code', 'name', 'detailed_type']
)[0]

# VALIDAR FILTRO:
if produto_odoo.get('detailed_type') != 'product':
    logger.warning(f"Produto {product_id_odoo} não é armazenável (detailed_type={produto_odoo.get('detailed_type')}) - IGNORADO")
    continue  # Pula este produto

# EXTRAIR CÓDIGO:
cod_produto = produto_odoo['default_code']  # "210639522"

if not cod_produto:
    logger.error(f"Produto {product_id_odoo} sem default_code - IGNORADO")
    continue
```

---

## 📦 CAMPO 9: `nome_produto`

| Propriedade | Valor |
|-------------|-------|
| **Tipo** | `db.String(255)` |
| **Nullable** | ✅ Sim |
| **Origem Odoo** | ✅ `product.product.name` |
| **Query** | ✅ Mesma query do `cod_produto` |
| **Obrigatório** | ❌ Não (mas recomendado) |

**Código**:
```python
# Mesma query acima:
produto_odoo = conn.read(
    'product.product',
    [product_id_odoo],
    fields=['id', 'default_code', 'name', 'detailed_type']
)[0]

nome_produto = produto_odoo.get('name')  # "ROTULO SWEET PICKLES BD 1,01KG - RETANGULAR - BY GEMEOS"
```

---

## 📊 CAMPO 10: `qtd_produto_requisicao`

| Propriedade | Valor |
|-------------|-------|
| **Tipo** | `db.Numeric(15, 3)` |
| **Nullable** | ❌ Não |
| **Origem Odoo** | ✅ `purchase.request.line.product_qty` |
| **Exemplo Odoo** | `6000.0` |
| **Processamento** | Converter para `Decimal` |
| **Obrigatório** | ✅ Sim |

**Código**:
```python
from decimal import Decimal

# Odoo retorna: 6000.0
qtd_produto_requisicao = Decimal(str(linha_odoo['product_qty']))
# Resultado: Decimal('6000.0')
```

---

## 📦 CAMPO 11: `qtd_produto_sem_requisicao`

| Propriedade | Valor |
|-------------|-------|
| **Tipo** | `db.Numeric(15, 3)` |
| **Default** | `0` |
| **Nullable** | ✅ Sim |
| **Origem** | ⚠️ **NÃO DISPONÍVEL** no Odoo |
| **Uso** | Controle interno (manual) |
| **Obrigatório** | ❌ Não |

**Código**:
```python
# Sempre zerar na importação:
qtd_produto_sem_requisicao = Decimal('0')
```

---

## ✅ CAMPO 12: `necessidade`

| Propriedade | Valor |
|-------------|-------|
| **Tipo** | `db.Boolean` |
| **Default** | `False` |
| **Origem Odoo** | ✅ `purchase.request.state` |
| **Lógica** | `True` se `state='approved'`, `False` caso contrário |
| **Obrigatório** | ❌ Não |

**Código**:
```python
# Odoo retorna: "approved", "draft", "done", etc.
necessidade = requisicao_odoo['state'] == 'approved'
# Resultado: True se aprovada
```

---

## 📅 CAMPO 13: `data_necessidade`

| Propriedade | Valor |
|-------------|-------|
| **Tipo** | `db.Date` |
| **Nullable** | ✅ Sim |
| **Origem Odoo** | ✅ `purchase.request.line.date_required` |
| **Exemplo Odoo** | `"2025-11-13"` |
| **Processamento** | Converter string para `date` |
| **Obrigatório** | ❌ Não |

**Código**:
```python
from datetime import datetime

# Odoo retorna: "2025-11-13"
data_str = linha_odoo['date_required']
data_necessidade = datetime.strptime(data_str, '%Y-%m-%d').date() if data_str else None
# Resultado: date(2025, 11, 13)
```

---

## 📋 CAMPO 14: `status`

| Propriedade | Valor |
|-------------|-------|
| **Tipo** | `db.String(20)` |
| **Default** | `'Pendente'` |
| **Index** | ✅ Sim |
| **Origem Odoo** | ✅ `purchase.request.state` |
| **Mapeamento** | Converter `state` Odoo → `status` Sistema |
| **Obrigatório** | ❌ Não (usa default se não mapear) |

**Mapeamento de Status**:
```python
MAPA_STATUS = {
    'draft': 'Rascunho',
    'to_approve': 'Aguardando Aprovação',
    'approved': 'Aprovada',
    'rejected': 'Rejeitada',
    'done': 'Concluída',
}

# Odoo retorna: "approved"
state_odoo = requisicao_odoo['state']
status = MAPA_STATUS.get(state_odoo, 'Pendente')
# Resultado: "Aprovada"
```

---

## 🔗 CAMPO 15: `importado_odoo`

| Propriedade | Valor |
|-------------|-------|
| **Tipo** | `db.Boolean` |
| **Default** | `False` |
| **Origem** | 🔧 **FIXO** |
| **Valor** | `True` (sempre para importações do Odoo) |
| **Obrigatório** | ✅ Sim (controle interno) |

**Código**:
```python
importado_odoo = True  # Sempre True quando importado do Odoo
```

---

## 🆔 CAMPO 16: `odoo_id`

| Propriedade | Valor |
|-------------|-------|
| **Tipo** | `db.String(50)` |
| **Nullable** | ✅ Sim |
| **Origem Odoo** | ✅ `purchase.request.line.id` |
| **Uso** | Identificar linha no Odoo (evitar duplicação) |
| **Obrigatório** | ❌ Não (mas recomendado) |

**Código**:
```python
# Odoo retorna: 20437 (id da linha)
odoo_id = str(linha_odoo['id'])  # "20437"
```

---

## 🔗 CAMPO 17: `requisicao_odoo_id`

| Propriedade | Valor |
|-------------|-------|
| **Tipo** | `db.String(50)` |
| **Index** | ✅ Sim |
| **Nullable** | ✅ Sim |
| **Origem Odoo** | ✅ `purchase.request.id` |
| **Uso** | Identificar requisição pai no Odoo |
| **Obrigatório** | ❌ Não (mas recomendado) |

**Código**:
```python
# Odoo retorna: 8004 (id da requisição pai)
requisicao_odoo_id = str(requisicao_odoo['id'])  # "8004"
```

---

## 📋 CAMPO 18: `status_requisicao`

| Propriedade | Valor |
|-------------|-------|
| **Tipo** | `db.String(20)` |
| **Default** | `'rascunho'` |
| **Origem** | 🔧 **FIXO** |
| **Valor** | `'enviada_odoo'` (já vem do Odoo) |
| **Uso** | Controle de sincronização |
| **Obrigatório** | ❌ Não |

**Código**:
```python
# Como vem do Odoo, já foi enviada:
status_requisicao = 'confirmada'  # ou 'enviada_odoo'
```

---

## 📅 CAMPO 19: `data_envio_odoo`

| Propriedade | Valor |
|-------------|-------|
| **Tipo** | `db.DateTime` |
| **Nullable** | ✅ Sim |
| **Origem** | ⚠️ **NÃO DISPONÍVEL** (campo interno do sistema) |
| **Sugestão** | Deixar `NULL` (requisição já existe no Odoo) |
| **Obrigatório** | ❌ Não |

**Código**:
```python
data_envio_odoo = None  # NULL - não aplicável para importação
```

---

## 📅 CAMPO 20: `data_confirmacao_odoo`

| Propriedade | Valor |
|-------------|-------|
| **Tipo** | `db.DateTime` |
| **Nullable** | ✅ Sim |
| **Origem** | 🔧 **CALCULADO** |
| **Valor** | Data/hora atual da importação |
| **Uso** | Quando foi confirmado/importado |
| **Obrigatório** | ❌ Não |

**Código**:
```python
from datetime import datetime

data_confirmacao_odoo = datetime.utcnow()  # Agora
```

---

## 📝 CAMPO 21: `observacoes_odoo`

| Propriedade | Valor |
|-------------|-------|
| **Tipo** | `db.Text` |
| **Nullable** | ✅ Sim |
| **Origem Odoo** | ✅ `purchase.request.description` |
| **Exemplo Odoo** | `false` ou texto |
| **Processamento** | Tratar `false` como `None` |
| **Obrigatório** | ❌ Não |

**Código**:
```python
# Odoo retorna: false ou "texto da descrição"
desc = requisicao_odoo.get('description')
observacoes_odoo = desc if desc and desc != False else None
# Resultado: None se false, ou texto se preenchido
```

---

## 📅 CAMPO 22: `criado_em`

| Propriedade | Valor |
|-------------|-------|
| **Tipo** | `db.DateTime` |
| **Default** | `datetime.utcnow` |
| **Nullable** | ✅ Sim |
| **Origem** | 🔧 **AUTO** (banco de dados) |
| **Obrigatório** | ❌ Não (usa default) |

**Código**:
```python
# Deixar vazio - banco preenche automaticamente
criado_em = None  # ou não passar no construtor
```

---

## 📋 RESUMO DE CAMPOS POR ORIGEM

### ✅ Campos do Odoo (Diretos - 11 campos):

1. `num_requisicao` ← `purchase.request.name`
2. `data_requisicao_criacao` ← `purchase.request.create_date`
3. `usuario_requisicao_criacao` ← `purchase.request.requested_by[1]`
4. `data_requisicao_solicitada` ← `purchase.request.date_start`
5. `qtd_produto_requisicao` ← `purchase.request.line.product_qty`
6. `necessidade` ← `purchase.request.state == 'approved'`
7. `data_necessidade` ← `purchase.request.line.date_required`
8. `status` ← `purchase.request.state` (mapeado)
9. `odoo_id` ← `purchase.request.line.id`
10. `requisicao_odoo_id` ← `purchase.request.id`
11. `observacoes_odoo` ← `purchase.request.description`

### 🔍 Campos com Query Adicional (2 campos):

12. `cod_produto` ← `product.product.default_code` (+ validar `detailed_type='product'`)
13. `nome_produto` ← `product.product.name`

### 🔧 Campos Calculados (2 campos):

14. `lead_time_requisicao` ← Dias entre `date_start` e `date_required`
15. `data_confirmacao_odoo` ← `datetime.utcnow()`

### 🔒 Campos Fixos/Controle (4 campos):

16. `importado_odoo` ← `True`
17. `status_requisicao` ← `'confirmada'`
18. `qtd_produto_sem_requisicao` ← `0`
19. `lead_time_previsto` ← `None` ou copiar de `lead_time_requisicao`

### ⚙️ Campos Auto/Default (3 campos):

20. `id` ← AUTO_INCREMENT
21. `data_envio_odoo` ← `None`
22. `criado_em` ← `datetime.utcnow()` (auto)

---

## 🔧 PSEUDOCÓDIGO COMPLETO DE IMPORTAÇÃO

```python
def importar_requisicao_compras(requisicao_odoo, linha_odoo, conn):
    """
    Importa uma linha de requisição do Odoo

    Args:
        requisicao_odoo: dict com dados de purchase.request
        linha_odoo: dict com dados de purchase.request.line
        conn: Conexão Odoo
    """
    from decimal import Decimal
    from datetime import datetime

    # ========================================
    # PASSO 1: BUSCAR PRODUTO (Query Adicional)
    # ========================================
    product_id_odoo = linha_odoo['product_id'][0]

    produto_odoo = conn.read(
        'product.product',
        [product_id_odoo],
        fields=['id', 'default_code', 'name', 'detailed_type']
    )[0]

    # VALIDAR FILTRO: detailed_type = 'product'
    if produto_odoo.get('detailed_type') != 'product':
        logger.warning(f"Produto {product_id_odoo} não é armazenável - IGNORADO")
        return None

    cod_produto = produto_odoo.get('default_code')
    if not cod_produto:
        logger.error(f"Produto {product_id_odoo} sem default_code - IGNORADO")
        return None

    nome_produto = produto_odoo.get('name')

    # ========================================
    # PASSO 2: CALCULAR CAMPOS
    # ========================================

    # Datas
    data_requisicao_criacao = datetime.strptime(
        requisicao_odoo['create_date'], '%Y-%m-%d %H:%M:%S'
    ).date()

    data_requisicao_solicitada = datetime.strptime(
        requisicao_odoo['date_start'], '%Y-%m-%d'
    ).date() if requisicao_odoo.get('date_start') else None

    data_necessidade = datetime.strptime(
        linha_odoo['date_required'], '%Y-%m-%d'
    ).date() if linha_odoo.get('date_required') else None

    # Lead time
    if data_requisicao_solicitada and data_necessidade:
        lead_time_requisicao = (data_necessidade - data_requisicao_solicitada).days
    else:
        lead_time_requisicao = None

    # Status
    MAPA_STATUS = {
        'draft': 'Rascunho',
        'to_approve': 'Aguardando Aprovação',
        'approved': 'Aprovada',
        'rejected': 'Rejeitada',
        'done': 'Concluída',
    }
    status = MAPA_STATUS.get(requisicao_odoo['state'], 'Pendente')

    # ========================================
    # PASSO 3: CRIAR OBJETO
    # ========================================
    requisicao = RequisicaoCompras(
        # Campos Odoo diretos:
        num_requisicao=requisicao_odoo['name'],
        data_requisicao_criacao=data_requisicao_criacao,
        usuario_requisicao_criacao=requisicao_odoo['requested_by'][1] if requisicao_odoo.get('requested_by') else None,
        data_requisicao_solicitada=data_requisicao_solicitada,
        qtd_produto_requisicao=Decimal(str(linha_odoo['product_qty'])),
        necessidade=(requisicao_odoo['state'] == 'approved'),
        data_necessidade=data_necessidade,
        status=status,
        odoo_id=str(linha_odoo['id']),
        requisicao_odoo_id=str(requisicao_odoo['id']),
        observacoes_odoo=requisicao_odoo.get('description') if requisicao_odoo.get('description') != False else None,

        # Campos com query adicional:
        cod_produto=cod_produto,
        nome_produto=nome_produto,

        # Campos calculados:
        lead_time_requisicao=lead_time_requisicao,
        data_confirmacao_odoo=datetime.utcnow(),

        # Campos fixos:
        importado_odoo=True,
        status_requisicao='confirmada',
        qtd_produto_sem_requisicao=Decimal('0'),
        lead_time_previsto=lead_time_requisicao,  # ou None

        # Campos auto/NULL:
        data_envio_odoo=None
        # id, criado_em → automáticos
    )

    return requisicao
```

---

## ✅ CHECKLIST DE VALIDAÇÃO

- [ ] **Filtro de produto**: Verificar `detailed_type='product'`
- [ ] **default_code existe**: Produto tem código cadastrado
- [ ] **Buscar product.product**: Query adicional implementada
- [ ] **Converter datas**: String → date object
- [ ] **Decimal para quantidades**: Usar `Decimal(str(valor))`
- [ ] **Tratar false do Odoo**: Converter para `None`
- [ ] **Mapear status**: Aplicar dicionário de conversão
- [ ] **Calcular lead_time**: Diferença entre datas
- [ ] **Evitar duplicação**: Verificar por `odoo_id` antes de inserir

---

**Status**: MAPEAMENTO COMPLETO - PRONTO PARA APROVAÇÃO
**Total de Campos**: 22 campos
**Campos do Odoo**: 13 (11 diretos + 2 com query adicional)
**Campos Calculados/Fixos**: 9
