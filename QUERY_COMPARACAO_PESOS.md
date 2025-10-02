# 📊 QUERIES DE COMPARAÇÃO DE PESOS

**Para copiar e colar no shell do PostgreSQL (Render)**

---

## 🔍 QUERY 1: Comparar Peso Unitário (Faturamento vs Cadastro)

**Copia e cola isso:**

```sql
SELECT
    fp.cod_produto,
    fp.nome_produto,
    fp.peso_unitario_produto as peso_faturamento,
    cp.peso_bruto as peso_cadastro,
    ROUND((fp.peso_unitario_produto - cp.peso_bruto)::numeric, 3) as diferenca,
    ROUND((((fp.peso_unitario_produto - cp.peso_bruto) / NULLIF(cp.peso_bruto, 0)) * 100)::numeric, 2) as dif_percentual,
    COUNT(fp.id) as qtd_nfs
FROM faturamento_produto fp
INNER JOIN cadastro_palletizacao cp ON fp.cod_produto = cp.cod_produto
WHERE fp.peso_unitario_produto != cp.peso_bruto
GROUP BY fp.cod_produto, fp.nome_produto, fp.peso_unitario_produto, cp.peso_bruto
ORDER BY ABS(fp.peso_unitario_produto - cp.peso_bruto) DESC
LIMIT 100;
```

**Resultado esperado:**

| cod_produto | nome_produto | peso_faturamento | peso_cadastro | diferenca | dif_percentual | qtd_nfs |
|-------------|--------------|------------------|---------------|-----------|----------------|---------|
| PROD123     | Produto X    | 25.500           | 25.000        | 0.500     | 2.00           | 45      |
| PROD456     | Produto Y    | 10.200           | 10.000        | 0.200     | 2.00           | 23      |

---

## 🔍 QUERY 2: Validar Cálculo de Peso Total

**Copia e cola isso:**

```sql
SELECT
    cod_produto,
    nome_produto,
    numero_nf,
    qtd_produto_faturado as qtd,
    peso_unitario_produto as peso_unit,
    peso_total as peso_registrado,
    ROUND((qtd_produto_faturado * peso_unitario_produto)::numeric, 3) as peso_calculado,
    ROUND((peso_total - (qtd_produto_faturado * peso_unitario_produto))::numeric, 3) as diferenca,
    ROUND((((peso_total - (qtd_produto_faturado * peso_unitario_produto)) / NULLIF(peso_total, 0)) * 100)::numeric, 2) as dif_percentual
FROM faturamento_produto
WHERE peso_total != (qtd_produto_faturado * peso_unitario_produto)
  AND peso_total > 0
  AND qtd_produto_faturado > 0
ORDER BY ABS(peso_total - (qtd_produto_faturado * peso_unitario_produto)) DESC
LIMIT 100;
```

**Resultado esperado:**

| cod_produto | numero_nf | qtd | peso_unit | peso_registrado | peso_calculado | diferenca | dif_percentual |
|-------------|-----------|-----|-----------|-----------------|----------------|-----------|----------------|
| PROD123     | 139906    | 10  | 25.500    | 255.000         | 255.000        | 0.000     | 0.00           |
| PROD456     | 139907    | 5   | 10.200    | 51.500          | 51.000         | 0.500     | 0.97           |

---

## 📈 QUERY 3: Resumo Estatístico (BÔNUS)

**Copia e cola isso:**

```sql
SELECT
    '1. Peso Unitário' as analise,
    COUNT(DISTINCT fp.cod_produto) as produtos_diferentes,
    ROUND(AVG(fp.peso_unitario_produto - cp.peso_bruto)::numeric, 3) as dif_media,
    ROUND(MIN(fp.peso_unitario_produto - cp.peso_bruto)::numeric, 3) as dif_minima,
    ROUND(MAX(fp.peso_unitario_produto - cp.peso_bruto)::numeric, 3) as dif_maxima
FROM faturamento_produto fp
INNER JOIN cadastro_palletizacao cp ON fp.cod_produto = cp.cod_produto
WHERE fp.peso_unitario_produto != cp.peso_bruto

UNION ALL

SELECT
    '2. Peso Total' as analise,
    COUNT(DISTINCT cod_produto),
    ROUND(AVG(peso_total - (qtd_produto_faturado * peso_unitario_produto))::numeric, 3),
    ROUND(MIN(peso_total - (qtd_produto_faturado * peso_unitario_produto))::numeric, 3),
    ROUND(MAX(peso_total - (qtd_produto_faturado * peso_unitario_produto))::numeric, 3)
FROM faturamento_produto
WHERE peso_total != (qtd_produto_faturado * peso_unitario_produto)
  AND peso_total > 0
  AND qtd_produto_faturado > 0;
```

**Resultado esperado:**

| analise           | produtos_diferentes | dif_media | dif_minima | dif_maxima |
|-------------------|---------------------|-----------|------------|------------|
| 1. Peso Unitário  | 45                  | 0.125     | -5.000     | 10.500     |
| 2. Peso Total     | 23                  | 0.050     | -2.000     | 8.000      |

---

## 🏆 QUERY 4: TOP 10 Produtos com Maior Divergência (BÔNUS)

