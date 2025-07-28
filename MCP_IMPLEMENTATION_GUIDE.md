# 📚 MCP Implementation Guide for Freight System

## 🎯 Overview

This guide provides detailed implementation instructions for converting the `claude_ai_novo` system into a Model Context Protocol (MCP) server. The MCP implementation will provide better performance, native Claude Desktop integration, and a more maintainable architecture.

## 🏗️ Architecture Overview

### Current System (`claude_ai_novo`)
```
Flask App → WebIntegration → MainOrchestrator → Multiple Components → Response
```

### New MCP Architecture
```
Claude Desktop → MCP Server → Tools/Resources/Prompts → Direct Response
```

## 🛠️ Implementation Details

### 1. Project Structure

```
mcp-freight-system/
├── src/
│   ├── index.ts              # MCP server entry point
│   ├── tools/
│   │   ├── queryAnalyzer.ts  # Query analysis tool
│   │   ├── dataLoader.ts     # Data loading tool
│   │   ├── contextManager.ts # Context management tool
│   │   └── responseGen.ts    # Response generation tool
│   ├── resources/
│   │   ├── systemStatus.ts   # System status resource
│   │   └── domainSchemas.ts  # Domain schemas resource
│   ├── prompts/
│   │   ├── freightExpert.ts  # Freight expert prompt
│   │   ├── dataAnalyst.ts    # Data analyst prompt
│   │   └── systemHelper.ts   # System helper prompt
│   ├── database/
│   │   ├── connection.ts     # PostgreSQL connection
│   │   └── queries.ts        # Database queries
│   └── utils/
│       ├── logger.ts         # Logging utility
│       └── validator.ts      # Data validation
├── tests/
│   ├── tools/
│   ├── resources/
│   └── integration/
├── package.json
├── tsconfig.json
└── README.md
```

### 2. Tool Implementations

#### Query Analyzer Tool

```typescript
// src/tools/queryAnalyzer.ts
import { Tool } from "@modelcontextprotocol/sdk/types.js";

export const queryAnalyzerTool: Tool = {
  name: "frete_query_analyzer",
  description: "Analyzes queries about the freight system, detects intent and extracts entities",
  inputSchema: {
    type: "object",
    properties: {
      query: {
        type: "string",
        description: "User query to analyze"
      },
      context: {
        type: "object",
        description: "Optional conversation context"
      }
    },
    required: ["query"]
  },
  handler: async ({ query, context }) => {
    // Intent detection logic
    const intent = detectIntent(query);
    
    // Domain detection
    const domain = detectDomain(query);
    
    // Entity extraction
    const entities = extractEntities(query);
    
    // Temporal analysis
    const temporal = analyzeTemporalAspects(query);
    
    return {
      intent,
      domain,
      entities,
      temporal,
      confidence: calculateConfidence(intent, domain, entities)
    };
  }
};
```

#### Data Loader Tool

```typescript
// src/tools/dataLoader.ts
import { Tool } from "@modelcontextprotocol/sdk/types.js";
import { pool } from "../database/connection.js";

export const dataLoaderTool: Tool = {
  name: "frete_data_loader",
  description: "Loads freight system data from PostgreSQL database",
  inputSchema: {
    type: "object",
    properties: {
      domain: {
        type: "string",
        enum: ["fretes", "pedidos", "entregas", "financeiro"],
        description: "Data domain to query"
      },
      filters: {
        type: "object",
        description: "Query filters"
      },
      limit: {
        type: "number",
        default: 100,
        description: "Maximum records to return"
      }
    },
    required: ["domain"]
  },
  handler: async ({ domain, filters, limit }) => {
    const queryBuilder = new QueryBuilder(domain);
    
    if (filters) {
      queryBuilder.applyFilters(filters);
    }
    
    queryBuilder.limit(limit);
    
    const result = await pool.query(queryBuilder.build());
    
    return {
      data: result.rows,
      count: result.rowCount,
      domain,
      timestamp: new Date().toISOString()
    };
  }
};
```

#### Context Manager Tool

