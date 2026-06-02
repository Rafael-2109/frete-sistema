"""
Audit F0 — Investigar pickings (stock.picking) vinculados as NFs de referencia.

Objetivo: descobrir, sem assumir:
1. picking_type_id de SAIDA por company (outgoing)
2. location_id (origem) e location_dest_id (destino) reais para
   transferencias inter-company

Le os pickings vinculados aos account.move ja mapeados em D002:
- 607443 industrializacao FB→LF
- 588209 perda LF→FB
- 590839 dev-industrializacao CD→LF
- 606403 LF→CD (ja temos id de audit 00d)
- 604472 transf-filial FB→CD
- 607334 transf-filial CD→FB (audit 00c)

Output:
- /tmp/audit_pickings.json
- Atualiza D000 com secao "Pickings inter-company"
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/..')

import json
import argparse
from app import create_app
from app.odoo.utils.connection import get_odoo_connection
from app.utils.timezone import agora_utc_naive

NFS_SAIDA = {
    # id account.move : (descricao, direcao_origem, direcao_destino)
    607443: ('industrializacao FB→LF', 1, 5),
    588209: ('perda LF→FB', 5, 1),
    590839: ('dev-industrializacao CD→LF', 4, 5),
    606403: ('dev-industrializacao LF→CD', 5, 4),
    604472: ('transf-filial FB→CD', 1, 4),
    607334: ('transf-filial CD→FB', 4, 1),
}


def buscar_pickings_de_move(odoo, move_id: int):
    """Le account.move e tenta descobrir pickings vinculados.

    Estrategias (em ordem):
    1. `stock_move_ids` em invoice_line_ids
    2. `picking_ids` se existir no account.move (algumas localizacoes)
    3. Buscar stock.picking com origin = name do move
    4. Buscar stock.move com l10n_br_account_move_id (se existir)
    """
    move = odoo.read('account.move', [move_id],
                     ['id', 'name', 'invoice_line_ids', 'l10n_br_numero_nota_fiscal'])
    if not move:
        return None
    move = move[0]
    pickings_encontrados = []

    # Estrategia 1: pickings com origin = move.name
    nome = move['name']
    if nome:
        pickings = odoo.search_read('stock.picking', [
            ['origin', '=', nome],
        ], ['id', 'name', 'picking_type_id', 'location_id', 'location_dest_id',
            'company_id', 'state', 'partner_id'])
        pickings_encontrados.extend(pickings)

    # Estrategia 2: picking com numero NF na origin
    if move.get('l10n_br_numero_nota_fiscal'):
        nf_num = str(move['l10n_br_numero_nota_fiscal'])
        try:
            pickings = odoo.search_read('stock.picking', [
                ['origin', 'ilike', nf_num],
            ], ['id', 'name', 'picking_type_id', 'location_id',
                'location_dest_id', 'company_id', 'state'], limit=5)
            for p in pickings:
                if p['id'] not in [pe['id'] for pe in pickings_encontrados]:
                    pickings_encontrados.append(p)
        except Exception:
            pass

    return {'move': move, 'pickings': pickings_encontrados}


def main(dry_run: bool):
    app = create_app()
    with app.app_context():
        odoo = get_odoo_connection()
        result = {
            'timestamp': agora_utc_naive().isoformat(),
            'nfs': {},
            'picking_types_outgoing_por_company': {},
        }

        # 1. Investigar pickings das NFs ref
        for move_id, (descricao, origem, destino) in NFS_SAIDA.items():
            print(f'\n=== {descricao} (account.move.id={move_id}) ===')
            print(f'  origem company={origem}, destino company={destino}')
            data = buscar_pickings_de_move(odoo, move_id)
            if not data:
                print('  [NAO ENCONTRADO]')
                continue
            print(f"  move.name={data['move']['name']!r}")
            print(f"  pickings vinculados: {len(data['pickings'])}")
            for p in data['pickings']:
                print(f"    id={p['id']} name={p['name']!r} "
                      f"picking_type={p['picking_type_id']} "
                      f"location_id={p['location_id']} "
                      f"location_dest={p['location_dest_id']} "
                      f"company={p['company_id']} state={p['state']}")
            result['nfs'][str(move_id)] = data

        # 2. Listar TODOS os picking types outgoing por company
        for cid, codigo in [(1, 'FB'), (4, 'CD'), (5, 'LF')]:
            print(f'\n=== Picking types OUTGOING company {codigo} ===')
            pts = odoo.search_read('stock.picking.type', [
                ['company_id', '=', cid],
                ['code', '=', 'outgoing'],
            ], ['id', 'name', 'sequence_code', 'default_location_src_id',
                'default_location_dest_id', 'active'])
            for pt in pts:
                print(f"  id={pt['id']} name={pt['name']!r} active={pt.get('active')}")
                print(f"    src={pt.get('default_location_src_id')} dest={pt.get('default_location_dest_id')}")
            result['picking_types_outgoing_por_company'][cid] = {
                'codigo': codigo,
                'picking_types': pts,
            }

        out = '/tmp/audit_pickings.json'
        with open(out, 'w') as f:
            json.dump(result, f, default=str, indent=2)
        print(f'\nSnapshot: {out}')

        if dry_run:
            return

        # Append em D000
        path = '/home/rafaelnascimento/projetos/frete_sistema/docs/inventario-2026-05/00-decisoes/D000-audit-odoo-realidade.md'
        if not os.path.exists(path):
            print(f'  [WARN] {path} nao existe')
            return
        nova = ['\n---\n', '## Audit 00e — Pickings inter-company\n\n']
        nova.append('### Picking types OUTGOING por company\n\n')
        for cid_str, c in result['picking_types_outgoing_por_company'].items():
            nova.append(f"**{c['codigo']} (company_id={cid_str}):**\n\n")
            for pt in c['picking_types']:
                nova.append(f"- id={pt['id']} {pt['name']!r} "
                            f"src={pt.get('default_location_src_id')} "
                            f"dest={pt.get('default_location_dest_id')}\n")
            nova.append('\n')

        nova.append('### Pickings vinculados as NFs ref\n\n')
        for _move_id_str, data in result['nfs'].items():
            if not data:
                continue
            move = data['move']
            nova.append(f"#### {move['name']} (account.move.id={move['id']})\n\n")
            for p in data['pickings']:
                nova.append(f"- id={p['id']} {p['name']!r} "
                            f"picking_type={p['picking_type_id']} "
                            f"location_id={p['location_id']} "
                            f"location_dest={p['location_dest_id']}\n")
            nova.append('\n')
        with open(path, 'a') as f:
            f.write(''.join(nova))
        print(f'D000 atualizado: {path}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    main(args.dry_run)
