#!/usr/bin/env python3
"""
🔧 FIX CLAUDE IDENTITY - Integração Final do Claude Development AI
Script para garantir que toda a integração esteja funcionando perfeitamente
"""

import os
import sys
from pathlib import Path

def fix_integration():
    """Corrige e valida toda a integração"""
    print("🔧 CORRIGINDO INTEGRAÇÃO DO CLAUDE DEVELOPMENT AI\n")
    
    success = True
    
    # 1. Verificar estrutura de arquivos
    print("📁 Verificando estrutura de arquivos...")
    required_files = [
        "app/claude_ai/claude_development_ai.py",
        "app/claude_ai/claude_project_scanner.py", 
        "app/claude_ai/claude_code_generator.py",
        "app/claude_ai/routes.py"
    ]
    
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"   ✅ {file_path}")
        else:
            print(f"   ❌ {file_path} - ARQUIVO FALTANDO!")
            success = False
    
    # 2. Verificar imports no __init__.py
    print("\n🔌 Verificando imports...")
    init_file = Path("app/claude_ai/__init__.py")
    
    if init_file.exists():
        content = init_file.read_text(encoding='utf-8')
        
        required_imports = [
            "claude_development_ai",
            "claude_project_scanner", 
            "claude_code_generator"
        ]
        
        for import_name in required_imports:
            if import_name in content:
                print(f"   ✅ Import {import_name} encontrado")
            else:
                print(f"   ⚠️ Import {import_name} pode estar faltando")
    
    # 3. Verificar se há conflitos nas rotas
    print("\n🌐 Verificando rotas...")
    routes_file = Path("app/claude_ai/routes.py")
    
    if routes_file.exists():
        content = routes_file.read_text(encoding='utf-8')
        
        # Verificar se há funções duplicadas
        import re
        function_defs = re.findall(r'def\s+(\w+)\s*\(', content)
        duplicates = [f for f in function_defs if function_defs.count(f) > 1]
        
        if duplicates:
            print(f"   ⚠️ Funções duplicadas encontradas: {duplicates}")
            success = False
        else:
            print("   ✅ Nenhuma função duplicada encontrada")
        
        # Contar rotas dev-ai
        dev_ai_routes = content.count("@claude_ai_bp.route('/dev-ai/")
        print(f"   📊 Total de rotas /dev-ai/: {dev_ai_routes}")
    
    # 4. Adicionar imports necessários se faltando
    print("\n⚙️ Corrigindo imports se necessário...")
    
    if init_file.exists():
        content = init_file.read_text(encoding='utf-8')
        
        imports_to_add = []
        
        if "claude_development_ai" not in content:
            imports_to_add.append("from . import claude_development_ai")
        
        if "claude_project_scanner" not in content:
            imports_to_add.append("from . import claude_project_scanner")
        
        if "claude_code_generator" not in content:
            imports_to_add.append("from . import claude_code_generator")
        
        if imports_to_add:
            print(f"   🔧 Adicionando {len(imports_to_add)} imports...")
            
            # Adicionar no final do arquivo
            new_content = content + "\n\n# Imports adicionados automaticamente\n"
            for imp in imports_to_add:
                new_content += f"{imp}\n"
            
            init_file.write_text(new_content, encoding='utf-8')
            print("   ✅ Imports adicionados com sucesso!")
        else:
            print("   ✅ Todos os imports já estão presentes")
    
    # 5. Verificar e corrigir problemas no claude_real_integration.py
    print("\n🔗 Verificando integração principal...")
    integration_file = Path("app/claude_ai/claude_real_integration.py")
    
    if integration_file.exists():
        content = integration_file.read_text(encoding='utf-8')
        
        # Verificar se há import do claude_development_ai
        if "claude_development_ai" in content:
            print("   ✅ Integração com Development AI encontrada")
        else:
            print("   ⚠️ Integração com Development AI pode estar faltando")
            
            # Adicionar import se necessário
            if "from .claude_development_ai import" not in content:
                lines = content.split('\n')
                
                # Encontrar onde adicionar o import
                import_index = -1
                for i, line in enumerate(lines):
                    if line.startswith('from .') and 'import' in line:
                        import_index = i + 1
                
                if import_index > 0:
                    new_import = "from .claude_development_ai import get_claude_development_ai, init_claude_development_ai"
                    lines.insert(import_index, new_import)
                    
                    new_content = '\n'.join(lines)
                    integration_file.write_text(new_content, encoding='utf-8')
                    print("   🔧 Import adicionado ao claude_real_integration.py")
    
    # 6. Criar arquivo de configuração se necessário
    print("\n📋 Criando arquivo de configuração...")
    config_content = """# Configuração do Claude Development AI
CLAUDE_DEV_AI_ENABLED = True
CLAUDE_DEV_AI_AUTO_SCAN = True
CLAUDE_DEV_AI_BACKUP_ENABLED = True
CLAUDE_DEV_AI_MAX_FILE_SIZE = 1024  # KB
"""
    
    config_file = Path("app/claude_ai/dev_ai_config.py")
    if not config_file.exists():
        config_file.write_text(config_content, encoding='utf-8')
        print("   ✅ Arquivo de configuração criado")
    else:
        print("   ✅ Arquivo de configuração já existe")
    
    return success

