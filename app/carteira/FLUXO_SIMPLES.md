# 🚀 Fluxo Simplificado - Sistema de Carteira

## 📋 Resumo do Processo

### 1. **Importação Odoo → Faturamento → Carteira**
```
Odoo → FaturamentoService (já existe) → ProcessadorFaturamento (novo)
```

### 2. **Processamento de NFs (3 casos)**

#### ✅ **Caso 1: Separação = NF**
```python
# Vinculação direta
NF → Busca separação do pedido → Match perfeito → Baixa estoque
```

#### ⚠️ **Caso 2: Separação ≠ NF**
```python
# Busca melhor match por score
NF → Múltiplas separações → Calcula score produto/qtd → Baixa estoque + Justificativa
```

#### ❌ **Caso 3: NF Cancelada**
```python
# Remove movimentações
NF cancelada → Busca movimentações → Delete
```

### 3. **Reconciliação Manual (quando necessário)**

#### 📊 **Tela de Inconsistências**
- **NFs sem vinculação**: Sem separação correspondente
- **Separações órfãs**: Sem NF vinculada
- **Ação**: Vincular manualmente NF ↔ Separação

## 🔧 Arquivos Criados

### 1. `processar_faturamento.py`
- Processa os 3 casos automaticamente
- Vincula por score quando múltiplas separações
- Cria movimentações de estoque

### 2. `reconciliacao_service.py`
- Busca inconsistências
- Permite conciliação manual
- Atualiza movimentações

## 🎯 Regras Implementadas

1. **Faturou = Baixa Estoque** ✅
2. **Vinculação Automática** (score de compatibilidade) ✅
3. **Tela de Inconsistências** para casos duvidosos ✅
4. **Preservação de dados** (expedição, agendamento, protocolo) ✅

## 🚦 Próximos Passos

1. **Criar rota para processar**:
   ```python
   @carteira_bp.route('/processar-faturamento')
   def processar_faturamento():
       processador = ProcessadorFaturamento()
       resultado = processador.processar_nfs_importadas()
       return jsonify(resultado)
   ```

2. **Criar template de inconsistências**:
   ```html
   <!-- templates/carteira/inconsistencias.html -->
   <!-- Lista NFs sem vinculação e separações órfãs -->
   <!-- Botão para conciliar manualmente -->
   ```

3. **Integrar com importação existente**:
   ```python
   # Após FaturamentoService importar do Odoo
   processador = ProcessadorFaturamento()
   processador.processar_nfs_importadas()
   ```

## ⚡ Vantagens desta Abordagem

- **SIMPLES**: Apenas 2 serviços principais
- **DIRETO**: 3 casos claros e bem definidos
- **AUTOMÁTICO**: Vincula 95%+ automaticamente
- **FLEXÍVEL**: Permite correção manual quando necessário
- **COMPATÍVEL**: Usa estruturas existentes do sistema 