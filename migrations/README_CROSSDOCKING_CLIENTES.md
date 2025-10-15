# Atualização de CrossDocking em Clientes

## 📋 Objetivo

Atualizar o campo `crossdocking` na tabela `cliente_moto` conforme regras de negócio, opcionalmente consultando a Receita Federal para atualizar dados cadastrais dos clientes.

## 🎯 Regra de Negócio

Marcar **`crossdocking=True`** para clientes que atendam **TODAS** as condições abaixo:

1. ✅ **NÃO** seja do vendedor **"DANI"**
2. ✅ **NÃO** seja do estado de **São Paulo (SP)**
3. ✅ **NÃO** seja o CNPJ **62.009.696/0001-74**

Todos os outros clientes terão `crossdocking=False`.

---

## 📂 Arquivos Disponíveis

### 1. `atualizar_crossdocking_clientes.py` (RECOMENDADO)
**Script Python completo que:**
- ✅ Consulta a API da Receita Federal (ReceitaWS) para atualizar dados dos clientes
- ✅ Atualiza endereço, telefone, email, etc.
- ✅ Aplica a regra de CrossDocking
- ✅ Gera relatório detalhado
- ⚠️ **Requer conexão com internet** (consulta API externa)
- ⏱️ **Demora mais tempo** (~20 segundos por cliente devido ao limite da API)

### 2. `atualizar_crossdocking_clientes.sql`
**Script SQL simples que:**
- ✅ Executa direto no banco de dados
- ✅ Rápido (atualiza em segundos)
- ✅ Pode ser executado no Shell do Render
- ❌ **NÃO** consulta a Receita Federal
- ❌ **NÃO** atualiza dados cadastrais
- ✅ Apenas aplica a regra de CrossDocking nos dados existentes

---

## 🚀 Como Executar

### Opção 1: Script Python (RECOMENDADO para primeira execução)

#### Ambiente Local:

```bash
# Ativar ambiente virtual
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Executar script
python migrations/atualizar_crossdocking_clientes.py
```

#### No Render:

```bash
# Conectar via SSH ou usar o Shell do Render
python migrations/atualizar_crossdocking_clientes.py
```

**Tempo estimado:**
- 10 clientes = ~3 minutos
- 50 clientes = ~17 minutos
- 100 clientes = ~33 minutos

---

### Opção 2: Script SQL (MAIS RÁPIDO, sem consulta Receita)

#### No Shell do Render:

```sql
-- 1. PASSO 1: Ver estado atual
SELECT COUNT(*) AS total_clientes_ativos
FROM cliente_moto
WHERE ativo = TRUE;

-- 2. PASSO 2: Simular (copiar queries do arquivo .sql)
-- Ver quem será marcado como TRUE/FALSE

-- 3. PASSO 3: EXECUTAR ATUALIZAÇÃO
-- Copiar os UPDATEs do arquivo .sql

-- 4. PASSO 4: Verificar resultado
SELECT crossdocking, COUNT(*) AS quantidade
FROM cliente_moto
WHERE ativo = TRUE
GROUP BY crossdocking;
```

**Tempo estimado:** Menos de 1 minuto

---

## 📊 Exemplo de Saída

### Script Python:

```
================================================================================
SCRIPT: Atualizar CrossDocking em Clientes
================================================================================

1. Buscando vendedor DANI...
   ✅ Vendedor DANI encontrado: ID=5, Nome=DANI

2. Buscando clientes ativos...
   ✅ 45 clientes encontrados

3. Processando clientes...
--------------------------------------------------------------------------------

[1/45] Cliente: LOJA ABC LTDA
   CNPJ: 12345678000190
   Vendedor: JOÃO
   Estado: RJ
   Consultando API ReceitaWS: 12345678000190... ✅ OK
   📝 Dados da Receita Federal atualizados
   ✅ MARCADO como CrossDocking=True
   📊 Status alterado: False → True
   ⏳ Aguardando 20 segundos (limite da API)...

[2/45] Cliente: EMPRESA XYZ SA
   CNPJ: 98765432000111
   Vendedor: DANI
   Estado: SP
   Consultando API ReceitaWS: 98765432000111... ✅ OK
   📝 Dados da Receita Federal atualizados
   ❌ É do vendedor DANI - NÃO marcar crossdocking
   ℹ️  Mantido como CrossDocking=False
   ...

================================================================================
RELATÓRIO FINAL
================================================================================
Total de clientes processados:        45
Total com status alterado:            23
Total marcado como CrossDocking:      30
Consultas à Receita Federal:          45
Consultas bem-sucedidas:              43
================================================================================
✅ Script finalizado!
================================================================================
```

