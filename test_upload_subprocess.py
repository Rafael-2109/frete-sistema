#!/usr/bin/env python3
"""
Script de teste para verificar o erro no upload subprocess
"""

import subprocess
import sys
import json
import tempfile
import os

# Criar um arquivo de teste
test_file = os.path.join(tempfile.gettempdir(), "test_sendas.xlsx")
with open(test_file, 'w') as f:
    f.write("teste")

print(f"Testando upload com arquivo: {test_file}")
print("-" * 50)

# Caminho do script
script_path = "/home/rafaelnascimento/projetos/frete_sistema/app/portal/sendas/upload_planilha_subprocess.py"

# Executar o script
try:
    result = subprocess.run(
        [sys.executable, script_path, test_file],
        capture_output=True,
        text=True,
        timeout=300  # Aumentado para 5 minutos
    )
    
    print(f"Return code: {result.returncode}")
    print(f"STDOUT:\n{result.stdout}")
    print(f"STDERR:\n{result.stderr}")
    
    # Tentar fazer parse do JSON
    if result.stdout:
        lines = result.stdout.strip().split('\n')
        for line in reversed(lines):
            if line.strip().startswith('{') and line.strip().endswith('}'):
                try:
                    response = json.loads(line.strip())
                    print(f"\nJSON Response: {json.dumps(response, indent=2)}")
                except:
                    pass
                break
    
except subprocess.TimeoutExpired:
    print("ERRO: Timeout no teste")
except Exception as e:
    print(f"ERRO: {e}")
finally:
    # Limpar arquivo de teste
    if os.path.exists(test_file):
        os.remove(test_file)