# Permission System Quick Start Guide

## 🚀 5-Minute Setup

### 1. Check Your Permissions

```python
from flask_login import current_user

# Quick check
if current_user.tem_permissao('vendas', 'visualizar'):
    # User can view sales module
    pass

# Check edit permission
if current_user.pode_editar('vendas', 'pedidos'):
    # User can edit orders
    pass
```

### 2. Protect Your Routes

```python
from app.permissions.decorators import require_permission

@app.route('/sales/orders')
@require_permission('vendas.pedidos')
def orders_list():
    # Only users with vendas.pedidos permission can access
    return render_template('orders.html')

@app.route('/sales/orders/edit/<id>')
@require_permission('vendas.pedidos', require_edit=True)
def edit_order(id):
    # Only users with edit permission can access
    return render_template('edit_order.html')
```

### 3. Filter Data by User's Vendors/Teams

```python
from app.permissions.decorators import filter_by_user_access

@app.route('/api/orders')
@require_permission('vendas.visualizar')
def get_orders():
    # Automatically filtered by user's vendors/teams
    orders = filter_by_user_access(Order.query).all()
    return jsonify([o.to_dict() for o in orders])
```

## 📝 Common Tasks

### Add Permission to User

```python
from app.permissions.services import PermissionService

# Grant single permission
PermissionService.grant_permission(
    user_id=123,
    module='vendas',
    function='criar_pedido',
    granted_by=current_user.id
)
```

### Apply Role Template

```python
# Get user and template
user = Usuario.query.get(user_id)
template = PermissionTemplate.query.filter_by(nome="Vendedor").first()

# Apply template
user.apply_permission_template(template.id)
```

### Add User to Vendor/Team

```python
# Add to vendor
user.add_vendor("Vendor ABC")

# Add to sales team  
user.add_sales_team("Equipe Sul")

# User will now see data from these vendors/teams
```

## 🎯 Frontend Integration

### Check Permissions in Templates

```html
<!-- Jinja2 template -->
{% if current_user.tem_permissao('vendas', 'criar') %}
    <button class="btn btn-primary">Create Order</button>
{% endif %}

{% if current_user.pode_editar('vendas', 'pedidos') %}
    <button class="btn btn-warning">Edit</button>
{% endif %}
```

### JavaScript Permission Check

```javascript
// Check permission via API
fetch('/api/v1/permissions/check', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        module: 'vendas',
        function: 'visualizar'
    })
})
.then(response => response.json())
.then(data => {
    if (data.has_permission) {
        // Show feature
    }
});
```

## 🔧 Debug Helpers

### Check All User Permissions

```python
# In a debug route or shell
user = Usuario.query.get(user_id)
permissions = user.get_all_permissions()

for perm in permissions:
    print(f"{perm['module']}.{perm['function']}: "
          f"View={perm['can_view']}, Edit={perm['can_edit']}")
```

### View User's Access

```python
# Check vendors and teams
print(f"Vendors: {user.get_vendors()}")
print(f"Teams: {user.get_sales_teams()}")

# Check specific module access
module_perms = user.get_permissions_for_module('vendas')
print(f"Sales permissions: {module_perms}")
```

## ⚡ Performance Tips

### 1. Use Caching

```python
# Permissions are automatically cached for 5 minutes
# Force refresh if needed
from app.permissions.services import PermissionService
PermissionService.clear_user_cache(user_id)
```

### 2. Batch Operations

```python
# Grant multiple permissions at once
PermissionService.batch_grant_permissions(
    user_ids=[1, 2, 3, 4, 5],
    module='vendas',
    functions=['visualizar', 'criar', 'editar'],
    granted_by=current_user.id
)
```

### 3. Use Templates for Common Roles

```python
# Create reusable templates
template = PermissionTemplate(
    nome="Sales Manager",
    dados_template={
        "modules": {
            "vendas": {"view": True, "edit": True},
            "relatorios": {"view": True, "edit": False}
        }
    }
)
db.session.add(template)
db.session.commit()
```

## 🛠️ Useful Decorators

```python
# Require any permission from a list
@require_any_permission(['vendas.visualizar', 'admin.vendas'])
def flexible_route():
    pass

# Require all permissions
@require_all_permissions(['vendas.visualizar', 'vendas.editar'])
def restricted_route():
    pass

# Custom permission check
@require_custom_permission
def custom_check(user):
    return user.is_manager() and user.has_vendor("ABC Corp")
```

## 📊 Permission Hierarchy

```
Category (e.g., "Vendas")
  └── Module (e.g., "Pedidos")
      └── Function (e.g., "Criar", "Editar", "Excluir")
```

- **Category**: Broad area of the system
- **Module**: Specific feature set
- **Function**: Individual actions

## 🔍 Quick Reference

### Permission Check Methods

| Method | Description | Example |
|--------|-------------|---------|
| `tem_permissao()` | Check view permission | `user.tem_permissao('vendas', 'pedidos')` |
| `pode_editar()` | Check edit permission | `user.pode_editar('vendas', 'pedidos')` |
| `tem_acesso_modulo()` | Check module access | `user.tem_acesso_modulo('vendas')` |
| `get_modulos_permitidos()` | List allowed modules | `modules = user.get_modulos_permitidos()` |

### Decorator Reference

| Decorator | Usage | Description |
|-----------|-------|-------------|
| `@require_permission()` | `@require_permission('module.function')` | Basic permission check |
| `@require_edit_permission()` | `@require_edit_permission('module.function')` | Requires edit access |
| `@require_any_permission()` | `@require_any_permission(['perm1', 'perm2'])` | Any of the listed |
| `@require_all_permissions()` | `@require_all_permissions(['perm1', 'perm2'])` | All of the listed |

## 🚨 Common Gotchas

1. **Edit implies View**: If a user has edit permission, they automatically have view permission
2. **Cache Delay**: Permission changes may take up to 5 minutes to reflect (or clear cache)
3. **Vendor Filtering**: Data is automatically filtered - no need to add WHERE clauses
4. **Template Override**: Applying a template replaces ALL existing permissions

## 📚 Next Steps

- Read the [full integration guide](PERMISSIONS_INTEGRATION_GUIDE.md) for detailed information
- Check [API documentation](app/permissions/routes.py) for all endpoints
- See [test examples](app/permissions/tests/) for more usage patterns
- Review [migration guide](migrations/upgrade_permissions_system.py) for database changes

---

Need help? Check the troubleshooting section in the full guide or contact the development team.