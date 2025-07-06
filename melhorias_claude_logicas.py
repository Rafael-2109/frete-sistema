#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MELHORIAS ESPECÍFICAS PARA CLAUDE_REAL_INTEGRATION.PY
Abordagem lógica e implementável
"""

from typing import Dict

# MELHORIA 1: Detecção de Intenção Refinada
def _detectar_intencao_melhorada(self, consulta: str) -> Dict[str, float]:
    """
    Detecta múltiplas intenções com scores de confiança
    Retorna dict com probabilidades ao invés de categoria única
    """
    consulta_lower = consulta.lower()
    
    intencoes_scores = {
        "analise_dados": 0.0,
        "desenvolvimento": 0.0,
        "resolucao_problema": 0.0,
        "explicacao_conceitual": 0.0,
        "comando_acao": 0.0
    }
    
    # Palavras-chave com pesos
    padroes = {
        "analise_dados": {
            "palavras": ["quantos", "qual", "status", "relatório", "dados", "estatística"],
            "peso": 0.2
        },
        "desenvolvimento": {
            "palavras": ["criar", "desenvolver", "implementar", "código", "função", "módulo"],
            "peso": 0.25
        },
        "resolucao_problema": {
            "palavras": ["erro", "bug", "problema", "não funciona", "corrigir"],
            "peso": 0.3
        },
        "explicacao_conceitual": {
            "palavras": ["como funciona", "o que é", "explique", "entender"],
            "peso": 0.15
        },
        "comando_acao": {
            "palavras": ["gerar", "exportar", "executar", "fazer", "processar"],
            "peso": 0.2
        }
    }
    
    # Calcular scores
    for intencao, config in padroes.items():
        for palavra in config["palavras"]:
            if palavra in consulta_lower:
                intencoes_scores[intencao] += config["peso"]
    
    # Normalizar scores
    total = sum(intencoes_scores.values())
    if total > 0:
        for intencao in intencoes_scores:
            intencoes_scores[intencao] /= total
    
    return intencoes_scores


# MELHORIA 2: Contexto Dinâmico Baseado em Intenção
def _build_contexto_por_intencao(self, intencoes_scores: Dict[str, float], 
                                  dados_contexto: Dict) -> str:
    """
    Constrói contexto específico baseado na intenção dominante
    """
    # Encontrar intenção dominante
    intencao_principal = max(intencoes_scores, key=lambda k: intencoes_scores[k])
    score_principal = intencoes_scores[intencao_principal]
    
    # Se confiança baixa, usar contexto genérico
    if score_principal < 0.4:
        return self._descrever_contexto_carregado(dados_contexto)
    
    # Contextos específicos por intenção
    if intencao_principal == "desenvolvimento":
        return """Contexto: Desenvolvimento Flask/PostgreSQL
Estrutura: app/[modulo]/{models,routes,forms}.py
Padrões: SQLAlchemy models, WTForms, Jinja2 templates"""
    
    elif intencao_principal == "analise_dados":
        periodo = dados_contexto.get('periodo_dias', 30)
        registros = dados_contexto.get('registros_carregados', 0)
        return f"Dados: {registros} registros, {periodo} dias"
    
    elif intencao_principal == "resolucao_problema":
        return "Contexto: Diagnóstico e resolução de problemas"
    
    else:
        return self._descrever_contexto_carregado(dados_contexto)


# MELHORIA 3: Reduzir Templates Hardcoded
def _gerar_resposta_dinamica(self, tipo_resposta: str, dados: Dict) -> str:
    """
    Gera respostas dinamicamente ao invés de usar templates fixos
    Permite que Claude construa a resposta naturalmente
    """
    # Ao invés de:
    # return f"🤖 **CLAUDE 4 SONNET REAL**\n\n📅 **ENTREGAS COM AGENDAMENTO**..."
    
    # Fazer:
    contexto_resposta = {
        "tipo": tipo_resposta,
        "dados_principais": dados,
        "formato_sugerido": "markdown",
        "incluir_rodape": True
    }
    
    # Deixar Claude formatar baseado no contexto
    return self._processar_com_claude(
        prompt=f"Apresente estes dados de {tipo_resposta}",
        contexto=contexto_resposta
    )


# MELHORIA 4: Sistema de Priorização de Processamento
def _deve_usar_sistema_avancado(self, consulta: str, intencoes: Dict[str, float]) -> bool:
    """
    Decide logicamente se deve usar sistemas avançados
    Baseado em critérios objetivos, não apenas palavras-chave
    """
    # Critérios lógicos
    criterios = {
        "complexidade_alta": len(consulta.split()) > 20,
        "multiplas_intencoes": sum(1 for s in intencoes.values() if s > 0.2) >= 2,
        "solicitacao_explicita": any(termo in consulta.lower() for termo in 
                                   ["análise avançada", "análise profunda"]),
        "historico_insatisfatorio": self._verificar_historico_feedback(),
        "carga_sistema_baixa": self._verificar_carga_sistema() < 0.7
    }
    
    # Decisão baseada em múltiplos fatores
    pontos = sum(1 for criterio, valor in criterios.items() if valor)
    return pontos >= 2  # Precisa de pelo menos 2 critérios verdadeiros


# EXEMPLO DE USO INTEGRADO
def processar_consulta_melhorado(self, consulta: str, user_context: Dict) -> str:
    """
    Processamento com melhorias aplicadas
    """
    # 1. Detectar intenções (múltiplas com scores)
    intencoes = self._detectar_intencao_melhorada(consulta)
    
    # 2. Decidir se usa sistemas avançados
    usar_avancado = self._deve_usar_sistema_avancado(consulta, intencoes)
    
    # 3. Carregar dados de contexto (seria feito por _carregar_contexto_inteligente)
    dados_contexto = self._carregar_contexto_inteligente({"periodo_dias": 30})
    
    # 4. Construir contexto específico
    contexto = self._build_contexto_por_intencao(intencoes, dados_contexto)
    
    # 5. Processar com abordagem adequada
    if usar_avancado:
        return self._processar_avancado(consulta, contexto)
    else:
        return self._processar_simples(consulta, contexto) 