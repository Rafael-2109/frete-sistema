# 🚀 INSTALAÇÃO DA TABELA entregas_rastreadas

## 📋 ARQUIVOS CRIADOS:

1. **`criar_tabela_entregas_rastreadas.py`** - Script Python para ambiente local
2. **`criar_tabela_entregas_rastreadas.sql`** - Script SQL para Render (produção)
3. **`verificar_entregas_rastreadas.sql`** - Script para verificar se tudo está OK
4. **`IMPLEMENTACAO_ENTREGA_RASTREADA_COMPLETA.md`** - Documentação completa

---

## 🖥️ INSTALAÇÃO LOCAL (Desenvolvimento)

### Opção 1: Usando script Python (Recomendado)

```bash
# 1. Ativar ambiente virtual
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# 2. Executar script
python criar_tabela_entregas_rastreadas.py
```

**Output esperado:**
```
================================================================================
🎯 CRIAÇÃO DA TABELA entregas_rastreadas
================================================================================

📋 Criando tabela entregas_rastreadas...
✅ Tabela entregas_rastreadas criada com sucesso!

📋 Criando índices...
✅ Índices criados com sucesso!

================================================================================
✅ SUCESSO! Tabela entregas_rastreadas está disponível no banco
================================================================================
```

### Opção 2: Usando psql direto

```bash
# 1. Conectar ao banco local
psql -U postgres -d frete_sistema

# 2. Executar script SQL
\i criar_tabela_entregas_rastreadas.sql

# 3. Verificar
\i verificar_entregas_rastreadas.sql
```

---

## ☁️ INSTALAÇÃO NO RENDER (Produção)

### Passo 1: Acessar Shell do PostgreSQL

1. Entre no dashboard do Render: https://dashboard.render.com
2. Vá em **Services** → Seu banco de dados PostgreSQL
3. Clique em **Shell** (no menu lateral)
4. Aguarde conectar

### Passo 2: Executar Script SQL

1. Abra o arquivo `criar_tabela_entregas_rastreadas.sql`
2. **COPIE TODO O CONTEÚDO** (Ctrl+A, Ctrl+C)
3. **COLE NO SHELL** do Render (Ctrl+V)
4. Pressione **ENTER**

**Output esperado:**
```
BEGIN
CREATE TABLE
CREATE INDEX
CREATE INDEX
CREATE INDEX
CREATE INDEX
COMMENT
COMMENT
...
COMMIT
```

### Passo 3: Verificar Instalação

1. Ainda no Shell do Render, copie o conteúdo de `verificar_entregas_rastreadas.sql`
2. Cole e execute
3. Verifique se mostra: `✅ Tabela entregas_rastreadas EXISTE`

---

## ✅ VERIFICAÇÃO PÓS-INSTALAÇÃO

### 1. Verificar tabela criada:

```sql
SELECT COUNT(*) FROM entregas_rastreadas;
```

**Esperado:** `0` (tabela vazia, mas existe)

### 2. Testar criação de cotação DIRETA:

1. Acesse o sistema
2. Crie uma cotação do tipo **DIRETA**
3. Adicione múltiplos pedidos/clientes
4. Feche o frete

### 3. Verificar se EntregaRastreada foi criada:

```sql
SELECT
    er.id,
    er.pedido,
    er.numero_nf,
    er.cliente,
    er.cidade,
    er.uf,
    er.status,
    CASE
        WHEN er.destino_latitude IS NOT NULL THEN 'Geocodificado ✅'
        ELSE 'Sem coordenadas ❌'
    END AS geocoding
FROM entregas_rastreadas er
ORDER BY er.criado_em DESC
LIMIT 5;
```

**Esperado:** Ver as entregas criadas automaticamente

### 4. Verificar logs do sistema:

```
[DEBUG] 🚚 Rastreamento GPS criado para embarque DIRETA #123
[DEBUG] ✅ 3 entregas rastreadas criadas para embarque #123
✅ Entrega rastreada criada: NF 12345 - Cliente A | Coords: ✅ -23.550,-46.633
```

