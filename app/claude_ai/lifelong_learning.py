"""
🧠 SISTEMA DE APRENDIZADO VITALÍCIO DO CLAUDE AI
Sistema que aprende permanentemente e melhora com o tempo
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy import text, func
from app import db
from app.utils.redis_cache import redis_cache, REDIS_DISPONIVEL

logger = logging.getLogger(__name__)


class LifelongLearningSystem:
    """Sistema de aprendizado contínuo e permanente"""
    
    def __init__(self):
        self.confidence_threshold = 0.7  # Threshold para aplicar padrões automaticamente
        self.learning_rate = 0.1  # Taxa de aprendizado
        logger.info("🧠 Sistema de Aprendizado Vitalício inicializado")
    
    def aprender_com_interacao(self, 
                               consulta: str, 
                               interpretacao: Dict[str, Any],
                               resposta: str,
                               feedback: Optional[Dict[str, Any]] = None,
                               usuario_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Aprende com cada interação do usuário
        
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
                "padroes_detectados": [],
                "mapeamentos_atualizados": [],
                "grupos_descobertos": [],
                "melhorias_aplicadas": []
            }
            
            # 1. DETECTAR E APRENDER PADRÕES
            padroes = self._extrair_padroes(consulta, interpretacao)
            for padrao in padroes:
                padrao_salvo = self._salvar_padrao(padrao)
                if padrao_salvo:
                    aprendizados["padroes_detectados"].append(padrao_salvo)
            
            # 2. APRENDER MAPEAMENTOS SEMÂNTICOS
            if interpretacao.get("cliente_especifico"):
                mapeamento = self._aprender_mapeamento_cliente(
                    consulta, 
                    interpretacao["cliente_especifico"]
                )
                if mapeamento:
                    aprendizados["mapeamentos_atualizados"].append(mapeamento)
            
            # 3. DESCOBRIR NOVOS GRUPOS EMPRESARIAIS
            if interpretacao.get("tipo_consulta") == "grupo_empresarial":
                grupo = self._descobrir_grupo_empresarial(interpretacao)
                if grupo:
                    aprendizados["grupos_descobertos"].append(grupo)
            
            # 4. PROCESSAR FEEDBACK (se houver)
            if feedback:
                correcoes = self._processar_feedback(
                    consulta, interpretacao, resposta, feedback, usuario_id
                )
                aprendizados["melhorias_aplicadas"].extend(correcoes)
            
            # 5. ATUALIZAR MÉTRICAS
            self._atualizar_metricas(interpretacao, feedback)
            
            # 6. SALVAR HISTÓRICO
            self._salvar_historico(
                consulta, interpretacao, resposta, feedback, aprendizados, usuario_id
            )
            
            logger.info(f"✅ Aprendizado concluído: {len(aprendizados['padroes_detectados'])} padrões, "
                       f"{len(aprendizados['mapeamentos_atualizados'])} mapeamentos")
            
            return aprendizados
            
        except Exception as e:
            logger.error(f"❌ Erro no aprendizado: {e}")
            return {"erro": str(e)}
    
    def _extrair_padroes(self, consulta: str, interpretacao: Dict[str, Any]) -> List[Dict]:
        """Extrai padrões da consulta e interpretação"""
        padroes = []
        
        # Padrão de período
        if interpretacao.get("periodo_dias"):
            if "últimos" in consulta.lower() or "ultimos" in consulta.lower():
                padroes.append({
                    "tipo": "periodo",
                    "texto": f"últimos {interpretacao['periodo_dias']} dias",
                    "interpretacao": {"periodo_dias": interpretacao["periodo_dias"]},
                    "contexto": consulta
                })
        
        # Padrão de domínio
        if interpretacao.get("dominio"):
            palavras_dominio = self._extrair_palavras_chave(consulta, interpretacao["dominio"])
            if palavras_dominio:
                padroes.append({
                    "tipo": "dominio",
                    "texto": " ".join(palavras_dominio),
                    "interpretacao": {"dominio": interpretacao["dominio"]},
                    "contexto": consulta
                })
        
        # Padrão de intenção
        intencao = self._detectar_intencao(consulta)
        if intencao:
            padroes.append({
                "tipo": "intencao",
                "texto": intencao["texto"],
                "interpretacao": {"intencao": intencao["tipo"]},
                "contexto": consulta
            })
        
        return padroes
    
    def _salvar_padrao(self, padrao: Dict) -> Optional[Dict]:
        """Salva ou atualiza um padrão no banco"""
        try:
            # Verificar se já existe
            existe = db.session.execute(
                text("""
                    SELECT id, confidence, usage_count, success_rate
                    FROM ai_knowledge_patterns
                    WHERE pattern_type = :tipo AND pattern_text = :texto
                """),
                {"tipo": padrao["tipo"], "texto": padrao["texto"]}
            ).first()
            
            if existe:
                # Atualizar padrão existente
                nova_confianca = min(1.0, existe.confidence + self.learning_rate)
                novo_uso = existe.usage_count + 1
                
                db.session.execute(
                    text("""
                        UPDATE ai_knowledge_patterns
                        SET confidence = :conf,
                            usage_count = :uso,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = :id
                    """),
                    {"conf": nova_confianca, "uso": novo_uso, "id": existe.id}
                )
            else:
                # Criar novo padrão
                result = db.session.execute(
                    text("""
                        INSERT INTO ai_knowledge_patterns 
                        (pattern_type, pattern_text, interpretation, created_by)
                        VALUES (:tipo, :texto, :interp, 'sistema')
                        RETURNING id, pattern_type, pattern_text, confidence
                    """),
                    {
                        "tipo": padrao["tipo"],
                        "texto": padrao["texto"],
                        "interp": json.dumps(padrao["interpretacao"])
                    }
                )
                padrao_novo = result.first()
                if padrao_novo:
                    padrao["id"] = padrao_novo.id
                    padrao["confidence"] = padrao_novo.confidence
            
            db.session.commit()
            return padrao
            
        except Exception as e:
            logger.error(f"Erro ao salvar padrão: {e}")
            db.session.rollback()
            return None
    
    def _aprender_mapeamento_cliente(self, consulta: str, cliente: str) -> Optional[Dict]:
        """Aprende como usuários se referem a clientes"""
        try:
            # Extrair termos usados para o cliente
            termos = self._extrair_termos_cliente(consulta, cliente)
            
            for termo in termos:
                # Verificar se já existe
                existe = db.session.execute(
                    text("""
                        SELECT id, frequencia
                        FROM ai_semantic_mappings
                        WHERE termo_usuario = :termo 
                        AND campo_sistema = :campo
                        AND modelo = 'cliente'
                    """),
                    {"termo": termo.lower(), "campo": cliente}
                ).first()
                
                if existe:
                    # Incrementar frequência
                    db.session.execute(
                        text("""
                            UPDATE ai_semantic_mappings
                            SET frequencia = frequencia + 1,
                                ultima_uso = CURRENT_TIMESTAMP
                            WHERE id = :id
                        """),
                        {"id": existe.id}
                    )
                else:
                    # Criar novo mapeamento
                    db.session.execute(
                        text("""
                            INSERT INTO ai_semantic_mappings
                            (termo_usuario, campo_sistema, modelo, contexto)
                            VALUES (:termo, :campo, 'cliente', :contexto)
                        """),
                        {
                            "termo": termo.lower(),
                            "campo": cliente,
                            "contexto": consulta
                        }
                    )
            
            db.session.commit()
            return {"cliente": cliente, "termos_aprendidos": termos}
            
        except Exception as e:
            logger.error(f"Erro ao aprender mapeamento: {e}")
            db.session.rollback()
            return None
    
    def _descobrir_grupo_empresarial(self, interpretacao: Dict) -> Optional[Dict]:
        """Descobre e salva novos grupos empresariais"""
        try:
            grupo_info = interpretacao.get("grupo_empresarial", {})
            if not grupo_info:
                return None
            
            # Verificar se já existe
            existe = db.session.execute(
                text("SELECT id FROM ai_grupos_empresariais WHERE nome_grupo = :nome"),
                {"nome": grupo_info.get("grupo_detectado")}
            ).first()
            
            if not existe:
                # Salvar novo grupo descoberto
                result = db.session.execute(
                    text("""
                        INSERT INTO ai_grupos_empresariais
                        (nome_grupo, tipo_negocio, cnpj_prefixos, palavras_chave, 
                         filtro_sql, regras_deteccao, estatisticas, aprendido_automaticamente)
                        VALUES (:nome, :tipo, :cnpjs, :palavras, :filtro, :regras, :stats, TRUE)
                        RETURNING id
                    """),
                    {
                        "nome": grupo_info.get("grupo_detectado"),
                        "tipo": grupo_info.get("tipo_negocio"),
                        "cnpjs": grupo_info.get("cnpj_prefixos", []),
                        "palavras": grupo_info.get("keywords", []),
                        "filtro": grupo_info.get("filtro_sql"),
                        "regras": json.dumps(grupo_info.get("regras_deteccao", {})),
                        "stats": json.dumps(grupo_info.get("estatisticas", {}))
                    }
                )
                
                db.session.commit()
                logger.info(f"🏢 Novo grupo empresarial descoberto: {grupo_info.get('grupo_detectado')}")
                return grupo_info
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao descobrir grupo: {e}")
            db.session.rollback()
            return None
    
    def _processar_feedback(self, consulta: str, interpretacao: Dict, 
                           resposta: str, feedback: Dict, usuario_id: Optional[int]) -> List[Dict]:
        """Processa feedback do usuário e aprende com correções"""
        correcoes = []
        
        try:
            tipo_feedback = feedback.get("tipo", "correction")
            
            if tipo_feedback == "correction":
                # Usuário corrigiu a interpretação
                correcao_info = {
                    "tipo": "interpretacao",
                    "original": interpretacao,
                    "corrigido": feedback.get("interpretacao_correta", {})
                }
                
                # Aprender com a correção
                self._aprender_com_correcao(consulta, interpretacao, 
                                          feedback.get("interpretacao_correta", {}))
                
                correcoes.append(correcao_info)
                
            elif tipo_feedback == "improvement":
                # Usuário sugeriu melhoria
                melhoria = {
                    "tipo": "melhoria",
                    "sugestao": feedback.get("sugestao", ""),
                    "aplicada": False
                }
                
                # Avaliar e aplicar melhoria se apropriada
                if self._avaliar_melhoria(feedback.get("sugestao", "")):
                    self._aplicar_melhoria(feedback.get("sugestao", ""))
                    melhoria["aplicada"] = True
                
                correcoes.append(melhoria)
            
            return correcoes
            
        except Exception as e:
            logger.error(f"Erro ao processar feedback: {e}")
            return []
    
    def _aprender_com_correcao(self, consulta: str, 
                               interpretacao_errada: Dict, 
                               interpretacao_correta: Dict):
        """Aprende com correções do usuário"""
        try:
            # Identificar o tipo de erro
            tipo_erro = self._identificar_tipo_erro(interpretacao_errada, interpretacao_correta)
            
            # Ajustar confiança dos padrões que levaram ao erro
            if tipo_erro == "cliente_errado":
                # Reduzir confiança em padrões que detectaram cliente errado
                cliente_errado = interpretacao_errada.get("cliente_especifico")
                if cliente_errado:
                    db.session.execute(
                        text("""
                            UPDATE ai_knowledge_patterns
                            SET confidence = GREATEST(0.1, confidence - :reducao),
                                success_rate = GREATEST(0.1, success_rate - :reducao)
                            WHERE pattern_type = 'cliente'
                            AND interpretation::jsonb @> :filtro
                        """),
                        {
                            "reducao": self.learning_rate * 2,
                            "filtro": json.dumps({"cliente": cliente_errado})
                        }
                    )
            
            # Criar novo padrão correto
            if interpretacao_correta.get("cliente_especifico"):
                self._salvar_padrao({
                    "tipo": "cliente",
                    "texto": consulta.lower(),
                    "interpretacao": {"cliente": interpretacao_correta["cliente_especifico"]},
                    "contexto": f"Corrigido de: {interpretacao_errada.get('cliente_especifico')}"
                })
            
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Erro ao aprender com correção: {e}")
            db.session.rollback()
    
    def _salvar_historico(self, consulta: str, interpretacao: Dict, 
                         resposta: str, feedback: Optional[Dict], 
                         aprendizados: Dict, usuario_id: Optional[int]):
        """Salva histórico completo da interação"""
        try:
            db.session.execute(
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
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Erro ao salvar histórico: {e}")
            db.session.rollback()
    
    def aplicar_conhecimento(self, consulta: str) -> Dict[str, Any]:
        """
        Aplica conhecimento aprendido para melhorar interpretação
        
        Returns:
            Dict com padrões e conhecimentos aplicáveis
        """
        conhecimento = {
            "padroes_aplicaveis": [],
            "grupos_conhecidos": [],
            "mapeamentos": [],
            "contextos_negocio": [],
            "confianca_geral": 0.0
        }
        
        try:
            # 1. Buscar padrões aplicáveis
            padroes = db.session.execute(
                text("""
                    SELECT pattern_type, pattern_text, interpretation, confidence
                    FROM ai_knowledge_patterns
                    WHERE confidence > :threshold
                    AND LOWER(:consulta) LIKE '%' || LOWER(pattern_text) || '%'
                    ORDER BY confidence DESC, usage_count DESC
                    LIMIT 10
                """),
                {"consulta": consulta, "threshold": 0.5}
            ).fetchall()
            
            for padrao in padroes:
                conhecimento["padroes_aplicaveis"].append({
                    "tipo": padrao.pattern_type,
                    "texto": padrao.pattern_text,
                    "interpretacao": json.loads(padrao.interpretation),
                    "confianca": padrao.confidence
                })
            
            # 2. Buscar grupos empresariais conhecidos
            try:
                # Primeiro, buscar por palavras-chave usando ANY
                grupos = db.session.execute(
                    text("""
                        SELECT nome_grupo, tipo_negocio, filtro_sql, 
                               array_to_string(cnpj_prefixos, ',') as cnpjs_str,
                               array_to_string(palavras_chave, ',') as palavras_str
                        FROM ai_grupos_empresariais
                        WHERE ativo = TRUE
                        AND (
                            -- Buscar em palavras_chave usando ANY
                            EXISTS (
                                SELECT 1 FROM unnest(palavras_chave) AS palavra
                                WHERE LOWER(:consulta) LIKE '%' || LOWER(palavra) || '%'
                            )
                            OR 
                            -- Buscar no nome do grupo
                            nome_grupo ILIKE '%' || :consulta || '%'
                        )
                        LIMIT 5
                    """),
                    {"consulta": consulta}
                ).fetchall()
                
                for grupo in grupos:
                    # Converter strings de volta para listas
                    cnpjs = grupo.cnpjs_str.split(',') if grupo.cnpjs_str else []
                    palavras = grupo.palavras_str.split(',') if grupo.palavras_str else []
                    
                    conhecimento["grupos_conhecidos"].append({
                        "nome": grupo.nome_grupo,
                        "tipo": grupo.tipo_negocio,
                        "filtro": grupo.filtro_sql,
                        "cnpjs": [c.strip() for c in cnpjs if c.strip()],
                        "palavras": [p.strip() for p in palavras if p.strip()]
                    })
                    
            except Exception as e:
                logger.warning(f"Erro ao buscar grupos empresariais: {e}")
                # Fallback: busca simples sem arrays
                try:
                    db.session.rollback()
                    grupos = db.session.execute(
                        text("""
                            SELECT nome_grupo, tipo_negocio, filtro_sql
                            FROM ai_grupos_empresariais
                            WHERE ativo = TRUE
                            ORDER BY nome_grupo
                            LIMIT 3
                        """)
                    ).fetchall()
                    
                    for grupo in grupos:
                        conhecimento["grupos_conhecidos"].append({
                            "nome": grupo.nome_grupo,
                            "tipo": grupo.tipo_negocio,
                            "filtro": grupo.filtro_sql,
                            "cnpjs": [],
                            "palavras": []
                        })
                except:
                    pass  # Ignora se ainda falhar
            
            # 3. Buscar mapeamentos semânticos
            mapeamentos = db.session.execute(
                text("""
                    SELECT DISTINCT campo_sistema, modelo, MAX(frequencia) as frequencia
                    FROM ai_semantic_mappings
                    WHERE LOWER(:consulta) LIKE '%' || LOWER(termo_usuario) || '%'
                    AND frequencia > 2
                    GROUP BY campo_sistema, modelo
                    ORDER BY frequencia DESC
                    LIMIT 5
                """),
                {"consulta": consulta}
            ).fetchall()
            
            for mapa in mapeamentos:
                conhecimento["mapeamentos"].append({
                    "campo": mapa.campo_sistema,
                    "modelo": mapa.modelo
                })
            
            # 4. Calcular confiança geral
            if conhecimento["padroes_aplicaveis"]:
                conhecimento["confianca_geral"] = max(
                    p["confianca"] for p in conhecimento["padroes_aplicaveis"]
                )
            
            return conhecimento
            
        except Exception as e:
            logger.error(f"Erro ao aplicar conhecimento: {e}")
            return conhecimento
    
    def obter_estatisticas_aprendizado(self) -> Dict[str, Any]:
        """Retorna estatísticas do sistema de aprendizado"""
        try:
            stats = {}
            
            # Total de padrões aprendidos
            total_padroes = db.session.execute(
                text("SELECT COUNT(*) as total FROM ai_knowledge_patterns")
            ).scalar()
            
            # Padrões de alta confiança
            padroes_confiaveis = db.session.execute(
                text("SELECT COUNT(*) as total FROM ai_knowledge_patterns WHERE confidence > 0.8")
            ).scalar()
            
            # Grupos empresariais
            total_grupos = db.session.execute(
                text("SELECT COUNT(*) as total FROM ai_grupos_empresariais WHERE ativo = TRUE")
            ).scalar()
            
            # Mapeamentos semânticos
            total_mapeamentos = db.session.execute(
                text("SELECT COUNT(*) as total FROM ai_semantic_mappings")
            ).scalar()
            
            # Taxa de aprendizado (últimos 7 dias)
            aprendizado_recente = db.session.execute(
                text("""
                    SELECT COUNT(*) as total 
                    FROM ai_learning_history 
                    WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '7 days'
                """)
            ).scalar()
            
            stats = {
                "total_padroes": total_padroes or 0,
                "padroes_confiaveis": padroes_confiaveis or 0,
                "taxa_confianca": (padroes_confiaveis / total_padroes * 100) if total_padroes and total_padroes > 0 else 0,
                "total_grupos": total_grupos or 0,
                "total_mapeamentos": total_mapeamentos or 0,
                "aprendizado_semanal": aprendizado_recente or 0,
                "status": "ativo" if aprendizado_recente and aprendizado_recente > 0 else "inativo"
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {e}")
            return {}
    
    def _extrair_palavras_chave(self, texto: str, dominio: str) -> List[str]:
        """Extrai palavras-chave relevantes do texto"""
        # Implementação simplificada - pode ser melhorada com NLP
        palavras = texto.lower().split()
        palavras_relevantes = []
        
        # Palavras comuns por domínio
        vocabulario_dominio = {
            "entregas": ["entrega", "entregue", "prazo", "atraso", "monitoramento"],
            "fretes": ["frete", "cte", "valor", "aprovação", "transportadora"],
            "pedidos": ["pedido", "cotar", "aberto", "faturado", "embarque"]
        }
        
        for palavra in palavras:
            if palavra in vocabulario_dominio.get(dominio, []):
                palavras_relevantes.append(palavra)
        
        return palavras_relevantes
    
    def _detectar_intencao(self, consulta: str) -> Optional[Dict]:
        """Detecta a intenção da consulta"""
        consulta_lower = consulta.lower()
        
        # Padrões de intenção
        intencoes = {
            "consultar": ["qual", "quanto", "como está", "status", "situação"],
            "listar": ["liste", "mostre", "quais são", "todos", "todas"],
            "comparar": ["compare", "diferença", "versus", "vs", "melhor"],
            "exportar": ["excel", "planilha", "exportar", "relatório", "gerar"],
            "analisar": ["análise", "tendência", "padrão", "estatística"]
        }
        
        for tipo, palavras in intencoes.items():
            for palavra in palavras:
                if palavra in consulta_lower:
                    return {"tipo": tipo, "texto": palavra}
        
        return None
    
    def _extrair_termos_cliente(self, consulta: str, cliente: str) -> List[str]:
        """Extrai termos usados para referenciar o cliente"""
        termos = []
        consulta_lower = consulta.lower()
        cliente_lower = cliente.lower()
        
        # Se o nome completo está na consulta
        if cliente_lower in consulta_lower:
            termos.append(cliente_lower)
        
        # Buscar variações e abreviações
        palavras = consulta_lower.split()
        for palavra in palavras:
            if len(palavra) > 3 and palavra in cliente_lower:
                termos.append(palavra)
        
        return list(set(termos))  # Remover duplicatas
    
    def _identificar_tipo_erro(self, errada: Dict, correta: Dict) -> str:
        """Identifica o tipo de erro na interpretação"""
        if errada.get("cliente_especifico") != correta.get("cliente_especifico"):
            return "cliente_errado"
        elif errada.get("periodo_dias") != correta.get("periodo_dias"):
            return "periodo_errado"
        elif errada.get("dominio") != correta.get("dominio"):
            return "dominio_errado"
        else:
            return "outro"
    
    def _avaliar_melhoria(self, sugestao: str) -> bool:
        """Avalia se uma sugestão de melhoria deve ser aplicada"""
        # Implementação simplificada
        # Em produção, isso poderia usar ML ou regras mais complexas
        palavras_chave = ["melhor", "correto", "deveria", "precisa", "importante"]
        return any(palavra in sugestao.lower() for palavra in palavras_chave)
    
    def _aplicar_melhoria(self, sugestao: str):
        """Aplica uma melhoria sugerida"""
        # Implementação dependeria do tipo de melhoria
        logger.info(f"📈 Melhoria registrada: {sugestao}")
    
    def _atualizar_metricas(self, interpretacao: Dict, feedback: Optional[Dict]):
        """Atualiza métricas de performance"""
        try:
            # Calcular satisfação baseada no feedback
            satisfacao = 1.0  # Default: satisfeito
            if feedback:
                if feedback.get("tipo") == "correction":
                    satisfacao = 0.3  # Correção indica problema
                elif feedback.get("tipo") == "improvement":
                    satisfacao = 0.7  # Sugestão indica espaço para melhorar
            
            # Salvar métrica
            db.session.execute(
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
            
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Erro ao atualizar métricas: {e}")
            db.session.rollback()


# Singleton para uso global
_lifelong_learning = None

def get_lifelong_learning() -> LifelongLearningSystem:
    """Retorna instância única do sistema de aprendizado"""
    global _lifelong_learning
    if _lifelong_learning is None:
        _lifelong_learning = LifelongLearningSystem()
    return _lifelong_learning 