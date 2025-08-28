"""
Service para lógica de agrupamento de pedidos da carteira
"""

from sqlalchemy import func, and_, exists
from app import db
from app.carteira.models import CarteiraPrincipal, SaldoStandby
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
            
            # Ordenar após enriquecimento para usar rotas calculadas
            def get_rota_para_ordenacao(pedido):
                """Retorna a rota considerando incoterm FOB/RED como rota especial"""
                incoterm = pedido.get('incoterm', 'CIF')
                if incoterm == 'FOB':
                    return 'FOB'
                elif incoterm == 'RED':
                    return 'RED'
                else:
                    return pedido.get('rota') or 'ZZZZZ'
            
            pedidos_ordenados = sorted(pedidos_enriquecidos, 
                key=lambda p: (
                    get_rota_para_ordenacao(p),     # 1º Rota/Incoterm (nulls no final)
                    p.get('sub_rota') or 'ZZZZZ',  # 2º Sub-rota (nulls no final)
                    p.get('cnpj_cpf') or 'ZZZZZ'   # 3º CNPJ (nulls no final)
                )
            )
            
            return pedidos_ordenados
            
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
            CarteiraPrincipal.data_entrega_pedido,
            CarteiraPrincipal.observ_ped_1,
            CarteiraPrincipal.status_pedido,
            CarteiraPrincipal.pedido_cliente,
            CarteiraPrincipal.cod_uf,
            CarteiraPrincipal.nome_cidade,
            CarteiraPrincipal.incoterm,
            CarteiraPrincipal.protocolo,
            CarteiraPrincipal.agendamento,
            CarteiraPrincipal.agendamento_confirmado,
            CarteiraPrincipal.forma_agendamento,
            
            # Agregações conforme especificação
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido * 
                    CarteiraPrincipal.preco_produto_pedido).label('valor_total'),
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido * 
                    CadastroPalletizacao.peso_bruto).label('peso_total'),
            func.sum(
                func.coalesce(
                    CarteiraPrincipal.qtd_saldo_produto_pedido / 
                    func.nullif(CadastroPalletizacao.palletizacao, 0),
                    0
                )
            ).label('pallet_total'),
            func.count(CarteiraPrincipal.id).label('total_itens')
            
        ).outerjoin(
            CadastroPalletizacao,
            and_(
                CarteiraPrincipal.cod_produto == CadastroPalletizacao.cod_produto,
                CadastroPalletizacao.ativo == True
            )
        ).filter(
            CarteiraPrincipal.ativo == True,
            # Filtrar pedidos que NÃO estão em standby OU estão CONFIRMADOS
            ~exists().where(
                and_(
                    SaldoStandby.num_pedido == CarteiraPrincipal.num_pedido,
                    SaldoStandby.status_standby.in_(['ATIVO', 'BLOQ. COML.', 'SALDO'])
                )
            )
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
            CarteiraPrincipal.data_entrega_pedido,
            CarteiraPrincipal.observ_ped_1,
            CarteiraPrincipal.status_pedido,
            CarteiraPrincipal.pedido_cliente,
            CarteiraPrincipal.cod_uf,
            CarteiraPrincipal.nome_cidade,
            CarteiraPrincipal.incoterm,
            CarteiraPrincipal.protocolo,
            CarteiraPrincipal.agendamento,
            CarteiraPrincipal.agendamento_confirmado,
            CarteiraPrincipal.forma_agendamento
        ).order_by(
            CarteiraPrincipal.rota.asc().nullslast(),      # 1º Rota: menor para maior (A-Z)
            CarteiraPrincipal.sub_rota.asc().nullslast(),  # 2º Sub-rota: menor para maior (A-Z)
            CarteiraPrincipal.cnpj_cpf.asc().nullslast()   # 3º CNPJ: menor para maior (0-9)
        ).all()
    
    def _enriquecer_pedido_com_separacoes(self, pedido):
        """Enriquece pedido com informações de separação"""
        try:
            # Importar funções de busca de rotas
            from app.carteira.utils.separacao_utils import buscar_rota_por_uf, buscar_sub_rota_por_uf_cidade
            
            # Calcular informações de separação
            qtd_separacoes, valor_separacoes, dados_separacao_completa = self._calcular_separacoes(pedido.num_pedido)
            
            # Calcular valor do saldo restante
            valor_pedido = float(pedido.valor_total) if pedido.valor_total else 0
            valor_saldo_restante = valor_pedido - float(valor_separacoes)
            
            # Determinar se está totalmente em separação
            totalmente_separado = valor_saldo_restante <= 0.01  # Margem de 1 centavo
            
            # Para separações tipo_envio 'total', usar dados da separação completa
            if dados_separacao_completa and dados_separacao_completa['expedicao']:
                expedicao_final = dados_separacao_completa['expedicao']
                agendamento_final = dados_separacao_completa['agendamento'] if dados_separacao_completa['agendamento'] else pedido.agendamento
                protocolo_final = dados_separacao_completa['protocolo'] if dados_separacao_completa['protocolo'] else pedido.protocolo
                # Usar agendamento_confirmado da separação se existir
                agendamento_confirmado_final = dados_separacao_completa.get('agendamento_confirmado', pedido.agendamento_confirmado)
            else:
                # Verificar se existe pré-separação total
                from app.carteira.models import PreSeparacaoItem
                pre_sep_total = db.session.query(PreSeparacaoItem).filter(
                    PreSeparacaoItem.num_pedido == pedido.num_pedido,
                    PreSeparacaoItem.tipo_envio == 'total',
                    PreSeparacaoItem.status.in_(['CRIADO', 'RECOMPOSTO'])
                ).first()
                
                if pre_sep_total:
                    expedicao_final = pre_sep_total.data_expedicao_editada if pre_sep_total.data_expedicao_editada else pedido.expedicao
                    agendamento_final = pre_sep_total.data_agendamento_editada if pre_sep_total.data_agendamento_editada else pedido.agendamento
                    protocolo_final = pre_sep_total.protocolo_editado if pre_sep_total.protocolo_editado else pedido.protocolo
                    agendamento_confirmado_final = pre_sep_total.agendamento_confirmado if hasattr(pre_sep_total, 'agendamento_confirmado') else pedido.agendamento_confirmado
                else:
                    expedicao_final = pedido.expedicao
                    agendamento_final = pedido.agendamento
                    protocolo_final = pedido.protocolo
                    agendamento_confirmado_final = pedido.agendamento_confirmado
            
            # Buscar rota e sub-rota das localidades
            rota_calculada = buscar_rota_por_uf(pedido.cod_uf) if pedido.cod_uf else None
            sub_rota_calculada = buscar_sub_rota_por_uf_cidade(pedido.cod_uf, pedido.nome_cidade) if pedido.cod_uf and pedido.nome_cidade else None
            
            return {
                'num_pedido': pedido.num_pedido,
                'vendedor': pedido.vendedor,
                'equipe_vendas': pedido.equipe_vendas,
                'data_pedido': pedido.data_pedido,
                'cnpj_cpf': pedido.cnpj_cpf,
                'raz_social_red': pedido.raz_social_red,
                'rota': rota_calculada,
                'sub_rota': sub_rota_calculada,
                'expedicao': expedicao_final,  # Usa expedição da separação completa se existir
                'expedicao_original': pedido.expedicao,  # Mantém a original para referência
                'data_entrega_pedido': pedido.data_entrega_pedido,
                'observ_ped_1': pedido.observ_ped_1,  
                'status_pedido': pedido.status_pedido,
                'pedido_cliente': pedido.pedido_cliente,
                'cod_uf': pedido.cod_uf,
                'nome_cidade': pedido.nome_cidade,
                'incoterm': pedido.incoterm,  # Mantém apenas a sigla (CIF, FOB, etc)
                'protocolo': protocolo_final,  # Usa protocolo da separação completa se existir
                'protocolo_original': pedido.protocolo,  # Mantém o original para referência
                'agendamento': agendamento_final,  # Usa agendamento da separação completa se existir
                'agendamento_original': pedido.agendamento,  # Mantém o original para referência
                'agendamento_confirmado': agendamento_confirmado_final,  # Usa o valor da separação/pré-separação se existir
                'forma_agendamento': pedido.forma_agendamento,
                'valor_total': valor_pedido,
                'peso_total': float(pedido.peso_total) if pedido.peso_total else 0,
                'pallet_total': float(pedido.pallet_total) if pedido.pallet_total else 0,
                'total_itens': pedido.total_itens,
                # Informações de separação
                'valor_separacoes': float(valor_separacoes),
                'valor_saldo_restante': valor_saldo_restante,
                'qtd_separacoes': qtd_separacoes,
                'totalmente_separado': totalmente_separado,
                'tem_separacao_completa': dados_separacao_completa and dados_separacao_completa['expedicao'] is not None,
                'separacao_lote_id': dados_separacao_completa.get('separacao_lote_id')  # Passar lote_id
            }
            
        except Exception as e:
            logger.warning(f"Erro ao enriquecer pedido {pedido.num_pedido}: {e}")
            return self._criar_pedido_basico(pedido)
    
    def _calcular_separacoes(self, num_pedido):
        """Calcula quantidade e valor das separações ativas e retorna dados de separação completa"""
        try:
            from app.carteira.models import PreSeparacaoItem
            
            # Contar separacao_lote_id únicos (quantidade de envios para separação)
            # Considera apenas pedidos com status DIFERENTE de 'FATURADO'
            qtd_separacoes = db.session.query(
                func.count(func.distinct(Separacao.separacao_lote_id))
            ).join(
                Pedido, and_(
                    Separacao.separacao_lote_id == Pedido.separacao_lote_id,
                    Separacao.num_pedido == Pedido.num_pedido
                )
            ).filter(
                Separacao.num_pedido == num_pedido,
                # Considera apenas pedidos não faturados
                Pedido.status != 'FATURADO'
            ).scalar() or 0
            
            # Buscar separações para calcular valor total e verificar tipo_envio
            # Considera apenas pedidos não faturados
            separacoes_ativas = db.session.query(Separacao, Pedido).join(
                Pedido, and_(
                    Separacao.separacao_lote_id == Pedido.separacao_lote_id,
                    Separacao.num_pedido == Pedido.num_pedido
                )
            ).filter(
                Separacao.num_pedido == num_pedido,
                # Considera apenas pedidos não faturados
                Pedido.status != 'FATURADO'
            ).all()
            
            # Calcular valor total das separações e buscar dados de separação completa
            valor_separacoes = 0
            dados_separacao_completa = {
                'expedicao': None,
                'agendamento': None,
                'protocolo': None,
                'agendamento_confirmado': False,
                'separacao_lote_id': None  # Adicionar lote_id
            }
            
            for sep, ped in separacoes_ativas:
                if sep.qtd_saldo and sep.valor_saldo:
                    valor_unit = sep.valor_saldo / sep.qtd_saldo if sep.qtd_saldo > 0 else 0
                    valor_separacoes += sep.qtd_saldo * valor_unit
                
                # Se encontrar uma separação com tipo_envio 'total', pegar dados do Pedido
                if sep.tipo_envio == 'total':
                    dados_separacao_completa['expedicao'] = ped.expedicao
                    dados_separacao_completa['agendamento'] = ped.agendamento
                    dados_separacao_completa['protocolo'] = ped.protocolo
                    dados_separacao_completa['agendamento_confirmado'] = sep.agendamento_confirmado if hasattr(sep, 'agendamento_confirmado') else False
                    dados_separacao_completa['separacao_lote_id'] = sep.separacao_lote_id  # Adicionar lote_id
            
            # Buscar pré-separações completas também
            if not dados_separacao_completa['expedicao']:
                pre_sep_completa = PreSeparacaoItem.query.filter(
                    PreSeparacaoItem.num_pedido == num_pedido,
                    PreSeparacaoItem.tipo_envio == 'total',
                    PreSeparacaoItem.status.in_(['CRIADO', 'RECOMPOSTO'])
                ).first()
                
                if pre_sep_completa:
                    dados_separacao_completa['expedicao'] = pre_sep_completa.data_expedicao_editada
                    dados_separacao_completa['agendamento'] = pre_sep_completa.data_agendamento_editada
                    dados_separacao_completa['protocolo'] = pre_sep_completa.protocolo_editado
                    # IMPORTANTE: Incluir também o agendamento_confirmado da pré-separação
                    dados_separacao_completa['agendamento_confirmado'] = pre_sep_completa.agendamento_confirmado if hasattr(pre_sep_completa, 'agendamento_confirmado') else False
                    dados_separacao_completa['separacao_lote_id'] = pre_sep_completa.separacao_lote_id  # Adicionar lote_id
            
            return qtd_separacoes, valor_separacoes, dados_separacao_completa
            
        except Exception as e:
            logger.warning(f"Erro ao calcular separações para {num_pedido}: {e}")
            return 0, 0, {'expedicao': None, 'agendamento': None, 'protocolo': None}
    
    def _criar_pedido_basico(self, pedido):
        """Cria estrutura básica de pedido em caso de erro"""
        from app.carteira.utils.separacao_utils import buscar_rota_por_uf, buscar_sub_rota_por_uf_cidade
        
        # Buscar rota e sub-rota das localidades
        rota_calculada = buscar_rota_por_uf(pedido.cod_uf) if pedido.cod_uf else None
        sub_rota_calculada = buscar_sub_rota_por_uf_cidade(pedido.cod_uf, pedido.nome_cidade) if pedido.cod_uf and pedido.nome_cidade else None
        
        return {
            'num_pedido': pedido.num_pedido,
            'vendedor': pedido.vendedor,
            'equipe_vendas': pedido.equipe_vendas,
            'data_pedido': pedido.data_pedido,
            'cnpj_cpf': pedido.cnpj_cpf,
            'raz_social_red': pedido.raz_social_red,
            'rota': rota_calculada,
            'sub_rota': sub_rota_calculada,
            'expedicao': pedido.expedicao,
            'expedicao_original': pedido.expedicao,
            'data_entrega_pedido': pedido.data_entrega_pedido,
            'observ_ped_1': pedido.observ_ped_1,
            'status_pedido': pedido.status_pedido,
            'pedido_cliente': pedido.pedido_cliente,
            'cod_uf': pedido.cod_uf,
            'nome_cidade': pedido.nome_cidade,
            'incoterm': pedido.incoterm,
            'protocolo': pedido.protocolo,
            'agendamento': pedido.agendamento,
            'agendamento_confirmado': pedido.agendamento_confirmado,
            'forma_agendamento': pedido.forma_agendamento,
            'valor_total': float(pedido.valor_total) if pedido.valor_total else 0,
            'peso_total': float(pedido.peso_total) if pedido.peso_total else 0,
            'pallet_total': float(pedido.pallet_total) if pedido.pallet_total else 0,
            'total_itens': pedido.total_itens,
            'valor_separacoes': 0,
            'valor_saldo_restante': float(pedido.valor_total) if pedido.valor_total else 0,
            'qtd_separacoes': 0,
            'totalmente_separado': False,
            'tem_separacao_completa': False
        }