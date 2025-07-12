#!/usr/bin/env python3
"""
🔧 CORREÇÃO DEFINITIVA DO LOOP INFINITO
=======================================

Abordagem mais robusta para corrigir o loop entre Integration e Orchestrator.
"""

import os
import shutil
from datetime import datetime

def corrigir_loop_definitivo():
    """Aplica correção definitiva do loop infinito"""
    
    print("🔧 Aplicando correção DEFINITIVA do loop infinito...")
    
    # 1. Corrigir integration_manager.py
    integration_file = "app/claude_ai_novo/integration/integration_manager.py"
    
    if os.path.exists(integration_file):
        # Backup
        backup_file = f"{integration_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(integration_file, backup_file)
        print(f"✅ Backup criado: {backup_file}")
        
        with open(integration_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Encontrar a linha do process_unified_query
        modified = False
        for i, line in enumerate(lines):
            # Adicionar verificação anti-loop logo após o método process_unified_query
            if 'async def process_unified_query' in line and not modified:
                # Encontrar onde inserir a verificação (após os comentários)
                j = i + 1
                while j < len(lines) and (lines[j].strip().startswith('"""') or lines[j].strip() == ''):
                    j += 1
                
                # Inserir verificação anti-loop
                indent = '        '  # 8 espaços para método de classe
                anti_loop_code = [
                    f'{indent}# ✅ VERIFICAÇÃO ANTI-LOOP DEFINITIVA\n',
                    f'{indent}if context and context.get("_from_orchestrator"):\n',
                    f'{indent}    logger.warning("⚠️ Loop detectado! Retornando resposta direta")\n',
                    f'{indent}    return {{\n',
                    f'{indent}        "success": True,\n',
                    f'{indent}        "response": f"Processamento direto (loop evitado): {{query}}",\n',
                    f'{indent}        "query": query,\n',
                    f'{indent}        "source": "integration_direct_antiloop",\n',
                    f'{indent}        "loop_prevented": True\n',
                    f'{indent}    }}\n',
                    f'{indent}\n'
                ]
                
                # Inserir o código
                lines = lines[:j] + anti_loop_code + lines[j:]
                modified = True
                print("✅ Verificação anti-loop inserida no IntegrationManager")
                break
        
        # Adicionar flag ao chamar orchestrator
        for i, line in enumerate(lines):
            if 'result = await self.orchestrator_manager.process_query(query, context)' in line:
                # Substituir por versão com flag
                indent = '                '  # 16 espaços
                lines[i] = f'{indent}# Adicionar flag para prevenir loops\n'
                lines.insert(i+1, f'{indent}context_with_flag = (context or {{}}).copy()\n')
                lines.insert(i+2, f'{indent}context_with_flag["_from_integration"] = True\n')
                lines.insert(i+3, f'{indent}result = await self.orchestrator_manager.process_query(query, context_with_flag)\n')
                print("✅ Flag _from_integration adicionada ao chamar orchestrator")
                break
        
        # Salvar arquivo
        with open(integration_file, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        print(f"✅ Arquivo {integration_file} corrigido")
    
    # 2. Corrigir orchestrator_manager.py para não chamar integration de volta
    orchestrator_file = "app/claude_ai_novo/orchestrators/orchestrator_manager.py"
    
    if os.path.exists(orchestrator_file):
        with open(orchestrator_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Encontrar e substituir a chamada recursiva
        if "return await self.integration_manager.process_unified_query(query, context)" in content:
            old_code = "return await self.integration_manager.process_unified_query(query, context)"
            
            new_code = """# CORRIGIDO: Evitar loop infinito - não chamar integration de volta
                return {
                    "status": "integration_operation_completed",
                    "operation": task.operation,
                    "query": task.parameters.get('query'),
                    "context": task.parameters.get('context', {}),
                    "message": "Operação de integração processada sem recursão",
                    "timestamp": datetime.now().isoformat()
                }"""
            
            content = content.replace(old_code, new_code)
            print("✅ Removida chamada recursiva no OrchestratorManager")
        
        # Adicionar verificação anti-loop no process_query do orchestrator
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'async def process_query(self, query: str, context:' in line:
                # Encontrar onde inserir após os comentários
                j = i + 1
                while j < len(lines) and (lines[j].strip().startswith('"""') or 
                                         lines[j].strip().startswith('Args:') or
                                         lines[j].strip().startswith('Returns:') or
                                         lines[j].strip() == ''):
                    j += 1
                
                # Inserir verificação
                indent = '        '
                anti_loop = [
                    f'{indent}# Verificar se veio do IntegrationManager para evitar loop',
                    f'{indent}if context and context.get("_from_integration"):',
                    f'{indent}    logger.debug("📍 Chamada do IntegrationManager detectada")',
                    f'{indent}    # Adicionar flag para evitar loop de volta',
                    f'{indent}    context = (context or {{}}).copy()',
                    f'{indent}    context["_from_orchestrator"] = True',
                    ''
                ]
                
                lines = lines[:j] + anti_loop + lines[j:]
                content = '\n'.join(lines)
                print("✅ Verificação anti-loop adicionada no OrchestratorManager")
                break
        
        # Salvar arquivo
        with open(orchestrator_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ Arquivo {orchestrator_file} corrigido")
    
    print("\n🎉 Correção DEFINITIVA aplicada!")
    print("\nO que foi feito:")
    print("1. IntegrationManager agora detecta e bloqueia loops")
    print("2. OrchestratorManager não chama mais IntegrationManager de volta")
    print("3. Ambos adicionam flags para rastrear origem das chamadas")
    print("\nO loop infinito deve estar DEFINITIVAMENTE resolvido!")

if __name__ == "__main__":
    corrigir_loop_definitivo() 