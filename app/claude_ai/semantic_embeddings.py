"""
🧠 SISTEMA DE EMBEDDINGS SEMÂNTICOS
Busca avançada usando OpenAI Embeddings para RAG de alta precisão
"""

import logging
import numpy as np
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import openai
import pickle
import os
from dataclasses import dataclass, asdict
from sklearn.metrics.pairwise import cosine_similarity
import redis
from app.utils.redis_cache import redis_cache, REDIS_DISPONIVEL

logger = logging.getLogger(__name__)

@dataclass
class DocumentoEmbedding:
    """Documento com embedding semântico"""
    id: str
    conteudo: str
    categoria: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = None
    timestamp: datetime = None
    relevancia_score: float = 0.0

class SemanticEmbeddingSystem:
    """
    Sistema de embeddings semânticos para busca avançada de contexto
    """
    
    def __init__(self, openai_api_key: Optional[str] = None):
        self.openai_api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        self.embedding_model = "text-embedding-ada-002"
        self.embedding_cache = {}
        self.documentos_indexados = []
        
        if self.openai_api_key:
            openai.api_key = self.openai_api_key
            logger.info("🧠 Sistema de Embeddings Semânticos inicializado com OpenAI")
        else:
            logger.warning("⚠️ OpenAI API Key não encontrada - usando fallback textual")
    
    def gerar_embedding(self, texto: str) -> List[float]:
        """Gera embedding semântico para um texto"""
        
        # Cache local primeiro
        texto_hash = hash(texto)
        if texto_hash in self.embedding_cache:
            return self.embedding_cache[texto_hash]
        
        # Cache Redis se disponível
        if REDIS_DISPONIVEL:
            cache_key = f"embedding:{texto_hash}"
            cached_embedding = redis_cache.get(cache_key)
            if cached_embedding:
                self.embedding_cache[texto_hash] = cached_embedding
                return cached_embedding
        
        # Gerar novo embedding
        try:
            if self.openai_api_key:
                response = openai.Embedding.create(
                    input=texto,
                    model=self.embedding_model
                )
                embedding = response['data'][0]['embedding']
            else:
                # Fallback: embedding simples baseado em frequência de palavras
                embedding = self._embedding_fallback(texto)
            
            # Salvar em cache
            self.embedding_cache[texto_hash] = embedding
            
            if REDIS_DISPONIVEL:
                redis_cache.set(cache_key, embedding, ttl=86400)  # 24h
            
            return embedding
            
        except Exception as e:
            logger.error(f"❌ Erro ao gerar embedding: {e}")
            return self._embedding_fallback(texto)
    
    def _embedding_fallback(self, texto: str) -> List[float]:
        """Fallback simples para quando OpenAI não está disponível"""
        # Embedding simples baseado em TF-IDF manual
        palavras_importantes = [
            'entrega', 'frete', 'cliente', 'prazo', 'atraso', 'agendamento',
            'transportadora', 'embarque', 'pedido', 'faturamento', 'problema',
            'reagendamento', 'protocolo', 'destino', 'origem', 'volume'
        ]
        
        texto_lower = texto.lower()
        embedding = []
        
        for palavra in palavras_importantes:
            # Frequência normalizada da palavra
            freq = texto_lower.count(palavra) / len(texto_lower.split())
            embedding.append(freq)
        
        # Padronizar para 1536 dimensões (como OpenAI ada-002)
        while len(embedding) < 1536:
            embedding.append(0.0)
        
        return embedding[:1536]
    
    def indexar_dados_sistema(self) -> None:
        """Indexa dados históricos do sistema para busca semântica"""
        
        logger.info("🔄 Iniciando indexação semântica dos dados...")
        
        try:
            from app import db
            from app.monitoramento.models import EntregaMonitorada
            from app.fretes.models import Frete
            from app.embarques.models import Embarque
            
            # Indexar entregas com problemas/comentários
            entregas_problemas = EntregaMonitorada.query.filter(
                EntregaMonitorada.observacoes_entrega.isnot(None),
                EntregaMonitorada.observacoes_entrega != ''
            ).limit(100).all()
            
            for entrega in entregas_problemas:
                conteudo = f"""
                Cliente: {entrega.nome_cliente}
                Destino: {entrega.destino}
                Status: {entrega.status_finalizacao}
                Observações: {entrega.observacoes_entrega}
                Data Entrega: {entrega.data_entrega_prevista}
                """
                
                doc = DocumentoEmbedding(
                    id=f"entrega_{entrega.id}",
                    conteudo=conteudo.strip(),
                    categoria="entregas_problemas",
                    metadata={
                        'cliente': entrega.nome_cliente,
                        'status': entrega.status_finalizacao,
                        'data_entrega': entrega.data_entrega_prevista.isoformat() if entrega.data_entrega_prevista else None
                    },
                    timestamp=datetime.now()
                )
                
                doc.embedding = self.gerar_embedding(doc.conteudo)
                self.documentos_indexados.append(doc)
            
            # Indexar padrões de fretes por transportadora
            fretes_analise = db.session.query(
                Frete.id_transportadora,
                Frete.destino_uf,
                db.func.avg(Frete.valor_cotado).label('valor_medio'),
                db.func.count(Frete.id).label('volume_fretes')
            ).group_by(Frete.id_transportadora, Frete.destino_uf).limit(50).all()
            
            for frete_pattern in fretes_analise:
                conteudo = f"""
                Transportadora ID: {frete_pattern.id_transportadora}
                Destino UF: {frete_pattern.destino_uf}
                Valor Médio: R$ {frete_pattern.valor_medio:.2f}
                Volume: {frete_pattern.volume_fretes} fretes
                Padrão: frete médio para {frete_pattern.destino_uf}
                """
                
                doc = DocumentoEmbedding(
                    id=f"frete_pattern_{frete_pattern.id_transportadora}_{frete_pattern.destino_uf}",
                    conteudo=conteudo.strip(),
                    categoria="padroes_frete",
                    metadata={
                        'transportadora_id': frete_pattern.id_transportadora,
                        'uf': frete_pattern.destino_uf,
                        'valor_medio': float(frete_pattern.valor_medio),
                        'volume': frete_pattern.volume_fretes
                    },
                    timestamp=datetime.now()
                )
                
                doc.embedding = self.gerar_embedding(doc.conteudo)
                self.documentos_indexados.append(doc)
            
            logger.info(f"✅ Indexação concluída: {len(self.documentos_indexados)} documentos")
            
        except Exception as e:
            logger.error(f"❌ Erro na indexação: {e}")
    
    def buscar_contexto_semantico(self, consulta: str, top_k: int = 5, categoria_filtro: str = None) -> List[DocumentoEmbedding]:
        """Busca contexto relevante usando similaridade semântica"""
        
        if not self.documentos_indexados:
            self.indexar_dados_sistema()
        
        # Gerar embedding da consulta
        consulta_embedding = self.gerar_embedding(consulta)
        
        # Calcular similaridades
        documentos_relevantes = []
        
        for doc in self.documentos_indexados:
            # Filtrar por categoria se especificado
            if categoria_filtro and doc.categoria != categoria_filtro:
                continue
            
            # Calcular similaridade do cosseno
            if doc.embedding:
                similarity = cosine_similarity(
                    [consulta_embedding],
                    [doc.embedding]
                )[0][0]
                
                doc.relevancia_score = similarity
                
                # Threshold mínimo de relevância
                if similarity > 0.7:  # Apenas muito relevantes
                    documentos_relevantes.append(doc)
        
        # Ordenar por relevância e retornar top_k
        documentos_relevantes.sort(key=lambda x: x.relevancia_score, reverse=True)
        
        logger.info(f"🔍 Busca semântica: {len(documentos_relevantes)} docs relevantes (threshold >0.7)")
        
        return documentos_relevantes[:top_k]
    
    def analisar_intencao_consulta(self, consulta: str) -> Dict[str, Any]:
        """Analisa a intenção da consulta usando embeddings semânticos"""
        
        # Padrões de intenção com embeddings pré-calculados
        intencoes_padrao = {
            "analise_performance": "análise de performance entregas pontualidade prazo kpi indicadores",
            "resolucao_problema": "problema erro falha resolver ajudar suporte troubleshooting",
            "previsao_demanda": "previsão demanda volume futuro planejamento capacidade forecasting",
            "comparacao_clientes": "comparar clientes performance diferença ranking",
            "status_operacional": "status situação como está andamento operação atual",
            "custos_financeiro": "custo valor preço financeiro orçamento investimento",
            "otimizacao_rotas": "rota otimizar melhorar eficiência reduzir tempo"
        }
        
        consulta_embedding = self.gerar_embedding(consulta)
        
        melhor_intencao = "geral"
        melhor_score = 0.0
        
        for intencao, padrao in intencoes_padrao.items():
            padrao_embedding = self.gerar_embedding(padrao)
            
            similarity = cosine_similarity(
                [consulta_embedding],
                [padrao_embedding]
            )[0][0]
            
            if similarity > melhor_score:
                melhor_score = similarity
                melhor_intencao = intencao
        
        return {
            "intencao_detectada": melhor_intencao,
            "confianca": melhor_score,
            "sugere_template": melhor_intencao if melhor_score > 0.75 else "geral"
        }
    
    def construir_prompt_semantico(self, consulta: str, dados_sistema: Dict[str, Any]) -> str:
        """Constrói prompt enriquecido com contexto semântico"""
        
        # 1. Analisar intenção
        analise_intencao = self.analisar_intencao_consulta(consulta)
        
        # 2. Buscar contexto semântico relevante
        contexto_semantico = self.buscar_contexto_semantico(consulta, top_k=3)
        
        # 3. Construir contexto enriquecido
        contexto_prompt = f"""
🧠 **ANÁLISE SEMÂNTICA DA CONSULTA**
- Intenção detectada: {analise_intencao['intencao_detectada']}
- Confiança: {analise_intencao['confianca']:.2%}
- Template sugerido: {analise_intencao['sugere_template']}

📊 **DADOS DO SISTEMA**
{json.dumps(dados_sistema, indent=2, ensure_ascii=False)}

🔍 **CONTEXTO SEMÂNTICO RELEVANTE**
"""
        
        if contexto_semantico:
            for i, doc in enumerate(contexto_semantico, 1):
                contexto_prompt += f"""
**Documento {i}** (Relevância: {doc.relevancia_score:.2%})
Categoria: {doc.categoria}
Conteúdo: {doc.conteudo[:300]}...
Metadata: {json.dumps(doc.metadata, ensure_ascii=False)}
---"""
        else:
            contexto_prompt += "\nNenhum contexto histórico específico encontrado."
        
        contexto_prompt += f"""

💡 **INSTRUÇÕES ESPECÍFICAS PARA A INTENÇÃO '{analise_intencao['intencao_detectada'].upper()}'**
"""
        
        # Instruções específicas baseadas na intenção
        instrucoes_intencao = {
            "analise_performance": """
- Foque em KPIs e métricas de performance
- Compare com benchmarks do setor
- Identifique tendências e padrões
- Sugira melhorias específicas""",
            
            "resolucao_problema": """
- Identifique a causa raiz do problema
- Forneça soluções imediatas e de longo prazo
- Use o contexto histórico para soluções similares
- Inclua steps acionáveis""",
            
            "previsao_demanda": """
- Analise padrões históricos e sazonais
- Considere fatores externos
- Forneça previsões quantitativas
- Inclua cenários (otimista/realista/pessimista)""",
            
            "comparacao_clientes": """
- Compare métricas entre clientes
- Identifique outliers e padrões
- Rankear por performance
- Destacar oportunidades de melhoria""",
            
            "status_operacional": """
- Forneça visão atual clara e objetiva
- Destaque pontos de atenção
- Use indicadores visuais
- Inclua próximos passos""",
            
            "custos_financeiro": """
- Analise custos e ROI
- Identifique oportunidades de economia
- Compare cenários
- Forneça recomendações financeiras""",
            
            "otimizacao_rotas": """
- Analise eficiência atual
- Identifique gargalos
- Sugira otimizações práticas
- Calcule impacto potencial"""
        }
        
        contexto_prompt += instrucoes_intencao.get(
            analise_intencao['intencao_detectada'],
            "- Forneça análise abrangente e insights acionáveis"
        )
        
        return contexto_prompt
    
    def salvar_cache_embeddings(self, filepath: str = "cache_embeddings.pkl"):
        """Salva cache de embeddings em arquivo"""
        try:
            with open(filepath, 'wb') as f:
                pickle.dump({
                    'cache': self.embedding_cache,
                    'documentos': self.documentos_indexados,
                    'timestamp': datetime.now()
                }, f)
            logger.info(f"💾 Cache de embeddings salvo em {filepath}")
        except Exception as e:
            logger.error(f"❌ Erro ao salvar cache: {e}")
    
    def carregar_cache_embeddings(self, filepath: str = "cache_embeddings.pkl"):
        """Carrega cache de embeddings de arquivo"""
        try:
            if os.path.exists(filepath):
                with open(filepath, 'rb') as f:
                    cache_data = pickle.load(f)
                    
                self.embedding_cache = cache_data.get('cache', {})
                self.documentos_indexados = cache_data.get('documentos', [])
                
                logger.info(f"📂 Cache de embeddings carregado: {len(self.documentos_indexados)} docs")
                return True
        except Exception as e:
            logger.error(f"❌ Erro ao carregar cache: {e}")
        
        return False

