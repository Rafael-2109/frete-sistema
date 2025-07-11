#!/usr/bin/env python3
"""
🧪 TESTE COMPLETO DE MÓDULOS - Claude AI Novo
=============================================

Testa todos os módulos do sistema Claude AI Novo para verificar:
- Imports funcionando
- Classes instanciáveis  
- Métodos principais disponíveis
- Compatibilidade entre componentes

Versão: 2.0 - Com PYTHONPATH corrigido
"""

import sys
import os
import importlib
import traceback
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import json
from datetime import datetime

# 🔧 CORREÇÃO CRÍTICA: Adicionar diretório pai ao PYTHONPATH
current_dir = Path(__file__).parent
parent_dir = current_dir.parent  # Vai para app/
root_dir = parent_dir.parent     # Vai para raiz do projeto

# Adicionar caminhos necessários
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(parent_dir))
sys.path.insert(0, str(current_dir))

print(f"📂 Diretório atual: {current_dir}")
print(f"📂 Diretório pai: {parent_dir}")
print(f"📂 Diretório raiz: {root_dir}")
print(f"🔧 PYTHONPATH configurado para encontrar módulo 'app'\n")

class TestadorModulos:
    """Testador completo de módulos do Claude AI Novo"""
    
    def __init__(self):
        self.resultados = {}
        self.estatisticas = {
            'total_modulos': 0,
            'sucessos': 0,
            'falhas': 0,
            'por_categoria': {}
        }
        
        # Mapeamento de módulos por categoria
        self.categorias = {
            'ANALYZERS': [
                'analyzers.analyzer_manager',
                'analyzers.intention_analyzer',
                'analyzers.query_analyzer',
                'analyzers.semantic_analyzer',
                'analyzers.structural_analyzer'
            ],
            'PROCESSORS': [
                'processors.context_processor',
                'processors.query_processor',
                'processors.data_processor',
                'processors.intelligence_processor',
                'processors.semantic_loop_processor'
            ],
            'LOADERS': [
                'loaders.context_loader',
                'loaders.database_loader'
            ],
            'MAPPERS': [
                'mappers.semantic_mapper',
                'mappers.pedidos_mapper',
                'mappers.embarques_mapper',
                'mappers.entregas_mapper',
                'mappers.faturamento_mapper',
                'mappers.fretes_mapper',
                'mappers.agendamentos_mapper'
            ],
            'VALIDATORS': [
                'validators.data_validator'
            ],
            'ENRICHERS': [
                'enrichers.semantic_enricher'
            ],
            'LEARNERS': [
                'learners.pattern_learner',
                'learners.human_in_loop_learning',
                'learners.learning_core',
                'learners.adaptive_learning'
            ],
            'MEMORIZERS': [
                'memorizers.knowledge_manager'
            ],
            'CONVERSERS': [
                'conversers.conversation_manager'
            ],
            'ORCHESTRATORS': [
                'orchestrators.multi_agent_orchestrator',
                'orchestrators.intelligence_manager'
            ],
            'COORDINATORS': [
                'coordinators.integration_coordinator',
                'coordinators.intelligence_coordinator'
            ],
            'PROVIDERS': [
                'providers.data_provider'
            ],
            'INTEGRATION': [
                'integration.integration_manager',
                'integration.claude.claude_integration',
                'integration.advanced.advanced_integration'
            ],
            'SCANNING': [
                'scanning.code_scanner',
                'scanning.database_scanner',
                'scanning.structure_scanner',
                'scanning.project_scanner'
            ],
            'COMMANDS': [
                'commands.base',
                'commands.auto_command_processor',
                'commands.cursor_commands',
                'commands.dev_commands',
                'commands.file_commands',
                'commands.excel.fretes',
                'commands.excel.pedidos',
                'commands.excel.entregas',
                'commands.excel.faturamento',
                'commands.excel_orchestrator'
            ],
            'TOOLS': [
                'tools.tools_manager'
            ],
            'SUGGESTIONS': [
                'suggestions.engine',
                'suggestions.suggestions_manager'
            ],
            'UTILS': [
                'utils.base_classes',
                'utils.flask_context_wrapper',
                'utils.flask_fallback',
                'utils.response_utils',
                'utils.utils_manager'
            ],
            'CONFIG': [
                'config.advanced_config',
                'config.system_config'
            ],
            'SECURITY': [
                'security.security_guard'
            ],
            'TESTS': [
                'tests.test_advanced_integration',
                'tests.test_config'
            ]
        }
    
    def testar_modulo(self, nome_modulo: str) -> Dict[str, Any]:
        """Testa um módulo específico"""
        resultado = {
            'nome': nome_modulo,
            'sucesso': False,
            'erro': None,
            'classes_encontradas': [],
            'funcoes_encontradas': [],
            'detalhes': {}
        }
        
        try:
            # Tentar importar o módulo
            modulo = importlib.import_module(nome_modulo)
            resultado['sucesso'] = True
            
            # Analisar conteúdo do módulo
            for attr_name in dir(modulo):
                if not attr_name.startswith('_'):
                    attr = getattr(modulo, attr_name)
                    if isinstance(attr, type):
                        resultado['classes_encontradas'].append(attr_name)
                    elif callable(attr):
                        resultado['funcoes_encontradas'].append(attr_name)
            
            resultado['detalhes']['total_attrs'] = len(resultado['classes_encontradas']) + len(resultado['funcoes_encontradas'])
            
        except Exception as e:
            resultado['erro'] = str(e)
            resultado['detalhes']['traceback'] = traceback.format_exc()
        
        return resultado
    
    def testar_categoria(self, categoria: str, modulos: List[str]) -> Dict[str, Any]:
        """Testa todos os módulos de uma categoria"""
        print(f"\n🔍 Testando categoria: {categoria}")
        
        resultados_categoria = []
        sucessos = 0
        
        for modulo in modulos:
            resultado = self.testar_modulo(modulo)
            resultados_categoria.append(resultado)
            
            if resultado['sucesso']:
                print(f"  ✅ {modulo}")
                sucessos += 1
            else:
                print(f"  ❌ {modulo}: {resultado['erro']}")
        
        taxa_sucesso = (sucessos / len(modulos)) * 100 if modulos else 0
        print(f"  📊 {categoria}: {sucessos}/{len(modulos)} ({taxa_sucesso:.1f}%)")
        
        return {
            'categoria': categoria,
            'modulos': resultados_categoria,
            'sucessos': sucessos,
            'total': len(modulos),
            'taxa_sucesso': taxa_sucesso
        }
    
    def executar_teste_completo(self) -> Dict[str, Any]:
        """Executa teste completo de todos os módulos"""
        print("🚀 Iniciando teste completo do Claude AI Novo...")
        print("=" * 60)
        
        resultados_por_categoria = {}
        total_sucessos = 0
        total_modulos = 0
        
        # Testar cada categoria
        for categoria, modulos in self.categorias.items():
            resultado_categoria = self.testar_categoria(categoria, modulos)
            resultados_por_categoria[categoria] = resultado_categoria
            
            total_sucessos += resultado_categoria['sucessos']
            total_modulos += resultado_categoria['total']
        
        # Calcular estatísticas finais
        taxa_sucesso_geral = (total_sucessos / total_modulos) * 100 if total_modulos > 0 else 0
        
        print("\n" + "=" * 60)
        print("📊 RELATÓRIO FINAL")
        print("=" * 60)
        
        print(f"📈 Taxa de Sucesso Geral: {taxa_sucesso_geral:.1f}% ({total_sucessos}/{total_modulos})")
        print(f"✅ Módulos Funcionando: {total_sucessos}")
        print(f"❌ Módulos com Problema: {total_modulos - total_sucessos}")
        
        print("\n📋 Resumo por Categoria:")
        for categoria, resultado in resultados_por_categoria.items():
            status = "🟢" if resultado['taxa_sucesso'] == 100 else "🟡" if resultado['taxa_sucesso'] >= 50 else "🔴"
            print(f"  {status} {categoria}: {resultado['sucessos']}/{resultado['total']} ({resultado['taxa_sucesso']:.1f}%)")
        
        # Salvar relatório detalhado
        relatorio_completo = {
            'timestamp': datetime.now().isoformat(),
            'estatisticas_gerais': {
                'total_modulos': total_modulos,
                'total_sucessos': total_sucessos,
                'taxa_sucesso_geral': taxa_sucesso_geral
            },
            'resultados_por_categoria': resultados_por_categoria,
            'pythonpath_configurado': {
                'current_dir': str(current_dir),
                'parent_dir': str(parent_dir),
                'root_dir': str(root_dir)
            }
        }
        
        with open('RELATORIO_TESTE_PYTHONPATH.json', 'w', encoding='utf-8') as f:
            json.dump(relatorio_completo, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Relatório salvo em: RELATORIO_TESTE_PYTHONPATH.json")
        
        return relatorio_completo

def main():
    """Função principal"""
    testador = TestadorModulos()
    testador.executar_teste_completo()

if __name__ == "__main__":
    main() 