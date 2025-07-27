# Permission System Architecture Design

## Executive Summary

This document outlines the complete architecture for a hierarchical permission system that supports:
- Three-level hierarchy: Categories → Modules → SubModules
- Checkbox-based view/edit permissions at each level
- Module permissions that override submodule permissions (with customization options)
- Users linked to multiple vendors OR multiple sales teams
- Batch permission editing capabilities
- Complete audit trail and security

## System Overview

### Core Concepts

1. **Permission Hierarchy**
   ```
   Category (e.g., "Commercial Operations")
   └── Module (e.g., "Order Management")
       └── SubModule (e.g., "Create Orders", "Edit Orders")
   ```

2. **Permission Types**
   - **View**: Read-only access to data and interfaces
   - **Edit**: Full CRUD operations on data

3. **User Associations**
   - Users can be linked to 1+ vendors (N:N relationship)
   - Users can be linked to 1+ sales teams (N:N relationship)
   - Data filtering is automatic based on these associations

4. **Permission Inheritance**
   - Module-level permissions cascade to all submodules by default
   - SubModule permissions can be customized to override module defaults
   - Category permissions affect all modules within

## Database Schema Design

### Enhanced Models Structure

```sql
-- 1. Permission Categories (NEW)
CREATE TABLE permission_categories (
    id INTEGER PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    icon VARCHAR(50),
    color VARCHAR(7),
    order_index INTEGER DEFAULT 0,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES usuarios(id)
);

-- 2. Enhanced Module System (UPDATED)
CREATE TABLE modulo_sistema (
    id INTEGER PRIMARY KEY,
    category_id INTEGER REFERENCES permission_categories(id),
    name VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    icon VARCHAR(50),
    color VARCHAR(7),
    active BOOLEAN DEFAULT TRUE,
    order_index INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. SubModules (RENAMED from funcao_modulo)
CREATE TABLE sub_modules (
    id INTEGER PRIMARY KEY,
    module_id INTEGER REFERENCES modulo_sistema(id),
    name VARCHAR(50) NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    route_pattern VARCHAR(200),
    critical_level VARCHAR(10) DEFAULT 'NORMAL',
    active BOOLEAN DEFAULT TRUE,
    order_index INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(module_id, name)
);

-- 4. User Permissions (ENHANCED)
CREATE TABLE user_permissions (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES usuarios(id),
    -- Permission can be at any level
    category_id INTEGER REFERENCES permission_categories(id),
    module_id INTEGER REFERENCES modulo_sistema(id),
    submodule_id INTEGER REFERENCES sub_modules(id),
    -- Permissions
    can_view BOOLEAN DEFAULT FALSE,
    can_edit BOOLEAN DEFAULT FALSE,
    -- Inheritance control
    inherit_from_parent BOOLEAN DEFAULT TRUE,
    is_custom_override BOOLEAN DEFAULT FALSE,
    -- Metadata
    granted_by INTEGER REFERENCES usuarios(id),
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    notes TEXT,
    active BOOLEAN DEFAULT TRUE,
    -- Ensure only one permission per user per level
    UNIQUE(user_id, category_id, module_id, submodule_id),
    -- Check that at least one level is specified
    CHECK(category_id IS NOT NULL OR module_id IS NOT NULL OR submodule_id IS NOT NULL)
);

-- 5. Batch Permission Templates (NEW)
CREATE TABLE permission_templates (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    template_data JSON NOT NULL, -- Stores permission configuration
    created_by INTEGER REFERENCES usuarios(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    active BOOLEAN DEFAULT TRUE
);

-- 6. Batch Operations Log (NEW)
CREATE TABLE batch_permission_operations (
    id INTEGER PRIMARY KEY,
    operation_type VARCHAR(50) NOT NULL, -- 'APPLY_TEMPLATE', 'BULK_UPDATE', etc.
    affected_users JSON NOT NULL, -- Array of user IDs
    changes_made JSON NOT NULL, -- Detailed changes
    performed_by INTEGER REFERENCES usuarios(id),
    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'COMPLETED',
    error_details TEXT
);

-- Indexes for performance
CREATE INDEX idx_user_permissions_hierarchy ON user_permissions(user_id, category_id, module_id, submodule_id);
CREATE INDEX idx_user_permissions_active ON user_permissions(user_id, active);
CREATE INDEX idx_modules_category ON modulo_sistema(category_id, active);
CREATE INDEX idx_submodules_module ON sub_modules(module_id, active);
```

### Permission Resolution Algorithm

