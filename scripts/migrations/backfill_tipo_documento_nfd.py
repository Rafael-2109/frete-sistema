#!/usr/bin/env python3
"""
Backfill para preencher os novos campos em NFDs existentes:
- tipo_documento: 'NFD' ou 'NF'
- status_odoo: 'Devolução', 'Revertida' ou NULL
- status_monitoramento: sincronizado com EntregaMonitorada

Autor: Sistema de Fretes
Data: 11/01/2026
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db # noqa: E402
from app.devolucao.models import NFDevolucao # noqa: E402
from app.monitoramento.models import EntregaMonitorada # noqa: E402


def backfill():
    """Executa backfill dos novos campos"""
    app = create_app()
    with app.app_context():
        # Estatísticas
        stats = {
            'total': 0,
            'nfd_devolucao': 0,
            'nf_revertida': 0,
            'nf_monitoramento': 0,
            'nf_outros': 0,
            'status_monit_sync': 0,
            'ja_preenchidos': 0
        }

        print("=" * 60)
        print("📊 BACKFILL - tipo_documento e status_odoo")
        print("=" * 60)

        # Buscar todas as NFDs
        todas_nfds = NFDevolucao.query.filter(
            NFDevolucao.ativo == True
        ).all()

        stats['total'] = len(todas_nfds)
        print(f"\n📦 Total de NFDs no banco: {stats['total']}")

        # Filtrar apenas as que não têm tipo_documento preenchido
        nfds_sem_tipo = [n for n in todas_nfds if n.tipo_documento is None]
        print(f"📋 NFDs sem tipo_documento: {len(nfds_sem_tipo)}")

        for nfd in nfds_sem_tipo:
            # REGRA 1: Se origem_registro='ODOO' e tem odoo_dfe_id
            # Pode ser NFD (finnfe=4) ou NF revertida
            if nfd.origem_registro == 'ODOO':
                if nfd.odoo_nota_credito_id:
                    # NF revertida (tem nota de crédito vinculada)
                    nfd.tipo_documento = 'NF'
                    nfd.status_odoo = 'Revertida'
                    stats['nf_revertida'] += 1
                elif nfd.odoo_dfe_id:
                    # NFD (DFe com finnfe=4)
                    nfd.tipo_documento = 'NFD'
                    nfd.status_odoo = 'Devolução'
                    stats['nfd_devolucao'] += 1
                else:
                    # Outro tipo de registro do Odoo
                    nfd.tipo_documento = 'NF'
                    nfd.status_odoo = None
                    stats['nf_outros'] += 1

            # REGRA 2: Se origem_registro='MONITORAMENTO'
            elif nfd.origem_registro == 'MONITORAMENTO':
                nfd.tipo_documento = 'NF'
                nfd.status_odoo = None  # Será preenchido quando sincronizar
                stats['nf_monitoramento'] += 1

            # REGRA 3: Outros casos
            else:
                nfd.tipo_documento = 'NF'
                nfd.status_odoo = None
                stats['nf_outros'] += 1

        # Sincronizar status_monitoramento para TODAS as NFDs com entrega vinculada
        print("\n🔄 Sincronizando status_monitoramento...")
        for nfd in todas_nfds:
            if nfd.entrega_monitorada_id:
                entrega = db.session.get(EntregaMonitorada,nfd.entrega_monitorada_id) if nfd.entrega_monitorada_id else None
                if entrega and entrega.status_finalizacao in ('Cancelada', 'Devolvida', 'Troca de NF'):
                    if nfd.status_monitoramento != entrega.status_finalizacao:
                        nfd.status_monitoramento = entrega.status_finalizacao
                        stats['status_monit_sync'] += 1

        db.session.commit()

        # Contar já preenchidos
        stats['ja_preenchidos'] = stats['total'] - len(nfds_sem_tipo)

        print("\n" + "=" * 60)
        print("✅ BACKFILL CONCLUÍDO")
        print("=" * 60)
        print(f"\n📊 RESUMO:")
        print(f"   📄 NFD/Devolução: {stats['nfd_devolucao']}")
        print(f"   🔄 NF/Revertida: {stats['nf_revertida']}")
        print(f"   📊 NF/Monitoramento: {stats['nf_monitoramento']}")
        print(f"   ❓ NF/Outros: {stats['nf_outros']}")
        print(f"   ⏭️  Já preenchidos: {stats['ja_preenchidos']}")
        print(f"   🔗 Status Monit Sync: {stats['status_monit_sync']}")
        print("=" * 60)


if __name__ == '__main__':
    backfill()
