# Permission System UI Component Design

## Overview

This document outlines the UI/UX design for the hierarchical permission management system. The design focuses on usability, clarity, and efficiency for managing complex permission structures.

## Design Principles

1. **Visual Hierarchy**: Clear representation of Category → Module → SubModule structure
2. **Immediate Feedback**: Real-time updates with optimistic UI
3. **Bulk Operations**: Efficient management of multiple permissions
4. **Progressive Disclosure**: Show complexity only when needed
5. **Accessibility**: WCAG 2.1 AA compliance

## Component Architecture

### Main Layout Structure

```
┌─────────────────────────────────────────────────────────────────┐
│ Permission Management System                          [User Menu] │
├─────────────────────────────────────────────────────────────────┤
│ ┌─────────────┬─────────────────────────────────────────────┐  │
│ │ User Select │  Permission Tree                             │  │
│ │ & Filters   │  ┌─────────────────────────────────────────┐│  │
│ │             │  │ Category > Module > SubModule           ││  │
│ │ [User List] │  │ [Checkbox Grid and Controls]            ││  │
│ │ [Search]    │  │                                         ││  │
│ │ [Filters]   │  └─────────────────────────────────────────┘│  │
│ │             │  ┌─────────────────────────────────────────┐│  │
│ │ [Templates] │  │ Vendor/Team Associations                ││  │
│ │ [Bulk Ops]  │  └─────────────────────────────────────────┘│  │
│ └─────────────┴─────────────────────────────────────────────┘  │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ Audit Trail / Activity Log                                  ││
│ └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

## Detailed Component Specifications

### 1. User Selection Panel

```html
<div class="user-selection-panel">
  <!-- Search Bar -->
  <div class="search-container">
    <input type="text" placeholder="Search users..." />
    <button class="search-btn"><i class="icon-search"></i></button>
  </div>
  
  <!-- Filter Options -->
  <div class="filter-section">
    <select class="filter-profile">
      <option>All Profiles</option>
      <option>Admin</option>
      <option>Sales Manager</option>
      <option>Sales Rep</option>
    </select>
    
    <select class="filter-vendor">
      <option>All Vendors</option>
      <!-- Dynamic vendor list -->
    </select>
    
    <select class="filter-team">
      <option>All Teams</option>
      <!-- Dynamic team list -->
    </select>
  </div>
  
  <!-- User List -->
  <div class="user-list">
    <div class="user-item selected">
      <img src="avatar.jpg" class="user-avatar" />
      <div class="user-info">
        <span class="user-name">John Doe</span>
        <span class="user-role">Sales Manager</span>
      </div>
      <span class="permission-count">45 permissions</span>
    </div>
    <!-- More users... -->
  </div>
  
  <!-- Quick Actions -->
  <div class="quick-actions">
    <button class="btn-template">
      <i class="icon-template"></i> Apply Template
    </button>
    <button class="btn-bulk">
      <i class="icon-bulk"></i> Bulk Edit
    </button>
  </div>
