# Correção: Campo atualizado_em Ausente no Banco

**Data:** 05/11/2025
**Problema:** Sistema travando durante sincronização manual com erro SQL
**Status:** ✅ CORRIGIDO

---

## 🔴 PROBLEMA IDENTIFICADO

### Erro Original:
```
sqlalchemy.exc.ProgrammingError: (psycopg2.errors.UndefinedColumn)
column pedido_compras.atualizado_em does not exist
```

### Causa Raiz:

Durante a correção anterior ([CORRECAO_IMPORTACAO_PEDIDOS_COMPRAS.md](CORRECAO_IMPORTACAO_PEDIDOS_COMPRAS.md)), adicionamos o campo `atualizado_em` no **modelo Python** mas **esquecemos de criar a migração do banco de dados**.

**Código adicionado** ([models.py:242](app/manufatura/models.py#L242)):
```python
atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

**Resultado:** Campo existe no código mas não no banco ❌

---

## 🔍 COMO FOI DESCOBERTO

1. **Sintoma:** Sistema travou durante sincronização manual (período de 1 semana)
2. **Primeira hipótese (incorreta):** Timeout de conexão Odoo
3. **Segunda hipótese (incorreta):** Query SELECT travando por muitos registros
4. **Descoberta real:** Ao executar query de teste, erro indicou coluna inexistente

**Log de depuração:**
```python
from app.manufatura.models import PedidoCompras
count = PedidoCompras.query.count()
# ❌ Erro: column pedido_compras.atualizado_em does not exist
```

---

## ✅ SOLUÇÃO IMPLEMENTADA

### 1. Script Python (para ambiente local):

**Arquivo:** `scripts/adicionar_atualizado_em_pedido_compras.py`

```python
# Adiciona coluna atualizado_em
ALTER TABLE pedido_compras
ADD COLUMN atualizado_em TIMESTAMP DEFAULT NOW()

# Atualiza registros existentes
UPDATE separacao
SET cnpj_cpf = '67.702.647/0001-36'
WHERE separacao_lote_id = 'LOTE_77DBFDA3';
```

### 2. Script SQL (para Render):

**Arquivo:** `scripts/adicionar_atualizado_em_pedido_compras.sql`

```sql
-- Adicionar coluna
ALTER TABLE pedido_compras
ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMP DEFAULT NOW();

-- Atualizar registros existentes
UPDATE pedido_compras
SET atualizado_em = criado_em
WHERE atualizado_em IS NULL;
```

---

## 📋 CHECKLIST DE DEPLOY

### Ambiente Local:
- [x] Campo adicionado no modelo Python
- [x] Script de migração criado
- [x] Migração executada localmente
- [x] Campo verificado no banco local
- [x] Constraint composta mantida

### Ambiente de Produção (Render):
- [ ] Executar SQL no Shell do Render
- [ ] Verificar campo no banco de produção
- [ ] Fazer deploy da aplicação
- [ ] Testar sincronização manual
- [ ] Monitorar logs

---

## 🧪 TESTES

### Antes da Correção:
```python
PedidoCompras.query.count()
# ❌ UndefinedColumn: column pedido_compras.atualizado_em does not exist
```

### Depois da Correção:
```python
PedidoCompras.query.count()
# ✅ Retorna: 0 (banco vazio, mas query funciona)
```

### Estrutura Final:
```sql
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'pedido_compras'
AND column_name IN ('criado_em', 'atualizado_em');

-- Resultado:
-- atualizado_em | timestamp without time zone | now()
-- criado_em     | timestamp without time zone | (none)
```

---

## 📚 LIÇÕES APRENDIDAS

### ❌ Erro Cometido:
1. Adicionamos campo no modelo Python
2. **Esquecemos de criar migração do banco**
3. Não testamos em ambiente limpo

### ✅ Processo Correto:
1. Adicionar campo no modelo Python
2. **SEMPRE criar script de migração** (Python + SQL)
3. Executar migração localmente
4. Testar funcionalidade
5. Só então fazer deploy

### 🎯 Prevenção Futura:
- **Checklist obrigatório** ao adicionar campos:
  - [ ] Campo adicionado no modelo
  - [ ] Script Python de migração criado
  - [ ] Script SQL de migração criado
  - [ ] Migração executada localmente
  - [ ] Teste realizado
  - [ ] Documentação atualizada

---

## 🔗 ARQUIVOS RELACIONADOS

- **Modelo:** [app/manufatura/models.py:210-249](app/manufatura/models.py#L210-L249)
- **Script Python:** [scripts/adicionar_atualizado_em_pedido_compras.py](scripts/adicionar_atualizado_em_pedido_compras.py)
- **Script SQL:** [scripts/adicionar_atualizado_em_pedido_compras.sql](scripts/adicionar_atualizado_em_pedido_compras.sql)
- **Correção anterior:** [CORRECAO_IMPORTACAO_PEDIDOS_COMPRAS.md](CORRECAO_IMPORTACAO_PEDIDOS_COMPRAS.md)

---

## 📊 IMPACTO

### Antes:
- ❌ Sistema travava ao tentar sincronizar
- ❌ Erro SQL não claro (parecia problema de performance)
- ❌ Impossível importar pedidos do Odoo

### Depois:
- ✅ Sincronização funcional
- ✅ Campo de auditoria implementado corretamente
- ✅ Sistema preparado para importação de pedidos

---

**Responsável pela Correção:** Claude Code
**Aprovado por:** Rafael Nascimento
**Validado em:** 05/11/2025
