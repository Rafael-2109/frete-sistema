#!/usr/bin/env python3
"""
🔍 MAPEADOR DE CLASSES DUPLICADAS - CLAUDE AI NOVO
Identifica classes com mesmo nome em arquivos diferentes
"""

import os
import ast
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from datetime import datetime
from collections import defaultdict

class ClassDuplicateFinder:
    """Encontra e analisa classes duplicadas no sistema."""
    
    def __init__(self, root_path: str = "."):
        self.root_path = Path(root_path)
        self.classes_map = defaultdict(list)  # nome_classe: [(arquivo, linha, docstring)]
        self.duplicates = {}
        self.stats = {
            'total_files': 0,
            'total_classes': 0,
            'unique_classes': 0,
            'duplicate_classes': 0,
            'files_with_duplicates': set()
        }
        
    def scan_directory(self, directory: Optional[Path] = None) -> None:
        """Escaneia diretório em busca de definições de classes."""
        if directory is None:
            directory = self.root_path
            
        for py_file in directory.rglob("*.py"):
            # Pular arquivos de teste e __pycache__
            if "__pycache__" in str(py_file) or "test_" in py_file.name:
                continue
                
            self.scan_file(py_file)
            
    def scan_file(self, filepath: Path) -> None:
        """Escaneia um arquivo Python em busca de classes."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                
            tree = ast.parse(content)
            self.stats['total_files'] += 1
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_info = self.extract_class_info(node, filepath, content)
                    self.classes_map[node.name].append(class_info)
                    self.stats['total_classes'] += 1
                    
        except Exception as e:
            print(f"⚠️ Erro ao processar {filepath}: {e}")
            
    def extract_class_info(self, node: ast.ClassDef, filepath: Path, content: str) -> Dict:
        """Extrai informações detalhadas de uma classe."""
        # Pegar docstring
        docstring = ast.get_docstring(node) or ""
        
        # Pegar herança
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(f"{base.value.id}.{base.attr}" if isinstance(base.value, ast.Name) else base.attr)
                
        # Pegar métodos
        methods = []
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                methods.append(item.name)
                
        # Calcular tamanho aproximado
        lines = content.split('\n')
        class_size = 0
        if hasattr(node, 'end_lineno') and node.end_lineno is not None:
            class_size = node.end_lineno - node.lineno + 1
            
        return {
            'file': str(filepath.relative_to(self.root_path)),
            'line': node.lineno,
            'docstring': docstring[:100] + "..." if len(docstring) > 100 else docstring,
            'bases': bases,
            'methods': methods[:10],  # Primeiros 10 métodos
            'method_count': len(methods),
            'size_lines': class_size
        }
        
    def find_duplicates(self) -> None:
        """Identifica classes duplicadas."""
        for class_name, locations in self.classes_map.items():
            if len(locations) > 1:
                self.duplicates[class_name] = locations
                self.stats['duplicate_classes'] += 1
                
                # Adicionar arquivos com duplicatas
                for loc in locations:
                    self.stats['files_with_duplicates'].add(loc['file'])
                    
        self.stats['unique_classes'] = len(self.classes_map)
        
    def analyze_duplicates(self) -> Dict[str, Dict]:
        """Analisa as diferenças entre classes duplicadas."""
        analysis = {}
        
        for class_name, locations in self.duplicates.items():
            analysis[class_name] = {
                'count': len(locations),
                'locations': locations,
                'similarity': self.calculate_similarity(locations),
                'recommendation': self.get_recommendation(class_name, locations)
            }
            
        return analysis
        
    def calculate_similarity(self, locations: List[Dict]) -> Dict:
        """Calcula similaridade entre implementações duplicadas."""
        if len(locations) < 2:
            return {'identical': True}
            
        # Comparar bases, métodos e tamanhos
        all_bases = [set(loc['bases']) for loc in locations]
        all_methods = [set(loc['methods']) for loc in locations]
        sizes = [loc['size_lines'] for loc in locations]
        
        # Verificar se são idênticas
        bases_identical = all(b == all_bases[0] for b in all_bases)
        methods_identical = all(m == all_methods[0] for m in all_methods)
        
        # Calcular overlap de métodos
        if len(all_methods) > 1:
            common_methods = set.intersection(*all_methods)
            all_methods_union = set.union(*all_methods)
            method_overlap = len(common_methods) / len(all_methods_union) if all_methods_union else 0
        else:
            method_overlap = 1.0
            
        return {
            'identical': bases_identical and methods_identical,
            'bases_identical': bases_identical,
            'methods_identical': methods_identical,
            'method_overlap': method_overlap,
            'size_variance': max(sizes) - min(sizes) if sizes else 0
        }
        
    def get_recommendation(self, class_name: str, locations: List[Dict]) -> str:
        """Gera recomendação para resolver duplicação."""
        similarity = self.calculate_similarity(locations)
        
        if similarity['identical']:
            return f"CONSOLIDAR: Classes idênticas. Manter apenas uma em local apropriado."
            
        elif similarity['method_overlap'] > 0.8:
            return f"REFATORAR: Alta similaridade ({similarity['method_overlap']:.0%}). Considerar herança ou composição."
            
        elif similarity['method_overlap'] < 0.3:
            return f"RENOMEAR: Baixa similaridade ({similarity['method_overlap']:.0%}). Provavelmente são classes diferentes."
            
        else:
            return f"ANALISAR: Similaridade média ({similarity['method_overlap']:.0%}). Revisar caso a caso."
            
    def generate_report(self) -> str:
        """Gera relatório detalhado em Markdown."""
        report = []
        report.append("# 📊 RELATÓRIO DE CLASSES DUPLICADAS - CLAUDE AI NOVO")
        report.append(f"\n**Data**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"**Diretório**: {self.root_path.absolute()}")
        
        # Estatísticas
        report.append("\n## 📈 ESTATÍSTICAS GERAIS")
        report.append(f"- **Arquivos analisados**: {self.stats['total_files']}")
        report.append(f"- **Total de classes**: {self.stats['total_classes']}")
        report.append(f"- **Classes únicas**: {self.stats['unique_classes']}")
        report.append(f"- **Classes duplicadas**: {self.stats['duplicate_classes']}")
        report.append(f"- **Arquivos com duplicatas**: {len(self.stats['files_with_duplicates'])}")
        
        if not self.duplicates:
            report.append("\n✅ **Nenhuma classe duplicada encontrada!**")
            return "\n".join(report)
            
        # Análise detalhada
        analysis = self.analyze_duplicates()
        
        report.append("\n## 🔍 CLASSES DUPLICADAS ENCONTRADAS")
        
        # Ordenar por número de duplicatas (mais críticas primeiro)
        sorted_duplicates = sorted(analysis.items(), key=lambda x: x[1]['count'], reverse=True)
        
        for class_name, info in sorted_duplicates:
            report.append(f"\n### 🔴 `{class_name}` ({info['count']} ocorrências)")
            report.append(f"\n**Recomendação**: {info['recommendation']}")
            
            # Similaridade
            sim = info['similarity']
            report.append(f"\n**Análise de Similaridade**:")
            report.append(f"- Herança idêntica: {'✅' if sim['bases_identical'] else '❌'}")
            report.append(f"- Métodos idênticos: {'✅' if sim['methods_identical'] else '❌'}")
            report.append(f"- Overlap de métodos: {sim['method_overlap']:.0%}")
            report.append(f"- Variação de tamanho: {sim['size_variance']} linhas")
            
            # Localizações
            report.append(f"\n**Localizações**:")
            for i, loc in enumerate(info['locations'], 1):
                report.append(f"\n{i}. **{loc['file']}** (linha {loc['line']})")
                report.append(f"   - Herança: {', '.join(loc['bases']) if loc['bases'] else 'Nenhuma'}")
                report.append(f"   - Métodos: {loc['method_count']} métodos")
                report.append(f"   - Tamanho: {loc['size_lines']} linhas")
                if loc['docstring']:
                    report.append(f"   - Docstring: `{loc['docstring']}`")
                    
        # Resumo por pasta
        report.append("\n## 📁 RESUMO POR PASTA")
        folder_stats = defaultdict(int)
        for class_name, locs in self.duplicates.items():
            for loc in locs:
                folder = os.path.dirname(loc['file'])
                folder_stats[folder or 'raiz'] += 1
                
        for folder, count in sorted(folder_stats.items(), key=lambda x: x[1], reverse=True):
            report.append(f"- `{folder}/`: {count} classes duplicadas")
            
        # Ações recomendadas
        report.append("\n## 🎯 AÇÕES RECOMENDADAS")
        report.append("\n1. **Revisar classes idênticas** - Consolidar em local apropriado")
        report.append("2. **Analisar alta similaridade** - Considerar herança ou traits")
        report.append("3. **Renomear baixa similaridade** - Classes diferentes com mesmo nome")
        report.append("4. **Atualizar imports** - Após consolidação/renomeação")
        report.append("5. **Documentar decisões** - Registrar motivos para manter duplicatas (se necessário)")
        
        return "\n".join(report)
        
    def save_results(self, output_dir: str = ".") -> None:
        """Salva resultados em arquivos."""
        # Salvar relatório Markdown
        report = self.generate_report()
        report_path = Path(output_dir) / "RELATORIO_CLASSES_DUPLICADAS.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
            
        # Salvar dados JSON para processamento
        data = {
            'timestamp': datetime.now().isoformat(),
            'stats': dict(self.stats),
            'duplicates': self.duplicates,
            'analysis': self.analyze_duplicates()
        }
        
        # Converter set para list no JSON
        data['stats']['files_with_duplicates'] = list(self.stats['files_with_duplicates'])
        
        json_path = Path(output_dir) / "classes_duplicadas.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        print(f"✅ Relatório salvo em: {report_path}")
        print(f"✅ Dados JSON salvos em: {json_path}")


def main():
    """Função principal."""
    print("🔍 MAPEADOR DE CLASSES DUPLICADAS - CLAUDE AI NOVO")
    print("=" * 80)
    
    # Configurar diretório
    root_dir = str(Path(__file__).parent)
    
    # Criar finder
    finder = ClassDuplicateFinder(root_dir)
    
    print(f"\n📂 Escaneando diretório: {finder.root_path.absolute()}")
    finder.scan_directory()
    
    print(f"\n📊 Encontradas {finder.stats['total_classes']} classes em {finder.stats['total_files']} arquivos")
    
    # Encontrar duplicatas
    finder.find_duplicates()
    
    if finder.duplicates:
        print(f"\n⚠️ Encontradas {len(finder.duplicates)} classes duplicadas!")
        
        # Mostrar preview
        print("\n🔍 Preview das duplicatas:")
        for class_name, locations in list(finder.duplicates.items())[:5]:
            print(f"\n- {class_name} ({len(locations)} ocorrências):")
            for loc in locations[:3]:
                print(f"  → {loc['file']}:{loc['line']}")
                
        if len(finder.duplicates) > 5:
            print(f"\n... e mais {len(finder.duplicates) - 5} classes duplicadas")
    else:
        print("\n✅ Nenhuma classe duplicada encontrada!")
        
    # Salvar resultados
    print("\n💾 Salvando resultados...")
    finder.save_results()
    
    print("\n✅ Análise concluída!")


if __name__ == "__main__":
    main() 