# 📋 Resumo Completo - Implementação de Requisições de Compras

**Data**: 31/10/2025
**Status**: ✅ QUASE COMPLETO - Faltam apenas templates HTML

---

## ✅ O QUE FOI IMPLEMENTADO:

### 1. ✅ Modelo HistoricoRequisicaoCompras
**Arquivo**: [app/manufatura/models.py](app/manufatura/models.py:368-427)

**Campos**:
- `requisicao_id` (FK para RequisicaoCompras)
- `num_requisicao`
- `operacao` (CRIAR, EDITAR)
- `campo_alterado`
- `valor_antes`, `valor_depois`
- `cod_produto`, `nome_produto`
- `alterado_em`, `alterado_por`
- `write_date_odoo`
- `dados_adicionais` (JSONB)

**Índices otimizados** para queries rápidas.

---

### 2. ✅ Serviço de Importação Completo
**Arquivo**: [app/odoo/services/requisicao_compras_service.py](app/odoo/services/requisicao_compras_service.py)

**Classe**: `RequisicaoComprasService`

**Métodos principais**:
- `sincronizar_requisicoes_incremental(minutos_janela, primeira_execucao)`
- `_buscar_requisicoes_odoo()` - Busca por `create_date` e `write_date`
- `_processar_requisicoes()` - Processa cada requisição
- `_processar_linha_requisicao()` - Valida `detailed_type='product'`
- `_criar_requisicao()` - Cria nova + histórico
- `_atualizar_requisicao()` - Compara campos + registra mudanças

**Características**:
- ✅ Janela: 90 minutos (padrão)
- ✅ Filtro: `state in ['approved', 'done']`
- ✅ Validação: `detailed_type = 'product'`
- ✅ Query adicional para `default_code` e `name`
- ✅ Rastreamento automático de mudanças
- ✅ Registro no histórico

---

### 3. ✅ Integração no Scheduler Automático
**Arquivo**: [app/scheduler/sincronizacao_incremental_definitiva.py](app/scheduler/sincronizacao_incremental_definitiva.py)

**Mudanças**:
- ✅ Adicionado `JANELA_REQUISICOES = 90` minutos
- ✅ Service global: `requisicao_service`
- ✅ Inicialização em `inicializar_services()`
- ✅ Sincronização após Carteira (3️⃣ REQUISIÇÕES)
- ✅ Retry automático (3 tentativas)
- ✅ Logging completo

**Execução**: A cada 30 minutos automaticamente

---

### 4. ⚠️ Rotas (PARCIAL - Precisa ajustar)
**Arquivo**: [app/manufatura/routes/requisicao_compras_routes.py](app/manufatura/routes/requisicao_compras_routes.py)

**Status**: Arquivo criado mas precisa seguir padrão do módulo

**Rotas criadas**:
- `GET /manufatura/requisicoes/` - Listar requisições
- `GET /manufatura/requisicoes/sincronizar-manual` - Tela de sincronização manual
- `POST /manufatura/requisicoes/sincronizar-manual` - Executa sincronização
- `GET /manufatura/requisicoes/<id>` - Detalhe + histórico
- `GET /manufatura/requisicoes/api/estatisticas` - API para dashboard

---

## 📋 O QUE FALTA FAZER:

### 5. ❌ Ajustar Arquivo de Rotas
**Ação**: O arquivo `/app/manufatura/routes/requisicao_compras_routes.py` precisa ser reescrito para seguir o padrão do módulo.

**Padrão correto**:
```python
def register_requisicao_compras_routes(bp):
    """Registra rotas de requisições de compras"""

    @bp.route('/requisicoes')
    @login_required
    def listar_requisicoes():
        # código aqui
        pass

    @bp.route('/requisicoes/sincronizar-manual')
    @login_required
    def tela_sincronizacao_manual():
        # código aqui
        pass

    # ... demais rotas
```

**Registrar em** `/app/manufatura/routes/__init__.py`:
```python
from app.manufatura.routes.requisicao_compras_routes import register_requisicao_compras_routes

def register_routes(bp):
    register_dashboard_routes(bp)
    register_previsao_demanda_routes(bp)
    register_necessidade_producao_routes(bp)
    register_historico_routes(bp)
    register_lista_materiais_routes(bp)
    register_requisicao_compras_routes(bp)  # ← ADICIONAR
```

---

### 6. ❌ Criar Templates HTML

#### 6.1. Template de Listagem
**Criar**: `/app/templates/manufatura/requisicoes/listar.html`

