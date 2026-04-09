"""
Migration: adicionar icms_aliquota a carvia_operacoes
+ criar tabela carvia_emissao_cte_complementar.

Backfill: re-parseia XMLs de CTe do S3 para preencher icms_aliquota.

Uso:
    source .venv/bin/activate
    python scripts/migrations/add_icms_aliquota_carvia_operacoes.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)


def run():
    from app import create_app, db

    app = create_app()
    with app.app_context():
        conn = db.engine.raw_connection()
        cursor = conn.cursor()

        try:
            # 1. DDL — adicionar coluna icms_aliquota
            cursor.execute("""
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'carvia_operacoes'
                AND column_name = 'icms_aliquota'
            """)
            if not cursor.fetchone():
                cursor.execute(
                    "ALTER TABLE carvia_operacoes ADD COLUMN icms_aliquota NUMERIC(5, 2)"
                )
                conn.commit()
                logger.info("Coluna icms_aliquota adicionada a carvia_operacoes")
            else:
                logger.info("Coluna icms_aliquota ja existe — skip DDL")

            # 2. DDL — criar tabela carvia_emissao_cte_complementar
            cursor.execute("""
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'carvia_emissao_cte_complementar'
            """)
            if not cursor.fetchone():
                cursor.execute("""
                    CREATE TABLE carvia_emissao_cte_complementar (
                        id SERIAL PRIMARY KEY,
                        custo_entrega_id INTEGER NOT NULL
                            REFERENCES carvia_custos_entrega(id),
                        cte_complementar_id INTEGER NOT NULL
                            REFERENCES carvia_cte_complementares(id),
                        operacao_id INTEGER NOT NULL
                            REFERENCES carvia_operacoes(id),
                        ctrc_pai VARCHAR(30) NOT NULL,
                        motivo_ssw VARCHAR(5) NOT NULL,
                        filial_ssw VARCHAR(10) NOT NULL DEFAULT 'CAR',
                        valor_calculado NUMERIC(15, 2) NOT NULL,
                        icms_aliquota_usada NUMERIC(5, 2),
                        status VARCHAR(20) NOT NULL DEFAULT 'PENDENTE',
                        etapa VARCHAR(30),
                        job_id VARCHAR(100),
                        erro_ssw TEXT,
                        resultado_json JSONB,
                        criado_por VARCHAR(100) NOT NULL,
                        criado_em TIMESTAMP DEFAULT NOW(),
                        atualizado_em TIMESTAMP DEFAULT NOW()
                    )
                """)
                cursor.execute("""
                    CREATE INDEX ix_emissao_cte_comp_custo
                        ON carvia_emissao_cte_complementar(custo_entrega_id)
                """)
                cursor.execute("""
                    CREATE INDEX ix_emissao_cte_comp_cte
                        ON carvia_emissao_cte_complementar(cte_complementar_id)
                """)
                cursor.execute("""
                    CREATE INDEX ix_emissao_cte_comp_operacao
                        ON carvia_emissao_cte_complementar(operacao_id)
                """)
                cursor.execute("""
                    CREATE INDEX ix_emissao_cte_comp_status
                        ON carvia_emissao_cte_complementar(status)
                """)
                conn.commit()
                logger.info("Tabela carvia_emissao_cte_complementar criada")
            else:
                logger.info("Tabela carvia_emissao_cte_complementar ja existe — skip")

            # 3. Backfill — re-parsear XMLs para preencher icms_aliquota
            cursor.execute("""
                SELECT id, cte_xml_path FROM carvia_operacoes
                WHERE icms_aliquota IS NULL
                AND cte_xml_path IS NOT NULL
                AND cte_xml_path != ''
            """)
            rows = cursor.fetchall()
            logger.info("Backfill: %d operacoes com XML mas sem icms_aliquota", len(rows))

            sucesso = 0
            erro = 0
            for op_id, xml_path in rows:
                try:
                    from app.utils.file_storage import get_file_storage
                    storage = get_file_storage()
                    xml_bytes = storage.get_file_content(xml_path)
                    if not xml_bytes:
                        logger.warning("  op=%d: XML vazio/nao encontrado em %s", op_id, xml_path)
                        erro += 1
                        continue

                    from app.carvia.services.parsers.cte_xml_parser_carvia import (
                        CTeXMLParserCarvia,
                    )
                    xml_str = xml_bytes.decode('utf-8', errors='replace')
                    parser = CTeXMLParserCarvia(xml_str)
                    impostos = parser.get_impostos()
                    aliquota = impostos.get('aliquota_icms')

                    if aliquota is not None:
                        cursor.execute(
                            "UPDATE carvia_operacoes SET icms_aliquota = %s WHERE id = %s",
                            (float(aliquota), op_id)
                        )
                        sucesso += 1
                    else:
                        logger.debug("  op=%d: XML sem aliquota ICMS", op_id)
                except Exception as e:
                    logger.warning("  op=%d: erro no backfill: %s", op_id, e)
                    erro += 1

            conn.commit()
            logger.info(
                "Backfill concluido: %d atualizados, %d erros, %d total",
                sucesso, erro, len(rows)
            )

        finally:
            cursor.close()
            conn.close()


if __name__ == '__main__':
    run()
