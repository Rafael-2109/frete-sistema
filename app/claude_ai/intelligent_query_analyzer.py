#!/usr/bin/env python3
"""
🧠 ANALISADOR INTELIGENTE DE CONSULTAS - Entendimento Avançado do Usuário
Melhora a interpretação das consultas para respostas mais precisas e coerentes
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
import json
import difflib

# Tentar importar NLP avançado
try:
    from .nlp_enhanced_analyzer import get_nlp_analyzer, AnaliseNLP
    NLP_AVAILABLE = True
except ImportError:
    NLP_AVAILABLE = False
    logging.warning("⚠️ NLP avançado não disponível. Instale com: pip install -r requirements_completo.txt")

import logging

logger = logging.getLogger(__name__)

class TipoInformacao(Enum):
    """Tipos de informação que o usuário pode estar buscando"""
    LISTAGEM = "listagem"  # "quais são", "liste", "mostre"
    QUANTIDADE = "quantidade"  # "quantos", "quantas", "total"
    STATUS = "status"  # "situação", "como está", "posição"
    HISTORICO = "historico"  # "histórico", "evolução", "antes"
    COMPARACAO = "comparacao"  # "comparar", "diferença", "vs"
    DETALHAMENTO = "detalhamento"  # "detalhes", "completo", "informações"
    PROBLEMAS = "problemas"  # "atrasos", "problemas", "pendências"
    METRICAS = "metricas"  # "performance", "indicadores", "percentual"
    PREVISAO = "previsao"  # "quando", "prazo", "estimativa"
    LOCALIZACAO = "localizacao"  # "onde", "local", "endereço"

class NivelDetalhamento(Enum):
    """Nível de detalhamento desejado"""
    RESUMO = "resumo"  # Resposta sintética
    COMPLETO = "completo"  # Resposta detalhada
    EXECUTIVO = "executivo"  # Visão gerencial
    OPERACIONAL = "operacional"  # Detalhes operacionais

class UrgenciaConsulta(Enum):
    """Urgência da consulta"""
    BAIXA = "baixa"  # Consulta informativa
    MEDIA = "media"  # Consulta operacional
    ALTA = "alta"  # Problema a resolver
    CRITICA = "critica"  # Emergência

@dataclass
class InterpretacaoConsulta:
    """Resultado da interpretação inteligente da consulta"""
    consulta_original: str
    intencao_principal: TipoInformacao
    tipo_detalhamento: NivelDetalhamento
    urgencia: UrgenciaConsulta
    entidades_detectadas: Dict[str, List[str]]
    escopo_temporal: Dict[str, Any]
    filtros_implicitios: Dict[str, Any]
    contexto_negocio: Dict[str, Any]
    probabilidade_interpretacao: float
    consultas_similares: List[str]
    sugestoes_esclarecimento: List[str]
    prompt_otimizado: str
    
    @property
    def confianca_interpretacao(self) -> float:
        """Propriedade para acessar a probabilidade como confiança"""
        return self.probabilidade_interpretacao

class IntelligentQueryAnalyzer:
    """
    🧠 Analisador Inteligente de Consultas
    
    Melhora drasticamente o entendimento das consultas do usuário através de:
    - Análise semântica avançada
    - Detecção de intenção precisa
    - Contextualização inteligente
    - Sugestões de esclarecimento
    - Otimização de prompts para Claude
    """
    
    def __init__(self):
        """Inicializa o analisador inteligente"""
        self.padroes_intencao = self._criar_padroes_intencao()
        self.termos_negocio = self._criar_dicionario_negocio()
        self.padroes_temporais = self._criar_padroes_temporais()
        self.contextos_urgencia = self._criar_contextos_urgencia()
        self.mapeamento_clientes = self._criar_mapeamento_clientes()
        
        logger.info("🧠 Analisador Inteligente de Consultas inicializado")
    
    def _criar_padroes_intencao(self) -> Dict[TipoInformacao, List[str]]:
        """Cria padrões para detectar intenção do usuário"""
        
        return {
            TipoInformacao.LISTAGEM: [
                r"(?:liste|mostre|quais são|quais|listar|mostrar)",
                r"(?:veja|verifique|consulte)\s+(?:as|os|todas|todos)",
                r"(?:dê uma olhada|dá uma olhada)\s+(?:nas|nos)",
                r"(?:preciso ver|quero ver|gostaria de ver)"
            ],
            
            TipoInformacao.QUANTIDADE: [
                r"(?:quantos?|quantas?|total de|número de|qtd)",
                r"(?:conte|contar|somar|somatório)",
                r"(?:volume de|quantidade de)",
                r"(?:tenho|temos)\s+(?:quantos?|quantas?)"
            ],
            
            TipoInformacao.STATUS: [
                r"(?:situação|status|posição|estado)\s+(?:do|da|dos|das)",
                r"(?:como está|como estão|como anda|como andam)",
                r"(?:em que pé|andamento|progresso)",
                r"(?:qual o status|qual a situação)"
            ],
            
            TipoInformacao.HISTORICO: [
                r"(?:histórico|evolução|progressão|desenvolvimento)",
                r"(?:ao longo do tempo|durante|período|timeline)",
                r"(?:antes|anteriormente|passou|aconteceu)",
                r"(?:linha do tempo|cronologia|sequência)"
            ],
            
            TipoInformacao.COMPARACAO: [
                r"(?:comparar?|comparação|versus|vs|contra)",
                r"(?:diferença|diferenças|distinguir)",
                r"(?:melhor|pior|mais|menos)\s+(?:que|do que)",
                r"(?:em relação a|comparado com|face a)"
            ],
            
            TipoInformacao.DETALHAMENTO: [
                r"(?:detalhes|informações completas|dados completos)",
                r"(?:detalhar|detalhe|especificar|especificação)",
                r"(?:completo|completa|integral|integralmente)",
                r"(?:mais informações|dados adicionais|tudo sobre)"
            ],
            
            TipoInformacao.PROBLEMAS: [
                r"(?:problema|problemas|erro|falha|issue)",
                r"(?:atraso|atrasado|atrasada|pendente|pendência)",
                r"(?:crítico|urgente|emergência|bloqueado)",
                r"(?:não entregue|não chegou|não foi|falhou)"
            ],
            
            TipoInformacao.METRICAS: [
                r"(?:performance|desempenho|indicador|métrica)",
                r"(?:percentual|porcentagem|taxa|índice)",
                r"(?:eficiência|produtividade|qualidade)",
                r"(?:kpi|resultado|meta|objetivo)"
            ],
            
            TipoInformacao.PREVISAO: [
                r"(?:quando|que horas?|que dia|previsão)",
                r"(?:vai|irá|será)\s+(?:entregar?|chegar?|partir?)",
                r"(?:estimativa|prazo|tempo|duração)",
                r"(?:prever|prognóstico|expectativa)"
            ],
            
            TipoInformacao.LOCALIZACAO: [
                r"(?:onde|local|localização|endereço)",
                r"(?:está localizado|se encontra|fica)",
                r"(?:destino|origem|rota|caminho)",
                r"(?:posição|coordenadas|mapa)"
            ]
        }
    
    def _criar_dicionario_negocio(self) -> Dict[str, Dict[str, List[str]]]:
        """Cria dicionário expandido de termos de negócio"""
        
        return {
            "clientes": {
                "grandes_redes": [
                    "assai", "atacadão", "atacadao", "carrefour", "tenda", "fort", "mateus",
                    "coco bambu", "mercantil rodrigues", "rede", "filial", "loja"
                ],
                "sinonimos": [
                    "cliente", "comprador", "destinatário", "empresa", "corporação",
                    "estabelecimento", "negócio", "conta", "parceiro comercial"
                ]
            },
            
            "produtos_servicos": {
                "entrega": [
                    "entrega", "delivery", "distribuição", "envio", "despacho",
                    "expedição", "remessa", "transporte", "logística"
                ],
                "agendamento": [
                    "agendamento", "agenda", "agendado", "marcado", "programado",
                    "protocolo", "horário", "data marcada", "appointment"
                ]
            },
            
            "status_operacionais": {
                "positivos": [
                    "entregue", "completo", "finalizado", "ok", "sucesso",
                    "realizado", "concluído", "aprovado", "liberado"
                ],
                "negativos": [
                    "atrasado", "pendente", "bloqueado", "cancelado", "problema",
                    "falha", "erro", "crítico", "rejeitado", "devolvido"
                ],
                "neutros": [
                    "em andamento", "processando", "aguardando", "em análise",
                    "em trânsito", "separação", "preparando"
                ]
            },
            
            "indicadores_tempo": {
                "urgente": [
                    "urgente", "emergência", "crítico", "imediato", "já",
                    "agora", "hoje", "priority", "rush", "express"
                ],
                "periodos": [
                    "hoje", "ontem", "amanhã", "semana", "mês", "trimestre",
                    "ano", "período", "intervalo", "desde", "até"
                ]
            },
            
            "geografia": {
                "regioes": [
                    "sudeste", "sul", "nordeste", "norte", "centro-oeste",
                    "região", "estado", "capital", "interior", "litoral"
                ],
                "localidades": [
                    "cidade", "município", "bairro", "zona", "distrito",
                    "área", "região", "localidade", "endereço"
                ]
            }
        }
    
    def _criar_padroes_temporais(self) -> Dict[str, Any]:
        """Cria padrões para interpretar referências temporais"""
        
        return {
            "absolutos": {
                "hoje": {"dias": 0, "tipo": "data_especifica"},
                "ontem": {"dias": -1, "tipo": "data_especifica"},
                "amanhã": {"dias": 1, "tipo": "data_especifica"},
                r"(\d{1,2})/(\d{1,2})": {"tipo": "data_formatada", "formato": "dd/mm"},
                r"(\d{1,2})/(\d{1,2})/(\d{4})": {"tipo": "data_formatada", "formato": "dd/mm/aaaa"}
            },
            
            "relativos": {
                "última semana": {"dias": -7, "tipo": "periodo"},
                "próxima semana": {"dias": 7, "tipo": "periodo"},
                "último mês": {"dias": -30, "tipo": "periodo"},
                "próximo mês": {"dias": 30, "tipo": "periodo"},
                r"últimos? (\d+) dias?": {"tipo": "periodo_personalizado", "multiplicador": -1},
                r"próximos? (\d+) dias?": {"tipo": "periodo_personalizado", "multiplicador": 1}
            },
            
            "meses": {
                "janeiro": 1, "fevereiro": 2, "março": 3, "abril": 4,
                "maio": 5, "junho": 6, "julho": 7, "agosto": 8,
                "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12
            }
        }
    
    def _criar_contextos_urgencia(self) -> Dict[UrgenciaConsulta, List[str]]:
        """Define contextos que indicam urgência"""
        
        return {
            UrgenciaConsulta.CRITICA: [
                "emergência", "crítico", "urgent", "parou", "quebrou",
                "não funciona", "erro grave", "falha crítica", "problema sério"
            ],
            
            UrgenciaConsulta.ALTA: [
                "urgente", "rápido", "imediato", "já", "agora",
                "problema", "atraso", "atrasado", "pendente crítico"
            ],
            
            UrgenciaConsulta.MEDIA: [
                "importante", "necessário", "preciso", "operacional",
                "rotina", "verificar", "confirmar", "status"
            ],
            
            UrgenciaConsulta.BAIXA: [
                "informação", "consulta", "gostaria", "curiosidade",
                "relatório", "dados", "estatística", "análise"
            ]
        }
    
    def _criar_mapeamento_clientes(self) -> Dict[str, List[str]]:
        """Cria mapeamento inteligente de clientes e variações"""
        
        return {
            "Assai": [
                "assai", "assaí", "asai", "açaí", "assa", "assay"
            ],
            "Atacadão": [
                "atacadão", "atacadao", "atacadão", "atacado", "ataca", "atacadao"
            ],
            "Carrefour": [
                "carrefour", "carrefur", "carrefor", "carrefou", "carreful"
            ],
            "Tenda": [
                "tenda", "tend", "tendas"
            ],
            "Fort": [
                "fort", "forte", "fortemente"
            ],
            "Mateus": [
                "mateus", "matheus", "mateeus", "supermercados mateus"
            ]
        }
    
    def analisar_consulta_inteligente(self, consulta: str, contexto_usuario: Dict[str, Any] = None) -> InterpretacaoConsulta:
        """
        Análise inteligente completa da consulta do usuário
        
        Args:
            consulta: Consulta em linguagem natural
            contexto_usuario: Contexto adicional do usuário
            
        Returns:
            InterpretacaoConsulta: Interpretação completa e inteligente
        """
        
        logger.info(f"🧠 Analisando consulta inteligente: '{consulta[:50]}...'")
        
        # 1. Pré-processamento e normalização
        consulta_normalizada = self._normalizar_consulta(consulta)
        
        # 2. Detecção de intenção principal
        intencao = self._detectar_intencao_principal(consulta_normalizada)
        
        # 3. Análise de nível de detalhamento
        detalhamento = self._analisar_nivel_detalhamento(consulta_normalizada)
        
        # 4. Avaliação de urgência
        urgencia = self._avaliar_urgencia(consulta_normalizada)
        
        # 5. Extração de entidades de negócio
        entidades = self._extrair_entidades_negocio(consulta_normalizada)
        
        # 6. Análise temporal
        escopo_temporal = self._analisar_escopo_temporal(consulta_normalizada)
        
        # 7. Detecção de filtros implícitos
        filtros = self._detectar_filtros_implicitos(consulta_normalizada, entidades)
        
        # 8. Análise de contexto de negócio
        contexto_negocio = self._analisar_contexto_negocio(entidades, intencao)
        
        # 9. Cálculo de probabilidade de interpretação
        probabilidade = self._calcular_probabilidade_interpretacao(
            intencao, entidades, escopo_temporal
        )
        
        # 10. Busca de consultas similares
        consultas_similares = self._buscar_consultas_similares(consulta_normalizada)
        
        # 11. Geração de sugestões de esclarecimento
        sugestoes = self._gerar_sugestoes_esclarecimento(
            consulta_normalizada, intencao, entidades, probabilidade
        )
        
        # 12. Otimização do prompt para Claude
        prompt_otimizado = self._otimizar_prompt_claude(
            consulta, intencao, entidades, escopo_temporal, filtros
        )
        
        interpretacao = InterpretacaoConsulta(
            consulta_original=consulta,
            intencao_principal=intencao,
            tipo_detalhamento=detalhamento,
            urgencia=urgencia,
            entidades_detectadas=entidades,
            escopo_temporal=escopo_temporal,
            filtros_implicitios=filtros,
            contexto_negocio=contexto_negocio,
            probabilidade_interpretacao=probabilidade,
            consultas_similares=consultas_similares,
            sugestoes_esclarecimento=sugestoes,
            prompt_otimizado=prompt_otimizado
        )
        
        logger.info(f"✅ Interpretação concluída - Intenção: {intencao.value}, Confiança: {probabilidade:.2f}")
        
        return interpretacao
    
    def _normalizar_consulta(self, consulta: str) -> str:
        """Normaliza a consulta para análise"""
        
        # Se NLP disponível, usar análise avançada
        if NLP_AVAILABLE:
            nlp_analyzer = get_nlp_analyzer()
            analise = nlp_analyzer.analisar_com_nlp(consulta)
            
            # Aplicar correções sugeridas pelo NLP
            texto_corrigido = consulta.lower()
            for erro, correcao in analise.correcoes_sugeridas.items():
                texto_corrigido = texto_corrigido.replace(erro, correcao)
            
            logger.info(f"🧠 NLP aplicou {len(analise.correcoes_sugeridas)} correções")
            
            # Se teve correções significativas, usar texto corrigido
            if analise.correcoes_sugeridas:
                normalizada = texto_corrigido
            else:
                normalizada = consulta.lower().strip()
        else:
            # Converter para minúsculas
            normalizada = consulta.lower().strip()
        
        # Correções ortográficas comuns (mesmo com NLP, aplicar extras)
        correcoes = {
            "assai": "assai",
            "asai": "assai", 
            "açaí": "assai",
            "atacadao": "atacadão",
            "atacado": "atacadão",
            "carrefur": "carrefour",
            "entrgas": "entregas",
            "pedids": "pedidos",
            "relatoru": "relatório",
            "quantd": "quando",
            "ond": "onde"
        }
        
        for erro, corrigido in correcoes.items():
            normalizada = re.sub(rf"\b{erro}\b", corrigido, normalizada)
        
        # Expansão de abreviações
        abreviacoes = {
            r"\bnf\b": "nota fiscal",
            r"\bcte\b": "conhecimento de transporte",  
            r"\bpdd\b": "pedido",
            r"\bqtd\b": "quantidade",
            r"\bsp\b": "são paulo",
            r"\brj\b": "rio de janeiro"
        }
        
        for pattern, expansao in abreviacoes.items():
            normalizada = re.sub(pattern, expansao, normalizada)
        
        return normalizada
    
    def _detectar_intencao_principal(self, consulta: str) -> TipoInformacao:
        """Detecta a intenção principal da consulta"""
        
        pontuacoes = {}
        
        # 🎯 PRIORIDADE 1: FATURAMENTO - Detectar primeiro palavras de faturamento
        padroes_faturamento = [
            r"\bfaturad[oa]s?\b",              # "faturado", "faturada", "faturados"
            r"\bfaturamento\b",                # "faturamento"
            r"\bfatura(?:s)?\b",               # "fatura", "faturas"
            r"\bnota(?:s)?\s+fiscal(?:ais)?\b", # "nota fiscal", "notas fiscais"
            r"\bemitid[oa]s?\b.*\bnf\b",       # "emitido NF", "emitida nota"
            r"(?:o\s+)?que\s+foi\s+faturad[oa]", # "o que foi faturado"
            r"valor\s+faturad[oa]",            # "valor faturado"
            r"receita\s+(?:do\s+)?(?:dia|mês|período)" # "receita do dia"
        ]
        
        for pattern in padroes_faturamento:
            if re.search(pattern, consulta, re.IGNORECASE):
                logger.info(f"💰 FATURAMENTO detectado: padrão '{pattern}'")
                return TipoInformacao.STATUS  # Faturamento é um tipo de status/informação
        
        # 🔧 PRIORIDADE 2: STATUS - Priorizar padrões específicos de STATUS sobre LOCALIZACAO
        padroes_status_prioritarios = [
            r"como\s+está(?:o|ão|m)?\s+(?:os?|as?)\s+\w+",  # "como estão os embarques"
            r"como\s+anda(?:m)?\s+(?:os?|as?)\s+\w+",       # "como andam as entregas"
            r"situação\s+(?:do|da|dos|das)\s+\w+",           # "situação dos pedidos"
            r"status\s+(?:do|da|dos|das)\s+\w+",             # "status das entregas"
            r"(?:qual|como)\s+(?:o|a)\s+(?:situação|status|posição)"  # "qual o status"
        ]
        
        # Se encontrar padrão de STATUS prioritário, definir como STATUS
        for pattern in padroes_status_prioritarios:
            if re.search(pattern, consulta, re.IGNORECASE):
                logger.info(f"🎯 PADRÃO STATUS PRIORITÁRIO detectado: {pattern}")
                return TipoInformacao.STATUS
        
        # 🔧 PRIORIDADE 3: EMBARQUES - Detectar padrões de EMBARQUES especificamente
        if re.search(r"\bembarques?\b", consulta, re.IGNORECASE):
            # Se menciona "embarques", é provável que seja STATUS ou LISTAGEM
            if any(palavra in consulta.lower() for palavra in ["como", "status", "situação", "estão", "está"]):
                logger.info("🎯 EMBARQUES + STATUS detectado")
                return TipoInformacao.STATUS
            else:
                logger.info("🎯 EMBARQUES + LISTAGEM detectado")
                return TipoInformacao.LISTAGEM
        
        # Continuar com detecção normal para outros casos
        for intencao, padroes in self.padroes_intencao.items():
            pontos = 0
            for pattern in padroes:
                matches = re.findall(pattern, consulta, re.IGNORECASE)
                pontos += len(matches) * 2  # Peso maior para matches de padrão
            
            # Busca por palavras-chave relacionadas
            palavras_chave = self._obter_palavras_chave_intencao(intencao)
            for palavra in palavras_chave:
                if palavra in consulta:
                    pontos += 1
            
            if pontos > 0:
                pontuacoes[intencao] = pontos
        
        # 🔧 CORREÇÃO CRÍTICA: Penalizar/remover LOCALIZACAO quando não é realmente sobre localização
        if TipoInformacao.LOCALIZACAO in pontuacoes:
            # Lista de palavras que realmente indicam localização
            palavras_localizacao_explicitas = [
                "onde", "local", "localização", "endereço", "fica", "localizado", 
                "posição", "coordenadas", "mapa", "lugar", "está localizado",
                "se encontra", "destino", "origem", "rota", "caminho"
            ]
            
            # Lista de palavras que NUNCA são sobre localização
            palavras_que_nao_sao_localizacao = [
                "faturado", "faturamento", "fatura", "situação", "status", 
                "como está", "como estão", "o que foi", "valor", "receita",
                "até agora", "hoje", "nota fiscal", "emitido"
            ]
            
            # Se tem palavras que NÃO são localização, remover LOCALIZACAO completamente
            if any(palavra in consulta.lower() for palavra in palavras_que_nao_sao_localizacao):
                del pontuacoes[TipoInformacao.LOCALIZACAO]
                logger.info("❌ LOCALIZACAO removida: consulta sobre status/faturamento/informações")
            
            # Se não tem palavras explícitas de localização, penalizar drasticamente
            elif not any(palavra in consulta.lower() for palavra in palavras_localizacao_explicitas):
                pontuacoes[TipoInformacao.LOCALIZACAO] = pontuacoes[TipoInformacao.LOCALIZACAO] * 0.01
                logger.info("⬇️ LOCALIZACAO drasticamente penalizada: sem palavras explícitas de localização")
        
        # Se não detectou nenhuma intenção específica ou dicionário ficou vazio, usar heurísticas
        if not pontuacoes:
            if any(palavra in consulta for palavra in ["?", "como", "qual"]):
                logger.info("🎯 Heurística: STATUS (palavras interrogativas)")
                return TipoInformacao.STATUS
            else:
                logger.info("🎯 Heurística: LISTAGEM (padrão)")
                return TipoInformacao.LISTAGEM
        
        # Retornar intenção com maior pontuação (só se dict não estiver vazio)
        intencao_detectada = max(pontuacoes.items(), key=lambda x: x[1])[0]
        
        logger.info(f"🎯 Intenção detectada: {intencao_detectada.value} (pontos: {pontuacoes})")
        
        return intencao_detectada
    
    def _obter_palavras_chave_intencao(self, intencao: TipoInformacao) -> List[str]:
        """Obtém palavras-chave relacionadas a cada intenção"""
        
        palavras_chave = {
            TipoInformacao.LISTAGEM: ["lista", "todos", "todas", "ver", "mostre"],
            TipoInformacao.QUANTIDADE: ["total", "soma", "contagem", "número"],
            TipoInformacao.STATUS: ["situação", "andamento", "progresso", "está"],
            TipoInformacao.HISTORICO: ["histórico", "antes", "passado", "evolução"],
            TipoInformacao.COMPARACAO: ["vs", "versus", "diferença", "comparação"],
            TipoInformacao.DETALHAMENTO: ["detalhes", "completo", "informações"],
            TipoInformacao.PROBLEMAS: ["problema", "atraso", "erro", "falha"],
            TipoInformacao.METRICAS: ["performance", "indicador", "percentual"],
            TipoInformacao.PREVISAO: ["quando", "prazo", "estimativa", "previsão"],
            TipoInformacao.LOCALIZACAO: ["onde", "local", "endereço", "destino"]
        }
        
        return palavras_chave.get(intencao, [])
    
    def _analisar_nivel_detalhamento(self, consulta: str) -> NivelDetalhamento:
        """Analisa o nível de detalhamento desejado"""
        
        if any(palavra in consulta for palavra in ["resumo", "rápido", "sintético", "overview"]):
            return NivelDetalhamento.RESUMO
        elif any(palavra in consulta for palavra in ["completo", "detalhado", "tudo", "todas informações"]):
            return NivelDetalhamento.COMPLETO
        elif any(palavra in consulta for palavra in ["executivo", "gerencial", "direção", "gestão"]):
            return NivelDetalhamento.EXECUTIVO
        elif any(palavra in consulta for palavra in ["operacional", "técnico", "específico"]):
            return NivelDetalhamento.OPERACIONAL
        else:
            return NivelDetalhamento.COMPLETO  # Padrão
    
    def _avaliar_urgencia(self, consulta: str) -> UrgenciaConsulta:
        """Avalia a urgência da consulta"""
        
        for urgencia, palavras in self.contextos_urgencia.items():
            for palavra in palavras:
                if palavra in consulta:
                    return urgencia
        
        return UrgenciaConsulta.MEDIA  # Padrão
    
    def _extrair_entidades_negocio(self, consulta: str) -> Dict[str, List[str]]:
        """Extrai entidades de negócio da consulta com integração ao sistema de grupos empresariais"""
        
        entidades = {
            "clientes": [],
            "grupos_empresariais": [],
            "produtos": [],
            "localidades": [],
            "documentos": [],
            "status": [],
            "pessoas": [],
            "valores": []
        }
        
        # 🏢 INTEGRAÇÃO COM SISTEMA AVANÇADO DE GRUPOS EMPRESARIAIS
        try:
            from app.utils.grupo_empresarial import detectar_grupo_empresarial
            
            grupo_detectado = detectar_grupo_empresarial(consulta)
            
            if grupo_detectado:
                logger.info(f"🏢 GRUPO EMPRESARIAL DETECTADO VIA SISTEMA AVANÇADO: {grupo_detectado['grupo_detectado']}")
                
                entidades["grupos_empresariais"].append({
                    "nome": grupo_detectado['grupo_detectado'],
                    "tipo": grupo_detectado.get('tipo_negocio', 'grupo'),
                    "filtro_sql": grupo_detectado.get('filtro_sql', ''),
                    "metodo_deteccao": grupo_detectado.get('tipo_deteccao', 'nome'),
                    "keyword_encontrada": grupo_detectado.get('keyword_encontrada', ''),
                    "descricao": grupo_detectado.get('descricao', ''),
                    "cnpj_prefixos": grupo_detectado.get('cnpj_prefixos', [])
                })
                
                # Adicionar também como cliente individual para compatibilidade
                nome_grupo_simples = grupo_detectado.get('keyword_encontrada', '').title()
                if nome_grupo_simples:
                    entidades["clientes"].append(nome_grupo_simples)
                
                logger.info(f"✅ Grupo detectado: {nome_grupo_simples} | Método: {grupo_detectado.get('tipo_deteccao')}")
                
        except ImportError:
            logger.warning("⚠️ Sistema de grupos empresariais não disponível - usando detecção básica")
            
            # Fallback para detecção básica se sistema avançado não estiver disponível
            for cliente_oficial, variacoes in self.mapeamento_clientes.items():
                for variacao in variacoes:
                    if variacao in consulta:
                        entidades["clientes"].append(cliente_oficial)
                        break
        
        except Exception as e:
            logger.error(f"❌ Erro ao integrar sistema de grupos empresariais: {e}")
            # Fallback para detecção básica em caso de erro
            for cliente_oficial, variacoes in self.mapeamento_clientes.items():
                for variacao in variacoes:
                    if variacao in consulta:
                        entidades["clientes"].append(cliente_oficial)
                        break
        
        # Se não detectou grupo empresarial, usar mapeamento básico adicional
        if not entidades["grupos_empresariais"] and not entidades["clientes"]:
            for cliente_oficial, variacoes in self.mapeamento_clientes.items():
                for variacao in variacoes:
                    if variacao in consulta:
                        entidades["clientes"].append(cliente_oficial)
                        break
        
        # Extrair documentos (NFs, CTes, Pedidos)
        # NFs (começam com 1 e têm 6 dígitos)
        nfs = re.findall(r'1\d{5}', consulta)
        if nfs:
            entidades["documentos"].extend([f"NF {nf}" for nf in nfs])
        
        # Pedidos (números que podem ser pedidos)
        pedidos = re.findall(r'(?:pedido|pdd|num)\s*(\d+)', consulta)
        if pedidos:
            entidades["documentos"].extend([f"Pedido {p}" for p in pedidos])
        
        # Extrair localidades (UFs)
        ufs_br = ["SP", "RJ", "MG", "RS", "PR", "SC", "GO", "DF", "BA", "PE", "CE"]
        for uf in ufs_br:
            if re.search(rf'\b{uf}\b', consulta.upper()):
                entidades["localidades"].append(uf)
        
        # Extrair valores monetários
        valores = re.findall(r'R\$\s*[\d.,]+', consulta)
        if valores:
            entidades["valores"].extend(valores)
        
        # Extrair status operacionais
        for categoria, status_lista in self.termos_negocio["status_operacionais"].items():
            for status in status_lista:
                if status in consulta:
                    entidades["status"].append(status)
        
        logger.info(f"🔍 Entidades extraídas: {sum(len(v) for v in entidades.values())} encontradas")
        
        return entidades
    
    def _analisar_escopo_temporal(self, consulta: str) -> Dict[str, Any]:
        """Analisa o escopo temporal da consulta"""
        
        escopo = {
            "tipo": "padrao",
            "periodo_dias": 30,  # Padrão
            "data_inicio": None,
            "data_fim": None,
            "descricao": "Últimos 30 dias (padrão)"
        }
        
        # Verificar padrões absolutos
        for pattern, info in self.padroes_temporais["absolutos"].items():
            if isinstance(pattern, str):
                if pattern in consulta:
                    if info["tipo"] == "data_especifica":
                        data_ref = datetime.now() + timedelta(days=info["dias"])
                        escopo.update({
                            "tipo": "data_especifica",
                            "data_inicio": data_ref.date(),
                            "data_fim": data_ref.date(),
                            "periodo_dias": 1,
                            "descricao": f"Data específica: {pattern}"
                        })
                        break
        
        # Verificar padrões relativos
        for pattern, info in self.padroes_temporais["relativos"].items():
            if isinstance(pattern, str):
                if pattern in consulta:
                    escopo.update({
                        "tipo": "periodo_relativo",
                        "periodo_dias": abs(info["dias"]),
                        "descricao": pattern.title()
                    })
                    break
            else:
                # Padrão regex
                match = re.search(pattern, consulta)
                if match:
                    dias = int(match.group(1))
                    escopo.update({
                        "tipo": "periodo_personalizado",
                        "periodo_dias": dias,
                        "descricao": f"Últimos {dias} dias"
                    })
                    break
        
        # Verificar meses específicos
        for mes_nome, mes_num in self.padroes_temporais["meses"].items():
            if mes_nome in consulta:
                hoje = datetime.now()
                if hoje.month >= mes_num:
                    # Mês atual do ano
                    inicio_mes = datetime(hoje.year, mes_num, 1)
                    dias_mes = (hoje - inicio_mes).days + 1
                else:
                    # Mês do ano anterior
                    inicio_mes = datetime(hoje.year - 1, mes_num, 1)
                    dias_mes = 31  # Aproximação
                
                escopo.update({
                    "tipo": "mes_especifico",
                    "periodo_dias": min(dias_mes, 31),
                    "mes_especifico": mes_nome,
                    "descricao": f"Mês de {mes_nome.title()}"
                })
                break
        
        logger.info(f"📅 Escopo temporal: {escopo['descricao']} ({escopo['periodo_dias']} dias)")
        
        return escopo
    
    def _detectar_filtros_implicitos(self, consulta: str, entidades: Dict[str, List[str]]) -> Dict[str, Any]:
        """Detecta filtros implícitos na consulta"""
        
        filtros = {}
        
        # Filtros de cliente
        if entidades["clientes"]:
            filtros["cliente_especifico"] = entidades["clientes"][0]
        
        # Filtros geográficos
        if entidades["localidades"]:
            filtros["uf"] = entidades["localidades"][0]
        
        # Filtros de status
        if entidades["status"]:
            filtros["status"] = entidades["status"]
        
        # Filtros de tipo de consulta
        if any(palavra in consulta for palavra in ["urgente", "atrasado", "problema"]):
            filtros["prioridade"] = "alta"
        
        if any(palavra in consulta for palavra in ["pendente", "aguardando"]):
            filtros["status_pendente"] = True
        
        return filtros
    
    def _analisar_contexto_negocio(self, entidades: Dict[str, List[str]], intencao: TipoInformacao) -> Dict[str, Any]:
        """Analisa o contexto de negócio da consulta"""
        
        contexto = {
            "dominio_principal": "geral",
            "complexidade": "media",
            "areas_envolvidas": [],
            "nivel_acesso_necessario": "operacional"
        }
        
        # Determinar domínio baseado nas entidades
        if entidades["clientes"] or intencao == TipoInformacao.STATUS:
            contexto["dominio_principal"] = "entregas"
            contexto["areas_envolvidas"].append("operacional")
        
        if any("problema" in status for status in entidades["status"]):
            contexto["areas_envolvidas"].append("suporte")
            contexto["complexidade"] = "alta"
        
        if any(doc.startswith("NF") for doc in entidades["documentos"]):
            contexto["areas_envolvidas"].append("financeiro")
        
        # Determinar nível de acesso necessário
        if intencao in [TipoInformacao.METRICAS, TipoInformacao.COMPARACAO]:
            contexto["nivel_acesso_necessario"] = "gerencial"
        
        return contexto
    
    def _calcular_probabilidade_interpretacao(self, intencao: TipoInformacao, 
                                            entidades: Dict[str, List[str]], 
                                            escopo_temporal: Dict[str, Any]) -> float:
        """Calcula a probabilidade de que a interpretação está correta"""
        
        probabilidade = 0.5  # Base
        
        # Boost por entidades específicas encontradas
        total_entidades = sum(len(lista) for lista in entidades.values())
        probabilidade += min(total_entidades * 0.1, 0.3)
        
        # Boost por especificidade temporal
        if escopo_temporal["tipo"] != "padrao":
            probabilidade += 0.1
        
        # Boost por clareza da intenção
        if intencao != TipoInformacao.LISTAGEM:  # LISTAGEM é padrão/genérico
            probabilidade += 0.1
        
        # Penalidade por ambiguidade
        if entidades["clientes"] and len(entidades["clientes"]) > 1:
            probabilidade -= 0.1
        
        return min(max(probabilidade, 0.1), 1.0)
    
    def _buscar_consultas_similares(self, consulta: str) -> List[str]:
        """Busca consultas similares para sugerir"""
        
        consultas_exemplo = [
            "Entregas do Assai em SP",
            "Quantas entregas estão atrasadas?", 
            "Status das entregas de hoje",
            "Relatório de entregas de junho",
            "Pedidos pendentes de cotação",
            "Entregas urgentes do Atacadão",
            "Agendamentos confirmados da semana",
            "Problemas de entrega em SP"
        ]
        
        # Usar difflib para encontrar similares
        consulta_lower = consulta.lower()
        similares = difflib.get_close_matches(
            consulta_lower, 
            [ex.lower() for ex in consultas_exemplo], 
            n=3, 
            cutoff=0.3
        )
        
        # Retornar versões originais das similares encontradas
        resultado = []
        for similar in similares:
            for exemplo in consultas_exemplo:
                if exemplo.lower() == similar:
                    resultado.append(exemplo)
                    break
        
        return resultado
    
    def _gerar_sugestoes_esclarecimento(self, consulta: str, intencao: TipoInformacao, 
                                      entidades: Dict[str, List[str]], 
                                      probabilidade: float) -> List[str]:
        """Gera sugestões de esclarecimento quando necessário"""
        
        sugestoes = []
        
        # Se probabilidade baixa, sugerir esclarecimento
        if probabilidade < 0.7:
            sugestoes.append("Poderia ser mais específico sobre o que deseja saber?")
        
        # Se não encontrou clientes específicos mas menciona "cliente"
        if "cliente" in consulta and not entidades["clientes"]:
            sugestoes.append("Qual cliente específico você gostaria de consultar? (ex: Assai, Atacadão, Carrefour)")
        
        # Se não especificou período temporal
        if "período" in consulta or "tempo" in consulta:
            if not any(entidades.get(k) for k in ["datas", "periodo"]):
                sugestoes.append("Que período você gostaria de analisar? (ex: últimos 7 dias, junho, ontem)")
        
        # Se consulta muito genérica
        if len(consulta.split()) <= 2:
            sugestoes.append("Gostaria de mais detalhes sobre sua consulta para dar uma resposta mais precisa")
        
        # Sugestões baseadas na intenção
        if intencao == TipoInformacao.PROBLEMAS:
            sugestoes.append("Que tipo de problema você gostaria de investigar? (atrasos, entregas pendentes, etc.)")
        
        return sugestoes
    
    def _otimizar_prompt_claude(self, consulta_original: str, intencao: TipoInformacao,
                               entidades: Dict[str, List[str]], escopo_temporal: Dict[str, Any],
                               filtros: Dict[str, Any]) -> str:
        """Otimiza o prompt para enviar ao Claude"""
        
        # Base do prompt otimizado
        prompt = f"CONSULTA DO USUÁRIO: {consulta_original}\n\n"
        
        # Adicionar interpretação
        prompt += f"INTERPRETAÇÃO INTELIGENTE:\n"
        prompt += f"• Intenção detectada: {intencao.value.upper()}\n"
        prompt += f"• Escopo temporal: {escopo_temporal['descricao']}\n"
        
        # Adicionar entidades encontradas - CORREÇÃO para grupos empresariais
        entidades_encontradas = []
        for tipo, lista in entidades.items():
            if lista:
                # Tratar grupos empresariais de forma especial (são dicionários)
                if tipo == "grupos_empresariais":
                    nomes_grupos = []
                    for grupo in lista:
                        if isinstance(grupo, dict):
                            nomes_grupos.append(grupo.get('nome', str(grupo)))
                        else:
                            nomes_grupos.append(str(grupo))
                    if nomes_grupos:
                        entidades_encontradas.append(f"{tipo}: {', '.join(nomes_grupos)}")
                else:
                    # Para outros tipos, converter todos para string
                    lista_str = [str(item) for item in lista]
                    entidades_encontradas.append(f"{tipo}: {', '.join(lista_str)}")
        
        if entidades_encontradas:
            prompt += f"• Entidades identificadas: {' | '.join(entidades_encontradas)}\n"
        
        # Adicionar filtros
        if filtros:
            filtros_texto = ", ".join([f"{k}={v}" for k, v in filtros.items()])
            prompt += f"• Filtros aplicados: {filtros_texto}\n"
        
        # Instruções específicas por intenção
        instrucoes_especificas = {
            TipoInformacao.LISTAGEM: "Forneça uma lista organizada com os dados solicitados",
            TipoInformacao.QUANTIDADE: "Foque nos números e totais. Inclua percentuais quando relevante",
            TipoInformacao.STATUS: "Apresente a situação atual de forma clara e objetiva",
            TipoInformacao.PROBLEMAS: "Identifique problemas e sugira ações corretivas",
            TipoInformacao.METRICAS: "Inclua indicadores de performance e comparações",
            TipoInformacao.DETALHAMENTO: "Forneça informações completas e detalhadas"
        }
        
        instrucao = instrucoes_especificas.get(intencao, "Responda de forma completa e precisa")
        prompt += f"\nINSTRUÇÃO ESPECÍFICA: {instrucao}\n"
        
        return prompt

# Instância global
intelligent_analyzer = IntelligentQueryAnalyzer()

def get_intelligent_analyzer() -> IntelligentQueryAnalyzer:
    """Retorna instância do analisador inteligente"""
    return intelligent_analyzer 