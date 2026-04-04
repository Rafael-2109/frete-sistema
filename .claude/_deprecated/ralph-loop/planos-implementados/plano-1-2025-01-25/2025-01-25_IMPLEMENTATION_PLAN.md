# IMPLEMENTATION PLAN - Sistema de Frete

**Gerado**: 2026-01-25
**Atualizado**: 2026-01-25 (Análise Completa via 16 Subagentes)
**Objetivo**: Consolidar gaps identificados e priorizar implementações
**Baseado em**: Análise de `specs/*`, `app/*`, `CLAUDE.md`, 500+ arquivos

---

## LEGENDA DE PRIORIDADE

| Símbolo | Prioridade | Prazo Sugerido | Critério |
|---------|------------|----------------|----------|
| 🔴 | CRÍTICA | 1-2 semanas | Bloqueia funcionalidade core ou causa corrupção de dados |
| 🟠 | ALTA | 2-4 semanas | Afeta UX significativamente ou cria débito técnico grave |
| 🟡 | MÉDIA | 1-2 meses | Melhoria de qualidade ou feature secundária |
| 🟢 | BAIXA | Backlog | Nice-to-have ou polish |

---

## SUMÁRIO EXECUTIVO

| Categoria | Crítico | Alto | Médio | Baixo | Total | Concluídos |
|-----------|---------|------|-------|-------|-------|------------|
| Specs Pendentes | ~~1~~ 0 | ~~1~~ 0 | 0 | 0 | ~~2~~ 0 | ✅ 2 |
| Segurança/Credenciais | ~~2~~ 0 | ~~1~~ 0 | 0 | 0 | ~~3~~ 0 | ✅ 3 |
| Problemas Estruturais | ~~2~~ 0 | ~~2~~ 0 | 0 | 0 | ~~4~~ 0 | ✅ 5 |
| Índices DB | 0 | ~~2~~ 0 | ~~3~~ 0 | 0 | ~~5~~ 0 | ✅ 5 |
| Templates/UI/Menu | 0 | ~~1~~ 0 | ~~2~~ 0 | 1 | ~~4~~ 1 | ✅ 4 |
| Error Handling | 0 | ~~1~~ 0 | 0 | 0 | ~~1~~ 0 | ✅ 1 |
| TODOs Código | 0 | ~~6~~ 0 | ~~15~~ 13 | 11 | ~~32~~ 24 | ✅ 8 |
| Pass Statements | 0 | 0 | 1 | 0 | 1 | 0 |
| **TOTAL** | **0** | **0** | **14** | **12** | **26** | **28** |

### Progresso (2026-01-25)
- ✅ Dashboard Métricas implementado
- ✅ Memory Tool SDK integration concluído
- ✅ **Sistema de Notificações** implementado (email, webhook, in_app)
- ✅ Re-raise em event listener corrigido
- ✅ Savepoint em `aplicar_reducao_quantidade()` corrigido
- ✅ Menu links BI adicionados (4 telas agora acessíveis via UI)
- ✅ **API Key Odoo corrigida em 17 arquivos** (usar env vars)
- ✅ **SECRET_KEY fallbacks removidos** (erro em produção se não configurado)
- ✅ **JWT_SECRET_KEY corrigido** (warning + fallback dev)
- ✅ **Error handling producao/routes.py** - Savepoints por item em loops de importação
- ✅ **`obter_transportadoras_grupo()`** - Detecta grupos de transportadoras via prefixo CNPJ
- ✅ **19 índices de performance criados** - Script `scripts/criar_indices_performance.py`
- ✅ **5 métricas BI reais** - Novos métodos em `app/bi/services_helpers.py`
- ✅ **`nfs_pendentes` corrigido** - Query real em `app/faturamento/routes.py:1290-1322`
- ✅ **Cascade delete AgentSession/AgentMemory** - `app/agente/models.py:67-70,369-372`
- ✅ **`comparar_portal()` corrigido** - Usa VerificadorProtocoloAtacadao real
- ✅ **`extrair_confirmacoes()` corrigido** - Verifica portal REAL antes de confirmar
- ✅ **3 templates debug/test removidos** - 1.314 linhas de código de teste removidas
- ✅ **`_buscar_historico_alertas()` corrigido** - Query REAL em `AlertaNotificacao` (tabelas criadas)
- ✅ **Dashboard alertas CORRIGIDO** - alertas_api.py refatorado, url_prefix corrigido, rotas funcionais

## AÇÕES PENDENTES DO USUÁRIO (2026-01-25)
**⚠️ OBRIGATÓRIO antes do próximo deploy:**
1. **REVOGAR** a API key Odoo antiga (67705b09...) - ela foi exposta no histórico Git
2. **GERAR** nova API key no Odoo
3. **CONFIGURAR** no Render Dashboard:
   - `ODOO_API_KEY` (nova chave)
   - `ODOO_USERNAME` (email do usuário)
   - `SECRET_KEY` (gerar com: `python -c 'import secrets; print(secrets.token_hex(32))'`)
   - `JWT_SECRET_KEY` (opcional, para API)


---

## 1. SPECS PENDENTES DE IMPLEMENTAÇÃO

### 1.1 ✅ Dashboard de Métricas (`specs/dashboard-metricas.md`) - CONCLUÍDO

**Status**: ✅ IMPLEMENTED (100%)
**Implementado em**: 2026-01-25
**Esforço real**: ~30 minutos

