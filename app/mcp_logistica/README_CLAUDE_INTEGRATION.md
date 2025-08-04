# Claude 4 Sonnet Integration for MCP Logística

## Overview

This integration adds Claude 4 Sonnet as an intelligent fallback and enhancement layer for the MCP Logística natural language query system. When the NLP engine cannot confidently translate queries to SQL or when users need more contextual insights, Claude provides natural language responses and suggestions.

## Features

### 1. **Intelligent Fallback**
- Activates when NLP confidence is below 70%
- Handles queries with missing entities
- Provides direct answers when SQL generation fails
- Gracefully degrades when Claude is unavailable

### 2. **Session Context Management**
- Maintains conversation history per user session
- Stores up to 10 recent queries for context
- Uses session context to provide more relevant responses
- Supports session clearing for privacy

### 3. **Hybrid Response System**
- Combines SQL query results with Claude insights
- Provides business-level interpretations of data
- Suggests follow-up queries based on results
- Enhances responses with actionable recommendations

### 4. **Automatic Prompt Generation**
- Generates optimized prompts based on intent and entities
- Includes relevant database schema context
- Incorporates session history for continuity
- Adapts prompts based on query complexity

## Configuration

### Environment Variables

Add to your `.env` file:

```bash
# Claude AI Configuration
ANTHROPIC_API_KEY=your-anthropic-api-key-here
```

### Feature Flags

The integration supports several modes:

1. **Disabled Mode**: When no API key is configured
2. **Fallback Mode**: Only activates for low-confidence queries
3. **Enhancement Mode**: Always adds insights to SQL results

## API Endpoints

### Query Processing

**POST** `/api/mcp/logistica/query`

Enhanced request body:
```json
{
    "query": "analise os atrasos desta semana",
    "enhance_with_claude": true  // Optional: force Claude enhancement
}
```

Enhanced response:
```json
{
    "success": true,
    "data": {...},
    "natural_response": "Encontrei 15 entregas atrasadas esta semana. A maioria dos atrasos...",
    "claude_insights": {
        "used": true,
        "response_type": "hybrid",
        "confidence": 0.9
    },
    "suggestions": [
        "Ver detalhes das transportadoras com mais atrasos",
        "Analisar padrões de atraso por região",
        "Comparar com a semana anterior"
    ]
}
```

### Session Management

**GET** `/api/mcp/logistica/session/summary`
- Returns summary of current session interactions

**POST** `/api/mcp/logistica/session/clear`
- Clears session context for the current user

**GET** `/api/mcp/logistica/claude/config`
- Returns Claude configuration and feature status

## Usage Examples

### 1. Complex Analysis Query
```
Query: "analise a performance das entregas para São Paulo comparando com o mês passado"

Response:
- SQL results showing delivery metrics
- Claude insights about trends and patterns
- Recommendations for improvement
- Suggested follow-up queries
```

### 2. Exploratory Query
```
Query: "o que posso fazer para melhorar o tempo de entrega?"

Response:
- Direct Claude response with actionable suggestions
- Analysis based on current data patterns
- Specific recommendations for the logistics context
```

### 3. Low-Confidence Query
```
Query: "mostrar problemas"

Response:
- Claude asks for clarification
- Suggests specific query formats
- Provides examples of valid queries
```

## Error Handling

The integration includes robust error handling:

1. **API Key Missing**: System continues without Claude, using only NLP
2. **API Errors**: Logs errors and returns SQL-only results
3. **Timeout Handling**: Falls back to basic responses
4. **Rate Limiting**: Implements retry logic with exponential backoff

## Performance Considerations

- Claude calls are made asynchronously when possible
- Responses are cached for identical queries within 5 minutes
- Session contexts are stored in memory for fast access
- Prompts are optimized to minimize token usage

## Security

- API keys are never exposed in responses
- Session contexts are isolated per user
- Sensitive data is filtered from Claude prompts
- All interactions are logged for audit purposes

## Testing

Run the test script:

```bash
python app/mcp_logistica/test_claude_integration.py
```

This will test:
- Fallback scenarios
- Session context management
- Various query types
- Error handling

## Monitoring

Monitor Claude integration performance:
- Check `/api/mcp/logistica/health` for system status
- Review logs for Claude API errors
- Track usage metrics via `/api/mcp/logistica/stats`

## Future Enhancements

1. **Fine-tuning**: Custom prompts for specific domains
2. **Caching**: Redis-based response caching
3. **Streaming**: Real-time response streaming
4. **Multi-language**: Support for queries in multiple languages
5. **Learning**: Feedback loop to improve responses over time