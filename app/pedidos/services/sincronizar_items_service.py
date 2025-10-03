"""
Serviço para sincronizar items de Separacao com FaturamentoProduto

Busca dados reais de quantidade, valor, peso e pallets do FaturamentoProduto
e atualiza a Separacao para refletir o que foi realmente faturado.
"""

import logging
from typing import Dict, Any
from app import db
from app.separacao.models import Separacao
from app.faturamento.models import FaturamentoProduto
from app.producao.models import CadastroPalletizacao

logger = logging.getLogger(__name__)


class SincronizadorItemsService:
    """
    Serviço para sincronizar items de Separacao com dados de FaturamentoProduto
    """

    def sincronizar_items_faturamento(
        self,
        separacao_lote_id: str,
        usuario: str = 'Sistema'
    ) -> Dict[str, Any]:
        """
        Sincroniza items de Separacao com FaturamentoProduto

        LÓGICA:
        1. Buscar Separacao com separacao_lote_id e sincronizado_nf=True
        2. Extrair numero_nf da primeira Separacao encontrada
        3. Para cada cod_produto da Separacao:
           a. Buscar em FaturamentoProduto por numero_nf + cod_produto
           b. Atualizar qtd_saldo, valor_saldo, peso, pallet

        Args:
            separacao_lote_id: ID do lote de separação
            usuario: Nome do usuário que solicitou

        Returns:
            Dict com resultado da operação
        """
        try:
            logger.info(f"🔄 Iniciando sincronização de items para lote {separacao_lote_id}")

            # 1. Buscar Separacoes do lote com sincronizado_nf=True
            separacoes = Separacao.query.filter_by(
                separacao_lote_id=separacao_lote_id,
                sincronizado_nf=True
            ).all()

            if not separacoes:
                logger.warning(f"  ⚠️ Nenhuma Separacao com sincronizado_nf=True para lote {separacao_lote_id}")
                return {
                    'success': False,
                    'erro': 'Nenhuma separação sincronizada encontrada neste lote'
                }

            # 2. Extrair numero_nf (deve ser igual para todos do lote)
            numero_nf = separacoes[0].numero_nf

            if not numero_nf:
                logger.warning(f"  ⚠️ Separação não possui numero_nf")
                return {
                    'success': False,
                    'erro': 'Separação não possui número de NF'
                }

            logger.info(f"  📋 NF encontrada: {numero_nf}")
            logger.info(f"  📦 Total de items a sincronizar: {len(separacoes)}")

            # 3. Para cada item da Separacao, buscar em FaturamentoProduto
            atualizados = 0
            erros = 0
            detalhes = []

            for separacao in separacoes:
                try:
                    resultado_item = self._sincronizar_item(
                        separacao=separacao,
                        numero_nf=numero_nf,
                        usuario=usuario
                    )

                    detalhes.append(resultado_item)

                    if resultado_item['status'] == 'atualizado':
                        atualizados += 1
                    else:
                        erros += 1

                except Exception as e:
                    logger.error(f"  ❌ Erro ao sincronizar item {separacao.cod_produto}: {e}")
                    detalhes.append({
                        'cod_produto': separacao.cod_produto,
                        'status': 'erro',
                        'erro': str(e)
                    })
                    erros += 1

            # Commit
            db.session.commit()

            logger.info(f"  ✅ Sincronização concluída: {atualizados} itens atualizados, {erros} erros")

            return {
                'success': True,
                'separacao_lote_id': separacao_lote_id,
                'numero_nf': numero_nf,
                'atualizados': atualizados,
                'erros': erros,
                'detalhes': detalhes
            }

        except Exception as e:
            logger.error(f"❌ Erro ao sincronizar items do lote {separacao_lote_id}: {e}")
            db.session.rollback()
            return {
                'success': False,
                'separacao_lote_id': separacao_lote_id,
                'erro': str(e)
            }

    def _sincronizar_item(
        self,
        separacao: Separacao,
        numero_nf: str,
        usuario: str
    ) -> Dict[str, Any]:
        """
        Sincroniza um item de Separacao com FaturamentoProduto

        Args:
            separacao: Objeto Separacao a atualizar
            numero_nf: Número da NF para buscar em FaturamentoProduto
            usuario: Usuário que solicitou

        Returns:
            Dict com resultado da sincronização do item
        """
        cod_produto = separacao.cod_produto

        # Buscar item em FaturamentoProduto
        faturamento_item = FaturamentoProduto.query.filter_by(
            numero_nf=numero_nf,
            cod_produto=cod_produto
        ).first()

        if not faturamento_item:
            logger.warning(f"    ⚠️ Produto {cod_produto} não encontrado em FaturamentoProduto para NF {numero_nf}")
            return {
                'cod_produto': cod_produto,
                'status': 'nao_encontrado',
                'motivo': 'Produto não encontrado no faturamento'
            }

        # Extrair dados de FaturamentoProduto
        qtd_faturada = float(faturamento_item.qtd_produto_faturado or 0)
        valor_faturado = float(faturamento_item.valor_produto_faturado or 0)
        peso_total = float(faturamento_item.peso_total or 0)

        # Calcular pallets usando CadastroPalletizacao
        cadastro = CadastroPalletizacao.query.filter_by(
            cod_produto=cod_produto,
            ativo=True
        ).first()

        pallets = 0
        if cadastro and cadastro.palletizacao > 0:
            pallets = round(qtd_faturada / float(cadastro.palletizacao), 2)

        # Atualizar Separacao
        separacao.qtd_saldo = qtd_faturada
        separacao.valor_saldo = valor_faturado
        separacao.peso = peso_total
        separacao.pallet = pallets

        logger.info(f"    ✅ {cod_produto}: qtd={qtd_faturada}, valor=R${valor_faturado:.2f}, peso={peso_total}kg, pallets={pallets}")

        return {
            'cod_produto': cod_produto,
            'status': 'atualizado',
            'dados_anteriores': {
                'qtd_saldo': float(separacao.qtd_saldo or 0),
                'valor_saldo': float(separacao.valor_saldo or 0),
                'peso': float(separacao.peso or 0),
                'pallet': float(separacao.pallet or 0)
            },
            'dados_novos': {
                'qtd_saldo': qtd_faturada,
                'valor_saldo': valor_faturado,
                'peso': peso_total,
                'pallet': pallets
            }
        }
