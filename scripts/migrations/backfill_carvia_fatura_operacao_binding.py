"""
Backfill: vincular operacoes a faturas cliente via itens existentes
===================================================================

Problema: faturas importadas via PDF nunca setavam fatura_cliente_id
nas operacoes, deixando 100% das operacoes com fatura_cliente_id=NULL
mesmo quando os itens da fatura ja tinham operacao_id resolvido.

Solucao: para cada fatura cliente, buscar itens com operacao_id
preenchido e setar operacao.fatura_cliente_id + status=FATURADO.

Idempotente: so atualiza operacoes com fatura_cliente_id IS NULL.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db


def run_backfill():
    """Executa backfill usando LinkingService.vincular_operacoes_da_fatura."""
    from app.carvia.models import CarviaFaturaCliente, CarviaOperacao
    from app.carvia.services.linking_service import LinkingService

    linker = LinkingService()

    # Diagnostico ANTES
    total_ops = CarviaOperacao.query.count()
    ops_sem_fatura = CarviaOperacao.query.filter(
        CarviaOperacao.fatura_cliente_id.is_(None)
    ).count()
    ops_faturadas = CarviaOperacao.query.filter(
        CarviaOperacao.status == 'FATURADO'
    ).count()

    print(f"=== ANTES do backfill ===")
    print(f"Total operacoes: {total_ops}")
    print(f"Operacoes sem fatura_cliente_id: {ops_sem_fatura}")
    print(f"Operacoes com status FATURADO: {ops_faturadas}")
    print()

    # Executar backfill
    faturas = CarviaFaturaCliente.query.all()
    total_vinculadas = 0
    total_ja_vinculadas = 0

    for fatura in faturas:
        stats = linker.vincular_operacoes_da_fatura(fatura.id)
        if stats['operacoes_vinculadas'] > 0:
            print(
                f"  Fatura {fatura.id} ({fatura.numero_fatura}): "
                f"{stats['operacoes_vinculadas']} vinculada(s), "
                f"{stats['operacoes_ja_vinculadas']} ja OK"
            )
        total_vinculadas += stats['operacoes_vinculadas']
        total_ja_vinculadas += stats['operacoes_ja_vinculadas']

    db.session.commit()

    # Diagnostico DEPOIS
    ops_sem_fatura_depois = CarviaOperacao.query.filter(
        CarviaOperacao.fatura_cliente_id.is_(None)
    ).count()
    ops_faturadas_depois = CarviaOperacao.query.filter(
        CarviaOperacao.status == 'FATURADO'
    ).count()

    print()
    print(f"=== RESULTADO ===")
    print(f"Faturas processadas: {len(faturas)}")
    print(f"Operacoes vinculadas (novas): {total_vinculadas}")
    print(f"Operacoes ja vinculadas: {total_ja_vinculadas}")
    print()
    print(f"=== DEPOIS do backfill ===")
    print(f"Operacoes sem fatura_cliente_id: {ops_sem_fatura_depois}")
    print(f"Operacoes com status FATURADO: {ops_faturadas_depois}")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        run_backfill()
