# Permission System REST API Documentation

## Overview

The Permission System provides a comprehensive RESTful API for managing hierarchical permissions with categories, modules, and submodules. All endpoints follow REST principles and return consistent JSON responses.

## Base URL

```
https://api.example.com/api/v1/permissions
```

## Authentication

All endpoints (except health check) require JWT authentication:

```
Authorization: Bearer <jwt_token>
```

## Response Format

### Success Response
```json
{
  "success": true,
  "data": { ... },
  "message": "Optional success message",
  "meta": {
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

### Error Response
```json
{
  "success": false,
  "error": {
    "code": "PERMISSION_DENIED",
    "message": "You don't have permission to perform this action",
    "details": { ... }
  },
  "meta": {
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

## Endpoints

### 1. Health Check

Check API health status (no authentication required).

```http
GET /api/v1/permissions/health
```

**Response:**
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "version": "1.0.0",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

### 2. Category Management

#### List Categories

```http
GET /api/v1/permissions/categories
```

**Query Parameters:**
- `active` (boolean): Filter by active status
- `include_modules` (boolean): Include nested modules
- `include_counts` (boolean): Include module counts

**Response:**
```json
{
  "success": true,
  "data": {
    "categories": [
      {
        "id": 1,
        "name": "commercial_operations",
        "display_name": "Commercial Operations",
        "description": "Sales and order management",
        "icon": "shopping-cart",
        "color": "#28a745",
        "order_index": 1,
        "active": true,
        "module_count": 5,
        "modules": [...]
      }
    ],
    "total": 10
  }
}
```

#### Create Category

```http
POST /api/v1/permissions/categories
```

**Request Body:**
```json
{
  "name": "financial_operations",
  "display_name": "Financial Operations",
  "description": "Financial and accounting modules",
  "icon": "dollar-sign",
  "color": "#ffc107",
  "order_index": 2
}
```

### 3. Module Management

#### List Modules

```http
GET /api/v1/permissions/modules
```

**Query Parameters:**
- `category_id` (integer): Filter by category
- `active` (boolean): Filter by active status
- `include_submodules` (boolean): Include nested submodules
- `search` (string): Search in name and display_name
- `page` (integer): Page number (default: 1)
- `per_page` (integer): Results per page (default: 50, max: 100)

#### Create Module

```http
POST /api/v1/permissions/modules
```

**Request Body:**
```json
{
  "category_id": 1,
  "name": "order_management",
  "display_name": "Order Management",
  "description": "Create and manage customer orders",
  "icon": "file-text",
  "color": "#007bff",
  "order_index": 1
}
```

### 4. SubModule Management

#### List SubModules

```http
GET /api/v1/permissions/submodules
```

**Query Parameters:**
- `module_id` (integer): Filter by module
- `critical_level` (string): Filter by critical level (LOW, NORMAL, HIGH, CRITICAL)
- `active` (boolean): Filter by active status
- `page` (integer): Page number
- `per_page` (integer): Results per page

### 5. User Permissions

#### Get User Permissions (Hierarchical)

```http
GET /api/v1/permissions/users/{user_id}/permissions
```

**Query Parameters:**
- `effective` (boolean): Return effective permissions (with inheritance)
- `include_inherited` (boolean): Show inheritance details

**Response Structure:**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": 123,
      "name": "John Doe",
      "email": "john@example.com",
      "profile": "sales_manager"
    },
    "vendors": ["Vendor A", "Vendor B"],
    "teams": ["Sales Team North"],
    "permissions": {
      "categories": [
        {
          "id": 1,
          "name": "commercial_operations",
          "permissions": {
            "can_view": true,
            "can_edit": false,
            "can_delete": false,
            "can_export": true
          },
          "modules": [...]
        }
      ]
    },
    "summary": {
      "total_permissions": 45,
      "category_permissions": 3,
      "module_permissions": 12,
      "submodule_permissions": 30
    }
  }
}
```

#### Update User Permissions

```http
POST /api/v1/permissions/users/{user_id}/permissions
```

**Request Body:**
```json
{
  "permissions": [
    {
      "type": "module",
      "id": 10,
      "can_view": true,
      "can_edit": true,
      "can_delete": false,
      "can_export": true,
      "inherit_to_submodules": true,
      "reason": "Promoted to order manager"
    }
  ],
  "notify_user": true
}
```

### 6. Vendor Management

#### Get User Vendors

```http
GET /api/v1/permissions/users/{user_id}/vendors
```

#### Add Vendor

```http
POST /api/v1/permissions/users/{user_id}/vendors
```

**Request Body:**
```json
{
  "vendor": "Vendor C",
  "notes": "Added for Q1 2024 campaign"
}
```

#### Remove Vendor

```http
DELETE /api/v1/permissions/users/{user_id}/vendors/{vendor_id}
```

### 7. Batch Operations

#### Apply Permission Template

```http
POST /api/v1/permissions/batch/apply-template
```

**Request Body:**
```json
{
  "template_id": 5,
  "user_ids": [123, 124, 125],
  "options": {
    "override_existing": false,
    "apply_vendors": true,
    "apply_teams": true,
    "send_notifications": true
  },
  "reason": "New team onboarding"
}
```

#### Bulk Update Permissions

```http
POST /api/v1/permissions/batch/bulk-update
```

**Request Body:**
```json
{
  "filters": {
    "user_ids": [123, 124, 125],
    "profile": "sales_rep"
  },
  "permissions": [
    {
      "type": "category",
      "id": 1,
      "can_view": true,
      "can_edit": false
    }
  ],
  "options": {
    "dry_run": false,
    "create_backup": true
  },
  "reason": "Q1 2024 permission review"
}
```

### 8. Permission Templates

#### List Templates

```http
GET /api/v1/permissions/templates
```

**Query Parameters:**
- `category` (string): Filter by template category
- `active` (boolean): Filter by active status
- `system_only` (boolean): Show only system templates

#### Create Template

```http
POST /api/v1/permissions/templates
```

**Request Body:**
```json
{
  "name": "Sales Manager Template",
  "code": "sales_manager",
  "description": "Standard permissions for sales managers",
  "category": "roles",
  "template_data": {
    "permissions": [...],
    "vendors": [],
    "teams": ["Sales Management"]
  }
}
```

### 9. Audit Logs

#### Get Audit Logs

```http
GET /api/v1/permissions/audit
```

**Query Parameters:**
- `user_id` (integer): Filter by user
- `action_category` (string): Filter by action category
- `date_from` (date): Start date
- `date_to` (date): End date
- `page` (integer): Page number
- `limit` (integer): Results per page

### 10. Analytics

#### Permission Usage Analytics

```http
GET /api/v1/permissions/analytics/usage
```

**Query Parameters:**
- `period` (string): Time period (day, week, month, year)
- `group_by` (string): Grouping (user, module, category)

#### Security Risk Assessment

```http
GET /api/v1/permissions/analytics/security-risk
```

## Error Codes

| Code | Description | HTTP Status |
|------|-------------|-------------|
| UNAUTHORIZED | Missing or invalid authentication | 401 |
| PERMISSION_DENIED | Insufficient permissions | 403 |
| NOT_FOUND | Resource not found | 404 |
| VALIDATION_ERROR | Invalid request data | 400 |
| CONFLICT | Resource conflict | 409 |
| INTERNAL_ERROR | Server error | 500 |

## Rate Limiting

- Standard endpoints: 1000 requests/hour
- Batch operations: 100 requests/hour
- Export endpoints: 10 requests/hour

## Best Practices

1. **Use Pagination**: Always paginate list endpoints
2. **Batch Operations**: Use batch endpoints for multiple changes
3. **Error Handling**: Check the `success` field in all responses
4. **Caching**: Implement client-side caching where appropriate
5. **Filtering**: Use specific filters to reduce response size

## Example: Complete Permission Assignment Flow

```javascript
// 1. Get available categories and modules
const categories = await fetch('/api/v1/permissions/categories?include_modules=true');

// 2. Get user's current permissions
const userPerms = await fetch('/api/v1/permissions/users/123/permissions?effective=true');

// 3. Update permissions
const updateResult = await fetch('/api/v1/permissions/users/123/permissions', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer ' + token,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    permissions: [
      {
        type: 'module',
        id: 10,
        can_view: true,
        can_edit: true,
        inherit_to_submodules: true,
        reason: 'New role assignment'
      }
    ],
    notify_user: true
  })
});

// 4. Add vendor access
const vendorResult = await fetch('/api/v1/permissions/users/123/vendors', {
  method: 'POST',
  body: JSON.stringify({
    vendor: 'Vendor ABC',
    notes: 'Assigned to new territory'
  })
});

// 5. Check audit log
const auditLogs = await fetch('/api/v1/permissions/audit?user_id=123&limit=10');
```