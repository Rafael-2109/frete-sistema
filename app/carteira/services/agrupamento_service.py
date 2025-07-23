"""
Service para lógica de agrupamento de pedidos da carteira
"""

from sqlalchemy import func, and_
from app import db
from app.carteira.models import CarteiraPrincipal
from app.separacao.models import Separacao
from app.pedidos.models import Pedido
from app.producao.models import CadastroPalletizacao
import logging

logger = logging.getLogger(__name__)


class AgrupamentoService:
    """Service responsável por agrupar pedidos da carteira"""
    
    def obter_pedidos_agrupados(self):
        """
        Obtém pedidos agrupados por num_pedido com agregações
        Retorna lista de dicionários com dados enriquecidos
        """
        try:
            # Buscar pedidos agrupados base
            pedidos_agrupados = self._query_agrupamento_base()
            
            # Enriquecer com dados de separação
            pedidos_enriquecidos = []
            for pedido in pedidos_agrupados:
                pedido_enriquecido = self._enriquecer_pedido_com_separacoes(pedido)
                pedidos_enriquecidos.append(pedido_enriquecido)
            
            return pedidos_enriquecidos
            
        except Exception as e:
            logger.error(f"Erro ao obter pedidos agrupados: {e}")
            return []
    
    def _query_agrupamento_base(self):
        """Query principal de agrupamento conforme especificação"""
        return db.session.query(
            # Campos base do agrupamento
            CarteiraPrincipal.num_pedido,
            CarteiraPrincipal.vendedor,
            CarteiraPrincipal.equipe_vendas,
            CarteiraPrincipal.data_pedido,
            CarteiraPrincipal.cnpj_cpf,
            CarteiraPrincipal.raz_social_red,
            CarteiraPrincipal.rota,
            CarteiraPrincipal.sub_rota,
            CarteiraPrincipal.expedicao,
            CarteiraPrincipal.observ_ped_1,
            CarteiraPrincipal.status_pedido,
            CarteiraPrincipal.pedido_cliente,
            CarteiraPrincipal.cod_uf,
            CarteiraPrincipal.nome_cidade,
            CarteiraPrincipal.incoterm,
            CarteiraPrincipal.protocolo,
            CarteiraPrincipal.agendamento,
            CarteiraPrincipal.agendamento_confirmado,
            
            # Agregações conforme especificação
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido * 
                    CarteiraPrincipal.preco_produto_pedido).label('valor_total'),
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido * 
                    CadastroPalletizacao.peso_bruto).label('peso_total'),
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido / 
                    CadastroPalletizacao.palletizacao).label('pallet_total'),
            func.count(CarteiraPrincipal.id).label('total_itens')
            
        ).outerjoin(
            CadastroPalletizacao,
            and_(
                CarteiraPrincipal.cod_produto == CadastroPalletizacao.cod_produto,
                CadastroPalletizacao.ativo == True
            )
        ).filter(
            CarteiraPrincipal.ativo == True
        ).group_by(
            CarteiraPrincipal.num_pedido,
            CarteiraPrincipal.vendedor,
            CarteiraPrincipal.equipe_vendas,
            CarteiraPrincipal.data_pedido,
            CarteiraPrincipal.cnpj_cpf,
            CarteiraPrincipal.raz_social_red,
            CarteiraPrincipal.rota,
            CarteiraPrincipal.sub_rota,
            CarteiraPrincipal.expedicao,
            CarteiraPrincipal.observ_ped_1,
            CarteiraPrincipal.status_pedido,
            CarteiraPrincipal.pedido_cliente,
            CarteiraPrincipal.cod_uf,
            CarteiraPrincipal.nome_cidade,
            CarteiraPrincipal.incoterm,
            CarteiraPrincipal.protocolo,
            CarteiraPrincipal.agendamento,
            CarteiraPrincipal.agendamento_confirmado
        ).order_by(
            CarteiraPrincipal.expedicao.asc().nullslast(),
            CarteiraPrincipal.num_pedido.asc()
        ).all()
    
    def _enriquecer_pedido_com_separacoes(self, pedido):
        """Enriquece pedido com informações de separação"""
        try:
            # Calcular informações de separação
            qtd_separacoes, valor_separacoes = self._calcular_separacoes(pedido.num_pedido)
            
            # Calcular valor do saldo restante
            valor_pedido = float(pedido.valor_total) if pedido.valor_total else 0
            valor_saldo_restante = valor_pedido - float(valor_separacoes)
            
            # Determinar se está totalmente em separação
            totalmente_separado = valor_saldo_restante <= 0.01  # Margem de 1 centavo
            
            return {
                'num_pedido': pedido.num_pedido,
                'vendedor': pedido.vendedor,
                'equipe_vendas': pedido.equipe_vendas,
                'data_pedido': pedido.data_pedido,
                'cnpj_cpf': pedido.cnpj_cpf,
                'raz_social_red': pedido.raz_social_red,
                'rota': pedido.rota,
                'sub_rota': pedido.sub_rota,
                'expedicao': pedido.expedicao,
                'observ_ped_1': pedido.observ_ped_1,
                'status_pedido': pedido.status_pedido,
                'pedido_cliente': pedido.pedido_cliente,
                'cod_uf': pedido.cod_uf,
                'nome_cidade': pedido.nome_cidade,
                'incoterm': pedido.incoterm,
                'protocolo': pedido.protocolo,
                'agendamento': pedido.agendamento,
                'agendamento_confirmado': pedido.agendamento_confirmado,
                'valor_total': valor_pedido,
                'peso_total': float(pedido.peso_total) if pedido.peso_total else 0,
                'pallet_total': float(pedido.pallet_total) if pedido.pallet_total else 0,
                'total_itens': pedido.total_itens,
                # Informações de separação
                'valor_separacoes': float(valor_separacoes),
                'valor_saldo_restante': valor_saldo_restante,
                'qtd_separacoes': qtd_separacoes,
                'totalmente_separado': totalmente_separado
            }
            
        except Exception as e:
            logger.warning(f"Erro ao enriquecer pedido {pedido.num_pedido}: {e}")
            return self._criar_pedido_basico(pedido)
    
    def _calcular_separacoes(self, num_pedido):
        """Calcula quantidade e valor das separações ativas"""
        try:
            # Contar separacao_lote_id únicos (quantidade de envios para separação)
            qtd_separacoes = db.session.query(
                func.count(func.distinct(Separacao.separacao_lote_id))
            ).join(
                Pedido, Separacao.separacao_lote_id == Pedido.separacao_lote_id
            ).filter(
                Separacao.num_pedido == num_pedido,
                Pedido.status.in_(['ABERTO', 'COTADO'])
            ).scalar() or 0
            
            # Buscar separações para calcular valor total
            separacoes_ativas = db.session.query(Separacao).join(
                Pedido, Separacao.separacao_lote_id == Pedido.separacao_lote_id
            ).filter(
                Separacao.num_pedido == num_pedido,
                Pedido.status.in_(['ABERTO', 'COTADO'])
            ).all()
            
            # Calcular valor total das separações
            valor_separacoes = 0
            for sep in separacoes_ativas:
                if sep.qtd_saldo and sep.valor_saldo:
                    valor_unit = sep.valor_saldo / sep.qtd_saldo if sep.qtd_saldo > 0 else 0
                    valor_separacoes += sep.qtd_saldo * valor_unit
            
            return qtd_separacoes, valor_separacoes
            
        except Exception as e:
            logger.warning(f"Erro ao calcular separações para {num_pedido}: {e}")
            return 0, 0
    
    def _criar_pedido_basico(self, pedido):
        """Cria estrutura básica de pedido em caso de erro"""
        return {
            'num_pedido': pedido.num_pedido,
            'vendedor': pedido.vendedor,
            'equipe_vendas': pedido.equipe_vendas,
            'data_pedido': pedido.data_pedido,
            'cnpj_cpf': pedido.cnpj_cpf,
            'raz_social_red': pedido.raz_social_red,
            'rota': pedido.rota,
            'sub_rota': pedido.sub_rota,
            'expedicao': pedido.expedicao,
            'observ_ped_1': pedido.observ_ped_1,
            'status_pedido': pedido.status_pedido,
            'pedido_cliente': pedido.pedido_cliente,
            'cod_uf': pedido.cod_uf,
            'nome_cidade': pedido.nome_cidade,
            'incoterm': pedido.incoterm,
            'protocolo': pedido.protocolo,
            'agendamento': pedido.agendamento,
            'agendamento_confirmado': pedido.agendamento_confirmado,
            'valor_total': float(pedido.valor_total) if pedido.valor_total else 0,
            'peso_total': float(pedido.peso_total) if pedido.peso_total else 0,
            'pallet_total': float(pedido.pallet_total) if pedido.pallet_total else 0,
            'total_itens': pedido.total_itens,
            'valor_separacoes': 0,
            'valor_saldo_restante': float(pedido.valor_total) if pedido.valor_total else 0,
            'qtd_separacoes': 0,
            'totalmente_separado': False
        }