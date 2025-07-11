#!/usr/bin/env python3
"""Script para verificar pontas soltas nos orquestradores"""

import os
import json

def verificar_pontas_soltas():
    """Verifica se os orquestradores existem e importam os módulos"""
    
    print("🔍 VERIFICANDO PONTAS SOLTAS NOS ORQUESTRADORES")
    print("=" * 50)
    
    # Orquestradores principais que deveriam existir
    orquestradores = [
        'integration/integration_manager.py',
        'integration/advanced/advanced_integration.py',
        '__init__.py',
        'multi_agent/system.py',
        'coordinators/system.py',
        'data/data_manager.py'
    ]
    
    resultados = {}
    
    for orq in orquestradores:
        existe = os.path.exists(orq)
        
        if existe:
            # Contar imports
            try:
                with open(orq, 'r', encoding='utf-8') as f:
                    conteudo = f.read()
                    imports = conteudo.count('import')
                    linhas = len(conteudo.split('\n'))
                    
                print(f"✅ {orq}: {imports} imports, {linhas} linhas")
                resultados[orq] = {'existe': True, 'imports': imports, 'linhas': linhas}
            except Exception as e:
                print(f"⚠️ {orq}: Erro ao ler - {e}")
                resultados[orq] = {'existe': True, 'erro': str(e)}
        else:
            print(f"❌ {orq}: NÃO EXISTE")
            resultados[orq] = {'existe': False}
    
    # Verificar pastas com módulos órfãos
    pastas_modulos = ['analyzers', 'processors', 'learners', 'providers', 'coordinators']
    
    print("\n📂 VERIFICANDO PASTAS COM MÓDULOS:")
    for pasta in pastas_modulos:
        if os.path.exists(pasta):
            arquivos = [f for f in os.listdir(pasta) if f.endswith('.py') and f != '__init__.py']
            print(f"📁 {pasta}: {len(arquivos)} módulos")
            resultados[f"pasta_{pasta}"] = {'existe': True, 'modulos': len(arquivos)}
        else:
            print(f"❌ {pasta}: NÃO EXISTE")
            resultados[f"pasta_{pasta}"] = {'existe': False}
    
    # Conclusões
    print("\n🎯 CONCLUSÕES:")
    orquestradores_faltando = [k for k, v in resultados.items() if not k.startswith('pasta_') and not v['existe']]
    
    if orquestradores_faltando:
        print(f"❌ PONTAS SOLTAS CRÍTICAS: {len(orquestradores_faltando)} orquestradores faltando")
        print("   Isso explica os 108 módulos órfãos!")
        for orq in orquestradores_faltando:
            print(f"   - {orq}")
    else:
        print("✅ Todos os orquestradores principais existem")
    
    # Salvar resultado
    with open('resultado_pontas_soltas.json', 'w', encoding='utf-8') as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)
    
    return resultados

if __name__ == "__main__":
    verificar_pontas_soltas() 