```python
def resolve_user_permission(user_id, category_id, module_id, submodule_id, permission_type='view'):
    """
    Resolves effective permission considering hierarchy and inheritance
    Priority: SubModule > Module > Category
    """
    # 1. Check for explicit submodule permission
    if submodule_id:
        perm = get_permission(user_id, submodule_id=submodule_id)
        if perm and (not perm.inherit_from_parent or perm.is_custom_override):
            return getattr(perm, f'can_{permission_type}')
    
    # 2. Check for module permission
    if module_id:
        perm = get_permission(user_id, module_id=module_id)
        if perm:
            return getattr(perm, f'can_{permission_type}')
    
    # 3. Check for category permission
    if category_id:
        perm = get_permission(user_id, category_id=category_id)
        if perm:
            return getattr(perm, f'can_{permission_type}')
    
    # 4. Default: no permission
    return False
```

## API Architecture

### RESTful Endpoints

```yaml
# Permission Management APIs
/api/v1/permissions:
  # Category Level
  /categories:
    GET: List all categories with modules
    POST: Create new category
    /{id}:
      GET: Get category details
      PUT: Update category
      DELETE: Soft delete category
      /permissions:
        GET: Get all permissions for category
        POST: Set category-level permissions

  # Module Level
  /modules:
    GET: List all modules with submodules
    /{id}:
      GET: Get module details
      /permissions:
        GET: Get module permissions
        POST: Set module-level permissions
        /batch:
          POST: Apply permissions to multiple users

  # SubModule Level
  /submodules:
    GET: List all submodules
    /{id}:
      GET: Get submodule details
      /permissions:
        GET: Get submodule permissions
        POST: Set submodule-level permissions

  # User Permissions
  /users/{user_id}/permissions:
    GET: Get all user permissions (hierarchical)
    POST: Update user permissions
    /effective:
      GET: Get effective permissions (resolved)
    /vendors:
      GET: Get user's vendors
      POST: Add vendor
      DELETE: Remove vendor
    /teams:
      GET: Get user's sales teams
      POST: Add team
      DELETE: Remove team

  # Batch Operations
  /batch:
    /apply-template:
      POST: Apply permission template to multiple users
    /copy-permissions:
      POST: Copy permissions from one user to others
    /bulk-update:
      POST: Update permissions for multiple users

  # Audit
  /audit:
    GET: Get audit logs with filters
    /export:
      GET: Export audit logs (CSV/Excel)
```

### API Request/Response Examples

```json
// GET /api/v1/permissions/users/123/permissions
{
  "user": {
    "id": 123,
    "name": "John Doe",
    "email": "john@example.com"
  },
  "vendors": ["Vendor A", "Vendor B"],
  "teams": ["Sales Team 1"],
  "permissions": {
    "categories": [
      {
        "id": 1,
        "name": "commercial_ops",
        "display_name": "Commercial Operations",
        "can_view": true,
        "can_edit": false,
        "modules": [
          {
            "id": 10,
            "name": "orders",
            "display_name": "Order Management",
            "can_view": true,
            "can_edit": true,
            "inherited": false,
            "submodules": [
              {
                "id": 101,
                "name": "create_order",
                "display_name": "Create Orders",
                "can_view": true,
                "can_edit": true,
                "inherited": true
              },
              {
                "id": 102,
                "name": "cancel_order",
                "display_name": "Cancel Orders",
                "can_view": true,
                "can_edit": false,
                "inherited": false,
                "custom_override": true
              }
            ]
          }
        ]
      }
    ]
  }
}

// POST /api/v1/permissions/batch/bulk-update
{
  "user_ids": [123, 124, 125],
  "permissions": {
    "module_id": 10,
    "can_view": true,
    "can_edit": false,
    "apply_to_submodules": true
  },
  "reason": "Quarterly permission review"
}
```

## UI Component Architecture

### Component Hierarchy

```
PermissionManager (Root Component)
├── UserSelector
│   ├── UserSearch
│   └── UserInfo
├── VendorTeamManager
│   ├── VendorList
│   ├── TeamList
│   └── AssociationModal
├── PermissionTree
│   ├── CategoryNode
│   │   ├── CategoryCheckboxes
│   │   └── ModuleList
│   │       ├── ModuleNode
│   │       │   ├── ModuleCheckboxes
│   │       │   └── SubModuleList
│   │       │       └── SubModuleNode
│   │       │           └── SubModuleCheckboxes
│   └── BatchActions
│       ├── ApplyTemplate
│       ├── CopyPermissions
│       └── BulkOperations
└── AuditLog
    ├── LogFilter
    └── LogViewer
```

### React Component Example