**Copia e cola isso:**

```sql
SELECT
    fp.cod_produto,
    fp.nome_produto,
    COUNT(DISTINCT fp.numero_nf) as nfs_afetadas,
    ROUND(AVG(fp.peso_unitario_produto)::numeric, 3) as peso_medio_faturamento,
    cp.peso_bruto as peso_cadastro,
    ROUND((AVG(fp.peso_unitario_produto) - cp.peso_bruto)::numeric, 3) as diferenca,
    ROUND((((AVG(fp.peso_unitario_produto) - cp.peso_bruto) / NULLIF(cp.peso_bruto, 0)) * 100)::numeric, 2) as dif_percentual
FROM faturamento_produto fp
INNER JOIN cadastro_palletizacao cp ON fp.cod_produto = cp.cod_produto
WHERE fp.peso_unitario_produto != cp.peso_bruto
GROUP BY fp.cod_produto, fp.nome_produto, cp.peso_bruto
ORDER BY ABS(AVG(fp.peso_unitario_produto) - cp.peso_bruto) DESC
LIMIT 10;
```

---

## 🔎 QUERY 5: Verificar NF Específica (Substitua o número)

**Copia e cola isso (mude '139906' pela NF desejada):**

```sql
SELECT
    numero_nf,
    cod_produto,
    nome_produto,
    qtd_produto_faturado as qtd,
    peso_unitario_produto as peso_unit,
    peso_total as registrado,
    ROUND((qtd_produto_faturado * peso_unitario_produto)::numeric, 3) as calculado,
    ROUND((peso_total - (qtd_produto_faturado * peso_unitario_produto))::numeric, 3) as diferenca,
    CASE
        WHEN peso_total = (qtd_produto_faturado * peso_unitario_produto) THEN 'OK'
        WHEN ABS(peso_total - (qtd_produto_faturado * peso_unitario_produto)) < 0.1 THEN 'PEQUENO'
        ELSE 'ERRO'
    END as status
FROM faturamento_produto
WHERE numero_nf = '139906'
ORDER BY cod_produto;
```

---

## 📋 COMO USAR NO RENDER

### **Passo 1: Conectar ao PostgreSQL**

1. Acesse: https://dashboard.render.com
2. Selecione seu **banco PostgreSQL**
3. Clique em **"Connect"**
4. Copie o comando **PSQL Command**
5. Cole no **terminal local** (ou use Web Shell do Render)

### **Passo 2: Executar Query**

1. **Copie** uma das queries acima (Ctrl+C)
2. **Cole** no shell PSQL (Ctrl+V)
3. Pressione **Enter**
4. **Veja os resultados!**

### **Passo 3: Exportar Resultados (Opcional)**

Para salvar resultados em CSV:

```sql
\copy (QUERY_AQUI) TO '/tmp/resultados.csv' WITH CSV HEADER;
```

---

## 🧪 TESTE RÁPIDO

**Verificar se tabelas existem:**

```sql
-- Ver tabelas
\dt faturamento_produto
\dt cadastro_palletizacao

-- Contar registros
SELECT COUNT(*) FROM faturamento_produto;
SELECT COUNT(*) FROM cadastro_palletizacao;

-- Ver estrutura
\d faturamento_produto
\d cadastro_palletizacao
```

---

## 🔧 TROUBLESHOOTING

### **Erro: "relation does not exist"**

**Causa**: Tabela não existe no banco

**Solução**: Verifique nome correto:
```sql
\dt *faturamento*
\dt *palletiza*
```

### **Erro: "column does not exist"**

**Causa**: Campo tem nome diferente

**Solução**: Veja estrutura da tabela:
```sql
\d faturamento_produto
```

### **Nenhum resultado retornado**

**Causa**: Não há divergências

**Solução**: Teste sem filtro:
```sql
-- Ver todos os registros (sem filtro de diferença)
SELECT
    fp.cod_produto,
    fp.peso_unitario_produto,
    cp.peso_bruto
FROM faturamento_produto fp
INNER JOIN cadastro_palletizacao cp ON fp.cod_produto = cp.cod_produto
LIMIT 10;
```

---

## ✅ RESULTADO ESPERADO

Após executar as queries, você verá:

**QUERY 1**: Lista de produtos onde peso do faturamento ≠ peso do cadastro
**QUERY 2**: Lista de NFs onde peso_total ≠ (qtd × peso_unitário)

Se retornar **0 linhas**, significa que **não há divergências**! ✅

---

## 📊 INTERPRETAR RESULTADOS

### **Diferença Aceitável**
- < 0.1 kg: **Arredondamento** (normal)
- < 1%: **Tolerância** (aceitável)

### **Diferença Preocupante**
- \> 5%: **Verificar** cadastro
- \> 10%: **Corrigir** urgente

### **Ação Sugerida**

Se encontrar divergências:

1. **Identifique** produtos com maior diferença (QUERY 4)
2. **Verifique** cadastro de palletização
3. **Atualize** peso correto:
   ```sql
   UPDATE cadastro_palletizacao
   SET peso_bruto = 25.500
   WHERE cod_produto = 'PRODXXX';
   ```

---

**Criado com precisão! 🎯**
