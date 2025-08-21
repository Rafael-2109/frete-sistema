"""
Mapper para dados do Portal Atacadão
Converte dados entre o sistema e o portal
Inclui mapeamento de códigos de produtos (DE-PARA)
"""

import logging
from datetime import datetime


logger = logging.getLogger(__name__)

class AtacadaoMapper:
    """Mapeia dados entre o sistema e o portal Atacadão"""
    
    @staticmethod
    def mapear_dados_sistema_para_portal(dados_sistema):
        """
        Converte dados do sistema para formato esperado pelo portal
        
        IMPORTANTE: O Atacadão precisa do campo 'pedido_cliente' da CarteiraPrincipal
        """
        try:
            # Buscar pedido_cliente da CarteiraPrincipal se não vier nos dados
            pedido_cliente = dados_sistema.get('pedido_cliente')
            
            if not pedido_cliente and dados_sistema.get('num_pedido'):
                # Buscar pedido_cliente na CarteiraPrincipal
                from app.carteira.models import CarteiraPrincipal
                
                item_carteira = CarteiraPrincipal.query.filter_by(
                    num_pedido=dados_sistema['num_pedido']
                ).first()
                
                if item_carteira:
                    pedido_cliente = item_carteira.pedido_cliente
                else:
                    logger.warning(f"Pedido {dados_sistema['num_pedido']} não encontrado na CarteiraPrincipal")
            
            dados_portal = {
                # Campo crítico para Atacadão
                'pedido_cliente': pedido_cliente,
                
                # Dados básicos
                'cnpj_cliente': dados_sistema.get('cnpj_cpf', '').replace('.', '').replace('/', '').replace('-', ''),
                'nota_fiscal': dados_sistema.get('nota_fiscal') or dados_sistema.get('num_pedido'),
                'data_agendamento': dados_sistema.get('agendamento') or dados_sistema.get('data_agendamento_editada'),
                'hora_agendamento': dados_sistema.get('hora_agendamento'),
                
                # Veículo - mapear para IDs do Atacadão
                'tipo_veiculo': dados_sistema.get('tipo_veiculo', '8'),  # Default: Truck-Baú
                
                # Dados de carga
                'volumes': dados_sistema.get('volumes', 1),
                'peso': float(dados_sistema.get('peso', 0) or 0),
                'valor': float(dados_sistema.get('valor_saldo', 0) or dados_sistema.get('valor', 0) or 0),
                'observacoes': dados_sistema.get('observ_ped_1', ''),
                
                # Produtos para mapeamento
                'produtos': dados_sistema.get('produtos', []),
                
                # Dados adicionais para rastreamento
                'num_pedido': dados_sistema.get('num_pedido'),
                'lote_id': dados_sistema.get('separacao_lote_id'),
                'cliente': dados_sistema.get('raz_social_red'),
                'cidade': dados_sistema.get('nome_cidade'),
                'uf': dados_sistema.get('cod_uf')
            }
            
            # Formatar data se necessário
            if dados_portal['data_agendamento']:
                if isinstance(dados_portal['data_agendamento'], str):
                    try:
                        dados_portal['data_agendamento'] = datetime.strptime(
                            dados_portal['data_agendamento'], 
                            '%Y-%m-%d'
                        ).date()
                    except Exception as e:
                        logger.error(f"Erro ao formatar data: {e}")
                        pass
            
            # Validar campos obrigatórios
            if not dados_portal.get('pedido_cliente'):
                raise ValueError("Campo 'pedido_cliente' é obrigatório para o Atacadão")
            
            return dados_portal
            
        except Exception as e:
            logger.error(f"Erro ao mapear dados para portal: {e}")
            raise
    
    @staticmethod
    def mapear_codigo_produto(codigo_nosso, cnpj_cliente=None):
        """
        Mapeia código de produto nosso para código do cliente
        
        TODO: Implementar tabela de DE-PARA
        """
        # Por enquanto, retornar o mesmo código
        # Futuramente, consultar tabela de mapeamento
        return codigo_nosso
    
    @staticmethod
    def mapear_tipo_veiculo(descricao_veiculo):
        """
        Mapeia descrição do veículo para ID do Atacadão
        
        IDs permitidos:
        6 = Kombi/Van (Cód.: 1 - Máx: 5 paletes)
        5 = F4000-3/4 - Baú (Cód.: 3 - Máx: 10 paletes)
        11 = Toco-Baú (Cód.: 4 - Máx: 24 paletes)
        8 = Truck-Baú (Cód.: 5 - Máx: 75 paletes)
        2 = Carreta-Baú (Cód.: 7 - Máx: 80 paletes)
        """
        if not descricao_veiculo:
            return '8'  # Default: Truck-Baú
        
        descricao_lower = descricao_veiculo.lower()
        
        mapeamento = {
            'kombi': '6',
            'van': '6',
            'f4000': '5',
            '3/4': '5',
            'toco': '11',
            'truck': '8',
            'carreta': '2'
        }
        
        for chave, valor in mapeamento.items():
            if chave in descricao_lower:
                return valor
        
        return '8'  # Default se não encontrar
    
    @staticmethod
    def mapear_resposta_portal_para_sistema(resposta_portal):
        """
        Converte resposta do portal para formato do sistema
        """
        try:
            dados_sistema = {
                'protocolo': resposta_portal.get('protocolo'),
                'status': 'aguardando',
                'data_solicitacao': resposta_portal.get('data_solicitacao') or datetime.now(),
                'resposta_portal': resposta_portal,
                'sucesso': resposta_portal.get('sucesso', False)
            }
            
            # Adicionar ID da carga se disponível
            if resposta_portal.get('carga_id'):
                dados_sistema['navegador_sessao_id'] = f"carga_{resposta_portal['carga_id']}"
            
            # Mapear status
            if resposta_portal.get('status'):
                dados_sistema['status'] = AtacadaoMapper.mapear_status_portal(
                    resposta_portal['status']
                )
            
            return dados_sistema
            
        except Exception as e:
            logger.error(f"Erro ao mapear resposta do portal: {e}")
            raise
    
    @staticmethod
    def mapear_status_portal(status_texto):
        """
        Mapeia status do portal para status do sistema
        """
        if not status_texto:
            return 'aguardando'
        
        status_lower = status_texto.lower()
        
        mapeamento = {
            'confirmado': 'confirmado',
            'aprovado': 'confirmado',
            'agendado': 'confirmado',
            'aguardando aprovação': 'aguardando',
            'aguardando': 'aguardando',
            'em análise': 'aguardando',
            'cancelado': 'cancelado',
            'rejeitado': 'rejeitado',
            'recusado': 'rejeitado'
        }
        
        for chave, valor in mapeamento.items():
            if chave in status_lower:
                return valor
        
        return 'aguardando'
    
    @staticmethod
    def extrair_dados_lote(items):
        """
        Extrai dados consolidados de um lote de items
        Busca pedido_cliente da CarteiraPrincipal
        """
        if not items:
            return {}
        
        primeiro_item = items[0]
        
        # Buscar pedido_cliente na CarteiraPrincipal
        pedido_cliente = None
        num_pedido = getattr(primeiro_item, 'num_pedido', None)
        
        if num_pedido:
            from app.carteira.models import CarteiraPrincipal
            item_carteira = CarteiraPrincipal.query.filter_by(
                num_pedido=num_pedido
            ).first()
            
            if item_carteira:
                pedido_cliente = item_carteira.pedido_cliente
                logger.info(f"Pedido cliente encontrado: {pedido_cliente} para pedido {num_pedido}")
        
        # Somar valores do lote
        total_peso = sum(float(getattr(item, 'peso', 0) or 0) for item in items)
        total_valor = sum(float(getattr(item, 'valor_saldo', 0) or 0) for item in items)
        total_volumes = len(items)
        
        # Extrair produtos únicos com quantidades
        produtos = []
        produtos_dict = {}
        
        for item in items:
            cod_produto = getattr(item, 'cod_produto', None)
            if cod_produto:
                if cod_produto not in produtos_dict:
                    produtos_dict[cod_produto] = {
                        'codigo': cod_produto,
                        'nome': getattr(item, 'nome_produto', ''),
                        'quantidade': 0,
                        'peso_unitario': getattr(item, 'peso', 0),
                        'valor_unitario': getattr(item, 'preco_produto_pedido', 0)
                    }
                
                # Somar quantidade
                qtd = float(getattr(item, 'qtd_saldo', 0) or getattr(item, 'qtd_selecionada_usuario', 0) or 0)
                produtos_dict[cod_produto]['quantidade'] += qtd
        
        produtos = list(produtos_dict.values())
        
        dados_lote = {
            # Campo crítico para Atacadão
            'pedido_cliente': pedido_cliente,
            
            # Identificação
            'cnpj_cpf': getattr(primeiro_item, 'cnpj_cpf', None) or getattr(primeiro_item, 'cnpj_cliente', None),
            'separacao_lote_id': getattr(primeiro_item, 'separacao_lote_id', None),
            'raz_social_red': getattr(primeiro_item, 'raz_social_red', None),
            'nome_cidade': getattr(primeiro_item, 'nome_cidade', None),
            'cod_uf': getattr(primeiro_item, 'cod_uf', None),
            
            # Datas
            'agendamento': getattr(primeiro_item, 'agendamento', None) or getattr(primeiro_item, 'data_agendamento_editada', None),
            'hora_agendamento': getattr(primeiro_item, 'hora_agendamento', None),
            'protocolo': getattr(primeiro_item, 'protocolo', None) or getattr(primeiro_item, 'protocolo_editado', None),
            'observ_ped_1': getattr(primeiro_item, 'observ_ped_1', None) or getattr(primeiro_item, 'observacoes_usuario', None),
            
            # Valores totais
            'peso': total_peso,
            'valor': total_valor,
            'volumes': total_volumes,
            
            # Produtos detalhados
            'produtos': produtos,
            
            # Lista de pedidos/NFs
            'pedidos': list(set(getattr(item, 'num_pedido', '') for item in items if getattr(item, 'num_pedido', None))),
            'notas_fiscais': list(set(getattr(item, 'nota_fiscal', '') for item in items if getattr(item, 'nota_fiscal', None)))
        }
        
        # Usar primeira NF ou primeiro pedido como referência
        if dados_lote['notas_fiscais']:
            dados_lote['nota_fiscal'] = dados_lote['notas_fiscais'][0]
        elif dados_lote['pedidos']:
            dados_lote['nota_fiscal'] = dados_lote['pedidos'][0]
            dados_lote['num_pedido'] = dados_lote['pedidos'][0]
        else:
            dados_lote['nota_fiscal'] = primeiro_item.separacao_lote_id
        
        return dados_lote