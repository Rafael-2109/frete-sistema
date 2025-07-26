#!/usr/bin/env python3
"""
Teste de sintaxe completo para todos os arquivos Python do claude_ai_novo
"""

import ast
import os
from datetime import datetime
from pathlib import Path

print("🧪 TESTE DE SINTAXE COMPLETO - SISTEMA CLAUDE_AI_NOVO")
print("="*60)
print(f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
print("="*60)

# Diretório base
base_dir = Path("app/claude_ai_novo")

# Estatísticas
total_files = 0
success_count = 0
error_count = 0
errors_detail = []

print("\n📦 Verificando TODOS os arquivos Python...\n")

# Percorrer todos os arquivos .py
for py_file in base_dir.rglob("*.py"):
    # Ignorar __pycache__
    if "__pycache__" in str(py_file):
        continue
        
    total_files += 1
    
    try:
        print(f"✓ {py_file.relative_to(base_dir)}...", end=" ")
        
        # Ler arquivo
        with open(py_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Tentar compilar (verifica sintaxe)
        compile(content, str(py_file), 'exec')
        
        # Tentar fazer parse AST
        ast.parse(content)
        
        print("✅")
        success_count += 1
        
    except SyntaxError as e:
        print(f"❌ ERRO!")
        error_count += 1
        errors_detail.append({
            'file': str(py_file),
            'relative': str(py_file.relative_to(base_dir)),
            'line': e.lineno,
            'msg': e.msg,
            'text': e.text.strip() if e.text else None
        })
        
    except Exception as e:
        print(f"❌ {type(e).__name__}")
        error_count += 1
        errors_detail.append({
            'file': str(py_file),
            'relative': str(py_file.relative_to(base_dir)),
            'error': str(e)
        })

# Resumo
print("\n" + "="*60)
print(f"📊 RESUMO DA VERIFICAÇÃO COMPLETA:")
print(f"  📁 Total de arquivos: {total_files}")
print(f"  ✅ Arquivos OK: {success_count}")
print(f"  ❌ Arquivos com erro: {error_count}")
print(f"  📈 Taxa de sucesso: {(success_count/total_files*100):.1f}%")
print("="*60)

if errors_detail:
    print("\n❌ ARQUIVOS COM ERROS DE SINTAXE:\n")
    for err in errors_detail:
        print(f"📁 {err['relative']}")
        if 'line' in err:
            print(f"   Linha {err['line']}: {err['msg']}")
            if err.get('text'):
                print(f"   → {err['text']}")
        else:
            print(f"   Erro: {err.get('error', 'N/A')}")
        print()

if error_count == 0:
    print("\n🎉 PARABÉNS! TODOS OS ARQUIVOS PASSARAM NA VERIFICAÇÃO!")
    print("✅ O sistema está livre de erros de sintaxe!")
    print("\n💡 Próximo passo: Reiniciar o servidor Flask.")
else:
    print(f"\n⚠️ Ainda há {error_count} arquivos com erros.")
    print("📝 Corrija os erros listados acima antes de continuar.")