"""
Service para Importação de Entradas de Materiais do Odoo
=========================================================

OBJETIVO:
    Importar recebimentos de materiais (stock.picking + stock.move) do Odoo
    e registrar em MovimentacaoEstoque

REGRAS:
    1. Apenas stock.picking com state='done' (recebidos)
    2. Apenas picking_type_id.code='incoming' (entradas)
    3. Excluir fornecedores do grupo (CNPJ iniciando com 61.724.241 e 18.467.441)
    4. Vincular com PedidoCompras via purchase_id
    5. Registrar em MovimentacaoEstoque tipo=ENTRADA, local=COMPRA

AUTOR: Sistema de Fretes
DATA: 11/11/2025
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional
from sqlalchemy import and_

from app import db
from app.estoque.models import MovimentacaoEstoque
from app.manufatura.models import PedidoCompras
from app.producao.models import CadastroPalletizacao
from app.odoo.utils.connection import OdooConnection

logger = logging.getLogger(__name__)


class EntradaMaterialService:
    """
    Service para importação de entradas de materiais do Odoo
    """

    # CNPJs de empresas do grupo (estoque consolidado - não importar)
    CNPJS_GRUPO = ['61.724.241', '18.467.441']

    def __init__(self):
        """Inicializa conexão com Odoo"""
        self.odoo = OdooConnection()

    def _eh_fornecedor_grupo(self, cnpj: str) -> bool:
        """
        Verifica se o CNPJ é de uma empresa do grupo

        Args:
            cnpj: CNPJ do fornecedor

        Returns:
            True se for empresa do grupo
        """
        if not cnpj:
            return False

        # Remove formatação
        cnpj_limpo = cnpj.replace('.', '').replace('/', '').replace('-', '').strip()

        # Verifica se começa com algum CNPJ do grupo
        for cnpj_grupo in self.CNPJS_GRUPO:
            cnpj_grupo_limpo = cnpj_grupo.replace('.', '')
            if cnpj_limpo.startswith(cnpj_grupo_limpo):
                logger.info(f"⚠️  CNPJ {cnpj} é empresa do grupo - PULANDO")
                return True

        return False

    def importar_entradas(
        self,
        dias_retroativos: int = 7,
        limite: Optional[int] = None
    ) -> Dict:
        """
        Importa entradas de materiais do Odoo

        Args:
            dias_retroativos: Quantos dias para trás buscar (padrão: 7)
            limite: Limite de registros (None = todos)

        Returns:
            Dict com estatísticas da importação
        """
        logger.info("=" * 80)
        logger.info("🚚 INICIANDO IMPORTAÇÃO DE ENTRADAS DE MATERIAIS")
        logger.info("=" * 80)

        resultado = {
            'sucesso': False,
            'entradas_processadas': 0,
            'entradas_novas': 0,
            'entradas_atualizadas': 0,
            'entradas_ignoradas': 0,
            'erros': []
        }

        try:
            # 1. Buscar recebimentos do Odoo
            data_inicio = (datetime.now() - timedelta(days=dias_retroativos)).strftime('%Y-%m-%d')

            logger.info(f"📅 Buscando recebimentos desde {data_inicio}")

            pickings = self._buscar_recebimentos_odoo(data_inicio, limite)

            if not pickings:
                logger.warning("⚠️  Nenhum recebimento encontrado no Odoo")
                resultado['sucesso'] = True
                return resultado

            logger.info(f"📦 Total de recebimentos encontrados: {len(pickings)}")

            # 2. Processar cada recebimento
            for picking in pickings:
                try:
                    picking_id = picking.get('id')
                    picking_name = picking.get('name')

                    logger.info(f"\n📋 Processando recebimento: {picking_name} (ID: {picking_id})")

                    # 2.1 Verificar fornecedor
                    partner = picking.get('partner_id')
                    if not partner or len(partner) < 2:
                        logger.warning(f"⚠️  Recebimento {picking_name} sem fornecedor - PULANDO")
                        resultado['entradas_ignoradas'] += 1
                        continue

                    # Buscar CNPJ do fornecedor
                    partner_id = partner[0]
                    cnpj_fornecedor = self._buscar_cnpj_fornecedor(partner_id)

                    if self._eh_fornecedor_grupo(cnpj_fornecedor):
                        logger.info(f"   ⏭️  Fornecedor do grupo - PULANDO")
                        resultado['entradas_ignoradas'] += 1
                        continue

                    # 2.2 Buscar movimentos do picking
                    movimentos = self._buscar_movimentos_picking(picking_id)

                    if not movimentos:
                        logger.warning(f"⚠️  Recebimento {picking_name} sem movimentos - PULANDO")
                        resultado['entradas_ignoradas'] += 1
                        continue

                    logger.info(f"   📦 Movimentos encontrados: {len(movimentos)}")

                    # 2.3 Processar cada movimento
                    for movimento in movimentos:
                        try:
                            estatisticas = self._processar_movimento(
                                picking=picking,
                                movimento=movimento,
                                cnpj_fornecedor=cnpj_fornecedor
                            )

                            resultado['entradas_processadas'] += 1
                            if estatisticas.get('novo'):
                                resultado['entradas_novas'] += 1
                            else:
                                resultado['entradas_atualizadas'] += 1

                        except Exception as e:
                            erro_msg = f"Erro ao processar movimento {movimento.get('id')}: {str(e)}"
                            logger.error(f"❌ {erro_msg}")
                            resultado['erros'].append(erro_msg)

                except Exception as e:
                    erro_msg = f"Erro ao processar recebimento {picking.get('name')}: {str(e)}"
                    logger.error(f"❌ {erro_msg}")
                    resultado['erros'].append(erro_msg)

            # 3. Commit final
            db.session.commit()

            resultado['sucesso'] = True
            logger.info("=" * 80)
            logger.info("✅ IMPORTAÇÃO DE ENTRADAS CONCLUÍDA")
            logger.info(f"   📊 Processadas: {resultado['entradas_processadas']}")
            logger.info(f"   ✨ Novas: {resultado['entradas_novas']}")
            logger.info(f"   🔄 Atualizadas: {resultado['entradas_atualizadas']}")
            logger.info(f"   ⏭️  Ignoradas: {resultado['entradas_ignoradas']}")
            logger.info(f"   ❌ Erros: {len(resultado['erros'])}")
            logger.info("=" * 80)

            return resultado

        except Exception as e:
            db.session.rollback()
            erro_msg = f"Erro fatal na importação de entradas: {str(e)}"
            logger.error(f"❌ {erro_msg}")
            resultado['erros'].append(erro_msg)
            resultado['sucesso'] = False
            return resultado

    def _buscar_recebimentos_odoo(
        self,
        data_inicio: str,
        limite: Optional[int]
    ) -> List[Dict]:
        """
        Busca recebimentos no Odoo

        Args:
            data_inicio: Data mínima (YYYY-MM-DD)
            limite: Limite de registros

        Returns:
            Lista de recebimentos
        """
        try:
            filtros = [
                ['picking_type_code', '=', 'incoming'],  # Apenas recebimentos
                ['state', '=', 'done'],                  # Apenas concluídos
                ['date_done', '>=', data_inicio]         # Data >= início
            ]

            campos = [
                'id',
                'name',
                'state',
                'date_done',
                'scheduled_date',
                'origin',
                'partner_id',
                'purchase_id',
                'location_dest_id',
                'move_ids_without_package'
            ]

            params = {'fields': campos}
            if limite:
                params['limit'] = limite

            pickings = self.odoo.execute_kw(
                'stock.picking',
                'search_read',
                [filtros],
                params
            )

            return pickings or []

        except Exception as e:
            logger.error(f"❌ Erro ao buscar recebimentos do Odoo: {e}")
            return []

    def _buscar_cnpj_fornecedor(self, partner_id: int) -> Optional[str]:
        """
        Busca CNPJ do fornecedor no Odoo

        Args:
            partner_id: ID do fornecedor

        Returns:
            CNPJ ou None
        """
        try:
            partner = self.odoo.execute_kw(
                'res.partner',
                'read',
                [[partner_id]],
                {'fields': ['l10n_br_cnpj_cpf', 'vat']}
            )

            if partner and len(partner) > 0:
                return partner[0].get('l10n_br_cnpj_cpf') or partner[0].get('vat')

            return None

        except Exception as e:
            logger.error(f"❌ Erro ao buscar CNPJ do fornecedor {partner_id}: {e}")
            return None

    def _buscar_movimentos_picking(self, picking_id: int) -> List[Dict]:
        """
        Busca movimentos de um picking

        Args:
            picking_id: ID do picking

        Returns:
            Lista de movimentos
        """
        try:
            filtros = [['picking_id', '=', picking_id]]

            campos = [
                'id',
                'picking_id',
                'product_id',
                'product_uom_qty',
                'quantity',
                'quantity_done',
                'product_uom',
                'date',
                'state',
                'origin',
                'purchase_line_id'
            ]

            movimentos = self.odoo.execute_kw(
                'stock.move',
                'search_read',
                [filtros],
                {'fields': campos}
            )

            return movimentos or []

        except Exception as e:
            logger.error(f"❌ Erro ao buscar movimentos do picking {picking_id}: {e}")
            return []

    def _processar_movimento(
        self,
        picking: Dict,
        movimento: Dict,
        cnpj_fornecedor: str
    ) -> Dict:
        """
        Processa um movimento e cria/atualiza MovimentacaoEstoque

        Args:
            picking: Dados do picking
            movimento: Dados do movimento
            cnpj_fornecedor: CNPJ do fornecedor

        Returns:
            Dict com estatísticas
        """
        # 1. Extrair dados do movimento
        move_id = str(movimento.get('id'))
        picking_id = str(picking.get('id'))
        picking_name = picking.get('name')

        product = movimento.get('product_id')
        if not product or len(product) < 2:
            logger.warning(f"⚠️  Movimento {move_id} sem produto - PULANDO")
            return {'novo': False}

        product_id, product_name = product[0], product[1]

        # Buscar default_code
        cod_produto = self._buscar_codigo_produto(product_id)
        if not cod_produto:
            logger.warning(f"⚠️  Produto {product_id} sem código - PULANDO")
            return {'novo': False}

        # 2. Verificar se produto é comprado
        produto_cadastro = CadastroPalletizacao.query.filter_by(
            cod_produto=str(cod_produto),
            produto_comprado=True
        ).first()

        if not produto_cadastro:
            logger.debug(f"   ⏭️  Produto {cod_produto} não é comprado - PULANDO")
            return {'novo': False}

        # 3. Quantidade recebida
        qtd_recebida = Decimal(str(movimento.get('quantity_done', 0)))
        if qtd_recebida <= 0:
            logger.warning(f"⚠️  Movimento {move_id} com quantidade zero - PULANDO")
            return {'novo': False}

        # 4. Data do recebimento
        date_done_str = picking.get('date_done')
        if date_done_str:
            date_done = datetime.fromisoformat(date_done_str.replace('Z', '+00:00')).date()
        else:
            date_done = datetime.now().date()

        # 5. Vincular com pedido local
        purchase_id_odoo = picking.get('purchase_id')
        pedido_local = None

        if purchase_id_odoo and len(purchase_id_odoo) >= 1:
            purchase_odoo_id = str(purchase_id_odoo[0])
            pedido_local = PedidoCompras.query.filter_by(
                odoo_id=purchase_odoo_id
            ).first()

        # 6. Verificar se já existe
        movimentacao_existe = MovimentacaoEstoque.query.filter_by(
            odoo_move_id=move_id
        ).first()

        if movimentacao_existe:
            # Atualizar
            logger.info(f"   🔄 Atualizando movimentação existente: {cod_produto}")
            movimentacao_existe.qtd_movimentacao = qtd_recebida
            movimentacao_existe.data_movimentacao = date_done
            movimentacao_existe.atualizado_em = datetime.now()
            movimentacao_existe.atualizado_por = 'Sistema Odoo'

            return {'novo': False}

        # 7. Criar nova movimentação
        logger.info(f"   ✨ Criando nova movimentação: {cod_produto} - {qtd_recebida}")

        movimentacao = MovimentacaoEstoque(
            # Produto
            cod_produto=str(cod_produto),
            nome_produto=product_name,

            # Movimentação
            data_movimentacao=date_done,
            tipo_movimentacao='ENTRADA',
            local_movimentacao='COMPRA',
            qtd_movimentacao=qtd_recebida,

            # Rastreabilidade
            num_pedido=picking.get('origin') or picking_name,
            tipo_origem='ODOO',

            # Odoo - Rastreabilidade
            odoo_picking_id=picking_id,
            odoo_move_id=move_id,
            purchase_line_id=str(movimento.get('purchase_line_id')) if movimento.get('purchase_line_id') else None,
            pedido_compras_id=pedido_local.id if pedido_local else None,

            # Observação
            observacao=f"Recebimento {picking_name} - Fornecedor CNPJ: {cnpj_fornecedor or 'N/A'}",

            # Auditoria
            criado_por='Sistema Odoo',
            ativo=True
        )

        db.session.add(movimentacao)

        return {'novo': True}

    def _buscar_codigo_produto(self, product_id: int) -> Optional[str]:
        """
        Busca default_code do produto no Odoo

        Args:
            product_id: ID do produto

        Returns:
            Código do produto ou None
        """
        try:
            produto = self.odoo.execute_kw(
                'product.product',
                'read',
                [[product_id]],
                {'fields': ['default_code']}
            )

            if produto and len(produto) > 0:
                return produto[0].get('default_code')

            return None

        except Exception as e:
            logger.error(f"❌ Erro ao buscar código do produto {product_id}: {e}")
            return None
