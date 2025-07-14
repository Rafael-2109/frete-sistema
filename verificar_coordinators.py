#!/usr/bin/env python3
"""Script para verificar se módulo coordinators está correto com Flask fallback"""

import os
import re
from pathlib import Path

def verificar_arquivo(filepath):
    """Verifica se arquivo usa Flask fallback corretamente"""
    problemas = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        conteudo = f.read()
        linhas = conteudo.split('\n')
    
    # Verifica imports diretos de db
    if re.search(r'from\s+app\s+import\s+db(?:\s|,|$)', conteudo):
        problemas.append("❌ Import direto de 'db' encontrado")
    
    if re.search(r'from\s+app\.models\s+import.*\bdb\b', conteudo):
        problemas.append("❌ Import de 'db' via app.models")
    
    # Verifica uso direto de db.session
    if re.search(r'\bdb\.session\.', conteudo):
        problemas.append("❌ Uso direto de 'db.session' encontrado")
    
    # Verifica se acessa banco de dados
    acessa_banco = any([
        'query(' in conteudo,
        'filter(' in conteudo,
        'filter_by(' in conteudo,
        'session.query' in conteudo,
        'session.add' in conteudo,
        'session.commit' in conteudo,
        'RelatorioFaturamentoImportado' in conteudo,
        'Pedido' in conteudo,
        'Embarque' in conteudo,
        'EntregaMonitorada' in conteudo,
        'Separacao' in conteudo,
        'Frete' in conteudo,
        'MonitoramentoEntregas' in conteudo
    ])
    
    # Se acessa banco, verifica se tem Flask fallback
    if acessa_banco:
        tem_flask_fallback = 'from app.claude_ai_novo.utils.flask_fallback import' in conteudo
        tem_property_db = '@property' in conteudo and 'def db(self)' in conteudo
        usa_self_db = 'self.db.' in conteudo
        
        if not tem_flask_fallback:
            problemas.append("⚠️  Acessa banco mas não importa flask_fallback")
        
        if tem_flask_fallback and not (tem_property_db or usa_self_db):
            problemas.append("⚠️  Importa flask_fallback mas não parece usar")
    
    return problemas

def main():
    """Verifica todos os arquivos do módulo coordinators"""
    print("🔍 Verificando módulo coordinators...\n")
    
    coordinators_path = Path("coordinators")
    arquivos_py = list(coordinators_path.rglob("*.py"))
    
    total_arquivos = 0
    arquivos_com_problemas = 0
    todos_problemas = []
    
    for arquivo in sorted(arquivos_py):
        if "__pycache__" in str(arquivo):
            continue
            
        total_arquivos += 1
        caminho_relativo = arquivo.relative_to(".")
        problemas = verificar_arquivo(arquivo)
        
        if problemas:
            arquivos_com_problemas += 1
            print(f"\n❌ {caminho_relativo}:")
            for problema in problemas:
                print(f"   {problema}")
            todos_problemas.append((str(caminho_relativo), problemas))
        else:
            print(f"✅ {caminho_relativo}")
    
    # Resumo
    print(f"\n{'='*60}")
    print(f"📊 RESUMO:")
    print(f"   Total de arquivos: {total_arquivos}")
    print(f"   Arquivos OK: {total_arquivos - arquivos_com_problemas}")
    print(f"   Arquivos com problemas: {arquivos_com_problemas}")
    
    if arquivos_com_problemas > 0:
        print(f"\n⚠️  AÇÃO NECESSÁRIA:")
        print(f"   {arquivos_com_problemas} arquivo(s) precisam de correção")
    else:
        print(f"\n✅ TODOS OS ARQUIVOS ESTÃO CORRETOS!")
    
    return arquivos_com_problemas == 0

if __name__ == "__main__":
    main() 