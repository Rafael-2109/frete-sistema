#!/usr/bin/env python3
"""
🔧 SCRIPT PARA CORRIGIR OS 3 PROBLEMAS RESTANTES DO CLAUDE AI
Resolve: import circular, arquivos faltantes, módulo colorlog
"""

import os
import sys
import json
from pathlib import Path

def main():
    """Função principal que corrige os 3 problemas restantes"""
    print("🔧 CORRIGINDO OS 3 PROBLEMAS RESTANTES DO CLAUDE AI")
    print("=" * 80)
    
    problemas_resolvidos = 0
    
    # 1. Corrigir import circular
    print("\n🔄 1. CORRIGINDO IMPORT CIRCULAR...")
    if corrigir_import_circular():
        print("✅ Import circular corrigido!")
        problemas_resolvidos += 1
    else:
        print("❌ Falha ao corrigir import circular")
    
    # 2. Criar arquivos faltantes no diretório correto
    print("\n📁 2. CRIANDO ARQUIVOS FALTANTES...")
    if criar_arquivos_faltantes():
        print("✅ Arquivos faltantes criados!")
        problemas_resolvidos += 1
    else:
        print("❌ Falha ao criar arquivos faltantes")
    
    # 3. Adicionar colorlog ao requirements
    print("\n🎨 3. ADICIONANDO COLORLOG AO REQUIREMENTS...")
    if adicionar_colorlog_requirements():
        print("✅ Colorlog adicionado ao requirements!")
        problemas_resolvidos += 1
    else:
        print("❌ Falha ao adicionar colorlog")
    
    print(f"\n🎯 RESULTADO: {problemas_resolvidos}/3 problemas corrigidos")
    
    if problemas_resolvidos == 3:
        print("\n🎉 TODOS OS 3 PROBLEMAS RESTANTES FORAM CORRIGIDOS!")
        print("📋 PRÓXIMOS PASSOS:")
        print("1. git add .")
        print("2. git commit -m 'fix: Corrigir 3 problemas restantes Claude AI'")
        print("3. git push")
        return True
    else:
        print(f"\n⚠️ Ainda restam {3 - problemas_resolvidos} problemas para corrigir")
        return False

def corrigir_import_circular():
    """Corrige o import circular no enhanced_claude_integration.py"""
    
    try:
        arquivo = Path('app/claude_ai/enhanced_claude_integration.py')
        
        if not arquivo.exists():
            print("❌ Arquivo enhanced_claude_integration.py não encontrado")
            return False
        
        # Ler conteúdo atual
        content = arquivo.read_text(encoding='utf-8')
        
        # Verificar se a função get_enhanced_claude_system existe
        if 'def get_enhanced_claude_system(' not in content:
            print("❌ Função get_enhanced_claude_system não encontrada")
            return False
        
        # Verificar se há import circular
        if 'from .claude_real_integration import ClaudeRealIntegration' in content:
            print("🔄 Removendo import circular...")
            
            # Substituir import circular por import lazy
            content_corrigido = content.replace(
                'from .claude_real_integration import ClaudeRealIntegration',
                '# from .claude_real_integration import ClaudeRealIntegration  # Removido para evitar import circular'
            )
            
            # Modificar __init__ para fazer import lazy
            content_corrigido = content_corrigido.replace(
                'self.claude_integration = ClaudeRealIntegration()',
                '''# Import lazy para evitar circular import
        try:
            from .claude_real_integration import ClaudeRealIntegration
            self.claude_integration = ClaudeRealIntegration()
        except ImportError as e:
            print(f"⚠️ Warning: ClaudeRealIntegration não disponível: {e}")
            self.claude_integration = None'''
            )
            
            # Salvar arquivo corrigido
            arquivo.write_text(content_corrigido, encoding='utf-8')
            print("✅ Import circular removido com sucesso!")
            return True
        else:
            print("✅ Nenhum import circular detectado")
            return True
            
    except Exception as e:
        print(f"❌ Erro ao corrigir import circular: {e}")
        return False

def criar_arquivos_faltantes():
    """Cria os arquivos faltantes nos diretórios corretos"""
    
    try:
        # Criar diretório instance/claude_ai se não existir
        instance_dir = Path('instance/claude_ai')
        instance_dir.mkdir(parents=True, exist_ok=True)
        print(f"✅ Diretório {instance_dir} criado")
        
        # 1. Criar security_config.json no instance/claude_ai
        security_config = {
            "security_level": "production",
            "max_requests_per_minute": 60,
            "allowed_commands": [
                "descobrir_projeto",
                "ler_arquivo", 
                "criar_modulo",
                "inspecionar_banco",
                "listar_diretorio"
            ],
            "blocked_patterns": [
                "rm -rf",
                "del /",
                "format",
                "DROP DATABASE"
            ],
            "logging": {
                "enabled": True,
                "level": "INFO",
                "max_log_size_mb": 10
            }
        }
        
        security_file = instance_dir / 'security_config.json'
        with open(security_file, 'w', encoding='utf-8') as f:
            json.dump(security_config, f, indent=2, ensure_ascii=False)
        print(f"✅ Arquivo {security_file} criado")
        
        # 2. Criar diretório backups no instance/claude_ai
        backups_dir = instance_dir / 'backups'
        backups_dir.mkdir(exist_ok=True)
        
        # Criar subdiretórios
        (backups_dir / 'projects').mkdir(exist_ok=True)
        (backups_dir / 'generated').mkdir(exist_ok=True)
        
        # Criar arquivos .gitkeep
        (backups_dir / 'projects' / '.gitkeep').touch()
        (backups_dir / 'generated' / '.gitkeep').touch()
        
        print(f"✅ Diretório {backups_dir} e subdiretórios criados")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao criar arquivos faltantes: {e}")
        return False

def adicionar_colorlog_requirements():
    """Adiciona colorlog ao requirements.txt"""
    
    try:
        requirements_file = Path('requirements.txt')
        
        if not requirements_file.exists():
            print("❌ Arquivo requirements.txt não encontrado")
            return False
        
        # Ler requirements atual
        content = requirements_file.read_text(encoding='utf-8')
        
        # Verificar se colorlog já está presente
        if 'colorlog' in content:
            print("✅ Colorlog já está no requirements.txt")
            return True
        
        # Adicionar colorlog
        content += "\n# Logging colorido\ncolorlog>=6.7.0\n"
        
        # Salvar arquivo
        requirements_file.write_text(content, encoding='utf-8')
        print("✅ Colorlog adicionado ao requirements.txt")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao adicionar colorlog: {e}")
        return False

if __name__ == "__main__":
    main() 