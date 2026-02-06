# Cadeia Completa: Pedido -> Entrega

Documentacao da cadeia de dados desde o pedido ate a entrega final, incluindo JOINs, campos-chave e estados.

---

## Cadeia de Tabelas

```
CarteiraPrincipal (num_pedido)
    │
    ├── qtd_produto_pedido (total)
    ├── qtd_saldo_produto_pedido (pendente de faturamento)
    └── preco_produto_pedido
    │
    ▼
Separacao (num_pedido)
    │
    ├── sincronizado_nf = False → em separacao (pre-faturamento)
    ├── sincronizado_nf = True  → ja faturado
    ├── qtd_saldo (qtd na separacao)
    ├── expedicao (data programada)
    └── separacao_lote_id (chave para embarque)
    │
    ▼
EmbarqueItem (separacao_lote_id)
    │
    ├── embarque_id → Embarque
    ├── cnpj_cliente, cliente, pedido
    ├── nota_fiscal, peso, valor
    └── uf_destino, cidade_destino
    │
    ▼
Embarque (id)
    │
    ├── numero (identificador unico)
    ├── data_embarque
    ├── tipo_carga (DIRETA, FRACIONADA)
    ├── transportadora_id → Transportadora
    └── peso_total, valor_total
    │
    ▼
FaturamentoProduto (numero_nf)
    │
    ├── IMPORTANTE: campo 'origem' = num_pedido (link direto!)
    ├── cnpj_cliente, nome_cliente
    ├── cod_produto, nome_produto
    ├── qtd_faturada, valor_produto_faturado
    └── data_fatura
    │
    ▼
EntregaMonitorada (numero_nf)
    │
    ├── status_finalizacao (NULL=pendente, 'Entregue', etc.)
    ├── data_embarque, data_entrega_prevista
    ├── data_hora_entrega_realizada
    ├── entregue (boolean)
    ├── nf_cd (boolean - voltou pro CD?)
    ├── lead_time (dias)
    ├── transportadora
    └── canhoto_arquivo
    │
    ▼
Frete (embarque_id)
    │
    ├── valor_cotado (tabela de preco)
    ├── valor_cte (cobrado pela transportadora)
    ├── valor_pago (efetivo)
    ├── numeros_nfs (CSV)
    └── tipo_carga, peso_total, uf_destino
```

---

## JOINs Chave

### Pedido -> Separacao
```sql
SELECT * FROM separacao WHERE num_pedido = 'VCD123'
```

### Separacao -> Embarque
```sql
SELECT e.* FROM embarques e
JOIN embarque_itens ei ON ei.embarque_id = e.id
WHERE ei.separacao_lote_id = [separacao.separacao_lote_id]
```

### Pedido -> NF (via FaturamentoProduto.origem)
```sql
-- LINK DIRETO (mais simples):
SELECT * FROM faturamento_produto WHERE origem = 'VCD123'

-- LINK ALTERNATIVO (via separacao):
SELECT fp.* FROM faturamento_produto fp
JOIN separacao s ON s.numero_nf = fp.numero_nf
WHERE s.num_pedido = 'VCD123' AND s.sincronizado_nf = True
```

### NF -> Entrega
```sql
SELECT * FROM entregas_monitoradas WHERE numero_nf = '12345'
```

### Embarque -> Frete
```sql
SELECT * FROM fretes WHERE embarque_id = [embarque.id]
```

### Co-passageiros (quem embarcou junto)
```sql
SELECT * FROM embarque_itens WHERE embarque_id = [embarque.id]
-- Retorna todos os clientes/pedidos/NFs no mesmo caminhao
```

---

## Estados do Pedido

### 1. Em Carteira (pendente)
```sql
CarteiraPrincipal WHERE num_pedido = 'X'
  AND qtd_saldo_produto_pedido > 0
```

### 2. Separado (aguardando faturamento)
```sql
Separacao WHERE num_pedido = 'X'
  AND sincronizado_nf = False
```

### 3. Faturado (NF emitida)
```sql
FaturamentoProduto WHERE origem = 'X'
```

### 4. Em Transito
```sql
EntregaMonitorada WHERE numero_nf IN (NFs do pedido)
  AND status_finalizacao IS NULL
  AND data_embarque IS NOT NULL
  AND nf_cd = False
```

### 5. Entregue
```sql
EntregaMonitorada WHERE numero_nf IN (NFs do pedido)
  AND entregue = True
```

### 6. Devolvido (parcial ou total)
```sql
EntregaMonitorada WHERE numero_nf IN (NFs do pedido)
  AND teve_devolucao = True
-- Detalhes: NFDevolucao via entrega_monitorada_id ou numero_nf
```

---

## Formulas de Calculo por Pedido

### Total do pedido (valor original)
```sql
SELECT SUM(qtd_produto_pedido * preco_produto_pedido)
FROM carteira_principal WHERE num_pedido = 'VCD123'
```

### Total pendente de faturamento
```sql
SELECT SUM(qtd_saldo_produto_pedido * preco_produto_pedido)
FROM carteira_principal WHERE num_pedido = 'VCD123'
```

### Total programado para expedicao
```sql
SELECT SUM(qtd_saldo) as qtd, SUM(valor_saldo) as valor
FROM separacao
WHERE sincronizado_nf = False AND num_pedido = 'VCD123'
```

### Valor faturado
```sql
SELECT SUM(valor_produto_faturado)
FROM faturamento_produto WHERE origem = 'VCD123'
```

### O que falta entregar
```sql
-- Calculo: total pedido - faturado entregue
-- Requer cruzamento:
-- 1. CarteiraPrincipal: qtd total
-- 2. FaturamentoProduto: qtd faturada
-- 3. EntregaMonitorada: entregue = True
```
