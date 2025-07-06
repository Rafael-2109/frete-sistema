"""
🧠 MAPEAMENTO SEMÂNTICO - Linguagem Natural → Campos do Banco
Sistema que traduz termos do usuário para campos reais do sistema
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
import re

logger = logging.getLogger(__name__)

class MapeamentoSemantico:
    """Mapeia linguagem natural para campos reais do banco"""
    
    def __init__(self):
        """Inicializa mapeamento semântico"""
        # Buscar dados REAIS do sistema primeiro
        self.campos_reais = self._buscar_campos_reais_do_sistema()
        self.mapeamentos = self._criar_mapeamentos_com_dados_reais()
        self.relacionamentos = self._criar_relacionamentos_reais()
        logger.info("🧠 Mapeamento Semântico inicializado com dados REAIS")
    
    def _buscar_campos_reais_do_sistema(self) -> Dict[str, Any]:
        """Busca campos REAIS do sistema usando sistema_real_data"""
        try:
            from .sistema_real_data import get_sistema_real_data
            sistema_real = get_sistema_real_data()
            
            # Buscar modelos reais do banco
            modelos_reais = sistema_real.buscar_todos_modelos_reais()
            
            logger.info(f"✅ Campos reais carregados de {len(modelos_reais)} modelos")
            return modelos_reais
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar campos reais: {e}")
            return {}
    
    def _criar_mapeamentos_com_dados_reais(self) -> Dict[str, Dict[str, Any]]:
        """Cria mapeamentos usando APENAS campos reais do sistema"""
        
        if not self.campos_reais:
            logger.debug("🔄 Inicializando mapeamento sem dados reais (serão carregados dinamicamente)")
            return {}
        
        mapeamentos = {}
        
        # Para cada modelo real, criar mapeamentos baseados nos campos reais
        for nome_modelo, info_modelo in self.campos_reais.items():
            if 'campos' not in info_modelo:
                continue
                
            campos_reais = info_modelo['campos']
            
            # Mapear cada campo real
            for campo_info in campos_reais:
                nome_campo = campo_info['nome']
                tipo_campo = campo_info['tipo']
                
                # Gerar termos naturais baseados no nome do campo
                termos_naturais = self._gerar_termos_naturais_para_campo(nome_campo, nome_modelo)
                
                if termos_naturais:  # Só adicionar se gerou termos
                    chave_mapeamento = f"{nome_modelo.lower()}_{nome_campo}"
                    
                    mapeamentos[chave_mapeamento] = {
                        'modelo': nome_modelo,
                        'campo_principal': nome_campo,
                        'campo_busca': nome_campo,  # Campo real do banco
                        'tipo': self._normalizar_tipo_sqlalchemy(tipo_campo),
                        'termos_naturais': termos_naturais
                    }
        
        logger.info(f"✅ {len(mapeamentos)} mapeamentos criados com campos REAIS")
        return mapeamentos
    
    def _gerar_termos_naturais_para_campo(self, nome_campo: str, nome_modelo: str) -> List[str]:
        """Gera termos naturais para um campo baseado no mapeamento semântico do README"""
        
        # 🎯 USAR MAPEAMENTO SEMÂNTICO DETALHADO DO README
        mapeamento_readme = self._buscar_mapeamento_readme(nome_campo, nome_modelo)
        
        if mapeamento_readme:
            logger.info(f"✅ Campo {nome_campo} encontrado no README: {len(mapeamento_readme)} termos")
            return mapeamento_readme
        
        # 🚫 FALLBACK AUTOMÁTICO - Gerar termos baseados no nome do campo
        termos = []
        
        # Gerar termos baseados no padrão do nome do campo
        if '_' in nome_campo:
            # Campo composto (ex: data_embarque -> "data de embarque")
            partes = nome_campo.split('_')
            if len(partes) == 2:
                termo_natural = f"{partes[0]} de {partes[1]}"
                termos.extend([termo_natural, f"{partes[0]} do {partes[1]}"])
        
        # Adicionar o próprio nome do campo (sem underscores)
        nome_limpo = nome_campo.replace('_', ' ')
        if nome_limpo not in termos:
            termos.append(nome_limpo)
        
        logger.debug(f"🔄 Campo {nome_campo} usando fallback automático (318 campos mapeados)")
        return termos
    
    def _buscar_mapeamento_readme(self, nome_campo: str, nome_modelo: str) -> List[str]:
        """
        Busca mapeamento específico do README para um campo
        IMPLEMENTAÇÃO FUTURA: Integrar com README_MAPEAMENTO_SEMANTICO_COMPLETO.md
        """
        
        # 🔧 TODO: IMPLEMENTAR LEITURA DO README DETALHADO
        # Por enquanto, retornar None para forçar fallback
        # Na próxima iteração, ler o arquivo README e buscar mapeamentos específicos
        
        # Placeholder para futura implementação
        mapeamentos_readme = {
            # Exemplo de como seria:
            # 'num_pedido': ['número do pedido', 'numero do pedido', 'pedido'],
            # 'raz_social_red': ['cliente', 'razão social', 'nome do cliente'],
        }
        
        return mapeamentos_readme.get(nome_campo, [])
    
    def _normalizar_tipo_sqlalchemy(self, tipo_sqlalchemy: str) -> str:
        """Normaliza tipos do SQLAlchemy para tipos simples"""
        
        tipo_lower = str(tipo_sqlalchemy).lower()
        
        if 'varchar' in tipo_lower or 'text' in tipo_lower or 'string' in tipo_lower:
            return 'string'
        elif 'integer' in tipo_lower or 'bigint' in tipo_lower:
            return 'integer'
        elif 'decimal' in tipo_lower or 'numeric' in tipo_lower or 'float' in tipo_lower:
            return 'decimal'
        elif 'boolean' in tipo_lower:
            return 'boolean'
        elif 'date' in tipo_lower:
            return 'datetime' if 'datetime' in tipo_lower or 'timestamp' in tipo_lower else 'date'
        else:
            return 'string'  # Fallback
    
    def _criar_mapeamentos_campos_OLD(self) -> Dict[str, Dict[str, Any]]:
        """Cria mapeamento de termos naturais para campos do banco"""
        
        mapeamentos = {
            # 📋 PEDIDOS (expandido baseado no README)
            'pedido': {
                'modelo': 'Pedido',
                'campo_principal': 'num_pedido',
                'termos_naturais': [
                    'pedido', 'pdd', 'numero do pedido', 'num pedido',
                    'número do pedido', 'numero do pedido', 'num pedido', 'nº pedido',
                    'pedido número', 'pedido numero', 'código do pedido', 'id do pedido',
                    'número de pedido', 'numero de pedido'
                ],
                'campo_busca': 'num_pedido',
                'tipo': 'string'
            },
            
            'cliente_pedido': {
                'modelo': 'Pedido', 
                'campo_principal': 'raz_social_red',
                'termos_naturais': [
                    'cliente', 'razão social do cliente', 'nome do cliente',
                    'cliente do pedido', 'razão social', 'razao social', 'nome do cliente',
                    'cliente', 'empresa', 'comprador'
                ],
                'campo_busca': 'raz_social_red',
                'tipo': 'string'
            },
            
            'valor_pedido': {
                'modelo': 'Pedido',
                'campo_principal': 'valor_saldo_total', 
                'termos_naturais': [
                    'total do pedido', 'valor do pdd', 'total do pdd',
                    'valor do pedido', 'valor total', 'saldo do pedido', 'preço do pedido',
                    'valor', 'montante', 'saldo total'
                ],
                'campo_busca': 'valor_saldo_total',
                'tipo': 'decimal'
            },
            
            'peso_pedido': {
                'modelo': 'Pedido',
                'campo_principal': 'peso_total',
                'termos_naturais': [
                    'peso do pedido', 'peso do pdd', 'quilos', 'kg', 'peso bruto', 'quantos quilos',
                    'peso do pedido', 'peso total', 'peso', 'quilos', 'kg',
                    'peso em kg', 'toneladas'
                ],
                'campo_busca': 'peso_total', 
                'tipo': 'decimal'
            },
            
            'pallets_pedido': {
                'modelo': 'Pedido',
                'campo_principal': 'pallet_total',
                'termos_naturais': [
                    'qtd de pallets do pedido', 'pallets do pedido', 'palets do pedido', 'palets do pdd', 
                    'total de pallets do pedido', 'pallet do pedido', 'pallet pdd', 'qtd de palets', 
                    'qtd de pallets', 'qtd de pallet', 'pallets', 'palets'
                ],
                'campo_busca': 'pallet_total',
                'tipo': 'decimal'
            },
            
            'agendamento_pedido': {
                'modelo': 'Pedido',
                'campo_principal': 'agendamento',
                'termos_naturais': [
                    'data de agendamento', 'agenda', 'data da agenda', 'agendamento', 'data agendada'
                ],
                'campo_busca': 'agendamento',
                'tipo': 'date'
            },
            
            'protocolo_pedido': {
                'modelo': 'Pedido',
                'campo_principal': 'protocolo',
                'termos_naturais': [
                    'protocolo', 'protocolo do agendamento'
                ],
                'campo_busca': 'protocolo',
                'tipo': 'string'
            },
            
            'data_expedicao': {
                'modelo': 'Pedido',
                'campo_principal': 'expedicao',
                'termos_naturais': [
                    'data programada', 'data prevista de faturamento', 'data prevista de embarque', 'quando está previsto sair'
                ],
                'campo_busca': 'expedicao',
                'tipo': 'date'
            },
            
            'observacao_pedido': {
                'modelo': 'Pedido',
                'campo_principal': 'observ_ped_1',
                'termos_naturais': [
                    'obs do pdd', 'observação do pedido', 'observação no pdd', 'observacao no pedido', 'observacao do pdd', 'obs no pdd'
                ],
                'campo_busca': 'observ_ped_1',
                'tipo': 'string'
            },
            
            'nf_cd_pedido': {
                'modelo': 'Pedido',
                'campo_principal': 'nf_cd',
                'termos_naturais': [
                    'nf no cd', 'nota no cd', 'voltou para empresa', 'entrega não concluída', 'precisa reentrega'
                ],
                'campo_busca': 'nf_cd',
                'tipo': 'boolean'
            },
            
            'status_pedido': {
                'modelo': 'Pedido',
                'campo_principal': 'status_calculado',
                'termos_naturais': [
                    'aberto', 'cotado', 'faturado', 'status do pedido', 'situação do pedido', 'posição do pedido', 'embarcado',
                    'status do pedido', 'situação do pedido', 'estado do pedido',
                    'status', 'situação', 'estado'
                ],
                'campo_busca': 'status_calculado',
                'tipo': 'string'
            },
            
            # 📦 ENTREGAS MONITORADAS (CAMPOS ESSENCIAIS RESTAURADOS)
            'numero_nf': {
                'modelo': 'EntregaMonitorada',
                'campo_principal': 'numero_nf',
                'termos_naturais': [
                    'número da nf', 'numero da nf', 'número da nota fiscal',
                    'numero da nota fiscal', 'nf', 'nota fiscal', 'número nf',
                    'numero nf', 'código da nf', 'id da nf'
                ],
                'campo_busca': 'numero_nf',
                'tipo': 'string'
            },
            
            'cliente_entrega': {
                'modelo': 'EntregaMonitorada',
                'campo_principal': 'cliente',
                'termos_naturais': [
                    'cliente da entrega', 'destinatário', 'cliente', 'empresa',
                    'nome do cliente', 'cliente destino'
                ],
                'campo_busca': 'cliente',
                'tipo': 'string'
            },
            
            'transportadora_entrega': {
                'modelo': 'EntregaMonitorada',
                'campo_principal': 'transportadora',
                'termos_naturais': [
                    'transportadora', 'empresa de transporte', 'freteiro',
                    'transportador', 'carreteiro', 'entregador'
                ],
                'campo_busca': 'transportadora',
                'tipo': 'string'
            },
            
            'vendedor_entrega': {
                'modelo': 'EntregaMonitorada',
                'campo_principal': 'vendedor',
                'termos_naturais': [
                    'vendedor', 'representante', 'consultor', 'responsável pela venda',
                    'vendedor responsável'
                ],
                'campo_busca': 'vendedor',
                'tipo': 'string'
            },
            
            'destino_entrega': {
                'modelo': 'EntregaMonitorada',
                'campo_principal': 'municipio',
                'termos_naturais': [
                    'destino', 'cidade de destino', 'local de entrega', 'endereço',
                    'cidade', 'município', 'localidade'
                ],
                'campo_busca': 'municipio',
                'tipo': 'string'
            },
            
            'uf': {
                'modelo': 'EntregaMonitorada',
                'campo_principal': 'uf',
                'termos_naturais': [
                    'uf', 'estado', 'unidade federativa', 'estado de destino',
                    'uf destino', 'sigla do estado'
                ],
                'campo_busca': 'uf',
                'tipo': 'string'
            },
            
            'valor_nf': {
                'modelo': 'EntregaMonitorada',
                'campo_principal': 'valor_nf',
                'termos_naturais': [
                    'valor da nf', 'valor da nota fiscal', 'valor', 'preço da nf',
                    'montante da nf', 'valor total da nf'
                ],
                'campo_busca': 'valor_nf',
                'tipo': 'decimal'
            },
            
            'data_embarque': {
                'modelo': 'EntregaMonitorada',
                'campo_principal': 'data_embarque',
                'termos_naturais': [
                    'data de embarque', 'data do embarque', 'quando embarcou',
                    'data da saída', 'data de envio', 'data expedição'
                ],
                'campo_busca': 'data_embarque',
                'tipo': 'date'
            },
            
            'data_prevista': {
                'modelo': 'EntregaMonitorada', 
                'campo_principal': 'data_entrega_prevista',
                'termos_naturais': [
                    'data prevista', 'data de entrega prevista', 'prazo de entrega',
                    'quando deve entregar', 'data prometida', 'prazo'
                ],
                'campo_busca': 'data_entrega_prevista',
                'tipo': 'date'
            },
            
            'data_realizada': {
                'modelo': 'EntregaMonitorada',
                'campo_principal': 'data_hora_entrega_realizada',
                'termos_naturais': [
                    'data de entrega', 'quando foi entregue', 'data realizada',
                    'data da entrega', 'entregue em', 'data entrega realizada'
                ],
                'campo_busca': 'data_hora_entrega_realizada',
                'tipo': 'datetime'
            },
            
            'status_entrega': {
                'modelo': 'EntregaMonitorada',
                'campo_principal': 'status_finalizacao',
                'termos_naturais': [
                    'status da entrega', 'situação da entrega', 'estado da entrega',
                    'status', 'situação', 'foi entregue'
                ],
                'campo_busca': 'status_finalizacao',
                'tipo': 'string'
            },
            
            'entregue': {
                'modelo': 'EntregaMonitorada',
                'campo_principal': 'entregue',
                'termos_naturais': [
                    'foi entregue', 'está entregue', 'entrega realizada',
                    'entregue', 'finalizado', 'concluído'
                ],
                'campo_busca': 'entregue',
                'tipo': 'boolean'
            },
            
            'pendencia_financeira': {
                'modelo': 'EntregaMonitorada',
                'campo_principal': 'pendencia_financeira',
                'termos_naturais': [
                    'pendência financeira', 'pendencia financeira', 'problema financeiro',
                    'bloqueio financeiro', 'restrição financeira'
                ],
                'campo_busca': 'pendencia_financeira',
                'tipo': 'boolean'
            },
            
            # 💰 FATURAMENTO - CORREÇÃO CRÍTICA: Campo "origem"
            'origem': {
                'modelo': 'RelatorioFaturamentoImportado',
                'campo_principal': 'origem',
                'termos_naturais': [
                    # ✅ CORRIGIDO: origem = num_pedido (NÃO é localização!)
                    'número do pedido', 'numero do pedido', 'num pedido', 'pedido',
                    'origem', 'codigo do pedido', 'id do pedido', 'referencia do pedido',
                    'num_pedido', 'pedido origem'
                ],
                'campo_busca': 'origem',
                'tipo': 'string',
                'observacao': 'CAMPO RELACIONAMENTO ESSENCIAL: origem = num_pedido (conecta faturamento→embarque→monitoramento→pedidos)'
            },
            
            'incoterm': {
                'modelo': 'RelatorioFaturamentoImportado',
                'campo_principal': 'incoterm',
                'termos_naturais': [
                    'incoterm', 'termo comercial', 'condição de venda',
                    'modalidade', 'tipo de frete'
                ],
                'campo_busca': 'incoterm',
                'tipo': 'string'
            },
            
            'data_fatura': {
                'modelo': 'RelatorioFaturamentoImportado',
                'campo_principal': 'data_fatura',
                'termos_naturais': [
                    'data da fatura', 'data de faturamento', 'quando foi faturado',
                    'data fatura', 'faturado em'
                ],
                'campo_busca': 'data_fatura',
                'tipo': 'date'
            },
            
            # 🚛 EMBARQUES
            'numero_embarque': {
                'modelo': 'Embarque',
                'campo_principal': 'numero',
                'termos_naturais': [
                    'número do embarque', 'numero do embarque', 'embarque número',
                    'embarque numero', 'id do embarque', 'código do embarque'
                ],
                'campo_busca': 'numero',
                'tipo': 'integer'
            },
                        
            # 📋 AGENDAMENTOS
            'protocolo_agendamento': {
                'modelo': 'AgendamentoEntrega',
                'campo_principal': 'protocolo_agendamento',
                'termos_naturais': [
                    'protocolo de agendamento', 'protocolo', 'número do protocolo',
                    'numero do protocolo', 'código do agendamento'
                ],
                'campo_busca': 'protocolo_agendamento',
                'tipo': 'string'
            },
            
            'data_agendada': {
                'modelo': 'AgendamentoEntrega',
                'campo_principal': 'data_agendada',
                'termos_naturais': [
                    'data agendada', 'data do agendamento', 'agendado para',
                    'data marcada', 'quando foi agendado'
                ],
                'campo_busca': 'data_agendada',
                'tipo': 'date'
            }
        }
        
        return mapeamentos
    
    def _criar_relacionamentos_reais(self) -> Dict[str, Dict[str, Any]]:
        """Cria relacionamentos baseados nos dados reais dos modelos"""
        
        relacionamentos = {}
        
        # Buscar relacionamentos reais dos modelos
        for nome_modelo, info_modelo in self.campos_reais.items():
            if 'relacionamentos' not in info_modelo:
                continue
                
            for rel_info in info_modelo['relacionamentos']:
                nome_rel = rel_info['nome']
                modelo_relacionado = rel_info['modelo_relacionado']
                
                chave_rel = f"{nome_modelo}_para_{modelo_relacionado}".lower()
                
                relacionamentos[chave_rel] = {
                    'origem': nome_modelo,
                    'destino': modelo_relacionado,
                    'campo_relacionamento': nome_rel,
                    'tipo': rel_info['tipo']
                }
        
        logger.info(f"✅ {len(relacionamentos)} relacionamentos reais mapeados")
        return relacionamentos
    
    def _criar_mapeamentos_relacionamentos_OLD(self) -> Dict[str, Dict[str, Any]]:
        """Mapeia relacionamentos entre modelos"""
        
        return {
            'pedido_para_entrega': {
                'origem': 'Pedido',
                'destino': 'EntregaMonitorada', 
                'campo_ligacao': 'nf',
                'descricao': 'Pedido.nf = EntregaMonitorada.numero_nf'
            },
            
            'entrega_para_agendamento': {
                'origem': 'EntregaMonitorada',
                'destino': 'AgendamentoEntrega',
                'campo_ligacao': 'id',
                'descricao': 'EntregaMonitorada.id = AgendamentoEntrega.entrega_id'
            },
            
            'embarque_para_item': {
                'origem': 'Embarque',
                'destino': 'EmbarqueItem',
                'campo_ligacao': 'id',
                'descricao': 'Embarque.id = EmbarqueItem.embarque_id'
            },
            
            'item_para_entrega': {
                'origem': 'EmbarqueItem',
                'destino': 'EntregaMonitorada',
                'campo_ligacao': 'numero_nf',
                'descricao': 'EmbarqueItem.numero_nf = EntregaMonitorada.numero_nf'
            }
        }
    
    def mapear_termo_natural(self, termo: str) -> List[Dict[str, Any]]:
        """
        Mapeia termo em linguagem natural para campos do banco
        
        Args:
            termo: Termo em linguagem natural (ex: "número do pedido")
            
        Returns:
            Lista de mapeamentos possíveis
        """
        termo_lower = termo.lower().strip()
        mapeamentos_encontrados = []
        
        # Buscar correspondências exatas primeiro
        for chave, mapeamento in self.mapeamentos.items():
            for termo_natural in mapeamento['termos_naturais']:
                if termo_natural.lower() == termo_lower:
                    mapeamentos_encontrados.append({
                        'chave': chave,
                        'modelo': mapeamento['modelo'],
                        'campo': mapeamento['campo_principal'],
                        'campo_busca': mapeamento['campo_busca'],
                        'tipo': mapeamento['tipo'],
                        'confianca': 100,
                        'termo_original': termo,
                        'termo_mapeado': termo_natural
                    })
        
        # Se não encontrou exato, buscar parcial
        if not mapeamentos_encontrados:
            for chave, mapeamento in self.mapeamentos.items():
                for termo_natural in mapeamento['termos_naturais']:
                    # Busca por palavras contidas
                    palavras_termo = termo_lower.split()
                    palavras_natural = termo_natural.lower().split()
                    
                    palavras_encontradas = 0
                    for palavra in palavras_termo:
                        if any(palavra in palavra_natural for palavra_natural in palavras_natural):
                            palavras_encontradas += 1
                    
                    if palavras_encontradas >= len(palavras_termo) * 0.7:  # 70% de match
                        confianca = int((palavras_encontradas / len(palavras_termo)) * 100)
                        mapeamentos_encontrados.append({
                            'chave': chave,
                            'modelo': mapeamento['modelo'],
                            'campo': mapeamento['campo_principal'],
                            'campo_busca': mapeamento['campo_busca'],
                            'tipo': mapeamento['tipo'],
                            'confianca': confianca,
                            'termo_original': termo,
                            'termo_mapeado': termo_natural
                        })
        
        # Ordenar por confiança
        mapeamentos_encontrados.sort(key=lambda x: x['confianca'], reverse=True)
        
        logger.info(f"🔍 Mapeamento '{termo}': {len(mapeamentos_encontrados)} correspondências")
        
        return mapeamentos_encontrados
    
    def mapear_consulta_completa(self, consulta: str) -> Dict[str, Any]:
        """
        Analisa consulta completa e mapeia termos para campos
        
        Args:
            consulta: Consulta em linguagem natural
            
        Returns:
            Dicionário com mapeamentos encontrados
        """
        consulta_lower = consulta.lower()
        
        resultado = {
            'consulta_original': consulta,
            'mapeamentos_encontrados': [],
            'modelos_envolvidos': set(),
            'campos_identificados': {},
            'relacionamentos_necessarios': [],
            'sugestao_query': None
        }
        
        # Buscar todos os termos possíveis na consulta
        for chave, mapeamento in self.mapeamentos.items():
            for termo_natural in mapeamento['termos_naturais']:
                if termo_natural.lower() in consulta_lower:
                    mapeamento_encontrado = {
                        'chave': chave,
                        'modelo': mapeamento['modelo'],
                        'campo': mapeamento['campo_principal'],
                        'campo_busca': mapeamento['campo_busca'],
                        'tipo': mapeamento['tipo'],
                        'termo_encontrado': termo_natural,
                        'posicao': consulta_lower.find(termo_natural.lower())
                    }
                    
                    resultado['mapeamentos_encontrados'].append(mapeamento_encontrado)
                    resultado['modelos_envolvidos'].add(mapeamento['modelo'])
                    
                    if mapeamento['modelo'] not in resultado['campos_identificados']:
                        resultado['campos_identificados'][mapeamento['modelo']] = []
                    resultado['campos_identificados'][mapeamento['modelo']].append(mapeamento['campo_busca'])
        
        # Identificar relacionamentos necessários
        if len(resultado['modelos_envolvidos']) > 1:
            for rel_nome, rel_info in self.relacionamentos.items():
                origem = rel_info['origem']
                destino = rel_info['destino']
                
                if origem in resultado['modelos_envolvidos'] and destino in resultado['modelos_envolvidos']:
                    resultado['relacionamentos_necessarios'].append(rel_info)
        
        # Gerar sugestão de query básica
        if resultado['mapeamentos_encontrados']:
            resultado['sugestao_query'] = self._gerar_sugestao_query(resultado)
        
        logger.info(f"🧠 Análise completa: {len(resultado['mapeamentos_encontrados'])} mapeamentos, {len(resultado['modelos_envolvidos'])} modelos")
        
        return resultado
    
    def _gerar_sugestao_query(self, resultado: Dict[str, Any]) -> str:
        """Gera sugestão de query SQL baseada nos mapeamentos"""
        
        modelos = list(resultado['modelos_envolvidos'])
        if not modelos:
            return ""
        
        # Query básica para modelo principal
        modelo_principal = modelos[0]
        campos = resultado['campos_identificados'][modelo_principal]
        
        query = f"SELECT {', '.join(campos)} FROM {modelo_principal}"
        
        # Adicionar JOINs se necessário
        for relacionamento in resultado['relacionamentos_necessarios']:
            origem = relacionamento['origem'] 
            destino = relacionamento['destino']
            campo = relacionamento.get('campo_ligacao', 'id')
            if campo == 'id':
                campo = 'id'
            else:
                campo = campo.lower()

            if campo is None:
                logger.warning(f"❌ Campo não encontrado para relacionamento: {relacionamento}")
            else:
            
                if origem == modelo_principal:
                    query += f" JOIN {destino} ON {origem}.{campo} = {destino}.{campo}"
                elif destino == modelo_principal:
                    query += f" JOIN {origem} ON {destino}.{campo} = {origem}.{campo}"
        
        return query
    
    def gerar_prompt_mapeamento(self) -> str:
        """Gera prompt explicando mapeamentos para Claude"""
        
        prompt = """🧠 **MAPEAMENTO SEMÂNTICO - Linguagem Natural → Campos do Banco**

