# 🔧 MIGRAÇÃO DE CAMPOS - SISTEMA MOTOCHEFE

**Data**: 2025-01-04
**Status**: ✅ **PRONTO PARA EXECUTAR**

---

## 📋 RESUMO

Este documento descreve **TODOS os campos faltantes** identificados na comparação entre `create_tables.sql` e os modelos Python atuais.

---

## 🔍 CAMPOS FALTANTES IDENTIFICADOS

### 1. ✅ **transportadora_moto** - 5 CAMPOS
**Localização**: [cadastro.py:59-63](app/motochefe/models/cadastro.py#L59-63)

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `chave_pix` | VARCHAR(100) | Chave PIX para pagamento |
| `agencia` | VARCHAR(20) | Agência bancária |
| `conta` | VARCHAR(20) | Número da conta |
| `banco` | VARCHAR(100) | Nome do banco |
| `cod_banco` | VARCHAR(10) | Código do banco |

---

### 2. ✅ **empresa_venda_moto** - TABELA INTEIRA
**Localização**: [cadastro.py:108-131](app/motochefe/models/cadastro.py#L108-131)

**⚠️ TABELA NÃO EXISTE NO create_tables.sql!**

Estrutura completa:
```sql
CREATE TABLE empresa_venda_moto (
    id SERIAL PRIMARY KEY,
    cnpj_empresa VARCHAR(20) NOT NULL UNIQUE,
    empresa VARCHAR(255) NOT NULL,
    chave_pix VARCHAR(100),
    banco VARCHAR(100),
    cod_banco VARCHAR(10),
    agencia VARCHAR(20),
    conta VARCHAR(20),
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    criado_por VARCHAR(100),
    atualizado_em TIMESTAMP,
    atualizado_por VARCHAR(100)
);
```

---

### 3. ✅ **pedido_venda_moto** - 1 CAMPO
**Localização**: [vendas.py:57](app/motochefe/models/vendas.py#L57)

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `empresa_venda_id` | INTEGER FK | Empresa emissora da NF |

**⚠️ DEPENDE** de `empresa_venda_moto` ser criada primeiro!

---

### 4. ✅ **titulo_financeiro** - 1 CAMPO + 1 ALTERAÇÃO
**Localização**: [financeiro.py:29-30](app/motochefe/models/financeiro.py#L29-30)

| Mudança | Descrição |
|---------|-----------|
| **Adicionar** `prazo_dias` | INTEGER - Prazo em dias (30, 60, 90) |
| **Alterar** `data_vencimento` | Tornar NULLABLE (era NOT NULL) |

**Motivo**: `data_vencimento` é calculado no faturamento usando `data_nf + prazo_dias`

---

### 5. ✅ **embarque_moto** - 3 CAMPOS + 1 ALTERAÇÃO
**Localização**: [logistica.py:30-34](app/motochefe/models/logistica.py#L30-34)

| Mudança | Tipo | Descrição |
|---------|------|-----------|
| **Adicionar** `valor_frete_contratado` | NUMERIC(15,2) NOT NULL | Valor acordado (usado no rateio) |
| **Adicionar** `data_pagamento_frete` | DATE | Data do pagamento |
| **Adicionar** `status_pagamento_frete` | VARCHAR(20) DEFAULT 'PENDENTE' | Status: PENDENTE, PAGO, ATRASADO |
| **Alterar** `valor_frete_pago` | Tornar NULLABLE | (era NOT NULL) |

**⚠️ MIGRAÇÃO DE DADOS**: Copiar `valor_frete_pago` → `valor_frete_contratado` nos registros existentes

---

### 6. ✅ **embarque_pedido** - 1 CAMPO
**Localização**: [logistica.py:93](app/motochefe/models/logistica.py#L93)

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `enviado` | BOOLEAN NOT NULL DEFAULT FALSE | Trigger de rateio e atualização do pedido |

**⚠️ CAMPO CRÍTICO** para funcionalidade de embarques!

---

### 7. ✅ **comissao_vendedor** - 1 CAMPO
**Localização**: [financeiro.py:103](app/motochefe/models/financeiro.py#L103)

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `atualizado_por` | VARCHAR(100) | Auditoria (faltava) |

---

## 📊 ESTATÍSTICAS

| Item | Quantidade |
|------|------------|
| Tabelas a criar | 1 (empresa_venda_moto) |
| Tabelas a alterar | 5 |
| Campos a adicionar | 13 |
| Campos a tornar nullable | 2 |
| Índices a criar | 3 |

---

## 🚀 COMO EXECUTAR

### **OPÇÃO 1: RENDER (PostgreSQL Remoto)**

```bash
# 1. Acessar o dashboard do Render
# 2. Ir em Shell do PostgreSQL
# 3. Copiar e colar o conteúdo de:
cat app/motochefe/scripts/alteracoes_render.sql

# OU via psql:
psql $DATABASE_URL < app/motochefe/scripts/alteracoes_render.sql
```

---

### **OPÇÃO 2: LOCAL (Python Script)**

```bash
# Na raiz do projeto:
python app/motochefe/scripts/migrar_campos_local.py
```

**O que o script faz:**
- ✅ Verifica se cada coluna/tabela já existe
- ✅ Cria apenas o que falta (idempotente)
- ✅ Mostra progresso em tempo real
- ✅ Faz rollback em caso de erro
- ✅ Atualiza dados existentes quando necessário

---

## ⚠️ ORDEM DE EXECUÇÃO OBRIGATÓRIA

**IMPORTANTE**: A ordem importa por causa das FKs!

1. ✅ Criar `empresa_venda_moto` (referenciada por pedido)
2. ✅ Adicionar campos em `transportadora_moto`
3. ✅ Adicionar `empresa_venda_id` em `pedido_venda_moto`
4. ✅ Adicionar `prazo_dias` em `titulo_financeiro`
5. ✅ Adicionar campos de frete em `embarque_moto`
6. ✅ Adicionar `enviado` em `embarque_pedido`
7. ✅ Adicionar `atualizado_por` em `comissao_vendedor`

**Ambos os scripts seguem esta ordem automaticamente!**

---

## 🧪 TESTES APÓS MIGRAÇÃO

Execute estes comandos SQL para verificar:

```sql
-- 1. Verificar se empresa_venda_moto existe
SELECT COUNT(*) FROM empresa_venda_moto;

-- 2. Verificar colunas de transportadora_moto
SELECT column_name FROM information_schema.columns
WHERE table_name = 'transportadora_moto'
ORDER BY ordinal_position;

-- 3. Verificar FK em pedido_venda_moto
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'pedido_venda_moto' AND column_name = 'empresa_venda_id';

-- 4. Verificar prazo_dias em titulo_financeiro
SELECT column_name, is_nullable
FROM information_schema.columns
WHERE table_name = 'titulo_financeiro'
AND column_name IN ('prazo_dias', 'data_vencimento');

-- 5. Verificar campos de frete em embarque_moto
SELECT column_name FROM information_schema.columns
WHERE table_name = 'embarque_moto'
AND column_name LIKE '%frete%';

-- 6. Verificar enviado em embarque_pedido
SELECT column_name FROM information_schema.columns
WHERE table_name = 'embarque_pedido' AND column_name = 'enviado';
```

---

## 🔴 IMPACTOS NAS FUNCIONALIDADES

### **1. Vendas (CRÍTICO)**
- ❌ **Sem `empresa_venda_id`**: Faturamento não funciona
- ❌ **Sem `prazo_dias`**: Títulos não calculam vencimento

### **2. Embarques (CRÍTICO)**
- ❌ **Sem `enviado`**: Sistema de embarques não funciona
- ❌ **Sem `valor_frete_contratado`**: Rateio incorreto

### **3. Cadastros (BAIXO)**
- ⚠️ **Sem dados bancários**: Funciona, mas falta info

---

## 📝 LOGS DE EXECUÇÃO

### **Script Python** mostra:
```
============================================================
🔧 MIGRAÇÃO DE CAMPOS - SISTEMA MOTOCHEFE
============================================================
📅 Data: 04/01/2025 23:30:15
============================================================

🔍 Verificando tabela empresa_venda_moto...
   ⏳ Criando tabela empresa_venda_moto...
   ✅ Tabela empresa_venda_moto criada com sucesso!

🔍 Verificando transportadora_moto...
   ⏳ Adicionando coluna chave_pix...
   ✅ Coluna chave_pix adicionada!
   ...

============================================================
✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!
============================================================
```

---

## 🆘 TROUBLESHOOTING

### **Erro: "column already exists"**
✅ **Normal!** Script é idempotente, apenas informa que já existe.

### **Erro: "relation does not exist"**
❌ **Problema!** Verifique se as tabelas base existem:
```sql
SELECT tablename FROM pg_tables WHERE tablename LIKE '%_moto';
```

### **Erro: "violates foreign key constraint"**
❌ **Problema!** Execute na ordem correta (empresa_venda_moto PRIMEIRO).

### **Script Python não encontra app**
```bash
# Certifique-se de estar na raiz do projeto:
cd /home/rafaelnascimento/projetos/frete_sistema
python app/motochefe/scripts/migrar_campos_local.py
```

---

## 📂 ARQUIVOS RELACIONADOS

- 📄 **SQL Render**: [alteracoes_render.sql](app/motochefe/scripts/alteracoes_render.sql)
- 🐍 **Script Python**: [migrar_campos_local.py](app/motochefe/scripts/migrar_campos_local.py)
- 📋 **Create Tables Original**: [create_tables.sql](app/motochefe/scripts/create_tables.sql)
- 📖 **Models Python**: [app/motochefe/models/](app/motochefe/models/)

---

## ✅ CHECKLIST FINAL

Após executar migração:

- [ ] Tabela `empresa_venda_moto` existe
- [ ] `transportadora_moto` tem dados bancários
- [ ] `pedido_venda_moto` tem `empresa_venda_id`
- [ ] `titulo_financeiro` tem `prazo_dias`
- [ ] `embarque_moto` tem 3 campos de frete
- [ ] `embarque_pedido` tem `enviado`
- [ ] `comissao_vendedor` tem `atualizado_por`
- [ ] Reiniciar servidor Flask
- [ ] Testar faturamento de pedido
- [ ] Testar criação de embarque
- [ ] Testar marcar pedido como enviado

---

## 🎉 CONCLUSÃO

Após executar a migração:

1. ✅ Todos os models Python estarão sincronizados com o banco
2. ✅ Funcionalidades de vendas funcionarão corretamente
3. ✅ Sistema de embarques funcionará completamente
4. ✅ Auditoria estará completa

**Escolha a opção que preferir (SQL direto ou Python script) e execute!**

---

**Última atualização**: 04/01/2025
**Versão**: 1.0.0
