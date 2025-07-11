#!/usr/bin/env python3
"""
IntentionAnalyzer - Análise especializada de intenções
Foco exclusivo em detectar a intenção do usuário
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class IntentionAnalyzer:
    """Analisador especializado em detectar intenções do usuário"""
    
    def __init__(self):
        self._historico_performance = []
        logger.info("🎯 IntentionAnalyzer inicializado")
    
    def analyze_intention(self, query: str) -> Dict[str, Any]:
        """Analisa a intenção principal do usuário na consulta"""
        
        # Detectar múltiplas intenções com scores
        intencoes = self._detectar_intencoes_multiplas(query)
        
        # Determinar intenção principal
        if intencoes:
            intencao_principal = max(intencoes.keys(), key=lambda k: intencoes[k])
            confianca = max(intencoes.values())
        else:
            intencao_principal = "analise_dados"
            confianca = 0.5
        
        # Detectar contexto e urgência
        contexto = self._analisar_contexto_intencao(query)
        urgencia = self._detectar_urgencia(query)
        
        # Determinar complexidade da intenção
        complexidade = self._calcular_complexidade_intencao(query, intencoes)
        
        resultado = {
            'intention': intencao_principal,
            'confidence': confianca,
            'all_intentions': intencoes,
            'context': contexto,
            'urgency': urgencia,
            'complexity': complexidade,
            'query_length': len(query.split()),
            'use_advanced': self._deve_usar_sistema_avancado(query, intencoes, contexto),
            'timestamp': datetime.now().isoformat()
        }
        
        # Salvar para análise de tendências
        self._salvar_performance(resultado)
        
        return resultado
    
    def _detectar_intencoes_multiplas(self, consulta: str) -> Dict[str, float]:
        """
        Detecta múltiplas intenções com scores de confiança refinados
        """
        consulta_lower = consulta.lower()
        
        intencoes_scores = {
            "buscar_dados": 0.0,
            "gerar_relatorio": 0.0,
            "resolver_problema": 0.0,
            "monitorar_status": 0.0,
            "analisar_performance": 0.0,
            "obter_informacao": 0.0
        }
        
        # Padrões de intenção com pesos otimizados
        padroes_intencao = {
            "buscar_dados": {
                "palavras": ["quantos", "qual", "quais", "lista", "listar", "mostrar", "ver", "buscar", "encontrar"],
                "frases": ["me mostra", "quero ver", "preciso saber"],
                "peso_base": 0.3,
                "peso_frase": 0.5
            },
            "gerar_relatorio": {
                "palavras": ["relatório", "excel", "planilha", "exportar", "gerar", "fazer", "criar"],
                "frases": ["gerar relatório", "exportar excel", "fazer planilha"],
                "peso_base": 0.4,
                "peso_frase": 0.7
            },
            "resolver_problema": {
                "palavras": ["erro", "problema", "não funciona", "falha", "bug", "corrigir", "resolver"],
                "frases": ["não está funcionando", "deu erro", "tem problema"],
                "peso_base": 0.5,
                "peso_frase": 0.8
            },
            "monitorar_status": {
                "palavras": ["status", "situação", "estado", "acompanhar", "monitorar", "verificar"],
                "frases": ["qual o status", "como está", "situação atual"],
                "peso_base": 0.3,
                "peso_frase": 0.6
            },
            "analisar_performance": {
                "palavras": ["análise", "performance", "eficiência", "comparar", "tendência", "evolução"],
                "frases": ["análise de", "como está a performance", "comparado com"],
                "peso_base": 0.4,
                "peso_frase": 0.7
            },
            "obter_informacao": {
                "palavras": ["como", "por que", "quando", "onde", "explique", "entender"],
                "frases": ["como funciona", "por que acontece", "me explica"],
                "peso_base": 0.2,
                "peso_frase": 0.4
            }
        }
        
        # Calcular scores
        for intencao, config in padroes_intencao.items():
            score = 0.0
            
            # Score por palavras individuais
            for palavra in config["palavras"]:
                if palavra in consulta_lower:
                    score += config["peso_base"]
            
            # Score por frases completas (mais confiável)
            for frase in config.get("frases", []):
                if frase in consulta_lower:
                    score += config["peso_frase"]
            
            intencoes_scores[intencao] = min(score, 1.0)  # Cap em 1.0
        
        # Normalizar apenas se houver scores > 0
        scores_positivos = {k: v for k, v in intencoes_scores.items() if v > 0}
        if scores_positivos:
            total = sum(scores_positivos.values())
            for intencao in scores_positivos:
                intencoes_scores[intencao] = scores_positivos[intencao] / total
        
        return intencoes_scores
    
    def _analisar_contexto_intencao(self, consulta: str) -> Dict[str, Any]:
        """Analisa contexto específico da intenção"""
        consulta_lower = consulta.lower()
        
        contexto = {
            'temporal': self._detectar_contexto_temporal(consulta_lower),
            'escopo': self._detectar_escopo(consulta_lower),
            'especificidade': self._detectar_especificidade(consulta_lower),
            'publico_alvo': self._detectar_publico_alvo(consulta_lower)
        }
        
        return contexto
    
    def _detectar_contexto_temporal(self, consulta: str) -> str:
        """Detecta contexto temporal da intenção"""
        if any(palavra in consulta for palavra in ['hoje', 'agora', 'atual', 'neste momento']):
            return 'imediato'
        elif any(palavra in consulta for palavra in ['ontem', 'semana passada', 'mês passado']):
            return 'historico'
        elif any(palavra in consulta for palavra in ['amanhã', 'próxima', 'futuro', 'vai']):
            return 'futuro'
        else:
            return 'geral'
    
    def _detectar_escopo(self, consulta: str) -> str:
        """Detecta escopo da consulta"""
        if any(palavra in consulta for palavra in ['todos', 'total', 'geral', 'completo']):
            return 'amplo'
        elif any(palavra in consulta for palavra in ['específico', 'particular', 'apenas', 'só']):
            return 'especifico'
        else:
            return 'medio'
    
    def _detectar_especificidade(self, consulta: str) -> str:
        """Detecta nível de especificidade"""
        # Contar entidades específicas (empresas, códigos, nomes)
        entidades_especificas = 0
        
        # Empresas conhecidas
        empresas = ['assai', 'atacadão', 'carrefour', 'tenda', 'mateus']
        entidades_especificas += sum(1 for emp in empresas if emp in consulta)
        
        # Códigos/números
        import re
        numeros = re.findall(r'\d+', consulta)
        entidades_especificas += len(numeros)
        
        if entidades_especificas >= 2:
            return 'muito_especifica'
        elif entidades_especificas == 1:
            return 'especifica'
        else:
            return 'generica'
    
    def _detectar_publico_alvo(self, consulta: str) -> str:
        """Detecta para quem é direcionada a consulta"""
        if any(palavra in consulta for palavra in ['gerência', 'diretoria', 'executivo']):
            return 'executivo'
        elif any(palavra in consulta for palavra in ['operação', 'operacional', 'dia a dia']):
            return 'operacional'
        else:
            return 'geral'
    
    def _detectar_urgencia(self, consulta: str) -> str:
        """Detecta nível de urgência da intenção"""
        consulta_lower = consulta.lower()
        
        # Indicadores de alta urgência
        alta_urgencia = ['urgente', 'emergência', 'imediato', 'agora', 'já', 'crítico', 'parado']
        if any(palavra in consulta_lower for palavra in alta_urgencia):
            return 'alta'
        
        # Indicadores de média urgência
        media_urgencia = ['hoje', 'rápido', 'logo', 'breve', 'preciso']
        if any(palavra in consulta_lower for palavra in media_urgencia):
            return 'media'
        
        return 'baixa'
    
    def _calcular_complexidade_intencao(self, consulta: str, intencoes: Dict[str, float]) -> str:
        """Calcula complexidade da intenção detectada"""
        
        # Fatores de complexidade
        fatores_complexidade = [
            len(consulta.split()) > 15,  # Consulta longa
            len([i for i in intencoes.values() if i > 0.2]) > 1,  # Múltiplas intenções
            max(intencoes.values()) < 0.6 if intencoes else False,  # Intenção ambígua
            any(palavra in consulta.lower() for palavra in ['análise', 'comparação', 'tendência']),  # Requer análise
            any(palavra in consulta.lower() for palavra in ['e', 'ou', 'mas', 'além']),  # Múltiplas condições
        ]
        
        pontos_complexidade = sum(fatores_complexidade)
        
        if pontos_complexidade >= 3:
            return 'alta'
        elif pontos_complexidade >= 2:
            return 'media'
        else:
            return 'baixa'
    
    def _deve_usar_sistema_avancado(self, consulta: str, intencoes: Dict[str, float], contexto: Dict[str, Any]) -> bool:
        """
        Decide se deve usar sistema avançado baseado na intenção detectada
        """
        # Critérios para sistema avançado
        criterios = {
            "intencao_complexa": max(intencoes.values()) < 0.6 if intencoes else False,
            "multiplas_intencoes": len([i for i in intencoes.values() if i > 0.2]) > 1,
            "escopo_amplo": contexto.get('escopo') == 'amplo',
            "analise_requerida": any(palavra in consulta.lower() for palavra in ['análise', 'comparação', 'tendência']),
            "publico_executivo": contexto.get('publico_alvo') == 'executivo',
            "consulta_longa": len(consulta.split()) > 20
        }
        
        # Log para debug
        logger.debug(f"🔍 Critérios sistema avançado: {criterios}")
        
        # Decisão baseada em múltiplos fatores
        pontos = sum(1 for criterio, valor in criterios.items() if valor)
        usar_avancado = pontos >= 2
        
        if usar_avancado:
            logger.info(f"🚀 Sistema avançado recomendado: {pontos} critérios atendidos")
        
        return usar_avancado
    
    def _salvar_performance(self, resultado: Dict[str, Any]) -> None:
        """Salva resultado para análise de performance"""
        self._historico_performance.append({
            'timestamp': resultado['timestamp'],
            'intention': resultado['intention'],
            'confidence': resultado['confidence'],
            'complexity': resultado['complexity'],
            'use_advanced': resultado['use_advanced']
        })
        
        # Manter apenas últimos 100 registros
        if len(self._historico_performance) > 100:
            self._historico_performance = self._historico_performance[-100:]
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas de performance do analyzer"""
        if not self._historico_performance:
            return {'message': 'Nenhum dado de performance disponível'}
        
        # Calcular estatísticas
        intencoes_count = {}
        confiancas = []
        uso_avancado = 0
        
        for registro in self._historico_performance:
            intencao = registro['intention']
            intencoes_count[intencao] = intencoes_count.get(intencao, 0) + 1
            confiancas.append(registro['confidence'])
            if registro['use_advanced']:
                uso_avancado += 1
        
        return {
            'total_analises': len(self._historico_performance),
            'intencao_mais_comum': max(intencoes_count.keys(), key=lambda k: intencoes_count[k]),
            'confianca_media': sum(confiancas) / len(confiancas),
            'percentual_sistema_avancado': (uso_avancado / len(self._historico_performance)) * 100,
            'distribuicao_intencoes': intencoes_count
        }

# Instância global
_intentionanalyzer = None

def get_intentionanalyzer():
    """Retorna instância de IntentionAnalyzer"""
    global _intentionanalyzer
    if _intentionanalyzer is None:
        _intentionanalyzer = IntentionAnalyzer()
    return _intentionanalyzer

# Alias para compatibilidade
def get_intention_analyzer():
    """Retorna instância de IntentionAnalyzer (alias para compatibilidade)"""
    return get_intentionanalyzer()

# Exportações
__all__ = [
    'IntentionAnalyzer',
    'get_intentionanalyzer', 
    'get_intention_analyzer'
]