def test_integration():
    """Testa a integração"""
    print("\n🧪 TESTANDO INTEGRAÇÃO...")
    
    try:
        # Adicionar ao path para importar
        sys.path.insert(0, str(Path.cwd()))
        
        # Testar imports básicos
        print("   🔍 Testando imports básicos...")
        
        try:
            from app.claude_ai.claude_development_ai import ClaudeDevelopmentAI
            print("   ✅ ClaudeDevelopmentAI importado com sucesso")
        except Exception as e:
            print(f"   ❌ Erro ao importar ClaudeDevelopmentAI: {e}")
            return False
        
        try:
            from app.claude_ai.claude_project_scanner import ClaudeProjectScanner
            print("   ✅ ClaudeProjectScanner importado com sucesso")
        except Exception as e:
            print(f"   ❌ Erro ao importar ClaudeProjectScanner: {e}")
            return False
        
        try:
            from app.claude_ai.claude_code_generator import ClaudeCodeGenerator
            print("   ✅ ClaudeCodeGenerator importado com sucesso")
        except Exception as e:
            print(f"   ❌ Erro ao importar ClaudeCodeGenerator: {e}")
            return False
        
        # Testar inicialização básica
        print("   🚀 Testando inicialização...")
        
        try:
            scanner = ClaudeProjectScanner()
            print("   ✅ ProjectScanner inicializado")
        except Exception as e:
            print(f"   ⚠️ Erro na inicialização do ProjectScanner: {e}")
        
        try:
            generator = ClaudeCodeGenerator()
            print("   ✅ CodeGenerator inicializado")
        except Exception as e:
            print(f"   ⚠️ Erro na inicialização do CodeGenerator: {e}")
        
        try:
            dev_ai = ClaudeDevelopmentAI()
            print("   ✅ ClaudeDevelopmentAI inicializado")
        except Exception as e:
            print(f"   ⚠️ Erro na inicialização do ClaudeDevelopmentAI: {e}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Erro geral no teste: {e}")
        return False

