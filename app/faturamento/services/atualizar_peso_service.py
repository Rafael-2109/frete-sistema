"""
Serviço para atualizar peso em cascata usando CadastroPalletizacao

Fluxo de atualização:
1. FaturamentoProduto (peso_unitario_produto, peso_total)
2. RelatorioFaturamentoImportado (peso_bruto)
3. EmbarqueItem (peso, pallet) - CALCULADO de FaturamentoProduto
4. Embarque (peso_total, pallet_total)
5. Frete (peso_total)
"""

import logging
from typing import Dict, Any
from sqlalchemy import func
from app import db
from app.faturamento.models import FaturamentoProduto, RelatorioFaturamentoImportado
from app.producao.models import CadastroPalletizacao
from app.embarques.models import EmbarqueItem, Embarque
from app.fretes.models import Frete

logger = logging.getLogger(__name__)


class AtualizadorPesoService:
    """
    Serviço para atualizar peso em cascata usando dados de CadastroPalletizacao
    """

    def atualizar_peso_nf(self, numero_nf: str, usuario: str = 'Sistema') -> Dict[str, Any]:
        """
        Atualiza peso de uma NF em cascata em todas as tabelas relacionadas

        Args:
            numero_nf: Número da NF a atualizar
            usuario: Nome do usuário que solicitou a atualização

        Returns:
            Dict com resultado da operação
        """
        try:
            logger.info(f"🔄 Iniciando atualização de peso para NF {numero_nf}")

            # 1. Atualizar FaturamentoProduto
            resultado_faturamento = self._atualizar_faturamento_produto(numero_nf, usuario)

            # 2. Atualizar RelatorioFaturamentoImportado
            resultado_relatorio = self._atualizar_relatorio_faturamento(numero_nf)

            # 3. Atualizar EmbarqueItem (usa dados de FaturamentoProduto)
            resultado_embarque_item = self._atualizar_embarque_item(numero_nf)

            # 4. Atualizar Embarque (totais)
            resultado_embarque = self._atualizar_embarque_totais(numero_nf)

            # 5. Atualizar Frete
            resultado_frete = self._atualizar_frete(numero_nf)

            # Commit final
            db.session.commit()

            return {
                'success': True,
                'numero_nf': numero_nf,
                'faturamento_produto': resultado_faturamento,
                'relatorio': resultado_relatorio,
                'embarque_item': resultado_embarque_item,
                'embarque': resultado_embarque,
                'frete': resultado_frete
            }

        except Exception as e:
            logger.error(f"❌ Erro ao atualizar peso da NF {numero_nf}: {e}")
            db.session.rollback()
            return {
                'success': False,
                'numero_nf': numero_nf,
                'erro': str(e)
            }

    def _atualizar_faturamento_produto(self, numero_nf: str, usuario: str) -> Dict[str, Any]:
        """
        Atualiza peso_unitario_produto e peso_total em FaturamentoProduto
        usando dados de CadastroPalletizacao
        """
        logger.info(f"  📦 Atualizando FaturamentoProduto...")

        itens = FaturamentoProduto.query.filter_by(numero_nf=numero_nf).all()

        if not itens:
            logger.warning(f"  ⚠️ Nenhum item encontrado em FaturamentoProduto para NF {numero_nf}")
            return {'atualizados': 0, 'erros': 0, 'detalhes': []}

        atualizados = 0
        erros = 0
        detalhes = []

        for item in itens:
            try:
                # Buscar peso em CadastroPalletizacao
                cadastro = CadastroPalletizacao.query.filter_by(
                    cod_produto=item.cod_produto,
                    ativo=True
                ).first()

                if not cadastro:
                    logger.warning(f"  ⚠️ Produto {item.cod_produto} não encontrado em CadastroPalletizacao")
                    detalhes.append({
                        'cod_produto': item.cod_produto,
                        'status': 'sem_cadastro'
                    })
                    erros += 1
                    continue

                # Calcular pesos
                peso_unitario = float(cadastro.peso_bruto)
                quantidade = float(item.qtd_produto_faturado or 0)
                peso_total = quantidade * peso_unitario

                # Atualizar item
                item.peso_unitario_produto = peso_unitario
                item.peso_total = peso_total
                item.updated_by = usuario

                detalhes.append({
                    'cod_produto': item.cod_produto,
                    'quantidade': quantidade,
                    'peso_unitario': peso_unitario,
                    'peso_total': peso_total,
                    'status': 'atualizado'
                })

                atualizados += 1

            except Exception as e:
                logger.error(f"  ❌ Erro ao atualizar item {item.cod_produto}: {e}")
                detalhes.append({
                    'cod_produto': item.cod_produto,
                    'status': 'erro',
                    'erro': str(e)
                })
                erros += 1

        db.session.flush()
        logger.info(f"  ✅ FaturamentoProduto: {atualizados} itens atualizados, {erros} erros")

        return {
            'atualizados': atualizados,
            'erros': erros,
            'detalhes': detalhes
        }

    def _atualizar_relatorio_faturamento(self, numero_nf: str) -> Dict[str, Any]:
        """
        Atualiza peso_bruto em RelatorioFaturamentoImportado
        somando peso_total de FaturamentoProduto
        """
        logger.info(f"  📊 Atualizando RelatorioFaturamentoImportado...")

        relatorio = RelatorioFaturamentoImportado.query.filter_by(numero_nf=numero_nf).first()

        if not relatorio:
            logger.warning(f"  ⚠️ RelatorioFaturamentoImportado não encontrado para NF {numero_nf}")
            return {'atualizado': False, 'motivo': 'não_encontrado'}

        # Garantir que mudanças em FaturamentoProduto sejam visíveis
        db.session.flush()

        # Somar peso_total de FaturamentoProduto
        peso_total = db.session.query(
            func.sum(FaturamentoProduto.peso_total)
        ).filter_by(numero_nf=numero_nf).scalar() or 0

        # Log detalhado para debug
        itens_fat = FaturamentoProduto.query.filter_by(numero_nf=numero_nf).all()
        logger.info(f"     DEBUG: Encontrados {len(itens_fat)} itens em FaturamentoProduto")
        for item in itens_fat:
            logger.info(f"     - {item.cod_produto}: peso_total={item.peso_total}")

        relatorio.peso_bruto = float(peso_total)

        db.session.flush()
        logger.info(f"  ✅ RelatorioFaturamentoImportado: peso_bruto = {peso_total}kg")

        return {
            'atualizado': True,
            'peso_bruto': float(peso_total)
        }

    def _atualizar_embarque_item(self, numero_nf: str) -> Dict[str, Any]:
        """
        Atualiza peso e pallet em EmbarqueItem

        LÓGICA CORRETA:
        1. Buscar TODOS os FaturamentoProduto da NF
        2. Para CADA produto, buscar CadastroPalletizacao e calcular pallets
        3. SOMAR peso e pallets de todos os produtos
        4. Gravar totais em EmbarqueItem
        """
        logger.info(f"  🚚 Atualizando EmbarqueItem...")

        embarque_items = EmbarqueItem.query.filter_by(nota_fiscal=numero_nf).all()

        if not embarque_items:
            logger.warning(f"  ⚠️ Nenhum EmbarqueItem encontrado para NF {numero_nf}")
            return {'atualizados': 0, 'motivo': 'não_encontrado'}

        # Buscar TODOS os produtos da NF em FaturamentoProduto
        produtos_nf = FaturamentoProduto.query.filter_by(numero_nf=numero_nf).all()

        if not produtos_nf:
            logger.warning(f"  ⚠️ Nenhum produto encontrado em FaturamentoProduto para NF {numero_nf}")
            return {'atualizados': 0, 'motivo': 'sem_produtos'}

        # Calcular peso e pallets totais da NF
        peso_total_nf = 0
        pallets_total_nf = 0
        detalhes_calculo = []

        for produto in produtos_nf:
            try:
                # Peso já está calculado em FaturamentoProduto
                peso_produto = float(produto.peso_total or 0)
                peso_total_nf += peso_produto

                # Buscar palletização para calcular pallets
                cadastro = CadastroPalletizacao.query.filter_by(
                    cod_produto=produto.cod_produto,
                    ativo=True
                ).first()

                if cadastro and cadastro.palletizacao > 0:
                    quantidade = float(produto.qtd_produto_faturado or 0)
                    pallets_produto = quantidade / float(cadastro.palletizacao)
                    pallets_total_nf += pallets_produto

                    detalhes_calculo.append({
                        'cod_produto': produto.cod_produto,
                        'quantidade': quantidade,
                        'palletizacao': float(cadastro.palletizacao),
                        'pallets': round(pallets_produto, 2),
                        'peso': peso_produto
                    })
                else:
                    logger.warning(f"    ⚠️ Produto {produto.cod_produto} sem palletização cadastrada")
                    detalhes_calculo.append({
                        'cod_produto': produto.cod_produto,
                        'status': 'sem_palletizacao'
                    })

            except Exception as e:
                logger.error(f"    ❌ Erro ao calcular produto {produto.cod_produto}: {e}")

        # Atualizar TODOS os EmbarqueItems com esta NF
        atualizados = 0
        for embarque_item in embarque_items:
            try:
                embarque_item.peso = round(peso_total_nf, 2)
                embarque_item.pallets = round(pallets_total_nf, 2)
                atualizados += 1

            except Exception as e:
                logger.error(f"  ❌ Erro ao atualizar EmbarqueItem {embarque_item.id}: {e}")

        db.session.flush()

        logger.info(f"  ✅ EmbarqueItem: {atualizados} itens atualizados")
        logger.info(f"     Peso total: {round(peso_total_nf, 2)}kg")
        logger.info(f"     Pallets total: {round(pallets_total_nf, 2)}")
        logger.info(f"     Produtos processados: {len(detalhes_calculo)}")

        return {
            'atualizados': atualizados,
            'peso_total': round(peso_total_nf, 2),
            'pallets_total': round(pallets_total_nf, 2),
            'produtos_processados': len(detalhes_calculo),
            'detalhes': detalhes_calculo
        }

    def _atualizar_embarque_totais(self, numero_nf: str) -> Dict[str, Any]:
        """
        Atualiza peso_total e pallet_total em Embarque recalculando de EmbarqueItem
        """
        logger.info(f"  📦 Atualizando totais do Embarque...")

        # Buscar embarques que contém esta NF
        embarque_items = EmbarqueItem.query.filter_by(nota_fiscal=numero_nf).all()

        if not embarque_items:
            return {'atualizados': 0, 'motivo': 'sem_embarque_items'}

        embarques_atualizados = set()

        for embarque_item in embarque_items:
            embarque = embarque_item.embarque

            if not embarque:
                continue

            # Recalcular totais do embarque baseado em TODOS os itens ativos
            totais = db.session.query(
                func.sum(EmbarqueItem.peso).label('peso_total'),
                func.sum(EmbarqueItem.pallets).label('pallet_total')
            ).filter(
                EmbarqueItem.embarque_id == embarque.id,
                EmbarqueItem.status == 'ativo'
            ).first()

            embarque.peso_total = float(totais.peso_total or 0)
            embarque.pallet_total = float(totais.pallet_total or 0)

            embarques_atualizados.add(embarque.id)

        db.session.flush()
        logger.info(f"  ✅ Embarque: {len(embarques_atualizados)} embarques atualizados")

        return {
            'atualizados': len(embarques_atualizados),
            'embarques_ids': list(embarques_atualizados)
        }

    def _atualizar_frete(self, numero_nf: str) -> Dict[str, Any]:
        """
        Atualiza peso_total e RECALCULA valor_cotado do Frete

        LÓGICA:
        1. Buscar todas as NFs do CNPJ do frete
        2. Somar peso de todas as NFs do CNPJ
        3. Atualizar peso_total
        4. Recalcular valor_cotado usando CalculadoraFrete
        """
        logger.info(f"  💰 Atualizando Frete...")

        # Buscar fretes vinculados aos embarques desta NF
        embarque_items = EmbarqueItem.query.filter_by(nota_fiscal=numero_nf).all()

        if not embarque_items:
            return {'atualizados': 0, 'motivo': 'sem_embarque_items'}

        embarque_ids = [item.embarque_id for item in embarque_items if item.embarque_id]

        if not embarque_ids:
            return {'atualizados': 0, 'motivo': 'sem_embarque_id'}

        # Buscar fretes vinculados
        fretes = Frete.query.filter(Frete.embarque_id.in_(embarque_ids)).all()

        if not fretes:
            logger.warning(f"  ⚠️ Nenhum Frete encontrado para embarques: {embarque_ids}")
            return {'atualizados': 0, 'motivo': 'sem_frete'}

        atualizados = 0
        recalculados = 0

        for frete in fretes:
            try:
                # Buscar todas as NFs do CNPJ deste frete no embarque
                nfs_cnpj = EmbarqueItem.query.filter(
                    EmbarqueItem.embarque_id == frete.embarque_id,
                    EmbarqueItem.cnpj_cliente == frete.cnpj_cliente,
                    EmbarqueItem.status == 'ativo'
                ).all()

                if not nfs_cnpj:
                    continue

                # Somar peso e valor de todas as NFs do CNPJ
                peso_total_cnpj = sum(float(item.peso or 0) for item in nfs_cnpj)
                valor_total_cnpj = sum(float(item.valor or 0) for item in nfs_cnpj)

                # Atualizar peso_total
                frete.peso_total = peso_total_cnpj
                frete.valor_total_nfs = valor_total_cnpj

                # Recalcular valor_cotado usando CalculadoraFrete
                try:
                    from app.utils.calculadora_frete import CalculadoraFrete
                    from app.transportadoras.models import Transportadora

                    # Buscar transportadora para pegar configurações
                    transportadora = Transportadora.query.get(frete.transportadora_id)

                    if not transportadora:
                        logger.warning(f"    ⚠️ Transportadora {frete.transportadora_id} não encontrada")
                        atualizados += 1
                        continue

                    # Preparar dados da tabela
                    tabela_dados = {
                        'valor_kg': frete.tabela_valor_kg,
                        'percentual_valor': frete.tabela_percentual_valor,
                        'frete_minimo_valor': frete.tabela_frete_minimo_valor,
                        'frete_minimo_peso': frete.tabela_frete_minimo_peso,
                        'icms': frete.tabela_icms,
                        'percentual_gris': frete.tabela_percentual_gris,
                        'pedagio_por_100kg': frete.tabela_pedagio_por_100kg,
                        'valor_tas': frete.tabela_valor_tas,
                        'percentual_adv': frete.tabela_percentual_adv,
                        'percentual_rca': frete.tabela_percentual_rca,
                        'valor_despacho': frete.tabela_valor_despacho,
                        'valor_cte': frete.tabela_valor_cte,
                        'icms_incluso': frete.tabela_icms_incluso,
                        'gris_minimo': frete.tabela_gris_minimo,
                        'adv_minimo': frete.tabela_adv_minimo,
                        'icms_proprio': frete.tabela_icms_proprio
                    }

                    # Preparar config da transportadora
                    transportadora_config = {
                        'aplica_gris_pos_minimo': transportadora.aplica_gris_pos_minimo,
                        'aplica_adv_pos_minimo': transportadora.aplica_adv_pos_minimo,
                        'aplica_rca_pos_minimo': transportadora.aplica_rca_pos_minimo,
                        'aplica_pedagio_pos_minimo': transportadora.aplica_pedagio_pos_minimo,
                        'aplica_despacho_pos_minimo': transportadora.aplica_despacho_pos_minimo,
                        'aplica_cte_pos_minimo': transportadora.aplica_cte_pos_minimo,
                        'aplica_tas_pos_minimo': transportadora.aplica_tas_pos_minimo,
                        'pedagio_por_fracao': transportadora.pedagio_por_fracao
                    }

                    # Recalcular frete
                    resultado_calculo = CalculadoraFrete.calcular_frete_unificado(
                        peso=peso_total_cnpj,
                        valor_mercadoria=valor_total_cnpj,
                        tabela_dados=tabela_dados,
                        codigo_ibge=None,  # Poderia buscar da cidade se necessário
                        transportadora_optante=transportadora.optante_simples,
                        transportadora_config=transportadora_config
                    )

                    # Atualizar valor_cotado com novo cálculo
                    novo_valor_cotado = resultado_calculo.get('valor_liquido', frete.valor_cotado)
                    valor_antigo = frete.valor_cotado

                    frete.valor_cotado = novo_valor_cotado

                    logger.info(f"    ✅ Frete {frete.id} recalculado:")
                    logger.info(f"       Peso: {peso_total_cnpj}kg")
                    logger.info(f"       Valor antigo: R$ {valor_antigo:.2f}")
                    logger.info(f"       Valor novo: R$ {novo_valor_cotado:.2f}")

                    recalculados += 1

                except Exception as calc_error:
                    logger.error(f"    ❌ Erro ao recalcular frete {frete.id}: {calc_error}")
                    # Continua mesmo se falhar o recálculo, pelo menos atualiza o peso
                    pass

                atualizados += 1

            except Exception as e:
                logger.error(f"  ❌ Erro ao atualizar frete {frete.id}: {e}")

        db.session.flush()
        logger.info(f"  ✅ Frete: {atualizados} fretes atualizados, {recalculados} recalculados")

        return {
            'atualizados': atualizados,
            'recalculados': recalculados
        }
