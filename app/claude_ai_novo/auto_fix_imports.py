#!/usr/bin/env python3
"""
Script para corrigir automaticamente os imports críticos do sistema
"""

import os
import re
import ast
from pathlib import Path
from typing import List, Tuple, Dict

def fix_flask_imports(content: str) -> str:
    """Corrige imports do Flask para usar fallback"""
    # Padrão para from flask import X, Y, Z
    pattern = r'from flask import ([^\n]+)'
    
    def replace_flask(match):
        imports = match.group(1).strip()
        return f"""try:
    from flask import {imports}
    FLASK_AVAILABLE = True
except ImportError:
    {imports} = None
    FLASK_AVAILABLE = False
except ImportError:
    from app.claude_ai_novo.system_dependencies import get_flask
    flask_mock = get_flask()
    {', '.join([f"{i.strip()} = getattr(flask_mock, '{i.strip()}', None)" for i in imports.split(',')])}"""
    
    return re.sub(pattern, replace_flask, content)

def fix_sqlalchemy_imports(content: str) -> str:
    """Corrige imports do SQLAlchemy para usar fallback"""
    patterns = [
        (r'from sqlalchemy import ([^\n]+)', 'sqlalchemy'),
        (r'from sqlalchemy\.orm import ([^\n]+)', 'sqlalchemy.orm'),
        (r'from sqlalchemy\.sql import ([^\n]+)', 'sqlalchemy.sql'),
    ]
    
    for pattern, module in patterns:
        def replace_sqlalchemy(match):
            imports = match.group(1).strip()
            module_path = module.replace('.', '_')
            return f"""try:
    from {module} import {imports}
except ImportError:
    from app.claude_ai_novo.system_dependencies import get_sqlalchemy
    sa_mock = get_sqlalchemy()
    {', '.join([f"{i.strip()} = getattr(sa_mock, '{i.strip()}', None)" for i in imports.split(',')])}"""
        
        content = re.sub(pattern, replace_sqlalchemy, content)
    
    return content

def fix_model_imports(content: str) -> str:
    """Corrige imports de modelos do sistema antigo"""
    # Padrão para from app.models import X, Y, Z
    pattern = r'from app\.models import ([^\n]+)'
    
    def replace_models(match):
        imports = match.group(1).strip()
        model_names = [i.strip() for i in imports.split(',')]
        return f"""try:
    from app.models import {imports}
except ImportError:
    from app.claude_ai_novo.system_dependencies import get_system_models
    _models = get_system_models()
    {'; '.join([f"{name} = _models.get('{name}', None)" for name in model_names])}"""
    
    content = re.sub(pattern, replace_models, content)
    
    # Outros modelos específicos
    other_patterns = [
        (r'from app\.auth\.models import ([^\n]+)', 'auth'),
        (r'from app\.cadastros_agendamento\.models import ([^\n]+)', 'cadastros'),
        (r'from app\.cotacao\.models import ([^\n]+)', 'cotacao'),
    ]
    
    for pattern, module_type in other_patterns:
        content = re.sub(pattern, 
            lambda m: f"""try:
    {m.group(0)}
except ImportError:
    from app.claude_ai_novo.system_dependencies import get_model_mock
    {'; '.join([f"{i.strip()} = get_model_mock('{i.strip()}')" for i in m.group(1).split(',')])}""",
            content)
    
    return content

def fix_redis_imports(content: str) -> str:
    """Corrige imports do Redis"""
    pattern = r'import redis'
    replacement = """try:
    import redis
except ImportError:
    from app.claude_ai_novo.system_dependencies import get_redis
    redis = get_redis()"""
    
    return re.sub(pattern, replacement, content)

def fix_pandas_imports(content: str) -> str:
    """Corrige imports do Pandas"""
    patterns = [
        (r'import pandas as pd', 'pd'),
        (r'import pandas', 'pandas'),
    ]
    
    for pattern, alias in patterns:
        replacement = f"""try:
    {pattern}
except ImportError:
    from app.claude_ai_novo.system_dependencies import get_pandas
    {alias} = get_pandas()"""
        content = re.sub(pattern, replacement, content)
    
    return content

def fix_openpyxl_imports(content: str) -> str:
    """Corrige imports do OpenPyXL"""
    pattern = r'from openpyxl import ([^\n]+)'
    
    def replace_openpyxl(match):
        imports = match.group(1).strip()
        return f"""try:
    from openpyxl import {imports}
    OPENPYXL_AVAILABLE = True
except ImportError:
    from unittest.mock import Mock
    {imports} = Mock()
    OPENPYXL_AVAILABLE = False
except ImportError:
    from app.claude_ai_novo.system_dependencies import get_openpyxl
    _openpyxl = get_openpyxl()
    {', '.join([f"{i.strip()} = getattr(_openpyxl, '{i.strip()}', None)" for i in imports.split(',')])}"""
    
    return re.sub(pattern, replace_openpyxl, content)

