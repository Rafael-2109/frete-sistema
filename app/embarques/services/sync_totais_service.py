"""
🔄 SERVIÇO DE SINCRONIZAÇÃO DE TOTAIS DO EMBARQUE
================================================

OBJETIVO:
    Garantir que Embarque.peso_total, pallet_total e valor_total estejam
    sincronizados com os dados REAIS de NF (FaturamentoProduto) ou Separacao.

REGRA DE PRIORIDADE:
    1. SE EmbarqueItem tem NF validada (erro_validacao IS NULL):
       → Busca dados de FaturamentoProduto
    2. SENÃO:
       → Busca dados de Separacao

USO:
    from app.embarques.services.sync_totais_service import sincronizar_totais_embarque

    resultado = sincronizar_totais_embarque(embarque_id)
    # ou
    resultado = sincronizar_totais_embarque(embarque)

RETORNO:
    {
        'success': True,
        'embarque_id': 123,
        'itens_atualizados': 5,
        'totais': {
            'peso_total': 1500.0,
            'valor_total': 50000.0,
            'pallet_total': 12.5
        },
        'detalhes': [...]
    }
"""

from app import db
from app.embarques.models import Embarque, EmbarqueItem
from app.faturamento.models import FaturamentoProduto
from app.separacao.models import Separacao
from app.producao.models import CadastroPalletizacao
from sqlalchemy import func
import logging

logger = logging.getLogger(__name__)


