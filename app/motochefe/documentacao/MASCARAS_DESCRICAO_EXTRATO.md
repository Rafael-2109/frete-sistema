# 📋 Máscaras de Descrição do Extrato Financeiro

## 📍 Localização
**Arquivo:** `app/motochefe/services/extrato_financeiro_service.py`

---

## 🟢 RECEBIMENTOS

### 1. Movimentações Financeiras (MovimentacaoFinanceira)
**Fonte:** Tabela `movimentacao_financeira` onde `tipo='RECEBIMENTO'`

**Máscara:**
```sql
CONCAT(
    mf.descricao,
    CASE WHEN mf.origem_identificacao IS NOT NULL
         THEN CONCAT(' - ', mf.origem_identificacao)
         ELSE '' END
)
```

**Exemplos:**
- `"Recebimento Parcela 1/3 - Cliente XYZ"`
- `"Recebimento Moto Chassi ABC123 - Cliente XYZ"`
- `"Recebimento 5 títulos - Cliente XYZ"`

**Campos disponíveis:**
- `mf.categoria` - Ex: "Título", "Lote Título" (disponível mas não usado na descrição)
- `mf.descricao` - Descrição detalhada (sem prefixo de categoria)
- `mf.origem_identificacao` - Nome do cliente/origem

---

## 🔴 PAGAMENTOS

### 2. Pagamentos de Lote e Individuais (MovimentacaoFinanceira)
**Fonte:** Tabela `movimentacao_financeira` onde `tipo='PAGAMENTO'`

**Máscara:**
```sql
mf.descricao
```

**Categorias:**
- **Lotes:**
  - `'Lote Custo Moto'`
  - `'Lote Comissão'`
  - `'Lote Montagem'`
  - `'Lote Despesa'`

- **Individuais:**
  - `'Custo Moto'`
  - `'Comissão'`
  - `'Montagem'`
  - `'Despesa'`
  - `'Frete'`

**Exemplos:**
- `"Pagamento Lote 10 custo(s) de moto"`
- `"Custo Moto Chassi ABC123 - NF 12345 - Fornecedor ABC"`
- `"Comissão Vendedor João - Pedido MC 0001 - Chassi ABC123"`
- `"Montagem Chassi ABC123 - Oficina XYZ"`
- `"Pagamento Despesa - Aluguel"`

**Cliente/Fornecedor:**
```sql
COALESCE(
    mf.destino_identificacao,
    (SELECT empresa FROM empresa_venda_moto WHERE id = mf.empresa_destino_id),
    'Fornecedor'
)
```

---

### 3. Fretes (EmbarqueMoto)
**Fonte:** Tabela `embarque_moto` onde `status_pagamento_frete='PAGO'`

**Máscara:**
```sql
CONCAT(
    'Frete Embarque ', em.numero_embarque,
    ' - Transportadora: ', tm.transportadora
)
```

**Exemplo:**
- `"Frete Embarque 123 - Transportadora: TransLog Ltda"`

**Cliente/Fornecedor:**
```sql
tm.transportadora
```

---

## 📊 Estrutura de Retorno

Cada movimentação retorna um dict com:

```python
{
    'tipo': 'RECEBIMENTO' ou 'PAGAMENTO',
    'categoria': str,  # 'Título', 'Custo Moto', 'Comissão', etc.
    'data_movimentacao': date,
    'descricao': str,  # Conforme máscaras acima
    'valor': Decimal,  # Positivo para recebimento, negativo para pagamento
    'cliente_fornecedor': str,
    'numero_pedido': str ou None,
    'numero_nf': str ou None,
    'numero_chassi': str ou None,
    'numero_embarque': str ou None,
    'rota_detalhes': str,  # URL para detalhes
    'id_original': str,
    'criado_em': datetime  # Data de criação do registro
}
```

---

## 🔄 Ordenação

**Critério:** `ORDER BY criado_em DESC, id_original DESC`

- **Primário:** Data de criação (mais recentes primeiro)
- **Secundário:** ID original (desempate)

---

## 📝 Observações

1. **Movimentações FILHAS não aparecem:**
   - Apenas movimentações PAI (lotes) e individuais aparecem
   - Filtro: `movimentacao_origem_id IS NULL`

2. **Fretes ainda em tabela separada:**
   - EmbarqueMoto ainda não migrado para MovimentacaoFinanceira
   - Usa `data_pagamento_frete` e `criado_em` da tabela `embarque_moto`

3. **Valores:**
   - Recebimentos: valor positivo
   - Pagamentos: valor negativo

4. **Saldo Acumulado:**
   - Calculado após a query principal
   - Função: `calcular_saldo_acumulado()`

---

**Última Atualização:** 11/10/2025
