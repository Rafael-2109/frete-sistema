"""
Interface de Transição - Claude AI
Permite usar tanto o sistema antigo quanto o novo com diagnóstico completo
"""

import os
import asyncio
from typing import Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)

class ClaudeTransition:
    """Classe de transição entre sistemas antigo e novo com diagnóstico"""
    
    def __init__(self):
        # CONFIGURAÇÃO: Definir qual sistema usar
        self.usar_sistema_novo = os.getenv('USE_NEW_CLAUDE_SYSTEM', 'false').lower() == 'true'
        
        # DIAGNÓSTICO: Tentar inicializar sistema preferido
        if self.usar_sistema_novo:
            if not self._inicializar_sistema_novo():
                logger.warning("⚠️ Sistema novo falhou, usando sistema antigo")
                self._inicializar_sistema_antigo()
        else:
            self._inicializar_sistema_antigo()
    
    def _inicializar_sistema_novo(self) -> bool:
        """Inicializa sistema novo com diagnóstico detalhado"""
        try:
            logger.info("🚀 Tentando inicializar sistema Claude AI NOVO...")
            
            # Verificar contexto Flask
            try:
                from flask import current_app
                if not current_app:
                    logger.error("❌ Contexto Flask não disponível")
                    return False
            except RuntimeError:
                logger.error("❌ Não está rodando dentro do contexto Flask")
                return False
            
            # Tentar importar componentes principais
            from app.claude_ai_novo.integration.external_api_integration import get_claude_integration
            self.claude = get_claude_integration()
            
            # Verificar se está funcionando
            status = self.claude.get_system_status()
            if not status.get('system_ready', False):
                logger.warning("⚠️ Sistema novo não está pronto")
            
            self.sistema_ativo = "novo"
            logger.info("✅ Sistema Claude AI NOVO ativado com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar sistema novo: {e}")
            return False
    
    def _inicializar_sistema_antigo(self):
        """Inicializa sistema antigo (sempre funciona)"""
        try:
            from app.claude_ai.claude_real_integration import processar_com_claude_real
            self.processar_consulta_real = processar_com_claude_real
            self.sistema_ativo = "antigo"
            logger.info("✅ Sistema Claude AI ANTIGO ativado")
        except Exception as e:
            logger.error(f"❌ ERRO CRÍTICO: Sistema antigo também falhou: {e}")
            self.sistema_ativo = "nenhum"
    
    def diagnosticar_sistema(self) -> Dict[str, Any]:
        """Executa diagnóstico completo do sistema ativo"""
        diagnostico = {
            'sistema_ativo': self.sistema_ativo,
            'timestamp': __import__('datetime').datetime.now().isoformat(),
            'problemas': [],
            'componentes': {},
            'recomendacoes': []
        }
        
        if self.sistema_ativo == "novo":
            diagnostico.update(self._diagnosticar_sistema_novo())
        elif self.sistema_ativo == "antigo":
            diagnostico.update(self._diagnosticar_sistema_antigo())
        else:
            diagnostico['problemas'].append("CRÍTICO: Nenhum sistema disponível")
        
        return diagnostico
    
    def _diagnosticar_sistema_novo(self) -> Dict[str, Any]:
        """Diagnóstico específico do sistema novo"""
        result = {
            'componentes': {},
            'problemas': [],
            'recomendacoes': []
        }
        
        # Testar componentes principais
        componentes_teste = [
            ('Learning Core', 'app.claude_ai_novo.learners.learning_core', 'get_lifelong_learning'),
            ('Security Guard', 'app.claude_ai_novo.security.security_guard', 'get_security_guard'),
            ('Orchestrators', 'app.claude_ai_novo.orchestrators.orchestrator_manager', 'get_orchestrator_manager'),
            ('Analyzers', 'app.claude_ai_novo.analyzers.analyzer_manager', 'get_analyzer_manager'),
        ]
        
        for nome, modulo, funcao in componentes_teste:
            try:
                mod = __import__(modulo, fromlist=[funcao])
                func = getattr(mod, funcao)
                instance = func()
                result['componentes'][nome] = f"✅ {type(instance).__name__}"
            except Exception as e:
                result['componentes'][nome] = f"❌ {str(e)[:50]}..."
                result['problemas'].append(f"{nome}: {e}")
        
        # Analisar problemas
        if result['problemas']:
            result['recomendacoes'].append("Corrigir imports e dependências")
            result['recomendacoes'].append("Verificar se todas as tabelas existem no banco")
        
        return result
    
    def _diagnosticar_sistema_antigo(self) -> Dict[str, Any]:
        """Diagnóstico específico do sistema antigo"""
        return {
            'componentes': {'Sistema Antigo': '✅ Funcional'},
            'problemas': [],
            'recomendacoes': ['Sistema antigo está funcionando normalmente']
        }
    
    async def processar_consulta(self, consulta: str, user_context: Optional[Dict] = None) -> str:
        """Processa consulta usando o sistema ativo (com diagnóstico)"""
        
        if self.sistema_ativo == "novo":
            try:
                # Sistema novo - verificar se é assíncrono
                if hasattr(self.claude, 'process_query'):
                    result = await self.claude.process_query(consulta, user_context)
                else:
                    # Fallback para método síncrono
                    result = str(self.claude.get_system_status())
                
                return str(result) if result is not None else "Resposta não disponível"
                
            except Exception as e:
                logger.error(f"❌ Erro no sistema novo: {e}")
                # Fallback automático para sistema antigo
                return await self._processar_com_antigo(consulta, user_context)
            
        elif self.sistema_ativo == "antigo":
            return await self._processar_com_antigo(consulta, user_context)
        else:
            return "❌ Nenhum sistema Claude AI disponível"
    
    async def _processar_com_antigo(self, consulta: str, user_context: Optional[Dict] = None) -> str:
        """Processa com sistema antigo (sempre funciona)"""
        try:
            result = self.processar_consulta_real(consulta, user_context)
            return str(result) if result is not None else "Resposta não disponível"
        except Exception as e:
            logger.error(f"❌ Erro no sistema antigo: {e}")
            return f"❌ Erro no processamento: {str(e)}"
    
    def forcar_sistema_novo(self) -> Dict[str, Any]:
        """Força uso do sistema novo e retorna diagnóstico"""
        logger.info("🔄 Forçando ativação do sistema novo...")
        
        self.usar_sistema_novo = True
        success = self._inicializar_sistema_novo()
        
        diagnostico = self.diagnosticar_sistema()
        diagnostico['forced_activation'] = success
        
        return diagnostico
    
    def alternar_sistema(self):
        """Alterna entre sistema antigo e novo"""
        if self.sistema_ativo == "novo":
            self._inicializar_sistema_antigo()
        else:
            self.forcar_sistema_novo()
        
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
        logger.error(f"❌ Erro na transição: {e}")
        return f"❌ Erro no sistema de transição: {e}"

def diagnosticar_claude_ai() -> Dict[str, Any]:
    """Função de conveniência para diagnóstico completo"""
    transition = get_claude_transition()
    return transition.diagnosticar_sistema()
