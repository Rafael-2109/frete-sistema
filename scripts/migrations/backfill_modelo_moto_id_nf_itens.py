"""
Backfill: Persistir modelo_moto_id em itens existentes
======================================================

Roda deteccao automatica em todos os itens de carvia_nf_itens que
ainda nao tem modelo_moto_id e persiste o resultado.

Pré-requisito: add_modelo_moto_id_nf_itens.py ja executada.

Uso: python scripts/migrations/backfill_modelo_moto_id_nf_itens.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app import create_app, db  # noqa: E402


def verificar_antes():
    """Mostra estado atual."""
    result = db.session.execute(db.text("""
        SELECT
            COUNT(*) AS total,
            COUNT(modelo_moto_id) AS com_modelo,
            COUNT(*) - COUNT(modelo_moto_id) AS sem_modelo
        FROM carvia_nf_itens
    """))
    row = result.fetchone()
    print(f"[BEFORE] Total itens: {row[0]}, com modelo: {row[1]}, sem modelo: {row[2]}")
    return row[2]


def executar():
    """Roda deteccao em batch por NF."""
    from app.carvia.services.pricing.moto_recognition_service import MotoRecognitionService

    moto_svc = MotoRecognitionService()

    # Buscar NFs distintas que tem itens sem modelo
    nf_ids = db.session.execute(db.text("""
        SELECT DISTINCT nf_id FROM carvia_nf_itens
        WHERE modelo_moto_id IS NULL
        ORDER BY nf_id
    """)).scalars().all()

    total_detectados = 0
    for i, nf_id in enumerate(nf_ids, 1):
        count = moto_svc.detectar_e_persistir_nf(nf_id)
        total_detectados += count
        if count > 0:
            print(f"  NF {nf_id}: {count} modelo(s) detectado(s)")
        if i % 100 == 0:
            db.session.commit()
            print(f"  ... processadas {i}/{len(nf_ids)} NFs")

    db.session.commit()
    print(f"[OK] Backfill completo: {total_detectados} itens atualizados em {len(nf_ids)} NFs")


def verificar_depois():
    """Mostra estado final."""
    result = db.session.execute(db.text("""
        SELECT
            COUNT(*) AS total,
            COUNT(modelo_moto_id) AS com_modelo,
            COUNT(*) - COUNT(modelo_moto_id) AS sem_modelo
        FROM carvia_nf_itens
    """))
    row = result.fetchone()
    print(f"[AFTER] Total itens: {row[0]}, com modelo: {row[1]}, sem modelo: {row[2]}")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        sem_modelo = verificar_antes()
        if sem_modelo == 0:
            print("[SKIP] Todos os itens ja tem modelo — nada a fazer")
        else:
            executar()
        verificar_depois()
