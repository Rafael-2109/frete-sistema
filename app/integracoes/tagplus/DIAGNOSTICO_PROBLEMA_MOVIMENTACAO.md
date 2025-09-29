# 🚨 DIAGNÓSTICO: Problema de Movimentação de Estoque - TagPlus

## 📍 ACESSO À TELA DE CORREÇÃO DE PEDIDOS

**URL:** `/integracoes/tagplus/correcao-pedidos`

Esta tela permite:
- Listar NFs importadas sem número de pedido
- Preencher o número do pedido manualmente
- Reprocessar NFs corrigidas

---

## 🔴 PROBLEMAS IDENTIFICADOS

### 1. **NFs sem Pedido Não Geram Movimentação Correta**

#### Fluxo Atual:
```
ImportadorTagPlusV2.importar_nfs()
    ↓
_processar_nfe() → cria FaturamentoProduto
    ↓
_consolidar_relatorio_faturamento() → cria RelatorioFaturamentoImportado
    ↓
_processar_faturamento() → ProcessadorFaturamento.processar_nfs_importadas()
    ↓
_processar_nf_simplificado()
    ↓
SE nf.origem (pedido) está VAZIO:
    → NÃO encontra EmbarqueItem
    → Chama _criar_movimentacao_sem_separacao()
```

#### Problema no _criar_movimentacao_sem_separacao():

**Arquivo:** `app/faturamento/services/processar_faturamento.py` linha 257-260

```python
# ERRO: Está marcando como ODOO mas deveria ser TAGPLUS
mov.tipo_origem = "ODOO"  # ProcessadorFaturamento processa dados do Odoo
```

### 2. **Captura do Pedido no TagPlus**

**Arquivo:** `app/integracoes/tagplus/importador_v2.py` linha 457-463

```python
origem=(
    str(nfe_data.get('numero_pedido', '') or '') or
    str(item.get('numero_pedido_compra', '') or '') or
    ''  # ← SE AMBOS VAZIOS, ORIGEM FICA VAZIA
)
```

Se a NF do TagPlus não tem o campo `numero_pedido` nem `numero_pedido_compra`, o campo `origem` fica vazio.

---

## 🔧 SOLUÇÕES NECESSÁRIAS

### 1. **Corrigir tipo_origem em ProcessadorFaturamento**

**PROBLEMA:** ProcessadorFaturamento sempre marca `tipo_origem = 'ODOO'`

**SOLUÇÃO:** Detectar a origem baseado no campo `created_by` do FaturamentoProduto:

```python
# Em _criar_movimentacao_sem_separacao
# Detectar origem baseado em quem criou
if produtos and len(produtos) > 0:
    primeiro_produto = produtos[0]
    if 'TagPlus' in (primeiro_produto.created_by or ''):
        tipo_origem = 'TAGPLUS'
    else:
        tipo_origem = 'ODOO'
else:
    tipo_origem = 'ODOO'  # fallback

mov.tipo_origem = tipo_origem
```

### 2. **Fluxo de Correção de Pedidos**

O fluxo correto para NFs sem pedido é:

1. **Importar NFs** → Cria FaturamentoProduto e RelatorioFaturamentoImportado
2. **Processar** → Cria MovimentacaoEstoque "Sem Separação"
3. **Acessar Tela de Correção** → `/integracoes/tagplus/correcao-pedidos`
4. **Preencher Pedidos** → Atualiza campo `origem`
5. **Reprocessar** → Vincula com EmbarqueItem e atualiza movimentações

---

## 📋 VERIFICAÇÃO DO FLUXO COMPLETO

### ✅ Fluxo FUNCIONANDO:
1. **Autenticação OAuth2** ✅
2. **Buscar NFs da API TagPlus** ✅
3. **Criar FaturamentoProduto** ✅
4. **Criar RelatorioFaturamentoImportado** ✅
5. **Tela de Correção de Pedidos** ✅

### ⚠️ Fluxo COM PROBLEMAS:
1. **Criar MovimentacaoEstoque** ⚠️
   - Cria mas com `tipo_origem = 'ODOO'` incorreto
   - Se não tem pedido, cria "Sem Separação"

2. **Vincular com EmbarqueItem** ⚠️
   - Só funciona se NF tem pedido preenchido
   - Sem pedido, não vincula

3. **Atualizar Separacao.sincronizado_nf** ⚠️
   - Só funciona se encontrar EmbarqueItem
   - Sem pedido, não atualiza

---

## 🎯 AÇÃO RECOMENDADA

### Passo 1: Corrigir NFs Já Importadas
```sql
-- Ver quantas NFs estão sem pedido
SELECT COUNT(*)
FROM relatorio_faturamento_importado
WHERE (origem IS NULL OR origem = '' OR origem = ' ')
  AND ativo = true;

-- Ver movimentações criadas incorretamente
SELECT COUNT(*)
FROM movimentacao_estoque
WHERE tipo_origem = 'ODOO'
  AND criado_por = 'ImportTagPlus';
```

### Passo 2: Usar Tela de Correção
1. Acessar `/integracoes/tagplus/correcao-pedidos`
2. Preencher pedidos faltantes
3. Reprocessar NFs

### Passo 3: Corrigir o Código
Implementar a correção do `tipo_origem` no ProcessadorFaturamento

---

## 📊 RESUMO

**CAUSA RAIZ:** NFs do TagPlus frequentemente não têm número de pedido, causando:
1. Movimentações criadas com tipo_origem incorreto
2. Não vinculação com EmbarqueItem
3. Não atualização de Separacao.sincronizado_nf

**SOLUÇÃO:**
1. Usar tela de correção para preencher pedidos
2. Corrigir ProcessadorFaturamento para detectar origem correta
3. Reprocessar NFs após correção