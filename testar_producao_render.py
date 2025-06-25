#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
🌐 TESTE DO SISTEMA EM PRODUÇÃO - RENDER
Testa funcionalidades do Claude AI em produção
"""

import requests
import json
from datetime import datetime
from colorama import init, Fore, Style

# Inicializar colorama
init()

# URL de produção
PROD_URL = "https://sistema-fretes.onrender.com"

class TestadorProducao:
    """Testa sistema em produção no Render"""
    
    def __init__(self):
        self.session = requests.Session()
        self.resultados = []
        
    def testar_disponibilidade(self):
        """Testa se o sistema está online"""
        print(f"\n{Fore.CYAN}🌐 TESTE 1: Disponibilidade do Sistema{Style.RESET_ALL}")
        
        try:
            response = self.session.get(PROD_URL, timeout=10)
            if response.status_code == 200:
                print(f"{Fore.GREEN}✅ Sistema online em produção!{Style.RESET_ALL}")
                print(f"   URL: {PROD_URL}")
                return True
            else:
                print(f"{Fore.RED}❌ Sistema retornou status: {response.status_code}{Style.RESET_ALL}")
                return False
        except Exception as e:
            print(f"{Fore.RED}❌ Erro ao acessar sistema: {e}{Style.RESET_ALL}")
            return False
    
    def testar_rotas_claude(self):
        """Testa rotas do Claude AI"""
        print(f"\n{Fore.CYAN}🤖 TESTE 2: Rotas Claude AI{Style.RESET_ALL}")
        
        rotas = [
            ("/claude-ai/", "Claude AI Principal"),
            ("/claude-ai/dashboard-executivo", "Dashboard Executivo"),
            ("/claude-ai/dashboard", "Dashboard MCP"),
            ("/claude-ai/advanced-dashboard", "Dashboard Avançado"),
            ("/claude-ai/advanced-feedback-interface", "Interface Feedback")
        ]
        
        sucesso = 0
        for rota, nome in rotas:
            try:
                response = self.session.get(f"{PROD_URL}{rota}", timeout=10)
                # 302 = redirect para login (normal para rotas protegidas)
                if response.status_code in [200, 302]:
                    print(f"{Fore.GREEN}✅ {nome}: OK (Status: {response.status_code}){Style.RESET_ALL}")
                    sucesso += 1
                else:
                    print(f"{Fore.RED}❌ {nome}: Erro {response.status_code}{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}❌ {nome}: Timeout/Erro{Style.RESET_ALL}")
        
        print(f"\n📊 Rotas funcionais: {sucesso}/{len(rotas)}")
        return sucesso == len(rotas)
    
    def testar_api_endpoints(self):
        """Testa endpoints da API"""
        print(f"\n{Fore.CYAN}🔌 TESTE 3: API Endpoints{Style.RESET_ALL}")
        
        # Nota: Alguns endpoints podem requerer autenticação
        endpoints = [
            ("/claude-ai/api/health", "Health Check"),
            ("/claude-ai/api/suggestions", "Sugestões"),
            ("/claude-ai/api/advanced-analytics", "Analytics")
        ]
        
        for endpoint, nome in endpoints:
            try:
                response = self.session.get(f"{PROD_URL}{endpoint}", timeout=10)
                if response.status_code in [200, 401, 302]:  # 401/302 = precisa login
                    print(f"{Fore.GREEN}✅ {nome}: Endpoint existe (Status: {response.status_code}){Style.RESET_ALL}")
                else:
                    print(f"{Fore.YELLOW}⚠️ {nome}: Status {response.status_code}{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}❌ {nome}: Erro de conexão{Style.RESET_ALL}")
    
    def info_producao(self):
        """Mostra informações sobre o ambiente de produção"""
        print(f"\n{Fore.CYAN}📋 INFORMAÇÕES DE PRODUÇÃO{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        
        print(f"\n🌐 URL Base: {Fore.BLUE}{PROD_URL}{Style.RESET_ALL}")
        print(f"\n📍 URLs Importantes:")
        print(f"   • Login: {PROD_URL}/login")
        print(f"   • Claude AI: {PROD_URL}/claude-ai/real")
        print(f"   • Dashboard: {PROD_URL}/claude-ai/dashboard-executivo")
        print(f"   • Feedback: {PROD_URL}/claude-ai/advanced-feedback-interface")
        
        print(f"\n⚙️ Configurações Esperadas:")
        print(f"   • ANTHROPIC_API_KEY: Configurada no Render")
        print(f"   • PostgreSQL: Banco de produção")
        print(f"   • Redis: Se disponível")
        print(f"   • SSL: HTTPS ativo")
        
        print(f"\n🔐 Autenticação:")
        print(f"   • Sistema requer login")
        print(f"   • CSRF tokens ativos")
        print(f"   • Sessões persistentes")

def main():
    """Função principal"""
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}🌐 TESTE EM PRODUÇÃO - SISTEMA CLAUDE AI{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"\n🔗 Testando: {Fore.YELLOW}{PROD_URL}{Style.RESET_ALL}")
    
    testador = TestadorProducao()
    
    # Executar testes
    online = testador.testar_disponibilidade()
    
    if online:
        testador.testar_rotas_claude()
        testador.testar_api_endpoints()
    
    # Informações
    testador.info_producao()
    
    # Instruções finais
    print(f"\n{Fore.CYAN}🧪 PRÓXIMOS PASSOS:{Style.RESET_ALL}")
    print(f"\n1. Faça login no sistema:")
    print(f"   {Fore.BLUE}{PROD_URL}/login{Style.RESET_ALL}")
    
    print(f"\n2. Teste o Claude AI:")
    print(f"   {Fore.BLUE}{PROD_URL}/claude-ai/real{Style.RESET_ALL}")
    
    print(f"\n3. Execute testes manuais:")
    print(f"   • Faça consultas variadas")
    print(f"   • Teste grupos empresariais (Assai, Atacadão)")
    print(f"   • Gere relatórios Excel")
    print(f"   • Envie feedback (positivo/negativo)")
    
    print(f"\n4. Para testes automatizados com login:")
    print(f"   {Fore.YELLOW}python testar_claude_ai_completo.py --prod{Style.RESET_ALL}")
    print(f"   {Fore.YELLOW}python testar_human_in_loop_web.py --prod{Style.RESET_ALL}")
    
    print(f"\n{Fore.GREEN}✅ Teste de produção concluído!{Style.RESET_ALL}")

if __name__ == "__main__":
    main() 