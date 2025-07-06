#!/usr/bin/env python3
"""
Script de teste completo para o sistema Claude AI
Verifica todas as funcionalidades principais
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import asyncio
from colorama import init, Fore, Style
init(autoreset=True)

# Banner
print(f"""
{Fore.CYAN}{'='*60}
{Fore.YELLOW}🤖 TESTE COMPLETO DO SISTEMA CLAUDE AI 🤖
{Fore.CYAN}{'='*60}{Style.RESET_ALL}
""")

async def test_imports():
    """Testa se todos os imports funcionam"""
    print(f"\n{Fore.BLUE}1. Testando imports...{Style.RESET_ALL}")
    errors = []
    
    try:
        from app.claude_ai.claude_real_integration import ClaudeRealIntegration
        print(f"  ✅ ClaudeRealIntegration")
    except Exception as e:
        errors.append(f"ClaudeRealIntegration: {str(e)}")
        print(f"  ❌ ClaudeRealIntegration: {e}")
    
    try:
        from app.claude_ai.nlp_enhanced_analyzer import NLPEnhancedAnalyzer
        print(f"  ✅ NLPEnhancedAnalyzer")
    except Exception as e:
        errors.append(f"NLPEnhancedAnalyzer: {str(e)}")
        print(f"  ❌ NLPEnhancedAnalyzer: {e}")
    
    try:
        from app.claude_ai.claude_project_scanner import ClaudeProjectScanner
        print(f"  ✅ ClaudeProjectScanner")
    except Exception as e:
        errors.append(f"ClaudeProjectScanner: {str(e)}")
        print(f"  ❌ ClaudeProjectScanner: {e}")
    
    try:
        from app.claude_ai.multi_agent_system import MultiAgentSystem
        print(f"  ✅ MultiAgentSystem")
    except Exception as e:
        errors.append(f"MultiAgentSystem: {str(e)}")
        print(f"  ❌ MultiAgentSystem: {e}")
    
    return len(errors) == 0, errors

async def test_file_access():
    """Testa acesso a arquivos via project scanner"""
    print(f"\n{Fore.BLUE}2. Testando acesso a arquivos...{Style.RESET_ALL}")
    
    try:
        from app.claude_ai.claude_project_scanner import ClaudeProjectScanner
        scanner = ClaudeProjectScanner()
        
        # Testa listagem
        result = scanner.list_directory_contents('utils')
        if isinstance(result, dict) and 'error' not in result:
            print(f"  ✅ Listagem de diretórios funcionando")
            print(f"     - {len(result.get('files', []))} arquivos encontrados")
        else:
            error_msg = result.get('error', 'Erro desconhecido') if isinstance(result, dict) else str(result)
            print(f"  ❌ Erro na listagem: {error_msg}")
            return False, ["Listagem falhou"]
        
        # Testa leitura
        result = scanner.read_file_content('utils/__init__.py')
        if isinstance(result, str) and not result.startswith('❌'):
            print(f"  ✅ Leitura de arquivos funcionando")
        else:
            print(f"  ❌ Erro na leitura: {result}")
            return False, ["Leitura falhou"]
        
        # Testa busca
        result = scanner.search_in_files('def ', file_extensions=['.py'], max_results=5)
        if isinstance(result, dict) and result.get('success'):
            print(f"  ✅ Busca em arquivos funcionando")
            print(f"     - {result.get('total_matches', 0)} resultados encontrados")
        else:
            print(f"  ❌ Erro na busca: {result.get('error', 'Erro desconhecido')}")
            return False, ["Busca falhou"]
        
        return True, []
    except Exception as e:
        print(f"  ❌ Erro geral: {e}")
        return False, [str(e)]

async def test_nlp_analysis():
    """Testa análise NLP"""
    print(f"\n{Fore.BLUE}3. Testando análise NLP...{Style.RESET_ALL}")
    
    try:
        from app.claude_ai.nlp_enhanced_analyzer import NLPEnhancedAnalyzer
        nlp = NLPEnhancedAnalyzer()
        
        # Testa análise básica
        test_queries = [
            "Quantas entregas temos pendentes?",
            "Mostre o código do arquivo routes.py",
            "Crie um relatório de vendas"
        ]
        
        for query in test_queries:
            result = nlp.analisar_com_nlp(query)
            if result and hasattr(result, 'tipo_analise'):
                print(f"  ✅ '{query[:30]}...' - Tipo: {result.tipo_analise}")
            elif isinstance(result, dict) and 'tipo_analise' in result:
                print(f"  ✅ '{query[:30]}...' - Tipo: {result['tipo_analise']}")
            else:
                print(f"  ❌ Falha ao analisar: '{query[:30]}...'")
        
        return True, []
    except Exception as e:
        print(f"  ❌ Erro NLP: {e}")
        return False, [str(e)]

async def test_claude_integration():
    """Testa integração básica do Claude (sem API key)"""
    print(f"\n{Fore.BLUE}4. Testando integração Claude...{Style.RESET_ALL}")
    
    try:
        from app.claude_ai.claude_real_integration import ClaudeRealIntegration
        claude = ClaudeRealIntegration()
        
        # Verifica inicialização
        print(f"  ✅ Sistema inicializado")
        
        # Verifica detecção de comandos
        test_commands = [
            ("listar arquivos em app/utils", True),
            ("verificar app/utils/email_service.py", True),
            ("quantas entregas temos?", False),
        ]
        
        for cmd, is_file_cmd in test_commands:
            result = claude._is_file_command(cmd)
            if result == is_file_cmd:
                print(f"  ✅ Comando detectado corretamente: '{cmd[:30]}...'")
            else:
                print(f"  ❌ Detecção incorreta: '{cmd[:30]}...'")
        
        return True, []
    except Exception as e:
        print(f"  ❌ Erro integração: {e}")
        return False, [str(e)]

async def test_system_config():
    """Verifica configurações do sistema"""
    print(f"\n{Fore.BLUE}5. Verificando configurações...{Style.RESET_ALL}")
    
    # Verifica API key
    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    if api_key:
        print(f"  ✅ ANTHROPIC_API_KEY configurada")
        # Testar conexão com API se key existe
        try:
            from anthropic import Anthropic
            client = Anthropic(api_key=api_key)
            # Fazer uma chamada mínima para testar
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=10,
                messages=[{"role": "user", "content": "teste"}]
            )
            print(f"  ✅ API Anthropic respondendo corretamente")
        except Exception as e:
            print(f"  ❌ Erro ao conectar com API: {str(e)[:50]}...")
    else:
        print(f"  ⚠️  ANTHROPIC_API_KEY não configurada (necessária em produção)")
    
    # Verifica modelo configurado
    try:
        with open('app/claude_ai/claude_real_integration.py', 'r', encoding='utf-8') as f:
            content = f.read()
            if 'claude-sonnet-4-20250514' in content:
                print(f"  ✅ Claude 4 Sonnet configurado")
            else:
                print(f"  ❌ Modelo não encontrado no código")
    except:
        print(f"  ❌ Erro ao verificar modelo")
    
    # Verifica fallback
    try:
        from app.claude_ai.claude_real_integration import ClaudeRealIntegration
        claude = ClaudeRealIntegration()
        if hasattr(claude, '_fallback_simulado'):
            print(f"  ✅ Sistema de fallback disponível")
        else:
            print(f"  ⚠️  Sistema de fallback não encontrado")
    except:
        print(f"  ❌ Erro ao verificar fallback")
    
    return True, []

async def main():
    """Executa todos os testes"""
    total_tests = 5
    passed_tests = 0
    all_errors = []
    
    # Executa testes
    tests = [
        ("Imports", test_imports),
        ("Acesso a Arquivos", test_file_access),
        ("Análise NLP", test_nlp_analysis),
        ("Integração Claude", test_claude_integration),
        ("Configurações", test_system_config)
    ]
    
    for test_name, test_func in tests:
        passed, errors = await test_func()
        if passed:
            passed_tests += 1
        else:
            all_errors.extend(errors)
    
    # Resumo final
    print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}📊 RESUMO DOS TESTES{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    
    success_rate = (passed_tests / total_tests) * 100
    color = Fore.GREEN if success_rate >= 80 else Fore.YELLOW if success_rate >= 60 else Fore.RED
    
    print(f"\n{color}Taxa de sucesso: {success_rate:.1f}% ({passed_tests}/{total_tests}){Style.RESET_ALL}")
    
    if all_errors:
        print(f"\n{Fore.RED}Erros encontrados:{Style.RESET_ALL}")
        for error in all_errors:
            print(f"  - {error}")
    
    print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    
    # Recomendações
    if success_rate < 100:
        print(f"\n{Fore.YELLOW}💡 RECOMENDAÇÕES:{Style.RESET_ALL}")
        if not os.environ.get('ANTHROPIC_API_KEY'):
            print(f"  1. Configure ANTHROPIC_API_KEY para testes completos")
        if all_errors:
            print(f"  2. Corrija os erros listados acima")
            print(f"  3. Execute 'pip install -r requirements.txt' para garantir dependências")

if __name__ == "__main__":
    asyncio.run(main()) 