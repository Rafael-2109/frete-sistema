#!/usr/bin/env python3
"""
Script para corrigir temporariamente o problema dos triggers
Execute este script antes de rodar a sincronização
"""

import sys
import os

# Adicionar o diretório do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def aplicar_patch():
    """Aplica o patch temporário nos triggers"""
    try:
        # Substituir o módulo de triggers pelo corrigido
        import app.estoque.cache_triggers_fixed as fixed_triggers
        import app.estoque
        
        # Substituir o módulo original
        app.estoque.cache_triggers = fixed_triggers
        
        # Desabilitar triggers durante operações críticas
        fixed_triggers.desabilitar_triggers()
        
        print("✅ Patch aplicado com sucesso!")
        print("🔴 Triggers desabilitados temporariamente")
        print("ℹ️  Para reabilitar, use: fixed_triggers.habilitar_triggers()")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao aplicar patch: {e}")
        return False

if __name__ == "__main__":
    if aplicar_patch():
        print("\n📌 Agora você pode executar a sincronização sem erros de triggers")
        print("📌 Os triggers foram desabilitados temporariamente")
    else:
        print("\n❌ Falha ao aplicar o patch")
        sys.exit(1)