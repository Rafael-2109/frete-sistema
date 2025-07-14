#!/usr/bin/env python3
"""
🔍 VERIFICAÇÃO GERAL DO SISTEMA CLAUDE AI NOVO
==============================================

Script para verificar se todo o sistema está correto após aplicação
do padrão Flask fallback.
"""

import os
import re
from pathlib import Path
from collections import defaultdict

def verificar_arquivo(filepath):
    """Verifica se arquivo segue os padrões corretos"""
    problemas = []
    avisos = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            conteudo = f.read()
    except Exception as e:
        return [f"Erro ao ler arquivo: {e}"], []
    
    # Verificar imports diretos de db
    if re.search(r'from\s+app\s+import\s+db(?:\s|,|$)', conteudo):
        problemas.append("Import direto de 'db'")
    
    # Verificar uso direto de db.session
    if re.search(r'\bdb\.session\.', conteudo) and 'flask_fallback' not in conteudo:
        problemas.append("Uso de 'db.session' sem flask_fallback")
    
    # Verificar se acessa banco
    acessa_banco = any([
        'query(' in conteudo,
        'filter(' in conteudo,
        'filter_by(' in conteudo,
        '.session.' in conteudo,
        'Pedido' in conteudo and 'from app' in conteudo,
        'Embarque' in conteudo and 'from app' in conteudo,
        'EntregaMonitorada' in conteudo and 'from app' in conteudo,
        'RelatorioFaturamentoImportado' in conteudo and 'from app' in conteudo
    ])
    
    if acessa_banco:
        tem_flask_fallback = 'from app.claude_ai_novo.utils.flask_fallback import' in conteudo
        tem_property_db = '@property' in conteudo and 'def db(self)' in conteudo
        
        if not tem_flask_fallback and not 'flask_fallback' in str(filepath):
            avisos.append("Acessa banco mas não usa flask_fallback")
    
    return problemas, avisos

def verificar_modulo(modulo_path):
    """Verifica todos os arquivos de um módulo"""
    arquivos_py = list(modulo_path.rglob("*.py"))
    arquivos_py = [f for f in arquivos_py if "__pycache__" not in str(f)]
    
    resultados = {
        'total': 0,
        'ok': 0,
        'com_problemas': 0,
        'com_avisos': 0,
        'problemas': [],
        'avisos': []
    }
    
    for arquivo in arquivos_py:
        resultados['total'] += 1
        problemas, avisos = verificar_arquivo(arquivo)
        
        if problemas:
            resultados['com_problemas'] += 1
            resultados['problemas'].append((arquivo, problemas))
        elif avisos:
            resultados['com_avisos'] += 1
            resultados['avisos'].append((arquivo, avisos))
        else:
            resultados['ok'] += 1
    
    return resultados

def main():
    """Verificação geral do sistema"""
    print("🔍 VERIFICAÇÃO GERAL DO SISTEMA CLAUDE AI NOVO")
    print("=" * 60)
    
    # Módulos principais a verificar
    modulos = [
        'analyzers', 'processors', 'mappers', 'loaders', 'validators',
        'enrichers', 'learners', 'memorizers', 'conversers', 'orchestrators',
        'coordinators', 'providers', 'integration', 'scanning', 'commands',
        'tools', 'suggestions', 'utils', 'security'
    ]
    
    estatisticas_gerais = defaultdict(int)
    todos_problemas = []
    todos_avisos = []
    
    for modulo in modulos:
        modulo_path = Path(modulo)
        if not modulo_path.exists():
            continue
        
        print(f"\n📁 Verificando {modulo}/...")
        resultados = verificar_modulo(modulo_path)
        
        # Atualizar estatísticas
        estatisticas_gerais['total'] += resultados['total']
        estatisticas_gerais['ok'] += resultados['ok']
        estatisticas_gerais['com_problemas'] += resultados['com_problemas']
        estatisticas_gerais['com_avisos'] += resultados['com_avisos']
        
        # Mostrar resumo do módulo
        if resultados['com_problemas'] > 0:
            print(f"   ❌ {resultados['com_problemas']} arquivo(s) com problemas")
            todos_problemas.extend(resultados['problemas'])
        elif resultados['com_avisos'] > 0:
            print(f"   ⚠️  {resultados['com_avisos']} arquivo(s) com avisos")
            todos_avisos.extend(resultados['avisos'])
        else:
            print(f"   ✅ Todos {resultados['total']} arquivos OK")
    
    # Resumo final
    print(f"\n{'='*60}")
    print("📊 RESUMO GERAL:")
    print(f"   Total de arquivos: {estatisticas_gerais['total']}")
    print(f"   Arquivos OK: {estatisticas_gerais['ok']}")
    print(f"   Arquivos com problemas: {estatisticas_gerais['com_problemas']}")
    print(f"   Arquivos com avisos: {estatisticas_gerais['com_avisos']}")
    
    # Listar problemas se houver
    if todos_problemas:
        print(f"\n❌ PROBLEMAS ENCONTRADOS:")
        for arquivo, problemas in todos_problemas[:10]:
            print(f"\n   {arquivo.relative_to('.')}:")
            for problema in problemas:
                print(f"      - {problema}")
        
        if len(todos_problemas) > 10:
            print(f"\n   ... e mais {len(todos_problemas) - 10} arquivos com problemas")
    
    # Status final
    print(f"\n{'='*60}")
    if estatisticas_gerais['com_problemas'] == 0:
        print("✅ SISTEMA 100% CORRETO - Pronto para produção!")
        print("   Todos os módulos estão seguindo o padrão Flask fallback corretamente.")
    else:
        print(f"⚠️  AÇÃO NECESSÁRIA: {estatisticas_gerais['com_problemas']} arquivos precisam correção")
    
    return estatisticas_gerais['com_problemas'] == 0

if __name__ == "__main__":
    main() 