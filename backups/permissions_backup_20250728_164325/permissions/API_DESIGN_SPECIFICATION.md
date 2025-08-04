# Permission System API Design Specification

## Overview

This document defines the RESTful API design for the hierarchical permission system. All endpoints follow REST principles and return consistent JSON responses.

## Base URL

```
https://api.example.com/api/v1/permissions
```

## Authentication

All endpoints require authentication via JWT token in the Authorization header:

```
Authorization: Bearer <jwt_token>
```

## Common Response Format

### Success Response

```json
{
  "success": true,
  "data": { ... },
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

## API Endpoints

### 1. Category Management

#### List All Categories
```http
GET /api/v1/permissions/categories
```

Query Parameters:
- `active` (boolean): Filter by active status
- `include_modules` (boolean): Include nested modules
- `include_counts` (boolean): Include permission counts

Response:
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
        "modules": [ ... ] // If include_modules=true
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

Request Body:
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

### 2. Module Management

#### List Modules
```http
GET /api/v1/permissions/modules
```

Query Parameters:
- `category_id` (integer): Filter by category
- `active` (boolean): Filter by active status
- `include_submodules` (boolean): Include nested submodules
- `search` (string): Search in name and display_name

Response:
```json
{
  "success": true,
  "data": {
    "modules": [
      {
        "id": 10,
        "category_id": 1,
        "category_name": "commercial_operations",
        "name": "order_management",
        "display_name": "Order Management",
        "description": "Create and manage customer orders",
        "icon": "file-text",
        "color": "#007bff",
        "active": true,
        "submodule_count": 8,
        "submodules": [ ... ] // If include_submodules=true
      }
    ],
    "total": 25
  }
}
```

### 3. SubModule Management

#### List SubModules
```http
GET /api/v1/permissions/submodules
```

Query Parameters:
- `module_id` (integer): Filter by module
- `critical_level` (string): Filter by critical level
- `active` (boolean): Filter by active status

### 4. User Permissions

#### Get User Permissions (Hierarchical)
```http
GET /api/v1/permissions/users/{user_id}/permissions
```

Query Parameters:
- `effective` (boolean): Return effective permissions (resolved)
- `include_inherited` (boolean): Show inheritance details

Response:
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
          "display_name": "Commercial Operations",
          "permissions": {
            "can_view": true,
            "can_edit": false,
            "can_delete": false,
            "can_export": true,
            "granted_at": "2024-01-10T10:00:00Z",
            "granted_by": "admin@example.com"
          },
          "modules": [
            {
              "id": 10,
              "name": "order_management",
              "display_name": "Order Management",
              "permissions": {
                "can_view": true,
                "can_edit": true,
                "can_delete": false,
                "can_export": true,
                "inherited": false,
                "custom_override": true
              },
              "submodules": [
                {
                  "id": 101,
                  "name": "create_order",
                  "display_name": "Create Orders",
                  "permissions": {
                    "can_view": true,
                    "can_edit": true,
                    "can_delete": false,
                    "can_export": true,
                    "inherited": true,
                    "inherited_from": "module"
                  }
                }
              ]
            }
          ]
        }
      ]
    },
    "summary": {
      "total_permissions": 45,
      "category_permissions": 3,
      "module_permissions": 12,
      "submodule_permissions": 30,
      "custom_overrides": 5,
      "temporary_permissions": 2
    }
  }
}
```

#### Update User Permission
```http
POST /api/v1/permissions/users/{user_id}/permissions
```

