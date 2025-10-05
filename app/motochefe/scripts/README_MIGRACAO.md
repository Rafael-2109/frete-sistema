# 🔧 Migração: Adicionar campo `modelo_rejeitado`

## 📋 Objetivo

Adicionar a coluna `modelo_rejeitado` na tabela `moto` para suportar o salvamento de motos rejeitadas por falta de modelo durante a importação.

---

## 🚀 Opção 1: Script Python (Recomendado para Local/Dev)

### Executar:

```bash
cd /home/rafaelnascimento/projetos/frete_sistema
python3 -m app.motochefe.scripts.adicionar_campo_modelo_rejeitado
```

### O que o script faz:

1. ✅ Verifica se a coluna já existe
2. ✅ Adiciona coluna `modelo_rejeitado VARCHAR(100) NULL`
3. ✅ Cria índice para performance
4. ✅ Mostra mensagens de sucesso/erro

### Saída esperada:

```
📝 Adicionando coluna 'modelo_rejeitado'...
✅ Coluna 'modelo_rejeitado' adicionada com sucesso!
📝 Criando índice para busca rápida...
✅ Índice criado com sucesso!
```

---

## 🌐 Opção 2: SQL Manual (Para Render/Production)

### Passos:

1. Acessar o painel do Render
2. Ir em **Database** → Sua base PostgreSQL
3. Clicar em **Connect** → **Psql**
4. Copiar e colar o conteúdo do arquivo `ADICIONAR_CAMPO_RENDER.sql`

### Ou via linha de comando:

```bash
# Conectar via psql
psql -h <HOST> -U <USER> -d <DATABASE> -f app/motochefe/scripts/ADICIONAR_CAMPO_RENDER.sql
```

---

## 📊 Validação Pós-Migração

### Verificar se a coluna foi criada:

**SQL:**
```sql
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'moto'
AND column_name = 'modelo_rejeitado';
```

**Resultado esperado:**
```
 column_name      | data_type         | is_nullable
------------------+-------------------+-------------
 modelo_rejeitado | character varying | YES
```

### Verificar índices:

**SQL:**
```sql
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'moto'
AND indexname LIKE '%modelo_rejeitado%';
```

**Resultado esperado:**
```
             indexname              |                    indexdef
------------------------------------+------------------------------------------------
 idx_moto_modelo_rejeitado          | CREATE INDEX idx_moto_modelo_rejeitado...
 idx_moto_ativo_modelo_rejeitado    | CREATE INDEX idx_moto_ativo_modelo_rejeitado...
```

---

## ⚠️ Troubleshooting

### Erro: "column already exists"

A coluna já foi adicionada. Pode prosseguir normalmente.

### Erro: "permission denied"

Seu usuário não tem permissão para alterar a tabela. Verifique as credenciais.

### Erro: "relation 'moto' does not exist"

A tabela `moto` não existe. Verifique se está conectado ao banco correto.

---

## 🔄 Rollback (Desfazer)

**⚠️ CUIDADO: Isso vai APAGAR a coluna e todos os dados nela!**

```sql
DROP INDEX IF EXISTS idx_moto_modelo_rejeitado;
DROP INDEX IF EXISTS idx_moto_ativo_modelo_rejeitado;
ALTER TABLE moto DROP COLUMN modelo_rejeitado;
```

---

## 📝 Detalhes Técnicos

| Item | Valor |
|------|-------|
| **Coluna** | `modelo_rejeitado` |
| **Tipo** | `VARCHAR(100)` |
| **Nullable** | `TRUE` |
| **Uso** | Armazena nome do modelo não encontrado quando `ativo=False` |
| **Índices** | 2 (um simples, um composto com `ativo`) |

---

## ✅ Checklist de Migração

- [ ] Executar script Python (local) OU SQL (Render)
- [ ] Validar que coluna foi criada
- [ ] Validar que índices foram criados
- [ ] Testar importação de motos com modelo inexistente
- [ ] Verificar que motos são salvas como `ativo=False`
- [ ] Cadastrar modelo e verificar ativação automática

---

**Data da Migração**: 2025-10-05
**Versão do Sistema**: MotoChefe v1.0
