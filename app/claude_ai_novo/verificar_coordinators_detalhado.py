#!/usr/bin/env python3
"""Verificação detalhada do módulo coordinators"""

import os
from pathlib import Path

def verificar_arquivo_detalhado(filepath):
    """Verifica arquivo mostrando detalhes específicos"""
    print(f"\n{'='*60}")
    print(f"📄 Arquivo: {filepath}")
    print('='*60)
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            conteudo = f.read()
            linhas = conteudo.split('\n')
        
        # Verifica imports
        print("\n🔍 IMPORTS RELACIONADOS AO BANCO:")
        imports_banco = []
        for i, linha in enumerate(linhas):
            if 'import' in linha and any(x in linha for x in ['db', 'flask_fallback', 'get_db', 'Pedido', 'Embarque', 'EntregaMonitorada']):
                imports_banco.append(f"  Linha {i+1}: {linha.strip()}")
        
        if imports_banco:
            for imp in imports_banco:
                print(imp)
        else:
            print("  Nenhum import relacionado ao banco encontrado")
        
        # Verifica uso de banco
        print("\n🔍 USO DE BANCO DE DADOS:")
        usos_banco = []
        for i, linha in enumerate(linhas):
            if any(x in linha for x in ['db.session', 'query(', 'filter(', 'filter_by(', 'self.db']):
                usos_banco.append(f"  Linha {i+1}: {linha.strip()}")
        
        if usos_banco:
            for uso in usos_banco[:10]:  # Mostra até 10 exemplos
                print(uso)
            if len(usos_banco) > 10:
                print(f"  ... e mais {len(usos_banco) - 10} ocorrências")
        else:
            print("  Nenhum acesso ao banco encontrado")
        
        # Verifica se tem property db
        print("\n🔍 PROPERTY DB:")
        tem_property = False
        for i, linha in enumerate(linhas):
            if '@property' in linha:
                if i+1 < len(linhas) and 'def db(self)' in linhas[i+1]:
                    tem_property = True
                    print(f"  ✅ Property db encontrada na linha {i+1}")
                    break
        
        if not tem_property:
            print("  ❌ Property db não encontrada")
        
        # Análise final
        print("\n📊 ANÁLISE:")
        tem_flask_fallback = 'from app.claude_ai_novo.utils.flask_fallback import' in conteudo
        tem_import_db_direto = 'from app import db' in conteudo
        usa_db_session = 'db.session' in conteudo
        
        if tem_import_db_direto:
            print("  ❌ PROBLEMA: Import direto de 'db'")
        if usa_db_session and not tem_flask_fallback:
            print("  ❌ PROBLEMA: Usa db.session sem flask_fallback")
        if tem_flask_fallback and tem_property:
            print("  ✅ OK: Usa flask_fallback corretamente")
        elif not any([tem_import_db_direto, usa_db_session, tem_flask_fallback]):
            print("  ✅ OK: Não acessa banco de dados")
        
    except Exception as e:
        print(f"  ❌ ERRO ao analisar arquivo: {e}")

def main():
    """Verifica todos os arquivos do coordinators"""
    print("🔍 VERIFICAÇÃO DETALHADA DO MÓDULO COORDINATORS")
    
    coordinators_path = Path("coordinators")
    
    # Lista todos os arquivos Python
    arquivos_py = list(coordinators_path.rglob("*.py"))
    arquivos_py = [f for f in arquivos_py if "__pycache__" not in str(f)]
    
    print(f"\n📁 Total de arquivos encontrados: {len(arquivos_py)}")
    
    for arquivo in sorted(arquivos_py):
        verificar_arquivo_detalhado(arquivo)
    
    print(f"\n{'='*60}")
    print("✅ Verificação concluída!")

if __name__ == "__main__":
    main() 