</div>
```

### 2. Permission Tree Component

```jsx
// React Component Structure
const PermissionTree = () => {
  return (
    <div className="permission-tree">
      {/* Tree Header with Bulk Controls */}
      <div className="tree-header">
        <h3>Permissions for: John Doe</h3>
        <div className="bulk-controls">
          <button onClick={expandAll}>Expand All</button>
          <button onClick={collapseAll}>Collapse All</button>
          <button onClick={selectAll}>Select All View</button>
          <button onClick={clearAll}>Clear All</button>
        </div>
      </div>
      
      {/* Permission Categories */}
      <div className="permission-categories">
        <CategoryNode 
          category={category}
          userId={selectedUser.id}
          onPermissionChange={handlePermissionChange}
        />
      </div>
    </div>
  );
};
```

### 3. Category/Module/SubModule Node Design

```jsx
const PermissionNode = ({ node, level, userId }) => {
  const [expanded, setExpanded] = useState(true);
  const [permissions, setPermissions] = useState(node.permissions);
  
  return (
    <div className={`permission-node level-${level}`}>
      {/* Node Header */}
      <div className="node-header">
        <button 
          className="expand-toggle"
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? '▼' : '▶'}
        </button>
        
        <div className="node-info">
          <i className={`node-icon ${node.icon}`}></i>
          <span className="node-name">{node.display_name}</span>
          <span className="node-badge">{node.subcount} items</span>
        </div>
        
        {/* Permission Checkboxes */}
        <div className="permission-controls">
          {/* View Permission */}
          <div className="permission-group">
            <label className="checkbox-container">
              <input
                type="checkbox"
                checked={permissions.can_view}
                onChange={(e) => handleChange('can_view', e.target.checked)}
                className={permissions.inherited ? 'inherited' : ''}
              />
              <span className="checkbox-custom"></span>
              <span className="checkbox-label">View</span>
            </label>
          </div>
          
          {/* Edit Permission */}
          <div className="permission-group">
            <label className="checkbox-container">
              <input
                type="checkbox"
                checked={permissions.can_edit}
                onChange={(e) => handleChange('can_edit', e.target.checked)}
                disabled={!permissions.can_view}
                className={permissions.inherited ? 'inherited' : ''}
              />
              <span className="checkbox-custom"></span>
              <span className="checkbox-label">Edit</span>
            </label>
          </div>
          
          {/* Inheritance Override (for non-category levels) */}
          {level !== 'category' && (
            <button 
              className="override-btn"
              onClick={() => toggleOverride()}
              title="Override parent permissions"
            >
              <i className={permissions.custom_override ? 'icon-lock-open' : 'icon-lock'}></i>
            </button>
          )}
        </div>
      </div>
      
      {/* Children Nodes */}
      {expanded && node.children && (
        <div className="node-children">
          {node.children.map(child => (
            <PermissionNode
              key={child.id}
              node={child}
              level={getNextLevel(level)}
              userId={userId}
            />
          ))}
        </div>
      )}
    </div>
  );
};
```

### 4. Vendor/Team Association Component

```jsx
const VendorTeamManager = ({ userId }) => {
  return (
    <div className="vendor-team-manager">
      <div className="association-grid">
        {/* Vendors Section */}
        <div className="association-section">
          <h4>
            <i className="icon-vendor"></i> Authorized Vendors
          </h4>
          <div className="association-list">
            {vendors.map(vendor => (
              <div className="association-item" key={vendor.id}>
                <span className="item-name">{vendor.name}</span>
                <button 
                  className="remove-btn"
                  onClick={() => removeVendor(vendor.id)}
                >
                  <i className="icon-remove"></i>
                </button>
              </div>
            ))}
          </div>
          <button className="add-btn" onClick={showAddVendorModal}>
            <i className="icon-plus"></i> Add Vendor
          </button>
        </div>
        
        {/* Teams Section */}
        <div className="association-section">
          <h4>
            <i className="icon-team"></i> Sales Teams
          </h4>
          <div className="association-list">
            {teams.map(team => (
              <div className="association-item" key={team.id}>
                <span className="item-name">{team.name}</span>
                <button 
                  className="remove-btn"
                  onClick={() => removeTeam(team.id)}
                >
                  <i className="icon-remove"></i>
                </button>
              </div>
            ))}
          </div>
          <button className="add-btn" onClick={showAddTeamModal}>
            <i className="icon-plus"></i> Add Team
          </button>
        </div>
      </div>
    </div>
  );
};
```

### 5. Batch Operations Modal

```jsx
const BatchOperationsModal = ({ isOpen, onClose }) => {
  return (
    <Modal isOpen={isOpen} onClose={onClose} size="large">
      <div className="batch-operations">
        <h2>Batch Permission Update</h2>
        
        {/* User Selection */}
        <div className="batch-section">
          <h3>Select Users</h3>
          <div className="user-selection-grid">
            <div className="selection-method">
              <input type="radio" name="method" value="individual" />
              <label>Select Individual Users</label>
              <UserMultiSelect />
            </div>
            <div className="selection-method">
              <input type="radio" name="method" value="filter" />
              <label>Select by Filter</label>
              <FilterBuilder />
            </div>
          </div>
        </div>
        
        {/* Permission Selection */}
        <div className="batch-section">
          <h3>Permissions to Apply</h3>
          <div className="permission-selector">
            <select className="level-select">
              <option>Category Level</option>
              <option>Module Level</option>
              <option>SubModule Level</option>
            </select>
            <PermissionPicker />
          </div>
        </div>
        
        {/* Options */}
        <div className="batch-section">
          <h3>Options</h3>
          <label>
            <input type="checkbox" checked={options.override} />
            Override existing permissions
          </label>
          <label>
            <input type="checkbox" checked={options.notify} />
            Notify affected users
          </label>
          <label>
            <input type="checkbox" checked={options.backup} />
            Create backup before applying
          </label>
        </div>
        
        {/* Preview */}
        <div className="batch-preview">
          <h3>Preview Changes</h3>
          <div className="preview-summary">
            <p>This will affect <strong>25 users</strong></p>
            <p>Granting <strong>12 new permissions</strong></p>
            <p>Modifying <strong>8 existing permissions</strong></p>
          </div>
        </div>
        
        {/* Actions */}
        <div className="modal-actions">
          <button className="btn-cancel" onClick={onClose}>Cancel</button>
          <button className="btn-preview">Preview Details</button>
          <button className="btn-apply">Apply Changes</button>
        </div>
      </div>
    </Modal>
  );
};
```

## Visual Design System

### Color Palette

```css
:root {
  /* Primary Colors */
  --primary: #007bff;
  --primary-dark: #0056b3;
  --primary-light: #cce5ff;
  
  /* Status Colors */
  --success: #28a745;
  --warning: #ffc107;
  --danger: #dc3545;
  --info: #17a2b8;
  
  /* Permission States */
  --perm-granted: #28a745;
  --perm-denied: #dc3545;
  --perm-inherited: #6c757d;
  --perm-override: #ffc107;
  
  /* UI Colors */
  --border: #dee2e6;
  --background: #f8f9fa;
  --text-primary: #212529;
  --text-secondary: #6c757d;
}
```

### Permission Checkbox States

```css
/* Default State */
.checkbox-container {
  position: relative;
  padding-left: 24px;
  cursor: pointer;
}

