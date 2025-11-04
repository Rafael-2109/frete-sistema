# 🔴 CORREÇÃO CRÍTICA: Proteção contra Múltiplos Lotes

## 📋 PROBLEMA IDENTIFICADO

**Arquivo**: `app/odoo/services/ajuste_sincronizacao_service.py`
**Função afetada**: `_identificar_lotes_afetados()` e `processar_pedido_alterado()`

### Sintoma
Quando um pedido possui **N** `separacao_lote_id` diferentes (ex: 3 lotes), a sincronização estava:
1. Identificando todos os lotes do pedido
2. Processando CADA lote com a quantidade TOTAL do pedido
3. **RESULTADO**: Quantidade multiplicada por N (ex: triplicada se 3 lotes)

### Causa Raiz
A função `processar_pedido_alterado()` recebia:
- `num_pedido`: Pedido a processar
- `itens_odoo`: Lista com quantidades TOTAIS do pedido (não separadas por lote)

E então processava **cada lote encontrado** com os mesmos `itens_odoo`, causando a multiplicação.

---

## ✅ SOLUÇÃO IMPLEMENTADA

### Regra de Negócio Confirmada
> **Pedidos com múltiplos `separacao_lote_id` NÃO devem ser alterados automaticamente**

Motivo: Quando um pedido foi dividido manualmente em múltiplos lotes, houve uma decisão operacional específica que não deve ser revertida pela sincronização automática.

### Código Alterado

**Arquivo**: `app/odoo/services/ajuste_sincronizacao_service.py`
**Linhas**: 171-179

```python
# 🔴 PROTEÇÃO CRÍTICA: Se pedido tem múltiplos lotes, IGNORAR completamente
# Pedidos divididos manualmente não devem ser alterados automaticamente
if len(seps) > 1:
    lotes_ids = [lote_id for lote_id, _, _ in seps]
    logger.warning(
        f"🛡️ PROTEÇÃO: Pedido {num_pedido} possui {len(seps)} separacao_lote_id diferentes "
        f"({', '.join(lotes_ids)}) - Alteração automática BLOQUEADA para evitar corrupção de dados"
    )
    return []  # Retorna vazio para não processar
```

### O que a correção faz:

1. **Verifica** quantos `separacao_lote_id` distintos existem para o pedido
2. **Se > 1 lote**: Retorna lista vazia → pedido NÃO será processado
3. **Se = 1 lote**: Continua normalmente → pedido será processado
4. **Logs claros**: Informa exatamente por que o pedido foi bloqueado

---

## 🎯 IMPACTO E COMPORTAMENTO

### ANTES da correção:
```
Pedido VSC12345 com 3 lotes:
- Lote A: 100 unidades → ATUALIZADO para 300 (ERRADO!)
- Lote B: 100 unidades → ATUALIZADO para 300 (ERRADO!)
- Lote C: 100 unidades → ATUALIZADO para 300 (ERRADO!)
TOTAL: 900 unidades (deveria ser 300)
```

### DEPOIS da correção:
```
Pedido VSC12345 com 3 lotes:
⚠️ PROTEÇÃO: Pedido possui 3 separacao_lote_id diferentes
→ Alteração automática BLOQUEADA
→ Lotes mantidos como estavam (100 + 100 + 100 = 300)
```

---

## 📊 CENÁRIOS COBERTOS

### ✅ Cenário 1: Pedido com 1 único lote
- **Status**: Processado normalmente ✅
- **Ação**: Atualiza quantidades conforme Odoo
- **Resultado**: Funciona como antes

### ✅ Cenário 2: Pedido com múltiplos lotes (2+)
- **Status**: BLOQUEADO pela proteção 🛡️
- **Ação**: Nenhuma alteração automática
- **Resultado**: Quantidades preservadas
- **Log**: Warning claro com IDs dos lotes

### ✅ Cenário 3: Pedido com NF processada sem lote
- **Status**: Já tinha proteção anterior ✅
- **Ação**: Continua bloqueado
- **Resultado**: Sem mudanças (proteção existente mantida)

---

## 🔍 VALIDAÇÃO

### Como verificar se a correção está funcionando:

1. **Procurar nos logs** por mensagens como:
   ```
   🛡️ PROTEÇÃO: Pedido VSC12345 possui 3 separacao_lote_id diferentes
   (lote_A, lote_B, lote_C) - Alteração automática BLOQUEADA
   ```

2. **Query SQL para testar**:
   ```sql
   -- Encontrar pedidos com múltiplos lotes
   SELECT
       num_pedido,
       COUNT(DISTINCT separacao_lote_id) as total_lotes,
       STRING_AGG(DISTINCT separacao_lote_id, ', ') as lotes_ids
   FROM separacao
   WHERE separacao_lote_id IS NOT NULL
     AND sincronizado_nf = FALSE
   GROUP BY num_pedido
   HAVING COUNT(DISTINCT separacao_lote_id) > 1;
   ```

3. **Executar sincronização** e verificar que pedidos com múltiplos lotes:
   - NÃO aparecem em "alterações aplicadas"
   - APARECEM nos logs com mensagem de proteção
   - Mantêm quantidades originais intactas

---

## 📝 DOCUMENTAÇÃO ATUALIZADA

A função `_identificar_lotes_afetados()` agora documenta explicitamente:

```python
"""
Identifica todos os lotes de Separacao afetados pelo pedido.

IMPORTANTE:
- Processa apenas Separacao com sincronizado_nf=False
- Apenas status alteráveis: PREVISAO, ABERTO, COTADO
- 🔴 PROTEÇÃO: IGNORA pedidos com múltiplos separacao_lote_id

Returns:
    Lista de dicts com {lote_id, tipo, status}
"""
```

---

## ⚠️ AÇÃO NECESSÁRIA APÓS DEPLOY

1. **Monitorar logs** na primeira sincronização após deploy
2. **Verificar pedidos** que tinham problema antes do fix
3. **Documentar casos** onde múltiplos lotes foram bloqueados
4. **Decidir estratégia** para pedidos já corrompidos (se houver):
   - Correção manual?
   - Script de restauração?
   - Aceitar estado atual?

---

## 📚 ARQUIVOS MODIFICADOS

- ✅ `app/odoo/services/ajuste_sincronizacao_service.py` (linhas 140, 171-179)
- ✅ `CORRECAO_MULTIPLOS_LOTES.md` (este arquivo - documentação)
- ✅ `testar_protecao_multiplos_lotes.py` (script de teste - opcional)

---

## 🔐 SEGURANÇA

Esta correção adiciona uma **camada crítica de proteção** que previne:
- ❌ Multiplicação indevida de quantidades
- ❌ Corrupção de dados em pedidos divididos manualmente
- ❌ Perda de decisões operacionais anteriores
- ❌ Inconsistências entre lotes do mesmo pedido

**Data da Correção**: 2025-11-03
**Autor**: Rafael Nascimento (via Claude Code)
**Revisão**: Aprovada pelo usuário
