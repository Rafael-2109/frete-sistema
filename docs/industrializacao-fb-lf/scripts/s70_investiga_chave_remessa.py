"""s70 — INVESTIGA (READ-only) como resolver a CHAVE da remessa (R3 refNFe) p/ o WIRE do R2.

Zero escrita. Mapeia caminhos robustos para chegar à chave da NF de remessa (RPI saída FB)
a partir do que o WIRE tem em mãos:
  - nf1_saida_lf (791437) → referencia_ids (R3 já gravado pela SA da saída, s59)
  - remessa.picking_id (322451, da descoberta) → purchase/origin/move→PO → chave
  - account.move 735679 (RPI) = ground truth da chave.

Uso: python docs/industrializacao-fb-lf/scripts/s70_investiga_chave_remessa.py
"""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema_wire_r2')

from app.odoo.utils.connection import get_odoo_connection

NF1_SAIDA_LF = 791437     # NF-1 serviço (saída LF) — input do wire / descoberta
NF2_SAIDA_LF = 791441     # NF-2 insumos (saída LF)
PICK_REMESSA = 322451     # picking de entrada LF da remessa (da descoberta)
REMESSA_MOVE = 735679     # account.move RPI (saída FB) — ground truth da chave
CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
SEP = '=' * 78


def main():
    o = get_odoo_connection()
    assert o.authenticate(), 'falha autenticacao Odoo'
    print(SEP)
    print('s70 — INVESTIGA chave da remessa (READ-only)')
    print(SEP)

    def rd(model, ids, fields):
        return o.execute_kw(model, 'read', [ids], {'fields': fields, 'context': CTX})

    # ground truth: chave da RPI
    rem = rd('account.move', [REMESSA_MOVE], ['name', 'l10n_br_chave_nf', 'move_type', 'company_id'])[0]
    chave_gt = rem.get('l10n_br_chave_nf')
    print(f"\n[GROUND TRUTH] remessa {REMESSA_MOVE}: {rem.get('name')} "
          f"move_type={rem.get('move_type')} company={rem.get('company_id')}")
    print(f"  chave RPI = {chave_gt}")

    # CAMINHO 1 — referencia_ids da NF de saída LF (R3 já gravado na saída)
    print(f"\n[CAMINHO 1] referencia_ids das NFs de SAÍDA LF")
    am_fields = o.execute_kw('account.move', 'fields_get', [],
                             {'attributes': ['string', 'relation', 'type'], 'context': CTX})
    ref_fields = {k: (am_fields[k].get('type'), am_fields[k].get('relation'))
                  for k in am_fields
                  if 'referencia' in k.lower() or 'refnfe' in k.lower() or 'ref_nfe' in k.lower()}
    print(f"  campos referencia em account.move: {ref_fields}")
    for nf_id, tag in ((NF1_SAIDA_LF, 'NF-1'), (NF2_SAIDA_LF, 'NF-2')):
        for refcampo in [k for k in ref_fields if ref_fields[k][0] in ('one2many', 'many2many')]:
            try:
                mv = rd('account.move', [nf_id], [refcampo, 'name', 'invoice_origin'])[0]
                ids = mv.get(refcampo) or []
                print(f"  {tag} {nf_id} ({mv.get('name')}) .{refcampo} = {ids} | origin={mv.get('invoice_origin')}")
                if ids:
                    rel = ref_fields[refcampo][1]
                    rf = o.execute_kw(rel, 'fields_get', [], {'attributes': ['string'], 'context': CTX})
                    campos = [k for k in rf if 'chave' in k.lower() or 'chnfe' in k.lower() or 'nf' in k.lower()]
                    rows = rd(rel, ids, list(set(campos + ['l10n_br_chave_nf', 'company_id'])))
                    for r in rows:
                        achou = any(str(v).endswith(str(chave_gt)[-20:]) for v in r.values() if v)
                        print(f"     ref {r.get('id')}: { {k: v for k, v in r.items() if v} }  "
                              f"{'<<< CASA COM A CHAVE RPI' if achou else ''}")
            except Exception as e:
                print(f"  {tag} {nf_id} .{refcampo}: erro ({str(e)[:90]})")

    # CAMINHO 2 — picking da remessa → vínculos
    print(f"\n[CAMINHO 2] picking de entrada LF da remessa {PICK_REMESSA}")
    pk_fields = o.execute_kw('stock.picking', 'fields_get', [],
                             {'attributes': ['string', 'relation', 'type'], 'context': CTX})
    cand = [k for k in pk_fields if any(s in k.lower()
            for s in ('purchase', 'origin', 'chave', 'dfe', 'invoice', 'sale'))]
    try:
        pk = rd('stock.picking', [PICK_REMESSA], list(set(cand + ['name', 'origin', 'purchase_id'])))[0]
        print(f"  picking {PICK_REMESSA} ({pk.get('name')}):")
        for k, v in pk.items():
            if v and k != 'id':
                print(f"     {k} = {v}")
        # se tem purchase_id, ver a PO
        po = pk.get('purchase_id')
        if po:
            po_id = po[0] if isinstance(po, list) else po
            po_fields = o.execute_kw('purchase.order', 'fields_get', [],
                                     {'attributes': ['string'], 'context': CTX})
            pcand = [k for k in po_fields if any(s in k.lower()
                     for s in ('chave', 'chnfe', 'dfe', 'origin', 'nf'))]
            por = rd('purchase.order', [po_id], list(set(pcand + ['name', 'origin'])))[0]
            print(f"  → PO {po_id}: { {k: v for k, v in por.items() if v} }")
    except Exception as e:
        print(f"  erro lendo picking: {str(e)[:120]}")

    print(f"\n{SEP}\nFIM s70 — escolher o caminho que CASA com a chave RPI (ground truth acima).")


if __name__ == '__main__':
    main()
