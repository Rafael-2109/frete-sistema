#!/usr/bin/env python3
"""
🚀 TESTE SIMPLES - DETECÇÃO DE COMANDOS AUTOMÁTICOS
Testa apenas se o Auto Command Processor detecta comandos corretamente
"""

import os
import sys
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Adicionar path do projeto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def teste_deteccao_comandos():
    """Testa apenas a detecção de comandos"""
    
    print("🚀 TESTE DE DETECÇÃO DE COMANDOS")
    print("=" * 50)
    
    try:
        # Importar Auto Command Processor diretamente
        from app.claude_ai.auto_command_processor import AutoCommandProcessor
        
        # Criar instância
        processor = AutoCommandProcessor()
        print("✅ Auto Command Processor criado com sucesso")
        
        # Teste de comandos
        comandos_teste = [
            "descobrir projeto",
            "lê o arquivo carteira/models.py", 
            "cria um módulo teste com campos nome, ativo",
            "inspeciona o banco",
            "lista o diretório embarques",
            "quantas entregas do Assai"  # Este NÃO deve ser detectado
        ]
        
        sucessos = 0
        total = len(comandos_teste)
        
        for i, consulta in enumerate(comandos_teste, 1):
            print(f"\n[{i}/{total}] Testando: '{consulta}'")
            
            # Detectar comando
            comando_detectado, parametros = processor.detect_command(consulta)
            
            if i <= 5:  # Primeiros 5 devem ser detectados
                if comando_detectado:
                    print(f"   ✅ DETECTADO: {comando_detectado} - {parametros}")
                    sucessos += 1
                else:
                    print(f"   ❌ NÃO DETECTADO (deveria ser detectado)")
            else:  # Último não deve ser detectado
                if not comando_detectado:
                    print(f"   ✅ CORRETO: Consulta normal não foi detectada como comando")
                    sucessos += 1
                else:
                    print(f"   ❌ INCORRETO: Consulta normal foi detectada como comando: {comando_detectado}")
        
        # Resultado
        percentual = (sucessos / total * 100)
        print("\n" + "=" * 50)
        print("RESULTADO FINAL")
        print("=" * 50)
        print(f"✅ Sucessos: {sucessos}/{total} ({percentual:.1f}%)")
        
        if percentual == 100:
            print("🎉 DETECÇÃO FUNCIONANDO PERFEITAMENTE!")
            print("Auto Command Processor está pronto para integração!")
        elif percentual >= 80:
            print("⚠️ DETECÇÃO PARCIALMENTE FUNCIONAL")
            print("Algumas regras precisam de ajuste")
        else:
            print("❌ DETECÇÃO COM PROBLEMAS")
            print("Necessário revisar padrões de detecção")
        
        return percentual == 100
        
    except ImportError as e:
        print(f"❌ ERRO DE IMPORT: {e}")
        return False
    except Exception as e:
        print(f"❌ ERRO: {e}")
        return False

if __name__ == '__main__':
    sucesso = teste_deteccao_comandos()
    
    if sucesso:
        print("\n🎉 INTEGRAÇÃO PRONTA!")
        print("O Auto Command Processor detecta comandos corretamente")
        print("A integração ao chat principal deve funcionar!")
    else:
        print("\n⚠️ Problemas encontrados")
        print("Revisar implementação antes de usar em produção") 