---

## 🐛 TROUBLESHOOTING

### Erro: "relation entregas_rastreadas already exists"

**Solução:** A tabela já existe! Tudo OK. Use o script de verificação:
```bash
psql -U postgres -d frete_sistema -f verificar_entregas_rastreadas.sql
```

### Erro: "foreign key violation" ao criar rastreamento

**Causa:** Tabelas `rastreamento_embarques` ou `embarque_itens` não existem

**Solução:**
1. Verificar se tabelas de rastreamento estão criadas:
```sql
SELECT tablename FROM pg_tables WHERE tablename LIKE '%rastreamento%';
```

2. Se não existirem, executar migrations do rastreamento primeiro

### Erro: "could not serialize access due to concurrent update"

**Causa:** Múltiplas requisições criando entregas ao mesmo tempo

**Solução:** Isso é normal. O sistema tenta novamente automaticamente.

### Entregas criadas mas sem coordenadas (geocoding falhou)

**Causa:** API do Google Maps pode ter retornado erro ou endereço inválido

**Verificação:**
```sql
SELECT
    COUNT(*) AS total,
    COUNT(destino_latitude) AS geocodificadas,
    COUNT(*) - COUNT(destino_latitude) AS sem_coords
FROM entregas_rastreadas;
```

**Solução:**
- ✅ Geocoding não é crítico, sistema funciona sem
- ✅ Motorista pode selecionar manualmente mesmo sem proximidade automática
- ✅ Sistema usa mesma Google Maps API do mapa de pedidos
- ⚠️ Verificar se `GOOGLE_MAPS_API_KEY` está configurada no `.env`
- ⚠️ Verificar logs para ver erros específicos do Google Maps

---

## 📊 QUERIES ÚTEIS PARA MONITORAMENTO

### Ver estatísticas gerais:

```sql
SELECT
    COUNT(*) AS total_entregas,
    COUNT(CASE WHEN status = 'ENTREGUE' THEN 1 END) AS entregues,
    COUNT(CASE WHEN status = 'PENDENTE' THEN 1 END) AS pendentes,
    COUNT(CASE WHEN destino_latitude IS NOT NULL THEN 1 END) AS geocodificadas
FROM entregas_rastreadas;
```

### Ver entregas em andamento:

```sql
SELECT
    r.id AS rastreamento_id,
    e.numero AS embarque,
    er.pedido,
    er.cliente,
    er.status,
    er.cidade
FROM entregas_rastreadas er
JOIN rastreamento_embarques r ON r.id = er.rastreamento_id
JOIN embarques e ON e.id = r.embarque_id
WHERE er.status IN ('PENDENTE', 'EM_ROTA', 'PROXIMO')
ORDER BY er.criado_em DESC;
```

### Ver performance de entregas (distância):

```sql
SELECT
    pedido,
    cliente,
    entregue_distancia_metros AS distancia_metros,
    CASE
        WHEN entregue_distancia_metros <= 200 THEN 'Próximo ✅'
        WHEN entregue_distancia_metros <= 500 THEN 'Aceitável ⚠️'
        ELSE 'Longe ❌'
    END AS avaliacao,
    entregue_em
FROM entregas_rastreadas
WHERE status = 'ENTREGUE'
  AND entregue_distancia_metros IS NOT NULL
ORDER BY entregue_em DESC
LIMIT 20;
```

---

## 🎉 PRONTO!

Se tudo deu certo, você deve ver:

1. ✅ Tabela `entregas_rastreadas` criada
2. ✅ 4 índices criados
3. ✅ Foreign keys configuradas
4. ✅ Entregas sendo criadas automaticamente em cotações DIRETA
5. ✅ Geocodificação funcionando (maioria dos casos)

**Próximo passo:** Testar o rastreamento completo com QR Code!

---

## 📞 SUPORTE

Se encontrar problemas:

1. Verificar logs do sistema
2. Executar `verificar_entregas_rastreadas.sql`
3. Verificar se código Python foi deployado no Render
4. Conferir se variáveis de ambiente estão configuradas