def create_usage_guide():
    """Cria guia de uso"""
    print("\n📚 Criando guia de uso...")
    
    guide_content = """# 🧠 Guia de Uso - Claude Development AI

## Capacidades Implementadas

### 🔍 Análise de Projeto
- **Comando:** "analisar projeto"
- **API:** `/claude-ai/dev-ai/analyze-project`
- **Funcionalidade:** Escaneia todo o projeto e gera relatório detalhado

### 📄 Análise de Arquivo
- **Comando:** "analisar arquivo app/models.py"
- **API:** `/claude-ai/dev-ai/analyze-file-v2`
- **Funcionalidade:** Analisa arquivo específico com métricas

### 🚀 Geração de Módulo
- **Comando:** "criar módulo vendas"
- **API:** `/claude-ai/dev-ai/generate-module-v2`
- **Funcionalidade:** Gera módulo Flask completo

### ✏️ Modificação de Arquivo
- **Comando:** "adicionar campo ao modelo"
- **API:** `/claude-ai/dev-ai/modify-file-v2`
- **Funcionalidade:** Modifica arquivos existentes

### 🔧 Detecção de Problemas
- **Comando:** "detectar problemas"
- **API:** `/claude-ai/dev-ai/detect-and-fix`
- **Funcionalidade:** Detecta e corrige problemas automaticamente

### 📚 Geração de Documentação
- **Comando:** "gerar documentação"
- **API:** `/claude-ai/dev-ai/generate-documentation`
- **Funcionalidade:** Gera documentação automática

### 📋 Listar Capacidades
- **Comando:** "capacidades" ou "o que você pode fazer"
- **API:** `/claude-ai/dev-ai/capabilities-v2`
- **Funcionalidade:** Lista todas as capacidades disponíveis

## Como Usar

### 1. No Chat do Claude AI
Digite consultas como:
- "Analisar o projeto completo"
- "Criar módulo de vendas com campos nome, email, telefone"
- "Detectar problemas de segurança"
- "Gerar documentação do projeto"

### 2. Via API REST
```javascript
// Análise de projeto
fetch('/claude-ai/dev-ai/analyze-project')

// Geração de módulo
fetch('/claude-ai/dev-ai/generate-module-v2', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        module_name: 'vendas',
        description: 'Módulo de vendas'
    })
})
```

### 3. Integração Automática
O Claude AI detecta automaticamente consultas sobre desenvolvimento e usa as ferramentas apropriadas.

## Arquivos Principais

- `claude_development_ai.py` - Sistema central
- `claude_project_scanner.py` - Escaneamento de projeto
- `claude_code_generator.py` - Geração de código
- `routes.py` - APIs REST

## Comandos de Teste

Execute o script de teste:
```bash
python test_claude_identity.py
```

## Solução de Problemas

1. **Erro de import:** Verifique se todos os arquivos estão presentes
2. **Erro de rota:** Verifique se não há duplicatas nas rotas
3. **Erro de permissão:** Certifique-se de ter permissões de escrita

## Próximos Passos

1. Teste as funcionalidades básicas
2. Customize conforme suas necessidades
3. Adicione novas capacidades conforme necessário
"""
    
    guide_file = Path("GUIA_CLAUDE_DEVELOPMENT_AI.md")
    guide_file.write_text(guide_content, encoding='utf-8')
    print("   ✅ Guia criado: GUIA_CLAUDE_DEVELOPMENT_AI.md")

def main():
    """Função principal"""
    print("🧠 CLAUDE DEVELOPMENT AI - CORREÇÃO E VALIDAÇÃO FINAL")
    print("="*70)
    
    # Verificar se estamos no diretório correto
    if not Path("app").exists():
        print("❌ Execute este script a partir do diretório raiz do projeto!")
        sys.exit(1)
    
    # Executar correções
    integration_ok = fix_integration()
    
    # Testar integração
    test_ok = test_integration()
    
    # Criar guia
    create_usage_guide()
    
    # Resultado final
    print("\n" + "="*70)
    print("📊 RESULTADO FINAL")
    print("="*70)
    
    if integration_ok and test_ok:
        print("🎉 INTEGRAÇÃO CONCLUÍDA COM SUCESSO!")
        print("\n✅ O Claude Development AI está pronto para uso!")
        print("\n📚 Consulte o arquivo GUIA_CLAUDE_DEVELOPMENT_AI.md para instruções")
        print("\n🧪 Execute 'python test_claude_identity.py' para testes completos")
        return True
    else:
        print("⚠️ PROBLEMAS ENCONTRADOS NA INTEGRAÇÃO")
        print("Revise os erros acima e execute novamente")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 