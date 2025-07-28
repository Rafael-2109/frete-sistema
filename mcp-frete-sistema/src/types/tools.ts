/**
 * MCP Tool Type Definitions for Frete Sistema
 */

// Query Analyzer Types
export interface QueryAnalyzerInput {
  query: string;
  context?: {
    sessionId?: string;
    previousQueries?: Array<{
      query: string;
      timestamp: string;
      domain?: string;
    }>;
    userProfile?: {
      role: 'admin' | 'operator' | 'driver' | 'customer' | 'manager';
      preferences?: Record<string, any>;
    };
  };
  options?: {
    deepAnalysis?: boolean;
    extractEntities?: boolean;
    detectTemporal?: boolean;
  };
}

export interface QueryAnalyzerOutput {
  analysis: {
    intent: {
      primary: 'query' | 'create' | 'update' | 'delete' | 'report' | 'monitor' | 'help';
      confidence: number;
      subIntents?: string[];
    };
    domain: {
      primary: 'fretes' | 'pedidos' | 'entregas' | 'embarques' | 'financeiro' | 'transportadoras' | 'monitoramento' | 'multi-domain';
      secondary?: string[];
      confidence: number;
    };
    entities: Array<{
      type: 'order_id' | 'freight_id' | 'customer' | 'driver' | 'vehicle' | 'route' | 'date' | 'value' | 'status';
      value: string;
      normalized: string;
      position: {
        start: number;
        end: number;
      };
    }>;
    temporal: {
      detected: boolean;
      references?: Array<{
        type: 'absolute' | 'relative' | 'range' | 'recurring';
        value: string;
        startDate?: string;
        endDate?: string;
      }>;
    };
    semantic: {
      keywords: string[];
      concepts: Array<{
        concept: string;
        relevance: number;
      }>;
      sentiment: 'positive' | 'neutral' | 'negative' | 'urgent';
    };
    suggestions?: Array<{
      type: 'clarification' | 'refinement' | 'alternative' | 'expansion';
      suggestion: string;
      reason: string;
    }>;
  };
  metadata: {
    processingTime: number;
    complexity: 'simple' | 'moderate' | 'complex';
    requiresAuth: boolean;
    suggestedTools: string[];
  };
}

// Data Loader Types
export interface DataLoaderInput {
  domain: 'fretes' | 'pedidos' | 'entregas' | 'embarques' | 'financeiro' | 'transportadoras' | 'monitoramento';
  filters?: {
    ids?: string[];
    dateRange?: {
      start: string;
      end: string;
      field?: 'created_at' | 'updated_at' | 'delivery_date' | 'scheduled_date';
    };
    status?: Array<'pending' | 'active' | 'completed' | 'cancelled' | 'delayed' | 'in_transit' | 'delivered'>;
    search?: {
      term: string;
      fields?: string[];
    };
    customFilters?: Record<string, any>;
  };
  options?: {
    limit?: number;
    offset?: number;
    orderBy?: {
      field: string;
      direction?: 'asc' | 'desc';
    };
    include?: Array<'related' | 'history' | 'metadata' | 'calculations' | 'enrichments'>;
    format?: 'full' | 'summary' | 'minimal' | 'custom';
    enrichData?: boolean;
  };
  aggregations?: Array<{
    type: 'count' | 'sum' | 'avg' | 'min' | 'max' | 'group_by';
    field: string;
    groupBy?: string;
    alias?: string;
  }>;
}

export interface DataLoaderOutput {
  data: Array<Record<string, any>>;
  metadata: {
    domain: string;
    total: number;
    returned: number;
    offset: number;
    hasMore: boolean;
    executionTime: number;
    query?: {
      sql: string;
      params: any[];
    };
  };
  aggregations?: Record<string, {
    value: number | Record<string, any>;
    groups?: any[];
  }>;
  enrichments?: {
    insights?: Array<{
      type: string;
      message: string;
      severity: 'info' | 'warning' | 'critical';
      data?: any;
    }>;
    trends?: Array<{
      metric: string;
      direction: 'up' | 'down' | 'stable';
      percentage: number;
    }>;
    recommendations?: Array<{
      action: string;
      reason: string;
      impact: string;
    }>;
  };
  errors?: Array<{
    code: string;
    message: string;
    field?: string;
  }>;
}

