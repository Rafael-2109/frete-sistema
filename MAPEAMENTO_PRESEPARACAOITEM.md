# 📋 MAPEAMENTO COMPLETO DE PreSeparacaoItem

**Data**: 2025-01-29  
**Objetivo**: Mapear todos os usos de PreSeparacaoItem para substituir por Separacao com status='PREVISAO'

## 📊 RESUMO

- **33 arquivos Python** usando PreSeparacaoItem
- **3 arquivos HTML** com referências
- **6 arquivos JavaScript** com lógica relacionada

## 🔄 ESTRATÉGIA DE MIGRAÇÃO

### Fase 1: Manter ambos funcionando
1. PreSeparacaoItem continua existindo
2. Criar adapter que sincroniza com Separacao (status='PREVISAO')
3. Testar funcionalidades

### Fase 2: Migrar gradualmente
1. Substituir queries uma por uma
2. Testar cada substituição
3. Manter log de mudanças

### Fase 3: Remover PreSeparacaoItem
1. Remover modelo
2. Remover tabela do banco
3. Limpar código residual

---

## 📁 BACKEND - ARQUIVOS PYTHON

### 1. **MODELS**
- `app/carteira/models.py` - Define o modelo PreSeparacaoItem (linhas 619-761)
- `app/estoque/models.py` - Possível referência em relacionamentos

### 2. **ROUTES PRINCIPAIS**
- `app/carteira/routes/pre_separacao_api.py` - API principal de pré-separação
- `app/carteira/routes/separacao_api.py` - Usa PreSeparacaoItem para criar separações
- `app/carteira/routes/workspace_api.py` - Workspace de montagem de lotes
- `app/carteira/routes/agendamento_api.py` - Agendamento usa pré-separações
- `app/carteira/routes/agendamento_confirmacao_api.py` - Confirmação de agendamento
- `app/carteira/routes/relatorios_api.py` - Relatórios que incluem pré-separações
- `app/carteira/routes/ruptura_api.py` - Análise de ruptura
- `app/carteira/main_routes.py` - Rotas principais da carteira

### 3. **SERVICES**
- `app/carteira/services/agrupamento_service.py` - Serviço de agrupamento
- `app/carteira/services/atualizar_dados_service.py` - Atualização de dados
- `app/odoo/services/carteira_service.py` - Integração com Odoo
- `app/odoo/services/ajuste_sincronizacao_service.py` - Ajustes de sincronização
- `app/manufatura/services/demanda_service.py` - Cálculo de demanda
- `app/manufatura/services/ordem_producao_service.py` - Ordens de produção

### 4. **PORTAL**
- `app/portal/routes.py` - Portal pode usar pré-separações

### 5. **TRIGGERS E MIGRATIONS**
- `app/estoque/triggers_sql_corrigido.py` - Triggers SQL
- `app/estoque/triggers_recalculo_otimizado.py` - Recálculo otimizado
- `migrations/versions/fix_pre_sep_system.py` - Migration específica
- `migrations/versions/ensure_separacao_lote_id.py` - Garante lote_id
- `migrations/versions/2b5f3637c189_fix_dependent_objects_cascade.py`

### 6. **INTEGRAÇÃO MCP**
- `app/carteira/routes/mcp_integration.py` - Integração MCP
- `services/portfolio/mcp_portfolio_service.py` - Serviço portfolio
- `integration/portfolio_bridge.py` - Bridge de integração

### 7. **MONITORING**
- `app/carteira/monitoring.py` - Monitoramento

---

## 🌐 FRONTEND - HTML

### 1. **app/templates/carteira/agrupados_balanceado.html**
- Template principal da carteira agrupada
- Usa pré-separações no workspace

### 2. **app/templates/carteira/listar_agrupados.html**
- Lista de agrupamentos (versão antiga)

### 3. **app/templates/carteira/partials/_separacoes_pedido.html**
- Partial para exibir separações de um pedido

---

## 💻 FRONTEND - JAVASCRIPT

### 1. **app/templates/carteira/js/pre-separacao-manager.js**
- **ARQUIVO PRINCIPAL** - Gerencia toda lógica de pré-separação
- Funções: salvar, carregar, limpar pré-separações

### 2. **app/templates/carteira/js/workspace-montagem.js**
- Workspace de montagem de lotes
- Drag & drop de itens
- Criação de pré-separações

### 3. **app/templates/carteira/js/separacao-manager.js**
- Gerencia separações (conversão de pré para definitiva)

