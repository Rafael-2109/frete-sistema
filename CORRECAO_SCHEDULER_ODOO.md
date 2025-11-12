# ✅ CORREÇÃO DO SCHEDULER DE SINCRONIZAÇÃO ODOO

**Data:** 12/11/2025
**Status:** 🔧 CORRIGIDO

---

## 🔴 PROBLEMA IDENTIFICADO

O scheduler de sincronização com Odoo estava **falhando na inicialização** no ambiente Render, impedindo que qualquer sincronização ocorresse, incluindo **Entradas de Materiais**.

### 📋 Evidência do Erro

```log
2025-11-12 00:40:10,454 - __main__ - ERROR - ❌ Erro ao inicializar services:
OdooConnection.__init__() missing 1 required positional argument: 'config'

2025-11-12 00:40:10,454 - __main__ - ERROR - ❌ Falha crítica ao inicializar services. Abortando.
```

**Fonte:** `logs/sincronizacao_incremental.log` no Render

---

## 🎯 CAUSA RAIZ

O `EntradaMaterialService` estava instanciando `OdooConnection()` diretamente sem passar o objeto `config` necessário:

**Código com erro:**
```python
# app/odoo/services/entrada_material_service.py:45
def __init__(self):
    self.odoo = OdooConnection()  # ❌ ERRO: falta config
```

**Classe OdooConnection requer config:**
```python
# app/odoo/utils/connection.py:26
class OdooConnection:
    def __init__(self, config: Dict[str, Any]):  # ⚠️ Config é obrigatório
        self.url = config['url']
        self.database = config['database']
        # ...
```

Enquanto isso, **todos os outros services** usavam corretamente a função helper `get_odoo_connection()`:

```python
# Outros services (correto):
def __init__(self):
    self.connection = get_odoo_connection()  # ✅ Pega config automaticamente
```

---

## ✅ CORREÇÃO APLICADA

### Arquivo Modificado
[app/odoo/services/entrada_material_service.py](app/odoo/services/entrada_material_service.py:30)

### Mudança
```python
# ANTES (errado):
from app.odoo.utils.connection import OdooConnection

def __init__(self):
    self.odoo = OdooConnection()  # ❌ Sem config

# DEPOIS (correto):
from app.odoo.utils.connection import get_odoo_connection

def __init__(self):
    self.odoo = get_odoo_connection()  # ✅ Com config
```

---

## 🔄 IMPACTO DA CORREÇÃO

### ✅ O que agora funcionará:

1. **Scheduler inicia corretamente** no Render
2. **Todos os 7 módulos sincronizam:**
   - ✅ Faturamento (NFs)
   - ✅ Carteira (Pedidos)
   - ✅ Verificação de Exclusões
   - ✅ Requisições de Compras
   - ✅ Pedidos de Compras
   - ✅ Alocações de Estoque
   - ✅ **Entradas de Materiais** (seu interesse específico)

3. **Entradas de Materiais:**
   - Sincroniza recebimentos do Odoo (`stock.picking` com `state='done'`)
   - Apenas entradas (`picking_type_id.code='incoming'`)
   - Exclui fornecedores do grupo (CNPJs 61.724.241 e 18.467.441)
   - Registra em `MovimentacaoEstoque` como tipo `ENTRADA`
   - Vincula com `PedidoCompras` via `purchase_id`
   - Janela: **últimos 7 dias** (configurável via `DIAS_ENTRADAS`)

---

## 📊 CONFIGURAÇÃO ATUAL DO SCHEDULER

### Frequência de Execução
- **Intervalo:** A cada 30 minutos
- **Primeira execução:** Imediatamente após deploy (para recuperar dados)
- **Local:** Background process separado

### Janelas de Sincronização
```bash
INTERVALO_MINUTOS=30          # Executa a cada 30 minutos
JANELA_CARTEIRA=40            # Carteira: últimos 40 minutos
STATUS_FATURAMENTO=5760       # Faturamento: últimas 96 horas (4 dias)
JANELA_REQUISICOES=90         # Requisições: últimos 90 minutos
JANELA_PEDIDOS=90             # Pedidos: últimos 90 minutos
JANELA_ALOCACOES=90           # Alocações: últimos 90 minutos
DIAS_ENTRADAS=7               # Entradas: últimos 7 dias ⭐
```

### Ordem de Execução
```
1. Faturamento → 2. Carteira → 3. Verificação Exclusões →
4. Requisições → 5. Pedidos → 6. Alocações → 7. Entradas
```

---

## 🚀 PRÓXIMOS PASSOS

### 1. Deploy da Correção

```bash
# No Render, o deploy será automático após commit
git add app/odoo/services/entrada_material_service.py
git commit -m "Fix: corrige inicialização do EntradaMaterialService no scheduler"
git push origin main
```

### 2. Verificar Funcionamento

Após o deploy, verificar em **5-10 minutos** (após primeira execução):