def sincronizar_totais_embarque(embarque_ou_id):
    """
    Sincroniza totais do embarque com dados de NF ou Separacao.

    Args:
        embarque_ou_id: Objeto Embarque ou ID do embarque

    Returns:
        dict: Resultado da sincronização
    """
    try:
        # Resolve embarque
        if isinstance(embarque_ou_id, int):
            embarque = db.session.get(Embarque,embarque_ou_id) if embarque_ou_id else None
            if not embarque:
                return {'success': False, 'error': f'Embarque {embarque_ou_id} não encontrado'}
        else:
            embarque = embarque_ou_id

        logger.info(f"[SYNC] 🔄 Iniciando sincronização Embarque #{embarque.numero}")

        itens_atualizados = []
        itens_com_erro = []

        # Carrega itens uma unica vez (memoizado via Embarque.itens)
        todos_itens = embarque.itens
        itens_ativos = [i for i in todos_itens if i.status == 'ativo']

        # Processa cada EmbarqueItem ativo
        for item in itens_ativos:
            try:
                resultado_item = _sincronizar_item(item)
                itens_atualizados.append(resultado_item)

            except Exception as e:
                logger.error(f"[SYNC] ❌ Erro ao sincronizar item {item.id}: {str(e)}")
                itens_com_erro.append({
                    'item_id': item.id,
                    'pedido': item.pedido,
                    'erro': str(e)
                })

        # Recalcula totais do embarque em uma unica iteracao sobre itens_ativos
        peso = valor = pallet = 0.0
        for i in itens_ativos:
            peso += i.peso or 0
            valor += i.valor or 0
            pallet += i.pallets or 0
        embarque.peso_total = peso
        embarque.valor_total = valor
        embarque.pallet_total = pallet

        db.session.commit()

        resultado = {
            'success': True,
            'embarque_id': embarque.id,
            'embarque_numero': embarque.numero,
            'itens_atualizados': len(itens_atualizados),
            'itens_com_erro': len(itens_com_erro),
            'totais': {
                'peso_total': float(embarque.peso_total or 0),
                'valor_total': float(embarque.valor_total or 0),
                'pallet_total': float(embarque.pallet_total or 0)
            },
            'detalhes': itens_atualizados,
            'erros': itens_com_erro
        }

        logger.info(f"[SYNC] ✅ Embarque #{embarque.numero} sincronizado: "
                   f"Peso={embarque.peso_total:.2f}kg | "
                   f"Valor=R${embarque.valor_total:.2f} | "
                   f"Pallets={embarque.pallet_total:.2f}")

        return resultado

    except Exception as e:
        db.session.rollback()
        logger.error(f"[SYNC] ❌ Erro na sincronização: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


def _sincronizar_item(item: EmbarqueItem) -> dict:
    """
    Sincroniza um EmbarqueItem com dados de NF ou Separacao.

    REGRA:
        - SE erro_validacao IS NULL → NF validada → usa FaturamentoProduto
        - SENÃO → usa Separacao
    """
    peso_antigo = item.peso or 0
    valor_antigo = item.valor or 0
    pallets_antigo = item.pallets or 0

    # ========================================
    # CASO 1: NF VALIDADA (erro_validacao IS NULL)
    # ========================================
    if item.nota_fiscal and (item.erro_validacao is None or item.erro_validacao == ''):
        logger.info(f"[SYNC] 📋 Item {item.id} (NF {item.nota_fiscal}): Usando dados de FaturamentoProduto")

        # Busca produtos da NF
        produtos_nf = FaturamentoProduto.query.filter_by(
            numero_nf=item.nota_fiscal
        ).all()

        if not produtos_nf:
            raise ValueError(f"NF {item.nota_fiscal} não encontrada em FaturamentoProduto")

        # Soma totais da NF
        peso_nf = sum(float(p.peso_total or 0) for p in produtos_nf)
        valor_nf = sum(float(p.valor_produto_faturado or 0) for p in produtos_nf)

        # Calcula pallets usando CadastroPalletizacao
        pallets_nf = _calcular_pallets_from_produtos(produtos_nf)

        # Atualiza EmbarqueItem
        item.peso = peso_nf
        item.valor = valor_nf
        item.pallets = pallets_nf

        return {
            'item_id': item.id,
            'pedido': item.pedido,
            'nota_fiscal': item.nota_fiscal,
            'fonte': 'FaturamentoProduto',
            'alteracoes': {
                'peso': {'antes': peso_antigo, 'depois': peso_nf},
                'valor': {'antes': valor_antigo, 'depois': valor_nf},
                'pallets': {'antes': pallets_antigo, 'depois': pallets_nf}
            }
        }

    # ========================================
    # CASO 2: NF NÃO VALIDADA → USA SEPARACAO
    # ========================================
    else:
        logger.info(f"[SYNC] 📦 Item {item.id} (Lote {item.separacao_lote_id}): Usando dados de Separacao")

        if not item.separacao_lote_id:
            raise ValueError(f"Item {item.id} sem separacao_lote_id e sem NF validada")

        # Busca separações do lote
        separacoes = Separacao.query.filter_by(
            separacao_lote_id=item.separacao_lote_id,
            num_pedido=item.pedido
        ).all()

        if not separacoes:
            raise ValueError(f"Separacao não encontrada para lote {item.separacao_lote_id}")

        # Soma totais das separações
        peso_sep = sum(float(s.peso or 0) for s in separacoes)
        valor_sep = sum(float(s.valor_saldo or 0) for s in separacoes)
        pallets_sep = sum(float(s.pallet or 0) for s in separacoes)

        # Atualiza EmbarqueItem
        item.peso = peso_sep
        item.valor = valor_sep
        item.pallets = pallets_sep

        return {
            'item_id': item.id,
            'pedido': item.pedido,
            'separacao_lote_id': item.separacao_lote_id,
            'fonte': 'Separacao',
            'alteracoes': {
                'peso': {'antes': peso_antigo, 'depois': peso_sep},
                'valor': {'antes': valor_antigo, 'depois': valor_sep},
                'pallets': {'antes': pallets_antigo, 'depois': pallets_sep}
            }
        }


def _calcular_pallets_from_produtos(produtos_nf: list) -> float:
    """
    Calcula pallets total a partir de lista de FaturamentoProduto.

    Usa CadastroPalletizacao para obter fator de conversão correto.
    """
    pallets_total = 0.0

    for produto in produtos_nf:
        # Busca cadastro de palletização
        cadastro = CadastroPalletizacao.query.filter_by(
            cod_produto=produto.cod_produto
        ).first()

        if cadastro and cadastro.palletizacao and cadastro.palletizacao > 0:
            # Usa fator de palletização cadastrado
            qtd = float(produto.qtd_produto_faturado or 0)
            pallets_produto = qtd / cadastro.palletizacao
            pallets_total += pallets_produto

            logger.debug(f"[SYNC]   Produto {produto.cod_produto}: "
                        f"{qtd} un / {cadastro.palletizacao} = {pallets_produto:.2f} pallets")
        else:
            # Fallback: peso / 1000 (aproximação grosseira)
            peso = float(produto.peso_total or 0)
            pallets_aprox = peso / 1000
            pallets_total += pallets_aprox

            logger.warning(f"[SYNC]   ⚠️ Produto {produto.cod_produto} sem cadastro de palletização. "
                          f"Usando aproximação: {peso}kg / 1000 = {pallets_aprox:.2f} pallets")

    return round(pallets_total, 2)
