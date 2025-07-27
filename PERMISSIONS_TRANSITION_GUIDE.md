# Transition Guide: Old to New Permission System

## Overview

This guide helps you transition from the old permission system to the new hierarchical system while maintaining backward compatibility.

## Key Differences

### Old System
- Fixed user profiles (perfil enum)
- Simple module/function permissions
- Single vendor per user
- No sales team association
- Limited batch operations

### New System
- Flexible permission categories
- Hierarchical permissions (Category → Module → SubModule → Function)
- Multiple vendors per user
- Multiple sales teams per user
- Comprehensive batch operations
- Permission templates
- Complete audit trail

## Migration Mapping

### User Profiles → Permission Templates

| Old Profile | New Template | Permissions Included |
|-------------|--------------|---------------------|
| `admin` | "Administrator" | All modules with full access |
| `gerente` | "Manager" | Sales, Reports, limited Admin |
| `vendedor` | "Sales Person" | Sales view/edit, Reports view |
| `usuario` | "Basic User" | Limited view permissions |

### Code Migration Examples

#### 1. Permission Checks

**Old Code:**
```python
# Check by profile
if current_user.perfil == 'admin':
    # Admin access
    
# Check module access
if current_user.tem_acesso_modulo('vendas'):
    # Has access to sales module
```

**New Code (Backward Compatible):**
```python
# Same methods still work!
if current_user.perfil == 'admin':
    # Still works
    
# New recommended way
if current_user.tem_permissao('vendas', 'visualizar'):
    # More granular control
```

#### 2. Route Protection

**Old Code:**
```python
@login_required
def admin_only():
    if current_user.perfil != 'admin':
        abort(403)
    return render_template('admin.html')
```

**New Code:**
```python
from app.permissions.decorators import require_permission

@require_permission('admin.dashboard')
def admin_only():
    # Automatically handles authorization
    return render_template('admin.html')
```

#### 3. Data Filtering

**Old Code:**
```python
# Manual vendor filtering
if current_user.vendedor:
    orders = Order.query.filter_by(vendedor=current_user.vendedor).all()
else:
    orders = Order.query.all()
```

**New Code:**
```python
from app.permissions.decorators import filter_by_user_access

# Automatic filtering by user's vendors AND teams
orders = filter_by_user_access(Order.query).all()
```

## Step-by-Step Transition

### Phase 1: Database Migration (Week 1)

1. **Run Migration Script**
   ```bash
   python migrations/upgrade_permissions_system.py
   ```

2. **Verify Migration**
   ```bash
   python scripts/verify_permissions.py
   ```

3. **Initialize Templates**
   ```python
   from app.permissions.models import inicializar_dados_padrao
   inicializar_dados_padrao()
   ```

### Phase 2: Update User Associations (Week 2)

1. **Migrate Vendor Associations**
   ```python
   # Script to migrate existing vendor associations
   from app.auth.models import Usuario
   from app import db
   
   users = Usuario.query.filter(Usuario.vendedor.isnot(None)).all()
   for user in users:
       user.add_vendor(user.vendedor)
   db.session.commit()
   ```

2. **Assign Sales Teams**
   ```python
   # Assign users to appropriate teams
   sales_users = Usuario.query.filter_by(perfil='vendedor').all()
   for user in sales_users:
       # Logic to determine team based on region/vendor
       user.add_sales_team("Equipe Sul")  # Example
   ```

### Phase 3: Apply Permission Templates (Week 3)

1. **Apply Templates by Profile**
   ```python
   from app.permissions.models import PermissionTemplate
   
   # Map profiles to templates
   profile_template_map = {
       'admin': 'Administrator',
       'gerente': 'Manager', 
       'vendedor': 'Sales Person',
       'usuario': 'Basic User'
   }
   
   for profile, template_name in profile_template_map.items():
       template = PermissionTemplate.query.filter_by(nome=template_name).first()
       users = Usuario.query.filter_by(perfil=profile).all()
       
       for user in users:
           user.apply_permission_template(template.id)
   ```

### Phase 4: Update Application Code (Week 4+)

1. **Update Decorators Gradually**
   ```python
   # Start with new modules
   @require_permission('new_module.function')
   
   # Keep old code for existing modules
   if current_user.perfil == 'admin':  # Still works
   ```

2. **Implement New Features**
   - Batch permission management UI
   - Audit log viewer
   - Template management

## Compatibility Layer

The system maintains full backward compatibility:

