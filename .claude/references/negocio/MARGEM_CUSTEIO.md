# Margem e Custeio

Documentacao da composicao de margem bruta e tabelas de custeio.

---

## Formula da Margem Bruta

```
Margem Bruta = Preco Venda
             - CustoConsiderado (custo do produto)
             - CustoFrete (% frete sobre venda, por incoterm e UF)
             - RegraComissao (comissao do vendedor)
             - ParametroCusteio('CUSTO_OPERACAO') (custo operacional fixo %)
             - ICMS
             - PIS
             - COFINS
```

### Campo pre-calculado
`CarteiraPrincipal.margem_bruta` contem a margem ja calculada para cada linha de pedido.

---

## Tabelas de Custeio

### CustoConsiderado (tabela `custo_considerado`)
- Custo unitario do produto usado para calculo de margem
- `cod_produto` - Codigo do produto
- `tipo_produto` - PA (acabado), MP (materia-prima), etc.
- `custo_atual` = True para versao vigente
- `tipo_custo_selecionado` - Qual custo usar: MEDIO_MES, ULTIMO_CUSTO, BOM
- `custo_considerado` - Valor efetivamente usado na margem
- Outros custos disponiveis: `custo_medio_mes`, `ultimo_custo`, `custo_medio_estoque`, `custo_bom`

### CustoFrete (tabela `custo_frete`)
- Percentual de frete sobre valor de venda
- `incoterm` - CIF (vendedor paga frete) ou FOB (comprador paga)
- `cod_uf` - UF de destino
- `percentual_frete` - % aplicado sobre valor venda

### CustoMensal (tabela `custo_mensal`)
- Historico mensal de custos por produto
- `ano`, `mes`, `cod_produto`
- `custo_liquido_medio`, `custo_medio_estoque`, `ultimo_custo`, `custo_bom`
- **NOTA**: Tabela com 0 rows em producao (06/02/2026). Dependente de populacao.

### ParametroCusteio (tabela `parametro_custeio`)
- Parametros globais de custeio
- `chave` (unica) - Ex: 'CUSTO_OPERACAO', 'ICMS_SP', etc.
- `valor` - Valor numerico do parametro
- `descricao` - Explicacao do parametro

---

## Consultas Uteis

### Margem de um pedido
```sql
SELECT num_pedido, cod_produto, nome_produto,
       preco_produto_pedido, margem_bruta,
       (margem_bruta / NULLIF(preco_produto_pedido, 0) * 100) as margem_pct
FROM carteira_principal
WHERE num_pedido = 'VCD123'
```

### Custo atual de um produto
```sql
SELECT cod_produto, nome_produto, tipo_custo_selecionado,
       custo_considerado, custo_medio_mes, ultimo_custo
FROM custo_considerado
WHERE cod_produto = 'PA001' AND custo_atual = True
```

### Percentual de frete por UF
```sql
SELECT cod_uf, incoterm, percentual_frete
FROM custo_frete
WHERE vigencia_fim IS NULL OR vigencia_fim >= CURRENT_DATE
ORDER BY cod_uf, incoterm
```
