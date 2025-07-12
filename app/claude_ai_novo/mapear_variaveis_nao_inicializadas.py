#!/usr/bin/env python3
"""
🔍 MAPEADOR DE VARIÁVEIS NÃO INICIALIZADAS - CLAUDE AI NOVO
Detecta variáveis que são usadas mas podem não estar inicializadas
"""

import os
import ast
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from datetime import datetime
from collections import defaultdict

class VariableTracker(ast.NodeVisitor):
    """Rastreia definições e usos de variáveis."""
    
    def __init__(self):
        self.defined_vars = set()  # Variáveis definidas
        self.used_vars = []  # [(linha, nome, contexto)]
        self.assignments = []  # [(linha, nome)]
        self.function_params = set()  # Parâmetros de função
        self.class_attributes = set()  # Atributos de classe
        self.imports = set()  # Nomes importados
        
    def visit_Import(self, node):
        """Rastreia imports."""
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.imports.add(name.split('.')[0])
        self.generic_visit(node)
        
    def visit_ImportFrom(self, node):
        """Rastreia from imports."""
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.imports.add(name)
        self.generic_visit(node)
        
    def visit_FunctionDef(self, node):
        """Rastreia definições de função e parâmetros."""
        # Adicionar parâmetros como definidos
        for arg in node.args.args:
            self.function_params.add(arg.arg)
            self.defined_vars.add(arg.arg)
        self.generic_visit(node)
        
    def visit_ClassDef(self, node):
        """Rastreia definições de classe."""
        self.defined_vars.add(node.name)
        # Visitar corpo da classe
        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        self.class_attributes.add(target.id)
        self.generic_visit(node)
        
    def visit_Assign(self, node):
        """Rastreia atribuições."""
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.defined_vars.add(target.id)
                self.assignments.append((node.lineno, target.id))
        self.generic_visit(node)
        
    def visit_Name(self, node):
        """Rastreia uso de variáveis."""
        if isinstance(node.ctx, ast.Load):
            # Variável sendo lida
            self.used_vars.append((node.lineno, node.id, 'load'))
        elif isinstance(node.ctx, ast.Store):
            # Variável sendo escrita
            self.defined_vars.add(node.id)
        self.generic_visit(node)