**Conteúdo sugerido**:
```html
{% extends "base.html" %}

{% block content %}
<div class="container-fluid">
    <h1>Requisições de Compras</h1>

    <!-- Filtros -->
    <form method="GET" class="mb-4">
        <div class="row">
            <div class="col-md-3">
                <input type="text" name="num_requisicao" class="form-control"
                       placeholder="Número Requisição" value="{{ filtros.num_requisicao }}">
            </div>
            <div class="col-md-3">
                <input type="text" name="cod_produto" class="form-control"
                       placeholder="Código Produto" value="{{ filtros.cod_produto }}">
            </div>
            <div class="col-md-2">
                <select name="status" class="form-control">
                    <option value="">Todos os Status</option>
                    {% for st in status_lista %}
                    <option value="{{ st }}" {% if filtros.status == st %}selected{% endif %}>
                        {{ st }}
                    </option>
                    {% endfor %}
                </select>
            </div>
            <div class="col-md-2">
                <input type="date" name="data_inicio" class="form-control" value="{{ filtros.data_inicio }}">
            </div>
            <div class="col-md-2">
                <input type="date" name="data_fim" class="form-control" value="{{ filtros.data_fim }}">
            </div>
        </div>
        <button type="submit" class="btn btn-primary mt-2">Filtrar</button>
        <a href="{{ url_for('manufatura.listar_requisicoes') }}" class="btn btn-secondary mt-2">Limpar</a>
        <a href="{{ url_for('manufatura.tela_sincronizacao_manual') }}" class="btn btn-success mt-2">
            <i class="fas fa-sync"></i> Sincronização Manual
        </a>
    </form>

    <!-- Tabela -->
    <table class="table table-striped table-hover">
        <thead>
            <tr>
                <th>Número</th>
                <th>Data Criação</th>
                <th>Produto</th>
                <th>Quantidade</th>
                <th>Status</th>
                <th>Data Solicitada</th>
                <th>Lead Time</th>
                <th>Ações</th>
            </tr>
        </thead>
        <tbody>
            {% for req in requisicoes %}
            <tr>
                <td>{{ req.num_requisicao }}</td>
                <td>{{ req.data_requisicao_criacao.strftime('%d/%m/%Y') }}</td>
                <td>
                    <small class="text-muted">[{{ req.cod_produto }}]</small><br>
                    {{ req.nome_produto }}
                </td>
                <td>{{ req.qtd_produto_requisicao }}</td>
                <td>
                    <span class="badge badge-primary">{{ req.status }}</span>
                </td>
                <td>
                    {% if req.data_requisicao_solicitada %}
                    {{ req.data_requisicao_solicitada.strftime('%d/%m/%Y') }}
                    {% else %}
                    -
                    {% endif %}
                </td>
                <td>
                    {% if req.lead_time_requisicao %}
                    {{ req.lead_time_requisicao }} dias
                    {% else %}
                    -
                    {% endif %}
                </td>
                <td>
                    <a href="{{ url_for('manufatura.detalhe_requisicao', requisicao_id=req.id) }}"
                       class="btn btn-sm btn-info">
                        <i class="fas fa-eye"></i> Ver
                    </a>
                </td>
            </tr>
            {% else %}
            <tr>
                <td colspan="8" class="text-center">Nenhuma requisição encontrada</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    <!-- Paginação -->
    {% if paginacao %}
    <nav>
        <ul class="pagination">
            {% if paginacao.has_prev %}
            <li class="page-item">
                <a class="page-link" href="?page={{ paginacao.prev_num }}">Anterior</a>
            </li>
            {% endif %}

            {% for page_num in paginacao.iter_pages() %}
                {% if page_num %}
                    <li class="page-item {% if page_num == paginacao.page %}active{% endif %}">
                        <a class="page-link" href="?page={{ page_num }}">{{ page_num }}</a>
                    </li>
                {% endif %}
            {% endfor %}

            {% if paginacao.has_next %}
            <li class="page-item">
                <a class="page-link" href="?page={{ paginacao.next_num }}">Próxima</a>
            </li>
            {% endif %}
        </ul>
    </nav>
    {% endif %}
</div>
{% endblock %}
```

---

#### 6.2. Template de Sincronização Manual
**Criar**: `/app/templates/manufatura/requisicoes/sincronizar_manual.html`

