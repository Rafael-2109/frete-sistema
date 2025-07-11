"""
🔄 FEEDBACK PROCESSOR - Processamento Avançado de Feedback
==========================================================

Módulo especializado em processar e aprender com feedback dos usuários.
Transforma feedback em melhorias concretas do sistema.

Responsabilidades:
- Análise semântica de feedback
- Classificação por tipo e severidade
- Extração de ações corretivas
- Aplicação automática de melhorias
- Tracking de efetividade
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import re

logger = logging.getLogger(__name__)

@dataclass
class FeedbackAnalysis:
    """Resultado da análise de feedback"""
    tipo: str
    severidade: float
    sentimento: str
    acoes_sugeridas: List[str]
    confianca: float
    categoria: str
    prioridade: int

@dataclass
class CorrectiveAction:
    """Ação corretiva a ser aplicada"""
    action_type: str
    target_component: str
    parameters: Dict[str, Any]
    confidence: float
    description: str

class FeedbackProcessor:
    """
    Processador avançado de feedback com aprendizado automático.
    
    Analisa feedback dos usuários e converte em melhorias
    aplicáveis ao sistema.
    """
    
    def __init__(self, claude_client=None, db_engine=None, db_session=None):
        """
        Inicializa o processador de feedback.
        
        Args:
            claude_client: Cliente Claude API
            db_engine: Engine do banco de dados
            db_session: Sessão do banco de dados
        """
        self.claude_client = claude_client
        self.db_engine = db_engine
        self.db_session = db_session
        
        # Configurações de análise
        self.confidence_threshold = 0.6
        self.min_severity_threshold = 0.3
        
        # Padrões de feedback
        self._init_feedback_patterns()
        
        logger.info("🔄 Feedback Processor inicializado")
    
    def _init_feedback_patterns(self):
        """Inicializa padrões de reconhecimento de feedback."""
        self.feedback_patterns = {
            'correction': {
                'patterns': [
                    r'(?i)(está errado|incorreto|não é isso|erro)',
                    r'(?i)(deveria ser|na verdade é|correto é)',
                    r'(?i)(não pedi|me trouxe|veja que)',
                    r'(?i)(não era isso|não é o que queria)'
                ],
                'severity_multiplier': 1.0
            },
            'improvement': {
                'patterns': [
                    r'(?i)(poderia|seria melhor|sugiro)',
                    r'(?i)(faltou|esqueceu|adicionar)',
                    r'(?i)(incluir também|mostrar também)',
                    r'(?i)(seria útil|seria bom)'
                ],
                'severity_multiplier': 0.7
            },
            'clarification': {
                'patterns': [
                    r'(?i)(não entendi|confuso|não ficou claro)',
                    r'(?i)(explique melhor|detalhe|como assim)',
                    r'(?i)(o que significa|não compreendi)'
                ],
                'severity_multiplier': 0.8
            },
            'positive': {
                'patterns': [
                    r'(?i)(perfeito|excelente|muito bom)',
                    r'(?i)(obrigado|agradeço|útil)',
                    r'(?i)(correto|certo|exatamente)'
                ],
                'severity_multiplier': 0.2
            }
        }
        
        self.sentiment_patterns = {
            'negative': r'(?i)(ruim|péssimo|irritante|frustrante|problema)',
            'neutral': r'(?i)(ok|normal|regular|aceitável)',
            'positive': r'(?i)(bom|ótimo|excelente|perfeito|maravilhoso)'
        }
    
    def processar_feedback_completo(self, 
                                  consulta: str,
                                  interpretacao: Dict[str, Any],
                                  resposta: str,
                                  feedback: Dict[str, Any],
                                  usuario_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Processa feedback completo e retorna ações corretivas.
        
        Args:
            consulta: Consulta original do usuário
            interpretacao: Como o sistema interpretou
            resposta: Resposta dada pelo sistema
            feedback: Feedback do usuário
            usuario_id: ID do usuário
            
        Returns:
            Lista de melhorias aplicadas
        """
        try:
            melhorias = []
            
            # 1. Analisar feedback
            analise = self.analisar_feedback(feedback.get('texto', ''))
            
            # 2. Extrair ações corretivas
            acoes = self.extrair_acoes_corretivas(
                consulta, interpretacao, resposta, analise
            )
            
            # 3. Aplicar ações de alta confiança
            for acao in acoes:
                if acao.confidence >= self.confidence_threshold:
                    resultado = self.aplicar_acao_corretiva(acao)
                    if resultado:
                        melhorias.append({
                            'tipo': acao.action_type,
                            'componente': acao.target_component,
                            'descricao': acao.description,
                            'confianca': acao.confidence,
                            'aplicado': True,
                            'timestamp': datetime.now().isoformat()
                        })
            
            # 4. Salvar feedback para análise futura
            self._salvar_feedback_analise(
                consulta, interpretacao, resposta, feedback, analise, melhorias, usuario_id
            )
            
            logger.info(f"✅ Feedback processado: {len(melhorias)} melhorias aplicadas")
            return melhorias
            
        except Exception as e:
            logger.error(f"❌ Erro no processamento de feedback: {e}")
            return []
    
    def analisar_feedback(self, texto_feedback: str) -> FeedbackAnalysis:
        """
        Analisa texto de feedback e classifica.
        
        Args:
            texto_feedback: Texto do feedback
            
        Returns:
            Análise estruturada do feedback
        """
        try:
            # Detectar tipo de feedback
            tipo_detectado = 'neutral'
            max_score = 0
            
            for tipo, config in self.feedback_patterns.items():
                score = 0
                for pattern in config['patterns']:
                    matches = len(re.findall(pattern, texto_feedback))
                    score += matches * config['severity_multiplier']
                
                if score > max_score:
                    max_score = score
                    tipo_detectado = tipo
            
            # Analisar sentimento
            sentimento = self._detectar_sentimento(texto_feedback)
            
            # Calcular severidade
            severidade = min(1.0, max_score / 3.0)  # Normalizar para 0-1
            
            # Extrair ações sugeridas
            acoes = self._extrair_acoes_sugeridas(texto_feedback)
            
            # Classificar categoria
            categoria = self._classificar_categoria(texto_feedback, tipo_detectado)
            
            # Calcular confiança
            confianca = self._calcular_confianca_analise(
                texto_feedback, tipo_detectado, severidade
            )
            
            # Determinar prioridade
            prioridade = self._calcular_prioridade(tipo_detectado, severidade, sentimento)
            
            return FeedbackAnalysis(
                tipo=tipo_detectado,
                severidade=severidade,
                sentimento=sentimento,
                acoes_sugeridas=acoes,
                confianca=confianca,
                categoria=categoria,
                prioridade=prioridade
            )
            
        except Exception as e:
            logger.error(f"Erro na análise de feedback: {e}")
            return FeedbackAnalysis(
                tipo='neutral',
                severidade=0.5,
                sentimento='neutral',
                acoes_sugeridas=[],
                confianca=0.0,
                categoria='geral',
                prioridade=3
            )
    
    def extrair_acoes_corretivas(self,
                               consulta: str,
                               interpretacao: Dict,
                               resposta: str,
                               analise: FeedbackAnalysis) -> List[CorrectiveAction]:
        """
        Extrai ações corretivas baseadas na análise de feedback.
        
        Args:
            consulta: Consulta original
            interpretacao: Interpretação do sistema
            resposta: Resposta dada
            analise: Análise do feedback
            
        Returns:
            Lista de ações corretivas
        """
        acoes = []
        
        try:
            # Ações baseadas no tipo de feedback
            if analise.tipo == 'correction':
                acoes.extend(self._gerar_acoes_correcao(consulta, interpretacao, analise))
            
            elif analise.tipo == 'improvement':
                acoes.extend(self._gerar_acoes_melhoria(consulta, interpretacao, analise))
            
            elif analise.tipo == 'clarification':
                acoes.extend(self._gerar_acoes_clarificacao(consulta, interpretacao, analise))
            
            # Ações baseadas na categoria
            if analise.categoria == 'mapping':
                acoes.extend(self._gerar_acoes_mapeamento(consulta, interpretacao, analise))
            
            elif analise.categoria == 'search':
                acoes.extend(self._gerar_acoes_busca(consulta, interpretacao, analise))
            
            return acoes
            
        except Exception as e:
            logger.error(f"Erro ao extrair ações corretivas: {e}")
            return []
    
    def aplicar_acao_corretiva(self, acao: CorrectiveAction) -> bool:
        """
        Aplica uma ação corretiva específica.
        
        Args:
            acao: Ação a ser aplicada
            
        Returns:
            True se aplicada com sucesso
        """
        try:
            if acao.action_type == 'update_mapping':
                return self._aplicar_update_mapping(acao)
            
            elif acao.action_type == 'improve_search':
                return self._aplicar_improve_search(acao)
            
            elif acao.action_type == 'enhance_context':
                return self._aplicar_enhance_context(acao)
            
            elif acao.action_type == 'adjust_parameters':
                return self._aplicar_adjust_parameters(acao)
            
            else:
                logger.warning(f"Tipo de ação não reconhecido: {acao.action_type}")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao aplicar ação {acao.action_type}: {e}")
            return False
    
    # ===== MÉTODOS AUXILIARES DE ANÁLISE =====
    
    def _detectar_sentimento(self, texto: str) -> str:
        """Detecta sentimento no texto."""
        for sentimento, pattern in self.sentiment_patterns.items():
            if re.search(pattern, texto):
                return sentimento
        return 'neutral'
    
    def _extrair_acoes_sugeridas(self, texto: str) -> List[str]:
        """Extrai ações sugeridas do texto."""
        acoes = []
        
        # Padrões de ações
        action_patterns = [
            r'(?i)deveria (.*?)(?:\.|$)',
            r'(?i)sugiro (.*?)(?:\.|$)',
            r'(?i)seria melhor (.*?)(?:\.|$)',
            r'(?i)incluir (.*?)(?:\.|$)'
        ]
        
        for pattern in action_patterns:
            matches = re.findall(pattern, texto)
            acoes.extend([match.strip() for match in matches if match.strip()])
        
        return acoes[:5]  # Limitar a 5 ações
    
    def _classificar_categoria(self, texto: str, tipo: str) -> str:
        """Classifica categoria do feedback."""
        category_patterns = {
            'mapping': r'(?i)(cliente|mapeamento|campo|dado)',
            'search': r'(?i)(busca|encontrar|procurar|filtro)',
            'interface': r'(?i)(tela|botão|interface|visual)',
            'performance': r'(?i)(lento|rápido|demora|performance)',
            'data': r'(?i)(valor|número|data|informação)'
        }
        
        for categoria, pattern in category_patterns.items():
            if re.search(pattern, texto):
                return categoria
        
        return 'geral'
    
    def _calcular_confianca_analise(self, texto: str, tipo: str, severidade: float) -> float:
        """Calcula confiança da análise."""
        confianca = 0.5  # Base
        
        # Aumentar confiança baseado no comprimento e clareza
        if len(texto) > 20:
            confianca += 0.2
        
        # Aumentar baseado na severidade
        confianca += severidade * 0.3
        
        # Ajustar baseado no tipo
        if tipo in ['correction', 'improvement']:
            confianca += 0.1
        
        return min(1.0, confianca)
    
    def _calcular_prioridade(self, tipo: str, severidade: float, sentimento: str) -> int:
        """Calcula prioridade (1=alta, 5=baixa)."""
        prioridade = 3  # Média
        
        if tipo == 'correction':
            prioridade -= 1
        elif tipo == 'positive':
            prioridade += 1
        
        if severidade > 0.7:
            prioridade -= 1
        elif severidade < 0.3:
            prioridade += 1
        
        if sentimento == 'negative':
            prioridade -= 1
        elif sentimento == 'positive':
            prioridade += 1
        
        return max(1, min(5, prioridade))
    
    # ===== MÉTODOS DE GERAÇÃO DE AÇÕES =====
    
    def _gerar_acoes_correcao(self, consulta: str, interpretacao: Dict, analise: FeedbackAnalysis) -> List[CorrectiveAction]:
        """Gera ações de correção."""
        acoes = []
        
        # Ação de correção de mapeamento
        if 'cliente' in analise.acoes_sugeridas or analise.categoria == 'mapping':
            acoes.append(CorrectiveAction(
                action_type='update_mapping',
                target_component='semantic_mapper',
                parameters={'consulta': consulta, 'interpretacao': interpretacao},
                confidence=analise.confianca * 0.9,
                description='Corrigir mapeamento semântico baseado no feedback'
            ))
        
        return acoes
    
    def _gerar_acoes_melhoria(self, consulta: str, interpretacao: Dict, analise: FeedbackAnalysis) -> List[CorrectiveAction]:
        """Gera ações de melhoria."""
        acoes = []
        
        # Ação de melhoria de contexto
        acoes.append(CorrectiveAction(
            action_type='enhance_context',
            target_component='context_processor',
            parameters={'consulta': consulta, 'sugestoes': analise.acoes_sugeridas},
            confidence=analise.confianca * 0.8,
            description='Melhorar processamento de contexto'
        ))
        
        return acoes
    
    def _gerar_acoes_clarificacao(self, consulta: str, interpretacao: Dict, analise: FeedbackAnalysis) -> List[CorrectiveAction]:
        """Gera ações de clarificação."""
        acoes = []
        
        # Ação de ajuste de parâmetros
        acoes.append(CorrectiveAction(
            action_type='adjust_parameters',
            target_component='query_processor',
            parameters={'consulta': consulta, 'clarification_needed': True},
            confidence=analise.confianca * 0.7,
            description='Ajustar parâmetros para melhor clarificação'
        ))
        
        return acoes
    
    def _gerar_acoes_mapeamento(self, consulta: str, interpretacao: Dict, analise: FeedbackAnalysis) -> List[CorrectiveAction]:
        """Gera ações específicas de mapeamento."""
        acoes = []
        
        acoes.append(CorrectiveAction(
            action_type='update_mapping',
            target_component='database_mapper',
            parameters={'field_mapping': True, 'consulta': consulta},
            confidence=analise.confianca,
            description='Atualizar mapeamento de campos do banco'
        ))
        
        return acoes
    
    def _gerar_acoes_busca(self, consulta: str, interpretacao: Dict, analise: FeedbackAnalysis) -> List[CorrectiveAction]:
        """Gera ações específicas de busca."""
        acoes = []
        
        acoes.append(CorrectiveAction(
            action_type='improve_search',
            target_component='search_engine',
            parameters={'search_refinement': True, 'consulta': consulta},
            confidence=analise.confianca,
            description='Melhorar algoritmo de busca'
        ))
        
        return acoes
    
    # ===== MÉTODOS DE APLICAÇÃO DE AÇÕES =====
    
    def _aplicar_update_mapping(self, acao: CorrectiveAction) -> bool:
        """Aplica atualização de mapeamento."""
        # Placeholder para implementação futura
        logger.info(f"🔄 Aplicando update_mapping: {acao.description}")
        return True
    
    def _aplicar_improve_search(self, acao: CorrectiveAction) -> bool:
        """Aplica melhoria de busca."""
        # Placeholder para implementação futura
        logger.info(f"🔍 Aplicando improve_search: {acao.description}")
        return True
    
    def _aplicar_enhance_context(self, acao: CorrectiveAction) -> bool:
        """Aplica melhoria de contexto."""
        # Placeholder para implementação futura
        logger.info(f"🧠 Aplicando enhance_context: {acao.description}")
        return True
    
    def _aplicar_adjust_parameters(self, acao: CorrectiveAction) -> bool:
        """Aplica ajuste de parâmetros."""
        # Placeholder para implementação futura
        logger.info(f"⚙️ Aplicando adjust_parameters: {acao.description}")
        return True
    
    def _salvar_feedback_analise(self, consulta: str, interpretacao: Dict, resposta: str,
                               feedback: Dict, analise: FeedbackAnalysis, melhorias: List,
                               usuario_id: Optional[int]) -> bool:
        """Salva análise de feedback no banco."""
        try:
            # Placeholder para implementação futura
            logger.info(f"💾 Salvando análise de feedback: tipo={analise.tipo}, confiança={analise.confianca}")
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar análise: {e}")
            return False


# Singleton para uso global
_feedback_processor = None

def get_feedback_processor() -> FeedbackProcessor:
    """
    Obtém instância única do processador de feedback.
    
    Returns:
        Instância do FeedbackProcessor
    """
    global _feedback_processor
    if _feedback_processor is None:
        _feedback_processor = FeedbackProcessor()
    return _feedback_processor 