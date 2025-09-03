# 🔍 VERIFICAÇÃO DE SEGURANÇA - Exclusão de Código Obsoleto de Estoque

## Data: 02/09/2025

## 🚨 RESUMO EXECUTIVO

### ❌ AINDA TEM CÓDIGO USANDO AS CLASSES OBSOLETAS!

Encontrei **vários arquivos ativos** que ainda usam as classes obsoletas. **NÃO É SEGURO** apagar ainda!

---

## 📊 ANÁLISE DETALHADA

### 1. ❌ `EstoqueTempoReal` - AINDA EM USO!

**Arquivos que AINDA USAM:**
- ✅ `app/producao/relatorios_bp.py` - **ATIVO!** Usa para relatórios
- ✅ `app/estoque/models.py` - **ATIVO!** Tem referências
- ✅ `recalcular_estoque_unificado.py` - Script de recálculo

### 2. ❌ `MovimentacaoPrevista` - AINDA EM USO!

**Arquivos que AINDA USAM:**
- ✅ `app/producao/routes.py` - **ATIVO!** Faz update/delete direto
- ✅ `app/producao/relatorios_bp.py` - **ATIVO!** Usa em queries

### 3. ❌ `SaldoEstoque` - AINDA EM USO EXTENSIVO!

**Arquivos que AINDA USAM:**
- ✅ `app/carteira/utils/workspace_utils.py` - **ATIVO!**
- ✅ `app/carteira/routes/cardex_api.py` - **ATIVO!** 
- ✅ `app/carteira/main_routes.py` - **ATIVO!**
- ✅ `app/estoque/routes.py` - **ATIVO!**
- ✅ `app/estoque/models.py` - **ATIVO!** (classe definida aqui)

### 4. ⚠️ `ProjecaoEstoqueCache` - MENOS CRÍTICO

**Arquivos que referenciam:**
- ⚠️ `app/init_db_fixes.py` - Verifica/corrige tabela
- ⚠️ `migrations/versions/criar_cache_estoque.py` - Migration
- ❌ `check_table_structure.py` - Script de verificação (pode deletar)

---

## 🔧 O QUE PRECISA SER FEITO ANTES DE APAGAR

### 1. Para remover `EstoqueTempoReal`:
```python
# app/producao/relatorios_bp.py - LINHA ~300
# TROCAR:
estoques = EstoqueTempoReal.query.order_by(EstoqueTempoReal.cod_produto).all()
# POR:
# Usar ServicoEstoqueSimples.exportar_estoque_completo() ou similar

# app/estoque/models.py
# Remover imports e referências
```

### 2. Para remover `MovimentacaoPrevista`:
```python
# app/producao/routes.py - LINHA ~200
# TROCAR:
MovimentacaoPrevista.query.update({'entrada_prevista': 0})
# POR:
# Não fazer nada - o novo sistema calcula tudo em tempo real

# app/producao/relatorios_bp.py
# Remover queries de MovimentacaoPrevista
```

### 3. Para remover `SaldoEstoque`:
```python
# CRÍTICO! Usado em MUITOS lugares
# app/carteira/utils/workspace_utils.py
# app/carteira/main_routes.py
# app/estoque/routes.py

# TODOS precisam ser migrados para usar:
from app.estoque.services.estoque_simples import ServicoEstoqueSimples

# Exemplo:
# ANTES:
producao = SaldoEstoque.calcular_producao_periodo(cod_produto, hoje, hoje)
# DEPOIS:
# Usar ServicoEstoqueSimples.calcular_entradas_previstas()
```

---

---

## 🎯 PLANO DE AÇÃO RECOMENDADO

### Fase 1 - Migrar código ativo (FAZER PRIMEIRO!)
1. [ ] Migrar `app/producao/relatorios_bp.py`
2. [ ] Migrar `app/producao/routes.py`
3. [ ] Migrar `app/carteira/utils/workspace_utils.py`
4. [ ] Migrar `app/carteira/main_routes.py`
5. [ ] Migrar `app/estoque/routes.py`
6. [ ] Atualizar `app/estoque/models.py`

### Fase 2 - Testar tudo
1. [ ] Testar relatórios de produção
2. [ ] Testar workspace
3. [ ] Testar cardex
4. [ ] Testar rotas de estoque

### Fase 3 - Limpar (SÓ DEPOIS DOS TESTES!)
1. [ ] Deletar `app/estoque/services/estoque_tempo_real.py`
2. [ ] Deletar `app/estoque/models_tempo_real.py`
3. [ ] Deletar tabelas do banco
4. [ ] Deletar scripts obsoletos

---

## ⚠️ AVISO IMPORTANTE

**NÃO DELETE NADA AINDA!** 

Precisamos primeiro:
1. Migrar os arquivos que ainda usam as classes antigas
2. Testar tudo
3. Só então fazer a limpeza

---

## 📝 CHECKLIST PARA VOCÊ VERIFICAR

Para ter certeza absoluta antes de apagar, execute:

```bash
# 1. Verificar se ainda tem imports
grep -r "from.*EstoqueTempoReal\|from.*MovimentacaoPrevista\|from.*SaldoEstoque" --include="*.py" . | grep -v "#"

# 2. Verificar uso direto
grep -r "EstoqueTempoReal\.\|MovimentacaoPrevista\.\|SaldoEstoque\." --include="*.py" . | grep -v "#"

# 3. Verificar tabelas no banco
psql $DATABASE_URL -c "\dt *estoque*"
psql $DATABASE_URL -c "\dt *movimentacao*"
psql $DATABASE_URL -c "\dt *saldo*"
psql $DATABASE_URL -c "\dt *projecao*"
```

Se TODOS retornarem vazio, então é seguro apagar!

---

**Autor**: Sistema de Verificação
**Status**: ❌ NÃO É SEGURO APAGAR AINDA