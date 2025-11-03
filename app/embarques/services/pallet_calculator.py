"""
Serviço para cálculo preciso de pallets usando CadastroPalletizacao
✅ FONTE DA VERDADE: Sempre usa palletização do cadastro de produtos
"""
from app import db
from app.producao.models import CadastroPalletizacao
from app.separacao.models import Separacao
from app.faturamento.models import FaturamentoProduto
import logging

logger = logging.getLogger(__name__)


class PalletCalculator:
    """Calculadora inteligente de pallets baseada em CadastroPalletizacao"""

    @staticmethod
    def calcular_pallets_por_produto(cod_produto: str, quantidade: float) -> float:
        """
        Calcula pallets para um produto específico usando CadastroPalletizacao

        Args:
            cod_produto: Código do produto
            quantidade: Quantidade em unidades

        Returns:
            float: Quantidade de pallets (arredondado para 2 casas)
        """
        try:
            cadastro = CadastroPalletizacao.query.filter_by(
                cod_produto=cod_produto,
                ativo=True
            ).first()

            if cadastro and cadastro.palletizacao > 0:
                pallets = quantidade / cadastro.palletizacao
                logger.debug(f"[PALLET] {cod_produto}: {quantidade} un ÷ {cadastro.palletizacao} = {pallets:.2f} pallets")
                return round(pallets, 2)
            else:
                logger.warning(f"[PALLET] ⚠️ Produto {cod_produto} sem palletização cadastrada")
                return 0

        except Exception as e:
            logger.error(f"[PALLET] ❌ Erro ao calcular pallets para {cod_produto}: {str(e)}")
            return 0

    @staticmethod
    def calcular_pallets_separacao_lote(separacao_lote_id: str) -> float:
        """
        Calcula total de pallets para um lote de separação
        Soma pallets de TODOS os produtos do lote usando CadastroPalletizacao

        Args:
            separacao_lote_id: ID do lote de separação

        Returns:
            float: Total de pallets do lote
        """
        try:
            separacoes = Separacao.query.filter_by(
                separacao_lote_id=separacao_lote_id
            ).all()

            if not separacoes:
                logger.warning(f"[PALLET] ⚠️ Lote {separacao_lote_id} não encontrado em Separacao")
                return 0

            total_pallets = 0
            produtos_calculados = []

            for sep in separacoes:
                if sep.cod_produto and sep.qtd_saldo:
                    pallets_item = PalletCalculator.calcular_pallets_por_produto(
                        sep.cod_produto,
                        float(sep.qtd_saldo)
                    )
                    total_pallets += pallets_item
                    produtos_calculados.append({
                        'produto': sep.cod_produto,
                        'qtd': sep.qtd_saldo,
                        'pallets': pallets_item
                    })

            logger.info(f"[PALLET] ✅ Lote {separacao_lote_id}: {len(produtos_calculados)} produtos = {total_pallets:.2f} pallets")
            for p in produtos_calculados:
                logger.debug(f"[PALLET]   - {p['produto']}: {p['qtd']} un = {p['pallets']} pallets")

            return round(total_pallets, 2)

        except Exception as e:
            logger.error(f"[PALLET] ❌ Erro ao calcular pallets do lote {separacao_lote_id}: {str(e)}")
            return 0

    @staticmethod
    def calcular_pallets_por_nf(numero_nf: str) -> float:
        """
        Calcula total de pallets para uma NF usando dados de FaturamentoProduto
        Usa CadastroPalletizacao para cada produto da NF

        Args:
            numero_nf: Número da nota fiscal

        Returns:
            float: Total de pallets da NF
        """
        try:
            produtos_nf = FaturamentoProduto.query.filter_by(
                numero_nf=numero_nf
            ).all()

            if not produtos_nf:
                logger.warning(f"[PALLET] ⚠️ NF {numero_nf} não encontrada em FaturamentoProduto")
                return 0

            total_pallets = 0
            produtos_calculados = []

            for produto in produtos_nf:
                if produto.cod_produto and produto.qtd_produto_faturado:
                    pallets_item = PalletCalculator.calcular_pallets_por_produto(
                        produto.cod_produto,
                        float(produto.qtd_produto_faturado)
                    )
                    total_pallets += pallets_item
                    produtos_calculados.append({
                        'produto': produto.cod_produto,
                        'qtd': produto.qtd_produto_faturado,
                        'pallets': pallets_item
                    })

            logger.info(f"[PALLET] ✅ NF {numero_nf}: {len(produtos_calculados)} produtos = {total_pallets:.2f} pallets")
            for p in produtos_calculados:
                logger.debug(f"[PALLET]   - {p['produto']}: {p['qtd']} un = {p['pallets']} pallets")

            return round(total_pallets, 2)

        except Exception as e:
            logger.error(f"[PALLET] ❌ Erro ao calcular pallets da NF {numero_nf}: {str(e)}")
            return 0

    @staticmethod
    def calcular_pallets_embarque_item(item_embarque) -> float:
        """
        Calcula pallets para um EmbarqueItem baseado no separacao_lote_id

        Args:
            item_embarque: Instância de EmbarqueItem

        Returns:
            float: Total de pallets calculado
        """
        if not item_embarque.separacao_lote_id:
            logger.warning(f"[PALLET] ⚠️ EmbarqueItem {item_embarque.id} sem separacao_lote_id")
            return 0

        return PalletCalculator.calcular_pallets_separacao_lote(
            item_embarque.separacao_lote_id
        )

    @staticmethod
    def recalcular_pallets_embarque(embarque) -> dict:
        """
        Recalcula TODOS os pallets de um embarque (itens + total)
        Atualiza banco de dados

        Args:
            embarque: Instância de Embarque

        Returns:
            dict: Resultado com totais antigos e novos
        """
        try:
            pallet_total_antigo = embarque.pallet_total or 0
            pallet_total_novo = 0
            itens_atualizados = []

            # Recalcula pallets de cada item ativo
            for item in embarque.itens:
                if item.status == 'ativo':
                    pallets_antigo = item.pallets or 0

                    # Se tem NF, usa dados da NF
                    if item.nota_fiscal and item.nota_fiscal.strip():
                        pallets_novo = PalletCalculator.calcular_pallets_por_nf(item.nota_fiscal)
                    # Senão, usa separacao_lote_id
                    elif item.separacao_lote_id:
                        pallets_novo = PalletCalculator.calcular_pallets_separacao_lote(item.separacao_lote_id)
                    else:
                        pallets_novo = 0

                    # Atualiza item
                    item.pallets = pallets_novo
                    pallet_total_novo += pallets_novo

                    itens_atualizados.append({
                        'pedido': item.pedido,
                        'pallets_antigo': pallets_antigo,
                        'pallets_novo': pallets_novo,
                        'diferenca': pallets_novo - pallets_antigo
                    })

            # Atualiza total do embarque
            embarque.pallet_total = pallet_total_novo
            db.session.commit()

            resultado = {
                'success': True,
                'pallet_total_antigo': pallet_total_antigo,
                'pallet_total_novo': pallet_total_novo,
                'diferenca_total': pallet_total_novo - pallet_total_antigo,
                'itens_atualizados': len(itens_atualizados),
                'detalhes_itens': itens_atualizados
            }

            logger.info(f"[PALLET] ✅ Embarque #{embarque.numero} recalculado: {pallet_total_antigo:.2f} → {pallet_total_novo:.2f} pallets")

            return resultado

        except Exception as e:
            db.session.rollback()
            logger.error(f"[PALLET] ❌ Erro ao recalcular embarque #{embarque.numero}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
