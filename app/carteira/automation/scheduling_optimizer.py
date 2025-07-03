# 📅 OTIMIZADOR DE AGENDAMENTO INTELIGENTE
# Geração automática de protocolos e otimização de datas

from datetime import datetime, date, timedelta
from typing import Dict, List, Tuple, Optional
import logging
import random
import string

logger = logging.getLogger(__name__)

class SchedulingOptimizer:
    """
    📅 Otimizador inteligente de agendamento da carteira
    
    FUNCIONALIDADES:
    - Geração automática de protocolos de agendamento
    - Otimização de datas de entrega baseado em disponibilidade
    - Integração com campos agendamento e protocolo
    - Consideração de clientes que necessitam agendamento
    - Balanceamento de carga de entregas por região
    """
    
    def __init__(self):
        # 📅 CONFIGURAÇÕES DE AGENDAMENTO
        self.config = {
            'dias_antecedencia_min': 3,      # Mínimo 1 dia de antecedência
            'dias_antecedencia_max': 30,      # Máximo 7 dias de antecedência
            'max_entregas_por_dia': 50,      # Máximo 50 entregas por dia
            'prefixo_protocolo': 'AGD',      # Prefixo dos protocolos
            'dias_uteis_apenas': True,       # Apenas dias úteis
            'horarios_preferenciais': [      # Horários preferenciais
                '08:00-12:00',
                '13:00-17:00'
            ]
        }
        
        # 🏢 CONFIGURAÇÕES POR TIPO DE CLIENTE
        self.config_clientes = {
            'estrategico': {
                'prioridade': 1,
                'antecedencia_max': 3,    # Clientes estratégicos: até 3 dias
                'slot_reservado': True
            },
            'agendamento_obrigatorio': {
                'prioridade': 2,
                'antecedencia_max': 7,
                'slot_reservado': False
            },
            'sem_agendamento': {
                'prioridade': 3,
                'antecedencia_max': 7,
                'slot_reservado': False
            }
        }
        
        logger.info("📅 SchedulingOptimizer inicializado")
    
    def otimizar_agendamento_completo(self, item, classificacao: Dict, analise_estoque: Dict) -> Dict:
        """
        🎯 OTIMIZAÇÃO COMPLETA DE AGENDAMENTO
        
        Args:
            item: Instância de CarteiraPrincipal
            classificacao: Resultado da classificação (ClassificationEngine)
            analise_estoque: Resultado da análise de estoque (StockAnalyzer)
            
        Returns:
            Dict com otimização de agendamento
        """
        try:
            resultado = {
                'num_pedido': str(item.num_pedido),
                'cod_produto': str(item.cod_produto),
                'necessita_agendamento': self._verificar_necessidade_agendamento(item, classificacao),
                'protocolo_atual': getattr(item, 'protocolo', None),
                'data_entrega_atual': getattr(item, 'data_entrega_pedido', None),
                'data_expedicao_sugerida': analise_estoque.get('data_expedicao_sugerida'),
                'agendamento_otimizado': None,
                'protocolo_gerado': None,
                'justificativa': None,
                'conflitos_detectados': []
            }
            
            # 🎯 OTIMIZAR AGENDAMENTO
            if resultado['necessita_agendamento']:
                resultado['agendamento_otimizado'] = self._otimizar_data_agendamento(
                    item, classificacao, analise_estoque
                )
                
                # Gerar protocolo se necessário
                if not resultado['protocolo_atual']:
                    resultado['protocolo_gerado'] = self._gerar_protocolo_automatico(
                        item, resultado['agendamento_otimizado']
                    )
            
            # 📊 DEFINIR JUSTIFICATIVA
            resultado['justificativa'] = self._gerar_justificativa(resultado, classificacao, analise_estoque)
            
            # ⚠️ DETECTAR CONFLITOS
            resultado['conflitos_detectados'] = self._detectar_conflitos(resultado, analise_estoque)
            
            # 📅 ATUALIZAR CAMPOS DO ITEM
            self._atualizar_campos_agendamento(item, resultado)
            
            logger.debug(f"✅ Agendamento otimizado {item.num_pedido}-{item.cod_produto}")
            
            return resultado
            
        except Exception as e:
            logger.error(f"❌ Erro na otimização de agendamento {item.num_pedido}-{item.cod_produto}: {str(e)}")
            return self._otimizacao_erro(item)
    
    def _verificar_necessidade_agendamento(self, item, classificacao: Dict) -> bool:
        """
        📋 VERIFICAÇÃO DA NECESSIDADE DE AGENDAMENTO
        """
        # Verificar campo direto
        necessita_agendamento = getattr(item, 'cliente_nec_agendamento', None)
        if necessita_agendamento == 'Sim':
            return True
        
        # Verificar se é cliente estratégico
        if classificacao.get('tipo_cliente', {}).get('estrategico', False):
            return True
        
        # Verificar características especiais
        caracteristicas = classificacao.get('caracteristicas_especiais', [])
        if 'ALTO_VALOR' in caracteristicas:
            return True
        
        return False
    
    def _otimizar_data_agendamento(self, item, classificacao: Dict, analise_estoque: Dict) -> Dict:
        """
        📅 OTIMIZAÇÃO DA DATA DE AGENDAMENTO
        """
        try:
            # Dados base
            data_entrega_pedido = getattr(item, 'data_entrega_pedido', None)
            data_expedicao_sugerida = analise_estoque.get('data_expedicao_sugerida')
            urgencia = classificacao.get('classificacao_urgencia', {}).get('nivel', 'NORMAL')
            eh_estrategico = classificacao.get('tipo_cliente', {}).get('estrategico', False)
            
            # Determinar configuração do cliente
            if eh_estrategico:
                config_cliente = self.config_clientes['estrategico']
            elif getattr(item, 'cliente_nec_agendamento', None) == 'Sim':
                config_cliente = self.config_clientes['agendamento_obrigatorio']
            else:
                config_cliente = self.config_clientes['sem_agendamento']
            
            # Calcular janela de agendamento
            data_minima = data_expedicao_sugerida or date.today()
            data_maxima = data_entrega_pedido or (date.today() + timedelta(days=config_cliente['antecedencia_max']))
            
            # Ajustar para urgência
            if urgencia == 'CRITICO':
                data_maxima = min(data_maxima, date.today() + timedelta(days=3))
            elif urgencia == 'ATENCAO':
                data_maxima = min(data_maxima, date.today() + timedelta(days=5))
            
            # Encontrar melhor data
            melhor_data = self._encontrar_melhor_data_agendamento(
                data_minima, data_maxima, config_cliente
            )
            
            return {
                'data_agendamento_otimizada': melhor_data,
                'data_minima': data_minima,
                'data_maxima': data_maxima,
                'config_cliente': config_cliente,
                'horario_sugerido': self._sugerir_horario_agendamento(melhor_data, config_cliente) if melhor_data else None,
                'prioridade': config_cliente['prioridade'],
                'observacoes': self._gerar_observacoes_agendamento(item, melhor_data) if melhor_data else "Data de agendamento não disponível"
            }
            
        except Exception as e:
            logger.warning(f"Erro na otimização de data de agendamento: {str(e)}")
            return {
                'data_agendamento_otimizada': None,
                'erro': str(e)
            }
    
    def _encontrar_melhor_data_agendamento(self, data_minima: date, data_maxima: date, config_cliente: Dict) -> Optional[date]:
        """
        🔍 ENCONTRAR A MELHOR DATA DE AGENDAMENTO
        """
        try:
            # Iterar pelas datas possíveis
            data_atual = data_minima
            melhores_opcoes = []
            
            while data_atual <= data_maxima:
                # Verificar se é dia útil (se necessário)
                if self.config['dias_uteis_apenas']:
                    if data_atual.weekday() >= 5:  # Sábado=5, Domingo=6
                        data_atual += timedelta(days=1)
                        continue
                
                # Calcular score da data
                score = self._calcular_score_data(data_atual, config_cliente)
                
                melhores_opcoes.append({
                    'data': data_atual,
                    'score': score
                })
                
                data_atual += timedelta(days=1)
            
            # Ordenar por score e retornar a melhor
            if melhores_opcoes:
                melhores_opcoes.sort(key=lambda x: x['score'], reverse=True)
                return melhores_opcoes[0]['data']
            
            return None
            
        except Exception as e:
            logger.warning(f"Erro ao encontrar melhor data: {str(e)}")
            return None
    
    def _calcular_score_data(self, data: date, config_cliente: Dict) -> float:
        """
        📊 CÁLCULO DO SCORE DE UMA DATA
        """
        score = 100.0
        
        # Penalizar datas muito distantes
        dias_ate_data = (data - date.today()).days
        if dias_ate_data > 5:
            score -= (dias_ate_data - 5) * 10
        
        # Bonificar datas próximas para clientes estratégicos
        if config_cliente['prioridade'] == 1 and dias_ate_data <= 3:
            score += 20
        
        # Penalizar segunda-feira (muita demanda)
        if data.weekday() == 0:
            score -= 10
        
        # Bonificar quarta e quinta (menor demanda)
        if data.weekday() in [2, 3]:
            score += 10
        
        return score
    
    def _sugerir_horario_agendamento(self, data: date, config_cliente: Dict) -> str:
        """
        🕐 SUGESTÃO DE HORÁRIO DE AGENDAMENTO
        """
        # Clientes estratégicos têm prioridade no horário da manhã
        if config_cliente['prioridade'] == 1:
            return self.config['horarios_preferenciais'][0]  # 08:00-12:00
        
        # Outros clientes: distribuir entre os horários
        return random.choice(self.config['horarios_preferenciais'])
    
    def _gerar_observacoes_agendamento(self, item, data_agendamento: date) -> str:
        """
        📝 GERAÇÃO DE OBSERVAÇÕES DO AGENDAMENTO
        """
        observacoes = []
        
        # Informações básicas
        observacoes.append(f"Agendamento otimizado automaticamente")
        observacoes.append(f"Cliente: {getattr(item, 'raz_social_red', 'N/A')}")
        observacoes.append(f"Produto: {getattr(item, 'nome_produto', 'N/A')}")
        
        # Observações específicas do pedido
        observ_ped = getattr(item, 'observ_ped_1', '')
        if observ_ped:
            observacoes.append(f"Obs. Pedido: {observ_ped}")
        
        return " | ".join(observacoes)
    
    def _gerar_protocolo_automatico(self, item, agendamento_otimizado: Dict) -> str:
        """
        🔢 GERAÇÃO DE PROTOCOLO AUTOMÁTICO
        """
        try:
            # Gerar número sequencial
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            sufixo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))
            
            protocolo = f"{self.config['prefixo_protocolo']}{timestamp}{sufixo}"
            
            logger.info(f"📋 Protocolo gerado: {protocolo}")
            
            return protocolo
            
        except Exception as e:
            logger.warning(f"Erro na geração de protocolo: {str(e)}")
            return f"AGD{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    def _gerar_justificativa(self, resultado: Dict, classificacao: Dict, analise_estoque: Dict) -> str:
        """
        📝 GERAÇÃO DE JUSTIFICATIVA DA OTIMIZAÇÃO
        """
        justificativas = []
        
        # Justificativa por urgência
        urgencia = classificacao.get('classificacao_urgencia', {}).get('nivel', 'NORMAL')
        if urgencia == 'CRITICO':
            justificativas.append("Pedido CRÍTICO - prioridade máxima")
        elif urgencia == 'ATENCAO':
            justificativas.append("Pedido em atenção - prazo apertado")
        
        # Justificativa por estoque
        situacao_estoque = analise_estoque.get('situacao_estoque', '')
        if situacao_estoque == 'DISPONIVEL_SEGURO':
            justificativas.append("Estoque disponível - expedição imediata")
        elif situacao_estoque == 'AGUARDA_REPOSICAO_CURTA':
            justificativas.append("Aguardando reposição - agendamento programado")
        
        # Justificativa por cliente
        if classificacao.get('tipo_cliente', {}).get('estrategico', False):
            justificativas.append("Cliente estratégico - tratamento diferenciado")
        
        # Justificativa por características especiais
        caracteristicas = classificacao.get('caracteristicas_especiais', [])
        if 'ALTO_VALOR' in caracteristicas:
            justificativas.append("Pedido de alto valor - cuidado especial")
        
        return " | ".join(justificativas) if justificativas else "Otimização automática padrão"
    
    def _detectar_conflitos(self, resultado: Dict, analise_estoque: Dict) -> List[str]:
        """
        ⚠️ DETECÇÃO DE CONFLITOS DE AGENDAMENTO
        """
        conflitos = []
        
        try:
            # Conflito: Data de agendamento antes da disponibilidade de estoque
            if resultado.get('agendamento_otimizado'):
                data_agendamento = resultado['agendamento_otimizado'].get('data_agendamento_otimizada')
                data_expedicao = analise_estoque.get('data_expedicao_sugerida')
                
                if data_agendamento and data_expedicao and data_agendamento < data_expedicao:
                    conflitos.append("AGENDAMENTO_ANTES_ESTOQUE")
            
            # Conflito: Estoque em ruptura crítica
            if analise_estoque.get('situacao_estoque') == 'RUPTURA_CRITICA':
                conflitos.append("ESTOQUE_RUPTURA_CRITICA")
            
            # Conflito: Data de entrega pedido já vencida
            data_entrega_pedido = resultado.get('data_entrega_atual')
            if data_entrega_pedido and data_entrega_pedido < date.today():
                conflitos.append("PRAZO_ENTREGA_VENCIDO")
            
        except Exception as e:
            logger.warning(f"Erro na detecção de conflitos: {str(e)}")
            conflitos.append("ERRO_DETECCAO_CONFLITOS")
        
        return conflitos
    
    def _atualizar_campos_agendamento(self, item, resultado: Dict):
        """
        📅 ATUALIZAÇÃO DOS CAMPOS DE AGENDAMENTO NO ITEM
        """
        try:
            # Atualizar protocolo gerado
            if resultado.get('protocolo_gerado') and hasattr(item, 'protocolo'):
                item.protocolo = resultado['protocolo_gerado']
            
            # Atualizar campo agendamento
            if resultado.get('agendamento_otimizado') and hasattr(item, 'agendamento'):
                data_agendamento = resultado['agendamento_otimizado'].get('data_agendamento_otimizada')
                if data_agendamento:
                    item.agendamento = data_agendamento
            
            # Atualizar data de entrega se otimizada
            if resultado.get('agendamento_otimizado') and hasattr(item, 'data_entrega_pedido'):
                data_otimizada = resultado['agendamento_otimizado'].get('data_agendamento_otimizada')
                if data_otimizada and not item.data_entrega_pedido:
                    item.data_entrega_pedido = data_otimizada
            
        except Exception as e:
            logger.warning(f"Erro na atualização de campos de agendamento: {str(e)}")
    
    def _otimizacao_erro(self, item) -> Dict:
        """
        ❌ OTIMIZAÇÃO DE FALLBACK PARA ERROS
        """
        return {
            'num_pedido': str(getattr(item, 'num_pedido', 'N/A')),
            'cod_produto': str(getattr(item, 'cod_produto', 'N/A')),
            'necessita_agendamento': False,
            'protocolo_atual': None,
            'data_entrega_atual': None,
            'data_expedicao_sugerida': None,
            'agendamento_otimizado': None,
            'protocolo_gerado': None,
            'justificativa': 'Erro na otimização - processamento manual necessário',
            'conflitos_detectados': ['ERRO_OTIMIZACAO']
        }
    
    def otimizar_lote_agendamentos(self, itens_carteira: List, classificacoes: List, analises_estoque: List) -> Dict:
        """
        📊 OTIMIZAÇÃO EM LOTE DE AGENDAMENTOS
        
        Args:
            itens_carteira: Lista de instâncias CarteiraPrincipal
            classificacoes: Lista de classificações
            analises_estoque: Lista de análises de estoque
            
        Returns:
            Dict com otimizações e estatísticas
        """
        try:
            logger.info(f"🔄 Iniciando otimização de agendamentos para {len(itens_carteira)} itens")
            
            resultados = []
            estatisticas = {
                'total_itens': len(itens_carteira),
                'necessitam_agendamento': 0,
                'protocolos_gerados': 0,
                'conflitos_detectados': {},
                'distribuicao_por_data': {},
                'tempo_processamento': None
            }
            
            inicio = datetime.now()
            
            # Otimizar cada item
            for i, item in enumerate(itens_carteira):
                classificacao = classificacoes[i] if i < len(classificacoes) else {}
                analise_estoque = analises_estoque[i] if i < len(analises_estoque) else {}
                
                otimizacao = self.otimizar_agendamento_completo(item, classificacao, analise_estoque)
                resultados.append(otimizacao)
                
                # Atualizar estatísticas
                self._atualizar_estatisticas_lote(estatisticas, otimizacao)
            
            # Tempo de processamento
            fim = datetime.now()
            estatisticas['tempo_processamento'] = (fim - inicio).total_seconds()
            
            logger.info(f"✅ Otimização de agendamentos concluída em {estatisticas['tempo_processamento']:.2f}s")
            
            return {
                'resultados': resultados,
                'estatisticas': estatisticas,
                'sucesso': True
            }
            
        except Exception as e:
            logger.error(f"❌ Erro na otimização em lote de agendamentos: {str(e)}")
            return {
                'resultados': [],
                'estatisticas': {'erro': str(e)},
                'sucesso': False
            }
    
    def _atualizar_estatisticas_lote(self, stats: Dict, otimizacao: Dict):
        """
        📊 ATUALIZAÇÃO DAS ESTATÍSTICAS DO LOTE
        """
        # Contar agendamentos necessários
        if otimizacao['necessita_agendamento']:
            stats['necessitam_agendamento'] += 1
        
        # Contar protocolos gerados
        if otimizacao['protocolo_gerado']:
            stats['protocolos_gerados'] += 1
        
        # Contar conflitos
        for conflito in otimizacao['conflitos_detectados']:
            stats['conflitos_detectados'][conflito] = stats['conflitos_detectados'].get(conflito, 0) + 1
        
        # Distribuição por data
        if otimizacao.get('agendamento_otimizado'):
            data_agendamento = otimizacao['agendamento_otimizado'].get('data_agendamento_otimizada')
            if data_agendamento:
                data_str = data_agendamento.strftime('%Y-%m-%d')
                stats['distribuicao_por_data'][data_str] = stats['distribuicao_por_data'].get(data_str, 0) + 1 