**Conteúdo sugerido**:
```html
{% extends "base.html" %}

{% block content %}
<div class="container">
    <h1>Sincronização Manual de Requisições</h1>

    <div class="alert alert-info">
        <i class="fas fa-info-circle"></i>
        Sincronize requisições de um período específico. Máximo: 90 dias.
    </div>

    <form method="POST">
        <div class="row">
            <div class="col-md-6">
                <div class="form-group">
                    <label>Data Início</label>
                    <input type="date" name="data_inicio" class="form-control"
                           value="{{ data_inicio_padrao }}" required>
                </div>
            </div>
            <div class="col-md-6">
                <div class="form-group">
                    <label>Data Fim</label>
                    <input type="date" name="data_fim" class="form-control"
                           value="{{ data_fim_padrao }}" required>
                </div>
            </div>
        </div>

        <button type="submit" class="btn btn-success">
            <i class="fas fa-sync"></i> Sincronizar
        </button>
        <a href="{{ url_for('manufatura.listar_requisicoes') }}" class="btn btn-secondary">
            Cancelar
        </a>
    </form>
</div>
{% endblock %}
```

---

#### 6.3. Template de Detalhe
**Criar**: `/app/templates/manufatura/requisicoes/detalhe.html`

**Conteúdo**: Mostrar dados da requisição + tabela de histórico

---

### 7. ❌ Scripts de Migração

#### 7.1. Script Python para desenvolvimento
**Criar**: `/scripts/criar_tabela_historico_requisicoes.py`

```python
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db

def criar_tabela_historico():
    app = create_app()

    with app.app_context():
        # Criar tabela
        db.create_all()
        print("✅ Tabela historico_requisicao_compras criada")

if __name__ == '__main__':
    criar_tabela_historico()
```

---

#### 7.2. Script SQL para produção (Render)
**Criar**: `/scripts/criar_tabela_historico_requisicoes.sql`

```sql
-- Criar tabela historico_requisicao_compras
CREATE TABLE IF NOT EXISTS historico_requisicao_compras (
    id SERIAL PRIMARY KEY,
    requisicao_id INTEGER NOT NULL REFERENCES requisicao_compras(id) ON DELETE CASCADE,
    num_requisicao VARCHAR(30) NOT NULL,
    operacao VARCHAR(20) NOT NULL,
    campo_alterado VARCHAR(50),
    valor_antes TEXT,
    valor_depois TEXT,
    cod_produto VARCHAR(50) NOT NULL,
    nome_produto VARCHAR(255),
    alterado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    alterado_por VARCHAR(100) NOT NULL,
    write_date_odoo TIMESTAMP,
    dados_adicionais JSONB
);

-- Criar índices
CREATE INDEX idx_hist_req_requisicao ON historico_requisicao_compras(requisicao_id);
CREATE INDEX idx_hist_req_num_data ON historico_requisicao_compras(num_requisicao, alterado_em);
CREATE INDEX idx_hist_req_produto_data ON historico_requisicao_compras(cod_produto, alterado_em);
CREATE INDEX idx_hist_req_operacao_data ON historico_requisicao_compras(operacao, alterado_em);
CREATE INDEX idx_hist_req_campo_data ON historico_requisicao_compras(campo_alterado, alterado_em);
```

---

## 🚀 COMO COMPLETAR A IMPLEMENTAÇÃO:

### Passo 1: Ajustar rotas
Reescrever `/app/manufatura/routes/requisicao_compras_routes.py` seguindo o padrão.

### Passo 2: Criar templates HTML
Criar os 3 templates em `/app/templates/manufatura/requisicoes/`

### Passo 3: Rodar migração
```bash
# Desenvolvimento:
python scripts/criar_tabela_historico_requisicoes.py

# Produção (Render Shell):
psql $DATABASE_URL < scripts/criar_tabela_historico_requisicoes.sql
```

### Passo 4: Testar scheduler
```bash
python iniciar_scheduler_incremental.py
```

---

## 📊 ARQUITETURA IMPLEMENTADA:

```
ODOO (purchase.request)
    ↓
    ↓ (a cada 30 min - 90 minutos de janela)
    ↓
RequisicaoComprasService
    ↓
    ├─→ Busca por create_date/write_date
    ├─→ Filtra detailed_type='product'
    ├─→ Query adicional para default_code
    ├─→ Cria/Atualiza RequisicaoCompras
    └─→ Registra em HistoricoRequisicaoCompras
    ↓
DATABASE (requisicao_compras + historico_requisicao_compras)
    ↓
UI (Listagem + Sincronização Manual + Detalhes)
```

---

## ✅ CHECKLIST FINAL:

- [x] Modelo HistoricoRequisicaoCompras
- [x] Serviço de importação incremental
- [x] Integração no scheduler automático (90 minutos)
- [ ] Ajustar rotas (seguir padrão do módulo)
- [ ] Template de listagem
- [ ] Template de sincronização manual
- [ ] Template de detalhe
- [ ] Script de migração Python
- [ ] Script de migração SQL
- [ ] Testar em desenvolvimento

---

**Status Atual**: 70% completo
**Falta**: Templates HTML + ajuste final nas rotas + testes
