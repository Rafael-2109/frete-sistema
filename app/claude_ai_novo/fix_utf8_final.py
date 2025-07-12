#!/usr/bin/env python3
"""
🔧 FIX UTF-8 FINAL - Correção específica do erro UTF-8
=====================================================

Script para identificar e corrigir o erro específico:
'utf-8' codec can't decode byte 0xe3 in position 82: invalid continuation byte
"""

import os
import sys
import logging
from pathlib import Path

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def find_utf8_problem():
    """Encontra o arquivo/variável com problema UTF-8"""
    
    print("🔍 INVESTIGANDO ERRO UTF-8")
    print("=" * 50)
    
    # Verificar DATABASE_URL especificamente
    database_url = os.environ.get('DATABASE_URL', '')
    if database_url:
        print(f"📊 DATABASE_URL encontrada: {len(database_url)} caracteres")
        
        # Verificar cada caractere
        for i, char in enumerate(database_url):
            if i == 82:  # Posição 82 mencionada no erro
                print(f"🎯 Posição 82: '{char}' (código: {ord(char)})")
                try:
                    char.encode('utf-8')
                    print(f"✅ Caractere na posição 82 é válido UTF-8")
                except UnicodeEncodeError as e:
                    print(f"❌ PROBLEMA ENCONTRADO na posição 82: {e}")
                    print(f"   Caractere: '{char}' (código: {ord(char)})")
                    
            # Verificar se há caracteres problemáticos
            try:
                char.encode('utf-8')
            except UnicodeEncodeError as e:
                print(f"❌ Caractere problemático na posição {i}: '{char}' (código: {ord(char)})")
    
    # Verificar outras variáveis de ambiente
    problematic_vars = []
    for key, value in os.environ.items():
        if isinstance(value, str):
            try:
                value.encode('utf-8')
            except UnicodeEncodeError as e:
                problematic_vars.append((key, str(e)))
    
    if problematic_vars:
        print(f"\n❌ Variáveis de ambiente com problemas UTF-8:")
        for var, error in problematic_vars:
            print(f"   {var}: {error}")
    else:
        print(f"\n✅ Todas as variáveis de ambiente são válidas UTF-8")

def test_flask_import():
    """Testa o import do Flask app especificamente"""
    
    print("\n🧪 TESTANDO IMPORT FLASK APP")
    print("=" * 50)
    
    try:
        # Adicionar path do projeto
        project_root = Path(__file__).parent.parent.parent
        sys.path.insert(0, str(project_root))
        
        print("🔄 Tentando importar app...")
        
        # Tentar diferentes formas de import
        import_attempts = [
            "from app import create_app",
            "from app import app",
            "import app",
            "from app import db",
        ]
        
        for attempt in import_attempts:
            try:
                print(f"   Testando: {attempt}")
                exec(attempt)
                print(f"   ✅ {attempt} - SUCESSO")
            except UnicodeDecodeError as e:
                print(f"   ❌ {attempt} - ERRO UTF-8: {e}")
                if hasattr(e, 'start') and hasattr(e, 'end'):
                    print(f"      Posição do erro: {e.start} - {e.end}")
            except Exception as e:
                print(f"   ⚠️ {attempt} - OUTRO ERRO: {type(e).__name__}: {e}")
        
    except Exception as e:
        print(f"❌ ERRO GERAL: {e}")

def fix_utf8_issues():
    """Tenta corrigir problemas UTF-8 identificados"""
    
    print("\n🔧 CORRIGINDO PROBLEMAS UTF-8")
    print("=" * 50)
    
    # Backup da DATABASE_URL original
    original_db_url = os.environ.get('DATABASE_URL')
    
    if original_db_url:
        print(f"🔄 Processando DATABASE_URL...")
        
        # Estratégias de correção
        try:
            # Estratégia 1: Remover caracteres não-ASCII
            clean_url = ''.join(char for char in original_db_url if ord(char) < 128)
            os.environ['DATABASE_URL'] = clean_url
            print(f"✅ Estratégia 1: Removidos caracteres não-ASCII")
            
            # Testar se funciona
            test_flask_import()
            
        except Exception as e:
            print(f"❌ Estratégia 1 falhou: {e}")
            
            # Estratégia 2: Recodificação
            try:
                if original_db_url:
                    # Tentar diferentes codificações
                    encodings = ['latin-1', 'cp1252', 'iso-8859-1']
                    for encoding in encodings:
                        try:
                            decoded = original_db_url.encode(encoding).decode('utf-8')
                            os.environ['DATABASE_URL'] = decoded
                            print(f"✅ Estratégia 2: Recodificação {encoding} → utf-8")
                            test_flask_import()
                            break
                        except:
                            continue
                            
            except Exception as e2:
                print(f"❌ Estratégia 2 falhou: {e2}")
                
                # Restaurar URL original
                if original_db_url:
                    os.environ['DATABASE_URL'] = original_db_url

def check_file_encodings():
    """Verifica encoding de arquivos Python relevantes"""
    
    print("\n📁 VERIFICANDO ENCODING DE ARQUIVOS")
    print("=" * 50)
    
    # Arquivos para verificar
    files_to_check = [
        'app/__init__.py',
        'app/models.py',
        'run.py',
        'config.py',
        'app/claude_transition.py',
        'app/utils/redis_cache.py',
    ]
    
    project_root = Path(__file__).parent.parent.parent
    
    for file_path in files_to_check:
        full_path = project_root / file_path
        if full_path.exists():
            try:
                # Tentar ler com UTF-8
                content = full_path.read_text(encoding='utf-8')
                print(f"✅ {file_path} - UTF-8 OK ({len(content)} chars)")
            except UnicodeDecodeError as e:
                print(f"❌ {file_path} - ERRO UTF-8: {e}")
                
                # Tentar outras codificações
                for encoding in ['latin-1', 'cp1252', 'iso-8859-1']:
                    try:
                        content = full_path.read_text(encoding=encoding)
                        print(f"⚠️ {file_path} - Codificação: {encoding}")
                        
                        # Tentar converter para UTF-8
                        full_path.write_text(content, encoding='utf-8')
                        print(f"🔧 {file_path} - Convertido para UTF-8")
                        break
                    except:
                        continue

if __name__ == "__main__":
    print("🔧 FIX UTF-8 FINAL - INICIANDO")
    print("=" * 60)
    
    # Executar diagnósticos e correções
    find_utf8_problem()
    check_file_encodings()
    test_flask_import()
    fix_utf8_issues()
    
    print("\n📊 DIAGNÓSTICO COMPLETO")
    print("=" * 60)
    print("✅ Verificações concluídas")
    print("💡 Execute o validador novamente para verificar se o problema foi resolvido") 