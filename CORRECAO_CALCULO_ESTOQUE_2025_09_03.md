# 🔧 CORREÇÃO DO CÁLCULO DE ESTOQUE - USAR APENAS CAMPO ATIVO

**Data:** 03/09/2025  
**Problema:** Estoque calculado incorretamente devido ao filtro `status_nf != 'CANCELADO'`  
**Solução:** Usar apenas o campo `ativo` para determinar movimentações válidas

## 🚨 PROBLEMA IDENTIFICADO

### Situação Anterior (INCORRETA)
```python
# ❌ PROBLEMA: NULL != 'CANCELADO' resulta em NULL, não TRUE
resultado = db.session.query(
    func.sum(MovimentacaoEstoque.qtd_movimentacao)
).filter(
    MovimentacaoEstoque.cod_produto.in_(codigos),
    MovimentacaoEstoque.ativo == True,
    MovimentacaoEstoque.status_nf != 'CANCELADO'  # ❌ EXCLUI REGISTROS COM NULL!
).scalar()
```

### Por que estava errado?
1. **Movimentações de PRODUÇÃO**: Não têm NF, logo `status_nf = NULL`
2. **Movimentações de AJUSTE**: Não têm NF, logo `status_nf = NULL`
3. **Movimentações antigas**: Podem ter `status_nf = NULL`

**RESULTADO**: Essas movimentações eram EXCLUÍDAS do cálculo de estoque!

## ✅ SOLUÇÃO IMPLEMENTADA

### Nova Abordagem (CORRETA)
```python
# ✅ CORRETO: Usar apenas o campo ativo
resultado = db.session.query(
    func.sum(MovimentacaoEstoque.qtd_movimentacao)
).filter(
    MovimentacaoEstoque.cod_produto.in_(codigos),
    MovimentacaoEstoque.ativo == True  # Único critério necessário
).scalar()
```

### Vantagens:
1. ✅ **Universal**: Campo `ativo` existe em TODAS as movimentações
2. ✅ **Simples**: Apenas um critério para verificar
3. ✅ **Consistente**: Cancelamento sempre define `ativo=False`
4. ✅ **Performance**: Query mais simples e rápida

## 📝 ARQUIVOS ALTERADOS

### 1. `app/estoque/services/estoque_simples.py`
- **Linha 42-49**: Removido filtro `status_nf != 'CANCELADO'`
- Agora usa apenas `ativo == True`

### 2. `app/odoo/services/faturamento_service.py`
- **Linha 250-258**: Ao cancelar NF, agora define `ativo = False`
- Mantém `status_nf = 'CANCELADO'` para compatibilidade

### 3. `app/estoque/services/compatibility_layer.py`
- **Linha 167**: Removido filtro de `status_nf`
- Usa apenas `ativo == True`

### 4. `app/estoque/api_tempo_real.py`
- **Linhas 168 e 186**: Removido filtro complexo com `or_`
- Usa apenas `ativo == True`

## 🔄 PROCESSO DE CANCELAMENTO

Quando uma NF é cancelada no Odoo:
1. Sistema marca `status_nf = 'CANCELADO'` (para histórico)
2. Sistema marca `ativo = False` (para excluir do estoque)
3. Movimentação não é deletada (mantém auditoria)
4. Estoque é recalculado automaticamente (exclui inativos)

## ⚠️ AÇÕES NECESSÁRIAS

### 1. Verificar dados históricos
```sql
-- Verificar movimentações que estavam sendo ignoradas
SELECT tipo_movimentacao, COUNT(*) 
FROM movimentacao_estoque 
WHERE ativo = true 
  AND status_nf IS NULL
GROUP BY tipo_movimentacao;
```

### 2. Garantir que cancelamentos futuros usem ativo=false
- ✅ Odoo: Já ajustado em `faturamento_service.py`
- ⚠️ TagPlus: Verificar se existe processo similar
- ⚠️ Manual: Orientar usuários a usar `ativo=false`

### 3. Atualizar índices do banco
```sql
-- Índice otimizado para nova query
CREATE INDEX IF NOT EXISTS idx_mov_estoque_produto_ativo 
ON movimentacao_estoque(cod_produto, ativo, qtd_movimentacao)
WHERE ativo = true;
```

## 📊 IMPACTO ESPERADO

### Antes (INCORRETO):
- Excluía movimentações com `status_nf = NULL`
- Estoque calculado MENOR que o real
- Produção e ajustes ignorados

### Depois (CORRETO):
- Inclui TODAS as movimentações ativas
- Estoque calculado CORRETAMENTE
- Todos os tipos de movimentação considerados

## 🎯 REGRA DE OURO

> **SEMPRE use `ativo` para determinar se uma movimentação deve ser considerada no estoque**

- `ativo = true`: Movimentação VALE para o estoque
- `ativo = false`: Movimentação NÃO VALE (cancelada, erro, etc)

## 📞 SUPORTE

Em caso de dúvidas:
1. Verificar se movimentação tem `ativo = true`
2. Não usar `status_nf` para cálculos de estoque
3. Para cancelar: sempre definir `ativo = false`

---

**Correção aplicada com sucesso!** 🎉

O cálculo de estoque agora considera corretamente TODAS as movimentações ativas, independente do tipo ou status de NF.