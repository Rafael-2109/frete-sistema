"""
Investigacao G003 (segunda rodada): variacoes nao abordadas.

Usuario confirmou: FB, CD, LF ficam TODAS em Santana de Parnaiba/SP.
Logo, CFOP 6902 (interestadual) em FB→LF eh anomalo. Investigar:

1. NF SPI/2026/00007 (id=559045) — verificar partner_id real
2. Buscar NFs FB→partner=LF (filtro restrito) — fiscal_position correto?
3. Buscar TODAS as direcoes filtradas por partner_id da company destino
4. Compilar variacoes finais de fiscal_position_id por (origem, destino)

Output: /tmp/audit_variacoes.json + appendice em D001.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/..')

import json
import argparse
from app import create_app
from app.odoo.utils.connection import get_odoo_connection
from app.utils.timezone import agora_utc_naive

# Partner_id de cada company (confirmado em audits anteriores)
COMPANY_PARTNER_ID = {
    1: 1,    # FB → res.partner.id=1
    4: 34,   # CD → res.partner.id=34
    5: 35,   # LF → res.partner.id=35
}

DIRECOES_FINAIS = [
    # (company_origem, partner_destino_company_id, tipo_pedido, descricao)
    (1, 5, 'industrializacao', 'industrializacao FB → LF'),
    (5, 1, 'perda', 'perda LF → FB'),
    (1, 5, 'dev-industrializacao', 'dev-industrializacao FB → LF'),
    (4, 5, 'dev-industrializacao', 'dev-industrializacao CD → LF'),
    (5, 1, 'dev-industrializacao', 'dev-industrializacao LF → FB'),
    (5, 4, 'dev-industrializacao', 'dev-industrializacao LF → CD'),
    (1, 4, 'transf-filial', 'transf-filial FB → CD'),
    (4, 1, 'transf-filial', 'transf-filial CD → FB'),
]


def investigar_nf_spi(odoo):
    """Verifica NF SPI/2026/00007 — por que CFOP 6902 se tudo eh SP?"""
    print('\n=== Investigando NF SPI/2026/00007 (id=559045) ===')
    moves = odoo.read('account.move', [559045],
        ['id', 'name', 'move_type', 'l10n_br_tipo_pedido',
         'company_id', 'partner_id', 'fiscal_position_id',
         'state', 'invoice_line_ids'])
    if not moves:
        print('  NF nao encontrada')
        return None
    nf = moves[0]
    print(f"  company_id: {nf['company_id']}")
    print(f"  partner_id: {nf['partner_id']}")

    # Le res.partner para ver endereco
    if nf['partner_id']:
        partner = odoo.read('res.partner', [nf['partner_id'][0]],
            ['name', 'state_id', 'city', 'l10n_br_cnpj'])
        print(f'  partner detalhes:')
        for k, v in partner[0].items():
            print(f'    {k}: {v}')

    # Le linha completa
    if nf['invoice_line_ids']:
        linha = odoo.read('account.move.line', [nf['invoice_line_ids'][0]],
            ['product_id', 'l10n_br_cfop_codigo', 'l10n_br_operacao_id'])
        print(f'  linha[0]: {linha[0]}')

    return nf


def buscar_nfs_direcao_estrito(odoo, company_origem, partner_company_destino, tipo_pedido, limit=10):
    """Busca NFs filtrando explicitamente partner_id de destino."""
    partner_id = COMPANY_PARTNER_ID.get(partner_company_destino)
    domain = [
        ['move_type', '=', 'out_invoice'],
        ['company_id', '=', company_origem],
        ['l10n_br_tipo_pedido', '=', tipo_pedido],
        ['partner_id', '=', partner_id],
        ['state', '=', 'posted'],
    ]
    return odoo.search_read('account.move', domain,
        ['id', 'name', 'fiscal_position_id', 'partner_id',
         'company_id', 'invoice_date', 'invoice_line_ids'],
        limit=limit, order='invoice_date desc')


def main(dry_run: bool):
    app = create_app()
    with app.app_context():
        odoo = get_odoo_connection()

        # 1. Investigar NF SPI especifica
        spi = investigar_nf_spi(odoo)

        # 2. Investigar TODAS as direcoes com filtro partner restrito
        result = {
            'timestamp': agora_utc_naive().isoformat(),
            'nf_spi_anomala': spi,
            'direcoes': {},
        }

        for origem, destino, tipo, descricao in DIRECOES_FINAIS:
            print(f'\n=== {descricao} (filtro partner_id={COMPANY_PARTNER_ID[destino]}) ===')
            nfs = buscar_nfs_direcao_estrito(odoo, origem, destino, tipo)
            print(f'  {len(nfs)} NFs')

            fiscals = {}  # fp_id -> exemplo
            cfops = {}    # cfop -> count
            for nf in nfs:
                # Le linha para CFOP
                if nf.get('invoice_line_ids'):
                    try:
                        linha = odoo.read('account.move.line', [nf['invoice_line_ids'][0]],
                                          ['l10n_br_cfop_codigo'])
                        cfop = linha[0].get('l10n_br_cfop_codigo')
                    except Exception:
                        cfop = None
                else:
                    cfop = None

                fp = tuple(nf['fiscal_position_id']) if nf.get('fiscal_position_id') else None
                if fp not in fiscals:
                    fiscals[fp] = {'exemplo_id': nf['id'], 'name': nf['name']}
                cfops[cfop] = cfops.get(cfop, 0) + 1

            print(f'  fiscal_positions distintos: {len(fiscals)}')
            for fp, ex in fiscals.items():
                print(f'    {fp}: exemplo id={ex["exemplo_id"]} name={ex["name"]!r}')
            print(f'  CFOPs distintos: {cfops}')

            result['direcoes'][descricao] = {
                'origem_company_id': origem,
                'destino_company_id': destino,
                'tipo_pedido': tipo,
                'partner_id_filtro': COMPANY_PARTNER_ID[destino],
                'total_nfs': len(nfs),
                'fiscal_positions': [{'fp': list(fp) if fp else None,
                                      'exemplo_id': ex['exemplo_id'],
                                      'name': ex['name']}
                                     for fp, ex in fiscals.items()],
                'cfops_distribuicao': cfops,
            }

        out = '/tmp/audit_variacoes.json'
        with open(out, 'w') as f:
            json.dump(result, f, default=str, indent=2)
        print(f'\nSnapshot: {out}')

        if dry_run:
            return

        # Append em D001
        path = '/home/rafaelnascimento/projetos/frete_sistema/docs/inventario-2026-05/00-decisoes/D001-escolhas-pos-audit.md'
        nova = ['\n---\n', '## G003 — Variacoes confirmadas (audit 00d)\n\n',
                'Filtro partner_id restrito (companies em Santana de Parnaiba/SP):\n\n',
                '| Direcao | CFOPs distribuidos | fiscal_position_id distintos |\n',
                '|---|---|---|\n']
        for descricao, d in result['direcoes'].items():
            cfops_str = ', '.join(f"{c}:{n}" for c, n in d['cfops_distribuicao'].items())
            fps_str = '; '.join(
                f"id={fp['fp'][0] if fp['fp'] else 'None'} ({fp['fp'][1] if fp['fp'] else ''})"
                for fp in d['fiscal_positions']
            )
            nova.append(f'| {descricao} | {cfops_str or "—"} | {fps_str or "—"} |\n')
        with open(path, 'a') as f:
            f.write(''.join(nova))
        print(f'D001 atualizado: {path}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    main(args.dry_run)
