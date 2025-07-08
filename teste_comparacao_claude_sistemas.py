#!/usr/bin/env python3
"""
TESTE DE COMPARAÇÃO: Claude AI Atual vs Claude AI Novo
Script para validar funcionalidades e demonstrar diferenças
"""

import sys
import os
import importlib
from datetime import datetime
import traceback

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class TestadorSistemasClaude:
    """Testador para comparar sistemas Claude AI"""
    
    def __init__(self):
        self.resultados = {
            'sistema_atual': {},
            'sistema_novo': {},
            'comparacao': {}
        }
        self.consultas_teste = [
            "Quantas entregas do Assai em dezembro?",
            "Gere um relatório Excel das entregas atrasadas",
            "Qual o status dos embarques hoje?",
            "Descubra a estrutura do projeto",
            "Ler arquivo app/models.py"
        ]
    
    def executar_todos_testes(self):
        """Executa todos os testes de comparação"""
        print("🔍 INICIANDO TESTE DE COMPARAÇÃO DOS SISTEMAS CLAUDE AI")
        print("=" * 70)
        
        # Testar sistema atual
        self.testar_sistema_atual()
        
        # Testar sistema novo
        self.testar_sistema_novo()
        
        # Comparar resultados
        self.comparar_sistemas()
        
        # Exibir relatório final
        self.exibir_relatorio_final()
    
    def testar_sistema_atual(self):
        """Testa o sistema Claude AI atual"""
        print("\n🤖 TESTANDO SISTEMA ATUAL (claude_ai/)")
        print("-" * 50)
        
        try:
            # Importar sistema atual
            from app.claude_ai.claude_real_integration import ClaudeRealIntegration
            
            sistema_atual = ClaudeRealIntegration()
            
            # Testar funcionalidades
            self.resultados['sistema_atual']['inicializacao'] = True
            self.resultados['sistema_atual']['funcionalidades'] = []
            
            # Contar funcionalidades disponíveis
            funcionalidades_atual = [
                'multi_agent_system',
                'advanced_ai_system', 
                'nlp_analyzer',
                'intelligent_analyzer',
                'suggestion_engine',
                'ml_models',
                'human_learning',
                'excel_generator',
                'auto_command_processor',
                'conversation_context',
                'mapeamento_semantico',
                'project_scanner'
            ]
            
            for func in funcionalidades_atual:
                if hasattr(sistema_atual, func) and getattr(sistema_atual, func) is not None:
                    self.resultados['sistema_atual']['funcionalidades'].append(func)
                    print(f"   ✅ {func}")
                else:
                    print(f"   ❌ {func}")
            
            # Testar consultas
            print("\n📝 TESTANDO CONSULTAS:")
            self.resultados['sistema_atual']['consultas'] = {}
            
            for consulta in self.consultas_teste:
                try:
                    resposta = sistema_atual.processar_consulta_real(consulta)
                    sucesso = len(resposta) > 10 and "erro" not in resposta.lower()
                    self.resultados['sistema_atual']['consultas'][consulta] = {
                        'sucesso': sucesso,
                        'tamanho_resposta': len(resposta),
                        'tempo_resposta': 'N/A'
                    }
                    status = "✅" if sucesso else "❌"
                    print(f"   {status} {consulta[:50]}...")
                except Exception as e:
                    self.resultados['sistema_atual']['consultas'][consulta] = {
                        'sucesso': False,
                        'erro': str(e)
                    }
                    print(f"   ❌ {consulta[:50]}... - ERRO: {str(e)[:30]}")
            
            # Métricas do sistema atual
            self.resultados['sistema_atual']['metricas'] = {
                'funcionalidades_ativas': len(self.resultados['sistema_atual']['funcionalidades']),
                'taxa_sucesso_consultas': sum(1 for c in self.resultados['sistema_atual']['consultas'].values() if c.get('sucesso', False)) / len(self.consultas_teste),
                'modo_real': sistema_atual.modo_real,
                'redis_disponivel': getattr(sistema_atual, 'redis_disponivel', False),
                'client_ativo': sistema_atual.client is not None
            }
            
            print(f"\n📊 MÉTRICAS SISTEMA ATUAL:")
            print(f"   🔧 Funcionalidades ativas: {self.resultados['sistema_atual']['metricas']['funcionalidades_ativas']}")
            print(f"   📈 Taxa de sucesso: {self.resultados['sistema_atual']['metricas']['taxa_sucesso_consultas']:.1%}")
            print(f"   🌐 Modo real: {self.resultados['sistema_atual']['metricas']['modo_real']}")
            print(f"   💾 Redis: {self.resultados['sistema_atual']['metricas']['redis_disponivel']}")
            
        except Exception as e:
            print(f"❌ ERRO NO SISTEMA ATUAL: {e}")
            self.resultados['sistema_atual']['inicializacao'] = False
            self.resultados['sistema_atual']['erro'] = str(e)
            traceback.print_exc()
    
    def testar_sistema_novo(self):
        """Testa o sistema Claude AI novo"""
        print("\n🆕 TESTANDO SISTEMA NOVO (claude_ai_novo/)")
        print("-" * 50)
        
        try:
            # Importar sistema novo
            from app.claude_ai_novo.integration.claude import ClaudeRealIntegration as ClaudeNovo
            
            sistema_novo = ClaudeNovo()
            
            # Testar funcionalidades
            self.resultados['sistema_novo']['inicializacao'] = True
            self.resultados['sistema_novo']['funcionalidades'] = []
            
            # Contar funcionalidades disponíveis
            funcionalidades_novo = [
                'excel_commands',
                'database_loader',
                'conversation_context',
                'human_learning',
                'lifelong_learning',
                'suggestion_engine',
                'intention_analyzer',
                'query_analyzer',
                'redis_cache',
                'intelligent_cache'
            ]
            
            for func in funcionalidades_novo:
                if hasattr(sistema_novo, func) and getattr(sistema_novo, func) is not None:
                    self.resultados['sistema_novo']['funcionalidades'].append(func)
                    print(f"   ✅ {func}")
                else:
                    print(f"   ❌ {func}")
            
            # Testar consultas
            print("\n📝 TESTANDO CONSULTAS:")
            self.resultados['sistema_novo']['consultas'] = {}
            
            for consulta in self.consultas_teste:
                try:
                    resposta = sistema_novo.processar_consulta_real(consulta)
                    sucesso = len(resposta) > 10 and "erro" not in resposta.lower()
                    self.resultados['sistema_novo']['consultas'][consulta] = {
                        'sucesso': sucesso,
                        'tamanho_resposta': len(resposta),
                        'tempo_resposta': 'N/A'
                    }
                    status = "✅" if sucesso else "❌"
                    print(f"   {status} {consulta[:50]}...")
                except Exception as e:
                    self.resultados['sistema_novo']['consultas'][consulta] = {
                        'sucesso': False,
                        'erro': str(e)
                    }
                    print(f"   ❌ {consulta[:50]}... - ERRO: {str(e)[:30]}")
            
            # Métricas do sistema novo
            self.resultados['sistema_novo']['metricas'] = {
                'funcionalidades_ativas': len(self.resultados['sistema_novo']['funcionalidades']),
                'taxa_sucesso_consultas': sum(1 for c in self.resultados['sistema_novo']['consultas'].values() if c.get('sucesso', False)) / len(self.consultas_teste),
                'modo_real': sistema_novo.modo_real,
                'redis_disponivel': getattr(sistema_novo, 'redis_disponivel', False),
                'client_ativo': sistema_novo.client is not None
            }
            
            print(f"\n📊 MÉTRICAS SISTEMA NOVO:")
            print(f"   🔧 Funcionalidades ativas: {self.resultados['sistema_novo']['metricas']['funcionalidades_ativas']}")
            print(f"   📈 Taxa de sucesso: {self.resultados['sistema_novo']['metricas']['taxa_sucesso_consultas']:.1%}")
            print(f"   🌐 Modo real: {self.resultados['sistema_novo']['metricas']['modo_real']}")
            print(f"   💾 Redis: {self.resultados['sistema_novo']['metricas']['redis_disponivel']}")
            
        except Exception as e:
            print(f"❌ ERRO NO SISTEMA NOVO: {e}")
            self.resultados['sistema_novo']['inicializacao'] = False
            self.resultados['sistema_novo']['erro'] = str(e)
            traceback.print_exc()
    
    def comparar_sistemas(self):
        """Compara os dois sistemas"""
        print("\n⚖️ COMPARAÇÃO ENTRE SISTEMAS")
        print("-" * 50)
        
        # Inicialização
        atual_ok = self.resultados['sistema_atual'].get('inicializacao', False)
        novo_ok = self.resultados['sistema_novo'].get('inicializacao', False)
        
        print(f"🔄 Inicialização:")
        print(f"   Sistema Atual: {'✅' if atual_ok else '❌'}")
        print(f"   Sistema Novo:  {'✅' if novo_ok else '❌'}")
        
        if atual_ok and novo_ok:
            # Funcionalidades
            func_atual = len(self.resultados['sistema_atual']['funcionalidades'])
            func_novo = len(self.resultados['sistema_novo']['funcionalidades'])
            
            print(f"\n🔧 Funcionalidades:")
            print(f"   Sistema Atual: {func_atual} funcionalidades")
            print(f"   Sistema Novo:  {func_novo} funcionalidades")
            print(f"   Diferença:     {func_atual - func_novo:+d} funcionalidades")
            
            # Taxa de sucesso
            taxa_atual = self.resultados['sistema_atual']['metricas']['taxa_sucesso_consultas']
            taxa_novo = self.resultados['sistema_novo']['metricas']['taxa_sucesso_consultas']
            
            print(f"\n📈 Taxa de Sucesso:")
            print(f"   Sistema Atual: {taxa_atual:.1%}")
            print(f"   Sistema Novo:  {taxa_novo:.1%}")
            print(f"   Diferença:     {taxa_atual - taxa_novo:+.1%}")
            
            # Armazenar comparação
            self.resultados['comparacao'] = {
                'funcionalidades_atual': func_atual,
                'funcionalidades_novo': func_novo,
                'diferenca_funcionalidades': func_atual - func_novo,
                'taxa_sucesso_atual': taxa_atual,
                'taxa_sucesso_novo': taxa_novo,
                'diferenca_taxa_sucesso': taxa_atual - taxa_novo,
                'recomendacao': 'MANTER ATUAL' if func_atual > func_novo else 'MIGRAR NOVO'
            }
        else:
            self.resultados['comparacao'] = {
                'status': 'ERRO_INICIALIZACAO',
                'recomendacao': 'MANTER ATUAL' if atual_ok else 'NENHUM FUNCIONAL'
            }
    
    def exibir_relatorio_final(self):
        """Exibe relatório final da comparação"""
        print("\n" + "="*70)
        print("📋 RELATÓRIO FINAL - COMPARAÇÃO SISTEMAS CLAUDE AI")
        print("="*70)
        
        # Resumo executivo
        comparacao = self.resultados['comparacao']
        
        if 'diferenca_funcionalidades' in comparacao:
            print(f"\n🎯 RESUMO EXECUTIVO:")
            print(f"   Sistema Atual: {comparacao['funcionalidades_atual']} funcionalidades - Taxa: {comparacao['taxa_sucesso_atual']:.1%}")
            print(f"   Sistema Novo:  {comparacao['funcionalidades_novo']} funcionalidades - Taxa: {comparacao['taxa_sucesso_novo']:.1%}")
            print(f"   Diferença:     {comparacao['diferenca_funcionalidades']:+d} funcionalidades - {comparacao['diferenca_taxa_sucesso']:+.1%}")
            
            # Recomendação
            print(f"\n🏆 RECOMENDAÇÃO: {comparacao['recomendacao']}")
            
            if comparacao['diferenca_funcionalidades'] > 0:
                print("   ✅ Sistema atual é SUPERIOR em funcionalidades")
            elif comparacao['diferenca_funcionalidades'] < 0:
                print("   ⚠️ Sistema novo tem mais funcionalidades")
            else:
                print("   ⚖️ Sistemas equivalentes em funcionalidades")
                
            if comparacao['diferenca_taxa_sucesso'] > 0:
                print("   ✅ Sistema atual é SUPERIOR em taxa de sucesso")
            elif comparacao['diferenca_taxa_sucesso'] < 0:
                print("   ⚠️ Sistema novo tem melhor taxa de sucesso")
            else:
                print("   ⚖️ Sistemas equivalentes em taxa de sucesso")
        
        # Detalhes por consulta
        print(f"\n📝 DETALHES POR CONSULTA:")
        for consulta in self.consultas_teste:
            atual = self.resultados['sistema_atual']['consultas'].get(consulta, {})
            novo = self.resultados['sistema_novo']['consultas'].get(consulta, {})
            
            status_atual = "✅" if atual.get('sucesso', False) else "❌"
            status_novo = "✅" if novo.get('sucesso', False) else "❌"
            
            print(f"   {consulta[:40]}...")
            print(f"     Atual: {status_atual} | Novo: {status_novo}")
        
        print(f"\n📊 ESTATÍSTICAS FINAIS:")
        print(f"   Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"   Consultas testadas: {len(self.consultas_teste)}")
        print(f"   Funcionalidades comparadas: {len(self.resultados['sistema_atual']['funcionalidades']) + len(self.resultados['sistema_novo']['funcionalidades'])}")
        
        # Salvar resultados
        self.salvar_resultados()
    
    def salvar_resultados(self):
        """Salva resultados em arquivo"""
        import json
        
        with open('resultados_comparacao_claude.json', 'w', encoding='utf-8') as f:
            json.dump(self.resultados, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n💾 Resultados salvos em: resultados_comparacao_claude.json")

def main():
    """Função principal"""
    print("🚀 INICIANDO TESTE DE COMPARAÇÃO CLAUDE AI")
    print("🔍 Análise: Sistema Atual vs Sistema Novo")
    print("⏱️ Tempo estimado: 2-3 minutos")
    
    testador = TestadorSistemasClaude()
    testador.executar_todos_testes()
    
    print("\n🎯 CONCLUSÃO DO TESTE:")
    print("   Consulte o arquivo ANALISE_REFATORACAO_CLAUDE_AI.md para análise detalhada")
    print("   Consulte o arquivo resultados_comparacao_claude.json para dados brutos")

if __name__ == "__main__":
    main() 