# 🎯 Quando Flask Context é Necessário

## ✅ NECESSÁRIO - Módulos que acessam banco de dados

### 1. **Loaders** ✅ NECESSÁRIO
```python
# Acessam db.session e modelos SQLAlchemy
from app import db
from app.pedidos.models import Pedido
query = Pedido.query.filter(...)  # PRECISA DE FLASK CONTEXT!
```

### 2. **Providers** ✅ NECESSÁRIO  
```python
# Se acessam banco diretamente (não através de loaders)
from app import db
db.session.execute(...)  # PRECISA DE FLASK CONTEXT!
```

## ❌ NÃO NECESSÁRIO - Módulos que apenas processam dados

### 1. **Analyzers** ❌ NÃO PRECISA
```python
# Apenas analisam texto/consultas
def analyze_query(query: str):
    # Processa string, detecta intenções
    # NÃO acessa banco
    return {"intent": "consultar_pedidos"}
```

### 2. **Processors** ❌ NÃO PRECISA
```python
# Processam dados já carregados
def process_data(data: dict):
    # Transforma, formata, calcula
    # NÃO acessa banco
    return formatted_data
```

### 3. **Mappers** ❌ NÃO PRECISA
```python
# Mapeiam campos e conceitos
def map_field(field_name: str):
    # Usa dicionários em memória
    # NÃO acessa banco
    return semantic_terms
```

### 4. **Memorizers** ❌ NÃO PRECISA (geralmente)
```python
# Armazenam em memória ou Redis
self.memory = {}  # Memória local
redis_cache.set(...)  # Redis não precisa Flask context
```

### 5. **Learners** ❌ NÃO PRECISA
```python
# Aprendem padrões de dados
def learn_pattern(data):
    # Algoritmos ML, estatísticas
    # NÃO acessa banco
    return pattern
```

### 6. **Coordinators** ❌ NÃO PRECISA
```python
# Coordenam outros módulos
def coordinate_agents(agents):
    # Lógica de coordenação
    # NÃO acessa banco diretamente
    return results
```

### 7. **Orchestrators** ❌ NÃO PRECISA
```python
# Orquestram fluxo de trabalho
def orchestrate_flow(query):
    # Chama outros módulos
    # NÃO acessa banco diretamente
    analyzer.analyze(query)
    loader.load_data()  # Loader cuida do context
```

### 8. **Enrichers** ❌ NÃO PRECISA
```python
# Enriquecem dados já carregados
def enrich_data(data):
    # Adiciona informações calculadas
    # NÃO acessa banco
    return enriched_data
```

### 9. **Validators** ❌ NÃO PRECISA
```python
# Validam estruturas de dados
def validate_data(data):
    # Verifica regras, formatos
    # NÃO acessa banco
    return is_valid
```

## 🔍 Regra Simples

**Flask Context é necessário APENAS quando:**

1. **Importa modelos**: `from app.pedidos.models import Pedido`
2. **Usa db.session**: `db.session.query(...)`, `db.session.execute(...)`
3. **Usa current_app**: `current_app.config['KEY']`
4. **Usa request**: `request.json`, `request.args`
5. **Usa session**: `session['user_id']`

## 💡 Por que só Loaders/Providers precisam?

```
Fluxo de Dados:
1. Analyzer analisa query (sem banco) ❌
2. Orchestrator coordena (sem banco) ❌
3. Loader carrega dados (COM BANCO) ✅
4. Processor processa (sem banco) ❌
5. Enricher enriquece (sem banco) ❌
```

## ✅ Solução Atual é Suficiente

A correção feita no `claude_transition.py` é suficiente porque:

1. **Flask context criado no início** - Todo o sistema roda dentro
2. **Loaders são os únicos que acessam banco** - E estão protegidos
3. **Outros módulos não precisam** - Apenas processam dados

## 🎯 Resumo

- **90% dos módulos NÃO precisam** de Flask context
- **Apenas Loaders e alguns Providers precisam**
- **Solução atual já resolve** o problema completamente 