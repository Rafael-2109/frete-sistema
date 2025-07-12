# 🎯 PLANO DE AÇÃO - CORREÇÃO DE IMPORTS
## Análise Prioritizada para Correção Eficiente

## 📊 RESUMO EXECUTIVO
- **Total de problemas REAIS**: 798
- **Arquivos afetados**: 26

## 🚨 TOP 10 IMPORTS MAIS PROBLEMÁTICOS
*(Foque nestes primeiro para máximo impacto)*

1. **`app`** - 92 ocorrências (other)
1. **`openpyxl.styles`** - 44 ocorrências (other)
1. **`dataclasses`** - 19 ocorrências (python_stdlib)
1. **`time`** - 18 ocorrências (python_stdlib)
1. **`flask_login`** - 18 ocorrências (other)
1. **`excel`** - 16 ocorrências (other)
1. **`flask_fallback`** - 16 ocorrências (other)
1. **`specialist_agents`** - 14 ocorrências (other)
1. **`external_api_integration`** - 14 ocorrências (external_integration)
1. **`domain`** - 12 ocorrências (other)

## 📁 ARQUIVOS CRÍTICOS
*(Arquivos com mais de 10 problemas)*

### `utils\__init__.py` (52 problemas)
  - other: 24
  - base_classes: 18
  - internal_components: 10

### `commands\__init__.py` (34 problemas)
  - other: 29
  - internal_components: 5

### `integration\__init__.py` (32 problemas)
  - external_integration: 28
  - internal_components: 4

### `mappers\__init__.py` (32 problemas)
  - internal_components: 32

### `analyzers\__init__.py` (30 problemas)
  - internal_components: 30

### `processors\__init__.py` (26 problemas)
  - internal_components: 24
  - base_classes: 2

### `orchestrators\__init__.py` (20 problemas)
  - internal_components: 10
  - other: 10

### `coordinators\__init__.py` (18 problemas)
  - other: 16
  - internal_components: 2

### `learners\__init__.py` (18 problemas)
  - other: 18

### `loaders\loader_manager.py` (18 problemas)
  - internal_components: 18

## 📋 AÇÕES POR CATEGORIA

### 1. BIBLIOTECA PADRÃO PYTHON
*13 módulos afetados*

**AÇÃO**: Verificar se estão instalados no ambiente Python
```python
# Estes são módulos padrão que deveriam estar disponíveis
import traceback
import subprocess
import time
import threading
import dataclasses
```

- `traceback` (9 ocorrências)

- `subprocess` (3 ocorrências)

- `time` (18 ocorrências)
- ... e mais 10 módulos

### 2. COMPONENTES INTERNOS DO SISTEMA
*82 módulos afetados*

**AÇÃO**: Verificar se arquivos existem e imports estão corretos
```python
# Exemplo de correções comuns:
# from .analyzer_manager import AnalyzerManager
# from ..utils.base_classes import BaseComponent
```

- `intention_analyzer` (2 ocorrências)

- `query_analyzer` (2 ocorrências)

- `metacognitive_analyzer` (2 ocorrências)
- ... e mais 79 módulos

### 3. CLASSES BASE E UTILITÁRIOS
*11 módulos afetados*

**AÇÃO**: Criar/verificar classes base em utils/

- `openpyxl.utils` (8 ocorrências)

- `basic_config` (1 ocorrências)

- `system_config` (7 ocorrências)
- ... e mais 8 módulos

### 4. COMPONENTES ESPECÍFICOS DE DOMÍNIO
*2 módulos afetados*


- `embarques_agent` (1 ocorrências)

- `pedidos_agent` (1 ocorrências)

### 5. INTEGRAÇÕES EXTERNAS
*4 módulos afetados*

**AÇÃO**: Verificar configuração de integrações externas

- `app.claude_ai_novo.integration.claude.claude_client` (2 ocorrências)

- `external_api_integration` (14 ocorrências)

- `web_integration` (10 ocorrências)
- ... e mais 1 módulos

## 🔧 CORREÇÕES SUGERIDAS

### 1. IMPORTS DA BIBLIOTECA PADRÃO
```python
# Adicione no início dos arquivos afetados:
import dataclasses
import time
import traceback
```

### 2. PADRÃO DE IMPORTS INTERNOS
```python
# Use imports relativos para componentes internos:
from .manager import ComponentManager
from ..utils.base_classes import BaseClass
from ...config import system_config
```

### 3. VERIFICAÇÃO RÁPIDA
```bash
# Execute para verificar correções:
python -m app.claude_ai_novo.verificar_imports_quebrados
```