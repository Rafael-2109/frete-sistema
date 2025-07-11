#!/usr/bin/env python3
"""
🔍 INVENTORY SCANNER COMPLETO
============================

Sistema que escaneia TUDO no claude_ai_novo/ para garantir validação completa.
- Mapeia todos os arquivos, classes, funções, dependências
- Executa health checks em cada componente
- Gera relatório completo do sistema
- Identifica pontos críticos e de falha
"""

import os
import sys
import ast
import inspect
import importlib
import pkgutil
import json
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, asdict
import subprocess

# Adicionar ao path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

@dataclass
class ComponentInfo:
    """Informações detalhadas de um componente"""
    name: str
    type: str  # 'module', 'class', 'function', 'variable'
    file_path: str
    line_number: int
    dependencies: List[str]
    imports: List[str]
    methods: List[str]
    attributes: List[str]
    docstring: Optional[str]
    size_lines: int
    health_status: str  # 'healthy', 'warning', 'error', 'unknown'
    health_details: List[str]
    last_checked: str
    is_critical: bool
    fallback_available: bool

@dataclass
class SystemInventory:
    """Inventário completo do sistema"""
    scan_timestamp: str
    total_files: int
    total_modules: int
    total_classes: int
    total_functions: int
    components: List[ComponentInfo]
    dependency_graph: Dict[str, List[str]]
    critical_components: List[str]
    health_summary: Dict[str, int]
    recommendations: List[str]
    warnings: List[str]
    errors: List[str]