---

## ⚠️ Avisos Importantes

### API ReceitaWS (Script Python)

- **Limite:** ~3 requisições por minuto
- **Gratuita:** Não requer certificado digital
- **Delay automático:** O script já aguarda 20 segundos entre requisições
- **Timeout:** 15 segundos por consulta
- **Erros comuns:**
  - `Timeout`: API demorou muito (tenta novamente)
  - `Status 429`: Muitas requisições (aguarde e tente novamente)
  - `CNPJ não encontrado`: CNPJ inválido ou inexistente

### Antes de Executar

1. ✅ **FAÇA BACKUP DO BANCO** (especialmente no Render)
2. ✅ Execute primeiro as **consultas de simulação** (PASSO 2 do SQL)
3. ✅ Verifique se o vendedor "DANI" existe no banco
4. ✅ Confirme que o CNPJ exceção está correto: `62.009.696/0001-74`

### Rollback (caso necessário)

Se precisar reverter as alterações:

```sql
-- Reverter TODOS os clientes para crossdocking=False
UPDATE cliente_moto
SET crossdocking = FALSE,
    atualizado_em = NOW(),
    atualizado_por = 'Rollback CrossDocking'
WHERE ativo = TRUE;
```

---

## 🔍 Validação

### Verificar resultado após execução:

```sql
-- Total por status de crossdocking
SELECT
    crossdocking,
    COUNT(*) AS quantidade
FROM cliente_moto
WHERE ativo = TRUE
GROUP BY crossdocking;

-- Clientes por estado e crossdocking
SELECT
    estado_cliente,
    COUNT(*) AS total_clientes,
    SUM(CASE WHEN crossdocking THEN 1 ELSE 0 END) AS com_crossdocking,
    SUM(CASE WHEN NOT crossdocking THEN 1 ELSE 0 END) AS sem_crossdocking
FROM cliente_moto
WHERE ativo = TRUE
GROUP BY estado_cliente
ORDER BY total_clientes DESC;

-- Verificar exceções (DANI, SP, CNPJ específico)
SELECT
    c.cnpj_cliente,
    c.cliente,
    c.estado_cliente,
    v.vendedor,
    c.crossdocking,
    CASE
        WHEN v.vendedor ILIKE '%DANI%' THEN 'Vendedor DANI'
        WHEN c.estado_cliente = 'SP' THEN 'São Paulo'
        WHEN REPLACE(REPLACE(REPLACE(c.cnpj_cliente, '.', ''), '/', ''), '-', '') = '62009696000174' THEN 'CNPJ Exceção'
        ELSE 'Normal'
    END AS categoria
FROM cliente_moto c
LEFT JOIN vendedor_moto v ON c.vendedor_id = v.id
WHERE c.ativo = TRUE
ORDER BY categoria, c.cliente;
```

---

## 📞 Suporte

Caso encontre problemas:

1. Verifique se o ambiente Python está configurado corretamente
2. Confirme a conexão com o banco de dados
3. Teste primeiro em ambiente local antes de executar no Render
4. Em caso de erro na API ReceitaWS, use o script SQL (não consulta API)

---

## 📝 Changelog

- **14/10/2025**: Criação inicial dos scripts
  - Script Python com consulta à Receita Federal
  - Script SQL para atualização rápida
  - Documentação completa
