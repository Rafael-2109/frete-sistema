#!/usr/bin/env python3
"""
🚀 INTEGRAÇÃO CLAUDE MELHORADA - Entendimento Inteligente do Usuário
Combina Claude 4 Sonnet com análise inteligente de consultas para respostas mais precisas
"""

import os
import anthropic
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

import logging
from .intelligent_query_analyzer import get_intelligent_analyzer, TipoInformacao, UrgenciaConsulta
# # from .claude_real_integration import ClaudeRealIntegration  # Removido para evitar circular import  # Removido para evitar import circular
from .sistema_real_data import get_sistema_real_data

logger = logging.getLogger(__name__)

class EnhancedClaudeIntegration:
    """
    🚀 Integração Claude Melhorada com Entendimento Inteligente
    
    Funcionalidades:
    - Análise inteligente de consultas antes de enviar ao Claude
    - Otimização automática de prompts
    - Detecção de ambiguidades e sugestões de esclarecimento
    - Contextualização inteligente baseada na intenção
    - Respostas mais precisas e coerentes
    """
    
    def __init__(self):
        """Inicializa a integração Claude melhorada"""
        # Import lazy para evitar circular import
        try:
            # Import dentro do método para evitar circular import
            from .claude_real_integration import ClaudeRealIntegration
            self.claude_integration = ClaudeRealIntegration()
        except ImportError as e:
            logger.warning(f"⚠️ ClaudeRealIntegration não disponível: {e}")
            self.claude_integration = None
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar ClaudeRealIntegration: {e}")
            self.claude_integration = None
        
        self.intelligent_analyzer = get_intelligent_analyzer()
        self.sistema_data = get_sistema_real_data()
        
        logger.info("🚀 Integração Claude Melhorada inicializada com IA de entendimento")
    
    def processar_consulta_inteligente(self, consulta: str, user_context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Processa consulta com análise inteligente ANTES de enviar ao Claude
        
        Args:
            consulta: Consulta em linguagem natural
            user_context: Contexto do usuário
            
        Returns:
            Resposta completa com análise + resposta Claude
        """
        
        logger.info(f"🚀 Processando consulta inteligente: '{consulta[:500]}...'")
        
        # 1. ANÁLISE INTELIGENTE DA CONSULTA
        interpretacao = self.intelligent_analyzer.analisar_consulta_inteligente(
            consulta, user_context or {}
        )
        
        # 2. VERIFICAR SE PRECISA DE ESCLARECIMENTO
        if interpretacao.probabilidade_interpretacao < 0.5 and interpretacao.sugestoes_esclarecimento:
            return self._gerar_resposta_esclarecimento(interpretacao)
        
        # 3. VERIFICAR URGÊNCIA CRÍTICA
        if interpretacao.urgencia == UrgenciaConsulta.CRITICA:
            return self._processar_consulta_critica(interpretacao, user_context)
        
        # 4. OTIMIZAR CONTEXTO BASEADO NA INTERPRETAÇÃO
        contexto_otimizado = self._otimizar_contexto_baseado_interpretacao(
            interpretacao, user_context
        )
        
        # 5. PROCESSAR COM CLAUDE USANDO PROMPT OTIMIZADO
        if self.claude_integration:
            resposta_claude = self.claude_integration.processar_consulta_real(
                interpretacao.prompt_otimizado, contexto_otimizado
            )
        else:
            # Fallback quando Claude não está disponível
            logger.warning("⚠️ Claude Integration não disponível, usando resposta padrão")
            resposta_claude = "⚠️ Sistema Claude temporariamente indisponível. Por favor, tente novamente em alguns instantes."
        
        # 6. PÓS-PROCESSAMENTO DA RESPOSTA
        resposta_final = self._pos_processar_resposta(
            resposta_claude, interpretacao
        )
        
        # 7. RETORNAR RESULTADO COMPLETO
        return {
            "resposta": resposta_final,
            "interpretacao": {
                "intencao": interpretacao.intencao_principal.value,
                "urgencia": interpretacao.urgencia.value,
                "entidades": interpretacao.entidades_detectadas,
                "confianca": interpretacao.probabilidade_interpretacao,
                "escopo_temporal": interpretacao.escopo_temporal
            },
            "metadados": {
                "processamento_inteligente": True,
                "tempo_processamento": datetime.now().isoformat(),
                "consultas_similares": interpretacao.consultas_similares
            }
        }
    
    def process_enhanced_query(self, consulta: str, contexto: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa consulta com análise inteligente e otimização
        
        Args:
            consulta: Consulta em linguagem natural
            contexto: Contexto enriquecido com dados
            
        Returns:
            Dict com resposta e metadados
        """
        
        logger.info(f"🚀 Processing enhanced query: '{consulta[:100]}...'")
        
        # 🚨 PROTEÇÃO ANTI-LOOP: Detectar se já estamos em processamento
        if contexto.get('_from_claude_real'):
            logger.warning("⚠️ Detectado possível loop - retornando resposta direta")
            
            # Retornar resposta inteligente baseada no contexto
            dados = contexto.get('dados_carregados', {})
            cliente = contexto.get('cliente_especifico', '')
            
            if 'entregas' in consulta.lower() or 'entrega' in consulta.lower():
                entregas = dados.get('entregas', [])
                total_entregas = len(entregas)
                if cliente and 'atacadão' in cliente.lower():
                    return {
                        'success': True,
                        'response': f"📦 Encontrei {total_entregas} entregas do Atacadão no período consultado.\n\n"
                                   f"Para mais detalhes, você pode perguntar sobre:\n"
                                   f"- Status específico das entregas\n"
                                   f"- Entregas atrasadas ou pendentes\n"
                                   f"- Relatório detalhado por período",
                        'metadata': {'source': 'anti_loop_protection', 'total': total_entregas}
                    }
                else:
                    return {
                        'success': True,
                        'response': f"📊 Análise de entregas: {total_entregas} registros encontrados.\n\n"
                                   f"Posso ajudar com informações mais específicas sobre:\n"
                                   f"- Entregas por cliente\n"
                                   f"- Status de entrega\n"
                                   f"- Prazos e atrasos",
                        'metadata': {'source': 'anti_loop_protection', 'total': total_entregas}
                    }
            
            # Resposta genérica se não for sobre entregas
            return {
                'success': True,
                'response': "Processando sua consulta com os dados disponíveis. "
                           "Por favor, seja mais específico sobre o que deseja saber.",
                'metadata': {'source': 'anti_loop_protection'}
            }
        
        # Análise inteligente da consulta
        interpretacao = self.intelligent_analyzer.analisar_consulta_inteligente(
            consulta, contexto.get('user_context', {})
        )
        
        # Se confiança baixa, retornar sugestão de esclarecimento
        if interpretacao.probabilidade_interpretacao < 0.5:
            return {
                'success': True,
                'response': self._gerar_texto_esclarecimento(interpretacao),
                'metadata': {
                    'requer_esclarecimento': True,
                    'confianca': interpretacao.probabilidade_interpretacao
                }
            }
        
        # 🚨 IMPORTANTE: NÃO chamar claude_integration aqui para evitar loop!
        # Usar os dados já fornecidos no contexto
        
        dados_carregados = contexto.get('dados_carregados', {})
        tipo_consulta = contexto.get('tipo_consulta', 'geral')
        cliente_especifico = contexto.get('cliente_especifico', '')
        
        # Gerar resposta baseada nos dados fornecidos
        resposta = self._gerar_resposta_inteligente(
            interpretacao,
            dados_carregados,
            tipo_consulta,
            cliente_especifico
        )
        
        return {
            'success': True,
            'response': resposta,
            'metadata': {
                'interpretacao': interpretacao.to_dict(),
                'enhanced': True,
                'source': 'enhanced_claude_no_loop'
            }
        }
    
    def _gerar_resposta_inteligente(self, interpretacao, dados, tipo_consulta, cliente):
        """Gera resposta inteligente baseada nos dados sem chamar Claude novamente"""
        
        # Implementar lógica de geração de resposta baseada nos dados
        if tipo_consulta == 'entregas':
            entregas = dados.get('entregas', [])
            total = len(entregas)
            
            if cliente:
                return f"📦 Análise de entregas para {cliente}:\n\n" \
                       f"Total de entregas: {total}\n" \
                       f"Período analisado: {dados.get('periodo', 'últimos 30 dias')}\n\n" \
                       f"Detalhes disponíveis mediante consulta específica."
            else:
                return f"📊 Resumo geral de entregas:\n\n" \
                       f"Total no sistema: {total} entregas\n" \
                       f"Use filtros específicos para análise detalhada."
        
        # Resposta genérica para outros tipos
        return "Dados processados com sucesso. Por favor, faça uma pergunta mais específica."
    
    def _gerar_resposta_esclarecimento(self, interpretacao) -> Dict[str, Any]:
        """Gera resposta solicitando esclarecimento quando necessário"""
        
        logger.info(f"❓ Gerando resposta de esclarecimento (confiança: {interpretacao.probabilidade_interpretacao:.2f})")
        
        resposta = "🤔 **Preciso de um esclarecimento para te ajudar melhor:**\n\n"
        
        # Mostrar o que foi entendido
        resposta += f"**O que entendi:**\n"
        resposta += f"• Tipo de consulta: {interpretacao.intencao_principal.value.title()}\n"
        
        if interpretacao.entidades_detectadas["clientes"]:
            resposta += f"• Cliente(s): {', '.join(interpretacao.entidades_detectadas['clientes'])}\n"
        
        if interpretacao.entidades_detectadas["localidades"]:
            resposta += f"• Local: {', '.join(interpretacao.entidades_detectadas['localidades'])}\n"
        
        resposta += f"• Período: {interpretacao.escopo_temporal['descricao']}\n\n"
        
        # Adicionar sugestões específicas
        if interpretacao.sugestoes_esclarecimento:
            resposta += "**Para uma resposta mais precisa:**\n"
            for sugestao in interpretacao.sugestoes_esclarecimento:
                resposta += f"• {sugestao}\n"
            resposta += "\n"
        
        # Sugerir consultas similares
        if interpretacao.consultas_similares:
            resposta += "**Exemplos de consultas semelhantes:**\n"
            for exemplo in interpretacao.consultas_similares:
                resposta += f"• \"{exemplo}\"\n"
        
        resposta += "\n💡 **Reformule sua pergunta com mais detalhes e eu terei uma resposta precisa para você!**"
        
        return {
            "resposta": resposta,
            "interpretacao": {
                "status": "esclarecimento_necessario",
                "confianca": interpretacao.probabilidade_interpretacao,
                "sugestoes": interpretacao.sugestoes_esclarecimento
            },
            "metadados": {
                "requer_esclarecimento": True,
                "consultas_similares": interpretacao.consultas_similares
            }
        }
    
    def _processar_consulta_critica(self, interpretacao, user_context: Optional[Dict] = None) -> Dict[str, Any]:
        """Processa consultas críticas com prioridade máxima"""
        
        logger.warning(f"🚨 Processando consulta CRÍTICA: {interpretacao.consulta_original}")
        
        # Prompt especializado para emergências
        prompt_critico = f"""
🚨 CONSULTA CRÍTICA DETECTADA 🚨

CONSULTA DO USUÁRIO: {interpretacao.consulta_original}
URGÊNCIA: MÁXIMA
INTENÇÃO: {interpretacao.intencao_principal.value.upper()}

INSTRUÇÕES ESPECIAIS:
1. Esta é uma consulta de EMERGÊNCIA que requer ação imediata
2. Priorize informações que ajudem a resolver o problema AGORA
3. Se há atrasos ou problemas, liste ações corretivas específicas
4. Inclua contatos/responsáveis se necessário
5. Forneça timeline de resolução se possível

Responda de forma DIRETA e ACIONÁVEL:
"""
        
        if self.claude_integration:
            resposta_claude = self.claude_integration.processar_consulta_real(
                prompt_critico, user_context
            )
        else:
            # Fallback para consultas críticas quando Claude não está disponível
            logger.error("❌ CRÍTICO: Claude Integration não disponível para consulta urgente")
            resposta_claude = "🚨 **ATENÇÃO**: Sistema Claude temporariamente indisponível para consulta crítica. Entre em contato com o suporte imediatamente."
        
        # Adicionar indicadores visuais de urgência
        resposta_final = f"🚨 **RESPOSTA PRIORITÁRIA - URGÊNCIA CRÍTICA** 🚨\n\n{resposta_claude}"
        
        return {
            "resposta": resposta_final,
            "interpretacao": {
                "status": "critica",
                "urgencia": "maxima",
                "requer_acao_imediata": True
            },
            "metadados": {
                "processamento_critico": True,
                "timestamp_urgencia": datetime.now().isoformat()
            }
        }
    
    def _otimizar_contexto_baseado_interpretacao(self, interpretacao, user_context: Optional[Dict] = None) -> Dict[str, Any]:
        """Otimiza o contexto baseado na interpretação inteligente"""
        
        contexto_otimizado = user_context.copy() if user_context else {}
        
        # Ajustar período baseado na interpretação temporal
        if interpretacao.escopo_temporal["tipo"] != "padrao":
            contexto_otimizado["periodo_dias_override"] = interpretacao.escopo_temporal["periodo_dias"]
        
        # 🏢 INTEGRAÇÃO GRUPOS EMPRESARIAIS - Aplicar filtros inteligentes
        if interpretacao.entidades_detectadas.get("grupos_empresariais"):
            for grupo in interpretacao.entidades_detectadas["grupos_empresariais"]:
                logger.info(f"🏢 Aplicando filtro de grupo empresarial: {grupo['nome']}")
                
                # Usar filtro SQL específico do grupo detectado
                if grupo.get("filtro_sql"):
                    contexto_otimizado["filtro_cliente_sql"] = grupo["filtro_sql"]
                
                # Adicionar informações do grupo ao contexto para Claude
                contexto_otimizado["grupo_empresarial_detectado"] = {
                    "nome": grupo["nome"],
                    "tipo": grupo["tipo"],
                    "metodo_deteccao": grupo["metodo_deteccao"],
                    "descricao": grupo["descricao"]
                }
                
                # Se tem CNPJs específicos, adicionar ao contexto
                if grupo.get("cnpj_prefixos"):
                    contexto_otimizado["cnpj_prefixos_grupo"] = grupo["cnpj_prefixos"]
        
        # Aplicar outros filtros detectados
        for filtro, valor in interpretacao.filtros_implicitios.items():
            contexto_otimizado[f"filtro_{filtro}"] = valor
        
        # Adicionar metadados de interpretação
        contexto_otimizado["interpretacao_meta"] = {
            "intencao": interpretacao.intencao_principal.value,
            "detalhamento": interpretacao.tipo_detalhamento.value,
            "entidades_detectadas": interpretacao.entidades_detectadas
        }
        
        logger.info(f"🔧 Contexto otimizado baseado em interpretação inteligente")
        
        return contexto_otimizado
    
    def _pos_processar_resposta(self, resposta_claude: str, interpretacao) -> str:
        """Pós-processa a resposta do Claude baseado na interpretação"""
        
        resposta_processada = resposta_claude
        
        # Adicionar contexto de interpretação no cabeçalho
        cabecalho_interpretacao = self._gerar_cabecalho_interpretacao(interpretacao)
        
        # Se resposta não contém o cabeçalho Claude, adicionar nosso contexto
        if "🤖 **CLAUDE" not in resposta_processada:
            resposta_processada = f"{cabecalho_interpretacao}\n\n{resposta_processada}"
        else:
            # Inserir contexto antes do rodapé do Claude
            partes = resposta_processada.split("---")
            if len(partes) >= 2:
                resposta_processada = f"{partes[0]}\n{cabecalho_interpretacao}\n\n---{partes[1]}"
        
        # Adicionar sugestões de consultas relacionadas se relevante
        if interpretacao.consultas_similares and interpretacao.intencao_principal == TipoInformacao.LISTAGEM:
            sugestoes_texto = "\n\n💡 **Consultas relacionadas que você pode fazer:**\n"
            for sugestao in interpretacao.consultas_similares[:3]:
                sugestoes_texto += f"• \"{sugestao}\"\n"
            resposta_processada += sugestoes_texto
        
        return resposta_processada
    
    def _gerar_cabecalho_interpretacao(self, interpretacao) -> str:
        """Gera cabeçalho explicando a interpretação"""
        
        cabecalho = "🧠 **INTERPRETAÇÃO INTELIGENTE:**\n"
        
        # Mostrar intenção detectada
        icones_intencao = {
            TipoInformacao.LISTAGEM: "📋",
            TipoInformacao.QUANTIDADE: "🔢",
            TipoInformacao.VALOR: "💰",
            TipoInformacao.STATUS: "📊",
            TipoInformacao.HISTORICO: "📈",
            TipoInformacao.PROBLEMAS: "⚠️",
            TipoInformacao.METRICAS: "📊",
            TipoInformacao.DETALHAMENTO: "🔍"
        }
        
        icone = icones_intencao.get(interpretacao.intencao_principal, "💭")
        cabecalho += f"{icone} Consulta interpretada como: **{interpretacao.intencao_principal.value.title()}**\n"
        
        # Mostrar escopo temporal se específico
        if interpretacao.escopo_temporal["tipo"] != "padrao":
            cabecalho += f"📅 Período analisado: **{interpretacao.escopo_temporal['descricao']}**\n"
        
        # 🏢 Mostrar grupos empresariais detectados com prioridade
        if interpretacao.entidades_detectadas.get("grupos_empresariais"):
            for grupo in interpretacao.entidades_detectadas["grupos_empresariais"]:
                cabecalho += f"🏢 **GRUPO EMPRESARIAL DETECTADO:** {grupo['nome']}\n"
                cabecalho += f"📊 Tipo: {grupo['tipo'].title()} | Método: {grupo['metodo_deteccao']}\n"
        
        # Mostrar clientes individuais se não há grupos
        elif interpretacao.entidades_detectadas.get("clientes"):
            cabecalho += f"🏢 Cliente(s): **{', '.join(interpretacao.entidades_detectadas['clientes'])}**\n"
        
        if interpretacao.entidades_detectadas.get("localidades"):
            cabecalho += f"🗺️ Local: **{', '.join(interpretacao.entidades_detectadas['localidades'])}**\n"
        
        # Indicador de confiança
        if interpretacao.probabilidade_interpretacao >= 0.8:
            cabecalho += f"✅ Confiança da interpretação: **Alta** ({interpretacao.probabilidade_interpretacao:.0%})"
        elif interpretacao.probabilidade_interpretacao >= 0.6:
            cabecalho += f"⚠️ Confiança da interpretação: **Média** ({interpretacao.probabilidade_interpretacao:.0%})"
        else:
            cabecalho += f"❓ Confiança da interpretação: **Baixa** ({interpretacao.probabilidade_interpretacao:.0%})"
        
        return cabecalho
    
    def validar_resposta_coerencia(self, consulta_original: str, resposta: str, interpretacao) -> Dict[str, Any]:
        """Valida se a resposta está coerente com a consulta original"""
        
        # Análise de coerência básica
        coerencia = {
            "score": 0.8,  # Padrão
            "problemas": [],
            "sugestoes": []
        }
        
        # Verificar se resposta aborda a intenção principal
        intenção_keywords = {
            TipoInformacao.QUANTIDADE: ["total", "quantos", "quantidade", "número"],
            TipoInformacao.STATUS: ["situação", "status", "está", "estado"],
            TipoInformacao.LISTAGEM: ["lista", "são", "seguintes"],
            TipoInformacao.PROBLEMAS: ["problema", "atraso", "pendente", "erro"]
        }
        
        keywords_esperadas = intenção_keywords.get(interpretacao.intencao_principal, [])
        keywords_encontradas = sum(1 for kw in keywords_esperadas if kw.lower() in resposta.lower())
        
        if keywords_encontradas == 0 and keywords_esperadas:
            coerencia["problemas"].append("Resposta pode não estar abordando o tipo de informação solicitado")
            coerencia["score"] -= 0.2
        
        # Verificar se entidades mencionadas estão na resposta
        for cliente in interpretacao.entidades_detectadas.get("clientes", []):
            if cliente.lower() not in resposta.lower():
                coerencia["problemas"].append(f"Cliente '{cliente}' mencionado na consulta não aparece na resposta")
                coerencia["score"] -= 0.1
        
        # Sugestões de melhoria
        if coerencia["score"] < 0.7:
            coerencia["sugestoes"].append("Considere reformular a consulta para ser mais específica")
        
        return coerencia

# Instância global
enhanced_claude_integration = EnhancedClaudeIntegration()

def processar_consulta_com_ia_avancada(consulta: str, user_context: Optional[Dict] = None) -> str:
    """
    Função principal para processar consultas com IA avançada
    
    Args:
        consulta: Consulta em linguagem natural
        user_context: Contexto do usuário
        
    Returns:
        Resposta processada com IA avançada
    """
    
    resultado = enhanced_claude_integration.processar_consulta_inteligente(consulta, user_context)
    
    # Se requer esclarecimento, retornar resposta de esclarecimento
    if resultado.get("metadados", {}).get("requer_esclarecimento"):
        return resultado["resposta"]
    
    # Senão, retornar resposta processada normalmente
    return resultado["resposta"]

# FUNÇÃO GET_ ÓRFÃ CRÍTICA - ESTAVA FALTANDO!
def get_enhanced_claude_system(claude_client=None) -> EnhancedClaudeIntegration:
    """Retorna instância do sistema Enhanced Claude - FUNÇÃO ÓRFÃ RECUPERADA"""
    return enhanced_claude_integration 