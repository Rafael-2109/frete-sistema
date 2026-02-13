"""
Discovery: IDs fixos para Recebimento CD (company_id=4)

Busca:
- payment.provider.onjournal: "Sem Pagamento" na company CD (4)
- purchase.order.team: verificar team_id=119 na company CD

Executar:
    source .venv/bin/activate && python scripts/discovery_recebimento_cd.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app
from app.odoo.utils.connection import get_odoo_connection


def main():
    app = create_app()
    with app.app_context():
        odoo = get_odoo_connection()

        print("=" * 60)
        print("DISCOVERY: IDs fixos para Recebimento CD (company_id=4)")
        print("=" * 60)

        # 1. payment.provider.onjournal — "Sem Pagamento" no CD
        print("\n--- payment.provider.onjournal (company_id=4) ---")
        providers = odoo.execute_kw(
            'payment.provider.onjournal', 'search_read',
            [[['company_id', '=', 4]]],
            {'fields': ['id', 'name', 'company_id', 'journal_id']}
        )
        if providers:
            for p in providers:
                journal = p.get('journal_id')
                journal_name = journal[1] if isinstance(journal, (list, tuple)) else journal
                marker = " <-- CANDIDATO" if 'sem' in str(p.get('name', '')).lower() else ""
                print(f"  ID={p['id']:>5}  name='{p['name']}'  journal={journal_name}{marker}")
        else:
            print("  NENHUM encontrado! Verificar se modelo existe.")

        # 2. Buscar especificamente "Sem Pagamento"
        print("\n--- Busca especifica: 'Sem Pagamento' CD ---")
        sem_pag = odoo.execute_kw(
            'payment.provider.onjournal', 'search_read',
            [[
                ['company_id', '=', 4],
                ['name', 'ilike', 'Sem Pagamento'],
            ]],
            {'fields': ['id', 'name']}
        )
        if sem_pag:
            for sp in sem_pag:
                print(f"  >>> PAYMENT_PROVIDER_ID_CD = {sp['id']}  (name='{sp['name']}')")
        else:
            print("  NAO encontrado. Listar todos para identificar manualmente.")

        # 3. Verificar team_id=119 no CD
        print("\n--- crm.team ID=119 ---")
        try:
            teams = odoo.execute_kw(
                'crm.team', 'read',
                [[119]],
                {'fields': ['id', 'name', 'company_id']}
            )
            if teams:
                t = teams[0]
                company = t.get('company_id')
                company_str = f"{company[0]} ({company[1]})" if isinstance(company, (list, tuple)) else company
                print(f"  ID={t['id']}  name='{t['name']}'  company={company_str}")
            else:
                print("  Team 119 nao encontrado")
        except Exception as e:
            print(f"  Erro ao buscar team: {e}")

        # 4. Verificar payment.term ID=2800
        print("\n--- account.payment.term ID=2800 ---")
        try:
            terms = odoo.execute_kw(
                'account.payment.term', 'read',
                [[2800]],
                {'fields': ['id', 'name', 'company_id']}
            )
            if terms:
                t = terms[0]
                company = t.get('company_id')
                company_str = f"{company[0]} ({company[1]})" if isinstance(company, (list, tuple)) else company
                print(f"  ID={t['id']}  name='{t['name']}'  company={company_str}")
            else:
                print("  Payment term 2800 nao encontrado")
        except Exception as e:
            print(f"  Erro ao buscar payment term: {e}")

        # 5. Verificar picking_type ID=13 no CD
        print("\n--- stock.picking.type ID=13 ---")
        try:
            pts = odoo.execute_kw(
                'stock.picking.type', 'read',
                [[13]],
                {'fields': ['id', 'name', 'code', 'company_id', 'warehouse_id']}
            )
            if pts:
                pt = pts[0]
                company = pt.get('company_id')
                company_str = f"{company[0]} ({company[1]})" if isinstance(company, (list, tuple)) else company
                wh = pt.get('warehouse_id')
                wh_str = f"{wh[0]} ({wh[1]})" if isinstance(wh, (list, tuple)) else wh
                print(f"  ID={pt['id']}  name='{pt['name']}'  code={pt['code']}  company={company_str}  warehouse={wh_str}")
            else:
                print("  Picking type 13 nao encontrado")
        except Exception as e:
            print(f"  Erro ao buscar picking type: {e}")

        print("\n" + "=" * 60)
        print("FIM do discovery")
        print("=" * 60)


if __name__ == '__main__':
    main()
