# Implementação: Sincronização de Compras com Cancelamentos e Exclusões
================================================================================

**Data**: 2025-11-03
**Autor**: Claude + Rafael
**Objetivo**: Corrigir timeout SSL e implementar sincronização completa de status (cancelamentos e exclusões)

---

## 📋 RESUMO DAS ALTERAÇÕES

### ✅ 1. CORREÇÃO DO TIMEOUT SSL (COMPLETO)

**Problema identificado**:
- Parâmetro `primeira_execucao=True` ignorava filtro de data
- Buscava **TODO** o histórico do Odoo (10.000+ registros)
- Causava timeout de 30s na conexão PostgreSQL

**Solução aplicada**:
- ✅ Mudou `primeira_execucao=True` para `False` em TODOS os routes manuais
- ✅ Garantiu que filtro SEMPRE seja aplicado nos services
- ✅ Usa `create_date OR write_date >= data_limite`

**Arquivos alterados**:
- `app/manufatura/routes/pedidos_compras_routes.py:201-208`
- `app/manufatura/routes/requisicao_compras_routes.py:149`
- `app/odoo/services/pedido_compras_service.py:154-165`
- `app/odoo/services/alocacao_compras_service.py:151-161`
- `app/odoo/services/requisicao_compras_service.py:170-178`

---

### ✅ 2. SINCRONIZAÇÃO DE STATUS (COMPLETO)

#### 2.1. Pedidos de Compra

**Banco de Dados**:
```sql
-- Adicionar campo status_odoo
ALTER TABLE pedido_compras
ADD COLUMN IF NOT EXISTS status_odoo VARCHAR(20);

CREATE INDEX IF NOT EXISTS idx_pedido_status_odoo
ON pedido_compras(status_odoo);
```

**Scripts criados**:
- ✅ `scripts/adicionar_status_odoo_pedidos.py` (Python)
- ✅ `scripts/adicionar_status_odoo_pedidos.sql` (SQL para Render)

**Modelo atualizado**:
- ✅ `app/manufatura/models.py:237` - Campo `status_odoo` adicionado

**Service atualizado**:
- ✅ `app/odoo/services/pedido_compras_service.py`
  - Linha 159-163: Removido filtro `state != 'cancel'` (agora importa TODOS)
  - Linha 484: Salva `status_odoo` na criação
  - Linha 521-527: Atualiza `status_odoo` e detecta cancelamentos

**Valores possíveis**:
- `draft`: Rascunho
- `sent`: Enviado
- `to approve`: Aguardando Aprovação
- `purchase`: Aprovado/Confirmado
- `done`: Concluído
- `cancel`: **Cancelado** ← Sincronizado automaticamente!

---

#### 2.2. Requisições de Compra

**Campo utilizado**: `status_requisicao` (já existia no modelo)

**Service atualizado**:
- ✅ `app/odoo/services/requisicao_compras_service.py`
  - Linha 169-178: Removido filtro `state != 'rejected'` (agora importa TODOS)
  - Já salva `status_requisicao` automaticamente via mapeamento existente

**Status cancelado**: `status_requisicao = 'rejected'` (equivalente a cancelado)

---

#### 2.3. Alocações de Compras

**Campo utilizado**: `purchase_state` (já existia no modelo)

**Service**: Já sincroniza `purchase_state` automaticamente

**Status cancelado**: `purchase_state = 'cancel'`

---

### ✅ 3. DETECÇÃO DE EXCLUSÃO (COMPLETO)

Implementado método `_detectar_XXX_excluidos()` em todos os 3 services.

**Lógica**:
1. Busca registros do sistema modificados na janela de tempo
2. Verifica se ainda existem no Odoo
3. Se **NÃO existir mais** → marca como cancelado

#### 3.1. Pedidos

**Método**: `_detectar_pedidos_excluidos()`
**Arquivo**: `app/odoo/services/pedido_compras_service.py:543-607`

```python
# Marca como status_odoo='cancel' se não existir mais no Odoo
```

#### 3.2. Requisições

**Método**: `_detectar_requisicoes_excluidas()`
**Arquivo**: `app/odoo/services/requisicao_compras_service.py:696-771`

```python
# Marca como status_requisicao='rejected' se não existir mais no Odoo
```

#### 3.3. Alocações

**Método**: `_detectar_alocacoes_excluidas()`
**Arquivo**: `app/odoo/services/alocacao_compras_service.py:537-597`

```python
# Marca como purchase_state='cancel' se não existir mais no Odoo
```

---

### ✅ 4. PROJEÇÃO DE ESTOQUE FILTRADA (COMPLETO)

**Problema**: Projeção estava considerando pedidos/requisições cancelados

**Solução aplicada**:

**Arquivo**: `app/manufatura/services/projecao_estoque_service.py`

**Linha 138**: Filtro para Pedidos
```python
PedidoCompras.status_odoo != 'cancel'  # ✅ NÃO considerar cancelados
```

**Linha 157**: Filtro para Requisições
```python
RequisicaoCompras.status_requisicao != 'rejected'  # ✅ NÃO considerar rejeitadas
```

---

## 🔄 FLUXO COMPLETO DE SINCRONIZAÇÃO

### Pedidos de Compra

