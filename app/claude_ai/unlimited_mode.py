"""
💪 MODO ILIMITADO DO CLAUDE AI
Funcionalidades sem limitações para máxima capacidade
"""

import os
import re
import ast
import json
from typing import Dict, List, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class UnlimitedClaudeMode:
    """Modo ilimitado com capacidades expandidas"""
    
    def __init__(self, app_path: Optional[str] = None):
        self.app_path = Path(app_path) if app_path else Path(__file__).parent.parent
        self.unlimited_active = True
        logger.info("💪 Modo Ilimitado ativado!")
    
    def read_entire_project(self) -> Dict[str, Any]:
        """Lê o projeto INTEIRO sem limitações"""
        project_data = {
            'files': {},
            'structure': {},
            'total_files': 0,
            'total_lines': 0,
            'total_size_mb': 0
        }
        
        try:
            for root, dirs, files in os.walk(self.app_path):
                # Não filtrar diretórios - ler TUDO
                for file in files:
                    if file.endswith(('.py', '.html', '.js', '.css', '.md', '.txt', '.json', '.yml', '.yaml')):
                        file_path = Path(root) / file
                        rel_path = file_path.relative_to(self.app_path)
                        
                        try:
                            content = file_path.read_text(encoding='utf-8')
                            project_data['files'][str(rel_path)] = {
                                'content': content,  # Conteúdo COMPLETO
                                'lines': len(content.split('\n')),
                                'size_kb': len(content) / 1024,
                                'type': file_path.suffix
                            }
                            
                            project_data['total_files'] += 1
                            project_data['total_lines'] += len(content.split('\n'))
                            project_data['total_size_mb'] += len(content) / (1024 * 1024)
                            
                        except Exception as e:
                            logger.warning(f"Erro ao ler {file_path}: {e}")
            
            logger.info(f"💪 Projeto COMPLETO lido: {project_data['total_files']} arquivos, "
                       f"{project_data['total_lines']} linhas, {project_data['total_size_mb']:.2f}MB")
            
            return project_data
            
        except Exception as e:
            logger.error(f"Erro na leitura ilimitada: {e}")
            return project_data
    
    def analyze_unlimited_patterns(self, project_data: Dict) -> Dict[str, Any]:
        """Analisa padrões sem limitação de complexidade"""
        patterns = {
            'code_patterns': [],
            'architectural_patterns': [],
            'data_flow_patterns': [],
            'security_patterns': [],
            'performance_patterns': []
        }
        
        try:
            for file_path, file_info in project_data['files'].items():
                if file_path.endswith('.py'):
                    content = file_info['content']
                    
                    # Análise AST completa
                    try:
                        tree = ast.parse(content)
                        
                        # Analisar TODOS os nós, não apenas alguns
                        for node in ast.walk(tree):
                            # Classes
                            if isinstance(node, ast.ClassDef):
                                patterns['architectural_patterns'].append({
                                    'type': 'class_definition',
                                    'name': node.name,
                                    'file': file_path,
                                    'methods': [n.name for n in node.body if isinstance(n, ast.FunctionDef)],
                                    'inheritance': [base.id for base in node.bases if hasattr(base, 'id')]
                                })
                            
                            # Funções
                            elif isinstance(node, ast.FunctionDef):
                                patterns['code_patterns'].append({
                                    'type': 'function_definition',
                                    'name': node.name,
                                    'file': file_path,
                                    'args': len(node.args.args),
                                    'decorators': [d.id for d in node.decorator_list if hasattr(d, 'id')]
                                })
                            
                            # Imports
                            elif isinstance(node, ast.Import):
                                for alias in node.names:
                                    patterns['data_flow_patterns'].append({
                                        'type': 'import',
                                        'module': alias.name,
                                        'file': file_path
                                    })
                    
                    except Exception as e:
                        logger.warning(f"Erro na análise AST de {file_path}: {e}")
            
            logger.info(f"💪 Análise ilimitada concluída: {len(patterns['code_patterns'])} padrões encontrados")
            return patterns
            
        except Exception as e:
            logger.error(f"Erro na análise ilimitada: {e}")
            return patterns
    
    def generate_unlimited_insights(self, patterns: Dict) -> List[str]:
        """Gera insights sem limitação de profundidade"""
        insights = []
        
        try:
            # Análise de arquitetura
            classes = [p for p in patterns['architectural_patterns'] if p['type'] == 'class_definition']
            functions = [p for p in patterns['code_patterns'] if p['type'] == 'function_definition']
            imports = [p for p in patterns['data_flow_patterns'] if p['type'] == 'import']
            
            # Insights arquiteturais
            if len(classes) > 50:
                insights.append(f"🏗️ Arquitetura robusta: {len(classes)} classes encontradas - sistema bem estruturado")
            
            if len(functions) > 200:
                insights.append(f"⚙️ Sistema complexo: {len(functions)} funções - alta funcionalidade")
            
            # Análise de padrões MVC
            mvc_files = [f for f in patterns['architectural_patterns'] if any(keyword in f.get('file', '') for keyword in ['models', 'views', 'controllers', 'routes'])]
            if mvc_files:
                insights.append(f"🎯 Padrão MVC detectado: {len(mvc_files)} componentes arquiteturais")
            
            # Análise de dependências
            unique_modules = set(p['module'] for p in imports)
            if len(unique_modules) > 20:
                insights.append(f"📦 Sistema rico em dependências: {len(unique_modules)} módulos únicos")
            
            # Análise de complexidade
            total_methods = sum(len(c.get('methods', [])) for c in classes)
            if total_methods > 100:
                insights.append(f"🧠 Alta complexidade: {total_methods} métodos distribuídos")
            
            logger.info(f"💪 Insights ilimitados gerados: {len(insights)} descobertas")
            return insights
            
        except Exception as e:
            logger.error(f"Erro na geração de insights: {e}")
            return insights
    
    def unlimited_code_analysis(self, file_content: str, file_path: str) -> Dict[str, Any]:
        """Análise de código sem limitações"""
        analysis = {
            'complexity_score': 0,
            'maintainability_score': 0,
            'security_issues': [],
            'performance_issues': [],
            'suggestions': [],
            'detailed_metrics': {}
        }
        
        try:
            lines = file_content.split('\n')
            
            # Métricas detalhadas
            analysis['detailed_metrics'] = {
                'total_lines': len(lines),
                'code_lines': len([l for l in lines if l.strip() and not l.strip().startswith('#')]),
                'comment_lines': len([l for l in lines if l.strip().startswith('#')]),
                'blank_lines': len([l for l in lines if not l.strip()]),
                'avg_line_length': sum(len(l) for l in lines) / len(lines) if lines else 0
            }
            
            # Análise de complexidade (sem limites)
            if file_path.endswith('.py'):
                try:
                    tree = ast.parse(file_content)
                    
                    complexity = 0
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                            complexity += 1
                        elif isinstance(node, ast.FunctionDef):
                            complexity += 2
                        elif isinstance(node, ast.ClassDef):
                            complexity += 3
                    
                    analysis['complexity_score'] = complexity
                    
                    # Score de manutenibilidade
                    analysis['maintainability_score'] = max(0, 100 - (complexity * 2))
                    
                except Exception as e:
                    logger.warning(f"Erro na análise AST: {e}")
            
            # Detecção de problemas de segurança (expandida)
            security_patterns = [
                ('eval(', 'Uso de eval() - risco de execução de código'),
                ('exec(', 'Uso de exec() - risco de execução de código'),
                ('subprocess.call', 'Chamada de subprocess - verificar entrada'),
                ('os.system', 'Uso de os.system - risco de injeção'),
                ('sql.*%', 'Possível SQL injection'),
                (r'password.*=.*["\']', 'Password hardcoded'),
                (r'api_key.*=.*["\']', 'API key hardcoded')
            ]
            
            for pattern, description in security_patterns:
                if re.search(pattern, file_content, re.IGNORECASE):
                    analysis['security_issues'].append(description)
            
            # Detecção de problemas de performance
            performance_patterns = [
                (r'for.*in.*query\.all\(\)', 'Query em loop - usar select_related'),
                (r'time\.sleep', 'Sleep em código - pode afetar performance'),
                (r'print\(', 'Print em código de produção'),
                (r'\.filter\(.*\)\.filter\(', 'Múltiplos filters - considerar combinar')
            ]
            
            for pattern, description in performance_patterns:
                if re.search(pattern, file_content, re.IGNORECASE):
                    analysis['performance_issues'].append(description)
            
            # Sugestões de melhoria (expandidas)
            if analysis['complexity_score'] > 50:
                analysis['suggestions'].append('Considere refatorar - complexidade alta')
            
            if analysis['detailed_metrics']['avg_line_length'] > 120:
                analysis['suggestions'].append('Linhas muito longas - considere quebrar')
            
            if analysis['detailed_metrics']['comment_lines'] < analysis['detailed_metrics']['code_lines'] * 0.1:
                analysis['suggestions'].append('Adicionar mais comentários - documentação baixa')
            
            logger.info(f"💪 Análise ilimitada de {file_path}: complexidade {analysis['complexity_score']}")
            return analysis
            
        except Exception as e:
            logger.error(f"Erro na análise ilimitada: {e}")
            return analysis

# Instância global
unlimited_mode = None

def get_unlimited_mode() -> UnlimitedClaudeMode:
    """Retorna instância do modo ilimitado"""
    global unlimited_mode
    if unlimited_mode is None:
        unlimited_mode = UnlimitedClaudeMode()
    return unlimited_mode

def activate_unlimited_mode() -> bool:
    """Ativa modo ilimitado"""
    try:
        mode = get_unlimited_mode()
        logger.info("💪 Modo Ilimitado ATIVADO - Capacidades expandidas!")
        return True
    except Exception as e:
        logger.error(f"Erro ao ativar modo ilimitado: {e}")
        return False
