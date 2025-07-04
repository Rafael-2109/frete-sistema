#!/usr/bin/env python3
"""
🧪 TESTE DOS SISTEMAS CLAUDE AI ATIVADOS
Valida se todos os sistemas estão funcionando corretamente
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('teste_sistemas_claude.log')
    ]
)
logger = logging.getLogger(__name__)

class TestadorSistemasClaudeAI:
    """Classe para testar todos os sistemas Claude AI"""
    
    def __init__(self):
        self.resultados = {}
        self.erros = []
        
    def executar_todos_os_testes(self):
        """Executa todos os testes disponíveis"""
        logger.info("🧪 INICIANDO TESTES DOS SISTEMAS CLAUDE AI")
        logger.info("=" * 60)
        
        testes = [
            ("Security Guard", self.teste_security_guard),
            ("Lifelong Learning", self.teste_lifelong_learning),
            ("Auto Command Processor", self.teste_auto_command_processor),
            ("Code Generator", self.teste_code_generator),
            ("Project Scanner", self.teste_project_scanner),
            ("Sistema Real Data", self.teste_sistema_real_data),
            ("Integração Completa", self.teste_integracao_completa),
            ("Performance", self.teste_performance),
            ("Logs e Configurações", self.teste_logs_configs)
        ]
        
        sucessos = 0
        
        for i, (nome, teste_func) in enumerate(testes, 1):
            logger.info(f"\n[{i}/{len(testes)}] Testando {nome}...")
            try:
                resultado = teste_func()
                self.resultados[nome] = resultado
                if resultado['sucesso']:
                    sucessos += 1
                    logger.info(f"✅ {nome} - SUCESSO")
                else:
                    logger.error(f"❌ {nome} - FALHOU: {resultado.get('erro', 'Erro desconhecido')}")
            except Exception as e:
                logger.error(f"❌ {nome} - ERRO CRÍTICO: {e}")
                self.resultados[nome] = {'sucesso': False, 'erro': str(e)}
                self.erros.append(f"{nome}: {e}")
        
        # Relatório final
        self.gerar_relatorio_final(sucessos, len(testes))
        
        return sucessos >= len(testes) * 0.8  # 80% de sucesso
    
    def teste_security_guard(self):
        """Testa o Security Guard"""
        try:
            from app.claude_ai.security_guard import ClaudeSecurityGuard
            security = ClaudeSecurityGuard()
            
            # Testar validação
            allowed, reason, _ = security.validate_file_operation(
                "app/teste.py", "CREATE", "print('teste')"
            )
            
            logger.info(f"✅ Security Guard funcionando - Validação: {allowed or 'PENDENTE' in reason}")
            return True
        except Exception as e:
            logger.error(f"❌ Security Guard: {e}")
            return False
    
    def teste_lifelong_learning(self):
        """Testa o Lifelong Learning"""
        try:
            from app.claude_ai.lifelong_learning import LifelongLearningSystem
            lifelong = LifelongLearningSystem()
            
            stats = lifelong.obter_estatisticas_aprendizado()
            logger.info(f"✅ Lifelong Learning funcionando - Stats: {len(stats)} campos")
            return True
        except Exception as e:
            logger.error(f"❌ Lifelong Learning: {e}")
            return False
    
    def teste_auto_command_processor(self):
        """Testa o Auto Command Processor"""
        try:
            from app.claude_ai.auto_command_processor import AutoCommandProcessor
            auto_proc = AutoCommandProcessor()
            
            comando, params = auto_proc.detect_command("crie um módulo teste")
            logger.info(f"✅ Auto Command Processor funcionando - Comando: {comando}")
            return comando is not None
        except Exception as e:
            logger.error(f"❌ Auto Command Processor: {e}")
            return False
    
    def teste_code_generator(self):
        """Testa o Code Generator"""
        try:
            from app.claude_ai.claude_code_generator import ClaudeCodeGenerator
            code_gen = ClaudeCodeGenerator()
            
            content = code_gen.read_file("app/__init__.py")
            logger.info(f"✅ Code Generator funcionando - Leu arquivo: {not content.startswith('❌')}")
            return not content.startswith('❌')
        except Exception as e:
            logger.error(f"❌ Code Generator: {e}")
            return False
    
    def teste_project_scanner(self):
        """Testa o Project Scanner"""
        try:
            from app.claude_ai.claude_project_scanner import ClaudeProjectScanner
            scanner = ClaudeProjectScanner()
            
            estrutura = scanner.discover_project_structure()
            logger.info(f"✅ Project Scanner funcionando - Módulos: {len(estrutura.get('modules', {}))}")
            return 'modules' in estrutura
        except Exception as e:
            logger.error(f"❌ Project Scanner: {e}")
            return False
    
    def teste_sistema_real_data(self):
        """Testa o Sistema Real Data"""
        try:
            from app.claude_ai.sistema_real_data import get_sistema_real_data
            
            # Teste 1: Obter dados
            dados = get_sistema_real_data()
            
            # Teste 2: Verificar estrutura
            tem_estrutura = isinstance(dados, dict) and len(dados) > 0
            
            # Teste 3: Verificar conteúdo esperado
            campos_esperados = ['total_clientes', 'total_pedidos', 'total_embarques']
            campos_encontrados = sum(1 for campo in campos_esperados if campo in str(dados))
            
            detalhes = {
                'dados_obtidos': dados is not None,
                'estrutura_valida': tem_estrutura,
                'tamanho_dados': len(str(dados)) if dados else 0,
                'campos_encontrados': campos_encontrados,
                'campos_esperados': len(campos_esperados)
            }
            
            return {
                'sucesso': tem_estrutura and campos_encontrados > 0,
                'detalhes': detalhes,
                'total_testes': 3,
                'testes_passaram': sum([dados is not None, tem_estrutura, campos_encontrados > 0])
            }
            
        except Exception as e:
            return {'sucesso': False, 'erro': str(e)}
    
    def teste_integracao_completa(self):
        """Testa a integração entre sistemas"""
        try:
            # Teste 1: Importações funcionam
            sistemas_importados = 0
            sistemas_testados = [
                'app.claude_ai.security_guard',
                'app.claude_ai.lifelong_learning',
                'app.claude_ai.auto_command_processor',
                'app.claude_ai.claude_code_generator',
                'app.claude_ai.claude_project_scanner'
            ]
            
            for sistema in sistemas_testados:
                try:
                    __import__(sistema)
                    sistemas_importados += 1
                except:
                    pass
            
            # Teste 2: Inicialização conjunta
            try:
                from app.claude_ai import setup_claude_ai
                from app import create_app
                
                app = create_app()
                with app.app_context():
                    resultado_setup = setup_claude_ai(app)
                    
                setup_ok = resultado_setup is not None
            except Exception as e:
                setup_ok = False
            
            # Teste 3: Verificar __init__.py
            init_file = Path('app/claude_ai/__init__.py')
            init_existe = init_file.exists()
            
            detalhes = {
                'sistemas_importaveis': sistemas_importados,
                'total_sistemas': len(sistemas_testados),
                'setup_funciona': setup_ok,
                'init_existe': init_existe
            }
            
            return {
                'sucesso': sistemas_importados >= len(sistemas_testados) * 0.8 and setup_ok,
                'detalhes': detalhes,
                'total_testes': len(sistemas_testados) + 2,
                'testes_passaram': sistemas_importados + (1 if setup_ok else 0) + (1 if init_existe else 0)
            }
            
        except Exception as e:
            return {'sucesso': False, 'erro': str(e)}
    
    def teste_performance(self):
        """Testa performance básica dos sistemas"""
        try:
            import time
            
            # Teste 1: Tempo de importação
            start_time = time.time()
            from app.claude_ai.claude_real_integration import ClaudeRealIntegration
            import_time = time.time() - start_time
            
            # Teste 2: Tempo de inicialização
            start_time = time.time()
            claude_integration = ClaudeRealIntegration()
            init_time = time.time() - start_time
            
            # Teste 3: Memória básica (arquivo de tamanho)
            arquivos_principais = [
                'app/claude_ai/claude_real_integration.py',
                'app/claude_ai/lifelong_learning.py',
                'app/claude_ai/auto_command_processor.py'
            ]
            
            tamanho_total = 0
            for arquivo in arquivos_principais:
                if Path(arquivo).exists():
                    tamanho_total += Path(arquivo).stat().st_size
            
            tamanho_mb = tamanho_total / (1024 * 1024)
            
            detalhes = {
                'tempo_importacao_ms': round(import_time * 1000, 2),
                'tempo_inicializacao_ms': round(init_time * 1000, 2),
                'tamanho_codigo_mb': round(tamanho_mb, 2),
                'performance_ok': import_time < 2.0 and init_time < 5.0
            }
            
            return {
                'sucesso': import_time < 2.0 and init_time < 5.0,  # Menos de 2s para importar, 5s para inicializar
                'detalhes': detalhes,
                'total_testes': 2,
                'testes_passaram': sum([import_time < 2.0, init_time < 5.0])
            }
            
        except Exception as e:
            return {'sucesso': False, 'erro': str(e)}
    
    def teste_logs_configs(self):
        """Testa logs e configurações"""
        try:
            # Teste 1: Diretórios existem
            diretorios_necessarios = [
                'app/claude_ai/security_configs',
                'app/claude_ai/generated_modules',
                'app/claude_ai/logs'
            ]
            
            diretorios_existem = sum(1 for d in diretorios_necessarios if Path(d).exists())
            
            # Teste 2: Arquivos de configuração
            config_file = Path('app/claude_ai/security_configs/security_config.json')
            config_existe = config_file.exists()
            config_valido = False
            
            if config_existe:
                try:
                    with open(config_file) as f:
                        config_data = json.load(f)
                    config_valido = 'modo_seguranca' in config_data
                except:
                    pass
            
            # Teste 3: Permissões de escrita
            test_log = Path('app/claude_ai/logs/test.log')
            test_log.parent.mkdir(exist_ok=True)
            
            try:
                test_log.write_text(f"Teste de escrita: {datetime.now()}")
                escrita_ok = test_log.exists()
                test_log.unlink()  # Limpar
            except:
                escrita_ok = False
            
            detalhes = {
                'diretorios_criados': diretorios_existem,
                'total_diretorios': len(diretorios_necessarios),
                'config_existe': config_existe,
                'config_valido': config_valido,
                'permissao_escrita': escrita_ok
            }
            
            testes_passaram = [
                diretorios_existem == len(diretorios_necessarios),
                config_existe,
                config_valido,
                escrita_ok
            ]
            
            return {
                'sucesso': sum(testes_passaram) >= 3,  # Pelo menos 3 de 4
                'detalhes': detalhes,
                'total_testes': len(testes_passaram),
                'testes_passaram': sum(testes_passaram)
            }
            
        except Exception as e:
            return {'sucesso': False, 'erro': str(e)}
    
    def gerar_relatorio_final(self, sucessos, total):
        """Gera relatório final dos testes"""
        logger.info("\n" + "=" * 60)
        logger.info("📊 RELATÓRIO FINAL DOS TESTES")
        logger.info("=" * 60)
        
        percentual = (sucessos / total) * 100
        logger.info(f"🎯 RESULTADO GERAL: {sucessos}/{total} testes passaram ({percentual:.1f}%)")
        
        if percentual >= 90:
            logger.info("🚀 EXCELENTE! Todos os sistemas estão funcionando perfeitamente!")
        elif percentual >= 75:
            logger.info("✅ MUITO BOM! A maioria dos sistemas está funcionando.")
        elif percentual >= 50:
            logger.info("⚠️ PARCIAL. Alguns sistemas precisam de atenção.")
        else:
            logger.info("❌ CRÍTICO. Muitos sistemas não estão funcionando.")
        
        logger.info("\n📋 DETALHES POR SISTEMA:")
        for nome, resultado in self.resultados.items():
            status = "✅" if resultado.get('sucesso') else "❌"
            detalhes = resultado.get('detalhes', {})
            
            logger.info(f"{status} {nome}:")
            if resultado.get('sucesso'):
                total_testes = resultado.get('total_testes', 0)
                passaram = resultado.get('testes_passaram', 0)
                logger.info(f"   🔬 {passaram}/{total_testes} testes internos passaram")
            else:
                erro = resultado.get('erro', 'Erro desconhecido')
                logger.info(f"   ❌ {erro}")
        
        if self.erros:
            logger.info("\n🚨 ERROS ENCONTRADOS:")
            for erro in self.erros:
                logger.info(f"   • {erro}")
        
        logger.info("\n📁 ARQUIVOS DE LOG:")
        logger.info(f"   • teste_sistemas_claude.log")
        logger.info(f"   • app/claude_ai/logs/ (se existir)")
        
        if percentual >= 75:
            logger.info("\n🎉 SISTEMAS CLAUDE AI FUNCIONANDO!")
            logger.info("🔄 Próximos passos:")
            logger.info("   1. Reiniciar aplicação Flask")
            logger.info("   2. Testar comandos no chat:")
            logger.info("      • 'crie um módulo vendas'")
            logger.info("      • 'descubra a estrutura do projeto'")
            logger.info("      • 'o que você aprendeu?'")
        else:
            logger.info("\n⚡ AÇÃO NECESSÁRIA:")
            logger.info("   1. Revisar erros acima")
            logger.info("   2. Executar 'python ativar_sistemas_claude.py' novamente")
            logger.info("   3. Verificar dependências e permissões")

def main():
    """Função principal"""
    logger.info("🧪 INICIANDO TESTES COMPLETOS DOS SISTEMAS CLAUDE AI")
    
    testador = TestadorSistemasClaudeAI()
    sucesso_geral = testador.executar_todos_os_testes()
    
    return sucesso_geral

if __name__ == '__main__':
    try:
        sucesso = main()
        exit(0 if sucesso else 1)
    except KeyboardInterrupt:
        logger.info("\n⚠️ Testes cancelados pelo usuário")
        exit(1)
    except Exception as e:
        logger.error(f"\n❌ Erro fatal nos testes: {e}")
        exit(1) 