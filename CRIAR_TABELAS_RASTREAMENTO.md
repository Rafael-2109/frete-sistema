# 🚀 CRIAÇÃO DAS TABELAS DE RASTREAMENTO GPS

**Escolha o método de acordo com seu ambiente:**

---

## 📋 MÉTODO 1: RENDER.COM (Produção) - SQL Manual

### **Passo 1: Acessar Shell do PostgreSQL**

1. Acesse [dashboard.render.com](https://dashboard.render.com)
2. Selecione seu banco de dados PostgreSQL
3. Clique em **"Connect"** → **"PSQL Command"**
4. Cole o comando PSQL no terminal

### **Passo 2: Executar SQL**

**Abra o arquivo:** [`migrations/rastreamento_gps_manual.sql`](migrations/rastreamento_gps_manual.sql)

**Copie TODO o conteúdo** e cole no shell do PSQL do Render.

```sql
-- O arquivo contém:
-- - CREATE TABLE rastreamento_embarques
-- - CREATE TABLE pings_gps
-- - CREATE TABLE logs_rastreamento
-- - CREATE TABLE configuracao_rastreamento
-- - CREATE INDEX (todos os índices)
-- - INSERT configuração padrão
```

### **Passo 3: Verificar**

No shell do PSQL, execute:

```sql
-- Listar tabelas
\dt rastreamento*

-- Verificar estrutura
\d rastreamento_embarques

-- Contar registros
SELECT COUNT(*) FROM rastreamento_embarques;
SELECT COUNT(*) FROM pings_gps;
SELECT * FROM configuracao_rastreamento;
```

**Resultado esperado:**
- ✅ 4 tabelas criadas
- ✅ Índices criados
- ✅ 1 registro em `configuracao_rastreamento`

---

## 🐍 MÉTODO 2: LOCAL (Desenvolvimento) - Script Python

### **Passo 1: Executar Script**

```bash
cd /home/rafaelnascimento/projetos/frete_sistema

# Ativar ambiente virtual
source venv/bin/activate

# Executar script
python criar_tabelas_rastreamento.py
```

### **O que o script faz:**

1. ✅ Cria contexto Flask
2. ✅ Conecta ao banco de dados local
3. ✅ Executa SQL para criar 4 tabelas
4. ✅ Cria índices automaticamente
5. ✅ Insere configuração padrão
6. ✅ Verifica se tudo foi criado
7. ✅ Mostra contagem de registros
8. ✅ Oferece criar rastreamento de teste (opcional)

### **Saída esperada:**

```
================================================================================
🚚 CRIAÇÃO DAS TABELAS DE RASTREAMENTO GPS
================================================================================

📦 Criando contexto Flask...
✅ Contexto Flask criado
🔗 Conectado ao banco: postgresql://...

🔨 Executando SQL para criar tabelas...

  ✅ Tabela criada: rastreamento_embarques
  ✅ Índice criado: idx_rastreamento_embarques_embarque_id
  ✅ Índice criado: idx_rastreamento_embarques_token
  ✅ Tabela criada: pings_gps
  ✅ Índice criado: idx_pings_gps_rastreamento_id
  ✅ Tabela criada: logs_rastreamento
  ✅ Índice criado: idx_logs_rastreamento_rastreamento_id
  ✅ Tabela criada: configuracao_rastreamento
  ✅ Configuração padrão inserida

================================================================================
✅ TABELAS CRIADAS COM SUCESSO!
================================================================================

🔍 VERIFICANDO TABELAS CRIADAS:

  ✅ rastreamento_embarques: 13 colunas
     └─ 4 índices criados
  ✅ pings_gps: 12 colunas
     └─ 2 índices criados
  ✅ logs_rastreamento: 4 colunas
     └─ 3 índices criados
  ✅ configuracao_rastreamento: 11 colunas

📊 CONTAGEM DE REGISTROS:

  📋 rastreamento_embarques: 0 registro(s)
  📋 pings_gps: 0 registro(s)
  📋 logs_rastreamento: 0 registro(s)
  📋 configuracao_rastreamento: 1 registro(s)

⚙️  CONFIGURAÇÃO PADRÃO:

  Intervalo de ping: 120s (2 minutos)
  Distância de chegada: 200.0m
  Retenção LGPD: 90 dias
  Versão termo LGPD: 1.0

================================================================================
🧪 TESTE OPCIONAL: Criar rastreamento de teste?
================================================================================

Digite 'S' para criar um rastreamento de teste:
```

---

## ✅ VERIFICAÇÃO PÓS-CRIAÇÃO

Execute no PostgreSQL (ambos os métodos):

```sql
-- Ver todas as tabelas de rastreamento
SELECT table_name
FROM information_schema.tables
WHERE table_name LIKE 'rastreamento%'
   OR table_name IN ('pings_gps', 'logs_rastreamento', 'configuracao_rastreamento')
ORDER BY table_name;

-- Ver configuração
SELECT
    intervalo_ping_segundos,
    distancia_chegada_metros,
    dias_retencao_dados,
    versao_termo_lgpd
FROM configuracao_rastreamento;
```

**Resultado esperado:**

| table_name |
|------------|
| configuracao_rastreamento |
| logs_rastreamento |
| pings_gps |
| rastreamento_embarques |

---

## 🔧 TROUBLESHOOTING

### **Erro: "relation embarques does not exist"**

**Causa**: Tabela `embarques` não existe no banco

**Solução**: Remover a constraint de foreign key no SQL:

```sql
-- Comentar esta linha:
-- CONSTRAINT fk_rastreamento_embarque FOREIGN KEY (embarque_id)
--     REFERENCES embarques(id) ON DELETE CASCADE
```

### **Erro: "permission denied"**

**Causa**: Usuário sem permissão para criar tabelas

**Solução**: Usar usuário admin do banco de dados

### **Tabelas já existem**

**Causa**: Script já foi executado antes

**Solução**: Normal! O script usa `CREATE TABLE IF NOT EXISTS`

Para recriar do zero:

```sql
-- CUIDADO: Isso apaga todos os dados!
DROP TABLE IF EXISTS logs_rastreamento CASCADE;
DROP TABLE IF EXISTS pings_gps CASCADE;
DROP TABLE IF EXISTS rastreamento_embarques CASCADE;
DROP TABLE IF EXISTS configuracao_rastreamento CASCADE;

-- Depois execute o script novamente
```

---

## 📁 ARQUIVOS

| Arquivo | Uso | Descrição |
|---------|-----|-----------|
| [`migrations/rastreamento_gps_manual.sql`](migrations/rastreamento_gps_manual.sql) | Render | SQL puro para copiar/colar |
| [`criar_tabelas_rastreamento.py`](criar_tabelas_rastreamento.py) | Local | Script Python automático |
| Este arquivo | Ambos | Instruções de uso |

---

## 🎯 PRÓXIMOS PASSOS

Após criar as tabelas:

1. ✅ **Reiniciar aplicação**
   ```bash
   flask run
   # ou em produção:
   sudo systemctl restart gunicorn
   ```

2. ✅ **Criar embarque de teste**
   - Acesse a interface web
   - Crie um novo embarque
   - Verifique se rastreamento foi criado automaticamente

3. ✅ **Imprimir embarque**
   - Imprima o embarque
   - Verifique se QR Code aparece na última página

4. ✅ **Testar com celular**
   - Escaneie o QR Code
   - Aceite termo LGPD
   - Verifique rastreamento GPS

5. ✅ **Verificar dashboard**
   - Acesse `/rastreamento/dashboard`
   - Veja rastreamentos ativos no mapa

---

## 📞 SUPORTE

Em caso de problemas:

1. Verifique logs: `tail -f /var/log/gunicorn/error.log`
2. Teste conexão: `psql -d frete_sistema`
3. Consulte documentação: [`INSTALACAO_RASTREAMENTO_GPS.md`](INSTALACAO_RASTREAMENTO_GPS.md)

---

**Desenvolvido com precisão! 🎯**