class UninitializedVariableFinder:
    """Encontra variáveis usadas mas não inicializadas."""
    
    def __init__(self, root_path: str = "."):
        self.root_path = Path(root_path)
        self.uninitialized_vars = defaultdict(list)
        self.stats = {
            'total_files': 0,
            'files_with_issues': 0,
            'total_variables_used': 0,
            'uninitialized_variables': 0,
            'suspicious_patterns': 0
        }
        
    def scan_directory(self, directory: Optional[Path] = None) -> None:
        """Escaneia diretório em busca de variáveis não inicializadas."""
        if directory is None:
            directory = self.root_path
            
        for py_file in directory.rglob("*.py"):
            # Pular arquivos de teste e __pycache__
            if "__pycache__" in str(py_file) or "test_" in py_file.name:
                continue
                
            self.scan_file(py_file)
            
    def scan_file(self, filepath: Path) -> None:
        """Escaneia um arquivo em busca de variáveis não inicializadas."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                
            tree = ast.parse(content)
            self.stats['total_files'] += 1
            
            # Rastrear variáveis
            tracker = VariableTracker()
            tracker.visit(tree)
            
            # Analisar usos suspeitos
            file_has_issues = False
            
            for line, var_name, context in tracker.used_vars:
                self.stats['total_variables_used'] += 1
                
                if self._is_suspicious_usage(var_name, line, tracker, content):
                    self.uninitialized_vars[str(filepath)].append({
                        'line': line,
                        'variable': var_name,
                        'context': context,
                        'code': self._get_line_context(content, line),
                        'pattern': self._identify_pattern(var_name, content)
                    })
                    self.stats['uninitialized_variables'] += 1
                    file_has_issues = True
                    
            if file_has_issues:
                self.stats['files_with_issues'] += 1
                
        except Exception as e:
            print(f"⚠️ Erro ao processar {filepath}: {e}")
            
    def _is_suspicious_usage(self, var_name: str, line: int, tracker: VariableTracker, content: str) -> bool:
        """Verifica se um uso de variável é suspeito."""
        # Ignorar built-ins e imports
        if var_name in __builtins__ or var_name in tracker.imports:
            return False
            
        # Ignorar self, cls
        if var_name in ['self', 'cls', 'True', 'False', 'None']:
            return False
            
        # Verificar padrões suspeitos específicos
        suspicious_patterns = [
            'get_semantic_mapper()',  # Variável mencionada que parece não existir
            'readers',  # Pode não estar inicializada
            'readme_reader',
            'database_reader',
        ]
        
        if var_name in suspicious_patterns:
            # Verificar se foi definida antes do uso
            defined_before = False
            for assign_line, assign_var in tracker.assignments:
                if assign_var == var_name and assign_line < line:
                    defined_before = True
                    break
                    
            if not defined_before:
                self.stats['suspicious_patterns'] += 1
                return True
                
        # Verificar se a variável nunca foi definida
        if var_name not in tracker.defined_vars:
            return True
            
        return False
        
    def _identify_pattern(self, var_name: str, content: str) -> str:
        """Identifica o padrão de uso da variável."""
        if 'get_semantic_mapper()' in var_name:
            return "get_semantic_mapper() não definido"
        elif var_name in ['readers', 'readme_reader', 'database_reader']:
            return "reader possivelmente não inicializado"
        elif var_name.startswith('_'):
            return "variável privada"
        else:
            return "variável não definida"
            
    def _get_line_context(self, content: str, line_num: int) -> str:
        """Obtém contexto da linha com erro."""
        lines = content.split('\n')
        if 0 <= line_num - 1 < len(lines):
            return lines[line_num - 1].strip()
        return ""
        
    def generate_report(self) -> str:
        """Gera relatório detalhado em Markdown."""
        report = []
        report.append("# 🔍 RELATÓRIO DE VARIÁVEIS NÃO INICIALIZADAS")
        report.append(f"\n**Data**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"**Diretório**: {self.root_path.absolute()}")
        
        # Estatísticas
        report.append("\n## 📈 ESTATÍSTICAS GERAIS")
        report.append(f"- **Arquivos analisados**: {self.stats['total_files']}")
        report.append(f"- **Arquivos com problemas**: {self.stats['files_with_issues']}")
        report.append(f"- **Total variáveis usadas**: {self.stats['total_variables_used']}")
        report.append(f"- **Variáveis suspeitas**: {self.stats['uninitialized_variables']}")
        report.append(f"- **Padrões conhecidos**: {self.stats['suspicious_patterns']}")
        
        if not self.uninitialized_vars:
            report.append("\n✅ **Nenhuma variável suspeita encontrada!**")
            return "\n".join(report)
            
        # Problemas encontrados
        report.append("\n## 🔍 VARIÁVEIS SUSPEITAS ENCONTRADAS")
        
        # Agrupar por variável
        by_variable = defaultdict(list)
        for filepath, issues in self.uninitialized_vars.items():
            for issue in issues:
                by_variable[issue['variable']].append((filepath, issue))
                
        # Ordenar por frequência
        sorted_vars = sorted(by_variable.items(), key=lambda x: len(x[1]), reverse=True)
        
        for var_name, locations in sorted_vars:
            report.append(f"\n### 🔴 `{var_name}` ({len(locations)} ocorrências)")
            
            # Padrão identificado
            first_issue = locations[0][1]
            pattern = first_issue['pattern']
            report.append(f"\n**Padrão**: {pattern}")
            
            # Localizações
            report.append("\n**Localizações**:")
            for filepath, issue in locations[:5]:  # Mostrar até 5
                rel_path = Path(filepath).relative_to(self.root_path)
                report.append(f"\n- **{rel_path}** (linha {issue['line']})")
                report.append(f"  ```python")
                report.append(f"  {issue['code']}")
                report.append(f"  ```")
                
            if len(locations) > 5:
                report.append(f"\n... e mais {len(locations) - 5} ocorrências")
                
        # Padrões por tipo
        report.append("\n## 📊 ANÁLISE POR PADRÃO")
        
        pattern_count = defaultdict(int)
        for _, issues in self.uninitialized_vars.items():
            for issue in issues:
                pattern_count[issue['pattern']] += 1
                
        for pattern, count in sorted(pattern_count.items(), key=lambda x: x[1], reverse=True):
            report.append(f"- **{pattern}**: {count} ocorrências")
            
        # Recomendações
        report.append("\n## 🎯 RECOMENDAÇÕES")
        report.append("\n1. **Inicializar variáveis** - Sempre inicializar antes de usar")
        report.append("2. **Verificar existência** - Use `if var_name:` ou `hasattr()`")
        report.append("3. **Try/except blocks** - Capturar NameError quando apropriado")
        report.append("4. **Valores padrão** - Use `var = getattr(obj, 'attr', default)`")
        report.append("5. **Type hints** - Ajudam a detectar problemas em tempo de desenvolvimento")
        
        # Exemplos de correção
        report.append("\n## 💡 EXEMPLOS DE CORREÇÃO")
        report.append("\n### Antes:")
        report.append("```python")
        report.append("readers = self.orchestrator.obter_readers()  # Método não existe")
        report.append("```")
        report.append("\n### Depois:")
        report.append("```python")
        report.append("# Opção 1: Verificar se método existe")
        report.append("if hasattr(self.orchestrator, 'obter_readers'):")
        report.append("    readers = self.orchestrator.obter_readers()")
        report.append("else:")
        report.append("    readers = {}")
        report.append("")
        report.append("# Opção 2: Try/except")
        report.append("try:")
        report.append("    readers = self.orchestrator.obter_readers()")
        report.append("except AttributeError:")
        report.append("    readers = {}")
        report.append("```")
        
        return "\n".join(report)
        
    def save_results(self, output_dir: str = ".") -> None:
        """Salva resultados em arquivos."""
        # Salvar relatório Markdown
        report = self.generate_report()
        report_path = Path(output_dir) / "RELATORIO_VARIAVEIS_NAO_INICIALIZADAS.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
            
        # Salvar dados JSON
        data = {
            'timestamp': datetime.now().isoformat(),
            'stats': self.stats,
            'uninitialized_vars': dict(self.uninitialized_vars)
        }
        
        json_path = Path(output_dir) / "variaveis_nao_inicializadas.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        print(f"✅ Relatório salvo em: {report_path}")
        print(f"✅ Dados JSON salvos em: {json_path}")


def main():
    """Função principal."""
    print("🔍 MAPEADOR DE VARIÁVEIS NÃO INICIALIZADAS")
    print("=" * 80)
    
    # Configurar diretório
    root_dir = str(Path(__file__).parent)
    
    # Criar finder
    finder = UninitializedVariableFinder(root_dir)
    
    print(f"\n📂 Escaneando diretório: {finder.root_path.absolute()}")
    finder.scan_directory()
    
    print(f"\n📊 Analisados {finder.stats['total_files']} arquivos")
    print(f"📊 Total de variáveis usadas: {finder.stats['total_variables_used']}")
    print(f"📊 Variáveis suspeitas: {finder.stats['uninitialized_variables']}")
    print(f"📊 Padrões conhecidos: {finder.stats['suspicious_patterns']}")
    
    if finder.uninitialized_vars:
        print(f"\n⚠️ Problemas encontrados em {finder.stats['files_with_issues']} arquivos!")
    else:
        print("\n✅ Nenhuma variável suspeita encontrada!")
        
    # Salvar resultados
    print("\n💾 Salvando resultados...")
    finder.save_results()
    
    print("\n✅ Análise concluída!")


if __name__ == "__main__":
    main() 