### 4. **app/templates/carteira/js/lote-manager.js**
- Gerenciamento de lotes
- Usa pré-separações para criar lotes

### 5. **app/templates/carteira/js/carteira-agrupada.js**
- Lógica principal da carteira agrupada
- Integra com pré-separações

### 6. **app/templates/carteira/interface_enhancements.js**
- Melhorias de interface
- Pode ter referências a pré-separações

---

## 🔑 PRINCIPAIS OPERAÇÕES A SUBSTITUIR

### 1. **Criar Pré-Separação**
```python
# ANTES
pre_sep = PreSeparacaoItem(
    separacao_lote_id=lote_id,
    status='CRIADO',
    ...
)

# DEPOIS
separacao = Separacao(
    separacao_lote_id=lote_id,
    status='PREVISAO',  # Novo status
    ...
)
```

### 2. **Buscar Pré-Separações**
```python
# ANTES
PreSeparacaoItem.query.filter_by(
    separacao_lote_id=lote_id,
    recomposto=False
)

# DEPOIS
Separacao.query.filter_by(
    separacao_lote_id=lote_id,
    status='PREVISAO'
)
```

### 3. **Converter para Separação Definitiva**
```python
# ANTES
# Criar Separacao a partir de PreSeparacaoItem
# Marcar PreSeparacaoItem como recomposto=True

# DEPOIS
# Apenas atualizar status de PREVISAO para ABERTO
UPDATE separacao SET status='ABERTO' WHERE separacao_lote_id=? AND status='PREVISAO'
```

### 4. **APIs a Atualizar**

#### `/api/pre-separacao/salvar`
- Criar Separacao com status='PREVISAO'

#### `/api/pre-separacao/carregar`
- Buscar Separacao com status='PREVISAO'

#### `/api/pre-separacao/limpar`
- Deletar Separacao com status='PREVISAO'

#### `/api/separacao/gerar`
- Atualizar status de PREVISAO para ABERTO

---

## ⚠️ PONTOS DE ATENÇÃO

1. **Campo `recomposto`** - Não existe em Separacao, usar status='PREVISAO'/'ABERTO'
2. **Campo `qtd_selecionada_usuario`** - Mapear para `qtd_saldo`
3. **Campo `observacoes_usuario`** - Mapear para `observ_ped_1`
4. **Workspace** - JavaScript precisa ser adaptado para novo modelo
5. **Odoo sync** - Verificar se recomposição ainda é necessária

---

## 📝 ORDEM SUGERIDA DE MIGRAÇÃO

1. **Criar adapter** em `app/carteira/models.py` que faz PreSeparacaoItem funcionar como proxy para Separacao
2. **Atualizar APIs** uma por uma, testando cada uma
3. **Atualizar frontend** para usar novo modelo
4. **Remover PreSeparacaoItem** após tudo testado

---

## 🔧 SCRIPTS NECESSÁRIOS

1. **migrar_pre_separacao_para_separacao.py** - Migrar dados existentes
2. **adapter_pre_separacao.py** - Adapter temporário
3. **atualizar_apis_pre_separacao.py** - Atualizar todas as APIs
4. **limpar_pre_separacao.py** - Limpeza final

---

## ✅ CHECKLIST DE MIGRAÇÃO

### Backend
- [ ] Criar campo status='PREVISAO' em Separacao
- [ ] Criar adapter PreSeparacaoItem → Separacao
- [ ] Migrar API `/api/pre-separacao/salvar`
- [ ] Migrar API `/api/pre-separacao/carregar`
- [ ] Migrar API `/api/pre-separacao/limpar`
- [ ] Migrar API `/api/separacao/gerar`
- [ ] Atualizar serviços de agrupamento
- [ ] Atualizar integração Odoo
- [ ] Atualizar triggers de estoque

### Frontend
- [ ] Atualizar pre-separacao-manager.js
- [ ] Atualizar workspace-montagem.js
- [ ] Atualizar separacao-manager.js
- [ ] Atualizar lote-manager.js
- [ ] Testar drag & drop
- [ ] Testar criação de lotes
- [ ] Testar agendamento

### Banco de Dados
- [ ] Migrar dados de pre_separacao_item
- [ ] Verificar integridade
- [ ] Criar backup
- [ ] Remover tabela antiga

---

**NOTA**: Este é um mapeamento inicial. Cada arquivo precisa ser analisado em detalhe antes da substituição.