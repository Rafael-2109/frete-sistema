"""
Workflow Orchestrator - Orquestração de Fluxos de Trabalho
Responsabilidade: ORQUESTRAR fluxos de trabalho complexos e sequenciais
"""

import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime

logger = logging.getLogger(__name__)

class WorkflowOrchestrator:
    """
    Orquestrador de fluxos de trabalho complexos.
    
    Responsabilidades:
    - Orquestrar sequências de tarefas
    - Gerenciar dependências entre etapas
    - Controlar fluxo de execução
    - Monitorar progresso de workflows
    """
    
    def __init__(self):
        """
        Inicializa o orquestrador de workflows.
        """
        self.workflows_ativos: Dict[str, Dict[str, Any]] = {}
        self.templates_workflow: Dict[str, List[Dict[str, Any]]] = {}
        self.executores: Dict[str, Callable] = {}
        
        # Registrar templates padrão
        self._registrar_templates_padrao()
        
        logger.info("🔄 WorkflowOrchestrator inicializado com templates padrão")
    
    def _registrar_templates_padrao(self) -> None:
        """
        Registra templates de workflow padrão.
        """
        # Template de análise completa
        self.templates_workflow['analise_completa'] = [
            {
                'etapa': 'validacao',
                'executor': 'validar_dados',
                'parametros': {},
                'obrigatorio': True,
                'timeout': 30
            },
            {
                'etapa': 'analise',
                'executor': 'analisar_consulta',
                'parametros': {},
                'obrigatorio': True,
                'timeout': 60,
                'dependencias': ['validacao']
            },
            {
                'etapa': 'processamento',
                'executor': 'processar_resultado',
                'parametros': {},
                'obrigatorio': True,
                'timeout': 90,
                'dependencias': ['analise']
            },
            {
                'etapa': 'finalizacao',
                'executor': 'finalizar_workflow',
                'parametros': {},
                'obrigatorio': False,
                'timeout': 30,
                'dependencias': ['processamento']
            }
        ]
        
        # Template de processamento em lote
        self.templates_workflow['processamento_lote'] = [
            {
                'etapa': 'preparacao',
                'executor': 'preparar_lote',
                'parametros': {},
                'obrigatorio': True,
                'timeout': 60
            },
            {
                'etapa': 'processamento_paralelo',
                'executor': 'processar_itens_paralelo',
                'parametros': {'max_workers': 3},
                'obrigatorio': True,
                'timeout': 300,
                'dependencias': ['preparacao']
            },
            {
                'etapa': 'consolidacao',
                'executor': 'consolidar_resultados',
                'parametros': {},
                'obrigatorio': True,
                'timeout': 60,
                'dependencias': ['processamento_paralelo']
            }
        ]
        
        logger.debug(f"📋 {len(self.templates_workflow)} templates de workflow registrados")
    
    def executar_workflow(self, workflow_id: str, template_nome: str, 
                         dados_entrada: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executa um workflow baseado em template.
        
        Args:
            workflow_id: ID único do workflow
            template_nome: Nome do template a usar
            dados_entrada: Dados de entrada do workflow
            
        Returns:
            Dict com resultado da execução
        """
        if template_nome not in self.templates_workflow:
            logger.error(f"❌ Template '{template_nome}' não encontrado")
            return {'sucesso': False, 'erro': f'Template {template_nome} não existe'}
        
        try:
            # Inicializar workflow
            workflow_info = {
                'id': workflow_id,
                'template': template_nome,
                'status': 'iniciado',
                'etapas': self.templates_workflow[template_nome].copy(),
                'dados_entrada': dados_entrada,
                'resultados_etapas': {},
                'inicio': datetime.now(),
                'progresso': 0.0
            }
            
            self.workflows_ativos[workflow_id] = workflow_info
            
            logger.info(f"🔄 Iniciando workflow '{workflow_id}' com template '{template_nome}'")
            
            # Executar etapas sequencialmente
            resultado = self._executar_etapas_workflow(workflow_id)
            
            # Finalizar workflow
            workflow_info['status'] = 'concluido' if resultado['sucesso'] else 'erro'
            workflow_info['fim'] = datetime.now()
            workflow_info['duracao'] = (workflow_info['fim'] - workflow_info['inicio']).total_seconds()
            
            logger.info(f"✅ Workflow '{workflow_id}' {'concluído' if resultado['sucesso'] else 'falhou'} em {workflow_info['duracao']:.2f}s")
            
            return resultado
            
        except Exception as e:
            logger.error(f"❌ Erro na execução do workflow '{workflow_id}': {e}")
            if workflow_id in self.workflows_ativos:
                self.workflows_ativos[workflow_id]['status'] = 'erro'
                self.workflows_ativos[workflow_id]['erro'] = str(e)
            
            return {'sucesso': False, 'erro': str(e)}
    
    def _executar_etapas_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """
        Executa as etapas de um workflow.
        
        Args:
            workflow_id: ID do workflow
            
        Returns:
            Dict com resultado da execução
        """
        workflow_info = self.workflows_ativos[workflow_id]
        etapas = workflow_info['etapas']
        total_etapas = len(etapas)
        
        resultados = {}
        etapas_concluidas = set()
        
        for i, etapa_config in enumerate(etapas):
            etapa_nome = etapa_config['etapa']
            
            try:
                # Verificar dependências
                dependencias = etapa_config.get('dependencias', [])
                if not all(dep in etapas_concluidas for dep in dependencias):
                    dependencias_pendentes = [dep for dep in dependencias if dep not in etapas_concluidas]
                    logger.error(f"❌ Etapa '{etapa_nome}' tem dependências pendentes: {dependencias_pendentes}")
                    return {'sucesso': False, 'erro': f'Dependências pendentes: {dependencias_pendentes}'}
                
                logger.debug(f"🔄 Executando etapa '{etapa_nome}'")
                
                # Executar etapa
                resultado_etapa = self._executar_etapa(etapa_config, workflow_info['dados_entrada'], resultados)
                
                if resultado_etapa['sucesso']:
                    resultados[etapa_nome] = resultado_etapa['resultado']
                    etapas_concluidas.add(etapa_nome)
                    
                    # Atualizar progresso
                    workflow_info['progresso'] = (i + 1) / total_etapas * 100
                    workflow_info['resultados_etapas'][etapa_nome] = resultado_etapa
                    
                    logger.debug(f"✅ Etapa '{etapa_nome}' concluída. Progresso: {workflow_info['progresso']:.1f}%")
                else:
                    # Verificar se etapa é obrigatória
                    if etapa_config.get('obrigatorio', True):
                        logger.error(f"❌ Etapa obrigatória '{etapa_nome}' falhou: {resultado_etapa.get('erro')}")
                        return {'sucesso': False, 'erro': f"Etapa '{etapa_nome}' falhou: {resultado_etapa.get('erro')}"}
                    else:
                        logger.warning(f"⚠️ Etapa opcional '{etapa_nome}' falhou, continuando: {resultado_etapa.get('erro')}")
                        etapas_concluidas.add(etapa_nome)  # Marcar como concluída mesmo com falha
                
            except Exception as e:
                logger.error(f"❌ Erro na execução da etapa '{etapa_nome}': {e}")
                if etapa_config.get('obrigatorio', True):
                    return {'sucesso': False, 'erro': f"Erro na etapa '{etapa_nome}': {str(e)}"}
        
        return {
            'sucesso': True,
            'resultados': resultados,
            'etapas_concluidas': list(etapas_concluidas),
            'progresso': 100.0
        }
    
    def _executar_etapa(self, etapa_config: Dict[str, Any], dados_entrada: Dict[str, Any], 
                       resultados_anteriores: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executa uma etapa específica do workflow.
        
        Args:
            etapa_config: Configuração da etapa
            dados_entrada: Dados de entrada do workflow
            resultados_anteriores: Resultados das etapas anteriores
            
        Returns:
            Dict com resultado da etapa
        """
        executor_nome = etapa_config['executor']
        parametros = etapa_config.get('parametros', {})
        timeout = etapa_config.get('timeout', 60)
        
        try:
            # Preparar contexto da etapa
            contexto = {
                'dados_entrada': dados_entrada,
                'resultados_anteriores': resultados_anteriores,
                'parametros': parametros,
                'timeout': timeout
            }
            
            # Executar usando executor registrado ou método padrão
            if executor_nome in self.executores:
                resultado = self.executores[executor_nome](contexto)
            else:
                resultado = self._executor_padrao(executor_nome, contexto)
            
            return {'sucesso': True, 'resultado': resultado}
            
        except Exception as e:
            logger.error(f"❌ Erro na execução do executor '{executor_nome}': {e}")
            return {'sucesso': False, 'erro': str(e)}
    
    def _executor_padrao(self, nome_executor: str, contexto: Dict[str, Any]) -> Any:
        """
        Executor padrão para etapas não especializadas.
        
        Args:
            nome_executor: Nome do executor
            contexto: Contexto da execução
            
        Returns:
            Resultado da execução
        """
        # Simulação de execução para manter compatibilidade
        if nome_executor == 'validar_dados':
            return {'dados_validos': True, 'validacoes': ['formato', 'tipo', 'conteudo']}
        
        elif nome_executor == 'analisar_consulta':
            return {'analise_concluida': True, 'tipo_consulta': 'geral', 'confianca': 0.8}
        
        elif nome_executor == 'processar_resultado':
            return {'processamento_concluido': True, 'registros_processados': 1}
        
        elif nome_executor == 'finalizar_workflow':
            return {'finalizacao_concluida': True, 'cleanup_realizado': True}
        
        elif nome_executor == 'preparar_lote':
            return {'lote_preparado': True, 'total_itens': contexto['dados_entrada'].get('total_itens', 1)}
        
        elif nome_executor == 'processar_itens_paralelo':
            return {'processamento_paralelo_concluido': True, 'itens_processados': 1}
        
        elif nome_executor == 'consolidar_resultados':
            return {'consolidacao_concluida': True, 'resultado_final': 'processado'}
        
        else:
            logger.warning(f"⚠️ Executor '{nome_executor}' não implementado, retornando resultado padrão")
            return {'executor_executado': nome_executor, 'resultado': 'padrao'}
    
    def registrar_executor(self, nome: str, executor: Callable) -> None:
        """
        Registra um executor personalizado.
        
        Args:
            nome: Nome do executor
            executor: Função executor
        """
        self.executores[nome] = executor
        logger.debug(f"📝 Executor '{nome}' registrado")
    
    def obter_status_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtém status de um workflow.
        
        Args:
            workflow_id: ID do workflow
            
        Returns:
            Dict com status do workflow ou None
        """
        return self.workflows_ativos.get(workflow_id)
    
    def listar_workflows_ativos(self) -> List[str]:
        """
        Lista workflows ativos.
        
        Returns:
            Lista de IDs de workflows ativos
        """
        return list(self.workflows_ativos.keys())
    
    def cancelar_workflow(self, workflow_id: str) -> bool:
        """
        Cancela um workflow ativo.
        
        Args:
            workflow_id: ID do workflow
            
        Returns:
            True se cancelado com sucesso
        """
        if workflow_id in self.workflows_ativos:
            self.workflows_ativos[workflow_id]['status'] = 'cancelado'
            self.workflows_ativos[workflow_id]['fim'] = datetime.now()
            logger.info(f"⏹️ Workflow '{workflow_id}' cancelado")
            return True
        return False
    
    def limpar_workflows_concluidos(self) -> int:
        """
        Remove workflows concluídos da memória.
        
        Returns:
            Número de workflows removidos
        """
        workflows_para_remover = [
            wf_id for wf_id, wf_info in self.workflows_ativos.items()
            if wf_info['status'] in ['concluido', 'erro', 'cancelado']
        ]
        
        for wf_id in workflows_para_remover:
            del self.workflows_ativos[wf_id]
        
        logger.debug(f"🧹 {len(workflows_para_remover)} workflows concluídos removidos")
        return len(workflows_para_remover)
    
    def obter_estatisticas(self) -> Dict[str, Any]:
        """
        Obtém estatísticas dos workflows.
        
        Returns:
            Dict com estatísticas
        """
        if not self.workflows_ativos:
            return {'total_workflows': 0, 'workflows_por_status': {}}
        
        status_counts = {}
        for wf_info in self.workflows_ativos.values():
            status = wf_info['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            'total_workflows': len(self.workflows_ativos),
            'workflows_por_status': status_counts,
            'templates_disponiveis': list(self.templates_workflow.keys()),
            'executores_registrados': list(self.executores.keys())
        }

# Função de conveniência
def get_workflow_orchestrator() -> WorkflowOrchestrator:
    """Retorna instância configurada do WorkflowOrchestrator."""
    return WorkflowOrchestrator()

# Export explícito
__all__ = [
    'WorkflowOrchestrator',
    'get_workflow_orchestrator'
] 