```jsx
// PermissionNode Component
const PermissionNode = ({ node, level, userId, onChange }) => {
  const [expanded, setExpanded] = useState(true);
  const [permissions, setPermissions] = useState({
    can_view: node.can_view || false,
    can_edit: node.can_edit || false,
    inherited: node.inherited || false
  });

  const handlePermissionChange = async (type, value) => {
    const updates = { ...permissions, [type]: value };
    
    // If unchecking view, also uncheck edit
    if (type === 'can_view' && !value) {
      updates.can_edit = false;
    }
    
    // If checking edit, also check view
    if (type === 'can_edit' && value) {
      updates.can_view = true;
    }

    setPermissions(updates);
    
    // Call API to update
    await updatePermission(userId, node.id, level, updates);
    onChange(node.id, updates);
  };

  const getCheckboxState = (type) => {
    if (permissions.inherited && level !== 'category') {
      return 'inherited';
    }
    return permissions[type] ? 'checked' : 'unchecked';
  };

  return (
    <div className={`permission-node level-${level}`}>
      <div className="node-header">
        <button onClick={() => setExpanded(!expanded)}>
          {expanded ? '▼' : '▶'}
        </button>
        <span className="node-name">{node.display_name}</span>
        <div className="permission-controls">
          <PermissionCheckbox
            label="View"
            state={getCheckboxState('can_view')}
            onChange={(v) => handlePermissionChange('can_view', v)}
            disabled={permissions.inherited && level !== 'category'}
          />
          <PermissionCheckbox
            label="Edit"
            state={getCheckboxState('can_edit')}
            onChange={(v) => handlePermissionChange('can_edit', v)}
            disabled={!permissions.can_view || (permissions.inherited && level !== 'category')}
          />
          {level !== 'category' && (
            <OverrideToggle
              checked={!permissions.inherited}
              onChange={(v) => handlePermissionChange('inherited', !v)}
            />
          )}
        </div>
      </div>
      {expanded && node.children && (
        <div className="node-children">
          {node.children.map(child => (
            <PermissionNode
              key={child.id}
              node={child}
              level={getChildLevel(level)}
              userId={userId}
              onChange={onChange}
            />
          ))}
        </div>
      )}
    </div>
  );
};
```

## Security Considerations

### Access Control

1. **Permission to Manage Permissions**
   - Only users with `admin.permissions.manage` can access permission management
   - Super admins can manage all permissions
   - Department heads can manage permissions for their department only

2. **Data Filtering**
   - Automatic vendor/team filtering applied at ORM level
   - SQL injection prevention through parameterized queries
   - Input validation on all permission changes

3. **Audit Trail**
   - Every permission change is logged with:
     - Who made the change
     - When it was made
     - What was changed (before/after values)
     - IP address and user agent
     - Reason (if provided)

### Performance Optimization

1. **Caching Strategy**
   ```python
   # Redis cache keys
   user_permissions:{user_id} - TTL: 5 minutes
   effective_permissions:{user_id}:{module_id} - TTL: 5 minutes
   vendor_users:{vendor} - TTL: 10 minutes
   team_users:{team} - TTL: 10 minutes
   ```

2. **Database Optimization**
   - Composite indexes on frequently queried columns
   - Materialized views for permission resolution
   - Batch operations to reduce database round trips

3. **Frontend Optimization**
   - Virtual scrolling for large permission trees
   - Debounced API calls on checkbox changes
   - Local state management with optimistic updates

## Migration Strategy

### Phase 1: Database Migration
1. Create new tables alongside existing ones
2. Migrate existing permissions to new structure
3. Run parallel validation for 2 weeks

### Phase 2: API Migration
1. Deploy new APIs with version prefix
2. Update frontend to use new APIs
3. Maintain backwards compatibility

### Phase 3: Cleanup
1. Remove old permission tables
2. Update all references in codebase
3. Archive migration code

## Monitoring and Metrics

### Key Metrics to Track
- Permission check latency (target: <50ms)
- Cache hit rate (target: >90%)
- Failed permission checks per hour
- Batch operation success rate
- Audit log query performance

### Alerting Rules
- Permission check latency > 100ms
- Cache hit rate < 80%
- Failed permission checks > 100/hour
- Batch operation failures > 5%

## Future Enhancements

1. **Role-Based Templates**
   - Pre-defined permission sets for common roles
   - One-click role assignment

2. **Time-Based Permissions**
   - Temporary access grants
   - Scheduled permission changes

3. **Approval Workflows**
   - Permission change requests
   - Multi-level approval chains

4. **Advanced Analytics**
   - Permission usage heatmaps
   - Unused permission detection
   - Security risk scoring

## Conclusion

This architecture provides a robust, scalable, and user-friendly permission system that meets all requirements while maintaining security and performance. The hierarchical structure with inheritance provides flexibility while the batch operations enable efficient management at scale.