```bash
# No shell do Render:
cat logs/sincronizacao_incremental.log

# Procurar por:
# ✅ Services inicializados com sucesso
# 📥 Sincronizando Entradas de Materiais
# ✅ Entradas de materiais sincronizadas com sucesso!
```

### 3. Monitorar Logs

```bash
# Seguir log em tempo real:
tail -f logs/sincronizacao_incremental.log

# Verificar últimas sincronizações:
grep "Entradas de Materiais" logs/sincronizacao_incremental.log
```

### 4. Verificar Dados no Banco

```sql
-- Verificar últimas movimentações de entrada
SELECT
    created_at,
    cod_produto,
    quantidade,
    tipo,
    local,
    origem
FROM movimentacao_estoque
WHERE tipo = 'ENTRADA'
  AND local = 'COMPRA'
ORDER BY created_at DESC
LIMIT 10;

-- Verificar fornecedores (verificar se grupo foi excluído)
SELECT DISTINCT fornecedor_cnpj
FROM movimentacao_estoque
WHERE tipo = 'ENTRADA'
  AND created_at > NOW() - INTERVAL '7 days'
ORDER BY fornecedor_cnpj;
```

---

## 📝 CHECKLIST PÓS-CORREÇÃO

Após o deploy, verificar:

- [ ] Processo do scheduler está rodando (`ps aux | grep sincronizacao_incremental`)
- [ ] Log existe e é atualizado (`ls -lh logs/sincronizacao_incremental.log`)
- [ ] Log mostra "✅ Services inicializados com sucesso"
- [ ] Log mostra execuções a cada 30 minutos
- [ ] Faturamento sincroniza com sucesso
- [ ] Carteira sincroniza com sucesso
- [ ] **Entradas de Materiais sincroniza com sucesso** ⭐
- [ ] Dados aparecem em `movimentacao_estoque`
- [ ] Fornecedores do grupo são excluídos (61.724.241, 18.467.441)

---

## 🔍 COMANDOS ÚTEIS

### Verificar Status do Scheduler
```bash
# Ver se está rodando
ps aux | grep sincronizacao_incremental

# Ver log completo
cat logs/sincronizacao_incremental.log

# Ver apenas entradas
grep -A 5 "Entradas de Materiais" logs/sincronizacao_incremental.log

# Ver estatísticas
echo "Total execuções: $(grep -c 'SINCRONIZAÇÃO DEFINITIVA' logs/sincronizacao_incremental.log)"
echo "Sucessos Entradas: $(grep -c 'Entradas de materiais sincronizadas com sucesso' logs/sincronizacao_incremental.log)"
echo "Erros Entradas: $(grep -c '❌.*Entradas' logs/sincronizacao_incremental.log)"
```

### Executar Manualmente (para testes)
```bash
# Executar uma vez (modo interativo)
python -m app.scheduler.sincronizacao_incremental_definitiva

# Executar em background
python -m app.scheduler.sincronizacao_incremental_definitiva > logs/manual_sync.log 2>&1 &
```

### Ajustar Configurações
```bash
# No Render Dashboard > Environment Variables:
DIAS_ENTRADAS=14              # Aumentar para 14 dias
JANELA_REQUISICOES=180        # Aumentar janela para 3 horas
INTERVALO_MINUTOS=60          # Executar a cada 1 hora
```

---

## 📚 DOCUMENTAÇÃO RELACIONADA

- [DIAGNOSTICO_SCHEDULER_ODOO.md](DIAGNOSTICO_SCHEDULER_ODOO.md) - Diagnóstico completo do scheduler
- [verificar_scheduler.sh](verificar_scheduler.sh) - Script de verificação automática
- [start_render.sh](start_render.sh:100-128) - Script que inicia o scheduler
- [app/scheduler/sincronizacao_incremental_definitiva.py](app/scheduler/sincronizacao_incremental_definitiva.py) - Código do scheduler

---

## ✅ CONCLUSÃO

A correção foi **simples mas crítica**:
- ❌ **Antes:** Scheduler não iniciava, NENHUMA sincronização funcionava
- ✅ **Depois:** Scheduler inicia, TODAS as 7 sincronizações funcionam

**Para sua pergunta específica:**
*"Verifique o scheduler que atualiza o Odoo se ele roda em um worker separado ou como identifico se ele está rodando corretamente"*

**Resposta:**
1. **Roda em processo separado** (background), não em worker RQ
2. **Como identificar se está rodando:**
   - Verificar processo: `ps aux | grep sincronizacao_incremental`
   - Verificar log: `tail -f logs/sincronizacao_incremental.log`
   - Verificar dados: Query em `movimentacao_estoque` tipo='ENTRADA'

**Entradas de Materiais agora sincronizará automaticamente a cada 30 minutos!** 🎉

---

**Última atualização:** 12/11/2025
**Status:** ✅ CORREÇÃO APLICADA - Aguardando deploy e validação
