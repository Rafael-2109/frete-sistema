"""
Serviço de Sincronização Manual de Pedido Específico
=====================================================

Permite atualizar ou excluir um pedido específico do Odoo de forma manual.

REGRAS:
- Se pedido ENCONTRADO no Odoo: ATUALIZA conforme sincronização incremental
- Se pedido NÃO ENCONTRADO no Odoo: EXCLUI completamente do sistema

Autor: Sistema de Fretes
Data: 2025-01-20
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from app import db
from app.odoo.utils.connection import get_odoo_connection
from app.odoo.services.carteira_service import CarteiraService
from app.odoo.services.ajuste_sincronizacao_service import AjusteSincronizacaoService
from app.faturamento.models import FaturamentoProduto
from sqlalchemy import func

logger = logging.getLogger(__name__)


class PedidoSyncService:
    """
    Serviço para sincronizar um pedido específico com o Odoo

    Permite atualização ou exclusão manual de pedidos individuais
    """

    def __init__(self):
        self.connection = get_odoo_connection()
        self.carteira_service = CarteiraService()
        self.ajuste_service = AjusteSincronizacaoService()

    def sincronizar_pedido_especifico(self, num_pedido: str) -> Dict[str, Any]:
        """
        Sincroniza um pedido específico com o Odoo

        FLUXO:
        1. Buscar pedido no Odoo
        2. Se NÃO ENCONTRADO → EXCLUIR do sistema
        3. Se ENCONTRADO → ATUALIZAR conforme Odoo

        Args:
            num_pedido: Número do pedido a sincronizar

        Returns:
            Dict com resultado da operação:
            {
                'sucesso': bool,
                'acao': 'ATUALIZADO' | 'EXCLUIDO' | 'NAO_PROCESSADO',
                'mensagem': str,
                'detalhes': dict,
                'timestamp': datetime
            }
        """
        inicio = datetime.now()

        try:
            logger.info(f"🔄 Iniciando sincronização manual do pedido {num_pedido}")

            # Validar conexão com Odoo
            if not self.connection:
                return {
                    'sucesso': False,
                    'acao': 'NAO_PROCESSADO',
                    'mensagem': 'Conexão com Odoo não disponível',
                    'erro': 'Conexão indisponível',
                    'timestamp': datetime.now()
                }

            # ETAPA 1: Buscar pedido no Odoo
            logger.info(f"🔍 Buscando pedido {num_pedido} no Odoo...")
            pedido_odoo = self._buscar_pedido_odoo(num_pedido)

            # ETAPA 2: Decidir ação baseado no resultado
            if pedido_odoo is None:
                # NÃO ENCONTRADO → EXCLUIR
                logger.warning(f"⚠️ Pedido {num_pedido} NÃO ENCONTRADO no Odoo - será EXCLUÍDO")
                resultado = self._excluir_pedido_sistema(num_pedido)

            elif pedido_odoo == 'CANCELADO':
                # CANCELADO no Odoo → EXCLUIR
                logger.warning(f"⚠️ Pedido {num_pedido} CANCELADO no Odoo - será EXCLUÍDO")
                resultado = self._excluir_pedido_sistema(num_pedido)

            else:
                # ENCONTRADO → ATUALIZAR
                logger.info(f"✅ Pedido {num_pedido} encontrado no Odoo - será ATUALIZADO")
                resultado = self._atualizar_pedido_sistema(num_pedido, pedido_odoo)

            # Adicionar tempo de execução
            tempo_total = (datetime.now() - inicio).total_seconds()
            resultado['tempo_execucao'] = round(tempo_total, 2)
            resultado['timestamp'] = datetime.now()

            logger.info(f"✅ Sincronização do pedido {num_pedido} concluída em {tempo_total:.2f}s - Ação: {resultado['acao']}")

            return resultado

        except Exception as e:
            tempo_total = (datetime.now() - inicio).total_seconds()
            logger.error(f"❌ Erro ao sincronizar pedido {num_pedido}: {e}")

            return {
                'sucesso': False,
                'acao': 'NAO_PROCESSADO',
                'mensagem': f'Erro ao sincronizar pedido: {str(e)}',
                'erro': str(e),
                'tempo_execucao': round(tempo_total, 2),
                'timestamp': datetime.now()
            }

    def _buscar_pedido_odoo(self, num_pedido: str) -> Optional[Any]:
        """
        Busca pedido no Odoo e retorna dados ou None se não encontrado

        Returns:
            - Dict com dados do pedido se encontrado
            - 'CANCELADO' se pedido está cancelado
            - None se não encontrado
        """
        try:
            # Buscar sale.order pelo nome usando OdooConnection
            domain = [('name', '=', num_pedido)]

            pedidos = self.connection.search_read(
                model='sale.order',
                domain=domain,
                fields=['id', 'name', 'state', 'l10n_br_tipo_pedido'],
                limit=1
            )

            if not pedidos or len(pedidos) == 0:
                logger.warning(f"⚠️ Pedido {num_pedido} não encontrado no Odoo")
                return None

            pedido = pedidos[0]

            # Verificar se está cancelado
            if pedido.get('state') == 'cancel':
                logger.warning(f"⚠️ Pedido {num_pedido} está CANCELADO no Odoo")
                return 'CANCELADO'

            logger.info(f"✅ Pedido {num_pedido} encontrado no Odoo - State: {pedido.get('state')}, Tipo: {pedido.get('l10n_br_tipo_pedido')}")

            # Buscar linhas do pedido (sale.order.line)
            linhas_domain = [('order_id', '=', pedido['id'])]

            linhas = self.connection.search_read(
                model='sale.order.line',
                domain=linhas_domain,
                fields=[
                    'id',
                    'product_id',
                    'product_uom_qty',  # Quantidade total do pedido
                    'qty_delivered',     # Quantidade já entregue
                    'qty_invoiced',      # Quantidade já faturada
                    'qty_to_invoice',    # Quantidade a faturar (calculado)
                    'price_unit',
                    # Campos customizados (se existirem no seu Odoo)
                    'qty_saldo',         # Campo customizado de saldo
                    'qty_cancelado'      # Campo customizado de cancelado
                ]
            )

            logger.info(f"📦 Encontradas {len(linhas)} linhas para o pedido {num_pedido}")

            # LOG CRÍTICO: Mostrar EXATAMENTE o que veio do Odoo
            logger.warning("=" * 80)
            logger.warning("🔍 DADOS BRUTOS DO ODOO - VERIFIQUE OS VALORES:")
            for idx, linha in enumerate(linhas, 1):
                logger.warning(f"   Linha {idx}:")
                logger.warning(f"      product_id = {linha.get('product_id')}")
                logger.warning(f"      product_uom_qty = {linha.get('product_uom_qty')}")
                logger.warning(f"      qty_saldo = {linha.get('qty_saldo')} ← ⚠️ ESTE CAMPO É CRÍTICO!")
                logger.warning(f"      qty_cancelado = {linha.get('qty_cancelado')}")
                logger.warning(f"      qty_delivered = {linha.get('qty_delivered')}")
                logger.warning(f"      qty_invoiced = {linha.get('qty_invoiced')}")
                logger.warning(f"      price_unit = {linha.get('price_unit')}")
            logger.warning("=" * 80)

            return {
                'pedido': pedido,
                'linhas': linhas,
                'num_pedido': num_pedido
            }

        except Exception as e:
            logger.error(f"❌ Erro ao buscar pedido {num_pedido} no Odoo: {e}")
            raise

    def _excluir_pedido_sistema(self, num_pedido: str) -> Dict[str, Any]:
        """
        Exclui pedido completamente do sistema usando a função existente

        Reutiliza: CarteiraService._processar_cancelamento_pedido()
        """
        try:
            logger.info(f"🗑️ Excluindo pedido {num_pedido} do sistema...")

            # Usar função existente de cancelamento
            sucesso = self.carteira_service._processar_cancelamento_pedido(num_pedido)

            if sucesso:
                db.session.commit()
                logger.info(f"✅ Pedido {num_pedido} EXCLUÍDO com sucesso")

                return {
                    'sucesso': True,
                    'acao': 'EXCLUIDO',
                    'mensagem': f'Pedido {num_pedido} excluído completamente do sistema (não encontrado no Odoo)',
                    'detalhes': {
                        'num_pedido': num_pedido,
                        'motivo': 'Pedido não encontrado ou cancelado no Odoo'
                    }
                }
            else:
                db.session.rollback()
                return {
                    'sucesso': False,
                    'acao': 'NAO_PROCESSADO',
                    'mensagem': f'Falha ao excluir pedido {num_pedido}',
                    'erro': 'Erro no processamento de cancelamento'
                }

        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ Erro ao excluir pedido {num_pedido}: {e}")

            return {
                'sucesso': False,
                'acao': 'NAO_PROCESSADO',
                'mensagem': f'Erro ao excluir pedido: {str(e)}',
                'erro': str(e)
            }

    def _atualizar_pedido_sistema(self, num_pedido: str, dados_odoo: Dict) -> Dict[str, Any]:
        """
        Atualiza pedido no sistema conforme dados do Odoo

        FLUXO:
        1. Atualiza CarteiraPrincipal com dados do Odoo
        2. Chama AjusteSincronizacaoService que atualiza Separações baseado na CarteiraPrincipal
        """
        try:
            logger.info(f"📝 Atualizando pedido {num_pedido} no sistema...")

            # Mapear dados do Odoo para formato do sistema
            itens_mapeados = self._mapear_linhas_odoo(dados_odoo)

            if not itens_mapeados:
                return {
                    'sucesso': False,
                    'acao': 'NAO_PROCESSADO',
                    'mensagem': f'Nenhum item válido encontrado para o pedido {num_pedido}',
                    'detalhes': {'num_pedido': num_pedido}
                }

            logger.info(f"📊 {len(itens_mapeados)} itens mapeados do Odoo")

            # ETAPA 1: Atualizar CarteiraPrincipal
            logger.info(f"📝 ETAPA 1: Atualizando CarteiraPrincipal...")
            resultado_carteira = self._atualizar_carteira_principal(num_pedido, itens_mapeados)

            if not resultado_carteira['sucesso']:
                return resultado_carteira

            # ETAPA 2: Chamar AjusteSincronizacaoService que usa CarteiraPrincipal
            logger.info(f"🔄 ETAPA 2: Processando ajuste nas Separações via AjusteSincronizacaoService...")
            resultado_ajuste = self.ajuste_service.processar_pedido_alterado(
                num_pedido=num_pedido,
                itens_odoo=itens_mapeados
            )

            if resultado_ajuste.get('sucesso', False):
                db.session.commit()
                logger.info(f"✅ Pedido {num_pedido} ATUALIZADO com sucesso")

                return {
                    'sucesso': True,
                    'acao': 'ATUALIZADO',
                    'mensagem': f'Pedido {num_pedido} atualizado conforme dados do Odoo',
                    'detalhes': {
                        'num_pedido': num_pedido,
                        'itens_processados': len(itens_mapeados),
                        'tipo_processamento': resultado_ajuste.get('tipo_processamento'),
                        'alteracoes': resultado_ajuste.get('alteracoes_aplicadas', []),
                        'alertas': resultado_ajuste.get('alertas_gerados', [])
                    }
                }
            else:
                db.session.rollback()
                return {
                    'sucesso': False,
                    'acao': 'NAO_PROCESSADO',
                    'mensagem': f'Falha ao atualizar pedido {num_pedido}',
                    'erro': resultado_ajuste.get('erro', 'Erro desconhecido'),
                    'erros': resultado_ajuste.get('erros', [])
                }

        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ Erro ao atualizar pedido {num_pedido}: {e}")

            return {
                'sucesso': False,
                'acao': 'NAO_PROCESSADO',
                'mensagem': f'Erro ao atualizar pedido: {str(e)}',
                'erro': str(e)
            }

    def _atualizar_carteira_principal(self, num_pedido: str, itens_mapeados: List[Dict]) -> Dict[str, Any]:
        """
        Atualiza CarteiraPrincipal com dados do Odoo

        Similar ao que CarteiraService faz
        """
        try:
            from app.carteira.models import CarteiraPrincipal

            logger.info(f"🔄 Atualizando {len(itens_mapeados)} itens na CarteiraPrincipal...")

            itens_atualizados = 0

            for item in itens_mapeados:
                cod_produto = item['cod_produto']

                # Buscar item na CarteiraPrincipal
                item_carteira = CarteiraPrincipal.query.filter_by(
                    num_pedido=num_pedido,
                    cod_produto=cod_produto
                ).first()

                if item_carteira:
                    # ATUALIZAR quantidades
                    item_carteira.qtd_produto_pedido = item['qtd_produto_pedido']
                    item_carteira.qtd_saldo_produto_pedido = item['qtd_saldo_produto_pedido']
                    item_carteira.qtd_cancelada_produto_pedido = item['qtd_cancelada_produto_pedido']
                    item_carteira.preco_produto_pedido = item['preco_produto_pedido']

                    itens_atualizados += 1
                    logger.info(f"   ✅ Atualizado {cod_produto}: saldo={item['qtd_saldo_produto_pedido']}")
                else:
                    logger.warning(f"   ⚠️ Produto {cod_produto} não encontrado na CarteiraPrincipal")

            logger.info(f"✅ CarteiraPrincipal atualizada: {itens_atualizados} itens")

            return {
                'sucesso': True,
                'itens_atualizados': itens_atualizados
            }

        except Exception as e:
            logger.error(f"❌ Erro ao atualizar CarteiraPrincipal: {e}")
            return {
                'sucesso': False,
                'acao': 'NAO_PROCESSADO',
                'mensagem': f'Erro ao atualizar CarteiraPrincipal: {str(e)}',
                'erro': str(e)
            }

    def _mapear_linhas_odoo(self, dados_odoo: Dict) -> list:
        """
        Mapeia linhas do Odoo para formato esperado pelo AjusteSincronizacaoService

        IMPORTANTE: CALCULA o saldo como CarteiraService faz (linha 1627):
        qtd_saldo = qtd_produto - qtd_faturada

        Formato esperado:
        {
            'cod_produto': str,
            'qtd_saldo_produto_pedido': float,  ← CALCULADO, não vem direto do Odoo
            'nome_produto': str,
            'preco_produto_pedido': float,
        }
        """
        try:
            linhas_mapeadas = []
            num_pedido = dados_odoo.get('num_pedido')

            # BUSCAR quantidades já faturadas (como CarteiraSer vice faz - linha 1578-1596)
            logger.info(f"🔍 Buscando quantidades faturadas para pedido {num_pedido}...")

            faturamentos_dict = {}
            try:
                resultados = db.session.query(
                    FaturamentoProduto.cod_produto,
                    func.sum(FaturamentoProduto.qtd_produto_faturado).label('qtd_faturada')
                ).filter(
                    FaturamentoProduto.origem == num_pedido,
                    FaturamentoProduto.status_nf != 'Cancelado'
                ).group_by(
                    FaturamentoProduto.cod_produto
                ).all()

                for row in resultados:
                    faturamentos_dict[row.cod_produto] = float(row.qtd_faturada or 0)

                logger.info(f"✅ Encontrados {len(faturamentos_dict)} produtos com faturamento")
            except Exception as e:
                logger.error(f"❌ Erro ao buscar faturamentos: {e}")

            # MAPEAR cada linha calculando o saldo
            for linha in dados_odoo.get('linhas', []):
                # Extrair dados da linha
                product_id = linha.get('product_id')

                # product_id pode vir como [id, 'nome'] ou apenas id
                if isinstance(product_id, list) and len(product_id) > 1:
                    produto_nome = product_id[1]
                else:
                    produto_nome = ''

                # Buscar código do produto
                cod_produto = self._buscar_codigo_produto(linha.get('product_id'))

                if not cod_produto:
                    logger.warning(f"⚠️ Produto sem código encontrado, pulando linha")
                    continue

                # CALCULAR SALDO: qtd_produto - qtd_cancelada - qtd_faturada
                qtd_produto = float(linha.get('product_uom_qty', 0))
                qtd_cancelada = float(linha.get('qty_cancelado', 0) or 0)
                qtd_faturada = faturamentos_dict.get(cod_produto, 0)

                # FÓRMULA: qtd_produto - qtd_cancelada - qtd_faturada
                qtd_saldo_calculado = qtd_produto - qtd_cancelada - qtd_faturada

                logger.info(f"   📊 {cod_produto}: qtd_produto={qtd_produto}, "
                          f"qtd_cancelada={qtd_cancelada}, "
                          f"qtd_faturada={qtd_faturada}, "
                          f"qtd_saldo_CALCULADO={qtd_saldo_calculado}")

                item_mapeado = {
                    'cod_produto': cod_produto,
                    'nome_produto': produto_nome,
                    'qtd_produto_pedido': qtd_produto,
                    'qtd_saldo_produto_pedido': qtd_saldo_calculado,  # ← CALCULADO!
                    'qtd_cancelada_produto_pedido': linha.get('qty_cancelado', 0),
                    'preco_produto_pedido': linha.get('price_unit', 0)
                }

                linhas_mapeadas.append(item_mapeado)

            logger.info(f"✅ {len(linhas_mapeadas)} linhas mapeadas com saldo CALCULADO")
            return linhas_mapeadas

        except Exception as e:
            logger.error(f"❌ Erro ao mapear linhas do Odoo: {e}")
            return []

    def _buscar_codigo_produto(self, product_id) -> Optional[str]:
        """
        Busca código do produto (default_code) no Odoo
        """
        try:
            # product_id pode vir como [id, 'nome'] ou apenas id
            if isinstance(product_id, list) and len(product_id) > 0:
                prod_id = product_id[0]
            else:
                prod_id = product_id

            if not prod_id:
                return None

            # Usar OdooConnection.read()
            produto = self.connection.read(
                model='product.product',
                ids=[prod_id],
                fields=['default_code']
            )

            if produto and len(produto) > 0:
                return produto[0].get('default_code', '')

            return None

        except Exception as e:
            logger.error(f"❌ Erro ao buscar código do produto {product_id}: {e}")
            return None
