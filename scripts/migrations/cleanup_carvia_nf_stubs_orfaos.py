"""
Cleanup: remover stubs FATURA_REFERENCIA orfaos em carvia_nfs
=============================================================

Identifica stubs CarviaNf (tipo_fonte='FATURA_REFERENCIA') que possuem
uma NF real correspondente (mesmo numero+CNPJ normalizados).

Para cada par stub/NF real:
1. Re-linka FKs em carvia_fatura_cliente_itens (nf_id stub -> NF real)
2. Re-linka FKs em carvia_fatura_transportadora_itens (nf_id stub -> NF real)
3. Re-linka junctions em carvia_operacao_nfs (nf_id stub -> NF real)
4. Deleta itens orfaos do stub (carvia_nf_itens)
5. Deleta o stub

Uso:
    python scripts/migrations/cleanup_carvia_nf_stubs_orfaos.py [--dry-run]

IMPORTANTE: Executar APOS deploy da Mudanca 1 (merge NF sobre stub).
"""

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def run(dry_run=True):
    from app import create_app, db
    from sqlalchemy import func, text

    app = create_app()
    with app.app_context():
        # 1. Encontrar stubs FATURA_REFERENCIA
        stubs_query = text("""
            SELECT s.id AS stub_id,
                   s.numero_nf AS stub_numero,
                   s.cnpj_emitente AS stub_cnpj,
                   r.id AS real_id,
                   r.numero_nf AS real_numero,
                   r.tipo_fonte AS real_tipo
            FROM carvia_nfs s
            JOIN carvia_nfs r ON (
                ltrim(r.numero_nf, '0') = ltrim(s.numero_nf, '0')
                AND regexp_replace(r.cnpj_emitente, '[^0-9]', '', 'g')
                    = regexp_replace(s.cnpj_emitente, '[^0-9]', '', 'g')
                AND r.tipo_fonte != 'FATURA_REFERENCIA'
                AND r.id != s.id
            )
            WHERE s.tipo_fonte = 'FATURA_REFERENCIA'
            ORDER BY s.id
        """)

        result = db.session.execute(stubs_query).fetchall()
        logger.info(f"Stubs FATURA_REFERENCIA com NF real correspondente: {len(result)}")

        if not result:
            logger.info("Nenhum stub orfao encontrado. Nada a fazer.")
            return

        total_itens_cli = 0
        total_itens_transp = 0
        total_junctions = 0
        total_nf_itens = 0
        total_stubs = 0

        for row in result:
            stub_id = row[0]
            stub_numero = row[1]
            real_id = row[3]
            real_numero = row[4]

            logger.info(
                f"Processando stub_id={stub_id} (NF {stub_numero}) "
                f"-> real_id={real_id} (NF {real_numero})"
            )

            # Re-link fatura_cliente_itens
            count_cli = db.session.execute(text("""
                UPDATE carvia_fatura_cliente_itens
                SET nf_id = :real_id
                WHERE nf_id = :stub_id
            """), {'real_id': real_id, 'stub_id': stub_id}).rowcount
            total_itens_cli += count_cli
            if count_cli > 0:
                logger.info(f"  Re-linked {count_cli} fatura_cliente_itens")

            # Re-link fatura_transportadora_itens
            count_transp = db.session.execute(text("""
                UPDATE carvia_fatura_transportadora_itens
                SET nf_id = :real_id
                WHERE nf_id = :stub_id
            """), {'real_id': real_id, 'stub_id': stub_id}).rowcount
            total_itens_transp += count_transp
            if count_transp > 0:
                logger.info(f"  Re-linked {count_transp} fatura_transportadora_itens")

            # Re-link junctions (carvia_operacao_nfs)
            # Cuidado: pode haver junction duplicada (stub + real para mesma operacao)
            # Primeiro, verificar quais operacoes ja tem junction com real_id
            existing_ops = db.session.execute(text("""
                SELECT operacao_id FROM carvia_operacao_nfs
                WHERE nf_id = :real_id
            """), {'real_id': real_id}).fetchall()
            existing_op_ids = {r[0] for r in existing_ops}

            # Junctions do stub que NAO conflitam com real
            stub_junctions = db.session.execute(text("""
                SELECT id, operacao_id FROM carvia_operacao_nfs
                WHERE nf_id = :stub_id
            """), {'stub_id': stub_id}).fetchall()

            for junc_row in stub_junctions:
                junc_id = junc_row[0]
                op_id = junc_row[1]
                if op_id in existing_op_ids:
                    # Conflito: real ja tem junction com essa operacao, deletar a do stub
                    db.session.execute(text("""
                        DELETE FROM carvia_operacao_nfs WHERE id = :junc_id
                    """), {'junc_id': junc_id})
                    logger.info(f"  Junction duplicada removida: op={op_id}")
                else:
                    # Sem conflito: re-linkar para real
                    db.session.execute(text("""
                        UPDATE carvia_operacao_nfs
                        SET nf_id = :real_id
                        WHERE id = :junc_id
                    """), {'real_id': real_id, 'junc_id': junc_id})
                    logger.info(f"  Junction re-linked: op={op_id}")
                total_junctions += 1

            # Deletar itens de produto do stub (carvia_nf_itens)
            count_nf_itens = db.session.execute(text("""
                DELETE FROM carvia_nf_itens WHERE nf_id = :stub_id
            """), {'stub_id': stub_id}).rowcount
            total_nf_itens += count_nf_itens

            # Deletar o stub
            db.session.execute(text("""
                DELETE FROM carvia_nfs WHERE id = :stub_id
            """), {'stub_id': stub_id})
            total_stubs += 1
            logger.info(f"  Stub deletado: id={stub_id}")

        logger.info(
            f"\n{'=' * 60}\n"
            f"RESUMO {'(DRY-RUN)' if dry_run else '(EXECUTADO)'}:\n"
            f"  Stubs removidos: {total_stubs}\n"
            f"  Itens fatura cliente re-linked: {total_itens_cli}\n"
            f"  Itens fatura transportadora re-linked: {total_itens_transp}\n"
            f"  Junctions processadas: {total_junctions}\n"
            f"  Itens NF (produto) removidos: {total_nf_itens}\n"
            f"{'=' * 60}"
        )

        if dry_run:
            db.session.rollback()
            logger.info("DRY-RUN: nenhuma mudanca gravada. Rode sem --dry-run para aplicar.")
        else:
            db.session.commit()
            logger.info("COMMIT: mudancas aplicadas com sucesso.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Cleanup stubs FATURA_REFERENCIA orfaos em carvia_nfs'
    )
    parser.add_argument(
        '--dry-run', action='store_true', default=True,
        help='Simular sem gravar (default: True)'
    )
    parser.add_argument(
        '--execute', action='store_true',
        help='Executar de verdade (override dry-run)'
    )
    args = parser.parse_args()

    dry_run = not args.execute
    run(dry_run=dry_run)
