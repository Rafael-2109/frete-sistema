"""
Interface de Transição - Claude AI
Permite usar tanto o sistema antigo quanto o novo
"""

import os
import asyncio
from typing import Dict, Optional, Any

class ClaudeTransition:
    """Classe de transição entre sistemas antigo e novo"""
    
    def __init__(self):
        self.usar_sistema_novo = os.getenv('USE_NEW_CLAUDE_SYSTEM', 'true').lower() == 'true'
        
        if self.usar_sistema_novo:
            self._inicializar_sistema_novo()
        else:
            self._inicializar_sistema_antigo()
    
    def _inicializar_sistema_novo(self):
        """Inicializa sistema novo"""
        try:
            from app.claude_ai_novo.integration.claude import get_claude_integration
            self.claude = get_claude_integration()
            self.sistema_ativo = "novo"
            print("✅ Sistema Claude AI NOVO ativado")
        except Exception as e:
            print(f"❌ Erro ao inicializar sistema novo: {e}")
            self._inicializar_sistema_antigo()
    
    def _inicializar_sistema_antigo(self):
        """Inicializa sistema antigo"""
        try:
            from app.claude_ai.claude_real_integration import processar_com_claude_real
            self.processar_consulta_real = processar_com_claude_real
            self.sistema_ativo = "antigo"
            print("✅ Sistema Claude AI ANTIGO ativado")
        except Exception as e:
            print(f"❌ Erro ao inicializar sistema antigo: {e}")
            self.sistema_ativo = "nenhum"
    
    async def processar_consulta(self, consulta: str, user_context: Optional[Dict] = None) -> str:
        """Processa consulta usando o sistema ativo (agora async)"""
        
        if self.sistema_ativo == "novo":
            # Sistema novo - verificar se é assíncrono e garantir retorno string
            if hasattr(self.claude.processar_consulta_real, '__await__'):
                result = await self.claude.processar_consulta_real(consulta, user_context)
            else:
                result = self.claude.processar_consulta_real(consulta, user_context)
            
            # Garantir que sempre retorne string
            return str(result) if result is not None else "Resposta não disponível"
            
        elif self.sistema_ativo == "antigo":
            # Sistema antigo é síncrono
            result = self.processar_consulta_real(consulta, user_context)
            return str(result) if result is not None else "Resposta não disponível"
        else:
            return "❌ Nenhum sistema Claude AI disponível"
    
    def alternar_sistema(self):
        """Alterna entre sistema antigo e novo"""
        if self.sistema_ativo == "novo":
            self._inicializar_sistema_antigo()
        else:
            self._inicializar_sistema_novo()
        
        return f"🔄 Sistema alterado para: {self.sistema_ativo}"

# Instância global
_claude_transition = None

def get_claude_transition():
    """Retorna instância de transição"""
    global _claude_transition
    if _claude_transition is None:
        _claude_transition = ClaudeTransition()
    return _claude_transition

async def processar_consulta_transicao_async(consulta: str, user_context: Optional[Dict] = None) -> str:
    """Função ASYNC para processar consultas independente do sistema"""
    transition = get_claude_transition()
    return await transition.processar_consulta(consulta, user_context)

def processar_consulta_transicao(consulta: str, user_context: Optional[Dict] = None) -> str:
    """Função SÍNCRONA para compatibilidade - executa versão async"""
    try:
        # Tentar usar loop existente
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Se loop já está rodando, criar uma task
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, 
                    processar_consulta_transicao_async(consulta, user_context))
                return future.result(timeout=30)  # 30 segundos timeout
        else:
            # Loop não está rodando, usar run_until_complete
            return loop.run_until_complete(
                processar_consulta_transicao_async(consulta, user_context)
            )
    except RuntimeError:
        # Se não há loop, criar um novo
        return asyncio.run(
            processar_consulta_transicao_async(consulta, user_context)
        )
    except Exception as e:
        print(f"❌ Erro na transição: {e}")
        return f"❌ Erro no sistema de transição: {e}"