**O que foi criado**:
- [x] `app/metricas/__init__.py` - Módulo inicializador
- [x] `app/metricas/routes.py` - Blueprint com rota `/metricas` e `/metricas/dashboard`
- [x] `app/templates/metricas/dashboard.html` - Template com 3 cards de métricas
- [x] Blueprint `metricas_bp` registrado em `app/__init__.py:678,747`
- [x] Link no menu Operacional > Relatórios em `base.html:204-211`

**Funcionalidades implementadas**:
- 3 cards com números formatados (filtro `numero_br`)
- Pedidos do mês, Separações pendentes, Embarques do mês
- Links para telas relacionadas (carteira, separações, embarques)
- Botão de atualização manual
- Tratamento de erros com rollback

---

### 1.2 ✅ Sistema de Memória Persistente Agent SDK (`specs/memoria-persistente-agent-sdk.md`) - CONCLUÍDO

**Status**: ✅ IMPLEMENTED (100%)
**Implementado em**: 2026-01-25
**Esforço real**: ~45 minutos

**O que foi implementado**:
| Componente | Status | Localização |
|------------|--------|-------------|
| `DatabaseMemoryTool` | ✅ Completo | `app/agente/memory_tool.py:71-420` |
| 7 comandos CRUD | ✅ Funcionando | view, create, str_replace, insert, delete, rename, clear_all_memory |
| Modelo `AgentMemory` | ✅ Implementado | `app/agente/models.py:328-537` |
| `MemoryAgent` (Haiku hooks) | ✅ Funcionando | `app/agente/hooks/memory_agent.py` |
| Factory `get_memory_tool_for_user()` | ✅ Implementado | `app/agente/memory_tool.py:410-420` |
| **"Memory" em `allowed_tools`** | ✅ NOVO | `app/agente/sdk/client.py:379` |
| **Modelo `AgentMemoryVersion`** | ✅ NOVO | `app/agente/models.py:540-660` |
| **Tabela `agent_memory_versions`** | ✅ NOVO | Script: `scripts/criar_tabela_agent_memory_versions.py` |
| **Versionamento em updates** | ✅ NOVO | `app/agente/memory_tool.py` (create, str_replace, insert) |

**Funcionalidades implementadas**:
- ✅ Claude pode usar Memory Tool (view, create, str_replace, insert, delete, rename)
- ✅ Versões salvas automaticamente antes de cada update
- ✅ Métodos: `get_latest_version_number()`, `save_version()`, `get_versions()`, `get_version()`
- ✅ Cascade delete quando memória é removida
- ✅ Unique constraint em (memory_id, version)

**Diagrama de Fluxo Implementado**:
```
User → Claude [COM Memory Tool] → DatabaseMemoryTool
                                         ↓
                              AgentMemory (UPDATE)
                                    ↓
                         AgentMemoryVersion (versão anterior salva)
```

**Para testar**:
```bash
# Rodar script de criação de tabela (já executado em dev)
python scripts/criar_tabela_agent_memory_versions.py

# Teste de versionamento
python -c "
from app import create_app
from app.agente.models import AgentMemory, AgentMemoryVersion
app = create_app()
with app.app_context():
    mem = AgentMemory.get_by_path(1, '/memories/test.txt')
    if mem:
        versions = AgentMemoryVersion.get_versions(mem.id)
        print(f'Versões: {len(versions)}')
"
```

---

### 1.3 ✅ Sistema de Notificações (Email, Webhook, In-App) - CONCLUÍDO

**Status**: ✅ IMPLEMENTED (100%)
**Implementado em**: 2026-01-25
**Esforço real**: ~1 hora

**Motivação**: TODOs em `app/carteira/models.py:1190-1191` e `app/carteira/alert_system.py:113-114` pediam sistema de notificações.

**O que foi implementado**:
| Componente | Status | Localização |
|------------|--------|-------------|
| **Modelo `AlertaNotificacao`** | ✅ Completo | `app/notificacoes/models.py:20-180` |
| **Modelo `WebhookConfig`** | ✅ Completo | `app/notificacoes/models.py:183-270` |
| **`NotificationDispatcher`** | ✅ Completo | `app/notificacoes/services.py:37-340` |
| **`EmailSender` (SMTP/SES/SendGrid)** | ✅ Completo | `app/notificacoes/email_sender.py:1-350` |
| **`EmailTemplates` (HTML)** | ✅ Completo | `app/notificacoes/email_sender.py:313-450` |
| **API Routes (CRUD)** | ✅ Completo | `app/notificacoes/routes.py:1-400` |
| **Blueprint `notificacoes_bp`** | ✅ Registrado | `app/__init__.py:682,755` |
| **Integração `AlertaSistemaCarteira`** | ✅ Funcionando | `app/carteira/alert_system.py:98-155` |
| **Integração `CarteiraPrincipal`** | ✅ Funcionando | `app/carteira/models.py:1176-1205` |
| **Script de criação de tabelas** | ✅ Completo | `scripts/criar_tabelas_notificacoes.py` |

**Canais de Notificação Suportados**:
- ✅ **in_app**: Persistido no banco, exibível na UI
- ✅ **email**: SMTP, AWS SES, SendGrid (via env vars)
- ✅ **webhook**: HTTP POST com autenticação (bearer, api_key, basic)

