# MCP Frete Sistema - Usage Guide

## 🚀 Getting Started

The MCP (Model Context Protocol) Frete Sistema provides natural language access to freight data and intelligent search capabilities powered by AI embeddings.

### Prerequisites

- Node.js 18 or higher
- PostgreSQL database with freight data
- Claude Desktop or compatible MCP client

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd frete_sistema
```

2. Install dependencies:
```bash
npm install
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env with your database credentials
```

4. Build the project:
```bash
npm run build
```

5. Start the MCP server:
```bash
npm run mcp:dev
```

## 💬 Natural Language Queries

The system understands natural language questions about freight data. Here are examples:

### Basic Queries

#### Finding Records
```
"Show me all records"
"List the latest freight records"
"Find records from last week"
"Show records with high prices"
```

#### Filtering by Date
```
"Show freight from January 2024"
"Find records between March and May"
"List today's freight"
"Show records from last 30 days"
```

#### Price Queries
```
"Find freight with prices over 1000"
"Show the most expensive shipments"
"List freight under 500 reais"
"What's the average freight price?"
```

#### Location Queries
```
"Show freight to São Paulo"
"Find shipments from Rio de Janeiro"
"List all routes to the Northeast"
"Which cities have the most freight?"
```

### Advanced Queries

#### Statistical Analysis
```
"What's the total freight value this month?"
"Show price trends over time"
"Compare prices between regions"
"Calculate average price per route"
```

#### Complex Filters
```
"Find urgent freight over 1000 reais to São Paulo"
"Show high-value shipments from last week"
"List pending freight sorted by price"
"Find the top 10 most expensive routes"
```

#### Business Intelligence
```
"Which routes are most profitable?"
"Show freight volume by month"
"Identify seasonal patterns"
"Find underutilized routes"
```

## 🔧 Using with Claude Desktop

### Configuration

Add to your Claude Desktop config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "mcp-frete": {
      "command": "node",
      "args": ["./dist/index.js"],
      "cwd": "/path/to/frete_sistema",
      "env": {
        "DATABASE_URL": "postgresql://user:password@localhost/frete_db"
      }
    }
  }
}
```

### Available Tools

#### 1. search_freight
Natural language search with AI-powered understanding:
```
Tool: search_freight
Query: "urgent shipments to São Paulo this week"
```

#### 2. get_freight_stats
Statistical analysis of freight data:
```
Tool: get_freight_stats
Parameters: {
  "metric": "total_value",
  "group_by": "month",
  "date_range": "last_6_months"
}
```

#### 3. analyze_routes
Route analysis and optimization:
```
Tool: analyze_routes
Parameters: {
  "origin": "Rio de Janeiro",
  "destination": "São Paulo",
  "analysis_type": "cost_trends"
}
```

## 📊 API Integration

### REST API Endpoints

The system also provides REST API access:

#### Search Endpoint
```bash
POST /api/search
Content-Type: application/json

{
  "query": "freight to São Paulo",
  "limit": 20,
  "offset": 0
}
```

#### Stats Endpoint
```bash
GET /api/stats?metric=total_value&group_by=day&range=7d
```

#### Routes Endpoint
```bash
GET /api/routes/analysis?origin=SP&destination=RJ
```

### Response Format

All responses follow this structure:
```json
{
  "success": true,
  "data": [...],
  "metadata": {
    "total": 100,
    "returned": 20,
    "query_time": "45ms"
  }
}
```

## 🎯 Best Practices

### Query Optimization

1. **Be Specific**: More specific queries return better results
   - ❌ "Show freight"
   - ✅ "Show urgent freight to São Paulo under 2000 reais"

2. **Use Natural Language**: The AI understands context
   - ✅ "What were the most expensive shipments last month?"
   - ✅ "Find freight that needs urgent delivery"

3. **Leverage Filters**: Combine multiple criteria
   - ✅ "High-value freight from SP to RJ in December"
   - ✅ "Pending shipments over 1000 reais sorted by date"

### Performance Tips

1. **Use Pagination**: For large result sets
   ```
   "Show me the first 50 freight records"
   "Get the next page of results"
   ```

2. **Cache Common Queries**: The system caches embeddings
   - Repeated similar queries are faster
   - Cache expires after 24 hours

3. **Batch Operations**: Group related queries
   ```
   "Show freight stats for Q1, Q2, Q3, and Q4"
   ```

## 🔍 Advanced Features

### Semantic Search

The system uses AI embeddings for intelligent search:

1. **Synonym Understanding**
   - "expensive" = "high-value" = "costly"
   - "urgent" = "priority" = "rush"

2. **Context Awareness**
   - "recent" understands relative time
   - "nearby" understands geographical proximity

3. **Intent Recognition**
   - Questions trigger analysis
   - Commands trigger actions

### Custom Embeddings

You can add domain-specific knowledge:

1. Create custom embedding file:
```json
{
  "terms": {
    "carga pesada": ["heavy freight", "oversized", "special cargo"],
    "região sul": ["RS", "SC", "PR", "southern region"]
  }
}
```

2. Load custom embeddings:
```bash
npm run embeddings:load custom-terms.json
```

## 🆘 Getting Help

### Built-in Help

Ask the system for help:
- "How do I search for freight?"
- "What queries can I make?"
- "Show me example searches"

### Documentation

- API Reference: `/docs/API_QUICKSTART.md`
- Troubleshooting: `/docs/TROUBLESHOOTING.md`
- Admin Guide: `/docs/MAINTENANCE_GUIDE.md`

### Support

- GitHub Issues: Report bugs and request features
- Email: support@example.com
- Documentation: https://docs.example.com

## 📝 Examples Gallery

### Common Use Cases

#### Daily Operations
```
"Show today's pending freight"
"List urgent deliveries for tomorrow"
"Find freight awaiting pickup"
```

#### Financial Analysis
```
"Calculate total revenue this month"
"Show profit margins by route"
"Compare prices with last month"
```

#### Route Planning
```
"Find the most efficient route to Salvador"
"Show available freight along the SP-RJ corridor"
"Optimize delivery sequence for multiple stops"
```

#### Customer Service
```
"Check status of freight #12345"
"Find all shipments for customer ABC Corp"
"Show delivery history for last week"
```

Remember: The more natural your query, the better the AI understands your intent!