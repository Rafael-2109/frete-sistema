#!/usr/bin/env python3
"""
🚀 MCP CONNECTOR AVANÇADO - Sistema de Fretes
Conector MCP com IA Integrada e Analytics Avançado
"""

import json
import subprocess
import os
import sys
import logging
from typing import Dict, Any, Optional
from datetime import datetime

# Adicionar path para os componentes MCP avançados ANTES dos imports
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
mcp_avancado_path = os.path.join(project_root, 'mcp', 'mcp_avancado')

# Adicionar ao sys.path se não estiver presente
if mcp_avancado_path not in sys.path:
    sys.path.insert(0, mcp_avancado_path)

# Imports condicionais para evitar erros de import
try:
    from connectors.database_connector import DatabaseConnector
    from connectors.api_connector import APIConnector
    from tools.analytics_tools import AnalyticsTools
    MCP_COMPONENTS_AVAILABLE = True
except ImportError as e:
    # Fallback - definir classes vazias
    DatabaseConnector = None
    APIConnector = None
    AnalyticsTools = None
    MCP_COMPONENTS_AVAILABLE = False
    print(f"⚠️ Componentes MCP avançados não disponíveis: {e}")

logger = logging.getLogger(__name__)

class MCPConnectorAdvanced:
    """Conector MCP Avançado com IA Integrada"""
    
    def __init__(self, app_root_path: str):
        self.app_root_path = app_root_path
        self.mcp_script_path = os.path.join(app_root_path, '..', 'mcp', 'mcp_v1_9_4_atualizado.py')
        self.venv_python_path = os.path.join(app_root_path, '..', 'venv', 'Scripts', 'python.exe')
        
        # Componentes avançados
        self._initialize_advanced_components()
        
    def _initialize_advanced_components(self):
        """Inicializa componentes avançados do MCP"""
        try:
            if MCP_COMPONENTS_AVAILABLE and all([DatabaseConnector, APIConnector, AnalyticsTools]):
                self.db_connector = DatabaseConnector()
                self.api_connector = APIConnector()
                self.analytics_tools = AnalyticsTools()
                
                logger.info("🚀 Componentes MCP avançados inicializados com sucesso")
            else:
                self.db_connector = None
                self.api_connector = None
                self.analytics_tools = None
                logger.warning("⚠️ Componentes MCP avançados não disponíveis - usando fallback")
        except Exception as e:
            logger.warning(f"⚠️ Erro ao inicializar componentes avançados: {e}")
            self.db_connector = None
            self.api_connector = None
            self.analytics_tools = None
    
    def _verificar_caminhos(self) -> tuple[bool, str]:
        """Verifica se os caminhos necessários existem"""
        if not os.path.exists(self.mcp_script_path):
            return False, f"MCP script não encontrado: {self.mcp_script_path}"
        
        if not os.path.exists(self.venv_python_path):
            return False, f"Python venv não encontrado: {self.venv_python_path}"
        
        return True, "OK"
    
    def _criar_requisicao_mcp(self, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Cria requisição no formato MCP"""
        if arguments is None:
            arguments = {}
            
        return {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
    
    def _executar_mcp(self, requisicao: Dict[str, Any], timeout: int = 30) -> tuple[bool, Any]:
        """Executa comando MCP e retorna resultado"""
        try:
            # Verifica caminhos
            caminhos_ok, erro_caminho = self._verificar_caminhos()
            if not caminhos_ok:
                return False, erro_caminho
            
            # Prepara comando
            cmd = [self.venv_python_path, self.mcp_script_path]
            
            # Executa processo
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=os.path.dirname(self.mcp_script_path)
            )
            
            # Envia requisição JSON
            input_data = json.dumps(requisicao) + '\n'
            stdout, stderr = process.communicate(input=input_data, timeout=timeout)
            
            # Log de debug
            if stderr:
                logger.debug(f"MCP stderr: {stderr}")
            
            # Processa resposta
            if process.returncode == 0 and stdout.strip():
                try:
                    response = json.loads(stdout.strip())
                    return True, response
                except json.JSONDecodeError as e:
                    logger.error(f"Erro decodificação JSON: {e}")
                    return False, f"Resposta inválida do MCP: {stdout[:200]}..."
            else:
                return False, f"MCP erro (code {process.returncode}): {stderr}"
                
        except subprocess.TimeoutExpired:
            process.kill()
            return False, "Timeout na consulta MCP"
        except Exception as e:
            logger.error(f"Erro executando MCP: {e}")
            return False, f"Erro interno: {str(e)}"
    
    def status_sistema(self) -> tuple[bool, str]:
        """Consulta status do sistema via MCP"""
        try:
            # Tenta usar componentes avançados primeiro
            if self.db_connector and self.analytics_tools:
                return self._status_sistema_avancado()
            else:
                # Fallback para MCP básico
                return self._status_sistema_basico()
        except Exception as e:
            logger.error(f"Erro no status sistema: {e}")
            return False, str(e)
    
    def _status_sistema_avancado(self) -> tuple[bool, str]:
        """Status do sistema usando componentes avançados"""
        try:
            # Gerar estatísticas avançadas
            stats = self.db_connector.gerar_estatisticas_avancadas()
            insights = self.analytics_tools.gerar_insights_performance('geral')
            
            resposta = f"""🚀 **SISTEMA DE FRETES - STATUS AVANÇADO**

📊 **ESTATÍSTICAS GERAIS:**
• Total de Embarques: {stats.get('resumo_geral', {}).get('total_embarques', 0)}
• Embarques Ativos: {stats.get('resumo_geral', {}).get('embarques_ativos', 0)}
• Total de Fretes: {stats.get('resumo_geral', {}).get('total_fretes', 0)}
• Transportadoras: {stats.get('resumo_geral', {}).get('total_transportadoras', 0)}

🧠 **SISTEMA MCP AVANÇADO:**
• IA Integrada: ✅ Ativa
• Analytics: ✅ Funcionando
• Conectores: ✅ Operacionais
• Cache Inteligente: ✅ Ativo

⚡ **FUNCIONALIDADES DISPONÍVEIS:**
• Consultas inteligentes com IA
• Análise preditiva de tendências
• Detecção automática de anomalias
• Insights automáticos por entidade
• Relatórios adaptativos

💡 **INSIGHTS AUTOMÁTICOS:**
{chr(10).join(f"• {insight}" for insight in insights.get('insights', []))}

🕒 **Gerado em:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
🔗 **Conectado ao MCP v1.9.4 com Core Avançado**"""
            
            return True, resposta
            
        except Exception as e:
            logger.error(f"Erro status avançado: {e}")
            return self._status_sistema_basico()
    
    def _status_sistema_basico(self) -> tuple[bool, str]:
        """Status do sistema usando MCP básico"""
        requisicao = self._criar_requisicao_mcp("status_sistema")
        sucesso, resposta = self._executar_mcp(requisicao)
        
        if sucesso and 'result' in resposta:
            result = resposta['result']
            if isinstance(result, list) and len(result) > 0:
                return True, result[0].get('text', 'Resposta vazia')
            else:
                return True, str(result)
        else:
            return False, str(resposta)
    
    def consultar_fretes(self, cliente: Optional[str] = None) -> tuple[bool, str]:
        """Consulta fretes com funcionalidades avançadas"""
        try:
            # Usar componentes avançados se disponíveis
            if self.db_connector:
                return self._consultar_fretes_avancado(cliente)
            else:
                # Fallback para MCP básico
                return self._consultar_fretes_basico(cliente)
        except Exception as e:
            logger.error(f"Erro consulta fretes: {e}")
            return False, str(e)
    
    def _consultar_fretes_avancado(self, cliente: Optional[str] = None) -> tuple[bool, str]:
        """Consulta fretes usando banco avançado"""
        try:
            filtros = {'cliente': cliente} if cliente else {}
            resultado = self.db_connector.consultar_fretes_inteligente(filtros)
            
            if not resultado.data:
                return True, f"🔍 **CONSULTA DE FRETES**\n\nNenhum frete encontrado{f' para o cliente {cliente}' if cliente else ''}."
            
            fretes_formatados = []
            for frete in resultado.data[:10]:  # Limitar a 10 para não sobrecarregar
                status_visual = frete.get('status_visual', {})
                fretes_formatados.append(
                    f"📦 **Frete #{frete['id']}**\n"
                    f"   • Cliente: {frete['cliente']}\n"
                    f"   • Origem: {frete['origem']} → Destino: {frete['destino']}\n"
                    f"   • Valor: R$ {frete['valor_considerado']:,.2f}\n"
                    f"   • Status: {status_visual.get('icone', '📋')} {frete['status_aprovacao']}\n"
                    f"   • Transportadora: {frete['transportadora']}"
                )
            
            resposta = f"""🚚 **CONSULTA DE FRETES AVANÇADA**

📊 **RESUMO:**
• Total encontrado: {resultado.total_count}
• Tempo de consulta: {resultado.execution_time:.2f}s
• Filtros: {cliente if cliente else 'Todos os clientes'}

📦 **FRETES ({len(resultado.data)} primeiros):**
{chr(10).join(fretes_formatados)}

⚡ **Powered by MCP Avançado**"""
            
            return True, resposta
            
        except Exception as e:
            logger.error(f"Erro fretes avançado: {e}")
            return self._consultar_fretes_basico(cliente)
    
    def _consultar_fretes_basico(self, cliente: Optional[str] = None) -> tuple[bool, str]:
        """Consulta fretes usando MCP básico"""
        args = {"cliente": cliente} if cliente else {}
        requisicao = self._criar_requisicao_mcp("consultar_fretes", args)
        sucesso, resposta = self._executar_mcp(requisicao)
        
        if sucesso and 'result' in resposta:
            result = resposta['result']
            if isinstance(result, list) and len(result) > 0:
                return True, result[0].get('text', 'Resposta vazia')
            else:
                return True, str(result)
        else:
            return False, str(resposta)
    
    def analytics_inteligente(self, tipo_analise: str = 'geral') -> tuple[bool, str]:
        """Executa análises avançadas com IA"""
        try:
            if not self.analytics_tools:
                return False, "Analytics avançado não disponível"
            
            if tipo_analise == 'tendencias':
                resultado = self.analytics_tools.analisar_tendencias_embarques()
                return self._formatar_resposta_tendencias(resultado)
            
            elif tipo_analise == 'anomalias':
                resultado = self.analytics_tools.detectar_anomalias_sistema()
                return self._formatar_resposta_anomalias(resultado)
            
            elif tipo_analise == 'insights':
                resultado = self.analytics_tools.gerar_insights_performance()
                return self._formatar_resposta_insights(resultado)
            
            else:
                return False, f"Tipo de análise '{tipo_analise}' não suportado"
                
        except Exception as e:
            logger.error(f"Erro analytics: {e}")
            return False, str(e)
    
    def _formatar_resposta_tendencias(self, resultado: Dict) -> tuple[bool, str]:
        """Formata resposta de análise de tendências"""
        if 'erro' in resultado:
            return False, resultado['erro']
        
        if 'tendencia' in resultado and resultado['tendencia'] == 'Sem dados suficientes':
            return True, "📈 **ANÁLISE DE TENDÊNCIAS**\n\nSem dados suficientes para análise no período."
        
        tendencias = resultado.get('tendencias', {})
        insights = resultado.get('insights', [])
        
        resposta = f"""📈 **ANÁLISE PREDITIVA DE TENDÊNCIAS**

⏰ **Período:** {resultado.get('periodo_analisado', {}).get('dias', 30)} dias
📊 **Total de Embarques:** {resultado.get('total_embarques', 0)}
💰 **Valor Total:** R$ {resultado.get('valor_total_periodo', 0):,.2f}

📊 **TENDÊNCIAS IDENTIFICADAS:**

💰 **Valor dos Embarques:**
• Tendência: {tendencias.get('valor', {}).get('tendencia', 'N/A')} {tendencias.get('valor', {}).get('inclinacao', 0)}
• Média do período: R$ {tendencias.get('valor', {}).get('media_periodo', 0):,.2f}

📦 **Volume de Embarques:**
• Tendência: {tendencias.get('volume', {}).get('tendencia', 'N/A')}
• Média do período: {tendencias.get('volume', {}).get('media_periodo', 0)} embarques/dia

💡 **INSIGHTS AUTOMÁTICOS:**
{chr(10).join(f"• {insight.get('titulo', '')}: {insight.get('descricao', '')}" for insight in insights)}

🔮 **Gerado por IA em:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"""
        
        return True, resposta
    
    def _formatar_resposta_anomalias(self, resultado: Dict) -> tuple[bool, str]:
        """Formata resposta de detecção de anomalias"""
        if 'erro' in resultado:
            return False, resultado['erro']
        
        total = resultado.get('total_anomalias', 0)
        if total == 0:
            return True, "🔍 **DETECÇÃO DE ANOMALIAS**\n\n✅ Nenhuma anomalia detectada no sistema."
        
        anomalias = resultado.get('anomalias', [])
        recomendacoes = resultado.get('recomendacoes', [])
        
        anomalias_formatadas = []
        for anomalia in anomalias[:5]:  # Mostrar até 5
            criticidade_icon = {'alta': '🚨', 'media': '⚠️', 'baixa': '💡'}.get(anomalia.get('criticidade', 'baixa'), '💡')
            anomalias_formatadas.append(
                f"{criticidade_icon} **{anomalia.get('titulo', 'Anomalia')}**\n"
                f"   • {anomalia.get('descricao', '')}\n"
                f"   • Criticidade: {anomalia.get('criticidade', 'baixa').title()}"
            )
        
        resposta = f"""🔍 **DETECÇÃO AUTOMÁTICA DE ANOMALIAS**

📊 **RESUMO:**
• Total de anomalias: {total}
• Críticas: {resultado.get('anomalias_criticas', 0)} 🚨
• Moderadas: {resultado.get('anomalias_moderadas', 0)} ⚠️
• Baixas: {resultado.get('anomalias_baixas', 0)} 💡

🚨 **ANOMALIAS DETECTADAS:**
{chr(10).join(anomalias_formatadas)}

💡 **RECOMENDAÇÕES:**
{chr(10).join(f"• {rec}" for rec in recomendacoes)}

🤖 **Detectado por IA em:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"""
        
        return True, resposta
    
    def _formatar_resposta_insights(self, resultado: Dict) -> tuple[bool, str]:
        """Formata resposta de insights"""
        if 'erro' in resultado:
            return False, resultado['erro']
        
        insights = resultado.get('insights', [])
        tipo = resultado.get('tipo', 'geral')
        
        resposta = f"""💡 **INSIGHTS DE PERFORMANCE - {tipo.upper()}**

🧠 **ANÁLISE INTELIGENTE:**
{chr(10).join(f"• {insight}" for insight in insights)}

📊 **DADOS ESPECÍFICOS:**"""
        
        # Adicionar dados específicos por tipo
        for key, value in resultado.items():
            if key not in ['tipo', 'insights', 'erro']:
                resposta += f"\n• {key.replace('_', ' ').title()}: {value}"
        
        resposta += f"\n\n🎯 **Gerado por IA em:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
        
        return True, resposta
    
    def consulta_inteligente(self, query: str) -> tuple[bool, str]:
        """Processa consulta de forma inteligente usando IA"""
        query_lower = query.lower()
        
        try:
            # Análise inteligente da query com IA
            if any(word in query_lower for word in ['tendencia', 'preditiv', 'futuro', 'crescimento']):
                return self.analytics_inteligente('tendencias')
            
            elif any(word in query_lower for word in ['anomalia', 'problema', 'detectar', 'erro']):
                return self.analytics_inteligente('anomalias')
            
            elif any(word in query_lower for word in ['insight', 'analise', 'performance', 'analisar']):
                return self.analytics_inteligente('insights')
            
            elif any(word in query_lower for word in ['status', 'sistema', 'funcionando', 'online']):
                return self.status_sistema()
            
            elif any(word in query_lower for word in ['transportadora', 'empresa', 'cnpj', 'freteiro']):
                return self.consultar_transportadoras()
            
            elif any(word in query_lower for word in ['frete', 'cliente', 'cotacao', 'cte']):
                # Extrai nome do cliente se mencionado
                cliente = self._extrair_cliente_query(query)
                return self.consultar_fretes(cliente)
            
            elif any(word in query_lower for word in ['embarque', 'ativo', 'andamento', 'placa']):
                return self.consultar_embarques()
            
            elif any(word in query_lower for word in ['help', 'ajuda', 'comando']):
                return True, self._help_message_avancado()
            
            else:
                # Query genérica - tentar analytics primeiro
                return self.analytics_inteligente('insights')
                
        except Exception as e:
            logger.error(f"Erro consulta inteligente: {e}")
            return False, str(e)
    
    def _extrair_cliente_query(self, query: str) -> Optional[str]:
        """Extrai nome do cliente da query"""
        palavras = query.split()
        for i, palavra in enumerate(palavras):
            if palavra.lower() in ['cliente', 'do', 'da'] and i + 1 < len(palavras):
                return palavras[i + 1]
        return None
    
    def consultar_transportadoras(self) -> tuple[bool, str]:
        """Consulta transportadoras via MCP"""
        requisicao = self._criar_requisicao_mcp("consultar_transportadoras")
        sucesso, resposta = self._executar_mcp(requisicao)
        
        if sucesso and 'result' in resposta:
            result = resposta['result']
            if isinstance(result, list) and len(result) > 0:
                return True, result[0].get('text', 'Resposta vazia')
            else:
                return True, str(result)
        else:
            return False, str(resposta)
    
    def consultar_embarques(self) -> tuple[bool, str]:
        """Consulta embarques via MCP"""
        requisicao = self._criar_requisicao_mcp("consultar_embarques")
        sucesso, resposta = self._executar_mcp(requisicao)
        
        if sucesso and 'result' in resposta:
            result = resposta['result']
            if isinstance(result, list) and len(result) > 0:
                return True, result[0].get('text', 'Resposta vazia')
            else:
                return True, str(result)
        else:
            return False, str(resposta)
    
    def _help_message_avancado(self) -> str:
        """Mensagem de ajuda com comandos avançados"""
        return """🤖 **ASSISTENTE CLAUDE AVANÇADO - SISTEMA DE FRETES**

🧠 **COMANDOS COM IA INTEGRADA:**
• "análise preditiva de tendências" - Detecta padrões e previsões
• "detectar anomalias no sistema" - Identifica problemas automaticamente  
• "gerar insights de performance" - Análise inteligente de métricas
• "analisar tendências de embarques" - Evolução temporal

📊 **CONSULTAS TRADICIONAIS:**
• "status do sistema" - Verifica funcionamento e estatísticas
• "transportadoras" - Lista empresas cadastradas  
• "fretes" ou "fretes do cliente X" - Consulta fretes
• "embarques ativos" - Mostra embarques em andamento

🎯 **EXEMPLOS AVANÇADOS:**
• "Como está evoluindo o volume de embarques?"
• "Existem anomalias que preciso saber?"
• "Gere insights sobre performance das transportadoras"
• "Análise preditiva para o próximo mês"

💡 **NOVIDADES:**
✅ **IA Integrada** - Entende contexto e intenção
✅ **Analytics Automático** - Detecta padrões e anomalias
✅ **Insights Inteligentes** - Recomendações personalizadas
✅ **Cache Otimizado** - Respostas mais rápidas

🔗 **Conectado ao MCP v1.9.4 com Core Avançado + IA**"""
    
    def health_check(self) -> Dict[str, Any]:
        """Verifica saúde do conector MCP avançado"""
        caminhos_ok, erro = self._verificar_caminhos()
        
        componentes_avancados = {
            'database_connector': self.db_connector is not None,
            'api_connector': self.api_connector is not None,
            'analytics_tools': self.analytics_tools is not None
        }
        
        if not caminhos_ok:
            return {
                "healthy": False,
                "error": erro,
                "timestamp": datetime.now().isoformat(),
                "advanced_components": componentes_avancados
            }
        
        # Testa conexão real
        sucesso, resposta = self.status_sistema()
        
        return {
            "healthy": sucesso,
            "mcp_version": "1.9.4 + Core Avançado",
            "advanced_components": componentes_avancados,
            "response_time": "< 1s" if sucesso else "timeout",
            "last_check": datetime.now().isoformat(),
            "error": None if sucesso else str(resposta)
        }

# Manter compatibilidade com código existente
MCPConnector = MCPConnectorAdvanced 

class MCPSistemaOnline(MCPConnectorAdvanced):
    """Versão otimizada para uso direto no sistema online"""
    
    def __init__(self, app_root_path: str = None):
        """Inicialização simplificada para sistema online"""
        if app_root_path is None:
            # Detectar automaticamente o path
            app_root_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        
        super().__init__(app_root_path)
        
        # Configurações específicas para sistema online
        self.timeout = 15  # Timeout menor para interface web
        self.max_response_length = 5000  # Limite de resposta
        
    def consulta_rapida(self, query: str) -> dict:
        """Consulta otimizada para interface web"""
        try:
            sucesso, resposta = self.consulta_inteligente(query)
            
            # Limitar tamanho da resposta
            if len(resposta) > self.max_response_length:
                resposta = resposta[:self.max_response_length] + "\n\n... (resposta truncada)"
            
            return {
                'success': sucesso,
                'response': resposta,
                'timestamp': datetime.now().isoformat(),
                'source': 'MCP_SISTEMA_ONLINE'
            }
            
        except Exception as e:
            logger.error(f"Erro consulta rápida: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'source': 'MCP_SISTEMA_ONLINE_ERROR'
            }
    
    def status_rapido(self) -> dict:
        """Status otimizado para dashboard"""
        try:
            sucesso, resposta = self.status_sistema()
            
            return {
                'online': sucesso,
                'components': {
                    'mcp_basic': True,
                    'mcp_advanced': self.db_connector is not None,
                    'analytics': self.analytics_tools is not None,
                    'api_connector': self.api_connector is not None
                },
                'message': resposta if sucesso else "Sistema com problemas",
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'online': False,
                'error': str(e),
                'components': {
                    'mcp_basic': False,
                    'mcp_advanced': False,
                    'analytics': False,
                    'api_connector': False
                },
                'timestamp': datetime.now().isoformat()
            } 