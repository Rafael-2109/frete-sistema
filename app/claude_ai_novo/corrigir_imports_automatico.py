#!/usr/bin/env python3
"""
Corretor Automático de Imports - Claude AI Novo
Corrige automaticamente os imports quebrados identificados
"""

import os
import sys
import json
import re
from datetime import datetime
from typing import Dict, List, Tuple

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Mapeamento de correções conhecidas
IMPORT_FIXES = {
    # Flask-SQLAlchemy
    "from flask_sqlalchemy import db": "from app import db",
    
    # Funções get_* que precisam ser criadas ou corrigidas
    "from app.claude_ai_novo.analyzers.analyzer_manager import get_analyzer_manager": 
        "from app.claude_ai_novo.analyzers.analyzer_manager import AnalyzerManager",
    
    "from app.claude_ai_novo.processors import get_processormanager":
        "from app.claude_ai_novo.processors.processor_manager import ProcessorManager",
    
    "from app.claude_transition import get_claude_transition":
        "from app.claude_transition import ClaudeTransitionManager",
    
    # Módulos que não existem - comentar ou remover
    "from app.claude_ai_novo.orchestrators.get_semantic_mapper() import SemanticManager":
        "# from app.claude_ai_novo.orchestrators.get_semantic_mapper() import SemanticManager  # TODO: Módulo não existe",
    
    "from app.claude_ai_novo.integration.claude import get_claude_integration":
        "# from app.claude_ai_novo.integration.claude import get_claude_integration  # TODO: Módulo não existe",
    
    # Atributos que não existem
    "from app.cotacao.models import CotacaoFrete":
        "from app.cotacao.models import Cotacao  # TODO: Verificar se CotacaoFrete foi renomeado",
    
    "from app.claude_ai_novo.providers.data_provider import SistemaRealData as RealSistemaRealData":
        "from app.claude_ai_novo.providers.data_provider import DataProvider  # TODO: SistemaRealData não existe"
}

