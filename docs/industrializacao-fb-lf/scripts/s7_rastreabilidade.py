#!/usr/bin/env python3
"""S7 RASTREABILIDADE remessa X PA + BoM (READ-only) — qual vínculo de TELA do Odoo liga
a NF de retorno a' remessa, p/ suportar 2 NF com rastreabilidade.

  1. as 2 BoMs do PA (14653 normal / 14794 subcontract) — componentes (a fonte dos 5902).
  2. campos de NF-e REFERENCIADA / documento de origem em account.move (vínculo fiscal nativo).
  3. esses campos estao PREENCHIDOS na VND de retorno e/ou na remessa real? (rastreabilidade hoje)
  4. campos `invoice_origin`/`ref` da VND.

Evita campos pesados (xml/pdf/danfe). NAO escreve nada.
"""
import sys
import argparse
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5]}
PESADOS = ('xml', 'pdf', 'danfe', 'base64', 'qrcode', 'logo', 'image')


def m2o(v):
    return f"{v[0]}|{v[1]}" if isinstance(v, list) and v else ('-' if not v else str(v))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--move-nf', type=int, default=738097)
    ap.add_argument('--boms', nargs='*', type=int, default=[14653, 14794])
    args = ap.parse_args()

    o = get_odoo_connection()
    assert o.authenticate(), "FALHA AUTH"
    print(f"UID {o._uid}")

    def rd(model, ids, fields):
        return o.execute_kw(model, 'read', [list(ids)], {'fields': fields, 'context': CTX}) if ids else []

    # 1) BoMs
    print("\n" + "=" * 88)
    print("1) BoMs do PA (componentes = a fonte dos 5902)")
    print("=" * 88)
    for b in rd('mrp.bom', args.boms, ['id', 'code', 'type', 'product_qty', 'bom_line_ids', 'subcontractor_ids']):
        print(f"\n  BoM {b['id']} type={b.get('type')} qty={b.get('product_qty')} "
              f"subcontractor_ids={b.get('subcontractor_ids')}")
        bls = rd('mrp.bom.line', b.get('bom_line_ids') or [], ['product_id', 'product_qty'])
        for bl in bls:
            print(f"     {m2o(bl.get('product_id'))[:40]:40} qty={bl.get('product_qty')}")

    # 2) campos de NF referenciada / documento origem em account.move
    print("\n" + "=" * 88)
    print("2) account.move — campos de REFERENCIA / documento de origem (vínculo de tela)")
    print("=" * 88)
    fg = o.execute_kw('account.move', 'fields_get', [], {'attributes': ['string', 'type', 'relation'], 'context': CTX})
    refs = {k: v for k, v in fg.items()
            if any(n in k.lower() for n in ('referenc', 'ref_', '_ref', 'documento', 'origin', 'nfe_ref', 'chave', 'related', 'reversed'))
            and not any(p in k.lower() for p in PESADOS)}
    for k, v in sorted(refs.items()):
        print(f"   {k:38} {v.get('type'):10} {str(v.get('string'))[:36]:36} rel={v.get('relation')}")

    # 3) valores desses campos na VND de retorno
    print("\n" + "=" * 88)
    print(f"3) valores dos campos de referencia na VND {args.move_nf}")
    print("=" * 88)
    chave = [k for k in refs if refs[k].get('type') not in ('one2many', 'many2many')]
    chave = ['name', 'invoice_origin', 'ref'] + chave
    chave = list(dict.fromkeys(chave))
    mv = rd('account.move', [args.move_nf], chave)
    if mv:
        for k in chave:
            v = mv[0].get(k)
            if v not in (False, [], None, ''):
                print(f"  {k:34} = {m2o(v) if isinstance(v, list) else v}")

    # 4) tem campo de linhas referenciadas (refNFe)? procurar modelo
    print("\n" + "=" * 88)
    print("4) modelos de NF-e referenciada (refNFe) no ambiente")
    print("=" * 88)
    try:
        models_ref = o.execute_kw('ir.model', 'search_read',
                                  [[('model', 'like', 'l10n_br')]], {'fields': ['model', 'name'], 'context': CTX, 'limit': 200})
        cand = [m for m in models_ref if any(n in m['model'].lower() for n in ('ref', 'documento', 'import_nfe', 'nfe'))]
        for m in cand[:30]:
            print(f"   {m['model']:46} {m['name']}")
    except Exception as e:
        print(f"   erro: {e}")

    print("\n[FIM s7_rastreabilidade — READ-only]")


if __name__ == '__main__':
    main()
