#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
🔄 TESTE INTERATIVO HUMAN-IN-THE-LOOP
Simula interações de usuário para testar aprendizado
"""

import requests
import json
import time
from datetime import datetime
from colorama import init, Fore, Style

# Inicializar colorama
init()

# Configurações
import argparse

# Parse argumentos de linha de comando
parser = argparse.ArgumentParser(description='Testa Human-in-the-Loop')
parser.add_argument('--prod', action='store_true', help='Usar servidor de produção')
parser.add_argument('--url', type=str, help='URL customizada do servidor')
args = parser.parse_args()

# Determinar URL base
if args.url:
    BASE_URL = args.url
elif args.prod:
    BASE_URL = "https://sistema-fretes.onrender.com"
else:
    BASE_URL = "http://localhost:5000"
    
SESSION = requests.Session()

class TestadorHumanInLoop:
    """Testa Human-in-the-Loop via interface web"""
    
    def __init__(self):
        self.cookie_jar = {}
        
    def login(self, email="admin@teste.com", senha="admin123"):
        """Faz login no sistema"""
        print(f"{Fore.YELLOW}🔐 Fazendo login...{Style.RESET_ALL}")
        
        # Primeiro, pegar CSRF token
        response = SESSION.get(f"{BASE_URL}/login")
        if response.status_code != 200:
            print(f"{Fore.RED}❌ Erro ao acessar página de login{Style.RESET_ALL}")
            return False
        
        # Simular login (ajustar conforme seu sistema)
        # Este é um exemplo genérico
        print(f"{Fore.GREEN}✅ Login simulado (ajustar para seu sistema){Style.RESET_ALL}")
        return True
    
    def testar_fluxo_feedback(self):
        """Testa fluxo completo de feedback"""
        print(f"\n{Fore.CYAN}🔄 TESTE: Fluxo Human-in-the-Loop{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        
        # Cenário 1: Consulta inicial
        print(f"\n{Fore.YELLOW}📝 Cenário 1: Consulta com resposta incorreta{Style.RESET_ALL}")
        
        consulta1 = {
            "query": "Mostre entregas do Assai",
            "user_context": {
                "perfil": "vendedor",
                "vendedor_codigo": "VEND001"
            }
        }
        
        print(f"→ Enviando: '{consulta1['query']}'")
        response1 = self.enviar_consulta(consulta1)
        
        if response1:
            print(f"{Fore.GREEN}✅ Resposta recebida{Style.RESET_ALL}")
            
            # Simular feedback negativo
            feedback1 = {
                "query": consulta1["query"],
                "response": response1.get("response", ""),
                "rating": 2,
                "feedback_type": "wrong_data",
                "comment": "Eu queria ver TODAS as entregas, não só do Assai"
            }
            
            print(f"\n{Fore.YELLOW}❌ Enviando feedback negativo...{Style.RESET_ALL}")
            self.enviar_feedback(feedback1)
            
        # Aguardar processamento
        time.sleep(2)
        
        # Cenário 2: Repetir consulta similar
        print(f"\n{Fore.YELLOW}📝 Cenário 2: Consulta similar após feedback{Style.RESET_ALL}")
        
        consulta2 = {
            "query": "Mostre entregas", 
            "user_context": consulta1["user_context"]
        }
        
        print(f"→ Enviando: '{consulta2['query']}'")
        response2 = self.enviar_consulta(consulta2)
        
        if response2:
            print(f"{Fore.GREEN}✅ Sistema deve mostrar TODAS as entregas agora{Style.RESET_ALL}")
            
            # Feedback positivo
            feedback2 = {
                "query": consulta2["query"],
                "response": response2.get("response", ""),
                "rating": 5,
                "feedback_type": "perfect",
                "comment": "Agora sim, era isso que eu queria!"
            }
            
            print(f"\n{Fore.GREEN}✅ Enviando feedback positivo...{Style.RESET_ALL}")
            self.enviar_feedback(feedback2)
        
        # Cenário 3: Testar detecção de correção
        print(f"\n{Fore.YELLOW}📝 Cenário 3: Detecção de correção do usuário{Style.RESET_ALL}")
        
        consulta3 = {
            "query": "Não era isso que pedi, quero apenas entregas atrasadas",
            "user_context": consulta1["user_context"]
        }
        
        print(f"→ Enviando correção: '{consulta3['query']}'")
        response3 = self.enviar_consulta(consulta3)
        
        if response3:
            print(f"{Fore.GREEN}✅ Sistema deve detectar correção e ajustar{Style.RESET_ALL}")
    
    def enviar_consulta(self, dados):
        """Envia consulta para o Claude AI"""
        try:
            response = SESSION.post(
                f"{BASE_URL}/claude-ai/real",
                json=dados,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"{Fore.RED}❌ Erro: Status {response.status_code}{Style.RESET_ALL}")
                return None
                
        except Exception as e:
            print(f"{Fore.RED}❌ Erro ao enviar consulta: {e}{Style.RESET_ALL}")
            return None
    
    def enviar_feedback(self, dados):
        """Envia feedback para o sistema"""
        try:
            response = SESSION.post(
                f"{BASE_URL}/claude-ai/api/advanced-feedback",
                json=dados,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                print(f"{Fore.GREEN}✅ Feedback registrado com sucesso{Style.RESET_ALL}")
                return True
            else:
                print(f"{Fore.RED}❌ Erro ao enviar feedback: {response.status_code}{Style.RESET_ALL}")
                return False
                
        except Exception as e:
            print(f"{Fore.RED}❌ Erro: {e}{Style.RESET_ALL}")
            return False
    
    def verificar_aprendizado(self):
        """Verifica se o sistema aprendeu com o feedback"""
        print(f"\n{Fore.CYAN}📊 VERIFICAÇÃO: Padrões de Aprendizado{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        
        try:
            response = SESSION.get(f"{BASE_URL}/claude-ai/api/advanced-analytics")
            
            if response.status_code == 200:
                dados = response.json()
                
                # Verificar feedback
                feedback_history = dados.get("feedback_stats", {})
                if feedback_history:
                    print(f"\n{Fore.GREEN}📈 Estatísticas de Feedback:{Style.RESET_ALL}")
                    print(f"   Total: {feedback_history.get('total', 0)}")
                    print(f"   Positivos: {feedback_history.get('positive', 0)}")
                    print(f"   Negativos: {feedback_history.get('negative', 0)}")
                
                # Verificar padrões
                patterns = dados.get("learning_patterns", [])
                if patterns:
                    print(f"\n{Fore.GREEN}🧠 Padrões Aprendidos:{Style.RESET_ALL}")
                    for i, pattern in enumerate(patterns[:3], 1):
                        print(f"   {i}. {pattern.get('pattern_type', 'N/A')}")
                        print(f"      Frequência: {pattern.get('frequency', 0)}")
                
                return True
                
        except Exception as e:
            print(f"{Fore.RED}❌ Erro ao verificar aprendizado: {e}{Style.RESET_ALL}")
            return False
    
    def testar_interface_feedback(self):
        """Instrui como testar interface manual"""
        print(f"\n{Fore.CYAN}🖥️ TESTE MANUAL: Interface de Feedback{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        
        print(f"\n{Fore.YELLOW}Passos para teste manual:{Style.RESET_ALL}")
        print(f"\n1. Acesse: {Fore.BLUE}{BASE_URL}/claude-ai/advanced-feedback-interface{Style.RESET_ALL}")
        print(f"\n2. Faça uma consulta qualquer:")
        print(f"   Exemplo: 'Quantas entregas estão atrasadas?'")
        print(f"\n3. Observe a resposta e avalie:")
        print(f"   {Fore.YELLOW}⭐⭐⭐⭐⭐{Style.RESET_ALL} - Clique nas estrelas")
        print(f"   - 1-2 estrelas = Ruim")
        print(f"   - 3 estrelas = Regular")
        print(f"   - 4-5 estrelas = Bom/Ótimo")
        print(f"\n4. Selecione o tipo de feedback:")
        print(f"   {Fore.GREEN}✅ Resposta Correta{Style.RESET_ALL}")
        print(f"   {Fore.RED}❌ Resposta Incorreta{Style.RESET_ALL}")
        print(f"   {Fore.YELLOW}⚠️ Parcialmente Correto{Style.RESET_ALL}")
        print(f"   {Fore.BLUE}💡 Sugestão de Melhoria{Style.RESET_ALL}")
        print(f"\n5. Adicione comentário (opcional)")
        print(f"\n6. Clique em 'Enviar Feedback'")
        print(f"\n7. Repita a consulta para ver se melhorou!")

def main():
    """Função principal"""
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}🔄 TESTE HUMAN-IN-THE-LOOP - SISTEMA CLAUDE AI{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"\n📍 Testando em: {Fore.YELLOW}{BASE_URL}{Style.RESET_ALL}")
    
    testador = TestadorHumanInLoop()
    
    # Verificar servidor
    print(f"\n{Fore.YELLOW}🔍 Verificando servidor...{Style.RESET_ALL}")
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code != 200:
            raise Exception("Servidor offline")
        print(f"{Fore.GREEN}✅ Servidor online!{Style.RESET_ALL}")
    except:
        print(f"{Fore.RED}❌ Servidor offline! Execute 'python run.py' primeiro.{Style.RESET_ALL}")
        return
    
    # Menu de opções
    while True:
        print(f"\n{Fore.CYAN}📋 MENU DE TESTES:{Style.RESET_ALL}")
        print(f"1. Testar fluxo automático de feedback")
        print(f"2. Verificar padrões de aprendizado")
        print(f"3. Instruções para teste manual")
        print(f"4. Sair")
        
        opcao = input(f"\n{Fore.YELLOW}Escolha uma opção (1-4): {Style.RESET_ALL}")
        
        if opcao == "1":
            testador.testar_fluxo_feedback()
        elif opcao == "2":
            testador.verificar_aprendizado()
        elif opcao == "3":
            testador.testar_interface_feedback()
        elif opcao == "4":
            print(f"\n{Fore.GREEN}✅ Teste finalizado!{Style.RESET_ALL}")
            break
        else:
            print(f"{Fore.RED}❌ Opção inválida!{Style.RESET_ALL}")

if __name__ == "__main__":
    main() 