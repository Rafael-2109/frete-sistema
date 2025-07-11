#!/usr/bin/env python3
"""
🔧 CORREÇÃO DE IMPORTS UTILS - Claude AI Novo
============================================

Script para corrigir todos os imports problemáticos de 'from app import db'
nos utilitários do claude_ai_novo, substituindo por imports seguros com fallback.
"""

import os
import re
from pathlib import Path

def corrigir_import_app_db(conteudo: str) -> str:
    """
    Corrige imports 'from app import db' por versão segura com fallback.
    
    Args:
        conteudo: Conteúdo do arquivo
        
    Returns:
        Conteúdo corrigido
    """
    # Padrão para encontrar 'from app import db'
    padrao = r'from app import db'
    
    # Substituição segura
    substituicao = '''try:
    # Tentar import com fallback seguro
    import sys
    import os
    # Adicionar caminho para encontrar app
    parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    from app import db
except ImportError:
    # Fallback para mock se app não disponível
    from .flask_fallback import get_db
    db = get_db()'''
    
    # Aplicar substituição
    conteudo_corrigido = re.sub(padrao, substituicao, conteudo)
    
    return conteudo_corrigido

def corrigir_arquivo(caminho_arquivo: Path) -> bool:
    """
    Corrige imports em um arquivo específico.
    
    Args:
        caminho_arquivo: Caminho para o arquivo
        
    Returns:
        True se arquivo foi modificado
    """
    try:
        # Ler arquivo
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            conteudo_original = f.read()
        
        # Verificar se precisa de correção
        if 'from app import db' not in conteudo_original:
            print(f"⏭️  {caminho_arquivo.name}: Nenhuma correção necessária")
            return False
        
        # Aplicar correção
        conteudo_corrigido = corrigir_import_app_db(conteudo_original)
        
        # Salvar arquivo corrigido
        with open(caminho_arquivo, 'w', encoding='utf-8') as f:
            f.write(conteudo_corrigido)
        
        print(f"✅ {caminho_arquivo.name}: Imports corrigidos")
        return True
        
    except Exception as e:
        print(f"❌ {caminho_arquivo.name}: Erro - {e}")
        return False

def main():
    """Função principal"""
    print("🔧 Iniciando correção de imports em utils/...")
    print("=" * 50)
    
    # Diretório utils
    utils_dir = Path(__file__).parent / 'utils'
    
    # Arquivos para corrigir
    arquivos_problema = [
        'base_classes.py',
        'flask_context_wrapper.py',
        'response_utils.py',
        'utils_manager.py'
    ]
    
    corrigidos = 0
    total = len(arquivos_problema)
    
    for arquivo in arquivos_problema:
        caminho = utils_dir / arquivo
        
        if caminho.exists():
            if corrigir_arquivo(caminho):
                corrigidos += 1
        else:
            print(f"⚠️  {arquivo}: Arquivo não encontrado")
    
    print("=" * 50)
    print(f"📊 Resultado: {corrigidos}/{total} arquivos corrigidos")
    
    if corrigidos > 0:
        print("✅ Correções aplicadas com sucesso!")
        print("🔄 Execute o teste novamente para verificar melhorias")
    else:
        print("ℹ️  Nenhuma correção foi necessária")

if __name__ == "__main__":
    main() 