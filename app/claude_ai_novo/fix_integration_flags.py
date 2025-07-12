#!/usr/bin/env python3
"""
🔧 FIX INTEGRATION FLAGS
========================

Corrige o IntegrationManager para retornar as flags corretas
de data_provider_available e claude_integration_available.
"""

import os
import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))


def fix_integration_manager():
    """Corrige o método get_system_status do IntegrationManager"""
    
    file_path = Path("app/claude_ai_novo/integration/integration_manager.py")
    
    print("🔧 Corrigindo IntegrationManager...")
    
    # Ler o arquivo
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Encontrar o método get_system_status
    old_method = '''    def get_system_status(self) -> Dict[str, Any]:
        """
        Retorna status do sistema de integração.
        
        Returns:
            Dict com status detalhado
        """
        return {
            "orchestrator_manager": self.orchestrator_manager is not None,
            "orchestrator_loaded": self.system_metrics['orchestrator_loaded'],
            "orchestrator_active": self.system_metrics['orchestrator_active'],
            "initialization_time": self.system_metrics['initialization_time'],
            "last_health_check": self.system_metrics['last_health_check'],
            "modules_available": 21,  # Todos via orchestrator
            "modules_active": 21 if self.orchestrator_manager else 0,
            "integration_score": 1.0 if self.orchestrator_manager else 0.0,
            "ready_for_operation": self.orchestrator_manager is not None
        }'''
    
    new_method = '''    def get_system_status(self) -> Dict[str, Any]:
        """
        Retorna status do sistema de integração.
        
        Returns:
            Dict com status detalhado
        """
        # Verificar recursos reais disponíveis
        data_provider_available = False
        claude_integration_available = False
        
        # Verificar se temos variáveis de ambiente configuradas
        if os.environ.get('DATABASE_URL'):
            data_provider_available = True
        
        if os.environ.get('ANTHROPIC_API_KEY'):
            claude_integration_available = True
        
        return {
            "orchestrator_manager": self.orchestrator_manager is not None,
            "orchestrator_loaded": self.system_metrics['orchestrator_loaded'],
            "orchestrator_active": self.system_metrics['orchestrator_active'],
            "initialization_time": self.system_metrics['initialization_time'],
            "last_health_check": self.system_metrics['last_health_check'],
            "modules_available": 21,  # Todos via orchestrator
            "modules_active": 21 if self.orchestrator_manager else 0,
            "integration_score": 1.0 if self.orchestrator_manager else 0.0,
            "ready_for_operation": self.orchestrator_manager is not None,
            # Flags para recursos reais
            "data_provider_available": data_provider_available,
            "claude_integration_available": claude_integration_available
        }'''
    
    # Adicionar import do os no início se não existir
    if 'import os' not in content:
        # Adicionar após os outros imports
        import_section = content.split('\n\n')[0]
        new_import_section = import_section + '\nimport os'
        content = content.replace(import_section, new_import_section)
    
    # Substituir o método
    if old_method in content:
        content = content.replace(old_method, new_method)
        print("✅ Método get_system_status corrigido!")
    else:
        print("⚠️ Método não encontrado no formato esperado")
        print("Tentando correção alternativa...")
        
        # Tentar encontrar e substituir de forma mais flexível
        start_idx = content.find('def get_system_status(self)')
        if start_idx != -1:
            # Encontrar o próximo método ou o fim da classe
            next_method_idx = content.find('\n    def ', start_idx + 1)
            if next_method_idx == -1:
                next_method_idx = content.find('\n\n', start_idx + 200)
            
            if next_method_idx != -1:
                content = content[:start_idx] + new_method.strip() + '\n' + content[next_method_idx:]
                print("✅ Método corrigido com abordagem alternativa!")
    
    # Salvar o arquivo
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ IntegrationManager atualizado com sucesso!")
    print("\n📊 Agora o sistema detectará automaticamente:")
    print("   - DATABASE_URL → data_provider_available")
    print("   - ANTHROPIC_API_KEY → claude_integration_available")


def test_fix():
    """Testa se a correção funcionou"""
    print("\n🧪 Testando correção...")
    
    try:
        # Simular variáveis de ambiente
        os.environ['DATABASE_URL'] = 'postgresql://test'
        os.environ['ANTHROPIC_API_KEY'] = 'sk-test'
        
        # Importar e testar
        from app.claude_ai_novo.integration.integration_manager import IntegrationManager
        
        manager = IntegrationManager()
        status = manager.get_system_status()
        
        print("\n✅ Status do sistema:")
        print(f"   - data_provider_available: {status.get('data_provider_available', 'NÃO ENCONTRADO')}")
        print(f"   - claude_integration_available: {status.get('claude_integration_available', 'NÃO ENCONTRADO')}")
        
        # Limpar variáveis de teste
        del os.environ['DATABASE_URL']
        del os.environ['ANTHROPIC_API_KEY']
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")


if __name__ == "__main__":
    fix_integration_manager()
    test_fix() 