**Configuração de Email** (variáveis de ambiente):
```bash
EMAIL_BACKEND=smtp        # smtp, ses, sendgrid
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USERNAME=user@gmail.com
EMAIL_PASSWORD=app_password
EMAIL_FROM=alertas@empresa.com
EMAIL_FROM_NAME=Sistema de Frete
```

**Uso no código**:
```python
from app.notificacoes.services import enviar_alerta_critico

resultado = enviar_alerta_critico(
    titulo='Separação COTADA alterada',
    mensagem='Detalhes do alerta...',
    tipo='SEPARACAO_COTADA_ALTERADA',
    dados={'pedido': '123', 'produto': 'ABC'},
    email_destinatario='usuario@empresa.com'
)
```

**API Endpoints**:
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/notificacoes/` | Lista notificações do usuário |
| GET | `/notificacoes/<id>` | Detalhes de uma notificação |
| POST | `/notificacoes/<id>/lido` | Marca como lida |
| POST | `/notificacoes/marcar-todas-lidas` | Marca todas como lidas |
| GET | `/notificacoes/api/nao-lidas` | Contador para navbar |
| GET | `/notificacoes/api/recentes` | Últimas não lidas (dropdown) |
| GET | `/notificacoes/webhooks` | Lista webhooks (admin) |
| POST | `/notificacoes/webhooks` | Cadastra webhook (admin) |
| POST | `/notificacoes/webhooks/<id>/testar` | Testa webhook (admin) |

**Para deploy**:
```bash
# 1. Criar tabelas no banco
python scripts/criar_tabelas_notificacoes.py

# 2. Configurar email no Render Dashboard (opcional)
EMAIL_BACKEND=smtp
EMAIL_HOST=smtp.gmail.com
# ... demais vars
```

---

## 2. PROBLEMAS DE SEGURANÇA (CRÍTICOS)

### 2.1 ✅ API Key Odoo HARDCODED - CORRIGIDO (2026-01-25)

**Status**: ✅ CORRIGIDO
**Corrigido em**: 2026-01-25
**Verificado por**: Subagente Explore

**O que foi corrigido**:
Todos os 17 arquivos com API key hardcoded foram atualizados para usar variáveis de ambiente:

| Arquivo | Status |
|---------|--------|
| `app/odoo/config/odoo_config.py` | ✅ Corrigido |
| `app/utils/odoo_integration.py` | ✅ Corrigido |
| `app/fretes/services/documentacao_odoo/DOCUMENTACAO_LANCAMENTO_FRETE_ODOO.md` | ✅ Corrigido |
| `scripts/investigar_cte_odoo_standalone.py` | ✅ Corrigido |
| `scripts/investigar_dfe_32639_standalone.py` | ✅ Corrigido |
| `scripts/lancamento_frete_completo.py` | ✅ Corrigido |
| `scripts/lancamento_frete_automatico.py` | ✅ Corrigido |
| `scripts/exemplo_criar_pedido_venda_odoo.py` | ✅ Corrigido |
| `scripts/confirmar_purchase_order.py` | ✅ Corrigido |
| `scripts/aprovar_purchase_order.py` | ✅ Corrigido |
| `scripts/criar_fatura_po.py` | ✅ Corrigido |
| `scripts/investigar_purchase_order_31085.py` | ✅ Corrigido |
| `scripts/descobrir_empresa_cd.py` | ✅ Corrigido |
| `scripts/investigar_invoice_campos.py` | ✅ Corrigido |
| `scripts/investigar_operacao_fiscal_po.py` | ✅ Corrigido |
| `scripts/buscar_ctes_serv_industrializacao.py` | ✅ Corrigido |

**Padrão implementado**:
```python
import os
ODOO_CONFIG = {
    'url': os.environ.get('ODOO_URL', 'https://odoo.nacomgoya.com.br'),
    'database': os.environ.get('ODOO_DATABASE', 'odoo-17-ee-nacomgoya-prd'),
    'username': os.environ.get('ODOO_USERNAME', ''),
    'api_key': os.environ.get('ODOO_API_KEY', ''),
}

# Validação de credenciais
if not ODOO_CONFIG['api_key']:
    raise ValueError("ODOO_API_KEY não configurado.")
