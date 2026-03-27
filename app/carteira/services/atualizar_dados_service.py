"""
Serviço para atualizar dados de Separacao baseado nos dados da CarteiraPrincipal

Atualiza todas as separações não sincronizadas (sincronizado_nf=False),
"""

from sqlalchemy import and_, func
from app import db
from app.carteira.models import CarteiraPrincipal
from app.separacao.models import Separacao
from app.carteira.utils.separacao_utils import buscar_rota_por_uf, buscar_sub_rota_por_uf_cidade
from app.utils.text_utils import truncar_observacao
import logging

logger = logging.getLogger(__name__)


class AtualizarDadosService:
    """
    Serviço para atualizar dados de Separacao baseado nos dados da CarteiraPrincipal
    """
    
    def __init__(self):
        self.total_separacoes_atualizadas = 0
        self.total_pedidos_processados = 0
        self.erros_encontrados = []
    
    def atualizar_dados_pos_sincronizacao(self):
        """
        Atualiza Separacao com dados da CarteiraPrincipal
        para todas as separações não sincronizadas (sincronizado_nf=False)
        
        Campos atualizados:
        1. CNPJ
        2. raz_social_red
        3. Cidade
        4. UF
        5. Rota (com regra de incoterm FOB e RED)
        6. SubRota
        7. Observação
        8. Tags do Pedido (Odoo)
        
        Returns:
            dict: Resumo da atualização
        """
        try:
            logger.info("🔄 Iniciando atualização de dados baseado na CarteiraPrincipal...")
            
            # Buscar todos os pedidos únicos das separações não sincronizadas
            pedidos_nao_sincronizados = db.session.query(
                func.distinct(Separacao.num_pedido)
            ).filter(
                Separacao.sincronizado_nf == False
            ).all()
            
            pedidos_unicos = [p[0] for p in pedidos_nao_sincronizados if p[0]]
            logger.info(f"📋 Encontrados {len(pedidos_unicos)} pedidos com separações não sincronizadas")

            # ==================================================================
            # BATCH LOADING: 2 queries substituem ~1000+ queries N+1
            # ==================================================================
            all_carteira = CarteiraPrincipal.query.filter(
                CarteiraPrincipal.num_pedido.in_(pedidos_unicos),
                CarteiraPrincipal.ativo == True
            ).all() if pedidos_unicos else []

            # Cache por pedido (primeiro item) e por (pedido, produto)
            carteira_por_pedido = {}
            carteira_por_chave = {}
            for item in all_carteira:
                if item.num_pedido not in carteira_por_pedido:
                    carteira_por_pedido[item.num_pedido] = item
                carteira_por_chave[(item.num_pedido, item.cod_produto)] = item

            all_separacoes = Separacao.query.filter(
                Separacao.num_pedido.in_(pedidos_unicos),
                Separacao.sincronizado_nf == False
            ).all() if pedidos_unicos else []

            seps_por_pedido = {}
            for sep in all_separacoes:
                seps_por_pedido.setdefault(sep.num_pedido, []).append(sep)

            logger.info(
                f"   [BATCH] Carregados {len(all_carteira)} itens carteira, "
                f"{len(all_separacoes)} separações (2 queries vs ~{len(pedidos_unicos)*3} N+1)"
            )

            for num_pedido in pedidos_unicos:
                try:
                    # O(1) lookup em vez de query individual
                    item_carteira = carteira_por_pedido.get(num_pedido)

                    if not item_carteira:
                        logger.debug(f"⚠️ Nenhum item encontrado na carteira para pedido {num_pedido}")
                        continue

                    self.total_pedidos_processados += 1

                    # O(1) lookup em vez de query individual
                    separacoes = seps_por_pedido.get(num_pedido, [])

                    for separacao in separacoes:
                        # O(1) lookup em vez de query individual
                        item_produto = carteira_por_chave.get(
                            (separacao.num_pedido, separacao.cod_produto)
                        )

                        if not item_produto:
                            item_produto = item_carteira  # Usar dados gerais do pedido
                        
                        campos_alterados = []
                        
                        # CNPJ
                        if separacao.cnpj_cpf != item_produto.cnpj_cpf:
                            separacao.cnpj_cpf = item_produto.cnpj_cpf
                            campos_alterados.append('cnpj_cpf')
                        
                        # Razão Social
                        if separacao.raz_social_red != item_produto.raz_social_red:
                            separacao.raz_social_red = item_produto.raz_social_red
                            campos_alterados.append('raz_social_red')
                        
                        # Cidade
                        if separacao.nome_cidade != item_produto.nome_cidade:
                            separacao.nome_cidade = item_produto.nome_cidade
                            campos_alterados.append('nome_cidade')
                        
                        # UF
                        if separacao.cod_uf != item_produto.cod_uf:
                            separacao.cod_uf = item_produto.cod_uf
                            campos_alterados.append('cod_uf')
                        
                        # Rota - aplicar regra de incoterm
                        rota_calculada = self._calcular_rota(item_produto)
                        if separacao.rota != rota_calculada:
                            separacao.rota = rota_calculada
                            campos_alterados.append('rota')
                        
                        # SubRota
                        sub_rota_calculada = buscar_sub_rota_por_uf_cidade(
                            item_produto.cod_uf or '',
                            item_produto.nome_cidade or ''
                        )
                        if separacao.sub_rota != sub_rota_calculada:
                            separacao.sub_rota = sub_rota_calculada
                            campos_alterados.append('sub_rota')
                        
                        # Observação (trunca se necessário)
                        observacao_truncada = truncar_observacao(item_produto.observ_ped_1)
                        if separacao.observ_ped_1 != observacao_truncada:
                            separacao.observ_ped_1 = observacao_truncada
                            campos_alterados.append('observ_ped_1')

                        # Tags do Pedido (Odoo)
                        if separacao.tags_pedido != item_produto.tags_pedido:
                            separacao.tags_pedido = item_produto.tags_pedido
                            campos_alterados.append('tags_pedido')

                        if campos_alterados:
                            self.total_separacoes_atualizadas += 1
                            status_info = f" [{separacao.status}]" if separacao.status else ""
                            logger.debug(f"✅ Separação{status_info} {separacao.separacao_lote_id}/{separacao.cod_produto} atualizada")
                
                except Exception as e:
                    erro_msg = f"Erro ao processar pedido {num_pedido}: {str(e)}"
                    logger.error(erro_msg)
                    self.erros_encontrados.append(erro_msg)
                    continue
            
            # Commit das alterações
            if self.total_separacoes_atualizadas > 0:
                db.session.commit()
                logger.info("✅ Alterações salvas no banco de dados")
            
            # Resumo da operação
            resumo = {
                'sucesso': True,
                'total_separacoes_atualizadas': self.total_separacoes_atualizadas,
                'total_pedidos_atualizados': self.total_pedidos_processados,  # Compatibilidade com carteira_service
                'total_pedidos_processados': self.total_pedidos_processados,
                'erros': self.erros_encontrados
            }
            
            logger.info(f"""
                ✅ ATUALIZAÇÃO DE DADOS CONCLUÍDA:
                - Pedidos processados: {resumo['total_pedidos_processados']}
                - Separações atualizadas: {resumo['total_separacoes_atualizadas']}
                - Erros encontrados: {len(resumo['erros'])}
            """)
            
            return resumo
            
        except Exception as e:
            logger.error(f"❌ Erro crítico na atualização de dados: {str(e)}")
            db.session.rollback()
            return {
                'sucesso': False,
                'erro': str(e),
                'total_separacoes_atualizadas': self.total_separacoes_atualizadas,
                'total_pedidos_atualizados': self.total_pedidos_processados,  # Compatibilidade com carteira_service
                'total_pedidos_processados': self.total_pedidos_processados,
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