// Context Manager Types
export interface ContextManagerInput {
  action: 'get' | 'set' | 'update' | 'clear' | 'merge' | 'analyze';
  sessionId: string;
  scope?: 'session' | 'user' | 'global' | 'domain';
  data?: {
    conversation?: {
      history?: Array<{
        role: 'user' | 'assistant' | 'system';
        content: string;
        timestamp: string;
        metadata?: any;
      }>;
      currentTopic?: string;
      activeFilters?: any;
      preferences?: any;
    };
    user?: {
      id?: string;
      role?: string;
      permissions?: string[];
      preferences?: {
        language?: string;
        timezone?: string;
        dateFormat?: string;
        defaultDomain?: string;
      };
    };
    domain?: {
      current?: string;
      history?: Array<{
        domain: string;
        timestamp: string;
        queries: number;
      }>;
      cache?: any;
    };
    workflow?: {
      current?: string;
      step?: number;
      data?: any;
      history?: any[];
    };
    memory?: {
      shortTerm?: any[];
      longTerm?: any;
      insights?: any[];
    };
  };
  options?: {
    persist?: boolean;
    ttl?: number;
    encrypt?: boolean;
    compress?: boolean;
  };
}

export interface ContextManagerOutput {
  success: boolean;
  action: string;
  sessionId: string;
  context?: {
    conversation?: any;
    user?: any;
    domain?: any;
    workflow?: any;
    memory?: any;
    metadata?: {
      created: string;
      updated: string;
      version: number;
      size: number;
    };
  };
  analysis?: {
    patterns?: Array<{
      type: string;
      frequency: number;
      significance: number;
    }>;
    insights?: Array<{
      type: string;
      message: string;
      confidence: number;
    }>;
    recommendations?: Array<{
      action: string;
      reason: string;
    }>;
  };
  errors?: Array<{
    code: string;
    message: string;
  }>;
}

// Response Generator Types
export interface ResponseGeneratorInput {
  analysis: {
    intent: any;
    domain: any;
    entities?: any[];
    temporal?: any;
    semantic?: any;
  };
  data: {
    results?: any[];
    metadata?: any;
    aggregations?: any;
    enrichments?: any;
  };
  context?: {
    user?: any;
    conversation?: any;
    preferences?: any;
  };
  options?: {
    format?: 'text' | 'markdown' | 'html' | 'json' | 'table' | 'chart';
    style?: 'formal' | 'conversational' | 'technical' | 'executive';
    length?: 'brief' | 'normal' | 'detailed' | 'comprehensive';
    includeInsights?: boolean;
    includeRecommendations?: boolean;
    includeVisualizations?: boolean;
    language?: 'pt-BR' | 'en-US' | 'es-ES';
  };
  templates?: {
    header?: string;
    body?: string;
    footer?: string;
    error?: string;
  };
}

export interface ResponseGeneratorOutput {
  response: {
    content: string;
    format: 'text' | 'markdown' | 'html' | 'json' | 'table' | 'chart';
    sections?: Array<{
      type: 'summary' | 'data' | 'insights' | 'recommendations' | 'actions' | 'warnings';
      title: string;
      content: string;
      priority?: 'high' | 'medium' | 'low';
      metadata?: any;
    }>;
    data?: {
      summary?: {
        total: number;
        highlights: any[];
        metrics: any;
      };
      details?: any[];
      visualizations?: Array<{
        type: 'chart' | 'table' | 'map' | 'timeline';
        config: any;
        data: any[];
      }>;
    };
    actions?: Array<{
      type: 'button' | 'link' | 'command' | 'suggestion';
      label: string;
      action: string;
      params?: any;
      icon?: string;
    }>;
    metadata?: {
      confidence: number;
      sources: string[];
      processingTime: number;
      tokens?: {
        input: number;
        output: number;
      };
      cache?: {
        hit: boolean;
        key: string;
      };
    };
  };
  followUp?: {
    suggestions?: Array<{
      text: string;
      intent: string;
      relevance: number;
    }>;
    relatedTopics?: Array<{
      topic: string;
      query: string;
    }>;
  };
  errors?: Array<{
    code: string;
    message: string;
    userMessage: string;
  }>;
}