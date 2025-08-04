# Sistema Unificado de Permissões

## Visão Geral

O novo sistema unificado de permissões fornece um decorador único e flexível (`@check_permission`) que suporta tanto o sistema legado quanto verificações hierárquicas avançadas, com cache integrado e auditoria completa.

## Características Principais

- ✅ **Decorador Único**: `@check_permission` para todas as necessidades
- ✅ **Verificação Hierárquica**: Categoria → Módulo → Submódulo → Função
- ✅ **Cache Multi-nível**: Memória (L1), Redis (L2), Banco (L3)
- ✅ **Auditoria Completa**: Todos os acessos são registrados
- ✅ **Compatibilidade**: Funciona com código legado existente
- ✅ **Performance**: Cache inteligente com invalidação seletiva
- ✅ **Flexibilidade**: Validadores customizados e permissões alternativas

## Instalação

1. Os arquivos já foram criados em `app/permissions/`:
   - `decorators_unified.py` - Sistema principal de decoradores
   - `cache_unified.py` - Sistema de cache otimizado
   - `utils_unified.py` - Utilitários e helpers

2. Para usar no seu código:

```python
from app.permissions.decorators_unified import check_permission
```

## Uso Básico

### Verificação Simples de Módulo

```python
@app.route('/faturamento')
@login_required
@check_permission(module='faturamento')
def listar_faturas():
    return render_template('faturamento/listar.html')
```

### Verificação com Ação Específica

```python
@app.route('/usuarios/<int:id>/editar')
@login_required
@check_permission(module='usuarios', action='edit')
def editar_usuario(id):
    # Apenas usuários com permissão de edição
    return render_template('usuarios/editar.html')
```

### Verificação Hierárquica Completa

```python
@app.route('/financeiro/faturamento/faturas/aprovar/<int:id>')
@login_required
@check_permission(
    category='financeiro',
    module='faturamento', 
    submodule='faturas',
    function='aprovar',
    action='edit'
)
def aprovar_fatura(id):
    # Verificação em todos os níveis hierárquicos
    return "Fatura aprovada!"
```

## Uso Avançado

### Permissões Alternativas

```python
@app.route('/relatorios/vendas')
@login_required
@check_permission(
    module='relatorios',
    allow_if_any=['administrador', 'gerente', 'vendedor']
)
def relatorio_vendas():
    # Acesso permitido para qualquer um dos perfis
    return render_template('relatorios/vendas.html')
```

### Validador Customizado

```python
def vendedor_ativo(user):
    """Verifica se é vendedor ativo"""
    return user.perfil == 'vendedor' and user.ativo

@app.route('/vendas/criar')
@login_required
@check_permission(
    module='vendas',
    custom_validator=vendedor_ativo,
    message="Apenas vendedores ativos podem criar vendas"
)
def criar_venda():
    return render_template('vendas/criar.html')
```

### Respostas JSON para APIs

```python
@app.route('/api/usuarios')
@login_required
@check_permission(
    module='api',
    function='usuarios',
    json_response=True,
    redirect_on_fail=False
)
def api_usuarios():
    return jsonify({'usuarios': [....]})
```

### Controle de Cache

```python
# Cache por 10 minutos
@check_permission(
    module='relatorios',
    use_cache=True,
    cache_ttl=600
)
def relatorio_pesado():
    pass

# Sem cache (sempre verifica)
@check_permission(
    module='seguranca',
    use_cache=False
)
def area_critica():
    pass
```

### Auditoria Detalhada

```python
@check_permission(
    module='financeiro',
    function='transferencia',
    audit_level='detailed'  # 'minimal', 'normal', 'detailed'
)
def transferencia_bancaria():
    # Todas as informações são logadas
    pass
```

## Uso em Templates

### Verificação Simples

```jinja2
{% if can_access('faturamento') %}
    <a href="/faturamento">Acessar Faturamento</a>
{% endif %}
```

### Verificação com Ação

```jinja2
{% if can_access('usuarios', action='edit') %}
    <button onclick="editarUsuario()">Editar</button>
{% endif %}
```

### Verificação Hierárquica

```jinja2
{% if can_access(category='financeiro', module='relatorios', function='gerar') %}
    <a href="/relatorios/financeiro">Gerar Relatório</a>
{% endif %}
```

### Menu Dinâmico