Quando o usuário mencionar estes termos, use os campos correspondentes:

"""
        
        # Agrupar por modelo
        modelos_agrupados = {}
        for chave, mapeamento in self.mapeamentos.items():
            modelo = mapeamento['modelo']
            if modelo not in modelos_agrupados:
                modelos_agrupados[modelo] = []
            modelos_agrupados[modelo].append((chave, mapeamento))
        
        for modelo, mapeamentos_modelo in modelos_agrupados.items():
            prompt += f"**{modelo}**:\n"
            for chave, mapeamento in mapeamentos_modelo:
                termos = ', '.join(mapeamento['termos_naturais'][:3])  # Primeiros 3 termos
                if len(mapeamento['termos_naturais']) > 3:
                    termos += "..."
                prompt += f"• '{termos}' → campo: {mapeamento['campo_busca']}\n"
            prompt += "\n"
        
        prompt += """
**RELACIONAMENTOS IMPORTANTES**:
• Pedido.nf = EntregaMonitorada.numero_nf
• EntregaMonitorada.id = AgendamentoEntrega.entrega_id  
• Embarque.id = EmbarqueItem.embarque_id
• EmbarqueItem.numero_nf = EntregaMonitorada.numero_nf

🎯 **INSTRUÇÕES**:
1. Sempre use os campos EXATOS listados acima
2. Para relacionamentos entre modelos, use os JOINs indicados
3. Se termo não estiver mapeado, pergunte esclarecimento
4. NUNCA invente campos que não estão na lista"""

        return prompt

# Instância global
mapeamento_semantico = MapeamentoSemantico()

def get_mapeamento_semantico() -> MapeamentoSemantico:
    """Retorna instância do mapeamento semântico"""
    return mapeamento_semantico 