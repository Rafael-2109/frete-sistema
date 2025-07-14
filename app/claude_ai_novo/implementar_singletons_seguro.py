"""
🔧 IMPLEMENTADOR SEGURO DE SINGLETONS
=====================================

Versão mais segura que analisa riscos antes de aplicar.
"""

import os
import re
import ast
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
import shutil
from datetime import datetime

# Configurar caminhos
ROOT_PATH = Path(__file__).parent
BACKUP_DIR = ROOT_PATH / "backups" / f"pre_singleton_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

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


class SingletonAnalyzer:
    """Analisa riscos antes de aplicar singleton"""
    
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.content = file_path.read_text(encoding='utf-8')
        self.tree = None
        self.risks = []
        
    def analyze(self, class_name: str) -> Dict[str, Any]:
        """Analisa a classe e identifica riscos"""
        try:
            self.tree = ast.parse(self.content)
        except SyntaxError as e:
            return {
                'safe': False,
                'error': f'Erro de sintaxe no arquivo: {e}',
                'risks': ['syntax_error']
            }
        
        # Encontrar a classe
        class_node = self._find_class(class_name)
        if not class_node:
            return {
                'safe': False,
                'error': f'Classe {class_name} não encontrada',
                'risks': ['class_not_found']
            }
        
        # Analisar riscos
        analysis = {
            'safe': True,
            'risks': [],
            'has_new': self._has_new_method(class_node),
            'has_complex_init': self._has_complex_init(class_node),
            'has_inheritance': self._has_inheritance(class_node),
            'has_metaclass': self._has_metaclass(class_node),
            'has_inner_classes': self._has_inner_classes(class_node),
            'init_params': self._get_init_params(class_node)
        }
        
        # Avaliar riscos
        if analysis['has_new']:
            analysis['risks'].append('already_has_new')
            analysis['safe'] = False
            
        if analysis['has_metaclass']:
            analysis['risks'].append('has_metaclass')
            analysis['safe'] = False
            
        if analysis['has_complex_init']:
            analysis['risks'].append('complex_init')
            # Não é impeditivo, mas precisa cuidado
            
        if analysis['has_inheritance']:
            analysis['risks'].append('has_inheritance')
            # Não é impeditivo, mas precisa verificação
            
        return analysis
    
    def _find_class(self, class_name: str) -> Optional[ast.ClassDef]:
        """Encontra o nó da classe no AST"""
        if not self.tree:
            return None
        for node in ast.walk(self.tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                return node
        return None
    
    def _has_new_method(self, class_node: ast.ClassDef) -> bool:
        """Verifica se a classe já tem __new__"""
        for node in class_node.body:
            if isinstance(node, ast.FunctionDef) and node.name == '__new__':
                return True
        return False
    
    def _has_complex_init(self, class_node: ast.ClassDef) -> bool:
        """Verifica se tem __init__ complexo"""
        for node in class_node.body:
            if isinstance(node, ast.FunctionDef) and node.name == '__init__':
                # Considera complexo se tem mais de 5 linhas
                return len(node.body) > 5
        return False
    
    def _has_inheritance(self, class_node: ast.ClassDef) -> bool:
        """Verifica se a classe herda de outra"""
        return len(class_node.bases) > 0
    
    def _has_metaclass(self, class_node: ast.ClassDef) -> bool:
        """Verifica se usa metaclass"""
        for keyword in class_node.keywords:
            if keyword.arg == 'metaclass':
                return True
        return False
    
    def _has_inner_classes(self, class_node: ast.ClassDef) -> bool:
        """Verifica se tem classes internas"""
        for node in class_node.body:
            if isinstance(node, ast.ClassDef):
                return True
        return False
    
    def _get_init_params(self, class_node: ast.ClassDef) -> List[str]:
        """Obtém parâmetros do __init__"""
        for node in class_node.body:
            if isinstance(node, ast.FunctionDef) and node.name == '__init__':
                params = []
                for arg in node.args.args[1:]:  # Skip self
                    params.append(arg.arg)
                return params
        return []


def fazer_backup_completo():
    """Faz backup completo da pasta"""
    print(f"📁 Criando backup completo em: {BACKUP_DIR}")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    
    for arquivo_relativo, _, _ in MANAGERS_PARA_CORRIGIR:
        arquivo_path = ROOT_PATH / arquivo_relativo
        if arquivo_path.exists():
            backup_path = BACKUP_DIR / arquivo_relativo
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(arquivo_path, backup_path)
            print(f"  ✅ Backup: {arquivo_relativo}")


def implementar_singleton_seguro(arquivo_path: Path, classe_nome: str, instance_var: str) -> Dict[str, Any]:
    """Implementa singleton de forma segura"""
    
    # Analisar riscos
    analyzer = SingletonAnalyzer(arquivo_path)
    analysis = analyzer.analyze(classe_nome)
    
    if not analysis['safe']:
        return {
            'success': False,
            'reason': 'unsafe',
            'analysis': analysis
        }
    
    # Se tem riscos menores, avisar mas continuar
    if analysis['risks']:
        print(f"  ⚠️  Riscos detectados: {', '.join(analysis['risks'])}")
    
    # Implementar singleton preservando parâmetros do __init__
    conteudo = arquivo_path.read_text(encoding='utf-8')
    lines = conteudo.split('\n')
    
    # 1. Adicionar variável instance
    import_end = 0
    for i, line in enumerate(lines):
        if line.strip() and not line.startswith(('import ', 'from ', '#', '"""', "'''")):
            if i > 0 and lines[i-1].strip() == '':
                import_end = i
                break
    
    lines.insert(import_end, f"\n# Singleton instance\n{instance_var} = None\n")
    
    # 2. Adicionar __new__ com suporte a parâmetros
    class_start = -1
    for i, line in enumerate(lines):
        if f"class {classe_nome}" in line:
            class_start = i
            break
    
    if class_start == -1:
        return {
            'success': False,
            'reason': 'class_not_found'
        }
    
    # Detectar indentação
    indent = "    "  # Default
    for i in range(class_start + 1, min(class_start + 10, len(lines))):
        if lines[i].strip() and not lines[i].strip().startswith(('"""', "'''")):
            indent = lines[i][:len(lines[i]) - len(lines[i].lstrip())]
            break
    
    # Criar método __new__ que preserva parâmetros
    new_method = f'''
{indent}def __new__(cls, *args, **kwargs):
{indent}    """Implementação do padrão Singleton"""
{indent}    global {instance_var}
{indent}    if {instance_var} is None:
{indent}        {instance_var} = super().__new__(cls)
{indent}    return {instance_var}
'''
    
    # Inserir após docstring da classe
    insert_pos = class_start + 1
    if insert_pos < len(lines) and lines[insert_pos].strip().startswith(('"""', "'''")):
        quote = '"""' if '"""' in lines[insert_pos] else "'''"
        if lines[insert_pos].strip().endswith(quote) and lines[insert_pos].count(quote) == 2:
            insert_pos += 1
        else:
            insert_pos += 1
            while insert_pos < len(lines) and quote not in lines[insert_pos]:
                insert_pos += 1
            insert_pos += 1
    
    lines.insert(insert_pos, new_method)
    
    # 3. Atualizar funções get_* 
    conteudo_novo = '\n'.join(lines)
    
    # Encontrar e atualizar funções get
    pattern = rf"(def get_\w*{classe_nome.lower().replace('manager', '_?manager')}[^(]*\([^)]*\)[^:]*:)(.*?)(return {classe_nome}\([^)]*\))"
    
    def replace_get_function(match):
        func_def = match.group(1)
        body = match.group(2)
        return_stmt = match.group(3)
        
        # Criar novo return com singleton
        new_return = f"""
    global {instance_var}
    if {instance_var} is None:
        {instance_var} = {classe_nome}()
    return {instance_var}"""
        
        return func_def + body.rstrip() + new_return
    
    conteudo_novo = re.sub(pattern, replace_get_function, conteudo_novo, flags=re.DOTALL)
    
    # Salvar
    arquivo_path.write_text(conteudo_novo, encoding='utf-8')
    
    return {
        'success': True,
        'analysis': analysis
    }


def criar_teste_singleton(classe_nome: str, modulo_path: str) -> str:
    """Cria código de teste para verificar singleton"""
    return f'''
# Teste do singleton {classe_nome}
from app.claude_ai_novo.{modulo_path.replace("/", ".").replace(".py", "")} import get_{classe_nome.lower().replace("manager", "_manager")}

# Obter duas instâncias
instance1 = get_{classe_nome.lower().replace("manager", "_manager")}()
instance2 = get_{classe_nome.lower().replace("manager", "_manager")}()

# Verificar se são a mesma
assert instance1 is instance2, f"❌ {classe_nome} não é singleton!"
print(f"✅ {classe_nome} é singleton corretamente")
'''


def main():
    """Execução principal com análise de riscos"""
    print("🔧 IMPLEMENTADOR SEGURO DE SINGLETONS")
    print("=" * 60)
    
    # Fazer backup completo primeiro
    fazer_backup_completo()
    
    resultados = {
        'sucesso': [],
        'falha': [],
        'pulados': []
    }
    
    # Criar arquivo de testes
    teste_code = "# Testes de Singleton\n\n"
    
    for arquivo_relativo, classe, instance_var in MANAGERS_PARA_CORRIGIR:
        arquivo_path = ROOT_PATH / arquivo_relativo
        print(f"\n📄 Analisando: {arquivo_relativo}")
        
        if not arquivo_path.exists():
            print(f"  ❌ Arquivo não encontrado")
            resultados['falha'].append((arquivo_relativo, 'not_found'))
            continue
        
        # Verificar se já tem singleton
        conteudo = arquivo_path.read_text(encoding='utf-8')
        if instance_var in conteudo or "__new__" in conteudo:
            print(f"  ⏭️  Já tem singleton, pulando")
            resultados['pulados'].append(arquivo_relativo)
            continue
        
        # Implementar com segurança
        resultado = implementar_singleton_seguro(arquivo_path, classe, instance_var)
        
        if resultado['success']:
            print(f"  ✅ Singleton implementado com sucesso")
            resultados['sucesso'].append(arquivo_relativo)
            teste_code += criar_teste_singleton(classe, arquivo_relativo) + "\n"
        else:
            print(f"  ❌ Falha: {resultado['reason']}")
            if 'analysis' in resultado and resultado['analysis']['risks']:
                print(f"     Riscos: {', '.join(resultado['analysis']['risks'])}")
            resultados['falha'].append((arquivo_relativo, resultado))
    
    # Salvar testes
    teste_file = ROOT_PATH / "testar_singletons.py"
    teste_file.write_text(teste_code, encoding='utf-8')
    
    # Resumo
    print("\n" + "=" * 60)
    print("📊 RESUMO DA IMPLEMENTAÇÃO")
    print(f"✅ Sucesso: {len(resultados['sucesso'])}")
    print(f"⏭️  Pulados: {len(resultados['pulados'])}")
    print(f"❌ Falhas: {len(resultados['falha'])}")
    
    if resultados['falha']:
        print("\n⚠️  ARQUIVOS COM FALHA:")
        for arquivo, razao in resultados['falha']:
            print(f"  - {arquivo}: {razao}")
    
    print(f"\n📁 Backups em: {BACKUP_DIR}")
    print(f"🧪 Testes em: {teste_file}")
    
    print("\n⚠️  PRÓXIMOS PASSOS:")
    print("1. Execute testar_singletons.py para verificar")
    print("2. Revise os arquivos modificados")
    print("3. Execute os testes unitários")
    print("4. Se tudo OK, faça commit")


if __name__ == "__main__":
    main() 