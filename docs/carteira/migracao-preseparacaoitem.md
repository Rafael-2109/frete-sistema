<!-- doc:meta
tipo: explanation
camada: L3
sot_de: Mapeamento e estrategia de migracao de PreSeparacaoItem para Separacao com status='PREVISAO' via adapter
hub: docs/INDEX.md
superseded_by: —
atualizado: 2026-06-15
-->
# Mapeamento Completo de PreSeparacaoItem

> **Papel:** Fonte-de-verdade do mapeamento de usos de PreSeparacaoItem e da estrategia de substituicao por Separacao com status='PREVISAO'.

## Contexto

Este documento mapeia onde PreSeparacaoItem e usado no codigo e descreve a estrategia de migracao em fases (manter ambos -> migrar gradualmente -> remover) por meio de um adapter que faz PreSeparacaoItem operar sobre Separacao. O mapeamento original e de 2025-01-29; contagens e numeros de linha foram reconciliados com o codigo em 2026-06-15.

## Indice

- [Resumo](#resumo)
- [Estrategia de Migracao](#estrategia-de-migracao)
- [Backend - Arquivos Python](#backend---arquivos-python)
- [Frontend - HTML](#frontend---html)
- [Frontend - JavaScript](#frontend---javascript)
- [Principais Operacoes a Substituir](#principais-operacoes-a-substituir)
- [Pontos de Atencao](#pontos-de-atencao)
- [Ordem Sugerida de Migracao](#ordem-sugerida-de-migracao)
- [Scripts Necessarios](#scripts-necessarios)
- [Checklist de Migracao](#checklist-de-migracao)

## Resumo

- **49 ocorrencias em arquivos Python** usando PreSeparacaoItem (grep atual em 2026-06-15, incluindo adapter e novas referencias; o numero real diverge do mapeamento de 2025-01-29 que apontava 33 arquivos)
- **3 arquivos HTML** com referencias
- **6 arquivos JavaScript** com logica relacionada

## Estrategia de Migracao

### Fase 1: Manter ambos funcionando
1. PreSeparacaoItem continua existindo
2. Criar adapter que sincroniza com Separacao (status='PREVISAO')
3. Testar funcionalidades

### Fase 2: Migrar gradualmente
1. Substituir queries uma por uma
2. Testar cada substituicao
3. Manter log de mudancas

### Fase 3: Remover PreSeparacaoItem
1. Remover modelo
2. Remover tabela do banco
3. Limpar codigo residual

---

## Backend - Arquivos Python

### 1. MODELS
- `app/carteira/models.py` - Define o modelo PreSeparacaoItem (linhas 441-526); a ativacao do adapter PreSeparacaoItem -> Separacao esta nas linhas 640-656
- `app/estoque/models.py` - Possivel referencia em relacionamentos

### 2. ROUTES PRINCIPAIS
- `app/carteira/routes/pre_separacao_api.py` - API principal de pre-separacao
- `app/carteira/routes/separacao_api.py` - Usa PreSeparacaoItem para criar separacoes
- `app/carteira/routes/workspace_api.py` - Workspace de montagem de lotes
- `app/carteira/routes/agendamento_api.py` - Agendamento usa pre-separacoes
- `app/carteira/routes/agendamento_confirmacao_api.py` - Confirmacao de agendamento
- `app/carteira/routes/relatorios_api.py` - Relatorios que incluem pre-separacoes
- `app/carteira/routes/ruptura_api.py` - Analise de ruptura
- `app/carteira/main_routes.py` - Rotas principais da carteira

### 3. SERVICES
- `app/carteira/services/agrupamento_service.py` - Servico de agrupamento
- `app/carteira/services/atualizar_dados_service.py` - Atualizacao de dados
- `app/odoo/services/carteira_service.py` - Integracao com Odoo
- `app/odoo/services/ajuste_sincronizacao_service.py` - Ajustes de sincronizacao
- `app/manufatura/services/demanda_service.py` - Calculo de demanda
- `app/manufatura/services/ordem_producao_service.py` - Ordens de producao

### 4. PORTAL
- `app/portal/routes.py` - Portal pode usar pre-separacoes

### 5. TRIGGERS E MIGRATIONS
- `app/estoque/triggers_sql_corrigido.py` - Triggers SQL
- `app/estoque/triggers_recalculo_otimizado.py` - Recalculo otimizado
- `migrations/versions/fix_pre_sep_system.py` - Migration especifica
- `migrations/versions/ensure_separacao_lote_id.py` - Garante lote_id
- `migrations/versions/2b5f3637c189_fix_dependent_objects_cascade.py`

### 6. INTEGRACAO MCP
- `app/carteira/routes/mcp_integration.py` - Integracao MCP
- `services/portfolio/mcp_portfolio_service.py` - Servico portfolio
- `integration/portfolio_bridge.py` - Bridge de integracao

### 7. MONITORING
- `app/carteira/monitoring.py` - Monitoramento

---

## Frontend - HTML

### 1. `app/templates/carteira/agrupados_balanceado.html`
- Template principal da carteira agrupada
- Usa pre-separacoes no workspace

### 2. `app/templates/carteira/listar_agrupados.html`
- Lista de agrupamentos (versao antiga)

### 3. `app/templates/carteira/partials/_separacoes_pedido.html`
- Partial para exibir separacoes de um pedido

---

## Frontend - JavaScript

### 1. `app/templates/carteira/js/pre-separacao-manager.js`
- **ARQUIVO PRINCIPAL** - Gerencia toda logica de pre-separacao
- Funcoes: salvar, carregar, limpar pre-separacoes

### 2. `app/templates/carteira/js/workspace-montagem.js`
- Workspace de montagem de lotes
- Drag & drop de itens
- Criacao de pre-separacoes

### 3. `app/templates/carteira/js/separacao-manager.js`
- Gerencia separacoes (conversao de pre para definitiva)

### 4. `app/templates/carteira/js/lote-manager.js`
- Gerenciamento de lotes
- Usa pre-separacoes para criar lotes

### 5. `app/templates/carteira/js/carteira-agrupada.js`
- Logica principal da carteira agrupada
- Integra com pre-separacoes

### 6. `app/templates/carteira/interface_enhancements.js`
- Melhorias de interface
- Pode ter referencias a pre-separacoes

---

## Principais Operacoes a Substituir

### 1. Criar Pre-Separacao
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

### 2. Buscar Pre-Separacoes
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

### 3. Converter para Separacao Definitiva
```python
# ANTES
# Criar Separacao a partir de PreSeparacaoItem
# Marcar PreSeparacaoItem como recomposto=True

# DEPOIS
# Apenas atualizar status de PREVISAO para ABERTO
UPDATE separacao SET status='ABERTO' WHERE separacao_lote_id=? AND status='PREVISAO'
```

### 4. APIs a Atualizar

#### `/api/pre-separacao/salvar`
- Criar Separacao com status='PREVISAO'

#### `/api/pre-separacao/carregar`
- Buscar Separacao com status='PREVISAO'

#### `/api/pre-separacao/limpar`
- Deletar Separacao com status='PREVISAO'

#### `/api/separacao/gerar`
- Atualizar status de PREVISAO para ABERTO

---

## Pontos de Atencao

1. **Campo `recomposto`** - Nao existe em Separacao, usar status='PREVISAO'/'ABERTO'. O comentario inline em `app/carteira/models.py:485-491` (bloco ATENCAO) classifica `recomposto` como "Campo praticamente INUTIL": e um ciclo decorativo que detecta mudancas via hash mas apenas gera logs — NAO reaplica divisoes nem modifica a carteira.
2. **Campo `qtd_selecionada_usuario`** - Mapear para `qtd_saldo`
3. **Campo `observacoes_usuario`** - Mapear para `observ_ped_1`
4. **Workspace** - JavaScript precisa ser adaptado para novo modelo
5. **Odoo sync** - Verificar se recomposicao ainda e necessaria

---

## Ordem Sugerida de Migracao

1. **Criar adapter** em `app/carteira/models.py` que faz PreSeparacaoItem funcionar como proxy para Separacao
2. **Atualizar APIs** uma por uma, testando cada uma
3. **Atualizar frontend** para usar novo modelo
4. **Remover PreSeparacaoItem** apos tudo testado

---

## Scripts Necessarios

1. **migrar_pre_separacao_para_separacao.py** - Migrar dados existentes
2. **adapter_pre_separacao.py** - Adapter temporario
3. **atualizar_apis_pre_separacao.py** - Atualizar todas as APIs
4. **limpar_pre_separacao.py** - Limpeza final

---

## Checklist de Migracao

### Backend
- [ ] Criar campo status='PREVISAO' em Separacao
- [ ] Criar adapter PreSeparacaoItem -> Separacao
- [ ] Migrar API `/api/pre-separacao/salvar`
- [ ] Migrar API `/api/pre-separacao/carregar`
- [ ] Migrar API `/api/pre-separacao/limpar`
- [ ] Migrar API `/api/separacao/gerar`
- [ ] Atualizar servicos de agrupamento
- [ ] Atualizar integracao Odoo
- [ ] Atualizar triggers de estoque

### Frontend
- [ ] Atualizar pre-separacao-manager.js
- [ ] Atualizar workspace-montagem.js
- [ ] Atualizar separacao-manager.js
- [ ] Atualizar lote-manager.js
- [ ] Testar drag & drop
- [ ] Testar criacao de lotes
- [ ] Testar agendamento

### Banco de Dados
- [ ] Migrar dados de pre_separacao_item
- [ ] Verificar integridade
- [ ] Criar backup
- [ ] Remover tabela antiga

---

**NOTA**: Este e um mapeamento inicial. Cada arquivo precisa ser analisado em detalhe antes da substituicao.

**NOTA DE RECONCILIACAO (2026-06-15)**: O schema `.claude/skills/consultando-sql/schemas/tables/pre_separacao_items.json` NAO existe na pasta `schemas/tables/`; apenas `separacao.json` esta presente para o modelo alvo da migracao.
