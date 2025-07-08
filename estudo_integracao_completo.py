#!/usr/bin/env python3
"""
📊 ESTUDO DE INTEGRAÇÃO COMPLETO - CLAUDE AI NOVO
Análise abrangente de todos os módulos e suas integrações

OBJETIVOS:
1. Mapear TODOS os módulos do claude_ai_novo
2. Identificar lacunas de integração
3. Verificar se routes.py usa o sistema novo
4. Listar funcionalidades não integradas
5. Criar plano de integração completa
"""

import os
import sys
import importlib
import inspect
from pathlib import Path
from typing import Dict, List, Any, Set, Optional
from datetime import datetime
import ast

class EstudoIntegracaoCompleto:
    """Analisa completamente a integração do claude_ai_novo"""
    
    def __init__(self):
        self.base_path = Path("app/claude_ai_novo")
        self.modules_map = {}
        self.classes_map = {}
        self.functions_map = {}
        self.integration_gaps = []
        self.integration_status = {}
        
    def executar_estudo_completo(self) -> Dict[str, Any]:
        """Executa estudo completo de integração"""
        print("🔍 INICIANDO ESTUDO COMPLETO DE INTEGRAÇÃO")
        print("=" * 60)
        
        # 1. Mapear todos os módulos
        print("\n1️⃣ MAPEANDO TODOS OS MÓDULOS...")
        self._mapear_todos_modulos()
        
        # 2. Analisar classes e funções
        print("\n2️⃣ ANALISANDO CLASSES E FUNÇÕES...")
        self._analisar_classes_funcoes()
        
        # 3. Verificar integração com routes.py
        print("\n3️⃣ VERIFICANDO INTEGRAÇÃO COM ROUTES.PY...")
        self._verificar_integracao_routes()
        
        # 4. Verificar sistema de transição
        print("\n4️⃣ VERIFICANDO SISTEMA DE TRANSIÇÃO...")
        self._verificar_sistema_transicao()
        
        # 5. Identificar lacunas
        print("\n5️⃣ IDENTIFICANDO LACUNAS DE INTEGRAÇÃO...")
        self._identificar_lacunas()
        
        # 6. Gerar relatório
        print("\n6️⃣ GERANDO RELATÓRIO COMPLETO...")
        relatorio = self._gerar_relatorio_completo()
        
        return relatorio
    
    def _mapear_todos_modulos(self):
        """Mapeia todos os módulos do claude_ai_novo"""
        print(f"📁 Analisando diretório: {self.base_path}")
        
        # Percorrer toda a estrutura
        for root, dirs, files in os.walk(self.base_path):
            # Ignorar __pycache__
            dirs[:] = [d for d in dirs if d != '__pycache__']
            
            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    relative_path = file_path.relative_to(self.base_path)
                    
                    # Converter para módulo Python
                    module_name = str(relative_path.with_suffix(''))
                    module_name = module_name.replace(os.sep, '.')
                    
                    # Analisar módulo
                    self._analisar_modulo(file_path, module_name)
    
    def _analisar_modulo(self, file_path: Path, module_name: str):
        """Analisa um módulo específico"""
        try:
            # Ler arquivo
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parsear AST
            tree = ast.parse(content)
            
            # Extrair informações
            module_info = {
                'path': str(file_path),
                'module_name': module_name,
                'classes': [],
                'functions': [],
                'imports': [],
                'size_lines': len(content.splitlines()),
                'size_bytes': len(content.encode('utf-8')),
                'last_modified': datetime.fromtimestamp(file_path.stat().st_mtime)
            }
            
            # Analisar AST
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    module_info['classes'].append({
                        'name': node.name,
                        'methods': [n.name for n in node.body if isinstance(n, ast.FunctionDef)],
                        'line': node.lineno
                    })
                elif isinstance(node, ast.FunctionDef):
                    # Apenas funções no nível do módulo
                    if node.col_offset == 0:
                        module_info['functions'].append({
                            'name': node.name,
                            'line': node.lineno,
                            'args': len(node.args.args)
                        })
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        module_info['imports'].append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        for alias in node.names:
                            module_info['imports'].append(f"{node.module}.{alias.name}")
            
            self.modules_map[module_name] = module_info
            print(f"✅ {module_name} - {len(module_info['classes'])} classes, {len(module_info['functions'])} functions")
            
        except Exception as e:
            print(f"❌ Erro ao analisar {module_name}: {e}")
            self.modules_map[module_name] = {
                'error': str(e),
                'path': str(file_path)
            }
    
    def _analisar_classes_funcoes(self):
        """Análise detalhada de classes e funções"""
        total_classes = 0
        total_functions = 0
        
        for module_name, module_info in self.modules_map.items():
            if 'error' in module_info:
                continue
                
            # Mapear classes
            for class_info in module_info.get('classes', []):
                class_key = f"{module_name}.{class_info['name']}"
                self.classes_map[class_key] = {
                    'module': module_name,
                    'name': class_info['name'],
                    'methods': class_info['methods'],
                    'line': class_info['line']
                }
                total_classes += 1
            
            # Mapear funções
            for func_info in module_info.get('functions', []):
                func_key = f"{module_name}.{func_info['name']}"
                self.functions_map[func_key] = {
                    'module': module_name,
                    'name': func_info['name'],
                    'args': func_info['args'],
                    'line': func_info['line']
                }
                total_functions += 1
        
        print(f"📊 Total: {total_classes} classes, {total_functions} funções")
    
    def _verificar_integracao_routes(self):
        """Verifica se routes.py usa o sistema novo"""
        routes_path = "app/claude_ai/routes.py"
        
        if not os.path.exists(routes_path):
            self.integration_status['routes'] = {'status': 'error', 'message': 'Arquivo routes.py não encontrado'}
            return
        
        try:
            with open(routes_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Verificar imports do sistema novo
            novo_imports = [
                'claude_ai_novo',
                'ClaudeAINovo',
                'IntegrationManager',
                'AdvancedAIIntegration',
                'create_claude_ai_novo'
            ]
            
            imports_found = []
            for import_name in novo_imports:
                if import_name in content:
                    imports_found.append(import_name)
            
            # Verificar uso do sistema de transição
            transicao_usado = 'processar_consulta_transicao' in content
            
            self.integration_status['routes'] = {
                'status': 'analyzed',
                'imports_novo_sistema': imports_found,
                'usa_transicao': transicao_usado,
                'total_imports_novo': len(imports_found),
                'integracao_direta': len(imports_found) > 0
            }
            
            print(f"📋 Routes.py - Imports do sistema novo: {len(imports_found)}")
            print(f"📋 Routes.py - Usa transição: {transicao_usado}")
            
        except Exception as e:
            self.integration_status['routes'] = {
                'status': 'error',
                'message': str(e)
            }
    
    def _verificar_sistema_transicao(self):
        """Verifica se o sistema de transição funciona"""
        transicao_path = "app/claude_transition.py"
        
        if not os.path.exists(transicao_path):
            self.integration_status['transicao'] = {'status': 'missing'}
            return
        
        try:
            with open(transicao_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Verificar imports
            imports_necessarios = {
                'claude_ai_novo': 'app.claude_ai_novo.integration.claude' in content,
                'claude_antigo': 'app.claude_ai.claude_real_integration' in content,
                'system_switch': 'alternar_sistema' in content
            }
            
            self.integration_status['transicao'] = {
                'status': 'analyzed',
                'imports_verificados': imports_necessarios,
                'funcional': all(imports_necessarios.values())
            }
            
            print(f"🔄 Sistema de transição - Funcional: {all(imports_necessarios.values())}")
            
        except Exception as e:
            self.integration_status['transicao'] = {
                'status': 'error',
                'message': str(e)
            }
    
    def _identificar_lacunas(self):
        """Identifica lacunas de integração"""
        print("🔍 IDENTIFICANDO LACUNAS...")
        
        # Lacuna 1: Routes.py não usa sistema novo diretamente
        if not self.integration_status['routes'].get('integracao_direta'):
            self.integration_gaps.append({
                'tipo': 'INTEGRAÇÃO_ROUTES',
                'severidade': 'ALTA',
                'descrição': 'Routes.py não importa diretamente o sistema novo',
                'solução': 'Adicionar imports do ClaudeAINovo e IntegrationManager'
            })
        
        # Lacuna 2: Módulos órfãos (não referenciados)
        modulos_referenciados = set()
        
        # Verificar referências no IntegrationManager
        integration_manager_path = "app/claude_ai_novo/integration_manager.py"
        if os.path.exists(integration_manager_path):
            with open(integration_manager_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Extrair módulos referenciados
            for module_name in self.modules_map.keys():
                if module_name in content:
                    modulos_referenciados.add(module_name)
        
        # Encontrar módulos órfãos
        modulos_orfaos = []
        for module_name in self.modules_map.keys():
            if module_name not in modulos_referenciados:
                # Verificar se não é módulo de teste ou auxiliar
                if not any(x in module_name for x in ['test', 'docs', '__pycache__', 'migrations']):
                    modulos_orfaos.append(module_name)
        
        if modulos_orfaos:
            self.integration_gaps.append({
                'tipo': 'MÓDULOS_ÓRFÃOS',
                'severidade': 'MÉDIA',
                'descrição': f'{len(modulos_orfaos)} módulos não referenciados',
                'módulos': modulos_orfaos,
                'solução': 'Integrar módulos ao IntegrationManager'
            })
        
        # Lacuna 3: Sistema de transição não funcional
        if not self.integration_status['transicao'].get('funcional'):
            self.integration_gaps.append({
                'tipo': 'SISTEMA_TRANSIÇÃO',
                'severidade': 'CRÍTICA',
                'descrição': 'Sistema de transição não está funcional',
                'solução': 'Corrigir imports e configuração da transição'
            })
        
        print(f"❌ Lacunas identificadas: {len(self.integration_gaps)}")
    
    def _gerar_relatorio_completo(self) -> Dict[str, Any]:
        """Gera relatório completo do estudo"""
        # Estatísticas gerais
        total_modules = len(self.modules_map)
        total_classes = len(self.classes_map)
        total_functions = len(self.functions_map)
        
        # Módulos por categoria
        categorias = {
            'multi_agent': [m for m in self.modules_map.keys() if 'multi_agent' in m],
            'intelligence': [m for m in self.modules_map.keys() if 'intelligence' in m],
            'semantic': [m for m in self.modules_map.keys() if 'semantic' in m],
            'integration': [m for m in self.modules_map.keys() if 'integration' in m],
            'data': [m for m in self.modules_map.keys() if 'data' in m],
            'suggestions': [m for m in self.modules_map.keys() if 'suggestions' in m],
            'commands': [m for m in self.modules_map.keys() if 'commands' in m],
            'utils': [m for m in self.modules_map.keys() if 'utils' in m],
            'outros': []
        }
        
        # Classificar módulos não categorizados
        categorized_modules = set()
        for categoria, modules in categorias.items():
            if categoria != 'outros':
                categorized_modules.update(modules)
        
        categorias['outros'] = [m for m in self.modules_map.keys() if m not in categorized_modules]
        
        # Relatório final
        relatorio = {
            'timestamp': datetime.now().isoformat(),
            'resumo_executivo': {
                'total_modules': total_modules,
                'total_classes': total_classes,
                'total_functions': total_functions,
                'lacunas_identificadas': len(self.integration_gaps),
                'status_integracao': self._calcular_status_integracao()
            },
            'detalhes_modulos': {
                'categorias': categorias,
                'modules_map': self.modules_map,
                'classes_map': self.classes_map,
                'functions_map': self.functions_map
            },
            'analise_integracao': {
                'routes_status': self.integration_status.get('routes', {}),
                'transicao_status': self.integration_status.get('transicao', {}),
                'lacunas': self.integration_gaps
            },
            'recomendacoes': self._gerar_recomendacoes()
        }
        
        return relatorio
    
    def _calcular_status_integracao(self) -> str:
        """Calcula status geral da integração"""
        if len(self.integration_gaps) == 0:
            return "COMPLETA"
        elif len(self.integration_gaps) <= 2:
            return "QUASE_COMPLETA"
        elif len(self.integration_gaps) <= 5:
            return "PARCIAL"
        else:
            return "CRÍTICA"
    
    def _gerar_recomendacoes(self) -> List[Dict[str, Any]]:
        """Gera recomendações para melhorar a integração"""
        recomendacoes = []
        
        # Recomendação 1: Integração direta com routes.py
        if not self.integration_status['routes'].get('integracao_direta'):
            recomendacoes.append({
                'prioridade': 'ALTA',
                'titulo': 'Integração direta com routes.py',
                'descricao': 'Adicionar imports diretos do sistema novo no routes.py',
                'acao': 'Modificar app/claude_ai/routes.py para usar ClaudeAINovo',
                'beneficio': 'Acesso completo às funcionalidades do sistema novo'
            })
        
        # Recomendação 2: Corrigir sistema de transição
        if not self.integration_status['transicao'].get('funcional'):
            recomendacoes.append({
                'prioridade': 'CRÍTICA',
                'titulo': 'Corrigir sistema de transição',
                'descricao': 'Resolver problemas nos imports do sistema de transição',
                'acao': 'Verificar e corrigir imports em app/claude_transition.py',
                'beneficio': 'Alternância funcional entre sistemas antigo e novo'
            })
        
        # Recomendação 3: Integrar módulos órfãos
        modulos_orfaos = []
        for gap in self.integration_gaps:
            if gap['tipo'] == 'MÓDULOS_ÓRFÃOS':
                modulos_orfaos = gap.get('módulos', [])
                break
        
        if modulos_orfaos:
            recomendacoes.append({
                'prioridade': 'MÉDIA',
                'titulo': 'Integrar módulos órfãos',
                'descricao': f'Integrar {len(modulos_orfaos)} módulos não referenciados',
                'acao': 'Adicionar módulos ao IntegrationManager',
                'beneficio': 'Aproveitamento completo de todas as funcionalidades'
            })
        
        return recomendacoes
    
    def imprimir_relatorio(self, relatorio: Dict[str, Any]):
        """Imprime relatório formatado"""
        print("\n" + "="*80)
        print("📊 RELATÓRIO COMPLETO DE INTEGRAÇÃO - CLAUDE AI NOVO")
        print("="*80)
        
        # Resumo executivo
        resumo = relatorio['resumo_executivo']
        print(f"\n🎯 RESUMO EXECUTIVO:")
        print(f"   📦 Total de módulos: {resumo['total_modules']}")
        print(f"   🏗️ Total de classes: {resumo['total_classes']}")
        print(f"   ⚙️ Total de funções: {resumo['total_functions']}")
        print(f"   ❌ Lacunas identificadas: {resumo['lacunas_identificadas']}")
        print(f"   📊 Status de integração: {resumo['status_integracao']}")
        
        # Módulos por categoria
        categorias = relatorio['detalhes_modulos']['categorias']
        print(f"\n📂 MÓDULOS POR CATEGORIA:")
        for categoria, modules in categorias.items():
            if modules:
                print(f"   {categoria.upper()}: {len(modules)} módulos")
        
        # Análise de integração
        print(f"\n🔗 ANÁLISE DE INTEGRAÇÃO:")
        routes_status = relatorio['analise_integracao']['routes_status']
        if routes_status.get('status') == 'analyzed':
            print(f"   📋 Routes.py: {routes_status['total_imports_novo']} imports do sistema novo")
            print(f"   📋 Usa transição: {routes_status['usa_transicao']}")
        
        # Lacunas
        lacunas = relatorio['analise_integracao']['lacunas']
        if lacunas:
            print(f"\n❌ LACUNAS IDENTIFICADAS:")
            for lacuna in lacunas:
                print(f"   • {lacuna['tipo']} ({lacuna['severidade']}): {lacuna['descrição']}")
        
        # Recomendações
        recomendacoes = relatorio['recomendacoes']
        if recomendacoes:
            print(f"\n💡 RECOMENDAÇÕES:")
            for rec in recomendacoes:
                print(f"   • {rec['prioridade']} - {rec['titulo']}")
                print(f"     📝 {rec['descricao']}")
                print(f"     🔧 {rec['acao']}")
                print(f"     ✅ {rec['beneficio']}")
                print()


def main():
    """Executa estudo completo"""
    estudo = EstudoIntegracaoCompleto()
    relatorio = estudo.executar_estudo_completo()
    estudo.imprimir_relatorio(relatorio)
    
    # Salvar relatório
    import json
    with open('relatorio_integracao_completo.json', 'w', encoding='utf-8') as f:
        json.dump(relatorio, f, indent=2, ensure_ascii=False)
    
    print("\n💾 Relatório salvo em 'relatorio_integracao_completo.json'")
    print("✅ Estudo completo finalizado!")


if __name__ == "__main__":
    main() 