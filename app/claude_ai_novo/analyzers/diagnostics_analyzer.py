"""
📊 DIAGNOSTICS ANALYZER - Estatísticas e Diagnósticos
=====================================================

Módulo responsável por gerar estatísticas, diagnósticos
e relatórios completos do sistema semântico.

Responsabilidades:
- Estatísticas completas do sistema
- Diagnóstico de qualidade
- Relatórios enriquecidos
- Recomendações do sistema
"""

from typing import Dict, List, Any, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class DiagnosticsAnalyzer:
    """
    Gerador de diagnósticos e estatísticas semânticas.
    
    Produz análises completas sobre qualidade, performance
    e saúde do sistema de mapeamentos semânticos.
    """
    
    def __init__(self, orchestrator):
        """
        Inicializa o módulo de diagnósticos.
        
        Args:
            orchestrator: Instância do SemanticOrchestrator
        """
        self.orchestrator = orchestrator
        self._scanning_manager = None
        logger.info("📊 DiagnosticsAnalyzer inicializado")
    
    @property
    def scanning_manager(self):
        """Lazy loading do ScanningManager"""
        if self._scanning_manager is None:
            try:
                from app.claude_ai_novo.scanning import get_scanning_manager
                self._scanning_manager = get_scanning_manager()
            except ImportError:
                logger.warning("⚠️ ScanningManager não disponível")
                self._scanning_manager = False
        return self._scanning_manager if self._scanning_manager is not False else None
    
    def gerar_estatisticas_completas(self) -> Dict[str, Any]:
        """
        Gera estatísticas completas do sistema de mapeamento.
        
        Returns:
            Dict com estatísticas detalhadas
        """
        estatisticas = {
            'timestamp': datetime.now().isoformat(),
            'mappers_ativos': len(self.orchestrator.mappers),
            'total_campos': 0,
            'total_termos_naturais': 0,
            'media_termos_por_campo': 0,
            'campos_deprecated': 0,
            'modelos_cobertos': [],
            'estatisticas_por_mapper': {}
        }
        
        # Calcular estatísticas por mapper
        for nome_mapper, mapper in self.orchestrator.mappers.items():
            try:
                stats_mapper = mapper.gerar_estatisticas()
                estatisticas['estatisticas_por_mapper'][nome_mapper] = stats_mapper
                
                # Acumular totais
                estatisticas['total_campos'] += stats_mapper['total_campos']
                estatisticas['total_termos_naturais'] += stats_mapper['total_termos_naturais']
                estatisticas['campos_deprecated'] += stats_mapper['campos_deprecated']
                estatisticas['modelos_cobertos'].append(stats_mapper['modelo'])
                
            except Exception as e:
                logger.error(f"❌ Erro ao gerar estatísticas para {nome_mapper}: {e}")
        
        # Calcular médias
        if estatisticas['total_campos'] > 0:
            estatisticas['media_termos_por_campo'] = (
                estatisticas['total_termos_naturais'] / estatisticas['total_campos']
            )
        
        # Avaliar qualidade geral
        estatisticas['qualidade'] = self._avaliar_qualidade_geral(estatisticas)
        
        return estatisticas
    
    def diagnosticar_qualidade(self) -> Dict[str, Any]:
        """
        Executa diagnóstico de qualidade dos mapeamentos.
        
        Returns:
            Dict com diagnóstico detalhado
        """
        diagnostico = {
            'timestamp': datetime.now().isoformat(),
            'status_geral': 'OK',
            'erros_encontrados': [],
            'warnings': [],
            'mappers_validados': 0,
            'mappers_com_erro': 0,
            'pontuacao_qualidade': 0
        }
        
        total_pontos = 0
        pontos_obtidos = 0
        
        # Validar cada mapper
        for nome_mapper, mapper in self.orchestrator.mappers.items():
            try:
                erros_mapper = mapper.validar_mapeamentos()
                diagnostico['mappers_validados'] += 1
                total_pontos += 100
                
                if erros_mapper:
                    diagnostico['mappers_com_erro'] += 1
                    diagnostico['erros_encontrados'].extend([
                        f"[{nome_mapper}] {erro}" for erro in erros_mapper
                    ])
                    pontos_obtidos += max(0, 100 - len(erros_mapper) * 20)
                else:
                    pontos_obtidos += 100
                    
            except Exception as e:
                diagnostico['mappers_com_erro'] += 1
                diagnostico['erros_encontrados'].append(
                    f"[{nome_mapper}] Erro na validação: {e}"
                )
        
        # Calcular pontuação geral
        if total_pontos > 0:
            diagnostico['pontuacao_qualidade'] = (pontos_obtidos / total_pontos) * 100
        
        # Determinar status geral
        diagnostico['status_geral'] = self._determinar_status_geral(diagnostico)
        
        return diagnostico
    
    def _avaliar_qualidade_geral(self, estatisticas: Dict[str, Any]) -> str:
        """
        Avalia qualidade geral baseada nas estatísticas.
        
        Args:
            estatisticas: Estatísticas do sistema
            
        Returns:
            Qualidade geral do sistema
        """
        total_campos = estatisticas.get('total_campos', 0)
        
        if total_campos == 0:
            return 'INDEFINIDA'
        
        campos_deprecated = estatisticas.get('campos_deprecated', 0)
        taxa_deprecated = campos_deprecated / total_campos
        media_termos = estatisticas.get('media_termos_por_campo', 0)
        
        # Critérios de qualidade
        if taxa_deprecated < 0.05 and media_termos >= 3:
            return 'EXCELENTE'
        elif taxa_deprecated < 0.1 and media_termos >= 2:
            return 'BOA'
        elif taxa_deprecated < 0.2 and media_termos >= 1:
            return 'REGULAR'
        else:
            return 'RUIM'
    
    def _determinar_status_geral(self, diagnostico: Dict[str, Any]) -> str:
        """
        Determina status geral baseado no diagnóstico.
        
        Args:
            diagnostico: Dados do diagnóstico
            
        Returns:
            Status geral do sistema
        """
        pontuacao = diagnostico.get('pontuacao_qualidade', 0)
        erros = len(diagnostico.get('erros_encontrados', []))
        
        if erros == 0 and pontuacao >= 90:
            return 'EXCELENTE'
        elif erros <= 2 and pontuacao >= 70:
            return 'BOM'
        elif erros <= 5 and pontuacao >= 50:
            return 'REGULAR'
        else:
            return 'CRÍTICO'
    
    def gerar_relatorio_enriquecido(self) -> Dict[str, Any]:
        """
        Gera relatório completo com dados dos scanners integrados.
        
        Returns:
            Dict com relatório enriquecido
        """
        relatorio = {
            'timestamp': datetime.now().isoformat(),
            'sistema_semantic_manager': self.gerar_estatisticas_completas(),
            'readme_scanner_status': {},
            'database_scanner_status': {},
            'integracao_status': {},
            'recomendacoes': [],
            'saude_sistema': {}
        }
        
        # Obter scanners diretamente do ScanningManager
        readme_scanner = None
        database_scanner = None
        
        if self.scanning_manager:
            readme_scanner = self.scanning_manager.get_readme_scanner()
            database_scanner = self.scanning_manager.get_database_scanner()
        
        # Status ReadmeScanner
        if readme_scanner:
            relatorio['readme_scanner_status'] = {
                'disponivel': True,
                'validacao': readme_scanner.validar_estrutura_readme()
            }
        else:
            relatorio['readme_scanner_status'] = {'disponivel': False}
        
        # Status DatabaseScanner
        if database_scanner:
            relatorio['database_scanner_status'] = {
                'disponivel': True,
                'estatisticas': database_scanner.obter_estatisticas_gerais()
            }
        else:
            relatorio['database_scanner_status'] = {'disponivel': False}
        
        # Status da integração
        relatorio['integracao_status'] = self._avaliar_integracao(readme_scanner, database_scanner)
        
        # Saúde geral do sistema
        relatorio['saude_sistema'] = self._verificar_saude_sistema()
        
        # Gerar recomendações
        relatorio['recomendacoes'] = self._gerar_recomendacoes_sistema(relatorio)
        
        return relatorio
    
    def _avaliar_integracao(self, readme_scanner, database_scanner) -> Dict[str, Any]:
        """
        Avalia status da integração dos scanners.
        
        Args:
            readme_scanner: Instância do ReadmeScanner
            database_scanner: Instância do DatabaseScanner
            
        Returns:
            Status da integração
        """
        status = {
            'scanners_integrados': 2,
            'scanners_funcionais': sum([
                readme_scanner is not None,
                database_scanner is not None
            ]),
            'consistencia_validacao': {}
        }
        
        # Executar validação de consistência se ambos disponíveis
        if readme_scanner and database_scanner:
            try:
                from app.claude_ai_novo.validators.semantic_validator import get_semantic_validator
                validator = get_semantic_validator(self.orchestrator)
                status['consistencia_validacao'] = validator.validar_consistencia_readme_banco()
            except Exception as e:
                status['consistencia_validacao'] = {'erro': str(e)}
        
        return status
    
    def _verificar_saude_sistema(self) -> Dict[str, Any]:
        """
        Verifica a saúde do sistema baseado nos componentes disponíveis.
        
        Returns:
            Dict com status de saúde
        """
        saude = {
            'timestamp': datetime.now().isoformat(),
            'status_geral': 'OK',
            'scanning_manager_disponivel': self.scanning_manager is not None,
            'readme_scanner_disponivel': False,
            'database_scanner_disponivel': False
        }
        
        # Verificar scanners
        if self.scanning_manager:
            readme_scanner = self.scanning_manager.get_readme_scanner()
            database_scanner = self.scanning_manager.get_database_scanner()
            saude['readme_scanner_disponivel'] = readme_scanner is not None
            saude['database_scanner_disponivel'] = database_scanner is not None
        
        # Determinar status geral baseado em componentes disponíveis
        componentes_disponiveis = sum([
            saude['scanning_manager_disponivel'],
            saude['readme_scanner_disponivel'],
            saude['database_scanner_disponivel']
        ])
        
        if componentes_disponiveis >= 3:
            saude['status_geral'] = 'EXCELENTE'
        elif componentes_disponiveis >= 2:
            saude['status_geral'] = 'BOM'
        elif componentes_disponiveis >= 1:
            saude['status_geral'] = 'REGULAR'
        else:
            saude['status_geral'] = 'CRÍTICO'
            
        return saude
    
    def _gerar_recomendacoes_sistema(self, relatorio: Dict[str, Any]) -> List[str]:
        """
        Gera recomendações baseadas no relatório.
        
        Args:
            relatorio: Relatório do sistema
            
        Returns:
            Lista de recomendações
        """
        recomendacoes = []
        
        # Verificar scanners funcionais
        integracao = relatorio.get('integracao_status', {})
        scanners_funcionais = integracao.get('scanners_funcionais', 0)
        
        if scanners_funcionais < 2:
            recomendacoes.append("🔧 Ativar todos os scanners para funcionalidade completa")
        
        # Verificar qualidade do README
        readme_status = relatorio.get('readme_scanner_status', {})
        if readme_status.get('disponivel'):
            validacao = readme_status.get('validacao', {})
            warnings = validacao.get('warnings', [])
            if warnings:
                recomendacoes.append(f"📄 Melhorar README: {len(warnings)} avisos encontrados")
        
        # Verificar banco de dados
        db_status = relatorio.get('database_scanner_status', {})
        if db_status.get('disponivel'):
            stats = db_status.get('estatisticas', {})
            total_tabelas = stats.get('total_tabelas', 0)
            if total_tabelas > 50:
                recomendacoes.append(f"📊 Banco com {total_tabelas} tabelas - considerar otimização de cache")
        
        # Verificar consistência
        consistencia = integracao.get('consistencia_validacao', {})
        inconsistencias = len(consistencia.get('inconsistencias', []))
        if inconsistencias > 0:
            recomendacoes.append(f"⚠️ Resolver {inconsistencias} inconsistências README/Banco")
        
        # Verificar saúde geral
        saude = relatorio.get('saude_sistema', {})
        status_geral = saude.get('status_geral', 'CRÍTICO')
        if status_geral in ['REGULAR', 'CRÍTICO']:
            recomendacoes.append(f"🚨 Status geral {status_geral} - requer atenção")
        
        # Verificar sistema de mapeamentos
        sistema = relatorio.get('sistema_semantic_manager', {})
        qualidade = sistema.get('qualidade', 'INDEFINIDA')
        if qualidade in ['REGULAR', 'RUIM']:
            recomendacoes.append(f"📈 Qualidade dos mapeamentos {qualidade} - melhorar documentação")
        
        return recomendacoes
    
    def gerar_relatorio_resumido(self) -> Dict[str, Any]:
        """
        Gera relatório resumido para dashboard.
        
        Returns:
            Dict com relatório resumido
        """
        estatisticas = self.gerar_estatisticas_completas()
        diagnostico = self.diagnosticar_qualidade()
        saude = self._verificar_saude_sistema()
        
        return {
            'timestamp': datetime.now().isoformat(),
            'resumo': {
                'mappers_ativos': estatisticas['mappers_ativos'],
                'total_campos': estatisticas['total_campos'],
                'qualidade_geral': estatisticas['qualidade'],
                'status_sistema': saude['status_geral'],
                'pontuacao_qualidade': diagnostico['pontuacao_qualidade']
            },
            'alertas': {
                'erros_criticos': len(diagnostico['erros_encontrados']),
                'scanners_indisponiveis': 2 - sum([
                    saude['readme_scanner_disponivel'],
                    saude['database_scanner_disponivel']
                ])
            },
            'metricas_rapidas': {
                'media_termos_campo': estatisticas['media_termos_por_campo'],
                'taxa_deprecated': (
                    estatisticas['campos_deprecated'] / estatisticas['total_campos'] * 100
                    if estatisticas['total_campos'] > 0 else 0
                )
            }
        }


# Função de conveniência
def get_diagnostics_analyzer(orchestrator) -> DiagnosticsAnalyzer:
    """
    Obtém instância do módulo de diagnósticos.
    
    Args:
        orchestrator: Instância do SemanticOrchestrator
        
    Returns:
        Instância do DiagnosticsAnalyzer
    """
    return DiagnosticsAnalyzer(orchestrator) 