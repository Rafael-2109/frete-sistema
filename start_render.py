#!/usr/bin/env python3
"""Script de inicialização para o Render"""

import subprocess
import sys
import os

print("🚀 INICIANDO SISTEMA NO RENDER...")

# 1. Executar correções
print("🔧 Aplicando correções...")
subprocess.run([sys.executable, 'corrigir_deploy_render_final.py'])

# 2. Inicializar banco
print("🗄️ Inicializando banco...")
subprocess.run([sys.executable, 'init_db.py'])

# 3. Aplicar migrações com tratamento de erro
print("🔄 Aplicando migrações...")
try:
    # Tentar upgrade normal
    result = subprocess.run(['flask', 'db', 'upgrade'], capture_output=True, text=True)
    
    if result.returncode != 0:
        if 'Multiple head revisions' in result.stderr:
            print("⚠️ Múltiplas heads detectadas - aplicando correção...")
            
            # Aplicar stamp na migração de merge
            subprocess.run(['flask', 'db', 'stamp', 'merge_heads_20250705_093743'])
            
            # Tentar upgrade novamente
            subprocess.run(['flask', 'db', 'upgrade'])
        else:
            print(f"❌ Erro na migração: {result.stderr}")
            # Continuar mesmo com erro
    else:
        print("✅ Migrações aplicadas com sucesso")
        
except Exception as e:
    print(f"⚠️ Erro ao aplicar migrações: {e}")
    # Continuar mesmo com erro

print("✅ Inicialização concluída!")

# 4. Iniciar Gunicorn
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
