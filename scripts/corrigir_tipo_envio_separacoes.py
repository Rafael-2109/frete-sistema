"""
Script para corrigir tipo_envio em Separações existentes
=========================================================

Problema: Algumas Separações foram criadas com tipo_envio='total' quando
deveriam ser 'parcial', pois não contêm TODOS os produtos do pedido.

Este script:
1. Busca Separações com tipo_envio='total'
2. Verifica se realmente contêm TODOS os produtos do pedido
3. Corrige para 'parcial' se necessário

Autor: Sistema
Data: 2025-01-11
"""

import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.separacao.models import Separacao
from app.carteira.models import CarteiraPrincipal
from sqlalchemy import func, distinct
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def corrigir_tipo_envio_separacoes(dry_run=True):
    """
    Corrige tipo_envio de Separações que estão incorretas

    Args:
        dry_run: Se True, apenas simula sem alterar dados
    """
    app = create_app()

    with app.app_context():
        logger.info("=" * 80)
        logger.info("SCRIPT DE CORREÇÃO DE tipo_envio EM SEPARAÇÕES")
        logger.info("=" * 80)

        if dry_run:
            logger.info("🔍 MODO DRY-RUN: Nenhuma alteração será feita")
        else:
            logger.warning("⚠️ MODO REAL: Alterações serão commitadas!")

        logger.info("")

        # Buscar todos os lotes com tipo_envio='total' e sincronizado_nf=False
        lotes_total = db.session.query(
            Separacao.separacao_lote_id,
            Separacao.num_pedido
        ).filter(
            Separacao.tipo_envio == 'total',
            Separacao.sincronizado_nf == False
        ).distinct().all()

        logger.info(f"📊 Encontrados {len(lotes_total)} lotes com tipo_envio='total'")
        logger.info("")

        lotes_corrigidos = 0
        lotes_corretos = 0

        for lote_id, num_pedido in lotes_total:
            # Buscar produtos na Separação
            produtos_separacao = db.session.query(
                Separacao.cod_produto,
                func.sum(Separacao.qtd_saldo).label('qtd_separada')
            ).filter(
                Separacao.separacao_lote_id == lote_id,
                Separacao.num_pedido == num_pedido,
                Separacao.sincronizado_nf == False
            ).group_by(Separacao.cod_produto).all()

            # Buscar produtos na CarteiraPrincipal
            produtos_pedido = db.session.query(
                CarteiraPrincipal.cod_produto,
                func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido).label('qtd_pedido')
            ).filter(
                CarteiraPrincipal.num_pedido == num_pedido,
                CarteiraPrincipal.ativo == True
            ).group_by(CarteiraPrincipal.cod_produto).all()

            # Criar dicionários para comparação
            sep_dict = {p.cod_produto: float(p.qtd_separada or 0) for p in produtos_separacao}
            ped_dict = {p.cod_produto: float(p.qtd_pedido or 0) for p in produtos_pedido}

            # Verificar se é realmente total
            e_total = True
            motivos = []

            # 1. Verificar se tem todos os produtos
            produtos_faltando = set(ped_dict.keys()) - set(sep_dict.keys())
            if produtos_faltando:
                e_total = False
                motivos.append(f"{len(produtos_faltando)} produtos faltando: {', '.join(list(produtos_faltando)[:3])}")

            # 2. Verificar se as quantidades estão completas
            for cod_produto in sep_dict.keys():
                qtd_sep = sep_dict.get(cod_produto, 0)
                qtd_ped = ped_dict.get(cod_produto, 0)

                if abs(qtd_sep - qtd_ped) > 0.01:  # Tolerância para float
                    e_total = False
                    motivos.append(f"{cod_produto}: sep={qtd_sep:.2f}, pedido={qtd_ped:.2f}")

            if e_total:
                lotes_corretos += 1
                logger.info(f"✅ Lote {lote_id} (pedido {num_pedido}): tipo_envio='total' CORRETO")
            else:
                lotes_corrigidos += 1
                logger.warning(f"🔧 Lote {lote_id} (pedido {num_pedido}): tipo_envio='total' INCORRETO")
                logger.warning(f"   Motivos: {'; '.join(motivos[:3])}")
                logger.warning(f"   Produtos na separação: {len(sep_dict)}, no pedido: {len(ped_dict)}")

                if not dry_run:
                    # Atualizar tipo_envio para 'parcial'
                    db.session.query(Separacao).filter(
                        Separacao.separacao_lote_id == lote_id,
                        Separacao.num_pedido == num_pedido
                    ).update({'tipo_envio': 'parcial'}, synchronize_session=False)
                    logger.info(f"   ✅ Corrigido para tipo_envio='parcial'")

        logger.info("")
        logger.info("=" * 80)
        logger.info("RESUMO DA CORREÇÃO")
        logger.info("=" * 80)
        logger.info(f"Total de lotes analisados: {len(lotes_total)}")
        logger.info(f"✅ Lotes corretos: {lotes_corretos}")
        logger.info(f"🔧 Lotes corrigidos: {lotes_corrigidos}")

        if not dry_run and lotes_corrigidos > 0:
            db.session.commit()
            logger.info("")
            logger.info("✅ ALTERAÇÕES COMMITADAS NO BANCO DE DADOS")
        elif dry_run and lotes_corrigidos > 0:
            logger.info("")
            logger.info("ℹ️ Execute com dry_run=False para aplicar as correções")

        logger.info("=" * 80)

        return {
            'total': len(lotes_total),
            'corretos': lotes_corretos,
            'corrigidos': lotes_corrigidos
        }


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Corrige tipo_envio em Separações')
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Executa as correções (sem este flag, apenas simula)'
    )

    args = parser.parse_args()

    resultado = corrigir_tipo_envio_separacoes(dry_run=not args.execute)

    print("\n")
    if not args.execute and resultado['corrigidos'] > 0:
        print("⚠️ Para aplicar as correções, execute:")
        print(f"   python {__file__} --execute")
