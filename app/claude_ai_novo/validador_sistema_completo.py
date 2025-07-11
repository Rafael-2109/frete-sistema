#!/usr/bin/env python3
"""
🛡️ VALIDADOR SISTEMA COMPLETO
============================

Testa TODAS as funcionalidades do sistema claude_ai_novo
para garantir que tudo funciona corretamente.
"""

import sys
import os
import json
import traceback
import importlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import subprocess
import time

# Adicionar ao path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

class ValidadorSistemaCompleto:
    """Validador completo do sistema"""
    
    def __init__(self):
        self.base_path = Path(__file__).parent
        self.resultados = {
            'timestamp': datetime.now().isoformat(),
            'testes_executados': 0,
            'testes_aprovados': 0,
            'testes_falharam': 0,
            'testes_warning': 0,
            'detalhes_testes': [],
            'componentes_criticos': [],
            'recomendacoes': [],
            'score_geral': 0.0
        }
        
        # Componentes críticos para teste
        self.componentes_criticos = [
            'orchestrators', 'integration', 'processors', 'analyzers',
            'validators', 'mappers', 'providers', 'utils', 'commands'
        ]
        
        print("🛡️ Validador Sistema Completo inicializado")
    
    def validar_sistema_completo(self) -> Dict[str, Any]:
        """Executa validação completa do sistema"""
        print("🚀 Iniciando validação completa do sistema...")
        
        testes = [
            ("📁 Estrutura de Diretórios", self._testar_estrutura_diretorios),
            ("📄 Imports Principais", self._testar_imports_principais),
            ("🔧 Componentes Críticos", self._testar_componentes_criticos),
            ("🎭 Orchestrators", self._testar_orchestrators),
            ("🔗 Integration Manager", self._testar_integration_manager),
            ("⚙️ Processor Registry", self._testar_processor_registry),
            ("🔍 Analyzers", self._testar_analyzers),
            ("🗺️ Mappers", self._testar_mappers),
            ("✅ Validators", self._testar_validators),
            ("📊 Providers", self._testar_providers),
            ("🧠 Memorizers", self._testar_memorizers),
            ("🔍 Enrichers", self._testar_enrichers),
            ("🛠️ Utils", self._testar_utils),
            ("📋 Commands", self._testar_commands),
            ("🔒 Security", self._testar_security),
            ("📈 Performance", self._testar_performance),
            ("📊 Health Checks", self._testar_health_checks),
            ("🔄 Fallbacks", self._testar_fallbacks)
        ]
        
        print(f"📋 Executando {len(testes)} categorias de testes...")
        
        for nome_teste, funcao_teste in testes:
            print(f"\n{nome_teste}")
            print("-" * 40)
            
            try:
                resultado = funcao_teste()
                self._processar_resultado_teste(nome_teste, resultado)
                
            except Exception as e:
                self._processar_erro_teste(nome_teste, e)
        
        # Calcular score final
        self._calcular_score_final()
        
        # Gerar recomendações
        self._gerar_recomendacoes()
        
        print(f"\n✅ Validação completa! Score: {self.resultados['score_geral']:.1f}%")
        return self.resultados
    
    def _testar_estrutura_diretorios(self) -> Dict[str, Any]:
        """Testa se a estrutura de diretórios está correta"""
        resultados = []
        
        for componente in self.componentes_criticos:
            dir_path = self.base_path / componente
            
            if dir_path.exists():
                # Verificar se tem __init__.py
                init_file = dir_path / "__init__.py"
                if init_file.exists():
                    resultados.append({
                        'teste': f"Diretório {componente}",
                        'status': 'aprovado',
                        'detalhes': f"Estrutura OK com __init__.py"
                    })
                else:
                    resultados.append({
                        'teste': f"Diretório {componente}",
                        'status': 'warning',
                        'detalhes': f"Sem __init__.py"
                    })
            else:
                resultados.append({
                    'teste': f"Diretório {componente}",
                    'status': 'falhou',
                    'detalhes': f"Diretório não encontrado"
                })
        
        return {'resultados': resultados}
    
    def _testar_imports_principais(self) -> Dict[str, Any]:
        """Testa imports dos módulos principais"""
        resultados = []
        
        imports_testar = [
            'app.claude_ai_novo.orchestrators',
            'app.claude_ai_novo.integration',
            'app.claude_ai_novo.processors',
            'app.claude_ai_novo.analyzers',
            'app.claude_ai_novo.validators',
            'app.claude_ai_novo.mappers',
            'app.claude_ai_novo.providers',
            'app.claude_ai_novo.utils'
        ]
        
        for import_name in imports_testar:
            try:
                importlib.import_module(import_name)
                resultados.append({
                    'teste': f"Import {import_name}",
                    'status': 'aprovado',
                    'detalhes': 'Import bem-sucedido'
                })
            except ImportError as e:
                resultados.append({
                    'teste': f"Import {import_name}",
                    'status': 'falhou',
                    'detalhes': f"Erro: {str(e)}"
                })
            except Exception as e:
                resultados.append({
                    'teste': f"Import {import_name}",
                    'status': 'warning',
                    'detalhes': f"Erro inesperado: {str(e)}"
                })
        
        return {'resultados': resultados}
    
    def _testar_componentes_criticos(self) -> Dict[str, Any]:
        """Testa componentes críticos específicos"""
        resultados = []
        
        # Testar OrchestratorManager
        try:
            from app.claude_ai_novo.orchestrators.orchestrator_manager import get_orchestrator_manager
            orchestrator_manager = get_orchestrator_manager()
            
            if orchestrator_manager:
                resultados.append({
                    'teste': 'OrchestratorManager',
                    'status': 'aprovado',
                    'detalhes': 'Criado com sucesso'
                })
            else:
                resultados.append({
                    'teste': 'OrchestratorManager',
                    'status': 'falhou',
                    'detalhes': 'Retornou None'
                })
                
        except Exception as e:
            resultados.append({
                'teste': 'OrchestratorManager',
                'status': 'falhou',
                'detalhes': f'Erro: {str(e)}'
            })
        
        # Testar IntegrationManager
        try:
            from app.claude_ai_novo.integration.integration_manager import IntegrationManager
            integration_manager = IntegrationManager()
            
            # Testar se tem get_integration_status
            if hasattr(integration_manager, 'get_integration_status'):
                status = integration_manager.get_integration_status()
                resultados.append({
                    'teste': 'IntegrationManager.get_integration_status',
                    'status': 'aprovado',
                    'detalhes': f'Status: {status.get("integration_active", "N/A")}'
                })
            else:
                resultados.append({
                    'teste': 'IntegrationManager.get_integration_status',
                    'status': 'falhou',
                    'detalhes': 'Método não encontrado'
                })
                
        except Exception as e:
            resultados.append({
                'teste': 'IntegrationManager',
                'status': 'falhou',
                'detalhes': f'Erro: {str(e)}'
            })
        
        # Testar ProcessorRegistry
        try:
            from app.claude_ai_novo.utils.processor_registry import get_processor_registry
            registry = get_processor_registry()
            
            processadores = registry.list_processors()
            if len(processadores) >= 6:
                resultados.append({
                    'teste': 'ProcessorRegistry',
                    'status': 'aprovado',
                    'detalhes': f'{len(processadores)} processadores registrados'
                })
            else:
                resultados.append({
                    'teste': 'ProcessorRegistry',
                    'status': 'warning',
                    'detalhes': f'Apenas {len(processadores)} processadores (esperados 6+)'
                })
                
        except Exception as e:
            resultados.append({
                'teste': 'ProcessorRegistry',
                'status': 'falhou',
                'detalhes': f'Erro: {str(e)}'
            })
        
        return {'resultados': resultados}
    
    def _testar_orchestrators(self) -> Dict[str, Any]:
        """Testa módulo orchestrators"""
        resultados = []
        
        try:
            from app.claude_ai_novo.orchestrators import get_orchestrator_manager
            orchestrator_manager = get_orchestrator_manager()
            
            # Testar method process_query
            if hasattr(orchestrator_manager, 'process_query'):
                resultados.append({
                    'teste': 'Orchestrator.process_query',
                    'status': 'aprovado',
                    'detalhes': 'Método existe'
                })
            else:
                resultados.append({
                    'teste': 'Orchestrator.process_query',
                    'status': 'falhou',
                    'detalhes': 'Método não encontrado'
                })
                
        except Exception as e:
            resultados.append({
                'teste': 'Orchestrators Module',
                'status': 'falhou',
                'detalhes': f'Erro: {str(e)}'
            })
        
        return {'resultados': resultados}
    
    def _testar_integration_manager(self) -> Dict[str, Any]:
        """Testa Integration Manager detalhadamente"""
        resultados = []
        
        try:
            from app.claude_ai_novo.integration.integration_manager import IntegrationManager
            manager = IntegrationManager()
            
            # Testar métodos principais
            metodos_testar = [
                'get_integration_status',
                'get_system_status',
                'initialize_all_modules',
                'process_unified_query'
            ]
            
            for metodo in metodos_testar:
                if hasattr(manager, metodo):
                    resultados.append({
                        'teste': f'IntegrationManager.{metodo}',
                        'status': 'aprovado',
                        'detalhes': 'Método existe'
                    })
                else:
                    resultados.append({
                        'teste': f'IntegrationManager.{metodo}',
                        'status': 'falhou',
                        'detalhes': 'Método não encontrado'
                    })
                    
        except Exception as e:
            resultados.append({
                'teste': 'Integration Manager',
                'status': 'falhou',
                'detalhes': f'Erro: {str(e)}'
            })
        
        return {'resultados': resultados}
    
    def _testar_processor_registry(self) -> Dict[str, Any]:
        """Testa Processor Registry detalhadamente"""
        resultados = []
        
        try:
            from app.claude_ai_novo.utils.processor_registry import get_processor_registry
            registry = get_processor_registry()
            
            # Testar processadores esperados
            processadores_esperados = [
                'context', 'response', 'semantic_loop', 
                'query', 'intelligence', 'data'
            ]
            
            processadores_encontrados = registry.list_processors()
            
            for processador in processadores_esperados:
                if processador in processadores_encontrados:
                    resultados.append({
                        'teste': f'Processor {processador}',
                        'status': 'aprovado',
                        'detalhes': 'Registrado'
                    })
                else:
                    resultados.append({
                        'teste': f'Processor {processador}',
                        'status': 'falhou',
                        'detalhes': 'Não registrado'
                    })
                    
        except Exception as e:
            resultados.append({
                'teste': 'Processor Registry',
                'status': 'falhou',
                'detalhes': f'Erro: {str(e)}'
            })
        
        return {'resultados': resultados}
    
    def _testar_analyzers(self) -> Dict[str, Any]:
        """Testa módulo analyzers"""
        resultados = []
        
        try:
            from app.claude_ai_novo.analyzers import get_analyzer_manager
            analyzer_manager = get_analyzer_manager()
            
            if analyzer_manager:
                resultados.append({
                    'teste': 'AnalyzerManager',
                    'status': 'aprovado',
                    'detalhes': 'Criado com sucesso'
                })
            else:
                resultados.append({
                    'teste': 'AnalyzerManager',
                    'status': 'falhou',
                    'detalhes': 'Retornou None'
                })
                
        except Exception as e:
            resultados.append({
                'teste': 'Analyzers Module',
                'status': 'falhou',
                'detalhes': f'Erro: {str(e)}'
            })
        
        return {'resultados': resultados}
    
    def _testar_mappers(self) -> Dict[str, Any]:
        """Testa módulo mappers"""
        resultados = []
        
        try:
            from app.claude_ai_novo.mappers import get_mapper_manager
            mapper_manager = get_mapper_manager()
            
            if mapper_manager:
                resultados.append({
                    'teste': 'MapperManager',
                    'status': 'aprovado',
                    'detalhes': 'Criado com sucesso'
                })
            else:
                resultados.append({
                    'teste': 'MapperManager',
                    'status': 'falhou',
                    'detalhes': 'Retornou None'
                })
                
        except Exception as e:
            resultados.append({
                'teste': 'Mappers Module',
                'status': 'falhou',
                'detalhes': f'Erro: {str(e)}'
            })
        
        return {'resultados': resultados}
    
    def _testar_validators(self) -> Dict[str, Any]:
        """Testa módulo validators"""
        resultados = []
        
        try:
            from app.claude_ai_novo.validators import get_validator_manager
            validator_manager = get_validator_manager()
            
            if validator_manager:
                resultados.append({
                    'teste': 'ValidatorManager',
                    'status': 'aprovado',
                    'detalhes': 'Criado com sucesso'
                })
            else:
                resultados.append({
                    'teste': 'ValidatorManager',
                    'status': 'falhou',
                    'detalhes': 'Retornou None'
                })
                
        except Exception as e:
            resultados.append({
                'teste': 'Validators Module',
                'status': 'falhou',
                'detalhes': f'Erro: {str(e)}'
            })
        
        return {'resultados': resultados}
    
    def _testar_providers(self) -> Dict[str, Any]:
        """Testa módulo providers"""
        resultados = []
        
        try:
            from app.claude_ai_novo.providers import get_provider_manager
            provider_manager = get_provider_manager()
            
            if provider_manager:
                resultados.append({
                    'teste': 'ProviderManager',
                    'status': 'aprovado',
                    'detalhes': 'Criado com sucesso'
                })
            else:
                resultados.append({
                    'teste': 'ProviderManager',
                    'status': 'falhou',
                    'detalhes': 'Retornou None'
                })
                
        except Exception as e:
            resultados.append({
                'teste': 'Providers Module',
                'status': 'falhou',
                'detalhes': f'Erro: {str(e)}'
            })
        
        return {'resultados': resultados}
    
    def _testar_memorizers(self) -> Dict[str, Any]:
        """Testa módulo memorizers"""
        resultados = []
        
        try:
            from app.claude_ai_novo.memorizers import get_memory_manager
            memory_manager = get_memory_manager()
            
            if memory_manager:
                resultados.append({
                    'teste': 'MemoryManager',
                    'status': 'aprovado',
                    'detalhes': 'Criado com sucesso'
                })
            else:
                resultados.append({
                    'teste': 'MemoryManager',
                    'status': 'falhou',
                    'detalhes': 'Retornou None'
                })
                
        except Exception as e:
            resultados.append({
                'teste': 'Memorizers Module',
                'status': 'falhou',
                'detalhes': f'Erro: {str(e)}'
            })
        
        return {'resultados': resultados}
    
    def _testar_enrichers(self) -> Dict[str, Any]:
        """Testa módulo enrichers"""
        resultados = []
        
        try:
            from app.claude_ai_novo.enrichers.semantic_enricher import SemanticEnricher
            enricher = SemanticEnricher()
            
            if enricher:
                resultados.append({
                    'teste': 'SemanticEnricher',
                    'status': 'aprovado',
                    'detalhes': 'Criado com sucesso'
                })
            else:
                resultados.append({
                    'teste': 'SemanticEnricher',
                    'status': 'falhou',
                    'detalhes': 'Retornou None'
                })
                
        except Exception as e:
            resultados.append({
                'teste': 'Enrichers Module',
                'status': 'falhou',
                'detalhes': f'Erro: {str(e)}'
            })
        
        return {'resultados': resultados}
    
    def _testar_utils(self) -> Dict[str, Any]:
        """Testa módulo utils"""
        resultados = []
        
        try:
            from app.claude_ai_novo.utils import get_utils_manager
            utils_manager = get_utils_manager()
            
            if utils_manager:
                resultados.append({
                    'teste': 'UtilsManager',
                    'status': 'aprovado',
                    'detalhes': 'Criado com sucesso'
                })
            else:
                resultados.append({
                    'teste': 'UtilsManager',
                    'status': 'falhou',
                    'detalhes': 'Retornou None'
                })
                
        except Exception as e:
            resultados.append({
                'teste': 'Utils Module',
                'status': 'falhou',
                'detalhes': f'Erro: {str(e)}'
            })
        
        return {'resultados': resultados}
    
    def _testar_commands(self) -> Dict[str, Any]:
        """Testa módulo commands"""
        resultados = []
        
        try:
            from app.claude_ai_novo.commands import get_command_manager
            command_manager = get_command_manager()
            
            if command_manager:
                resultados.append({
                    'teste': 'CommandManager',
                    'status': 'aprovado',
                    'detalhes': 'Criado com sucesso'
                })
            else:
                resultados.append({
                    'teste': 'CommandManager',
                    'status': 'falhou',
                    'detalhes': 'Retornou None'
                })
                
        except Exception as e:
            resultados.append({
                'teste': 'Commands Module',
                'status': 'falhou',
                'detalhes': f'Erro: {str(e)}'
            })
        
        return {'resultados': resultados}
    
    def _testar_security(self) -> Dict[str, Any]:
        """Testa módulo security"""
        resultados = []
        
        try:
            from app.claude_ai_novo.security import get_security_guard
            security_guard = get_security_guard()
            
            if security_guard:
                resultados.append({
                    'teste': 'SecurityGuard',
                    'status': 'aprovado',
                    'detalhes': 'Criado com sucesso'
                })
            else:
                resultados.append({
                    'teste': 'SecurityGuard',
                    'status': 'falhou',
                    'detalhes': 'Retornou None'
                })
                
        except Exception as e:
            resultados.append({
                'teste': 'Security Module',
                'status': 'falhou',
                'detalhes': f'Erro: {str(e)}'
            })
        
        return {'resultados': resultados}
    
    def _testar_performance(self) -> Dict[str, Any]:
        """Testa performance básica"""
        resultados = []
        
        try:
            # Teste de import speed
            start_time = time.time()
            from app.claude_ai_novo.orchestrators import get_orchestrator_manager
            orchestrator_manager = get_orchestrator_manager()
            import_time = time.time() - start_time
            
            if import_time < 5.0:  # Menos de 5 segundos
                resultados.append({
                    'teste': 'Performance Import',
                    'status': 'aprovado',
                    'detalhes': f'Tempo: {import_time:.2f}s'
                })
            else:
                resultados.append({
                    'teste': 'Performance Import',
                    'status': 'warning',
                    'detalhes': f'Tempo lento: {import_time:.2f}s'
                })
                
        except Exception as e:
            resultados.append({
                'teste': 'Performance Test',
                'status': 'falhou',
                'detalhes': f'Erro: {str(e)}'
            })
        
        return {'resultados': resultados}
    
    def _testar_health_checks(self) -> Dict[str, Any]:
        """Testa health checks do sistema"""
        resultados = []
        
        try:
            # Testar health check do OrchestratorManager
            from app.claude_ai_novo.orchestrators import get_orchestrator_manager
            orchestrator_manager = get_orchestrator_manager()
            
            if hasattr(orchestrator_manager, 'health_check'):
                health = orchestrator_manager.health_check()
                resultados.append({
                    'teste': 'Orchestrator Health Check',
                    'status': 'aprovado' if health else 'warning',
                    'detalhes': f'Status: {health}'
                })
            else:
                resultados.append({
                    'teste': 'Orchestrator Health Check',
                    'status': 'warning',
                    'detalhes': 'Método não implementado'
                })
                
        except Exception as e:
            resultados.append({
                'teste': 'Health Checks',
                'status': 'falhou',
                'detalhes': f'Erro: {str(e)}'
            })
        
        return {'resultados': resultados}
    
    def _testar_fallbacks(self) -> Dict[str, Any]:
        """Testa sistemas de fallback"""
        resultados = []
        
        try:
            # Testar fallback do ProcessorRegistry
            from app.claude_ai_novo.utils.processor_registry import get_processor_registry
            registry = get_processor_registry()
            
            # Verificar se tem fallbacks
            stats = registry.get_registry_stats()
            if stats.get('healthy_processors', 0) > 0:
                resultados.append({
                    'teste': 'Processor Fallbacks',
                    'status': 'aprovado',
                    'detalhes': f'{stats["healthy_processors"]} processadores saudáveis'
                })
            else:
                resultados.append({
                    'teste': 'Processor Fallbacks',
                    'status': 'warning',
                    'detalhes': 'Nenhum processador saudável'
                })
                
        except Exception as e:
            resultados.append({
                'teste': 'Fallback Systems',
                'status': 'falhou',
                'detalhes': f'Erro: {str(e)}'
            })
        
        return {'resultados': resultados}
    
    def _processar_resultado_teste(self, nome_teste: str, resultado: Dict[str, Any]):
        """Processa resultado de um teste"""
        resultados = resultado.get('resultados', [])
        
        for res in resultados:
            self.resultados['detalhes_testes'].append({
                'categoria': nome_teste,
                'teste': res['teste'],
                'status': res['status'],
                'detalhes': res['detalhes'],
                'timestamp': datetime.now().isoformat()
            })
            
            self.resultados['testes_executados'] += 1
            
            if res['status'] == 'aprovado':
                self.resultados['testes_aprovados'] += 1
                print(f"  ✅ {res['teste']}: {res['detalhes']}")
            elif res['status'] == 'warning':
                self.resultados['testes_warning'] += 1
                print(f"  ⚠️ {res['teste']}: {res['detalhes']}")
            else:
                self.resultados['testes_falharam'] += 1
                print(f"  ❌ {res['teste']}: {res['detalhes']}")
    
    def _processar_erro_teste(self, nome_teste: str, erro: Exception):
        """Processa erro de um teste"""
        self.resultados['detalhes_testes'].append({
            'categoria': nome_teste,
            'teste': nome_teste,
            'status': 'falhou',
            'detalhes': f'Erro inesperado: {str(erro)}',
            'timestamp': datetime.now().isoformat()
        })
        
        self.resultados['testes_executados'] += 1
        self.resultados['testes_falharam'] += 1
        
        print(f"  ❌ {nome_teste}: Erro inesperado - {str(erro)}")
    
    def _calcular_score_final(self):
        """Calcula score final baseado nos resultados"""
        total_testes = self.resultados['testes_executados']
        
        if total_testes == 0:
            self.resultados['score_geral'] = 0.0
            return
        
        # Aprovados = 100%, Warnings = 50%, Falhas = 0%
        score = (
            (self.resultados['testes_aprovados'] * 100) +
            (self.resultados['testes_warning'] * 50) +
            (self.resultados['testes_falharam'] * 0)
        ) / total_testes
        
        self.resultados['score_geral'] = round(score, 1)
    
    def _gerar_recomendacoes(self):
        """Gera recomendações baseadas nos resultados"""
        recomendacoes = []
        
        # Análise de falhas
        if self.resultados['testes_falharam'] > 0:
            recomendacoes.append(f"🔴 CRÍTICO: {self.resultados['testes_falharam']} testes falharam - correção imediata necessária")
        
        # Análise de warnings
        if self.resultados['testes_warning'] > 5:
            recomendacoes.append(f"🟡 ATENÇÃO: {self.resultados['testes_warning']} warnings - revisar e corrigir")
        
        # Análise de score
        if self.resultados['score_geral'] < 80:
            recomendacoes.append("📊 QUALIDADE: Score abaixo de 80% - sistema precisa de melhorias")
        elif self.resultados['score_geral'] < 95:
            recomendacoes.append("📈 OTIMIZAÇÃO: Score bom mas pode ser melhorado")
        else:
            recomendacoes.append("🎉 EXCELENTE: Sistema funcionando perfeitamente!")
        
        # Análise de componentes críticos
        falhas_criticas = [
            t for t in self.resultados['detalhes_testes'] 
            if t['status'] == 'falhou' and any(comp in t['teste'].lower() for comp in ['orchestrator', 'integration', 'processor'])
        ]
        
        if falhas_criticas:
            recomendacoes.append(f"⚡ CRÍTICO: {len(falhas_criticas)} componentes críticos com falha")
        
        self.resultados['recomendacoes'] = recomendacoes
    
    def salvar_resultados(self, filename: Optional[str] = None):
        """Salva resultados em arquivo"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"validacao_completa_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.resultados, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Resultados salvos em: {filename}")
        return filename
    
    def imprimir_resumo(self):
        """Imprime resumo dos resultados"""
        print("\n" + "="*80)
        print("📊 RESUMO DA VALIDAÇÃO COMPLETA DO SISTEMA")
        print("="*80)
        
        print(f"🕒 Timestamp: {self.resultados['timestamp']}")
        print(f"📋 Testes executados: {self.resultados['testes_executados']}")
        print(f"✅ Testes aprovados: {self.resultados['testes_aprovados']}")
        print(f"⚠️ Testes com warning: {self.resultados['testes_warning']}")
        print(f"❌ Testes falharam: {self.resultados['testes_falharam']}")
        print(f"🏆 Score geral: {self.resultados['score_geral']:.1f}%")
        
        # Classificação do score
        if self.resultados['score_geral'] >= 95:
            classificacao = "🎉 EXCELENTE"
        elif self.resultados['score_geral'] >= 80:
            classificacao = "👍 BOM"
        elif self.resultados['score_geral'] >= 60:
            classificacao = "⚠️ PRECISA MELHORAR"
        else:
            classificacao = "🔴 CRÍTICO"
        
        print(f"📈 Classificação: {classificacao}")
        
        print("\n💡 RECOMENDAÇÕES PRINCIPAIS:")
        for rec in self.resultados['recomendacoes']:
            print(f"  • {rec}")
        
        # Mostrar falhas críticas
        falhas_criticas = [
            t for t in self.resultados['detalhes_testes'] 
            if t['status'] == 'falhou'
        ]
        
        if falhas_criticas:
            print("\n❌ FALHAS CRÍTICAS:")
            for falha in falhas_criticas[:5]:  # Mostrar apenas as 5 primeiras
                print(f"  • {falha['teste']}: {falha['detalhes']}")
        
        print("="*80)

def main():
    """Função principal"""
    print("🛡️ VALIDADOR SISTEMA COMPLETO")
    print("="*50)
    
    validador = ValidadorSistemaCompleto()
    resultados = validador.validar_sistema_completo()
    
    # Salvar resultados
    filename = validador.salvar_resultados()
    
    # Imprimir resumo
    validador.imprimir_resumo()
    
    print(f"\n✅ Validação completa! Arquivo: {filename}")
    print(f"🎯 Score final: {resultados['score_geral']:.1f}%")
    
    return resultados

if __name__ == "__main__":
    main() 