class ImportFixer:
    """Corrige imports quebrados automaticamente"""
    
    def __init__(self, error_file: str = None):
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        self.error_file = error_file or self._find_latest_error_file()
        self.fixes_applied = []
        self.backups_created = []
        
    def _find_latest_error_file(self) -> str:
        """Encontra o arquivo de erros mais recente"""
        files = [f for f in os.listdir(self.base_path) if f.startswith('import_errors_') and f.endswith('.json')]
        if not files:
            raise FileNotFoundError("Nenhum arquivo de erros encontrado. Execute verificar_imports_quebrados.py primeiro.")
        
        # Pegar o mais recente
        files.sort(reverse=True)
        return os.path.join(self.base_path, files[0])
    
    def load_errors(self) -> Dict:
        """Carrega erros do arquivo JSON"""
        with open(self.error_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def fix_imports(self):
        """Corrige todos os imports quebrados"""
        print("🔧 CORRETOR AUTOMÁTICO DE IMPORTS")
        print("=" * 80)
        
        # Carregar erros
        data = self.load_errors()
        errors = data.get('errors', [])
        
        if not errors:
            print("✅ Nenhum erro para corrigir!")
            return
        
        print(f"\n📊 Encontrados {len(errors)} imports quebrados para corrigir")
        
        # Agrupar por arquivo
        by_file = {}
        for error in errors:
            file_path = os.path.join(self.base_path, error['file'])
            if file_path not in by_file:
                by_file[file_path] = []
            by_file[file_path].append(error)
        
        # Corrigir cada arquivo
        for file_path, file_errors in by_file.items():
            self._fix_file(file_path, file_errors)
        
        # Relatório final
        self._print_report()
    
    def _fix_file(self, file_path: str, errors: List[Dict]):
        """Corrige imports em um arquivo específico"""
        relative_path = os.path.relpath(file_path, self.base_path)
        print(f"\n📄 Corrigindo: {relative_path}")
        
        try:
            # Fazer backup
            backup_path = self._create_backup(file_path)
            self.backups_created.append((file_path, backup_path))
            
            # Ler arquivo
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Aplicar correções
            modified = False
            for error in errors:
                line_num = error['line'] - 1  # Converter para índice 0
                import_stmt = error['import']
                
                # Verificar se temos uma correção
                fix = self._find_fix(import_stmt)
                if fix:
                    if line_num < len(lines):
                        old_line = lines[line_num].rstrip()
                        new_line = lines[line_num].replace(import_stmt, fix)
                        
                        if old_line != new_line.rstrip():
                            lines[line_num] = new_line
                            print(f"   ✅ Linha {error['line']}: {import_stmt}")
                            print(f"      → {fix}")
                            self.fixes_applied.append({
                                'file': relative_path,
                                'line': error['line'],
                                'old': import_stmt,
                                'new': fix
                            })
                            modified = True
                else:
                    print(f"   ⚠️ Linha {error['line']}: {import_stmt}")
                    print(f"      Sem correção automática disponível")
            
            # Salvar arquivo se modificado
            if modified:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                print(f"   💾 Arquivo salvo com {len([e for e in errors if self._find_fix(e['import'])])} correções")
            
        except Exception as e:
            print(f"   ❌ Erro ao processar arquivo: {e}")
    
    def _find_fix(self, import_stmt: str) -> str:
        """Encontra correção para um import"""
        # Verificar correções exatas
        for pattern, fix in IMPORT_FIXES.items():
            if pattern in import_stmt:
                return import_stmt.replace(pattern, fix)
        
        # Correções baseadas em padrões
        # flask_sqlalchemy import db
        if "from flask_sqlalchemy import db" in import_stmt:
            return "from app import db"
        
        return None
    
    def _create_backup(self, file_path: str) -> str:
        """Cria backup do arquivo"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{file_path}.backup_{timestamp}"
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return backup_path
    
    def _print_report(self):
        """Imprime relatório das correções"""
        print("\n" + "=" * 80)
        print("📊 RELATÓRIO DE CORREÇÕES")
        print("=" * 80)
        
        if self.fixes_applied:
            print(f"\n✅ {len(self.fixes_applied)} correções aplicadas:")
            
            # Agrupar por tipo de correção
            by_type = {}
            for fix in self.fixes_applied:
                fix_type = fix['new'].split()[0]  # Primeira palavra da correção
                if fix_type not in by_type:
                    by_type[fix_type] = []
                by_type[fix_type].append(fix)
            
            for fix_type, fixes in by_type.items():
                print(f"\n{fix_type} ({len(fixes)} correções):")
                for fix in fixes[:3]:  # Mostrar até 3 exemplos
                    print(f"   {fix['file']} linha {fix['line']}")
                if len(fixes) > 3:
                    print(f"   ... e mais {len(fixes) - 3}")
        
        if self.backups_created:
            print(f"\n💾 {len(self.backups_created)} backups criados")
            print("   Para reverter, use os arquivos .backup_*")
    
    def create_fix_functions(self):
        """Cria funções get_* que estão faltando"""
        print("\n🔧 Criando funções get_* faltantes...")
        
        # analyzer_manager.py
        self._add_get_function(
            "analyzers/analyzer_manager.py",
            "get_analyzer_manager",
            """
def get_analyzer_manager(orchestrator=None):
    \"\"\"Retorna instância do AnalyzerManager\"\"\"
    return AnalyzerManager(orchestrator)
"""
        )
        
        # processor_manager.py
        self._add_get_function(
            "processors/processor_manager.py",
            "get_processormanager",
            """
def get_processormanager():
    \"\"\"Retorna instância do ProcessorManager\"\"\"
    return ProcessorManager()
"""
        )
    
    def _add_get_function(self, file_path: str, func_name: str, func_code: str):
        """Adiciona função get_* ao final do arquivo"""
        full_path = os.path.join(self.base_path, file_path)
        
        if not os.path.exists(full_path):
            print(f"   ⚠️ Arquivo não encontrado: {file_path}")
            return
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Verificar se função já existe
            if f"def {func_name}" in content:
                print(f"   ℹ️ Função {func_name} já existe em {file_path}")
                return
            
            # Adicionar função no final
            content = content.rstrip() + "\n\n" + func_code.strip() + "\n"
            
            # Backup
            backup_path = self._create_backup(full_path)
            self.backups_created.append((full_path, backup_path))
            
            # Salvar
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"   ✅ Função {func_name} adicionada em {file_path}")
            
        except Exception as e:
            print(f"   ❌ Erro ao adicionar função: {e}")


def main():
    """Função principal"""
    fixer = ImportFixer()
    
    # Corrigir imports
    fixer.fix_imports()
    
    # Criar funções faltantes
    fixer.create_fix_functions()
    
    print("\n✅ Correção concluída!")
    print("   Execute verificar_imports_quebrados.py novamente para validar")


if __name__ == "__main__":
    main() 