.checkbox-custom {
  position: absolute;
  left: 0;
  top: 2px;
  width: 18px;
  height: 18px;
  border: 2px solid var(--border);
  border-radius: 3px;
  background: white;
  transition: all 0.2s;
}

/* Checked State */
.checkbox-container input:checked ~ .checkbox-custom {
  background: var(--perm-granted);
  border-color: var(--perm-granted);
}

.checkbox-container input:checked ~ .checkbox-custom::after {
  content: '✓';
  position: absolute;
  color: white;
  font-size: 14px;
  top: -2px;
  left: 2px;
}

/* Inherited State */
.checkbox-container input.inherited ~ .checkbox-custom {
  background: var(--perm-inherited);
  opacity: 0.7;
}

/* Disabled State */
.checkbox-container input:disabled ~ .checkbox-custom {
  background: #e9ecef;
  cursor: not-allowed;
}
```

### Tree Node Styling

```css
.permission-node {
  border: 1px solid transparent;
  margin: 2px 0;
  transition: all 0.2s;
}

.permission-node:hover {
  background: var(--background);
  border-color: var(--border);
}

/* Level-based Indentation */
.permission-node.level-category {
  margin-left: 0;
  font-weight: 600;
}

.permission-node.level-module {
  margin-left: 24px;
  font-weight: 500;
}

.permission-node.level-submodule {
  margin-left: 48px;
  font-weight: 400;
}

/* Node Header */
.node-header {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  gap: 12px;
}

