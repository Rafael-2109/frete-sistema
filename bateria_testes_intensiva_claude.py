#!/usr/bin/env python3
"""
🧪 BATERIA INTENSIVA DE TESTES - CLAUDE AI
Teste completo e detalhado de TODAS as funcionalidades
"""

import sys
import os
import importlib
import traceback
import time
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class BateriaTestesIntensiva:
    """Bateria intensiva de testes para sistemas Claude AI"""
    
    def __init__(self):
        self.resultados = {
            'sistema_atual': {},
            'sistema_novo': {},
            'testes_funcionais': {},
            'testes_performance': {},
            'testes_integracao': {},
            'comparacao_detalhada': {}
        }
        
        # Consultas de teste mais diversificadas
        self.consultas_basicas = [
            "Quantas entregas do Assai em dezembro?",
            "Gere um relatório Excel das entregas atrasadas",
            "Qual o status dos embarques hoje?",
            "Análise de fretes por transportadora",
            "Pedidos pendentes de faturamento"
        ]
        
        # Consultas específicas para testar funcionalidades
        self.consultas_excel = [
            "Exportar dados do Carrefour para Excel",
            "Gerar planilha de entregas atrasadas",
            "Relatório completo em Excel dos fretes",
            "Criar planilha de análise de pedidos"
        ]
        
        self.consultas_nlp = [
            "Qual cliente tem mais problemas?",
            "Analise padrões de atraso nas entregas",
            "Identifique tendências nos dados",
            "Extraia insights dos embarques"
        ]
        
        self.consultas_contexto = [
            ("Entregas do Assai em janeiro", "E em fevereiro?"),
            ("Fretes da transportadora X", "Qual o valor total?"),
            ("Pedidos atrasados", "Quantos são urgentes?")
        ]
        
        self.consultas_desenvolvimento = [
            "Leia o arquivo app/models.py",
            "Descubra a estrutura do projeto",
            "Analise o código da aplicação",
            "Liste todos os módulos disponíveis"
        ]
    
    def executar_bateria_completa(self):
        """Executa bateria completa de testes"""
        print("🧪 BATERIA INTENSIVA DE TESTES - CLAUDE AI")
        print("=" * 80)
        print("🕒 Tempo estimado: 10-15 minutos")
        print("🔍 Testes: Funcional, Performance, Integração, NLP, Excel, Contexto")
        print()
        
        inicio = time.time()
        
        # 1. Testes de inicialização e módulos
        self.testar_inicializacao_modulos()
        
        # 2. Testes funcionais básicos
        self.testar_funcionalidades_basicas()
        
        # 3. Testes específicos por categoria
        self.testar_funcionalidades_excel()
        self.testar_funcionalidades_nlp()
        self.testar_contexto_conversacional()
        self.testar_funcionalidades_desenvolvimento()
        
        # 4. Testes de integração
        self.testar_integracao_banco()
        
        # 5. Testes de performance
        self.testar_performance()
        
        # 6. Testes de recuperação de erro
        self.testar_recuperacao_erros()
        
        # 7. Comparação detalhada
        self.comparar_sistemas_detalhado()
        
        fim = time.time()
        tempo_total = fim - inicio
        
        # 8. Relatório final
        self.gerar_relatorio_completo(tempo_total)
    
    def testar_inicializacao_modulos(self):
        """Testa inicialização e presença de módulos específicos"""
        print("🔧 TESTE 1: INICIALIZAÇÃO E MÓDULOS")
        print("-" * 60)
        
        # Sistema Atual
        print("\n🤖 SISTEMA ATUAL:")
        try:
            from app.claude_ai.claude_real_integration import ClaudeRealIntegration
            sistema_atual = ClaudeRealIntegration()
            
            # Lista completa de módulos para testar
            modulos_testar = [
                'multi_agent_system',
                'advanced_ai_system', 
                'nlp_analyzer',
                'intelligent_analyzer',
                'enhanced_claude',
                'suggestion_engine',
                'ml_models',
                'human_learning',
                'input_validator',
                'ai_config',
                'vendedor_analyzer',
                'geral_analyzer',
                'alert_engine',
                'mapeamento_semantico',
                'mcp_connector',
                'system_alerts',
                'ai_logger',
                'intelligent_cache',
                'project_scanner',
                'client',
                'redis_disponivel'
            ]
            
            modulos_presentes = []
            modulos_funcionais = []
            
            for modulo in modulos_testar:
                presente = hasattr(sistema_atual, modulo)
                if presente:
                    obj = getattr(sistema_atual, modulo)
                    funcional = obj is not None
                    modulos_presentes.append(modulo)
                    if funcional:
                        modulos_funcionais.append(modulo)
                    print(f"   {'✅' if funcional else '⚠️'} {modulo}: {'Funcional' if funcional else 'Presente mas None'}")
                else:
                    print(f"   ❌ {modulo}: Ausente")
            
            # Testar métodos específicos
            metodos_testar = [
                'processar_consulta_real',
                '_processar_comando_excel',
                '_processar_comando_desenvolvimento',
                '_is_excel_command',
                '_is_dev_command'
            ]
            
            metodos_funcionais = []
            for metodo in metodos_testar:
                if hasattr(sistema_atual, metodo):
                    metodos_funcionais.append(metodo)
                    print(f"   ✅ Método {metodo}: Presente")
                else:
                    print(f"   ❌ Método {metodo}: Ausente")
            
            self.resultados['sistema_atual'] = {
                'inicializacao': True,
                'modulos_presentes': modulos_presentes,
                'modulos_funcionais': modulos_funcionais,
                'metodos_funcionais': metodos_funcionais,
                'total_modulos': len(modulos_funcionais),
                'modo_real': sistema_atual.modo_real,
                'client_ativo': sistema_atual.client is not None
            }
            
        except Exception as e:
            print(f"❌ ERRO SISTEMA ATUAL: {e}")
            self.resultados['sistema_atual'] = {'inicializacao': False, 'erro': str(e)}
            traceback.print_exc()
        
        # Sistema Novo
        print("\n🆕 SISTEMA NOVO:")
        try:
            from app.claude_ai_novo.core.claude_integration import ClaudeRealIntegration as ClaudeNovo
            sistema_novo = ClaudeNovo()
            
            # Lista de módulos do sistema novo
            modulos_novo = [
                'excel_commands',
                'database_loader',
                'conversation_context',
                'human_learning',
                'lifelong_learning',
                'suggestion_engine',
                'intention_analyzer',
                'query_analyzer',
                'redis_cache',
                'intelligent_cache',
                'client',
                'redis_disponivel'
            ]
            
            modulos_presentes_novo = []
            modulos_funcionais_novo = []
            
            for modulo in modulos_novo:
                presente = hasattr(sistema_novo, modulo)
                if presente:
                    obj = getattr(sistema_novo, modulo)
                    funcional = obj is not None
                    modulos_presentes_novo.append(modulo)
                    if funcional:
                        modulos_funcionais_novo.append(modulo)
                    print(f"   {'✅' if funcional else '⚠️'} {modulo}: {'Funcional' if funcional else 'Presente mas None'}")
                else:
                    print(f"   ❌ {modulo}: Ausente")
            
            # Testar métodos específicos do novo sistema
            metodos_novo = [
                'processar_consulta_real',
                '_analisar_intencao',
                '_recuperar_contexto_conversacional',
                '_verificar_cache_redis',
                '_aplicar_lifelong_learning'
            ]
            
            metodos_funcionais_novo = []
            for metodo in metodos_novo:
                if hasattr(sistema_novo, metodo):
                    metodos_funcionais_novo.append(metodo)
                    print(f"   ✅ Método {metodo}: Presente")
                else:
                    print(f"   ❌ Método {metodo}: Ausente")
            
            self.resultados['sistema_novo'] = {
                'inicializacao': True,
                'modulos_presentes': modulos_presentes_novo,
                'modulos_funcionais': modulos_funcionais_novo,
                'metodos_funcionais': metodos_funcionais_novo,
                'total_modulos': len(modulos_funcionais_novo),
                'modo_real': sistema_novo.modo_real,
                'client_ativo': sistema_novo.client is not None
            }
            
        except Exception as e:
            print(f"❌ ERRO SISTEMA NOVO: {e}")
            self.resultados['sistema_novo'] = {'inicializacao': False, 'erro': str(e)}
            traceback.print_exc()
    
    def testar_funcionalidades_basicas(self):
        """Testa funcionalidades básicas de consulta"""
        print("\n📝 TESTE 2: FUNCIONALIDADES BÁSICAS")
        print("-" * 60)
        
        for sistema_nome, sistema_key in [("ATUAL", "sistema_atual"), ("NOVO", "sistema_novo")]:
            print(f"\n🤖 TESTANDO {sistema_nome}:")
            
            if not self.resultados[sistema_key].get('inicializacao', False):
                print("   ❌ Sistema não inicializado - Pulando testes")
                continue
            
            try:
                if sistema_key == "sistema_atual":
                    from app.claude_ai.claude_real_integration import ClaudeRealIntegration
                    sistema = ClaudeRealIntegration()
                else:
                    from app.claude_ai_novo.core.claude_integration import ClaudeRealIntegration as ClaudeNovo
                    sistema = ClaudeNovo()
                
                resultados_consultas = {}
                
                for i, consulta in enumerate(self.consultas_basicas, 1):
                    print(f"   Teste {i}: {consulta[:40]}...")
                    
                    try:
                        inicio = time.time()
                        resposta = sistema.processar_consulta_real(consulta)
                        fim = time.time()
                        tempo = fim - inicio
                        
                        sucesso = (
                            len(resposta) > 20 and 
                            "erro" not in resposta.lower() and
                            "exception" not in resposta.lower()
                        )
                        
                        resultados_consultas[consulta] = {
                            'sucesso': sucesso,
                            'tempo_resposta': tempo,
                            'tamanho_resposta': len(resposta),
                            'contem_dados': any(palavra in resposta.lower() for palavra in ['total', 'quantidade', 'dados', 'registros'])
                        }
                        
                        print(f"      {'✅' if sucesso else '❌'} {tempo:.2f}s - {len(resposta)} chars")
                        
                    except Exception as e:
                        resultados_consultas[consulta] = {
                            'sucesso': False,
                            'erro': str(e),
                            'tempo_resposta': 0
                        }
                        print(f"      ❌ ERRO: {str(e)[:50]}")
                
                self.resultados['testes_funcionais'][sistema_key] = resultados_consultas
                
            except Exception as e:
                print(f"   ❌ ERRO GERAL: {e}")
                self.resultados['testes_funcionais'][sistema_key] = {'erro': str(e)}
    
    def testar_funcionalidades_excel(self):
        """Testa funcionalidades específicas de Excel"""
        print("\n📊 TESTE 3: FUNCIONALIDADES EXCEL")
        print("-" * 60)
        
        for sistema_nome, sistema_key in [("ATUAL", "sistema_atual"), ("NOVO", "sistema_novo")]:
            print(f"\n📈 TESTANDO EXCEL {sistema_nome}:")
            
            if not self.resultados[sistema_key].get('inicializacao', False):
                continue
            
            try:
                if sistema_key == "sistema_atual":
                    from app.claude_ai.claude_real_integration import ClaudeRealIntegration
                    sistema = ClaudeRealIntegration()
                else:
                    from app.claude_ai_novo.core.claude_integration import ClaudeRealIntegration as ClaudeNovo
                    sistema = ClaudeNovo()
                
                resultados_excel = {}
                
                for consulta in self.consultas_excel:
                    try:
                        # Testar detecção de comando Excel
                        if hasattr(sistema, '_is_excel_command'):
                            eh_excel = sistema._is_excel_command(consulta)
                            print(f"   📊 Detecção Excel: {'✅' if eh_excel else '❌'} - {consulta[:30]}")
                        elif hasattr(sistema, 'excel_commands') and sistema.excel_commands:
                            eh_excel = sistema.excel_commands.is_excel_command(consulta)
                            print(f"   📊 Detecção Excel: {'✅' if eh_excel else '❌'} - {consulta[:30]}")
                        else:
                            eh_excel = False
                            print(f"   📊 Detecção Excel: ❌ Módulo não encontrado - {consulta[:30]}")
                        
                        # Testar processamento
                        resposta = sistema.processar_consulta_real(consulta)
                        contem_excel = any(palavra in resposta.lower() for palavra in ['excel', 'planilha', '.xlsx', 'relatório'])
                        
                        resultados_excel[consulta] = {
                            'detectou_excel': eh_excel,
                            'resposta_contem_excel': contem_excel,
                            'processou_com_sucesso': len(resposta) > 20
                        }
                        
                    except Exception as e:
                        resultados_excel[consulta] = {
                            'erro': str(e),
                            'detectou_excel': False
                        }
                        print(f"   ❌ ERRO: {str(e)[:40]}")
                
                if 'testes_excel' not in self.resultados:
                    self.resultados['testes_excel'] = {}
                self.resultados['testes_excel'][sistema_key] = resultados_excel
                
            except Exception as e:
                print(f"   ❌ ERRO GERAL EXCEL: {e}")
    
    def testar_funcionalidades_nlp(self):
        """Testa funcionalidades de NLP"""
        print("\n🔬 TESTE 4: FUNCIONALIDADES NLP")
        print("-" * 60)
        
        for sistema_nome, sistema_key in [("ATUAL", "sistema_atual"), ("NOVO", "sistema_novo")]:
            print(f"\n🧠 TESTANDO NLP {sistema_nome}:")
            
            if not self.resultados[sistema_key].get('inicializacao', False):
                continue
            
            try:
                if sistema_key == "sistema_atual":
                    from app.claude_ai.claude_real_integration import ClaudeRealIntegration
                    sistema = ClaudeRealIntegration()
                else:
                    from app.claude_ai_novo.core.claude_integration import ClaudeRealIntegration as ClaudeNovo
                    sistema = ClaudeNovo()
                
                resultados_nlp = {}
                
                # Testar presença de analisadores NLP
                nlp_presente = False
                if hasattr(sistema, 'nlp_analyzer') and sistema.nlp_analyzer:
                    nlp_presente = True
                    print("   ✅ NLP Analyzer: Presente e ativo")
                elif hasattr(sistema, 'intention_analyzer') and sistema.intention_analyzer:
                    nlp_presente = True
                    print("   ✅ Intention Analyzer: Presente e ativo")
                else:
                    print("   ❌ Analisadores NLP: Não encontrados")
                
                # Testar consultas que requerem análise inteligente
                for consulta in self.consultas_nlp:
                    try:
                        resposta = sistema.processar_consulta_real(consulta)
                        
                        # Verificar se a resposta demonstra análise inteligente
                        palavras_analise = ['análise', 'padrão', 'tendência', 'insight', 'conclusão', 'porque', 'indica']
                        tem_analise = any(palavra in resposta.lower() for palavra in palavras_analise)
                        
                        resultados_nlp[consulta] = {
                            'processou': len(resposta) > 20,
                            'demonstrou_analise': tem_analise,
                            'tamanho_resposta': len(resposta)
                        }
                        
                        print(f"   {'✅' if tem_analise else '⚠️'} {consulta[:30]}... - {'Análise detectada' if tem_analise else 'Resposta simples'}")
                        
                    except Exception as e:
                        resultados_nlp[consulta] = {'erro': str(e)}
                        print(f"   ❌ ERRO: {str(e)[:40]}")
                
                if 'testes_nlp' not in self.resultados:
                    self.resultados['testes_nlp'] = {}
                self.resultados['testes_nlp'][sistema_key] = {
                    'nlp_presente': nlp_presente,
                    'resultados_consultas': resultados_nlp
                }
                
            except Exception as e:
                print(f"   ❌ ERRO GERAL NLP: {e}")
    
    def testar_contexto_conversacional(self):
        """Testa funcionalidades de contexto conversacional"""
        print("\n🗣️ TESTE 5: CONTEXTO CONVERSACIONAL")
        print("-" * 60)
        
        for sistema_nome, sistema_key in [("ATUAL", "sistema_atual"), ("NOVO", "sistema_novo")]:
            print(f"\n💬 TESTANDO CONTEXTO {sistema_nome}:")
            
            if not self.resultados[sistema_key].get('inicializacao', False):
                continue
            
            try:
                if sistema_key == "sistema_atual":
                    from app.claude_ai.claude_real_integration import ClaudeRealIntegration
                    sistema = ClaudeRealIntegration()
                else:
                    from app.claude_ai_novo.core.claude_integration import ClaudeRealIntegration as ClaudeNovo
                    sistema = ClaudeNovo()
                
                resultados_contexto = {}
                
                # Verificar se o sistema tem contexto conversacional
                tem_contexto = False
                if hasattr(sistema, 'conversation_context') and sistema.conversation_context:
                    tem_contexto = True
                    print("   ✅ Conversation Context: Presente e ativo")
                else:
                    print("   ❌ Conversation Context: Não encontrado")
                
                # Testar conversas sequenciais
                for i, (pergunta1, pergunta2) in enumerate(self.consultas_contexto, 1):
                    try:
                        print(f"   Teste {i}: Conversa sequencial")
                        
                        # Primeira pergunta
                        resposta1 = sistema.processar_consulta_real(pergunta1)
                        print(f"      P1: {pergunta1}")
                        print(f"      R1: {resposta1[:50]}...")
                        
                        # Segunda pergunta (dependente do contexto)
                        resposta2 = sistema.processar_consulta_real(pergunta2)
                        print(f"      P2: {pergunta2}")
                        print(f"      R2: {resposta2[:50]}...")
                        
                        # Verificar se a segunda resposta mantém contexto
                        contextual = (
                            len(resposta2) > 20 and
                            "não entendi" not in resposta2.lower() and
                            "mais específico" not in resposta2.lower()
                        )
                        
                        resultados_contexto[f"conversa_{i}"] = {
                            'pergunta1': pergunta1,
                            'pergunta2': pergunta2,
                            'manteve_contexto': contextual,
                            'tamanho_resposta1': len(resposta1),
                            'tamanho_resposta2': len(resposta2)
                        }
                        
                        print(f"      {'✅' if contextual else '❌'} Contexto {'mantido' if contextual else 'perdido'}")
                        
                    except Exception as e:
                        resultados_contexto[f"conversa_{i}"] = {'erro': str(e)}
                        print(f"      ❌ ERRO: {str(e)[:40]}")
                
                if 'testes_contexto' not in self.resultados:
                    self.resultados['testes_contexto'] = {}
                self.resultados['testes_contexto'][sistema_key] = {
                    'tem_contexto': tem_contexto,
                    'resultados_conversas': resultados_contexto
                }
                
            except Exception as e:
                print(f"   ❌ ERRO GERAL CONTEXTO: {e}")
    
    def testar_funcionalidades_desenvolvimento(self):
        """Testa funcionalidades de desenvolvimento/projeto"""
        print("\n🔧 TESTE 6: FUNCIONALIDADES DESENVOLVIMENTO")
        print("-" * 60)
        
        for sistema_nome, sistema_key in [("ATUAL", "sistema_atual"), ("NOVO", "sistema_novo")]:
            print(f"\n⚙️ TESTANDO DEV {sistema_nome}:")
            
            if not self.resultados[sistema_key].get('inicializacao', False):
                continue
            
            try:
                if sistema_key == "sistema_atual":
                    from app.claude_ai.claude_real_integration import ClaudeRealIntegration
                    sistema = ClaudeRealIntegration()
                else:
                    from app.claude_ai_novo.core.claude_integration import ClaudeRealIntegration as ClaudeNovo
                    sistema = ClaudeNovo()
                
                resultados_dev = {}
                
                # Verificar se tem funcionalidades de desenvolvimento
                tem_dev = False
                if hasattr(sistema, 'project_scanner') and sistema.project_scanner:
                    tem_dev = True
                    print("   ✅ Project Scanner: Presente e ativo")
                elif hasattr(sistema, '_is_dev_command'):
                    tem_dev = True
                    print("   ✅ Dev Commands: Método presente")
                else:
                    print("   ❌ Funcionalidades Dev: Não encontradas")
                
                # Testar comandos de desenvolvimento
                for consulta in self.consultas_desenvolvimento:
                    try:
                        # Testar detecção de comando dev
                        eh_dev = False
                        if hasattr(sistema, '_is_dev_command'):
                            eh_dev = sistema._is_dev_command(consulta)
                        
                        resposta = sistema.processar_consulta_real(consulta)
                        
                        # Verificar se a resposta contém informações técnicas
                        termos_tecnicos = ['class', 'def', 'import', 'function', 'module', 'arquivo', 'código']
                        tem_info_tecnica = any(termo in resposta.lower() for termo in termos_tecnicos)
                        
                        resultados_dev[consulta] = {
                            'detectou_dev': eh_dev,
                            'tem_info_tecnica': tem_info_tecnica,
                            'processou_com_sucesso': len(resposta) > 20
                        }
                        
                        print(f"   {'✅' if tem_info_tecnica else '⚠️'} {consulta[:30]}... - {'Info técnica' if tem_info_tecnica else 'Resposta genérica'}")
                        
                    except Exception as e:
                        resultados_dev[consulta] = {'erro': str(e)}
                        print(f"   ❌ ERRO: {str(e)[:40]}")
                
                if 'testes_dev' not in self.resultados:
                    self.resultados['testes_dev'] = {}
                self.resultados['testes_dev'][sistema_key] = {
                    'tem_funcionalidades_dev': tem_dev,
                    'resultados_comandos': resultados_dev
                }
                
            except Exception as e:
                print(f"   ❌ ERRO GERAL DEV: {e}")
    
    def testar_integracao_banco(self):
        """Testa integração com banco de dados"""
        print("\n🗄️ TESTE 7: INTEGRAÇÃO BANCO DE DADOS")
        print("-" * 60)
        # Implementar testes de integração com banco
        # Por enquanto, placeholder
        self.resultados['testes_integracao'] = {'placeholder': True}
    
    def testar_performance(self):
        """Testa performance dos sistemas"""
        print("\n⚡ TESTE 8: PERFORMANCE")
        print("-" * 60)
        
        consulta_teste = "Qual o status do sistema?"
        
        for sistema_nome, sistema_key in [("ATUAL", "sistema_atual"), ("NOVO", "sistema_novo")]:
            print(f"\n🏃 TESTANDO PERFORMANCE {sistema_nome}:")
            
            if not self.resultados[sistema_key].get('inicializacao', False):
                continue
            
            try:
                if sistema_key == "sistema_atual":
                    from app.claude_ai.claude_real_integration import ClaudeRealIntegration
                    sistema = ClaudeRealIntegration()
                else:
                    from app.claude_ai_novo.core.claude_integration import ClaudeRealIntegration as ClaudeNovo
                    sistema = ClaudeNovo()
                
                tempos = []
                sucessos = 0
                
                for i in range(5):  # 5 execuções para média
                    try:
                        inicio = time.time()
                        resposta = sistema.processar_consulta_real(consulta_teste)
                        fim = time.time()
                        tempo = fim - inicio
                        
                        tempos.append(tempo)
                        if len(resposta) > 10:
                            sucessos += 1
                        
                        print(f"   Execução {i+1}: {tempo:.3f}s")
                        
                    except Exception as e:
                        print(f"   Execução {i+1}: ERRO - {str(e)[:30]}")
                
                if tempos:
                    tempo_medio = sum(tempos) / len(tempos)
                    tempo_min = min(tempos)
                    tempo_max = max(tempos)
                    
                    print(f"   📊 Média: {tempo_medio:.3f}s | Min: {tempo_min:.3f}s | Max: {tempo_max:.3f}s")
                    print(f"   ✅ Taxa sucesso: {sucessos}/5 ({sucessos*20}%)")
                else:
                    tempo_medio = 0
                    sucessos = 0
                
                if 'performance' not in self.resultados:
                    self.resultados['performance'] = {}
                self.resultados['performance'][sistema_key] = {
                    'tempo_medio': tempo_medio,
                    'tempo_min': tempo_min if tempos else 0,
                    'tempo_max': tempo_max if tempos else 0,
                    'taxa_sucesso': sucessos / 5,
                    'execucoes_realizadas': len(tempos)
                }
                
            except Exception as e:
                print(f"   ❌ ERRO PERFORMANCE: {e}")
    
    def testar_recuperacao_erros(self):
        """Testa recuperação de erros"""
        print("\n🚨 TESTE 9: RECUPERAÇÃO DE ERROS")
        print("-" * 60)
        
        consultas_erro = [
            "",  # Consulta vazia
            "askdjaskdj askdja skdj",  # Consulta sem sentido
            "SELECT * FROM tabela_inexistente",  # Comando SQL inválido
            "A" * 10000  # Consulta muito longa
        ]
        
        for sistema_nome, sistema_key in [("ATUAL", "sistema_atual"), ("NOVO", "sistema_novo")]:
            print(f"\n⚠️ TESTANDO ERROS {sistema_nome}:")
            
            if not self.resultados[sistema_key].get('inicializacao', False):
                continue
            
            try:
                if sistema_key == "sistema_atual":
                    from app.claude_ai.claude_real_integration import ClaudeRealIntegration
                    sistema = ClaudeRealIntegration()
                else:
                    from app.claude_ai_novo.core.claude_integration import ClaudeRealIntegration as ClaudeNovo
                    sistema = ClaudeNovo()
                
                recuperacao_erros = {}
                
                for i, consulta in enumerate(consultas_erro, 1):
                    try:
                        resposta = sistema.processar_consulta_real(consulta)
                        
                        # Verificar se o sistema se recuperou graciosamente
                        recuperou = (
                            len(resposta) > 5 and
                            "traceback" not in resposta.lower() and
                            "exception" not in resposta.lower()
                        )
                        
                        recuperacao_erros[f"erro_{i}"] = {
                            'recuperou_graciosamente': recuperou,
                            'tamanho_resposta': len(resposta)
                        }
                        
                        print(f"   Erro {i}: {'✅' if recuperou else '❌'} {'Recuperação OK' if recuperou else 'Erro exposto'}")
                        
                    except Exception as e:
                        recuperacao_erros[f"erro_{i}"] = {
                            'recuperou_graciosamente': False,
                            'excecao_lancada': str(e)
                        }
                        print(f"   Erro {i}: ❌ Exceção lançada")
                
                if 'recuperacao_erros' not in self.resultados:
                    self.resultados['recuperacao_erros'] = {}
                self.resultados['recuperacao_erros'][sistema_key] = recuperacao_erros
                
            except Exception as e:
                print(f"   ❌ ERRO GERAL: {e}")
    
    def comparar_sistemas_detalhado(self):
        """Compara sistemas de forma detalhada"""
        print("\n⚖️ COMPARAÇÃO DETALHADA")
        print("-" * 60)
        
        atual = self.resultados.get('sistema_atual', {})
        novo = self.resultados.get('sistema_novo', {})
        
        comparacao = {
            'modulos': {
                'atual_total': atual.get('total_modulos', 0),
                'novo_total': novo.get('total_modulos', 0),
                'diferenca': atual.get('total_modulos', 0) - novo.get('total_modulos', 0)
            },
            'funcionalidades_unicas': {
                'apenas_atual': [],
                'apenas_novo': [],
                'ambos': []
            }
        }
        
        # Identificar funcionalidades únicas
        modulos_atual = set(atual.get('modulos_funcionais', []))
        modulos_novo = set(novo.get('modulos_funcionais', []))
        
        comparacao['funcionalidades_unicas']['apenas_atual'] = list(modulos_atual - modulos_novo)
        comparacao['funcionalidades_unicas']['apenas_novo'] = list(modulos_novo - modulos_atual)
        comparacao['funcionalidades_unicas']['ambos'] = list(modulos_atual & modulos_novo)
        
        print(f"📊 MÓDULOS FUNCIONAIS:")
        print(f"   Sistema Atual: {len(modulos_atual)} módulos")
        print(f"   Sistema Novo:  {len(modulos_novo)} módulos")
        print(f"   Diferença:     {len(modulos_atual) - len(modulos_novo):+d}")
        
        print(f"\n🔧 FUNCIONALIDADES EXCLUSIVAS ATUAL:")
        for func in comparacao['funcionalidades_unicas']['apenas_atual']:
            print(f"   ⚡ {func}")
        
        print(f"\n🆕 FUNCIONALIDADES EXCLUSIVAS NOVO:")
        for func in comparacao['funcionalidades_unicas']['apenas_novo']:
            print(f"   ⚡ {func}")
        
        print(f"\n🤝 FUNCIONALIDADES EM AMBOS:")
        for func in comparacao['funcionalidades_unicas']['ambos']:
            print(f"   ✅ {func}")
        
        self.resultados['comparacao_detalhada'] = comparacao
    
    def gerar_relatorio_completo(self, tempo_total: float):
        """Gera relatório completo dos testes"""
        print("\n" + "="*80)
        print("📋 RELATÓRIO COMPLETO - BATERIA INTENSIVA DE TESTES")
        print("="*80)
        
        print(f"\n⏱️ ESTATÍSTICAS GERAIS:")
        print(f"   Tempo total: {tempo_total:.1f} segundos")
        print(f"   Testes realizados: 9 categorias")
        print(f"   Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        
        # Resumo por sistema
        for sistema_nome, sistema_key in [("SISTEMA ATUAL", "sistema_atual"), ("SISTEMA NOVO", "sistema_novo")]:
            print(f"\n🤖 {sistema_nome}:")
            
            dados = self.resultados.get(sistema_key, {})
            if dados.get('inicializacao', False):
                print(f"   ✅ Inicialização: OK")
                print(f"   🔧 Módulos ativos: {dados.get('total_modulos', 0)}")
                print(f"   🌐 Modo real: {dados.get('modo_real', False)}")
                print(f"   💾 Client ativo: {dados.get('client_ativo', False)}")
            else:
                print(f"   ❌ Inicialização: FALHOU")
                print(f"   🚨 Erro: {dados.get('erro', 'Desconhecido')}")
        
        # Performance
        perf_atual = self.resultados.get('performance', {}).get('sistema_atual', {})
        perf_novo = self.resultados.get('performance', {}).get('sistema_novo', {})
        
        print(f"\n⚡ PERFORMANCE:")
        if perf_atual:
            print(f"   Sistema Atual: {perf_atual.get('tempo_medio', 0):.3f}s médio")
        if perf_novo:
            print(f"   Sistema Novo:  {perf_novo.get('tempo_medio', 0):.3f}s médio")
        
        # Recomendação final
        self.gerar_recomendacao_final()
        
        # Salvar resultados
        self.salvar_resultados_detalhados()
    
    def gerar_recomendacao_final(self):
        """Gera recomendação final baseada em todos os testes"""
        print(f"\n🎯 RECOMENDAÇÃO FINAL:")
        
        atual_ok = self.resultados.get('sistema_atual', {}).get('inicializacao', False)
        novo_ok = self.resultados.get('sistema_novo', {}).get('inicializacao', False)
        
        if atual_ok and novo_ok:
            modulos_atual = len(self.resultados.get('sistema_atual', {}).get('modulos_funcionais', []))
            modulos_novo = len(self.resultados.get('sistema_novo', {}).get('modulos_funcionais', []))
            
            if modulos_atual > modulos_novo:
                print("   🏆 SISTEMA ATUAL tem mais funcionalidades ativas")
                print("   💡 RECOMENDAÇÃO: MANTER SISTEMA ATUAL")
            elif modulos_novo > modulos_atual:
                print("   🏆 SISTEMA NOVO tem mais funcionalidades ativas")
                print("   💡 RECOMENDAÇÃO: MIGRAR PARA SISTEMA NOVO")
            else:
                print("   ⚖️ SISTEMAS EQUIVALENTES em funcionalidades")
                print("   💡 RECOMENDAÇÃO: ESCOLHA BASEADA EM ARQUITETURA")
        elif atual_ok:
            print("   🏆 APENAS SISTEMA ATUAL funcional")
            print("   💡 RECOMENDAÇÃO: MANTER SISTEMA ATUAL")
        elif novo_ok:
            print("   🏆 APENAS SISTEMA NOVO funcional")
            print("   💡 RECOMENDAÇÃO: MIGRAR PARA SISTEMA NOVO")
        else:
            print("   🚨 NENHUM SISTEMA funcional")
            print("   💡 RECOMENDAÇÃO: INVESTIGAR PROBLEMAS")
    
    def salvar_resultados_detalhados(self):
        """Salva resultados detalhados em arquivo"""
        with open('bateria_testes_claude_completa.json', 'w', encoding='utf-8') as f:
            json.dump(self.resultados, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n💾 Resultados detalhados salvos em: bateria_testes_claude_completa.json")

def main():
    """Função principal"""
    print("🧪 BATERIA INTENSIVA DE TESTES - CLAUDE AI")
    print("🔬 Análise científica e detalhada dos sistemas")
    print("⏱️ Tempo estimado: 10-15 minutos")
    print()
    input("Pressione ENTER para iniciar a bateria intensiva de testes...")
    
    bateria = BateriaTestesIntensiva()
    bateria.executar_bateria_completa()
    
    print("\n🎯 BATERIA DE TESTES CONCLUÍDA!")
    print("📊 Consulte bateria_testes_claude_completa.json para dados completos")

if __name__ == "__main__":
    main() 