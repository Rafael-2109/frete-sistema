# 📋 PROGRESSO DA IMPLEMENTAÇÃO - SISTEMA MOTOCHEFE

**Data**: Outubro 2025
**Status**: Em andamento

---

## ✅ CONCLUÍDO

### 1. **Modelo Usuario Atualizado**
- ✅ Adicionados campos `sistema_logistica` e `sistema_motochefe`
- ✅ Métodos `pode_acessar_logistica()` e `pode_acessar_motochefe()`
- ✅ Arquivo: [app/auth/models.py](../auth/models.py)

### 2. **Forms Atualizados**
- ✅ `AprovarUsuarioForm` com checkboxes dos sistemas
- ✅ `EditarUsuarioForm` com checkboxes dos sistemas
- ✅ Arquivo: [app/auth/forms.py](../auth/forms.py)

### 3. **Rotas Criadas/Atualizadas**
- ✅ `/auth/registro` - Sistema Logística (default)
- ✅ `/auth/registro-motochefe` - Sistema MotoChefe (novo)
- ✅ Função `aprovar_usuario()` atualizada para incluir campos
- ✅ Arquivo: [app/auth/routes.py](../auth/routes.py)

### 4. **SQL de Migração**
- ✅ Script criado: [scripts/add_sistema_fields_usuario.sql](scripts/add_sistema_fields_usuario.sql)
- ⚠️ **EXECUTAR NO RENDER**

---

## ⏳ PENDENTE

### 1. **Templates HTML - Atualizar**

#### A. `aprovar_usuario.html` - Adicionar checkboxes
```html
<!-- Adicionar após linha 74 (após vendedor_vinculado): -->
<div class="row mb-3">
    <div class="col-md-12">
        <label class="form-label"><i class="fas fa-desktop"></i> Sistemas Permitidos:</label>
        <div class="card bg-light">
            <div class="card-body">
                <div class="form-check">
                    {{ form.sistema_logistica(class="form-check-input", id="sistemaLogistica") }}
                    {{ form.sistema_logistica.label(class="form-check-label", for="sistemaLogistica") }}
                </div>
                <div class="form-check mt-2">
                    {{ form.sistema_motochefe(class="form-check-input", id="sistemaMotochefe") }}
                    {{ form.sistema_motochefe.label(class="form-check-label", for="sistemaMotochefe") }}
                </div>
            </div>
        </div>
    </div>
</div>
```

#### B. `editar_usuario.html` - Mesmo código acima
#### C. `usuarios_pendentes.html` - Mostrar badge do sistema solicitado

### 2. **Base.html - Navbar Dinâmico**

Localizar: `app/templates/base.html`

#### Alterar Título:
```html
<!-- ANTES -->
<a class="navbar-brand" href="/">Logística Nacom Goya</a>

<!-- DEPOIS -->
<a class="navbar-brand" href="/">
    {% if current_user.is_authenticated %}
        {% if current_user.sistema_motochefe and not current_user.sistema_logistica %}
        Sistema MotoChefe
        {% else %}
        Logística Nacom Goya
        {% endif %}
    {% else %}
    Logística Nacom Goya
    {% endif %}
</a>
```

