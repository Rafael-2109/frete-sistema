#!/usr/bin/env python3
"""
Script para corrigir conflitos entre ValidationUtils genérica e específica
"""

import os
import re
from pathlib import Path

def fix_validation_conflicts():
    """Corrige conflitos entre ValidationUtils"""
    
    print("🔧 CORRIGINDO CONFLITOS DE ValidationUtils")
    print("=" * 50)
    
    # Definir regras de correção
    corrections = {
        # utils/ deve usar BaseValidationUtils (genérica)
        'utils/': {
            'from .validation_utils import ValidationUtils': 'from .validation_utils import BaseValidationUtils',
            'ValidationUtils()': 'BaseValidationUtils()',
            'ValidationUtils is not None': 'BaseValidationUtils is not None',
            '_validation_utils_available = True': '_validation_utils_available = True',
            'ValidationUtils = None': 'BaseValidationUtils = None'
        },
        
        # validators/ deve usar ValidationUtils (específica de negócio)
        'validators/': {
            'from ..utils.validation_utils import ValidationUtils': 'from .data_validator import ValidationUtils',
            'from .data_validator import ValidationUtils as DataValidator': 'from .data_validator import ValidationUtils as DataValidator'
        }
    }
    
    # Arquivos específicos para corrigir
    files_to_fix = [
        'utils/utils_manager.py',
        'utils/__init__.py',
        'validators/validator_manager.py',
        'validators/__init__.py'
    ]
    
    total_fixes = 0
    
    for file_path in files_to_fix:
        if not os.path.exists(file_path):
            print(f"❌ Arquivo não encontrado: {file_path}")
            continue
        
        print(f"\n🔧 Corrigindo: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            file_fixes = 0
            
            # Determinar pasta para aplicar regras específicas
            folder = None
            if file_path.startswith('utils/'):
                folder = 'utils/'
            elif file_path.startswith('validators/'):
                folder = 'validators/'
            
            if folder and folder in corrections:
                for old_pattern, new_pattern in corrections[folder].items():
                    if old_pattern in content:
                        content = content.replace(old_pattern, new_pattern)
                        file_fixes += 1
                        print(f"  ✅ {old_pattern} → {new_pattern}")
            
            # Salvar se houve alterações
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"  💾 Arquivo salvo com {file_fixes} correções")
                total_fixes += file_fixes
            else:
                print(f"  ℹ️ Nenhuma correção necessária")
                
        except Exception as e:
            print(f"❌ Erro ao processar {file_path}: {e}")
    
    print(f"\n📊 RESUMO:")
    print(f"Total de correções aplicadas: {total_fixes}")
    
    return total_fixes

def verify_imports():
    """Verifica se os imports estão corretos"""
    
    print("\n🔍 VERIFICANDO IMPORTS CORRIGIDOS:")
    print("-" * 40)
    
    test_cases = [
        {
            'description': 'BaseValidationUtils (genérica)',
            'test': 'from utils.validation_utils import BaseValidationUtils; BaseValidationUtils()'
        },
        {
            'description': 'ValidationUtils (negócio)',
            'test': 'from validators.data_validator import ValidationUtils; ValidationUtils()'
        }
    ]
    
    for case in test_cases:
        try:
            exec(case['test'])
            print(f"✅ {case['description']}: OK")
        except Exception as e:
            print(f"❌ {case['description']}: {e}")

def create_usage_guide():
    """Cria guia de uso das duas ValidationUtils"""
    
    guide = """
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
"""
    
    with open('GUIA_VALIDATION_UTILS.md', 'w', encoding='utf-8') as f:
        f.write(guide)
    
    print("\n📝 Guia criado: GUIA_VALIDATION_UTILS.md")

def main():
    """Função principal"""
    print("🚀 Iniciando correção de conflitos ValidationUtils...")
    
    # 1. Corrigir conflitos
    total_fixes = fix_validation_conflicts()
    
    # 2. Verificar imports
    verify_imports()
    
    # 3. Criar guia
    create_usage_guide()
    
    print(f"\n🎉 CORREÇÃO CONCLUÍDA!")
    print(f"📊 {total_fixes} correções aplicadas")
    print(f"📝 Guia de uso criado")
    print(f"🧪 Execute os testes para verificar se tudo funciona")

if __name__ == "__main__":
    main() 