class InventoryScanner:
    """Scanner completo do sistema"""
    
    def __init__(self, base_path: Optional[str] = None):
        # Determinar o caminho base automaticamente
        if base_path is None:
            current_file = Path(__file__).parent
            if current_file.name == 'claude_ai_novo':
                self.base_path = current_file
            else:
                self.base_path = Path("app/claude_ai_novo")
        else:
            self.base_path = Path(base_path)
        self.components: List[ComponentInfo] = []
        self.dependency_graph: Dict[str, List[str]] = {}
        self.critical_components: Set[str] = set()
        self.warnings: List[str] = []
        self.errors: List[str] = []
        self.recommendations: List[str] = []
        
        # Componentes críticos conhecidos
        self.known_critical = {
            'orchestrators', 'integration', 'utils', 'processors',
            'analyzers', 'mappers', 'validators', 'providers'
        }
        
        print(f"🔍 Inventory Scanner inicializado para: {self.base_path}")
    
    def scan_complete_system(self) -> SystemInventory:
        """Escaneia o sistema completo"""
        print("🚀 Iniciando escaneamento completo do sistema...")
        
        # Fase 1: Descobrir todos os arquivos
        print("📁 Fase 1: Descobrindo arquivos...")
        python_files = self._discover_python_files()
        print(f"   📄 Encontrados {len(python_files)} arquivos Python")
        
        # Fase 2: Analisar estrutura de cada arquivo
        print("🔍 Fase 2: Analisando estrutura dos arquivos...")
        for file_path in python_files:
            self._analyze_file(file_path)
        
        # Fase 3: Mapear dependências
        print("🔗 Fase 3: Mapeando dependências...")
        self._map_dependencies()
        
        # Fase 4: Health checks
        print("🏥 Fase 4: Executando health checks...")
        self._perform_health_checks()
        
        # Fase 5: Identificar componentes críticos
        print("⚡ Fase 5: Identificando componentes críticos...")
        self._identify_critical_components()
        
        # Fase 6: Gerar recomendações
        print("💡 Fase 6: Gerando recomendações...")
        self._generate_recommendations()
        
        # Criar inventário final
        inventory = self._create_inventory()
        
        print(f"✅ Escaneamento completo! {len(self.components)} componentes analisados")
        return inventory
    
    def _discover_python_files(self) -> List[Path]:
        """Descobre todos os arquivos Python no sistema"""
        python_files = []
        
        for root, dirs, files in os.walk(self.base_path):
            # Ignorar diretórios desnecessários
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            
            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    python_files.append(file_path)
        
        return python_files
    
    def _analyze_file(self, file_path: Path):
        """Analisa um arquivo Python"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse do AST
            tree = ast.parse(content)
            
            # Analisar cada nó do AST
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    self._analyze_class(node, file_path, content)
                elif isinstance(node, ast.FunctionDef):
                    self._analyze_function(node, file_path, content)
                elif isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                    self._analyze_import(node, file_path)
            
            # Analisar módulo como um todo
            self._analyze_module(file_path, content, tree)
            
        except Exception as e:
            self.errors.append(f"Erro ao analisar {file_path}: {str(e)}")
    
    def _analyze_class(self, node: ast.ClassDef, file_path: Path, content: str):
        """Analisa uma classe"""
        try:
            # Extrair métodos
            methods = []
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    methods.append(item.name)
            
            # Extrair atributos
            attributes = []
            for item in node.body:
                if isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name):
                            attributes.append(target.id)
            
            # Extrair docstring
            docstring = ast.get_docstring(node)
            
            # Extrair imports usados
            imports = self._extract_imports_from_content(content)
            
            component = ComponentInfo(
                name=node.name,
                type='class',
                file_path=str(file_path),
                line_number=node.lineno,
                dependencies=[],  # Será preenchido depois
                imports=imports,
                methods=methods,
                attributes=attributes,
                docstring=docstring,
                size_lines=len(content.split('\n')),
                health_status='unknown',
                health_details=[],
                last_checked=datetime.now().isoformat(),
                is_critical=False,
                fallback_available=False
            )
            
            self.components.append(component)
            
        except Exception as e:
            self.errors.append(f"Erro ao analisar classe {node.name} em {file_path}: {str(e)}")
    
    def _analyze_function(self, node: ast.FunctionDef, file_path: Path, content: str):
        """Analisa uma função"""
        try:
            # Extrair argumentos
            args = [arg.arg for arg in node.args.args]
            
            # Extrair docstring
            docstring = ast.get_docstring(node)
            
            # Extrair imports usados
            imports = self._extract_imports_from_content(content)
            
            component = ComponentInfo(
                name=node.name,
                type='function',
                file_path=str(file_path),
                line_number=node.lineno,
                dependencies=[],  # Será preenchido depois
                imports=imports,
                methods=[],
                attributes=args,
                docstring=docstring,
                size_lines=len(content.split('\n')),
                health_status='unknown',
                health_details=[],
                last_checked=datetime.now().isoformat(),
                is_critical=False,
                fallback_available=False
            )
            
            self.components.append(component)
            
        except Exception as e:
            self.errors.append(f"Erro ao analisar função {node.name} em {file_path}: {str(e)}")
    
    def _analyze_import(self, node, file_path: Path):
        """Analisa um import"""
        try:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    import_name = alias.name
                    # Adicionar ao grafo de dependências
                    file_key = str(file_path.relative_to(self.base_path))
                    if file_key not in self.dependency_graph:
                        self.dependency_graph[file_key] = []
                    self.dependency_graph[file_key].append(import_name)
            
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module_name = node.module
                    file_key = str(file_path.relative_to(self.base_path))
                    if file_key not in self.dependency_graph:
                        self.dependency_graph[file_key] = []
                    self.dependency_graph[file_key].append(module_name)
        
        except Exception as e:
            self.errors.append(f"Erro ao analisar import em {file_path}: {str(e)}")
    
    def _analyze_module(self, file_path: Path, content: str, tree: ast.AST):
        """Analisa um módulo completo"""
        try:
            # Extrair docstring do módulo
            docstring = ast.get_docstring(tree)
            
            # Extrair imports
            imports = self._extract_imports_from_content(content)
            
            # Contar componentes
            classes = len([n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)])
            functions = len([n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)])
            
            module_name = file_path.stem
            
            component = ComponentInfo(
                name=module_name,
                type='module',
                file_path=str(file_path),
                line_number=1,
                dependencies=[],
                imports=imports,
                methods=[],
                attributes=[f"{classes} classes", f"{functions} functions"],
                docstring=docstring,
                size_lines=len(content.split('\n')),
                health_status='unknown',
                health_details=[],
                last_checked=datetime.now().isoformat(),
                is_critical=any(critical in str(file_path) for critical in self.known_critical),
                fallback_available=False
            )
            
            self.components.append(component)
            
        except Exception as e:
            self.errors.append(f"Erro ao analisar módulo {file_path}: {str(e)}")
    
    def _extract_imports_from_content(self, content: str) -> List[str]:
        """Extrai imports do conteúdo"""
        imports = []
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
        except:
            pass
        return imports
    
    def _map_dependencies(self):
        """Mapeia dependências entre componentes"""
        print("   🔗 Mapeando dependências...")
        
        # Criar mapa de nome -> componente
        component_map = {}
        for comp in self.components:
            component_map[comp.name] = comp
        
        # Mapear dependências
        for comp in self.components:
            deps = []
            for import_name in comp.imports:
                # Verificar se é dependência interna
                if import_name.startswith('app.claude_ai_novo'):
                    deps.append(import_name)
                # Verificar se é componente conhecido
                elif import_name in component_map:
                    deps.append(import_name)
            
            comp.dependencies = deps
    
    def _perform_health_checks(self):
        """Executa health checks em cada componente"""
        print("   🏥 Executando health checks...")
        
        for comp in self.components:
            try:
                health_details = []
                status = 'healthy'
                
                # Check 1: Arquivo existe?
                if not Path(comp.file_path).exists():
                    status = 'error'
                    health_details.append("Arquivo não encontrado")
                
                # Check 2: Pode ser importado?
                if comp.type == 'module':
                    try:
                        # Tentar importar dinamicamente
                        module_path = comp.file_path.replace('/', '.').replace('.py', '')
                        if module_path.startswith('app.'):
                            importlib.import_module(module_path)
                        health_details.append("Importação ok")
                    except Exception as e:
                        status = 'warning'
                        health_details.append(f"Importação falhou: {str(e)[:100]}")
                
                # Check 3: Tamanho do arquivo
                if comp.size_lines > 1000:
                    status = 'warning' if status == 'healthy' else status
                    health_details.append(f"Arquivo grande: {comp.size_lines} linhas")
                
                # Check 4: Tem documentação?
                if not comp.docstring:
                    status = 'warning' if status == 'healthy' else status
                    health_details.append("Sem documentação")
                
                # Check 5: Dependências críticas
                critical_deps = [dep for dep in comp.dependencies if any(crit in dep for crit in self.known_critical)]
                if critical_deps:
                    comp.is_critical = True
                    health_details.append(f"Tem dependências críticas: {len(critical_deps)}")
                
                comp.health_status = status
                comp.health_details = health_details
                
            except Exception as e:
                comp.health_status = 'error'
                comp.health_details = [f"Erro no health check: {str(e)}"]
    
    def _identify_critical_components(self):
        """Identifica componentes críticos"""
        print("   ⚡ Identificando componentes críticos...")
        
        # Critérios para componentes críticos
        for comp in self.components:
            is_critical = False
            
            # Critério 1: Está em pasta crítica
            if any(critical in comp.file_path for critical in self.known_critical):
                is_critical = True
            
            # Critério 2: Muitas dependências
            if len(comp.dependencies) > 5:
                is_critical = True
            
            # Critério 3: Muitos outros dependem dele
            dependents = 0
            for other in self.components:
                if comp.name in other.dependencies:
                    dependents += 1
            
            if dependents > 3:
                is_critical = True
            
            # Critério 4: Palavras-chave no nome
            critical_keywords = ['manager', 'orchestrator', 'integration', 'processor', 'main']
            if any(keyword in comp.name.lower() for keyword in critical_keywords):
                is_critical = True
            
            comp.is_critical = is_critical
            if is_critical:
                self.critical_components.add(comp.name)
    
    def _generate_recommendations(self):
        """Gera recomendações baseadas na análise"""
        print("   💡 Gerando recomendações...")
        
        # Análise de saúde
        error_count = len([c for c in self.components if c.health_status == 'error'])
        warning_count = len([c for c in self.components if c.health_status == 'warning'])
        
        if error_count > 0:
            self.recommendations.append(f"🔴 CRÍTICO: {error_count} componentes com erro precisam de correção imediata")
        
        if warning_count > 5:
            self.recommendations.append(f"🟡 ATENÇÃO: {warning_count} componentes com avisos - revisar prioridades")
        
        # Análise de documentação
        no_docs = len([c for c in self.components if not c.docstring])
        if no_docs > 10:
            self.recommendations.append(f"📝 DOCUMENTAÇÃO: {no_docs} componentes sem documentação")
        
        # Análise de arquivos grandes
        large_files = len([c for c in self.components if c.size_lines > 500])
        if large_files > 5:
            self.recommendations.append(f"📦 REFATORAÇÃO: {large_files} arquivos grandes (>500 linhas)")
        
        # Análise de dependências
        high_deps = len([c for c in self.components if len(c.dependencies) > 10])
        if high_deps > 0:
            self.recommendations.append(f"🔗 DEPENDÊNCIAS: {high_deps} componentes com muitas dependências")
        
        # Análise de componentes críticos
        if len(self.critical_components) > 20:
            self.recommendations.append(f"⚡ CRÍTICOS: {len(self.critical_components)} componentes críticos - considerar fallbacks")
    
    def _create_inventory(self) -> SystemInventory:
        """Cria o inventário final"""
        
        # Contadores
        total_files = len(set(c.file_path for c in self.components))
        total_modules = len([c for c in self.components if c.type == 'module'])
        total_classes = len([c for c in self.components if c.type == 'class'])
        total_functions = len([c for c in self.components if c.type == 'function'])
        
        # Resumo de saúde
        health_summary = {
            'healthy': len([c for c in self.components if c.health_status == 'healthy']),
            'warning': len([c for c in self.components if c.health_status == 'warning']),
            'error': len([c for c in self.components if c.health_status == 'error']),
            'unknown': len([c for c in self.components if c.health_status == 'unknown'])
        }
        
        return SystemInventory(
            scan_timestamp=datetime.now().isoformat(),
            total_files=total_files,
            total_modules=total_modules,
            total_classes=total_classes,
            total_functions=total_functions,
            components=self.components,
            dependency_graph=self.dependency_graph,
            critical_components=list(self.critical_components),
            health_summary=health_summary,
            recommendations=self.recommendations,
            warnings=self.warnings,
            errors=self.errors
        )
    
    def save_inventory(self, inventory: SystemInventory, filename: Optional[str] = None):
        """Salva o inventário em arquivo"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"system_inventory_{timestamp}.json"
        
        # Converter para dict
        inventory_dict = asdict(inventory)
        
        # Salvar
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(inventory_dict, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Inventário salvo em: {filename}")
        return filename
    
    def print_summary(self, inventory: SystemInventory):
        """Imprime resumo do inventário"""
        print("\n" + "="*80)
        print("📊 RESUMO DO INVENTÁRIO DO SISTEMA")
        print("="*80)
        
        print(f"🕒 Timestamp: {inventory.scan_timestamp}")
        print(f"📁 Total de arquivos: {inventory.total_files}")
        print(f"📦 Total de módulos: {inventory.total_modules}")
        print(f"🏛️ Total de classes: {inventory.total_classes}")
        print(f"⚡ Total de funções: {inventory.total_functions}")
        print(f"💎 Componentes críticos: {len(inventory.critical_components)}")
        
        print("\n🏥 SAÚDE DO SISTEMA:")
        print(f"  ✅ Saudáveis: {inventory.health_summary['healthy']}")
        print(f"  ⚠️ Avisos: {inventory.health_summary['warning']}")
        print(f"  ❌ Erros: {inventory.health_summary['error']}")
        print(f"  ❓ Desconhecidos: {inventory.health_summary['unknown']}")
        
        total_components = sum(inventory.health_summary.values())
        if total_components > 0:
            health_percentage = (inventory.health_summary['healthy'] / total_components) * 100
            print(f"  📊 Taxa de saúde: {health_percentage:.1f}%")
        else:
            print(f"  📊 Taxa de saúde: 0.0% (nenhum componente encontrado)")
        
        if inventory.recommendations:
            print("\n💡 RECOMENDAÇÕES PRINCIPAIS:")
            for rec in inventory.recommendations[:5]:
                print(f"  • {rec}")
        
        if inventory.errors:
            print("\n❌ ERROS ENCONTRADOS:")
            for error in inventory.errors[:5]:
                print(f"  • {error}")
        
        print("\n" + "="*80)

def main():
    """Função principal"""
    print("🔍 INVENTORY SCANNER COMPLETO")
    print("="*50)
    
    # Criar scanner
    scanner = InventoryScanner()
    
    # Executar escaneamento
    inventory = scanner.scan_complete_system()
    
    # Salvar inventário
    filename = scanner.save_inventory(inventory)
    
    # Mostrar resumo
    scanner.print_summary(inventory)
    
    print(f"\n✅ Escaneamento completo! Arquivo salvo: {filename}")
    print("🚀 Use este inventário para implementar testes e monitoramento")
    
    return inventory

if __name__ == "__main__":
    inventory = main() 