```jinja2
<nav>
    {% if can_access('dashboard') %}
        <li><a href="/dashboard">Dashboard</a></li>
    {% endif %}
    
    {% if can_access('vendas') %}
        <li class="dropdown">
            <a href="#">Vendas</a>
            <ul>
                {% if can_access('vendas', function='listar') %}
                    <li><a href="/vendas">Listar</a></li>
                {% endif %}
                {% if can_access('vendas', function='criar', action='edit') %}
                    <li><a href="/vendas/nova">Nova Venda</a></li>
                {% endif %}
            </ul>
        </li>
    {% endif %}
</nav>
```

## Cache de Permissões

### Como Funciona

O sistema usa cache em 3 níveis:

1. **L1 - Memória (LRU)**: Mais rápido, limitado a 1000 entradas
2. **L2 - Redis**: Compartilhado entre processos
3. **L3 - Banco de Dados**: Persistente, mais lento

### Invalidação de Cache

```python
from app.permissions.decorators_unified import invalidate_user_cache, invalidate_all_cache

# Invalidar cache de um usuário
invalidate_user_cache(user_id=123)

# Invalidar todo o cache
invalidate_all_cache()
```

### Estatísticas de Cache

```python
from app.permissions.cache_unified import UnifiedPermissionCache

cache = UnifiedPermissionCache()
stats = cache.get_stats()

# Retorna:
{
    'total_requests': 1000,
    'memory_cache': {
        'size': 245,
        'hits': 800,
        'misses': 200,
        'hit_rate': '80.00%'
    },
    'hit_rates': {
        'l1': '60.00%',
        'l2': '30.00%', 
        'l3': '5.00%',
        'overall': '95.00%'
    }
}
```

## Auditoria

Todos os acessos são registrados automaticamente:

```python
from app.permissions.utils_unified import AuditLogger

audit = AuditLogger()

# Buscar logs de acesso
logs = audit.get_access_logs(
    user_id=123,
    module='faturamento',
    start_date=datetime(2024, 1, 1),
    success_only=True,
    limit=100
)
```

## Migração do Sistema Legado

### Código Legado

```python
# Antes
@requer_permissao('faturamento')
def listar():
    pass

@requer_edicao('faturamento')
def editar():
    pass
```

### Código Novo

```python
# Depois
@check_permission(module='faturamento')
def listar():
    pass

@check_permission(module='faturamento', action='edit')
def editar():
    pass
```

### Modo de Compatibilidade

```python
# Força uso do sistema legado
@check_permission(module='faturamento', legacy_mode=True)
def funcao_legada():
    pass
```

## Melhores Práticas

### 1. Use Hierarquia Quando Possível

```python
# ❌ Evite
@check_permission(module='faturamento')

# ✅ Prefira
@check_permission(
    category='financeiro',
    module='faturamento',
    submodule='faturas'
)
```

### 2. Seja Específico com Ações

```python
# ❌ Genérico demais
@check_permission(module='usuarios')

# ✅ Específico
@check_permission(module='usuarios', action='delete')
```

### 3. Use Cache Inteligentemente

```python
# Operações frequentes: cache longo
@check_permission(module='dashboard', cache_ttl=3600)

# Operações críticas: sem cache
@check_permission(module='seguranca', use_cache=False)
```

### 4. Mensagens de Erro Claras

```python
@check_permission(
    module='financeiro',
    action='edit',
    message='Você precisa de permissão financeira para realizar esta operação'
)
```

### 5. Auditoria para Operações Críticas

```python
@check_permission(
    module='usuarios',
    action='delete',
    audit_level='detailed'
)
```

## Troubleshooting

### Cache não está funcionando

1. Verifique se o Redis está configurado:
   ```python
   REDIS_URL = os.environ.get('REDIS_URL')
   ```

2. Verifique as estatísticas:
   ```python
   stats = cache.get_stats()
   print(stats)
   ```

### Permissões não estão sendo aplicadas

1. Verifique se o usuário está autenticado:
   ```python
   @login_required
   @check_permission(...)
   ```

2. Verifique o log de auditoria para entender negações

### Performance lenta

1. Ative o cache:
   ```python
   @check_permission(use_cache=True, cache_ttl=600)
   ```

2. Use Redis para cache compartilhado entre processos

## Exemplos Completos

Veja o arquivo `examples_unified.py` para exemplos detalhados de todos os recursos.

## Suporte

Para dúvidas ou problemas:
1. Verifique os logs de auditoria
2. Consulte as estatísticas de cache
3. Use o modo `audit_level='detailed'` para debug