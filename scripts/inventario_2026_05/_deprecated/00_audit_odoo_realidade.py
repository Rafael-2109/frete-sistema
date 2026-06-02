"""
Audit Run: descobre realidade do Odoo antes de gerar constantes.

Saidas:
- docs/inventario-2026-05/00-decisoes/D000-audit-odoo-realidade.md
- /tmp/audit_odoo_realidade.json (consumido por scripts seguintes)

Descobre:
1. location_id de estoque interno por company (FB=1, CD=4, LF=5)
2. picking_type_id por company (validar IDS_FIXOS.md)
3. fiscal_position_id por (company, CFOP) das 4 NFs de referencia
4. Estrutura completa das NFs ref 94457 / 13075 / 147772 / 94410

Uso:
    python scripts/inventario_2026_05/00_audit_odoo_realidade.py --dry-run
    python scripts/inventario_2026_05/00_audit_odoo_realidade.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/..')

import json
import argparse
from app import create_app
from app.odoo.utils.connection import get_odoo_connection
from app.utils.timezone import agora_utc_naive

COMPANIES = {1: 'FB', 4: 'CD', 5: 'LF'}
NFS_REFERENCIA = {
    94457: ('industrializacao', '5901'),
    13075: ('perda', '5903'),
    147772: ('dev-industrializacao', '5949'),
    94410: ('transf-filial', '5152'),
}


def main(dry_run: bool):
    app = create_app()
    with app.app_context():
        odoo = get_odoo_connection()
        result = {
            'timestamp': agora_utc_naive().isoformat(),
            'companies': {},
            'nfs_referencia': {},
        }

        for company_id, codigo in COMPANIES.items():
            print(f'\n=== {codigo} (company_id={company_id}) ===')

            # 1. location_id de estoque interno
            locations = odoo.search_read(
                'stock.location',
                [
                    ['company_id', '=', company_id],
                    ['usage', '=', 'internal'],
                ],
                ['id', 'name', 'complete_name'],
                limit=20,
            )
            print(f'  Locations internas ({len(locations)}):')
            for loc in locations:
                print(f"    id={loc['id']} name={loc['complete_name']!r}")

            # 2. picking_type_id de Recebimento
            picking_types = odoo.search_read(
                'stock.picking.type',
                [
                    ['company_id', '=', company_id],
                    ['code', '=', 'incoming'],
                ],
                ['id', 'name', 'default_location_dest_id'],
            )
            print(f'  Picking types (incoming) ({len(picking_types)}):')
            for pt in picking_types:
                print(f"    id={pt['id']} name={pt['name']!r}")

            result['companies'][company_id] = {
                'codigo': codigo,
                'locations': locations,
                'picking_types_incoming': picking_types,
            }

        for nf_numero, (tipo, cfop) in NFS_REFERENCIA.items():
            print(f'\n=== NF {nf_numero} ({tipo} / CFOP {cfop}) ===')

            # Busca account.move por 'name'. Padrao Odoo: NACOM/YYYY/NNNNN
            # Tentamos 2 campos diferentes para robustez:
            campos_busca = ['l10n_br_numero_nota_fiscal', 'name']
            moves = []
            for campo in campos_busca:
                try:
                    moves = odoo.search_read(
                        'account.move',
                        [[campo, 'ilike', str(nf_numero)]],
                        [
                            'id', 'name', 'move_type', 'l10n_br_tipo_pedido',
                            'l10n_br_numero_nota_fiscal',
                            'partner_id', 'company_id', 'fiscal_position_id',
                            'invoice_date', 'state', 'amount_total',
                            'invoice_line_ids',
                        ],
                        limit=5,
                    )
                    if moves:
                        print(f"  encontrada via campo '{campo}'")
                        break
                except Exception as e:
                    print(f"  campo '{campo}' falhou: {e}")
                    continue

            if not moves:
                print(f'  [NAO ENCONTRADO] NF {nf_numero}')
                result['nfs_referencia'][nf_numero] = {'erro': 'nao_encontrado'}
                continue

            move = moves[0]
            print(f"  id={move['id']} state={move['state']} name={move['name']!r}")
            print(f"  l10n_br_tipo_pedido={move['l10n_br_tipo_pedido']}")
            print(f"  fiscal_position_id={move['fiscal_position_id']}")
            print(f"  company_id={move['company_id']}")
            print(f"  invoice_line_ids count={len(move['invoice_line_ids'])}")

            # Le 1 linha para entender estrutura
            if move['invoice_line_ids']:
                try:
                    linha = odoo.read(
                        'account.move.line',
                        [move['invoice_line_ids'][0]],
                        ['product_id', 'quantity', 'price_unit',
                         'account_id', 'tax_ids', 'l10n_br_operacao_id',
                         'l10n_br_cfop_codigo'],
                    )
                    print(f"  Linha sample: {linha[0]}")
                    move['_linha_sample'] = linha[0]
                except Exception as e:
                    print(f"  erro ao ler linha: {e}")

            result['nfs_referencia'][nf_numero] = move

        # Salva snapshot
        out_path = '/tmp/audit_odoo_realidade.json'
        with open(out_path, 'w') as f:
            json.dump(result, f, default=str, indent=2)
        print(f'\nSnapshot: {out_path}')

        if dry_run:
            print('\n[DRY RUN] Nao gerou documento de decisao. Use sem --dry-run.')
            return

        # Gera documento D000
        doc_path = '/home/rafaelnascimento/projetos/frete_sistema/docs/inventario-2026-05/00-decisoes/D000-audit-odoo-realidade.md'
        os.makedirs(os.path.dirname(doc_path), exist_ok=True)
        with open(doc_path, 'w') as f:
            f.write(_render_decisao(result))
        print(f'Documento: {doc_path}')


def _render_decisao(result):
    lines = [
        '# D000 — Audit Run: realidade do Odoo',
        '',
        f"**Data:** {result['timestamp']}",
        '**Origem:** `scripts/inventario_2026_05/00_audit_odoo_realidade.py`',
        '**Spec:** `docs/superpowers/specs/2026-05-17-ajuste-inventario-nacom-lf-design.md`',
        '',
        '## Locations e Picking Types por Company',
        '',
    ]
    for cid, c in result['companies'].items():
        lines.append(f"### {c['codigo']} (`company_id={cid}`)")
        lines.append('')
        lines.append('**Locations internas:**')
        lines.append('')
        if c['locations']:
            for loc in c['locations']:
                lines.append(f"- `id={loc['id']}` — {loc['complete_name']}")
        else:
            lines.append('- (nenhuma — verificar)')
        lines.append('')
        lines.append('**Picking types (incoming):**')
        lines.append('')
        if c['picking_types_incoming']:
            for pt in c['picking_types_incoming']:
                lines.append(f"- `id={pt['id']}` — {pt['name']}")
        else:
            lines.append('- (nenhum — verificar)')
        lines.append('')

    lines.append('## NFs de Referência')
    lines.append('')
    for nf_num, data in result['nfs_referencia'].items():
        if data.get('erro'):
            lines.append(f"### NF {nf_num} — **NAO ENCONTRADA**")
            lines.append('')
            lines.append('Possibilidade: numero esta em outro campo ou NF nao existe.')
            lines.append('Acao: investigar e atualizar `NFS_REFERENCIA` no script.')
            lines.append('')
            continue
        lines.append(f"### NF {nf_num} (`account.move.id={data['id']}`)")
        lines.append('')
        lines.append(f"- `name`: {data.get('name')!r}")
        lines.append(f"- `move_type`: {data.get('move_type')}")
        lines.append(f"- `l10n_br_tipo_pedido`: {data.get('l10n_br_tipo_pedido')}")
        lines.append(f"- `fiscal_position_id`: {data.get('fiscal_position_id')}")
        lines.append(f"- `company_id`: {data.get('company_id')}")
        lines.append(f"- `state`: {data.get('state')}")
        if '_linha_sample' in data:
            lines.append(f"- Linha sample: `{data['_linha_sample']}`")
        lines.append('')

    lines.append('## Decisões derivadas')
    lines.append('')
    lines.append('Após este audit, atualizar:')
    lines.append('- `app/odoo/constants/locations.py` com `COMPANY_LOCATIONS = {1: ..., 4: ..., 5: ...}`')
    lines.append('- `app/odoo/constants/operacoes_fiscais.py` com `MATRIZ_INTERCOMPANY` (4 entradas, `fiscal_position_id` por company)')
    lines.append('- `.claude/references/odoo/IDS_FIXOS.md` se algum ID divergir')
    lines.append('')
    lines.append('## Itens em aberto')
    lines.append('')
    lines.append('- [ ] Confirmar com Rafael qual `location_id` interno usar quando há múltiplos (escolher principal)')
    lines.append('- [ ] Confirmar com Rafael se NFs com estado ≠ `posted` são válidas como referência')
    lines.append('- [ ] Confirmar `fiscal_position_id` por company para cada CFOP (FB e LF para 5901/5903/5949; FB e CD para 5152)')

    return '\n'.join(lines)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help='Nao gera documento, so imprime')
    args = parser.parse_args()
    main(args.dry_run)
