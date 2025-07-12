#!/usr/bin/env python3
"""
🔧 CORRIGIR RESPOSTA GENÉRICA
============================

O problema: SessionOrchestrator está retornando respostas genéricas
em vez de usar dados reais do banco.

Solução: Fazer o SessionOrchestrator usar o MainOrchestrator
que tem acesso aos dados reais.
"""

import os
import sys
from pathlib import Path

# Adicionar diretório raiz ao path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

# Configurar variáveis de ambiente
os.environ['USE_NEW_CLAUDE_SYSTEM'] = 'true'

def corrigir_session_orchestrator():
    """Corrige o SessionOrchestrator para usar dados reais"""
    
    print("🔧 CORRIGINDO RESPOSTA GENÉRICA DO CLAUDE AI NOVO\n")
    
    # Ler arquivo
    file_path = Path(__file__).parent / "orchestrators" / "session_orchestrator.py"
    
    print(f"📄 Arquivo: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verificar se já foi corrigido
    if "# Usar MainOrchestrator para dados reais" in content:
        print("✅ Arquivo já foi corrigido!")
        return
    
    # Substituição 1: Adicionar property para MainOrchestrator
    old_property = """    @property
    def integration_manager(self):"""
    
    new_property = """    @property
    def main_orchestrator(self):
        \"\"\"Lazy loading do MainOrchestrator\"\"\"
        if not hasattr(self, '_main_orchestrator') or self._main_orchestrator is None:
            try:
                from app.claude_ai_novo.orchestrators.main_orchestrator import get_main_orchestrator
                self._main_orchestrator = get_main_orchestrator()
                logger.info("🎯 MainOrchestrator integrado ao SessionOrchestrator")
            except ImportError as e:
                logger.warning(f"⚠️ MainOrchestrator não disponível: {e}")
                self._main_orchestrator = False
        return self._main_orchestrator if self._main_orchestrator is not False else None
    
    @property
    def integration_manager(self):"""
    
    content = content.replace(old_property, new_property)
    
    # Substituição 2: Modificar _process_general_inquiry para usar MainOrchestrator
    old_method = '''    def _process_general_inquiry(self, query: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Processa consultas gerais"""
        return {
            'success': True,
            'result': f"ℹ️ Consulta Geral: '{query}' - Sistema Claude AI Novo está operacional e processando consultas. Como posso ajudá-lo com informações específicas sobre fretes, entregas, pedidos ou relatórios?",
            'query': query,
            'intent': 'geral',
            'source': 'session_orchestrator'
        }'''
    
    new_method = '''    def _process_general_inquiry(self, query: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Processa consultas gerais"""
        # Usar MainOrchestrator para dados reais
        if self.main_orchestrator:
            try:
                # MainOrchestrator tem acesso a todos os módulos
                result = self.main_orchestrator.execute_workflow(
                    'intelligent_query',
                    {'query': query, 'context': context or {}}
                )
                
                # Se tem resposta válida, retornar
                if isinstance(result, dict) and result.get('response'):
                    return {
                        'success': True,
                        'result': result['response'],
                        'query': query,
                        'intent': 'geral',
                        'source': 'main_orchestrator',
                        'data': result.get('data', {})
                    }
            except Exception as e:
                logger.error(f"Erro ao usar MainOrchestrator: {e}")
        
        # Fallback para resposta genérica
        return {
            'success': True,
            'result': f"ℹ️ Consulta Geral: '{query}' - Sistema Claude AI Novo está operacional e processando consultas. Como posso ajudá-lo com informações específicas sobre fretes, entregas, pedidos ou relatórios?",
            'query': query,
            'intent': 'geral',
            'source': 'session_orchestrator'
        }'''
    
    content = content.replace(old_method, new_method)
    
    # Salvar arquivo
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Arquivo corrigido com sucesso!")
    print("\n📝 MUDANÇAS APLICADAS:")
    print("1. Adicionado property main_orchestrator")
    print("2. Modificado _process_general_inquiry para usar MainOrchestrator")
    print("3. MainOrchestrator tem acesso aos dados reais via loaders")
    
    # Testar importação
    print("\n🧪 Testando importação...")
    try:
        from app.claude_ai_novo.orchestrators.session_orchestrator import SessionOrchestrator
        print("✅ Importação funcionando!")
    except Exception as e:
        print(f"❌ Erro na importação: {e}")

if __name__ == "__main__":
    corrigir_session_orchestrator() 