"""Backfill: cria EntregaMonitorada (origem='CARVIA') para CarviaNf ATIVAS existentes.

Idempotente: usa sincronizar_entrega_carvia_por_nf que faz upsert. Pode ser
re-executado sem duplicar registros.

Executa em batches de 100 com commit incremental para evitar transacao longa.
Erros individuais sao logados mas nao abortam o batch.

Pre-requisito: migration add_origem_entrega_monitorada.py ja aplicada.

Uso:
    source .venv/bin/activate
    python scripts/migrations/backfill_entrega_monitorada_carvia.py
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db
from app.carvia.models import CarviaNf
from app.monitoramento.models import EntregaMonitorada
from app.utils.sincronizar_entregas_carvia import sincronizar_entrega_carvia_por_nf

BATCH_SIZE = 100


def main():
    app = create_app()
    with app.app_context():
        total = CarviaNf.query.filter_by(status='ATIVA').count()
        print(f"[info] Total CarviaNf ATIVA: {total}")

        ja_existem = (
            EntregaMonitorada.query
            .filter_by(origem='CARVIA')
            .count()
        )
        print(f"[info] EntregaMonitorada origem='CARVIA' existentes: {ja_existem}")

        if total == 0:
            print("[skip] Nenhuma CarviaNf para processar")
            return

        processadas = 0
        criadas = 0
        atualizadas = 0
        erros = 0
        nfs_com_erro: list = []

        offset = 0
        while offset < total:
            batch = (
                CarviaNf.query
                .filter_by(status='ATIVA')
                .order_by(CarviaNf.id)
                .offset(offset)
                .limit(BATCH_SIZE)
                .all()
            )

            for nf in batch:
                try:
                    # Verifica se ja existia antes para contabilizar criadas vs atualizadas
                    ja_existia = (
                        EntregaMonitorada.query
                        .filter_by(numero_nf=nf.numero_nf, origem='CARVIA')
                        .first()
                    ) is not None

                    sincronizar_entrega_carvia_por_nf(nf.numero_nf)

                    if ja_existia:
                        atualizadas += 1
                    else:
                        criadas += 1
                except Exception as e:
                    db.session.rollback()
                    erros += 1
                    nfs_com_erro.append((nf.numero_nf, str(e)))
                    print(
                        f"[erro] NF {nf.numero_nf} (id={nf.id}): {e}"
                    )
                finally:
                    processadas += 1

            offset += BATCH_SIZE
            print(
                f"[progresso] {processadas}/{total} "
                f"(criadas={criadas} atualizadas={atualizadas} erros={erros})"
            )

        # Resumo final
        print("\n[resumo]")
        print(f"  Total processadas: {processadas}")
        print(f"  Criadas: {criadas}")
        print(f"  Atualizadas: {atualizadas}")
        print(f"  Erros: {erros}")

        total_carvia_pos = (
            EntregaMonitorada.query
            .filter_by(origem='CARVIA')
            .count()
        )
        total_nacom_pos = (
            EntregaMonitorada.query
            .filter_by(origem='NACOM')
            .count()
        )
        print("\n[estado final]")
        print(f"  EntregaMonitorada origem='CARVIA': {total_carvia_pos}")
        print(f"  EntregaMonitorada origem='NACOM':  {total_nacom_pos}")

        if nfs_com_erro:
            print("\n[nfs com erro]")
            for numero, msg in nfs_com_erro[:20]:
                print(f"  {numero}: {msg}")
            if len(nfs_com_erro) > 20:
                print(f"  ... +{len(nfs_com_erro) - 20} erros adicionais")


if __name__ == '__main__':
    main()