```typescript
// src/tools/contextManager.ts
import { Tool } from "@modelcontextprotocol/sdk/types.js";
import Redis from "ioredis";

const redis = new Redis(process.env.REDIS_URL);

export const contextManagerTool: Tool = {
  name: "frete_context_manager",
  description: "Manages conversational context and session state",
  inputSchema: {
    type: "object",
    properties: {
      action: {
        type: "string",
        enum: ["get", "set", "clear"],
        description: "Action to perform"
      },
      sessionId: {
        type: "string",
        description: "Session identifier"
      },
      data: {
        type: "object",
        description: "Context data (for set action)"
      }
    },
    required: ["action", "sessionId"]
  },
  handler: async ({ action, sessionId, data }) => {
    const key = `context:${sessionId}`;
    
    switch (action) {
      case "get":
        const context = await redis.get(key);
        return context ? JSON.parse(context) : null;
        
      case "set":
        if (!data) throw new Error("Data required for set action");
        await redis.set(key, JSON.stringify(data), "EX", 3600);
        return { success: true };
        
      case "clear":
        await redis.del(key);
        return { success: true };
        
      default:
        throw new Error(`Unknown action: ${action}`);
    }
  }
};
```

#### Response Generator Tool

```typescript
// src/tools/responseGen.ts
import { Tool } from "@modelcontextprotocol/sdk/types.js";

export const responseGeneratorTool: Tool = {
  name: "frete_response_generator",
  description: "Generates optimized responses with insights",
  inputSchema: {
    type: "object",
    properties: {
      analysis: {
        type: "object",
        description: "Query analysis results"
      },
      data: {
        type: "object",
        description: "Retrieved data"
      },
      context: {
        type: "object",
        description: "Conversation context"
      }
    },
    required: ["analysis", "data"]
  },
  handler: async ({ analysis, data, context }) => {
    // Format response based on intent
    const formattedResponse = formatResponse(analysis.intent, data);
    
    // Add business insights
    const insights = generateInsights(data, analysis.domain);
    
    // Optimize for user experience
    const optimized = optimizeForUser(formattedResponse, context);
    
    return {
      response: optimized,
      insights,
      metadata: {
        domain: analysis.domain,
        recordCount: data.count,
        timestamp: new Date().toISOString()
      }
    };
  }
};
```

### 3. Resource Implementations

#### System Status Resource

```typescript
// src/resources/systemStatus.ts
import { Resource } from "@modelcontextprotocol/sdk/types.js";

export const systemStatusResource: Resource = {
  uri: "frete://status/system",
  name: "Freight System Status",
  mimeType: "application/json",
  description: "Real-time system status and health metrics",
  handler: async () => {
    const status = await checkSystemHealth();
    
    return {
      contents: [
        {
          uri: "frete://status/system",
          mimeType: "application/json",
          text: JSON.stringify({
            status: status.overall,
            modules: {
              database: status.database,
              cache: status.cache,
              api: status.api
            },
            metrics: {
              uptime: process.uptime(),
              memory: process.memoryUsage(),
              connections: status.activeConnections
            },
            timestamp: new Date().toISOString()
          }, null, 2)
        }
      ]
    };
  }
};
```

#### Domain Schemas Resource

```typescript
// src/resources/domainSchemas.ts
import { Resource } from "@modelcontextprotocol/sdk/types.js";

export const domainSchemasResource: Resource = {
  uri: "frete://schemas/{domain}",
  name: "Domain Schemas",
  mimeType: "application/json",
  description: "Database schemas for freight system domains",
  handler: async (uri: string) => {
    const domain = extractDomainFromUri(uri);
    const schema = await loadDomainSchema(domain);
    
    return {
      contents: [
        {
          uri,
          mimeType: "application/json",
          text: JSON.stringify({
            domain,
            tables: schema.tables,
            fields: schema.fields,
            relationships: schema.relationships,
            indexes: schema.indexes
          }, null, 2)
        }
      ]
    };
  }
};
```

### 4. Prompt Implementations

#### Freight Expert Prompt

```typescript
// src/prompts/freightExpert.ts
import { Prompt } from "@modelcontextprotocol/sdk/types.js";

export const freightExpertPrompt: Prompt = {
  name: "freight_expert",
  description: "Expert knowledge about freight operations",
  arguments: [
    {
      name: "domain",
      description: "Specific freight domain",
      required: true
    }
  ],
  handler: async ({ domain }) => {
    return {
      messages: [
        {
          role: "system",
          content: `You are an expert in ${domain} for the freight management system.

Key responsibilities:
- Analyze freight data with precision
- Provide actionable business insights
- Identify cost optimization opportunities
- Ensure compliance with regulations
- Suggest process improvements