Request Body:
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
    },
    {
      "type": "submodule",
      "id": 102,
      "can_view": true,
      "can_edit": false,
      "custom_override": true,
      "override_reason": "Limited access to cancellations"
    }
  ],
  "notify_user": true
}
```

### 5. Vendor and Team Management

#### Get User Vendors
```http
GET /api/v1/permissions/users/{user_id}/vendors
```

Response:
```json
{
  "success": true,
  "data": {
    "vendors": [
      {
        "id": 1,
        "vendor": "Vendor A",
        "added_at": "2024-01-01T10:00:00Z",
        "added_by": "admin@example.com",
        "notes": "Primary vendor"
      }
    ],
    "available_vendors": ["Vendor C", "Vendor D"],
    "total": 2
  }
}
```

#### Add Vendor to User
```http
POST /api/v1/permissions/users/{user_id}/vendors
```

Request Body:
```json
{
  "vendor": "Vendor C",
  "notes": "Added for Q1 2024 campaign"
}
```

#### Remove Vendor from User
```http
DELETE /api/v1/permissions/users/{user_id}/vendors/{vendor_id}
```

### 6. Batch Operations

#### Apply Permission Template
```http
POST /api/v1/permissions/batch/apply-template
```

Request Body:
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

Response:
```json
{
  "success": true,
  "data": {
    "operation_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "IN_PROGRESS",
    "affected_users": 3,
    "estimated_completion": "2024-01-15T10:35:00Z"
  }
}
```

#### Bulk Update Permissions
```http
POST /api/v1/permissions/batch/bulk-update
```

Request Body:
```json
{
  "filters": {
    "user_ids": [123, 124, 125],
    "profile": "sales_rep",
    "vendors": ["Vendor A"]
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

#### Copy Permissions
```http
POST /api/v1/permissions/batch/copy-permissions
```

Request Body:
```json
{
  "source_user_id": 100,
  "target_user_ids": [201, 202, 203],
  "options": {
    "include_vendors": true,
    "include_teams": false,
    "include_temporary": false,
    "merge_permissions": true
  },
  "reason": "Replicate manager permissions to team"
}
```

### 7. Permission Templates

#### List Templates
```http
GET /api/v1/permissions/templates
```

Query Parameters:
- `category` (string): Filter by template category
- `active` (boolean): Filter by active status
- `system_only` (boolean): Show only system templates

#### Create Template
```http
POST /api/v1/permissions/templates
```

Request Body:
```json
{
  "name": "Sales Manager Template",
  "code": "sales_manager",
  "description": "Standard permissions for sales managers",
  "category": "roles",
  "template_data": {
    "permissions": [
      {
        "type": "category",
        "id": 1,
        "can_view": true,
        "can_edit": true,
        "can_delete": false,
        "can_export": true
      }
    ],
    "vendors": [],
    "teams": ["Sales Management"]
  }
}
```

### 8. Audit and Reporting

#### Get Audit Logs
```http
GET /api/v1/permissions/audit
```

Query Parameters:
- `user_id` (integer): Filter by user
- `action_category` (string): Filter by action category
- `entity_type` (string): Filter by entity type
- `date_from` (date): Start date
- `date_to` (date): End date
- `risk_level` (string): Filter by risk level
- `page` (integer): Page number
- `limit` (integer): Results per page

Response:
```json
{
  "success": true,
  "data": {
    "logs": [
      {
        "id": 1000,
        "timestamp": "2024-01-15T10:00:00Z",
        "user": {
          "id": 123,
          "name": "John Doe"
        },
        "action": "PERMISSION_GRANTED",
        "action_category": "PERMISSION",
        "entity_type": "MODULE",
        "entity_id": 10,
        "entity_name": "order_management",
        "old_values": {
          "can_view": false,
          "can_edit": false
        },
        "new_values": {
          "can_view": true,
          "can_edit": true
        },
        "risk_level": "MEDIUM",
        "ip_address": "192.168.1.100",
        "user_agent": "Mozilla/5.0...",
        "notes": "Promoted to order manager"
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 50,
      "total": 245,
      "pages": 5
    }
  }
}
```

#### Export Audit Report
```http
GET /api/v1/permissions/audit/export
```

Query Parameters:
- Same as audit logs
- `format` (string): Export format (csv, excel, pdf)

### 9. Analytics and Insights

#### Permission Usage Analytics
```http
GET /api/v1/permissions/analytics/usage
```

Query Parameters:
- `period` (string): Time period (day, week, month, year)
- `group_by` (string): Grouping (user, module, category)

Response:
```json
{
  "success": true,
  "data": {
    "period": "month",
    "usage_stats": {
      "most_used_permissions": [
        {
          "module": "order_management",
          "submodule": "view_orders",
          "usage_count": 15420,
          "unique_users": 45
        }
      ],
      "unused_permissions": [
        {
          "module": "legacy_reports",
          "last_used": "2023-06-15T10:00:00Z"
        }
      ],
      "permission_distribution": {
        "view_only": 120,
        "view_edit": 45,
        "full_access": 10
      }
    }
  }
}
```

#### Security Risk Assessment
```http
GET /api/v1/permissions/analytics/security-risk
```

Response:
```json
{
  "success": true,
  "data": {
    "risk_summary": {
      "high_risk_users": 5,
      "excessive_permissions": 12,
      "stale_permissions": 34,
      "suspicious_patterns": 2
    },
    "recommendations": [
      {
        "type": "EXCESSIVE_PERMISSION",
        "user_id": 123,
        "user_name": "John Doe",
        "description": "User has edit access to financial modules but hasn't used it in 6 months",
        "action": "Review and potentially revoke"
      }
    ]
  }
}
```

## WebSocket Events

For real-time updates, connect to:
```
wss://api.example.com/ws/permissions
```

### Event Types

#### Permission Changed
```json
{
  "event": "permission.changed",
  "data": {
    "user_id": 123,
    "changed_by": 1,
    "changes": [ ... ]
  }
}
```

#### Batch Operation Progress
```json
{
  "event": "batch.progress",
  "data": {
    "operation_id": "550e8400-e29b-41d4-a716-446655440000",
    "progress": 75,
    "completed": 75,
    "total": 100,
    "status": "IN_PROGRESS"
  }
}
```

## Error Codes

| Code | Description | HTTP Status |
|------|-------------|-------------|
| UNAUTHORIZED | Missing or invalid authentication | 401 |
| PERMISSION_DENIED | Insufficient permissions | 403 |
| NOT_FOUND | Resource not found | 404 |
| VALIDATION_ERROR | Invalid request data | 400 |
| CONFLICT | Resource conflict (e.g., duplicate) | 409 |
| RATE_LIMITED | Too many requests | 429 |
| INTERNAL_ERROR | Server error | 500 |

## Rate Limiting

- Standard endpoints: 1000 requests per hour
- Batch operations: 100 requests per hour
- Export endpoints: 10 requests per hour

Headers:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1673784000
```

## Best Practices

1. **Pagination**: Always use pagination for list endpoints
2. **Filtering**: Use specific filters to reduce response size
3. **Batch Operations**: Prefer batch operations for multiple changes
4. **Caching**: Implement client-side caching with ETags
5. **Error Handling**: Always check the success field and handle errors gracefully