# Exemplos Práticos de Importação Manual

## 📋 Cenários Comuns

### Cenário 1: Cliente Ligou Reclamando que Pedido Não Aparece no Sistema

**Situação**: Cliente fez pedido VSC25001 há 2 horas, mas não aparece na carteira.

**Solução**:
```bash
# 1. Importar o pedido específico
python scripts/importar_pedido_nf_especifico.py --pedido VSC25001

# 2. Verificar o resultado
# O script mostrará quantas linhas foram importadas/atualizadas
```

**Resultado Esperado**:
```
✅ PEDIDO IMPORTADO COM SUCESSO!
📋 Pedido: VSC25001
📊 Total de linhas: 3
🆕 Novos: 3
🔄 Atualizados: 0
```

---

### Cenário 2: NF Emitida Mas Não Gerou Movimentação de Estoque

**Situação**: NF 45678 foi emitida no Odoo, mas não aparece no estoque.

**Solução**:
```bash
# 1. Importar a NF específica
python scripts/importar_pedido_nf_especifico.py --nf 45678

# 2. O script irá:
#    - Buscar NF no Odoo
#    - Criar movimentações de estoque
#    - Atualizar embarques
#    - Marcar separações como faturadas
```

**Resultado Esperado**:
```
✅ NF IMPORTADA COM SUCESSO!
📄 NF: 45678
✅ Processadas: 1
📦 Movimentações criadas: 2
🚚 EmbarqueItems atualizados: 1
```

---

### Cenário 3: Importação em Lote de Pedidos Pendentes

**Situação**: Após manutenção do sistema, precisa importar vários pedidos.

**Solução**:
```bash
# Importar múltiplos pedidos de uma vez
python scripts/importar_pedido_nf_especifico.py --pedido VSC25001 VSC25002 VSC25003 VSC25004

# Ou criar um arquivo com os pedidos e iterar
cat pedidos.txt | while read pedido; do
    python scripts/importar_pedido_nf_especifico.py --pedido $pedido
    sleep 2  # Aguardar 2 segundos entre cada importação
done
```

**Arquivo pedidos.txt**:
```
VSC25001
VSC25002
VSC25003
VSC25004
```

---

### Cenário 4: Verificar Detalhes da Importação (Debug)

**Situação**: Precisa ver EXATAMENTE o que está acontecendo na importação.

**Solução**:
```bash
# Usar modo verbose
python scripts/importar_pedido_nf_especifico.py --pedido VSC25001 --verbose

# Redirecionar logs para arquivo
python scripts/importar_pedido_nf_especifico.py --pedido VSC25001 --verbose > importacao_VSC25001.log 2>&1
```

**O que o verbose mostra**:
- Queries executadas no Odoo
- Queries executadas no PostgreSQL
- Cálculos de saldo
- Atualizações de quantidade
- Detalhes de cada etapa

---

### Cenário 5: Importar NFs de um Dia Específico

**Situação**: Todas as NFs do dia 10/01/2025 não foram processadas.

**Solução**:
```bash
# 1. No PostgreSQL, buscar NFs do dia
psql -d seu_banco -c "
SELECT numero_nf
FROM relatorio_faturamento_importado
WHERE data_fatura = '2025-01-10'
AND ativo = true
ORDER BY numero_nf;
" -t -A > nfs_dia_10.txt

# 2. Importar todas
cat nfs_dia_10.txt | while read nf; do
    python scripts/importar_pedido_nf_especifico.py --nf $nf
    echo "NF $nf processada, aguardando 3 segundos..."
    sleep 3
done
```

---

### Cenário 6: Pedido Foi Cancelado no Odoo Mas Ainda Aparece Aqui

**Situação**: Pedido VSC24999 foi cancelado, mas ainda aparece na carteira.

**Solução**:
```bash
# O script detecta cancelamentos automaticamente
python scripts/importar_pedido_nf_especifico.py --pedido VSC24999

# Se o pedido está cancelado no Odoo, será removido da carteira
```

