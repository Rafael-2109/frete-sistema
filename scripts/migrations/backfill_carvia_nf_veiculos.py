"""
Backfill: Extrair e persistir veiculos (chassi/modelo/cor) em carvia_nf_veiculos
=================================================================================

Data fix (sem DDL) — tabela carvia_nf_veiculos ja existe mas nunca foi populada.

O parser DANFE extrai veiculos via LLM (get_veiculos_info()), mas o ImportacaoService
nao persistia os dados. Este script re-parseia PDFs armazenados no S3 para NFs que:
1. Tem arquivo_pdf_path (PDF no S3)
2. Tem itens com modelo_moto_id IS NOT NULL (sao NFs de moto)
3. Nao tem registros em carvia_nf_veiculos (ainda nao processadas)

Idempotente: pula NFs que ja tem veiculos. Dedup por chassi (UNIQUE constraint).
Requer: ANTHROPIC_API_KEY configurada (extracoes via LLM Haiku/Sonnet).
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from app.carvia.models import CarviaNf, CarviaNfItem, CarviaNfVeiculo

import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def backfill_veiculos(dry_run=False):
    """Re-parseia PDFs de NFs moto para extrair e persistir veiculos."""
    from app.utils.file_storage import get_file_storage
    from app.carvia.services.parsers.danfe_pdf_parser import DanfePDFParser

    # NFs candidatas: tem PDF, tem itens moto, sem veiculos
    nfs_moto = (
        db.session.query(CarviaNf)
        .filter(
            CarviaNf.status == 'ATIVA',
            CarviaNf.arquivo_pdf_path.isnot(None),
            CarviaNf.id.in_(
                db.session.query(CarviaNfItem.nf_id)
                .filter(CarviaNfItem.modelo_moto_id.isnot(None))
                .distinct()
            ),
            ~CarviaNf.id.in_(
                db.session.query(CarviaNfVeiculo.nf_id).distinct()
            ),
        )
        .order_by(CarviaNf.id)
        .all()
    )

    print(f"NFs candidatas (moto, com PDF, sem veiculos): {len(nfs_moto)}")
    if not nfs_moto:
        print("Nada a fazer.")
        return

    storage = get_file_storage()
    total_inseridos = 0
    total_erros = 0
    total_sem_veiculos = 0

    for nf in nfs_moto:
        print(f"\n--- NF #{nf.id} ({nf.numero_nf}) | PDF: {nf.arquivo_pdf_path}")

        try:
            pdf_bytes = storage.download_file(nf.arquivo_pdf_path)
            if not pdf_bytes:
                print(f"  ERRO: falha ao baixar PDF")
                total_erros += 1
                continue

            parser = DanfePDFParser(pdf_bytes=pdf_bytes)
            if not parser.is_valid():
                print(f"  ERRO: PDF invalido pelo parser")
                total_erros += 1
                continue

            veiculos = parser.get_veiculos_info()
            if not veiculos:
                print(f"  Nenhum veiculo extraido (gate NCM ou LLM nao encontrou)")
                total_sem_veiculos += 1
                continue

            nf_inseridos = 0
            for v in veiculos:
                chassi = (v.get('chassi') or '').strip()
                if not chassi:
                    continue

                # Dedup: chassi UNIQUE no banco
                existente = CarviaNfVeiculo.query.filter_by(chassi=chassi).first()
                if existente:
                    print(f"  Chassi {chassi} ja existe (NF #{existente.nf_id}) — skip")
                    continue

                if not dry_run:
                    db.session.add(CarviaNfVeiculo(
                        nf_id=nf.id,
                        chassi=chassi,
                        modelo=v.get('modelo'),
                        cor=v.get('cor'),
                        numero_motor=v.get('numero_motor'),
                        ano=v.get('ano_modelo'),
                    ))
                nf_inseridos += 1

            if nf_inseridos:
                if not dry_run:
                    db.session.flush()
                total_inseridos += nf_inseridos
                print(f"  {nf_inseridos} veiculo(s) {'inserido(s)' if not dry_run else '(dry-run)'}")

        except Exception as e:
            logger.error(f"  ERRO NF #{nf.id}: {e}")
            total_erros += 1
            if not dry_run:
                db.session.rollback()
            continue

    if not dry_run:
        db.session.commit()

    print(f"\n{'='*60}")
    print(f"Backfill {'(DRY-RUN) ' if dry_run else ''}concluido:")
    print(f"  NFs processadas: {len(nfs_moto)}")
    print(f"  Veiculos inseridos: {total_inseridos}")
    print(f"  NFs sem veiculos extraidos: {total_sem_veiculos}")
    print(f"  Erros: {total_erros}")


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv
    if dry_run:
        print("*** MODO DRY-RUN — nenhuma alteracao sera gravada ***\n")

    app = create_app()
    with app.app_context():
        # BEFORE
        total_veiculos_antes = db.session.query(CarviaNfVeiculo).count()
        total_nfs_com_veiculos = (
            db.session.query(CarviaNfVeiculo.nf_id).distinct().count()
        )
        print(f"BEFORE: {total_veiculos_antes} veiculos em {total_nfs_com_veiculos} NFs")

        backfill_veiculos(dry_run=dry_run)

        # AFTER
        total_veiculos_depois = db.session.query(CarviaNfVeiculo).count()
        total_nfs_com_veiculos_depois = (
            db.session.query(CarviaNfVeiculo.nf_id).distinct().count()
        )
        print(f"\nAFTER: {total_veiculos_depois} veiculos em {total_nfs_com_veiculos_depois} NFs")
