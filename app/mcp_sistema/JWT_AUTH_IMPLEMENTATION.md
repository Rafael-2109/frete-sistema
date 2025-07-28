# JWT Authentication Implementation for MCP Sistema

## Overview

This document summarizes the complete JWT authentication system implementation for the MCP freight management system.

## Components Implemented

### 1. **Core Security Module** (`core/security.py`)
- JWT token creation and validation
- Access and refresh token support
- Password hashing with bcrypt
- API key generation and validation
- Security context for request handling
- Password strength validation
- Rate limiting helpers

Key Features:
- Multiple token types (access, refresh, password reset, email verification)
- Security levels (public, authenticated, verified, admin, superuser)
- Comprehensive security context with permission checking
- Password policy enforcement

### 2. **User Models** (`models/user.py`)
- User model with full authentication support
- Role-Based Access Control (RBAC) with Role model
- Fine-grained permissions with Permission model
- Refresh token management
- API key management

Key Features:
- Many-to-many relationships between users, roles, and permissions
- Account lockout after failed login attempts
- Soft delete support
- Email verification status
- MCP client ID support for API access

### 3. **Authentication Routes** (`api/routes/auth.py`)
- `/auth/register` - User registration
- `/auth/login` - Login with username/password
- `/auth/refresh` - Refresh access token
- `/auth/logout` - Logout (revoke refresh tokens)
- `/auth/me` - Get current user info
- `/auth/api-keys` - API key management
- `/auth/request-password-reset` - Request password reset
- `/auth/reset-password` - Reset password with token
- `/auth/verify-email` - Verify email address

### 4. **User Management Routes** (`api/routes/users.py`)
- Full CRUD operations for users
- Role management endpoints
- Permission listing
- Password change functionality
- User search and filtering

### 5. **Authentication Dependencies** (`api/dependencies/auth.py`)
- JWT token extraction and validation
- API key authentication
- Flexible authentication (JWT or API key)
- Permission-based access control
- Role-based access control
- Security level requirements
- Optional authentication support

### 6. **Authentication Middleware** (`api/middlewares/auth.py`)
- JWT validation middleware
- Rate limiting middleware
- CORS handling middleware
- Automatic user context injection

### 7. **Initialization Script** (`utils/init_auth.py`)
- Creates default permissions
- Creates system roles (superadmin, admin, manager, operator, viewer, mcp_client)
- Creates default superuser
- Creates sample users for testing

## Security Features

### Password Security
- Bcrypt hashing
- Configurable password policy
- Password strength validation
- Secure password generation

### Token Security
- JWT with configurable expiration
- Refresh token rotation
- Token type validation
- Secure token storage

### Account Security
- Account lockout after failed attempts
- Email verification
- Two-factor authentication ready
- API key authentication for services

### Access Control
- Role-Based Access Control (RBAC)
- Fine-grained permissions
- Resource-based permissions
- Hierarchical security levels

## Default Roles and Permissions

### Roles
1. **superadmin** - Full system access
2. **admin** - Administrative access
3. **manager** - Operational management
4. **operator** - Basic operations
5. **viewer** - Read-only access
6. **mcp_client** - MCP API access

### Permission Format
- `resource:action` (e.g., `user:create`, `freight:read`)
- Wildcard support (e.g., `user:*` for all user actions)

### Resources
- user, role, permission
- freight, shipment, invoice
- report, mcp, api

## Usage Examples

### 1. User Registration
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "email": "newuser@example.com",
    "password": "SecurePass123!",
    "full_name": "New User"
  }'
```

### 2. Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"
```

### 3. Using JWT Token
```bash
curl -X GET http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer <access_token>"
```

### 4. Creating API Key
```bash
curl -X POST http://localhost:8000/api/v1/auth/api-keys \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My API Key",
    "description": "For automated scripts",
    "expires_in_days": 90,
    "permissions": ["freight:read", "shipment:read"]
  }'
```

### 5. Using API Key
```bash
curl -X GET http://localhost:8000/api/v1/mcp/tools \
  -H "X-API-Key: mcp_<your_api_key>"
```

## Configuration

Key settings in `core/settings.py`:
- `SECRET_KEY` - JWT signing key (MUST be changed in production)
- `ACCESS_TOKEN_EXPIRE_MINUTES` - Access token lifetime (default: 30)
- `REFRESH_TOKEN_EXPIRE_DAYS` - Refresh token lifetime (default: 7)
- `PASSWORD_MIN_LENGTH` - Minimum password length (default: 8)
- `MAX_LOGIN_ATTEMPTS` - Before account lockout (default: 5)
- `API_RATE_LIMIT` - Requests per minute (default: 100)

## Security Best Practices

1. **Change Default Passwords** - The system creates a default admin user with password "admin123". Change this immediately!

2. **Use Strong Secret Key** - Generate a strong SECRET_KEY for production:
   ```python
   import secrets
   print(secrets.token_urlsafe(32))
   ```

3. **Enable HTTPS** - Always use HTTPS in production to protect tokens in transit

4. **Regular Token Rotation** - Implement regular token rotation for long-lived sessions

5. **Monitor Failed Logins** - Review logs for suspicious login attempts

6. **Implement 2FA** - The system is ready for two-factor authentication implementation

## Integration with MCP

The authentication system is fully integrated with the MCP protocol:
- MCP clients authenticate using API keys
- Each MCP session is associated with an authenticated user
- Tool execution is logged with user context
- Permissions control access to MCP tools and resources

## Next Steps

1. Implement email service for:
   - Password reset emails
   - Email verification
   - Account notifications

2. Add two-factor authentication

3. Implement session management UI

4. Add audit logging for all authentication events

5. Create admin UI for user/role management