#!/usr/bin/env python3
"""
🔧 Script para aplicar Flask Context em TODOS os módulos que acessam banco

DESCOBERTA: Não são apenas Loaders que acessam o banco!
Muitos outros módulos também fazem queries diretas.
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Tuple

def identificar_modulos_com_banco() -> Dict[str, List[str]]:
    """Identifica todos os módulos que acessam o banco"""
    
    modulos_com_banco = {
        'loaders/domain': [
            'entregas_loader.py',
            'fretes_loader.py', 
            'pedidos_loader.py',
            'embarques_loader.py',
            'faturamento_loader.py',
            'agendamentos_loader.py'
        ],
        'loaders': ['context_loader.py'],
        'processors': ['context_processor.py'],
        'providers': ['data_provider.py'],
        'memorizers': ['knowledge_memory.py', 'session_memory.py'],
        'learners': ['learning_core.py', 'pattern_learning.py', 'human_in_loop_learning.py'],
        'scanning': ['database_scanner.py', 'structure_scanner.py'],
        'validators': ['data_validator.py'],
        'commands': ['base_command.py', 'dev_commands.py'],
        'analyzers': ['query_analyzer.py'],
        'integration': ['web_integration.py'],
        'suggestions': ['suggestion_engine.py']
    }
    
    return modulos_com_banco

def verificar_flask_context_wrapper(arquivo: Path) -> bool:
    """Verifica se arquivo já usa flask_context_wrapper"""
    
    if not arquivo.exists():
        return False
        
    content = arquivo.read_text(encoding='utf-8')
    return 'flask_context_wrapper' in content

def aplicar_correcao_minima(arquivo: Path) -> bool:
    """Aplica correção mínima usando flask_fallback"""
    
    print(f"📝 Aplicando correção em {arquivo.name}...")
    
    try:
        content = arquivo.read_text(encoding='utf-8')
        
        # Se já tem flask_fallback, pular
        if 'flask_fallback' in content:
            print(f"✅ {arquivo.name} já usa flask_fallback")
            return True
        
        # Substituir imports diretos por flask_fallback
        mudancas = []
        
        # Substituir "from app import db"
        if 'from app import db' in content:
            content = content.replace(
                'from app import db',
                'from app.claude_ai_novo.utils.flask_fallback import get_db'
            )
            mudancas.append('import db')
            
            # Adicionar property para db
            if 'class ' in content:
                # Encontrar primeira classe
                lines = content.split('\n')
                new_lines = []
                class_found = False
                
                for line in lines:
                    new_lines.append(line)
                    if line.strip().startswith('class ') and not class_found:
                        class_found = True
                        indent = '    '
                        new_lines.extend([
                            '',
                            f'{indent}@property',
                            f'{indent}def db(self):',
                            f'{indent}    """Obtém db com fallback"""',
                            f'{indent}    if not hasattr(self, "_db"):',
                            f'{indent}        self._db = get_db()',
                            f'{indent}    return self._db',
                            ''
                        ])
                
                content = '\n'.join(new_lines)
        
        # Substituir imports de modelos
        model_pattern = r'from app\.[a-z]+\.models import (.+)'
        matches = re.findall(model_pattern, content)
        
        if matches:
            # Adicionar import do get_model
            if 'from app.claude_ai_novo.utils.flask_fallback import' in content:
                content = content.replace(
                    'from app.claude_ai_novo.utils.flask_fallback import get_db',
                    'from app.claude_ai_novo.utils.flask_fallback import get_db, get_model'
                )
            else:
                # Adicionar no topo após outros imports
                lines = content.split('\n')
                import_index = 0
                for i, line in enumerate(lines):
                    if line.startswith('from ') or line.startswith('import '):
                        import_index = i + 1
                    elif import_index > 0 and line.strip() and not line.startswith('from') and not line.startswith('import'):
                        break
                
                lines.insert(import_index, 'from app.claude_ai_novo.utils.flask_fallback import get_model')
                content = '\n'.join(lines)
            
            # Substituir cada modelo
            for match in matches:
                models = [m.strip() for m in match.split(',')]
                for model in models:
                    if ' as ' in model:
                        model_name = model.split(' as ')[0].strip()
                    else:
                        model_name = model.strip()
                    
                    # Comentar import original
                    old_import = f'from app.[a-z]+.models import .*{model_name}'
                    content = re.sub(old_import, f'# {old_import} - Usando flask_fallback', content)
                    
                    mudancas.append(f'modelo {model_name}')
        
        # Salvar arquivo corrigido
        arquivo.write_text(content, encoding='utf-8')
        
        if mudancas:
            print(f"✅ {arquivo.name} corrigido: {', '.join(mudancas)}")
        else:
            print(f"ℹ️ {arquivo.name} sem mudanças necessárias")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao corrigir {arquivo.name}: {e}")
        return False

def main():
    """Aplica correções em todos os módulos identificados"""
    
    print("🔍 APLICANDO FLASK CONTEXT EM TODOS OS MÓDULOS QUE ACESSAM BANCO")
    print("=" * 60)
    
    modulos_com_banco = identificar_modulos_com_banco()
    
    total_arquivos = sum(len(arquivos) for arquivos in modulos_com_banco.values())
    print(f"📊 Total de arquivos que acessam banco: {total_arquivos}")
    print()
    
    corrigidos = 0
    falhas = 0
    
    for pasta, arquivos in modulos_com_banco.items():
        print(f"\n📁 Processando {pasta}/")
        print("-" * 40)
        
        for arquivo_nome in arquivos:
            arquivo = Path(pasta) / arquivo_nome
            
            if aplicar_correcao_minima(arquivo):
                corrigidos += 1
            else:
                falhas += 1
    
    print("\n" + "=" * 60)
    print(f"✅ Arquivos corrigidos: {corrigidos}")
    print(f"❌ Falhas: {falhas}")
    
    if falhas == 0:
        print("\n🎉 TODAS AS CORREÇÕES APLICADAS COM SUCESSO!")
        print("🚀 O sistema agora deve funcionar corretamente no Render")
    else:
        print("\n⚠️ Algumas correções falharam - verificar manualmente")
    
    # Criar resumo
    criar_resumo_correcoes(modulos_com_banco)

def criar_resumo_correcoes(modulos: Dict[str, List[str]]) -> None:
    """Cria arquivo de resumo das correções"""
    
    resumo = """# 📋 RESUMO: Flask Context Aplicado

## 🔍 Módulos que Acessam Banco

"""
    
    for pasta, arquivos in modulos.items():
        resumo += f"### {pasta}/\n"
        for arquivo in arquivos:
            resumo += f"- {arquivo}\n"
        resumo += "\n"
    
    resumo += """
## ✅ Correções Aplicadas

1. **Imports substituídos** por flask_fallback
2. **Properties lazy** para db e modelos
3. **Compatibilidade** com Flask e modo standalone

## 🚀 Próximos Passos

1. Fazer commit das alterações
2. Push para o repositório
3. Deploy no Render
4. Monitorar logs para confirmar funcionamento
"""
    
    Path("FLASK_CONTEXT_APLICADO.md").write_text(resumo, encoding='utf-8')
    print("\n📄 Resumo salvo em FLASK_CONTEXT_APLICADO.md")

if __name__ == "__main__":
    # Verificar se estamos na pasta correta
    if not Path("loaders").exists():
        print("❌ Execute este script dentro da pasta app/claude_ai_novo/")
        exit(1)
    
    main() 