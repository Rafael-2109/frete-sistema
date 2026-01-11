#!/usr/bin/env python3
"""
Sincroniza data_entrada do Odoo para NFDs existentes
Busca l10n_br_data_entrada no Odoo via odoo_dfe_id

Autor: Sistema de Fretes
Data: 11/01/2026
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from app.devolucao.models import NFDevolucao
from app.odoo.utils.connection import get_odoo_connection
from datetime import datetime


def sync_data_entrada():
    """Sincroniza data_entrada do Odoo para NFDs existentes"""
    app = create_app()
    with app.app_context():
        print("=" * 60)
        print("📊 SYNC - data_entrada do Odoo")
        print("=" * 60)

        try:
            odoo = get_odoo_connection()
        except Exception as e:
            print(f"❌ Erro ao conectar ao Odoo: {e}")
            return

        # Buscar NFDs tipo 'NFD' sem data_entrada
        nfds = NFDevolucao.query.filter(
            NFDevolucao.tipo_documento == 'NFD',
            NFDevolucao.odoo_dfe_id.isnot(None),
            NFDevolucao.data_entrada.is_(None),
            NFDevolucao.ativo == True
        ).all()

        print(f"\n📦 NFDs sem data_entrada: {len(nfds)}")

        if not nfds:
            print("✅ Todas as NFDs já têm data_entrada")
            return

        # Buscar em lote no Odoo
        dfe_ids = [nfd.odoo_dfe_id for nfd in nfds]

        print(f"🔍 Buscando {len(dfe_ids)} registros no Odoo...")

        try:
            registros = odoo.execute_kw(
                'l10n_br_ciel_it_account.dfe',
                'search_read',
                [[('id', 'in', dfe_ids)]],
                {'fields': ['id', 'l10n_br_data_entrada']}
            )
        except Exception as e:
            print(f"❌ Erro ao buscar no Odoo: {e}")
            return

        # Mapear por ID
        mapa_entrada = {}
        for r in registros:
            data_entrada = r.get('l10n_br_data_entrada')
            if data_entrada and data_entrada != False:
                mapa_entrada[r['id']] = data_entrada

        print(f"📅 Registros com data_entrada no Odoo: {len(mapa_entrada)}")

        atualizados = 0
        pendentes = 0
        for nfd in nfds:
            data_str = mapa_entrada.get(nfd.odoo_dfe_id)
            if data_str:
                try:
                    nfd.data_entrada = datetime.strptime(data_str, '%Y-%m-%d').date()
                    atualizados += 1
                except Exception as e:
                    print(f"   ⚠️ Erro ao parsear data {data_str}: {e}")
            else:
                pendentes += 1

        db.session.commit()

        print("\n" + "=" * 60)
        print("✅ SYNC data_entrada CONCLUÍDO")
        print("=" * 60)
        print(f"\n📊 RESUMO:")
        print(f"   ✅ NFDs atualizadas: {atualizados}")
        print(f"   ⏳ NFDs pendentes (ainda sem entrada no Odoo): {pendentes}")
        print("=" * 60)


if __name__ == '__main__':
    sync_data_entrada()
