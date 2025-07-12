#!/usr/bin/env python3
"""
🚀 ATIVADOR RÁPIDO DO CLAUDE API REAL
=====================================

Script para ativar rapidamente o Claude API real no sistema.
Execute este script para transformar respostas genéricas em análises inteligentes.
"""

import os
import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))


def ativar_claude_real():
    """Modifica o SessionOrchestrator para usar Claude API real"""
    
    print("🚀 ATIVANDO CLAUDE API REAL")
    print("=" * 60)
    
    # Caminho do arquivo
    session_orch_path = Path("app/claude_ai_novo/orchestrators/session_orchestrator.py")
    
    print(f"📄 Modificando: {session_orch_path}")
    
    # Ler o arquivo
    with open(session_orch_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Backup
    backup_path = session_orch_path.with_suffix('.py.backup')
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"💾 Backup salvo em: {backup_path}")
    
    # Modificações
    modifications = [
        {
            'description': 'Importar anthropic',
            'find': 'import logging',
            'replace': 'import logging\nimport anthropic\nimport json'
        },
        {
            'description': 'Adicionar cliente Claude',
            'find': 'def __init__(self):',
            'replace': '''def __init__(self):
        """Inicializa o orquestrador de sessão"""
        self.sessions = {}
        self.integration_manager = None
        
        # Inicializar Claude API real se disponível
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if api_key:
            try:
                self.claude_client = anthropic.Anthropic(api_key=api_key)
                self.use_claude_real = True
                logger.info("✅ Claude API real ativada!")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao inicializar Claude: {e}")
                self.claude_client = None
                self.use_claude_real = False
        else:
            self.claude_client = None
            self.use_claude_real = False'''
        },
        {
            'description': 'Modificar process_query para usar Claude real',
            'find': 'async def process_query(',
            'replace': '''async def _process_with_claude_real(self, query: str, context: Dict) -> str:
        """Processa query usando Claude API real"""
        try:
            # Preparar contexto enriquecido
            enriched_prompt = f"""
Você é um assistente especializado em análise de dados de fretes e logística.

CONTEXTO DO SISTEMA:
- Usuário: {context.get('username', 'N/A')}
- Domínio detectado: {context.get('domain', 'geral')}
- Dados disponíveis: {context.get('data_summary', 'Sistema de fretes completo')}

CONSULTA DO USUÁRIO:
{query}

INSTRUÇÕES:
1. Responda em português brasileiro
2. Seja específico e use números quando disponível
3. Forneça insights acionáveis
4. Mantenha um tom profissional mas amigável
"""
            
            # Chamar Claude API
            response = self.claude_client.messages.create(
                model="claude-3-sonnet-20241022",
                max_tokens=1000,
                temperature=0.7,
                messages=[{
                    "role": "user",
                    "content": enriched_prompt
                }]
            )
            
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Erro ao chamar Claude API: {e}")
            # Fallback para resposta genérica
            return self._generate_generic_response(query, context)
    
    async def process_query('''
        }
    ]
    
    # Aplicar modificações
    for mod in modifications:
        if mod['find'] in content:
            content = content.replace(mod['find'], mod['replace'], 1)
            print(f"✅ {mod['description']}")
        else:
            print(f"⚠️ Não encontrado: {mod['description']}")
    
    # Adicionar método para usar Claude no process_query
    process_query_new = '''
        # Se tiver Claude real disponível, usar
        if self.use_claude_real and self.claude_client:
            try:
                response_text = await self._process_with_claude_real(query, context)
                
                return {
                    'success': True,
                    'result': response_text,
                    'query': query,
                    'intent': intent_info.get('intent', 'general'),
                    'source': 'claude_api_real',
                    'model': 'claude-3-sonnet-20241022'
                }
            except Exception as e:
                logger.warning(f"Fallback para genérico: {e}")
        
        # Fallback para resposta genérica existente'''
    
    # Inserir antes do return com resposta genérica
    marker = "# Gerar resposta baseada no tipo"
    if marker in content:
        content = content.replace(marker, process_query_new + "\n\n" + marker)
        print("✅ Integração com Claude real adicionada ao process_query")
    
    # Salvar arquivo modificado
    with open(session_orch_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("\n" + "=" * 60)
    print("✅ CLAUDE API REAL ATIVADA COM SUCESSO!")
    print("\n📋 Próximos passos:")
    print("1. Faça commit das alterações")
    print("2. Deploy no Render")
    print("3. Teste com queries reais")
    print("\n💡 Exemplo de teste:")
    print('   "Qual o status das entregas do Atacadão em SP?"')
    print("\n🎯 Resultado esperado:")
    print("   Resposta específica com dados reais ao invés de genérica")


if __name__ == "__main__":
    ativar_claude_real() 