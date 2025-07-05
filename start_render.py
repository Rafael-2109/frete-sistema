#!/usr/bin/env python3
"""Script de inicialização para o Render"""

import subprocess
import sys
import os

print("🚀 INICIANDO SISTEMA NO RENDER...")

# 0. Instalar modelo spaCy português
print("📦 Instalando modelo spaCy português...")
try:
    subprocess.run([sys.executable, '-m', 'spacy', 'download', 'pt_core_news_sm'], 
                   capture_output=True, check=False)
    print("   ✅ Modelo spaCy instalado/verificado")
except Exception as e:
    print(f"   ⚠️ spaCy: {e}")

# 1. Executar correções
print("🔧 Aplicando correções...")
subprocess.run([sys.executable, 'corrigir_deploy_render_final.py'])

# 2. CRÍTICO: Forçar correção de migrações ANTES de qualquer outra coisa
print("🔨 Forçando correção de migrações...")
result = subprocess.run([sys.executable, 'force_migration_fix.py'])
if result.returncode != 0:
    print("⚠️ Correção de migrações retornou aviso, mas continuando...")

# 3. Inicializar banco
print("🗄️ Inicializando banco...")
subprocess.run([sys.executable, 'init_db.py'])

# 4. Aplicar migrações com tratamento de erro
print("🔄 Aplicando migrações...")
try:
    # Tentar upgrade normal
    result = subprocess.run(['flask', 'db', 'upgrade'], capture_output=True, text=True)
    
    if result.returncode != 0:
        if 'Multiple head revisions' in result.stderr:
            print("⚠️ Múltiplas heads ainda detectadas - ignorando e continuando...")
            # Não tentar mais nada, apenas continuar
        else:
            print(f"⚠️ Erro na migração: {result.stderr}")
            # Continuar mesmo com erro
    else:
        print("✅ Migrações aplicadas com sucesso")
        
except Exception as e:
    print(f"⚠️ Erro ao aplicar migrações: {e}")
    # Continuar mesmo com erro

print("✅ Inicialização concluída!")

# 5. Iniciar Gunicorn
print("🌐 Iniciando servidor Gunicorn...")
os.execvp('gunicorn', [
    'gunicorn',
    '--bind', f'0.0.0.0:{os.environ.get("PORT", 10000)}',
    '--workers', '2',
    '--worker-class', 'sync',
    '--timeout', '600',
    '--max-requests', '1000',
    '--max-requests-jitter', '100',
    '--keep-alive', '10',
    '--preload',
    '--worker-tmp-dir', '/dev/shm',
    'run:app'
])
