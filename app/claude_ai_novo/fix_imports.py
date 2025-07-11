#!/usr/bin/env python3
"""
Script para corrigir imports quebrados automaticamente
"""

import os
import re
from pathlib import Path

def fix_validation_utils_imports():
    """Corrige imports do ValidationUtils"""
    
    print("🔧 Corrigindo imports do ValidationUtils...")
    
    # Arquivos que precisam ser corrigidos
    files_to_fix = [
        'validators/validator_manager.py',
        'validators/__init__.py'
    ]
    
    for file_path in files_to_fix:
        if not os.path.exists(file_path):
            print(f"❌ Arquivo não encontrado: {file_path}")
            continue
            
        print(f"🔧 Corrigindo: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Substituir imports incorretos
            fixes = [
                # Corrigir import direto do ValidationUtils
                (r'from \.data_validator import ValidationUtils', 
                 'from ..utils.validation_utils import ValidationUtils'),
                
                # Corrigir import no __init__.py
                (r'from \.data_validator import ValidationUtils as DataValidator',
                 'from ..utils.validation_utils import ValidationUtils as DataValidator'),
                
                # Corrigir referência ao ValidationUtils no __init__.py
                (r'from \.data_validator import ValidationUtils',
                 'from ..utils.validation_utils import ValidationUtils'),
            ]
            
            content_changed = False
            for old_pattern, new_pattern in fixes:
                if re.search(old_pattern, content):
                    content = re.sub(old_pattern, new_pattern, content)
                    content_changed = True
                    print(f"  ✅ Corrigido: {old_pattern} -> {new_pattern}")
            
            if content_changed:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"  💾 Arquivo salvo: {file_path}")
            else:
                print(f"  ℹ️ Nenhuma correção necessária em: {file_path}")
                
        except Exception as e:
            print(f"❌ Erro ao processar {file_path}: {e}")

def fix_utils_manager_imports():
    """Corrige imports no utils_manager.py"""
    
    print("🔧 Corrigindo imports no utils_manager.py...")
    
    file_path = 'utils/utils_manager.py'
    
    if not os.path.exists(file_path):
        print(f"❌ Arquivo não encontrado: {file_path}")
        return
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Remover classe mock ValidationUtils se existir
        mock_class_pattern = r'# ValidationUtils não existe, criar classe mock.*?return isinstance\(context, dict\)'
        if re.search(mock_class_pattern, content, re.DOTALL):
            content = re.sub(mock_class_pattern, '', content, flags=re.DOTALL)
            print("  ✅ Removida classe mock ValidationUtils")
        
        # Garantir que o import está correto
        import_pattern = r'from \.validation_utils import ValidationUtils'
        if not re.search(import_pattern, content):
            # Adicionar import se não existir
            content = content.replace(
                'ResponseUtils = None',
                'ResponseUtils = None\n\ntry:\n    from .validation_utils import ValidationUtils\n    _validation_utils_available = True\nexcept ImportError:\n    _validation_utils_available = False\n    ValidationUtils = None'
            )
            print("  ✅ Adicionado import correto do ValidationUtils")
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  💾 Arquivo salvo: {file_path}")
        
    except Exception as e:
        print(f"❌ Erro ao processar {file_path}: {e}")

def fix_utils_init():
    """Corrige o __init__.py do utils"""
    
    print("🔧 Corrigindo utils/__init__.py...")
    
    file_path = 'utils/__init__.py'
    
    if not os.path.exists(file_path):
        print(f"❌ Arquivo não encontrado: {file_path}")
        return
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verificar se ValidationUtils já está no __all__
        if 'ValidationUtils' not in content:
            # Adicionar ValidationUtils ao __all__
            content = content.replace(
                "'ResponseUtils',",
                "'ResponseUtils', 'ValidationUtils', 'get_validation_utils',"
            )
            print("  ✅ Adicionado ValidationUtils ao __all__")
        
        # Verificar se o import está correto
        if 'from .validation_utils import ValidationUtils' not in content:
            # Adicionar import se necessário
            content = content.replace(
                "except ImportError as e:\n    logger.warning(f\"⚠️ ResponseUtils não disponível: {e}\")\n    _response_utils_available = False",
                "except ImportError as e:\n    logger.warning(f\"⚠️ ResponseUtils não disponível: {e}\")\n    _response_utils_available = False\n\ntry:\n    from .validation_utils import ValidationUtils, get_validation_utils\n    _validation_utils_available = True\nexcept ImportError as e:\n    logger.warning(f\"⚠️ ValidationUtils não disponível: {e}\")\n    _validation_utils_available = False"
            )
            print("  ✅ Adicionado import do ValidationUtils")
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  💾 Arquivo salvo: {file_path}")
        
    except Exception as e:
        print(f"❌ Erro ao processar {file_path}: {e}")

def main():
    """Função principal"""
    print("🚀 Iniciando correção automática de imports...")
    
    # Corrigir ValidationUtils
    fix_validation_utils_imports()
    
    # Corrigir utils_manager
    fix_utils_manager_imports()
    
    # Corrigir utils/__init__.py
    fix_utils_init()
    
    print("✅ Correção automática concluída!")
    print("🧪 Execute 'python check_imports.py' para verificar se os problemas foram resolvidos")

if __name__ == "__main__":
    main() 