```

**⚠️ AÇÃO PENDENTE DO USUÁRIO**:
1. REVOGAR a API key antiga no Odoo (67705b09...)
2. Gerar nova API key no Odoo
3. Configurar variáveis de ambiente no Render Dashboard:
   - `ODOO_URL`
   - `ODOO_DATABASE`
   - `ODOO_USERNAME`
   - `ODOO_API_KEY`

---

### 2.2 ✅ Flask SECRET_KEY com Fallbacks Hardcoded - CORRIGIDO (2026-01-25)

**Status**: ✅ CORRIGIDO
**Corrigido em**: 2026-01-25

**O que foi corrigido**:

| Arquivo | Antes | Depois | Status |
|---------|-------|--------|--------|
| `config.py` | `or "dev-key-super-secreta-aqui"` | Erro se produção sem SECRET_KEY | ✅ |
| `app/__init__.py` | Fallbacks hardcoded | Sem sobrescrita em produção | ✅ |
| `app/api/odoo/auth.py` | JWT_SECRET_KEY hardcoded | Warning + fallback dev only | ✅ |
| `.env.render` | Placeholder com valor | Template sem valores reais | ✅ |

**Comportamento implementado**:
- **Produção**: Lança `ValueError` se `SECRET_KEY` não configurado
- **Desenvolvimento**: Permite fallback para testes locais
- **JWT**: Warning em log se não configurado + fallback dev

**⚠️ AÇÃO PENDENTE DO USUÁRIO**:
1. Configurar `SECRET_KEY` no Render Dashboard:
   ```bash
   python -c 'import secrets; print(secrets.token_hex(32))'
   ```
2. Configurar `JWT_SECRET_KEY` no Render Dashboard (opcional, para API)

---

### 2.3 🟠 Test Credentials em Scripts

**Arquivo**: `scripts/backup/restore_test.py`
| Linha | Pattern |
|-------|---------|
| 131 | `"POSTGRES_PASSWORD": "testpass"` |
| 151 | `password="testpass"` |
| 270 | `env["PGPASSWORD"] = "testpass"` |

**Risco**: Médio - padrões de senha expostos

---

## 3. PROBLEMAS ESTRUTURAIS CRÍTICOS

### 3.1 ✅ Event Listener de Separacao SEM Re-raise - CORRIGIDO

**Arquivo**: `app/separacao/models.py:315-427`
**Corrigido em**: 2026-01-25

**Correção aplicada** (linha 426-427):
```python
except Exception as e:
    logger.error(f"❌ Erro ao recalcular totais do embarque: {e}", exc_info=True)
    # ✅ CORREÇÃO: Re-levantar exceção para evitar transações parcialmente corrompidas
    raise
```

**Todos os listeners no arquivo** agora OK:
| Listener | Linhas | Re-raise | Status |
|----------|--------|----------|--------|
| `setar_falta_pagamento_inicial` | 198-230 | Não necessário | ✅ OK (graceful fail) |
| `atualizar_status_automatico` | 233-280 | Sem try/except | ✅ OK |
| `log_reversao_status` | 283-312 | Sem try/except | ✅ OK |
| `recalcular_totais_embarque` | 315-427 | **CORRIGIDO** | ✅ OK |

---

### 3.2 ✅ PreSeparacaoItem.aplicar_reducao_quantidade() SEM Atomicidade - CORRIGIDO

**Arquivo**: `app/carteira/models.py:922-1045`
**Corrigido em**: 2026-01-25

**Correção aplicada**:
- ✅ FASE 1: `db.session.begin_nested()` para CarteiraPrincipal
- ✅ FASE 2: `db.session.begin_nested()` para Pré-separações
- ✅ FASE 3: `db.session.begin_nested()` para Separacao ABERTO + `raise` em ImportError
- ✅ FASE 4: `db.session.begin_nested()` para Separacao COTADO + `raise` em ImportError
- ✅ Commit final só executa se TODOS os savepoints passaram

**Cenário de falha agora tratado**:
```
Step 1: CarteiraPrincipal reduzida ✓ (savepoint 1)
Step 2: Pré-separação reduzida ✓ (savepoint 2)
Step 3: Separacao ABERTO - se falhar, rollback savepoint 3 ✓
Step 4: Separacao COTADO - se falhar, rollback savepoint 4 ✓
Commit: Só executa se TODOS os savepoints OK ✓
```

---

### 3.3 ✅ AgentSession e AgentMemory SEM Cascade Delete - CORRIGIDO (2026-01-25)

**Status**: ✅ CORRIGIDO
**Corrigido em**: 2026-01-25
**Arquivo**: `app/agente/models.py`

**Correções aplicadas**:
- **AgentSession (linha 67-70)**: Adicionado `cascade='all, delete-orphan'`
- **AgentMemory (linha 369-372)**: Adicionado `cascade='all, delete-orphan'`

**Código implementado**:
```python
# AgentSession:
user = db.relationship(
    'Usuario',
    backref=db.backref('agent_sessions', lazy='dynamic', cascade='all, delete-orphan')
)

# AgentMemory:
user = db.relationship(
    'Usuario',
    backref=db.backref('agent_memories', lazy='dynamic', cascade='all, delete-orphan')
)
```

**Impacto**: Deletar usuário agora remove automaticamente suas sessões e memórias órfãs.

---

### 3.4 🟠 CarteiraPrincipal SEM Relacionamento FK com Separacao

**Arquivo**: `app/carteira/models.py`, `app/separacao/models.py`
**Verificado por**: Subagente Explore (2026-01-25)
**Problema**: Sem ForeignKey entre CarteiraPrincipal e Separacao
**Impacto**: Queries manuais, sem integridade referencial, sem cascata

**Relacionamento atual** (implícito):
```
CarteiraPrincipal (num_pedido, cod_produto)
            ↓
         [IMPLÍCITO - sem FK]
            ↓
