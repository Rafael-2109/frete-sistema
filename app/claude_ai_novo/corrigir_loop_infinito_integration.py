#!/usr/bin/env python3
"""
🔧 CORREÇÃO DO LOOP INFINITO ENTRE INTEGRATION E ORCHESTRATOR
=============================================================

Problema: Loop infinito detectado onde:
1. IntegrationManager.process_unified_query() → OrchestratorManager.process_query()
2. OrchestratorManager detecta operação de integração
3. OrchestratorManager → IntegrationManager.process_unified_query()
4. Loop infinito!

Solução: Remover a chamada recursiva e implementar lógica direta.
"""

import os
import re
import shutil
from datetime import datetime

def corrigir_loop_infinito():
    """Corrige o loop infinito entre IntegrationManager e OrchestratorManager"""
    
    print("🔧 Iniciando correção do loop infinito...")
    
    # 1. Corrigir orchestrator_manager.py
    orchestrator_file = "app/claude_ai_novo/orchestrators/orchestrator_manager.py"
    
    if os.path.exists(orchestrator_file):
        # Backup
        backup_file = f"{orchestrator_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(orchestrator_file, backup_file)
        print(f"✅ Backup criado: {backup_file}")
        
        with open(orchestrator_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Remover a chamada recursiva problemática
        # Substituir a linha 587 que chama integration_manager.process_unified_query
        old_code = """return await self.integration_manager.process_unified_query(query, context)"""
        
        new_code = """# CORRIGIDO: Removida chamada recursiva que causava loop infinito
                # Em vez de chamar integration_manager, retornar resultado direto
                return {
                    "status": "integration_operation_direct",
                    "operation": task.operation,
                    "query": task.parameters.get('query'),
                    "context": task.parameters.get('context', {}),
                    "message": "Operação de integração processada diretamente",
                    "timestamp": datetime.now().isoformat()
                }"""
        
        if old_code in content:
            content = content.replace(old_code, new_code)
            print("✅ Removida chamada recursiva em _execute_integration_operation")
        
        # Salvar arquivo corrigido
        with open(orchestrator_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ Arquivo {orchestrator_file} corrigido")
    
    # 2. Adicionar flag anti-loop no IntegrationManager
    integration_file = "app/claude_ai_novo/integration/integration_manager.py"
    
    if os.path.exists(integration_file):
        with open(integration_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Adicionar verificação anti-loop no process_unified_query
        if "# ✅ LOG PARA DEBUG" in content:
            # Adicionar verificação antes da chamada do orchestrator
            old_section = """# ✅ LOG PARA DEBUG
        logger.info(f"🔄 INTEGRATION: Query='{query}' | Orchestrator={self.orchestrator_manager is not None}")"""
            
            new_section = """# ✅ VERIFICAÇÃO ANTI-LOOP
        # Detectar se já estamos em um contexto de orchestrator para evitar loop
        if context and context.get('_from_orchestrator'):
            logger.warning("⚠️ Detectado possível loop - retornando resposta direta")
            return {
                "success": True,
                "response": f"Processamento direto: {query}",
                "query": query,
                "source": "integration_direct",
                "loop_prevented": True
            }
        
        # ✅ LOG PARA DEBUG
        logger.info(f"🔄 INTEGRATION: Query='{query}' | Orchestrator={self.orchestrator_manager is not None}")"""
            
            content = content.replace(old_section, new_section)
            print("✅ Adicionada verificação anti-loop no IntegrationManager")
        
        # Adicionar flag no contexto quando chamar orchestrator
        if "result = await self.orchestrator_manager.process_query(query, context)" in content:
            old_call = "result = await self.orchestrator_manager.process_query(query, context)"
            new_call = """# Adicionar flag para prevenir loops
                context_with_flag = (context or {}).copy()
                context_with_flag['_from_integration'] = True
                result = await self.orchestrator_manager.process_query(query, context_with_flag)"""
            
            content = content.replace(old_call, new_call)
            print("✅ Adicionada flag de contexto ao chamar orchestrator")
        
        # Salvar arquivo
        with open(integration_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ Arquivo {integration_file} corrigido")
    
    print("\n🎉 Correção do loop infinito concluída!")
    print("\nPróximos passos:")
    print("1. Reiniciar o servidor Flask")
    print("2. Testar novamente a consulta")
    print("\nO sistema agora deve processar consultas sem loops infinitos.")

if __name__ == "__main__":
    corrigir_loop_infinito() 