Domain-specific knowledge for ${domain}:
${getDomainSpecificKnowledge(domain)}

Always provide data-driven recommendations and consider the broader business context.`
        }
      ]
    };
  }
};
```

### 5. Database Integration

#### Connection Setup

```typescript
// src/database/connection.ts
import { Pool } from 'pg';

export const pool = new Pool({
  host: process.env.DB_HOST,
  port: parseInt(process.env.DB_PORT || '5432'),
  database: process.env.DB_NAME,
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
  max: 20,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000,
});

// Health check
export async function checkDatabaseHealth(): Promise<boolean> {
  try {
    const result = await pool.query('SELECT 1');
    return result.rowCount === 1;
  } catch (error) {
    console.error('Database health check failed:', error);
    return false;
  }
}
```

#### Query Builder

```typescript
// src/database/queries.ts
export class QueryBuilder {
  private domain: string;
  private conditions: string[] = [];
  private limitValue: number = 100;
  
  constructor(domain: string) {
    this.domain = domain;
  }
  
  applyFilters(filters: Record<string, any>): this {
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        this.conditions.push(`${key} = $${this.conditions.length + 1}`);
      }
    });
    return this;
  }
  
  limit(value: number): this {
    this.limitValue = value;
    return this;
  }
  
  build(): string {
    const table = this.getTableName(this.domain);
    let query = `SELECT * FROM ${table}`;
    
    if (this.conditions.length > 0) {
      query += ` WHERE ${this.conditions.join(' AND ')}`;
    }
    
    query += ` LIMIT ${this.limitValue}`;
    
    return query;
  }
  
  private getTableName(domain: string): string {
    const tableMap = {
      fretes: 'freight_orders',
      pedidos: 'orders',
      entregas: 'deliveries',
      financeiro: 'financial_transactions'
    };
    return tableMap[domain] || domain;
  }
}
```

### 6. MCP Server Configuration

#### Main Server File

```typescript
// src/index.ts
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

// Import tools
import { queryAnalyzerTool } from "./tools/queryAnalyzer.js";
import { dataLoaderTool } from "./tools/dataLoader.js";
import { contextManagerTool } from "./tools/contextManager.js";
import { responseGeneratorTool } from "./tools/responseGen.js";

// Import resources
import { systemStatusResource } from "./resources/systemStatus.js";
import { domainSchemasResource } from "./resources/domainSchemas.js";

// Import prompts
import { freightExpertPrompt } from "./prompts/freightExpert.js";

// Create server
const server = new Server(
  {
    name: "mcp-freight-system",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
      resources: {},
      prompts: {},
    },
  }
);

// Register tools
server.setRequestHandler("tools/list", async () => ({
  tools: [
    queryAnalyzerTool,
    dataLoaderTool,
    contextManagerTool,
    responseGeneratorTool
  ],
}));

// Register resources
server.setRequestHandler("resources/list", async () => ({
  resources: [
    systemStatusResource,
    domainSchemasResource
  ],
}));

// Register prompts
server.setRequestHandler("prompts/list", async () => ({
  prompts: [
    freightExpertPrompt
  ],
}));

// Start server
const transport = new StdioServerTransport();
await server.connect(transport);
```

### 7. Testing Strategy

#### Unit Tests

```typescript
// tests/tools/queryAnalyzer.test.ts
import { describe, it, expect } from 'vitest';
import { queryAnalyzerTool } from '../../src/tools/queryAnalyzer';

describe('Query Analyzer Tool', () => {
  it('should correctly identify freight query intent', async () => {
    const result = await queryAnalyzerTool.handler({
      query: "Show me all pending freight orders from São Paulo"
    });
    
    expect(result.intent).toBe('list');
    expect(result.domain).toBe('fretes');
    expect(result.entities).toContain('São Paulo');
  });
  
  it('should handle complex temporal queries', async () => {
    const result = await queryAnalyzerTool.handler({
      query: "What were the delivery rates last month?"
    });
    
    expect(result.temporal).toBeDefined();
    expect(result.temporal.period).toBe('last_month');
  });
});
```

#### Integration Tests