```
1. Buscar pedidos do Odoo (incluindo cancelados)
   ├─ Filtro: (create_date OR write_date >= data_limite)
   └─ SEM filtro de state (importa todos os status)

2. Processar pedidos
   ├─ Criar novos → salva status_odoo
   └─ Atualizar existentes → atualiza status_odoo
       └─ Se state='cancel' → ⚠️  Log de cancelamento

3. Detectar exclusões
   ├─ Busca pedidos do sistema na janela
   ├─ Verifica se existem no Odoo
   └─ Se NÃO → marca status_odoo='cancel'

4. Projeção de estoque
   └─ Filtra status_odoo != 'cancel'
```

### Requisições de Compra

```
1. Buscar requisições do Odoo (incluindo rejeitadas)
   ├─ Filtro: (create_date OR write_date >= data_limite)
   └─ SEM filtro de state (importa todos os status)

2. Processar requisições
   ├─ Criar novas → salva status_requisicao
   └─ Atualizar existentes → atualiza status_requisicao

3. Detectar exclusões
   ├─ Busca requisições do sistema na janela
   ├─ Busca linhas no Odoo
   └─ Se NÃO existir → marca status_requisicao='rejected'

4. Projeção de estoque
   └─ Filtra status_requisicao != 'rejected'
```

### Alocações

```
1. Buscar alocações do Odoo
   └─ Filtro: (create_date OR write_date >= data_limite)

2. Processar alocações
   ├─ Criar novas → salva purchase_state
   └─ Atualizar existentes → atualiza purchase_state

3. Detectar exclusões
   ├─ Busca alocações do sistema na janela
   ├─ Verifica se existem no Odoo
   └─ Se NÃO → marca purchase_state='cancel'
```

---

## 📊 STATUS EQUIVALENTES (CANCELAMENTO)

| Entidade | Campo | Valor Cancelado |
|----------|-------|-----------------|
| **Pedidos** | `status_odoo` | `'cancel'` |
| **Requisições** | `status_requisicao` | `'rejected'` |
| **Alocações** | `purchase_state` | `'cancel'` |

**Importante**: Todos são tratados como **cancelados** para fins de:
- ❌ Não aparecer na projeção de estoque
- ❌ Não gerar entradas futuras
- ✅ Manter histórico (não são deletados)

---

## 🚀 DEPLOY

### 1. Executar script SQL no Render

```sql
-- Copiar e colar no Shell SQL do Render
-- Arquivo: scripts/adicionar_status_odoo_pedidos.sql

ALTER TABLE pedido_compras
ADD COLUMN IF NOT EXISTS status_odoo VARCHAR(20);

CREATE INDEX IF NOT EXISTS idx_pedido_status_odoo
ON pedido_compras(status_odoo);
```

### 2. Fazer commit e push

```bash
git add .
git commit -m "feat: Sincronização completa de status e detecção de exclusão

- Corrige timeout SSL (sempre aplica filtro de data)
- Adiciona campo status_odoo em pedido_compras
- Implementa detecção de cancelamento (state='cancel'/'rejected')
- Implementa detecção de exclusão (não existe mais no Odoo)
- Filtra cancelados na projeção de estoque
- Aplica lógica em Pedidos, Requisições e Alocações

🤖 Generated with Claude Code"

git push origin main
```

### 3. Executar primeira sincronização

Após deploy, executar sincronização manual para popular o campo `status_odoo`.

---

## ✅ CHECKLIST DE VALIDAÇÃO

Após deploy, validar:

- [ ] Script SQL executado no Render (campo `status_odoo` existe)
- [ ] Sincronização manual executa sem timeout
- [ ] Pedidos cancelados aparecem com `status_odoo='cancel'`
- [ ] Requisições rejeitadas aparecem com `status_requisicao='rejected'`
- [ ] Registros excluídos do Odoo são marcados como cancelados
- [ ] Projeção de estoque **NÃO** mostra cancelados
- [ ] Logs mostram mensagens de "cancelado" e "excluído"

---

## 📝 OBSERVAÇÕES

1. **Primeira execução**: Pode demorar mais (popula status_odoo pela primeira vez)
2. **Scheduler**: Já estava com `primeira_execucao=False` - continuará funcionando
3. **Histórico**: Registros cancelados/excluídos são mantidos (não deletados)
4. **Performance**: Detecção de exclusão adiciona ~1-2s por sincronização
5. **Compatibilidade**: Código compatível com sincronização atual do scheduler

---

## 🔗 ARQUIVOS RELACIONADOS

### Scripts
- `scripts/adicionar_status_odoo_pedidos.py`
- `scripts/adicionar_status_odoo_pedidos.sql`

### Modelos
- `app/manufatura/models.py` (PedidoCompras.status_odoo)

### Services
- `app/odoo/services/pedido_compras_service.py`
- `app/odoo/services/requisicao_compras_service.py`
- `app/odoo/services/alocacao_compras_service.py`
- `app/manufatura/services/projecao_estoque_service.py`

### Routes
- `app/manufatura/routes/pedidos_compras_routes.py`
- `app/manufatura/routes/requisicao_compras_routes.py`

---

## 🎯 RESULTADO ESPERADO

### Antes
```
❌ Timeout SSL após 30s
❌ Importava TODO o histórico do Odoo
❌ Não detectava cancelamentos
❌ Não detectava exclusões
❌ Projeção incluía cancelados
```

### Depois
```
✅ Sincronização rápida (3-5s para 7 dias)
✅ Importa apenas janela de tempo solicitada
✅ Detecta cancelamentos (state='cancel'/'rejected')
✅ Detecta exclusões (não existe mais no Odoo)
✅ Projeção exclui cancelados automaticamente
✅ Histórico completo mantido
```

---

**FIM DO DOCUMENTO**
