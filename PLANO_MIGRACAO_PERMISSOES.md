# 🔄 Plano de Migração - Sistema de Permissões Avançado

## 📋 **SITUAÇÃO ATUAL vs NOVA**

### ❌ **Sistema Antigo (Obsoleto):**
```python
# Decorators simples e limitados
@require_admin           # Apenas admin/não-admin
@require_profiles('administrador', 'gerente')  # Lista fixa
@require_permission('pode_acessar_financeiro')  # Hardcoded
```

### ✅ **Sistema Novo (Avançado):**
```python
# Sistema granular e flexível
@require_permission('faturamento', 'editar', 'editar')  # Módulo.Função.Nível
@require_profile_level(8)  # Nível hierárquico (0-10)
@require_module_access('carteira')  # Qualquer acesso ao módulo
```

## 🎯 **VANTAGENS DO SISTEMA NOVO:**

### 1. **Granularidade Total:**
- ✅ Controle por **módulo** (faturamento, carteira, estoque)
- ✅ Controle por **função** (listar, editar, exportar, importar)  
- ✅ Controle por **nível** (visualizar, editar)

### 2. **Flexibilidade Administrativa:**
- ✅ Criar novos perfis via interface (sem código)
- ✅ Criar novos módulos/funções dinamicamente
- ✅ Modificar permissões em tempo real

### 3. **Auditoria Completa:**
- ✅ Log de todas as ações de permissão
- ✅ Rastreamento de alterações
- ✅ IP e timestamp de todas as operações

## 🔧 **GUIA DE MIGRAÇÃO:**

### **ANTES (Sistema Antigo):**
```python
# app/localidades/routes.py
@localidades_bp.route('/rotas/importar')
@login_required
@require_admin
def importar_rotas():
    return render_template('localidades/importar_rotas.html')
```

### **DEPOIS (Sistema Novo):**
```python
# app/localidades/routes.py
from app.permissions.decorators import require_permission

@localidades_bp.route('/rotas/importar')
@login_required
@require_permission('localidades', 'importar', 'editar')
def importar_rotas():
    return render_template('localidades/importar_rotas.html')
```

## 📚 **EXEMPLOS PRÁTICOS:**

### 1. **Faturamento - Diferentes Níveis:**
```python
# Visualizar relatórios (vendedores podem)
@require_permission('faturamento', 'listar', 'visualizar')
def listar_faturamento():
    pass

# Editar dados (apenas gestores)
@require_permission('faturamento', 'editar', 'editar')
def editar_faturamento():
    pass

# Importar dados (apenas admin/logística)
@require_permission('faturamento', 'importar', 'editar')
def importar_faturamento():
    pass
```

### 2. **Por Nível Hierárquico:**
```python
# Apenas níveis altos (admin, gerentes)
@require_profile_level(8)
def configuracoes_sistema():
    pass

# Níveis médios e altos (incluindo supervisores)
@require_profile_level(5)
def relatorios_gerenciais():
    pass
```

### 3. **Acesso a Módulo Inteiro:**
```python
# Qualquer permissão no módulo carteira
@require_module_access('carteira')
def dashboard_carteira():
    pass
```

## 🛠️ **ESTRUTURA DOS MÓDULOS/FUNÇÕES:**

```yaml
Módulos e Funções Padrão:

faturamento:
  - listar: Visualizar relatórios
  - editar: Modificar dados
  - importar: Importar do Odoo
  - exportar: Exportar relatórios
  - processar: Processar NFs

carteira:
  - listar: Ver pedidos
  - editar: Modificar pedidos
  - separacao: Criar separações
  - agendamento: Agendar entregas
  - expedicao: Gerenciar expedições

estoque:
  - listar: Ver movimentações
  - ajustar: Ajustes de estoque
  - importar: Importar dados
  - relatorio: Relatórios de estoque

localidades:
  - listar: Ver cidades/rotas
  - editar: Modificar dados
  - importar: Importar planilhas

producao:
  - listar: Ver programação
  - editar: Modificar programação
  - palletizacao: Configurar pallets

claude_ai:
  - consultar: Fazer consultas IA
  - configurar: Configurar sistema
  - logs: Ver histórico

admin:
  - usuarios: Gerenciar usuários
  - permissoes: Gerenciar permissões
  - sistema: Configurações sistema
```

## 📝 **TEMPLATES - HELPERS DISPONÍVEIS:**

```html
<!-- Verificar permissão específica -->
{% if user_can_access('faturamento', 'editar', 'editar') %}
<button>Editar Faturamento</button>
{% endif %}

<!-- Verificar se é admin -->
{% if user_is_admin() %}
<a href="/admin">Painel Admin</a>
{% endif %}

<!-- Verificar nível do usuário -->
{% if user_level() >= 8 %}
<div>Conteúdo para gerentes+</div>
{% endif %}
```

## 🚀 **PLANO DE IMPLEMENTAÇÃO:**

### **Fase 1: Migração Gradual (Recomendado)**
1. ✅ **Manter decorators antigos funcionando**
2. ✅ **Migrar rotas críticas para sistema novo**
3. ✅ **Testar funcionalidades importantes**
4. ✅ **Migrar resto gradualmente**

### **Fase 2: Remoção do Sistema Antigo**
1. 🔄 **Remover imports de auth_decorators antigo**
2. 🔄 **Deletar auth_decorators.py**
3. 🔄 **Limpar código legado**

## ⚡ **IMPLEMENTAÇÃO IMEDIATA:**

### **1. Atualizar imports:**
```python
# ANTES
from app.utils.auth_decorators import require_admin

# DEPOIS
from app.permissions.decorators import require_admin_new as require_admin
# OU melhor ainda:
from app.permissions.decorators import require_permission
```

### **2. Trocar decorator:**
```python
# ANTES
@require_admin

# DEPOIS - Compatibilidade:
@require_admin_new

# OU MELHOR - Sistema completo:
@require_permission('admin', 'configurar', 'editar')
```

## 🎉 **BENEFÍCIOS IMEDIATOS:**

- ✅ **Controle granular** por módulo/função
- ✅ **Interface admin** para gerenciar permissões
- ✅ **Flexibilidade total** sem alteração de código
- ✅ **Auditoria completa** de todas as ações
- ✅ **Escalabilidade** para crescimento do sistema
- ✅ **Segurança aprimorada** com controle fino

## 🔄 **COMPATIBILIDADE:**

O sistema novo **mantém compatibilidade** com o antigo durante a migração:
- ✅ `@require_admin` → `@require_admin_new`
- ✅ Verificações antigas continuam funcionando
- ✅ Migração pode ser feita gradualmente
- ✅ Zero downtime durante a transição

**Recomendação: Migrar gradualmente para aproveitar todas as funcionalidades avançadas!** 🚀