class AdvancedPromptChaining:
    """
    Sistema de encadeamento de prompts para consultas complexas
    """
    
    def __init__(self, embedding_system: SemanticEmbeddingSystem):
        self.embedding_system = embedding_system
    
    def processar_consulta_multi_step(self, consulta: str, dados_sistema: Dict[str, Any]) -> str:
        """
        Processa consultas complexas em múltiplas etapas
        """
        
        # Step 1: Analisar complexidade da consulta
        complexidade = self._analisar_complexidade(consulta)
        
        if complexidade['nivel'] == 'simples':
            # Processamento direto
            return self.embedding_system.construir_prompt_semantico(consulta, dados_sistema)
        
        elif complexidade['nivel'] == 'multipla':
            # Quebrar em sub-consultas
            sub_consultas = self._quebrar_consulta(consulta)
            
            prompt_encadeado = "🔗 **CONSULTA MULTI-STEP DETECTADA**\\n\\n"
            
            for i, sub_consulta in enumerate(sub_consultas, 1):
                prompt_encadeado += f"""
**STEP {i}**: {sub_consulta}
{self.embedding_system.construir_prompt_semantico(sub_consulta, dados_sistema)}
---
"""
            
            prompt_encadeado += """
💡 **INSTRUÇÕES FINAIS**:
1. Processe cada STEP sequencialmente
2. Use resultados anteriores para steps seguintes
3. Forneça resposta integrada final
4. Destaque conexões entre os steps
"""
            
            return prompt_encadeado
        
        else:  # complexidade avançada
            return self._processar_consulta_avancada(consulta, dados_sistema)
    
    def _analisar_complexidade(self, consulta: str) -> Dict[str, Any]:
        """Analisa complexidade da consulta"""
        
        indicadores_complexos = [
            'comparar', 'e também', 'além disso', 'ao mesmo tempo',
            'correlação', 'impacto', 'consequência', 'se então'
        ]
        
        indicadores_multiplos = [
            'primeiro', 'segundo', 'depois', 'em seguida',
            'por último', 'antes de', 'após', 'simultaneamente'
        ]
        
        consulta_lower = consulta.lower()
        
        if any(ind in consulta_lower for ind in indicadores_complexos):
            return {'nivel': 'avancada', 'razao': 'consulta_complexa'}
        elif any(ind in consulta_lower for ind in indicadores_multiplos):
            return {'nivel': 'multipla', 'razao': 'multi_step'}
        else:
            return {'nivel': 'simples', 'razao': 'consulta_direta'}
    
    def _quebrar_consulta(self, consulta: str) -> List[str]:
        """Quebra consulta complexa em sub-consultas"""
        
        # Padrões para quebrar consulta
        separadores = [
            r'e também', r'além disso', r'ao mesmo tempo',
            r'depois', r'em seguida', r'por último'
        ]
        
        import re
        
        sub_consultas = [consulta]
        
        for separador in separadores:
            novas_consultas = []
            for sub in sub_consultas:
                partes = re.split(separador, sub, flags=re.IGNORECASE)
                novas_consultas.extend([p.strip() for p in partes if p.strip()])
            sub_consultas = novas_consultas
        
        return sub_consultas[:5]  # Máximo 5 sub-consultas
    
    def _processar_consulta_avancada(self, consulta: str, dados_sistema: Dict[str, Any]) -> str:
        """Processa consultas muito complexas com análise avançada"""
        
        return f"""
🧠 **CONSULTA AVANÇADA DETECTADA**

{self.embedding_system.construir_prompt_semantico(consulta, dados_sistema)}

🔬 **ANÁLISE AVANÇADA REQUERIDA**:
1. Identifique todas as variáveis mencionadas
2. Analise correlações e dependências
3. Considere fatores externos e contexto histórico
4. Forneça análise multi-dimensional
5. Inclua cenários alternativos
6. Sugira investigações adicionais se necessário

⚡ **PROCESSAMENTO**: Use Claude 4 Sonnet em modo de raciocínio extendido
"""

# Instâncias globais
semantic_system = SemanticEmbeddingSystem()
prompt_chaining = AdvancedPromptChaining(semantic_system)

def processar_com_embeddings_semanticos(consulta: str, dados_sistema: Dict[str, Any]) -> str:
    """
    Função principal para processar consultas com embeddings semânticos
    """
    return prompt_chaining.processar_consulta_multi_step(consulta, dados_sistema) 