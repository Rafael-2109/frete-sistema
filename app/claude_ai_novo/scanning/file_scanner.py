"""
📁 FILE SCANNER - Manipulação de Arquivos
=========================================

Especialista em descoberta de templates,
manipulação de arquivos e busca em código.

Responsabilidades:
- Descoberta de templates HTML
- Leitura de arquivos
- Busca em código
- Listagem de diretórios
"""

import os
import re
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class FileScanner:
    """
    Especialista em manipulação de arquivos e templates.
    
    Descobre templates, lê arquivos e executa
    buscas avançadas no código do projeto.
    """
    
    def __init__(self, app_path: Path):
        """
        Inicializa o scanner de arquivos.
        
        Args:
            app_path: Caminho raiz do projeto
        """
        self.app_path = app_path
        logger.info("📁 FileScanner inicializado")
    
    def discover_all_templates(self) -> Dict[str, Any]:
        """
        Descobre todos os templates HTML do projeto.
        
        Returns:
            Dict com templates descobertos
        """
        templates = {}
        
        try:
            templates_dir = self.app_path / 'templates'
            if templates_dir.exists():
                for root, dirs, files in os.walk(templates_dir):
                    for file in files:
                        if file.endswith('.html'):
                            file_path = Path(root) / file
                            rel_path = file_path.relative_to(templates_dir)
                            
                            templates[str(rel_path)] = {
                                'full_path': str(file_path),
                                'size_kb': round(file_path.stat().st_size / 1024, 2),
                                'module': rel_path.parts[0] if len(rel_path.parts) > 1 else 'root',
                                'template_vars': self._extract_template_variables(file_path),
                                'extends': self._extract_template_extends(file_path),
                                'blocks': self._extract_template_blocks(file_path),
                                'includes': self._extract_template_includes(file_path)
                            }
            
            logger.info(f"🎨 Templates descobertos: {len(templates)}")
            return templates
            
        except Exception as e:
            logger.error(f"❌ Erro ao descobrir templates: {e}")
            return {}
    
    def _extract_template_variables(self, template_file: Path) -> List[str]:
        """
        Extrai variáveis de um template HTML.
        
        Args:
            template_file: Caminho para o template
            
        Returns:
            Lista de variáveis encontradas
        """
        variables = set()
        
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Variáveis {{ variable }}
            var_pattern = r'\{\{\s*([^}]+)\s*\}\}'
            matches = re.findall(var_pattern, content)
            for match in matches:
                # Extrair apenas o nome da variável (antes do primeiro . ou |)
                var_name = match.split('.')[0].split('|')[0].strip()
                if var_name and not var_name.startswith('"') and not var_name.startswith("'"):
                    variables.add(var_name)
            
            # Tags {% for x in y %}
            for_pattern = r'\{\%\s*for\s+\w+\s+in\s+([^%]+)\s*\%\}'
            matches = re.findall(for_pattern, content)
            for match in matches:
                var_name = match.strip()
                if var_name:
                    variables.add(var_name)
            
            # Tags {% if x %}
            if_pattern = r'\{\%\s*if\s+([^%]+)\s*\%\}'
            matches = re.findall(if_pattern, content)
            for match in matches:
                var_name = match.split()[0].strip()
                if var_name and not var_name.startswith('"'):
                    variables.add(var_name)
            
            return sorted(list(variables))[:20]  # Limitar a 20 variáveis
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao extrair variáveis de {template_file}: {e}")
            return []
    
    def _extract_template_extends(self, template_file: Path) -> Optional[str]:
        """Extrai template base que este template estende"""
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # {% extends "base.html" %}
            extends_pattern = r'\{\%\s*extends\s+["\']([^"\']+)["\']\s*\%\}'
            match = re.search(extends_pattern, content)
            return match.group(1) if match else None
            
        except Exception as e:
            logger.debug(f"Erro ao extrair extends: {e}")
            return None
    
    def _extract_template_blocks(self, template_file: Path) -> List[str]:
        """Extrai blocos definidos no template"""
        blocks = []
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # {% block name %}
            block_pattern = r'\{\%\s*block\s+([^%]+)\s*\%\}'
            matches = re.findall(block_pattern, content)
            for match in matches:
                block_name = match.strip()
                if block_name:
                    blocks.append(block_name)
            
        except Exception as e:
            logger.debug(f"Erro ao extrair blocks: {e}")
        
        return blocks
    
    def _extract_template_includes(self, template_file: Path) -> List[str]:
        """Extrai templates incluídos"""
        includes = []
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # {% include "template.html" %}
            include_pattern = r'\{\%\s*include\s+["\']([^"\']+)["\']\s*\%\}'
            matches = re.findall(include_pattern, content)
            includes.extend(matches)
            
        except Exception as e:
            logger.debug(f"Erro ao extrair includes: {e}")
        
        return includes
    
    def read_file_content(self, file_path: str, encoding: str = 'utf-8') -> str:
        """
        Lê conteúdo de qualquer arquivo do projeto.
        
        Args:
            file_path: Caminho relativo ou absoluto do arquivo
            encoding: Codificação do arquivo
            
        Returns:
            Conteúdo do arquivo ou mensagem de erro
        """
        try:
            full_path = self.app_path / file_path if not os.path.isabs(file_path) else Path(file_path)
            
            # Verificar se arquivo existe
            if not full_path.exists():
                return f"❌ Arquivo não encontrado: {file_path}"
            
            # Verificar se está dentro do projeto (segurança)
            if not str(full_path).startswith(str(self.app_path)):
                return f"🔒 Acesso negado: arquivo fora do projeto"
            
            # Verificar tamanho do arquivo (máx 1MB)
            file_size = full_path.stat().st_size
            if file_size > 1024 * 1024:  # 1MB
                return f"⚠️ Arquivo muito grande ({file_size // 1024}KB). Use busca específica."
            
            with open(full_path, 'r', encoding=encoding) as f:
                content = f.read()
            
            logger.info(f"📖 Lido arquivo: {file_path} ({len(content)} chars)")
            return content
            
        except UnicodeDecodeError:
            return f"❌ Erro de codificação: arquivo pode ser binário ou usar codificação diferente"
        except Exception as e:
            logger.error(f"❌ Erro ao ler {file_path}: {e}")
            return f"❌ Erro ao ler arquivo: {e}"
    
    def list_directory_contents(self, dir_path: str = '') -> Dict[str, Any]:
        """
        Lista conteúdo de qualquer diretório do projeto.
        
        Args:
            dir_path: Caminho relativo do diretório
            
        Returns:
            Dict com conteúdo do diretório
        """
        try:
            target_dir = self.app_path / dir_path if dir_path else self.app_path
            
            if not target_dir.exists() or not target_dir.is_dir():
                return {'error': f"Diretório não encontrado: {dir_path}"}
            
            contents = {
                'path': str(target_dir.relative_to(self.app_path)),
                'directories': [],
                'files': [],
                'summary': {}
            }
            
            file_types = {}
            total_size = 0
            
            for item in target_dir.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    contents['directories'].append({
                        'name': item.name,
                        'items_count': len(list(item.iterdir())) if item.is_dir() else 0
                    })
                elif item.is_file():
                    file_size = item.stat().st_size
                    total_size += file_size
                    
                    file_info = {
                        'name': item.name,
                        'size_kb': round(file_size / 1024, 2),
                        'extension': item.suffix,
                        'modified': item.stat().st_mtime
                    }
                    
                    contents['files'].append(file_info)
                    
                    # Contar tipos de arquivo
                    ext = item.suffix or 'no_extension'
                    file_types[ext] = file_types.get(ext, 0) + 1
            
            # Adicionar resumo
            contents['summary'] = {
                'total_directories': len(contents['directories']),
                'total_files': len(contents['files']),
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'file_types': file_types
            }
            
            return contents
            
        except Exception as e:
            logger.error(f"❌ Erro ao listar diretório {dir_path}: {e}")
            return {'error': str(e)}
    
    def search_in_files(self, pattern: str, file_extensions: Optional[List[str]] = None, 
                       max_results: int = 100) -> Dict[str, Any]:
        """
        Busca por padrão em arquivos do projeto.
        
        Args:
            pattern: Padrão de busca (regex)
            file_extensions: Lista de extensões para buscar
            max_results: Máximo de resultados
            
        Returns:
            Dict com resultados da busca
        """
        try:
            if file_extensions is None:
                file_extensions = ['.py', '.html', '.js', '.css', '.json', '.md']
            
            results = []
            files_searched = 0
            
            # Buscar recursivamente
            for root, dirs, files in os.walk(self.app_path):
                # Ignorar diretórios desnecessários
                dirs[:] = [d for d in dirs if not d.startswith(('.', '__pycache__', 'node_modules', 'venv', 'env'))]
                
                for file in files:
                    # Verificar extensão
                    if not any(file.endswith(ext) for ext in file_extensions):
                        continue
                    
                    file_path = Path(root) / file
                    files_searched += 1
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            for line_num, line in enumerate(f, 1):
                                if re.search(pattern, line, re.IGNORECASE):
                                    results.append({
                                        'file': str(file_path.relative_to(self.app_path)),
                                        'line_number': line_num,
                                        'line_content': line.strip()[:200],  # Limitar tamanho
                                        'match_context': self._extract_match_context(line, pattern)
                                    })
                                    
                                    if len(results) >= max_results:
                                        return self._format_search_results(
                                            results, files_searched, pattern, True
                                        )
                    except Exception:
                        # Ignorar arquivos que não podem ser lidos
                        continue
            
            logger.info(f"🔍 Busca '{pattern}': {len(results)} resultados em {files_searched} arquivos")
            
            return self._format_search_results(results, files_searched, pattern, False)
            
        except Exception as e:
            logger.error(f"❌ Erro na busca: {e}")
            return {'success': False, 'error': str(e)}
    
    def _extract_match_context(self, line: str, pattern: str) -> str:
        """Extrai contexto ao redor do match"""
        try:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                start = max(0, match.start() - 20)
                end = min(len(line), match.end() + 20)
                return line[start:end]
        except:
            pass
        return line[:50]
    
    def _format_search_results(self, results: List[Dict], files_searched: int, 
                              pattern: str, truncated: bool) -> Dict[str, Any]:
        """Formata resultados da busca"""
        return {
            'success': True,
            'pattern': pattern,
            'results': results,
            'summary': {
                'total_matches': len(results),
                'files_searched': files_searched,
                'truncated': truncated,
                'unique_files': len(set(r['file'] for r in results))
            }
        }


# Singleton para uso global
_file_scanner = None

def get_file_scanner(app_path: Optional[Path] = None) -> FileScanner:
    """
    Obtém instância do scanner de arquivos.
    
    Args:
        app_path: Caminho do projeto
        
    Returns:
        Instância do FileScanner
    """
    global _file_scanner
    if _file_scanner is None or app_path:
        if app_path is None:
            app_path = Path(__file__).parent.parent
        _file_scanner = FileScanner(app_path)
    return _file_scanner 