# 📋 Aumentar Tamanho do Campo numero_chassi

**Data**: 06/10/2025
**Alteração**: VARCHAR(17) → VARCHAR(30)
**Motivo**: Suportar variações de VIN com caracteres extras ou prefixos

---

## 🎯 Resumo da Mudança

### Antes:
```sql
numero_chassi VARCHAR(17)  -- Padrão VIN internacional
```

### Depois:
```sql
numero_chassi VARCHAR(30)  -- Suporta variações e prefixos
```

**Exemplos que agora funcionam:**
- ✅ `:R36CP3000NA010742` (19 caracteres)
- ✅ `9BD123456789ABC01` (17 caracteres - padrão)
- ✅ Qualquer chassi com até 30 caracteres

---

## 📁 Arquivos Modificados

### 1. **Modelo Python** (✅ Já alterado)
```python
# app/motochefe/models/produto.py
numero_chassi = db.Column(db.String(30), primary_key=True)
```

### 2. **Validação de Importação** (✅ Já alterado)
```python
# app/motochefe/routes/produtos.py
if len(chassi) > 30:
    erros.append(f'Chassi muito longo (máximo 30).')
```

### 3. **Scripts de Migração** (🆕 Criados)
- `AUMENTAR_TAMANHO_CHASSI_RENDER.sql` - Para Render (PostgreSQL)
- `aumentar_chassi_local.py` - Para banco local

---

## 🚀 Como Executar

### 📍 BANCO LOCAL (PostgreSQL/SQLite)

#### Opção 1: Script Python Automatizado (Recomendado)
```bash
cd /home/rafaelnascimento/projetos/frete_sistema
python app/motochefe/scripts/aumentar_chassi_local.py
```

**O script irá:**
1. ✅ Verificar estado atual da coluna
2. ✅ Mostrar dados existentes
3. ✅ Pedir confirmação
4. ✅ Executar ALTER TABLE
5. ✅ Verificar se alteração foi aplicada

#### Opção 2: SQL Direto (PostgreSQL)
```sql
ALTER TABLE moto ALTER COLUMN numero_chassi TYPE VARCHAR(30);
```

#### Opção 3: SQLite
- ✅ Nenhuma ação necessária (SQLite não valida tamanho de VARCHAR)
- Apenas atualize o modelo Python (já feito)

---

### 📍 RENDER (PostgreSQL)

#### 1. Acessar o Render Dashboard
- Acesse: https://dashboard.render.com
- Entre no seu banco de dados PostgreSQL

#### 2. Abrir SQL Shell
- Clique no banco → **Connect** → Copie comando de conexão
- Ou use a interface Web SQL do Render

#### 3. Executar SQL
```sql
-- Abra o arquivo: AUMENTAR_TAMANHO_CHASSI_RENDER.sql
-- Execute seção por seção (recomendado) ou tudo de uma vez

-- Principal:
ALTER TABLE moto ALTER COLUMN numero_chassi TYPE VARCHAR(30);
```

#### 4. Verificar Resultado
```sql
SELECT column_name, character_maximum_length
FROM information_schema.columns
WHERE table_name = 'moto' AND column_name = 'numero_chassi';

-- Deve retornar: 30
```

---

## ⚠️ IMPORTANTE

### ✅ Operação é SEGURA porque:
- NÃO perde dados existentes
- NÃO causa downtime
- NÃO quebra Primary Key
- NÃO afeta índices
- É reversível (se não houver chassi > 17 chars)

### 🔴 Cuidados:
- ✅ Faça backup antes (recomendado)
- ✅ Execute em horário de baixo uso (opcional)
- ✅ Verifique resultado após executar

---

## 🧪 Testes Após Migração

### 1. Verificar estrutura:
```sql
SELECT column_name, data_type, character_maximum_length
FROM information_schema.columns
WHERE table_name = 'moto' AND column_name = 'numero_chassi';
```

**Esperado:**
```
column_name   | data_type | character_maximum_length
numero_chassi | varchar   | 30
```

### 2. Testar importação:
- Importe planilha com chassi de 19+ caracteres
- Deve aceitar até 30 caracteres
- Deve rejeitar > 30 caracteres com mensagem clara

### 3. Verificar dados existentes:
```sql
SELECT COUNT(*) FROM moto;  -- Deve retornar total correto
```

---

## 🔄 Rollback (Se Necessário)

**⚠️ APENAS SE HOUVER PROBLEMA!**

### PostgreSQL:
```sql
-- Falha se existir chassi > 17 caracteres
ALTER TABLE moto ALTER COLUMN numero_chassi TYPE VARCHAR(17);
```

### Reverter código Python:
```python
# Voltar para:
numero_chassi = db.Column(db.String(17), primary_key=True)
```

---

## 📊 Checklist de Execução

### Banco Local:
- [ ] Backup do banco (opcional, mas recomendado)
- [ ] Executar `aumentar_chassi_local.py`
- [ ] Verificar resultado (script faz automaticamente)
- [ ] Testar importação com chassi longo

### Render:
- [ ] Acessar Render Dashboard
- [ ] Abrir SQL Shell
- [ ] Executar `AUMENTAR_TAMANHO_CHASSI_RENDER.sql` (seção 3)
- [ ] Verificar resultado (seção 4 do SQL)
- [ ] Reiniciar aplicação (se necessário)

### Código:
- [x] Modelo Python atualizado ✅
- [x] Validação de importação atualizada ✅
- [x] Scripts de migração criados ✅

---

## 📞 Suporte

Em caso de dúvida ou problema:
1. Verifique logs do banco de dados
2. Execute queries de verificação do script SQL
3. Confirme que modelo Python está com `String(30)`

---

**Criado em**: 06/10/2025
**Versão**: 1.0
