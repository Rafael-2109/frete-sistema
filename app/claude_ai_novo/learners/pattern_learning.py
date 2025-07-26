"""
🎯 PATTERN LEARNER - Aprendizado de Padrões
==========================================

Módulo especializado em detectar, extrair e salvar padrões
de comportamento e linguagem natural dos usuários.

Responsabilidades:
- Extração de padrões de consultas
- Detecção de intenções
- Aprendizado de vocabulário
- Análise semântica básica
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
try:
    from flask import current_app
    FLASK_AVAILABLE = True
except ImportError:
    current_app = None
    FLASK_AVAILABLE = False
from app.claude_ai_novo.utils.flask_fallback import get_db

logger = logging.getLogger(__name__)

class PatternLearner:

    @property
    def db(self):
        """Obtém db com fallback"""
        if not hasattr(self, "_db"):
            self._db = get_db()
        return self._db

    """
    Especialista em aprendizado de padrões comportamentais e linguísticos.
    
    Detecta padrões nas consultas dos usuários e aprende com eles
    para melhorar futuras interpretações.
    """
    
    def __init__(self, learning_rate: float = 0.1):
        """
        Inicializa o aprendiz de padrões.
        
        Args:
            learning_rate: Taxa de aprendizado (0-1)
        """
        self.learning_rate = learning_rate
        logger.info("🎯 PatternLearner inicializado")
    
    def extrair_e_salvar_padroes(self, consulta: str, interpretacao: Dict[str, Any]) -> List[Dict]:
        """
        Extrai padrões da consulta e salva no banco.
        
        Args:
            consulta: Consulta do usuário
            interpretacao: Interpretação gerada pelo sistema
            
        Returns:
            Lista de padrões detectados e salvos
        """
        try:
            padroes_detectados = []
            
            # 1. Extrair diferentes tipos de padrões
            padroes_extraidos = self._extrair_padroes_multipos(consulta, interpretacao)
            
            # 2. Salvar cada padrão no banco
            for padrao in padroes_extraidos:
                padrao_salvo = self._salvar_padrao_otimizado(padrao)
                if padrao_salvo:
                    padroes_detectados.append(padrao_salvo)
            
            logger.debug(f"🎯 Extraídos {len(padroes_detectados)} padrões da consulta")
            return padroes_detectados
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair padrões: {e}")
            return []
    
    def _extrair_padroes_multipos(self, consulta: str, interpretacao: Dict[str, Any]) -> List[Dict]:
        """
        Extrai múltiplos tipos de padrões da consulta.
        
        Args:
            consulta: Consulta original
            interpretacao: Interpretação do sistema
            
        Returns:
            Lista de padrões extraídos
        """
        padroes = []
        
        # 1. Padrões de período temporal
        padroes.extend(self._extrair_padroes_periodo(consulta, interpretacao))
        
        # 2. Padrões de domínio/contexto
        padroes.extend(self._extrair_padroes_dominio(consulta, interpretacao))
        
        # 3. Padrões de intenção/ação
        padroes.extend(self._extrair_padroes_intencao(consulta, interpretacao))
        
        # 4. Padrões de entidades (clientes, produtos, etc.)
        padroes.extend(self._extrair_padroes_entidades(consulta, interpretacao))
        
        # 5. Padrões de estrutura linguística
        padroes.extend(self._extrair_padroes_linguisticos(consulta, interpretacao))
        
        return padroes
    
    def _extrair_padroes_periodo(self, consulta: str, interpretacao: Dict) -> List[Dict]:
        """Extrai padrões relacionados a período temporal"""
        padroes = []
        
        if interpretacao.get("periodo_dias"):
            consulta_lower = consulta.lower()
            
            # Detectar expressões temporais
            expressoes_temporais = [
                ("últimos", "ultimos"), ("última", "ultima"), 
                ("ontem", "hoje"), ("semana", "mês"), ("dias", "dia")
            ]
            
            for expr_grupo in expressoes_temporais:
                for expr in expr_grupo:
                    if expr in consulta_lower:
                        padroes.append({
                            "tipo": "periodo_temporal",
                            "texto": expr,
                            "interpretacao": {
                                "periodo_dias": interpretacao["periodo_dias"],
                                "expressao_detectada": expr
                            },
                            "contexto": consulta,
                            "confianca": 0.8
                        })
                        break  # Não duplicar para sinônimos
        
        return padroes
    
    def _extrair_padroes_dominio(self, consulta: str, interpretacao: Dict) -> List[Dict]:
        """Extrai padrões relacionados ao domínio/área de negócio"""
        padroes = []
        
        if interpretacao.get("dominio"):
            dominio = interpretacao["dominio"]
            palavras_chave = self._extrair_palavras_chave_dominio(consulta, dominio)
            
            for palavra in palavras_chave:
                padroes.append({
                    "tipo": "dominio_negocio",
                    "texto": palavra,
                    "interpretacao": {
                        "dominio": dominio,
                        "palavra_chave": palavra
                    },
                    "contexto": consulta,
                    "confianca": 0.7
                })
        
        return padroes
    
    def _extrair_padroes_intencao(self, consulta: str, interpretacao: Dict) -> List[Dict]:
        """Extrai padrões de intenção do usuário"""
        padroes = []
        
        # Detectar intenção automaticamente
        intencao_info = self._detectar_intencao_avancada(consulta)
        
        if intencao_info:
            padroes.append({
                "tipo": "intencao_usuario",
                "texto": intencao_info["trigger"],
                "interpretacao": {
                    "intencao": intencao_info["tipo"],
                    "confianca_deteccao": intencao_info["confianca"]
                },
                "contexto": consulta,
                "confianca": intencao_info["confianca"]
            })
        
        return padroes
    
    def _extrair_padroes_entidades(self, consulta: str, interpretacao: Dict) -> List[Dict]:
        """Extrai padrões de entidades nomeadas (clientes, produtos, etc.)"""
        padroes = []
        
        # Padrão de cliente específico
        if interpretacao.get("cliente_especifico"):
            cliente = interpretacao["cliente_especifico"]
            termos_cliente = self._extrair_termos_cliente(consulta, cliente)
            
            for termo in termos_cliente:
                padroes.append({
                    "tipo": "entidade_cliente",
                    "texto": termo,
                    "interpretacao": {
                        "cliente_oficial": cliente,
                        "termo_usado": termo
                    },
                    "contexto": consulta,
                    "confianca": 0.9  # Alta confiança para clientes
                })
        
        # Padrão de localização/UF
        if interpretacao.get("uf_especifica"):
            uf = interpretacao["uf_especifica"]
            padroes.append({
                "tipo": "entidade_localizacao",
                "texto": uf,
                "interpretacao": {
                    "uf": uf,
                    "tipo_entidade": "estado"
                },
                "contexto": consulta,
                "confianca": 0.8
            })
        
        return padroes
    
    def _extrair_padroes_linguisticos(self, consulta: str, interpretacao: Dict) -> List[Dict]:
        """Extrai padrões de estrutura linguística"""
        padroes = []
        
        # Padrões de pergunta
        if consulta.strip().endswith('?'):
            tipo_pergunta = self._classificar_tipo_pergunta(consulta)
            padroes.append({
                "tipo": "estrutura_pergunta",
                "texto": tipo_pergunta["palavra_chave"],
                "interpretacao": {
                    "tipo_pergunta": tipo_pergunta["tipo"],
                    "estrutura": "interrogativa"
                },
                "contexto": consulta,
                "confianca": 0.6
            })
        
        # Padrões de comando/solicitação
        verbos_comando = ["mostre", "liste", "gere", "exporte", "busque", "encontre"]
        consulta_lower = consulta.lower()
        
        for verbo in verbos_comando:
            if verbo in consulta_lower:
                padroes.append({
                    "tipo": "estrutura_comando",
                    "texto": verbo,
                    "interpretacao": {
                        "verbo_comando": verbo,
                        "estrutura": "imperativa"
                    },
                    "contexto": consulta,
                    "confianca": 0.7
                })
                break  # Apenas um verbo comando por consulta
        
        return padroes
    
    def _salvar_padrao_otimizado(self, padrao: Dict) -> Optional[Dict]:
        """
        Salva ou atualiza um padrão no banco com otimizações.
        
        Args:
            padrao: Padrão a ser salvo
            
        Returns:
            Padrão salvo ou None se erro
        """
        try:
            with current_app.app_context():
                from app.claude_ai_novo.utils.flask_fallback import get_db
        except Exception as e:
            logger.error(f'Erro: {e}')
            pass
try:
    from sqlalchemy import text
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    text = None
    SQLALCHEMY_AVAILABLE = False
                
                # Verificar se já existe
                existe = self.db.session.execute(
                    text("""
                        SELECT id, confidence, usage_count, success_rate
                        FROM ai_knowledge_patterns
                        WHERE pattern_type = :tipo AND pattern_text = :texto
                    """),
                    {"tipo": padrao["tipo"], "texto": padrao["texto"]}
                ).fetchone()
                
                if existe:
                    # Atualizar existente
                    self.db.session.execute(
                        text("""
                            UPDATE ai_knowledge_patterns
                            SET confidence = :conf, usage_count = usage_count + 1,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = :id
                        """),
                        {"conf": padrao["confidence"], "id": existe[0]}
                    )
                else:
                    # Inserir novo
                    result = self.db.session.execute(
                        text("""
                            INSERT INTO ai_knowledge_patterns
                            (pattern_type, pattern_text, confidence, usage_count, 
                             success_rate, metadata)
                            VALUES (:tipo, :texto, :conf, 1, 0.7, :meta)
                            RETURNING id
                        """),
                        {
                            "tipo": padrao["tipo"],
                            "texto": padrao["texto"],
                            "conf": padrao["confidence"],
                            "meta": self._safe_json_dumps(padrao.get("metadata", {}))
                        }
                    )
                    row = result.fetchone()
                    if row:
                        padrao["id"] = row[0]
                
                self.db.session.commit()
                return padrao
                
        except Exception as e:
            logger.error(f"Erro ao salvar padrão: {e}")
            try:
                from app.claude_ai_novo.utils.flask_fallback import get_db
                self.db.session.rollback()
            except:
                pass
    
    def buscar_padroes_aplicaveis(self, consulta: str, threshold: float = 0.5) -> List[Dict]:
        """
        Busca padrões aplicáveis a uma consulta.
        
        Args:
            consulta: Consulta a ser analisada
            threshold: Threshold mínimo de confiança
            
        Returns:
            Lista de padrões aplicáveis
        """
        try:
            with current_app.app_context():
                from app.claude_ai_novo.utils.flask_fallback import get_db
        except Exception as e:
            logger.error(f'Erro: {e}')
            pass
try:
    from sqlalchemy import text
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    text = None
    SQLALCHEMY_AVAILABLE = False
                
                padroes = self.db.session.execute(
                    text("""
                        SELECT pattern_type, pattern_text, interpretation, confidence, usage_count
                        FROM ai_knowledge_patterns
                        WHERE confidence > :threshold
                        AND LOWER(:consulta) LIKE '%' || LOWER(pattern_text) || '%'
                        ORDER BY confidence DESC, usage_count DESC
                        LIMIT 10
                    """),
                    {"consulta": consulta, "threshold": threshold}
                ).fetchall()
                
                padroes_aplicaveis = []
                for padrao in padroes:
                    # Fazer parse seguro da interpretação
                    try:
                        if isinstance(padrao.interpretation, str):
                            interpretacao = json.loads(padrao.interpretation)
                        else:
                            # Já é um dict, usar diretamente
                            interpretacao = padrao.interpretation
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.warning(f"⚠️ Erro ao fazer parse da interpretação: {e}")
                        interpretacao = {}
                    
                    padroes_aplicaveis.append({
                        "tipo": padrao.pattern_type,
                        "texto": padrao.pattern_text,
                        "interpretacao": interpretacao,
                        "confianca": padrao.confidence,
                        "uso_count": padrao.usage_count
                    })
                
                return padroes_aplicaveis
                
        except Exception as e:
            logger.error(f"❌ Erro ao buscar padrões: {e}")
            return []
    
    def _extrair_palavras_chave_dominio(self, texto: str, dominio: str) -> List[str]:
        """Extrai palavras-chave relevantes para o domínio"""
        palavras = texto.lower().split()
        palavras_relevantes = []
        
        # Vocabulário por domínio
        vocabulario_dominio = {
            "entregas": ["entrega", "entregue", "prazo", "atraso", "monitoramento", "pendente"],
            "fretes": ["frete", "cte", "valor", "aprovação", "transportadora", "aprovado"],
            "pedidos": ["pedido", "cotar", "aberto", "faturado", "embarque", "separação"],
            "financeiro": ["pagar", "pago", "fatura", "cobrança", "vencimento", "pendência"]
        }
        
        vocab = vocabulario_dominio.get(dominio, [])
        for palavra in palavras:
            if palavra in vocab:
                palavras_relevantes.append(palavra)
        
        return list(set(palavras_relevantes))  # Remove duplicatas
    
    def _detectar_intencao_avancada(self, consulta: str) -> Optional[Dict]:
        """Detecta intenção da consulta com análise avançada"""
        consulta_lower = consulta.lower()
        
        # Padrões de intenção mais refinados
        intencoes = {
            "consultar_status": {
                "triggers": ["qual", "como está", "status", "situação", "onde está"],
                "confianca": 0.8
            },
            "listar_itens": {
                "triggers": ["liste", "mostre", "quais são", "todos", "todas as"],
                "confianca": 0.9
            },
            "comparar_dados": {
                "triggers": ["compare", "diferença", "versus", "vs", "melhor", "pior"],
                "confianca": 0.7
            },
            "exportar_dados": {
                "triggers": ["excel", "planilha", "exportar", "relatório", "gerar", "baixar"],
                "confianca": 0.9
            },
            "analisar_tendencias": {
                "triggers": ["análise", "tendência", "padrão", "estatística", "evolução"],
                "confianca": 0.8
            },
            "buscar_informacao": {
                "triggers": ["buscar", "encontrar", "procurar", "localizar", "descobrir"],
                "confianca": 0.7
            }
        }
        
        # Encontrar melhor match
        melhor_match = None
        melhor_confianca = 0
        
        for intencao, config in intencoes.items():
            for trigger in config["triggers"]:
                if trigger in consulta_lower:
                    confianca = config["confianca"]
                    # Bonus por trigger mais específico (palavras maiores)
                    if len(trigger) > 5:
                        confianca += 0.1
                    
                    if confianca > melhor_confianca:
                        melhor_confianca = confianca
                        melhor_match = {
                            "tipo": intencao,
                            "trigger": trigger,
                            "confianca": min(1.0, confianca)
                        }
        
        return melhor_match
    
    def _extrair_termos_cliente(self, consulta: str, cliente: str) -> List[str]:
        """Extrai termos usados para referenciar um cliente"""
        termos = []
        consulta_lower = consulta.lower()
        cliente_lower = cliente.lower()
        
        # Nome completo
        if cliente_lower in consulta_lower:
            termos.append(cliente_lower)
        
        # Palavras individuais do nome do cliente
        palavras_cliente = cliente_lower.split()
        for palavra in palavras_cliente:
            if len(palavra) > 2 and palavra in consulta_lower:
                termos.append(palavra)
        
        # Abreviações e variações
        palavras_consulta = consulta_lower.split()
        for palavra in palavras_consulta:
            if len(palavra) > 2:
                # Verificar se palavra está contida no nome do cliente
                if palavra in cliente_lower or cliente_lower.startswith(palavra):
                    termos.append(palavra)
        
        return list(set(termos))  # Remove duplicatas
    
    def _classificar_tipo_pergunta(self, consulta: str) -> Dict[str, str]:
        """Classifica o tipo de pergunta baseado na estrutura"""
        consulta_lower = consulta.lower()
        
        # Palavras interrogativas
        tipos_pergunta = {
            "qual": "especificacao",
            "quais": "listagem", 
            "quanto": "quantidade",
            "quando": "temporal",
            "onde": "localizacao",
            "como": "processo",
            "por que": "causa",
            "porque": "causa",
            "quem": "responsavel"
        }
        
        for palavra, tipo in tipos_pergunta.items():
            if palavra in consulta_lower:
                return {"tipo": tipo, "palavra_chave": palavra}
        
        # Default para perguntas sem palavra interrogativa clara
        return {"tipo": "generica", "palavra_chave": "?"}

    def _safe_json_dumps(self, obj: Any) -> str:
        """
        Safely dumps an object to JSON, handling potential errors.
        Returns an empty string on error.
        """
        try:
            return json.dumps(obj, ensure_ascii=False, default=str)
        except Exception as e:
            logger.error(f"❌ Erro ao serializar JSON: {e}")
            return ""


# Singleton para uso global
_pattern_learner = None

def get_pattern_learner() -> PatternLearner:
    """
    Obtém instância única do aprendiz de padrões.
    
    Returns:
        Instância do PatternLearner
    """
    global _pattern_learner
    if _pattern_learner is None:
        _pattern_learner = PatternLearner()
    return _pattern_learner 