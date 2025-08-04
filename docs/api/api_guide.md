# Frete Sistema API Guide

## Table of Contents
1. [Introduction](#introduction)
2. [Authentication](#authentication)
3. [API Endpoints](#api-endpoints)
4. [Request/Response Format](#requestresponse-format)
5. [Error Handling](#error-handling)
6. [Rate Limiting](#rate-limiting)
7. [Best Practices](#best-practices)
8. [Code Examples](#code-examples)
9. [Postman Collection](#postman-collection)

## Introduction

The Frete Sistema API provides comprehensive access to freight management functionality through a RESTful interface. This guide covers all aspects of using the API effectively.

### Base URLs
- **Development**: `http://localhost:5000/api/v1`
- **Production**: `https://api.fretesistema.com.br/api/v1`

### API Features
- 🔐 JWT-based authentication
- 📊 Real-time freight tracking
- 💰 Financial management
- 📈 Analytics and reporting
- 🤖 AI-powered insights via MCP

## Authentication

The API uses JWT (JSON Web Tokens) for authentication. All endpoints except `/health` and `/docs` require authentication.

### Getting Started

1. **Obtain Access Token**
```bash
curl -X POST https://api.fretesistema.com.br/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "your_password"
  }'
```

Response:
```json
{
  "success": true,
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

2. **Use Token in Requests**
```bash
curl -X GET https://api.fretesistema.com.br/api/v1/embarques \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Token Management

- **Access Token**: Valid for 1 hour (3600 seconds)
- **Refresh Token**: Valid for 30 days
- **Token Refresh**: Use the refresh endpoint before expiration

```bash
curl -X POST https://api.fretesistema.com.br/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "your_refresh_token"
  }'
```

## API Endpoints

### Embarques (Shipments)

#### List Shipments
```http
GET /api/v1/embarques
```

Parameters:
- `status` (optional): Filter by status (ativo, cancelado, finalizado)
- `page` (optional): Page number (default: 1)
- `limit` (optional): Items per page (default: 10, max: 100)

Example:
```bash
curl -X GET "https://api.fretesistema.com.br/api/v1/embarques?status=ativo&limit=20" \
  -H "Authorization: Bearer $TOKEN"
```

#### Create Shipment
```http
POST /api/v1/embarques
```

Body:
```json
{
  "numero": "EMB-2024-001",
  "status": "ativo",
  "data_embarque": "2024-01-17T08:00:00Z",
  "transportadora_id": 45,
  "observacoes": "Carga refrigerada",
  "fretes_ids": [567, 568, 569]
}
```

#### Update Shipment
```http
PUT /api/v1/embarques/{id}
```

Body:
```json
{
  "status": "finalizado",
  "observacoes": "Entrega concluída"
}
```

### Fretes (Freight)

#### List Freight
```http
GET /api/v1/fretes
```

Parameters:
- `status_aprovacao`: Filter by approval status
- `embarque_id`: Filter by shipment
- `limit`: Results per page

#### Approve Freight
```http
PUT /api/v1/fretes/{id}/approve
```

Body:
```json
{
  "valor_aprovado": 1200.00,
  "observacoes": "Valor negociado"
}
```

#### Add CT-e
```http
PUT /api/v1/fretes/{id}/cte
```

Body:
```json
{
  "numero_cte": "35240112345678000190570010000123450123456789"
}
```

### Monitoramento (Monitoring)

#### Track Deliveries
```http
GET /api/v1/monitoramento
```

Parameters:
- `nf_numero`: Invoice number
- `pendencia_financeira`: true/false
- `status`: Delivery status

#### Update Delivery Status
```http
PUT /api/v1/monitoramento/{id}
```

Body:
```json
{
  "status_finalizacao": "entregue",
  "data_entrega_real": "2024-01-16T14:30:00Z"
}
```

### Cliente (Client)

#### Get Client Details
```http
GET /api/v1/cliente/{nome}
```

Parameters:
- `uf`: State filter (e.g., SP, RJ)
- `limite`: Number of orders to return

Example:
```bash
curl -X GET "https://api.fretesistema.com.br/api/v1/cliente/Carrefour?uf=SP&limite=10" \
  -H "Authorization: Bearer $TOKEN"
```

#### Export Client Report
```http
GET /api/v1/cliente/{nome}/excel
```

Returns an Excel file with client data.

### Estatísticas (Statistics)

#### System Statistics
```http
GET /api/v1/estatisticas
```

Parameters:
- `periodo_dias`: Analysis period in days (default: 30)

### MCP (Model Context Protocol)

#### Analyze Query
```http
POST /api/v1/mcp/analyze
```

Body:
```json
{
  "query": "Show me pending shipments for São Paulo",
  "context": {
    "user_role": "manager"
  },
  "include_suggestions": true
}
```

#### Process Command
```http
POST /api/v1/mcp/process
```

Body:
```json
{
  "command": "approve_freight",
  "parameters": {
    "freight_id": 5678,
    "approved_value": 1200.00
  },
  "auto_execute": false
}
```

## Request/Response Format

### Standard Response Structure

All API responses follow this structure:

```json
{
  "success": true,
  "data": {
    // Response data
  },
  "message": "Optional message",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Pagination

Paginated endpoints include:

```json
{
  "data": [...],
  "total": 156,
  "page": 1,
  "pages": 16,
  "limit": 10
}
```

### Filtering

Use query parameters for filtering:
```
GET /api/v1/embarques?status=ativo&transportadora_id=45&data_inicio=2024-01-01
```

## Error Handling

### Error Response Format

```json
{
  "success": false,
  "error": "Error message",
  "error_code": "ERROR_CODE",
  "details": {
    // Additional error information
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Common Error Codes

| Code | Status | Description |
|------|--------|-------------|
| `AUTH_REQUIRED` | 401 | Missing or invalid authentication |
| `AUTH_FAILED` | 401 | Invalid credentials |
| `INSUFFICIENT_PERMISSIONS` | 403 | User lacks required permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `VALIDATION_ERROR` | 422 | Request validation failed |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error |

### Handling Errors

```javascript
try {
  const response = await fetch('/api/v1/embarques', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  const data = await response.json();
  
  if (!data.success) {
    console.error(`Error: ${data.error} (${data.error_code})`);
    // Handle specific error codes
    switch (data.error_code) {
      case 'AUTH_REQUIRED':
        // Redirect to login
        break;
      case 'RATE_LIMIT_EXCEEDED':
        // Wait and retry
        break;
    }
  }
} catch (error) {
  console.error('Network error:', error);
}
```

## Rate Limiting

The API implements rate limiting to ensure fair usage:

- **Default Limit**: 100 requests per minute
- **Authenticated Users**: 1000 requests per minute
- **Premium Users**: 5000 requests per minute

### Rate Limit Headers

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1673785860
```

### Handling Rate Limits

```javascript
const makeRequest = async (url, options, retries = 3) => {
  try {
    const response = await fetch(url, options);
    
    if (response.status === 429 && retries > 0) {
      const retryAfter = response.headers.get('Retry-After') || 60;
      await new Promise(resolve => setTimeout(resolve, retryAfter * 1000));
      return makeRequest(url, options, retries - 1);
    }
    
    return response;
  } catch (error) {
    throw error;
  }
};
```

## Best Practices

### 1. Authentication
- Store tokens securely (never in localStorage for sensitive apps)
- Refresh tokens before expiration
- Implement token rotation for enhanced security

### 2. Error Handling
- Always check the `success` field
- Implement proper error logging
- Provide user-friendly error messages

### 3. Performance
- Use pagination for large datasets
- Implement caching where appropriate
- Batch requests when possible

### 4. Security
- Always use HTTPS in production
- Validate all inputs
- Implement request signing for sensitive operations

### 5. Monitoring
- Log all API interactions
- Monitor rate limit usage
- Track response times

## Code Examples

### JavaScript/TypeScript

```typescript
class FreteAPI {
  private baseURL: string;
  private token: string;

  constructor(baseURL: string) {
    this.baseURL = baseURL;
  }

  async login(email: string, password: string): Promise<void> {
    const response = await fetch(`${this.baseURL}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ email, password })
    });

    const data = await response.json();
    if (data.success) {
      this.token = data.access_token;
    } else {
      throw new Error(data.error);
    }
  }

  async getEmbarques(status?: string): Promise<any> {
    const params = new URLSearchParams();
    if (status) params.append('status', status);

    const response = await fetch(
      `${this.baseURL}/embarques?${params}`,
      {
        headers: {
          'Authorization': `Bearer ${this.token}`
        }
      }
    );

    return response.json();
  }
}

// Usage
const api = new FreteAPI('https://api.fretesistema.com.br/api/v1');
await api.login('user@example.com', 'password');
const embarques = await api.getEmbarques('ativo');
```

### Python

```python
import requests
from typing import Optional, Dict, Any

class FreteAPI:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.token = None
        self.session = requests.Session()
    
    def login(self, email: str, password: str) -> None:
        response = self.session.post(
            f"{self.base_url}/auth/login",
            json={"email": email, "password": password}
        )
        data = response.json()
        
        if data["success"]:
            self.token = data["access_token"]
            self.session.headers.update({
                "Authorization": f"Bearer {self.token}"
            })
        else:
            raise Exception(data["error"])
    
    def get_embarques(self, status: Optional[str] = None) -> Dict[str, Any]:
        params = {}
        if status:
            params["status"] = status
        
        response = self.session.get(
            f"{self.base_url}/embarques",
            params=params
        )
        return response.json()

# Usage
api = FreteAPI("https://api.fretesistema.com.br/api/v1")
api.login("user@example.com", "password")
embarques = api.get_embarques("ativo")
```

### cURL Examples

```bash
# Set variables
API_URL="https://api.fretesistema.com.br/api/v1"
EMAIL="user@example.com"
PASSWORD="your_password"

# Login and get token
TOKEN=$(curl -s -X POST "$API_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" \
  | jq -r '.access_token')

# Get active shipments
curl -X GET "$API_URL/embarques?status=ativo" \
  -H "Authorization: Bearer $TOKEN" \
  | jq '.'

# Create new shipment
curl -X POST "$API_URL/embarques" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "numero": "EMB-2024-001",
    "status": "ativo",
    "data_embarque": "2024-01-17T08:00:00Z",
    "transportadora_id": 45
  }'
```

## Postman Collection

We provide a complete Postman collection for easy API testing:

1. **Import Collection**: Download from `/docs/api/frete_sistema.postman_collection.json`
2. **Configure Environment**:
   ```json
   {
     "base_url": "https://api.fretesistema.com.br/api/v1",
     "email": "your_email",
     "password": "your_password",
     "access_token": ""
   }
   ```
3. **Run Authentication**: Execute the Login request first
4. **Use Collection**: All subsequent requests will use the saved token

### Collection Features
- Pre-request scripts for automatic token refresh
- Response tests for validation
- Example requests for all endpoints
- Environment variables for easy configuration

## Support

For API support:
- 📧 Email: suporte@fretesistema.com.br
- 📚 Documentation: https://docs.fretesistema.com.br
- 🐛 Issues: https://github.com/fretesistema/api/issues

## Changelog

### Version 1.0.0 (2024-01-15)
- Initial API release
- JWT authentication
- Complete CRUD operations for shipments and freight
- Client reporting endpoints
- MCP integration for AI features
- Comprehensive error handling
- Rate limiting implementation