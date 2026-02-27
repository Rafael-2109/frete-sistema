"""
Correcao de Dados: UoM De-Para ↔ Odoo (product.supplierinfo)
==============================================================

Corrige registros existentes onde:
1. fator_conversao = 1000 mas um_fornecedor = 'Units' (deveria ser 'MIL')
2. odoo_product_uom_id esta NULL (precisa ser preenchido com ID da UoM do Odoo)

Acoes:
1. Busca o ID da UoM 'MIL' no Odoo
2. UPDATE local: preenche odoo_product_uom_id para todos com fator_conversao = 1000
3. UPDATE Odoo: corrige product.supplierinfo.product_uom para registros com 'Units' errado
4. UPDATE local: corrige um_fornecedor de 'Units' para 'MIL' nos registros afetados

Uso:
    source .venv/bin/activate
    python scripts/migrations/corrigir_uom_depara_odoo.py [--dry-run]
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from app.recebimento.models import ProdutoFornecedorDepara
from app.odoo.utils.connection import get_odoo_connection
from decimal import Decimal

import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='Corrigir UoM no De-Para e Odoo')
    parser.add_argument('--dry-run', action='store_true', help='Apenas mostrar o que seria feito')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        # =================================================================
        # PASSO 1: Buscar ID da UoM 'MIL' no Odoo
        # =================================================================
        logger.info("=== PASSO 1: Buscar UoM 'MIL' no Odoo ===")

        odoo = get_odoo_connection()
        if not odoo.authenticate():
            logger.error("Falha ao autenticar no Odoo")
            sys.exit(1)

        # Tentar buscar MIL
        mil_id = None
        for nome in ['MIL', 'MI', 'ML']:
            uom_ids = odoo.search('uom.uom', [('name', '=ilike', nome)], limit=1)
            if uom_ids:
                mil_id = uom_ids[0]
                uom_data = odoo.read('uom.uom', [mil_id], ['id', 'name', 'factor'])
                logger.info(f"UoM encontrada: {uom_data}")
                break

        if not mil_id:
            logger.error("UoM 'MIL'/'MI'/'ML' NAO encontrada no Odoo!")
            logger.error("Verifique as UoMs disponiveis: uom.uom")
            sys.exit(1)

        logger.info(f"UoM MIL ID no Odoo: {mil_id}")

        # =================================================================
        # PASSO 2: Buscar registros locais que precisam de correcao
        # =================================================================
        logger.info("\n=== PASSO 2: Buscar registros locais ===")

        # Registros com fator_conversao = 1000 que precisam de odoo_product_uom_id
        registros_sem_uom_id = ProdutoFornecedorDepara.query.filter(
            ProdutoFornecedorDepara.fator_conversao == Decimal('1000.0000'),
            ProdutoFornecedorDepara.odoo_product_uom_id.is_(None)
        ).all()

        logger.info(f"Registros com fator=1000 sem odoo_product_uom_id: {len(registros_sem_uom_id)}")

        # Registros com um_fornecedor = 'Units' E fator_conversao = 1000 (UoM errada)
        registros_units_errado = ProdutoFornecedorDepara.query.filter(
            ProdutoFornecedorDepara.fator_conversao == Decimal('1000.0000'),
            ProdutoFornecedorDepara.um_fornecedor == 'Units'
        ).all()

        logger.info(f"Registros com 'Units' errado (fator=1000): {len(registros_units_errado)}")

        for r in registros_units_errado:
            logger.info(
                f"  ID={r.id} | CNPJ={r.cnpj_fornecedor} | "
                f"Prod={r.cod_produto_fornecedor} | "
                f"UM={r.um_fornecedor} | Fator={r.fator_conversao} | "
                f"SupplierInfo={r.odoo_supplierinfo_id}"
            )

        if args.dry_run:
            logger.info("\n[DRY-RUN] Nenhuma alteracao sera feita")
            logger.info(f"[DRY-RUN] {len(registros_sem_uom_id)} registros receberiam odoo_product_uom_id={mil_id}")
            logger.info(f"[DRY-RUN] {len(registros_units_errado)} registros teriam um_fornecedor corrigido para 'MIL'")
            logger.info(f"[DRY-RUN] {len(registros_units_errado)} supplierinfos seriam atualizados no Odoo")
            return

        # =================================================================
        # PASSO 3: UPDATE local — preencher odoo_product_uom_id
        # =================================================================
        logger.info("\n=== PASSO 3: UPDATE local (odoo_product_uom_id) ===")

        for r in registros_sem_uom_id:
            r.odoo_product_uom_id = mil_id
            logger.info(f"  ID={r.id}: odoo_product_uom_id = {mil_id}")

        # =================================================================
        # PASSO 4: UPDATE local — corrigir um_fornecedor de 'Units' para 'MIL'
        # =================================================================
        logger.info("\n=== PASSO 4: UPDATE local (um_fornecedor) ===")

        for r in registros_units_errado:
            r.um_fornecedor = 'MIL'
            r.odoo_product_uom_id = mil_id
            logger.info(f"  ID={r.id}: um_fornecedor 'Units' -> 'MIL'")

        db.session.commit()
        logger.info("Commit local OK")

        # =================================================================
        # PASSO 5: UPDATE Odoo — corrigir product_uom nos supplierinfos
        # =================================================================
        logger.info("\n=== PASSO 5: UPDATE Odoo (product.supplierinfo.product_uom) ===")

        erros_odoo = 0
        corrigidos_odoo = 0

        for r in registros_units_errado:
            if not r.odoo_supplierinfo_id:
                logger.warning(f"  ID={r.id}: sem odoo_supplierinfo_id, pulando Odoo")
                continue

            try:
                odoo.write(
                    'product.supplierinfo',
                    [r.odoo_supplierinfo_id],
                    {'product_uom': mil_id}
                )
                corrigidos_odoo += 1
                logger.info(
                    f"  Supplierinfo {r.odoo_supplierinfo_id}: "
                    f"product_uom = {mil_id} (MIL)"
                )
            except Exception as e:
                erros_odoo += 1
                logger.error(
                    f"  Supplierinfo {r.odoo_supplierinfo_id}: ERRO - {e}"
                )

        # =================================================================
        # RESUMO
        # =================================================================
        logger.info("\n" + "=" * 60)
        logger.info("RESUMO DA CORRECAO")
        logger.info("=" * 60)
        logger.info(f"UoM MIL ID no Odoo: {mil_id}")
        logger.info(f"Registros com odoo_product_uom_id preenchido: {len(registros_sem_uom_id)}")
        logger.info(f"Registros com um_fornecedor corrigido: {len(registros_units_errado)}")
        logger.info(f"Supplierinfos corrigidos no Odoo: {corrigidos_odoo}")
        logger.info(f"Erros Odoo: {erros_odoo}")
        logger.info("=" * 60)

        if erros_odoo > 0:
            logger.warning("ATENCAO: Houve erros ao atualizar Odoo. Verifique os logs acima.")
        else:
            logger.info("Correcao concluida com sucesso!")


if __name__ == '__main__':
    main()
