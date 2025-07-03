# 🎯 MOTOR DE CLASSIFICAÇÃO AUTOMÁTICA
# Classifica pedidos por urgência e tipo de cliente

from datetime import datetime, date, timedelta
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class ClassificationEngine:
    """
    🎯 Motor de classificação automática de pedidos da carteira
    
    FUNCIONALIDADES:
    - Classificação por urgência (data_entrega_pedido)
    - Identificação de tipo de cliente (cliente_nec_agendamento)  
    - Priorização automática baseada em criticidade
    - Detecção de pedidos especiais (valores altos, clientes estratégicos)
    """
    
    def __init__(self):
        # 📊 CONFIGURAÇÕES DE CLASSIFICAÇÃO
        self.config = {
            'dias_critico': 7,        # ≤7 dias = CRÍTICO
            'dias_atencao': 15,       # 8-15 dias = ATENÇÃO
            'valor_alto': 50000.0,    # Pedidos de alto valor
            'qtd_alta': 1000.0        # Quantidades altas
        }
        
        # 🏢 CLIENTES ESTRATÉGICOS (baseado em análise real do sistema)
        self.clientes_estrategicos = {
            '06.057.223/',  # Assai
            '75.315.333/',  # Atacadão  
            '45.543.915/',  # Carrefour
            '01.157.555/'   # Tenda
        }
        
        logger.info("🎯 ClassificationEngine inicializado")
    
    def classificar_pedido_completo(self, item) -> Dict:
        """
        🔍 CLASSIFICAÇÃO COMPLETA DE UM ITEM DA CARTEIRA
        
        Args:
            item: Instância de CarteiraPrincipal
            
        Returns:
            Dict com classificação completa
        """
        try:
            resultado = {
                'num_pedido': str(item.num_pedido),
                'cod_produto': str(item.cod_produto),
                'classificacao_urgencia': self._classificar_urgencia(item),
                'tipo_cliente': self._identificar_tipo_cliente(item),
                'prioridade_geral': None,
                'caracteristicas_especiais': self._identificar_caracteristicas_especiais(item),
                'pipeline_recomendado': None
            }
            
            # 🎯 DEFINIR PRIORIDADE GERAL
            resultado['prioridade_geral'] = self._calcular_prioridade_geral(resultado)
            
            # 🛤️ DEFINIR PIPELINE RECOMENDADO
            resultado['pipeline_recomendado'] = self._definir_pipeline(resultado)
            
            logger.debug(f"✅ Pedido {item.num_pedido}-{item.cod_produto} classificado: {resultado['prioridade_geral']}")
            
            return resultado
            
        except Exception as e:
            logger.error(f"❌ Erro na classificação de {item.num_pedido}-{item.cod_produto}: {str(e)}")
            return self._classificacao_erro(item)
    
    def _classificar_urgencia(self, item) -> Dict:
        """
        🔴 CLASSIFICAÇÃO POR URGÊNCIA
        Baseado no campo 'data_entrega_pedido'
        """
        try:
            data_entrega = getattr(item, 'data_entrega_pedido', None)
            
            if not data_entrega:
                return {
                    'nivel': 'SEM_PRAZO',
                    'dias_restantes': None,
                    'cor': 'CINZA',
                    'descricao': 'Pedido sem data de entrega definida'
                }
            
            # Calcular dias restantes
            hoje = date.today()
            dias_restantes = (data_entrega - hoje).days
            
            # Classificar por urgência
            if dias_restantes <= self.config['dias_critico']:
                return {
                    'nivel': 'CRITICO',
                    'dias_restantes': dias_restantes,
                    'cor': 'VERMELHO',
                    'descricao': f'Entrega em {dias_restantes} dia(s) - CRÍTICO!'
                }
            elif dias_restantes <= self.config['dias_atencao']:
                return {
                    'nivel': 'ATENCAO',
                    'dias_restantes': dias_restantes,
                    'cor': 'AMARELO', 
                    'descricao': f'Entrega em {dias_restantes} dia(s) - Atenção'
                }
            else:
                return {
                    'nivel': 'NORMAL',
                    'dias_restantes': dias_restantes,
                    'cor': 'VERDE',
                    'descricao': f'Entrega em {dias_restantes} dia(s) - Normal'
                }
                
        except Exception as e:
            logger.warning(f"Erro na classificação de urgência: {str(e)}")
            return {
                'nivel': 'ERRO',
                'dias_restantes': None,
                'cor': 'CINZA',
                'descricao': 'Erro ao calcular urgência'
            }
    
    def _identificar_tipo_cliente(self, item) -> Dict:
        """
        📅 IDENTIFICAÇÃO DO TIPO DE CLIENTE
        Baseado no campo 'cliente_nec_agendamento'
        """
        try:
            necessita_agendamento = getattr(item, 'cliente_nec_agendamento', None)
            cnpj_cliente = getattr(item, 'cnpj_cpf', '')
            
            # Verificar se é cliente estratégico
            eh_estrategico = any(
                cnpj_cliente.startswith(cnpj_estrategico) 
                for cnpj_estrategico in self.clientes_estrategicos
            )
            
            if necessita_agendamento == 'Sim':
                return {
                    'tipo': 'COM_AGENDAMENTO',
                    'necessita_protocolo': True,
                    'pipeline': 'AGENDAMENTO',
                    'estrategico': eh_estrategico,
                    'descricao': 'Cliente necessita agendamento prévio'
                }
            else:
                return {
                    'tipo': 'SEM_AGENDAMENTO',
                    'necessita_protocolo': False,
                    'pipeline': 'EXPEDICAO_LIVRE',
                    'estrategico': eh_estrategico,
                    'descricao': 'Cliente com expedição livre'
                }
                
        except Exception as e:
            logger.warning(f"Erro na identificação do tipo de cliente: {str(e)}")
            return {
                'tipo': 'INDEFINIDO',
                'necessita_protocolo': False,
                'pipeline': 'MANUAL',
                'estrategico': False,
                'descricao': 'Tipo de cliente indefinido'
            }
    
    def _identificar_caracteristicas_especiais(self, item) -> List[str]:
        """
        ⭐ IDENTIFICAÇÃO DE CARACTERÍSTICAS ESPECIAIS
        """
        caracteristicas = []
        
        try:
            # Valor alto
            valor_produto = float(getattr(item, 'preco_produto_pedido', 0) or 0)
            qtd_produto = float(getattr(item, 'qtd_produto_pedido', 0) or 0)
            valor_total = valor_produto * qtd_produto
            
            if valor_total >= self.config['valor_alto']:
                caracteristicas.append('ALTO_VALOR')
            
            # Quantidade alta
            if qtd_produto >= self.config['qtd_alta']:
                caracteristicas.append('ALTA_QUANTIDADE')
            
            # Cliente estratégico
            cnpj_cliente = getattr(item, 'cnpj_cpf', '')
            if any(cnpj_cliente.startswith(cnpj) for cnpj in self.clientes_estrategicos):
                caracteristicas.append('CLIENTE_ESTRATEGICO')
            
            # Produto específico
            categoria = getattr(item, 'categoria_produto', '')
            if categoria and 'ESPECIAL' in categoria.upper():
                caracteristicas.append('PRODUTO_ESPECIAL')
            
            # Já tem separação vinculada
            lote_separacao = getattr(item, 'lote_separacao_id', None)
            if lote_separacao:
                caracteristicas.append('COM_SEPARACAO')
            
            # Tem protocolo definido
            protocolo = getattr(item, 'protocolo', None)
            if protocolo:
                caracteristicas.append('COM_PROTOCOLO')
                
        except Exception as e:
            logger.warning(f"Erro na identificação de características especiais: {str(e)}")
            caracteristicas.append('ERRO_ANALISE')
        
        return caracteristicas
    
    def _calcular_prioridade_geral(self, classificacao: Dict) -> Dict:
        """
        🎯 CÁLCULO DA PRIORIDADE GERAL
        """
        # Score base por urgência
        scores_urgencia = {
            'CRITICO': 100,
            'ATENCAO': 70,
            'NORMAL': 50,
            'SEM_PRAZO': 30,
            'ERRO': 10
        }
        
        score = scores_urgencia.get(classificacao['classificacao_urgencia']['nivel'], 30)
        
        # Bonus por características especiais
        caracteristicas = classificacao['caracteristicas_especiais']
        
        if 'CLIENTE_ESTRATEGICO' in caracteristicas:
            score += 20
        if 'ALTO_VALOR' in caracteristicas:
            score += 15
        if 'COM_SEPARACAO' in caracteristicas:
            score += 10
        if 'COM_PROTOCOLO' in caracteristicas:
            score += 5
        
        # Determinar nível final
        if score >= 90:
            nivel = 'MAXIMA'
        elif score >= 70:
            nivel = 'ALTA'
        elif score >= 50:
            nivel = 'MEDIA'
        else:
            nivel = 'BAIXA'
        
        return {
            'nivel': nivel,
            'score': score,
            'fatores': {
                'urgencia': classificacao['classificacao_urgencia']['nivel'],
                'caracteristicas': caracteristicas
            }
        }
    
    def _definir_pipeline(self, classificacao: Dict) -> str:
        """
        🛤️ DEFINIÇÃO DO PIPELINE RECOMENDADO
        """
        urgencia = classificacao['classificacao_urgencia']['nivel']
        tipo_cliente = classificacao['tipo_cliente']['tipo']
        prioridade = classificacao['prioridade_geral']['nivel']
        
        # Pipeline crítico
        if urgencia == 'CRITICO' or prioridade == 'MAXIMA':
            return 'URGENTE'
        
        # Pipeline por tipo de cliente
        if tipo_cliente == 'COM_AGENDAMENTO':
            return 'AGENDAMENTO'
        else:
            return 'EXPEDICAO_LIVRE'
    
    def _classificacao_erro(self, item) -> Dict:
        """
        ❌ CLASSIFICAÇÃO DE FALLBACK PARA ERROS
        """
        return {
            'num_pedido': str(getattr(item, 'num_pedido', 'N/A')),
            'cod_produto': str(getattr(item, 'cod_produto', 'N/A')),
            'classificacao_urgencia': {
                'nivel': 'ERRO',
                'dias_restantes': None,
                'cor': 'CINZA',
                'descricao': 'Erro na classificação'
            },
            'tipo_cliente': {
                'tipo': 'INDEFINIDO',
                'necessita_protocolo': False,
                'pipeline': 'MANUAL',
                'estrategico': False,
                'descricao': 'Processamento manual necessário'
            },
            'prioridade_geral': {
                'nivel': 'BAIXA',
                'score': 10,
                'fatores': {'urgencia': 'ERRO', 'caracteristicas': ['ERRO_ANALISE']}
            },
            'caracteristicas_especiais': ['ERRO_ANALISE'],
            'pipeline_recomendado': 'MANUAL'
        }
    
    def classificar_lote(self, itens_carteira: List) -> Dict:
        """
        📊 CLASSIFICAÇÃO EM LOTE DE ITENS DA CARTEIRA
        
        Args:
            itens_carteira: Lista de instâncias CarteiraPrincipal
            
        Returns:
            Dict com estatísticas e classificações
        """
        try:
            logger.info(f"🔄 Iniciando classificação de {len(itens_carteira)} itens")
            
            resultados = []
            estatisticas = {
                'total_itens': len(itens_carteira),
                'por_urgencia': {},
                'por_pipeline': {},
                'por_prioridade': {},
                'caracteristicas_especiais': {},
                'tempo_processamento': None
            }
            
            inicio = datetime.now()
            
            # Classificar cada item
            for item in itens_carteira:
                classificacao = self.classificar_pedido_completo(item)
                resultados.append(classificacao)
                
                # Atualizar estatísticas
                self._atualizar_estatisticas(estatisticas, classificacao)
            
            # Tempo de processamento
            fim = datetime.now()
            estatisticas['tempo_processamento'] = (fim - inicio).total_seconds()
            
            logger.info(f"✅ Classificação concluída em {estatisticas['tempo_processamento']:.2f}s")
            
            return {
                'resultados': resultados,
                'estatisticas': estatisticas,
                'sucesso': True
            }
            
        except Exception as e:
            logger.error(f"❌ Erro na classificação em lote: {str(e)}")
            return {
                'resultados': [],
                'estatisticas': {'erro': str(e)},
                'sucesso': False
            }
    
    def _atualizar_estatisticas(self, stats: Dict, classificacao: Dict):
        """
        📊 ATUALIZAÇÃO DAS ESTATÍSTICAS
        """
        # Por urgência
        urgencia = classificacao['classificacao_urgencia']['nivel']
        stats['por_urgencia'][urgencia] = stats['por_urgencia'].get(urgencia, 0) + 1
        
        # Por pipeline
        pipeline = classificacao['pipeline_recomendado']
        stats['por_pipeline'][pipeline] = stats['por_pipeline'].get(pipeline, 0) + 1
        
        # Por prioridade
        prioridade = classificacao['prioridade_geral']['nivel']
        stats['por_prioridade'][prioridade] = stats['por_prioridade'].get(prioridade, 0) + 1
        
        # Características especiais
        for caracteristica in classificacao['caracteristicas_especiais']:
            stats['caracteristicas_especiais'][caracteristica] = stats['caracteristicas_especiais'].get(caracteristica, 0) + 1 