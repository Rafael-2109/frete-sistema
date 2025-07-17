#!/usr/bin/env python3
"""
Script para substituir separacao_lote_id por separacao_lote_id
em app/carteira/routes.py
"""

import re

def fix_carteira_routes():
    file_path = 'app/carteira/routes.py'
    
    print(f"🔧 Corrigindo {file_path}...")
    
    try:
        # Ler arquivo
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Substituições específicas
        replacements = [
            # Campos de modelo
            ('separacao_lote_id', 'separacao_lote_id'),
            # Funções relacionadas  
            ('separacao_lote_id_invalido', 'separacao_lote_id_invalido'),
            # Comentários
            ('separacao_lote_id, peso, pallet', 'separacao_lote_id, peso, pallet'),
            ('considerando separacao_lote_id', 'considerando separacao_lote_id'),
            ('separacao_lote_id na carteira', 'separacao_lote_id na carteira'),
            ('separacao_lote_id: Vínculo', 'separacao_lote_id: Vínculo'),
        ]
        
        # Aplicar substituições
        original_content = content
        for old, new in replacements:
            content = content.replace(old, new)
        
        # Verificar se houve mudanças
        if content != original_content:
            # Escrever arquivo corrigido
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("✅ Arquivo corrigido com sucesso!")
            
            # Contar substituições
            lines_changed = 0
            for line_old, line_new in zip(original_content.split('\n'), content.split('\n')):
                if line_old != line_new:
                    lines_changed += 1
            
            print(f"📊 {lines_changed} linhas alteradas")
        else:
            print("ℹ️ Nenhuma alteração necessária")
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = fix_carteira_routes()
    if success:
        print("🎯 Correção concluída!")
    else:
        print("�� Correção falhou!") 