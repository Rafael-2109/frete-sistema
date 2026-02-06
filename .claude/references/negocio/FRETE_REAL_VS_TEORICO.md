# Frete Real vs Teorico

Documentacao dos 4 tipos de valor de frete e como consultar custos reais.

---

## 4 Tipos de Valor (tabela `fretes`)

| Campo | Significado | Quando Populado |
|-------|-------------|-----------------|
| `valor_cotado` | Calculado pela tabela de frete (teorico) | Ao criar o frete (automatico) |
| `valor_cte` | Cobrado pela transportadora no CTe | Ao receber/importar CTe |
| `valor_considerado` | Validado internamente (pode ser cotado ou ajustado) | Apos conferencia interna |
| `valor_pago` | Efetivamente pago a transportadora | Apos pagamento/fatura |

### Regra de uso
- **Para custo real**: usar `valor_pago` (campo definitivo)
- **Para estimativa**: usar `valor_cotado` (tabela de preco)
- **Para divergencia**: comparar `valor_cte` vs `valor_cotado`

---

## Divergencia CTe vs Cotacao

### Campos do modelo Frete
```python
# Metodo: diferenca_cotado_cte()
# Retorna: valor_cte - valor_cotado (positivo = transportadora cobra mais)

# Metodo: requer_aprovacao_por_valor()
# Retorna: (bool, list[str]) com motivos
```

### Query de divergencias
```sql
SELECT f.id, f.numero_cte, t.razao_social,
       f.valor_cotado, f.valor_cte,
       ABS(f.valor_cte - f.valor_cotado) as diferenca
FROM fretes f
JOIN transportadoras t ON t.id = f.transportadora_id
WHERE f.valor_cte IS NOT NULL
  AND ABS(f.valor_cte - f.valor_cotado) > 5.00  -- tolerancia
ORDER BY diferenca DESC
```

---

## Despesas Extras (tabela `despesas_extras`)

### Tipos de despesa (`tipo_despesa`)
```
REENTREGA          - Tentativa de entrega que falhou
TDE                - Taxa de dificuldade de entrega
PERNOITE           - Pernoite do motorista
DEVOLUCAO          - Frete de devolucao
DIARIA             - Diaria de veiculo parado
COMPLEMENTO DE FRETE - Ajuste de valor
COMPRA/AVARIA      - Avaria ou compra emergencial
TRANSFERENCIA      - Frete de transferencia
DESCARGA           - Taxa de descarga
ESTACIONAMENTO     - Estacionamento em destino
CARRO DEDICADO     - Veiculo exclusivo
ARMAZENAGEM        - Armazenagem em destino
```

### Campos-chave
- `valor_despesa` - Valor da despesa
- `frete_id` - FK para Frete (obrigatorio)
- `nfd_id` - FK para NFDevolucao (quando tipo_despesa='DEVOLUCAO')
- `transportadora_id` - Override de transportadora (quando diferente do frete original)
- `setor_responsavel` - Quem paga: LOGISTICA, COMERCIAL, QUALIDADE
- `motivo_despesa` - Razao da despesa
- `status` - PENDENTE, APROVADO, LANCADO

### Custo REAL total de um frete
```sql
SELECT f.valor_pago + COALESCE(SUM(de.valor_despesa), 0) as custo_total
FROM fretes f
LEFT JOIN despesas_extras de ON de.frete_id = f.id
WHERE f.id = [frete_id]
GROUP BY f.id, f.valor_pago
```

---

## Conta Corrente com Transportadoras (tabela `conta_corrente_transportadoras`)

### Logica
- `tipo_movimentacao`: CREDITO, DEBITO, COMPENSACAO
- `valor_credito` / `valor_debito` - Valores individuais
- `status`: ATIVO, COMPENSADO, DESCONSIDERADO
- Cada registro vincula a um `frete_id`

### Saldo por transportadora
```sql
SELECT t.razao_social,
       SUM(cc.valor_credito) as total_credito,
       SUM(cc.valor_debito) as total_debito,
       SUM(cc.valor_credito) - SUM(cc.valor_debito) as saldo
FROM conta_corrente_transportadoras cc
JOIN transportadoras t ON t.id = cc.transportadora_id
WHERE cc.status = 'ATIVO'
GROUP BY t.razao_social
```

---

## Fretes Pendentes de Lancamento no Odoo

```sql
SELECT f.id, f.numero_cte, f.valor_pago, t.razao_social
FROM fretes f
JOIN transportadoras t ON t.id = f.transportadora_id
WHERE f.status = 'APROVADO'
  AND f.lancado_odoo_em IS NULL
ORDER BY f.criado_em
```

### Campos de integracao Odoo
- `lancado_odoo_em` (DateTime) - Quando foi lancado
- `odoo_dfe_id` (Integer) - ID do DFe no Odoo
- `odoo_purchase_order_id` (Integer) - ID do PO no Odoo
- `odoo_invoice_id` (Integer) - ID da invoice no Odoo

---

## Custo de Frete por Pedido (chain completa)

```sql
-- Via embarque chain:
SELECT f.*
FROM fretes f
JOIN embarques e ON e.id = f.embarque_id
JOIN embarque_itens ei ON ei.embarque_id = e.id
JOIN separacao s ON s.separacao_lote_id = ei.separacao_lote_id
WHERE s.num_pedido = 'VCD123'

-- NOTA: Um embarque pode ter multiplos pedidos.
-- O frete e rateado pelo peso de cada CNPJ.
-- Para rateio por pedido: (peso_pedido / peso_total_embarque) * valor_frete
```

## Custo de Frete por Cliente (grupo empresarial)

```sql
-- Usando prefixo CNPJ (primeiros 8 digitos = raiz do grupo):
SELECT SUM(f.valor_pago) as total_frete,
       SUM(COALESCE(de_total.valor_despesas, 0)) as total_despesas
FROM fretes f
LEFT JOIN (
    SELECT frete_id, SUM(valor_despesa) as valor_despesas
    FROM despesas_extras GROUP BY frete_id
) de_total ON de_total.frete_id = f.id
WHERE f.cnpj_cliente LIKE '12345678%'  -- prefixo do grupo
  AND f.criado_em >= '2026-01-01'
```
