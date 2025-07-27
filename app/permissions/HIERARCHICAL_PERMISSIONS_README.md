# Hierarchical Permission Management System

## Overview

The Hierarchical Permission Management System provides a comprehensive interface for managing user permissions with a cascading checkbox structure. It supports three levels of hierarchy: Categories → Modules → SubModules, with granular view/edit permissions at each level.

## Features

### 1. **Cascading Permissions**
- Parent-child relationship enforcement
- Checking a parent automatically checks all children
- Unchecking view permission automatically unchecks edit permission
- Edit permission requires view permission
- Indeterminate state for partially selected parents

### 2. **User Management**
- User selection dropdown with profile information
- Real-time permission statistics
- Vendor and team associations management
- User info cards showing profile, vendor count, team count, and active permissions

### 3. **Batch Operations**
- Select all permissions at once
- Apply view-only or edit permissions in batch
- Template application for quick role-based setup
- Batch save functionality

### 4. **Visual Interface**
- Color-coded hierarchy levels
- Expandable/collapsible tree structure
- Critical level indicators (CRITICAL, HIGH, NORMAL)
- Real-time selected count badge
- Toast notifications for success/error feedback

## File Structure

```
app/
├── permissions/
│   ├── api_hierarchical.py       # API endpoints for hierarchical permissions
│   ├── initialize_hierarchy.py   # Script to create default hierarchy
│   └── models.py                # Database models
├── templates/permissions/
│   └── hierarchical_manager.html # Main UI template
└── static/
    ├── js/
    │   └── permission-hierarchical.js  # JavaScript logic
    └── css/
        └── permission-hierarchical.css # Styling
```

## API Endpoints

### User Hierarchy
- `GET /permissions/api/hierarchy/<user_id>` - Get user's permission hierarchy
- `POST /permissions/api/users/<user_id>/permissions/batch` - Update permissions in batch

### Templates
- `GET /permissions/api/templates` - List available templates
- `POST /permissions/api/users/<user_id>/permissions/template` - Apply template

### Vendors/Teams
- `GET /permissions/api/users/<user_id>/vendors` - Get user's vendors
- `POST /permissions/api/users/<user_id>/vendors` - Add vendor
- `DELETE /permissions/api/users/<user_id>/vendors/<vendor_id>` - Remove vendor
- Similar endpoints for teams

## Usage

### Accessing the Interface
Navigate to `/permissions/hierarchical-manager` to access the hierarchical permission manager.

### Managing Permissions

1. **Select a User**
   - Choose a user from the dropdown
   - View their current profile and statistics

2. **Configure Permissions**
   - Expand categories to see modules and submodules
   - Check/uncheck view and edit permissions
   - Use batch actions for quick configuration

3. **Manage Vendors/Teams**
   - Click "Adicionar" to add new vendors or teams
   - Click the trash icon to remove associations

4. **Apply Templates**
   - Click "Aplicar Template" to use predefined permission sets
   - Select a template and confirm

5. **Save Changes**
   - Click "Salvar Permissões" to persist all changes
   - View success/error messages in toast notifications

### Permission Hierarchy

```
Category (e.g., Comercial)
├── Module (e.g., Carteira de Pedidos)
│   ├── SubModule (e.g., Listar Pedidos)
│   ├── SubModule (e.g., Gerar Separação)
│   └── SubModule (e.g., Configurar Tipo de Carga)
└── Module (e.g., Monitoramento)
    ├── SubModule (e.g., Listar Entregas)
    └── SubModule (e.g., Agendar Entrega)
```

## Initialization

Run the initialization script to create default categories, modules, and templates:

```bash
python -m app.permissions.initialize_hierarchy
```

This creates:
- 4 main categories (Commercial, Financial, Operational, Administrative)
- Multiple modules under each category
- Submodules with specific functions
- Default permission templates

## Permission Rules

1. **View Permission**
   - Required for any access to the resource
   - Can be granted independently

2. **Edit Permission**
   - Requires view permission
   - Grants modification rights
   - Includes delete and export capabilities

3. **Cascading Logic**
   - Parent permissions cascade to children
   - Child permissions can override parent settings
   - Indeterminate state shows partial selection

## Security Considerations

- All operations require `usuarios.permissoes` permission
- Actions are logged in the audit trail
- Soft delete for vendor/team associations
- Permission changes tracked with timestamp and user

## Customization

### Adding New Categories/Modules
Edit `initialize_hierarchy.py` to add new hierarchy items.

### Modifying Templates
Update the `templates` array in `initialize_hierarchy.py` to create new permission templates.

### Styling
Modify `permission-hierarchical.css` to customize the appearance.

## Troubleshooting

### Common Issues

1. **Permissions not saving**
   - Check browser console for errors
   - Verify user has appropriate permissions
   - Ensure database connectivity

2. **Hierarchy not loading**
   - Run initialization script
   - Check API endpoint responses
   - Verify blueprint registration

3. **Cascading not working**
   - Clear browser cache
   - Check JavaScript console for errors
   - Verify jQuery is loaded

### Debug Mode
Enable debug logging in JavaScript:
```javascript
// In browser console
localStorage.setItem('permission_debug', 'true');
```