# MCP Integration Guide for Sistema de Frete

## Overview

This guide describes the MCP (Model Context Protocol) server implementation for Sistema de Frete, designed to replace the current `claude_ai_novo` system with a more efficient, native Claude Desktop integration.

## Architecture

### Current System (claude_ai_novo)
```
User → Browser → Flask → WebIntegration → Orchestrators → Processors → Database → Response
```

### New MCP System
```
User → Claude Desktop → MCP Server → Tools → Database → Response
```

## MCP Tools

### 1. Query Analyzer (`frete_query_analyzer`)
- **Purpose**: Analyzes natural language queries
- **Capabilities**:
  - Intent detection (query, create, update, delete, report, monitor, help)
  - Domain identification (fretes, pedidos, entregas, etc.)
  - Entity extraction (order IDs, dates, values, statuses)
  - Temporal reference detection
  - Semantic analysis

### 2. Data Loader (`frete_data_loader`)
- **Purpose**: Retrieves data from PostgreSQL database
- **Capabilities**:
  - Multi-domain data access
  - Advanced filtering and pagination
  - Aggregations and calculations
  - Data enrichment with insights
  - Performance optimization

### 3. Context Manager (`frete_context_manager`)
- **Purpose**: Manages conversation state and user preferences
- **Capabilities**:
  - Session management
  - Conversation history
  - User preferences
  - Domain context caching
  - Workflow state tracking

### 4. Response Generator (`frete_response_generator`)
- **Purpose**: Creates optimized responses
- **Capabilities**:
  - Multiple format support (text, markdown, HTML, JSON, charts)
  - Multilingual responses (pt-BR, en-US, es-ES)
  - Style adaptation (formal, conversational, technical, executive)
  - Insights and recommendations
  - Action suggestions

## MCP Resources

### 1. System Status (`frete://status/system`)
- Real-time health monitoring
- Module status tracking
- Performance metrics
- Alert management

### 2. Domain Schemas (`frete://schemas/{domain}`)
- Complete database schemas
- Field descriptions
- Business rules
- Relationships

## MCP Prompts

### Freight Expert (`freight_expert`)
Available expertise domains:
- **fretes**: Freight calculation and optimization
- **pedidos**: Order management
- **entregas**: Delivery and last-mile
- **financeiro**: Financial analysis
- **operacional**: Operations management
- **estrategico**: Strategic planning

## Implementation Steps

### Phase 1: MCP Server Setup
1. Initialize TypeScript project
2. Implement MCP SDK integration
3. Create database connection layer
4. Set up authentication

### Phase 2: Tool Implementation
1. Implement Query Analyzer with NLP capabilities
2. Create Data Loader with SQL query builder
3. Build Context Manager with Redis caching
4. Develop Response Generator with template engine

### Phase 3: Resource Implementation
1. System Status resource with real-time monitoring
2. Domain Schemas resource with dynamic schema loading

### Phase 4: Prompt Configuration
1. Create domain-specific expert prompts
2. Implement multilingual support
3. Add context-aware responses

### Phase 5: Testing & Migration
1. Unit tests for each tool
2. Integration tests with Claude Desktop
3. Performance benchmarking
4. Gradual migration from claude_ai_novo

## Database Integration

The MCP server maintains compatibility with the existing PostgreSQL schema:

```typescript
// Connection configuration
const dbConfig = {
  host: process.env.DB_HOST,
  port: process.env.DB_PORT,
  database: process.env.DB_NAME,
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
  ssl: { rejectUnauthorized: false }
};
```

## Security Considerations

1. **Authentication**: JWT tokens for API access
2. **Authorization**: Role-based access control
3. **Data Encryption**: TLS for data in transit
4. **Input Validation**: Strict schema validation
5. **Rate Limiting**: Prevent abuse

## Performance Optimizations

1. **Query Optimization**: Indexed queries, query planning
2. **Caching Strategy**: Redis for frequent queries
3. **Connection Pooling**: Efficient database connections
4. **Response Compression**: Gzip for large responses
5. **Lazy Loading**: Load data on demand

## Migration Strategy

### Week 1-2: Development
- Implement core MCP server
- Create all tools and resources
- Set up testing environment

### Week 3: Testing
- Integration testing with Claude Desktop
- Performance benchmarking
- Security audit

### Week 4: Gradual Migration
- Deploy MCP server in parallel
- Route 10% traffic initially
- Monitor performance and errors
- Gradually increase traffic

### Week 5: Full Migration
- Complete traffic migration
- Deprecate old endpoints
- Monitor system stability

## Monitoring & Maintenance

1. **Logging**: Structured JSON logs
2. **Metrics**: Prometheus-compatible metrics
3. **Alerts**: Real-time alert system
4. **Dashboards**: Grafana dashboards
5. **Error Tracking**: Sentry integration

## Example Usage

### Query Analysis
```typescript
const result = await mcpServer.callTool('frete_query_analyzer', {
  query: "Show me delayed deliveries from last week",
  context: { sessionId: "abc123" }
});
```

### Data Loading
```typescript
const data = await mcpServer.callTool('frete_data_loader', {
  domain: "entregas",
  filters: {
    dateRange: { start: "2024-01-01", end: "2024-01-07" },
    status: ["delayed", "failed"]
  },
  options: { limit: 100, enrichData: true }
});
```

### Response Generation
```typescript
const response = await mcpServer.callTool('frete_response_generator', {
  analysis: analysisResult,
  data: loadedData,
  context: userContext,
  options: {
    format: "markdown",
    style: "executive",
    includeInsights: true
  }
});
```

## Benefits

1. **Performance**: 40-60% faster response times
2. **User Experience**: Native Claude Desktop integration
3. **Maintainability**: Type-safe, modular architecture
4. **Scalability**: Better resource utilization
5. **Flexibility**: Easy to add new capabilities

## Support & Documentation

- Technical Documentation: `/docs/technical`
- API Reference: `/docs/api`
- Troubleshooting Guide: `/docs/troubleshooting`
- Contact: dev-team@frete-sistema.com