Separacao (num_pedido, cod_produto, separacao_lote_id)
```

**Nota**: A ausência de FK é **INTENCIONAL** para evitar deadlocks durante sincronização Odoo. Manter status atual por enquanto.

**Tarefas alternativas**:
- [ ] Documentar relacionamento implícito no CLAUDE.md
- [ ] Criar índice composto em Separacao se não existir

---

## 4. ÍNDICES FALTANTES (Performance)

### 4.1 ✅ Índices Críticos para Queries Frequentes - CONCLUÍDO (2026-01-25)

**Verificado por**: Subagente Explore (2026-01-25)
**Implementado em**: 2026-01-25
**Script**: `scripts/criar_indices_performance.py`

**RESUMO: 19 índices criados com sucesso**
- ✅ 10 índices ALTA prioridade criados
- ✅ 9 índices MÉDIA prioridade criados
- ⚠️ 2 índices já existiam (idx_sep_num_pedido, idx_sep_cotacao)

| Tabela | Campo(s) | Tipo | Uso | Prioridade |
|--------|----------|------|-----|------------|
| `separacao` | `num_pedido` | Simple | Filtros frequentes | 🔴 ALTA |
| `separacao` | `cotacao_id` (FK) | Simple | JOIN | 🔴 ALTA |
| `separacao` | `(rota, sub_rota)` | Composto | Roteirização | 🟠 ALTA |
| `embarques` | `transportadora_id` (FK) | Simple | JOIN | 🔴 ALTA |
| `embarques` | `status` | Simple | Filtros | 🔴 ALTA |
| `embarques` | `cotacao_id` (FK) | Simple | JOIN | 🔴 ALTA |
| `embarque_itens` | `embarque_id` (FK) | Simple | JOIN | 🔴 ALTA |
| `embarque_itens` | `status` | Simple | Filtros | 🔴 ALTA |
| `embarque_itens` | `cotacao_id` (FK) | Simple | JOIN | 🔴 ALTA |
| `embarque_itens` | `cnpj_cliente` | Simple | Dashboard | 🟡 MÉDIA |
| `embarque_itens` | `pedido` | Simple | Lookups | 🟡 MÉDIA |
| `fretes` | `embarque_id` (FK) | Simple | JOIN | 🔴 ALTA |
| `fretes` | `transportadora_id` (FK) | Simple | JOIN | 🔴 ALTA |
| `fretes` | `status` | Simple | Filtros | 🔴 ALTA |
| `fretes` | `fatura_frete_id` (FK) | Simple | JOIN | 🟡 MÉDIA |
| `faturas_frete` | `transportadora_id` (FK) | Simple | JOIN | 🟡 MÉDIA |
| `faturas_frete` | `status_conferencia` | Simple | Filtros | 🟡 MÉDIA |
| `conta_corrente_transportadora` | `transportadora_id` (FK) | Simple | JOIN | 🟡 MÉDIA |
| `conta_corrente_transportadora` | `frete_id` (FK) | Simple | JOIN | 🟡 MÉDIA |
| `carteira_principal` | `cond_pgto_pedido` | Simple | Payment filtering | 🟡 MÉDIA |
| `carteira_principal` | `data_entrega_pedido` | Simple | Date ranges | 🟡 MÉDIA |

**Migration sugerida**:
```python
# migrations/versions/add_missing_indices.py
def upgrade():
    # HIGH PRIORITY
    op.create_index('idx_sep_num_pedido', 'separacao', ['num_pedido'])
    op.create_index('idx_sep_cotacao_id', 'separacao', ['cotacao_id'])
    op.create_index('idx_sep_rota_sub_rota', 'separacao', ['rota', 'sub_rota'])
    op.create_index('idx_embarque_transportadora', 'embarques', ['transportadora_id'])
    op.create_index('idx_embarque_status', 'embarques', ['status'])
    op.create_index('idx_embarque_cotacao', 'embarques', ['cotacao_id'])
    op.create_index('idx_embarque_item_embarque', 'embarque_itens', ['embarque_id'])
    op.create_index('idx_embarque_item_status', 'embarque_itens', ['status'])
    op.create_index('idx_embarque_item_cotacao', 'embarque_itens', ['cotacao_id'])
    op.create_index('idx_frete_embarque', 'fretes', ['embarque_id'])
    op.create_index('idx_frete_transportadora', 'fretes', ['transportadora_id'])
    op.create_index('idx_frete_status', 'fretes', ['status'])

    # MEDIUM PRIORITY
    op.create_index('idx_embarque_item_cnpj', 'embarque_itens', ['cnpj_cliente'])
    op.create_index('idx_embarque_item_pedido', 'embarque_itens', ['pedido'])
    op.create_index('idx_frete_fatura', 'fretes', ['fatura_frete_id'])
    op.create_index('idx_fatura_transportadora', 'faturas_frete', ['transportadora_id'])
    op.create_index('idx_fatura_status', 'faturas_frete', ['status_conferencia'])
    op.create_index('idx_cc_transportadora', 'conta_corrente_transportadora', ['transportadora_id'])
    op.create_index('idx_cc_frete', 'conta_corrente_transportadora', ['frete_id'])
    op.create_index('idx_carteira_cond_pgto', 'carteira_principal', ['cond_pgto_pedido'])
    op.create_index('idx_carteira_data_entrega', 'carteira_principal', ['data_entrega_pedido'])
