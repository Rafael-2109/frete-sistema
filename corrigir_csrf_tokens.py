#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import glob

def corrigir_csrf_tokens():
    """
    Corrige todos os tokens CSRF mal formatados nos templates HTML.
    
    Converte de:
    <form>
    {{ csrf_token() }} method="POST">
    
    Para:
    <form method="POST">
        <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
    """
    
    # Procurar todos os arquivos HTML
    templates_dir = "app/templates"
    arquivos_html = []
    
    for root, dirs, files in os.walk(templates_dir):
        for file in files:
            if file.endswith('.html'):
                arquivos_html.append(os.path.join(root, file))
    
    arquivos_corrigidos = []
    total_correcoes = 0
    
    # Padrões para encontrar CSRF tokens mal formatados
    patterns = [
        # Padrão 1: <form {{ csrf_token() }} method="POST">
        r'<form\s*{{ csrf_token\(\) }}\s*(.*?)>',
        # Padrão 2: <form>\n{{ csrf_token() }} method="POST">
        r'<form>\s*\n\s*{{ csrf_token\(\) }}\s*(.*?)>',
        # Padrão 3: <form {{ csrf_token() }}\n method="POST">
        r'<form\s*{{ csrf_token\(\) }}\s*\n\s*(.*?)>'
    ]
    
    for arquivo in arquivos_html:
        try:
            # Tentar diferentes encodings
            encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            conteudo = None
            encoding_usado = None
            
            for encoding in encodings:
                try:
                    with open(arquivo, 'r', encoding=encoding) as f:
                        conteudo = f.read()
                    encoding_usado = encoding
                    break
                except UnicodeDecodeError:
                    continue
            
            if conteudo is None:
                print(f"❌ Não foi possível ler: {arquivo}")
                continue
            
            # Verificar se há padrão problemático
            encontrou_problema = False
            for pattern in patterns:
                if re.search(pattern, conteudo, re.MULTILINE | re.IGNORECASE):
                    encontrou_problema = True
                    break
            
            if encontrou_problema:
                print(f"🔧 Corrigindo: {arquivo} (encoding: {encoding_usado})")
                
                conteudo_original = conteudo
                
                # Aplicar todas as correções
                for pattern in patterns:
                    def replace_csrf(match):
                        atributos = match.group(1).strip()
                        return f'<form {atributos}>\n    <input type="hidden" name="csrf_token" value="{{{{ csrf_token() }}}}"/>'
                    
                    conteudo = re.sub(pattern, replace_csrf, conteudo, flags=re.MULTILINE | re.IGNORECASE)
                
                # Salvar arquivo corrigido com UTF-8
                with open(arquivo, 'w', encoding='utf-8') as f:
                    f.write(conteudo)
                
                # Contar correções
                correcoes = 0
                for pattern in patterns:
                    correcoes += len(re.findall(pattern, conteudo_original, re.MULTILINE | re.IGNORECASE))
                
                total_correcoes += correcoes
                arquivos_corrigidos.append(arquivo)
                
                print(f"   ✅ {correcoes} correções aplicadas")
        
        except Exception as e:
            print(f"❌ Erro ao processar {arquivo}: {e}")
    
    print(f"\n🎯 **RESUMO DA CORREÇÃO:**")
    print(f"   📁 Arquivos corrigidos: {len(arquivos_corrigidos)}")
    print(f"   🔧 Total de correções: {total_correcoes}")
    print(f"   ✅ Todos os tokens CSRF foram corrigidos para input hidden!")
    
    return arquivos_corrigidos

if __name__ == "__main__":
    print("🚀 Iniciando correção de tokens CSRF...")
    corrigir_csrf_tokens() 