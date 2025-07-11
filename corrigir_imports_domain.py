#!/usr/bin/env python3
"""
Script para corrigir imports nos mappers domain
"""

import os
import re

def corrigir_imports_domain():
    """Corrige imports incorretos nos mappers domain"""
    
    pasta_domain = "mappers/domain"
    
    # Arquivos para corrigir
    arquivos = [
        "embarques_mapper.py",
        "faturamento_mapper.py", 
        "monitoramento_mapper.py",
        "transportadoras_mapper.py"
    ]
    
    print("🔧 Corrigindo imports nos mappers domain...")
    
    for arquivo in arquivos:
        caminho = os.path.join(pasta_domain, arquivo)
        
        if not os.path.exists(caminho):
            print(f"⚠️ Arquivo não encontrado: {arquivo}")
            continue
            
        try:
            with open(caminho, 'r', encoding='utf-8') as f:
                conteudo = f.read()
            
            # Corrigir import absoluto para relativo
            conteudo_corrigido = re.sub(
                r'from app\.claude_ai_novo\.mappers\.base_mapper import BaseMapper',
                'from .base_mapper import BaseMapper',
                conteudo
            )
            
            # Verificar se houve mudança
            if conteudo != conteudo_corrigido:
                with open(caminho, 'w', encoding='utf-8') as f:
                    f.write(conteudo_corrigido)
                print(f"✅ Corrigido: {arquivo}")
            else:
                print(f"ℹ️ Já correto: {arquivo}")
                
        except Exception as e:
            print(f"❌ Erro ao corrigir {arquivo}: {e}")
    
    print("\n🎯 Testando imports...")
    
    # Testar import
    try:
        from mappers.domain import PedidosMapper
        mapper = PedidosMapper()
        print(f"✅ PedidosMapper funcionando!")
        print(f"   Modelo: {mapper.modelo_nome}")
        print(f"   Campos: {len(mapper.mapeamentos)}")
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")

if __name__ == "__main__":
    corrigir_imports_domain() 