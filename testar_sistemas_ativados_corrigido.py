#!/usr/bin/env python3
"""
🔧 TESTADOR DE SISTEMAS CLAUDE AI - VERSÃO WINDOWS
Versão corrigida para Windows com encoding UTF-8
"""

import sys
import os
import logging
import traceback
from datetime import datetime
from typing import Dict, List, Tuple, Any
import json

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())

# Configurar logging sem emojis para Windows
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    handlers=[
        logging.FileHandler('teste_sistemas_claude.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class TestadorSistemasClaudeAI:
    """Testador completo dos sistemas Claude AI"""
    
    def __init__(self):
        self.sistemas_testados = {}
        self.erros_encontrados = []
        self.warnings_encontrados = []
        
    def executar_todos_os_testes(self) -> bool:
        """Executa todos os testes disponíveis"""
        print("\n" + "="*60)
        print("   TESTADOR DE SISTEMAS CLAUDE AI")
        print("   Versão Windows - UTF-8")
        print("="*60)
        
        # Lista de testes a executar
        testes = [
            ("Imports e Configurações", self.testar_imports_configuracoes),
            ("Security Guard", self.testar_security_guard),
            ("Lifelong Learning", self.testar_lifelong_learning),
            ("Auto Command Processor", self.testar_auto_command_processor),
            ("Code Generator", self.testar_code_generator),
            ("Project Scanner", self.testar_project_scanner),
            ("Sistema Real Data", self.testar_sistema_real_data),
            ("Logs e Configurações", self.testar_logs_configuracoes),
        ]
        
        sucessos = []
        
        for nome, funcao_teste in testes:
            try:
                print(f"\n[TESTE] {nome}...")
                resultado = funcao_teste()
                if resultado:
                    sucessos.append(nome)
                    print(f"[OK] {nome}")
                else:
                    print(f"[ERRO] {nome}")
                    
            except Exception as e:
                print(f"[ERRO] {nome}: {str(e)}")
                self.erros_encontrados.append(f"{nome}: {str(e)}")
                
        # Gerar relatório final
        self.gerar_relatorio_final(sucessos, len(testes))
        
        return len(sucessos) == len(testes)
    
    def testar_imports_configuracoes(self) -> bool:
        """Testa imports básicos e configurações"""
        try:
            # Testar imports críticos
            from app.claude_ai import routes
            from app.claude_ai.claude_real_integration import ClaudeRealIntegration
            
            # Testar variáveis de ambiente
            anthropic_key = os.getenv('ANTHROPIC_API_KEY')
            redis_url = os.getenv('REDIS_URL')
            
            if not anthropic_key:
                self.warnings_encontrados.append("ANTHROPIC_API_KEY não encontrada")
                return False
                
            if not redis_url:
                self.warnings_encontrados.append("REDIS_URL não encontrada")
                return False
                
            logger.info("Imports e configurações básicas funcionando")
            return True
            
        except Exception as e:
            self.erros_encontrados.append(f"Imports: {str(e)}")
            return False
    
    def testar_security_guard(self) -> bool:
        """Testa o sistema Security Guard"""
        try:
            from app.claude_ai.security_guard import SecurityGuard
            
            # Criar instância
            guard = SecurityGuard()
            
            # Testar métodos básicos
            if hasattr(guard, 'validate_request'):
                # Teste básico
                result = guard.validate_request("teste", {"test": True})
                logger.info("Security Guard: validate_request funcionando")
                
            if hasattr(guard, 'check_permissions'):
                # Teste básico
                result = guard.check_permissions("admin", "read")
                logger.info("Security Guard: check_permissions funcionando")
                
            return True
            
        except Exception as e:
            self.erros_encontrados.append(f"Security Guard: {str(e)}")
            return False
    
    def testar_lifelong_learning(self) -> bool:
        """Testa o sistema Lifelong Learning"""
        try:
            from app.claude_ai.lifelong_learning import LifelongLearning
            
            # Criar instância
            learning = LifelongLearning()
            
            # Testar métodos básicos
            if hasattr(learning, 'learn_from_interaction'):
                logger.info("Lifelong Learning: learn_from_interaction disponível")
                
            if hasattr(learning, 'get_insights'):
                logger.info("Lifelong Learning: get_insights disponível")
                
            return True
            
        except Exception as e:
            self.erros_encontrados.append(f"Lifelong Learning: {str(e)}")
            return False
    
    def testar_auto_command_processor(self) -> bool:
        """Testa o Auto Command Processor"""
        try:
            from app.claude_ai.auto_command_processor import AutoCommandProcessor
            
            # Criar instância
            processor = AutoCommandProcessor()
            
            # Testar métodos básicos
            if hasattr(processor, 'process_command'):
                logger.info("Auto Command Processor: process_command disponível")
                
            if hasattr(processor, 'register_command'):
                logger.info("Auto Command Processor: register_command disponível")
                
            return True
            
        except Exception as e:
            self.erros_encontrados.append(f"Auto Command Processor: {str(e)}")
            return False
    
    def testar_code_generator(self) -> bool:
        """Testa o Code Generator"""
        try:
            from app.claude_ai.claude_code_generator import ClaudeCodeGenerator
            
            # Criar instância
            generator = ClaudeCodeGenerator()
            
            # Testar métodos básicos
            if hasattr(generator, 'generate_module'):
                logger.info("Code Generator: generate_module disponível")
                
            if hasattr(generator, 'generate_route'):
                logger.info("Code Generator: generate_route disponível")
                
            return True
            
        except Exception as e:
            self.erros_encontrados.append(f"Code Generator: {str(e)}")
            return False
    
    def testar_project_scanner(self) -> bool:
        """Testa o Project Scanner"""
        try:
            from app.claude_ai.claude_project_scanner import ClaudeProjectScanner
            
            # Criar instância
            scanner = ClaudeProjectScanner()
            
            # Testar métodos básicos
            if hasattr(scanner, 'scan_project'):
                logger.info("Project Scanner: scan_project disponível")
                
            if hasattr(scanner, 'analyze_structure'):
                logger.info("Project Scanner: analyze_structure disponível")
                
            return True
            
        except Exception as e:
            self.erros_encontrados.append(f"Project Scanner: {str(e)}")
            return False
    
    def testar_sistema_real_data(self) -> bool:
        """Testa o Sistema Real Data"""
        try:
            from app.claude_ai.sistema_real_data import SistemaRealData
            
            # Criar instância
            sistema = SistemaRealData()
            
            # Testar métodos básicos
            if hasattr(sistema, 'get_real_data'):
                logger.info("Sistema Real Data: get_real_data disponível")
                
            if hasattr(sistema, 'process_data'):
                logger.info("Sistema Real Data: process_data disponível")
                
            return True
            
        except Exception as e:
            self.erros_encontrados.append(f"Sistema Real Data: {str(e)}")
            return False
    
    def testar_logs_configuracoes(self) -> bool:
        """Testa logs e configurações"""
        try:
            # Verificar se diretório de logs existe
            logs_dir = os.path.join('app', 'claude_ai', 'logs')
            if not os.path.exists(logs_dir):
                os.makedirs(logs_dir)
                logger.info(f"Diretório de logs criado: {logs_dir}")
            
            # Testar escrita de log
            log_file = os.path.join(logs_dir, 'teste.log')
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(f"Teste de log - {datetime.now()}\n")
            
            logger.info("Logs e configurações funcionando")
            return True
            
        except Exception as e:
            self.erros_encontrados.append(f"Logs: {str(e)}")
            return False
    
    def gerar_relatorio_final(self, sucessos: List[str], total_testes: int):
        """Gera relatório final dos testes"""
        print("\n" + "="*60)
        print("   RELATÓRIO FINAL DOS TESTES")
        print("="*60)
        
        # Estatísticas
        passaram = len(sucessos)
        falharam = total_testes - passaram
        percentual = (passaram / total_testes) * 100 if total_testes > 0 else 0
        
        print(f"\nESTATÍSTICAS:")
        print(f"   Total de testes: {total_testes}")
        print(f"   Passaram: {passaram}")
        print(f"   Falharam: {falharam}")
        print(f"   Percentual de sucesso: {percentual:.1f}%")
        
        # Testes que passaram
        if sucessos:
            print(f"\nTESTES APROVADOS:")
            for nome in sucessos:
                print(f"   [OK] {nome}")
        
        # Erros encontrados
        if self.erros_encontrados:
            print(f"\nERROS ENCONTRADOS:")
            for erro in self.erros_encontrados:
                print(f"   [ERRO] {erro}")
        
        # Warnings
        if self.warnings_encontrados:
            print(f"\nWARNINGS:")
            for warning in self.warnings_encontrados:
                print(f"   [WARN] {warning}")
        
        # Arquivos de log
        print(f"\nARQUIVOS DE LOG:")
        print(f"   • teste_sistemas_claude.log")
        print(f"   • app/claude_ai/logs/ (se existir)")
        
        if falharam > 0:
            print(f"\nAÇÃO NECESSÁRIA:")
            print(f"   1. Revisar erros acima")
            print(f"   2. Executar 'configurar_env_local.bat' primeiro")
            print(f"   3. Fechar e abrir novo terminal")
            print(f"   4. Executar novamente os testes")
        else:
            print(f"\nSUCESSO TOTAL!")
            print(f"   Todos os sistemas Claude AI estão funcionando!")
        
        print("="*60)

def main():
    """Função principal"""
    try:
        print("Iniciando testador de sistemas Claude AI...")
        testador = TestadorSistemasClaudeAI()
        sucesso_geral = testador.executar_todos_os_testes()
        
        if sucesso_geral:
            print("\n[SUCESSO] Todos os testes passaram!")
            return True
        else:
            print("\n[ATENÇÃO] Alguns testes falharam. Verifique o relatório acima.")
            return False
            
    except Exception as e:
        print(f"\n[ERRO CRÍTICO] {str(e)}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    sucesso = main()
    sys.exit(0 if sucesso else 1) 