**Resultado Esperado**:
```
✅ PEDIDO IMPORTADO COM SUCESSO!
📋 Pedido: VSC24999
❌ Cancelados: 5
(Todas as linhas foram canceladas)
```

---

### Cenário 7: Erro Durante Importação - Como Investigar

**Situação**: Script retornou erro ao importar.

**Solução**:
```bash
# 1. Rodar com verbose para ver detalhes
python scripts/importar_pedido_nf_especifico.py --pedido VSC25001 --verbose 2>&1 | tee erro.log

# 2. Analisar o arquivo erro.log
grep "ERROR" erro.log
grep "ERRO" erro.log

# 3. Verificar no Odoo se pedido existe
# 4. Verificar conectividade: variáveis de ambiente
```

**Erros Comuns**:

| Erro | Causa | Solução |
|------|-------|---------|
| "Pedido não encontrado no Odoo" | Número incorreto ou pedido não existe | Verificar número no Odoo |
| "Connection refused" | Odoo indisponível | Verificar ODOO_URL e conectividade |
| "Authentication failed" | Credenciais incorretas | Verificar ODOO_USERNAME e ODOO_PASSWORD |
| "Database error" | Problema no PostgreSQL | Verificar DATABASE_URL |

---

### Cenário 8: Importar e Verificar Estoque Imediatamente

**Situação**: Após importar, precisa confirmar que estoque foi atualizado.

**Solução**:
```bash
# 1. Importar NF
python scripts/importar_pedido_nf_especifico.py --nf 45678

# 2. Verificar movimentações criadas (PostgreSQL)
psql -d seu_banco -c "
SELECT
    cod_produto,
    tipo_movimentacao,
    qtd_movimentacao,
    data_movimentacao,
    numero_nf
FROM movimentacao_estoque
WHERE numero_nf = '45678'
ORDER BY data_movimentacao DESC;
"

# 3. Verificar saldo atualizado
psql -d seu_banco -c "
SELECT
    cod_produto,
    nome_produto,
    saldo_estoque
FROM estoque_produtos
WHERE cod_produto IN (
    SELECT DISTINCT cod_produto
    FROM movimentacao_estoque
    WHERE numero_nf = '45678'
);
"
```

---

## 🔧 Scripts Auxiliares Úteis

### Listar Pedidos Pendentes no Odoo Mas Não no Sistema
```sql
-- Execute no PostgreSQL
-- (Requer acesso ao Odoo para comparação manual)

SELECT DISTINCT num_pedido
FROM carteira_principal
WHERE num_pedido LIKE 'VSC%'
AND data_pedido >= '2025-01-01'
ORDER BY num_pedido;
```

### Verificar NFs Sem Movimentação
```sql
-- NFs importadas mas sem movimentação de estoque
SELECT
    r.numero_nf,
    r.data_fatura,
    r.nome_cliente,
    COUNT(DISTINCT m.id) as total_movimentacoes
FROM relatorio_faturamento_importado r
LEFT JOIN movimentacao_estoque m ON r.numero_nf = m.numero_nf
WHERE r.ativo = true
AND r.data_fatura >= '2025-01-01'
GROUP BY r.numero_nf, r.data_fatura, r.nome_cliente
HAVING COUNT(DISTINCT m.id) = 0
ORDER BY r.data_fatura DESC;
```

---

## 📞 Quando Usar Este Script

✅ **USE quando**:
- Cliente reclama que pedido não aparece
- NF emitida mas sem movimentação
- Após manutenção/migração de dados
- Correção de sincronização pontual
- Importação histórica específica

❌ **NÃO USE quando**:
- Sincronização automática está funcionando
- Necessita importar TODOS os pedidos (use sincronização completa)
- Dados estão corretos (evite reprocessamento desnecessário)

---

## 🆘 Suporte

Se encontrar problemas:
1. Verifique os logs com `--verbose`
2. Confirme dados no Odoo
3. Verifique conectividade (Odoo e PostgreSQL)
4. Consulte README_IMPORTACAO_MANUAL.md para troubleshooting
