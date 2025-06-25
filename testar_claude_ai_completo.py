#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
🧪 SCRIPT DE TESTE AUTOMATIZADO - SISTEMA CLAUDE AI
Executa testes das principais funcionalidades
"""

import os
import sys
import time
import json
import requests
from datetime import datetime
from colorama import init, Fore, Style

# Inicializar colorama para Windows
init()

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configurações
import argparse

# Parse argumentos de linha de comando
parser = argparse.ArgumentParser(description='Testa Sistema Claude AI')
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

class TestadorClaudeAI:
    """Classe para testar funcionalidades do Claude AI"""
    
    def __init__(self):
        self.resultados = []
        self.total_testes = 0
        self.testes_aprovados = 0
        
    def log_teste(self, nome, resultado, detalhes=""):
        """Registra resultado do teste"""
        self.total_testes += 1
        if resultado:
            self.testes_aprovados += 1
            print(f"{Fore.GREEN}✅ {nome}{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}❌ {nome}{Style.RESET_ALL}")
            if detalhes:
                print(f"   {Fore.YELLOW}Detalhes: {detalhes}{Style.RESET_ALL}")
        
        self.resultados.append({
            "teste": nome,
            "resultado": resultado,
            "detalhes": detalhes,
            "timestamp": datetime.now().isoformat()
        })
    
    def testar_servidor_online(self):
        """Testa se o servidor está online"""
        try:
            response = SESSION.get(f"{BASE_URL}/")
            return response.status_code == 200
        except:
            return False
    
    def testar_analise_inteligente(self):
        """Testa análise inteligente de consultas"""
        print(f"\n{Fore.CYAN}🧠 TESTE 1: Análise Inteligente{Style.RESET_ALL}")
        
        # Importar analisador
        try:
            from app.claude_ai.intelligent_query_analyzer import get_intelligent_analyzer
            analyzer = get_intelligent_analyzer()
            
            # Casos de teste
            casos = [
                {
                    "consulta": "Quantas entregas do Assai estão atrasadas?",
                    "intencao_esperada": "QUANTIDADE",
                    "cliente_esperado": "Assai"
                },
                {
                    "consulta": "Como está a situação do Atacadão em SP?",
                    "intencao_esperada": "STATUS",
                    "uf_esperada": "SP"
                },
                {
                    "consulta": "Detalhes da NF 123456",
                    "intencao_esperada": "DETALHAMENTO",
                    "nf_esperada": "123456"
                }
            ]
            
            for caso in casos:
                try:
                    resultado = analyzer.analisar_consulta_inteligente(caso["consulta"])
                    
                    # Verificar intenção
                    intencao_ok = resultado.intencao_principal.value == caso["intencao_esperada"]
                    
                    # Verificar entidades
                    entidades_ok = True
                    if "cliente_esperado" in caso:
                        clientes = resultado.entidades_detectadas.get("clientes", [])
                        entidades_ok = any(caso["cliente_esperado"].lower() in str(c).lower() for c in clientes)
                    
                    sucesso = intencao_ok and entidades_ok
                    detalhes = f"Confiança: {resultado.confianca_interpretacao:.1%}"
                    
                    self.log_teste(f"Análise: {caso['consulta'][:30]}...", sucesso, detalhes)
                    
                except Exception as e:
                    self.log_teste(f"Análise: {caso['consulta'][:30]}...", False, str(e))
            
        except Exception as e:
            self.log_teste("Importar analisador inteligente", False, str(e))
    
    def testar_grupos_empresariais(self):
        """Testa detecção de grupos empresariais"""
        print(f"\n{Fore.CYAN}🏢 TESTE 2: Grupos Empresariais{Style.RESET_ALL}")
        
        try:
            from app.utils.grupo_empresarial import GrupoEmpresarial
            detector = GrupoEmpresarial()
            
            # Testar detecção por CNPJ
            casos = [
                ("06.057.223/0001-00", "Rede Assai"),
                ("75.315.333/0001-00", "Grupo Atacadão"),
                ("45.543.915/0001-00", "Grupo Carrefour")
            ]
            
            for cnpj, grupo_esperado in casos:
                resultado = detector.detectar_grupo(cnpj=cnpj)
                sucesso = resultado is not None and grupo_esperado in str(resultado.get('nome', ''))
                detalhes = f"Detectado: {resultado.get('nome') if resultado else 'Nenhum'}"
                self.log_teste(f"Grupo CNPJ {cnpj[:11]}...", sucesso, detalhes)
                
        except Exception as e:
            self.log_teste("Sistema de grupos empresariais", False, str(e))
    
    def testar_human_in_loop(self):
        """Testa sistema Human-in-the-Loop"""
        print(f"\n{Fore.CYAN}🔄 TESTE 3: Human-in-the-Loop{Style.RESET_ALL}")
        
        try:
            from app.claude_ai.human_in_loop_learning import HumanInLoopLearning
            sistema = HumanInLoopLearning()
            
            # Capturar feedback
            feedback = sistema.capture_user_feedback(
                query="Teste de feedback",
                response="Resposta teste",
                feedback="Ótimo resultado!",
                feedback_type="positive",
                severity=5,
                context={"teste": True}
            )
            
            self.log_teste("Captura de feedback", feedback is not None, "Feedback registrado")
            
            # Verificar aprendizado
            patterns = sistema.get_learning_patterns(limit=1)
            self.log_teste("Padrões de aprendizado", len(patterns) > 0, f"{len(patterns)} padrões")
            
        except Exception as e:
            self.log_teste("Sistema Human-in-the-Loop", False, str(e))
    
    def testar_multi_agent(self):
        """Testa sistema Multi-Agent"""
        print(f"\n{Fore.CYAN}🤖 TESTE 4: Multi-Agent System{Style.RESET_ALL}")
        
        try:
            from app.claude_ai.multi_agent_system import get_multi_agent_system
            sistema = get_multi_agent_system()
            
            # Testar inicialização
            self.log_teste("Inicialização Multi-Agent", sistema is not None, "Sistema criado")
            
            # Testar agents disponíveis
            if hasattr(sistema, 'agents'):
                num_agents = len(sistema.agents)
                self.log_teste("Agents disponíveis", num_agents >= 3, f"{num_agents} agents")
            
        except Exception as e:
            self.log_teste("Sistema Multi-Agent", False, str(e))
    
    def testar_excel_generator(self):
        """Testa gerador de Excel"""
        print(f"\n{Fore.CYAN}📊 TESTE 5: Excel Generator{Style.RESET_ALL}")
        
        try:
            from app.claude_ai.excel_generator import ExcelGenerator
            generator = ExcelGenerator()
            
            # Verificar detecção de comandos Excel
            comandos = [
                "Gere um relatório Excel",
                "Exportar para planilha",
                "Criar xlsx com dados"
            ]
            
            for cmd in comandos:
                is_excel = generator._is_excel_command(cmd)
                self.log_teste(f"Detectar comando: '{cmd}'", is_excel, f"Excel: {is_excel}")
                
        except Exception as e:
            self.log_teste("Sistema Excel Generator", False, str(e))
    
    def testar_sugestoes_inteligentes(self):
        """Testa sistema de sugestões"""
        print(f"\n{Fore.CYAN}💡 TESTE 6: Sugestões Inteligentes{Style.RESET_ALL}")
        
        try:
            from app.claude_ai.suggestion_engine import SuggestionEngine
            engine = SuggestionEngine()
            
            # Gerar sugestões
            sugestoes = engine.generate_smart_suggestions(
                user_context={"perfil": "vendedor"},
                conversation_history=[]
            )
            
            self.log_teste("Gerar sugestões", len(sugestoes) > 0, f"{len(sugestoes)} sugestões")
            
            # Testar personalização
            if sugestoes:
                tem_categorias = all('categoria' in s for s in sugestoes)
                self.log_teste("Categorização", tem_categorias, "Todas categorizadas")
                
        except Exception as e:
            self.log_teste("Sistema de sugestões", False, str(e))
    
    def testar_contexto_conversacional(self):
        """Testa contexto conversacional"""
        print(f"\n{Fore.CYAN}💬 TESTE 7: Contexto Conversacional{Style.RESET_ALL}")
        
        try:
            from app.claude_ai.conversation_context import ConversationContext
            contexto = ConversationContext()
            
            # Adicionar mensagens
            contexto.add_message("user123", "user", "Teste 1")
            contexto.add_message("user123", "assistant", "Resposta 1")
            
            # Recuperar contexto
            historico = contexto.get_context("user123")
            self.log_teste("Armazenar contexto", len(historico) == 2, f"{len(historico)} mensagens")
            
            # Limpar contexto
            contexto.clear_context("user123")
            historico_limpo = contexto.get_context("user123")
            self.log_teste("Limpar contexto", len(historico_limpo) == 0, "Contexto limpo")
            
        except Exception as e:
            self.log_teste("Sistema de contexto", False, str(e))
    
    def testar_dashboards(self):
        """Testa disponibilidade dos dashboards"""
        print(f"\n{Fore.CYAN}📊 TESTE 8: Dashboards{Style.RESET_ALL}")
        
        dashboards = [
            ("/claude-ai/dashboard-executivo", "Dashboard Executivo"),
            ("/claude-ai/advanced-dashboard", "Dashboard Avançado"),
            ("/claude-ai/dashboard", "Dashboard MCP")
        ]
        
        for url, nome in dashboards:
            try:
                response = SESSION.get(f"{BASE_URL}{url}")
                sucesso = response.status_code in [200, 302]  # 302 = redirect login
                self.log_teste(nome, sucesso, f"Status: {response.status_code}")
            except Exception as e:
                self.log_teste(nome, False, str(e))
    
    def gerar_relatorio(self):
        """Gera relatório final dos testes"""
        print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}📊 RELATÓRIO FINAL{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        
        taxa_sucesso = (self.testes_aprovados / self.total_testes * 100) if self.total_testes > 0 else 0
        
        # Cor baseada na taxa
        if taxa_sucesso >= 80:
            cor = Fore.GREEN
        elif taxa_sucesso >= 60:
            cor = Fore.YELLOW
        else:
            cor = Fore.RED
        
        print(f"\n📈 Taxa de Sucesso: {cor}{taxa_sucesso:.1f}%{Style.RESET_ALL}")
        print(f"✅ Testes Aprovados: {self.testes_aprovados}/{self.total_testes}")
        
        # Salvar relatório
        with open("relatorio_testes_claude_ai.json", "w", encoding="utf-8") as f:
            json.dump({
                "data_execucao": datetime.now().isoformat(),
                "taxa_sucesso": taxa_sucesso,
                "total_testes": self.total_testes,
                "testes_aprovados": self.testes_aprovados,
                "resultados": self.resultados
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Relatório salvo em: relatorio_testes_claude_ai.json")
        
        # Conclusão
        if taxa_sucesso >= 80:
            print(f"\n{Fore.GREEN}🎉 SISTEMA CLAUDE AI APROVADO!{Style.RESET_ALL}")
        else:
            print(f"\n{Fore.YELLOW}⚠️ SISTEMA PRECISA DE AJUSTES{Style.RESET_ALL}")

def main():
    """Função principal"""
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}🧪 TESTE AUTOMATIZADO - SISTEMA CLAUDE AI{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"\n📍 Testando em: {Fore.YELLOW}{BASE_URL}{Style.RESET_ALL}")
    
    testador = TestadorClaudeAI()
    
    # Verificar servidor
    print(f"\n{Fore.YELLOW}🔍 Verificando servidor...{Style.RESET_ALL}")
    if not testador.testar_servidor_online():
        print(f"{Fore.RED}❌ Servidor offline! Execute 'python run.py' primeiro.{Style.RESET_ALL}")
        return
    
    print(f"{Fore.GREEN}✅ Servidor online!{Style.RESET_ALL}")
    
    # Executar testes
    testador.testar_analise_inteligente()
    testador.testar_grupos_empresariais()
    testador.testar_human_in_loop()
    testador.testar_multi_agent()
    testador.testar_excel_generator()
    testador.testar_sugestoes_inteligentes()
    testador.testar_contexto_conversacional()
    testador.testar_dashboards()
    
    # Gerar relatório
    testador.gerar_relatorio()

if __name__ == "__main__":
    main() 