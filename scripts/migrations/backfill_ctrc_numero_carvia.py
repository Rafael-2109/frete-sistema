"""
Backfill: Extrair ctrc_numero de cte_chave_acesso em carvia_operacoes e carvia_cte_complementares.

O CTRC e derivado da chave de acesso do CTe (44 digitos):
  [25:34] = nCT (9 digitos, ex: "000000133" -> 133)
  [43]    = cDV (digito verificador)
  ctrc_numero = f"CAR-{nCT}-{cDV}"

Apenas registros com cte_chave_acesso NOT NULL e ctrc_numero IS NULL sao atualizados.

Uso:
    source .venv/bin/activate
    python scripts/migrations/backfill_ctrc_numero_carvia.py
"""

import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def extrair_ctrc_de_chave(chave: str) -> str | None:
    """Extrai CTRC formatado (CAR-nCT-cDV) da chave de acesso do CTe.

    Estrutura da chave (44 digitos):
      [0:2]=cUF [2:6]=AAMM [6:20]=CNPJ [20:22]=mod [22:25]=serie
      [25:34]=nCT [34]=tpEmis [35:43]=cCT [43]=cDV
    """
    if not chave or len(chave) != 44:
        return None
    try:
        nct_str = chave[25:34]  # 9 digitos zero-padded
        cdv = chave[43]          # 1 digito
        nct = int(nct_str)       # remove zeros a esquerda
        return f"CAR-{nct}-{cdv}"
    except (ValueError, IndexError):
        return None


def run():
    from app import create_app, db

    app = create_app()
    with app.app_context():
        conn = db.engine.raw_connection()
        cursor = conn.cursor()

        try:
            # ── carvia_operacoes ──
            cursor.execute("""
                SELECT id, cte_chave_acesso
                FROM carvia_operacoes
                WHERE cte_chave_acesso IS NOT NULL
                  AND ctrc_numero IS NULL
            """)
            ops = cursor.fetchall()
            logger.info("carvia_operacoes: %d registros para backfill", len(ops))

            ops_updated = 0
            for op_id, chave in ops:
                ctrc = extrair_ctrc_de_chave(chave)
                if ctrc:
                    cursor.execute(
                        "UPDATE carvia_operacoes SET ctrc_numero = %s WHERE id = %s",
                        (ctrc, op_id)
                    )
                    ops_updated += 1
                else:
                    logger.warning(
                        "Chave invalida para op_id=%d: %s", op_id, chave[:20] if chave else None
                    )

            logger.info("carvia_operacoes: %d atualizados", ops_updated)

            # ── carvia_cte_complementares ──
            cursor.execute("""
                SELECT id, cte_chave_acesso
                FROM carvia_cte_complementares
                WHERE cte_chave_acesso IS NOT NULL
                  AND ctrc_numero IS NULL
            """)
            comps = cursor.fetchall()
            logger.info("carvia_cte_complementares: %d registros para backfill", len(comps))

            comps_updated = 0
            for comp_id, chave in comps:
                ctrc = extrair_ctrc_de_chave(chave)
                if ctrc:
                    cursor.execute(
                        "UPDATE carvia_cte_complementares SET ctrc_numero = %s WHERE id = %s",
                        (ctrc, comp_id)
                    )
                    comps_updated += 1
                else:
                    logger.warning(
                        "Chave invalida para comp_id=%d: %s", comp_id, chave[:20] if chave else None
                    )

            conn.commit()
            logger.info(
                "Backfill concluido: %d operacoes + %d ctes_complementares atualizados",
                ops_updated, comps_updated
            )

            # Verificacao: quantos ficaram sem CTRC
            cursor.execute("""
                SELECT COUNT(*) FROM carvia_operacoes WHERE ctrc_numero IS NULL
            """)
            sem_ctrc_ops = cursor.fetchone()[0]
            cursor.execute("""
                SELECT COUNT(*) FROM carvia_cte_complementares WHERE ctrc_numero IS NULL
            """)
            sem_ctrc_comps = cursor.fetchone()[0]
            logger.info(
                "Pos-backfill: %d ops sem CTRC (manual/auto-portaria), %d comps sem CTRC",
                sem_ctrc_ops, sem_ctrc_comps
            )

        except Exception as e:
            conn.rollback()
            logger.error("Erro no backfill: %s", e)
            raise
        finally:
            cursor.close()
            conn.close()


if __name__ == '__main__':
    run()
