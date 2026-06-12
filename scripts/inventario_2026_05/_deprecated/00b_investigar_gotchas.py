"""
Investigacao focada dos GOTCHAS descobertos em F0 Task 0.1:

G001 — Para cada NF de entrada encontrada, buscar a SAIDA correspondente
       (mesmo numero fiscal mas em outra company / outro move_type).

INV-002 — Identificar o que e stock.picking.type id=16 (que IDS_FIXOS.md
       documenta como LF picking_type mas audit nao encontrou).

Output:
- /tmp/audit_gotchas_2026_05.json
- Atualiza docs/inventario-2026-05/02-gotchas/G001-*.md e INV-002-*.md com achados
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/..')

import json
import argparse
from app import create_app
from app.odoo.utils.connection import get_odoo_connection
from app.utils.timezone import agora_utc_naive

# IDs das NFs entrada encontradas em audit anterior
NFS_ENTRADA_ENCONTRADAS = {
    # nf_numero: {'account_move_id_entrada': ..., 'cfop_entrada': ..., 'company_entrada': ...}
    94457: {'id_entrada': 607443, 'cfop': '5901', 'company': 1, 'esperado_saida': True},  # ja eh saida!
    13075: {'id_entrada': 588577, 'cfop': '1903', 'company': 1, 'esperado_saida': False},
    147772: {'id_entrada': 603226, 'cfop': '1949', 'company': 5, 'esperado_saida': False},
    94410: {'id_entrada': 606166, 'cfop': '1152', 'company': 4, 'esperado_saida': False},
}

# CFOP entrada -> CFOP saida correspondente
CFOP_ENTRADA_PARA_SAIDA = {
    '1903': '5903',
    '1949': '5949',
    '1152': '5152',
}

# Onde a SAIDA deve estar (company origem do espelho)
SAIDA_COMPANY_ORIGEM = {
    13075: 5,   # perda: saida da LF -> entrada na FB
    147772: 1,  # dev: a entrada esta na LF, entao saida pode estar na FB (5949)
    94410: 1,   # transf-filial: entrada na CD -> saida na FB (5152)
}


def buscar_saida_correspondente(odoo, nf_numero, _dados_entrada=None):
    """
    Para um numero de NF, busca todos os account.move com aquele numero
    em qualquer company. Filtra os que sao SAIDA (move_type=out_invoice e CFOP 5xxx).
    `_dados_entrada` mantido por compatibilidade futura mas nao acessado.
    """
    _ = _dados_entrada  # marca como usado (no-op)
    moves = odoo.search_read('account.move', [
        ['l10n_br_numero_nota_fiscal', 'ilike', str(nf_numero)],
    ], [
        'id', 'name', 'move_type', 'l10n_br_tipo_pedido',
        'l10n_br_numero_nota_fiscal',
        'company_id', 'fiscal_position_id',
        'invoice_date', 'state',
        'invoice_line_ids',
    ])
    print(f'  Total moves com numero {nf_numero}: {len(moves)}')
    for m in moves:
        print(f"    id={m['id']} move_type={m['move_type']} company={m['company_id']} "
              f"name={m['name']!r} state={m['state']}")

    # Identificar saidas
    saidas = []
    for m in moves:
        if m['move_type'] != 'out_invoice':
            continue
        # Le CFOP da primeira linha
        if not m.get('invoice_line_ids'):
            continue
        linha = odoo.read('account.move.line', [m['invoice_line_ids'][0]],
                          ['l10n_br_cfop_codigo', 'l10n_br_operacao_id'])
        cfop = linha[0].get('l10n_br_cfop_codigo')
        if cfop and cfop.startswith('5'):
            saidas.append({
                **m,
                'cfop_linha': cfop,
                'operacao_linha': linha[0].get('l10n_br_operacao_id'),
            })
    return moves, saidas


def investigar_picking_type_16(odoo):
    """Busca stock.picking.type id=16 sem filtros."""
    try:
        pts = odoo.read('stock.picking.type', [16],
            ['id', 'name', 'code', 'company_id', 'sequence_code',
             'default_location_src_id', 'default_location_dest_id', 'active'])
        if pts:
            pt = pts[0]
            print(f'  stock.picking.type id=16 EXISTE:')
            print(f"    name={pt['name']!r}")
            print(f"    code={pt['code']}")
            print(f"    company_id={pt['company_id']}")
            print(f"    active={pt['active']}")
            print(f"    default_location_src_id={pt.get('default_location_src_id')}")
            print(f"    default_location_dest_id={pt.get('default_location_dest_id')}")
            return pt
    except Exception as e:
        print(f'  Erro lendo id=16: {e}')

    # Listar todos os picking types da LF (active=False inclusive)
    print('\n  Todos os picking types da LF (company_id=5), incluindo inativos:')
    all_pts = odoo.search_read('stock.picking.type', [
        ['company_id', '=', 5],
    ], ['id', 'name', 'code', 'active'])
    for pt in all_pts:
        print(f"    id={pt['id']} name={pt['name']!r} code={pt['code']} active={pt.get('active', True)}")
    return None


def main(dry_run: bool):
    app = create_app()
    with app.app_context():
        odoo = get_odoo_connection()
        result = {
            'timestamp': agora_utc_naive().isoformat(),
            'g001_saidas_correspondentes': {},
            'g002_picking_type_16': None,
        }

        print('\n=== G001: buscar NFs de SAIDA correspondentes ===\n')
        for nf_num, dados in NFS_ENTRADA_ENCONTRADAS.items():
            print(f'\n--- NF {nf_num} (entrada CFOP {dados["cfop"]}, company {dados["company"]}) ---')
            todos, saidas = buscar_saida_correspondente(odoo, nf_num, dados)
            cfop_saida_esperado = CFOP_ENTRADA_PARA_SAIDA.get(dados['cfop'])
            company_saida_esperada = SAIDA_COMPANY_ORIGEM.get(nf_num, dados['company'])

            print(f'  CFOP saida esperado: {cfop_saida_esperado} | company saida esperada: {company_saida_esperada}')
            if saidas:
                print(f'  SAIDAS encontradas ({len(saidas)}):')
                for s in saidas:
                    print(f"    id={s['id']} company={s['company_id']} cfop_linha={s['cfop_linha']} "
                          f"l10n_br_tipo_pedido={s['l10n_br_tipo_pedido']!r}")
            else:
                print(f'  Sem saida correspondente encontrada com numero {nf_num}')
                if dados['cfop'].startswith('5'):
                    print('  (NB: NF original ja era saida — sem busca adicional necessaria)')

            result['g001_saidas_correspondentes'][nf_num] = {
                'todos': todos,
                'saidas_5xxx': saidas,
                'cfop_saida_esperado': cfop_saida_esperado,
                'company_saida_esperada': company_saida_esperada,
            }

        print('\n=== INV-002: investigar stock.picking.type id=16 ===\n')
        pt16 = investigar_picking_type_16(odoo)
        result['g002_picking_type_16'] = pt16

        out = '/tmp/audit_gotchas_2026_05.json'
        with open(out, 'w') as f:
            json.dump(result, f, default=str, indent=2)
        print(f'\nSnapshot: {out}')

        if dry_run:
            print('\n[DRY RUN] (snapshot ja gravado, sem atualizar G001/INV-002.md)')
            return

        # Atualizar G001 com achados
        _atualizar_g001(result['g001_saidas_correspondentes'])
        _atualizar_g002(result['g002_picking_type_16'])


def _atualizar_g001(saidas_por_nf):
    """Adiciona seção ## Resultado da investigação ao G001.md."""
    path = '/home/rafaelnascimento/projetos/frete_sistema/docs/inventario-2026-05/02-gotchas/G001-nfs-referencia-sao-entradas-nao-saidas.md'
    if not os.path.exists(path):
        print(f'  [WARN] {path} nao existe')
        return
    nova_secao = ['\n---\n', '## Resultado da investigação (audit 00b)\n']
    for nf_num, dados in saidas_por_nf.items():
        nova_secao.append(f'\n### NF {nf_num}\n')
        if not dados['saidas_5xxx']:
            nova_secao.append('- **Sem NF de saída** com mesmo número fiscal encontrada.\n')
            nova_secao.append(f'- CFOP saída esperado: {dados["cfop_saida_esperado"]}, '
                              f'company esperada: {dados["company_saida_esperada"]}\n')
            nova_secao.append('- Conclusão: NF de saída pode estar com numeração diferente, '
                              'ou registrada apenas como entrada.\n')
        else:
            nova_secao.append(f'- **{len(dados["saidas_5xxx"])} NF(s) de saída encontrada(s)** '
                              f'com mesmo número.\n')
            for s in dados['saidas_5xxx']:
                nova_secao.append(f"  - `account.move.id={s['id']}` company={s['company_id']} "
                                  f"cfop_linha={s['cfop_linha']} "
                                  f"l10n_br_tipo_pedido={s['l10n_br_tipo_pedido']!r}\n")
    with open(path, 'a') as f:
        f.write(''.join(nova_secao))
    print(f'  G001 atualizado: {path}')


def _atualizar_g002(pt16):
    path = '/home/rafaelnascimento/projetos/frete_sistema/docs/inventario-2026-05/02-gotchas/INV-002-picking-type-LF-divergente.md'
    if not os.path.exists(path):
        return
    nova_secao = ['\n---\n', '## Resultado da investigação\n\n']
    if pt16 is None:
        nova_secao.append('- `stock.picking.type id=16` **não existe** no Odoo atual.\n')
        nova_secao.append('- IDS_FIXOS.md precisa ser corrigido. Usar picking_type id=19 '
                          '(Recebimento principal LF) como referência.\n')
    else:
        nova_secao.append(f'- `stock.picking.type id=16` existe e tem características:\n')
        for k, v in pt16.items():
            nova_secao.append(f'  - `{k}`: {v}\n')
    with open(path, 'a') as f:
        f.write(''.join(nova_secao))
    print(f'  INV-002 atualizado: {path}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    main(args.dry_run)
