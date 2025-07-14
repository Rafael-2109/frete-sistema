"""
🧠 LEARNING CORE - Núcleo Principal do Aprendizado
================================================

Núcleo central que coordena todo o sistema de aprendizado vitalício.
Orquestra os demais módulos especializados.

Responsabilidades:
- Coordenação principal do aprendizado
- Interface unificada
- Gestão do ciclo completo de aprendizado
- Aplicação de conhecimento adquirido
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from flask import current_app

# Local imports - Flask fallback
from app.claude_ai_novo.utils.flask_fallback import get_db

logger = logging.getLogger(__name__)

class LearningCore:

    @property
    def db(self):
        """Obtém db com fallback"""
        if not hasattr(self, "_db"):
            self._db = get_db()
        return self._db

    """
    Núcleo central do sistema de aprendizado vitalício.
    
    Coordena todos os processos de aprendizado e aplicação
    de conhecimento no sistema Claude AI.
    """
    
    def __init__(self, claude_client=None, db_engine=None, db_session=None):
        """
        Inicializa o núcleo de aprendizado
        
        Args:
            claude_client: Cliente Claude API
            db_engine: Engine do banco de dados
            db_session: Sessão do banco de dados
        """
        self.claude_client = claude_client
        self.db_engine = db_engine
        self.db_session = db_session
        
        self.confidence_threshold = 0.7
        self.learning_rate = 0.1
        
        # Inicializar módulos especializados (lazy loading)
        self._pattern_learner = None
        self._feedback_processor = None
        self._knowledge_memory = None
        
        logger.info("🧠 Learning Core inicializado")
    
    @property
    def pattern_learner(self):
        """Lazy loading do PatternLearner"""
        if self._pattern_learner is None:
            from app.claude_ai_novo.learners.pattern_learning import get_pattern_learner
            self._pattern_learner = get_pattern_learner()
        return self._pattern_learner
    
    @property
    def feedback_processor(self):
        """Lazy loading do FeedbackProcessor"""
        if self._feedback_processor is None:
            from app.claude_ai_novo.learners.feedback_learning import get_feedback_processor
            self._feedback_processor = get_feedback_processor()
        return self._feedback_processor
    
    @property
    def knowledge_memory(self):
        """Lazy loading do KnowledgeMemory"""
        if self._knowledge_memory is None:
            from ..memorizers.knowledge_memory import get_knowledge_memory
            self._knowledge_memory = get_knowledge_memory()
        return self._knowledge_memory
    
    def aprender_com_interacao(self, 
                               consulta: str, 
                               interpretacao: Dict[str, Any],
                               resposta: str,
                               feedback: Optional[Dict[str, Any]] = None,
                               usuario_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Aprende com cada interação do usuário (método principal).
        
        Args:
            consulta: Consulta original do usuário
            interpretacao: Como o sistema interpretou
            resposta: Resposta dada
            feedback: Feedback do usuário (se houver)
            usuario_id: ID do usuário
            
        Returns:
            Dict com aprendizados extraídos
        """
        try:
            aprendizados = {
                "timestamp": datetime.now().isoformat(),
                "padroes_detectados": [],
                "mapeamentos_atualizados": [],
                "grupos_descobertos": [],
                "melhorias_aplicadas": [],
                "metricas_atualizadas": False
            }
            
            # 1. DETECTAR E APRENDER PADRÕES
            padroes = self.pattern_learner.extrair_e_salvar_padroes(consulta, interpretacao)
            aprendizados["padroes_detectados"] = padroes
            
            # 2. APRENDER MAPEAMENTOS E GRUPOS
            if interpretacao.get("cliente_especifico"):
                mapeamento = self.knowledge_memory.aprender_mapeamento_cliente(
                    consulta, interpretacao["cliente_especifico"]
                )
                if mapeamento:
                    aprendizados["mapeamentos_atualizados"].append(mapeamento)
            
            if interpretacao.get("tipo_consulta") == "grupo_empresarial":
                grupo = self.knowledge_memory.descobrir_grupo_empresarial(interpretacao)
                if grupo:
                    aprendizados["grupos_descobertos"].append(grupo)
            
            # 3. PROCESSAR FEEDBACK (se houver)
            if feedback:
                correcoes = self.feedback_processor.processar_feedback_completo(
                    consulta, interpretacao, resposta, feedback, usuario_id
                )
                aprendizados["melhorias_aplicadas"] = correcoes
            
            # 4. ATUALIZAR MÉTRICAS
            metricas_sucesso = self._atualizar_metricas(interpretacao, feedback)
            aprendizados["metricas_atualizadas"] = metricas_sucesso
            
            # 5. SALVAR HISTÓRICO CONSOLIDADO
            self._salvar_historico_aprendizado(
                consulta, interpretacao, resposta, feedback, aprendizados, usuario_id
            )
            
            # 6. CALCULAR SCORE DE APRENDIZADO
            aprendizados["score_aprendizado"] = self._calcular_score_aprendizado(aprendizados)
            
            logger.info(f"✅ Aprendizado concluído: {len(aprendizados['padroes_detectados'])} padrões, "
                       f"{len(aprendizados['mapeamentos_atualizados'])} mapeamentos, "
                       f"score: {aprendizados['score_aprendizado']:.2f}")
            
            return aprendizados
            
        except Exception as e:
            logger.error(f"❌ Erro no aprendizado: {e}")
            return {"erro": str(e), "timestamp": datetime.now().isoformat()}
    
    def aplicar_conhecimento(self, consulta: str) -> Dict[str, Any]:
        """
        Aplica conhecimento aprendido para melhorar interpretação.
        
        Args:
            consulta: Consulta a ser analisada
            
        Returns:
            Dict com conhecimentos aplicáveis
        """
        try:
            conhecimento = {
                "timestamp": datetime.now().isoformat(),
                "padroes_aplicaveis": [],
                "grupos_conhecidos": [],
                "mapeamentos": [],
                "contextos_negocio": [],
                "confianca_geral": 0.0,
                "recomendacoes": []
            }
            
            # 1. Aplicar padrões aprendidos
            padroes = self.pattern_learner.buscar_padroes_aplicaveis(consulta, self.confidence_threshold)
            conhecimento["padroes_aplicaveis"] = padroes
            
            # 2. Aplicar conhecimento de grupos e mapeamentos
            grupos = self.knowledge_memory.buscar_grupos_aplicaveis(consulta)
            mapeamentos = self.knowledge_memory.buscar_mapeamentos_aplicaveis(consulta)
            
            conhecimento["grupos_conhecidos"] = grupos
            conhecimento["mapeamentos"] = mapeamentos
            
            # 3. Calcular confiança geral
            if conhecimento["padroes_aplicaveis"]:
                conhecimento["confianca_geral"] = max(
                    p.get("confianca", 0) for p in conhecimento["padroes_aplicaveis"]
                )
            
            # 4. Gerar recomendações baseadas no conhecimento
            conhecimento["recomendacoes"] = self._gerar_recomendacoes_aplicacao(conhecimento)
            
            logger.debug(f"🔍 Conhecimento aplicado: {len(padroes)} padrões, "
                        f"{len(grupos)} grupos, confiança: {conhecimento['confianca_geral']:.2f}")
            
            return conhecimento
            
        except Exception as e:
            logger.error(f"❌ Erro ao aplicar conhecimento: {e}")
            return {
                "erro": str(e),
                "timestamp": datetime.now().isoformat(),
                "padroes_aplicaveis": [],
                "grupos_conhecidos": [],
                "mapeamentos": [],
                "confianca_geral": 0.0
            }
    
    def obter_status_sistema(self) -> Dict[str, Any]:
        """
        Obtém status geral do sistema de aprendizado.
        
        Returns:
            Dict com status completo
        """
        try:
            status = {
                "timestamp": datetime.now().isoformat(),
                "sistema_ativo": True,
                "modulos_carregados": {},
                "estatisticas_gerais": {},
                "saude_sistema": "OK"
            }
            
            # Status dos módulos
            status["modulos_carregados"] = {
                "pattern_learner": self._pattern_learner is not None,
                "feedback_processor": self._feedback_processor is not None,
                "knowledge_memory": self._knowledge_memory is not None
            }
            
            # Estatísticas gerais via knowledge_manager
            try:
                status["estatisticas_gerais"] = self.knowledge_memory.obter_estatisticas_aprendizado()
            except Exception as e:
                logger.warning(f"Erro ao obter estatísticas: {e}")
                status["estatisticas_gerais"] = {"erro": str(e)}
            
            # Avaliar saúde do sistema
            status["saude_sistema"] = self._avaliar_saude_sistema(status)
            
            return status
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter status: {e}")
            return {
                "erro": str(e),
                "timestamp": datetime.now().isoformat(),
                "sistema_ativo": False
            }
    
    def _atualizar_metricas(self, interpretacao: Dict, feedback: Optional[Dict]) -> bool:
        """
        Atualiza métricas de performance do sistema.
        
        Args:
            interpretacao: Interpretação realizada
            feedback: Feedback do usuário
            
        Returns:
            True se métricas foram atualizadas com sucesso
        """
        try:
            with current_app.app_context():
                from app.claude_ai_novo.utils.flask_fallback import get_db
                
                # Calcular satisfação baseada no feedback
                satisfacao = 1.0  # Default: satisfeito
                if feedback:
                    if feedback.get("tipo") == "correction":
                        satisfacao = 0.3  # Correção indica problema
                    elif feedback.get("tipo") == "improvement":
                        satisfacao = 0.7  # Sugestão indica espaço para melhorar
                
                # Salvar métrica
                from sqlalchemy import text
                self.db.session.execute(
                    text("""
                        INSERT INTO ai_learning_metrics
                        (metrica_tipo, metrica_valor, contexto, periodo_inicio, periodo_fim)
                        VALUES ('satisfaction', :valor, :contexto, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """),
                    {
                        "valor": satisfacao,
                        "contexto": json.dumps({"dominio": interpretacao.get("dominio")})
                    }
                )
                
                self.db.session.commit()
                return True
                
        except Exception as e:
            logger.error(f"Erro ao atualizar métricas: {e}")
            try:
                self.db.session.rollback()
            except:
                pass
            return False
    
    def _salvar_historico_aprendizado(self, consulta: str, interpretacao: Dict, 
                                    resposta: str, feedback: Optional[Dict], 
                                    aprendizados: Dict, usuario_id: Optional[int]) -> bool:
        """
        Salva histórico completo da interação de aprendizado.
        
        Returns:
            True se histórico foi salvo com sucesso
        """
        try:
            with current_app.app_context():
                from sqlalchemy import text
                
                self.db.session.execute(
                    text("""
                        INSERT INTO ai_learning_history
                        (consulta_original, interpretacao_inicial, resposta_inicial,
                         feedback_usuario, aprendizado_extraido, usuario_id)
                        VALUES (:consulta, :interp, :resp, :feedback, :aprendizado, :user_id)
                    """),
                    {
                        "consulta": consulta,
                        "interp": json.dumps(interpretacao),
                        "resp": resposta[:5000],  # Limitar tamanho
                        "feedback": json.dumps(feedback) if feedback else None,
                        "aprendizado": json.dumps(aprendizados),
                        "user_id": usuario_id
                    }
                )
                self.db.session.commit()
                return True
                
        except Exception as e:
            logger.error(f"Erro ao salvar histórico: {e}")
            try:
                self.db.session.rollback()
            except:
                pass
            return False
    
    def _calcular_score_aprendizado(self, aprendizados: Dict) -> float:
        """
        Calcula score de qualidade do aprendizado.
        
        Args:
            aprendizados: Dict com aprendizados da interação
            
        Returns:
            Score de 0-100
        """
        score = 0.0
        
        # Pontos por padrões detectados
        score += len(aprendizados.get("padroes_detectados", [])) * 20
        
        # Pontos por mapeamentos atualizados
        score += len(aprendizados.get("mapeamentos_atualizados", [])) * 25
        
        # Pontos por grupos descobertos
        score += len(aprendizados.get("grupos_descobertos", [])) * 30
        
        # Pontos por melhorias aplicadas
        score += len(aprendizados.get("melhorias_aplicadas", [])) * 15
        
        # Bônus por métricas atualizadas
        if aprendizados.get("metricas_atualizadas"):
            score += 10
        
        return min(100.0, score)
    
    def _gerar_recomendacoes_aplicacao(self, conhecimento: Dict) -> List[str]:
        """
        Gera recomendações baseadas no conhecimento aplicável.
        
        Args:
            conhecimento: Conhecimento disponível
            
        Returns:
            Lista de recomendações
        """
        recomendacoes = []
        
        # Recomendações baseadas em confiança
        confianca = conhecimento.get("confianca_geral", 0)
        if confianca > 0.8:
            recomendacoes.append("🎯 Alta confiança nos padrões - aplicar automaticamente")
        elif confianca > 0.5:
            recomendacoes.append("⚡ Confiança média - aplicar com validação")
        elif confianca > 0:
            recomendacoes.append("🔍 Baixa confiança - usar como sugestão")
        
        # Recomendações baseadas em quantidade de conhecimento
        total_conhecimento = (
            len(conhecimento.get("padroes_aplicaveis", [])) +
            len(conhecimento.get("grupos_conhecidos", [])) +
            len(conhecimento.get("mapeamentos", []))
        )
        
        if total_conhecimento > 5:
            recomendacoes.append("📚 Rico conhecimento disponível - análise completa")
        elif total_conhecimento > 2:
            recomendacoes.append("📖 Conhecimento moderado - aplicação seletiva")
        else:
            recomendacoes.append("📝 Pouco conhecimento - oportunidade de aprendizado")
        
        return recomendacoes
    
    def _avaliar_saude_sistema(self, status: Dict) -> str:
        """
        Avalia saúde geral do sistema de aprendizado.
        
        Args:
            status: Status atual do sistema
            
        Returns:
            Status de saúde
        """
        try:
            estatisticas = status.get("estatisticas_gerais", {})
            
            # Verificar se há erros
            if "erro" in estatisticas:
                return "ERRO"
            
            # Verificar atividade recente
            aprendizado_semanal = estatisticas.get("aprendizado_semanal", 0)
            if aprendizado_semanal == 0:
                return "INATIVO"
            
            # Verificar qualidade dos padrões
            total_padroes = estatisticas.get("total_padroes", 0)
            padroes_confiaveis = estatisticas.get("padroes_confiaveis", 0)
            
            if total_padroes > 0:
                taxa_qualidade = padroes_confiaveis / total_padroes
                if taxa_qualidade > 0.7:
                    return "EXCELENTE"
                elif taxa_qualidade > 0.5:
                    return "BOM"
                else:
                    return "REGULAR"
            
            return "INICIANDO"
            
        except Exception as e:
            logger.error(f"Erro ao avaliar saúde: {e}")
            return "INDETERMINADO"


# Singleton para uso global
_learning_core = None

def get_learning_core() -> LearningCore:
    """
    Obtém instância única do núcleo de aprendizado.
    
    Returns:
        Instância do LearningCore
    """
    global _learning_core
    if _learning_core is None:
        _learning_core = LearningCore()
    return _learning_core

# Alias para compatibilidade
def get_lifelong_learning() -> LearningCore:
    """Alias para compatibilidade com código existente"""
    return get_learning_core() 