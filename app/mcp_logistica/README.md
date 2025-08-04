# MCP Logística - Sistema de Consultas em Linguagem Natural

Sistema autônomo para processar consultas em linguagem natural sobre dados logísticos, com suporte completo para português brasileiro.

## 🚀 Características Principais

- **Processamento de Linguagem Natural (NLP)** em português
- **Mapeamento Dinâmico de Entidades** sem hardcode
- **Classificação de Intenções** com alta precisão
- **Sistema de Preferências** com aprendizado contínuo
- **Human-in-the-Loop** para ações críticas
- **Tratamento de Erros** com fallback inteligente
- **API REST** integrada com Flask

## 📦 Componentes

### 1. NLP Engine (`nlp_engine.py`)
- Normalização e tokenização para pt-BR
- Extração de entidades (datas, valores, locais, etc.)
- Análise de contexto e urgência
- Geração de SQL a partir de linguagem natural

### 2. Entity Mapper (`entity_mapper.py`)
- Resolução dinâmica de referências
- Agrupamento por CNPJ (primeiros 8 dígitos)
- Fuzzy matching para nomes similares
- Detecção automática de padrões

### 3. Intent Classifier (`intent_classifier.py`)
- Classificação multi-nível de intenções
- Suporte para intenções compostas
- Validação de requisitos por intenção
- Sugestões de próximos passos

### 4. Query Processor (`query_processor.py`)
- Integração de todos os componentes
- Construção dinâmica de consultas SQL
- Pós-processamento de resultados
- Geração de sugestões contextuais

### 5. Preference Manager (`preference_manager.py`)
- Aprendizado de padrões de uso
- Personalização por usuário
- Sugestões baseadas em histórico
- Exportação/importação de preferências

### 6. Confirmation System (`confirmation_system.py`)
- Confirmação para ações críticas
- Múltiplos tipos de ação (reagendar, cancelar, aprovar)
- Validação de regras de negócio
- Auditoria completa

### 7. Error Handler (`error_handler.py`)
- Classificação de erros por categoria
- Estratégias de fallback específicas
- Detecção de padrões de erro
- Notificação de erros críticos

## 🔧 Instalação

1. **Instalar dependências:**
```bash
pip install jellyfish  # Para fuzzy matching
```

2. **Criar tabelas no banco:**
```python
from app.mcp_logistica.models import create_mcp_tables, seed_initial_data
create_mcp_tables()
seed_initial_data()
```

3. **Registrar no Flask:**
```python
from app.mcp_logistica.flask_integration import register_blueprint
register_blueprint(app)
```

## 📋 Exemplos de Uso

### Consultas Simples
```
"Quantas entregas estão atrasadas?"
"Mostrar pedidos do Assaí"
"Status da NF 12345"
"Entregas de hoje em SP"
```

### Consultas Complexas
```
"Listar todas as entregas atrasadas do Carrefour em São Paulo nos últimos 7 dias"
"Qual a tendência de atrasos por transportadora este mês?"
"Reagendar entrega do pedido 789 para amanhã"
```

### Ações com Confirmação
```
"Cancelar pedido 456"
"Aprovar frete divergente da NF 789"
"Desbloquear entregas pendentes do cliente X"
```

## 🔌 API Endpoints

### POST `/api/mcp/logistica/query`
Processa consulta em linguagem natural.

**Request:**
```json
{
    "query": "Quantas entregas estão atrasadas hoje?"
}
```

**Response:**
```json
{
    "success": true,
    "data": {
        "total": 15,
        "contexto": "Quantidade moderada (15)"
    },
    "intent": {
        "primary": "contar",
        "confidence": 0.85
    },
    "suggestions": [
        "Ver detalhes dos itens contados",
        "Comparar com período anterior"
    ]
}
```

### GET `/api/mcp/logistica/suggestions?q=entregas`
Obtém sugestões de consultas.

### GET `/api/mcp/logistica/preferences`
Obtém preferências e insights do usuário.

### POST `/api/mcp/logistica/confirmations/{id}/confirm`
Confirma uma ação pendente.

## 🧠 Aprendizado e Personalização

O sistema aprende continuamente com:
- Padrões de consulta mais frequentes
- Períodos preferidos (hoje, semana, mês)
- Domínios mais acessados (entregas, pedidos, fretes)
- Formatos de resposta preferidos

## 🛡️ Segurança

- Autenticação obrigatória via Flask-Login
- Validação de todas as entradas
- Proteção contra SQL Injection
- Auditoria de ações críticas
- Permissões granulares por usuário

## 📊 Monitoramento

### Estatísticas Disponíveis
- Taxa de sucesso de consultas
- Erros por categoria
- Tempo médio de resposta
- Intenções mais comuns
- Padrões de uso por usuário

### Health Check
```bash
GET /api/mcp/logistica/health
```

## 🔄 Integração com Sistema Existente

O MCP se integra perfeitamente com os modelos existentes:
- `EntregaMonitorada`
- `Pedido`
- `Embarque`
- `Frete`

Usa as mesmas tabelas e relacionamentos, apenas adiciona inteligência na camada de consulta.

## 🚧 Limitações Conhecidas

1. **Contexto de Sessão**: Ainda não mantém contexto entre consultas
2. **Ambiguidade**: Pode ter dificuldade com consultas muito ambíguas
3. **Performance**: Consultas muito complexas podem ser lentas

## 🔮 Próximos Passos

1. Adicionar suporte para consultas contextuais
2. Implementar cache inteligente
3. Adicionar mais tipos de visualização
4. Expandir para outros domínios do sistema
5. Implementar feedback visual em tempo real

## 📝 Contribuindo

Para adicionar novos tipos de consulta:

1. Adicione padrões em `nlp_engine.py`
2. Crie nova intenção em `intent_classifier.py`
3. Implemente query builder em `query_processor.py`
4. Adicione testes correspondentes

## 🐛 Troubleshooting

### Erro: "Entidade não encontrada"
- Verifique ortografia
- Use nome completo ou CNPJ
- Sistema sugerirá alternativas similares

### Erro: "Intenção não compreendida"
- Use palavras-chave como: buscar, contar, listar
- Seja mais específico na consulta
- Veja exemplos de consultas válidas

### Performance lenta
- Reduza período de busca
- Use filtros mais específicos
- Verifique índices do banco de dados