"""
Script para Limpeza de SaldoStandby
===================================

OBJETIVO:
---------
Excluir registros de SaldoStandby que:
1. Têm qtd_saldo = 0 ou NULL (zerados)
2. Não existem mais na CarteiraPrincipal (órfãos - pedido/produto não existe)
3. Existem na CarteiraPrincipal mas com qtd_saldo_produto_pedido = 0 (zerados na carteira)

LÓGICA:
-------
- SaldoStandby contém itens enviados DA carteira
- CarteiraPrincipal quando zera um item, deixa qtd_saldo_produto_pedido = 0
- Precisamos EXCLUIR de SaldoStandby o que foi zerado ou não existe mais

Data de Criação: 2025-01-29
Autor: Sistema de Fretes
"""

import sys
import os
from datetime import datetime

# Adicionar caminho do projeto ao sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.carteira.models import CarteiraPrincipal, SaldoStandby
from sqlalchemy import and_, or_
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def limpar_saldo_standby():
    """
    Executa limpeza completa de SaldoStandby
    """
    app = create_app()

    with app.app_context():
        try:
            logger.info("=" * 80)
            logger.info("🧹 INICIANDO LIMPEZA DE SALDO STANDBY")
            logger.info("=" * 80)

            # ====================================================================
            # ETAPA 1: EXCLUIR REGISTROS COM QTD_SALDO = 0 OU NULL
            # ====================================================================
            logger.info("\n📊 ETAPA 1: Excluindo registros com qtd_saldo = 0 ou NULL...")

            itens_zerados = SaldoStandby.query.filter(
                or_(
                    SaldoStandby.qtd_saldo == 0,
                    SaldoStandby.qtd_saldo.is_(None)
                )
            ).all()

            if itens_zerados:
                logger.info(f"   ❌ Encontrados {len(itens_zerados)} registros zerados para excluir")

                for item in itens_zerados:
                    logger.info(f"      → Excluindo: Pedido {item.num_pedido} | Produto {item.cod_produto} | Qtd: {item.qtd_saldo}")
                    db.session.delete(item)

                db.session.commit()
                logger.info(f"   ✅ {len(itens_zerados)} registros zerados EXCLUÍDOS com sucesso")
            else:
                logger.info("   ✅ Nenhum registro zerado encontrado")


            # ====================================================================
            # ETAPA 2: EXCLUIR ÓRFÃOS (não existem na CarteiraPrincipal)
            # ====================================================================
            logger.info("\n📊 ETAPA 2: Excluindo órfãos (não existem na carteira)...")

            todos_standby = SaldoStandby.query.all()
            orfaos_excluidos = 0

            for standby in todos_standby:
                # Verificar se existe na CarteiraPrincipal
                existe_na_carteira = CarteiraPrincipal.query.filter_by(
                    num_pedido=standby.num_pedido,
                    cod_produto=standby.cod_produto
                ).first()

                if not existe_na_carteira:
                    logger.info(f"      → ÓRFÃO: Pedido {standby.num_pedido} | Produto {standby.cod_produto} não existe na carteira")
                    db.session.delete(standby)
                    orfaos_excluidos += 1

            if orfaos_excluidos > 0:
                db.session.commit()
                logger.info(f"   ✅ {orfaos_excluidos} órfãos EXCLUÍDOS com sucesso")
            else:
                logger.info("   ✅ Nenhum órfão encontrado")


            # ====================================================================
            # ETAPA 3: EXCLUIR ZERADOS NA CARTEIRA (qtd_saldo_produto_pedido = 0)
            # ====================================================================
            logger.info("\n📊 ETAPA 3: Excluindo itens zerados na carteira...")

            todos_standby_atualizados = SaldoStandby.query.all()
            zerados_na_carteira = 0

            for standby in todos_standby_atualizados:
                # Buscar na CarteiraPrincipal
                item_carteira = CarteiraPrincipal.query.filter_by(
                    num_pedido=standby.num_pedido,
                    cod_produto=standby.cod_produto
                ).first()

                if item_carteira:
                    # Verificar se qtd_saldo_produto_pedido é 0 ou NULL
                    if not item_carteira.qtd_saldo_produto_pedido or item_carteira.qtd_saldo_produto_pedido == 0:
                        logger.info(f"      → ZERADO NA CARTEIRA: Pedido {standby.num_pedido} | Produto {standby.cod_produto} | Carteira Qtd: {item_carteira.qtd_saldo_produto_pedido}")
                        db.session.delete(standby)
                        zerados_na_carteira += 1

            if zerados_na_carteira > 0:
                db.session.commit()
                logger.info(f"   ✅ {zerados_na_carteira} itens zerados na carteira EXCLUÍDOS com sucesso")
            else:
                logger.info("   ✅ Nenhum item zerado na carteira encontrado")


            # ====================================================================
            # ESTATÍSTICAS FINAIS
            # ====================================================================
            logger.info("\n" + "=" * 80)
            logger.info("📊 ESTATÍSTICAS FINAIS DA LIMPEZA")
            logger.info("=" * 80)

            total_excluidos = len(itens_zerados) + orfaos_excluidos + zerados_na_carteira

            logger.info(f"   🗑️  Registros zerados excluídos: {len(itens_zerados)}")
            logger.info(f"   🗑️  Órfãos excluídos: {orfaos_excluidos}")
            logger.info(f"   🗑️  Zerados na carteira excluídos: {zerados_na_carteira}")
            logger.info(f"   ✅ TOTAL EXCLUÍDO: {total_excluidos}")

            # Contar registros restantes
            registros_restantes = SaldoStandby.query.count()
            logger.info(f"   📦 Registros restantes em SaldoStandby: {registros_restantes}")

            logger.info("\n" + "=" * 80)
            logger.info("✅ LIMPEZA CONCLUÍDA COM SUCESSO!")
            logger.info("=" * 80)

            return {
                'sucesso': True,
                'zerados': len(itens_zerados),
                'orfaos': orfaos_excluidos,
                'zerados_carteira': zerados_na_carteira,
                'total_excluido': total_excluidos,
                'restantes': registros_restantes
            }

        except Exception as e:
            logger.error(f"❌ ERRO durante limpeza: {str(e)}")
            db.session.rollback()
            return {
                'sucesso': False,
                'erro': str(e)
            }


if __name__ == '__main__':
    resultado = limpar_saldo_standby()

    if resultado['sucesso']:
        print(f"\n✅ Script executado com sucesso!")
        print(f"   Total excluído: {resultado['total_excluido']}")
        print(f"   Registros restantes: {resultado['restantes']}")
        sys.exit(0)
    else:
        print(f"\n❌ Script falhou: {resultado.get('erro', 'Erro desconhecido')}")
        sys.exit(1)
