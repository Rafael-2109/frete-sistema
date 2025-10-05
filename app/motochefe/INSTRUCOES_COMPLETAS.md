# 🚀 INSTRUÇÕES COMPLETAS - IMPLEMENTAÇÃO MOTOCHEFE

**Status**: 70% Concluído
**Última atualização**: Outubro 2025

---

## ✅ JÁ IMPLEMENTADO (70%)

### 1. **Backend Completo**
- ✅ Modelo `Usuario` com campos `sistema_logistica` e `sistema_motochefe`
- ✅ Forms (`AprovarUsuarioForm`, `EditarUsuarioForm`) atualizados
- ✅ Rotas de registro separadas (`/auth/registro` e `/auth/registro-motochefe`)
- ✅ Função `aprovar_usuario()` salvando campos
- ✅ Função `editar_usuario()` salvando campos
- ✅ SQL de migração criado

### 2. **Templates Parciais**
- ✅ `registro.html` - título dinâmico baseado no sistema
- ✅ `aprovar_usuario.html` - checkboxes adicionados + badge do sistema solicitado

---

## ⏳ FALTA FAZER (30%)

### FASE 1: COMPLETAR TEMPLATES DE AUTENTICAÇÃO

#### 1A. Atualizar `editar_usuario.html`

**Arquivo**: `app/templates/auth/editar_usuario.html`

**Adicionar após a linha com `form.status` (~linha 110)**:

```html
<!-- Sistemas Permitidos -->
<div class="row mb-3">
    <div class="col-md-12">
        <label class="form-label"><i class="fas fa-desktop"></i> Sistemas Permitidos:</label>
        <div class="card bg-light">
            <div class="card-body">
                <div class="form-check">
                    {{ form.sistema_logistica(class="form-check-input", id="sistemaLogistica") }}
                    {{ form.sistema_logistica.label(class="form-check-label", for="sistemaLogistica") }}
                    <small class="text-muted d-block">Acesso ao sistema de logística, embarques e fretes</small>
                </div>
                <div class="form-check mt-2">
                    {{ form.sistema_motochefe(class="form-check-input", id="sistemaMotochefe") }}
                    {{ form.sistema_motochefe.label(class="form-check-label", for="sistemaMotochefe") }}
                    <small class="text-muted d-block">Acesso ao sistema de gestão de motos elétricas</small>
                </div>
            </div>
        </div>
    </div>
</div>
```

---

#### 1B. Atualizar `login.html`

**Arquivo**: `app/templates/auth/login.html`

**Adicionar ANTES do `</div>` final (logo após o formulário)**:

```html
<!-- Links de Cadastro -->
<div class="text-center mt-4">
    <p class="text-muted mb-2">Não tem acesso ao sistema?</p>
    <div class="d-grid gap-2">
        <a href="{{ url_for('auth.registro') }}" class="btn btn-outline-primary btn-sm">
            <i class="fas fa-truck"></i> Solicitar Acesso - Sistema Logística
        </a>
        <a href="{{ url_for('auth.registro_motochefe') }}" class="btn btn-outline-success btn-sm">
            <i class="fas fa-motorcycle"></i> Solicitar Acesso - Sistema MotoChefe
        </a>
    </div>
</div>
```

---

#### 1C. Atualizar `base.html` - Navbar Dinâmico

**Arquivo**: `app/templates/base.html`

**PASSO 1**: Localizar a linha com `<a class="navbar-brand"`

**SUBSTITUIR**:
```html
<a class="navbar-brand" href="/">Logística Nacom Goya</a>
```

**POR**:
```html
<a class="navbar-brand" href="/">
    {% if current_user.is_authenticated %}
        {% if current_user.sistema_motochefe and not current_user.sistema_logistica %}
        <i class="fas fa-motorcycle"></i> Sistema MotoChefe
        {% else %}
        <i class="fas fa-truck"></i> Logística Nacom Goya
        {% endif %}
    {% else %}
    Logística Nacom Goya
    {% endif %}
</a>
```

**PASSO 2**: Localizar `<ul class="navbar-nav me-auto mb-2 mb-lg-0">` e **ADICIONAR APÓS**:

```html
<!-- Dropdown MotoChefe -->
{% if current_user.is_authenticated and current_user.pode_acessar_motochefe() %}
<li class="nav-item dropdown">
    <a class="nav-link dropdown-toggle" href="#" id="navbarMotochefe" role="button"
       data-bs-toggle="dropdown" aria-expanded="false">
        <i class="fas fa-motorcycle"></i> MotoChefe
    </a>
    <ul class="dropdown-menu" aria-labelledby="navbarMotochefe">
        <li><h6 class="dropdown-header"><i class="fas fa-address-book"></i> Cadastros Básicos</h6></li>
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
        <li><h6 class="dropdown-header"><i class="fas fa-box"></i> Produtos</h6></li>
        <li><a class="dropdown-item" href="{{ url_for('motochefe.listar_modelos') }}">
            <i class="fas fa-motorcycle"></i> Modelos de Motos
        </a></li>

        <li><hr class="dropdown-divider"></li>
        <li><h6 class="dropdown-header"><i class="fas fa-cog"></i> Operacional</h6></li>
        <li><a class="dropdown-item" href="{{ url_for('motochefe.custos_operacionais') }}">
            <i class="fas fa-dollar-sign"></i> Custos Operacionais
        </a></li>
    </ul>
</li>
{% endif %}
```

---

### FASE 2: EXECUTAR SQL NO RENDER

**COMANDO**:
```bash
# Copiar conteúdo de: app/motochefe/scripts/add_sistema_fields_usuario.sql
# Colar no Shell PostgreSQL do Render e executar
```

---

### FASE 3: CRIAR ESTRUTURA MOTOCHEFE (BLUEPRINT E ROTAS)

Já criei um arquivo separado com toda a estrutura. Veja:

📄 **[ESTRUTURA_ROTAS_CRUD.md](./ESTRUTURA_ROTAS_CRUD.md)** - Arquivo com:
- Blueprint completo
- Rotas CRUD para 6 tabelas
- Import/Export Excel
- Templates HTML

⚠️ **IMPORTANTE**: Este arquivo será criado no próximo passo

---

## 📋 RESUMO DO QUE FALTA

| Item | Arquivo | Status |
|------|---------|--------|
| 1. editar_usuario.html | `app/templates/auth/editar_usuario.html` | ⏳ Copiar código acima |
| 2. login.html | `app/templates/auth/login.html` | ⏳ Copiar código acima |
| 3. base.html | `app/templates/base.html` | ⏳ Copiar código acima |
| 4. SQL Render | Shell PostgreSQL | ⏳ Executar migração |
| 5. Blueprint | `app/motochefe/routes/` | ⏳ Criar estrutura |
| 6. Templates CRUD | `app/motochefe/templates/` | ⏳ Criar 18 templates |

---

## ⚡ AÇÕES IMEDIATAS

### 1. **Executar SQL** (5 minutos)
```bash
# No Render Shell:
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS sistema_logistica BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS sistema_motochefe BOOLEAN NOT NULL DEFAULT FALSE;
UPDATE usuarios SET sistema_logistica = TRUE WHERE sistema_logistica = FALSE;
```

### 2. **Atualizar 3 Templates** (10 minutos)
- Copiar código dos blocos 1A, 1B, 1C acima

### 3. **Criar Blueprint** (15 minutos)
- Aguardar próximo arquivo com estrutura completa

---

## 🎯 ORDEM DE EXECUÇÃO RECOMENDADA

1. ✅ **SQL no Render** (caso contrário dará erro)
2. ✅ **Atualizar templates** (autenticação funcional)
3. ✅ **Testar login e aprovação** (validar campos salvam)
4. ✅ **Criar blueprint motochefe** (estrutura CRUD)
5. ✅ **Criar templates CRUD** (telas de cadastro)
6. ✅ **Implementar Excel** (import/export)

---

**Continuar em**: [ESTRUTURA_ROTAS_CRUD.md](./ESTRUTURA_ROTAS_CRUD.md) (próximo arquivo)