def fix_anthropic_imports(content: str) -> str:
    """Corrige imports do Anthropic"""
    patterns = [
        r'import anthropic',
        r'from anthropic import ([^\n]+)',
    ]
    
    # Import direto
    content = re.sub(patterns[0], """try:
    import anthropic
except ImportError:
    from app.claude_ai_novo.system_dependencies import get_anthropic
    anthropic = get_anthropic()""", content)
    
    # From import
    def replace_anthropic(match):
        imports = match.group(1).strip()
        return f"""try:
    from anthropic import {imports}
except ImportError:
    from app.claude_ai_novo.system_dependencies import get_anthropic
    _anthropic = get_anthropic()
    {', '.join([f"{i.strip()} = getattr(_anthropic, '{i.strip()}', None)" for i in imports.split(',')])}"""
    
    content = re.sub(patterns[1], replace_anthropic, content)
    
    return content

def fix_ufs_import(content: str) -> str:
    """Corrige import de UF_LIST"""
    pattern = r'from app\.utils\.ufs import ([^\n]+)'
    
    def replace_ufs(match):
        imports = match.group(1).strip()
        if 'UF_LIST' in imports:
            return """try:
    from app.utils.ufs import UF_LIST
except ImportError:
    from app.claude_ai_novo.system_dependencies import UF_LIST"""
        return match.group(0)
    
    return re.sub(pattern, replace_ufs, content)

def fix_db_imports(content: str) -> str:
    """Corrige imports de db e current_user"""
    # db
    content = re.sub(
        r'from app import db',
        """try:
    from app import db
except ImportError:
    from app.claude_ai_novo.system_dependencies import get_db_mock
    db = get_db_mock()""",
        content
    )
    
    # current_user
    content = re.sub(
        r'from flask_login import current_user',
        """try:
    from flask_login import current_user
    FLASK_LOGIN_AVAILABLE = True
except ImportError:
    from unittest.mock import Mock
    current_user = Mock()
    FLASK_LOGIN_AVAILABLE = False
except ImportError:
    from app.claude_ai_novo.system_dependencies import get_current_user_mock
    current_user = get_current_user_mock()""",
        content
    )
    
    return content

def process_file(filepath: str) -> bool:
    """Processa um arquivo e aplica todas as correções"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        
        # Aplicar todas as correções
        content = fix_flask_imports(content)
        content = fix_sqlalchemy_imports(content)
        content = fix_model_imports(content)
        content = fix_redis_imports(content)
        content = fix_pandas_imports(content)
        content = fix_openpyxl_imports(content)
        content = fix_anthropic_imports(content)
        content = fix_ufs_import(content)
        content = fix_db_imports(content)
        
        # Adicionar import do system_dependencies se necessário
        if 'from app.claude_ai_novo.system_dependencies import' in content and 'import logging' in content:
            # Já tem o import, não precisa adicionar
            pass
        elif 'from app.claude_ai_novo.system_dependencies import' in content:
            # Adicionar logging no início
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if line.strip() and not line.startswith('#'):
                    lines.insert(i, 'import logging\n')
                    break
            content = '\n'.join(lines)
        
        if content != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        return False
        
    except Exception as e:
        print(f"Erro ao processar {filepath}: {e}")
        return False

def main():
    """Função principal"""
    base_path = Path("/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo")
    
    # Lista de arquivos críticos para corrigir primeiro
    critical_files = [
        "utils/flask_fallback.py",
        "utils/flask_context_wrapper.py",
        "utils/base_classes.py",
        "utils/data_manager.py",
        "loaders/context_loader.py",
        "loaders/database_loader.py",
        "providers/data_provider.py",
        "commands/base_command.py",
        "processors/context_processor.py",
        "processors/response_processor.py",
    ]
    
    print("🔧 Corrigindo imports críticos...")
    
    fixed_count = 0
    
    # Corrigir arquivos críticos primeiro
    for file_path in critical_files:
        full_path = base_path / file_path
        if full_path.exists():
            if process_file(str(full_path)):
                print(f"✅ {file_path}")
                fixed_count += 1
            else:
                print(f"⏭️  {file_path} (sem mudanças)")
    
    # Depois corrigir todos os outros arquivos Python
    print("\n🔧 Corrigindo outros arquivos...")
    
    for py_file in base_path.rglob("*.py"):
        # Pular arquivos já processados
        relative_path = py_file.relative_to(base_path)
        if str(relative_path) in critical_files:
            continue
        
        # Pular arquivos de teste e scripts
        if any(part in str(relative_path) for part in ['test_', 'tests/', '__pycache__', 'verificar_', 'mapear_', 'testar_']):
            continue
        
        if process_file(str(py_file)):
            print(f"✅ {relative_path}")
            fixed_count += 1
    
    print(f"\n✅ Total de arquivos corrigidos: {fixed_count}")

if __name__ == "__main__":
    main()