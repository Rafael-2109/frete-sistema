"""
Investigacao G003: fiscal_position_id para as direcoes inversas/faltantes.

Direcoes ja confirmadas em D001:
- industrializacao FB → LF: FB fiscal_pos=25
- perda LF → FB:           LF fiscal_pos=91
- dev-industrializacao CD → LF: CD fiscal_pos=74
- transf-filial FB → CD:   FB fiscal_pos=20

Direcoes faltantes (este script investiga):
1. transf-filial CD → FB                 (CFOP 5152 saindo da CD)
2. dev-industrializacao FB → LF          (CFOP 5949 saindo da FB)
3. dev-industrializacao LF → FB          (CFOP 5949 saindo da LF, devolucao)
4. dev-industrializacao LF → CD          (CFOP 5949 saindo da LF, devolucao para CD)

Para cada: busca recente account.move com filtros e le fiscal_position_id.

Output: /tmp/audit_g003.json + atualiza D001 com achados.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/..')

import json
import argparse
from app import create_app
from app.odoo.utils.connection import get_odoo_connection
from app.utils.timezone import agora_utc_naive

DIRECOES_FALTANTES = [
    {
        'descricao': 'transf-filial CD → FB',
        'company_origem': 4,
        'cfop_alvo': '5152',
        'tipo_pedido': 'transf-filial',
    },
    {
        'descricao': 'dev-industrializacao FB → LF',
        'company_origem': 1,
        'cfop_alvo': '5949',
        'tipo_pedido': 'dev-industrializacao',
    },
    {
        'descricao': 'dev-industrializacao LF → FB',
        'company_origem': 5,
        'cfop_alvo': '5949',
        'tipo_pedido': 'dev-industrializacao',
    },
    {
        'descricao': 'dev-industrializacao LF → CD',
        'company_origem': 5,
        'cfop_alvo': '5949',
        'tipo_pedido': 'dev-industrializacao',
    },
]


def buscar_nfs_direcao(odoo, company_origem, tipo_pedido, partner_company_destino=None, limit=5):
    """Busca account.move com filtros da direcao."""
    domain = [
        ['move_type', '=', 'out_invoice'],
        ['company_id', '=', company_origem],
        ['l10n_br_tipo_pedido', '=', tipo_pedido],
        ['state', '=', 'posted'],
    ]
    if partner_company_destino:
        # Tenta filtrar pelo partner_id correspondente a outra company
        # Para isso precisamos do partner_id da company destino (commercial_partner_id)
        try:
            partner = odoo.read('res.company', [partner_company_destino], ['partner_id'])
            if partner and partner[0]['partner_id']:
                domain.append(['partner_id', '=', partner[0]['partner_id'][0]])
        except Exception:
            pass
    return odoo.search_read('account.move', domain,
        ['id', 'name', 'l10n_br_tipo_pedido', 'fiscal_position_id',
         'company_id', 'partner_id', 'invoice_date', 'invoice_line_ids'],
        limit=limit, order='invoice_date desc')


def confirmar_cfop_linha(odoo, move_id):
    """Le primeira linha do move e retorna campos cfop/operacao para o caller comparar."""
    move = odoo.read('account.move', [move_id], ['invoice_line_ids'])
    if not move or not move[0].get('invoice_line_ids'):
        return None
    linha = odoo.read('account.move.line', [move[0]['invoice_line_ids'][0]],
                      ['l10n_br_cfop_codigo', 'l10n_br_operacao_id'])
    return linha[0] if linha else None


def main(dry_run: bool):
    app = create_app()
    with app.app_context():
        odoo = get_odoo_connection()
        result = {
            'timestamp': agora_utc_naive().isoformat(),
            'direcoes': {},
        }

        for direcao in DIRECOES_FALTANTES:
            print(f'\n=== {direcao["descricao"]} ===')
            nfs = buscar_nfs_direcao(
                odoo,
                company_origem=direcao['company_origem'],
                tipo_pedido=direcao['tipo_pedido'],
            )
            print(f'  {len(nfs)} NFs encontradas (limit=5, recentes primeiro)')

            achados = []
            for nf in nfs:
                cfop_linha = confirmar_cfop_linha(odoo, nf['id'])
                cfop = cfop_linha.get('l10n_br_cfop_codigo') if cfop_linha else None
                print(f"    id={nf['id']} name={nf['name']!r} "
                      f"fiscal_pos={nf['fiscal_position_id']} cfop_linha={cfop}")
                if cfop and cfop == direcao['cfop_alvo']:
                    achados.append({
                        'account_move_id': nf['id'],
                        'name': nf['name'],
                        'fiscal_position_id': nf['fiscal_position_id'],
                        'partner_id': nf['partner_id'],
                        'cfop_linha': cfop,
                        'invoice_date': nf['invoice_date'],
                    })

            # Distinct fiscal_position_id
            fiscals_unicos = {}
            for a in achados:
                if a['fiscal_position_id']:
                    fp = tuple(a['fiscal_position_id'])
                    if fp not in fiscals_unicos:
                        fiscals_unicos[fp] = a

            if fiscals_unicos:
                print(f'  fiscal_position_ids distintos para CFOP {direcao["cfop_alvo"]}:')
                for fp, a in fiscals_unicos.items():
                    print(f'    fiscal_pos={fp} (exemplo: id={a["account_move_id"]} '
                          f'name={a["name"]!r})')
            else:
                print(f'  Nenhuma NF com cfop={direcao["cfop_alvo"]} confirmada')

            result['direcoes'][direcao['descricao']] = {
                'criterios': direcao,
                'achados': achados,
                'fiscal_positions_distintos': [
                    {'fiscal_position': list(fp), 'exemplo_id': a['account_move_id']}
                    for fp, a in fiscals_unicos.items()
                ],
            }

        out = '/tmp/audit_g003.json'
        with open(out, 'w') as f:
            json.dump(result, f, default=str, indent=2)
        print(f'\nSnapshot: {out}')

        if dry_run:
            return

        # Atualizar D001
        path = '/home/rafaelnascimento/projetos/frete_sistema/docs/inventario-2026-05/00-decisoes/D001-escolhas-pos-audit.md'
        nova = ['\n---\n', '## G003 — Resultado da investigação (2026-05-17)\n\n']
        for descricao, d in result['direcoes'].items():
            nova.append(f'### {descricao}\n\n')
            if d['fiscal_positions_distintos']:
                nova.append(f'`fiscal_position_id` candidatos:\n')
                for fp in d['fiscal_positions_distintos']:
                    nova.append(f"- `{fp['fiscal_position']}` (exemplo: account.move.id={fp['exemplo_id']})\n")
            else:
                nova.append(f'- Nenhuma NF de SAÍDA com CFOP {d["criterios"]["cfop_alvo"]} '
                            f'confirmada na company {d["criterios"]["company_origem"]} ainda. '
                            f'Direcao pode nao ter precedente no Odoo — investigar manualmente.\n')
            nova.append('\n')
        with open(path, 'a') as f:
            f.write(''.join(nova))
        print(f'D001 atualizado: {path}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    main(args.dry_run)
