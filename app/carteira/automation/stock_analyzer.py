# 📊 ANALISADOR INTELIGENTE DE ESTOQUE
# Análise preditiva baseada nos campos estoque_d0 até estoque_d28

from datetime import datetime, date, timedelta
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class StockAnalyzer:
    """
    📊 Analisador inteligente de estoque da carteira
    
    FUNCIONALIDADES:
    - Análise dos campos estoque_d0 até estoque_d28 
    - Detecção automática de disponibilidade e rupturas
    - Programação otimizada de expedições
    - Cálculo de menor estoque em 7 dias (menor_estoque_produto_d7)
    - Integração com sistema de produção programada
    """
    
    def __init__(self):
        # 📊 CONFIGURAÇÕES DE ANÁLISE
        self.config = {
            'margem_seguranca': 0.1,     # 10% margem de segurança
            'dias_alerta_ruptura': 3,    # Alertar rupturas em D+3  
            'estoque_minimo': 1.0,       # Estoque mínimo considerado
            'projecao_maxima': 28        # Máximo D+28
        }
        
        logger.info("📊 StockAnalyzer inicializado")
    
    def analisar_disponibilidade_completa(self, item) -> Dict:
        """
        🔍 ANÁLISE COMPLETA DE DISPONIBILIDADE DE ESTOQUE
        
        Args:
            item: Instância de CarteiraPrincipal
            
        Returns:
            Dict com análise completa de estoque
        """
        try:
            qtd_necessaria = float(getattr(item, 'qtd_saldo_produto_pedido', 0) or 0)
            
            resultado = {
                'num_pedido': str(item.num_pedido),
                'cod_produto': str(item.cod_produto),
                'qtd_necessaria': qtd_necessaria,
                'disponibilidade_hoje': self._verificar_disponibilidade_hoje(item, qtd_necessaria),
                'projecao_28_dias': self._analisar_projecao_28_dias(item, qtd_necessaria),
                'primeira_data_disponivel': self._encontrar_primeira_data_disponivel(item, qtd_necessaria),
                'situacao_estoque': None,
                'acao_recomendada': None,
                'data_expedicao_sugerida': None,
                'riscos_identificados': self._identificar_riscos(item, qtd_necessaria)
            }
            
            # 🎯 DEFINIR SITUAÇÃO E AÇÃO
            resultado['situacao_estoque'] = self._classificar_situacao_estoque(resultado)
            resultado['acao_recomendada'] = self._recomendar_acao(resultado)
            resultado['data_expedicao_sugerida'] = self._calcular_data_expedicao(resultado)
            
            # 📊 ATUALIZAR CAMPOS CALCULADOS DO ITEM
            self._atualizar_campos_calculados(item, resultado)
            
            logger.debug(f"✅ Estoque analisado {item.num_pedido}-{item.cod_produto}: {resultado['situacao_estoque']}")
            
            return resultado
            
        except Exception as e:
            logger.error(f"❌ Erro na análise de estoque {item.num_pedido}-{item.cod_produto}: {str(e)}")
            return self._analise_erro(item)
    
    def _verificar_disponibilidade_hoje(self, item, qtd_necessaria: float) -> Dict:
        """
        📋 VERIFICAÇÃO DA DISPONIBILIDADE HOJE (D0)
        """
        try:
            estoque_d0 = float(getattr(item, 'estoque_d0', 0) or 0)
            estoque_atual = float(getattr(item, 'estoque', 0) or estoque_d0)  # Fallback para estoque_d0
            
            disponivel = estoque_atual >= qtd_necessaria
            margem_seguranca = qtd_necessaria * (1 + self.config['margem_seguranca'])
            seguro = estoque_atual >= margem_seguranca
            
            return {
                'estoque_atual': estoque_atual,
                'qtd_necessaria': qtd_necessaria,
                'disponivel': disponivel,
                'com_margem_seguranca': seguro,
                'saldo_apos_separacao': estoque_atual - qtd_necessaria if disponivel else None,
                'percentual_atendimento': (estoque_atual / qtd_necessaria * 100) if qtd_necessaria > 0 else 100
            }
            
        except Exception as e:
            logger.warning(f"Erro na verificação de disponibilidade hoje: {str(e)}")
            return {
                'estoque_atual': 0,
                'qtd_necessaria': qtd_necessaria,
                'disponivel': False,
                'com_margem_seguranca': False,
                'saldo_apos_separacao': None,
                'percentual_atendimento': 0
            }
    
    def _analisar_projecao_28_dias(self, item, qtd_necessaria: float) -> Dict:
        """
        📈 ANÁLISE DA PROJEÇÃO D0 ATÉ D28
        """
        try:
            projecao = {}
            
            # Analisar cada dia D0 até D28
            for dia in range(29):  # 0 a 28
                campo_estoque = f'estoque_d{dia}'
                estoque_dia = float(getattr(item, campo_estoque, 0) or 0)
                
                projecao[f'd{dia}'] = {
                    'estoque': estoque_dia,
                    'disponivel': estoque_dia >= qtd_necessaria,
                    'data': date.today() + timedelta(days=dia),
                    'saldo_apos': estoque_dia - qtd_necessaria if estoque_dia >= qtd_necessaria else None
                }
            
            # Calcular estatísticas da projeção
            estatisticas = self._calcular_estatisticas_projecao(projecao, qtd_necessaria)
            
            return {
                'projecao_diaria': projecao,
                'estatisticas': estatisticas
            }
            
        except Exception as e:
            logger.warning(f"Erro na análise de projeção 28 dias: {str(e)}")
            return {
                'projecao_diaria': {},
                'estatisticas': {'erro': str(e)}
            }
    
    def _calcular_estatisticas_projecao(self, projecao: Dict, qtd_necessaria: float) -> Dict:
        """
        📊 CÁLCULO DE ESTATÍSTICAS DA PROJEÇÃO
        """
        try:
            # Encontrar primeiro dia disponível
            primeiro_dia_disponivel = None
            dias_disponiveis = 0
            menor_estoque_7_dias = float('inf')
            
            for dia_key, dados in projecao.items():
                dia_num = int(dia_key[1:])  # Extrair número do dia
                
                # Primeiro dia disponível
                if dados['disponivel'] and primeiro_dia_disponivel is None:
                    primeiro_dia_disponivel = dia_num
                
                # Contar dias disponíveis
                if dados['disponivel']:
                    dias_disponiveis += 1
                
                # Menor estoque em 7 dias
                if dia_num <= 7:
                    menor_estoque_7_dias = min(menor_estoque_7_dias, dados['estoque'])
            
            # Ajustar menor estoque se foi infinito
            if menor_estoque_7_dias == float('inf'):
                menor_estoque_7_dias = 0
            
            return {
                'primeiro_dia_disponivel': primeiro_dia_disponivel,
                'dias_com_estoque': dias_disponiveis,
                'percentual_disponibilidade': (dias_disponiveis / 29) * 100,
                'menor_estoque_7_dias': menor_estoque_7_dias,
                'tem_reposicao_programada': primeiro_dia_disponivel is not None,
                'data_primeira_disponibilidade': date.today() + timedelta(days=primeiro_dia_disponivel) if primeiro_dia_disponivel is not None else None
            }
            
        except Exception as e:
            logger.warning(f"Erro no cálculo de estatísticas: {str(e)}")
            return {
                'primeiro_dia_disponivel': None,
                'dias_com_estoque': 0,
                'percentual_disponibilidade': 0,
                'menor_estoque_7_dias': 0,
                'tem_reposicao_programada': False,
                'data_primeira_disponibilidade': None
            }
    
    def _encontrar_primeira_data_disponivel(self, item, qtd_necessaria: float) -> Optional[date]:
        """
        📅 ENCONTRAR PRIMEIRA DATA COM ESTOQUE DISPONÍVEL
        """
        try:
            for dia in range(29):  # D0 até D28
                campo_estoque = f'estoque_d{dia}'
                estoque_dia = float(getattr(item, campo_estoque, 0) or 0)
                
                if estoque_dia >= qtd_necessaria:
                    return date.today() + timedelta(days=dia)
            
            # Não encontrou em 28 dias
            return None
            
        except Exception as e:
            logger.warning(f"Erro ao encontrar primeira data disponível: {str(e)}")
            return None
    
    def _identificar_riscos(self, item, qtd_necessaria: float) -> List[str]:
        """
        ⚠️ IDENTIFICAÇÃO DE RISCOS NO ESTOQUE
        """
        riscos = []
        
        try:
            # Risco de ruptura em 3 dias
            for dia in range(self.config['dias_alerta_ruptura'] + 1):
                campo_estoque = f'estoque_d{dia}'
                estoque_dia = float(getattr(item, campo_estoque, 0) or 0)
                
                if estoque_dia < qtd_necessaria:
                    riscos.append(f'RUPTURA_D{dia}')
            
            # Estoque baixo em 7 dias
            menor_estoque_7_dias = float('inf')
            for dia in range(8):  # D0 até D7
                campo_estoque = f'estoque_d{dia}'
                estoque_dia = float(getattr(item, campo_estoque, 0) or 0)
                menor_estoque_7_dias = min(menor_estoque_7_dias, estoque_dia)
            
            if menor_estoque_7_dias < self.config['estoque_minimo']:
                riscos.append('ESTOQUE_BAIXO_7_DIAS')
            
            # Sem reposição programada
            tem_reposicao = False
            for dia in range(1, 29):  # D1 até D28
                campo_estoque = f'estoque_d{dia}'
                estoque_dia = float(getattr(item, campo_estoque, 0) or 0)
                if estoque_dia >= qtd_necessaria:
                    tem_reposicao = True
                    break
            
            if not tem_reposicao:
                riscos.append('SEM_REPOSICAO_PROGRAMADA')
            
            # Produto crítico
            if hasattr(item, 'categoria_produto'):
                categoria = str(getattr(item, 'categoria_produto', '')).upper()
                if 'CRITICO' in categoria or 'ESPECIAL' in categoria:
                    riscos.append('PRODUTO_CRITICO')
            
        except Exception as e:
            logger.warning(f"Erro na identificação de riscos: {str(e)}")
            riscos.append('ERRO_ANALISE_RISCOS')
        
        return riscos
    
    def _classificar_situacao_estoque(self, analise: Dict) -> str:
        """
        🎯 CLASSIFICAÇÃO DA SITUAÇÃO DO ESTOQUE
        """
        disponibilidade_hoje = analise['disponibilidade_hoje']
        projecao = analise['projecao_28_dias']['estatisticas']
        riscos = analise['riscos_identificados']
        
        # Disponível hoje
        if disponibilidade_hoje['disponivel']:
            if disponibilidade_hoje['com_margem_seguranca']:
                return 'DISPONIVEL_SEGURO'
            else:
                return 'DISPONIVEL_LIMITADO'
        
        # Não disponível hoje, mas tem reposição programada
        if projecao['tem_reposicao_programada']:
            primeiro_dia = projecao['primeiro_dia_disponivel']
            if primeiro_dia <= 7:
                return 'AGUARDA_REPOSICAO_CURTA'
            else:
                return 'AGUARDA_REPOSICAO_LONGA'
        
        # Sem reposição programada
        return 'RUPTURA_CRITICA'
    
    def _recomendar_acao(self, analise: Dict) -> str:
        """
        🎯 RECOMENDAÇÃO DE AÇÃO BASEADA NA ANÁLISE
        """
        situacao = analise['situacao_estoque']
        
        acoes = {
            'DISPONIVEL_SEGURO': 'SEPARAR_IMEDIATAMENTE',
            'DISPONIVEL_LIMITADO': 'SEPARAR_COM_PRIORIZACAO',
            'AGUARDA_REPOSICAO_CURTA': 'PROGRAMAR_EXPEDICAO',
            'AGUARDA_REPOSICAO_LONGA': 'REAGENDAR_ENTREGA',
            'RUPTURA_CRITICA': 'STANDBY_COMERCIAL'
        }
        
        return acoes.get(situacao, 'ANALISE_MANUAL')
    
    def _calcular_data_expedicao(self, analise: Dict) -> Optional[date]:
        """
        📅 CÁLCULO DA DATA SUGERIDA DE EXPEDIÇÃO
        """
        situacao = analise['situacao_estoque']
        
        if situacao in ['DISPONIVEL_SEGURO', 'DISPONIVEL_LIMITADO']:
            return date.today()
        
        primeira_data = analise['primeira_data_disponivel']
        if primeira_data:
            return primeira_data
        
        return None
    
    def _atualizar_campos_calculados(self, item, analise: Dict):
        """
        📊 ATUALIZAÇÃO DOS CAMPOS CALCULADOS NO ITEM
        """
        try:
            # Atualizar menor_estoque_produto_d7
            menor_estoque_7_dias = analise['projecao_28_dias']['estatisticas']['menor_estoque_7_dias']
            if hasattr(item, 'menor_estoque_produto_d7'):
                item.menor_estoque_produto_d7 = menor_estoque_7_dias
            
            # Atualizar saldo_estoque_pedido (estoque na data de expedição sugerida)
            data_expedicao = analise['data_expedicao_sugerida']
            if data_expedicao and hasattr(item, 'saldo_estoque_pedido'):
                dias_ate_expedicao = (data_expedicao - date.today()).days
                if 0 <= dias_ate_expedicao <= 28:
                    campo_estoque = f'estoque_d{dias_ate_expedicao}'
                    estoque_expedicao = float(getattr(item, campo_estoque, 0) or 0)
                    item.saldo_estoque_pedido = estoque_expedicao
            
            # Atualizar data de expedição sugerida
            if data_expedicao and hasattr(item, 'expedicao'):
                item.expedicao = data_expedicao
            
        except Exception as e:
            logger.warning(f"Erro na atualização de campos calculados: {str(e)}")
    
    def _analise_erro(self, item) -> Dict:
        """
        ❌ ANÁLISE DE FALLBACK PARA ERROS
        """
        return {
            'num_pedido': str(getattr(item, 'num_pedido', 'N/A')),
            'cod_produto': str(getattr(item, 'cod_produto', 'N/A')),
            'qtd_necessaria': 0,
            'disponibilidade_hoje': {
                'estoque_atual': 0,
                'disponivel': False,
                'com_margem_seguranca': False,
                'percentual_atendimento': 0
            },
            'projecao_28_dias': {
                'projecao_diaria': {},
                'estatisticas': {'erro': 'Erro na análise'}
            },
            'primeira_data_disponivel': None,
            'situacao_estoque': 'ERRO_ANALISE',
            'acao_recomendada': 'ANALISE_MANUAL',
            'data_expedicao_sugerida': None,
            'riscos_identificados': ['ERRO_ANALISE']
        }
    
    def analisar_lote_estoque(self, itens_carteira: List) -> Dict:
        """
        📊 ANÁLISE EM LOTE DO ESTOQUE DA CARTEIRA
        
        Args:
            itens_carteira: Lista de instâncias CarteiraPrincipal
            
        Returns:
            Dict com análises e estatísticas do lote
        """
        try:
            logger.info(f"🔄 Iniciando análise de estoque para {len(itens_carteira)} itens")
            
            resultados = []
            estatisticas = {
                'total_itens': len(itens_carteira),
                'por_situacao': {},
                'por_acao': {},
                'riscos_detectados': {},
                'disponibilidade_geral': {
                    'disponiveis_hoje': 0,
                    'com_reposicao': 0,
                    'ruptura_critica': 0
                },
                'tempo_processamento': None
            }
            
            inicio = datetime.now()
            
            # Analisar cada item
            for item in itens_carteira:
                analise = self.analisar_disponibilidade_completa(item)
                resultados.append(analise)
                
                # Atualizar estatísticas
                self._atualizar_estatisticas_lote(estatisticas, analise)
            
            # Tempo de processamento
            fim = datetime.now()
            estatisticas['tempo_processamento'] = (fim - inicio).total_seconds()
            
            logger.info(f"✅ Análise de estoque concluída em {estatisticas['tempo_processamento']:.2f}s")
            
            return {
                'resultados': resultados,
                'estatisticas': estatisticas,
                'sucesso': True
            }
            
        except Exception as e:
            logger.error(f"❌ Erro na análise em lote de estoque: {str(e)}")
            return {
                'resultados': [],
                'estatisticas': {'erro': str(e)},
                'sucesso': False
            }
    
    def _atualizar_estatisticas_lote(self, stats: Dict, analise: Dict):
        """
        📊 ATUALIZAÇÃO DAS ESTATÍSTICAS DO LOTE
        """
        # Por situação
        situacao = analise['situacao_estoque']
        stats['por_situacao'][situacao] = stats['por_situacao'].get(situacao, 0) + 1
        
        # Por ação recomendada
        acao = analise['acao_recomendada']
        stats['por_acao'][acao] = stats['por_acao'].get(acao, 0) + 1
        
        # Riscos detectados
        for risco in analise['riscos_identificados']:
            stats['riscos_detectados'][risco] = stats['riscos_detectados'].get(risco, 0) + 1
        
        # Disponibilidade geral
        if analise['disponibilidade_hoje']['disponivel']:
            stats['disponibilidade_geral']['disponiveis_hoje'] += 1
        elif analise['primeira_data_disponivel']:
            stats['disponibilidade_geral']['com_reposicao'] += 1
        else:
            stats['disponibilidade_geral']['ruptura_critica'] += 1 