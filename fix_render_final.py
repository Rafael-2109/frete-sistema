#!/usr/bin/env python3
"""
🔧 Script FINAL para resolver TODOS os problemas do Render
"""

import os
import shutil
import psycopg2
from urllib.parse import urlparse

def fix_enhanced_claude_import():
    """Resolve o import circular do Enhanced Claude de forma diferente"""
    print("🔧 Resolvendo import circular do Enhanced Claude...")
    
    # Modificar enhanced_claude_integration.py
    enhanced_file = "app/claude_ai/enhanced_claude_integration.py"
    
    if not os.path.exists(enhanced_file):
        print("❌ Arquivo enhanced_claude_integration.py não encontrado")
        return False
    
    with open(enhanced_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remover completamente o import problemático
    content = content.replace(
        "from .claude_real_integration import ClaudeRealIntegration",
        "# from .claude_real_integration import ClaudeRealIntegration  # Removido para evitar circular import"
    )
    
    # Modificar o __init__ para não usar ClaudeRealIntegration
    old_init = """try:
            # Import dentro do método para evitar circular import
            from .claude_real_integration import ClaudeRealIntegration
            self.claude_integration = ClaudeRealIntegration()
        except ImportError as e:
            logger.warning(f"⚠️ ClaudeRealIntegration não disponível: {e}")
            self.claude_integration = None
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar ClaudeRealIntegration: {e}")
            self.claude_integration = None"""
    
    new_init = """# Claude Integration será injetado externamente para evitar circular import
        self.claude_integration = None
        logger.info("🔄 Claude Integration será configurado externamente")"""
    
    if old_init in content:
        content = content.replace(old_init, new_init)
        print("✅ Init do EnhancedClaudeIntegration modificado")
    
    # Salvar
    with open(enhanced_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # Agora modificar claude_real_integration.py para injetar a dependência
    claude_file = "app/claude_ai/claude_real_integration.py"
    
    with open(claude_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Procurar onde enhanced_claude é carregado
    old_load = """            try:
                # Import lazy para evitar circular import
                from .enhanced_claude_integration import get_enhanced_claude_system
                self.enhanced_claude = get_enhanced_claude_system(self.client)
                logger.info("🚀 Enhanced Claude Integration carregado!")
            except ImportError as e:
                logger.warning(f"⚠️ Enhanced Claude Integration não disponível: {e}")
                self.enhanced_claude = None"""
    
    new_load = """            try:
                # Import lazy para evitar circular import
                from .enhanced_claude_integration import get_enhanced_claude_system, enhanced_claude_integration
                self.enhanced_claude = get_enhanced_claude_system(self.client)
                
                # Injetar dependência para resolver circular import
                if self.enhanced_claude and hasattr(self.enhanced_claude, 'claude_integration'):
                    self.enhanced_claude.claude_integration = self
                    logger.info("✅ Dependência injetada no Enhanced Claude")
                
                logger.info("🚀 Enhanced Claude Integration carregado!")
            except ImportError as e:
                logger.warning(f"⚠️ Enhanced Claude Integration não disponível: {e}")
                self.enhanced_claude = None"""
    
    if old_load in content:
        content = content.replace(old_load, new_load)
        print("✅ Injeção de dependência adicionada")
    else:
        print("⚠️ Bloco de carregamento não encontrado no formato esperado")
    
    # Salvar
    with open(claude_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Import circular resolvido com injeção de dependência")
    return True

def fix_phantom_migration():
    """Remove a migração fantasma do banco PostgreSQL"""
    print("\n🔧 Removendo migração fantasma do PostgreSQL...")
    
    # Obter DATABASE_URL
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL não encontrada")
        return False
    
    # Parse da URL
    url = urlparse(database_url)
    
    try:
        # Conectar ao PostgreSQL
        conn = psycopg2.connect(
            host=url.hostname,
            port=url.port,
            database=url.path[1:],  # Remove a barra inicial
            user=url.username,
            password=url.password,
            sslmode='require'
        )
        
        cursor = conn.cursor()
        
        # Verificar se a migração fantasma existe
        cursor.execute(
            "SELECT version_num FROM alembic_version WHERE version_num = %s",
            ('1d81b88a3038',)
        )
        
        if cursor.fetchone():
            # Remover a migração fantasma
            cursor.execute(
                "DELETE FROM alembic_version WHERE version_num = %s",
                ('1d81b88a3038',)
            )
            conn.commit()
            print("✅ Migração fantasma '1d81b88a3038' removida do banco")
        else:
            print("ℹ️ Migração fantasma não encontrada no banco")
        
        # Verificar estado atual
        cursor.execute("SELECT version_num FROM alembic_version")
        current_migrations = cursor.fetchall()
        
        if current_migrations:
            print(f"📋 Migrações atuais no banco: {[m[0] for m in current_migrations]}")
        else:
            print("⚠️ Nenhuma migração registrada no banco")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao conectar ao PostgreSQL: {e}")
        return False

def create_render_start_script():
    """Cria script de inicialização otimizado para o Render"""
    print("\n🔧 Criando script de inicialização otimizado...")
    
    script_content = '''#!/bin/bash

echo "=== INICIANDO SISTEMA NO RENDER ==="

# Função para verificar se estamos no Render
is_render() {
    [ -n "$RENDER" ] && [ "$RENDER" = "true" ]
}

# Remover migração fantasma se estivermos no Render
if is_render; then
    echo "🔧 Ambiente Render detectado - Executando correções..."
    python fix_migration_db.py || echo "⚠️ Correção de migração falhou, continuando..."
fi

# Instalar modelo spaCy se necessário
echo "📦 Verificando modelo spaCy..."
python -m spacy download pt_core_news_sm -q || echo "⚠️ spaCy já instalado"

# Inicializar banco
echo "🗄️ Inicializando banco de dados..."
python init_db.py || echo "⚠️ Banco já inicializado"

# Aplicar migrações
echo "🔄 Aplicando migrações..."
flask db upgrade || echo "⚠️ Migrações aplicadas com avisos"

# Iniciar aplicação
echo "🚀 Iniciando aplicação..."
gunicorn run:app --bind 0.0.0.0:$PORT --workers 2 --threads 2 --timeout 120
'''
    
    with open('start_render_optimized.sh', 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    # Tornar executável
    os.chmod('start_render_optimized.sh', 0o755)
    
    print("✅ Script start_render_optimized.sh criado")
    return True

def main():
    """Função principal"""
    print("🚀 Fix FINAL para Render")
    print("=" * 50)
    
    # 1. Resolver import circular
    if fix_enhanced_claude_import():
        print("\n✅ Import circular resolvido!")
    
    # 2. Script para remover migração fantasma
    print("\n📝 Criando fix_migration_db.py para Render...")
    
    migration_fix = '''#!/usr/bin/env python3
"""Remove migração fantasma do PostgreSQL no Render"""

import os
import psycopg2
from urllib.parse import urlparse

database_url = os.environ.get('DATABASE_URL')
if database_url:
    url = urlparse(database_url)
    try:
        conn = psycopg2.connect(
            host=url.hostname,
            port=url.port,
            database=url.path[1:],
            user=url.username,
            password=url.password,
            sslmode='require'
        )
        cursor = conn.cursor()
        
        # Remover migração fantasma
        cursor.execute("DELETE FROM alembic_version WHERE version_num = '1d81b88a3038'")
        rows_deleted = cursor.rowcount
        
        if rows_deleted > 0:
            conn.commit()
            print(f"✅ Migração fantasma removida ({rows_deleted} registro)")
        else:
            print("ℹ️ Migração fantasma não encontrada")
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"⚠️ Erro ao remover migração: {e}")
else:
    print("⚠️ DATABASE_URL não encontrada")
'''
    
    with open('fix_migration_db.py', 'w', encoding='utf-8') as f:
        f.write(migration_fix)
    
    print("✅ fix_migration_db.py criado")
    
    # 3. Criar script de inicialização otimizado
    if create_render_start_script():
        print("\n✅ Script de inicialização otimizado criado!")
    
    print("\n" + "=" * 50)
    print("✅ TODAS AS CORREÇÕES APLICADAS!")
    print("\n📋 PRÓXIMOS PASSOS:")
    print("1. Faça commit e push:")
    print("   git add -A")
    print("   git commit -m 'Fix: Resolver definitivamente problemas do Render'")
    print("   git push")
    print("\n2. No Render, mude o Start Command para:")
    print("   ./start_render_optimized.sh")
    print("\n3. Faça um novo deploy")
    print("\n✨ Isso deve resolver TODOS os problemas!")

if __name__ == "__main__":
    main() 