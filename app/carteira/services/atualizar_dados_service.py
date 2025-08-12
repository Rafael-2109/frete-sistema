"""
Serviço para atualizar dados de Separacao, Pedido e PreSeparacaoItem
baseado nos dados da CarteiraPrincipal
"""

from sqlalchemy import and_
from app import db
from app.carteira.models import CarteiraPrincipal, PreSeparacaoItem
from app.separacao.models import Separacao
from app.pedidos.models import Pedido
from app.carteira.utils.separacao_utils import buscar_rota_por_uf, buscar_sub_rota_por_uf_cidade
import logging

logger = logging.getLogger(__name__)


class AtualizarDadosService:
    """
    Serviço para atualizar dados de Separacao, Pedido e PreSeparacaoItem
    baseado nos dados da CarteiraPrincipal
    """
    
    def __init__(self):
        self.total_separacoes_atualizadas = 0
        self.total_pedidos_atualizados = 0
        self.total_pre_separacoes_atualizadas = 0
        self.erros_encontrados = []
    
    def atualizar_dados_pos_sincronizacao(self):
        """
        Atualiza Separacao, Pedido e PreSeparacaoItem com dados da CarteiraPrincipal
        para pedidos com status != 'FATURADO'
        
        Campos atualizados:
        1. CNPJ
        2. raz_social_red
        3. Cidade
        4. UF
        5. Rota (com regra de incoterm FOB e RED)
        6. SubRota
        7. Observação
        
        Returns:
            dict: Resumo da atualização
        """
        try:
            logger.info("🔄 Iniciando atualização de dados baseado na CarteiraPrincipal...")
            
            # Buscar pedidos que não estão faturados
            pedidos_nao_faturados = Pedido.query.filter(
                Pedido.status != 'FATURADO'
            ).all()
            
            logger.info(f"📋 Encontrados {len(pedidos_nao_faturados)} pedidos não faturados")
            
            for pedido in pedidos_nao_faturados:
                try:
                    # Buscar dados atualizados da CarteiraPrincipal
                    # Pegar o primeiro item para obter dados do cliente (todos têm o mesmo cliente)
                    item_carteira = CarteiraPrincipal.query.filter(
                        CarteiraPrincipal.num_pedido == pedido.num_pedido,
                        CarteiraPrincipal.ativo == True
                    ).first()
                    
                    if not item_carteira:
                        logger.debug(f"⚠️ Nenhum item encontrado na carteira para pedido {pedido.num_pedido}")
                        continue
                    
                    # ========================================
                    # ATUALIZAR PEDIDO
                    # ========================================
                    campos_alterados_pedido = []
                    
                    # CNPJ
                    if pedido.cnpj_cpf != item_carteira.cnpj_cpf:
                        pedido.cnpj_cpf = item_carteira.cnpj_cpf
                        campos_alterados_pedido.append('cnpj_cpf')
                    
                    # Razão Social
                    if pedido.raz_social_red != item_carteira.raz_social_red:
                        pedido.raz_social_red = item_carteira.raz_social_red
                        campos_alterados_pedido.append('raz_social_red')
                    
                    # Cidade
                    if pedido.nome_cidade != item_carteira.nome_cidade:
                        pedido.nome_cidade = item_carteira.nome_cidade
                        campos_alterados_pedido.append('nome_cidade')
                    
                    # UF
                    if pedido.cod_uf != item_carteira.cod_uf:
                        pedido.cod_uf = item_carteira.cod_uf
                        campos_alterados_pedido.append('cod_uf')
                    
                    # Rota - aplicar regra de incoterm
                    rota_calculada = self._calcular_rota(item_carteira)
                    if hasattr(pedido, 'rota') and pedido.rota != rota_calculada:
                        pedido.rota = rota_calculada
                        campos_alterados_pedido.append('rota')
                    
                    # SubRota
                    sub_rota_calculada = buscar_sub_rota_por_uf_cidade(
                        item_carteira.cod_uf or '',
                        item_carteira.nome_cidade or ''
                    )
                    if hasattr(pedido, 'sub_rota') and pedido.sub_rota != sub_rota_calculada:
                        pedido.sub_rota = sub_rota_calculada
                        campos_alterados_pedido.append('sub_rota')
                    
                    # Observação
                    if hasattr(pedido, 'observ_ped_1') and pedido.observ_ped_1 != item_carteira.observ_ped_1:
                        pedido.observ_ped_1 = item_carteira.observ_ped_1
                        campos_alterados_pedido.append('observ_ped_1')
                    
                    if campos_alterados_pedido:
                        self.total_pedidos_atualizados += 1
                        logger.debug(f"✅ Pedido {pedido.num_pedido} atualizado: {', '.join(campos_alterados_pedido)}")
                    
                    # ========================================
                    # ATUALIZAR SEPARAÇÕES
                    # ========================================
                    if pedido.separacao_lote_id:
                        separacoes = Separacao.query.filter(
                            Separacao.separacao_lote_id == pedido.separacao_lote_id
                        ).all()
                        
                        for separacao in separacoes:
                            # Buscar item específico da carteira para este produto
                            item_produto = CarteiraPrincipal.query.filter(
                                and_(
                                    CarteiraPrincipal.num_pedido == separacao.num_pedido,
                                    CarteiraPrincipal.cod_produto == separacao.cod_produto,
                                    CarteiraPrincipal.ativo == True
                                )
                            ).first()
                            
                            if not item_produto:
                                item_produto = item_carteira  # Usar dados gerais do pedido
                            
                            campos_alterados_sep = []
                            
                            # CNPJ
                            if separacao.cnpj_cpf != item_produto.cnpj_cpf:
                                separacao.cnpj_cpf = item_produto.cnpj_cpf
                                campos_alterados_sep.append('cnpj_cpf')
                            
                            # Razão Social
                            if separacao.raz_social_red != item_produto.raz_social_red:
                                separacao.raz_social_red = item_produto.raz_social_red
                                campos_alterados_sep.append('raz_social_red')
                            
                            # Cidade
                            if separacao.nome_cidade != item_produto.nome_cidade:
                                separacao.nome_cidade = item_produto.nome_cidade
                                campos_alterados_sep.append('nome_cidade')
                            
                            # UF
                            if separacao.cod_uf != item_produto.cod_uf:
                                separacao.cod_uf = item_produto.cod_uf
                                campos_alterados_sep.append('cod_uf')
                            
                            # Rota - aplicar regra de incoterm
                            rota_calculada = self._calcular_rota(item_produto)
                            if separacao.rota != rota_calculada:
                                separacao.rota = rota_calculada
                                campos_alterados_sep.append('rota')
                            
                            # SubRota
                            sub_rota_calculada = buscar_sub_rota_por_uf_cidade(
                                item_produto.cod_uf or '',
                                item_produto.nome_cidade or ''
                            )
                            if separacao.sub_rota != sub_rota_calculada:
                                separacao.sub_rota = sub_rota_calculada
                                campos_alterados_sep.append('sub_rota')
                            
                            # Observação
                            if separacao.observ_ped_1 != item_produto.observ_ped_1:
                                separacao.observ_ped_1 = item_produto.observ_ped_1
                                campos_alterados_sep.append('observ_ped_1')
                            
                            if campos_alterados_sep:
                                self.total_separacoes_atualizadas += 1
                                logger.debug(f"✅ Separação {separacao.separacao_lote_id}/{separacao.cod_produto} atualizada")
                    
                    # ========================================
                    # ATUALIZAR PRÉ-SEPARAÇÕES
                    # ========================================
                    pre_separacoes = PreSeparacaoItem.query.filter(
                        PreSeparacaoItem.num_pedido == pedido.num_pedido,
                        PreSeparacaoItem.status.in_(['CRIADO', 'RECOMPOSTO'])
                    ).all()
                    
                    for pre_sep in pre_separacoes:
                        # Buscar item específico da carteira para este produto
                        item_produto = CarteiraPrincipal.query.filter(
                            and_(
                                CarteiraPrincipal.num_pedido == pre_sep.num_pedido,
                                CarteiraPrincipal.cod_produto == pre_sep.cod_produto,
                                CarteiraPrincipal.ativo == True
                            )
                        ).first()
                        
                        if not item_produto:
                            item_produto = item_carteira  # Usar dados gerais do pedido
                        
                        campos_alterados_pre = []
                        
                        # CNPJ (campo é cnpj_cliente em PreSeparacaoItem)
                        if pre_sep.cnpj_cliente != item_produto.cnpj_cpf:
                            pre_sep.cnpj_cliente = item_produto.cnpj_cpf
                            campos_alterados_pre.append('cnpj_cliente')
                        
                        # PreSeparacaoItem NÃO tem os campos:
                        # - raz_social_red
                        # - nome_cidade
                        # - cod_uf
                        # - rota
                        # - sub_rota
                        
                        # Observação (campo é observacoes_usuario em PreSeparacaoItem)
                        # Vamos adicionar a observação da carteira ao campo de observações do usuário
                        # sem sobrescrever completamente
                        if item_produto.observ_ped_1:
                            obs_carteira = f"[Obs. Pedido]: {item_produto.observ_ped_1}"
                            if not pre_sep.observacoes_usuario:
                                pre_sep.observacoes_usuario = obs_carteira
                                campos_alterados_pre.append('observacoes_usuario')
                            elif obs_carteira not in pre_sep.observacoes_usuario:
                                # Adicionar observação da carteira se ainda não estiver presente
                                pre_sep.observacoes_usuario = f"{pre_sep.observacoes_usuario}\n{obs_carteira}"
                                campos_alterados_pre.append('observacoes_usuario')
                        
                        if campos_alterados_pre:
                            self.total_pre_separacoes_atualizadas += 1
                            logger.debug(f"✅ Pré-separação {pre_sep.num_pedido}/{pre_sep.cod_produto} atualizada")
                
                except Exception as e:
                    erro_msg = f"Erro ao processar pedido {pedido.num_pedido}: {str(e)}"
                    logger.error(erro_msg)
                    self.erros_encontrados.append(erro_msg)
                    continue
            
            # Commit das alterações
            if self.total_pedidos_atualizados > 0 or self.total_separacoes_atualizadas > 0 or self.total_pre_separacoes_atualizadas > 0:
                db.session.commit()
                logger.info("✅ Alterações salvas no banco de dados")
            
            # Resumo da operação
            resumo = {
                'sucesso': True,
                'total_pedidos_atualizados': self.total_pedidos_atualizados,
                'total_separacoes_atualizadas': self.total_separacoes_atualizadas,
                'total_pre_separacoes_atualizadas': self.total_pre_separacoes_atualizadas,
                'total_pedidos_processados': len(pedidos_nao_faturados),
                'erros': self.erros_encontrados
            }
            
            logger.info(f"""
                ✅ ATUALIZAÇÃO DE DADOS CONCLUÍDA:
                - Pedidos processados: {resumo['total_pedidos_processados']}
                - Pedidos atualizados: {resumo['total_pedidos_atualizados']}
                - Separações atualizadas: {resumo['total_separacoes_atualizadas']}
                - Pré-separações atualizadas: {resumo['total_pre_separacoes_atualizadas']}
                - Erros encontrados: {len(resumo['erros'])}
            """)
            
            return resumo
            
        except Exception as e:
            logger.error(f"❌ Erro crítico na atualização de dados: {str(e)}")
            db.session.rollback()
            return {
                'sucesso': False,
                'erro': str(e),
                'total_pedidos_atualizados': self.total_pedidos_atualizados,
                'total_separacoes_atualizadas': self.total_separacoes_atualizadas,
                'total_pre_separacoes_atualizadas': self.total_pre_separacoes_atualizadas,
                'erros': self.erros_encontrados
            }
    
    def _calcular_rota(self, item_carteira):
        """
        Calcula a rota baseado no incoterm ou UF
        
        Regra:
        - Se incoterm for RED → rota = 'RED'
        - Se incoterm for FOB → rota = 'FOB'
        - Senão → buscar rota por UF
        
        Args:
            item_carteira: Item da CarteiraPrincipal
            
        Returns:
            str: Rota calculada
        """
        if hasattr(item_carteira, 'incoterm') and item_carteira.incoterm in ['RED', 'FOB']:
            return item_carteira.incoterm
        else:
            return buscar_rota_por_uf(item_carteira.cod_uf or 'SP')