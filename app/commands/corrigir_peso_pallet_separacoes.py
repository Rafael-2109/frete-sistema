#!/usr/bin/env python3
"""
Comando para corrigir peso e pallet das Separações
===================================================

Este comando identifica e corrige Separações que estão sem peso ou pallet,
recalculando baseado no CadastroPalletizacao.

Uso:
    python app/commands/corrigir_peso_pallet_separacoes.py

Autor: Sistema de Fretes
Data: 2025-01-23
"""

import logging
import sys
import os
from datetime import datetime

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from app.separacao.models import Separacao
from app.producao.models import CadastroPalletizacao
from sqlalchemy import or_, and_

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def identificar_separacoes_sem_peso_pallet():
    """
    Identifica Separações que estão sem peso ou pallet
    """
    try:
        # Buscar separações com problemas de peso ou pallet
        separacoes_problematicas = Separacao.query.filter(
            and_(
                Separacao.sincronizado_nf == False,  # Apenas não sincronizadas
                or_(
                    Separacao.peso == None,
                    Separacao.peso == 0,
                    Separacao.pallet == None
                )
            )
        ).all()

        logger.info(f"🔍 Encontradas {len(separacoes_problematicas)} separações com peso ou pallet faltantes")

        # Estatísticas detalhadas
        sem_peso = [s for s in separacoes_problematicas if s.peso is None or s.peso == 0]
        sem_pallet = [s for s in separacoes_problematicas if s.pallet is None]
        sem_ambos = [s for s in separacoes_problematicas if (s.peso is None or s.peso == 0) and s.pallet is None]

        logger.info(f"   - Sem peso: {len(sem_peso)}")
        logger.info(f"   - Sem pallet: {len(sem_pallet)}")
        logger.info(f"   - Sem ambos: {len(sem_ambos)}")

        return separacoes_problematicas

    except Exception as e:
        logger.error(f"❌ Erro ao identificar separações: {e}")
        return []


def corrigir_peso_pallet(separacoes):
    """
    Corrige peso e pallet das separações baseado no CadastroPalletizacao
    """
    contador_peso_corrigido = 0
    contador_pallet_corrigido = 0
    produtos_sem_cadastro = set()

    if not separacoes:
        logger.info("✅ Nenhuma separação para corrigir")
        return 0, 0

    # Buscar todos os produtos únicos
    produtos_unicos = {s.cod_produto for s in separacoes if s.cod_produto}

    # Buscar palletizações em lote
    logger.info(f"📦 Buscando dados de palletização para {len(produtos_unicos)} produtos...")
    palletizacoes = {p.cod_produto: p for p in CadastroPalletizacao.query.filter(
        CadastroPalletizacao.cod_produto.in_(list(produtos_unicos))
    ).all()}
    logger.info(f"   ✅ Encontrados dados para {len(palletizacoes)} produtos")

    logger.info(f"🔧 Processando {len(separacoes)} separações...")

    for sep in separacoes:
        try:
            if not sep.cod_produto:
                logger.warning(f"   ⚠️ Separação {sep.id} sem código de produto")
                continue

            palletizacao = palletizacoes.get(sep.cod_produto)
            qtd = float(sep.qtd_saldo or 0)

            if qtd == 0:
                logger.debug(f"   ⚠️ Separação {sep.id} com quantidade zero")
                continue

            peso_anterior = sep.peso
            pallet_anterior = sep.pallet

            if palletizacao:
                # Calcular e corrigir peso
                if sep.peso is None or sep.peso == 0:
                    sep.peso = qtd * float(palletizacao.peso_bruto or 1.0)
                    contador_peso_corrigido += 1
                    logger.debug(f"   ✅ Peso corrigido: {sep.cod_produto} = {qtd:.2f} * {palletizacao.peso_bruto:.2f} = {sep.peso:.2f}")

                # Calcular e corrigir pallet
                if sep.pallet is None:
                    if palletizacao.palletizacao and palletizacao.palletizacao > 0:
                        sep.pallet = qtd / float(palletizacao.palletizacao)
                    else:
                        sep.pallet = 0
                    contador_pallet_corrigido += 1
                    logger.debug(f"   ✅ Pallet corrigido: {sep.cod_produto} = {qtd:.2f} / {palletizacao.palletizacao or 0:.2f} = {sep.pallet:.2f}")

            else:
                # Produto sem cadastro de palletização
                produtos_sem_cadastro.add(sep.cod_produto)

                # Aplicar valores padrão mínimos
                if sep.peso is None or sep.peso == 0:
                    sep.peso = qtd  # Assumir peso 1:1 com quantidade
                    contador_peso_corrigido += 1
                    logger.debug(f"   ⚠️ Peso padrão aplicado: {sep.cod_produto} = {sep.peso:.2f} (1:1 com qtd)")

                if sep.pallet is None:
                    sep.pallet = 0  # Sem dados para calcular
                    contador_pallet_corrigido += 1
                    logger.debug(f"   ⚠️ Pallet zerado: {sep.cod_produto} (sem cadastro)")

            # Log de progresso a cada 100 registros
            total_corrigido = contador_peso_corrigido + contador_pallet_corrigido
            if total_corrigido > 0 and total_corrigido % 100 == 0:
                logger.info(f"   ... {total_corrigido} correções realizadas...")

        except Exception as e:
            logger.error(f"   ❌ Erro ao corrigir separação {sep.id}: {e}")
            continue

    if produtos_sem_cadastro:
        logger.warning(f"\n⚠️ {len(produtos_sem_cadastro)} produtos sem cadastro de palletização:")
        for i, prod in enumerate(sorted(produtos_sem_cadastro)[:10], 1):  # Mostrar até 10
            logger.warning(f"   {i}. {prod}")
        if len(produtos_sem_cadastro) > 10:
            logger.warning(f"   ... e mais {len(produtos_sem_cadastro) - 10} produtos")

    return contador_peso_corrigido, contador_pallet_corrigido


