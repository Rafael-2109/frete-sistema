"""
Migration: Unifica DACTE PDF do CTe Complementar em coluna direta.

Adiciona `cte_pdf_path` em carvia_cte_complementares (alinhando com
carvia_operacoes e carvia_subcontratos — SOT do PDF) e faz backfill a
partir da emissao SUCESSO mais recente, copiando
`resultado_json['dacte_s3_path']` para o campo direto.

Antes desta unificacao havia 2 locais para o mesmo PDF:
  - CarviaEmissaoCteComplementar.resultado_json['dacte_s3_path']
  - (campo cte_pdf_path nao existia → AttributeError no worker
     verificar_ctrc_cte_comp_job, commit 7e7ceee7)

Agora: SOT = CarviaCteComplementar.cte_pdf_path. resultado_json mantem
o path como audit log da emissao.

Executar: python scripts/migrations/adicionar_cte_pdf_path_cte_complementar.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


def run():
    from app import create_app, db

    app = create_app()
    with app.app_context():
        conn = db.engine.connect()

        # 1) Adicionar coluna se nao existir
        result = conn.execute(db.text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'carvia_cte_complementares'
              AND column_name = 'cte_pdf_path'
        """))
        if result.fetchone():
            print("[OK] carvia_cte_complementares.cte_pdf_path ja existe.")
        else:
            conn.execute(db.text("""
                ALTER TABLE carvia_cte_complementares
                ADD COLUMN cte_pdf_path VARCHAR(500)
            """))
            conn.commit()
            print("[+] carvia_cte_complementares.cte_pdf_path adicionado.")

        # 2) Backfill: copia dacte_s3_path da emissao SUCESSO mais recente
        #    para o campo direto, apenas onde ainda nao foi populado.
        antes = conn.execute(db.text("""
            SELECT COUNT(*) FROM carvia_cte_complementares
            WHERE cte_pdf_path IS NULL OR cte_pdf_path = ''
        """)).scalar()

        backfill_result = conn.execute(db.text("""
            UPDATE carvia_cte_complementares cc
            SET cte_pdf_path = sub.dacte_s3_path
            FROM (
                SELECT DISTINCT ON (e.cte_complementar_id)
                    e.cte_complementar_id,
                    e.resultado_json->>'dacte_s3_path' AS dacte_s3_path
                FROM carvia_emissao_cte_complementar e
                WHERE e.status = 'SUCESSO'
                  AND e.resultado_json->>'dacte_s3_path' IS NOT NULL
                  AND e.resultado_json->>'dacte_s3_path' <> ''
                ORDER BY e.cte_complementar_id, e.criado_em DESC
            ) sub
            WHERE cc.id = sub.cte_complementar_id
              AND (cc.cte_pdf_path IS NULL OR cc.cte_pdf_path = '')
        """))
        conn.commit()

        atualizados = backfill_result.rowcount
        depois = conn.execute(db.text("""
            SELECT COUNT(*) FROM carvia_cte_complementares
            WHERE cte_pdf_path IS NULL OR cte_pdf_path = ''
        """)).scalar()

        print(
            f"[+] Backfill: {atualizados} CTe Comps populados via emissao "
            f"SUCESSO (vazios: {antes} -> {depois})."
        )

        conn.close()
        print("\nMigration concluida.")


if __name__ == '__main__':
    run()