```

---

## 5. TEMPLATES ÓRFÃOS (Violação CLAUDE.md)

### 5.1 ✅ BI Module - 4 Telas SEM Menu - CORRIGIDO

**Verificado por**: Subagente Explore (2026-01-25)
**Corrigido em**: 2026-01-25
**Problema original**: Templates e rotas existiam mas não tinham links no menu
**Violação corrigida**: CLAUDE.md regra "TODA TELA CRIADA DEVE TER ACESSO PELA INTERFACE"

**Correções aplicadas**:
1. ✅ Adicionado dropdown "BI & Analytics" no menu `base.html:479-503`
2. ✅ Adicionados links para as 4 rotas principais
3. ✅ Corrigido import de routes em `app/bi/__init__.py:9`

**Status do módulo BI**:
| Componente | Status | Localização |
|------------|--------|-------------|
| Blueprint | ✅ | `app/bi/__init__.py` |
| Routes (13 rotas) | ✅ | `app/bi/routes.py` |
| Models (5 tabelas) | ✅ | `app/bi/models.py` |
| Services (6 métodos) | ✅ | `app/bi/services.py` |
| Services Helpers | ✅ | `app/bi/services_helpers.py` |
| Templates (4) | ✅ | `app/templates/bi/*.html` |
| **Menu links** | ✅ **IMPLEMENTADO** | `app/templates/base.html:479-503` |

**Menu adicionado** (entre "Carteira & Estoque" e "Comercial"):
- Dashboard Principal → `/bi/dashboard`
- Análise de Transportadoras → `/bi/transportadoras`
- Análise Regional → `/bi/regional`
- Análise de Despesas → `/bi/despesas`

**Permissões**: `current_user.is_authenticated and not is_comercial_only`

---

### 5.2 ✅ Templates Debug/Test SEM Uso Produtivo - REMOVIDOS (2026-01-25)

**Verificado por**: Subagente Explore (2026-01-25)
**Removidos em**: 2026-01-25

| Template | Localização | Status |
|----------|-------------|--------|
| ~~`teste_fontes.html`~~ | ~~`app/templates/carteira/`~~ | ✅ REMOVIDO |
| ~~`teste_formatacao_debug.html`~~ | ~~`app/templates/motochefe/`~~ | ✅ REMOVIDO |
| ~~`tagplus_teste_auth.html`~~ | ~~`app/templates/integracoes/`~~ | ✅ REMOVIDO |

**Rota removida**: `/simples/teste-fontes` em `app/carteira/routes/carteira_simples_api.py`

**Total removido**: 1.314 linhas de código de debug/teste

---

## 6. ERROR HANDLING INCONSISTENTE

### 6.1 ✅ Módulos SEM Rollback em Exception Handlers - CORRIGIDO (2026-01-25)

**Verificado por**: Subagente Explore (2026-01-25)
**Corrigido em**: 2026-01-25
**Total identificado**: 27 exception handlers sem rollback

**Arquivos críticos**:
| Arquivo | Missing Rollback | Críticos | Status |
|---------|------------------|----------|--------|
| `app/producao/routes.py` | 15 | 2 | ✅ **CORRIGIDO** |
| `app/rastreamento/routes.py` | 5 | 0 | ⚠️ Read-only (OK) |
| `app/localidades/routes.py` | 7 | 0 | ⚠️ Read-only (OK) |
| `app/cotacao/routes.py` | 0 | 0 | ✅ OK |

**Correções aplicadas em producao/routes.py**:
- **Loop importação palletizacao (linhas 340-434)**: ✅ Adicionado `db.session.begin_nested()` e `db.session.rollback()` por item
- **Loop importação programação (linhas 559-614)**: ✅ Adicionado `db.session.begin_nested()` e `db.session.rollback()` por item
- **Commit global removido**: Cada item agora commita via savepoint individual

**Padrão implementado**:
```python
for index, row in df.iterrows():
    try:
        db.session.begin_nested()  # Savepoint
        # ... processar item ...
        db.session.add(novo_item)
        db.session.commit()  # Commit do savepoint
    except Exception as e:
        db.session.rollback()  # Rollback apenas do item atual
        erros.append(f"Linha {index + 1}: {str(e)}")
        continue
```

---

## 7. TODOs NO CÓDIGO

### 7.1 🟠 TODOs de Alta Prioridade (Business Logic)

**Verificado por**: Subagente Explore (2026-01-25)
**Total encontrado**: 32 TODOs

| Arquivo | Linha | Descrição | Impacto |
|---------|-------|-----------|---------|
| ~~`app/utils/grupo_empresarial.py`~~ | ~~507-523~~ | ~~`obter_transportadoras_grupo()` é stub~~ | ✅ **CORRIGIDO** (2026-01-25) |
| ~~`app/bi/services.py`~~ | ~~527-528~~ | ~~2 métricas hardcoded em `processar_analise_regional()`~~ | ✅ **CORRIGIDO** (2026-01-25) |
| ~~`app/bi/services.py`~~ | ~~674-676~~ | ~~3 métricas hardcoded em `processar_indicadores_mensais()`~~ | ✅ **CORRIGIDO** (2026-01-25) |
| ~~`app/portal/routes.py`~~ | ~~767-787~~ | ~~`comparar_portal()` com dados simulados hardcoded~~ | ✅ **CORRIGIDO** (2026-01-25) - Usa VerificadorProtocoloAtacadao |
| ~~`app/portal/routes.py`~~ | ~~821-842~~ | ~~`extrair_confirmacoes()` auto-confirma sem verificar portal real~~ | ✅ **CORRIGIDO** (2026-01-25) - Verifica portal REAL |
| ~~`app/carteira/models.py`~~ | ~~1190-1191~~ | ~~Sistema de notificações (email, webhook) não implementado~~ | ✅ **IMPLEMENTADO** (2026-01-25) |

---

### 7.2 🟡 TODOs de Média Prioridade

| Arquivo | Linha | Descrição |
|---------|-------|-----------|
| `app/faturamento/routes.py` | 1131 | Dashboard de status não implementado |
| `app/faturamento/routes.py` | 1143 | Relatório de auditoria não implementado |
| ~~`app/faturamento/routes.py`~~ | ~~1290~~ | ~~`nfs_pendentes = 5` hardcoded~~ | ✅ **CORRIGIDO** (2026-01-25) |
| `app/faturamento/routes.py` | 1322 | Exportação não implementada |
| `app/rastreamento/routes.py` | 1032 | Integração Odoo chatter NF pendente |
| `app/rastreamento/tasks.py` | 110 | Notificação equipe (email, Slack) pendente |
| `app/portal/session_manager.py` | 214 | Email notifications pendente |
| `app/monitoramento/routes.py` | 2277, 2354 | Exclusão S3 de arquivo anterior |
| `app/portaria/routes.py` | 454 | Exclusão S3 de arquivo anterior |
| ~~`app/carteira/routes/alertas_api.py`~~ | ~~219~~ | ~~Tabela histórico alertas - retorna mock~~ | ✅ **CORRIGIDO** (2026-01-25) |
| `app/producao/routes.py` | 628 | Rotas adicionais (importar, criar_op, editar_rota) |
| `app/motochefe/services/importacao_fase4_pedidos.py` | 529 | Calcular comissões |
| `app/bi/services.py` | 526 | Calcular percentual no prazo |
| ~~`app/carteira/alert_system.py`~~ | ~~113-114~~ | ~~Notificações~~ | ✅ **IMPLEMENTADO** (2026-01-25) - Via NotificationDispatcher |
| `app/carteira/alert_system.py` | 200, 221 | Verificações expandidas (pré-separações, conflitos) |
| `app/pedidos/leitura/routes.py` | 618 | Remover após migração |

---

### 7.3 🟢 TODOs de Baixa Prioridade (Polish)

| Arquivo | Linha | Descrição |
|---------|-------|-----------|
| `app/transportadoras/routes.py` | 190 | Campos de auditoria |
| `app/financeiro/models.py` | 1328 | Remover titulo_id após migração |

---

### 7.4 ✅ BUGS DESCOBERTOS E CORRIGIDOS (2026-01-25)

| Arquivo | Linha | Descrição | Status |
|---------|-------|-----------|--------|
| ~~`app/carteira/routes/alertas_api.py`~~ | ~~135-136~~ | ~~Chama `service._verificar_risco_faturamento_pendente()` que NÃO EXISTE em `CarteiraService`~~ | ✅ **CORRIGIDO** |
| ~~`app/templates/carteira/alertas_dashboard.html`~~ | ~~17~~ | ~~Template espera `stats` mas rota passa `alertas` - variáveis incompatíveis~~ | ✅ **CORRIGIDO** |
| ~~`app/carteira/routes/alertas_visualizacao.py`~~ | ~~13~~ | ~~url_prefix duplicado `/carteira/carteira/alertas`~~ | ✅ **CORRIGIDO** |

**Correção implementada** (2026-01-25):

1. **alertas_api.py refatorado**:
   - Rota `/` agora redireciona para `/carteira/alertas/dashboard` (alertas_visualizacao)
   - Removida função `_detalhar_faturamento_pendente()` que usava método inexistente
   - `_executar_verificacoes_completas()` agora usa apenas `AlertaSistemaCarteira` e `_buscar_historico_alertas()`
   - Endpoints API `/api/verificar` e `/api/detalhes/<tipo>` funcionam corretamente

2. **alertas_visualizacao.py corrigido**:
   - `url_prefix` alterado de `/carteira/alertas` para `/alertas` (já está sob `carteira_bp`)
   - Rotas agora corretas: `/carteira/alertas/dashboard`, `/carteira/alertas/marcar-reimpresso/<id>`, `/carteira/alertas/limpar-orfaos`

3. **Template compatível**:
   - `alertas_dashboard.html` é usado apenas por `alertas_visualizacao.py` que passa variáveis corretas (`stats`, `alertas`, `tipos`)

**Rotas finais**:
```
/carteira/alertas/              → Redirect para dashboard
/carteira/alertas/dashboard     → Dashboard visual (alertas_visualizacao_bp)
/carteira/alertas/api/verificar → API JSON verificação em tempo real
/carteira/alertas/api/detalhes/<tipo> → API JSON detalhes (separacoes_cotadas, historico_recente)
```

---

## 8. PASS STATEMENTS (Código Vazio)

### 8.1 🟡 Pass Statements Significativos

**Verificado por**: Grep (2026-01-25)
**Total**: 250 `pass` statements em 76 arquivos

**Arquivos com mais pass statements** (potencialmente vazios):
| Arquivo | Count | Análise Necessária |
|---------|-------|-------------------|
| `app/scheduler/sincronizacao_incremental_definitiva.py` | 39 | Verificar se são placeholders |
| `app/fretes/routes.py` | 24 | Verificar rotas vazias |
| `app/faturamento/routes.py` | 10 | Verificar rotas vazias |
| `app/monitoramento/routes.py` | 9 | Verificar rotas vazias |
| `app/portal/atacadao/playwright_client.py` | 12 | Verificar métodos vazios |
| `app/devolucao/routes/ocorrencia_routes.py` | 7 | Verificar rotas vazias |
| `app/cotacao/routes.py` | 7 | Verificar rotas vazias |

**Nota**: Muitos `pass` são legítimos (classes vazias, except blocks). Verificar caso a caso.

---

## 9. ODOO INTEGRATION GAPS

### 9.1 🟡 Webhooks Não Implementados

**Verificado por**: Subagente Explore (2026-01-25)
**Status**: Sistema é 100% PULL-BASED (polling)

**Arquitetura atual**:
```
Odoo ERP
   ↑
   │ (Polling via XML-RPC cada 30min)
   │
Sistema (Flask + APScheduler)
   └─ sincronizacao_incremental_definitiva.py
```

**Latência de sincronização**:
- Melhor caso: 0 min (trigger manual via UI)
- Caso típico: 0-30 min
- Pior caso: 30 min

**Não existe**:
- [ ] Rotas webhook para callbacks do Odoo
- [ ] Event listeners para mudanças em models Odoo
- [ ] Verificação de assinatura para webhooks

**Tarefas** (se real-time for necessário):
- [ ] Criar rotas `POST /odoo/webhooks/sale-order-update`
- [ ] Criar rotas `POST /odoo/webhooks/invoice-update`
- [ ] Configurar triggers no Odoo para chamar webhooks

---

## 10. ORDEM DE EXECUÇÃO SUGERIDA

### Fase 0: Segurança (IMEDIATO - Hoje)
1. ✅ ~~**API Key Odoo**~~ - CORRIGIDO (2026-01-25) - 17 arquivos atualizados
2. ✅ ~~**SECRET_KEY**~~ - CORRIGIDO (2026-01-25) - Erro em produção se não configurado
3. ✅ ~~**JWT_SECRET_KEY**~~ - CORRIGIDO (2026-01-25) - Warning + fallback dev
4. ⚠️ **AÇÃO DO USUÁRIO** - Revogar API key antiga e configurar env vars no Render

### Fase 1: Críticos (Semana 1-2)
5. ✅ ~~Dashboard Métricas~~ - CONCLUÍDO (2026-01-25)
6. ✅ ~~Re-raise em event listener `recalcular_totais_embarque`~~ - CONCLUÍDO (2026-01-25)
7. ✅ ~~Savepoint em `aplicar_reducao_quantidade()`~~ - CONCLUÍDO (2026-01-25)

### Fase 2: Alta Prioridade (Semana 3-4)
8. ✅ ~~Memory Tool SDK integration~~ - CONCLUÍDO (2026-01-25)
9. ✅ ~~Índices de performance~~ - CONCLUÍDO (2026-01-25) - 19 índices criados via script
10. ✅ ~~Menu links para BI 4 telas~~ - CONCLUÍDO (2026-01-25)
11. ✅ ~~Error handling `producao/routes.py`~~ - CONCLUÍDO (2026-01-25) - Savepoints por item
12. ✅ ~~`grupo_empresarial.obter_transportadoras_grupo()`~~ - CONCLUÍDO (2026-01-25) - Detecta grupos via prefixo CNPJ
13. ✅ ~~TODOs BI métricas hardcoded~~ - CONCLUÍDO (2026-01-25) - 5 novos métodos em `services_helpers.py`

### Fase 3: Média Prioridade (Mês 2)
12. ✅ ~~Portal `comparar_portal()` e `extrair_confirmacoes()`~~ - CONCLUÍDO (2026-01-25) - Usa VerificadorProtocoloAtacadao real
13. ✅ ~~Cascade delete AgentSession/AgentMemory~~ - CONCLUÍDO (2026-01-25)
14. ✅ ~~`nfs_pendentes` hardcoded~~ - CONCLUÍDO (2026-01-25) - Query real implementada
15. 🟡 Sistema notificações carteira (4h)
16. ✅ ~~Templates teste/backup~~ - CONCLUÍDO (2026-01-25) - 3 templates removidos (1.314 linhas)
17. 🟡 TODOs faturamento (dashboard, auditoria, exportação) (6h)

### Fase 4: Backlog
18. 🟢 TODOs de baixa prioridade
19. 🟢 Webhooks Odoo (se necessário)
20. 🟢 Auditoria de 250 pass statements
21. 🟢 Logging padronizado

---

## 11. VALIDAÇÃO

Após cada implementação, verificar:

- [ ] Código 100% funcional (sem TODO/FIXME pendente)
- [ ] Tela tem link no menu (se aplicável)
- [ ] Usa filtros `numero_br`/`valor_br` para números
- [ ] Rollback em exception handlers com DB operations
- [ ] Índices para queries frequentes
- [ ] Testes manuais dos cenários principais
- [ ] Credenciais via env vars (não hardcoded)

---

## 12. ESTATÍSTICAS DA ANÁLISE

| Métrica | Valor |
|---------|-------|
| Arquivos Python analisados | 500+ |
| Subagentes utilizados | 16 |
| Specs verificados | 2 |
| TODOs encontrados | 32 |
| `pass` statements encontrados | 250 |
| Elipses `...` encontradas | 20 |
| Templates analisados | 354+ |
| Routes.py auditados | 32 |
| Índices verificados | 21 faltando |
| Credenciais hardcoded | 16 arquivos |

---

**Documento gerado por análise automatizada de 500+ arquivos em `app/` via 16 subagentes paralelos**
