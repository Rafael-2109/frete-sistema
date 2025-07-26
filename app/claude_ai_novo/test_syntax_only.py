#!/usr/bin/env python3
"""
Teste apenas de sintaxe - verifica se arquivos podem ser compilados
"""

import ast
import os
from datetime import datetime

print("🧪 TESTE DE SINTAXE - SISTEMA CLAUDE_AI_NOVO")
print("="*60)
print(f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
print("="*60)

# Lista de arquivos críticos para testar
critical_files = [
    "app/claude_ai_novo/memorizers/system_memory.py",
    "app/claude_ai_novo/utils/flask_fallback.py",
    "app/claude_ai_novo/utils/base_classes.py",
    "app/claude_ai_novo/memorizers/knowledge_memory.py",
    "app/claude_ai_novo/providers/data_provider.py",
    "app/claude_ai_novo/orchestrators/orchestrator_manager.py",
    "app/claude_ai_novo/orchestrators/session_orchestrator.py",
    "app/claude_ai_novo/processors/response_processor.py"
]

success_count = 0
error_count = 0
errors_detail = []

print("\n📦 Verificando sintaxe dos arquivos...\n")

for file_path in critical_files:
    if os.path.exists(file_path):
        try:
            print(f"✓ Verificando {os.path.basename(file_path)}...", end=" ")
            
            # Ler arquivo
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Tentar compilar (verifica sintaxe)
            compile(content, file_path, 'exec')
            
            # Tentar fazer parse AST (verificação mais profunda)
            ast.parse(content)
            
            print("✅ SINTAXE OK!")
            success_count += 1
            
        except SyntaxError as e:
            print(f"❌ ERRO DE SINTAXE!")
            error_count += 1
            errors_detail.append({
                'file': file_path,
                'line': e.lineno,
                'msg': e.msg,
                'text': e.text
            })
            print(f"   → Linha {e.lineno}: {e.msg}")
            if e.text:
                print(f"   → Código: {e.text.strip()}")
                
        except Exception as e:
            print(f"❌ ERRO: {e}")
            error_count += 1
            errors_detail.append({
                'file': file_path,
                'error': str(e)
            })
    else:
        print(f"⚠️ Arquivo não encontrado: {file_path}")

# Resumo
print("\n" + "="*60)
print(f"📊 RESUMO DA VERIFICAÇÃO DE SINTAXE:")
print(f"  ✅ Arquivos OK: {success_count}")
print(f"  ❌ Arquivos com erro: {error_count}")
print("="*60)

if errors_detail:
    print("\n❌ DETALHES DOS ERROS DE SINTAXE:\n")
    for err in errors_detail:
        print(f"📁 {err['file']}")
        if 'line' in err:
            print(f"   Linha {err['line']}: {err['msg']}")
            if err.get('text'):
                print(f"   Código: {err['text'].strip()}")
        else:
            print(f"   Erro: {err.get('error', 'N/A')}")
        print()

if error_count == 0:
    print("\n🎉 TODOS OS ARQUIVOS PASSARAM NA VERIFICAÇÃO DE SINTAXE!")
    print("✅ Os erros de sintaxe foram corrigidos com sucesso!")
    print("\n💡 Agora o sistema pode ser iniciado no Flask sem erros de sintaxe.")
else:
    print(f"\n⚠️ Ainda há {error_count} arquivos com erros de sintaxe.")
    print("❌ Estes erros precisam ser corrigidos antes de iniciar o sistema.")