def main():
    """
    Função principal
    """
    app = create_app()

    with app.app_context():
        try:
            logger.info("=" * 80)
            logger.info("🔧 CORREÇÃO DE PESO E PALLET DAS SEPARAÇÕES")
            logger.info("=" * 80)
            logger.info(f"Início: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            # 1. Identificar separações problemáticas
            logger.info("\n📊 Fase 1: Identificando separações com problemas...")
            separacoes = identificar_separacoes_sem_peso_pallet()

            if not separacoes:
                logger.info("✅ Todas as separações já possuem peso e pallet!")
                return

            # 2. Corrigir peso e pallet
            logger.info("\n📊 Fase 2: Corrigindo peso e pallet...")
            peso_corrigidos, pallet_corrigidos = corrigir_peso_pallet(separacoes)

            # 3. Commit das mudanças
            logger.info("\n💾 Salvando alterações no banco de dados...")
            db.session.commit()

            # 4. Estatísticas finais
            logger.info("\n" + "=" * 80)
            logger.info("✅ CORREÇÃO CONCLUÍDA COM SUCESSO!")
            logger.info(f"   📊 Estatísticas:")
            logger.info(f"   - Separações analisadas: {len(separacoes):,}")
            logger.info(f"   - Pesos corrigidos: {peso_corrigidos:,}")
            logger.info(f"   - Pallets corrigidos: {pallet_corrigidos:,}")
            logger.info(f"   - Total de correções: {peso_corrigidos + pallet_corrigidos:,}")
            logger.info(f"\nTérmino: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("=" * 80)

            # 5. Verificação final
            logger.info("\n🔍 Verificação final...")
            separacoes_restantes = identificar_separacoes_sem_peso_pallet()
            if separacoes_restantes:
                logger.warning(f"⚠️ Ainda restam {len(separacoes_restantes)} separações com problemas")
                logger.warning("   Estas podem estar com quantidade zero ou precisar de correção manual")
            else:
                logger.info("✅ Todas as separações estão com peso e pallet corretos!")

        except Exception as e:
            logger.error(f"❌ ERRO FATAL: {e}")
            db.session.rollback()
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    main()