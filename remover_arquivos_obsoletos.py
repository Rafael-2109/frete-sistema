#!/usr/bin/env python3
"""
Script para remover arquivos obsoletos do sistema híbrido
"""

import os
import sys

# Lista de arquivos obsoletos para remover
ARQUIVOS_OBSOLETOS = [
    # Sistema híbrido antigo
    "app/estoque/models_hibrido.py",
    "app/estoque/init_hibrido.py",
    "app/estoque/triggers_hibrido.py",
    "app/estoque/api_hibrida.py",
    "app/estoque/cli_cache.py",
    
    # Arquivos de teste/debug do sistema antigo
    "test_hibrido.py",
    "deploy_sistema_hibrido.py",
    "fix_estoque_atual.py",
    
    # Documentação obsoleta
    "SISTEMA_HIBRIDO_FINAL.md",
    "SOLUCAO_HIBRIDA.md",
    "INTEGRACAO_HIBRIDA.md",
    
    # Cache obsoleto
    "app/estoque/cache_optimized.py",
    "app/estoque/cache_triggers_safe.py",
    "app/estoque/cache_fix_pg1082.py",
    
    # Diagnóstico obsoleto
    "app/estoque/diagnostico_pg1082.py",
    "app/estoque/pg_register.py",
    "app/estoque/pg_types_fix.py",
    
    # Routes antigas
    "app/estoque/routes_cache.py",
    "app/estoque/models_cache.py"
]

def remover_arquivos():
    """Remove arquivos obsoletos"""
    removidos = []
    nao_encontrados = []
    
    for arquivo in ARQUIVOS_OBSOLETOS:
        caminho_completo = os.path.join(os.path.dirname(os.path.abspath(__file__)), arquivo)
        
        if os.path.exists(caminho_completo):
            try:
                os.remove(caminho_completo)
                removidos.append(arquivo)
                print(f"✅ Removido: {arquivo}")
            except Exception as e:
                print(f"❌ Erro ao remover {arquivo}: {e}")
        else:
            nao_encontrados.append(arquivo)
    
    print(f"\n📊 Resumo:")
    print(f"  ✅ {len(removidos)} arquivos removidos")
    print(f"  ℹ️  {len(nao_encontrados)} arquivos não encontrados (já removidos?)")
    
    if removidos:
        print(f"\n📝 Arquivos removidos com sucesso:")
        for arquivo in removidos:
            print(f"    - {arquivo}")
    
    return len(removidos)

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════╗
║     LIMPEZA DE ARQUIVOS OBSOLETOS DO SISTEMA        ║
╚══════════════════════════════════════════════════════╝
    """)
    
    resposta = input("⚠️  Deseja remover os arquivos obsoletos do sistema híbrido? (s/N): ")
    
    if resposta.lower() == 's':
        total = remover_arquivos()
        print(f"\n✅ Limpeza concluída! {total} arquivos removidos.")
    else:
        print("❌ Operação cancelada.")
        sys.exit(0)