```typescript
// tests/integration/endToEnd.test.ts
import { describe, it, expect } from 'vitest';
import { MCPClient } from './helpers/mcpClient';

describe('End-to-End MCP Integration', () => {
  const client = new MCPClient();
  
  it('should handle complete query flow', async () => {
    // Analyze query
    const analysis = await client.callTool('frete_query_analyzer', {
      query: "Show freight costs for last week"
    });
    
    // Load data
    const data = await client.callTool('frete_data_loader', {
      domain: analysis.domain,
      filters: analysis.filters
    });
    
    // Generate response
    const response = await client.callTool('frete_response_generator', {
      analysis,
      data
    });
    
    expect(response).toBeDefined();
    expect(response.insights).toBeArray();
  });
});
```

### 8. Deployment Configuration

#### Package.json

```json
{
  "name": "mcp-freight-system",
  "version": "1.0.0",
  "description": "MCP server for freight management system",
  "type": "module",
  "main": "dist/index.js",
  "scripts": {
    "build": "tsc",
    "start": "node dist/index.js",
    "dev": "tsx watch src/index.ts",
    "test": "vitest",
    "lint": "eslint src --ext .ts",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "@modelcontextprotocol/sdk": "^0.5.0",
    "pg": "^8.11.0",
    "ioredis": "^5.3.0",
    "zod": "^3.22.0"
  },
  "devDependencies": {
    "@types/node": "^20.0.0",
    "@types/pg": "^8.10.0",
    "typescript": "^5.0.0",
    "vitest": "^1.0.0",
    "tsx": "^4.0.0",
    "eslint": "^8.0.0"
  }
}
```

#### TypeScript Configuration

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "Node16",
    "moduleResolution": "Node16",
    "lib": ["ES2022"],
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "allowJs": false,
    "noEmit": false,
    "incremental": true,
    "sourceMap": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist", "tests"]
}
```

### 9. Claude Desktop Configuration

```json
{
  "mcpServers": {
    "freight-system": {
      "command": "node",
      "args": ["/path/to/mcp-freight-system/dist/index.js"],
      "env": {
        "DB_HOST": "localhost",
        "DB_PORT": "5432",
        "DB_NAME": "freight_db",
        "DB_USER": "freight_user",
        "DB_PASSWORD": "secure_password",
        "REDIS_URL": "redis://localhost:6379"
      }
    }
  }
}
```

## 📊 Migration Strategy

### Phase 1: Parallel Running
1. Keep `claude_ai_novo` operational
2. Deploy MCP server alongside
3. Route 10% of traffic to MCP
4. Monitor and compare results

### Phase 2: Gradual Increase
1. Increase MCP traffic to 50%
2. A/B test response quality
3. Gather user feedback
4. Fix identified issues

### Phase 3: Full Migration
1. Route 100% traffic to MCP
2. Deprecate old endpoints
3. Archive legacy code
4. Update documentation

## 🎯 Performance Optimization

### Caching Strategy
- Use Redis for frequently accessed data
- Cache query analysis results
- Implement TTL based on data volatility
- Pre-warm cache for common queries

### Connection Pooling
- PostgreSQL: 20 max connections
- Redis: 10 max connections
- Implement connection retry logic
- Monitor connection health

### Query Optimization
- Create necessary database indexes
- Use prepared statements
- Implement query result pagination
- Optimize JOIN operations

## 🔒 Security Considerations

### Authentication
- Validate JWT tokens
- Implement rate limiting
- Secure database credentials
- Use environment variables

### Data Protection
- Sanitize user inputs
- Implement SQL injection prevention
- Encrypt sensitive data
- Audit data access

## 📈 Monitoring and Observability

### Metrics to Track
- Response time percentiles (p50, p95, p99)
- Error rates by tool
- Database query performance
- Cache hit rates
- Memory usage

### Logging
- Structured JSON logging
- Log levels: ERROR, WARN, INFO, DEBUG
- Correlation IDs for request tracking
- Log aggregation with ELK stack

### Alerting
- Response time > 2 seconds
- Error rate > 5%
- Database connection failures
- Memory usage > 80%

## ✅ Success Criteria

1. **Performance**: All responses < 2 seconds
2. **Reliability**: 99.9% uptime
3. **Accuracy**: 100% data consistency with legacy system
4. **User Experience**: Improved satisfaction scores
5. **Maintainability**: Reduced code complexity by 30%

---

This implementation guide provides a complete roadmap for converting the freight system to MCP. Follow the phases sequentially and ensure thorough testing at each step.