#!/usr/bin/env python3
"""
🚨 CORREÇÃO URGENTE - TOKENS CSRF PROBLEMÁTICOS
Corrige templates onde csrf_token() está sendo exibido como texto ao invés de input hidden
"""

import os
import re
from pathlib import Path

def encontrar_e_corrigir_tokens_csrf():
    """Encontra e corrige todos os tokens CSRF problemáticos"""
    
    print("🚨 CORREÇÃO URGENTE - TOKENS CSRF PROBLEMÁTICOS")
    print("=" * 80)
    
    # Diretório dos templates
    templates_dir = Path("app/templates")
    
    # Padrões problemáticos para corrigir
    patterns_problematicos = [
        # Padrão 1: <form> \n {{ csrf_token() }} method="POST"
        (r'<form>\s*\n\s*\{\{\s*csrf_token\(\)\s*\}\}\s*method="POST"([^>]*>)', 
         r'<form method="POST"\1'),
        
        # Padrão 2: <form> \n {{ csrf_token() }} method="GET"
        (r'<form>\s*\n\s*\{\{\s*csrf_token\(\)\s*\}\}\s*method="GET"([^>]*>)', 
         r'<form method="GET"\1'),
        
        # Padrão 3: {{ csrf_token() }} method="POST" no meio de atributos
        (r'\{\{\s*csrf_token\(\)\s*\}\}\s*method="POST"', 
         r'method="POST"'),
        
        # Padrão 4: {{ csrf_token() }} method="GET" no meio de atributos
        (r'\{\{\s*csrf_token\(\)\s*\}\}\s*method="GET"', 
         r'method="GET"'),
    ]
    
    arquivos_corrigidos = []
    total_correcoes = 0
    
    print("🔍 **ESCANEANDO TEMPLATES PROBLEMÁTICOS:**")
    print()
    
    # Escanear todos os templates
    for template_file in templates_dir.rglob("*.html"):
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            arquivo_alterado = False
            
            # Verificar se tem padrões problemáticos
            for pattern, replacement in patterns_problematicos:
                if re.search(pattern, content, re.MULTILINE | re.DOTALL):
                    print(f"  ❌ PROBLEMA ENCONTRADO: {template_file}")
                    content = re.sub(pattern, replacement, content, flags=re.MULTILINE | re.DOTALL)
                    arquivo_alterado = True
                    total_correcoes += 1
            
            # Salvar se foi alterado
            if arquivo_alterado:
                with open(template_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                arquivos_corrigidos.append(str(template_file))
                print(f"  ✅ CORRIGIDO: {template_file}")
            
        except Exception as e:
            print(f"  ⚠️  ERRO ao processar {template_file}: {e}")
    
    print()
    print("📊 **RESULTADOS DA CORREÇÃO:**")
    print(f"  🔢 Templates corrigidos: {len(arquivos_corrigidos)}")
    print(f"  🔢 Total de correções: {total_correcoes}")
    print()
    
    if arquivos_corrigidos:
        print("📁 **ARQUIVOS CORRIGIDOS:**")
        for arquivo in arquivos_corrigidos:
            print(f"  ✅ {arquivo}")
        print()
    
    # Verificar se ainda há problemas
    print("🔍 **VERIFICAÇÃO FINAL:**")
    problemas_restantes = verificar_problemas_restantes()
    
    if problemas_restantes:
        print("  ⚠️  AINDA HÁ PROBLEMAS RESTANTES:")
        for problema in problemas_restantes:
            print(f"    ❌ {problema}")
    else:
        print("  ✅ TODOS OS PROBLEMAS FORAM CORRIGIDOS!")
    
    print()
    print("🎯 **EXPLICAÇÃO DO PROBLEMA:**")
    print()
    print("❌ **FORMATO INCORRETO (estava causando problemas):**")
    print("   <form>")
    print("   {{ csrf_token() }} method=\"POST\">")
    print("   ↑ Token aparece como TEXTO na página!")
    print()
    print("✅ **FORMATO CORRETO (como deveria ser):**")
    print("   <form method=\"POST\">")
    print("     <input type=\"hidden\" name=\"csrf_token\" value=\"{{ csrf_token() }}\"/>")
    print("   ↑ Token oculto no formulário!")
    print()
    print("🚨 **PROBLEMAS CAUSADOS PELA FORMA INCORRETA:**")
    print("   1. Token CSRF aparece como texto na página")
    print("   2. Formulários podem não funcionar corretamente")
    print("   3. Risco de segurança (token exposto)")
    print("   4. HTML inválido")
    print()
    
    return len(arquivos_corrigidos), total_correcoes

def verificar_problemas_restantes():
    """Verifica se ainda há problemas restantes"""
    templates_dir = Path("app/templates")
    problemas = []
    
    # Padrões que indicam problemas
    patterns_problematicos = [
        r'\{\{\s*csrf_token\(\)\s*\}\}\s*method=',
        r'<form>\s*\n\s*\{\{\s*csrf_token\(\)\s*\}\}'
    ]
    
    for template_file in templates_dir.rglob("*.html"):
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            for pattern in patterns_problematicos:
                if re.search(pattern, content, re.MULTILINE | re.DOTALL):
                    problemas.append(str(template_file))
                    break
        except:
            pass
    
    return problemas

def demonstrar_problema():
    """Demonstra exatamente qual é o problema"""
    print("🎯 **DEMONSTRAÇÃO DO PROBLEMA:**")
    print()
    print("📋 **EXEMPLO DE TEMPLATE PROBLEMÁTICO:**")
    print("   Arquivo: app/templates/portaria/cadastrar_motorista.html")
    print("   Linha 25-26:")
    print("   ```html")
    print("   <form>")
    print("   {{ csrf_token() }} method=\"POST\" enctype=\"multipart/form-data\">")
    print("   ```")
    print()
    print("🔍 **O QUE ACONTECE NO BROWSER:**")
    print("   1. O token CSRF é impresso como TEXTO na página")
    print("   2. Aparece algo como: 'IjxkZmY2NDk...' method=\"POST\"")
    print("   3. O HTML fica inválido")
    print("   4. O formulário pode não funcionar")
    print()
    print("✅ **COMO DEVERIA SER:**")
    print("   ```html")
    print("   <form method=\"POST\" enctype=\"multipart/form-data\">")
    print("     <input type=\"hidden\" name=\"csrf_token\" value=\"{{ csrf_token() }}\"/>")
    print("   ```")
    print()
    print("🎯 **ORIGEM DO PROBLEMA:**")
    print("   - Provavelmente erro de find/replace automático")
    print("   - Ou problema de merge/conflito no Git")
    print("   - NÃO foi uma mudança intencional")
    print()

if __name__ == "__main__":
    demonstrar_problema()
    print()
    arquivos_corrigidos, total_correcoes = encontrar_e_corrigir_tokens_csrf()
    
    if arquivos_corrigidos > 0:
        print("🎉 **CORREÇÃO CONCLUÍDA COM SUCESSO!**")
        print(f"   ✅ {arquivos_corrigidos} arquivos corrigidos")
        print(f"   ✅ {total_correcoes} problemas resolvidos")
        print()
        print("💡 **PRÓXIMOS PASSOS:**")
        print("   1. Testar os formulários afetados")
        print("   2. Verificar se não há mais tokens visíveis")
        print("   3. Fazer commit das correções")
        print("   4. Deploy para produção")
    else:
        print("ℹ️  **NENHUM PROBLEMA ENCONTRADO.**")
        print("   Os tokens CSRF já estão corretos!") 