.node-icon {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Permission Controls */
.permission-controls {
  display: flex;
  gap: 16px;
  margin-left: auto;
}

.permission-group {
  display: flex;
  align-items: center;
  gap: 4px;
}
```

## Interaction Patterns

### 1. Permission Toggle Logic

```javascript
function handlePermissionChange(nodeId, permissionType, value) {
  // View permission logic
  if (permissionType === 'can_view') {
    if (!value) {
      // If unchecking view, also uncheck edit
      updatePermission(nodeId, {
        can_view: false,
        can_edit: false,
        can_delete: false,
        can_export: false
      });
    } else {
      updatePermission(nodeId, { can_view: true });
    }
  }
  
  // Edit permission logic
  if (permissionType === 'can_edit') {
    if (value) {
      // If checking edit, ensure view is also checked
      updatePermission(nodeId, {
        can_view: true,
        can_edit: true
      });
    } else {
      updatePermission(nodeId, { can_edit: false });
    }
  }
}
```

### 2. Inheritance Override Pattern

```javascript
function toggleInheritanceOverride(nodeId) {
  const node = getNode(nodeId);
  
  if (node.inherit_from_parent) {
    // Show confirmation dialog
    confirm({
      title: 'Override Parent Permissions?',
      message: 'This will create custom permissions for this item, overriding any inherited settings.',
      onConfirm: () => {
        updateNode(nodeId, {
          inherit_from_parent: false,
          is_custom_override: true
        });
      }
    });
  } else {
    // Revert to inherited
    updateNode(nodeId, {
      inherit_from_parent: true,
      is_custom_override: false
    });
  }
}
```

### 3. Batch Selection Pattern

```javascript
function applyBatchSelection(level, permissionType, value) {
  const nodes = getNodesAtLevel(level);
  const updates = [];
  
  nodes.forEach(node => {
    if (!node.is_custom_override) {
      updates.push({
        id: node.id,
        [permissionType]: value
      });
    }
  });
  
  // Show preview before applying
  showBatchPreview(updates, () => {
    batchUpdatePermissions(updates);
  });
}
```

## Responsive Design

### Mobile Layout (< 768px)

```css
@media (max-width: 767px) {
  /* Stack panels vertically */
  .permission-management {
    flex-direction: column;
  }
  
  /* Simplify tree view */
  .permission-node {
    font-size: 14px;
  }
  
  .permission-controls {
    flex-direction: column;
    gap: 8px;
  }
  
  /* Use modal for user selection */
  .user-selection-panel {
    position: fixed;
    top: 0;
    left: -100%;
    width: 80%;
    height: 100%;
    transition: left 0.3s;
  }
  
  .user-selection-panel.open {
    left: 0;
  }
}
```

### Tablet Layout (768px - 1024px)

```css
@media (min-width: 768px) and (max-width: 1024px) {
  /* Adjust spacing */
  .permission-node {
    padding: 6px 10px;
  }
  
  /* Compact controls */
  .permission-controls {
    gap: 12px;
  }
}
```

## Accessibility Features

1. **Keyboard Navigation**
   - Tab through all interactive elements
   - Space to toggle checkboxes
   - Enter to expand/collapse nodes
   - Arrow keys to navigate tree

2. **Screen Reader Support**
   - Proper ARIA labels
   - Role attributes for tree structure
   - Live regions for updates

3. **Color Contrast**
   - All text meets WCAG AA standards
   - Icons have text alternatives
   - Status indicated by more than color

## Performance Optimizations

1. **Virtual Scrolling**: For large permission trees
2. **Debounced Updates**: Batch API calls
3. **Optimistic UI**: Immediate feedback
4. **Lazy Loading**: Load submodules on expand
5. **Caching**: Cache permission structure

## Future Enhancements

1. **Drag and Drop**: Reorder permissions
2. **Permission Comparison**: Compare two users
3. **Timeline View**: Permission history
4. **Smart Suggestions**: ML-based recommendations
5. **Mobile App**: Native mobile experience