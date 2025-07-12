#!/usr/bin/env python3
"""
Script de verificação pré-commit
Executa testes automáticos para detectar loops antes do commit
"""

import sys
import os
import subprocess
import json
from datetime import datetime

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Importa o simulador
from app.claude_ai_novo.simular_producao import ProductionSimulator


def run_basic_tests():
    """Executa testes básicos de importação"""
    print("\n🔍 Verificando imports básicos...")
    
    try:
        from app.claude_ai_novo.integration.integration_manager import IntegrationManager
        from app.claude_ai_novo.orchestrators.orchestrator_manager import OrchestratorManager
        print("✅ Imports básicos OK")
        return True
    except Exception as e:
        print(f"❌ Erro nos imports: {e}")
        return False


def run_loop_detection():
    """Executa detecção de loops"""
    print("\n🔄 Executando detecção de loops...")
    
    simulator = ProductionSimulator()
    simulator.timeout_seconds = 5  # Timeout mais curto para pré-commit
    simulator.max_depth = 3  # Detecção mais agressiva
    
    # Testa queries problemáticas conhecidas
    critical_queries = [
        "Como estão as entregas do Atacadão?",
        "Status do sistema",
        "Relatório de fretes pendentes"
    ]
    
    all_passed = True
    
    for query in critical_queries:
        print(f"\n   Testando: '{query}'")
        result = simulator.simulate_query(query, {"_pre_commit_test": True})
        
        if not result['success']:
            print(f"   ❌ FALHOU!")
            all_passed = False
        else:
            print(f"   ✅ OK ({result['elapsed_time']:.2f}s)")
    
    return all_passed


def check_anti_loop_protection():
    """Verifica se proteções anti-loop estão ativas"""
    print("\n🛡️ Verificando proteções anti-loop...")
    
    checks = []
    
    # Verifica IntegrationManager
    integration_file = os.path.join(
        os.path.dirname(__file__), 
        'integration/integration_manager.py'
    )
    
    if os.path.exists(integration_file):
        with open(integration_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Verifica presença de proteções
        if '_from_orchestrator' in content:
            print("✅ Proteção _from_orchestrator encontrada")
            checks.append(True)
        else:
            print("❌ Proteção _from_orchestrator NÃO encontrada")
            checks.append(False)
            
        if 'anti-loop' in content.lower() or 'antiloop' in content.lower():
            print("✅ Resposta anti-loop encontrada")
            checks.append(True)
        else:
            print("❌ Resposta anti-loop NÃO encontrada")
            checks.append(False)
    
    # Verifica OrchestratorManager
    orchestrator_file = os.path.join(
        os.path.dirname(__file__), 
        'orchestrators/orchestrator_manager.py'
    )
    
    if os.path.exists(orchestrator_file):
        with open(orchestrator_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if '_from_integration' in content:
            print("✅ Proteção _from_integration encontrada")
            checks.append(True)
        else:
            print("❌ Proteção _from_integration NÃO encontrada")
            checks.append(False)
    
    return all(checks) if checks else False


def generate_report(results):
    """Gera relatório de verificação"""
    report = {
        'timestamp': datetime.now().isoformat(),
        'results': results,
        'passed': all(r['passed'] for r in results),
        'git_info': {}
    }
    
    # Tenta obter informações do Git
    try:
        branch = subprocess.check_output(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            text=True
        ).strip()
        report['git_info']['branch'] = branch
        
        commit = subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'],
            text=True
        ).strip()[:8]
        report['git_info']['commit'] = commit
    except:
        pass
    
    # Salva relatório
    report_file = f"pre_commit_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_path = os.path.join(os.path.dirname(__file__), report_file)
    
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Relatório salvo em: {report_file}")
    
    return report


def main():
    """Função principal do pré-commit check"""
    print("\n" + "="*60)
    print("🚀 VERIFICAÇÃO PRÉ-COMMIT - CLAUDE AI NOVO")
    print("="*60)
    
    results = []
    
    # 1. Testes básicos
    print("\n[1/3] Testes Básicos")
    basic_ok = run_basic_tests()
    results.append({
        'test': 'imports_basicos',
        'passed': basic_ok
    })
    
    if not basic_ok:
        print("\n❌ Falha nos testes básicos! Abortando...")
        return False
    
    # 2. Verificação de proteções
    print("\n[2/3] Verificação de Proteções")
    protections_ok = check_anti_loop_protection()
    results.append({
        'test': 'protecoes_antiloop',
        'passed': protections_ok
    })
    
    # 3. Detecção de loops
    print("\n[3/3] Detecção de Loops")
    loops_ok = run_loop_detection()
    results.append({
        'test': 'deteccao_loops',
        'passed': loops_ok
    })
    
    # Gera relatório
    report = generate_report(results)
    
    # Resultado final
    print("\n" + "="*60)
    if report['passed']:
        print("✅ TODAS AS VERIFICAÇÕES PASSARAM!")
        print("   Sistema seguro para commit.")
        return True
    else:
        print("❌ VERIFICAÇÕES FALHARAM!")
        print("\n   Problemas encontrados:")
        for r in results:
            if not r['passed']:
                print(f"   - {r['test']}")
        print("\n⚠️  NÃO FAÇA COMMIT até resolver os problemas!")
        return False


if __name__ == '__main__':
    # Executa verificações
    success = main()
    
    # Se chamado como hook, retorna código apropriado
    sys.exit(0 if success else 1) 