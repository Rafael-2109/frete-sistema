# 📋 RESUMO DA MIGRAÇÃO: PEDIDO → VIEW

**Data**: 2025-01-29  
**Objetivo**: Transformar tabela `pedidos` em VIEW que agrega dados de `separacao`

## ✅ ARQUIVOS CRIADOS E PRONTOS PARA EXECUÇÃO

### 1️⃣ **sql_criar_view_pedidos_final.sql**
```sql
-- VIEW com ID determinístico usando hash MD5
-- ID = ABS(('x' || substr(md5(separacao_lote_id), 1, 8))::bit(32)::int)
```
**Características**:
- ✅ ID determinístico (sempre o mesmo para o mesmo lote)
- ✅ Funciona com `Pedido.query.get(id)`
- ✅ Agrega dados por `separacao_lote_id`
- ✅ 13 RULEs para UPDATE automático
- ✅ DELETE remove de Separacao (não marca sincronizado)

### 2️⃣ **executar_migracao_final.sh**
Script bash que executa em ordem:
1. Verifica DATABASE_URL
2. Cria backup do banco
3. Adiciona campos em Separacao (sql_render_modular.sql)
4. Adiciona cotacao_id em Separacao
5. Migra dados Pedido → Separacao
6. Cria VIEW pedidos (sql_criar_view_pedidos_final.sql)
7. Atualiza modelo Python

### 3️⃣ **app/pedidos/models_adapter.py**
Modelo Python adaptado para VIEW com:
- ✅ Property `status_calculado` preservada
- ✅ Método `save()` que atualiza Separacao
- ✅ Helpers para atualizar campos específicos
- ✅ Marca como VIEW para SQLAlchemy

### 4️⃣ **app/utils/lote_utils.py**
Função padronizada para gerar lotes:
- ✅ Formato único: `LOTE_YYYYMMDD_HHMMSS_XXX`
- ✅ Verificação de unicidade
- ✅ Função `calcular_hash_lote()` para IDs

## 📊 CAMPOS ADICIONADOS EM SEPARACAO

| Campo | Tipo | Descrição |
|-------|------|-----------|
| status | VARCHAR(20) | Status do pedido (ABERTO, FATURADO, etc) |
| nf_cd | BOOLEAN | Flag NF voltou para CD |
| data_embarque | DATE | Data de embarque |
| cidade_normalizada | VARCHAR(120) | Cidade normalizada |
| uf_normalizada | VARCHAR(2) | UF normalizada |
| codigo_ibge | VARCHAR(10) | Código IBGE |
| separacao_impressa | BOOLEAN | Flag de impressão |
| separacao_impressa_em | TIMESTAMP | Data/hora impressão |
| separacao_impressa_por | VARCHAR(100) | Usuário que imprimiu |
| cotacao_id | INTEGER | ID da cotação (FK) |

## 🔄 RULES DA VIEW (UPDATE AUTOMÁTICO)

Quando atualizar em Pedido → Atualiza em Separacao:

1. ✅ status
2. ✅ nf_cd
3. ✅ data_embarque
4. ✅ agendamento, protocolo, agendamento_confirmado
5. ✅ nf → numero_nf
6. ✅ separacao_impressa, separacao_impressa_em, separacao_impressa_por
7. ✅ cidade_normalizada, uf_normalizada, codigo_ibge
8. ✅ rota, sub_rota, roteirizacao
9. ✅ expedicao
10. ✅ observ_ped_1
11. ✅ pedido_cliente
12. ✅ cotacao_id
13. ✅ data_pedido

## 🚀 COMO EXECUTAR

### Pré-requisitos:
```bash
# 1. Configurar DATABASE_URL
export DATABASE_URL="postgresql://usuario:senha@host:porta/banco"

# 2. Verificar que arquivos existem
ls -la sql_render_modular.sql
ls -la sql_criar_view_pedidos_final.sql
ls -la executar_migracao_final.sh
```

### Execução:
```bash
# Executar migração completa
./executar_migracao_final.sh
```

### Validação pós-migração:
```sql
-- Verificar VIEW criada
SELECT COUNT(*) FROM pedidos;

-- Testar ID determinístico
SELECT id, separacao_lote_id FROM pedidos LIMIT 5;

-- Testar UPDATE
UPDATE pedidos SET status = 'TESTE' WHERE id = <algum_id>;

-- Verificar se atualizou Separacao
SELECT status FROM separacao WHERE separacao_lote_id = '<lote_correspondente>';
```

## ⚠️ ROLLBACK (se necessário)

```bash
# O script cria backup automático
# Para reverter:
psql $DATABASE_URL < backup_migracao_pedido_view_YYYYMMDD_HHMMSS.sql

# Restaurar modelo Python
cp app/pedidos/models_backup_*.py app/pedidos/models.py
```

## 🎯 BENEFÍCIOS DA MIGRAÇÃO

1. **Elimina redundância** - Pedido não duplica dados de Separacao
2. **Single source of truth** - Separacao é a única fonte de dados
3. **Compatibilidade total** - Código existente continua funcionando
4. **Performance** - Menos tabelas para manter sincronizadas
5. **Simplificação** - Remove PreSeparacaoItem completamente

## 📝 NOTAS IMPORTANTES

- `separacao_lote_id` é único por pedido (confirmado)
- ID da VIEW é hash MD5 determinístico
- DELETE em pedidos deleta de Separacao (não marca sincronizado)
- INSERT em pedidos está bloqueado (criar via Separacao)
- Campos de transporte (transportadora, valor_frete) vêm NULL na VIEW

## ✅ CHECKLIST FINAL

- [x] Campos adicionados em Separacao
- [x] VIEW com ID determinístico
- [x] RULEs para todos os campos editáveis
- [x] Adapter Python com status_calculado
- [x] Script de migração completo
- [x] Função padronizada gerar_lote_id()
- [x] Backup automático no script

**STATUS: PRONTO PARA EXECUÇÃO** 🚀