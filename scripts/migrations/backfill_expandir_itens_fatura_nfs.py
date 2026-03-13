"""
Backfill: Expandir itens de fatura com NFs do CTe ausentes
===========================================================

Problema: PDF SSW mostra 1 NF por linha de CTe, mesmo quando o CTe
referencia múltiplas NFs. O parser criou 1 item por linha.
Resultado: NFs extras do CTe ficam sem item na fatura.

Solução: Para cada fatura existente, chama expandir_itens_com_nfs_do_cte()
que cria itens suplementares para NFs da operação não representadas.

Pré-requisito: linking_service.py com método expandir_itens_com_nfs_do_cte()
Idempotente: pode rodar múltiplas vezes sem duplicar (verifica nf_ids existentes)
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


def main():
    from app import create_app, db
    from app.carvia.models import CarviaFaturaCliente
    from app.carvia.services.linking_service import LinkingService

    app = create_app()

    with app.app_context():
        faturas = CarviaFaturaCliente.query.order_by(CarviaFaturaCliente.id).all()
        print(f"Total de faturas cliente: {len(faturas)}")

        linker = LinkingService()
        total_criados = 0

        for fatura in faturas:
            stats = linker.expandir_itens_com_nfs_do_cte(fatura.id)
            criados = stats.get('itens_criados', 0)
            if criados > 0:
                total_criados += criados
                print(
                    f"  Fatura {fatura.id} ({fatura.numero_fatura}): "
                    f"+{criados} itens suplementares "
                    f"({stats['operacoes_verificadas']} ops verificadas)"
                )

        if total_criados > 0:
            db.session.commit()
            print(f"\nTotal: {total_criados} itens suplementares criados e commitados.")
        else:
            print("\nNenhum item suplementar necessário. Todas as NFs já estão representadas.")


if __name__ == '__main__':
    main()
