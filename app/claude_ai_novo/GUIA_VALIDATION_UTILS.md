
# 📋 GUIA DE USO - ValidationUtils

## 🎯 DUAS CLASSES DIFERENTES:

### 1. **BaseValidationUtils** (Genérica)
**Arquivo**: `utils/validation_utils.py`  
**Uso**: Validações genéricas, segurança, sanitização  

```python
from utils.validation_utils import BaseValidationUtils, get_validation_utils

# Instanciação
validator = BaseValidationUtils()
# ou
validator = get_validation_utils()

# Métodos principais:
validator.validate(data, rules)
validator.validate_query(query)
validator.validate_context(context)
validator.sanitize_input(input_data)
```

### 2. **ValidationUtils** (Negócio)
**Arquivo**: `validators/data_validator.py`  
**Uso**: Validações específicas de entregas, estatísticas, métricas  

```python
from validators.data_validator import ValidationUtils, get_validationutils

# Instanciação
validator = ValidationUtils()
# ou
validator = get_validationutils()

# Métodos principais:
validator._verificar_prazo_entrega(entrega)
validator._calcular_metricas_prazo(entregas)
validator._calcular_estatisticas_especificas(analise, filtros)
```

## ✅ REGRAS DE USO:

1. **utils/** → Use `BaseValidationUtils` (genérica)
2. **validators/** → Use `ValidationUtils` (específica)
3. **Nunca misturar** as duas no mesmo arquivo
4. **Sempre especificar** o import completo para evitar ambiguidade

## 🚨 EVITAR:

```python
# ❌ AMBÍGUO - qual ValidationUtils?
from some_module import ValidationUtils

# ✅ ESPECÍFICO - claro qual usar
from utils.validation_utils import BaseValidationUtils
from validators.data_validator import ValidationUtils
```
