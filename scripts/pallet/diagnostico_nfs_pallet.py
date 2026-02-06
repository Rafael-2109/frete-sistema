"""
Diagnostico: NFs de pallet no Odoo vs importadas localmente.

Compara NFs com l10n_br_tipo_pedido='vasilhame' no Odoo
com registros em PalletNFRemessa e MovimentacaoEstoque locais.

Identifica NFs faltantes e a causa provavel (state, intercompany, data, etc.)

Uso:
    source .venv/bin/activate
    python scripts/pallet/diagnostico_nfs_pallet.py
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from datetime import datetime, timedelta
from app import create_app, db
from app.odoo.utils.connection import get_odoo_connection
from app.pallet.models.nf_remessa import PalletNFRemessa
from app.estoque.models import MovimentacaoEstoque
from app.pallet.services.sync_odoo_service import CNPJS_INTERCOMPANY_PREFIXOS


def diagnosticar():
    app = create_app()
    with app.app_context():
        odoo = get_odoo_connection()
        odoo.authenticate()

        data_inicio = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
        print(f"=== DIAGNOSTICO DE NFs DE PALLET (desde {data_inicio}) ===\n")

        # ---------------------------------------------------------------
        # 1. Buscar TODAS as NFs de vasilhame no Odoo (qualquer state)
        # ---------------------------------------------------------------
        print("1. Buscando NFs de vasilhame no Odoo (TODOS os states)...")
        nfs_odoo_todas = odoo.search_read('account.move', [
            ('l10n_br_tipo_pedido', '=', 'vasilhame'),
            ('invoice_date', '>=', data_inicio),
        ], [
            'id', 'name', 'l10n_br_numero_nota_fiscal', 'state',
            'move_type', 'invoice_date', 'partner_id', 'company_id'
        ])
        print(f"   Total NFs vasilhame (qualquer state): {len(nfs_odoo_todas)}")

        # Agrupar por state
        por_state = {}
        for nf in nfs_odoo_todas:
            st = nf.get('state', '?')
            por_state.setdefault(st, []).append(nf)
        for st, lista in sorted(por_state.items()):
            print(f"   - state='{st}': {len(lista)} NFs")

        # Agrupar por move_type
        por_move_type = {}
        for nf in nfs_odoo_todas:
            mt = nf.get('move_type', '?')
            por_move_type.setdefault(mt, []).append(nf)
        print()
        for mt, lista in sorted(por_move_type.items()):
            print(f"   - move_type='{mt}': {len(lista)} NFs")

        # ---------------------------------------------------------------
        # 2. Filtrar exatamente como o sync faz (posted + out_invoice/out_refund)
        # ---------------------------------------------------------------
        print("\n2. Aplicando filtro identico ao sync (posted + out_invoice/out_refund)...")
        nfs_sync_filtro = [
            nf for nf in nfs_odoo_todas
            if nf.get('state') == 'posted'
            and nf.get('move_type') in ('out_invoice', 'out_refund')
        ]
        print(f"   NFs que passam no filtro do sync: {len(nfs_sync_filtro)}")

        # NFs que NAO passam no filtro (potenciais faltantes por filtro)
        nfs_excluidas_filtro = [
            nf for nf in nfs_odoo_todas
            if nf not in nfs_sync_filtro
        ]
        if nfs_excluidas_filtro:
            print(f"   NFs EXCLUIDAS pelo filtro: {len(nfs_excluidas_filtro)}")
            for nf in nfs_excluidas_filtro[:10]:
                print(f"      NF {nf.get('l10n_br_numero_nota_fiscal', '?')} "
                      f"- state={nf.get('state')} "
                      f"- move_type={nf.get('move_type')} "
                      f"- data={nf.get('invoice_date')}")
            if len(nfs_excluidas_filtro) > 10:
                print(f"      ... e mais {len(nfs_excluidas_filtro) - 10}")

        # ---------------------------------------------------------------
        # 3. Verificar filtro intercompany
        # ---------------------------------------------------------------
        print("\n3. Verificando filtro intercompany...")
        nfs_intercompany = []
        nfs_nao_intercompany = []
        partner_ids = set()
        for nf in nfs_sync_filtro:
            p = nf.get('partner_id', [])
            pid = p[0] if isinstance(p, (list, tuple)) else p
            if pid:
                partner_ids.add(pid)

        # Batch fetch partners
        partners_cache = {}
        if partner_ids:
            partners_data = odoo.search_read(
                'res.partner',
                [('id', 'in', list(partner_ids))],
                ['id', 'l10n_br_cnpj', 'name']
            )
            for p in partners_data:
                partners_cache[p['id']] = p

        for nf in nfs_sync_filtro:
            p = nf.get('partner_id', [])
            pid = p[0] if isinstance(p, (list, tuple)) else p
            partner = partners_cache.get(pid, {})
            cnpj = (partner.get('l10n_br_cnpj', '') or '').replace('.', '').replace('-', '').replace('/', '')
            prefixo = cnpj[:8] if cnpj else ''

            if prefixo in CNPJS_INTERCOMPANY_PREFIXOS:
                nfs_intercompany.append(nf)
            else:
                nfs_nao_intercompany.append(nf)

        print(f"   NFs intercompany (ignoradas pelo sync): {len(nfs_intercompany)}")
        print(f"   NFs validas (deveriam ser importadas): {len(nfs_nao_intercompany)}")

        # ---------------------------------------------------------------
        # 4. Comparar com importadas localmente
        # ---------------------------------------------------------------
        print("\n4. Comparando com banco local...")
        nfs_locais_remessa = set(
            r.numero_nf for r in
            PalletNFRemessa.query.filter(PalletNFRemessa.ativo == True).all()
        )
        nfs_locais_mov = set(
            r.numero_nf for r in
            MovimentacaoEstoque.query.filter(
                MovimentacaoEstoque.local_movimentacao == 'PALLET',
                MovimentacaoEstoque.tipo_movimentacao == 'REMESSA',
                MovimentacaoEstoque.ativo == True
            ).all()
        )
        print(f"   PalletNFRemessa locais: {len(nfs_locais_remessa)}")
        print(f"   MovimentacaoEstoque REMESSA/PALLET: {len(nfs_locais_mov)}")

        # NFs do Odoo que deveriam estar localmente mas nao estao
        numeros_odoo_validos = set()
        nfs_por_numero = {}
        for nf in nfs_nao_intercompany:
            num = str(nf.get('l10n_br_numero_nota_fiscal', ''))
            if num:
                numeros_odoo_validos.add(num)
                nfs_por_numero[num] = nf

        faltando_remessa = numeros_odoo_validos - nfs_locais_remessa
        faltando_mov = numeros_odoo_validos - nfs_locais_mov

        print(f"\n   NFs validas no Odoo: {len(numeros_odoo_validos)}")
        print(f"   Faltando em PalletNFRemessa: {len(faltando_remessa)}")
        print(f"   Faltando em MovimentacaoEstoque: {len(faltando_mov)}")

        # ---------------------------------------------------------------
        # 5. Detalhar NFs faltantes
        # ---------------------------------------------------------------
        if faltando_mov:
            print(f"\n5. Detalhes das {len(faltando_mov)} NFs FALTANTES:")
            for num in sorted(list(faltando_mov))[:30]:
                nf = nfs_por_numero.get(num, {})
                p = nf.get('partner_id', [])
                pid = p[0] if isinstance(p, (list, tuple)) else p
                partner = partners_cache.get(pid, {})
                cnpj = (partner.get('l10n_br_cnpj', '') or '').replace('.', '').replace('-', '').replace('/', '')
                company = nf.get('company_id', [])
                company_id = company[0] if isinstance(company, (list, tuple)) else company

                print(f"   NF {num:>10s} | data={nf.get('invoice_date', '?'):>12s} "
                      f"| move_type={nf.get('move_type', '?'):>12s} "
                      f"| company={company_id} "
                      f"| CNPJ={cnpj[:14] if cnpj else '-':>14s} "
                      f"| {partner.get('name', '?')[:40]}")
            if len(faltando_mov) > 30:
                print(f"   ... e mais {len(faltando_mov) - 30}")

            # Verificar se sao NFs sem numero
            sem_numero = [
                nf for nf in nfs_nao_intercompany
                if not str(nf.get('l10n_br_numero_nota_fiscal', '')).strip()
            ]
            if sem_numero:
                print(f"\n   ALERTA: {len(sem_numero)} NFs validas SEM numero (l10n_br_numero_nota_fiscal vazio)")
                for nf in sem_numero[:5]:
                    print(f"      name={nf.get('name')} data={nf.get('invoice_date')}")
        else:
            print("\n5. TODAS as NFs validas do Odoo estao importadas localmente!")

        # ---------------------------------------------------------------
        # 6. Resumo
        # ---------------------------------------------------------------
        print("\n" + "=" * 60)
        print("RESUMO DO DIAGNOSTICO")
        print("=" * 60)
        print(f"NFs vasilhame totais no Odoo:     {len(nfs_odoo_todas)}")
        print(f"  - Passam filtro sync:            {len(nfs_sync_filtro)}")
        print(f"  - Excluidas por state/move_type: {len(nfs_excluidas_filtro)}")
        print(f"  - Excluidas por intercompany:    {len(nfs_intercompany)}")
        print(f"  - Validas para importar:         {len(nfs_nao_intercompany)}")
        print(f"Importadas localmente:             {len(nfs_locais_remessa)}")
        print(f"FALTANDO:                          {len(faltando_mov)}")

        if faltando_mov:
            print("\nACAO RECOMENDADA: Verificar os detalhes acima e corrigir o filtro do sync.")
        else:
            print("\nSITUACAO: Todas as NFs validas estao importadas. "
                  "Se NFs ainda faltam, pode ser problema no campo "
                  "l10n_br_tipo_pedido (NFs nao marcadas como 'vasilhame').")


if __name__ == '__main__':
    diagnosticar()
