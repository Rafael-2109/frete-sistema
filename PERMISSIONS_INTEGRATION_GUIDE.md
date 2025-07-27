# Comprehensive Permission System Integration Guide

## Table of Contents

1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Migration Guide](#migration-guide)
4. [Configuration](#configuration)
5. [API Usage](#api-usage)
6. [UI Integration](#ui-integration)
7. [Common Scenarios](#common-scenarios)
8. [Troubleshooting](#troubleshooting)
9. [Deployment Checklist](#deployment-checklist)

## Overview

The new permission system provides a hierarchical, granular approach to access control with the following key features:

- **Hierarchical Structure**: Categories → Modules → SubModules → Functions
- **Flexible User Associations**: Users can belong to multiple vendors and sales teams
- **Batch Operations**: Manage permissions for multiple users at once
- **Template System**: Pre-defined permission sets for common roles
- **Complete Audit Trail**: Track all permission changes
- **Backward Compatibility**: Works with existing code

## System Architecture

### Database Structure

```
permission_category
    ├── modulo_sistema
    │   ├── sub_module
    │   └── funcao_modulo
    │       └── permissao_usuario
    │
    ├── usuario_vendedor (N:N with usuarios)
    ├── usuario_equipe_vendas (N:N with usuarios)
    ├── permission_templates
    └── batch_permission_operations
```

### Permission Resolution

Permissions are resolved hierarchically:
1. Check SubModule permission (most specific)
2. Check Module permission
3. Check Category permission (most general)
4. Default: No permission

## Migration Guide

### Step 1: Backup Your Database

```bash
# Create a backup before migration
pg_dump -h localhost -U your_user -d your_database > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Step 2: Run the Migration Script

```bash
# From the project root
python migrations/upgrade_permissions_system.py
```

This script will:
- Create new permission tables
- Migrate existing permissions
- Initialize default categories and templates
- Create indexes for performance

### Step 3: Verify Migration

```bash
# Run verification script
python scripts/verify_permissions.py
```

### Step 4: Update Application Code

The system maintains backward compatibility, but you should gradually update your code to use the new methods:

```python
# Old way (still works)
if current_user.tem_acesso_funcao('faturamento', 'visualizar'):
    # ...

# New way (recommended)
if current_user.tem_permissao('faturamento', 'visualizar'):
    # ...
```

## Configuration

### 1. Initialize Permission Categories

```python
from app.permissions.models import inicializar_dados_padrao

# Run this once to create default categories
inicializar_dados_padrao()
```

### 2. Configure Default Templates

```python
from app.permissions.models import PermissionTemplate

# Create a template for sales team
template = PermissionTemplate(
    nome="Equipe de Vendas",
    descricao="Permissões padrão para equipe de vendas",
    dados_template={
        "modules": {
            "vendas": {"view": True, "edit": True},
            "carteira": {"view": True, "edit": False},
            "faturamento": {"view": True, "edit": False}
        }
    }
)
db.session.add(template)
db.session.commit()
```

### 3. Environment Variables

Add to your `.env` file:

```bash
# Permission System Config
PERMISSION_CACHE_TTL=300  # Cache timeout in seconds
PERMISSION_AUDIT_ENABLED=true
PERMISSION_BATCH_SIZE=100  # Max users for batch operations
```

## API Usage

### 1. Check User Permissions

```python
from flask import jsonify
from flask_login import current_user
from app.permissions.decorators import require_permission

@app.route('/api/protected-resource')
@require_permission('vendas.visualizar')
def protected_endpoint():
    # User has permission
    return jsonify({"status": "authorized"})
```

### 2. Get User's Effective Permissions

```python
# Get all permissions for current user
permissions = current_user.get_all_permissions()

# Get permissions for specific module
module_perms = current_user.get_permissions_for_module('vendas')

# Check specific permission
can_edit = current_user.can_edit('vendas', 'pedidos')
```

### 3. Apply Permission Template

```python
# Apply template to user
user = Usuario.query.get(user_id)
template = PermissionTemplate.query.filter_by(nome="Vendedor").first()
user.apply_permission_template(template.id)
```

### 4. Batch Operations

```python
from app.permissions.services import PermissionService

# Grant permissions to multiple users
PermissionService.batch_grant_permissions(
    user_ids=[1, 2, 3, 4],
    module='vendas',
    functions=['visualizar', 'editar'],
    granted_by=current_user.id
)

# Apply template to multiple users
PermissionService.batch_apply_template(
    user_ids=[5, 6, 7],
    template_id=template.id,
    granted_by=current_user.id
)
```

### 5. Manage User Associations

```python
# Add vendor to user
user.add_vendor('Vendor ABC')

# Add sales team
user.add_sales_team('Team North')

# Get user's vendors
vendors = user.get_vendors()

# Remove association
user.remove_vendor('Vendor XYZ')
```

## UI Integration

### 1. Include Required Assets

```html
<!-- In your base template -->
<link rel="stylesheet" href="{{ url_for('static', filename='css/permission-manager.css') }}">
<script src="{{ url_for('static', filename='js/permission-manager.js') }}"></script>
```

### 2. Initialize Permission Manager

```javascript
document.addEventListener('DOMContentLoaded', function() {
    // Initialize the permission manager
    PermissionManager.init();
});
```

### 3. Use Permission Components

```html
<!-- User Permission Manager -->
<div id="permission-manager-root">
    <!-- Component will be rendered here -->
</div>

<!-- Quick Permission Check -->
<div class="permission-checker" 
     data-module="vendas" 
     data-function="editar">
    <!-- Content only visible if user has permission -->
</div>
```

### 4. Programmatic UI Usage

```javascript
// Check permission in JavaScript
PermissionManager.checkPermission(userId, 'vendas', 'visualizar')
    .then(hasPermission => {
        if (hasPermission) {
            // Show/enable feature
        }
    });

// Apply template to users
PermissionManager.applyTemplate({
    userIds: [1, 2, 3],
    templateId: 5,
    reason: "New team members"
});
```

## Common Scenarios

### Scenario 1: Onboarding New Sales Team Member

```python
# 1. Create user
new_user = Usuario(
    nome="João Silva",
    email="joao@empresa.com",
    perfil="vendedor"
)
db.session.add(new_user)
db.session.commit()

# 2. Assign to vendors and teams
new_user.add_vendor("Vendor Sul")
new_user.add_vendor("Vendor Norte")
new_user.add_sales_team("Equipe Regional Sul")

# 3. Apply sales template
sales_template = PermissionTemplate.query.filter_by(
    nome="Vendedor Padrão"
).first()
new_user.apply_permission_template(sales_template.id)

# 4. Add specific permissions
from app.permissions.services import PermissionService
PermissionService.grant_permission(
    user_id=new_user.id,
    module='relatorios',
    function='exportar',
    granted_by=current_user.id
)
```

### Scenario 2: Promoting User to Manager

```python
# 1. Change user profile
user = Usuario.query.get(user_id)
user.perfil = 'gerente'

# 2. Apply manager template
manager_template = PermissionTemplate.query.filter_by(
    nome="Gerente Regional"
).first()
user.apply_permission_template(manager_template.id)

# 3. Grant additional permissions
PermissionService.batch_grant_permissions(
    user_ids=[user.id],
    module='admin',
    functions=['usuarios', 'relatorios'],
    granted_by=current_user.id
)
```

### Scenario 3: Restricting Access Temporarily

```python
from datetime import datetime, timedelta

# Remove specific permission with expiry
permission = PermissaoUsuario.query.filter_by(
    usuario_id=user_id,
    modulo_id=modulo.id,
    funcao_id=funcao.id
).first()

if permission:
    permission.ativo = False
    permission.expires_at = datetime.now() + timedelta(days=30)
    permission.notes = "Temporary restriction due to audit"
    db.session.commit()
```

### Scenario 4: Bulk Permission Update

```python
# Update permissions for entire team
team_users = Usuario.query.join(UsuarioEquipeVendas).filter(
    UsuarioEquipeVendas.equipe_vendas == "Team Alpha"
).all()

user_ids = [u.id for u in team_users]

# Grant new module access
PermissionService.batch_grant_permissions(
    user_ids=user_ids,
    module='novo_modulo',
    functions=['visualizar', 'criar', 'editar'],
    granted_by=current_user.id,
    reason="New module rollout for Team Alpha"
)
```

## Troubleshooting

### Common Issues and Solutions

#### 1. User Can't Access Feature After Permission Grant

**Check Permission Resolution:**
```python
# Debug permission resolution
from app.permissions.utils import resolve_user_permission

effective_perm = resolve_user_permission(
    user_id=user.id,
    module_name='vendas',
    function_name='editar'
)
print(f"Permission granted: {effective_perm}")
```

**Clear Cache:**
```python
from app.permissions.services import PermissionService
PermissionService.clear_user_cache(user_id)
```

#### 2. Batch Operation Fails

**Check Logs:**
```python
# View recent batch operations
operations = BatchPermissionOperation.query.order_by(
    BatchPermissionOperation.performed_at.desc()
).limit(10).all()

for op in operations:
    print(f"Operation: {op.operation_type}")
    print(f"Status: {op.status}")
    print(f"Error: {op.error_details}")
```

#### 3. Migration Issues

**Verify Table Creation:**
```sql
-- Check if all tables exist
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name LIKE '%permission%';
```

**Check Migration Status:**
```python
# Run verification
python scripts/verify_permissions.py --detailed
```

#### 4. Performance Issues

**Add Missing Indexes:**
```sql
-- Add composite index for permission lookups
CREATE INDEX idx_user_module_function 
ON permissao_usuario(usuario_id, modulo_id, funcao_id, ativo);

-- Add index for vendor filtering
CREATE INDEX idx_usuario_vendedor_lookup 
ON usuario_vendedor(usuario_id, vendedor, ativo);
```

### Debug Mode

Enable debug logging for permissions:

```python
# In your app config
import logging
logging.getLogger('app.permissions').setLevel(logging.DEBUG)
```

## Deployment Checklist

### Pre-Deployment

- [ ] **Backup Production Database**
  ```bash
  pg_dump -h prod_host -U prod_user -d prod_db > backup_prod_$(date +%Y%m%d).sql
  ```

- [ ] **Test Migration on Staging**
  ```bash
  # Copy production data to staging
  # Run migration
  python migrations/upgrade_permissions_system.py
  # Run tests
  python -m pytest app/permissions/tests/
  ```

- [ ] **Review Permission Templates**
  - Verify all role templates are created
  - Test template application
  - Confirm default permissions

- [ ] **Update Environment Variables**
  ```bash
  # Add to production .env
  PERMISSION_CACHE_TTL=300
  PERMISSION_AUDIT_ENABLED=true
  ```

### Deployment Steps

1. **Deploy Code**
   ```bash
   git pull origin main
   pip install -r requirements.txt
   ```

2. **Run Migration**
   ```bash
   python migrations/upgrade_permissions_system.py
   ```

3. **Initialize Data**
   ```bash
   python init_permissions_data.py
   ```

4. **Verify Deployment**
   ```bash
   python scripts/verify_permissions.py --production
   ```

5. **Clear Application Cache**
   ```bash
   # If using Redis
   redis-cli FLUSHDB
   ```

### Post-Deployment

- [ ] **Monitor Error Logs**
  ```bash
  tail -f logs/app.log | grep -i permission
  ```

- [ ] **Check Performance Metrics**
  - Query response times
  - Cache hit rates
  - Database connection pool

- [ ] **User Acceptance Testing**
  - Test with different user roles
  - Verify data filtering works
  - Confirm UI displays correctly

- [ ] **Backup New State**
  ```bash
  pg_dump -h prod_host -U prod_user -d prod_db > backup_post_migration_$(date +%Y%m%d).sql
  ```

### Rollback Plan

If issues arise:

1. **Restore Database Backup**
   ```bash
   psql -h prod_host -U prod_user -d prod_db < backup_prod_YYYYMMDD.sql
   ```

2. **Revert Code**
   ```bash
   git revert <migration-commit>
   git push origin main
   ```

3. **Clear Cache**
   ```bash
   redis-cli FLUSHDB
   ```

4. **Restart Application**
   ```bash
   systemctl restart your-app
   ```

## Support and Maintenance

### Regular Maintenance Tasks

1. **Weekly**: Review audit logs for suspicious activity
2. **Monthly**: Analyze permission usage patterns
3. **Quarterly**: Review and update permission templates
4. **Yearly**: Archive old audit logs

### Monitoring Queries

```sql
-- Active users by module
SELECT m.nome_exibicao, COUNT(DISTINCT p.usuario_id) as user_count
FROM permissao_usuario p
JOIN modulo_sistema m ON p.modulo_id = m.id
WHERE p.ativo = true
GROUP BY m.nome_exibicao
ORDER BY user_count DESC;

-- Recent permission changes
SELECT 
    l.created_at,
    u1.nome as changed_by,
    u2.nome as affected_user,
    l.acao,
    l.detalhes
FROM log_permissao l
JOIN usuarios u1 ON l.usuario_id = u1.id
JOIN usuarios u2 ON l.usuario_afetado_id = u2.id
ORDER BY l.created_at DESC
LIMIT 50;
```

### Contact for Issues

- **Technical Issues**: Create issue in project repository
- **Security Concerns**: Contact security team immediately
- **Feature Requests**: Submit through project management system

---

This guide covers the complete integration process. For specific implementation details, refer to the source code and inline documentation.