```python
# These old methods STILL WORK:
current_user.tem_acesso_modulo('vendas')
current_user.tem_acesso_funcao('vendas', 'visualizar')
current_user.perfil == 'admin'
current_user.vendedor  # Returns first vendor if multiple

# But you can use new methods too:
current_user.tem_permissao('vendas', 'visualizar')
current_user.pode_editar('vendas', 'pedidos')
current_user.get_vendors()  # Returns all vendors
current_user.get_sales_teams()  # New feature
```

## Testing the Transition

### 1. Unit Tests
```python
def test_backward_compatibility():
    # Old method should still work
    assert user.tem_acesso_modulo('vendas') == True
    
    # New method should give same result
    assert user.tem_permissao('vendas', 'visualizar') == True

def test_multiple_vendors():
    user.add_vendor('Vendor A')
    user.add_vendor('Vendor B')
    
    # Old property returns first vendor
    assert user.vendedor == 'Vendor A'
    
    # New method returns all
    assert len(user.get_vendors()) == 2
```

### 2. Integration Tests
```python
def test_data_filtering():
    # Create orders for different vendors
    order1 = Order(vendedor='Vendor A')
    order2 = Order(vendedor='Vendor B')
    
    # User with Vendor A should only see order1
    user.add_vendor('Vendor A')
    filtered = filter_by_user_access(Order.query).all()
    assert len(filtered) == 1
    assert filtered[0].vendedor == 'Vendor A'
```

## Common Transition Scenarios

### Scenario 1: Admin User Transition
```python
# Old system: Check if admin
if current_user.perfil == 'admin':
    show_all_data()

# Transition: Both work
if current_user.perfil == 'admin':  # Still works
    show_all_data()
    
# Or use new permission
if current_user.tem_permissao('admin', 'visualizar_tudo'):
    show_all_data()
```

### Scenario 2: Sales Team Features
```python
# Old system: No team concept
# New system: Filter by team
team_orders = Order.query.join(Usuario).join(UsuarioEquipeVendas).filter(
    UsuarioEquipeVendas.equipe_vendas == 'Team Alpha'
).all()
```

### Scenario 3: Granular Permissions
```python
# Old: All or nothing for module
if current_user.tem_acesso_modulo('vendas'):
    # Can do everything in sales

# New: Specific permissions
if current_user.tem_permissao('vendas', 'visualizar'):
    # Can view
if current_user.pode_editar('vendas', 'pedidos'):
    # Can edit orders specifically
```

## Rollback Plan

If you need to rollback:

1. **Keep Old Tables**: Migration doesn't delete old tables
2. **Compatibility Mode**: Old code continues to work
3. **Gradual Rollback**: Can rollback module by module

```python
# To rollback a specific module to old system
USE_OLD_PERMISSIONS = {
    'vendas': True,  # Use old system for sales
    'admin': False   # Use new system for admin
}

def check_permission(module, function):
    if USE_OLD_PERMISSIONS.get(module, False):
        return current_user.tem_acesso_funcao(module, function)
    else:
        return current_user.tem_permissao(module, function)
```

## Timeline Recommendations

- **Week 1**: Run migration, verify data integrity
- **Week 2**: Update user associations (vendors/teams)
- **Week 3**: Apply permission templates
- **Week 4-8**: Gradually update code module by module
- **Week 9-12**: Enable new features (batch ops, audit logs)
- **Week 13+**: Deprecate old methods (optional)

## Support During Transition

### Monitoring
```python
# Log both old and new permission checks
import logging

def permission_check_logger(user, module, function, old_method=False):
    logging.info(f"Permission check: user={user.id}, "
                f"module={module}, function={function}, "
                f"old_method={old_method}")
```

### Dual Permission Check
```python
def safe_permission_check(user, module, function):
    """Check both old and new systems during transition"""
    old_result = user.tem_acesso_funcao(module, function)
    new_result = user.tem_permissao(module, function)
    
    if old_result != new_result:
        logging.warning(f"Permission mismatch for {user.id}: "
                       f"{module}.{function} old={old_result}, "
                       f"new={new_result}")
    
    return old_result  # Use old during transition
```

## FAQ

**Q: Will the old permission checks stop working?**
A: No, all old methods are maintained for backward compatibility.

**Q: Can I transition one module at a time?**
A: Yes, the system is designed for gradual transition.

**Q: What happens to existing user permissions?**
A: They are migrated automatically by the migration script.

**Q: Can users have different permissions than their profile suggests?**
A: Yes, the new system allows complete customization beyond templates.

**Q: How do I handle custom permission logic?**
A: Use the new decorator system with custom permission functions.

---

For detailed information, see the [Integration Guide](PERMISSIONS_INTEGRATION_GUIDE.md) and [Quick Start Guide](PERMISSIONS_QUICK_START.md).