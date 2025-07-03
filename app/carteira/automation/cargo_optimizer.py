# 🚛 OTIMIZADOR INTELIGENTE DE CARGAS
# Formação automática de embarques otimizados

from datetime import datetime, date, timedelta
from typing import Dict, List, Tuple, Optional
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

class CargoOptimizer:
    """
    🚛 Otimizador inteligente de formação de cargas
    
    FUNCIONALIDADES:
    - Formação automática de embarques otimizados
    - Consideração de lote_separacao_id para vinculação
    - Tratamento de cancelamentos de NFs
    - Detecção de inconsistências de faturamento
    - Geração de justificativas para cargas parciais
    - Otimização por peso, volume e capacidade de veículos
    """
    
    def __init__(self):
        # 🚛 CONFIGURAÇÕES DE OTIMIZAÇÃO DE CARGA
        self.config = {
            'peso_maximo_padrao': 27000.0,      # 27 toneladas padrão
            'volume_maximo_padrao': 80.0,       # 80m³ padrão
            'ocupacao_minima': 0.70,            # 70% ocupação mínima
            'ocupacao_ideal': 0.85,             # 85% ocupação ideal
            'max_paradas_rota': 5,              # Máximo 5 paradas por rota
            'tolerancia_peso': 0.05,            # 5% tolerância no peso
            'priorizar_agendamentos': True,     # Priorizar cargas com agendamento
        }
        
        # 📋 TIPOS DE CARGA E CARACTERÍSTICAS
        self.tipos_carga = {
            'TOTAL': {
                'descricao': 'Carga completa do pedido',
                'ocupacao_minima': 0.70,
                'justificativa_desnecessaria': True
            },
            'PARCIAL': {
                'descricao': 'Carga parcial do pedido',
                'ocupacao_minima': 0.60,
                'justificativa_obrigatoria': True
            },
            'FRACIONADA': {
                'descricao': 'Carga fracionada entre múltiplos embarques',
                'ocupacao_minima': 0.50,
                'justificativa_obrigatoria': True
            }
        }
        
        # ⚠️ MOTIVOS PARA CARGAS PARCIAIS
        self.motivos_carga_parcial = {
            'ESTOQUE_INSUFICIENTE': 'Estoque insuficiente para atender pedido completo',
            'CAPACIDADE_VEICULO': 'Capacidade do veículo não comporta pedido completo',
            'RESTRICAO_AGENDAMENTO': 'Restrição de agendamento impede carga total',
            'SEPARACAO_INCOMPLETA': 'Separação ainda não finalizada completamente',
            'CANCELAMENTO_PARCIAL': 'Cancelamento de parte das NFs do pedido',
            'INCONSISTENCIA_FATURAMENTO': 'Inconsistência detectada no faturamento',
            'CLIENTE_SOLICITOU': 'Solicitação específica do cliente',
            'URGENCIA_ENTREGA': 'Urgência na entrega - embarque parcial necessário'
        }
        
        logger.info("🚛 CargoOptimizer inicializado")
    
    def otimizar_formacao_carga(self, itens_carteira: List, classificacoes: List, 
                               analises_estoque: List, agendamentos: List) -> Dict:
        """
        🎯 OTIMIZAÇÃO COMPLETA DE FORMAÇÃO DE CARGAS
        
        Args:
            itens_carteira: Lista de instâncias CarteiraPrincipal
            classificacoes: Lista de classificações
            analises_estoque: Lista de análises de estoque  
            agendamentos: Lista de agendamentos otimizados
            
        Returns:
            Dict com otimização de cargas
        """
        try:
            logger.info(f"🔄 Iniciando otimização de cargas para {len(itens_carteira)} itens")
            
            resultado = {
                'cargas_otimizadas': [],
                'itens_processados': len(itens_carteira),
                'estatisticas': {
                    'total_cargas': 0,
                    'cargas_totais': 0,
                    'cargas_parciais': 0,
                    'justificativas_geradas': 0,
                    'inconsistencias_detectadas': 0,
                    'ocupacao_media': 0.0
                },
                'problemas_detectados': [],
                'tempo_processamento': None
            }
            
            inicio = datetime.now()
            
            # 📊 AGRUPAR ITENS POR CRITÉRIOS DE OTIMIZAÇÃO
            grupos_otimizacao = self._agrupar_itens_para_otimizacao(
                itens_carteira, classificacoes, analises_estoque, agendamentos
            )
            
            # 🚛 PROCESSAR CADA GRUPO
            for grupo in grupos_otimizacao:
                cargas_grupo = self._processar_grupo_otimizacao(grupo)
                resultado['cargas_otimizadas'].extend(cargas_grupo)
                
                # Atualizar estatísticas
                self._atualizar_estatisticas_cargas(resultado['estatisticas'], cargas_grupo)
            
            # 📊 FINALIZAR ESTATÍSTICAS
            resultado['estatisticas']['total_cargas'] = len(resultado['cargas_otimizadas'])
            if resultado['estatisticas']['total_cargas'] > 0:
                resultado['estatisticas']['ocupacao_media'] = (
                    sum(carga.get('ocupacao_percentual', 0) for carga in resultado['cargas_otimizadas']) /
                    resultado['estatisticas']['total_cargas']
                )
            
            # ⚠️ DETECTAR PROBLEMAS GLOBAIS
            resultado['problemas_detectados'] = self._detectar_problemas_globais(resultado)
            
            # Tempo de processamento
            fim = datetime.now()
            resultado['tempo_processamento'] = (fim - inicio).total_seconds()
            
            logger.info(f"✅ Otimização de cargas concluída em {resultado['tempo_processamento']:.2f}s")
            logger.info(f"📊 Resultado: {resultado['estatisticas']['total_cargas']} cargas, "
                      f"{resultado['estatisticas']['ocupacao_media']:.1f}% ocupação média")
            
            return resultado
            
        except Exception as e:
            logger.error(f"❌ Erro na otimização de cargas: {str(e)}")
            return {
                'cargas_otimizadas': [],
                'estatisticas': {'erro': str(e)},
                'problemas_detectados': ['ERRO_OTIMIZACAO'],
                'sucesso': False
            }
    
    def _agrupar_itens_para_otimizacao(self, itens_carteira: List, classificacoes: List,
                                     analises_estoque: List, agendamentos: List) -> List[Dict]:
        """
        📊 AGRUPAMENTO DE ITENS PARA OTIMIZAÇÃO DE CARGAS
        """
        try:
            # Agrupar por critérios de embarque
            grupos = defaultdict(list)
            
            for i, item in enumerate(itens_carteira):
                classificacao = classificacoes[i] if i < len(classificacoes) else {}
                analise_estoque = analises_estoque[i] if i < len(analises_estoque) else {}
                agendamento = agendamentos[i] if i < len(agendamentos) else {}
                
                # Determinar chave de agrupamento
                chave_grupo = self._determinar_chave_agrupamento(
                    item, classificacao, analise_estoque, agendamento
                )
                
                grupos[chave_grupo].append({
                    'item': item,
                    'classificacao': classificacao,
                    'analise_estoque': analise_estoque,
                    'agendamento': agendamento,
                    'indice': i
                })
            
            # Converter para lista de grupos
            grupos_lista = []
            for chave, itens_grupo in grupos.items():
                grupos_lista.append({
                    'chave_agrupamento': chave,
                    'itens': itens_grupo,
                    'total_itens': len(itens_grupo)
                })
            
            # Ordenar grupos por prioridade
            grupos_lista.sort(key=lambda g: self._calcular_prioridade_grupo(g), reverse=True)
            
            logger.info(f"📊 Criados {len(grupos_lista)} grupos de otimização")
            
            return grupos_lista
            
        except Exception as e:
            logger.error(f"❌ Erro no agrupamento de itens: {str(e)}")
            return []
    
    def _determinar_chave_agrupamento(self, item, classificacao: Dict, 
                                    analise_estoque: Dict, agendamento: Dict) -> str:
        """
        🔑 DETERMINAÇÃO DA CHAVE DE AGRUPAMENTO
        """
        # Componentes da chave
        componentes = []
        
        # 1. Data de expedição/agendamento
        if agendamento.get('agendamento_otimizado'):
            data_expedicao = agendamento['agendamento_otimizado'].get('data_agendamento_otimizada')
        else:
            data_expedicao = analise_estoque.get('data_expedicao_sugerida')
        
        if data_expedicao:
            componentes.append(f"DATA_{data_expedicao.strftime('%Y%m%d')}")
        else:
            componentes.append("DATA_INDEFINIDA")
        
        # 2. Região/Estado de destino
        estado = getattr(item, 'estado', 'XX')
        componentes.append(f"UF_{estado}")
        
        # 3. Prioridade da carga
        prioridade = classificacao.get('prioridade_geral', {}).get('nivel', 'MEDIA')
        componentes.append(f"PRIO_{prioridade}")
        
        # 4. Necessidade de agendamento
        necessita_agendamento = agendamento.get('necessita_agendamento', False)
        componentes.append(f"AGD_{necessita_agendamento}")
        
        # 5. Situação do estoque
        situacao_estoque = analise_estoque.get('situacao_estoque', 'INDEFINIDO')
        componentes.append(f"EST_{situacao_estoque}")
        
        return "_".join(componentes)
    
    def _calcular_prioridade_grupo(self, grupo: Dict) -> int:
        """
        📊 CÁLCULO DA PRIORIDADE DO GRUPO
        """
        score = 0
        
        # Prioridade por urgência
        for item_data in grupo['itens']:
            urgencia = item_data['classificacao'].get('classificacao_urgencia', {}).get('nivel', 'NORMAL')
            if urgencia == 'CRITICO':
                score += 100
            elif urgencia == 'ATENCAO':
                score += 50
        
        # Prioridade por agendamento
        if any(item_data['agendamento'].get('necessita_agendamento', False) 
               for item_data in grupo['itens']):
            score += 30
        
        # Prioridade por clientes estratégicos
        if any(item_data['classificacao'].get('tipo_cliente', {}).get('estrategico', False)
               for item_data in grupo['itens']):
            score += 20
        
        return score
    
    def _processar_grupo_otimizacao(self, grupo: Dict) -> List[Dict]:
        """
        🚛 PROCESSAMENTO DE UM GRUPO PARA OTIMIZAÇÃO
        """
        try:
            cargas_grupo = []
            itens_restantes = grupo['itens'][:]
            
            while itens_restantes:
                # Formar uma carga otimizada
                carga_otimizada = self._formar_carga_otimizada(itens_restantes)
                
                if carga_otimizada:
                    cargas_grupo.append(carga_otimizada)
                    
                    # Remover itens processados
                    itens_processados = carga_otimizada['itens_incluidos']
                    itens_restantes = [
                        item for item in itens_restantes 
                        if item['indice'] not in [ip['indice'] for ip in itens_processados]
                    ]
                else:
                    # Se não conseguiu formar carga, processar item individualmente
                    if itens_restantes:
                        carga_individual = self._formar_carga_individual(itens_restantes[0])
                        cargas_grupo.append(carga_individual)
                        itens_restantes.pop(0)
            
            logger.debug(f"✅ Grupo processado: {len(cargas_grupo)} cargas formadas")
            
            return cargas_grupo
            
        except Exception as e:
            logger.error(f"❌ Erro no processamento do grupo: {str(e)}")
            return []
    
    def _formar_carga_otimizada(self, itens_disponiveis: List[Dict]) -> Optional[Dict]:
        """
        🎯 FORMAÇÃO DE UMA CARGA OTIMIZADA
        """
        try:
            if not itens_disponiveis:
                return None
            
            # Inicializar carga
            carga = {
                'id_carga': f"CARGA_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'itens_incluidos': [],
                'peso_total': 0.0,
                'volume_total': 0.0,
                'valor_total': 0.0,
                'ocupacao_percentual': 0.0,
                'tipo_carga': 'TOTAL',
                'destinos': set(),
                'agendamentos_necessarios': False,
                'inconsistencias_detectadas': [],
                'justificativa_carga_parcial': None,
                'data_expedicao_prevista': None
            }
            
            # Ordenar itens por prioridade
            itens_ordenados = sorted(
                itens_disponiveis,
                key=lambda x: self._calcular_prioridade_item(x),
                reverse=True
            )
            
            # Adicionar itens à carga respeitando capacidades
            for item_data in itens_ordenados:
                if self._pode_adicionar_item_carga(carga, item_data):
                    self._adicionar_item_carga(carga, item_data)
                    
                    # Verificar se carga atingiu ocupação ideal
                    if carga['ocupacao_percentual'] >= self.config['ocupacao_ideal'] * 100:
                        break
            
            # Validar carga formada
            if not carga['itens_incluidos']:
                return None
            
            # 📊 FINALIZAR ANÁLISE DA CARGA
            self._finalizar_analise_carga(carga)
            
            return carga
            
        except Exception as e:
            logger.error(f"❌ Erro na formação de carga otimizada: {str(e)}")
            return None
    
    def _calcular_prioridade_item(self, item_data: Dict) -> int:
        """
        📊 CÁLCULO DA PRIORIDADE DE UM ITEM
        """
        score = 0
        
        # Prioridade por urgência
        urgencia = item_data['classificacao'].get('classificacao_urgencia', {}).get('nivel', 'NORMAL')
        scores_urgencia = {'CRITICO': 100, 'ATENCAO': 70, 'NORMAL': 50, 'SEM_PRAZO': 30}
        score += scores_urgencia.get(urgencia, 30)
        
        # Prioridade por agendamento
        if item_data['agendamento'].get('necessita_agendamento', False):
            score += 30
        
        # Prioridade por cliente estratégico
        if item_data['classificacao'].get('tipo_cliente', {}).get('estrategico', False):
            score += 20
        
        # Prioridade por valor
        if 'ALTO_VALOR' in item_data['classificacao'].get('caracteristicas_especiais', []):
            score += 15
        
        # Prioridade por disponibilidade de estoque
        situacao_estoque = item_data['analise_estoque'].get('situacao_estoque', '')
        if situacao_estoque == 'DISPONIVEL_SEGURO':
            score += 10
        
        return score
    
    def _pode_adicionar_item_carga(self, carga: Dict, item_data: Dict) -> bool:
        """
        ✅ VERIFICAÇÃO SE ITEM PODE SER ADICIONADO À CARGA
        """
        try:
            item = item_data['item']
            
            # Verificar peso
            peso_item = float(getattr(item, 'peso', 0) or 0)
            if carga['peso_total'] + peso_item > self.config['peso_maximo_padrao']:
                return False
            
            # Verificar compatibilidade de destino (mesmo estado)
            estado_item = getattr(item, 'estado', '')
            if carga['destinos'] and estado_item not in carga['destinos']:
                return False
            
            # Verificar compatibilidade de data de expedição
            data_expedicao_item = item_data['analise_estoque'].get('data_expedicao_sugerida')
            if carga['data_expedicao_prevista'] and data_expedicao_item:
                if abs((data_expedicao_item - carga['data_expedicao_prevista']).days) > 1:
                    return False
            
            # Verificar disponibilidade de estoque
            situacao_estoque = item_data['analise_estoque'].get('situacao_estoque', '')
            if situacao_estoque in ['RUPTURA_CRITICA', 'ERRO_ANALISE']:
                return False
            
            # Verificar lote de separação (se já vinculado)
            lote_separacao = getattr(item, 'lote_separacao_id', None)
            if lote_separacao:
                # Verificar se há conflito com outros lotes na carga
                lotes_carga = {
                    getattr(item_incluido['item'], 'lote_separacao_id', None)
                    for item_incluido in carga['itens_incluidos']
                    if getattr(item_incluido['item'], 'lote_separacao_id', None)
                }
                if lotes_carga and lote_separacao not in lotes_carga:
                    return False
            
            return True
            
        except Exception as e:
            logger.warning(f"Erro na verificação de adição de item: {str(e)}")
            return False
    
    def _adicionar_item_carga(self, carga: Dict, item_data: Dict):
        """
        ➕ ADIÇÃO DE ITEM À CARGA
        """
        try:
            item = item_data['item']
            
            # Adicionar item
            carga['itens_incluidos'].append(item_data)
            
            # Atualizar totais
            peso_item = float(getattr(item, 'peso', 0) or 0)
            valor_item = float(getattr(item, 'preco_produto_pedido', 0) or 0) * float(getattr(item, 'qtd_produto_pedido', 0) or 0)
            
            carga['peso_total'] += peso_item
            carga['valor_total'] += valor_item
            
            # Atualizar destinos
            estado_item = getattr(item, 'estado', '')
            if estado_item:
                carga['destinos'].add(estado_item)
            
            # Atualizar agendamentos
            if item_data['agendamento'].get('necessita_agendamento', False):
                carga['agendamentos_necessarios'] = True
            
            # Atualizar data de expedição
            data_expedicao_item = item_data['analise_estoque'].get('data_expedicao_sugerida')
            if data_expedicao_item and not carga['data_expedicao_prevista']:
                carga['data_expedicao_prevista'] = data_expedicao_item
            
            # Calcular ocupação percentual
            carga['ocupacao_percentual'] = (carga['peso_total'] / self.config['peso_maximo_padrao']) * 100
            
            # Detectar inconsistências
            inconsistencias = self._detectar_inconsistencias_item(item_data)
            if inconsistencias:
                carga['inconsistencias_detectadas'].extend(inconsistencias)
            
        except Exception as e:
            logger.warning(f"Erro na adição de item à carga: {str(e)}")
    
    def _detectar_inconsistencias_item(self, item_data: Dict) -> List[str]:
        """
        ⚠️ DETECÇÃO DE INCONSISTÊNCIAS NO ITEM
        """
        inconsistencias = []
        
        try:
            item = item_data['item']
            
            # Inconsistência: Quantidade zerada
            qtd_produto = float(getattr(item, 'qtd_produto_pedido', 0) or 0)
            if qtd_produto <= 0:
                inconsistencias.append(f"QUANTIDADE_ZERADA_{item.num_pedido}_{item.cod_produto}")
            
            # Inconsistência: Preço zerado
            preco_produto = float(getattr(item, 'preco_produto_pedido', 0) or 0)
            if preco_produto <= 0:
                inconsistencias.append(f"PRECO_ZERADO_{item.num_pedido}_{item.cod_produto}")
            
            # Inconsistência: Sem data de entrega em pedido crítico
            urgencia = item_data['classificacao'].get('classificacao_urgencia', {}).get('nivel', 'NORMAL')
            data_entrega = getattr(item, 'data_entrega_pedido', None)
            if urgencia == 'CRITICO' and not data_entrega:
                inconsistencias.append(f"CRITICO_SEM_DATA_{item.num_pedido}_{item.cod_produto}")
            
            # Inconsistência: Data de entrega vencida
            if data_entrega and data_entrega < date.today():
                inconsistencias.append(f"DATA_VENCIDA_{item.num_pedido}_{item.cod_produto}")
            
            # Inconsistência: Estoque em ruptura mas pedido ativo
            situacao_estoque = item_data['analise_estoque'].get('situacao_estoque', '')
            if situacao_estoque == 'RUPTURA_CRITICA':
                inconsistencias.append(f"RUPTURA_CRITICA_{item.num_pedido}_{item.cod_produto}")
            
        except Exception as e:
            logger.warning(f"Erro na detecção de inconsistências: {str(e)}")
            inconsistencias.append(f"ERRO_DETECCAO_{getattr(item, 'num_pedido', 'N/A')}")
        
        return inconsistencias
    
    def _finalizar_analise_carga(self, carga: Dict):
        """
        📊 FINALIZAÇÃO DA ANÁLISE DA CARGA
        """
        try:
            # Determinar tipo de carga
            carga['tipo_carga'] = self._determinar_tipo_carga(carga)
            
            # Gerar justificativa se necessário
            if carga['tipo_carga'] in ['PARCIAL', 'FRACIONADA']:
                carga['justificativa_carga_parcial'] = self._gerar_justificativa_carga_parcial(carga)
            
            # Converter destinos para lista
            carga['destinos'] = list(carga['destinos'])
            
            # Validar lote de separação
            carga['lote_separacao_vinculado'] = self._verificar_lote_separacao(carga)
            
            # Calcular métricas finais
            carga['total_pedidos'] = len(set(item_data['item'].num_pedido for item_data in carga['itens_incluidos']))
            carga['total_produtos'] = len(carga['itens_incluidos'])
            
        except Exception as e:
            logger.warning(f"Erro na finalização da análise da carga: {str(e)}")
    
    def _determinar_tipo_carga(self, carga: Dict) -> str:
        """
        🎯 DETERMINAÇÃO DO TIPO DE CARGA
        """
        try:
            # Verificar se todos os itens de todos os pedidos estão incluídos
            pedidos_na_carga = set(item_data['item'].num_pedido for item_data in carga['itens_incluidos'])
            
            # Para cada pedido, verificar se está completo
            cargas_parciais = 0
            for num_pedido in pedidos_na_carga:
                itens_pedido_carga = [
                    item_data for item_data in carga['itens_incluidos']
                    if item_data['item'].num_pedido == num_pedido
                ]
                
                # Verificar se há mais itens deste pedido fora da carga
                # (Isso seria determinado comparando com a carteira completa,
                # mas por simplicidade, assumimos com base na ocupação)
                if len(itens_pedido_carga) == 1 and carga['ocupacao_percentual'] < 70:
                    cargas_parciais += 1
            
            # Determinar tipo
            if cargas_parciais > 0:
                if carga['ocupacao_percentual'] < self.config['ocupacao_minima'] * 100:
                    return 'FRACIONADA'
                else:
                    return 'PARCIAL'
            else:
                return 'TOTAL'
                
        except Exception as e:
            logger.warning(f"Erro na determinação do tipo de carga: {str(e)}")
            return 'PARCIAL'
    
    def _gerar_justificativa_carga_parcial(self, carga: Dict) -> str:
        """
        📝 GERAÇÃO DE JUSTIFICATIVA PARA CARGA PARCIAL
        """
        justificativas = []
        
        try:
            # Justificativa por ocupação baixa
            if carga['ocupacao_percentual'] < self.config['ocupacao_minima'] * 100:
                justificativas.append(self.motivos_carga_parcial['CAPACIDADE_VEICULO'])
            
            # Justificativa por inconsistências
            if carga['inconsistencias_detectadas']:
                justificativas.append(self.motivos_carga_parcial['INCONSISTENCIA_FATURAMENTO'])
            
            # Justificativa por agendamento
            if carga['agendamentos_necessarios']:
                justificativas.append(self.motivos_carga_parcial['RESTRICAO_AGENDAMENTO'])
            
            # Justificativa por urgência
            urgencias_criticas = [
                item_data['classificacao'].get('classificacao_urgencia', {}).get('nivel', 'NORMAL')
                for item_data in carga['itens_incluidos']
            ]
            if 'CRITICO' in urgencias_criticas:
                justificativas.append(self.motivos_carga_parcial['URGENCIA_ENTREGA'])
            
            # Justificativa por estoque
            situacoes_estoque = [
                item_data['analise_estoque'].get('situacao_estoque', '')
                for item_data in carga['itens_incluidos']
            ]
            if any(situacao in ['DISPONIVEL_LIMITADO', 'AGUARDA_REPOSICAO_CURTA'] for situacao in situacoes_estoque):
                justificativas.append(self.motivos_carga_parcial['ESTOQUE_INSUFICIENTE'])
            
            # Justificativa por separação
            lotes_separacao = [
                getattr(item_data['item'], 'lote_separacao_id', None)
                for item_data in carga['itens_incluidos']
            ]
            if any(lote is None for lote in lotes_separacao):
                justificativas.append(self.motivos_carga_parcial['SEPARACAO_INCOMPLETA'])
            
            # Retornar justificativa consolidada
            if justificativas:
                return " | ".join(set(justificativas))  # Remove duplicatas
            else:
                return "Carga parcial necessária - múltiplos fatores operacionais"
                
        except Exception as e:
            logger.warning(f"Erro na geração de justificativa: {str(e)}")
            return "Erro na geração de justificativa - análise manual necessária"
    
    def _verificar_lote_separacao(self, carga: Dict) -> Optional[str]:
        """
        🔗 VERIFICAÇÃO DE LOTE DE SEPARAÇÃO VINCULADO
        """
        try:
            lotes_separacao = [
                getattr(item_data['item'], 'lote_separacao_id', None)
                for item_data in carga['itens_incluidos']
                if getattr(item_data['item'], 'lote_separacao_id', None)
            ]
            
            if lotes_separacao:
                # Se todos têm o mesmo lote, retornar
                lotes_unicos = set(lotes_separacao)
                if len(lotes_unicos) == 1:
                    return list(lotes_unicos)[0]
                elif len(lotes_unicos) > 1:
                    return f"MULTIPLOS_LOTES_{len(lotes_unicos)}"
            
            return None
            
        except Exception as e:
            logger.warning(f"Erro na verificação de lote de separação: {str(e)}")
            return None
    
    def _formar_carga_individual(self, item_data: Dict) -> Dict:
        """
        👤 FORMAÇÃO DE CARGA INDIVIDUAL (FALLBACK)
        """
        try:
            item = item_data['item']
            
            carga = {
                'id_carga': f"INDIVIDUAL_{item.num_pedido}_{item.cod_produto}_{datetime.now().strftime('%H%M%S')}",
                'itens_incluidos': [item_data],
                'peso_total': float(getattr(item, 'peso', 0) or 0),
                'volume_total': 0.0,
                'valor_total': float(getattr(item, 'preco_produto_pedido', 0) or 0) * float(getattr(item, 'qtd_produto_pedido', 0) or 0),
                'ocupacao_percentual': (float(getattr(item, 'peso', 0) or 0) / self.config['peso_maximo_padrao']) * 100,
                'tipo_carga': 'INDIVIDUAL',
                'destinos': [getattr(item, 'estado', 'XX')],
                'agendamentos_necessarios': item_data['agendamento'].get('necessita_agendamento', False),
                'inconsistencias_detectadas': self._detectar_inconsistencias_item(item_data),
                'justificativa_carga_parcial': "Carga individual - não foi possível otimizar com outros itens",
                'data_expedicao_prevista': item_data['analise_estoque'].get('data_expedicao_sugerida'),
                'lote_separacao_vinculado': getattr(item, 'lote_separacao_id', None),
                'total_pedidos': 1,
                'total_produtos': 1
            }
            
            return carga
            
        except Exception as e:
            logger.error(f"❌ Erro na formação de carga individual: {str(e)}")
            return {}
    
    def _atualizar_estatisticas_cargas(self, stats: Dict, cargas: List[Dict]):
        """
        📊 ATUALIZAÇÃO DAS ESTATÍSTICAS DE CARGAS
        """
        for carga in cargas:
            # Contar por tipo
            tipo_carga = carga.get('tipo_carga', 'INDIVIDUAL')
            if tipo_carga in ['TOTAL', 'INDIVIDUAL']:
                stats['cargas_totais'] += 1
            else:
                stats['cargas_parciais'] += 1
            
            # Contar justificativas
            if carga.get('justificativa_carga_parcial'):
                stats['justificativas_geradas'] += 1
            
            # Contar inconsistências
            if carga.get('inconsistencias_detectadas'):
                stats['inconsistencias_detectadas'] += len(carga['inconsistencias_detectadas'])
    
    def _detectar_problemas_globais(self, resultado: Dict) -> List[str]:
        """
        ⚠️ DETECÇÃO DE PROBLEMAS GLOBAIS
        """
        problemas = []
        
        try:
            stats = resultado['estatisticas']
            
            # Muitas cargas parciais
            if stats['cargas_parciais'] > stats['cargas_totais']:
                problemas.append("EXCESSO_CARGAS_PARCIAIS")
            
            # Muitas inconsistências
            if stats['inconsistencias_detectadas'] > stats['total_cargas'] * 0.1:
                problemas.append("EXCESSO_INCONSISTENCIAS")
            
            # Ocupação muito baixa
            if stats['ocupacao_media'] < self.config['ocupacao_minima'] * 100:
                problemas.append("OCUPACAO_BAIXA_GERAL")
            
            # Poucas cargas formadas
            if stats['total_cargas'] == 0:
                problemas.append("NENHUMA_CARGA_FORMADA")
            
        except Exception as e:
            logger.warning(f"Erro na detecção de problemas globais: {str(e)}")
            problemas.append("ERRO_DETECCAO_PROBLEMAS")
        
        return problemas 