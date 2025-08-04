# MCP Logística - Test Suite

Bateria completa de testes automatizados para o sistema MCP Logística.

## 📋 Estrutura de Testes

```
tests/mcp_logistica/
├── nlp/                    # Testes de processamento de linguagem natural
├── intent/                 # Testes de classificação de intenções
├── entity/                 # Testes de mapeamento de entidades
├── sql/                    # Testes de geração SQL e query processor
├── human_loop/            # Testes do sistema de confirmação
├── claude/                # Testes de integração com Claude
├── api/                   # Testes dos endpoints REST
├── security/              # Testes de segurança
├── persistence/           # Testes de persistência e aprendizado
├── integration/           # Testes de integração
├── fixtures/              # Dados de teste
├── mocks/                 # Mocks para testes
└── reports/               # Relatórios de cobertura e resultados
```

## 🚀 Executando os Testes

### Instalação das Dependências

```bash
pip install -r tests/mcp_logistica/requirements_test.txt
```

### Executar Todos os Testes

```bash
# Com cobertura completa
python tests/mcp_logistica/test_runner.py

# Ou usando pytest diretamente
pytest tests/mcp_logistica -v --cov=app.mcp_logistica
```

### Executar Categoria Específica

```bash
# Testes de NLP
python tests/mcp_logistica/test_runner.py --domain nlp

# Testes de segurança
python tests/mcp_logistica/test_runner.py --security

# Testes de performance
python tests/mcp_logistica/test_runner.py --performance
```

### Executar com Suite Runner

```bash
# Suite completa com relatório detalhado
python tests/mcp_logistica/test_suite_runner.py

# Categoria específica
python tests/mcp_logistica/test_suite_runner.py --category api

# Modo silencioso
python tests/mcp_logistica/test_suite_runner.py --quiet
```

## 📊 Categorias de Testes

### 1. **NLP (Natural Language Processing)**
- Normalização de queries em português
- Extração de entidades temporais
- Identificação de CNPJs, NFs, valores
- Tokenização e remoção de stopwords

### 2. **Intent Classification**
- Classificação de intenções (buscar, contar, status, etc.)
- Detecção de ações que requerem confirmação
- Cálculo de confiança
- Sugestões de follow-up

### 3. **Entity Mapping**
- Mapeamento dinâmico via CNPJ
- Agrupamento por raiz de CNPJ
- Similaridade de nomes (fuzzy matching)
- Detecção de padrões

### 4. **SQL Generation**
- Geração segura de consultas SQL
- Prevenção de SQL injection
- Otimização de queries
- Serialização de resultados

### 5. **Human-in-the-Loop**
- Sistema de confirmação de ações
- Validação de requisitos
- Handlers de ação
- Audit logging

### 6. **Claude Integration**
- Fallback para queries ambíguas
- Enriquecimento de respostas
- Manutenção de contexto de sessão
- Geração de insights

### 7. **API Endpoints**
- Autenticação e autorização
- Processamento de queries
- Gerenciamento de preferências
- Sistema de confirmações

### 8. **Security**
- Prevenção de SQL injection
- Validação de entrada
- Sanitização de dados
- Rate limiting

### 9. **Persistence & Learning**
- Aprendizado de preferências
- Detecção de padrões de uso
- Exportação/importação de dados
- Isolamento multi-usuário

### 10. **Integration**
- Fluxo completo de processamento
- Integração entre componentes
- Cenários do mundo real
- Performance end-to-end

## 📈 Métricas de Cobertura

### Meta de Cobertura
- **Global**: > 80%
- **Componentes críticos**: > 90%
- **Handlers de segurança**: 100%

### Visualizar Cobertura

```bash
# Gerar relatório HTML
pytest tests/mcp_logistica --cov=app.mcp_logistica --cov-report=html

# Abrir relatório
open tests/mcp_logistica/reports/coverage/index.html
```

## 🧪 Fixtures Principais

### `nlp_engine`
Motor de processamento de linguagem natural configurado.

### `query_processor`
Processador de queries com banco de dados mockado.

### `claude_integration`
Integração com Claude mockada para testes.

### `confirmation_system`
Sistema de confirmação configurado.

### `mock_user`
Usuário mockado para testes de autenticação.

## 🔧 Configuração de Testes

### conftest.py
Arquivo principal de configuração com:
- Fixtures compartilhadas
- Configuração do Flask app
- Mocks de banco de dados
- Geradores de dados de teste

### Performance Testing
```python
# Usar fixture performance_logger
def test_performance(nlp_engine, performance_logger):
    ctx = performance_logger.start("operation")
    # ... operação ...
    duration = performance_logger.end(ctx)
    assert duration < 0.1  # Max 100ms
```

## 🐛 Debugging

### Executar teste específico
```bash
pytest tests/mcp_logistica/nlp/test_nlp_engine.py::TestNLPEngine::test_normalize_query -v
```

### Com debugging
```bash
pytest tests/mcp_logistica/nlp/test_nlp_engine.py --pdb
```

### Logs detalhados
```bash
pytest tests/mcp_logistica -v -s --log-cli-level=DEBUG
```

## 📝 Escrevendo Novos Testes

### Estrutura Padrão
```python
class TestNovoComponente:
    """Descrição do componente"""
    
    def test_initialization(self, fixture):
        """Test initialization"""
        assert fixture is not None
        
    def test_feature_x(self, fixture):
        """Test specific feature"""
        result = fixture.method()
        assert result == expected
        
    def test_edge_case(self, fixture):
        """Test edge cases"""
        # Test boundary conditions
        
    def test_performance(self, fixture, performance_logger):
        """Test performance"""
        # Measure execution time
```

### Convenções
- Use docstrings descritivas
- Agrupe testes por funcionalidade
- Teste casos normais e extremos
- Inclua testes de segurança quando relevante
- Meça performance de operações críticas

## 🚨 Testes Críticos

Os seguintes testes são considerados críticos e devem sempre passar:

1. **SQL Injection Prevention** - `test_sql_injection_prevention_basic`
2. **Authentication Required** - `test_authentication_required`
3. **Entity Resolution** - `test_resolve_entity_reference_exact`
4. **Query Processing** - `test_process_simple_query`
5. **Confirmation Validation** - `test_validation_rules_*`

## 📊 Relatórios

### Relatório de Resumo
Gerado automaticamente em: `tests/mcp_logistica/reports/test_summary.json`

### Relatório de Cobertura
- HTML: `tests/mcp_logistica/reports/coverage/index.html`
- JSON: `tests/mcp_logistica/reports/coverage.json`

### JUnit XML
Para integração com CI/CD: `tests/mcp_logistica/reports/junit.xml`

## 🔄 Integração Contínua

### GitHub Actions
```yaml
- name: Run MCP Tests
  run: |
    pip install -r tests/mcp_logistica/requirements_test.txt
    python tests/mcp_logistica/test_suite_runner.py
```

### Pre-commit Hook
```bash
#!/bin/bash
python tests/mcp_logistica/test_runner.py --domain security
```

## 📞 Suporte

Para problemas ou dúvidas sobre os testes:
1. Verifique os logs em `tests/mcp_logistica/reports/`
2. Execute com `--pdb` para debugging
3. Consulte a documentação do componente específico