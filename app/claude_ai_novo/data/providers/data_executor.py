"""
🎯 DATA EXECUTOR - Executador de Consultas Reais
Integra sistema novo com funcionalidades de dados do sistema antigo
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

class DataExecutor:
    """Executador de consultas reais no banco de dados"""
    
    def __init__(self):
        """Inicializa executor de dados"""
        self._carregar_funcoes_dados()
        logger.info("🎯 Data Executor inicializado")
    
    def _carregar_funcoes_dados(self):
        """Carrega funções de dados do sistema antigo"""
        try:
            # Importar funções do sistema antigo que fazem queries reais
            from app.claude_ai.claude_real_integration import (
                _carregar_dados_entregas,
                _carregar_dados_fretes,
                _carregar_dados_pedidos,
                _carregar_dados_embarques,
                _carregar_dados_faturamento,
                _carregar_dados_financeiro,
                _carregar_dados_transportadoras
            )
            
            # Mapear funções por domínio
            self.funcoes_dados = {
                'entregas': _carregar_dados_entregas,
                'fretes': _carregar_dados_fretes,
                'pedidos': _carregar_dados_pedidos,
                'embarques': _carregar_dados_embarques,
                'faturamento': _carregar_dados_faturamento,
                'financeiro': _carregar_dados_financeiro,
                'transportadoras': _carregar_dados_transportadoras
            }
            
            logger.info("✅ Funções de dados carregadas do sistema antigo")
            
        except Exception as e:
            logger.error(f"❌ Erro ao carregar funções de dados: {e}")
            self.funcoes_dados = {}
    
    def executar_consulta_dados(self, consulta: str, user_context: Optional[Dict] = None) -> Dict[str, Any]:
        """Executa consulta e retorna dados reais do banco"""
        try:
            # Detectar domínio da consulta
            dominio = self._detectar_dominio_consulta(consulta)
            
            # Preparar parâmetros para consulta
            analise = self._analisar_consulta(consulta, user_context)
            filtros_usuario = self._obter_filtros_usuario(user_context)
            data_limite = self._calcular_data_limite(analise)
            
            # Executar consulta no domínio específico
            if dominio in self.funcoes_dados:
                logger.info(f"🔍 Executando consulta no domínio: {dominio}")
                dados = self.funcoes_dados[dominio](analise, filtros_usuario, data_limite)
                
                # Adicionar metadados
                dados['dominio_detectado'] = dominio
                dados['consulta_original'] = consulta
                dados['timestamp'] = datetime.now().isoformat()
                
                return dados
            else:
                # Consulta geral - tentar múltiplos domínios
                return self._executar_consulta_geral(analise, filtros_usuario, data_limite)
                
        except Exception as e:
            logger.error(f"❌ Erro ao executar consulta: {e}")
            return {
                'erro': str(e),
                'consulta_original': consulta,
                'timestamp': datetime.now().isoformat()
            }
    
    def _detectar_dominio_consulta(self, consulta: str) -> str:
        """Detecta domínio principal da consulta"""
        consulta_lower = consulta.lower()
        
        # Palavras-chave por domínio
        palavras_entrega = ['entrega', 'entregar', 'entregue', 'monitoramento', 'canhoto']
        palavras_frete = ['frete', 'freteiro', 'transportadora', 'cte']
        palavras_pedido = ['pedido', 'cotação', 'cotacao', 'orcamento']
        palavras_embarque = ['embarque', 'embarcar', 'expedição', 'expedicao', 'carregamento']
        palavras_faturamento = ['faturamento', 'fatura', 'nf', 'nota fiscal']
        palavras_financeiro = ['financeiro', 'despesa', 'pendencia', 'pagamento']
        
        # Contagem por domínio
        scores = {
            'entregas': sum(1 for p in palavras_entrega if p in consulta_lower),
            'fretes': sum(1 for p in palavras_frete if p in consulta_lower),
            'pedidos': sum(1 for p in palavras_pedido if p in consulta_lower),
            'embarques': sum(1 for p in palavras_embarque if p in consulta_lower),
            'faturamento': sum(1 for p in palavras_faturamento if p in consulta_lower),
            'financeiro': sum(1 for p in palavras_financeiro if p in consulta_lower)
        }
        
        # Retornar domínio com maior score
        dominio_principal = max(scores.keys(), key=lambda x: scores[x])
        
        # Se score muito baixo, considerar geral
        if scores[dominio_principal] == 0:
            return 'geral'
        
        logger.info(f"🎯 Domínio detectado: {dominio_principal} (score: {scores[dominio_principal]})")
        return dominio_principal
    
    def _analisar_consulta(self, consulta: str, user_context: Optional[Dict] = None) -> Dict[str, Any]:
        """Analisa consulta para extrair filtros e parâmetros"""
        analise = {
            'consulta_original': consulta,
            'periodo_dias': 30,  # Padrão
            'cliente_especifico': None,
            'uf_especifica': None,
            'correcao_usuario': False
        }
        
        consulta_lower = consulta.lower()
        
        # Detectar período
        if 'hoje' in consulta_lower:
            analise['periodo_dias'] = 1
        elif 'semana' in consulta_lower:
            analise['periodo_dias'] = 7
        elif 'mês' in consulta_lower or 'mes' in consulta_lower:
            analise['periodo_dias'] = 30
        
        # Detectar cliente específico
        clientes_conhecidos = ['assai', 'atacadão', 'atacadao', 'carrefour', 'tenda', 'mateus', 'coco bambu']
        for cliente in clientes_conhecidos:
            if cliente in consulta_lower:
                analise['cliente_especifico'] = cliente.title()
                break
        
        # Detectar UF
        ufs = ['sp', 'rj', 'mg', 'rs', 'pr', 'sc', 'ba', 'pe', 'ce', 'go', 'df']
        for uf in ufs:
            if f' {uf} ' in consulta_lower or f' {uf.upper()} ' in consulta:
                analise['uf_especifica'] = uf.upper()
                break
        
        return analise
    
    def _obter_filtros_usuario(self, user_context: Optional[Dict] = None) -> Dict[str, Any]:
        """Obtém filtros baseados no contexto do usuário"""
        filtros = {}
        
        if user_context:
            # Filtros baseados no perfil do usuário
            if 'vendedor_codigo' in user_context:
                filtros['vendedor_codigo'] = user_context['vendedor_codigo']
            
            if 'user_id' in user_context:
                filtros['user_id'] = user_context['user_id']
        
        return filtros
    
    def _calcular_data_limite(self, analise: Dict[str, Any]) -> datetime:
        """Calcula data limite baseada no período"""
        periodo_dias = analise.get('periodo_dias', 30)
        return datetime.now() - timedelta(days=periodo_dias)
    
    def _executar_consulta_geral(self, analise: Dict[str, Any], filtros_usuario: Dict[str, Any], data_limite: datetime) -> Dict[str, Any]:
        """Executa consulta geral em múltiplos domínios"""
        try:
            resultados = {}
            
            # Executar em todos os domínios disponíveis
            for dominio, funcao in self.funcoes_dados.items():
                try:
                    resultado = funcao(analise, filtros_usuario, data_limite)
                    resultados[dominio] = resultado
                except Exception as e:
                    logger.warning(f"⚠️ Erro no domínio {dominio}: {e}")
                    resultados[dominio] = {'erro': str(e)}
            
            return {
                'tipo_consulta': 'geral',
                'dominios_consultados': list(resultados.keys()),
                'resultados': resultados,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Erro na consulta geral: {e}")
            return {'erro': str(e)}

# Instância global
_data_executor = None

def get_data_executor():
    """Retorna instância do executor de dados"""
    global _data_executor
    if _data_executor is None:
        _data_executor = DataExecutor()
    return _data_executor 