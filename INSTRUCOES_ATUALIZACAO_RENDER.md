# 📋 Instruções para Atualizar o Banco de Dados no Render

## 🎯 O que este script faz:

### ✅ ADICIONA (Seguro):
- Colunas faltantes nas tabelas existentes
- Índices para melhorar performance
- Tabelas de cache para otimização
- Inicialização do cache com dados existentes

### ❌ NÃO FAZ (Garantido):
- NÃO apaga dados
- NÃO remove tabelas
- NÃO altera dados existentes (exceto limpeza de valores inválidos)
- NÃO modifica estruturas críticas

## 🚀 Como executar no Render:

### Opção 1: Copiar e Colar no Shell (MAIS SIMPLES)

1. **Acesse o Shell do Render:**
   - Entre no painel do Render
   - Clique no seu serviço
   - Clique em "Shell"

2. **Crie o arquivo Python:**
```bash
# Criar o arquivo
cat > atualizar_banco.py << 'ENDOFFILE'
# Cole aqui o conteúdo do arquivo atualizar_banco_render.py
ENDOFFILE
```

3. **Execute o script:**
```bash
# Instalar psycopg2 se necessário
pip install psycopg2-binary

# Executar o script
python atualizar_banco.py
```

### Opção 2: Upload via Git (MAIS PROFISSIONAL)

1. **Faça commit do arquivo:**
```bash
git add atualizar_banco_render.py
git commit -m "Add: script de atualização do banco"
git push
```

2. **No Shell do Render, execute:**
```bash
# Atualizar o código
git pull

# Executar
python atualizar_banco_render.py
```

### Opção 3: Executar Direto do Shell (MAIS RÁPIDO)

1. **No Shell do Render, baixe e execute:**
```bash
# Baixar o script (se você colocar em um Gist ou repo)
curl -o atualizar_banco.py https://seu-link-aqui/atualizar_banco_render.py

# Ou criar direto
python -c "
import os
import psycopg2
# ... código do script aqui ...
"
```

## 📊 O que será atualizado:

### Tabela `separacao`:
- ➕ Coluna `separacao_lote_id` (VARCHAR 50)
- ➕ Coluna `tipo_envio` (VARCHAR 10, default 'total')
- 🔍 Índices para performance

### Tabela `pre_separacao_itens`:
- ➕ Coluna `tipo_envio` (VARCHAR 10, default 'total')
- 🔍 Índice em `carteira_principal_id`

### Tabela `carteira_principal`:
- ➕ Coluna `qtd_pre_separacoes` (INTEGER, default 0)
- ➕ Coluna `qtd_separacoes` (INTEGER, default 0)
- 🔍 Índices em `num_pedido` e `cod_produto`

### Tabelas de Cache (criadas se não existirem):
- ➕ `saldo_estoque_cache` - Cache de saldos
- ➕ `projecao_estoque_cache` - Projeções de estoque
- ➕ `cache_update_log` - Log de atualizações

## 🛡️ Recursos de Segurança:

1. **Transação Automática:**
   - Se algo der errado, faz ROLLBACK automático
   - Nenhuma mudança é aplicada se houver erro

2. **Verificações Antes de Alterar:**
   - Verifica se coluna já existe antes de adicionar
   - Verifica se índice já existe antes de criar
   - Não duplica estruturas

3. **Log Detalhado:**
   - Mostra cada ação executada
   - Salva log em arquivo
   - Exibe estatísticas antes e depois

## 📝 Exemplo de Execução:

```
╔════════════════════════════════════════════╗
║   ATUALIZADOR DE BANCO DE DADOS - RENDER  ║
╠════════════════════════════════════════════╣
║  Este script irá:                          ║
║  • Adicionar colunas necessárias          ║
║  • Criar índices para performance         ║
║  • Limpar dados inválidos                 ║
║  • NÃO apagará nenhum dado importante     ║
╚════════════════════════════════════════════╝

❓ Deseja continuar com a atualização? (s/n): s

🔌 Conectando ao banco de dados...
✅ Conectado com sucesso!

📋 Atualizando tabela SEPARACAO...
✅ Coluna separacao_lote_id adicionada
✅ Coluna tipo_envio adicionada

📋 Atualizando tabela PRE_SEPARACAO_ITENS...
⚠️ Coluna tipo_envio já existe

📋 Atualizando tabela CARTEIRA_PRINCIPAL...
✅ Coluna qtd_pre_separacoes adicionada
✅ Coluna qtd_separacoes adicionada

🔍 Criando índices para melhor performance...
✅ Índice idx_separacao_lote_id criado

💾 Verificando/criando tabelas de cache...
✅ Cache inicializado com 1234 produtos

📊 Estatísticas das tabelas:
   - carteira_principal: 45678
   - separacao: 12345
   - pre_separacao_itens: 6789
   - saldo_estoque_cache: 1234

✅ ATUALIZAÇÃO CONCLUÍDA COM SUCESSO!
```

## ⚠️ Possíveis Problemas e Soluções:

### Erro: "psycopg2 not found"
```bash
pip install psycopg2-binary
```

### Erro: "DATABASE_URL not found"
```bash
# Verificar se a variável existe
echo $DATABASE_URL

# Se não existir, o Render deve configurar automaticamente
```

### Erro de Permissão
```bash
# Executar como usuário do serviço
python atualizar_banco_render.py
```

## 🔍 Verificação Pós-Execução:

```bash
# Verificar se as colunas foram criadas
psql $DATABASE_URL -c "
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'separacao' 
AND column_name IN ('separacao_lote_id', 'tipo_envio');
"

# Verificar contagem de registros
psql $DATABASE_URL -c "
SELECT 'carteira' as tabela, COUNT(*) FROM carteira_principal
UNION ALL
SELECT 'separacao', COUNT(*) FROM separacao
UNION ALL  
SELECT 'cache', COUNT(*) FROM saldo_estoque_cache;
"
```

## 📞 Suporte:

Se houver algum problema:
1. O script faz ROLLBACK automático (dados seguros)
2. Verifique o arquivo `database_update.log`
3. O banco permanece inalterado se houver erro

## ✅ Checklist Final:

- [ ] Backup baixado e salvo
- [ ] Script revisado
- [ ] Shell do Render acessado
- [ ] Script executado
- [ ] Verificação pós-execução feita
- [ ] Sistema testado

---

**LEMBRE-SE:** Este script é 100% seguro e não apaga dados. Usa transações para garantir integridade.