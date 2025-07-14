"""
🔧 IMPLEMENTADOR DE SINGLETONS CRÍTICOS
======================================

Adiciona padrão Singleton aos managers críticos que estão faltando.
"""

import os
import re
from pathlib import Path
from typing import List, Tuple, Dict, Any

# Configurar caminhos
ROOT_PATH = Path(__file__).parent
BACKUP_DIR = ROOT_PATH / "backups" / "pre_singleton"

# Managers que precisam de singleton
MANAGERS_PARA_CORRIGIR = [
    ("loaders/loader_manager.py", "LoaderManager", "_loader_manager_instance"),
    ("mappers/mapper_manager.py", "MapperManager", "_mapper_manager_instance"),
    ("scanning/scanning_manager.py", "ScanningManager", "_scanning_manager_instance"),
    ("scanning/database_manager.py", "DatabaseManager", "_database_manager_instance"),
    ("orchestrators/main_orchestrator.py", "MainOrchestrator", "_main_orchestrator_instance"),
    ("providers/data_provider.py", "DataProvider", "_data_provider_instance"),
    ("coordinators/intelligence_coordinator.py", "IntelligenceCoordinator", "_intelligence_coordinator_instance"),
    ("coordinators/coordinator_manager.py", "CoordinatorManager", "_coordinator_manager_instance"),
    ("enrichers/enricher_manager.py", "EnricherManager", "_enricher_manager_instance"),
    ("memorizers/memory_manager.py", "MemoryManager", "_memory_manager_instance"),
]


def fazer_backup(arquivo_path: Path):
    """Faz backup do arquivo antes de modificar"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_path = BACKUP_DIR / f"{arquivo_path.name}.backup"
    
    if arquivo_path.exists():
        conteudo = arquivo_path.read_text(encoding='utf-8')
        backup_path.write_text(conteudo, encoding='utf-8')
        print(f"✅ Backup criado: {backup_path}")


def adicionar_singleton(arquivo_path: Path, classe_nome: str, instance_var: str) -> bool:
    """
    Adiciona padrão singleton a uma classe.
    
    Returns:
        bool: True se modificou, False se já tinha
    """
    if not arquivo_path.exists():
        print(f"❌ Arquivo não encontrado: {arquivo_path}")
        return False
    
    conteudo = arquivo_path.read_text(encoding='utf-8')
    
    # Verifica se já tem singleton
    if instance_var in conteudo or "__new__" in conteudo:
        print(f"⚠️  {classe_nome} já parece ter singleton")
        return False
    
    # Fazer backup
    fazer_backup(arquivo_path)
    
    # Adicionar variável global no início do arquivo (após imports)
    import_section_end = 0
    lines = conteudo.split('\n')
    
    # Encontrar onde terminam os imports
    for i, line in enumerate(lines):
        if line.strip() and not line.startswith(('import ', 'from ', '#', '"""', "'''")):
            if i > 0 and lines[i-1].strip() == '':
                import_section_end = i
                break
    
    # Adicionar variável instance
    lines.insert(import_section_end, f"\n# Singleton instance\n{instance_var} = None\n")
    
    # Encontrar a classe e adicionar __new__
    class_start = -1
    indent = ""
    
    for i, line in enumerate(lines):
        if f"class {classe_nome}" in line:
            class_start = i
            # Detectar indentação
            next_line_idx = i + 1
            while next_line_idx < len(lines):
                if lines[next_line_idx].strip() and not lines[next_line_idx].strip().startswith(('"""')):
                    indent = lines[next_line_idx][:len(lines[next_line_idx]) - len(lines[next_line_idx].lstrip())]
                    break
                next_line_idx += 1
            break
    
    if class_start == -1:
        print(f"❌ Não encontrou classe {classe_nome}")
        return False
    
    # Adicionar método __new__ após a definição da classe
    new_method = f'''
{indent}def __new__(cls, *args, **kwargs):
{indent}    """Implementação do padrão Singleton"""
{indent}    global {instance_var}
{indent}    if {instance_var} is None:
{indent}        {instance_var} = super().__new__(cls)
{indent}    return {instance_var}
'''
    
    # Inserir após a linha da classe e docstring (se houver)
    insert_pos = class_start + 1
    
    # Pular docstring da classe se existir
    if insert_pos < len(lines) and lines[insert_pos].strip().startswith(('"""', "'''")):
        quote_char = '"""' if '"""' in lines[insert_pos] else "'''"
        # Se é docstring de uma linha
        if lines[insert_pos].strip().endswith(quote_char) and lines[insert_pos].count(quote_char) == 2:
            insert_pos += 1
        else:
            # Docstring de múltiplas linhas
            insert_pos += 1
            while insert_pos < len(lines):
                if quote_char in lines[insert_pos]:
                    insert_pos += 1
                    break
                insert_pos += 1
    
    lines.insert(insert_pos, new_method)
    
    # Atualizar funções get_* para usar singleton
    conteudo_novo = '\n'.join(lines)
    
    # Padrão para encontrar funções get_*
    get_func_pattern = rf"def get_{classe_nome.lower().replace('manager', '_manager')}.*?\n(.*?)return {classe_nome}\(\)"
    
    def replace_get_function(match):
        func_def = match.group(0)
        # Substituir return ClassName() por código singleton
        return func_def.replace(
            f"return {classe_nome}()",
            f"""global {instance_var}
    if {instance_var} is None:
        {instance_var} = {classe_nome}()
    return {instance_var}"""
        )
    
    conteudo_novo = re.sub(get_func_pattern, replace_get_function, conteudo_novo, flags=re.DOTALL)
    
    # Salvar arquivo modificado
    arquivo_path.write_text(conteudo_novo, encoding='utf-8')
    print(f"✅ Singleton adicionado a {classe_nome}")
    
    return True


def main():
    """Executa a implementação de singletons"""
    print("🔧 IMPLEMENTANDO SINGLETONS CRÍTICOS")
    print("=" * 60)
    
    modificados = 0
    
    for arquivo_relativo, classe, instance_var in MANAGERS_PARA_CORRIGIR:
        arquivo_path = ROOT_PATH / arquivo_relativo
        print(f"\n📄 Processando: {arquivo_relativo}")
        
        if adicionar_singleton(arquivo_path, classe, instance_var):
            modificados += 1
    
    print("\n" + "=" * 60)
    print(f"✅ Total de arquivos modificados: {modificados}")
    print(f"📁 Backups salvos em: {BACKUP_DIR}")
    
    if modificados > 0:
        print("\n⚠️  IMPORTANTE:")
        print("1. Revise as modificações antes de fazer commit")
        print("2. Execute os testes para garantir que tudo funciona")
        print("3. Os backups estão disponíveis caso precise reverter")


if __name__ == "__main__":
    main() 