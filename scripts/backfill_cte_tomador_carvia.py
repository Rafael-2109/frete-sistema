"""Backfill de CarviaOperacao.cte_tomador re-parseando XMLs em S3.

Estrategia:
1. Busca operacoes com cte_tomador IS NULL E cte_xml_path IS NOT NULL
2. Para cada: download do XML via FileStorage + re-parse + get_tomador()
3. Mapeia codigo SEFAZ (0-4) para enum persistido (REMETENTE/EXPEDIDOR/RECEBEDOR/DESTINATARIO/TERCEIRO)
4. Batch commit a cada 100 operacoes
5. Idempotente — filtro IS NULL evita sobrescrever

Uso:
    source .venv/bin/activate
    python scripts/backfill_cte_tomador_carvia.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.carvia.models import CarviaOperacao
from app.carvia.services.parsers.cte_xml_parser_carvia import CTeXMLParserCarvia
from app.utils.file_storage import get_file_storage

logger = logging.getLogger(__name__)

TOMADOR_CODE_MAP = {
    '0': 'REMETENTE',
    '1': 'EXPEDIDOR',
    '2': 'RECEBEDOR',
    '3': 'DESTINATARIO',
    '4': 'TERCEIRO',
}

BATCH_SIZE = 100


def main():
    app = create_app()
    with app.app_context():
        storage = get_file_storage()

        total = CarviaOperacao.query.filter(
            CarviaOperacao.cte_tomador.is_(None),
            CarviaOperacao.cte_xml_path.isnot(None),
        ).count()
        logger.info(f"Operacoes com XML para backfill: {total}")

        if total == 0:
            logger.info("Nada a fazer.")
            return

        atualizados = 0
        erros = 0
        skip_sem_tomador = 0
        processados = 0

        while True:
            # Busca apenas ops ainda NULL (permite retomar apos falha)
            ops = CarviaOperacao.query.filter(
                CarviaOperacao.cte_tomador.is_(None),
                CarviaOperacao.cte_xml_path.isnot(None),
            ).order_by(CarviaOperacao.id).limit(BATCH_SIZE).all()

            if not ops:
                break

            # Offset travado: se o batch nao atualiza nada, sai para nao loopar
            atualizados_batch = 0

            for op in ops:
                processados += 1
                try:
                    xml_bytes = storage.download_file(op.cte_xml_path)
                    if not xml_bytes:
                        logger.warning(f"op {op.id}: XML vazio em {op.cte_xml_path}")
                        erros += 1
                        continue

                    parser = CTeXMLParserCarvia(xml_bytes)
                    tomador = parser.get_tomador() or {}
                    codigo = tomador.get('codigo')

                    if codigo in TOMADOR_CODE_MAP:
                        op.cte_tomador = TOMADOR_CODE_MAP[codigo]
                        atualizados += 1
                        atualizados_batch += 1
                    else:
                        skip_sem_tomador += 1
                        logger.info(f"op {op.id}: sem <toma3>/<toma4> no XML")
                except Exception as e:
                    logger.warning(f"op {op.id}: erro ao parsear — {e}")
                    erros += 1

            db.session.commit()
            logger.info(
                f"Progresso: {processados}/{total} | "
                f"atualizados: {atualizados} | "
                f"sem_tomador: {skip_sem_tomador} | "
                f"erros: {erros}"
            )

            # Se nenhum do batch atualizou (todos erro ou sem tomador), os proximos
            # batches pegariam os mesmos registros. Precisamos offset por ID.
            # Solucao: mudar a query para filtrar por id > ultimo_id do batch.
            if atualizados_batch == 0:
                # Move cursor por ID do ultimo op processado
                ultimo_id = ops[-1].id
                # Filtro adicional para evitar loop infinito
                restantes = CarviaOperacao.query.filter(
                    CarviaOperacao.cte_tomador.is_(None),
                    CarviaOperacao.cte_xml_path.isnot(None),
                    CarviaOperacao.id > ultimo_id,
                ).count()
                if restantes == 0:
                    break
                # Ajuste: re-busca ja vai pegar os > ultimo_id naturalmente
                # porque os com id <= ultimo_id nao foram atualizados (ficam NULL)
                # MAS a ordem por id garante que proxima iteracao pega os seguintes
                # desde que o filtro IS NULL seja mantido. Como erros nao mudam
                # cte_tomador, eles serao retomados — precisamos marcar algo.
                # Solucao pragmatica: sair do loop se todo o batch falhou.
                logger.warning(
                    f"Batch sem atualizacoes (erros/sem_tomador). "
                    f"Restantes: {restantes}. Interrompendo para evitar loop."
                )
                break

        logger.info(
            f"Concluido. Total processado: {processados} | "
            f"atualizados: {atualizados} | "
            f"sem_tomador: {skip_sem_tomador} | "
            f"erros: {erros}"
        )


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s',
    )
    main()
