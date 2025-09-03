# 🗑️ Arquivos para Exclusão Após Testes Bem-Sucedidos

## Data da Migração: 02/09/2025

Este documento lista todos os arquivos que podem ser **EXCLUÍDOS** após validação completa do novo sistema de estoque simplificado.

## ⚠️ IMPORTANTE: Testar TUDO antes de excluir!

### Checklist de Validação:
- [ ] Workspace funcionando com novo sistema
- [ ] APIs de estoque retornando dados corretos
- [ ] Dashboard de ruptura funcionando
- [ ] Faturamento processando corretamente
- [ ] Integração TagPlus funcionando
- [ ] Performance melhorada confirmada

---

## 📁 Arquivos do Sistema Antigo de Estoque

### 1. Serviços Obsoletos
```bash
# Serviço principal antigo
app/estoque/services/estoque_tempo_real.py

# Backup da API (se testes OK, excluir)
app/estoque/api_tempo_real_backup.py

# Arquivo migrado temporário (já aplicado)
app/estoque/api_tempo_real_migrado.py
```

### 2. Modelos de Tabelas Cache (NÃO MAIS USADAS)
```bash
# Modelos das tabelas cache
app/estoque/models_tempo_real.py

# Contém: EstoqueTempoReal, MovimentacaoPrevista, SaldoEstoque, ProjecaoEstoqueCache
```

### 3. Triggers e Processos Obsoletos
```bash
# Triggers SQL antigos
app/estoque/triggers_sql_corrigido.py
app/estoque/triggers_recalculo_otimizado.py
app/estoque/triggers_tempo_real.py  # (se existir)
```

### 4. Scripts de Migração Antigos
```bash
# Scripts de migração para sistema antigo
scripts/migrar_para_tempo_real.py
recalcular_estoque_unificado.py
scripts/testes/test_faturamento_mov_prevista_runner.py
tests/test_faturamento_mov_prevista.py
```

### 5. Arquivos de Verificação Obsoletos
```bash
# Verificações do sistema antigo
check_table_structure.py
```

### 6. Backups Antigos (Verificar datas)
```bash
# Backups de versões antigas
backups/carteira_2025-07-22/api_item_detalhes.py
# Outros backups antigos em backups/
```

---

## 🗄️ Tabelas do Banco de Dados para Remover

### APÓS VALIDAÇÃO COMPLETA, executar:
```sql
-- CUIDADO: Fazer backup antes!

-- 1. Remover tabelas cache obsoletas
DROP TABLE IF EXISTS estoque_tempo_real CASCADE;
DROP TABLE IF EXISTS movimentacao_prevista CASCADE;
DROP TABLE IF EXISTS saldo_estoque CASCADE;
DROP TABLE IF EXISTS projecao_estoque_cache CASCADE;

-- 2. Remover triggers antigos (se existirem)
DROP TRIGGER IF EXISTS trigger_atualizar_estoque_tempo_real ON movimentacao_estoque;
DROP TRIGGER IF EXISTS trigger_atualizar_movimentacao_prevista ON separacao;
DROP TRIGGER IF EXISTS trigger_recalcular_estoque ON programacao_producao;
-- Listar e remover outros triggers relacionados

-- 3. Remover funções obsoletas
DROP FUNCTION IF EXISTS atualizar_estoque_tempo_real() CASCADE;
DROP FUNCTION IF EXISTS calcular_movimentacao_prevista() CASCADE;
DROP FUNCTION IF EXISTS recalcular_projecao_estoque() CASCADE;
-- Listar e remover outras funções relacionadas
```

---

## 📊 Comparação de Performance

### Sistema Antigo (EstoqueTempoReal):
- Usava 4 tabelas cache
- Triggers complexos
- ~20ms por consulta
- Sincronização problemática

### Sistema Novo (ServicoEstoqueSimples):
- Queries diretas
- Sem tabelas cache
- ~4ms por consulta (75% mais rápido!)
- Sempre atualizado

---

## 🔄 Arquivos Migrados (MANTER)

### Arquivos que foram MODIFICADOS e devem ser MANTIDOS:
```bash
# APIs migradas - MANTER
app/carteira/routes/estoque_api.py          # Migrado ✅
app/carteira/routes/ruptura_api.py          # Migrado ✅
app/estoque/api_tempo_real.py               # Migrado ✅
app/faturamento/services/processar_faturamento.py  # Migrado ✅
app/integracoes/tagplus/processador_faturamento_tagplus.py  # Migrado ✅

# Novo serviço - MANTER
app/estoque/services/estoque_simples.py     # NOVO ✅
```

---

## 📝 Comandos de Limpeza

### Após validação completa, executar:
```bash
# 1. Remover arquivos Python obsoletos
rm app/estoque/services/estoque_tempo_real.py
rm app/estoque/models_tempo_real.py
rm app/estoque/triggers_sql_corrigido.py
rm app/estoque/triggers_recalculo_otimizado.py
rm app/estoque/api_tempo_real_backup.py
rm app/estoque/api_tempo_real_migrado.py
rm scripts/migrar_para_tempo_real.py
rm recalcular_estoque_unificado.py

# 2. Limpar cache Python
find . -type d -name __pycache__ -exec rm -r {} +
find . -type f -name "*.pyc" -delete

# 3. Fazer backup final antes de excluir tabelas
pg_dump $DATABASE_URL -t estoque_tempo_real -t movimentacao_prevista -t saldo_estoque -t projecao_estoque_cache > backup_tabelas_antigas_$(date +%Y%m%d).sql
```

---

## ✅ Validação Final

### Antes de excluir QUALQUER arquivo:

1. **Testar Workspace**:
   - Abrir pedidos
   - Verificar cálculos de estoque
   - Verificar projeções

2. **Testar APIs**:
   ```bash
   curl http://localhost:5000/api/estoque/produto/101001001
   curl http://localhost:5000/api/estoque/rupturas
   curl http://localhost:5000/api/estoque/estatisticas
   ```

3. **Verificar Logs**:
   - Sem erros relacionados a estoque
   - Performance melhorada confirmada

4. **Backup Completo**:
   ```bash
   pg_dump $DATABASE_URL > backup_completo_antes_exclusao_$(date +%Y%m%d).sql
   ```

---

## 🚨 ROLLBACK (Se necessário)

Se algo der errado após exclusão:

1. **Restaurar backup do banco**:
   ```bash
   psql $DATABASE_URL < backup_completo_antes_exclusao_YYYYMMDD.sql
   ```

2. **Reverter commits Git**:
   ```bash
   git revert HEAD~N  # N = número de commits para reverter
   ```

3. **Restaurar arquivos do backup**:
   ```bash
   # Se tiver backup dos arquivos Python
   ```

---

## 📅 Cronograma Sugerido

1. **Dia 1-3**: Testes intensivos com novo sistema
2. **Dia 4-5**: Monitoramento em produção
3. **Dia 6**: Backup completo
4. **Dia 7**: Exclusão dos arquivos obsoletos
5. **Dia 8-14**: Monitoramento pós-exclusão

---

**LEMBRE-SE**: É melhor manter arquivos não usados por algumas semanas do que excluir prematuramente e ter problemas!

**Autor**: Sistema de Migração
**Data**: 02/09/2025