#### Adicionar Dropdown MotoChefe:
```html
<!-- Adicionar após <ul class="navbar-nav me-auto mb-2 mb-lg-0"> -->
{% if current_user.is_authenticated and current_user.pode_acessar_motochefe() %}
<li class="nav-item dropdown">
    <a class="nav-link dropdown-toggle" href="#" id="navbarMotochefe" role="button"
       data-bs-toggle="dropdown" aria-expanded="false">
        <i class="fas fa-motorcycle"></i> MotoChefe
    </a>
    <ul class="dropdown-menu" aria-labelledby="navbarMotochefe">
        <li><h6 class="dropdown-header">Cadastros Básicos</h6></li>
        <li><a class="dropdown-item" href="{{ url_for('motochefe.listar_equipes') }}">
            <i class="fas fa-users"></i> Equipes de Vendas
        </a></li>
        <li><a class="dropdown-item" href="{{ url_for('motochefe.listar_vendedores') }}">
            <i class="fas fa-user-tie"></i> Vendedores
        </a></li>
        <li><a class="dropdown-item" href="{{ url_for('motochefe.listar_transportadoras') }}">
            <i class="fas fa-truck"></i> Transportadoras
        </a></li>
        <li><a class="dropdown-item" href="{{ url_for('motochefe.listar_clientes') }}">
            <i class="fas fa-building"></i> Clientes
        </a></li>
        <li><hr class="dropdown-divider"></li>
        <li><h6 class="dropdown-header">Produtos</h6></li>
        <li><a class="dropdown-item" href="{{ url_for('motochefe.listar_modelos') }}">
            <i class="fas fa-motorcycle"></i> Modelos de Motos
        </a></li>
        <li><hr class="dropdown-divider"></li>
        <li><h6 class="dropdown-header">Operacional</h6></li>
        <li><a class="dropdown-item" href="{{ url_for('motochefe.custos_operacionais') }}">
            <i class="fas fa-dollar-sign"></i> Custos Operacionais
        </a></li>
    </ul>
</li>
{% endif %}
```

### 3. **Login.html - Links de Cadastro**

Localizar: `app/templates/auth/login.html`

```html
<!-- Adicionar após o form de login: -->
<div class="text-center mt-3">
    <p class="text-muted">Não tem acesso?</p>
    <div class="d-grid gap-2">
        <a href="{{ url_for('auth.registro') }}" class="btn btn-outline-primary btn-sm">
            <i class="fas fa-user-plus"></i> Solicitar Acesso - Sistema Logística
        </a>
        <a href="{{ url_for('auth.registro_motochefe') }}" class="btn btn-outline-success btn-sm">
            <i class="fas fa-motorcycle"></i> Solicitar Acesso - Sistema MotoChefe
        </a>
    </div>
</div>
```

### 4. **Criar Blueprint Motochefe**

Criar: `app/motochefe/routes/__init__.py`

```python
from flask import Blueprint

motochefe_bp = Blueprint('motochefe', __name__, url_prefix='/motochefe')

# Importar rotas depois de criar blueprint
from . import cadastros, produtos, operacional
```

### 5. **Registrar Blueprint no app/__init__.py**

```python
# Adicionar após outros blueprints:
from app.motochefe.routes import motochefe_bp
app.register_blueprint(motochefe_bp)
```

---

## 📁 PRÓXIMOS PASSOS

### FASE 1: Completar Autenticação (URGENTE)
1. ✅ Executar SQL no Render: `add_sistema_fields_usuario.sql`
2. ⏳ Atualizar templates HTML (aprovar, editar, login)
3. ⏳ Atualizar base.html (navbar dinâmico)

### FASE 2: CRUD Cadastros Básicos
1. ⏳ Criar rotas para Equipes, Vendedores, Transportadoras, Clientes
2. ⏳ Criar templates para listar/adicionar/editar/remover
3. ⏳ Implementar importação/exportação Excel

### FASE 3: CRUD Produtos e Operacional
1. ⏳ Criar rotas para ModeloMoto e CustosOperacionais
2. ⏳ Criar templates
3. ⏳ Implementar funcionalidades

---

## 🚀 COMANDO PARA EXECUTAR NO RENDER

```sql
-- Copiar e executar no Shell PostgreSQL do Render
\i app/motochefe/scripts/add_sistema_fields_usuario.sql
```

---

## 📝 NOTAS IMPORTANTES

1. **Navbar** mostra "MotoChefe" APENAS se usuário tem `sistema_motochefe=True` e `sistema_logistica=False`
2. **Links de cadastro** são separados: `/auth/registro` (logística) e `/auth/registro-motochefe`
3. **Dropdown MotoChefe** só aparece se `current_user.pode_acessar_motochefe()` retornar True
4. **Sistema é independente** - usar `sistema_motochefe` para controlar acesso

---

**Última atualização**: Outubro 2025
