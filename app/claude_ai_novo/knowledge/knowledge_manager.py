"""
📊 KNOWLEDGE MANAGER - Gestão de Conhecimento
============================================

Módulo especializado em gerenciar conhecimento adquirido,
mapeamentos semânticos e grupos empresariais.

Responsabilidades:
- Gestão de mapeamentos semânticos
- Descoberta de grupos empresariais
- Estatísticas de aprendizado
- Base de conhecimento
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from flask import current_app

logger = logging.getLogger(__name__)

class KnowledgeManager:
    """
    Especialista em gestão de conhecimento e descoberta de padrões.
    
    Gerencia base de conhecimento, mapeamentos semânticos
    e descoberta automática de grupos empresariais.
    """
    
    def __init__(self):
        """Inicializa o gerenciador de conhecimento"""
        logger.info("📊 KnowledgeManager inicializado")
    
    def aprender_mapeamento_cliente(self, consulta: str, cliente: str) -> Optional[Dict]:
        """
        Aprende como usuários se referem a clientes específicos.
        
        Args:
            consulta: Consulta original
            cliente: Nome oficial do cliente
            
        Returns:
            Dict com mapeamento aprendido ou None se erro
        """
        try:
            with current_app.app_context():
                from app import db
                from sqlalchemy import text
                
                # Extrair termos usados para o cliente
                termos = self._extrair_termos_cliente(consulta, cliente)
                mapeamentos_criados = []
                
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
                        mapeamentos_criados.append({"termo": termo, "acao": "atualizado"})
                    else:
                        # Criar novo mapeamento
                        db.session.execute(
                            text("""
                                INSERT INTO ai_semantic_mappings
                                (termo_usuario, campo_sistema, modelo, contexto, frequencia)
                                VALUES (:termo, :campo, 'cliente', :contexto, 1)
                            """),
                            {
                                "termo": termo.lower(),
                                "campo": cliente,
                                "contexto": json.dumps({"consulta": consulta})
                            }
                        )
                        mapeamentos_criados.append({"termo": termo, "acao": "criado"})
                
                db.session.commit()
                
                return {
                    "cliente": cliente,
                    "termos_aprendidos": [m["termo"] for m in mapeamentos_criados],
                    "mapeamentos": mapeamentos_criados,
                    "total_termos": len(termos)
                }
                
        except Exception as e:
            logger.error(f"❌ Erro ao aprender mapeamento: {e}")
            try:
                from app import db
                db.session.rollback()
            except:
                pass
            return None
    
    def descobrir_grupo_empresarial(self, interpretacao: Dict) -> Optional[Dict]:
        """
        Descobre e salva novos grupos empresariais automaticamente.
        
        Args:
            interpretacao: Interpretação que contém dados de grupo
            
        Returns:
            Dict com grupo descoberto ou None se já existe/erro
        """
        try:
            grupo_info = interpretacao.get("grupo_empresarial", {})
            if not grupo_info:
                return None
            
            nome_grupo = grupo_info.get("grupo_detectado")
            if not nome_grupo:
                return None
            
            with current_app.app_context():
                from app import db
                from sqlalchemy import text
                
                # Verificar se já existe
                existe = db.session.execute(
                    text("SELECT id FROM ai_grupos_empresariais WHERE nome_grupo = :nome"),
                    {"nome": nome_grupo}
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
                            "nome": nome_grupo,
                            "tipo": grupo_info.get("tipo_negocio", "varejo"),
                            "cnpjs": grupo_info.get("cnpj_prefixos", []),
                            "palavras": grupo_info.get("keywords", []),
                            "filtro": grupo_info.get("filtro_sql", ""),
                            "regras": json.dumps(grupo_info.get("regras_deteccao", {})),
                            "stats": json.dumps(grupo_info.get("estatisticas", {}))
                        }
                    )
                    
                    novo_id = result.scalar()
                    db.session.commit()
                    
                    logger.info(f"🏢 Novo grupo empresarial descoberto: {nome_grupo}")
                    
                    return {
                        "id": novo_id,
                        "nome_grupo": nome_grupo,
                        "tipo_negocio": grupo_info.get("tipo_negocio"),
                        "descoberto_automaticamente": True,
                        "data_descoberta": datetime.now().isoformat()
                    }
                
                return None  # Já existe
                
        except Exception as e:
            logger.error(f"❌ Erro ao descobrir grupo: {e}")
            try:
                from app import db
                db.session.rollback()
            except:
                pass
            return None
    
    def buscar_grupos_aplicaveis(self, consulta: str) -> List[Dict]:
        """
        Busca grupos empresariais aplicáveis à consulta.
        
        Args:
            consulta: Consulta a ser analisada
            
        Returns:
            Lista de grupos aplicáveis
        """
        try:
            with current_app.app_context():
                from app import db
                from sqlalchemy import text
                
                grupos = db.session.execute(
                    text("""
                        SELECT nome_grupo, tipo_negocio, filtro_sql, 
                               array_to_string(cnpj_prefixos, ',') as cnpjs_str,
                               array_to_string(palavras_chave, ',') as palavras_str
                        FROM ai_grupos_empresariais
                        WHERE ativo = TRUE
                        AND (
                            EXISTS (
                                SELECT 1 FROM unnest(palavras_chave) AS palavra
                                WHERE LOWER(:consulta) LIKE '%' || LOWER(palavra) || '%'
                            )
                            OR 
                            nome_grupo ILIKE '%' || :consulta || '%'
                        )
                        LIMIT 5
                    """),
                    {"consulta": consulta}
                ).fetchall()
                
                grupos_aplicaveis = []
                for grupo in grupos:
                    # Converter strings de volta para listas
                    cnpjs = grupo.cnpjs_str.split(',') if grupo.cnpjs_str else []
                    palavras = grupo.palavras_str.split(',') if grupo.palavras_str else []
                    
                    grupos_aplicaveis.append({
                        "nome": grupo.nome_grupo,
                        "tipo": grupo.tipo_negocio,
                        "filtro": grupo.filtro_sql,
                        "cnpjs": [c.strip() for c in cnpjs if c.strip()],
                        "palavras": [p.strip() for p in palavras if p.strip()]
                    })
                
                return grupos_aplicaveis
                
        except Exception as e:
            logger.warning(f"Erro ao buscar grupos: {e}")
            return []
    
    def buscar_mapeamentos_aplicaveis(self, consulta: str) -> List[Dict]:
        """
        Busca mapeamentos semânticos aplicáveis à consulta.
        
        Args:
            consulta: Consulta a ser analisada
            
        Returns:
            Lista de mapeamentos aplicáveis
        """
        try:
            with current_app.app_context():
                from app import db
                from sqlalchemy import text
                
                mapeamentos = db.session.execute(
                    text("""
                        SELECT DISTINCT campo_sistema, modelo, MAX(frequencia) as frequencia,
                               array_agg(DISTINCT termo_usuario) as termos
                        FROM ai_semantic_mappings
                        WHERE LOWER(:consulta) LIKE '%' || LOWER(termo_usuario) || '%'
                        AND frequencia > 1
                        GROUP BY campo_sistema, modelo
                        ORDER BY frequencia DESC
                        LIMIT 10
                    """),
                    {"consulta": consulta}
                ).fetchall()
                
                mapeamentos_aplicaveis = []
                for mapa in mapeamentos:
                    mapeamentos_aplicaveis.append({
                        "campo": mapa.campo_sistema,
                        "modelo": mapa.modelo,
                        "frequencia": mapa.frequencia,
                        "termos_usuario": mapa.termos[:5]  # Limitar a 5 termos
                    })
                
                return mapeamentos_aplicaveis
                
        except Exception as e:
            logger.error(f"❌ Erro ao buscar mapeamentos: {e}")
            return []
    
    def obter_estatisticas_aprendizado(self) -> Dict[str, Any]:
        """
        Obtém estatísticas completas do sistema de aprendizado.
        
        Returns:
            Dict com estatísticas detalhadas
        """
        try:
            with current_app.app_context():
                from app import db
                from sqlalchemy import text
                
                stats = {}
                
                # Total de padrões aprendidos
                total_padroes = db.session.execute(
                    text("SELECT COUNT(*) as total FROM ai_knowledge_patterns")
                ).scalar() or 0
                
                # Padrões de alta confiança
                padroes_confiaveis = db.session.execute(
                    text("SELECT COUNT(*) as total FROM ai_knowledge_patterns WHERE confidence > 0.8")
                ).scalar() or 0
                
                # Grupos empresariais
                total_grupos = db.session.execute(
                    text("SELECT COUNT(*) as total FROM ai_grupos_empresariais WHERE ativo = TRUE")
                ).scalar() or 0
                
                # Grupos descobertos automaticamente
                grupos_auto = db.session.execute(
                    text("SELECT COUNT(*) as total FROM ai_grupos_empresariais WHERE aprendido_automaticamente = TRUE")
                ).scalar() or 0
                
                # Mapeamentos semânticos
                total_mapeamentos = db.session.execute(
                    text("SELECT COUNT(*) as total FROM ai_semantic_mappings")
                ).scalar() or 0
                
                # Mapeamentos ativos (frequência > 1)
                mapeamentos_ativos = db.session.execute(
                    text("SELECT COUNT(*) as total FROM ai_semantic_mappings WHERE frequencia > 1")
                ).scalar() or 0
                
                # Taxa de aprendizado (últimos 7 dias)
                aprendizado_recente = db.session.execute(
                    text("""
                        SELECT COUNT(*) as total 
                        FROM ai_learning_history 
                        WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '7 days'
                    """)
                ).scalar() or 0
                
                # Feedback recente (últimos 7 dias)
                feedback_recente = db.session.execute(
                    text("""
                        SELECT COUNT(*) as total 
                        FROM ai_feedback_history 
                        WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '7 days'
                    """)
                ).scalar() or 0
                
                # Calcular métricas derivadas
                taxa_confianca = (padroes_confiaveis / total_padroes * 100) if total_padroes > 0 else 0
                taxa_grupos_auto = (grupos_auto / total_grupos * 100) if total_grupos > 0 else 0
                taxa_mapeamentos_ativos = (mapeamentos_ativos / total_mapeamentos * 100) if total_mapeamentos > 0 else 0
                
                stats = {
                    "timestamp": datetime.now().isoformat(),
                    "padroes": {
                        "total": total_padroes,
                        "confiaveis": padroes_confiaveis,
                        "taxa_confianca": round(taxa_confianca, 2)
                    },
                    "grupos_empresariais": {
                        "total": total_grupos,
                        "descobertos_automaticamente": grupos_auto,
                        "taxa_descoberta_automatica": round(taxa_grupos_auto, 2)
                    },
                    "mapeamentos_semanticos": {
                        "total": total_mapeamentos,
                        "ativos": mapeamentos_ativos,
                        "taxa_uso": round(taxa_mapeamentos_ativos, 2)
                    },
                    "atividade_recente": {
                        "aprendizado_semanal": aprendizado_recente,
                        "feedback_semanal": feedback_recente,
                        "status": "ativo" if aprendizado_recente > 0 else "inativo"
                    },
                    "qualidade_geral": self._calcular_qualidade_geral(taxa_confianca, aprendizado_recente)
                }
                
                return stats
                
        except Exception as e:
            logger.error(f"❌ Erro ao obter estatísticas: {e}")
            return {
                "erro": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _extrair_termos_cliente(self, consulta: str, cliente: str) -> List[str]:
        """
        Extrai termos usados para referenciar um cliente.
        
        Args:
            consulta: Consulta original
            cliente: Nome oficial do cliente
            
        Returns:
            Lista de termos extraídos
        """
        termos = []
        consulta_lower = consulta.lower()
        cliente_lower = cliente.lower()
        
        # Nome completo
        if cliente_lower in consulta_lower:
            termos.append(cliente_lower)
        
        # Palavras individuais significativas do nome do cliente
        palavras_cliente = [p for p in cliente_lower.split() if len(p) > 2]
        for palavra in palavras_cliente:
            if palavra in consulta_lower:
                termos.append(palavra)
        
        # Buscar abreviações e variações na consulta
        palavras_consulta = [p for p in consulta_lower.split() if len(p) > 2]
        for palavra in palavras_consulta:
            # Verificar se palavra está contida no nome do cliente
            if palavra in cliente_lower or cliente_lower.startswith(palavra):
                termos.append(palavra)
        
        return list(set(termos))  # Remove duplicatas
    
    def _calcular_qualidade_geral(self, taxa_confianca: float, atividade_recente: int) -> str:
        """
        Calcula qualidade geral do sistema baseada nas métricas.
        
        Args:
            taxa_confianca: Taxa de confiança dos padrões
            atividade_recente: Atividade de aprendizado recente
            
        Returns:
            Qualidade geral do sistema
        """
        if atividade_recente == 0:
            return "INATIVO"
        elif taxa_confianca >= 80:
            return "EXCELENTE"
        elif taxa_confianca >= 60:
            return "BOA"
        elif taxa_confianca >= 40:
            return "REGULAR"
        else:
            return "BAIXA"


# Singleton para uso global
_knowledge_manager = None

def get_knowledge_manager() -> KnowledgeManager:
    """
    Obtém instância única do gerenciador de conhecimento.
    
    Returns:
        Instância do KnowledgeManager
    """
    global _knowledge_manager
    if _knowledge_manager is None:
        _knowledge_manager = KnowledgeManager()
    return _knowledge_manager 